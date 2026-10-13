# Hermes docs: роутинг для оркестратора

Локальная подборка документации Hermes для исследований. **Начинай с этой карты, затем поручай ресёрчеру конкретный файл и разделы.** Точные главы и диапазоны строк находятся в [CHAPTERS.md](CHAPTERS.md). Это исследовательские источники, а не описание уже реализованных возможностей Kinodel.

## Бюджет контекста

**Все значения токенов приблизительные:** число Unicode-символов / 4, с округлением; учитываются frontmatter, текст и код. Токенизатор модели не использовался, реальный объём зависит от модели и языка. Строки посчитаны точно, с 1.

21 исходник суммарно содержит **≈143 775 токенов**. Особенно большие: hooks **≈31,4k**, Kanban **≈30,6k**, plugins **≈15,6k**, delegation **≈12,7k**, API **≈11k**. Их следует читать по главам: `limit=400` ограничивает строки, но не токены — длинные строки тоже занимают контекст.

## Карта файлов

В колонке «Содержание / задача ресёрчеру» указано, какой вопрос отправлять в соответствующий файл. Последняя колонка — **строки нужного блока в CHAPTERS.md**, а не в исходнике. Сам README занимает ≈2,9k токенов, полный индекс — ≈3,8k; индекс можно читать только нужным блоком.

| Файл | Строк | ≈ токенов целиком | Содержание / задача ресёрчеру | Главы: строки CHAPTERS |
| --- | ---: | ---: | --- | --- |
| [overview.md](overview.md) | 57 | 1 827 | Каталог возможностей: core, automation, media/web, integrations, customization. Найти семейство функций и дальнейшие upstream-источники. | [7–19](CHAPTERS.md#overview) |
| [backend/plugins.md](backend/plugins.md) | 1 020 | **15 591** | Расширения: discovery, opt-in, установка/обновление, consent, isolation, message injection, MCP. Выбрать extension point и проверить условия активации. | [20–50](CHAPTERS.md#plugins) |
| [backend/api-server.md](backend/api-server.md) | 841 | **11 038** | HTTP/OpenAI-compatible endpoints, Runs/SSE/approval, sessions/jobs, model/profile routing, auth. Исследовать внешний UI/control plane, continuation и повторы запросов. | [51–76](CHAPTERS.md#api-server) |
| [backend/delegation.md](backend/delegation.md) | 674 | **12 700** | Subagents: отдельный контекст, batch/schema, async delivery, steering/cancel, модели, nesting, worktrees. Составить briefing и проверить lifetime/durability делегации. | [77–108](CHAPTERS.md#delegation) |
| [backend/hooks-big-context.md](backend/hooks-big-context.md) | 2 147 | **31 360** | Gateway/plugin/shell hooks и outbound webhooks; подробные payload/return-контракты, injection/transforms, approval и lifecycle. Выбрать событие и проверить timing/обработку ошибок. | [109–172](CHAPTERS.md#hooks) |
| [context/context-files.md](context/context-files.md) | 249 | 3 095 | Автозагрузка .hermes.md/AGENTS/CLAUDE/SOUL/.cursorrules, цепочка каталогов, progressive discovery, лимиты и scanning. Проверить, какие инструкции попадут в контекст. | [173–188](CHAPTERS.md#context-files) |
| [context/context-references.md](context/context-references.md) | 142 | 1 347 | CLI-ссылки `@file/folder/diff/git/url`, диапазоны строк, лимиты и ограничения платформ. Выбрать способ точечного прикрепления контекста. | [189–206](CHAPTERS.md#context-references) |
| [context/personality.md](context/personality.md) | 289 | 2 436 | Глобальный SOUL, presets, session overlays, config/reset и prompt stack. Разделить личность, проектные правила и временный режим. | [207–231](CHAPTERS.md#personality) |
| [tools/tools.md](tools/tools.md) | 265 | 3 787 | Tools/toolsets, terminal backends, контейнеры, background processes/receipts, sudo. Выбрать поверхность исполнения и исследовать изоляцию/сохранность результатов. | [232–245](CHAPTERS.md#tools) |
| [tools/batch-processing.md](tools/batch-processing.md) | 230 | 2 259 | JSONL batch runner для training/evals: toolset distributions, ShareGPT trajectories, checkpoint/resume, filtering. Исследовать массовый сбор траекторий. | [246–263](CHAPTERS.md#batch-processing) |
| [kanban/kanban-big-context.md](kanban/kanban-big-context.md) | 1 449 | **30 568** | Основной справочник board/SQLite: dependencies, claims/runs, dispatcher, artifacts/workspaces, PR gates, GUI/REST, notify/wake. Проверить долговечную координацию и lifecycle задач. | [264–300](CHAPTERS.md#kanban) |
| [kanban/kanban-tutorial.md](kanban/kanban-tutorial.md) | 310 | 4 995 | Сквозные сценарии solo/fleet/role pipeline, review/retry, crash recovery и follow-up. Восстановить последовательность работы и handoff. | [301–318](CHAPTERS.md#kanban-tutorial) |
| [kanban/kanban-worker-lanes.md](kanban/kanban-worker-lanes.md) | 143 | 3 349 | Контракт executor lane: assignee, spawn/env, descendant scope, outputs/review, audit/failures. Оценить подключение внешнего CLI-worker. | [319–334](CHAPTERS.md#worker-lanes) |
| [kanban/kanban-multi-gateway.md](kanban/kanban-multi-gateway.md) | 52 | 562 | Один dispatcher и доставка по владельцу profile, включая review feedback. Проверить несколько gateway без дублирования dispatch. | [335–345](CHAPTERS.md#multi-gateway) |
| [tools/tool-gateway.md](tools/tool-gateway.md) | 249 | 4 124 | Nous-managed tools: подписка/OAuth, явный выбор provider, BYOK, image fallback, connector accounts и endpoints. Проверить активацию и правила маршрутизации/отказов. | [346–363](CHAPTERS.md#tool-gateway) |
| [tools/adding-tools.md](tools/adding-tools.md) | 211 | 1 672 | Добавление встроенного/core tool: schema/handler/check_fn, autodiscovery, toolsets, async, task_id и intercepts. Выбрать skill/plugin/core и определить минимальные изменения для core tool. | [364–380](CHAPTERS.md#adding-tools) |
| [backend/architecture.md](backend/architecture.md) | 280 | 3 694 | Внутреннее устройство Hermes: entry points, AIAgent, prompt/provider/tools, storage/backends и data flows. Найти владельцев подсистем и upstream code entry points. | [381–395](CHAPTERS.md#architecture) |
| [tools/image-gen-provider-plugin.md](tools/image-gen-provider-plugin.md) | 321 | 3 310 | Image provider plugin: ABC, capabilities/references, model/setup metadata, discovery, response, URL/base64 и overrides. Выделить контракт адаптера генерации и минимальные contract/smoke-проверки. | [396–415](CHAPTERS.md#image-gen-provider-plugin) |
| [backend/subagent-lifecycle-api.md](backend/subagent-lifecycle-api.md) | 61 | 737 | Plugin API управления дочерними сессиями: capability handle, launch/status/wait/cancel/result/reconnect. Проверить supervision и in-process lifetime; отличить от model-facing delegation и restart recovery. | [416–423](CHAPTERS.md#subagent-lifecycle-api) |
| [tools/tools-runtime.md](tools/tools-runtime.md) | 250 | 2 997 | Внутренние registry/dispatch: schema, availability/toolsets, override consent, hooks/errors/async, terminal approval и owner-bound process receipts. Восстановить путь исполнения и границы полномочий/результатов. | [424–439](CHAPTERS.md#tools-runtime) |
| [tools/video-gen-provider-plugin.md](tools/video-gen-provider-plugin.md) | 233 | 2 327 | Video provider plugin: text/image-to-video, ABC/capabilities, model families → endpoints, selection, response и media cache. Проверить modality routing, ограничения параметров и сохранение output. | [440–457](CHAPTERS.md#video-gen-provider-plugin) |

`future/` пока пуст. `README.md` — краткая карта; `CHAPTERS.md` — навигационный индекс, а не дополнительный upstream-источник.

## Быстрые маршруты по задачам

| Вопрос | Начать с | Дополнительный источник при необходимости |
| --- | --- | --- |
| Как выдавать ограниченные задачи сабагентам? | delegation → How Subagent Context Works; Batch Mode Details | kanban → Kanban vs. delegate_task; сверить различия с delegation |
| Как организовать долговечную очередь, review/retry и recovery? | kanban-tutorial → Stories 3–4 | kanban → worker lifecycle; Runs; worker-lanes |
| Как подключить UI к выполнению/статусу/сессиям? | api-server → Runs; Sessions; Endpoints | kanban → Dashboard (GUI); hooks → lifecycle observers |
| Как внедрить контекст или перехватить tool/LLM вызов? | hooks → нужный pre/post/transform контракт | plugins → Pluggable interfaces; consent/isolation |
| Как управлять инструкциями и размером контекста? | context-files → загрузка и Size Limits | context-references → Line Ranges; personality → prompt stack |
| Как исполнять команды и управлять background work? | tools → Terminal Backends; Background Process Management | delegation → Background process lifetime; worker-lanes |
| Как запускать массовые eval/training-задания? | batch-processing → Dataset Format; Output Format; Checkpointing | tools → toolsets |
| Где искать владельцев подсистем Hermes? | architecture → System Overview; Data Flow; Major Subsystems | профильная страница нужного runtime/extension |
| Как добавить tool и проверить его dispatch? | adding-tools → выбор core/plugin; Steps 1–2 | tools-runtime → registration; availability; Dispatch; plugins |
| Как написать image/video provider adapter? | image-gen-provider-plugin / video-gen-provider-plugin → ABC; response; Testing | plugins → discovery/opt-in; tool-gateway → managed routing |
| Как подключить managed tools или смешать их с BYOK? | tool-gateway → enablement; Mix and match; Configuration reference | image/video provider contracts при собственном adapter |
| Как плагину запускать и контролировать дочернюю сессию? | subagent-lifecycle-api → вся страница | delegation → Lifetime and Durability; hooks → subagent_start/stop |

## Как поручать чтение по главам

1. Выбери файл по карте и открой **его блок** в `CHAPTERS.md` по последней колонке; например, plugins: `offset=20, limit=31`.
2. Передай ресёрчеру вопрос, путь и диапазоны нужных глав. Он читает соседние разделы только при необходимости.
3. Для диапазона `start–end`: `offset=start`, `limit=end-start+1`. Нумерация с 1, конец включён.

Например, вместо загрузки всех ≈15,6k токенов `backend/plugins.md`:

```text
Задача: выяснить extension point, consent и isolation для нашего плагина.
→ Read docs/hermes/hermes-docs/backend/plugins.md [offset=352, limit=29]
→ Read docs/hermes/hermes-docs/backend/plugins.md [offset=518, limit=65]
→ Read docs/hermes/hermes-docs/backend/plugins.md [offset=803, limit=51]
Вернуть: вывод, ограничения, ссылки path:line и что требуется проверить в коде.
```

Для инструмента `read` путь передаётся абсолютным: `filePath="D:\\Ai\\kinodel-ide\\docs\\hermes\\hermes-docs\\backend\\plugins.md"`. Пример целевого чтения hooks: `offset=546, limit=79` — контракт `pre_tool_call` вместо всего файла на ≈31,4k токенов.

## Как трактовать источники

- Большие справочники пересекаются: plugins даёт обзор hooks; tutorial/lanes/multi-gateway дополняют Kanban. Читать весь набор для одного вопроса обычно не требуется.
- Единой версии/commit snapshot здесь не указано. В источниках есть расхождения по concurrency/durability делегации, plugin opt-in и защите Kanban REST. При исследовании гарантий сверяй профильную главу, соседний контракт и актуальную реализацию; возвращай расхождения явно.
- Tool Gateway описывает managed provider routing, а не messaging Gateway. Subagent Lifecycle API хранит supervision/results in-process; гарантии завершённых результатов из delegation не переносятся на него автоматически. Image/video provider-контракты сами по себе не задают durable jobs или idempotency.
- Часть исходных upstream-ссылок и изображения отсутствуют локально. Ссылки в этой карте ведут к имеющимся файлам. Диапазоны индекса относятся к текущей копии: после изменения исходников их нужно пересчитать.
