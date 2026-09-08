# Storyboard

Class: creative agent  
Status: **Active design**

## Responsibility

Translate story units and approved visual direction into model-guided image plans for the main continuity frame and later storyboard frames.

## Input

- approved Brief and VisualAnchorPlan;
- exact approved spine and its declared units: Story shots/acts, proposed Season episode blueprints, or proposed MusicPlan plus selected song and validated timing projection;
- exact promoted approved main/style/act anchors for later-frame modes; no generated anchor is required when planning that anchor itself;
- hydrated appearance/continuity/reference projections and frozen prompt guidance, with the operation's context-selection reference;
- previous exact FramePlan, reviewed candidate evidence, and `RevisionRequestV1` when repairing this image-plan owner's output;
- declared frame units/order and supported reference/image constraints; mapping is identity on Story shot IDs for first cinematic `i2v`, not a separate mapping object. The agent does not invent endpoint units.

Node-specific adapters hydrate these bodies from prepared refs. The durable selection trace alone is not agent context, and Season/music modes do not require a fabricated `StoryV1`.

The [cinematic declaration](../pipelines/cinematic.md#unit-contracts) supplies the single anchor key `main`. Storyboard writes its chosen existing `source_shot_id` and moment in FramePlan; the adapter freezes the unit declaration before the call, not this creative choice. Later-frame input includes that exact supporting plan and promoted anchor result. Selected rendered references use the [exact result plus unit selector](../backend/artifacts.md#selected-media-references), resolving AssetRefs rather than inventing frame IDs.

## Output

`FramePlanV1`: one ordered frame specification per declared unit, with exact selected-media references, semantic intent, model-targeted image prompt from the frozen `@prompt-engine` guidance, and optional timing window. These are creative units, not provider jobs. API payload mapping remains outside the artifact.

This is one aggregate validated plan, not an independently approved result. Render reads it through a deterministic adapter without a second universal request artifact. Unit IDs/order must map explicitly to the narrative/timed units; any additional terminal frame required by `flf2v` must be declared by the pipeline before rendering. The main frame is a continuity anchor, not implicitly shot one. Later frames declare what they preserve/change relative to exact approved anchors.

Candidate-media revision is Critic -> corresponding image-plan owner -> full render aggregate/join -> same selection gate. It cannot rewrite approved VisualAnchorPlan, narrative, or selected anchors. Out-of-scope feedback returns a new request for the same subject, not a hidden Wardrobe call. Same-request technical retry belongs to Render; selective reuse across creative revisions is deferred.

## Content And Quality Contract

- Each frame names its frame-unit ID, mapped story/timed unit and frame role, visible action state, subject references, composition, camera position/shot scale, pose/emotion, foreground/background depth, and concrete light/material cues.
- Main-frame mode chooses a representative moment from the approved spine and explains its suitability as the continuity anchor. It need not be shot one; it cannot invent a new story beat. The same owner chooses within the declared single anchor unit, not a new graph branch.
- Later-frame mode references the exact approved anchor assets and explicitly states what is preserved and what changes. Every reference has a semantic role; do not apply all reference backgrounds or poses indiscriminately.
- Distinct shots have distinct visual functions that serve their beats. Repeated framing is allowed when intentional, not prompts duplicated with only IDs changed.
- Image prompts describe a drawable instant, not a temporal sequence. Negative constraints protect identity/continuity when supported by the frozen guidance; no universal provider syntax or fixed prompt length.
- Explicit endpoint frames depict the declared end state. Main-anchor reuse as a story frame requires an explicit mapping; it is never inferred merely because an image already exists.

Acceptance example: an anchor taken from shot two still yields complete ordered coverage of all story frames. A plan with correct count but duplicate unit IDs, missing terminal endpoint, or an unapproved identity change is rejected before rendering.

## Boundaries

- Main-frame mode creates one continuity-anchor request; later frame modes preserve the approved anchor revision.
- Does not change declared narrative/timed unit count or order; additional endpoint frame units require an explicit pipeline mapping.
- Does not render, change the frozen generation profile, or plan motion.
- Does not infer selected media by scanning outputs.
- Uses only explicit approved anchors and context.

## Tools

None. Authorized reference images and any bounded observations are prepared by the adapter; no provider, retrieval, or filesystem tools.

## Minimal System Prompt

```text
You are Storyboard, Kinodel's frame planner. Convert each declared story or timed unit into one clear visual frame while preserving approved identity, style, order, and timing. Specify purposeful composition and preserve/change against exact supplied anchors. Return FramePlanV1 when ready, otherwise the declared needs_input or out_of_scope result. Do not alter the narrative, render images, plan motion, or choose provider settings.
```
