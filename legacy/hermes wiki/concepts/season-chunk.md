---
title: Season Chunk — approved season bible for serial Kinodel
created: 2026-05-17
updated: 2026-05-23
type: concept
tags: [kinodel, rag, embedding, storytelling, agent-memory, video-pipeline, prompt-engineering, patch]
sources:
  - current-chat:kinodel-two-stage-serial-pipeline
  - user:webui:2026-05-22
  - [[agent-craft-kinodel]]
confidence: medium
contested: false
contradictions: []
---

# Season Chunk — approved season bible for serial Kinodel

`season_chunk` — final output первого этапа [[serial-pipeline]]: approved season bible/checkpoint, который становится input вместо обычного `brief.json` для второго этапа production каждой серии. Он фиксирует сезонный замысел, персонажей, стиль, параметры production, episode list и approved visual anchors.

## Why it exists

Сезон может долго правиться через [[agent-critic-kinodel]] до approval. После approval нужен durable artifact, который можно использовать в будущих сессиях без повторного BriefGate. `season_chunk` превращает Stage 1 в завершённый product: approved context package for episode production.

## Craft ownership

### Five-subject craft contract

Новый canonical shape для craft-owned chunks: `context`, `references`, `action`, `focus`, `timing`. Это вдохновлено [[gemini-omni-video-model]], но адаптировано под RAG/chunk architecture: `timing` означает только source-derived sequence/phase info, а не захардкоженные video timings. Downstream agents — [[agent-wardrobe-kinodel]], [[agent-storyboard-kinodel]], [[agent-filmmaker-kinodel]] — читают прежде всего `references` + `focus`, чтобы выбирать правильные media refs без догадок.

После p4 season checkpoint Producer может вызвать [[agent-craft-kinodel]], чтобы собрать `season_chunk` из approved `season_plan.json`, `episodes/*.json`, avatar refs и render result manifests. Craft отвечает не за переписывание сезона, а за упаковку approved смысла: compact season summary, continuity bible, episode refs, avatar bindings, visual anchor roles и `retrieval_text` для RAG.

## Proposed schema

```json
{
  "schema": "kinodel.season_chunk.v1",
  "project_id": "serial_project",
  "season_id": "season_01",
  "status": "approved",
  "source_artifacts": {
    "brief": "brief.json",
    "season_plan": "season_plan.json",
    "episode_chunks": ["episode_chunks/episode_01_chunk.json"],
    "visual_anchors_result": "render_results/season_anchors_result.json"
  },
  "production_defaults": {
    "aspect_ratio": "9:16",
    "episode_count": 4,
    "episode_duration": "short-form",
    "style": "..."
  },
  "season_summary": "compact approved season arc",
  "characters": [],
  "avatar_chunks": [],
  "episodes": [
    {
      "episode_id": "episode_01",
      "status": "planned",
      "logline": "...",
      "must_happen": [],
      "visual_anchor": {
        "handle": "@image1",
        "path": "outputs/episode_01_anchor.png",
        "role": "episode visual anchor",
        "take": ["tone", "main visual premise"],
        "ignore": ["temporary render artifacts"]
      }
    }
  ],
  "continuity_bible": [],
  "approved_gate": "p4_season_checkpoint",
  "craft": {
    "crafted_by": "craft-kinodel",
    "craft_version": "kinodel.craft.v1",
    "retrieval_text": "title: ... | text: season summary + characters + continuity bible + episode loglines",
    "quality_checks": ["approved only", "episode refs compact", "no draft revision history"]
  }
}
```

## Relation to episode chunks

- `season_chunk` is the global approved season authority.
- Planned [[episode-chunk]] artifacts are produced from the approved `season_plan.json` after p4; completed versions are produced after each episode montage.
- For episode N, [[agent-episode-kinodel]] reads `season_chunk` + target planned/current `episode_chunk` + previous completed episode chunks.
- Older/future planned episode chunks can be retrieved compactly with lower dimension embeddings / MRL-style retrieval to preserve broad context without flooding prompts.

## What it must not contain

- provider queue IDs, raw render payloads, debug logs, costs;
- every draft revision from the season development phase;
- full chat history;
- unapproved critic notes except final resolved constraints.

## См. также

- [[agent-craft-kinodel]] — crafts approved season chunk and retrieval text.
- [[serial-pipeline]] — pipeline that writes and consumes this chunk.
- [[agent-season-kinodel]] — creates season_plan and episode blueprints before this chunk is approved.
- [[agent-episode-kinodel]] — consumes this chunk during per-episode p1_story.
