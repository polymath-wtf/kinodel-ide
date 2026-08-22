---
title: Serial Pipeline — two-stage multi-episode Kinodel production flow
created: 2026-05-17
updated: 2026-05-23
type: concept
tags: [kinodel, pipeline, video-pipeline, storytelling, serial, rag, chunks, patch]
sources:
  - [[kinodel-rag-chunk-architecture]]
confidence: high
contested: false
contradictions: []
---

# Serial Pipeline — two-stage multi-episode Kinodel production flow

`serial-pipeline` is a two-stage Kinodel production family:

1. `serial_season.v1` creates and approves a whole season.
2. `serial_episode.v1` produces one episode at a time using approved season and episode memory chunks.

The pipeline must use real chunk/RAG context. Season and Episode agents receive selected chunk paths and, only when useful, a per-run resolver context pack. They do not receive raw project dumps.

## Core decision

- [[agent-season-kinodel]] writes one `season_plan.json` with embedded episode blueprints from `brief.json` plus RAG-selected avatar/style/music/cinema chunk inspiration.
- After p4 approval, Producer/Craft writes [[season-chunk]] and planned [[episode-chunk]] artifacts for every episode in the approved season plan.
- [[agent-episode-kinodel]] runs per episode at Stage 2 `p1_story`, reading approved `season_chunk`, the target planned `episode_chunk`, previous completed `episode_chunk` if needed, and avatar refs through selected chunk paths/context pack.
- After episode montage/completion, Producer/Craft writes a new completed version of that episode's [[episode-chunk]].

## Stage 1 — `serial_season.v1`

```text
p0_season_briefgate
→ chunk_resolver: select season context chunks for season-kinodel
→ p1_season_plan: season-kinodel writes season_plan.json with embedded episode blueprints
→ p2_season_anchor_plan: wardrobe writes one visual anchor request per episode
→ p3_season_anchor_render: render episode posters/anchors
→ p4_season_checkpoint: hard ReviewGate with season story + image per episode
→ p5_season_chunks: Craft/Producer writes approved season_chunk.json + planned episode_chunks/*.json
```

Stage 1 stops at `season_chunk` plus `planned` episode chunks; it does not storyboard/render full episodes. Stage 1 may render episode poster/anchor images, and Craft binds those refs into each planned episode chunk.

## Stage 2 — `serial_episode.v1`

```text
p0_episode_context_gate: validate approved season_chunk, selected planned episode_chunk, previous completed episode_chunk if N>1
→ chunk_resolver: select current/neighbor episode chunks for episode-kinodel
→ p1_story: episode-kinodel writes detailed story.json for episode_N
→ p2_episode_anchor_plan: wardrobe writes act-level visual anchors
→ p3_episode_anchor_render
→ p4_episode_story_gate: hard ReviewGate for story + act anchors
→ p5_storyboard_plan
→ p6_story_images_render
→ p7_story_images_gate: hard ReviewGate
→ p8_video_plan
→ p9_video_render
→ p10_montage
→ p11_episode_chunk: Craft/Producer writes completed episode_chunk.json
```

## RAG dependencies

### Season stage

```json
{
  "context_pack": {
    "consumer_agent": "season-kinodel",
    "profile": "season_architect_balanced",
    "max_context_tokens": 9000,
    "include": ["avatar_context", "optional_music_inspiration", "optional_cinema_inspiration"]
  }
}
```

### Episode stage

```json
{
  "context_pack": {
    "consumer_agent": "episode-kinodel",
    "profile": "episode_writer_balanced",
    "max_context_tokens": 8000,
    "include": ["season_context", "target_planned_episode_chunk_full", "previous_completed_episode_chunk", "neighbor_episode_chunks_summary", "avatar_context", "older_continuity_context"]
  }
}
```

Dependency rules:

- `season_chunk.status == approved` before Stage 2.
- `episode_chunks/episode_N_chunk.json` exists with `status == planned|approved` and is selected.
- For N > 1, `episode_{N-1}_chunk.status == completed` is mandatory.
- Future planned episode chunks can guide foreshadowing; future completed-state fields cannot be treated as facts.
- Avatar chunks are required or strongly recommended for identity stability.

## Editing/invalidation

- If an unproduced episode changes: edit `season_plan.json` or the planned episode chunk, recraft/reindex affected chunks, then rerun `episode-kinodel` p1 for that episode.
- If a completed episode changes: regenerate its `episode_chunk`, re-index it, and mark later episodes `needs_continuity_review`.
- If whole-season canon changes: return to Stage 1 edit loop, write a new `season_chunk` version, recraft affected planned episode chunks, and invalidate derived resolver context packs.

## Wardrobe generalization

Wardrobe must support explicit anchor modes:

- `per_episode` for Stage 1 season anchors;
- `per_act` for Stage 2 episode anchors;
- `single` remains cinematic-compatible.

Wardrobe consumes selected avatar/style refs from direct chunk paths or context pack; it should not scan global RAG itself.

## Episode story formula

- 5 acts by default.
- Dan Harmon Story Circle as emotional motion.
- Each act changes choice, danger, relationship, information, or visual state.
- Each episode pays off one thread and opens/sharpens another.

## См. также

- [[agent-season-kinodel]]
- [[agent-episode-kinodel]]
- [[season-chunk]]
- [[episode-chunk]]
- [[avatar-chunk]]
- [[kinodel-rag-chunk-architecture]]
