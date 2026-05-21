# Kinodel /goal State Machine

Use this when running Kinodel with Hermes `/goal`. A goal is a checkpoint, not a vague intention. Producer may work inside one goal until its exit condition is true, then must either move to the next deterministic goal or stop at a user gate.

This file follows the canonical p0–p11 numbering used by `pipeline-kinodel`, `producer-kinodel/references/state-machine.md`, and `producer-kinodel/scripts/state_guard.py`.

## Canonical goals

```text
/goal p0_briefgate
  Input: user creative request.
  Do: confirm vibe + production format; after approval derive project_id and initialize v1 tree with brief.json + pending stubs.
  Exit: v1/brief.json exists, valid JSON, status=complete, project_id matches folder.
  Stop: yes before project init if anything was inferred; after explicit approval continue to p1.

/goal p1_story
  Input: brief.json.
  Do: write story.json directly or via storytell-kinodel.
  Exit: story.json status=complete, project_id match, scene_count == brief.shot_count.

/goal p2_main_frame_plan
  Input: brief.json + story.json.
  Do: write wardrobe_request.json with one t2i main_frame job.
  Exit: status=complete, jobs[0].kind=t2i, render_prompt non-empty.

/goal p3_main_frame_render
  Input: wardrobe_request.json.
  Do: launch render worker --stage images in background; on wake-up update render_results/main_frame_result.json.
  Exit: selected_outputs contains one current main_frame path+url.

/goal p4_story_main_gate
  Input: story.json + main_frame selected output.
  Do: show compact preview and ask A/B/C/D.
  Exit: user reply in a later turn.
  Stop: hard stop. No storyboard before explicit approval.

/goal p5_storyboard_plan
  Input: approved p4 + main_frame selected output URL.
  Do: write storyboard_requests.json with shot_count image jobs.
  Exit: status=complete, jobs non-empty, public URL input_media where external provider needs it.

/goal p6_story_images_render
  Input: storyboard_requests.json.
  Do: render --stage images; update render_results/story_frames_result.json.
  Exit: selected_outputs contains one selected image per shot.

/goal p7_story_images_gate
  Input: selected story images.
  Do: show compact preview and ask A/B/C/D.
  Exit: user reply in a later turn.
  Stop: hard stop. No video_requests before explicit approval.

/goal p8_video_plan
  Input: approved p7 + story image selected output URLs.
  Do: write video_requests.json. Default is flf2v transition clips between neighboring approved story frames; use i2v only when explicitly requested.
  Exit: status=complete, jobs non-empty, all input_media are public URLs.

/goal p9_video_render
  Input: video_requests.json.
  Do: render --stage videos; update render_results/shot_videos_result.json.
  Exit: selected_outputs contains current video clips.

/goal p10_montage
  Input: selected video clips.
  Do: assemble outputs/final.mp4.
  Exit: final.mp4 exists and ffprobe sees a video stream.

/goal p11_final_chunk
  Input: final media refs + story.
  Do: write final_chunk.json only with final story/hook/media/conclusion.
  Exit: valid final_chunk.json, no provider logs or prompt garbage.
```

## Rules

- Producer tracks exactly one current goal.
- A goal cannot consume a `pending` artifact as if it were complete.
- Render completion is an exit condition for render goals only; it is not approval for review goals.
- p4 and p7 are turn-boundary gates. The next goal starts only after the user's later message approves A.
- Free text while a review goal is pending means edit-fix notes unless it is a clear A/B/C/D.
