# fal.ai Nano Banana 2 — Image to Image / Edit

## Endpoint
- `POST https://queue.fal.run/fal-ai/nano-banana-2/edit`

## Required fields
- `prompt: string`
- `image_urls: string[]`

## Common optional fields Kinodel cares about
- `aspect_ratio`: usually `"9:16"`
- `resolution`: usually `"1K"`
- `output_format`: usually `"png"`
- `safety_tolerance`: usually `"4"`
- `num_images`: always `1`
- `seed`: optional deterministic reuse
- `limit_generations`: usually `true`

## Common Kinodel body
```json
{
  "prompt": "Transform into a cinematic establishing shot while preserving character identity.",
  "image_urls": ["https://storage.googleapis.com/falserverless/..."],
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

## Validation-critical rule
- `image_urls` is REQUIRED and must be an array.
- `image_url` singular causes 422 validation failure.
- Local paths are invalid for fal.ai; use public URLs from prior result manifests.

## Queue/result shape
Submit/poll/final response lifecycle matches t2i.
Successful final payload again contains `images[0].url`.

## What the worker should verify
- source ref was public URL, not local path
- final status = `COMPLETED`
- `images` non-empty
- first image URL downloadable

## Common mistakes
- passing `image_url` instead of `image_urls`
- passing `outputs/foo.png` or any local path
- planner leaking provider payload fields into `jobs[]`
