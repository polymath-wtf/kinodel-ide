# Render bugs mapping

Compact map of render failures that can still occur. Load only the matching bug note.

| Trigger | Bug note | Fix summary |
| --- | --- | --- |
| fal.ai 422 with local path or `outputs/...` | `render-kinodel/bug/local-url-to-fal-422.md` | Use public `selected_outputs[].url` for remote provider inputs. |
| nano-banana-2 422 on `aspect_ratio: custom` | `render-kinodel/bug/nano-banana-2-custom-aspect-422-fix.md` | Use supported 9:16/worker mapping; patch worker mapping if needed. |
| worker skips/rejects jobs or sees legacy `anchors` | `render-kinodel/bug/payload-schema-mismatch.md` | Rewrite to `kinodel.render_requests.v1` with `jobs`. |
| ComfyUI `/health` okay but `/prompt` wrong | `render-kinodel/bug/comfyui-endpoint-drift.md` | Re-probe endpoint identity and update ComfyUI URL. |
| ComfyUI validation enum/model/seed errors | `render-kinodel/bug/comfyui-schema-validation-pitfalls.md` | Normalize exact node input_config values. |
