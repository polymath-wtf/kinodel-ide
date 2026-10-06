"""OpenRouter wire validation and the existing durable Story protocol (no paid calls)."""

import asyncio
from functools import partial
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx

from backend.api import fixture_story
from backend.database import open_database
from backend.review_store import accept_story_decision
from backend.saver import open_saver
from backend.story_control import cancel_story, retry_story_work
from backend.story_runner import run_story_work
from backend.story_start import start_test_story
from backend.story_store import read_story


class LiveStoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="kinodel live text ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "data"
        self.project = str(uuid4())
        self.requests = []
        self.environment = patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret", "LLM_MODEL": "z-ai/glm-5.3-flash"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def transport(self, handler=None):
        def respond(request):
            if request.url.path.endswith("/models"):
                return httpx.Response(200, json={"data": [{"id": "z-ai/glm-5.3-flash", "supported_parameters": ["response_format", "structured_outputs"]}]})
            self.assertEqual(request.url, "https://openrouter.ai/api/v1/chat/completions")
            self.assertEqual(request.headers["authorization"], "Bearer test-secret")
            body = json.loads(request.content)
            self.requests.append(body)
            if handler:
                return handler(request, body)
            task = json.loads(body["messages"][1]["content"])
            if task["action"] == "clarify":
                result = {"status": "clarified", "explanation": "The fox's choice pays off the hook."}
            else:
                story = fixture_story(task["brief"]["user_vibe"], task["shot_ids"], None, task["feedback"])
                story = story.model_dump(mode="json")
                story.update(schema_version="2", generated_characters=[])
                for shot in story["shots"]:
                    shot["subject_ids"] = ["fox"]
                result = {"status": "ready", "story": story, "explanation": None}
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(result)}}]})
        return patch("backend.openrouter_client.httpx.AsyncClient", partial(httpx.AsyncClient, transport=httpx.MockTransport(respond)))

    async def start(self, db, saver):
        from backend.domain import StoryTextInputV1
        from backend.story_start import start_live_story

        brief = StoryTextInputV1(user_vibe="A fox returns a lost ribbon", subjects=[{"subject_id": "fox", "description": "A curious fox"}], shot_duration_ms=5000)
        return await start_live_story(db, saver, self.project, "live-start", ["s1", "s2"], brief)

    def review(self, db, execution):
        return db.execute("SELECT request_id,request_digest,binding_revision FROM review_requests WHERE execution_id=? ORDER BY request_revision DESC LIMIT 1", (execution,)).fetchone()

    async def test_shared_provider_preserves_v2_request_bytes_and_envelope_diagnostic(self):
        self.assertIsNotNone(importlib.util.find_spec("backend.openrouter_client"), "Shared provider adapter is absent")
        from backend import openrouter_client as provider
        from backend.domain import canonical_json, sha256_digest
        from backend.openrouter import read_owner_config
        from backend.story_reads import story_activity

        def output(request, body):
            finish = "length" if len(self.requests) == 1 else "stop"
            result = {"status": "needs_input", "story": None, "explanation": "Required canon is missing."}
            return httpx.Response(200, json={"choices": [{"finish_reason": finish, "message": {"content": json.dumps(result)}}]})

        with self.transport(output), patch.object(provider, "structured_request", wraps=provider.structured_request) as builder, \
                patch.object(provider, "model_metadata", wraps=provider.model_metadata) as metadata, \
                patch.object(provider, "parse_completion", wraps=provider.parse_completion) as parser:
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await self.start(db, saver)
                    frozen_config = db.execute("SELECT owner_config FROM executions").fetchone()[0]
                    config = read_owner_config(frozen_config)
                    self.assertEqual(canonical_json(config).decode(), frozen_config)
                    with self.assertRaisesRegex(ValueError, "Storytell needs_input"):
                        await run_story_work(db, saver, fixture_story)
                    frozen, digest = db.execute("SELECT owner_request,owner_request_digest FROM story_operations").fetchone()
                    task = json.loads(self.requests[0]["messages"][1]["content"])
                    expected = {"model": config.model, "stream": False, "max_tokens": 8192,
                                "provider": {"require_parameters": True}, "reasoning": {"effort": "low"},
                                "messages": [{"role": "system", "content": config.system_prompt},
                                             {"role": "user", "content": json.dumps(task, ensure_ascii=False, sort_keys=True, separators=(",", ":"))}],
                                "response_format": {"type": "json_schema", "json_schema": {
                                    "name": "storytell_result", "strict": True, "schema": config.result_schema}}}
                    self.assertEqual(frozen, json.dumps(expected, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
                    self.assertEqual(digest, sha256_digest(frozen.encode()))
                    self.assertEqual(story_activity(db, receipt.execution_id)["operations"][0]["validation_diagnostic"],
                                     {"attempt": 1, "stage": "finish", "code": "incomplete_output",
                                      "paths": ["choices[0].finish_reason"], "finish_reason": "length"})
                    self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs FROM story_operations").fetchone(), (2, 1))
                    self.assertEqual(db.execute("SELECT owner_config FROM executions").fetchone()[0], frozen_config)
        self.assertEqual(builder.call_count, 1)
        self.assertEqual(metadata.call_count, 1)
        self.assertEqual(parser.call_count, 2)

    async def test_live_and_fixture_are_separate_and_clarify_revise_approve_survive_reopen(self):
        from backend.story_start import LIVE_GRAPH_ID, load_test_story_start
        from backend.story_reads import story_projection, recent_story_executions

        with self.transport():
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    live = await self.start(db, saver)
                    fixture = await start_test_story(db, saver, str(uuid4()), "fixture", "Fixture", ["s1"])
                    self.assertEqual(await self.start(db, saver), live)
                    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": "invalid/new-model"}):
                        self.assertEqual(await self.start(db, saver), live)
                    await run_story_work(db, saver, fixture_story)
                    first_ref, first_body = read_story(db, live.execution_id)
                    self.assertEqual(len(self.requests), 1)
                    self.assertEqual(read_story(db, fixture.execution_id)[1].hook, "Fixture")
                    self.assertEqual(story_projection(db, live.execution_id)["graph"]["id"], LIVE_GRAPH_ID)
                    self.assertEqual(len(recent_story_executions(db, 20)), 2)
                    self.assertNotIn("test-secret", db.execute("SELECT owner_config FROM executions WHERE execution_id=?", (live.execution_id,)).fetchone()[0])
                    review = self.review(db, live.execution_id)
                    accept_story_decision(db, live.execution_id, *review, "question", "clarify", "Why?")
                    await run_story_work(db, saver, fixture_story)
                    self.assertEqual(read_story(db, live.execution_id), (first_ref, first_body))
                    review = self.review(db, live.execution_id)
                    accept_story_decision(db, live.execution_id, *review, "edit", "revise", "Make the ending hopeful")
            # Current environment/resources must not replace a run's frozen model or prompt.
            with patch.dict(os.environ, {"LLM_MODEL": "invalid/new-model"}), patch("pathlib.Path.read_text", side_effect=AssertionError("must use frozen prompt")):
                with open_database(self.root) as db:
                    async with open_saver(self.root, db) as saver:
                        load_test_story_start(db, live.execution_id)
                        await run_story_work(db, saver, fixture_story)
                        second_ref, _ = read_story(db, live.execution_id)
                        self.assertNotEqual(second_ref, first_ref)
                        self.assertEqual(read_story(db, live.execution_id, artifact_id=first_ref.artifact_id)[1], first_body)
                        task = json.loads(self.requests[-1]["messages"][1]["content"])
                        self.assertEqual(task["previous_story"], first_body.model_dump(mode="json"))
                        self.assertEqual(task["discussion"][0][0], "clarify")
                        self.assertEqual(self.requests[0]["messages"][0], self.requests[-1]["messages"][0])
                        self.assertEqual(self.requests[-1]["model"], "z-ai/glm-5.3-flash")
                        review = self.review(db, live.execution_id)
                        accept_story_decision(db, live.execution_id, *review, "approve", "approve", None)
                        await run_story_work(db, saver, fixture_story)
                        self.assertEqual(story_projection(db, live.execution_id)["outcome"]["subject_artifact_id"], second_ref.artifact_id)
                        self.assertEqual(await run_story_work(db, saver, fixture_story), 0)
        self.assertEqual(len(self.requests), 3)
        self.assertEqual(self.requests[0]["reasoning"], {"effort": "low"})

    async def test_invalid_output_has_one_durable_repair_then_blocks_without_artifact(self):
        def invalid(request, body):
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": '{"status":"ready","story":null,"explanation":null}'}}]})
        with self.transport(invalid):
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await self.start(db, saver)
                    with self.assertRaisesRegex(ValueError, "invalid_output"):
                        await run_story_work(db, saver, fixture_story)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (0,))
                    self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs FROM story_operations").fetchone(), (2, 1))
                    from backend.api import StoryActivity
                    from backend.story_reads import story_activity
                    diagnostic = StoryActivity.model_validate(story_activity(db, receipt.execution_id)).operations[0].validation_diagnostic
                    self.assertEqual(diagnostic.model_dump(), {"attempt": 2, "stage": "schema", "code": "result_invariant",
                                                             "paths": ["status", "story", "explanation"], "finish_reason": "stop"})
                    reason = db.execute("SELECT blocked_reason FROM execution_work").fetchone()[0]
                    self.assertIn("result_invariant", reason)
                    self.assertIn("story", reason)
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    self.assertEqual(await run_story_work(db, saver, fixture_story), 0)
                    self.assertEqual(story_activity(db, receipt.execution_id)["operations"][0]["validation_diagnostic"], diagnostic.model_dump())
                    with self.assertRaisesRegex(ValueError, "not explicitly retryable"):
                        retry_story_work(db, receipt.execution_id, receipt.work_id, "invalid-retry", 2)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.requests[-1]["provider"], {"require_parameters": True})

    async def test_rejection_variants_are_safe_specific_and_repaired_without_mutating_request(self):
        from backend.api import StoryActivity
        from backend.domain import sha256_digest
        from backend.story_reads import story_activity

        secret = "private-value-test-secret-reasoning"
        story = fixture_story("Fox", ["s1", "s2"], None, None).model_dump(mode="json")
        story.update(schema_version="2", generated_characters=[])
        for shot in story["shots"]:
            shot["subject_ids"] = ["fox"]
        valid = {"status": "ready", "story": story, "explanation": None}
        def envelope(result=valid, finish="stop", **message):
            return {"choices": [{"finish_reason": finish, "message": {"content": json.dumps(result), **message}}]}
        variants = [
            (envelope({**valid, "story": {**story, "schema_version": "1"}}), "schema", "schema_validation", "story.schema_version", "stop"),
            (envelope({**valid, "story": {k: v for k, v in story.items() if k != "generated_characters"}}), "schema", "schema_validation", "story.generated_characters", "stop"),
            (envelope({**valid, "explanation": secret}), "schema", "result_invariant", "explanation", "stop"),
            (envelope({**valid, "story": {**story, "generated_characters": [{"subject_id": "fox", "description": secret}]}}), "constraints", "cast_namespace", "story.generated_characters", "stop"),
            (envelope({**valid, "story": {**story, "shots": list(reversed(story["shots"]))}}), "constraints", "shot_order", "story.shots", "stop"),
            (envelope({**valid, "story": {**story, "shots": story["shots"][:1]}}), "constraints", "shot_order", "story.shots", "stop"),
            (envelope({**valid, "story": {**story, "shots": [story["shots"][0]] * 2}}), "schema", "duplicate_shot_ids", "story.shots", "stop"),
            (envelope({**valid, "story": {**story, "shots": [{**s, "subject_ids": [secret]} for s in story["shots"]]}}), "constraints", "undeclared_subject", "story.shots", "stop"),
            (envelope({**valid, "story": {**story, "generated_characters": [{"subject_id": "new", "description": secret}] * 2}}), "schema", "duplicate_generated_ids", "story.generated_characters", "stop"),
            (envelope({**valid, "story": {**story, "generated_characters": [{"subject_id": f"new-{i}", "description": secret} for i in range(16)]}}), "constraints", "cast_limit", "story.generated_characters", "stop"),
            (envelope({**valid, secret: secret}), "schema", "schema_validation", "*", "stop"),
            ({"choices": []}, "envelope", "invalid_envelope", "choices", "missing"),
            ({"choices": envelope(finish="length")["choices"] + envelope()["choices"]},
             "finish", "incomplete_output", "choices[0].finish_reason", "length"),
            ({"choices": [{"finish_reason": "stop", "message": []}]}, "envelope", "invalid_envelope", "choices[0].message", "stop"),
            ({"choices": [{"finish_reason": "stop", "message": {"content": None}}]}, "content", "non_text_content", "choices[0].message.content", "stop"),
            ({"choices": [{"finish_reason": "stop", "message": {"content": [{"text": secret}]}}]}, "content", "non_text_content", "choices[0].message.content", "stop"),
            (envelope(content=secret), "content", "invalid_json", "choices[0].message.content", "stop"),
            (envelope(content='{"status":"ready","status":"' + secret + '"}'), "content", "invalid_json", "choices[0].message.content", "stop"),
            (envelope(content='{"private":"\\ud800"}'), "content", "invalid_json", "choices[0].message.content", "stop"),
            (envelope(tool_calls=[{"arguments": secret}]), "finish", "tool_calls", "choices[0].message.tool_calls", "stop"),
        ]
        for finish, normalized in [("length", "length"), ("content_filter", "content_filter"), ("tool_calls", "tool_calls"),
                                    ("function_call", "function_call"), ("error", "error"),
                                    (secret, "unknown"), (None, "missing"), ({"private": secret}, "invalid_type")]:
            variants.append((envelope(finish=finish), "finish", "incomplete_output", "choices[0].finish_reason", normalized))
        parent = self.root.parent
        for index, (output, stage, code, path, finish) in enumerate(variants):
            with self.subTest(stage=stage, code=code, path=path, finish=finish):
                self.root = parent / f"variant-{index}"
                self.requests.clear()
                def respond(request, body):
                    return httpx.Response(200, json=output if len(self.requests) == 1 else envelope())
                with self.transport(respond), open_database(self.root) as db:
                    async with open_saver(self.root, db) as saver:
                        receipt = await self.start(db, saver)
                        await run_story_work(db, saver, fixture_story)
                        diagnostic = StoryActivity.model_validate(story_activity(db, receipt.execution_id)).operations[0].validation_diagnostic.model_dump()
                        self.assertEqual((diagnostic["stage"], diagnostic["code"], diagnostic["finish_reason"]), (stage, code, finish))
                        self.assertTrue(any(path in p for p in diagnostic["paths"]), diagnostic)
                        self.assertEqual(diagnostic["attempt"], 1)
                        encoded = json.dumps(diagnostic, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                        repair = self.requests[1]["messages"][-1]["content"]
                        self.assertIn(encoded, repair)
                        for required in ('schema_version="2"', 'generated_characters', 'explanation=null', 'story=null', 'needs_input', 'ordered shot_ids'):
                            self.assertIn(required, repair)
                        self.assertNotIn(secret, encoded + repair)
                        frozen, digest = db.execute("SELECT owner_request,owner_request_digest FROM story_operations").fetchone()
                        self.assertEqual(json.loads(frozen), self.requests[0])
                        self.assertEqual(digest, sha256_digest(frozen.encode()))
                        self.assertEqual(self.requests[1]["messages"][:2], self.requests[0]["messages"])
                        self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs FROM story_operations").fetchone(), (2, 1))
                        self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (1,))

    async def test_repair_uses_durable_diagnostic_after_restart_and_exhaustion_adds_no_call(self):
        from backend.story_reads import story_activity
        from backend.story_store import _assert_writable

        def invalid(request, body):
            return httpx.Response(200, json={"choices": [{"finish_reason": "length", "message": {"content": "private discarded output", "reasoning": "private reasoning"}}]})
        def stop_before_repair(db, execution):
            _assert_writable(db, execution)
            if db.execute("SELECT owner_attempts,owner_repairs FROM story_operations").fetchone() == (1, 1):
                raise RuntimeError("process loss before repair")
        with self.transport(invalid):
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await self.start(db, saver)
                    with patch("backend.openrouter._assert_writable", side_effect=stop_before_repair):
                        with self.assertRaisesRegex(RuntimeError, "process loss"):
                            await run_story_work(db, saver, fixture_story)
                    frozen = db.execute("SELECT owner_request,owner_request_digest FROM story_operations").fetchone()
                    diagnostic = story_activity(db, receipt.execution_id)["operations"][0]["validation_diagnostic"]
                    self.assertEqual(diagnostic["finish_reason"], "length")
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    self.assertEqual(story_activity(db, receipt.execution_id)["operations"][0]["validation_diagnostic"], diagnostic)
                    with self.assertRaisesRegex(ValueError, "incomplete_output.*length"):
                        await run_story_work(db, saver, fixture_story)
                    self.assertEqual(db.execute("SELECT owner_request,owner_request_digest FROM story_operations").fetchone(), frozen)
                    self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs FROM story_operations").fetchone(), (2, 1))
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (0,))
                    # Even direct adapter re-entry after exhaustion cannot send a third call.
                    from backend.openrouter import produce_live_story
                    activation = db.execute("SELECT activation_id FROM story_operations").fetchone()[0]
                    with self.assertRaisesRegex(ValueError, "incomplete_output.*length"):
                        await produce_live_story(db, receipt.execution_id, activation, None, None, None)
                    self.assertNotIn("private", json.dumps(story_activity(db, receipt.execution_id)))
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    self.assertEqual(await run_story_work(db, saver, fixture_story), 0)
        self.assertEqual(len(self.requests), 2)
        self.assertIn('"attempt":1', self.requests[1]["messages"][-1]["content"])
        self.assertIn('"code":"incomplete_output"', self.requests[1]["messages"][-1]["content"])

    async def test_transport_failure_retry_preserves_exact_request_and_committed_replay_skips_call(self):
        def timeout(request, body):
            raise httpx.ReadTimeout("do not persist provider data or secret", request=request)
        with self.transport(timeout):
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await self.start(db, saver)
                    await run_story_work(db, saver, fixture_story)
                    version = db.execute("SELECT work_version FROM execution_work WHERE work_id=?", (receipt.work_id,)).fetchone()[0]
                    self.assertEqual(db.execute("SELECT blocked_reason FROM execution_work").fetchone(), ("owner_unavailable",))
                    from backend.story_reads import story_activity
                    activity = story_activity(db, receipt.execution_id)
                    self.assertEqual(activity["operations"][0]["status"], "blocked")
                    self.assertEqual(activity["operations"][0]["reserved_attempts"], 1)
                    self.assertIsNone(activity["operations"][0]["story_ref"])
                    failure = {"attempt": 1, "stage": "transport", "status_code": None,
                               "exception_type": "ReadTimeout", "previous_validation": None}
                    self.assertEqual(activity["operations"][0]["validation_diagnostic"], failure)
                    self.assertNotIn("provider data or secret", json.dumps(activity))
                    retry_story_work(db, receipt.execution_id, receipt.work_id, "retry", version)
                    retry_story_work(db, receipt.execution_id, receipt.work_id, "retry", version)
        from backend.story_store import commit_story_operation
        original = commit_story_operation
        def stop_after_commit(*args):
            original(*args)
            raise RuntimeError("after live commit")
        with self.transport():
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    self.assertEqual(story_activity(db, receipt.execution_id)["operations"][0]["validation_diagnostic"], failure)
                    with patch("backend.story_graph.commit_story_operation", side_effect=stop_after_commit):
                        with self.assertRaisesRegex(RuntimeError, "after live commit"):
                            await run_story_work(db, saver, fixture_story)
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    await run_story_work(db, saver, fixture_story)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (1,))
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.requests[0], self.requests[1])

    async def test_http_statuses_preserve_story_errors_and_single_reserved_attempt(self):
        from backend.openrouter import produce_live_story
        from backend.story_graph import StoryOwnerUnavailable, initial_story_state
        from backend.story_store import prepare_story_operation

        with self.transport(), open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                receipt = await self.start(db, saver)
            activation = initial_story_state(self.project, receipt.execution_id, live=True)["story_activation"]
            prepare_story_operation(db, receipt.execution_id, activation)
            for status in (302, 400, 401, 403, 408, 429, 500, 503):
                self.requests.clear()
                db.execute("UPDATE story_operations SET owner_attempts=0")
                transient = status in (408, 429, 500, 503)
                error = StoryOwnerUnavailable if transient else ValueError
                message = ("Story owner unavailable" if transient else
                           f"OpenRouter request rejected (HTTP {status}); check server configuration")
                with self.subTest(status=status), self.transport(lambda request, _: httpx.Response(
                        status, content=b"private-test-secret", headers={"location": "https://elsewhere.test/"})), \
                        self.assertRaises(error) as raised:
                    await produce_live_story(db, receipt.execution_id, activation, None, None, None)
                self.assertEqual(str(raised.exception), message)
                self.assertEqual(len(self.requests), 1)
                attempts, repairs, diagnostic = db.execute("SELECT owner_attempts,owner_repairs,owner_validation_diagnostic FROM story_operations").fetchone()
                self.assertEqual((attempts, repairs), (1, 0))
                self.assertIsNotNone(diagnostic)
                self.assertEqual(json.loads(diagnostic), {"attempt": 1, "stage": "http", "status_code": status,
                                                         "exception_type": None, "previous_validation": None})

    async def test_transport_after_repair_keeps_frozen_validation_and_exhaustion_classification(self):
        from backend.openrouter import produce_live_story
        from backend.story_graph import StoryOwnerUnavailable
        from backend.story_reads import story_activity

        def invalid_then_timeout(request, body):
            if len(self.requests) == 1:
                return httpx.Response(200, json={"choices": [{"finish_reason": "length", "message": {"content": "private"}}]})
            raise httpx.ReadTimeout("private-test-secret", request=request)

        with self.transport(invalid_then_timeout), open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                receipt = await self.start(db, saver)
                await run_story_work(db, saver, fixture_story)
                validation = {"attempt": 1, "stage": "finish", "code": "incomplete_output",
                              "paths": ["choices[0].finish_reason"], "finish_reason": "length"}
                failure = {"attempt": 2, "stage": "transport", "status_code": None,
                           "exception_type": "ReadTimeout", "previous_validation": validation}
                self.assertEqual(story_activity(db, receipt.execution_id)["operations"][0]["validation_diagnostic"], failure)
                self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs FROM story_operations").fetchone(), (2, 1))
                version = db.execute("SELECT work_version FROM execution_work").fetchone()[0]
                activation = db.execute("SELECT activation_id FROM story_operations").fetchone()[0]
                with self.assertRaises(StoryOwnerUnavailable):
                    await produce_live_story(db, receipt.execution_id, activation, None, None, None)
                self.assertEqual(len(self.requests), 2)
        with self.transport(), open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                self.assertEqual(story_activity(db, receipt.execution_id)["operations"][0]["validation_diagnostic"], failure)
                self.assertEqual(await run_story_work(db, saver, fixture_story), 0)
                retry_story_work(db, receipt.execution_id, receipt.work_id, "retry-repair", version)
                await run_story_work(db, saver, fixture_story)
                self.assertEqual(self.requests[1], self.requests[2])
                self.assertNotIn("ReadTimeout", self.requests[2]["messages"][-1]["content"])
                self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs FROM story_operations").fetchone(), (3, 1))

    async def test_wire_failures_capture_only_allowlisted_type_and_received_status(self):
        from backend import openrouter_client as provider

        async def check(handler, exception_type, status=None, seconds=1):
            with patch("backend.openrouter_client.httpx.AsyncClient", partial(httpx.AsyncClient, transport=httpx.MockTransport(handler))):
                with self.assertRaises(provider.OpenRouterUnavailable) as raised:
                    await provider.http("POST", "chat/completions", seconds, 1024, "{}", "test-secret")
            self.assertEqual(raised.exception.exception_type, exception_type)
            self.assertEqual(raised.exception.status_code, status)
            self.assertEqual(str(raised.exception), "OpenRouter unavailable")

        for kind in (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout,
                     httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError):
            with self.subTest(kind=kind.__name__):
                def fail(request):
                    raise kind("private-test-secret", request=request)
                await check(fail, kind.__name__)

        class Partial(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b"private-test-secret"
                raise httpx.ReadTimeout("private-test-secret")
        await check(lambda _: httpx.Response(200, stream=Partial()), "ReadTimeout", 200)

        async def slow(_):
            await asyncio.sleep(1)
        await check(slow, "TimeoutError", seconds=0.01)

        class PrivateExceptionName(httpx.ReadTimeout):
            pass
        def private_name(request):
            raise PrivateExceptionName("private-test-secret", request=request)
        await check(private_name, "HTTPError")

    async def test_oversized_completions_repair_or_exhaust_without_unsafe_commit_and_replay(self):
        from backend.domain import MAX_JSON_BYTES, sha256_digest
        from backend.openrouter import produce_live_story
        from backend.story_reads import story_activity

        story = fixture_story("Only the repaired Story", ["s1", "s2"], None, None).model_dump(mode="json")
        story.update(schema_version="2", generated_characters=[])
        for shot in story["shots"]:
            shot["subject_ids"] = ["fox"]
        valid = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(
            {"status": "ready", "story": story, "explanation": None})}}]}
        rejected_story = {**story, "hook": "Rejected oversized Story"}
        # A valid-looking creative result precedes oversized private provider data: never salvage it.
        prefix = (json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(
            {"status": "ready", "story": rejected_story, "explanation": None})}}]})[:-1] + ',"reasoning":"').encode()
        chunk = (b"private-test-secret" * 4000)[:65536]
        parent = self.root.parent
        for repair_succeeds in (True, False):
            with self.subTest(repair_succeeds=repair_succeeds):
                self.root = parent / ("cap-repaired" if repair_succeeds else "cap-exhausted")
                self.requests.clear()
                consumed, closed = [], []
                class Oversized(httpx.AsyncByteStream):
                    async def __aiter__(self):
                        yield prefix
                        for index in range(MAX_JSON_BYTES // len(chunk) + 3):
                            consumed.append(index)
                            yield chunk
                        yield b'"}'
                    async def aclose(self):
                        closed.append(True)
                diagnostic = {"attempt": 1 if repair_succeeds else 2, "stage": "envelope", "code": "invalid_envelope",
                              "paths": ["choices"], "finish_reason": "missing"}
                def respond(request, body):
                    if len(self.requests) == 2:
                        self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (0,))
                        self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs FROM story_operations").fetchone(), (2, 1))
                        self.assertEqual(story_activity(db, receipt.execution_id)["operations"][0]["validation_diagnostic"],
                                         {**diagnostic, "attempt": 1})
                        if repair_succeeds:
                            return httpx.Response(200, json=valid)
                    return httpx.Response(200, stream=Oversized())
                with self.transport(respond), open_database(self.root) as db:
                    async with open_saver(self.root, db) as saver:
                        receipt = await self.start(db, saver)
                        config = db.execute("SELECT owner_config FROM executions").fetchone()[0]
                        failure = None
                        try:
                            await run_story_work(db, saver, fixture_story)
                        except ValueError as error:
                            failure = error
                        attempts, repairs, diagnostic_body = db.execute(
                            "SELECT owner_attempts,owner_repairs,owner_validation_diagnostic FROM story_operations").fetchone()
                        self.assertEqual(((attempts, repairs), len(self.requests), diagnostic_body is not None),
                                         ((2, 1), 2, True))
                        self.assertEqual(json.loads(diagnostic_body), diagnostic)
                        self.assertEqual(diagnostic_body, json.dumps(diagnostic, sort_keys=True, separators=(",", ":")))
                        frozen = db.execute("SELECT owner_request,owner_request_digest FROM story_operations").fetchone()
                        self.assertEqual(frozen[0], json.dumps(self.requests[0], ensure_ascii=False, sort_keys=True, separators=(",", ":")))
                        self.assertEqual(frozen[1], sha256_digest(frozen[0].encode()))
                        self.assertEqual(self.requests[1]["messages"][:2], self.requests[0]["messages"])
                        repair = self.requests[1]["messages"][-1]["content"]
                        self.assertIn(json.dumps({**diagnostic, "attempt": 1}, sort_keys=True, separators=(",", ":")), repair)
                        self.assertNotIn("private-test-secret", diagnostic_body + repair + str(failure))
                        if repair_succeeds:
                            self.assertIsNone(failure)
                            saved = read_story(db, receipt.execution_id)
                            self.assertEqual(saved[1].hook, story["hook"])
                            self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (1,))
                        else:
                            self.assertIsInstance(failure, ValueError)
                            self.assertEqual(str(failure), "OpenRouter invalid_output: structured repair budget exhausted; "
                                             "envelope/invalid_envelope; paths=choices; finish_reason=missing")
                            self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (0,))
                self.assertEqual(len(closed), 1 if repair_succeeds else 2)
                self.assertLess(len(consumed), len(closed) * (MAX_JSON_BYTES // len(chunk) + 3))
                with self.transport(lambda *_: self.fail("Replay sent a third POST")), open_database(self.root) as db:
                    async with open_saver(self.root, db) as saver:
                        self.assertEqual(await self.start(db, saver), receipt)
                        self.assertEqual(await run_story_work(db, saver, fixture_story), 0)
                        if repair_succeeds:
                            self.assertEqual(read_story(db, receipt.execution_id), saved)
                        else:
                            activation = db.execute("SELECT activation_id FROM story_operations").fetchone()[0]
                            with self.assertRaisesRegex(ValueError, "invalid_output.*invalid_envelope.*missing") as replay_error:
                                await produce_live_story(db, receipt.execution_id, activation, None, None, None)
                            self.assertEqual(str(replay_error.exception), str(failure))
                        self.assertEqual(db.execute("SELECT owner_config FROM executions").fetchone()[0], config)
                        self.assertEqual(db.execute("SELECT owner_request,owner_request_digest FROM story_operations").fetchone(), frozen)
                        self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs,owner_validation_diagnostic FROM story_operations").fetchone(),
                                         (2, 1, diagnostic_body))
                        self.assertEqual(story_activity(db, receipt.execution_id)["operations"][0]["validation_diagnostic"], diagnostic)
                self.assertEqual(len(self.requests), 2)

    async def test_cancel_stops_live_await_and_prevents_binding(self):
        entered = asyncio.Event()
        stopped = asyncio.Event()
        async def slow(request):
            if request.url.path.endswith("/models"):
                return httpx.Response(200, json={"data": [{"id": "z-ai/glm-5.3-flash", "supported_parameters": ["response_format", "structured_outputs"]}]})
            entered.set()
            try:
                await asyncio.sleep(30)
            finally:
                stopped.set()
        with patch("backend.openrouter_client.httpx.AsyncClient", partial(httpx.AsyncClient, transport=httpx.MockTransport(slow))):
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await self.start(db, saver)
                    running = asyncio.create_task(run_story_work(db, saver, fixture_story))
                    await asyncio.wait_for(entered.wait(), 5)
                    cancel_story(db, receipt.execution_id, "cancel")
                    await asyncio.wait_for(running, 5)
                    self.assertTrue(stopped.is_set())
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (0,))
                    self.assertEqual(db.execute("SELECT outcome FROM execution_outcomes").fetchone(), ("cancelled",))

    async def test_unknown_model_fails_before_durable_start_without_substitution(self):
        with self.transport(), patch.dict(os.environ, {"LLM_MODEL": "invalid/model"}):
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    with self.assertRaisesRegex(ValueError, "model.*unavailable"):
                        await self.start(db, saver)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM executions").fetchone(), (0,))
        self.assertEqual(self.requests, [])

    async def test_missing_live_config_fails_closed_as_integrity_not_fixture_fallback(self):
        from backend.story_start import load_test_story_start
        with self.transport():
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await self.start(db, saver)
                    db.execute("UPDATE executions SET owner_config=NULL WHERE execution_id=?", (receipt.execution_id,))
                    with self.assertRaises(ValueError):
                        load_test_story_start(db, receipt.execution_id)
                    from backend.story_reads import story_activity
                    with self.assertRaisesRegex(ValueError, "Missing frozen"):
                        story_activity(db, receipt.execution_id)
        self.assertEqual(self.requests, [])

    async def test_commit_boundary_rechecks_live_subjects(self):
        from backend.story_graph import initial_story_state
        from backend.story_store import commit_story_operation, prepare_story_operation
        with self.transport():
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await self.start(db, saver)
                    state = initial_story_state(self.project, receipt.execution_id, live=True)
                    _, digest, _ = prepare_story_operation(db, receipt.execution_id, state["story_activation"])
                    story = fixture_story("Fox", ["s1", "s2"], None, None).model_dump(mode="json")
                    story.update(schema_version="2", generated_characters=[])
                    story["shots"][0]["subject_ids"] = ["undeclared"]
                    from backend.domain import StoryV2
                    with self.assertRaisesRegex(ValueError, "declared"):
                        commit_story_operation(db, receipt.execution_id, state["story_activation"], digest, str(uuid4()), StoryV2.model_validate(story))
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (0,))

    async def test_crash_reservations_exhaust_without_extra_calls_until_explicit_retry(self):
        def die(request, body):
            raise RuntimeError("simulated process loss before response")
        with self.transport(die):
            for _ in range(2):
                with open_database(self.root) as db:
                    async with open_saver(self.root, db) as saver:
                        receipt = await self.start(db, saver)
                        with self.assertRaisesRegex(RuntimeError, "simulated process loss"):
                            await run_story_work(db, saver, fixture_story)
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    await run_story_work(db, saver, fixture_story)
                    self.assertEqual(db.execute("SELECT blocked_reason FROM execution_work").fetchone(), ("owner_unavailable",))
                    self.assertEqual(db.execute("SELECT owner_attempts FROM story_operations").fetchone(), (2,))
                    version = db.execute("SELECT work_version FROM execution_work").fetchone()[0]
                    retry_story_work(db, receipt.execution_id, receipt.work_id, "retry", version)
                    retry_story_work(db, receipt.execution_id, receipt.work_id, "retry", version)
                    self.assertEqual(db.execute("SELECT owner_budget FROM story_operations").fetchone(), (4,))
        self.assertEqual(len(self.requests), 2)
        with self.transport():
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    await run_story_work(db, saver, fixture_story)
                    self.assertIsNotNone(read_story(db, receipt.execution_id))
        self.assertEqual(len(self.requests), 3)

    async def test_schema_valid_undeclared_subject_and_wrong_keys_do_not_commit(self):
        def invalid(request, body):
            story = fixture_story("Fox", ["extra"], None, None).model_dump(mode="json")
            if len(self.requests) == 2:
                story = fixture_story("Fox", ["s1", "s2"], None, None).model_dump(mode="json")
                story["shots"][0]["subject_ids"] = ["undeclared"]
            story.update(schema_version="2", generated_characters=[])
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"status": "ready", "story": story, "explanation": None})}}]})
        with self.transport(invalid):
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    await self.start(db, saver)
                    with self.assertRaisesRegex(ValueError, "invalid_output"):
                        await run_story_work(db, saver, fixture_story)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (0,))
        self.assertEqual(len(self.requests), 2)

    async def test_initial_needs_input_blocks_without_repairing_into_invented_ready_story(self):
        def missing(request, body):
            result = {"status": "needs_input", "story": None, "explanation": "The submitted subject descriptions contradict the requested action."}
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(result)}}]})
        with self.transport(missing):
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    await self.start(db, saver)
                    with self.assertRaisesRegex(ValueError, "Storytell needs_input"):
                        await run_story_work(db, saver, fixture_story)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (0,))
                    self.assertEqual(db.execute("SELECT owner_attempts,owner_repairs,owner_validation_diagnostic FROM story_operations").fetchone(), (1, 0, None))
        self.assertEqual(len(self.requests), 1)

    async def test_activity_reads_frozen_prompt_requests_and_saved_outputs_without_secrets(self):
        from backend.api import StoryActivity
        from backend.story_reads import story_activity
        with self.transport():
            with open_database(self.root) as db:
                async with open_saver(self.root, db) as saver:
                    receipt = await self.start(db, saver)
                    await run_story_work(db, saver, fixture_story)
                    review = self.review(db, receipt.execution_id)
                    accept_story_decision(db, receipt.execution_id, *review, "question", "clarify", "Why?")
                    await run_story_work(db, saver, fixture_story)
                    fixture = await start_test_story(db, saver, str(uuid4()), "fixture", "Fixture", ["s1"])
            with patch.dict(os.environ, {"LLM_MODEL": "different/model"}), patch("pathlib.Path.read_text", side_effect=AssertionError("disk prompt is not execution prompt")):
                with open_database(self.root) as db:
                    activity = StoryActivity.model_validate(story_activity(db, receipt.execution_id)).model_dump(mode="json")
                    self.assertEqual(activity["system_prompt"], self.requests[0]["messages"][0]["content"])
                    self.assertEqual(activity["model"], "z-ai/glm-5.3-flash")
                    self.assertEqual([o["action"] for o in activity["operations"]], ["generate", "clarify"])
                    self.assertEqual(activity["operations"][0]["input"], json.loads(self.requests[0]["messages"][1]["content"]))
                    self.assertEqual(activity["operations"][0]["status"], "saved")
                    self.assertIsNotNone(activity["operations"][0]["story_ref"])
                    self.assertEqual(activity["operations"][1]["response"]["explanation"], "The fox's choice pays off the hook.")
                    self.assertNotIn("test-secret", json.dumps(activity))
                    self.assertNotIn("reasoning", json.dumps(activity))
                    self.assertIsNone(story_activity(db, fixture.execution_id))
                    # Reads neither repair corrupt records nor borrow the current disk prompt.
                    db.execute("UPDATE story_operations SET owner_request_digest=? WHERE execution_id=?", ("sha256:" + "0" * 64, receipt.execution_id))
                    with self.assertRaisesRegex(ValueError, "request mismatch"):
                        story_activity(db, receipt.execution_id)


class EnvFileTests(unittest.TestCase):
    def test_explicit_allowlisted_loading_preserves_environment_and_never_evaluates_values(self):
        from backend.launch import load_env_file
        with tempfile.TemporaryDirectory(prefix="kinodel env loader ") as directory:
            path = Path(directory) / "config.env"
            path.write_text('OPENROUTER_API_KEY="file-test-secret"\nLLM_MODEL=z-ai/glm-5.3-flash\nUNRELATED=ignored\n', encoding="utf-8")
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "existing-secret"}, clear=True):
                load_env_file(path)
                self.assertEqual(os.environ["OPENROUTER_API_KEY"], "existing-secret")
                self.assertEqual(os.environ["LLM_MODEL"], "z-ai/glm-5.3-flash")
                self.assertNotIn("UNRELATED", os.environ)
            path.write_text('OPENROUTER_API_KEY="invalid-secret\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 1") as failure:
                load_env_file(path)
            self.assertNotIn("invalid-secret", str(failure.exception))


if __name__ == "__main__":
    unittest.main()
