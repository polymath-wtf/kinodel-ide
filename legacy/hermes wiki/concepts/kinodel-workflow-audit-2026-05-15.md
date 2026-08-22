# Kinodel workflow audit — 2026-05-15

## Diagnosis

Kinodel broke because three architectural directions were mixed together:

1. Old autonomous ReviewGate experiments: timeout approval / inline preview / continue downstream.
2. Later STOP_AT_GATE invariant: BriefGate, p4, p7 are hard turn-boundary user gates.
3. Artifact-centric state machine: Producer should pass paths and selected refs, not full JSON bodies or provider logs.

The restored checkpoint reintroduced some stale language, especially in `producer-kinodel` and duplicated `pipeline-kinodel/references/producer-playbook.md`.

## Immediate fixes applied

- Removed the stale autonomous ReviewGate override from `producer-kinodel`.
- Replaced CLI-hostile `MEDIA:/path` wording with platform-neutral preview refs.
- Re-aligned provider defaults to user-confirmed Kinodel defaults:
  - images/story frames: `fal:nano_banana_2`, 9:16 `image_size` 576x1024;
  - videos: `fal:veo31_lite_i2v`, 4s, 720p, audio off;
  - ComfyUI is backup only.
- Updated `render-kinodel/scripts/fal.py` so default t2i/i2i providers are Nano Banana 2 and the normalized payload carries `image_size`.
- Added explicit `/goal` state machine reference: `pipeline-kinodel/references/goal-pipeline.md`.
- Added explicit artifact sandwich reference: `pipeline-kinodel/references/artifact-layers-l0-l6.md`.

## Proposed slim skill architecture

### pipeline-kinodel
Keep as the short law + route map only:
- factory law;
- canonical goal list;
- hard gate invariant;
- artifact contracts;
- links to references.

Move examples, incidents, verbose tables, and provider payload details out of the hot path.

### producer-kinodel
Keep as a thin runtime checklist:
- current goal;
- validate input artifact;
- run owner stage;
- validate output artifact;
- stop at gates;
- launch packaged render worker.

Do not store HTTP payload templates, long incident histories, or provider details here.

### render-kinodel
Own all provider payload mappings, queue polling, downloads, and public URL rules.

### comfyui
Own all ComfyUI-specific troubleshooting and API references. Pipeline skills should only say: ComfyUI is a backup provider; see `comfyui` / `render-kinodel` for low-level details.

## /goal pipeline

Use explicit checkpoint names:

- p0_briefgate
- p1_init_project
- p2_story
- p3_main_frame_plan
- p4_render_main_frame
- p5_review_story_main_frame
- p6_storyboard_plan
- p7_render_story_images
- p8_review_story_images
- p9_video_plan
- p10_render_videos
- p11_montage
- p12_final_chunk

p5 and p8 are hard stops. Render completion only unlocks the review goal; it never approves it.

## Artifact sandwich L0-L6

- L0: pipeline law and gate rules.
- L1: project identity and current goal.
- L2: brief path + tiny derived summary.
- L3: creative artifact paths.
- L4: render_results selection manifests.
- L5: selected media path+url pairs needed by the next stage.
- L6: runtime scratch, provider ids, logs, retries; never given to creative agents.

Producer passes L1-L5 envelopes to stage owners. L6 stays under `/tmp/kinodel/<project_id>/<run_id>/`.

## Next refactor batch

1. Shrink `pipeline-kinodel/SKILL.md` from ~458 lines to ~150-180 lines by moving examples into references.
2. Shrink `render-kinodel/SKILL.md` from ~395 lines by moving ComfyUI troubleshooting into `comfyui` and keeping only provider maps + worker contract.
3. Remove duplicated `producer-playbook.md` content or make `producer-kinodel` load it as its only detailed reference.
4. Consolidate reference folders:
   - provider payloads → `render-kinodel/references/`;
   - ComfyUI API/debugging → `comfyui/references/`;
   - pipeline laws/goals/artifact contracts → `pipeline-kinodel/references/`;
   - stage-specific creative contracts → either each specialist skill's references or compact pipeline links.
5. Add a small validator script that checks before every transition:
   - JSON parses;
   - `project_id` matches;
   - `status == complete` where required;
   - `jobs` non-empty before render;
   - public URLs for external i2i/i2v/flf2v;
   - p5/p8 gate state cannot be bypassed.
