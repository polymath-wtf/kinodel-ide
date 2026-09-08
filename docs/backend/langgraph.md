# LangGraph Backend Contract

Status: **Decided design; pinned-version integration proof pending**

Use Python LangGraph `StateGraph` for deterministic production routing, persistent tasks, interrupts, and later fan-out. A structured model call or bounded LangChain agent lives inside a node adapter. Deep Agents, chat routing, and a second state-machine library are unnecessary.

## Build Boundary

Author `build_foundation_v0_graph()` first and `build_cinematic_v1_graph()` later. Keep stage declarations next to their factory; validate read/write owners, finite routes, required approvals and gate policy before registration. A registry maps the frozen pipeline ID/version/digest to tested code and schema versions. Existing threads do not silently run a changed factory.

Build/compile with `AsyncPostgresSaver` bound to the invocation's dedicated lock-owning connection. Graph topology builders may be reused, but a cached compiled graph must not capture another invocation's saver or context. Use `InMemorySaver` only for unit tests. Saver setup is a deployment migration, not an operation on every startup.

All invoke, state inspection and history calls use `thread_id = execution_id`. The worker supplies runtime repositories, provider adapters, authorization scope and current fence via `Runtime[Context]`. Only compact references enter the [checkpoint schema](state-machine.md).

## Invocation Modes

| Purpose | Input | Conditions |
|---|---|---|
| first start | exact persisted initial-state projection | no checkpoint exists for this execution |
| recover unfinished tasks | `None` | latest checkpoint, no unanswered human interrupt requiring a new response |
| answer one known interrupt | `Command(resume={interrupt_id: decision_ref})` | matching immutable application wait and durable response |

Use async APIs and `durability="sync"` so the next super-step waits for checkpoint persistence. Default asynchronous durability and exit-only persistence are not the foundation recovery contract. The worker classifies pending resume writes before sending a response again; see [runtime recovery](runtime.md#recovery-decision-table).

The browser never supplies checkpoint IDs, internal interrupt IDs, or `Command`. Never use an initial-state dictionary, `Command(update=...)`, `goto`, or `update_state()` as a substitute for review resume. Debug time travel is not user revision: business side effects are not rolled back by a checkpoint fork. A public rerun uses a new execution with explicit source refs.

## Node Granularity

One node performs one bounded semantic step. Do not put generation, approval, Critic, regeneration, and rendering into one loop inside an agent node.

| Node kind | Effects and result |
|---|---|
| proposal/repair | prepare operation, call one owner, validate/commit artifact or typed needs-input result |
| request preparation | persist exact review/input request, return its reference |
| wait | call one `interrupt()` with a small card, return validated decision ref |
| decision application | idempotently record decision outcome and next activation |
| Critic | commit bounded report; finite ready/needs-input/out-of-scope result |
| explanation | commit bounded Producer answer linked to next same-subject card |
| completion | validate required outputs/approvals, commit terminal receipt, then `END` |
| external submit/wait/join | separate nodes; no provider submission inside the wait node |

Logical review routes are defined once in [reviews.md](reviews.md#foundation-routes). Each logical gate expands into `prepare -> wait -> apply`; no separate graph compiler is required. Foundation uses explicit brief/story instances of these ordinary node functions, not stateful agent subgraphs.

## Replay Rules

- Nodes return partial updates, never mutate their input state.
- On re-entry, read the exact operation first. A committed result restores its recorded delta/transition without another model call or binding replacement.
- All external effects and durable writes require idempotency, **including after `interrupt()`**. Moving an insert below an interrupt does not close a crash-before-checkpoint window.
- A gate task always uses the request reference saved by preparation. Do not look up the most recent request for its gate while replaying an old task.
- One `interrupt()` per wait-node invocation; re-prompt via a new graph cycle/request, not `while True` inside a node.
- Do not wrap interrupt/control exceptions in a broad retry/repair handler. Catch declared provider/model errors around the effect itself, not around the whole graph.
- Pending writes can preserve successful tasks or a resume value before the next complete checkpoint. Recovery must retain them; do not delete task history to make retry work.

LangGraph may skip already checkpointed work, but it cannot make a file write or provider charge atomic with a checkpoint. Project DB operations and the artifact file protocol close the business commit windows. Do not layer a second generic task journal on top of `operations`.

## Edges And Outcomes

Use static `add_edge` for unconditional successors. Use a deterministic conditional edge or a node-returned `Command[Literal[...]]` for finite authored outcomes. Do not attach a static successor to the same node's `Command(goto=...)` path: both would run.

Critic's outcome is bounded semantic data. The node adapter validates it and the graph maps it to fixed destinations; free-form text, agent names, and model-proposed `goto` are never routing inputs. `START` is entry-only; `END` follows a durable terminal receipt, not a shortcut that implies approval.

Product loop counters live in durable gate/operation policy. LangGraph recursion limits are a defensive ceiling derived from the allowed topology/loops, not the creator's revision allowance. A recursion/programming error is diagnosed, never automatically routed as user rejection.

## Fan-Out And Subgraphs

No `Send` in foundation. With rendering, plan stable group/unit IDs and submit idempotent unit jobs. Workers return only keyed refs; the reducer accepts identical duplicates and rejects conflicts. The deterministic join checks every expected unit and plan order, then alone publishes the aggregate manifest/binding. Reset group state before a new activation so old results cannot satisfy a new generation.

Provider duration belongs to durable jobs, not blocked Python tasks or one human interrupt per fan-out child. The parent waits once for the declared job group. Successful unit jobs survive a sibling's technical failure; a changed creative plan starts a new aggregate activation initially.

Keep foundation flat. A later subgraph uses inherited per-invocation checkpointing by default when it needs pauses; `checkpointer=False` is only for work that needs no pause/persistence. Persistent `checkpointer=True` agent conversations require a demonstrated use case and isolated namespaces, not a shared subgraph invoked concurrently. A subgraph called inside a parent node can replay both parent and child, so it does not remove idempotency requirements.

## Memory Boundary

Checkpoint persistence is execution memory, not creative memory. LangGraph Store does not replace Project DB, artifact publication, or rights controls. Context is prepared and frozen on the operation, hydrated only at the agent boundary, and traced by exact revisions. RAG can later suggest inputs through that boundary; embeddings cannot mutate state, approve a gate, or schedule an edge.

## Reference And Verification

Read locally: `skills/LangGraph/langgraph-fundamentals/SKILL.md`, `langgraph-human-in-the-loop/SKILL.md`, and `langgraph-persistence/SKILL.md`. They establish StateGraph, reducers, interrupts, threads and saver scopes. Their illustrative "after interrupt only runs once" examples are not a crash-safety guarantee, and their in-node validation loop is not our production pattern.

Official sources checked on 2026-09-07:

- [Durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution): replay and synchronous durability.
- [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts): same-thread resume, per-task resume values, one-interrupt node pattern.
- [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence): checkpoints and pending writes.
- [AsyncPostgresSaver source](https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint-postgres/langgraph/checkpoint/postgres/aio.py): accepts a direct async connection, not only a pool.

These sources support the design; they do not pin a deployed dependency or prove our wrapper. Before implementation acceptance, pin concrete packages and exercise the [runtime acceptance matrix](runtime.md#acceptance-matrix) against PostgreSQL, including connection loss, pending resume writes, cancellation, and process death. Do not introduce newer streaming/fault-handling APIs merely because the current docs advertise them.
