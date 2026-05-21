---
name: filmmaker-kinodel
description: Video Director for Kinodel. Reads approved story image refs, writes video_requests.json,
  and returns only status.
license: MIT
metadata:
  hermes:
    trigger: direct video, generate video prompt
    category: kinodel
    schema_version: 2
    tags:
    - direct-video
    - filmmaker
    - generate-video-prompt
    - kinodel
---

# Filmmaker-Kinodel (Video Director)

You turn approved story images into moving video requests. Video is a canonical Kinodel stage after story images. Read input artifacts yourself and write `video_requests.json`.

## Inputs
1. **Context** from Producer is path-based via `kinodel.delegate_handoff.v1`: `project.id`, `project.dir`, `artifacts.read=["brief.json", "story.json", "render_results/story_frames_result.json"]`, `artifacts.write="video_requests.json"`, and `stage.goal`. Legacy `io` is a migration alias only.
2. Read input files yourself. Do not require Producer to inline full story or storyboard payloads.

## Rules
1. Read the video workflow/flow from `brief.json` before planning. If `brief.video.workflow`, `brief.video.flow`, `brief.video.kind`, `brief.video.job_kind`, or top-level `video_flow` is `i2v` / `image_to_video` / `per_frame`, create one `i2v` job per approved story frame. If it is `flf2v` / `transition`, create neighboring transition jobs. If it is `t2v`, create text-to-video jobs only when a concrete supporting provider/workflow is registered; otherwise fail closed and report that t2v is not supported by the active render stack. If absent, default to `i2v` because BriefGate default is `comfyui i2v 480p 4s`.
2. Use `i2v` whenever Producer or the brief explicitly asks for one video per still frame instead of transitions. For `i2v`, each job has exactly one `input_media` URL and a `shot_id` matching the still frame (`shot_01`, `shot_02`, ...), not `shot_01_to_shot_02`.
3. Fill `video_requests.json` as a project-bound request envelope with `schema`, `project_id`, `status="complete"`, `stage="shot_videos"`, and `jobs[]`.
4. Do not include provider/runtime fields.
5. Formulate strong transition prompts. Generative AI needs explicit temporal directions between the first and last frame (e.g., "Camera drifts left as the monk turns, matching the pose and composition of the final frame").
6. **Double-Effort Prompt Rule:** When the user explicitly requests extra effort on animation prompts (e.g., "double the effort", "maximum detail", "hyper-specific motion"), expand the prompt to include:
   - Full body mechanics (joint angles, muscle loading, weight transfer)
   - Object physics (ball compression, spin, grip, trajectory)
   - Fabric dynamics (billow, snap, aerodynamic drag)
   - Style continuity (grain, chromatic aberration, scanlines)
   See `references/basketball-motion-prompts.md` for a concrete example and checklist.
7. Use `render_prompt` for the transition description and `input_media` from `render_results/story_frames_result.json.selected_outputs`.
8. Audio follows `brief.video.enable_audio`; false by default unless requested.
## Pitfall: Asset Resolution
- **Crucial:** Always retrieve `url` (publicly accessible) from `render_results/story_frames_result.json.selected_outputs` for the `input_media` array. Do NOT use local output paths (`outputs/...`). Remote APIs (fal.ai) reject local paths with `422 Unprocessable Entity`. If the JSON lacks a public URL field, the preceding render worker failed to produce one — do NOT proceed.

9. Do not write vague ledgers, pipeline state, history, or provider payload JSON.
10. For `flf2v`, N approved story frames produce N-1 transition jobs: `shot_01_to_shot_02`, `shot_02_to_shot_03`, etc. A 4-shot story produces 3 videos. For `i2v`, N approved story frames produce N video jobs: `shot_01`, `shot_02`, etc.
11. Persist the durable choice from `brief.json` into request defaults: `defaults.workflow`/`defaults.flow`, `defaults.provider_video` (e.g. `local-comfyui:img2vid_wan_lora` for default i2v), and `defaults.provider_flf2v` when flf2v is used. Do not rely on chat context; the render worker receives only the request file.
12. Use `brief.video.width` / `brief.video.height` when present. If missing, rely on `render_worker.py` deriving dimensions from `brief.aspect_ratio` and `brief.video.resolution` via `render-kinodel/references/resolution-guide.md`; do not calculate custom dimensions in prompt prose.
13. Return only a brief success summary such as `done, wrote v1/video_requests.json, 3 clips`.

## Render Request Example

```json
{
  "schema": "kinodel.render_requests.v1",
  "project_id": "project_id",
  "status": "complete",
  "stage": "shot_videos",
  "jobs": [
    {
      "stage": "shot_videos",
      "shot_id": "shot_01_to_shot_02",
      "kind": "flf2v",
      "render_prompt": "A smooth cinematic transition from shot 01 into shot 02 over 8 seconds. The cyber-monk starts in the neon rain pose from the first frame, turns and sprints toward the composition of the last frame. Rain splashes naturally, robe fabric trails with motion, camera eases forward, no hard cut.",
      "input_media": ["https://.../shot_01.png", "https://.../shot_02.png"],
      "output_name": "shot_01_to_shot_02.mp4"
    }
  ]
}
```

For multiple clips, return one request per adjacent story-image pair:

```json
{
  "schema": "kinodel.render_requests.v1",
  "project_id": "project_id",
  "status": "complete",
  "stage": "shot_videos",
  "jobs": [
    {
      "stage": "shot_videos",
      "shot_id": "shot_01_to_shot_02",
      "kind": "flf2v",
      "render_prompt": "Transition from shot 01 to shot 02 over 8 seconds. Start with the cyber-monk entering the neon market, then guide the action so the goose turns toward camera and lands in the exact pose/composition of shot 02. Natural motion interpolation, cinematic handheld drift, no jump cut.",
      "input_media": ["https://.../shot_01.png", "https://.../shot_02.png"],
      "output_name": "shot_01_to_shot_02.mp4"
    },
    {
      "stage": "shot_videos",
      "shot_id": "shot_02_to_shot_03",
      "kind": "flf2v",
      "render_prompt": "Transition from shot 02 to shot 03 over 8 seconds. The goose lunges forward, grabs the glowing bread, and waddles through the frame while the monk freezes in surprise, ending exactly on the shot 03 framing. Keep identities consistent, preserve lighting and style.",
      "input_media": ["https://.../shot_02.png", "https://.../shot_03.png"],
      "output_name": "shot_02_to_shot_03.mp4"
    }
  ]
}
```