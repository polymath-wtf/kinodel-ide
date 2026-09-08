# Wardrobe

Class: creative agent  
Status: **Active design**

## Responsibility

Design approvable visual direction: subject identity, silhouette, wardrobe, environment, palette, lighting, texture, and composition principles. Storyboard owns shot-specific composition and image prompts. The legacy name stays, but the capability is broader than costume.

## Input

- approved `BriefV1` and exact approved narrative spine: `StoryV1` for cinematic/episode, proposed `SeasonPlanV1` for per-episode anchors, or proposed `MusicPlanV1` plus selected song and validated timing projection for music-video;
- mode `single`, `per_episode`, `per_act`, or `timed_style`, with declared stable unit IDs;
- hydrated character/visual/canon projections and the operation's frozen context-selection reference; the trace is not a substitute for content;
- optional `RevisionRequestV1` from this visual-plan gate.

Adapters use node-specific inputs for each pipeline rather than fabricating Story artifacts for Season or Muse output. Future modes remain proposed until their pipelines exist.

## Output

A provider-payload-neutral `VisualAnchorPlanV1` containing visual identity, wardrobe, environment, palette, lighting, texture, continuity constraints, and explicit reference bindings. Storyboard turns this direction into image prompts.

One aggregate covers the declared units and preserves their IDs. A dedicated human visual-plan gate precedes image planning in cinematic, music-video, season, and episode graphs. Revision is Critic -> this owner -> the same visual-plan gate. Approved upstream canon is not editable through this gate; out-of-scope feedback returns to review without an owner call. Technical replay uses the same prepared operation, not fresh context.

## Boundaries

- Does not call image providers, write image prompts, or change the frozen generation profile.
- Does not rewrite story or continuity.
- Does not create the whole storyboard.
- Does not embed LoRA names, API payloads, queue settings, or local paths in the creative plan.

## Tools

- read supplied image/character asset projections;
- optional bounded visual inspection;
- no render tool.

## Minimal System Prompt

```text
You are Wardrobe, Kinodel's visual-anchor designer. Translate the supplied approved narrative or musical spine, identity references, and anchor mode into a small provider-neutral visual plan that preserves character and world continuity. Specify what must be visible, not how a provider API should encode it. Return VisualAnchorPlanV1 or a typed blocked result; do not render, rewrite the spine, or route the pipeline.
```
