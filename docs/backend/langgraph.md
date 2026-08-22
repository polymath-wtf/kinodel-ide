# LangGraph Decisions

Status: **Decided foundation**

Kinodel uses a directly authored LangGraph `StateGraph` as the top-level runtime because the product needs explicit state, branching, loops, persistence, parallel work, and human interrupts.

## Use

- one `thread_id` per pipeline execution;
- `PostgresSaver` for durable deployment, in-memory saver only in tests;
- nodes return partial state updates and do not mutate input state;
- `interrupt()` for creative review and external-job waits;
- `Command(resume=...)` with the same thread ID to resume;
- `Send` plus a keyed reducer for later shot/frame fan-out;
- structured model output inside agent nodes;
- ordinary nodes before specialist subgraphs.

## Replay Rule

An interrupted node restarts from its beginning on resume. Code before `interrupt()` must therefore be pure or idempotent. Generate and persist a proposal in a preceding node; let the gate node only build the review request, interrupt, validate the decision, and route.

## Routing Rule

Agents never select arbitrary graph destinations. Use deterministic edges or a typed `Command(goto=...)`, but do not accidentally combine both for the same route.

## Persistence Rule

The checkpointer stores execution memory, not project artifacts. LangGraph Store is deferred until a proven cross-thread preference or fact requires it.

## Framework Boundaries

- LangChain agents or structured model calls may run inside a graph node.
- Deep Agents are not the production pipeline orchestrator.
- Agent swarms are not a foundation dependency.
- Human approval of pipeline artifacts belongs in LangGraph, not generic tool middleware.

Local reference: `skills/LangGraph/`.
