---
title: Project — Kinodel (AI Filmmaking Pipeline)
created: 2026-06-24
updated: 2026-06-24
type: entity
tags: [project, kinodel, cinema, agent-architecture, pipeline, video-gen, image-gen, mcp, rag, product]
sources: [wiki/entities/project-kinodel.md, ~/.hermes/skills/kinodel/pipeline-kinodel/SKILL.md, ~/.hermes/skills/kinodel/producer-kinodel/SKILL.md, ~/.hermes/skills/kinodel/craft-kinodel/SKILL.md, ~/.hermes/skills/kinodel/render-kinodel/SKILL.md]
confidence: high
---

# Kinodel — Multi-Agent AI Filmmaking Pipeline

> **Runtime-vibe-factory**: creator открывает идею → выбирает vibe → AI crew делает story, visuals, video, music, episodes, worlds и reusable creative memory. Artifact-centric, not chat-centric.

---

## TL;DR

Kinodel — это staged production graph с явной ответственностью. Каждый агент владеет ровно одним артефактом, render worker изолирован от планирования, а пользователь контролирует результат через hard gates (human-in-the-loop). Durable production state живёт в файлах, не в чате.

**Статус:** Production-capable pipeline — от brief до final MP4 с montage, chunk memory и RAG indexing
**Архитектура:** 13-goal state machine (p0–p13), 10 specialist skills, provider-neutral render layer

---

## Контекст и мотивация

**Проблема:** Существующие подходы к AI-видеогенерации — это либо single-shot prompt → video (Runway, Pika), либо хаотичные prompt chains в одном чате. Ни один подход не даёт:
- Воспроизводимости (тот же prompt ≠ тот же результат)
- Контроля качества на промежуточных стадиях
- Безопасного resume после сбоя/перезапуска
- Переиспользования creative assets между проектами

**Боль, которую закрывает:**
1. Context bloat в монолитных prompt chains — один чат становится production database
2. Autonomous drift — агент "улетает" от изначального brief без возможности контроля
3. Provider lock-in — артефакты планирования загрязнены payload конкретного провайдера
4. Нет durable memory — каждый проект начинается с нуля, нет переиспользования стилей/персонажей

---

## Архитектура

### Artifact-Centric Pipeline (13 Goals)

```
p0  BriefGate → brief.json
p1  Story → story.json
p2  Main Frame Plan → wardrobe_request.json
p3  Main Frame Render → render_results/main_frame_result.json
p4  🛑 ReviewGate (story + main frame approval)
p5  Storyboard Plan → storyboard_requests.json
p6  Story Images Render → render_results/story_frames_result.json
p7  🛑 ReviewGate (story images approval)
p8  Video Plan → video_requests.json
p9  Video Render → render_results/shot_videos_result.json
p10 Montage → outputs/final.mp4
p11 Final Chunk → final_chunk.json
p12 🛑 Final ReviewGate
p13 Cinema Chunk → chunks/cinema_chunk.json + RAG index
```

**Ключевой принцип:** Durable production state живёт в файлах, не в чате. `render_results/*.json.selected_outputs` — chaining truth; `outputs/` — архив/кэш, не state.

```
~/projects/<project_id>/v1/
  brief.json
  story.json
  wardrobe_request.json
  storyboard_requests.json
  video_requests.json
  render_results/
    main_frame_result.json
    story_frames_result.json
    shot_videos_result.json
  qc/
  outputs/
  workflow/                    # Provider payloads for audit
  final_chunk.json
  chunks/cinema_chunk.json
```

### Producer as Lean State Machine

Producer — не content warehouse, а lean state machine (~2k tokens context). Маршрутизируется через `producer_step.py`:

```
producer_step.py --project-dir <project>/v1
→ action JSON (delegate_stage | render_stage | show_gate | complete)
→ if delegate_stage: delegate_task(owner_skill) + validate_after
→ if render_stage: background render.py → render_wakeup.py → next action
→ if show_gate: present preview refs + A/B/C/D, stop
→ if complete: report done
```

После BriefGate approval Producer сразу запускает детерминистичный цикл до следующего hard gate, рендера или ошибки. Не останавливается на "if you want, I can continue."

**`state_guard.py`** — валидация артефактов, safe resume, gate decisions, handoff construction:
- `validate` — проверка schema, project_id, status=complete, non-empty jobs, URL форматов
- `next-goal` — определение следующей стадии
- `handoff` — построение compact delegate envelope
- `approve-gate` — персистенция gate decision для cross-chat resume
- `list-projects` — список незавершённых проектов

Creative work делегируется через compact handoff envelopes:

```json
{
  "schema": "kinodel.delegate_handoff.v1",
  "project": {"id": "id", "dir": "/home/user/projects/id/v1"},
  "artifacts": {
    "read": ["brief.json", "story.json"],
    "write": "wardrobe_request.json"
  },
  "stage": {"goal": "p2_main_frame_plan", "owner_skill": "wardrobe-kinodel"},
  "context_cache": [...],
  "selected_media": [...],
  "edit_notes": null
}
```

**Результат:** clean context, prompt-cache locality, один чат не становится production DB.

### 10 Specialist Skills

| Скил | Роль | Артефакт |
|------|------|----------|
| **producer-kinodel** | Оркестратор, state machine, gate enforcement | `producer_state.json` |
| **pipeline-kinodel** | Закон/маршрут, artifact contracts, skill ownership | law only |
| **kinodel-project-layout** | Filesystem scaffold, brief.json shape | project tree |
| **storytell-kinodel** | Сценарист | `story.json` |
| **wardrobe-kinodel** | Visual anchor / main_frame planner | `wardrobe_request.json` |
| **storyboard-kinodel** | Раскадровщик | `storyboard_requests.json` |
| **filmmaker-kinodel** | Video request planner | `video_requests.json` |
| **render-kinodel** | Provider-neutral executor | `render_results/*.json` |
| **montage-kinodel** | Final video assembly | `outputs/final.mp4` |
| **critic-kinodel** | Optional QC / edit-fix notes | `qc/*.json` |
| **craft-kinodel** | Chunk packaging + RAG indexing | `chunks/cinema_chunk.json` |

### Hard ReviewGates

```
BriefGate (p0) — подтверждение формата производства перед инициализацией
ReviewGate p4 — story + main frame approval
ReviewGate p7 — story images approval
Final Gate p12 — final video + final_chunk approval
```

На gate пользователь выбирает:
```
A — approve
B — auto-fix via critic
C — edit-fix with notes
D — stop
```

Render completion ≠ approval. Runtime safe to resume across chats, terminals и long render jobs. Gate decisions персистируются в `producer_state.json.gate_decisions[]`.

### Provider-Neutral Render Layer

Planner-агенты пишут request envelopes (provider-neutral):

```json
{
  "schema": "kinodel.render_requests.v1",
  "project_id": "id",
  "status": "complete",
  "stage": "story_frames",
  "jobs": [{
    "kind": "i2i",
    "render_prompt": "...",
    "input_media": ["https://..."],
    "output_name": "shot_01.png"
  }]
}
```

**Forbidden в planner artifacts:** provider payloads, queue URLs, retry state, raw responses, logs, costs.

Render worker (`render-kinodel`) owns: provider mapping, retries, events, result manifests, output promotion.

**Render-boundary architecture:**
```
render.py → render_worker.py → providers/{fal,comfyui}_provider.py
→ temp results in /tmp/kinodel/<project_id>/<run_id>/
→ render_wakeup.py: promote → validate → next-action → notify Producer
```

**Supported providers:**
- **Local ComfyUI** — `img2img_klein` (images), `img2vid_wan_lora` (video), multi-ref img2img, LoRA slots
- **fal.ai** — Veo 3.1 (i2v + flf2v), HiDream O1 (t2i + edit), Nano Banana 2 (fallback)
- **Background render execution** с `notify_on_complete=true`, result files и universal wake-up bridge

---

## Инженерные решения

### 1. Artifact-First State Machine
Вместо chat-centric подхода — всё состояние в файлах. Каждый артефакт несёт `project_id`. `status=pending` ≠ production-ready. `render_results/*.json.selected_outputs` — chaining truth; `outputs/` — архив. Downstream агенты читают `selected_outputs`, не сканируют `outputs/`.

### 2. Compact Handoff Pattern
Делегирование через `delegate_task` с compact envelope: read listed artifacts → write owned artifact → return only status/path/summary. Context Producer остаётся ~2k tokens. Specialist skills не загружаются в Producer context — только delegate + validate.

### 3. Provider-Neutral Contracts
Планировщики не знают про provider payloads. Provider mapping, retries, events — внутри render worker. Добавление нового провайдера = новый adapter в `providers/`, не переписывание planner skills. Provider adapter architecture: `registry.py` → `fal_provider.py` / `comfyui_provider.py`.

### 4. Gate-Based Control Flow
Text-first hard stops вместо autonomous drift. Пользователь видит визуальные превью на каждом gate (A/B/C/D). Safe to resume после любого прерывания — gate decisions персистированы. BriefGate → p0 approval авторизует детерминистичный p1→p2→p3 без дополнительных вопросов.

### 5. Chunk Memory Layer (CRAFT Architecture)
`final_chunk.json` — sealed creative memory: story, hook, main_frame, story_images, video_clips, final_video, conclusion. Compact, reusable.

**Craft-Kinodel** превращает raw refs в durable `*_chunk.json` артефакты для RAG indexing. Five-subject CRAFT contract:

| Subject | Meaning |
|---------|---------|
| `context` | What this chunk represents, canon/inspiration boundary |
| `references` | Media/doc refs with @handles, roles, take/ignore rules, priorities |
| `action` | What downstream agents should do with this chunk |
| `focus` | Non-drift priority: identity lock, continuity, style DNA |
| `timing` | Source-derived sequence/phase info (no invented seconds) |

**Chunk types:** `cinema_chunk`, `avatar_chunk`, `music_chunk`, `season_chunk`, `episode_chunk`.

**Embedding profiles:** `fast_recall` (256d) → `default_rag` (768d) → `deep_retrieval` (1536d) → `full_fidelity` (3072d). Не индексировать всё на 3072d.

**RAG policy:** Direct chunk paths when Producer knows what's needed; semantic/vector search deferred until explicitly required.

### 6. Token Aerodynamics
Hot-path Producer load: ~5k skill tokens (pipeline + producer only). Specialist skills: 366–1245 tokens each, загружаются только в delegated subagent. ComfyUI skill (23k chars) изолирован от production hot path. `context_cache` — compact digest layer для high-reuse artifacts.

### 7. Pipeline Specs (Phase A–C → LangGraph)
От одного hardcoded cinematic route — к family of validated production graphs:

| Phase | Что | Статус |
|-------|-----|--------|
| **Phase A** | `pipeline_spec.json` schema, `cinematic.v1` spec, static validator | ✅ done |
| **Phase B** | `state_guard.py` spec-aware route compiler, CompiledRoute, explicit gate-decision rule | ✅ done |
| **Phase C** | Initializer profiles, capability binding, contracts/templates | ✅ done |
| **Phase RAG** | Chunk schemas, embeddings, indexer, resolver, cinema_chunk crafting | ✅ foundation |
| **Future** | LangGraph graph-native runtime | 📋 planned |

Planned pipelines: `serial_season.v1`, `serial_episode.v1`, `music_video.v1`, `renovation_timelapse.v1`.

### 8. Render Wake-Up Bridge
Universal `render_wakeup.py` — единая точка возврата из background render:
```
render.py → temp result
render_wakeup.py → copy_worker_result.py (promote selected outputs)
                → state_guard.py validate
                → producer_step.py (next action)
                → producer_notify.py (format message)
                → producer_agent_prompt (wake payload)
```
Не per-stage wake-up скрипты; один universal bridge для p3/p6/p9.

### 9. flf2v (First-Last Frame to Video)
`fal:veo31_lite_flf2v` — для cinematic transitions между соседними story frames. 8s стандартная длительность. Filmmaker-kinodel учитывает first/last frame pairs при написании `video_requests.json`.

### 10. IP-Safety QC
Если preview из "style of <famous franchise>" brief визуально слишком близок к оригиналу (exact costume, logo, signature mask, direct likeness), Producer флагит это на p4/p7 и рекомендует `C` edit-fix.

---

## Результаты

- **Production-capable pipeline** — от brief до final MP4 с montage + RAG chunk
- **13-goal state machine** с lean Producer (~2k tokens context)
- **10 specialist skills** с clean ownership boundaries
- **Provider-neutral render** — ComfyUI + fal.ai, modular adapter architecture
- **Safe resume** — любой проект можно продолжить после прерывания, gate decisions персистированы
- **Chunk memory** — `cinema_chunk.json` с @handles, CRAFT contract, embedding profiles
- **Pipeline specs** — Phase A/B/C runtime: spec validation, CompiledRoute, capability binding
- **Universal render bridge** — один `render_wakeup.py` для всех render stages
- **Успешный проект 'kungfu-cat-vhs'** — flf2v 8s transitions, VHS/retro-futurism aesthetic

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Runtime** | Hermes Agent, Python |
| **Architecture** | Artifact-centric, subagent delegation, pipeline specs |
| **Image Gen** | ComfyUI (`img2img_klein`), fal.ai (HiDream O1, Nano Banana 2) |
| **Video Gen** | ComfyUI (`img2vid_wan_lora`), fal.ai (Veo 3.1 i2v + flf2v) |
| **RAG** | gemini-embedding-2, sqlite-vec, chunk schemas, embedding profiles |
| **Video** | FFmpeg, PyAV fallback |
| **State** | on-disk artifacts, `state_guard.py`, `producer_state.json` |
| **Future** | LangGraph graph-native runtime, serial/music pipelines |

---

## Что отличается от аналогов

| | Runway/Pika | Kinodel |
|---|---|---|
| Подход | Single-shot prompt → video | Staged production graph (13 goals) |
| Контроль | Пост-фактум | Hard gates на каждой стадии (p0/p4/p7/p12) |
| Resume | Нет | Safe to resume across chats + gate decisions persisted |
| Memory | Нет | Chunk-based creative memory (CRAFT, embedding profiles) |
| Multi-agent | Нет | 10 specialist skills, lean Producer state machine |
| Provider lock-in | Да | Provider-neutral, modular adapter architecture |
| State | Chat context | Artifact-first, on-disk files |
| RAG | Нет | Chunk crafting + indexing + resolver |

---

## Roadmap

- [x] cinematic.v1 — working pipeline (13 goals)
- [x] ComfyUI + fal.ai render adapters (modular providers)
- [x] Hard gates (p0, p4, p7, p12)
- [x] Chunk memory (final_chunk.json + cinema_chunk.json)
- [x] Pipeline specs Phase A/B/C (validator, CompiledRoute, capability binding)
- [x] RAG foundation (chunk schemas, embeddings, indexer, resolver)
- [x] Universal render wake-up bridge
- [ ] LangGraph runtime migration
- [ ] Serial: season + episode pipelines
- [ ] Muse (music-driven pipeline)
- [ ] Semantic/vector nearest-neighbor retrieval activation
- [ ] Webapp UI для creators
