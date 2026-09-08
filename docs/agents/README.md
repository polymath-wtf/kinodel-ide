# Agent Catalog

Status: **Foundation contract**

Kinodel agents are narrow creative capabilities invoked inside LangGraph nodes. They do not coordinate the pipeline, persist arbitrary files, call generation providers directly, or choose the next stage.

## Classes

| Capability | Class | Status | Owned output |
|---|---|---|---|
| [Producer](producer.md) | user-facing agent | active design | brief draft or clarification answer |
| [Storytell](storytell.md) | creative agent | active design | story |
| [Wardrobe](wardrobe.md) | creative agent | active design | visual-anchor plan |
| [Storyboard](storyboard.md) | creative agent | active design | frame plan |
| [Filmmaker](filmmaker.md) | creative agent | active design | motion plan |
| [Critic](critic.md) | review agent | active design | bounded `RevisionRequestV1`, including non-ready outcomes |
| [Craft](craft.md) | memory agent | active design | reusable creative chunk |
| [Render](render.md) | service, not agent | active design | candidates and promoted selected media |
| [Montage](montage.md) | creative agent | active design | montage plan |
| [Montage executor](montage.md) | service | active design | final assembled media |
| [Muse](muse.md) | creative agent | planned | music concept and request |
| [Season](season.md) | creative agent | planned | season plan |
| [Episode](episode.md) | creative agent | planned | episode story |

Pipeline, project initialization, finalization, indexing, ALM analysis, provider adapters, and ffmpeg execution are nodes/tools/services, not agent personas.

## Legacy Disposition

- Generic Muse is folded into planned Kinodel Muse; there is one music-planning capability.
- Guzlik is a product/monetization persona, not a production capability, and is excluded.
- Pipeline and Project Layout become runtime configuration/tools.
- Prompt support skills are bundled references for their owning agent, not separate runtime agents.
- Season, Episode, and Muse remain planned until their pipelines are implemented.

## Common Contract

### Design Before Activation

Before the first backend build, define the input/output meaning, ownership, context, revision scope, and quality checks for **every catalog capability**, not only Producer, Storytell, and Critic. Cinematic is the complete reference chain. Muse/Season/Episode have architectural contracts now; their pipeline activation remains later.

`foundation.v0` activates three capabilities to test runtime safety. It is not a three-agent backend architecture. Use the same invocation, validation, context, and revision boundaries for all capabilities; do not add a generic agent framework, stub agents, or live render dependencies just to register names. Contract design, executable schemas, packaged instructions, and passing model/runtime tests are separate readiness levels. These pages establish design, not the latter three.

### Prepared Input

Every node adapter prepares:

- project and execution identity;
- exact validated input artifact revisions;
- one resolved `ContextSelectionV1` from explicit mentions, pipeline requirements, and allowed agent resources;
- stage mode, declared stable units, and provider-neutral capability constraints relevant to the task;
- on repair, the previous exact owned output and `RevisionRequestV1`; media repair also includes the reviewed candidate set and relevant observations;
- one declared typed output contract and its validation rules.

The agent receives hydrated task bodies and labelled context/media, not DB handles to look up. IDs, digests, approval receipts, access decisions, and operation bookkeeping remain adapter-owned. Each mode uses its own typed input; no universal dictionary of optional fields. An empty optional context selection is valid, missing required inputs are not.

Artifact/operation identities are not narrative unit identities. The adapter supplies stable unit IDs for declared counts; the creative owner assigns their meaning and order within its contract. For variable structures such as music sections or episode acts, the first candidate declares local unit keys, validated and frozen at commit. Repairs preserve keys for corresponding units; new keys are permitted only for an authorized structural change. Downstream planners consume that exact mapping rather than allocating replacements.

### Result And Repair

| Semantic outcome | Required content | Adapter/graph handling |
|---|---|---|
| `ready` | one complete candidate of the mode's declared schema | validate schema, references, cross-artifact invariants; persist and return compact refs |
| `needs_input` | missing/conflicting creative facts, exact affected refs/fields, one actionable question | no partial artifact; existing-subject repair returns to its unchanged gate; pre-Brief uses the bounded input path |
| `out_of_scope` | requested change and the approved constraint/owner boundary it violates | no replacement artifact or upstream mutation; existing-subject feedback path |

These are common outcome semantics, not a generic tool/handoff envelope or finished schema. Critic's concrete result is [RevisionRequestV1](critic.md); Producer has separate draft/question/explanation modes. Non-ready reasons are durable operation results, not reusable creative artifacts. A first-generation stage without a subject blocks with the reason rather than fabricating a review subject or a graph destination. Runtime/storage/provider failures remain typed service errors, not agent-written creative outcomes.

Repair produces a full new aggregate; stable IDs survive for corresponding units. Original feedback and the exact previous output are both supplied, so the owner changes the requested parts while preserving unrelated content. No owner reinterprets an approved ancestor. Semantic outcome selects only an already-authored route; models never return stage IDs to execute.

### Invocation And Registry

Start with one bounded structured model invocation per operation, plus the runtime's bounded output repair if needed. Agents have **no callable tools by default**: inspection means authorized media/content supplied by adapters, optionally with a separately validated observation service result. An image-only or text-only model cannot certify unseen motion or unheard audio. Missing required modality evidence blocks the operation; a poster frame is not proof of clip continuity.

A static versioned capability record declares `capability_id/version`, supported modes and input/output schema IDs, instruction/resource digests, context-policy version, required model modalities, and the runtime model/timeout/attempt/budget configuration. The initial tool allowlist is empty. A stage binds one exact capability/mode; operation preparation pins its effective configuration for replay. Graph loading rejects enabled stages with missing schemas, policies, validators, resources, or incompatible modalities. Unimplemented modes are unavailable, never silently routed to Producer or another model role. No database agent marketplace or dynamic discovery is needed.

### Consumer Context

| Capability | Required task projection | Optional explicitly selected context |
|---|---|---|
| Producer | raw request, allowed defaults/constraints, selected mandatory character canon; exact subject for explanation | explicitly selected inspiration |
| Storytell | approved Brief and selected mandatory narrative canon | story lessons, not image prompts |
| Wardrobe | approved spine, character identity/current physical state | palette, materials, environment references with take/ignore |
| Storyboard | approved visual direction/spine, exact anchors for later frames, profile-required image guidance and selected mandatory appearance canon | permitted composition inspiration |
| Filmmaker | approved spine/visual direction, selected frames, unit mapping/timing, required motion/voice canon and profile-required video guidance | permitted motion inspiration |
| Montage | approved narrative spine when applicable, approved clips/audio, measured metadata, Brief and edit constraints | editing lessons; no search for alternative takes |
| Critic | exact subject, feedback, supporting owner plan, gate scope/criteria and approved constraints | only relevant supplied evidence |
| Craft | exact approved sources/media, labelled supporting plans, rights and consumer policy | none through discovery |
| Muse | approved music Brief and rights restrictions | permitted music attributes and audio guidance |
| Season | approved serial Brief, selected characters/prior-season canon when required | labelled story/world inspiration |
| Episode | approved Brief, season, target blueprint, required previous ending and characters | bounded older continuity and explicitly future plans |

Required projections and media must fit the configured budget or block; optional omissions are recorded before preparation. Numerical budgets and executable projections must be tested per deployed model, not invented in this catalog.

Selected canon and resources required by a frozen profile are mandatory even when their original selection was optional to the creator. This table never permits dropping them during preparation or retry.

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
If required creative information is absent or contradictory, return needs_input; an edit outside your scope returns out_of_scope.
```

Agent pages are contracts for later builds under `.agents/`; they are not deployable prompts yet. Before enabling a mode, provide its executable schema/semantic validator, versioned instructions/resources, one representative valid fixture and one scope/continuity failure fixture, and a model-quality check against its page's criteria. Deterministic validators enforce counts/IDs/rights/bounds; craft criteria require inspection and do not become automatic human approval. The same rule applies to all agents, including those not invoked by the first graph.
