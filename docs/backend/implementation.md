# Backend Implementation Plan

Status: **Decided foundation**

Deployment decision: SQLite local / PostgreSQL server. The [profiles](../database/local-vs-hosted.md) share the logical project/execution/artifact entity model, not interchangeable SQL, locks or migrations. Table names below are a logical target inventory; no tables or migrations are implemented by this plan. Checkpointer implementations for both profiles remain #todo. Do not add a transparent DB compatibility abstraction without a demonstrated requirement.

This is the smallest real backend shape. It makes no assumption about a microservice fleet or a generic pipeline compiler.

## Repository Shape

Target layout, not existing folders. Create modules only with implemented responsibilities; [package dependency rules](architecture.md#package-boundaries) apply. This is a modular Python backend, not frontend FSD.

```text
backend/
  api/             FastAPI routes and Pydantic request/response DTOs
  graphs/          explicit StateGraph factories and node functions
  domain/          artifact schemas, validators, pipeline declarations
  services/        agent adapters, render adapter, montage adapter, retrieval
  repositories/    SQLite local / PostgreSQL server transactions and managed storage access
  worker/          execution-work claim, graph invocation and recovery; later provider jobs
  migrations/      Project DB migrations; LangGraph saver setup is deployment-owned
```

Server API and workers have separate process entry points sharing domain/services. Local API and a single background graph runner live in one application process holding exclusive data-directory ownership. Do not create a service per agent, provider, or pipeline.

## Project DB Tables

The following 13 entities are the same logical schema in local SQLite and server PostgreSQL where the feature is enabled. Physical types, constraints, transactions and migration ownership must be verified per engine. Chat persistence is accepted as a product requirement, but chat/event/attachment table names and edit/partial schema remain Q10; they are not silently added to this inventory or to the nine-table text foundation.

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

Unique constraints enforce start idempotency within a project, `(execution_id, slot)` for execution bindings, one active revision per logical chunk subject, `(execution_id, operation_id)` for operations, `(execution_id, gate_id, request_revision)` for reviews, one pending review request per execution in V1, and `(execution_id, kind, source_id)` for work across all statuses. Graph business commits verify current fence and cancellation with execution-row locking on PostgreSQL or serialized short write transactions on SQLite. API command transactions authorize and validate expected revisions under the same profile-specific serialization; they do not acquire graph ownership. Artifact metadata, binding replacement, operation success, and next activation commit in one transaction. `execution_start` creates the immutable `initial_request` artifact and binding with the execution and unique start work, before the first graph call.

This is a target table inventory, not a requirement to migrate all production tables in foundation. Assets/jobs arrive with rendering, chunk bindings with memory, and the event outbox with streaming. The first slice includes `execution_work` and `execution_controls` from its first accepted execution. [runtime.md](runtime.md) owns claim, recovery, cancellation, and segment-settlement semantics.

## Managed Project Storage

Start with one backend-managed local root for local projects. Object names are server-generated from immutable IDs and content digests. Store artifact JSON, promoted assets, render attempts, and restricted job audit separately. Database records, never filesystem paths or provider URLs, establish identity and canonical selection. No downstream stage discovers work by scanning folders. Kinodel endpoint uses private GCS, verified uploads and authorized signed downloads; no S3 compatibility layer. See [endpoint storage](../database/credits-billing.md#результат-удалённого-рендера).

## Implementation Order

Pre-build prerequisite: complete the semantic contracts for **all catalog agents and service boundaries**, with full cinematic handoffs, repair outcomes, context/media requirements, and craft acceptance cases in [agents/](../agents/README.md). This is broader than the first graph. The backend uses a static versioned capability/mode registry and the same prepared-input/validated-output boundary for every enabled role; no special runtime built around three agent names. Unimplemented capabilities stay unavailable rather than becoming fake runnable stubs.

1. Implement and test the proposed [physical DTOs](physical-dtos.md) and exact foundation routes: opening request, Brief, Story, state/refs, review/input decisions, Critic/revision outcomes, work/controls, and `ContextSelectionV1`. The existing nine-table text inventory is logical; proposed `execution_start_reservations` is an additional physical Q8 table, not already implemented. Do not add every future media/billing table to foundation.
2. Migrate foundation Project DB tables and implement managed-file publication, idempotent operations, and atomic command/work transactions. Include project access checks, path isolation, validation, and credential separation; do not wait for product hardening.
3. Implement the direct context resolver and Producer/Storytell/Critic projections before their model calls. Persist an exact selection, even with no optional attachments; no search or vector dependency.
4. Prove the text-only Brief/Story review/repair path as an internal runtime test milestone, with cancellation checks at commit boundaries. The deployable `foundation.v0` follows [foundation routes](reviews.md#foundation-routes) through Wardrobe visual-plan review, Storyboard main-frame planning, one durable ComfyUI job, verified import/join, candidate review and promotion before completion. Activate those five capabilities through the common contract, not special runtime branches around agent names. Separate test graph identity from the production snapshot; never change an open thread's factory to append rendering.
5. Add execution/status/review/cancel endpoints and the single `execution_work` worker together. API transactions only accept commands; the worker alone starts, resumes, recovers, and finalizes cancellation. Work remains recoverable until a stable pause, block, or terminal outcome, not merely decision consumption.
6. #todo Integrate SQLite checkpointer under exclusive local application ownership and PostgreSQL `AsyncPostgresSaver` on the invocation's advisory-lock-owning connection per [runtime.md](runtime.md#single-writer-ownership). Pin and verify each saver, including pending writes; the common interface is not proof of recovery compatibility.
7. #todo Run the [runtime acceptance matrix](runtime.md#acceptance-matrix) on real SQLite with process termination before local release; PostgreSQL passes its own matrix before hosted activation, not as a local-only blocker. Include start-before-invoke, commit-before-checkpoint, consumed-answer/unfinished-next-node, stale/duplicate decisions, profile-specific ownership, cancellation races and pinned-context recovery. Automatic local setup follows [local-startup.md](local-startup.md); backup/RPO/RTO are #future production.
8. For the first deployable rendered slice, implement Wardrobe/Storyboard main-mode DTOs/resources, direct media projections, `assets`/`jobs` plus the minimal Q13 physical group/candidate records, pinned workflow mapping, external wait and selection/promotion. Pass lost-response, fast-result, duplicate-wake, invalid import and late-cancel checks before declaring the local build ready. Full storyboard frames/video/montage/memory and [rework entry](rework.md) remain later activations.

No legacy TypeScript script is ported wholesale. Extract a typed capability only when a pipeline stage needs it.
