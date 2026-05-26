# Final chunk completion recipe

Use this when a Kinodel project has finished p10_montage but still needs the durable completion artifact.

## When to apply
- `state_guard.py resume` returns `next_goal: p11_final_chunk` or `reason: final_chunk.json missing or invalid`.
- `outputs/final.mp4` already exists and validates.

## Steps
1. Read `render_results/shot_videos_result.json` and use its `selected_outputs` / ordered clip refs.
2. Write `final_chunk.json` with:
   - `schema: kinodel.final_chunk.v1`
   - `project_id`
   - concise `story`, `hook`, `conclusion`
   - `main_frame.path`
   - all approved `story_images`
   - all approved `video_clips`
   - `final_video.path: outputs/final.mp4`
3. Do not include provider payloads, logs, retries, or queue metadata.
4. Validate `final_chunk.json`.
5. Re-run `state_guard.py resume`; after `final_chunk.json`, the next goal should be `p12_final_gate`, not Craft or complete.
6. Show the final video (`MEDIA:.../outputs/final.mp4`) and a concise final_chunk summary at p12, then stop for A/B/C/D.
7. Only after p12 approval may Producer delegate `p13_cinema_chunk` to Craft; project completion is only true when `next_goal` is null and `complete: true`.

## Pitfall
- Do not treat a finished `outputs/final.mp4` as the end of the pipeline. The project is not complete until `final_chunk.json` is written, p12 final gate is approved, and `chunks/cinema_chunk.json` is crafted/validated.