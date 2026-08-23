# Music Video Pipeline

Status: **Proposed after cinematic**

Music is the temporal spine. Muse replaces Storytell for the primary creative structure; Storyboard and Filmmaker operate on timed units.

```text
music_video_brief
-> brief_review                  [human]
-> resolve_selected_inspiration
-> muse
-> generate_music
-> analyze_timing
-> visual_anchor_plan
-> render_style_frame
-> song_style_review             [human: select song + concept approval]
-> timed_frame_plan
-> render_frames
-> timed_motion_plan
-> visual_review                 [human: approve storyboard]
-> render_clips
-> audio_master_montage
-> final_review                  [human: approve video clips]
-> craft_music_video_memory
-> complete
```

## Decisions

- Muse writes one provider-neutral `MusicPlanV1` containing the audio request; Render owns Suno/other provider mapping.
- Provider candidates are selected explicitly and recorded in the audio result artifact.
- ALM/timing analysis is a service result, not an autonomous orchestrator.
- MVP timing uses sections and lyric windows; beat-accurate editing waits for demonstrated need.
- Montage treats the selected song as timeline master.
- Final reusable memory is `MusicVideoChunkV1`; generated songs become general `MusicChunkV1` only through a separate approved action.

## Rights

Inspiration context must declare permitted abstractions and forbidden imitation. Muse may use mood, energy, structure, instrumentation, and delivery, but must not copy lyrics, melody, voice, or artist identity.
