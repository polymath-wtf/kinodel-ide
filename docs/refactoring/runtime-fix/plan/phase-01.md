---
phase: 1
name: compact-runtime-facts
depends_on: approved bounded code plan
---

# 01. Compact facts и native occupancy

## Цель

Убрать повторное восстановление creative/provider inputs из slot и повторных reference/result reads. Сохранить точное доказательство dispatch, terminal release и origin/attempt ownership.

## Контекст

Исходный [аудит](../../../../test-results/README.md#read-only-responsiveness-audit--16-october-2026) показал блокировку loop из `_native_slot`, уходящего через submission preview/reference parents в Wardrobe config. В DB24 уже есть terminal observations; заново реализовывать observer не нужно. [Дизайн §5–6](../../runtime-fix.md) разделяет recorded facts и эффектные границы.

## Создать

### `tests/test_runtime_fact_reads.py`

Реальные disposable saved records с большими Wardrobe config/repair strings и несколькими historical groups. Ввести counted/forbidden wrappers для config/request reconstruction, parent resolution, PNG decode. Проверять компактное чтение против актуальных owner records, а не дублировать SQL реализации в expected values.

## Изменить

### `backend/portrait_submission_store.py:286–389`

- Добавить узкий `read_submission_facts` для уже сохранённого submission: row selectors, bounded canonical body/digest, state/revision, dispatch/native ID/wire/endpoint/input pins. Не вызывать `_preview`, batch resolver или candidate original reader.
- Разделить self-validation stored submission и сравнение с подготовленным executable preview. `read_anchor_unit_submission` на effect/recovery boundary сохраняет точную проверку входов; cheap facts не дают permission на POST.
- У `read_native_terminal_observation` выделить compact identity comparison с exact attempt/input/wire/endpoint/native ID и dispatched evidence. Не требовать ради lookup повторно построенный creative request.
- Не освобождать слот на malformed facts, local failure, missing/evicted provider history или cancellation. Противоречия — явный integrity block.

### `backend/image_group_worker.py:188–240`

- `_native_slot` читает только сохранённые selected attempt/submission facts и terminal observations. Дедупликация физического attempt по точной identity, retained-success bindings не создают нового holder.
- SQL отбирает/join-ит compact terminal evidence, но **наличие строки observation не освобождает слот**. До исключения holder проверить bounded body/digest и exact dispatched attempt/input/wire/endpoint/native identity. Malformed/mismatched observation — integrity block. Заведомо unsent записи отсеиваются только по согласованным validated facts.
- Дешёвый eligibility/due scan предшествует hydration. Отсутствие eligible graph work не отменяет known native observation turn.
- Изменить внутренний holder DTO/tuple так, чтобы полный observer context загружался только для выбранного unresolved holder, а не для каждого исторического attempt.
- Сохранить один native turn за sweep и fail-closed поведение нескольких unresolved holders.

### `backend/portrait_worker.py:78–96,428–484,579–698` и `backend/anchor_reference_worker.py:44–67,234–307`

- Повторное queue/history/reference observation использует сохранённый wire/transfer и compact current facts, **не `_preview`/Wardrobe ancestry на каждом GET**. Иначе удешевление одного `_native_slot` просто перенесёт тот же freeze в observer turn.
- Для native exact matcher загружать frozen wire/output/schema pins непосредственно из владельца записи без пересборки creative request; graph/correlation/client/output equality не ослаблять.
- `_fresh` rechecks вокруг await сравнивают текущие row revision/identity/control/pins. Heavy immutable context используется один раз на реальной подготовке эффекта; authorized GET/import не восстанавливает его заново.
- `record_native_terminal_observation` проверяет тот же compact dispatched identity и transaction OCC; возможность сохранить terminal fact после cancel не зависит от creative source-writability.

### `backend/anchor_reference_store.py:281–385,420–424`

- Отдельный saved-transfer facts reader: canonical row/body/digest, exact job/attempt/unit/intent selector, ordered upload states/receipt/final identities. Обычный read не вызывает `_context`, `_final`, parent PNG или `_snapshots` всей истории.
- Подготовка нового transfer/final graph и effect admission по-прежнему проверяют executable inputs/parents и destination ownership. Один validated context на операцию; повторный read receipt не строит его заново.
- Не менять подпись mutation reader молча: callers явно выбирают facts или effect context. В транзакции mutation сравнивать текущие точные binding/control/revision facts, не доверять фактам прошлого read.

### `backend/wardrobe_store.py:209–289,468` и `backend/anchor_parent_resolver.py:43`

- Отделить read committed plan/receipt от `read_wardrobe_operation`, который восстанавливает model config и repair request.
- Committed reader проверяет exact operation/result/input/approval refs и сохранённый immutable result digest, не пересобирает repair body. Source-authority read получает эти компактные подтверждения, а не whole provider preparation.
- Full prepared-request reconstruction остаётся перед реальным owner replay/effect. Source approval/binding revision не выводить из terminal status или существования PNG.

### `backend/image_group_results.py:131–244`

- `_facts` и parent-context callers используют узкие saved readers там, где нужен уже сохранённый lifecycle fact. `_output`/full manifest/join по-прежнему валидируют соответствующий результат на своей границе.
- Не добавлять общий ValidationContext/cache framework. Достаточны typed functions и request/operation-local reuse уже существующих contexts.

## Удалить

- Вызовы `_preview`/repair reconstruction/parent PNG из occupancy и stored-reference reads.
- Повторные одинаковые проверки одной immutable записи внутри единственной операции, сохранив проверку current authority перед mutation.
- Не удалять submission/reference/terminal evidence и не переписывать старые bodies для удобства нового reader.

## Проверка

Из корня после установки TEMP/TMP в approved temp directory:

```powershell
.\.venv313\Scripts\python.exe -B -m unittest tests.test_runtime_fact_reads
.\.venv313\Scripts\python.exe -B -m unittest tests.test_portrait_submission_store tests.test_anchor_reference_store tests.test_image_group_worker
```

- [ ] Slot и повторный transfer read: **0** Wardrobe config/repair reconstruction, parent original decode, provider HTTP. Known native/reference observer GET turn также не запускает creative/config reconstruction.
- [ ] Completed/cancelled/blocked/unknown native attempts правильно удерживают/освобождают слот, terminal observation переживает reopen/eviction.
- [ ] Corrupt SQL/body/digest/selector, foreign attempt и два holders отвергаются; отсутствующее evidence не становится permission.
- [ ] Existing lost-response/no-second-POST и cancelled-consumer late-promotion проверки проходят.
- [ ] GET-only facts не пишут SQL и не делают healing; snapshot records byte-identical после чтения.

Время и call counts записать в существующий test-results entry/новую соответствующую секцию, без отчёта в domain docs. Stop/control API этой фазой не активируется.
