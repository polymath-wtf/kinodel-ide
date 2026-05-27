# Kinodel Artifact Contracts

## Purpose

Artifacts are the production truth. LangGraph state stores only references to them.

The new rule is:

```text
artifact = typed durable product boundary
runtime state = compact pointer/checkpoint boundary
provider scratch = disposable execution boundary
```

## Durable project artifacts

| Artifact | Owner | Purpose |
| --- | --- | --- |
| `pipeline_spec.json` | `PipelineRegistry` | Frozen per-project graph contract. |
| `brief.json` | BriefGate / ProjectStore | User-approved creative and technical production parameters. |
| `story.json` | `storytell-kinodel` | Narrative arc and renderable shot beats. |
| `wardrobe_request.json` | `wardrobe-kinodel` | Main-frame provider-neutral render request. |
| `storyboard_requests.json` | `storyboard-kinodel` | Story-frame provider-neutral render requests. |
| `video_requests.json` | `filmmaker-kinodel` | Video provider-neutral render requests. |
| `render_results/main_frame_result.json` | `RenderService` | Selected main-frame refs. |
| `render_results/story_frames_result.json` | `RenderService` | Selected story-frame refs. |
| `render_results/shot_videos_result.json` | `RenderService` | Selected clip refs. |
| `outputs/final.mp4` | `MontageService` | Final assembled video. |
| `final_chunk.json` | `ChunkService` / `craft-kinodel` | Minimal final cinematic memory. |
| `chunks/cinema_chunk.json` | `craft-kinodel` | Reusable indexed memory after final approval. |

## Common JSON invariants

- **`project_id`** — top-level and equal to `brief.json.project_id`.
- **`schema`** — explicit schema ID.
- **`status`** — working artifacts use `pending` or `complete`; downstream stages require `complete`.
- **Atomic ownership** — one stage owns one write artifact unless the spec declares otherwise.
- **No provider scratch** — provider queue IDs, logs, raw responses, retries, costs, and debug payloads never enter planner artifacts.

## Brief contract

`brief.json` stores user-approved production intent:

- `user_vibe`
- `platform`
- `aspect_ratio`
- `shot_count`
- `image` technical settings
- `video` technical settings and workflow
- optional provider family defaults

Do not use old ad-hoc fields like `concept`, `output_mode`, `video.enabled`, or `inferred` as live contract fields.

## Render request contract

Planner agents write `kinodel.render_requests.v1`:

```json
{
  "schema": "kinodel.render_requests.v1",
  "project_id": "project",
  "status": "complete",
  "stage": "story_frames",
  "jobs": [
    {
      "kind": "i2i",
      "shot_id": "shot_01",
      "render_prompt": "final prompt",
      "input_media": ["https://public/ref.png"],
      "output_name": "shot_01.png"
    }
  ]
}
```

Allowed job kinds for cinematic v1:

- `t2i`
- `i2i`
- `i2v`
- `flf2v`

`input_media` must be an array. External providers require public HTTP(S) URLs.

## Render result contract

RenderService writes `kinodel.render_result.v1`:

```json
{
  "schema": "kinodel.render_result.v1",
  "project_id": "project",
  "status": "complete",
  "stage": "story_frames",
  "selected_outputs": [
    {
      "shot_id": "shot_01",
      "kind": "image",
      "path": "outputs/shot_01.png",
      "url": "https://public/shot_01.png"
    }
  ]
}
```

Downstream chaining uses `selected_outputs`, not filesystem discovery.

## Final chunk contract

`final_chunk.json` contains only the completed cinematic:

- story or summary
- hook
- anchor/main-frame ref
- 1-5 story image refs
- optional final video ref when the app produced montage media
- conclusion

It must not contain runtime prompts, render job IDs, provider responses, logs, QC notes, pipeline state, or intermediate alternatives.

## Validator map

Validators should be backend services, not Producer prose:

- `kinodel.brief.v1`
- `kinodel.story.v1`
- `kinodel.render_requests.v1`
- `kinodel.render_result.v1`
- `kinodel.montage_output.v1`
- `kinodel.final_chunk.v1`
- `kinodel.cinema_chunk.v1`

Every graph node exits through validation before the next edge.
