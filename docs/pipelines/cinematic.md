# Cinematic Pipeline

Status: **First full production pipeline, after `foundation.v0`**

`cinematic.v1` is the reference graph. Build it explicitly before extracting a generic compiler.

```text
brief_draft
-> brief_review                 [human]
-> story
-> story_review                 [human]
-> visual_anchor_plan
-> visual_anchor_review         [human]
-> main_frame_plan
-> render_main_frame_candidates
-> main_frame_review            [human: select]
-> promote_main_frame
-> frame_plan
-> render_frame_candidates
-> frame_review                 [human: select]
-> promote_frames
-> motion_plan
-> render_clip_candidates
-> clip_review                  [human: select]
-> promote_clips
-> montage_plan
-> montage_execute
-> final_review                 [human]
-> craft_cinema_memory
-> cinema_memory_review         [human]
-> promote_cinema_memory
-> complete
```

## Stage Ownership

| Stage | Owner | Output |
|---|---|---|
| brief draft | Producer | `BriefV1` candidate |
| brief review | human gate | `ReviewDecision` |
| story | Storytell | `StoryV1` |
| story review | human gate | exact `StoryV1` decision |
| visual anchor | Wardrobe | `VisualAnchorPlanV1` |
| visual-anchor review | human gate | exact `VisualAnchorPlanV1` decision |
| main-frame image plan | Storyboard | `FramePlanV1` for the continuity anchor |
| candidate rendering | Render service | durable candidate set, no artifact binding |
| media review | human gate | exact candidate selection |
| media promotion | Render service | `RenderResultV1` with approved `AssetRef`s |
| frame plan | Storyboard | `FramePlanV1` |
| motion plan | Filmmaker | `MotionPlanV1` |
| montage plan | Montage agent | `MontagePlanV1` |
| assembly | Montage execution service | `MontageResultV1` |
| reusable memory | Craft | `CinemaChunkV1` |
| memory review | human gate | exact reusable-memory decision |
| memory promotion | deterministic service | approved active `CinemaChunkV1` revision |

## Revision Routes

- brief edits return through Critic to Producer;
- story edits return through Critic to Storytell and make every downstream binding stale;
- visual-direction edits return through Critic to Wardrobe's `visual_anchor_plan` and its own review;
- main-frame candidate edits return through Critic to Storyboard's `main_frame_plan`;
- storyboard-frame candidate edits return through Critic to Storyboard's `frame_plan`;
- clip candidate edits return through Critic to Filmmaker's `motion_plan`;
- final edits return through Critic to Montage, which creates a new plan for the execution service;
- cinema-memory edits return through Critic to Craft;
- every revised output returns to the same gate as a new exact subject revision.

Each gate has one graph-declared revision stage. Critic refines feedback but never chooses a target. Stale bindings remain visible for history and preview but cannot satisfy a downstream precondition. Staleness is derived from input digests, not manually toggled file statuses.

These routes run only for Critic `ready`. `needs_input`/`out_of_scope` creates a new request for the same subject with an explanation, without calling its owner. An anchor-media gate cannot rewrite Wardrobe's approved direction; a clip gate cannot replace approved frames; final review cannot regenerate clips. Such upstream changes require a new execution with adjusted Brief/context, not automatic rewind. Limits and clarification semantics follow [`../backend/pipeline.md`](../backend/pipeline.md#activation-and-repair).

## Exact Dependencies

The following slots and stage contracts are the full production design, not completed executable schemas. All local production dependencies use `current_execution`; external selected canon/resources use `pinned_revision`. Required approvals are checked separately from transitive freshness.

| Owner stage | Reads | Writes / approval requirement |
|---|---|---|
| `brief_draft` | `initial_request`, selected refs and frozen execution settings | `brief`: `BriefV1`, brief gate |
| `story` | approved `brief`, prepared narrative context | `story`: `StoryV1`, story gate |
| `visual_anchor_plan` | approved `brief`, `story`, selected visual canon | `visual_anchor_plan`: `VisualAnchorPlanV1`, visual gate |
| `main_frame_plan` | approved `brief`, `story`, `visual_anchor_plan` | `main_frame_plan`: validated `FramePlanV1` |
| `promote_main_frame` | current main-frame plan, joined candidates, exact selection approval | `main_frame`: `RenderResultV1` |
| `frame_plan` | approved `brief`, `story`, `visual_anchor_plan`, promoted approved `main_frame` | `frame_plan`: validated `FramePlanV1` |
| `promote_frames` | current frame plan, joined candidates, exact selection approval | `story_frames`: `RenderResultV1` |
| `motion_plan` | approved `brief`, `story`, promoted approved `story_frames` | `motion_plan`: validated `MotionPlanV1` |
| `promote_clips` | current motion plan, joined candidates, exact selection approval | `clips`: `RenderResultV1` |
| `montage_plan` | approved `brief`, promoted approved `clips`, approved audio if supplied | `montage_plan`: validated `MontagePlanV1` |
| `montage_execute` | current montage plan and its exact clip/audio inputs | `final_video`: `MontageResultV1`, final gate |
| `craft_cinema_memory` | approved Brief/Story/visual direction, selected media, approved final result, supporting provenance | `cinema_memory_draft`: `CinemaChunkV1` candidate, memory gate |
| `promote_cinema_memory` | exact memory approval, valid sources/rights, expected chunk-binding revision | active approved Cinema chunk binding |

Each `render_*_candidates` stage deterministically adapts its corresponding plan, fans out unit jobs, and joins one immutable stage-level manifest. It writes no artifact slot. Repairs traverse that render/join path before revisiting the selection gate. Main/frame/motion/montage plans are validated supporting inputs, not independently human-approved artifacts. Promotion transfers the exact selection approval to its recorded selected result, not to all upstream plans.

## Unit Contracts

The main frame is the approved visual continuity anchor, not necessarily the first story shot. Storyboard receives its exact promoted revision and declares what each later frame preserves or changes.

Story defines stable shot IDs and order; FramePlan maps declared frame units to shots; MotionPlan maps each ordered clip unit to exact promoted frame IDs. `i2v` requires a start frame. `flf2v` requires explicit start/end frames for every clip, including the terminal clip; the pipeline must declare any additional terminal frame unit before rendering. Do not infer adjacency, wrap the final clip to the first frame, or silently reduce clip count. Counts, durations, aspect ratio, and timing must satisfy Brief and workflow capabilities or block before provider submission.

Same-request technical retry retains successful units and reconciles uncertain jobs. A creative plan revision creates new downstream activations and rebuilds the whole render aggregate initially. Join/promotion require complete ordered coverage. Selective cross-revision reuse is deferred.

## First Slice

Implement a separate reduced `foundation.v0` graph with brief and story review first. It is a runtime proving ground, not a shortened execution of `cinematic.v1`. Add the full visual/render topology after restart, stale-review, and idempotency tests pass.
