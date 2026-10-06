"""New frozen route only; real SQLite checkpoints/work, mocked provider HTTP."""

from functools import partial
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx

from backend import story_graph, wardrobe_store
from backend.database import open_database
from backend.domain import OwnerResponseV1, StoryTextInputV1, StorytellResultV2, canonical_json, sha256_digest
from backend.openrouter import StoryOwnerConfigV2
from backend.review_store import accept_story_decision, apply_story_decision
from backend.saver import open_saver
from backend.story_control import cancel_story
from backend.story_runner import run_story_work
from backend.story_start import _payload_digest, load_test_story_start
from backend.story_store import read_story
from tests.test_story_cast import draft
from tests.test_story_runner import produce_story
from tests.test_wardrobe_openrouter import capability, envelope


class StoryWardrobeRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel wardrobe runtime ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "data"
        self.library = Path(temporary.name) / "characters"
        self.project, self.execution = str(uuid4()), str(uuid4())
        self.requests = []
        environment = patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret", "LLM_MODEL": "test/model"})
        environment.start()
        self.addCleanup(environment.stop)

    def seed_start(self, db):
        # No public start exposure in this slice; create a NEW exact frozen execution.
        prompt = "Frozen Story instruction"
        config = StoryOwnerConfigV2(adapter_version="2", model="test/model",
            brief=StoryTextInputV1(user_vibe="A robot joke", subjects=[], shot_duration_ms=5000),
            selected_characters=[], system_prompt=prompt, result_schema=StorytellResultV2.model_json_schema(),
            clarification_schema=OwnerResponseV1.model_json_schema(), prompt_digest=sha256_digest(prompt.encode()),
            timeout_seconds=60, max_tokens=8192, max_attempts=2, repair_limit=1, reasoning_effort="low")
        frozen = canonical_json(config).decode()
        digest = _payload_digest(config.brief.user_vibe, ["s1"], frozen)
        db.execute("INSERT INTO executions (execution_id,project_id,input_message,shot_ids,client_key,start_digest,"
                   "graph_id,graph_version,graph_digest,owner_config) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (self.execution, self.project, config.brief.user_vibe, '["s1"]', "new-route", digest,
                    wardrobe_store.GRAPH_ID, wardrobe_store.GRAPH_VERSION, wardrobe_store.GRAPH_DIGEST, frozen))
        db.execute("INSERT INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,status) "
                   "VALUES (?,?, 'start', ?, ?, 'pending')", (str(uuid4()), self.execution, self.execution, digest))

    def transport(self, wardrobe_output=None, before_wardrobe=None):
        def respond(request):
            self.requests.append(request)
            if request.method == "GET":
                return httpx.Response(200, json={"data": [{**capability(), "id": "test/model"}]})
            payload = json.loads(request.content)
            if payload["response_format"]["json_schema"]["name"] != "wardrobe_result":
                if json.loads(payload["messages"][1]["content"])["action"] == "clarify":
                    return httpx.Response(200, json=envelope({"status": "clarified", "explanation": "It is a joke."}))
                return httpx.Response(200, json=envelope({"status": "ready", "story": draft(), "explanation": None}))
            if before_wardrobe:
                before_wardrobe(request)
            if callable(wardrobe_output):
                return wardrobe_output(request)
            # A reusable fixture draft, with its subject changed to this execution's generated cast.
            result = wardrobe_output or json.loads(envelope()["choices"][0]["message"]["content"])
            if result.get("plan"):
                for unit in result["plan"]["units"]:
                    unit["subject_ids"] = ["comedian"] if unit["role"] != "background" else []
            return httpx.Response(200, json=envelope(result))
        return patch("backend.openrouter_client.httpx.AsyncClient",
                     partial(httpx.AsyncClient, transport=httpx.MockTransport(respond)))

    async def drain(self, db, saver):
        return await run_story_work(db, saver, produce_story, character_root=self.library)

    async def start_and_approve(self, db, saver):
        self.seed_start(db)
        await self.drain(db, saver)
        request = db.execute("SELECT request_id,request_digest,binding_revision FROM review_requests").fetchone()
        decision = accept_story_decision(db, self.execution, request[0], request[1], request[2], "approve", "approve", None)
        return request, decision

    async def test_loader_accepts_only_exact_new_identity(self):
        with open_database(self.root) as db:
            self.seed_start(db)
            receipt, initial = load_test_story_start(db, self.execution)
            self.assertEqual(receipt.execution_id, self.execution)
            self.assertEqual(initial, story_graph.initial_story_state(self.project, self.execution, live=True))
            for column, value in (("graph_digest", sha256_digest(b"wrong")), ("graph_version", "2")):
                original = db.execute(f"SELECT {column} FROM executions").fetchone()[0]
                db.execute(f"UPDATE executions SET {column}=?", (value,))
                with self.assertRaises(ValueError):
                    load_test_story_start(db, self.execution)
                db.execute(f"UPDATE executions SET {column}=?", (original,))

    async def test_approval_handoff_is_nonterminal_and_atomic(self):
        with open_database(self.root) as db, self.transport():
            async with open_saver(self.root, db) as saver:
                request, decision = await self.start_and_approve(db, saver)
                db.execute("CREATE TEMP TRIGGER fail_handoff BEFORE UPDATE OF applied_activation ON review_requests "
                           "BEGIN SELECT RAISE(ABORT, 'handoff gap'); END")
                with self.assertRaises(sqlite3.IntegrityError):
                    apply_story_decision(db, self.execution, request[0], decision.decision_id)
                self.assertEqual(db.execute("SELECT applied_activation FROM review_requests").fetchone(), (None,))
                db.execute("DROP TRIGGER fail_handoff")
                activation = apply_story_decision(db, self.execution, request[0], decision.decision_id)
                self.assertEqual(apply_story_decision(db, self.execution, request[0], decision.decision_id), activation)
                self.assertEqual(db.execute("SELECT * FROM execution_outcomes").fetchall(), [])
                self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(), ("pending",))
                self.assertEqual(wardrobe_store.wardrobe_authority(db, self.execution, request[0])[0].activation_id, activation)

    async def test_exact_plan_completes_before_end_with_resume_work_held(self):
        with open_database(self.root) as db, self.transport():
            async with open_saver(self.root, db) as saver:
                request, decision = await self.start_and_approve(db, saver)
                def check_claim(_):
                    self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(), ("claimed",))
                    self.assertEqual(db.execute("SELECT * FROM execution_outcomes").fetchall(), [])
                    self.assertIsNotNone(db.execute("SELECT applied_activation FROM review_requests").fetchone()[0])
                with self.transport(before_wardrobe=check_claim):
                    self.assertEqual(await self.drain(db, saver), 1)
                ref, plan = wardrobe_store.read_wardrobe_plan(db, self.execution)
                self.assertEqual(plan.narrative_ref, read_story(db, self.execution)[0])
                self.assertEqual(db.execute("SELECT outcome,source_id,subject_artifact_id FROM execution_outcomes").fetchone(),
                                 ("completed", ref.operation_id, ref.artifact_id))
                self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(), ("completed",))
                snapshot = await story_graph.build_story_graph(db, saver, produce_story, wardrobe=True, character_root=self.library).aget_state({"configurable": {"thread_id": self.execution}})
                self.assertEqual(snapshot.next, ())
                self.assertEqual(snapshot.values["wardrobe_plan"], ref.model_dump(mode="json"))
                self.assertEqual(snapshot.values["review_ref"]["request_id"], request[0])
                self.assertEqual(await self.drain(db, saver), 0)

    async def test_committed_nonready_is_durable_block_not_success(self):
        for status in ("needs_input", "out_of_scope"):
            self.root = self.root.with_name(status)
            self.execution = str(uuid4())
            with self.subTest(status=status), open_database(self.root) as db, self.transport():
                async with open_saver(self.root, db) as saver:
                    _, decision = await self.start_and_approve(db, saver)
                    with self.transport({"status": status, "plan": None, "explanation": "New run needs direction"}):
                        self.assertEqual(await self.drain(db, saver), 1)
                    self.assertEqual(db.execute("SELECT status,blocked_reason FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(),
                                     ("blocked", f"wardrobe_{status}"))
                    self.assertIsNotNone(db.execute("SELECT next_activation FROM wardrobe_operations").fetchone()[0])
                    self.assertEqual(db.execute("SELECT * FROM execution_outcomes").fetchall(), [])
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_bindings WHERE slot='wardrobe_plan'").fetchone(), (0,))
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    with patch("backend.wardrobe_operation.produce_wardrobe_operation", side_effect=AssertionError("Blocked run invoked")):
                        self.assertEqual(await self.drain(db, saver), 0)
                    cancel_story(db, self.execution, "cancel")
                    await self.drain(db, saver)
                    self.assertEqual(db.execute("SELECT outcome FROM execution_outcomes").fetchone(), ("cancelled",))

    async def test_transport_block_keeps_hard_budget_on_reopen(self):
        with open_database(self.root) as db, self.transport():
            async with open_saver(self.root, db) as saver:
                _, decision = await self.start_and_approve(db, saver)
                with self.transport(lambda _: httpx.Response(503)):
                    await self.drain(db, saver)
                self.assertEqual(db.execute("SELECT status,blocked_reason FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(),
                                 ("blocked", "wardrobe_unavailable"))
                frozen = db.execute("SELECT owner_config FROM wardrobe_operations").fetchone()[0]
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                self.assertEqual(await self.drain(db, saver), 0)
                # Test-only requeue; authorization/OCC control is the next task's layer.
                db.execute("UPDATE execution_work SET status='pending',blocked_reason=NULL WHERE work_id=?", (decision.work_id,))
                with self.transport(lambda _: httpx.Response(503)):
                    await self.drain(db, saver)
                self.assertEqual(db.execute("SELECT owner_attempts,owner_config FROM wardrobe_operations").fetchone(), (2, frozen))
                self.assertEqual(db.execute("SELECT blocked_reason FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(), ("wardrobe_exhausted",))
                db.execute("UPDATE execution_work SET status='pending',blocked_reason=NULL WHERE work_id=?", (decision.work_id,))
                with self.transport():
                    await self.drain(db, saver)
                self.assertEqual(db.execute("SELECT * FROM execution_outcomes").fetchall(), [])
                posts = [r for r in self.requests if r.method == "POST" and b'wardrobe_result' in r.content]
                self.assertEqual(len(posts), 2)
                self.assertEqual(posts[0].content, posts[1].content)

    async def test_recovery_after_apply_and_plan_commit_does_not_recall_committed_work(self):
        for boundary in ("apply", "plan"):
            self.root = self.root.with_name(boundary)
            self.execution = str(uuid4())
            with self.subTest(boundary=boundary), open_database(self.root) as db, self.transport():
                async with open_saver(self.root, db) as saver:
                    _, decision = await self.start_and_approve(db, saver)
                    original = apply_story_decision if boundary == "apply" else wardrobe_store.commit_wardrobe_operation
                    def crash(*args):
                        original(*args)
                        raise RuntimeError("after business commit")
                    target = "backend.story_graph.apply_story_decision" if boundary == "apply" else "backend.wardrobe_store.commit_wardrobe_operation"
                    with patch(target, side_effect=crash), self.assertRaisesRegex(RuntimeError, "business commit"):
                        await self.drain(db, saver)
                    self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(), ("claimed",))
                    self.assertEqual(db.execute("SELECT * FROM execution_outcomes").fetchall(), [])
            with open_database(self.root) as db, self.transport():
                async with open_saver(self.root, db) as saver:
                    before = len(self.requests)
                    await self.drain(db, saver)
                    if boundary == "plan":
                        self.assertEqual(len(self.requests), before)
                    self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(), ("completed",))
                    self.assertEqual(db.execute("SELECT outcome FROM execution_outcomes").fetchone(), ("completed",))
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM wardrobe_operations").fetchone(), (1,))

    async def test_terminal_commit_without_checkpoint_settles_without_provider(self):
        with open_database(self.root) as db, self.transport():
            async with open_saver(self.root, db) as saver:
                _, decision = await self.start_and_approve(db, saver)
                original = saver.aput_writes
                async def crash_after_terminal(*args, **kwargs):
                    if db.execute("SELECT 1 FROM execution_outcomes").fetchone():
                        raise RuntimeError("terminal before checkpoint")
                    return await original(*args, **kwargs)
                with patch.object(saver, "aput_writes", side_effect=crash_after_terminal), self.assertRaisesRegex(RuntimeError, "terminal before"):
                    await self.drain(db, saver)
                self.assertEqual(db.execute("SELECT outcome FROM execution_outcomes").fetchone(), ("completed",))
                self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(), ("claimed",))
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                with patch("backend.wardrobe_operation.produce_wardrobe_operation", side_effect=AssertionError("Terminal replay invoked")):
                    self.assertEqual(await self.drain(db, saver), 1)
                self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(), ("completed",))

    async def test_empty_end_has_no_story_only_completion_fallback(self):
        with open_database(self.root) as db, self.transport():
            async with open_saver(self.root, db) as saver:
                request, decision = await self.start_and_approve(db, saver)
                def crash(*args):
                    apply_story_decision(*args)
                    raise RuntimeError("after apply")
                with patch("backend.story_graph.apply_story_decision", side_effect=crash), self.assertRaises(RuntimeError):
                    await self.drain(db, saver)
                graph = story_graph.build_story_graph(db, saver, produce_story, wardrobe=True)
                config = {"configurable": {"thread_id": self.execution}}
                # A corrupt/operator-edited checkpoint is not permission to complete production.
                await graph.aupdate_state(config, {"approved_story": read_story(db, self.execution)[0].model_dump(mode="json"),
                    "decision_id": "", "wardrobe_activation": db.execute("SELECT applied_activation FROM review_requests").fetchone()[0]}, as_node="wardrobe")
                self.assertEqual((await graph.aget_state(config)).next, ())
                with self.assertRaisesRegex(ValueError, "No committed Wardrobe plan"):
                    await self.drain(db, saver)
                self.assertEqual(db.execute("SELECT * FROM execution_outcomes").fetchall(), [])
                self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(), ("blocked",))

    async def test_config_invalid_output_and_late_cancel_are_non_success(self):
        for case, expected in (("config", "wardrobe_invalid"), ("invalid", "wardrobe_invalid_output"), ("cancel", None)):
            self.root = self.root.with_name(case)
            self.execution = str(uuid4())
            with self.subTest(case=case), open_database(self.root) as db, self.transport():
                async with open_saver(self.root, db) as saver:
                    _, decision = await self.start_and_approve(db, saver)
                    if case == "config":
                        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
                            await self.drain(db, saver)
                    elif case == "invalid":
                        with self.transport(lambda _: httpx.Response(200, json={"choices": []})):
                            await self.drain(db, saver)
                        self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs FROM wardrobe_operations").fetchone(), (2, 1))
                    else:
                        commit = wardrobe_store.commit_wardrobe_operation
                        def cancel_after_plan(*args):
                            result = commit(*args)
                            cancel_story(db, self.execution, "late-cancel")
                            return result
                        with patch.object(wardrobe_store, "commit_wardrobe_operation", side_effect=cancel_after_plan):
                            await self.drain(db, saver)
                        self.assertEqual(db.execute("SELECT outcome FROM execution_outcomes").fetchone(), ("cancelled",))
                        self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_bindings WHERE slot='wardrobe_plan'").fetchone(), (1,))
                    if expected:
                        self.assertEqual(db.execute("SELECT status,blocked_reason FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(), ("blocked", expected))
                        self.assertEqual(db.execute("SELECT * FROM execution_outcomes").fetchall(), [])

    async def test_committed_plan_integrity_failure_on_recovery_blocks(self):
        with open_database(self.root) as db, self.transport():
            async with open_saver(self.root, db) as saver:
                _, decision = await self.start_and_approve(db, saver)
                commit = wardrobe_store.commit_wardrobe_operation
                def crash(*args):
                    ref, _ = commit(*args)
                    self.plan_path = wardrobe_store._destination(db, self.project, ref.artifact_id, ref.digest)
                    raise RuntimeError("plan committed")
                with patch.object(wardrobe_store, "commit_wardrobe_operation", side_effect=crash), self.assertRaises(RuntimeError):
                    await self.drain(db, saver)
        self.plan_path.unlink()
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                with patch("backend.openrouter_wardrobe.complete_wardrobe", side_effect=AssertionError("Corrupt committed plan recalled")):
                    await self.drain(db, saver)
                self.assertEqual(db.execute("SELECT status,blocked_reason FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(), ("blocked", "wardrobe_invalid"))
                self.assertEqual(db.execute("SELECT * FROM execution_outcomes").fetchall(), [])

    async def test_transport_retry_can_finish_same_approval_without_budget_expansion(self):
        with open_database(self.root) as db, self.transport():
            async with open_saver(self.root, db) as saver:
                request, decision = await self.start_and_approve(db, saver)
                with self.transport(lambda _: httpx.Response(503)):
                    await self.drain(db, saver)
        with open_database(self.root) as db, self.transport():
            async with open_saver(self.root, db) as saver:
                db.execute("UPDATE execution_work SET status='pending',blocked_reason=NULL WHERE work_id=?", (decision.work_id,))
                await self.drain(db, saver)
                self.assertEqual(db.execute("SELECT owner_attempts,approval_request_id FROM wardrobe_operations").fetchone(), (2, request[0]))
                self.assertEqual(db.execute("SELECT outcome FROM execution_outcomes").fetchone(), ("completed",))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM review_requests").fetchone(), (1,))

    async def test_new_route_clarify_revise_then_approve_uses_exact_new_story(self):
        with open_database(self.root) as db, self.transport():
            async with open_saver(self.root, db) as saver:
                self.seed_start(db)
                await self.drain(db, saver)
                for action in ("clarify", "revise"):
                    request = db.execute("SELECT request_id,request_digest,binding_revision FROM review_requests ORDER BY request_revision DESC LIMIT 1").fetchone()
                    decision = accept_story_decision(db, self.execution, request[0], request[1], request[2], action, action, "Explain or improve")
                    await self.drain(db, saver)
                    self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(), ("completed",))
                    self.assertEqual(db.execute("SELECT * FROM wardrobe_operations").fetchall(), [])
                    self.assertEqual(db.execute("SELECT * FROM execution_outcomes").fetchall(), [])
                request = db.execute("SELECT request_id,request_digest,binding_revision FROM review_requests ORDER BY request_revision DESC LIMIT 1").fetchone()
                self.assertEqual(request[2], 2)
                accept_story_decision(db, self.execution, request[0], request[1], request[2], "approve", "approve", None)
                await self.drain(db, saver)
                self.assertEqual(wardrobe_store.read_wardrobe_plan(db, self.execution)[1].narrative_ref, read_story(db, self.execution)[0])
                self.assertEqual(db.execute("SELECT approval_request_id FROM wardrobe_operations").fetchone(), (request[0],))

    async def test_terminal_recovery_rejects_missing_plan_and_corrupt_resume(self):
        for case in ("missing", "resume"):
            self.root = self.root.with_name(case)
            self.execution = str(uuid4())
            with self.subTest(case=case), open_database(self.root) as db, self.transport():
                async with open_saver(self.root, db) as saver:
                    _, decision = await self.start_and_approve(db, saver)
                    original = saver.aput_writes
                    async def crash(*args, **kwargs):
                        if db.execute("SELECT 1 FROM execution_outcomes").fetchone():
                            raise RuntimeError("terminal before checkpoint")
                        return await original(*args, **kwargs)
                    with patch.object(saver, "aput_writes", side_effect=crash), self.assertRaises(RuntimeError):
                        await self.drain(db, saver)
                    ref = wardrobe_store.read_wardrobe_plan(db, self.execution)[0]
                    outcome = db.execute("SELECT * FROM execution_outcomes").fetchone()
                    if case == "missing":
                        wardrobe_store._destination(db, self.project, ref.artifact_id, ref.digest).unlink()
                    else:
                        db.execute("UPDATE execution_work SET resume_ref='wrong' WHERE work_id=?", (decision.work_id,))
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    try:
                        await self.drain(db, saver)
                    except (ValueError, FileNotFoundError):
                        pass
                    self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(), ("blocked",))
                    self.assertEqual(db.execute("SELECT * FROM execution_outcomes").fetchone(), outcome)

    async def test_wrong_returned_transition_cannot_commit_success(self):
        from backend.wardrobe_operation import produce_wardrobe_operation
        with open_database(self.root) as db, self.transport():
            async with open_saver(self.root, db) as saver:
                _, decision = await self.start_and_approve(db, saver)
                async def wrong_transition(*args, **kwargs):
                    ref, _ = await produce_wardrobe_operation(*args, **kwargs)
                    return ref, sha256_digest(b"wrong transition")
                with patch("backend.wardrobe_operation.produce_wardrobe_operation", side_effect=wrong_transition):
                    await self.drain(db, saver)
                self.assertEqual(db.execute("SELECT * FROM execution_outcomes").fetchall(), [])
                self.assertEqual(db.execute("SELECT status,blocked_reason FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(), ("blocked", "wardrobe_invalid"))


if __name__ == "__main__":
    unittest.main()
