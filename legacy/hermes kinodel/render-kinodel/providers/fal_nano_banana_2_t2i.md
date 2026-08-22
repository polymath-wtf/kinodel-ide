# fal.ai Nano Banana 2 — Text to Image

## Endpoint
- `POST https://queue.fal.run/fal-ai/nano-banana-2`

## Required fields
- `prompt: string`

## Common optional fields Kinodel cares about
- `aspect_ratio`: usually `"9:16"`
- `resolution`: usually `"1K"`
- `output_format`: usually `"png"`
- `safety_tolerance`: usually `"4"`
- `num_images`: always `1`
- `seed`: optional deterministic reuse
- `limit_generations`: usually `true`
- `enable_web_search`: usually `false`
- `thinking_level`: omit unless intentionally needed

## Common Kinodel body
```json
{
  "prompt": "medium shot, cinematic neon noir, lone cyber-monk in rain...",
  "aspect_ratio": "1:1",
  "resolution": "1K",
  "output_format": "png",
  "safety_tolerance": "4",
  "num_images": 1,
  "seed": 42,
  "limit_generations": true,
  "enable_web_search": false
}
```

## Submit response shape
```json
{
  "request_id": "uuid",
  "status": "IN_QUEUE",
  "status_url": "https://queue.fal.run/fal-ai/nano-banana-2/requests/uuid/status",
  "response_url": "https://queue.fal.run/fal-ai/nano-banana-2/requests/uuid"
}
```

## Polling rules
1. Poll `status_url` every 3-5s initially.
2. HTTP 202 + `IN_PROGRESS` means keep waiting.
3. Stop only on terminal states: `COMPLETED`, `FAILED`, `CANCELLED`.
4. Fetch `response_url` only after completion.

## Final response shape
```json
{
  "images": [
    {
      "file_name": "nano-banana-2-t2i-output.png",
      "url": "https://storage.googleapis.com/falserverless/...",
      "content_type": "image/png"
    }
  ],
  "description": "..."
}
```

## What the worker should verify
- final status = `COMPLETED`
- `images[0].url` exists
- URL downloads successfully
- output filename matches planned output slot

## Common mistakes
- treating HTTP 202 as failure
- polling the final result endpoint too early
- stuffing provider payloads into planner artifacts instead of provider-neutral `jobs[]`
