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
from tests.test_wardrobe import draft_data, full_batch_draft, full_batch_input, input_data


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


def large_png(size=(768, 960)):
    import random
    pixels = bytearray(size[0] * size[1] * 3)
    noise = random.Random(1).randbytes(size[0] * size[1] * 2)
    pixels[0::3], pixels[1::3] = noise[0::2], noise[1::2]
    output = BytesIO()
    Image.frombytes("RGB", size, bytes(pixels)).save(output, format="PNG")
    return output.getvalue()


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
            self.assertIn(options["timeout"], (15, 60, 180))
            return factory(**options)
        return patch("backend.openrouter_client.httpx.AsyncClient", client)

    async def test_v2_timeout_is_bounded_and_historical_timeout_rejects(self):
        from backend import openrouter_wardrobe as adapter
        with self.transport():
            frozen = await adapter.prepare_wardrobe_request(supplied_input(), {})
        self.assertEqual(adapter.read_wardrobe_config(frozen).timeout_seconds, 180)
        historical = json.loads(frozen)
        historical["timeout_seconds"] = 60
        body = encoded(historical)
        with self.assertRaisesRegex(ValueError, "frozen"):
            adapter.read_wardrobe_config(body)

    async def test_full_five_batch_and_frozen_prompt_capabilities_are_supplied_before_completion(self):
        from backend import openrouter_wardrobe as adapter
        from backend.domain import parse_json_model
        from backend.wardrobe import VisualAnchorPlanV2, WardrobeResultV2
        supplied, draft = full_batch_input(), full_batch_draft()
        with self.transport(envelope({"status": "ready", "plan": draft, "explanation": None})):
            settings = adapter.pin_wardrobe_settings(MODEL)
            frozen = await adapter.prepare_wardrobe_request(supplied, {}, settings=settings)
            config = adapter.read_wardrobe_config(frozen)
            plan = await adapter.complete_wardrobe(frozen)
        self.assertEqual(settings.adapter_version, "2")
        self.assertEqual(config.result_schema, WardrobeResultV2.model_json_schema())
        request = json.loads(self.requests[-1].content)
        prompt = request["messages"][0]["content"]
        self.assertEqual(prompt, settings.system_prompt)
        for term in ("WardrobeInputV2", "WardrobeResultV2", "batch_prompt", "anchor-basics.v2",
                     "hero-face", "location", "hero-sheet", "txt2img", "img2img", "batch_unit",
                     "portrait/background", "1–256", "filename"):
            self.assertIn(term, prompt)
        for term in ("WardrobeInputV1", "WardrobeResultV1", "anchor-basics.v1", "anchor_unit"):
            self.assertNotIn(term, prompt)
        self.assertEqual(plan.schema_version, "2")
        self.assertEqual(plan.narrative_ref.model_dump(mode="json"), supplied["narrative_ref"])
        self.assertEqual(plan.model_dump(mode="json")["batch_prompt"], draft["batch_prompt"])
        self.assertEqual(config.prompt_digest, sha256_digest(prompt.encode()))
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": ""}), \
                patch("pathlib.Path.read_text", side_effect=AssertionError("exact DTO reopen only")):
            self.assertEqual(parse_json_model(canonical_json(plan), VisualAnchorPlanV2), plan)
        self.assertEqual([r.method for r in self.requests], ["GET", "POST"])

    async def test_old_adapter_schema_input_request_and_settings_reject_offline_before_http(self):
        from backend import openrouter_wardrobe as adapter
        with self.transport():
            frozen = await adapter.prepare_wardrobe_request(supplied_input(), {})
        original = json.loads(frozen)
        variants = []
        old_adapter = deepcopy(original)
        old_adapter["adapter_version"] = "1"
        variants.append(old_adapter)
        old_schema = deepcopy(original)
        old_schema["result_schema"] = {"title": "WardrobeResultV1", "type": "object"}
        old_schema["result_schema_digest"] = sha256_digest(encoded(old_schema["result_schema"]).encode())
        variants.append(old_schema)
        old_input = deepcopy(original)
        old_input["wardrobe_input"].update(schema_version="1", capability_set="anchor-basics.v1")
        old_input["input_digest"] = sha256_digest(encoded(old_input["wardrobe_input"]).encode())
        variants.append(old_input)
        old_request = deepcopy(original)
        request = json.loads(old_request["base_request"])
        request["messages"][1]["content"][0]["text"] = encoded(old_input["wardrobe_input"])
        old_request["base_request"] = encoded(request)
        old_request["base_request_digest"] = sha256_digest(old_request["base_request"].encode())
        variants.append(old_request)
        self.requests.clear()
        with self.transport(), patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "LLM_MODEL": ""}), \
                patch("pathlib.Path.read_text", side_effect=AssertionError("offline config read")):
            for changed in variants:
                with self.subTest(version=changed["adapter_version"]), self.assertRaisesRegex(ValueError, "frozen"):
                    adapter.read_wardrobe_config(encoded(changed))
                with self.assertRaisesRegex(ValueError, "frozen"):
                    await adapter.complete_wardrobe(encoded(changed))
        with self.transport():
            with self.assertRaises(ValueError):
                await adapter.prepare_wardrobe_request(old_input["wardrobe_input"], {})
            settings = adapter.pin_wardrobe_settings(MODEL).model_dump(mode="json")
            settings["adapter_version"] = "1"
            with self.assertRaises(ValueError):
                await adapter.prepare_wardrobe_request(supplied_input(), {}, settings=settings)
        self.assertEqual(self.requests, [])

    async def test_invalid_output_and_explicit_repair_keep_exact_v2_schema_and_base_request(self):
        from backend import openrouter_wardrobe as adapter
        from backend.wardrobe import WardrobeResultV2
        with self.transport():
            frozen = await adapter.prepare_wardrobe_request(supplied_input(), {})
        self.requests.clear()
        malformed = envelope({"status": "ready", "plan": {"direction": {}, "units": []}, "explanation": None})
        with self.transport(malformed), self.assertRaises(adapter.WardrobeInvalidOutput):
            await adapter.complete_wardrobe(frozen)
        self.assertEqual([r.method for r in self.requests], ["POST"])
        instruction = adapter.REPAIR_INSTRUCTION
        repair = adapter.prepare_wardrobe_repair(frozen, instruction)
        with self.transport(), patch("pathlib.Path.read_text", side_effect=AssertionError("frozen repair only")):
            result = await adapter.complete_wardrobe(frozen, repair_instruction=instruction)
        config = adapter.read_wardrobe_config(frozen)
        request, base = json.loads(repair), json.loads(config.base_request)
        self.assertEqual(request["messages"][:-1], base["messages"])
        self.assertEqual(request["messages"][-1], {"role": "user", "content": instruction})
        self.assertEqual(request["response_format"], base["response_format"])
        self.assertEqual(request["response_format"]["json_schema"]["schema"], WardrobeResultV2.model_json_schema())
        self.assertEqual(self.requests[-1].content, repair.encode())
        self.assertEqual([r.method for r in self.requests], ["POST", "POST"])
        self.assertEqual(result.schema_version, "2")
        self.assertIn("batch_prompt", instruction)
        self.assertIn("batch_unit", instruction)

    async def test_failed_http_measures_actual_phase_without_private_text(self):
        from backend import openrouter_client as provider
        class BrokenRead(httpx.AsyncByteStream):
            async def __aiter__(self):
                raise httpx.ReadTimeout("private-test-secret")
                yield b""
        for phase in ("connection", "response_read", "client_cleanup"):
            class CleanupClient(httpx.AsyncClient):
                async def __aexit__(self, *args):
                    await super().__aexit__(*args)
                    if phase == "client_cleanup":
                        raise httpx.CloseError("private-test-secret")
            def respond(request):
                if phase == "connection":
                    raise httpx.ConnectTimeout("private-test-secret")
                return httpx.Response(200, stream=BrokenRead()) if phase == "response_read" else httpx.Response(200, content=b"ok")
            with self.subTest(phase=phase), patch.object(provider.httpx, "AsyncClient", partial(
                    CleanupClient, transport=httpx.MockTransport(respond))), \
                    patch.object(provider, "monotonic", side_effect=[10.0, 10.125]), \
                    self.assertRaises(provider.OpenRouterUnavailable) as raised:
                await provider.http("POST", "chat/completions", 60, MAX_JSON_BYTES, "{}", "test-secret")
            self.assertEqual(raised.exception.phase, phase)
            self.assertEqual(raised.exception.elapsed_ms, 125)
            self.assertEqual(raised.exception.status_code, None if phase == "connection" else 200)
            self.assertNotIn("private", str(raised.exception))

    async def test_total_deadline_after_200_headers_reports_response_read(self):
        from backend import openrouter_client as provider
        timeout = asyncio.timeout
        closed = []
        class SlowRead(httpx.AsyncByteStream):
            async def __aiter__(self):
                await asyncio.sleep(10)
                yield b"private-test-secret"
            async def aclose(self):
                closed.append(True)
        with patch.object(provider.httpx, "AsyncClient", partial(httpx.AsyncClient,
                transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=SlowRead())))), \
                patch.object(provider.asyncio, "timeout", side_effect=lambda _: timeout(0.01)), \
                self.assertRaises(provider.OpenRouterUnavailable) as raised:
            await provider.http("POST", "chat/completions", 180, MAX_JSON_BYTES, "{}", "test-secret")
        self.assertEqual((raised.exception.status_code, raised.exception.exception_type, raised.exception.phase),
                         (200, "TimeoutError", "response_read"))
        self.assertGreaterEqual(raised.exception.elapsed_ms, 0)
        self.assertTrue(closed)

    async def test_zero_image_freezes_exact_request_and_returns_typed_plan_in_one_call(self):
        self.assertIsNotNone(importlib.util.find_spec("backend.openrouter_wardrobe"),
                             "The concrete frozen Wardrobe adapter is absent")
        from backend import openrouter_wardrobe as adapter
        from backend.wardrobe import VisualAnchorPlanV2, WardrobeResultV2

        self.assertIsNotNone(importlib.util.find_spec("backend.openrouter_client"), "Shared provider adapter is absent")
        from backend import openrouter_client as provider
        supplied = supplied_input()
        with self.transport(), patch.object(provider, "structured_request", wraps=provider.structured_request) as builder, \
                patch.object(provider, "model_metadata", wraps=provider.model_metadata) as metadata, \
                patch.object(provider, "parse_completion", wraps=provider.parse_completion) as parser:
            frozen = await adapter.prepare_wardrobe_request(supplied, {})
            config = adapter.read_wardrobe_config(frozen)
            result = await adapter.complete_wardrobe(config)
        self.assertIsInstance(result, VisualAnchorPlanV2)
        self.assertEqual(result.schema_version, "2")
        self.assertEqual(result.model_dump(mode="json")["batch_prompt"], draft_data()["batch_prompt"])
        self.assertEqual(config.adapter_version, "2")
        self.assertEqual(config.result_schema, WardrobeResultV2.model_json_schema())
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
            adapter.wardrobe_model_input(supplied), ensure_ascii=False, sort_keys=True, separators=(",", ":"))}])
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
        self.assertEqual(json.loads(content[0]["text"]), adapter.wardrobe_model_input(supplied))
        self.assertEqual(len(content), 1 + 2 * len(bodies))
        for index, image in enumerate(supplied["image_evidence"]):
            label, picture = content[1 + 2 * index:3 + 2 * index]
            self.assertEqual(label, {"type": "text", "text": encoded({key: image[key] for key in ("alias", "role", "subject_ids")})})
            self.assertEqual(picture, {"type": "image_url", "image_url": {"url":
                f'data:{image["ref"]["mime_type"]};base64,' + base64.b64encode(bodies[image["alias"]]).decode("ascii")}})
        self.assertEqual((supplied, bodies), before)
        self.assertEqual(result.batch_prompt[0].references, [])  # Evidence is not automatic render conditioning.
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
        for body in (frozen + " ", frozen.replace('"adapter_version":"2"', '"adapter_version":"2","adapter_version":"2"')):
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
        wrong_subject["batch_prompt"][0]["subject_ids"] = [private]
        wrong_parent = draft_data()
        wrong_parent["batch_prompt"][2]["references"][0]["source"]["unit_key"] = private
        invalid_ref = draft_data()
        invalid_ref["batch_prompt"][2]["references"][0]["source"] = {"kind": "supplied_image", "alias": private}
        wrong_mode = draft_data()
        wrong_mode["batch_prompt"][2]["workflow"] = "txt2img"
        v1_draft = {"direction": {}, "units": [
            {"unit_key": "hero_face", "subject_ids": ["hero"], "role": "portrait",
             "purpose": "Identity", "framing": "Close-up", "drawable_content": "Traveler",
             "image_prompt": "Watercolor traveler in a red coat.", "preserve": [], "ignore": [], "references": []}]}
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
                          for draft in (wrong_subject, wrong_parent, invalid_ref, wrong_mode, v1_draft)]):
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
            if error is adapter.WardrobeOwnerUnavailable:
                self.assertEqual((raised.exception.status_code, raised.exception.exception_type), (status, None))
        for error in (httpx.ReadTimeout, httpx.ConnectError):
            self.requests.clear()
            def unavailable(request):
                raise error("private-test-secret", request=request)
            with self.transport(unavailable), self.assertRaises(adapter.WardrobeOwnerUnavailable) as raised:
                await adapter.complete_wardrobe(config)
            self.assertNotIn("private", str(raised.exception))
            self.assertEqual([r.method for r in self.requests], ["POST"])
            self.assertEqual((raised.exception.status_code, raised.exception.exception_type), (None, error.__name__))
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
            self.assertEqual(seconds, 180)
            return original_timeout(0.01)
        with patch("backend.openrouter_client.httpx.AsyncClient",
                   partial(httpx.AsyncClient, transport=httpx.MockTransport(slow))), \
                patch("backend.openrouter_client.asyncio.timeout", side_effect=short_timeout), \
                self.assertRaises(adapter.WardrobeOwnerUnavailable) as raised:
            await adapter.complete_wardrobe(config)
        self.assertEqual((raised.exception.status_code, raised.exception.exception_type), (None, "TimeoutError"))
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
        from backend.wardrobe import WardrobeInputV2
        supplied = WardrobeInputV2.model_validate(supplied_input())
        supplied.story.shots[0].subject_ids.append("undeclared")
        with self.transport(), self.assertRaises(ValueError):
            await adapter.prepare_wardrobe_request(supplied, {})
        supplied, bodies = visual_input(("PNG",))
        alias = next(iter(bodies))
        output = BytesIO()
        # A normal original exceeds the old text-only ceiling, not Character image limits.
        import random
        Image.frombytes("RGB", (600, 600), random.Random(1).randbytes(600 * 600 * 3)).save(output, format="PNG")
        raw = output.getvalue()
        supplied["image_evidence"][0]["ref"].update(
            width=600, height=600, byte_length=len(raw), digest=sha256_digest(raw))
        with self.transport():
            frozen = await adapter.prepare_wardrobe_request(supplied, {alias: raw})
            config = adapter.read_wardrobe_config(frozen)
            await adapter.complete_wardrobe(config)
        self.assertGreater(len(frozen.encode()), MAX_JSON_BYTES)
        self.assertEqual([r.method for r in self.requests], ["GET", "POST"])
        self.assertEqual(self.requests[-1].content, config.base_request.encode())

    async def test_input_size_diagnostic_counts_combined_evidence_and_utf8_exactly(self):
        from backend import openrouter_wardrobe as adapter
        from backend.wardrobe import WardrobeInputV2

        supplied, bodies = visual_input(("PNG", "PNG"))
        self.assertIsNone(adapter.wardrobe_input_size_diagnostic(WardrobeInputV2.model_validate(supplied)))
        raw = large_png((2100, 1800))
        self.assertLess(len(raw), 10 * MAX_JSON_BYTES)
        self.assertLess(4 * ((len(raw) + 2) // 3), 16 * MAX_JSON_BYTES)
        for image in supplied["image_evidence"]:
            image["ref"].update(width=2100, height=1800, byte_length=len(raw), digest=sha256_digest(raw))
            bodies[image["alias"]] = raw
        expected: list[dict] = [{"type": "text", "text": encoded(adapter.wardrobe_model_input(supplied))}]
        for image in supplied["image_evidence"]:
            expected.extend([{"type": "text", "text": encoded({key: image[key] for key in ("alias", "role", "subject_ids")})},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(raw).decode()}}])
        with self.transport(), patch.object(adapter, "_image_bytes", side_effect=AssertionError("Over-budget images decoded")), \
                patch.object(adapter.base64, "b64encode", side_effect=AssertionError("Over-budget base64 allocated")), \
                self.assertRaises(adapter.WardrobeInputSizeLimit) as rejected:
            await adapter.prepare_wardrobe_request(supplied, bodies)
        self.assertEqual(rejected.exception.diagnostic.serialized_evidence_bytes, len(encoded(expected).encode()))
        self.assertEqual(rejected.exception.diagnostic.limit_bytes, 16 * MAX_JSON_BYTES)
        self.assertEqual(self.requests, [])

    async def test_story_and_artifact_default_limits_remain_one_mib(self):
        from backend import openrouter_client as provider
        from backend.domain import BriefV1, artifact_digest, parse_json_model
        from tests.test_domain import brief_data
        supplied = brief_data()
        supplied["must_keep"] = ["x" * 5000] * 256
        body = BriefV1.model_validate(supplied)
        with self.assertRaisesRegex(ValueError, "large"):
            canonical_json(body)
        with self.assertRaisesRegex(ValueError, "large"):
            artifact_digest(body)
        with self.assertRaisesRegex(ValueError, "large"):
            parse_json_model(encoded(supplied).encode(), BriefV1)
        with self.assertRaisesRegex(ValueError, "limit"):
            provider.structured_request(MODEL, "prompt", "x" * (MAX_JSON_BYTES + 1), {}, "story_result", 8192, "low")
        with self.transport(), self.assertRaisesRegex(ValueError, "limit"):
            await provider.http("POST", "chat/completions", 60, MAX_JSON_BYTES, "x" * (MAX_JSON_BYTES + 1), "test-secret")
        self.assertEqual(self.requests, [])

    async def test_single_character_max_original_fits_scoped_media_envelopes(self):
        from backend import openrouter_wardrobe as adapter
        from backend.characters import MAX_IMAGE_BYTES
        supplied, bodies = visual_input(("PNG",))
        alias = next(iter(bodies))
        # PNG permits trailing bytes: preserve a valid original at the exact byte ceiling.
        original = bodies[alias] + b"\0" * (MAX_IMAGE_BYTES - len(bodies[alias]))
        bodies[alias] = original
        supplied["image_evidence"][0]["ref"].update(byte_length=len(original), digest=sha256_digest(original))
        with self.transport():
            frozen = await adapter.prepare_wardrobe_request(supplied, bodies)
        config = adapter.read_wardrobe_config(frozen)
        self.assertGreater(len(config.base_request.encode()), 13 * MAX_JSON_BYTES)
        self.assertLess(len(config.base_request.encode()), adapter.MAX_WARDROBE_REQUEST_BYTES)
        self.assertLess(len(frozen.encode()), adapter.MAX_WARDROBE_CONFIG_BYTES)
        picture = json.loads(config.base_request)["messages"][1]["content"][2]["image_url"]["url"]
        self.assertEqual(base64.b64decode(picture.split(",", 1)[1]), original)
        self.assertEqual([r.method for r in self.requests], ["GET"])

    async def test_scoped_http_config_and_repair_limits_fail_closed(self):
        from types import SimpleNamespace
        from backend import openrouter_wardrobe as adapter
        with self.transport(), self.assertRaisesRegex(ValueError, "limit"):
            await adapter._http("POST", "chat/completions", 60, MAX_JSON_BYTES,
                                "x" * (adapter.MAX_WARDROBE_REQUEST_BYTES + 1), "test-secret")
        with patch("backend.domain._check_depth", side_effect=AssertionError("Oversized config parsed")), \
                self.assertRaisesRegex(ValueError, "frozen"):
            adapter.read_wardrobe_config(" " * (adapter.MAX_WARDROBE_CONFIG_BYTES + 1))
        base = encoded({"messages": [{"role": "user", "content": "x" * (adapter.MAX_WARDROBE_REQUEST_BYTES - 1024)}]})
        with patch.object(adapter, "read_wardrobe_config", return_value=SimpleNamespace(base_request=base)), \
                self.assertRaisesRegex(ValueError, "repair.*limit"):
            adapter.prepare_wardrobe_repair("unused", "x" * 4096)
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
