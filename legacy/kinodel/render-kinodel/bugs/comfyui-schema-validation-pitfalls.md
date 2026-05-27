---
name: bug comfyui schema validation
trigger: "ComfyUI prompt_outputs_failed_validation, value_not_in_list, bool/string enum mismatch, seed below min"
description: ComfyUI node schemas are strict. Normalize seed and enum strings from the node input_config before submit.
category: bug
---

# Bug: ComfyUI schema validation

Crash/signature: HTTP 400 `prompt_outputs_failed_validation`, `value_not_in_list`, `seed smaller than min`, bool received where string enum is expected.

Cause: ComfyUI workflow node inputs require exact enum strings/model names and valid numeric ranges.

Fix:
1. Read `node_errors.*.errors[].extra_info.input_config`.
2. Use exact enum/model values from ComfyUI.
3. Normalize common fields: `seed >= 0`, resize mode string such as `stretch`, attention string such as `disabled`.
4. Keep this path backup-only; fal.ai remains the Kinodel default.
