---
title: Music Video Pipeline — Kinodel pipeline variant
created: 2026-05-17
updated: 2026-05-23
type: concept
tags: [kinodel, video-pipeline, audio-gen, music-video, rag, chunks, patch]
sources:
  - [[kinodel-rag-chunk-architecture]]
confidence: high
contested: false
contradictions: []
---

# Music Video Pipeline — Kinodel pipeline variant

`music-video-pipeline` is the Kinodel production family where music is the spine. It uses [[agent-muse-kinodel]] and real `music_chunk` RAG, not ordinary artifact dumps.

Muse plans music and timing; Render/audio adapter produces audio; visual agents align image/video/montage stages to approved music and section timing.

## Route: `music_video.v1`

```text
p0_music_briefgate
→ chunk_resolver: select music/avatar/cinema chunks and optional context pack for muse-kinodel
→ p1_muse: muse writes muse_output.json + music_request.json
→ p2_music_render: render/audio adapter writes outputs/music.mp3 + render_results/music_result.json
→ p3_style_frame_plan: wardrobe writes style/main-frame request from muse_output + selected chunks
→ p4_music_style_gate: approve song + visual style, hard stop
→ p5_timed_storyboard_plan: storyboard writes timed image prompts from lyrics/sections
→ p6_timed_images_render
→ p7_music_visual_gate: hard stop
→ p8_timed_video_plan
→ p9_timed_video_render
→ p10_music_montage: align clips to music.mp3
→ p11_music_video_chunk / cinema_chunk
```

## What stays common

- Producer is a state machine and passes paths/status, not giant JSON bodies.
- Specialists own artifacts and return status only.
- Render executes explicit request artifacts.
- ReviewGates remain hard stops.
- Provider payloads, queue IDs, callbacks, retries, costs, and logs stay in Render/runtime scratch, not durable planner artifacts.

## What changes

- `storytell` is skipped/replaced by Muse for music-video narrative spine.
- Storyboard unit can be `lyric_line`, `section`, `beat`, `bar_range`, `drop`, `hook`, or `transition`, not just “shot”.
- `music_chunk` RAG can provide inspiration, ALM energy curves, section maps, and audio refs.
- Timed visuals must align to `music_timing`/sections from Muse and/or music analysis.
- Montage is first-class and obeys audio timeline.

## Required RAG dependencies

```json
{
  "context_pack": {
    "consumer_agent": "muse-kinodel",
    "profile": "muse_inspiration_balanced",
    "max_context_tokens": 6000,
    "include": ["music_inspiration", "optional_avatar_context", "optional_cinema_style_context"]
  }
}
```

Rules:

- `music_chunk` refs are inspiration unless explicitly project-owned/generated.
- Audio paths may be included as refs; audio blobs are never inlined.
- Lyrics are summarized/selected unless user owns/permits full text use.
- Audio high-fidelity retrieval uses 1536/3072 only for top candidate rerank.

## Required artifacts

- selected chunk paths / optional context pack
- `muse_output.json`
- `music_request.json`
- `render_results/music_result.json`
- `music_timing.json` or timing inside `muse_output.json`
- `wardrobe_request.json` or style-frame request artifact
- `storyboard_requests.json` with timing per job
- `video_requests.json` with `start_sec`, `end_sec`, `duration_sec`, `audio_anchor`
- `render_results/*` manifests
- `outputs/music.mp3`, `outputs/final.mp4`
- `music_video_chunk.json` / `cinema_chunk.json`

## Muse ownership

[[agent-muse-kinodel]] writes:

- lyrics / lyrics sections;
- music prompt;
- vibe DNA / style tags;
- timing skeleton;
- selected `music_chunk` refs;
- provider-neutral `music_request.json`.

Render/audio adapter writes:

- `outputs/music.mp3`;
- `render_results/music_result.json`.

Muse must not call Suno/fal/ComfyUI directly.

## MVP limits

- Start with 15–30 seconds.
- 5–8 timed image prompts before scaling.
- Music-video activation depends on [[kinodel-patch-phase-rag]] and then [[kinodel-patch-phase-e-music-video]].

## См. также

- [[agent-muse-kinodel]]
- [[agent-muse]]
- [[music-chunk]]
- [[alm]]
- [[kinodel-rag-chunk-architecture]]

