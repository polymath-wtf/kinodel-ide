import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from backend.database import APPLICATION_ID, DATABASE_NAME, open_database
from backend.domain import StoryV1, make_operation_id
from backend.story_store import create_test_execution, read_story, save_story


class StoryStorageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel story ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "данные"
        self.project = str(uuid4())
        self.execution = str(uuid4())
        self.operation = make_operation_id(self.execution, "storytell", "sha256:" + "a" * 64, "generate")
        self.story = StoryV1(
            schema_id="story", schema_version="1", hook="Light", story="A fox appears.",
            shots=[dict(shot_id="s1", action="Fox appears", narrative_function="Arrival",
                        subject_ids=[], state_before="Dark", state_after="Light")],
        )

    def test_reopen_replay_and_conflicts(self):
        with open_database(self.root) as db:
            create_test_execution(db, self.project, self.execution, " Creator input ", ["s1"])
            ref = save_story(db, self.execution, self.operation, str(uuid4()), self.story)
            self.assertEqual(save_story(db, self.execution, self.operation, str(uuid4()), self.story), ref)
            with self.assertRaises(ValueError):
                save_story(db, self.execution, self.operation, str(uuid4()),
                           self.story.model_copy(update={"hook": "Different"}))
            with self.assertRaises(sqlite3.IntegrityError):
                save_story(db, self.execution, make_operation_id(
                    self.execution, "storytell", "sha256:" + "b" * 64, "generate"
                ), str(uuid4()), self.story)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (1,))
        with open_database(self.root) as db:
            self.assertEqual(db.execute("SELECT input_message FROM executions").fetchone(), (" Creator input ",))
            self.assertEqual(read_story(db, self.execution), (ref, self.story))
            path = self.root / "projects" / self.project / "artifacts" / f"{ref.artifact_id}.{ref.digest[7:]}.json"
            path.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "integrity"):
                read_story(db, self.execution)

    def test_file_before_db_failure_stays_invisible_and_retries(self):
        with open_database(self.root) as db:
            create_test_execution(db, self.project, self.execution, "Input", ["s1"])
            artifact = str(uuid4())
            with patch("backend.story_store._publish", side_effect=OSError("disk failed")):
                with self.assertRaisesRegex(OSError, "disk failed"):
                    save_story(db, self.execution, self.operation, artifact, self.story)
            with self.assertRaisesRegex(ValueError, "not committed"):
                read_story(db, self.execution)
            db.execute("CREATE TEMP TRIGGER reject_story BEFORE INSERT ON artifacts BEGIN SELECT RAISE(ABORT, 'db failed'); END")
            with self.assertRaisesRegex(sqlite3.IntegrityError, "db failed"):
                save_story(db, self.execution, self.operation, artifact, self.story)
            with self.assertRaisesRegex(ValueError, "not committed"):
                read_story(db, self.execution)
            db.execute("DROP TRIGGER reject_story")
            ref = save_story(db, self.execution, self.operation, artifact, self.story)
            self.assertEqual(read_story(db, self.execution)[0], ref)

    def test_existing_object_conflict_and_v1_migration(self):
        self.root.mkdir()
        with closing(sqlite3.connect(self.root / DATABASE_NAME)) as old:
            old.execute(f"PRAGMA application_id={APPLICATION_ID}")
            old.execute("PRAGMA user_version=1")
        with open_database(self.root) as db:
            create_test_execution(db, self.project, self.execution, "Input", ["s1"])
            artifact = str(uuid4())
            from backend.domain import artifact_digest
            path = self.root / "projects" / self.project / "artifacts" / f"{artifact}.{artifact_digest(self.story)[7:]}.json"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"wrong bytes")
            with self.assertRaisesRegex(ValueError, "Conflicting immutable"):
                save_story(db, self.execution, self.operation, artifact, self.story)
            self.assertEqual(path.read_bytes(), b"wrong bytes")
            with self.assertRaisesRegex(ValueError, "not committed"):
                read_story(db, self.execution)
        with open_database(self.root) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM executions").fetchone(), (1,))


if __name__ == "__main__":
    unittest.main()
