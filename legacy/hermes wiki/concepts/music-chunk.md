---
title: Music Chunk — audio reference memory для Muse-Kinodel
created: 2026-05-17
updated: 2026-05-23
type: concept
tags: [kinodel, rag, embedding, audio-gen, music, prompt-engineering, agent-memory, patch]
sources:
  - current-chat:kinodel-pipeline-update-ideas
  - user:webui:2026-05-22
  - [[agent-craft-kinodel]]
confidence: medium
contested: false
contradictions: []
---

# Music Chunk — audio reference memory для Muse-Kinodel

`music_chunk` — чанк любимой песни или музыкального референса для вдохновения [[agent-muse-kinodel]]. Он хранит MP3/WAV, lyrics/transcript при наличии, music prompt, ALM-анализ, теги настроения, жанра, структуры и production tricks. Это не production output, а reusable reference memory.

## Роль в архитектуре

В [[music-video-pipeline]] Muse получает brief + top-K `music_chunk` references из RAG на [[gemini-embedding-2]], затем пишет `lyrics`, `music_prompt`, vibe DNA and `music_request.json` for music provider. `outputs/music.mp3` генерирует Render-kinodel from that `music_request.json`. [[alm]] нужен до индексации: он превращает сырое аудио в нормальное описание, по которому Muse сможет “выкупать” вайб.

## Craft ownership

### Five-subject craft contract

Новый canonical shape для craft-owned chunks: `context`, `references`, `action`, `focus`, `timing`. Это вдохновлено [[gemini-omni-video-model]], но адаптировано под RAG/chunk architecture: `timing` означает только source-derived sequence/phase info, а не захардкоженные video timings. Downstream agents — [[agent-wardrobe-kinodel]], [[agent-storyboard-kinodel]], [[agent-filmmaker-kinodel]] — читают прежде всего `references` + `focus`, чтобы выбирать правильные media refs без догадок.

`music_chunk` крафтит [[agent-craft-kinodel]]. Он назначает `@audio`/`@doc` handles, связывает audio/lyrics/ALM/prompt с ролями и пишет `take/ignore` правила. Для музыки это критично: Muse должна брать energy curve, instrumentation, vocal delivery, structure и mood, но не копировать melody или copyrighted lyrics.

## Draft schema

```json
{
  "schema": "kinodel.chunk.music.v1",
  "chunk_id": "music:<artist-or-style>:<slug>:v1",
  "chunk_type": "music_chunk",
  "status": "active",
  "media": {
    "audio": {
      "handle": "@audio1",
      "audio_path": "refs/song.mp3",
      "mime_type": "audio/mpeg",
      "duration_sec": 180,
      "role": "music vibe reference",
      "take": ["energy curve", "instrumentation", "vocal delivery", "section contrast"],
      "ignore": ["exact melody", "copyrighted lyrics", "artist identity cloning"],
      "use_cases": ["muse inspiration", "montage mood reference"]
    },
    "lyrics_path": "refs/lyrics.txt"
  },
  "analysis": {
    "alm_summary": "what the song feels like and how it moves",
    "genre_tags": ["hyperpop", "sad trap"],
    "energy_curve": ["intro low", "drop high", "bridge float"],
    "vocal_style": "...",
    "instrumentation": ["808", "glossy synth", "pitched vocal chops"],
    "section_notes": [
      {"section": "intro", "event": "low energy setup"},
      {"section": "chorus", "event": "peak hook energy"}
    ]
  },
  "generation_hints": {
    "music_prompt": "compact inspiration prompt, not copyright-copy",
    "avoid": ["direct melody clone", "recognizable copyrighted lyrics"]
  },
  "craft": {
    "crafted_by": "craft-kinodel",
    "craft_version": "kinodel.craft.v1",
    "retrieval_text": "title: ... | text: ALM summary + tags + energy + generation hints",
    "quality_checks": ["audio has role", "take/ignore explicit", "lyrics not copied into prompt unless allowed"]
  }
}
```

## Indexing strategy

- Audio part: MP3/WAV ≤180s для `gemini-embedding-2`; длинные треки режутся на logical sections: intro/verse/drop/bridge/outro.
- Text part: ALM summary + tags + section map + generation hints.
- Retrieval: query от Muse должен искать не только жанр, но и energy curve, hook mechanics, vocal delivery, texture.
- MRL: broad search обычно 768 text; high-fidelity audio rerank может использовать 1536/3072.

## См. также

- [[agent-craft-kinodel]] — владелец music chunk crafting и reference binding.
- [[alm]] — Audio Language Model analysis layer.
- [[agent-muse-kinodel]] — агент, который использует эти чанки.
- [[avatar-chunk]] — визуальный equivalent для персонажей.
