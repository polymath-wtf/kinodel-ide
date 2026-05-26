# Fal.ai troubleshooting for Kinodel

## Authentication
- Use `Authorization: Key $FAL_KEY`
- Do not use `Bearer`

## Public URL rule for input media
Problem:
- Passing `outputs/foo.png` or any local path into `input_media` for fal.ai jobs causes preflight failure / validation failure.

Fix:
- Always use public URLs from `render_results/*.json.selected_outputs[].url`.
- `selected_outputs` is the chaining truth.
- `outputs/` is local archive/cache only.

## Request schema mismatch
Problem:
- Planner writes non-canonical shapes such as `anchors`, nested job containers, or provider payloads directly.

Fix:
- Request artifacts must follow `kinodel.render_requests.v1` with top-level `jobs[]`.

## Queue rules
- Poll queue status endpoints, not final response endpoints, until terminal state.
- HTTP 202 during polling means in-progress, not failure.
- For Veo 3.1 Lite, prefer returned `status_url` and `response_url` over hand-constructed URLs.

## Nano Banana edit validation
- `/edit` requires `image_urls: string[]`
- `image_url` singular causes 422

## Canonical locations
- Provider details: `providers/fal_nano_banana_2*.md`, `providers/fal_veo31_lite*.md`
- Render chaining truth: `render_results/*.json.selected_outputs[].url`
