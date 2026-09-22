# Local Cinematic MVP: Build Plan

Обновлено: **22 сентября 2026**. Это единственный список подготовки, реализации и приёмки первого билда. Статусы ниже — фактическая готовность, не обещание работающего приложения.

## Результат для пользователя

Фиксированный последовательный [cinematic](pipelines/cinematic.md): brief → Storytell → HITL → Wardrobe → anchor-gen → HITL → Storyboard → frames-gen → HITL → Filmmaker → video-gen → HITL → Montage → final. Пользователь видит входы/результаты нод, пишет правки непосредственно владельцу, сравнивает v1/v2/v3 и утверждает конкретную версию.

Первый пилот выпускается для **Windows** и включает видео и сборку финального файла. Текстовый и image-only эксперименты — промежуточные инженерные проверки. Linux проверяется отдельным последним шагом после Windows-пилота. Critic, публикация памяти, свободный конструктор, группировка нод, облачные аккаунты/кредиты и творческий монтаж не входят в этот выпуск.

Первый обязательный инженерный milestone внутри этого cinematic MVP — **Restart-safe text foundation**: автор получает Story v1, задаёт вопрос или просит правку, получает Story v2, утверждает точную версию и после перезапуска продолжает тот же execution без повторного результата или применения решения к следующему review. Это не отдельный text-only продукт и не сокращение cinematic scope, а доказательство механизма сохранения, HITL и восстановления до подключения живых моделей и рендера.

## Готовность И Ближайшие Решения

**Шаг 1 (внутренняя Story v1) реализован на Windows; передавать пользовательский билд пока рано.** Есть data-root ownership, SQLite preflight/recovery, foundation DTO, schema v2, immutable Story publication и точное чтение после reopen. Saver/runtime, review, UI и подтверждённые provider profiles ещё не реализованы. Следующий шаг — Story v1 → вопрос/правка → Story v2 → утверждение точной версии → продолжение после перезапуска. Первый deploy здесь означает локальный Windows-пилот, не hosted-сервис.

| Когда | Что закрыть в реализации, не отдельным архитектурным проектом |
|---|---|
| Шаг 0 | Сохранить текущую рабочую копию, назначить `.venv313` единственным dev interpreter, закрепить транзитивные зависимости и воспроизвести установку отдельно от рабочей среды |
| Шаги 1–2 | Явный mapping внутренних graph steps → `stage_id`/operation kind/slot writer; все исходы approve/revise/clarify/non-ready/cancel, новый request после ответа без новой версии результата; стабильные activation refs и recovery по pending writes |
| По мере шагов 1–2 | Добавлять SQL constraints и DTO с первым реальным запросом: сначала Story/ref и test execution, затем `ActivationRef`, review/work/decision/apply. Точные digest encodings и численные caps уже есть; не добавлять неописанный production slot молча |
| До публичного cinematic Run | Сохранить InitialRequest и полный submitted Brief с start identity/receipt; проверить оба image/video profiles. Определить ввод `Brief.subjects`: Storytell запрещено добавлять неописанных участников, а свободная идея сама по себе не создаёт список. Показать состав в том же Brief до Run; автоматическое извлечение не считать уже существующей функцией |
| Шаги 1–2 | Data root, file publication на целевой ОС, application/saver DB settings, local session/Host/Origin/CSRF; команды start/respond/retry/cancel и read projections для того же execution |
| Переход от шага 3 к шагу 4 | После работающих текстовых вызовов и сохранённых планов с промптами Wardrobe настроить существующий ComfyUI и его workflows **до первого реального рендера** через обязательный native REST API. Работа workflow в UI не считается проверкой API-пути |
| До соответствующих живых вызовов | Для Storytell — model ID, инструкции, structured-output repair, timeout и durable attempt budget; media evidence и пригодность Storyboard moment как начала `i2v` проверить при подключении Wardrobe/Storyboard/Filmmaker, до их живого feedback/rendering |
| Настройка ComfyUI, до rendering | Пины реально работающих workflows/profiles, mappings всех reference roles, output schemas/nullability, duration/format tolerance; проверить поддержку формата для последующего silent montage. `ref2vid` не считать доказанным `i2v`, один image input — поддержкой нескольких независимых references |
| До Windows-пилота | Минимальный экран по [WebUI](frontend/webui.md#minimal-workspace), reproducible install/test command, transitive lock и заявленная версия Windows с фактической приёмкой |

Для первого сквозного fixture достаточно новой истории без library chunks: subjects могут иметь `character_ref=null`, явный дополнительный контекст может быть пустым. Встроенные agent resources и upstream artifacts нужно подключить через direct resolver в этом билде. Source/wiki/chunk selectors включаются только с работающим хранением и проверками; неподдержанный selector отклоняется, а не игнорируется. Библиотека не становится скрытой зависимостью первого билда.

Первый клиент — собственный локальный [React Flow workspace](frontend/webui.md#first-ui-slice). Он показывает фиксированный маршрут и управляет им через durable command/read API; редактирование графа и node-packs не входят в MVP. Начать runtime можно с API-проверок, но пользовательский проход требует этого минимального экрана.

## Repository And Dependencies

Единственная рабочая среда — `.venv313`, создана системным CPython 3.13.15 и изолирована (`include-system-site-packages=false`). Старая `.venv` на Python 3.12.9 удалена после проверки потребителей и воспроизводимости нового baseline; она не являлась запасной средой запуска MVP.

| Компонент | Повторно проверенный факт на 22 сентября |
|---|---|
| Python / встроенная SQLite | 3.13.15 / 3.50.4 |
| LangGraph / checkpoint core | 1.2.11 / 4.2.0 |
| langchain-core / Pydantic / httpx | 1.6.3 / 2.13.5 / 0.28.1 |
| SQLite saver / aiosqlite | 3.1.1 / 0.22.1 |
| FastAPI / Uvicorn / Starlette | 0.141.1 / 0.53.0 / 1.6.0 |
| Model-provider integrations / hosted profile | SDK моделей и hosted packages не установлены; живые модели и profiles не проверены |
| Зависимости / приложение | [requirements.txt](../requirements.txt) фиксирует прямые зависимости; [Windows lock](../requirements-win-py313.lock) содержит 46 runtime pins и прошёл чистую установку; backend реализует config, ownership, SQLite preflight/recovery, foundation DTO и внутреннее хранение Story, но ещё не runtime |

Полезные локальные references:

- `.venv313` — единственная dev-среда. IDE, тесты и команды используют её явный interpreter path; активация shell и изменение PowerShell execution policy не нужны. В пользовательской установке launcher создаст собственную `.venv` на Python 3.13; это отдельная release-среда, не dev-папка из checkout.
- Официальный индекс web-документации и исходники StateGraph, SQLite saver и prebuilt tools находятся в опциональном ignored checkout `.reference/langgraph`.
- [Локальные навыки LangGraph](../skills/LangGraph/): fundamentals, human-in-the-loop, persistence. Примеры не доказывают crash-safety нашей интеграции.

Reference checkout — справочник, не backend Kinodel и не зависимость через editable install. SQLite saver 3.1.1 с checkpoint 4.2.0 прошёл сохранение interrupt, продолжение в другом процессе и чтение результата в третьем, включая изоляцию thread IDs. Реальный Uvicorn HTTP-запрос прошёл через FastAPI/Pydantic; неверный тип, лишнее поле и неизвестное действие отклонены. Это совместимость библиотек, не доказательство Kinodel crash-safety, business approvals или provider integration. Linux и hosted PostgreSQL ещё не проверены. LangGraph не требует полного `langchain` или Deep Agents.

Сверка 22 сентября подтвердила версии, успешные imports и простой HTTP GET через FastAPI `TestClient`; загруженные StateGraph/SQLite saver находятся в `.venv313/Lib/site-packages`, не в reference. На шаге 0 добавлены `scripts/test.ps1` и тест конфигурации; сохранённого framework smoke-test script пока нет. Описанный выше межпроцессный interrupt/resume — прежняя проверка, в этом аудите не повторён. В [`.agents/`](../.agents/README.md) написаны четыре MVP-системника и четыре отложенных микро-контекста; runtime/model integration ещё предстоит. Это не прикладная приёмка. `langgraph-cli` не установлен и не требуется.

В системе доступны Node.js **22.17.0**, npm **10.9.2** и ffmpeg/ffprobe **N-117940-gbc991ca048-20241128**; проверен вывод версии, не сборка UI или обработка видео. Node удовлетворяет требованию выбранного Vite `^20.19.0 || >=22.12.0`; обновлять его глобально ради первого среза не требуется. ComfyUI — внешний сервис со своим окружением, его зависимости не переносятся в Python Kinodel.

### Какие библиотеки ставим и когда

| Момент | Закреплённый состав / способ | Зачем и граница |
|---|---|---|
| Шаг 0, backend | Девять точных pins из `requirements.txt`: LangGraph, checkpoint core/SQLite saver, langchain-core, Pydantic, aiosqlite, FastAPI, Uvicorn, httpx | Сохраняем текущий baseline; никаких `--upgrade` или upstream extras |
| Шаги 1–2, хранение и тесты | Уже имеющиеся `aiosqlite`/saver; stdlib `sqlite3`, `unittest`, `tempfile`, `subprocess`, `hashlib`, OS locks | Конкретный SQL для работающего сценария, без ORM/Alembic; миграции при появлении данных, которые нужно сохранять. Текущая команда: `.\.venv313\Scripts\python.exe -m unittest discover -s tests -v`; ноль найденных тестов не считается успехом |
| Шаг 3, модели | Один OpenRouter adapter через уже установленный `httpx.AsyncClient`, Pydantic для ответа | Базовый bounded non-streaming HTTP call; полный `langchain`, Deep Agents, OpenAI SDK и `langchain-openai` не нужны для этого пути. Model IDs/modalities фиксируются после живой проверки, не выбираются моделью/runner на ходу |
| При необходимости локального config-файла | Сначала переменные окружения; если нужен явный ignored config-файл, тогда выбрать способ чтения и проверить его установку | `.env` сам собой не загружается; секреты не включать в fixtures/logs и не перезаписывать заданные environment variables |
| Между текстовыми планами шага 3 и рендером шага 4, ComfyUI | Тот же `httpx`: обязательный native REST API, upload, polling, import | Настраиваем внешний ComfyUI по уже сохранённым промптам и выбранным workflows; не ставим ComfyUI, torch/CUDA, custom nodes или fal SDK в Kinodel. WebSocket client не нужен для polling |
| Шаг 5, медиа | Внешние `ffmpeg` + `ffprobe`, stdlib subprocess | Без `ffmpeg-python`/MoviePy. Проверить decode, размеры/длительность и silent encode на fixture; затем закрепить проверенную сборку, её источник и checksum для каждой ОС |
| Шаг 6, UI runtime | `react@19.3.0`, `react-dom@19.3.0`, `@xyflow/react@12.11.6` | Установка через `npm install --save-exact` в каталоге frontend; в `package.json` точные versions без `^`/`~`. CSS React Flow обязателен; HTTP через native `fetch` |
| Шаг 6, UI build only | `vite@8.0.10`, `@vitejs/plugin-react@6.0.1`, `typescript@5.9.3`, `@types/react@19.3.0`, `@types/react-dom@19.3.0`, `@types/node@22.15.30` | Установка через `npm install --save-dev --save-exact`. Кандидат baseline: существование versions и engine/основные peer ranges проверены в npm registry, install/build ещё нет. Не включать необязательный React Compiler/Babel; сохранить `package-lock.json`, затем `npm ci` и `npm run build` (`tsc` + Vite) |

UI pins — задание на проверяемую установку, не утверждение уже проверенной совместимости. Если конкретный pin не проходит install/typecheck/build, зафиксировать ошибку и изменить только необходимую зависимость с повторной проверкой; не заменять весь список на `latest`. Node/npm нужны разработчику и сборщику UI; пользовательский пакет получает готовые static assets, не запускает Vite server и не требует npm.

Транзитивные пакеты не удалять по названию: `langgraph-prebuilt`/`langgraph-sdk` приходят с LangGraph, `langsmith` — с langchain-core, `sqlite-vec` — с SQLite saver; `httpx2`/`httpcore2` требуются установленному LangSmith и не заменяют прикладной `httpx`. Наличие SDK/vec не включает Agent Server, tracing или RAG. Для локального билда tracing выключен по умолчанию; внешнюю отправку материалов не включать побочным эффектом окружения.

PostgreSQL saver/psycopg, Supabase/GCS SDK, Redis/Celery, vector stores, LangGraph CLI/Agent Server и Deep Agents остаются вне локальной установки. Не устанавливать `fastapi[standard]`, `uvicorn[standard]` или dev/test extras upstream «на всякий случай».

### Шаг 0. Подготовка репозитория и окружения

- [x] Зафиксированы прямые runtime pins и `.venv313`; imports/API sanity и `pip check` проходят. Runtime/restart checks ещё не созданы.
- [x] Сохранено исходное состояние: HEAD `68e9b4901396055f14a8500a76133185f54cc4cc`, только `M docs/roadmap-mvp.md`, без исходных untracked. HEAD ZIP и binary diff сохранены отдельно; авторские изменения сохранены. Commit не выполнялся.
- [x] `.venv313` задана в `.vscode/settings.json` и `scripts/test.ps1`; проверены `sys.executable`, CPython 3.13.15, SQLite 3.50.4 и `pip check`. Рабочая среда не пересоздавалась и не обновлялась. Уже сохранённый IDE interpreter при необходимости выбрать вручную: workspace default не переопределяет пользовательский выбор.
- [x] UTF-8 [requirements-win-py313.lock](../requirements-win-py313.lock): 46 точных runtime pins из `pip freeze`, без editable/local URL. В отдельной venv установка **из lock**, `pip check`, imports и сравнение inventory прошли; Python/pip/ОС записаны ниже.
- [x] Linux-проверка перенесена в последний шаг после Windows-пилота: CPython 3.13, binary wheels, clean install/test и только затем `requirements-linux-py313.lock`. **Сама Linux-приёмка не выполнена и не блокирует Windows-пилот.** Windows snapshot не считается переносимым lock; `requirements.txt` остаётся источником прямых pins.
- [x] Добавлены ignore rules для `.env.*` (кроме `.env.example`), `node_modules`, frontend dist и test outputs. Существующая `.env` не читалась и не изменялась. Data root выбирается вне checkout и venv с override `KINODEL_DATA_ROOT`.
- [x] Первый модуль [backend/config.py](../backend/config.py) и [тест](../tests/test_config.py): абсолютный путь, платформенные defaults, override, запрет checkout/venv/file/UNC, пробелы и кириллица. Модуль ничего не создаёт и не открывает для записи. Единственная команда discovery: `.\.venv313\Scripts\python.exe -m unittest discover -s tests -v`; `scripts/test.ps1` сначала проверяет interpreter, затем вызывает её. Выполнен 1 тест с несколькими subtests; ноль тестов не считается успехом.

#### Evidence шага 0 — 22 сентября 2026

- Windows 11 x64 `10.0.22631`; CPython `3.13.15`, pip `26.2.1`, SQLite `3.50.4`.
- Исходная копия: `%TEMP%\opencode\kinodel-step0-68e9b490-HEAD.zip` и `kinodel-step0-68e9b490-before.patch`; ignored окружения и секреты не включены.
- Чистая venv: `%TEMP%\opencode\kinodel-lock-5f4197f2f0774bf39d8379488682abdd`. Создана через `.\.venv313\Scripts\python.exe -B -I -m venv <clean>`; установка: `<clean>\Scripts\python.exe -I -m pip --isolated --disable-pip-version-check install --no-input -r requirements-win-py313.lock`.
- `pip check` в обеих средах: `No broken requirements found`; нормализованный `pip list --format=json`: 46/46 runtime packages совпадают, pip тоже. `pip freeze` совпадает; imports FastAPI/Pydantic/httpx/StateGraph/AsyncSqliteSaver загружаются из чистой venv.
- Проверка dev: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test.ps1` (policy только дочернего процесса). Базовая команда выше не требует изменения execution policy. Тест прошёл в рабочей и чистой venv; `git diff --check` прошёл. Независимый review выявил ошибочный отказ для Windows extended local path; исправление подтверждено regression subtest, включая запрет extended alias checkout.
- Config — только выбор пути, не storage preflight: writable/local-volume/cloud-sync проверки, lock, DB и immutable publication относятся к шагу 1. Linux defaults проверены подменой окружения в Windows-тесте, не запуском Linux.

#### Шаг 1 — первый срез: владение data root

- [x] `backend/ownership.py`: `own_data_root(Path)` удерживает OS-backed lock на всё время context manager. Постоянный `.kinodel.lock` не перезаписывается и не удаляется; descriptor non-inheritable. Windows — nonblocking byte-zero `msvcrt.locking`, Linux — `flock`.
- [x] Проверены отдельные процессы: второй владелец получает отказ; после обычного выхода и принудительного завершения первого повторное получение работает. Содержимое существующих файлов и identity lock сохраняются; ошибки открытия не допускают вход в защищённый блок.
- [x] Отклоняются directory/hardlink lock и обнаруженные перенаправления. Тест symlink пропущен на этой Windows из-за отсутствия privilege; это не подтверждённая платформенная приёмка symlink.
- [x] Application DB identity/version/preflight и первая header migration реализованы следующим срезом ниже. Saver DB и immutable publication проверяются отдельно; полный шаг 1 ещё не завершён.

Проверка первого среза: `.\.venv313\Scripts\python.exe -m unittest discover -s tests -v` — 9 tests, 8 passed, 1 skipped (Windows symlink privilege). Независимый review: блокирующих замечаний в границах trusted local root нет. Linux branch ещё не запускался; non-inheritable не защищает от POSIX fork-only child, поэтому fork-based workers этим срезом не разрешены. Volume/cloud-sync preflight ещё не реализован. Вызывающий код обязан остановить writers до выхода из context manager.

IDE: после сообщения о невозможности разрешить папку `.venv313` workspace default уточнён до `${workspaceFolder}/.venv313/Scripts/python.exe` для текущего Windows dev profile. Interpreter запускается; если IDE сохранила старый выбор, использовать **Python: Select Interpreter → Enter interpreter path**. Исчезновение уведомления требует проверки в самой IDE.

#### Шаг 1 — второй срез: application SQLite preflight

- [x] `backend/database.py`: `open_database(root)` удерживает data-root lock до закрытия SQLite connection. `application.sqlite3` получает `application_id=0x4B494E4F` (`KINO`) и `user_version=1` одной транзакцией; версия 1 пока не содержит business tables.
- [x] На реальном соединении проверяются `WAL`, `synchronous=FULL`, `foreign_keys=ON`, `busy_timeout=1000 ms`. Незавершённая явная транзакция откатывается при закрытии; используем `BEGIN`/`COMMIT`, автокоммит включён.
- [x] Проверяются integrity, identity, точная version и ожидаемая пустая schema v1. Missing/empty/corrupt/foreign/newer DB и неожиданные tables отклоняются без переинициализации, кроме доказанной незавершённой свежей initialization (третий срез ниже). Database/sidecar hardlinks и обнаруженные перенаправления отклоняются.
- [x] Regression с реальным аварийно оставленным rollback journal: отказ сохраняет байты чужой БД и journal. Первоначальный `mode=ro` preflight заменён проверкой временной копии в третьем срезе: даже read-only connection может создавать WAL/SHM рядом с оригиналом.
- [x] `.\.venv313\Scripts\python.exe -m unittest discover -s tests -v`: 23 tests, 21 passed, 2 skipped (Windows symlink privilege). Проверены reopen, bounded busy, rollback, lifecycle lock/connection и отказ после процесса, оставившего пустой DB-файл. Это не проверка всех crash windows транзакционной инициализации.
- [x] Process-death bootstrap recovery и восстановление поддержанного hot rollback journal реализованы третьим срезом ниже. Неизвестный lock-only root и непроверенные данные по-прежнему не переинициализируются.
- [x] Executable текстовые DTO/refs и canonical encoding реализованы четвёртым срезом ниже. Минимальные application tables/immutable Story publication реализованы пятым срезом; отдельная saver DB ещё не реализована. Linux, volume/cloud-sync preflight и полноценная restart-приёмка не выполнены.

#### Шаг 1 — третий срез: bootstrap и journal recovery

- [x] Постоянные пустые versioned markers `.kinodel-initializing-v1` и `.kinodel-ready-v1` различают зарезервированный fresh root и завершённую initialization. Reservation публикуется до lock-файла; любой процесс, получивший OS lock, может продолжить. Markers проверяются и fsync выполняется до следующих действий. Missing DB в ready root не пересоздаётся.
- [x] Десять subprocess crash windows (`os._exit`): до/после fsync reservation, перед lock, пустая DB, незавершённая transaction, spilled pages, после commit, до/после fsync ready, готовое соединение. После каждого повторное открытие успешно. Детерминированная гонка reservation/lock и два одновременных первых запуска больше не оставляют невосстановимый root.
- [x] Preflight выполняется на временной копии DB и sidecars, включая WAL (SHM перестраивается). SQLite восстанавливает копию, затем проверяются committed identity/version/schema/integrity. Только после успеха открывается оригинал для writable recovery. Грязный заголовок основной DB не считается доказательством принадлежности.
- [x] Для rollback journal проверяются поддержанный формат и checksums synced records: SQLite может молча пропустить повреждённые записи. Повреждённые, усечённые и неподдержанные журналы отклоняются; foreign/newer DB сохраняются вместе с журналами, даже если их незавершённый header выглядит совместимым.
- [x] Отдельный regression: чистая чужая WAL-mode DB отклоняется без создания WAL/SHM. Проверка выполняется на копии даже при отсутствии sidecars, поскольку `mode=ro` оригинала не гарантирует отсутствия этих записей.
- [x] `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test.ps1`: **39 tests, 35 passed, 4 skipped** (Windows symlink privilege). CPython 3.13.15 / SQLite 3.50.4. Проверку реализации и дополнительный regression выполнила основная сессия; независимый subagent review этого среза не состоялся из-за rate limit.

Границы: доказано восстановление после завершения процесса на Windows, **не после отключения питания**: stdlib Windows не предоставляет fsync directory entries. Linux directory fsync реализован, но Linux приёмка ещё не выполнена. Preflight требует временного места под копию DB/sidecars и trusted root, где все writers соблюдают lock. Super-journals (multi-database transactions) и неподдержанные journal forms требуют maintenance. Эти markers не заменяют будущие operation receipts, artifact/file commit protocol или saver recovery.

#### Шаг 1 — четвёртый срез: foundation DTO и canonical JSON

- [x] `backend/domain.py`: строгие frozen Pydantic v2 модели `ArtifactStateRef`, `ArtifactRef`, tagged `ContextSourceRefV1`, `InitialRequestV1`, `BriefV1`, `StoryV1`; `extra=forbid`, повторная validation constructed instances и обязательные nullable keys.
- [x] UUID — canonical lowercase; digest и derived activation/operation identity — `sha256:` + 64 lowercase hex. Internal artifact URI проверяется против exact project/artifact IDs. Context role ограничен `canon/continuity/plan/inspiration/evidence/guidance`.
- [x] Brief проверяет уникальные subjects, positive bounded production settings и aspect ratio через cross multiplication. Story проверяет уникальные shot/subject keys; `validate_story_for_brief` требует подготовленные shot keys в точном порядке, Brief shot count и только объявленные subjects. Права, существование refs и profile capability остаются repository/service checks.
- [x] `canonical_json_v1`: bytes-only parser, strict UTF-8 без BOM, максимум 1 MiB/32 уровня, duplicate-key/float/NaN/surrogate rejection; canonical UTF-8 с sorted keys, compact separators, materialized null/defaults и сохранённым list order/creator text. Artifact digest покрывает только canonical body bytes.
- [x] Release caps первого контракта: generic string 16 Ki chars, creator message/narrative 128 Ki chars, list 256, shots/subjects 128, dimension 16384, shot duration 600000 ms. Output format остаётся bounded string: его поддержку доказывает frozen profile resolver, а не DTO.
- [x] Review исправил activation identity UUID→digest, arbitrary context roles и три лишних ограничения, которых нет в контракте: reduced-only ratio, `mp4` literal и запрет source evidence для defaults/assumptions.
- [x] `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test.ps1`: **48 tests, 44 passed, 4 skipped** (Windows symlink privilege); `git diff --check` прошёл.
- [x] Пятый срез: на временном root сохранены внутренний тестовый ввод и одна валидная Story v1 с точным ref, immutable JSON и минимальными SQL-записями; после повторного открытия читается та же версия. Конфликт файла, отказ до публикации и ошибка DB после публикации оставляют binding невидимым; повтор того же operation возвращает прежний ref. Версия 1 (пустой header) мигрирует транзакционно в версию 2; чужая схема отклоняется. Review/work/saver относятся к шагу 2.

Проверка пятого среза на Windows: `.\.venv313\Scripts\python.exe -m unittest discover -s tests -v` — **51 tests, 47 passed, 4 skipped** (symlink privilege); `git diff --check` прошёл. Fixture повторно открывает DB, сверяет exact ref/body и проверяет tampering, конфликт файла, отказ публикации и rollback после уже опубликованного файла. Это ещё не crash-приёмка checkpoint/graph и не доказательство Windows power-loss durability.

Пустая dev-БД schema v1 не содержала проектов или творческих результатов; она мигрирует в schema v2 без сброса root. Неизвестный/непустой root не удалять и не переинициализировать при startup. Дальнейшие миграции обязаны сохранять уже записанные тестовые Story и будущие пользовательские данные.

Проверка существующей рабочей среды на Windows — без установки:

```powershell
.\.venv313\Scripts\python.exe -c "import sys, sqlite3; print(sys.executable); print(sys.version); print(sqlite3.sqlite_version)"
.\.venv313\Scripts\python.exe -m pip check
```

Только если целевой папки ещё нет: проверить родительский каталог и CPython 3.13.15, затем `py -3.13 -m venv .venv313`; на Linux — `python3.13 -m venv .venv313`. Использовать явный `.venv313/Scripts/python.exe` или `.venv313/bin/python`. Повторные установки идут через `python -m pip install -r <platform-lock>`; `python` здесь означает интерпретатор выбранной venv, не глобальный executable. Проверить exit code каждого шага, остановиться при ошибке. Не изменять среду работающего приложения.

### Reference checkout: можно обновлять отдельно

На 22 сентября `.reference/langgraph` — чистый самостоятельный checkout `main`, remote `https://github.com/langchain-ai/langgraph.git`, HEAD `ed384f3` от 20 сентября. В корневом Git он ignored, не submodule; установленные Python distributions не имеют `direct_url.json`, reference отсутствует в проверенном `sys.path`. Наличие этой папки сейчас не подменяет runtime. Свежесть remote без fetch не установлена.

Для ручного обновления справочника из корня Kinodel:

```powershell
git -C .reference/langgraph status --short --branch
git -C .reference/langgraph rev-parse HEAD
git -C .reference/langgraph pull --ff-only
git -C .reference/langgraph rev-parse HEAD
```

Выполнять pull только после проверки чистой ветки с ожидаемым upstream; при локальных изменениях/расхождении остановиться, не reset/stash автоматически. Записать новый SHA для исследования. Это обновляет исходники справочника, **не pip-пакеты Kinodel**. Не делать editable install из reference, не добавлять его в `PYTHONPATH`, release package или test discovery. Поведение установленного saver проверять по `.venv313` и тестам: свежий `main` может отличаться от наших pins. Автоматический pull при запуске приложения не нужен.

## Implementation

<a id="b-реализация-до-передачи-билда-тестировщику"></a>

| Шаг | Минимальная работа | Доказательство |
|---|---|---|
| [x] 1. Минимальное хранение Story | На изолированном test root: внутренний тестовый ввод, identity execution, Story/ref, immutable JSON и нужные SQL constraints; читать точный результат после reopen. Текущие config/lock/DTO использовать без нового каталога таблиц | Валидная Story v1 доступна после reopen; duplicate/conflict и file→DB сбой не создают видимый полурезультат; неизвестные/непустые данные не сбрасываются |
| [ ] 2. Restart-safe text foundation + command API | Добавить отдельную saver DB и authored LangGraph с детерминированной заменой модели: test start → Storytell → prepare/wait/apply. Добавлять operations/reviews/work/controls, `ActivationRef` и command/read API по ходу revise/clarify/retry/cancel; local session/Host/Origin/CSRF при открытии HTTP | Story v1 → вопрос или правка → тот же subject → Story v2 → approve; restart продолжает тот же execution; повтор команды не создаёт результат и не отвечает следующему HITL |
| [ ] 3. Живые агенты и текстовые планы | Сначала Storytell через один проверенный OpenRouter adapter, затем Wardrobe с сохранёнными промптами для якорей. После настройки ComfyUI добавлять Storyboard/Filmmaker по мере появления утверждённых изображений; system prompts из `.agents/<agent>/system.md`, versioned instructions, typed output, direct context и feedback | Текстовые вызовы дают валидные сохранённые Story и план с промптами; следующие агенты получают нужные изображения/наблюдения и не переписывают утверждённых предков; model IDs и budgets записаны до включения |
| [ ] 4. ComfyUI REST и generation tools | По сохранённым промптам Wardrobe настроить существующий внешний ComfyUI и проверить API-format workflows через **native REST API**. Затем `anchor-gen`, `frames-gen`, `video-gen`: saved plan → durable submit → status/reconcile → verified import; один provider adapter | REST-путь (upload, `POST /prompt`, queue/history, `/view`) реально проходит; LLM завершён до рендера; нет повторного submit после неизвестного исхода; все обязательные refs доходят до провайдера |
| [ ] 5. Media HITL и montage | Выбор полного набора; сохранение anchor_frames/story_frames/shot_videos; прямые правки и зависимая перегенерация якорей; ffmpeg assembly | Каждый утверждённый кадр превращён в свой видеошот; финал содержит все утверждённые видео в порядке истории |
| [ ] 6. Минимальный node workspace | Закреплённый React/Vite/React Flow стек; canvas + node panel: status/input/output, версии и правки/вопросы; typed command/read client, polling/reconnect, готовые static assets с local origin | Полный маршрут без консоли; видна ожидающая работа и причина остановки; stale tab не утверждает новую версию. HTTP authorization уже работает с шага 2 |
| [ ] 7. Windows-пилот | Windows launcher, isolated locked install, readiness, проверка существующих данных и bounded shutdown; release включает backend, schemas/migrations, prompts/resources, profiles и compiled UI | Чистая установка и повторный запуск на Windows без аккаунта/DB-сервера/npm; данные и принятая работа сохранены; Windows-приёмка пройдена |
| [ ] 8. Linux после Windows-пилота | Linux launcher, CPython 3.13/binary wheels, отдельный transitive lock, clean install и Linux-приёмка тех же runtime/storage/HITL/media сценариев | Проверенный Linux-профиль добавлен к заявленным ОС только после собственной приёмки; Windows lock не выдаётся за переносимый |

Шаги 1–2 — один restart-safe вертикальный срез; сохранность не откладывается до подключения живой модели. Первый тестовый ввод имеет собственную минимальную идентичность, не является неполным cinematic Brief и не открывает публичный Run. После первого сохранённого результата проверить сбои на границах файл → DB → checkpoint, в том числе повтор исполнения после commit; не строить заранее универсальный crash-framework. Для обеих SQLite DB проверить FK где применимо, WAL, synchronous и bounded busy на реальных соединениях, включая saver. До первого эксперимента не нужно проектировать весь API, будущие агенты или установщик.

После шага 2 можно начать текстовую часть того же UI, расширяя её по мере появления медиа; отдельный временный frontend не нужен. Шаг 2 и первые текстовые вызовы шага 3 — внутренние проверки на минимальном тестовом вводе. До публичного cinematic Run сохранять InitialRequest и полный Brief с видимыми `subjects`, проверенными image/video profiles и start receipt; это не требуется до первого внутреннего графа. Для сквозного задания: два Story shots → три примерных якоря → два кадра → два видео → финал. Числа относятся к fixture, не ограничивают схемы. Изменение тестового маршрута не меняет граф уже сохранённого запуска.

Когда текстовые LLM-вызовы уже сохраняют Story и Wardrobe plan с промптами, **перед первым anchor-gen** настроить доступный приложению ComfyUI endpoint. Проверить существующие workflows через native REST API и фактическую передачу reference images, затем сохранить проверенные mappings/fixtures как зарегистрированные image/video profiles. До проверки обоих profiles публичный cinematic Run не открывать. Не переписывать рабочие workflows ради Kinodel и не добавлять gateway/webhook, пока native REST API покрывает upload, submit, status/history и import.

## Provider Setup

<a id="comfyui-transport"></a>

- [ ] Перед живым Storytell закрепить OpenRouter model ID, text input и structured output для generate/revise/clarify. Для JSON Schema использовать `response_format` и `provider.require_parameters=true`; проверить ответ Pydantic, обрыв/пустой ответ/отказ/лимит и единый durable repair budget. Image/video capabilities проверять при подключении соответствующих агентов; не выбирать `auto` и не ослаблять обязательные capabilities при fallback.
- [ ] Перед живым media feedback определить evidence: Wardrobe/Storyboard получают реальные изображения; Filmmaker — доступное видео либо явно ограниченные наблюдения/выбранные кадры. Текстовый adapter не должен утверждать, что просмотрел клип. Формат evidence, лимиты и версии проекций закрепить до этого review.
- [ ] Выбрать endpoint без публикации секретов, auth, image/video workflows и модели; проверить доступность с машины приложения.
- [ ] Проверить портрет, sheet с точным портретом, независимую location, кадр с несколькими ролями референсов и `i2v` для каждого кадра. Декларация входов в JSON не доказывает доставку/использование изображений.
- [ ] Зафиксировать request/response/status/output fixtures и mappings; определить reference upload/URL delivery, размер/длительность и silent output policy.
- [ ] Для ComfyUI обязателен native REST API: readiness, upload, `POST /prompt`, queue/history polling и `/view`/import. Начать с исходящего polling; WebSocket/callback не обязателен. Потеря submit response требует correlation/status lookup или явной остановки, не слепого повторного платного вызова.
- [ ] Проверить ffmpeg/ffprobe, процесс исполнения и безопасный импорт финального файла. Внешний ComfyUI не устанавливается и не останавливается приложением автоматически.

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

## Источники проверки стека

Аудит 22 сентября: локальные `importlib.metadata`, `pip check`, imports/TestClient, `pyvenv.cfg`, Git status/ignore/HEAD и versions Node/npm/ffmpeg; npm registry проверен для перечисленных UI pins. Ничего не устанавливалось в рабочие venv, reference не обновлялся, provider generation не запускалась. Новые package pins требуют своего install/smoke gate.

Официальные механизмы: [Python venv](https://docs.python.org/3.13/library/venv.html), [LangGraph checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers), [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs), [Vite requirements](https://vite.dev/guide/), [React Flow setup](https://reactflow.dev/learn), [git pull](https://git-scm.com/docs/git-pull). Они подтверждают API и требования, не заменяют прикладную приёмку Kinodel.
