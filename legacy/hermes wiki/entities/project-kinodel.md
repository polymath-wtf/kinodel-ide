---
title: Kinodel — Агентное Кинопроизводство
created: 2026-05-04
updated: 2026-05-12
type: entity
tags: [project, kinodel, cinema, video-gen, agent-architecture, pipeline, mvp]
sources:
  - wiki/concepts/cinema-pipeline.md
  - wiki/concepts/pipeline-kinodel.md
  - ~/.hermes/skills/kinodel/pipeline-kinodel/SKILL.md
  - ~/.hermes/skills/kinodel/kinodel-project-layout/SKILL.md
  - wiki/concepts/storyboard-pattern.md
  - wiki/concepts/ffmpeg-video-pipeline.md
  - wiki/concepts/prompt-engineering.md
  - wiki/concepts/vlm-analysis.md
  - wiki/concepts/timeline-editor.md
  - wiki/concepts/quality-check-pattern.md
  - wiki/entities/agent-producer-kinodel.md
  - wiki/entities/agent-storytell-kinodel.md
  - wiki/entities/agent-critic-kinodel.md
  - wiki/entities/agent-wardrobe-kinodel.md
  - wiki/entities/agent-storyboard-kinodel.md
  - wiki/entities/agent-filmmaker-kinodel.md
  - wiki/entities/agent-montage-kinodel.md
confidence: high
contested: false
contradictions: []
---

# Kinodel — Агентное Кинопроизводство

**Kinodel** (от "кино" + "node" / "model") — это автоматизированный пайплайн агентного кинопроизводства: от первичного вайба пользователя до собранного мини-фильма. Оркестратором выступает [[agent-producer-kinodel]], который делегирует задачи специализированным кинокрю (cinema crew) через встроенные механизмы Hermes Agent.

> **Принцип:** Artifact-centric pipeline. Каждый запуск — последовательная state machine: Producer держит только stage + artifact paths, специалисты читают/пишут файлы, а provider/runtime мусор остаётся scratch.

---

## Core Pipeline

От [[cinema-pipeline]] — упрощённая стадийная карта:

```
[0 user input]
   │
   ▼
[1 brief intake] — уточняющие вопросы
   │
   ▼
[2 preproduction-pack] — vibe + параметры
   │
   ▼ (ProducerAgent принимает пакет)
[3 story.json] → [4 wardrobe_request.json] → [5 main_frame render] — 🛑 #1
   │
   ▼
[6 storyboard_requests.json]
   │
   ▼
[7 story images render] — 🛑 #2
   │
   ▼
[8 video_requests.json]
   │
   ▼
[9 video clips render]
   │
   ▼
[10 montage]
   │
   ▼
[11 outputs/final.mp4]
   │
   ▼
[12 final_chunk.json]
```

**User-review protocol:** mandatory gates occur after story+main_frame and after story images. Each `ReviewGate` has 4 variants: `a) approve`, `b) auto-fix`, `c) edit fix`, `d) stop`. Optional [[agent-critic-kinodel]] notes may be written under `qc/`.

---

## Cinema Crew — Роли

| Роль | Агент | Артефакт |
|------|-------|----------|
| Режиссёр / Продюсер | [[agent-producer-kinodel]] | live `{stage, artifacts}` + `final_chunk.json` |
| Сценарист | [[agent-storytell-kinodel]] | `story.json` |
| Кинокритик | [[agent-critic-kinodel]] | optional `qc/*_critic.json` |
| Гардероб / Локации | [[agent-wardrobe-kinodel]] | `wardrobe_request.json` |
| Раскадровщик | [[agent-storyboard-kinodel]] | `storyboard_requests.json` |
| Оператор / I2V | [[agent-filmmaker-kinodel]] | `video_requests.json` |
| Монтажёр | [[agent-montage-kinodel]] | `outputs/final.mp4` |

Target skill package names use `kinodel/<role>-kinodel` without the `agent-` prefix; wiki entity names keep legacy `agent-*` wikilinks for continuity.

---

## Key Patterns

- **[[storyboard-pattern]]** — UGC 3-shot (Hook → Core → Result) и Cinematic 5-shot (Establishing → Build-up → Climax → Resolution → Outro).
- **[[prompt-engineering]]** — image/video prompt структуры; style_anchor из первого шота копируется в остальные для consistency.
- **[[ffmpeg-video-pipeline]]** — сборка через `compose` (crossfade / fadeblack / wipe / cut); platform presets (TikTok/Reels/YouTube).
- **[[vlm-analysis]]** — Vision Language Model для визуального QC (по запросу пользователя в Phase 1; авто-QC в Phase 2).
- **[[quality-check-pattern]]** — техпроверка `compose` (duration, resolution, FPS) + визуальная оценка VLM.
- **[[timeline-editor]]** — лёгкий NLE поверх ffmpeg; timeline как shared артефакт между агентом и пользователем.

---

## Tech Stack (MVP)

| Слой | Инструмент | Почему |
|------|-----------|--------|
| Runtime | Hermes Agent | agent loop, skills, delegation, sessions, approval gates — из коробки |
| Image Gen | Nano Banana 2 (Gemini 3 Flash Image) | `fal-ai/nano-banana-2` для одного anchor + `fal-ai/nano-banana-2/edit` для shot frames |
| Video Gen | Veo | first frame reference + motion_prompt, `enable_audio=false` by default |
| Post-process | fluent-ffmpeg | concat, transitions, global soundtrack; фоли уже в видео от Veo |
| Skills | `SKILL.md` per agent under `~/.hermes/skills/` | контракты + поведение |
| State | on-disk artifacts under `projects/<id>/v<N>/` | Producer context holds only stage + paths |
| VLM (Phase 2) | Claude Vision / Gemini Pro Vision | агент видит результат |
| Memory / Archive | gemini-embedding-2 + sqlite-vec | archival RAG для следующих синематиков/серий; indexing на release или explicit archive checkpoint |

---

## Phases

| Phase | Что | Статус |
|-------|-----|--------|
| **Phase 1** | MCP-style pipeline через Hermes. Шесть агентов-skills, ручные review-ворота, ffmpeg монтаж. | MVP / in-progress |
| **Phase 2** | Автономный agent loop, RAG memory (стиль/ошибки/предпочтения), VLM auto-QC, timeline editor, webhook. | backlog |
| **Phase 3** | Production: Mac Mini + NemoClaw = Guzlik. | backlog |

> Phase 1 не переизобретает runtime: **не** пишем свой agent loop, skills loader, DAG executor, event log, approval system, VLM client — всё это Hermes.

---

## Project Layout

```
projects/<project_id>/
└── v1/
    ├── brief.json
    ├── story.json
    ├── wardrobe_request.json
    ├── storyboard_requests.json
    ├── video_requests.json
    ├── render_results/
    │   ├── main_frame_result.json
    │   ├── story_frames_result.json
    │   └── shot_videos_result.json
    ├── qc/
    │   └── *_critic.json
    ├── outputs/                          # Accumulates all render iterations (current + old)
    │   ├── main_frame.png / main_frame_v02.png
    │   ├── shot_01.png / shot_01_v02.png
    │   ├── shot_01.mp4 / shot_01_v02.mp4
    │   └── final.mp4
    └── final_chunk.json
```

Initialization creates `brief.json`, `outputs/`, `render_results/`, `qc/`, and project-bound `pending` stubs for `story.json`, `wardrobe_request.json`, `storyboard_requests.json`, and `video_requests.json`. Gates treat stubs as identity anchors only; stages are ready only after `project_id` matches and `status` becomes `complete`.

`render_results/*.json` are selection manifests: `selected_outputs` points to current approved media refs, `attempts` keeps compact refs for all generated iterations (including rejected ones). Downstream agents must consume `selected_outputs`, not scan `outputs/` directly.

---

## Relationships

- Orchestrator: [[agent-producer-kinodel]]
- Sub-agents: [[agent-storytell-kinodel]], [[agent-critic-kinodel]], [[agent-wardrobe-kinodel]], [[agent-storyboard-kinodel]], [[agent-filmmaker-kinodel]], [[agent-montage-kinodel]]
- Concepts: [[cinema-pipeline]], [[storyboard-pattern]], [[ffmpeg-video-pipeline]], [[prompt-engineering]], [[vlm-analysis]], [[timeline-editor]], [[quality-check-pattern]]
- Legacy context: [[agent-runtime-pattern]], [[task-engine-dag]], [[agent-tracking]] (read-only)

## См. также

- [[project-mille]] — смежный опыт автоматизации (img2img pipeline через n8n + Flux)
- [[rag-memory]] — Phase 2 память агента
- [[goals-roadmap]] — общие цели проекта
