#!/usr/bin/env python3
"""Scaffold a new Kinodel project with artifact-centric project-bound stubs.

Backward-compatible usage:
    python3 init_project.py <project_id> <brief_json>

Phase C optional flags:
    --pipeline-id cinematic.v1
    --layout-profile cinematic
    --pipeline-spec /path/to/pipeline_spec.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

BASE = Path.home() / "projects"
PIPELINE_ROOT = Path.home() / ".hermes" / "skills" / "kinodel" / "pipeline-kinodel"
PIPELINE_REGISTRY = PIPELINE_ROOT / "pipelines"
PIPELINE_SPEC_SCHEMA = "kinodel.pipeline_spec.v1"
PRODUCER_STATE_SCHEMA = "kinodel.producer_state.v1"
DEFAULT_PIPELINE_ID = "cinematic.v1"
DEFAULT_LAYOUT_PROFILE = "cinematic"
REQUIRED_BRIEF_FIELDS = (
    "user_vibe",
    "characters",
    "feature",
)

LAYOUT_PROFILES: dict[str, dict[str, Any]] = {
    "cinematic": {
        "status": "active",
        "pipeline_id": "cinematic.v1",
        "artifacts": {
            "story.json": {
                "schema": "kinodel.story.v1",
                "status": "pending",
                "hook": "",
                "story": "",
                "scene_count": 0,
                "shots": [],
            },
            "wardrobe_request.json": {
                "schema": "kinodel.render_requests.v1",
                "status": "pending",
                "stage": "main_frame",
                "jobs": [],
            },
            "storyboard_requests.json": {
                "schema": "kinodel.render_requests.v1",
                "status": "pending",
                "stage": "story_frames",
                "jobs": [],
            },
            "video_requests.json": {
                "schema": "kinodel.render_requests.v1",
                "status": "pending",
                "stage": "shot_videos",
                "jobs": [],
            },
        },
        "render_results": {
            "main_frame_result.json": "main_frame",
            "story_frames_result.json": "story_frames",
            "shot_videos_result.json": "shot_videos",
        },
    },
    "serial_season": {"status": "planned", "pipeline_id": "serial_season.v1"},
    "serial_episode": {"status": "planned", "pipeline_id": "serial_episode.v1"},
    "music_video": {"status": "planned", "pipeline_id": "music_video.v1"},
    "renovation_timelapse": {"status": "planned", "pipeline_id": "renovation_timelapse.v1"},
}

ACTIVE_PIPELINES = {"cinematic.v1": "cinematic"}
PLANNED_PIPELINES = {
    "serial_season.v1": "serial_season",
    "serial_episode.v1": "serial_episode",
    "music_video.v1": "music_video",
    "renovation_timelapse.v1": "renovation_timelapse",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    sys.exit(1)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"cannot parse {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"{path} is not a JSON object")
    return data


def resolve_layout_profile(pipeline_id: str, layout_profile: str | None) -> str:
    if pipeline_id in ACTIVE_PIPELINES:
        inferred = ACTIVE_PIPELINES[pipeline_id]
    elif pipeline_id in PLANNED_PIPELINES:
        fail(f"pipeline {pipeline_id!r} is planned/locked in Phase C and cannot initialize production projects")
    else:
        fail(f"unknown pipeline_id {pipeline_id!r}; only cinematic.v1 is active in Phase C")

    profile = layout_profile or inferred
    if profile not in LAYOUT_PROFILES:
        fail(f"unknown layout profile {profile!r}")
    if LAYOUT_PROFILES[profile].get("status") != "active":
        fail(f"layout profile {profile!r} is planned/locked in Phase C")
    if profile != inferred:
        fail(f"pipeline_id {pipeline_id!r} requires layout_profile {inferred!r}, got {profile!r}")
    return profile


def resolve_pipeline_spec(pipeline_id: str, explicit_spec: str | None = None) -> dict[str, Any]:
    path = Path(explicit_spec).expanduser().resolve() if explicit_spec else PIPELINE_REGISTRY / f"{pipeline_id}.json"
    if not path.exists():
        fail(f"missing pipeline spec {path}")
    spec = load_json(path)
    if spec.get("schema") != PIPELINE_SPEC_SCHEMA:
        fail(f"pipeline spec schema mismatch: {spec.get('schema')!r} != {PIPELINE_SPEC_SCHEMA!r}")
    if spec.get("pipeline_id") != pipeline_id:
        fail(f"pipeline spec pipeline_id mismatch: {spec.get('pipeline_id')!r} != {pipeline_id!r}")
    return spec


def pending_with_project(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    out.setdefault("project_id", project_id)
    return out


def has_brief_content(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return value is not None


def validate_brief_intake(brief: dict[str, Any]) -> None:
    """Fail closed if the approved minimal BriefGate was not persisted."""
    missing = [field for field in REQUIRED_BRIEF_FIELDS if not has_brief_content(brief.get(field))]
    if missing:
        fail(
            "brief_json missing approved minimal intake fields: "
            + ", ".join(missing)
            + ". Show the minimal BriefGate card and pass only user_vibe, characters, feature, and workflow defaults into brief.json."
        )


def normalize_brief_defaults(brief: dict[str, Any]) -> dict[str, Any]:
    """Ensure brief.json freezes video workflow/provider defaults at init time."""
    out = dict(brief)
    video = dict(out.get("video") if isinstance(out.get("video"), dict) else {})
    video.setdefault("workflow", video.get("flow") or out.get("video_workflow") or out.get("video_flow") or "i2v")
    video.setdefault("flow", video.get("workflow") or "i2v")
    video.setdefault("seconds_per_shot", "4s")
    video.setdefault("resolution", "480p")
    video.setdefault("width", 480)
    video.setdefault("height", 480)
    video.setdefault("enable_audio", False)
    out["video"] = video

    defaults = dict(out.get("defaults") if isinstance(out.get("defaults"), dict) else {})
    provider = out.get("provider") or defaults.get("provider") or "comfyui"
    defaults.setdefault("provider", provider)
    provider_token = str(provider).strip().lower().replace(" ", "_")
    wants_fal = provider_token in {"fal", "fal.ai", "fal_ai"}
    defaults.setdefault("provider_image", out.get("provider_image") or ("fal:hidream_o1" if wants_fal else "local-comfyui:img2img_klein"))
    defaults.setdefault("provider_edit", out.get("provider_edit") or ("fal:hidream_o1_edit" if wants_fal else "local-comfyui:img2img_klein"))
    defaults.setdefault("provider_video", out.get("provider_video") or ("fal:veo31_lite_i2v" if wants_fal else "local-comfyui:img2vid_wan_lora"))
    defaults.setdefault("provider_flf2v", out.get("provider_flf2v") or "fal:veo31_lite_flf2v")
    out["provider"] = provider
    out.setdefault("provider_image", defaults["provider_image"])
    out.setdefault("provider_edit", defaults["provider_edit"])
    out.setdefault("provider_video", defaults["provider_video"])
    out.setdefault("provider_flf2v", defaults["provider_flf2v"])
    out["defaults"] = defaults
    return out


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def initial_producer_state(project_id: str, pipeline_id: str, layout_profile: str) -> dict[str, Any]:
    return {
        "schema": PRODUCER_STATE_SCHEMA,
        "project_id": project_id,
        "pipeline_id": pipeline_id,
        "layout_profile": layout_profile,
        "current_goal": "p0_briefgate",
        "stage_cursor": 0,
        "gate_decisions": [],
    }


def init_project(
    project_id: str,
    brief: dict[str, Any] | None = None,
    *,
    pipeline_id: str = DEFAULT_PIPELINE_ID,
    layout_profile: str | None = None,
    pipeline_spec: str | None = None,
    base_dir: Path = BASE,
) -> Path:
    if not brief:
        fail("brief_json is required. Collect generation parameters before initializing.")

    layout_profile = resolve_layout_profile(pipeline_id, layout_profile)
    spec = resolve_pipeline_spec(pipeline_id, pipeline_spec)
    if spec.get("project_layout_profile") != layout_profile:
        fail(f"pipeline spec layout profile mismatch: {spec.get('project_layout_profile')!r} != {layout_profile!r}")

    brief = normalize_brief_defaults(brief)
    brief.setdefault("schema", "kinodel.brief.v1")
    brief.setdefault("project_id", project_id)
    brief.setdefault("status", "complete")
    validate_brief_intake(brief)
    if brief.get("project_id") != project_id:
        fail(f"brief project_id mismatch: {brief.get('project_id')!r} != {project_id!r}")

    root = base_dir / project_id / "v1"
    if root.exists():
        fail(f"{root} already exists. Refuse to overwrite.")

    root.mkdir(parents=True)
    (root / "outputs").mkdir()
    (root / "render_results").mkdir()
    (root / "qc").mkdir()

    write_json(root / "brief.json", brief)
    write_json(root / "pipeline_spec.json", spec)
    write_json(root / "producer_state.json", initial_producer_state(project_id, pipeline_id, layout_profile))

    profile = LAYOUT_PROFILES[layout_profile]
    for name, payload in profile["artifacts"].items():
        write_json(root / name, pending_with_project(project_id, payload))

    for name, stage in profile["render_results"].items():
        write_json(root / "render_results" / name, {
            "schema": "kinodel.render_result.v1",
            "project_id": project_id,
            "status": "pending",
            "stage": stage,
            "selected_outputs": [],
            "attempts": [],
            "selection_policy": "outputs/ may contain many generated iterations; selected_outputs contains the current approved refs for downstream stages.",
        })

    return root


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a Kinodel project directory after BriefGate approval.")
    parser.add_argument("project_id")
    parser.add_argument("brief_json")
    parser.add_argument("--pipeline-id", default=DEFAULT_PIPELINE_ID)
    parser.add_argument("--layout-profile", default=None)
    parser.add_argument("--pipeline-spec", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        brief = json.loads(args.brief_json)
    except json.JSONDecodeError as exc:
        fail(f"invalid brief JSON: {exc}")
    if not isinstance(brief, dict):
        fail("brief_json must be a JSON object")
    root = init_project(
        args.project_id,
        brief,
        pipeline_id=args.pipeline_id,
        layout_profile=args.layout_profile,
        pipeline_spec=args.pipeline_spec,
    )
    print(f"Initialized {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
