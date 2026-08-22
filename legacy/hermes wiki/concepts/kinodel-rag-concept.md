---
title: Kinodel + Gemini Embedding 2 — Векторизация Артефактов Кинопроизводства
created: 2026-05-04
updated: 2026-05-09
type: concept
tags:
  [
    kinodel,
    cinema,
    rag,
    embedding,
    gemini-embedding-2,
    ge2,
    vector,
    chunk,
    artifact,
    pipeline,
    multimodal,
    memory,
    knowledge-graph,
    retrieval,
    project-phase,
    ai-ml,
    video-pipeline,
    patch
  ]
sources:
  - wiki/entities/project-kinodel.md
  - wiki/concepts/cinematic-pipeline.md
  - wiki/concepts/kinodel-context-layers.md
  - .hermes/hermes-agent/tools/delegate_tool.py
  - raw/rag/mrl.md
  - raw/rag/embedding-2-hermes-deep-research.md
confidence: high
contested: false
contradictions: []
---

# Kinodel + Gemini Embedding 2 — Векторизация Артефактов Кинопроизводства

Концепт объединяет пайплайн агентного кинопроизводства [[project-kinodel]] с мультимодальной RAG-системой на базе [[gemini-embedding-2]]. Каждый артефакт pipeline (JSON, картинка, видео-шот) превращается в вектор и индексируется для семантического поиска, кросс-модального retrieval и долгосрочной памяти проекта.

## Проблема

В [[cinema-pipeline]] артефакты хранятся как immutable JSON-файлы в `projects/<id>/v<N>/`. Это хорошо для версионирования и review-ворот, но:

1. **Нет семантического поиска** по прошлым проектам — "найди мне сценарий в стиле noir с одиноким детективом"
2. **Нет кросс-модального поиска** — текстовый запрос не может найти референс-картинку или видео-шот
3. **Нет долгосрочной памяти** — сабагенты не помнят, какие промпты работали лучше в прошлых проектах
4. **Нет rerank'а** — при 50+ проектах поиск по метаданным (filename, tag) неэффективен

## Решение: Artifact-as-Vector

Каждый артефакт pipeline векторизуется через gemini-embedding-2 и складывается в sqlite-vec (или внешнюю векторную БД). Индекс — project-scoped, что позволяет агенту "вспоминать" предыдущие решения.

Размерность не хардкодится: используем MRL-размерности (256 / 768 / 1536 / 3072) в зависимости от типа поиска. Конкретное `output_dimensionality` — configurable property проекта, задаётся на старте pipeline и может меняться по результатам тестов.

### Артефакты → embeddable content

| Артефакт (стадия) | Тип | Что векторизуем | task_type prefix | Рекомендуемая dim |
|:---|:---|:---|:---|:---|
| `preproduction.json` | JSON | Текст logline + setting + tone + hero + conflict | text-only | 768 (default) |
| `story.json` | JSON | Сцены, action, dialogue (в master/continuation) | text-only | 768 (default) |
| `critic_notes.json` | JSON | Issue + fix (учимся на ошибках) | text-only | 768 (default) |
| `wardrobe.json` | JSON | hero_prompt, location_prompt, style_anchor | text-only | 768 (default) |
| `storyboard.json` | JSON | image_prompt + video_prompt + main_action | text + image | 768 (default) |
| shot images | PNG/JPEG | Сгенерированные кадры | image-only | 3072 (deep rerank) |
| `final.mp4` | MP4 | Результат монтажа (20–120s) | video-only | 768 (default) |

> **Важно:** dim — configurable. 768 для текстовых/смешанных (default), 3072 для visual-only deep rerank.

### Иерархия чанков: Master + Continuations + Character Profiles

Gemini-embedding-2 принимает до **8,192 токенов**, **до 6 изображений** и **до 120 секунд видео** (stable, April 2026). Конкретика по чанкам вынесена в `[[kinodel-chunk]]`.

**Default формат (1 чанк):** 20 sec, 5 shots, 6 images (1 hero-in-location anchor + 5 shot картинки). **Extended (> 6 images):** master + continuation chunks + character-profile chunks для secondary characters.

**Master Chunk (`chunk_type: "production-master"`)**
- Один на проект (версонируется), живёт у [[agent-producer-kinodel]] как "рукопись" фильма.
- Default: 6 картинок (hero-in-location anchor + shots 1–5) + весь текст production pack.

**Continuation Chunks (`chunk_type: "continuation"`)**
- Для extended формата (shots > 5). Каждый — до 6 shot-картинок + их описания.
- Содержат `master_id` + `continues_from: shot_id` + `shot_range: [N, M]`.

**Character Profile Chunks (`chunk_type: "character-profile"`)**
- Для secondary characters: внешность + роль в истории + до 5 картинок.
- Связан с master через `master_id`.

## Мультимодальные сценарии поиска (архивный RAG)

Благодаря unified semantic space gemini-embedding-2, поиск по *архиву прошлых проектов* работает так:

1. **Text → Image:** "грустный детектив в дождливом окне" → находит shot image из проекта Film-Noir-2026
2. **Image → Text:** загружаем референс-картинку → находит похожие `image_prompt` из storyboard'ов прошлых проектов
3. **Video → Text:** загружаем видео-шот → находит сценарные сцены с похожим action
4. **Text → Video:** "драматичный zoom-in на лицо" → находит shot videos с таким движением камеры
5. **Style transfer memory:** "примени style_anchor из проекта Cyberpunk-2025" → вектор style_anchor из `wardrobe.json` используется как query для поиска похожих проектов

Это *архивный* (cross-project) поиск. В активном производстве агенты редко его используют — они уже находятся в контексте своего production-чанка. Он нужен для вдохновения, проверки стилевых повторов и few-shot retrieval.

## Мультимодальные сценарии работы киноделов

Каждый агент в kinodel работает со своим профильным слоем production-чанка. Они — не "бездомные поисковики":

| Агент | С каким чанком работает | Как использует |
|:---|:---|:---|
| **ProducerAgent (продюсер)** | `production-master` | Держит approved `ContextLayer[]` на протяжении производства. Во время горячего pipeline не обязан пересчитывать embedding на каждом gate: фиксирует layers и двигает prompt-cache stack. На `release` или explicit archive checkpoint создаёт/обновляет production-master / continuation / video chunks append-only для RAG/time-travel. |
| **Agent-storytell-kinodel** | `production-master` + опционально `continuation` | Читает текущий (`is_active: true`) master-чанк. Пишет продолжение, сохраняя tone и style_anchor in-context. Не делает generic RAG-запрос без project_id. |
| **Agent-critic-kinodel** | `production-master` | Читает master-чанк и выдаёт diff (`CriticNotes`). ProducerAgent применяет diff через Append-Only — новая версия master, не in-place mutation. |
| **Agent-wardrobe-kinodel** | `production-master` | Читает master-чанк (hero, setting, style_anchor). Изменения style_anchor → новая версия master через ProducerAgent (Append-Only). |
| **Agent-storyboard-kinodel** | `production-master` + новые `continuation` | Default раскадровка = **5 shots** + 1 hero-in-location anchor = 6 images, влезает в один master-чанк. Shots 6+ — continuation чанки (каждый ≤ 6 images). При revise storyboard — Append-Only новой версии соответствующего чанка. |
| **Agent-filmmaker-kinodel** | `continuation` + `character-profile` | Для каждой shot-группы читает continuation-чанк. Для генерации видео с лицом персонажа — читает `character-profile` и выбирает FaceID по `use_case` (close_up / side_portrait / smile и т.д.) — Identity Anchor для консистентности. |
| **Agent-montage-kinodel** | все `continuation` + `production-master` + `audio-embed` | Собирает все continuation чанки и master для финального монтажа. Через ffmpeg извлекает аудио из final.mp4 → `audio-embed` chunk для архивного soundscape search. |
| **Agent-render-kinodel** | НЕ читает чанки | Получает RenderJob payload + ссылки на референсы (URL'ы из master-чанка), вызывает fal/Veo/Banana, пишет результат в `output_path`. LLM-контекст не держит — кешировать нечего. См. [[agent-render-kinodel]]. |

**Ключевой принцип:** агенты kinodel — не "бездомные поисковики", которые на каждом шаге делают `cosine_similarity` по всему vault. Они находятся **в контексте активного производства** (in-context production). У них на руках production-чанк — они добавляют его содержимое в LLM-запрос и продолжают работу.

RAG отдельно нужен только для:
- **Вдохновения перед стартом:** ProducerAgent может искать похожие проекты в global index.
- **Проверки стилевых повторов:** "не встречался ли уже такой style_anchor?" (Cross-project style memory).
- **Few-shot retrieval:** Storyteller может подтянуть 2–3 референсных сценария из архива, но это дополнение, не замена production-чанку.

## Production Context: как агенты работают с чанками

### Production-чанк как архивный снимок

ProducerAgent (продюсер) не делает embedding/index update после каждого user-review и не обновляет chunks **in-place**. В горячем пути он фиксирует approved `ContextLayer[]`; archival chunking запускается на `release` или explicit archive checkpoint. Когда архивный индекс всё-таки обновляется — используется Append-Only Soft Delete:

1. **Горячий путь:** `state.json.approved_layers[]` содержит L0-L6, а agents получают читаемые JSON/URL слои через [[kinodel-context-layers]]. Embedding не нужен для понимания текущего проекта.
2. **Archive checkpoint:** создаёт или обновляет `production-master` chunk:
   ```json
   {
     "project_id": "film-noir-2026-04",
     "chunk_type": "production-master",
     "chunk_id": "master-uuid-v1",
     "version": 1,
     "is_active": true,
     "previous_chunk_id": null,
     "artifact_path": "projects/film-noir-2026-04/v1/",
     "content_summary": "L0_BRIEF + L1_SCENARIO + L2_WARDROBE_REFS + L3/L4/L5/L6 release artifacts",
     "text_dim": 768,
     "visual_dim": 3072
   }
   ```
3. **Архивное обновление на release / archive checkpoint (Append-Only):** если проект завершён или пользователь явно просит сохранить промежуточный архив:
   - Старый master chunk: `is_active: false` (soft delete, вектор остаётся для Time-Travel RAG).
   - Новый master chunk: `is_active: true`, `version: N+1`, `previous_chunk_id: <old master>`.
   - Новый embedding вставляется в sqlite-vec (INSERT), старый не трогается.
   - sqlite-vec не получает UPDATE/DELETE — индекс HNSW остаётся здоровым.

### Implicit Prompt Caching для ProducerAgent

Gemini 2.5 Pro / Flash, Kimi 2.6 и Moonshot AI поддерживают **implicit (automated) prompt caching** через OpenRouter: никакого ручного `cache_control`, никаких дополнительных конфигураций. Cache write — бесплатно, cache read — **0.25x** стоимости обычного input.

**Как работает:** модель автоматически кэширует токены, если начальная часть message array совпадает между запросами. TTL ~3–5 минут. Minimum: 1024 tokens (Flash), 4096 tokens (Pro).

**Применение в kinodel:** не один захардкоженный `PROJECT_STATE`, а **слоёный cache stack**. Каждый approved artifact становится immutable `ContextLayer` (см. [[kinodel-context-layers]]). ProducerAgent добавляет слои в стабильном порядке: старые байты не меняются, новый слой добавляется ниже.

### Где этот prefix живёт в Hermes

Hermes `delegate_task(goal, context, ...)` собирает child system prompt как `goal + context + boilerplate` (см. `_build_child_system_prompt` в `tools/delegate_tool.py`). Поэтому:

- **`goal` = cacheable layer stack** — каноническая JSON-строка из стабильных `ContextLayer[]`, которые должны быть в prefix для текущего агента.
- **`context` = task layer stack + role instructions** — предыдущие outputs, нужные только текущему шагу, ссылка на `SKILL.md`, CriticNotes / user revise / failed_jobs.

**Что реально кэшируется:**
- ✅ **L0 survives everything:** `PreproductionPack` почти никогда не меняется, поэтому остаётся самым верхним reusable prefix.
- ✅ **Scenario revise не обязан ломать refs:** если правка сценария не меняет героя/локацию/стиль, обновляется только `L1_SCENARIO`; `L2_WARDROBE_REFS` остаётся approved.
- ✅ **Storyboard → Filmmaker layering:** filmmaker получает stable `L0+L1+L2`, а `L3_STORYBOARD_PLAN + L4_SHOT_IMAGES` как task context. При 1–2k токенах сценария это дешевле и эргономичнее, чем отдельная система сжатых prompt-представлений.
- ✅ **Montage не делает лишний lookup:** montage получает `L0_BRIEF` + `L6_SHOT_VIDEOS`; platform/audio/style уже в PreproductionPack.

**Важно:** cache prefix собирается из отдельных approved layers и работает без embedding. Master/continuation/video chunks нужны для archival RAG, сериалов, продолжений и time-travel; по умолчанию они индексируются на `release` или explicit archive checkpoint, а не на каждый approve.

### DO / DON'T для ContextLayer cache stack

- **DO** использовать `ContextLayer[]`, а не один фиксированный blob.
- **DO** сортировать layers в порядке `L0 → L1 → L2 → L3 → L4 → L5 → L6`.
- **DO** класть в `goal` только stable/cacheable слои для текущего агента.
- **DO** класть previous output конкретного шага (`Storyboard`, `shot_images`, `video_payloads`) в `context`, если он не нужен всем downstream агентам.
- **DO** использовать embeddings как RAG/time-travel/semantic navigation bonus;
- **DO** держать timestamp / `requested_at` ВНЕ cacheable layers (в `context` или dynamic suffix), иначе любая секунда убивает cache hit.
- **DO** держать render runtime state (`request_id`, `status_url`, `response_url`, retry counters) только в `render_queue.jsonl`; это не production context для сабагентов.
- **DO** сериализовать JSON с `sort_keys=true` и фиксированным `separators` — детерминизм.
- **DON'T** включать в cacheable layer поля, меняющиеся между сабагентами (например `requested_by`).
- **DON'T** ставить тяжёлые base64-картинки внутрь, если у провайдера отдельный image input — лучше URL. Хотя можно картинки сохранять в project артефакт, но нужно так-же сохранять и ссылку на оригинал url output.

**Пример message array для Storyboarder:**
```json
[
  {
    "role": "system",
    "content": "--- CONTEXT LAYERS ---\n[L0_BRIEF, L1_SCENARIO, L2_WARDROBE_REFS]\n--- END CONTEXT LAYERS ---"
  },
  {
    "role": "system",
    "content": "Твоя роль: Storyboarder Agent. Задача: сделать 5 image payloads + motion_help. Правила: [SKILL.md]"
  },
  {
    "role": "user",
    "content": "Если есть user revise / CriticNotes — они только здесь."
  }
]
```

**Пример message array для Filmmaker:**
```json
[
  {
    "role": "system",
    "content": "--- CONTEXT LAYERS ---\n[L0_BRIEF, L1_SCENARIO, L2_WARDROBE_REFS]\n--- END CONTEXT LAYERS ---"
  },
  {
    "role": "system",
    "content": "--- TASK CONTEXT ---\n[L3_STORYBOARD_PLAN, L4_SHOT_IMAGES]\n--- END TASK CONTEXT ---\nТвоя роль: Filmmaker. Задача: video_payloads + RenderJob[i2v]."
  },
  {
    "role": "user",
    "content": "Motion revise / failed shot ids / retry reason."
  }
]
```

**Результат:** верхние слои (`L0`, затем `L1`, затем `L2`) автоматически кэшируются. Чем дальше по pipeline, тем больше reusable prefix уже накоплено, а текущий агент получает только нужный delta-context без отдельной projection-системы.

**Не нужно:** вызывать `cache_control`, управлять TTL, создавать именованные кэши. Просто держи static prefix в начале prompts, а динамику — в конце.

**Embedding API (gemini-embedding-2):** кэширование не применимо — embedding вызовы атомарны, дёшевы и быстры. Эта оптимизация только для generation API (LLM-вызовов ProducerAgent / CriticAgent).

**Render API:** prompt caching тоже не применимо. RenderJob queue оптимизируется через durable resume: сохраняем provider `status_url` / `response_url`, чтобы повторный запуск не создавал новый paid request.

### Почему не in-place update?

Векторные базы (sqlite-vec с HNSW) плохо переносят UPDATE/DELETE: фрагментация, деградация скорости поиска, некорректные distance bounds. Append-Only решает все три проблемы за цену +3 KB на версию.

### Пример: agent-storytell-kinodel в production-контексте

Storyteller работает **не через RAG**, а через **in-context continuation**:

```
system_prompt: "Ты сценарист в активном производстве. Вот текущий production-чанк:
  [content из production-master (is_active: true): logline, tone, hero, setting, conflict, style_anchor]
  
  Пользователь просит: 'добавь сцену, где герой бежит по крышам'.
  
  Продолжи сценарий, сохраняя tone и style_anchor."
```

Если длина сценария превысила ~6000 токенов — storyteller:
1. Читает continuation chunk, соответствующий последней сцене.
2. Использует `continues_from` как контекст.
3. Добавляет новую сцену.
4. Если continuation заполнен — создаёт следующий.

Агент не ищет «какой сценарий похож?» — он **знает** project_id, читает production chunk и продолжает.

### Пример: agent-filmmaker-kinodel

Filmmaker получает задачу: «сделай видео для shot 7». Он:
1. Находит continuation chunk с `shot_range: [7, 12]`.
2. Извлекает: `shot_image + image_prompt + video_prompt + main_action + style_anchor`.
3. Если shot содержит персонажа — читает `character-profile` chunk, выбирает FaceID по `use_case`.
4. Формирует motion-prompt (с FaceID image + prompt) и делает i2v.
5. Не делает generic «Text → Video» RAG — контекст у него на руках.

## Project-scoped vs Global index

| Уровень | Scope | Использование |
|:---|:---|:---|
| Global | Все проекты в `projects/` | Поиск по архиву: "покажи все проекты в стиле anime" |
| Project | `projects/<id>/` | Текущий проект: production-master + continuation chunks |
| Stage | `projects/<id>/v<N>/<stage>` | Интра-стадийный поиск: "какие шоты уже одобрены?" |

## Техническая реализация (MVP)

**Хранение:** sqlite-vec (SIMD-ускоренный cosine similarity) в `projects/<id>/index.sqlite`

**Конфигурируемая размерность:**
```sql
-- проектная конфигурация dim
CREATE TABLE project_embedding_cfg (
  project_id TEXT PRIMARY KEY,
  text_dim INT,      -- e.g. 768 (default) или 256 (fast scan)
  visual_dim INT     -- e.g. 3072 (default) или 1536
);
```

**Векторные таблицы (пример с разделением):**
```sql
-- векторы для production-master и continuation текстовых частей
CREATE VIRTUAL TABLE embeddings_text USING vec0(
  chunk_id INTEGER,
  embedding FLOAT[768]  -- конфигурируется: может быть 256/768/1536
);

-- векторы для visual parts (images, videos)
CREATE VIRTUAL TABLE embeddings_visual USING vec0(
  chunk_id INTEGER,
  embedding FLOAT[3072]  -- конфигурируется: может быть 1536/3072
);
```

**Почему разные таблицы:** query с text-only (768-dim) не совместим с visual (3072-dim). Разделяем по типу или храним оба вектора в одной таблице с префиксами `vector_768`, `vector_3072`.

**Гибридный поиск (RRF):**
- sqlite-vec: `cosine_similarity(query_vector, embedding)`
- FTS5: `bm25_score(content)`
- Combine: `score = 1/(k + rank_vec) + 1/(k + rank_fts)`

## Метаданные для каждого чанка

**Production-master:**
```json
{
  "project_id": "film-noir-2026-04",
  "chunk_id": "master-uuid-v3",
  "version": 3,
  "chunk_type": "production-master",
  "is_active": true,
  "previous_chunk_id": "master-uuid-v2",
  "artifact_path": "projects/film-noir-2026-04/v1/",
  "text_dim": 768,
  "visual_dim": 3072,
  "style_anchor": "noir, high contrast, rain, neon reflections",
  "tone": "melancholic",
  "format": "16:9",
  "platform": "youtube",
  "agent": "agent-drama",
  "continuation_chunks": ["chunk-uuid-1", "chunk-uuid-2"],
  "character_profile_ids": ["char-uuid-1"],
  "audio_embed_id": "audio-uuid-1"
}
```

**Continuation:**
```json
{
  "project_id": "film-noir-2026-04",
  "chunk_type": "continuation",
  "is_active": true,
  "master_id": "master-uuid-v3",
  "previous_chunk_id": null,
  "continues_from": 7,
  "shot_range": [7, 12],
  "agent": "agent-storyboard-kinodel"
}
```

**Audio-embed (soundscape):**
```json
{
  "project_id": "film-noir-2026-04",
  "chunk_type": "audio-embed",
  "is_active": true,
  "video_chunk_id": "video-uuid-1",
  "audio_type": "soundscape",
  "extracted_by": "ffmpeg"
}
```

## Open questions

1. **Оптимальная размерность:** какой dim optimal для production-master (768 vs 1536)? Тесты MTEB показывают 768 > 97.5%, но для сложных multimodal сюжетов с текстом + картинками может быть нужен 1536. Решаем бенчмарком.
2. **Cross-project style memory:** как агрегировать `style_anchor` из множества проектов для генерализации стиля? Скорее всего — отдельный global `style_index`.
3. **Миграция между agent-чатами:** если сессия агента прерывается — как ProducerAgent восстанавливает `active_chunk_id`? Через `state.json` → chunk_id lookup.

> **Решенные вопросы** (подробности — см. [[kinodel-chunk]]):
> - ✅ Default format: 20 sec, 5 shots, 6 images — влезает в 1 master chunk. Extended: 60 sec ⇒ continuation + character-profile chunks.
> - ✅ Revise: Append-Only Soft Delete (не in-place). Новый чанк + `is_active: true`, старый `is_active: false`. Time-Travel RAG + здоровый HNSW.
> - ✅ Video: один video-visual chunk + отдельный audio-embed (ffmpeg). Видео до 120s, аудио до 180s.
> - ✅ Bulk indexing — Batch API (50% cheaper).
> - ✅ Identity Anchor (FaceID): 6 face references per character для кросс-шотовой консистентности.
> - ✅ **Implicit Prompt Caching.** Gemini 2.5 Pro/Flash и Kimi 2.6 (через OpenRouter) — automated implicit caching: никакого `cache_control`, cache read по 0.25x. Static prefix (production-master content: logline + hero + style_anchor + 6 images) — начало каждого message array, dynamic suffix (CriticNotes diff, user questions) — в конце. TTL ~3–5 минут. ProducerAgent и CriticAgent получают автоматическое ускорение review-циклов без дополнительной конфигурации.

## См. также

- [[kinodel-chunk]] -- детальная стратегия чанкования, token budget, dimensionality, Batch API
- [[gemini-embedding-2]] -- entity модели (спецификация, API, MRL, task types)
- [[project-kinodel]] -- мастер-entity кинопроизводства
- [[cinema-pipeline]] -- ориентированный граф стадий с артефактами
- [[agent-producer-kinodel]] -- оркестратор, владеющий production-чанком
- [[embedding-2-hermes-deep-research]] -- интеграция с Hermes + sqlite-vec + FTS5 + RRF
