import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from backend.database import APPLICATION_ID, DATABASE_NAME, OPERATION_SCHEMA, STORY_SCHEMA, V2_SCHEMA, open_database
from backend.domain import StoryV1, canonical_json, make_operation_id, sha256_digest
from backend.story_store import (commit_story_operation, create_test_execution,
                                 prepare_story_operation, read_story, save_story)


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
            with self.assertRaisesRegex(ValueError, "revision"):
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

    def test_revision_history_replay_and_occ(self):
        revised = self.story.model_copy(update={"hook": "Night"})
        second = make_operation_id(self.execution, "storytell", "sha256:" + "b" * 64, "revise")
        third = make_operation_id(self.execution, "storytell", "sha256:" + "c" * 64, "revise")
        with open_database(self.root) as db:
            create_test_execution(db, self.project, self.execution, "Input", ["s1"])
            first_ref = save_story(db, self.execution, self.operation, str(uuid4()), self.story)
            with self.assertRaisesRegex(ValueError, "revision"):
                save_story(db, self.execution, second, str(uuid4()), revised)
            with self.assertRaisesRegex(ValueError, "revision"):
                save_story(db, self.execution, second, str(uuid4()), revised, expected_revision=0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (1,))
            second_ref = save_story(db, self.execution, second, str(uuid4()), revised, expected_revision=1)
            self.assertEqual(read_story(db, self.execution), (second_ref, revised))
            self.assertEqual(read_story(db, self.execution, artifact_id=first_ref.artifact_id), (first_ref, self.story))
            self.assertEqual(save_story(db, self.execution, self.operation, str(uuid4()), self.story), first_ref)
            self.assertEqual(db.execute("SELECT binding_revision FROM execution_bindings").fetchone(), (2,))
            with self.assertRaisesRegex(ValueError, "revision"):
                save_story(db, self.execution, third, str(uuid4()), self.story, expected_revision=1)
            with self.assertRaisesRegex(ValueError, "replay conflicts"):
                save_story(db, self.execution, self.operation, str(uuid4()), revised)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (2,))
        with open_database(self.root) as db:
            self.assertEqual(read_story(db, self.execution), (second_ref, revised))
            self.assertEqual(read_story(db, self.execution, artifact_id=first_ref.artifact_id), (first_ref, self.story))
            with self.assertRaisesRegex(ValueError, "not committed"):
                read_story(db, str(uuid4()), artifact_id=first_ref.artifact_id)

    def test_failed_revision_leaves_current_unchanged(self):
        with open_database(self.root) as db:
            create_test_execution(db, self.project, self.execution, "Input", ["s1"])
            first = save_story(db, self.execution, self.operation, str(uuid4()), self.story)
            second = make_operation_id(self.execution, "storytell", "sha256:" + "b" * 64, "revise")
            revised = self.story.model_copy(update={"hook": "Night"})
            with patch("backend.story_store._publish", side_effect=OSError("disk failed")):
                with self.assertRaisesRegex(OSError, "disk failed"):
                    save_story(db, self.execution, second, str(uuid4()), revised, expected_revision=1)
            db.execute("CREATE TEMP TRIGGER reject_story BEFORE INSERT ON artifacts BEGIN SELECT RAISE(ABORT, 'db failed'); END")
            with self.assertRaisesRegex(sqlite3.IntegrityError, "db failed"):
                save_story(db, self.execution, second, str(uuid4()), revised, expected_revision=1)
            self.assertEqual(read_story(db, self.execution), (first, self.story))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (1,))

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

    def test_v2_migration_preserves_committed_story(self):
        self.root.mkdir()
        artifact = str(uuid4())
        body = canonical_json(self.story)
        digest = sha256_digest(body)
        path = self.root / "projects" / self.project / "artifacts" / f"{artifact}.{digest[7:]}.json"
        path.parent.mkdir(parents=True)
        path.write_bytes(body)
        with closing(sqlite3.connect(self.root / DATABASE_NAME)) as old:
            old.executescript(f"PRAGMA application_id={APPLICATION_ID}; PRAGMA user_version=2; {V2_SCHEMA}")
            with old:
                old.execute("INSERT INTO executions VALUES (?,?,?,?)", (self.execution, self.project, "Input", '["s1"]'))
                old.execute("INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)", (
                    artifact, self.execution, self.operation, digest,
                    f"kinodel://projects/{self.project}/artifacts/{artifact}", "story", "1", "storytell",
                ))
                old.execute("INSERT INTO execution_bindings VALUES (?,?,?,?)", (self.execution, "story", artifact, 1))
        with open_database(self.root) as db:
            original, story = read_story(db, self.execution)
            self.assertEqual((original.artifact_id, story), (artifact, self.story))
            second = make_operation_id(self.execution, "storytell", "sha256:" + "b" * 64, "revise")
            revised = self.story.model_copy(update={"hook": "Night"})
            new_ref = save_story(db, self.execution, second, str(uuid4()), revised, expected_revision=1)
            self.assertEqual(read_story(db, self.execution, artifact_id=artifact), (original, self.story))
            self.assertEqual(read_story(db, self.execution), (new_ref, revised))

    def test_prepared_operation_survives_publication_failure_replay_and_newer_binding(self):
        activation = "sha256:" + "a" * 64
        revised_activation = "sha256:" + "b" * 64
        changed = self.story.model_copy(update={"hook": "Night"})
        with open_database(self.root) as db:
            create_test_execution(db, self.project, self.execution, "Input", ["s1"])
            operation, digest, replay = prepare_story_operation(db, self.execution, activation)
            self.assertEqual(operation, make_operation_id(self.execution, "storytell", activation, "generate"))
            self.assertIsNone(replay)
            artifact = str(uuid4())
            db.execute("CREATE TEMP TRIGGER reject_story BEFORE INSERT ON artifacts BEGIN SELECT RAISE(ABORT, 'db failed'); END")
            with self.assertRaisesRegex(sqlite3.IntegrityError, "db failed"):
                commit_story_operation(db, self.execution, activation, digest, artifact, self.story)
            self.assertEqual(db.execute("SELECT input_digest, artifact_id FROM story_operations").fetchone(), (digest, None))
            with self.assertRaisesRegex(ValueError, "not committed"):
                read_story(db, self.execution)
            db.execute("DROP TRIGGER reject_story")
        with open_database(self.root) as db:
            self.assertEqual(prepare_story_operation(db, self.execution, activation), (operation, digest, None))
            first, next_activation = commit_story_operation(db, self.execution, activation, digest, artifact, self.story)
            self.assertEqual(prepare_story_operation(db, self.execution, activation),
                             (operation, digest, (first, next_activation)))
            with self.assertRaisesRegex(ValueError, "activation"):
                commit_story_operation(db, self.execution, revised_activation, digest, str(uuid4()), self.story)
            with self.assertRaisesRegex(ValueError, "digest"):
                commit_story_operation(db, self.execution, activation, "sha256:" + "0" * 64, str(uuid4()), self.story)
            with self.assertRaisesRegex(ValueError, "inputs"):
                prepare_story_operation(db, self.execution, activation, feedback="different")
            revised_op, revised_digest, _ = prepare_story_operation(
                db, self.execution, revised_activation, prior_ref=first, feedback="Make it night", expected_revision=1)
            self.assertEqual(revised_op, make_operation_id(self.execution, "storytell", revised_activation, "revise"))
            with self.assertRaisesRegex(ValueError, "revision"):
                prepare_story_operation(db, self.execution, "sha256:" + "c" * 64,
                                        prior_ref=first, feedback="Again", expected_revision=0)
            second, second_next = commit_story_operation(db, self.execution, revised_activation, revised_digest,
                                                          str(uuid4()), changed)
            self.assertNotEqual(next_activation, second_next)
            self.assertEqual(read_story(db, self.execution)[0], second)
            with patch("backend.story_store._publish", side_effect=AssertionError("republished")):
                self.assertEqual(commit_story_operation(db, self.execution, activation, digest,
                                                        str(uuid4()), self.story), (first, next_activation))
            self.assertEqual(read_story(db, self.execution)[0], second)
            self.assertEqual(db.execute("SELECT binding_revision FROM execution_bindings").fetchone(), (2,))
        with open_database(self.root) as db:
            self.assertEqual(prepare_story_operation(db, self.execution, activation),
                             (operation, digest, (first, next_activation)))
            self.assertEqual(read_story(db, self.execution)[0], second)

    def test_v3_migration_keeps_both_story_revisions_and_prepares_new_operation(self):
        self.root.mkdir()
        first_id, second_id = str(uuid4()), str(uuid4())
        revised = self.story.model_copy(update={"hook": "Night"})
        with closing(sqlite3.connect(self.root / DATABASE_NAME)) as old:
            old.executescript(f"PRAGMA application_id={APPLICATION_ID}; PRAGMA user_version=3; {STORY_SCHEMA}")
            with old:
                old.execute("INSERT INTO executions VALUES (?,?,?,?)", (self.execution, self.project, "Input", '["s1"]'))
                for artifact_id, operation, story in ((first_id, self.operation, self.story),
                                                       (second_id, make_operation_id(self.execution, "storytell", "sha256:" + "b" * 64, "revise"), revised)):
                    body = canonical_json(story)
                    digest = sha256_digest(body)
                    path = self.root / "projects" / self.project / "artifacts" / f"{artifact_id}.{digest[7:]}.json"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(body)
                    old.execute("INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)", (
                        artifact_id, self.execution, operation, digest,
                        f"kinodel://projects/{self.project}/artifacts/{artifact_id}", "story", "1", "storytell"))
                old.execute("INSERT INTO execution_bindings VALUES (?,?,?,?)", (self.execution, "story", second_id, 2))
        with open_database(self.root) as db:
            self.assertEqual(read_story(db, self.execution, artifact_id=first_id)[1], self.story)
            self.assertEqual(read_story(db, self.execution), (read_story(db, self.execution, artifact_id=second_id)[0], revised))
            self.assertIsNone(prepare_story_operation(db, self.execution, "sha256:" + "c" * 64,
                                prior_ref=read_story(db, self.execution)[0], feedback="More night", expected_revision=2)[2])

    def test_v4_migration_preserves_prepared_operation(self):
        self.root.mkdir()
        activation = "sha256:" + "a" * 64
        operation = make_operation_id(self.execution, "storytell", activation, "generate")
        with closing(sqlite3.connect(self.root / DATABASE_NAME)) as old:
            old.executescript(f"PRAGMA application_id={APPLICATION_ID}; PRAGMA user_version=4; "
                              f"{STORY_SCHEMA} {OPERATION_SCHEMA}")
            with old:
                old.execute("INSERT INTO executions VALUES (?,?,?,?)", (self.execution, self.project, "Idea", '["s1"]'))
                old.execute("INSERT INTO story_operations VALUES (?,?,?,?,?,?,?,?)",
                            (operation, self.execution, activation, "sha256:" + "b" * 64,
                             '["pinned"]', None, None, None))
        with open_database(self.root) as db:
            self.assertEqual(db.execute("SELECT operation_id,input_digest,prepared_inputs FROM story_operations").fetchone(),
                             (operation, "sha256:" + "b" * 64, '["pinned"]'))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM review_requests").fetchone(), (0,))


if __name__ == "__main__":
    unittest.main()
