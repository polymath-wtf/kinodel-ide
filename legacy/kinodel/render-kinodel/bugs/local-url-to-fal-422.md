---
name: bug local url
trigger: "fal.ai i2i/i2v/flf2v returns 422 or rejects input_media path"
description: Remote fal.ai providers cannot read local filesystem paths. Use public HTTPS URLs from previous render_results.selected_outputs.
category: bug
---

# Bug: local URL/path passed to fal.ai

Crash/signature: HTTP 422 from fal.ai, usually in `i2i`, `i2v`, or `flf2v`, with `input_media` containing `/home/...`, `outputs/...`, or `file://...`.

Cause: fal.ai is remote and cannot access local Kinodel paths.

Fix:
1. Read the previous `render_results/*.json` manifest.
2. Use `selected_outputs[].url`, not `selected_outputs[].path`, for remote provider `input_media`.
3. Re-run `state_guard.py validate` before submitting.
