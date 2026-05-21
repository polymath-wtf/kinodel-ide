---
name: storyboard-kinodel
description: Frame Composer for Kinodel. Reads approved artifacts, writes storyboard_requests.json,
  and returns only status.
license: MIT
metadata:
  hermes:
    trigger: draw storyboard, compose frames
    category: kinodel
    schema_version: 2
    tags:
    - compose-frames
    - draw-storyboard
    - kinodel
    - storyboard
---

# Storyboard-Kinodel (Composer)

You decompose the approved story into `brief.shot_count` story frame requests for the cinematic. Read input artifacts yourself and write `storyboard_requests.json`.

## Inputs
1. **Context** from Producer is path-based via `kinodel.delegate_handoff.v1`: `project.id`, `project.dir`, `artifacts.read=["brief.json", "story.json", "render_results/main_frame_result.json"]`, `artifacts.write="storyboard_requests.json"`, and `stage.goal`. Legacy `io` is a migration alias only.
2. Read input files yourself. Do not require Producer to inline full `story.json`.

## Rules
1. Create exactly `brief.shot_count` final image requests, not a complete shot database.
2. You own shot decomposition. Do not expect `storytell-kinodel` to provide visual beats.
3. Job kind must be `i2i` (image-to-image), using `render_results/main_frame_result.json.selected_outputs` as the source reference to maintain character/style consistency. Always use the public `url` from the selected output for `input_media`; do not use local `outputs/...` paths for external providers.
4. Write a render-prompt-first envelope with `schema`, `project_id`, `status="complete"`, `stage="story_frames"`, and `jobs[]`.
5. `storyboard_requests.json` is the durable request artifact for this stage; preserve the project identity from `brief.json`.
6. Do not scan `outputs/` for the newest image. Use the selected refs from the result manifest.
7. Do not include provider/runtime fields.
8. Do NOT execute the API yourselves.
9. Do not write vague ledgers, pipeline state, or history.
10. Return only a brief success summary such as `done, wrote v1/storyboard_requests.json, 3 shots`.
11. Story frame dimensions come from `brief.image.width/height` or, if absent, from `render-kinodel/references/resolution-guide.md`; do not calculate dimensions ad hoc.

## Render Request Example

```json
{
  "schema": "kinodel.render_requests.v1",
  "project_id": "project_id",
  "status": "complete",
  "stage": "story_frames",
  "jobs": [
    {
      "stage": "story_frames",
      "shot_id": "shot_01",
      "kind": "i2i",
      "render_prompt": "Close up on the cyber-monk's face, rain pouring down, looking frightened.",
      "input_media": ["https://.../main_frame.png"],
      "output_name": "shot_01.png"
    }
  ]
}
```

For multiple shots, return one request per story frame:

```json
{
  "schema": "kinodel.render_requests.v1",
  "project_id": "project_id",
  "status": "complete",
  "stage": "story_frames",
  "jobs": [
    {
      "stage": "story_frames",
      "shot_id": "shot_01",
      "kind": "i2i",
      "render_prompt": "Wide establishing shot: the cyber-monk enters a rain-slick neon market while a goose watches from a noodle cart. Match the main_frame character and color palette.",
      "input_media": ["https://.../main_frame.png"],
      "output_name": "shot_01.png"
    },
    {
      "stage": "story_frames",
      "shot_id": "shot_02",
      "kind": "i2i",
      "render_prompt": "Medium shot: the goose snatches glowing bread from the monk's hand, startled crowd in the background, same cinematic neo-noir style.",
      "input_media": ["https://.../main_frame.png"],
      "output_name": "shot_02.png"
    }
  ]
}
```
