---
phase: 4
name: projects-and-atomic-run
depends_on: phase-03, isolated graph-step proof
---

# 04. Project без запуска и атомарный Run

## Цель

Проект/draft существуют без execution; Run фиксирует exact draft revision и принимает один execution/start work. История executions не подменяет список проектов.

## Контекст

Stores/lifecycle уже готовы без production startup work. Текущий UI создаёт project UUID прямо перед Start (`web/src/pages/workspace/Workspace.tsx:228–230`); backend принимает execution/work отдельной транзакцией (`backend/story_start.py:245–283`). [Contracts §2–3,6](contracts.md) задают partial draft, exact API и additive DB25. Early proof снял необходимость отдельной Continue delivery-таблицы.

## Создать

### `backend/projects.py`

- Strict `ProjectDraftV1`, Project/receipts/request DTO по contracts.md. Partial draft сохраняется без model/provider/graph calls, без inline media/credentials.
- Concrete functions create/read/list/save/history/run; canonical draft JSON + digest, project OCC, exact command receipts. Scope key — project + command_key; kind/payload collision отвергается.
- Run сначала возвращает saved receipt, затем читает draft/revision, проверяет поддержанный exact graph и settings, разрешает exact Character revisions и замораживает owner config через existing Start preparation.
- Финальная короткая transaction повторно проверяет revision и отсутствие любого nonterminal execution проекта. В ней же execution/start work, running-control, project pointer/revision, receipt. Если preparation завершилась после чужого Save/Run, 409, без принятого execution.
- Внутренний Start client key детерминирован из project/Run key; одинаковый envelope не повторяет remote model-metadata lookup, Character resolution или приём работы.
- Fresh Run сохраняет существующую bounded metadata/capability validation выбранного model перед acceptance (`backend/openrouter.py:189–206`). Это не owner generation; запуск owner принадлежит worker. Не добавлять отдельный mandatory preflight click.
- Первым поддержать нынешний Story-Wardrobe V2 route. Draft image/video настройки не выдают разрешение неактивным этапам.

### `backend/runtime_control.py`

На этом срезе только initial storage owner: read control и `initialize_running_control` внутри caller-owned acceptance transaction. `desired_mode=running`, revision=1; **pause/continue HTTP commands не активируются**. Новая запись создаётся вместе с Run; самостоятельного scheduler/work kind нет.

Initial control создаётся **для каждого нового supported execution**, не только Project Run: shared Story acceptance (`backend/story_start.py:270–282`) и image acceptance (`backend/image_group_store.py:265–280`) вызывают этот helper в своей existing transaction. Так first delivery старого Start envelope после upgrade, historical Continue handoff и explicit image Retry получают control без изменения их endpoint/receipt/scope. GET ничего не достраивает.

Если такой explicit legacy Start впервые использует project ID после upgrade, тот же acceptance через Project storage owner создаёт отсутствующую историческую Project-запись с draft=null и safe title. Не оставлять этот execution невидимым в Project list до следующей migration. Не заменять существующий draft и не навязывать legacy private starts Project-Run uniqueness.

### `tests/test_projects.py`

Create/save/list/history/Run/replay/race/migration и restart на disposable stores. Считать owner/provider generation calls, а отдельно metadata validation calls; не выдавать отсутствие LLM за отсутствие любого metadata GET.

## Изменить

### `backend/database.py:18,402–448,830–843` и `tests/test_database.py`

- Additive 24→25 из contracts.md: Projects/receipts/running-control. Обновить `_expected_schema` и исторические schema checks, не предыдущие DDL.
- Backfill existing project IDs без изменения execution bodies/rowids/work/checkpoints/outcomes. Не выбирать latest при нескольких незавершённых executions.
- Невосстановимый draft=null; Run unavailable до явного Save. Initial running-control только для поддержанных nonterminal execution; migration сама не вызывает runtime/provider.
- DDL/backfill/post-validation failure откатывают новые schema/data атомарно, прежняя база остаётся проверяемой.

### `backend/story_start.py:145–202,215–283`

- Разделить existing Start preparation и transaction-owned acceptance. Конкретный typed prepared-start value содержит frozen bytes/digests/graph/brief/shot pins, но не живые connections.
- Shared acceptance helper выполняет SQL без собственного COMMIT, если вызывается Project use case. Existing Start routes вызывают тот же helper в своей транзакции и сохраняют прежние receipts/replay semantics.
- Не оборачивать `await pin_story_owner`/Character loading во write transaction. Не принимать execution до project OCC и не исправлять orphan acceptance удалением.
- Подготовленные immutable files, если нужны, следуют existing reservation/publication protocol; незакоммиченный файл не становится execution/result.

### `backend/story_control.py:137–195`, `backend/api.py:568–628`, `backend/runtime_reads.py`

- Добавить Project API routes из contracts.md, use cases через существующий runtime ownership/admission tracking. Run вызывает wake после COMMIT.
- Read runtime control через initial owner, nullable historical terminal control сохраняется. Stop/Continue availability пока false с явной причиной, поскольку command contract ещё не подключён.
- Project current pointer проверяется на принадлежность; history ограничена exact project ID. Старый `/api/executions` остаётся execution-list контрактом.

### `backend/image_group_store.py:223–280,389–458`

Подключить initial-control owner в общем `_accept_image_start`, которым пользуются private starts, old Continue bridge и Retry. Не добавлять им Project-Run uniqueness/новую capability. Проверить все insertion paths, включая standalone Story/internal/live/anchor starts после migration.

## Проверка

```powershell
.\.venv313\Scripts\python.exe -B -m unittest tests.test_projects tests.test_database
.\.venv313\Scripts\python.exe -B -m unittest tests.test_story_start tests.test_live_story tests.test_story_wardrobe_api tests.test_story_anchor_start
```

- [ ] Create → fresh-process reopen: проект/draft есть, **0 executions/work/checkpoints/генераций**.
- [ ] Save неполного draft и потерянный receipt восстанавливаются; stale save не перетирает чужую правку.
- [ ] Same Run envelope — один receipt; два разных ключа на одной revision — один execution/start work/running-control, второй conflict.
- [ ] Gated preparation + concurrent Save/Run не создаёт execution со смешанными inputs; rollback оставляет прежние данные.
- [ ] Draft после Run редактируется без изменения frozen execution; новый Run после terminal сохраняет прошлую историю.
- [ ] Исторические standalone Starts/private consumers сохраняют свой scope и не получают искусственную глобальную source-plan uniqueness.
- [ ] First delivery старого Start envelope **после upgrade**, новый historical image handoff и image Retry создают running-control в одной acceptance transaction; subsequent pause guard не оставляет их бесконтрольными/неисполняемыми.
- [ ] Неподдержанный graph/profile/Characters/settings отвергается без owner/render effects, retired route не оживает.

Обновить Project/Start ownership в canonical docs после проверки; новые terminal states или pause UI этой фазой не вводятся.
