# Agent Catalog

Status: **Foundation contract**

Kinodel agents are narrow creative capabilities invoked inside LangGraph nodes. They do not coordinate the pipeline, persist arbitrary files, call generation providers directly, or choose the next stage.

## Classes

| Capability | Class | Status | Owned output |
|---|---|---|---|
| [Producer](producer.md) | user-facing agent | active design | brief draft or review interpretation |
| [Storytell](storytell.md) | creative agent | active design | story |
| [Wardrobe](wardrobe.md) | creative agent | active design | visual-anchor plan |
| [Storyboard](storyboard.md) | creative agent | active design | frame plan |
| [Filmmaker](filmmaker.md) | creative agent | active design | motion plan |
| [Critic](critic.md) | review agent | active design | issue report |
| [Craft](craft.md) | memory agent | active design | reusable creative chunk |
| [Render](render.md) | service, not agent | active design | selected generated media |
| [Montage](montage.md) | service, not agent | active design | final assembled media |
| [Muse](muse.md) | creative agent | planned | music concept and request |
| [Season](season.md) | creative agent | planned | season plan |
| [Episode](episode.md) | creative agent | planned | episode story |

Pipeline, project initialization, finalization, indexing, ALM analysis, and provider adapters are nodes/tools/services, not agent personas.

## Legacy Disposition

- Generic Muse is folded into planned Kinodel Muse; there is one music-planning capability.
- Guzlik is a product/monetization persona, not a production capability, and is excluded.
- Pipeline and Project Layout become runtime configuration/tools.
- Prompt support skills are bundled references for their owning agent, not separate runtime agents.
- Season, Episode, and Muse remain planned until their pipelines are implemented.

## Common Contract

Every agent node receives only:

- project and execution identity;
- exact validated input artifact revisions;
- explicit user-selected or runtime-resolved context;
- optional typed revision feedback;
- one declared output schema.

Every agent returns structured candidate content. The node adapter validates and commits it, then returns an `ArtifactRef` to the graph.

Legacy `avatar_chunk` is renamed to `CharacterChunkV1`: avatar, actor, and fictional-character identity are one continuity capability. `avatar` may remain a UI alias, not a second schema.

## Common Boundaries

- No graph routing or `/goal` selection.
- No `delegate_task` handoff envelopes.
- No checkpoint, database, terminal, or arbitrary filesystem access.
- No provider payloads, queue IDs, retries, costs, or logs in creative output.
- No silent approval or mutation of upstream canon.
- No broad retrieval when direct context was supplied.
- No hidden side effects before a human interrupt.

## Minimal Prompt Pattern

```text
You own <capability> for Kinodel.
Use only the supplied validated inputs and context.
Create <output> that satisfies <schema and invariants>.
Do not route the pipeline, call generation providers, persist files, or invent missing canon.
If required information is absent or contradictory, return a typed blocked result.
```

Agent pages are contracts for later builds under `.agents/`; they are not deployable prompts yet.
