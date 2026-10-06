"""W4 commands/reads on real starts and checkpoints; provider HTTP is always mocked."""

import asyncio
import base64
from functools import partial
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from backend import story_start, wardrobe_store
from backend.api import create_app, fixture_story, StoryProjection
from backend.characters import CharacterBio, CharacterRepository
from backend.database import open_database
from backend.domain import StoryTextInputV1
from backend.saver import open_saver
from backend.story_control import open_story_runtime
from backend.story_reads import story_projection
from backend.story_store import _destination
from tests.test_characters import image_input
from tests.test_story_cast import draft
from tests.test_wardrobe_openrouter import capability, envelope


class WardrobeFixtures:
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel wardrobe api ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "data"
        self.library = Path(temporary.name) / "selected characters"
        self.project = str(uuid4())
        self.brief = StoryTextInputV1(user_vibe="A robot joke", subjects=[], shot_duration_ms=5000)
        self.requests = []
        environment = patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret", "LLM_MODEL": "test/model"})
        environment.start()
        self.addCleanup(environment.stop)

    def transport(self, wardrobe_output=None):
        def respond(request):
            self.requests.append(request)
            if request.method == "GET":
                return httpx.Response(200, json={"data": [{**capability(), "id": "test/model"}]})
            payload = json.loads(request.content)
            if payload["response_format"]["json_schema"]["name"] != "wardrobe_result":
                return httpx.Response(200, json=envelope({"status": "ready", "story": draft(), "explanation": None}))
            if callable(wardrobe_output):
                return wardrobe_output(request)
            result = wardrobe_output or json.loads(envelope()["choices"][0]["message"]["content"])
            if result.get("plan"):
                for unit in result["plan"]["units"]:
                    unit["subject_ids"] = ["comedian"] if unit["role"] != "background" else []
            return httpx.Response(200, json=envelope(result))
        return patch("backend.openrouter_client.httpx.AsyncClient",
                     partial(httpx.AsyncClient, transport=httpx.MockTransport(respond)))

    def approve(self, runtime, execution):
        review = story_projection(runtime.db, execution)["review"]
        return runtime.respond(execution, review["request_id"], review["digest"],
                               review["binding_revision"], "approve", "approve", None)


class WardrobeCommandTests(WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    async def test_start_freezes_wardrobe_before_hitl_and_reopen(self):
        from backend import openrouter_wardrobe as adapter
        prompt = "Original Wardrobe instruction"
        with patch.object(adapter, "PROMPT") as resource, self.transport():
            resource.read_text.return_value = prompt
            async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
                receipt = await runtime.start_wardrobe(self.project, "frozen", ["s1"], self.brief)
                frozen = runtime.db.execute("SELECT owner_config FROM executions").fetchone()[0]
                await runtime.run()  # Story HITL, before any Wardrobe preparation.
            resource.read_text.return_value = "Changed Wardrobe instruction"
            with patch.dict(os.environ, {"LLM_MODEL": "changed/model"}):
                async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
                    self.assertEqual(await runtime.start_wardrobe(self.project, "frozen", ["s1"], self.brief), receipt)
                    self.assertEqual(runtime.db.execute("SELECT owner_config FROM executions").fetchone()[0], frozen)
                    self.approve(runtime, receipt.execution_id)
                    await runtime.run()
                    row = runtime.db.execute("SELECT owner_config FROM wardrobe_operations").fetchone()
                    self.assertIsNotNone(row, "Wardrobe preparation switched to the changed model")
                    config = adapter.read_wardrobe_config(row[0])
                    self.assertEqual(config.model, "test/model")
                    self.assertEqual(config.system_prompt, prompt)
                    self.assertEqual(config.timeout_seconds, 180)
                    self.assertEqual(config.max_tokens, 8192)
                    ref, _ = wardrobe_store.read_wardrobe_plan(runtime.db, receipt.execution_id)
            resource.read_text.side_effect = AssertionError("Offline replay read current prompt")
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": ""}):
                async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
                    self.assertEqual(await runtime.start_wardrobe(self.project, "frozen", ["s1"], self.brief), receipt)
                    self.assertEqual(wardrobe_store.read_wardrobe_plan(runtime.db, receipt.execution_id)[0], ref)
                    self.assertEqual(await runtime.run(), 0)
            self.assertEqual(resource.read_text.call_count, 1)

    async def test_start_settings_reject_preparation_substitution(self):
        from backend import openrouter_wardrobe as adapter
        from backend.openrouter import read_owner_config
        from backend.review_store import apply_story_decision
        async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
            with self.transport():
                receipt = await runtime.start_wardrobe(self.project, "settings", ["s1"], self.brief)
                await runtime.run()
                review = story_projection(runtime.db, receipt.execution_id)["review"]
                decision = self.approve(runtime, receipt.execution_id)
                apply_story_decision(runtime.db, receipt.execution_id, review["request_id"], decision.decision_id)
                _, supplied, _ = wardrobe_store.wardrobe_authority(runtime.db, receipt.execution_id, review["request_id"])
                start = read_owner_config(runtime.db.execute("SELECT owner_config FROM executions").fetchone()[0])
                frozen = await adapter.prepare_wardrobe_request(supplied, {}, settings=start.wardrobe_settings)
                with self.assertRaisesRegex(ValueError, "frozen Start settings"):
                    wardrobe_store.prepare_wardrobe_operation(runtime.db, receipt.execution_id, review["request_id"],
                                                             frozen, "Substituted repair instruction")
                with patch.object(adapter, "PROMPT") as resource:
                    resource.read_text.return_value = "Substituted prompt"
                    substituted = await adapter.prepare_wardrobe_request(supplied, {})
                with self.assertRaisesRegex(ValueError, "frozen Start settings"):
                    wardrobe_store.prepare_wardrobe_operation(runtime.db, receipt.execution_id, review["request_id"],
                                                             substituted, start.wardrobe_settings.repair_instruction)
                self.assertEqual(runtime.db.execute("SELECT COUNT(*) FROM wardrobe_operations").fetchone(), (0,))

    async def test_explicit_start_replay_cross_route_keys_and_concurrent_acceptance(self):
        self.assertTrue(callable(getattr(story_start, "start_story_wardrobe", None)), "Explicit Wardrobe start missing")
        with self.transport(), open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                start = story_start.start_story_wardrobe
                receipt = await start(db, saver, self.project, "new", ["s1"], self.brief)
                self.assertEqual(db.execute("SELECT graph_id,graph_version,graph_digest FROM executions").fetchone(),
                                 (wardrobe_store.GRAPH_ID, wardrobe_store.GRAPH_VERSION, wardrobe_store.GRAPH_DIGEST))
                with patch("backend.openrouter.pin_story_owner", side_effect=AssertionError("Replay re-pinned")):
                    self.assertEqual(await start(db, saver, self.project, "new", ["s1"], self.brief), receipt)
                    with self.assertRaisesRegex(ValueError, "client key conflicts"):
                        await story_start.start_live_story(db, saver, self.project, "new", ["s1"], self.brief)
                    with self.assertRaisesRegex(ValueError, "client key conflicts"):
                        await story_start.start_test_story(db, saver, self.project, "new", self.brief.user_vibe, ["s1"])
                await story_start.start_live_story(db, saver, self.project, "old", ["s1"], self.brief)
                with self.assertRaisesRegex(ValueError, "client key conflicts"):
                    await start(db, saver, self.project, "old", ["s1"], self.brief)
                await story_start.start_test_story(db, saver, self.project, "fixture", self.brief.user_vibe, ["s1"])
                with self.assertRaisesRegex(ValueError, "client key conflicts"):
                    await start(db, saver, self.project, "fixture", ["s1"], self.brief)
                from backend.openrouter import pin_story_owner
                barrier, calls = asyncio.Event(), 0
                async def pin_together(*args):
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        barrier.set()
                    await asyncio.wait_for(barrier.wait(), 3)
                    return await pin_story_owner(*args)
                with patch("backend.openrouter.pin_story_owner", side_effect=pin_together):
                    results = await asyncio.gather(start(db, saver, self.project, "race", ["s1"], self.brief),
                        story_start.start_live_story(db, saver, self.project, "race", ["s1"], self.brief), return_exceptions=True)
                self.assertEqual(sum(isinstance(result, ValueError) for result in results), 1, results)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM executions").fetchone(), (4,))

    async def test_retry_uses_remaining_budget_occ_and_frozen_authority_only(self):
        async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
            with self.transport():
                receipt = await runtime.start_wardrobe(self.project, "new", ["s1"], self.brief)
                await runtime.run()
                decision = self.approve(runtime, receipt.execution_id)
            with self.transport(lambda _: httpx.Response(503)):
                await runtime.run()
            db = runtime.db
            record = db.execute("SELECT prepared_inputs,owner_config,repair_request,owner_attempts FROM wardrobe_operations").fetchone()
            story_budget = db.execute("SELECT owner_budget FROM story_operations").fetchall()
            version = db.execute("SELECT work_version FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone()[0]
            with self.assertRaisesRegex(ValueError, "version"):
                runtime.retry(receipt.execution_id, decision.work_id, "retry", version - 1)
            ref = story_projection(db, receipt.execution_id)["stories"][0]["ref"]
            path = _destination(db, self.project, ref["artifact_id"], ref["digest"])
            parked = path.with_suffix(".parked")
            path.rename(parked)
            try:
                with self.assertRaisesRegex(ValueError, "Wardrobe retry"):
                    runtime.retry(receipt.execution_id, decision.work_id, "retry", version)
            finally:
                parked.rename(path)
            db.execute("UPDATE executions SET start_digest='changed' WHERE execution_id=?", (receipt.execution_id,))
            with self.assertRaises(ValueError):
                runtime.retry(receipt.execution_id, decision.work_id, "retry", version)
            db.execute("UPDATE executions SET start_digest=? WHERE execution_id=?", (json.loads(record[0])["start_digest"], receipt.execution_id))
            self.assertEqual(runtime.retry(receipt.execution_id, decision.work_id, "retry", version), decision.work_id)
            self.assertEqual(runtime.retry(receipt.execution_id, decision.work_id, "retry", version), decision.work_id)
            self.assertEqual(db.execute("SELECT owner_budget FROM story_operations").fetchall(), story_budget)
            self.assertEqual(db.execute("SELECT prepared_inputs,owner_config,repair_request,owner_attempts FROM wardrobe_operations").fetchone(), record)
        async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
            with patch.dict(os.environ, {"LLM_MODEL": "changed/model"}), self.transport(lambda _: httpx.Response(503)):
                await runtime.run()
            projection = StoryProjection.model_validate(story_projection(runtime.db, receipt.execution_id))
            self.assertEqual(projection.status, "blocked")
            self.assertEqual(projection.wardrobe_stop.reason, "wardrobe_exhausted")
            self.assertEqual(projection.wardrobe_stop.allowed_actions, ["cancel", "new_run"])
            work = next(work for work in projection.work if work.work_id == decision.work_id)
            with self.assertRaises(ValueError):
                runtime.retry(receipt.execution_id, decision.work_id, "third", work.work_version)
            # Even a stale/mislabelled reason cannot authorize a third POST.
            runtime.db.execute("UPDATE execution_work SET blocked_reason='wardrobe_unavailable' WHERE work_id=?", (decision.work_id,))
            with self.assertRaises(ValueError):
                runtime.retry(receipt.execution_id, decision.work_id, "third", work.work_version)
            runtime.cancel(receipt.execution_id, "cancel")
            await runtime.run()
            self.assertEqual(story_projection(runtime.db, receipt.execution_id)["status"], "cancelled")
        posts = [r.content for r in self.requests if r.method == "POST" and b'wardrobe_result' in r.content]
        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0], posts[1])

    async def test_transient_retry_can_finish_without_new_story_or_review(self):
        async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
            with self.transport():
                receipt = await runtime.start_wardrobe(self.project, "new", ["s1"], self.brief)
                await runtime.run()
                decision = self.approve(runtime, receipt.execution_id)
            with self.transport(lambda _: httpx.Response(503)):
                await runtime.run()
            before = story_projection(runtime.db, receipt.execution_id)
            work = next(w for w in before["work"] if w["work_id"] == decision.work_id)
            runtime.retry(receipt.execution_id, decision.work_id, "retry", work["work_version"])
            with self.transport():
                await runtime.run()
            after = story_projection(runtime.db, receipt.execution_id)
            self.assertEqual(after["status"], "completed")
            self.assertEqual(after["stories"], before["stories"])
            self.assertEqual(len(after["reviews"]), 1)
            self.assertEqual(runtime.db.execute("SELECT owner_attempts FROM wardrobe_operations").fetchone(), (2,))

    async def test_cancel_drains_suspended_http_and_checkpoint_without_late_plan(self):
        parent = self.root
        for boundary in ("http", "checkpoint"):
            self.root = parent / boundary
            entered, stopped, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
            with self.subTest(boundary=boundary), self.transport():
                async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
                    receipt = await runtime.start_wardrobe(self.project, "new", ["s1"], self.brief)
                    await runtime.run()
                    decision = self.approve(runtime, receipt.execution_id)
                    original_writes = runtime.saver.aput_writes

                    async def suspended_http(request):
                        if request.method == "GET":
                            return httpx.Response(200, json={"data": [{**capability(), "id": "test/model"}]})
                        self.assertIn(b'wardrobe_result', request.content)
                        entered.set()
                        try:
                            await asyncio.Event().wait()
                        except asyncio.CancelledError:
                            # A provider response can arrive despite task cancellation; never bind it.
                            result = json.loads(envelope()["choices"][0]["message"]["content"])
                            for unit in result["plan"]["units"]:
                                unit["subject_ids"] = ["comedian"] if unit["role"] != "background" else []
                            return httpx.Response(200, json=envelope(result))
                        finally:
                            stopped.set()

                    async def suspended_checkpoint(*args, **kwargs):
                        if any(channel == "wardrobe_activation" for channel, _ in args[1]):
                            entered.set()
                            try:
                                await release.wait()
                                return await original_writes(*args, **kwargs)
                            finally:
                                stopped.set()
                        return await original_writes(*args, **kwargs)

                    suspension = (patch("backend.openrouter_client.httpx.AsyncClient", partial(httpx.AsyncClient,
                        transport=httpx.MockTransport(suspended_http))) if boundary == "http" else
                        patch.object(runtime.saver, "aput_writes", suspended_checkpoint))
                    with suspension:
                        running = asyncio.create_task(runtime.run())
                        try:
                            await asyncio.wait_for(entered.wait(), 5)
                            cancel = runtime.cancel(receipt.execution_id, "cancel")
                            self.assertEqual(story_projection(runtime.db, receipt.execution_id)["status"], "cancelling")
                            if boundary == "checkpoint":
                                # Saver writes are drained, not abandoned on graph cancellation.
                                done, _ = await asyncio.wait({running}, timeout=0.15)
                                self.assertFalse(done)
                                self.assertFalse(stopped.is_set())
                                self.assertEqual(runtime.db.execute("SELECT * FROM execution_outcomes").fetchall(), [])
                                release.set()
                            await asyncio.wait_for(running, 5)
                        finally:
                            release.set()
                            if not running.done():
                                running.cancel()
                            await asyncio.gather(running, return_exceptions=True)
                    self.assertTrue(stopped.is_set(), "Terminal cancellation preceded writer cleanup")
                    self.assertEqual(runtime.db.execute("SELECT status FROM execution_work WHERE work_id=?", (decision.work_id,)).fetchone(), ("obsolete",))
                    self.assertEqual(runtime.db.execute("SELECT COUNT(*) FROM execution_bindings WHERE slot='wardrobe_plan'").fetchone(), (0,))
                    self.assertEqual(runtime.db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (1,))
                    self.assertEqual(runtime.db.execute("SELECT COUNT(*) FROM review_requests").fetchone(), (1,))
                    self.assertEqual(runtime.db.execute("SELECT COUNT(*) FROM wardrobe_operations WHERE candidate_body IS NOT NULL").fetchone(), (0,))
                    self.assertEqual(runtime.cancel(receipt.execution_id, "cancel"), cancel)
                    final = story_projection(runtime.db, receipt.execution_id)
                    self.assertEqual(final["status"], "cancelled")
            with patch("backend.openrouter_client.httpx.AsyncClient", side_effect=AssertionError("Cancelled reopen made HTTP")):
                async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
                    self.assertEqual(await runtime.run(), 0)
                    self.assertEqual(story_projection(runtime.db, receipt.execution_id), final)


class WardrobeAPITests(WardrobeFixtures, unittest.TestCase):
    def client(self):
        return TestClient(create_app(self.root, fixture_story, character_root=self.library),
                          base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000))

    def start_body(self, **changes):
        return {"project_id": self.project, "client_key": "new", "input_message": self.brief.user_vibe,
                "shot_ids": ["s1"], "subjects": [], "shot_duration_ms": 5000, **changes}

    def wait(self, client, execution, status):
        for _ in range(250):
            response = client.get(f"/api/executions/{execution}/projection")
            self.assertEqual(response.status_code, 200, response.text)
            projection = response.json()
            if projection["status"] == status and (status != "completed" or all(
                    work["status"] in ("completed", "obsolete") for work in projection["work"])):
                return projection
            time.sleep(0.02)
        self.fail(f"Execution did not reach {status}: {response.text}")

    def http_approve(self, client, execution, projection, headers):
        review = projection["review"]
        response = client.post(f"/api/executions/{execution}/reviews/{review['request_id']}/respond", headers=headers,
            json={"command_key": "approve", "request_digest": review["digest"], "expected_revision": review["binding_revision"],
                  "action": "approve"})
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()

    def test_api_start_approval_exact_plan_selected_images_and_offline_reopen(self):
        repository = CharacterRepository(self.library)
        image = image_input()
        selected = repository.save(CharacterBio(name="Lea", vibe="Warm"), [image], mutation_id="create").ref
        stored_image = repository.read_exact(selected).images[0]
        original = repository.read_image(selected, stored_image.digest)[1]
        body = self.start_body(character_refs=[selected.model_dump(mode="json")])
        with self.transport(), self.client() as client:
            self.assertEqual(client.post("/api/executions/story-wardrobe", json=body).status_code, 401)
            headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
            self.assertEqual(client.post("/api/executions/story-wardrobe", json=body).status_code, 403)
            # Commands accept durable work only; the independent worker is temporarily held.
            with patch("backend.story_control.StoryRuntime.run", return_value=0):
                response = client.post("/api/executions/story-wardrobe", json=body, headers=headers)
                self.assertEqual(response.status_code, 202, response.text)
                self.assertFalse(any(r.method == "POST" for r in self.requests))
            receipt = response.json()
            execution = receipt["execution_id"]
            projection = self.wait(client, execution, "waiting_review")
            self.assertEqual(projection["graph"]["id"], wardrobe_store.GRAPH_ID)
            self.assertIsNone(projection["wardrobe_plan_ref"])
            self.assertIsNone(projection["wardrobe_stop"])
            self.http_approve(client, execution, projection, headers)
            final = self.wait(client, execution, "completed")
            self.assertEqual(len(final["stories"]), 1)
            self.assertEqual(final["reviews"][-1]["result"]["kind"], "approved_subject")
            ref = final["wardrobe_plan_ref"]
            self.assertEqual(ref["schema_id"], "visual_anchor_plan")
            self.assertEqual(final["outcome"]["subject_artifact_id"], ref["artifact_id"])
            path = f"/api/executions/{execution}/wardrobe-plans/{ref['artifact_id']}"
            plan = client.get(path)
            self.assertEqual(plan.status_code, 200, plan.text)
            saved = plan.json()
            self.assertEqual(saved["ref"], ref)
            self.assertEqual(saved["plan"]["narrative_ref"], final["stories"][0]["ref"])
            self.assertEqual(client.get(f"/api/executions/{execution}").status_code, 200)
            self.assertEqual(client.get(f"/api/executions/{execution}/stories/{ref['artifact_id']}").status_code, 404)
            self.assertEqual(client.get(f"/api/executions/{uuid4()}/wardrobe-plans/{ref['artifact_id']}").status_code, 404)
            self.assertEqual(client.get(f"/api/executions/{execution}/wardrobe-plans/{final['stories'][0]['ref']['artifact_id']}").status_code, 404)
            self.assertIn(execution, [item["execution_id"] for item in client.get("/api/executions").json()["items"]])
            for private in ("owner_config", "repair_request", "image_url", "data_base64", "test-secret"):
                self.assertNotIn(private, json.dumps(final) + plan.text)
        wardrobe_request = next(json.loads(r.content) for r in self.requests if r.method == "POST" and b'wardrobe_result' in r.content)
        supplied = json.loads(wardrobe_request["messages"][1]["content"][0]["text"])
        self.assertEqual(supplied["selected_characters"], [selected.model_dump(mode="json")])
        self.assertEqual(supplied["narrative_ref"], saved["plan"]["narrative_ref"])
        self.assertEqual(supplied["story"]["generated_characters"], draft()["generated_characters"])
        self.assertEqual(supplied["text_context"][0]["source_ref"]["digest"], selected.digest)
        self.assertIn("Lea", supplied["text_context"][0]["content"])
        self.assertEqual(supplied["image_evidence"][0]["subject_ids"], [selected.subject_id])
        self.assertEqual(supplied["image_evidence"][0]["ref"]["digest"], stored_image.digest)
        self.assertIn("data:image/png;base64," + base64.b64encode(original).decode(), json.dumps(wardrobe_request))
        self.library.rename(self.library.with_name("parked"))
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": ""}), \
                patch("backend.openrouter_client.httpx.AsyncClient", side_effect=AssertionError("Offline reopen made HTTP")), self.client() as client:
            headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
            self.assertEqual(client.post("/api/executions/story-wardrobe", json=body, headers=headers).json(), receipt)
            self.assertEqual(client.post("/api/executions/live-story", json=body, headers=headers).status_code, 409)
            self.assertEqual(client.get(path).json(), saved)
            self.assertEqual(self.wait(client, execution, "completed"), final)

    def test_safe_frozen_wardrobe_read_without_provider_or_library_and_corrupt_pins(self):
        selected = CharacterRepository(self.library).save(CharacterBio(name="Frozen Lea"), [image_input()], mutation_id="create").ref
        with self.transport(), self.client() as client:
            self.assertEqual(client.get(f"/api/executions/{uuid4()}/wardrobe-activity").status_code, 401)
            headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
            execution = client.post("/api/executions/story-wardrobe", json=self.start_body(character_refs=[selected.model_dump(mode="json")]), headers=headers).json()["execution_id"]
            projection = self.wait(client, execution, "waiting_review")
            path = f"/api/executions/{execution}/wardrobe-activity"
            before = client.get(path)
            self.assertEqual(before.status_code, 200, before.text)
            self.assertIsNone(before.json())
            self.assertEqual(client.get(path, headers={"Origin": "https://foreign.invalid"}).status_code, 403)
            self.http_approve(client, execution, projection, headers)
            final = self.wait(client, execution, "completed")
            read = client.get(path)
            self.assertEqual(read.status_code, 200, read.text)
            saved = read.json()
            diagnostic_read = client.get(path + "?include_validation_diagnostic=true").json()
            self.assertEqual({k: v for k, v in diagnostic_read.items() if k != "attempts"}, saved)
            self.assertEqual(diagnostic_read["attempts"], {"reserved_attempts": 1, "remaining_attempts": 1,
                                                        "repairs": 0, "diagnostic": None})
            self.assertEqual(saved["config"]["model"], "test/model")
            self.assertEqual(saved["config"]["provider"], "OpenRouter")
            self.assertEqual(saved["input"]["narrative_ref"], final["stories"][0]["ref"])
            self.assertEqual(saved["input"]["selected_characters"], [selected.model_dump(mode="json")])
            self.assertIn("Frozen Lea", saved["input"]["text_context"][0]["content"])
            self.assertEqual(saved["input"]["story"]["generated_characters"], draft()["generated_characters"])
            self.assertEqual(len(saved["input"]["image_evidence"]), 1)
            for private in ("base_request", "repair_request", "image_url", "data:image", "test-secret"):
                self.assertNotIn(private, read.text)
        self.library.rename(self.library.with_name("parked"))
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": "changed"}), \
                patch("backend.openrouter_client.httpx.AsyncClient", side_effect=AssertionError("Read made HTTP")), self.client() as client:
            client.get("/api/session")
            self.assertEqual(client.get(path).json(), saved)
            self.assertEqual(client.get(f"/api/executions/{uuid4()}/wardrobe-activity").status_code, 404)
            client.portal.call(lambda: client.app.state.runtime.db.execute("UPDATE wardrobe_operations SET input_digest='corrupt'").rowcount)
            self.assertEqual(client.get(path).status_code, 409)

    def test_nonready_stop_explanation_no_success_no_retry_and_cancel(self):
        for status in ("needs_input", "out_of_scope"):
            self.root = self.root.with_name(status)
            with self.subTest(status=status), self.transport({"status": status, "plan": None, "explanation": "New direction needs a new run."}), self.client() as client:
                headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
                response = client.post("/api/executions/story-wardrobe", json=self.start_body(), headers=headers)
                self.assertEqual(response.status_code, 202, response.text)
                execution = response.json()["execution_id"]
                self.http_approve(client, execution, self.wait(client, execution, "waiting_review"), headers)
                blocked = self.wait(client, execution, "blocked")
                self.assertIsNone(blocked["outcome"])
                self.assertIsNone(blocked["wardrobe_plan_ref"])
                self.assertEqual(blocked["reviews"][-1]["result"]["kind"], "approved_subject")
                self.assertEqual(blocked["wardrobe_stop"]["reason"], f"wardrobe_{status}")
                self.assertEqual(blocked["wardrobe_stop"]["explanation"], "New direction needs a new run.")
                self.assertEqual(blocked["wardrobe_stop"]["allowed_actions"], ["cancel", "new_run"])
                work = next(w for w in blocked["work"] if w["status"] == "blocked")
                retry = {"command_key": "retry", "work_id": work["work_id"], "expected_version": work["work_version"]}
                self.assertEqual(client.post(f"/api/executions/{execution}/retry", json=retry, headers=headers).status_code, 409)
                self.assertEqual(client.post(f"/api/executions/{execution}/cancel", json={"command_key": "cancel"}, headers=headers).status_code, 202)
                self.wait(client, execution, "cancelled")

    def test_oversized_frozen_evidence_has_opt_in_diagnostic_without_prepared_operation(self):
        from backend.characters import ImageInput
        from backend.openrouter_wardrobe import MAX_WARDROBE_REQUEST_BYTES
        from tests.test_wardrobe_openrouter import large_png

        original = large_png((2100, 1800))
        selected = CharacterRepository(self.library).save(CharacterBio(name="Private diagnostic name"),
            [ImageInput(original, "image/png")] * 2, mutation_id="create").ref
        with self.transport(), self.client() as client:
            headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
            execution = client.post("/api/executions/story-wardrobe", headers=headers,
                json=self.start_body(character_refs=[selected.model_dump(mode="json")])).json()["execution_id"]
            projection = self.wait(client, execution, "waiting_review")
            path = f"/api/executions/{execution}/wardrobe-activity"
            diagnostic_path = path + "?include_validation_diagnostic=true"
            self.assertIsNone(client.get(diagnostic_path).json())
            before = len(self.requests)
            self.http_approve(client, execution, projection, headers)
            blocked = self.wait(client, execution, "blocked")
            self.assertEqual(self.requests[before:], [])  # No Wardrobe catalog GET or completion POST.
            self.assertEqual(blocked["wardrobe_stop"]["reason"], "wardrobe_invalid")
            self.assertEqual(blocked["wardrobe_stop"]["allowed_actions"], ["cancel", "new_run"])
            self.assertIsNone(client.get(path).json())  # Existing strict clients retain their wire.
            response = client.get(diagnostic_path)
            self.assertEqual(response.status_code, 200, response.text)
            saved = response.json()
            self.assertIsNotNone(saved, "Oversized preparation still hides its exact safe cause")
            self.assertEqual(set(saved), {"operation_id", "approval_request_id", "input_digest", "validation_diagnostic"})
            self.assertIsNone(saved["operation_id"])
            self.assertEqual(saved["approval_request_id"], projection["review"]["request_id"])
            diagnostic = saved["validation_diagnostic"]
            self.assertEqual(diagnostic["basis"], "frozen_input_size")  # Reconstructed bound, not historical HTTP evidence.
            self.assertEqual((diagnostic["stage"], diagnostic["code"]), ("input", "evidence_size_limit"))
            self.assertEqual(diagnostic["limit_bytes"], MAX_WARDROBE_REQUEST_BYTES)
            self.assertGreater(diagnostic["serialized_evidence_bytes"], 4 * ((len(original) + 2) // 3))
            for private in ("Private diagnostic name", "test-secret", "base_request", "image_url", "data:image", str(self.library)):
                self.assertNotIn(private, response.text)
            self.assertEqual(client.portal.call(lambda: client.app.state.runtime.db.execute("SELECT COUNT(*) FROM wardrobe_operations").fetchone()), (0,))
            work = next(w for w in blocked["work"] if w["status"] == "blocked")
            retry = client.post(f"/api/executions/{execution}/retry", headers=headers, json={"command_key": "retry",
                "work_id": work["work_id"], "expected_version": work["work_version"]})
            self.assertEqual(retry.status_code, 409)
        self.library.rename(self.library.with_name("parked"))
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": ""}), \
                patch("backend.openrouter_client.httpx.AsyncClient", side_effect=AssertionError("Diagnostic made HTTP")), self.client() as client:
            self.assertEqual(client.get(diagnostic_path).status_code, 401)
            headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
            self.assertEqual(client.get(diagnostic_path).json(), saved)
            self.assertEqual(self.wait(client, execution, "blocked"), blocked)
            self.assertEqual(client.get(f"/api/executions/{uuid4()}/wardrobe-activity?include_validation_diagnostic=true").status_code, 404)
            client.portal.call(lambda: client.app.state.runtime.db.execute("UPDATE executions SET start_digest=?", ("sha256:" + "0" * 64,)).rowcount)
            self.assertEqual(client.get(diagnostic_path).status_code, 409)
            self.assertIsNone(client.get(path).json())
            self.assertEqual(client.post(f"/api/executions/{execution}/cancel", headers=headers,
                json={"command_key": "cancel"}).status_code, 202)
            self.wait(client, execution, "cancelled")

    def test_historical_wire_has_no_new_fields_and_approval_still_ends(self):
        with self.transport(), self.client() as client:
            headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
            for route in ("internal-story", "live-story"):
                body = self.start_body(client_key=route)
                if route == "internal-story":
                    body.pop("subjects")
                    body.pop("shot_duration_ms")
                response = client.post(f"/api/executions/{route}", json=body, headers=headers)
                self.assertEqual(response.status_code, 202, response.text)
                execution = response.json()["execution_id"]
                projection = self.wait(client, execution, "waiting_review")
                self.assertNotIn("wardrobe_plan_ref", projection)
                self.assertNotIn("wardrobe_stop", projection)
                self.assertIn("model", projection)
                self.assertIn("text_brief", projection["submitted"])
                self.http_approve(client, execution, projection, headers)
                final = self.wait(client, execution, "completed")
                self.assertEqual(final["outcome"]["subject_artifact_id"], final["stories"][0]["ref"]["artifact_id"])
                self.assertNotIn("wardrobe_plan_ref", final)
        self.assertFalse(any(r.method == "POST" and b'wardrobe_result' in r.content for r in self.requests))

    def test_http_transient_retry_preserves_work_then_completes(self):
        with self.transport(lambda _: httpx.Response(503)), self.client() as client:
            headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
            response = client.post("/api/executions/story-wardrobe", json=self.start_body(), headers=headers)
            self.assertEqual(response.status_code, 202, response.text)
            execution = response.json()["execution_id"]
            decision = self.http_approve(client, execution, self.wait(client, execution, "waiting_review"), headers)
            blocked = self.wait(client, execution, "blocked")
            self.assertEqual(blocked["wardrobe_stop"]["reason"], "wardrobe_unavailable")
            self.assertEqual(blocked["wardrobe_stop"]["allowed_actions"], ["retry", "cancel", "new_run"])
            work = next(w for w in blocked["work"] if w["work_id"] == decision["work_id"])
            command = {"command_key": "retry", "work_id": work["work_id"], "expected_version": work["work_version"]}
            with self.transport():
                retry = client.post(f"/api/executions/{execution}/retry", json=command, headers=headers)
                self.assertEqual(retry.status_code, 202, retry.text)
                self.assertEqual(retry.json(), {"work_id": decision["work_id"]})
                final = self.wait(client, execution, "completed")
                self.assertEqual(client.post(f"/api/executions/{execution}/retry", json=command, headers=headers).json(), retry.json())
            self.assertEqual(final["stories"], blocked["stories"])
            self.assertEqual(len(final["reviews"]), 1)
            self.assertIsNone(final["wardrobe_stop"])

    def test_attempt_diagnostics_are_guarded_opt_in_offline_and_corruption_fails_closed(self):
        with self.transport(lambda _: httpx.Response(429, content=b"private-test-secret")), self.client() as client:
            headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
            execution = client.post("/api/executions/story-wardrobe", headers=headers, json=self.start_body()).json()["execution_id"]
            path = f"/api/executions/{execution}/wardrobe-activity"
            diagnostic_path = path + "?include_validation_diagnostic=true"
            self.assertIsNone(client.get(diagnostic_path).json())
            self.http_approve(client, execution, self.wait(client, execution, "waiting_review"), headers)
            self.wait(client, execution, "blocked")
            default = client.get(path).json()
            self.assertEqual(set(default), {"operation_id", "approval_request_id", "input_digest", "input", "config"})
            response = client.get(diagnostic_path)
            self.assertEqual(response.status_code, 200, response.text)
            saved = response.json()
            self.assertEqual({k: v for k, v in saved.items() if k != "attempts"}, default)
            self.assertEqual(saved["attempts"], {"reserved_attempts": 1, "remaining_attempts": 1, "repairs": 0,
                "diagnostic": {"attempt": 1, "stage": "http", "status_code": 429,
                               "exception_type": None, "previous_validation": None,
                               "elapsed_ms": saved["attempts"]["diagnostic"]["elapsed_ms"], "phase": "response_read"}})
            self.assertIs(type(saved["attempts"]["diagnostic"]["elapsed_ms"]), int)
            self.assertGreaterEqual(saved["attempts"]["diagnostic"]["elapsed_ms"], 0)
            self.assertEqual(saved["config"]["timeout_seconds"], 180)
            for private in ("private-test-secret", "base_request", "repair_request", "image_url", "data:image"):
                self.assertNotIn(private, response.text)
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": ""}), \
                patch("backend.openrouter_client.httpx.AsyncClient", side_effect=AssertionError("Offline read made HTTP")), self.client() as client:
            self.assertEqual(client.get(diagnostic_path).status_code, 401)
            client.get("/api/session")
            self.assertEqual(client.get(diagnostic_path, headers={"Origin": "https://foreign.invalid"}).status_code, 403)
            self.assertEqual(client.get(diagnostic_path, headers={"Host": "foreign.invalid"}).status_code, 403)
            self.assertEqual(client.get(path).json(), default)
            self.assertEqual(client.get(diagnostic_path).json(), saved)
            client.portal.call(lambda: client.app.state.runtime.db.execute("UPDATE wardrobe_operations SET validation_diagnostic=NULL").rowcount)
            self.assertIsNone(client.get(diagnostic_path).json()["attempts"]["diagnostic"])
            client.portal.call(lambda: client.app.state.runtime.db.execute("UPDATE wardrobe_operations SET validation_diagnostic='{}'").rowcount)
            self.assertEqual(client.get(path).status_code, 409)
            self.assertEqual(client.get(diagnostic_path).status_code, 409)

    def test_invalid_stops_are_safe_visible_nonretryable(self):
        for case, reason in (("output", "wardrobe_invalid_output"), ("config", "wardrobe_invalid")):
            self.root = self.root.with_name(case)
            with self.subTest(case=case), self.transport(lambda _: httpx.Response(200, json={"choices": []})), self.client() as client:
                headers = {"X-Kinodel-CSRF": client.get("/api/session").json()["csrf_token"]}
                response = client.post("/api/executions/story-wardrobe", json=self.start_body(), headers=headers)
                self.assertEqual(response.status_code, 202, response.text)
                execution = response.json()["execution_id"]
                review = self.wait(client, execution, "waiting_review")
                with patch.dict(os.environ, {"OPENROUTER_API_KEY": "" if case == "config" else "test-secret"}):
                    self.http_approve(client, execution, review, headers)
                    blocked = self.wait(client, execution, "blocked")
                self.assertEqual(blocked["wardrobe_stop"]["reason"], reason)
                self.assertTrue(blocked["wardrobe_stop"]["explanation"])
                self.assertEqual(blocked["wardrobe_stop"]["allowed_actions"], ["cancel", "new_run"])
                self.assertIsNone(blocked["outcome"])
                if case == "config":
                    self.assertIsNone(client.get(f"/api/executions/{execution}/wardrobe-activity?include_validation_diagnostic=true").json())
                work = next(w for w in blocked["work"] if w["status"] == "blocked")
                retry = client.post(f"/api/executions/{execution}/retry", headers=headers,
                    json={"command_key": "retry", "work_id": work["work_id"], "expected_version": work["work_version"]})
                self.assertEqual(retry.status_code, 409)
                for private in ("test-secret", "owner_config", "image_url", str(self.library)):
                    self.assertNotIn(private, json.dumps(blocked) + retry.text)


if __name__ == "__main__":
    unittest.main()
