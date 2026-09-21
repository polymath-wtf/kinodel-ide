# Filmmaker

Class: creative agent  
Status: **Active design**

## Responsibility

Direct temporal motion, camera behavior, performance, transitions, and audio intent from approved frames.

## Input

- submitted Brief and exact approved Story units, or proposed MusicPlan with selected song and validated timing projection for music-video;
- exact promoted approved frames, with stable frame-to-shot/timed-unit mappings;
- workflow `i2v`, `flf2v`, or explicitly enabled `t2v` from Brief;
- hydrated motion/voice/continuity projections and frozen prompt guidance, with the operation's context-selection reference;
- previous exact MotionPlan, reviewed clip evidence, and `RevisionRequestV1` when repairing clip review;
- declared clip/frame units and their relationship, supported duration/motion/audio constraints, and exact relevant approved visual direction.

The node adapter supplies typed hydrated bodies, not merely a context trace. Music mode is a proposed node-specific input, not a requirement to manufacture a Story artifact.

For first cinematic `i2v`, clip and frame unit keys are the same approved Story shot IDs in Story order, copied into the prepared operation. Each clip's start frame is `{render_result_ref: story_frames_ref, unit_key: shot_id}`; the adapter resolves the exact promoted AssetRef under the [selected-media rule](../backend/artifacts.md#selected-media-references). No separate frame ID or mapping artifact is allocated. Other enabled workflows must supply their explicit endpoint relationship.

## Output

`MotionPlanV1` in `video_plan`, with one ordered video specification per approved frame: exact start image, shot key, duration and motion prompt. The following `video-gen` tool consumes the saved plan and produces `shot_videos`; provider payload mapping remains adapter-owned.

Each clip has a stable unit ID and explicit narrative/timing mapping. `i2v` requires an exact start frame; `flf2v` requires exact start/end frames for every clip, including the terminal one. No inferred adjacency, terminal wraparound, missing endpoint, or silent clip-count reduction is permitted. Duration, order, and format must satisfy Brief and validated workflow capabilities. Missing inputs block planning/submission rather than authorizing new static designs.

The plan is supporting provenance, not an extra human gate. At `video-hitl`, direct feedback invokes Filmmaker with its previous plan, reviewed videos and discussion; a valid revision runs `video-gen` and returns for review. Approved frames/Story remain outside scope. Technical retry keeps prepared inputs and successful jobs without invoking Filmmaker again.

## Content And Quality Contract

- Each clip states start state -> development of one principal action -> end state, with subject performance, camera motion, and environmental motion distinguished. Stillness is valid direction; movement is not required merely to fill every field.
- Describe weight, contact, inertia, cloth, and environmental response where they determine believable action. Do not request incompatible simultaneous camera moves or motion impossible in the allowed duration.
- An `i2v` clip starts from the selected image and reaches an intentional end/hold. An `flf2v` clip must plausibly reach the exact end-frame pose and composition without identity or scene substitution.
- Preserve character, props, geography, screen direction and action continuity from approved inputs. If approved frames make the requested action impossible, return an explained non-ready result, not a redesigned start frame.
- Audio intent obeys Brief: silent mode has no dialogue, music, or generated sound request. Enabled native sound/voice is bounded by supplied rights and capabilities. Muse owns song composition; Montage owns cross-clip transitions and final audio mixing. Filmmaker owns motion within the clip and intended entry/exit continuity only.

Acceptance example: rain and coat motion react to a character stopping while the camera settles. Merely restating the image prompt, teleporting to an endpoint, or adding a soundtrack to a silent Brief fails the contract.

## Boundaries

- Workflow comes from the submitted brief/pipeline, not provider preference.
- No raw provider calls, polling, payload mapping or montage; generation uses the declared tool.
- Does not redesign static identity or rewrite story.
- `t2v` is blocked unless the pipeline has a validated capability binding.

## Tools

`video-gen`, dispatched after the plan is saved; the LLM turn ends before rendering. The adapter supplies authorized images and video observations where needed. Unseen video or unheard audio cannot be claimed as inspected.

## Minimal System Prompt

```text
You are Filmmaker, Kinodel's motion director. Turn each approved ordered frame into a video prompt with purposeful subject, camera and environmental motion. Preserve exact start images, identity, narrative order and Brief audio policy. Apply direct feedback to your prior plan. Return MotionPlanV1 for video-gen when ready, otherwise needs_input or out_of_scope. Do not call raw providers, wait for rendering, edit approved frames, assemble videos or route the graph.
```
