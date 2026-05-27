# Mid-pipeline video flow changes

Use this reference when the user changes video flow/provider/duration after p7 or after `video_requests.json` already exists.

## Failure pattern

A late request such as `switch to i2v comfyui`, `2s clips`, or `not flf2v` changes production intent, but existing downstream artifacts may still contain stale `flf2v` transition jobs. Rendering that stale artifact can silently route to fal first-last-frame video and ignore the user's new ComfyUI/i2v intent until provider failure.

## Root cause

Kinodel request artifacts are durable state. Changing `brief.json` alone does not mutate already-written request artifacts. The render worker receives the request file and its defaults; it does not infer intent from chat history.

## Required repair sequence

1. Update `brief.json` with durable fields:
   - `video.flow`: `i2v` or `flf2v`
   - `video.seconds_per_shot` / `video.duration`
   - `provider_video` or `video.provider`
2. Regenerate the affected downstream request artifact, usually `video_requests.json`.
3. For `i2v`, write one job per approved story frame:
   - `kind: "i2v"`
   - one `input_media` URL from `render_results/story_frames_result.json.selected_outputs[].url`
   - `shot_id: "shot_01"`, `shot_02`, ...
   - `defaults.provider_video: "comfyui"` or concrete `local-comfyui:img2vid_wan_lora` when requested
4. For `flf2v`, write neighboring transition jobs:
   - `kind: "flf2v"`
   - two `input_media` URLs: first and last frame
   - `shot_id: "shot_01_to_shot_02"`, ...
   - standard duration is 8s unless a provider explicitly supports otherwise
5. Run:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py validate \
  --project-dir ~/projects/<project_id>/v1 \
  --artifact video_requests.json
```

6. Only launch `render-kinodel` after validation passes.

## Anti-patterns

- Do not patch only `brief.video.seconds_per_shot` and render an old `video_requests.json`.
- Do not rely on live chat text like “i2v comfyui” to reach the render worker; persist it into the artifact.
- Do not infer current media from `outputs/`; use `render_results/*.json.selected_outputs`.
