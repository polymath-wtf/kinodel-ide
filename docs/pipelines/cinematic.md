# Cinematic Pipeline

Status: **First full production pipeline, after `foundation.v0`**

`cinematic.v1` is the reference graph. Build it explicitly before extracting a generic compiler.

```text
brief_draft
-> brief_review                 [human]
-> story
-> visual_anchor_plan
-> render_main_frame
-> story_anchor_review          [human]
-> frame_plan
-> render_frames
-> frame_review                 [human]
-> motion_plan
-> render_clips
-> montage
-> final_review                 [human]
-> craft_cinema_memory
-> complete
```

## Stage Ownership

| Stage | Owner | Output |
|---|---|---|
| brief draft | Producer | `BriefV1` candidate |
| brief review | human gate | `ReviewDecision` |
| story | Storytell | `StoryV1` |
| visual anchor | Wardrobe | `VisualAnchorPlanV1` |
| main frame render | Render service | `RenderResultV1` |
| frame plan | Storyboard | `FramePlanV1` |
| frame render | Render service | `RenderResultV1` |
| motion plan | Filmmaker | `MotionPlanV1` |
| clip render | Render service | `RenderResultV1` |
| assembly | Montage service | `MontageResultV1` |
| reusable memory | Craft | `CinemaChunkV1` |

## Revision Routes

- story feedback uses target `storytell` and makes every downstream binding stale;
- anchor feedback uses target `wardrobe` and makes anchor render onward stale;
- frame feedback uses the gate-declared target `storyboard` or `render`;
- motion feedback uses the gate-declared target `filmmaker` or `render`;
- final feedback uses one target from the gate's authored `RevisionTarget` enum.

Producer/Critic may propose a target, but runtime validation maps only the finite enum to graph edges. Stale bindings remain visible for history and preview but cannot satisfy a downstream precondition. Staleness is derived from input digests, not manually toggled file statuses.

## First Slice

Implement a separate reduced `foundation.v0` graph with brief and story review first. It is a runtime proving ground, not a shortened execution of `cinematic.v1`. Add the full visual/render topology after restart, stale-review, and idempotency tests pass.
