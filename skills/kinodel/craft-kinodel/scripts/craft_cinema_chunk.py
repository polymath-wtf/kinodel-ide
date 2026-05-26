#!/usr/bin/env python3
"""Craft one project's cinema_chunk.json after final_chunk.json exists.

This is the Craft-owned packaged entrypoint Producer delegates after p11. It writes
v1/chunks/cinema_chunk.json from the approved final_chunk.json, validates schema/token
budget, and can optionally index the chunk plus its image attachments.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKFILL_PATH = SCRIPT_DIR / "backfill_cinema_chunks.py"
INDEXER_PATH = Path.home() / ".hermes/skills/kinodel/pipeline-kinodel/scripts/index_chunks.py"

spec = importlib.util.spec_from_file_location("backfill_cinema_chunks", BACKFILL_PATH)
backfill = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(backfill)


def run_index(chunk_path: Path, *, mock: bool, rebuild: bool = False) -> dict[str, Any]:
    argv = ["python3", str(INDEXER_PATH)]
    if mock:
        argv.append("--mock")
    if rebuild:
        argv.append("--rebuild")
    argv.append(str(chunk_path))
    proc = subprocess.run(argv, text=True, capture_output=True)
    try:
        parsed = json.loads(proc.stdout) if proc.stdout.strip() else None
    except Exception:
        parsed = None
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "command": argv,
        "stdout_json": parsed,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Craft a cinema_chunk.json for one Kinodel project")
    parser.add_argument("--project-dir", help="Path to ~/projects/<id>/v1")
    parser.add_argument("--force", action="store_true", help="overwrite existing/manual cinema_chunk.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--index", action="store_true", help="index crafted chunk and image attachments after writing")
    parser.add_argument("--mock", action="store_true", help="use mock embeddings for indexing")
    parser.add_argument("--rebuild-index", action="store_true", help="rebuild persistent index before indexing this chunk")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return backfill.self_test()
    if not args.project_dir:
        parser.error("--project-dir is required unless --self-test is used")

    project_dir = Path(args.project_dir).expanduser().resolve()
    final_path = project_dir / "final_chunk.json"
    if not final_path.exists():
        print(json.dumps({"ok": False, "status": "blocked", "error": f"missing {final_path}"}, ensure_ascii=False, indent=2))
        return 2
    result = backfill.process_one(final_path, force=args.force, dry_run=args.dry_run)
    out = {
        "schema": "kinodel.craft_cinema_chunk.result.v1",
        "ok": result.get("status") not in {"error", "skipped_manual_edit"},
        "project_dir": str(project_dir),
        "status": result.get("status"),
        "chunk_path": result.get("chunk_path"),
        "warnings": result.get("warnings") or [],
        "errors": result.get("errors") or [],
        "token_guard": result.get("token_guard"),
    }
    if args.index and out["ok"] and not args.dry_run:
        index_result = run_index(Path(str(result["chunk_path"])), mock=args.mock, rebuild=args.rebuild_index)
        out["index"] = index_result
        out["ok"] = bool(index_result.get("ok"))
        if not out["ok"]:
            out.setdefault("errors", []).append("index_chunks.py failed")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
