# Backend Implementation Plan

Status: **Decided foundation**

This is the smallest real backend shape. It makes no assumption about a microservice fleet or a generic pipeline compiler.

## Repository Shape

```text
backend/
  api/             FastAPI routes and Pydantic request/response DTOs
  graphs/          explicit StateGraph factories and node functions
  domain/          artifact schemas, validators, pipeline declarations
  services/        agent adapters, render adapter, montage adapter, retrieval
  repositories/    PostgreSQL transactions and object-store access
  worker/          execution-work claim, graph invocation and recovery; later provider jobs
  migrations/      Project DB migrations; LangGraph saver setup is deployment-owned
```

Keep the API and worker as separate Python process entry points that import the same domain and service code. Do not create a service per agent, provider, or pipeline.

## Project DB Tables

| Table | Purpose |
|---|---|
| `projects` | workspace identity and authorization boundary |
| `pipeline_snapshots` | frozen pipeline ID, version, digest, and registered graph compatibility |
| `executions` | execution lifecycle, thread ID, lease fence, start idempotency, failure summary |
| `artifacts` | immutable metadata, schema, digest, object URI, provenance |
| `assets` | immutable metadata and managed URI for promoted image, video, audio, and document files |
| `execution_bindings` | current exact artifact per `(execution_id, slot)` and binding revision |
| `chunk_bindings` | active approved artifact revision and status for each reusable logical chunk subject |
| `operations` | logical attempt revision, idempotency key, input/context digest, context trace, and committed result map |
| `review_requests` | review card identity, digest, status, and submitted decision |
| `execution_work` | durable start/resume/reconcile/cancel segments, claims, retries, and settlement |
| `jobs` | provider operation state, idempotency, audit payload, output promotion |
| `execution_controls` | cancellation and later operator controls |
| `event_outbox` | deferred normalized API event publication |

Unique constraints enforce start idempotency within a project, `(execution_id, slot)` for execution bindings, one active revision per logical chunk subject, `(execution_id, operation_id)` for operations, `(execution_id, gate_id, request_revision)` for reviews, one pending review request per execution in V1, and `(execution_id, kind, source_id)` for work across all statuses. Graph business commits verify the current lease fence and cancellation under an execution-row lock. API command transactions authorize and validate expected revisions under short row locks; they do not acquire graph ownership. Artifact metadata, binding replacement, operation success, and next activation commit in one transaction. `execution_start` creates the immutable `initial_request` artifact and binding with the execution and unique start work, before the first graph call.

This is a target table inventory, not a requirement to migrate all production tables in foundation. Assets/jobs arrive with rendering, chunk bindings with memory, and the event outbox with streaming. The first slice includes `execution_work` and `execution_controls` from its first accepted execution. [runtime.md](runtime.md) owns claim, recovery, cancellation, and segment-settlement semantics.

## Managed Project Storage

Start with one backend-managed local root. Object names are server-generated from immutable IDs and content digests. Store artifact JSON, promoted assets, render attempts, and restricted job audit separately. Database records, never filesystem paths or provider URLs, establish identity and canonical selection. No downstream stage discovers work by scanning folders. S3-compatible storage is added only when a remote deployment needs it.

## Implementation Order

Pre-build prerequisite: complete the semantic contracts for **all catalog agents and service boundaries**, with full cinematic handoffs, repair outcomes, context/media requirements, and craft acceptance cases in [agents/](../agents/README.md). This is broader than the first graph. The backend uses a static versioned capability/mode registry and the same prepared-input/validated-output boundary for every enabled role; no special runtime built around three agent names. Unimplemented capabilities stay unavailable rather than becoming fake runnable stubs.

1. Finish executable foundation contracts and the exact route table: opening request, Brief, Story, state/refs, review/input decisions, Critic/revision outcomes, work/controls, and `ContextSelectionV1`. Specify settings freeze and loop limits before encoding them.
2. Migrate foundation Project DB tables and implement managed-file publication, idempotent operations, and atomic command/work transactions. Include project access checks, path isolation, validation, and credential separation; do not wait for product hardening.
3. Implement the direct context resolver and Producer/Storytell/Critic projections before their model calls. Persist an exact selection, even with no optional attachments; no search or vector dependency.
4. Implement the authored `foundation.v0` graph and activate Producer/Storytell/Critic through those shared capability boundaries: brief proposal -> review/critic/clarification loop -> story proposal -> review/critic/clarification loop -> explicit completion, with cancellation checks at commit boundaries. This tests the runtime, not the completeness of the cinematic crew. Other agents' schemas/adapters are enabled against their already-defined contracts as their stages arrive.
5. Add execution/status/review/cancel endpoints and the single `execution_work` worker together. API transactions only accept commands; the worker alone starts, resumes, recovers, and finalizes cancellation. Work remains recoverable until a stable pause, block, or terminal outcome, not merely decision consumption.
6. Integrate `AsyncPostgresSaver` on the invocation's advisory-lock-owning connection per [runtime.md](runtime.md#single-writer-ownership). In-memory graph tests are development checks, not proof of restart safety; verify same-session checkpoint writes against pinned versions before claiming this guarantee.
7. Run the [runtime acceptance matrix](runtime.md#acceptance-matrix) applicable to foundation on real PostgreSQL with process termination. Include start-before-invoke, commit-before-checkpoint, consumed-answer/unfinished-next-node, stale/duplicate decisions, live-lock ownership, cancellation races, and pinned-context recovery. Provider-job cases arrive with rendering.

No legacy TypeScript script is ported wholesale. Extract a typed capability only when a pipeline stage needs it.
