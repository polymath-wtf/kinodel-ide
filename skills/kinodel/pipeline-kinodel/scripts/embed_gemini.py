#!/usr/bin/env python3
"""Gemini Embedding 2 adapter for Kinodel chunks.

Keeps the embedding contract in one place: google-genai, model gemini-embedding-2,
explicit output_dimensionality and stable document/query prefixes. The deprecated
API task field is intentionally not passed to google-genai.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
from pathlib import Path
from typing import Literal

# Hermès terminal subprocesses do not automatically inherit ~/.hermes/.env, and
# this host keeps google-genai in a Kinodel-local venv to avoid system Python writes.
VENV_SITE = Path.home() / ".hermes/venvs/kinodel-rag-312/lib/python3.12/site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

def load_hermes_env() -> None:
    env_path = Path.home() / ".hermes/.env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val

MODEL = "gemini-embedding-2"
FORMAT_VERSION = "kinodel.gemini_embedding_2.prefix.v1"
PROFILE_DIMS = {
    "fast_recall": 256,
    "default_rag": 768,
    "deep_retrieval": 1536,
    "full_fidelity": 3072,
}


def profile_dim(profile: str | None = None, dim: int | None = None) -> int:
    if dim:
        if dim < 128 or dim > 3072:
            raise ValueError("output_dimensionality must be 128..3072")
        return int(dim)
    if not profile:
        profile = "default_rag"
    if profile not in PROFILE_DIMS:
        raise ValueError(f"unknown embedding profile {profile!r}; known={sorted(PROFILE_DIMS)}")
    return PROFILE_DIMS[profile]


def format_document(title: str, retrieval_text: str) -> str:
    return f"title: {title or 'none'} | text: {retrieval_text}"


def format_query(consumer_agent: str, context_need: str, filters: str | None = None) -> str:
    suffix = f" Constraints: {filters}" if filters else ""
    return f"task: search result | query: {consumer_agent} needs {context_need}.{suffix}"


def _mock_vector(text: str, dim: int) -> list[float]:
    seed = int(hashlib.sha256((FORMAT_VERSION + text + str(dim)).encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    values = [rng.uniform(-1.0, 1.0) for _ in range(dim)]
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def embed_text(text: str, *, profile: str = "default_rag", dim: int | None = None, mock: bool = False) -> dict:
    output_dimensionality = profile_dim(profile, dim)
    if mock:
        return {
            "model": MODEL,
            "format_version": FORMAT_VERSION,
            "profile": profile,
            "dim": output_dimensionality,
            "embedding": _mock_vector(text, output_dimensionality),
            "mock": True,
        }
    load_hermes_env()
    try:
        from google import genai
        from google.genai import types
    except Exception as exc:  # pragma: no cover - depends on environment
        raise RuntimeError("google-genai is required for real embeddings; use --mock for dry-run") from exc
    # google-genai accepts GEMINI_API_KEY in recent versions, but mirror to
    # GOOGLE_API_KEY for compatibility with older clients/environments.
    if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
    client = genai.Client()
    result = client.models.embed_content(
        model=MODEL,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=output_dimensionality),
    )
    return {
        "model": MODEL,
        "format_version": FORMAT_VERSION,
        "profile": profile,
        "dim": output_dimensionality,
        "embedding": result.embeddings[0].values,
        "mock": False,
    }


def self_test() -> int:
    doc = format_document("Demo", "compact retrieval text")
    query = format_query("episode-kinodel", "continuity for episode_03", "chunk_type=episode_chunk")
    assert doc == "title: Demo | text: compact retrieval text"
    assert query.startswith("task: search result | query:")
    assert profile_dim("fast_recall") == 256
    assert profile_dim("default_rag") == 768
    assert len(embed_text(doc, mock=True)["embedding"]) == 768
    source = open(__file__, "r", encoding="utf-8").read()
    forbidden_api_field = "task" + "_type"
    assert forbidden_api_field not in source
    print("embed_gemini self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Embed Kinodel text with Gemini Embedding 2")
    parser.add_argument("--text", help="Already formatted text to embed")
    parser.add_argument("--document", action="store_true", help="Format --title + --retrieval-text as a document")
    parser.add_argument("--query", action="store_true", help="Format --consumer-agent + --need as a query")
    parser.add_argument("--title", default="none")
    parser.add_argument("--retrieval-text")
    parser.add_argument("--consumer-agent")
    parser.add_argument("--need")
    parser.add_argument("--filters")
    parser.add_argument("--profile", default="default_rag", choices=sorted(PROFILE_DIMS))
    parser.add_argument("--dim", type=int)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.document:
        if args.retrieval_text is None:
            parser.error("--document requires --retrieval-text")
        text = format_document(args.title, args.retrieval_text)
    elif args.query:
        if not args.consumer_agent or not args.need:
            parser.error("--query requires --consumer-agent and --need")
        text = format_query(args.consumer_agent, args.need, args.filters)
    elif args.text:
        text = args.text
    else:
        parser.error("provide --text, --document, or --query")
    result = embed_text(text, profile=args.profile, dim=args.dim, mock=args.mock)
    printable = dict(result)
    printable["embedding"] = {"length": len(result["embedding"]), "sha256": hashlib.sha256(json.dumps(result["embedding"][:16]).encode()).hexdigest()[:16]}
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
