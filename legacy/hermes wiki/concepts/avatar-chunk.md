---
title: Avatar Chunk — identity/style capsule для Kinodel
created: 2026-05-17
updated: 2026-05-23
type: concept
tags: [kinodel, rag, embedding, avatar, character, style-consistency, img2img, prompt-engineering, patch]
sources:
  - current-chat:kinodel-pipeline-update-ideas
  - user:webui:2026-05-22
  - [[agent-craft-kinodel]]
confidence: medium
contested: false
contradictions: []
---

# Avatar Character Chunk — identity/style capsule для Kinodel

`avatar_chunk` — reusable мультимодальный чанк для персонажа, аватара или persona identity. Он хранит 1–6 картинок, compact character prompt, vibe/характер, style notes и опционально voice reference MP3. Цель — держать персонажа консистентным между разными проектами [[project-kinodel]], а не пересобирать identity заново в каждом cinematic или music-video production.

## Зачем нужен

Сейчас [[pipeline-kinodel]] делает visual identity в рамках одного проекта через main_frame/story frames. `avatar_chunk` поднимает identity на уровень библиотеки: [[agent-wardrobe-kinodel]] может брать готовые face/body/emotion references для main_frame, [[agent-storyboard-kinodel]] может выбирать нужные позы/эмоции для кадров, а [[agent-filmmaker-kinodel]] — прокидывать voice.mp3 refs в video workflows.

## Craft ownership

### Five-subject craft contract

Новый canonical shape для craft-owned chunks: `context`, `references`, `action`, `focus`, `timing`. Это вдохновлено [[gemini-omni-video-model]], но адаптировано под RAG/chunk architecture: `timing` означает только source-derived sequence/phase info, а не захардкоженные video timings. Downstream agents — [[agent-wardrobe-kinodel]], [[agent-storyboard-kinodel]], [[agent-filmmaker-kinodel]] — читают прежде всего `references` + `focus`, чтобы выбирать правильные media refs без догадок.

`avatar_chunk` должен крафтиться через [[agent-craft-kinodel]]. Craft не просто складывает картинки в папку: он инспектит refs, назначает `@image` handles, пишет role/take/ignore/use_cases и делает compact `retrieval_text` для [[gemini-embedding-2]]. Это похоже на CRAFT-style binding из prompt engineering, но без video timing hardcode.

Для avatar refs особенно важно поле `ignore`: background, random lighting, плохой crop, temporary props и чужие персонажи не должны случайно попасть в identity prompt.

## Draft schema

```json
{
  "schema": "kinodel.chunk.avatar.v1",
  "chunk_id": "avatar:<slug>:v1",
  "chunk_type": "avatar_chunk",
  "title": "character/persona name",
  "status": "active",
  "media": {
    "images": [
      {
        "handle": "@image1",
        "path": "refs/front.png",
        "role": "front_closeup",
        "prompt": "stable prompt for this ref",
        "take": ["face structure", "hair silhouette", "wardrobe palette"],
        "ignore": ["background", "temporary lighting"],
        "use_cases": ["wardrobe main frame", "storyboard close-up", "filmmaker face reference"]
      },
      {
        "handle": "@image2",
        "path": "refs/full_body.png",
        "role": "full_body",
        "prompt": "...",
        "take": ["body proportions", "outfit silhouette"],
        "ignore": [],
        "use_cases": ["wide shots", "wardrobe continuity"]
      }
    ],
    "voice_mp3": null
  },
  "identity": {
    "character_prompt": "stable appearance and wardrobe description",
    "vibe": "temperament, behavior, emotional palette",
    "negative_identity_drift": ["different face", "age drift", "wrong outfit"]
  },
  "craft": {
    "crafted_by": "craft-kinodel",
    "craft_version": "kinodel.craft.v1",
    "retrieval_text": "title: ... | text: compact identity + vibe + ref roles",
    "quality_checks": ["all images have roles", "take/ignore explicit", "no raw render logs"]
  },
  "usage": {
    "wardrobe": "use as identity source for main_frame or episode anchors",
    "storyboard": "select pose/emotion refs per shot",
    "filmmaker": "select specific reference by role/use_case for i2v/flf2v workflows"
  }
}
```

## Rules

- Не больше 6 картинок в один `gemini-embedding-2` aggregate request; если refs больше — делать continuation или отдельные pose chunks.
- `avatar_chunk` не должен хранить project runtime logs, provider payloads или render attempts.
- Картинки должны иметь semantic roles: `front_closeup`, `side_profile`, `full_body`, `emotion_smile`, `emotion_angry`, `in_environment`.
- Если pipeline использует `avatar_chunk`, `brief.json`/pipeline spec должен ссылаться на `avatar_chunk_id`, а не копировать весь prompt.
- Каждый media ref должен иметь `handle`, `role`, `take`, `ignore`, `use_cases`; это основной контракт для downstream prompt agents.

## Открытые вопросы

- Нужен ли отдельный `voice_chunk` или `voice_mp3` достаточно держать внутри avatar? Текущий ответ: voice.mp3 можно держать внутри `avatar_chunk`, пока не появится отдельная voice pipeline.
- Как валидировать identity similarity: VLM judge, face embedding, CLIP-style similarity или human gate? Текущий рабочий подход: semantic roles + prompt/use_case для каждой картинки, а агенты читают весь chunk включая подсказки.
- Глобальная библиотека нужна: avatars живут в `~/chunk/avatars/<avatar_id>/avatar_chunk.json`, а проект может хранить копию/зеркало в `~/projects/<project_id>/v1/`.

## См. также

- [[agent-craft-kinodel]] — будущий владелец chunk crafting и reference binding.
- [[music-chunk]] — audio inspiration chunk для Muse.
- [[cinema-chunk]] — переименование текущего final cinematic memory.
- [[kinodel-rag-chunk-architecture]] — как chunks индексируются и попадают в subagent context packs.
