"""W5: kill the real Wardrobe graph/lock/saver owner, then recover in a fresh process."""

import asyncio
from contextlib import nullcontext
from dataclasses import asdict
from functools import partial
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from story_process_support import ProcessStoryTest, parked, snapshot
import httpx

from backend import story_graph, wardrobe_store
from backend.api import fixture_story
from backend.domain import StoryTextInputV1, sha256_digest
from backend.story_control import open_story_runtime
from tests.test_story_cast import draft
from tests.test_wardrobe_openrouter import capability, envelope
from tests.test_story_wardrobe_runtime import five_unit_plan


async def child(root, mode, action=None):
    requests = []
    entered = asyncio.Event()

    async def respond(request):
        # Only mock HTTP; preparation, validation, business commits and saver are real.
        if mode in ("inspect", "offline"):
            raise AssertionError("Read/committed recovery attempted HTTP")
        requests.append({"method": request.method, "body": request.content.decode()})
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{**capability(), "id": "test/model"}]})
        payload = json.loads(request.content)
        if payload["response_format"]["json_schema"]["name"] != "wardrobe_result":
            raise AssertionError("Recovered route repeated committed Story generation")
        if mode == "cancel_http":
            entered.set()
            await asyncio.Event().wait()
        if mode == "repair":
            return httpx.Response(200, json={"choices": []})
        result = {"status": "ready", "plan": five_unit_plan(), "explanation": None}
        return httpx.Response(200, json=envelope(result))

    async def setup_response(request):
        requests.append({"method": request.method, "body": request.content.decode()})
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{**capability(), "id": "test/model"}]})
        return httpx.Response(200, json=envelope({"status": "ready", "story": draft(), "explanation": None}))

    transport = httpx.MockTransport(setup_response if mode == "setup" else respond)
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret", "LLM_MODEL": "test/model"}), \
            patch("backend.openrouter_client.httpx.AsyncClient", partial(httpx.AsyncClient, transport=transport)):
        async with open_story_runtime(root, fixture_story, character_root=root / "unused-library") as runtime:
            db, saver = runtime.db, runtime.saver
            if mode == "setup":
                await runtime.start_wardrobe(str(uuid4()), "start", ["s1"],
                    StoryTextInputV1(user_vibe="A robot joke", subjects=[], shot_duration_ms=5000))
                await runtime.run()
            eid = db.execute("SELECT execution_id FROM executions WHERE client_key='start'").fetchone()[0]
            if mode in ("decide", "duplicate"):
                row = db.execute("SELECT request_id,request_digest,binding_revision FROM review_requests").fetchone()
                print(json.dumps(asdict(runtime.respond(eid, *row, "approve", "approve", None))), flush=True)
                return
            processed = None
            if mode in ("recover", "offline"):
                # Retry/replay must not select a current model/catalog/prompt.
                prepared = db.execute("SELECT 1 FROM wardrobe_operations").fetchone() is not None
                with patch.dict(os.environ, {"LLM_MODEL": "changed/model"}) if prepared else nullcontext(), \
                        patch("pathlib.Path.read_text", side_effect=AssertionError("Recovery read current prompt")) if prepared else nullcontext():
                    processed = await runtime.run()
            elif mode in ("resume", "terminal_writes", "terminal_checkpoint", "cancel_checkpoint"):
                name = "aput" if mode == "terminal_checkpoint" else "aput_writes"
                original = getattr(saver, name)
                original_writes = saver.aput_writes
                task_writes_saved = asyncio.Event()

                async def after_task_writes(*args, **kwargs):
                    result = await original_writes(*args, **kwargs)
                    if any(channel == "wardrobe_plan" for channel, _ in args[1]):
                        task_writes_saved.set()
                    return result

                async def at_checkpoint(*args, **kwargs):
                    if mode == "cancel_checkpoint" and any(channel == "wardrobe_activation" for channel, _ in args[1]):
                        entered.set()  # Apply committed, but its task delta is not saved.
                        await asyncio.Event().wait()
                    if mode == "terminal_writes" and db.execute("SELECT 1 FROM execution_outcomes").fetchone():
                        parked(mode)  # Terminal committed; even Wardrobe task writes are absent.
                    if mode == "terminal_checkpoint" and db.execute("SELECT 1 FROM execution_outcomes").fetchone():
                        await asyncio.wait_for(task_writes_saved.wait(), 5)
                        parked(mode)  # Task writes persisted; final super-step checkpoint is absent.
                    result = await original(*args, **kwargs)
                    if mode == "resume" and any(channel == "__resume__" for channel, _ in args[1]):
                        parked(mode)  # Exact resume value actually persisted, before apply.
                    return result

                with patch.object(saver, name, at_checkpoint), \
                        patch.object(saver, "aput_writes", after_task_writes) if mode == "terminal_checkpoint" else nullcontext():
                    if mode == "cancel_checkpoint":
                        running = asyncio.create_task(runtime.run())
                        await asyncio.wait_for(entered.wait(), 10)
                        assert not running.done()
                        runtime.cancel(eid, "cancel")
                        parked(mode)  # Kill without graceful graph/saver/task cleanup.
                    await runtime.run()
                raise AssertionError(mode + " boundary not reached")
            elif mode == "cancel_http":
                running = asyncio.create_task(runtime.run())
                await asyncio.wait_for(entered.wait(), 10)
                assert not running.done()
                runtime.cancel(eid, "cancel")
                parked(mode)
            elif mode not in ("setup", "inspect"):
                target, name = ((story_graph, "apply_story_decision") if mode == "apply" else
                                (wardrobe_store, {"attempt": "reserve_wardrobe_attempt", "publish": "_publish",
                                                  "plan": "commit_wardrobe_operation", "repair": "record_wardrobe_invalid"}[mode]))
                original = getattr(target, name)

                def at_commit(*args, **kwargs):
                    original(*args, **kwargs)
                    parked(mode)  # Actual transaction/publication finished, no node return.

                with patch.object(target, name, at_commit):
                    await runtime.run()
                raise AssertionError(mode + " boundary not reached")

            saved = await saver.aget_tuple({"configurable": {"thread_id": eid}})
            data = snapshot(runtime, saved)
            columns = "operation_id,input_digest,prepared_inputs,owner_config,repair_request,owner_attempts,owner_repairs,candidate_body,candidate_digest,artifact_id,next_activation"
            cursor = db.execute(f"SELECT {columns} FROM wardrobe_operations")
            row = cursor.fetchone()
            record = dict(zip(columns.split(","), row)) if row else None
            data.update(wardrobe=record, requests=requests, processed=processed,
                plan_binding=db.execute("SELECT artifact_id,binding_revision FROM execution_bindings WHERE slot='wardrobe_plan'").fetchone(),
                wardrobe_count=db.execute("SELECT COUNT(*) FROM wardrobe_operations").fetchone()[0],
                plan_count=db.execute("SELECT COUNT(*) FROM artifacts WHERE schema_id='visual_anchor_plan'").fetchone()[0],
                plan=None, published_digest=None)
            if record and record["candidate_body"]:
                pins = json.loads(record["prepared_inputs"])
                path = wardrobe_store._destination(db, pins["story_ref"]["project_id"], pins["planned_artifact_id"], record["candidate_digest"])
                if path.exists():
                    data["published_digest"] = sha256_digest(path.read_bytes())
            if data["plan_binding"]:
                ref, plan = wardrobe_store.read_wardrobe_plan(db, eid)
                data["plan"] = {"ref": ref.model_dump(mode="json"), "body": plan.model_dump(mode="json")}
            print(json.dumps(data), flush=True)


class StoryWardrobeProcessTests(ProcessStoryTest):
    child_script = Path(__file__)

    def check_boundary(self, mode):
        before = self.complete("setup")
        decision = self.complete("decide")
        self.kill_at(mode)
        crashed = self.complete("inspect")
        review = crashed["reviews"][0]
        self.assertEqual(review[:8], before["reviews"][0][:8])
        self.assertEqual(review[8], decision["decision_id"])
        self.assertEqual(crashed["work"][-1], ["resume", review[0], "claimed"])
        self.assertEqual(len(crashed["refs"]), 1)
        self.assertEqual(crashed["refs"][0]["schema_version"], "2")
        terminal = mode.startswith("terminal_")
        self.assertEqual(crashed["outcome"] is not None, terminal)
        self.assertNotIn("wardrobe_plan", crashed["state"])
        if mode == "resume":
            self.assertIsNone(review[9])
            self.assertIn([review[6], "__resume__", [decision["decision_id"]]], crashed["pending"])
            self.assertIsNone(crashed["wardrobe"])
        else:
            self.assertIsNotNone(review[9])
        if mode == "apply":
            self.assertNotIn("wardrobe_activation", crashed["state"])
            self.assertIsNone(crashed["wardrobe"])
        if mode in ("attempt", "repair"):
            self.assertIsNone(crashed["wardrobe"]["candidate_body"])
            self.assertIsNone(crashed["plan_binding"])
        if mode == "publish":
            self.assertEqual(crashed["published_digest"], crashed["wardrobe"]["candidate_digest"])
            self.assertIsNone(crashed["wardrobe"]["artifact_id"])
            self.assertIsNone(crashed["plan_binding"])
        if terminal:
            self.assertEqual(any(channel == "wardrobe_plan" for _, channel, _ in crashed["pending"]),
                             mode == "terminal_checkpoint")
        recovered = self.complete("offline" if mode in ("publish", "plan") or terminal else "recover")
        self.assertEqual(recovered["processed"], 1)
        for key in ("execution", "project", "refs", "stories", "binding", "reviews", "operations"):
            if key == "reviews" and mode == "resume":
                self.assertEqual(recovered[key][0][:9], crashed[key][0][:9])
                self.assertIsNotNone(recovered[key][0][9])
            else:
                self.assertEqual(recovered[key], crashed[key], key)
        self.assertEqual(recovered["work"][-1], ["resume", review[0], "completed"])
        self.assertEqual(len(recovered["reviews"]), 1)
        self.assertEqual((recovered["wardrobe_count"], recovered["plan_count"]), (1, 1))
        record = recovered["wardrobe"]
        self.assertEqual((record["owner_attempts"], record["owner_repairs"]),
                         (2 if mode in ("attempt", "repair") else 1, int(mode == "repair")))
        if crashed["wardrobe"]:
            for key in ("operation_id", "input_digest", "prepared_inputs", "owner_config", "repair_request"):
                self.assertEqual(record[key], crashed["wardrobe"][key], key)
        if mode in ("publish", "plan") or terminal:
            self.assertEqual(record["candidate_body"], crashed["wardrobe"]["candidate_body"])
            self.assertEqual(recovered["requests"], [])
        else:
            posts = [r["body"] for r in recovered["requests"] if r["method"] == "POST"]
            self.assertEqual(len(posts), 1)
            if mode in ("attempt", "repair"):
                expected = record["repair_request"] if mode == "repair" else json.loads(record["owner_config"])["base_request"]
                self.assertEqual(posts[0], expected)
        ref = recovered["plan"]["ref"]
        self.assertEqual(ref["schema_version"], "2")
        self.assertEqual(len(recovered["plan"]["body"]["batch_prompt"]), 5)
        self.assertEqual(recovered["plan"]["body"]["narrative_ref"], before["current_ref"])
        self.assertEqual(recovered["plan_binding"], [ref["artifact_id"], 1])
        self.assertEqual(recovered["outcome"], ["completed", ref["operation_id"], ref["artifact_id"]])
        if mode == "plan" or terminal:
            self.assertEqual(recovered["plan"], crashed["plan"])
        if terminal:
            for key in ("checkpoint", "state", "pending", "outcome"):
                self.assertEqual(recovered[key], crashed[key], key)  # Outcome wins; no graph END replay.
        self.assertEqual(self.complete("duplicate"), decision)
        self.assertEqual(self.complete("offline"), dict(recovered, processed=0, requests=[]))

    def test_persisted_approval_resume_before_apply(self):
        self.check_boundary("resume")

    def test_nonterminal_approval_commit_before_checkpoint(self):
        self.check_boundary("apply")

    def test_reserved_attempt_before_post(self):
        self.check_boundary("attempt")

    def test_malformed_repair_selection_before_second_attempt(self):
        self.check_boundary("repair")

    def test_published_plan_before_database_commit(self):
        self.check_boundary("publish")

    def test_plan_commit_before_terminal_and_checkpoint(self):
        self.check_boundary("plan")

    def test_terminal_commit_before_task_writes(self):
        self.check_boundary("terminal_writes")

    def test_terminal_commit_pending_writes_before_final_checkpoint(self):
        self.check_boundary("terminal_checkpoint")

    def test_cancel_suspended_http_or_checkpoint_survives_process_death(self):
        parent = self.root
        for mode in ("cancel_http", "cancel_checkpoint"):
            with self.subTest(mode=mode):
                self.root = parent / mode
                before = self.complete("setup")
                self.complete("decide")
                self.kill_at(mode)
                crashed = self.complete("inspect")
                self.assertIsNone(crashed["outcome"])
                self.assertIsNone(crashed["plan_binding"])
                self.assertIsNotNone(crashed["reviews"][0][9])
                if mode == "cancel_http":
                    self.assertEqual(crashed["wardrobe"]["owner_attempts"], 1)
                    self.assertIsNone(crashed["wardrobe"]["candidate_body"])
                else:
                    self.assertIsNone(crashed["wardrobe"])
                self.assertEqual(crashed["work"][-1], ["cancel", "cancel", "pending"])
                recovered = self.complete("offline")
                for key in ("refs", "stories", "reviews", "wardrobe", "plan_binding", "checkpoint", "state", "pending"):
                    self.assertEqual(recovered[key], crashed[key], key)
                self.assertEqual(recovered["refs"], before["refs"])
                self.assertEqual(recovered["work"][-2][2], "obsolete")
                self.assertEqual(recovered["work"][-1][2], "completed")
                self.assertEqual(recovered["outcome"], ["cancelled", "cancel", None])
                self.assertEqual(self.complete("offline"), dict(recovered, processed=0))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        asyncio.run(child(Path(sys.argv[2]), sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None))
    else:
        unittest.main()
