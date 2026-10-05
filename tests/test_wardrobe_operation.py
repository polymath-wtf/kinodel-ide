"""Storage acceptance only: the synthetic approval handoff is NOT graph acceptance.

Every execution is created from scratch. Existing review prepare/bind/accept are
real; only the future applied-approval receipt is seeded transactionally. No old
execution is retagged, no terminal receipt is removed, and HTTP is always mocked.
"""

from contextlib import closing
from functools import partial
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx

from backend import database, openrouter_wardrobe as adapter
from backend.characters import CharacterBio, CharacterRepository
from backend.domain import (OwnerResponseV1, StoryTextInputV1, StoryV2, canonical_json,
                            sha256_digest)
from backend.openrouter import SelectedCharacter, StoryOwnerConfigV2, encode
from backend.review_store import (_digest, accept_story_decision, bind_story_wait,
                                  prepare_story_review)
from backend.story_start import _payload_digest
from backend.story_store import commit_story_operation, prepare_story_operation, read_story
from tests.test_characters import image_input
from tests.test_wardrobe_openrouter import MODEL, capability, envelope, supplied_input


GRAPH_ID = "kinodel.story-wardrobe"
GRAPH_DIGEST = sha256_digest(b"kinodel.story-wardrobe.v1:OpenRouter+frozen-storytell-v2+text-input+generated-cast>storytell>story_prepare_review>story_wait>story_apply>wardrobe>END|clarify+revise>storytell")


class WardrobeOperationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel wardrobe operation ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "data"
        self.library = Path(temporary.name) / "characters"
        self.project, self.execution = str(uuid4()), str(uuid4())
        self.requests = []
        environment = patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret", "LLM_MODEL": MODEL})
        environment.start()
        self.addCleanup(environment.stop)

    def modules(self):
        self.assertIsNotNone(importlib.util.find_spec("backend.wardrobe_operation"),
                             "Restart-safe Wardrobe operation is absent")
        from backend import wardrobe_operation, wardrobe_store
        return wardrobe_operation, wardrobe_store

    def transport(self, output=None, before_post=None):
        def respond(request):
            self.requests.append(request)
            if request.method == "GET":
                return httpx.Response(200, json={"data": [capability()]})
            if before_post:
                before_post(request)
            if callable(output):
                return output(request)
            if output is not None:
                return httpx.Response(200, json=output)
            task = json.loads(json.loads(request.content)["messages"][1]["content"][0]["text"])
            subject = task["narrative_input"]["subjects"][0]["subject_id"]
            return httpx.Response(200, json=envelope({"status": "ready", "explanation": None,
                "plan": {"direction": {"appearance": "Warm silhouette", "wardrobe": "Blue coat",
                    "environment": "Rainy street", "lighting": "Soft daylight", "palette": ["blue"],
                    "must_preserve": [], "prohibited_drift": []},
                    "units": [{"unit_key": "hero portrait", "subject_ids": [subject], "role": "portrait",
                        "purpose": "Identity", "framing": "Close-up", "drawable_content": "Person in blue coat",
                        "image_prompt": "A person in a blue coat under soft daylight.",
                        "preserve": [], "ignore": [], "references": []}]}}))
        return patch("backend.openrouter_client.httpx.AsyncClient",
                     partial(httpx.AsyncClient, transport=httpx.MockTransport(respond)))

    def fixture(self, db, *, selected=False, apply=True, graph_id=GRAPH_ID):
        subjects = [{"subject_id": "hero", "description": "A warm traveler"}]
        cards = []
        if selected:
            repo = CharacterRepository(self.library)
            ref = repo.save(CharacterBio(name="Лея", vibe="Blue coat"),
                            [image_input(), image_input(color="blue")], mutation_id="create").ref
            cards = [SelectedCharacter(ref=ref, character=repo.read_exact(ref))]
            subjects = [item.narrative_subject().model_dump(mode="json") for item in cards]
        brief = StoryTextInputV1(user_vibe="Return a ribbon", subjects=subjects, shot_duration_ms=5000)
        from backend.domain import StorytellResultV2
        config = StoryOwnerConfigV2(adapter_version="2", model=MODEL, brief=brief,
            selected_characters=cards, system_prompt="Frozen Story instruction", result_schema=StorytellResultV2.model_json_schema(),
            clarification_schema=OwnerResponseV1.model_json_schema(), prompt_digest=sha256_digest(b"Frozen Story instruction"),
            timeout_seconds=60, max_tokens=8192, max_attempts=2, repair_limit=1, reasoning_effort="low")
        frozen = canonical_json(config).decode()
        start_digest = _payload_digest(brief.user_vibe, ["s1"], frozen)
        db.execute("INSERT INTO executions (execution_id,project_id,input_message,shot_ids,client_key,start_digest,"
                   "graph_id,graph_version,graph_digest,owner_config) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (self.execution, self.project, brief.user_vibe, '["s1"]', "new-synthetic", start_digest,
                    graph_id, "1", GRAPH_DIGEST, frozen))
        db.execute("INSERT INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,status) "
                   "VALUES (?,?, 'start', ?, ?, 'completed')", (str(uuid4()), self.execution, self.execution, start_digest))
        activation = sha256_digest(b"synthetic new Story activation")
        _, digest, _ = prepare_story_operation(db, self.execution, activation)
        story = StoryV2(schema_id="story", schema_version="2", hook="A ribbon", story="A traveler returns a ribbon.",
            generated_characters=[{"subject_id": "robot", "description": "Tiny brass robot"}],
            shots=[{"shot_id": "s1", "action": "Return ribbon", "narrative_function": "Resolve loss",
                    "subject_ids": [subjects[0]["subject_id"], "robot"], "state_before": "Lost", "state_after": "Found"}])
        ref, trigger = commit_story_operation(db, self.execution, activation, digest, str(uuid4()), story)
        review = prepare_story_review(db, self.execution, trigger, ref, 1)
        bind_story_wait(db, self.execution, review.request_id, "fixture-cp", "fixture-task", "fixture-interrupt")
        decision = accept_story_decision(db, self.execution, review.request_id, review.digest, 1,
                                         "explicit-approve", "approve", None)
        if apply:
            # Only the future business handoff receipt; current apply would end a text run.
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE review_requests SET applied_activation=? WHERE request_id=?",
                       (_digest("kinodel.story-review-apply.v1", review.request_id, decision.decision_id, "approve"), review.request_id))
            db.execute("COMMIT")
        return review, ref, cards

    async def test_typed_invalid_output_and_frozen_repair_request(self):
        with self.transport(output={"choices": []}):
            frozen = await adapter.prepare_wardrobe_request(supplied_input(), {})
            try:
                await adapter.complete_wardrobe(frozen)
            except ValueError as error:
                self.assertEqual(type(error).__name__, "WardrobeInvalidOutput")
            else:
                self.fail("Malformed output was accepted")
        self.assertTrue(hasattr(adapter, "prepare_wardrobe_repair"), "Frozen repair builder is absent")
        instruction = "The prior output was invalid. Return complete JSON matching the supplied schema."
        repair = adapter.prepare_wardrobe_repair(frozen, instruction)
        base = json.loads(adapter.read_wardrobe_config(frozen).base_request)
        self.assertEqual(json.loads(repair), {**base, "messages": base["messages"] + [{"role": "user", "content": instruction}]})
        with self.transport(output=envelope()), patch.object(adapter, "REPAIR_INSTRUCTION", "Changed instruction"):
            await adapter.complete_wardrobe(frozen, repair_instruction=instruction)
        self.assertEqual(self.requests[-1].content, repair.encode())

    async def test_commit_reopen_replay_and_original_images(self):
        operation, store = self.modules()
        with database.open_database(self.root) as db:
            review, story_ref, cards = self.fixture(db, selected=True)
            def reserved(_):
                self.assertFalse(db.in_transaction)
                self.assertEqual(db.execute("SELECT owner_attempts FROM wardrobe_operations").fetchone(), (1,))
                self.assertIsNotNone(db.execute("SELECT repair_request FROM wardrobe_operations").fetchone()[0])
            with self.transport(before_post=reserved):
                result, next_activation = await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            self.assertEqual((result.schema_id, result.produced_by_stage), ("visual_anchor_plan", "wardrobe"))
            self.assertEqual(store.read_wardrobe_plan(db, self.execution)[1].narrative_ref, story_ref)
            self.assertEqual(db.execute("SELECT slot,binding_revision FROM execution_bindings ORDER BY slot").fetchall(),
                             [("story", 1), ("wardrobe_plan", 1)])
            config = adapter.read_wardrobe_config(db.execute("SELECT owner_config FROM wardrobe_operations").fetchone()[0])
            supplied = config.wardrobe_input
            self.assertEqual(supplied.selected_characters, [item.ref for item in cards])
            self.assertEqual(supplied.narrative_input.model_dump(mode="json"),
                             json.loads(db.execute("SELECT owner_config FROM executions").fetchone()[0])["brief"])
            self.assertEqual([e.ref.digest for e in supplied.image_evidence], [image.digest for image in cards[0].character.images])
            self.assertEqual([e.role for e in supplied.image_evidence], ["portrait", "portrait"])
            self.assertEqual(supplied.text_context[0].content, cards[0].narrative_subject().description)
            self.assertEqual([c.subject_id for c in supplied.story.generated_characters], ["robot"])
            self.assertEqual(db.execute("SELECT * FROM execution_outcomes").fetchall(), [])
        self.library.rename(self.library.with_name("parked"))
        with database.open_database(self.root) as db, patch.dict(os.environ, {"LLM_MODEL": "", "OPENROUTER_API_KEY": ""}), \
                patch.object(CharacterRepository, "read_image", side_effect=AssertionError("Replay read library")), \
                patch.object(adapter, "prepare_wardrobe_request", side_effect=AssertionError("Replay prepared")), \
                patch.object(adapter, "complete_wardrobe", side_effect=AssertionError("Replay called")):
            self.assertEqual(await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library), (result, next_activation))
            db.execute("UPDATE execution_bindings SET binding_revision=2 WHERE slot='wardrobe_plan'")
            self.assertEqual(await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library), (result, next_activation))
            self.assertEqual(db.execute("SELECT binding_revision FROM execution_bindings WHERE slot='wardrobe_plan'").fetchone(), (2,))
            path = store._destination(db, self.project, result.artifact_id, result.digest)
            path.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "integrity"):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            path.unlink()
            with self.assertRaises(FileNotFoundError):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)

    async def test_nonready_commits_without_repair_or_plan(self):
        operation, _ = self.modules()
        for status in ("needs_input", "out_of_scope"):
            self.root = self.root.with_name(status)
            self.execution = str(uuid4())
            with database.open_database(self.root) as db:
                review, _, _ = self.fixture(db)
                with self.transport(envelope({"status": status, "plan": None, "explanation": "Need direction"})):
                    result = await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
                self.assertEqual(result[0], OwnerResponseV1(status=status, explanation="Need direction"))
                self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs FROM wardrobe_operations").fetchone(), (1, 0))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_bindings WHERE slot='wardrobe_plan'").fetchone(), (0,))
                with patch.object(adapter, "complete_wardrobe", side_effect=AssertionError("Nonready replay called")):
                    self.assertEqual(await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library), result)

    async def test_hard_attempt_budget_survives_transport_and_reopen(self):
        operation, store = self.modules()
        with database.open_database(self.root) as db:
            review, _, _ = self.fixture(db)
            with self.transport(lambda _: httpx.Response(503)), self.assertRaises(adapter.WardrobeOwnerUnavailable):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
        with database.open_database(self.root) as db:
            with self.transport(lambda _: httpx.Response(503)), patch.dict(os.environ, {"LLM_MODEL": "other/model"}), \
                    patch.object(adapter, "prepare_wardrobe_request", side_effect=AssertionError("Retry prepared")), \
                    self.assertRaises(adapter.WardrobeOwnerUnavailable):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs FROM wardrobe_operations").fetchone(), (2, 0))
            with self.transport(), self.assertRaises(store.WardrobeAttemptBudgetExhausted):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
        posts = [r.content for r in self.requests if r.method == "POST"]
        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0], posts[1])

    async def test_invalid_output_repairs_once_and_never_posts_third(self):
        operation, _ = self.modules()
        with database.open_database(self.root) as db:
            review, _, _ = self.fixture(db)
            with self.transport({"choices": []}), self.assertRaises(adapter.WardrobeInvalidOutput):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs FROM wardrobe_operations").fetchone(), (2, 1))
        with database.open_database(self.root) as db, self.transport(), self.assertRaises(adapter.WardrobeInvalidOutput):
            await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
        self.assertEqual(len([r for r in self.requests if r.method == "POST"]), 2)

    async def test_pending_candidate_finishes_after_file_before_db_failure(self):
        operation, store = self.modules()
        with database.open_database(self.root) as db:
            review, _, _ = self.fixture(db)
            db.execute("CREATE TEMP TRIGGER stop_plan BEFORE INSERT ON artifacts "
                       "WHEN NEW.schema_id='visual_anchor_plan' BEGIN SELECT RAISE(ABORT, 'commit gap'); END")
            with self.transport(), self.assertRaisesRegex(sqlite3.IntegrityError, "commit gap"):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            self.assertIsNotNone(db.execute("SELECT candidate_body FROM wardrobe_operations").fetchone()[0])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_bindings WHERE slot='wardrobe_plan'").fetchone(), (0,))
        with database.open_database(self.root) as db, patch.object(adapter, "complete_wardrobe", side_effect=AssertionError("Candidate recovery called")):
            result, _ = await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            self.assertEqual(store.read_wardrobe_plan(db, self.execution)[0], result)
            self.assertEqual(db.execute("SELECT owner_attempts FROM wardrobe_operations").fetchone(), (1,))

    async def test_authority_rejects_old_unapplied_terminal_and_tampered_lineage_before_http(self):
        operation, _ = self.modules()
        for case in ("old", "unapplied", "terminal", "cancel", "start", "work", "resume", "approval", "binding", "body", "output"):
            self.root = self.root.with_name(case)
            self.execution = str(uuid4())
            with self.subTest(case=case), database.open_database(self.root) as db:
                review, ref, _ = self.fixture(db, apply=case != "unapplied",
                                             graph_id="kinodel.live-story" if case == "old" else GRAPH_ID)
                if case == "terminal":
                    db.execute("INSERT INTO execution_outcomes VALUES (?, 'completed', ?, ?)", (self.execution, review.request_id, ref.artifact_id))
                elif case == "cancel":
                    self.cancel(db)
                elif case == "start":
                    db.execute("UPDATE executions SET start_digest=?", (sha256_digest(b"wrong"),))
                elif case == "work":
                    db.execute("UPDATE execution_work SET payload_digest=? WHERE kind='start'", (sha256_digest(b"wrong"),))
                elif case == "resume":
                    db.execute("UPDATE execution_work SET payload_digest=? WHERE kind='resume'", (sha256_digest(b"wrong"),))
                elif case == "approval":
                    db.execute("UPDATE review_requests SET decision_digest=?", (sha256_digest(b"wrong"),))
                elif case == "binding":
                    db.execute("UPDATE execution_bindings SET binding_revision=2 WHERE slot='story'")
                elif case == "body":
                    from backend.story_store import _destination
                    _destination(db, self.project, ref.artifact_id, ref.digest).write_bytes(b"bad Story")
                elif case == "output":
                    db.execute("INSERT INTO execution_bindings VALUES (?, 'wardrobe_plan', ?, 1)", (self.execution, ref.artifact_id))
                before = len(self.requests)
                with self.transport(), self.assertRaises(ValueError):
                    await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
                self.assertEqual(len(self.requests), before)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM wardrobe_operations").fetchone(), (0,))
                if case == "terminal":
                    self.assertEqual(db.execute("SELECT outcome FROM execution_outcomes").fetchone(), ("completed",))

    def cancel(self, db):
        work = str(uuid4())
        db.execute("INSERT INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,status) "
                   "VALUES (?,?, 'cancel', 'cancel-command', ?, 'pending')", (work, self.execution, sha256_digest(b"cancel")))
        db.execute("INSERT INTO execution_controls VALUES (?, 'cancel-command', 'cancel', ?, NULL)", (self.execution, work))

    async def test_reservation_and_repair_selection_survive_interruption(self):
        operation, store = self.modules()
        with database.open_database(self.root) as db:
            review, _, _ = self.fixture(db, selected=True)
            reserve = store.reserve_wardrobe_attempt
            def crash_before_repair(*args):
                if db.execute("SELECT owner_attempts,owner_repairs FROM wardrobe_operations").fetchone() == (1, 1):
                    raise RuntimeError("process interruption")
                return reserve(*args)
            with self.transport({"choices": []}), patch.object(store, "reserve_wardrobe_attempt", side_effect=crash_before_repair), \
                    self.assertRaisesRegex(RuntimeError, "interruption"):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            repair = db.execute("SELECT repair_request FROM wardrobe_operations").fetchone()[0]
        self.library.rename(self.library.with_name("parked"))
        with database.open_database(self.root) as db, self.transport(), patch.dict(os.environ, {"LLM_MODEL": "other/model"}), \
                patch.object(adapter, "REPAIR_INSTRUCTION", "changed"), patch("pathlib.Path.read_text", side_effect=AssertionError("Retry read prompt")), \
                patch.object(CharacterRepository, "read_image", side_effect=AssertionError("Retry read originals")):
            await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs FROM wardrobe_operations").fetchone(), (2, 1))
        self.assertEqual(self.requests[-1].content, repair.encode())

    async def test_crash_after_reservation_consumes_attempt_without_changing_request(self):
        operation, store = self.modules()
        with database.open_database(self.root) as db:
            review, _, _ = self.fixture(db)
            reserve = store.reserve_wardrobe_attempt
            def crash(*args):
                reserve(*args)
                raise RuntimeError("reserved before process interruption")
            with self.transport(), patch.object(store, "reserve_wardrobe_attempt", side_effect=crash), self.assertRaises(RuntimeError):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            request = adapter.read_wardrobe_config(db.execute("SELECT owner_config FROM wardrobe_operations").fetchone()[0]).base_request
            self.assertEqual(db.execute("SELECT owner_attempts FROM wardrobe_operations").fetchone(), (1,))
            self.assertEqual([r.method for r in self.requests], ["GET"])
        with database.open_database(self.root) as db, self.transport():
            await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            self.assertEqual(db.execute("SELECT owner_attempts FROM wardrobe_operations").fetchone(), (2,))
        self.assertEqual(self.requests[-1].content, request.encode())

    async def test_oversized_completion_is_repaired_but_http_rejection_is_not(self):
        operation, _ = self.modules()
        count = 0
        def oversized_then_valid(_):
            nonlocal count
            count += 1
            return httpx.Response(200, content=b"x" * (1024 * 1024 + 1)) if count == 1 else httpx.Response(200, json=envelope())
        with database.open_database(self.root) as db:
            review, _, _ = self.fixture(db)
            with self.transport(oversized_then_valid):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs FROM wardrobe_operations").fetchone(), (2, 1))
        self.root = self.root.with_name("rejected")
        self.execution = str(uuid4())
        with database.open_database(self.root) as db:
            review, _, _ = self.fixture(db)
            with self.transport(lambda _: httpx.Response(400)), self.assertRaises(ValueError) as raised:
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            self.assertNotIsInstance(raised.exception, adapter.WardrobeInvalidOutput)
            self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs FROM wardrobe_operations").fetchone(), (1, 0))

    async def test_cancel_after_http_and_before_commit_prevents_binding(self):
        operation, store = self.modules()
        with database.open_database(self.root) as db:
            review, _, _ = self.fixture(db)
            with self.transport(before_post=lambda _: self.cancel(db)), self.assertRaisesRegex(ValueError, "cancelling"):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            self.assertEqual(db.execute("SELECT candidate_body FROM wardrobe_operations").fetchone(), (None,))
        self.root = self.root.with_name("cancel-at-publication")
        self.execution = str(uuid4())
        with database.open_database(self.root) as db:
            review, _, _ = self.fixture(db)
            publish = store._publish
            def cancel_after_publish(*args):
                publish(*args)
                self.cancel(db)
            with self.transport(), patch.object(store, "_publish", side_effect=cancel_after_publish), self.assertRaisesRegex(ValueError, "cancelling"):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            self.assertIsNotNone(db.execute("SELECT candidate_body FROM wardrobe_operations").fetchone()[0])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_bindings WHERE slot='wardrobe_plan'").fetchone(), (0,))

    async def test_persisted_config_request_and_candidate_tampering_fail_before_post(self):
        operation, store = self.modules()
        with database.open_database(self.root) as db:
            review, _, _ = self.fixture(db)
            with self.transport(), patch.object(store, "_publish", side_effect=OSError("disk full")), self.assertRaises(OSError):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            columns = ("input_digest", "prepared_inputs", "owner_config", "repair_request", "candidate_body", "candidate_digest")
            for column in columns:
                original = db.execute(f"SELECT {column} FROM wardrobe_operations").fetchone()[0]
                db.execute(f"UPDATE wardrobe_operations SET {column}='corrupt'")
                with self.subTest(column=column), self.transport(), self.assertRaises(ValueError):
                    await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
                db.execute(f"UPDATE wardrobe_operations SET {column}=?", (original,))
            self.assertEqual(len([r for r in self.requests if r.method == "POST"]), 1)

    async def test_missing_selected_images_block_without_omission(self):
        operation, _ = self.modules()
        with database.open_database(self.root) as db:
            review, _, _ = self.fixture(db, selected=True)
            self.library.rename(self.library.with_name("parked"))
            with self.transport(), self.assertRaises((ValueError, FileNotFoundError)):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            self.assertEqual(self.requests, [])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM wardrobe_operations").fetchone(), (0,))

    async def test_repair_flag_tampering_does_not_change_prepared_request_selection(self):
        operation, store = self.modules()
        with database.open_database(self.root) as db:
            review, _, _ = self.fixture(db)
            reserve = store.reserve_wardrobe_attempt
            def pause(*args):
                if db.execute("SELECT owner_attempts FROM wardrobe_operations").fetchone() == (1,):
                    raise RuntimeError("after rejected attempt")
                return reserve(*args)
            with self.transport({"choices": []}), patch.object(store, "reserve_wardrobe_attempt", side_effect=pause), self.assertRaises(RuntimeError):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            db.execute("UPDATE wardrobe_operations SET owner_repairs=0")
            with self.transport(), self.assertRaisesRegex(ValueError, "repair"):
                await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
            self.assertEqual(len([r for r in self.requests if r.method == "POST"]), 1)

    async def test_process_death_after_reservation_and_publication_recovers_same_operation(self):
        operation, store = self.modules()
        child = """
import os, sys
from pathlib import Path
from backend.database import open_database
from backend import wardrobe_store as store
with open_database(Path(sys.argv[1])) as db:
    operation_id = db.execute('SELECT operation_id FROM wardrobe_operations').fetchone()[0]
    if sys.argv[2] == 'reserve':
        store.reserve_wardrobe_attempt(db, operation_id)
        os._exit(23)
    publish = store._publish
    def die_after_publish(*args):
        publish(*args)
        os._exit(23)
    store._publish = die_after_publish
    store.commit_wardrobe_operation(db, operation_id)
raise AssertionError('crash hook not reached')
"""
        for boundary in ("reserve", "publish"):
            self.root = self.root.with_name(f"process-{boundary}")
            self.execution = str(uuid4())
            with self.subTest(boundary=boundary), database.open_database(self.root) as db:
                review, _, _ = self.fixture(db)
                target = "reserve_wardrobe_attempt" if boundary == "reserve" else "_publish"
                with self.transport(), patch.object(store, target, side_effect=RuntimeError("pause parent")), self.assertRaises(RuntimeError):
                    await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
                frozen = db.execute("SELECT operation_id,input_digest,owner_config,repair_request,candidate_body FROM wardrobe_operations").fetchone()
            died = subprocess.run([sys.executable, "-B", "-c", child, str(self.root), boundary], capture_output=True, text=True, timeout=20)
            self.assertEqual(died.returncode, 23, died.stderr)
            with database.open_database(self.root) as db, self.transport():
                self.assertEqual(db.execute("SELECT operation_id,input_digest,owner_config,repair_request,candidate_body FROM wardrobe_operations").fetchone(), frozen)
                before = len([r for r in self.requests if r.method == "POST"])
                result, _ = await operation.produce_wardrobe_operation(db, self.execution, review.request_id, character_root=self.library)
                self.assertEqual(store.read_wardrobe_plan(db, self.execution)[0], result)
                self.assertEqual(db.execute("SELECT owner_attempts FROM wardrobe_operations").fetchone(), (2 if boundary == "reserve" else 1,))
                self.assertEqual(len([r for r in self.requests if r.method == "POST"]) - before, 1 if boundary == "reserve" else 0)


class WardrobeMigrationTests(unittest.TestCase):
    def test_v12_migration_preserves_history_and_rolls_back(self):
        with tempfile.TemporaryDirectory(prefix="kinodel wardrobe migration ") as temporary:
            root = Path(temporary)
            path = root / database.DATABASE_NAME
            script = (database.STORY_SCHEMA + database.OPERATION_SCHEMA + database.REVIEW_SCHEMA + database.START_SCHEMA
                      + database.RUNNER_SCHEMA + database.CONTROL_SCHEMA + database.DISCUSSION_SCHEMA
                      + database.LIVE_STORY_SCHEMA + database.STORY_V2_SCHEMA + database.STORY_DIAGNOSTIC_SCHEMA)
            with closing(sqlite3.connect(path, isolation_level=None)) as old:
                old.executescript(f"PRAGMA application_id={database.APPLICATION_ID}; {script} PRAGMA user_version=12;")
                execution, project, artifact = str(uuid4()), str(uuid4()), str(uuid4())
                old.execute("INSERT INTO executions (execution_id,project_id,input_message,shot_ids) VALUES (?,?, 'Historic', '[\"s1\"]')", (execution, project))
                old.execute("INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)", (artifact, execution, sha256_digest(b"old operation"), sha256_digest(b"old body"), f"kinodel://projects/{project}/artifacts/{artifact}", "story", "2", "storytell"))
                old.execute("INSERT INTO execution_bindings VALUES (?,?,?,1)", (execution, "story", artifact))
                old.execute("INSERT INTO execution_outcomes VALUES (?, 'completed', 'old approval', ?)", (execution, artifact))
                tables = ("executions", "artifacts", "execution_bindings", "execution_outcomes")
                frozen = {table: old.execute(f"SELECT rowid,* FROM {table}").fetchall() for table in tables}
            with database.open_database(root) as db:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone(), (13,), "Wardrobe schema migration is absent")
                for table in tables:
                    self.assertEqual(db.execute(f"SELECT rowid,* FROM {table}").fetchall(), frozen[table])
                self.assertEqual(db.execute("SELECT COUNT(*) FROM wardrobe_operations").fetchone(), (0,))
                self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
            # A separate fresh v12 root exercises rollback, never downgrade an upgraded DB.
            rollback = root / "rollback"
            rollback.mkdir()
            with closing(sqlite3.connect(rollback / database.DATABASE_NAME, isolation_level=None)) as old:
                old.executescript(f"PRAGMA application_id={database.APPLICATION_ID}; {script} PRAGMA user_version=12;")
                before = database._schema(old)
            with patch.object(database, "WARDROBE_SCHEMA", database.WARDROBE_SCHEMA + "SELECT * FROM missing_table;"):
                with self.assertRaises(sqlite3.OperationalError):
                    with database.open_database(rollback):
                        self.fail("Partial migration accepted")
            with closing(sqlite3.connect(rollback / database.DATABASE_NAME)) as old:
                self.assertEqual(old.execute("PRAGMA user_version").fetchone(), (12,))
                self.assertEqual(database._schema(old), before)
            with database.open_database(rollback) as db:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone(), (13,))


if __name__ == "__main__":
    unittest.main()
