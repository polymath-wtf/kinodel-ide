# Local Cinematic MVP: Build Plan

Обновлено: **21 сентября 2026**. Это единственный список подготовки, реализации и приёмки первого билда. Статусы ниже — фактическая готовность, не обещание работающего приложения.

## Результат для пользователя

Фиксированный последовательный [cinematic](pipelines/cinematic.md): brief → Storytell → HITL → Wardrobe → anchor-gen → HITL → Storyboard → frames-gen → HITL → Filmmaker → video-gen → HITL → Montage → final. Пользователь видит входы/результаты нод, пишет правки непосредственно владельцу, сравнивает v1/v2/v3 и утверждает конкретную версию.

Первый MVP включает видео и сборку финального файла. Текстовый и image-only эксперименты — промежуточные инженерные проверки. Critic, публикация памяти, свободный конструктор, группировка нод, облачные аккаунты/кредиты и творческий монтаж не входят в этот выпуск.

## Repository And Dependencies

Рабочая среда для нового baseline — `.venv313`, создана системным CPython 3.13.15; старая `.venv` с Python 3.12.9 сохранена, но больше не целевая среда. На Windows x64 были проверены установка и `pip check`; прикладной smoke check ещё предстоит добавить вместе с первым runtime-срезом.

| Компонент | Факт на 21 сентября |
|---|---|
| Python / встроенная SQLite | 3.13.15 / 3.50.4 |
| LangGraph / checkpoint core | 1.2.11 / 4.2.0 |
| langchain-core / Pydantic / httpx | 1.6.3 / 2.13.5 / 0.28.1 |
| SQLite saver / aiosqlite | 3.1.1 / 0.22.1 |
| FastAPI / Uvicorn / Starlette | 0.141.1 / 0.53.0 / 1.6.0 |
| Model-provider integrations / hosted profile | Не выбраны и не проверены; не входят в локальный smoke check |
| Зависимости / приложение | [requirements.txt](../requirements.txt) фиксирует прямые зависимости; transitive lock и приложение ещё не созданы |

Полезные локальные references:

- `.venv313` — текущая среда CPython 3.13; обе локальные среды исключены из Git и не являются хранилищем проектов.
- Официальный индекс web-документации и исходники StateGraph, SQLite saver и prebuilt tools находятся в опциональном ignored checkout `.reference/langgraph`.
- [Локальные навыки LangGraph](../skills/LangGraph/): fundamentals, human-in-the-loop, persistence. Примеры не доказывают crash-safety нашей интеграции.

Reference checkout — справочник, не backend Kinodel и не зависимость через editable install. SQLite saver 3.1.1 с checkpoint 4.2.0 прошёл сохранение interrupt, продолжение в другом процессе и чтение результата в третьем, включая изоляцию thread IDs. Реальный Uvicorn HTTP-запрос прошёл через FastAPI/Pydantic; неверный тип, лишнее поле и неизвестное действие отклонены. Это совместимость библиотек, не доказательство Kinodel crash-safety, business approvals или provider integration. Linux и hosted PostgreSQL ещё не проверены. LangGraph не требует полного `langchain` или Deep Agents.

В системе также доступны Node.js 22.17.0 и ffmpeg/ffprobe build N-117940 (2024-11-28); проверен только запуск с выводом версии, не сборка UI или обработка видео. ComfyUI — внешний сервис со своим окружением, его зависимости не переносятся в Python Kinodel.

### Подготовка репозитория

- [x] Зафиксировать проверенные прямые зависимости локального runtime в `requirements.txt`, создать `.venv313` и выполнить smoke check.
- [ ] Добавить transitive lock при оформлении приложения; не ставить dev/test extras всего upstream monorepo.
- [ ] Выбрать и проверить model-provider adapter с реальными моделями. Сборку UI выбрать с первым экраном; готовые static assets отдавать с local origin.
- [ ] Создать только нужные backend-модули и один test command. Игнорировать secrets, `.venv`, generated project data и reference checkout; не удалять существующие материалы пользователя.
- [ ] Выбрать постоянный data root вне `.venv`, SQLite layout и численные timeout/size/attempt limits. Рекомендация: отдельные application/saver DB в одном root, короткие транзакции, проверенные FK/WAL/synchronous/busy настройки.

Повторение проверки на Windows (создание venv нужно только при отсутствии этой среды):

```powershell
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install -r requirements.txt
.\.venv313\Scripts\python.exe -m pip check
```

На Linux создать среду через `python3.13 -m venv .venv313` и использовать `.venv313/bin/python`; проверка там ещё предстоит. `requirements.txt` закрепляет прямые версии, не все транзитивные зависимости. Не обновлять весь стек автоматически и не считать smoke check приёмкой приложения.

## Implementation

<a id="b-реализация-до-передачи-билда-тестировщику"></a>

| Шаг | Минимальная работа | Доказательство |
|---|---|---|
| [ ] 1. Текстовый фундамент | Submitted Brief, Story, refs, direct feedback, operations/reviews/commands; LangGraph + SQLite saver; детерминированная замена модели | Brief → Storytell → HITL; v1→v2 напрямую; restart продолжает тот же запуск |
| [ ] 2. Сохранение и восстановление | Immutable outputs, versioned bindings, durable start/resume/cancel, data lock и replay receipts | Повтор команды не создаёт второй результат; принятый ответ не теряется и не попадает в другой HITL |
| [ ] 3. Живые агенты | Storytell, Wardrobe, Storyboard, Filmmaker; versioned instructions, typed output, выбранный контекст и node-local feedback | Каждый получает нужные данные, сохраняет валидную версию и не переписывает утверждённых предков |
| [ ] 4. Generation tools | `anchor-gen`, `frames-gen`, `video-gen`; saved plan → durable submit → status/reconcile → verified import; один provider adapter | LLM завершён до рендера; нет повторного submit после неизвестного исхода; реальные refs доходят до провайдера |
| [ ] 5. Media HITL и montage | Выбор полного набора; сохранение anchor_frames/story_frames/shot_videos; прямые правки и зависимая перегенерация якорей; ffmpeg assembly | Каждый утверждённый кадр превращён в свой видеошот; финал содержит все утверждённые видео в порядке истории |
| [ ] 6. Node workspace | Фиксированные ноды, status/input/output, версии и чат правок/вопросов; API authorization, polling/reconnect | Полный маршрут без консоли; видна ожидающая работа и причина остановки |
| [ ] 7. Пользовательский запуск | Windows/Linux launchers, isolated install, readiness, проверка существующих данных и bounded shutdown | Чистая установка и повторный запуск без аккаунта/DB-сервера; данные и принятая работа сохранены |

Шаги 1–2 делаются вместе. До первого эксперимента не нужно проектировать весь API, будущие агенты или установщик. Для проверяемого задания использовать два Story shots: три примерных якоря → два кадра → два видео → финал. Числа относятся к fixture, не ограничивают схемы. Изменение тестового маршрута не меняет граф уже сохранённого запуска.

## Provider Setup

<a id="comfyui-transport"></a>

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
| [ ] Resume до/после apply и следующего wait | Уже принятый ответ завершает свой переход, никогда не отвечает следующей ноде |
| [ ] Generation timeout / lost response / restart | Подготовленные inputs/seeds сохранены; неизвестный submit сверяется; job failure даёт понятный retry/cancel, не вечное ожидание |
| [ ] Anchor lineage / references | Новое лицо пересоздаёт sheet и сохраняет неизменную location; смешанные родители отклоняются; ни один required reference не потерян |
| [ ] Every frame → video → montage | Полное совпадение shot keys/order; start image каждого видео — выбранный кадр; финал содержит все видео, корректный формат и нет audio stream |
| [ ] Cancel / duplicate / fast / late result | Отмена запрещает новые creative commits; повтор/поздний результат не оживляет запуск; быстрый результат ждёт своего точного wait |
| [ ] Ownership / storage / import / access | Второй writer не запускается; disk-full/busy/corruption дают отказ без reset; чужие refs/path escape/неверные media/Host/Origin/session отклоняются |
| [ ] Install / shutdown на заявленных ОС | Paths с пробелами/кириллицей, нет Python/network/disk, несовместимая DB: понятный отказ; нет записи после release lock или осиротевшего installer/montage процесса |
| [ ] Пользовательский проход | Идея → правки → утверждение → финал без консоли; после restart доступны те же версии, feedback и изображения/видео даже без провайдера |

Чекпоинт в памяти или один удачный render не заменяет эти проверки. Разработку начинать сейчас; передавать билд пользователю после прохождения относящихся к нему проверок на заявленных ОС.
