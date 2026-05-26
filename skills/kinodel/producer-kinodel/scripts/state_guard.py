#!/usr/bin/env python3
"""Compact Kinodel project guard and handoff generator.

Usage:
  python state_guard.py summary --project-dir ~/projects/demo/v1
  python state_guard.py validate --project-dir ~/projects/demo/v1 --artifact storyboard_requests.json
  python state_guard.py next-goal --project-dir ~/projects/demo/v1
  python state_guard.py next-goal --project-dir ~/projects/demo/v1 --skip-gates  # DEBUG ONLY
  python state_guard.py handoff --project-dir ~/projects/demo/v1 --goal p5_storyboard_plan --edit-notes notes.txt
  python state_guard.py approve-gate --project-dir ~/projects/demo/v1 --gate p4 --decision A
  python state_guard.py resume --project-dir ~/projects/demo/v1
  python state_guard.py list-projects --root ~/projects --unfinished

Use `handoff` for production; it outputs a compact JSON envelope for delegate_task.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

REQUEST_ARTIFACTS = {
    "wardrobe_request.json": "main_frame",
    "storyboard_requests.json": "story_frames",
    "video_requests.json": "shot_videos",
}

RESULT_ARTIFACTS = {
    "render_results/main_frame_result.json": "main_frame",
    "render_results/story_frames_result.json": "story_frames",
    "render_results/shot_videos_result.json": "shot_videos",
}

RESULT_TO_REQUEST_ARTIFACT = {
    "render_results/main_frame_result.json": "wardrobe_request.json",
    "render_results/story_frames_result.json": "storyboard_requests.json",
    "render_results/shot_videos_result.json": "video_requests.json",
}

EXPECTED_SCHEMAS = {
    "brief.json": "kinodel.brief.v1",
    "story.json": "kinodel.story.v1",
    "wardrobe_request.json": "kinodel.render_requests.v1",
    "storyboard_requests.json": "kinodel.render_requests.v1",
    "video_requests.json": "kinodel.render_requests.v1",
    "render_results/main_frame_result.json": "kinodel.render_result.v1",
    "render_results/story_frames_result.json": "kinodel.render_result.v1",
    "render_results/shot_videos_result.json": "kinodel.render_result.v1",
    "final_chunk.json": "kinodel.final_chunk.v1",
    "chunks/cinema_chunk.json": "kinodel.cinema_chunk.v1",
}

GOAL_ORDER = [
    "p0_briefgate",
    "p1_story",
    "p2_main_frame_plan",
    "p3_main_frame_render",
    "p4_story_main_gate",
    "p5_storyboard_plan",
    "p6_story_images_render",
    "p7_story_images_gate",
    "p8_video_plan",
    "p9_video_render",
    "p10_montage",
    "p11_final_chunk",
    "p12_final_gate",
    "p13_cinema_chunk",
]

GOAL_EXIT_ARTIFACT = {
    "p0_briefgate": "brief.json",
    "p1_story": "story.json",
    "p2_main_frame_plan": "wardrobe_request.json",
    "p3_main_frame_render": "render_results/main_frame_result.json",
    "p5_storyboard_plan": "storyboard_requests.json",
    "p6_story_images_render": "render_results/story_frames_result.json",
    "p8_video_plan": "video_requests.json",
    "p9_video_render": "render_results/shot_videos_result.json",
    "p10_montage": "outputs/final.mp4",
    "p11_final_chunk": "final_chunk.json",
    "p13_cinema_chunk": "chunks/cinema_chunk.json",
}

GOALS = {
    "p1_story": {
        "skill": "storytell-kinodel",
        "read": ["brief.json"],
        "write": "story.json",
        "selected_from": [],
    },
    "p2_main_frame_plan": {
        "skill": "wardrobe-kinodel",
        "support_skills": ["flux2-prompt-engine"],
        "read": ["brief.json", "story.json"],
        "write": "wardrobe_request.json",
        "selected_from": [],
    },
    "p5_storyboard_plan": {
        "skill": "storyboard-kinodel",
        "support_skills": ["flux2-prompt-engine"],
        "read": ["brief.json", "story.json", "render_results/main_frame_result.json"],
        "write": "storyboard_requests.json",
        "selected_from": ["render_results/main_frame_result.json"],
    },
    "p8_video_plan": {
        "skill": "filmmaker-kinodel",
        "support_skills": ["prompt-videos"],
        "read": ["brief.json", "story.json", "render_results/story_frames_result.json"],
        "write": "video_requests.json",
        "selected_from": ["render_results/story_frames_result.json"],
    },
    "p10_montage": {
        "skill": "montage-kinodel",
        "read": ["render_results/shot_videos_result.json"],
        "write": "outputs/final.mp4",
        "selected_from": ["render_results/shot_videos_result.json"],
    },
    "p13_cinema_chunk": {
        "skill": "craft-kinodel",
        "read": ["final_chunk.json", "render_results/main_frame_result.json", "render_results/story_frames_result.json", "render_results/shot_videos_result.json"],
        "write": "chunks/cinema_chunk.json",
        "selected_from": ["render_results/main_frame_result.json", "render_results/story_frames_result.json"],
    },
}

REVIEW_GATES = {"p4_story_main_gate", "p7_story_images_gate", "p12_final_gate"}

PIPELINE_SPEC_SCHEMA = "kinodel.pipeline_spec.v1"
PRODUCER_STATE_SCHEMA = "kinodel.producer_state.v1"
SPEC_REGISTRY_DIR = Path.home() / ".hermes" / "skills" / "kinodel" / "pipeline-kinodel" / "pipelines"
CHUNK_VALIDATOR_PATH = Path.home() / ".hermes" / "skills" / "kinodel" / "pipeline-kinodel" / "scripts" / "validate_chunk_schema.py"
APPROVE_DECISIONS = {"A", "approve", "approved", "yes", "true"}
DELEGATABLE_STAGE_TYPES = {"agent_stage", "montage_stage"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"ERROR: cannot parse {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {path} is not a JSON object")
    return data


def project_id(project_dir: Path) -> str:
    brief = project_dir / "brief.json"
    if not brief.exists():
        raise SystemExit(f"ERROR: missing {brief}")
    pid = load_json(brief).get("project_id")
    if not pid:
        raise SystemExit("ERROR: brief.json has no project_id")
    return str(pid)


def rel(project_dir: Path, relpath: str) -> Path:
    return (project_dir / relpath).expanduser().resolve()


def file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_schema(relpath: str, data: dict[str, Any], errors: list[str]) -> None:
    expected = EXPECTED_SCHEMAS.get(relpath)
    if expected and data.get("schema") != expected:
        errors.append(f"schema mismatch: {data.get('schema')!r} != {expected!r}")


def validate_story(data: dict[str, Any], errors: list[str]) -> None:
    if data.get("status") != "complete":
        errors.append("status is not complete")
    shots = data.get("shots")
    scene_count = data.get("scene_count")
    if not data.get("story"):
        errors.append("story missing")
    if not isinstance(shots, list) or not shots:
        errors.append("shots is empty or not a list")
    if scene_count is not None and isinstance(shots, list) and int(scene_count) != len(shots):
        errors.append(f"scene_count mismatch: {scene_count} != len(shots) {len(shots)}")


def normalize_token(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def video_flow_from_brief(brief: dict[str, Any]) -> str | None:
    """Return an explicit video job-kind override from brief, if present.

    BriefGate now persists the workflow up front so p8 does not invent it.
    Accept migration aliases for older briefs.
    """
    video = brief.get("video") if isinstance(brief.get("video"), dict) else {}
    raw = (
        video.get("workflow")
        or video.get("flow")
        or video.get("mode")
        or video.get("kind")
        or video.get("job_kind")
        or brief.get("video_workflow")
        or brief.get("video_flow")
        or brief.get("video_kind")
    )
    token = normalize_token(raw)
    if token in {"i2v", "image_to_video", "image2video", "per_frame", "per_frame_i2v"}:
        return "i2v"
    if token in {"flf2v", "first_last_frame", "first_last_frame_to_video", "transition", "transitions"}:
        return "flf2v"
    if token in {"t2v", "text_to_video", "text2video"}:
        return "t2v"
    return None


def video_duration_from_brief(brief: dict[str, Any]) -> str | None:
    video = brief.get("video") if isinstance(brief.get("video"), dict) else {}
    raw = video.get("seconds_per_shot") or video.get("duration") or brief.get("video_duration") or brief.get("duration")
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return f"{raw:g}s"
    return str(raw).strip()


def provider_tokens_from_brief(brief: dict[str, Any]) -> set[str]:
    video = brief.get("video") if isinstance(brief.get("video"), dict) else {}
    defaults = brief.get("defaults") if isinstance(brief.get("defaults"), dict) else {}
    raw_values = [
        brief.get("provider_video"),
        brief.get("video_provider"),
        brief.get("provider"),
        defaults.get("provider_video"),
        defaults.get("video_provider"),
        defaults.get("provider"),
        video.get("provider"),
        video.get("provider_video"),
    ]
    return {normalize_token(v) for v in raw_values if v}


def request_provider_tokens(data: dict[str, Any]) -> set[str]:
    defaults = data.get("defaults") if isinstance(data.get("defaults"), dict) else {}
    tokens = {normalize_token(defaults.get(k)) for k in ("provider", "provider_video", "video_provider") if defaults.get(k)}
    for job in data.get("jobs") or []:
        if isinstance(job, dict) and job.get("provider"):
            tokens.add(normalize_token(job.get("provider")))
    return {t for t in tokens if t}


def validate_video_request_against_brief(project_dir: Path, data: dict[str, Any], errors: list[str]) -> None:
    """Catch stale p8 artifacts after mid-pipeline video flow/provider changes."""
    brief_path = rel(project_dir, "brief.json")
    if not brief_path.exists():
        return
    brief = load_json(brief_path)
    expected_flow = video_flow_from_brief(brief)
    jobs = [j for j in (data.get("jobs") or []) if isinstance(j, dict)]
    if expected_flow:
        wrong = [j.get("shot_id") or f"jobs[{i}]" for i, j in enumerate(jobs) if j.get("kind") != expected_flow]
        if wrong:
            errors.append(f"video flow mismatch with brief: expected kind={expected_flow}, stale jobs={wrong}")

    duration = video_duration_from_brief(brief)
    if duration and normalize_token(duration) not in {"8s", "8"}:
        flf_jobs = [j.get("shot_id") or f"jobs[{i}]" for i, j in enumerate(jobs) if j.get("kind") == "flf2v"]
        if flf_jobs:
            errors.append(f"brief requests video duration {duration}, but flf2v jobs are fixed/standard 8s transitions: {flf_jobs}")

    provider_tokens = provider_tokens_from_brief(brief)
    wants_comfy = bool(provider_tokens & {"comfyui", "local_comfyui", "local_comfyui:img2vid_wan_lora", "comfyui:img2vid_wan_lora"})
    if wants_comfy:
        req_tokens = request_provider_tokens(data)
        if not req_tokens:
            errors.append("brief requests ComfyUI video, but video_requests.json has no defaults.provider_video or job.provider")
        elif not any(t.startswith("comfyui") or t.startswith("local_comfyui") for t in req_tokens):
            errors.append(f"brief requests ComfyUI video, but video request provider is {sorted(req_tokens)}")


def validate_request(relpath: str, data: dict[str, Any], errors: list[str]) -> None:
    if data.get("status") != "complete":
        errors.append("status is not complete")
    expected_stage = REQUEST_ARTIFACTS.get(relpath)
    if expected_stage and data.get("stage") not in {expected_stage, None}:
        errors.append(f"stage mismatch: {data.get('stage')!r} != {expected_stage!r}")
    jobs = data.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        errors.append("jobs is empty or not a list")
        return
    for i, job in enumerate(jobs):
        if not isinstance(job, dict):
            errors.append(f"jobs[{i}] is not object")
            continue
        if job.get("kind") not in {"t2i", "i2i", "i2v", "flf2v"}:
            errors.append(f"jobs[{i}].kind invalid")
        if not job.get("render_prompt"):
            errors.append(f"jobs[{i}].render_prompt missing")
        media = job.get("input_media", [])
        if isinstance(media, str):
            errors.append(f"jobs[{i}].input_media is bare string; must be array")
        if job.get("kind") in {"i2i", "i2v", "flf2v"}:
            if not isinstance(media, list) or not media:
                errors.append(f"jobs[{i}].input_media required")
            elif any(not str(x).startswith("https://") for x in media):
                errors.append(f"jobs[{i}].input_media must be public https URLs")


def validate_result(project_dir: Path, relpath: str, data: dict[str, Any], errors: list[str]) -> None:
    if data.get("status") != "complete":
        errors.append("status is not complete")
    expected_stage = RESULT_ARTIFACTS.get(relpath)
    if expected_stage and data.get("stage") not in {expected_stage, None}:
        errors.append(f"stage mismatch: {data.get('stage')!r} != {expected_stage!r}")
    source_request = data.get("source_request") if isinstance(data.get("source_request"), dict) else {}
    if source_request:
        expected_request = RESULT_TO_REQUEST_ARTIFACT.get(relpath)
        source_artifact = source_request.get("artifact")
        source_sha = source_request.get("sha256")
        if expected_request and source_artifact and source_artifact != expected_request:
            errors.append(f"source_request.artifact mismatch: {source_artifact!r} != {expected_request!r}")
        if expected_request and source_sha:
            current_sha = file_sha256(rel(project_dir, expected_request))
            if current_sha and current_sha != source_sha:
                snapshot_path = source_request.get("snapshot_path")
                if snapshot_path:
                    snapshot_file = resolve_project_media_path(project_dir, str(snapshot_path))
                    snapshot_sha = file_sha256(snapshot_file)
                    if not snapshot_file.exists():
                        errors.append(f"source_request.snapshot_path does not exist: {snapshot_path}")
                    elif snapshot_sha != source_sha:
                        errors.append(f"source_request.snapshot_path sha mismatch: {snapshot_sha} != {source_sha}")
                else:
                    errors.append(f"stale render result: {relpath} was rendered from {expected_request} sha256={source_sha[:12]}, current sha256={current_sha[:12]}")
    outs = data.get("selected_outputs")
    if not isinstance(outs, list) or not outs:
        errors.append("selected_outputs is empty or not a list")
        return
    for i, out in enumerate(outs):
        if not isinstance(out, dict):
            errors.append(f"selected_outputs[{i}] is not object")
            continue
        path_value = out.get("path")
        if not path_value:
            errors.append(f"selected_outputs[{i}].path missing")
        else:
            media_path = resolve_project_media_path(project_dir, str(path_value))
            if not media_path.exists():
                errors.append(f"selected_outputs[{i}].path does not exist: {path_value}")
            elif not media_path.is_file():
                errors.append(f"selected_outputs[{i}].path is not a file: {path_value}")
            else:
                expected_sha = out.get("sha256")
                actual_sha = file_sha256(media_path)
                if expected_sha and actual_sha != expected_sha:
                    errors.append(f"selected_outputs[{i}].sha256 mismatch for {path_value}: {actual_sha} != {expected_sha}")
                source_value = out.get("source_path")
                if source_value:
                    source_path = resolve_project_media_path(project_dir, str(source_value))
                    if not source_path.exists():
                        errors.append(f"selected_outputs[{i}].source_path does not exist: {source_value}")
                    elif source_path.is_file():
                        source_sha = file_sha256(source_path)
                        if actual_sha and source_sha and actual_sha != source_sha:
                            errors.append(f"selected_outputs[{i}] canonical/source hash mismatch: {path_value} != {source_value}")
                    else:
                        errors.append(f"selected_outputs[{i}].source_path is not a file: {source_value}")
        if not out.get("url"):
            errors.append(f"selected_outputs[{i}].url missing")


def resolve_project_media_path(project_dir: Path, value: str) -> Path:
    media_path = Path(value).expanduser()
    if media_path.is_absolute():
        return media_path
    return rel(project_dir, value)


def validate_final_chunk(project_dir: Path, data: dict[str, Any], errors: list[str]) -> None:
    if data.get("status") and data.get("status") != "complete":
        errors.append("status is not complete")
    final_video = data.get("final_video")
    if not isinstance(final_video, dict):
        errors.append("final_video missing or not an object")
        return
    video_path_value = final_video.get("path")
    if not video_path_value:
        errors.append("final_video.path missing")
        return
    video_path = resolve_project_media_path(project_dir, str(video_path_value))
    if not video_path.exists():
        errors.append(f"final_video.path does not exist: {video_path_value}")
        return
    if not video_path.is_file():
        errors.append(f"final_video.path is not a file: {video_path_value}")
        return
    if video_path.stat().st_size <= 0:
        errors.append(f"final_video.path is empty: {video_path_value}")


def validate_crafted_chunk(path: Path) -> list[str]:
    try:
        spec = importlib.util.spec_from_file_location("validate_chunk_schema", CHUNK_VALIDATOR_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        data = load_json(path)
        return list(module.validate_document(data, path))
    except Exception as exc:
        return [f"chunk schema validation failed: {exc}"]


def validate_artifact(project_dir: Path, relpath: str) -> dict[str, Any]:
    pid = project_id(project_dir)
    path = rel(project_dir, relpath)
    if not path.exists():
        return {"path": relpath, "ok": False, "error": "missing"}
    if path.suffix.lower() != ".json":
        return {"path": relpath, "ok": path.stat().st_size > 0, "size": path.stat().st_size}

    data = load_json(path)
    errors: list[str] = []
    check_schema(relpath, data, errors)
    if data.get("project_id") and data.get("project_id") != pid:
        errors.append(f"project_id mismatch: {data.get('project_id')} != {pid}")
    if relpath == "brief.json":
        if data.get("status") != "complete":
            errors.append("status is not complete")
        if not data.get("project_id"):
            errors.append("project_id missing")
    elif relpath == "story.json":
        validate_story(data, errors)
    elif relpath in REQUEST_ARTIFACTS:
        validate_request(relpath, data, errors)
        if relpath == "video_requests.json":
            validate_video_request_against_brief(project_dir, data, errors)
    elif relpath in RESULT_ARTIFACTS:
        validate_result(project_dir, relpath, data, errors)
    elif relpath == "final_chunk.json":
        validate_final_chunk(project_dir, data, errors)
    elif relpath == "chunks/cinema_chunk.json":
        errors.extend(validate_crafted_chunk(path))
    elif data.get("status") and data.get("status") != "complete":
        errors.append("status is not complete")
    return {"path": relpath, "ok": not errors, "errors": errors}


def collect_selected(project_dir: Path, refs: list[str]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for r in refs:
        p = rel(project_dir, r)
        if not p.exists():
            continue
        data = load_json(p)
        for item in data.get("selected_outputs", []) or []:
            if isinstance(item, dict):
                selected.append({k: item[k] for k in ("shot_id", "kind", "path", "url") if k in item})
    return selected


def compact_context_cache(project_dir: Path, read_refs: list[str]) -> list[dict[str, Any]]:
    """Inline digest for high-reuse artifacts, not a durable cache.

    Delegates still read authoritative files. The cache carries tiny identity and
    shape hints so the handoff is debuggable without pasting full artifacts.
    """
    cache: list[dict[str, Any]] = []
    for r in read_refs:
        if r not in {"brief.json", "story.json"}:
            continue
        p = rel(project_dir, r)
        if not p.exists():
            continue
        raw = p.read_text(encoding="utf-8")
        item: dict[str, Any] = {
            "path": r,
            "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16],
        }
        try:
            data = json.loads(raw)
        except Exception:
            cache.append(item)
            continue
        if r == "brief.json":
            video = data.get("video") if isinstance(data.get("video"), dict) else {}
            item["summary"] = {
                "project_id": data.get("project_id"),
                "shot_count": data.get("shot_count"),
                "aspect_ratio": data.get("aspect_ratio"),
                "seconds_per_shot": video.get("seconds_per_shot") or video.get("duration"),
                "enable_audio": video.get("enable_audio"),
            }
        elif r == "story.json":
            story = str(data.get("story") or data.get("summary") or "")
            hooks = data.get("hook_candidates")  # migration-only legacy field
            hook = data.get("hook") or (hooks[0] if isinstance(hooks, list) and hooks else None)
            item["summary"] = {
                "scene_count": data.get("scene_count") or len(data.get("shots", []) or []),
                "story_excerpt": story[:280],
                "hook": hook,
            }
        cache.append(item)
    return cache


def read_edit_notes(value: str | None) -> str | None:
    if not value:
        return None
    p = Path(value).expanduser()
    if p.exists() and p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return value.strip()


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(x) for x in value if x]
    return []


def first_or_none(values: list[str]) -> str | None:
    return values[0] if values else None


def load_producer_state(project_dir: Path) -> dict[str, Any]:
    path = rel(project_dir, "producer_state.json")
    if not path.exists():
        return {}
    data = load_json(path)
    if data.get("schema") and data.get("schema") != PRODUCER_STATE_SCHEMA:
        raise SystemExit(f"ERROR: producer_state.json schema mismatch: {data.get('schema')!r} != {PRODUCER_STATE_SCHEMA!r}")
    return data


def load_pipeline_spec(project_dir: Path, explicit_spec: str | None = None) -> dict[str, Any] | None:
    """Resolve a pipeline spec using the Phase B order.

    Order:
    1. explicit CLI/API path;
    2. project-local pipeline_spec.json;
    3. producer_state.json.pipeline_id -> skill registry;
    4. None, so caller uses hardcoded cinematic fallback.
    """
    if explicit_spec:
        path = Path(explicit_spec).expanduser().resolve()
        data = load_json(path)
        if data.get("schema") != PIPELINE_SPEC_SCHEMA:
            raise SystemExit(f"ERROR: explicit pipeline spec schema mismatch: {data.get('schema')!r} != {PIPELINE_SPEC_SCHEMA!r}")
        return data

    local = rel(project_dir, "pipeline_spec.json")
    if local.exists():
        data = load_json(local)
        if data.get("schema") != PIPELINE_SPEC_SCHEMA:
            raise SystemExit(f"ERROR: pipeline_spec.json schema mismatch: {data.get('schema')!r} != {PIPELINE_SPEC_SCHEMA!r}")
        return data
    state = load_producer_state(project_dir)
    pipeline_id = state.get("pipeline_id")
    if pipeline_id:
        registry = SPEC_REGISTRY_DIR / f"{pipeline_id}.json"
        if registry.exists():
            data = load_json(registry)
            if data.get("schema") != PIPELINE_SPEC_SCHEMA:
                raise SystemExit(f"ERROR: {registry} schema mismatch: {data.get('schema')!r} != {PIPELINE_SPEC_SCHEMA!r}")
            return data
        raise SystemExit(f"ERROR: producer_state.json requested unknown pipeline_id {pipeline_id!r}; missing {registry}")
    return None


def compile_legacy_route() -> dict[str, Any]:
    """Compile the legacy hardcoded cinematic maps into the same route shape.

    Phase B keeps these maps as fallback only for projects that do not carry
    pipeline_spec.json and do not name a pipeline_id in producer_state.json.
    """
    stage_descriptors = {goal: {"goal": goal, "type": "legacy_stage", "writes": as_list(artifact)} for goal, artifact in GOAL_EXIT_ARTIFACT.items()}
    for goal, spec in GOALS.items():
        stage_descriptors[goal] = {
            "goal": goal,
            "type": "agent_stage" if goal != "p10_montage" else "montage_stage",
            "owner_skill": spec.get("skill"),
            "reads": spec.get("read", []),
            "writes": as_list(spec.get("write")),
        }
    review_gates = {g: {"goal": g, "gate_alias": g.split("_", 1)[0], "gate_kind": "review_gate", "stop": True, "choices": ["A", "B", "C", "D"]} for g in REVIEW_GATES}
    if "p12_final_gate" in review_gates:
        review_gates["p12_final_gate"].update({
            "gate_alias": "p12",
            "label": "Final Project ReviewGate",
            "reads": ["outputs/final.mp4", "final_chunk.json"],
            "previews": ["outputs/final.mp4", "final_chunk.json"],
        })
    stage_descriptors.update({goal: dict(meta, type="review_gate") for goal, meta in review_gates.items()})
    return {
        "spec_based": False,
        "pipeline_id": "legacy.cinematic",
        "ordered_goals": list(GOAL_ORDER),
        "stages_by_goal": stage_descriptors,
        "delegated": GOALS,
        "exit_artifacts": GOAL_EXIT_ARTIFACT,
        "validators": dict(EXPECTED_SCHEMAS),
        "render_stages": {},
        "review_gates": review_gates,
        "final_chunk": {"path": "final_chunk.json", "schema": EXPECTED_SCHEMAS["final_chunk.json"]},
        "compatibility": {"legacy_goal_aliases": True, "hard_gate_aliases": ["p4", "p7", "p12"]},
    }


def selected_from_for_stage(stage: dict[str, Any], reads: list[str]) -> list[str]:
    explicit = as_list(stage.get("selected_from"))
    if explicit:
        return explicit
    return [r for r in reads if r.startswith("render_results/")]


def compile_spec_route(spec: dict[str, Any]) -> dict[str, Any]:
    """Compile pipeline_spec.v1 into the single route shape used by state_guard.

    This is the Phase B CompiledRoute abstraction: helpers read this structure
    instead of growing parallel dynamic replacements for every old cinematic map.
    """
    stages = spec.get("stages")
    if not isinstance(stages, list) or not stages:
        raise SystemExit("ERROR: pipeline spec has no non-empty stages[]")
    ordered_goals: list[str] = []
    stages_by_goal: dict[str, dict[str, Any]] = {}
    delegated: dict[str, dict[str, Any]] = {}
    exit_artifacts: dict[str, str] = {}
    validators: dict[str, str] = {}
    render_stages: dict[str, dict[str, Any]] = {}
    review_gates: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for stage in stages:
        if not isinstance(stage, dict):
            raise SystemExit("ERROR: pipeline spec stage is not an object")
        goal = str(stage.get("goal") or "")
        stage_type = str(stage.get("type") or "")
        if not goal:
            raise SystemExit("ERROR: pipeline spec stage missing goal")
        if goal in seen:
            raise SystemExit(f"ERROR: duplicate pipeline goal {goal}")
        seen.add(goal)
        ordered_goals.append(goal)
        reads = as_list(stage.get("reads"))
        writes = as_list(stage.get("writes"))
        stages_by_goal[goal] = dict(stage, reads=reads, writes=writes)
        validator = stage.get("validator")
        if validator:
            for artifact in writes:
                validators[artifact] = str(validator)
        if stage_type == "review_gate":
            if stage.get("stop") is not True:
                raise SystemExit(f"ERROR: review gate {goal} must declare stop: true")
            review_gates[goal] = {
                "goal": goal,
                "gate_alias": stage.get("gate_alias") or goal.split("_", 1)[0],
                "gate_kind": stage.get("gate_kind"),
                "label": stage.get("label"),
                "stop": True,
                "choices": stage.get("choices") or ["A", "B", "C", "D"],
                "reads": reads,
                "previews": as_list(stage.get("previews")) or reads,
                "resume_scope": stage.get("resume_scope"),
            }
            continue
        if stage_type in DELEGATABLE_STAGE_TYPES:
            owner = stage.get("owner_skill")
            if not owner:
                raise SystemExit(f"ERROR: delegated stage {goal} missing owner_skill")
            delegated[goal] = {
                "skill": owner,
                "support_skills": as_list(stage.get("support_skills")),
                "read": reads,
                "write": first_or_none(writes),
                "selected_from": selected_from_for_stage(stage, reads),
                "requires_capabilities": as_list(stage.get("requires_capabilities")),
                "validator": stage.get("validator"),
            }
        if stage_type == "render_stage":
            result_artifact = stage.get("result_artifact") or first_or_none(writes)
            request_artifact = stage.get("request_artifact")
            if not request_artifact or not result_artifact:
                raise SystemExit(f"ERROR: render stage {goal} missing request_artifact/result_artifact")
            render_stages[goal] = {
                "goal": goal,
                "request_artifact": str(request_artifact),
                "result_artifact": str(result_artifact),
                "modality": stage.get("modality"),
                "adapter_profile": stage.get("adapter_profile"),
                "reads": reads,
                "writes": writes,
            }
            exit_artifacts[goal] = str(result_artifact)
        elif writes:
            exit_artifacts[goal] = writes[0]
    return {
        "spec_based": True,
        "pipeline_id": spec.get("pipeline_id"),
        "ordered_goals": ordered_goals,
        "stages_by_goal": stages_by_goal,
        "delegated": delegated,
        "exit_artifacts": exit_artifacts,
        "validators": validators,
        "render_stages": render_stages,
        "review_gates": review_gates,
        "final_chunk": spec.get("final_chunk") or {},
        "compatibility": spec.get("compatibility") or {},
    }


def load_route(project_dir: Path, explicit_spec: str | None = None) -> dict[str, Any]:
    spec = load_pipeline_spec(project_dir, explicit_spec=explicit_spec)
    if spec:
        return compile_spec_route(spec)
    return compile_legacy_route()


def approved_gate_keys(project_dir: Path) -> set[str]:
    state = load_producer_state(project_dir)
    keys: set[str] = set()
    decisions = state.get("gate_decisions", [])
    if not isinstance(decisions, list):
        raise SystemExit("ERROR: producer_state.json gate_decisions must be a list")
    for item in decisions:
        if not isinstance(item, dict):
            continue
        decision = str(item.get("decision") or "").strip()
        if decision not in APPROVE_DECISIONS and decision.lower() not in APPROVE_DECISIONS:
            continue
        if item.get("goal"):
            keys.add(str(item["goal"]))
        if item.get("gate_alias"):
            keys.add(str(item["gate_alias"]))
    return keys


def gate_is_approved(project_dir: Path, gate: dict[str, Any]) -> bool:
    keys = approved_gate_keys(project_dir)
    return str(gate.get("goal")) in keys or str(gate.get("gate_alias")) in keys


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def producer_state_path(project_dir: Path) -> Path:
    return rel(project_dir, "producer_state.json")


def save_producer_state(project_dir: Path, state: dict[str, Any]) -> None:
    path = producer_state_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def goal_cursor(route: dict[str, Any], goal: str | None) -> int:
    if not goal:
        return max(0, len(route.get("ordered_goals", [])) - 1)
    ordered = route.get("ordered_goals") or GOAL_ORDER
    try:
        return int(ordered.index(goal))
    except ValueError:
        try:
            return GOAL_ORDER.index(goal)
        except ValueError:
            return 0


def next_goal_after(route: dict[str, Any], goal: str) -> str | None:
    ordered = route.get("ordered_goals") or GOAL_ORDER
    if goal not in ordered:
        return None
    idx = ordered.index(goal)
    if idx + 1 >= len(ordered):
        return None
    return str(ordered[idx + 1])


def resolve_gate(route: dict[str, Any], gate_name: str) -> dict[str, Any]:
    token = str(gate_name or "").strip()
    for gate in route["review_gates"].values():
        if token in {str(gate.get("goal")), str(gate.get("gate_alias"))}:
            return gate
    known = [f"{g.get('goal')} ({g.get('gate_alias')})" for g in route["review_gates"].values()]
    raise SystemExit(f"ERROR: unknown review gate {gate_name!r}; known: {known}")


def approve_gate(project_dir: Path, gate_name: str, decision: str = "A", source: str = "user", explicit_spec: str | None = None) -> dict[str, Any]:
    project_dir = project_dir.expanduser().resolve()
    route = load_route(project_dir, explicit_spec=explicit_spec)
    gate = resolve_gate(route, gate_name)
    decision = str(decision or "A").strip()
    if decision not in APPROVE_DECISIONS and decision.lower() not in APPROVE_DECISIONS:
        raise SystemExit(f"ERROR: approve-gate only records approving decisions; got {decision!r}")

    state = load_producer_state(project_dir)
    if not state:
        state = {
            "schema": PRODUCER_STATE_SCHEMA,
            "project_id": project_id(project_dir),
            "pipeline_id": route.get("pipeline_id"),
            "current_goal": "p0_briefgate",
            "stage_cursor": 0,
            "gate_decisions": [],
        }
    state.setdefault("schema", PRODUCER_STATE_SCHEMA)
    state.setdefault("project_id", project_id(project_dir))
    if route.get("pipeline_id"):
        state.setdefault("pipeline_id", route.get("pipeline_id"))
    decisions = state.setdefault("gate_decisions", [])
    if not isinstance(decisions, list):
        raise SystemExit("ERROR: producer_state.json gate_decisions must be a list")

    goal = str(gate.get("goal"))
    alias = str(gate.get("gate_alias"))
    existing = None
    for item in decisions:
        if isinstance(item, dict) and (item.get("goal") == goal or item.get("gate_alias") == alias):
            existing = item
            break
    record = {
        "goal": goal,
        "gate_alias": alias,
        "decision": decision,
        "approved_at": utc_now(),
        "source": source,
    }
    if existing is not None:
        existing.update(record)
    else:
        decisions.append(record)

    next_goal = next_goal_after(route, goal)
    inferred = infer_next_goal(project_dir, include_gates=True, explicit_spec=explicit_spec)
    if inferred.get("next_goal") == goal:
        # infer_next_goal reads producer_state from disk, so before saving it may
        # still see this gate as unapproved. Use the graph successor here.
        inferred = {"next_goal": next_goal, "reason": f"{goal} approved", "stop": False}
    state["current_goal"] = str(inferred.get("next_goal") or next_goal or goal)
    state["stage_cursor"] = goal_cursor(route, state.get("current_goal"))
    state["updated_at"] = utc_now()
    save_producer_state(project_dir, state)

    after = infer_next_goal(project_dir, include_gates=True, explicit_spec=explicit_spec)
    after_goal = after.get("next_goal")
    # If approval completes the pipeline, do not leave producer_state pointing at
    # the previous downstream goal. Resume reports use current_goal=None as the
    # unambiguous durable marker for a complete project.
    state["current_goal"] = str(after_goal) if after_goal else None
    state["stage_cursor"] = goal_cursor(route, state.get("current_goal"))
    state["updated_at"] = utc_now()
    save_producer_state(project_dir, state)
    return {
        "project_id": project_id(project_dir),
        "goal": goal,
        "gate_alias": alias,
        "decision": decision,
        "next_goal": after.get("next_goal"),
        "stop": after.get("stop"),
        "state_path": str(producer_state_path(project_dir)),
    }


def completed_goals(project_dir: Path, route: dict[str, Any]) -> list[str]:
    done: list[str] = []
    for goal in route.get("ordered_goals", [])[1:]:
        gate = route["review_gates"].get(goal)
        if gate:
            if gate_is_approved(project_dir, gate):
                done.append(goal)
            continue
        artifact = route["exit_artifacts"].get(goal)
        if artifact and is_complete(project_dir, artifact):
            done.append(goal)
    return done


GATE_PROMPT = "Reply with one letter: A — approve this gate; B — auto-fix via critic; C — edit-fix, with your notes; D — stop here"


def build_gate_preview(project_dir: Path, gate_name: str = "next", explicit_spec: str | None = None) -> dict[str, Any]:
    """Return compact, copy-safe ReviewGate preview refs.

    This helper exists so Producer does not hand-assemble gate messages from
    full manifests or retype media URLs. It reads only the gate preview result
    manifests declared by the compiled route and copies selected_outputs refs.
    """
    project_dir = project_dir.expanduser().resolve()
    route = load_route(project_dir, explicit_spec=explicit_spec)
    if gate_name == "next":
        inferred = infer_next_goal(project_dir, include_gates=True, explicit_spec=explicit_spec)
        goal = inferred.get("next_goal")
        if not goal or goal not in route["review_gates"]:
            raise SystemExit(f"ERROR: next goal {goal!r} is not a ReviewGate")
        gate = route["review_gates"][goal]
    else:
        gate = resolve_gate(route, gate_name)
        goal = str(gate.get("goal"))

    preview_artifacts = as_list(gate.get("previews") or gate.get("reads"))
    preview_refs: list[dict[str, Any]] = []
    validation: list[dict[str, Any]] = []
    for artifact in preview_artifacts:
        path = rel(project_dir, artifact)
        if not path.exists():
            validation.append({"path": artifact, "ok": False, "error": "missing"})
            continue
        result = validate_artifact(project_dir, artifact)
        validation.append(result)
        if path.suffix.lower() == ".json":
            data = load_json(path)
            for item in data.get("selected_outputs", []) or []:
                if isinstance(item, dict):
                    preview_refs.append({k: item[k] for k in ("shot_id", "kind", "path", "url") if k in item})
        else:
            preview_refs.append({"path": artifact})

    return {
        "schema": "kinodel.gate_preview.v1",
        "project_id": project_id(project_dir),
        "project_dir": str(project_dir),
        "gate": gate.get("gate_alias"),
        "goal": goal,
        "label": gate.get("label") or str(goal),
        "preview_artifacts": preview_artifacts,
        "preview_refs": preview_refs,
        "validation": validation,
        "prompt": GATE_PROMPT,
        "stop": True,
    }


def sync_producer_state_with_resume(project_dir: Path, route: dict[str, Any], next_goal: str | None, complete: bool) -> dict[str, Any]:
    state = load_producer_state(project_dir)
    if not state:
        return {}
    changed = False
    desired_goal = str(next_goal) if next_goal else None
    desired_cursor = goal_cursor(route, desired_goal)
    if state.get("current_goal") != desired_goal:
        state["current_goal"] = desired_goal
        changed = True
    if state.get("stage_cursor") != desired_cursor:
        state["stage_cursor"] = desired_cursor
        changed = True
    if state.get("complete") != complete:
        state["complete"] = complete
        changed = True
    if complete:
        final_video = rel(project_dir, "outputs/final.mp4")
        completion = state.get("completion") if isinstance(state.get("completion"), dict) else {}
        completion.setdefault("completed_at", utc_now())
        completion["complete"] = True
        if final_video.exists():
            completion["final_video"] = "outputs/final.mp4"
        if state.get("completion") != completion:
            state["completion"] = completion
            changed = True
    if changed:
        state.setdefault("schema", PRODUCER_STATE_SCHEMA)
        state.setdefault("project_id", project_id(project_dir))
        if route.get("pipeline_id"):
            state.setdefault("pipeline_id", route.get("pipeline_id"))
        state["updated_at"] = utc_now()
        save_producer_state(project_dir, state)
    return state


def build_resume_report(project_dir: Path, explicit_spec: str | None = None) -> dict[str, Any]:
    project_dir = project_dir.expanduser().resolve()
    route = load_route(project_dir, explicit_spec=explicit_spec)
    next_info = infer_next_goal(project_dir, include_gates=True, explicit_spec=explicit_spec)
    next_goal = next_info.get("next_goal")
    pending_gate = None
    preview_artifacts: list[str] = []
    if next_goal and next_goal in route["review_gates"]:
        gate = route["review_gates"][next_goal]
        pending_gate = {k: gate.get(k) for k in ("goal", "gate_alias", "label", "gate_kind") if gate.get(k) is not None}
        preview_artifacts = [p for p in as_list(gate.get("previews") or gate.get("reads")) if rel(project_dir, p).exists()]
    elif next_goal and next_goal in route["delegated"]:
        preview_artifacts = [p for p in as_list(route["delegated"][next_goal].get("selected_from")) if rel(project_dir, p).exists()]

    complete = next_goal is None
    state = sync_producer_state_with_resume(project_dir, route, str(next_goal) if next_goal else None, complete) or load_producer_state(project_dir)
    if pending_gate:
        next_action = "show_review_gate"
    elif complete:
        next_action = "complete"
    elif next_goal in route["delegated"]:
        next_action = "delegate_stage"
    elif next_goal in route["render_stages"]:
        next_action = "render_stage"
    else:
        next_action = "handle_in_producer"

    return {
        "project_id": project_id(project_dir),
        "project_dir": str(project_dir),
        "pipeline_id": route.get("pipeline_id"),
        "state_current_goal": state.get("current_goal"),
        "state_stage_cursor": state.get("stage_cursor"),
        "next_goal": next_goal,
        "reason": next_info.get("reason"),
        "stop": bool(next_info.get("stop")),
        "complete": complete,
        "completed_goals": completed_goals(project_dir, route),
        "pending_gate": pending_gate,
        "preview_artifacts": preview_artifacts,
        "next_action": next_action,
    }


def discover_project_dirs(root: Path) -> list[Path]:
    root = root.expanduser().resolve()
    if not root.exists():
        return []
    candidates: list[Path] = []
    for path in root.rglob("brief.json"):
        if path.parent.name == "v1":
            candidates.append(path.parent)
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)


def compact_project_report(report: dict[str, Any]) -> dict[str, Any]:
    pending_gate = report.get("pending_gate")
    if isinstance(pending_gate, dict):
        pending_gate_value = pending_gate.get("gate_alias") or pending_gate.get("goal")
    else:
        pending_gate_value = pending_gate
    return {
        "project_id": report.get("project_id"),
        "next_goal": report.get("next_goal"),
        "next_action": report.get("next_action"),
        "pending_gate": pending_gate_value,
    }


def list_projects(root: Path, unfinished_only: bool = False, limit: int | None = None, compact: bool = False) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for project_dir in discover_project_dirs(root):
        try:
            report = build_resume_report(project_dir)
        except SystemExit as exc:
            report = {"project_dir": str(project_dir), "project_id": project_dir.parent.name, "error": str(exc), "complete": False, "next_goal": None, "next_action": "inspect_error", "pending_gate": None}
        if unfinished_only and report.get("complete"):
            continue
        try:
            report["updated_mtime"] = project_dir.stat().st_mtime
        except OSError:
            pass
        items.append(compact_project_report(report) if compact else report)
        if limit and len(items) >= limit:
            break
    return items


def unapproved_prior_gates(project_dir: Path, route: dict[str, Any], goal: str) -> list[dict[str, Any]]:
    if not route.get("spec_based"):
        return []
    ordered = route["ordered_goals"]
    if goal not in ordered:
        return []
    target_index = ordered.index(goal)
    gates = route["review_gates"]
    blocked: list[dict[str, Any]] = []
    for prior_goal in ordered[:target_index]:
        gate = gates.get(prior_goal)
        if gate and not gate_is_approved(project_dir, gate):
            blocked.append(gate)
    return blocked


def build_handoff(project_dir: Path, goal: str, edit_notes: str | None = None, explicit_spec: str | None = None, chunk_paths: list[str] | None = None, context_pack_path: str | None = None) -> dict[str, Any]:
    route = load_route(project_dir, explicit_spec=explicit_spec)
    delegated = route["delegated"]
    spec = delegated.get(goal)
    if not spec:
        raise SystemExit(f"ERROR: unknown delegated goal {goal}; known: {', '.join(delegated)}")
    blocked_gates = unapproved_prior_gates(project_dir, route, goal)
    if blocked_gates:
        labels = [f"{g.get('goal')} ({g.get('gate_alias')})" for g in blocked_gates]
        raise SystemExit(f"ERROR: goal {goal} requires explicit approval for prior ReviewGate(s): {labels}")
    missing = [r for r in spec["read"] if not rel(project_dir, r).exists()]
    if missing:
        raise SystemExit(f"ERROR: missing required reads: {missing}")
    handoff = {
        "schema": "kinodel.delegate_handoff.v1",
        "contract": "producer.delegated_design_stage.v1",
        "project": {
            "id": project_id(project_dir),
            "dir": str(project_dir),
        },
        "artifacts": {
            "read": spec["read"],
            "write": spec["write"],
        },
        "stage": {
            "goal": goal,
            "owner_skill": spec.get("skill"),
            "support_skills": as_list(spec.get("support_skills")),
        },
        "selected_media": collect_selected(project_dir, spec["selected_from"]),
        "context_cache": compact_context_cache(project_dir, spec["read"]),
        "edit_notes": read_edit_notes(edit_notes),
        "context_policy": {
            "direct_chunks_are_primary": True,
            "semantic_rag_role": "optional inspiration/continuity support only",
            "render_must_not_query_rag": True,
            "active_project_artifacts_override_indexed_memory": True,
        },
    }
    if chunk_paths:
        handoff["selected_chunks"] = [
            {
                "artifact_path": str(Path(p).expanduser()),
                "handoff_mode": "direct_selected_chunk",
                "use_as": "mandatory known context or explicitly selected inspiration/continuity support",
                "source_of_truth": "durable crafted chunk artifact; active project artifacts still win conflicts",
            }
            for p in chunk_paths
        ]
    if context_pack_path:
        context_pack = Path(context_pack_path).expanduser()
        if not context_pack.exists():
            raise SystemExit(f"ERROR: context pack path does not exist: {context_pack}")
        handoff["context_pack"] = {
            "path": str(context_pack),
            "source_of_truth": "derived_per_run_cache",
            "use_as": "compact selected support only; never a durable canon artifact",
            "broad_rag_forbidden_for_render": True,
        }
    return handoff


def is_complete(project_dir: Path, artifact: str) -> bool:
    path = rel(project_dir, artifact)
    if not path.exists():
        return False
    result = validate_artifact(project_dir, artifact)
    return bool(result.get("ok"))


def infer_next_goal(project_dir: Path, include_gates: bool = True, explicit_spec: str | None = None) -> dict[str, Any]:
    if not rel(project_dir, "brief.json").exists():
        return {"next_goal": "p0_briefgate", "reason": "missing brief.json", "stop": True}
    route = load_route(project_dir, explicit_spec=explicit_spec)
    if route.get("spec_based"):
        for goal in route["ordered_goals"][1:]:
            gate = route["review_gates"].get(goal)
            if gate:
                if include_gates and not gate_is_approved(project_dir, gate):
                    return {
                        "next_goal": goal,
                        "reason": f"{goal} requires explicit approval before downstream stages",
                        "stop": True,
                        "gate_alias": gate.get("gate_alias"),
                    }
                continue
            artifact = route["exit_artifacts"].get(goal)
            if artifact and not is_complete(project_dir, artifact):
                return {"next_goal": goal, "reason": f"{artifact} missing or invalid", "stop": False}
        return {"next_goal": None, "reason": "pipeline complete", "stop": False}

    for goal in GOAL_ORDER[1:]:
        if goal in REVIEW_GATES:
            if include_gates:
                gate = compile_legacy_route()["review_gates"].get(goal, {"goal": goal, "gate_alias": goal.split("_", 1)[0]})
                if not gate_is_approved(project_dir, gate):
                    if goal == "p4_story_main_gate" and is_complete(project_dir, "render_results/main_frame_result.json") and not is_complete(project_dir, "storyboard_requests.json"):
                        return {"next_goal": goal, "reason": "main frame rendered; awaiting p4 approval", "stop": True, "gate_alias": "p4"}
                    if goal == "p7_story_images_gate" and is_complete(project_dir, "render_results/story_frames_result.json") and not is_complete(project_dir, "video_requests.json"):
                        return {"next_goal": goal, "reason": "story images rendered; awaiting p7 approval", "stop": True, "gate_alias": "p7"}
                    if goal == "p12_final_gate" and is_complete(project_dir, "final_chunk.json"):
                        return {"next_goal": goal, "reason": "final video and final_chunk ready; awaiting final approval before RAG craft", "stop": True, "gate_alias": "p12"}
            continue
        artifact = GOAL_EXIT_ARTIFACT.get(goal)
        if artifact and not is_complete(project_dir, artifact):
            return {"next_goal": goal, "reason": f"{artifact} missing or invalid", "stop": False}
    return {"next_goal": None, "reason": "pipeline complete", "stop": False}


def cmd_summary(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    artifacts = [
        "brief.json", "story.json", "wardrobe_request.json", "storyboard_requests.json", "video_requests.json",
        "render_results/main_frame_result.json", "render_results/story_frames_result.json", "render_results/shot_videos_result.json",
        "final_chunk.json", "chunks/cinema_chunk.json",
    ]
    print(json.dumps({"project_id": project_id(project_dir), "artifacts": [validate_artifact(project_dir, a) for a in artifacts if rel(project_dir, a).exists()]}, ensure_ascii=False, indent=2))
    return 0


def inspect_artifact(project_dir: Path, artifact: str, compact: bool = False) -> dict[str, Any]:
    validation = validate_artifact(project_dir, artifact)
    if not compact or not artifact.endswith(".json") or not rel(project_dir, artifact).exists():
        return validation
    data = load_json(rel(project_dir, artifact))
    summary: dict[str, Any] = {"path": artifact, "ok": validation.get("ok", False), "schema": data.get("schema"), "stage": data.get("stage"), "status": data.get("status")}
    if artifact in REQUEST_ARTIFACTS:
        jobs = data.get("jobs")
        summary["jobs"] = len(jobs) if isinstance(jobs, list) else 0
        kinds = sorted({str(j.get("kind")) for j in jobs if isinstance(j, dict) and j.get("kind")}) if isinstance(jobs, list) else []
        if kinds:
            summary["kinds"] = kinds
    elif artifact in RESULT_ARTIFACTS:
        outs = data.get("selected_outputs")
        summary["selected_outputs"] = len(outs) if isinstance(outs, list) else 0
        summary["paths"] = [o.get("path") for o in outs if isinstance(o, dict) and o.get("path")] if isinstance(outs, list) else []
        if isinstance(data.get("source_request"), dict):
            summary["source_request"] = {k: data["source_request"].get(k) for k in ("artifact", "sha256", "snapshot_path") if data["source_request"].get(k)}
    if not validation.get("ok"):
        summary["errors"] = validation.get("errors") or validation.get("error")
    return summary


def cmd_validate(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    result = validate_artifact(project_dir, args.artifact)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


def cmd_inspect(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    result = inspect_artifact(project_dir, args.artifact, compact=args.compact)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


def cmd_next_goal(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    result = infer_next_goal(project_dir, include_gates=not args.skip_gates, explicit_spec=args.pipeline_spec)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_handoff(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    goal = args.goal
    if goal == "next":
        inferred = infer_next_goal(project_dir, explicit_spec=args.pipeline_spec)
        goal = inferred.get("next_goal")
        if not goal:
            raise SystemExit("ERROR: no next goal; pipeline appears complete")
        route = load_route(project_dir, explicit_spec=args.pipeline_spec)
        if goal not in route["delegated"]:
            raise SystemExit(f"ERROR: next goal {goal} is not delegatable; handle in Producer")
    handoff = build_handoff(project_dir, goal, args.edit_notes, explicit_spec=args.pipeline_spec, chunk_paths=args.chunk_path, context_pack_path=args.context_pack)
    print(json.dumps(handoff, ensure_ascii=False, indent=2))
    return 0


def cmd_approve_gate(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    result = approve_gate(project_dir, args.gate, decision=args.decision, source=args.source, explicit_spec=args.pipeline_spec)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_gate_preview(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    result = build_gate_preview(project_dir, gate_name=args.gate, explicit_spec=args.pipeline_spec)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    result = build_resume_report(project_dir, explicit_spec=args.pipeline_spec)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_list_projects(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    result = list_projects(root, unfinished_only=args.unfinished, limit=args.limit, compact=args.compact)
    print(json.dumps({"root": str(root), "projects": result}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("summary")
    s.add_argument("--project-dir", required=True)
    s.set_defaults(func=cmd_summary)
    v = sub.add_parser("validate")
    v.add_argument("--project-dir", required=True)
    v.add_argument("--artifact", required=True)
    v.set_defaults(func=cmd_validate)
    ins = sub.add_parser("inspect")
    ins.add_argument("--project-dir", required=True)
    ins.add_argument("--artifact", required=True)
    ins.add_argument("--compact", action="store_true")
    ins.set_defaults(func=cmd_inspect)
    n = sub.add_parser("next-goal")
    n.add_argument("--project-dir", required=True)
    n.add_argument("--skip-gates", action="store_true", help="DEBUG ONLY: infer next non-gate work item; never use for normal production because p4/p7 are hard stops")
    n.add_argument("--pipeline-spec", help="explicit pipeline_spec.v1 JSON path; Phase B diagnostic/compatibility input")
    n.set_defaults(func=cmd_next_goal)
    h = sub.add_parser("handoff")
    h.add_argument("--project-dir", required=True)
    h.add_argument("--goal", required=True, help="delegated goal name or 'next'")
    h.add_argument("--edit-notes", help="literal edit notes or a path to a notes file")
    h.add_argument("--chunk-path", action="append", help="selected crafted chunk artifact path to include in the handoff; repeatable")
    h.add_argument("--context-pack", help="optional resolver-created /tmp context_pack JSON path; derived cache, not canon")
    h.add_argument("--pipeline-spec", help="explicit pipeline_spec.v1 JSON path; Phase B diagnostic/compatibility input")
    h.set_defaults(func=cmd_handoff)
    a = sub.add_parser("approve-gate")
    a.add_argument("--project-dir", required=True)
    a.add_argument("--gate", required=True, help="gate goal or alias, e.g. p4 or p4_story_main_gate")
    a.add_argument("--decision", default="A", help="approving decision token; default A")
    a.add_argument("--source", default="user", help="decision source recorded in producer_state.json")
    a.add_argument("--pipeline-spec", help="explicit pipeline_spec.v1 JSON path; Phase B diagnostic/compatibility input")
    a.set_defaults(func=cmd_approve_gate)
    gp = sub.add_parser("gate-preview")
    gp.add_argument("--project-dir", required=True)
    gp.add_argument("--gate", default="next", help="gate goal/alias or next; default next")
    gp.add_argument("--pipeline-spec", help="explicit pipeline_spec.v1 JSON path; Phase B diagnostic/compatibility input")
    gp.set_defaults(func=cmd_gate_preview)
    r = sub.add_parser("resume")
    r.add_argument("--project-dir", required=True)
    r.add_argument("--pipeline-spec", help="explicit pipeline_spec.v1 JSON path; Phase B diagnostic/compatibility input")
    r.set_defaults(func=cmd_resume)
    lp = sub.add_parser("list-projects")
    lp.add_argument("--root", default=str(Path.home() / "projects"))
    lp.add_argument("--unfinished", action="store_true")
    lp.add_argument("--limit", type=int)
    lp.add_argument("--compact", action="store_true", help="return only first-contact fields: project_id, next_goal, next_action, pending_gate")
    lp.set_defaults(func=cmd_list_projects)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
