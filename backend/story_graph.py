"""Frozen Story-only and Story→Wardrobe routes; invocation/wait binding stay worker-owned."""

import json
import inspect
import sqlite3
from pathlib import Path
from typing import Awaitable, Callable, Literal, NotRequired, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from backend.domain import ArtifactRef, OwnerResponseV1, StoryV1, sha256_digest
from backend.review_store import apply_story_decision, prepare_story_review
from backend.story_store import (_assert_writable, _uuid, commit_owner_response, commit_story_operation,
                                 prepare_story_operation, read_story)


STAGE_ID = "storytell"
GATE_ID = "story-hitl"
SLOT = "story"


class StoryOwnerUnavailable(Exception):
    """Only a bounded owner-call transport failure can be retried as the same operation."""


class WardrobeBlocked(Exception):
    """Stable non-success work reason; the operation retains its result/budget."""


class StoryState(TypedDict):
    project_id: str
    execution_id: str
    story_activation: str
    story_ref: NotRequired[dict]
    binding_revision: NotRequired[int]
    review_ref: NotRequired[dict]
    previous_request_id: NotRequired[str]
    decision_id: NotRequired[str]
    approved_story: NotRequired[dict]
    wardrobe_activation: NotRequired[str]
    wardrobe_plan: NotRequired[dict]
    wardrobe_transition: NotRequired[str]


def initial_story_state(project_id: str, execution_id: str, *, live: bool = False) -> StoryState:
    _uuid(project_id)
    _uuid(execution_id)
    activation = sha256_digest(json.dumps(
        ["kinodel.live-story-start.v1" if live else "kinodel.test-story-start.v1", execution_id, STAGE_ID], separators=(",", ":")
    ).encode("utf-8"))
    return {"project_id": project_id, "execution_id": execution_id, "story_activation": activation}


def build_story_graph(db: sqlite3.Connection, saver: object,
                      produce_story: Callable[[str, list[str], StoryV1 | None, str | None], StoryV1 | Awaitable[StoryV1]],
                      *, wardrobe: bool = False, character_root: Path | None = None):
    """Historical topology and terminal semantics remain frozen."""
    return story_graph_builder(db, produce_story, wardrobe=wardrobe,
                               character_root=character_root).compile(checkpointer=saver)


def story_graph_builder(db, produce_story, *, wardrobe=False, character_root=None,
                        anchor_batch=False, state_schema=StoryState):
    """Concrete shared Story/review/Wardrobe nodes, not a pipeline compiler."""

    def require_route(state):
        from backend import wardrobe_store
        from backend.story_start import GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST, LIVE_GRAPH_ID, LIVE_GRAPH_DIGESTS

        identity = db.execute("SELECT graph_id,graph_version,graph_digest FROM executions WHERE execution_id=?",
                              (state["execution_id"],)).fetchone()
        supported = (wardrobe_store.is_story_anchor_graph(identity) if anchor_batch else
            wardrobe_store.is_current_wardrobe_graph(identity) if wardrobe else
            identity == (GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST) or (identity is not None and
                identity[0] == LIVE_GRAPH_ID and identity[1] in LIVE_GRAPH_DIGESTS and
                identity[2] == LIVE_GRAPH_DIGESTS[identity[1]]))
        if not supported:
            raise ValueError("Story graph does not match a supported frozen approval route")

    async def story(state: StoryState) -> dict:
        require_route(state)
        execution = state["execution_id"]
        row = db.execute("SELECT project_id,input_message,shot_ids,owner_config FROM executions WHERE execution_id=?",
                         (execution,)).fetchone()
        if row is None or row[0] != state["project_id"]:
            raise ValueError("Unknown test execution/project")
        prior = None
        feedback = None
        expected = None
        action = None
        if "previous_request_id" in state:
            previous = db.execute("SELECT decision_id,action,message,applied_activation "
                                  "FROM review_requests WHERE execution_id=? AND request_id=?",
                                  (execution, state["previous_request_id"])).fetchone()
            if previous is None or previous[1] not in ("revise", "clarify") or previous[3] != state["story_activation"]:
                raise ValueError("Revision activation does not match applied review")
            prior = read_story(db, execution, artifact_id=state["story_ref"]["artifact_id"])[0]
            if prior.model_dump(mode="json") != state["story_ref"]:
                raise ValueError("Prior Story ref changed")
            feedback, expected = previous[2], state["binding_revision"]
            action = previous[1]
        _, digest, replay = prepare_story_operation(
            db, execution, state["story_activation"], prior_ref=prior,
            feedback=feedback, expected_revision=expected,
            request_id=state.get("previous_request_id"), action=action,
        )
        if replay is None:
            prior_body = read_story(db, execution, artifact_id=prior.artifact_id)[1] if prior else None
            try:
                kwargs = {}
                if action and row[3] is None and "discussion" in inspect.signature(produce_story).parameters:
                    prepared = db.execute("SELECT prepared_inputs FROM story_operations WHERE execution_id=? "
                                          "AND activation_id=?", (execution, state["story_activation"])).fetchone()[0]
                    kwargs["discussion"] = json.loads(prepared)[-1]
                if row[3] is not None:
                    from backend.openrouter import produce_live_story
                    draft = produce_live_story(db, execution, state["story_activation"], prior_body, feedback, action)
                else:
                    draft = produce_story(row[1], json.loads(row[2]), prior_body, feedback, **kwargs)
                if inspect.isawaitable(draft):
                    draft = await draft
            except (TimeoutError, ConnectionError) as error:
                raise StoryOwnerUnavailable("Story owner unavailable") from error
            if isinstance(draft, (dict, OwnerResponseV1)):
                response = OwnerResponseV1.model_validate(draft)
                trigger = commit_owner_response(db, execution, state["story_activation"],
                                                digest, response.model_dump(mode="json"))
                return {"story_activation": trigger}
            if action == "clarify":
                raise ValueError("Clarification must return an owner explanation")
            ref, trigger = commit_story_operation(db, execution, state["story_activation"],
                                                  digest, str(uuid4()), draft)
        else:
            ref, trigger = replay
            if isinstance(ref, dict):
                OwnerResponseV1.model_validate(ref)
                return {"story_activation": trigger}
        return {"story_ref": ref.model_dump(mode="json"),
                "binding_revision": (expected or 0) + 1, "story_activation": trigger}

    async def prepare(state: StoryState) -> dict:
        require_route(state)
        ref = ArtifactRef.model_validate(state["story_ref"])
        request = prepare_story_review(
            db, state["execution_id"], state["story_activation"], ref,
            state["binding_revision"], previous_request_id=state.get("previous_request_id"),
        )
        return {"review_ref": {"request_id": request.request_id, "revision": request.revision,
                               "digest": request.digest, "binding_revision": state["binding_revision"]}}

    async def wait(state: StoryState) -> dict:
        # Pure before interrupt: the node is replayed on every resume.
        require_route(state)
        decision_id = interrupt(state["review_ref"])
        if not isinstance(decision_id, str):
            raise ValueError("Invalid decision reference")
        return {"decision_id": decision_id}

    async def apply(state: StoryState) -> Command[Literal["storytell", "wardrobe", "__end__"]]:
        require_route(state)
        request_id = state["review_ref"]["request_id"]
        row = db.execute("SELECT action FROM review_requests WHERE execution_id=? AND request_id=? "
                         "AND decision_id=?", (state["execution_id"], request_id, state["decision_id"])).fetchone()
        if row is None:
            raise ValueError("Review decision does not match this wait")
        activation = apply_story_decision(db, state["execution_id"], request_id, state["decision_id"])
        if row[0] == "approve":
            if wardrobe:
                return Command(update={"approved_story": state["story_ref"], "decision_id": "",
                                       "wardrobe_activation": activation}, goto="wardrobe")
            return Command(update={"approved_story": state["story_ref"], "decision_id": ""}, goto=END)
        if row[0] in ("revise", "clarify"):
            return Command(update={"story_activation": activation, "previous_request_id": request_id,
                                   "decision_id": ""}, goto=STAGE_ID)
        raise ValueError("Unsupported Story decision")

    async def wardrobe_node(state: StoryState) -> dict:
        require_route(state)
        from backend.openrouter_wardrobe import WardrobeInvalidOutput, WardrobeOwnerUnavailable
        from backend.story_start import DEFAULT_CHARACTER_ROOT
        from backend.wardrobe_operation import produce_wardrobe_operation
        from backend import wardrobe_store

        execution, request = state["execution_id"], state["review_ref"]["request_id"]
        try:
            _assert_writable(db, execution)
            approval = db.execute("SELECT applied_activation,request_digest,request_revision,binding_revision "
                                  "FROM review_requests WHERE execution_id=? AND request_id=?",
                                  (execution, request)).fetchone()
            if (approval != (state["wardrobe_activation"], state["review_ref"]["digest"],
                             state["review_ref"]["revision"], state["review_ref"]["binding_revision"]) or
                    ArtifactRef.model_validate(state["approved_story"]) != read_story(db, execution)[0]):
                raise ValueError("Wardrobe checkpoint handoff mismatch")
            result, transition = await produce_wardrobe_operation(db, execution, request,
                character_root=character_root if character_root is not None else DEFAULT_CHARACTER_ROOT)
            if isinstance(result, OwnerResponseV1):
                raise WardrobeBlocked(f"wardrobe_{result.status}")
            db.execute("BEGIN IMMEDIATE")
            try:
                _assert_writable(db, execution)
                ref = validate_wardrobe_success(db, execution, request)
                if ref != result or db.execute("SELECT next_activation FROM wardrobe_operations WHERE operation_id=?",
                                               (ref.operation_id,)).fetchone() != (transition,):
                    raise ValueError("Wardrobe result ref/transition mismatch")
                if not anchor_batch:
                    # Only the historical route completes at Wardrobe.
                    db.execute("INSERT INTO execution_outcomes VALUES (?, 'completed', ?, ?)",
                               (execution, ref.operation_id, ref.artifact_id))
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise
            return {"wardrobe_plan": ref.model_dump(mode="json"), "wardrobe_transition": transition}
        except WardrobeOwnerUnavailable:
            record = wardrobe_store.find_wardrobe_operation(db, execution, request)
            reason = "wardrobe_exhausted" if record is not None and record["owner_attempts"] >= 2 else "wardrobe_unavailable"
            raise WardrobeBlocked(reason) from None
        except wardrobe_store.WardrobeAttemptBudgetExhausted:
            raise WardrobeBlocked("wardrobe_exhausted") from None
        except WardrobeInvalidOutput:
            raise WardrobeBlocked("wardrobe_invalid_output") from None
        except (ValueError, OSError):
            raise WardrobeBlocked("wardrobe_invalid") from None

    graph = StateGraph(state_schema)
    graph.add_node(STAGE_ID, story)
    graph.add_node("story_prepare_review", prepare)
    graph.add_node("story_wait", wait)
    graph.add_node("story_apply", apply, destinations=(STAGE_ID, "wardrobe" if wardrobe else END))
    graph.add_edge(START, STAGE_ID)
    graph.add_edge(STAGE_ID, "story_prepare_review")
    graph.add_edge("story_prepare_review", "story_wait")
    graph.add_edge("story_wait", "story_apply")
    if wardrobe:
        graph.add_node("wardrobe", wardrobe_node)
        if not anchor_batch:
            graph.add_edge("wardrobe", END)
    return graph


def validate_wardrobe_success(db: sqlite3.Connection, execution_id: str, request_id: str) -> ArtifactRef:
    """Read-only terminal validation, including after a terminal commit lost its checkpoint."""
    from backend import wardrobe_store
    return wardrobe_store.read_committed_wardrobe_plan(db, execution_id, request_id).ref
