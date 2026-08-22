---
title: Kinodel Render Requests — RenderJob Provider Workflows
created: 2026-05-07
updated: 2026-05-23
type: concept
tags: [kinodel, render-queue, api, provider-adapter, fal, openrouter, comfyui, video-gen, image-gen]
sources:
  - wiki/entities/agent-render-kinodel.md
  - wiki/concepts/kinodel-context-layers.md
  - wiki/concepts/cinema-pipeline.md
  - ~/.hermes/skills/kinodel/render-kinodel/scripts/render.py
  - ~/.hermes/skills/kinodel/render-kinodel/scripts/fal.py
  - ~/.hermes/skills/kinodel/render-kinodel/workflows/fal_veo31_lite_flf2v.json
  - ~/.hermes/skills/kinodel/filmmaker-kinodel/SKILL.md
  - raw/prompt-engine/gemini-omni-prompt-guide.md
confidence: high
contested: false
contradictions: []
---

# Kinodel Render Requests

## Core idea

> Planning agents emit `render_prompt` and `input_media`; [[agent-render-kinodel]] owns provider payloads, endpoint URLs, status polling, retries, and result bookkeeping.

This keeps the hot path small:
- **Planner job contract:** `stage`, `kind`, `render_prompt`, optional `input_media`, `output_name`; `flf2v` uses exactly two public image URLs in `input_media`.
- **Artifact contract:** planners complete `wardrobe_request.json`, `storyboard_requests.json`, or `video_requests.json` envelopes with `project_id`, `status: "complete"`, and non-empty `jobs[]`, then return status only.
- **Producer responsibility:** add defaults from [[kinodel-brief]] and launch the worker with explicit `--stage images|videos`.
- **Worker contract:** normalize requests into provider payloads and write compact temporary result JSON; Producer copies generated refs into project-bound `render_results/*.json` selection manifests with `selected_outputs` (current approved refs), `attempts` (all iterations), and `selection_policy`.
- **Final memory:** selected media refs become `main_frame`, `story_images`, optional videos, and conclusion in [[kinodel-final-chunk]].

## Shared request bundle

```json
{
  "schema": "kinodel.render_requests.v1",
  "project_id": "project_id",
  "status": "complete",
  "stage": "main_frame | story_frames | shot_videos",
  "defaults": {
    "aspect_ratio": "9:16",
    "video_duration": "4s",
    "flf2v_duration": "8s",
    "enable_audio": false
  },
  "jobs": [
    {
      "stage": "main_frame | story_frames | shot_videos",
      "kind": "t2i | i2i | i2v | flf2v",
      "render_prompt": "final visual or motion prompt",
      "input_media": ["optional image refs"],
      "output_name": "shot_01.png"
    }
  ]
}
```

Planning agents write the job list into their owned request artifact and preserve top-level `project_id`. Producer may add `defaults` from [[kinodel-brief]]. Worker normalization may add `job_id`, `provider`, `workflow`, `payload`, `params`, `output_path`, and status fields internally. These fields are runtime scratch, not planner-facing contract.

Project identity is both artifact identity and run context: top-level `project_id` must match `brief.json`, while Producer launches `render-kinodel/scripts/render.py` with either a compatible stage artifact or a normalized `/tmp/kinodel/<project_id>/<run_id>/requests.json`, `/tmp/kinodel/<project_id>/<run_id>/results.json`, explicit `--stage`, and `~/projects/<project_id>/v1/outputs`.

Field meaning is intentionally small:

- `kind` chooses the render class: `t2i` means text-to-image, `i2i` means image edit, `i2v` means image-to-video from one start frame, and `flf2v` means first-last-frame transition video.
- `stage` names the production stage: `main_frame`, `story_frames`, or `shot_videos`.
- `render_prompt` is the final visual or motion instruction.
- `input_media` are input media paths/URLs: optional for `t2i`, required for `i2i` and `i2v`; for `flf2v` it must be `[first_frame_url, last_frame_url]` from approved `selected_outputs`, with default/minimum transition duration `8s`.
- `output_name` is the desired output filename.

## Provider workflow registry

`render-kinodel` owns provider-specific workflow templates. Planning agents only set stage-level request fields.

| Provider family | Template location | Responsibility |
|---|---|---|
| `fal:*` | `kinodel/render-kinodel/workflows/fal_*.json` | Map common `payload.prompt`, `payload.image_urls`, `payload.image_url`, `payload.first_frame_url`, `payload.last_frame_url`, and `payload.params` into fal queue body; default images use HiDream O1, default video transitions use Veo 3.1 Lite FLF2V, Nano Banana 2 remains fallback for images; keep `request_id/status_url/response_url` in runtime result state only. |
| `openrouter:*` | `kinodel/render-kinodel/workflows/openrouter_*.json` | Use an LLM/VLM model for text asset generation, prompt rewriting, QC descriptions, or provider-compatible JSON creation. OpenRouter does not replace render providers for image/video binary generation unless a chosen model explicitly supports it. |
| `local-comfyui` / `comfy:<workflow>` | `kinodel/render-kinodel/workflows/*.json` plus `kinodel/comfyui/workflows/*.json` | Load ComfyUI API-format graph, inject schema-mapped params, submit `{prompt, client_id}` to `/prompt`, poll `/history/{prompt_id}`, download via `/view`. |
| `google:gemini_omni_video` (draft) | future `render-kinodel` adapter | Candidate adapter for [[gemini-omni-video-model]]: multimodal video generation/editing from text + image/video/audio refs. Planner contract should remain `kind + render_prompt + input_media`; Gemini/Flow/API-specific payload shape stays worker-owned until a stable API exists. |

This is the simplification cascade: **every external generation call starts as `kind + render_prompt + input_media`, then `render-kinodel` transforms it through exactly one adapter**. No specialist agent contains endpoint-specific code.

## T2I: main frame

Produced by [[agent-wardrobe-kinodel]].
The example below is one job inside the top-level `jobs[]` envelope.

```json
{
  "stage": "main_frame",
  "kind": "t2i",
  "render_prompt": "cinematic vertical main frame, woman with silver bob haircut standing on flooded neon city street, neo-noir, film grain",
  "output_name": "main_frame.png"
}
```

For high-quality "Redo with Pro", Producer passes an explicit runtime override to the worker; planning agents still return only stage-level request fields.

Output lands in `outputs/`; Producer selects approved refs into `render_results/main_frame_result.json.selected_outputs`. Previous iterations remain in `outputs/` and may be tracked in `attempts`.

## I2I/Edit: storyboard shot image

Produced by [[agent-storyboard-kinodel]].
The example below is one job inside the top-level `jobs[]` envelope.

```json
{
  "stage": "story_frames",
  "shot_id": "shot_01",
  "kind": "i2i",
  "render_prompt": "Make an establishing shot. The subject from the input image stands centred, looking up at a glowing drone, neo-noir, film grain",
  "input_media": ["outputs/main_frame.png"],
  "output_name": "shot_01.png"
}
```

Output lands in `outputs/`; Producer selects approved refs into `render_results/story_frames_result.json.selected_outputs` after ReviewGate approve. Previous iterations remain in `outputs/` and may be tracked in `attempts`.

## I2V / FLF2V: shot video

Produced by [[agent-filmmaker-kinodel]]. Default Kinodel video jobs are `flf2v` transitions between adjacent approved story frames. `i2v` remains available only when Producer explicitly requests one video per still frame.

```json
{
  "stage": "shot_videos",
  "shot_id": "shot_01_to_shot_02",
  "kind": "flf2v",
  "render_prompt": "Transition from shot 01 to shot 02 over 8 seconds. Start exactly from the first frame, move the camera and subject naturally, preserve identity and lighting, and land in the exact final composition of shot 02. No hard cut.",
  "input_media": ["https://.../shot_01.png", "https://.../shot_02.png"],
  "output_name": "shot_01_to_shot_02.mp4"
}
```

Output lands in `outputs/`; Producer selects approved refs into `render_results/shot_videos_result.json.selected_outputs`. Previous iterations remain in `outputs/` and may be tracked in `attempts`.

## OpenRouter: LLM/VLM asset helper jobs

OpenRouter is a provider family for worker-internal text/JSON/analysis jobs, not the default binary image/video renderer and not a planner-facing specialist contract.

```json
{
  "kind": "llm_asset",
  "provider": "openrouter:json_asset",
  "workflow": "openrouter_json_asset",
  "payload": {
    "prompt": "Rewrite these 5 shot motion prompts into provider-safe concise English JSON.",
    "references": [
      "projects/<id>/v1/storyboard_requests.json"
    ],
    "params": {
      "model": "google/gemini-2.5-flash",
      "response_format": "json_object",
      "temperature": 0.2
    }
  },
  "output_path": "/tmp/kinodel/<project_id>/<run_id>/video_payloads.normalized.json"
}
```

OpenRouter output remains runtime scratch unless a named Kinodel skill explicitly owns it as a durable artifact. It is never a hidden prompt side-channel.

## Gemini Omni: draft multimodal video adapter

[[gemini-omni-video-model]] is a design candidate for a future Kinodel provider profile that can consume mixed media refs (`@image`, `@video`, `@audio`) and a structured CRAFT-style video prompt. Until a production API is chosen, treat this as wiki architecture only: do not change planner artifacts or live render workers just to match Google Flow UI semantics.

Potential planner-facing job shape stays compact:

```json
{
  "stage": "shot_videos",
  "kind": "omni_video",
  "render_prompt": "CRAFT-style context/reference/action/framing/timing prompt",
  "input_media": ["outputs/shot_01.png", "refs/motion.mp4", "refs/music.mp3"],
  "output_name": "shot_01.mp4"
}
```

Provider-specific mapping — uploaded media handles, Google account/session details, Flow/GenAI request body, editing state, and audio/text-rendering parameters — belongs inside [[agent-render-kinodel]], not inside [[agent-filmmaker-kinodel]] or storyboard/wardrobe planners.

## Local ComfyUI: workflow-backed i2i / i2v

Runtime override used by [[agent-render-kinodel]] when a shot should render on local ComfyUI rather than hosted fal. Planning agents still return only the compact render request contract.

```json
{
  "kind": "i2i",
  "provider": "local-comfyui",
  "payload": {
    "prompt": "cinematic vertical shot, consistent heroine, neon rain...",
    "references": [
      "https://example.com/ref_1.png",
      "https://example.com/ref_2.png"
    ],
    "params": {
      "workflow": "img2img_klein",
      "seed": -1,
      "width": 576,
      "height": 1024,
      "turbo": false
    },
    "loras": [
      {"enabled": true, "path": "character_lora.safetensors", "weight": 0.75}
    ]
  },
  "output_path": "projects/<id>/v1/outputs/shot_01.png"
}
```

For video runtime overrides, use `kind: "i2v"`, `params.workflow: "img2vid_wan_lora"`, `params.video_width`, `params.video_height`, `params.duration`, and a single start image reference. [[agent-render-kinodel]] injects this runtime payload into the schema-mapped ComfyUI API workflow and submits:

```json
{
  "prompt": "<workflow API JSON>",
  "client_id": "<uuid>"
}
```

The local API base is `COMFYUI_LOCAL_NGROK_URL`; paths stay local ComfyUI style: `/prompt`, `/history/{prompt_id}`, `/view`.

## Adapter mapping

`agent-render-kinodel` / target skill `render-kinodel` performs provider-specific mapping:

| Provider | Kind | Adapter responsibility |
|----------|------|------------------------|
| `fal:hidream_o1` | `t2i` | Default image provider. Load `fal_hidream_o1_t2i` template, POST `https://queue.fal.run/fal-ai/hidream-o1-image`. Body keys: `prompt`, derived or explicit `image_size`, `num_inference_steps`, `guidance_scale`, `num_images`, `output_format`, `enable_safety_checker`, optional `seed`. |
| `fal:hidream_o1_edit` | `i2i` | Default image edit/story-frame provider. Load `fal_hidream_o1_edit_i2i` template, POST `https://queue.fal.run/fal-ai/hidream-o1-image/edit`. Body keys include REQUIRED `reference_image_urls` array derived from planner `input_media`. |
| `fal:nano_banana_2` | `t2i` | Fallback image provider. Load `fal_nano_banana_2_t2i` template, POST `https://queue.fal.run/fal-ai/nano-banana-2`. Body keys: `prompt`, `aspect_ratio`, `resolution`, `output_format`, `safety_tolerance`, `num_images`, `seed`, `limit_generations`, `enable_web_search`, `thinking_level`. |
| `fal:nano_banana_2_edit` | `i2i` | Fallback image edit provider. Load `fal_nano_banana_2_edit_i2i` template, POST `https://queue.fal.run/fal-ai/nano-banana-2/edit`. Body keys include REQUIRED `image_urls` array. |
| `fal:veo31_lite_i2v` / legacy `fal:veo` | `i2v` | Load `fal_veo31_lite_i2v` template, POST `https://queue.fal.run/fal-ai/veo3.1/lite/image-to-video`. Body keys: `image_url`, `prompt`, `aspect_ratio: "auto"`, `duration` string (`"4s"` default), `resolution: "720p"`, `generate_audio`, `safety_tolerance: "4"`. |
| `fal:veo31_lite_flf2v` | `flf2v` | Load `fal_veo31_lite_flf2v` template, POST `https://queue.fal.run/fal-ai/veo3.1/lite/first-last-frame-to-video`. Body keys: `prompt`, `aspect_ratio: "auto"`, `duration` string (`"8s"` default/minimum), `resolution: "720p"`, `generate_audio`, `safety_tolerance: "4"`, required `first_frame_url` and `last_frame_url` derived from `input_media[0]` and `input_media[1]`. |
| `openrouter:*` | `llm_asset`, `qc`, future | Load `openrouter_*.json`, POST OpenRouter chat/completions-compatible body, save JSON/text artifact to `output_path`, track cost and errors like any other job. |
| `local-comfyui` | `i2i`, `i2v` | Load `payload.params.workflow` from `agent-render-kinodel/workflows/*.json`, inject schema parameters, POST `$COMFYUI_LOCAL_NGROK_URL/prompt` with `{prompt, client_id}`, poll `/history/{prompt_id}`, download first media from `/view`. |
| `comfy:<workflow>` | `i2i`, `i2v`, future | Same as `local-comfyui`, but workflow name comes from provider suffix when `payload.params.workflow` is omitted. |

No planner depends on provider-specific SDK shape. If provider changes, only [[agent-render-kinodel]] and this page change.

## Autonomous worker rules

- `requested_at` stays outside cacheable `ContextLayer` prompt prefixes.
- After submit, `request_id`, `status_url`, and `response_url` are runtime result fields only.
- Repeat runner invocations resume from persisted URLs / prompt IDs; they must not re-submit a job that already has `status_url`.
- HTTP 202 / `IN_QUEUE` / `IN_PROGRESS` are non-terminal. Terminal statuses are `COMPLETED`, `FAILED`, `CANCELLED`, or local `done` / `failed`.
- Worker status polling is economical: start at 5 seconds and adaptively back off up to 30 seconds between provider HTTP status checks.
- When a batch is terminal, worker writes a compact temporary result file/summary. Producer copies generated refs into project-bound `render_results/*.json` manifests: appending to `attempts`, updating `selected_outputs` for approved refs only. Raw provider payloads, status URLs, retries, and debug responses remain runtime scratch.
- Veo 3.1 Lite uses `duration` and `generate_audio`; `flf2v` uses `first_frame_url` and `last_frame_url`; never emit `duration_seconds` or `audio_url` in provider HTTP body.
- Local ComfyUI requests write debug JSON under `<output_dir>/.render_debug/` so the exact submitted workflow and ComfyUI responses are auditable.

## См. также

- [[agent-render-kinodel]] — executor and retry/cost guardrails
- [[kinodel-context-layers]] — how render outputs become context layers
- [[cinema-pipeline]] — where render requests are produced
- [[agent-wardrobe-kinodel]] · [[agent-storyboard-kinodel]] · [[agent-filmmaker-kinodel]]
- [[gemini-omni-video-model]] — draft multimodal video model/provider candidate
