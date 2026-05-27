#!/usr/bin/env python3
"""
Kinodel generic provider-backed background render worker.

Usage: python3 render_worker.py [--request-file path/to/render_requests.json --stage images|videos]

1. Reads render_prompt temporary requests plus optional brief/defaults
2. Normalizes requests into provider-neutral jobs internally
3. Dispatches to provider adapters (fal.ai, local ComfyUI workflows)
4. Polls/downloads outputs and writes a compact result JSON
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from providers.comfyui_provider import run_comfy_workflow_job
from providers.fal_provider import load_fal_key, run_fal_image_job, run_fal_video_job
from providers.registry import clamp_concurrency_for_jobs, is_comfyui_provider as registry_is_comfyui_provider, require_workflow

FAL_KEY = load_fal_key()


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)


def _deep_merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge_dicts(out[key], value)
        else:
            out[key] = value
    return out


def _project_brief_defaults_for_request(path: Path) -> dict[str, Any]:
    """Load sibling brief.json when a project request artifact is rendered directly.

    Render workers receive explicit request files, but Kinodel project-local
    requests intentionally keep provider-neutral defaults. This bridge makes
    brief.json the durable source for dimensions/provider/duration without
    asking planner agents to duplicate every low-level provider field.
    """
    brief_path = path.parent / "brief.json"
    if not brief_path.exists():
        return {}
    try:
        data = json.loads(brief_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log(f"WARN could not read sibling brief defaults {brief_path}: {exc}")
        return {}
    return data if isinstance(data, dict) else {}


def load_request_bundle(path: Path) -> tuple[list[dict], dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data, _project_brief_defaults_for_request(path)
    if isinstance(data, dict) and isinstance(data.get("jobs"), list):
        brief_defaults = _project_brief_defaults_for_request(path)
        inline_defaults = data.get("defaults") or data.get("brief") or {}
        if not isinstance(inline_defaults, dict):
            inline_defaults = {}
        defaults = _deep_merge_dicts(brief_defaults, inline_defaults)
        return data["jobs"], defaults
    raise ValueError("request file must be a job list or an object with jobs[]")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_request_file(path: Path) -> list[dict]:
    jobs, _defaults = load_request_bundle(path)
    return jobs


def save_result_file(path: Path, jobs: list[dict], summary: dict, defaults: dict[str, Any] | None = None) -> None:
    payload = {"summary": summary, "jobs": jobs}
    if defaults:
        payload["defaults"] = defaults
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_existing_result_jobs(path: Path | None) -> list[dict[str, Any]]:
    """Load prior worker jobs so reruns can resume instead of redoing successes."""
    if path is None or not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log(f"WARN could not read previous result file for resume: {path}: {exc}")
        return []
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list):
        return []
    return [j for j in jobs if isinstance(j, dict)]


def job_resume_keys(job: dict[str, Any]) -> list[tuple[str, str]]:
    """Stable identities for matching request jobs to prior result jobs."""
    keys: list[tuple[str, str]] = []
    for field in ("job_id", "shot_id", "output_name"):
        value = job.get(field)
        if isinstance(value, str) and value:
            keys.append((field, value))
    output_path = job.get("output_path")
    if isinstance(output_path, str) and output_path:
        keys.append(("output_path_name", Path(output_path).name))
    return keys


def completed_prior_job(job: dict[str, Any]) -> bool:
    if job.get("status") != "done":
        return False
    output_path = job.get("output_path")
    output_url = job.get("output_url")
    # Prefer verifying local files when present. Some providers may only return
    # a durable URL, so a URL-only completed job is also resumable.
    if isinstance(output_path, str) and output_path:
        return Path(output_path).exists()
    return isinstance(output_url, str) and output_url.startswith(("http://", "https://"))


def apply_resume_state(jobs: list[dict[str, Any]], previous_jobs: list[dict[str, Any]]) -> int:
    """Carry forward completed jobs from a previous result file.

    Failed/missing jobs intentionally remain pending so a rerun continues from
    the failed point instead of rendering the whole batch again.
    """
    previous_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for previous in previous_jobs:
        if not completed_prior_job(previous):
            continue
        for key in job_resume_keys(previous):
            previous_by_key.setdefault(key, previous)

    resumed = 0
    for job in jobs:
        prior = None
        for key in job_resume_keys(job):
            prior = previous_by_key.get(key)
            if prior:
                break
        if not prior:
            continue
        # Preserve current request metadata, but carry terminal output fields
        # forward so downstream result manifests still contain compact refs.
        for field in ("status", "workflow_id", "request_id", "output_path", "output_url", "error"):
            if field in prior:
                if field == "error" and prior.get("status") == "done":
                    continue
                job[field] = prior[field]
        job["status"] = "done"
        resumed += 1
    return resumed


def append_event(path: Path | None, event: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    event.setdefault("created_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


IMAGE_QUALITY_LONG_SIDE = {"1K": 1024, "1.5K": 1536, "2K": 2048}
VIDEO_QUALITY_BASE = {"480P": 480, "720P": 720, "1080P": 1080}
ASPECT_RATIO_ALIASES = {
    "portrait": "9:16",
    "vertical": "9:16",
    "reels": "9:16",
    "tiktok": "9:16",
    "shorts": "9:16",
    "landscape": "16:9",
    "youtube": "16:9",
    "wide": "16:9",
    "square": "1:1",
}


def _round_to_multiple(value: float, multiple: int = 8) -> int:
    return max(multiple, int(round(value / multiple) * multiple))


def parse_aspect_ratio(value: Any) -> tuple[int, int]:
    text = str(value or "1:1").strip().lower()
    text = ASPECT_RATIO_ALIASES.get(text, text)
    if ":" not in text:
        return (1, 1)
    left, right = text.split(":", 1)
    try:
        w = int(float(left))
        h = int(float(right))
    except ValueError:
        return (1, 1)
    if w <= 0 or h <= 0:
        return (1, 1)
    return (w, h)


def image_size_for_quality(aspect_ratio: Any, quality: Any = "1K") -> dict[str, int]:
    """Kinodel image quality: 1K/1.5K/2K means long side in pixels."""
    w_ratio, h_ratio = parse_aspect_ratio(aspect_ratio)
    long_side = IMAGE_QUALITY_LONG_SIDE.get(str(quality or "1K").upper(), 1024)
    if w_ratio >= h_ratio:
        return {"width": long_side, "height": _round_to_multiple(long_side * h_ratio / w_ratio)}
    return {"width": _round_to_multiple(long_side * w_ratio / h_ratio), "height": long_side}


def video_size_for_quality(aspect_ratio: Any, quality: Any = "480p") -> dict[str, int]:
    """Kinodel video quality: 480p/720p/1080p means the short side in pixels."""
    w_ratio, h_ratio = parse_aspect_ratio(aspect_ratio)
    short_side = VIDEO_QUALITY_BASE.get(str(quality or "480p").upper(), 480)
    if w_ratio > h_ratio:
        return {"width": _round_to_multiple(short_side * w_ratio / h_ratio, 2), "height": short_side}
    if h_ratio > w_ratio:
        return {"width": short_side, "height": _round_to_multiple(short_side * h_ratio / w_ratio, 2)}
    return {"width": short_side, "height": short_side}


def _size_from_fields(*sources: dict[str, Any], keys: tuple[str, str] = ("width", "height")) -> dict[str, int] | None:
    width_key, height_key = keys
    for source in sources:
        if not isinstance(source, dict):
            continue
        size_keys = ("video_size", "size") if width_key.startswith("video_") else ("image_size", "size")
        for size_key in size_keys:
            size = source.get(size_key)
            if isinstance(size, dict) and size.get("width") and size.get("height"):
                return {"width": int(size["width"]), "height": int(size["height"])}
        width = source.get(width_key) or source.get("width")
        height = source.get(height_key) or source.get("height")
        if width and height:
            return {"width": int(width), "height": int(height)}
    return None


def brief_defaults(raw: dict[str, Any]) -> dict[str, Any]:
    video = raw.get("video") if isinstance(raw.get("video"), dict) else {}
    image = raw.get("image") if isinstance(raw.get("image"), dict) else {}
    audio = raw.get("audio") if isinstance(raw.get("audio"), dict) else {}
    aspect_ratio = raw.get("aspect_ratio") or image.get("aspect_ratio") or video.get("aspect_ratio") or "1:1"
    image_resolution = raw.get("image_resolution") or image.get("resolution") or "1K"
    video_resolution = raw.get("video_resolution") or video.get("resolution") or raw.get("resolution") or "480p"
    image_size = _size_from_fields(raw, image) or image_size_for_quality(aspect_ratio, image_resolution)
    video_size = _size_from_fields(raw, video, keys=("video_width", "video_height")) or video_size_for_quality(aspect_ratio, video_resolution)
    return {
        "aspect_ratio": aspect_ratio,
        "image_size": image_size,
        "video_size": video_size,
        "image_resolution": image_resolution,
        "video_resolution": video_resolution,
        "video_duration": raw.get("video_duration") or raw.get("seconds_per_shot") or video.get("seconds_per_shot") or video.get("duration") or raw.get("duration") or "4s",
        "enable_audio": bool(raw.get("enable_audio", video.get("enable_audio", audio.get("enable_audio", False)))),
    }


def provider_family_defaults(raw_defaults: dict[str, Any], kind: str | None) -> str:
    """Resolve compact brief provider choices into concrete worker provider IDs."""
    nested_defaults = raw_defaults.get("defaults") if isinstance(raw_defaults.get("defaults"), dict) else {}

    def choice(*keys: str) -> Any:
        for key in keys:
            if raw_defaults.get(key):
                return raw_defaults.get(key)
            if nested_defaults.get(key):
                return nested_defaults.get(key)
        return None

    image_choice = choice("provider_image", "image_provider", "provider", "render_provider")
    edit_choice = choice("provider_edit", "edit_provider") or image_choice
    video_choice = choice("provider_video", "video_provider", "provider", "render_provider") or image_choice
    flf2v_choice = choice("provider_flf2v", "flf2v_provider") or video_choice

    def concrete(choice: Any, *, fal_default: str, comfyui_default: str) -> str:
        cid = str(choice or "").strip().lower().replace(" ", "_")
        if cid in {"fal", "fal.ai", "fal_ai"}:
            return fal_default
        if cid in {"comfyui", "local-comfyui", "local_comfyui"}:
            return comfyui_default
        return str(choice) if choice else comfyui_default

    if kind == "t2i":
        return concrete(image_choice, fal_default="fal:hidream_o1", comfyui_default="local-comfyui:img2img_klein")
    if kind == "i2i":
        return concrete(edit_choice, fal_default="fal:hidream_o1_edit", comfyui_default="local-comfyui:img2img_klein")
    if kind == "i2v":
        return concrete(video_choice, fal_default="fal:veo31_lite_i2v", comfyui_default="local-comfyui:img2vid_wan_lora")
    if kind == "flf2v":
        # No production ComfyUI first-last-frame workflow is registered yet; keep fal explicit.
        return concrete(flf2v_choice, fal_default="fal:veo31_lite_flf2v", comfyui_default="fal:veo31_lite_flf2v")
    return "local-comfyui:img2img_klein"


def normalize_job(job: dict, index: int, defaults: dict[str, Any] | None = None) -> dict:
    job = dict(job)
    kind = job.get("kind")
    render_prompt = job.get("render_prompt") or job.get("final_prompt")
    input_media = job.get("input_media") or job.get("refs") or job.get("references") or []
    raw_defaults = dict(defaults) if defaults else {}
    defaults = brief_defaults(defaults or {})
    if isinstance(input_media, str):
        input_media = [input_media]
    if render_prompt:
        payload = dict(job.get("payload") or {})
        payload.setdefault("prompt", render_prompt)
        if input_media:
            payload.setdefault("references", input_media)
            if kind == "i2i":
                payload.setdefault("image_urls", input_media)
            if kind == "i2v":
                payload.setdefault("image_url", input_media[0])
            if kind == "flf2v":
                payload.setdefault("image_urls", input_media)
                if len(input_media) >= 1:
                    payload.setdefault("first_frame_url", input_media[0])
                if len(input_media) >= 2:
                    payload.setdefault("last_frame_url", input_media[1])
        payload.setdefault("params", {})
        params = payload["params"]
        params.setdefault("aspect_ratio", "auto" if kind in ("i2v", "flf2v") else defaults["aspect_ratio"])
        if kind in ("t2i", "i2i"):
            if defaults.get("image_size"):
                params.setdefault("image_size", defaults["image_size"])
            params.setdefault("resolution", defaults["image_resolution"])
            params.setdefault("output_format", "png")
            params.setdefault("num_images", 1)
        if kind in ("i2v", "flf2v"):
            params.setdefault("duration", "8s" if kind == "flf2v" else defaults["video_duration"])
            params.setdefault("resolution", defaults["video_resolution"])
            video_size = defaults.get("video_size")
            if isinstance(video_size, dict):
                params.setdefault("video_width", video_size.get("width"))
                params.setdefault("video_height", video_size.get("height"))
            params.setdefault("enable_audio", defaults["enable_audio"])
        job["payload"] = payload
    # Allow producer/brief defaults to override provider selection. Bare "fal" and
    # "comfyui" choices are expanded to concrete provider IDs here. Default is ComfyUI.
    if kind == "t2i":
        job.setdefault("provider", provider_family_defaults(raw_defaults, kind))
        job.setdefault("stage", "main_frame")
    elif kind == "i2i":
        job.setdefault("provider", provider_family_defaults(raw_defaults, kind))
        job.setdefault("stage", "story_frames")
    elif kind == "i2v":
        job.setdefault("provider", provider_family_defaults(raw_defaults, kind))
        job.setdefault("stage", "shot_videos")
    elif kind == "flf2v":
        job.setdefault("provider", provider_family_defaults(raw_defaults, kind))
        job.setdefault("stage", "shot_videos")
    output_name = job.get("output_name")
    output_stem = Path(output_name).stem if isinstance(output_name, str) and output_name else None
    shot_id = job.get("shot_id") or output_stem or job.get("stage") or kind or "job"
    job.setdefault("job_id", f"{shot_id}_{index + 1}")
    job.setdefault("status", "pending")
    return job


def output_destination(output_dir: Path, job: dict, default_ext: str) -> Path:
    output_name = job.get("output_name")
    if isinstance(output_name, str) and output_name:
        name = Path(output_name).name
        if Path(name).suffix:
            return output_dir / name
        return output_dir / f"{name}.{default_ext}"
    return output_dir / f"{job['job_id']}.{default_ext}"


def is_public_http_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def is_comfyui_provider(provider: Any) -> bool:
    return registry_is_comfyui_provider(provider)


def validate_job(job: dict) -> None:
    kind = job.get("kind")
    provider = job.get("provider")
    payload = job.get("payload", {})
    prompt = payload.get("prompt") or payload.get("action_prompt")
    if not prompt:
        raise RuntimeError(f"job missing prompt: {job.get('job_id')}")
    refs = payload.get("image_urls") or payload.get("references") or []
    if isinstance(refs, str):
        refs = [refs]
    if kind == "t2i":
        if is_comfyui_provider(provider):
            require_workflow(provider, kind)
        return
    if kind == "i2i":
        # local-comfyui/img2img_klein is a hybrid txt2img+img2img workflow:
        # no refs => txt2img, 1-4 refs => img2img/reference edit.
        if is_comfyui_provider(provider):
            require_workflow(provider, kind)
        if is_comfyui_provider(provider) and not refs:
            return
        if not refs:
            raise RuntimeError(f"i2i job missing input_media/image_urls: {job.get('job_id')}")
        bad = [ref for ref in refs if not is_public_http_url(ref)]
        if bad:
            raise RuntimeError(f"i2i job requires public http(s) input_media URLs: {bad}")
    elif kind == "i2v":
        if is_comfyui_provider(provider):
            require_workflow(provider, kind)
        image_url = payload.get("reference_image_url") or payload.get("image_url") or (refs[0] if refs else None)
        if not is_public_http_url(image_url):
            raise RuntimeError(f"i2v job requires one public http(s) image URL: {job.get('job_id')}")
    elif kind == "flf2v":
        first_frame_url = payload.get("first_frame_url") or (refs[0] if len(refs) >= 1 else None)
        last_frame_url = payload.get("last_frame_url") or (refs[1] if len(refs) >= 2 else None)
        if not is_public_http_url(first_frame_url) or not is_public_http_url(last_frame_url):
            raise RuntimeError(f"flf2v job requires exactly two public http(s) frame URLs: {job.get('job_id')}")
    else:
        raise RuntimeError(f"unsupported kind: {kind}")


def process_image_job(job: dict, output_dir: Path) -> dict:
    provider = job["provider"]
    if is_comfyui_provider(provider):
        return run_comfy_workflow_job(job, output_dir, output_destination, log)
    return run_fal_image_job(job, output_dir, output_destination, log)


def process_video_job(job: dict, output_dir: Path) -> dict:
    provider = job["provider"]
    if is_comfyui_provider(provider):
        return run_comfy_workflow_job(job, output_dir, output_destination, log)
    return run_fal_video_job(job, output_dir, output_destination, log)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request-file", required=True, help="Temporary render request JSON file")
    ap.add_argument("--result-file", help="Temporary render result JSON file")
    ap.add_argument("--output-dir", default=".", help="Directory for downloaded outputs")
    ap.add_argument("--stage", choices=("images", "videos"), required=True)
    ap.add_argument("--events-file", help="Optional JSONL event stream")
    ap.add_argument("--image-concurrency", type=int, default=6)
    ap.add_argument("--video-concurrency", type=int, default=4)
    args = ap.parse_args()

    # FAL_KEY is required only for fal.ai jobs. Local ComfyUI image jobs run
    # through the ComfyUI REST API and can be used without fal credentials.

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    request_path = Path(args.request_file)
    result_path = Path(args.result_file) if args.result_file else None
    events_path = Path(args.events_file) if args.events_file else None
    request_sha256 = file_sha256(request_path)
    defaults: dict[str, Any] = {}
    jobs, defaults = load_request_bundle(request_path)
    if result_path is None:
        result_path = request_path.with_name(request_path.stem + ".results.json")
    jobs = [normalize_job(j, i, defaults) for i, j in enumerate(jobs)]
    resumed = apply_resume_state(jobs, load_existing_result_jobs(result_path))
    if resumed:
        log(f"resume: carried forward {resumed} completed job(s) from {result_path}")
    expected_kinds = {"t2i", "i2i"} if args.stage == "images" else {"i2v", "flf2v"}
    pending = [j for j in jobs if j.get("status") in ("pending", None, "failed") and j.get("kind") in expected_kinds]
    for job in pending:
        if job.get("status") == "failed":
            job["status"] = "pending"
            job.pop("error", None)
    if not FAL_KEY and any(not is_comfyui_provider(j.get("provider")) for j in pending):
        log("ERROR: FAL_KEY not set for fal.ai render jobs")
        return 2

    if not pending:
        summary = {
            "event_type": "render_batch_terminal",
            "batch_id": f"render_{args.stage}",
            "status": "no_pending_jobs",
            "done": len([j for j in jobs if j.get("status") == "done"]),
            "failed": len([j for j in jobs if j.get("status") == "failed"]),
            "outputs": [{"job_id": j["job_id"], "kind": j["kind"], "output_path": j.get("output_path"), "output_url": j.get("output_url")} for j in jobs if j.get("status") == "done"],
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "request_sha256": request_sha256,
        }
        save_result_file(result_path, jobs, summary, defaults)
        append_event(events_path, summary)
        log(f"no pending {args.stage} jobs")
        return 0

    append_event(events_path, {
        "event_type": "render_batch_started",
        "stage": args.stage,
        "pending": len(pending),
        "request_file": str(request_path),
        "result_file": str(result_path),
    })

    preflight_errors = []
    for job in pending:
        try:
            validate_job(job)
        except Exception as exc:
            job["status"] = "failed"
            job["error"] = str(exc)
            preflight_errors.append({"job_id": job.get("job_id"), "error": str(exc)})
    if preflight_errors:
        summary = {
            "event_type": "render_batch_terminal",
            "batch_id": f"render_{args.stage}",
            "status": "failed_preflight",
            "done": len([j for j in jobs if j.get("status") == "done"]),
            "failed": len([j for j in jobs if j.get("status") == "failed"]),
            "outputs": [{"job_id": j["job_id"], "kind": j["kind"], "output_path": j.get("output_path"), "output_url": j.get("output_url")} for j in jobs if j.get("status") == "done"],
            "errors": preflight_errors,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "request_sha256": request_sha256,
        }
        save_result_file(result_path, jobs, summary, defaults)
        append_event(events_path, summary)
        log(f"stage={args.stage} failed preflight")
        return 1

    requested_workers = args.image_concurrency if args.stage == "images" else args.video_concurrency
    max_workers = clamp_concurrency_for_jobs(pending, requested_workers)
    max_workers = max(1, min(int(max_workers or 1), len(pending)))
    log(f"stage={args.stage} pending={len(pending)} concurrency={max_workers}")

    def run_one(job: dict) -> dict:
        job_id = job["job_id"]
        try:
            if args.stage == "images":
                job = process_image_job(job, output_dir)
            else:
                job = process_video_job(job, output_dir)
            append_event(events_path, {
                "event_type": "render_job_done",
                "stage": args.stage,
                "job_id": job_id,
                "kind": job.get("kind"),
                "output_path": job.get("output_path"),
                "output_url": job.get("output_url"),
            })
        except Exception as exc:
            log(f"ERROR job {job_id}: {exc}")
            job["status"] = "failed"
            job["error"] = str(exc)
            append_event(events_path, {
                "event_type": "render_job_failed",
                "stage": args.stage,
                "job_id": job_id,
                "kind": job.get("kind"),
                "error": str(exc),
            })
        return job

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(run_one, job) for job in pending]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    summary = {
        "event_type": "render_batch_terminal",
        "batch_id": f"fal_{args.stage}",
        "status": "done",
        "done": len([j for j in jobs if j.get("status") == "done"]),
        "failed": len([j for j in jobs if j.get("status") == "failed"]),
        "outputs": [{"job_id": j["job_id"], "kind": j["kind"], "output_path": j.get("output_path"), "output_url": j.get("output_url")} for j in jobs if j.get("status") == "done"],
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "request_sha256": request_sha256,
    }
    save_result_file(result_path, jobs, summary, defaults)
    append_event(events_path, summary)
    failed_count = summary["failed"]
    if failed_count:
        log(f"stage={args.stage} completed with failed={failed_count}")
        return 1
    log(f"stage={args.stage} done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())