# Story Workspace — препродакшн первого frontend-среза

Статус: **апрув пользователя получен 2 октября 2026; Story-срез 6A–6E принят 3 октября после визуального утверждения каркаса 6F**. [Bounded задания сабагентам](story-workspace-tasks.md); фактические статусы — в roadmap.
Порядок работ и чекбоксы остаются в [шаге 6 Local MVP](../roadmap-mvp.md#frontend-story-slice). Здесь — границы, решения и критерии этого среза.

**As-built уточнение 4 октября:** исторический препродакшн ниже сохраняет fixture-first контекст. Live text/Characters подключены; [последние правки пользователя](uiux-audit-2026-10-04.md#8-правки-пользователя-после-ux1ux5) возвращают rail Pipeline/Canvas/Characters, компактное имя проекта и полный breadcrumb. Click ноды — правые Details 380px / Story 520px, double-click — authored scope; node footer-кнопок нет. Right-click везде Back, keyboard Enter/Shift+Enter. Character picker всегда виден; Character info содержит pinned images/Bio/параметры. Гендер — Male/Female, ID не скрыт. Test Start, «Что будет создано», «О версиях» отсутствуют. Shot keys расширенные, секунды при прежнем ms API. Screenshots и technical/browser acceptance пройдены; пользовательское visual approval новой версии не заявлено. Полное cinematic/media исполнение отдельное; Canvas сейчас пустой.

## Где находится билд

Шаги 0–2 закрыты на Windows: локальное хранение, immutable Story, durable start, вопросы/правки, exact approval, retry/cancel и process-death recovery. Это `kinodel.internal-story` с детерминированной заменой модели. Approval завершает этот execution, не запускает Wardrobe. Живой Storytell — следующий backend-шаг 3; первый подключённый UI можно собрать сейчас внутри шага 6.

Самостоятельный HTML/CSS/JS mock сохранён в `web/prototype/`; connected workspace с Vite размещён отдельно в `web/`. После read-only 6C реализован 6D: общий durable start/respond/approve/retry/cancel, receipt reconciliation и reload drafts/UI. Уточнение 3 октября: перед 6E выполнен и визуально утверждён пользователем 6F — полный объявленный cinematic-каркас с неподключёнными этапами; техническая приёмка 6E пройдена. Runnable evidence и ограничения — в `web/README.md`. Состояния и scripted действия прототипа не являются runtime.

Историческая проверка препродакшна 2 октября (до реализации 6A–6F):

- Из корня: `.\.venv313\Scripts\python.exe -B -m unittest tests.test_api -v` — **6 passed, 6.862 s**. Полный process-death suite повторно не запускался; его evidence — в шаге 2 roadmap.
- Из `web/`: `$env:PLAYWRIGHT_MODULE='C:\Users\Seryoger\AppData\Local\Temp\opencode\node_modules\playwright'; node "prototype/prototype-check.cjs"` при unset `CAPTURE_SCREENSHOTS` — **PASS** offline assets, desktop/mobile geometry, navigation, drafts, inspector и workflow mappings. Это проверка mock, не клиента.
- `node --version`, `npm --version` — **22.17.0 / 10.9.2**. `npm view <exact-spec> version engines peerDependencies --json --registry=https://registry.npmjs.org/` подтвердил доступность всех frontend-кандидатов roadmap и соответствие прямых engine/peer ranges. Install, transitive resolution и production build ещё не выполнены.

## Первый наблюдаемый результат

Автор из браузера создаёт **тестовый Story run**, видит сохранённый ввод и Story v1, задаёт вопрос, получает сохранённое объяснение, просит правку, сравнивает v1/v2 и утверждает именно v2. После закрытия браузера или restart backend открывает тот же execution с теми же версиями и решениями. Pipeline и Chat показывают один exact review и используют один командный цикл.

Постоянная подпись: **«Story foundation · тестовая модель»**, включая узкий экран. Это production frontend на реальном durable API, но ещё не живой cinematic Run.

## Экран и визуальный язык

| Поверхность | Первый срез |
|---|---|
| Вход | Компактная форма `input_message` и явные `shot_ids`; project/client identities создаются клиентом. Это internal test input, не полный Brief с subjects/profiles |
| Открыть сохранённый запуск | Короткий список последних созданных internal executions из текущего data root, без галереи проектов |
| Pipeline | Полная объявленная семинодовая cinematic-карта; внутри Storytell — storytell/story-hitl и общий real Story reader/review. Остальные группы — объявленные agent/gen/HITL; без выдуманного tool-loop/trace |
| Chat | Сохранённый ввод, реальные версии/feedback/ответы владельца, одна actionable карточка и адресный composer «Вопрос / Правка» |
| Review | Читаемые hook/story/shots, переключение версий, отдельные Story version и request revision; явное «Утвердить Story v2» |
| Details | Закрытая по умолчанию панель Inputs / Outputs / Config; показываем только существующие frozen inputs, graph identity и refs. Не сочиняем model/profile settings |
| Run controls | Cancel; Retry только для разрешённого blocked work с точной work version |

Берём из текущего mock near-black/graphite, sky selection, violet agents, coral review, amber текущего этапа, синий primary; фон `background v2.png` без второй сетки, непрозрачные карточки, rail и объединённый header/breadcrumb. История в Chat — одна читаемая колонка, inspector не дублирует результат.

Предлагается dark-first с semantic tokens, системным `Segoe UI`/sans-serif с кириллицей, как в текущем `styles.css`. IBM Plex и light/system theme остаются целевыми из webui, но не входят в первую приёмку. Подписи интерфейса — русские; stage IDs и refs остаются техническими идентификаторами.

Wardrobe, Storyboard, Filmmaker, Montage и Final уже доступны для contract inspection в 6F, но помечены `Не подключено`; их исполнение и media/Canvas подключаются по готовности backend. Mock-фотографии, waiting/ready-статусы и provider settings не включаем в production. Карта доступна без test run; старый двухscope cache расширяется defaults без потери черновиков и pending commands. Internal Story approval по-прежнему END, не Wardrobe.

На desktop текущий review доступен через ноду `story-hitl` без обязательного Fit; Fit не сжимает текст до микрошрифта. На <768px стартовый вид — Chat, детали/review как sheet с focus return, touch targets ≥44px. Keyboard использует реальные Flow-ноды/кнопки с offscreen auto-pan; отдельные список этапов и верхний Story shortcut удалены. Правый клик по ноде или пустому canvas возвращает один scope вверх, по dialog/backdrop — закрывает только окно с сохранением scope/черновика; Back возвращает focus к родительскому действию. Polling не меняет viewport, selection или scroll чтения истории; viewport сохраняется на завершении pan/zoom, не на каждом pointer update.

## Минимальный backend seam

Команды `internal-story`, `respond`, `retry`, `cancel` уже реализованы в [backend/api.py](../../backend/api.py). Новые публичные cinematic команды этому срезу не нужны.

Реализованы **два read endpoints** (6A), используемые workspace 6C; окончательные Pydantic DTO — в `backend/api.py`:

| Read | Данные и смысл |
|---|---|
| `GET /api/executions/{id}/projection` | SQL-backed identity/status/outcome, frozen submitted input/graph, work, Story refs/version/current, ordered review history, текущий actionable review, allowed actions и remaining revise/clarify budgets |
| `GET /api/executions?limit=20` | Ограниченный список internal graph: execution/project IDs, preview ввода, status, current Story identity/version; порядок создания, не «последняя активность» |

История связывает request с **base ref**, accepted decision, применённым переходом, work и committed owner result/response. `applied` означает сохранённый маршрут решения, не готовность новой Story. Approved показывается только по committed approval outcome. Null owner response не означает ожидание: ready revision может создавать Story без отдельного объяснения.

Эти данные есть в `executions`, `review_requests`, `execution_work`, `story_operations`, artifacts/bindings: новый scheduler, журнал событий или миграция для runtime Story не требуются. У storage-only старых artifacts точная version может быть неизвестна; не выводим её из позиции в массиве. В БД нет timestamps/project titles — не придумываем их.

Projection не читает все Story-файлы. Выбранный body загружается существующим `GET /api/executions/{id}/stories/{artifact_id}` и валидируется. Ошибка файла остаётся у результата, status/history/Cancel доступны; DB ref сам по себе не доказывает доступность bytes. Approve недоступен, если отображаемый exact subject не удалось прочитать/проверить. Старый execution GET сохраняет совместимость.

Built assets раздаются FastAPI с `http://127.0.0.1:8765`, независимо от cwd; отсутствующая frontend-сборка даёт понятное сообщение, не мешая internal API. Static routing не перехватывает `/api` и `/docs`, не открывает исходники/данные проекта. Сохраняем loopback/Host/Origin/session/CSRF и текущий lifespan/runner.

Первый dev loop — Vite build (при необходимости `vite build --watch`) и тот же backend origin; отдельный HMR/proxy не нужен для приёмки. Прямые запросы со стандартного Vite origin текущий API отклоняет; разрешения не ослабляем ради dev server. [Vite build](https://vite.dev/guide/build) / [backend integration](https://vite.dev/guide/backend-integration).

## Клиент: стек и владельцы

React 19 + TypeScript + **Vite 8.0.10** и Lucide установлены в 6B; React Flow для фиксированной схемы, React Query, typed fetch + Zod подключены в 6C. Exact pins и `package-lock.json` — в `web/`. Tailwind 4 и необходимые source-owned shadcn/React Flow UI primitives добавляются только с потребителем. Vite 8.0.16 — история удалённого эксперимента, не текущий baseline. Browser tooling остаётся внешним и не входит в frontend runtime.

FSD применяется к реальным владельцам, без пустых слоёв:

| Область | Ответственность |
|---|---|
| `app` | Bootstrap/providers/theme |
| `pages/workspace` | Выбранный execution и композиция workspace |
| `widgets` | Shell, Pipeline и Chat; только представление/навигация |
| `features` | Start/reopen, общий Story review/discussion, run controls и command reconciliation |
| `entities/execution` | Валидированные read projections, queries и точные Story refs/bodies |
| `shared` | Низкоуровневый HTTP/session и используемые UI primitives/tokens |

React Flow state не становится server state. Оба вида переиспользуют review UI и mutation handlers. Canvas scope/viewport, выбранная версия и локальный draft принадлежат UI; они не пишутся в graph/artifact.

Standalone HTML/CSS/JS и checker перенесены в `web/prototype/`; согласованное исключение: бинарные mock-фотографии остаются без изменений в `web/assets/` и читаются прототипом по `../assets/`. `web/index.html` — Vite entry, `web/src` — shell, `web/dist` — build output. Mock и его stock assets не импортируются в runtime.

## Командный цикл и recovery

1. Bootstrap `/api/session`; cookie/CSRF обновляются после backend restart. Read/refetch до разблокировки действий; offline freshness не равна execution status.
2. До POST сохранить immutable pending envelope: endpoint, execution/project identity, payload и key. Если browser persistence недоступна, показать причину и не отправлять невосстановимую команду.
3. `respond.expected_revision` — **review.binding_revision**, не review.revision. Request ID/digest и draft фиксируются вместе с subject. Retry использует work ID + expected_version.
4. После lost response/reload повторить только **тот же payload/key**. 202 — accepted; Applying заканчивается по authoritative projection, без optimistic approval/result. Envelope не удаляется при неопределённом ответе.
5. После 409 перечитать projection, оставить draft неприменённым; не переназначать его новому request. Одновременные действия из двух вкладок решает backend OCC; старый экран ничего не утверждает.
6. Poll active/waiting/blocked, refetch на focus/reconnect; terminal прекращает interval. Не скрывать pending reconciliation только из-за terminal status. Browser storage — кеш/черновики; сохранённые execution/version/decisions восстанавливаются из backend списка.

## Приёмка первого среза

| Проверка | Наблюдение |
|---|---|
| Install/build | Exact lock; `npm ci`, `npm run typecheck`, `npm run build`; нет remote font/runtime CDN зависимости |
| HTTP | Same-origin static + session/CSRF, прежние API-тесты и focused проверки projection/list/history/budgets; commands по-прежнему не вызывают граф в handlers |
| Пользовательский путь | Test input → v1 → clarify → новый request на v1 → revise → v2 → exact approve; версии, feedback и ответ доступны после reopen |
| Два представления | Одинаковый subject/доступные действия; отправка в Pipeline сразу видна в Chat; историческая версия не имеет Approve |
| Неопределённый ответ | Потерять HTTP response после принятия start/respond; reload/reconnect не создаёт второй execution/decision/Story |
| Конфликт/лимиты | Stale request из второй вкладки и exhausted budget объяснены; draft сохранён, action не пересылается автоматически |
| Recovery/controls | Restart backend обновляет session; Retry использует тот же source/inputs, Cancel различает cancelling/cancelled; список открывает сохранённый run после очистки browser storage |
| Read failure | Недоступный исторический body не скрывает SQL status/control projection; ошибочный/current unreadable subject нельзя утвердить из UI |
| UX | Keyboard/focus return, 1440×900 и 390×844, Chat без обязательного canvas; возврат scope/viewport, ошибки inline, reduced motion |
| Visual evidence | Desktop screenshot каждой изменённой страницы в новой `test-results/screenshots/<prototype>/vNN-<change>/`, индекс `test-results/README.md`; Playwright output отдельно |

Полный frontend-шаг 6 остаётся открытым до cinematic/media integration и прохода автора; успешный Story-срез не закрывает Windows-пилот.

**Согласовано и принято в 6E:** первый connected Story-сценарий; визуальная основа текущего mock с dark-first русским UI; два минимальных read endpoints и same-origin static serving; размещение production/prototype. Реализация выполнена по bounded заданиям с проверкой каждого handoff; окончательные wire DTO определены в `backend/api.py` и [local startup](../backend/local-startup.md), а не черновыми полями выше.
