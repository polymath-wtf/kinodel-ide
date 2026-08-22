# fal.ai Veo 3.1 Lite — First/Last Frame to Video

## Endpoint
- `POST https://queue.fal.run/fal-ai/veo3.1/lite/first-last-frame-to-video`

## Required fields
- `prompt: string`
- `first_frame_url: string`
- `last_frame_url: string`

## Common optional fields Kinodel cares about
- `aspect_ratio`: usually `"auto"`
- `duration`: usually `"8s"`
- `resolution`: usually `"480p"`
- `generate_audio`: usually `false`
- `safety_tolerance`: usually `"4"`

## Common Kinodel body
```json
{
  "first_frame_url": "https://public.example.com/shot_01.png",
  "last_frame_url": "https://public.example.com/shot_02.png",
  "prompt": "Smooth cinematic transition from shot 01 to shot 02, preserving identity and landing exactly on the final composition.",
  "aspect_ratio": "auto",
  "duration": "8s",
  "resolution": "480p",
  "generate_audio": false,
  "safety_tolerance": "4"
}
```

## Kinodel usage note
- flf2v is the transition default when neighboring approved story frames exist.
- source refs should come from `render_results/story_frames_result.json.selected_outputs[].url`.

## Submit / status / final result
- submit returns `request_id`, `status_url`, `response_url`
- poll `status_url` until terminal completion
- final response should contain `video.url`

## What the worker should verify
- both frame refs are public URLs
- final status = `COMPLETED`
- `video.url` exists and downloads successfully
- output file matches planned transition clip slot
