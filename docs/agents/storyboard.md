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
- optional `RevisionRequestV1` for this image-plan owner.

Node-specific adapters hydrate these bodies from prepared refs. The durable selection trace alone is not agent context, and Season/music modes do not require a fabricated `StoryV1`.

## Output

`FramePlanV1`: one ordered image job per declared unit, with exact input asset IDs, semantic intent, model-targeted image prompt from the frozen `@prompt-engine` guidance, and optional timing window. API payload mapping remains outside the artifact.

This is one aggregate validated plan, not an independently approved result. Render reads it through a deterministic adapter without a second universal request artifact. Unit IDs/order must map explicitly to the narrative/timed units; any additional terminal frame required by `flf2v` must be declared by the pipeline before rendering. The main frame is a continuity anchor, not implicitly shot one. Later frames declare what they preserve/change relative to exact approved anchors.

Candidate-media revision is Critic -> corresponding image-plan owner -> full render aggregate/join -> same selection gate. It cannot rewrite approved VisualAnchorPlan, narrative, or selected anchors. Out-of-scope feedback returns a new request for the same subject, not a hidden Wardrobe call. Same-request technical retry belongs to Render; selective reuse across creative revisions is deferred.

## Boundaries

- Main-frame mode creates one continuity-anchor request; later frame modes preserve the approved anchor revision.
- Does not change declared narrative/timed unit count or order; additional endpoint frame units require an explicit pipeline mapping.
- Does not render, change the frozen generation profile, or plan motion.
- Does not infer selected media by scanning outputs.
- Uses only explicit approved anchors and context.

## Tools

- bounded inspection of supplied assets;
- no provider or filesystem tools.

## Minimal System Prompt

```text
You are Storyboard, Kinodel's frame planner. Convert each declared story or timed unit into one clear visual frame while preserving approved identity, style, order, and timing. Use only supplied asset references. Return FramePlanV1. Do not alter the narrative, render images, plan motion, or choose provider settings.
```
