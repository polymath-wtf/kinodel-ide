---
title: Kinodel Patch Phase A — Spec and validator only
created: 2026-05-18
type: query
tags: [kinodel, patch-phase, pipeline-runtime, phase-a]
phase: A
status: done
sources:
  - [[kinodel-patch-implementation-plan]]
  - [[kinodel-pipeline-runtime]]
  - [[kinodel-flexible-pipeline-patch]]
  - current-skills:kinodel/pipeline-kinodel
---

# Kinodel Patch Phase A — Spec and validator only

## Copy-paste prompt for GPT agent

```text
Read first:
/home/seryogasakura/wiki/queries/kinodel-patch-implementation-plan.md
/home/seryogasakura/wiki/queries/kinodel-patch-phase-a-spec-validator.md
Then inspect linked pages only as needed: [[kinodel-pipeline-runtime]], [[kinodel-flexible-pipeline-patch]], [[pipeline-kinodel]].

Task: implement ONLY Phase A of the Kinodel flexible runtime patch.
Core goal: add machine-readable pipeline spec schema, cinematic.v1 spec, and a validator. Do not change production behavior, state_guard runtime, init_project behavior, render behavior, or specialist prompts.

Hard constraints:
- Backward compatibility first.
- No behavior changes in live Kinodel production commands.
- p4 and p7 remain hard ReviewGates with stop=true.
- cinematic.v1 must be a lossless mirror of the current hardcoded p0-p11 route.
- pipeline-kinodel must NOT become a cinematic-only skill; it remains universal law/runtime architecture.
- Use TDD / regression checks where possible.

After implementation, run validator on cinematic.v1, run negative validator tests, and run Python syntax checks. Summarize exact files changed and explicitly confirm what was NOT changed.
```

## Objective

Introduce spec files and validation infrastructure without changing runtime behavior.

This phase exists to make later changes safe: the current cinematic pipeline becomes executable data, but Producer still uses its old hardcoded path until Phase B.

`cinematic.v1` is the saved compatibility mirror of the current hardcoded p0-p11 route. Do not rename or narrow `pipeline-kinodel` into a cinematic-pipeline skill; `pipeline-kinodel` remains the universal architecture/law owner.

## Scope

Create:

- `/home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/pipelines/schema/pipeline_spec.v1.json`
- `/home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/pipelines/cinematic.v1.json`
- `/home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py`
- tests or lightweight unittest file for the validator if no test framework is installed.

Optional:

- `/home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/pipelines/README.md`

Do not modify:

- `producer-kinodel/scripts/state_guard.py`
- `kinodel-project-layout/scripts/init_project.py`
- render scripts
- specialist SKILL.md files, except a tiny reference pointer if truly necessary.

## Core implementation requirements

### 1. pipeline_spec.v1 schema

Minimum required shape:

```json
{
  "schema": "kinodel.pipeline_spec.v1",
  "pipeline_id": "cinematic.v1",
  "display_name": "Cinematic Pipeline",
  "version": 1,
  "compatibility": {
    "legacy_goal_aliases": true,
    "hard_gate_aliases": ["p4", "p7"]
  },
  "project_layout_profile": "cinematic",
  "final_chunk": {
    "type": "cinema_chunk",
    "path": "final_chunk.json",
    "schema": "kinodel.final_chunk.v1"
  },
  "chunk_dependencies": [],
  "stages": []
}
```

Each stage must have:

- `goal`
- `type`
- `reads`
- `writes`

Additional fields by stage type:

- `agent_stage`: `owner_skill`, `requires_capabilities`, `validator`
- `render_stage`: `request_artifact`, `result_artifact`, `modality`, `adapter_profile`
- `review_gate`: `gate_alias`, `gate_kind`, `label`, `stop: true`, `choices`
- `montage_stage`: `owner_skill`, `validator`
- `chunk_write_stage`: `chunk_type`, `validator`
- `briefgate` / `context_gate`: explicit input contract.

### 2. cinematic.v1 must mirror current p0-p11

Canonical order:

```text
p0_briefgate
p1_story
p2_main_frame_plan
p3_main_frame_render
p4_story_main_gate
p5_storyboard_plan
p6_story_images_render
p7_story_images_gate
p8_video_plan
p9_video_render
p10_montage
p11_final_chunk
```

Keep existing artifact names:

- `brief.json`
- `story.json`
- `wardrobe_request.json`
- `render_results/main_frame_result.json`
- `storyboard_requests.json`
- `render_results/story_frames_result.json`
- `video_requests.json`
- `render_results/shot_videos_result.json`
- `outputs/final.mp4`
- `final_chunk.json`

### 3. validator checks

Validator should fail on:

- wrong top-level schema
- missing `pipeline_id`
- duplicate goals
- unknown stage type
- missing owner for agent/montage stages
- render stage without request/result artifacts
- review gate without `stop: true`
- p4/p7 aliases not marked hard for cinematic
- final chunk missing `path` or `schema`
- non-linear MVP route inconsistencies, if `next`/graph is included.

Validator should print a clear OK/error summary and exit non-zero on failure.

## Test gate

Minimum commands:

```bash
python3 /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py   /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/pipelines/cinematic.v1.json

python3 -m py_compile   /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py
```

If tests are added:

```bash
python3 /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/tests/test_validate_pipeline_spec.py
```

Required negative checks, either as tests or temp invalid specs:

- duplicate goals fail;
- `review_gate` with `stop: false` fails;
- cinematic spec missing hard p4/p7 aliases fails;
- render stage missing request/result artifact fails.

Required non-change check:

- confirm `producer-kinodel/scripts/state_guard.py` was not changed;
- confirm `kinodel-project-layout/scripts/init_project.py` was not changed;
- confirm render scripts were not changed.

## Acceptance criteria

- `cinematic.v1` validates.
- It is visibly a lossless mirror of the current route.
- `pipeline-kinodel` remains universal architecture/law, not a cinematic-only skill.
- No runtime behavior changed.
- No new dynamic pipelines are introduced yet.
- The next phase can consume the spec as read-only data.

## Stop line

Stop after validator + cinematic spec. Do not start Phase B in the same pass.

## Related docs

- [[kinodel-patch-implementation-plan]]
- [[kinodel-pipeline-runtime]]
- [[kinodel-flexible-pipeline-patch]]
