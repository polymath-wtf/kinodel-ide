from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from langgraph.graph import START, StateGraph
from langgraph.types import Command, interrupt
from typing_extensions import TypedDict

from backend.database import BUSY_TIMEOUT_MS, open_database
from backend.domain import StoryV1, make_operation_id
from backend.saver import SAVER_ID, SAVER_NAME, open_saver
from backend.story_store import create_test_execution, read_story, save_story


class State(TypedDict):
    answer: str


def graph_for(saver):
    graph = StateGraph(State)
    graph.add_node("ask", lambda state: {"answer": interrupt("question")})
    graph.add_edge(START, "ask")
    return graph.compile(checkpointer=saver)


class SaverTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel saver ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "root #1"
        self.path = self.root / SAVER_NAME

    async def test_interrupt_survives_close_and_reopen(self):
        config = {"configurable": {"thread_id": "t1"}}
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                conn = saver.conn
                for key, expected in {"journal_mode": "wal", "synchronous": 2,
                                      "busy_timeout": BUSY_TIMEOUT_MS, "foreign_keys": 1}.items():
                    self.assertEqual((await (await conn.execute(f"PRAGMA {key}")).fetchone())[0], expected)
                paused = await graph_for(saver).ainvoke({"answer": ""}, config, durability="sync")
                self.assertEqual(paused["__interrupt__"][0].value, "question")
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                graph = graph_for(saver)
                state = await graph.aget_state(config)
                self.assertEqual(state.interrupts[0].value, "question")
                self.assertEqual((await graph.ainvoke(Command(resume="yes"), config, durability="sync"))["answer"], "yes")
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                self.assertEqual((await graph_for(saver).aget_state(config)).values["answer"], "yes")

    async def test_legacy_story_root_acquires_saver_without_changing_story(self):
        project, execution = str(uuid4()), str(uuid4())
        story = StoryV1(
            schema_id="story", schema_version="1", hook="Light", story="A fox appears.",
            shots=[dict(shot_id="s1", action="Fox appears", narrative_function="Arrival",
                        subject_ids=[], state_before="Dark", state_after="Light")],
        )
        with open_database(self.root) as db:
            create_test_execution(db, project, execution, "input", ["s1"])
            ref = save_story(db, execution, make_operation_id(
                execution, "storytell", "sha256:" + "a" * 64, "generate"
            ), str(uuid4()), story)
        with open_database(self.root) as db:
            async with open_saver(self.root, db):
                self.assertEqual(read_story(db, execution), (ref, story))
        with open_database(self.root) as db:
            self.assertEqual(read_story(db, execution), (ref, story))
            async with open_saver(self.root, db):
                pass

    async def test_missing_saver_after_prepared_operation_is_not_recreated(self):
        from backend.story_store import prepare_story_operation

        with open_database(self.root) as db:
            create_test_execution(db, str(uuid4()), str(uuid4()), "input", ["s1"])
            execution = db.execute("SELECT execution_id FROM executions").fetchone()[0]
            prepare_story_operation(db, execution, "sha256:" + "a" * 64)
        with open_database(self.root) as db:
            with self.assertRaisesRegex(ValueError, "Missing saver"):
                async with open_saver(self.root, db):
                    pass
        self.assertFalse(self.path.exists())

    async def test_missing_saver_on_future_application_version_is_not_created(self):
        with open_database(self.root) as db:
            db.execute("PRAGMA user_version=6")
            try:
                with self.assertRaisesRegex(ValueError, "Missing saver"):
                    async with open_saver(self.root, db):
                        pass
                self.assertFalse(self.path.exists())
            finally:
                db.execute("PRAGMA user_version=5")

    async def test_failed_publish_does_not_leave_empty_saver(self):
        with open_database(self.root) as db:
            with patch("backend.saver.os.link", side_effect=OSError("publish failed")):
                with self.assertRaisesRegex(OSError, "publish failed"):
                    async with open_saver(self.root, db):
                        pass
            self.assertFalse(self.path.exists())
            self.assertFalse(any(p.name.startswith(".saver-") for p in self.root.iterdir()))
        with open_database(self.root) as db:
            async with open_saver(self.root, db):
                pass
            self.assertTrue(self.path.exists())

    async def test_publish_collision_preserves_foreign_saver(self):
        foreign = b"foreign bytes"

        def collide(source, destination):
            Path(destination).write_bytes(foreign)
            raise FileExistsError("already exists")

        with open_database(self.root) as db:
            with patch("backend.saver.os.link", side_effect=collide):
                with self.assertRaisesRegex(ValueError, "appeared"):
                    async with open_saver(self.root, db):
                        pass
            self.assertEqual(self.path.read_bytes(), foreign)
            self.assertFalse(any(p.name.startswith(".saver-") for p in self.root.iterdir()))
        with open_database(self.root) as db:
            with self.assertRaises((ValueError, sqlite3.DatabaseError)):
                async with open_saver(self.root, db):
                    pass
        self.assertEqual(self.path.read_bytes(), foreign)

    async def test_foreign_and_corrupt_files_unchanged(self):
        with open_database(self.root) as db:
            for contents in (b"not sqlite", None):
                if contents is None:
                    with closing(sqlite3.connect(self.path)) as foreign:
                        foreign.execute("CREATE TABLE unknown (id INTEGER)")
                        foreign.execute("INSERT INTO unknown VALUES (42)")
                else:
                    self.path.write_bytes(contents)
                before = self.path.read_bytes()
                with self.assertRaises((ValueError, sqlite3.DatabaseError)):
                    async with open_saver(self.root, db):
                        pass
                self.assertEqual(self.path.read_bytes(), before)
                self.path.unlink()

    async def test_missing_saver_with_redirected_sidecar_refused(self):
        with open_database(self.root) as db:
            sidecar = Path(str(self.path) + "-wal")
            sidecar.write_bytes(b"preserve")
            with self.assertRaises(ValueError):
                async with open_saver(self.root, db):
                    pass
            self.assertFalse(self.path.exists())
            self.assertEqual(sidecar.read_bytes(), b"preserve")

    async def test_identified_but_changed_saver_refused_without_mutation(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db):
                pass
        with closing(sqlite3.connect(self.path)) as foreign:
            foreign.execute("CREATE TABLE unexpected (value TEXT)")
            foreign.execute("INSERT INTO unexpected VALUES ('keep')")
        before = self.path.read_bytes()
        with open_database(self.root) as db:
            with self.assertRaisesRegex(ValueError, "schema"):
                async with open_saver(self.root, db):
                    pass
        self.assertEqual(self.path.read_bytes(), before)

    async def test_known_identity_with_unsupported_version_refused(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db):
                pass
        with closing(sqlite3.connect(self.path)) as foreign:
            foreign.execute("PRAGMA user_version=99")
            self.assertEqual(foreign.execute("PRAGMA application_id").fetchone()[0], SAVER_ID)
        before = self.path.read_bytes()
        with open_database(self.root) as db:
            with self.assertRaisesRegex(ValueError, "identity/version"):
                async with open_saver(self.root, db):
                    pass
        self.assertEqual(self.path.read_bytes(), before)

    async def test_foreign_wal_is_inspected_without_touching_original(self):
        with open_database(self.root) as db:
            with closing(sqlite3.connect(self.path)) as foreign:
                foreign.execute("PRAGMA journal_mode=WAL")
                foreign.execute("CREATE TABLE outsider (id INTEGER)")
                foreign.execute("INSERT INTO outsider VALUES (42)")
                foreign.commit()
                paths = [self.path, Path(str(self.path) + "-wal")]
                before = [p.read_bytes() for p in paths]
                with self.assertRaises(ValueError):
                    async with open_saver(self.root, db):
                        pass
                self.assertEqual([p.read_bytes() for p in paths], before)

    async def test_hardlinked_saver_is_refused(self):
        with open_database(self.root) as db:
            target = self.root / "other"
            target.write_bytes(b"preserve")
            os.link(target, self.path)
            with self.assertRaises(ValueError):
                async with open_saver(self.root, db):
                    pass
            self.assertEqual(target.read_bytes(), b"preserve")

    async def test_busy_timeout_is_bounded_on_saver_connection(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                with closing(sqlite3.connect(self.path, isolation_level=None)) as blocker:
                    blocker.execute("BEGIN IMMEDIATE")
                    try:
                        started = time.monotonic()
                        with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                            await saver.conn.execute("BEGIN IMMEDIATE")
                        self.assertLess(time.monotonic() - started, BUSY_TIMEOUT_MS / 1000 + 3)
                    finally:
                        blocker.execute("ROLLBACK")
