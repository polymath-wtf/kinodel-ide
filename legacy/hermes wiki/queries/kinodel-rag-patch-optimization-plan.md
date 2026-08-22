---
title: Kinodel RAG Patch Optimization Plan
created: 2026-05-23
type: query
tags: [kinodel, rag, chunks, optimization, deploy-readiness]
status: draft-ready
sources:
  - [[kinodel-patch-phase-rag]]
  - [[kinodel-rag-chunk-architecture]]
  - [[gemini-embedding-2]]
---

# Kinodel RAG Patch Optimization Plan

## Readiness verdict

Phase RAG is architecturally deployable as a foundation patch if it stays scoped to chunk schemas, token guard, Gemini Embedding 2 adapter, local index dry-run/mock mode, resolver, and optional context-pack handoff.

Do not activate serial_season.v1, serial_episode.v1, or music_video.v1 production routes in this patch.

## Critical invariants to preserve

1. Approved artifacts and crafted chunks are canon; vector indexes and context packs are derived cache.
2. Render never queries RAG; Render receives explicit render request artifacts and selected media refs only.
3. Query/document embeddings must share model, output_dimensionality, and formatting version.
4. Separate storage by vector dimension: 256, 768, 1536, 3072.
5. retrieval_text is search text only, not an instruction prompt or JSON dump.
6. Future planned episode chunks are foreshadowing only, not completed facts.
7. Context packs are /tmp per-run projections unless copied for audit/debug/repro.

## Token aerodynamics plan

### Retrieval text

Target 150–600 estimated tokens. Warn above 600. Reject above 1200 unless an explicit test/manual override is passed.

Keep retrieval_text dense:
- title/name aliases;
- canon/inspiration boundary;
- must-preserve / must-not-drift facts;
- retrieval tags and continuity hooks;
- selected reference handles by role, not full reference prose.

Remove:
- long intros;
- duplicated summaries;
- provider details;
- raw JSON/logs;
- unbound adjectives with no function.

### Handoff projection

Preferred handoff order:
1. direct chunk paths for exact canon;
2. compact context_pack only when the agent needs a frozen selected projection;
3. selected media refs with role/take/ignore/use_cases/priority.

Default budgets:
- visual planner: 2500–5000 tokens;
- episode writer: 5000–8000 tokens;
- season planner: 6000–9000 tokens;
- muse/music: 3000–6000 tokens.

### Embedding profiles

Use 768 default_rag for normal production retrieval. Use 256 only for broad global scans. Use 1536/3072 only for high-risk rerank or multimodal fidelity; do not index everything at 3072.

## Deployment sequence

### Gate 0 — static safety

Run:

```bash
python3 ~/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py ~/.hermes/skills/kinodel/pipeline-kinodel/pipelines/cinematic.v1.json
python3 ~/.hermes/skills/kinodel/craft-kinodel/scripts/estimate_chunk_tokens.py --self-test
python3 ~/.hermes/skills/kinodel/pipeline-kinodel/scripts/embed_gemini.py --self-test
python3 ~/.hermes/skills/kinodel/pipeline-kinodel/scripts/index_chunks.py --dry-run --fixtures
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/chunk_resolver.py --self-test
```

Also verify:

```bash
grep -R --include='*.py' "task_type" ~/.hermes/skills/kinodel/pipeline-kinodel/scripts ~/.hermes/skills/kinodel/producer-kinodel/scripts ~/.hermes/skills/kinodel/craft-kinodel/scripts
```

Expected: no matches.

### Gate 1 — fixture expansion

Add fixtures for:
- oversized retrieval_text rejection;
- archived chunk excluded;
- planned future episode excluded from fact context;
- context pack over-budget rejection;
- mixed FTS + metadata RRF selection;
- dimension/profile mismatch refusal.

### Gate 2 — state_guard integration

Use `state_guard.py handoff --chunk-path ... --context-pack ...` only for selected resolver outputs. Do not make Producer paste full chunks into handoff.

### Gate 3 — real Gemini smoke test

With GEMINI_API_KEY available, embed one tiny fixture chunk at 256 and 768, verify vector lengths, write persistent SQLite index, then query through resolver. Keep this separate from CI/dry-run so tests work without credentials.

### Gate 4 — downstream phase unlock

Only after Phase RAG passes:
- Phase D may add serial season/episode specs and chunk_dependencies.
- Phase E may add Muse/music-video chunk dependencies.

## Optimization backlog

Current preproduction decision: do not add semantic/vector nearest-neighbor search in this patch. Agents can receive explicitly selected chunk paths/context packs by known indexes and use_case instructions. Keep embeddings/index metadata as foundation, not autonomous retrieval authority.

Done for preproduction:

1. Added `scripts/validate_chunk_schema.py` for chunk/context_pack JSON Schema validation, with dependency-light fallback.
2. Integrated schema validation into `scripts/index_chunks.py` before indexing.
3. Added regression checks for provider/runtime key rejection and embedding profile/dimension mismatch.
4. Expanded resolver self-test for archived exclusion and planned-episode exclusion when `--fact-context` is requested.

Deferred until after the build is stable:

1. Replace JSON vector storage with sqlite-vec tables or another vector backend, preserving mock fallback.
2. Add real semantic vector candidate search to resolver only when autonomous/semantic retrieval is actually needed.
3. Add deterministic normalized content_hash helper shared by Craft and indexer.
4. Add media metadata hash sidecar for selected refs, with bytes hashing optional and lazy.
5. Add resolver RRF tuning if/when multiple candidate sources are active: direct/metadata first, FTS second, vector third, rerank only for top-K.
6. Add context-pack compressor per consumer: visual, episode, season, muse.
7. Add index invalidation command: reindex stale profile records when content_hash or format_version changes.
8. Add audit report command that proves Render has no resolver imports/calls.
9. Add small benchmark: fixture count, index time, resolver latency, context tokens saved.
10. After serial/music activation, add regression tests for future-as-foreshadowing and lyrics/melody non-cloning policies.
