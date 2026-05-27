# Kinodel Pipeline Specs

This directory stores machine-readable `kinodel.pipeline_spec.v1` specs.

Phase A adds validation infrastructure only:

- `schema/pipeline_spec.v1.json` describes the minimum JSON shape.
- `cinematic.v1.json` is the compatibility mirror of the current p0-p11 cinematic route.
- `scripts/validate_pipeline_spec.py` performs semantic checks that JSON Schema alone cannot safely express.

Phase A does not change Producer, project initialization, render scripts, or specialist prompts. Runtime consumption is intentionally deferred to later phases.
