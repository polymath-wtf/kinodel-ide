# Storyboard

Class: creative agent  
Status: **Accepted design; implementation and provider verification pending**

Wardrobe designs anchor prompts; Render generates the images; the human approves the complete `main_frames` set before this agent runs. The [cinematic route](../pipelines/cinematic.md) and [node architecture](../pipelines/node-architecture.md) use the same handoff. Implementation and executable checks remain pending.

## Responsibility

Translate approved story units, visual direction, and approved anchor assets into shot image plans. Own shot composition, visible action, and image prompts using explicit multi-image reference roles; Wardrobe owns anchor design and anchor prompts.

## Input

- exact approved Brief and validated Wardrobe VisualAnchorPlan bound to the approved anchor set, including the stable named anchor units and their reference roles; the plan has no separate mandatory approval in the minimal new route;
- exact approved spine and its declared units: Story shots/acts, proposed Season episode blueprints, or proposed MusicPlan plus selected song and validated timing projection;
- exact promoted approved assets for the complete required anchor set, with selection/approval provenance; generation completion or plan approval alone is insufficient;
- hydrated appearance/continuity/reference projections and frozen prompt guidance, with the operation's context-selection reference;
- previous exact FramePlan, reviewed candidate evidence, and `RevisionRequestV1` when repairing this image-plan owner's output;
- declared frame units/order and supported reference/image constraints; mapping is identity on Story shot IDs for first cinematic `i2v`, not a separate mapping object. The agent does not invent endpoint units.

Node-specific adapters hydrate these bodies from prepared refs. The durable selection trace alone is not agent context, and Season/music modes do not require a fabricated `StoryV1`.

Adapters verify complete anchor-set approval and freshness before invocation. Selected rendered references use the [exact result plus unit selector](../backend/artifacts.md#selected-media-references), resolving AssetRefs rather than inventing frame IDs. Each shot binds the relevant anchors by role, for example face identity, body/wardrobe, and environment; the set's size follows the declared visual needs, not a mandatory count of three.

The frozen provider profile must explicitly support the required multi-image inputs and role mapping. Missing capability, insufficient reference capacity, or inability to preserve required roles blocks at the adapter/service boundary before submission. Do not silently drop references, flatten them into text, or substitute a single main frame as equivalent support. These capability checks and DTOs remain activation requirements.

## Output

`FramePlanV1`: one ordered shot-frame specification per declared unit, with a list of exact selected-media references and their semantic roles, explicit preserve/change constraints, semantic intent, image prompt from the frozen `@prompt-engine` guidance, and optional timing window. These are creative units, not provider jobs. API payload mapping remains outside the artifact; fields follow [physical DTOs](../backend/physical-dtos.md#cinematic-extension).

This is one aggregate validated plan, not an independently approved result. Render reads it through a deterministic adapter without a second universal request artifact. Unit IDs/order must map explicitly to the narrative/timed units; any additional terminal frame required by `flf2v` must be declared by the pipeline before rendering. Anchor units are separate from shot units: anchor existence never supplies or omits a shot frame implicitly.

Shot candidate-media revision is Critic -> Storyboard -> full shot render aggregate/join -> same selection gate. It cannot rewrite the anchor set's supporting VisualAnchorPlan, approved narrative, or selected anchors. Out-of-scope feedback returns a new request for the same subject, not a hidden Wardrobe call. Changing already approved anchors requires a new execution with Wardrobe-owned repair and new anchor review; dependent shot plans/results cannot remain current. Same-request technical retry belongs to Render. Selective reuse is currently specified only inside the anchor set, not across shot-plan revisions.

## Content And Quality Contract

- Each frame names its frame-unit ID, mapped story/timed unit and frame role, visible action state, subject references, composition, camera position/shot scale, pose/emotion, foreground/background depth, and concrete light/material cues.
- Depict a drawable moment of the approved shot's action without inventing a new story beat or redesigning its anchors.
- Reference the exact approved anchor assets with explicit roles and preserve/change constraints: face identity from the portrait, body proportions and wardrobe from the character sheet, spatial/material cues from the environment where applicable. Do not apply all reference backgrounds, poses, or lighting indiscriminately.
- Distinct shots have distinct visual functions that serve their beats. Repeated framing is allowed when intentional, not prompts duplicated with only IDs changed.
- Image prompts describe a drawable instant, not a temporal sequence. Negative constraints protect identity/continuity when supported by the frozen guidance; no universal provider syntax or fixed prompt length.
- Explicit endpoint frames depict the declared end state. Anchor reuse as a story frame requires an explicit mapping; it is never inferred merely because an image already exists.

Acceptance example: a hero shot preserves face identity from the approved portrait and wardrobe from the approved full-body sheet while staging the approved action in the environment anchor. All required references retain their roles through provider adaptation. A plan with duplicate unit IDs, a missing terminal endpoint, an unapproved identity change, or unsupported required multi-image references is rejected before rendering.

## Boundaries

- Does not design anchors or write anchor-generation prompts; consumes the exact complete approved anchor set and its validated supporting plan and preserves the selected design.
- Does not change declared narrative/timed unit count or order; additional endpoint frame units require an explicit pipeline mapping.
- Does not render, change the frozen generation profile, or plan motion.
- Does not infer selected media by scanning outputs.
- Uses only explicit approved anchors and context.
- Does not drop required references or replace multi-image roles with the earlier single-main-frame fallback.

## Tools

None. Authorized reference images and any bounded observations are prepared by the adapter; no provider, retrieval, or filesystem tools.

## Minimal System Prompt

```text
You are Storyboard, Kinodel's shot-frame planner. Use the supplied approved Brief, story/context, Wardrobe plan, and complete approved anchor set to compose each declared shot or timed unit as one drawable instant. Write shot image prompts with purposeful composition and visible action, binding exact anchor assets by face-identity, body/wardrobe, environment, or other declared roles and explicit preserve/change constraints. Preserve approved identity, style, order, and timing; never drop required references or replace them with a single-frame fallback. Return FramePlanV1 when ready, otherwise the declared needs_input or out_of_scope result. Do not design anchors, alter the narrative, render images, plan motion, change provider settings, or route the pipeline.
```
