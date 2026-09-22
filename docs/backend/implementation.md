# Backend Implementation Boundaries

Status: **Partial foundation: config/ownership, SQLite preflight/recovery, text DTO/canonical encoding and internal Story v1 storage are implemented and tested on Windows. Review/runtime pending.** Build order and dependencies live in [Local MVP](../roadmap-mvp.md), not here.

## Repository Shape

Create modules only with working responsibilities: `domain`, `repositories`, `services`, `graphs`, `api`, `worker` and application migrations under `backend/`. [Architecture](architecture.md#package-boundaries) owns import/dependency rules. No empty package tree, generic repository interface or per-agent microservice is required.

## Project DB Tables

Logical inventory, not implemented SQL or a mandate to create all future tables:

| Record | Purpose |
|---|---|
| `projects`, `pipeline_snapshots`, `executions` | Workspace, frozen graph/configuration and execution identity/outcome |
| `artifacts`, `assets`, `execution_bindings` | Immutable result metadata and current exact output selection |
| `operations` | Prepared inputs/context, attempts and committed result/transition receipts |
| `review_requests` | Exact reviewed subject, feedback/question/decision and apply identity |
| `execution_work`, `execution_controls` | Durable commands/resumes/reconciliation and cancellation |
| `jobs` and minimal group/attempt records | Generation intent, provider identity/status, verified outputs and lineage |

Node discussion uses accepted review feedback and owner response records; version refs and message identity survive reconnect. No separate chat framework is needed for this bounded interaction. Library `chunk_bindings` and streaming `event_outbox` are later features.

Use scalar columns for identities, constraints and work queries, typed JSON for bounded prepared inputs/policies/results. Start idempotency is unique per project/key; operations per execution/operation; bindings per execution/slot; work per execution/kind/source across all statuses. Review subject and replacement use optimistic concurrency. Concrete schemas and indices are implemented with their actual queries.

## Managed Project Storage

Use one managed local root. SQLite stores identities, decisions, bindings and job records; immutable JSON/media lives in managed files, not media BLOBs or user-written state files. Initial raw request and submitted normalized Brief are saved with the start's identity before execution is exposed. A start reservation, if used for pre-commit file publication, protects both bodies.

Publication, metadata/binding/operation commits and checkpoint writes are not one cross-store transaction. [Artifact protocol](artifacts.md#commit-protocol) owns recovery. No automatic orphan deletion before its pin/commit races are tested.

Local application uses one data-lock-owning process and one graph runner. PostgreSQL is a separate hosted implementation of the same logical rules, not a transparent SQLite compatibility layer. [Runtime](runtime.md) owns work delivery; [startup](local-startup.md) owns safe opening/updating/shutdown.
