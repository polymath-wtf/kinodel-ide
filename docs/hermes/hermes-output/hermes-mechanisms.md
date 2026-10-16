---
title: "Kinodel — конкретные механизмы поверх Hermes"
created: 2026-10-15
updated: 2026-10-16
type: research
tags: [kinodel, preproduction, architecture, backend, workflow]
sources: [kinodel-preproduction/backend-boundaries.md, kinodel-preproduction/pipeline-and-gates.md, ../plugins/plugin_storage.py, ../gateway/session_kanban.py, ../hermes_cli/kanban_db.py, ../hermes_cli/kanban_db_dispatch.py]
confidence: medium
status: proposed-architecture
---

# Конкретные механизмы поверх Hermes

## 1. Доказательства и выбранная поверхность
Исследован checkout `dfa79389773271ee78c41a7af340848948d461ee`, повторная проверка 2026-10-16. **Source inspection + архитектурные предложения**, не runtime-приёмка. Официальные страницы Plugins, Extending the Dashboard и Kanban сверены онлайн. Tasks/profiles/config не менялись, LLM workers, ComfyUI и FFmpeg не запускались.

**Уточнение прежнего прохода:** Kinodel — самостоятельный localhost React/React Flow WebUI. Desktop SDK/composer/iframe не входят в выбранную архитектуру. Browser packaging, auth, chat и port ownership вынесены в [[kinodel-preproduction/localhost-webui]]. Одного существования plugin REST недостаточно, чтобы считать browser bootstrap решённым.

## 2. Минимальные части одного plugin
| Часть | Владеет | Не делает |
|---|---|---|
| Domain | Фиксированные stage definitions, refs, validation, совместимость, selections/approvals | Не знает FastAPI, Kanban SQL и provider SDK |
| Application | Prepare, publish, approve, rework, generate, stop; одна реализация для tools и HTTP | Не запускает свой agent loop |
| Adapters | Native Kanban/session calls, SQLite/files, provider submit/poll/import, montage | Не принимает творческих решений |
| Web | Собственный React UI, REST/read model, native chat WS adapter | Не определяет допуск следующего этапа |

Это модули одного внешнего пакета, не микросервисы. Нужны узкие границы только у реальных внешних зависимостей, не универсальный workflow engine, event bus или repository на каждый тип. Вызовы private Kanban Python API, если публичного пути недостаточно, изолируются в одном version-sensitive adapter. Инсталлятор и runtime остаются Hermes.

## 3. Канонические данные
| Владелец | Данные |
|---|---|
| Native Kanban | Task, dependency, claim, run/attempt, lifecycle, comments/attachments |
| Native sessions | Producer conversation и worker transcripts |
| Kinodel | Project/production, exact prepared inputs, полные revisions, candidates/parents, selection/approval, command receipts, stage→task связь |
| Provider | Внешний job до импорта; provider URL не является архивом original |

`plugin_db('kinodel')` / `plugin_data_dir('kinodel')` дают profile-aware storage; caller управляет transactions (`plugins/plugin_storage.py:27–46`). Domain DB не дублирует tasks/runs/claims: хранит только ссылки. Read model объединяет данные на чтении. `ctx.state.get/set` атомарны по отдельности, но не образуют compare-and-swap между вызовами (`hermes_cli/plugins_state.py:173–195`). Поэтому предлагается одна domain SQLite, не набор изменяемых JSON для approvals.

**Предлагаемый минимум групп записей:** projects/productions; stage bindings/prepared inputs; revisions; candidates; selections/approvals; command operations с ordered steps и receipts. Это логические группы, не окончательная DDL. Полные текстовые JSON можно хранить в SQLite вместе с metadata, чтобы публикация была одной transaction; большие originals — immutable files в plugin-data. Файл сначала temp → проверка/hash → atomic rename, затем DB reference. Orphan после сбоя допустим, committed ссылка на недописанный файл — нет.

## 4. Контракт команды и авторизация
У mutation: command ID, target project/production/stage, expected version, payload. Actor устанавливает server. У worker publish дополнительно доверенные board/task/run/role и digest prepared input. Модель не назначает себе identity. Command ID уникален в owner scope; повтор с тем же payload возвращает receipt, другой payload — conflict. SQLite transaction проверяет expected version и записывает решение вместе с намерением внешнего действия.

Human Approve доступен человеку, не Producer/worker. Backend проверяет полный валидный output или совместимый selection, exact parents и Stop. `completed` модели, native `done`, selection и creative approval различаются. Обычный completion hook не может быть validator: он post-commit, а native dependencies уже могли продвинуться (`hermes_cli/kanban_db.py:2655–2758`).

Bindings разрешаются до dispatch в exact snapshot/digest. Wardrobe/Storyboard/Filmmaker получают полные approved Brief и Story плюс свои inputs. Task body содержит durable input handle и инструкцию чтения, не единственную копию Story. Проверка доставки полного input обязательна; silently summarize нельзя.

## 5. Проход Brief → Story → Wardrobe
1. Producer — штатная session, отображаемая в browser ProducerChat. Domain action сохраняет полный Brief revision. Сам разговор не означает approval.
2. Автор подтверждает точный Brief и согласованный scope работы. Transaction сохраняет approval, production, prepared Storytell input и create-stage intent.
3. Adapter создаёт одну native task с точной ролью/skills/input handle и operation key. Mapping и inputs существуют до допустимого worker admission; при гонке task уже создана, mapping ещё нет — запуск должен ждать, а не угадывать inputs.
4. Storytell читает exact input и публикует полный output через domain handler. Schema/domain validation → revision + request-review intent в одной transaction. Невалидный output не становится revision; сохранённый valid output не регенерируется из-за сбоя native перехода.
5. Adapter переводит текущий run в native review. LLM attempt завершён. Kinodel показывает Story review; следующей task ещё нет.
6. Автор делает Question, RequestRework или Approve. Approve сохраняет exact decision и prepared Wardrobe input; ordered intent завершает Story task и затем создаёт Wardrobe task.
7. Wardrobe публикует AnchorPlan и освобождает LLM. Render operations создают portrait/location, затем sheet от точных родителей; автор выбирает совместимый набор. Аналогично frames/videos. Для media native review может означать render-wait, а domain state показывает его точную причину; такой mapping требует runtime проверки.

## 6. Human hold уже есть, но scope важен
`kanban.review_dispatch: false` исключает review lane из **автоматического** dispatch; default и fallback при ошибке чтения — true (`hermes_cli/kanban_db_dispatch.py:1817–1825,2382–2385`). Это не board/task field и не настройка assignee: действует config исполняющего dispatcher/home. Embedded watcher обходит boards (`gateway/kanban_watchers_common.py:25–46`; `gateway/kanban_watchers_dispatcher.py:216–218`). Отдельная board сама по себе не изолирует toggle. Direct `claim_review_task` не проверяет его (`hermes_cli/kanban_db.py:2225–2250`).

**Условие deployment:** установить, кто реально диспетчеризует Kinodel board, и подтвердить human-only policy без изменения чужих workflows. Если общий dispatcher должен одновременно auto-review чужие boards, нужен поддержанный scoped механизм; не отключать всё молча и не ставить фиктивного reviewer. Существующий test source `tests/hermes_cli/test_kanban_review_lifecycle.py:383–422` проверяет dry-run toggle, здесь тест не запускался.

Проверить также `kanban.auto_decompose: false` в нужном dispatcher scope: triage scanner — отдельная автоматика (`gateway/kanban_watchers_dispatcher.py:247–279`). `auto_subscribe_on_create:false` влияет только на новые автоматические subscriptions. Existing/inherited `notify+wake` не исчезают; явное passive `delivery_mode: notify` предпочтительно. Link наследует подписки (`tools/kanban_tools.py:1220–1251`; `hermes_cli/kanban_db_notify.py:84–98`; `hermes_cli/kanban_db.py:1608`). Goal loops не включаем.

## 7. Переходы и восстановление: не только create
Одна domain transaction не охватывает native Kanban DB. Предлагается небольшой durable command journal с ordered steps и **одним сериализованным исполнителем**; он выполняет намерения, не назначает/claim-ит агентные работы. Immediate execution и recovery используют один путь. Host scheduler может будить восстановление, но его ownership/latency ещё проверяются.

| Переход | Durable запись до внешнего действия | Сверка после сбоя |
|---|---|---|
| Publish → review | Revision, captured task/run, review intent, operation ID | Сначала найти matching native review event/run metadata; если commit был, записать receipt; если ещё тот же eligible run — вызвать review; иначе conflict |
| Approval → complete | Approval, exact selection/version, downstream snapshot, complete step | Проверить native done и provenance completion; несовпадающее ручное закрытие не выдавать за receipt нашей команды |
| Complete → create-next | Completion receipt и create step с deterministic key | Искать matching task, включая archived, сверять role/production/input digest; нет однозначного соответствия — conflict, не blind create |
| Rework → reopen | Exact previous revision, feedback, новый prepared input, captured task/version | Проверить, был ли именно этот reopen и новая попытка; не послать feedback дважды и не открыть работающий чужой run |
| Submit → provider receipt | Render operation, exact payload/seed/refs и разрешение | Если receipt потерян, reconcile provider; невозможность доказать исход → unknown, не новый платный submit |

`request_review` CAS-ит expected run, закрывает claim и пишет run/event, но повтор в review возвращает false. Metadata находится в run, event связывает run ID; false нельзя считать доказательством отсутствия эффекта (`hermes_cli/kanban_db.py:3315–3404`). Approval не завершает родительскую native task автоматически: complete step обязателен прежде, чем полагаться на dependency child. Native parent done **или archived** снимает dependency, но не creative gate.

Native `idempotency_key` проверяется до write transaction и исключает archived; concurrent create может дать дубль (`hermes_cli/kanban_db.py:1244–1271`). Domain UNIQUE без общей блокировки исполнителей этого не исправляет. Нужны serialized reconciliation и crash tests; если доступный adapter не обеспечивает однозначный lookup/receipt — generic atomic create-or-get, не новая task DB. Exactly-once не обещаем. Команда с неустановленным исходом остаётся видимой пользователю.

## 8. Rework и вопрос
Native request-review/reopen позволяют повторную попытку той же task. Повтор одного `(board, task, run_id)` восстанавливает ту же session; новый claim создаёт новый run/session. `tasks.session_id` — originating session, не постоянная worker session (`gateway/session_kanban.py:82–102`; `hermes_cli/kanban_db.py:3620–3653`).

Предлагаемая база: rework сохраняет прошлый полный output, inputs и feedback, затем запускает новую попытку той же task. Это не тождественно пожеланию продолжить ту же session; вопрос H08 остаётся открытым до согласования/проверки resume. Не обходить dispatcher произвольным session-send. Question-only не разрешает revision/render; безопасный адресный read-only turn к idle specialist отдельно не установлен. Producer может объяснить опубликованный результат, но это не ответ от имени специалиста.

## 9. Ограничения workers и Stop — реальные блокеры
Native policy принудительно добавляет `kanban` к toolsets (`gateway/session_kanban.py:50–69`). `kanban_create` и `kanban_link` доступны owning workers для fan-out; own-task guard lifecycle не запрещает их (`tools/kanban_tools.py:1094–1154,1274–1288`). Поэтому только минимального profile/prompt и domain handlers **недостаточно**, чтобы обещать фиксированный маршрут.

Нужна проверенная restriction/admission граница: worker не может создать/link произвольную task, обойти публикацию или запустить render/terminal. Plugin execution middleware может обернуть tool call, но его исключение до next_call ведёт к skip-and-continue (`hermes_cli/middleware.py:143–212`); не выдавать его за fail-closed security boundary без отдельной проверки. Если существующие policy seams недостаточны, требуется узкое generic host capability restriction, не Kinodel-specific orchestrator в core.

Domain Stop сразу запрещает новые domain commands/submits/transitions. Но native ready task/retry уже может пройти claim/spawn: `hermes_cli/kanban_db_dispatch.py:2048–2147,2206–2228`. Глобальная emergency pause проверяется до tick и не останавливает running workers (`gateway/kanban_watchers.py:296–308`), не является production Stop.

**Незакрытый контракт:** production-aware admission/re-admission fence, синхронизированный со Stop, включая ready, retry, review и direct claims. Один дополнительный if без синхронизации оставляет race. До реализации этого seam нельзя обещать «после Stop новый LLM не стартует». Уже admitted worker/job может завершиться; поздний результат сохраняется без смены selection/approval. Состояния stop_requested и фактическая остановка admissions должны быть различимы. Не ослабляем исходное требование молча.

## 10. Media и Montage без ожидающего LLM
Один path для автоматического render и Manual Generate: validate → persist operation → submit → receipt → poll → import original → measured metadata → candidate. Settings/role order/exact refs/workflow digest фиксируются до submit; random seed выбирается один раз. Manual override не переписывает агентный plan; поздний candidate не меняет selection.

`ImageGenProvider`/`VideoGenProvider` и FAL существуют, но не дают готового Kinodel operation journal. ComfyUI script содержит submit/monitor/download, однако не является стабильным library API (`agent/image_gen_provider.py:30–119`; `agent/video_gen_provider.py:42–69,139–156`; `optional-skills/creative/comfyui/scripts/run_workflow.py:565–589`). Нельзя silently clamp duration/size или отбросить ref.

`cron no_agent` действительно выполняет script без AIAgent (`cron/scheduler.py:1522–1548,2269–2271`). Это кандидат для коротких recovery/poll/import шагов, не выбранный без проверки render runtime: default ticker interval 60 секунд, нужны acceptable latency, startup, overlap и owner scope (`cron/scheduler_provider.py:152`; `cron/scheduler.py:569,807`). `ctx.spawn_task` не durable и отменяется при unload. Не держим агентный turn на время GPU job и не строим свой scheduler.

Шесть JSON в `wiki/raw/comfyui-workflow/` повторно распарсены без обращения к ComfyUI. Krea txt2img: prompt 864, seed 856, geometry 814/815, output 865. Qwen 3img: refs 470/496/498 → encoder 459_474; двухref sheet mapping не проверен, не дублировать третий ref молча. MiniMax img2vid: prompt/frame 162, source 160, geometry 152/153, duration 132→131, seed 129, RIFE 158, output 157 с audio от 121. Это structural evidence, не доказательство доступности nodes/models/geometry/duration.

Montage — фиксированная техническая операция: полные approved clips в Story-порядке → согласованная нормализация → немой MP4 → ffprobe → original + recipe. Без творческой LLM и без shell у специалистов. Codec/FPS/tolerance остаются согласуемыми.

## 11. Контекст, scope и инспектор
Project принадлежит owner profile. Worker с другим profile должен получить только свой exact prepared input и право публикации в своё task/run. Request profile scope существует (`hermes_cli/web_server_dashboard.py:815–826`), но это не доказательство cross-profile authorization. Не кэшировать home/DB в module globals. Проверить server-derived identity и привязку session/task/run до первого worker.

Wiki picker возвращает resource ID/type/role, backend читает только разрешённые объекты и сохраняет snapshot text/media с digest. Для неизменяемого input revisionless wiki превращается в snapshot, не «latest path». Text/vision delivery проверяется отдельно; `@file` не browser attachment protocol. Inspector показывает prepared instructions и наблюдаемо loaded skills отдельно, не весь скрытый system prompt.

## Первый срез и граница готовности
Browser bootstrap + Producer → Brief v2 → Storytell → validated Story → human approval → одна Wardrobe task, **без render как prerequisite текстового среза**. До первого ограниченного worker проверить auth/scope, human hold, publication/recovery, capability restriction и Stop admission. Отдельно ранний image→video smoke после разрешения на запуск. Наличие source не закрывает runtime acceptance.

Связи: [[kinodel-preproduction/localhost-webui]], [[kinodel-preproduction/kinodel-features]], [[kinodel-preproduction/decisions-and-questions]], [[kinodel-preproduction/backend-boundaries]].
