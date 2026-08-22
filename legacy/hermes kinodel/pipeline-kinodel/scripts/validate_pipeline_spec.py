#!/usr/bin/env python3
"""Validate Kinodel pipeline_spec.v1 files.

Phase A validator: static schema/semantic checks only. It does not change or
execute Kinodel runtime behavior.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA = "kinodel.pipeline_spec.v1"
KNOWN_STAGE_TYPES = {
    "briefgate",
    "context_gate",
    "agent_stage",
    "render_stage",
    "review_gate",
    "montage_stage",
    "chunk_write_stage",
}
CINEMATIC_GOAL_ORDER = [
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
CINEMATIC_ARTIFACTS = {
    "brief.json",
    "story.json",
    "wardrobe_request.json",
    "render_results/main_frame_result.json",
    "storyboard_requests.json",
    "render_results/story_frames_result.json",
    "video_requests.json",
    "render_results/shot_videos_result.json",
    "outputs/final.mp4",
    "final_chunk.json",
    "chunks/cinema_chunk.json",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - exact parser message varies
        raise SystemExit(f"ERROR: cannot parse {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {path} must be a JSON object")
    return data


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def require_string_list(stage: dict[str, Any], key: str, errors: list[str], prefix: str) -> None:
    value = stage.get(key)
    if not isinstance(value, list):
        errors.append(f"{prefix}.{key} must be a list")
        return
    for index, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(f"{prefix}.{key}[{index}] must be a string")


def optional_string_list(stage: dict[str, Any], key: str, errors: list[str], prefix: str) -> None:
    if key in stage:
        require_string_list(stage, key, errors, prefix)


def validate_stage(stage: Any, index: int, errors: list[str]) -> str | None:
    prefix = f"stages[{index}]"
    if not isinstance(stage, dict):
        errors.append(f"{prefix} must be an object")
        return None

    goal = stage.get("goal")
    if not isinstance(goal, str) or not goal:
        errors.append(f"{prefix}.goal is required")
        goal = None

    stage_type = stage.get("type")
    if stage_type not in KNOWN_STAGE_TYPES:
        errors.append(f"{prefix}.type unknown: {stage_type!r}")

    require_string_list(stage, "reads", errors, prefix)
    require_string_list(stage, "writes", errors, prefix)
    optional_string_list(stage, "support_skills", errors, prefix)

    if stage_type == "agent_stage":
        if not stage.get("owner_skill"):
            errors.append(f"{prefix} agent_stage missing owner_skill")
        if not isinstance(stage.get("requires_capabilities"), list) or not stage.get("requires_capabilities"):
            errors.append(f"{prefix} agent_stage missing requires_capabilities")
        if not stage.get("validator"):
            errors.append(f"{prefix} agent_stage missing validator")

    elif stage_type == "render_stage":
        if not stage.get("request_artifact"):
            errors.append(f"{prefix} render_stage missing request_artifact")
        if not stage.get("result_artifact"):
            errors.append(f"{prefix} render_stage missing result_artifact")
        if not stage.get("modality"):
            errors.append(f"{prefix} render_stage missing modality")
        if not stage.get("adapter_profile"):
            errors.append(f"{prefix} render_stage missing adapter_profile")

    elif stage_type == "review_gate":
        if not stage.get("gate_alias"):
            errors.append(f"{prefix} review_gate missing gate_alias")
        if not stage.get("gate_kind"):
            errors.append(f"{prefix} review_gate missing gate_kind")
        if not stage.get("label"):
            errors.append(f"{prefix} review_gate missing label")
        if stage.get("stop") is not True:
            errors.append(f"{prefix} review_gate must declare stop: true")
        choices = stage.get("choices")
        if not isinstance(choices, list) or not set(["A", "B", "C", "D"]).issubset(set(map(str, choices))):
            errors.append(f"{prefix} review_gate choices must include A/B/C/D")

    elif stage_type == "montage_stage":
        if not stage.get("owner_skill"):
            errors.append(f"{prefix} montage_stage missing owner_skill")
        if not stage.get("validator"):
            errors.append(f"{prefix} montage_stage missing validator")

    elif stage_type == "chunk_write_stage":
        if not stage.get("chunk_type"):
            errors.append(f"{prefix} chunk_write_stage missing chunk_type")
        if not stage.get("validator"):
            errors.append(f"{prefix} chunk_write_stage missing validator")

    elif stage_type in {"briefgate", "context_gate"}:
        if not (stage.get("input_contract") or stage.get("validator")):
            errors.append(f"{prefix} {stage_type} missing input_contract or validator")

    return goal


def validate_cinematic(spec: dict[str, Any], errors: list[str]) -> None:
    stages = as_list(spec.get("stages"))
    goals = [stage.get("goal") for stage in stages if isinstance(stage, dict)]
    if goals != CINEMATIC_GOAL_ORDER:
        errors.append(f"cinematic.v1 goal order mismatch: {goals!r} != {CINEMATIC_GOAL_ORDER!r}")

    hard_aliases = set(map(str, as_list(spec.get("compatibility", {}).get("hard_gate_aliases"))))
    if not {"p4", "p7"}.issubset(hard_aliases):
        errors.append("cinematic.v1 compatibility.hard_gate_aliases must include p4 and p7")

    gate_by_alias = {
        stage.get("gate_alias"): stage
        for stage in stages
        if isinstance(stage, dict) and stage.get("type") == "review_gate"
    }
    for alias in ("p4", "p7"):
        gate = gate_by_alias.get(alias)
        if not gate:
            errors.append(f"cinematic.v1 missing review_gate with gate_alias {alias}")
        elif gate.get("stop") is not True:
            errors.append(f"cinematic.v1 gate {alias} must declare stop: true")

    artifacts: set[str] = set()
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        artifacts.update(x for x in as_list(stage.get("reads")) if isinstance(x, str))
        artifacts.update(x for x in as_list(stage.get("writes")) if isinstance(x, str))
        for key in ("request_artifact", "result_artifact"):
            if isinstance(stage.get(key), str):
                artifacts.add(stage[key])
    missing = sorted(CINEMATIC_ARTIFACTS - artifacts)
    if missing:
        errors.append(f"cinematic.v1 is missing legacy artifact(s): {missing}")


def validate_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if spec.get("schema") != EXPECTED_SCHEMA:
        errors.append(f"top-level schema must be {EXPECTED_SCHEMA!r}")
    if not spec.get("pipeline_id"):
        errors.append("missing pipeline_id")
    if not spec.get("display_name"):
        errors.append("missing display_name")
    if not isinstance(spec.get("version"), int):
        errors.append("version must be an integer")

    compatibility = spec.get("compatibility")
    if not isinstance(compatibility, dict):
        errors.append("compatibility must be an object")
    else:
        if "legacy_goal_aliases" not in compatibility:
            errors.append("compatibility.legacy_goal_aliases is required")
        if not isinstance(compatibility.get("hard_gate_aliases"), list):
            errors.append("compatibility.hard_gate_aliases must be a list")

    final_chunk = spec.get("final_chunk")
    if not isinstance(final_chunk, dict):
        errors.append("final_chunk must be an object")
    else:
        if not final_chunk.get("path"):
            errors.append("final_chunk.path is required")
        if not final_chunk.get("schema"):
            errors.append("final_chunk.schema is required")

    if not isinstance(spec.get("chunk_dependencies"), list):
        errors.append("chunk_dependencies must be a list")

    stages = spec.get("stages")
    if not isinstance(stages, list) or not stages:
        errors.append("stages must be a non-empty list")
        return errors

    seen: set[str] = set()
    for index, stage in enumerate(stages):
        goal = validate_stage(stage, index, errors)
        if goal:
            if goal in seen:
                errors.append(f"duplicate goal: {goal}")
            seen.add(goal)

    if spec.get("pipeline_id") == "cinematic.v1":
        validate_cinematic(spec, errors)

    return errors


def validate_file(path: Path) -> list[str]:
    return validate_spec(load_json(path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Kinodel pipeline_spec.v1 JSON file")
    parser.add_argument("spec", help="Path to pipeline spec JSON")
    args = parser.parse_args()

    path = Path(args.spec).expanduser().resolve()
    errors = validate_file(path)
    if errors:
        print(f"ERROR: {path} failed validation with {len(errors)} issue(s):")
        for error in errors:
            print(f"- {error}")
        return 2
    print(f"OK: {path} validates as kinodel.pipeline_spec.v1 ({load_json(path).get('pipeline_id')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
