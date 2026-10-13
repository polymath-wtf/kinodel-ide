# Hermes: фактическая база для Kinodel Studio

**Исследование: 10 октября 2026.** Продуктовый вывод — [концепт](README.md).
Официальная документация сопоставлена с upstream `main` на commit [`dce1e9b37581dd62e480a9064dc04a709c2940d3`](https://github.com/NousResearch/hermes-agent/commit/dce1e9b37581dd62e480a9064dc04a709c2940d3). Ни установленный релиз, ни совместная работа с Kinodel не проверялись исполнением. Источники ниже подтверждают наличие механизмов, не результаты будущего интеграционного эксперимента.

Обозначения: **docs** — публичный документированный механизм; **source** — наблюдение исходников указанного commit; **гипотеза** — требует практической проверки. Установок, миграции, вызовов провайдера и изменений текущего runtime в рамках исследования нет.

## 1. Backend и agent runtime

**Docs/source.** Core написан на Python. `run_agent.py::AIAgent` — фасад собственного engine; цикл находится в `agent/conversation_loop.py` и `agent/turn_*.py`. Это LLM → tools → LLM, с лимитами, retries, compression и provider fallback, а не исполняемый граф творческих стадий.

LangGraph/LangChain не являются основой описанного core: архитектура описывает собственную оркестрацию, manifest не объявляет эти зависимости. Provider SDK не надо путать с agent framework. Публичный `/v1` API server реализован на aiohttp; FastAPI/Uvicorn относятся к dashboard/Desktop backend и plugin routes. Официальный Desktop — Electron/React.

В текущем manifest поддерживаемым runtime назван Python 3.14; более широкий диапазон оставлен для обновления старых установок. Это **не рекомендация менять `.venv313` Kinodel**: HTTP-мост позволяет раздельные окружения. Импорт `AIAgent` поддержан, но обычного supported wheel/sdist для простого подключения через `requirements.txt` документация не обещает — требуется подготовленный checkout.

Источники: [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture), [Agent Loop](https://hermes-agent.nousresearch.com/docs/developer-guide/agent-loop), [Python library](https://hermes-agent.nousresearch.com/docs/guides/python-library), [pinned manifest](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/pyproject.toml).

## 2. State machine: разговор, а не фильм

**Docs.** Gateway `SessionEntry` управляет жизнью conversation lane:

| Механизм | Что он означает | Чего из него нельзя заключить |
|---|---|---|
| `suspended` | На следующем обращении нужна новая session incarnation | Что отменён уже отправленный внешний render |
| `resume_pending` | Сохранить прежний transcript и допустить continuation | Что восстановлены точная нода, её inputs и paid-effect receipt |
| `/new`, `/reset` | Явная граница разговоров | Что материалы проекта удалены или производство откатилось |
| Active-turn marker + delivery ledger | Различить сохранённый ответ и незавершённый turn | Что любой вызов инструмента выполнится ровно один раз |
| Startup recovery | Gateway может продолжить незавершённый turn | Что HTTP run и живой child имеют тот же lifecycle |

После аварии уже сохранённый ответ может доставляться без его повторной генерации; незавершённый turn может запускать продолжение. Есть freshness/recovery policy и escalation для повторных неудачных рестартов. Это полезная надёжность чатовой системы, но не доказательство безопасного повторения всех внешних действий.

**Source: расхождение с docs.** `gateway/session_persistence.py` называет SQLite `gateway_routing` primary store, а `sessions.json` — legacy mirror; страница lifecycle частично описывает прежний вариант. В диаграмме остались idle/daily resets, хотя текст страницы отрицает их поддержку, а `_route_reset_reason` проверяет suspension. Не проектировать мост по одной картинке или boolean flags.

Источники: [Gateway lifecycle](https://hermes-agent.nousresearch.com/docs/developer-guide/gateway-session-lifecycle#boolean-flags-state-machine), [Session storage](https://hermes-agent.nousresearch.com/docs/developer-guide/session-storage), [persistence source](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/gateway/session_persistence.py), [lifecycle source](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/gateway/session_lifecycle.py).

## 3. Сабагенты и `delegate_task`

**Source.** `delegate_task` создаёт новый child `AIAgent` с отдельной беседой, session/task identity и контекстом задания. История родителя не передаётся автоматически. Контракт включает `spawn/list/steer/stop`; публичного `resume` прежнего child worker по task ID в исследованной схеме нет.

В model-facing top-level dispatch background выбирается при подходящем получателе результата; finite/stateless вызовы и ограничения pool могут переводить работу в synchronous fallback. Nested orchestrator ждёт workers внутри своего turn. Direct Python call имеет другую исходную семантику. Следовательно, «delegate всегда background» неверно.

Есть progress events и durable `async_delegations` ledger: dispatch, завершённые частичные результаты и completion. После смерти владельца незавершённые units становятся `unknown`; записанные результаты могут сохраняться и повторно доставляться. Старые workers автоматически не восстанавливаются. Есть ограничения retention/replay; при неудачной durable записи код допускает in-memory-only delivery.

Cancellation кооперативная. Остановка агента не подтверждает остановку внешней генерации. Gateway может принимать поздние completion как внутренний wake; HTTP server-history consumer допускает detached result для следующего client turn **без такого же automatic model wake**. HTTP `/v1/runs` имеет отдельные terminal statuses, включая interruption при shutdown.

**Следствие.** Для Kinodel стабильная сущность — собственное задание и его сохранённый результат, не живой child object. `unknown` требует выяснения исхода; новый spawn не является безопасным Retry автоматически. Для проекта нужно связывать child session, Hermes run и собственное work ID, не использовать один произвольный ID вместо всех трёх.

Источники: [delegate schema/construction](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/tools/delegate_tool.py), [dispatch](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/tools/delegate_tool_dispatch.py), [config/depth](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/tools/delegate_tool_config.py), [durability/recovery](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/tools/async_delegation.py#L260), [in-memory degradation](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/tools/async_delegation.py#L897), [Programmatic Integration](https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration).

## 4. Structured output есть, но приём результата нужен свой

**Source.** `output_schema` добавляет JSON Schema contract в prompt child. Код извлекает JSON, проверяет его и допускает один correction turn. После неудачи результат может иметь `status="completed"` вместе с `schema_valid=false`; при исчерпании budget возможен `truncated=true`.

Если `jsonschema` недоступен, parsed JSON принимается без проверки schema. Correction использует полноценный `child.run_conversation()`, а не изолированный formatter без tools. Поэтому нельзя рассчитывать, что коррекция формата никогда не повторит побочный эффект.

**Граница Kinodel:** обязательный локальный validator, проверка полноты и принадлежности результата заданию; только после этого сохранение версии и открытие downstream. `completed`, valid JSON и creative approval — три разные проверки. Семантическую правильность результата одна schema тоже не обеспечивает.

Источники: [schema helpers](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/tools/delegation_output_schema.py), [correction/result handling](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/tools/delegate_tool_child_run.py#L478).

## 5. Публичные API и видимость разговоров

| Поверхность | Подтверждено в docs/source | Ограничение для Kinodel |
|---|---|---|
| HTTP API server | Chat Completions/Responses; `/v1/runs`, status/events, approval/steer/stop; session history; `/v1/capabilities` | Не путать model-compatible completion с production lifecycle. Проверять точные capabilities релиза |
| HTTP SSE | Text, tool lifecycle, approval, subagent start/complete | Не полный поток всех действий child; child tool/progress events фильтруются |
| Run steering | Очередь уточнений работающему run | HTTP endpoint не равен child-steering; accepted не доказывает consumed |
| JSON-RPC | TUI gateway по stdio/WS; методы session/subagent | Для live child требуется связь с точным parent runtime/transport |
| RPC child operations | `subagent.list/tail/steer/interrupt` | Tail ограничен; roster не гарантирует право управления после reconnect |
| Saved child history | Listing с `include_children`, чтение сохранённых messages | Не гарантия полного live transcript в каждый момент |
| Server→client questions | Approval/clarify с capability handshake и ответом по id | Недостаточно только слушать events |

Маршруты `/v1/...`, `/api/...` и RPC принадлежат разным поверхностям; нельзя считать их одним идентичным контрактом. Для первого внешнего localhost-приложения рекомендуется backend-to-backend HTTP + SSE, не браузер с Hermes bearer. Если обязательны live child chats, RPC нужно проверить до обещания этой функции, а не прикрыть её parent HTTP steer.

Наблюдаемое расхождение: краткий пример API key в docs не соответствует minimum 16 текущего source; CORS allowlist не покрывает все используемые headers/methods. Серверный мост уменьшает browser-зависимость, но не снимает проверки доступа и корректной session routing.

Источники: [API server](https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server), [Programmatic Integration](https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration), [registered HTTP routes](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/gateway/platforms/api_server.py#L1718), [HTTP steering](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/gateway/platforms/api_server_runs.py#L1219), [WS gateway](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/tui_gateway/ws.py), [subagent RPC](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/tui_gateway/methods_subagents.py#L47).

## 6. Плагины: три разных SDK/контракта

| Расширение | Где работает | Что можно добавить |
|---|---|---|
| Python agent plugin | CLI/gateway process | Tools, hooks, commands, skills, providers |
| Dashboard extension | Web dashboard | Tab/slots, JS/IIFE через `window.__HERMES_PLUGIN_SDK__`, optional FastAPI routes |
| Desktop plugin | Официальный Electron Desktop | React panes/pages/nav через `@hermes/plugin-sdk`, gateway RPC и plugin REST namespace |

Desktop disk entry — ESM `desktop-plugins/<id>/plugin.js`; unified package может содержать `plugins/<id>/desktop/plugin.js`. Loader не компилирует JSX и напрямую разрешает только SDK/React imports. Это не запрет React, но и не готовая загрузка любого Vite-приложения с graph-library.

Python backend `plugin_api.py` может монтироваться под `/api/plugins/<id>` и требует отдельного allow-list enablement. Включение renderer plugin не означает разрешения импортировать backend code. Agent plugin выполняется с правами процесса: capability consent не является sandbox.

`SandboxedFrame` позволяет встроить внешнюю localhost-страницу, но исключает `allow-same-origin`; SDK не передаётся внутрь автоматически. Storage, auth/cookies, `Origin: null` и CSP требуют проверки. **Гипотеза:** тонкая Desktop-оболочка сможет удобно открыть Kinodel; готовность всего текущего UI внутри frame не доказана.

Источники: [Build a plugin](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins), [Observer hooks](https://hermes-agent.nousresearch.com/docs/developer-guide/observer-hooks), [Dashboard extensions](https://hermes-agent.nousresearch.com/docs/user-guide/features/extending-the-dashboard), [Desktop](https://hermes-agent.nousresearch.com/docs/user-guide/desktop), [Desktop SDK](https://hermes-agent.nousresearch.com/docs/developer-guide/desktop-plugin-sdk), [sandbox source](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/apps/desktop/src/components/ui/sandboxed-frame.tsx#L7).

## 7. Skills, локальная библиотека и память

**Docs/source.** Skills — переносимые инструкции и ресурсы. Memory включает компактные `MEMORY.md`/`USER.md`, session recall через SQLite/FTS и дополнительные providers. Внешние providers могут выводить данные за локальный диск: «Hermes локальный» не означает «ни один материал не отправляется наружу»; модельные вызовы тоже зависят от выбранного провайдера.

Profile разделяет configuration/memory/skills/session DB; Bot Mode представляет durable специалистов через profiles. Отдельный child conversation не равен profile. Profile — не filesystem sandbox. `session_id` или session key не создаёт авторизацию Kinodel автоматически.

Bundled `llm-wiki` использует Markdown/filesystem и `WIKI_PATH`. Provenance и правила библиотеки описаны в skill, а не обеспечены транзакционным wiki backend. Для Kinodel нужен отдельный корень библиотеки; проектные знания можно читать явно, но утверждения, immutable versions и operation receipts публикуются через контролируемый путь.

Команда сжатия в reference — `/compress [here [N] | focus topic]`; `/compact` там не указан. Compression не заменяет сохранённые результаты. Точная связь durable lineage/live session после compression тоже должна проверяться мостом, а не выводиться из неизменности одного ID.

Источники: [Skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills), [Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory), [Profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles), [Bot Mode](https://hermes-agent.nousresearch.com/docs/user-guide/bot-mode), [wiki skill](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/skills/research/llm-wiki/SKILL.md), [slash reference](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/website/docs/reference/slash-commands.md).

## 8. Инструменты, ComfyUI и approval

У Hermes есть tools, terminal, web/browser и MCP. ComfyUI представлен официальным **optional skill** со скриптами workflow/schema/dependencies, REST/WS monitoring, batches/downloads. Наличие инструментов сильно сокращает путь к творческому эксперименту, но не подтверждает работу любого установленного workflow, модели или provider.

Terminal approval и API approval регулируют разрешённые действия. Это не готовое согласование конкретной версии сценария или дубля. HTTP submit и WS progress не заменяют хранение точного заказа, локального оригинала и решения автора. Отмена, Retry и неизвестный ответ провайдера остаются consequential границами.

Анализ музыки/beat tracking не проверялся. Доступ к терминалу позволяет применять подходящий анализатор, но его доступность, качество и формат результата — отдельные гипотезы. Большие arrays/timelines не должны становиться постоянным содержимым основного чата.

Источники: [Tools runtime](https://hermes-agent.nousresearch.com/docs/developer-guide/tools-runtime), [Tools/toolsets](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools), [MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp), [ComfyUI skill](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/optional-skills/creative/comfyui/SKILL.md).

## 9. Что означает добавление LangGraph

Hermes не обязан знать LangGraph. Узел Kinodel может сформировать ограниченное задание, вызвать Hermes API, принять проверенный результат и сохранить ссылку. Так объединяются разные runtimes; общей системы классов нод или «одинакового языка» не требуется.

LangGraph checkpoints сохраняют ход маршрута; `interrupt` поддерживает остановку до решения человека. Но при resume функция узла может выполняться заново. Checkpointer не заменяет идемпотентность tools, receipts и сверку внешнего заказа. Привязка approval к revision и политика исправления последующих материалов — логика Kinodel, не автоматическая функция framework.

Для новой свободной sketch-сессии LangGraph необязателен. Для управляемого маршрута разумнее переиспользовать существующий Kinodel/LangGraph, чем писать собственный generic workflow engine поверх Hermes. В обоих случаях один владелец управляет конкретной производственной работой; продюсер предлагает действия и использует контролируемые tools.

Источники: [LangGraph re-execution/idempotency](https://docs.langchain.com/oss/python/langgraph/graph-api#re-execution-and-idempotency), [revision-boundaries Kinodel](../backend/artifacts.md), [runtime Kinodel](../backend/runtime.md), [architecture Kinodel](../backend/architecture.md).

## 10. Лицензия и предел вывода

Core Hermes — MIT: коммерческое использование и модификация разрешены с сохранением notice. Лицензии сторонних skills/plugins, моделей, зависимостей и условия сервисов проверяются отдельно. Нельзя переносить MIT core на всю будущую библиотеку контента.

Источник: [pinned LICENSE](https://github.com/NousResearch/hermes-agent/blob/dce1e9b37581dd62e480a9064dc04a709c2940d3/LICENSE).

**Не установлено этим исследованием:** production-гарантия отсутствия повторных paid effects; полностью восстанавливаемый child worker; строгая schema-гарантия любого final answer; готовый arbitrary-node workflow editor; автоматическое согласование ревизий; беспроблемная загрузка Kinodel UI в Desktop; измеренное сокращение срока/стоимости MVP. Это не доказательство отсутствия каждой возможности во всём repo, а границы проверенных поверхностей.

Практический вывод и предложенные границы эксперимента находятся только в [концепте](README.md). При начале реализации нужно заново выбрать точный доступный релиз, проверить capabilities и провести focused integration checks; этот upstream snapshot не является принятой зависимостью Kinodel.
