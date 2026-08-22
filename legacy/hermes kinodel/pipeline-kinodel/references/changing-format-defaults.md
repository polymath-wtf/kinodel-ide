# Changing Kinodel Format Defaults

Use this checklist when the user changes canonical production defaults such as `aspect_ratio`, image quality, video quality, platform, or default pixel dimensions.

## Source of truth

- Resolution math lives in `render-kinodel/references/resolution-guide.md` and `render_worker.py` helper defaults.
- Project scaffold/brief shape lives in `kinodel-project-layout` and `pipeline-kinodel/templates/brief.json`.
- User-facing default wording lives in `producer-kinodel` and its gate/default references.
- Provider payload examples/templates live in `render-kinodel` provider docs, workflow JSON templates, and provider adapters.

## Required update sweep

1. Update `pipeline-kinodel/templates/brief.json` with explicit `platform`, `aspect_ratio`, `image.width/height`, `video.width/height`, and quality labels.
2. Update `render-kinodel/references/resolution-guide.md` default section. Keep all aspect-ratio tables; only the default section and examples should change unless the math changed.
3. Update runtime fallbacks in `render-kinodel/scripts/render_worker.py`:
   - `parse_aspect_ratio(None)` fallback.
   - `brief_defaults()` fallback `aspect_ratio` and `video_resolution`.
   - `video_size_for_quality()` default quality if video default changed.
4. Update provider fallbacks where they exist:
   - `render-kinodel/scripts/providers/fal_provider.py` default image aspect and video resolution.
   - `render-kinodel/scripts/providers/comfyui_provider.py` default image dimensions.
   - any standalone helper such as `scripts/fal_video_generate.py`.
5. Update durable docs/contracts:
   - `pipeline-kinodel/SKILL.md` provider stack defaults.
   - `producer-kinodel/SKILL.md` BriefGate defaults.
   - `kinodel-project-layout/SKILL.md` brief contract example.
   - `render-kinodel/SKILL.md` dimension pitfall/default text.
   - `render-kinodel/references/request-contract.md` default request example.
   - `producer-kinodel/references/gate-ui.md` and `brief-gate-defaults.md`.
6. Update provider examples/workflow templates under `render-kinodel/workflows/`, `templates/`, and `providers/` so audit payloads do not contradict runtime defaults.
7. Update tests that encode defaults. Keep tests for non-default aspect ratios; they verify the resolution guide still works beyond the default.
8. Run verification:
   ```bash
   python3 -m py_compile ~/.hermes/skills/kinodel/render-kinodel/scripts/render_worker.py \
     ~/.hermes/skills/kinodel/render-kinodel/scripts/providers/fal_provider.py \
     ~/.hermes/skills/kinodel/render-kinodel/scripts/providers/comfyui_provider.py
   python3 ~/.hermes/skills/kinodel/render-kinodel/tests/test_render_worker_resume.py
   python3 ~/.hermes/skills/kinodel/render-kinodel/tests/test_render_entrypoint_retry.py
   python3 ~/.hermes/skills/kinodel/render-kinodel/tests/test_copy_worker_result.py
   python3 ~/.hermes/skills/kinodel/producer-kinodel/tests/test_state_guard_pipeline_runtime.py
   python3 ~/.hermes/skills/kinodel/kinodel-project-layout/tests/test_init_project_phase_c.py
   ```
9. Search for stale default wording, not for legitimate table rows:
   - bad stale default patterns: `Default 9:16`, `default 9:16`, `vertical reels`, `720p, audio off`, `image.width=576`, `video.width=720`.
   - acceptable table rows: resolution-guide entries for non-default aspect ratios such as `9:16 | 576x1024`.

## Pitfall

Do not only patch the brief template. Default changes are cross-cutting: Producer BriefGate prompts, Layout examples, `kinodel-project-layout/scripts/init_project.py` brief normalizers, specialist-agent defaults (especially `filmmaker-kinodel` for video workflow), Render runtime fallbacks, provider payload examples, ComfyUI workflow defaults, fal helper defaults, `producer-kinodel/scripts/state_guard.py` stale-artifact validation, and regression tests all need to agree.

Workflow/provider brief pitfall: if `brief.json` does not persist both `video.workflow`/`video.flow` and provider/default fields (`provider`, `provider_image`, `provider_edit`, `provider_video`, `provider_flf2v`, plus `defaults.*`), downstream agents tend to invent workflow/provider choices. For Kinodel default changes, verify the canonical default is frozen at BriefGate/init time and enforced by state_guard before render. Current default: `comfyui + i2v + 480p + 4s`; explicit `flf2v` remains `fal:veo31_lite_flf2v` until a production ComfyUI flf2v workflow is registered.