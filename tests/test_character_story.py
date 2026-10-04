"""Exact library selections frozen into live Story, with mocked provider transport."""

import asyncio
from functools import partial
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from backend.api import create_app, fixture_story
from backend.characters import CharacterBio, CharacterRepository
from backend.database import open_database
from backend.domain import StoryTextInputV1, canonical_json
from backend.openrouter import read_owner_config
from backend.review_store import accept_story_decision
from backend.saver import open_saver
from backend.story_runner import run_story_work
from backend.story_start import start_live_story
from tests.test_characters import image_input


class CharacterStoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel selected characters ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "data"
        self.library = Path(temporary.name) / "characters"
        self.repo = CharacterRepository(self.library)
        self.image = image_input()
        self.bio = CharacterBio(name="Лея", age="young adult", gender="woman", vibe="Warm, curious; loves rainy streets")
        self.ref = self.repo.save(self.bio, [self.image], mutation_id="create").ref
        self.card = self.repo.read_exact(self.ref)
        self.project = str(uuid4())
        self.brief = StoryTextInputV1(user_vibe="She returns a lost ribbon", subjects=[], shot_duration_ms=5000)
        self.requests = []
        environment = patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret", "LLM_MODEL": "test/model"})
        environment.start()
        self.addCleanup(environment.stop)

    def transport(self):
        def respond(request):
            if request.url.path.endswith("/models"):
                return httpx.Response(200, json={"data": [{"id": "test/model", "supported_parameters": ["response_format", "structured_outputs"]}]})
            payload = json.loads(request.content)
            self.requests.append(payload)
            task = json.loads(payload["messages"][1]["content"])
            story = fixture_story(task["brief"]["user_vibe"], task["shot_ids"], None, None).model_dump(mode="json")
            story.update(schema_version="2", generated_characters=[])
            story["shots"][0]["subject_ids"] = [subject["subject_id"] for subject in task["brief"]["subjects"]]
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"status": "ready", "story": story, "explanation": None})}}]})
        return patch("backend.openrouter.httpx.AsyncClient", partial(httpx.AsyncClient, transport=httpx.MockTransport(respond)))

    async def start(self, db, saver, refs=None, brief=None):
        return await start_live_story(db, saver, self.project, "start", ["s1"], brief or self.brief,
                                      character_refs=[self.ref] if refs is None else refs, character_root=self.library)

    async def test_exact_snapshot_survives_edit_reopen_missing_library_and_environment(self):
        with self.transport():
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await self.start(db, saver)
                    encoded = db.execute("SELECT owner_config FROM executions").fetchone()[0]
                    config = read_owner_config(encoded)
                    self.assertEqual(config.selected_characters[0].ref, self.ref)
                    self.assertEqual(config.selected_characters[0].character, self.card)
                    subject = config.brief.subjects[0]
                    self.assertEqual(subject.subject_id, self.ref.subject_id)
                    for text in (self.bio.name, self.bio.age, self.bio.gender, self.bio.vibe):
                        self.assertIn(text, subject.description)
                    self.repo.save(CharacterBio(name="New name", vibe="Different vibe"), [self.image], mutation_id="edit", subject_id=self.ref.subject_id, expected_revision=1)
            parked = self.library.with_name("parked")
            self.library.rename(parked)
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": ""}), patch.object(CharacterRepository, "read_exact", side_effect=AssertionError("replay rehydrated library")), patch("backend.openrouter.pin_story_owner", side_effect=AssertionError("replay pinned environment")):
                        self.assertEqual(await self.start(db, saver), receipt)
                    self.assertFalse(self.library.exists())
                    self.assertEqual(db.execute("SELECT owner_config FROM executions").fetchone()[0], encoded)
                    await run_story_work(db, saver, fixture_story)
                    from backend.story_reads import story_projection, story_activity
                    from backend.api import StoryProjection
                    projection = StoryProjection.model_validate(story_projection(db, receipt.execution_id)).model_dump(mode="json")
                    self.assertEqual(projection["submitted"]["text_brief"], config.brief.model_dump(mode="json"))
                    self.assertEqual(projection["submitted"]["selected_characters"], [{"ref": self.ref.model_dump(mode="json"), "character": self.card.model_dump(mode="json")}])
                    task = json.loads(self.requests[0]["messages"][1]["content"])
                    self.assertEqual(task["brief"], config.brief.model_dump(mode="json"))
                    self.assertEqual(task["context"]["selected_canon"], [{"kind": "character", "ref": self.ref.model_dump(mode="json")}])
                    self.assertNotIn("images", task["context"])
                    self.assertNotIn("data_base64", json.dumps(self.requests))
                    self.assertNotIn("image_url", json.dumps(self.requests))
                    self.assertEqual(story_activity(db, receipt.execution_id)["operations"][0]["input"], task)
                    self.assertEqual(canonical_json(read_owner_config(encoded)).decode(), encoded)
                    review = projection["review"]
                    self.assertIsNotNone(review)
                    accept_story_decision(db, receipt.execution_id, review["request_id"], review["digest"], review["binding_revision"], "edit-story", "revise", "Make the ending hopeful")
                    await run_story_work(db, saver, fixture_story)
                    revised_task = json.loads(self.requests[-1]["messages"][1]["content"])
                    self.assertEqual(revised_task["brief"], task["brief"])
                    self.assertEqual(revised_task["context"]["selected_canon"], task["context"]["selected_canon"])
                    self.assertEqual(revised_task["action"], "revise")
        self.assertEqual(len(self.requests), 2)

    async def test_changed_exact_refs_conflict_even_with_identical_bio_and_no_rehydration(self):
        with self.transport():
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await self.start(db, saver)
                    same_bio = self.repo.save(self.bio, [self.image], mutation_id="same-bio", subject_id=self.ref.subject_id, expected_revision=1).ref
                    with patch.object(CharacterRepository, "read_exact", side_effect=AssertionError("conflict rehydrated")), patch("backend.openrouter.pin_story_owner", side_effect=AssertionError("conflict checked credentials")):
                        for refs, brief in (([same_bio], self.brief), ([], self.brief), ([self.ref], self.brief.model_copy(update={"subjects": [{"subject_id": "extra", "description": "Manual subject"}]}))):
                            with self.subTest(refs=refs), self.assertRaisesRegex(ValueError, "client key conflicts"):
                                await self.start(db, saver, refs, brief)
                    self.assertEqual(await self.start(db, saver), receipt)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM executions").fetchone(), (1,))

    async def test_deleted_exact_ref_remains_startable_and_existing_execution_stays_frozen(self):
        with self.transport():
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    original = await self.start(db, saver)
                    encoded = db.execute("SELECT owner_config FROM executions").fetchone()[0]
                    self.repo.delete(mutation_id="delete", subject_id=self.ref.subject_id, expected_revision=1)
                    self.assertEqual(self.repo.list(), [])
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    with patch.object(CharacterRepository, "read_exact", side_effect=AssertionError("frozen replay reread library")):
                        self.assertEqual(await self.start(db, saver), original)
                    fresh = await start_live_story(db, saver, self.project, "after-delete", ["s1"], self.brief,
                                                   character_refs=[self.ref], character_root=self.library)
                    self.assertNotEqual(fresh.execution_id, original.execution_id)
                    for row in db.execute("SELECT owner_config FROM executions"):
                        self.assertEqual(row[0], encoded)
                        self.assertEqual(read_owner_config(row[0]).selected_characters[0].character, self.card)
                    await run_story_work(db, saver, fixture_story)
                    task = json.loads(self.requests[0]["messages"][1]["content"])
                    self.assertEqual(task["brief"], read_owner_config(encoded).brief.model_dump(mode="json"))
                    self.assertEqual(task["context"]["selected_canon"],
                                     [{"kind": "character", "ref": self.ref.model_dump(mode="json")}])
                    self.assertEqual(self.repo.list(), [])

    async def test_invalid_duplicate_combined_and_missing_selections_do_not_accept_start(self):
        with self.transport(), open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                for refs, brief in (([self.ref, self.ref], self.brief), ([self.ref] * 17, self.brief), ([self.ref], self.brief.model_copy(update={"subjects": [{"subject_id": self.ref.subject_id, "description": "Untrusted override"}]})), ([self.ref], self.brief.model_copy(update={"subjects": [{"subject_id": f"s{i}", "description": "Manual"} for i in range(16)]}))):
                    with self.subTest(refs=refs), self.assertRaises(ValueError):
                        await self.start(db, saver, refs, brief)
                with self.assertRaises(FileNotFoundError):
                    await self.start(db, saver, [self.ref.model_copy(update={"digest": "sha256:" + "0" * 64})])
                self.assertEqual(db.execute("SELECT COUNT(*) FROM executions").fetchone(), (0,))

    async def test_concurrent_same_key_with_different_revisions_and_identical_bio_conflicts(self):
        from backend.openrouter import pin_story_owner
        second = self.repo.save(self.bio, [self.image], mutation_id="same-bio", subject_id=self.ref.subject_id, expected_revision=1).ref
        both = asyncio.Event()
        calls = 0
        async def pin_together(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                both.set()
            await asyncio.wait_for(both.wait(), 3)
            return await pin_story_owner(*args)
        with self.transport(), patch("backend.openrouter.pin_story_owner", side_effect=pin_together), open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                results = await asyncio.gather(self.start(db, saver, [self.ref]), self.start(db, saver, [second]), return_exceptions=True)
                self.assertEqual(sum(isinstance(result, ValueError) for result in results), 1, results)
                conflict = next(result for result in results if isinstance(result, ValueError))
                self.assertIn("client key conflicts", str(conflict))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM executions").fetchone(), (1,))

    async def test_frozen_snapshot_integrity_and_narrative_projection_fail_closed(self):
        with self.transport(), open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                await self.start(db, saver)
                config = json.loads(db.execute("SELECT owner_config FROM executions").fetchone()[0])
                for field in ("image", "bio", "projection"):
                    damaged = json.loads(json.dumps(config))
                    if field == "image":
                        damaged["selected_characters"][0]["character"]["images"][0]["digest"] = "sha256:" + "0" * 64
                    elif field == "bio":
                        damaged["selected_characters"][0]["character"]["bio"]["name"] = "Tampered"
                    else:
                        damaged["brief"]["subjects"][0]["description"] = "Untrusted override"
                    from backend.openrouter import encode
                    with self.subTest(field=field), self.assertRaises(ValueError):
                        read_owner_config(encode(damaged))

    def test_http_selection_shape_validation_and_safe_projection(self):
        body = {"project_id": self.project, "client_key": "http", "input_message": self.brief.user_vibe,
                "subjects": [], "character_refs": [self.ref.model_dump(mode="json")], "shot_ids": ["s1"], "shot_duration_ms": 5000}
        with self.transport(), TestClient(create_app(self.root, fixture_story, character_root=self.library), base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000)) as client:
            headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
            response = client.post("/api/executions/live-story", json=body, headers=headers)
            self.assertEqual(response.status_code, 202, response.text)
            receipt = response.json()
            projection = client.get(f"/api/executions/{receipt['execution_id']}/projection")
            self.assertEqual(projection.status_code, 200, projection.text)
            self.assertEqual(projection.json()["submitted"]["selected_characters"][0]["ref"], body["character_refs"][0])
            self.assertEqual(projection.json()["submitted"]["text_brief"]["subjects"][0]["subject_id"], self.ref.subject_id)
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": ""}), patch.object(CharacterRepository, "read_exact", side_effect=AssertionError("HTTP replay reread library")):
                self.assertEqual(client.post("/api/executions/live-story", json=body, headers=headers).json(), receipt)
                changed = {**body, "character_refs": [{**body["character_refs"][0], "revision": 2}]}
                self.assertEqual(client.post("/api/executions/live-story", json=changed, headers=headers).status_code, 409)
            for change in ({"character_refs": body["character_refs"] * 2}, {"character_refs": body["character_refs"] * 17},
                           {"subjects": [{"subject_id": self.ref.subject_id, "description": "Override"}]},
                           {"subjects": [{"subject_id": "duplicate", "description": "x"}] * 2}):
                self.assertEqual(client.post("/api/executions/live-story", json={**body, "client_key": "invalid", **change}, headers=headers).status_code, 422)
            missing = {**body, "client_key": "missing", "character_refs": [{**body["character_refs"][0], "digest": "sha256:" + "0" * 64}]}
            response = client.post("/api/executions/live-story", json=missing, headers=headers)
            self.assertEqual(response.status_code, 404, response.text)
            self.assertNotIn(str(self.library), response.text)
            # Historical journal commands omit refs and still submit their original text subjects.
            manual = {key: value for key, value in body.items() if key != "character_refs"}
            manual.update(client_key="old-journal", subjects=[{"subject_id": "fox", "description": "A curious fox"}])
            response = client.post("/api/executions/live-story", json=manual, headers=headers)
            self.assertEqual(response.status_code, 202, response.text)
            submitted = client.get(f"/api/executions/{response.json()['execution_id']}/projection").json()["submitted"]
            self.assertEqual(submitted["selected_characters"], [])
            self.assertEqual(submitted["text_brief"]["subjects"], manual["subjects"])


if __name__ == "__main__":
    unittest.main()
