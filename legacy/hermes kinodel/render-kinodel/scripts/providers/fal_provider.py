from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests

FAL_QUEUE = "https://queue.fal.run"
ENDPOINTS = {
    "fal:hidream_o1": "fal-ai/hidream-o1-image",
    "fal:hidream_o1_edit": "fal-ai/hidream-o1-image/edit",
    "fal:nano_banana_2": "fal-ai/nano-banana-2",
    "fal:nano_banana_pro": "fal-ai/nano-banana-2",
    "fal:nano_banana_2_edit": "fal-ai/nano-banana-2/edit",
    "fal:veo31_lite_i2v": "fal-ai/veo3.1/lite/image-to-video",
    "fal:veo31_lite_flf2v": "fal-ai/veo3.1/lite/first-last-frame-to-video",
}


def load_fal_key() -> str | None:
    key = os.environ.get("FAL_KEY")
    if key:
        return key
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("FAL_KEY="):
                return line.split("=", 1)[1].strip().strip('"')
    return None


def headers() -> dict[str, str]:
    key = load_fal_key()
    return {"Authorization": f"Key {key}", "Content-Type": "application/json"}


def hidream_image_size(params: dict) -> Any:
    if params.get("image_size"):
        return params["image_size"]
    resolution = str(params.get("resolution", "1K")).upper()
    aspect_ratio = str(params.get("aspect_ratio", "1:1"))
    long_side = 2048 if resolution == "2K" else 1024
    if aspect_ratio in ("16:9", "landscape"):
        return {"width": long_side, "height": round(long_side * 9 / 16)}
    if aspect_ratio in ("1:1", "square"):
        return {"width": long_side, "height": long_side}
    return {"width": round(long_side * 9 / 16), "height": long_side}


def fal_post(endpoint: str, body: dict) -> dict:
    r = requests.post(f"{FAL_QUEUE}/{endpoint}", headers=headers(), json=body, timeout=30)
    if r.status_code == 422:
        raise RuntimeError(f"422: {r.text}")
    r.raise_for_status()
    return r.json()


def fal_get(url: str) -> dict:
    r = requests.get(url, headers=headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def poll_fal(status_url: str, result_url: str, *, timeout: int = 600, interval: int = 5, max_interval: int = 30, log: Any = None) -> dict:
    deadline = time.time() + timeout
    last_status = ""
    current_interval = interval
    while time.time() < deadline:
        st = fal_get(status_url)
        status = st.get("status", "")
        if status != last_status:
            if log:
                log(f"poll status={status}")
            last_status = status
        if status == "COMPLETED":
            return fal_get(result_url)
        if status in ("FAILED", "CANCELLED", "ERROR"):
            raise RuntimeError(f"job failed: {st}")
        time.sleep(current_interval)
        current_interval = min(max_interval, max(current_interval + 2, int(current_interval * 1.5)))
    raise RuntimeError(f"poll timeout (last={last_status})")


def download(url: str, dest: Path) -> None:
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)


def save_submitted_payload(output_dir: Path, provider: str, endpoint: str, job: dict, body: dict, log: Any = None) -> None:
    """Persist the exact fal payload sent to the queue for audit/debugging."""
    try:
        project_dir = output_dir.parent if output_dir.name == "outputs" else output_dir
        audit_dir = project_dir / "workflow"
        audit_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        safe_provider = provider.replace(":", "_").replace("/", "_")
        safe_job = str(job.get("job_id") or job.get("shot_id") or "job").replace("/", "_")
        path = audit_dir / f"{ts}_{safe_provider}_{safe_job}.json"
        envelope = {
            "schema": "kinodel.submitted_workflow.v1",
            "provider": provider,
            "endpoint": endpoint,
            "job_id": job.get("job_id"),
            "shot_id": job.get("shot_id"),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "payload": body,
        }
        path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        job["submitted_workflow_path"] = str(path)
        if log:
            log(f"saved submitted payload -> {path}")
    except Exception as exc:
        if log:
            log(f"WARN could not save submitted payload: {exc}")


def run_fal_image_job(job: dict, output_dir: Path, output_destination: Any, log: Any = None) -> dict:
    provider = job["provider"]
    payload = job.get("payload", {})
    params = payload.get("params", {})
    prompt = payload.get("prompt") or payload.get("action_prompt")
    if not prompt:
        raise RuntimeError(f"image job missing prompt: {job['job_id']}")
    if provider in ("fal:hidream_o1", "fal:hidream_o1_edit"):
        body = {
            "prompt": prompt,
            "image_size": hidream_image_size(params),
            "num_inference_steps": params.get("num_inference_steps", 50),
            "guidance_scale": params.get("guidance_scale", 5),
            "num_images": params.get("num_images", 1),
            "output_format": params.get("output_format", "png"),
            "enable_safety_checker": params.get("enable_safety_checker", False),
        }
        if "sync_mode" in params:
            body["sync_mode"] = params["sync_mode"]
        if "keep_original_aspect" in params:
            body["keep_original_aspect"] = params["keep_original_aspect"]
    else:
        body = {
            "prompt": prompt,
            "output_format": params.get("output_format", "png"),
            "safety_tolerance": str(params.get("safety_tolerance", "4")),
            "num_images": params.get("num_images", 1),
        }
        image_size = params.get("image_size") or hidream_image_size(params)
        if image_size:
            body["image_size"] = image_size
    if provider in ("fal:nano_banana_2_edit", "fal:hidream_o1_edit"):
        image_urls = payload.get("image_urls") or payload.get("references")
        if isinstance(image_urls, str):
            image_urls = [image_urls]
        if not image_urls:
            raise RuntimeError(f"edit job missing image_urls: {job['job_id']}")
        if provider == "fal:hidream_o1_edit":
            body["reference_image_urls"] = image_urls
        else:
            body["image_urls"] = image_urls
    if "seed" in params and params["seed"] is not None:
        body["seed"] = params["seed"]
    endpoint = ENDPOINTS.get(provider)
    if not endpoint:
        raise RuntimeError(f"unsupported fal provider: {provider}")
    save_submitted_payload(output_dir, provider, endpoint, job, body, log)
    if log:
        log(f"submit image job_id={job['job_id']} endpoint={endpoint}")
    resp = fal_post(endpoint, body)
    job["request_id"] = resp.get("request_id")
    job["status_url"] = resp.get("status_url") or f"{FAL_QUEUE}/{endpoint}/requests/{resp['request_id']}/status"
    job["response_url"] = resp.get("response_url") or f"{FAL_QUEUE}/{endpoint}/requests/{resp['request_id']}"

    result = poll_fal(job["status_url"], job["response_url"], log=log)
    images = result.get("images", [])
    if images:
        url = images[0].get("url")
        ext = images[0].get("content_type", "image/png").split("/")[-1] or "png"
    else:
        url = result.get("image", {}).get("url")
        ext = "png"
    if not url:
        raise RuntimeError(f"No image url in result: {result}")
    dest = output_destination(output_dir, job, ext)
    download(url, dest)
    job["status"] = "done"
    job["output_path"] = str(dest)
    job["output_url"] = url
    if log:
        log(f"done image -> {dest}")
    return job


def run_fal_video_job(job: dict, output_dir: Path, output_destination: Any, log: Any = None) -> dict:
    provider = job["provider"]
    payload = job.get("payload", {})
    params = payload.get("params", {})
    image_urls = payload.get("image_urls") or []
    references = payload.get("references") or []
    if isinstance(image_urls, str):
        image_urls = [image_urls]
    if isinstance(references, str):
        references = [references]
    image_url = payload.get("reference_image_url") or payload.get("image_url") or (image_urls[0] if image_urls else None) or (references[0] if references else None)
    first_frame_url = payload.get("first_frame_url") or (image_urls[0] if len(image_urls) >= 1 else None) or (references[0] if len(references) >= 1 else None)
    last_frame_url = payload.get("last_frame_url") or (image_urls[1] if len(image_urls) >= 2 else None) or (references[1] if len(references) >= 2 else None)
    if provider == "fal:veo31_lite_flf2v" and (not first_frame_url or not last_frame_url):
        raise RuntimeError(f"flf2v job missing first_frame_url/last_frame_url: {job['job_id']}")
    if provider != "fal:veo31_lite_flf2v" and not image_url:
        raise RuntimeError(f"video job missing image_url: {job['job_id']}")
    duration = params.get("duration", "8s" if provider == "fal:veo31_lite_flf2v" else "4s")
    if isinstance(duration, (int, float)):
        duration = f"{duration}s"
    endpoint = ENDPOINTS.get(provider)
    if not endpoint:
        raise RuntimeError(f"unsupported fal provider: {provider}")
    body = {
        "prompt": payload["prompt"],
        "aspect_ratio": params.get("aspect_ratio", "auto"),
        "duration": duration,
        "resolution": params.get("resolution", "480p"),
        "generate_audio": params.get("generate_audio", params.get("enable_audio", False)),
        "safety_tolerance": str(params.get("safety_tolerance", "4")),
    }
    if provider == "fal:veo31_lite_flf2v":
        body["first_frame_url"] = first_frame_url
        body["last_frame_url"] = last_frame_url
    else:
        body["image_url"] = image_url
    save_submitted_payload(output_dir, provider, endpoint, job, body, log)
    if log:
        log(f"submit video job_id={job['job_id']} endpoint={endpoint}")
    resp = fal_post(endpoint, body)
    job["request_id"] = resp.get("request_id")
    job["status_url"] = resp.get("status_url") or f"{FAL_QUEUE}/{endpoint}/requests/{resp['request_id']}/status"
    job["response_url"] = resp.get("response_url") or f"{FAL_QUEUE}/{endpoint}/requests/{resp['request_id']}"
    result = poll_fal(job["status_url"], job["response_url"], timeout=900, interval=5, log=log)
    video = result.get("video") or {}
    url = video.get("url")
    if not url:
        raise RuntimeError(f"No video.url in result: {result}")
    dest = output_destination(output_dir, job, "mp4")
    download(url, dest)
    job["status"] = "done"
    job["output_path"] = str(dest)
    job["output_url"] = url
    if log:
        log(f"done video -> {dest}")
    return job
