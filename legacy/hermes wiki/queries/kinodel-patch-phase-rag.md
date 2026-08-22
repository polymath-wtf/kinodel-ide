---
title: Kinodel Patch Phase RAG — Full chunk crafting, indexing, and resolver foundation
created: 2026-05-23
type: query
tags: [kinodel, patch-phase, rag, chunks, gemini-embedding-2, phase-rag]
phase: RAG
status: ready
position: after phase-c before phase-d
depends_on: phase-c
sources:
  - [[kinodel-patch-implementation-plan]]
  - [[kinodel-rag-chunk-architecture]]
  - [[gemini-embedding-2]]
  - [[gemini-token-counter]]
  - [[agent-craft-kinodel]]
  - [[avatar-chunk]]
  - [[music-chunk]]
  - [[season-chunk]]
  - [[episode-chunk]]
  - [[cinema-chunk]]
  - [[kinodel-rag-patch-optimization-plan]]
---

# Kinodel Patch Phase RAG — Full chunk crafting, indexing, and resolver foundation

## Copy-paste prompt for GPT agent

```text
Read first:
/home/seryogasakura/wiki/queries/kinodel-patch-implementation-plan.md
/home/seryogasakura/wiki/queries/kinodel-patch-phase-rag.md
/home/seryogasakura/wiki/queries/kinodel-rag-chunk-architecture.md
/home/seryogasakura/wiki/queries/kinodel-rag-patch-optimization-plan.md
Then inspect: [[gemini-embedding-2]], [[agent-craft-kinodel]], [[avatar-chunk]], [[music-chunk]], [[season-chunk]], [[episode-chunk]], [[cinema-chunk]].

Task: implement ONLY Phase RAG of the Kinodel patch.
Core goal: build the real chunk/RAG foundation before serial and music-video activation: crafted chunk schemas, token counter guard, local index schema, Gemini Embedding 2 adapter, indexer dry-run/mock mode, chunk resolver, and context pack contract.

Scope clarification: Phase RAG is vector-ready foundation, not full semantic/vector nearest-neighbor retrieval activation. Keep embedding profile/dimension metadata and mock vector storage so a later explicit semantic retrieval phase can add sqlite-vec/NN search safely. At startup, resolver readiness is based on direct mandatory loads, metadata filters, FTS, policy filters, RRF-style merge where applicable, token-budget selection, and optional context pack writing.

Do not activate serial_season.v1, serial_episode.v1, or music_video.v1 production routes in this phase. Do not make Render query RAG. Do not inline media blobs or provider logs into chunks/context packs. Do not add a mandatory sqlite-vec dependency or require real vector NN search in this pass.

Required proof: cinematic.v1 still validates with empty chunk_dependencies; chunk schemas validate; token guard rejects oversized retrieval_text; resolver produces compact selected chunk paths / optional context pack from fixtures without vector NN; Gemini embedding calls use google-genai with model="gemini-embedding-2" and output_dimensionality, no API task_type field.
```

## Objective

Build the shared RAG substrate so Phase D serial and Phase E music-video do not rely on temporary “chunk refs in handoff” hacks.

## Scope

Create/modify:

- `pipeline-kinodel/contracts/chunks/*.schema.json`
- `pipeline-kinodel/contracts/context_pack.schema.json`
- `pipeline-kinodel/scripts/index_chunks.py`
- `pipeline-kinodel/scripts/embed_gemini.py` or equivalent adapter
- `producer-kinodel/scripts/chunk_resolver.py`
- `craft-kinodel/scripts/estimate_chunk_tokens.py`
- `craft-kinodel/references/rag-index-contract.md`
- fixture chunks for avatar/music/season/episode/cinema if test layout needs them

May patch:

- `craft-kinodel` skill docs/templates to remove water and align five-subject chunk shape.
- `state_guard.py` handoff assembly only enough to accept/write selected chunk paths / optional context pack path for later phases, without activating non-cinematic routes.

Do not modify:

- render provider payload logic except tests ensuring Render does not use RAG;
- music-video route activation;
- serial route activation;
- ReviewGate behavior.

## Core implementation requirements

### 1. Crafted chunk schemas

Support:

- `avatar_chunk`
- `music_chunk`
- `season_chunk`
- `episode_chunk`
- `cinema_chunk`
- `section_chunk` optional if docs indexing is included

Required common fields:

```text
schema, chunk_id, chunk_type, title, status,
context, references, action, focus, timing,
retrieval_text, embedding_profiles, content_hash, craft
```

References require:

```text
handle, path or url, modality, role, take, ignore, use_cases, priority, consumers
```

Reject chunks with raw blobs, provider queues, raw responses, retries/costs/logs, or long history dumps.

### 2. Token guard

Use [[gemini-token-counter]] rules for local estimation:

- text ≈ 4 chars/token;
- image <=384px ≈ 258 tokens, larger images tile;
- audio ≈ 32 tokens/sec;
- video ≈ 263 tokens/sec.

Hard rules:

- warn above 600 tokens for `retrieval_text`;
- reject above 1200 tokens unless `allow_large_retrieval_text=true` in a test-only/config override;
- reject context packs above their `max_context_tokens` after compression/selection.

### 3. Gemini Embedding 2 adapter

Use `google-genai`:

```python
from google import genai
from google.genai import types

client = genai.Client()
client.models.embed_content(
    model="gemini-embedding-2",
    contents="title: ... | text: ...",
    config=types.EmbedContentConfig(output_dimensionality=768),
)
```

Do not use API `task_type`. Task goes into text prefix:

- documents: `title: {title} | text: {retrieval_text}`
- queries: `task: search result | query: {need}`

### 4. Index schema

MVP backend: SQLite + FTS5 plus vector-ready storage/metadata. sqlite-vec/nearest-neighbor search is optional future work, not required for this Phase RAG pass; dry-run/mock vector store must exist for tests and future compatibility.

Separate vector tables/columns by dimension:

- 256 `fast_recall`
- 768 `default_rag`
- 1536 `deep_retrieval`
- 3072 `full_fidelity`

Index metadata records `model`, `dim`, `profile`, `format_version`, and `content_hash`.

### 5. Chunk resolver

`chunk_resolver.py` must support:

- direct mandatory loads by spec dependency;
- metadata filters by project/season/episode/chunk_type/status/is_active;
- FTS search;
- vector-ready metadata and storage separated by profile/dim, but no full semantic/vector nearest-neighbor search in this phase;
- FTS + metadata candidate merge; keep RRF-style merge extension points for future FTS + vector candidates;
- policy filters: no archived/unapproved canon/future-as-facts;
- token-budget selection;
- write selected chunk paths / optional context pack.

### 6. Context pack schema

`kinodel.context_pack.v1` includes:

```text
project_id, pipeline_id, goal, consumer_agent, retrieval_profile,
source_of_truth, query, direct_chunks, projected_chunks, media_refs,
token_budget, forbidden
```

It contains selected summaries and refs only. It must not contain full chunk JSON unless explicitly selected and token-budgeted.

## Test gate

Minimum commands should exist and pass:

```bash
python3 /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/pipelines/cinematic.v1.json

python3 /home/seryogasakura/.hermes/skills/kinodel/craft-kinodel/scripts/estimate_chunk_tokens.py --self-test

python3 /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/scripts/index_chunks.py --dry-run --fixtures

python3 /home/seryogasakura/.hermes/skills/kinodel/producer-kinodel/scripts/chunk_resolver.py --self-test
```

Also verify by search/tests:

- no `task_type` field is used for `gemini-embedding-2` embeddings;
- no vector table mixes dimensions;
- oversized `retrieval_text` is rejected;
- `context pack` contains no base64/media blobs/provider traces;
- Render code does not query chunk resolver.

## Acceptance criteria

- Full chunk schema foundation exists.
- Token guard exists and is used before indexing/handoff.
- Gemini Embedding 2 syntax is correct.
- Local indexer can run in dry-run/mock mode without credentials.
- Resolver writes compact context packs from fixtures using direct loads, metadata filters, FTS, policy filters, and token-budget selection.
- Vector profile/dim metadata and mock vector storage are present for a later explicit semantic retrieval phase, but full vector NN search is not required or activated now.
- Cinematic route remains unaffected.
- Phase D and Phase E can now depend on a real RAG foundation.

## Stop line

Stop after the shared RAG foundation. Do not activate serial or music-video production routes in this pass.

## Related docs

- [[kinodel-rag-chunk-architecture]]
- [[gemini-embedding-2]]
- [[agent-craft-kinodel]]
- [[serial-pipeline]]
- [[music-video-pipeline]]

