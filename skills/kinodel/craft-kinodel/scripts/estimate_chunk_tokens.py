#!/usr/bin/env python3
"""Estimate Kinodel chunk/context token budgets before RAG indexing or handoff.

This is intentionally dependency-light. It implements Gemini token-counting rules from
raw/rag/gemini-token-counter.md as a local guard. Exact Gemini count_tokens calls can be
added by callers when credentials are available, but this estimator should catch obvious
oversized chunks without network access.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

WARN_RETRIEVAL_TOKENS = 600
REJECT_RETRIEVAL_TOKENS = 1200
VAGUE_FILLER_TERMS = ("cinematic", "beautiful", "interesting")
FORBIDDEN_PHRASES = ("take everything from this image", "use everything from this image")


def estimate_text_tokens(text: str) -> int:
    """Gemini rough rule: 1 token ~= 4 characters."""
    return max(1, math.ceil(len(text or "") / 4)) if text else 0


def estimate_image_tokens(width: int | None = None, height: int | None = None) -> int:
    """Gemini rough image rule: <=384px both dimensions is 258 tokens; larger tile at 768x768."""
    if not width or not height:
        return 258
    if width <= 384 and height <= 384:
        return 258
    tiles = math.ceil(width / 768) * math.ceil(height / 768)
    return max(1, tiles) * 258


def estimate_audio_tokens(seconds: float) -> int:
    return int(math.ceil(max(0.0, seconds) * 32))


def estimate_video_tokens(seconds: float) -> int:
    return int(math.ceil(max(0.0, seconds) * 263))


def load_json(path: str) -> dict[str, Any]:
    with open(os.path.expanduser(path), "r", encoding="utf-8") as f:
        return json.load(f)


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(v) for v in value)
    return ""


def check_water_and_binding(chunk: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Cheap static checks for prompt-dump/filler and unbound refs."""
    warnings: list[str] = []
    errors: list[str] = []

    retrieval_text = chunk.get("retrieval_text") or ""
    text_blob = _flatten_text(chunk).lower()

    for phrase in FORBIDDEN_PHRASES:
        if phrase in text_blob:
            errors.append(f"forbidden vague media instruction: {phrase!r}")

    for term in VAGUE_FILLER_TERMS:
        if term in retrieval_text.lower():
            warnings.append(f"retrieval_text contains vague filler term; keep only if functionally specified: {term!r}")

    focus = chunk.get("focus") or {}
    if not focus.get("must_preserve"):
        warnings.append("focus.must_preserve is empty")
    if not focus.get("must_not_drift"):
        warnings.append("focus.must_not_drift is empty")

    refs = ((chunk.get("references") or {}).get("items") or [])
    seen_handles: set[str] = set()
    required_ref_fields = ("handle", "role", "take", "ignore", "use_cases", "priority")
    for idx, ref in enumerate(refs):
        handle = ref.get("handle")
        if handle in seen_handles:
            errors.append(f"duplicate ref handle: {handle}")
        if handle:
            seen_handles.add(handle)
        missing = [field for field in required_ref_fields if not ref.get(field)]
        if missing:
            errors.append(f"ref[{idx}] missing binding fields: {', '.join(missing)}")

    return warnings, errors


FORBIDDEN_RUNTIME_KEYS = {"base64", "provider_payload", "queue_id", "callback_url", "raw_response", "retry_log", "cost_log"}


def _flatten_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys = set(value.keys())
        for child in value.values():
            keys |= _flatten_keys(child)
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for child in value:
            keys |= _flatten_keys(child)
        return keys
    return set()


def estimate_chunk(chunk: dict[str, Any], allow_large_retrieval_text: bool = False) -> dict[str, Any]:
    retrieval_text = chunk.get("retrieval_text") or ""
    retrieval_tokens = estimate_text_tokens(retrieval_text)

    ref_tokens = 0
    refs = ((chunk.get("references") or {}).get("items") or [])
    for ref in refs:
        modality = ref.get("modality")
        meta = ref.get("metadata") or {}
        if modality == "image":
            ref_tokens += estimate_image_tokens(meta.get("width"), meta.get("height"))
        elif modality == "audio":
            ref_tokens += estimate_audio_tokens(float(meta.get("duration_sec") or 0))
        elif modality == "video":
            ref_tokens += estimate_video_tokens(float(meta.get("duration_sec") or 0))
        else:
            ref_tokens += estimate_text_tokens(" ".join(str(x) for x in [ref.get("role"), ref.get("take"), ref.get("ignore")]))

    errors: list[str] = []
    warnings: list[str] = []
    if retrieval_tokens > REJECT_RETRIEVAL_TOKENS:
        message = f"retrieval_text too large: {retrieval_tokens} tokens > {REJECT_RETRIEVAL_TOKENS}"
        if allow_large_retrieval_text:
            warnings.append(message + " (override enabled)")
        else:
            errors.append(message)
    elif retrieval_tokens > WARN_RETRIEVAL_TOKENS:
        warnings.append(f"retrieval_text large: {retrieval_tokens} tokens > {WARN_RETRIEVAL_TOKENS}")

    forbidden_keys = FORBIDDEN_RUNTIME_KEYS & _flatten_keys(chunk)
    if forbidden_keys:
        errors.append(f"forbidden runtime/blob keys present: {', '.join(sorted(forbidden_keys))}")

    water_warnings, water_errors = check_water_and_binding(chunk)
    warnings.extend(water_warnings)
    errors.extend(water_errors)

    return {
        "chunk_id": chunk.get("chunk_id"),
        "chunk_type": chunk.get("chunk_type"),
        "retrieval_tokens_estimate": retrieval_tokens,
        "media_refs_tokens_estimate_if_embedded": ref_tokens,
        "warnings": warnings,
        "errors": errors,
        "ok": not errors,
    }


def self_test() -> int:
    assert estimate_text_tokens("abcd") == 1
    assert estimate_image_tokens(384, 384) == 258
    assert estimate_image_tokens(1024, 1024) == 4 * 258
    assert estimate_audio_tokens(10) == 320
    assert estimate_video_tokens(2) == 526
    sample = {"chunk_id": "test:v1", "chunk_type": "music_chunk", "retrieval_text": "x" * 2400, "references": {"items": []}, "focus": {"must_preserve": ["beat"], "must_not_drift": ["lyrics"]}}
    result = estimate_chunk(sample)
    assert result["retrieval_tokens_estimate"] == 600
    assert result["ok"] is True
    too_large = dict(sample, retrieval_text="x" * 4804)
    rejected = estimate_chunk(too_large)
    assert rejected["retrieval_tokens_estimate"] == 1201
    assert rejected["ok"] is False
    overridden = estimate_chunk(too_large, allow_large_retrieval_text=True)
    assert overridden["ok"] is True
    forbidden = dict(sample, provider_payload={"bad": True})
    assert estimate_chunk(forbidden)["ok"] is False
    print("estimate_chunk_tokens self-test: OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("chunk_json", nargs="?", help="Path to *_chunk.json")
    parser.add_argument("--allow-large-retrieval-text", action="store_true", help="warn instead of reject retrieval_text above 1200 estimated tokens; intended for tests/manual override only")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.chunk_json:
        parser.error("chunk_json is required unless --self-test is used")

    result = estimate_chunk(load_json(args.chunk_json), allow_large_retrieval_text=args.allow_large_retrieval_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
