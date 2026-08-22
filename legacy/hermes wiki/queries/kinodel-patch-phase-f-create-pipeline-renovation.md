---
title: Kinodel Patch Phase F — create-pipeline and renovation_timelapse draft/test
created: 2026-05-18
type: query
tags: [kinodel, patch-phase, create-pipeline, renovation-timelapse, phase-f]
phase: F
status: planned
depends_on: phase-e
sources:
  - [[kinodel-patch-implementation-plan]]
  - [[kinodel-patch-phase-e-music-video]]
  - [[kinodel-pipeline-runtime]]
  - [[create-pipeline]]
  - [[kinodel-flexible-pipeline-patch]]
---

# Kinodel Patch Phase F — create-pipeline and renovation_timelapse draft/test

## Copy-paste prompt for GPT agent

```text
Read first:
/home/seryogasakura/wiki/queries/kinodel-patch-implementation-plan.md
/home/seryogasakura/wiki/queries/kinodel-patch-phase-f-create-pipeline-renovation.md
Then inspect: [[create-pipeline]], [[kinodel-pipeline-runtime]], [[kinodel-flexible-pipeline-patch]].

Task: implement ONLY Phase F of the Kinodel flexible runtime patch.
Core goal: add create-pipeline spec drafting support and run a test/draft creation of renovation_timelapse.v1 through that path.

Do not mutate live runtime automatically from create-pipeline output. Do not make renovation_timelapse an active production pipeline unless separately approved after draft validation. Do not rewrite cinematic/serial/music runtime unless regression tests prove it is necessary.

Required proof: create-pipeline drafts specs without applying them; renovation_timelapse draft contains stage map, artifacts, capabilities, render profiles/workflow IDs, unsupported capability notes, and verification plan.
```

## Objective

Add the meta-pipeline authoring path after cinematic, serial, and music runtime compatibility is proven.

This phase validates that Kinodel can design future pipeline specs safely without live mutation.

## Scope

Create/modify:

- create-pipeline docs/contracts for draft spec output.
- optional helper/validator for draft pipeline proposals.
- draft/test `renovation_timelapse.v1` output path, preferably under a drafts/proposals area until explicitly approved.

Optional only after create-pipeline contract is stable:

- `pipeline-kinodel/pipelines/renovation_timelapse.v1.json` as a draft/example with `status: draft` or equivalent inactive marker.

Do not modify:

- live runtime to auto-apply create-pipeline proposals.
- cinematic/serial/music specs except if validation exposes a real bug.
- render provider code unless draft validation requires a non-invasive adapter declaration.

## Core implementation requirements

### 1. create-pipeline drafts specs, not live mutations

`create-pipeline` must output a proposal, not directly patch live skills or execute production.

Output must include:

- proposed `pipeline_id`
- proposed spec path
- stage-by-stage agent task map
- required artifacts/contracts/chunks
- render profiles/workflow IDs
- unsupported capabilities
- verification plan
- activation checklist.

For serial designs, it must not emit `serial.v1` as MVP. Use `serial_season.v1` and/or `serial_episode.v1`.

### 2. Draft proposal lifecycle

A generated pipeline proposal should have states such as:

- `draft`
- `validated`
- `approved_for_activation`
- `active`

Only `active` pipeline specs may appear as production choices in PipelineChoiceGate.

### 3. Renovation timelapse draft/test

Use create-pipeline to draft/test `renovation_timelapse.v1`.

Draft route concept:

```text
brief/reference trend/VLM analysis
→ first bad-renovation frame
→ final luxury-renovation frame
→ intermediate i2i progression frames
→ p4 progression checkpoint, hard stop
→ flf2v transitions across adjacent frames
→ montage as reel/timelapse
→ trend_chunk.json
```

The draft must identify required capabilities, for example:

- reference/trend analysis
- first/last/progression visual anchor planning
- i2i progression frame rendering
- flf2v transition rendering
- montage assembly
- trend_chunk writer.

If any capability is not implemented, mark it unsupported/planned instead of pretending it is active.

### 4. Activation is separate

`renovation_timelapse.v1` remains draft/test unless a later explicit phase or user approval activates it.

PipelineChoiceGate must not offer it as active production unless activation criteria pass.

## Test gate

Minimum:

```bash
python3 /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py   /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/pipelines/cinematic.v1.json

python3 /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py   /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/pipelines/serial_season.v1.json

python3 /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py   /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/pipelines/serial_episode.v1.json

python3 /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py   /home/seryogasakura/.hermes/skills/kinodel/pipeline-kinodel/pipelines/music_video.v1.json
```

Also verify:

- create-pipeline proposal output does not edit live skill files automatically;
- renovation_timelapse proposal includes unsupported capability notes if needed;
- renovation_timelapse is draft/test only unless activation is explicitly approved;
- PipelineChoiceGate does not list draft-only pipelines as active production choices;
- no raw provider workflow payloads are embedded in planner artifacts.

If a draft `renovation_timelapse.v1.json` is committed to the registry, validator must understand inactive/draft specs or the file must live outside the active registry.

## Acceptance criteria

- create-pipeline can draft specs without applying them.
- Test/draft renovation_timelapse proposal exists with stage map, artifacts, capabilities, render profiles, unsupported items, and verification plan.
- Active cinematic/serial/music specs still validate.
- No automatic live mutation or production activation occurs.

## Stop line

Stop after create-pipeline + renovation draft/test. Activation of renovation_timelapse is a separate future phase.

## Related docs

- [[create-pipeline]]
- [[kinodel-pipeline-runtime]]
- [[kinodel-flexible-pipeline-patch]]
