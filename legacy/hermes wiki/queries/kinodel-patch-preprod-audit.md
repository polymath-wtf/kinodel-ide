---
title: Kinodel Patch Pre-production Audit
created: 2026-05-18
type: query
tags: [kinodel, patch, preprod-audit, architecture, blockers]
sources:
  - [[kinodel-patch-implementation-plan]]
  - [[kinodel-patch-phase-a-spec-validator]]
  - [[kinodel-patch-phase-b-producer-runtime]]
  - [[kinodel-patch-phase-c-layout-contracts-templates]]
  - [[kinodel-patch-phase-d-serial-chunks]]
  - [[kinodel-patch-phase-e-music-video]]
  - [[kinodel-patch-phase-f-create-pipeline-renovation]]
confidence: high
contested: false
---

# Kinodel Patch Pre-production Audit

Verdict: NOT ready to build until the blockers below are folded into the phase docs or explicitly accepted as implementation-time constraints.

The phased strategy is directionally sound: docs/spec first, then spec-aware runtime, then layout/contracts, then serial, music, create-pipeline. The risky part is not the architecture direction; the risky part is that several production-critical invariants are stated as principles but not yet enforced as concrete phase tasks/tests.

## Blockers

### 1. Explicit ReviewGate approval state is underspecified

Spec-based projects must not pass gates by artifact existence alone, but Phase B only requires a placeholder/interface for gate decisions, and Phase C starts writing `producer_state.json` for new projects.

Risk: after Phase C, default cinematic projects become spec-based and may deadlock at p4/p7 because there is no production-safe approval writer, or implementers may reintroduce artifact-existence bypasses.

Required before Phase C default spec/state rollout:

- Define durable gate decision schema and storage path, likely in `producer_state.json.gate_decisions[]`.
- Include fields: `goal`, `gate_alias`, `decision`, `approved_at`, `notes_ref`, optional `preview_refs`, optional `actor`.
- Add producer/state_guard command/API to record approve/reject/auto-fix/edit-fix decisions.
- Test:
  - complete p3 result without p4 approval stops at p4;
  - explicit p4 approval unlocks p5;
  - direct `handoff --goal p5_storyboard_plan` fails before approval;
  - same pattern for p7 -> p8;
  - `--skip-gates` stays diagnostic-only.

### 2. Runtime must validate specs before binding

Phase B resolves specs from CLI/project-local/producer_state/registry, but does not explicitly require validation before `CompiledRoute` use.

Risk: malformed or draft specs can route around hard gates or bind missing/unsafe stages.

Required:

- Every loaded non-hardcoded spec must pass `validate_pipeline_spec.py` before runtime binding.
- Runtime must fail closed on validation errors.
- Negative runtime tests:
  - missing p4/p7 hard gate in cinematic spec fails;
  - review_gate with `stop:false` fails;
  - duplicate goal fails;
  - unknown owner/capability fails once contract validation exists.

### 3. Phase D/E activation path is incomplete

Phase C locks non-cinematic profiles. Phase D/E create serial/music specs, but do not explicitly update active pipeline registry / PipelineChoiceGate / init_project allow-list.

Risk: specs validate but cannot be initialized safely, or someone bypasses the official locked-profile path.

Required:

- Phase D must explicitly activate `serial_season.v1` and `serial_episode.v1` only after specs/contracts/layouts validate.
- Phase E must explicitly activate `music_video.v1` only after specs/contracts/audio adapter validate.
- Add init smoke tests for each newly active pipeline.
- PipelineChoiceGate must list only active pipelines; planned/draft remain locked.

### 4. Draft pipeline lifecycle is not fail-closed enough

Phase F allows optional `renovation_timelapse.v1.json` in a registry-looking path as draft/example, while Phase B loads registry specs by pipeline_id.

Risk: draft renovation pipeline becomes runnable just because the file exists.

Required:

- Add top-level spec lifecycle/status: `draft | validated | approved_for_activation | active`.
- Runtime/PipelineChoiceGate must reject non-`active` specs except explicit draft validation tooling.
- Prefer storing drafts outside the active registry, e.g. `pipelines/drafts/` or wiki proposals.
- Test direct attempts to initialize/run a draft pipeline fail closed.

### 5. Phase A cinematic parity needs a real parity test

`cinematic.v1` must be a lossless mirror, but Phase A tests only validate schema and negative cases.

Required:

- Add static parity test comparing `cinematic.v1` to current hardcoded constants/artifacts:
  - p0-p11 order;
  - owner skills;
  - reads/writes;
  - request/result artifact paths;
  - p4/p7 stop gates;
  - final_chunk compatibility.

## High-risk implementation hazards from live skills

These were found by inspecting the current live skill code and templates.

### state_guard.py

- Current runtime is fully cinematic-map based: goal order, schemas, request/result artifacts, review gates, selected refs.
- `build_handoff(project_dir, goal)` can be called directly; for spec projects it must enforce gate approvals, not only read/write availability.
- Phase B should cover `validate_artifact`, summary, next-goal, handoff, selected refs, render metadata, gate metadata, and final chunk metadata through `CompiledRoute`.

### init_project.py duplication

- There are two live copies:
  - `kinodel-project-layout/scripts/init_project.py`
  - `pipeline-kinodel/scripts/init_project.py`
- They must be converted to one canonical implementation plus wrapper, or kept byte-identical via tests.
- Phase C must preserve old CLI: `init_project.py <project_id> '<brief_json>'`.

### templates are currently unsafe examples

Current canonical templates include legacy/bad shapes:

- `storyboard_requests.json` bare array.
- `video_requests.json` bare array.
- `wardrobe_request.json` not a full `kinodel.render_requests.v1` envelope.
- Some input media examples use local `/home/...` paths.

Phase C must make this production-blocking:

- no canonical request template is a bare array;
- every durable request has `schema`, `project_id`, `status`, `stage`, `jobs`;
- no canonical template uses machine-local `/home/...` input media.

### render/copy/wakeup are cinematic-stage hardcoded

- `render.py` supports only `--stage images|videos`.
- `fal.py` defaults kind -> cinematic stage mapping: t2i -> main_frame, i2i -> story_frames, i2v/flf2v -> shot_videos.
- `copy_worker_result.py` only promotes `main_frame`, `story_frames`, `shot_videos`.
- `render_wakeup.py` only knows main_frame/story_frames/shot_videos/montage next actions.

Required for D/E:

- serial anchor stages must not silently become `main_frame`/`story_frames`;
- music/audio needs explicit modality support, not just registry docs;
- copy/wakeup must derive destination/next action/gate requirement from pipeline route or fail safe.

### Wardrobe multi-anchor is not just a spec change

Current Wardrobe contract says one composite anchor / one job. Phase D cannot activate multi-anchor by spec alone.

Required:

- Phase C keeps `visual_anchor_planning.single.v1` active only.
- Phase D updates Wardrobe prompt/contract/tests together before enabling per_episode/per_act.
- Cinematic p2 still produces exactly one main-frame job.

## Mechanical audit results

- No missing wikilinks found in the audited patch docs.
- No live `[[agent-serial-kinodel]]` link found.
- `serial.v1` appears only in warning/negative contexts, not as an MVP spec target.
- Phase E should change `music_request.json` envelope wording from “may include” to “must include at minimum” for `schema`, `project_id`, `status`, `stage`, `jobs`.
- Phase B test gate should not use unconditional `|| true` for `pipeline_runtime.py`; if the file exists, py_compile must pass.
- Phase E/F copy-paste prompts should include their direct dependency phase docs in Read first.

## Minimum patch to the plan before build

1. Add a Phase B gate-decision schema and approval command/API requirement.
2. Add runtime spec-validation-before-binding requirement to Phase B.
3. Add Phase A cinematic parity test.
4. Add Phase D/E activation tasks and init smoke tests.
5. Add lifecycle/status handling for draft specs before Phase F.
6. Make copy_worker_result/render_wakeup dynamic or fail-closed before non-cinematic render stages are active.
7. Make Phase C template cleanup production-blocking.
8. Replace `pipeline_runtime.py || true` with conditional compile semantics.

## Go / No-Go

No-Go for production build as currently written.

Go condition: start with Phase A only after adding the Phase A parity test, then stop. Do not proceed to Phase B/C until explicit gate decision state and runtime spec validation are documented as hard requirements.
