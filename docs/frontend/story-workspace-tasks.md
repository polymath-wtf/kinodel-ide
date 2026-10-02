# Story workspace — последовательные задания сабагентам

Апрув пользователя: **2 октября 2026**. Границы — [препродакшн](story-workspace-preproduction.md), статусы и evidence — только [roadmap, шаг 6](../roadmap-mvp.md#frontend-story-slice).

Один `coder` за раз. Primary выдаёт задание, проверяет diff и consequential evidence, закрывает замечания, затем передаёт следующий шаг. Read-only review — отдельное bounded задание; исправления возвращаются тому же coder через `task_id`. Коммиты не входят в задания.

## Общий контракт каждого задания

- Прочитать root/scoped `AGENTS.md`, `SOUL.md`, `docs/README.md`, `docs/backend/architecture.md`, затем указанные ниже контракты. Исследовать source/callers только внутри назначенного поведения.
- Preserve существующие данные и чужие/uncommitted изменения. Не читать `.env`, не вызывать live providers, не менять `.venv313`, graph route, checkpoint/write protocol или migrations без возврата решения primary.
- Править через `apply_patch`; зависимости только exact и в frontend workspace. Не создавать пустые FSD-слои, универсальные registries, второй scheduler или demo runtime в production.
- Final report ≤30 строк: changed files, wire/behavior handoff, exact commands/results, blockers. Не ставить roadmap checkbox самостоятельно.
- Для UI-задания захватить и **прочитать** desktop screenshot каждой изменённой страницы; новый каталог `test-results/screenshots/story-workspace/vNN-<change>/`, имя `screen-state-desktop.png` внутри page-подкаталога; обновить `test-results/README.md`. Playwright output — отдельно.

## 6A · Backend read seam — coder

**Goal:** metadata читаются независимо от Story-файлов; frontend получает exact историю и может найти сохранённый execution.

**Edit scope:** `backend/api.py`, конкретный read module, `backend/review_store.py` только общий policy constant; focused API tests; wire documentation в `docs/backend/local-startup.md`.

**Context/contracts:** existing internal start/respond/retry/cancel и per-artifact Story read. Добавить `GET /api/executions/{id}/projection`, `GET /api/executions?limit=20` (1–100, internal graph only, newest created first). Identity/status/outcome, submitted input/frozen graph, work, refs/version/current, ordered reviews, current review, remaining/allowed actions.

**Invariants:** exact base/result refs; accepted ≠ applied ≠ owner result finished; completed outcome — authority approval; unknown version не выдумывается. Raw damaged graph identity остаётся readable для blocked inspection, не считается validated runtime identity. List не валидирует всю историческую review/body каждого запуска. Existing response shapes/security/command semantics сохраняются; metadata ref не подтверждает bytes.

**Acceptance/verify:** start → v1 → clarify/new request на том же subject → revise/v2 → approve, история после reopen; budgets/duplicates, list bounds/filter/security, damaged graph/review/file reads не дают непредусмотренный 500 и не скрывают здоровые runs. `tests.test_api`, полный `unittest discover -s tests -q`, `git diff --check`.

**Handoff:** финальные Pydantic DTO и HTTP error semantics из source/OpenAPI, а не предложенные поля прежнего документа.

## 6B · Locked frontend + same-origin shell — coder

Shell собран и проверен; формальная отметка шага и evidence принадлежат primary в roadmap. Ниже — исходные границы задания, не список ожидающих реализации пунктов.

**Goal:** браузер открывает настоящий React shell с backend origin; standalone прототип остаётся доступным отдельно.

**Edit scope:** `web/`, `backend/api.py` и минимальный static-serving helper при необходимости, focused static API tests, `.gitignore` только build/browser output, startup/frontend docs и screenshot index. Roadmap primary обновляет сам.

**Context:** `docs/frontend/webui.md`, approved preproduction, исходный mock теперь в `web/prototype/index.html`, `styles.css`, `prototype.js`; final 6A DTO; existing runtime lifespan/security. Node/npm и exact candidates — dependency раздел roadmap.

**Tasks:**

1. Перенести standalone sources/checker в `web/prototype/`, поправить относительные refs/workflows и инструкции; проверить исходный mock. Принятое исключение: бинарные mock assets остаются в `web/assets/`, прототип ссылается на `../assets/`.
2. Создать Vite entry и TypeScript strict client, `package.json` + lock, scripts `typecheck`, `build`, `build:watch`; Vite **8.0.10**, остальные exact candidates roadmap. Фиксировать новые primitives/icons/tooling pins после metadata проверки. Устанавливать только потребляемые пакеты; сохранить generated source/notices.
3. Shell: русский dark-first интерфейс, системный шрифт, локальный фон, project/header/breadcrumb/rail, идентификация тестовой модели, пустое/loading/error состояние. Создавать FSD-владельцев по появлению поведения. Pipeline/Chat не показывают fake live results.
4. Отдавать `web/dist` с `127.0.0.1:8765` независимо от cwd; missing build даёт понятную страницу. Static path traversal/source/data access запрещены; `/api`, `/docs`, unknown API routes не заменяются SPA HTML. Host/Origin/peer checks действуют, session bootstrap остаётся доступен до authenticated reads, CSRF не ослабляется.

**Acceptance:** `npm ci`, `npm run typecheck`, `npm run build` работают; shell/static assets offline, `/api/session` и API доступны. Никаких POST start/review из shell. Responsive/keyboard на 1440×900 и 390×844, screenshot inspected. Backend static tests + existing `tests.test_api`; prototype checker проходит после перемещения. Документировать точные build/run команды.

## 6C · Read-only connected Pipeline / Chat — coder

Реализовано и принято как read-only workspace; результаты проверок — в roadmap. Ниже — границы выполненного задания; активация команд остаётся 6D.

**Goal:** открыть реальный сохранённый execution, читать версии, review и discussion в двух видах без клиентской симуляции.

**Edit scope:** реальные FSD modules под `web/src`, только нужные frontend test/browser files и package scripts, frontend docs/screenshots. Backend read seam read-only; отсутствующий контракт вернуть primary.

**Context:** final `backend/api.py` DTO, `backend/story_reads.py`, `docs/backend/local-startup.md`. Использовать новые list/projection и per-artifact Story GET; полный body-heavy execution GET не нужен для workspace polling.

**Tasks:**

1. Typed fetch/session bootstrap + Zod response validation; общий React Query cache для list/projection/exact artifact body. Graph digest в projection — raw recorded string, не validated Digest. Session renewal после restart; last snapshot и connection freshness отдельно.
2. Список сохранённых executions; выбранный ID в URL, чтобы reopening не зависел только от browser storage. Empty/unknown/invalid response/404/409 отображаются явно.
3. Pipeline: submitted input → раскрываемая Storytell → результат fixture. Один React Flow scope, authored positions, без editing/connections/deletion; explicit Open inside/Back и accessible stage list. Scope/viewport/selection сохраняются при переключении Chat и polling.
4. Общий Story reader с hook/story/shots, version picker и exact ref; historical versions read-only. Config/Inputs/Outputs доступны по запросу, только подтверждённые поля. Body failure не скрывает metadata/navigation.
5. Chat из сохранённых submitted/reviews/result/response; applied-without-result — activity, не fabricated reply. Current review и draft «Вопрос / Правка» адресованы точным request/subject, draft сохраняется неприменённым при смене request.

**Invariants:** status только server-derived; current ≠ approved; output version ≠ request revision. Не рисовать Wardrobe/live media/agent trace. На этом handoff **нет активных мутирующих действий**, пока 6D не добавит durable command cycle.

**Acceptance/verify:** schema checks и browser read flow на реальном fixture, одинаковый subject в обоих видах, unreadable historical body, narrow Chat/focus return/viewport. `npm run typecheck`, `npm run build`, focused browser checks; screenshots Pipeline/Chat. Fixtures создавать existing API через test harness, не публичные кнопки обхода command envelope.

## 6D · Durable commands + активация пользовательского пути — coder

Реализовано и принято; evidence и отметка — в roadmap. Receipt подтверждает доставку/acceptance, projection — дальнейшее выполнение. Финальная сквозная приёмка остаётся 6E.

**Goal:** безопасно включить start/clarify/revise/approve/retry/cancel; lost response/reload/restart не создаёт дублей и не переназначает feedback.

**Edit scope:** `web/src/features` и необходимые callers/shared transport, focused command/browser tests, startup/frontend docs/screenshots. Backend commands immutable; реальный gap вернуть primary, не строить новый receipt engine.

**Context:** final command DTOs `TestStart`, `ResponseCommand`, `RetryCommand`, `ControlCommand` (cancel); accepted receipts and projection. Existing idempotent POST повторяет receipt даже после применённого решения/terminal state.

**Tasks:**

1. Один command flow, общий для Pipeline/Chat: сохранить endpoint + exact payload/key + identity **до POST** в browser storage. Если persistence не работает, отказ до отправки с понятной причиной. Не хранить session/CSRF как durable credentials; не создавать долгоживущую offline queue для будущих review.
2. При lost response/reload повторить тот же envelope/key, включая start. 401 → bootstrap/refetch/reconciliation без нового ключа. 202 → Applying и authoritative read; accepted не равно completed. Не терять pending envelope из-за terminal/no-review snapshot.
3. Для respond `expected_revision=review.binding_revision`; request ID/digest/base immutable. Retry использует work_id/expected_version; разрешённый owner_unavailable recovery, не creative reroll. Cancel различает cancelling/cancelled.
4. 409/422 показывают причину, refetch и сохраняют draft, не повторяют его на новом subject. Cross-view pending guard и multi-tab OCC. При offline/reconnecting/stale snapshot actions disabled; не делать optimistic approval/results.
5. Включить компактный internal test start с явными shot IDs, draft/validation, список/reopen, общий composer и отдельный exact Approve. Body текущего subject должен успешно загружаться/совпадать с ref; historical/unreadable subject без Approve. remaining/allowed из backend определяют доступность review actions.

**Acceptance:** browser path input → v1 → clarify → same Story/new request → revise → v2 → approve; duplicate/lost POST response start/respond + reload; server restart session; conflicting tab/exhausted budget/draft retention; Retry и Cancel; reopen после очистки browser storage. Один meaningful runnable command regression плюс browser scenarios; не зеркалить реализацию десятками suites.

**Verify:** `npm run typecheck`, `npm run build`, command check и focused real-backend browser checks. Screenshots каждой изменённой страницы. Сначала journal/reconciliation и его check, **затем** активация кнопок в том же задании.

## 6E · Приёмка Story UI — general (read-only), fixes → coder

**Goal:** независимо подтвердить весь approved Story-срез; не закрывать полный cinematic шаг 6.

**Scope:** read-only code/contract audit и execution checks; временные runs в отдельном external test data root. Evidence/screenshots допускаются в назначенных test-results местах, migrations/providers/данные пользователя не трогать. Изменения поведения — отдельное bounded исправление coder.

**Verify:** locked `npm ci`, typecheck/build; backend applicable regression once for final code; real HTTP browser flow, lost-response/reload, conflict/budgets, retry/cancel, restart, browser-storage-loss rediscovery, offline assets, malformed response/body failure; Pipeline/Chat identical exact decision, keyboard, 1440×900 и 390×844, scope/viewport/focus, fixture badge. Проверить screenshots визуально, консоль/page errors и static/security boundaries.

**Return:** ≤30 строк, pass/fail по acceptance препродакшна, exact commands/dependency/platform versions, evidence paths, actionable blockers. Primary отмечает 6A–6E только по реальным результатам и формирует следующий handoff для live Storytell/cinematic integration.
