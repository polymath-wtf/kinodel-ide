"""Authored text-foundation route; invocation and checkpoint binding belong to the worker."""

import json
import inspect
import sqlite3
from typing import Awaitable, Callable, Literal, NotRequired, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from backend.domain import ArtifactRef, OwnerResponseV1, StoryV1, sha256_digest
from backend.review_store import apply_story_decision, prepare_story_review
from backend.story_store import (_uuid, commit_owner_response, commit_story_operation,
                                 prepare_story_operation, read_story)


STAGE_ID = "storytell"
GATE_ID = "story-hitl"
SLOT = "story"


class StoryOwnerUnavailable(Exception):
    """Only a bounded owner-call transport failure can be retried as the same operation."""


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


def initial_story_state(project_id: str, execution_id: str) -> StoryState:
    _uuid(project_id)
    _uuid(execution_id)
    activation = sha256_digest(json.dumps(
        ["kinodel.test-story-start.v1", execution_id, STAGE_ID], separators=(",", ":")
    ).encode("utf-8"))
    return {"project_id": project_id, "execution_id": execution_id, "story_activation": activation}


def build_story_graph(db: sqlite3.Connection, saver: object,
                      produce_story: Callable[[str, list[str], StoryV1 | None, str | None], StoryV1 | Awaitable[StoryV1]]):
    """Build the fixed Story route with a bounded model substitute supplied by caller."""

    async def story(state: StoryState) -> dict:
        execution = state["execution_id"]
        row = db.execute("SELECT project_id,input_message,shot_ids FROM executions WHERE execution_id=?",
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
                if action and "discussion" in inspect.signature(produce_story).parameters:
                    prepared = db.execute("SELECT prepared_inputs FROM story_operations WHERE execution_id=? "
                                          "AND activation_id=?", (execution, state["story_activation"])).fetchone()[0]
                    kwargs["discussion"] = json.loads(prepared)[-1]
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
        ref = ArtifactRef.model_validate(state["story_ref"])
        request = prepare_story_review(
            db, state["execution_id"], state["story_activation"], ref,
            state["binding_revision"], previous_request_id=state.get("previous_request_id"),
        )
        return {"review_ref": {"request_id": request.request_id, "revision": request.revision,
                               "digest": request.digest, "binding_revision": state["binding_revision"]}}

    async def wait(state: StoryState) -> dict:
        # Pure before interrupt: the node is replayed on every resume.
        decision_id = interrupt(state["review_ref"])
        if not isinstance(decision_id, str):
            raise ValueError("Invalid decision reference")
        return {"decision_id": decision_id}

    async def apply(state: StoryState) -> Command[Literal["storytell", "__end__"]]:
        request_id = state["review_ref"]["request_id"]
        row = db.execute("SELECT action FROM review_requests WHERE execution_id=? AND request_id=? "
                         "AND decision_id=?", (state["execution_id"], request_id, state["decision_id"])).fetchone()
        if row is None:
            raise ValueError("Review decision does not match this wait")
        activation = apply_story_decision(db, state["execution_id"], request_id, state["decision_id"])
        if row[0] == "approve":
            return Command(update={"approved_story": state["story_ref"], "decision_id": ""}, goto=END)
        if row[0] in ("revise", "clarify"):
            return Command(update={"story_activation": activation, "previous_request_id": request_id,
                                   "decision_id": ""}, goto=STAGE_ID)
        raise ValueError("Unsupported Story decision")

    graph = StateGraph(StoryState)
    graph.add_node(STAGE_ID, story)
    graph.add_node("story_prepare_review", prepare)
    graph.add_node("story_wait", wait)
    graph.add_node("story_apply", apply)
    graph.add_edge(START, STAGE_ID)
    graph.add_edge(STAGE_ID, "story_prepare_review")
    graph.add_edge("story_prepare_review", "story_wait")
    graph.add_edge("story_wait", "story_apply")
    return graph.compile(checkpointer=saver)
