---
title: Episode Chunk — continuity memory for serial Kinodel
created: 2026-05-17
updated: 2026-05-23
type: concept
tags: [kinodel, rag, embedding, storytelling, agent-memory, video-pipeline, prompt-engineering, patch]
sources:
  - current-chat:kinodel-universal-runtime-serial-pipeline
  - user:webui:2026-05-22
  - [[agent-craft-kinodel]]
confidence: medium
contested: false
contradictions: []
---

# Episode Chunk — continuity memory for serial Kinodel

`episode_chunk` — compact durable memory capsule для одной завершённой серии в [[serial-pipeline]]. Он помогает следующей серии продолжить с правильного места: что произошло, кто изменился, какие visual/audio anchors approved, какие нерешённые hooks и cliffhangers должны payoff позже.

## Why not reuse cinema_chunk only

[[cinema-chunk]] фиксирует завершённый cinematic artifact как standalone memory. `episode_chunk` должен быть continuity-oriented: он важен не только как финальный output, но и как input для следующей серии, [[agent-season-kinodel]], [[agent-episode-kinodel]], wardrobe/storyboard/filmmaker stages.

## Craft ownership

### Five-subject craft contract

Новый canonical shape для craft-owned chunks: `context`, `references`, `action`, `focus`, `timing`. Это вдохновлено [[gemini-omni-video-model]], но адаптировано под RAG/chunk architecture: `timing` означает только source-derived sequence/phase info, а не захардкоженные video timings. Downstream agents — [[agent-wardrobe-kinodel]], [[agent-storyboard-kinodel]], [[agent-filmmaker-kinodel]] — читают прежде всего `references` + `focus`, чтобы выбирать правильные media refs без догадок.

После montage / final episode acceptance Producer может вызвать [[agent-craft-kinodel]], чтобы собрать `episode_chunk` из `story.json`, render manifests, final video refs, approved visual/audio anchors и continuity deltas. Craft не меняет сюжет серии; он компактно упаковывает approved результат для будущего retrieval и handoff.

## Proposed schema

```json
{
  "schema": "kinodel.episode_chunk.v1",
  "project_id": "serial_project",
  "season_id": "season_01",
  "episode_id": "episode_01",
  "status": "completed",
  "title": "Episode title",
  "summary": "compact plot recap",
  "ending_state": {
    "where_we_left": "exact continuation point",
    "cliffhanger": "open hook",
    "emotional_state": "main character mood"
  },
  "character_deltas": [
    {"avatar_chunk_id": "hero", "change": "lost trust in mentor"}
  ],
  "continuity_facts": [],
  "visual_anchors": [
    {
      "handle": "@image1",
      "path": "outputs/episode_01_anchor.png",
      "role": "approved act/episode visual anchor",
      "take": ["location state", "wardrobe state", "emotional color"],
      "ignore": ["render artifact", "background extra identity"]
    }
  ],
  "audio_anchors": [],
  "open_threads": [],
  "payoffs_required": [],
  "final_video": "outputs/episode_01/final.mp4",
  "craft": {
    "crafted_by": "craft-kinodel",
    "craft_version": "kinodel.craft.v1",
    "retrieval_text": "title: ... | text: plot recap + ending state + continuity facts + open threads",
    "quality_checks": ["completed episode only", "refs have roles", "no full transcript unless explicitly required"]
  }
}
```

## What it must contain

- plot recap only as compact story state, not full script;
- exact ending point for next episode;
- character relationship changes;
- visual continuity facts: outfits, locations, props, injuries, weather, style;
- selected outputs refs from render manifests;
- open threads and required payoffs;
- links to [[avatar-chunk]] IDs, not duplicated avatar images.

## What it must not contain

- provider queue IDs, raw prompts, costs, retries, debug logs;
- full episode transcript unless explicitly required;
- huge base64/audio/video blobs;
- stale temporary paths from `/tmp/kinodel`.

## Retrieval behavior

Для episode N runtime should load:

1. [[season-chunk]] compact approved season bible;
2. target planned/current `episode_chunk`;
3. `episode_chunks/episode_{N-1}_chunk.json` required previous context;
4. optionally all older episode chunks as summarized RAG results;
5. relevant [[avatar-chunk]] refs.

## См. также

- [[agent-craft-kinodel]] — crafts completed episode memory and reference bindings.
- [[serial-pipeline]] — pipeline that consumes and writes episode chunks.
- [[season-chunk]] — approved season bible that episode chunks extend.
- [[kinodel-rag-chunk-architecture]] — chunk resolver and MRL context pack design.
- [[avatar-chunk]] — character identity anchors used across episodes.

