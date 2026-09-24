import tempfile
import unittest
from contextlib import closing
from pathlib import Path
import sqlite3
from uuid import uuid4

from backend.database import APPLICATION_ID, DATABASE_NAME, REVIEW_SCHEMA, STORY_SCHEMA, OPERATION_SCHEMA, SCHEMA_VERSION, open_database
from backend.domain import StoryV1, make_operation_id
from backend.review_store import prepare_story_review
from backend.saver import SAVER_NAME, open_saver
from backend.story_graph import build_story_graph, initial_story_state
from backend.story_start import load_test_story_start, start_test_story
from backend.story_store import create_test_execution, read_story, save_story


class StartTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel start ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "data"
        self.project = str(uuid4())

    async def test_duplicate_conflict_and_recovery_without_checkpoint(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                first = await start_test_story(db, saver, self.project, "request-1", "An idea", ["s1", "s2"])
                self.assertEqual(first, await start_test_story(db, saver, self.project, "request-1", "An idea", ["s1", "s2"]))
                self.assertEqual(load_test_story_start(db, first.execution_id),
                                 (first, initial_story_state(self.project, first.execution_id)))
                self.assertEqual(db.execute("SELECT execution_id,kind,source_id,status FROM execution_work").fetchone(),
                                 (first.execution_id, "start", first.execution_id, "pending"))
                self.assertEqual(db.execute("SELECT input_message,shot_ids FROM executions").fetchone(),
                                 ("An idea", '["s1","s2"]'))
                self.assertIsNone(await saver.aget_tuple({"configurable": {"thread_id": first.execution_id}}))
                with self.assertRaisesRegex(ValueError, "conflict"):
                    await start_test_story(db, saver, self.project, "request-1", "Other", ["s1", "s2"])
                with self.assertRaisesRegex(ValueError, "conflict"):
                    await start_test_story(db, saver, self.project, "request-1", "An idea", ["s2", "s1"])
                self.assertNotEqual(first, await start_test_story(db, saver, self.project, "request-2", "An idea", ["s1", "s2"]))
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                self.assertEqual(first, await start_test_story(db, saver, self.project, "request-1", "An idea", ["s1", "s2"]))
                receipt, state = load_test_story_start(db, first.execution_id)
                self.assertEqual((receipt, state), (first, initial_story_state(self.project, first.execution_id)))
                def produce(message, shots, prior, feedback):
                    return StoryV1(schema_id="story", schema_version="1", hook=message,
                                   story="A new story.", shots=[dict(shot_id=shot, action="Arrive",
                                   narrative_function="Arrival", subject_ids=[], state_before="Dark",
                                   state_after="Light") for shot in shots])
                paused = await build_story_graph(db, saver, produce).ainvoke(
                    state, {"configurable": {"thread_id": receipt.execution_id}}, durability="sync")
                self.assertEqual(len(paused["__interrupt__"]), 1)
                self.assertEqual(read_story(db, first.execution_id)[1].hook, "An idea")
                self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_work").fetchone(), (2,))

    async def test_invalid_inputs_and_work_failure_roll_back_whole_start(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                for message, shots in (("", ["s1"]), ("ok", []), ("ok", ["s1", "s1"]), ("ok", ["\ud800"])):
                    with self.assertRaises((ValueError, UnicodeError)):
                        await start_test_story(db, saver, self.project, "key", message, shots)
                with self.assertRaises(ValueError):
                    await start_test_story(db, saver, self.project, "", "ok", ["s1"])
                db.execute("CREATE TEMP TRIGGER reject_start BEFORE INSERT ON execution_work "
                           "BEGIN SELECT RAISE(ABORT, 'work failed'); END")
                with self.assertRaisesRegex(sqlite3.IntegrityError, "work failed"):
                    await start_test_story(db, saver, self.project, "key", "ok", ["s1"])
                self.assertEqual(db.execute("SELECT COUNT(*) FROM executions").fetchone(), (0,))
                db.execute("DROP TRIGGER reject_start")
                self.assertEqual(load_test_story_start(db, (await start_test_story(db, saver, self.project, "key", "ok", ["s1"])).execution_id)[1]["project_id"], self.project)

    async def test_missing_or_unopened_saver_refuses_start_but_legacy_bootstraps(self):
        with open_database(self.root) as db:
            with self.assertRaises((ValueError, AttributeError)):
                await start_test_story(db, None, self.project, "key", "ok", ["s1"])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM executions").fetchone(), (0,))
            async with open_saver(self.root, db) as saver:
                receipt = await start_test_story(db, saver, self.project, "key", "ok", ["s1"])
        (self.root / SAVER_NAME).unlink()
        with open_database(self.root) as db:
            with self.assertRaisesRegex(ValueError, "Missing saver"):
                async with open_saver(self.root, db):
                    pass
            self.assertEqual(load_test_story_start(db, receipt.execution_id)[0], receipt)
        self.assertFalse((self.root / SAVER_NAME).exists())

    async def test_wrong_root_saver_and_changed_graph_pin_fail_closed(self):
        other_root = self.root.parent / "other"
        with open_database(self.root) as db:
            with open_database(other_root) as other_db:
                async with open_saver(other_root, other_db) as wrong_saver:
                    with self.assertRaisesRegex(ValueError, "Saver"):
                        await start_test_story(db, wrong_saver, self.project, "key", "Idea", ["s1"])
                self.assertEqual(db.execute("SELECT COUNT(*) FROM executions").fetchone(), (0,))
            async with open_saver(self.root, db) as saver:
                receipt = await start_test_story(db, saver, self.project, "key", "Idea", ["s1"])
                db.execute("UPDATE executions SET graph_digest='unrecognized' WHERE execution_id=?", (receipt.execution_id,))
                with self.assertRaisesRegex(ValueError, "unsupported"):
                    load_test_story_start(db, receipt.execution_id)
                with self.assertRaisesRegex(ValueError, "unsupported"):
                    await start_test_story(db, saver, self.project, "key", "Idea", ["s1"])

    async def test_v5_story_and_review_survive_migration(self):
        self.root.mkdir()
        with closing(sqlite3.connect(self.root / DATABASE_NAME)) as old:
            old.executescript(f"PRAGMA application_id={APPLICATION_ID}; PRAGMA user_version=5; "
                              f"{STORY_SCHEMA} {OPERATION_SCHEMA} {REVIEW_SCHEMA}")
        execution = str(uuid4())
        story = StoryV1(schema_id="story", schema_version="1", hook="Light", story="Fox arrives.",
                        shots=[dict(shot_id="s1", action="Fox arrives", narrative_function="Arrival",
                                    subject_ids=[], state_before="Dark", state_after="Light")])
        with closing(sqlite3.connect(self.root / DATABASE_NAME, isolation_level=None)) as db:
            db.execute("PRAGMA foreign_keys=ON")
            create_test_execution(db, self.project, execution, "Idea", ["s1"])
            ref = save_story(db, execution, make_operation_id(execution, "storytell", "sha256:" + "a" * 64, "generate"), str(uuid4()), story)
            review = prepare_story_review(db, execution, "sha256:" + "b" * 64, ref, 1)
        with open_database(self.root) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone(), (SCHEMA_VERSION,))
            self.assertEqual(read_story(db, execution), (ref, story))
            self.assertEqual(db.execute("SELECT request_id FROM review_requests").fetchone(), (review.request_id,))
            self.assertEqual(db.execute("SELECT client_key FROM executions WHERE execution_id=?", (execution,)).fetchone(), (None,))
            with self.assertRaisesRegex(ValueError, "Missing saver"):
                async with open_saver(self.root, db):
                    pass


if __name__ == "__main__":
    unittest.main()
