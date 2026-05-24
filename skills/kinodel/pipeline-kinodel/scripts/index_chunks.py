#!/usr/bin/env python3
"""Index crafted Kinodel chunks into a local SQLite/FTS/mock-vector store.

Phase RAG foundation: dependency-light dry-run and fixture mode must work without
Gemini credentials or sqlite-vec. Real vector search can be upgraded behind the same
metadata/profile contract later.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
EMBED_PATH = SCRIPT_DIR / "embed_gemini.py"
spec = importlib.util.spec_from_file_location("embed_gemini", EMBED_PATH)
embed_gemini = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(embed_gemini)

VALIDATOR_PATH = SCRIPT_DIR / "validate_chunk_schema.py"
validator_spec = importlib.util.spec_from_file_location("validate_chunk_schema", VALIDATOR_PATH)
validate_chunk_schema = importlib.util.module_from_spec(validator_spec)
assert validator_spec and validator_spec.loader
validator_spec.loader.exec_module(validate_chunk_schema)

FORBIDDEN_KEYS = {"base64", "provider_payload", "queue_id", "raw_response", "retry_log", "cost_log", "callback_url"}
PROFILE_DIMS = embed_gemini.PROFILE_DIMS


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def flatten_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys = set(value.keys())
        for v in value.values():
            keys |= flatten_keys(v)
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys |= flatten_keys(item)
        return keys
    return set()


def chunk_scope(chunk: dict[str, Any]) -> dict[str, Any]:
    context = chunk.get("context") if isinstance(chunk.get("context"), dict) else {}
    scope = context.get("scope") if isinstance(context.get("scope"), dict) else {}
    return scope


def validate_chunk_minimal(chunk: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    required = ["schema", "chunk_id", "chunk_type", "title", "status", "context", "references", "action", "focus", "timing", "retrieval_text", "embedding_profiles", "content_hash", "craft"]
    for key in required:
        if key not in chunk:
            errors.append(f"{path}: missing {key}")
    bad = FORBIDDEN_KEYS & flatten_keys(chunk)
    if bad:
        errors.append(f"{path}: forbidden provider/runtime/blob keys present: {sorted(bad)}")
    refs = ((chunk.get("references") or {}).get("items") or []) if isinstance(chunk.get("references"), dict) else []
    for idx, ref in enumerate(refs):
        if not isinstance(ref, dict):
            errors.append(f"{path}: references.items[{idx}] is not object")
            continue
        for field in ("handle", "modality", "role", "take", "ignore", "use_cases", "priority"):
            if not ref.get(field):
                errors.append(f"{path}: ref[{idx}] missing {field}")
        if not (ref.get("path") or ref.get("url")):
            errors.append(f"{path}: ref[{idx}] missing path or url")
    return errors


def validate_chunk(chunk: dict[str, Any], path: Path) -> list[str]:
    """Validate against JSON Schema, then keep minimal guard as a safety net."""
    errors = validate_chunk_schema.validate_document(chunk, path)
    for err in validate_chunk_minimal(chunk, path):
        if err not in errors:
            errors.append(err)
    return errors


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS chunks (
      chunk_id TEXT PRIMARY KEY,
      chunk_type TEXT NOT NULL,
      status TEXT NOT NULL,
      project_id TEXT,
      season_id TEXT,
      episode_id TEXT,
      version INTEGER DEFAULT 1,
      is_active INTEGER DEFAULT 1,
      title TEXT,
      summary TEXT,
      retrieval_text TEXT NOT NULL,
      artifact_path TEXT NOT NULL,
      global_path TEXT,
      modality TEXT NOT NULL DEFAULT 'mixed',
      media_refs_json TEXT NOT NULL DEFAULT '[]',
      metadata_json TEXT NOT NULL DEFAULT '{}',
      content_hash TEXT NOT NULL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
      chunk_id UNINDEXED, title, summary, retrieval_text, chunk_type UNINDEXED,
      project_id UNINDEXED, season_id UNINDEXED, episode_id UNINDEXED
    );
    CREATE TABLE IF NOT EXISTS embedding_records (
      chunk_id TEXT NOT NULL,
      profile TEXT NOT NULL,
      dim INTEGER NOT NULL,
      model TEXT NOT NULL,
      format_version TEXT NOT NULL,
      embedded_at TEXT DEFAULT CURRENT_TIMESTAMP,
      content_hash TEXT NOT NULL,
      vector_sha256 TEXT NOT NULL,
      is_mock INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY (chunk_id, profile)
    );
    """)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(embedding_records)")}
    if "is_mock" not in cols:
        conn.execute("ALTER TABLE embedding_records ADD COLUMN is_mock INTEGER NOT NULL DEFAULT 1")
    for dim in (256, 768, 1536, 3072):
        conn.execute(f"CREATE TABLE IF NOT EXISTS chunk_vec_{dim} (chunk_id TEXT PRIMARY KEY, embedding_json TEXT NOT NULL)")


def index_chunk(conn: sqlite3.Connection, chunk: dict[str, Any], path: Path, *, mock: bool = True) -> list[dict[str, Any]]:
    scope = chunk_scope(chunk)
    refs = ((chunk.get("references") or {}).get("items") or []) if isinstance(chunk.get("references"), dict) else []
    modalities = sorted({str(r.get("modality")) for r in refs if isinstance(r, dict) and r.get("modality")}) or ["mixed"]
    summary = str((chunk.get("context") or {}).get("summary") or "")
    conn.execute("""
      INSERT OR REPLACE INTO chunks(chunk_id, chunk_type, status, project_id, season_id, episode_id, title, summary, retrieval_text, artifact_path, modality, media_refs_json, metadata_json, content_hash)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (chunk["chunk_id"], chunk["chunk_type"], chunk["status"], scope.get("project_id"), scope.get("season_id"), scope.get("episode_id"), chunk["title"], summary, chunk["retrieval_text"], str(path), "+".join(modalities), json.dumps(refs, ensure_ascii=False), json.dumps({"schema": chunk.get("schema")}, ensure_ascii=False), chunk["content_hash"]))
    conn.execute("DELETE FROM chunks_fts WHERE chunk_id=?", (chunk["chunk_id"],))
    conn.execute("INSERT INTO chunks_fts(chunk_id,title,summary,retrieval_text,chunk_type,project_id,season_id,episode_id) VALUES(?,?,?,?,?,?,?,?)", (chunk["chunk_id"], chunk["title"], summary, chunk["retrieval_text"], chunk["chunk_type"], scope.get("project_id"), scope.get("season_id"), scope.get("episode_id")))
    records=[]
    for profile in chunk.get("embedding_profiles") or ["default_rag"]:
        if profile not in PROFILE_DIMS:
            raise ValueError(f"unknown profile {profile!r} in {path}")
        dim = PROFILE_DIMS[profile]
        text = embed_gemini.format_document(chunk["title"], chunk["retrieval_text"])
        embedded = embed_gemini.embed_text(text, profile=profile, mock=mock)
        vector = embedded["embedding"]
        if int(embedded.get("dim", -1)) != dim or len(vector) != dim:
            raise ValueError(f"embedding dimension mismatch for {chunk['chunk_id']} profile {profile}: expected {dim}, got result_dim={embedded.get('dim')} len={len(vector)}")
        vector_sha = hashlib.sha256(json.dumps(vector, separators=(",", ":")).encode("utf-8")).hexdigest()
        conn.execute(f"INSERT OR REPLACE INTO chunk_vec_{dim}(chunk_id, embedding_json) VALUES(?,?)", (chunk["chunk_id"], json.dumps(vector)))
        conn.execute("INSERT OR REPLACE INTO embedding_records(chunk_id,profile,dim,model,format_version,content_hash,vector_sha256,is_mock) VALUES(?,?,?,?,?,?,?,?)", (chunk["chunk_id"], profile, dim, embed_gemini.MODEL, embed_gemini.FORMAT_VERSION, chunk["content_hash"], vector_sha, 1 if embedded.get("mock") else 0))
        records.append({"chunk_id": chunk["chunk_id"], "profile": profile, "dim": dim, "vector_sha256": vector_sha[:16], "is_mock": bool(embedded.get("mock"))})
    return records


def fixture_chunk(tmp: Path) -> Path:
    data = {
        "schema": "kinodel.avatar_chunk.v1",
        "chunk_id": "avatar:fixture:hero:v1",
        "chunk_type": "avatar_chunk",
        "title": "Fixture Hero Identity",
        "status": "approved",
        "context": {"summary": "Approved fixture identity anchor.", "scope": {"project_id": "fixture_project"}, "canon_policy": "canon", "source_artifacts": []},
        "references": {"items": [{"handle": "@image1", "path": "refs/hero.png", "modality": "image", "role": "front identity reference", "take": ["face shape"], "ignore": ["background"], "use_cases": ["wardrobe"], "priority": "P1", "consumers": ["wardrobe-kinodel"]}]},
        "action": {"consumer_tasks": ["preserve identity"], "instructions": ["use selected refs only"], "forbidden_uses": ["do not copy background"]},
        "focus": {"primary": "identity_lock", "must_preserve": ["face shape"], "must_not_drift": ["species"]},
        "timing": {"mode": "not_applicable", "reason": "static identity", "items": []},
        "retrieval_text": "Fixture hero identity anchor, face shape, wardrobe planning, approved canon.",
        "embedding_profiles": ["default_rag"],
        "content_hash": "sha256:" + hashlib.sha256(b"fixture").hexdigest(),
        "craft": {"crafted_by": "craft-kinodel", "craft_version": "kinodel.craft.v1", "quality_checks": ["fixture"]},
    }
    path = tmp / "avatar_fixture_chunk.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        good_path = fixture_chunk(tmp)
        good = load_json(good_path)
        assert validate_chunk(good, good_path) == []

        # provider/runtime key rejected before indexing
        bad_provider = json.loads(json.dumps(good))
        bad_provider["references"]["items"][0]["provider_payload"] = {"queue_id": "forbidden"}
        bad_provider_path = tmp / "bad_provider_chunk.json"
        bad_provider_path.write_text(json.dumps(bad_provider, ensure_ascii=False), encoding="utf-8")
        provider_errors = validate_chunk(bad_provider, bad_provider_path)
        assert provider_errors and "provider_payload" in "\n".join(provider_errors)

        # dimension/profile mismatch rejected even if the profile name is valid
        conn = sqlite3.connect(tmp / "idx.sqlite")
        init_db(conn)
        original_embed = embed_gemini.embed_text

        def wrong_dim_embed(text: str, *, profile: str = "default_rag", mock: bool = False, **kwargs: Any) -> dict[str, Any]:
            return {"model": embed_gemini.MODEL, "format_version": embed_gemini.FORMAT_VERSION, "profile": profile, "dim": 256, "embedding": [0.0] * 256, "mock": True}

        embed_gemini.embed_text = wrong_dim_embed
        try:
            try:
                index_chunk(conn, good, good_path, mock=True)
                raise AssertionError("dimension mismatch was not rejected")
            except ValueError as exc:
                assert "dimension mismatch" in str(exc)
        finally:
            embed_gemini.embed_text = original_embed
    print("index_chunks self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Index Kinodel crafted chunks")
    parser.add_argument("paths", nargs="*", help="Chunk JSON files")
    parser.add_argument("--db", default=str(Path.home() / "chunk/indexes/kinodel_chunks.sqlite"))
    parser.add_argument("--dry-run", action="store_true", help="Use temp DB and mock embeddings")
    parser.add_argument("--mock", action="store_true", help="Mock embeddings even with a persistent DB")
    parser.add_argument("--fixtures", action="store_true", help="Index built-in fixture chunks")
    parser.add_argument("--rebuild", action="store_true", help="delete existing persistent DB before indexing; ignored with --dry-run")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        paths = [Path(p).expanduser().resolve() for p in args.paths]
        if args.fixtures:
            paths.append(fixture_chunk(tmp))
        if not paths:
            parser.error("provide chunk paths or --fixtures")
        db_path = tmp / "kinodel_chunks.sqlite" if args.dry_run else Path(args.db).expanduser().resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if args.rebuild and not args.dry_run and db_path.exists():
            db_path.unlink()
        conn = sqlite3.connect(db_path)
        init_db(conn)
        all_errors=[]
        indexed=[]
        for path in paths:
            chunk = load_json(path)
            errors = validate_chunk(chunk, path)
            if errors:
                all_errors.extend(errors)
                continue
            indexed.extend(index_chunk(conn, chunk, path, mock=(args.dry_run or args.mock)))
        conn.commit()
        out = {"ok": not all_errors, "db": str(db_path), "dry_run": args.dry_run, "indexed": indexed, "errors": all_errors}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if not all_errors else 2


if __name__ == "__main__":
    sys.exit(main())
