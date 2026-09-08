# Kinodel Documentation

This directory is the source of truth for the rebuild. It records decisions, contracts, and explicit unknowns. Prompt-like research notes and legacy behavior are not architecture until distilled here.

## Read Order

1. [`backend/architecture.md`](backend/architecture.md) - system shape and boundaries.
2. [`backend/runtime.md`](backend/runtime.md) - execution, persistence, interrupts, workers.
3. [`backend/reviews.md`](backend/reviews.md) - human gates, revision through Critic, and approval identity.
4. [`backend/implementation.md`](backend/implementation.md) - chosen Python backend, database ownership, implementation order.
5. [`backend/artifacts.md`](backend/artifacts.md) - production truth and typed references.
6. [`agents/README.md`](agents/README.md) - creative capability catalog.
7. [`backend/pipeline.md`](backend/pipeline.md) and [`pipelines/`](pipelines/) - pipeline topology.
8. [`tools/tools.md`](tools/tools.md) - controlled side effects.
9. [`context/context.md`](context/context.md) and [`rag/rag.md`](rag/rag.md) - direct context, chunks, and future retrieval.

## Domain Routes

- Runtime state: [`backend/state-machine.md`](backend/state-machine.md)
- Human review: [`backend/reviews.md`](backend/reviews.md)
- LangGraph rules: [`backend/langgraph.md`](backend/langgraph.md)
- ComfyUI boundary: [`backend/comfyui.md`](backend/comfyui.md)
- Frontend: [`frontend/webui.md`](frontend/webui.md)
- Roadmap: [`roadmap.md`](roadmap.md)
- Migration brief: [`refactoring.md`](refactoring.md)
- Deferred feature notes: [`features/`](features/)

## Authority

When documents disagree, use this order:

1. current contract in `docs/`;
2. tested implementation, once it exists;
3. local framework docs under `skills/`;
4. targeted evidence under `legacy/`;
5. old prose, examples, and provider defaults.

Provider defaults, shot counts, and model IDs are configuration, not universal architecture.

## Status Labels

- **Decided**: foundation to implement.
- **Proposed**: plausible design that needs a vertical-slice test.
- **Deferred**: intentionally not part of the first implementation.
- **Legacy**: evidence only.

## Core Decisions

- Build the reduced `foundation.v0` graph first, then the full directly authored `cinematic.v1` graph.
- One thread per pipeline execution, not per permanent project.
- Typed references in graph state; immutable content in an Artifact Store.
- Explicit `interrupt()`/`Command(resume=...)` human gates.
- Agents generate typed creative output; node adapters validate and persist it.
- Services perform rendering, montage, retrieval, and indexing.
- Direct explicit context first; add FTS/vector discovery only when a real library-search use case and gold set prove value.
- Build `cinematic.v1` as the first full production pipeline; extract abstractions only after a second pipeline works.

## Deferred

- natural-language pipelines that execute immediately;
- generic pipeline-spec compiler;
- autonomous producer/critic swarms;
- parallel human interrupts;
- graph database and distributed event bus;
- multiple embedding dimensions in production;
- LangGraph Store as a project database;
- visual node editor and time-travel UI.
