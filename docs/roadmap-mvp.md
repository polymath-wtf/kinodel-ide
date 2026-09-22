# Local Cinematic MVP: Build Plan

Обновлено: **22 сентября 2026**. Это единственный список подготовки, реализации и приёмки первого билда. Статусы ниже — фактическая готовность, не обещание работающего приложения.

## Результат для пользователя

Фиксированный последовательный [cinematic](pipelines/cinematic.md): brief → Storytell → HITL → Wardrobe → anchor-gen → HITL → Storyboard → frames-gen → HITL → Filmmaker → video-gen → HITL → Montage → final. Пользователь видит входы/результаты нод, пишет правки непосредственно владельцу, сравнивает v1/v2/v3 и утверждает конкретную версию.

Первый MVP включает видео и сборку финального файла. Текстовый и image-only эксперименты — промежуточные инженерные проверки. Critic, публикация памяти, свободный конструктор, группировка нод, облачные аккаунты/кредиты и творческий монтаж не входят в этот выпуск.

## Готовность И Ближайшие Решения

**Можно начинать реализацию; передавать пользовательский билд пока рано.** Ownership, маршрут и правила review определены; сохранение/восстановление пока описаны, не реализованы. Прикладного backend, executable DTO/SQL, UI и подтверждённых provider profiles ещё нет. Первый deploy здесь означает локальный пользовательский билд, не hosted-сервис.

| Когда | Что закрыть в реализации, не отдельным архитектурным проектом |
|---|---|
| Шаг 0 | Сохранить текущую рабочую копию, назначить `.venv313` единственным dev interpreter, закрепить транзитивные зависимости и воспроизвести установку отдельно от рабочей среды |
| Шаги 1–2 | Явный mapping внутренних graph steps → `stage_id`/operation kind/slot writer; все исходы approve/revise/clarify/non-ready/cancel, новый request после ответа без новой версии результата; стабильные activation refs и recovery по pending writes |
| Шаги 1–2 | Executable DTO и SQL constraints: точные digest encodings, `ActivationRef`, decision/apply variants, хранение InitialRequest через start receipt/binding, численные caps; не добавлять неописанный production slot молча |
| Шаг 1, до публичного Run | Определить ввод `Brief.subjects`: Storytell запрещено добавлять неописанных участников, а свободная идея сама по себе не создаёт список. Показать состав в том же Brief до Run; автоматическое извлечение не считать уже существующей функцией |
| Шаги 1–2 | Data root, file publication на целевой ОС, application/saver DB settings, local session/Host/Origin/CSRF; команды start/respond/retry/cancel и read projections для того же execution |
| До живых вызовов | Model IDs/modalities, инструкции, structured-output repair, timeouts и durable attempt budgets; политика передачи изображений/наблюдений видео при feedback. Проверить, что выбранный Storyboard moment пригоден как старт `i2v` для заданного Story action, а не уже показывает его завершение |
| Проверить рано, закрыть до rendering | Пины реально работающих ComfyUI workflows/profiles, mappings всех reference roles, output schemas/nullability, duration/format tolerance; полный путь до silent montage. `ref2vid` не считать доказанным `i2v`, один image input — поддержкой нескольких независимых references |
| До пользовательского выпуска | Минимальный экран по [WebUI](frontend/webui.md#minimal-workspace), reproducible install/test command, transitive lock и заявленные версии Windows/Linux с фактической приёмкой |

Для первого сквозного fixture достаточно новой истории без library chunks: subjects могут иметь `character_ref=null`, явный дополнительный контекст может быть пустым. Встроенные agent resources и upstream artifacts нужно подключить через direct resolver в этом билде. Source/wiki/chunk selectors включаются только с работающим хранением и проверками; неподдержанный selector отклоняется, а не игнорируется. Библиотека не становится скрытой зависимостью первого билда.

Первый клиент — собственный локальный [React Flow workspace](frontend/webui.md#first-ui-slice). Он показывает фиксированный маршрут и управляет им через durable command/read API; редактирование графа и node-packs не входят в MVP. Начать runtime можно с API-проверок, но пользовательский проход требует этого минимального экрана.

## Repository And Dependencies

Рабочая среда — `.venv313`, создана системным CPython 3.13.15. Старая `.venv` использует Python 3.12.9, не содержит FastAPI/Uvicorn/SQLite saver и не является запасной средой запуска MVP. Обе изолированы (`include-system-site-packages=false`) и проходят `pip check` на 22 сентября; это проверка зависимостей каждой среды, не их функциональной равнозначности.

| Компонент | Повторно проверенный факт на 22 сентября |
|---|---|
| Python / встроенная SQLite | 3.13.15 / 3.50.4 |
| LangGraph / checkpoint core | 1.2.11 / 4.2.0 |
| langchain-core / Pydantic / httpx | 1.6.3 / 2.13.5 / 0.28.1 |
| SQLite saver / aiosqlite | 3.1.1 / 0.22.1 |
| FastAPI / Uvicorn / Starlette | 0.141.1 / 0.53.0 / 1.6.0 |
| Model-provider integrations / hosted profile | SDK моделей и hosted packages не установлены; живые модели и profiles не проверены |
| Зависимости / приложение | [requirements.txt](../requirements.txt) фиксирует прямые зависимости; transitive lock и приложение ещё не созданы |

Полезные локальные references:

- `.venv313` — единственная целевая dev-среда. IDE, тесты и команды используют её явный interpreter path; активация shell и изменение PowerShell execution policy не нужны. Две папки допустимы, но поддерживать два baseline не нужно. Старую `.venv` можно удалить отдельным действием после проверки её потребителей и воспроизводимого нового baseline; не переименовывать/переносить готовую venv. В пользовательской установке launcher создаст собственную единственную `.venv` на Python 3.13 — это не старая dev-папка из этого checkout.
- Официальный индекс web-документации и исходники StateGraph, SQLite saver и prebuilt tools находятся в опциональном ignored checkout `.reference/langgraph`.
- [Локальные навыки LangGraph](../skills/LangGraph/): fundamentals, human-in-the-loop, persistence. Примеры не доказывают crash-safety нашей интеграции.

Reference checkout — справочник, не backend Kinodel и не зависимость через editable install. SQLite saver 3.1.1 с checkpoint 4.2.0 прошёл сохранение interrupt, продолжение в другом процессе и чтение результата в третьем, включая изоляцию thread IDs. Реальный Uvicorn HTTP-запрос прошёл через FastAPI/Pydantic; неверный тип, лишнее поле и неизвестное действие отклонены. Это совместимость библиотек, не доказательство Kinodel crash-safety, business approvals или provider integration. Linux и hosted PostgreSQL ещё не проверены. LangGraph не требует полного `langchain` или Deep Agents.

Сверка 22 сентября подтвердила версии, успешные imports и простой HTTP GET через FastAPI `TestClient`; загруженные StateGraph/SQLite saver находятся в `.venv313/Lib/site-packages`, не в reference. `scripts/` пуст, сохранённого smoke-test script нет. Описанный выше межпроцессный interrupt/resume — прежняя проверка, в этом аудите не повторён. В [`.agents/`](../.agents/README.md) написаны четыре MVP-системника и четыре отложенных микро-контекста; runtime/model integration ещё предстоит. Это не прикладная приёмка. `langgraph-cli` не установлен и не требуется.

В системе доступны Node.js **22.17.0**, npm **10.9.2** и ffmpeg/ffprobe **N-117940-gbc991ca048-20241128**; проверен вывод версии, не сборка UI или обработка видео. Node удовлетворяет требованию выбранного Vite `^20.19.0 || >=22.12.0`; обновлять его глобально ради первого среза не требуется. ComfyUI — внешний сервис со своим окружением, его зависимости не переносятся в Python Kinodel.

### Какие библиотеки ставим и когда

| Момент | Закреплённый состав / способ | Зачем и граница |
|---|---|---|
| Шаг 0, backend | Девять точных pins из `requirements.txt`: LangGraph, checkpoint core/SQLite saver, langchain-core, Pydantic, aiosqlite, FastAPI, Uvicorn, httpx | Сохраняем текущий baseline; никаких `--upgrade` или upstream extras |
| Шаги 1–2, хранение и тесты | Уже имеющиеся `aiosqlite`/saver; stdlib `sqlite3`, `unittest`, `tempfile`, `subprocess`, `hashlib`, OS locks | Конкретный SQL и versioned migration scripts, без ORM/Alembic. Один будущий test command: `.\.venv313\Scripts\python.exe -m unittest discover -s tests -v`; ноль найденных тестов не считается успехом |
| Шаг 3, модели | Один OpenRouter adapter через уже установленный `httpx.AsyncClient`, Pydantic для ответа | Базовый bounded non-streaming HTTP call; полный `langchain`, Deep Agents, OpenAI SDK и `langchain-openai` не нужны для этого пути. Model IDs/modalities фиксируются после живой проверки, не выбираются моделью/runner на ходу |
| Шаг 3, локальная конфигурация | Добавить прямой pin `python-dotenv==1.2.3`, обновить runtime lock и проверить чистую установку | Чтение одного явно указанного ignored config-файла без перезаписи уже заданных environment variables. Версия доступна в индексе, ещё не установлена/проверена. До этого `.env` сам собой не загружается; секреты не включать в fixtures/logs |
| Шаг 4, ComfyUI | Тот же `httpx`: native HTTP, upload, polling, import | Не ставить ComfyUI, torch/CUDA, custom nodes или fal SDK в Kinodel. WebSocket client не нужен для polling |
| Шаг 5, медиа | Внешние `ffmpeg` + `ffprobe`, stdlib subprocess | Без `ffmpeg-python`/MoviePy. Проверить decode, размеры/длительность и silent encode на fixture; затем закрепить проверенную сборку, её источник и checksum для каждой ОС |
| Шаг 6, UI runtime | `react@19.3.0`, `react-dom@19.3.0`, `@xyflow/react@12.11.6` | Установка через `npm install --save-exact` в каталоге frontend; в `package.json` точные versions без `^`/`~`. CSS React Flow обязателен; HTTP через native `fetch` |
| Шаг 6, UI build only | `vite@8.0.10`, `@vitejs/plugin-react@6.0.1`, `typescript@5.9.3`, `@types/react@19.3.0`, `@types/react-dom@19.3.0`, `@types/node@22.15.30` | Установка через `npm install --save-dev --save-exact`. Кандидат baseline: существование versions и engine/основные peer ranges проверены в npm registry, install/build ещё нет. Не включать необязательный React Compiler/Babel; сохранить `package-lock.json`, затем `npm ci` и `npm run build` (`tsc` + Vite) |

UI pins — задание на проверяемую установку, не утверждение уже проверенной совместимости. Если конкретный pin не проходит install/typecheck/build, зафиксировать ошибку и изменить только необходимую зависимость с повторной проверкой; не заменять весь список на `latest`. Node/npm нужны разработчику и сборщику UI; пользовательский пакет получает готовые static assets, не запускает Vite server и не требует npm.

Транзитивные пакеты не удалять по названию: `langgraph-prebuilt`/`langgraph-sdk` приходят с LangGraph, `langsmith` — с langchain-core, `sqlite-vec` — с SQLite saver; `httpx2`/`httpcore2` требуются установленному LangSmith и не заменяют прикладной `httpx`. Наличие SDK/vec не включает Agent Server, tracing или RAG. Для локального билда tracing выключен по умолчанию; внешнюю отправку материалов не включать побочным эффектом окружения.

PostgreSQL saver/psycopg, Supabase/GCS SDK, Redis/Celery, vector stores, LangGraph CLI/Agent Server и Deep Agents остаются вне локальной установки. Не устанавливать `fastapi[standard]`, `uvicorn[standard]` или dev/test extras upstream «на всякий случай».

### Шаг 0. Подготовка репозитория и окружения

- [x] Зафиксированы прямые runtime pins и `.venv313`; imports/API sanity и `pip check` проходят. Прикладные/restart checks ещё не созданы.
- [ ] Зафиксировать исходное состояние `git status`/diff и сохранить текущую авторскую работу перед реализацией. В аудите есть многочисленные изменённые/удалённые docs и untracked `.agents/`; это не мусор. Commit — только по отдельной команде владельца.
- [ ] Выбрать `.venv313` в IDE/скриптах; проверить `sys.executable`, Python/SQLite и `pip check`. Рабочую среду не пересоздавать и не обновлять при этом.
- [ ] Снять полный version snapshot текущей `.venv313` через `python -m pip freeze`, проверить отсутствие editable/local URL и сохранить UTF-8 `requirements-win-py313.lock`. В отдельной временной venv установить **из lock**, выполнить `pip check`, imports и сравнить package inventory. `pip freeze` сам по себе не доказывает воспроизводимость; записать также Python/pip/ОС. Lock не генерировать из старой `.venv` или ComfyUI.
- [ ] Запланировать отдельную Linux-проверку CPython 3.13, binary wheels и зависимостей перед шагом 7; закрепить `requirements-linux-py313.lock` после проверки. Первый dev-срез можно делать на Windows, Linux не блокирует первый код. Не считать Windows snapshot переносимым lock для любой ОС. Launchers используют соответствующий release lock; `requirements.txt` остаётся источником прямых pins.
- [ ] До появления генерируемых файлов добавить точечные ignore rules для local config variants, `node_modules`, UI dist и test outputs. `.env`, `.venv*` и `.reference` уже ignored и не tracked; секреты из существующей `.env` не переписывать. Data root — вне checkout и venv, например `%LOCALAPPDATA%\Kinodel` / `${XDG_DATA_HOME:-$HOME/.local/share}/kinodel`, с явным override на другой локальный несинхронизируемый путь.
- [ ] Создать первый работающий backend-модуль вместе с тестом, без пустого дерева будущих компонентов. Сохранить одну команду тестов и проверку используемого interpreter; дальнейшие срезы проходят её перед переходом дальше.

Проверка существующей рабочей среды на Windows — без установки:

```powershell
.\.venv313\Scripts\python.exe -c "import sys, sqlite3; print(sys.executable); print(sys.version); print(sqlite3.sqlite_version)"
.\.venv313\Scripts\python.exe -m pip check
```

Только если целевой папки ещё нет: проверить родительский каталог и CPython 3.13.15, затем `py -3.13 -m venv .venv313`; на Linux — `python3.13 -m venv .venv313`. Использовать явный `.venv313/Scripts/python.exe` или `.venv313/bin/python`. До появления lock baseline ставится через `python -m pip install -r requirements.txt`; после шага 0 повторные установки идут через `python -m pip install -r <platform-lock>`. Здесь `python` означает именно интерпретатор выбранной venv, не глобальный executable. Проверить exit code каждого шага, остановиться при ошибке. Не изменять среду работающего приложения.

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
| [ ] 1. Хранение и текстовые контракты | Минимальные DTO/SQL для input/story/refs, operations/reviews/work/controls; canonical encoding, InitialRequest identity, data lock, immutable publication, отдельные application/saver DB и preflight | На временном root проходят validation, duplicate/conflict и file→DB crash checks; существующие/повреждённые данные не переинициализируются |
| [ ] 2. Текстовый runtime + command API | Authored LangGraph с детерминированной заменой модели; start → Storytell → prepare/wait/apply; прямые revise/clarify, retry/cancel, recovery classifier и read projections; local session/Host/Origin/CSRF | v1→вопрос→тот же subject→v2→approve; restart продолжает тот же запуск; повтор команды не создаёт результат и не отвечает следующему HITL |
| [ ] 3. Живые агенты | Сначала Storytell через один проверенный OpenRouter adapter, затем Wardrobe/Storyboard/Filmmaker с точными media fixtures; system prompts из `.agents/<agent>/system.md`, versioned instructions, typed output, direct context и feedback | Каждый получает нужные текст/изображения/наблюдения, сохраняет валидную версию и не переписывает утверждённых предков; model IDs и budgets записаны до включения |
| [ ] 4. Generation tools | `anchor-gen`, `frames-gen`, `video-gen`; saved plan → durable submit → status/reconcile → verified import; один provider adapter | LLM завершён до рендера; нет повторного submit после неизвестного исхода; реальные refs доходят до провайдера |
| [ ] 5. Media HITL и montage | Выбор полного набора; сохранение anchor_frames/story_frames/shot_videos; прямые правки и зависимая перегенерация якорей; ffmpeg assembly | Каждый утверждённый кадр превращён в свой видеошот; финал содержит все утверждённые видео в порядке истории |
| [ ] 6. Минимальный node workspace | Закреплённый React/Vite/React Flow стек; canvas + node panel: status/input/output, версии и правки/вопросы; typed command/read client, polling/reconnect, готовые static assets с local origin | Полный маршрут без консоли; видна ожидающая работа и причина остановки; stale tab не утверждает новую версию. HTTP authorization уже работает с шага 2 |
| [ ] 7. Пользовательский запуск | Windows/Linux launchers, isolated locked install, readiness, проверка существующих данных и bounded shutdown; release включает backend, schemas/migrations, prompts/resources, profiles и compiled UI | Чистая установка и повторный запуск без аккаунта/DB-сервера/npm; данные и принятая работа сохранены; каждый заявленный OS profile прошёл приёмку |

Шаги 1–2 — один restart-safe вертикальный срез; сохранность не откладывается до подключения живой модели. Для обеих SQLite DB проверить FK где применимо, WAL, synchronous и bounded busy на реальных соединениях, включая saver; численные limits зафиксировать в release policy до приёма входов. До первого эксперимента не нужно проектировать весь API, будущие агенты или установщик.

После шага 2 можно начать текстовую часть того же UI, расширяя её по мере появления медиа; отдельный временный frontend не нужен. Проверку возможностей ComfyUI начать рано на существующих workflows, не ждать завершения всех четырёх агентов. Для сквозного задания: два Story shots → три примерных якоря → два кадра → два видео → финал. Числа относятся к fixture, не ограничивают схемы. Изменение тестового маршрута не меняет граф уже сохранённого запуска.

## Provider Setup

<a id="comfyui-transport"></a>

- [ ] До шага 3 закрепить OpenRouter model IDs, поддерживаемые text/image/video inputs и structured output для каждого режима generate/revise/clarify. Для JSON Schema использовать `response_format` и `provider.require_parameters=true`; проверить ответ Pydantic, обрыв/пустой ответ/отказ/лимит и единый durable repair budget. Не выбирать `auto` и не ослаблять обязательные capabilities при fallback.
- [ ] Определить evidence для media feedback: Wardrobe/Storyboard получают реальные изображения; Filmmaker — доступное видео либо явно ограниченные наблюдения/выбранные кадры. Текстовый adapter не должен утверждать, что просмотрел клип. Формат evidence, лимиты и версии проекций закрепить до живого review.
- [ ] Выбрать endpoint без публикации секретов, auth, image/video workflows и модели; проверить доступность с машины приложения.
- [ ] Проверить портрет, sheet с точным портретом, независимую location, кадр с несколькими ролями референсов и `i2v` для каждого кадра. Декларация входов в JSON не доказывает доставку/использование изображений.
- [ ] Зафиксировать request/response/status/output fixtures и mappings; определить reference upload/URL delivery, размер/длительность и silent output policy.
- [ ] Начать с исходящего polling. Callback не обязателен; потеря submit response требует correlation/status lookup или явной остановки, не слепого повторного платного вызова.
- [ ] Проверить ffmpeg/ffprobe, процесс исполнения и безопасный импорт финального файла. Внешний ComfyUI не устанавливается и не останавливается приложением автоматически.

## Acceptance

<a id="t-обязательная-техническая-приёмка-до-локального-выпуска"></a>

Для каждой проверки сохранить команду, версии build/dependencies/graph/workflow, ОС и фактический результат. Сейчас эти проверки **не пройдены**.

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
| [ ] Install / shutdown на заявленных ОС | Paths с пробелами/кириллицей, нет Python/network/disk, несовместимая DB: понятный отказ; нет записи после release lock или осиротевшего installer/montage процесса |
| [ ] Пользовательский проход | Идея → правки → утверждение → финал без консоли; после restart доступны те же версии, feedback и изображения/видео даже без провайдера |

Чекпоинт в памяти или один удачный render не заменяет эти проверки. Разработку начинать сейчас; передавать билд пользователю после прохождения относящихся к нему проверок на заявленных ОС.

## Источники проверки стека

Аудит 22 сентября: локальные `importlib.metadata`, `pip check`, imports/TestClient, `pyvenv.cfg`, Git status/ignore/HEAD и versions Node/npm/ffmpeg; npm registry проверен для перечисленных UI pins, pip index — для dotenv. Ничего не устанавливалось в рабочие venv, reference не обновлялся, provider generation не запускалась. Новые package pins требуют своего install/smoke gate.

Официальные механизмы: [Python venv](https://docs.python.org/3.13/library/venv.html), [LangGraph checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers), [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs), [Vite requirements](https://vite.dev/guide/), [React Flow setup](https://reactflow.dev/learn), [git pull](https://git-scm.com/docs/git-pull). Они подтверждают API и требования, не заменяют прикладную приёмку Kinodel.
