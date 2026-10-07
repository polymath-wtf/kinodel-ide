"""Current compact V2 activation and publication recovery, with mocked HTTP only."""

import os
import unittest
from unittest.mock import patch

from backend import database, openrouter_wardrobe as adapter, wardrobe_store
from backend.api import fixture_story
from backend.characters import CharacterBio, CharacterRepository
from backend.domain import canonical_json
from backend.openrouter import read_owner_config
from backend.story_control import open_story_runtime
from backend.story_reads import story_projection
from tests.test_characters import image_input
from tests import test_story_wardrobe_api as api_tests
from tests.test_story_wardrobe_runtime import retained_inventory
from tests.test_wardrobe_compact_v2 import compact_draft


class CompactWardrobeAPITests(api_tests.WardrobeFixtures, unittest.TestCase):
    client = api_tests.WardrobeAPITests.client
    start_body = api_tests.WardrobeAPITests.start_body
    wait = api_tests.WardrobeAPITests.wait
    http_approve = api_tests.WardrobeAPITests.http_approve

    def test_v2_selected_and_generated_save_three_exact_units_and_reopen_offline(self):
        for selected in (False, True):
            self.root = self.root.with_name("selected" if selected else "generated")
            refs = []
            if selected:
                ref = CharacterRepository(self.library).save(CharacterBio(name="Lea"), [image_input()],
                    mutation_id="create").ref
                refs = [ref.model_dump(mode="json")]
            target = refs[0]["subject_id"] if refs else "comedian"
            body = self.start_body(character_refs=refs)
            output = {"status": "ready", "plan": compact_draft([target]), "explanation": None}
            with self.subTest(selected=selected), self.transport(output), self.client() as client:
                headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
                response = client.post("/api/executions/story-wardrobe/v2", json=body, headers=headers)
                self.assertEqual(response.status_code, 202, response.text)
                receipt = response.json()
                execution = receipt["execution_id"]
                projection = self.wait(client, execution, "waiting_review")
                self.assertEqual(projection["graph"], {"id": wardrobe_store.GRAPH_ID,
                    "version": "2", "digest": wardrobe_store.GRAPH_DIGEST})
                self.http_approve(client, execution, projection, headers)
                final = self.wait(client, execution, "completed")
                ref = final["wardrobe_plan_ref"]
                path = f"/api/executions/{execution}/wardrobe-plans/{ref['artifact_id']}"
                saved = client.get(path)
                self.assertEqual(saved.status_code, 200, saved.text)
                saved = saved.json()
                self.assertEqual((ref["schema_version"], saved["plan"]["schema_version"]), ("2", "2"))
                self.assertEqual(len(saved["plan"]["batch_prompt"]), 3)
                self.assertEqual(saved["plan"]["batch_prompt"], output["plan"]["batch_prompt"])
                self.assertEqual(set(saved["plan"]), {"schema_id", "schema_version", "narrative_ref", "batch_prompt"})
                self.assertEqual(saved["plan"]["narrative_ref"], final["stories"][0]["ref"])
                activity = client.get(f"/api/executions/{execution}/wardrobe-activity").json()
                self.assertEqual(activity["config"]["adapter_version"], "2")
                self.assertEqual(activity["input"]["schema_version"], "2")
            with database.open_database(self.root) as db:
                before = retained_inventory(db, execution)
                frozen = read_owner_config(before["executions"][0][-1])
                self.assertEqual(frozen.wardrobe_settings.adapter_version, "2")
                actual_ref, plan = wardrobe_store.read_wardrobe_plan(db, execution)
                file = wardrobe_store._destination(db, self.project, actual_ref.artifact_id, actual_ref.digest)
                original = file.read_bytes()
                self.assertEqual(original, canonical_json(plan))
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": ""}), \
                    patch("backend.openrouter_client.httpx.AsyncClient", side_effect=AssertionError("Offline HTTP")), \
                    patch("backend.openrouter_wardrobe.PROMPT") as prompt, self.client() as client:
                prompt.read_text.side_effect = AssertionError("Offline prompt read")
                headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
                self.assertEqual(client.post("/api/executions/story-wardrobe/v2", json=body, headers=headers).json(), receipt)
                self.assertEqual(client.get(path).json(), saved)
                self.assertEqual(self.wait(client, execution, "completed"), final)
            with database.open_database(self.root) as db:
                self.assertEqual(retained_inventory(db, execution), before)
                self.assertEqual(file.read_bytes(), original)

    def test_preparation_and_opt_in_size_failure_use_same_compact_projection(self):
        diagnostic = adapter.WardrobeInputSizeDiagnostic(serialized_evidence_bytes=adapter.MAX_WARDROBE_REQUEST_BYTES + 1)
        inputs = []
        def size(supplied):
            inputs.append(supplied)
            return diagnostic
        with self.transport(), self.client() as client:
            headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
            response = client.post("/api/executions/story-wardrobe/v2", json=self.start_body(), headers=headers)
            self.assertEqual(response.status_code, 202, response.text)
            execution = response.json()["execution_id"]
            projection = self.wait(client, execution, "waiting_review")
            with patch.object(adapter, "wardrobe_input_size_diagnostic", side_effect=size):
                self.http_approve(client, execution, projection, headers)
                blocked = self.wait(client, execution, "blocked")
                self.assertEqual(blocked["wardrobe_stop"]["reason"], "wardrobe_invalid")
                read = client.get(f"/api/executions/{execution}/wardrobe-activity?include_validation_diagnostic=true")
                self.assertEqual(read.status_code, 200, read.text)
                self.assertEqual(read.json()["validation_diagnostic"], diagnostic.model_dump(mode="json"))
            self.assertEqual(len(inputs), 2)
            self.assertEqual(inputs[0], inputs[1])


class CompactWardrobeRecoveryTests(api_tests.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    async def test_pinned_candidate_recovers_after_publication_without_http_or_repin(self):
        output = {"status": "ready", "plan": compact_draft(["comedian"]), "explanation": None}
        with self.transport(output):
            async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
                receipt = await runtime.start_wardrobe(self.project, "compact", ["s1"], self.brief)
                await runtime.run()
                self.approve(runtime, receipt.execution_id)
                publish = wardrobe_store._publish
                def crash(*args):
                    publish(*args)
                    raise RuntimeError("after immutable publication")
                with patch.object(wardrobe_store, "_publish", side_effect=crash), self.assertRaisesRegex(RuntimeError, "publication"):
                    await runtime.run()
                row = runtime.db.execute("SELECT operation_id FROM wardrobe_operations").fetchone()
                record = wardrobe_store.read_wardrobe_operation(runtime.db, row[0])
                self.assertEqual(record["candidate"].schema_version, "2")
                self.assertEqual(record["owner_attempts"], 1)
                self.assertIsNone(record["next_activation"])
                self.assertEqual(runtime.db.execute("SELECT COUNT(*) FROM artifacts WHERE schema_id='visual_anchor_plan'").fetchone(), (0,))
                body, config = record["candidate_body"], record["owner_config"]
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": "changed/model"}), \
                patch("backend.openrouter_client.httpx.AsyncClient", side_effect=AssertionError("Recovery HTTP")), \
                patch.object(adapter, "pin_wardrobe_settings", side_effect=AssertionError("Recovery re-pin")):
            async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
                self.assertEqual(await runtime.run(), 1)
                ref, plan = wardrobe_store.read_wardrobe_plan(runtime.db, receipt.execution_id)
                self.assertEqual(ref.schema_version, "2")
                self.assertEqual(canonical_json(plan).decode(), body)
                recovered = wardrobe_store.read_wardrobe_operation(runtime.db, ref.operation_id)
                self.assertEqual((recovered["owner_config"], recovered["owner_attempts"]), (config, 1))
                self.assertEqual(story_projection(runtime.db, receipt.execution_id)["status"], "completed")

    async def test_invalid_compact_output_uses_one_repair_and_never_commits_candidate(self):
        output = {"status": "ready", "plan": compact_draft(["undeclared"]), "explanation": None}
        with self.transport(output):
            async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
                receipt = await runtime.start_wardrobe(self.project, "invalid", ["s1"], self.brief)
                await runtime.run()
                self.approve(runtime, receipt.execution_id)
                await runtime.run()
                self.assertEqual(runtime.db.execute("SELECT owner_attempts,owner_repairs,candidate_body FROM wardrobe_operations").fetchone(), (2, 1, None))
                self.assertEqual(runtime.db.execute("SELECT COUNT(*) FROM artifacts WHERE schema_id='visual_anchor_plan'").fetchone(), (0,))
                self.assertEqual(runtime.db.execute("SELECT COUNT(*) FROM execution_outcomes").fetchone(), (0,))
                self.assertEqual(story_projection(runtime.db, receipt.execution_id)["wardrobe_stop"]["reason"], "wardrobe_invalid_output")


if __name__ == "__main__":
    unittest.main()
