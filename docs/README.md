# Kinodel Documentation

Kinodel is a **runtime-vibe-factory for creators**: a user follows a production pipeline, inspects each result and approves or revises it through human-in-the-loop interaction. Cinematic is the first workflow, not the limit of the product.

## Start Here

1. [Local MVP](roadmap-mvp.md) — repository/dependencies, implementation sequence and first-build acceptance. The only current build checklist.
2. [Architecture](backend/architecture.md) — stack, ownership and system boundaries.
3. [Cinematic](pipelines/cinematic.md) — node route, inputs/results and direct revisions; [JSON](pipelines/cinematic.v1.json) is its non-executable inspection reference.
4. Read the domain page being implemented; do not redesign the entire catalog before writing code.

## Domain Routes

| Concern | Source |
|---|---|
| Graph execution and replay | [Runtime](backend/runtime.md), [LangGraph](backend/langgraph.md), [state](backend/state-machine.md) |
| Framework implementation guidance and official MCP lookup | [LangGraph reference index](langgraph/README.md) |
| Human approval, owner chat revisions and future execution forks | [HITL](hilp/hilp.md), [Fork](hilp/fork.md) |
| Immutable outputs and proposed wire types | [Artifacts](backend/artifacts.md), [physical DTOs](backend/dto.md) |
| Storage/module layout and startup | [Implementation](backend/implementation.md), [local startup](backend/local-startup.md) |
| Agents | [Catalog](agents/README.md), individual craft contracts |
| Generation and other side effects | [Tools](tools/tools.md), [ComfyUI](backend/comfyui.md) |
| Node types, boundaries and later composition | [Nodes](backend/node.md), [Web UI](frontend/webui.md) |
| Explicit context and future memory/search | [Context](context/context.md), [RAG](rag/rag.md), [chunks](rag/chunks.md) |
| Database/hosted decisions | [Database](database/README.md) |
| Later features | [Product roadmap](roadmap.md), [future topics](features/future.md) |

## Authority And Status

Current domain contracts in `docs/` define intended behavior; tests establish what is implemented. `Decided/Accepted` does not mean tested. `Proposed` needs implementation evidence; `Deferred` is not an MVP prerequisite. Historical notes, dry runs and legacy code are research only.

The 2026-09-21 cinematic/review decisions supersede earlier image-only release plans, mandatory Brief/Critic/final-memory gates and old stage/slot names. Future pipeline sketches must be reconciled at activation. The optional ignored `.reference/langgraph` checkout and tracked [skills](../skills/LangGraph/) explain framework mechanisms, not Kinodel product decisions.

## Core Rules

- One execution/thread runs a frozen graph; layout is only presentation.
- Agent output is validated and saved; downstream uses exact selected results, not conversation history.
- Generation tools submit durable work and return promptly; no LLM waits for rendering.
- Human edits go directly to the declared owner; every new result version needs its own required review.
- Jobs, saves and commands are idempotent locally; uncertain provider acceptance needs reconciliation.
- Explicit context first. Generic compilation, arbitrary code/tools, swarms and broad retrieval wait for real use cases.
