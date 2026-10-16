---
title: "Kinodel — localhost WebUI и подключение к Hermes"
created: 2026-10-16
updated: 2026-10-16
type: research
tags: [kinodel, preproduction, frontend, backend, architecture]
sources: [kinodel-preproduction/frontend-workspace.md, ../hermes_cli/web_server_dashboard.py, ../hermes_cli/web_routers/dashboard_ui.py, ../tui_gateway/contracts/canonical_sessions.py, ../gateway/run_api.py]
confidence: medium
status: proposed-architecture
---

# Localhost WebUI и подключение к Hermes

## Поверхность продукта
**Требование:** самостоятельное браузерное приложение React + React Flow на localhost. Не вкладка административного dashboard, не Desktop plugin, не замена штатного Hermes UI. Можно переиспользовать сервер Hermes, не переиспользуя его экранную оболочку.

**Исследовано 2026-10-16:** checkout `dfa79389773271ee78c41a7af340848948d461ee`, исходники и официальная документация Plugins / Extending the Dashboard / Kanban. Это source inspection, не проверенный запуск браузера. Утверждения предыдущего исследования про обязательные `desktop/plugin.js`, `host.openSession` и Desktop composer к этому продукту не относятся.

## Предпочтительная схема — один origin
```text
Браузер: собственная оболочка Kinodel
  ├─ React Flow / Canvas / Inspector / ProducerChat
  ├─ REST → /api/plugins/kinodel/… → domain commands/read model
  ├─ WS JSON-RPC → /api/ws → штатные sessions и агентные turns
  └─ media → авторизованный resource-id endpoint Kinodel
Hermes HTTP listener: существующие auth, profile scope, plugin routing
  ├─ Kinodel domain + persistence + Kanban adapter
  └─ Native session authority + Kanban dispatcher
```
REST/polling достаточно для производства; native WS обслуживает чат. Не нужен второй SSE-сервер для каждого render и не нужно переносить chat streaming внутрь plugin API. Hosted plugin isolation буферизует HTTP и не поддерживает streaming/WS: `hermes_cli/web_server_dashboard.py:829–854`.

## Упаковка без Desktop
Предлагаемый внешний пакет: `plugin.yaml`, `__init__.py` с регистрацией узких tools/commands, role skills, `dashboard/manifest.json`, `dashboard/plugin_api.py` и собранные HTML/JS/CSS в `dashboard/dist/`. Имя каталога `dashboard` — соглашение backend discovery, а не требование показывать административный dashboard пользователю.

Существующий asset handler может вернуть HTML по `/dashboard-plugins/kinodel/dist/index.html`; API монтируется под `/api/plugins/kinodel/`. HTML открывается как отдельное приложение. Bundle включает React Flow; asset URLs относительны, начальная навигация — hash-router, чтобы не требовать нового SPA history fallback. Это предложение сборки; manifest/discovery и загрузка bundle ещё требуют smoke test. Основания: `hermes_cli/web_server_dashboard.py:561–585,872–885,979–1045`; `hermes_cli/web_routers/dashboard_ui.py:374–414`.

**Уточнение аудита:** dashboard автоматически загружает manifest `entry`/CSS даже при hidden tab и ожидает plugin registration (`web/src/plugins/usePlugins.ts:102–154`; `hermes_cli/web_server_dashboard.py:526–553`). Самостоятельный SPA mount bundle нельзя без проверки использовать как тот же entry: он может выполниться в штатном dashboard. Требуется отдельный безопасный discovery entry и standalone HTML/bundle либо другой проверенный serving path. Это открытая часть packaging spike, не готовая реализация; см. [[kinodel-preproduction/readiness-audit]].

**Не добавляем** Desktop SDK, iframe bridge или зависимость от Electron. Не копируем dashboard source. Новый UI-компонент ProducerChat — представление native conversation, не новая история/модель/agent loop.

## Auth: главный незакрытый web-вопрос
Static plugin HTML отдаётся без auth и без обычной dashboard token injection. Там только публичные assets, никаких Brief, media, ключей или runtime bootstrap secrets. Защита пути static handler не заменяет авторизацию проекта. `hermes_cli/web_routers/dashboard_ui.py:385–414`.

У Hermes два разных режима:
- Обычный dashboard backend умеет инжектировать loopback session token в **свою** SPA; gated mode использует штатную browser login/session cookie. Не считать эту инъекцию свойством любого HTML. `hermes_cli/web_server_dashboard.py:151–196`; `hermes_cli/dashboard_auth/middleware.py:160–214`.
- Gateway-owned listener намеренно не публикует loopback token. Native control-socket ticket не является browser login: browser Origin отклоняется native bootstrap-путём. `gateway/run_api.py:63–72,291–300`; `hermes_cli/dashboard_auth/native_http.py:1–6`.

**Предпочтение:** штатная gated browser session, same-origin запросы и fresh single-use WS ticket через `POST /api/auth/ws-ticket`. Сам endpoint требует уже авторизованную session, не решает первоначальный вход. Проверить доступность этого режима на фактическом host; если её нет, первый web-срез блокируется на поддержанном browser bootstrap, а не обходится чтением private credentials или отключением Origin-check. `hermes_cli/dashboard_auth/routes.py:556–564`; `web/src/lib/api.ts:265–299`.

Не передавать долгоживущие токены в URL/localStorage и не извлекать секрет из другой вкладки. Domain actions проверяют actor, owner profile и project; `?profile=` задаёт scope, но само по себе не является разрешением. Cookie-команды должны проходить действующие host Origin/CSRF проверки. Media handler использует resource-id, containment и project authorization; MP4 playback требует проверенного Range-пути.

## Producer chat через native protocol
`/api/ws` передаёт соединение `tui_gateway.ws`; backend выбирает canonical session authority, когда она присутствует, иначе legacy dispatcher. Одинаковые имена методов не доказывают одинаковый контракт. Для первого среза предлагаем поддержать **один проверенный canonical contract**, а не писать совместимость со всеми версиями. `hermes_cli/web_routers/chat_ws.py:702–734`; `tui_gateway/ws.py:309–333`.

Предлагаемый browser adapter:
1. Проверить host/auth и установленный session contract, подключить WS.
2. Создать/восстановить Producer session; сохранить в Project только её native ID и owner profile.
3. Послать сообщение со стабильным `submission_id`/`input_id`; повтор доставки не становится новым пользовательским запросом.
4. Рендерить native messages/tool/clarify/approval events; полный transcript хранится в Hermes.
5. На reconnect запросить `session.events.since` с sequence/epoch; при `snapshot_required` перечитать snapshot, не переслать автоматически prompt.
6. Interrupt/steer и ответы на tool approvals адресовать текущему `execution_generation`.

Контракты: `tui_gateway/contracts/canonical_sessions.py:181–268`. `web/src/lib/gatewayClient.ts:16–61` показывает browser JSON-RPC plumbing, но не доказывает готовность Kinodel adapter. Native `approval.respond` отвечает на разрешения инструментов, **не** на творческий Approve Story/anchors.

Штатный dashboard chat — xterm/native TUI, не готовый React ProducerChat; на Windows у PTY-пути есть ограничения. Мы не переписываем этот core chat: Kinodel создаёт своё browser-представление native session. `web/AGENTS.md:7–28`.

## Запуск и владение портом
Сначала обнаружить действующего host owner и origin; не считать `9119` неизменным портом. Launcher dashboard/serve attach-first; явный несовместимый host/port отклоняется. `--isolated` создаёт другой режим, а не магически подключает ту же session authority. Gateway listener может получить порт от ОС. `hermes_cli/main_dashboard.py:873–941`; `gateway/run_api.py:138–166,199–204`.

`hermes serve` headless отключает обычную SPA; его запуск не равен запуску Kinodel. Предлагаемый launcher открывает URL bundle **после** проверки backend/auth/capabilities. Новую команду запуска здесь не объявляем существующей. `hermes_cli/subcommands/dashboard.py:15–36`; `hermes_cli/web_server_dashboard.py:118–141`.

Резервные варианты, не выбранные по умолчанию:
- `HERMES_WEB_DIST` позволяет подставить SPA root, но меняет root presentation dashboard и зависит от attach/boot режима.
- Отдельный frontend origin/proxy возможен, но добавляет port/process/auth/WS forwarding. Localhost CORS сам по себе не включает credentialed cookie requests (`hermes_cli/web_server.py:557–570`). Не вводить второй сервер без необходимости.

## Контракт UI ↔ domain
Предлагаемые команды, не существующие endpoints: SaveBrief, ApproveBrief, RequestRework, GenerateCandidate, SelectCandidate, ApproveStage, Stop, Continue. Browser не создаёт Kanban tasks напрямую.

Каждая mutation несёт стабильный command ID, target project/production, ожидаемую версию и payload. Actor берётся из auth; task/run специалиста — из доверенного execution context, не JSON от модели. Повтор command ID с тем же payload возвращает receipt; с другим payload — conflict. Backend возвращает фактический результат или accepted operation, не optimistic approval.

Read model объединяет native task status и доменные материалы по ID **на чтении**. UI получает `allowed_actions` с причинами блокировки и revision/version; сервер повторно валидирует действие, поскольку данные вкладки могли устареть. Клиент хранит viewport, filters, focus и несохранённые формы — не копию производственной БД.

## Приёмка ближайшего browser spike
Пока **не выполнена**: открыть bundle в обычном браузере → штатный вход → авторизованное чтение проекта → canonical Producer session → один текстовый turn → reconnect/replay → clarify/tool approval → domain command с повтором → запрет чужого profile/project → private image и MP4 Range. Отдельно проверить native Windows, public-static/private-media разделение и отсутствие зависимости от Desktop.

Связи: [[kinodel-preproduction/hermes-mechanisms]], [[kinodel-preproduction/frontend-workspace]], [[kinodel-preproduction/kinodel-features]].
