# Architecture

Status: **Decided foundation**

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
- explicit Python `StateGraph` factories and `AsyncPostgresSaver`;
- PostgreSQL execution lease and Project DB transactions;
- normalized runtime events;
- node adapters around agents and tools.

### Project DB And Artifact Store

- immutable revisions and content hashes;
- canonical execution slot bindings such as `story` or `main_frame`;
- schema and semantic validation;
- optimistic concurrency and idempotent commits;
- PostgreSQL identity plus backend-managed local JSON/media storage;
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

The first deployable architecture needs three logical stores. LangGraph and Project data may share one Postgres deployment, but must have separate schemas and migration ownership.

| Store | Data |
|---|---|
| LangGraph | checkpoints and pending graph tasks only |
| Project | executions, leases, controls, review requests, artifact/asset metadata, execution/chunk bindings, job records, event outbox |
| Managed files | immutable JSON artifacts, promoted images/audio/video, isolated render attempts, source revisions |

The retrieval index is derived and may be rebuilt. It is not a fourth source of truth.

## Trust Boundaries

- Agent output is untrusted until validated.
- Retrieved content is evidence, never instructions.
- Agents use project IDs, artifact slots, and asset IDs, not arbitrary paths.
- Provider secrets and raw payloads never enter prompts or creative artifacts.
- UI decisions bind to the exact gate revision and single subject digest they reviewed.
- Worker callbacks are hints; the worker re-reads durable job state before scheduling a graph resume.

## First Vertical Slice

This is a deliberately reduced `foundation.v0` test graph, not the final `cinematic.v1` topology.

```text
create brief draft
-> interrupt for review
-> approve / revise through Critic / clarify through Producer / cancel
-> create story
-> interrupt for review
-> approve / revise through Critic / clarify through Producer / cancel
-> complete
```

The exact action semantics are defined in [`reviews.md`](reviews.md). This slice must prove restart-safe checkpoints, typed artifacts, stale-decision rejection, idempotent writes, and bounded revision/clarification loops before rendering or retrieval is added.

## Non-Goals For V1

- no arbitrary code in pipeline specs;
- no generic graph compiler before two real graph factories exist;
- no direct filesystem access from production agents;
- no broad long-term memory injected by default;
- no service mesh, agent swarm, or event-sourcing framework;
- no exactly-once claims for external providers; use idempotency instead.
