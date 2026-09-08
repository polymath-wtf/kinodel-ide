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
  worker/          database-job claim, provider reconciliation, resume scheduler
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
| `execution_resumes` | durable one-shot resume intent from a review or terminal job |
| `jobs` | provider operation state, idempotency, audit payload, output promotion |
| `execution_controls` | cancellation and later operator controls |
| `event_outbox` | deferred normalized API event publication |

Unique constraints enforce start idempotency within a project, `(execution_id, slot)` for execution bindings, one active revision per logical chunk subject, `(execution_id, operation_id)` for operations, `(execution_id, gate_id, request_revision)` for reviews, one pending review request per execution in V1, and one unclaimed resume per control source. Every execution-scoped mutation verifies the current lease fence. Artifact metadata, binding replacement, and operation success commit in one transaction. `execution_start` creates the immutable `initial_request` artifact and binding with the execution, before the first graph call.

## Managed Project Storage

Start with one backend-managed local root. Object names are server-generated from immutable IDs and content digests. Store artifact JSON, promoted assets, render attempts, and restricted job audit separately. Database records, never filesystem paths or provider URLs, establish identity and canonical selection. No downstream stage discovers work by scanning folders. S3-compatible storage is added only when a remote deployment needs it.

## Implementation Order

1. Create Pydantic DTOs for `InitialRequestV1`, `PipelineRef`, `ArtifactRef`, `BindingRef`, `ExecutionStateV1`, `ReviewRequest`, and `ReviewDecision`.
2. Migrate Project DB tables and managed project-storage repository.
3. Implement explicit `foundation.v0` Python graph: brief proposal -> gate/critic loop -> story proposal -> gate/critic loop.
4. Add FastAPI execution/status/review endpoints and an in-memory test checkpointer.
5. Prove replay after each commit boundary and duplicate review resume.
6. Verify `AsyncPostgresSaver` checkpoint writes use the invocation's advisory-lock-owning connection; add a minimal fence-aware saver wrapper only if required.
7. Add the one DB resume worker before any render provider.

No legacy TypeScript script is ported wholesale. Extract a typed capability only when a pipeline stage needs it.
