---
title: Kinodel Build v1 — Skill Packaging Architecture
created: 2026-05-09
updated: 2026-05-13
type: concept
tags: [kinodel, agent-architecture, skills, render-queue, prompt-caching, workflow]
sources:
  - wiki/entities/project-kinodel.md
  - wiki/entities/agent-producer-kinodel.md
  - wiki/entities/agent-render-kinodel.md
  - wiki/entities/agent-storytell-kinodel.md
  - wiki/entities/agent-critic-kinodel.md
  - wiki/entities/agent-wardrobe-kinodel.md
  - wiki/entities/agent-storyboard-kinodel.md
  - wiki/entities/agent-filmmaker-kinodel.md
  - wiki/entities/agent-montage-kinodel.md
  - wiki/concepts/cinema-pipeline.md
  - wiki/concepts/kinodel-chunk.md
  - wiki/concepts/kinodel-context-layers.md
  - wiki/concepts/kinodel-sidecar-context.md
  - wiki/concepts/kinodel-render-requests.md
  - wiki/concepts/kinodel-rag-concept.md
  - wiki/queries/kinodel-roadmap.md
confidence: high
contested: false
contradictions: []
---

=== Задача ===
Ты — архитектор AI-систем. Твоя задача: спроектировать и сгенерировать полную архитектуру сабагентов для AI filmmaking pipeline "Kinodel" внутри фреймворка Hermes Agent (Nous Research).

=== Контекст: существующий стек ===
Hermes Agent — это open-source AI-фреймворк с поддержкой tool calling, skills, subagents (delegate_task), cron jobs, persistent memory и мультиплатформенного gateway (Telegram, Discord, etc.). Скилы живут в ~/.hermes/skills/.

Kinodel pipeline уже примерно есть в скиле `kinodel/kinodel`, но этот скил мы переделываем в **архитектурным framework skill**, а не ProducerAgent. Он описывает карту ролей, контракты, naming, shared invariants и ссылки на профильные skills. Работу продюсера выполняет отдельный `kinodel/producer-kinodel`.

Pipeline превращает текстовый brief в короткометражный фильм:
Brief → Scenario → Wardrobe → Storyboard → Filmmaker → Editor → Final

Существующие Kinodel-скилы:
- `kinodel/kinodel` — framework skill: архитектурная карта, общие контракты, правила упаковки, skill registry.
- `kinodel/render-kinodel` — target package name для автономного render worker. В текущем workspace legacy-директория может называться `agent-render-kinodel`, но при упаковке убрать prefix `agent-`.
- `kinodel/comfyui` — provider skill для ComfyUI lifecycle/workflow execution.
- media/fal-video-generation — fal.ai generate.py wrapper
- note-taking/wiki-creation — создание вики с frontmatter + wikilinks + provenance

=== Naming для упаковки skills ===
Паковать skills под namespace `kinodel/` без префикса `agent-`:
- `kinodel/producer-kinodel`
- `kinodel/storytell-kinodel`
- `kinodel/critic-kinodel`
- `kinodel/wardrobe-kinodel`
- `kinodel/storyboard-kinodel`
- `kinodel/filmmaker-kinodel`
- `kinodel/montage-kinodel`
- `kinodel/render-kinodel`

Wiki-страницы пока могут сохранять legacy имена `agent-*-kinodel` ради wikilink continuity, но в `SKILL.md` frontmatter `name:` и документации упаковки использовать имена без `agent-`.


=== Ключевое требование: Динамический User Approve ===
НЕ ИСПОЛЬЗУЙ механический approve (остановка сессии + ожидание ввода).
Вместо этого используй динамический чат-апрув:
- ProducerAgent после каждой стадии (Scenario, Wardrobe, Storyboard, Shots, Final) отправляет артефакт в Telegram/чат как `ReviewGate`.
- Каждый gate показывает **ровно 4 варианта**:
  - `a) approve` — принять артефакт и перейти дальше.
  - `b) auto-fix` — ProducerAgent запускает профильный fixer/Critic loop без уточнений, затем возвращает новый preview.
  - `c) edit fix` — пользователь пишет конкретные правки; ProducerAgent сохраняет их как `review_notes` и делегирует точечный revise.
  - `d) stop` — остановить pipeline и оставить `state.stage=paused:<gate_id>`.
- По умолчанию gate может иметь `timeout_sec=60` и `default_decision="approve"`, если проект запущен в fast/auto режим. Для strict/manual режима default отсутствует и ProducerAgent ждёт пользователя.
- ProducerAgent слушает ответ через обычное сообщение, не блокирует execution loop; текущий gate хранится в `state.json.review_gate`.
- Старые approval aliases (`го`, `збс`, `кайф`, `норм`, etc.) НЕ являются архитектурным контрактом. Свободный текст без `a/b/c/d` трактуется как `c) edit fix`, если содержит правки, либо ProducerAgent задаёт один уточняющий вопрос.


=== Архитектура сабагентов ===
Создай следующих специализированных агентов как Hermes skills в `~/.hermes/skills/kinodel/`:

0. **kinodel/kinodel** (Framework Skill)
   - Не является ProducerAgent и не пишет runtime-артефакты проекта
   - Знает registry всех Kinodel skills, общие контракты `ContextLayer`, `RenderJob`, `ReviewGate`
   - Описывает skill naming, project layout, lifecycle и ссылки на [[cinema-pipeline]], [[kinodel-context-layers]], [[kinodel-render-requests]]
   - Используется как архитектурная инструкция для разворачивания остальных skills

1. **producer-kinodel** (Orchestrator/Producer)
   - Единственный, кто общается с пользователем
   - Управляет state.json, routes задачи specialist agents
   - Делегирует через request-builder из [[kinodel-context-layers]]: `goal = stable cacheable L0-L6 layers`, `context = task-specific layers + role skill + dynamic suffix`
   - Никогда не генерирует контент сам (только делегирует)
   - Обрабатывает `ReviewGate` с вариантами `a/b/c/d`
   - После каждого approve: фиксирует артефакт, обновляет approved_layers[], reviews.jsonl

2. **storytell-kinodel** (Screenwriter)
   - Input: PreproductionPack.json → Output: Scenario.json (строгий JSON, no markdown fences)
   - Делит narrative на atomic shots (Cinematic 5-shot или UGC 3-shot)
   - Каждая сцена: scene_id, heading, action, visual_vibe
   - Diff-mode: при получении CriticNotes модифицирует только указанные scene_id
   - Может иметь `references/`, `hooks/`, `examples/` с micro examples; выбирает 1-3 коротких snippets, не грузит всю библиотеку

3. **critic-kinodel** (QC / Logic Reviewer)
   - Input: Scenario.json → Output: JSON diff issues (не переписывает сценарий)
   - Проверяет: visual realizability (может ли Nano Banana 2 / Veo сгенерировать?), character movement logic, style consistency
   - Если идеально — {"notes": []}

4. **wardrobe-kinodel** (Visual Anchors)
   - Input: Scenario.json → Output: hero_in_location_prompt + style_anchor
   - ОДИН composite anchor (hero в location), не отдельные hero/location
   - Пишет RenderJob `kind=t2i`; provider выбирается через `provider_policy`, default `fal:nano_banana_2`
   - Не вызывает render provider напрямую

5. **storyboard-kinodel** (Frame Composition)
   - Input: Scenario.json + hero_in_location_url → Output: storyboard_frames/
   - Один frame на scene_id
   - Пишет RenderJob `kind=i2i`; default provider `fal:nano_banana_2_edit`, но контракт не привязан к конкретной модели
   - Для каждого shot: provider-neutral `image_generation_payload` + `motion_help`

6. **filmmaker-kinodel** (Video Generation Operator)
   - НЕ генерирует видео синхронно
   - Input: storyboard frames → Output: render_queue.jsonl entries для Render Agent
   - Пишет RenderJob `kind=i2v`; default provider `fal:veo31_lite_i2v`, но может выбрать ComfyUI/OpenRouter-compatible provider policy
   - Группирует shots в batch’и по budget и параллельности

7. **render-kinodel** (Autonomous Worker) — уже существует как legacy `agent-render-kinodel`, но ДОЛЖЕН быть улучшен:
   - Читает render_queue.jsonl, выбирает adapter по `provider`
   - Собирает provider workflow JSON из `workflows/` templates для fal.ai / OpenRouter / ComfyUI
   - Для ComfyUI использует skill `kinodel/comfyui` и его workflow templates, либо локальные schema-mapped copies
   - Запускает concurrency limits per provider/job class, а не по названию модели
   - НЕ блокирует чат ProducerAgent — работает в background/autonomous mode
   - Пишет render_events.jsonl + обновляет state.render_last_summary
   - Resume (не resubmit): после submit request_id/status_url/response_url живут в queue
   - Экономичный polling: start 5s, adaptive backoff до 30s
   - HTTP 202 = IN_PROGRESS (не ошибка), терминал: COMPLETED/FAILED/CANCELLED
   - Бюджет-контроль: читает PreproductionPack.json → budget_usd, fail-fast при превышении

8. **montage-kinodel** (Post-Production / Montage)
   - Input: approved shot videos → Output: final mp4
   - Только assembly + transitions + global soundtrack
   - ffmpeg-based, один preset = один формат
   - Не перегенерирует отдельные shots

=== Оптимизационные требования ===
1. **Prompt Caching (Layer Alignment)**: specialist subagents НЕ получают один искусственно идентичный `goal`. ProducerAgent собирает `goal` из стабильных approved слоёв L0-L6, нужных конкретной задаче. Кэш выигрывает не от одинаковой фразы, а от byte-identical prefix слоёв: `L0_BRIEF`, затем `L1_SCENARIO`, затем `L2_WARDROBE_REFS`, etc. Ролевая инструкция живёт в `context` после stable prefix. См. [[kinodel-context-layers]].

1a. **Sidecar Context Packs**: `references/`, `hooks/`, `styles/`, `examples/`, and `templates/` are allowed inside specialist skill packages, but they are not L0-L6 layers and never go into cacheable `goal`. They are selected as 1-3 compact snippets in `context`. См. [[kinodel-sidecar-context]].

2. **Job-first Render Dispatch**:
   - Планирующие agents пишут provider-neutral `RenderJob` в `render_queue.jsonl`
   - Render Agent выбирает adapter и workflow template по `provider` + `kind`
   - Concurrency limits задаются per provider/job class (`image_hosted`, `video_hosted`, `local_comfyui`, `llm_asset`) и не хардкодятся как “Nano=8 / Veo=2” в архитектуре
   - Render Agent управляет семафорами, не ProducerAgent

3. **State Machine (state.json)**:
```json
   {
     "project_id": "...",
     "version": 1,
     "stage": "scenario_review|wardrobe_review|storyboard_review|rendering|editing|final_review|paused:<gate_id>",
     "approved_layers": ["L0_BRIEF", "L1_SCENARIO", "L2_WARDROBE_REFS"],
     "review_gate": {
       "gate_id": "storyboard_review",
       "artifact_path": "projects/<id>/v1/storyboard.json",
       "options": ["approve", "auto-fix", "edit-fix", "stop"],
       "timeout_sec": 60,
       "default_decision": "approve"
     },
     "render_queue_id": "batch-001",
     "render_last_summary": null,
     "total_cost_usd": 0.0
   }
```

4. **Append-Only State**: 
   - revisions создают новые chunks, старые помечаются is_active: false
   - render_queue.jsonl — append-only, job_id уникальный, идемпотентность
   - embedding/index update НЕ запускается на каждый checkpoint

5. **Embedding / RAG Policy**:
   - В горячем production path агенты работают по L0-L6 textual/image URL context layers и prompt cache
   - Не обновлять embedding после каждого approve/checkpoint
   - Индексировать в конце как готовый продукт: `production-master`, continuation chunks, `video-visual`, optional `audio-embed`
   - Для сериалов/следующих синематиков использовать embeddings предыдущих completed проектов как archival RAG; dimension выбирается per use case: 256 first-pass, 768 default retrieval, 1536/3072 visual rerank

6. **Error Recovery & Resume**:
   - Любой worker может быть прерван (parent turn interrupted)
   - При перезапуске Render Agent должен найти свои IN_PROGRESS job’ы по status_url и продолжить poll, не создавая новый paid request
   - ProducerAgent при старте проверяет state.stage — если rendering, проверяет render_events.jsonl на наличие новых completed events

=== ReviewGate grammar ===
Каждый gate показывает таблицу:

| Key | Decision | Что делает ProducerAgent |
|---|---|---|
| `a` | `approve` | фиксирует артефакт, добавляет слой в `approved_layers[]`, идёт дальше |
| `b` | `auto-fix` | запускает профильный fixer/Critic без дополнительных вопросов, возвращает preview |
| `c` | `edit-fix` | принимает текстовые правки пользователя, сохраняет `review_notes`, запускает targeted revise |
| `d` | `stop` | ставит `state.stage=paused:<gate_id>` и не двигает downstream |

Если сообщение содержит конкретные правки (типа "сделай дождь сильнее") — это `c) edit-fix`. Если сообщение двусмысленное — ProducerAgent задаёт один уточняющий вопрос. Старые alias-списки не использовать как контракт.

=== Выходные артефакты ===
Сгенерируй ЦЕЛИКОМ готовые файлы для каждого агента:

Для каждого `*-kinodel` создай:
1. `SKILL.md` — полный skill документ (frontmatter YAML + markdown body) с:
   - name, trigger, description
   - Роль и контракт input/output
   - Workflow (step-by-step)
   - Output contract (JSON schema примеры)
   - Pitfalls
2. Sidecar folders по [[kinodel-sidecar-context]] — если нужны дополнительные craft helpers:
   - `references/README.md` — что можно класть в refs и как не душнить контекст
   - `hooks/README.md` — story hooks / conflict seeds для творческих skills
   - `examples/micro-example.json` — маленький валидный пример output contract, до 30 строк
   - `styles/` / `templates/` — только если skill реально использует стиль или JSON/file skeletons
3. Обновления в существующих скиллах (если требуется)

Также создай:
4. `kinodel/kinodel/SKILL.md` — framework skill с архитектурной диаграммой, registry, state/review/render contracts. Он не заменяет `producer-kinodel`.
5. `projects/TEMPLATE/` — шаблон проекта с:
   - PreproductionPack.json (schema)
   - state.json (initial)
   - render_queue.jsonl (empty template)
   - reviews.jsonl (empty template)
   - render_events.jsonl (empty template)

=== Формат ответа ===
1. Начни с архитектурной схемы (mermaid diagram или ASCII tree) показывающей:
   - ProducerAgent в центре
   - Specialist agents как orbiting subagents (delegate_task)
   - Render Agent как background autonomous worker
   - State хранилища и data flow
   - Approve gate points как динамические transitions (не блокирующие)

2. Затем дай ОБЩИЙ design document (архитектурные решения, trade-offs, why delegate_task vs cron)

3. Затем пофайлово каждый SKILL.md (полный текст каждого файла)

4. Затем TEMPLATE проекта

5. Затем checklist "что нужно сделать вручную после генерации" (если есть)

=== Анти-overengineering ограничения ===
- Не создавать отдельный workflow engine: runtime state = `state.json` + jsonl logs на диске.
- Не создавать циклических зависимостей: specialist agents знают только свои inputs/outputs, а не внутренности ProducerAgent.
- Не создавать отдельный embedding/indexer на каждый approve: archival indexing запускается на release или explicit archive checkpoint.
- Не размножать provider-specific логику по агентам: все external calls проходят через `RenderJob` → `render-kinodel` adapter.
- Не hardcode модельные ограничения в ProducerAgent: Render Agent читает provider policy и workflow templates.
- Не использовать free-form approval aliases как state machine: только `ReviewGate` table `a/b/c/d` + typed edit notes.
- Проверенные fal.ai endpoints остаются в adapter templates, но архитектура допускает `fal.ai`, `openrouter`, `comfyui` и будущих провайдеров через тот же `RenderJob` envelope.
- Не превращать `references/hooks/styles/examples/templates` в production state: это skill-local sidecars, не L0-L6 и не `state.json`.

=== См. также ===
- [[kinodel-context-layers]] — L0-L6 context stack вместо identical goal
- [[kinodel-sidecar-context]] — references/hooks/styles/templates как компактные sidecar packs и micro examples
- [[kinodel-render-requests]] — RenderJob + provider workflow templates
- [[agent-producer-kinodel]] — orchestration и ReviewGate owner
- [[agent-render-kinodel]] — packaged/background render worker
- [[kinodel-rag-concept]] — embeddings как archival RAG для следующих проектов/серий
