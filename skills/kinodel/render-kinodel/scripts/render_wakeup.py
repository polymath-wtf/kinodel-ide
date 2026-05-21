#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


NEXT_ACTION = {
    "main_frame": "open_review_gate_p4_story_main_frame",
    "story_frames": "open_review_gate_p7_story_images",
    "shot_videos": "send_video_previews_then_run_montage",
    "montage": "send_final_video_then_write_final_chunk",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_last_event(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    last = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            last = json.loads(line)
    return last


def infer_stage(result: dict[str, Any], explicit: str | None) -> str:
    if explicit:
        return explicit
    jobs = result.get("jobs") if isinstance(result.get("jobs"), list) else []
    for job in jobs:
        stage = job.get("stage")
        if stage:
            return str(stage)
    return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--result-file", required=True)
    ap.add_argument("--events-file")
    ap.add_argument("--stage")
    args = ap.parse_args()

    result_path = Path(args.result_file)
    if not result_path.exists():
        print(json.dumps({"ready": False, "reason": "missing_result_file", "result_file": str(result_path)}, ensure_ascii=False))
        return 1

    result = load_json(result_path)
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    stage = infer_stage(result, args.stage)
    last_event = load_last_event(Path(args.events_file) if args.events_file else None)
    outputs = summary.get("outputs") or []
    failed = int(summary.get("failed") or 0)
    done = int(summary.get("done") or 0)

    print(json.dumps({
        "ready": summary.get("event_type") == "render_batch_terminal",
        "status": summary.get("status", "unknown"),
        "stage": stage,
        "next_action": NEXT_ACTION.get(stage, "inspect_result_file"),
        "done": done,
        "failed": failed,
        "outputs": outputs,
        "last_event": last_event,
        "gate_required": stage in ("main_frame", "story_frames"),
    }, ensure_ascii=False, indent=2))
    return 2 if failed and not done else 0


if __name__ == "__main__":
    raise SystemExit(main())
