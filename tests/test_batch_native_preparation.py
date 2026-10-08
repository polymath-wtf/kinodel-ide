"""Private, GET-only installed context acquisition for frozen batch preparation."""

from copy import deepcopy
import json
import os
import ssl
import unittest
from unittest.mock import patch

import httpx

from backend import batch_generation, comfyui, comfyui_workflows as registry
from backend.config import resolve_comfyui_connection
from tests import test_batch_generation as batch_fixtures, test_comfyui as native_fixtures
from tests.test_comfyui_workflows import TXT, QWEN


class NativePreparationTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = native_fixtures.PreflightTests.asyncSetUp
    handler = native_fixtures.PreflightTests.handler

    def arguments(self, workflow=TXT, connection="local", **changes):
        arguments = {"connection": connection, "workflow": workflow,
                     "expected_endpoint_digest": "sha256:" + resolve_comfyui_connection(connection).endpoint_digest,
                     "expected_registry_digest": "sha256:" + registry.canonical_digest(registry.workflow_snapshot(workflow)),
                     "transport": httpx.MockTransport(self.handler)}
        arguments.update(changes)
        return arguments

    async def acquire(self, workflow=TXT, **changes):
        self.assertTrue(callable(getattr(comfyui, "acquire_preparation_context", None)),
                        "Private installed-context acquisition is not implemented")
        return await comfyui.acquire_preparation_context(**self.arguments(workflow, **changes))

    async def test_native_context_prepares_face_and_two_reference_sheet_without_posts(self):
        fixture = batch_fixtures.BatchGenerationTests()
        fixture.setUp()
        selected = resolve_comfyui_connection("local")
        batch = fixture.freeze(connection={"connection": "local", "endpoint_digest": "sha256:" + selected.endpoint_digest})
        for workflow, key, reference_count in ((TXT, "hero_face", 0), (QWEN, "hero_sheet", 2)):
            with self.subTest(workflow=workflow):
                context = await self.acquire(workflow)
                self.assertEqual(context.workflow_id, workflow)
                self.assertEqual(context.registry_digest, self.arguments(workflow)["expected_registry_digest"])
                self.assertEqual((context.connection, context.endpoint_digest), ("local", batch.connection.endpoint_digest))
                self.assertEqual(registry.load_candidate(workflow, context.template),
                                 json.loads(fixture.templates[workflow]))
                self.assertEqual(set(context.schemas), set(registry.get_workflow(workflow).required_nodes))
                prepared = batch_generation.prepare_batch_unit(batch, key,
                    parent_bindings=fixture.parents(batch, key), template=context.template,
                    schemas=context.schemas, model_inventory=context.model_inventory, seed=42)
                pin = registry.replay_prepared(prepared.image_pin_json)
                self.assertEqual(len(pin["references"]), reference_count)
                self.assertEqual(pin["settings"]["seed"], 42)
                self.assertFalse(pin["reference_bytes_verified"])
                if reference_count:
                    self.assertEqual([ref["role"] for ref in pin["references"]], ["portrait", "background"])
                    self.assertIn("470", pin["graph"])
                    self.assertIn("496", pin["graph"])
                    self.assertNotIn("498", pin["graph"])
                self.assertNotIn("schemas", repr(context))
                self.assertNotIn("template", repr(context))
        self.assertTrue(self.calls)
        self.assertTrue(all(call.method == "GET" for call in self.calls))
        self.assertFalse(any("prompt" in call.url.path for call in self.calls))

    async def test_missing_mismatched_or_implicit_pins_block_before_http(self):
        for change in ({"expected_endpoint_digest": None}, {"expected_endpoint_digest": ""},
                       {"expected_endpoint_digest": "sha256:" + "1" * 64},
                       {"expected_registry_digest": None}, {"expected_registry_digest": "sha256:" + "2" * 64}):
            with self.subTest(change=change):
                try:
                    await self.acquire(**change)
                except Exception as error:
                    self.assertIsInstance(error, comfyui.PreparationContextError)
                else:
                    self.fail("Missing/stale pin was accepted")
                self.assertEqual(self.calls, [])
        args = self.arguments()
        args["connection"] = None
        with self.assertRaises(comfyui.PreparationContextError):
            await comfyui.acquire_preparation_context(**args)
        self.assertEqual(self.calls, [])

    async def test_unsupported_or_stale_registry_mapping_and_template_block_before_http(self):
        for workflow in ("qwen21-img2img", "minimax-h3-img2vid"):
            with self.subTest(workflow=workflow), self.assertRaises(comfyui.PreparationContextError):
                await self.acquire(workflow)
            self.assertEqual(self.calls, [])
        args = self.arguments()
        snapshot = registry.workflow_snapshot(TXT)
        snapshot["mapping"]["parameters"][0]["input_name"] = "not_the_frozen_mapping"
        with patch.object(registry, "workflow_snapshot", return_value=snapshot), \
                self.assertRaises(comfyui.PreparationContextError):
            await comfyui.acquire_preparation_context(**args)
        self.assertEqual(self.calls, [])
        template = (comfyui.WORKFLOW_ROOT / comfyui.DEFAULT_WORKFLOW).read_bytes()
        with patch("pathlib.Path.read_bytes", return_value=template + b" "), \
                self.assertRaises(comfyui.PreparationContextError) as rejected:
            await self.acquire()
        self.assertEqual(rejected.exception.code, "template_pin_mismatch")
        self.assertEqual(self.calls, [])

    async def test_missing_nodes_models_and_incompatible_schema_never_return_partial_context(self):
        original = deepcopy(self.schemas)
        mutations = [("missing_node", lambda s: s.pop("easy int")),
                     ("missing_model", lambda s: s["VAELoader"]["input"]["required"].update(vae_name=[[]])),
                     ("socket_type_mismatch", lambda s: s["VAEDecode"].update(output=["MASK"])),
                     ("missing_required_input", lambda s: s["CLIPTextEncode"]["input"]["required"].update(unmapped=["STRING"])),
                     ("unexpected_shape", lambda s: s["KSampler"].update(input=[]))]
        for expected, mutate in mutations:
            self.schemas = deepcopy(original)
            mutate(self.schemas)
            with self.subTest(expected=expected), self.assertRaises(comfyui.PreparationContextError) as rejected:
                await self.acquire()
            self.assertEqual(rejected.exception.code, expected)
            self.assertNotIn("schemas", str(rejected.exception))

    async def test_inventory_fallback_is_returned_exact_and_cannot_override_installed_combo(self):
        self.schemas["VAELoader"]["input"]["required"]["vae_name"] = ["STRING", {}]
        self.responses["/models/vae"] = httpx.Response(200, json=["qwen_image_vae.safetensors"])
        context = await self.acquire()
        self.assertEqual(context.model_inventory, {"vae": ["qwen_image_vae.safetensors"]})
        self.responses["/models/vae"] = httpx.Response(200, json=[])
        with self.assertRaises(comfyui.PreparationContextError) as rejected:
            await self.acquire()
        self.assertEqual(rejected.exception.code, "missing_model")

    async def test_unknown_workflow_config_and_unexpected_pipeline_failure_are_safe(self):
        args = self.arguments()
        args["workflow"] = "not-a-registered-workflow"
        with self.assertRaises(comfyui.PreparationContextError) as rejected:
            await comfyui.acquire_preparation_context(**args)
        self.assertEqual(rejected.exception.code, "unknown_workflow")
        self.assertEqual(self.calls, [])
        args = self.arguments()
        with patch.dict(os.environ, {"COMFYUI_LOCAL_ENDPOINT": "http://user:private-token@private.test"}), \
                self.assertRaises(comfyui.PreparationContextError) as rejected:
            await comfyui.acquire_preparation_context(**args)
        self.assertEqual(rejected.exception.code, "invalid_endpoint")
        self.assertNotIn("private-token", str(rejected.exception))
        self.assertEqual(self.calls, [])
        with patch.object(comfyui, "_dependencies", side_effect=KeyError("private-token")), \
                self.assertRaises(comfyui.PreparationContextError) as rejected:
            await self.acquire()
        self.assertEqual(rejected.exception.code, "invalid_preparation_context")
        self.assertNotIn("private-token", str(rejected.exception))

    async def test_explicit_server_connection_verified_transport_and_private_context(self):
        os.environ.update({"COMFYUI_SERVER_ENDPOINT": "https://private.test/native", "COMFYUI_LOCAL_ENDPOINT": "bad-unused",
                           "COMFYUI_AUTH_TOKEN": "private-token"})
        client = httpx.AsyncClient
        with patch("backend.comfyui.httpx.AsyncClient", wraps=client) as opened:
            context = await self.acquire(connection="server")
        self.assertEqual(context.connection, "server")
        self.assertFalse(opened.call_args.kwargs["trust_env"])
        self.assertFalse(opened.call_args.kwargs["follow_redirects"])
        self.assertIs(opened.call_args.kwargs["verify"], True)
        self.assertEqual(opened.call_args.kwargs["timeout"].connect, 5)
        self.assertTrue(all(request.url.host == "private.test" for request in self.calls))
        self.assertFalse(hasattr(context, "auth_token"))
        self.assertFalse(hasattr(context, "endpoint"))
        self.assertNotIn("private-token", repr(context))
        self.calls.clear()
        with self.assertRaises(comfyui.PreparationContextError):
            await self.acquire(connection="server", expected_endpoint_digest="sha256:" + "0" * 64)
        self.assertEqual(self.calls, [])

    async def test_transport_tls_timeout_redirect_and_auth_failures_are_typed_and_safe(self):
        errors = [(httpx.ConnectError("private-token https://private.test"), "unavailable"),
                  (httpx.ReadTimeout("private-token"), "timeout")]
        tls = httpx.ConnectError("private-token https://private.test")
        tls.__cause__ = ssl.SSLCertVerificationError("private-token")
        errors.append((tls, "tls_error"))
        for error, expected in errors:
            def fail(request):
                self.calls.append(request)
                raise error
            args = self.arguments(transport=httpx.MockTransport(fail))
            self.calls.clear()
            with self.subTest(expected=expected), self.assertRaises(comfyui.PreparationContextError) as rejected:
                await comfyui.acquire_preparation_context(**args)
            self.assertEqual(rejected.exception.code, expected)
            self.assertEqual(len(self.calls), 1)
            self.assertNotIn("private-token", str(rejected.exception))
            self.assertNotIn("private.test", str(rejected.exception))
        for status, expected in ((302, "redirect_rejected"), (401, "auth_failed"), (503, "http_error")):
            self.responses["/system_stats"] = httpx.Response(status, text="private-token")
            self.calls.clear()
            with self.subTest(status=status), self.assertRaises(comfyui.PreparationContextError) as rejected:
                await self.acquire()
            self.assertEqual(rejected.exception.code, expected)
            self.assertEqual(len(self.calls), 1)


if __name__ == "__main__":
    unittest.main()
