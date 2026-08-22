---
title: Muse-Kinodel — music/vibe agent for music-video production
created: 2026-05-17
updated: 2026-05-23
type: entity
tags: [agent, kinodel, audio-gen, music, rag, chunks, music-video, patch]
sources:
  - [[music-video-pipeline]]
  - [[kinodel-rag-chunk-architecture]]
confidence: high
contested: false
contradictions: []
---

# Muse-Kinodel — music/vibe agent for music-video production

`muse-kinodel` is the Kinodel music/vibe planner for [[music-video-pipeline]]. It reads a brief plus RAG-selected `music_chunk` context and writes `muse_output.json` + provider-neutral `music_request.json`.

Muse does not call Suno/fal/ComfyUI directly. Render/audio adapter owns provider calls and writes `outputs/music.mp3` plus `render_results/music_result.json`.

## Runtime position

```text
p0_music_briefgate
→ chunk_resolver selects music/avatar/cinema chunk paths and optional context pack
→ p1_muse: muse writes muse_output.json + music_request.json
→ p2_music_render: render/audio adapter writes music result
→ p3_style_frame_plan and downstream timed visuals
```

## Inputs

Required:

```text
brief.json
pipeline_spec.json
selected chunk paths / optional context pack
```

Context pack should include:

- selected `music_chunk` summaries, ALM notes, section/energy maps;
- selected audio refs by path/handle, not inline audio;
- optional avatar/style/cinema chunks if clip needs visual continuity;
- copyright/safety rule: use vibe, structure, instrumentation, energy; do not clone melody or copyrighted lyrics.

## RAG policy

Default profile: `muse_inspiration_balanced`; optional `muse_audio_deep` for top candidate audio rerank.

| Source | Mode | Dim | Rule |
|:---|:---|---:|:---|
| brief | direct | none | production intent |
| `music_chunk.retrieval_text` | RAG | 768 | main semantic retrieval |
| ALM summary / energy curve | selected text | 768 | section/timing guidance |
| audio media refs | optional rerank | 1536/3072 | high-fidelity vibe/texture only |
| prior generated music chunks | optional RAG | 768 | self-style memory |

Budget: 3000–6000 context tokens.

## Outputs

```json
{
  "schema": "kinodel.muse_output.v1",
  "project_id": "...",
  "status": "complete",
  "context_used": {
    "context_pack": "selected chunk paths / optional context pack",
    "music_chunks": ["music:..."]
  },
  "lyrics": {"text": "...", "sections": []},
  "music_prompt": "provider-neutral generation prompt",
  "vibe_dna": {
    "genre_tags": [],
    "mood_tags": [],
    "instrumentation": [],
    "energy_curve": []
  },
  "timing_skeleton": [],
  "music_request_path": "music_request.json"
}
```

`music_request.json` may include provider-neutral `adapter_profile`, `lyrics`, `prompt`, `style`, `title`, `instrumental`, `duration_target_seconds`, and `jobs[]`. It must not include API keys, callback URLs, queue IDs, raw provider responses, retries, costs, or logs.

## Boundaries

- Planner only: no provider calls.
- No direct copying of copyrighted lyrics unless user explicitly owns/provides/permits the text.
- Audio files stay as refs/paths; no inline mp3/wav in prompts or context packs.
- Muse writes music spine; Storyboard/Filmmaker/Montage align visuals to approved music/timing later.

## См. также

- [[music-video-pipeline]]
- [[music-chunk]]
- [[agent-muse]]
- [[kinodel-rag-chunk-architecture]]

