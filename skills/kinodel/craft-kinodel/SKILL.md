---
name: craft-kinodel
description: Use when crafting, importing, normalizing, or updating Kinodel chunks before RAG indexing or subagent handoff. Inspects refs, assigns @handles, packages context/references/action/focus/timing, writes compact retrieval_text, and returns artifact paths only.
license: MIT
metadata:
  hermes:
    trigger: craft kinodel, craft chunks, chunk crafting, avatar_chunk, music_chunk, season_chunk, episode_chunk, cinema_chunk, chunk refs, reference binding, retrieval_text, kinodel rag chunks
    category: kinodel
    schema_version: 1
    tags: [kinodel, chunks, rag, reference-binding, prompt-engineering, gemini-embedding-2, mrl]
    related_skills: [pipeline-kinodel, producer-kinodel, wardrobe-kinodel, storyboard-kinodel, filmmaker-kinodel, render-kinodel]
---

# Craft-Kinodel

Craft-Kinodel is the Kinodel chunk-crafting specialist. It turns raw refs, approved artifacts, and reusable library media into durable `*_chunk.json` artifacts that can be indexed by Gemini Embedding 2 and selected by the chunk resolver.

It does **not** write story content, render media, approve ReviewGates, or call providers. It packages context so other agents can work faster and with less drift.

## When to Use

Use this skill when:

- importing or updating `avatar_chunk`, `music_chunk`, `season_chunk`, `episode_chunk`, `cinema_chunk`, or future reusable chunks;
- turning media refs into stable `@imageN`, `@videoN`, `@audioN`, `@docN` handles;
- preparing chunk material for `gemini-embedding-2` indexing via compact `retrieval_text`;
- building subagent-ready chunk context for Wardrobe, Storyboard, Filmmaker, Season, Episode, or Muse;
- auditing whether a chunk is safe to hand off without raw blobs, provider logs, or ambiguous references.

Do **not** use this skill for:

- generating images/videos/audio — that belongs to `render-kinodel`;
- writing full story beats — that belongs to Storytell/Season/Episode agents;
- choosing pipeline route or bypassing gates — that belongs to Producer and Pipeline law;
- stuffing whole media files, logs, or long histories into prompts.

## Core Contract: CRAFT for Chunks

Every craft-owned chunk uses five subjects, inspired by Gemini Omni CRAFT but adapted for RAG chunks:

| Subject | Chunk meaning |
|---|---|
| `context` | What this chunk represents, source-of-truth status, project/season/episode scope, canon/inspiration boundary. |
| `references` | Media/doc refs with stable handles, roles, take/ignore rules, use cases, and downstream priorities. |
| `action` | What downstream agents should do with this chunk: plan, preserve identity, retrieve continuity, inspire vibe, select refs. |
| `focus` | The non-drift priority: identity lock, continuity fact, style DNA, emotional state, music energy, or render-relevant detail. |
| `timing` | Optional temporal/sequence map when source data has timing: music sections, episode order, act order, video beats. No invented fixed timings. |

Important: `timing` is allowed and useful, but it is **not** mandatory video-model timing. For chunks, timing means source-derived sequence/phase information only.

## Projection Contract

Do not treat a chunk as one large prompt dump. Every chunk has distinct projections:

1. **Durable full chunk** — canonical JSON on disk with `context`, `references`, `action`, `focus`, `timing`, `retrieval_text`, `source_artifacts`, `content_hash`, and craft metadata.
2. **Retrieval projection** — only compact `retrieval_text` plus index metadata. Target 150–600 tokens; warn above 600; reject above 1200 unless explicitly overridden.
3. **Handoff projection** — what one consumer agent actually receives: direct path to the current full chunk when safe, compact season/previous/neighbor summaries, and selected media refs only.
4. **Media refs projection** — stable `@image`/`@video`/`@audio`/`@doc` handles with `role`, `take`, `ignore`, `use_cases`, and `priority`; never inline media blobs.

Resolver/context-pack outputs are derived handoff/cache, not canon. Prefer direct chunk paths; materialize `/tmp/kinodel/<project_id>/<run_id>/context_pack.<consumer>.json` only when a subagent needs a frozen token-budgeted projection.

## Hot Workflow

```text
1. Read the requested chunk type and source artifacts.
2. Inspect every referenced file before describing it when possible.
3. Assign local handles: @image1, @video1, @audio1, @doc1.
4. Fill the five subjects: context, references, action, focus, timing.
5. Create compact retrieval_text for gemini-embedding-2.
6. Run token/water guard (`scripts/estimate_chunk_tokens.py`) and remove filler before indexing/handoff. The guard must reject `retrieval_text` above 1200 estimated tokens unless `--allow-large-retrieval-text` is deliberately passed for tests/manual override; it also rejects provider/runtime/blob keys such as `base64`, `provider_payload`, `queue_id`, `callback_url`, `raw_response`, `retry_log`, and `cost_log`.
7. Validate compactness, status, and no raw blobs/provider trace with `pipeline-kinodel/scripts/validate_chunk_schema.py` before treating any template or crafted artifact as ready. The concrete chunk templates in `chunks/*_chunk.v1.json` must use canonical schemas such as `kinodel.avatar_chunk.v1` / `kinodel.episode_chunk.v1`, include top-level `content_hash`, and pass both schema validation and token guard without warnings.
8. Write the chunk artifact and return path + short status only.
```

## Reference Binding Formula

```text
@handle as/for {specific role} — take {specific aspects}; ignore {irrelevant aspects}; use for {agent/stage use cases}; priority {P1-P5}
```

Examples:

```text
@image1 as hero front-closeup identity ref — take face, eye shape, hair silhouette, wardrobe palette; ignore background and temporary lighting; use for Wardrobe main frame and Filmmaker face lock; priority P1.
@audio1 as music vibe reference — take energy curve, instrumentation, vocal delivery, section contrast; ignore exact melody, copyrighted lyrics, artist identity cloning; use for Muse inspiration and Montage mood; priority P2.
@video1 as motion/style reference — take pacing, handheld texture, transition rhythm; ignore subject identity unless explicitly approved; use for Filmmaker motion language; priority P3.
```

## Load Progressive References

Load only what you need:

- `references/craft-subjects.md` — exact five-subject schema and filling rules.
- `references/reference-binding.md` — @handle slots, priority rules, take/ignore guidance.
- `references/handoff-contract.md` — how Craft talks to Producer, resolver, and downstream agents.
- `references/rag-index-contract.md` — practical Gemini Embedding 2/indexer/resolver contract and token guard policy.
- `references/chunk-rag-architecture-decisions.md` — Kinodel architecture decisions for optional context packs, planned episode chunks, retrieval_text, and chunk optimization.
- `references/projection-status-handoff-rules.md` — distilled rules for durable/retrieval/handoff/media projections, episode status policy, embedding profiles, hash invalidation, and water checks.
- `references/rag-smoke-test-cinematic-chunks.md` — real-project smoke recipe for crafting completed `cinema_chunk.json` artifacts from `final_chunk.json`, validating token/schema budget, indexing with mock vectors, and resolving context packs.
- `scripts/estimate_chunk_tokens.py` — local token estimator/guard before indexing/handoff.
- `scripts/backfill_cinema_chunks.py` — packaged backfill from completed `final_chunk.json` to `v1/chunks/cinema_chunk.json`; validates final chunks, protects manual edits unless `--force`, runs schema/token guards, and reports changed/unchanged/errors.
- `chunks/common-craft-chunk.v1.json` — common skeleton.
- `chunks/avatar_chunk.v1.json`, `music_chunk.v1.json`, `season_chunk.v1.json`, `episode_chunk.v1.json`, `cinema_chunk.v1.json` — artifact templates.
- `chunks/wardrobe-craft-pack.v1.json`, `storyboard-craft-pack.v1.json`, `filmmaker-craft-pack.v1.json` — task-specific context packs for prompt agents.

## Quality Gates

A crafted chunk is not ready unless:

- [ ] all refs have stable handles and existing paths/URLs;
- [ ] each ref states `role`, `take`, `ignore`, `use_cases`, and `priority`;
- [ ] `context.status` matches production truth (`active`, `approved`, `completed`, `archived`, etc.);
- [ ] `focus.must_preserve` and `focus.must_not_drift` are explicit;
- [ ] `timing` is source-derived or empty with a reason;
- [ ] `retrieval_text` is compact and stable for `gemini-embedding-2`;
- [ ] `retrieval_text` is search text only; agent instructions live in `action`/`focus`;
- [ ] no base64 media, raw provider payloads, queue IDs, retry logs, costs, or full chat histories are embedded;
- [ ] no watery filler: vague adjectives without function, duplicated summary fields, long intros, unbound refs, or “take everything from this image”;
- [ ] Render-facing output is explicit selected refs only, never broad RAG.

## Status-Aware Episode Policy

Episode chunks use lifecycle status: `planned -> active -> completed -> archived`.

- Future `planned` chunks are foreshadowing only: logline, promise, setup/payoff hints; never completed facts.
- Current `active` chunk can be loaded full/direct for the episode agent if token-safe.
- Previous `completed` chunk supplies continuity facts: ending state, unresolved hooks, character deltas, constraints.
- Older `completed` chunks should be compressed to 3–6 continuity bullets unless explicitly needed.
- `archived` chunks are not canon; use only as `reference_only`/`inspiration` when explicitly selected.

## Embedding Profiles

Do not index everything at 3072 dimensions. Use purpose-specific profiles:

- `fast_recall` / 256 — broad scan, old library, low-cost candidates.
- `default_rag` / 768 — normal text RAG.
- `deep_retrieval` / 1536 — continuity conflict and nuanced style rerank.
- `full_fidelity` / 3072 — high-fidelity media/avatar/music rerank only.

Store profiles separately; query vectors must match indexed dimensionality and embedding format version. For the current Phase RAG preproduction foundation, semantic/vector nearest-neighbor search is intentionally deferred: if Producer already knows which chunks belong in a handoff, pass those direct chunk paths/context packs with clear `use_cases` instead of asking agents to autonomously search and compare embeddings.

## Hash / Invalidation Policy

`content_hash` must account for normalized chunk JSON, `retrieval_text`, selected media metadata/bytes hash, craft schema version, and embedding format version. Exclude volatile runtime fields and the `content_hash` field itself from its own input.

- If hash changes, reindex affected profiles.
- If `season_plan.json` changes, recraft planned episode chunks.
- If a completed episode chunk changes, recraft that completed chunk and mark later episodes for continuity review.

## Pitfalls

1. **Using the old abstract CRAFT mapping.** Do not use `affordances`, `formatting/retrieval`, or `traceability` as the canonical chunk shape. The user's corrected contract is exactly five subjects: `context`, `references`, `action`, `focus`, `timing`.
2. **Copying Gemini Omni video timing into chunks.** Do not invent seconds. Use `timing` only for real source phases: episode order, act order, music sections, video beats, or render-result sequence.
3. **Ambiguous refs.** A path without role/take/ignore is not a crafted ref.
4. **Chunk as prompt dump.** Chunks are reusable memory artifacts, not final render prompts.
5. **RAG as source of truth.** Indexes derive from chunks; chunks derive from approved artifacts/refs.
6. **Render reading RAG.** Render gets explicit request artifacts and selected media refs only.
7. **Durable `chunk_context.json` as pseudo-canon.** Do not create a long-lived `references/chunk_context.json` as another artifact layer. Resolver output is optional per-run handoff glue (`/tmp/kinodel/<project_id>/<run_id>/context_pack.<consumer>.json`) and should be rebuilt from chunks.
8. **Separate per-episode JSON blueprints by default.** For serial, prefer one approved `season_plan.json` as authoring source, then Craft/Producer derives planned `episode_chunks/episode_N_chunk.json` after season approval. Episode agents should consume episode chunks, not raw `episodes/episode_N.json` dumps.
9. **Confusing retrieval text with prompt text.** `retrieval_text` is search/index text only: compact names, summaries, must-preserve/must-not-drift, continuity hooks, tags, and policy. Agent instructions belong in `action`/`focus`; full JSON/media/logs never belong in `retrieval_text`.
