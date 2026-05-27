# Provider Payload Cookbook

Load this only when debugging provider payloads or extending worker adapters. Planners must not emit these payloads directly.

## fal:hidream_o1 — text to image fal override

Endpoint: `POST https://queue.fal.run/fal-ai/hidream-o1-image`

```json
{
  "prompt": "<payload.prompt>",
  "image_size": {"width": 576, "height": 1024},
  "num_inference_steps": 50,
  "guidance_scale": 5,
  "num_images": 1,
  "output_format": "png",
  "enable_safety_checker": false,
  "seed": null,
  "sync_mode": null
}
```

For Kinodel 9:16 vertical anchors, prefer explicit `image_size` over aspect-ratio strings.

## fal:hidream_o1_edit — image edit / i2i fal override

Endpoint: `POST https://queue.fal.run/fal-ai/hidream-o1-image/edit`

```json
{
  "prompt": "<payload.prompt>",
  "reference_image_urls": ["https://..."],
  "image_size": {"width": 576, "height": 1024},
  "num_inference_steps": 50,
  "guidance_scale": 5,
  "num_images": 1,
  "output_format": "png",
  "enable_safety_checker": false,
  "seed": null,
  "sync_mode": null,
  "keep_original_aspect": false
}
```

`reference_image_urls` must be an array of public URLs. Local paths cause preflight failure or provider 422. Nano Banana edit remains available as explicit `fal:nano_banana_2_edit` fallback and uses `image_urls`.

## fal:veo31_lite_i2v — video

Endpoint: `POST https://queue.fal.run/fal-ai/veo3.1/lite/image-to-video`

```json
{
  "image_url": "https://.../shot_01.png",
  "prompt": "<motion prompt>",
  "aspect_ratio": "auto",
  "duration": "4s",
  "resolution": "480p",
  "generate_audio": false,
  "safety_tolerance": "4"
}
```

## fal:veo31_lite_flf2v — transition

Endpoint: `POST https://queue.fal.run/fal-ai/veo3.1/lite/first-last-frame-to-video`

```json
{
  "prompt": "<transition prompt>",
  "aspect_ratio": "auto",
  "duration": "8s",
  "resolution": "480p",
  "generate_audio": false,
  "safety_tolerance": "4",
  "first_frame_url": "https://.../shot_01.png",
  "last_frame_url": "https://.../shot_02.png"
}
```

Use only when the brief asks for interpolated transitions. Default Kinodel is one 4s i2v clip per approved story frame.

## Queue polling

- POST returns queue metadata and may return HTTP 202 while in progress.
- Worker uses bounded parallelism: image batches default to 6 concurrent jobs; video/flf2v batches default to 4 concurrent jobs.
- For normal 3-shot `flf2v` productions, all transition requests should enter the fal.ai queue together, then poll concurrently.
- Poll `status_url` with adaptive backoff: start ~5s, back off to ~30s.
- Terminal states: `COMPLETED`, `FAILED`, `CANCELLED`.
- On complete, fetch `response_url`, download media, and write compact result refs.

## Supported alternatives

- `fal:nano_banana_2`: text-to-image fallback/override.
- `fal:nano_banana_2_edit`: image-edit fallback/override.
- `local-comfyui`: current default provider family; use `local-comfyui:img2img_klein` for t2i/i2i and `local-comfyui:img2vid_wan_lora` for i2v.
