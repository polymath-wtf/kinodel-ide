"""Bounded Wardrobe HTTP adapter, with mocked transport only (no paid calls)."""

import asyncio
import base64
from copy import deepcopy
import importlib.util
from io import BytesIO
import json
import os
import struct
import unittest
from functools import partial
from unittest.mock import patch
import zlib

import httpx
from PIL import Image

from backend.domain import MAX_JSON_BYTES, canonical_json, sha256_digest
from tests.test_wardrobe import draft_data, input_data


MODEL = "test/wardrobe"


def supplied_input():
    supplied = input_data()
    supplied["image_evidence"] = []
    return supplied


def capability():
    return {"id": MODEL, "supported_parameters": ["response_format", "structured_outputs"],
            "architecture": {"input_modalities": ["text", "image"]},
            "reasoning": {"supported_efforts": ["low", "high"]}}


def envelope(result=None):
    result = result or {"status": "ready", "plan": draft_data(), "explanation": None}
    return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(result)}}]}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def visual_input(formats=("PNG", "JPEG", "WEBP")):
    supplied = supplied_input()
    bodies = {}
    for index, format in enumerate(formats):
        output = BytesIO()
        Image.new("RGB", (24 + index, 16 + index), (index * 60, 50, 100)).save(output, format=format)
        body = output.getvalue()
        alias = f"  evidence / {index}: 🦊  "
        bodies[alias] = body
        supplied["image_evidence"].append({
            "alias": alias, "role": "portrait", "subject_ids": ["hero"],
            "ref": {"source_id": f"../opaque-image-{index}", "revision_id": "r1",
                    "digest": sha256_digest(body), "mime_type": Image.MIME[format],
                    "byte_length": len(body), "width": 24 + index, "height": 16 + index}})
    return supplied, bodies


class WardrobeOpenRouterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret", "LLM_MODEL": MODEL})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.requests = []

    def transport(self, output=None, model=None, catalog=None):
        def respond(request):
            self.requests.append(request)
            if request.method == "GET":
                self.assertEqual(str(request.url), "https://openrouter.ai/api/v1/models")
                self.assertNotIn("authorization", request.headers)
                if callable(catalog):
                    return catalog(request)
                return httpx.Response(200, json={"data": [model or capability()]})
            self.assertEqual(request.method, "POST")
            self.assertEqual(str(request.url), "https://openrouter.ai/api/v1/chat/completions")
            self.assertEqual(request.headers["authorization"], "Bearer test-secret")
            if callable(output):
                return output(request)
            return httpx.Response(200, json=output if output is not None else envelope())
        factory = partial(httpx.AsyncClient, transport=httpx.MockTransport(respond))
        def client(**options):
            self.assertFalse(options["follow_redirects"])
            self.assertFalse(options["trust_env"])
            self.assertIn(options["timeout"], (15, 60))
            return factory(**options)
        return patch("backend.openrouter_client.httpx.AsyncClient", client)

    async def test_zero_image_freezes_exact_request_and_returns_typed_plan_in_one_call(self):
        self.assertIsNotNone(importlib.util.find_spec("backend.openrouter_wardrobe"),
                             "The concrete frozen Wardrobe adapter is absent")
        from backend import openrouter_wardrobe as adapter
        from backend.wardrobe import VisualAnchorPlanV1

        self.assertIsNotNone(importlib.util.find_spec("backend.openrouter_client"), "Shared provider adapter is absent")
        from backend import openrouter_client as provider
        supplied = supplied_input()
        with self.transport(), patch.object(provider, "structured_request", wraps=provider.structured_request) as builder, \
                patch.object(provider, "model_metadata", wraps=provider.model_metadata) as metadata, \
                patch.object(provider, "parse_completion", wraps=provider.parse_completion) as parser:
            frozen = await adapter.prepare_wardrobe_request(supplied, {})
            config = adapter.read_wardrobe_config(frozen)
            result = await adapter.complete_wardrobe(config)
        self.assertIsInstance(result, VisualAnchorPlanV1)
        self.assertEqual(result.narrative_ref.model_dump(mode="json"), supplied["narrative_ref"])
        self.assertEqual([r.method for r in self.requests], ["GET", "POST"])
        self.assertEqual(self.requests[1].content, config.base_request.encode())
        request = json.loads(config.base_request)
        self.assertEqual(request["model"], MODEL)
        self.assertEqual(request["reasoning"], {"effort": "low"})
        self.assertEqual(request["provider"], {"require_parameters": True})
        self.assertFalse(request["stream"])
        self.assertEqual(request["max_tokens"], 8192)
        self.assertEqual(request["messages"][1]["content"], [{"type": "text", "text": json.dumps(
            supplied, ensure_ascii=False, sort_keys=True, separators=(",", ":"))}])
        self.assertEqual(request["response_format"]["json_schema"]["schema"], config.result_schema)
        self.assertEqual(config.base_request_digest, sha256_digest(config.base_request.encode()))
        self.assertNotIn("test-secret", frozen)
        self.assertGreaterEqual(builder.call_count, 2)  # Frozen reads reconstruct the same shared request.
        self.assertEqual(metadata.call_count, 1)
        self.assertEqual(parser.call_count, 1)

    async def test_every_visual_alias_has_original_labelled_bytes_in_declared_order(self):
        from backend import openrouter_wardrobe as adapter
        supplied, bodies = visual_input()
        before = deepcopy((supplied, bodies))
        # Mapping order must not change the explicitly declared evidence order.
        with self.transport():
            frozen = await adapter.prepare_wardrobe_request(supplied, dict(reversed(list(bodies.items()))))
            config = adapter.read_wardrobe_config(frozen)
            result = await adapter.complete_wardrobe(frozen)
        content = json.loads(config.base_request)["messages"][1]["content"]
        self.assertEqual(json.loads(content[0]["text"]), supplied)
        self.assertEqual(len(content), 1 + 2 * len(bodies))
        for index, image in enumerate(supplied["image_evidence"]):
            label, picture = content[1 + 2 * index:3 + 2 * index]
            self.assertEqual(label, {"type": "text", "text": encoded(image)})
            self.assertEqual(picture, {"type": "image_url", "image_url": {"url":
                f'data:{image["ref"]["mime_type"]};base64,' + base64.b64encode(bodies[image["alias"]]).decode("ascii")}})
        self.assertEqual((supplied, bodies), before)
        self.assertEqual(result.units[0].references, [])  # Evidence is not automatic render conditioning.
        self.assertEqual([r.method for r in self.requests], ["GET", "POST"])

    async def test_missing_extra_or_wrong_image_bytes_never_reach_post(self):
        from backend import openrouter_wardrobe as adapter
        supplied, bodies = visual_input(("PNG",))
        alias = next(iter(bodies))
        for images in ({}, {**bodies, "undeclared": bodies[alias]}, {alias: b"wrong"},
                       {alias: bytearray(bodies[alias])}, {alias: "https://example.test/image"}):
            with self.subTest(images=list(images)), self.transport():
                with self.assertRaisesRegex(ValueError, "Wardrobe"):
                    await adapter.prepare_wardrobe_request(supplied, images)
        with self.transport(), self.assertRaises(ValueError):
            await adapter.prepare_wardrobe_request(supplied_input(), bodies)
        self.assertFalse(any(r.method == "POST" for r in self.requests))

    async def test_actual_mime_dimensions_length_digest_and_decode_are_checked(self):
        from backend import openrouter_wardrobe as adapter
        supplied, bodies = visual_input(("PNG",))
        alias = next(iter(bodies))
        for changes in ({"mime_type": "image/jpeg"}, {"width": 25}, {"height": 17},
                        {"byte_length": len(bodies[alias]) + 1}, {"digest": sha256_digest(b"wrong")}):
            changed = deepcopy(supplied)
            changed["image_evidence"][0]["ref"].update(changes)
            with self.subTest(changes=changes), self.transport(), self.assertRaises(ValueError):
                await adapter.prepare_wardrobe_request(changed, bodies)
        for raw in (b"not an image", bodies[alias][:48]):
            changed = deepcopy(supplied)
            changed["image_evidence"][0]["ref"].update(byte_length=len(raw), digest=sha256_digest(raw))
            with self.subTest(raw=raw[:10]), self.transport(), self.assertRaises(ValueError):
                await adapter.prepare_wardrobe_request(changed, {alias: raw})
        self.assertFalse(any(r.method == "POST" for r in self.requests))

    async def test_valid_container_with_undecodable_pixels_is_rejected(self):
        from backend import openrouter_wardrobe as adapter
        supplied, bodies = visual_input(("PNG",))
        alias = next(iter(bodies))
        raw = bodies[alias]
        chunks = [raw[:8]]
        offset = 8
        while offset < len(raw):
            size = struct.unpack(">I", raw[offset:offset + 4])[0]
            kind = raw[offset + 4:offset + 8]
            chunk = raw[offset:offset + 12 + size]
            if kind == b"IDAT":
                pixels = b"not a zlib stream"
                chunk = (struct.pack(">I", len(pixels)) + kind + pixels
                         + struct.pack(">I", zlib.crc32(kind + pixels)))
            chunks.append(chunk)
            offset += size + 12
        raw = b"".join(chunks)
        with Image.open(BytesIO(raw)) as image:
            image.verify()  # Correct container CRC is insufficient.
        with Image.open(BytesIO(raw)) as image, self.assertRaises(OSError):
            image.load()
        supplied["image_evidence"][0]["ref"].update(byte_length=len(raw), digest=sha256_digest(raw))
        with self.transport(), self.assertRaisesRegex(ValueError, "Wardrobe"):
            await adapter.prepare_wardrobe_request(supplied, {alias: raw})
        self.assertFalse(any(r.method == "POST" for r in self.requests))

    async def test_image_byte_dimension_pixel_animation_limits_reuse_character_bounds(self):
        from backend import openrouter_wardrobe as adapter
        from backend.characters import MAX_IMAGE_BYTES, MAX_IMAGE_PIXELS, MAX_IMAGE_SIDE
        supplied, bodies = visual_input(("PNG",))
        alias = next(iter(bodies))
        for size in ((MAX_IMAGE_SIDE + 1, 1), (4001, 4001)):
            self.assertTrue(size[0] > MAX_IMAGE_SIDE or size[0] * size[1] > MAX_IMAGE_PIXELS)
            output = BytesIO()
            Image.new("RGB", size).save(output, format="PNG")
            raw = output.getvalue()
            changed = deepcopy(supplied)
            changed["image_evidence"][0]["ref"].update(
                byte_length=len(raw), digest=sha256_digest(raw), width=size[0], height=size[1])
            with self.subTest(size=size), self.transport(), self.assertRaises(ValueError):
                await adapter.prepare_wardrobe_request(changed, {alias: raw})
        raw = b"x" * (MAX_IMAGE_BYTES + 1)
        changed = deepcopy(supplied)
        changed["image_evidence"][0]["ref"].update(byte_length=len(raw), digest=sha256_digest(raw))
        with self.transport(), self.assertRaises(ValueError):
            await adapter.prepare_wardrobe_request(changed, {alias: raw})
        output = BytesIO()
        frames = [Image.new("RGB", (24, 16), color) for color in ("red", "blue")]
        frames[0].save(output, format="PNG", save_all=True, append_images=frames[1:], duration=20)
        raw = output.getvalue()
        changed = deepcopy(supplied)
        changed["image_evidence"][0]["ref"].update(byte_length=len(raw), digest=sha256_digest(raw))
        with self.transport(), self.assertRaises(ValueError):
            await adapter.prepare_wardrobe_request(changed, {alias: raw})
        self.assertFalse(any(r.method == "POST" for r in self.requests))

    async def test_exact_model_structured_reasoning_and_visual_capabilities_fail_closed(self):
        from backend import openrouter_wardrobe as adapter
        supplied, bodies = visual_input(("PNG",))
        variants = [
            {**capability(), "id": "other/model"},
            {**capability(), "supported_parameters": ["response_format"]},
            {**capability(), "supported_parameters": ["structured_outputs"]},
            {**capability(), "reasoning": {"supported_efforts": ["high"]}},
            {**capability(), "architecture": {"input_modalities": ["text"]}},
            {**capability(), "architecture": {}},
        ]
        for model in variants:
            with self.subTest(model=model), self.transport(model=model), self.assertRaises(ValueError):
                await adapter.prepare_wardrobe_request(supplied, bodies)
        self.assertFalse(any(r.method == "POST" for r in self.requests))
        # Text-only preparation requires structured output, not image capability or advertised efforts.
        with self.transport(model={"id": MODEL, "supported_parameters": ["response_format", "structured_outputs"]}):
            await adapter.prepare_wardrobe_request(supplied_input(), {})

    async def test_read_and_call_use_frozen_model_input_prompt_schema_images_not_fresh_resources(self):
        from backend import openrouter_wardrobe as adapter
        supplied, bodies = visual_input(("PNG",))
        with self.transport():
            frozen = await adapter.prepare_wardrobe_request(supplied, bodies)
        supplied["text_context"].clear()
        bodies.clear()
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": "other/model"}), \
                patch("pathlib.Path.read_text", side_effect=AssertionError("frozen prompt only")):
            config = adapter.read_wardrobe_config(frozen)  # Reads need no credential.
            self.assertEqual(canonical_json(config).decode(), frozen)
        with self.transport(catalog=lambda _: self.fail("Replay must not fetch catalog")), \
                patch.dict(os.environ, {"LLM_MODEL": "other/model"}), \
                patch("pathlib.Path.read_text", side_effect=AssertionError("frozen prompt only")):
            await adapter.complete_wardrobe(config)
        self.assertEqual([r.method for r in self.requests], ["GET", "POST"])
        self.assertEqual(self.requests[-1].content, config.base_request.encode())

    async def test_configuration_pin_and_request_tampering_are_rejected_before_post(self):
        from backend import openrouter_wardrobe as adapter
        with self.transport():
            frozen = await adapter.prepare_wardrobe_request(supplied_input(), {})
        original = json.loads(frozen)
        for field in ("input_digest", "prompt_digest", "result_schema_digest", "model_metadata_digest", "base_request_digest"):
            changed = deepcopy(original)
            changed[field] = sha256_digest(b"corrupt")
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "frozen"):
                adapter.read_wardrobe_config(encoded(changed))
        for mutate in (
            lambda data: data.update(model="other/model"),
            lambda data: data.update(timeout_seconds=61),
            lambda data: data.update(max_tokens=8193),
            lambda data: data["wardrobe_input"]["text_context"].clear(),
            lambda data: data["result_schema"].clear(),
        ):
            changed = deepcopy(original)
            mutate(changed)
            with self.assertRaisesRegex(ValueError, "frozen"):
                adapter.read_wardrobe_config(encoded(changed))
        for mutate in (
            lambda request: request.update(model="other/model"),
            lambda request: request.update(tools=[]),
            lambda request: request["messages"][1]["content"][0].update(text="private corrupted input"),
        ):
            changed = deepcopy(original)
            request = json.loads(changed["base_request"])
            mutate(request)
            changed["base_request"] = encoded(request)
            changed["base_request_digest"] = sha256_digest(changed["base_request"].encode())
            with self.assertRaisesRegex(ValueError, "frozen"):
                adapter.read_wardrobe_config(encoded(changed))
        config = adapter.read_wardrobe_config(frozen)
        config.model_metadata.supported_parameters.clear()
        with self.transport(), self.assertRaisesRegex(ValueError, "frozen"):
            await adapter.complete_wardrobe(config)
        self.assertEqual([r.method for r in self.requests], ["GET"])
        for body in (frozen + " ", frozen.replace('"adapter_version":"1"', '"adapter_version":"1","adapter_version":"1"')):
            with self.assertRaisesRegex(ValueError, "frozen"):
                adapter.read_wardrobe_config(body)

    async def test_frozen_visual_url_pin_order_and_labels_are_revalidated(self):
        from backend import openrouter_wardrobe as adapter
        supplied, bodies = visual_input(("PNG", "JPEG"))
        with self.transport():
            frozen = await adapter.prepare_wardrobe_request(supplied, bodies)
        for mutate in (
            lambda content: content[2]["image_url"].update(url="https://example.test/image"),
            lambda content: content[2]["image_url"].update(url="data:image/png;base64,bm90LWFuLWltYWdl"),
            lambda content: content[2]["image_url"].update(url=content[4]["image_url"]["url"]),
            lambda content: content[1].update(text="unbound alias"),
            lambda content: content.pop(),
            lambda content: content.append(deepcopy(content[2])),
        ):
            changed = json.loads(frozen)
            request = json.loads(changed["base_request"])
            mutate(request["messages"][1]["content"])
            changed["base_request"] = encoded(request)
            changed["base_request_digest"] = sha256_digest(changed["base_request"].encode())
            with self.assertRaisesRegex(ValueError, "frozen"):
                adapter.read_wardrobe_config(encoded(changed))

    async def test_valid_nonready_outputs_are_typed_and_never_repaired_away(self):
        from backend import openrouter_wardrobe as adapter
        from backend.domain import OwnerResponseV1
        for status in ("needs_input", "out_of_scope"):
            self.requests.clear()
            result = {"status": status, "plan": None, "explanation": "Canon conflicts with the requested costume."}
            with self.transport(envelope(result)):
                config = await adapter.prepare_wardrobe_request(supplied_input(), {})
                response = await adapter.complete_wardrobe(config)
            self.assertEqual(response, OwnerResponseV1(status=status, explanation=result["explanation"]))
            self.assertEqual([r.method for r in self.requests], ["GET", "POST"])

    async def test_invalid_envelope_json_schema_subject_parent_and_capability_reject_once_safely(self):
        from backend import openrouter_wardrobe as adapter
        private = "private-provider-content-test-secret"
        wrong_subject = draft_data()
        wrong_subject["units"][0]["subject_ids"] = [private]
        wrong_parent = draft_data()
        wrong_parent["units"][2]["references"][0]["source"]["unit_key"] = private
        invalid_ref = draft_data()
        invalid_ref["units"][0]["references"] = [{"source": {"kind": "input", "alias": private},
                                                "role": "portrait", "take": [], "ignore": []}]
        variants = [None, [], {}, {"choices": []}, {"choices": envelope()["choices"] * 2},
                    {"choices": [{"finish_reason": "stop", "message": []}]},
                    {"choices": [{"finish_reason": "stop", "message": {"content": [{"text": private}]}}]},
                    {"choices": [{"finish_reason": "stop", "message": {"content": None}}]},
                    {"choices": [{"finish_reason": "stop", "message": {"content": private}}]}]
        for finish in (None, "length", "content_filter", "tool_calls", "function_call", "error", private, {}):
            changed = envelope()
            changed["choices"][0]["finish_reason"] = finish
            variants.append(changed)
        for message in ({"tool_calls": [{"arguments": private}]}, {"function_call": {"arguments": private}},
                        {"tool_calls": 0}, {"tool_calls": ""}, {"function_call": {}}, {"role": "user"},
                        {"content": '{"status":"ready","status":"ready","plan":null,"explanation":null}'},
                        {"content": '{"status":"needs_input","plan":null,"explanation":"\\ud800"}'}):
            changed = envelope()
            changed["choices"][0]["message"].update(message)
            variants.append(changed)
        for result in ({"status": "ready", "plan": None, "explanation": None},
                       {"status": "needs_input", "plan": draft_data(), "explanation": private},
                       {"status": "ready", "plan": {**draft_data(), "approved": True}, "explanation": None},
                       *[{"status": "ready", "plan": draft, "explanation": None}
                         for draft in (wrong_subject, wrong_parent, invalid_ref)]):
            variants.append(envelope(result))
        with self.transport():
            config = await adapter.prepare_wardrobe_request(supplied_input(), {})
        for output in variants:
            self.requests.clear()
            with self.subTest(output=str(output)[:60]), self.transport(
                    lambda _: httpx.Response(200, content=json.dumps(output).encode())):
                with self.assertRaisesRegex(ValueError, "invalid_output") as raised:
                    await adapter.complete_wardrobe(config)
                self.assertNotIn(private, str(raised.exception))
                self.assertEqual([r.method for r in self.requests], ["POST"])

    async def test_transport_status_malformed_and_transient_errors_do_not_expose_provider_data(self):
        from backend import openrouter_wardrobe as adapter
        with self.transport():
            config = await adapter.prepare_wardrobe_request(supplied_input(), {})
        for status in (302, 400, 401, 403, 408, 429, 500, 503):
            self.requests.clear()
            def failure(_):
                return httpx.Response(status, content=b"private-test-secret", headers={"location": "https://elsewhere.test/"})
            error = adapter.WardrobeOwnerUnavailable if status in (408, 429, 500, 503) else ValueError
            with self.subTest(status=status), self.transport(failure), self.assertRaises(error) as raised:
                await adapter.complete_wardrobe(config)
            self.assertNotIn("private", str(raised.exception))
            self.assertNotIn("test-secret", str(raised.exception))
            self.assertEqual([r.method for r in self.requests], ["POST"])
        for error in (httpx.ReadTimeout, httpx.ConnectError):
            self.requests.clear()
            def unavailable(request):
                raise error("private-test-secret", request=request)
            with self.transport(unavailable), self.assertRaises(adapter.WardrobeOwnerUnavailable) as raised:
                await adapter.complete_wardrobe(config)
            self.assertNotIn("private", str(raised.exception))
            self.assertEqual([r.method for r in self.requests], ["POST"])
        with self.transport(lambda _: httpx.Response(200, content=b"private-test-secret")), \
                self.assertRaisesRegex(ValueError, "invalid_output") as raised:
            await adapter.complete_wardrobe(config)
        self.assertNotIn("private", str(raised.exception))

    async def test_non_json_constants_in_metadata_or_envelope_are_rejected(self):
        from backend import openrouter_wardrobe as adapter
        with self.transport(catalog=lambda _: httpx.Response(200, content=encoded(
                {"data": [capability()], "other": float("nan")}).encode())), \
                self.assertRaises(ValueError):
            await adapter.prepare_wardrobe_request(supplied_input(), {})
        with self.transport():
            config = await adapter.prepare_wardrobe_request(supplied_input(), {})
        self.requests.clear()
        with self.transport(lambda _: httpx.Response(200, content=encoded(
                {**envelope(), "other": float("nan")}).encode())), \
                self.assertRaisesRegex(ValueError, "invalid_output"):
            await adapter.complete_wardrobe(config)
        self.assertEqual([r.method for r in self.requests], ["POST"])

    async def test_total_deadline_cancels_one_request_without_automatic_retry(self):
        from backend import openrouter_wardrobe as adapter
        with self.transport():
            config = await adapter.prepare_wardrobe_request(supplied_input(), {})
        self.requests.clear()
        cancelled = []
        async def slow(request):
            self.requests.append(request)
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.append(True)
        original_timeout = asyncio.timeout
        def short_timeout(seconds):
            self.assertEqual(seconds, 60)
            return original_timeout(0.01)
        with patch("backend.openrouter_client.httpx.AsyncClient",
                   partial(httpx.AsyncClient, transport=httpx.MockTransport(slow))), \
                patch("backend.openrouter_client.asyncio.timeout", side_effect=short_timeout), \
                self.assertRaises(adapter.WardrobeOwnerUnavailable):
            await adapter.complete_wardrobe(config)
        self.assertEqual([r.method for r in self.requests], ["POST"])
        self.assertEqual(cancelled, [True])

    async def test_response_cap_stops_stream_and_closes_without_returning_output(self):
        from backend import openrouter_wardrobe as adapter
        with self.transport():
            config = await adapter.prepare_wardrobe_request(supplied_input(), {})
        self.requests.clear()
        consumed, closed = [], []
        class Oversized(httpx.AsyncByteStream):
            async def __aiter__(self):
                for index in range(MAX_JSON_BYTES // 65536 + 3):
                    consumed.append(index)
                    yield b"x" * 65536
            async def aclose(self):
                closed.append(True)
        with self.transport(lambda _: httpx.Response(200, stream=Oversized())), \
                self.assertRaisesRegex(ValueError, "response.*limit"):
            await adapter.complete_wardrobe(config)
        self.assertLess(len(consumed), MAX_JSON_BYTES // 65536 + 3)
        self.assertEqual(closed, [True])
        self.assertEqual([r.method for r in self.requests], ["POST"])

    async def test_malformed_or_oversized_metadata_and_invalid_environment_are_safe(self):
        from backend import openrouter_wardrobe as adapter
        for catalog in (None, [], {}, {"data": None}, {"data": [None]}, {"data": [capability(), capability()]},
                        {"data": [{**capability(), "supported_parameters": "structured_outputs response_format"}]}):
            with self.subTest(catalog=catalog), self.transport(catalog=lambda _: httpx.Response(200, json=catalog)), \
                    self.assertRaisesRegex(ValueError, "OpenRouter") as raised:
                await adapter.prepare_wardrobe_request(supplied_input(), {})
            self.assertNotIn("test-secret", str(raised.exception))
        with self.transport(catalog=lambda _: httpx.Response(200, content=b"x" * (16 * MAX_JSON_BYTES + 1))), \
                self.assertRaisesRegex(ValueError, "response.*limit"):
            await adapter.prepare_wardrobe_request(supplied_input(), {})
        for environment in ({"LLM_MODEL": ""}, {"LLM_MODEL": "model\nprivate"}, {"OPENROUTER_API_KEY": ""},
                            {"OPENROUTER_API_KEY": "invalid key"}):
            with self.subTest(environment=environment), patch.dict(os.environ, environment), self.transport(), \
                    self.assertRaises(ValueError) as raised:
                await adapter.prepare_wardrobe_request(supplied_input(), {})
            self.assertNotIn("private", str(raised.exception))
        self.assertFalse(any(r.method == "POST" for r in self.requests))

    async def test_unusable_prompt_errors_are_safe_without_returning_prompt_or_context(self):
        from backend import openrouter_wardrobe as adapter
        for prompt in ("", "private-test-secret " * 20000):
            with self.transport(), patch("pathlib.Path.read_text", return_value=prompt), \
                    self.assertRaises(ValueError) as raised:
                await adapter.prepare_wardrobe_request(supplied_input(), {})
            self.assertNotIn("private-test-secret", str(raised.exception))
            self.assertNotIn("traveler", str(raised.exception))
        self.assertFalse(any(r.method == "POST" for r in self.requests))

    async def test_mutable_typed_input_and_request_capacity_are_checked_before_post(self):
        from backend import openrouter_wardrobe as adapter
        from backend.wardrobe import WardrobeInputV1
        supplied = WardrobeInputV1.model_validate(supplied_input())
        supplied.story.shots[0].subject_ids.append("undeclared")
        with self.transport(), self.assertRaises(ValueError):
            await adapter.prepare_wardrobe_request(supplied, {})
        supplied, bodies = visual_input(("PNG",))
        alias = next(iter(bodies))
        output = BytesIO()
        # Deterministic noisy pixels exceed the 1 MiB base64-request ceiling, not image limits.
        import random
        Image.frombytes("RGB", (600, 600), random.Random(1).randbytes(600 * 600 * 3)).save(output, format="PNG")
        raw = output.getvalue()
        supplied["image_evidence"][0]["ref"].update(
            width=600, height=600, byte_length=len(raw), digest=sha256_digest(raw))
        with self.transport(), self.assertRaisesRegex(ValueError, "limit|large"):
            await adapter.prepare_wardrobe_request(supplied, {alias: raw})
        self.assertEqual(self.requests, [])  # Oversized evidence must stop during bounded local preparation.


if __name__ == "__main__":
    unittest.main()
