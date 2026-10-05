from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1] / "workflow" / "comfyui"
TXT = "krea2-txt2img"
QWEN = "qwen21-multi-img2img"


def schema(required, outputs, optional=None, *, output_node=False):
    return {"input": {"required": required, "optional": optional or {}},
            "output": outputs, "output_node": output_node}


def installed_schemas():
    """Sanitized shape fixture from local object_info, not a private inventory."""
    integer = ["INT", {"min": 0, "max": 16384}]
    return {
        "easy int": schema({"value": ["INT", {"min": -999999, "max": 999999}]}, ["INT"]),
        "VAELoader": schema({"vae_name": [["qwen_image_vae.safetensors",
                                                  "qwen_image_2.1_vae_bf16.safetensors"]]}, ["VAE"]),
        "CLIPLoader": schema({"clip_name": [["qwen3vl_4b_fp8_scaled.safetensors",
                                                    "qwen3vl_8b_int8_convrot.safetensors"]],
                              "type": [["krea2", "qwen_image"]]}, ["CLIP"],
                             {"device": [["default", "cpu"]]}),
        "DiffusionModelLoaderKJ": schema({
            "model_name": [["krea2_turbo_int8_convrot.safetensors"]],
            "weight_dtype": [["default"]], "compute_dtype": [["default"]],
            "patch_cublaslinear": ["BOOLEAN"], "sage_attention": [["disabled"]],
            "enable_fp16_accumulation": ["BOOLEAN"]}, ["MODEL"]),
        "UNETLoader": schema({"unet_name": [["redqw21UNLOCKEDV2TI2I_redqw21UNLOCKEDV2_int8.safetensors"]],
                              "weight_dtype": [["default"]]}, ["MODEL"]),
        "Power Lora Loader (rgthree)": schema({}, ["MODEL", "CLIP"],
                                              {"model": ["MODEL"], "clip": ["CLIP"]}),
        "EmptyLatentImage": schema({"width": ["INT", {"min": 16, "max": 16384, "step": 8}],
                                    "height": ["INT", {"min": 16, "max": 16384, "step": 8}],
                                    "batch_size": ["INT", {"min": 1, "max": 4096}]}, ["LATENT"]),
        "CLIPTextEncode": schema({"text": ["STRING"], "clip": ["CLIP"]}, ["CONDITIONING"]),
        "ConditioningZeroOut": schema({"conditioning": ["CONDITIONING"]}, ["CONDITIONING"]),
        "KSampler": schema({"model": ["MODEL"], "seed": ["INT", {"min": 0, "max": 2**64 - 1}],
                            "steps": ["INT", {"min": 1, "max": 10000}],
                            "cfg": ["FLOAT", {"min": 0, "max": 100}],
                            "sampler_name": [["euler", "euler_ancestral"]],
                            "scheduler": [["simple"]], "positive": ["CONDITIONING"],
                            "negative": ["CONDITIONING"], "latent_image": ["LATENT"],
                            "denoise": ["FLOAT", {"min": 0, "max": 1}]}, ["LATENT"]),
        "VAEDecode": schema({"samples": ["LATENT"], "vae": ["VAE"]}, ["IMAGE"]),
        "SaveImage": schema({"images": ["IMAGE"], "filename_prefix": ["STRING"]}, ["IMAGE"],
                            output_node=True),
        "LoadImage": schema({"image": [["existing-public-fixture.png"], {"image_upload": True}]},
                            ["IMAGE", "MASK"]),
        "ImageResizeKJv2": schema({"image": ["IMAGE"], "width": integer, "height": integer,
                                   "upscale_method": [["lanczos", "bilinear"]],
                                   "keep_proportion": [["crop", "pad"]], "pad_color": ["STRING"],
                                   "crop_position": [["center", "top"]],
                                   "divisible_by": ["INT", {"min": 0, "max": 512}]},
                                  ["IMAGE", "INT", "INT", "MASK"], {"device": [["cpu", "gpu"]]}),
        "ModelAttentionBackend": schema({"model": ["MODEL"],
                                          "attention": ["COMBO", {"options": ["comfy kitchen attention",
                                                                                 "pytorch attention"]}]}, ["MODEL"]),
        "QwenImage21Cache": schema({"model": ["MODEL"],
                                    "device": ["COMBO", {"options": ["auto", "cpu", "off"]}],
                                    "dtype": ["COMBO", {"options": ["default", "int8", "int4"]}]}, ["MODEL"]),
        "TextEncodeQwenImage21": schema({"clip": ["CLIP"], "prompt": ["STRING"],
                                         "negative_prompt": ["STRING"],
                                         "resolution": ["INT", {"min": 0, "max": 4096, "step": 32}],
                                         "images": ["COMFY_AUTOGROW_V3", {"template": {
                                             "input": {"required": {"image": ["IMAGE", {}]}},
                                             "names": [f"image_{i}" for i in range(1, 17)], "min": 0}}]},
                                        ["CONDITIONING", "CONDITIONING", "LATENT"], {"vae": ["VAE"]}),
    }


class ImageWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("backend.comfyui_workflows"),
                             "The pure image registry/preparation module is not implemented")
        from backend import comfyui_workflows
        self.w = comfyui_workflows
        self.schemas = installed_schemas()
        self.qwen = (ROOT / "qwen img2img api v1.1 3img.json").read_bytes()
        self.txt = (ROOT / "txt2img krea2 api v1_local.json").read_bytes()

    def refs(self, roles):
        return [self.w.ReferenceSnapshot(role=role, source_id=f"candidate-{i}", sha256=f"{i+1:064x}",
                                         input_name=f"kinodel/job/ref-{i}.png") for i, role in enumerate(roles)]

    def prepare(self, workflow=QWEN, kind="sheet", roles=("portrait", "background"), **settings):
        values = {"prompt": "A quiet scene", "width": 768, "height": 768, "seed": 42}
        values.update(settings)
        return self.w.prepare_image(workflow, self.txt if workflow == TXT else self.qwen,
                                    kind=kind, settings=self.w.ImageSettings(**values),
                                    references=self.refs(roles), schemas=self.schemas)

    def test_authoritative_six_exact_file_pins_only_two_enabled(self):
        self.assertEqual(len(self.w.WORKFLOWS), 6)
        self.assertEqual({s.id for s in self.w.WORKFLOWS if s.preparation_enabled}, {TXT, QWEN})
        for spec in self.w.WORKFLOWS:
            with self.subTest(workflow=spec.id):
                data = (ROOT / spec.basename).read_bytes()
                self.assertEqual(spec.file_sha256, hashlib.sha256(data).hexdigest())
                graph = self.w.load_candidate(spec.id, data)
                self.assertEqual(set(spec.required_nodes), {n["class_type"] for n in graph.values()})
                for model in spec.models:
                    value = graph[model.node_id]["inputs"][model.input_name]
                    if model.value_key is not None:
                        value = value[model.value_key]
                    self.assertEqual(value, model.filename)
                self.assertEqual(self.w.get_workflow(spec.basename), spec)
                with self.assertRaises(ValueError):
                    self.w.load_candidate(spec.id, data + b" ")
        for candidate in ("krea2-img2img", "qwen21-img2img", "minimax-h3-img2vid", "minimax-h3-ref2vid"):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                self.prepare(candidate)

    def test_one_two_three_slots_order_removal_metadata_and_template_untouched(self):
        original = json.loads(self.qwen)
        for kind, roles in (("single_reference", ("reference",)), ("sheet", ("portrait", "background")),
                            ("frame", ("portrait", "character_sheet", "background"))):
            with self.subTest(kind=kind):
                pin = self.prepare(kind=kind, roles=roles)
                graph = pin["graph"]
                for i, (load, resize) in enumerate((("470", "488"), ("496", "497"), ("498", "499"))):
                    port = f"images.image_{i+1}"
                    if i < len(roles):
                        self.assertEqual(graph[load]["inputs"]["image"], f"kinodel/job/ref-{i}.png")
                        self.assertEqual(graph["459_474"]["inputs"][port], [resize, 0])
                        self.assertEqual(graph[resize]["inputs"]["image"], [load, 0])
                    else:
                        self.assertNotIn(port, graph["459_474"]["inputs"])
                        self.assertNotIn(load, graph)
                        self.assertNotIn(resize, graph)
                self.assertEqual([r["role"] for r in pin["references"]], list(roles))
                self.assertEqual(graph["459_474"]["_meta"], original["459_474"]["_meta"])
                self.assertEqual(graph["485"]["inputs"]["value"], 768)
                self.assertEqual(graph["484"]["inputs"]["value"], 768)
                self.assertEqual(graph["459_458"]["inputs"]["seed"], 42)
                self.assertEqual(graph["459_474"]["inputs"]["prompt"], "A quiet scene")
                self.assertEqual(pin["expected_geometry"]["predicted_size"], [768, 768])
                self.assertIsNone(pin["expected_geometry"]["measured_size"])
                self.assertFalse(pin["reference_bytes_verified"])
                self.assertEqual(self.w.replay_prepared(json.dumps(pin)), pin)
        self.assertEqual(json.loads(self.qwen), original)

    def test_txt2img_sizes_and_qwen_square_only(self):
        for width, height in ((512, 512), (768, 768), (1024, 1024), (768, 1024), (1024, 768)):
            for kind in ("portrait", "background"):
                pin = self.prepare(TXT, kind, (), width=width, height=height)
                self.assertEqual(pin["expected_geometry"]["predicted_size"], [width, height])
                self.assertEqual(pin["graph"]["815"]["inputs"]["value"], width)
                self.assertEqual(pin["graph"]["814"]["inputs"]["value"], height)
        for width in (512, 768, 1024):
            self.assertEqual(self.prepare(width=width, height=width)["expected_geometry"]["predicted_size"],
                             [width, width])
        for width, height in ((768, 1024), (1024, 768), (0, 0), (640, 640), (True, 768), (768.0, 768)):
            with self.subTest(size=(width, height)), self.assertRaises(ValueError):
                self.prepare(width=width, height=height)

    def test_exact_cardinality_roles_and_settings_fail_before_randomization(self):
        cases = (("single_reference", ()), ("single_reference", ("a", "b", "c", "d")),
                 ("sheet", ("portrait",)), ("sheet", ("background", "portrait")),
                 ("frame", ("portrait", "background")), ("frame", ("portrait", "sheet", "background")),
                 ("unregistered", ("portrait", "background")))
        with patch("backend.comfyui_workflows.secrets.randbelow", side_effect=AssertionError("RNG called")):
            for kind, roles in cases:
                with self.subTest(kind=kind, roles=roles), self.assertRaises(ValueError):
                    self.prepare(kind=kind, roles=roles, seed=None)
            invalid_settings: tuple[dict[str, Any], ...] = ({"prompt": ""}, {"prompt": 5}, {"seed": True},
                                                           {"seed": -2}, {"seed": 2**64}, {"seed": 1.5})
            for settings in invalid_settings:
                with self.subTest(settings=settings), self.assertRaises(ValueError):
                    self.prepare(**settings)
            with self.assertRaises(ValueError):
                self.prepare(TXT, "portrait", ("reference",), seed=None)

    def test_safe_planned_input_names_and_reference_identity(self):
        for name in ("/tmp/a.png", "C:/a.png", "https://a/x.png", "../a.png", "a/../b.png", "a\\b.png",
                     "a.png [input]", "a.png [output]", "a//b.png", "a/./b.png", "a/%2e%2e/b.png", "a\n.png"):
            refs = self.refs(("portrait", "background"))
            refs[0] = self.w.ReferenceSnapshot("portrait", "candidate", "a" * 64, name)
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.w.prepare_image(QWEN, self.qwen, kind="sheet", settings=self.w.ImageSettings("p", 768, 768, 42),
                                     references=refs, schemas=self.schemas)
        for source, digest in (("", "a" * 64), ("source", "not-a-sha256")):
            refs = [self.w.ReferenceSnapshot("reference", source, digest, "safe.png")]
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.w.prepare_image(QWEN, self.qwen, kind="single_reference",
                                     settings=self.w.ImageSettings("p", 768, 768, 42),
                                     references=refs, schemas=self.schemas)

    def test_random_seed_once_after_validation_and_replay_without_external_access(self):
        for sentinel in (None, -1):
            with patch("backend.comfyui_workflows.secrets.randbelow", return_value=123) as rng:
                pin = self.prepare(seed=sentinel)
                rng.assert_called_once_with(2**64)
                self.assertEqual(pin["settings"]["seed"], 123)
            self.qwen = b"mutated source"
            with patch("backend.comfyui_workflows.secrets.randbelow", side_effect=AssertionError), \
                    patch("backend.comfyui_workflows.get_workflow", side_effect=AssertionError), \
                    patch.object(Path, "read_bytes", side_effect=AssertionError):
                self.assertEqual(self.w.replay_prepared(json.dumps(pin)), pin)
            self.qwen = (ROOT / "qwen img2img api v1.1 3img.json").read_bytes()

    def test_pin_detects_graph_mapping_schema_settings_and_reference_tampering(self):
        pin = self.prepare()
        for key in ("graph", "registry_snapshot", "schemas", "model_inventory", "settings", "references", "expected_geometry"):
            changed = deepcopy(pin)
            if key == "references":
                changed[key][0]["role"] = "other"
            else:
                changed[key]["tampered"] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.w.replay_prepared(changed)
        self.assertEqual(pin["graph_sha256"], self.w.canonical_digest(pin["graph"]))
        self.assertEqual(pin["mapping_sha256"], self.w.canonical_digest(pin["registry_snapshot"]["mapping"]))
        for cls, digest in pin["schema_sha256"].items():
            self.assertEqual(digest, self.w.canonical_digest(pin["schemas"][cls]))

    def test_schema_required_unknown_fields_missing_class_model_output_and_numeric_bounds(self):
        changes = (
            lambda s: s.pop("QwenImage21Cache"),
            lambda s: s["TextEncodeQwenImage21"]["input"]["required"].update({"new_required": ["STRING"]}),
            lambda s: s["UNETLoader"]["input"]["required"].update({"unet_name": [[]]}),
            lambda s: s["UNETLoader"]["input"]["required"].update({"unet_name": ["STRING"]}),
            lambda s: s["TextEncodeQwenImage21"]["input"]["required"]["resolution"][1].update({"max": 512}),
            lambda s: s["ImageResizeKJv2"]["input"]["required"]["height"][1].update({"max": 512}),
            lambda s: s["SaveImage"].update({"output_node": False}),
            lambda s: s["VAEDecode"].update({"output": ["MASK"]}),
            lambda s: s["ModelAttentionBackend"]["input"]["required"]["attention"][1].update({"options": ["other"]}),
            lambda s: s["TextEncodeQwenImage21"]["input"]["required"]["images"][1]["template"].update({"names": ["image_1"]}),
        )
        for i, change in enumerate(changes):
            self.schemas = installed_schemas()
            change(self.schemas)
            with self.subTest(change=i), patch("backend.comfyui_workflows.secrets.randbelow", side_effect=AssertionError), \
                    self.assertRaises(ValueError):
                self.prepare(seed=None)

    def test_v3_model_combos_and_schema_limited_random_seed(self):
        for cls, field in (("UNETLoader", "unet_name"), ("CLIPLoader", "clip_name"), ("VAELoader", "vae_name")):
            spec = self.schemas[cls]["input"]["required"][field]
            self.schemas[cls]["input"]["required"][field] = ["COMBO", {"options": spec[0]}]
        self.schemas["KSampler"]["input"]["required"]["seed"][1] = {"min": 10, "max": 20}
        with patch("backend.comfyui_workflows.secrets.randbelow", return_value=5) as rng:
            pin = self.prepare(seed=None)
            rng.assert_called_once_with(11)
            self.assertEqual(pin["settings"]["seed"], 15)
        with self.assertRaises(ValueError):
            self.prepare(seed=42)

    def test_effective_parameters_validate_instead_of_template_defaults(self):
        self.schemas["KSampler"]["input"]["required"]["seed"][1] = {"min": 10, "max": 20}
        self.schemas["TextEncodeQwenImage21"]["input"]["required"]["resolution"][1]["max"] = 512
        self.schemas["ImageResizeKJv2"]["input"]["required"]["width"][1]["max"] = 512
        self.schemas["ImageResizeKJv2"]["input"]["required"]["height"][1]["max"] = 512
        pin = self.prepare(width=512, height=512, seed=15)
        self.assertEqual(pin["settings"], {"prompt": "A quiet scene", "width": 512, "height": 512, "seed": 15})
        self.assertEqual(self.w.replay_prepared(pin), pin)

    def test_prompt_model_clip_and_vae_paths_are_part_of_mapping(self):
        changes = {
            TXT: (("819", "model", None), ("819", "clip", None),
                  ("856", "positive", ["669", 0]), ("668", "vae", ["803", 1])),
            QWEN: (("495", "model", None), ("495", "clip", None),
                   ("459_474", "vae", None), ("459_458", "model", ["459_451", 0])),
        }
        for workflow, mutations in changes.items():
            template = self.txt if workflow == TXT else self.qwen
            for node_id, field, value in mutations:
                graph = self.w.load_candidate(workflow, template)
                if value is None:
                    del graph[node_id]["inputs"][field]
                else:
                    graph[node_id]["inputs"][field] = value
                with self.subTest(workflow=workflow, field=field), self.assertRaises(ValueError):
                    self.w.validate_graph(graph, self.schemas, workflow=self.w.workflow_snapshot(workflow),
                                          planned_loaders=("470", "496", "498") if workflow == QWEN else ())

    def test_inventory_fallback_is_explicit_frozen_and_cannot_override_combo(self):
        models = self.w.get_workflow(QWEN).models
        inventory = {m.folder: [m.filename] for m in models}
        self.schemas["UNETLoader"]["input"]["required"]["unet_name"] = ["STRING"]
        kwargs: dict[str, Any] = dict(kind="sheet", settings=self.w.ImageSettings("p", 768, 768, 42),
                                      references=self.refs(("portrait", "background")), schemas=self.schemas)
        pin = self.w.prepare_image(QWEN, self.qwen, model_inventory=inventory, **kwargs)
        self.assertEqual(pin["model_inventory"], inventory)
        self.assertEqual(pin["model_inventory_sha256"], self.w.canonical_digest(inventory))
        inventory["diffusion_models"].clear()
        self.assertEqual(self.w.replay_prepared(json.dumps(pin)), pin)
        for supplied in (None, inventory, {"diffusion_models": "not-a-list"}):
            with self.subTest(inventory=supplied), self.assertRaises(ValueError):
                self.w.prepare_image(QWEN, self.qwen, model_inventory=supplied, **kwargs)
        inventory["diffusion_models"] = [models[0].filename]
        self.schemas["UNETLoader"]["input"]["required"]["unet_name"] = [[]]
        with self.assertRaises(ValueError):
            self.w.prepare_image(QWEN, self.qwen, model_inventory=inventory, **kwargs)

    def test_malformed_autogrow_schema_fails_with_safe_error(self):
        for template in (None, [], {"input": None, "names": ["image_1"], "min": 0},
                         {"input": {"required": {}}, "names": ["image_1"], "min": 0}):
            self.schemas = installed_schemas()
            self.schemas["TextEncodeQwenImage21"]["input"]["required"]["images"][1]["template"] = template
            with self.subTest(template=template), self.assertRaises(self.w.WorkflowValidationError):
                self.prepare()

    def test_missing_or_malformed_seed_schema_blocks_before_rng(self):
        for raw in (None, ["FLOAT"], ["INT", {"min": "private-path"}],
                    ["INT", {"max": True}], ["INT", {"min": 10, "max": 9}]):
            self.schemas = installed_schemas()
            fields = self.schemas["KSampler"]["input"]["required"]
            if raw is None:
                del fields["seed"]
            else:
                fields["seed"] = raw
            with self.subTest(raw=raw), patch("backend.comfyui_workflows.secrets.randbelow", side_effect=AssertionError):
                with self.assertRaises(self.w.WorkflowValidationError) as raised:
                    self.prepare(seed=None)
                self.assertNotIn("private-path", str(raised.exception))

    def test_saved_live_schemas_both_connections_prepare_without_effects(self):
        evidence = ROOT.parents[1] / "test-results/comfyui-registry/v02-images/installed-schemas.json"
        if not evidence.is_file():
            self.skipTest("Ignored read-only local/server snapshot is not present in this checkout")
        snapshot = json.loads(evidence.read_bytes())
        for connection in ("local", "server"):
            self.schemas = snapshot["connections"][connection]["schemas"]
            self.assertEqual(len(self.schemas), 17)
            before = deepcopy(self.schemas)
            for workflow, kind, roles in ((TXT, "portrait", ()), (TXT, "background", ()),
                                          (QWEN, "single_reference", ("reference",)),
                                          (QWEN, "sheet", ("portrait", "background")),
                                          (QWEN, "frame", ("portrait", "character_sheet", "background"))):
                with self.subTest(connection=connection, workflow=workflow, kind=kind), \
                        patch("socket.create_connection", side_effect=AssertionError("Network used")), \
                        patch.object(Path, "read_bytes", side_effect=AssertionError("Source reloaded")):
                    pin = self.prepare(workflow, kind, roles)
                    self.assertEqual(self.w.replay_prepared(json.dumps(pin)), pin)
                    self.assertFalse(pin["expected_geometry"]["live_verified"])
                    self.assertEqual(pin["stage"], "pre_upload")
            self.assertEqual(self.schemas, before)

    def test_strict_api_json_and_only_declared_description_metadata(self):
        valid = '{"opaque_id":{"class_type":"X","inputs":{},"_meta":{"title":"kept"}}}'
        self.assertEqual(self.w.load_api_graph(valid)["opaque_id"]["_meta"], {"title": "kept"})
        described = '{"description":"declared only",' + valid[1:]
        self.assertEqual(self.w.load_api_graph(described, description_key="description"), json.loads(valid))
        invalid = ('{}', '{"nodes":[],"links":[]}', '{"1":{"class_type":"X","inputs":{},"inputs":{}}}',
                   '{"1":{"class_type":"X","inputs":{"x":NaN}}}',
                   '{"1":{"class_type":"X","inputs":{"x":1e999}}}',
                   '{"1":{"class_type":"X","inputs":[]}}',
                   '{"description":{"broken":true},' + valid[1:], described,
                   '{"1":{"class_type":"X","inputs":{},"_meta":[]}}')
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.w.load_api_graph(value)
        with self.assertRaises(ValueError):
            self.w.load_api_graph(invalid[-3], description_key="description")

    def test_links_cycles_widgets_and_template_mapping_fail_closed(self):
        graph = self.w.load_candidate(QWEN, self.qwen)
        snapshot = self.w.workflow_snapshot(QWEN)
        mutations = (
            lambda g: g["459_474"]["inputs"].update({"images.image_1": ["missing", 0]}),
            lambda g: g["459_474"]["inputs"].update({"images.image_1": ["488", 99]}),
            lambda g: g["459_474"]["inputs"].update({"images.image_1": ["488", True]}),
            lambda g: g["459_474"]["inputs"].update({"images.image_1": ["485", 0]}),
            lambda g: g["488"]["inputs"].update({"image": ["488", 0]}),
            lambda g: g["459_474"]["inputs"].pop("negative_prompt"),
            lambda g: g["495"]["inputs"].update({"lora_1": {"on": False}}),
            lambda g: g["495"]["inputs"].update({"➕ Add Lora": "not empty"}),
            lambda g: g["495"]["inputs"]["PowerLoraLoaderHeaderWidget"].update({"extra": True}),
        )
        for i, mutate in enumerate(mutations):
            changed = deepcopy(graph)
            mutate(changed)
            with self.subTest(change=i), self.assertRaises(ValueError):
                self.w.validate_graph(changed, self.schemas, workflow=snapshot,
                                      planned_loaders=("470", "496", "498"))
        for mutate in (lambda g: g["488"]["inputs"].update({"keep_proportion": "pad"}),
                       lambda g: g["459_474"]["inputs"].update({"images.image_2": ["488", 0]}),
                       lambda g: g["494"]["inputs"].update({"images": ["488", 0]})):
            changed = deepcopy(graph)
            mutate(changed)
            with self.assertRaises(ValueError):
                self.w.validate_graph(changed, self.schemas, workflow=snapshot,
                                      planned_loaders=("470", "496", "498"))

    def test_arbitrary_two_item_combo_literal_is_not_a_link(self):
        graph = {"opaque": {"class_type": "ArrayMenu", "inputs": {"choice": ["not-a-node", 0]}}}
        schemas = {"ArrayMenu": schema({"choice": [[["not-a-node", 0], ["another", 1]]]}, [])}
        self.w.validate_graph(graph, schemas)
        graph["opaque"]["inputs"]["choice"] = ["not-a-node", False]
        with self.assertRaises(ValueError):
            self.w.validate_graph(graph, schemas)


if __name__ == "__main__":
    unittest.main()
