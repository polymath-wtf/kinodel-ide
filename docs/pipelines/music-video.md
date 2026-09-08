# Music Video Pipeline

Status: **Proposed after cinematic**

Music is the temporal spine. Muse replaces Storytell for the primary creative structure; Storyboard and Filmmaker operate on timed units.

```text
music_video_brief
-> brief_review                  [human]
-> resolve_selected_inspiration
-> muse
-> music_plan_review              [human]
-> generate_music_candidates
-> song_review                    [human: select]
-> promote_song
-> analyze_timing
-> visual_anchor_plan
-> visual_anchor_review            [human]
-> style_frame_plan
-> render_style_frame_candidates
-> style_frame_review             [human: select]
-> promote_style_frame
-> timed_frame_plan
-> render_frame_candidates
-> frame_review                   [human: select]
-> promote_frames
-> timed_motion_plan
-> render_clip_candidates
-> clip_review                  [human: select]
-> promote_clips
-> montage_plan
-> audio_master_montage
-> final_review                  [human: approve final video]
-> craft_music_video_memory
-> music_video_memory_review     [human]
-> promote_music_video_memory
-> complete
```

## Decisions

- Muse writes one provider-neutral `MusicPlanV1` containing the audio request; Render owns Suno/other provider mapping.
- Provider candidates are selected explicitly and recorded in the audio result artifact.
- ALM/timing analysis is a service result, not an autonomous orchestrator.
- The analysis service owns `timing_map`: a validated `AudioAnalysisV1` with an exact-song timing projection. This is not a second creative story artifact or an independently approved plan.
- MVP timing uses sections and lyric windows; beat-accurate editing waits for demonstrated need.
- Montage agent treats the selected song as timeline master; the execution service validates its plan and runs ffmpeg.
- Final reusable memory is `MusicVideoChunkV1`; generated songs become general `MusicChunkV1` only through a separate approved action.

## Rights

Inspiration context must declare permitted abstractions and forbidden imitation. Muse may use mood, energy, structure, instrumentation, and delivery, but must not copy lyrics, melody, voice, or artist identity.

Selected `MusicChunkV1`, Character, or Cinema inspiration is resolved directly from Brief/user mentions. Once a song is selected, downstream stages use its exact promoted artifact and timing map rather than reinjecting the inspiration chunk. Search is not required.

## Revision Routes

| Gate | Critic returns to |
|---|---|
| brief | Producer |
| music plan / song candidates | Muse |
| visual-anchor plan | Wardrobe |
| style frame / storyboard frames | Storyboard for the corresponding image plan |
| clips | Filmmaker motion plan |
| final video | Montage agent |
| music-video memory | Craft |

Every Critic `ready` revision follows the declared repair path back to the same gate with a new exact subject. A song revision must traverse `muse -> music_plan_review -> generate_music_candidates -> song_review`: approval of the old MusicPlan cannot authorize generation from a revised plan. This is an explicit repair path, not a general upstream rewind. Image/clip revisions rerun their corresponding planner, render jobs, and join; final revision reruns Montage planning and execution; memory revision reruns Craft.

Critic `needs_input`/`out_of_scope` returns a new request for the unchanged subject without calling its owner. Style-media review cannot change approved visual direction; final review cannot replace the approved song. Outside declared repair scope, start a new execution with adjusted Brief/context. Shared limits and actions follow [`../backend/pipeline.md`](../backend/pipeline.md#activation-and-repair).

## Proposed Stage Contracts

These fields refine the future pipeline, not the `foundation.v0` implementation scope. Local inputs use `current_execution` dependencies; selected inspiration/canon stays pinned. No fabricated `StoryV1` is required for music production.

| Stage / owner | Exact inputs | Output slot / contract |
|---|---|---|
| music brief / Producer | initial request, selected refs, execution settings | `brief`: approved `BriefV1` |
| resolve inspiration / context adapter | approved Brief mentions | frozen operation context, no creative artifact |
| `muse` / Muse | approved Brief, rights-safe hydrated context | `music_plan`: `MusicPlanV1`, own gate |
| generate / Render; promote / service | approved MusicPlan; complete joined song candidates and selection | `song`: `RenderResultV1` |
| `analyze_timing` / analysis service | exact promoted approved song | `timing_map`: `AudioAnalysisV1` |
| visual direction / Wardrobe | approved Brief/MusicPlan/song, validated timing map, visual context | `visual_anchor_plan`: `VisualAnchorPlanV1`, own gate |
| style image / Storyboard; promote / Render | same spine plus approved visual plan | `style_frame_plan`: `FramePlanV1`; selected `style_frame`: `RenderResultV1` |
| timed frames / Storyboard; promote / Render | exact spine/timing, approved visual plan/style frame | `frame_plan`: `FramePlanV1`; selected `story_frames`: `RenderResultV1` |
| timed motion / Filmmaker; promote / Render | exact spine/timing and approved frames | `motion_plan`: `MotionPlanV1`; selected `clips`: `RenderResultV1` |
| Montage plan / agent; audio master / executor | approved Brief/song/clips and validated timing map | `montage_plan`: `MontagePlanV1`; `final_video`: `MontageResultV1`, final gate |
| Craft / memory promotion service | approved final sources, selected assets, supporting timing/montage provenance | `music_video_memory_draft`: `MusicVideoChunkV1`; own gate then chunk binding |

Render reads existing MusicPlan/FramePlan/MotionPlan through deterministic adapters, joins one immutable stage manifest per selection gate, and promotes exact approved selections. Supporting frame/motion/montage plans and timing analysis require validation, not implied independent approval. Craft's memory gate reviews any new reusable claims.

Timed units have stable IDs, explicit section/lyric-window boundaries, and declared order within the selected song's measured duration. Frame/clip mappings, terminal `flf2v` end-frame coverage, and montage duration must agree with that timing; no guessed beat precision or silent truncation. Technical retries preserve same-request successes; creative aggregate revisions rebuild all units initially. Song changes invalidate timing and all visual/montage descendants transitively.
