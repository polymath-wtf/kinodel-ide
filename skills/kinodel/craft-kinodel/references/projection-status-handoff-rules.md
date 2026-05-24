# Projection, Status, and Handoff Rules for Kinodel Chunks

Use this reference when auditing or implementing Kinodel RAG/chunk architecture. It captures durable rules from the chunk projection review.

## Core rule

A chunk is not one big prompt dump. Treat it as four related projections:

1. Durable full chunk — canonical JSON on disk with `context`, `references`, `action`, `focus`, `timing`, `retrieval_text`, `source_artifacts`, `integrity/content_hash`, and craft metadata.
2. Retrieval projection — `retrieval_text` plus index metadata only. Target 150–600 tokens, warn above 600, reject above 1200 unless explicitly overridden.
3. Handoff projection — per-consumer context: direct paths, compact summaries, and selected media refs only.
4. Media refs projection — handle-bound media refs; never inline media bytes/blobs.

Derived projections and context packs are cache/handoff, not canon. Canon remains approved artifacts plus crafted chunks.

## Retrieval vs instruction split

`retrieval_text` answers: how should this chunk be found?

`action` and `focus` answer: what should an agent do with it?

Never put full JSON, provider payloads, logs, media blobs, or long prompt instructions into `retrieval_text`.

## Episode status policy

Episode lifecycle:

```text
planned -> active -> completed -> archived
```

- Planned future chunks: foreshadowing only; logline, promise, setup/payoff hints. Never completed facts.
- Active/current chunk: can be full/direct for the episode agent if token-safe.
- Completed previous chunk: continuity facts; ending state, unresolved hooks, character deltas, continuity constraints.
- Older completed chunks: compress to 3–6 bullet continuity summaries unless explicitly needed.
- Archived chunks: not canon; only `reference_only`/`inspiration` when explicitly selected.

## Default serial episode handoff

For `episode-kinodel`, resolver/context pack should provide:

- current planned/active episode chunk: full/direct or compact full projection;
- compact season chunk;
- previous completed episode chunk: direct/compact continuity projection;
- older completed episodes: tiny continuity summaries;
- future planned neighbors: logline/promise/setup hints with “not completed facts” warning;
- selected media refs only, each with handle/role/take/ignore/use_cases/priority;
- short task instruction and owned output path.

Default frozen handoff path:

```text
/tmp/kinodel/<project_id>/<run_id>/context_pack.<consumer>.json
```

Only copy context packs into project storage for audit/debug/repro.

## Embedding profiles

Use purpose-specific dimensions:

- `fast_recall` / 256 — broad scan, old library, low-cost candidates.
- `default_rag` / 768 — normal text RAG.
- `deep_retrieval` / 1536 — continuity conflict and nuanced style rerank.
- `full_fidelity` / 3072 — high-fidelity media/avatar/music rerank only.

Store profiles separately. Query vectors must match indexed dimensionality and embedding format version.

## Hash and invalidation

`content_hash` should include:

- normalized chunk JSON;
- `retrieval_text`;
- selected media metadata and bytes hash when relevant;
- craft schema version;
- embedding format version.

Exclude `content_hash` itself and volatile runtime fields from the hash input.

Invalidation policy:

- hash changed -> reindex affected profiles;
- `season_plan.json` changed -> recraft planned episode chunks;
- completed episode chunk changed -> recraft it and mark later episodes for continuity review.

## Water/filler checks

Warn or reject before indexing/handoff when a chunk has:

- vague adjectives without functional meaning: “cinematic”, “beautiful”, “interesting”;
- duplicated summary fields;
- long natural-language intros;
- provider traces, queue IDs, callback URLs, retry/cost logs;
- unbound refs or refs missing role/take/ignore/use_cases/priority;
- “take everything from this image” style instructions;
- missing `must_preserve` or `must_not_drift`.
