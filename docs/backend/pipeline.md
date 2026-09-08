# Pipeline Architecture

Status: **Decided foundation**

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
| `approve` | Validate exact subject/selection and dependencies; promote or advance |
| `revise` / Critic `ready` | Critic -> fixed owner -> declared repair path -> same gate with new subject |
| `revise` / Critic `needs_input` or `out_of_scope` | New request for the same subject plus explanation; no owner call |
| `clarify` | Producer explanation -> new request for the same unchanged subject |
| `cancel` | Terminal cancellation path |

A repair path includes render joins, deterministic execution, and any required intermediate reapprovals; it is not a direct edge that skips them. Critic preserves feedback and cannot rewrite an approved ancestor. On `needs_input`/`out_of_scope`, the creator may revise feedback, approve the existing subject only if still valid, or cancel. Foundation/V1 has no automatic upstream rewind: use a new execution with adjusted Brief/context when the change exceeds this gate's owner. General reopening is deferred.

Freeze defaults of five accepted revisions and five clarifications per gate for the execution. Accepted feedback counts even if Critic cannot dispatch it; duplicates, crash replay, and technical retries do not. At either limit the next request offers approve/cancel only for a valid subject. Invalid mandatory context or stale dependencies block approval and require recovery/cancel. Revision progress labels derive from review requests and operations; no revision-workflow table is needed.

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

Node-specific models narrow this transport. The operation stores one frozen [`ContextSelectionV1`](../context/context.md), including projection versions/digests, before the model call; retries reuse it. Graph state and handoffs carry only the reference, not the full trace or bodies. At the agent boundary the adapter hydrates typed artifact bodies and consumer-specific context content from those prepared refs. A selection trace alone is not prompt content. Missing mandatory context blocks the stage. Do not pass writable paths, cache choreography, provider payloads, or duplicated selected media in each handoff.

An agent stage owns one aggregate output artifact. `StageSpec.writes` remains an array because deterministic service/join stages may commit more than one declared output atomically. Graph-factory validation builds a `slot -> owner stage` index within each pipeline version and rejects duplicate owners, except a declared revision loop back to that same owner. Gates write no artifact slots.

## Production Joins

Plans declare stable ordered unit IDs and exact inputs. Render adapters map the existing frame/motion/music plan to unit jobs, not to another universal request artifact. Parallel jobs write job-scoped results, never a shared canonical output slot. One deterministic join owns the immutable stage-level candidate manifest; one sequential human gate selects the complete required unit set; one promotion stage owns its `RenderResultV1` slot. Candidate manifests are runtime records, not creative artifact bindings.

Group waits carry immutable `wait_id` and `request_digest`. Same-request technical retries keep successes; creative aggregate revisions rebuild all units in the first renderer. Missing units block join/promotion rather than silently shortening production. Selective creative reuse and parallel human gates are deferred. A result gate approves its subject only; validated supporting plans do not acquire independent human approval by association.

## Versioning

- Freeze `{pipeline_id, version, spec_digest}` at execution creation.
- Existing executions always resume against the same graph version.
- Start with explicit graph factories such as `cinematicV1Graph()`.
- Add a registry mapping ID/version to graph factory.
- Consider a compiler only after at least two working pipelines expose stable repetition.

## Pipeline Creation

`create-pipeline` is initially a design assistant, not a live runtime mutation feature. It may propose stages using the known capability registry, but a human must review, validate, test, version, and register the resulting graph before execution.

## Pipeline Pages

- [`../pipelines/cinematic.md`](../pipelines/cinematic.md)
- [`../pipelines/music-video.md`](../pipelines/music-video.md)
- [`../pipelines/serial.md`](../pipelines/serial.md)
