# Chunk/RAG Architecture Decisions

Use this when crafting or auditing Kinodel chunks for serial, music-video, or future RAG-backed pipelines.

## Core simplification

Everything durable should be a chunk or an approved project artifact. Resolver outputs are derived views, not canon.

Source of truth:
- `season_chunk.json`
- `episode_chunks/episode_N_chunk.json`
- `avatar_chunk.json`
- `music_chunk.json`
- `cinema_chunk.json`
- approved authoring artifacts such as `season_plan.json`

Derived/cache:
- vector index
- FTS index
- optional per-run context pack

Do not introduce a durable `references/chunk_context.json` as another canonical artifact. If a resolver output is needed, write a disposable context pack under `/tmp/kinodel/<project_id>/<run_id>/context_pack.<consumer>.json`; copy to project `context_packs/` only for audit/debug/repro.

## Serial episode planning

`episodes/episode_N.json` should not be a separate hand-authored source of truth by default.

Preferred flow:
1. `season-kinodel` writes one coherent `season_plan.json` with embedded episode blueprints.
2. After season approval, Craft/Producer derives:
   - `season_chunk.json`
   - `episode_chunks/episode_01_chunk.json` ... `episode_chunks/episode_N_chunk.json` with `status: planned`
3. During episode production, `episode-kinodel` reads:
   - approved `season_chunk`
   - target planned/current `episode_chunk` in fuller detail
   - previous completed `episode_chunk` when N > 1
   - neighbor/future planned chunks only as compact foreshadowing, never completed facts
4. After montage/completion, Craft/Producer writes a new completed version of that episode chunk.

Lifecycle: `planned -> active/current -> completed -> archived`.

## Retrieval text

`retrieval_text` is for finding a chunk, not for instructing an agent and not for storing the whole chunk.

Document embedding prefix:

```text
title: {chunk title} | text: {retrieval_text}
```

Query embedding prefix:

```text
task: search result | query: {consumer_agent} needs {context_need}. Constraints: {filters}
```

Gemini Embedding 2 rules:
- model: `gemini-embedding-2`
- pass `output_dimensionality` explicitly
- do not use API `task_type`; put task semantics in the text prefix
- keep query/document vectors on the same dimension and format version

Good `retrieval_text` contains:
- names, aliases, IDs, tags
- logline / compact summary
- canon vs inspiration policy
- must preserve / must not drift
- continuity hooks
- selected visual/audio/timing terms needed for search

Bad `retrieval_text` contains:
- full JSON
- provider payloads, queue IDs, retry logs, costs
- base64 or media blobs
- full scripts/lyrics/chat history
- vague filler such as “important context for the story”

Target size: 150-600 tokens; warn above 600; reject above 1200 unless explicitly justified.

## Context pack rule

A context pack is optional handoff glue: a frozen, token-budgeted projection for one run/consumer. Prefer direct chunk paths when the consumer can safely load exact chunks.

Default location:

```text
/tmp/kinodel/<project_id>/<run_id>/context_pack.<consumer>.json
```

Only copy to durable project storage for debugging/audit/reproducibility:

```text
~/projects/<project_id>/v1/context_packs/<run_id>/<consumer>.json
```

## Chunk optimization checklist

- Separate durable full chunk from retrieval projection, handoff projection, and media refs projection.
- Keep durable full chunk as canonical JSON with `context`, `references`, `action`, `focus`, `timing`, `retrieval_text`, `source_artifacts`, `content_hash`, and craft metadata.
- Keep retrieval projection to `retrieval_text` + metadata only; target 150–600 tokens, warn above 600, reject above 1200 unless explicitly overridden.
- Handoff projection is per consumer: full/direct current episode, compact season, compact previous completed episode, tiny neighbor summaries, selected media refs only.
- Keep media as refs with handles, roles, take/ignore/use_cases/priority; never inline blobs.
- Use status-aware policy: planned future chunks are foreshadowing only, completed previous chunks are continuity facts, archived chunks are not canon.
- Use 256 for broad scan, 768 for normal text RAG, 1536 for nuanced continuity/style, 3072 only for high-fidelity media/avatar/music rerank.
- Keep `action`/`focus` as agent-use instructions; keep `retrieval_text` as search text.
- Hash normalized chunk JSON + retrieval_text + selected media metadata/bytes hash + craft/embedding format version; exclude `content_hash` and volatile runtime fields from its own input.
- Recraft and reindex affected chunks after season/episode edits.
- Apply water checks before indexing/handoff: vague adjectives without function, duplicated summaries, long intros, provider traces, unbound refs, “take everything from this image”, or missing must_preserve/must_not_drift.
