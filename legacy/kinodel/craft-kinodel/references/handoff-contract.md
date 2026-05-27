# Craft-Kinodel Handoff Contract

## Producer → Craft

Producer or an import command gives Craft:

```json
{
  "project_id": "...",
  "chunk_type": "avatar_chunk | music_chunk | season_chunk | episode_chunk | cinema_chunk",
  "target_path": ".../chunk.json",
  "source_artifacts": [],
  "media_refs": [],
  "status_policy": "active | approved | completed | draft",
  "consumer_targets": ["wardrobe-kinodel", "storyboard-kinodel", "filmmaker-kinodel"]
}
```

Craft returns:

```json
{
  "status": "complete | blocked",
  "chunk_path": ".../chunk.json",
  "chunk_id": "...",
  "refs_count": 0,
  "retrieval_text_ready": true,
  "blocked_reason": null
}
```

Return status and paths only. Do not return full chunk JSON into the main Producer prompt unless explicitly debugging.

## Craft → Indexer

Craft writes fields needed by the indexer:

- `chunk_id`
- `chunk_type`
- `status`
- `context.summary`
- `references.items`
- `focus`
- `timing.summary` or not-applicable reason
- `retrieval_text`
- `embedding_profiles` if known
- source/media hashes if available

The indexer calls `gemini-embedding-2`; Craft does not have to call embeddings.

## Craft → Downstream Agents

Downstream agents receive a per-consumer handoff projection, never all global chunks or broad RAG results directly.

Preferred resolver result:

```json
{
  "consumer_agent": "episode-kinodel",
  "target_chunk_path": ".../episode_chunks/episode_02_chunk.json",
  "direct_chunks": [".../season_chunk.json", ".../episode_chunks/episode_01_chunk.json"],
  "compact_projections": {
    "season": {},
    "previous_completed_episode": {},
    "older_completed_episodes": [],
    "future_planned_neighbors": []
  },
  "selected_media_refs": [],
  "context_pack_path": "/tmp/kinodel/<project_id>/<run_id>/context_pack.episode-kinodel.json"
}
```

Serial episode default:

- current planned/active episode chunk: full/direct when token-safe;
- season chunk: compact season projection;
- previous completed episode: direct/compact ending_state, unresolved_hooks, character deltas, continuity constraints;
- older episodes: 3–6 bullet continuity summaries;
- future planned episodes: logline, promise, setup/payoff hints, and explicit “not completed facts” warning;
- media: selected refs only, each with handle/role/take/ignore/use_cases/priority.

They use refs by handle and role. They should not load all global chunks or raw vector results directly.

## Render Boundary

Render never reads broad RAG. Render receives explicit request artifacts and selected media refs only.

Craft may prepare refs that later appear in render requests, but provider payloads and upload handles are Render-owned.

## Validation Checklist

- Required fields present.
- No raw blobs.
- No provider queue IDs or logs.
- `references.items[*].handle` unique.
- `references.items[*].path` exists or is a resolvable URL/path from a known artifact.
- `action` describes agent usage, not provider execution.
- `focus` states drift constraints.
- `timing` is source-derived or explicitly not applicable.
