# Phase A — Pipeline Spec + Validator

Use this reference when continuing the Kinodel flexible runtime patch after the static-spec phase.

## Current Phase A artifact locations

- `pipelines/schema/pipeline_spec.v1.json` — minimum JSON Schema shape for `kinodel.pipeline_spec.v1`.
- `pipelines/cinematic.v1.json` — lossless machine-readable mirror of the legacy p0-p11 cinematic route.
- `scripts/validate_pipeline_spec.py` — static semantic validator for pipeline specs.
- `tests/test_validate_pipeline_spec.py` — lightweight unittest regression suite for the validator.
- `pipelines/README.md` — short registry notes.

## Phase A invariant

Phase A is data/validation only. It must not change production runtime behavior. Do not modify Producer runtime, project initialization, render scripts, or specialist prompts as part of Phase A cleanup.

## Required verification commands

```bash
python3 ~/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py \
  ~/.hermes/skills/kinodel/pipeline-kinodel/pipelines/cinematic.v1.json

python3 -m py_compile \
  ~/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py

python3 ~/.hermes/skills/kinodel/pipeline-kinodel/tests/test_validate_pipeline_spec.py
```

Expected result: validator prints OK for `cinematic.v1`; unittest suite passes all tests.

## Negative checks covered by tests

- duplicate goals fail;
- `review_gate` with `stop: false` fails;
- `cinematic.v1` missing hard p4/p7 aliases fails;
- render stage missing request/result artifact fails;
- wrong top-level schema fails;
- unknown stage type fails;
- final chunk missing schema fails.

## Phase B handoff note

Before Phase B, inspect existing `producer-kinodel/scripts/state_guard.py`. It may already contain partial spec-aware route logic from previous work. Reconcile that code with `cinematic.v1` instead of blindly adding a second dynamic route layer. The desired abstraction remains one compiled route, not parallel maps.
