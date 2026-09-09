# Исполнение и согласования

Статус: **отображение текущих контрактов на Project DB; физические DTO ещё не готовы**. Владельцы правил: [implementation](../backend/implementation.md#project-db-tables), [runtime](../backend/runtime.md), [state-machine](../backend/state-machine.md), [reviews](../backend/reviews.md). Здесь не создаётся второй граф переходов.

## Таблицы и ключи

| Имя в логическом плане SQLite local / PostgreSQL server | Минимальный сохраняемый факт | Ключи и связи |
|---|---|---|
| `projects` | Workspace/access identity | Родитель execution |
| `pipeline_snapshots` | Frozen pipeline ID/version/digest, graph compatibility | Execution ссылается на один immutable snapshot; не произвольный исполняемый JSON |
| `executions` | Project, snapshot, thread, start payload digest/key, fence, durable terminal receipt | Start key уникален внутри project; thread равен execution ID; исход immutable |
| `operations` | Stage/activation/kind/task, prepared input digest, exact refs/context/config, durable budgets, result map и next activation | Уникально `(execution_id, operation_id)`; logical ordinal один на stage/activation |
| `execution_bindings` | Slot -> точный artifact, binding revision | Уникально `(execution_id, slot)`; OCC для замены |
| `review_requests` | Gate/request revision, subject/digest/policy, decision, связь с durable wait | Уникально execution/gate/request_revision и deterministic trigger; один pending request на execution в V1 |
| `execution_work` | Start/resume/reconcile/cancel segment, source/digest, claim/retry/block/settlement | Уникально `(execution_id, kind, source_id)` **во всех статусах**, не только pending |
| `execution_controls` | Принятый cancel и позднее authorized retry controls | Dedupe command + expected revision; принятие не означает завершённую отмену |
| `event_outbox`, позже | Нормализованное событие после business commit | Event ID для at-least-once UI; не очередь графа |

Artifacts/assets/jobs/chunk bindings описаны [отдельно](artifacts-media.md). Рекомендуем scalar columns для PK/FK/status/OCC/claim selection; typed JSON для policy snapshot, prepared inputs, selection trace и bounded results. Не раскладывать каждый Brief field в универсальную EAV-схему и не дублировать artifact body в БД.

#question Q7/Q9 в [реестре](open-questions.md): [physical DTO proposal](../backend/physical-dtos.md) теперь задаёт поля JSON/dependencies, request kind/action unions, counters и receipts; executable schema и saver binding test ещё #todo. Сохраняем существующие `review_requests` для review и initial input, decision внутри request, processing receipts в `operations`. Предлагаемая дополнительная start-reservation table защищает публикацию до появления execution. Это не объявление существующих колонок/миграций.

## Транзакционные границы

| Запись | Что фиксируется вместе | Что нельзя считать частью этой транзакции |
|---|---|---|
| Start API | execution + initial_request metadata/binding + unique start work после подготовки байтов | Model call, graph invoke, atomic filesystem transaction |
| Принятие ответа API | Exact decision + gate counter increment для принятого revise/clarify + unique resume work | Critic/owner call, checkpoint resume, usable approval до apply |
| Cancel API | Dedupe control + cancel work под execution row lock; отказ новым решениям | Немедленное прекращение внешней GPU работы |
| Prepare operation | Activation identity, exact input/config/context digest, expected bindings, planned objects/pins; резерв попытки до вызова | Сам модельный ответ |
| Graph business commit | Проверка fence/control/activation/dependencies + metadata/provenance/bindings/result/next activation | Следующий checkpoint |
| Apply decision | Idempotent decision effect, consumption receipt, next activation; проверка текущей допустимости | Завершение следующей Story/Critic работы |
| Terminal commit | Immutable completed/cancelled/failed с source/reason | Отсутствие `next` в checkpoint как доказательство успеха |
| Job group terminal, позже | Immutable group result + unique wake work | Прямая запись execution binding job worker |

API-команда авторизуется и сериализуется короткой транзакцией с OCC: execution-row lock на PostgreSQL, serialized write transaction на SQLite. API не берёт graph ownership. Server worker получает session advisory lock, затем увеличивает fence; saver пишет на той же lock-owning connection. Local application держит exclusive data-directory ownership и запускает только один active graph runner. Expired heartbeat не разрешает отобрать живого владельца. Детали и recovery classifier принадлежат [runtime](../backend/runtime.md#single-writer-ownership); обе saver integration #todo.

Рекомендуемые индексы определяются реальными чтениями: список executions проекта; pending/due work по статусу и `next_attempt_at`; work/operations/requests одного execution; exact binding lookup. Уникальные индексы не дублировать. #todo На миграции проверить планы этих запросов и индексы FK; числа throughput/размеров заранее не назначаются.

## Решение не равно утверждению

Пример: вкладка A показывает Story S1 и request R1. Во вкладке B уже принята правка и создана S2/R2. Нажатие approve в A отклоняется как stale, а не утверждает S2 и не возвращает S1 в production. Ранее успешно принятое идентичное решение можно вернуть как duplicate receipt; это не новое продвижение. Историческое approval S1 остаётся историей. Чтобы выбрать старую версию снова, нужен явный разрешённый новый review/reuse путь, не старая кнопка.

Один review subject: либо точный artifact/slot/binding revision/activation, либо immutable candidate set/stage/activation/digest. Supporting plans и previews не становятся дополнительными утверждёнными предметами. Input request до Brief вообще не имеет review subject; ответ сохраняется отдельно от InitialRequest.

```text
prepare exact request -> checkpointed wait -> worker binds exact interrupt
-> API accepts decision + work -> worker resumes exact task
-> apply rechecks preconditions -> receipt + next activation
-> same segment continues until stable pause/block/terminal outcome
```

До binding checkpoint/task namespace/interrupt ID карточка `opening`, не clickable. Браузер передаёт request/digest и разрешённое действие, но не внутренний checkpoint или interrupt ID. При duplicate сначала проверяется идентичность ранее принятого payload; противоположное решение не подменяет первое.

Для artifact approval receipt связывает exact subject с apply operation. Для candidate approval usable downstream result связан с exact selection/promotion receipt и `RenderResultV1`. Не нужен общий `approved=true` на artifact. Поданная, но затем заблокированная из-за отзыва прав decision остаётся историей, не разрешением дальнейшего производства.

`revision_id = request_id` принятого revise; Critic и owner имеют обычные операции. Отдельные revision_cases/revision_jobs/stage_status tables не вводятся. Лимиты считаются по gate за execution и не обнуляются новыми карточками или retry. Текущая policy задаёт отдельные лимиты правок и пояснений; их окончательная продуктовая конфигурация относится к Q4.

## История и восстановление

PostgreSQL row/session locks этой страницы относятся к server baseline. [SQLite local](local-vs-hosted.md) требует другого ownership/transaction protocol; одинаковые таблицы не делают блокировки переносимыми. Сохранение обычного HTTP-ответа агента до graph advancement описано в [node protocol](../backend/runtime.md#node-operation-protocol); webhook не обязателен.

Checkpoint owns pending task/resume state, Project DB owns accepted command/result/transition/outcome. При DB commit перед checkpoint replay возвращает recorded refs и transition **без повторного rebinding**. Старый checkpoint не переписывает новую binding. Work не становится completed только потому, что decision consumed.

UI status вычисляется из terminal receipt, controls, work и reconciled checkpoint. Не редактировать `running/ready/stale` как независимую истину. После cancel результаты ранее commit остаются историей; поздние model/provider outputs не получают новых canonical bindings. Provider audit может догружаться после terminal execution.

- #todo Выполнить [runtime acceptance matrix](../backend/runtime.md#acceptance-matrix) отдельно на SQLite local и PostgreSQL server с process termination и pending writes, а не только in-memory saver.
- #todo Проверить atomic decision/work, repeated apply, старую card, потерю ответа после consumption и cancel/completion ordering.
- #todo Проверить совпадение FK/project ownership и отсутствие циклов provenance; SQL FK сам не доказывает свежесть closure.
