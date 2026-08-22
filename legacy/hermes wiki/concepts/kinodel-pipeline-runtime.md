---
title: Kinodel Pipeline Runtime — patch plan for universal production execution
created: 2026-05-17
updated: 2026-05-17
type: concept
tags: [kinodel, agent-architecture, orchestrator, pipeline, workflow, production, patch]
sources: [current-chat:kinodel-universal-runtime-serial-pipeline]
confidence: medium
contested: false
contradictions: []
---

# Kinodel Pipeline Runtime — patch plan for universal production execution

`kinodel-pipeline-runtime` — planning page for превращения текущего [[pipeline-kinodel]] из cinematic-only route в universal runtime, который исполняет approved `kinodel.pipeline_spec.v1` specs: `cinematic.v1`, [[music-video-pipeline]], [[serial-pipeline]], timelapse, loop gif, reels trend clone.

## Canonical MVP decisions after patch review

- Use spec-declared gates, but keep p4/p7 as compatibility aliases and hard STOP_AT_GATE. `checkpoint` is semantic label, not auto-approval.
- MVP pipeline IDs are `cinematic.v1`, `serial_season.v1`, `serial_episode.v1`, `music_video.v1`, and `renovation_timelapse.v1`.
- Avoid ambiguous `serial.v1` during MVP; a parent serial orchestrator can be added later.
- Serial season anchors use `wardrobe_season_anchors_request.json` and `render_results/season_anchors_result.json`.
- Serial episode anchors use `wardrobe_episode_anchors_request.json` and `render_results/episode_anchors_result.json`.
- Muse plans music and writes request artifacts; render/audio workers generate `music.mp3`.
- Legacy `final_chunk.json` remains valid for cinematic compatibility; [[cinema-chunk]] is the semantic successor.

## Target architecture

```text
pipeline registry
  → selected pipeline_spec.v1
  → producer runtime state machine
  → stage contract binding
  → specialist agent handoff
  → artifact validator
  → render adapter / workflow_id
  → declared ReviewGate/checkpoint
  → final chunk writer
```

Important: this patch must preserve current Kinodel laws: artifact-centric state, path-only handoffs, render only from complete request artifacts, and hard stops at gates/checkpoints.

## Compatibility guardrail: compiled route as single source of truth

Avoid adding parallel dynamic versions of the old cinematic maps (`GOAL_ORDER`, `GOALS`, `EXPECTED_SCHEMAS`, `REQUEST_ARTIFACTS`, `RESULT_ARTIFACTS`, `REVIEW_GATES`, render destination maps, wake-up next actions, and layout stubs). The runtime should compile `kinodel.pipeline_spec.v1` into one `CompiledRoute` and make all helpers read from it.

`CompiledRoute` should expose:

- ordered stages / graph edges;
- stage descriptors by `goal`;
- artifact validators by artifact class and schema;
- gate descriptors including `goal`, `gate_alias`, `gate_kind`, `stop`, preview refs, and resume scope;
- render descriptors including request artifact, result artifact, modality, adapter profile, and next action;
- handoff descriptors including owner_skill, reads, writes, and required capabilities;
- layout descriptors and chunk dependencies;
- final chunk descriptor.

Hardcoded cinematic maps may remain only as legacy fallback while `cinematic.v1` parity tests are green.

## Gate state compatibility

Spec-declared gates cannot rely only on “preview artifact exists and next artifact missing”. New spec-based projects need explicit gate decision state, either in `producer_state.json.gate_decisions` or a small gate decision artifact. Minimum fields: `goal`, `gate_alias`, `decision`, `approved_at`, `notes_ref`. Old cinematic projects without this state may keep the existing p4/p7 heuristic as fallback.

## Core design decision: contracts in two places

Чтобы Producer не запутался, contracts should be split:

### 1. Pipeline contracts

Live in pipeline specs or `contracts/` next to each pipeline. They say what THIS pipeline needs:

- stage order / graph;
- goal IDs;
- owner_skill per stage;
- reads/writes artifacts;
- required agent capabilities;
- gate/checkpoint semantics;
- render profile or workflow_id;
- final chunk type.

### 2. Agent contracts

Live inside each agent skill/reference. They say what THIS agent can safely do:

- accepted input artifacts;
- output schemas;
- declared capabilities;
- forbidden behavior;
- examples of compact handoff;
- validation rules.

### 3. Runtime binding

Producer binds them by ID and validates compatibility:

```text
pipeline stage requires: multi_anchor_frames
wardrobe contract declares: multi_anchor_frames
stage writes: wardrobe_episode_anchors_request.json
validator checks: schema + jobs + count + episode IDs
```

This keeps pipeline-specific relationships out of generic agent prose, while still letting each pipeline customize tasks for the same agents.

## Pipeline spec skeleton

```json
{
  "schema": "kinodel.pipeline_spec.v1",
  "pipeline_id": "serial_season.v1",
  "display_name": "Serial Pipeline",
  "final_chunk_type": "season_chunk",
  "project_layout_profile": "serial_season",
  "stages": [
    {
      "goal": "p1_season_plan",
      "type": "agent_stage",
      "owner_skill": "season-kinodel",
      "requires_capabilities": ["season_arc", "episode_breakdown"],
      "reads": ["brief.json", "references/avatar_chunks.json"],
      "writes": ["season_plan.json", "episodes/*.json"],
      "validator": "season_plan.v1"
    },
    {
      "goal": "p4_season_checkpoint",
      "type": "review_gate",
      "gate_alias": "p4",
      "gate_kind": "checkpoint",
      "label": "Season Checkpoint",
      "previews": ["season_plan.json", "render_results/season_anchors_result.json"],
      "resume_scope": "season"
    }
  ]
}
```

## Required runtime changes

1. Move cinematic p0–p11 route into a `cinematic.v1` pipeline spec while keeping compatibility aliases.
2. Teach `state_guard.py next-goal` to read `producer_state.json.pipeline_id` and stage cursor from spec.
3. Teach `handoff` to derive `owner_skill`, `reads`, `writes`, and required capabilities from spec.
4. Add artifact validators keyed by schema, not by hardcoded filename only.
5. Add project layout profiles: `cinematic`, `serial_season`, `serial_episode`, `music_video`, and `renovation_timelapse` (`season` may exist only as a backward-compatible alias for `serial_season`).
6. Add checkpoint model: p4/p7 aliases remain, but each gate has `gate_kind`, `label`, `resume_scope`.
7. Add render profiles/workflow IDs, so [[agent-render-kinodel]] can route fal.ai vs ComfyUI without planner payload leakage.
8. Add chunk resolver: pipeline declares `chunk_dependencies`; runtime mounts refs into `references/*.json`.

## Wardrobe patch requirement

Current Wardrobe is effectively one-main-frame oriented. Runtime should not force that assumption. `wardrobe-kinodel` should accept task contracts like:

```json
{
  "capability": "visual_anchor_planning",
  "anchor_mode": "single | multi | per_episode | first_last | progression",
  "anchor_count": 4,
  "anchor_units": ["episode_01", "episode_02", "episode_03", "episode_04"],
  "input_chunks": ["avatar_chunk"],
  "writes": "wardrobe_request.json"
}
```

Then cinematic uses `single`, serial uses `per_episode`, renovation timelapse uses `first_last + progression`, music video may use `main_style_frame + timed_scene_frames`.

## Checkpoint semantics

Use `checkpoint` as semantic label, but do not break p4/p7 tooling immediately.

```text
p4 = first major approval checkpoint
p7 = second major visual approval checkpoint
custom gate IDs may exist later, but MVP keeps aliases
```

For serial: p4 season checkpoint approves season_plan + episode anchors. Per-episode sessions resume from that checkpoint and current episode status.

## Implementation phases

Canonical executable phase docs live under [[kinodel-patch-implementation-plan]]. Each phase file starts with a copy-paste GPT agent prompt and must be executed in order.

### Phase A — Spec and validator only

File: [[kinodel-patch-phase-a-spec-validator]]

Add spec schema and validate current cinematic route. No behavior change.

### Phase B — Producer state reads spec

File: [[kinodel-patch-phase-b-producer-runtime]]

Keep hardcoded fallback, but let runtime load `cinematic.v1` spec and produce the same next goals.

### Phase C — Contract binding / layout / templates

File: [[kinodel-patch-phase-c-layout-contracts-templates]]

Introduce safe layout profiles, project-local spec/state, capability registry, and canonical render request templates.

### Phase D — Serial MVP / two-stage serial runtime

File: [[kinodel-patch-phase-d-serial-chunks]]

Implement chunk resolver plus Stage 1 season development ending in [[season-chunk]], then Stage 2 episode production where [[agent-episode-kinodel]] occupies p1_story and writes detailed `story.json` for one episode. Support `season_chunk + selected episode + previous episode_chunk` as p0 context instead of a fresh user brief.

### Phase E — Music video / workflow adapters / create-pipeline

File: [[kinodel-patch-phase-e-music-create-pipeline]]

Add workflow_id render profiles, timed image/video requests, music-video MVP, and create-pipeline spec drafting.

## См. также

- [[create-pipeline]] — skill that drafts new specs.
- [[kinodel-flexible-pipeline-patch]] — broader proposal.
- [[serial-pipeline]], [[season-chunk]], [[episode-chunk]], [[agent-season-kinodel]], [[agent-episode-kinodel]] — serial-specific design.
