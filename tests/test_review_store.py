import sqlite3
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from backend.database import open_database
from backend.domain import StoryV1, make_operation_id
from backend.review_store import (accept_story_decision, apply_story_decision,
                                  bind_story_wait, prepare_story_review)
from backend.story_store import create_test_execution, read_story, save_story


class StoryReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel review ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "data"
        self.project, self.execution = str(uuid4()), str(uuid4())
        self.activation = "sha256:" + "a" * 64
        self.story = StoryV1(
            schema_id="story", schema_version="1", hook="Light", story="A fox appears.",
            shots=[dict(shot_id="s1", action="Fox appears", narrative_function="Arrival",
                        subject_ids=[], state_before="Dark", state_after="Light")],
        )
        with open_database(self.root) as db:
            create_test_execution(db, self.project, self.execution, "Idea", ["s1"])
            self.ref = save_story(db, self.execution, make_operation_id(
                self.execution, "storytell", self.activation, "generate"), str(uuid4()), self.story)

    def test_request_is_pinned_to_exact_story_and_reused_after_reopen(self):
        with open_database(self.root) as db:
            request = prepare_story_review(db, self.execution, self.activation, self.ref, 1)
            self.assertEqual(prepare_story_review(db, self.execution, self.activation, self.ref, 1), request)
            with self.assertRaisesRegex(ValueError, "subject"):
                prepare_story_review(db, self.execution, self.activation,
                                     self.ref.model_copy(update={"project_id": str(uuid4())}), 1)
            with self.assertRaisesRegex(ValueError, "activation"):
                prepare_story_review(db, self.execution, "sha256:" + "Z" * 64, self.ref, 1)
            with self.assertRaisesRegex(ValueError, "conflict"):
                prepare_story_review(db, self.execution, self.activation, self.ref, 2)
            bind_story_wait(db, self.execution, request.request_id, "cp1", "task1", "interrupt1")
            bind_story_wait(db, self.execution, request.request_id, "cp1", "task1", "interrupt1")
            with self.assertRaisesRegex(ValueError, "wait"):
                bind_story_wait(db, self.execution, request.request_id, "cp2", "task2", "interrupt2")
        with open_database(self.root) as db:
            self.assertEqual(prepare_story_review(db, self.execution, self.activation, self.ref, 1), request)
            self.assertEqual(read_story(db, self.execution)[0], self.ref)

    def test_decision_dedup_stale_and_exact_apply(self):
        with open_database(self.root) as db:
            request = prepare_story_review(db, self.execution, self.activation, self.ref, 1)
            with self.assertRaisesRegex(ValueError, "wait"):
                accept_story_decision(db, self.execution, request.request_id, request.digest, 1,
                                      "key1", "revise", "Make it dark")
            bind_story_wait(db, self.execution, request.request_id, "cp1", "task1", "interrupt1")
            with self.assertRaisesRegex(ValueError, "revision"):
                accept_story_decision(db, self.execution, request.request_id, request.digest, 2,
                                      "key1", "approve", None)
            with self.assertRaisesRegex(ValueError, "message"):
                accept_story_decision(db, self.execution, request.request_id, request.digest, 1,
                                      "key1", "revise", "")
            decision = accept_story_decision(db, self.execution, request.request_id, request.digest, 1,
                                             "key1", "revise", "Make it dark")
            self.assertEqual(accept_story_decision(db, self.execution, request.request_id, request.digest, 1,
                                                   "key1", "revise", "Make it dark"), decision)
            with self.assertRaisesRegex(ValueError, "conflict"):
                accept_story_decision(db, self.execution, request.request_id, request.digest, 1,
                                      "key1", "approve", None)
            with self.assertRaisesRegex(ValueError, "accepted"):
                accept_story_decision(db, self.execution, request.request_id, request.digest, 1,
                                      "key2", "approve", None)
            next_activation = apply_story_decision(db, self.execution, request.request_id, decision.decision_id)
            self.assertEqual(apply_story_decision(db, self.execution, request.request_id, decision.decision_id), next_activation)
            self.assertEqual(read_story(db, self.execution)[0], self.ref)
            with self.assertRaisesRegex(ValueError, "applied"):
                accept_story_decision(db, self.execution, request.request_id, request.digest, 1,
                                      "key3", "approve", None)
        with open_database(self.root) as db:
            self.assertEqual(apply_story_decision(db, self.execution, request.request_id, decision.decision_id), next_activation)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_work").fetchone(), (1,))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM review_requests").fetchone(), (1,))

    def test_new_question_on_same_subject_does_not_reuse_old_decision(self):
        with open_database(self.root) as db:
            first = prepare_story_review(db, self.execution, self.activation, self.ref, 1)
            bind_story_wait(db, self.execution, first.request_id, "cp1", "task1", "interrupt1")
            answer = accept_story_decision(db, self.execution, first.request_id, first.digest, 1,
                                           "key", "clarify", "Why?")
            apply_story_decision(db, self.execution, first.request_id, answer.decision_id)
            second = prepare_story_review(db, self.execution, "sha256:" + "b" * 64,
                                          self.ref, 1, previous_request_id=first.request_id)
            self.assertEqual(second.revision, 2)
            self.assertNotEqual(first.digest, second.digest)
            bind_story_wait(db, self.execution, second.request_id, "cp2", "task2", "interrupt2")
            with self.assertRaisesRegex(ValueError, "stale"):
                accept_story_decision(db, self.execution, first.request_id, first.digest, 1,
                                      "new", "approve", None)
            self.assertEqual(accept_story_decision(db, self.execution, first.request_id, first.digest, 1,
                                                   "key", "clarify", "Why?"), answer)
            with self.assertRaisesRegex(ValueError, "conflict"):
                accept_story_decision(db, self.execution, second.request_id, second.digest, 1,
                                      "key", "approve", None)

    def test_approved_story_cannot_open_another_review(self):
        with open_database(self.root) as db:
            first = prepare_story_review(db, self.execution, self.activation, self.ref, 1)
            bind_story_wait(db, self.execution, first.request_id, "cp1", "task1", "interrupt1")
            decision = accept_story_decision(db, self.execution, first.request_id, first.digest, 1,
                                             "approved", "approve", None)
            apply_story_decision(db, self.execution, first.request_id, decision.decision_id)
            with self.assertRaisesRegex(ValueError, "approved"):
                prepare_story_review(db, self.execution, "sha256:" + "b" * 64, self.ref, 1,
                                     previous_request_id=first.request_id)

    def test_resume_work_failure_rolls_back_decision(self):
        with open_database(self.root) as db:
            request = prepare_story_review(db, self.execution, self.activation, self.ref, 1)
            bind_story_wait(db, self.execution, request.request_id, "cp1", "task1", "interrupt1")
            db.execute("CREATE TEMP TRIGGER reject_work BEFORE INSERT ON execution_work "
                       "BEGIN SELECT RAISE(ABORT, 'work unavailable'); END")
            with self.assertRaisesRegex(sqlite3.IntegrityError, "work unavailable"):
                accept_story_decision(db, self.execution, request.request_id, request.digest, 1,
                                      "key", "approve", None)
            self.assertEqual(db.execute("SELECT decision_id FROM review_requests").fetchone(), (None,))
            db.execute("DROP TRIGGER reject_work")
            decision = accept_story_decision(db, self.execution, request.request_id, request.digest, 1,
                                             "key", "approve", None)
            self.assertEqual(db.execute("SELECT resume_ref FROM execution_work").fetchone(), (decision.decision_id,))


if __name__ == "__main__":
    unittest.main()
