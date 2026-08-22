# Kinodel skill refactor — 2026-05-15

## Goal

Reduce Kinodel hot-path token load and make pipeline/producer/render skills operate as a compact /goal state machine with progressive disclosure.

## Changed

- Rewrote `pipeline-kinodel/SKILL.md` as a lean architecture map: laws, /goal route, ownership, project layout, artifact contract, ReviewGate contract, defaults, and references.
- Rewrote `producer-kinodel/SKILL.md` as a compact state-machine operator manual.
- Rewrote `render-kinodel/SKILL.md` as a compact worker contract.
- Moved provider/API payload examples out of main SKILL.md into `render-kinodel/references/provider-payload-cookbook.md`.
- Added render request/result reference contracts:
  - `render-kinodel/references/request-contract.md`
  - `render-kinodel/references/result-manifest.md`
- Added Producer references:
  - `producer-kinodel/references/state-machine.md`
  - `producer-kinodel/references/token-aerodynamics.md`
  - `producer-kinodel/references/gate-ui.md`
- Added deterministic helper:
  - `producer-kinodel/scripts/state_guard.py`

## Reference cleanup

Moved misplaced provider references:

- `pipeline-kinodel/references/nano-banana-2-queue-api.md` → `render-kinodel/references/nano-banana-2-queue-api.md`
- `pipeline-kinodel/references/fal_api_troubleshooting.md` → `render-kinodel/references/fal-api-troubleshooting.md`
- `pipeline-kinodel/references/comfyui_api_troubleshooting.md` → `comfyui/references/api-troubleshooting.md`

## New script behavior

`state_guard.py` supports:

```bash
summary  --project-dir ~/projects/<project_id>/v1
validate --project-dir ~/projects/<project_id>/v1 --artifact storyboard_requests.json
handoff  --project-dir ~/projects/<project_id>/v1 --goal p5_storyboard_plan
```

It checks JSON parse, project_id preservation, status=complete, non-empty render jobs, input_media array shape, public HTTPS URLs for external media inputs, and selected_outputs in render manifests.

## Token/cache ergonomics

- Main SKILL.md files are now stable, short prompt prefixes.
- Volatile provider examples and troubleshooting live in references loaded only when needed.
- Producer handoffs are path/ref envelopes, not full artifact dumps.
- `render_results/*.json.selected_outputs` is the cache-friendly media truth.
- L6 runtime scratch remains outside prompt context.

## Validation

- `pipeline-kinodel/SKILL.md`: 168 lines.
- `producer-kinodel/SKILL.md`: 155 lines.
- `render-kinodel/SKILL.md`: 119 lines.
- `state_guard.py`, `render.py`, and `fal.py` compile.
- `state_guard.py handoff` tested on a temporary minimal project.
- Main skills scanned for stale dangerous phrases.
