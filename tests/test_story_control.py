"""Durable retry, cancellation and local worker lifetime on the real saver."""

import asyncio
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from backend.database import (APPLICATION_ID, DATABASE_NAME, OPERATION_SCHEMA, REVIEW_SCHEMA,
                              RUNNER_SCHEMA, START_SCHEMA, STORY_SCHEMA, open_database)
from backend.review_store import accept_story_decision
from backend.saver import open_saver
from backend.story_runner import run_story_work
from backend.story_start import start_test_story
from backend.story_store import read_story, save_story
from tests.test_story_runner import produce_story


class StoryControlTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel control ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "data"
        self.project = str(uuid4())

    async def test_retry_same_work_only_for_transient_block_with_occ(self):
        from backend.story_control import retry_story_work

        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                receipt = await start_test_story(db, saver, self.project, "start", "A fox", ["s1"])

                def offline(*args):
                    raise TimeoutError("provider unavailable")

                self.assertEqual(await run_story_work(db, saver, offline), 1)
                blocked = db.execute("SELECT status,blocked_reason,work_version FROM execution_work "
                                     "WHERE work_id=?", (receipt.work_id,)).fetchone()
                self.assertEqual(blocked[:2], ("blocked", "owner_unavailable"))
                with self.assertRaisesRegex(ValueError, "version"):
                    retry_story_work(db, receipt.execution_id, receipt.work_id, "retry", blocked[2] - 1)
                retry_story_work(db, receipt.execution_id, receipt.work_id, "retry", blocked[2])
                self.assertEqual(db.execute("SELECT status,kind,source_id FROM execution_work WHERE work_id=?",
                                            (receipt.work_id,)).fetchone(),
                                 ("pending", "start", receipt.execution_id))
                self.assertEqual(await run_story_work(db, saver, produce_story), 1)
                retry_story_work(db, receipt.execution_id, receipt.work_id, "retry", blocked[2])
                with self.assertRaisesRegex(ValueError, "conflict"):
                    retry_story_work(db, receipt.execution_id, receipt.work_id, "retry", blocked[2] + 1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (1,))

    async def test_integrity_block_cannot_be_retried(self):
        from backend.story_control import retry_story_work

        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                receipt = await start_test_story(db, saver, self.project, "start", "A fox", ["s1"])
                db.execute("UPDATE executions SET graph_digest='broken' WHERE execution_id=?", (receipt.execution_id,))
                with self.assertRaisesRegex(ValueError, "unsupported"):
                    await run_story_work(db, saver, produce_story)
                version = db.execute("SELECT work_version FROM execution_work WHERE work_id=?", (receipt.work_id,)).fetchone()[0]
                with self.assertRaisesRegex(ValueError, "retryable"):
                    retry_story_work(db, receipt.execution_id, receipt.work_id, "retry", version)

    async def test_cancel_wait_is_durable_and_rejects_new_decisions_and_writes(self):
        from backend.story_control import cancel_story

        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                receipt = await start_test_story(db, saver, self.project, "start", "A fox", ["s1"])
                await run_story_work(db, saver, produce_story)
                review = db.execute("SELECT request_id,request_digest,binding_revision FROM review_requests").fetchone()
                control = cancel_story(db, receipt.execution_id, "cancel-1")
                self.assertEqual(cancel_story(db, receipt.execution_id, "cancel-1"), control)
                self.assertIsNone(db.execute("SELECT outcome FROM execution_outcomes").fetchone())
                with self.assertRaisesRegex(ValueError, "cancell"):
                    accept_story_decision(db, receipt.execution_id, review[0], review[1], review[2],
                                          "approve", "approve", None)
                current = read_story(db, receipt.execution_id)[0]
                with self.assertRaisesRegex(ValueError, "cancell"):
                    save_story(db, receipt.execution_id, "sha256:" + "a" * 64, str(uuid4()),
                               produce_story("A fox", ["s1"], None, None),
                               expected_revision=1)
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                self.assertEqual(await run_story_work(db, saver, produce_story), 1)
                self.assertEqual(db.execute("SELECT outcome,source_id FROM execution_outcomes").fetchone(),
                                 ("cancelled", "cancel-1"))
                self.assertEqual(db.execute("SELECT kind,status FROM execution_work WHERE work_id=?",
                                            (control,)).fetchone(), ("cancel", "completed"))
                self.assertEqual(read_story(db, receipt.execution_id)[0], current)
                self.assertEqual(await run_story_work(db, saver, produce_story), 0)
                self.assertEqual(cancel_story(db, receipt.execution_id, "cancel-1"), control)
                with self.assertRaisesRegex(ValueError, "cancel"):
                    cancel_story(db, receipt.execution_id, "different")

    async def test_cancel_during_awaited_owner_call_drains_before_terminal(self):
        from backend.story_control import cancel_story

        entered, cleaned = asyncio.Event(), asyncio.Event()

        async def slow_owner(*args):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()
            return produce_story(*args)

        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                receipt = await start_test_story(db, saver, self.project, "start", "A fox", ["s1"])
                task = asyncio.create_task(run_story_work(db, saver, slow_owner))
                await asyncio.wait_for(entered.wait(), 5)
                cancel_story(db, receipt.execution_id, "stop")
                self.assertIsNone(db.execute("SELECT outcome FROM execution_outcomes").fetchone())
                await asyncio.wait_for(task, 5)
                self.assertTrue(cleaned.is_set())
                self.assertEqual(db.execute("SELECT outcome FROM execution_outcomes").fetchone(), ("cancelled",))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (0,))
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                self.assertEqual(await run_story_work(db, saver, produce_story), 0)

    async def test_cancel_preempts_queued_approval(self):
        from backend.story_control import cancel_story

        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                receipt = await start_test_story(db, saver, self.project, "start", "A fox", ["s1"])
                await run_story_work(db, saver, produce_story)
                review = db.execute("SELECT request_id,request_digest,binding_revision FROM review_requests").fetchone()
                decision = accept_story_decision(db, receipt.execution_id, review[0], review[1], review[2],
                                                 "approve", "approve", None)
                cancel_story(db, receipt.execution_id, "stop")
                await run_story_work(db, saver, produce_story)
                self.assertEqual(db.execute("SELECT outcome FROM execution_outcomes").fetchone(), ("cancelled",))
                self.assertEqual(db.execute("SELECT applied_activation FROM review_requests").fetchone(), (None,))
                self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?",
                                            (decision.work_id,)).fetchone(), ("obsolete",))

    async def test_owner_ignoring_task_cancel_cannot_commit_late_story(self):
        from backend.story_control import cancel_story

        entered = asyncio.Event()

        async def stubborn_owner(*args):
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                return produce_story(*args)

        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                receipt = await start_test_story(db, saver, self.project, "start", "A fox", ["s1"])
                running = asyncio.create_task(run_story_work(db, saver, stubborn_owner))
                await asyncio.wait_for(entered.wait(), 5)
                cancel_story(db, receipt.execution_id, "stop")
                await asyncio.wait_for(running, 5)
                self.assertEqual(db.execute("SELECT outcome FROM execution_outcomes").fetchone(), ("cancelled",))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (0,))

    async def test_cancel_work_insert_failure_rolls_back_control(self):
        from backend.story_control import cancel_story

        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                receipt = await start_test_story(db, saver, self.project, "start", "A fox", ["s1"])
                db.execute("CREATE TEMP TRIGGER reject_cancel BEFORE INSERT ON execution_controls "
                           "BEGIN SELECT RAISE(ABORT, 'control failed'); END")
                with self.assertRaisesRegex(sqlite3.IntegrityError, "control failed"):
                    cancel_story(db, receipt.execution_id, "stop")
                self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_controls").fetchone(), (0,))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_work WHERE kind='cancel'").fetchone(), (0,))

    async def test_v7_rows_survive_control_migration(self):
        self.root.mkdir()
        execution, project = str(uuid4()), str(uuid4())
        with closing(sqlite3.connect(self.root / DATABASE_NAME)) as old:
            old.executescript(f"PRAGMA application_id={APPLICATION_ID}; PRAGMA user_version=7; "
                              f"{STORY_SCHEMA} {OPERATION_SCHEMA} {REVIEW_SCHEMA} {START_SCHEMA} {RUNNER_SCHEMA}")
            old.execute("INSERT INTO executions (execution_id,project_id,input_message,shot_ids) "
                        "VALUES (?,?,?,?)", (execution, project, "Idea", '["s1"]'))
            old.execute("INSERT INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,status,"
                        "blocked_reason) VALUES (?,?, 'start', ?, ?, 'blocked', 'owner_unavailable')",
                        (execution, execution, execution, "sha256:" + "a" * 64))
            old.commit()
        with open_database(self.root) as db:
            self.assertEqual(db.execute("SELECT status,blocked_reason,work_version FROM execution_work").fetchone(),
                             ("blocked", "owner_unavailable", 0))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_controls").fetchone(), (0,))

    async def test_shutdown_drains_owner_before_releasing_root(self):
        from backend.story_control import open_story_runtime

        entered, cleaned = asyncio.Event(), asyncio.Event()

        async def slow_owner(*args):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()
            return produce_story(*args)

        async with open_story_runtime(self.root, slow_owner) as runtime:
            receipt = await runtime.start(self.project, "start", "A fox", ["s1"])
            running = asyncio.create_task(runtime.run())
            await asyncio.wait_for(entered.wait(), 5)
        self.assertTrue(cleaned.is_set())
        await asyncio.wait_for(running, 5)
        with self.assertRaisesRegex(ValueError, "closed"):
            await runtime.start(self.project, "later", "A fox", ["s1"])
        async with open_story_runtime(self.root, produce_story) as again:
            self.assertEqual(await again.run(), 1)
            self.assertIsNotNone(again.db.execute("SELECT checkpoint_id FROM review_requests "
                                                  "WHERE execution_id=?", (receipt.execution_id,)).fetchone()[0])


if __name__ == "__main__":
    unittest.main()
