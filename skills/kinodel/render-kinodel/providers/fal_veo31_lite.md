# fal.ai Veo 3.1 Lite

Balanced Kinodel provider contract for Veo 3.1 Lite. This file is the short overview; load the mode-specific docs for exact body shapes.

## Canonical endpoints
- i2v: `fal-ai/veo3.1/lite/image-to-video`
- flf2v: `fal-ai/veo3.1/lite/first-last-frame-to-video`
- submit: `POST https://queue.fal.run/<endpoint>`
- poll using returned `status_url`
- fetch final result using returned `response_url`

## What Kinodel uses it for
- `i2v`: animate a single approved still
- `flf2v`: create transition clips between neighboring approved story frames

## Kinodel defaults
- i2v duration: `4s`
- flf2v duration: `8s`
- resolution: `480p`
- `generate_audio: false` unless brief explicitly enables audio
- `safety_tolerance: "4"`
- aspect ratio usually `"auto"`, unless the worker/project chooses explicit vertical video rules

## Queue lifecycle
Typical submit response:
```json
{
  "request_id": "uuid",
  "status": "IN_QUEUE",
  "status_url": "https://queue.fal.run/.../requests/uuid/status",
  "response_url": "https://queue.fal.run/.../requests/uuid"
}
```

Typical status progression:
- `IN_QUEUE`
- `IN_PROGRESS`
- `COMPLETED` / `FAILED` / `CANCELLED`

Important:
- use returned `status_url` / `response_url`
- do not hand-construct queue URLs
- final success payload contains `video.url`

## Final result shape to check
```json
{
  "video": {
    "url": "https://storage.googleapis.com/falserverless/...",
    "content_type": "video/mp4",
    "file_name": "...mp4"
  }
}
```

Worker success checks:
1. terminal status is `COMPLETED`
2. `video.url` exists
3. download succeeds
4. file lands in expected output slot

## Critical rules
1. i2v uses `image_url`.
2. flf2v uses `first_frame_url` + `last_frame_url`.
3. External inputs must be public URLs from `render_results/*.json.selected_outputs[].url`.
4. Do not persist raw provider responses into durable project state.

## Load next
- `providers/fal_veo31_lite_i2v.md` — single-image animation details
- `providers/fal_veo31_lite_flf2v.md` — transition clip details
- `references/fal-api-troubleshooting.md` — queue/public-URL fixes
