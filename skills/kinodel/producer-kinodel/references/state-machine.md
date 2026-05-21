# Producer State Machine

Producer is a deterministic state machine. It carries paths and gate state, not full artifacts.

## Core loop

```text
current_goal
→ validate required artifact paths
→ create or update exactly one owned artifact
→ validate the produced artifact
→ if render: launch packaged render worker
→ if gate: show preview refs + A/B/C/D, stop the turn
→ else advance to the next goal
```

## Hard stops

- BriefGate: ask/confirm brief before creating the project directory.
- p4 ReviewGate: story + main_frame preview; stop until user replies A/B/C/D.
- p7 ReviewGate: story images preview; stop until user replies A/B/C/D.

Render completion never approves a gate.

## Goal ownership

| Goal | Owner | Reads | Writes | Exit condition |
| --- | --- | --- | --- | --- |
| p0_briefgate | producer | user request | brief.json after approval | user confirmed brief |
| p1_story | storytell | brief.json | story.json | status=complete |
| p2_main_frame_plan | wardrobe | brief.json, story.json | wardrobe_request.json | complete + jobs |
| p3_main_frame_render | render | wardrobe_request.json | render_results/main_frame_result.json | selected_outputs |
| p4_story_main_gate | producer | story.json, main frame refs | optional qc | user A/B/C/D, then stop |
| p5_storyboard_plan | storyboard | brief, story, main frame selected_outputs | storyboard_requests.json | complete + jobs |
| p6_story_images_render | render | storyboard_requests.json | render_results/story_frames_result.json | selected_outputs |
| p7_story_images_gate | producer | story image refs | optional qc | user A/B/C/D, then stop |
| p8_video_plan | filmmaker | brief, story, story frame selected_outputs | video_requests.json | complete + jobs |
| p9_video_render | render | video_requests.json | render_results/shot_videos_result.json | selected_outputs |
| p10_montage | montage | selected video refs | outputs/final.mp4 | file exists, size > 0 |
| p11_final_chunk | producer | final selected refs | final_chunk.json | minimal final memory |

## Resume rule

Resume only from project_id + validated artifacts. Never resume by vibe or by scanning newest files in `outputs/`.
