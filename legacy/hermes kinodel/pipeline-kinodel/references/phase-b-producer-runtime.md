# Phase B — Producer Spec-Aware Runtime

Use this reference when continuing the Kinodel flexible runtime patch after Phase B, or when auditing Producer/state_guard behavior.

## Current Phase B artifact locations

- `../producer-kinodel/scripts/state_guard.py` — spec-aware Producer guard/runtime helper.
- `../producer-kinodel/tests/test_state_guard_pipeline_runtime.py` — Phase B regression tests.
- `../producer-kinodel/references/pipeline-spec-runtime.md` — Producer-owned runtime details and CLI examples.
- `pipelines/cinematic.v1.json` — canonical cinematic spec consumed by Phase B.

## Phase B invariant

Phase B is Producer runtime parity only. It makes `state_guard.py` read `kinodel.pipeline_spec.v1` through one compiled route abstraction while preserving hardcoded cinematic fallback. It must not add layout profiles, mutate init_project behavior, activate serial/music pipelines, or change render provider behavior.

## Spec resolution order

Producer route resolution is:

1. explicit `--pipeline-spec` path for diagnostics/compatibility;
2. project-local `pipeline_spec.json`;
3. `producer_state.json.pipeline_id` resolved under `~/.hermes/skills/kinodel/pipeline-kinodel/pipelines/<pipeline_id>.json`;
4. legacy hardcoded cinematic fallback.

If `producer_state.json.pipeline_id` points to a missing registry spec, fail closed instead of silently falling back.

## CompiledRoute shape

Both spec-based and legacy fallback routes expose the same dictionary shape:

- `ordered_goals`
- `stages_by_goal`
- `delegated`
- `exit_artifacts`
- `validators`
- `render_stages`
- `review_gates`
- `final_chunk`
- `compatibility`

Future Producer helpers should read this compiled route rather than adding new parallel maps.

## Gate rule

Spec-based projects require explicit approval in `producer_state.json.gate_decisions[]` before downstream handoffs. Approval can match gate `goal` or `gate_alias`; accepted approvals are `A`, `approve`, `approved`, `yes`, and `true`.

Render-result existence alone never approves a spec-based ReviewGate. Legacy projects without spec/state keep the old p4/p7 heuristic fallback only for compatibility.

## Required verification commands

```bash
python3 -m py_compile ~/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py

python3 ~/.hermes/skills/kinodel/producer-kinodel/tests/test_state_guard_pipeline_runtime.py

python3 ~/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py \
  ~/.hermes/skills/kinodel/pipeline-kinodel/pipelines/cinematic.v1.json
```

Expected result: Producer tests pass; `cinematic.v1` still validates.

## Regression checks covered by tests

- `cinematic.v1` compiles into route metadata;
- p4/p7 are review gates and are not delegatable;
- registry resolution through `producer_state.json.pipeline_id` works;
- explicit `--pipeline-spec` has highest priority;
- spec route walks stage artifacts before p4;
- spec project with complete p3 but no p4 approval stops at p4;
- explicit p4 approval unlocks p5 next goal and handoff;
- spec project with complete story frames but no p7 approval stops at p7;
- explicit p7 approval unlocks p8 handoff;
- legacy project without spec/state preserves old p4/p7 fallback and direct handoff compatibility.

## Phase C handoff note

Phase C should build on this runtime by adding layout profiles, project-local frozen `pipeline_spec.json`, `producer_state.json`, PipelineChoiceGate, and active cinematic capability contracts. Do not bypass p4/p7 while adding these pieces.