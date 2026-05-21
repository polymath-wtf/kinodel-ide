# Render Request Contract

Planner artifacts stay provider-neutral. Worker adapters convert them into provider payloads.

## Envelope

```json
{
  "schema": "kinodel.render_requests.v1",
  "project_id": "project_id",
  "status": "complete",
  "stage": "main_frame|story_frames|shot_videos",
  "defaults": {
    "provider": "comfyui",
    "provider_edit": "comfyui",
    "provider_video": "comfyui",
    "provider_flf2v": "fal:veo31_lite_flf2v",
    "aspect_ratio": "1:1",
    "image_size": {"width": 1024, "height": 1024},
    "video_size": {"width": 480, "height": 480},
    "duration": "4s",
    "enable_audio": false
  },
  "jobs": [
    {
      "stage": "story_frames",
      "shot_id": "shot_01",
      "kind": "i2i",
      "render_prompt": "final image prompt",
      "input_media": ["https://.../main_frame.png"],
      "output_name": "shot_01.png"
    }
  ]
}
```

## Job fields

- `kind`: `t2i`, `i2i`, `i2v`, or `flf2v`.
- `render_prompt`: final visual/motion instruction.
- `input_media`: array of public URLs for external providers; required for `i2i`, `i2v`, `flf2v`.
- `output_name`: stable ergonomic filename.
- `shot_id`: optional but recommended for storyboard/video stages.

## Dimension defaults

Canonical image/video dimension tables live in `references/resolution-guide.md`. Planner agents should persist `brief.image.width/height` and `brief.video.width/height` when known, but request artifacts may stay provider-neutral; `render_worker.py` derives missing dimensions from sibling `brief.json`.

## Ownership boundary

`render-kinodel` is the only owner of runtime RenderJob normalization, provider selection, provider payload construction, status URLs, retries, and result summaries. Planner agents write only render-prompt-first request artifacts using `render_prompt` and `input_media`.

Project identity belongs to the request envelope (`project_id`), not to individual jobs. Producer passes runtime project context at launch time via explicit paths:

```bash
--request-file /tmp/kinodel/<project_id>/<run_id>/requests.json
--result-file /tmp/kinodel/<project_id>/<run_id>/results.json
--stage images|videos
--output-dir ~/projects/<project_id>/v1/outputs
```

## Forbidden in planner artifacts

- provider queue IDs
- status URLs
- response URLs
- raw provider responses
- retry state
- logs
- cost
- debug payloads
- ComfyUI workflow JSON

These belong in runtime scratch or worker debug output, not durable project knowledge.
