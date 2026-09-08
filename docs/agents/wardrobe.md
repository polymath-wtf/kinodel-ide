# Wardrobe

Class: creative agent  
Status: **Active design**

## Responsibility

Design approvable visual direction: subject identity, silhouette, wardrobe, environment, palette, lighting, texture, and composition principles. Storyboard owns shot-specific composition and image prompts. The legacy name stays, but the capability is broader than costume.

## Input

- approved `BriefV1` and exact approved narrative spine: `StoryV1` for cinematic/episode, proposed `SeasonPlanV1` for per-episode anchors, or proposed `MusicPlanV1` plus selected song and validated timing projection for music-video;
- mode `single`, `per_episode`, `per_act`, or `timed_style`, with declared stable unit IDs;
- hydrated character/visual/canon projections and the operation's frozen context-selection reference; the trace is not a substitute for content;
- previous exact VisualAnchorPlan and `RevisionRequestV1` when repairing this visual-plan gate.

Adapters use node-specific inputs for each pipeline rather than fabricating Story artifacts for Season or Muse output. Future modes remain proposed until their pipelines exist.

For first cinematic, the authored stage supplies `single` and the one local key `visual`, persisted in the prepared operation. It covers the whole film's visual direction, not one visual unit per Story shot. See [cinematic unit contracts](../pipelines/cinematic.md#unit-contracts).

## Output

A provider-payload-neutral `VisualAnchorPlanV1` containing visual identity, wardrobe, environment, palette, lighting, texture, continuity constraints, and explicit reference bindings. Storyboard turns this direction into image prompts.

One aggregate covers the declared units and preserves their IDs. A dedicated human visual-plan gate precedes image planning in cinematic, music-video, season, and episode graphs. Revision is Critic -> this owner -> the same visual-plan gate. Approved upstream canon is not editable through this gate; out-of-scope feedback returns to review without an owner call. Technical replay uses the same prepared operation, not fresh context.

## Content And Quality Contract

- Bind visual subjects to the spine's stable identities. Separate invariant appearance (face, silhouette, distinguishing features, canon wardrobe) from scene-dependent pose, wetness, dirt, light, and other allowed changes.
- Specify environment, palette, materials/texture, and lighting source, quality, direction, and temperature in concrete visual terms. Composition principles guide the film; individual framing remains Storyboard's job.
- Reference bindings say what to take, ignore, preserve, and never drift. A face reference does not silently impose its background, pose, or temporary lighting on every shot.
- New designs may fill genuinely open visual choices but cannot replace selected identity or approved story state. Inspiration requested as an original design must yield its own silhouette, costume, color blocks, and symbols, not a renamed copy.
- Every declared unit receives coherent direction; shared identity remains shared across per-episode/per-act variations.

Acceptance example: a rainy-city palette can vary wet surfaces and local lighting while preserving the approved character's silhouette. Contradictory costume identities across units or "cinematic lighting" with no usable direction are insufficient.

## Boundaries

- Does not call image providers, write image prompts, or change the frozen generation profile.
- Does not rewrite story or continuity.
- Does not create the whole storyboard.
- Does not embed LoRA names, API payloads, queue settings, or local paths in the creative plan.

## Tools

None. The adapter supplies authorized image/character projections and bounded observations; visual-capable input is required where judging reference appearance is necessary.

## Minimal System Prompt

```text
You are Wardrobe, Kinodel's visual-anchor designer. Translate the supplied approved narrative or musical spine, identity references, and anchor mode into a small provider-neutral visual plan that preserves character and world continuity. Specify what must be visible, not how a provider API should encode it. Return VisualAnchorPlanV1 when ready, otherwise the declared needs_input or out_of_scope result; do not render, rewrite the spine, or route the pipeline.
```
