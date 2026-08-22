---
title: Cinema Pipeline — Агентное Кинопроизводство (от брифа до релиза)
created: 2026-04-30
updated: 2026-05-09
type: concept
tags: [cinema, pipeline, agent-architecture, video-gen, workflow, project-phase, mvp, kinodel, prompt-caching, render-queue, patch]
sources:
  - wiki/entities/agent-producer-kinodel.md
  - wiki/concepts/kinodel-rag-concept.md
  - wiki/concepts/kinodel-context-layers.md
  - wiki/concepts/kinodel-render-requests.md
  - .hermes/hermes-agent/tools/delegate_tool.py
confidence: high
contested: false
contradictions: []
---

# Cinema Pipeline — Агентное Кинопроизводство

Главный пайплайн агентного кинопроизводства: от первой реплики юзера до собранного мини-фильма. [[agent-producer-kinodel]] выступает оркестратором / продюсером, делегирует работу сабагентам. Wiki сохраняет legacy wikilinks `agent-<role>-kinodel`, но target skill packages используют имена без `agent-`: `kinodel/producer-kinodel`, `kinodel/storyboard-kinodel`, `kinodel/render-kinodel`. Между этапами стоят **`ReviewGate`** ворота, на которых юзер может вносить правки.

> Этот документ — **шаблон todolist'а**. Каждый запуск производства = инстанс этого пайплайна с состоянием по этапам.

## Принципы

1. **Pipeline-as-state.** Производство = ориентированный граф этапов с явными артефактами на входе/выходе.
2. **User-review gates.** Между фазами — ручное одобрение или правки. Любой этап можно «откатить» и переснять.
3. **Каждый сабагент — узкая роль.** Один меседж, один артефакт, без раздувания.
4. **ProducerAgent держит pipeline в руках,** двигает таски, проверяет наличие артефакта, вызывает следующего исполнителя.
5. **Артефакты — JSON-файлы на диске.** Контракт каждого артефакта описан **текстом в `SKILL.md`** соответствующего агента.
6. **Layered context stack → implicit prompt caching.** Каждый approved artifact становится `ContextLayer` (`L0_BRIEF → L1_SCENARIO → L2_WARDROBE_REFS → ...`). ProducerAgent собирает request по одному правилу: `goal = stable cacheable layers`, `context = task-specific layers + role skill + dynamic suffix`. Старые слои остаются byte-identical, новые добавляются ниже. См. [[kinodel-context-layers]] и [[kinodel-rag-concept]].
7. **Render-as-autonomous-worker.** Тяжёлые ассеты (картинки, видео) генерируются НЕ внутри планирующих агентов и НЕ как долгий LLM `delegate_task`. [[agent-render-kinodel]] читает `RenderJob` payload'ы, запускается как автономный worker, делает provider submit, сразу сохраняет `request_id` / `status_url` / `response_url`, экономно polling'ит статус до terminal state, скачивает outputs и пишет wake-up event для ProducerAgent в `render_events.jsonl` + `state.json.render_last_summary`. Планирующие агенты завершаются за секунды → их implicit-cache не успевает протухнуть → ProducerAgent может «спать» в `stage=rendering:<batch>` и проснуться, когда worker завершился.
8. **Audio off by default.** Veo генерирует видео БЕЗ нативного звука (`enable_audio: false`). Звук добавляется только глобально на этапе монтажа или вручную пользователем.
9. **ReviewGate grammar.** Каждый gate показывает 4 варианта: `a) approve`, `b) auto-fix`, `c) edit fix`, `d) stop`. Старые approval aliases не являются state-machine контрактом; свободный текст с правками трактуется как `edit fix`.

## Stage Map

Default формат: **1 hero-in-location anchor + 5 shots** (помещается в один `production-master` чанк gemini-embedding-2: 6 картинок ≤ 8192 tokens — см. [[kinodel-chunk]]).

```
[0] user input — первичный вайб
  │
  ▼
[1] brief intake — ProducerAgent задаёт уточняющие вопросы
  │
  ▼
[2] preproduction-pack — ProducerAgent пакует ответы в PreproductionPack JSON,
     инициализирует projects/<id>/v1/ и production-master chunk v1
  │
  ▼
[3] scenario draft — agent-storytell-kinodel пишет Scenario.json
     (5 шотов / актов по умолчанию)
  │
  ▼
[4] critic-pass — agent-critic-kinodel возвращает CriticNotes (только diff)
  │
  ▼
[5] scenario revise — storyteller применяет diff (если notes != [])
  │
  ▼
🛑 user-review #1 — одобрение сценария (revise → откат к [3])
  │
  ▼
[6] wardrobe — agent-wardrobe-kinodel пишет hero_in_location_prompt
     + style_anchor
  │
  ▼
[7] anchor render — agent-render-kinodel durable batch выполняет:
      • 1× hero-in-location reference image (Nano Banana 2 t2i)
  │
  ▼
🛑 user-review #2 — одобрение референсов (revise → [6]/[7])
  │
  ▼
[8] storyboard — agent-storyboard-kinodel пишет Storyboard.json:
     5 shots × {edit payload image_urls=[hero_in_location_url], motion_help}
  │
  ▼
[9] shots render — agent-render-kinodel durable batch i2i (`fal-ai/nano-banana-2/edit`)
  │
  ▼
🛑 user-review #3 — одобрение кадров (per-shot revise → [8]/[9])
  │
  ▼
[10] video plan — agent-filmmaker-kinodel пишет video_payloads:
      {reference_image, motion_prompt, enable_audio: false (default)}
  │
  ▼
[11] videos render — agent-render-kinodel durable batch i2v (Veo)
  │
  ▼
🛑 user-review #4 — одобрение шот-видео (per-shot revise → [10]/[11])
  │
  ▼
[12] edit — agent-montage-kinodel: ffmpeg concat + transitions
      + опциональный global soundtrack (если PreproductionPack.audio.global_soundtrack=true)
  │
  ▼
[13] final.mp4 — 🛑 user-review #5 (release)
```

Номера user-review гейтов: **5 штук**, каждый обязателен в Phase 1. Fast/auto режим может задать `timeout_sec=60` и `default_decision=approve`, но это явный режим проекта, не скрытый alias.

## Master Todolist (template)

ProducerAgent ведёт состояние по этому списку. `[ ]` = pending, `[~]` = in-progress, `[x]` = done, `[!]` = blocked / awaiting user.

### Preproduction (ProducerAgent)
- [ ] **0. user-input** — поймать первичный вайб юзера
- [ ] **1. brief-intake** — обязательные вопросы:
  - сюжет (логлайн, сеттинг, тон)
  - главный персонаж (внешность, характер)
  - конфликт (что хочет, что мешает)
  - стиль (cinematic / UGC / anime / noir / …)
  - формат (9:16 / 16:9 / 1:1)
  - продолжительность (сек)
  - количество кадров (default 5 — см. [[storyboard-pattern]])
  - аудио (default `enable_audio: false`; глобальный саундтрек / войсовер — opt-in)
  - платформа-цель (TikTok, Reels, YouTube, …) → сразу упаковать в `platform_preset`
- [ ] **2. preproduction-pack** — упаковать в `PreproductionPack` как `L0_BRIEF`. Пробелы заполняются с пометкой `inferred: true`. Создать `production-master` chunk v1 и `approved_layers: [L0_BRIEF]`.

### Production
- [ ] **3. scenario-draft** → [[agent-storytell-kinodel]] → `story.json`
- [ ] **4. critic-pass** → [[agent-critic-kinodel]] → `CriticNotes.json` (diff)
- [ ] **5. scenario-revise** → storyteller применяет diff (loop пока `notes != []` или cap=2)
- [ ] **6. 🛑 user-review #1** — одобрение сценария
- [ ] **7. wardrobe** → [[agent-wardrobe-kinodel]] → `Wardrobe.json` (hero_in_location_prompt, style_anchor)
- [ ] **8. anchor-render** → [[agent-render-kinodel]] autonomous worker: 1× hero-in-location image (`fal-ai/nano-banana-2`)
- [ ] **9. 🛑 user-review #2** — одобрение референсов (revise → 7/8)
- [ ] **10. storyboard** → [[agent-storyboard-kinodel]] → `Storyboard.json` (5 shots × image_payload + motion_help)
- [ ] **11. shots-render** → [[agent-render-kinodel]] autonomous worker: batch i2i edit (`fal-ai/nano-banana-2/edit`, `image_urls=[hero_in_location_url]`)
- [ ] **12. 🛑 user-review #3** — одобрение кадров (per-shot revise → 10/11)
- [ ] **13. video-plan** → [[agent-filmmaker-kinodel]] → `video_payloads.json` (reference_image + motion_prompt; `enable_audio` наследуется из PreproductionPack)
- [ ] **14. videos-render** → [[agent-render-kinodel]] autonomous worker: batch i2v (Veo)
- [ ] **15. 🛑 user-review #4** — одобрение видеошотов (per-shot revise → 13/14)
- [ ] **16. edit** → [[agent-montage-kinodel]] → `final.mp4` (ffmpeg concat + transitions + опциональный global soundtrack)
- [ ] **17. 🛑 user-review #5** — финальная приёмка
- [ ] **18. release** — экспорт в платформенный пресет ([[ffmpeg-video-pipeline]])

## Артефакты (data contracts)

Минимальный набор JSON-форм, которые ходят между агентами. **Это не runtime-схемы**, а **примеры** — реальный контракт каждый агент держит у себя в `SKILL.md`. Хранятся как файлы в `projects/<project_id>/v<N>/<artifact>.json`.

### `PreproductionPack`
```json
{
 "logline": "string",
 "setting": "string",
 "tone": "string",
 "hero": { "name": "string", "look": "string", "vibe": "string" },
 "conflict": "string",
 "style": "cinematic | ugc | anime | noir | ...",
 "format": "9:16 | 16:9 | 1:1",
 "duration_sec": 0,
 "shot_count": 0,
 "audio": {
   "veo_native_audio": false,
   "global_soundtrack": false,
   "voiceover": false,
   "language": "ru|en|..."
 },
 "platform": "tiktok | reels | yt-shorts | youtube",
 "platform_preset": "→ see PLATFORM_PRESETS catalogue below",
 "montage_defaults": {
   "transition": "cut",
   "lufs": -14
 },
 "inferred_fields": ["..."]
}
```

`PreproductionPack` = `L0_BRIEF` в [[kinodel-context-layers]]. Это source of truth для platform/audio/export. Montage не должен делать runtime-lookup в таблицы пресетов; таблицы в [[ffmpeg-video-pipeline]] — справочник для skill/defaults, а не горячий путь.

### `PLATFORM_PRESETS` — каталог пресетов

Статический справочник. `platform_preset` в `PreproductionPack` ссылается на один из этих объектов по `preset_id`. Wardrobe/Director выбирают пресет при инициализации; Montage использует готовые значения напрямую.

```json
{
  "PLATFORM_PRESETS": [

    {
      "preset_id": "landscape_16x9_1080p",
      "label": "YouTube / Reels landscape HD",
      "aspect_ratio": "16:9",
      "resolution": "1280x720",
      "fps": 30,
      "codec": "h264",
      "bitrate_kbps": 8000,
      "max_duration_sec": 600,
      "safe_margin": null,
      "platforms": ["youtube", "reels", "vk-clips"]
    },

    {
      "preset_id": "portrait_9x16_1080p",
      "label": "TikTok / Reels / YT-Shorts portrait FHD",
      "aspect_ratio": "9:16",
      "resolution": "720x1280",
      "fps": 30,
      "codec": "h264",
      "bitrate_kbps": 6000,
      "max_duration_sec": 60,
      "safe_margin": "mobile_ui",
      "platforms": ["tiktok", "reels", "yt-shorts"]
    },

    {
      "preset_id": "portrait_3x4",
      "label": "Pinterest / Stories 3:4 portrait",
      "aspect_ratio": "3:4",
      "resolution": "768x1024",
      "fps": 30,
      "codec": "h264",
      "bitrate_kbps": 5000,
      "max_duration_sec": 60,
      "safe_margin": "mobile_ui",
      "platforms": ["pinterest", "reels"]
    },

    {
      "preset_id": "square_1x1",
      "label": "Instagram feed 1:1 square-ish",
      "aspect_ratio": "1:1",
      "resolution": "1080x1080",
      "fps": 30,
      "codec": "h264",
      "bitrate_kbps": 5000,
      "max_duration_sec": 60,
      "safe_margin": null,
      "platforms": ["reels", "vk-clips"]
    }

  ]
}
```

Поля каждого пресета:

| поле | тип | описание |
|---|---|---|
| `preset_id` | string | уникальный ключ, используется в `PreproductionPack.platform_preset` |
| `aspect_ratio` | string | `"16:9"` / `"9:16"` / `"2:3"` / `"5:4"` |
| `resolution` | string | `"WxH"` в пикселях |
| `fps` | int | кадров в секунду |
| `codec` | string | `"h264"` / `"h265"` |
| `bitrate_kbps` | int | целевой битрейт для ffmpeg `-b:v` |
| `max_duration_sec` | int | ограничение платформы |
| `safe_margin` | string\|null | `"mobile_ui"` — оставлять 10 % снизу/сверху под UI платформы |
| `platforms` | string[] | к каким платформам применим |

### `Scenario`
```json
{
 "version": 1,
 "logline": "string",
 "scenes": [
   { "scene_id": 1, "heading": "INT./EXT. LOCATION — TIME", "action": "string", "dialogue": [ { "who": "HERO", "text": "..." } ] }
 ],
 "notes": "string"
}
```

### `CriticNotes` (только правки, не дублирует сценарий)
```json
{
 "scenario_version": 1,
 "notes": [
   { "scene_id": 2, "issue": "плот-дыра X", "fix": "добавить Y" }
 ]
}
```

### `Wardrobe`
```json
{
 "hero_in_location_prompt": "string — герой В локации одним кадром (геометрия, свет, костюм)",
 "style_anchor": "string — стилевой хвост, добавляется ко всем shot prompts",
 "hero_in_location_url": "projects/<id>/v1/reference_images/hero_in_location.png"
}
```

> Один композитный anchor (hero-in-location) заменяет отдельные `hero_anchor`, `location_exterior`, `location_interior` и является единственным default input для Storyboard edit-запросов. Подробнее — [[storyboard-pattern]] и [[kinodel-rag-concept]].

### `Storyboard`
```json
{
 "shots": [
   {
     "shot_id": 1,
     "image_generation_payload": {
       "image_urls": ["hero_in_location_url"],
       "action_prompt": "string — что происходит в кадре",
       "style": "<style_anchor>"
     },
     "motion_help": "maion action of this frame (подсказка для filmmaker)"
   }
 ],
 "aspect_ratio": "9:16",
 "transition": "crossfade",
 "shot_count": 5
}
```

### `video_payloads` (от Filmmaker)
```json
{
 "video_generation_payloads": [
   {
     "shot_id": 1,
     "reference_image_url": "shot_1_img_url",
     "motion_prompt": "string",
     "enable_audio": false,
     "audio_cue": null
   }
 ]
}
```

> `enable_audio` по умолчанию `false`. Если `PreproductionPack.audio.veo_native_audio === true` (явный opt-in пользователя) — Filmmaker выставляет `enable_audio: true` и заполняет `audio_cue` для нативной звуковой дорожки Veo. В противном случае весь звук добавляется на этапе [[agent-montage-kinodel]] как глобальный саундтрек.

### `RenderJob` (от любого агента → Render Queue)
```json
{
 "job_id": "uuid",
 "project_id": "uuid",
 "kind": "t2i | i2i | i2v",
 "provider": "fal:nano_banana_2 | fal:nano_banana_2_edit | fal:veo31_lite_i2v | openrouter:<template> | local-comfyui | comfy:<workflow>",
 "workflow": "optional workflow template id",
 "payload": { "prompt": "...", "image_urls": ["..."], "params": {} },
 "output_path": "projects/<id>/v1/<dir>/<filename>",
 "requested_by": "agent-storyboard-kinodel",
 "requested_at": "2026-05-07T10:00:00Z",
 "status": "pending | in_progress | IN_QUEUE | IN_PROGRESS | done | failed",
 "output_url": null,
 "retries": 0,
 "request_id": null,
 "status_url": null,
 "response_url": null
}
```

Хранится в `projects/<id>/render_queue.jsonl` (append-only). [[agent-render-kinodel]] — единственный потребитель. `status_url` и `response_url` сохраняются сразу после submit; если процесс оборвался, следующий запуск продолжает polling по ним и не создаёт новый paid request.

### Project layout (вместо отдельного `ProductionState` класса)

Вся «стейт-машина» живёт **на диске**, в одной папке. Никакого in-memory store, никакой БД сверху Hermes — Hermes сам ведёт sessions и checkpoints.

```
projects/<project_id>/
├── state.json              # текущая стадия + todolist + ссылки на v<N> + active_chunk_id
├── reviews.jsonl           # append-only лог решений на user-review гейтах
├── render_queue.jsonl      # append-only очередь RenderJob (см. agent-render-kinodel)
├── render_events.jsonl     # terminal wake-up события render worker → ProducerAgent
├── index.sqlite            # sqlite-vec индекс чанков (gemini-embedding-2)
├── v1/
│   ├── preproduction.json
│   ├── scenario.json
│   ├── critic_notes.json
│   ├── wardrobe.json
│   ├── reference_images/   # hero_in_location.png; optional faceid/* only for explicit multi-character identity work
│   ├── storyboard.json
│   ├── shot_images/        # 01.png .. 05.png
│   ├── video_payloads.json
│   ├── shot_videos/        # 01.mp4 .. 05.mp4
│   └── final.mp4
└── v2/                     # после большого revise — следующая версия
```

`state.json` — простейший:

```json
{
 "project_id": "uuid",
 "stage": "scenario-draft | ... | release",
 "current_version": 1,
 "todolist": [ { "id": "3", "title": "scenario-draft", "status": "done" } ]
}
```

ProducerAgent читает/пишет эти файлы напрямую через filesystem-тулы Hermes. Версия = имя папки `v<N>`.

## User-Review Protocol

На каждом review-вороте ProducerAgent:

1. Показывает артефакт юзеру (текст / картинки / видео).
2. Просит решение по таблице: `a) approve`, `b) auto-fix`, `c) edit fix`, `d) stop`.
3. На `auto-fix` — запускает профильный fixer/Critic loop без уточнений и возвращает preview.
4. На `edit fix` — собирает правки, передаёт ответственному сабагенту, повторяет шаг.
5. На `approve` — фиксирует артефакт (immutable), двигает todolist дальше, аппендит запись в `reviews.jsonl`.
6. На `stop` — ставит `state.stage=paused:<gate_id>`.

Реализуется через `approvals.mode: manual` Hermes'а и обычный chat. Никакого собственного UI / SSE / WebSocket.

### ReviewGate table

| Key | Decision | Meaning |
|---|---|---|
| `a` | `approve` | принять и перейти дальше |
| `b` | `auto-fix` | исправить автоматически через Critic/fixer loop |
| `c` | `edit fix` | применить конкретные правки пользователя |
| `d` | `stop` | остановить pipeline |

Если фраза двусмысленная, ProducerAgent задаёт один уточняющий вопрос и не двигает `todolist`.

## Roles → Agents

| Этап | Агент | Артефакт на выходе |
|------|-------|--------------------|
| 0–2 | ProducerAgent (intake) | `PreproductionPack` + `production-master` chunk v1 |
| 3 | [[agent-storytell-kinodel]] | `story.json` |
| 4 | [[agent-critic-kinodel]] | `CriticNotes.json` (diff) |
| 5 | [[agent-storytell-kinodel]] | `story.json` v+1 (revise) |
| 7 | [[agent-wardrobe-kinodel]] | `Wardrobe.json` (промпты, без рендера) |
| 8, 11, 14 | [[agent-render-kinodel]] | рендеры: hero-in-location.png + shot_images/*.png + shot_videos/*.mp4; faceid/* только opt-in |
| 10 | [[agent-storyboard-kinodel]] | `Storyboard.json` |
| 13 | [[agent-filmmaker-kinodel]] | `video_payloads.json` |
| 16 | [[agent-montage-kinodel]] | `final.mp4` |
| оркестрация | [[agent-producer-kinodel]] | `state.json` + папка `projects/<id>/` + production-master chunk |

## Почему render-as-queue?

Без очереди: storyboarder/filmmaker вызывают fal/Veo синхронно и блокируются на 30–120 сек пер рендер. Их implicit-cache (TTL 3–5 мин) протухает прямо в паузах; при batch на 5+ шотов это равнозначно работе вообще без кэша.

Без autonomous worker: долгий LLM `delegate_task` может быть отменён, если parent turn прерван новым сообщением пользователя. Поэтому render — не рассуждающий child-chat, а возобновляемый batch process:

1. Планирующий агент пишет `RenderJob` и выходит.
2. ProducerAgent ставит `state.stage = rendering:<batch>` и запускает `agent-render-kinodel/scripts/render.py` как autonomous worker.
3. Worker сохраняет `request_id`, `status_url`, `response_url` сразу после submit; повторный запуск продолжает polling, не создавая новый paid request.
4. Worker экономно polling'ит provider status: стартовый интервал 5s, adaptive backoff до 30s, terminal statuses `COMPLETED | FAILED | CANCELLED`.
5. Когда batch terminal, worker пишет `render_events.jsonl` event `render_batch_terminal`, обновляет `state.render_last_summary` и переводит stage в `render_done:<batch>` / `render_partial_failed:<batch>` / `render_failed:<batch>`.
6. ProducerAgent просыпается от terminal summary, принимает output paths и открывает следующий user-review.

Экономия на cached input tokens сохраняется, а рендер не обрывается от чат-сообщений.

## Связанные концепции

- [[agent-producer-kinodel]] — оркестратор/продюсер
- [[agent-render-kinodel]] — рендер-очередь (t2i / i2i / i2v)
- [[kinodel-rag-concept]] — месседж-аррей, production-master, implicit caching
- [[kinodel-chunk]] — стратегия чанкования, dim, batch API
- [[storyboard-pattern]] — UGC 3-shot / Cinematic 5-shot
- [[prompt-engineering]] — image / video prompts, style anchor, Nano Banana 2, Veo
- [[ffmpeg-video-pipeline]] — финальный монтаж
- [[quality-check-pattern]] — авто-QC и VLM-проверки
