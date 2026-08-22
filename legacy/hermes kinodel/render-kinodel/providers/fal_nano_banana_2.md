# fal.ai Nano Banana 2

Balanced Kinodel provider contract for Nano Banana 2. This file is the short overview; load the mode-specific docs for full request examples.

## Canonical endpoints
- t2i: `fal-ai/nano-banana-2`
- i2i/edit: `fal-ai/nano-banana-2/edit`
- submit: `POST https://queue.fal.run/<endpoint>`
- poll: `GET .../requests/{request_id}/status`
- fetch final result: `GET .../requests/{request_id}` after `COMPLETED`

## What Kinodel uses it for
- `t2i`: main frame / first anchor generation
- `i2i`: story-frame generation and image edits chained from prior approved refs

## Kinodel defaults
- `num_images: 1`
- `output_format: "png"`
- `resolution: "1K"`
- `safety_tolerance: "4"`
- vertical default: `aspect_ratio: "9:16"`
- for explicit vertical anchor sizing in the worker, prefer `image_size: {"width": 576, "height": 1024}`
- `limit_generations: true`
- `enable_web_search: false`

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
- HTTP 202 during polling is normal while the job is still running.
- Do not fetch the final response endpoint before terminal completion.

## Final result shape to check
Successful final response contains:
```json
{
  "images": [
    {
      "file_name": "nano-banana-2-...png",
      "url": "https://storage.googleapis.com/falserverless/...",
      "content_type": "image/png"
    }
  ],
  "description": "..."
}
```

Worker success checks:
1. terminal status is `COMPLETED`
2. `images` is non-empty
3. `images[0].url` exists
4. downloaded file exists locally after worker fetch

## Critical rules
1. Use `prompt` for both t2i and i2i.
2. For i2i, required field is `image_urls` and it must be an array.
3. Never send local filesystem paths to fal.ai; use public URLs.
4. Persist compact refs into render manifests; do not persist raw provider payloads.

## Load next
- `providers/fal_nano_banana_2_t2i.md` — t2i request knobs, submit/poll/result examples
- `providers/fal_nano_banana_2_i2i.md` — i2i/edit request knobs and 422 pitfalls
- `bugs/fal-api-troubleshooting.md` — queue/public-URL/validation fixes
