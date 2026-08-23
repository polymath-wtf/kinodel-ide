# Runtime

Status: **Decided foundation**

## wtf Runtime?

Возникает вопрос: где хранится «то где мы находимся»? Старый проект отвечал: в переписке агента, в json-файлах, sqlite и в скриптах-будильниках (Это и есть те костыли). Runtime — наш ответ: отдельный слой, у которого единственный источник правды о позиции — чекпоинт состояния в state machine.

### Runtime — что это и какой нам нужен
*Гуманитарно*. Это сменный продюсер на площадке с журналом и системой автосохранения. Он сам ничего не снимает и не пишет — он следит, чтобы каждый специалист сделал свой кусок, записывает каждый принятый результат в журнал, останавливает конвейер перед кабинетом режиссёра и точно знает, кого разбудить после обеда длиной в три дня. Ночью сервер падает посреди рендера? Утром журнал говорит: «кадры досчитались, вот они, вот чекпоинт» — никто ничего не переделывает и не доплачивает за рендер дважды. Без него ты получаешь старый мир: «резюмим по самой свежей папочке в outputs и молимся».
*Реально*. А реально мы не знаем какой нам нужен runtime, но мы знаем что он должен быть простым и надежным.

## Execution Lifecycle

```text
create execution
-> freeze pipeline reference
-> invoke graph with thread_id = execution_id
-> checkpoint after each super-step
-> interrupt for review or external wait
-> resume the same thread with a typed command
-> complete, cancel, or fail
```

Every resume is a new invocation of the same thread. A database lock or lease prevents concurrent approve/resume/cancel races.

## Agent Node Adapter

```text
resolve declared ArtifactRefs
-> validate input schemas
-> select explicit context
-> construct typed agent input
-> derive stable operation_id
-> return existing committed output when operation_id is found
-> invoke bounded specialist
-> validate structured candidate
-> commit artifact idempotently
-> return compact state update
```

The agent has no checkpoint access, no arbitrary filesystem access, and no authority to route the graph.

The operation lookup must occur before model invocation. If a process crashes after commit but before checkpoint, replay reuses the committed `ArtifactRef` instead of asking the model to generate a second candidate.

## Human Review

The proposal node commits the exact revision to review. A separate gate node creates a small `ReviewRequest`, calls `interrupt()`, verifies the resumed decision against the request digest, and routes to approve, revise, or cancel.

Initially allow one active human gate per execution. Parallel review interrupts are deferred.

## External Jobs

Long renders do not poll inside a tight graph retry loop.

```text
submit job idempotently
-> persist JobRef in Project store and compact active_jobs state
-> interrupt with external_wait
-> worker/provider callback updates durable job record
-> runtime resumes thread
-> wait node re-reads job record
-> promote validated outputs
```

Callback payloads are untrusted hints. Durable job state and output hashes determine success.

## Idempotency

```text
operation_id = hash(
  execution_id,
  stage_id,
  task_id?,
  input artifact digests,
  operation kind
)
```

Do not include timestamps, retry numbers, invocation IDs, or provider request IDs. External adapters persist `operation_id -> provider_job_id` before an uncertain retry can duplicate work.

## Parallel Work

When frame or shot fan-out is introduced:

```text
plan tasks
-> Send(worker, task) x N
-> map reducer keyed by stable task_id
-> deterministic join
-> one review gate
```

Workers never replace a shared logical binding. The join validates all expected tasks, sorts deterministically, commits the aggregate result, and updates the binding.

## Events

Use LangGraph updates/custom streams internally and expose a normalized application event:

```ts
type RuntimeEvent = {
  event_id: string;
  project_id: string;
  execution_id: string;
  invocation_id: string;
  stage_id?: string;
  type:
    | "execution.started"
    | "stage.started"
    | "stage.progress"
    | "artifact.ready"
    | "review.required"
    | "execution.waiting_external"
    | "execution.completed"
    | "execution.failed"
    | "execution.cancelled";
  occurred_at: string;
  data: Record<string, unknown>;
};
```

Events are at-least-once projections. Clients deduplicate by `event_id`; project status remains recoverable from checkpoints, artifacts, decisions, and job records.

## Cancellation

Cancellation is a separate control record checked before external effects and between safe work units. A paused review resumes with `action: cancel`; a provider job is cancelled only when its adapter supports it. Already committed artifacts remain auditable.

## First Deployment

- Python or TypeScript runtime is an implementation decision still to validate.
- Use Postgres checkpointer in deployed environments.
- Use object storage for media and immutable JSON bodies.
- Start with one provider adapter and one explicit graph factory.
- Add an outbox only when reconnectable event delivery is required.
