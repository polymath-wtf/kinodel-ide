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
  reads: Array<{ slot: string; schema_id: string }>;
  writes: Array<{ slot: string; schema_id: string }>;
  retry_class: "none" | "transient";
  routes: readonly string[];
};

type RevisionTarget =
  | "storytell"
  | "wardrobe"
  | "storyboard"
  | "filmmaker"
  | "render"
  | "montage";

type GateSpec = StageSpec & {
  kind: "gate";
  revision_targets: readonly RevisionTarget[];
};
```

This metadata validates an authored graph. It is not yet an executable arbitrary DSL.

`revision_targets` is gate-specific and finite. Human or Critic feedback may select only one declared target; graph code owns the target-to-edge mapping.

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
type AgentHandoff = {
  handoff_id: string;
  project_id: string;
  execution_id: string;
  stage_id: string;
  input_bindings: Record<string, ArtifactRef>;
  context_refs: ArtifactRef[];
  feedback_ref?: ArtifactRef;
  output_contract: {
    slot: string;
    schema_id: string;
    schema_version: string;
  };
  operation_id: string;
};
```

Node-specific Pydantic/Zod models should narrow this generic transport further. Do not pass owner skill names, tool lists, writable paths, cache choreography, provider payloads, or duplicated selected media in each handoff.

An agent stage owns one aggregate output artifact. `StageSpec.writes` remains an array because deterministic service/join stages may commit more than one declared output atomically.

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
