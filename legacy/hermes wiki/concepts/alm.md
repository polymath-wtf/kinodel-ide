---
title: ALM — Audio Language Model analysis layer
created: 2026-05-17
updated: 2026-05-17
type: concept
tags: [kinodel, audio-gen, vlm, rag, embedding, music, patch, alm, music, muse, chunk]
sources: [current-chat:kinodel-pipeline-update-ideas]
confidence: medium
contested: false
contradictions: []
---

# ALM — Audio Language Model analysis layer

`alm.md` — proposed skill/reference for Audio Language Model style analysis: the audio equivalent of VLM analysis. ALM listens to a song or generated track and writes structured musical understanding: mood, genre, vocal style, instrumentation, section timings, energy curve, hooks and generation hints.

## Purpose

ALM is needed before saving [[music-chunk]] references and after generating new music in [[agent-muse-kinodel]]. Without ALM, RAG sees only filename/lyrics/prompt; with ALM, retrieval can search by “постепенный разгон к дропу”, “ломаный hyperpop vocal chop”, “melancholic late-night synth texture” and similar production-level vibes.

## Draft output

```json
{
  "schema": "kinodel.alm_analysis.v1",
  "audio_path": "refs/song.mp3",
  "duration_sec": 96,
  "summary": "...",
  "tags": {
    "genre": [],
    "mood": [],
    "vocal": [],
    "instrumentation": [],
    "production": []
  },
  "sections": [
    {"id": "intro", "start": 0.0, "end": 8.0, "description": "..."},
    {"id": "hook", "start": 8.0, "end": 22.0, "description": "..."}
  ],
  "energy_curve": [
    {"time": 0.0, "energy": 0.2},
    {"time": 18.0, "energy": 0.9}
  ],
  "visual_triggers": ["neon pulse", "fast cuts", "slow dreamy bridge"],
  "music_prompt_hints": "..."
}
```

## Integration points

- Before indexing favorite songs: raw MP3 → ALM analysis → [[music-chunk]].
- During production: generated `music.mp3` → ALM/timing refinement → [[music-video-pipeline]] storyboard and montage.
- For future QC: compare desired brief tags with generated song ALM tags.

## Open questions

- Which model/tool is ALM? Gemini gpt model , потому что она понимает много типов inputs и отлично стакается с нашим gemini-embedding-2
- How exact do timings need to be for ComfyUI img2vid: beat-level or section-level? Для понимания на каком моменте нужно делать переход, и какая строчка сейчас поётся, чтобы сделать раскадровку на весь клип.
- Should ALM output be stored inside `music_chunk`, or as separate `alm_analysis.json` linked by hash? alm анализ надо упаковывать в music_chunk.

## См. также

- [[music-chunk]] — storage target for analyzed songs.
- [[agent-muse-kinodel]] — consumer/producer of music analysis.
- [[music-video-pipeline]] — downstream timing-sensitive pipeline.
