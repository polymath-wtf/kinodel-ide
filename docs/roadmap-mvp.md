# Local Cinematic MVP: Build Plan

Обновлено: **24 сентября 2026**. Это единственный список подготовки, реализации и приёмки первого билда. Статусы ниже — фактическая готовность, не обещание работающего приложения.

## Результат для пользователя

Фиксированный последовательный [cinematic](pipelines/cinematic.md): brief → Storytell → HITL → Wardrobe → anchor-gen → HITL → Storyboard → frames-gen → HITL → Filmmaker → video-gen → HITL → Montage → final. Пользователь видит входы/результаты нод, пишет правки непосредственно владельцу, сравнивает v1/v2/v3 и утверждает конкретную версию.

Первый пилот выпускается для **Windows** и включает видео и сборку финального файла. Текстовый и image-only эксперименты — промежуточные инженерные проверки. Linux проверяется отдельным последним шагом после Windows-пилота. Critic, публикация памяти, свободный конструктор, группировка нод, облачные аккаунты/кредиты и творческий монтаж не входят в этот выпуск.

Первый обязательный инженерный milestone внутри этого cinematic MVP — **Restart-safe text foundation**: автор получает Story v1, задаёт вопрос или просит правку, получает Story v2, утверждает точную версию и после перезапуска продолжает тот же execution без повторного результата или применения решения к следующему review. Это не отдельный text-only продукт и не сокращение cinematic scope, а доказательство механизма сохранения, HITL и восстановления до подключения живых моделей и рендера.

## Сейчас и следующий результат

**Шаги 0–1 закрыты на Windows; шаг 2 в работе.** Внутренний runner провёл start → Story v1 → revise → v2 → approve через reopen; retry/cancel и остановка ожидающего owner call проверены на реальном saver. Далее — localhost API, затем discussion. HTTP-команды и экран пока отсутствуют. Подробнее — [шаг 2](#step-2). Первый deploy — локальный Windows-пилот, не hosted-сервис.

Единственный порядок работ — чекбоксы ниже. Таблицы зависимостей и приёмки не задают вторую нумерацию этапов; «готово» означает проверку именно Kinodel, не одного только установленного пакета.

## Repository And Dependencies

Единственная рабочая среда — `.venv313`, создана системным CPython 3.13.15 и изолирована (`include-system-site-packages=false`). Старая `.venv` на Python 3.12.9 удалена после проверки потребителей и воспроизводимости нового baseline; она не являлась запасной средой запуска MVP.

| Компонент | Проверенный baseline на Windows, 22 сентября |
|---|---|
| Python / встроенная SQLite | 3.13.15 / 3.50.4 |
| LangGraph / checkpoint core | 1.2.11 / 4.2.0 |
| langchain-core / Pydantic / httpx | 1.6.3 / 2.13.5 / 0.28.1 |
| SQLite saver / aiosqlite | 3.1.1 / 0.22.1 |
| FastAPI / Uvicorn / Starlette | 0.141.1 / 0.53.0 / 1.6.0 |
| Model-provider integrations / hosted profile | SDK моделей и hosted packages не установлены; живые модели и profiles не проверены |
| Зависимости | [requirements.txt](../requirements.txt) — девять прямых pins; [requirements-win-py313.lock](../requirements-win-py313.lock) — 46 runtime pins, воспроизведённых в чистой venv |

**Когда подключаем оставшееся:** на текущем шаге — уже установленные saver/SQLite, Pydantic, FastAPI и stdlib; на шаге 3 — один OpenRouter HTTP adapter на `httpx`, без нового SDK; на шаге 4 — тот же `httpx` для внешнего ComfyUI REST (не устанавливать его Python/GPU-зависимости в Kinodel); на шаге 5 — внешние `ffmpeg`/`ffprobe` через `subprocess`; на шаге 6 — React/Vite/React Flow. Не добавлять ORM, очередь, LangGraph CLI/Agent Server, полный `langchain`, Deep Agents или hosted-зависимости без работающего потребителя. Секреты — через окружение; `.env` автоматически не читается. Tracing выключен по умолчанию.

**UI-кандидат, ещё не установлен/собран:** runtime `react@19.3.0`, `react-dom@19.3.0`, `@xyflow/react@12.11.6`; build `vite@8.0.10`, `@vitejs/plugin-react@6.0.1`, `typescript@5.9.3`, `@types/react@19.3.0`, `@types/react-dom@19.3.0`, `@types/node@22.15.30`. Устанавливать exact pins, сохранить `package-lock.json`, проверить `npm ci` и `npm run build`. Node.js 22.17.0/npm 10.9.2 и ffmpeg/ffprobe N-117940-gbc991ca048-20241128 пока проверены только по версиям; это не проверка сборки/монтажа. Пользовательскому пакету npm не нужен.

`.venv313` — единственная dev-среда; пользовательский launcher позже создаст отдельную release-venv. `.reference/langgraph` — ignored upstream-справочник, не установленный код; [навыки LangGraph](../skills/LangGraph/) тоже не доказательство поведения приложения. Не менять dev-окружение и reference ради очередного среза.

Источники baseline (аудит 22 сентября): локальные imports/metadata, `pip check`, `pyvenv.cfg`, Git и версии Node/npm/ffmpeg; npm registry проверен для UI pins, но install/build ещё нет. Официальные справочники: [Python venv](https://docs.python.org/3.13/library/venv.html), [LangGraph checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers), [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs), [Vite](https://vite.dev/guide/), [React Flow](https://reactflow.dev/learn). Документация подтверждает API, не работу Kinodel.

Проверка среды без установки: `.\.venv313\Scripts\python.exe -m pip check`. Тесты: `.\.venv313\Scripts\python.exe -m unittest discover -s tests -v` (`scripts/test.ps1` вызывает тот же discovery). Новые установки проверять в отдельной среде из platform lock; не обновлять работающую venv и не устанавливать код из `.reference/langgraph`.

## Шаг 0. Подготовка репозитория и окружения

- [x] Сохранена исходная рабочая копия: HEAD `68e9b49` и тогдашний diff — отдельно от репозитория, без секретов и ignored-окружений.
- [x] Закреплены девять прямых pins, `.venv313` на CPython 3.13.15 и workspace interpreter; старая Python 3.12 venv удалена после проверки потребителей.
- [x] Windows lock из 46 транзитивных pins воспроизведён в чистой venv: `pip check`, imports и inventory 46/46 совпали.
- [x] Настроены ignore rules для секретов/результатов сборки; `backend/config.py` выбирает data root вне checkout/venv и проверен тестом. `scripts/test.ps1` запускает тесты через явный интерпретатор.
- [x] Linux вынесен после Windows-пилота: Windows lock не выдаётся за переносимый.

**Evidence 22 сентября:** Windows 11 x64 `10.0.22631`, CPython 3.13.15, pip 26.2.1, SQLite 3.50.4. Чистая установка из lock, `pip check` и совпадение 46/46 пакетов подтверждены; исходная копия HEAD и diff сохранены вне репозитория. Linux не запускался. Межпроцессный smoke-test SQLite saver и HTTP sanity подтвердили совместимость библиотек, **не** восстановление Kinodel; текущие прикладные проверки — в шагах ниже.

## Шаг 1. Сохранение истории — готово на Windows

Все пять срезов завершены; это внутренняя проверка хранения, не пользовательский запуск.

- [x] **Срез 1/5 — владение data root.** OS lock удерживается до закрытия БД; второй процесс не пишет. После выхода или аварийного завершения владельца root открывается вновь; lock-файл и данные сохраняются.
- [x] **Срез 2/5 — application SQLite.** Identity/version, schema/integrity и реальные WAL/FULL/FK/busy settings; чужая, повреждённая или новая БД не переинициализируется. Незавершённая транзакция откатывается.
- [x] **Срез 3/5 — bootstrap и восстановление.** Markers отличают незавершённый первый запуск от готового root; проверены процессные crash windows и гонка первого запуска. Preflight на копии DB/WAL/journal защищает исходные файлы; неподдержанный или повреждённый journal блокирует открытие.
- [x] **Срез 4/5 — контракты данных.** Строгие `InitialRequestV1`, `BriefV1`, `StoryV1` и refs; bounded canonical JSON/digest, точные shot IDs и объявленные subjects. Валидация не означает сохранение полного публичного Brief.
- [x] **Срез 5/5 — immutable Story v1.** Внутренний test execution публикует JSON и binding; после reopen доступен тот же ref/body. Конфликт файла, tampering и ошибка file → DB не создают видимый полурезультат; повтор операции возвращает прежнюю версию. Пустая v1 DB мигрирует без сброса данных.

Проверки по срезам: **9 → 23 → 39 → 48 → 51** тестов в соответствующих запусках; финальный прогон шага 1 — 51 тест, 4 пропуска из-за Windows symlink privilege. Это история контрольных точек; актуальный общий прогон указан в шаге 2.

Граница доказательства: проверен process death на Windows, не отключение питания; symlink-тесты на этой машине пропускаются без соответствующих прав. Linux и cloud-sync/network volumes не приняты. Для preflight нужно временное место под копию SQLite DB/sidecars. Все данные сохранять при следующих миграциях.

<a id="step-2"></a>
## Шаг 2 — история, правка и продолжение после перезапуска

Внутренний тестовый ввод пока не является публичным cinematic Brief. Проверка через API/тестовый клиент: Story v1 → вопрос/правка → Story v2 → утверждение именно её; после перезапуска тот же запуск продолжается без второго результата или ответа следующему review. Экран автора появится в шаге 6.

- [x] **Версии Story.** Story v2 сохраняется с `expected_revision`; прежний immutable ref остаётся доступен, повтор не возвращает устаревший binding в current. Миграции schema v1–v3 сохраняют записанные Story.
- [x] **Подготовка Story operation.** `story_operations` (schema v4) закрепляет точные test inputs до вызова детерминированной замены модели; миграция v3 → v4 сохраняет обе версии Story.
- [x] **Commit и replay.** Результат, текущий binding и следующий activation фиксируются одной транзакцией; повтор после reopen отдаёт прежний ref/переход без повторной публикации. Prepared operation сохраняется при миграции v4 → v5.
- [x] **Review и решение.** `review_requests` (schema v5) фиксирует точный subject/digest/revision и идентичность wait; `execution_work` записывает решение с dedup key и resume intent одной транзакцией. Apply идемпотентен, устаревшее решение отклоняется. Runner привязывает wait к настоящему checkpoint.
- [x] **Отдельный saver.** `checkpoints.sqlite3` открывается под lock и проходит preflight/settings; после подготовленной операции или review пропавшая БД не пересоздаётся. LangGraph interrupt переживает закрытие/reopen; сквозное восстановление проверено ниже.
- [x] **Доказать recovery перед runner.** На установленном `AsyncSqliteSaver` проверить unanswered interrupt, сохранённый resume в pending writes, незавершённый apply и следующий wait. Зафиксировать, когда нужен exact `Command(resume=...)`, а когда `ainvoke(None)`; несовпадение identities блокирует продолжение. Минимальные воспроизводимые проверки перенести в regression tests runner, не оставлять доказательство только во временном отчёте.
  `tests/test_story_recovery.py` и `tests/test_story_runner.py` проверяют exact source checkpoint/task/interrupt, сохранённый `__resume__` до следующего checkpoint, apply до следующего wait, mismatch block и новый wait без повторной доставки старого решения. Это fault-injection/reopen проверки, не процессное отключение питания.
- [x] **Durable internal start.** Одной транзакцией сохранить execution, проверенные test inputs, фиксированную identity/version/digest внутреннего графа и start receipt/work; project + client key дедуплицирует тот же payload и отклоняет другой. Initial state/activation восстанавливаются из durable records. Saver открывается и проверяется под root lock до приёма start: отсутствие checkpoint нового execution нормально, утрата существующего saver не разрешает его пересоздание. Сохранить допустимый bootstrap старых storage-only roots и данные при миграциях; registry/compiler не нужен.
- [x] **Первый сквозной runner: revise/approve.** `backend/story_runner.py` под одним root lock обрабатывает persisted start/resume/reconcile work: start → Story v1 → prepare/wait/apply → правка → v2 → approve. Вызов графа использует `durability="sync"`; runner сверяет frozen graph/start, checkpoint lineage и pending writes, привязывает точный wait только после checkpoint, блокирует несовпадения и не будит unanswered wait. Claimed work остаётся до следующего стабильного wait или terminal outcome; sweep восстанавливает потерянный runnable segment. Approval и terminal outcome коммитятся вместе до `END`, а runner закрывает сегмент после checkpoint. Проверены reopen, старое work при новом wait и fault-injection; процессная приёмка остаётся отдельным пунктом ниже.
- [x] **Retry/cancel и shutdown до открытия HTTP.** Schema v8 хранит dedup control commands и версию work для OCC. Только `owner_unavailable` после timeout/connection error модели разрешает ручной retry того же source/inputs; integrity/lineage/unsupported graph не переочередятся. Cancel атомарно сохраняет control/work и запрещает новые решения/creative commits/approval внутри транзакций. До terminal outcome статус выводится как `cancelling`; runner прерывает и ожидает cleanup активного awaitable owner call, затем фиксирует immutable `cancelled`. `open_story_runtime` закрывает приём команд, ожидает run и закрывает saver/DB до release root lock; тест проверяет reopen после остановки активного owner. Блокирующий синхронный вызов всё ещё требует собственного bounded timeout при подключении модели.
- [ ] **Первый localhost-прототип — API.** Открыть минимальные command/read HTTP для internal test start, respond (`approve/revise`), retry/cancel, версий Story и состояния. Lifespan владеет root/DB/saver/runner; loopback, Host, Origin, session и CSRF действуют с первого запуска. Handlers только сохраняют команды, граф вызывает runner. Дать воспроизводимую команду запуска и локальный URL API-документации; проверить HTTP-клиентом start → revise → approve и чтение после restart. До реализации discussion неподдержанный clarify отклоняется до принятия решения/work. Это промежуточный работающий прототип с заменой модели, не закрытие шага 2; экран автора остаётся в шаге 6.
- [ ] **Расширить работающий путь discussion.** Добавить clarify и non-ready revise (`needs_input`/`out_of_scope`) в тот же owner-operation protocol: точные inputs и ограниченный discussion context до вызова, сохранённый typed ответ вне graph state, replay без повторного owner call. Объяснение открывает новый request/interrupt на прежнем subject без изменения Story/binding; ready revision создаёт новую Story. Лимиты revise/clarify считаются при принятии действия, не растут от duplicate/retry и не сбрасываются новой карточкой; approve/cancel остаются доступны. Добавить HTTP-действия/чтение ответов и проверить clarify → новый review → revise → v2 → approve через runner/API. Сейчас clarify fail-closed до apply, сохранённого ответа владельца ещё нет.
- [ ] **Процессная приёмка.** Добавлять consequential crash checks по мере сборки пути; здесь сверить покрытие и закрыть недостающие окна start/file → DB → checkpoint, interrupt → binding, decision → resume → apply → следующий wait, terminal commit и cancel. После принудительной остановки новый процесс продолжает тот же execution без второй committed версии или ответа следующему review. Только после всех проверок шага 2 закрыть milestone и переходить к живому Storytell.

**Граница реализации:** расширять существующие `execution_work`, `story_operations` и `review_requests`; committed operation уже хранит результат/переход. Не добавлять параллельные очереди, отдельный discussion/revision engine или дублирующие receipts. Один local runner под существующим OS lock; abandoned claims восстанавливаются после reacquire ownership, без leases/heartbeat takeover. Graph выбирает творческий маршрут, runner только доставляет и восстанавливает work. Последовательность выше даёт localhost-путь раньше полного discussion, но не снимает требований restart safety, cancel и exact approval.

Последний общий прогон на Windows: `.\.venv313\Scripts\python.exe -m unittest discover -s tests -q` — **105 тестов, 4 пропуска** (нет Windows symlink privilege). Runner regression использует reopen и fault-injection; process-death/power-loss проверка остаётся открытой.

## Шаги 3–8 — оставшаяся сборка фильма

<a id="remaining-steps"></a>

- [ ] **3. Живой текст.** Один OpenRouter adapter, проверенные model ID/structured output/timeout/attempt budget; сначала Storytell, затем Wardrobe с сохранёнными промптами. Подключить `.agents/<agent>/system.md`, typed output, direct context и feedback. Подтверждение: валидные сохранённые Story/план без переписывания утверждённых предков.
- [ ] **4. Рендер.** Настроить существующий внешний ComfyUI **после** промптов Wardrobe и **до** первого anchor-gen. Проверить native REST upload → `POST /prompt` → queue/history → `/view`/import, фактическую доставку каждого обязательного reference, image/video profiles, output format и silent montage. Затем anchor-gen; после утверждённых изображений подключить Storyboard/frames-gen, затем Filmmaker/video-gen с доступным реальным media evidence. Сохранённый план → durable job → reconcile → verified import; неизвестный submit не повторять вслепую. `ref2vid` не считать доказанным `i2v`.
- [ ] **5. Выбор дублей и монтаж.** Утвердить полный набор anchors/frames/videos, при новом лице обновить зависимый sheet, но сохранить независимую location. Сборка ffmpeg/ffprobe: каждый выбранный кадр → свой видеошот, полный финал в порядке Story без аудио.
- [ ] **6. Минимальный экран.** Локальный [React Flow workspace](frontend/webui.md#first-ui-slice) с фиксированным маршрутом, версиями, входами/результатами, вопросами/правками и статусом после reconnect; static assets с local origin. Проход автора без консоли. Текстовую часть можно начать после шага 2 и расширять по мере рендера.
- [ ] **7. Windows-пилот.** До публичного cinematic Run сохранять InitialRequest + полный Brief с видимыми `subjects` (не выдумывать их из свободной идеи), start receipt и проверенными image/video profiles. Чистая locked install с backend, migrations, agent resources, profiles и собранным UI; launcher проверяет readiness, shutdown завершает writers до освобождения lock; сохранение данных/решений при restart и [приёмка](#acceptance) на Windows. Fixture: два шота → примерные якоря → два кадра → два видео → финал; библиотека chunks не нужна.
- [ ] **8. Linux после пилота.** Отдельный lock, чистая установка и те же runtime/storage/HITL/media проверки; заявлять поддержку Linux только после её приёмки.

Для этого билда: встроенные agent resources и утверждённые upstream artifacts через direct resolver; неподдержанные source/wiki/chunk selectors отклонять, а не молча игнорировать. Critic, поиск, graph editor и hosted profile не блокируют первый фильм.

## Provider Setup

<a id="comfyui-transport"></a>

Настройка выполняется в [шагах 3–5](#remaining-steps), это не параллельный список задач. Перед живым Storytell проверить структурированный ответ и ошибки через Pydantic, фиксированные model ID, timeout/repair budget. Перед media feedback предъявить агенту реальные доступные изображения/видео или честно ограничить наблюдения. Перед рендером закрепить endpoint, auth, workflow/profile versions, mappings reference roles, request/response/status fixtures и проверить portrait → sheet, независимую location, multi-ref frame, i2v для каждого кадра. Внешний ComfyUI работает отдельно; polling достаточно, потерянный ответ требует reconciliation. Перед монтажом проверить ffmpeg/ffprobe и silent output. Контракты и проверочные примеры — [ComfyUI](backend/comfyui.md), [tool](tools/comfyui-tool.md).

## Acceptance

<a id="t-обязательная-техническая-приёмка-до-локального-выпуска"></a>

Для каждой проверки сохранить команду, версии build/dependencies/graph/workflow, ОС и фактический результат. Сейчас эти проверки **не пройдены**. До Windows-пилота выполнять их на Windows; Linux проходит ту же приёмку в последнем шаге, до заявления поддержки Linux.

| Проверка | Обязательное наблюдение |
|---|---|
| [ ] Start / file / DB / checkpoint crash windows | Принятый start восстанавливается; нет видимого полурезультата или второй committed версии; model call до commit может повториться |
| [ ] HITL v1→v2→approve | Сообщение идёт текущему владельцу без Critic; новая версия не наследует approval; дубликат возвращает тот же receipt; старая версия отклоняется |
| [ ] Clarify / non-ready revision | Ответ сохранён; новый actionable request на прежнем subject, прежний interrupt не переоткрыт; output version и счётчики не сбрасываются |
| [ ] Resume до/после apply и следующего wait | Уже принятый ответ завершает свой переход, никогда не отвечает следующей ноде |
| [ ] Exact context / replay | Retry получает прежние inputs/resources/projections; missing/unauthorized/stale/over-budget required context блокирует; данные источника не становятся system instructions |
| [ ] Generation timeout / lost response / restart | Подготовленные inputs/seeds сохранены; неизвестный submit сверяется; job failure даёт понятный retry/cancel, не вечное ожидание |
| [ ] Anchor lineage / references | Новое лицо пересоздаёт sheet и сохраняет неизменную location; смешанные родители отклоняются; ни один required reference не потерян |
| [ ] Every frame → video → montage | Полное совпадение shot keys/order; start image каждого видео — выбранный кадр; финал содержит все видео, корректный формат и нет audio stream |
| [ ] Cancel / duplicate / fast / late result | Отмена запрещает новые creative commits; повтор/поздний результат не оживляет запуск; быстрый результат ждёт своего точного wait |
| [ ] Ownership / storage / import / access | Второй writer не запускается; disk-full/busy/corruption дают отказ без reset; чужие refs/path escape/неверные media/Host/Origin/session отклоняются |
| [ ] Install / shutdown на заявленной ОС | Paths с пробелами/кириллицей, нет Python/network/disk, несовместимая DB: понятный отказ; нет записи после release lock или осиротевшего installer/montage процесса |
| [ ] Пользовательский проход | Идея → правки → утверждение → финал без консоли; после restart доступны те же версии, feedback и изображения/видео даже без провайдера |

Чекпоинт в памяти или один удачный render не заменяет эти проверки. Разработку начинать сейчас; Windows-пилот передавать после Windows-приёмки. Linux не блокирует пилот и не заявляется поддерживаемым до шага 8.
