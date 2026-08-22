# Producer Pipeline Spec Runtime

Phase B adds spec-aware routing to `scripts/state_guard.py` while preserving the hardcoded cinematic fallback.

## Spec resolution order

When route metadata is needed, state_guard resolves:

1. explicit `--pipeline-spec` path passed to `next-goal` or `handoff`;
2. project-local `pipeline_spec.json`;
3. `producer_state.json.pipeline_id` mapped to `~/.hermes/skills/kinodel/pipeline-kinodel/pipelines/<pipeline_id>.json`;
4. hardcoded legacy cinematic fallback.

If `producer_state.json.pipeline_id` names a missing registry spec, state_guard fail-closes instead of silently falling back.

## CompiledRoute shape

`compile_spec_route()` and `compile_legacy_route()` both return the same route dictionary shape. This is the Phase B CompiledRoute abstraction and includes:

- `ordered_goals`
- `stages_by_goal`
- `delegated`
- `exit_artifacts`
- `validators`
- `render_stages`
- `review_gates`
- `final_chunk`
- `compatibility`

Helpers should read the compiled route instead of adding parallel dynamic maps.

## Gate rule

Spec-based projects require explicit approval in `producer_state.json.gate_decisions[]` before downstream handoffs. The approval may match either gate `goal` or `gate_alias`, and decisions accepted as approvals are `A`, `approve`, `approved`, `yes`, or `true`.

Render-result existence alone never approves a spec-based ReviewGate. Legacy projects without spec/state keep the old p4/p7 heuristic fallback for compatibility.

## Diagnostic CLI

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py next-goal \
  --project-dir ~/projects/<project_id>/v1 \
  --pipeline-spec ~/.hermes/skills/kinodel/pipeline-kinodel/pipelines/cinematic.v1.json

python3 ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py handoff \
  --project-dir ~/projects/<project_id>/v1 \
  --goal p5_storyboard_plan \
  --pipeline-spec ~/.hermes/skills/kinodel/pipeline-kinodel/pipelines/cinematic.v1.json
```

`--pipeline-spec` is a Phase B diagnostic/compatibility input. Normal Phase C+ projects should use project-local frozen `pipeline_spec.json` plus `producer_state.json`.

## Regression tests

Run:

```bash
python3 ~/.hermes/skills/kinodel/producer-kinodel/tests/test_state_guard_pipeline_runtime.py
```

The suite covers compiled route metadata, registry resolution, explicit spec priority, p4/p7 hard stops, explicit p4/p7 approval unlocks, non-delegatable gates, and legacy fallback compatibility.