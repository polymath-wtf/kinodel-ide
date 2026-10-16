# Контракты code plan

Статус: **предлагаемые точные контракты для Gate 2**, не описание уже существующих endpoints. [Архитектура](../../runtime-fix.md) определяет смысл; этот файл фиксирует wire/storage, чтобы разные фазы не изобретали их независимо.

## 1. Общие типы и HTTP правила

Обозначения в таблицах — JSON-типы, не дополнительные wire-поля:

- `UUID`: существующий `CanonicalUUID`; `Digest`: `sha256:<64 lowercase hex>`; `Key`: непустая UTF-8 строка до 128 символов.
- `Revision`: strict integer ≥ 1. Все объекты strict, неизвестные поля запрещены; `null` только там, где указан.
- `Graph`: `{id:string,version:string,digest:Digest}`; точное равенство одному из существующих поддержанных graph triples, не новая registry.
- `Profile`: существующий `ExactProfilePin`; `Connection`: существующий `BatchConnectionPinV1` (`backend/story_anchor_start.py:21–24`).
- `CommandAvailability`: `{available:boolean,reason:string|null}`; available=true требует reason=null. Это возможность admission сейчас, не гарантия успешной генерации.
- `Error`: `{"detail":{"message":string,"current_revision":Revision|null}}` для новых 404/409 команд. Неверный payload — существующий FastAPI 422 validation body; 401/403 — текущая local boundary. Старые endpoints не получают новый error shape.

Все routes требуют существующую loopback/Host/Origin/session boundary; POST также CSRF (`backend/api.py:465–485`). GET не выполняет writes, provider/network I/O, migration, repair или graph invocation. Mutating HTTP returns acceptance, не progress.

Receipt lookup по exact key+payload выполняется до проверки актуальной revision/config. Один key с другим payload — 409. После потерянного ответа повторяются тот же endpoint/body/key. Никакого автоматического нового POST после 409.

## 2. Project draft v1

Повторно использовать форму raw draft из `web/src/pages/workspace/model/productionDraft.ts:6–14`, а не требовать полного `CinematicDraftV2` при Save. Хранение partial strings позволяет пережить reload посреди ввода; runnable constraints проверяются на Run.

```text
ProjectDraftV1 = {
  schema_version: "1",
  graph: Graph,
  idea: string <= 131072 chars,
  selected_characters: CharacterRef[0..16],
  image_width: string <= 64 chars,
  image_height: string <= 64 chars,
  video_width: string <= 64 chars,
  video_height: string <= 64 chars,
  shot_count: string <= 64 chars,
  target_seconds: string <= 64 chars,
  video_mode: "img2vid" | "ref2vid",
  image_profile: Profile | null,
  video_profile: Profile | null,
  connection: Connection | null
}
```

`CharacterRef` — существующий exact domain type (`backend/domain.py:498`), unique subject IDs. Draft не содержит biographies/images/base64, credentials или current-provider payload. Video поля сохраняются как draft, но не активируют несуществующий cinematic/video runtime.

На Run: непустая идея; 1–8 shots; stable `shot-001…`; exact total/per-shot milliseconds без округления, существующие duration bounds. Для text-only graph render inputs остаются неисполняемыми draft settings; для Story-anchor graph image size/profile/connection обязательны и проверяются как `AnchorRenderIntentV1`. Exact Character revisions и owner settings замораживаются по существующему Start protocol.

Сначала разрешён текущий Story-Wardrobe V2 graph. Story-anchor graph допускается только после отдельной route acceptance. Изменение default graph меняет только новые drafts; сохранённый draft/envelope не ретаргетится. Пользователь явно сохраняет смену graph перед новым Run.

## 3. Project API

```text
Project = {
  project_id: UUID,
  title: string (1..256 chars),
  revision: Revision,
  draft: ProjectDraftV1 | null,
  current_execution_id: UUID | null,
  run: CommandAvailability
}

ProjectReceipt = {schema_version:"1",command_key:Key,project:Project}
```

`draft=null` допускается только для исторического проекта, если editable intent нельзя достоверно восстановить. Нужен explicit Save перед Run. `current_execution_id` не заменяет проверку всех nonterminal executions этого проекта при admission.

| Метод / path | Request | Response |
|---|---|---|
| `POST /api/projects` | `{command_key:Key,project_id:UUID,title:string,draft:ProjectDraftV1}` | 201 `ProjectReceipt` |
| `GET /api/projects?limit=20` | limit integer 1..100 | 200 `{schema_version:"1",items:Project[]}` |
| `GET /api/projects/{project_id}` | Exact UUID | 200 `Project` |
| `POST /api/projects/{project_id}/draft` | `{command_key:Key,expected_project_revision:Revision,title:string,draft:ProjectDraftV1}` | 200 `ProjectReceipt`; whole draft replacement |
| `GET /api/projects/{project_id}/executions?limit=20` | limit 1..100 | 200 `{schema_version:"1",project_id:UUID,items:ExecutionSummary[]}` |
| `POST /api/projects/{project_id}/run` | `{command_key:Key,expected_project_revision:Revision}` | 202 `RunReceipt` |

```text
ExecutionSummary = {
  execution_id:UUID,
  graph:{id:string|null,version:string|null,digest:string|null},
  status:string,outcome:"completed"|"cancelled"|"failed"|null
}
RunReceipt = {
  schema_version:"1",command_key:Key,project_id:UUID,
  project_revision:Revision,execution_id:UUID,thread_id:UUID,work_id:UUID,
  control_revision:Revision,graph:Graph,snapshot_digest:Digest
}
```

`status` — enum из runtime-status ниже, а не произвольная строка в реализации. History graph — raw recorded identity, включая unsupported/null legacy значения, не заявление о поддержке маршрута; runnable draft/Run используют строгий Graph. `thread_id=execution_id`; snapshot_digest — accepted Start/frozen-input identity, а не digest текущего mutable draft. Receipt возвращает accepted revisions; GET возвращает текущие.

Run проверяет project revision дважды: перед подготовкой и в финальной транзакции. В ней же проверяется отсутствие любого nonterminal execution проекта, создаются execution/start work/running-control, project pointer/revision и receipt. Короткая транзакция без await; подготовка exact Character/owner pins выполняется до неё. Не вызывать существующий Start с отдельным COMMIT, а затем дописывать Project receipt второй транзакцией.

Два разных Run keys с одной revision: один accepted, второй 409 с текущей revision; same-key replay — тот же RunReceipt. Unknown Project — 404. Неисправимый block сам по себе не разрешает новый Run; сначала terminal Cancel.

## 4. Runtime status и pause API

```text
RuntimeStatus = {
  schema_version:"1",project_id:UUID,execution_id:UUID,graph:Graph,
  control:{desired_mode:"running"|"paused",revision:Revision}|null,
  status:"created"|"running"|"opening"|"waiting_review"|"waiting_job"|
         "blocked"|"pausing"|"paused"|"cancelling"|"completed"|"cancelled"|"failed"|"unknown",
  outcome:"completed"|"cancelled"|"failed"|null,
  reason:string|null,
  wait:{kind:"human"|"external",id:string}|null,
  image_progress:{recorded:number,total:number}|null,
  external_work:"none"|"outstanding"|"uncertain",
  commands:{stop:CommandAvailability,continue:CommandAvailability,cancel:CommandAvailability}
}
ControlReceipt = {
  schema_version:"1",command_key:Key,execution_id:UUID,
  desired_mode:"running"|"paused",control_revision:Revision
}
```

| Метод / path | Request | Response |
|---|---|---|
| `GET /api/executions/{execution_id}/runtime-status` | Exact UUID | 200 `RuntimeStatus` |
| `POST /api/executions/{execution_id}/controls/pause` | `{command_key:Key,expected_control_revision:Revision}` | 202 `ControlReceipt` |
| `POST /api/executions/{execution_id}/controls/continue` | То же | 202 `ControlReceipt` |

До создания control record status возвращает control=null и stop/continue unavailable с причиной; cancellation остаётся доступной по существующей policy. После migration control существует у всех supported nonterminal executions.

Переход mode меняет revision; новый key для уже установленного mode с актуальной revision получает receipt без новой work и без increment. Stale revision, terminal/cancelling execution и Continue в `pausing` — 409. Continue на paused operational block может снять пользовательский mode, но не снимает сам block; status всё ещё объясняет его. `reason` и availability выводятся из компактных текущих фактов, не из checkpoint inspection.

Приоритет: terminal → cancelling → pausing/paused overlay → operational block/wait/runnable facts. Paused+claimed graph work означает `pausing` до flush/release/recovery; paused+нет такой claimed work — `paused`, независимо от уже отправленного GPU job. Native observer не владеет graph claim. После crash abandoned claim нормализуется runner под root ownership до показа подтверждённой safe boundary.

Terminal Cancel использует существующий `POST /api/executions/{execution_id}/cancel`, `{command_key:Key}`, 202 `{work_id:string}` (`backend/api.py:799–807`). Cancel не требует running-mode и не восстанавливает terminal run. Существующие receipt/error shapes этого endpoint сохраняются.

## 5. Image metadata v2

Новый `GET /api/executions/{execution_id}/images/metadata` возвращает:

```text
{
  schema_version:"2",execution_id:UUID,project_id:UUID,group_id:Digest,
  total_units:integer>=1,recorded_units:integer>=0,
  units:[{
    unit_key:string,use_case:string,
    state:"unstarted"|"in_progress"|"blocked"|"failed"|"candidate_recorded"|"metadata_invalid",
    original:ImageOriginalV1|null
  }],
  result:{result_id:Digest,digest:Digest,recorded_status:"complete"|"failed"}|null
}
```

`ImageOriginalV1` и exact opaque media selectors переиспользуются из `backend/image_reads.py:134–159`. Только candidate_recorded имеет original; recorded_units равен их числу, не числу успешно прочитанных PNG. Порядок и полное покрытие units соответствуют принятой membership; duplicates/foreign refs запрещены. `use_case` использует существующий enum из image DTO.

`recorded_status` — факт опубликованного manifest, не текущая полная проверка originals. GET проверяет compact publication/candidate envelope identity/digest/выбранный attempt, но не загружает original bytes или Wardrobe config. Неконсистентный published envelope — 409, не result=null. Unit-local повреждение metadata — metadata_invalid без URL. Исторический результат без достаточной проверяемой metadata не превращается в complete по N картинкам.

Старый `/images` v1 сохраняет прежний строгий контракт; новый клиент переключается на metadata v2 явно. Original GET сохраняет URL/selectors/MIME/no-store/nosniff и проверяет реальные возвращаемые bytes/digest/geometry. Missing/corrupt original даёт ошибку чтения, не repair. Manifest publication/join/явный полный result reader сохраняют полную проверку.

## 6. Persistent records

24→25 (имена и поля фиксированы для реализации при неизменном baseline):

```text
projects(
  project_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  draft_body TEXT NULL, draft_digest TEXT NULL,
  revision INTEGER NOT NULL CHECK(revision>=1),
  current_execution_id TEXT NULL REFERENCES executions(execution_id)
)
project_commands(
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  command_key TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('create','save','run')),
  payload_digest TEXT NOT NULL, receipt_body TEXT NOT NULL,
  PRIMARY KEY(project_id,command_key)
)
execution_runtime_controls(
  execution_id TEXT PRIMARY KEY REFERENCES executions(execution_id),
  desired_mode TEXT NOT NULL CHECK(desired_mode IN ('running','paused')),
  revision INTEGER NOT NULL CHECK(revision>=1)
)
```

25→26:

```text
runtime_control_commands(
  execution_id TEXT NOT NULL REFERENCES executions(execution_id),
  command_key TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('pause','continue')),
  payload_digest TEXT NOT NULL, receipt_body TEXT NOT NULL,
  PRIMARY KEY(execution_id,command_key)
)
```

Title/draft/key/receipt валидируются owner-функциями; draft_body/digest либо оба null, либо оба заданы, CHECK плюс проверка canonical bytes/digest на загрузке. Control row — intent, не task/delivery queue. Нет отдельного pause status, номера Continue-сегмента или provider job в этой таблице. Existing `execution_controls` cancel/retry и work uniqueness не меняются.

Backfill Projects группирует существующие project IDs, не создаёт work. Один достоверный nonterminal execution может стать current_execution_id; несколько — pointer=null и Run unavailable до их явного завершения. Не выбирать «самый свежий» и не отменять старую работу автоматически. Неизвестный draft — null; title — безопасный bounded preview без media/config. Nonterminal supported executions получают running-control revision=1, terminal/retired история не оживает. Readers supported terminal runs могут вернуть control=null.

После upgrade control создаётся атомарно **во всех поддержанных acceptance paths**, включая старые Start envelopes, first delivery после migration, historical image handoff и explicit Retry: shared Story acceptance и `_accept_image_start`. Project Run использует те же helpers; отдельная control-запись не меняет прежние receipts/unique scopes. Если explicit legacy Start впервые создаёт execution для ещё не зарегистрированного project ID, Project storage owner в той же transaction создаёт минимальную историческую запись с draft=null; текущий draft не перетирается. Initial control/Project нельзя лениво создавать в GET.

Run использует детерминированный внутренний Start client key из project ID/Run command key с доменным namespace, укладывающийся в текущий лимит; original command key/body остаются в project_commands. No extra global source-plan uniqueness.

При user pause runnable work остаётся той же pending после writer drain. Claim crash recovery не requeues operational block, не меняет source/resume identity и не обновляет budgets/seeds. Нормальный stable wait может завершить сегмент; дальнейшая доставка принадлежит exact review/result records.

У reconcile work immutable source checkpoint отличается от продвинувшейся current position: recovery проверяет source-to-current same-thread/root-namespace ancestry плюс exact application receipts, вместо строгого latest==source. Не переписывать source под latest и не принимать неподтверждённую/foreign fork lineage. Это проверка реального recovery, не status polling.

## 7. Bounded lifecycle и error policy

- Proposed network shutdown cancellation grace: **2 секунды** после запрета новых claims. Успешное mock shutdown с завершившимися локальными writers — ≤3 с.
- Это не разрешение выпускать lock через 2 с при живом SQLite writer. По превышению grace фиксируется fatal cleanup failure, admission остаётся закрытым; ownership удерживается до завершения writers/процесса по существующему local-startup правилу.
- Stop execution не использует этот shutdown timeout для насильственной отмены LLM: bounded разрешённый вызов сохраняет результат, следующие calls запрещаются.
- Expected worker CancelledError поглощается только после cleanup. Ошибки storage/identity и неожиданные exceptions не превращаются в штатный shutdown.

Пороговые значения подлежат Gate 2 вместе с планом; если реализация требует иных чисел, это явное уточнение с измерением, не скрытое увеличение ожидания.
