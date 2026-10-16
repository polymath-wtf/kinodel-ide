---
phase: 3
name: application-lifecycle
depends_on: phase-01, phase-02
---

# 03. Startup, due/wake loop и shutdown

## Цель

Readiness зависит от безопасного локального открытия stores, а не production работы. Idle не крутит expensive recovery с паузой 200 мс. Shutdown ожидаемо закрывает network/tasks/writers в правильном порядке.

## Контекст

01–02 убрали ancestry/config из cheap facts/status, а тяжёлые read tasks получили собственный lifetime. Исходный startup всё ещё ждёт `runtime.run()`, а native task отмена проходит через shield до lifespan (`backend/api.py:426–459`; `backend/story_runner.py:603–623`). [Contracts §7](contracts.md) задаёт 2-секундный network cancellation grace без права рано отпустить writer lock.

## Создать

### `tests/test_runtime_lifecycle.py`

Disposable FastAPI lifespan/real saver fixtures с gated mock owner/native network, counted idle scans, cancelled requests и delayed saver writes. Не запускать пользовательский сервер или working root.

## Изменить

### `backend/api.py:426–459`

- Удалить обязательный `await runtime.run()` до lifespan yield. Preflight/setup/root ownership остаются до readiness.
- Создать один owned background worker; сетевой provider outage не блокирует session/saved reads.
- Worker ждёт runtime event либо due timeout; no-work timeout с bounded backoff, например 0.5→2 с, сброс после accepted command/реальной работы. Native observation соблюдает свою next-due задержку; нет горячего full sweep каждые 200 мс.
- На выходе закрыть admission, сигналить worker и вызвать согласованный runtime cleanup; ожидаемую отмену принадлежащего worker поглотить только после его завершения.

### `backend/story_control.py:126–246`

- Добавить `asyncio.Event` для ускоренного wake и маленький `wake()`; все accepted start/review/retry/cancel/current Continue вызывают его после transaction acceptance. Event не durable, потеря event допустима.
- `_open` проверяет закрытый admission. Сохранить `_commands` tracking; async command, начавшая acceptance до shutdown, завершается/возвращает однозначный receipt либо откатывается.
- `close` различает graph/saver writer drain, native HTTP task cancellation и read-only offloop readers. Не отменять короткую SQLite запись вместе с network await.
- Cleanup идемпотентен: lifespan и context-manager finally не запускают конкурирующий drain.

### `backend/story_runner.py:81–113,603–628`

- Сохранить `_InvocationSaver.settle` барьер и existing operation replay правила.
- Вынести lifetime native HTTP task так, чтобы shutdown мог отменить await/network и дождаться закрытия stream/client. Expected cancellation не становится false blocked work.
- После cancellation submit acceptance остаётся unknown/sent, а не unsent. Зафиксировать durable uncertainty до разрешения дальнейшего dispatch; никакого автоматического POST при restart.
- Due/recovery scan сначала cheap; full checkpoint inspection только для реально unresolved work, а не всех исторических executions каждый idle turn.

### `backend/portrait_worker.py:141–181,484–527,641–714` и `backend/anchor_reference_worker.py:112–155,170–198,307–367`

- Обеспечить cancellation propagation на network await и finally close streams/clients. Отдельно завершать начатый short receipt/uncertainty commit.
- Не менять shutdown в server/global ComfyUI interrupt, queue delete или provider Cancel.

### Канонические документы

`docs/backend/local-startup.md:9–12,22–28` и `docs/backend/runtime.md` — изменить readiness/recovery порядок и expected cancellation lifetime после подтверждённых проверок. Отчёт остаётся только в test-results.

## Проверка

```powershell
.\.venv313\Scripts\python.exe -B -m unittest tests.test_runtime_lifecycle tests.test_api
.\.venv313\Scripts\python.exe -B -m unittest tests.test_story_control tests.test_story_process_recovery tests.test_ownership
```

- [ ] Provider/owner mock не отвечает, но readiness/session и saved status доступны после local preflight.
- [ ] Empty idle не вызывает config/native preparation; event и timeout оба находят accepted work, потерянный event не теряет команду.
- [ ] Shutdown с mock network и завершившимися writers ≤3 с, no expected lifespan traceback; thread/HTTP resources закрыты.
- [ ] Repeated task cancel не освобождает lock до завершения delayed saver write; unexpected storage failure остаётся видимой.
- [ ] Crash/shutdown между dispatch и receipt сохраняет uncertainty; fresh-process recovery без второго POST.
- [ ] Startup не меняет пользовательский mode: running work восстанавливается по текущим правилам, история не переписывается.

Если local writer не укладывается в grace, fail closed/удержать ownership по local-startup, а не помечать cleanup успешным. Не подменять этим сценарием измерение network cancellation.
