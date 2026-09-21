# Agent Catalog

Status: **Contracts for implementation, not deployed agents.** Agents reason inside LangGraph nodes; generation tools perform side effects after validated plans. [Cinematic](../pipelines/cinematic.md) owns the exact MVP route.

## Capabilities

| Capability | Role | Activation |
|---|---|---|
| [Storytell](storytell.md) | Story from submitted brief | MVP |
| [Wardrobe](wardrobe.md) | Anchor direction/prompts; generated result `anchor_frames` through its tool | MVP |
| [Storyboard](storyboard.md) | Shot image plans; `story_frames` through its tool | MVP |
| [Filmmaker](filmmaker.md) | Video motion plans; `shot_videos` through its tool | MVP |
| [Render](render.md) | Shared generation tool service, no LLM persona | MVP |
| [Montage](montage.md) | Deterministic assembly tool | MVP; creative agent later |
| [Producer](producer.md) | Optional brief preparation/assistance | Later; not a mandatory Brief node |
| [Critic](critic.md) | Optional recommendations for user consideration | After MVP |
| [Craft](craft.md) | Draft reusable memory for separate publication | Later |
| [Muse](muse.md), [Season](season.md), [Episode](episode.md) | Other creative pipelines | Later, reconcile at activation |

## Common Contract

Implement only the enabled capabilities. Their typed inputs/outputs, instructions, context and representative checks are required when activated; future agent proposals do not block the first code.

### Prepared Input

The adapter supplies the submitted Brief, exact approved upstream results, explicit references/roles and frozen instructions/profile constraints. It resolves authorized media and selected context before the model call. Agents receive usable content, not only IDs. On revise, include the previous complete output, base subject version, original user feedback and relevant node discussion.

Stable shot keys are prepared from the Brief count; Wardrobe can propose variable anchor keys, validated/frozen before generation. Repairs preserve corresponding keys. IDs, digests, approval, permissions and job metadata remain trusted application data, not fields invented by the model.

### Attachments And `@` References

Mentions select exact authorized artifact/source/resource references with roles. Adapters hydrate bounded projections, preserving required instructions and recording optional omissions. Reference text is data, not executable instructions. No arbitrary filesystem/network lookup by the agent. Missing required or conflicting context blocks the call.

### Result And Repair

| Outcome | Meaning |
|---|---|
| `ready` | Complete typed output; validate, save immutable version, return compact ref |
| `needs_input` | Explain missing information; no partial replacement |
| `out_of_scope` | Explain conflict with approved ancestors/owner scope; no hidden rewrite |

User feedback follows the [HITL revision contract](../hilp/hilp.md#revision-contract). The application prepares `RevisionRequestV1` for the fixed owner; downstream consumes selected outputs, not node conversation.

### Invocation And Registry

Use one bounded structured model response per operation, with bounded output repair. A static capability record pins instructions, schemas, permitted tools, model modalities and budgets. Wardrobe/Storyboard/Filmmaker have only their declared generation tool, dispatched by the next graph node from the saved plan. They neither poll jobs nor select provider endpoints. [Tools](../tools/tools.md) defines optional native tool-call handling without a second execution path.

No marketplace, universal handoff dictionary or agent framework is required. Build the enabled prompts/resources under `.agents/` with their actual implementation; the directory is not another scheduler.

### Consumer Context

| Capability | Required material |
|---|---|
| Storytell | Submitted brief and selected narrative canon |
| Wardrobe | Brief, approved story, character/style references and anchor prompt guidance |
| Storyboard | Brief, approved story, exact Wardrobe plan, approved anchor_frames and multi-image guidance |
| Filmmaker | Brief, approved story/frames, ordered shot keys and motion guidance |
| Montage tool | Approved shot_videos, order, measured media and output settings |

## Common Boundaries

No graph routing, direct persistence, arbitrary shell/path/endpoint access or implied approval. Schema validation does not prove creative quality. Check model output deterministically where possible and leave creative acceptance to the user. Later Critic recommendations cannot replace that decision.
