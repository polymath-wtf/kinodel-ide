# Runtime

Status: **Decided design; SQLite/PostgreSQL integration and crash tests #todo**

Decision, 2026-09-09: SQLite local and PostgreSQL server are selected. The [local profile](../database/local-vs-hosted.md) has one application process and one active graph runner per data directory; PostgreSQL supports multiple workers, with one invocation per execution. All durability/approval invariants apply to both; implementations and crash tests remain #todo, and PostgreSQL locks cannot be assumed on SQLite.

The runtime reliably delivers authorized work to an explicit LangGraph graph. It does not independently choose production stages. The target is recoverable execution with idempotent business commits, not exactly-once model/provider calls.

## First Deployment

Use Python 3.12, FastAPI and Pydantic. Local: SQLite, managed local data directory, API and one background graph runner in one application process. Server: PostgreSQL, managed server storage and separate API/worker entry points; begin with one worker and support multiple workers through execution ownership. SQLite/PostgreSQL checkpointer setup remains #todo. Redis, Celery, a graph compiler, and an event bus are not needed.

| Component | Owns |
|---|---|
| API | authorization, validated commands, short DB transactions, read projections |
| worker | sole graph invocation path; claim, start, resume, recover, finalize cancellation |
| authored graph | stage routing, typed node updates, checkpoints and interrupts |
| node adapter | exact input preparation, bounded agent call, validation, idempotent commit |
| Project DB | work, operations, bindings, requests, terminal outcomes, controls, later jobs |
| managed files | immutable validated artifact/media bytes; never scheduling |

The API returns an accepted execution/request/work identity after its transaction. HTTP completion, browser disconnect, and streaming lifetime never own graph execution. Additional server workers use the server claim protocol; the local profile does not allow a second active runner.

## Durable Work

Use one `execution_work` table, replacing the unshipped review-only `execution_resumes` design. It covers the whole runnable segment, not just delivery of a resume value.

```text
Work: work_id, execution_id, kind, source_id, payload_digest,
      resume_ref?, owner_token?, claim_version, heartbeat_at,
      retry_count, next_attempt_at, blocked_reason?, settled_checkpoint_id?
kind: start | resume | reconcile | cancel
status: pending -> claimed -> completed
                    |       -> blocked -> pending (authorized retry)
                    |       -> failed
                    |       -> obsolete
                    -> pending (safe recovery after ownership release)
```

The source uniqueness key is `(execution_id, kind, source_id)` across **all** statuses. Completed work cannot be recreated by duplicate callbacks or client retries. A `resume_ref` identifies a durable review/input decision or immutable external wait result, never an arbitrary graph update. Manual retry requeues the same blocked work with optimistic concurrency and a deduplicated control command; it preserves its original source and resume identity.

Work remains claimed through the graph call until a durable unanswered interrupt, an explicit runtime block, or a terminal outcome is settled. In particular, a resume is not completed just because its decision was consumed: a crash in the following Story/Critic node must still leave work to recover. Completion of a work row means a segment settled, not that the film is complete.

## Start Protocol

```text
authorize and validate opening request + frozen pipeline snapshot
-> prepare immutable InitialRequest bytes under the file commit protocol
-> transaction: execution + initial_request metadata/binding + start work
-> return accepted execution_id
-> worker claims work and execution ownership
-> absent checkpoint: invoke exact initial state
-> existing checkpoint: recover it; never submit initial state again
```

Start idempotency is scoped to project and client key. Store a normalized payload digest: same key/same digest returns the existing execution, changed digest conflicts. An orphan file before the transaction is not an execution. A committed start without a checkpoint is ordinary recoverable work. An empty project is not a started execution.

## Single-Writer Ownership

Local SQLite: one application holds exclusive OS-backed ownership before DB open/migrations and for its entire lifetime, including saver tasks. A second application refuses startup; heartbeat expiry never evicts a live owner. One active graph runner consumes durable work. Short serialized write transactions enforce OCC, current fence/activation and cancel checks; no write transaction spans model/network calls. API handlers enqueue work, never invoke the graph. Stop effects on ownership/DB failure; shutdown drains or stops tasks and flushes saver writes before releasing ownership. Recovery first reacquires directory ownership, then uses the common decision table. Network-share data directories and concurrent writable restored copies are unsupported. [Local startup](local-startup.md) proposes permanent-file stdlib OS locks, alias/child-process rules and bounded busy handling; platform selection and actual crash/saver tests remain #todo.

The numbered protocol below is **PostgreSQL server only**. References elsewhere to execution-row serialization mean short SQLite write transactions locally, row locks on server; the invariant is atomic control/commit ordering, not portable lock syntax.

1. Select due work, then obtain the execution's PostgreSQL **session advisory lock** on a dedicated connection. Use a server-derived stable lock key; collisions may serialize extra executions but never allow two writers.
2. Under that lock, claim the work and increment the durable execution fence in a short transaction. Read current controls/outcome and verify the registered frozen graph digest.
3. Construct the invocation's `AsyncPostgresSaver` with that same connection, not an unrelated pool. It remains open and lock-owning through all checkpoint writes and task cleanup. Use `durability="sync"`.
4. Heartbeat claim/ownership through short repository transactions. Graph business commits lock the execution row, validate current fence, active activation, expected bindings, and cancellation before commit.
5. On lost connection or heartbeat failure, stop issuing effects, cancel/await local graph tasks, and close the saver connection. Never reconnect a saver underneath an old invocation. Release ownership only after tasks/checkpoint writes are stopped.

Lease expiry is a recovery signal, **not permission to steal a live advisory lock**. The fence advances only after the new worker acquires the lock. Same-session saver ordering remains a proposed integration guarantee, not a passed test: pin and verify direct-connection support, connection lifetime, pending writes and failure cleanup. Do not introduce a custom fenced saver merely to bypass a live owner; if the pinned saver cannot preserve this invariant, block rollout and evaluate a minimal fenced saver explicitly.

A hung but connected process delays recovery until bounded call/DB timeouts or its process supervisor terminate it and PostgreSQL releases the session. The product does not promise immediate takeover during a network partition. This safety/availability tradeoff must be measured in the integration test. API cancellation does not require this long-lived lock.

## Node Operation Protocol

```text
derive operation identity from persisted activation
-> read operation record
-> committed: return recorded refs + transition, without redoing effects/rebinding
-> otherwise prepare exact input refs, expected outputs, settings, context selection
-> persist prepared input digest before model/provider effects
-> verify authorization, dependencies, cancellation and remaining attempt budget
-> perform one bounded unit of work
-> validate candidate and publish immutable bytes
-> transaction: recheck fence/controls/dependencies; commit metadata, bindings,
                provenance, result refs and deterministic next activation
-> return compact checkpoint delta
```

Operation identity, artifact commit, and dependency semantics are specified in [artifacts.md](artifacts.md). Technical retry/recovery retains the activation and prepared input. Creative revision or authorized upstream recomputation gets a new activation derived from the durable triggering transition. Clock time, lease fence, and process attempt never identify creative work.

Model output lost before commit may require another model call and may differ or incur another charge. Only the committed result is canonical. Paid external generation instead persists a job intent before submission and reconciles ambiguous acceptance before retrying.

For an agent's ordinary OpenRouter HTTP response/stream, the adapter completes and validates the bounded output, persists artifact bytes or the typed operation result, then commits result/next activation before returning graph state. This is not necessarily a webhook or a durable provider job. Partial streamed text is not a completed production result. A callback, if a provider later needs one, still cannot directly advance graph state.

Replay may return old recorded refs to finish an interrupted transition; it must never reinstall them over newer bindings. An unexpected active-activation mismatch blocks as an integrity problem, rather than guessing that the current binding belongs to this task.

## Human Input And Resume

The logical gate is `prepare_request -> wait -> apply_decision`:

- Prepare persists a deterministic request and returns its exact reference. It performs no model call.
- Wait calls `interrupt()` once using that reference; after resume it validates the decision reference and returns it. It does not commit approval, call Critic, or promote assets.
- Apply atomically records the decision effect, marks its source consumed, and records the next activation. This is an ordinary idempotent operation, including after an interrupt.

After the paused invocation flushes checkpoints, the worker binds the application request/wait ID to the exact checkpoint, task namespace, and interrupt ID. Only then is a pending human request actionable. If the worker crashes before binding it, recovery inspects the checkpoint and exposes the same card without rerunning generation.

The API transaction validates the current request, stores an idempotent decision and one resume work row. It never invokes `Command` itself. Review semantics and input questions are defined in [reviews.md](reviews.md).

## Recovery Decision Table

On startup and continuously, the worker selects due work and abandoned claims from the Project DB. Under execution ownership it inspects the latest checkpoint **including pending task writes**, the work source, and any durable apply receipt. A checkpoint ID or missing interrupt alone does not prove decision consumption.

| Observed state | Action |
|---|---|
| durable terminal outcome exists | no creative invocation; settle remaining work/controls as completed or obsolete |
| cancel requested, no terminal outcome | stop/settle local effects and finalize cancellation; do not invent a resume answer |
| start work, no checkpoint | invoke the persisted initial state once; synchronous input checkpoint precedes node effects |
| checkpoint has runnable/failed retryable tasks, no unanswered interrupt | `ainvoke(None, same_thread_config)`; replay only unfinished work |
| matching interrupt, durable response not yet in checkpoint task writes | `Command(resume={interrupt_id: decision_ref})` for that exact wait |
| response is already persisted for that task but apply/next node unfinished | `ainvoke(None, ...)`; do not send the response to a later interrupt |
| matching unanswered review/input wait and no decision | bind/expose it, settle current segment, wait for a new API command |
| external wait, no terminal group result yet | bind wait, settle current segment; jobs remain durable and worker polls/reconciles |
| later stable wait and original source has an apply receipt | settle original work; later wait needs its own source command |
| request exists but its wait was not checkpointed | continue the preceding checkpoint with `None`; prepare/wait replay reuses the same request |
| no runnable tasks and no business terminal receipt | integrity block; never infer successful production solely from `next == ()` |
| mismatched request, graph version, namespace, source digest or unexplained checkpoint lineage | block for diagnosis; never resume an arbitrary wait |

The checkpoint adapter must distinguish a pending interrupt from a task whose resume value is already persisted. Pin the framework/saver versions and test this classifier against real saved checkpoint tuples; do not infer it from UI status or node names. Preserve the exact source checkpoint and task identity on resume work for this comparison.

A small reconciliation sweep also checks nonterminal executions with no live work: `created` without a start checkpoint must still have its unique start work; unfinished checkpoint tasks need recoverable work; settled waits without an input are normal. If a segment was incorrectly marked complete while tasks remain, a unique reconcile item keyed by the observed checkpoint recovers it or records a mismatch. Do not continually invoke unanswered human gates.

## Errors, Retry And Blocking

| Failure | Owner and handling |
|---|---|
| transient network/rate limit | bounded node retry; same operation; retry budget recorded durably across crashes |
| unavailable database/storage | stop effects; leave recoverable work; backoff when dependencies return |
| invalid model draft | bounded structured-output repair; never commit invalid output; exhausted repair blocks with diagnosis |
| missing input before a Brief exists | typed input request, one focused Producer question |
| ambiguous or out-of-scope creative feedback | Critic feedback-needed path back to the exact gate |
| unavailable/withdrawn mandatory context | block before a call or commit; no fallback to search/other canon |
| ambiguous provider submission | reconcile by durable provider key/ID; if impossible block, do not blindly pay again |
| integrity, provenance tampering, unsupported frozen graph or programming failure | fail closed; durable failure/diagnostic, no model repair of control state |

`blocked` is nonterminal and includes reason, work/operation identity, and allowed resolution. `retry` is allowed only for an explicitly retryable reason and unchanged inputs; new requirements do not mutate a prepared operation. No graph interrupt is necessary for an operational outage: the unfinished checkpoint task plus blocked work already supplies the recovery point. Input/review questions use real interrupts instead.

Each deployed stage declares timeout, max technical attempts, structured repair limit, and cost/concurrency budget. RetryPolicy is one mechanism inside this persisted budget, not a second independently resetting allowance. Counters are reserved before calls; a crash may consume an attempt. Exhaustion requires an explicit authorized retry or cancellation, not an endless startup loop.

## Cancellation And Terminal Outcomes

Cancellation acceptance is a short execution-row transaction independent of the invocation advisory lock. It records a deduplicated control and cancel work, and rejects further new decisions. The UI says `cancelling`, not `cancelled`. Every commit checks this same row; therefore a result committed before cancellation remains history, and a later business commit cannot pass the cancellation check.

The active worker observes controls between bounded calls and before commits, stops scheduling effects, cancels local tasks, and best-effort cancels/reconciles provider jobs. Once it has stopped local production commits, it finalizes `cancelled` under execution ownership. A crashed worker's successor performs the same finalization. A hung invocation must release ownership through timeout/supervision first.

Terminal outcome is an immutable Project DB fact: `completed`, `cancelled`, or `failed`, with its source operation/control and reason. A completion node validates required current approvals and commits `completed` before `END`. If this commit survives but the final checkpoint does not, recovery honors the outcome without re-running production. If cancellation races completion, execution-row transaction ordering decides which was accepted first; the terminal result is never rewritten.

Late provider results may be retained as job audit but cannot promote assets, bind output, or resume cancelled/failed/completed executions. A final approved film may remain available after cancellation of its later memory step; execution completion and individual artifact approval are different facts.

## Rendering Extension

Provider jobs are added with cinematic production. Each has its own claim/fence, immutable request identity, unit ID, provider idempotency key, attempt budget, and restricted audit. Job workers do not hold the graph invocation lock while a provider renders and do not change execution bindings.

```text
planner commits exact plan
-> submit stage commits job-group intent and immutable wait identity
-> workers submit/reconcile units using job ownership
-> one graph wait for the group, not an interrupt per unit
-> group terminal result + unique wake work committed atomically
-> graph validates/join manifests -> candidate review -> promotion
```

The wait token is `{wait_id, stage_id, activation_id, request_digest}`. It is not an expected mutable provider job version. A fast result arriving before the wait checkpoint stays pending until recovery reaches that exact wait. A group with unfinished required units cannot publish a complete candidate set. Same-request technical retries preserve successful units; a creative aggregate revision starts new jobs under a new activation. Partial creative reuse is deferred.

Provider submission cannot be guaranteed exactly once without provider support. Unknown acceptance remains blocked/reconciling; a new charged attempt requires an explicit policy/creator authorization. Cancellation of external work is best effort, while prohibition of its downstream promotion is enforced locally.

## Context, Events And Deployment

Freeze one exact context selection on the prepared operation. Recovery rehydrates it, rechecking access and rights; it does not rerun discovery or select newly published canon. Derived index changes never schedule graph work. See [context.md](../context/context.md).

Foundation exposes polling-friendly execution/work/request/artifact queries. Streaming and an at-least-once outbox are later; dropped events cannot lose work. UI reconnect queries current records. Authorization, path isolation, validation, and credential separation apply from the first deployable slice, not only after streaming is added.

Deployment runs version-gated profile-specific migrations/saver setup, pins tested graph/schema/framework versions, retains registered graph versions for open executions, and starts worker reconciliation. Local startup checks schema versions every launch under ownership; initialization is automatic for fresh data, existing-data upgrades require an explicit tested maintenance path, never reset. Shutdown stops claiming, drains bounded work, flushes saver writes, then releases ownership. Restart safety assumes durable SQLite locally or PostgreSQL on server plus managed storage. Complete stopped-installation manual transfer includes Project DB, saver data/pending writes, immutable files and version manifest. Automated backups, RPO/RTO and disk-loss restore drills are #future production, not MVP acceptance; without an independent copy disk loss can destroy work.

## Acceptance Matrix

These are required runnable integration tests for implementation, not claims that they pass today.

| Inject failure/race | Required result |
|---|---|
| after start transaction, before first invoke | worker starts the same execution without browser retry |
| during model call, before business commit | same activation/input; no second canonical output; another model charge is possible |
| after file publish, before DB commit | orphan or reusable pinned bytes, never a visible half-committed artifact |
| after artifact/transition commit, before checkpoint | replay recorded output and transition, no rebinding/regeneration |
| after request preparation, before interrupt checkpoint | same request becomes actionable after replay |
| after decision transaction, before resume | same durable decision is delivered by worker |
| after persisted resume, before apply | recover pending task writes, apply once |
| after apply, during Critic/owner/next stage | original work recovers the remaining segment |
| after next wait checkpoint, before work completion | settle old work, never feed its answer into the new wait |
| expired heartbeat with still-live advisory session | no takeover or concurrent checkpoint writer |
| old session lost, old model response arrives | old business commit rejected; old saver cannot reconnect/write |
| cancel during generation or racing approval/completion | deterministic accepted ordering, no post-cancel promotion |
| after terminal DB commit, before END checkpoint | retain terminal outcome and outputs; no restart of production |
| fast job completion, duplicate callback, cancelled late result | one wake source; correct wait only; no cancelled promotion |
| context reindex/supersede/rights withdrawal during a pause | unchanged pinned input for first two; blocked use for withdrawal |

Run the common cases separately on real SQLite and PostgreSQL with process termination; an in-memory saver cannot prove these guarantees. PostgreSQL additionally tests session loss/live-lock takeover and concurrent workers. SQLite additionally tests second-app refusal, one active runner, busy/error handling and saver flush/process death. Compatible manual transfer is tested when shipped; automated backup/disk-loss restore is #future production. Test file publication on each supported filesystem before claiming power-loss durability. All checks remain #todo.
