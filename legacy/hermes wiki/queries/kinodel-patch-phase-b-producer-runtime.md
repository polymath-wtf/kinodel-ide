---
title: Kinodel Patch Phase B — Producer reads spec with hardcoded fallback
created: 2026-05-18
type: query
tags: [kinodel, patch-phase, pipeline-runtime, phase-b]
phase: B
status: done
depends_on: phase-a
sources:
  - [[kinodel-patch-implementation-plan]]
  - [[kinodel-patch-phase-a-spec-validator]]
  - [[kinodel-pipeline-runtime]]
  - current-skills:kinodel/pipeline-kinodel
  - current-skills:kinodel/producer-kinodel
---

# Kinodel Patch Phase B — Producer reads spec with hardcoded fallback

## Copy-paste prompt for GPT agent

```text
Read first:
/home/seryogasakura/wiki/queries/kinodel-patch-implementation-plan.md
/home/seryogasakura/wiki/queries/kinodel-patch-phase-a-spec-validator.md
/home/seryogasakura/wiki/queries/kinodel-patch-phase-b-producer-runtime.md

Task: implement ONLY Phase B of the Kinodel flexible runtime patch.
Core goal: make producer-kinodel/scripts/state_guard.py spec-aware through a CompiledRoute abstraction, while preserving hardcoded cinematic fallback and old command behavior.

Do not implement new serial/music pipelines. Do not change init_project layouts yet except reading existing project-local spec if present. Do not add multi-anchor behavior.

Required proof: old cinematic next-goal and handoff behavior must remain equivalent; spec-based projects cannot pass review gates by artifact existence alone; p4/p7 gates must still hard-stop and must not become delegatable.
```

## Objective

Producer can read `kinodel.pipeline_spec.v1` but current cinematic projects keep working exactly.

This phase converts the runtime from “many cinematic maps are truth” to “CompiledRoute is truth”, while keeping the old maps as fallback until parity is proven.

## Scope

Modify:

- `/home/seryogasakura/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py`

Possibly create:

- `/home/seryogasakura/.hermes/skills/kinodel/producer-kinodel/scripts/pipeline_runtime.py`
- `/home/seryogasakura/.hermes/skills/kinodel/producer-kinodel/tests/test_state_guard_pipeline_runtime.py`
- `/home/seryogasakura/.hermes/skills/kinodel/producer-kinodel/references/pipeline-spec-runtime.md`

Do not modify:

- layout initializer behavior
- render provider behavior
- specialist agent contracts
- serial/music specs.

## Core implementation requirements

### 1. Spec resolution order

When runtime needs a route, resolve in this order:

1. explicit CLI `--pipeline-spec`, if added
2. project-local `pipeline_spec.json`
3. `producer_state.json.pipeline_id` → skill registry spec path
4. hardcoded cinematic fallback.

Registry default path:

```text
/home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/pipelines/<pipeline_id>.json
```

### 2. CompiledRoute abstraction

Do not scatter dynamic replacements for every old map.

`CompiledRoute` should expose:

- ordered goals
- stage descriptor by goal
- reads/writes by goal
- validators by artifact/schema
- render stage metadata
- gate metadata
- final chunk metadata
- legacy compatibility aliases.

Old constants may remain but should feed fallback/compatibility only.

### 3. Next-goal behavior

`infer_next_goal()` must be able to walk the compiled route.

For old projects without spec/state:

- preserve current behavior.

For spec projects:

- use stage order and artifact validation.
- gate stages are returned as gates/stops, not delegated as normal agent stages.
- review gates cannot be treated as approved just because preview/render artifacts exist.
- if the route reaches a gate and no explicit approval exists in gate decision state, return STOP_AT_GATE / the gate goal.

### 4. Handoff behavior

`build_handoff()` should read owner/read/write metadata from route.

Preserve current handoff shape enough that existing specialist flows still work.

Handoff for a downstream stage after a spec gate must require explicit approved gate state. A completed render result is not enough.

### 5. Explicit gate-state prep

Minimum required in this phase:

- compiled gate descriptor includes `goal`, `gate_alias`, `gate_kind`, `stop`, `choices`.
- route/runtime has a function or placeholder interface for checking gate decisions.
- spec-based projects do not pass gates without explicit approval.
- old p4/p7 heuristic remains fallback only for legacy projects without spec/state.

## Test gate

Create temp cinematic projects with current stubs and compare:

- next goal at empty/brief/story/wardrobe/render checkpoints
- p4 and p7 returned as stop gates
- `handoff --goal p5_storyboard_plan` has same essential reads/writes as before after approval state
- `handoff --goal p5_storyboard_plan` is rejected or blocked before p4 approval state in spec projects.

Minimum commands:

```bash
python3 -m py_compile /home/seryogasakura/.hermes/skills/kinodel/producer-kinodel/scripts/state_guard.py
python3 -m py_compile /home/seryogasakura/.hermes/skills/kinodel/producer-kinodel/scripts/pipeline_runtime.py || true
python3 /home/seryogasakura/.hermes/skills/kinodel/producer-kinodel/tests/test_state_guard_pipeline_runtime.py
```

If test file is not created, use deterministic temp-project smoke scripts and include outputs in summary.

Required gate regression:

- spec project with complete p3 render result but no p4 gate decision must stop at p4;
- adding explicit p4 approval may unlock p5;
- legacy project without `pipeline_spec.json`/`producer_state.json` preserves old p4/p7 fallback behavior.

## Acceptance criteria

- Existing cinematic route still resumes correctly.
- `cinematic.v1` can drive route metadata.
- Hardcoded fallback still exists.
- Spec-based projects cannot pass review gates by artifact existence alone.
- p4/p7 are hard-stop stages, not normal delegate stages.
- No serial/music behavior is implemented yet.

## Stop line

Stop after spec-aware Producer parity. Do not start layout profiles or contracts in the same pass.

## Related docs

- [[kinodel-patch-phase-a-spec-validator]]
- [[kinodel-pipeline-runtime]]
- [[pipeline-kinodel]]
