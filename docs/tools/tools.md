Все тестовые тулы надо переписать на python!!!

# Tools And Services

Status: **Foundation registry**

Tools are typed, least-privilege operations. They do not replace graph nodes and they do not expose a terminal or arbitrary filesystem to agents.

## Boundary

| Concern | Correct home |
|---|---|
| route stage, interrupt, resume, join | LangGraph node/edge |
| creative judgment | specialist agent |
| validate/read/commit artifact | deterministic tool |
| provider submission and polling | background job service |
| render/montage execution | service/worker |
| UI cards and notifications | pure event projection |
| migration/backfill/rebuild | admin operation |

## Result Contract

```ts
type ToolResult<T> =
  | {
      ok: true;
      data: T;
      meta: {
        operation_id: string;
        idempotency_key?: string;
      };
    }
  | {
      ok: false;
      error: {
        code:
          | "INVALID_ARGUMENT"
          | "NOT_FOUND"
          | "ALREADY_EXISTS"
          | "VERSION_CONFLICT"
          | "SCHEMA_INVALID"
          | "PRECONDITION_FAILED"
          | "FORBIDDEN"
          | "PROVIDER_UNAVAILABLE"
          | "TIMEOUT_UNKNOWN"
          | "PARTIAL_FAILURE"
          | "INTERNAL";
        message: string;
        retryable: boolean;
        field_errors?: Array<{ path: string; message: string }>;
      };
      meta: { operation_id: string };
    };
```

Do not use stdout JSON or process exit codes as internal service contracts.

## Mutation Rules

Every mutating operation must:

- accept an idempotency key and canonical input digest;
- validate before side effects;
- enforce ownership and authorization;
- use optimistic concurrency when replacing an existing binding or control record;
- commit content and metadata atomically;
- return the previous result for the same key and same digest;
- reject the same key with different input;
- avoid arbitrary paths supplied by agents.

## P0: Artifact And Project Tools

### `project_create`

```ts
project_create({
  project_id,
  idempotency_key
}) -> { project_id, project_revision }
```

Creates the durable workspace, refuses accidental overwrite, and publishes atomically. It does not require an already approved brief.

### `execution_start`

```ts
execution_start({
  project_id,
  pipeline_ref,
  initial_request,
  idempotency_key
}) -> { execution_id, thread_id, pipeline_ref }
```

Freezes the pipeline reference and starts its first graph invocation. Brief drafting and approval occur inside the graph.

### `project_get_status`

```ts
project_get_status({ project_id, execution_id? })
  -> ProjectStatusSummary
```

Pure query over checkpoints/project metadata. It never repairs or synchronizes state.

### `project_list`

```ts
project_list({ status?, limit?, cursor? })
  -> { projects, next_cursor? }
```

Uses indexed metadata, not recursive filesystem discovery.

### `artifact_get`

```ts
artifact_get({
  project_id,
  artifact_id?,
  slot?,
  expected_schema?,
  projection?: "full" | "summary" | "selected_assets"
}) -> { ref, value }
```

Agents normally receive hydrated inputs from node adapters instead of calling this themselves.

### `artifact_validate`

```ts
artifact_validate({
  project_id,
  schema_id,
  candidate,
  input_refs
}) -> { valid, issues, content_digest }
```

Runs JSON-schema/Pydantic validation plus semantic and cross-artifact invariants. It never mutates state.

### `artifact_commit`

```ts
artifact_commit({
  project_id,
  execution_id,
  slot,
  schema_id,
  candidate,
  input_refs,
  expected_binding_revision,
  idempotency_key
}) -> { artifact_ref, binding_revision }
```

Only the declared stage owner may write the slot. Validation and immutable commit are one transaction boundary.

### `artifact_get_by_operation`

```ts
artifact_get_by_operation({ project_id, execution_id, operation_id })
  -> { artifact_ref } | null
```

Every model/service node calls this before repeating nondeterministic work. It makes replay after commit-before-checkpoint failure safe.

### `artifact_inspect`

```ts
artifact_inspect({ project_id, artifact_id })
  -> { ref, counts, selected_assets, issues }
```

Compact projection for Producer, UI, and diagnostics.

### `review_respond`

```ts
review_respond({
  execution_id,
  interrupt_id,
  decision,
  expected_request_digest,
  expected_checkpoint_id,
  idempotency_key
}) -> { accepted, checkpoint_id }
```

This is the typed API boundary around LangGraph resume. `checkpoint_id` is the LangGraph checkpoint observed by the client, not an application-invented state counter. Under the thread lock, the runtime rejects stale cards and conflicting duplicate decisions.

## P0: Render Tools And Service

### `render_preflight`

```ts
render_preflight({
  request_ref,
  stage_id,
  provider_profile_id
}) -> { request_digest, normalized_jobs, provider_bindings, resource_plan }
```

Validates stage/job compatibility, exact input assets, dimensions, capability support, and stable job fingerprints without loading secrets or submitting work.

### `render_start`

```ts
render_start({
  request_ref,
  provider_profile_id,
  idempotency_key
}) -> { run_id, request_digest, status, job_count }
```

Backed by a durable worker. Submission intent is persisted before provider contact. An unknown timeout is reconciled before retry.

### `render_get`

```ts
render_get({ run_id })
  -> { status, request_digest, jobs }
```

Returns compact job state; raw provider payloads stay in restricted diagnostics.

### `render_promote`

```ts
render_promote({
  run_id,
  expected_request_ref,
  expected_result_binding_revision,
  idempotency_key
}) -> { result_ref, selected_assets, binding_revision }
```

Verifies terminal success, output count, hashes, and request provenance; imports assets and commits the result binding atomically. The calling graph node updates checkpoint state.

### `provider_health`

Runtime/operator tool for liveness/readiness and declared capabilities. It is not exposed to creative agents and must not trigger paid generation as a health check.

## P0: Media Tools

- `media_inspect(asset_id)` returns bounded metadata and model-readable projections.
- `media_import_remote(url, policy, idempotency_key)` performs SSRF-safe, size-limited, MIME-verified import.
- `media_derive_dimensions(modality, aspect_ratio, quality)` is pure and rejects unsupported combinations.
- `montage_execute(timeline_ref, idempotency_key)` runs deterministic ffmpeg assembly and returns a technical result containing the final asset; the calling node validates and commits `MontageResultV1` before updating the graph binding.

## P1: Context And Chunk Tools

### `chunk_validate`

Validates a domain chunk, provenance, rights constraints, referenced assets, and forbidden runtime keys.

### `chunk_resolve`

```ts
chunk_resolve({
  project_id,
  consumer_capability,
  mandatory_refs,
  query?,
  filters?,
  mode: "direct" | "fts" | "hybrid",
  max_context_tokens,
  limit
}) -> {
  index_revision,
  selected_evidence,
  estimated_context_tokens
}
```

Order is direct references, filters, FTS, then optional vector retrieval. It returns compact cited projections, not a permanent context-pack file.

### `chunk_index`

Background operation keyed by chunk/source digest, model, dimension, input format, and chunker version. It replaces obsolete records transactionally and physically isolates test/mock vectors from production.

### `context_estimate`

Estimates the actual agent-context token cost. Embedding dimensionality is not used as a proxy for prompt tokens.

## Admin-Only Operations

- pipeline/capability registry validation;
- source and chunk backfill;
- remote media migration;
- embedding rebuild;
- retrieval evaluation;
- provider workflow registration.

Destructive rebuilds and mock indexing are never agent tools.

## Legacy Extraction

| Legacy script | Preserve | New home |
|---|---|---|
| `state_guard.py` | schema/provenance/gate invariants | validators + graph gates |
| `producer_step.py` | none of the action transport; only route intent | authored graph edges |
| `producer_notify.py` | compact review/progress presentation | pure UI event projector |
| `chunk_resolver.py` | direct-first retrieval and budget | `chunk_resolve` |
| `init_project.py` | validation and no-overwrite rule | `project_create` |
| pipeline compatibility `init_project.py` | no unique capability | delete |
| `render_worker.py` | preflight, per-job resume, concurrency | render service |
| `render.py` | bounded retry classification | worker retry policy |
| `render_wakeup.py` | completion validation and resume intent | job event handler |
| `copy_worker_result.py` | canonical import, hashes, provenance | `render_promote` |
| provider scripts | payload mapping and polling | provider adapters |
| `fal_video_generate.py` | duplicate fal submit/poll/download | delete; fal adapter owns it |
| `estimate_chunk_tokens.py` | context-size estimation | `context_estimate` |
| `craft_cinema_chunk.py` | approved-source projection | Craft node or typed function |
| `backfill_cinema_chunks.py` | migration and remote import | admin backfill + `media_import_remote` |
| `index_chunks.py` / `embed_gemini.py` | embedding/index behavior | index worker + embedding adapter |
| `eval_chunk_retrieval.py` | golden retrieval checks | evaluation suite |
| `validate_chunk_schema.py` | chunk/schema invariants | `chunk_validate` |
| `validate_pipeline_spec.py` / `validate_agent_contracts.py` | spec/capability validation | CI/startup registry validation |

## Do Not Rebuild

- shell command handoffs and wake-up prompts;
- hardcoded `/goal` route maps;
- `producer_state.json`;
- arbitrary `read/write/terminal` agent toolsets;
- provider registries duplicated in Python and JSON;
- `/tmp` context packs as durable truth;
- dynamic imports from user-home Hermes paths;
- output-directory scans as selection logic;
- render resume keyed only by filename or shot ID;
- production `--mock` vectors;
- compatibility forwarders for the unshipped legacy runtime.
