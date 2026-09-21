# Pipeline Architecture

Status: **Accepted boundaries.** [Cinematic](../pipelines/cinematic.md) owns its route and names; [Local MVP](../roadmap-mvp.md) owns implementation order.

A pipeline is a versioned LangGraph definition with declared node inputs, results, owners and human-review barriers. A node is not necessarily an agent: it can accept user input, reason, invoke a tool or wait for a human.

## Stage Kinds

| Kind | Role |
|---|---|
| Input | Validate/freeze explicit creator input |
| Agent | Return a bounded typed creative result or an explanation |
| Tool | Perform validated side effects, possibly as a durable background job |
| HITL | Review one exact result and apply the user's decision |

## Editor Mapping

The visible node instance uses `stage_id`; its type selects a known capability/tool/gate. Every new output has a unique declared binding slot. Multiple instances of one capability require different slots, operations, context and review subjects. A source supplies an exact context ref, not a mandatory source agent.

Connections declare input bindings and approval requirements, not automatic `add_edge` calls. The authored graph determines control flow. HITL internally uses prepare/wait/apply; a generation tool uses submit/wait/collect. These details are not separate user-facing nodes. MVP has individual fixed nodes; UI grouping and constrained sequential composition come later.

## Activation And Repair

Start, accepted feedback and completed predecessors provide durable activation identities. An operation pins its inputs before effects and returns the same committed result on replay. A review belongs to a fixed owner: user feedback → that owner → associated tool if needed → a new review. Clarification changes no output; cancellation follows the durable runtime protocol. Critic is not an intermediate dispatcher.

Only approved current results enter approval-required inputs under the [HITL contract](../hilp/hilp.md). Changing a submitted brief, graph configuration or approved ancestor requires a new run. Future [Fork](../hilp/fork.md) branches executions from a selected stage without changing the pipeline definition; it is outside MVP.

## Handoffs

Adapters hydrate exact creative bodies and selected context; graph state holds only refs. Do not forward all agent messages or inspect output folders to find inputs. Per-node instructions, context policy and output schema constrain both first generation and direct revision. A model cannot rewrite routing, ownership or trusted metadata.

One creative owner writes each plan. Its generation tool is the sole publisher of selected media on its behalf. Media selection is saved inside HITL apply, not an extra promotion node. Non-ready answers and clarification live as operation results/feedback, not replacement artifacts.

## Production Joins

Plans declare required units and dependencies; tools persist and execute jobs, then collect one complete immutable review set. Sequential execution needs no parallel graph reducer. Missing units block completion. Anchor regeneration preserves unrelated unchanged attempts with exact lineage; changed parents invalidate children. [Cinematic](../pipelines/cinematic.md#anchor-regeneration) defines the concrete rule.

## Versioning

Run freezes the graph/version/digest, submitted brief, selected profiles, instructions and explicit context. Operation preparation pins generated input refs; job preparation pins payload/seeds. Retry uses the same prepared layer. New draft instructions or connections cannot mutate an in-flight execution.

Validate static owners/connections and supported capabilities before Run; validate concrete generated values, rights and dependencies before each effect. Layout-only changes do not alter execution identity. Existing executions resume against their exact registered graph factory. The [JSON route reference](../pipelines/cinematic.v1.json) is not an executable DSL or compatibility layer.

## Pipeline Creation

Author the fixed graph directly in Python. A later editor may compile known node types into that same runtime after fixed-node configuration works. No second scheduler, universal plugin system or natural-language `/goal` routing. Future music/serial proposals must be reconciled to current agent and review contracts when activated.
