# ComfyUI provider architecture for Kinodel Render

Use this reference when patching or auditing `render-kinodel` support for local ComfyUI workflows.

## Boundary decision

ComfyUI should not be a production `delegate_task` subagent. In normal Kinodel render loops it is a low-level provider toolkit/workflow runtime used by `render-kinodel`.

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

Reasoning:

- Long render jobs should not depend on child-agent dialogue context.
- Render state belongs in request/result/events artifacts, not chat.
- ComfyUI execution is deterministic: API workflow JSON + schema params + output selection.
- Local GPU concurrency is a resource policy owned by the render worker.
- Provider payloads and workflow quirks must stay out of planner artifacts.

Use a `comfyui` subagent only for setup/debug/dependency repair/workflow migration, not the hot render path.

## Target registry pattern

Prefer one generic `ComfyWorkflowAdapter` backed by a registry entry over hardcoded per-workflow branches.

Minimal registry shape:

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

New ComfyUI workflows should require `workflow.json + schema.json + registry entry`, not dispatcher code rewrites.

## Adapter interface

Target class shape:

```python
class ProviderAdapter:
    def supports(self, job): ...
    def preflight(self, job) -> list[str]: ...
    def run(self, job, output_dir) -> RenderOutput: ...
```

Useful split:

- `FalImageAdapter`
- `FalVideoAdapter`
- `ComfyWorkflowAdapter`
- future `AudioAdapter` / `LocalToolAdapter`

Keep workflow-specific differences in schema/registry/mapping helpers unless a workflow truly needs custom code.

## `img2img_klein` ergonomic mapping

Provider IDs:

- Preferred: `local-comfyui:img2img_klein`.
- Compatibility aliases for image jobs: `local-comfyui`, `comfyui`.

Accepted job kinds:

- `t2i`: no `input_media`, prompt-only image generation.
- `i2i`: 1–4 public input URLs.

Mapping:

```text
render_prompt                    → prompt
image_size.width/height          → width/height, default 1024x1024
seed                             → seed (-1 random)
input_media[0..3]                → img_url_1..4
crop_resize                      → crop_resize, default stretch
crop_resize_side                 → crop_resize_side, default center
unet_path / sage_attn            → matching schema params
turbo / turbo_lora_*             → turbo params
loras[0..4]                      → lora_1..5_{on,path,strength}
```

Pitfall: missing LoRA paths must force `lora_N_on=false` to avoid blank-path PowerLoraLoader failures.

## `img2vid_wan_lora` ergonomic mapping

Provider ID: `local-comfyui:img2vid_wan_lora`.

Accepted job kind: `i2v` only.

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

Pitfall: current schema defaults are landscape `832x480`; do not silently force fal.ai-style 9:16 into Wan. Make vertical Wan a tested provider-profile override.

## Provider profile binding

Pipeline/runtime profiles should bind capabilities to provider IDs; stage planners should remain provider-neutral:

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

## Patch order

1. Add registry/profile docs only; no behavior change.
2. Preserve the stable `render.py` CLI, with generic worker logic in `render_worker.py` and provider modules under `scripts/providers/`.
3. Add `providers/registry.py`, `providers/fal_provider.py`, `providers/comfyui_provider.py`.
4. Replace subprocess `run_workflow.py` calls with importing the ComfyUI runner module.
5. Add registry entries for `img2img_klein` and `img2vid_wan_lora`.
6. Auto-clamp local ComfyUI concurrency to 1.
7. Tests: alias resolution, t2i/no-ref image flow, i2v public URL preflight, empty LoRA slots off, output media selection.
8. Later: stable public URL/object-store layer; ComfyUI `/view` remains debug/temporary.
