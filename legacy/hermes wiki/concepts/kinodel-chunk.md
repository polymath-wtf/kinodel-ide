---
title: Kinodel Chunking — Стратегия упаковки в Gemini Embedding 2
created: 2026-05-04
updated: 2026-05-22
type: concept
tags:
  [
    kinodel,
    cinema,
    chunk,
    embedding,
    gemini-embedding-2,
    ge2,
    mrl,
    token-budget,
    multimodal,
    rag,
    vector,
    production-master,
    continuation,
    patch
  ]
sources:
  - wiki/concepts/kinodel-rag-concept.md
  - wiki/concepts/kinodel-context-layers.md
  - wiki/concepts/cinematic-pipeline.md
  - wiki/entities/project-kinodel.md
  - wiki/entities/agent-producer-kinodel.md
  - raw/rag/gemini-embedding-2-docs-zbs.md
  - raw/rag/gemini-token-counter.md
  - user:webui:2026-05-22
  - [[agent-craft-kinodel]]
confidence: high
contested: false
contradictions: []
---

# Kinodel Chunking — Стратегия упаковки в Gemini Embedding 2

Документ описывает, как именно упаковывать артефакты кинопайплайна [[project-kinodel]] в чанки для `gemini-embedding-2`. Главный принцип: **максимально плотно упаковать в один эмбеддинг (single aggregated embedding)** всё, что входит в ограничения, а то, что не влезает — разносить в continuation-чанки с жёсткой связностью.

## Лимиты gemini-embedding-2 (официальные, stable — April 2026)

| Лимит | Значение | Примечание |
|:---|:---|:---|
| Текст | до **8,192 токенов** | Общий лимит на весь `contents` массив |
| Изображения | max **6** за request | PNG, JPEG |
| Аудио | max **180 секунд** | MP3, WAV |
| Видео | max **120 секунд** | MP4, MOV. Codecs: H264, H265, AV1, VP9. **Видео не обрабатывает аудио-трек** — only visual stream. |
| PDF | max **6 страниц** | — |
| **Aggregation behavior** | Single aggregated embedding для всех parts в одном `contents` | `[text, img1, img2]` → один вектор, а не три. Если нужно отдельно — Batch API. |
| Output dim | 128–3072, рекомендуется 768 / 1536 / 3072 | `output_dimensionality` param |

Критически для kinodel: **не более 6 картинок + текстовый пакет в один request**. Если у нас 9 shots — нужно минимум 2 continuation-части.

## Default format: 20-sec mini-cinematic (1 chunk)

Для фазы отладки и экономии чанков **хардкодим default формат**, который гарантированно влезает в один production-master chunk:

| Параметр | Значение | Почему |
|:---|:---|:---|
| **Длительность** | **20 секунд** | 5 shots × 4s = 20s. Видео ≤120s, так что final.mp4 visual = один чанк. |
| **Картинки в master** | **6** | 1 hero-in-location anchor + 5 storyboard shots = ровно лимит 6. |
| **Shots** | **5** | По 4 секунды каждый. Cinematic структура: Hook → Setup → Escalation → Climax → Button. |
| **Токенов text** | ~1800–3000 | Preproduction + 5 shot descriptions + wardrobe + style_anchor = уверенно влезает в 8192. |

**Расчёт длительности:** 5 shots × 4 sec = 20 sec. Это **mini-cinematic** — компактный формат для отработки pipeline. Можем делать и 60-секундные (12 shots), но тогда shots 6–12 уходят в continuation chunks.

## Extended format: 60-sec cinematic (master + continuation)

Для более длинных сюжетов:

| Параметр | Значение |
|:---|:---|
| Длительность | **60 секунд** |
| Shots | **12** (12 × 5s) |
| Master chunk images | 1 hero-in-location anchor + shots 1–5 = **6 images** |
| Continuation chunk #1 | shots 6–11 (6 images) |
| Continuation chunk #2 | shot 12 (1 image) |
| Вторичные персонажи | Отдельный chunk (char ref + его роль в истории + до 5 картинок) |

**Правило:** secondary characters + их story context (где появляются, какая функция) — отдельный chunk типа `character-profile` со ссылкой на `master_id`. Это позволяет добавлять/убирать персонажей без перепаковки master.

## Token budgeting: сколько текста реально влезает

В 8192 токена за один request влезает следующее rough-оценка для **default 20-sec формата**:

| Контент | ~Токенов | Комментарий |
|:---|---:|:---|
| logline + setting + tone + hero + conflict | 300–600 | PreproductionPack compact |
| Раскадровка (5 shots × prompt по 80–120 слов) | 600–1000 | image_prompt + video_prompt + main_action |
| Reference descriptions (hero_prompt + location_prompt + style_anchor) | 200–400 | Wardrobe |
| CriticNotes (ревью + фиксы) | 100–300 | diff-mode, только правки |
| Сценарий (compact beats) | 500–1200 | story beats для 5 shots; raw story вроде Dodik example обычно остаётся компактным |
| **Header padding / metadata / JSON wrappers** | ~300–500 | JSON keys, chunk metadata |
| **До 6 изображений** | ~0–200 visual tokens | Зависит от resolution |
| **Итог: default production pack** | **~2000–3500** | **Уверенно влезает**, запас ~4K+ токенов |

> **Максимальная норма для master chunk**: текст до ~6000 токенов + 6 картинок. Всё что свыше — continuation.

### Heuristic

Текстовый чанк может быть **значительно больше** классического RAG-чанка (512–1024), потому что gemini-embedding-2 агрегирует text + images. Лучше упаковать весь логический production-pack, чем резать по 512 токенов и терять связность персонажа / стиля / continuity.

## Иерархия чанков

### Craft layer

Перед индексированием reusable chunks должны проходить через [[agent-craft-kinodel]]. Craft назначает `@image`/`@video`/`@audio` handles, описывает role/take/ignore/use_cases для каждого media ref, пишет compact `retrieval_text` и проверяет, что в JSON нет raw provider logs, base64 blobs или лишней production trace. Это CRAFT-inspired подход из prompt engineering, адаптированный под chunk context, а не под video timing.

### Master Chunk (`chunk_type: "production-master"`)

Единый чанк, который держит в руках ProducerAgent. **Default содержит 6 картинок** (1 hero-in-location anchor + 5 shots):

```json
{
  "chunk_id": "master-uuid",
  "project_id": "film-noir-2026-04",
  "chunk_type": "production-master",
  "version": 3,
  "format": "mini-cinematic",
  "duration_sec": 20,
  "shot_count": 5,
  "contents_payload": {
    "text_parts": [
      "logline: Одинокий детектив в дождливом городе расследует исчезновение...",
      "setting: Neon-lit megacity, rain-soaked streets, 2077...",
      "hero: Detective Crow, 40s, trench coat, haunted eyes...",
      "style_anchor: noir, high contrast, rain, neon reflections, film grain...",
      "tone: melancholic, slow-burning tension...",
      "shots[1-5]: [{shot_id:1, image_prompt:'...', video_prompt:'...', main_action:'...'}, ...]"
    ],
    "image_parts": [
      "hero_in_location.png",
      "shot_01_image.png",
      "shot_02_image.png",
      "shot_03_image.png",
      "shot_04_image.png",
      "shot_05_image.png"
    ]
  },
  "metadata": {
    "text_token_est": 2200,
    "image_count": 6,
    "total_shot_count": 5,
    "continuation_ids": [],
    "character_profile_ids": [],
    "agents_involved": ["dram-agent", "storyteller", "wardrobe", "storyboarder"],
    "video_embedded": true,
    "video_duration_sec": 20
  }
}
```

**Video для default формата:** final.mp4 (20s) эмбеддится как **один video chunk** отдельно, но связан с master через `video_embedded: true`. Или, если нужен unified вектор — можно включить video как `[video]` part в тот же `contents`, но **single embedding** для text + images + video = 1 vector. Рекомендация: **видео — отдельный chunk** `video-visual` (dim 768/1536) для гибкости, но если нужен единый "смысл всего фильма" — aggregate в master.

### Continuation Chunk (`chunk_type: "continuation"`)

Для extended формата (shots > 5):

```json
{
  "chunk_id": "cont-uuid-1",
  "project_id": "film-noir-2026-04",
  "chunk_type": "continuation",
  "master_id": "master-uuid",
  "continues_from": 6,
  "shot_range": [6, 11],
  "contents_payload": {
    "text_parts": [
      "shots[6-11]: [{shot_id:6, image_prompt:'...', video_prompt:'...', main_action:'...'}, ...]"
    ],
    "image_parts": [
      "shot_06_image.png",
      "shot_07_image.png",
      "shot_08_image.png",
      "shot_09_image.png",
      "shot_10_image.png",
      "shot_11_image.png"
    ]
  },
  "metadata": {
    "text_token_est": 900,
    "image_count": 6,
    "prev_continuation_id": null,
    "next_continuation_id": "cont-uuid-2"
  }
}
```

### Character Profile Chunk (`chunk_type: "character-profile"`)

Для вторичных персонажей (extended format). **Ключевая фича — Identity Anchor (FaceID)** для строгой консистентности лица между shots:

```json
{
  "chunk_id": "char-uuid-1",
  "project_id": "film-noir-2026-04",
  "chunk_type": "character-profile",
  "master_id": "master-uuid",
  "character_name": "The Informant",
  "contents_payload": {
    "text_parts": [
      "name: The Informant, alias 'Sparrow'",
      "appearance: short man, nervous eyes, worn leather jacket...",
      "role_in_story: appears in shots 3 and 7, delivers clue about the clock...",
      "relationship_to_hero: former informant, unreliable ally..."
    ],
    "image_parts": [
      "informant_reference.png"
    ],
    "face_references": [
      {
        "type": "close_up",
        "image": "char_closeup.png",
        "prompt": "frontal face, neutral expression, sharp features, soft rim lighting...",
        "use_case": "default shot, any angle where face is primary focus"
      },
      {
        "type": "side_portrait",
        "image": "char_side.png",
        "prompt": "profile view, sharp jawline, ear visible, same lighting conditions...",
        "use_case": "side angle shots, walking scenes"
      },
      {
        "type": "full_body",
        "image": "char_fullbody.png",
        "prompt": "standing pose, complete outfit, proportions consistent with close-up...",
        "use_case": "wide shots, establishing, walking into frame"
      },
      {
        "type": "hips_level",
        "image": "char_hips.png",
        "prompt": "medium shot, hands visible, torso proportions match full-body reference...",
        "use_case": "dialogue shots, interaction scenes"
      },
      {
        "type": "smile",
        "image": "char_smile.png",
        "prompt": "genuine smile, eyes crinkled, same face structure as close_up...",
        "use_case": "happy, relief, reunion scenes"
      },
      {
        "type": "in_main_location",
        "image": "char_location.png",
        "prompt": "character in primary environment, ambient light interaction on face...",
        "use_case": "environmental integration, color/lighting consistency check"
      }
    ]
  },
  "metadata": {
    "appears_in_shots": [3, 7],
    "image_count": 7,
    "face_reference_count": 6,
    "identity_anchor_enabled": true
  }
}
```

**Identity Anchor — как используется filmmaker-agent:**
- Перед генерацией i2v/video агент анализирует shot: требуемый ракурс, эмоция, окружение.
- Выбирает подходящий `face_references` по `use_case` (например, `smile` для joyful shot, `side_portrait` для tracking shot сбоку).
- Включает выбранный FaceID image + его `prompt` в запрос к генератору (Fal.ai / Flux), обеспечивая кросс-шотовую консистентность лица.
- Модели генерации склонны к "галлюцинациям" черт лица при смене ракурса — Identity Anchor нивелирует это за счёт многовекторного референса.

## Как вызывать embed_content для наших чанков

Модель: **`gemini-embedding-2`** (stable, April 2026).

Главное — `gemini-embedding-2` **не поддерживает `task_type`**. Вместо этого — текстовый prefix в prompt'е. Для кинодела используем:

```python
from google import genai
from google.genai import types

client = genai.Client()

# Master chunk — text + images aggregated
result = client.models.embed_content(
    model="gemini-embedding-2",
    contents=[
        "task: search result | query: Production pack for film-noir-2026-04. "
        "Logline: ... Setting: ... Hero: ... Style anchor: ... "
        "Shots: ...",
        types.Part.from_bytes(data=open("hero.png", "rb").read(), mime_type="image/png"),
        types.Part.from_bytes(data=open("shot_01.png", "rb").read(), mime_type="image/png"),
        # ... до 6 images total
    ],
    config=types.EmbedContentConfig(
        output_dimensionality=768
    )
)

# Получаем ОДИН aggregated embedding для всей композиции
embedding = result.embeddings[0].values
len(embedding)  # 768
```

> ⚠️ **Важно**: `[text, img1, img2]` в одном contents → single embedding. Это ровно то, что нужно для master-чанка.

### Batch API для нескольких чанков

Так как запрос может подключать **несколько чанков одновременно** (master + continuation + character-profile), используем **Batch API** — дешевле на 50%:

```python
# Batch API: отправляем несколько contents за один batch call
# Каждый contents = один chunk (master, cont-1, char-profile)
# Получаем отдельный embedding для каждого chunk'а

batch_requests = [
    {"contents": [master_text_part, *master_images]},
    {"contents": [cont_text_part, *cont_images]},
    {"contents": [char_text_part, *char_images]},
]

results = client.models.embed_content(
    model="gemini-embedding-2",
    contents=batch_requests,  # batch mode
    config=types.EmbedContentConfig(output_dimensionality=768)
)
```

Batch API используем **всегда** при bulk indexing (создание/обновление всех чанков проекта за один проход).

## Выбор dimensionality (не хардкодим)

| Dim | MTEB Score¹ | Память/вектор | Когда использовать для kinodel |
|:---|---:|---:|:---|
| 3072 | baseline (100%) | 12 KB | Deep rerank / style-critical visual search |
| 1536 | 68.17 (≈99.9%) | 6 KB | Высокоточные visual+text mixed чанки |
| **768** | **67.99 (≈99.7%)** | **3 KB** | **Default для production-master / continuation / character-profile** |
| 512 | 67.55 | 2 KB | Быстрый first-pass scan |
| 256 | 66.19 | 1 KB | Архивный scan 1000+ проектов |
| 128 | 63.31 | 0.5 KB | Не рекомендуется для production |

¹ MTEB для gemini-embedding-001 (reference proxy). gemini-embedding-2 имеет auto-normalization.

**Рекомендация для kinodel:**
- **Production-master / continuation / character-profile**: `768` (default).
- **Visual-only deep rerank**: `1536` или `3072`.
- **Global архивный scan**: `256` first-pass.
- **Конкретная dim задаётся в project_embedding_cfg**, не глобально.

## Archive checkpoint strategy: Append-Only (Soft Delete)

При изменении контента пользователем на user-review gate горячий pipeline обновляет `ContextLayer[]` и `approved_layers[]`, но **не обязан** пересчитывать embedding. Embedding/chunk update запускается на `release` или explicit archive checkpoint.

**Проблема in-place updates:** Большинство векторных БД (включая sqlite-vec) плохо переносят частые UPDATE/DELETE. HNSW-индекс фрагментируется, скорость поиска деградирует.

**Решение — Append-Only с Soft Delete:**

1. **ProducerAgent создаёт новую архивную версию** production-master chunk (новый `chunk_id`, новый embedding), а не перезаписывает старый.
2. **Старый чанк** помечается `is_active: false` (soft delete) — вектор остаётся в БД, но фильтруется при поиске.
3. **Новый чанк** получает `is_active: true`, `version: N+1`, `previous_chunk_id` → старый чанк.
4. **Все continuation chunks** обновляют `master_id` на новый master chunk_id.

```json
{
  "chunk_id": "master-uuid-v4",
  "project_id": "film-noir-2026-04",
  "chunk_type": "production-master",
  "version": 4,
  "is_active": true,
  "previous_chunk_id": "master-uuid-v3",
  "contents_payload": { ... }
}
```

**Преимущества Append-Only:**
- **Индекс здоровый:** sqlite-vec получает только INSERT, никаких UPDATE/DELETE в HNSW.
- **Time-Travel RAG:** можем вернуться к любой версии проекта по `chunk_id`.
- **Diff-история:** `previous_chunk_id` образует связный список версий.
- **Поиск:** `WHERE is_active = 1 AND chunk_type = 'production-master'` — всегда один актуальный master.

**Cost:** +1 вектор на каждый archive checkpoint (~3 KB). По умолчанию checkpoints редкие: release, season/episode boundary или явная команда "заархивируй".

## Video: визуальный и аудио ландшафт

### Визуальный чанк (video-visual)

**Все видео kinodel = один video-visual chunk.** Обоснование:
- Final.mp4 до 60 секунд (default) или до 120 секунд (extended max) — оба влезают в лимит 120s видео.
- Модель семплирует 32 frames uniformly. Для 20-секундного — 1.6 fps (достаточно). Для 60-секундного — 0.53 fps (достаточно для вайба / тона).
- **Аудио-трек final.mp4 не обрабатывается** моделью при video embedding.

```python
# Video chunk — один на весь final.mp4 (20-120 sec)
video_result = client.models.embed_content(
    model="gemini-embedding-2",
    contents=[
        types.Part.from_bytes(data=open("final.mp4", "rb").read(), mime_type="video/mp4")
    ],
    config=types.EmbedContentConfig(output_dimensionality=768)
)
```

Если синематик превысит 120 секунд (редкий edge-case) — разбивать на video segments ≤120s, но **в рамках kinodel такого не планируем**.

### Аудио чанк (audio-embed): звуковой ландшафт

Для эстетики (киберпанк, нео-нуар) звуковой дизайн несет до 50% "вайба" сцены. Gemini-embedding-2 **не читает аудио из mp4** — только visual stream.

**Решение: FFMPEG-экстракция аудио-дорожки → отдельный audio-embed chunk:**

```bash
# Extract audio from final.mp4
ffmpeg -i final.mp4 -vn -ar 44100 -ac 2 -b:a 192k final_audio.mp3
```

```python
# Audio chunk — отдельный embedding
audio_result = client.models.embed_content(
    model="gemini-embedding-2",
    contents=[
        types.Part.from_bytes(data=open("final_audio.mp3", "rb").read(), mime_type="audio/mpeg")
    ],
    config=types.EmbedContentConfig(output_dimensionality=768)
)
```

**Объединение визуального и аудио ландшафта:** при финальном индексе video-visual и audio-embed chunks связаны через `chunk_id` (или `video_chunk_id` в audio metadata):

```json
{
  "chunk_id": "audio-uuid-1",
  "project_id": "film-noir-2026-04",
  "chunk_type": "audio-embed",
  "video_chunk_id": "video-uuid-1",
  "contents_payload": {
    "audio": "final_audio.mp3",
    "duration_sec": 20
  },
  "metadata": {
    "audio_type": "soundscape",  // or "voiceover", "music", "ambient"
    "extracted_by": "ffmpeg",
    "sample_rate": 44100
  }
}
```

**Use cases audio-embed:**
- Архивный поиск: "найди проект с меланхоличным саксофоном" — cosine similarity по audio embeddings.
- Генерация сиквелов: аудио-вайб первого фильма как query для contextual continuation.
- Mood matching: voiceover tone consistency между shots.

## Storage cost estimation

### Default 20-sec mini-cinematic (5 shots, 1 chunk матрица):

| Сущность | Кол-во chunks | Dim | Размер |
|:---|---:|---:|---:|
| production-master (text + 6 images) | 1 | 768 | 3 KB |
| final.mp4 video | 1 | 768 | 3 KB |
| **Итого** | **2** | mixed | **6 KB** |

### Extended 60-sec cinematic (12 shots + secondary character + audio):

| Сущность | Кол-во chunks | Dim | Размер |
|:---|---:|---:|---:|
| production-master (text + 6 images: hero-in-location + shots 1–5) | 1 | 768 | 3 KB |
| continuation #1 (shots 6–11, 6 images) | 1 | 768 | 3 KB |
| continuation #2 (shot 12, 1 image) | 1 | 768 | 3 KB |
| character-profile (informant + face references) | 1 | 768 | 3 KB |
| final.mp4 video-visual | 1 | 768 | 3 KB |
| final.mp4 audio-embed (via ffmpeg) | 1 | 768 | 3 KB |
| **Итого** | **6** | mixed | **18 KB** |

На практике: **6–20 KB векторных данных на проект** (зависит от кол-ва archive checkpoints и continuation chunks). sqlite-vec scan на 1000 проектов < 5ms.

## Decision matrix: какой chunk используем

| Ситуация | Chunk type | Dim | Method |
|:---|:---|:---|:---|
| Completed 20-sec production release | production-master | 768 | embedContent([text + 6 images]) |
| Extended (> 5 shots) | continuation | 768 | embedContent([shots text + ≤6 images]) |
| Secondary character | character-profile | 768 | embedContent([char text + ref image]) |
| Final video (20–120s) | video-visual | 768 | embedContent([video ≤120s]) |
| Voiceover/music context | audio-embed | 768 | embedContent([audio ≤180s]) |
| Сравнение референса с кадром pixel-to-pixel | visual-single | 3072 | embedContent([image]) |
| Глобальный архивный стилевой поиск | quick-scan | 256 | embedContent([text prefix]) |
| Bulk indexing всех чанков проекта | any | 768 | **Batch API** (50% cheaper) |

## Resolved decisions

1. ✅ **Видео — один video-visual чанк + отдельный audio-embed.** Все final.mp4 (20–120s) эмбеддятся как single video-visual chunk. Аудио-дорожка выделяется ffmpeg и эмбеддится отдельно как audio-embed chunk. Звуковой ландшафт доступен для архивного поиска и mood matching.
2. ✅ **Archive checkpoint — Append-Only Soft Delete.** При release или явном archive checkpoint создаётся новый master chunk (новый chunk_id + embedding), старый помечается `is_active: false`. sqlite-vec получает только INSERT — никакого фрагментирования HNSW. Time-Travel RAG: можем вернуться к архивным версиям.
3. ✅ **Default format: 20 sec, 5 shots, 6 images.** Это base case для отработки pipeline: 1 hero-in-location anchor + 5 storyboard shots. Extended (60s, 12 shots) — через continuation + character-profile chunks.
4. ✅ **Batch API — да.** Используем для bulk indexing всех чанков проекта за один проход (master + continuation + character-profile + video + audio). Дешевле на 50%.
5. ✅ **Identity Anchor (FaceID).** Для строгой консистентности персонажей в character-profile chunk хранятся 6 face references (close_up, side_portrait, full_body, hips_level, smile, in_main_location) с `prompt` и `use_case`. Filmmaker-agent выбирает подходящий по контексту shot'а — нивелирование галлюцинаций при смене ракурса.
6. ✅ **Implicit Prompt Caching.** Gemini 2.5 Pro/Flash, Kimi 2.6 и Moonshot AI (через OpenRouter) — automated implicit caching: никакого `cache_control`, cache read по 0.25x. Static prefix собирается из `ContextLayer[]` L0-L6, dynamic suffix (CriticNotes diff, user questions) — в конце. TTL ~3–5 минут. Embedding API (gemini-embedding-2) не участвует — это оптимизация только generation-вызовов.

## См. также

- [[kinodel-rag-concept]] — высокоуровневая концепция Artifact-as-Vector
- [[gemini-embedding-2]] — entity модели (спецификация, MRL, task types)
- [[cinema-pipeline]] — stage map и артефакты
- [[agent-producer-kinodel]] — продюсер, владеющий production-master
- raw/rag/gemini-embedding-2-docs-zbs.md — полная официальная документация
- raw/rag/gemini-token-counter.md — правила подсчёта токенов