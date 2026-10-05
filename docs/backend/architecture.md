# Architecture

Status: **Accepted boundaries; steps 0–2 internal Story foundation tested on Windows, including localhost discussion/revise/approve/retry/cancel and forced-process-death recovery. Connected Pipeline/Chat passed Story UI acceptance 6E after visual approval of the 6F map. The live OpenRouter Storytell text slice of step 3 passed browser/restart smoke on 3 October under its own frozen identity; historical fixture executions remain deterministic. Wardrobe agent/operation/storage are implemented; its graph activation/live verification, public cinematic API, rendering and full frontend step 6 remain pending. Step 3 is not complete. Build checklist/evidence: Local MVP.**

Kinodel is a **runtime-vibe-factory for creators**. A creator follows a pipeline from an idea through story, characters, storyboard and video, or another production scheme, inspecting and revising results through human-in-the-loop decisions. Cinematic is one pipeline, not the definition of the entire product.

## System Shape

```text
Node UI / API → durable commands → LangGraph runner ↔ Checkpointer
                                      │
                            Agent nodes / tool nodes
                                      │
                     Project DB + managed immutable files
                                      │
                       generation jobs → provider adapters
```

Graph coordinates. Agents reason. Tools perform side effects. Artifacts preserve validated results. Humans approve creative direction.

## Target Stack

| Concern | Choice | Boundary |
|---|---|---|
| Backend | CPython 3.13; verified patch 3.13.15 | One local application process |
| Orchestration | LangGraph `StateGraph` | Authored routing, checkpoints, interrupts; no second scheduler |
| Models/tools | Bounded calls; `langchain-core` types where useful | Provider integration only for selected models; no required Deep Agents/tool-loop framework |
| API / validation | FastAPI, Pydantic v2, Uvicorn ASGI server | Typed commands and reads, no graph invocation inside HTTP handlers |
| Local persistence | SQLite application records + `AsyncSqliteSaver` | Separate business/checkpoint ownership, even if files share one root |
| Media | Managed immutable files; generation tools and ffmpeg | Provider-specific payloads/transport stay in adapters |
| UI | React, TypeScript, Vite, React Flow UI + Tailwind/shadcn, typed HTTP client | Pipeline/Chat views and fixed nested-node inspection; graph editing and executable composition later |
| Hosted profile | PostgreSQL + PostgreSQL saver; Supabase identity, private GCS | Separate activation, not local installation dependencies |

Installed versions, missing dependencies, installation commands and release checks belong to [Local MVP](../roadmap-mvp.md#repository-and-dependencies), not this architecture. No ORM, Redis, Celery, event bus, generic plugin system or LangGraph Agent Server is required by these boundaries.

## Ownership

| Layer | Owns | Does not own |
|---|---|---|
| UI/API | Inputs, node inspection, review commands, progress | Routing or direct artifact writes |
| LangGraph | Finite transitions, waits, checkpoint projection | Media bytes, business truth, provider execution history |
| Agent | Creative result, semantic generation request, response to feedback | Approval, next edge, credentials or durable writes |
| Tool/adapter | Validated side effects, job submission, import, montage | Independent creative decisions or approval |
| Project DB / files | Immutable output revisions, bindings, jobs, feedback, decisions, receipts | Checkpoint scheduling position |
| Checkpointer | Execution state and pending tasks/resume values | Project library or implicit approval |

Each new logical output has one declared writer. A creative owner can have a generation tool publish media on its behalf; this does not create competing bindings. Downstream gets explicit selected result refs and prepared context, never an upstream conversation dump.

## Runtime Boundaries

Local API and one graph runner share one process holding the data-directory lock. API transactions accept commands into durable work; only the runner invokes LangGraph. Provider jobs persist separately so generation can continue while no graph invocation or model call is active. Browser disconnection does not cancel accepted work.

Business commits and checkpoints are separate. An operation records prepared inputs and its committed result; replay returns that result rather than repeating the effect. External submission may remain ambiguous after a lost response and must be reconciled, not blindly retried. Details belong to [runtime](runtime.md), [artifacts](artifacts.md) and [tools](../tools/tools.md).

Human approval, direct edits and questions follow the [HITL contract](../hilp/hilp.md). Cancellation is durable and prevents later creative commits; checkpoint rewind cannot mutate production history.

## Package Boundaries

Use modules for actual responsibilities, not empty scaffolding:

- `domain`: types and pure validation; no provider/HTTP/database imports.
- `repositories`: short transactions, immutable-file publication and read projections.
- `services`: context, model/tool adapters and application operations; no creative routing.
- `graphs`: authored stages and finite routes using domain/services.
- `api`: authorized command/read handlers. `worker`: invocation, recovery and tool-job lifetime.

Application migrations and checkpointer setup have separate ownership. Use concrete functions until real duplication warrants an abstraction. [Implementation](implementation.md) records storage layout; [Local MVP](../roadmap-mvp.md) owns build order.

Frontend organization is separate from these Python modules: `web/` builds a React/TypeScript/Vite Story workspace served from the FastAPI origin, with validated queries, fixed React Flow scopes, shared reader/review drafts and persist-before-POST exact command delivery. Receipts confirm acceptance; projections own progress/results. The standalone mock lives in `web/prototype/`; its binary photos remain in `web/assets/` and are not bundled into the client. [FSD](../frontend/fsd.md) owns client layout/import/state boundaries; [Web UI](../frontend/webui.md) owns interaction and visual contracts.

## Configuration Boundary

Run freezes submitted brief/settings, graph version, selected resources and supported profiles. Operation preparation pins available exact inputs/context; job preparation pins provider payload/seeds. Future generated outputs need not exist at Run. Editing an active review uses its fixed owner; changing the pipeline, submitted brief or approved ancestors starts a new execution.

Keep model limits, provider capabilities and instruction versions explicit. Credentials resolve separately in trusted adapters, never in creative artifacts or public tool arguments. Node layout is presentation, not an execution change. See [pipeline](pipeline.md) and [context](../context/context.md).

## Data Stores

| Store | Canonical content |
|---|---|
| Checkpointer | Graph position, compact state, pending writes |
| Project DB | Executions, operations, output bindings, jobs, reviews, feedback and controls |
| Managed files | Immutable JSON/media and isolated attempts |

Search indexes are derived and optional. Hosted and local implementations share logical rules, not interchangeable SQL/locks. Local project data is not uploaded by registration; remote generation receives only selected authorized inputs. Hosted identity/storage/billing policy remains in [database contracts](../database/README.md).

## Trust Boundaries

Validate model/client input, exact result ownership, required context and provider outputs. References grant no permissions by themselves. Local API uses loopback, Host/Origin/session and CSRF protection; CORS alone is insufficient. Agents have no arbitrary filesystem or endpoint access. Retrieved text is data, not trusted instructions.

Startup preserves existing data and releases ownership only after writers stop. Provider callbacks are hints, never permission to approve or advance. [Local startup](local-startup.md) owns process rules; all first-build implementation and acceptance gates live in [Local MVP](../roadmap-mvp.md).
