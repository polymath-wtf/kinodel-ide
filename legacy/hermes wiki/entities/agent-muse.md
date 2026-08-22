---
title: Muse — генерация и анализ музыки
created: 2026-04-30
updated: 2026-05-23
type: entity
tags: [agent, ai-art, audio-gen, music, rag, gemini-embedding-2, muse]
sources:
  - raw_data/work/agents/Muse/muse.md
  - [[agent-muse-kinodel]]
confidence: high
contested: false
contradictions: []
---

# Muse — агент генерации и анализа музыки

`agent-muse` — общий музыкальный агент: генерирует lyrics/prompt, анализирует треки, декомпозирует vibe/sections/energy и может готовить `music_chunk` для RAG. В Kinodel production роль отделена как [[agent-muse-kinodel]].

## Что меняется для Kinodel RAG

Старый подход “для каждого аудиофайла отдельный chunk” недостаточен. Нужен crafted `music_chunk`:

- audio path/ref, not inline mp3/wav;
- ALM summary;
- energy curve and timing sections;
- lyrics summary or owned/permitted lyrics excerpt;
- generation hints;
- `retrieval_text` for [[gemini-embedding-2]];
- explicit forbidden use: do not clone exact melody/lyrics/artist identity.

## Пайплайн Muse вне Kinodel

```text
vibe prompt
→ lyrics + music prompt
→ provider request by allowed runtime
→ music result
→ decomposition / ALM analysis
→ crafted music_chunk
→ RAG index
```

## Пайплайн Muse внутри Kinodel

```text
brief + selected chunk paths / optional context pack
→ [[agent-muse-kinodel]] writes muse_output.json + music_request.json
→ render/audio adapter produces outputs/music.mp3
→ Muse/Craft package resulting music_chunk after approval/completion
```

Muse-Kinodel is planner-only; provider calls are Render-owned.

## Gemini Embedding 2 usage

- Text/summary retrieval: 768 dim `default_rag`.
- Audio high-fidelity rerank: 1536 or 3072 dim only for top candidates.
- Query format: `task: search result | query: muse-kinodel needs ...`.
- Document format: `title: ... | text: music_chunk; ...`.

## См. также

- [[agent-muse-kinodel]]
- [[music-chunk]]
- [[kinodel-rag-chunk-architecture]]
- [[gemini-embedding-2]]

