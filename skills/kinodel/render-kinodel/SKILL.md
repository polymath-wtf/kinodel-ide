---
name: render-kinodel
description: Kinodel render worker. Executes explicit provider-neutral render request
  artifacts using packaged scripts, maps them to fal.ai/OpenRouter/ComfyUI payloads,
  downloads outputs, and writes compact result refs. Use for Kinodel main_frame/story_frames/video
  rendering, render audits, provider payload debugging, and request/result schema
  validation.
license: MIT
metadata:
  hermes:
    tags:
    - async
    - batch
    - comfyui
    - fal.ai
    - kinodel
    - hidream
    - nano-banana
    - render
    - veo
    related_skills:
    - pipeline-kinodel
    version: 1.2.1
    author: Hermes Agent + User
    comfyui_boundary: Do not load comfyui unless request provider is local-comfyui/comfyui
      or user explicitly asks for ComfyUI.
---

# Render-Kinodel

`render-kinodel` is a packaged worker, not a creative agent. It executes explicit render request artifacts and returns compact refs. It does not invent prompts, decide stages, or own project state.

## Hot path

```text
request artifact
→ normalize provider-neutral jobs with brief/defaults
→ dispatch provider queue
→ poll economically
→ download outputs
→ write temporary result JSON/events
→ render_wakeup.py promotes compact refs into v1/render_results/*.json
→ render_wakeup.py validates the durable manifest and emits the producer wake-up handoff/notification
```

## Run command

Producer launches the worker in a background terminal with `notify_on_complete=true`; the render command should be chained to the universal wake-up bridge:

```bash
python3 ~/.hermes/skills/kinodel/render-kinodel/scripts/render.py \
  --request-file /tmp/kinodel/<project_id>/<run_id>/requests.json \
  --result-file /tmp/kinodel/<project_id>/<run_id>/results.json \
  --events-file /tmp/kinodel/<project_id>/<run_id>/render_events.jsonl \
  --stage images \
  --output-dir ~/projects/<project_id>/v1/outputs && \
python3 ~/.hermes/skills/kinodel/render-kinodel/scripts/render_wakeup.py \
  --project-dir ~/projects/<project_id>/v1 \
  --worker-result /tmp/kinodel/<project_id>/<run_id>/results.json \
  --events-file /tmp/kinodel/<project_id>/<run_id>/render_events.jsonl \
  --stage main_frame
```

Use `--stage images` for `main_frame` and `story_frames`; use `--stage videos` for `shot_videos`. The worker has bounded parallelism: image concurrency defaults to 6, video/flf2v concurrency defaults to 4, so typical 3-shot flf2v batches submit together instead of serially.

Resume/retry behavior: `render.py` defaults to `--max-attempts 2` for retryable partial runtime failures. It reruns the worker with the same `--request-file` and `--result-file`; `render_worker.py` reads existing completed jobs from the result file, carries their `output_path`/`output_url` forward, and only submits missing or failed jobs. Manual reruns with the same result file also resume this way. Do not regenerate or rerun the whole request artifact just because one image/video failed. Preflight failures are not retried.

Do not run long provider polling inside `delegate_task` or a foreground terminal.

## Request contract

Planner artifacts are provider-neutral. Minimal job:

```json
{"stage":"story_frames","shot_id":"shot_01","kind":"i2i","render_prompt":"final prompt","input_media":["https://..."],"output_name":"shot_01.png"}
```

Before video render after any mid-pipeline flow/provider/duration change, Producer must validate `video_requests.json` with `producer-kinodel/scripts/state_guard.py validate --artifact video_requests.json`. Do not render stale `flf2v` requests after the brief has switched to `i2v` or ComfyUI; regenerate the request artifact first.

Rules:

- `kind`: `t2i`, `i2i`, `i2v`, or `flf2v`. `t2v` is a BriefGate workflow option only when a registered render provider/workflow supports it; otherwise fail closed rather than inventing a provider.
- `render_prompt`: required.
- `input_media`: array; required for `i2i`, `i2v`, `flf2v`.
- External providers require public `https://` URLs, never local file paths.
- Provider payload fields, queue IDs, status URLs, retry state, logs, and cost are forbidden in planner artifacts.

Full shape: `references/request-contract.md`.

## Default provider stack

- Brief/default provider choice is `comfyui` and default video workflow is `i2v` unless the user selects another provider/workflow.
- `t2i` default: `local-comfyui:img2img_klein`.
- `i2i` default: `local-comfyui:img2img_klein`.
- `i2v` default: `local-comfyui:img2vid_wan_lora`, 4s-equivalent local workflow where supported.
- `flf2v`: `fal:veo31_lite_flf2v` until a production ComfyUI first-last-frame workflow is registered.
- Bare `fal` expands to `fal:hidream_o1` / `fal:hidream_o1_edit` for images and `fal:veo31_lite_i2v` for videos.
- Nano Banana 2 remains supported as an explicit fallback/override (`fal:nano_banana_2`, `fal:nano_banana_2_edit`).
- `local-comfyui:img2img_klein` uses `workflows/img2img_klein.json`; no `input_media` means txt2img, 1-4 public image URLs become `img_url_1..4` for multi-reference img2img, and optional LoRA slots 1-5 are accepted via `payload.params.loras` or `lora_N_*` fields.

For ComfyUI generation, worker should send explicit pixel dimensions (`width`/`height` for images, `video_width`/`video_height` for Wan video). Project-local request files are merged with sibling `brief.json` defaults, so `brief.image.width/height` and `brief.video.width/height` are the durable source. If dimensions are missing, derive them from `aspect_ratio` plus image quality (`1K`/`1.5K`/`2K`) or video quality (`480p`/`720p`/`1080p`) using `references/resolution-guide.md`; do not invent per-agent calculations.

Dimension pitfall: never copy image dimensions into video dimensions. Default `1:1 image 1K` is `1024x1024`, while default `1:1 video 480p` is `480x480`. In runtime code, `image_size` must not fall back into `video_size`; video dimensions derive from `brief.video.width/height`, `video_size`, or `brief.video.resolution` only.

Provider payload details live in `references/provider-payload-cookbook.md` and provider-specific refs.

## ComfyUI image provider: img2img_klein

When a request job/provider selects `local-comfyui`, `comfyui`, `local-comfyui:img2img_klein`, or `comfyui:img2img_klein`, `scripts/render_worker.py` dispatches image jobs through `scripts/providers/comfyui_provider.py`. The old `scripts/fal.py` wrapper has been removed; use `scripts/render.py` as the stable entrypoint or `scripts/render_worker.py` for direct worker tests.

Request example:

```json
{
  "kind": "i2i",
  "provider": "local-comfyui:img2img_klein",
  "render_prompt": "...",
  "input_media": ["https://...optional-ref-1.png"],
  "payload": {
    "params": {
      "width": 576,
      "height": 1024,
      "seed": -1,
      "loras": [{"path": "wan/my_style.safetensors", "strength": 0.8}]
    }
  }
}
```

Mapping:
- `render_prompt` → `prompt`.
- `input_media` / `references` / `image_urls` first four public URLs → `img_url_1..4`.
- No input URLs is valid and runs as txt2img.
- `payload.params.loras` (list of strings or objects) maps to LoRA slots 1-5; empty/missing slots are forced off to avoid blank-path validation issues.
- Direct `lora_1_path`, `lora_1_strength`, `lora_1_on` ... `lora_5_*` fields are also supported.
- Output URL is synthesized from the ComfyUI/ngrok `/view` endpoint so downstream Kinodel stages can reuse it like fal.media URLs.

## Worker/provider module layout

- `scripts/render.py`: stable Producer entrypoint; launches `render_worker.py`.
- `scripts/render_worker.py`: generic scheduler/result/event worker; owns request normalization, preflight, concurrency, and job event summaries.
- `scripts/providers/registry.py`: provider/workflow alias resolution and local ComfyUI concurrency clamp.
- `scripts/providers/fal_provider.py`: fal.ai payloads, queue polling, downloads.
- `scripts/providers/comfyui_provider.py`: generic ComfyUI workflow adapter; imports the `comfyui` runner module directly instead of shelling out.
- `workflows/comfyui_registry.json`: human-readable ComfyUI workflow registry mirror for docs/profile generation.

## ComfyUI workflow architecture

ComfyUI remains a low-level provider toolkit, not a production subagent. Normal render loops should be executed by `render-kinodel` as background worker jobs with file-backed request/result/events. Use the `comfyui` skill/subagent only for setup, workflow debugging, dependency repair, or refactoring.

For future patches, prefer a registry-backed `ComfyWorkflowAdapter` over hardcoded per-workflow branches. Current explicit local flows are:

- `local-comfyui:img2img_klein`: image workflow accepting `t2i` with no refs and `i2i` with 1-4 refs; map refs to `img_url_1..4`; empty LoRA slots must be forced off.
- `local-comfyui:img2vid_wan_lora`: video workflow accepting `i2v`; map one input image to `image_url`; high/low LoRA banks may be separate or mirrored from generic `loras`.

Clamp local ComfyUI image/video concurrency to 1 unless a specific tested profile says otherwise. See `references/comfyui-provider-architecture.md` for the full boundary, registry shape, and mappings.

## Result contract

The worker writes temporary result files. `render_wakeup.py` is the normal render-boundary handoff back to Producer. It calls `copy_worker_result.py` to promote only compact selected refs into durable manifests, validates through `producer-kinodel/scripts/state_guard.py`, asks Producer for the next action, formats the wake-up message, and emits a `producer_agent_prompt` for a future Hermes wake consumer. It does not execute the Producer action loop itself; autonomous continuation beyond notification requires that wake consumer to enqueue the prompt as a new Producer agent turn in the target session/runtime. The detailed ownership boundary is documented in `producer-kinodel/references/render-wakeup-boundary.md`.

Manual promotion remains available for diagnostics/recovery:

```bash
python3 ~/.hermes/skills/kinodel/render-kinodel/scripts/copy_worker_result.py \
  --project-dir ~/projects/<project_id>/v1 \
  --worker-result /tmp/kinodel/<project_id>/<run_id>/results.json \
  --stage story_frames
```

Producer updates durable manifests and synchronizes canonical project-local media paths:

```json
{"schema":"kinodel.render_result.v1","project_id":"id","status":"complete","stage":"story_frames","selected_outputs":[{"shot_id":"shot_01","kind":"image","path":"outputs/shot_01.png","source_path":"outputs/api_00039_.png","url":"https://...","sha256":"..."}],"attempts":[],"selection_policy":"selected_outputs are current truth"}
```

`copy_worker_result.py` must copy the selected worker/raw output into stable canonical filenames (`outputs/main_frame.*`, `outputs/shot_XX.png`, `outputs/shot_XX.mp4`) and verify hash equality. This prevents a promoted older attempt from leaving `render_results/*.json.selected_outputs` and physical `outputs/shot_XX.*` out of sync.

Downstream agents consume `selected_outputs`; they must not scan `outputs/`.

Full shape: `references/result-manifest.md`.

Still-relevant failure signatures are mapped in `references/bugs-mapping.md`; load individual `bug/*.md` files only when a trigger matches.

See `references/upstream-edit-fix-invalidation.md` for the safe recovery pattern when a p4/p7 edit-fix changes the request but the old durable result still exists.

## Public URL rule

For fal.ai/OpenRouter media inputs, local paths are invalid. If a job references a local path, resolve it to a previous `url` from result manifests or fail before submit. Do not send local filesystem paths to external APIs.

## Polling and persistence

- HTTP 202 during fal.ai queue polling means in progress, not failure.
- Local ComfyUI is a single external FIFO resource. Queue wait (`/queue.queue_pending`) must not burn execution timeout; timeout applies after the prompt enters `queue_running` or when the prompt disappears without history.
- Do not auto-retry ComfyUI timeout failures: the prompt may still exist in the external queue. Preserve `request_id`/`prompt_id` in scratch result jobs and inspect `/queue` + `/history/<prompt_id>` before any manual rerun.
- Use adaptive backoff: ~5s start, up to ~30s.
- Terminal states: `COMPLETED`, `FAILED`, `CANCELLED`.
- Raw provider responses and debug payloads stay in `/tmp/kinodel/<project_id>/<run_id>/` or `<output_dir>/.render_debugs/`.
- Every submitted provider payload/workflow is also saved under the project-local `workflow/` directory (`v1/workflow/*.json`) for audit/debugging. For ComfyUI this is the injected workflow sent to the server; for fal.ai this is the exact queue payload. Do not use these files as pipeline state.
- Persist only compact output refs into project manifests.

## Troubleshooting references

Load only when needed:

- `references/resolution-guide.md` — canonical aspect-ratio/quality-to-pixel tables. Images use `1K`/`1.5K`/`2K`; videos use `480p`/`720p`/`1080p`.
- `references/provider-payload-cookbook.md` — compact HTTP body cookbook; canonical provider details live in `providers/`.
- `references/comfyui-provider-architecture.md` — ComfyUI boundary/registry/profile plan: ComfyUI is a provider toolkit under Render, not a production subagent; includes `img2img_klein` and `img2vid_wan_lora` mappings.
- `references/provider-adapter-architecture.md` — current provider adapter module split and checklist for adding new fal.ai/ComfyUI/local providers without bloating `render_worker.py`.
- `references/changing-image-provider-defaults.md` — checklist for switching Kinodel image defaults across worker, contracts, pipeline specs, and planner/producer skills.
- `providers/fal_hidream_o1_t2i.md` — default HiDream O1 text-to-image contract.
- `providers/fal_hidream_o1_edit.md` — default HiDream O1 edit/i2i contract.
- `providers/fal_nano_banana_2.md` — compact Nano Banana fallback overview.
- `providers/fal_nano_banana_2_t2i.md` — detailed Nano Banana fallback text-to-image contract.
- `providers/fal_nano_banana_2_i2i.md` — detailed Nano Banana fallback edit contract.
- `providers/fal_veo31_lite.md` — compact Veo overview.
- `providers/fal_veo31_lite_i2v.md` — detailed Veo image-to-video contract.
- `providers/fal_veo31_lite_flf2v.md` — detailed Veo first-last-frame contract.
- `references/fal-api-troubleshooting.md` — canonical fal queue/debug/public-URL notes.
- `comfyui` skill — local backup/provider debugging.
- historical incident notes only when a current failure signature matches.

## Hard no

- **Absolute Path Rule for Local Inputs**: External providers (fal.ai, etc.) cannot access the local filesystem. While some worker scripts attempt local-to-cloud resolution, the safest pattern for `input_media` is to use the `url` from previous result manifests. Do not use local paths for fal.ai inputs; always prefer `https://` URLs from parent manifests to avoid preflight failures.
- **Request Schema Rigidity**: Planners (wardrobe, storyboard, filmmaker) MUST write to the `jobs` array using the `kinodel.render_requests.v1` schema. Avoid custom top-level keys like `anchors` which cause the `render_worker.py` dispatcher to fail validation.
- **No stale compatibility wrappers**: When the architecture has moved to `render.py` + `render_worker.py` + provider modules, do not preserve old wrapper entrypoints only for historical projects unless the user explicitly asks for migration compatibility. Stale wrappers such as the removed `scripts/fal.py` create false ownership signals and should be deleted with docs/references updated to the canonical entrypoint.
- **Provider-Specific Payload Troubleshooting**:
    - `ValueError: request file must be a job list or an object with jobs[]`: The JSON structure is missing the `jobs` key or is not a raw list of jobs.
    - `failed preflight`: Usually indicates a local file path was passed to an external API that requires a public URL, or the path was relative and could not be resolved. Use `url` from the previous stage's result manifest.