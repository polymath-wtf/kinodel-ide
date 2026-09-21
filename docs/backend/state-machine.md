# Execution State Machine

Status: **Decided design; executable schemas pending**

Deployment decision: SQLite local / PostgreSQL server. Advisory-session mechanisms refer only to server; the [local profile](../database/local-vs-hosted.md) uses one application and one active graph runner with exclusive data-directory ownership. Both must prove the same durable-outcome invariants; saver integration and verification remain #todo.

There is one production transition graph, authored in LangGraph. Database lifecycles describe work, approvals, jobs, and outcomes; they are not a second switch statement that selects creative stages.

## Ownership

| Concern | Canonical owner | What a checkpoint carries |
|---|---|---|
| graph position, pending tasks, interrupt/resume values | LangGraph checkpointer | canonical task state |
| execution identity and frozen pipeline | Project DB execution/snapshot | immutable IDs |
| terminal outcome | Project DB execution terminal receipt | optional reference; may lag final commit |
| runnable intent, claim, block, retries | `execution_work` | not the scheduler |
| prepared inputs, result and authored next activation | `operations` | operation/activation refs and returned delta |
| artifact revisions and active execution bindings | Project DB metadata + managed immutable files | exact binding projections |
| review request, decision, application receipt | `review_requests` + apply operation | exact request/decision refs |
| provider attempt and group completion | jobs/group records | immutable group-wait ref |
| cancel request | `execution_controls` | queried, never copied as a mutable flag |
| reusable memory publication | `chunk_bindings` | only selected exact references via operation context |

The UI lifecycle status is **derived**, not canonical production truth. Only identity, control decisions, terminal receipts and committed results are authoritative business facts. A checkpoint can lag a business commit; replay restores its projection from the recorded operation, never repairs the database from an old checkpoint binding map.

## Identities

| Identity | Scope and rule |
|---|---|
| `project_id` | durable workspace, not one run |
| `execution_id` / `thread_id` | one run of a frozen graph; they are equal |
| `pipeline_id`, `version`, `digest` | frozen together at start; registry must match on resume |
| `stage_id` | one declared instance within the frozen graph; capability is its type, not instance identity |
| `work_id` | one durable runnable segment triggered by start/decision/job/control |
| `invocation_id` | process attempt for diagnostics only |
| `activation_id` | one authorized logical entry into a stage, derived from its durable trigger |
| `operation_id` | hash of execution, stage, activation, operation kind and optional unit/task ID |
| `logical_attempt_revision` | display ordinal allocated once per stage/activation, not a clock or retry count |
| `request_id` / `request_revision` | one exact human question/card; new card means new revision |
| `binding_revision` | monotonic version of one execution slot, not the artifact body |
| `wait_id` | one immutable external group wait, not the provider's mutable job version |

The triggering transition determines the next activation before it returns a state update. Start, owner revision, clarification, and downstream entry each have stable triggering IDs. Replay returns that recorded transition. Do not recalculate identities from current bindings, random IDs, or an increment performed outside an idempotent transaction.

Two instances of one capability retain separate stage activations, operation identities, context selections and declared output slots. A gate's exact subject/owner and fixed repair stage target one instance, never the latest result of that capability. Result port labels map to declared slots; existing cinematic slot names and identity formulas remain unchanged. Data wires do not themselves authorize transitions, and UI grouping adds no state machine or thread.

The [freeze layers](artifacts.md#freeze-layers) distinguish Run/submitted Brief/profiles/resources, prepared operation refs/context and job seeds/payloads. Future generated refs need not exist at start; draft UI edits cannot rewrite a prepared layer.

## Checkpoint Projection

`ExecutionStateV1` is implemented as a Python `TypedDict`; boundary DTOs use Pydantic. The contract is a compact JSON-serializable projection:

| Field | Content |
|---|---|
| `project_id`, `execution_id`, `pipeline` | immutable run identity |
| `bindings` | slot -> compact ArtifactRef plus binding revision |
| `activation_refs` | current authored stage activations, keyed by stage; no full operation records |
| `review_ref` | exact current review request ID, revision and digest, or null |
| `decision_ref` | exact accepted decision reference while wait/apply executes, or null |
| `wait_ref` | exact external wait identity, or null; introduced with rendering |
| `task_results` | later parallel fan-out group's keyed result refs; absent from sequential foundation |

Compact artifact refs contain ID, schema/version, URI, digest and media type. Hydration reads canonical metadata. No artifact bodies, context passages, transcripts, provider payloads, secrets, lifecycle status, or unbounded review history enter state. Runtime service handles, user authorization context and current fence enter through `Runtime[Context]`, not persistence.

Sequential nodes return partial updates. A gate clears completed decision/wait references as part of its recorded transition. An operation replay returns the same projected references; it does not choose the latest request or silently replace its input with newer canon.

For fan-out, only `task_results` has a keyed merge reducer. Its key includes group activation and stable unit/task identity. Identical duplicates are harmless; conflicts are integrity errors. Join verifies exact coverage/order and owns the candidate manifest; the gate's Render save operation owns the approved-result binding. Reset the accumulator per group; retained anchor candidates require explicit unchanged-input lineage, never an append-only list across revisions. Workers do not write bindings; no parallel human interrupts.

## Execution View

Compute the view in this priority order from durable records and the most recently reconciled checkpoint. No edge reads it.

| Status | Required evidence | User meaning |
|---|---|---|
| `completed` / `cancelled` / `failed` | immutable terminal receipt | final execution outcome |
| `cancelling` | accepted cancel control without terminal receipt | stopping, provider cancellation may still be pending |
| `blocked` | durable nonterminal work block with reason and permitted action | cannot safely continue; retry/cancel or required corrective action |
| `running` | claimed/runnable work, including an accepted decision not yet settled | preparing, creating, recovering, or applying feedback |
| `waiting_review` | durable actionable review interrupt without accepted response | approve, revise, clarify, or cancel |
| `waiting_job` | group wait with outstanding provider work and no runnable graph work | generation in progress externally |
| `created` | accepted start, not yet claimed/checkpointed | queued to start |

An unclaimed start displays `created`; queued accepted resume displays `running`. A prepared review awaiting durable wait binding displays `opening`, not `waiting_review`. `recovering`, `revising` and `applying` are activity labels, not new lifecycle machines. Return versioned views on read races; missing work/interrupts never proves success.

```text
created -> running -> waiting_review | waiting_job
              ^                  | accepted response / group ready
              +------------------+
running -> blocked -> running (authorized same-input retry)
any nonterminal -> cancelling -> cancelled
running -> completed | failed
```

An execution never leaves a terminal outcome. A new creative production after completion/cancellation/failure is a new execution; operator checkpoint editing is not a public restart mechanism. A retained approved output can remain useful even when a later stage failed.

## Operation And Stage View

Operations have `prepared`, `committed`, `blocked`, `failed` or `superseded` status. Running derives from work ownership. Prepared inputs precede effects; committed result/transition is not approval. Questions, owner explanations and control receipts can be operation results without creative bindings.

`blocked -> prepared` requires an authorized same-input retry; a change to effective creative inputs requires a new activation. `committed` is immutable. Marking an old unfinished activation superseded cannot erase its audit or promote a late result. Nodes validate activation identity before committing any output.

Stage display distinguishes `not_started`, `running`, `waiting_review`, `waiting_job`, `blocked`, `ready`, and `stale`. `ready` requires the stage's declared output checks and approval policy, not merely a committed operation. This is a projection over operation, review, binding and dependency records, never an editable stage-status table. Human actions are defined in [HITL](../hilp/hilp.md).

## Artifact State Is Not One Enum

| Dimension | Independent question |
|---|---|
| validation | did the candidate pass its schema, semantic and provenance checks? |
| freshness/availability | are its required dependency closure and rights usable for this execution? |
| approval | was this exact subject or selection explicitly approved? |
| binding/selection | is this the currently selected output of the declared owner? |
| publication | is this memory revision available through an approved chunk binding? |

An artifact can be historically approved but stale now. A rendered candidate can be technically valid but neither selected nor promoted. A final film may be approved while its memory draft is unapproved. These combinations are intentional, not contradictory statuses. See [artifacts.md](artifacts.md) for checks and transitive invalidation.

## Invariants

1. One execution has at most one live graph invocation. Server protects it through the saver-owning advisory-lock session; local permits one active runner under exclusive application/data-directory ownership. Expiry alone cannot steal live ownership.
2. API control/decision acceptance uses short optimistic transactions, not the invocation lock. Canonical graph commits additionally require the current fence.
3. Each accepted start/response/terminal job has durable work. An unfinished runnable segment cannot disappear when its process or HTTP request ends.
4. Every recorded transition contains the stable next activation; replay does not allocate another creative attempt.
5. Human request identity includes the exact subject and producing activation. Only a matching current request can create usable approval.
6. No operation consumes stale transitive execution dependencies; pinned library revisions do not silently follow `latest`, but access/rights are rechecked.
7. Approval is never inferred from artifact existence, status, checkpoint position, or a model's text.
8. Job history can advance under its own claim after execution cancellation; canonical promotion cannot.
9. Terminal outcomes are explicit and immutable. Empty checkpoint `next` alone is not a completed production.
10. A paused LangGraph thread is durable but not self-scheduling. [runtime.md](runtime.md) defines the one worker recovery protocol.
