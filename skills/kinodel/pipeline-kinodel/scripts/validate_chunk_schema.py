#!/usr/bin/env python3
"""Validate Kinodel crafted chunks and resolver context packs against JSON Schema.

This is the strict pre-index / pre-handoff validator for Phase RAG foundation.
It uses jsonschema when available and falls back to a minimal structural validator so
dry-run deployments can still fail safely without optional dependencies.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
CONTRACTS_DIR = SCRIPT_DIR.parent / "contracts"
CHUNK_SCHEMA_DIR = CONTRACTS_DIR / "chunks"
CONTEXT_PACK_SCHEMA = CONTRACTS_DIR / "context_pack.schema.json"

FORBIDDEN_KEYS = {"base64", "provider_payload", "queue_id", "raw_response", "retry_log", "cost_log", "callback_url"}
CHUNK_SCHEMA_BY_SCHEMA = {
    "kinodel.avatar_chunk.v1": CHUNK_SCHEMA_DIR / "avatar_chunk.schema.json",
    "kinodel.music_chunk.v1": CHUNK_SCHEMA_DIR / "music_chunk.schema.json",
    "kinodel.season_chunk.v1": CHUNK_SCHEMA_DIR / "season_chunk.schema.json",
    "kinodel.episode_chunk.v1": CHUNK_SCHEMA_DIR / "episode_chunk.schema.json",
    "kinodel.cinema_chunk.v1": CHUNK_SCHEMA_DIR / "cinema_chunk.schema.json",
    "kinodel.section_chunk.v1": CHUNK_SCHEMA_DIR / "section_chunk.schema.json",
}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: JSON root must be an object")
    return data


def flatten_forbidden_paths(value: Any, prefix: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}"
            if key in FORBIDDEN_KEYS:
                found.append(child_path)
            found.extend(flatten_forbidden_paths(child, child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            found.extend(flatten_forbidden_paths(child, f"{prefix}[{idx}]"))
    return found


def _schema_for_document(doc: dict[str, Any]) -> Path:
    schema_name = doc.get("schema")
    if schema_name == "kinodel.context_pack.v1":
        return CONTEXT_PACK_SCHEMA
    if schema_name in CHUNK_SCHEMA_BY_SCHEMA:
        return CHUNK_SCHEMA_BY_SCHEMA[str(schema_name)]
    raise ValueError(f"unknown schema {schema_name!r}; known={sorted(CHUNK_SCHEMA_BY_SCHEMA) + ['kinodel.context_pack.v1']}")


def _minimal_validate(doc: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    schema_name = doc.get("schema")
    if schema_name == "kinodel.context_pack.v1":
        required = ["schema", "project_id", "pipeline_id", "goal", "consumer_agent", "retrieval_profile", "source_of_truth", "query", "direct_chunks", "projected_chunks", "media_refs", "token_budget", "forbidden"]
    else:
        required = ["schema", "chunk_id", "chunk_type", "title", "status", "context", "references", "action", "focus", "timing", "retrieval_text", "embedding_profiles", "content_hash", "craft"]
    for key in required:
        if key not in doc:
            errors.append(f"{path}: missing required field {key}")
    if schema_name not in CHUNK_SCHEMA_BY_SCHEMA and schema_name != "kinodel.context_pack.v1":
        errors.append(f"{path}: unknown schema {schema_name!r}")
    return errors


def validate_document(doc: dict[str, Any], path: Path | None = None) -> list[str]:
    """Return validation errors. Empty list means valid."""
    label = path or Path("<memory>")
    errors: list[str] = []
    forbidden_paths = flatten_forbidden_paths(doc)
    if forbidden_paths:
        errors.append(f"{label}: forbidden provider/runtime/blob keys present at {forbidden_paths}")

    try:
        schema_path = _schema_for_document(doc)
    except ValueError as exc:
        errors.append(f"{label}: {exc}")
        return errors + _minimal_validate(doc, label)

    try:
        import jsonschema
        from jsonschema import Draft202012Validator
    except Exception:
        return errors + _minimal_validate(doc, label)

    schema = load_json(schema_path)
    resolver = jsonschema.RefResolver(
        base_uri=(schema_path.parent.as_uri() + "/"),
        referrer=schema,
    )
    validator = Draft202012Validator(schema, resolver=resolver)
    for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
        instance_path = "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in err.path)
        schema_path_txt = "/".join(str(p) for p in err.schema_path)
        errors.append(f"{label}: {instance_path}: {err.message} (schema: {schema_path_txt})")
    return errors


def validate_path(path: Path) -> list[str]:
    return validate_document(load_json(path), path)


def _valid_fixture() -> dict[str, Any]:
    return {
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
        "content_hash": "sha256:" + "0" * 64,
        "craft": {"crafted_by": "craft-kinodel", "craft_version": "kinodel.craft.v1", "quality_checks": ["fixture"]},
    }


def self_test() -> int:
    good = _valid_fixture()
    assert validate_document(good) == []

    bad_provider = json.loads(json.dumps(good))
    bad_provider["references"]["items"][0]["provider_payload"] = {"queue_id": "nope"}
    errs = validate_document(bad_provider)
    assert errs and "provider_payload" in "\n".join(errs) and "queue_id" in "\n".join(errs)

    bad_profile = json.loads(json.dumps(good))
    bad_profile["embedding_profiles"] = ["bad_profile"]
    errs = validate_document(bad_profile)
    assert errs and "bad_profile" in "\n".join(errs)

    pack = {
        "schema": "kinodel.context_pack.v1",
        "project_id": "fixture_project",
        "pipeline_id": "cinematic.v1",
        "goal": "p1_story",
        "consumer_agent": "wardrobe-kinodel",
        "retrieval_profile": "default_rag",
        "source_of_truth": "chunks_only",
        "query": {"text": "identity", "filters": {}},
        "direct_chunks": [{"chunk_id": "avatar:fixture:hero:v1", "artifact_path": "/tmp/avatar.json"}],
        "projected_chunks": [],
        "media_refs": [],
        "token_budget": {"max_context_tokens": 1000, "estimated_context_tokens": 10},
        "forbidden": ["no provider logs"],
    }
    assert validate_document(pack) == []
    print("validate_chunk_schema self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Kinodel chunk/context_pack JSON schemas")
    parser.add_argument("paths", nargs="*", help="Chunk/context_pack JSON files to validate")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable result")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.paths:
        parser.error("provide JSON paths or --self-test")
    results = []
    ok = True
    for raw in args.paths:
        path = Path(raw).expanduser().resolve()
        errs = validate_path(path)
        ok = ok and not errs
        results.append({"path": str(path), "ok": not errs, "errors": errs})
    if args.json:
        print(json.dumps({"ok": ok, "results": results}, ensure_ascii=False, indent=2))
    else:
        for result in results:
            if result["ok"]:
                print(f"OK: {result['path']}")
            else:
                print(f"ERROR: {result['path']}")
                for err in result["errors"]:
                    print(f"  - {err}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
