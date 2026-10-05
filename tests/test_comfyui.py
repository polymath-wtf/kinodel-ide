import asyncio
from dataclasses import FrozenInstanceError
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import ssl
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote

import httpx

from backend import comfyui, config
from backend.launch import load_env_file


class ConnectionTests(unittest.TestCase):
    def test_default_and_explicit_selection_are_frozen_and_private(self):
        self.assertTrue(callable(getattr(config, "resolve_comfyui_connection", None)))
        with patch.dict(os.environ, {"COMFYUI_SERVER_ENDPOINT": "bad-secret-url"}, clear=True):
            local = config.resolve_comfyui_connection()
            self.assertEqual(local.connection, "local")
            self.assertEqual(local.endpoint, "http://127.0.0.1:8188/")
            self.assertIs(local.verify, True)
            self.assertEqual(local.endpoint_digest, hashlib.sha256(local.endpoint.encode()).hexdigest())
            with self.assertRaises(FrozenInstanceError):
                setattr(local, "connection", "server")
        with patch.dict(os.environ, {
            "COMFYUI_LOCAL_ENDPOINT": "invalid-unused",
            "COMFYUI_SERVER_ENDPOINT": "https://private.test:8443/native/",
            "COMFYUI_CONNECTION": "server", "COMFYUI_AUTH_TOKEN": "test-secret-token",
        }, clear=True):
            server = config.resolve_comfyui_connection()
            self.assertEqual(server.connection, "server")
            self.assertEqual(server.auth_token, "test-secret-token")
            self.assertNotIn("private.test", repr(server))
            self.assertNotIn("test-secret-token", repr(server))
            os.environ["COMFYUI_LOCAL_ENDPOINT"] = "http://localhost:8188/prefix"
            self.assertEqual(config.resolve_comfyui_connection("local").endpoint, "http://localhost:8188/prefix/")

    def test_invalid_selected_configuration_has_no_private_error_text(self):
        invalid_urls = (
            "", "ftp://private.test", "http:///private.test", "http://user:secret@private.test",
            "http://private.test?secret", "http://private.test#secret", "http://private.test?",
            "http://private.test:0", "http://private.test:99999", "http://private.test:",
            "http://private.test\\secret", "http://private.test/\nsecret", "http://private.test/ secret",
            "http://private.test/a/../secret", "http://private.test/%0asecret", "http://private.test/%5csecret",
            "http://private.test/\x80secret", "http://private.test/%C2%80secret",
            "http://private.test/" + "a" * 9000, "http://[bad-ipv6]/", "http://bad%20host/",
        )
        for url in invalid_urls:
            with self.subTest(url=url[:80]), patch.dict(os.environ, {"COMFYUI_LOCAL_ENDPOINT": url}, clear=True):
                with self.assertRaises(ValueError) as error:
                    config.resolve_comfyui_connection()
                self.assertNotIn("private.test", str(error.exception))
                self.assertNotIn("secret", str(error.exception))
        for env in ({"COMFYUI_CONNECTION": "automatic"}, {"COMFYUI_CONNECTION": "server"},
                    {"COMFYUI_AUTH_TOKEN": "bad\nsecret"}, {"COMFYUI_CA_FILE": "relative-secret.pem"}):
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ValueError):
                    config.resolve_comfyui_connection()
        with patch.dict(os.environ, {"COMFYUI_LOCAL_ENDPOINT": "http://[::1]:8188/comfy"}, clear=True):
            self.assertEqual(config.resolve_comfyui_connection().endpoint, "http://[::1]:8188/comfy/")

    def test_private_ca_uses_verified_ssl_context(self):
        ca = str(Path(tempfile.gettempdir()) / "private-ca.pem")
        context = ssl.create_default_context()
        with patch.dict(os.environ, {"COMFYUI_CA_FILE": ca}, clear=True), \
                patch("backend.config.ssl.create_default_context", return_value=context) as create:
            connection = config.resolve_comfyui_connection()
            create.assert_called_once_with(cafile=ca)
            self.assertIs(connection.verify, context)
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)
            self.assertNotIn(ca, repr(connection))
        with patch.dict(os.environ, {"COMFYUI_CA_FILE": ca}, clear=True), \
                patch("backend.config.ssl.create_default_context", side_effect=OSError(ca)):
            with self.assertRaises(ValueError) as error:
                config.resolve_comfyui_connection()
            self.assertNotIn(ca, str(error.exception))

    def test_explicit_env_allowlist_and_exported_precedence(self):
        keys = ("COMFYUI_LOCAL_ENDPOINT", "COMFYUI_SERVER_ENDPOINT", "COMFYUI_CONNECTION",
                "COMFYUI_AUTH_TOKEN", "COMFYUI_CA_FILE")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "explicit.env"
            path.write_text("\n".join(f'{key}="file-value-{key}"' for key in keys)
                            + "\nUNRELATED=ignored\nHTTP_PROXY=ignored\n", encoding="utf-8")
            with patch.dict(os.environ, {keys[0]: "exported-value"}, clear=True):
                load_env_file(path)
                self.assertEqual(os.environ[keys[0]], "exported-value")
                for key in keys[1:]:
                    self.assertEqual(os.environ[key], f"file-value-{key}")
                self.assertNotIn("UNRELATED", os.environ)
                self.assertNotIn("HTTP_PROXY", os.environ)

    def test_empty_comfyui_assignments_are_equivalent_and_preserve_exported_values(self):
        keys = ("COMFYUI_LOCAL_ENDPOINT", "COMFYUI_SERVER_ENDPOINT", "COMFYUI_CONNECTION",
                "COMFYUI_AUTH_TOKEN", "COMFYUI_CA_FILE")
        exported = {"COMFYUI_LOCAL_ENDPOINT": "http://127.0.0.1:8188", "COMFYUI_CONNECTION": "local"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "explicit.env"
            for empty in ("", "''", '""'):
                path.write_text("\n".join(f"{key}={empty}" for key in keys), encoding="utf-8")
                with self.subTest(empty=empty), patch.dict(os.environ, exported, clear=True):
                    load_env_file(path)
                    self.assertEqual(dict(os.environ), {key: exported.get(key, "") for key in keys})
                    connection = config.resolve_comfyui_connection()
                    self.assertEqual(connection.connection, "local")
                    self.assertIsNone(connection.auth_token)
                    self.assertIs(connection.verify, True)
                with self.subTest(empty=empty, selected_empty=True), patch.dict(os.environ, {}, clear=True):
                    load_env_file(path)
                    self.assertEqual(dict(os.environ), dict.fromkeys(keys, ""))
                    with self.assertRaises(ValueError):
                        config.resolve_comfyui_connection()

    def test_empty_comfyui_values_do_not_relax_assignment_syntax_or_model_keys(self):
        keys = ("COMFYUI_LOCAL_ENDPOINT", "COMFYUI_SERVER_ENDPOINT", "COMFYUI_CONNECTION",
                "COMFYUI_AUTH_TOKEN", "COMFYUI_CA_FILE", "OPENROUTER_API_KEY", "LLM_MODEL")
        invalid = [line for key in keys for line in (
            key, f"{key}=\n{key}=duplicate", f"{key}='broken-secret", f'{key}="broken-secret',
        )]
        invalid.extend(f"{key}={empty}" for key in ("OPENROUTER_API_KEY", "LLM_MODEL")
                       for empty in ("", " ", "''", '""'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "explicit.env"
            for line in invalid:
                path.write_text(line, encoding="utf-8")
                with self.subTest(line=line), patch.dict(os.environ, {"LLM_MODEL": "exported"}, clear=True):
                    with self.assertRaises(ValueError) as error:
                        load_env_file(path)
                    self.assertNotIn("broken-secret", str(error.exception))
                    self.assertEqual(dict(os.environ), {"LLM_MODEL": "exported"})

    def test_launcher_environment_error_is_generic_and_sanitized(self):
        from backend.launch import main

        with patch("backend.launch.load_env_file", side_effect=OSError("private-secret-path")), \
                patch("sys.argv", ["backend.launch", "--env-file", "explicit.env"]), \
                patch("sys.stderr", new_callable=io.StringIO) as error_output:
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 2)
        self.assertIn("Cannot load the explicit environment file", error_output.getvalue())
        self.assertNotIn("private-secret-path", error_output.getvalue())


class PreflightTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_comfyui_workflows import installed_schemas

        self.comfy = comfyui
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.graph = json.loads((self.comfy.WORKFLOW_ROOT / self.comfy.DEFAULT_WORKFLOW).read_bytes())
        self.schemas = {cls: {**schema, "python_module": "nodes"}
                        for cls, schema in installed_schemas().items()}
        self.schemas["easy int"]["python_module"] = "custom_nodes.ComfyUI-Easy-Use"
        self.schemas["easy int"]["version"] = "1.2.3"
        self.schemas["Power Lora Loader (rgthree)"]["python_module"] = "custom_nodes.rgthree-comfy"
        self.stats = {
            "system": {"comfyui_version": "0.3.50", "python_version": "3.13.7 (main, date)",
                       "pytorch_version": "2.8.0+cu128", "required_frontend_version": "9.9.9",
                       "installed_templates_version": "0.7.4",
                       "comfy_package_versions": [{"name": "comfyui-frontend-package", "installed": "1.27.0", "required": "9.9.9"},
                                                  {"name": "comfyui-embedded-docs", "installed": None, "required": "4.5.6"},
                                                  {"name": "comfy-kitchen", "installed": "0.2.3", "required": "0.2.4"}],
                       "argv": ["--private-path=C:/private/secret", "--auth=test-secret-token"]},
            "devices": [{"name": "cuda:0 NVIDIA RTX Test : cudaMallocAsync", "type": "cuda", "vram_total": 24000000000,
                         "vram_free": 12000000000}],
        }
        self.calls = []
        self.responses = {}

    def handler(self, request):
        self.calls.append(request)
        self.assertEqual(request.method, "GET")
        path = unquote(request.url.path).removeprefix("/native")
        if path in self.responses:
            return self.responses[path]
        if path == "/system_stats":
            return httpx.Response(200, json=self.stats)
        if path.startswith("/object_info/"):
            cls = path.removeprefix("/object_info/")
            return httpx.Response(200, json={cls: self.schemas[cls]} if cls in self.schemas else {})
        if path == "/models":
            return httpx.Response(200, json=["diffusion_models", "text_encoders", "vae", "loras"])
        if path.startswith("/models/"):
            return httpx.Response(200, json=[])
        self.fail(f"Unexpected preflight path: {path}")

    async def run_preflight(self, **kwargs):
        return await self.comfy.preflight(transport=httpx.MockTransport(self.handler), **kwargs)

    async def test_read_only_report_exact_models_versions_and_digests(self):
        report = await self.run_preflight()
        self.assertTrue(report.reachable)
        self.assertTrue(report.dependencies_ready)
        self.assertEqual(report.workflow, self.comfy.DEFAULT_WORKFLOW)
        self.assertEqual(report.workflow_sha256, hashlib.sha256(
            (self.comfy.WORKFLOW_ROOT / self.comfy.DEFAULT_WORKFLOW).read_bytes()).hexdigest())
        self.assertEqual(report.versions.python, "3.13.7")
        self.assertEqual(report.versions.pytorch, "2.8.0+cu128")
        self.assertEqual(report.versions.comfyui, "0.3.50")
        self.assertEqual(report.versions.packages["comfyui-frontend-package"], "1.27.0")
        self.assertEqual(report.versions.packages["comfyui-workflow-templates"], "0.7.4")
        self.assertEqual(report.versions.packages["comfy-kitchen"], "0.2.3")
        self.assertIsNone(report.versions.packages["comfyui-embedded-docs"])
        self.assertNotIn("9.9.9", report.model_dump_json())
        self.assertNotIn("4.5.6", report.model_dump_json())
        self.assertEqual(report.devices[0].vram_total, 24000000000)
        self.assertEqual(report.devices[0].name, "cuda:0 NVIDIA RTX Test : cudaMallocAsync")
        self.assertEqual(report.devices[0].type, "cuda")
        self.assertEqual({model.filename for model in report.models}, {
            "krea2_turbo_int8_convrot.safetensors", "qwen3vl_4b_fp8_scaled.safetensors",
            "qwen_image_vae.safetensors",
        })
        self.assertTrue(all(model.available for model in report.models))
        rgthree = next(node for node in report.nodes if node.class_type == "Power Lora Loader (rgthree)")
        self.assertIsNone(rgthree.version)
        self.assertIn("nodes.Power Lora Loader (rgthree).version", report.unknowns)
        self.assertEqual(next(node for node in report.nodes if node.class_type == "easy int").version, "1.2.3")
        for node in report.nodes:
            digest = hashlib.sha256(json.dumps(self.schemas[node.class_type], sort_keys=True,
                                               separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
            self.assertEqual(node.schema_sha256, digest)
        output = report.model_dump_json()
        for private in ("argv", "private-path", "test-secret-token", "C:/private/secret", "127.0.0.1"):
            self.assertNotIn(private, output)

    async def test_registry_pin_and_schema_validation_are_reported_without_raw_graph(self):
        from backend.comfyui_workflows import get_workflow, workflow_snapshot, canonical_digest

        report = await self.run_preflight()
        spec = get_workflow(self.comfy.DEFAULT_WORKFLOW)
        self.assertEqual(report.workflow_id, spec.id)
        self.assertEqual(report.workflow_version, spec.version)
        self.assertEqual(report.registry_sha256, canonical_digest(workflow_snapshot(spec.id)))
        self.assertTrue(report.preparation_enabled)
        self.assertTrue(report.graph_ready)
        self.assertNotIn('"inputs"', report.model_dump_json())
        self.schemas["CLIPTextEncode"]["input"]["required"]["unmapped"] = ["STRING"]
        report = await self.run_preflight()
        self.assertTrue(report.dependencies_ready)
        self.assertFalse(report.graph_ready)
        self.assertIn("missing_required_input", {i.code for i in report.issues})
        del self.schemas["CLIPTextEncode"]["input"]["required"]["unmapped"]
        self.schemas["VAEDecode"]["output"] = ["MASK"]
        report = await self.run_preflight()
        self.assertFalse(report.graph_ready)
        self.assertIn("socket_type_mismatch", {i.code for i in report.issues})

    async def test_edited_pinned_template_blocks_before_network(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(self.comfy, "WORKFLOW_ROOT", Path(directory)):
            (Path(directory) / self.comfy.DEFAULT_WORKFLOW).write_bytes(
                json.dumps(self.graph).encode() + b" ")
            report = await self.run_preflight()
        self.assertFalse(report.dependencies_ready)
        self.assertIn("template_pin_mismatch", {i.code for i in report.issues})
        self.assertEqual(self.calls, [])

    async def test_qwen_registry_accepts_installed_autogrow_and_v3_model_combos(self):
        report = await self.run_preflight(workflow="qwen img2img api v1.1 3img.json")
        self.assertTrue(report.dependencies_ready)
        self.assertTrue(report.graph_ready)
        self.assertEqual(report.workflow_id, "qwen21-multi-img2img")
        declaration = self.schemas["UNETLoader"]["input"]["required"]["unet_name"]
        self.schemas["UNETLoader"]["input"]["required"]["unet_name"] = ["COMBO", {"options": declaration[0]}]
        self.calls.clear()
        report = await self.run_preflight(workflow="qwen img2img api v1.1 3img.json")
        self.assertTrue(report.graph_ready)
        self.assertFalse(any('/models' in request.url.path for request in self.calls))

    async def test_explicit_server_prefix_auth_escaped_class_and_verified_client_settings(self):
        os.environ.update({"COMFYUI_LOCAL_ENDPOINT": "bad-unused-url",
                           "COMFYUI_SERVER_ENDPOINT": "https://private.test:8443/native",
                           "COMFYUI_AUTH_TOKEN": "test-secret-token"})
        real_client = httpx.AsyncClient
        with patch("backend.comfyui.httpx.AsyncClient", wraps=real_client) as client:
            report = await self.run_preflight(connection="server")
        self.assertTrue(report.dependencies_ready)
        self.assertEqual(report.connection, "server")
        self.assertFalse(client.call_args.kwargs["trust_env"])
        self.assertFalse(client.call_args.kwargs["follow_redirects"])
        self.assertIs(client.call_args.kwargs["verify"], True)
        self.assertEqual(client.call_args.kwargs["timeout"].connect, 5)
        self.assertEqual(client.call_args.kwargs["timeout"].read, 15)
        self.assertTrue(all(request.url.host == "private.test" for request in self.calls))
        self.assertTrue(all(request.url.path.startswith("/native/") for request in self.calls))
        self.assertTrue(all(request.headers["authorization"] == "Bearer test-secret-token" for request in self.calls))
        self.assertTrue(any(b"Power%20Lora%20Loader%20%28rgthree%29" in request.url.raw_path for request in self.calls))
        self.assertNotIn("private.test", report.model_dump_json())
        self.assertNotIn("test-secret-token", report.model_dump_json())

    async def test_missing_class_and_exact_not_basename_model_matching(self):
        del self.schemas["easy int"]
        self.schemas["VAELoader"]["input"]["required"]["vae_name"][0] = ["folder/qwen_image_vae.safetensors"]
        report = await self.run_preflight()
        self.assertTrue(report.reachable)
        self.assertFalse(report.dependencies_ready)
        self.assertIn("missing_node", {issue.code for issue in report.issues})
        self.assertIn("missing_model", {issue.code for issue in report.issues})
        self.assertFalse(next(model for model in report.models if model.folder == "vae").available)

    async def test_model_inventory_when_combo_is_not_exposed(self):
        self.schemas["VAELoader"]["input"]["required"]["vae_name"] = ["STRING", {}]
        self.responses["/models/vae"] = httpx.Response(200, json=["qwen_image_vae.safetensors"])
        report = await self.run_preflight()
        self.assertTrue(report.dependencies_ready)
        self.assertEqual(next(model for model in report.models if model.folder == "vae").source, "inventory")
        self.assertIn("/models", [request.url.path for request in self.calls])
        self.assertIn("/models/vae", [request.url.path for request in self.calls])

    async def test_unknown_versions_are_advisory_not_invented(self):
        self.stats["system"] = {"argv": ["--private-path=secret"]}
        report = await self.run_preflight()
        self.assertTrue(report.dependencies_ready)
        self.assertIsNone(report.versions.comfyui)
        self.assertIsNone(report.versions.python)
        self.assertIsNone(report.versions.pytorch)
        self.assertIn("versions.comfyui", report.unknowns)
        self.assertIn("version_unknown", {issue.code for issue in report.issues})

    async def test_remote_diagnostic_strings_are_not_blindly_echoed(self):
        os.environ["COMFYUI_AUTH_TOKEN"] = "test-secret-token"
        self.stats["system"]["comfyui_version"] = "https://private.test/test-secret-token"
        self.stats["devices"][0]["name"] = "C:/private/test-secret-token"
        self.schemas["easy int"]["python_module"] = "C:/private/module.py"
        report = await self.run_preflight()
        for private in ("test-secret-token", "private.test", "C:/private"):
            self.assertNotIn(private, report.model_dump_json())

    async def test_bad_workflow_or_config_never_networks(self):
        for workflow in ("../secret.json", str(Path.cwd() / "secret.json"), "unknown.json", ""):
            with self.subTest(workflow=workflow):
                report = await self.run_preflight(workflow=workflow)
                self.assertFalse(report.dependencies_ready)
                self.assertEqual(report.issues[0].code, "invalid_workflow")
                self.assertIsNone(report.workflow)
        for env in ({"COMFYUI_CONNECTION": "bad"}, {"COMFYUI_CONNECTION": "server"},
                    {"COMFYUI_LOCAL_ENDPOINT": "http://user:secret@private.test"}):
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                report = await self.run_preflight()
                self.assertFalse(report.dependencies_ready)
                self.assertIn(report.issues[0].code, {"invalid_connection", "invalid_endpoint"})
        self.assertEqual(self.calls, [])

    async def test_trusted_workflow_list_and_malformed_graph_before_network(self):
        self.assertEqual(len(self.comfy.list_workflows()), 6)
        with tempfile.TemporaryDirectory() as directory, patch.object(self.comfy, "WORKFLOW_ROOT", Path(directory)):
            workflow = Path(directory) / self.comfy.DEFAULT_WORKFLOW
            workflow.write_text('{"nodes": [], "links": []}', encoding="utf-8")
            (Path(directory) / "undeclared.json").write_text("{}", encoding="utf-8")
            self.assertEqual(self.comfy.list_workflows(), [self.comfy.DEFAULT_WORKFLOW])
            report = await self.run_preflight()
            self.assertEqual(report.issues[0].code, "invalid_workflow_graph")
            workflow.write_text('{"1": {"class_type": "VAELoader", "inputs": []}}', encoding="utf-8")
            self.assertEqual((await self.run_preflight()).issues[0].code, "invalid_workflow_graph")
            workflow.write_text('{"unexpected_metadata": "do not ignore me"}', encoding="utf-8")
            self.assertEqual((await self.run_preflight()).issues[0].code, "invalid_workflow_graph")
        self.assertEqual(self.calls, [])

    async def test_symlink_workflow_and_root_are_not_trusted(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "target.json"
            target.write_text("{}", encoding="utf-8")
            root = base / "workflows"
            root.mkdir()
            try:
                (root / self.comfy.DEFAULT_WORKFLOW).symlink_to(target)
                (base / "linked-root").symlink_to(root, target_is_directory=True)
            except OSError:
                self.skipTest("Symlink permission unavailable on this platform")
            for folder in (root, base / "linked-root"):
                with patch.object(self.comfy, "WORKFLOW_ROOT", folder):
                    self.assertEqual(self.comfy.list_workflows(), [])
                    self.assertEqual((await self.run_preflight()).issues[0].code, "invalid_workflow")

    async def test_unavailable_or_linked_workflow_directory_is_sanitized_without_network(self):
        for target, effect in (("is_file", PermissionError("C:/private/secret")), ("is_symlink", True)):
            with self.subTest(target=target):
                with patch.object(Path, target) as probe:
                    if isinstance(effect, Exception):
                        probe.side_effect = effect
                    else:
                        probe.return_value = effect
                    self.assertEqual(self.comfy.list_workflows(), [])
                    report = await self.run_preflight()
                self.assertEqual(report.issues[0].code, "invalid_workflow")
                self.assertNotIn("C:/private/secret", report.model_dump_json())
        self.assertEqual(self.calls, [])

    async def test_enabled_nested_rgthree_lora_is_exact_dependency_not_header_or_fixture(self):
        workflow = "img2img krea2 v1.4_local.json"
        graph = json.loads((self.comfy.WORKFLOW_ROOT / workflow).read_bytes())
        for node in graph.values():
            self.schemas.setdefault(node["class_type"], {"input": {"required": {}}, "python_module": "nodes"})
        filename = graph["819"]["inputs"]["lora_1"]["lora"]
        self.responses["/models/loras"] = httpx.Response(200, json=[filename])
        report = await self.run_preflight(workflow=workflow)
        self.assertTrue(report.dependencies_ready)
        self.assertEqual(len(report.models), 4)
        self.assertTrue(next(model for model in report.models if model.folder == "loras").available)
        self.assertFalse(any(model.input_name == "image" for model in report.models))
        graph["819"]["inputs"]["lora_1"]["on"] = False
        with tempfile.TemporaryDirectory() as directory, patch.object(self.comfy, "WORKFLOW_ROOT", Path(directory)):
            (Path(directory) / workflow).write_text(json.dumps(graph), encoding="utf-8")
            report = await self.run_preflight(workflow=workflow)
            self.assertIn("template_pin_mismatch", {i.code for i in report.issues})
            self.assertFalse(report.dependencies_ready)

    async def test_special_loader_combo_does_not_prove_downloaded_model(self):
        workflow = "minimax img2vid api v1.json"
        graph = json.loads((self.comfy.WORKFLOW_ROOT / workflow).read_bytes())
        for node in graph.values():
            self.schemas.setdefault(node["class_type"], {"input": {"required": {}}, "python_module": "nodes"})
        self.schemas["RIFE VFI"]["input"]["required"]["ckpt_name"] = [["rife49.pth"], {}]
        report = await self.run_preflight(workflow=workflow)
        model = next(model for model in report.models if model.class_type == "RIFE VFI")
        self.assertIsNone(model.available)
        self.assertEqual(model.source, "unverified")
        self.assertFalse(report.dependencies_ready)
        self.assertIn("model_unverified", {issue.code for issue in report.issues})

    async def test_http_malformed_oversize_and_redirect_failures_are_sanitized(self):
        cases = [
            (httpx.Response(401, text="test-secret-token private-body"), "auth_failed"),
            (httpx.Response(403, text="private-body"), "auth_failed"),
            (httpx.Response(503, text="private-body"), "http_error"),
            (httpx.Response(302, headers={"location": "https://evil.test/test-secret-token"}), "redirect_rejected"),
            (httpx.Response(200, text="not-json private-body"), "malformed_json"),
            (httpx.Response(200, json=[]), "unexpected_shape"),
            (httpx.Response(200, json={"system": [], "devices": []}), "unexpected_shape"),
            (httpx.Response(200, content=b'{"system":{},"system":{},"devices":[]}'), "malformed_json"),
            (httpx.Response(200, headers={"content-encoding": "gzip"}, content=gzip.compress(b"{}")), "unexpected_shape"),
            (httpx.Response(200, headers={"Content-Length": "99999999"}, content=b"{}"), "response_too_large"),
        ]
        for response, code in cases:
            with self.subTest(code=code):
                self.calls.clear()
                self.responses["/system_stats"] = response
                report = await self.run_preflight()
                self.assertTrue(report.reachable)
                self.assertFalse(report.dependencies_ready)
                self.assertEqual(report.issues[0].code, code)
                self.assertEqual(len(self.calls), 1)
                for private in ("private-body", "test-secret-token", "evil.test"):
                    self.assertNotIn(private, report.model_dump_json())
        response = httpx.Response(200, content=b" " * (self.comfy.MAX_RESPONSE_BYTES + 1))
        del response.headers["content-length"]
        self.responses["/system_stats"] = response
        self.assertEqual((await self.run_preflight()).issues[0].code, "response_too_large")

    async def test_transport_errors_timeout_and_no_fallback(self):
        os.environ.update({"COMFYUI_CONNECTION": "server", "COMFYUI_SERVER_ENDPOINT": "https://private.test/native"})
        tls = httpx.ConnectError("private-body test-secret-token")
        tls.__cause__ = ssl.SSLCertVerificationError("private TLS details")
        for error, code in ((tls, "tls_error"), (httpx.ConnectError("private-body"), "unavailable"),
                            (httpx.ReadTimeout("private-body"), "timeout"),
                            (httpx.RemoteProtocolError("private-body"), "http_error")):
            calls = []

            def failing(request):
                calls.append(request)
                raise error

            with self.subTest(code=code):
                report = await self.comfy.preflight(transport=httpx.MockTransport(failing))
                self.assertFalse(report.reachable)
                self.assertEqual(report.issues[0].code, code)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0].url.host, "private.test")
                self.assertNotIn("private-body", report.model_dump_json())

    async def test_total_timeout_and_cancellation_close_transport(self):
        class SlowTransport(httpx.AsyncBaseTransport):
            closed = False

            def __init__(self):
                self.entered = asyncio.Event()

            async def handle_async_request(self, request):
                self.entered.set()
                await asyncio.sleep(10)
                return httpx.Response(200, json={})

            async def aclose(self):
                self.closed = True

        transport = SlowTransport()
        with patch.object(self.comfy, "TOTAL_TIMEOUT", 0.02):
            report = await self.comfy.preflight(transport=transport)
        self.assertEqual(report.issues[0].code, "timeout")
        self.assertTrue(transport.closed)
        transport = SlowTransport()
        task = asyncio.create_task(self.comfy.preflight(transport=transport))
        await transport.entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(transport.closed)

    async def test_bounded_request_stream_closes_on_timeout(self):
        class SlowStream(httpx.AsyncByteStream):
            closed = False

            async def __aiter__(self):
                yield b" "
                await asyncio.sleep(10)

            async def aclose(self):
                self.closed = True

        stream = SlowStream()
        self.responses["/system_stats"] = httpx.Response(200, stream=stream)
        with patch.object(self.comfy, "REQUEST_TIMEOUT", 0.02):
            report = await self.run_preflight()
        self.assertTrue(report.reachable)
        self.assertEqual(report.issues[0].code, "timeout")
        self.assertTrue(stream.closed)

    async def test_schema_and_model_inventory_shape_errors_do_not_become_readiness(self):
        for payload in ([], {"VAELoader": {"input": []}}, {"VAELoader": {"input": {"required": []}}}):
            with self.subTest(payload=payload):
                self.responses["/object_info/VAELoader"] = httpx.Response(200, json=payload)
                report = await self.run_preflight()
                self.assertFalse(report.dependencies_ready)
                self.assertIn("unexpected_shape", {issue.code for issue in report.issues})
        self.responses.clear()
        self.schemas["VAELoader"]["input"]["required"]["vae_name"] = ["STRING", {}]
        for path, payload in (("/models", {}), ("/models/vae", ["model", {"private-body": "secret"}])):
            with self.subTest(path=path):
                self.responses[path] = httpx.Response(200, json=payload)
                report = await self.run_preflight()
                self.assertFalse(report.dependencies_ready)
                self.assertIn("unexpected_shape", {issue.code for issue in report.issues})
                self.assertNotIn("private-body", report.model_dump_json())
                self.responses.clear()

    async def test_invalid_unicode_or_nonfinite_schema_is_sanitized(self):
        for value in ('"\\ud800"', "1e999"):
            with self.subTest(value=value):
                self.responses["/object_info/VAELoader"] = httpx.Response(
                    200, content=('{"VAELoader":{"input":{"required":{}},"private":' + value + '}}').encode())
                report = await self.run_preflight()
                self.assertFalse(report.dependencies_ready)
                self.assertIn("malformed_json", {issue.code for issue in report.issues})

    async def test_ssl_context_is_forwarded_without_disabling_verification(self):
        context = ssl.create_default_context()
        os.environ["COMFYUI_CA_FILE"] = str(Path(tempfile.gettempdir()) / "private-ca.pem")
        real_client = httpx.AsyncClient
        with patch("backend.config.ssl.create_default_context", return_value=context), \
                patch("backend.comfyui.httpx.AsyncClient", wraps=real_client) as client:
            report = await self.run_preflight()
        self.assertTrue(report.dependencies_ready)
        self.assertIs(client.call_args.kwargs["verify"], context)
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    async def test_cli_explicit_loader_json_and_nonzero_status(self):
        report = await self.run_preflight()
        with patch.object(self.comfy, "preflight", return_value=report) as preflight, \
                patch("backend.launch.load_env_file") as load, patch("sys.stdout", new_callable=io.StringIO) as output, \
                patch("sys.argv", ["backend.comfyui", "--env-file", "explicit.env", "--connection", "server"]):
            self.assertEqual(await asyncio.to_thread(self.comfy.main), 0)
            load.assert_called_once_with(Path("explicit.env"))
            preflight.assert_called_once_with("server", self.comfy.DEFAULT_WORKFLOW)
            self.assertTrue(json.loads(output.getvalue())["dependencies_ready"])
        report.dependencies_ready = False
        with patch.object(self.comfy, "preflight", return_value=report), \
                patch("sys.stdout", new_callable=io.StringIO), patch("sys.argv", ["backend.comfyui"]):
            self.assertEqual(await asyncio.to_thread(self.comfy.main), 1)
        report.dependencies_ready = True
        report.graph_ready = False
        with patch.object(self.comfy, "preflight", return_value=report), \
                patch("sys.stdout", new_callable=io.StringIO), patch("sys.argv", ["backend.comfyui"]):
            self.assertEqual(await asyncio.to_thread(self.comfy.main), 1)
        with patch.object(self.comfy, "preflight") as preflight, \
                patch("backend.launch.load_env_file", side_effect=OSError("C:/private/secret")), \
                patch("sys.stdout", new_callable=io.StringIO) as output, \
                patch("sys.argv", ["backend.comfyui", "--env-file", "explicit.env"]):
            self.assertEqual(await asyncio.to_thread(self.comfy.main), 2)
            preflight.assert_not_called()
            self.assertEqual(json.loads(output.getvalue())["issues"][0]["code"], "invalid_env_file")
            self.assertNotIn("C:/private/secret", output.getvalue())


if __name__ == "__main__":
    unittest.main()
