"""Historical live-v1 checkpoint writer, independent of the post-W4 graph factory."""

import asyncio
from dataclasses import asdict
from functools import partial
import json
import os
from pathlib import Path
import sys
from typing import Literal, NotRequired, TypedDict
import unittest
from unittest.mock import patch
from uuid import uuid4

from story_process_support import ProcessStoryTest, parked, snapshot
import httpx
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from backend.api import fixture_story
from backend.domain import ArtifactRef, StoryTextInputV1, sha256_digest
from backend.openrouter import produce_live_story
from backend.review_store import apply_story_decision, bind_story_wait, prepare_story_review
from backend.story_control import open_story_runtime
from backend.story_graph import initial_story_state
from backend.story_start import _start_story
from backend.story_store import commit_story_operation, prepare_story_operation
from tests.test_story_cast import old_config, OLD_PROMPT
from tests.test_wardrobe_openrouter import envelope


class PreW4StoryState(TypedDict):
    # Exact state channels before W4; do NOT derive these from today's StoryState.
    project_id: str
    execution_id: str
    story_activation: str
    story_ref: NotRequired[dict]
    binding_revision: NotRequired[int]
    review_ref: NotRequired[dict]
    previous_request_id: NotRequired[str]
    decision_id: NotRequired[str]
    approved_story: NotRequired[dict]


async def write_pre_w4_wait(runtime, project, execution, work_id):
    """Only bootstrap generate→review; subsequent recovery uses the production runner.

    Test-only reduction of the pre-W4 factory: original channels/node names/edges,
    v1 config, real Story operation and interrupt. No Wardrobe node or destinations.
    """
    db = runtime.db

    async def story(state):
        _, digest, replay = prepare_story_operation(db, execution, state["story_activation"])
        assert replay is None
        body = await produce_live_story(db, execution, state["story_activation"], None, None, None)
        ref, trigger = commit_story_operation(db, execution, state["story_activation"], digest, str(uuid4()), body)
        return {"story_ref": ref.model_dump(mode="json"), "binding_revision": 1, "story_activation": trigger}

    async def prepare(state):
        request = prepare_story_review(db, execution, state["story_activation"],
                                       ArtifactRef.model_validate(state["story_ref"]), state["binding_revision"])
        return {"review_ref": {"request_id": request.request_id, "revision": request.revision,
                               "digest": request.digest, "binding_revision": state["binding_revision"]}}

    async def wait(state):
        return {"decision_id": interrupt(state["review_ref"])}

    async def apply(state) -> Command[Literal["storytell", "__end__"]]:
        request = state["review_ref"]["request_id"]
        action = db.execute("SELECT action FROM review_requests WHERE request_id=?", (request,)).fetchone()[0]
        activation = apply_story_decision(db, execution, request, state["decision_id"])
        if action == "approve":
            return Command(update={"approved_story": state["story_ref"], "decision_id": ""}, goto=END)
        return Command(update={"story_activation": activation, "previous_request_id": request, "decision_id": ""}, goto="storytell")

    graph = StateGraph(PreW4StoryState)
    for name, node in (("storytell", story), ("story_prepare_review", prepare), ("story_wait", wait), ("story_apply", apply)):
        graph.add_node(name, node)
    for source, target in ((START, "storytell"), ("storytell", "story_prepare_review"),
                           ("story_prepare_review", "story_wait"), ("story_wait", "story_apply")):
        graph.add_edge(source, target)
    compiled = graph.compile(checkpointer=runtime.saver)
    config = {"configurable": {"thread_id": execution}}
    await compiled.ainvoke(initial_story_state(project, execution, live=True), config, durability="sync")
    saved = await compiled.aget_state(config)
    assert saved.next == ("story_wait",) and len(saved.tasks) == len(saved.interrupts) == 1
    bind_story_wait(db, execution, saved.values["review_ref"]["request_id"],
                    saved.config["configurable"]["checkpoint_id"], saved.tasks[0].id, saved.interrupts[0].id)
    db.execute("UPDATE execution_work SET status='completed',settled_checkpoint_id=? WHERE work_id=?",
               (saved.config["configurable"]["checkpoint_id"], work_id))


async def child(root, mode, action=None):
    requests = []

    def respond(request):
        if mode in ("inspect", "offline") or request.method != "POST":
            raise AssertionError("Historical reopen read a current catalog or repeated a committed effect")
        payload = json.loads(request.content)
        requests.append(payload)
        task = json.loads(payload["messages"][1]["content"])
        result = ({"status": "clarified", "explanation": "Frozen live-v1 explanation."} if task["action"] == "clarify" else
                  {"status": "ready", "story": fixture_story("Frozen live-v1", ["s1"], None, None).model_dump(mode="json"), "explanation": None})
        return httpx.Response(200, json=envelope(result))

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret", "LLM_MODEL": "changed/model"}), \
            patch("backend.openrouter_client.httpx.AsyncClient", partial(httpx.AsyncClient, transport=httpx.MockTransport(respond))), \
            patch("pathlib.Path.read_text", side_effect=AssertionError("Historical reopen read current prompt")):
        async with open_story_runtime(root, fixture_story) as runtime:
            db, saver = runtime.db, runtime.saver
            if mode == "setup":
                project = str(uuid4())
                brief = StoryTextInputV1(user_vibe="An old Story", subjects=[], shot_duration_ms=5000)
                # Real v1 owner config, start digest and graph identity from inception; not a retagged v2 run.
                start = await _start_story(db, saver, project, "start", brief.user_vibe, ["s1"], old_config(brief))
                await write_pre_w4_wait(runtime, project, start.execution_id, start.work_id)
            eid = db.execute("SELECT execution_id FROM executions WHERE client_key='start'").fetchone()[0]
            if mode in ("decide", "duplicate", "stale", "conflict"):
                if mode in ("decide", "duplicate"):
                    assert action is not None
                revision = int(action) if mode == "duplicate" else 1 if mode in ("stale", "conflict") else None
                row = db.execute("SELECT request_id,request_digest,binding_revision,action,message FROM review_requests "
                    "WHERE request_revision=COALESCE(?, (SELECT MAX(request_revision) FROM review_requests))", (revision,)).fetchone()
                command = "key-" + row[0] if mode != "stale" else "new-stale-key"
                selected = action if mode == "decide" else row[3] if mode == "duplicate" else "approve"
                message = None if selected == "approve" else "Explain or improve the old Story"
                try:
                    result = asdict(runtime.respond(eid, *row[:3], command, selected, row[4] if mode == "duplicate" else message))
                except ValueError as error:
                    if mode not in ("stale", "conflict"):
                        raise
                    result = {"rejected": str(error)}
                else:
                    assert mode not in ("stale", "conflict"), "Stale/conflicting decision was accepted"
                print(json.dumps(result), flush=True)
                return
            if mode == "resume":
                original = saver.aput_writes

                async def after_resume(*args, **kwargs):
                    result = await original(*args, **kwargs)
                    if any(channel == "__resume__" for channel, _ in args[1]):
                        parked(mode)
                    return result

                with patch.object(saver, "aput_writes", after_resume):
                    await runtime.run()
                raise AssertionError("Historical persisted resume boundary not reached")
            if mode == "approval_commit":
                from backend import story_graph
                original = story_graph.apply_story_decision

                def after_apply(*args):
                    original(*args)
                    parked(mode)

                with patch.object(story_graph, "apply_story_decision", after_apply):
                    await runtime.run()
                raise AssertionError("Historical approval boundary not reached")
            processed = await runtime.run() if mode in ("recover", "offline") else None
            saved = await saver.aget_tuple({"configurable": {"thread_id": eid}})
            data = snapshot(runtime, saved)
            data.update(processed=processed, requests=requests,
                identity=db.execute("SELECT graph_id,graph_version,graph_digest,owner_config FROM executions").fetchone(),
                wardrobe_count=db.execute("SELECT COUNT(*) FROM wardrobe_operations").fetchone()[0],
                checkpoint_channels=sorted(saved.checkpoint["channel_versions"]))
            print(json.dumps(data), flush=True)


class HistoricalLiveProcessTests(ProcessStoryTest):
    child_script = Path(__file__)

    def test_pre_w4_live_v1_checkpoint_resume_clarify_revise_duplicate_stale_approve_end(self):
        before = self.complete("setup")
        identity = before["identity"]
        self.assertEqual(identity[:3], ["kinodel.live-story", "1", sha256_digest(
            b"kinodel.live-story.v1:OpenRouter+frozen-storytell+text-input>storytell>story_prepare_review>story_wait>story_apply>END|clarify+revise>storytell")])
        self.assertEqual(json.loads(identity[3])["adapter_version"], "1")
        self.assertNotIn("selected_characters", json.loads(identity[3]))
        self.assertEqual(before["refs"][0]["schema_version"], "1")
        self.assertNotIn("generated_characters", before["stories"][0])
        self.assertFalse(any("wardrobe" in channel for channel in before["checkpoint_channels"]))
        self.assertEqual(self.complete("offline"), dict(before, processed=0, requests=[]))
        for revision, action in enumerate(("clarify", "revise"), 1):
            decision = self.complete("decide", action)
            self.kill_at("resume")
            crashed = self.complete("inspect")
            old = crashed["reviews"][-1]
            self.assertIn([old[6], "__resume__", [decision["decision_id"]]], crashed["pending"])
            recovered = self.complete("recover")
            self.assertEqual(recovered["processed"], 1)
            self.assertEqual(recovered["identity"], identity)
            self.assertEqual(recovered["wardrobe_count"], 0)
            self.assertIsNone(recovered["outcome"])
            self.assertEqual(len(recovered["reviews"]), revision + 1)
            new = recovered["reviews"][-1]
            self.assertEqual(new[8:10], [None, None])  # Old decision did not answer the next wait.
            self.assertNotEqual(new[6:8], old[6:8])
            self.assertEqual(new[10], old[0])
            self.assertEqual(recovered["refs"][:len(before["refs"])], before["refs"])
            self.assertEqual(len(recovered["refs"]), 1 if action == "clarify" else 2)
            self.assertEqual(len(recovered["requests"]), 1)
            request = recovered["requests"][0]
            self.assertEqual(request["model"], "test/model")
            self.assertEqual(request["messages"][0]["content"], OLD_PROMPT)
            task = json.loads(request["messages"][1]["content"])
            self.assertEqual(task["action"], action)
            self.assertEqual(task["context"]["projection_id"], "story-text.v1")
            self.assertEqual(task["previous_story"], before["stories"][-1])
            self.assertEqual(self.complete("duplicate", str(revision)), decision)
            self.assertIn("rejected", self.complete("stale"))
            self.assertIn("rejected", self.complete("conflict"))
            self.assertEqual(self.complete("offline"), dict(recovered, processed=0, requests=[]))
            before = recovered
        approval = self.complete("decide", "approve")
        self.kill_at("approval_commit")
        crashed = self.complete("inspect")
        self.assertNotIn("approved_story", crashed["state"])
        self.assertEqual(crashed["outcome"], ["completed", crashed["reviews"][-1][0], before["current_ref"]["artifact_id"]])
        completed = self.complete("offline")
        self.assertEqual(completed["processed"], 1)
        for key in ("identity", "refs", "stories", "reviews", "operations", "checkpoint", "state", "pending", "outcome"):
            self.assertEqual(completed[key], crashed[key], key)
        self.assertEqual(completed["wardrobe_count"], 0)
        self.assertTrue(all(work[2] == "completed" for work in completed["work"]))
        self.assertEqual(self.complete("duplicate", "3"), approval)
        self.assertEqual(self.complete("offline"), dict(completed, processed=0))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        asyncio.run(child(Path(sys.argv[2]), sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None))
    else:
        unittest.main()
