"""Frozen admission only; disposable roots, no graph invocation or provider access."""

import asyncio
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from backend import config, production, story_start
from backend.api import create_app
from backend.database import open_database
from backend.domain import StoryTextInputV1, canonical_json
from backend.openrouter import StoryWardrobeOwnerConfigV2, read_owner_config
from backend.openrouter_client import OpenRouterModelMetadataV1
from backend.saver import open_saver
from backend.story_control import StoryRuntime
from backend.story_graph import initial_story_state


class AnchorStartFixtures:
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("backend.story_anchor_start"),
                             "Frozen Story/anchor Start contract is missing")
        from backend import story_anchor_start
        self.start_module = story_anchor_start
        temporary = tempfile.TemporaryDirectory(prefix="kinodel anchor admission ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "data"
        self.project = str(uuid4())
        self.brief = StoryTextInputV1(user_vibe="A cat returns a ribbon", subjects=[], shot_duration_ms=5000)
        environment = patch.dict(os.environ, {
            "OPENROUTER_API_KEY": "test-secret", "LLM_MODEL": "test/anchor-start",
            "COMFYUI_LOCAL_ENDPOINT": "http://127.0.0.1:8188",
            "COMFYUI_SERVER_ENDPOINT": "https://render.invalid/native",
            "COMFYUI_AUTH_TOKEN": "private-test-token", "COMFYUI_CA_FILE": "",
        })
        environment.start()
        self.addCleanup(environment.stop)
        metadata = patch("backend.openrouter_client.model_metadata", side_effect=lambda model:
            OpenRouterModelMetadataV1(id=model, supported_parameters=["response_format", "structured_outputs"],
                input_modalities=["text", "image"], supported_efforts=["low"]))
        self.metadata = metadata.start()
        self.addCleanup(metadata.stop)
        for target in ("backend.openrouter_client.http", "backend.comfyui.acquire_preparation_context"):
            forbidden = patch(target, side_effect=AssertionError("Admission performed provider I/O"))
            forbidden.start()
            self.addCleanup(forbidden.stop)
        self.options = self.start_module.story_anchor_start_options().model_dump(mode="json")
        self.intent = {"image_size": self.options["supported_sizes"][0],
                       "image_profile": self.options["image_profile"], "connection": self.options["connections"][0]}

    async def start(self, db, saver, key="start", intent=None):
        return await self.start_module.start_story_anchor_batch(db, saver, self.project, key, ["s1"], self.brief,
            render_intent=self.intent if intent is None else intent)


class AnchorStartTests(AnchorStartFixtures, unittest.IsolatedAsyncioTestCase):
    async def test_options_are_exact_secret_free_offline_choices(self):
        self.assertEqual(set(self.options), {"schema_version", "graph", "image_profile", "supported_sizes", "connections"})
        profile = production.production_catalog()["image_only"]["profiles"][0]
        self.assertEqual(self.options["image_profile"], profile["pin"])
        self.assertEqual(self.options["supported_sizes"], profile["supported_sizes"])
        self.assertEqual(self.options["connections"], [{"connection": name, "endpoint_digest":
            "sha256:" + config.resolve_comfyui_connection(name).endpoint_digest} for name in ("local", "server")])
        self.assertEqual(self.options["graph"], {"id": self.start_module.GRAPH_ID,
            "version": self.start_module.GRAPH_VERSION, "digest": self.start_module.GRAPH_DIGEST})
        self.assertNotIn("render.invalid", json.dumps(self.options))
        self.assertNotIn("private-test-token", json.dumps(self.options))
        with patch.dict(os.environ, {"COMFYUI_SERVER_ENDPOINT": ""}):
            self.assertEqual([c.connection for c in self.start_module.story_anchor_start_options().connections], ["local"])
        self.metadata.assert_not_called()

    async def test_atomic_start_exact_offline_replay_and_frozen_intent(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                first = await self.start(db, saver)
                self.assertEqual(set(first.model_dump()), {"execution_id", "work_id", "graph", "render_intent"})
                self.assertEqual(first.render_intent.model_dump(mode="json"), self.intent)
                row = db.execute("SELECT graph_id,graph_version,graph_digest,owner_config,start_digest FROM executions").fetchone()
                self.assertEqual(row[:3], (self.start_module.GRAPH_ID, self.start_module.GRAPH_VERSION, self.start_module.GRAPH_DIGEST))
                owner = read_owner_config(row[3])
                self.assertIsInstance(owner, self.start_module.StoryAnchorOwnerConfigV1)
                self.assertEqual((owner.schema_id, owner.schema_version), ("story_anchor_start", "1"))
                self.assertEqual(owner.render_intent.model_dump(mode="json"), self.intent)
                self.assertNotIn("profile_snapshot", json.loads(row[3]))
                self.assertEqual(canonical_json(owner).decode(), row[3])
                self.assertEqual(row[4], story_start._payload_digest(self.brief.user_vibe, ["s1"], row[3]))
                self.assertEqual(db.execute("SELECT work_id,execution_id,kind,source_id,payload_digest,status FROM execution_work").fetchall(),
                    [(first.work_id, first.execution_id, "start", first.execution_id, row[4], "pending")])
                self.assertEqual(story_start.load_test_story_start(db, first.execution_id),
                    (story_start.StartReceipt(first.execution_id, first.work_id), initial_story_state(self.project, first.execution_id, live=True)))
                self.assertIsNone(await saver.aget_tuple({"configurable": {"thread_id": first.execution_id}}))
                for table in ("image_groups", "batch_input_pins", "render_jobs", "story_operations", "execution_outcomes"):
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM " + table).fetchone(), (0,))
                before = list(db.iterdump())
                changes = db.total_changes
                self.assertEqual(await self.start(db, saver), first)
                self.assertEqual(list(db.iterdump()), before)
                self.assertEqual(db.total_changes, changes)
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": "", "COMFYUI_LOCAL_ENDPOINT": "changed-invalid"}), \
                patch("backend.production.production_catalog", side_effect=AssertionError("Replay consulted catalog")), \
                patch("backend.openrouter.pin_story_owner", side_effect=AssertionError("Replay repinned owner")):
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    self.assertEqual(await self.start(db, saver), first)
                    self.assertEqual(db.execute("SELECT owner_config,start_digest FROM executions").fetchone(), row[3:])
                    self.assertEqual(list(db.iterdump()), before)
        self.assertEqual(self.metadata.call_count, 1)

    async def test_render_identity_is_frozen_before_owner_await_even_if_environment_changes(self):
        from backend.openrouter import pin_story_owner
        async def changed_after_validation(*args):
            os.environ["COMFYUI_LOCAL_ENDPOINT"] = "https://changed.invalid/new"
            return await pin_story_owner(*args)
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                with patch("backend.openrouter.pin_story_owner", side_effect=changed_after_validation):
                    receipt = await self.start(db, saver)
                self.assertEqual(receipt.render_intent.model_dump(mode="json"), self.intent)
                self.assertNotEqual(receipt.render_intent.connection.endpoint_digest,
                    "sha256:" + config.resolve_comfyui_connection("local").endpoint_digest)
                self.assertEqual(await self.start(db, saver), receipt)

    async def test_changed_submitted_fields_or_intent_conflict_without_repinning(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                await self.start(db, saver)
                before = list(db.iterdump())
                with patch("backend.openrouter.pin_story_owner", side_effect=AssertionError("Conflict reached owner")):
                    for size in self.options["supported_sizes"][1:]:
                        with self.assertRaises(ValueError):
                            await self.start(db, saver, intent={**self.intent, "image_size": size})
                    for shots, brief in ((["s2"], self.brief), (["s1"], self.brief.model_copy(update={"shot_duration_ms": 6000}))):
                        with self.assertRaises(ValueError):
                            await self.start_module.start_story_anchor_batch(db, saver, self.project, "start", shots, brief,
                                render_intent=self.intent)
                self.assertEqual(list(db.iterdump()), before)

    async def test_invalid_render_pins_reject_before_owner_io(self):
        variants = []
        for path, value in (("image_size", {"width": 123, "height": 456}),
                            ("image_profile", {**self.intent["image_profile"], "digest": "sha256:" + "0" * 64}),
                            ("image_profile", {**self.intent["image_profile"], "version": "unknown"}),
                            ("image_profile", {**self.intent["image_profile"], "profile_id": "unknown"}),
                            ("connection", {**self.intent["connection"], "endpoint_digest": "sha256:" + "0" * 64})):
            variants.append({**self.intent, path: value})
        variants.append({**self.intent, "image_profile": {**self.intent["image_profile"], "digest": None}})
        variants.append({**self.intent, "connection": {**self.intent["connection"], "endpoint": "http://secret.invalid"}})
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                with patch("backend.openrouter.pin_story_owner", side_effect=AssertionError("Invalid render reached owner")):
                    for index, intent in enumerate(variants):
                        with self.subTest(index=index), self.assertRaises(ValueError):
                            await self.start(db, saver, key=str(index), intent=intent)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM executions").fetchone(), (0,))
        self.metadata.assert_not_called()

    async def test_changed_declaration_blocks_frozen_profile_without_replacement(self):
        from backend import batch_generation
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                first = await self.start(db, saver)
                before = list(db.iterdump())
                catalog = deepcopy(production.production_catalog())
                catalog["image_only"]["profiles"][0]["pin"]["digest"] = "sha256:" + "a" * 64
                with patch("backend.production.production_catalog", return_value=catalog):
                    self.assertEqual(await self.start(db, saver), first)
                    with self.assertRaises(ValueError):
                        batch_generation.resolve_batch_image_profile(first.render_intent.image_profile, first.render_intent.image_size)
                self.assertEqual(list(db.iterdump()), before)

    async def test_concurrent_identical_submission_converges_but_render_or_route_conflicts(self):
        from backend.openrouter import pin_story_owner
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                for conflict in (None, "size", "connection", "route"):
                    arrived, calls = asyncio.Event(), 0
                    async def together(*args):
                        nonlocal calls
                        calls += 1
                        if calls == 2:
                            arrived.set()
                        await asyncio.wait_for(arrived.wait(), 3)
                        return await pin_story_owner(*args)
                    other = deepcopy(self.intent)
                    if conflict == "size":
                        other["image_size"] = self.options["supported_sizes"][-1]
                        self.assertNotEqual(other["image_size"], self.intent["image_size"])
                    if conflict == "connection":
                        other["connection"] = self.options["connections"][-1]
                    key = "race-" + str(conflict)
                    second = (story_start.start_story_wardrobe(db, saver, self.project, key, ["s1"], self.brief)
                              if conflict == "route" else self.start(db, saver, key=key, intent=other))
                    with patch("backend.openrouter.pin_story_owner", side_effect=together):
                        results = await asyncio.gather(self.start(db, saver, key=key), second, return_exceptions=True)
                    if conflict is None:
                        self.assertEqual(results[0], results[1])
                    else:
                        self.assertEqual(sum(isinstance(r, ValueError) for r in results), 1, results)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM executions").fetchone(), (4,))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_work").fetchone(), (4,))

    async def test_existing_route_keys_and_exact_config_schemas_are_preserved(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                legacy = await story_start.start_story_wardrobe(db, saver, self.project, "legacy", ["s1"], self.brief)
                original = db.execute("SELECT * FROM executions").fetchall()
                config_body = db.execute("SELECT owner_config FROM executions").fetchone()[0]
                self.assertIs(type(read_owner_config(config_body)), StoryWardrobeOwnerConfigV2)
                with self.assertRaises(ValueError):
                    await self.start(db, saver, key="legacy")
                with patch("backend.openrouter.pin_story_owner", side_effect=AssertionError("Legacy replay repinned")):
                    self.assertEqual(await story_start.start_story_wardrobe(db, saver, self.project, "legacy", ["s1"], self.brief), legacy)
                self.assertEqual(db.execute("SELECT * FROM executions").fetchall(), original)
                new = await self.start(db, saver)
                frozen = db.execute("SELECT owner_config FROM executions WHERE execution_id=?", (new.execution_id,)).fetchone()[0]
                with self.assertRaises(ValueError):
                    StoryWardrobeOwnerConfigV2.model_validate_json(frozen)
                with self.assertRaises(ValueError):
                    await story_start.start_story_wardrobe(db, saver, self.project, "start", ["s1"], self.brief)
                # Old graph envelopes cannot adopt the new schema, even with a recomputed input digest.
                db.execute("UPDATE executions SET owner_config=?,start_digest=? WHERE execution_id=?",
                    (frozen, story_start._payload_digest(self.brief.user_vibe, ["s1"], frozen), legacy.execution_id))
                with self.assertRaises(ValueError):
                    story_start.load_test_story_start(db, legacy.execution_id)

    async def test_work_failure_rolls_back_start_and_runtime_command_owns_only_admission(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                db.execute("CREATE TEMP TRIGGER reject_start BEFORE INSERT ON execution_work BEGIN SELECT RAISE(ABORT, 'work failed'); END")
                with self.assertRaises(sqlite3.IntegrityError):
                    await self.start(db, saver)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM executions").fetchone(), (0,))
                db.execute("DROP TRIGGER reject_start")
                runtime = StoryRuntime(db, saver, lambda *args: self.fail("Admission invoked Story"))
                first = await runtime.start_anchor_batch(self.project, "start", ["s1"], self.brief, render_intent=self.intent)
                await runtime.close()
                self.assertEqual(db.execute("SELECT status FROM execution_work WHERE work_id=?", (first.work_id,)).fetchone(), ("pending",))
                with self.assertRaises(ValueError):
                    await runtime.start_anchor_batch(self.project, "later", ["s1"], self.brief, render_intent=self.intent)


class AnchorStartAPITests(AnchorStartFixtures, unittest.TestCase):
    def test_guarded_options_and_strict_start_receipt_without_running_graph(self):
        path = "/api/executions/story-anchor-batch/v1"
        # The separately assigned graph/runner is deliberately not part of this admission test.
        with patch.object(StoryRuntime, "run", new_callable=AsyncMock, return_value=0), \
                TestClient(create_app(self.root), base_url="http://127.0.0.1:8765", client=("127.0.0.1", 1234)) as client:
            self.assertEqual(client.get(path + "/options").status_code, 401)
            csrf = client.get("/api/session").json()["csrf_token"]
            response = client.get(path + "/options")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.options)
            body = {"project_id": self.project, "client_key": "api", "input_message": self.brief.user_vibe,
                "shot_ids": ["s1"], "subjects": [], "character_refs": [], "shot_duration_ms": 5000, "render_intent": self.intent}
            self.assertEqual(client.post(path, json=body).status_code, 403)
            headers = {"X-Kinodel-CSRF": csrf}
            self.assertEqual(client.get(path + "/options", headers={"Origin": "https://foreign.invalid"}).status_code, 403)
            for invalid in ({k: v for k, v in body.items() if k != "render_intent"}, {**body, "extra": True}):
                self.assertEqual(client.post(path, json=invalid, headers=headers).status_code, 422)
            response = client.post(path, json=body, headers=headers)
            self.assertEqual(response.status_code, 202, response.text)
            receipt = response.json()
            self.assertEqual(set(receipt), {"execution_id", "work_id", "graph", "render_intent"})
            self.assertEqual(receipt["render_intent"], self.intent)
            self.assertEqual(receipt["graph"], self.options["graph"])
            with patch("backend.openrouter.pin_story_owner", side_effect=AssertionError("HTTP replay repinned")):
                self.assertEqual(client.post(path, json=body, headers=headers).json(), receipt)
            changed = deepcopy(body)
            changed["render_intent"]["connection"] = self.options["connections"][-1]
            self.assertEqual(client.post(path, json=changed, headers=headers).status_code, 409)
            invalid = deepcopy(body)
            invalid["client_key"] = "invalid-pins"
            invalid["render_intent"]["connection"]["endpoint_digest"] = "sha256:" + "0" * 64
            with patch("backend.openrouter.pin_story_owner", side_effect=AssertionError("HTTP invalid pins reached owner")):
                rejected = client.post(path, json=invalid, headers=headers)
            self.assertEqual(rejected.status_code, 409, rejected.text)
            self.assertNotIn("private-test-token", rejected.text)
            self.assertEqual(self.metadata.call_count, 1)


if __name__ == "__main__":
    unittest.main()
