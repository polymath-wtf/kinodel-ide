# LangGraph Backend Contract

Status: **Design for the installed framework; integration proof pending.** Package inventory and install/build steps live in [Local MVP](../roadmap-mvp.md#repository-and-dependencies).

## Build Boundary

Use Python `StateGraph` with directly authored nodes and finite routes. Keep stage declarations beside the factory and validate owners, inputs, outputs and required reviews. A static registry binds pipeline/version/digest to exact code and schemas; open executions cannot resume a different factory. The [cinematic JSON](../pipelines/cinematic.v1.json) is a design reference, not a runtime compiler.

Local uses `AsyncSqliteSaver` under one application/data-directory owner. Hosted PostgreSQL separately verifies the saver on the invocation's lock-owning session. Pass repositories, provider adapters, access scope and current fence through `Runtime[Context]`, not checkpoint state. Use `thread_id = execution_id` for invoke and inspection.

## Invocation Modes

| Purpose | Input |
|---|---|
| First invocation, no checkpoint | Persisted initial-state projection |
| Continue unfinished work | `None`, same thread |
| Answer exact saved interrupt | `Command(resume={interrupt_id: decision_ref})` |

Use async invocation and synchronous checkpoint durability. The worker examines pending writes and durable decision receipts before re-delivery; a consumed answer must not reach another interrupt. [Runtime recovery](runtime.md#recovery-decision-table) owns the classifier. HTTP clients never send checkpoint IDs, raw Command, goto or update_state.

## Node Granularity

The UI shows input, agent, generation-tool and HITL nodes. Internally a HITL separates request preparation, `interrupt()` wait and idempotent apply. A `*-gen` separates durable submit, external wait and output collection. These are bounded steps, not one long LLM loop. Direct revise invokes the fixed owner; there is no Critic dispatcher.

A saved creative plan can drive the following tool node directly. Native model tool-call adapters, when used, validate allowed calls against the same plan/operation and use the same durable tool service. ToolNode/async syntax alone is not a persistent background-job system. The [tool contract](../tools/tools.md) returns a durable group ref before rendering finishes.

## Replay Rules

- Return partial state updates; do not mutate input or persist media/transcripts in shared state.
- Before an effect, look up its operation. Committed work returns recorded refs/transition without another model call, provider submit or binding replacement.
- All writes/effects require idempotency, including those after `interrupt()`; a crash can occur before checkpoint persistence.
- Wait uses its exact prepared request, not “latest request for this node.” One interrupt per wait invocation; another question is another explicit graph cycle.
- Preserve pending checkpoint writes/resume values. Do not swallow control/interrupt exceptions in broad retry handlers.
- Apply saves the selected result before downstream; completion checks declared outputs and required approvals before its terminal receipt. Empty `next` alone is not proof of completion.

## Edges And Outcomes

Use static edges for unconditional successors and finite conditional edges (or bounded Command destinations) for explicit outcomes. Do not combine a static successor with Command routing from the same node unintentionally. Model output is semantic data, never an unrestricted stage destination.

`ready` commits a result; `needs_input/out_of_scope` explains why the current owner cannot replace it. On review the unchanged subject remains inspectable. First-generation failure without a subject blocks instead of inventing an approval target. Durable product/technical budgets are distinct from LangGraph's recursion ceiling.

## Fan-Out And Subgraphs

Keep the MVP flat and jobs sequential. The generation service handles exact face-to-sheet dependencies, complete-set collection and recovery without `Send` or parallel human interrupts. Introduce keyed reducers/subgraphs only with a working need. UI grouping requires neither.

## Reference And Verification

Follow [framework documentation routing](../../AGENTS.md#framework-documentation): official docs/API MCP for targeted questions, installed environment source for version-specific behavior. The optional ignored `.reference/langgraph` checkout is an upstream snapshot, not necessarily the installed version. Local [fundamentals](../../skills/LangGraph/langgraph-fundamentals/SKILL.md), [HITL](../../skills/LangGraph/langgraph-human-in-the-loop/SKILL.md), and [persistence](../../skills/LangGraph/langgraph-persistence/SKILL.md) provide task-specific guidance. Upstream examples do not prove application-level idempotency, local installation or recovery. Actual checks are in [Local MVP](../roadmap-mvp.md#acceptance).
