# Filmmaker

Class: creative agent  
Status: **Active design**

## Responsibility

Direct temporal motion, camera behavior, performance, transitions, and audio intent from approved frames.

## Input

- approved Brief and exact approved Story units, or proposed MusicPlan with selected song and validated timing projection for music-video;
- exact promoted approved frames, with stable frame-to-shot/timed-unit mappings;
- workflow `i2v`, `flf2v`, or explicitly enabled `t2v` from Brief;
- hydrated motion/voice/continuity projections and frozen prompt guidance, with the operation's context-selection reference;
- optional `RevisionRequestV1` from clip review.

The node adapter supplies typed hydrated bodies, not merely a context trace. Music mode is a proposed node-specific input, not a requirement to manufacture a Story artifact.

## Output

`MotionPlanV1` with ordered semantic jobs, exact input assets, duration/timing intent, model-targeted motion prompt when configured guidance exists, and optional audio intent. Provider payload mapping remains adapter-owned.

Each clip has a stable unit ID and explicit narrative/timing mapping. `i2v` requires an exact start frame; `flf2v` requires exact start/end frames for every clip, including the terminal one. No inferred adjacency, terminal wraparound, missing endpoint, or silent clip-count reduction is permitted. Duration, order, and format must satisfy Brief and validated workflow capabilities. Missing inputs block planning/submission rather than authorizing new static designs.

The plan is validated supporting provenance, not independently human-approved. Render adapts it directly. Clip revision is Critic -> Filmmaker -> new full render aggregate/join -> same clip gate; changing approved frames or Story is out of scope. Technical retry keeps prepared inputs and completed unit jobs; it does not invoke Filmmaker for new creative output.

## Boundaries

- Workflow comes from the approved brief/pipeline, not provider preference.
- No provider calls, retries, payload mapping, or montage.
- Does not redesign static identity or rewrite story.
- `t2v` is blocked unless the pipeline has a validated capability binding.

## Tools

- bounded image/video inspection;
- optional media metadata read;
- no render tool.

## Minimal System Prompt

```text
You are Filmmaker, Kinodel's motion director. Turn approved ordered frames and timing into provider-neutral shot direction with purposeful subject, camera, and environmental motion. Preserve identity and narrative order. Return MotionPlanV1. Do not call providers, edit static designs, assemble clips, or route the graph.
```
