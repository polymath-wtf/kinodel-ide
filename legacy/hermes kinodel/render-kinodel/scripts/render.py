#!/usr/bin/env python3
"""Kinodel render entrypoint.

Runs the generic provider-backed render worker for an explicit stage from one render request file.

Usage:
    python3 render.py --request-file /tmp/kinodel/requests.json --stage images --output-dir projects/.../v1/outputs
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def should_retry_result(result_file: Path) -> tuple[bool, str]:
    try:
        data = json.loads(result_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"could not read result file: {exc}"
    summary = data.get("summary") if isinstance(data, dict) else {}
    if not isinstance(summary, dict):
        return False, "missing summary"
    if summary.get("status") == "failed_preflight":
        return False, "preflight failure is not retryable"
    failed = int(summary.get("failed") or 0)
    if failed <= 0:
        return False, "no failed jobs"
    jobs = data.get("jobs") if isinstance(data, dict) else []
    if isinstance(jobs, list):
        for job in jobs:
            if not isinstance(job, dict) or job.get("status") != "failed":
                continue
            provider = str(job.get("provider") or "").lower()
            error = str(job.get("error") or "").lower()
            is_comfy = provider in {"comfyui", "local-comfyui"} or provider.startswith("comfyui:") or provider.startswith("local-comfyui:")
            if is_comfy and "timeout" in error:
                return False, "ComfyUI timeout is not auto-retryable; prompt may still exist in external queue"
    return True, f"{failed} failed job(s)"


def failed_job_summaries(result_file: Path) -> list[dict]:
    try:
        data = json.loads(result_file.read_text(encoding="utf-8"))
    except Exception:
        return []
    jobs = data.get("jobs") if isinstance(data, dict) else []
    if not isinstance(jobs, list):
        return []
    out = []
    for job in jobs:
        if isinstance(job, dict) and job.get("status") == "failed":
            out.append({
                "job_id": job.get("job_id"),
                "shot_id": job.get("shot_id"),
                "provider": job.get("provider"),
                "error": str(job.get("error") or "")[:600],
            })
    return out


def append_attempt_event(events_file: Path | None, event: dict) -> None:
    if not events_file:
        return
    try:
        events_file.parent.mkdir(parents=True, exist_ok=True)
        event.setdefault("created_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        with events_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-file", required=True, help="Temporary render request JSON")
    parser.add_argument("--result-file", help="Temporary render result JSON")
    parser.add_argument("--events-file", help="Optional JSONL event stream for wake-up/status consumers")
    parser.add_argument("--output-dir", required=True, help="Project outputs directory, e.g. ~/projects/<project_id>/v1/outputs")
    parser.add_argument("--stage", choices=("images", "videos"), required=True)
    parser.add_argument("--image-concurrency", type=int, default=6)
    parser.add_argument("--video-concurrency", type=int, default=4)
    parser.add_argument("--max-attempts", type=int, default=2, help="Total worker attempts for retryable partial failures. Reruns resume from result-file and only submit failed/missing jobs.")
    args = parser.parse_args()
    request_file = Path(args.request_file)
    result_file = Path(args.result_file) if args.result_file else request_file.with_name(request_file.stem + ".results.json")
    worker = Path(__file__).with_name("render_worker.py")
    current_request = request_file
    events_path = Path(args.events_file) if args.events_file else None
    cmd = [
        sys.executable,
        str(worker),
        "--request-file",
        str(current_request),
        "--result-file",
        str(result_file),
        "--stage",
        args.stage,
        "--output-dir",
        args.output_dir,
        "--image-concurrency",
        str(args.image_concurrency),
        "--video-concurrency",
        str(args.video_concurrency),
    ]
    if args.events_file:
        cmd.extend(["--events-file", args.events_file])

    max_attempts = max(1, int(args.max_attempts or 1))
    last_returncode = 0
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            print(f"render.py: retry attempt {attempt}/{max_attempts}; worker will resume from {result_file}", file=sys.stderr, flush=True)
        completed = subprocess.run(cmd)
        last_returncode = completed.returncode
        if completed.returncode == 0:
            return
        retry, reason = should_retry_result(result_file)
        failures = failed_job_summaries(result_file)
        append_attempt_event(events_path, {
            "event_type": "render_attempt_failed",
            "attempt": attempt,
            "max_attempts": max_attempts,
            "retrying": bool(retry and attempt < max_attempts),
            "reason": reason,
            "failed_jobs": failures,
        })
        if failures:
            compact = "; ".join(f"{f.get('job_id')}: {f.get('error')}" for f in failures[:3])
            print(f"render.py: attempt {attempt}/{max_attempts} failed jobs: {compact}", file=sys.stderr, flush=True)
        if not retry or attempt >= max_attempts:
            print(f"render.py: not retrying: {reason}", file=sys.stderr, flush=True)
            raise subprocess.CalledProcessError(completed.returncode, cmd)
        print(f"render.py: retrying partial failure: {reason}", file=sys.stderr, flush=True)
    if last_returncode:
        raise subprocess.CalledProcessError(last_returncode, cmd)

if __name__ == "__main__":
    main()
