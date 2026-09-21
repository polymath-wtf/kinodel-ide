# Serial Pipelines

Status: **Refreshed concept, 2026-09-21; deferred beyond cinematic MVP.** Season planning and episode production are distinct proposed workflows. Their decomposition, continuity publication and executable schemas still need design. [Cinematic](cinematic.md), [pipeline boundaries](../backend/pipeline.md) and [HITL](../hilp/hilp.md) define the shared execution rules.

## Season Planning

Proposed `serial_season.v1` core:

```text
brief (user input)
→ season → season-hitl
→ approved season plan
```

Season creates one aggregate `season_plan` (`SeasonPlanV1` proposal): premise, repeatable engine, arcs, linked setups/payoffs and ordered episode blueprints. The human approves that exact plan or sends feedback directly to Season. The output is planning authority, not completed episode history or automatic publication of reusable chunks.

This workflow does not produce full episodes. Shared visual development can later append `wardrobe → anchor-gen → anchor-hitl` when there is a concrete need for a season reference set. Per-episode anchors, mandatory season rendering and a separate visual-plan gate are not prerequisites for approving a season concept. The scope and reuse of such anchors remain open.

## Episode Production

Proposed `serial_episode.v1` core:

```text
brief (user input + exact episode selection)
→ episode → story-hitl
→ wardrobe → anchor-gen → anchor-hitl
→ storyboard → frames-gen → frames-hitl
→ filmmaker → video-gen → video-hitl
→ montage → final
```

The creator submits settings and selects one episode before Run; there is no mandatory Producer or Brief gate. Trusted preparation resolves and validates the exact season, target blueprint and required continuity before invoking Episode. Missing or contradictory mandatory context blocks with an explanation; it does not invent a new human gate or ask Episode to repair canon.

Episode replaces Storytell as the sole narrative owner. The visual/tool tail follows cinematic ownership and names. Agents create validated saved plans; `*-gen` nodes dispatch generation tools and wait on durable jobs. HITL applies complete media selection through the generation tool, with no separate promote node. Montage is deterministic assembly; final output is not an independent human approval or automatic memory publication.

## Proposed Handoffs

| Stage / owner | Required material | Result |
|---|---|---|
| `season` / Season | Submitted season brief, selected character canon and prior-season context if continuing | `season_plan`: one aggregate with ordered episode blueprints |
| `season-hitl` / human | Exact season plan | Approval of that revision |
| Episode input / adapter | Submitted episode settings, selected season/target blueprint and required prior continuity | Frozen authorized context, no new creative artifact |
| `episode` / Episode | Hydrated validated context and production constraints | `story`: episode narrative and ordered shot beats; continuity extension still proposed |
| `story-hitl` / human | Exact episode story | Approval of that revision |
| `wardrobe → anchor-gen → anchor-hitl` | Brief, approved story, exact character/visual references | `wardrobe_plan` and approved `anchor_frames` |
| `storyboard → frames-gen → frames-hitl` | Approved story/anchors and Wardrobe plan | `storyboard_plan` and approved `story_frames` |
| `filmmaker → video-gen → video-hitl` | Approved story/frames and output constraints | `video_plan` and approved `shot_videos` |
| `montage` / tool | Approved ordered videos and assembly settings | `final_video` |

Each output has one owner; generation tools are sole media writers on behalf of their creative owners. Plans support media review without acquiring separate approval. Reusing these capabilities does not mean current cinematic DTOs already encode episode acts, continuity or long-form production.

## Episode Breakdown And Execution

Season owns the creative breakdown into blueprints, not job scheduling. A stable episode key connects each blueprint to its later production; the application owns persistent identities. Episode selection must retain both the exact season-plan revision and target identity, not just an ordinal such as “episode 3”.

The simplest proposed launch is one explicitly started execution per episode, sequential by default. No parent `serial.v1` scheduler, automatic fan-out, nested episode threads or full-season render is implied. Starting episode N+1 requires available validated continuity, not merely a successful render for N.

How the approved aggregate becomes individually selectable planned episodes remains open: exact projections of the approved plan versus separately reviewed/published Episode chunks. Existing [context](../context/context.md#pipeline-required-context) and [chunk](../rag/chunks.md) concepts describe the latter; this sketch does not invent a second canonical copy or claim that publication already exists. Any extracted blueprint must preserve its source revision and approval coverage. Separate memory publication needs explicit review and optimistic concurrency, not another hidden model call.

Acts are narrative structure, not automatically graph nodes, subgraphs or anchor units. Decide long-episode segmentation, shot budgets, joins and interruption/review granularity before supporting long-form generation. Do not map every act or episode to a fixed anchor count. Wardrobe declares actual visual-reference needs from the selected narrative scope.

## Continuity Rules

- Pin exact approved season/target-plan sources and authorized Character revisions. Future blueprints are obligations and setup context, never accomplished facts.
- Episode one starts from declared initial canon. Later episodes require the relevant reviewed completed continuity; the previous episode alone may be insufficient if an older unresolved fact still matters.
- Supply a bounded relevant projection, not every conversation or every previous script. Required facts cannot disappear silently to fit the context budget.
- Keep planned narrative, approved story, rendered final and published completed continuity distinct. Story approval or a technically valid video does not prove that every proposed event is established shared canon.
- Preserve the exact planned input even if a future shared Episode binding points to a completed revision. A production plan and a record of what happened have different roles.
- Ordinary supersede does not mutate a running execution's pinned context. Rights withdrawal, missing bytes or lost authorization still block use. New runs explicitly select revised continuity.
- Revising completed episode N does not silently rewrite N+1. Existing outputs retain provenance; any downstream reproduction or continuity migration needs an explicit new flow.

The source and human review of completed continuity are activation blockers for a continuity-dependent next episode. Craft may eventually draft that memory, but a mandatory Craft chain, aggregate publication transaction and final-memory gate are not defined by this concept.

## Revision Routes

| Current HITL | Creative owner | Proposed route back |
|---|---|---|
| `season-hitl` | Season | `season → season-hitl` |
| `story-hitl` | Episode | `episode → story-hitl` |
| `anchor-hitl` | Wardrobe | `wardrobe → anchor-gen → anchor-hitl` |
| `frames-hitl` | Storyboard | `storyboard → frames-gen → frames-hitl` |
| `video-hitl` | Filmmaker | `filmmaker → video-gen → video-hitl` |

Direct feedback carries the exact previous output, current subject and relevant discussion. Valid replacements return to their own review; clarification and non-ready replies change no output. Critic is not a dispatcher. Episode cannot rewrite an approved season obligation or prior ending; frame/video feedback cannot rewrite story or anchors. Such ancestor changes require a new execution.

Use [cinematic anchor regeneration](cinematic.md#anchor-regeneration) where the same declared dependency contract applies. Technical retries preserve prepared inputs and successes; creative revisions require a new complete review subject. Selective episode/act repair and cross-execution reuse need their own declared scope, not inferred graph rewind.

## Open Before Activation

- Season/episode Brief contracts, episode counts/keys, blueprint granularity and constraints passed to each production.
- Exact plan-to-episode selection/publication model and launch UX; whether season-wide visual references are needed.
- Episode story schema: acts, shot mapping, obligations, before/after continuity and compatibility with cinematic consumers.
- Long-form segmentation and review granularity; start with one bounded episode rather than a season-wide orchestration framework.
- Completed-continuity evidence, review/publication and conflict handling before the next episode; optional reusable Season/Episode memory.
- Audio/dialogue and any richer montage/final review: the cinematic baseline currently assembles silent `i2v`, not a complete dialogue-series production system.

These questions do not expand [local MVP](../roadmap-mvp.md). Future concept checks: a repaired blueprint preserves other episode identities; an injury persists until a supported event changes it; a missing reviewed prior ending blocks episode N; updating season canon never silently changes a running episode.
