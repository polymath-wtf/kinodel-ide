# Changing Kinodel Image Provider Defaults

Use this when the user asks to make a new image model the default for Kinodel renders while keeping the provider-neutral request contract intact.

## Scope

Changing image defaults is not just a worker-code edit. Update all places that guide producer/planner behavior:

1. `scripts/render_worker.py`
   - `provider_family_defaults(... kind == "t2i")` default provider.
   - `provider_family_defaults(... kind == "i2i")` default provider_edit.
   - `provider_family_defaults(... kind == "i2v")` default video provider.
   - Provider payload mapping lives in `scripts/providers/*.py` if the provider is new.

2. `render-kinodel/SKILL.md`
   - Default provider stack.
   - Troubleshooting/provider reference list.
   - Tags/version if the provider family is new.

3. `render-kinodel/references/request-contract.md`
   - Envelope `defaults.provider` and `defaults.provider_edit` examples.

4. `render-kinodel/references/provider-payload-cookbook.md`
   - Default t2i and i2i payload examples.
   - Explicitly document old providers as fallback/override when they remain supported.

5. Pipeline/producer/planner skills and contracts that hard-code defaults:
   - `pipeline-kinodel/SKILL.md`
   - `pipeline-kinodel/references/producer-playbook.md`
   - `pipeline-kinodel/contracts/capabilities.v1.json`
   - `pipeline-kinodel/pipelines/*.json`
   - `producer-kinodel/SKILL.md`
   - `wardrobe-kinodel/SKILL.md` or other planner skills emitting default envelopes.

## Provider-family defaults

Current Kinodel default is ComfyUI (`local-comfyui:img2img_klein` for images, `local-comfyui:img2vid_wan_lora` for i2v). If the user selects fal, use HiDream O1 on fal.ai:

- t2i provider: `fal:hidream_o1`
- t2i endpoint: `fal-ai/hidream-o1-image`
- i2i provider: `fal:hidream_o1_edit`
- i2i endpoint: `fal-ai/hidream-o1-image/edit`
- i2i input field in provider payload: `reference_image_urls`
- Keep Kinodel 9:16 default as explicit `image_size: {"width": 576, "height": 1024}` unless user asks otherwise.
- Nano Banana 2 can remain supported as explicit fallback/override: `fal:nano_banana_2`, `fal:nano_banana_2_edit`.

## Verification

After changing defaults:

```bash
python3 -m py_compile ~/.hermes/skills/kinodel/render-kinodel/scripts/render_worker.py ~/.hermes/skills/kinodel/render-kinodel/scripts/render.py ~/.hermes/skills/kinodel/render-kinodel/scripts/providers/*.py
python3 -m json.tool ~/.hermes/skills/kinodel/pipeline-kinodel/contracts/capabilities.v1.json >/dev/null
python3 -m json.tool ~/.hermes/skills/kinodel/pipeline-kinodel/pipelines/cinematic.v1.json >/dev/null
```

Also run a dry normalization check by importing `scripts/render_worker.py` and calling `normalize_job` for one `t2i` and one `i2i` job with 9:16 defaults. Expected with default ComfyUI provider choice:

```text
t2i -> local-comfyui:img2img_klein, image_size={"width":576,"height":1024}
i2i -> local-comfyui:img2img_klein, image_size={"width":576,"height":1024}
```

## Pitfalls

- Do not only edit `scripts/render_worker.py`; planner/producer docs and pipeline specs may keep steering future runs back to the old provider.
- Do not send local file paths to fal.ai i2i/i2v/flf2v providers. Use public URLs from previous result manifests.
- For HiDream edit, provider payload must use `reference_image_urls`; Nano Banana edit uses `image_urls`.
