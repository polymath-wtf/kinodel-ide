---
title: Kinodel Patch Phase C — Layout profiles, contracts, templates, PipelineChoiceGate
created: 2026-05-18
type: query
tags: [kinodel, patch-phase, contracts, layout, templates, phase-c]
phase: C
status: done
depends_on: phase-b
sources:
  - [[kinodel-patch-implementation-plan]]
  - [[kinodel-patch-phase-b-producer-runtime]]
  - [[kinodel-pipeline-runtime]]
  - [[create-pipeline]]
  - current-skills:kinodel/producer-kinodel
  - current-skills:kinodel/kinodel-project-layout
  - current-skills:kinodel/pipeline-kinodel
---

# Kinodel Patch Phase C — Layout profiles, contracts, templates, PipelineChoiceGate

## Copy-paste prompt for GPT agent

```text
Read first:
/home/seryogasakura/wiki/queries/kinodel-patch-implementation-plan.md
/home/seryogasakura/wiki/queries/kinodel-patch-phase-b-producer-runtime.md
/home/seryogasakura/wiki/queries/kinodel-patch-phase-c-layout-contracts-templates.md

Task: implement ONLY Phase C of the Kinodel flexible runtime patch.
Core goal: add safe project layout profiles, project-local pipeline_spec copy, producer_state, PipelineChoiceGate before BriefGate/init_project, current-worker capability contracts, and fix legacy request templates so they match render request envelopes.

Do not implement serial agents, music-video, ComfyUI workflow routing, or Wardrobe multi-anchor active behavior. Keep cinematic default identical. Non-cinematic profiles may be declared/planned but must not be active production choices until D/E.

Required proof: old init_project CLI still produces compatible cinematic projects; new projects store pipeline_id/spec/state; cinematic.v1 validates against active contracts; canonical templates no longer contradict render request contract; non-cinematic profiles are rejected or locked until their phase activates them.
```

## Objective

Make the runtime ecosystem ready for new specs without actually adding new production pipelines.

This phase bridges Producer spec-awareness to project creation and worker binding:

- layout profiles
- frozen project-local spec
- producer_state fields
- PipelineChoiceGate before BriefGate/init_project
- current agent capability contracts
- canonical render request templates.

## Scope

Modify:

- `/home/seryogasakura/.hermes/skills/kinodel/kinodel-project-layout/scripts/init_project.py`
- sync or deprecate forwarding duplicate: `/home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/scripts/init_project.py`
- pipeline templates under `/home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/templates/`
- Producer docs/playbook for pipeline choice before BriefGate/init_project.

Create:

- per-skill `contracts/capabilities.v1.json` for current active cinematic workers, or a centralized contract registry if simpler.
- contract validator script, likely under `pipeline-kinodel/scripts/validate_agent_contracts.py`.

Do not modify:

- specialist creative instructions beyond pointers to contracts.
- render provider execution.
- serial/music pipeline specs.

## Core implementation requirements

### 1. Preserve existing init CLI

This must still work:

```bash
python3 ~/.hermes/skills/kinodel/kinodel-project-layout/scripts/init_project.py <project_id> '<brief_json>'
```

For default cinematic, output must remain compatible with current Producer and Phase B runtime.

### 2. Add optional layout/spec flags

Add optional flags only:

- `--pipeline-id`
- `--layout-profile`
- `--pipeline-spec`

Default:

- `pipeline_id=cinematic.v1`
- `layout_profile=cinematic`

### 3. Project-local frozen spec and state

For new initialized projects, write:

- `pipeline_spec.json`
- `producer_state.json`

Minimum producer state:

```json
{
  "schema": "kinodel.producer_state.v1",
  "pipeline_id": "cinematic.v1",
  "current_goal": "p0_briefgate",
  "stage_cursor": 0,
  "gate_decisions": []
}
```

For old projects without these files, Phase B fallback must still work.

### 4. PipelineChoiceGate before BriefGate/init_project

Producer must select or infer `pipeline_id` before initializing the project directory.

Rules:

- This is a pre-brief selector, not a ReviewGate and not approval to bypass p4/p7.
- If the user clearly asks for a normal short cinematic/reels/video, default to `cinematic.v1`.
- If intent is ambiguous or clearly non-cinematic, ask a compact PipelineChoiceGate.
- Only active pipelines may be selected for production.
- Planned pipelines can be displayed as locked/planned, but Producer must not initialize them until their activation phase passes.

Suggested text after all MVP phases are active:

```text
Choose pipeline:
A — cinematic.v1: short cinematic/reels video, current stable path
B — serial_season.v1: season/world/episode bible
C — serial_episode.v1: one episode from season_chunk
D — music_video.v1: music/lyrics/timing driven clip
```

During Phase C only:

```text
Active now:
A — cinematic.v1

Planned/locked until later phases:
B — serial_season.v1
C — serial_episode.v1
D — music_video.v1
```

### 5. Layout profiles

Supported profile names may be declared:

- `cinematic`
- `serial_season`
- `serial_episode`
- `music_video`
- `renovation_timelapse`

Only `cinematic` is active in this phase.

Non-cinematic profiles must be rejected or locked unless all of these are true:

- corresponding pipeline spec exists and validates;
- required active capability contracts are bindable;
- the relevant phase has explicitly activated the pipeline.

Other profiles may be skeleton-supported for validation only, but must not create random empty production projects before approved input/context exists.

### 6. Capability contracts

Active contracts only for current cinematic capabilities:

- `narrative_planning.cinematic.v1`
- `visual_anchor_planning.single.v1`
- `story_frame_planning.cinematic.v1`
- `video_motion_planning.i2v_flf2v.v1`
- `montage_assembly.simple.v1`
- `review_qc.v1`
- render fal image/video kinds currently supported.

Future capabilities may be included only as `status: planned` and must not validate as bindable.

### 7. Template cleanup

Canonical durable request templates must use envelope shape:

```json
{
  "schema": "kinodel.render_requests.v1",
  "project_id": "PROJECT_ID",
  "status": "complete",
  "stage": "main_frame",
  "jobs": []
}
```

Remove local `/home/...` paths from canonical examples. Use selected_outputs placeholders or `https://...` examples.

## Test gate

Minimum:

```bash
python3 -m py_compile   /home/seryogasakura/.hermes/skills/kinodel/kinodel-project-layout/scripts/init_project.py

python3 /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py   /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/pipelines/cinematic.v1.json

python3 /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_agent_contracts.py
```

Also run a temp cinematic init smoke test and inspect that old required files still exist plus new files:

- `brief.json`
- `story.json`
- `wardrobe_request.json`
- `storyboard_requests.json`
- `video_requests.json`
- `render_results/main_frame_result.json`
- `render_results/story_frames_result.json`
- `render_results/shot_videos_result.json`
- `pipeline_spec.json`
- `producer_state.json`

Required profile lock tests:

- default init creates `cinematic.v1` project;
- `--pipeline-id cinematic.v1` works;
- `--pipeline-id serial_season.v1` / `music_video.v1` is rejected or clearly locked in Phase C;
- planned capabilities do not validate as bindable.

Required template checks:

- no canonical render request template is a bare array;
- each durable request template has `schema`, `project_id`, `status`, `stage`, `jobs`.

## Acceptance criteria

- Existing cinematic init path still works.
- `pipeline_spec.json` and `producer_state.json` are present for new projects.
- Producer can select/store `pipeline_id` before BriefGate/init_project.
- `cinematic.v1` validates against active contracts.
- Non-cinematic profiles are not active production profiles before D/E.
- Planned capabilities cannot be bound.
- Durable templates match `kinodel.render_requests.v1` envelope.

## Stop line

Stop after layout/contracts/templates/PipelineChoiceGate. Do not implement serial specs or multi-anchor active behavior yet.

## Related docs

- [[kinodel-patch-phase-b-producer-runtime]]
- [[kinodel-pipeline-runtime]]
- [[create-pipeline]]
