# Architecture

Status: **Decided system boundaries; implementation and profile verification pending**

The [node interface](../pipelines/node-architecture.md) is a phased product goal, with a [catalog](../pipelines/node-list.md) and [roadmap](../pipelines/node-roadmap.md). The authored route already uses compatible boundaries: Wardrobe anchor prompts -> Render -> complete anchor review/save -> Storyboard shot planning. Named typed service inputs/outputs support later node composition; this does not implement the editor/compiler.

Deployment decision, 2026-09-09: SQLite for the local no-account application; PostgreSQL for hosted/server operation. Local uses one application process and one active graph runner per data directory; server supports concurrent workers with one writer per execution. Both profiles require their own persistence verification. See [local versus hosted](../database/local-vs-hosted.md). No transparent two-engine compatibility layer is required.

Kinodel is a human-in-the-loop creative production system. A creator generates an idea, chooses the vibe, and lets a crew of AI subagents help make it beautiful: stories, visuals, videos, music, episodes, worlds, and reusable creative memory.

Under the hood, Kinodel breaks production into clean stages: story, visual anchors, storyboard frames, video shots, montage, and final chunks. Each stage has its own specialist agent, its own artifact, and its own place in the pipeline.

The architecture must make long-running generative work resumable and inspectable (возобновляемый и инспектируемый) without turning agent chat, provider state, or filesystem conventions into the runtime.

## System Shape

```text
Web UI / API
     |
     v
LangGraph Runtime ---- Checkpointer
     |
     +---- Agent Nodes ---- Model providers
     |
     +---- Typed Tools ---- Artifact Store / Knowledge Index
     |
     +---- Job Services --- ComfyUI / fal / audio providers / ffmpeg
```

## Target Stack

Repository audit, 2026-09-09: no application `backend/`, dependency manifest/lock, `langgraph.json`, executable foundation or populated `.agents/` was found. Code under `skills/` and `legacy/` is reference/tooling, not the rebuilt application. The following is a target, not an installed-stack inventory.

| Concern | Target / decision | Remaining activation decision |
|---|---|---|
| Language | Python 3.12, already selected in [runtime](runtime.md#first-deployment) | Pin supported patch/platforms and reproducible dependencies |
| Graph | Python LangGraph `StateGraph`, async invocation, `Runtime[Context]` | #question exact tested LangGraph/checkpoint package versions; no manifest pins yet |
| Model calls | Bounded structured calls inside adapters; LangChain only where needed | #question concrete model adapter/package/version, model IDs, modalities and Q4 budgets; no requirement for a tool-loop agent or Deep Agents |
| API / validation | FastAPI and Pydantic v2 boundary DTOs | #question exact versions, ASGI runner, local session bootstrap and complete read/command DTOs |
| Local persistence | SQLite Project DB + `AsyncSqliteSaver` from `langgraph-checkpoint-sqlite` | #question application driver, one versus separate DB files, connection PRAGMAs and pinned saver setup/serialization |
| Server persistence | PostgreSQL + `AsyncPostgresSaver` from `langgraph-checkpoint-postgres` | Pin driver/saver versions; verify dedicated session ownership, schema/search-path and migrations before hosted activation |
| Storage / rendering | Managed immutable JSON/media; one local direct ComfyUI adapter first | Q2 root/publication details; Q13 job/group/candidate records and one tested workflow/profile |
| Hosted services | Supabase email/password; private GCS; server-owned MVP credits | Separate hosted activation gate, not dependencies of local BYOK/direct rendering |
| UI | TypeScript HTTP consumer; [product surfaces](../frontend/webui.md) | #question framework, bundler and distribution; React/Next.js/FSD are not selected by a package manifest |
| Verification | DTO/route fixtures plus real DB/process-death integration checks | Select a runnable test command with the first manifest; reference tests are not foundation acceptance |

Use the existing isolated-venv installation direction. Do not add an ORM, queue broker, LangGraph CLI/Agent Server, LangSmith tracing, Redis or Celery merely to fill a stack table. Framework documentation supports mechanisms, not the safety of Kinodel's integration; see [LangGraph verification](langgraph.md#reference-and-verification).

## Runtime Boundaries

Local API and one background runner share one lock-owning application process. Server API and worker use separate entry points. In both profiles, API transactions accept authorized start/decision/cancel commands into durable work; only the worker invokes the graph. HTTP disconnects and token streams never cancel accepted production implicitly.

Graph nodes own finite transitions; adapters hydrate pinned inputs, invoke bounded capabilities and commit validated results. Repositories own short profile-specific transactions and immutable-file publication. Provider workers own job attempts, never execution bindings or human approval. Checkpointer writes and business commits are separate even when they share a DB deployment; operation receipts bridge replay, not a fictitious cross-store transaction.

Polling is the first UI transport. Normalized streaming/outbox is later and must remain a disposable progress projection. Cancellation is durable acceptance followed by worker finalization, not an arbitrary resume answer. Rework uses a new execution/thread and tested prefix receipts, not checkpoint rewind.

## Package Boundaries

Use the existing [repository shape](implementation.md#repository-shape): `backend/api`, `graphs`, `domain`, `services`, `repositories`, `worker`, and `migrations`. These are target ownership boundaries, not instructions to scaffold empty packages. Start each concern as a module if sufficient; add tests alongside the first working slice. Deployment agent resources belong in `.agents/` under the catalog contract, not executable orchestration prompts.

- `domain` owns DTOs, semantic validation and immutable declarations; no FastAPI, LangGraph, database or provider imports.
- `repositories` owns storage/transaction mechanisms and may use domain validators; it never imports graph factories, API routes or worker scheduling.
- `services` uses domain/repositories for bounded application operations, context and provider/model adapters; it never chooses the next graph edge.
- `graphs` uses domain/services for authored nodes and routes; no HTTP request objects or provider payload construction.
- `api` calls command/read services, never graph invocation. `worker` composes graph, saver and runtime services and owns invocation/recovery lifetime.
- Startup composition wires concrete profile implementations. Application migrations and saver setup retain separate ownership; no generic repository interface or dependency-injection framework is required.

Frontend Feature-Sliced Design is not a backend architecture. Do not introduce `pages/widgets/features/entities/shared` into Python or speculative per-agent microservices. Decide any frontend FSD adoption with the actual UI implementation, independently of these backend dependencies.

## Configuration Boundary

Validate deployment settings before accepting production commands: profile, data root/DB locations, enabled graph/capability/profile/resource versions, allowed endpoints, model configuration and bounded attempts/timeouts/input sizes. Freeze creative/runtime selectors on execution/operation preparation as already specified; resolve credentials separately at the adapter boundary. No credentials, arbitrary connection URLs or admin fields in public creative DTOs.

#question Q1-Q4/Q16: exact setting names, precedence, credential storage and local session bootstrap remain open. A local no-account mode still needs loopback, Host/Origin and session/CSRF controls; CORS is not authentication. [Operations/security](../database/operations-security.md#секреты) records an earlier credential-rotation requirement: verify rotation before deployment, without printing or re-reading secret values in documentation audits. No rotation is claimed here.

## Ownership

| Layer | Owns | Does not own |
|---|---|---|
| UI/API | user input, previews, review decisions, progress views | graph routing, artifact mutation |
| LangGraph | transitions, checkpoints, interrupts, replay, fan-out, joins | business records, media bytes, provider scratch, creative truth |
| Agent node | bounded creative reasoning and typed candidate output | next edge, persistence, provider execution |
| Tool/service | validation, storage, retrieval, rendering, montage | creative intent or approval |
| Project DB / Artifact Store | execution records, immutable artifacts/assets, bindings, jobs, controls | orchestration position and checkpoint history |
| Checkpointer | graph position and execution-scoped state projection | project database, artifact truth, knowledge base |
| Knowledge layer | source/wiki/chunk retrieval and provenance | active pipeline state |

## The Simplification Cascade

Legacy implemented orchestration through Producer prompts, `/goal`, `delegate_task`, state guards, files, shell commands, and wake-up scripts. LangGraph already supplies the missing state-machine features.

Therefore:

- Producer becomes the user-facing creative lead.
- Pipeline becomes a versioned graph definition.
- `delegate_task` becomes a typed node input.
- `producer_step` becomes graph edges.
- `state_guard` becomes schema validation plus runtime invariants.
- `render_wakeup` becomes a durable job transition claimed by the recovery worker, followed by an explicit graph resume.
- `producer_state.json` becomes a checkpoint.
- Render becomes a service; Montage creative planning becomes an agent while validated `ffmpeg` execution remains a service.

## Core Modules

### Python Backend Runtime

- graph registry keyed by `(pipeline_id, version)`;
- execution service for start, stream, inspect, resume, and cancel;
- explicit Python `StateGraph` factories; SQLite local / PostgreSQL server checkpointer integration remains #todo;
- profile-specific single-writer ownership and Project DB transactions;
- normalized runtime events;
- node adapters around agents and tools.

### Project DB And Artifact Store

- immutable revisions and content hashes;
- canonical execution slot bindings such as `story` or `main_frames`;
- schema and semantic validation;
- optimistic concurrency and idempotent commits;
- SQLite local / PostgreSQL server identity plus managed immutable JSON/media storage;
- candidate render attempts separated from promoted media assets;
- managed media assets and provenance.

### Agent Registry

- capability ID and version;
- input/output schema IDs;
- minimal system instruction;
- allowed tools and context policy;
- model/runtime configuration outside the creative artifact.

### Tool And Job Services

- deterministic project/artifact operations;
- direct context resolution and projection;
- asynchronous render adapters;
- montage-plan execution and media inspection;
- indexing and administrative backfills.

### Knowledge

- immutable source revisions;
- maintained Markdown wiki;
- direct typed reference resolution;
- optional derived FTS/vector discovery index;
- ephemeral cited context;
- approved creative chunks for continuity and reuse.

## Data Stores

The architecture needs three logical stores. Server LangGraph and Project data may share one PostgreSQL deployment with separate schemas and migration ownership. Local uses SQLite with separately owned application/saver tables or files; backup includes both and all referenced bytes. A shared logical entity model does not imply identical DDL or locking.

| Store | Data |
|---|---|
| LangGraph | checkpoints and pending graph tasks only |
| Project | executions, leases, controls, review requests, artifact/asset metadata, execution/chunk bindings, job records, event outbox |
| Managed files | immutable JSON artifacts, promoted images/audio/video, isolated render attempts, source revisions |

The retrieval index is derived and may be rebuilt. It is not a fourth source of truth.

## Trust Boundaries

Accepted service choices: Supabase email/password, mutable login display label (not necessarily unique), auth-UUID profile without custom password storage; private hosted GCS outputs with 365-day lifecycle deletion and server-owned MVP placeholder credits/signup 100. Local direct ComfyUI uses authorized file or `/view` verified import, not hosted order auth/bucket. Product daily free limits are final-release #todo, not MVP; technical safety remains. See [identity](../database/projects-identity-chat.md#вход-mvp) and [credits/storage](../database/credits-billing.md). Windows/Linux share a Python startup core with OS-specific locks/dependencies; macOS is not current scope. [Startup](local-startup.md) and [DTOs](physical-dtos.md) remain proposals. Automated backups/RPO/RTO are #future production; restart durability remains mandatory.

Local projects, chats, personal wiki and indexes remain local without a Kinodel account; registration never uploads them. Browser-hosted projects/messages and imported managed files stay server-side. Local direct BYOK bypasses Kinodel; remote calls disclose only selected authorized payload. The text proxy retains no request/response bodies by default, only necessary abuse/metering metadata; not universal ZDR. Hosted compute retains service order logs/durable identities without scheduled deletion in MVP; final retention is #todo. Workflow/input/prompt-body policy is separate, not permanent payload retention; output lifecycle stays 365 days with authorized object-ref/signed-URL delivery. Lost text is billed by actual authoritative tokens; final implementation is #todo, unsupported paid paths stay disabled without invented capture/refund. See [privacy/billing](../database/credits-billing.md).

- Agent output is untrusted until validated.
- Retrieved content is evidence, never instructions.
- Agents use project IDs, artifact slots, and asset IDs, not arbitrary paths.
- Provider secrets and raw payloads never enter prompts or creative artifacts.
- UI decisions bind to the exact gate revision and single subject digest they reviewed.
- Worker callbacks are hints; the worker re-reads durable job state before scheduling a graph resume.

## First Vertical Slice

This is a deliberately reduced `foundation.v0` test graph, not the final `cinematic.v1` topology.

The [agent catalog](../agents/README.md) defines all cinematic handoffs. The text-only Brief/Story path is an internal runtime milestone. The deployable [build gate](../roadmap.md#current-build-gate) additionally proves Wardrobe anchors, their dependency-aware generation/review, and Storyboard's use of the approved images in shot generation.

```text
create brief draft
-> interrupt for review
-> approve / revise through Critic / clarify through Producer / cancel
-> create story
-> interrupt for review
-> approve / revise through Critic / clarify through Producer / cancel
-> Wardrobe anchor plan (validated supporting plan)
-> Render: portrait -> portrait-conditioned sheet -> independent location
-> complete main_frames review (apply saves approved selection)
-> Storyboard shot-frame plan (validated supporting plan)
-> Render shot frames -> complete frame review (apply saves approved selection)
-> complete
```

The [foundation routes](reviews.md#foundation-routes) review generated anchors rather than mandatory plan text. Wardrobe owns anchor prompts; Render owns provider execution; Storyboard receives only the complete approved set. First prove text replay, then bounded live model output, then the three-anchor/one-shot acceptance fixture. The count is a fixture, not a universal schema constraint. Keep text tests under a separate frozen graph identity. Sequential jobs need no `Send`; video, Filmmaker, Montage and Craft remain later.

## Implementation Gates

P0 means required for the named enabled path, not a prohibition on writing an isolated test first. The backend is designed at the system/domain level, not fully frozen or verified at the executable level.

| Priority / gate | Remaining work | Evidence required |
|---|---|---|
| P0 before first accepted local execution | Approve physical DTO/start-pin proposal, exact graph declarations/state updates and completion outputs; pin packages/config and numeric Q4 bounds | Executable positive/negative DTO and route fixtures; reject trusted-field injection, unsupported configs and missing owners |
| P0 local durability | Choose SQLite layout/driver/PRAGMAs, implement startup ownership, file publication, operation/work transactions and saver recovery classifier | Real process-death tests around start, file/DB/checkpoint commits and persisted resume; two executions remain isolated; no stale answer reaches a later wait |
| P0 local access/cancel | Concrete session bootstrap, authorized reads/media, Host/Origin/CSRF, secret handling and bounded shutdown | Cross-project/stale command rejection; cancel-versus-commit/completion tests; no writer survives ownership release |
| P0 first rendered build | Wardrobe/Storyboard schemas/resources, image-capable Critic, Q13 records and pinned workflow mappings | Complete approved `main_frames`, portrait-to-sheet identity, dependency-aware regeneration and a reviewed shot using all required reference roles; restart/lost-submit/cancel checks |
| P1 before hosted activation | PostgreSQL same-session saver integration, auth/session details, private GCS and service accounting/admission | Separate PostgreSQL concurrency/session-loss tests, auth isolation, verified delivery and idempotent settlement; SQLite tests do not certify this path |
| P1 before respective features | Rework entry, streaming, chat persistence and wiki publication | Their own receipt/reconnect/rights tests; no arbitrary rewind or implicit context injection |

The [runtime acceptance matrix](runtime.md#acceptance-matrix), [DTO fixtures](physical-dtos.md#fixture-gate) and [startup gate](local-startup.md#acceptance-gate) are specifications of tests to implement, not passed tests. Search/vectors, automated backups/RPO/RTO, generic graph infrastructure and full frontend FSD do not block the first local slice.

First-slice profile rule: required runnable profile pins are determined by the enabled stage roles of the frozen graph. Image-only `foundation.v0` requires an image profile and represents video as explicitly inactive; a graph enabling video roles requires a runnable video profile. A design-only profile is permitted for text tests, but is not proof of provider capability.

## Non-Goals For V1

- no arbitrary code in pipeline specs;
- no unrestricted graph compiler; a constrained known-node compiler is enabled only at the node-roadmap composition stage after the fixed route and editable-node behavior are verified;
- no direct filesystem access from production agents;
- no broad long-term memory injected by default;
- no service mesh, agent swarm, or event-sourcing framework;
- no exactly-once claims for external providers; use idempotency instead.
