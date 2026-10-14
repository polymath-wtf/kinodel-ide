# Hermes: краткая фактическая опора

**Обновлено 14 октября 2026.** Это указатель на исследованные механизмы и их ограничения, не архитектура или отчёт о работающем плагине. Продуктовые решения находятся в [plugin-docs](plugin-docs/hermes-kinodel.md).

Первоначальное исследование 10 октября сопоставляло upstream с commit [`dce1e9b37581dd62e480a9064dc04a709c2940d3`](https://github.com/NousResearch/hermes-agent/commit/dce1e9b37581dd62e480a9064dc04a709c2940d3). Локальный [снимок docs](hermes-docs/README.md) не привязан к этому commit. Нельзя объединять их в доказательство версии установленного Hermes. Интеграционные проверки здесь не проводились; полный прежний обзор сохранён в git history.

| Что можно переиспользовать | Источник снимка | Существенная граница |
|---|---|---|
| Python plugin tools/skills и dispatch | [plugins](hermes-docs/backend/plugins.md):95–119 | Не готовый endpoint для любого browser tool call |
| Sessions/history, HTTP runs и SSE | [api-server](hermes-docs/backend/api-server.md):448–565, 603–630 | Shutdown может прервать run; SSE не долговечный журнал |
| Session fork | [api-server](hermes-docs/backend/api-server.md):614–615 | Ветка разговора, не копия проекта, approvals или media jobs |
| Делегирование и structured output | [delegation](hermes-docs/backend/delegation.md):55–86 | Свежий контекст child; `completed` не всегда schema-valid |
| Ограниченный child lifecycle | [subagent API](hermes-docs/backend/subagent-lifecycle-api.md):8–61 | Active parent, in-process результаты; restart не возобновляет worker |
| Image/video generation providers | [image](hermes-docs/tools/image-gen-provider-plugin.md), [video](hermes-docs/tools/video-gen-provider-plugin.md) | FAL документирован; ComfyUI adapter и нужные workflows надо подтвердить отдельно |
| Context files и references | [files](hermes-docs/context/context-files.md), [references](hermes-docs/context/context-references.md):98–110 | Автоинструкции не хранилище проекта; `@` expansion прежде всего CLI, сжатие теряет точный текст |
| Kanban tasks/dispatcher | [Kanban](hermes-docs/kanban/kanban-big-context.md) | Выбран для исполнения cinematic; точные переходы задаёт plugin, `done` не creative approval; same-card rework не доказывает same-session resume |

## Расхождения, которые нельзя скрыть

- Kanban docs: token auth на строке 873 против unauthenticated plugin HTTP routes на 915–919. Это другая поверхность, чем bearer-protected API server; проверить actual routing, если её используем.
- Child lifecycle page описывает synchronous delegation, основной delegation guide — host-dependent background. Выбирать по установленному контракту, не по одному описанию.
- Run idempotency защищает создание run в рамках своего срока хранения, но не доказывает отсутствие повторного внешнего render. Нужны сохранённые связи операции и receipt.

## Что остаётся проверить

Точный способ поставки localhost UI и custom actions, механизм переходов и tool-wait, приём output, storage решений/версий и подключение выбранного ComfyUI-профиля. Пользователь сообщил о проверенном worker-session resume; способ вызова уточняется. Полная очередь — [вопросы реализации](plugin-docs/hermes-questions.md), а не повод перечитывать весь upstream или строить собственный Hermes.

Официальные исходные точки: [API server](https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server), [plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins), [architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture). Наличие механизма в документации не означает проверенный деплой Kinodel.
