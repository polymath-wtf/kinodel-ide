# LangGraph: Implementation Reference Index

Framework navigation, not a Kinodel contract. Start with [Kinodel LangGraph](../backend/langgraph.md), [runtime](../backend/runtime.md) and [context](../context/context.md). Installed versions and verification belong to [Local MVP](../roadmap-mvp.md#repository-and-dependencies).

## Skills First

Use the installed skill; these tracked copies are fallbacks:

- [Fundamentals](../../skills/LangGraph/langgraph-fundamentals/SKILL.md): StateGraph, state/reducers, nodes/edges, Command, Send, streaming and retries.
- [Persistence](../../skills/LangGraph/langgraph-persistence/SKILL.md): saver setup, thread IDs, state history, Store and subgraph persistence modes.
- [Human-in-the-loop](../../skills/LangGraph/langgraph-human-in-the-loop/SKILL.md): interrupt/resume, multiple interrupts and node replay.

These cover the basics previously repeated in six local reference pages. Their generic examples do not override Kinodel: local persistence uses AsyncSqliteSaver; all mutating effects require idempotency, including effects after an interrupt.

## Official Sources And MCP Queries

Start with one targeted `docs-langchain` search using the query below. Read the returned page only if its excerpt is insufficient. For a known API use `reference-langchain` get_symbol; otherwise search_api, with Python selected. Match consequential behavior to `.venv313` and a focused test, not an unversioned example. Fallback navigation: [official index](https://docs.langchain.com/llms.txt).

| Need | Official source | Suggested MCP query |
|---|---|---|
| State, reducers, routing | [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) | `Python StateGraph reducers Command static edges` |
| State vs. cross-thread storage | [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | `Python LangGraph checkpointer vs store` |
| Checkpoints, tasks, namespaces, recovery | [Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers) | `Python LangGraph StateSnapshot pending writes checkpoint_ns` |
| Write timing | [Durability modes](https://docs.langchain.com/oss/python/langgraph/checkpointers#durability-modes) | `Python LangGraph durability sync async exit` |
| Pausing and resuming | [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) | `Python interrupt Command resume node replay` |
| History, branching, as_node | [Time travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel) | `Python LangGraph update_state as_node replay interrupts` |
| Subgraph lifetime and inspection | [Subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs) | `Python subgraph checkpointer None True False subgraphs state` |
| Runtime dependency injection | [Context](https://docs.langchain.com/oss/python/concepts/context) | `Python Runtime context_schema runtime context versus prompt` |
| Namespace lookup and search | [Stores](https://docs.langchain.com/oss/python/langgraph/stores) | `Python LangGraph Store namespace_prefix limit offset ordering` |
| Memory design, later | [Memory concepts](https://docs.langchain.com/oss/python/concepts/memory), [memory management](https://docs.langchain.com/oss/python/langgraph/add-memory) | `semantic episodic procedural memory hot path background` |
| Saver internals, only if needed | [Serializer and custom saver](https://docs.langchain.com/oss/python/langgraph/checkpointers#serializer) | `Python BaseCheckpointSaver serializer conformance DeltaChannel` |

## Useful Details Beyond The Basic Skills

- Full checkpoints mark super-step boundaries; pending task writes can preserve successful siblings when another node fails. They do not atomically commit external effects or Kinodel records.
- `sync` persists a checkpoint before the next step; `async` overlaps persistence with execution; `exit` omits intermediate crash recovery. Kinodel's selected invocation policy lives in its runtime contract.
- Inspect the exact thread/checkpoint/namespace and pending tasks. `update_state` creates a checkpoint through reducers; `as_node` attributes the update and determines its successors. Historical replay re-executes subsequent calls and interrupts; it is not business rollback or Kinodel Fork.
- Runtime context supplies invocation dependencies, not a saved prompt. Store namespaces organize data, not permissions. Prefix search may include child namespaces, is bounded by limit/offset, and has backend-specific ordering.
- Memory concepts distinguish facts, examples and instructions, and synchronous versus background writes. They do not require automatic memory publication or a Store in Kinodel.
- Serializer/encryption, custom saver conformance and beta DeltaChannel are lookup topics, not MVP tasks. Compact refs already avoid growing message channels. Check installed `langgraph.store.base.BaseStore` before implementing an adapter: the old copied guide confused LangChain/LangGraph Store links and understated the batch/abatch contract.
