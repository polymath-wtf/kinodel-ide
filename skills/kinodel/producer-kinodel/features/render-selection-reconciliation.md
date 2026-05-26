# Render Selection Reconciliation

Use this note when the user explicitly prefers an earlier render attempt over a later rerender.

## What to do

1. Treat the user-chosen render batch as canonical, even if a newer rerender exists.
2. Promote that batch into `render_results/<stage>_result.json` by copying the worker result with the packaged copier.
3. Make the project-local `outputs/shot_XX.png` files byte-for-byte match the selected `api_*.png` files that the result manifest points to.
4. If a later rerender changed the request artifact, revert the request artifact back to the user-approved version so the validated request/result pair stays in sync.
5. Re-run validation after the revert so the durable request and result hashes agree.

## Why this matters

Kinodel state is request-hash driven. If `storyboard_requests.json` drifts after a selected render result is already accepted, `render_results/story_frames_result.json` becomes stale and downstream validation can fail even when the images themselves are fine.

## Practical check

- `render_results/<stage>_result.json.selected_outputs[]` should point to the canonical outputs.
- `outputs/shot_XX.png` should be copied from the selected batch, not left on a later rerender.
- If the user says an earlier attempt is better, prefer reconciliation over further rerendering unless they ask for new edits.