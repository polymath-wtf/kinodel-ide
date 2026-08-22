# fal.ai Veo 3.1 Lite — Image to Video

## Endpoint
- `POST https://queue.fal.run/fal-ai/veo3.1/lite/image-to-video`

## Required fields
- `prompt: string`
- `image_url: string`

## Common optional fields Kinodel cares about
- `aspect_ratio`: usually `"auto"`
- `duration`: usually `"4s"`
- `resolution`: usually `"480p"`
- `generate_audio`: usually `false`
- `safety_tolerance`: usually `"4"`
- `seed`: optional

## Common Kinodel body
```json
{
  "image_url": "https://public.example.com/image.png",
  "prompt": "The subject turns toward camera as the frame slowly pushes in.",
  "aspect_ratio": "auto",
  "duration": "4s",
  "resolution": "480p",
  "generate_audio": false,
  "safety_tolerance": "4"
}
```

## Important field notes
- `duration_seconds` is not the canonical Veo field.
- `audio_url` is not the canonical Veo audio field.
- Always use the public URL from prior manifests, never a local path.

## Submit / status / final result
- submit returns `request_id`, `status_url`, `response_url`
- poll `status_url` until `COMPLETED`
- final response should contain `video.url`

## What the worker should verify
- input ref is public URL
- final status = `COMPLETED`
- `video.url` exists and is downloadable
