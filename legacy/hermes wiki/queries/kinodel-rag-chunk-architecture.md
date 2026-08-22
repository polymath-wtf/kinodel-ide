---
title: Kinodel RAG Chunk Architecture — final preproduction vision
created: 2026-05-22
updated: 2026-05-23
type: query
tags: [kinodel, rag, chunks, gemini-embedding-2, mrl, serial, music, architecture, phase-rag]
status: ready-for-patch-planning
sources:
  - [[gemini-embedding-2]]
  - [[serial-pipeline]]
  - [[music-video-pipeline]]
  - [[agent-craft-kinodel]]
  - [[agent-season-kinodel]]
  - [[agent-episode-kinodel]]
  - [[agent-muse-kinodel]]
  - [[gemini-token-counter]]
  - [[avatar-chunk]]
  - [[music-chunk]]
  - [[season-chunk]]
  - [[episode-chunk]]
  - [[cinema-chunk]]
---

# Kinodel RAG Chunk Architecture — final preproduction vision

## Цель

Kinodel должен перейти от “обычных артефактов в handoff” к настоящей chunk/RAG архитектуре. Runtime остаётся artifact-centric, но долгоживущая память и контекст для новых агентов идут через crafted chunks и индекс Gemini Embedding 2. Resolver может материализовать короткий per-run context pack для handoff, но это не новый source of truth.

Нужные chunk families:

- `avatar_chunk` — identity/voice/style anchors;
- `music_chunk` — musical inspiration, ALM summary, energy/timing, audio refs;
- `season_chunk` — approved season bible;
- `episode_chunk` — completed episode continuity memory;
- `cinema_chunk` / `final_chunk` — completed cinematic or music-video memory;
- `section_chunk` — wiki/contract/code architecture chunks for implementation work.

## Canonical layers

```text
raw media / approved artifacts / user refs / wiki sections
        ↓ crafted by
craft-kinodel
  inspect refs, strip noise, bind @handles, write retrieval_text
        ↓ writes source of truth
*_chunk.json artifacts + refs/ sidecars
        ↓ indexed by
chunk_indexer using gemini-embedding-2
  metadata + FTS + vector profiles 256/768/1536/3072
        ↓ queried by
chunk_resolver
  direct loads + metadata filters + FTS + vector retrieval + rerank
        ↓ emits optional per-run materialized view
/tmp/kinodel/<project_id>/<run_id>/context_pack.<consumer>.json
  selected chunk IDs/paths + projections + selected media refs + token budget
        ↓ consumed by
season-kinodel / episode-kinodel / muse-kinodel / visual planners
```

Durable chunks are the source of truth. Vector indexes and context packs are derived cache/search infrastructure. If artifact and index/context pack disagree, rebuild the derived layer; do not patch the vector DB or context pack as canon.

## Non-negotiable laws

1. `craft-kinodel` owns chunk packaging before indexing. It removes water, assigns handles, binds references, and writes compact `retrieval_text`.
2. RAG selects context; it does not replace `producer_state.json`, `pipeline_spec.json`, gate decisions, or render result manifests.
3. Render workers do not query broad RAG. Render receives explicit request artifacts and selected media refs.
4. No full blob handoffs: no base64, no full mp3/wav/video, no full episode histories, no raw provider payloads, no queue IDs, no costs/retry logs.
5. Query vector and document vectors must share `model`, `output_dimensionality`, and formatting version.
6. Separate vector profile storage per dimension. Never mix 256/768/1536/3072 vectors in one ANN column/table without explicit profile separation.
7. Chunks are versioned append-only in hot runtime. Old versions become inactive/archived, not silently overwritten.
8. Gate approvals remain hard: p4/p7 and spec-declared gates are not bypassed by “good retrieval”.
9. Future episode chunks are not facts for earlier episodes. Future blueprints may be used only as foreshadowing context.
10. Context pack token budgets are enforced before subagent handoff.
11. `context_pack.*.json` is optional handoff glue, not a canonical artifact. Prefer direct chunk paths when the consumer can safely load the exact chunks itself.

## Crafted chunk contract

Every reusable chunk uses the same five subject blocks:

| Subject | Purpose |
|:---|:---|
| `context` | What this chunk represents, scope, status, canon/inspiration policy, source artifacts. |
| `references` | Media/doc refs with stable `@imageN`, `@videoN`, `@audioN`, `@docN` handles plus `role`, `take`, `ignore`, `use_cases`, `priority`. |
| `action` | What consumers should do with it: preserve identity, continue continuity, inspire vibe, select refs, avoid forbidden uses. |
| `focus` | Non-drift priority: identity lock, continuity fact, style DNA, music energy, emotional state, visual anchor. |
| `timing` | Source-derived sequence only: music sections, episode order, act order, video beats. Empty with reason if not applicable. |

Minimum chunk fields:

```json
{
  "schema": "kinodel.<chunk_type>.v1",
  "chunk_id": "<type>:<scope>:<stable_id>:v1",
  "chunk_type": "avatar_chunk|music_chunk|season_chunk|episode_chunk|cinema_chunk|section_chunk",
  "title": "human title",
  "status": "draft|active|approved|completed|archived",
  "context": {},
  "references": {"items": []},
  "action": {"consumer_tasks": [], "instructions": [], "forbidden_uses": []},
  "focus": {"primary": "identity_lock|continuity|style_dna|music_energy|emotional_state|visual_anchor", "must_preserve": [], "must_not_drift": []},
  "timing": {"mode": "not_applicable|music_sections|episode_sequence|act_sequence|video_beats", "summary": "", "items": []},
  "retrieval_text": "title: ... | text: ...",
  "embedding_profiles": ["default_rag"],
  "content_hash": "sha256:...",
  "craft": {"crafted_by": "craft-kinodel", "craft_version": "kinodel.craft.v1", "quality_checks": []}
}
```

Reference binding formula:

```text
@handle as/for {role} — take {specific aspects}; ignore {irrelevant aspects}; use for {agent/stage use cases}; priority {P1-P5}
```

## Source-of-truth layout

```text
~/chunk/
  avatars/<avatar_id>/avatar_chunk.json
  music/<music_id>/music_chunk.json
  cinema/<cinema_id>/cinema_chunk.json
  seasons/<project_id>/<season_id>/season_chunk.json
  episodes/<project_id>/<season_id>/<episode_id>_chunk.json
  indexes/kinodel_chunks.sqlite

~/projects/<project_id>/v1/
  season_chunk.json
  episode_chunks/episode_01_chunk.json
  indexes/kinodel_chunks.sqlite
  # optional audit copy only when needed:
  context_packs/<run_id>/<consumer>.json
```

Rules:

- Project-local chunks are authoritative for active production.
- `~/chunk/` is a reusable global library/archive mirror.
- Metadata stores both `artifact_path` and `global_path` when both exist.
- Global inspiration chunks are not project canon unless explicitly imported/approved.
- Normal resolver output lives under `/tmp/kinodel/<project_id>/<run_id>/context_pack.<consumer>.json`. Copy to project `context_packs/` only for debugging/audit/reproducibility.

## Gemini Embedding 2 contract

Use `gemini-embedding-2` via `google-genai`:

```python
from google import genai
from google.genai import types

client = genai.Client()

result = client.models.embed_content(
    model="gemini-embedding-2",
    contents="title: My chunk | text: compact retrieval text",
    config=types.EmbedContentConfig(output_dimensionality=768),
)
vector = result.embeddings[0].values
```

Important syntax and policy:

- Do not use an API `task_type` field for these flows. Put the task in the string prefix.
- Document prefix: `title: {title} | text: {retrieval_text}`.
- Query prefix: `task: search result | query: {consumer_agent} needs {context_need}. Constraints: {filters}`.
- Default output dimension is 3072, but Kinodel should request explicit dimensions.
- Query and document vectors must use identical dimension and formatting version.
- Input token limit is 8192 tokens; crafted `retrieval_text` should be much smaller than the limit.

Dimension profiles:

| Profile | Dim | Role | Use |
|:---|---:|:---|:---|
| `fast_recall` | 256 | cheap broad scan | global library scan, tags, old cinema summaries |
| `default_rag` | 768 | normal production RAG | season/episode/music/avatar text and mixed summaries |
| `deep_retrieval` | 1536 | precise rerank | continuity conflicts, important contracts, nuanced style |
| `full_fidelity` | 3072 | maximum multimodal fidelity | audio/image/video refs where similarity matters |

Recommended storage by chunk type:

| Chunk | Always | Optional |
|:---|:---|:---|
| `avatar_chunk` | 768 text/metadata | 1536/3072 image or voice refs |
| `music_chunk` | 768 ALM+lyrics+prompt summary | 1536/3072 audio rerank |
| `season_chunk` | 768 approved bible | 1536 for complex canon |
| `episode_chunk` | 768 continuity memory | 1536 for high-risk continuity |
| `cinema_chunk` | 256 summary + 768 text | 1536/3072 visual/video refs |
| `section_chunk` | 768 section | 1536 code/contract detail |

## Token counter policy before chunk craft

Before embedding or handoff, count or estimate token size. Use `[[gemini-token-counter]]` as raw reference.

Production target:

- `retrieval_text`: normally 150–600 tokens, hard reject above 1200 unless explicitly justified.
- selected resolver context pack: obey consumer budget.
- audio/video/image are passed as paths/refs, not inlined, except when the embedding/indexer intentionally embeds the media file itself.

Gemini token facts to encode in tooling:

- Text token estimate: roughly 4 characters per token.
- Image tokenization: small image <=384px counts about 258 tokens; larger images tile at 768x768, 258 tokens per tile.
- Audio: about 32 tokens/sec.
- Video: about 263 tokens/sec.
- `client.models.count_tokens(model=<model>, contents=<input>)` counts prompt/input tokens before a call.

`craft-kinodel` should run a local estimator/check first, then optional Gemini `count_tokens` when credentials are available and the exact model context matters.

## Index schema MVP

SQLite + FTS5 + sqlite-vec is the MVP backend. Backend can later move to pgvector/Qdrant without changing artifact contracts.

```sql
CREATE TABLE chunks (
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
  modality TEXT NOT NULL,
  media_refs_json TEXT NOT NULL DEFAULT '[]',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  content_hash TEXT NOT NULL,
  created_at TEXT,
  updated_at TEXT
);

CREATE VIRTUAL TABLE chunks_fts USING fts5(
  chunk_id UNINDEXED,
  title,
  summary,
  retrieval_text,
  chunk_type UNINDEXED,
  project_id UNINDEXED,
  season_id UNINDEXED,
  episode_id UNINDEXED
);

CREATE VIRTUAL TABLE chunk_vec_256 USING vec0(chunk_id TEXT PRIMARY KEY, embedding FLOAT[256]);
CREATE VIRTUAL TABLE chunk_vec_768 USING vec0(chunk_id TEXT PRIMARY KEY, embedding FLOAT[768]);
CREATE VIRTUAL TABLE chunk_vec_1536 USING vec0(chunk_id TEXT PRIMARY KEY, embedding FLOAT[1536]);
CREATE VIRTUAL TABLE chunk_vec_3072 USING vec0(chunk_id TEXT PRIMARY KEY, embedding FLOAT[3072]);

CREATE TABLE embedding_records (
  chunk_id TEXT NOT NULL,
  profile TEXT NOT NULL,
  dim INTEGER NOT NULL,
  model TEXT NOT NULL,
  format_version TEXT NOT NULL,
  embedded_at TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  PRIMARY KEY (chunk_id, profile)
);
```

`content_hash` = normalized chunk JSON + selected media metadata/bytes hash + `retrieval_text` + embedding format version.

## Retrieval cascade

```text
1. Read pipeline stage and declared chunk_dependencies.
2. Build metadata filters: pipeline_id, project_id, season_id, episode_id, chunk_type, status, active version.
3. Mandatory direct loads:
   - current season_chunk for serial episode;
   - target episode blueprint;
   - previous episode_chunk for episode N > 1;
   - explicitly selected avatar_chunks/music_chunks.
4. FTS prefilter by names, IDs, tags, continuity terms.
5. Vector retrieval:
   - 256 for global broad search;
   - 768 for normal production context;
   - 1536/3072 only for rerank/high-fidelity avatar/music/cinema retrieval.
6. RRF merge FTS + vector candidates.
7. Policy filter: no archived/unapproved/future-as-facts violations.
8. Token-budget selection and compression.
9. Return direct chunk paths plus, only if needed, write `/tmp/kinodel/<project_id>/<run_id>/context_pack.<consumer>.json` as a per-run materialized view.
10. Pass only paths + very short status to Producer/subagent handoff.
```

## Optional context pack contract

A context pack is a disposable resolver result for one run/consumer. It is useful when a subagent needs a frozen, token-budgeted projection of several chunks, but it is not required when direct chunk paths are enough.

```json
{
  "schema": "kinodel.context_pack.v1",
  "project_id": "serial_project",
  "pipeline_id": "serial_episode.v1",
  "goal": "p1_story",
  "consumer_agent": "episode-kinodel",
  "retrieval_profile": "episode_writer_balanced",
  "source_of_truth": "chunks_only",
  "query": {
    "text": "task: search result | query: episode-kinodel needs continuity for episode_03",
    "filters": {"chunk_types": ["season_chunk", "episode_chunk", "avatar_chunk"], "status": ["approved", "planned", "completed", "active"]}
  },
  "direct_chunks": [],
  "projected_chunks": [],
  "media_refs": [],
  "token_budget": {"max_context_tokens": 6000, "estimated_context_tokens": 0},
  "forbidden": ["do not treat future planned episodes as completed facts", "do not copy lyrics/melody directly from music chunks"]
}
```

Subagent handoff line:

```text
Read the explicit chunk paths first. If a context_pack path is provided, treat it as a frozen selection/projection for this run only. If you need a full chunk artifact, read the explicit path; do not assume unseen fields.
```

## Retrieval profiles by consumer

### `season-kinodel`

- Direct: `brief.json`.
- Direct/RAG: selected `avatar_chunk` summaries and P1 refs.
- Optional RAG: 2–4 `cinema_chunk`, old `season_chunk`, or `music_chunk` inspirations.
- Budget: 6000–9000 context tokens.
- Never: prior project dump as canon.

### `episode-kinodel`

- Direct: approved `season_chunk`, target planned/current `episode_chunk`.
- Direct for N>1: previous completed `episode_chunk`.
- Optional RAG: neighbor planned episode chunks, older completed episode chunks, avatars, relevant continuity hints.
- Budget: 5000–8000 context tokens.
- Never: future planned episode chunks as completed facts.

### `muse-kinodel`

- Direct: music/video brief.
- RAG: `music_chunk.retrieval_text`, ALM summary, energy curve, timing sections, compact generation hints.
- Optional high-fidelity: 1536/3072 audio rerank for top candidates only.
- Budget: 3000–6000 context tokens.
- Never: direct melody cloning or copyrighted lyric dumps by default.

### Visual planners

Wardrobe/Storyboard/Filmmaker consume selected refs from direct chunk paths or a resolver context pack, not broad RAG. Filmmaker should normally receive per-shot refs only.

## Pipeline spec integration

Pipeline specs declare chunk dependencies explicitly:

```json
{
  "chunk_dependencies": [
    {"name": "season_context", "chunk_type": "season_chunk", "required": true, "status": ["approved"], "scope": "project", "handoff_mode": "direct_compact"},
    {"name": "previous_episode_context", "chunk_type": "episode_chunk", "required_if": "episode_index > 1", "status": ["completed"], "scope": "project", "handoff_mode": "direct_compact"},
    {"name": "avatar_context", "chunk_type": "avatar_chunk", "required": true, "scope": "project_or_global", "handoff_mode": "selected_refs"}
  ]
}
```

Stage override:

```json
{
  "goal": "p1_story",
  "owner_skill": "episode-kinodel",
  "context_pack": {
    "consumer_agent": "episode-kinodel",
    "profile": "episode_writer_balanced",
    "max_context_tokens": 6000,
    "include": ["season_context", "target_planned_episode_chunk", "previous_completed_episode_context", "avatar_context"]
  }
}
```

## Implementation boundaries

Expected modules:

```text
craft-kinodel/scripts/estimate_chunk_tokens.py
craft-kinodel/scripts/craft_chunk.py               # later: deterministic packaging helper
producer-kinodel/scripts/chunk_resolver.py         # selects chunks and optionally writes context packs
pipeline-kinodel/scripts/index_chunks.py           # embeds/indexes crafted chunks
pipeline-kinodel/contracts/chunks/*.schema.json     # chunk schemas
pipeline-kinodel/contracts/context_pack.schema.json # optional resolver materialized view schema
```

Phase split:

- [[kinodel-patch-phase-rag]] builds full chunk crafting/index/resolver foundation.
- [[kinodel-patch-phase-d-serial-chunks]] consumes Phase RAG for serial season/episode specs and agents.
- [[kinodel-patch-phase-e-music-video]] consumes Phase RAG for Muse/music-video and audio/music chunks.

## Validation requirements

Before the RAG patch is safe:

- `cinematic.v1` validates with no chunk dependencies.
- `serial_season.v1` validates with optional avatar/music/cinema inspiration dependencies.
- `serial_episode.v1` validates required approved season chunk, target planned episode chunk, previous completed episode rule, and avatar context.
- `music_video.v1` validates with Muse/music chunk dependencies once Phase E runs.
- Resolver refuses missing required chunks, unapproved canon, archived chunks, dimension mismatch, and over-budget context packs.
- Token counter catches oversized `retrieval_text` and over-budget context packs before subagent handoff.
- Context pack tests assert no media blobs, provider logs, queue IDs, raw responses, or long histories are inlined.

## Summary

Final architecture: Craft produces dense, water-free durable chunks; Gemini Embedding 2 indexes them with explicit MRL profiles; chunk_resolver returns direct chunk paths and may materialize compact per-run context packs when helpful. New Season/Episode/Muse agents consume chunks/context packs rather than ordinary artifact dumps. This should be implemented as its own Phase RAG before serial and music-video activation, so Phase D/E build on a real retrieval foundation instead of temporary handoff hacks.
