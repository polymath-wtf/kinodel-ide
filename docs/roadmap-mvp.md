# Local Cinematic MVP: Build Plan

Обновлено: **7 октября 2026**.

- Шаг 3 закрыт: Storytell и Wardrobe W1–W7 приняты, включая live-приёмку W6 и UI-приёмку W7 с mocked HTTP; сохранённый план и полные image prompts доступны до рендера.
- [Wardrobe W8 / batch_prompt V2](#wardrobe-batch-output) реализован в pure/adapter, storage, runtime/API и frontend; финальная приёмка pending. Остались полный discovery и live V2 provider/offline acceptance. [Storyboard batch plan](#storyboard-batch-backend) ещё pending; историческая V1-приёмка шага 3 не подтверждает V2.
- ComfyUI шаги 1–3 реализованы: preflight, image preparation и production settings/draft diagnostics. Cinematic Run/render/media ещё не подключены.

Здесь ведём общий порядок сборки и задачи агентов: LLM, текстовые входы/результаты, версии, review, восстановление и подключение готового агента к существующему UI в его milestone. Подключение ComfyUI к сохранённым планам и render/media-задачи ведутся в [roadmap-comfyui.md](roadmap-comfyui.md). Статусы ниже — фактическая готовность, не обещание работающего приложения.

[Результаты проверок](../test-results/README.md).

## Результат для пользователя

Целевой последовательный [cinematic](pipelines/cinematic.md): brief → Storytell → HITL → Wardrobe → Batch generation (Anchors) → HITL → Storyboard → Batch generation (Storyboard) → HITL → Filmmaker → video-gen → HITL → Montage → final. Текущий authored UI-каркас уже именует будущие image-tools `anchor-batch`/`frames-batch`, но они не подключены; [batch runtime](tools/batch-generation.md) ещё pending. Исторический `cinematic.v1.json` и frozen execution identities не переписываются. Пользователь видит входы/результаты нод, пишет правки непосредственно владельцу, сравнивает v1/v2/v3 и утверждает конкретную версию.

Первый пилот выпускается для **Windows** и включает видео и сборку финального файла. Текстовый и image-only эксперименты — промежуточные инженерные проверки. Linux проверяется отдельным последним шагом после Windows-пилота. Critic, публикация памяти, свободный конструктор, произвольная исполняемая группировка нод, облачные аккаунты/кредиты и творческий монтаж не входят в этот выпуск. Фиксированные раскрываемые UI-матрёшки и виды Pipeline/Chat не меняют маршрут исполнения.

Первый обязательный инженерный milestone внутри этого cinematic MVP — **Restart-safe text foundation**: автор получает Story v1, задаёт вопрос или просит правку, получает Story v2, утверждает точную версию и после перезапуска продолжает тот же execution без повторного результата или применения решения к следующему review. Это не отдельный text-only продукт и не сокращение cinematic scope, а доказательство механизма сохранения, HITL и восстановления до подключения живых моделей и рендера.

## Сейчас и следующий результат

**Шаги 0–3 закрыты на Windows по исходной W1–W7 V1-приёмке; W8 реализован, но ещё не принят полностью.** Одна обычная «Начать историю» теперь создаёт `kinodel.story-wardrobe` v2 через `/api/executions/story-wardrobe/v2`: exact Story approval → Wardrobe → сохранённый `VisualAnchorPlanV2.batch_prompt`, без публикации библиотеки или рендера. Исторические internal/live Story routes и их approve→END не изменены. Старые Wardrobe v1 runs/configs сохранены, но изолированы и неподдержаны; unversioned Start возвращает 410, без conversion/reset. Live mode использует настроенный OpenRouter; V2 проверен с mocked HTTP, не paid calls. Ранее запущенный пользовательский backend ожидает перезапуска пользователем; миграция/инвентаризация его root этой приёмкой не подтверждены. ComfyUI подготовлен read-only; cinematic render/media ещё не подключены.

**Story UI 6A–6E и исторический Wardrobe UI W7 приняты; cinematic-каркас 6F визуально утверждён.** В существующем workspace W8 frontend показывает exact saved V2 plan, полные копируемые prompts, use_case/mode и обе sheet dependencies в Pipeline/Chat; browser checks и desktop evidence готовы. Следующий результат — финальная [приёмка W8](#wardrobe-batch-output), затем [передача exact saved V2 plan в ComfyUI](roadmap-comfyui.md#wardrobe-comfyui). Первые изображения, anchor review, кадры/видеошоты и монтаж ещё не подключены.

**Порядок ближайших работ: W8 final acceptance → ComfyUI saved-plan handoff (V2-only) → один portrait job → N batch/review → оставшиеся image/video/media этапы → montage и приёмка выпуска.** Для W8 остались две задачи: разобраться с незавершённым full discovery и обновить исторический live harness для V2/provider acceptance с offline reopen. Перезапуск пользовательского backend — отдельный существующий activation gate. Read-only ComfyUI preparation разрешена заранее, но первый live render потребляет только сохранённый validated Wardrobe V2 после W8 acceptance, без повторного Wardrobe call. Шаг 6 сохраняет cinematic/media integration и полный проход автора; первый deploy — локальный Windows-пилот.

## Repository And Dependencies

Единственная dev-среда — изолированная `.venv313` на CPython 3.13.15. Backend pins: [requirements.txt](../requirements.txt) и воспроизводимый Windows [lock](../requirements-win-py313.lock); frontend pins — `web/package-lock.json`. Пользовательский launcher создаст отдельную release-venv; Windows lock не считается переносимым на Linux.

**Когда подключаем оставшееся:** на текущем шаге — уже установленные saver/SQLite, Pydantic, FastAPI и stdlib; на шаге 3 — один OpenRouter HTTP adapter на `httpx`, без нового SDK; на шаге 4 — тот же `httpx` для внешнего ComfyUI REST (не устанавливать его Python/GPU-зависимости в Kinodel); на шаге 5 — внешние `ffmpeg`/`ffprobe` через `subprocess`; на шаге 6 — React/Vite/React Flow. Не добавлять ORM, очередь, LangGraph CLI/Agent Server, полный `langchain`, Deep Agents или hosted-зависимости без работающего потребителя. Секреты — через окружение; `.env` автоматически не читается. Tracing выключен по умолчанию.

**Frontend:** React/TypeScript/Vite, Lucide, React Flow, Query и Zod установлены и используются. Tailwind/shadcn и следующие слои добавлять только с потребителем. Node/npm нужны для сборки и checks, не пользовательскому пакету; ffmpeg/ffprobe доступны, монтаж ещё не принят. Выбор Vite и границы template reuse — в [Web UI](frontend/webui.md#1-стек-и-проверка-react-flow-ui). Известные Vite dev-server advisory и предупреждение о размере bundle остаются ограничениями baseline; production UI раздаётся FastAPI.

`.reference/langgraph` и [навыки LangGraph](../skills/LangGraph/) — справочные материалы, не установленный код и не доказательство поведения приложения. Не менять dev-окружение и reference ради очередного среза.

Проверка среды без установки: `.\.venv313\Scripts\python.exe -m pip check`. Тесты: `.\.venv313\Scripts\python.exe -m unittest discover -s tests -v` (`scripts/test.ps1` вызывает тот же discovery). Новые установки проверять в отдельной среде из platform lock; не обновлять работающую venv и не устанавливать код из `.reference/langgraph`.

## Шаг 0. Подготовка репозитория и окружения

- [x] Исходная рабочая копия сохранена вне репозитория, без секретов и ignored-окружений.
- [x] Закреплены pins, `.venv313` и workspace interpreter; старая Python 3.12 venv удалена.
- [x] Windows lock воспроизведён в чистой venv.
- [x] Настроены ignore rules для секретов/результатов сборки и локальных данных; `backend/config.py` выбирает `<installation>/stuff` независимо от cwd, project JSON/медиа лежат в `stuff/projects/<project_id>`, БД — в корне `stuff`. Override для изолированных проверок и защита venv/source paths сохранены. `scripts/test.ps1` запускает тесты через явный интерпретатор.
- [x] Linux вынесен после Windows-пилота: Windows lock не выдаётся за переносимый.

## Шаг 1. Сохранение истории — готово на Windows

Все пять срезов завершены; это внутренняя проверка хранения, не пользовательский запуск.

- [x] **Срез 1/5 — владение data root.** OS lock удерживается до закрытия БД; второй процесс не пишет. После выхода или аварийного завершения владельца root открывается вновь; lock-файл и данные сохраняются.
- [x] **Срез 2/5 — application SQLite.** Identity/version, schema/integrity и реальные WAL/FULL/FK/busy settings; чужая, повреждённая или новая БД не переинициализируется. Незавершённая транзакция откатывается.
- [x] **Срез 3/5 — bootstrap и восстановление.** Markers отличают незавершённый первый запуск от готового root; проверены процессные crash windows и гонка первого запуска. Preflight на копии DB/WAL/journal защищает исходные файлы; неподдержанный или повреждённый journal блокирует открытие.
- [x] **Срез 4/5 — контракты данных.** Строгие `InitialRequestV1`, `BriefV1`, `StoryV1` и refs; bounded canonical JSON/digest, точные shot IDs и объявленные subjects. Валидация не означает сохранение полного публичного Brief.
- [x] **Срез 5/5 — immutable Story v1.** Внутренний test execution публикует JSON и binding; после reopen доступен тот же ref/body. Конфликт файла, tampering и ошибка file → DB не создают видимый полурезультат; повтор операции возвращает прежнюю версию. Пустая v1 DB мигрирует без сброса данных.

**Ограничения:** проверен process death на Windows, не отключение питания; symlink checks требуют соответствующих прав. Linux и cloud-sync/network volumes не приняты. Для preflight нужно временное место под копию SQLite DB/sidecars. Все данные сохранять при следующих миграциях.

<a id="step-2"></a>
## Шаг 2 — история, правка и продолжение после перезапуска — готово на Windows

Internal Story foundation сохраняет v1 → вопрос/правка → v2 → exact approval и продолжает тот же execution после restart без дубля результата или ответа следующему review. Internal inputs не являются публичным cinematic Brief.

- [x] **Версии Story.** OCC через `expected_revision`, прежние immutable refs доступны; replay не возвращает устаревший binding в current. Миграции сохраняют данные.
- [x] **Подготовка Story operation.** `story_operations` закрепляет exact inputs до owner call.
- [x] **Commit и replay.** Результат, current binding и следующий activation коммитятся вместе; повтор после reopen возвращает прежний ref/переход.
- [x] **Review и решение.** `review_requests` фиксирует exact subject/digest/revision/wait; `execution_work` атомарно сохраняет dedup decision и resume intent. Apply идемпотентен, stale decision отклоняется; wait привязан к checkpoint.
- [x] **Отдельный saver.** `checkpoints.sqlite3` открывается под lock и проходит preflight/settings; после подготовленной операции или review пропавшая БД не пересоздаётся. LangGraph interrupt переживает закрытие/reopen; сквозное восстановление проверено ниже.
- [x] **Recovery перед runner.** Exact `Command(resume=...)`/`ainvoke(None)` учитывают source checkpoint/task/interrupt и persisted pending resume; mismatch блокирует продолжение, старое решение не отвечает следующему wait. Fault-injection/reopen cases закреплены в regression tests.
- [x] **Durable internal start.** Execution, exact inputs, frozen graph identity и receipt/work коммитятся вместе; project + client key дедуплицирует payload и отклоняет конфликт. Saver проверяется под lock до start; утрата существующего saver не разрешает его пересоздание. Bootstrap старых storage-only roots сохраняет данные.
- [x] **Первый сквозной runner: revise/approve.** Один runner обрабатывает persisted start/resume/reconcile с `durability="sync"`, сверяет frozen graph/lineage/pending writes и привязывает wait после checkpoint. Claimed work живёт до stable wait/terminal, sweep восстанавливает runnable segment. Approval и terminal outcome коммитятся до `END`, settlement — после checkpoint.
- [x] **Retry/cancel и shutdown до открытия HTTP.** Dedup controls и OCC; retry только для `owner_unavailable`, с прежними source/inputs. Cancel запрещает новые решения/creative commits/approval, ожидает cleanup owner call и фиксирует `cancelled`; до этого статус `cancelling`. Shutdown закрывает commands и writers/saver/DB до release lock. Owner calls требуют bounded timeout.
- [x] **Первый localhost-прототип — API.** Start/respond/retry/cancel и exact reads; handlers сохраняют work, не вызывают граф. Loopback peer, Host/Origin/session/CSRF guards сохранены. Запуск/session bootstrap — в [local startup](backend/local-startup.md#internal-story-api-prototype).
- [x] **Работающий discussion.** Clarify/non-ready revise сохраняет typed ответ и новый request на прежнем subject без изменения Story; ready revise создаёт версию. Committed replay не вызывает owner вновь; budgets не сбрасываются duplicate/retry или новым review.
- [x] **Процессная приёмка internal Story.** Forced process death в storage/command/checkpoint windows сохраняет exact refs, receipts и approval; recovery не дублирует committed results и не retargets решения. Cancel outcome и settlement атомарны.

**Граница реализации:** расширять существующие `execution_work`, `story_operations` и `review_requests`; committed operation хранит результат/переход. Без параллельных очередей, отдельного discussion/revision engine и дублирующих receipts. Один local runner под OS lock восстанавливает abandoned claims после reacquire ownership, без leases/heartbeat takeover. Graph выбирает маршрут, runner только доставляет и восстанавливает work.

**Граница приёмки:** internal graph с детерминированной заменой модели, не power loss или полный cinematic. Committed результат не дублируется; owner call до commit может повториться. Живые adapters имеют отдельные timeout/attempt budgets.

## Шаги 3–8 — оставшаяся сборка фильма

<a id="remaining-steps"></a>

- [x] **3. Генерация текста llm и доступ автора к результату.** Storytell → exact Story review → сохранённый Wardrobe plan через существующие OpenRouter/runtime/storage. Backend W1–W6 завершён: immutable план и offline reopen приняты в W6; restart/retry с прежними inputs/provenance — в W5. W7 принят: запуск, exact inputs/config и готовые копируемые промпты в существующем UI, browser acceptance с mocked HTTP. Рендер и полный публичный cinematic Start остаются следующими этапами.
  Это completion исходного V1 milestone, не новых W8/Storyboard backend-расширений.
  - [x] **Storytell.** `backend/openrouter.py` использует `httpx`, authored prompt и strict schemas; model/prompt/schema/context/request закреплены до HTTP. Профиль: 60 s / 8192 completion tokens, две durable attempts и одна repair; manual transport Retry сохраняет inputs и авторизует новый allowance. Проверенный GLM требует `reasoning=low`. Malformed output не коммитится, repair ограничен бюджетом. Запуск — `python -m backend.launch --env-file .env`, без автоматического чтения `.env` API ([контракт](backend/local-startup.md#live-storytell-text-slice)). Новый narrative ввод требует нового execution; публичный Brief/profile contract ещё нужен для полного cinematic.
  **Characters:** authored `CharacterV1` хранится в immutable JSON/images [wiki/characters](../wiki/characters/README.md), без cloud/index/`CharacterChunkV1`. Start замораживает exact refs/card snapshots и Bio; изображения не уходят в Storytell. Пустой выбор разрешает execution-local generated cast `StoryV2`; approval не публикует библиотеку. Старые inputs и command journals сохраняются. Live text/restart проверен, текущая character route имеет отдельную backend/wire проверку, не paid visual acceptance.
   - [x] **Wardrobe — готовый backend и текстовый план в UI.** <a id="wardrobe-backend"></a>

    Результат для автора: утверждённая история передаётся Wardrobe; визуальное направление и задания
    на изображения персонажей/локаций сохраняются как план. Здесь настраиваем LLM, передачу контекста,
    хранение результата и исполнение; генератор получает готовый план на следующем этапе.

    **История принятого V1 milestone — W1–W7:** описания ниже фиксируют прежние contracts/endpoints,
    не активный Wardrobe contract. Текущая V2-only реализация и незакрытая приёмка — [W8](#wardrobe-batch-output).

    **Готовые части — W1–W6:**

    - [x] **W1 · Контракт результата.** `backend/wardrobe.py`: `WardrobeInputV1`, creative draft →
      `VisualAnchorPlanV1`, согласованный prompt и validator exact Story/body/subjects, unit keys/order/roles.
      Portrait/background независимы; sheet ссылается на оба earlier parents в порядке `[portrait, background]`.
      Поддержаны `StoryV1/V2` и generated cast; количество units приходит из плана.
    - [x] **W2 · Вызов модели.** `backend/openrouter_wardrobe.py` поверх общего `openrouter_client.py`:
      frozen model/prompt/schema/input/request, bounded completion и проверка image-input capability.
      Exact original images закрепляются inline в исходном порядке; Wardrobe base/repair/HTTP requests
      ограничены 16 MiB, execution-owned config — 20 MiB, без resize/omission/re-encoding.
      Story/text metadata, response и creative artifact JSON сохраняют default 1 MiB; image limits Character
      не меняются, combined-media budget проверяется до library loading/base64/catalog. Adapter делает один POST;
      настоящий ответ модели принят в W6. Расширение media envelope не переочередяет ранее blocked work.
    - [x] **W3 · Надёжное сохранение.** `wardrobe_operation.py`/`wardrobe_store.py` получают authoritative
      frozen start/Story/Character snapshots и exact applied approval с local selection/provenance.
      До POST сохраняются base/repair requests и резервируется попытка: максимум две attempts/одна repair.
      Schema v13 сохраняет прежние данные; validated candidate recovery, immutable `wardrobe_plan`,
      атомарный commit и exact replay готовы. После preparation retry не зависит от библиотеки/model env/prompt file.

    - [x] **W4 · Подключение после Story approval.** Новый scoped маршрут:
      `Storytell → exact Story review → Wardrobe → сохранённый plan`.
      - [x] **Новый запуск и frozen route.** Зарегистрирован `kinodel.story-wardrobe` v1;
        явный API Start замораживает narrative/subjects/Character context.
        Старые text executions сохраняют прежние identity и approve→END.
      - [x] **Утверждение → передача.** Apply атомарно сохраняет exact Story approval и Wardrobe activation;
        в новом маршруте утверждение истории больше не создаёт terminal `completed`.
        Повтор принятого решения возвращает прежний переход, не запускает новую работу.
      - [x] **Исполнение → завершение.** Node вызывает готовую Wardrobe operation; checkpoint хранит refs.
        Runner удерживает resume work до устойчивой остановки/завершения. Успешный terminal commit требует
        валидного сохранённого плана и предшествует `END`; approval, graph и work settlement согласованы.
      - [x] **Отказы и управление.** Typed `needs_input`/`out_of_scope`, unavailable и exhaustion
        дают устойчивую blocked-причину с объяснением, не успех без плана. Retry для unavailable сохраняет
        pins и остаток жёсткого бюджета двух POST; иначе — cancel/new-run. Cancel запрещает поздний creative commit.
      - [x] **Минимальные commands/reads.** `POST /api/executions/story-wardrobe` принимает тот же `LiveStart`,
        что live-story; `GET /api/executions/{execution_id}/wardrobe-plans/{artifact_id}` возвращает `{ref,plan}`.
        Только новая route добавляет в projection `wardrobe_plan_ref` и
        `wardrobe_stop={work_id,reason,explanation,allowed_actions}`. Handlers сохраняют work, исполняет runner;
         UI и обычный pipeline Start подключены в W7.

    **Приёмка:**

    - [x] **W5 · Сквозная техническая приёмка с подменённой моделью.**
      - [x] Пройти настоящий start → Story/review → exact approve → Wardrobe → immutable plan;
        проверить selected Characters/generated cast, malformed repair, non-ready, retry/cancel и budgets.
      - [x] Проверить process death/reopen между approval commit и checkpoint, в Wardrobe attempt/publication
        и между plan/terminal commit и последним checkpoint. Сохранённый результат не создаётся повторно;
        уже принятое решение не переносится на другой wait. Вызов до commit может повториться в пределах budget.
      - [x] Пройти регрессии прежних internal/live Story routes: approve→END, revise/clarify,
        duplicate/stale commands и reopen работают по прежним frozen contracts.
      Покрыты реальные process death/reopen вокруг approval/resume/checkpoint, attempt/repair/publication
      и plan/terminal/task writes; cancel при suspended HTTP/checkpoint, включая поздний ответ;
      исторический pre-W4 live-v1 frozen checkpoint. Pins и budget сохраняются, committed recovery не делает POST.
      [Evidence](../test-results/README.md#backend-evidence).
    - [x] **W6 · Настоящая модель и reopen.**
      - [x] На вымышленном проекте получить через OpenRouter валидный план с корректными subjects,
        prompts и portrait/background → sheet bindings; проверить generated cast и выбранные Character images.
        Advertised capability модели подтверждается фактическим ответом, без автоматической подмены модели.
      - [x] После закрытия/открытия прочитать тот же plan/ref без provider; committed replay не делает новый POST.
        Evidence сквозного сохранённого результата закрывает backend W1–W6; пользовательская приёмка — в W7.

    <a id="wardrobe-ui"></a>
     - [x] **W7 · Принят — Wardrobe в существующем UI до рендера.** Использовать текущую «Новую историю»,
      Pipeline/Chat и Config/Inputs/Outputs inspector, без редизайна shell.
       - [x] **Один обычный Start пайплайна.** «Начать историю» в «Новой истории» создаёт
         `kinodel.story-wardrobe` v1 через существующий `/api/executions/story-wardrobe`, без отдельной кнопки Wardrobe.
         В том же execution exact Story approval запускает Wardrobe. Исторические executions сохраняют
         frozen route и approve→END; сохранённые command envelopes — прежние endpoint, payload bytes и key.
       - [x] **Реальное состояние.** Показывать backend-derived ход Wardrobe, завершение с plan ref
        и blocked/non-ready причину с объяснением. Retry/cancel доступны только по backend actions;
        не добавлять отдельный plan HITL, editing или creative regeneration.
       - [x] **Inputs и Config.** В inspector доступны exact approved Story, фактический frozen состав
        selected Character context и generated cast с provenance; frozen provider/model config Wardrobe
         без секретов доступны после preparation через guarded `GET /api/executions/{execution_id}/wardrobe-activity`.
         Текущие env/library не подменяют frozen inputs.
       - [x] **Outputs и копирование.** Читать exact saved plan по его ref: для каждого unit показывать
        role, subject_ids, полный копируемый prompt и ordered references → unit_key (зависимости плана,
        не image refs). Количество units определяется планом, без hardcoded 5.
        Pipeline/Chat используют один authoritative результат, не два набора данных.
       - [x] **Browser acceptance.** Новый run → exact Story approve → реальные Wardrobe statuses →
        сохранённый план; скопированный prompt совпадает с полным текстом unit. Reload/reopen и повторная
        доставка могут повторять POST с прежним envelope/key, но не создают повторных принятых работ/эффектов;
        исторический run по-прежнему approve→END. При работающем backend и недоступном provider reopen
        читает тот же plan/ref без новой генерации.
       - [x] **Визуальная проверка.** Capture и inspect один desktop screenshot каждой изменённой страницы:
        `test-results/screenshots/<prototype>/vNN-<change>/screen-state-desktop.png`, для нескольких страниц —
        отдельные папки. Evidence обновить только в `test-results/README.md`; Playwright output оставить отдельно.
        W7 принят по [evidence](../test-results/README.md#wardrobe-w7-ui-integration--6-october-2026): mocked HTTP,
        без нового paid browser run; существующая live-приёмка W6 сохраняется.
        ComfyUI render и anchor review не входят в W7; готовые prompts доступны автору до их подключения.

     - [ ] **Активация в пользовательской установке.** Пользователь перезапускает ранее запущенный backend
       с текущим кодом; browser reload не обновляет Python-процесс. Перезапуск пока не выполнен;
       code/browser acceptance W7 не означает, что старый работающий экземпляр уже обновлён.

     <a id="wardrobe-batch-output"></a>
       - [ ] **W8 · Wardrobe batch_prompt V2 — реализован; финальная приёмка pending.** A pure/adapter,
         B store, C activation/runtime/API и D frontend реализованы. W1–W7 остаются исторической V1-приёмкой,
         не активным контрактом и не доказательством V2 provider readiness.
         [Контракт](tools/batch-generation.md#3-новый-creative-output-batch_prompt).
        - [x] **A · Strict DTO/schema/prompt/config.** `WardrobeInputV2` / `anchor-basics.v2`,
          `WardrobeResultV2`, `VisualAnchorDraftV2` / `VisualAnchorPlanV2`: единственный массив `batch_prompt`,
          unique `unit_key`, повторяемый `use_case=hero-face|location|hero-sheet`, semantic `workflow=txt2img|img2img`.
          `batch_unit` refs именуют earlier keys; sheet требует ровно `[portrait,background]`, face/location — zero-ref.
          Direction/creative constraints/exact Story/evidence V1 переиспользуются без изменения смысла.
          `WardrobeStartSettingsV2` / `WardrobeOwnerConfigV2`, adapter 2: fresh 180 s / 8192 / low; старые configs не читаются.
        - [x] **B · Frozen storage и retention.** `PreparedWardrobeInputsV2`, immutable plan/binding,
          candidate recovery, exact reader и прежние attempt/repair budgets. DB v14 допускает старый artifact v1
          и новый v2, сохраняя rows/files; это retention migration, не V1 conversion или поддержка V1 reader.
        - [x] **C · Versioned activation и isolation choice.** Новая exact identity `kinodel.story-wardrobe` v2
          с новым digest; `POST /api/executions/story-wardrobe/v2` принимает `LiveStart`.
          Exact прежний graph triple сохранён, но исключён из runner/list; старые Wardrobe commands/reads отклоняются.
          Unversioned Start даёт 410 до payload validation/preparation/effects. Fixture preflight/isolation проверены;
          пользовательский root не инвентаризован/мигрирован этой приёмкой и ждёт пользовательского restart.
          Нет reset, mapping, V1 consumption/replay или retarget; отдельные Story/Brief/video/library не изменены.
        - [x] **D · V2 exact reader и UI.** Pipeline/Chat сохраняют full copyable prompts, use_case/mode,
          direction и обе sheet dependencies. Старые pending envelopes сохраняют endpoint/bytes/key,
          получают definitive 410 и никогда не перенаправляются в V2; Story envelopes не меняются.
          Authored TS scopes — disconnected `anchor-batch`/`frames-batch`; исторический `cinematic.v1.json` не заменён.
        - [x] **Mocked admission/recovery и UI-приёмка.** Strict output/invalid refs/N>3, retry/offline reopen,
          process death, historical Story isolation, cancellation/late writes и browser acceptance проверены.
          Invocation-scoped drain публичных saver writes предшествует terminal/lock release.
          [Backend evidence](../test-results/README.md#wardrobe-w8-backend-and-final-status--7-october-2026),
          [UI checks/screenshots](../test-results/README.md#wardrobe-w8-subtask-d--v2-frontend-evidence--7-october-2026).
        - [ ] **Full discovery acceptance.** Два запуска завершились timeout (120 s / 360 s), не PASS;
          изолированный последний observed recovery test прошёл, причина незавершённого discovery не установлена.
        - [ ] **Live V2 provider + offline real-model acceptance.** Обновить исторический V1
          `tests/live_wardrobe_check.py`, получить реальный `plan.batch_prompt` и после restart прочитать exact
          сохранённый V2 plan/ref без provider. Paid V2 calls не выполнялись; W6 доказывает только V1.
        **Критерий финальной приёмки:** полный discovery завершён и live V2/offline gate подтверждён;
        implemented schema/config/start/graph/storage/readers сами по себе W8 не закрывают.
        Генерация изображений и technical **V2-only** saved-plan handoff принадлежат
       [ComfyUI шагу 4](roadmap-comfyui.md#wardrobe-comfyui), без второго checklist здесь.

    **Границы backend-среза:** план — supporting output без отдельного обязательного approval.
    Полный cinematic Brief/video Start и завершённый media UI не блокируют W4–W6.
    Image evidence не является render binding; общий ACL/rights-withdrawal не активирован.

    **Backend-критерий выполнен (W1–W6):** новый запуск передаёт утверждённую Story в Wardrobe и сохраняет валидный план;
    restart/retry сохраняет inputs/resources/provenance, committed replay не вызывает модель заново.
    Прежние text executions продолжают завершаться после Story approval.
    **Закрытие шага 3 и Wardrobe milestone:** W7 принят — автор проходит новый маршрут в существующем UI,
    видит exact inputs/config и сохранённый план, копирует полные prompts и открывает тот же результат после restart.
    [Контракт](agents/wardrobe.md#durable-operation), [evidence](../test-results/README.md#backend-evidence).
      NEXT — [W8: финальная V2-only приёмка](#wardrobe-batch-output), затем
      [подключение сохранённого V2 плана к ComfyUI](roadmap-comfyui.md#wardrobe-comfyui).

  <a id="storyboard-batch-backend"></a>
  - [ ] **Следующий агентный backend milestone · Storyboard batch plan.** После появления exact approved
    anchor selection; контракт — [Storyboard](agents/storyboard.md#output). Работы выполняются bounded-срезами:
    - [ ] Pure versioned FramePlan/draft/response schema, согласованный authored prompt и validators:
      `batch_prompt`, `use_case=storyboard-frame`, mode/ordered refs, full Story shot coverage/order,
      state-before composition, supplied approved-anchor aliases и declared earlier-frame sources.
    - [ ] Frozen adapter/operation/storage для exact approved Story + complete anchor set/plan; bounded
      model/repair budgets, immutable plan, retry/reopen с прежними pins, без image submission из LLM.
    - [ ] Подключить сохранённый план и read/control path к scoped runtime/существующему UI; проверить
      mocked full shot coverage, invalid/future refs, non-ready stops и offline recovery без повторного POST.
    **Критерий:** exact сохранённый storyboard plan читается после restart и пригоден для technical handoff.
    Workflow binding, earlier-frame candidate resolution, jobs/import/review и live delivery —
    [ComfyUI шаг 11](roadmap-comfyui.md#11-multi-reference-frame-workflow--storyboard-batch).

- [ ] **4. Рендер.** Выполнить [ComfyUI Local roadmap](roadmap-comfyui.md): local HTTP/явный native HTTPS → pinned workflows/Brief settings → сохранённый Wardrobe plan → общий Batch-generation с N последовательными restart-safe image jobs → anchors (portrait + background → sheet) и exact selection → Canvas/attempt workflow inspection → Storyboard batch с adaptive 1/2/3-reference и earlier-frame dependencies → оба проверенных Brief-selected modes `img2vid/ref2vid`. Img2vid использует настоящий first-frame port; ref2vid — storyboard frame + portrait + sheet, без отдельного background. Первый live render — после Wardrobe; неизвестный submit не повторять вслепую. Закрыть шаг только после всего image/video пути, затем передать выбранные clips в montage. Детальные чекбоксы и критерии срезов находятся в отдельном документе.

  **Подготовлено:** [ComfyUI шаги 1–2](roadmap-comfyui.md#1-подключение-и-read-only-preflight) — read-only config/API/CLI, единый pinned registry, txt2img/Qwen 1/2/3 inputs и offline replay. [Шаг 3](roadmap-comfyui.md#3-production-settings-и-профильные-ограничения) — V2 production/Motion contracts и draft diagnostics; настройки доступны в единой «Новой истории». Confirmed profiles, cinematic Run/submit/media отсутствуют; saved Story reopen не зависит от provider, старые inputs/drafts сохранены.
- [ ] **5. Монтаж выбранных дублей.** Exact review/selection anchors → frames → videos выполняются внутри шага 4, перед каждым зависимым этапом. Здесь взять полный утверждённый набор видеошотов и собрать ffmpeg/ffprobe финал в порядке Story без аудио, проверить размеры/длительность/формат и сохранить final result.
- [ ] **6. Минимальный экран.** Локальный [React Flow UI workspace](frontend/webui.md#first-ui-slice), [новый wireframe](frontend/uiux-wireframe.md): один execution, виды Pipeline/Chat, фиксированные матрёшки с breadcrumbs и общий Config/Inputs/Outputs inspector. Версии, вопросы/правки, exact approval и статус после reconnect; static Vite assets с local origin. Начать общий Story review на internal API после шага 2; затем подключать настоящий cinematic projection, media и provider inspection по готовности backend, не выдавая demo за live run. Проверить `npm ci`, typecheck/build, keyboard и narrow-screen flow, одинаковые decisions в двух видах, возврат viewport/scope и отсутствие дубля команды при lost response/reload. Полный проход автора без консоли остаётся обязательным.
  <a id="frontend-story-slice"></a>
  Подключение готового агента к UI выполняется в его milestone: Wardrobe — [W7 шага 3](#wardrobe-ui),
  до первого live render. Здесь остаются сквозная cinematic/media integration и полный проход автора.
  **Story UI 6A–6E принят, 6F визуально утверждён.** [Препродакшн](frontend/story-workspace-preproduction.md), [bounded задания](frontend/story-workspace-tasks.md), текущие владельцы — [FSD](frontend/fsd.md), checks — [web/README](../web/README.md#checks). Полная карта заменяет раннее Story-only ограничение; состояния берутся только из backend. Reader/approval принадлежат execution, inspector — pipeline, UI cache/delivery имеют своих владельцев; storage keys/drafts/exact pending envelopes сохраняются.
  - [x] **6A · Read seam.** `backend/story_reads.py` и typed endpoints `/api/executions/{id}/projection`, `/api/executions?limit=20`: SQL-only frozen ввод, exact review history/actions/budgets и refs; ограниченный список сохранённых internal executions. Bodies читаются отдельно, status/control не исчезают из-за ошибки файла; damaged graph identity readable для blocked inspection, повреждённая review history одного run не скрывает список остальных. Existing commands/storage protocol сохранены, policy cap общий с acceptance. Wire contract — [local startup](backend/local-startup.md).
  - [x] **6B · Frontend baseline.** React/TypeScript/Vite shell с Pipeline/Chat, responsive navigation и fixture badge. FastAPI раздаёт `web/dist` с local origin и прежними HTTP guards; missing build — 503, SPA fallback не перехватывает API. Standalone mock/checker — `web/prototype/`, его фотографии не входят в production bundle.
  - [x] **6C · Read-only connected workspace.** Список executions и URL reopen; общий exact reader/version/review/draft в Pipeline/Chat. Typed GET/session + Zod, единый Query cache и lazy body отдельно от SQL projection; фиксированные React Flow scopes, viewport/selection, keyboard/mobile. Draft не переназначается новому request; approval завершает fixture.
  - [x] **6D · Durable commands и активация UI.** Start/clarify/revise/exact approve/retry/cancel доступны из Pipeline/Chat. Exact envelope сохраняется до POST; lost-response/reload/reconnect повторяет прежний payload/key, receipt сохраняется до завершения доставки. Acceptance отдельно от server-derived progression; новая session после restart, stale/multi-tab/budgets и ошибки storage обработаны. Draft и viewport/scope/selection сохраняются при reload; старый feedback не переназначается новому request. Approval завершает fixture, не запускает Wardrobe.
  - [x] **6F · Полный cinematic UI-каркас — визуально утверждён.** Одна горизонтальная карта **Brief → Storytell → Wardrobe → Storyboard → Filmmaker → Montage → Final** доступна без test run. Правый клик по ноде/свободному canvas возвращает на уровень; по окну/backdrop закрывает только окно, сохраняя scope/draft.
    - Раскрытие: **Storytell — агент → story-hitl**; **Wardrobe — агент → anchor-gen → anchor-hitl**; **Storyboard — агент → frames-gen → frames-hitl**; **Filmmaker — агент → video-gen → video-hitl**; **Montage — сборка → проверенный файл**. Проверка файла — часть инструмента, не новый агент или gate. Brief открывает ввод; Final — выход Montage. Внутренний model/tool-loop не рисуем без реализации.
    - UI-ноды соответствуют объявленному [cinematic](pipelines/cinematic.md), но сами не исполняют граф. Неподключённые этапы помечены **«Не подключено»**, доступны для inspection и не отправляют команды генерации. Карта не обещает продолжение internal Story после approval; его реальные результаты и тестовая модель обозначены отдельно. Нет фиктивных media, ready-статусов или provider settings.
    - Компактная нода: имя, роль/иконка, один статус, краткое содержание и действие раскрытия. Главный экран — карта; результат/review и детали открываются по запросу. На обычной поверхности — идея, результат, версия и следующее действие; IDs/digests/receipts и параметры — в техническом раскрытии. Один canvas на scope, breadcrumbs, читаемые ноды, keyboard/back и сохранение viewport/выбора/черновика. Chat использует тот же результат и review.
    - Приёмка: все семь нод читаемы на desktop; вложенные этапы открываются/закрываются без POST, narrow-screen pan/zoom и keyboard navigation доступны. Story-команды/версии/drafts, reload и прежний UI state сохраняются. Каркас не закрывает provider integration или полный шаг 6.
  - [x] **6E · Story UI acceptance — пройдена после 6F.** V1 → clarify → revise/v2 → exact approve, lost-response/reload/restart replay, reopen без browser storage и review/draft retention приняты. Navigation не отправляет команды; полный шаг 6 открыт до cinematic/media пути.
- [ ] **7. Windows-пилот.** До публичного cinematic Run сохранять InitialRequest + полный Brief с видимыми `subjects` (не выдумывать их из свободной идеи), start receipt и проверенными image/video profiles. Чистая locked install с backend, migrations, agent resources, profiles и собранным UI; launcher проверяет readiness, shutdown завершает writers до освобождения lock; сохранение данных/решений при restart и [приёмка](#acceptance) на Windows. Fixture: два шота → примерные якоря → два кадра → два видео → финал; библиотека chunks не нужна.
- [ ] **8. Linux после пилота.** Отдельный lock, чистая установка и те же runtime/storage/HITL/media проверки; заявлять поддержку Linux только после её приёмки.

Для этого билда: встроенные agent resources и утверждённые upstream artifacts через direct resolver; неподдержанные source/wiki/chunk selectors отклонять, а не молча игнорировать. Critic, поиск, graph editor и hosted profile не блокируют первый фильм.

## Provider Setup

<a id="comfyui-transport"></a>

Настройка выполняется в [шагах 3–5](#remaining-steps); подробная последовательность ComfyUI и связанного UI/Brief — [roadmap-comfyui.md](roadmap-comfyui.md), без второго списка этих же задач здесь. Перед живым Storytell проверить структурированный ответ и ошибки через Pydantic, фиксированные model ID, timeout/repair budget. Перед media feedback предъявить агенту реальные доступные изображения/видео или честно ограничить наблюдения. Внешний ComfyUI работает отдельно; local HTTP достаточен при локальном Kinodel backend, polling достаточно, потерянный ответ требует reconciliation. Перед монтажом проверить ffmpeg/ffprobe и silent output. Контракты и проверочные примеры — [ComfyUI](backend/comfyui.md), [tool](tools/comfyui-tool.md).

## Acceptance

<a id="t-обязательная-техническая-приёмка-до-локального-выпуска"></a>

Для каждой проверки сохранить команду, версии build/dependencies/graph/workflow, ОС и фактический результат. Ниже — приёмка полного cinematic; Story foundation прошёл применимые проверки шага 2, но это не закрывает весь выпуск. До Windows-пилота выполнять их на Windows; Linux проходит ту же приёмку в последнем шаге, до заявления поддержки Linux.

| Проверка | Обязательное наблюдение |
|---|---|
| [ ] Start / file / DB / checkpoint crash windows | Принятый start восстанавливается; нет видимого полурезультата или второй committed версии; model call до commit может повториться |
| [ ] HITL v1→v2→approve | Сообщение идёт текущему владельцу без Critic; новая версия не наследует approval; дубликат возвращает тот же receipt; старая версия отклоняется |
| [ ] Clarify / non-ready revision | Ответ сохранён; новый actionable request на прежнем subject, прежний interrupt не переоткрыт; output version и счётчики не сбрасываются |
| [ ] Resume до/после apply и следующего wait | Уже принятый ответ завершает свой переход, никогда не отвечает следующей ноде |
| [ ] Exact context / replay | Retry получает прежние inputs/resources/projections; missing/unauthorized/stale/over-budget required context блокирует; данные источника не становятся system instructions |
| [ ] Generation timeout / lost response / restart | Подготовленные inputs/seeds сохранены; неизвестный submit сверяется; job failure даёт понятный retry/cancel, не вечное ожидание |
| [ ] Anchor lineage / references | Новое лицо или background пересоздаёт зависимый sheet и сохраняет неизменного parent; обе lineage проверены, смешанные родители отклоняются; ни один required reference не потерян |
| [ ] Every frame → video → montage | Полное совпадение shot keys/order в обоих Brief-selected modes; img2vid начинает с selected frame, ref2vid получает ordered approved frame/portrait/sheet без обещания frame 0; финал содержит все видео, корректный формат и нет audio stream |
| [ ] Cancel / duplicate / fast / late result | Отмена запрещает новые creative commits; повтор/поздний результат не оживляет запуск; быстрый результат ждёт своего точного wait |
| [ ] Ownership / storage / import / access | Второй writer не запускается; disk-full/busy/corruption дают отказ без reset; чужие refs/path escape/неверные media/Host/Origin/session отклоняются |
| [ ] Install / shutdown на заявленной ОС | Paths с пробелами/кириллицей, нет Python/network/disk, несовместимая DB: понятный отказ; нет записи после release lock или осиротевшего installer/montage процесса |
| [ ] Пользовательский проход | Идея → правки → утверждение → финал без консоли; после restart доступны те же версии, feedback и изображения/видео даже без провайдера |

Чекпоинт в памяти или один удачный render не заменяет эти проверки. Разработку начинать сейчас; Windows-пилот передавать после Windows-приёмки. Linux не блокирует пилот и не заявляется поддерживаемым до шага 8.
