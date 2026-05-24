#!/usr/bin/env python3
"""Golden eval suite for Kinodel cinema chunk retrieval.

Runs against completed ~/projects/*/v1/chunks/cinema_chunk.json artifacts using a temporary
mock index by default, so it is safe without Gemini credentials. It verifies top-1/top-3,
policy filters, mock-vector blocking, and context budget behavior.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

INDEXER = Path.home() / ".hermes/skills/kinodel/pipeline-kinodel/scripts/index_chunks.py"
RESOLVER = Path.home() / ".hermes/skills/kinodel/producer-kinodel/scripts/chunk_resolver.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


resolver = load_module("chunk_resolver", RESOLVER)

GOLDEN_CASES = [
    ("cosmic surf", "cinema:space-surfing:v1"),
    ("VHS neural cybermonk", "cinema:quantum_neural_bugfix_vhs:v1"),
    ("kungfu dunk VHS basketball monk", "cinema:kungfu_dunk:v1"),
    ("goat parkour cliff wall run", "cinema:mountain-goat-parkour:v1"),
    ("goose decepticon robot transformation", "cinema:goose-decepticon:v1"),
    ("goose crumb steals life meme", "cinema:goose-meme:v1"),
    ("VHS cloud skateboard drift", "cinema:vhs-cloud-drift:v1"),
    ("sorceress crystalline tree magic spores", "cinema:magic_vibe_0511_2330:v1"),
    ("catan fantasy island RPG campaign", "cinema:catan-fantasy-rpg:v1"),
    ("peaceful mountain kung fu basketball tai chi", "cinema:peaceful-mountains-kungfu-basketball:v1"),
    ("masked urban acrobat neon web drone rescue", "cinema:spider_style_one_shot_test:v1"),
]


def discover_chunks() -> list[Path]:
    return sorted(Path.home().glob("projects/*/v1/chunks/cinema_chunk.json"))


def build_db(db: Path, chunks: list[Path]) -> None:
    cmd = [sys.executable, str(INDEXER), "--mock", "--rebuild", "--db", str(db)] + [str(p) for p in chunks]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL)


def ns(db: Path, **overrides: Any) -> argparse.Namespace:
    data = dict(
        db=str(db),
        chunk_path=None,
        project_id="global",
        pipeline_id="cinematic.v1",
        goal="p1_story",
        consumer_agent="producer-kinodel",
        query="",
        chunk_types="cinema_chunk",
        statuses="completed",
        limit=5,
        allow_archived=False,
        fact_context=False,
        max_context_tokens=6000,
        retrieval_mode="fts",
        profile="default_rag",
        allow_mock_vectors=False,
        global_library=True,
        write_context_pack=False,
        run_id=None,
        context_pack_path=None,
    )
    data.update(overrides)
    return argparse.Namespace(**data)


def insert_policy_fixtures(db: Path) -> None:
    conn = sqlite3.connect(db)
    rows = [
        ("cinema:archived-test:v1", "cinema_chunk", "archived", "global", "Archived Test", "archived cosmic surf decoy", "cosmic surf archived decoy must not appear", "/tmp/archived.json", "mixed", "[]", "{}", "sha256:" + "a" * 64),
        ("episode:planned-test:v1", "episode_chunk", "planned", "global", "Planned Test", "planned future fact decoy", "planned future completed fact decoy", "/tmp/planned.json", "text", "[]", "{}", "sha256:" + "b" * 64),
        ("episode:completed-test:v1", "episode_chunk", "completed", "global", "Completed Test", "completed fact", "completed episode continuity fact", "/tmp/completed.json", "text", "[]", "{}", "sha256:" + "c" * 64),
    ]
    for row in rows:
        conn.execute("""
          INSERT OR REPLACE INTO chunks(chunk_id, chunk_type, status, project_id, title, summary, retrieval_text, artifact_path, modality, media_refs_json, metadata_json, content_hash)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, row)
        conn.execute("INSERT INTO chunks_fts(chunk_id,title,summary,retrieval_text,chunk_type,project_id,season_id,episode_id) VALUES(?,?,?,?,?,?,?,?)", (row[0], row[4], row[5], row[6], row[1], row[3], None, None))
    conn.commit()
    conn.close()


def run_eval(db: Path) -> dict[str, Any]:
    cases = []
    top1 = 0
    top3 = 0
    for query, expected in GOLDEN_CASES:
        out = resolver.resolve(ns(db, query=query, limit=5, retrieval_mode="fts"))
        ids = out["selected_chunk_ids"]
        ok1 = bool(ids and ids[0] == expected)
        ok3 = expected in ids[:3]
        top1 += int(ok1)
        top3 += int(ok3)
        cases.append({"query": query, "expected": expected, "ids": ids[:5], "top1": ok1, "top3": ok3})

    insert_policy_fixtures(db)
    archived = resolver.resolve(ns(db, query="archived cosmic surf", statuses="completed,archived", allow_archived=False, retrieval_mode="fts"))
    planned = resolver.resolve(ns(db, query="planned future completed fact", chunk_types="episode_chunk", statuses="planned,completed", fact_context=True, retrieval_mode="fts"))
    vector_blocked = resolver.resolve(ns(db, query="cosmic surf", retrieval_mode="vector", allow_mock_vectors=False))
    budget = resolver.resolve(ns(db, query="VHS", retrieval_mode="fts", max_context_tokens=250, limit=10))

    policy = {
        "archived_excluded": "cinema:archived-test:v1" not in archived["selected_chunk_ids"],
        "planned_excluded_with_fact_context": "episode:planned-test:v1" not in planned["selected_chunk_ids"] and "episode:completed-test:v1" in planned["selected_chunk_ids"],
        "mock_vectors_blocked_without_flag": vector_blocked["selected_chunk_ids"] == [],
        "context_budget_respected": budget["estimated_context_tokens"] <= 250,
    }
    return {
        "ok": top1 == len(GOLDEN_CASES) and top3 == len(GOLDEN_CASES) and all(policy.values()),
        "top1": f"{top1}/{len(GOLDEN_CASES)}",
        "top3": f"{top3}/{len(GOLDEN_CASES)}",
        "cases": cases,
        "policy": policy,
        "budget_example": {"ids": budget["selected_chunk_ids"], "estimated_context_tokens": budget["estimated_context_tokens"]},
    }


def self_test() -> int:
    chunks = discover_chunks()
    if not chunks:
        raise SystemExit("ERROR: no cinema chunks found; run backfill_cinema_chunks.py first")
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "eval.sqlite"
        build_db(db, chunks)
        result = run_eval(db)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Kinodel chunk retrieval golden eval")
    parser.add_argument("--db", help="Use existing DB instead of temp mock rebuild")
    parser.add_argument("--self-test", action="store_true", help="Alias for default eval mode")
    args = parser.parse_args()
    if args.db:
        result = run_eval(Path(args.db).expanduser().resolve())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 2
    return self_test()


if __name__ == "__main__":
    raise SystemExit(main())
