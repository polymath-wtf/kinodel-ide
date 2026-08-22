---
title: ProducerAgent — Продюсер и Оркестратор
created: 2026-04-30
updated: 2026-05-25
type: entity
tags: [kinodel, agent, agent-architecture, orchestrator, cinema, video-pipeline]
sources:
  - ~/.hermes/skills/kinodel/producer-kinodel/SKILL.md
  - ~/.hermes/skills/kinodel/producer-kinodel/references/brief-start.md
  - ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py
  - ~/.hermes/skills/kinodel/producer-kinodel/scripts/producer_step.py
  - ~/.hermes/skills/kinodel/pipeline-kinodel/SKILL.md
  - .hermes/config.yaml
  - wiki/concepts/kinodel-context-layers.md
  - wiki/concepts/kinodel-rag-concept.md
confidence: high
contested: false
contradictions: []
---

# ProducerAgent — Продюсер и Оркестратор

## Core message

> «Я продюсер. Я state machine, не хранилище контента: держу в контексте только stage, artifact paths и gates, делегирую специалистам чтение/запись файлов, и не таскаю полный сценарий или промпты между агентами.»

ProducerAgent — **не сценарист, не раскадровщик, не монтажёр**. Он никогда не пишет сценарий и не генерирует картинки сам. Его работа — **artifact-centric orchestration**: BriefGate → интейк брифа → делегирование сабагенту с путями → file gate → user-review → следующий этап.

При упаковке skill name должен быть `kinodel/producer-kinodel`. Legacy wikilink `agent-producer-kinodel` остаётся названием страницы.

## Сабагенты

| Роль | Агент | Артефакт на выходе |
|------|-------|--------------------|
| Сценарист | [[agent-storytell-kinodel]] | `story.json` |
| Кинокритик | [[agent-critic-kinodel]] | optional `qc/*_critic.json` |
| Костюмер | [[agent-wardrobe-kinodel]] | `wardrobe_request.json` |
| Раскадровщик | [[agent-storyboard-kinodel]] | `storyboard_requests.json` |
| Кинодел | [[agent-filmmaker-kinodel]] | `video_requests.json` |
| Монтажёр | [[agent-montage-kinodel]] | `outputs/final.mp4` |
| **Render worker** | [[agent-render-kinodel]] | `outputs/*` + compact `render_results/*.json` |

**Никто кроме [[agent-render-kinodel]] не вызывает fal/Veo/Banana НАПРЯМУЮ.** Wardrobe, storyboard и filmmaker пишут request artifacts и выходят коротким статусом. ProducerAgent затем запускает packaged render worker. Это убирает двойную оплату токенов: контент генерируется в файл один раз и не перекладывается через summary в prompt следующего агента.

## Inputs / Outputs

- **Input:** реплика пользователя (свободный текст / правки / approve|revise на review-вороте).
- **Output (на каждом ходе):** одно из:
  - уточняющий вопрос юзеру (intake / review),
  - делегирование сабагенту (`storyteller`, `critic`, `wardrobe`, `storyboarder`, `filmmaker`, `editor`) с `project_dir/read/write`,
  - запись артефакта в `projects/<project_id>/v<N>/<artifact>.json`,
  - обновление live state `{stage, artifacts}` в текущем контексте,
  - финальный mp4 на `release`.

## Поведение

1. **BriefGate / Intake.** Ловит первичный вайб юзера, нормализует его через `references/brief-start.md` в компактную карточку vibe/story/hook/intrigue/characters/world/ending/format, завершает ход и ждёт ответа. Только после подтверждения пишет approved creative notes в `brief.user_vibe`; технические параметры раскладывает отдельно: platform, aspect_ratio, shot_count, image defaults, video defaults, provider/workflow, audio policy.
2. **Заводит проект.** Создаёт `projects/<project_id>/v1/brief.json`, `outputs/`, `render_results/`, and `qc/` через packaged initializer. Не создаёт future-stage stubs или empty `final_chunk.json`.
3. **Двигает пайплайн.** Выполняет route: brief → story.json → wardrobe_request.json → main_frame → ReviewGate → storyboard_requests.json → story images → ReviewGate → video_requests.json → videos → montage → final_chunk.
4. **Запускает render worker.** После появления request artifact пишет normalized execution request under `/tmp/kinodel/<project_id>/<run_id>/` или использует compatible stage artifact, запускает [[agent-render-kinodel]] with explicit `--stage images|videos`, `--result-file`, optional `--events-file`, and background `notify_on_complete=true`, then persists selected refs under `render_results/`. Default transition video is `fal:veo31_lite_flf2v` with minimum/default `8s`; legacy one-frame `i2v` may remain `4s`.
5. **Открывает ReviewGate.** После story + main_frame показывает media/summary и текстовый `A/B/C/D`; после story images повторяет gate перед запуском видео. Gate — hard stop: render completion не является approve, downstream skill нельзя грузить/делегировать до следующего явного ответа пользователя. "Run autonomously" may only continue deterministic work until the next ReviewGate; p4/p7 are never auto-approved.
6. **Финализирует.** В конце пишет [[kinodel-final-chunk]] only with final story/hook/media refs/conclusion.

## Правила

- **Не делает чужую работу.** Не пишет сценарий, не клеит видео, НЕ вызывает fal/Veo/Banana. Если возникает соблазн — это значит, нужного сабагента нет или RenderJob не попал в очередь.
- **BriefGate нельзя пропустить.** Defaults из `templates/brief.json` можно предложить как вариант, но нельзя молча считать их согласием пользователя. Перед созданием нового проекта Producer asks/confirms vibe + format and waits for an explicit reply (`A/B/C/D`, `ok`, `go`, or custom values).
- **Brief shape is fixed.** For new project intake, use `references/brief-start.md`; do not invent alternate brief schemas or persist ad-hoc fields outside canonical [[kinodel-brief]].
- **Gate hard-stop invariant.** BriefGate, ReviewGate p4 и ReviewGate p7 завершают текущий turn. Запрещён текст вроде "Autonomous pipeline continuing" / "storyboard next" после main_frame; следующий stage открывается только после явного approve в следующем user message. Нет autonomous/timeout bypass для p4/p7.
- **Один источник истины — диск.** `brief.json`, `story.json`, request artifacts, `render_results/`, `qc/`, `outputs/`, and final `final_chunk.json` are explicit artifacts. Raw provider/runtime garbage stays scratch.
- **Summaries are not transport.** Subagent response is only status like `done, wrote v1/story.json, 3 scenes`; Producer never forwards full artifact text to the next delegate unless a human preview requires a small excerpt.
- **Context layers — байт-в-байт.** Каждый approved artifact становится immutable layer. ProducerAgent не мутирует старые слои; при approve добавляет новый слой ниже, при revise заменяет только затронутый layer и invalidates только downstream. Это даёт бутербродный prompt-cache без hardcoded prefix.
- **User-review нельзя пропустить.** Story+main_frame gate and story-images gate are mandatory before downstream media. Each gate shows 4 variants: `A) approve`, `B) auto-fix`, `C) edit fix`, `D) stop`.
- **Approval grammar.** Text-first `A/B/C/D` is the state-machine contract across CLI, Telegram, and web. Кнопки допустимы только как UI sugar, если зеркалят те же варианты. Свободный текст на pending gate = `C) edit fix`; bare `C` → один уточняющий вопрос.
- **Идемпотентность.** Делегация одного и того же таска не создаёт дубли — ProducerAgent помечает `[~]` в todolist перед вызовом.
- **Render не держать в LLM child-chat.** Долгий render идёт через packaged/background worker and temporary request/result files. Producer waits for `notify_on_complete`, then reads result/events and shows media/gate.
- **Сабагенты — атомарны.** ProducerAgent смотрит только на `inputs` / `outputs` contract and file gates; each specialist reads input files itself.
- **Support skills не живут в Producer context.** Producer передаёт `handoff.stage.support_skills` в компактном JSON; delegated subagent загружает их после owner skill как methodology-only. `owner_skill` остаётся источником истины для schema/artifact/stage.
- **Redo with Pro.** Если юзеру не нравится качество кадра, ProducerAgent передаёт agent-render чтобы он сменил провайдера на `provider: fal:nano_banana_pro` и переделал конкретный кадр.

## Доступы

- **Hermes runtime** (`@/home/seryogasakura/.hermes/config.yaml`):
  - `delegation.orchestrator_enabled: true` — спавн сабагентов;
  - `approvals.mode: manual` — паузы на user-review;
  - `state.db` + `checkpoints/` — авто-снапшоты состояния агента;
  - `memory.memory_enabled` — память между сессиями.
- **Filesystem-тулы** для чтения/записи `projects/<id>/`.
- **MCP-тулы** для внешних API (image gen, video gen, ffmpeg `compose`) — но **сам не вызывает** генерацию, это ответственность профильных сабагентов.
- **Wiki**: [[cinema-pipeline]] (мастер-схема), [[storyboard-pattern]], [[ffmpeg-video-pipeline]], [[quality-check-pattern]], [[prompt-engineering]].

## Стек (Hermes-based)

| Компонент | Технология |
|-----------|-----------|
| Agent loop / runtime | **Hermes** CLI agent (`@/home/seryogasakura/.hermes/config.yaml`) |
| Master skill | `~/.hermes/skills/kinodel/producer-kinodel/SKILL.md` |
| Sub-agent orchestration | Hermes `delegate_task` (`goal=stable ContextLayer[]`, `context=task layers + role_skill`) |
| State / sessions / checkpoints | `state.db` (SQLite) + `sessions/` + `checkpoints/` |
| Project state on disk | `v<N>/brief.json`, `story.json`, request artifacts, `render_results/`, `qc/`, `outputs/`, `final_chunk.json` |
| Vector index | sqlite-vec (gemini-embedding-2 chunks, см. [[kinodel-rag-concept]]) |
| Approvals (user-review) | Text-first `A/B/C/D` ReviewGate + chat; optional buttons only mirror text choices |
| Image / Video generation | **Запускает [[agent-render-kinodel]] packaged/background worker** — не зовёт ни fal, ни Veo напрямую |
| VLM (Phase 2) | `auxiliary.vision` — QC референсов и шотов |
| MCP `compose` | использует только [[agent-montage-kinodel]] |
| Validation | **Текстовый контракт в `SKILL.md`** — без Zod / pydantic |

## Todolist реализации

- [ ] Master skill `~/.hermes/skills/kinodel/producer-kinodel/SKILL.md`:
  - роль продюсера / продюсера, явный запрет писать сценарий и генерировать ассеты лично;
  - алгоритм intake (список обязательных вопросов);
  - алгоритм state-machine (`{stage, artifacts}` → delegate with paths → gate file → advance);
  - правила user-review (5 гейтов, что показывать на каждом);
  - `ReviewGate` normalizer (`a/b/c/d`, free-text edits → `edit-fix`);
  - логика "Redo with Pro" для критичных кадров.
- [ ] Структура `projects/<project_id>/` (создание, layout, версионирование `v<N>`).
- [ ] Artifact gates: file exists + size > 0 + schema/field validation.
- [ ] Optional `qc/*_critic.json` notes for ReviewGate auto-fix/edit-fix loops.
- [ ] Делегирование 6 сабагентов через Hermes `delegation` с явными path-based inputs/outputs (по контракту из их `SKILL.md`).
- [ ] Логика инвалидации downstream-артефактов при `revise` (мап «какой шаг → что протухает»).
- [ ] Render wake-up loop: worker writes compact result JSON → Producer copies selected refs into `render_results/` → ProducerAgent opens review or retry; do not re-submit a paid job with existing provider status refs.
- [ ] Юнит-тест: один проход по фейк-проекту, без реальных вызовов image/video API (моки на MCP-тулы).
- [ ] Phase 1 = chat-only (CLI). Phase 2 = добавить [[timeline-editor]] для ручной правки монтажа.

## Фазы разработки

| Фаза | Описание |
|------|----------|
| 1 | Hermes-based MVP: 6 skills + ffmpeg `compose` + `projects/<id>/` на диске. Chat-only. |
| 2 | [[rag-memory]] для сабагентов, авто-[[vlm-analysis]] QC после каждой генерации, [[timeline-editor]] для ручной правки монтажа. |
| 3 | Production-deploy на Mac Mini + [[claw-integration]] → пересечение с [[agent-guzlik]]. |

> ⚠️ Claw (NemoClaw/OpenClaw) — ТОЛЬКО Phase 3, ТОЛЬКО Mac Mini. Никогда не разворачивать локально.

## См. также

- [[cinema-pipeline]] — мастер-схема пайплайна
- [[kinodel-rag-concept]] — message-array, production-master, implicit caching
- [[agent-render-kinodel]] — render-очередь (единственный исполнитель fal/Veo)
- [[agent-storytell-kinodel]] · [[agent-critic-kinodel]] · [[agent-wardrobe-kinodel]] · [[agent-storyboard-kinodel]] · [[agent-filmmaker-kinodel]] · [[agent-montage-kinodel]]
- [[storyboard-pattern]] · [[ffmpeg-video-pipeline]] · [[quality-check-pattern]] · [[prompt-engineering]]
- [[agent-guzlik]] — Phase 3 пересечение с Claw
