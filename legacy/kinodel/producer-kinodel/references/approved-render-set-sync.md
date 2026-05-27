# Approved render-set sync

Use this when a user picks an earlier render attempt as the canonical one for a stage.

## Rule of truth
- Treat `render_results/<stage>_result.json.selected_outputs` as the downstream source of truth.
- The manifest must point at the approved attempt, even if a later rerender exists in `/tmp/kinodel/...`.
- Downstream stages should consume the approved refs only; do not mix approved and superseded attempts.

## Sync recipe
1. Copy the approved worker result into the project manifest with `copy_worker_result.py`.
2. Overwrite project-local `outputs/<shot>.*` with the approved attempt's files if they drifted.
3. Revalidate the request artifact if it was edited after the approved render; a changed request can make the result stale.
4. If the request changed materially, rerender from the approved request instead of trying to reconcile mixed generations.

## Verification
- `state_guard.py validate --artifact render_results/<stage>_result.json`
- `state_guard.py validate --artifact <request>.json`
- Compare hashes of `outputs/<shot>` against the approved source files when the user explicitly asks to restore an older canonical attempt.