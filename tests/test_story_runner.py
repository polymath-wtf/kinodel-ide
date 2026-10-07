"""Real saver + durable work: no manual graph resume or wait binding."""

import asyncio
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
import sqlite3
from uuid import uuid4
from unittest.mock import patch

from backend.database import (APPLICATION_ID, CONTROL_SCHEMA, DATABASE_NAME, OPERATION_SCHEMA,
                              REVIEW_SCHEMA, RUNNER_SCHEMA, START_SCHEMA, STORY_SCHEMA, open_database)
from backend.domain import StoryV1
from backend.review_store import accept_story_decision
from backend.review_store import apply_story_decision
from backend.saver import open_saver
from backend.story_runner import run_story_work
from backend.story_start import start_test_story
from backend.story_store import prepare_story_operation, read_story, save_story
from backend.api import fixture_story


def produce_story(message, shots, prior, feedback):
    return StoryV1(schema_id="story", schema_version="1", hook="Night" if prior else "Light",
                   story="A fox appears.", shots=[dict(
                       shot_id="s1", action="Fox appears", narrative_function="Arrival",
                       subject_ids=[], state_before="Dark", state_after="Light")])


class StoryRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def _gated_writer(self, method, phase, control, *, repeat=False):
        """Public invocation/saver seams reproduce an unshielded EXIT waiter deterministically."""
        from langgraph.checkpoint.base import empty_checkpoint
        from backend.story_control import open_story_runtime

        entered, exit_entered, graph_finished, release, stopped = (asyncio.Event() for _ in range(5))
        writers, exits, proxies = [], [], []
        with tempfile.TemporaryDirectory(prefix="kinodel writer drain ") as directory:
            root = Path(directory) / "data"
            async with open_story_runtime(root, produce_story) as runtime:
                receipt = await runtime.start(str(uuid4()), "start", "Fox", ["s1"])
                raw_write = getattr(runtime.saver, method)
                calls = []

                async def gated(*args, **kwargs):
                    calls.append(args)
                    entered.set()
                    try:
                        await release.wait()
                        return await raw_write(*args, **kwargs)
                    finally:
                        stopped.set()

                def build(db, saver, *args, **kwargs):
                    proxies.append(saver)

                    class ExitGraph:
                        checkpointer = saver

                        async def ainvoke(self, state, config, **kwargs):
                            asyncio.current_task().add_done_callback(lambda _: graph_finished.set())
                            checkpoint = empty_checkpoint()
                            config = {"configurable": {**config["configurable"], "checkpoint_ns": "",
                                                       "checkpoint_id": checkpoint["id"]}}
                            writer = asyncio.create_task(saver.aput(config, checkpoint, {"source": "input", "step": -1}, {})
                                if method == "aput" else saver.aput_writes(config, [("story_activation", state["story_activation"])], "test-task"))
                            writers.append(writer)
                            await entered.wait()
                            try:
                                if phase == "execution":
                                    await asyncio.Event().wait()
                            finally:
                                async def exit_cleanup():
                                    exit_entered.set()
                                    await asyncio.wait({writer})
                                cleanup = asyncio.create_task(exit_cleanup())
                                exits.append(cleanup)
                                # Same failure shape as LG: cancellation of this await leaves the writer orphaned.
                                await cleanup

                    return ExitGraph()

                with patch.object(runtime.saver, method, gated), patch("backend.story_runner.build_story_graph", build):
                    running = asyncio.create_task(runtime.run())
                    closing = None
                    try:
                        await asyncio.wait_for(entered.wait() if phase == "execution" else exit_entered.wait(), 5)
                        if control == "cancel":
                            runtime.cancel(receipt.execution_id, "cancel")
                        elif control == "task":
                            running.cancel()
                        else:
                            closing = asyncio.create_task(runtime.close())
                        await asyncio.wait_for(exit_entered.wait(), 5)
                        if phase == "exit":
                            await asyncio.wait_for(graph_finished.wait(), 5)
                            with self.assertRaisesRegex(RuntimeError, "closed"):
                                await getattr(proxies[0], method)(*calls[0])
                            self.assertEqual(len(calls), 1)
                        # Repeated parent cancellation must not interrupt the final saver barrier.
                        for _ in range(3 if repeat else 1):
                            done, _ = await asyncio.wait({running}, timeout=0.1)
                            self.assertFalse(done, "Runner returned with its invocation writer still held")
                            self.assertFalse(stopped.is_set(), "Cancellation aborted instead of draining the saver write")
                            self.assertEqual(runtime.db.execute("SELECT * FROM execution_outcomes").fetchall(), [])
                            if repeat:
                                running.cancel()
                                if closing is not None:
                                    closing.cancel()
                        release.set()
                        result = await asyncio.gather(running, return_exceptions=True)
                        if control == "task" or repeat:
                            self.assertIsInstance(result[0], asyncio.CancelledError)
                        else:
                            self.assertEqual(result, [1])
                        if closing is not None:
                            await asyncio.gather(closing, return_exceptions=True)
                        self.assertTrue(stopped.is_set())
                        self.assertTrue(all(task.done() for task in writers + exits))
                        self.assertEqual(len(calls), 1)
                        if not repeat and control == "cancel":
                            self.assertEqual(runtime.db.execute("SELECT outcome FROM execution_outcomes").fetchone(), ("cancelled",))
                        # An old framework task cannot write through its proxy after invocation settlement.
                        with self.assertRaisesRegex(RuntimeError, "closed"):
                            await getattr(proxies[0], method)(*calls[0])
                        self.assertEqual(len(calls), 1)
                    finally:
                        release.set()
                        await asyncio.gather(running, *writers, *exits, *([closing] if closing else []), return_exceptions=True)

    async def test_cancel_during_exit_drains_checkpoint_and_pending_writes(self):
        for method in ("aput", "aput_writes"):
            with self.subTest(method=method):
                await self._gated_writer(method, "exit", "cancel")

    async def test_execution_cancel_and_repeated_exit_cancel_drain_writers(self):
        for method in ("aput", "aput_writes"):
            for phase in ("execution", "exit"):
                with self.subTest(method=method, phase=phase):
                    await self._gated_writer(method, phase, "task", repeat=True)

    async def test_runtime_stop_and_repeated_shutdown_cancel_drain_writers(self):
        for method in ("aput", "aput_writes"):
            for repeat in (False, True):
                with self.subTest(method=method, repeat=repeat):
                    await self._gated_writer(method, "exit", "stop", repeat=repeat)

    async def test_sweep_does_not_enqueue_reconcile_when_decision_arrives_during_saver_read(self):
        with tempfile.TemporaryDirectory(prefix="kinodel sweep race ") as directory:
            root = Path(directory) / "data"
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    receipt = await start_test_story(db, saver, str(uuid4()), "start", "Fox", ["s1"])
                    await run_story_work(db, saver, produce_story)
                    request = db.execute("SELECT request_id,request_digest,binding_revision FROM review_requests").fetchone()
                    original = saver.aget_tuple
                    injected = False

                    async def accept_while_reading(*args, **kwargs):
                        nonlocal injected
                        saved = await original(*args, **kwargs)
                        if not injected:
                            injected = True
                            accept_story_decision(db, receipt.execution_id, request[0], request[1], request[2],
                                                  "edit", "revise", "Darker")
                        return saved

                    saver.aget_tuple = accept_while_reading
                    self.assertEqual(await run_story_work(db, saver, produce_story), 1)
                    self.assertTrue(injected)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_work WHERE kind='reconcile'").fetchone(), (0,))
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (2,))

    async def test_committed_clarification_replays_without_second_owner_call(self):
        with tempfile.TemporaryDirectory(prefix="kinodel owner response ") as directory:
            root = Path(directory) / "data"
            project = str(uuid4())
            calls = []

            def owner(*args, discussion=None):
                calls.append(discussion)
                return fixture_story(*args, discussion=discussion)

            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    receipt = await start_test_story(db, saver, project, "start", "A fox", ["s1"])
                    await run_story_work(db, saver, owner)
                    first = db.execute("SELECT request_id,request_digest,binding_revision,checkpoint_id,task_id,"
                                       "interrupt_id FROM review_requests").fetchone()
                    accept_story_decision(db, receipt.execution_id, first[0], first[1], first[2],
                                          "question", "clarify", "Why?")
                    from backend.story_store import commit_owner_response
                    original = commit_owner_response

                    def stop_after_response(*args):
                        result = original(*args)
                        raise RuntimeError("after response commit")

                    with patch("backend.story_graph.commit_owner_response", side_effect=stop_after_response):
                        with self.assertRaisesRegex(RuntimeError, "after response commit"):
                            await run_story_work(db, saver, owner)
                    self.assertEqual(len(calls), 2)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (1,))
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    self.assertEqual(await run_story_work(db, saver, owner), 1)
                    self.assertEqual(len(calls), 2)
                    second = db.execute("SELECT request_id,request_digest,binding_revision,checkpoint_id,task_id,"
                                        "interrupt_id FROM review_requests ORDER BY request_revision DESC LIMIT 1").fetchone()
                    self.assertNotEqual(first[0], second[0])
                    self.assertNotEqual(first[3:], second[3:])
                    self.assertEqual(second[2], 1)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (1,))
                    self.assertEqual(db.execute("SELECT owner_response FROM story_operations "
                                                "WHERE owner_response IS NOT NULL").fetchone()[0],
                                     '{"explanation":"The Story follows: A fox","status":"clarified"}')
                    accept_story_decision(db, receipt.execution_id, second[0], second[1], second[2],
                                          "approve", "approve", None)
                    await run_story_work(db, saver, owner)

    async def test_approval_outcome_commits_before_final_checkpoint(self):
        with tempfile.TemporaryDirectory(prefix="kinodel approval gap ") as directory:
            root = Path(directory) / "data"
            project = str(uuid4())
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    receipt = await start_test_story(db, saver, project, "start", "A fox", ["s1"])
                    await run_story_work(db, saver, produce_story)
                    request = db.execute("SELECT request_id,request_digest,binding_revision FROM review_requests").fetchone()
                    decision = accept_story_decision(db, receipt.execution_id, request[0], request[1],
                                                     request[2], "approve", "approve", None)

                    def stop_after_apply(*args):
                        apply_story_decision(*args)
                        raise RuntimeError("stopped before END")

                    with patch("backend.story_graph.apply_story_decision", side_effect=stop_after_apply):
                        with self.assertRaisesRegex(RuntimeError, "stopped before END"):
                            await run_story_work(db, saver, produce_story)
                    self.assertEqual(db.execute("SELECT outcome,source_id FROM execution_outcomes").fetchone(),
                                     ("completed", request[0]))
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    self.assertEqual(await run_story_work(db, saver, produce_story), 1)
                    self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?",
                                                (decision.work_id,)).fetchone(), ("completed",))
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (1,))

    async def test_failed_terminal_commit_rolls_back_and_retries(self):
        with tempfile.TemporaryDirectory(prefix="kinodel terminal gap ") as directory:
            root = Path(directory) / "data"
            project = str(uuid4())
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    receipt = await start_test_story(db, saver, project, "start", "A fox", ["s1"])
                    await run_story_work(db, saver, produce_story)
                    request = db.execute("SELECT request_id,request_digest,binding_revision FROM review_requests").fetchone()
                    decision = accept_story_decision(db, receipt.execution_id, request[0], request[1],
                                                     request[2], "approve", "approve", None)
                    db.execute("CREATE TEMP TRIGGER stop_outcome BEFORE INSERT ON execution_outcomes "
                               "BEGIN SELECT RAISE(ABORT, 'terminal gap'); END")
                    with self.assertRaisesRegex(sqlite3.IntegrityError, "terminal gap"):
                        await run_story_work(db, saver, produce_story)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_outcomes").fetchone(), (0,))
                    self.assertEqual(db.execute("SELECT applied_activation FROM review_requests").fetchone(), (None,))
                    self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?",
                                                (decision.work_id,)).fetchone(), ("claimed",))
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    self.assertEqual(await run_story_work(db, saver, produce_story), 1)
                    self.assertEqual(db.execute("SELECT outcome,source_id FROM execution_outcomes").fetchone(),
                                     ("completed", request[0]))
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (1,))

    async def test_runner_rejects_saver_from_other_root(self):
        with tempfile.TemporaryDirectory(prefix="kinodel foreign runner ") as directory:
            base = Path(directory)
            project = str(uuid4())
            with open_database(base / "first") as db:
                async with open_saver(base / "first", db) as saver:
                    receipt = await start_test_story(db, saver, project, "start", "A fox", ["s1"])
                    with open_database(base / "second") as other_db:
                        async with open_saver(base / "second", other_db) as foreign:
                            with self.assertRaisesRegex(ValueError, "Saver"):
                                await run_story_work(db, foreign, produce_story)
                    self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?",
                                                (receipt.work_id,)).fetchone(), ("pending",))

    async def test_unfinished_checkpoint_without_live_work_is_reconciled(self):
        with tempfile.TemporaryDirectory(prefix="kinodel reconcile ") as directory:
            root = Path(directory) / "data"
            project = str(uuid4())
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    receipt = await start_test_story(db, saver, project, "start", "A fox", ["s1"])

                    def stop_before_result(*args):
                        raise RuntimeError("owner stopped")

                    with self.assertRaisesRegex(RuntimeError, "owner stopped"):
                        await run_story_work(db, saver, stop_before_result)
                    db.execute("UPDATE execution_work SET status='completed' WHERE work_id=?", (receipt.work_id,))
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    self.assertEqual(await run_story_work(db, saver, produce_story), 1)
                    self.assertEqual(db.execute("SELECT kind,status FROM execution_work WHERE kind='reconcile'").fetchone(),
                                     ("reconcile", "completed"))
                    self.assertIsNotNone(db.execute("SELECT checkpoint_id FROM review_requests").fetchone()[0])
                    self.assertEqual(await run_story_work(db, saver, produce_story), 0)

    async def test_bound_wait_with_unsettled_start_does_not_swallow_response(self):
        with tempfile.TemporaryDirectory(prefix="kinodel unsettled start ") as directory:
            root = Path(directory) / "data"
            project = str(uuid4())
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    receipt = await start_test_story(db, saver, project, "start", "A fox", ["s1"])
                    await run_story_work(db, saver, produce_story)
                    request = db.execute("SELECT request_id,request_digest,binding_revision FROM review_requests").fetchone()
                    accept_story_decision(db, receipt.execution_id, request[0], request[1], request[2],
                                          "revise", "revise", "Darker")
                    db.execute("UPDATE execution_work SET status='claimed' WHERE work_id=?", (receipt.work_id,))
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    self.assertEqual(await run_story_work(db, saver, produce_story), 2)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (2,))
                    self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?",
                                                (receipt.work_id,)).fetchone(), ("completed",))

    async def test_applied_decision_replays_through_next_wait(self):
        with tempfile.TemporaryDirectory(prefix="kinodel runner apply ") as directory:
            root = Path(directory) / "data"
            project = str(uuid4())
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    receipt = await start_test_story(db, saver, project, "start", "A fox", ["s1"])
                    await run_story_work(db, saver, produce_story)
                    request = db.execute("SELECT request_id,request_digest,binding_revision FROM review_requests").fetchone()
                    decision = accept_story_decision(db, receipt.execution_id, request[0], request[1],
                                                     request[2], "revise", "revise", "Darker")

                    def stop_after_apply(*args):
                        apply_story_decision(*args)
                        raise RuntimeError("stopped after apply")

                    with patch("backend.story_graph.apply_story_decision", side_effect=stop_after_apply):
                        with self.assertRaisesRegex(RuntimeError, "stopped after apply"):
                            await run_story_work(db, saver, produce_story)
                    self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?",
                                                (decision.work_id,)).fetchone(), ("claimed",))
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    self.assertEqual(await run_story_work(db, saver, produce_story), 1)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (2,))
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM review_requests").fetchone(), (2,))
                    self.assertIsNotNone(db.execute("SELECT checkpoint_id FROM review_requests "
                                                    "ORDER BY request_revision DESC LIMIT 1").fetchone()[0])

    async def test_v6_start_work_survives_runner_migration(self):
        with tempfile.TemporaryDirectory(prefix="kinodel v6 runner ") as directory:
            root = Path(directory) / "data"
            root.mkdir()
            execution, project = str(uuid4()), str(uuid4())
            with closing(sqlite3.connect(root / DATABASE_NAME)) as old:
                old.executescript(f"PRAGMA application_id={APPLICATION_ID}; PRAGMA user_version=6; "
                                  f"{STORY_SCHEMA} {OPERATION_SCHEMA} {REVIEW_SCHEMA} {START_SCHEMA}")
                old.execute("INSERT INTO executions (execution_id,project_id,input_message,shot_ids) "
                            "VALUES (?,?,?,?)", (execution, project, "Idea", '["s1"]'))
                old.commit()
            with open_database(root) as db:
                self.assertEqual(db.execute("SELECT input_message FROM executions WHERE execution_id=?",
                                            (execution,)).fetchone(), ("Idea",))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_outcomes").fetchone(), (0,))

    async def test_v8_discussion_migration_preserves_committed_story(self):
        with tempfile.TemporaryDirectory(prefix="kinodel v8 discussion ") as directory:
            root = Path(directory) / "data"
            root.mkdir()
            execution, project = str(uuid4()), str(uuid4())
            with closing(sqlite3.connect(root / DATABASE_NAME)) as old:
                old.executescript(f"PRAGMA application_id={APPLICATION_ID}; PRAGMA user_version=8; "
                                  f"{STORY_SCHEMA} {OPERATION_SCHEMA} {REVIEW_SCHEMA} {START_SCHEMA} "
                                  f"{RUNNER_SCHEMA} {CONTROL_SCHEMA}")
                old.execute("INSERT INTO executions (execution_id,project_id,input_message,shot_ids) "
                            "VALUES (?,?,?,?)", (execution, project, "Idea", '["s1"]'))
                old.commit()
            with open_database(root) as db:
                self.assertEqual(db.execute("SELECT input_message FROM executions WHERE execution_id=?",
                                            (execution,)).fetchone(), ("Idea",))
                self.assertEqual(db.execute("SELECT owner_response,discussion_activation FROM story_operations").fetchall(), [])

    async def test_persisted_resume_write_restarts_without_answering_next_wait(self):
        with tempfile.TemporaryDirectory(prefix="kinodel pending resume ") as directory:
            root = Path(directory) / "data"
            project = str(uuid4())
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    receipt = await start_test_story(db, saver, project, "start", "A fox", ["s1"])
                    await run_story_work(db, saver, produce_story)
                    first = db.execute("SELECT request_id,request_digest,binding_revision FROM review_requests").fetchone()
                    decision = accept_story_decision(db, receipt.execution_id, first[0], first[1], first[2],
                                                     "revise", "revise", "Darker")
                    original = saver.aput_writes
                    tripped = False

                    async def stop_after_resume(*args, **kwargs):
                        nonlocal tripped
                        result = await original(*args, **kwargs)
                        if not tripped and any(channel == "__resume__" for channel, _ in args[1]):
                            tripped = True
                            raise RuntimeError("persisted resume before checkpoint")
                        return result

                    saver.aput_writes = stop_after_resume
                    with self.assertRaisesRegex(RuntimeError, "persisted resume"):
                        await run_story_work(db, saver, produce_story)
                    self.assertTrue(tripped)
                    self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?",
                                                (decision.work_id,)).fetchone(), ("claimed",))
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    self.assertEqual(await run_story_work(db, saver, produce_story), 1)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (2,))
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM review_requests").fetchone(), (2,))
                    self.assertEqual(db.execute("SELECT decision_id FROM review_requests "
                                                "ORDER BY request_revision DESC LIMIT 1").fetchone(), (None,))

    async def test_wrong_source_identity_blocks_without_advancing(self):
        with tempfile.TemporaryDirectory(prefix="kinodel mismatched resume ") as directory:
            root = Path(directory) / "data"
            project = str(uuid4())
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    receipt = await start_test_story(db, saver, project, "start", "A fox", ["s1"])
                    await run_story_work(db, saver, produce_story)
                    request = db.execute("SELECT request_id,request_digest,binding_revision FROM review_requests").fetchone()
                    decision = accept_story_decision(db, receipt.execution_id, request[0], request[1], request[2],
                                                     "revise", "revise", "Darker")
                    db.execute("UPDATE execution_work SET resume_ref='wrong' WHERE work_id=?", (decision.work_id,))
                    with self.assertRaisesRegex(ValueError, "Resume work identity mismatch"):
                        await run_story_work(db, saver, produce_story)
                    self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?",
                                                (decision.work_id,)).fetchone(), ("blocked",))
                    self.assertEqual(db.execute("SELECT applied_activation FROM review_requests").fetchone(), (None,))
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (1,))

    async def test_start_revise_approve_across_reopens(self):
        with tempfile.TemporaryDirectory(prefix="kinodel runner ") as directory:
            root = Path(directory) / "data"
            project = str(uuid4())
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    receipt = await start_test_story(db, saver, project, "start", "A fox", ["s1"])
                    self.assertEqual(await run_story_work(db, saver, produce_story), 1)
                    first = db.execute("SELECT request_id,request_digest,binding_revision,checkpoint_id "
                                       "FROM review_requests WHERE execution_id=?", (receipt.execution_id,)).fetchone()
                    self.assertIsNotNone(first[3])
                    self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?",
                                                (receipt.work_id,)).fetchone(), ("completed",))
                    self.assertEqual(await run_story_work(db, saver, produce_story), 0)
                    revise = accept_story_decision(db, receipt.execution_id, first[0], first[1], first[2],
                                                   "revise", "revise", "Make it darker")
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    self.assertEqual(await run_story_work(db, saver, produce_story), 1)
                    second = db.execute("SELECT request_id,request_digest,binding_revision,checkpoint_id "
                                        "FROM review_requests WHERE execution_id=? ORDER BY request_revision DESC LIMIT 1",
                                        (receipt.execution_id,)).fetchone()
                    self.assertNotEqual(first[0], second[0])
                    self.assertEqual(second[2], 2)
                    self.assertIsNotNone(second[3])
                    self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?",
                                                (revise.work_id,)).fetchone(), ("completed",))
                    approve = accept_story_decision(db, receipt.execution_id, second[0], second[1], second[2],
                                                    "approve", "approve", None)
            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    self.assertEqual(await run_story_work(db, saver, produce_story), 1)
                    self.assertEqual(await run_story_work(db, saver, produce_story), 0)
                    self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?",
                                                (approve.work_id,)).fetchone(), ("completed",))
                    self.assertEqual(db.execute("SELECT subject_artifact_id FROM execution_outcomes "
                                                "WHERE execution_id=? AND outcome='completed'",
                                                (receipt.execution_id,)).fetchone(),
                                     (read_story(db, receipt.execution_id)[0].artifact_id,))
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts WHERE execution_id=?",
                                                (receipt.execution_id,)).fetchone(), (2,))
                    current, _ = read_story(db, receipt.execution_id)
                    with self.assertRaisesRegex(ValueError, "terminal"):
                        prepare_story_operation(db, receipt.execution_id, "sha256:" + "f" * 64,
                                                prior_ref=current, feedback="More", expected_revision=2)
                    with self.assertRaisesRegex(ValueError, "terminal"):
                        save_story(db, receipt.execution_id, "sha256:" + "e" * 64, str(uuid4()),
                                   produce_story("A fox", ["s1"], None, None), expected_revision=2)


if __name__ == "__main__":
    unittest.main()
