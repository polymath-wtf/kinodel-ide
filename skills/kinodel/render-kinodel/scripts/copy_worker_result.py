#!/usr/bin/env python3
"""Copy compact render worker result into durable Kinodel render_results manifest.

The render worker writes temporary results under /tmp/kinodel/<project>/<run>/.
Producer should use this helper to promote only compact selected refs into:
  v1/render_results/main_frame_result.json
  v1/render_results/story_frames_result.json
  v1/render_results/shot_videos_result.json

Raw provider logs, queue IDs, events, attempts, and debug payloads remain scratch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

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


def project_id(project_dir: Path) -> str:
    brief = load_json(project_dir / "brief.json")
    pid = brief.get("project_id")
    if not pid:
        raise SystemExit("ERROR: brief.json has no project_id")
    return str(pid)


def file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def request_artifact_for_stage(stage: str) -> str | None:
    return {
        "main_frame": "wardrobe_request.json",
        "story_frames": "storyboard_requests.json",
        "shot_videos": "video_requests.json",
    }.get(stage)


def _job_lookup(worker_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    jobs = worker_result.get("jobs")
    if not isinstance(jobs, list):
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for job in jobs:
        if not isinstance(job, dict):
            continue
        for key in ("job_id", "output_path", "output_url"):
            value = job.get(key)
            if value:
                lookup[str(value)] = job
    return lookup


def normalize_selected_outputs(worker_result: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = worker_result.get("selected_outputs") or worker_result.get("outputs") or worker_result.get("results")
    if outputs is None and isinstance(worker_result.get("result"), dict):
        outputs = worker_result["result"].get("selected_outputs") or worker_result["result"].get("outputs")
    if outputs is None and isinstance(worker_result.get("summary"), dict):
        # render_worker.py writes its native worker result as {"summary": {"outputs": [...]}, "jobs": [...]}
        # before Producer promotes compact refs into durable render_results/*.json.
        outputs = worker_result["summary"].get("selected_outputs") or worker_result["summary"].get("outputs")
    if outputs is None and isinstance(worker_result.get("jobs"), list):
        outputs = [job for job in worker_result["jobs"] if isinstance(job, dict) and job.get("status") == "done"]
    if not isinstance(outputs, list) or not outputs:
        raise SystemExit("ERROR: worker result has no selected_outputs/outputs/results list")

    jobs_by_key = _job_lookup(worker_result)
    selected: list[dict[str, Any]] = []
    for i, item in enumerate(outputs):
        if not isinstance(item, dict):
            raise SystemExit(f"ERROR: output {i} is not object")
        url = item.get("url") or item.get("output_url") or item.get("media_url")
        path = item.get("path") or item.get("output_path") or item.get("file")
        if not path:
            raise SystemExit(f"ERROR: output {i} missing path/output_path/file")
        if not url:
            raise SystemExit(f"ERROR: output {i} missing url/output_url/media_url")

        source = item
        for key in (item.get("job_id"), path, url):
            if key and str(key) in jobs_by_key:
                source = {**jobs_by_key[str(key)], **item}
                break
        compact = {k: source[k] for k in ("shot_id", "kind") if k in source}
        compact["path"] = str(path)
        compact["url"] = str(url)
        selected.append(compact)
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--worker-result", required=True)
    parser.add_argument("--stage", required=True, choices=sorted(STAGE_TO_DEST))
    parser.add_argument("--result-file", help="override durable result file path")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    worker_result = load_json(Path(args.worker_result).expanduser().resolve())
    pid = project_id(project_dir)
    dest = Path(args.result_file).expanduser().resolve() if args.result_file else project_dir / STAGE_TO_DEST[args.stage]
    dest.parent.mkdir(parents=True, exist_ok=True)

    selected_outputs = normalize_selected_outputs(worker_result)
    summary = worker_result.get("summary") if isinstance(worker_result.get("summary"), dict) else {}
    request_artifact = request_artifact_for_stage(args.stage)
    current_request_sha = file_sha256(project_dir / request_artifact) if request_artifact else None
    source_request_sha = summary.get("request_sha256") or current_request_sha
    manifest = {
        "schema": "kinodel.render_result.v1",
        "project_id": pid,
        "status": "complete",
        "stage": args.stage,
        "selected_outputs": selected_outputs,
        "attempts": [],
        "selection_policy": "selected_outputs are current truth",
    }
    if request_artifact and source_request_sha:
        manifest["source_request"] = {
            "artifact": request_artifact,
            "sha256": source_request_sha,
        }
    dest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "result_file": str(dest), "selected_outputs": len(selected_outputs)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
