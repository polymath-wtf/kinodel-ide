# Architecture

Status: **Decided foundation**

Kinodel is a human-in-the-loop creative production system. The architecture must make long-running generative work resumable and inspectable without turning agent chat, provider state, or filesystem conventions into the runtime.

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
| LangGraph | transitions, checkpoints, interrupts, retries, fan-out, joins | media bytes, provider scratch, creative truth |
| Agent node | bounded creative reasoning and typed candidate output | next edge, persistence, provider execution |
| Tool/service | validation, storage, retrieval, rendering, montage | creative intent or approval |
| Artifact Store | immutable validated artifacts and assets | orchestration position |
| Checkpointer | execution-scoped graph state | project database or knowledge base |
| Knowledge layer | source/wiki/chunk retrieval and provenance | active pipeline state |

## The Simplification Cascade

Legacy implemented orchestration through Producer prompts, `/goal`, `delegate_task`, state guards, files, shell commands, and wake-up scripts. LangGraph already supplies the missing state-machine features.

Therefore:

- Producer becomes the user-facing creative lead.
- Pipeline becomes a versioned graph definition.
- `delegate_task` becomes a typed node input.
- `producer_step` becomes graph edges.
- `state_guard` becomes schema validation plus runtime invariants.
- `render_wakeup` becomes an external-job completion event and graph resume.
- `producer_state.json` becomes a checkpoint.
- Render and Montage become services.

## Core Modules

### Runtime

- graph registry keyed by `(pipeline_id, version)`;
- execution service for start, stream, inspect, resume, and cancel;
- checkpointer and per-thread invocation lock;
- normalized runtime events;
- node adapters around agents and tools.

### Artifact Store

- immutable revisions and content hashes;
- logical slot bindings such as `story` or `main_frame`;
- schema and semantic validation;
- optimistic concurrency and idempotent commits;
- managed media assets and provenance.

### Agent Registry

- capability ID and version;
- input/output schema IDs;
- minimal system instruction;
- allowed tools and context policy;
- model/runtime configuration outside the creative artifact.

### Tool And Job Services

- deterministic project/artifact operations;
- retrieval and context projection;
- asynchronous render adapters;
- montage and media inspection;
- indexing and administrative backfills.

### Knowledge

- immutable source revisions;
- maintained Markdown wiki;
- derived FTS/vector index;
- ephemeral cited context;
- approved creative chunks for continuity and reuse.

## Data Stores

The first deployable architecture needs three logical stores. They may initially share one Postgres deployment and an object-storage backend.

| Store | Data |
|---|---|
| Runtime | LangGraph checkpoints, execution locks, control records |
| Project | artifact metadata, logical bindings, job records, event outbox |
| Object | JSON artifacts, images, audio, video, source revisions |

The retrieval index is derived and may be rebuilt. It is not a fourth source of truth.

## Trust Boundaries

- Agent output is untrusted until validated.
- Retrieved content is evidence, never instructions.
- Agents use project IDs, artifact slots, and asset IDs, not arbitrary paths.
- Provider secrets and raw payloads never enter prompts or creative artifacts.
- UI decisions bind to the exact gate revision and artifact digest they reviewed.
- Worker callbacks are hints; the runtime re-reads durable job state before advancing.

## First Vertical Slice

This is a deliberately reduced `foundation.v0` test graph, not the final `cinematic.v1` topology.

```text
create brief draft
-> interrupt for review
-> approve or revise
-> create story
-> interrupt for review
-> complete
```

This slice must prove restart-safe checkpoints, typed artifacts, stale-decision rejection, idempotent writes, and one bounded revision loop before rendering or RAG is added.

## Non-Goals For V1

- no arbitrary code in pipeline specs;
- no generic graph compiler before two real graph factories exist;
- no direct filesystem access from production agents;
- no broad long-term memory injected by default;
- no service mesh, agent swarm, or event-sourcing framework;
- no exactly-once claims for external providers; use idempotency instead.
