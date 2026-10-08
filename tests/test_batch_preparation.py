"""Real committed compact V2 sources; diagnostics never activate media work."""

from contextlib import asynccontextmanager
from copy import deepcopy
import importlib.util
import os
import sqlite3
import unittest
from unittest.mock import patch
from uuid import uuid4

from backend import batch_generation, config, database, wardrobe_store
from backend.api import fixture_story
from backend.domain import canonical_json, sha256_digest
from backend.production import production_catalog
from backend.story_control import open_story_runtime
from backend.story_reads import story_projection
from tests import test_story_wardrobe_api as fixtures
from tests.test_domain import DIGEST
from tests.test_story_cast import draft
from tests.test_story_wardrobe_runtime import retained_inventory
from tests.test_wardrobe_compact_v2 import compact_draft


ACTIVATION = "sha256:" + "7" * 64
CONNECTION = {"connection": "local", "endpoint_digest": "sha256:" + "8" * 64}


def assert_public_diagnostic(test, value):
    """Provider implementation data must be absent at every nesting level."""
    forbidden = {"prepared_input", "profile_snapshot", "registry_snapshot", "mapping", "graph", "raw_graph",
                 "schemas", "schema", "schema_sha256", "template", "template_sha256", "template_graph_sha256",
                 "file_sha256", "basename", "inventory", "model_inventory", "model_inventory_sha256",
                 "parameters", "slots", "links", "graph_links", "widgets", "widget_literals", "crop_policy", "geometry_source",
                 "models", "template_bytes", "schema_snapshot", "node_id", "node_ids", "load_id", "resize_id",
                 "consumer_id", "output_node", "class_type", "inputs",
                 "endpoint", "auth_token", "headers", "Authorization", "verify"}
    if isinstance(value, dict):
        test.assertFalse(forbidden & value.keys(), f"Private diagnostic fields: {sorted(forbidden & value.keys())}")
        for nested in value.values():
            assert_public_diagnostic(test, nested)
    elif isinstance(value, list):
        for nested in value:
            assert_public_diagnostic(test, nested)
    elif isinstance(value, str):
        for private in ("private-token", "rotated-token", "render.example.test", "127.0.0.1:8188"):
            test.assertNotIn(private, value)


class SavedBatchTests(fixtures.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec("backend.batch_preparation"),
                             "Trusted saved-plan preparation reader is not implemented")
        from backend import batch_preparation
        self.b = batch_preparation
        self.profile = production_catalog()["image_only"]["profiles"][0]["pin"]

    @asynccontextmanager
    async def committed(self, subjects=("comedian",)):
        story = draft(cast=[{"subject_id": key, "description": "Traveler " + key} for key in subjects],
                      subject_ids=list(subjects))
        output = {"status": "ready", "plan": compact_draft(subjects), "explanation": None}
        with self.transport(output), patch.object(fixtures, "draft", return_value=story):
            async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
                receipt = await runtime.start_wardrobe(self.project, "saved-batch", ["s1"], self.brief)
                await runtime.run()
                self.approve(runtime, receipt.execution_id)
                await runtime.run()
                ref, _ = wardrobe_store.read_wardrobe_plan(runtime.db, receipt.execution_id)
                projection = story_projection(runtime.db, receipt.execution_id)
                self.assertIsNotNone(projection)
                assert projection is not None
                self.assertEqual(projection["status"], "completed")
                yield runtime, ref

    def read(self, db, ref, **changes):
        arguments = {"execution_id": ref.execution_id, "source_plan_ref": ref,
                     "image_size": {"width": 768, "height": 768}, "image_profile": self.profile,
                     "connection": CONNECTION, "activation_id": ACTIVATION}
        arguments.update(changes)
        return self.b.read_saved_batch_input(db, **arguments)

    async def test_reads_exact_saved_v2_without_effects_or_changes_to_terminal_execution(self):
        async with self.committed() as (runtime, ref):
            db = runtime.db
            before = retained_inventory(db, ref.execution_id)
            tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            counts = {name: db.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in tables}
            changes = db.total_changes
            statements = []
            db.set_trace_callback(statements.append)
            denied = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE, sqlite3.SQLITE_TRANSACTION}
            db.set_authorizer(lambda action, *args: sqlite3.SQLITE_DENY if action in denied else sqlite3.SQLITE_OK)
            try:
                with patch.object(wardrobe_store, "wardrobe_authority", side_effect=AssertionError("Completed authority")), \
                        patch("backend.openrouter_client.httpx.AsyncClient", side_effect=AssertionError("No provider")), \
                        patch("backend.characters.CharacterRepository.read_exact", side_effect=AssertionError("No library")), \
                        patch.object(batch_generation.registry, "prepare_image", side_effect=AssertionError("No job preparation")):
                    result = self.read(db, ref)
                    self.assertEqual(result, self.read(db, ref))
            finally:
                db.set_authorizer(None)
                db.set_trace_callback(None)
            self.assertEqual(result.readiness, "preparation_only")
            self.assertIs(result.can_submit, False)
            self.assertEqual(result.prepared_input.source_plan_ref, ref)
            self.assertEqual(result.input_digest, batch_generation.batch_input_digest(result.prepared_input))
            self.assertEqual(result.input_digest, sha256_digest(canonical_json(result.prepared_input)))
            record = wardrobe_store.read_wardrobe_operation(db, ref.operation_id)
            self.assertEqual(result.prepared_input.story_approval.story_ref, record["pins"].story_ref)
            self.assertEqual(result.prepared_input.story_approval.applied_activation_id, record["pins"].activation_id)
            self.assertEqual(db.total_changes, changes)
            self.assertEqual(retained_inventory(db, ref.execution_id), before)
            self.assertEqual({name: db.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in tables}, counts)
            self.assertTrue(statements)
            self.assertTrue(all(sql.lstrip().startswith("SELECT") or sql == "PRAGMA database_list"
                                for sql in statements), statements)

    async def test_location_three_and_five_units_and_offline_reopen_keep_exact_handoff(self):
        for subjects in ((), ("comedian",), ("ada", "leo")):
            self.root = self.root.with_name("batch-" + str(len(subjects)))
            async with self.committed(subjects) as (runtime, ref):
                original = self.read(runtime.db, ref)
                before = retained_inventory(runtime.db, ref.execution_id)
                self.assertEqual(len(original.prepared_input.ordered_units), 2 * len(subjects) + 1)
                _, plan = wardrobe_store.read_wardrobe_plan(runtime.db, ref.execution_id, artifact_id=ref.artifact_id)
                self.assertEqual(original.prepared_input.ordered_units, plan.batch_prompt)
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": "changed/model"}), \
                    patch("backend.openrouter_client.httpx.AsyncClient", side_effect=AssertionError("Offline model")), \
                    patch("backend.openrouter_wardrobe.PROMPT") as prompt, database.open_database(self.root) as db:
                prompt.read_text.side_effect = AssertionError("No authored prompt read")
                self.assertEqual(self.read(db, ref), original)
                self.assertEqual(retained_inventory(db, ref.execution_id), before)

    async def test_public_projection_preserves_semantics_but_digest_still_covers_private_handoff(self):
        async with self.committed(("ada", "leo")) as (runtime, ref):
            result = self.read(runtime.db, ref)
            original = canonical_json(result.prepared_input)
            self.assertIn("mapping", result.prepared_input.profile_snapshot["workflows"][0])
            self.assertTrue(callable(getattr(self.b, "project_saved_batch_preparation", None)), "Public projector missing")
            public = self.b.project_saved_batch_preparation(result)
            assert_public_diagnostic(self, public.model_dump(mode="json"))
            for field in ("source_plan_ref", "story_approval", "stage_id", "activation_id", "image_size",
                          "image_profile", "connection", "mapping_digest", "ordered_units"):
                self.assertEqual(getattr(public, field), getattr(result.prepared_input, field))
            self.assertEqual(public.mapping_version, result.prepared_input.mapping.schema_version)
            self.assertEqual(public.workflow_bindings, result.prepared_input.mapping.bindings)
            self.assertEqual(public.input_digest, sha256_digest(original))
            self.assertEqual(result.input_digest, public.input_digest)
            self.assertEqual(canonical_json(result.prepared_input), original)
            self.assertNotEqual(sha256_digest(canonical_json(public)), public.input_digest)
            self.assertEqual(len(public.ordered_units), 5)
            self.assertIs(public.can_submit, False)
            with self.assertRaises(ValueError):
                type(public).model_validate({**public.model_dump(), "profile_snapshot": result.prepared_input.profile_snapshot})
            with self.assertRaises(ValueError):
                self.b.project_saved_batch_preparation(result.model_copy(update={"input_digest": DIGEST}))

    async def test_full_ref_equality_rejects_substitution_without_latest_fallback(self):
        async with self.committed() as (runtime, ref):
            changes = [("digest", DIGEST), ("operation_id", DIGEST), ("schema_version", "1"),
                       ("produced_by_stage", "storytell"), ("execution_id", str(uuid4()))]
            for field, value in changes:
                changed = ref.model_copy(update={field: value})
                with self.subTest(field=field), self.assertRaises(ValueError):
                    self.read(runtime.db, ref, source_plan_ref=changed)
            missing = str(uuid4())
            changed = ref.model_copy(update={"artifact_id": missing,
                "uri": f"kinodel://projects/{ref.project_id}/artifacts/{missing}"})
            with patch.object(batch_generation, "freeze_batch_input", side_effect=AssertionError("No freezing")), \
                    self.assertRaises(ValueError):
                self.read(runtime.db, ref, source_plan_ref=changed)
            with self.assertRaises(ValueError):
                self.read(runtime.db, ref, source_plan_ref=None)
            with self.assertRaises(LookupError):
                self.read(runtime.db, ref, execution_id=str(uuid4()))

    async def test_cancel_missing_terminal_or_incomplete_work_rejects(self):
        async with self.committed() as (runtime, ref):
            db = runtime.db
            outcome = db.execute("SELECT * FROM execution_outcomes").fetchone()
            db.execute("DELETE FROM execution_outcomes")
            with self.assertRaises(ValueError):
                self.read(db, ref)
            db.execute("INSERT INTO execution_outcomes VALUES (?,?,?,?)", outcome)
            for state in ("cancelled", "failed"):
                db.execute("UPDATE execution_outcomes SET outcome=?", (state,))
                with self.subTest(state=state), self.assertRaises(ValueError):
                    self.read(db, ref)
            db.execute("UPDATE execution_outcomes SET outcome='completed'")
            work_id = db.execute("SELECT work_id FROM execution_work WHERE kind='resume'").fetchone()[0]
            db.execute("INSERT INTO execution_controls (execution_id,command_key,kind,work_id) VALUES (?, 'cancel', 'cancel', ?)",
                       (ref.execution_id, work_id))
            with self.assertRaises(ValueError):
                self.read(db, ref)
            db.execute("DELETE FROM execution_controls")
            for state in ("pending", "claimed", "blocked", "failed", "obsolete"):
                db.execute("UPDATE execution_work SET status=? WHERE kind='resume'", (state,))
                with self.subTest(work_state=state), self.assertRaises(ValueError):
                    self.read(db, ref)
            db.execute("UPDATE execution_work SET status='completed' WHERE kind='resume'")
            self.read(db, ref)

    async def test_original_applied_receipt_is_required_not_just_valid_operation_pins(self):
        async with self.committed() as (runtime, ref):
            db = runtime.db
            fields = [("applied_activation", None), ("request_digest", DIGEST), ("decision_digest", DIGEST),
                      ("decision_key", "substituted"), ("action", "revise"), ("message", "not an approval"),
                      ("binding_revision", 2), ("subject_digest", DIGEST), ("task_id", ""),
                      ("request_revision", 2)]
            for column, value in fields:
                original = db.execute(f"SELECT {column} FROM review_requests").fetchone()[0]
                db.execute(f"UPDATE review_requests SET {column}=?", (value,))
                # Operation metadata itself still validates: it is not review authority.
                wardrobe_store.read_wardrobe_operation(db, ref.operation_id)
                with self.subTest(column=column), \
                        patch.object(batch_generation, "freeze_batch_input", side_effect=AssertionError("No freezer")), \
                        self.assertRaises(ValueError):
                    self.read(db, ref)
                db.execute(f"UPDATE review_requests SET {column}=?", (original,))
            self.read(db, ref)

    async def test_stale_bindings_and_work_lineage_and_wrong_completion_receipt_reject(self):
        async with self.committed() as (runtime, ref):
            db = runtime.db
            for slot in ("story", "wardrobe_plan"):
                db.execute("UPDATE execution_bindings SET binding_revision=2 WHERE slot=?", (slot,))
                with self.subTest(slot=slot), self.assertRaises(ValueError):
                    self.read(db, ref)
                db.execute("UPDATE execution_bindings SET binding_revision=1 WHERE slot=?", (slot,))
            for column, value in (("payload_digest", DIGEST), ("resume_ref", DIGEST), ("work_id", DIGEST),
                                  ("source_id", DIGEST)):
                original = db.execute(f"SELECT {column} FROM execution_work WHERE kind='resume'").fetchone()[0]
                db.execute(f"UPDATE execution_work SET {column}=? WHERE kind='resume'", (value,))
                with self.subTest(column=column), self.assertRaises(ValueError):
                    self.read(db, ref)
                db.execute(f"UPDATE execution_work SET {column}=? WHERE kind='resume'", (original,))
            original = db.execute("SELECT payload_digest FROM execution_work WHERE kind='start'").fetchone()[0]
            db.execute("UPDATE execution_work SET payload_digest=? WHERE kind='start'", (DIGEST,))
            with self.assertRaises(ValueError):
                self.read(db, ref)
            db.execute("UPDATE execution_work SET payload_digest=? WHERE kind='start'", (original,))
            db.execute("UPDATE execution_outcomes SET source_id=?", (DIGEST,))
            with self.assertRaises(ValueError):
                self.read(db, ref)

    async def test_missing_authority_records_and_unsupported_source_reject_before_freezing(self):
        async with self.committed() as (runtime, ref):
            db = runtime.db
            mutations = ["DELETE FROM review_requests", "DELETE FROM wardrobe_operations",
                         "DELETE FROM execution_work WHERE kind='start'",
                         "DELETE FROM execution_work WHERE kind='resume'",
                         "DELETE FROM execution_bindings WHERE slot='story'",
                         "DELETE FROM execution_bindings WHERE slot='wardrobe_plan'",
                         "DELETE FROM artifacts WHERE schema_id='visual_anchor_plan'",
                         "UPDATE executions SET graph_version='1'",
                         "UPDATE artifacts SET schema_version='1' WHERE schema_id='visual_anchor_plan'"]
            for statement in mutations:
                with self.subTest(statement=statement):
                    db.execute("SAVEPOINT corrupt_source")
                    db.execute("PRAGMA defer_foreign_keys=ON")
                    try:
                        db.execute(statement)
                        with patch.object(batch_generation, "freeze_batch_input", side_effect=AssertionError("No freezer")), \
                                self.assertRaises(ValueError):
                            self.read(db, ref)
                    finally:
                        db.execute("ROLLBACK TO corrupt_source")
                        db.execute("RELEASE corrupt_source")
            self.read(db, ref)

    async def test_missing_or_corrupt_immutable_source_and_uncommitted_operation_reject(self):
        async with self.committed() as (runtime, ref):
            db = runtime.db
            path = wardrobe_store._destination(db, ref.project_id, ref.artifact_id, ref.digest)
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            with self.assertRaises(ValueError):
                self.read(db, ref)
            path.unlink()
            with self.assertRaises(OSError):
                self.read(db, ref)
            path.write_bytes(original)
            transition = db.execute("SELECT next_activation FROM wardrobe_operations").fetchone()[0]
            db.execute("UPDATE wardrobe_operations SET artifact_id=NULL,next_activation=NULL")
            with self.assertRaises(ValueError):
                self.read(db, ref)
            db.execute("UPDATE wardrobe_operations SET artifact_id=?,next_activation=?", (ref.artifact_id, transition))
            db.execute("UPDATE wardrobe_operations SET candidate_digest=?", (DIGEST,))
            with self.assertRaises(ValueError):
                self.read(db, ref)


class BatchPreparationAPITests(fixtures.WardrobeFixtures, unittest.TestCase):
    client = fixtures.WardrobeAPITests.client
    start_body = fixtures.WardrobeAPITests.start_body
    wait = fixtures.WardrobeAPITests.wait
    http_approve = fixtures.WardrobeAPITests.http_approve

    def payload(self, ref):
        return {"source_plan_ref": ref, "image_size": {"width": 768, "height": 768},
                "image_profile": production_catalog()["image_only"]["profiles"][0]["pin"],
                "connection": "local", "activation_id": ACTIVATION}

    def complete(self, client, headers):
        response = client.post("/api/executions/story-wardrobe/v2", json=self.start_body(), headers=headers)
        self.assertEqual(response.status_code, 202, response.text)
        execution = response.json()["execution_id"]
        self.http_approve(client, execution, self.wait(client, execution, "waiting_review"), headers)
        final = self.wait(client, execution, "completed")
        return execution, final

    def test_endpoint_session_csrf_origin_and_strict_contract_precede_resolution(self):
        from tests.test_domain import artifact_ref
        route = f"/api/executions/{uuid4()}/anchor-batch/prepare"
        body = self.payload(artifact_ref())
        with self.client() as client, patch("backend.config.resolve_comfyui_connection", side_effect=AssertionError("No config")):
            self.assertEqual(client.post(route, json=body).status_code, 401)
            headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
            self.assertEqual(client.post(route, json=body).status_code, 403)
            self.assertEqual(client.post(route, json=body, headers={**headers, "Origin": "https://evil.test"}).status_code, 403)
            self.assertEqual(client.post(route, json=body, headers={**headers, "Host": "evil.test"}).status_code, 403)
            mutations = [lambda b: b.update(connection="automatic"), lambda b: b.pop("connection"),
                         lambda b: b.update(approved=True), lambda b: b.update(endpoint="http://evil.test"),
                         lambda b: b.update(activation_id="bad"), lambda b: b.update(source_plan_ref=None),
                         lambda b: b["image_size"].update(width=True), lambda b: b["image_profile"].update(digest="bad")]
            for mutate in mutations:
                changed = deepcopy(body)
                mutate(changed)
                with self.subTest(body=changed):
                    response = client.post(route, json=changed, headers=headers)
                    self.assertEqual(response.status_code, 422, response.text)

    def test_real_saved_source_local_server_identity_and_offline_reopen_do_not_start_jobs(self):
        with patch.dict(os.environ, {"COMFYUI_LOCAL_ENDPOINT": "http://127.0.0.1:8188",
                                    "COMFYUI_SERVER_ENDPOINT": "https://render.example.test/native",
                                    "COMFYUI_CONNECTION": "server", "COMFYUI_AUTH_TOKEN": "private-token",
                                    "COMFYUI_CA_FILE": ""}), self.transport(), self.client() as client:
            headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
            execution, final = self.complete(client, headers)
            before_requests = len(self.requests)
            route = f"/api/executions/{execution}/anchor-batch/prepare"
            for selected in ("local", "server"):
                body = {**self.payload(final["wardrobe_plan_ref"]), "connection": selected}
                response = client.post(route, json=body, headers=headers)
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertEqual(result["readiness"], "preparation_only")
                self.assertIs(result["can_submit"], False)
                assert_public_diagnostic(self, result)
                expected = config.resolve_comfyui_connection(selected)
                self.assertEqual(result["connection"],
                                 {"connection": selected, "endpoint_digest": "sha256:" + expected.endpoint_digest})
                self.assertEqual(result["source_plan_ref"], final["wardrobe_plan_ref"])
                self.assertEqual(result["story_approval"]["story_ref"], final["stories"][0]["ref"])
                self.assertEqual(result["activation_id"], ACTIVATION)
                self.assertEqual(result["stage_id"], "anchor-batch")
                self.assertEqual(result["image_size"], body["image_size"])
                self.assertEqual(result["image_profile"], body["image_profile"])
                plan = client.get(f"/api/executions/{execution}/wardrobe-plans/{final['wardrobe_plan_ref']['artifact_id']}").json()
                self.assertEqual(result["ordered_units"], plan["plan"]["batch_prompt"])
                self.assertEqual([(b["use_case"], b["workflow_id"], b["kind"], b["reference_roles"])
                                  for b in result["workflow_bindings"]],
                    [("hero-face", "krea2-txt2img", "portrait", []),
                     ("location", "krea2-txt2img", "background", []),
                     ("hero-sheet", "qwen21-multi-img2img", "sheet", ["portrait", "background"])])
                self.assertNotIn("private-token", response.text)
                self.assertNotIn("render.example.test", response.text)
                self.assertNotIn("work_id", result)
                self.assertEqual(client.get(f"/api/executions/{execution}/projection").json(), final)
            self.assertEqual(len(self.requests), before_requests)
            original = result
        with database.open_database(self.root) as db:
            before = retained_inventory(db, execution)
            from backend.batch_preparation import read_saved_batch_input
            full = read_saved_batch_input(db, execution, source_plan_ref=body["source_plan_ref"],
                image_size=body["image_size"], image_profile=body["image_profile"], connection=original["connection"],
                activation_id=body["activation_id"])
            self.assertEqual(original["input_digest"], sha256_digest(canonical_json(full.prepared_input)))
            self.assertEqual(original["mapping_digest"], full.prepared_input.mapping_digest)
            self.assertEqual(original["workflow_bindings"], [b.model_dump(mode="json") for b in full.prepared_input.mapping.bindings])
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": "",
                                    "COMFYUI_SERVER_ENDPOINT": "https://render.example.test/native",
                                    "COMFYUI_AUTH_TOKEN": "rotated-token", "COMFYUI_CA_FILE": ""}), \
                patch("backend.openrouter_client.httpx.AsyncClient", side_effect=AssertionError("Offline HTTP")), \
                self.client() as client:
            headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
            response = client.post(route, json=body, headers=headers)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), original)
            models = client.get("/openapi.json").json()["components"]["schemas"]
            self.assertEqual(set(models["AnchorBatchPreparationRequestV1"]["required"]), set(body))
            self.assertIs(models["AnchorBatchPreparationRequestV1"]["additionalProperties"], False)
            schema = client.get("/openapi.json").json()
            response_schema = schema["paths"]["/api/executions/{execution_id}/anchor-batch/prepare"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
            self.assertEqual(response_schema, {"$ref": "#/components/schemas/PublicBatchPreparationV1"})
            self.assertIs(models["PublicBatchPreparationV1"]["additionalProperties"], False)
            self.assertNotIn("BatchGenerationInputV1", models)
            self.assertNotIn("SavedBatchPreparationV1", models)
        with database.open_database(self.root) as db:
            self.assertEqual(retained_inventory(db, execution), before)

    def test_config_and_source_errors_are_safe_no_silent_connection_or_ref_fallback(self):
        with self.transport(), self.client() as client:
            headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
            execution, final = self.complete(client, headers)
            route = f"/api/executions/{execution}/anchor-batch/prepare"
            body = self.payload(final["wardrobe_plan_ref"])
            with patch.dict(os.environ, {"COMFYUI_SERVER_ENDPOINT": "", "COMFYUI_LOCAL_ENDPOINT": "http://127.0.0.1:8188",
                                        "COMFYUI_CA_FILE": ""}):
                response = client.post(route, json={**body, "connection": "server"}, headers=headers)
                self.assertEqual(response.status_code, 422, response.text)
                changed = deepcopy(body)
                changed["source_plan_ref"]["digest"] = DIGEST
                response = client.post(route, json=changed, headers=headers)
                self.assertEqual(response.status_code, 409, response.text)
                response = client.post(f"/api/executions/{uuid4()}/anchor-batch/prepare", json=body, headers=headers)
                self.assertEqual(response.status_code, 404, response.text)
            with patch("backend.config.resolve_comfyui_connection", side_effect=config.ComfyUIConfigError("invalid_endpoint", "private-token")):
                response = client.post(route, json=body, headers=headers)
                self.assertEqual(response.status_code, 422, response.text)
                self.assertNotIn("private-token", response.text)

    def test_deeply_corrupt_frozen_start_returns_safe_conflict_before_freezing(self):
        with self.transport(), self.client() as client:
            headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
            execution, final = self.complete(client, headers)
            db = client.app.state.runtime.db
            original = client.portal.call(lambda: db.execute("SELECT shot_ids FROM executions WHERE execution_id=?",
                                                             (execution,)).fetchone()[0])
            damaged = "[" * 10000 + '"private-token"' + "]" * 10000
            client.portal.call(lambda: db.execute("UPDATE executions SET shot_ids=? WHERE execution_id=?",
                                                  (damaged, execution)).rowcount)
            try:
                with patch.object(batch_generation, "freeze_batch_input", side_effect=AssertionError("No freezer")):
                    try:
                        response = client.post(f"/api/executions/{execution}/anchor-batch/prepare",
                                               json=self.payload(final["wardrobe_plan_ref"]), headers=headers)
                    except RecursionError:
                        self.fail("Corrupt frozen Start escaped the preparation API error boundary")
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual(response.json(), {
                    "detail": "Saved batch source or preparation settings are unavailable or invalid"})
                self.assertNotIn("private-token", response.text)
            finally:
                client.portal.call(lambda: db.execute("UPDATE executions SET shot_ids=? WHERE execution_id=?",
                                                      (original, execution)).rowcount)


if __name__ == "__main__":
    unittest.main()
