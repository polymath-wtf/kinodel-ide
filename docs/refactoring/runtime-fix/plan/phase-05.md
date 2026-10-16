---
phase: 5
name: backend-pause-continue
depends_on: phase-04, isolated graph-step proof
---

# 05. Backend Stop / Continue на том же work/thread

## Цель

Durable pause запрещает новые production dispatch, runner останавливается на сохранённой границе, Continue возобновляет ту же work без нового бюджета и без checkpoint-keyed управляющего reconcile.

## Контекст и выбранный механизм

Project Run уже создаёт running-control revision=1. [Ранний proof](../../../../test-results/README.md#runtime-graph-step-pause-proof--16-october-2026) проверил `interrupt_after="*"`, `durability="sync"`, свежий `_InvocationSaver` на sequential superstep и recovery без event. [Contracts §4,6](contracts.md) фиксируют pause API/receipts и DB26. Обязательные инварианты — [архитектура §3.3,4.4,7.2](../../runtime-fix.md).

## Создать

### `tests/test_runtime_pause.py`

Перенести meaningful proof scenarios в application-owned fixture с настоящим `open_story_runtime`, work/control schema и saver, добавив exact review/image waits и counted mock transports. Это интеграционная проверка, не копирование experimental SQL из proof.

## Изменить

### `backend/runtime_control.py` и `backend/database.py`

- Additive 25→26: только runtime_control_commands из contracts.md. Инициализация controls остаётся из 04.
- `pause_execution`/`continue_execution`: receipt-first replay, short transaction, control OCC, current cancel/outcome/safe-boundary checks; mode change increments revision, same-mode current-revision receipt не создаёт work.
- `assert_can_dispatch(db, execution_id)` проверяет current mode/cancel/outcome внутри existing exact attempt/operation dispatch reservation transaction. Разрешение на **конкретный** effect, не всю invocation.
- Отдельный expected `ExecutionPaused` signal для остановки до нового effect внутри ещё незаконченного узла. Он не становится owner_unavailable/operational error и не требует Retry. Никакого dynamic user-pause interrupt.
- Не встраивать pause в общий commit-writability guard: уже разрешённый результат/receipt/import может сохраняться на паузе. Cancel по-прежнему запрещает late creative promotion.

### `backend/story_runner.py:38–113,144–382,385–628`

- Разделить управление runnable segment и один graph invocation. На каждом superstep — свежий graph с новым `_InvocationSaver`, runtime `interrupt_after="*"`, sync durability, затем writer drain и latest snapshot classification.
- Внутри claimed segment переиспользовать уже проверенные immutable topology/config values, не повторять полную frozen-request reconstruction при каждом создании свежего saver/graph. Current authority/control/OCC проверяются на своих границах; global cache не нужен.
- При running+runnable boundary продолжать **тот же claimed work** с `None`; не отмечать completed и не выдавать ошибку из-за `snapshot.next`. Authored graph выбирает next; runner не вычисляет следующий stage.
- Перед первым invocation проверять mode; между шагами — снова mode/cancel/current work. На paused safe boundary после drain перевести ту же claimed work в pending с OCC/work_version. Source/resume/attempt/budget/seed остаются прежними.
- `ExecutionPaused` из dispatch guard оставляет recoverable unfinished task/checkpoint. На Continue replay `None` использует durable operation result и не повторяет уже выполненный effect. Не доставлять тот же `Command(resume=...)` второй раз: pending writes/source apply receipt остаются основой классификации.
- Human/external interrupt классифицировать отдельно: unanswered wait завершает обычный сегмент; ready exact decision/result доставляется только при running-mode. Обычный static step boundary не становится review/wait и не делает source consumed.
- После crash при paused+abandoned claimed work: под root ownership дождаться/проверить доступный checkpoint и application receipts без новой creative invocation, нормализовать claim в pending или объяснимый integrity block. Process-local active set не является durable evidence паузы.
- При running-mode claim pending/abandoned work из existing source facts. Не создавать control work из checkpoint ID; старый settled/blocked reconciliation не обходить повторной вставкой.
- У reconcile work `source_id` остаётся исходным checkpoint, но latest recovery position после шага может быть его потомком. Заменить строгую latest==source проверку (`backend/story_runner.py:220–224`; `backend/image_runner.py:308–309`) на проверку exact source-to-current same-thread/root-namespace ancestry и соответствующих application operation/activation receipts. Чужие/обновлённые/необъяснимые fork lineage отвергаются; source identity не переписывается под новый checkpoint.
- Cancel work/finalization обслуживается до pause filter. Terminal outcome сильнее mode; already-authorized final commit может завершить run при конкурирующем Stop.

### `backend/image_runner.py:11–19,281` и `backend/review_store.py` decision admission/apply

- Image work использует тот же stepped invocation/expected-pause result и exact pending-write classifier.
- Approval на паузе можно сохранить вместе с existing exact resume work; apply/next progression не исполняется до Continue.
- Доставленный source, на паузе после его apply, восстанавливается через `None`, а не тем же answer в новый interrupt. Wrong checkpoint/task/namespace/interrupt/result remains block.

### `backend/openrouter.py:209–317`, `backend/openrouter_wardrobe.py`, `backend/story_graph.py`

- Guard перед reservation **каждого** нового LLM call/repair, до увеличения attempt counter. Повторный guard у фактической отправки не резервирует новую attempt.
- Bounded call, разрешённый до Stop, может завершиться и сохранить результат. Следующий repair/owner call не начинается; stopping не теряет валидный оплаченный ответ.
- Expected pause не попадает в provider-unavailable catch. Existing committed replay возвращает результат без новых вызовов.

### `backend/wardrobe_store.py:329–349` и `backend/wardrobe_operation.py:47–59`

- В `reserve_wardrobe_attempt` проверить dispatch permission **в той же транзакции до increment**. Adapter `complete_wardrobe` не владеет DB и не заменяет эту границу поздней проверкой перед POST.
- Вынести из `BEGIN IMMEDIATE` тяжёлое восстановление config/repair: сначала bounded immutable validation, затем внутри короткой transaction exact current authority/OCC/mode и reservation. Старый вызов полного reader под write lock не сохранять.
- Operation loop пропускает `ExecutionPaused` в runner как expected control signal, а не repair/unavailable/budget error. Already-reserved call/response имеет прежнюю identity; следующий repair требует новой permission.

### `backend/image_group_worker.py:157–240`, `backend/portrait_worker.py:484–698`, `backend/anchor_reference_worker.py:112–155,307–367`

- Разделить progression и observation. Paused group не готовит новый unit/upload/submit, но уже admitted job получает bounded queue/history GET/reconciliation/import/result publication.
- Guard в exact store dispatch transition: portrait dispatch/unknown marker и reference role upload claim должны сериализоваться с Stop. Upload второго role — новый effect, требует новой проверки.
- Не ставить pause в `_active`/`_fresh` целиком: это отключит разрешённые GET/import/receipt completion. Существующие cancel/terminal guards не ослаблять.
- Paid acceptance неизвестен — observer продолжает exact reconciliation, POST запрещён. Terminal release не требует снятия паузы.

### `backend/api.py`, `backend/story_control.py`, `backend/runtime_reads.py`

- Подключить новые `/controls/pause` и `/controls/continue` paths, receipt-first admission, command tracking и event после COMMIT.
- Сохранить legacy `/continue` для saved envelopes; она не вызывается новой Continue-кнопкой и не используется как fallback.
- Runtime status вычисляет pausing/paused по durable mode и graph work; unrelated native observer не удерживает pausing. Return current revision on 409, не строить broad-history token.

## Проверка

```powershell
.\.venv313\Scripts\python.exe -B -m unittest tests.test_runtime_pause tests.test_runtime_reads tests.test_projects
.\.venv313\Scripts\python.exe -B -m unittest tests.test_story_control tests.test_story_runner tests.test_story_process_recovery tests.test_image_result_runtime
.\.venv313\Scripts\python.exe -B -m unittest tests.test_portrait_worker tests.test_anchor_reference_worker tests.test_image_group_worker
```

- [ ] Stop до dispatch — 0 новых calls/uploads/submits и не потрачена reservation budget; гонка после admitted dispatch допускает только этот exact effect.
- [ ] Stop во время LLM сохраняет completed output; следующий repair не начинается. Continue не повторяет committed call.
- [ ] Stop→Continue многократно на одном checkpoint, fresh-process lost-event recovery и crash до/после claim release: та же work/thread/attempt/seed/budget.
- [ ] **Reconcile** work от source checkpoint A проходит шаг до B, pauses/reopens и продолжает ту же work по подтверждённой lineage; source A неизменен, foreign fork отвергается. Проверить Story и image пути, не только start work.
- [ ] Wardrobe Stop гоняется с реальной `reserve_wardrobe_attempt`: либо exact reservation предшествует pause, либо increment/POST нет; большой config не разбирается внутри write transaction.
- [ ] Unanswered review остаётся ждать; approval на паузе принимается, apply ждёт Continue. Pending resume writes не доставляются в чужой interrupt.
- [ ] Paused native job сохраняет результат/wake, не запускает следующий unit; sent/unknown upload не POST-ится заново.
- [ ] Stop/Continue из двух соединений/API tasks разрешаются OCC; exact replay stale receipt остаётся исходным receipt, не текущей projection.
- [ ] Неисправимый blocked/paused можно terminal Cancel; paused mode не блокирует cancel cleanup. Новый Run ждёт outcome, observer сохраняет occupancy.
- [ ] Status/Stop p95 ≤200 мс и event-loop lag ≤100 мс на большом fixture, включая реальные read/preparation boundaries с mock provider.

Обновить runtime/state/HITL/artifact control contracts только после интеграционных проверок. При несовместимости stepping с существующим wait classifier исправлять конкретную границу, не вводить новый graph DSL или scheduler.
