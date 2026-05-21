# Universal Pipeline Runtime Planning Notes

Use this reference when the user asks to refactor Kinodel beyond the current cinematic route: music videos, serial/episode production, trend clones, timelapse, loop gifs, or a `create-pipeline` skill.

## Core direction

Kinodel should evolve from a hardcoded cinematic route into a universal pipeline runtime:

```text
pipeline registry
→ selected pipeline_spec.v1
→ producer state machine
→ stage contract binding
→ specialist agent handoff
→ artifact validation
→ render adapter/workflow_id
→ declared ReviewGate/checkpoint
→ final/chunk writer
```

The existing cinematic route remains the compatibility baseline. Do not break BriefGate, artifact-centric state, path-only handoffs, render-only-from-complete-request-artifacts, or hard stops at ReviewGates.

## Canonical MVP decisions

These decisions came from the Kinodel global patch architecture review and should be treated as canonical until explicitly changed by the user:

- MVP pipeline IDs: `cinematic.v1`, `serial_season.v1`, `serial_episode.v1`, `music_video.v1`, `renovation_timelapse.v1`.
- Avoid ambiguous `serial.v1` during MVP. If mentioned, treat it only as a future parent/orchestrator over `serial_season.v1` and `serial_episode.v1`.
- Pipeline specs declare gates, but p4/p7 remain compatibility aliases and hard STOP_AT_GATE. `checkpoint` is a semantic label, not permission to auto-approve.
- Pipeline specs live in the skill registry first and are copied into projects as frozen `pipeline_spec.json` for reproducible runs.
- `create-pipeline` drafts proposed specs and task maps only; it does not mutate live skills or execute production without approval.
- Muse is a planner/composer, not the runtime renderer. It writes `muse_output.json` and `music_request.json`; a render/audio worker produces `outputs/music.mp3` and `render_results/music_result.json` or equivalent.
- Legacy `final_chunk.json` remains valid for cinematic compatibility; `cinema_chunk` is the semantic successor.

## Two-level contracts

Keep contracts split so Producer does not become confused or overloaded.

### Pipeline-level contracts

Pipeline specs say what this pipeline needs:

- stage order / graph;
- goal IDs and compatibility aliases;
- owner_skill per stage;
- reads/writes artifacts;
- required agent capabilities;
- gate/checkpoint semantics;
- render profile or ComfyUI/fal workflow_id;
- final chunk type and chunk dependencies.

### Agent-level contracts

Agent skill references say what this agent can safely do:

- accepted input artifacts;
- output schemas;
- declared capabilities;
- forbidden behavior;
- compact handoff examples;
- validation rules.

### Runtime binding

Producer binds a pipeline stage to an agent capability and then validates the produced artifact:

```text
pipeline stage requires capability
→ agent contract declares capability
→ Producer creates compact handoff
→ agent writes artifact
→ validator checks schema/output
```

Source of truth for orchestration is the pipeline spec. Source of truth for capabilities is the agent contract.

## Pipeline spec MVP shape

Minimum fields for `kinodel.pipeline_spec.v1`:

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
  "stages": [
    {
      "goal": "p1_story",
      "type": "agent_stage",
      "owner_skill": "storytell-kinodel",
      "requires_capabilities": ["narrative_planning.cinematic.v1"],
      "reads": ["brief.json"],
      "writes": ["story.json"],
      "validator": "kinodel.story.v1"
    }
  ]
}
```

Stage types to support first: `agent_stage`, `render_stage`, `review_gate`, `montage_stage`, `chunk_write_stage`, and `context_gate` / `briefgate`.

## Implementation order

Use a smooth, compatibility-first upgrade path. Current canonical roadmap is Phase 0, A, B, C, D, E, F:

0. **Phase 0 — docs consistency cleanup:** before live skill changes, verify phase docs, sources, dependencies, MVP pipeline IDs, hard-gate language, and per-phase Test gates.
1. **Phase A — spec and validator only:** add `pipeline_spec.v1`, `pipelines/cinematic.v1.json`, and validator with no runtime behavior change. `cinematic.v1` is the lossless mirror of the current hardcoded p0-p11 route; `pipeline-kinodel` must remain universal architecture/law, not become a cinematic-only skill.
2. **Phase B — spec-aware Producer runtime:** let Producer/state_guard read specs through one `CompiledRoute` abstraction while preserving hardcoded cinematic fallback. Spec-based projects must not pass ReviewGates by artifact existence alone; explicit gate decision state is required.
3. **Phase C — layout/contracts/templates/PipelineChoiceGate:** add layout profiles, project-local frozen `pipeline_spec.json`, `producer_state.json`, active cinematic capability contracts, and canonical request templates. Producer selects or infers `pipeline_id` before BriefGate/init_project. Non-cinematic profiles remain planned/locked until their activation phases.
4. **Phase D — chunks and Serial MVP:** add chunk resolver, compact chunk handoffs, Wardrobe multi-anchor capability, `serial_season.v1`, and `serial_episode.v1` after cinematic compatibility tests pass.
5. **Phase E — music video:** add music/audio render adapter path, `music_video.v1`, Muse planner contracts, and Suno-compatible provider-neutral `music_request.json`. Muse remains planner-only; Render owns provider calls and `outputs/music.mp3`.
6. **Phase F — create-pipeline and renovation draft/test:** add `create-pipeline` spec drafting support and use it to draft/test `renovation_timelapse.v1`. Draft pipelines are not active production choices until separately approved/activated.

Every phase must end with its Test gate and a summary of changed files, tests, and explicit non-changes. Do not combine phases in one implementation pass.

## Pipeline selection before BriefGate

New projects use a lightweight `PipelineChoiceGate` before BriefGate/init_project so the project can be initialized with the correct `pipeline_id`, layout profile, project-local `pipeline_spec.json`, and `producer_state.json`.

Rules:

- This is a pre-brief selector, not a ReviewGate and not permission to bypass p4/p7.
- If the user clearly asks for a normal short cinematic/reels/video, default to `cinematic.v1`.
- If intent is ambiguous or clearly non-cinematic, ask which active pipeline to use.
- Only active pipelines may be selected for production. Planned/draft pipelines can be shown as locked/planned but must not initialize production projects.
- `renovation_timelapse.v1` is initially a Phase F create-pipeline draft/test and should not appear as an active production choice until separately approved.

## Current executable bottlenecks

When implementing the patch, inspect these live skill files first:

- `producer-kinodel/scripts/state_guard.py`: hardcoded `GOAL_ORDER`, `GOALS`, `EXPECTED_SCHEMAS`, `REQUEST_ARTIFACTS`, `RESULT_ARTIFACTS`, `REVIEW_GATES`, `infer_next_goal()`, and `build_handoff()`.
- `kinodel-project-layout/scripts/init_project.py`: fixed cinematic layout and stubs, no layout profiles or project-local spec copy.
- `render-kinodel/scripts/render.py`: stable entrypoint that dispatches to `render_worker.py`.
- `render-kinodel/scripts/render_worker.py`: supports provider-neutral `kind=t2i|i2i|i2v|flf2v` and adapter modules for fal.ai / ComfyUI.
- `render-kinodel/scripts/copy_worker_result.py` and `render_wakeup.py`: cinematic result/gate routing assumptions.
- `wardrobe-kinodel/SKILL.md`: currently says ONE composite anchor; multi-anchor must be an explicit capability upgrade.
- `pipeline-kinodel/templates/*`: some examples may be legacy bare arrays/jobs; canonical durable artifacts should be `kinodel.render_requests.v1` envelopes.

## Serial pipeline notes

MVP serial production is two explicit specs, not one ambiguous route.

### `serial_season.v1`

```text
p0_season_briefgate
→ p1_season_plan: season-kinodel writes season_plan.json + episodes/episode_N.json
→ p2_season_anchor_plan: wardrobe writes wardrobe_season_anchors_request.json
→ p3_season_anchor_render: render writes render_results/season_anchors_result.json
→ p4_season_checkpoint: ReviewGate/checkpoint, hard stop
→ p5_season_chunk: producer writes season_chunk.json after approval
```

### `serial_episode.v1`

```text
p0_episode_context_gate: validate season_chunk + selected episode + previous episode_chunk if needed
→ p1_story: episode-kinodel writes detailed story.json with 5 Acts / Harmon's Story Circle
→ p2_episode_anchor_plan: wardrobe writes wardrobe_episode_anchors_request.json, normally per_act
→ p3_episode_anchor_render: render writes render_results/episode_anchors_result.json
→ p4_episode_story_gate: hard checkpoint for story + act anchors
→ p5_storyboard_plan
→ p6_story_images_render
→ p7_story_images_gate
→ p8_video_plan
→ p9_video_render
→ p10_montage
→ p11_episode_chunk
```

Default MVP policy is strict sequential episode production. Future context should mean future episode blueprints/summaries, not future episode chunks. If a completed episode is edited, mark dependent later episodes `needs_continuity_review`.

Canonical serial anchor artifact names:

- Season: `wardrobe_season_anchors_request.json`, `render_results/season_anchors_result.json`.
- Episode: `wardrobe_episode_anchors_request.json`, `render_results/episode_anchors_result.json`.

## Checkpoints without breaking p4/p7

Use `checkpoint` as a semantic layer while preserving p4/p7 compatibility:

```json
{
  "gate_id": "p4",
  "gate_kind": "checkpoint",
  "gate_label": "Season Checkpoint",
  "resume_scope": "season",
  "stop": true
}
```

For serial production, p4 can approve the season plan plus one visual anchor/poster per episode. Later sessions resume from that checkpoint and the current episode status.

## Wardrobe generalization

Do not keep Wardrobe hardcoded to a single `main_frame`. Pipeline specs should be able to request visual anchor modes:

```json
{
  "capability": "visual_anchor_planning",
  "anchor_mode": "single | multi | per_episode | per_act | first_last | progression",
  "anchor_count": 4,
  "anchor_units": ["episode_01", "episode_02"],
  "input_chunks": ["avatar_chunk"],
  "writes": "wardrobe_request.json"
}
```

Examples:

- cinematic: `single`;
- serial season: `per_episode`;
- serial episode: `per_act`;
- renovation timelapse: `first_last` plus `progression`;
- music video: `main_style_frame` plus timed scene frames.

## Chunk taxonomy and migration

Relevant chunk types for flexible runtime:

- `avatar_chunk`: reusable identity/style/voice capsule for consistent characters;
- `music_chunk`: audio/lyrics/prompt/ALM tags for Muse retrieval;
- `cinema_chunk`: semantic successor to cinematic `final_chunk`;
- `season_chunk`: approved season bible/checkpoint for serial production;
- `episode_chunk`: continuity memory for completed serial episodes.

Status families:

- working artifacts: `pending | complete`;
- approved/final memory chunks: `draft | approved | completed | archived`.

Compatibility map:

- `final_chunk.json` + `kinodel.final_chunk.v1` = legacy cinematic output;
- `final_chunk.json` + `kinodel.chunk.cinema.v1` = new cinema chunk alias;
- `season_chunk.json` + `kinodel.season_chunk.v1` = serial season approval memory;
- `episode_chunks/episode_N_chunk.json` + `kinodel.episode_chunk.v1` = serial episode continuity memory.

Chunks should be referenced by ID/path and summarized into handoffs. Do not dump large media, raw logs, provider responses, or full histories into prompts.

## `create-pipeline` skill concept

`create-pipeline` designs new pipeline specs from an idea, reference video, reels trend, VLM/ALM analysis, or production brief. It does not execute production and does not mutate live skills automatically.

Expected output:

- proposed `kinodel.pipeline_spec.v1`;
- stage-by-stage agent task map;
- required chunks;
- required capabilities;
- render profiles/workflow IDs;
- open questions and missing agents/contracts.

## Pitfalls

- Do not let Producer invent stage graphs live; it executes approved specs.
- Do not put pipeline-specific relationships only in agent prose; keep them in pipeline specs.
- Do not put agent capability definitions only in pipeline specs; keep them in agent contracts.
- Do not bypass BriefGate/p4/p7 hard stops while generalizing runtime.
- Do not place provider payloads, queue IDs, retries, costs, or raw logs in durable artifacts.
- Do not implement Muse/Serial agents before the runtime can validate specs, capabilities, and chunks.
