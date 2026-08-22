from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from .registry import WorkflowSpec, render_root, require_workflow


def _comfy_scripts_dir() -> Path:
    return Path.home() / ".hermes" / "skills" / "kinodel" / "comfyui" / "scripts"


def _load_comfy_modules() -> dict[str, Any]:
    scripts_dir = _comfy_scripts_dir()
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from _common import DEFAULT_LOCAL_HOST, resolve_api_key, unwrap_workflow  # type: ignore
    from run_workflow import ComfyRunner, download_outputs, inject_params, load_schema  # type: ignore

    return {
        "DEFAULT_LOCAL_HOST": DEFAULT_LOCAL_HOST,
        "resolve_api_key": resolve_api_key,
        "unwrap_workflow": unwrap_workflow,
        "ComfyRunner": ComfyRunner,
        "download_outputs": download_outputs,
        "inject_params": inject_params,
        "load_schema": load_schema,
    }


def _first_list(*values: Any) -> list[Any]:
    for value in values:
        if isinstance(value, list):
            return value
        if isinstance(value, str) and value:
            return [value]
    return []


def _coerce_dims(params: dict[str, Any], *, default_width: int, default_height: int, video: bool = False) -> tuple[int, int]:
    image_size = params.get("image_size")
    if isinstance(image_size, dict):
        try:
            return int(image_size.get("width") or default_width), int(image_size.get("height") or default_height)
        except Exception:
            pass
    width_key = "video_width" if video else "width"
    height_key = "video_height" if video else "height"
    width = params.get(width_key) or params.get("width")
    height = params.get(height_key) or params.get("height")
    if width and height:
        return int(width), int(height)
    return default_width, default_height


def _duration_seconds(value: Any, default: int = 4) -> int:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip().lower()
    if s.endswith("s"):
        s = s[:-1]
    try:
        return int(float(s))
    except Exception:
        return default


def _lora_bank(raw: Any, *, limit: int = 5) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw[:limit]:
            if isinstance(item, str):
                out.append({"path": item, "strength": 1.0, "on": True})
            elif isinstance(item, dict):
                path = item.get("path") or item.get("lora") or item.get("name") or ""
                out.append({
                    "path": path,
                    "strength": item.get("strength", item.get("weight", 1.0)),
                    "on": bool(item.get("on", bool(path))) and bool(path),
                })
    return out[:limit]


def _overlay_direct_loras(params: dict[str, Any], out: list[dict[str, Any]], *, prefix: str = "lora", suffix: str = "") -> list[dict[str, Any]]:
    for i in range(1, 6):
        # Supported direct forms:
        #   lora_1_path                         (Klein/generic)
        #   lora_1_high_path / lora_1_low_path  (Wan schema)
        #   lora_1_path_high / lora_1_path_low  (compat)
        path_keys = [f"{prefix}_{i}_{suffix}_path", f"{prefix}_{i}_path_{suffix}"] if suffix else [f"{prefix}_{i}_path"]
        path = None
        for key in path_keys:
            if key in params:
                path = params.get(key)
                break
        if path is None:
            continue
        while len(out) < i:
            out.append({"path": "", "strength": 1.0, "on": False})
        if suffix:
            strength = params.get(f"{prefix}_{i}_{suffix}_strength", params.get(f"{prefix}_{i}_strength_{suffix}", 1.0))
            on = params.get(f"{prefix}_{i}_{suffix}_on", params.get(f"{prefix}_{i}_on_{suffix}", bool(path)))
        else:
            strength = params.get(f"{prefix}_{i}_strength", 1.0)
            on = params.get(f"{prefix}_{i}_on", bool(path))
        out[i - 1] = {"path": path or "", "strength": strength, "on": bool(on) and bool(path)}
    return out[:5]


def _set_lora_args(args: dict[str, Any], bank: list[dict[str, Any]], *, suffix: str = "") -> None:
    for i in range(1, 6):
        if suffix:
            args[f"lora_{i}_{suffix}_on"] = False
            args[f"lora_{i}_{suffix}_path"] = ""
            args[f"lora_{i}_{suffix}_strength"] = 1.0
        else:
            args[f"lora_{i}_on"] = False
            args[f"lora_{i}_path"] = ""
            args[f"lora_{i}_strength"] = 1.0
    for i, lora in enumerate(bank[:5], start=1):
        path = str(lora.get("path") or "")
        strength = lora.get("strength", 1.0)
        on = bool(lora.get("on", bool(path))) and bool(path)
        if suffix:
            args[f"lora_{i}_{suffix}_path"] = path
            args[f"lora_{i}_{suffix}_strength"] = strength
            args[f"lora_{i}_{suffix}_on"] = on
        else:
            args[f"lora_{i}_path"] = path
            args[f"lora_{i}_strength"] = strength
            args[f"lora_{i}_on"] = on


def _schema_defaults(spec: WorkflowSpec) -> dict[str, Any]:
    schema_path = render_root() / spec.schema_path
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    defaults: dict[str, Any] = {}
    for key, meta in (schema.get("parameters") or {}).items():
        if isinstance(meta, dict) and "default" in meta:
            defaults[key] = meta["default"]
    return defaults


def _build_klein_args(job: dict[str, Any], spec: WorkflowSpec) -> dict[str, Any]:
    payload = job.get("payload", {}) or {}
    params = payload.get("params", {}) or {}
    defaults = _schema_defaults(spec)
    prompt = payload.get("prompt") or payload.get("action_prompt")
    if not prompt:
        raise RuntimeError(f"comfyui klein image job missing prompt: {job.get('job_id')}")
    refs = _first_list(payload.get("image_urls"), payload.get("references"), payload.get("image_url"))[:4]
    width, height = _coerce_dims(params, default_width=int(defaults.get("width") or 1024), default_height=int(defaults.get("height") or 1024))
    args: dict[str, Any] = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "seed": params.get("seed", defaults.get("seed", -1)),
        "crop_resize": params.get("crop_resize", defaults.get("crop_resize", "stretch")),
        "crop_resize_side": params.get("crop_resize_side", defaults.get("crop_resize_side", "center")),
        "unet_path": params.get("unet_path", defaults.get("unet_path", "")),
        "sage_attn": params.get("sage_attn", defaults.get("sage_attn", "disabled")),
        "turbo": bool(params.get("turbo", defaults.get("turbo", False))),
        "turbo_lora_path": params.get("turbo_lora_path", defaults.get("turbo_lora_path", "")),
        "turbo_lora_strength": params.get("turbo_lora_strength", defaults.get("turbo_lora_strength", 0.69)),
    }
    for i in range(1, 5):
        args[f"img_url_{i}"] = refs[i - 1] if len(refs) >= i else ""
    loras = _lora_bank(job.get("loras") or params.get("loras") or [])
    loras = _overlay_direct_loras(params, loras)
    _set_lora_args(args, loras)
    return args


def _build_wan_args(job: dict[str, Any], spec: WorkflowSpec) -> dict[str, Any]:
    payload = job.get("payload", {}) or {}
    params = payload.get("params", {}) or {}
    defaults = _schema_defaults(spec)
    prompt = payload.get("prompt") or payload.get("action_prompt")
    if not prompt:
        raise RuntimeError(f"comfyui wan video job missing prompt: {job.get('job_id')}")
    refs = _first_list(payload.get("image_urls"), payload.get("references"), payload.get("image_url"))
    image_url = payload.get("reference_image_url") or payload.get("image_url") or (refs[0] if refs else None)
    if not image_url:
        raise RuntimeError(f"comfyui wan i2v job missing image_url: {job.get('job_id')}")
    width, height = _coerce_dims(
        params,
        default_width=int(defaults.get("video_width") or 832),
        default_height=int(defaults.get("video_height") or 480),
        video=True,
    )
    args: dict[str, Any] = {
        "prompt": prompt,
        "image_url": image_url,
        "video_width": width,
        "video_height": height,
        "crop_resize": params.get("crop_resize", defaults.get("crop_resize", "stretch")),
        "crop_resize_side": params.get("crop_resize_side", defaults.get("crop_resize_side", "center")),
        "seed": params.get("seed", defaults.get("seed", 42)),
        "duration": _duration_seconds(params.get("duration", defaults.get("duration", 4)), default=int(defaults.get("duration") or 4)),
        "unet_path_low": params.get("unet_path_low", defaults.get("unet_path_low", "")),
        "unet_path_high": params.get("unet_path_high", defaults.get("unet_path_high", "")),
        "sage_attn": params.get("sage_attn", defaults.get("sage_attn", "disabled")),
    }
    generic = job.get("loras") or params.get("wan_loras") or params.get("loras") or []
    high = _lora_bank(params.get("loras_high") or job.get("loras_high") or generic)
    low = _lora_bank(params.get("loras_low") or job.get("loras_low") or generic)
    high = _overlay_direct_loras(params, high, suffix="high")
    low = _overlay_direct_loras(params, low, suffix="low")
    _set_lora_args(args, high, suffix="high")
    _set_lora_args(args, low, suffix="low")
    return args


def build_workflow_args(job: dict[str, Any], spec: WorkflowSpec) -> dict[str, Any]:
    if spec.workflow_id == "img2img_klein":
        return _build_klein_args(job, spec)
    if spec.workflow_id == "img2vid_wan_lora":
        return _build_wan_args(job, spec)
    raise RuntimeError(f"no argument mapper for ComfyUI workflow: {spec.workflow_id}")


def _preferred_outputs(downloaded: list[dict[str, Any]], spec: WorkflowSpec) -> list[dict[str, Any]]:
    preferred = [o for o in downloaded if isinstance(o, dict) and o.get("type") == spec.preferred_media_type]
    if spec.output_kind == "image":
        output_source = [o for o in preferred if o.get("source_type") == "output"]
        return output_source or preferred
    return preferred or downloaded


def _copy_or_keep_output(out: dict[str, Any], dest: Path) -> Path:
    produced = Path(out["file"])
    if produced.resolve() == dest.resolve():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(produced, dest)
    return dest


def _view_url(filename: str, source_type: str = "output", subfolder: str = "", host: str | None = None) -> str | None:
    mods = _load_comfy_modules()
    base = (host or mods["DEFAULT_LOCAL_HOST"]).rstrip("/")
    return base + "/view?" + urlencode({"filename": filename, "type": source_type, "subfolder": subfolder})


def _save_submitted_workflow(output_dir: Path, workflow_id: str, job: dict[str, Any], workflow: dict[str, Any], log: Any = None) -> None:
    """Persist the exact workflow sent to ComfyUI for audit/debugging."""
    try:
        project_dir = output_dir.parent if output_dir.name == "outputs" else output_dir
        audit_dir = project_dir / "workflow"
        audit_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        safe_job = str(job.get("job_id") or job.get("shot_id") or "job").replace("/", "_")
        path = audit_dir / f"{ts}_{workflow_id}_{safe_job}.json"
        envelope = {
            "schema": "kinodel.submitted_workflow.v1",
            "provider": job.get("provider"),
            "workflow_id": workflow_id,
            "job_id": job.get("job_id"),
            "shot_id": job.get("shot_id"),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "workflow": workflow,
        }
        path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        job["submitted_workflow_path"] = str(path)
        if log:
            log(f"saved submitted workflow -> {path}")
    except Exception as exc:
        if log:
            log(f"WARN could not save submitted workflow: {exc}")


def run_comfy_workflow_job(job: dict[str, Any], output_dir: Path, output_destination: Any, log: Any = None) -> dict[str, Any]:
    spec = require_workflow(job.get("provider"), job.get("kind"))
    payload = job.get("payload", {}) or {}
    params = payload.get("params", {}) or {}
    workflow_path = render_root() / spec.workflow_path
    schema_path = render_root() / spec.schema_path
    timeout = int(params.get("timeout", spec.default_timeout_s))
    host = str(params.get("comfyui_host") or os.environ.get("COMFYUI_HOST") or "") or None

    mods = _load_comfy_modules()
    with workflow_path.open(encoding="utf-8") as f:
        workflow = mods["unwrap_workflow"](json.load(f))
    schema = mods["load_schema"](str(schema_path), workflow)
    workflow_args = build_workflow_args(job, spec)
    workflow, warnings = mods["inject_params"](workflow, schema, workflow_args)
    _save_submitted_workflow(output_dir, spec.workflow_id, job, workflow, log)
    if log:
        log(f"submit comfyui workflow={spec.workflow_id} job_id={job.get('job_id')} timeout={timeout}s")
        for warning in warnings:
            log(f"WARN comfyui {spec.workflow_id}: {warning}")

    runner = mods["ComfyRunner"](
        host=host or mods["DEFAULT_LOCAL_HOST"],
        api_key=mods["resolve_api_key"](params.get("comfyui_api_key")),
        partner_key=params.get("comfyui_partner_key"),
    )
    ok, info = runner.check_server()
    if not ok:
        raise RuntimeError(f"Cannot reach ComfyUI server at {runner.host}: {info}")
    submit_resp = runner.submit(workflow)
    if "_http_error" in submit_resp:
        raise RuntimeError(f"ComfyUI submission HTTP error: {submit_resp}")
    if submit_resp.get("error") or submit_resp.get("node_errors"):
        raise RuntimeError(f"ComfyUI workflow validation failed: {submit_resp}")
    prompt_id = submit_resp.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"No ComfyUI prompt_id in submit response: {submit_resp}")
    job["request_id"] = prompt_id
    job["workflow_id"] = spec.workflow_id
    job["provider"] = job.get("provider") or f"local-comfyui:{spec.workflow_id}"
    if log:
        queue_number = submit_resp.get("number")
        suffix = f" queue_number={queue_number}" if queue_number is not None else ""
        log(f"comfyui prompt_id={prompt_id} workflow={spec.workflow_id}{suffix}")
    wait_result = runner.poll_status(prompt_id, timeout=timeout)
    if wait_result.get("status") != "success":
        raise RuntimeError(f"ComfyUI workflow did not complete prompt_id={prompt_id}: {wait_result}")
    outputs = wait_result.get("outputs") or runner.get_outputs(prompt_id)
    downloaded = mods["download_outputs"](
        runner,
        outputs,
        output_dir,
        preserve_subfolder=False,
        overwrite=True,
    )
    selected = _preferred_outputs(downloaded, spec)
    if not selected:
        raise RuntimeError(f"ComfyUI {spec.workflow_id} produced no {spec.preferred_media_type} outputs: {downloaded}")
    out = selected[0]
    ext = Path(out.get("file", "")).suffix.lstrip(".") or spec.default_extension
    dest = output_destination(output_dir, job, ext)
    _copy_or_keep_output(out, dest)
    url = _view_url(out.get("filename") or dest.name, out.get("source_type") or "output", out.get("subfolder") or "", runner.host)
    job["status"] = "done"
    job["provider"] = job.get("provider") or f"local-comfyui:{spec.workflow_id}"
    job["workflow_id"] = spec.workflow_id
    job["request_id"] = prompt_id
    job["output_path"] = str(dest)
    job["output_url"] = url or str(dest)
    if log:
        log(f"done comfyui workflow={spec.workflow_id} -> {dest}")
    return job
