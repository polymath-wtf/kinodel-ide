# State Machine

Status: **Decided foundation**

The runtime state describes execution references and termination, not the creative project body.

```ts
type ExecutionStateV1 = {
  schema: "kinodel.execution_state.v1";
  project_id: string;
  execution_id: string;
  pipeline: PipelineRef;
  bindings: Record<string, ArtifactRef>;
  decisions: Record<string, ReviewDecision>;
  active_jobs: Record<string, JobRef>;
  task_results: Record<string, TaskResultRef>;
  termination?: {
    kind: "completed" | "cancelled" | "failed";
    reason?: string;
  };
  failure?: FailureRef;
};
```

`bindings` is the only slot map: logical slot to its latest produced immutable revision. A binding may be stale when its recorded input digests no longer match upstream bindings; validators prevent its use while keeping it inspectable. `decisions` is keyed by review-request digest; `active_jobs` contains compact references to durable Project-store job records. Do not duplicate a mutable `current_goal` or `pending_gate` unless an API proves it needs a cached projection. LangGraph checkpoints, `next`, and active interrupts already describe execution position.

## Identity

- `project_id`: durable creative workspace.
- `execution_id`: one attempt using a frozen pipeline version.
- `thread_id`: equal to `execution_id`.
- `invocation_id`: one start or resume API call.
- `operation_id`: stable key for one external effect across retries and resumes.

## Transition Invariants

1. Pipeline ID, version, and digest never change after execution start.
2. A node starts only after all declared input revisions validate.
3. A produced artifact enters state only after atomic commit.
4. Review decisions bind to gate ID, revision, and request digest.
5. Output existence never implies approval.
6. Revision and repair loops have hard bounds.
7. One invocation owns a thread lock at a time.
8. Parallel workers write unique task IDs; the join owns shared bindings.
9. Unexpected integrity errors fail the execution rather than asking an LLM to improvise.
10. Cancellation is cooperative and never rolls back committed artifacts.

## Review Decision

```ts
type ReviewDecision = {
  gate_id: string;
  request_revision: number;
  request_digest: string;
  action: "approve" | "revise" | "cancel";
  feedback?: string;
};
```

UI shortcuts such as A/B/C are presentation aliases, not domain state.

Review decisions are compact checkpoint state, not separate creative artifacts. Under the per-thread lock, `review_respond` first inspects the checkpoint: an identical recorded decision is an idempotent success, a different decision for the same request is a conflict, and an undecided active interrupt is resumed. The gate node records the validated decision in the same graph update that routes onward.

## Errors

- transient provider/network error: bounded retry;
- invalid structured model output: bounded repair in the agent adapter;
- missing human information: interrupt;
- creative rejection: explicit revision edge;
- provider still running: durable external wait;
- schema/integrity/programming error: fail with a typed failure reference.
