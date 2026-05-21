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
5. Re-run `state_guard.py resume`; completion is only true when `next_goal` is null and `complete: true`.

## Pitfall
- Do not treat a finished `outputs/final.mp4` as the end of the pipeline. The project is not complete until `final_chunk.json` is written and validated.