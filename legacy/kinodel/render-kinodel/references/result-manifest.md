# Result Manifest Contract

Worker temporary results are copied by Producer into project-bound manifests under `v1/render_results/`.

## Shape

```json
{
  "schema": "kinodel.render_result.v1",
  "project_id": "project_id",
  "status": "complete",
  "stage": "story_frames",
  "selected_outputs": [
    {
      "shot_id": "shot_01",
      "kind": "image",
      "path": "outputs/shot_01_v03.png",
      "url": "https://...",
      "selected": true
    }
  ],
  "attempts": [
    {
      "shot_id": "shot_01",
      "kind": "image",
      "path": "outputs/shot_01_v01.png",
      "url": "https://...",
      "selected": false,
      "reason": "superseded"
    }
  ],
  "selection_policy": "selected_outputs contains current refs for downstream stages."
}
```

## Semantics

- `selected_outputs` is the current truth for downstream agents.
- `attempts` is compact history for resume and user comparisons.
- `outputs/` may contain stale files; never infer truth from newest filename.
- `url` is required for external downstream i2i/i2v/flf2v.
- `path` is used for local preview and final chunk refs.

## Persistence rule

Keep temporary worker files and raw provider responses in `/tmp/kinodel/<project_id>/<run_id>/` or `.render_debugs/`. Copy only compact refs into `render_results/*.json`.
