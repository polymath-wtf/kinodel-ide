from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WorkflowSpec:
    workflow_id: str
    provider: str
    adapter: str
    output_kind: str
    accepted_job_kinds: tuple[str, ...]
    workflow_path: str
    schema_path: str
    default_timeout_s: int
    concurrency_class: str
    max_concurrency: int
    preferred_media_type: str
    default_extension: str


WORKFLOWS: dict[str, WorkflowSpec] = {
    "img2img_klein": WorkflowSpec(
        workflow_id="img2img_klein",
        provider="local-comfyui",
        adapter="comfyui_workflow",
        output_kind="image",
        accepted_job_kinds=("t2i", "i2i"),
        workflow_path="workflows/img2img_klein.json",
        schema_path="workflows/img2img_klein.schema.json",
        default_timeout_s=900,
        concurrency_class="local_comfyui_image",
        max_concurrency=1,
        preferred_media_type="image",
        default_extension="png",
    ),
    "img2vid_wan_lora": WorkflowSpec(
        workflow_id="img2vid_wan_lora",
        provider="local-comfyui",
        adapter="comfyui_workflow",
        output_kind="video",
        accepted_job_kinds=("i2v",),
        workflow_path="workflows/img2vid_wan_lora.json",
        schema_path="workflows/img2vid_wan_lora.schema.json",
        default_timeout_s=1800,
        concurrency_class="local_comfyui_video",
        max_concurrency=1,
        preferred_media_type="video",
        default_extension="mp4",
    ),
}

ALIASES: dict[str, str] = {
    "comfyui:img2img_klein": "img2img_klein",
    "local-comfyui:img2img_klein": "img2img_klein",
    "comfyui/img2img_klein": "img2img_klein",
    "local-comfyui/img2img_klein": "img2img_klein",
    "comfyui:img2vid_wan_lora": "img2vid_wan_lora",
    "local-comfyui:img2vid_wan_lora": "img2vid_wan_lora",
    "comfyui/img2vid_wan_lora": "img2vid_wan_lora",
    "local-comfyui/img2vid_wan_lora": "img2vid_wan_lora",
}

LOCAL_COMFY_PREFIXES = ("comfyui", "local-comfyui")


def render_root() -> Path:
    return Path(__file__).resolve().parents[2]


def normalize_provider_id(provider: Any) -> str:
    return str(provider or "").strip().lower().replace(" ", "_")


def is_comfyui_provider(provider: Any) -> bool:
    pid = normalize_provider_id(provider)
    if not pid:
        return False
    return pid in {"comfyui", "local-comfyui"} or pid.startswith("comfyui:") or pid.startswith("local-comfyui:") or pid.startswith("comfyui/") or pid.startswith("local-comfyui/")


def resolve_workflow_id(provider: Any, kind: str | None = None) -> str | None:
    pid = normalize_provider_id(provider)
    if not pid:
        return None
    if pid in ALIASES:
        return ALIASES[pid]
    # Ergonomic bare local provider aliases are kind-aware.
    if pid in {"comfyui", "local-comfyui"}:
        if kind in ("i2v", "video"):
            return "img2vid_wan_lora"
        return "img2img_klein"
    # Allow direct workflow id for internal profiles.
    if pid in WORKFLOWS:
        return pid
    return None


def workflow_for_provider(provider: Any, kind: str | None = None) -> WorkflowSpec | None:
    workflow_id = resolve_workflow_id(provider, kind)
    if not workflow_id:
        return None
    return WORKFLOWS.get(workflow_id)


def require_workflow(provider: Any, kind: str | None = None) -> WorkflowSpec:
    spec = workflow_for_provider(provider, kind)
    if not spec:
        raise RuntimeError(f"unsupported ComfyUI workflow provider: {provider}")
    if kind and kind not in spec.accepted_job_kinds:
        raise RuntimeError(
            f"ComfyUI workflow {spec.workflow_id} does not accept kind={kind}; "
            f"accepted={list(spec.accepted_job_kinds)}"
        )
    return spec


def clamp_concurrency_for_jobs(jobs: list[dict[str, Any]], requested: int) -> int:
    """Clamp local ComfyUI batches to safe GPU concurrency.

    For mixed batches we clamp the whole executor. This is intentionally simple:
    one local GPU queue plus remote fal jobs in the same executor is rare, and
    correctness/reproducibility beats throughput for local ComfyUI.
    """
    max_workers = max(1, int(requested or 1))
    local_specs = [workflow_for_provider(j.get("provider"), j.get("kind")) for j in jobs if is_comfyui_provider(j.get("provider"))]
    local_limits = [s.max_concurrency for s in local_specs if s]
    if local_limits:
        max_workers = min(max_workers, min(local_limits))
    return max_workers
