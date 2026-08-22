# Serial Pipelines

Status: **Proposed after cinematic**

Serial production uses two explicit pipelines. Do not add a parent `serial.v1` orchestrator until operating the pair proves one is needed.

## `serial_season.v1`

```text
season_brief
-> brief_review                  [human]
-> resolve_character_and_canon
-> season_plan
-> per_episode_anchor_plan
-> render_episode_anchors
-> season_review                 [human]
-> craft_approved_season_chunk
-> craft_planned_episode_chunks
-> complete
```

This graph stops after planning. It does not storyboard or produce full episodes.

## `serial_episode.v1`

```text
validate_continuity_context
-> episode_story
-> per_act_anchor_plan
-> render_act_anchors
-> story_anchor_review           [human]
-> frame_plan
-> render_frames
-> frame_review                  [human]
-> motion_plan
-> render_clips
-> montage
-> final_review                  [human]
-> craft_completed_episode_chunk
-> complete
```

## Continuity Rules

- Season chunk must be approved.
- Target episode chunk must be planned/approved.
- Episode N greater than one requires the previous completed episode chunk.
- Future episode plans are context for setup, never facts.
- Production is sequential by default.
- Editing completed episode N produces a new chunk revision and flags later active episodes for continuity review.
- Whole-season canon changes create a new season revision and invalidate affected context selections through provenance.

The initial context gate is machine validation. It becomes a human intervention only when required canon is missing or contradictory.
