#!/usr/bin/env python3
"""Kinodel chunk resolver: direct loads + filters + FTS + mock-vector-ready context packs.

Phase RAG foundation intentionally keeps the resolver deterministic and safe. Render
workers must never call this. Resolver outputs selected chunk paths and, only when
requested, a disposable /tmp context pack.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

TOKEN_ESTIMATOR = Path.home() / ".hermes/skills/kinodel/craft-kinodel/scripts/estimate_chunk_tokens.py"
DEFAULT_DB = Path.home() / "chunk/indexes/kinodel_chunks.sqlite"
EMBED_PATH = Path.home() / ".hermes/skills/kinodel/pipeline-kinodel/scripts/embed_gemini.py"
_embed_spec = importlib.util.spec_from_file_location("embed_gemini", EMBED_PATH)
embed_gemini = importlib.util.module_from_spec(_embed_spec)
assert _embed_spec and _embed_spec.loader
_embed_spec.loader.exec_module(embed_gemini)
FORBIDDEN_STATUSES_AS_CANON = {"archived"}
FORBIDDEN_RUNTIME_KEYS = {"base64", "provider_payload", "queue_id", "callback_url", "raw_response", "retry_log", "cost_log"}


def estimate_text_tokens(text: str) -> int:
    return max(0, (len(text or "") + 3) // 4)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def flatten_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys = set(value.keys())
        for child in value.values():
            keys |= flatten_keys(child)
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for child in value:
            keys |= flatten_keys(child)
        return keys
    return set()


def chunk_from_artifact(path: Path) -> dict[str, Any]:
    """Project a direct *_chunk.json artifact into the resolver row shape.

    Direct paths are the Phase RAG mandatory-load path used by Producer/state_guard
    handoffs. They must work without a prebuilt SQLite index and must remain compact:
    only summary, retrieval_text, and bound media refs enter context packs.
    """
    chunk = load_json(path)
    bad = FORBIDDEN_RUNTIME_KEYS & flatten_keys(chunk)
    if bad:
        raise ValueError(f"{path}: forbidden provider/runtime/blob keys present: {sorted(bad)}")
    refs = ((chunk.get("references") or {}).get("items") or []) if isinstance(chunk.get("references"), dict) else []
    context = chunk.get("context") if isinstance(chunk.get("context"), dict) else {}
    scope = context.get("scope") if isinstance(context.get("scope"), dict) else {}
    required = ["schema", "chunk_id", "chunk_type", "title", "status", "retrieval_text"]
    missing = [key for key in required if not chunk.get(key)]
    if missing:
        raise ValueError(f"{path}: missing direct chunk fields: {', '.join(missing)}")
    return {
        "chunk_id": chunk["chunk_id"],
        "chunk_type": chunk["chunk_type"],
        "status": chunk["status"],
        "project_id": scope.get("project_id"),
        "season_id": scope.get("season_id"),
        "episode_id": scope.get("episode_id"),
        "title": chunk["title"],
        "summary": context.get("summary") or "",
        "retrieval_text": chunk["retrieval_text"],
        "artifact_path": str(path),
        "media_refs": refs,
        "mandatory": True,
        "source": "direct_chunk_path",
    }


def connect(db: Path) -> sqlite3.Connection:
    if not db.exists():
        raise SystemExit(f"ERROR: chunk index not found: {db}; run index_chunks.py first or use --self-test")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_chunks(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    out=[]
    for row in rows:
        item=dict(row)
        try:
            item["media_refs"] = json.loads(item.pop("media_refs_json", "[]") or "[]")
        except Exception:
            item["media_refs"] = []
        out.append(item)
    return out


def metadata_query(conn: sqlite3.Connection, *, project_id: str | None, chunk_types: list[str], statuses: list[str], limit: int, global_library: bool = False) -> list[dict[str, Any]]:
    clauses=["is_active=1"]
    params=[]
    if project_id and not global_library:
        clauses.append("(project_id=? OR project_id IS NULL)")
        params.append(project_id)
    if chunk_types:
        clauses.append("chunk_type IN (%s)" % ",".join("?" for _ in chunk_types))
        params.extend(chunk_types)
    if statuses:
        clauses.append("status IN (%s)" % ",".join("?" for _ in statuses))
        params.extend(statuses)
    sql="SELECT * FROM chunks WHERE " + " AND ".join(clauses) + " LIMIT ?"
    params.append(limit)
    return rows_to_chunks(list(conn.execute(sql, params)))


def chunks_by_ids(conn: sqlite3.Connection, ids: list[str]) -> list[dict[str, Any]]:
    if not ids:
        return []
    rows: list[sqlite3.Row] = []
    for cid in ids:
        row = conn.execute("SELECT * FROM chunks WHERE chunk_id=? AND is_active=1", (cid,)).fetchone()
        if row is not None:
            rows.append(row)
    return rows_to_chunks(rows)


def fts_query(conn: sqlite3.Connection, query: str, limit: int) -> list[str]:
    if not query.strip():
        return []
    # Safe simple term search with prefix expansion, so "surf" can find "surfing".
    tokens = [re.sub(r"[^\w-]+", "", t, flags=re.UNICODE) for t in query.split()[:12]]
    tokens = [t for t in tokens if t]
    terms = " OR ".join(f'"{t.replace(chr(34), chr(34)*2)}" OR {t.replace(chr(34), "") }*' for t in tokens)
    if not terms:
        return []
    try:
        rows = conn.execute("SELECT chunk_id FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?", (terms, limit)).fetchall()
        return [str(r[0]) for r in rows]
    except sqlite3.OperationalError:
        return []


def rrf_merge(metadata_chunks: list[dict[str, Any]], fts_ids: list[str], vector_chunks: list[dict[str, Any]] | None = None, fts_chunks: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    scores: dict[str, float] = {}
    by_id: dict[str, dict[str, Any]] = {}
    for rank, chunk in enumerate(metadata_chunks, start=1):
        cid=str(chunk["chunk_id"])
        by_id[cid]=chunk
        scores[cid]=scores.get(cid,0.0)+1.0/(60+rank)
    for rank, chunk in enumerate(vector_chunks or [], start=1):
        cid=str(chunk["chunk_id"])
        by_id[cid]=chunk
        scores[cid]=scores.get(cid,0.0)+1.0/(60+rank)
    for rank, chunk in enumerate(fts_chunks or [], start=1):
        cid=str(chunk["chunk_id"])
        by_id[cid]=chunk
        scores[cid]=scores.get(cid,0.0)+1.0/(60+rank)
    for rank, cid in enumerate(fts_ids, start=1):
        scores[cid]=scores.get(cid,0.0)+1.0/(60+rank)
    return [by_id[cid] for cid,_ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True) if cid in by_id]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    denom = math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(y*y for y in b))
    if not denom:
        return -1.0
    return sum(x*y for x, y in zip(a, b)) / denom


def _embedding_mock_columns(conn: sqlite3.Connection) -> bool:
    return "is_mock" in {row[1] for row in conn.execute("PRAGMA table_info(embedding_records)")}


def vector_query(conn: sqlite3.Connection, *, query: str, consumer_agent: str, project_id: str | None, chunk_types: list[str], statuses: list[str], profile: str, limit: int, allow_mock_vectors: bool, global_library: bool) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    dim = embed_gemini.PROFILE_DIMS.get(profile)
    if not dim:
        raise ValueError(f"unknown profile {profile!r}")
    has_mock_col = _embedding_mock_columns(conn)
    clauses = ["c.is_active=1", "e.profile=?", "e.dim=?"]
    params: list[Any] = [profile, dim]
    if has_mock_col and not allow_mock_vectors:
        clauses.append("e.is_mock=0")
    if project_id and not global_library:
        clauses.append("(c.project_id=? OR c.project_id IS NULL)")
        params.append(project_id)
    if chunk_types:
        clauses.append("c.chunk_type IN (%s)" % ",".join("?" for _ in chunk_types))
        params.extend(chunk_types)
    if statuses:
        clauses.append("c.status IN (%s)" % ",".join("?" for _ in statuses))
        params.extend(statuses)
    sql = f"""
      SELECT c.*, v.embedding_json, {('e.is_mock' if has_mock_col else '1')} AS is_mock
      FROM chunks c
      JOIN embedding_records e ON e.chunk_id=c.chunk_id
      JOIN chunk_vec_{dim} v ON v.chunk_id=c.chunk_id
      WHERE {' AND '.join(clauses)}
    """
    rows = list(conn.execute(sql, params))
    if not rows:
        return []
    formatted = embed_gemini.format_query(consumer_agent, query, f"profile={profile}; chunk_types={','.join(chunk_types) or 'any'}; statuses={','.join(statuses) or 'any'}")
    q = embed_gemini.embed_text(formatted, profile=profile, mock=allow_mock_vectors and all(int(dict(r).get("is_mock", 0)) for r in rows))["embedding"]
    scored=[]
    for row in rows:
        item=dict(row)
        try:
            vec=json.loads(item.pop("embedding_json") or "[]")
            item["media_refs"] = json.loads(item.pop("media_refs_json", "[]") or "[]")
        except Exception:
            continue
        item["vector_score"] = cosine(q, vec)
        item["source"] = "vector"
        scored.append(item)
    scored.sort(key=lambda c: c.get("vector_score", -1.0), reverse=True)
    return scored[:limit]


def merge_direct_first(direct_chunks: list[dict[str, Any]], ranked_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mandatory direct chunks win ties and are never duplicated by indexed candidates."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for chunk in direct_chunks + ranked_chunks:
        cid = str(chunk.get("chunk_id") or "")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        out.append(chunk)
    return out


def policy_filter(chunks: list[dict[str, Any]], *, allow_archived: bool = False, future_as_facts: bool = False) -> list[dict[str, Any]]:
    filtered=[]
    for chunk in chunks:
        status=str(chunk.get("status") or "")
        if status == "archived" and not allow_archived:
            continue
        if status == "planned" and future_as_facts:
            # Caller requested fact context; planned chunks are not facts.
            continue
        filtered.append(chunk)
    return filtered


def select_budget(chunks: list[dict[str, Any]], max_context_tokens: int) -> tuple[list[dict[str, Any]], int]:
    selected=[]
    total=0
    for chunk in chunks:
        projection = str(chunk.get("summary") or "") + "\n" + str(chunk.get("retrieval_text") or "")
        tokens=estimate_text_tokens(projection)
        if total + tokens > max_context_tokens:
            if chunk.get("mandatory"):
                raise ValueError(f"mandatory chunk {chunk.get('chunk_id')} exceeds context budget: {total + tokens}>{max_context_tokens}")
            continue
        item=dict(chunk)
        item["estimated_tokens"] = tokens
        selected.append(item)
        total += tokens
    return selected, total


def build_context_pack(*, project_id: str, pipeline_id: str, goal: str, consumer_agent: str, query: str, chunks: list[dict[str, Any]], estimated_tokens: int, max_context_tokens: int) -> dict[str, Any]:
    direct=[]
    projected=[]
    media_refs=[]
    for c in chunks:
        direct.append({"chunk_id": c["chunk_id"], "artifact_path": c["artifact_path"], "handoff_mode": "direct_compact", "estimated_tokens": c.get("estimated_tokens", 0)})
        projected.append({"chunk_id": c["chunk_id"], "title": c.get("title"), "chunk_type": c.get("chunk_type"), "status": c.get("status"), "summary": c.get("summary"), "retrieval_text": c.get("retrieval_text")})
        media_refs.extend(c.get("media_refs") or [])
    return {
        "schema": "kinodel.context_pack.v1",
        "project_id": project_id,
        "pipeline_id": pipeline_id,
        "goal": goal,
        "consumer_agent": consumer_agent,
        "retrieval_profile": "default_rag",
        "source_of_truth": "chunks_only",
        "query": {"text": query, "filters": {}},
        "direct_chunks": direct,
        "projected_chunks": projected,
        "media_refs": media_refs,
        "token_budget": {"max_context_tokens": max_context_tokens, "estimated_context_tokens": estimated_tokens},
        "forbidden": ["do not treat future planned episodes as completed facts", "do not inline media blobs or provider logs"],
    }


def resolve(args: argparse.Namespace) -> dict[str, Any]:
    direct_chunks = []
    for raw_path in getattr(args, "chunk_path", None) or []:
        direct_chunks.append(chunk_from_artifact(Path(raw_path).expanduser().resolve()))

    metadata = []
    fts_ids = []
    vector_chunks = []
    fts_chunks = []
    db_path = Path(args.db).expanduser().resolve()
    conn = connect(db_path) if db_path.exists() else None
    if conn is None and not direct_chunks:
        raise SystemExit(f"ERROR: chunk index not found: {db_path}; run index_chunks.py first, pass --chunk-path, or use --self-test")

    chunk_types=[x.strip() for x in (args.chunk_types or "").split(",") if x.strip()]
    statuses=[x.strip() for x in (args.statuses or "approved,active,completed").split(",") if x.strip()]
    retrieval_mode = getattr(args, "retrieval_mode", "hybrid")
    if conn is not None:
        if retrieval_mode in ("fts", "hybrid"):
            metadata=[] if retrieval_mode == "fts" else metadata_query(conn, project_id=args.project_id, chunk_types=chunk_types, statuses=statuses, limit=args.limit, global_library=args.global_library)
            fts_ids=fts_query(conn, args.query or "", args.limit)
            fts_chunks=chunks_by_ids(conn, fts_ids)
            if chunk_types:
                fts_chunks=[c for c in fts_chunks if c.get("chunk_type") in chunk_types]
            if statuses:
                fts_chunks=[c for c in fts_chunks if c.get("status") in statuses]
            if args.project_id and not args.global_library:
                fts_chunks=[c for c in fts_chunks if c.get("project_id") in (args.project_id, None)]
        elif retrieval_mode == "direct":
            metadata=[]
        if retrieval_mode in ("vector", "hybrid"):
            vector_chunks=vector_query(conn, query=args.query or "", consumer_agent=args.consumer_agent, project_id=args.project_id, chunk_types=chunk_types, statuses=statuses, profile=args.profile, limit=args.limit, allow_mock_vectors=args.allow_mock_vectors, global_library=args.global_library)
    merged=rrf_merge(metadata, fts_ids, vector_chunks, fts_chunks)
    all_candidates=merge_direct_first(direct_chunks, merged)
    safe=policy_filter(all_candidates, allow_archived=args.allow_archived, future_as_facts=args.fact_context)
    selected, est=select_budget(safe, args.max_context_tokens)
    result={"ok": True, "retrieval_mode": getattr(args, "retrieval_mode", "hybrid"), "profile": getattr(args, "profile", "default_rag"), "selected_chunk_paths": [c["artifact_path"] for c in selected], "selected_chunk_ids": [c["chunk_id"] for c in selected], "estimated_context_tokens": est}
    if args.write_context_pack:
        run_id=args.run_id or str(int(time.time()))
        out=Path(args.context_pack_path) if args.context_pack_path else Path(f"/tmp/kinodel/{args.project_id}/{run_id}/context_pack.{args.consumer_agent}.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        pack=build_context_pack(project_id=args.project_id, pipeline_id=args.pipeline_id, goal=args.goal, consumer_agent=args.consumer_agent, query=args.query or "", chunks=selected, estimated_tokens=est, max_context_tokens=args.max_context_tokens)
        out.write_text(json.dumps(pack, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        result["context_pack_path"] = str(out)
    return result


def self_test() -> int:
    # Build a persistent mock fixture index, then resolve it with policy regressions.
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td)
        db=tmp/"idx.sqlite"
        indexer=Path.home()/".hermes/skills/kinodel/pipeline-kinodel/scripts/index_chunks.py"
        import subprocess
        subprocess.check_call([sys.executable, str(indexer), "--mock", "--fixtures", "--db", str(db)], stdout=subprocess.DEVNULL)

        conn=sqlite3.connect(db)
        conn.execute("""
          INSERT OR REPLACE INTO chunks(chunk_id, chunk_type, status, project_id, title, summary, retrieval_text, artifact_path, modality, media_refs_json, metadata_json, content_hash)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, ("avatar:fixture:archived:v1", "avatar_chunk", "archived", "fixture_project", "Archived Hero", "Archived ref", "archived identity should not be canon", str(tmp/"archived.json"), "image", "[]", "{}", "sha256:" + "1"*64))
        conn.execute("""
          INSERT OR REPLACE INTO chunks(chunk_id, chunk_type, status, project_id, title, summary, retrieval_text, artifact_path, modality, media_refs_json, metadata_json, content_hash)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, ("episode:fixture:planned:v1", "episode_chunk", "planned", "fixture_project", "Planned Episode", "Future setup only", "planned future episode foreshadowing not completed fact", str(tmp/"planned.json"), "text", "[]", "{}", "sha256:" + "2"*64))
        conn.execute("""
          INSERT OR REPLACE INTO chunks(chunk_id, chunk_type, status, project_id, title, summary, retrieval_text, artifact_path, modality, media_refs_json, metadata_json, content_hash)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, ("episode:fixture:completed:v1", "episode_chunk", "completed", "fixture_project", "Completed Episode", "Completed continuity", "completed episode continuity fact", str(tmp/"completed.json"), "text", "[]", "{}", "sha256:" + "3"*64))
        conn.commit()
        conn.close()

        # Happy path + context pack safety.
        ns=argparse.Namespace(db=str(db), project_id="fixture_project", pipeline_id="cinematic.v1", goal="p1_story", consumer_agent="wardrobe-kinodel", query="identity face", chunk_types="avatar_chunk", statuses="approved", limit=10, allow_archived=False, fact_context=False, max_context_tokens=1000, retrieval_mode="hybrid", profile="default_rag", allow_mock_vectors=True, global_library=False, write_context_pack=True, run_id="selftest", context_pack_path=str(tmp/"context_pack.json"))
        out=resolve(ns)
        assert out["selected_chunk_ids"] == ["avatar:fixture:hero:v1"]
        pack=load_json(tmp/"context_pack.json")
        assert pack["schema"] == "kinodel.context_pack.v1"
        blob=json.dumps(pack)
        for forbidden in ("base64", "provider_payload", "queue_id", "raw_response"):
            assert forbidden not in blob

        # Regression 1: archived excluded unless explicitly allowed.
        archived_ns=argparse.Namespace(db=str(db), project_id="fixture_project", pipeline_id="cinematic.v1", goal="p1_story", consumer_agent="wardrobe-kinodel", query="", chunk_types="avatar_chunk", statuses="approved,archived", limit=10, allow_archived=False, fact_context=False, max_context_tokens=1000, retrieval_mode="hybrid", profile="default_rag", allow_mock_vectors=True, global_library=False, write_context_pack=False, run_id=None, context_pack_path=None)
        archived_out=resolve(archived_ns)
        assert "avatar:fixture:archived:v1" not in archived_out["selected_chunk_ids"]
        assert "avatar:fixture:hero:v1" in archived_out["selected_chunk_ids"]

        # Regression 2: planned future episode excluded when caller requests fact context.
        planned_ns=argparse.Namespace(db=str(db), project_id="fixture_project", pipeline_id="cinematic.v1", goal="p1_story", consumer_agent="episode-kinodel", query="", chunk_types="episode_chunk", statuses="planned,completed", limit=10, allow_archived=False, fact_context=True, max_context_tokens=1000, retrieval_mode="hybrid", profile="default_rag", allow_mock_vectors=True, global_library=False, write_context_pack=False, run_id=None, context_pack_path=None)
        planned_out=resolve(planned_ns)
        assert "episode:fixture:planned:v1" not in planned_out["selected_chunk_ids"]
        assert "episode:fixture:completed:v1" in planned_out["selected_chunk_ids"]

        # Regression 3: direct mandatory chunk paths work without any SQLite index.
        direct_path = tmp / "direct_avatar_chunk.json"
        direct_path.write_text(json.dumps({
            "schema": "kinodel.avatar_chunk.v1",
            "chunk_id": "avatar:fixture:direct:v1",
            "chunk_type": "avatar_chunk",
            "title": "Direct Fixture Identity",
            "status": "approved",
            "context": {"summary": "Direct mandatory identity anchor.", "scope": {"project_id": "fixture_project"}, "canon_policy": "canon", "source_artifacts": []},
            "references": {"items": [{"handle": "@image1", "path": "refs/direct.png", "modality": "image", "role": "direct identity reference", "take": ["face"], "ignore": ["background"], "use_cases": ["wardrobe"], "priority": "P1", "consumers": ["wardrobe-kinodel"]}]},
            "action": {"consumer_tasks": ["preserve identity"], "instructions": ["use selected refs only"], "forbidden_uses": ["do not copy background"]},
            "focus": {"primary": "identity_lock", "must_preserve": ["face"], "must_not_drift": ["species"]},
            "timing": {"mode": "not_applicable", "reason": "static identity", "items": []},
            "retrieval_text": "Direct mandatory identity chunk for wardrobe handoff.",
            "embedding_profiles": ["default_rag"],
            "content_hash": "sha256:" + "4"*64,
            "craft": {"crafted_by": "craft-kinodel", "craft_version": "kinodel.craft.v1", "quality_checks": ["fixture"]},
        }, ensure_ascii=False), encoding="utf-8")
        direct_ns=argparse.Namespace(db=str(tmp/"missing.sqlite"), chunk_path=[str(direct_path)], project_id="fixture_project", pipeline_id="cinematic.v1", goal="p1_story", consumer_agent="wardrobe-kinodel", query="", chunk_types="avatar_chunk", statuses="approved", limit=10, allow_archived=False, fact_context=False, max_context_tokens=1000, retrieval_mode="hybrid", profile="default_rag", allow_mock_vectors=True, global_library=False, write_context_pack=True, run_id="direct", context_pack_path=str(tmp/"direct_context_pack.json"))
        direct_out=resolve(direct_ns)
        assert direct_out["selected_chunk_ids"] == ["avatar:fixture:direct:v1"]
        direct_pack=load_json(tmp/"direct_context_pack.json")
        assert direct_pack["direct_chunks"][0]["artifact_path"] == str(direct_path)
    print("chunk_resolver self-test: OK")
    return 0

def main() -> int:
    parser=argparse.ArgumentParser(description="Resolve Kinodel chunk context")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--chunk-path", action="append", help="Mandatory direct *_chunk.json path; repeatable. Works without an index DB.")
    parser.add_argument("--project-id", default="global")
    parser.add_argument("--pipeline-id", default="cinematic.v1")
    parser.add_argument("--goal", default="p1_story")
    parser.add_argument("--consumer-agent", default="producer-kinodel")
    parser.add_argument("--query", default="")
    parser.add_argument("--chunk-types", help="comma-separated chunk_type filter")
    parser.add_argument("--statuses", default="approved,active,completed")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--retrieval-mode", choices=["direct", "fts", "vector", "hybrid"], default="hybrid")
    parser.add_argument("--profile", default="default_rag", choices=sorted(embed_gemini.PROFILE_DIMS))
    parser.add_argument("--allow-mock-vectors", action="store_true", help="allow test/mock vectors; forbidden by default for production RAG")
    parser.add_argument("--global-library", action="store_true", help="do not clamp indexed retrieval to project_id")
    parser.add_argument("--max-context-tokens", type=int, default=6000)
    parser.add_argument("--allow-archived", action="store_true")
    parser.add_argument("--fact-context", action="store_true", help="exclude planned chunks because caller wants completed facts")
    parser.add_argument("--write-context-pack", action="store_true")
    parser.add_argument("--context-pack-path")
    parser.add_argument("--run-id")
    parser.add_argument("--self-test", action="store_true")
    args=parser.parse_args()
    if args.self_test:
        return self_test()
    print(json.dumps(resolve(args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
