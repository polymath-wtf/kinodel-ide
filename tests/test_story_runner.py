"""Real saver + durable work: no manual graph resume or wait binding."""

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
