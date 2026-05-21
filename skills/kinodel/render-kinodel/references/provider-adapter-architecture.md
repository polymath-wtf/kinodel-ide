# Render provider adapter architecture

Use this reference when extending `render-kinodel` beyond a single provider or adding new ComfyUI workflows.

## Core boundary

`render-kinodel` owns production execution:

- request normalization;
- preflight;
- scheduling/concurrency;
- event/result JSON shape;
- provider payload normalization;
- polling/download;
- compact output refs.

Provider/toolkit skills such as `comfyui` own setup, health checks, dependency debugging, workflow-format docs, and reusable runner utilities. They should not become production LLM subagents for normal render loops.

## Current module split

- `scripts/render.py` — stable Producer entrypoint.
- `scripts/render_worker.py` — generic worker/scheduler/result writer.
- `scripts/providers/registry.py` — provider/workflow alias resolution and local concurrency policy.
- `scripts/providers/fal_provider.py` — fal.ai payload mapping, queue polling, downloads.
- `scripts/providers/comfyui_provider.py` — generic ComfyUI workflow adapter that imports the ComfyUI runner module directly.
- `workflows/comfyui_registry.json` — human-readable ComfyUI workflow registry mirror.

## Simplification cascade

Treat every provider as:

```text
RenderJob -> ProviderAdapter -> ProviderResult -> OutputRef
```

Do not add provider-specific branches to `render_worker.py` unless the worker contract itself changes. Put provider-specific mapping into provider modules and put workflow-specific knobs into workflow schemas/registry entries.

## Adding a ComfyUI workflow

1. Add API-format workflow JSON under `workflows/`.
2. Add schema JSON under `workflows/`.
3. Add/extend registry entry in `workflows/comfyui_registry.json` and `scripts/providers/registry.py`.
4. Add only the minimum argument mapper needed in `scripts/providers/comfyui_provider.py`.
5. Keep empty LoRA slots explicitly off (`on=false`, path empty) to avoid blank-path loader failures.
6. Clamp local ComfyUI concurrency to 1 unless the specific local profile has been tested.
7. Preserve the worker result/event contract so Producer/copy_worker_result stays unchanged.

## Existing ComfyUI mappings

### `local-comfyui:img2img_klein`

Accepted kinds: `t2i`, `i2i`.

- No refs is valid and runs prompt-only generation.
- 1-4 public refs map to `img_url_1..4`.
- `payload.params.loras` or direct `lora_N_*` fields map to LoRA slots 1-5.
- Empty/missing slots must be forced off.

### `local-comfyui:img2vid_wan_lora`

Accepted kind: `i2v`.

- One public input image maps to `image_url`.
- `duration` is normalized to integer seconds for the workflow schema.
- `loras_high` and `loras_low` map to separate banks.
- Generic `loras` / `wan_loras` can be mirrored into both banks for ergonomic requests.
- Direct schema-style fields such as `lora_1_high_path` and `lora_1_low_path` are supported.

## Verification checklist

Before finishing a provider patch, run/check equivalents of:

- Python compile for `render.py`, `render_worker.py`, `providers/*.py`, and relevant toolkit runner modules.
- JSON validation for `workflows/comfyui_registry.json`.
- Alias resolution for bare and explicit provider IDs.
- Preflight for no-ref `img2img_klein` image jobs.
- Preflight for `img2vid_wan_lora` requiring one public image URL.
- LoRA slot behavior: generic list, high/low banks, direct fields, empty slots off.
- Local ComfyUI concurrency clamp.
- No-pending worker path through both `render_worker.py` and stable `render.py` entrypoint.

Do not require a real GPU render for structural patches unless the user explicitly asks for integration testing against a live ComfyUI server.
