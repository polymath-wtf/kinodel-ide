#!/usr/bin/env python3
"""Universal render→producer wake-up bridge for Kinodel.

Render owns provider execution and worker result files. When a background render
finishes, this script performs the universal handoff back to Producer:

1. verify the worker result exists and reached a terminal state;
2. promote compact refs into the durable project manifest with copy_worker_result.py;
3. validate the promoted artifact with producer-kinodel/state_guard.py;
4. ask producer-kinodel for the next step;
5. emit a machine-readable wake payload plus a human-facing notification.

This script is intentionally stage-agnostic. It does not know about p4/p7/p10 or
special-case video renders; Producer decides the next action from project state.
It does not run the Producer action loop itself. If autonomous continuation is
needed, a Hermes wake consumer must feed ``producer_agent_prompt`` into a new
agent turn in the target session/runtime.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
RENDER_SKILL_DIR = SCRIPT_DIR.parent
KINODEL_DIR = RENDER_SKILL_DIR.parent
PRODUCER_SCRIPT_DIR = KINODEL_DIR / "producer-kinodel" / "scripts"
COPY_WORKER_RESULT = SCRIPT_DIR / "copy_worker_result.py"
STATE_GUARD = PRODUCER_SCRIPT_DIR / "state_guard.py"
PRODUCER_STEP = PRODUCER_SCRIPT_DIR / "producer_step.py"
PRODUCER_NOTIFY = PRODUCER_SCRIPT_DIR / "producer_notify.py"

STAGE_TO_DEST = {
    "main_frame": "render_results/main_frame_result.json",
    "story_frames": "render_results/story_frames_result.json",
    "shot_videos": "render_results/shot_videos_result.json",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"ERROR: cannot parse {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {path} is not a JSON object")
    return data


def load_last_event(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    last: dict[str, Any] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                last = parsed
    return last


def infer_stage(result: dict[str, Any], explicit: str | None) -> str:
    if explicit:
        return explicit
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    stage = summary.get("stage")
    if stage:
        return str(stage)
    jobs = result.get("jobs") if isinstance(result.get("jobs"), list) else []
    for job in jobs:
        if isinstance(job, dict) and job.get("stage"):
            return str(job["stage"])
    return "unknown"


def worker_terminal_status(result: dict[str, Any]) -> tuple[bool, str, int, int]:
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    event_type = summary.get("event_type")
    status = str(summary.get("status") or "unknown")
    done = int(summary.get("done") or 0)
    failed = int(summary.get("failed") or 0)
    jobs = result.get("jobs") if isinstance(result.get("jobs"), list) else []
    if event_type == "render_batch_terminal":
        return True, status, done, failed
    if jobs and all(isinstance(j, dict) and j.get("status") in {"done", "failed", "cancelled"} for j in jobs):
        return True, status, done, failed
    return False, status, done, failed


def run_json(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, check=True, text=True, capture_output=True)
    stdout = proc.stdout.strip()
    if not stdout:
        return {}
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return {"stdout": stdout}
    return parsed if isinstance(parsed, dict) else {"stdout": stdout}


def run_text(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, check=True, text=True, capture_output=True)
    return proc.stdout


def build_producer_agent_prompt(wakeup: dict[str, Any]) -> str:
    """Build the self-contained prompt a Hermes wake consumer should enqueue.

    The prompt deliberately does not prescribe p-stage names such as p10_montage.
    Producer must inspect project state through its packaged scripts and decide
    the next action dynamically.
    """
    payload = json.dumps(wakeup, ensure_ascii=False, indent=2)
    return f"""Render completion event for Kinodel.

Load and follow the producer-kinodel skill. Treat this as a wake-up event, not as a user ReviewGate reply.

Project dir: {wakeup['project_dir']}
Completed render stage: {wakeup['stage']}

Wake payload:
```json
{payload}
```

Continue the Producer runtime-pipeline from durable project state:
1. Verify the promoted render artifact and project state using packaged producer-kinodel scripts.
2. Run the normal Producer hot path by calling producer_step.py for the project.
3. If the completed stage is `shot_videos`, first deliver the human-facing shot video MEDIA refs from the promoted manifest, then continue the returned Producer action. Do not silently skip the intermediate clips.
4. Execute the returned action loop as an LLM actor: delegate_stage via delegate_task, render_stage via background terminal notify_on_complete, show_gate by presenting media and stopping, complete by reporting completion.
5. Do not hardcode the next p-stage from this wake payload. Producer decides from files/state.
""".strip()


def build_wakeup(project_dir: Path, worker_result: Path, events_file: Path | None, stage: str | None, result_artifact: str | None) -> tuple[dict[str, Any], str]:
    if not worker_result.exists():
        raise SystemExit(f"ERROR: worker result missing: {worker_result}")
    result = load_json(worker_result)
    inferred_stage = infer_stage(result, stage)
    if inferred_stage not in STAGE_TO_DEST:
        raise SystemExit(f"ERROR: cannot promote unknown render stage: {inferred_stage}")

    terminal, status, done, failed = worker_terminal_status(result)
    if not terminal:
        raise SystemExit(f"ERROR: worker result is not terminal yet: status={status}")
    if failed and not done:
        raise SystemExit(f"ERROR: render worker failed all jobs: failed={failed}, done={done}")

    copy_cmd = [
        "python3", str(COPY_WORKER_RESULT),
        "--project-dir", str(project_dir),
        "--worker-result", str(worker_result),
        "--stage", inferred_stage,
    ]
    if result_artifact:
        copy_cmd.extend(["--result-file", str(project_dir / result_artifact if not Path(result_artifact).is_absolute() else Path(result_artifact))])
    copy_result = run_json(copy_cmd)

    durable_artifact = result_artifact or STAGE_TO_DEST[inferred_stage]
    validate_result = run_json([
        "python3", str(STATE_GUARD), "validate",
        "--project-dir", str(project_dir),
        "--artifact", durable_artifact,
    ])
    if not validate_result.get("ok"):
        raise SystemExit(f"ERROR: promoted render artifact failed validation: {json.dumps(validate_result, ensure_ascii=False)}")

    step = run_json(["python3", str(PRODUCER_STEP), "--project-dir", str(project_dir)])
    notification = run_text([
        "python3", str(PRODUCER_NOTIFY),
        "--project-dir", str(project_dir),
        "--completed-stage", inferred_stage,
    ])
    wakeup = {
        "schema": "kinodel.render_wakeup.v1",
        "ok": True,
        "project_dir": str(project_dir),
        "worker_result": str(worker_result),
        "events_file": str(events_file) if events_file else None,
        "stage": inferred_stage,
        "status": status,
        "done": done,
        "failed": failed,
        "last_event": load_last_event(events_file),
        "promotion": copy_result,
        "validation": validate_result,
        "producer_next": {
            "action": step.get("action"),
            "goal": step.get("goal") or (step.get("resume") or {}).get("next_goal"),
            "complete": bool((step.get("resume") or {}).get("complete")),
        },
    }
    wakeup["producer_agent_wake"] = {
        "required": step.get("action") not in {"show_gate", "complete", "blocked"},
        "mechanism": "enqueue producer_agent_prompt into a Hermes agent turn for this project/session",
        "reason": "terminal notify_on_complete only delivers stdout; it does not start an LLM tool loop",
    }
    wakeup["producer_agent_prompt"] = build_producer_agent_prompt(wakeup)
    return wakeup, notification


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--worker-result", required=True, help="/tmp/kinodel/.../results.json written by render.py")
    ap.add_argument("--events-file", help="optional render_events.jsonl for diagnostics")
    ap.add_argument("--stage", choices=sorted(STAGE_TO_DEST), help="durable render stage: main_frame/story_frames/shot_videos")
    ap.add_argument("--result-artifact", help="optional durable artifact path relative to project dir")
    ap.add_argument("--json-only", action="store_true", help="print machine-readable wakeup JSON instead of user-facing Producer notification")
    ap.add_argument("--prompt-only", action="store_true", help="print only the Hermes Producer agent wake prompt")
    args = ap.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    worker_result = Path(args.worker_result).expanduser().resolve()
    events_file = Path(args.events_file).expanduser().resolve() if args.events_file else None
    wakeup, notification = build_wakeup(project_dir, worker_result, events_file, args.stage, args.result_artifact)
    if args.prompt_only:
        print(wakeup["producer_agent_prompt"])
    elif args.json_only:
        print(json.dumps(wakeup, ensure_ascii=False, indent=2))
    else:
        print(notification, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
