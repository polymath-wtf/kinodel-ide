---
title: Kinodel ComfyUI Provider Architecture
created: 2026-05-19
updated: 2026-05-19
type: concept
tags: [kinodel, video-pipeline, image-gen, video-gen, img2img, lora, workflow, production, agent-architecture]
sources:
  - user:cli:2026-05-19-kinodel-comfyui-render-question
  - ~/.hermes/skills/kinodel/render-kinodel/SKILL.md
  - ~/.hermes/skills/kinodel/render-kinodel/scripts/render.py
  - ~/.hermes/skills/kinodel/render-kinodel/scripts/fal.py
  - ~/.hermes/skills/kinodel/render-kinodel/workflows/img2img_klein.schema.json
  - ~/.hermes/skills/kinodel/render-kinodel/workflows/img2vid_wan_lora.schema.json
  - ~/.hermes/skills/kinodel/comfyui/SKILL.md
  - ~/.hermes/skills/kinodel/comfyui/scripts/run_workflow.py
confidence: high
contested: false
contradictions: []
---

# Kinodel ComfyUI Provider Architecture

`ComfyUI` в Kinodel должен быть не отдельным production subagent, а низкоуровневым provider toolkit + workflow registry под [[agent-render-kinodel]]. Render owns execution, scheduling, event stream, retries, result contract and manifest promotion; `comfyui` owns lifecycle/debug/workflow-format knowledge: server health, API-format JSON, dependency checks, schema extraction, REST/WS runner.

## Main decision

Production path:

```text
Producer / pipeline_spec
  → complete render request artifact
  → render-kinodel background worker
  → provider adapter registry
  → ComfyUIWorkflowAdapter(workflow_id)
  → comfyui runner module
  → ComfyUI /prompt + /history + /view
  → render_results/*.json compact refs
```

Do not launch a `comfyui` LLM subagent for normal render loops. Use subagents only for architecture/debug/migration/dependency repair. Render loops need deterministic API execution and file-backed state, not dialogue context.

Simplification cascade: every provider call is `RenderJob → Adapter → ProviderResult → OutputRef`. `fal.ai`, ComfyUI image, ComfyUI video, future audio/music providers and local tools should differ by adapter/profile, not by agent role.

## Responsibilities

### `render-kinodel`

- Accepts provider-neutral jobs: `kind`, `render_prompt`, `input_media`, `output_name`, optional `provider`, optional `payload.params`.
- Normalizes defaults from brief/profile.
- Chooses adapter/workflow via registry.
- Runs preflight before provider submission.
- Clamps local GPU concurrency.
- Downloads/copies output into `outputs/`.
- Writes temporary result JSON/events; Producer promotes compact refs with the normal copier.

### `comfyui` skill

- Installs/starts/checks ComfyUI and `comfy-cli`.
- Validates API-format workflows and rejects editor-format JSON.
- Checks missing nodes/models/custom nodes.
- Provides reusable `ComfyRunner` for `/prompt`, `/history`, `/view`, output download and WS debug.
- Should be loaded in LLM context only for setup/debug/refactor, not for every normal Kinodel render.

## Workflow registry target

Add a registry under `render-kinodel`, replacing hardcoded provider branches:

```json
{
  "schema": "kinodel.render_workflow_registry.v1",
  "workflows": {
    "img2img_klein": {
      "provider": "local-comfyui",
      "adapter": "comfyui_workflow",
      "kind": "image",
      "accepted_job_kinds": ["t2i", "i2i"],
      "workflow_path": "workflows/img2img_klein.json",
      "schema_path": "workflows/img2img_klein.schema.json",
      "default_timeout_s": 900,
      "concurrency_class": "local_comfyui_image",
      "max_concurrency": 1,
      "outputs": {"preferred_media_type": "image", "prefer_source_type": "output"}
    },
    "img2vid_wan_lora": {
      "provider": "local-comfyui",
      "adapter": "comfyui_workflow",
      "kind": "video",
      "accepted_job_kinds": ["i2v"],
      "workflow_path": "workflows/img2vid_wan_lora.json",
      "schema_path": "workflows/img2vid_wan_lora.schema.json",
      "default_timeout_s": 1800,
      "concurrency_class": "local_comfyui_video",
      "max_concurrency": 1,
      "outputs": {"preferred_media_type": "video", "extension": "mp4"}
    }
  },
  "aliases": {
    "local-comfyui": "img2img_klein",
    "comfyui": "img2img_klein",
    "local-comfyui:img2img_klein": "img2img_klein",
    "local-comfyui:img2vid_wan_lora": "img2vid_wan_lora"
  }
}
```

New workflows should require only `workflow.json + schema.json + registry entry`, not dispatcher rewrites.

## Adapter interface

Target shape:

```python
class ProviderAdapter:
    def supports(self, job): ...
    def preflight(self, job) -> list[str]: ...
    def run(self, job, output_dir) -> RenderOutput: ...
```

Adapters: `FalImageAdapter`, `FalVideoAdapter`, `ComfyWorkflowAdapter`, later `AudioAdapter`/`LocalToolAdapter`. Prefer one generic `ComfyWorkflowAdapter`; put workflow differences into schemas, registry defaults, and mapping helpers.

## Flow 1 — `img2img_klein`

Provider IDs:

- Preferred: `local-comfyui:img2img_klein`.
- Compatibility aliases for image jobs: `local-comfyui`, `comfyui`.

Accepted Kinodel job kinds:

- `t2i`: no `input_media`, prompt-only image generation.
- `i2i`: 1–4 public input URLs mapped to `img_url_1..4`.

Mapping:

```text
render_prompt                    → prompt
image_size.width/height          → width/height, default 576x1024
seed                             → seed (-1 random)
input_media[0..3]                → img_url_1..4
crop_resize                      → crop_resize, default stretch
crop_resize_side                 → crop_resize_side, default center
unet_path / sage_attn            → matching schema params
turbo / turbo_lora_*             → turbo params
loras[0..4]                      → lora_1..5_{on,path,strength}
```

Important ergonomic rule: missing LoRA paths force `lora_N_on=false`, preventing blank-path PowerLoraLoader failures.

## Flow 2 — `img2vid_wan_lora`

Provider ID: `local-comfyui:img2vid_wan_lora`.

Accepted Kinodel job kind: `i2v` only.

Mapping:

```text
render_prompt                    → prompt
input_media[0] / image_url       → image_url
video_width/video_height         → schema defaults unless profile overrides
duration                         → integer seconds
seed                             → seed
crop_resize / crop_resize_side   → matching schema params
unet_path_low/high               → low/high model loaders
sage_attn                        → both model loaders
loras_high[0..4]                 → lora_1..5_high_{on,path,strength}
loras_low[0..4]                  → lora_1..5_low_{on,path,strength}
loras / wan_loras                → optional mirrored high+low banks
```

Open question: current schema defaults are landscape `832x480`. Do not silently force fal.ai-style `9:16`; make vertical Wan a tested provider-profile override.

## Provider profile binding

Pipeline/spec layer should bind capabilities to profile; stage planners should not write provider payloads:

```json
{
  "render_profile_id": "local_comfy_klein_wan.v1",
  "capabilities": {
    "image.generate": {"provider": "local-comfyui:img2img_klein"},
    "image.edit": {"provider": "local-comfyui:img2img_klein"},
    "video.i2v": {"provider": "local-comfyui:img2vid_wan_lora"}
  },
  "runtime_policy": {
    "local_comfyui_image_concurrency": 1,
    "local_comfyui_video_concurrency": 1
  }
}
```

This fits [[kinodel-pipeline-runtime]]: Producer selects `fal-fast`, `fal-quality`, `local-comfy-klein-wan`, or `hybrid`; agents still emit provider-neutral [[kinodel-render-requests]].

## Implementation status — 2026-05-19

Applied to live `render-kinodel` skill:

- `scripts/render.py` now launches `scripts/render_worker.py`.
- `scripts/fal.py` remains a backward-compatible wrapper.
- Provider-specific logic moved under `scripts/providers/`:
  - `registry.py` — workflow alias resolution and local ComfyUI concurrency clamp;
  - `fal_provider.py` — fal.ai payloads, queue polling, downloads;
  - `comfyui_provider.py` — generic ComfyUI workflow adapter importing the `comfyui` runner module directly.
- `workflows/registry.json` documents `img2img_klein` and `img2vid_wan_lora` mappings.
- `local-comfyui` bare alias is now kind-aware: image jobs map to `img2img_klein`, `i2v` maps to `img2vid_wan_lora`.
- Local ComfyUI jobs clamp worker concurrency to 1.

Verification performed: Python compile for worker/provider modules; dry checks for alias resolution, t2i/i2i no-ref image flow, i2v public URL preflight, generic LoRA mirroring into high/low Wan banks, empty LoRA slots off, no-pending worker result JSON.

Remaining later work: stable public URL/object-store layer; ComfyUI `/view` remains debug/temporary.

## См. также

- [[agent-render-kinodel]] — worker boundary and result/event contract.
- [[kinodel-render-requests]] — provider-neutral request envelope.
- [[kinodel-pipeline-runtime]] — pipeline spec / render profile binding.
- [[pipeline-kinodel]] — hard Kinodel laws and ReviewGate stops.
