# Serial Pipelines

Status: **Proposed after cinematic**

Serial production uses two explicit pipelines. Do not add a parent `serial.v1` orchestrator until operating the pair proves one is needed.

## `serial_season.v1`

```text
season_brief
-> brief_review                  [human]
-> resolve_character_and_canon
-> season_plan
-> season_plan_review            [human]
-> per_episode_visual_anchor_plan
-> season_visual_anchor_review   [human]
-> per_episode_anchor_image_plan
-> render_episode_anchor_candidates
-> season_anchor_review          [human: select]
-> promote_episode_anchors
-> craft_season_memory_draft
-> season_memory_review          [human]
-> promote_season_memory
-> complete
```

This graph stops after planning. It does not storyboard or produce full episodes.

## `serial_episode.v1`

```text
episode_brief
-> episode_brief_review          [human]
-> validate_continuity_context
-> episode_story
-> episode_story_review          [human]
-> per_act_visual_anchor_plan
-> act_visual_anchor_review      [human]
-> per_act_anchor_image_plan
-> render_act_anchor_candidates
-> act_anchor_review             [human: select]
-> promote_act_anchors
-> frame_plan
-> render_frame_candidates
-> frame_review                  [human: select]
-> promote_frames
-> motion_plan
-> render_clip_candidates
-> clip_review                  [human: select]
-> promote_clips
-> montage_plan
-> montage_execute
-> final_review                  [human]
-> craft_completed_episode_chunk
-> episode_memory_review         [human]
-> promote_episode_memory
-> complete
```

## Continuity Rules

- Season chunk must be approved.
- Target episode chunk must be planned/approved.
- Episode N greater than one requires the previous completed episode chunk.
- Future episode plans are context for setup, never facts.
- Production is sequential by default.
- Editing completed episode N requires an authorized new production/memory flow and produces a new reviewed chunk revision. Later executions select the revised continuity explicitly; existing executions retain their frozen selections.
- Whole-season canon changes create a new reviewed season revision. Ordinary supersede does not mutate or invalidate pinned selections in running executions. Rights withdrawal or unavailable mandatory pinned data blocks use regardless of pinning.

The initial context gate is machine validation. It becomes a human intervention only when required canon is missing or contradictory.

## Direct Context

- Season planning resolves exact selected Character chunks and prior-season canon only for an explicit continuation.
- Episode production selects the active approved Season, target planned Episode revision, previous completed Episode when required, and referenced Characters, then pins exact revisions for the execution. Preserve the planned Episode ref even after its logical subject's active binding becomes completed.
- Older episodes and inspiration are optional bounded projections; no search is required.
- Render adapts exact FramePlan/MotionPlan artifacts and assets; Montage execution consumes its validated plan and exact approved clips rather than creative-memory search.

## Revision Routes

| Gate | Critic returns to |
|---|---|
| season brief | Producer |
| season plan | Season |
| season visual-anchor plan | Wardrobe per-episode planning |
| season anchors | Storyboard anchor-image planning |
| season memory | Craft |
| episode brief | Producer |
| episode story | Episode |
| act visual-anchor plan | Wardrobe per-act planning |
| act anchors / frames | Storyboard for the corresponding image plan |
| clips | Filmmaker motion plan |
| final video | Montage agent |
| completed episode memory | Craft |

For Critic `ready`, the owner creates a new aggregate revision and follows its declared render/join, execution, or memory-review path back to the same gate. Critic `needs_input`/`out_of_scope` creates a new request for the same subject and explanation without calling the owner. Anchor-image review cannot rewrite approved Wardrobe direction or Season/Episode narrative. Changes outside that scope require a new execution with adjusted Brief/context; there is no general upstream rewind. Limits and actions follow [`../backend/pipeline.md`](../backend/pipeline.md#activation-and-repair).

## Proposed Stage Contracts

These are future pipeline contracts, not extra `foundation.v0` schemas. Each per-episode/per-act planner owns one aggregate artifact, not competing parallel writes to one slot. Local production refs use `current_execution`; shared canon uses `pinned_revision`.

| Pipeline stage / owner | Exact inputs | Output slot / contract |
|---|---|---|
| season brief / Producer | initial request, execution settings, selected canon | `brief`: `BriefV1`, own gate |
| canon resolution / adapter | approved Brief and selected shared revisions | frozen operation context, no creative artifact |
| season plan / Season | approved Brief and hydrated pinned canon | `season_plan`: `SeasonPlanV1`, own gate |
| per-episode direction / Wardrobe | approved Brief/SeasonPlan, character projections | `visual_anchor_plan`: `VisualAnchorPlanV1`, own gate |
| episode-anchor images / Storyboard | approved Brief/SeasonPlan/visual plan | `anchor_frame_plan`: validated `FramePlanV1` |
| anchor rendering / Render; promotion / service | exact frame plan; complete stage manifest and selection approval | `episode_anchors`: `RenderResultV1` |
| season memory / Craft | approved Brief/SeasonPlan/visual plan and selected episode anchors | `season_memory_draft`: `SeasonMemoryDraftV1`, own gate |
| season publication / service | approved draft, source/rights checks, expected revisions for every subject | separate Season and planned Episode chunks/bindings atomically in DB |
| episode brief / Producer | initial request/settings, selected continuity refs | `brief`: `BriefV1`, own gate |
| continuity validation / service | approved Brief, pinned Season/target plan/previous completed/Characters | validated prepared context or blocked, no creative artifact |
| episode story / Episode | approved Brief and hydrated validated continuity | `story`: episode-compatible `StoryV1`, own gate |
| per-act direction / Wardrobe | approved Brief/Story, relevant character/physical-state projections | `visual_anchor_plan`: `VisualAnchorPlanV1`, own gate |
| act-anchor images / Storyboard; Render | approved Brief/Story/visual plan | `anchor_frame_plan`: `FramePlanV1`; selected `act_anchors`: `RenderResultV1` |
| frames / Storyboard; Render | same inputs plus exact approved act anchors | `frame_plan`: `FramePlanV1`; selected `story_frames`: `RenderResultV1` |
| motion / Filmmaker; Render | approved Brief/Story/frames and current continuity | `motion_plan`: `MotionPlanV1`; selected `clips`: `RenderResultV1` |
| Montage / agent and executor | approved Brief/clips/audio when present | validated `montage_plan`; `final_video`: `MontageResultV1`, own gate |
| completed memory / Craft and promotion service | exact approved final sources, selected assets, supporting provenance | `episode_memory_draft`: completed `EpisodeChunkV1`, own gate then binding |

SeasonPlan assigns stable episode IDs; Story assigns stable act/shot IDs and order. Visual/image plans map every required episode or act anchor explicitly; frame and motion plans preserve shot mappings and terminal `flf2v` end-frame coverage. Join creates one stage-level candidate manifest across unit jobs, and a single gate selects every required unit before promotion. Technical retry keeps successful same-request units; revised creative aggregates rebuild all units initially. No full episode generation is hidden in the season graph.

Approval of a selected render/final result does not independently approve supporting FramePlan, MotionPlan, or MontagePlan. Season memory publication derives exactly the reviewed aggregate bodies, without another model call, and verifies every expected chunk-binding revision in one DB transaction. Planned and completed Episode revisions retain separate meaning and immutable history under one stable episode identity.
