---
title: Cinema Chunk — renamed final cinematic memory
created: 2026-05-17
updated: 2026-05-23
type: concept
tags: [kinodel, cinema, rag, embedding, video-pipeline, prompt-engineering, patch]
sources:
  - current-chat:kinodel-pipeline-update-ideas
  - user:webui:2026-05-22
  - [[agent-craft-kinodel]]
confidence: medium
contested: false
contradictions: []
---

# Cinema Chunk — renamed final cinematic memory

`cinema_chunk` — предлагаемое новое имя для текущего [[kinodel-final-chunk]], потому что `final_chunk` слишком общий, а старый pipeline был именно cinematic. После появления [[music-video-pipeline]], loop/gif pipelines и trend pipelines важно, чтобы final memory называлась по типу production output chunk.

## Почему переименовать

`final_chunk` сейчас означает “готовый cinematic release”: story, hook, main_frame, story_images, video_clips, final_video, conclusion. Но в universal Kinodel factory появятся outputs, где story может быть лишней или вторичной: music video, timelapse renovation, loop gif, reels trend clone, product UGC. Поэтому canonical type должен быть явным.

## Craft ownership

### Five-subject craft contract

Новый canonical shape для craft-owned chunks: `context`, `references`, `action`, `focus`, `timing`. Это вдохновлено [[gemini-omni-video-model]], но адаптировано под RAG/chunk architecture: `timing` означает только source-derived sequence/phase info, а не захардкоженные video timings. Downstream agents — [[agent-wardrobe-kinodel]], [[agent-storyboard-kinodel]], [[agent-filmmaker-kinodel]] — читают прежде всего `references` + `focus`, чтобы выбирать правильные media refs без догадок.

[[agent-craft-kinodel]] должен собирать `cinema_chunk` из approved final artifacts: story summary, main_frame, story images, video refs, final video и compact “what worked” notes. Craft добавляет semantic roles to refs (`@image`, `@video`, optional `@audio`) и пишет `retrieval_text`, чтобы later pipelines could retrieve this cinematic as inspiration/few-shot memory.

## Compatibility rule

- `cinema_chunk` = semantic successor of `final_chunk.json` for cinematic pipeline.
- На миграции можно поддержать alias: `final_chunk.json` остаётся filename v1, но внутри `schema` становится `kinodel.chunk.cinema.v1`.
- Новые pipeline-specific chunks могут иметь свои names: `music_video_chunk`, `loop_chunk`, `trend_chunk`.

## Draft schema

```json
{
  "schema": "kinodel.chunk.cinema.v1",
  "chunk_type": "cinema_chunk",
  "project_id": "...",
  "story": "compact final story memory",
  "hook": "...",
  "main_frame": {
    "handle": "@image1",
    "path": "outputs/main_frame.png",
    "url": "...",
    "role": "approved main style/identity frame",
    "take": ["overall style", "hero identity", "world mood"],
    "ignore": ["temporary render artifacts"]
  },
  "story_images": [],
  "video_clips": [],
  "final_video": {
    "handle": "@video1",
    "path": "outputs/final.mp4",
    "role": "completed cinematic result",
    "take": ["pacing", "visual language", "montage feel"],
    "ignore": ["provider-specific artifacts"]
  },
  "conclusion": "what worked visually",
  "craft": {
    "crafted_by": "craft-kinodel",
    "craft_version": "kinodel.craft.v1",
    "retrieval_text": "title: ... | text: story + hook + visual style + what worked",
    "quality_checks": ["final outputs selected", "refs have roles", "no raw production trace"]
  }
}
```

## См. также

- [[agent-craft-kinodel]] — crafts final cinematic memory and retrieval text.
- [[kinodel-final-chunk]] — current implementation page.
- [[kinodel-rag-chunk-architecture]] — RAG/index layer for chunks.
- [[avatar-chunk]] и [[music-chunk]] — reusable input memories, not final memories.
