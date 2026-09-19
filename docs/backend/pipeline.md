# Pipeline Architecture

Status: **Decided foundation**

Product amendment: [node architecture](../pipelines/node-architecture.md) defines the target user-authored editor and new anchor flow; [node roadmap](../pipelines/node-roadmap.md) lists required synchronization. The declarations below remain the authored-runtime baseline, not an implemented visual schema/compiler. User composition is introduced in a later verified phase rather than enabled by arbitrary `/goal` routing.

A pipeline is a versioned graph definition that binds stage IDs to capabilities, declared artifact slots, validators, routes, and human gates. It is configuration plus code, not an agent.

## Stage Kinds

- `agent`: bounded creative reasoning.
- `service`: deterministic or asynchronous execution.
- `gate`: human interrupt and semantic decision.
- `join`: validates and aggregates parallel results.

```ts
type StageSpec = {
  id: string;
  kind: "agent" | "service" | "gate" | "join";
  owner: string;
  reads: Array<{
    slot: string;
    schema_id: string;
    dependency_mode: "current_execution" | "pinned_revision";
    requires_approval: boolean;
  }>;
  writes: Array<{ slot: string; schema_id: string }>;
  context_policy_id?: string;
  retry_class: "none" | "transient";
  routes: readonly string[];
};

type GateSpec = StageSpec & {
  kind: "gate";
  subject_kind: "artifact" | "candidate_set";
  revision_stage_id: string;
};
```

These are architectural pseudo-types for declarations validated beside an authored graph factory, not implemented Pydantic schemas, TypeScript runtime code, or an executable arbitrary DSL.

Each gate reviews one exact current-stage object. `revision_stage_id` is fixed by the authored graph; neither human prose nor Critic output selects a graph destination. See [`reviews.md`](reviews.md).

## Activation And Repair

The API records commands; the worker is the sole graph invoker. Durable `execution_work` covers start/resume/retry/reconcile/cancel and remains live through invocation until a stable checkpoint pause or end. It replaces unshipped `execution_resumes`, not a shipped compatibility contract. Operations own prepared activations and exact inputs; result plus next activation commit together as defined in [`artifacts.md`](artifacts.md#operation-identity). A checkpoint projection or a provider callback cannot invent a new activation.

Review identity includes the exact subject, attempt, and dependency closure. Each authored gate defines these routes:

| Action/outcome | Authored route |
|---|---|
| `approve` | Validate exact subject/selection and dependencies; save approved result in apply path, then advance |
| `revise` / Critic `ready` | Critic -> fixed owner -> declared repair path -> same gate with new subject |
| `regenerate` at anchor review | Render selected units and dependents with new frozen seeds -> new complete-set review; no prompt edit or Critic |
| `revise` / Critic `needs_input` or `out_of_scope` | New request for the same subject plus explanation; no owner call |
| `clarify` | Producer explanation -> new request for the same unchanged subject |
| `cancel` | Terminal cancellation path |

A repair path includes render joins, deterministic execution, and any required intermediate reapprovals; it is not a direct edge that skips them. Critic preserves feedback and cannot rewrite an approved ancestor. On `needs_input`/`out_of_scope`, the creator may revise feedback, approve the existing subject only if still valid, or cancel. Foundation/V1 has no automatic upstream rewind: use a new execution with adjusted Brief/context when the change exceeds this gate's owner. General reopening is deferred.

Accepted earlier-stage rework uses a new execution/branch in the same project with an exact frozen prefix, explicit reuse receipt and validated source approvals/closure. Target and descendants are newly produced/reviewed; E1 outputs remain immutable for comparison. Only allowlisted authored entry stages may skip a reused prefix, never a client checkpoint or LLM-selected edge. Entry DTOs/routes and checks remain #todo; ordinary foundation start still begins at Brief until enabled. See [rework contract](../database/artifacts-media.md#возврат-к-раннему-этапу).

Freeze defaults of five accepted revisions and five clarifications per gate for the execution. Accepted feedback counts even if Critic cannot dispatch it; duplicates, crash replay, and technical retries do not. Exhausting one limit removes only that action; only when both are exhausted does the next request offer approve/cancel alone. Invalid mandatory context or stale dependencies block approval and require recovery/cancel. Revision progress labels derive from review requests and operations; no revision-workflow table is needed.

## Shared Shape

```text
input/context
-> creative spine
-> visual/audio anchor
-> hard review
-> detailed production plan
-> parallel generation
-> hard review
-> motion/audio assembly
-> final review
-> reusable approved memory
```

Not every pipeline uses every stage. `serial_season.v1`, for example, intentionally stops after planning and anchors.

## Handoffs

The runtime replaces legacy `delegate_task` envelopes with node-specific types. Static stage metadata supplies ownership and write targets; runtime adapters hydrate exact artifacts and selected context.

```ts
type ContextSelectionRef = {
  selection_id: string;
  digest: string;
};

type AgentHandoff = {
  handoff_id: string;
  project_id: string;
  execution_id: string;
  stage_id: string;
  input_bindings: Record<string, ArtifactRef>;
  context_selection_ref: ContextSelectionRef;
  feedback_ref?: ArtifactRef;
  output_contract: {
    slot: string;
    schema_id: string;
    schema_version: string;
  };
  operation_id: string;
};
```

This older `AgentHandoff` sketch is not a universal executable envelope. Concrete mode inputs follow [physical DTOs](physical-dtos.md); Critic feedback uses an `OperationResultRef`, not the sketch's `feedback_ref: ArtifactRef`. The operation stores one frozen [`ContextSelectionV1`](../context/context.md), including projection versions/digests, before the model call; retries reuse it. Graph state and handoffs carry only the reference, not the full trace or bodies. At the agent boundary the adapter hydrates typed artifact bodies and consumer-specific context content from those prepared refs. A selection trace alone is not prompt content. Missing mandatory context blocks the stage. Do not pass writable paths, cache choreography, provider payloads, or duplicated selected media in each handoff.

A successful creative production stage owns one aggregate output artifact. Critic, Producer explanations and non-ready outcomes store operation results without creative bindings. `StageSpec.writes` remains an array because services may commit multiple declared outputs atomically. Graph validation rejects competing slot owners. A media gate's apply path invokes its declared Render save operation, the sole owner of the selected-result slot; the human decision itself does not write creative content. No separate visible promotion node is required. Other capability rules follow the [agent catalog](../agents/README.md#common-contract).

## Production Joins

Plans declare stable units and exact references; workflow declarations specify named typed inputs/outputs. Stage mappings bind these directly to Render jobs, without a universal request artifact or a closed list of agent plans. Unit jobs write candidates, never a shared canonical binding. One join records a complete manifest; one human gate selects the full set, and its apply path saves `RenderResultV1` through Render. Sequential dependent jobs use the same mechanism as independent jobs, without requiring graph fan-out.

Group waits carry immutable `wait_id` and `request_digest`. Technical retries keep successes. Anchors use [changed-unit plus descendant regeneration](../pipelines/cinematic.md#anchor-regeneration) and exact retained-candidate lineage; other creative aggregates initially rebuild all units. Missing units or mismatched parent/child candidates block approval. General cross-execution selective reuse and parallel human gates remain deferred. Result approval does not separately approve supporting plans.

## Versioning

- Freeze `{pipeline_id, version, spec_digest}` at execution creation.
- Existing executions always resume against the same graph version.
- Start with explicit graph factories such as `cinematicV1Graph()`.
- Add a registry mapping ID/version to graph factory.
- Enable a constrained known-node compiler at the node-roadmap composition stage, after the fixed route and configurable node contracts work. General-purpose compilation remains deferred.

## Pipeline Creation

`create-pipeline` is initially a design assistant, not a live runtime mutation feature. It may propose stages using the known capability registry, but a human must review, validate, test, version, and register the resulting graph before execution.

The later visual editor replaces manual graph authoring for its supported node types through server-side validation and versioned compilation. It edits a draft for a new execution, not the graph of an in-flight thread; cross-version partial reuse requires separate verification.

## Pipeline Pages

- [`../pipelines/cinematic.md`](../pipelines/cinematic.md)
- [`../pipelines/music-video.md`](../pipelines/music-video.md)
- [`../pipelines/serial.md`](../pipelines/serial.md)
