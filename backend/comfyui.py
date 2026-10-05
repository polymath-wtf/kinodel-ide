"""Bounded, read-only native ComfyUI dependency preflight; never submits a graph."""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import ssl
from typing import Literal
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field

from backend.config import ComfyUIConfigError, resolve_comfyui_connection
from backend import comfyui_workflows as registry


DEFAULT_WORKFLOW = registry.get_workflow("krea2-txt2img").basename
WORKFLOW_ROOT = Path(__file__).resolve().parents[1] / "workflow" / "comfyui"
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
REQUEST_TIMEOUT = 15.0
TOTAL_TIMEOUT = 60.0


class PreflightIssue(BaseModel):
    code: str
    reason: str
    severity: Literal["error", "warning"] = "error"
    subject: str | None = None


class RuntimeVersions(BaseModel):
    comfyui: str | None = None
    python: str | None = None
    pytorch: str | None = None
    packages: dict[str, str | None] = Field(default_factory=dict)


class DeviceReport(BaseModel):
    name: str | None = None
    type: str | None = None
    vram_total: int | None = None
    vram_free: int | None = None


class NodeDependency(BaseModel):
    class_type: str
    available: bool = False
    python_module: str | None = None
    version: str | None = None
    schema_sha256: str | None = None


class ModelDependency(BaseModel):
    node_id: str
    class_type: str
    input_name: str
    folder: str | None = None
    filename: str | None = None
    available: bool | None = None
    source: Literal["combo", "inventory", "unverified"] = "unverified"


class PreflightReport(BaseModel):
    connection: Literal["local", "server"] | None = None
    endpoint_digest: str | None = None
    workflow: str | None = None
    workflow_sha256: str | None = None
    workflow_id: str | None = None
    workflow_version: str | None = None
    registry_sha256: str | None = None
    preparation_enabled: bool = False
    graph_ready: bool | None = None
    reachable: bool = False
    dependencies_ready: bool = False
    versions: RuntimeVersions = Field(default_factory=RuntimeVersions)
    devices: list[DeviceReport] = Field(default_factory=list)
    nodes: list[NodeDependency] = Field(default_factory=list)
    models: list[ModelDependency] = Field(default_factory=list)
    issues: list[PreflightIssue] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


_REASONS = {
    "invalid_workflow": "Select an available declared workflow basename from the installation workflow directory.",
    "invalid_workflow_graph": "Workflow must be a nonempty API graph of node objects with class_type and inputs.",
    "unavailable": "Selected ComfyUI endpoint could not be reached; no alternative connection was attempted.",
    "tls_error": "ComfyUI TLS verification or negotiation failed; check the certificate and trusted CA configuration.",
    "timeout": "ComfyUI preflight exceeded its bounded request or total timeout.",
    "auth_failed": "ComfyUI rejected authentication or access permission.",
    "http_error": "ComfyUI returned an unsuccessful HTTP response or transport protocol error.",
    "redirect_rejected": "ComfyUI redirected the request; redirects are disabled to protect credentials. Configure the final native endpoint.",
    "malformed_json": "ComfyUI returned malformed JSON.",
    "unexpected_shape": "ComfyUI returned an unexpected response shape or encoding.",
    "response_too_large": "ComfyUI JSON response exceeded the configured byte limit.",
    "missing_node": "Selected workflow requires a node class not exposed by the installed server.",
    "missing_model": "Exact selected model filename is absent from the installed loader combo or model inventory.",
    "model_unverified": "Selected model availability could not be verified; a declared option alone does not prove a special loader's model is installed.",
    "version_unknown": "Installed version was not exposed in the native response; no version was inferred.",
    "metadata_unknown": "Requested diagnostic metadata was not exposed or could not be safely projected.",
    "template_pin_mismatch": "Workflow bytes differ from the registry pin; audit the changed template and publish a new registry version before use.",
}


class _Failure(Exception):
    def __init__(self, code: str):
        self.code = code


def _issue(report: PreflightReport, code: str, subject: str | None = None, *, warning: bool = False) -> None:
    report.issues.append(PreflightIssue(code=code, reason=_REASONS[code],
                                        severity="warning" if warning else "error", subject=subject))


def _unknown(report: PreflightReport, subject: str, *, version: bool = False) -> None:
    report.unknowns.append(subject)
    code = "version_unknown" if version else "metadata_unknown"
    if not any(issue.code == code for issue in report.issues):
        _issue(report, code, warning=True)


def list_workflows() -> list[str]:
    """List only declared, regular installation files; reject symlinks/junctions."""
    try:
        if any(path.is_symlink() or path.is_junction() for path in (WORKFLOW_ROOT, *WORKFLOW_ROOT.parents)):
            return []
        return sorted(name for name in (spec.basename for spec in registry.WORKFLOWS)
                      if (WORKFLOW_ROOT / name).is_file() and not (WORKFLOW_ROOT / name).is_symlink()
                      and not (WORKFLOW_ROOT / name).is_junction())
    except OSError:
        return []


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _parse_json(data: bytes):
    def reject_constant(_):
        raise ValueError("Nonfinite JSON number")

    return json.loads(data, object_pairs_hook=_unique_object, parse_constant=reject_constant)


def _load_workflow(workflow: str, report: PreflightReport) -> dict:
    if workflow not in list_workflows():
        raise _Failure("invalid_workflow")
    report.workflow = workflow
    try:
        path = WORKFLOW_ROOT / workflow
        if path.stat().st_size > MAX_RESPONSE_BYTES:
            raise ValueError
        data = path.read_bytes()
        report.workflow_sha256 = hashlib.sha256(data).hexdigest()
        graph = _parse_json(data)
        spec = registry.get_workflow(workflow)
        graph = registry.load_api_graph(graph, description_key=spec.description_key)
        if any(not re.fullmatch(r"[\w .()+-]{1,160}", node["class_type"]) for node in graph.values()):
            raise ValueError
        report.workflow_id = spec.id
        report.workflow_version = spec.version
        report.registry_sha256 = registry.canonical_digest(registry.workflow_snapshot(spec.id))
        report.preparation_enabled = spec.preparation_enabled
        if report.workflow_sha256 != spec.file_sha256:
            raise _Failure("template_pin_mismatch")
        return graph
    except (OSError, ValueError, RecursionError):
        raise _Failure("invalid_workflow_graph") from None


async def _get_json(client: httpx.AsyncClient, route: str, report: PreflightReport):
    async with asyncio.timeout(REQUEST_TIMEOUT), client.stream("GET", route) as response:
        report.reachable = True
        if 300 <= response.status_code < 400:
            raise _Failure("redirect_rejected")
        if response.status_code in (401, 403):
            raise _Failure("auth_failed")
        if not 200 <= response.status_code < 300:
            raise _Failure("http_error")
        length = response.headers.get("content-length", "")
        if length.isdigit() and int(length) > MAX_RESPONSE_BYTES:
            raise _Failure("response_too_large")
        # Request identity encoding; reject compressed surprises before decoding a zip bomb.
        if response.headers.get("content-encoding", "identity").lower() != "identity":
            raise _Failure("unexpected_shape")
        data = bytearray()
        async for chunk in response.aiter_bytes(chunk_size=65536):
            if len(data) + len(chunk) > MAX_RESPONSE_BYTES:
                raise _Failure("response_too_large")
            data.extend(chunk)
        try:
            return _parse_json(bytes(data))
        except (ValueError, RecursionError):
            raise _Failure("malformed_json") from None


def _safe_text(value, pattern: str, token: str | None) -> str | None:
    if not isinstance(value, str) or len(value) > 160 or (token and token in value):
        return None
    return value if re.fullmatch(pattern, value) else None


def _version(value, token: str | None) -> str | None:
    # Native python_version may be sys.version; retain only its version token, not build paths.
    first = value.split(" ", 1)[0] if isinstance(value, str) else value
    return _safe_text(first, r"v?\d+(?:\.\d+){0,3}[a-zA-Z0-9.+_-]*", token)


def _system_report(stats, report: PreflightReport, token: str | None) -> None:
    if not isinstance(stats, dict) or not isinstance(stats.get("system"), dict) \
            or not isinstance(stats.get("devices"), list) or any(not isinstance(d, dict) for d in stats["devices"]):
        raise _Failure("unexpected_shape")
    system = stats["system"]
    for field, key in (("comfyui", "comfyui_version"), ("python", "python_version"), ("pytorch", "pytorch_version")):
        value = _version(system.get(key), token)
        setattr(report.versions, field, value)
        if value is None:
            _unknown(report, f"versions.{field}", version=True)
    report.versions.packages = {"comfyui-frontend-package": None, "comfyui-embedded-docs": None,
                               "comfyui-workflow-templates": _version(system.get("installed_templates_version"), token)}
    packages = system.get("comfy_package_versions", [])
    if not isinstance(packages, list) or any(not isinstance(package, dict) for package in packages):
        raise _Failure("unexpected_shape")
    for package in packages:
        name = _safe_text(package.get("name"), r"[a-zA-Z0-9_.-]+", token)
        if name is None:
            _unknown(report, "versions.packages.unprojectable")
            continue
        # The native response separates installed from required; required is not a real version.
        report.versions.packages[name] = _version(package.get("installed"), token)
    for package, value in report.versions.packages.items():
        if value is None:
            _unknown(report, f"versions.packages.{package}", version=True)
    for index, raw in enumerate(stats["devices"]):
        device = DeviceReport(name=_safe_text(raw.get("name"), r"[\w ()+.,:\-]+", token),
                              type=_safe_text(raw.get("type"), r"[a-zA-Z0-9_-]+", token))
        for field in ("vram_total", "vram_free"):
            value = raw.get(field)
            setattr(device, field, value if type(value) is int and value >= 0 else None)
        for field in DeviceReport.model_fields:
            if getattr(device, field) is None:
                _unknown(report, f"devices.{index}.{field}")
        report.devices.append(device)
    if not report.devices:
        _unknown(report, "devices")


# Only observed model loaders; special loaders (e.g. RIFE's downloadable menu) stay unverified.
_MODEL_FOLDERS = {
    ("DiffusionModelLoaderKJ", "model_name"): "diffusion_models",
    ("UNETLoader", "unet_name"): "diffusion_models",
    ("CLIPLoader", "clip_name"): "text_encoders",
    ("VAELoader", "vae_name"): "vae",
    ("LoraLoaderModelOnly", "lora_name"): "loras",
}
_MODEL_FIELDS = {field for _, field in _MODEL_FOLDERS} | {"ckpt_name"}


def _model_filename(value) -> str | None:
    if not isinstance(value, str) or not value or len(value) > 512 or ":" in value \
            or value.startswith(("/", "\\")) or any(ord(c) < 32 or ord(c) == 127 for c in value) \
            or any(part in ("", ".", "..") for part in re.split(r"[/\\]", value)):
        return None
    return value  # Preserve exact separators/case, never compare a fuzzy basename.


def _models(graph: dict) -> list[ModelDependency]:
    models = []
    for node_id, node in graph.items():
        cls, inputs = node["class_type"], node["inputs"]
        fields = {field for known, field in _MODEL_FOLDERS if known == cls} | (_MODEL_FIELDS & inputs.keys())
        for field in sorted(fields):
            models.append(ModelDependency(node_id=node_id, class_type=cls, input_name=field,
                                          folder=_MODEL_FOLDERS.get((cls, field)), filename=_model_filename(inputs.get(field))))
        if cls == "Power Lora Loader (rgthree)":
            for field, entry in inputs.items():
                if not re.fullmatch(r"lora_\d+", field) or (isinstance(entry, dict) and entry.get("on") is False):
                    continue
                filename = _model_filename(entry.get("lora")) if isinstance(entry, dict) and entry.get("on") is True else None
                models.append(ModelDependency(node_id=node_id, class_type=cls, input_name=f"{field}.lora",
                                              folder="loras", filename=filename))
    return models


def _combo(schema: dict, field: str) -> list[str] | None:
    for section in ("required", "optional"):
        declaration = schema.get("input", {}).get(section, {}).get(field)
        if isinstance(declaration, list) and declaration and isinstance(declaration[0], list) \
                and all(isinstance(option, str) for option in declaration[0]):
            return declaration[0]
        if isinstance(declaration, list) and len(declaration) == 2 and declaration[0] == "COMBO" \
                and isinstance(declaration[1], dict) and isinstance(declaration[1].get("options"), list) \
                and all(isinstance(option, str) for option in declaration[1]["options"]):
            return declaration[1]["options"]
    return None


def _string_list(value) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise _Failure("unexpected_shape")
    return value


async def _dependencies(client: httpx.AsyncClient, graph: dict, report: PreflightReport, token: str | None) -> tuple[dict, dict]:
    schemas = {}
    for cls in sorted({node["class_type"] for node in graph.values()}):
        payload = await _get_json(client, "object_info/" + quote(cls, safe=""), report)
        if not isinstance(payload, dict):
            raise _Failure("unexpected_shape")
        node = NodeDependency(class_type=cls)
        report.nodes.append(node)
        schema = payload.get(cls)
        if schema is None or schema == {}:
            _issue(report, "missing_node", cls)
            continue
        if not isinstance(schema, dict) or not isinstance(schema.get("input"), dict) \
                or any(not isinstance(schema["input"].get(section, {}), dict) for section in ("required", "optional")):
            raise _Failure("unexpected_shape")
        schemas[cls] = schema
        node.available = True
        try:
            node.schema_sha256 = hashlib.sha256(json.dumps(schema, sort_keys=True, separators=(",", ":"),
                                                            ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        except (ValueError, RecursionError):
            raise _Failure("malformed_json") from None
        node.python_module = _safe_text(schema.get("python_module"), r"[a-zA-Z0-9_.-]+", token)
        node.version = _version(schema.get("version"), token)
        if node.python_module is None:
            _unknown(report, f"nodes.{cls}.python_module")
        if node.version is None:
            _unknown(report, f"nodes.{cls}.version", version=True)
    assert report.workflow is not None  # The caller loaded and pinned the trusted candidate.
    spec = registry.get_workflow(report.workflow)
    report.models = [ModelDependency(node_id=model.node_id, class_type=graph[model.node_id]["class_type"],
                                    input_name=model.input_name, folder=model.folder, filename=model.filename)
                     for model in spec.models] if spec.preparation_enabled else _models(graph)
    folders = None
    inventories = {}
    for model in report.models:
        if model.filename is not None and model.folder is not None:
            options = _combo(schemas.get(model.class_type, {}), model.input_name)
            if options is not None:
                model.source = "combo"
            else:
                if folders is None:
                    folders = _string_list(await _get_json(client, "models", report))
                if model.folder not in inventories:
                    inventories[model.folder] = _string_list(await _get_json(client, "models/" + quote(model.folder, safe=""), report)) \
                        if model.folder in folders else []
                options = inventories[model.folder]
                model.source = "inventory"
            model.available = model.filename in options
        subject = f"{model.node_id}.{model.input_name}"
        if model.available is None:
            report.unknowns.append(f"models.{subject}.available")
            _issue(report, "model_unverified", subject)
        elif not model.available:
            _issue(report, "missing_model", subject)
    return schemas, inventories


def _is_tls_error(error: BaseException | None) -> bool:
    seen = set()
    while error is not None and id(error) not in seen:
        if isinstance(error, ssl.SSLError):
            return True
        seen.add(id(error))
        error = error.__cause__ or error.__context__
    return False


async def preflight(connection: Literal["local", "server"] | None = None, workflow: str = DEFAULT_WORKFLOW,
                    *, transport: httpx.AsyncBaseTransport | None = None) -> PreflightReport:
    """Check selected native dependencies, not execution/VRAM sufficiency or creative capability."""
    report = PreflightReport()
    try:
        graph = _load_workflow(workflow, report)
        settings = resolve_comfyui_connection(connection)
        report.connection = settings.connection
        report.endpoint_digest = settings.endpoint_digest
        headers = {"Accept": "application/json", "Accept-Encoding": "identity"}
        if settings.auth_token:
            headers["Authorization"] = "Bearer " + settings.auth_token
        async with asyncio.timeout(TOTAL_TIMEOUT), httpx.AsyncClient(
            base_url=settings.endpoint, headers=headers, verify=settings.verify, trust_env=False,
            follow_redirects=False, timeout=httpx.Timeout(REQUEST_TIMEOUT, connect=5.0), transport=transport,
        ) as client:
            stats = await _get_json(client, "system_stats", report)
            _system_report(stats, report, settings.auth_token)
            schemas, inventories = await _dependencies(client, graph, report, settings.auth_token)
        report.dependencies_ready = not any(issue.severity == "error" for issue in report.issues)
        if report.preparation_enabled:
            report.graph_ready = False
            if report.dependencies_ready:
                spec = registry.workflow_snapshot(workflow)
                try:
                    registry.validate_graph(graph, schemas, workflow=spec,
                                            planned_loaders=[s["load_id"] for s in spec["mapping"]["slots"]],
                                            model_inventory=inventories)
                    report.graph_ready = True
                except registry.WorkflowValidationError as error:
                    report.issues.append(PreflightIssue(code=error.code,
                        reason="Registered image graph does not satisfy the installed schema or declared mapping; inspect the trusted workflow before any upload."))
    except ComfyUIConfigError as error:
        report.issues.append(PreflightIssue(code=error.code, reason=str(error)))
    except _Failure as error:
        _issue(report, error.code)
    except (TimeoutError, httpx.TimeoutException):
        _issue(report, "timeout")
    except (httpx.HTTPError, ssl.SSLError) as error:
        code = "tls_error" if _is_tls_error(error) else "unavailable" if isinstance(error, httpx.ConnectError) else "http_error"
        _issue(report, code)
    return report


def main() -> int:
    from backend.launch import load_env_file

    parser = argparse.ArgumentParser(description="Read-only native ComfyUI dependency preflight (no generation)")
    parser.add_argument("--env-file", type=Path, help="Explicit environment file; never auto-loaded")
    parser.add_argument("--connection", choices=("local", "server"))
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW, help="Declared installation workflow basename")
    args = parser.parse_args()
    if args.env_file is not None:
        try:
            load_env_file(args.env_file)
        except (OSError, UnicodeError, ValueError):
            report = PreflightReport(issues=[PreflightIssue(code="invalid_env_file", reason="Cannot load the explicit environment file; check its path and assignment syntax.")])
            print(report.model_dump_json(indent=2))
            return 2
    report = asyncio.run(preflight(args.connection, args.workflow))
    print(report.model_dump_json(indent=2))
    return 0 if report.dependencies_ready and report.graph_ready is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
