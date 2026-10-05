"""Trusted candidate registry and offline, pre-upload image preparation.

No filesystem, transport, media authorization or persistence lives here. Callers
supply exact template bytes and installed object_info schemas. A pin is restricted
technical data, not a creative/browser DTO or proof of live render capability.
"""

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
import re
import secrets
from typing import NoReturn


@dataclass(frozen=True)
class Parameter:
    name: str
    node_id: str
    input_name: str
    class_type: str


@dataclass(frozen=True)
class ImageSlot:
    load_id: str
    resize_id: str
    consumer_id: str
    port: str


@dataclass(frozen=True)
class ModelRequirement:
    node_id: str
    input_name: str
    filename: str
    folder: str
    value_key: str | None = None  # Explicit nested rgthree literal, never split dotted API input keys.


@dataclass(frozen=True)
class ImageMapping:
    parameters: tuple[Parameter, ...]
    slots: tuple[ImageSlot, ...]
    # (axis, consumer node, input), and (consumer node, input, source node, output index).
    size_targets: tuple[tuple[str, str, str], ...]
    graph_links: tuple[tuple[str, str, str, int], ...]
    geometry_rule: str
    geometry_source: str
    crop_policy: tuple[tuple[str, str | int], ...] = ()
    # Only these exact undeclared literals are ignored UI widgets, not executable inputs.
    widget_literals: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True)
class WorkflowSpec:
    id: str
    version: str
    basename: str
    file_sha256: str
    preparation_enabled: bool
    mapping: ImageMapping
    required_nodes: tuple[str, ...]
    models: tuple[ModelRequirement, ...]
    kinds: tuple[tuple[str, tuple[str, ...]], ...]
    supported_sizes: tuple[tuple[int, int], ...]
    output_node: str
    output_class: str = "SaveImage"
    output_history_key: str = "images"
    output_media_type: str = "image/png"
    seed_min: int = 0
    seed_max: int = 2**64 - 1
    random_seed_sentinel: int = -1
    description_key: str | None = None


@dataclass(frozen=True)
class ImageSettings:
    prompt: str
    width: int
    height: int
    seed: int | None = None


@dataclass(frozen=True)
class ReferenceSnapshot:
    role: str
    source_id: str
    sha256: str
    input_name: str  # Planned ComfyUI input-relative name; NOT an upload receipt.


_WIDGETS = (("Power Lora Loader (rgthree)", "PowerLoraLoaderHeaderWidget",
             '{"type":"PowerLoraLoaderHeaderWidget"}'),
            ("Power Lora Loader (rgthree)", "➕ Add Lora", '""'))
_CROP = (("upscale_method", "lanczos"), ("keep_proportion", "crop"),
         ("crop_position", "center"), ("divisible_by", 2))
_KREA_NODES = ("CLIPLoader", "CLIPTextEncode", "ConditioningZeroOut", "DiffusionModelLoaderKJ",
               "EmptyLatentImage", "KSampler", "Power Lora Loader (rgthree)", "SaveImage",
               "VAEDecode", "VAELoader", "easy int")
_QWEN_NODES = ("CLIPLoader", "ImageResizeKJv2", "KSampler", "LoadImage", "ModelAttentionBackend",
               "Power Lora Loader (rgthree)", "QwenImage21Cache", "SaveImage", "TextEncodeQwenImage21",
               "UNETLoader", "VAEDecode", "VAELoader", "easy int")
_VIDEO_NODES = ("BasicGuider", "BasicScheduler", "CLIPLoader", "ComfyMathExpression", "ImageResizeKJv2",
                "Int", "KSamplerSelect", "LoadImage", "LoraLoaderModelOnly", "MiniMaxH3SigmaShift", "ModelAttentionBackend",
                "PrimitiveFloat", "RandomNoise", "RIFE VFI", "SamplerCustomAdvanced", "UNETLoader",
                "VAEDecode", "VAEDecodeAudio", "VAELoader", "VHS_VideoCombine")
_KREA_MODELS = (ModelRequirement("844", "model_name", "krea2_turbo_int8_convrot.safetensors", "diffusion_models"),
                ModelRequirement("817", "clip_name", "qwen3vl_4b_fp8_scaled.safetensors", "text_encoders"),
                ModelRequirement("803", "vae_name", "qwen_image_vae.safetensors", "vae"))
_QWEN_MODELS = (ModelRequirement("459_451", "unet_name", "redqw21UNLOCKEDV2TI2I_redqw21UNLOCKEDV2_int8.safetensors", "diffusion_models"),
                ModelRequirement("459_453", "clip_name", "qwen3vl_8b_int8_convrot.safetensors", "text_encoders"),
                ModelRequirement("459_454", "vae_name", "qwen_image_2.1_vae_bf16.safetensors", "vae"))
_VIDEO_MODELS = (ModelRequirement("127", "unet_name", "DasiwaMinimaxH3_dasiwaHybridTurboV3_int8.safetensors", "diffusion_models"),
                 ModelRequirement("128", "clip_name", "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "text_encoders"),
                 ModelRequirement("119", "vae_name", "minimax_h3_video_vae_int8_convrot.safetensors", "vae"),
                 ModelRequirement("120", "vae_name", "minimax_h3_audio_vae_fp32.safetensors", "vae"),
                 ModelRequirement("145", "lora_name", "minimax\\distill\\minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors", "loras"),
                 ModelRequirement("158", "ckpt_name", "rife49.pth", "rife"))
_TXT_MAPPING = ImageMapping(
    (Parameter("prompt", "864", "text", "CLIPTextEncode"), Parameter("width", "815", "value", "easy int"),
     Parameter("height", "814", "value", "easy int"), Parameter("seed", "856", "seed", "KSampler")), (),
    (("width", "854", "width"), ("height", "854", "height")),
    (("819", "model", "844", 0), ("819", "clip", "817", 0), ("864", "clip", "819", 1),
     ("669", "conditioning", "864", 0), ("856", "model", "819", 0),
     ("856", "positive", "864", 0), ("856", "negative", "669", 0),
     ("856", "latent_image", "854", 0), ("668", "samples", "856", 0),
     ("668", "vae", "803", 0), ("865", "images", "668", 0)),
    "krea_latent", "EmptyLatentImage width/height -> KSampler -> VAEDecode -> SaveImage", widget_literals=_WIDGETS)
_QWEN_MAPPING = ImageMapping(
    (Parameter("prompt", "459_474", "prompt", "TextEncodeQwenImage21"),
     Parameter("width", "485", "value", "easy int"), Parameter("height", "484", "value", "easy int"),
     Parameter("seed", "459_458", "seed", "KSampler")),
    (ImageSlot("470", "488", "459_474", "images.image_1"),
     ImageSlot("496", "497", "459_474", "images.image_2"), ImageSlot("498", "499", "459_474", "images.image_3")),
    (("width", "459_474", "resolution"),),
    (("491", "model", "459_451", 0), ("459_469", "model", "491", 0),
     ("495", "model", "459_469", 0), ("495", "clip", "459_453", 0),
     ("459_474", "clip", "495", 1), ("459_474", "vae", "459_454", 0),
     ("459_458", "model", "495", 0),
     ("459_458", "positive", "459_474", 0), ("459_458", "negative", "459_474", 1),
     ("459_458", "latent_image", "459_474", 2), ("459_457", "samples", "459_458", 0),
     ("459_457", "vae", "459_454", 0),
     ("494", "images", "459_457", 0)), "qwen_budget",
    "ComfyUI v0.38.2 comfy_extras/nodes_qwen.py TextEncodeQwenImage21.execute: "
    "a=first resized W/H; r=resolution>0; W=max(32,32*round(r*sqrt(a)/32)); "
    "H=max(32,32*round(r/sqrt(a)/32)); first reference sets latent geometry; "
    "height reaches generated output indirectly through resized reference aspect ratio",
    _CROP, _WIDGETS)
_VIDEO_MAPPING = ImageMapping(
    (Parameter("prompt", "162", "prompt", "MiniMaxH3ImageToVideo"),
     Parameter("width", "152", "Number", "Int"), Parameter("height", "153", "Number", "Int"),
     Parameter("seed", "129", "noise_seed", "RandomNoise"),
     Parameter("duration_seconds", "132", "value", "PrimitiveFloat")),
    (ImageSlot("160", "149", "162", "first_frame"),),
    (("width", "162", "width"), ("height", "162", "height")),
    (("126", "conditioning", "162", 0), ("125", "latent_image", "162", 1)),
    "inspection_only", "Timing/FPS/RIFE/audio and first-frame delivery unverified", _CROP)


WORKFLOWS = (
    WorkflowSpec("krea2-txt2img", "api-v1-local.image-preparation-v1", "txt2img krea2 api v1_local.json",
                 "6b50a21e8ed4932e6b42774afdd594bfca17a7ca74420f8bda90b8d7ed52aca3", True,
                 _TXT_MAPPING, _KREA_NODES, _KREA_MODELS, (("portrait", ()), ("background", ())),
                 ((512, 512), (768, 768), (1024, 1024), (768, 1024), (1024, 768)), "865"),
    WorkflowSpec("krea2-img2img", "api-v1.4-local.inspection-v1", "img2img krea2 v1.4_local.json",
                 "fc85d33a605543665c96473033f3655421c537f4786650b4aacf951ff4087143", False,
                 replace(_TXT_MAPPING, parameters=(Parameter("prompt", "876", "prompt", "Krea2EditGroundedEncode"),
                                                    *_TXT_MAPPING.parameters[1:]),
                         slots=(ImageSlot("880", "866", "876", "image"),), crop_policy=_CROP,
                         graph_links=(("875", "source_image", "866", 0), ("877", "pixels", "866", 0),
                                      ("856", "latent_image", "854", 0), ("668", "samples", "856", 0),
                                      ("881", "images", "668", 0)), geometry_rule="inspection_only"),
                 tuple(c for c in _KREA_NODES if c != "CLIPTextEncode") +
                 ("ImageResizeKJv2", "Krea2EditGroundedEncode", "Krea2EditModelPatch", "Krea2OstrisEditModelPatch", "LoadImage", "VAEEncode"),
                  _KREA_MODELS + (ModelRequirement("819", "lora_1", "krea 2\\edit\\krea2_identity_edit_v1_2.safetensors", "loras", "lora"),),
                 (("single_reference", ("*",)),), (), "881"),
    WorkflowSpec("qwen21-img2img", "api-v1.inspection-v1", "qwen img2img api v1.json",
                 "136482db648cc5325ff369a2b06550cb0214b7b8cdaf7ed4075377e941a2a04e", False,
                 replace(_QWEN_MAPPING, slots=_QWEN_MAPPING.slots[:1]), _QWEN_NODES, _QWEN_MODELS,
                 (("single_reference", ("*",)),), (), "494"),
    WorkflowSpec("qwen21-multi-img2img", "api-v1.1-3img.image-preparation-v1", "qwen img2img api v1.1 3img.json",
                 "5564a33d1103402d91d07fed06607ddf7255ff5a76f5e89ea02e7710a1eb246c", True,
                 _QWEN_MAPPING, _QWEN_NODES, _QWEN_MODELS,
                 (("single_reference", ("*",)), ("sheet", ("portrait", "background")),
                  ("frame", ("portrait", "character_sheet", "background"))),
                 ((512, 512), (768, 768), (1024, 1024)), "494"),
    WorkflowSpec("minimax-h3-img2vid", "api-v1-first-frame.inspection-v1", "minimax img2vid api v1.json",
                 "0bf65deb2bbcf09e1a84a785e1a44cdf94a6a45fc180a58b400a03fc5c32d806", False,
                 _VIDEO_MAPPING, _VIDEO_NODES + ("MiniMaxH3ImageToVideo",), _VIDEO_MODELS,
                 (("img2vid", ("storyboard_frame",)),), (), "157", "VHS_VideoCombine", "unverified", "video/mp4"),
    WorkflowSpec("minimax-h3-ref2vid", "api-v1.inspection-v1", "minimax ref2vid api v1.json",
                 "cdcab2186f1f5e2ae1762e2eb54b23ff29f2e0d34a605b48927533514fe034fc", False,
                 replace(_VIDEO_MAPPING, parameters=(Parameter("prompt", "136", "prompt", "MiniMaxH3ReferenceToVideo"),
                                                     *_VIDEO_MAPPING.parameters[1:]),
                         slots=(ImageSlot("160", "149", "136", "ref_images.ref_image_0"),
                                ImageSlot("159", "150", "136", "ref_images.ref_image_1"),
                                ImageSlot("161", "162", "136", "ref_images.ref_image_2")),
                         size_targets=(("width", "136", "width"), ("height", "136", "height")),
                         graph_links=(("126", "conditioning", "136", 0), ("125", "latent_image", "136", 1))),
                 _VIDEO_NODES + ("MiniMaxH3ReferenceToVideo",), _VIDEO_MODELS,
                 (("ref2vid", ("storyboard_frame", "portrait", "character_sheet")),), (),
                 "157", "VHS_VideoCombine", "unverified", "video/mp4"),
)


class WorkflowValidationError(ValueError):
    """Stable, safe reason codes; raw literals/inventories are never echoed."""

    def __init__(self, code: str, subject: str | None = None):
        self.code, self.subject = code, subject
        super().__init__(code if subject is None else f"{code}: {subject}")


def _fail(code, subject=None) -> NoReturn:
    raise WorkflowValidationError(code, subject)


def _json_value(value, depth=0):
    if depth > 64:
        _fail("json_too_deep")
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float:
        if not math.isfinite(value):
            _fail("invalid_json_value")
        return
    if type(value) in (list, tuple):
        for item in value:
            _json_value(item, depth + 1)
        return
    if type(value) is dict and all(type(k) is str for k in value):
        for item in value.values():
            _json_value(item, depth + 1)
        return
    _fail("invalid_json_value")


def _canonical(value):
    _json_value(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_digest(value) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _unique(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            _fail("duplicate_json_key")
        obj[key] = value
    return obj


def _parse(data):
    if type(data) is dict:
        _json_value(data)
        return deepcopy(data)
    if type(data) not in (str, bytes) or len(data) > 16 * 1024 * 1024:
        _fail("invalid_json_document")
    try:
        obj = json.loads(data, object_pairs_hook=_unique, parse_constant=lambda _: _fail("nonfinite_json"))
        _json_value(obj)
        return obj
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        _fail("invalid_json_document")


def get_workflow(workflow: str) -> WorkflowSpec:
    for spec in WORKFLOWS:
        if workflow in (spec.id, spec.basename):
            return spec
    _fail("unknown_workflow")


def workflow_snapshot(workflow: str) -> dict:
    """Selected authoritative entry, with JSON lists instead of Python tuples."""
    return json.loads(_canonical(asdict(get_workflow(workflow))))


def load_api_graph(data: bytes | str | dict, *, description_key: str | None = None) -> dict:
    graph = _parse(data)
    if type(graph) is not dict:
        _fail("invalid_api_graph")
    if description_key is not None and description_key in graph:
        if type(graph[description_key]) is not str:
            _fail("invalid_description")
        del graph[description_key]
    if not graph or len(graph) > 512:
        _fail("invalid_api_graph")
    for node_id, node in graph.items():
        if not node_id or type(node) is not dict or set(node) - {"class_type", "inputs", "_meta"} \
                or type(node.get("class_type")) is not str or not node["class_type"] \
                or type(node.get("inputs")) is not dict or ("_meta" in node and type(node["_meta"]) is not dict):
            _fail("invalid_api_node")
    return graph


def load_candidate(workflow: str, data: bytes) -> dict:
    """Caller reads a trusted installation file; this function pins its exact bytes."""
    spec = get_workflow(workflow)
    if type(data) is not bytes or hashlib.sha256(data).hexdigest() != spec.file_sha256:
        _fail("template_pin_mismatch")
    return load_api_graph(data, description_key=spec.description_key)


def _descriptor(raw):
    if type(raw) is not list or not 1 <= len(raw) <= 2 or (len(raw) == 2 and type(raw[1]) is not dict):
        _fail("invalid_input_schema")
    kind, options = raw[0], raw[1] if len(raw) == 2 else {}
    if type(kind) is list:
        return "COMBO", {**options, "options": kind}
    if type(kind) is not str or not kind:
        _fail("invalid_input_schema")
    if kind == "COMBO" and type(options.get("options")) is not list:
        _fail("unverified_combo")
    return kind, options


def _inputs(schema, live):
    if type(schema) is not dict or type(schema.get("input")) is not dict \
            or type(schema.get("output")) is not list or any(type(t) is not str for t in schema["output"]):
        _fail("invalid_node_schema")
    defs, required = {}, set()
    for group in ("required", "optional"):
        fields = schema["input"].get(group, {})
        if type(fields) is not dict:
            _fail("invalid_node_schema")
        for name, raw in fields.items():
            kind, options = _descriptor(raw)
            if kind != "COMFY_AUTOGROW_V3":
                if name in defs:
                    _fail("duplicate_schema_input")
                defs[name] = (kind, options)
                if group == "required":
                    required.add(name)
                continue
            template = options.get("template", {})
            if type(template) is not dict or type(template.get("input")) is not dict:
                _fail("unsupported_autogrow_schema")
            names, minimum = template.get("names"), template.get("min")
            inner = template.get("input", {}).get("required", {})
            if type(names) is not list or not all(type(n) is str and n and "." not in n for n in names) \
                    or len(set(names)) != len(names) or type(minimum) is not int \
                    or not 0 <= minimum <= len(names) or type(inner) is not dict or len(inner) != 1:
                _fail("unsupported_autogrow_schema")
            child = _descriptor(next(iter(inner.values())))
            ports = [f"{name}.{n}" for n in names]
            if any(p in defs for p in ports) or sum(p in live for p in ports) < minimum:
                _fail("invalid_autogrow_inputs")
            defs.update((p, child) for p in ports)
    return defs, required


def _same(a, b):
    return _canonical(a) == _canonical(b)  # JSON equality, never Python's True == 1.


def _input_name(value):
    if type(value) is not str or not value or len(value) > 512 or value.startswith("/") \
            or any(ord(c) < 32 or ord(c) == 127 or c in '\\:[]%?#<>"|*' for c in value) \
            or any(p in ("", ".", "..") or p.endswith((" ", ".")) for p in value.split("/")):
        _fail("unsafe_input_name")


def _literal(value, kind, options):
    if options.get("forceInput") is True:
        _fail("required_socket_link")
    if kind == "COMBO":
        if not any(_same(value, option) for option in options["options"]):
            _fail("invalid_combo_literal")
    elif kind == "INT":
        if type(value) is not int:
            _fail("invalid_integer_literal")
    elif kind == "FLOAT":
        if type(value) not in (int, float) or not math.isfinite(value):
            _fail("invalid_float_literal")
    elif kind == "STRING":
        if type(value) is not str:
            _fail("invalid_string_literal")
    elif kind == "BOOLEAN":
        if type(value) is not bool:
            _fail("invalid_boolean_literal")
    else:
        _fail("required_socket_link")
    if kind in ("INT", "FLOAT"):
        for bound in ("min", "max"):
            if bound in options and (type(options[bound]) not in (int, float) or not math.isfinite(options[bound])):
                _fail("invalid_numeric_schema")
        if ("min" in options and value < options["min"]) or ("max" in options and value > options["max"]):
            _fail("numeric_range")


def _contract(graph, spec, links):
    mapping = spec["mapping"]
    parameters = {p["name"]: p for p in mapping["parameters"]}
    if set(parameters) != {"prompt", "width", "height", "seed"} \
            or len({(p["node_id"], p["input_name"]) for p in parameters.values()}) != 4:
        _fail("invalid_parameter_mapping")
    for p in parameters.values():
        node = graph.get(p["node_id"], {})
        if node.get("class_type") != p["class_type"] or p["input_name"] not in node.get("inputs", {}) \
                or (p["node_id"], p["input_name"]) in links:
            _fail("invalid_parameter_mapping")
    if {n["class_type"] for n in graph.values()} != set(spec["required_nodes"]):
        _fail("node_requirements_mismatch")
    for axis, node_id, field in mapping["size_targets"]:
        if graph.get(node_id, {}).get("inputs", {}).get(field) != [parameters[axis]["node_id"], 0]:
            _fail("geometry_mapping_mismatch")
    for node_id, field, source_id, index in mapping["graph_links"]:
        if graph.get(node_id, {}).get("inputs", {}).get(field) != [source_id, index]:
            _fail("geometry_trace_mismatch")
    absent = False
    for slot in mapping["slots"]:
        load, resize, consumer, port = (slot[k] for k in ("load_id", "resize_id", "consumer_id", "port"))
        if load not in graph:
            absent = True
            if resize in graph or port in graph.get(consumer, {}).get("inputs", {}):
                _fail("incomplete_slot_removal")
            continue
        if absent or graph[load]["class_type"] != "LoadImage" \
                or graph.get(resize, {}).get("class_type") != "ImageResizeKJv2" \
                or graph.get(consumer, {}).get("inputs", {}).get(port) != [resize, 0] \
                or graph[resize]["inputs"].get("image") != [load, 0]:
            _fail("slot_mapping_mismatch")
        for axis in ("width", "height"):
            if graph[resize]["inputs"].get(axis) != [parameters[axis]["node_id"], 0]:
                _fail("resize_mapping_mismatch")
        for field, value in mapping["crop_policy"]:
            if not _same(graph[resize]["inputs"].get(field), value):
                _fail("crop_policy_mismatch")
        if {dst for dst, src in links.items() if src[0] == load} != {(resize, "image")} \
                or {dst for dst, src in links.items() if src[0] == resize} != {(consumer, port)}:
            _fail("shared_reference_branch")


def _freeze_inventory(workflow, inventory):
    if inventory is None:
        return {}
    if not isinstance(inventory, Mapping):
        _fail("invalid_model_inventory")
    frozen = {}
    for folder in {m["folder"] for m in workflow["models"]}:
        if folder in inventory:
            values = inventory[folder]
            if type(values) not in (list, tuple) or any(type(v) is not str or not v for v in values):
                _fail("invalid_model_inventory")
            frozen[folder] = list(values)
    return frozen


def validate_graph(graph: dict, schemas: Mapping[str, dict], *, workflow: dict | None = None,
                   planned_loaders: Sequence[str] = (),
                   model_inventory: Mapping[str, Sequence[str]] | None = None) -> None:
    """Validate actual installed schemas. No model menu => fail closed/unverified.

    Only registry-declared LoadImage.image fields may bypass an existing-file menu
    for safe planned names. This does not attest that those files exist or match bytes.
    """
    graph = load_api_graph(graph)
    inventory = {} if workflow is None else _freeze_inventory(workflow, model_inventory)
    used, definitions, links = {}, {}, {}
    widgets = {} if workflow is None else {(cls, field): encoded
                                           for cls, field, encoded in workflow["mapping"]["widget_literals"]}
    declared_loaders = set() if workflow is None else {s["load_id"] for s in workflow["mapping"]["slots"]}
    if set(planned_loaders) - declared_loaders:
        _fail("undeclared_reference_loader")
    for node_id, node in graph.items():
        cls = node["class_type"]
        if cls not in schemas:
            _fail("missing_node", cls)
        used[cls] = schemas[cls]
        defs, required = _inputs(schemas[cls], node["inputs"])
        definitions[node_id] = defs
        if required - node["inputs"].keys():
            _fail("missing_required_input", node_id)
        for field, value in node["inputs"].items():
            if field not in defs:
                if (cls, field) not in widgets or _canonical(value) != widgets[cls, field]:
                    _fail("unknown_input", node_id)
                continue
            kind, options = defs[field]
            if cls == "LoadImage" and field == "image" and node_id in planned_loaders:
                _input_name(value)
                continue
            # Schema-classified combo literals can themselves be arbitrary two-item arrays.
            literal_combo = kind == "COMBO" and any(_same(value, o) for o in options["options"])
            if type(value) is list and not literal_combo:
                if len(value) != 2 or type(value[0]) is not str or type(value[1]) is not int or value[1] < 0:
                    _fail("invalid_link", node_id)
                links[node_id, field] = value
            else:
                _literal(value, kind, options)
    for (node_id, field), (source_id, index) in links.items():
        if source_id not in graph:
            _fail("dangling_link", node_id)
        output = used[graph[source_id]["class_type"]]["output"]
        if index >= len(output):
            _fail("invalid_output_index", node_id)
        if output[index] != definitions[node_id][field][0]:
            _fail("socket_type_mismatch", node_id)
    visiting, visited = set(), set()
    parents = {node_id: [] for node_id in graph}
    for (node_id, _), (source_id, _) in links.items():
        parents[node_id].append(source_id)

    def visit(node_id):
        if node_id in visiting:
            _fail("graph_cycle")
        if node_id not in visited:
            visiting.add(node_id)
            for source_id in parents[node_id]:
                visit(source_id)
            visiting.remove(node_id)
            visited.add(node_id)

    for node_id in graph:
        visit(node_id)
    for (node_id, field), (source_id, index) in links.items():
        kind, options = definitions[node_id][field]
        if kind in ("INT", "FLOAT"):
            # The two enabled templates use only this declared, identity numeric primitive.
            source = graph[source_id]
            if source["class_type"] != "easy int" or index != 0:
                _fail("unresolved_numeric_bound", node_id)
            _literal(source["inputs"]["value"], kind, {k: v for k, v in options.items() if k != "forceInput"})
    if workflow is not None:
        _contract(graph, workflow, links)
        output_id = workflow["output_node"]
        if graph.get(output_id, {}).get("class_type") != workflow["output_class"] \
                or workflow["output_class"] != "SaveImage" \
                or {n for n in graph if used[graph[n]["class_type"]].get("output_node") is True} != {output_id}:
            _fail("unexpected_output_node")
        for model in workflow["models"]:
            node = graph.get(model["node_id"], {})
            if node.get("inputs", {}).get(model["input_name"]) != model["filename"]:
                _fail("model_mapping_mismatch")
            kind, options = definitions[model["node_id"]][model["input_name"]]
            if kind != "COMBO" and (kind != "STRING" or model["folder"] not in inventory):
                _fail("model_unverified")
            if kind == "COMBO" and not any(_same(model["filename"], o) for o in options["options"]):
                _fail("missing_model")
            if model["folder"] in inventory and model["filename"] not in inventory[model["folder"]]:
                _fail("missing_model")


def _request(spec, kind, settings, references):
    if not spec["preparation_enabled"]:
        _fail("inspection_only_workflow")
    roles = dict(spec["kinds"]).get(kind)
    if roles is None or len(references) != len(roles) \
            or (roles != ["*"] and [r["role"] for r in references] != roles):
        _fail("reference_roles_or_cardinality")
    if type(settings.get("prompt")) is not str or not settings["prompt"].strip() \
            or len(settings["prompt"]) > 32000:
        _fail("invalid_prompt")
    if any(type(settings.get(axis)) is not int for axis in ("width", "height")) \
            or [settings["width"], settings["height"]] not in spec["supported_sizes"]:
        _fail("unsupported_size")
    seed = settings.get("seed")
    if seed is not None and (type(seed) is not int or
                            (seed != spec["random_seed_sentinel"] and not spec["seed_min"] <= seed <= spec["seed_max"])):
        _fail("invalid_seed")
    for ref in references:
        if set(ref) != {"role", "source_id", "sha256", "input_name"} \
                or type(ref["role"]) is not str or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", ref["role"]) \
                or type(ref["source_id"]) is not str or not ref["source_id"].strip() or len(ref["source_id"]) > 256 \
                or type(ref["sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", ref["sha256"]):
            _fail("invalid_reference_snapshot")
        _input_name(ref["input_name"])
    if len({r["input_name"] for r in references}) != len(references):
        _fail("duplicate_reference_input")


def _bind_references(graph, spec, references):
    for index, slot in enumerate(spec["mapping"]["slots"]):
        load, resize, consumer, port = (slot[k] for k in ("load_id", "resize_id", "consumer_id", "port"))
        if index < len(references):
            graph[load]["inputs"]["image"] = references[index]["input_name"]
        else:
            del graph[consumer]["inputs"][port]
            del graph[load], graph[resize]


def _geometry(spec, settings):
    width, height = settings["width"], settings["height"]
    mapping = spec["mapping"]
    if mapping["geometry_rule"] == "qwen_budget":
        aspect = width / height
        predicted = [max(32, 32 * round(width * math.sqrt(aspect) / 32)),
                     max(32, 32 * round(width / math.sqrt(aspect) / 32))]
    elif mapping["geometry_rule"] == "krea_latent":
        predicted = [width, height]
    else:
        _fail("unverified_geometry")
    if predicted != [width, height]:
        _fail("predicted_geometry_mismatch")
    return {"predicted_size": predicted, "measured_size": None,
            "reference_resize_size": [width, height] if mapping["slots"] else None,
            "rule": mapping["geometry_rule"], "source": mapping["geometry_source"],
            "size_targets": mapping["size_targets"], "graph_links": mapping["graph_links"],
            "crop_policy": mapping["crop_policy"], "live_verified": False}


def prepare_image(workflow: str, template: bytes, *, kind: str, settings: ImageSettings,
                  references: Sequence[ReferenceSnapshot], schemas: Mapping[str, dict],
                  model_inventory: Mapping[str, Sequence[str]] | None = None) -> dict:
    """Pure except ONCE-only secrets sampling, strictly after all request/graph validation.

    Supply schemas as {class_type: actual object_info entry}. Model combos must
    expose the exact selected filename, or a STRING loader requires explicit native
    inventory as {folder: exact filenames}. Inventory never overrides a combo menu.
    No reference upload or checksum/authorization verification is performed.
    """
    spec = workflow_snapshot(workflow)
    if type(settings) is not ImageSettings or any(type(r) is not ReferenceSnapshot for r in references):
        _fail("invalid_typed_request")
    values, refs = asdict(settings), [asdict(r) for r in references]
    _request(spec, kind, values, refs)
    graph = load_candidate(workflow, template)
    template_graph_sha256 = canonical_digest(graph)
    used = {node["class_type"] for node in graph.values()}
    if used - schemas.keys():
        _fail("missing_node")
    frozen_schemas = _parse({cls: schemas[cls] for cls in sorted(used)})
    frozen_inventory = _freeze_inventory(spec, model_inventory)
    seed_target = next(p for p in spec["mapping"]["parameters"] if p["name"] == "seed")
    seed_defs, _ = _inputs(frozen_schemas[seed_target["class_type"]], graph[seed_target["node_id"]]["inputs"])
    seed_kind, seed_options = seed_defs.get(seed_target["input_name"], (None, {}))
    if seed_kind != "INT" or any(type(seed_options.get(bound, spec[f"seed_{bound}"])) is not int
                                 for bound in ("min", "max")):
        _fail("invalid_seed_schema")
    low = max(spec["seed_min"], seed_options.get("min", spec["seed_min"]))
    high = min(spec["seed_max"], seed_options.get("max", spec["seed_max"]))
    if type(low) is not int or type(high) is not int or low > high:
        _fail("invalid_seed_schema")
    randomize = values["seed"] in (None, spec["random_seed_sentinel"])
    if randomize:
        values["seed"] = low
    # Defaults are replaced, not executed. Check each mapping before replacing its literal.
    for p in spec["mapping"]["parameters"]:
        node = graph.get(p["node_id"], {})
        if node.get("class_type") != p["class_type"] or p["input_name"] not in node.get("inputs", {}) \
                or type(node["inputs"][p["input_name"]]) is list:
            _fail("invalid_parameter_mapping")
        node["inputs"][p["input_name"]] = values[p["name"]]
    # Validate all original branches before removing anything, including exclusive ownership.
    loaders = [s["load_id"] for s in spec["mapping"]["slots"]]
    validate_graph(graph, frozen_schemas, workflow=spec, planned_loaders=loaders, model_inventory=frozen_inventory)
    _bind_references(graph, spec, refs)
    loaders = [s["load_id"] for s in spec["mapping"]["slots"][:len(refs)]]
    validate_graph(graph, frozen_schemas, workflow=spec, planned_loaders=loaders, model_inventory=frozen_inventory)
    geometry = _geometry(spec, values)
    if randomize:
        values["seed"] = low + secrets.randbelow(high - low + 1)
        graph[seed_target["node_id"]]["inputs"][seed_target["input_name"]] = values["seed"]
    output = {"node_id": spec["output_node"], "class_type": spec["output_class"],
              "history_key": spec["output_history_key"], "media_type": spec["output_media_type"]}
    pin = {"pin_version": 1, "stage": "pre_upload", "kind": kind, "registry_snapshot": spec,
           "registry_sha256": canonical_digest(spec), "mapping_sha256": canonical_digest(spec["mapping"]),
           "template_sha256": spec["file_sha256"], "template_graph_sha256": template_graph_sha256,
            "graph": graph, "graph_sha256": canonical_digest(graph), "schemas": frozen_schemas,
            "schema_sha256": {cls: canonical_digest(s) for cls, s in frozen_schemas.items()},
            "model_inventory": frozen_inventory, "model_inventory_sha256": canonical_digest(frozen_inventory),
           "settings": values, "references": refs, "reference_bytes_verified": False,
           "expected_output": output, "expected_geometry": geometry}
    pin["pin_sha256"] = canonical_digest(pin)
    return pin


def replay_prepared(data: bytes | str | dict) -> dict:
    """Deserialize/validate a frozen technical pin, without files/registry/network/RNG.

    Digests detect corruption, not a malicious rewrite with recomputed digests;
    trusted worker storage must protect the pin's identity and authorization.
    """
    pin = _parse(data)
    if type(pin) is not dict:
        _fail("invalid_prepared_pin")
    checksum = pin.pop("pin_sha256", None)
    if checksum != canonical_digest(pin):
        _fail("prepared_pin_digest_mismatch")
    pin["pin_sha256"] = checksum
    try:
        spec, graph, schemas = pin["registry_snapshot"], pin["graph"], pin["schemas"]
        if pin["pin_version"] != 1 or pin["stage"] != "pre_upload" or pin["reference_bytes_verified"] is not False \
                or pin["registry_sha256"] != canonical_digest(spec) \
                or pin["mapping_sha256"] != canonical_digest(spec["mapping"]) \
                or pin["template_sha256"] != spec["file_sha256"] \
                or pin["graph_sha256"] != canonical_digest(graph) \
                or pin["model_inventory_sha256"] != canonical_digest(pin["model_inventory"]) \
                or pin["schema_sha256"] != {cls: canonical_digest(s) for cls, s in schemas.items()}:
            _fail("prepared_component_digest_mismatch")
        _request(spec, pin["kind"], pin["settings"], pin["references"])
        if type(pin["settings"]["seed"]) is not int or pin["settings"]["seed"] < spec["seed_min"]:
            _fail("unresolved_prepared_seed")
        loaders = [s["load_id"] for s in spec["mapping"]["slots"][:len(pin["references"])]]
        if set(schemas) != {n["class_type"] for n in graph.values()}:
            _fail("prepared_schema_set_mismatch")
        validate_graph(graph, schemas, workflow=spec, planned_loaders=loaders, model_inventory=pin["model_inventory"])
        for p in spec["mapping"]["parameters"]:
            if not _same(graph[p["node_id"]]["inputs"][p["input_name"]], pin["settings"][p["name"]]):
                _fail("prepared_parameter_mismatch")
        for slot, ref in zip(spec["mapping"]["slots"], pin["references"]):
            if graph[slot["load_id"]]["inputs"]["image"] != ref["input_name"]:
                _fail("prepared_reference_mismatch")
        if any(s["load_id"] in graph or s["resize_id"] in graph for s in spec["mapping"]["slots"][len(loaders):]) \
                or pin["expected_geometry"] != _geometry(spec, pin["settings"]) \
                or pin["expected_output"] != {"node_id": spec["output_node"], "class_type": spec["output_class"],
                                               "history_key": spec["output_history_key"], "media_type": spec["output_media_type"]}:
            _fail("prepared_contract_mismatch")
    except (KeyError, TypeError, IndexError, AttributeError):
        _fail("invalid_prepared_pin")
    return pin
