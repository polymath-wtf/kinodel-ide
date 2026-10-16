---
phase: 2
name: lightweight-reads
depends_on: phase-01
---

# 02. Лёгкие status/images reads и отзывчивость

## Цель

Status, metadata и idle не должны восстанавливать граф, model config или originals. Выдача конкретного PNG сохраняет строгие проверки bytes, не блокируя event loop.

## Контекст

01 предоставляет compact submission/reference/committed-result facts. Существующий image DTO v1 обещает полную проверку (`backend/image_reads.py:162–227`); metadata-only вводится **новым** endpoint/DTO из [contracts §4–5](contracts.md), без ослабления старого обещания. Управление control пока unavailable там, где записи ещё нет.

## Создать

### `backend/runtime_reads.py`

- Strict `RuntimeStatus` и `CommandAvailability`; функция `runtime_status(db, execution_id)` из compact execution/outcome/control/work/review/group/result facts.
- Exact execution identity, без source/effective/Retry/latest resolution. Terminal имеет приоритет; missing/inconsistent facts — unknown/block с причиной, а не invented runnable resume.
- Не импортировать graph builders, saver inspection, provider adapters или reconstruction validators. Control=null поддерживается явно; cancel capability следует существующим ограничениям supported routes.
- Availability и command admission используют одинаковые небольшие predicate functions. До control storage start/continue unavailable; таблица, отсутствующая в этой schema, не считается corruption.

### `tests/test_runtime_reads.py`

Проверки нового status, metadata v2, exact original, SQL query-only/network-forbidden reopen, call counts и concurrent heartbeat. Fixture сопоставим с аудитом по размеру Wardrobe strings и historical groups.

### `web/src/entities/execution/runtime.ts`

Strict runtime status DTO по contracts.md, включая временно nullable control. Используется уже в этом срезе действующим status polling; не ждать redesign кнопок, чтобы проверить реальную отзывчивость страницы.

## Изменить

### `backend/image_reads.py:80–227`

- Добавить `image_metadata_projection`: полная ordered declaration, selected attempt/candidate metadata, exact opaque media_ref/URL, recorded publication identity.
- Не вызывать `_completed_original`, PNG verifier или full manifest reader. Возвращать `recorded_units`/`recorded_status`, не старые verified `available_units`/`result.status`.
- Изолировать разрешение exact original selectors от общей ancestry reconstruction. Для оригинала проверить принадлежность accepted group/unit/selected attempt/completed submission и реальный candidate metadata/content digest; чужие ссылки не получают bytes.
- Full v1 reader оставить с прежним контрактом и regressions. Публикация/join не упрощаются до N candidates.

### `backend/api.py:628–707` и `backend/story_control.py:168–176`

- Добавить GET `/runtime-status` и `/images/metadata`, typed response/error boundary. Не вычислять старый Continue projection в новом status handler.
- Original GET выполняет bounded heavy read/PNG validation в `asyncio.to_thread` с **самостоятельно открытым read-only SQLite connection** внутри задачи. Передаются root/primitive selectors, не writer connection или живые DB cursors.
- Сохраняемый expensive image v1 HTTP reader также проходит через owned read-only wrapper; его старый контракт не даёт права оставлять синхронную блокировку loop. Explicit legacy process diagnostics разделяют тяжёлые immutable read/compute части и async saver I/O без передачи чужого connection в thread.
- Один конкретный async reader wrapper, без универсального task/connection pool. Отслеживать начатые readers в runtime lifetime: request cancellation не оставляет thread читающим закрываемый root без учёта.
- Один runtime-owned semaphore ограничивает одновременно исполняемые heavy read/PNG tasks до 1; status/command admission не ждут его. Отмена queued GET не запускает thread, отмена started GET не бросает его lifetime. Это bounded read gate, не новый scheduler.
- Если actual effect preparation всё ещё разбирает многомегабайтный frozen payload синхронно, разделить pure parsing/read-only validation и короткую application-thread current/OCC проверку. Тяжёлый read имеет собственный connection; post-await snapshot recheck перед mutation обязателен.

### `backend/story_reads.py:38–118` и `backend/continue_command.py:346–349`

- Обычная lightweight projection не присоединяет checkpoint inspection неявно. Сохранить explicit legacy `/process`/`include_process` контракт там, где он ещё вызывается.
- Новый status не зависит от `_inspect`; full recovery inspection остаётся в реальном runner/recovery path. Не заменить expensive polling на UI query, который внутри повторяет тот же вызов под новым именем.

### Действующие UI consumers: `queries.ts:24–38`, `images.ts`, `ImageCandidates.tsx`, `Workspace.tsx:35–125`, `ContinueControls.tsx:62–94` в `web/src/`

- Минимальным сквозным изменением переключить автоматический status polling на `/runtime-status`, image query/strip — на metadata v2. Recorded counts/status подписать честно; exact original URLs сохраняются.
- Убрать автоматический 2-секундный `/process` polling. Старую policy/handoff projection получать только по потребности legacy action/inspector; не выводить её action из нового status на клиенте.
- Общий lightweight query owner используется Pipeline/Chat. Body/activity queries не превращаются во второй фоновый status loop.
- Снять `useFresh`/`!isFetching` permission gate у текущих runtime commands, сохраняя command busy, exact identity, backend OCC и отдельную проверку Story subject/body. Это bounded UX-фикс, без Project navigation redesign.
- Добавить affected strict DTO/query/browser checks в существующие `web/checks/image-*`/`continue-*` checks; новые Project/control command kinds здесь не нужны.

## Проверка

```powershell
.\.venv313\Scripts\python.exe -B -m unittest tests.test_runtime_reads tests.test_image_reads
.\.venv313\Scripts\python.exe -B -m unittest tests.test_continue tests.test_api
```

Из `web/`: `npm run typecheck`, `npm run build`, `npm run check:schemas`, `npm run check:commands`, `node checks/image-browser-check.cjs`, `node checks/continue-browser-check.cjs`; обновить только ожидаемый read/UI-контракт.

- [ ] Runtime status: **0** graph construction/checkpoint inspect/config/base64/PNG; metadata list: **0** original-byte reads.
- [ ] p95 status ≤200 мс, max event-loop lag ≤100 мс на agreed fixture во время sweep и нескольких original GET. Считать тяжёлые функции отдельно от timing.
- [ ] В реальной странице/guarded browser harness нет автоматического `/process`/v1-images polling. Network request counts подтверждают использование новых reads; нельзя принять фазу только по быстрому unused endpoint.
- [ ] Exact selectors, retained Retry origins, missing/corrupt PNG и wrong input/candidate/attempt/digest по-прежнему отвергаются.
- [ ] Metadata candidate не отображается в DTO как проверенный complete-set; malformed published envelope даёт 409, не null/no-result.
- [ ] Старый v1 list/original HTTP contract и no-write/no-network read regressions сохранены.
- [ ] Отмена request не закрывает root lifetime поверх живого read thread; thread завершается и connection закрывается в finally.
- [ ] Desktop screenshot каждого реально изменённого Pipeline/Chat экрана сохранён, открыт и проверен; evidence index обновлён по AGENTS.md.

Не заявлять performance acceptance на маленьком новом fixture, если исходные большие frozen inputs не представлены. Доказательства — в test-results, контракты reads — в artifacts/frontend docs.
