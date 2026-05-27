#!/usr/bin/env python3
"""Packaged Kinodel Producer step planner.

This script keeps the main Producer hot path thin and machine-readable. It does
not execute creative work and it does not render; it returns the one next action
that the LLM/runner should perform.

Typical use:
  python producer_step.py --project-dir ~/projects/demo/v1

Actions:
- delegate_stage: call delegate_task with the static contract + handoff, then validate_after.
- render_stage: launch the returned self-contained render→promote→validate→notify command in background with notify_on_complete=true.
- show_gate: present the compact gate preview and stop.
- complete: project is complete.
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import state_guard  # noqa: E402

PRODUCER_SKILL_DIR = SCRIPT_DIR.parent
RENDER_SKILL_DIR = PRODUCER_SKILL_DIR.parent / "render-kinodel"
RENDER_ENTRYPOINT = RENDER_SKILL_DIR / "scripts" / "render.py"
RENDER_WAKEUP = RENDER_SKILL_DIR / "scripts" / "render_wakeup.py"
STATE_GUARD = SCRIPT_DIR / "state_guard.py"

DELEGATE_GOAL = "Execute one Kinodel delegated design stage from the authoritative handoff envelope."
DELEGATE_TOOLSETS = ["skills", "file", "terminal"]
DELEGATE_STATIC_CONTRACT = """Follow the Kinodel delegated design stage contract.

Static contract:
- Read the entire handoff envelope before acting.
- Load/follow exactly handoff.stage.owner_skill.
- If handoff.stage.support_skills is non-empty, load them after owner_skill and use them only as supporting guidance; owner_skill remains authoritative for outputs.
- Execute exactly handoff.stage.goal.
- Read only files listed in handoff.artifacts.read under handoff.project.dir.
- If handoff.selected_chunks or handoff.context_pack exist, treat them as compact support only: direct selected chunks are primary known context; semantic/indexed RAG is optional inspiration/continuity support and never overrides active project artifacts.
- Render stages must never query broad RAG; render receives only explicit request artifacts and selected media refs.
- Write exactly handoff.artifacts.write.
- If handoff.stage.owner_skill is craft-kinodel and goal is p13_cinema_chunk, run the packaged Craft entrypoint instead of hand-authoring JSON:
  python3 ~/.hermes/skills/kinodel/craft-kinodel/scripts/craft_cinema_chunk.py --project-dir <handoff.project.dir> --index --mock
  This creates chunks/cinema_chunk.json from final_chunk.json, attaches up to 6 image refs (main frame + story frames) by path/sha/mime metadata, and indexes text plus image attachment embeddings.
- Preserve handoff.project.id.
- Set status=complete in the written artifact.
- Do not include provider runtime fields, queue IDs, logs, retries, or costs.
- Do not read or scan outputs/ to infer state; use selected_media and render_results refs.
- `context_cache` carries tiny digests/summaries for high-reuse artifacts; it is a cache hint, not an authority. If writing an artifact, read the authoritative files from `artifacts.read` first.
- Return only {status, artifact_path, summary}.

Dynamic handoff envelope:
"""


def stage_arg_for_render(stage: dict[str, Any]) -> str:
    modality = str(stage.get("modality") or "").lower()
    if modality == "video":
        return "videos"
    return "images"


def shell_join(argv: list[str]) -> str:
    return " ".join(shlex.quote(str(x)) for x in argv)


def shell_chain(commands: list[list[str]]) -> str:
    return " && ".join(shell_join(cmd) for cmd in commands)


def build_render_action(project_dir: Path, route: dict[str, Any], goal: str) -> dict[str, Any]:
    stage = route["render_stages"][goal]
    request_artifact = str(stage["request_artifact"])
    result_artifact = str(stage["result_artifact"])
    validation = state_guard.validate_artifact(project_dir, request_artifact)
    if not validation.get("ok"):
        return {
            "schema": "kinodel.producer_step.v1",
            "action": "blocked",
            "reason": "render request artifact is missing or invalid",
            "goal": goal,
            "validate_before": validation,
        }

    project_id = state_guard.project_id(project_dir)
    run_id = f"{goal}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    runtime_dir = Path("/tmp") / "kinodel" / project_id / run_id
    worker_result = runtime_dir / "results.json"
    events_file = runtime_dir / "render_events.jsonl"
    render_argv = [
        "python3",
        str(RENDER_ENTRYPOINT),
        "--request-file",
        str(project_dir / request_artifact),
        "--result-file",
        str(worker_result),
        "--events-file",
        str(events_file),
        "--stage",
        stage_arg_for_render(stage),
        "--output-dir",
        str(project_dir / "outputs"),
    ]
    durable_stage = str(stage.get("result_artifact") or result_artifact).split("/")[-1].replace("_result.json", "")
    wakeup_argv = [
        "python3",
        str(RENDER_WAKEUP),
        "--project-dir",
        str(project_dir),
        "--worker-result",
        str(worker_result),
        "--events-file",
        str(events_file),
        "--stage",
        durable_stage,
        "--result-artifact",
        result_artifact,
    ]
    auto_wakeup_argv = ["bash", "-lc", shell_chain([render_argv, wakeup_argv])]
    return {
        "schema": "kinodel.producer_step.v1",
        "action": "render_stage",
        "goal": goal,
        "request_artifact": request_artifact,
        "result_artifact": result_artifact,
        "stage_arg": stage_arg_for_render(stage),
        "run_id": run_id,
        "runtime_dir": str(runtime_dir),
        "worker_result": str(worker_result),
        "events_file": str(events_file),
        "command_argv": auto_wakeup_argv,
        "command": shell_join(auto_wakeup_argv),
        "render_command_argv": render_argv,
        "render_command": shell_join(render_argv),
        "launch_mode": "background_notify_on_complete_autowakeup",
        "wakeup": {
            "wakeup_command_argv": wakeup_argv,
            "wakeup_command": shell_join(wakeup_argv),
            "validate_after": result_artifact,
            "resume_after": True,
        },
        "validate_before": validation,
    }


def build_delegate_action(project_dir: Path, goal: str, explicit_spec: str | None = None, edit_notes: str | None = None) -> dict[str, Any]:
    handoff = state_guard.build_handoff(project_dir, goal, edit_notes=edit_notes, explicit_spec=explicit_spec)
    artifact = handoff["artifacts"]["write"]
    action = {
        "schema": "kinodel.producer_step.v1",
        "action": "delegate_stage",
        "goal": goal,
        "owner_skill": handoff["stage"].get("owner_skill"),
        "artifact_path": str(project_dir / artifact),
        "validate_after": artifact,
        "delegate_task": {
            "goal": DELEGATE_GOAL,
            "toolsets": DELEGATE_TOOLSETS,
            "context": DELEGATE_STATIC_CONTRACT + json.dumps(handoff, ensure_ascii=False, indent=2),
            "return_shape": {"status": "complete|blocked|failed", "artifact_path": str(project_dir / artifact), "summary": "short"},
        },
        "handoff": handoff,
    }
    if handoff["stage"].get("owner_skill") == "craft-kinodel" and goal == "p13_cinema_chunk":
        action["delegate_task"]["goal"] = "Craft the completed project's cinema_chunk.json and index its text plus image attachments using the packaged craft-kinodel entrypoint."
        action["craft_command"] = shell_join([
            "python3",
            str(PRODUCER_SKILL_DIR.parent / "craft-kinodel" / "scripts" / "craft_cinema_chunk.py"),
            "--project-dir",
            str(project_dir),
            "--index",
            "--mock",
        ])
        action["delegate_task"]["context"] += "\n\nRequired packaged command for this Craft stage:\n" + action["craft_command"] + "\nReturn only status/path/index summary; do not paste full chunk JSON."
    return action


def build_step(project_dir: Path, explicit_spec: str | None = None, edit_notes: str | None = None) -> dict[str, Any]:
    project_dir = project_dir.expanduser().resolve()
    route = state_guard.load_route(project_dir, explicit_spec=explicit_spec)
    resume = state_guard.build_resume_report(project_dir, explicit_spec=explicit_spec)
    goal = resume.get("next_goal")
    if not goal:
        return {"schema": "kinodel.producer_step.v1", "action": "complete", "resume": resume}
    if goal in route["review_gates"]:
        return {
            "schema": "kinodel.producer_step.v1",
            "action": "show_gate",
            "goal": goal,
            "gate_preview": state_guard.build_gate_preview(project_dir, gate_name=str(goal), explicit_spec=explicit_spec),
            "resume": resume,
        }
    if goal in route["delegated"]:
        action = build_delegate_action(project_dir, str(goal), explicit_spec=explicit_spec, edit_notes=edit_notes)
        action["resume"] = resume
        return action
    if goal in route["render_stages"]:
        action = build_render_action(project_dir, route, str(goal))
        action["resume"] = resume
        return action
    return {
        "schema": "kinodel.producer_step.v1",
        "action": "handle_in_producer",
        "goal": goal,
        "reason": resume.get("reason"),
        "resume": resume,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--pipeline-spec", help="explicit pipeline_spec.v1 JSON path; diagnostic/compatibility input")
    parser.add_argument("--edit-notes", help="literal edit notes or a path to a notes file for delegated edit-fix loops")
    args = parser.parse_args()
    result = build_step(Path(args.project_dir), explicit_spec=args.pipeline_spec, edit_notes=args.edit_notes)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
