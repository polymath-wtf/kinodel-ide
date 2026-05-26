# Universal runtime patch audit checklist

Use this reference before upgrading Kinodel from the hardcoded cinematic p0-p11 route to `kinodel.pipeline_spec.v1` universal runtime. It captures compatibility hazards found during pre-upgrade audit of the flexible-pipeline patch docs and live Kinodel scripts.

## Audit scope

Check the canonical implementation plan first, then linked patch pages for flexible runtime, serial, music-video, create-pipeline, chunks, and new Muse/Season/Episode agents. Inspect live executable hotspots before patching:

- `producer-kinodel/scripts/state_guard.py`
- `kinodel-project-layout/scripts/init_project.py`
- duplicate `pipeline-kinodel/scripts/init_project.py`
- `render-kinodel/scripts/render.py`
- `render-kinodel/scripts/render_worker.py`
- `render-kinodel/scripts/copy_worker_result.py`
- `render-kinodel/scripts/render_wakeup.py`
- `pipeline-kinodel/templates/*.json`

## Blocking compatibility hazards

1. Gate approval state must become explicit for spec-based projects.
   Current cinematic `state_guard.py` infers p4/p7 from “preview result complete and next artifact missing”. That is not enough for serial/music gates because the runtime can loop forever at a gate after approval. Add project-local gate decisions or stage cursor for spec-based projects while preserving legacy heuristic fallback.

2. Avoid adding more parallel hardcoded maps.
   The simplification cascade is: everything is a special case of a compiled pipeline route. Generate a `CompiledRoute` from `pipeline_spec.v1` and use it for next-goal, handoff, artifact validation, render promotion, wakeup next actions, layout stubs, gates, chunks, and final chunk descriptors.

3. Validators must separate artifact status families.
   Working artifacts use `pending|complete`; approved/final chunks use `draft|approved|completed|archived`. Do not reject `season_chunk.status=approved` or `episode_chunk.status=completed` by reusing cinematic `status == complete` checks. Accept legacy `kinodel.final_chunk.v1` and new `kinodel.chunk.cinema.v1` as cinematic aliases.

4. Render result promotion and wakeup are still cinematic-only.
   `copy_worker_result.py` and `render_wakeup.py` must derive destination result files and next actions from render stage descriptors in the pipeline spec. Keep `main_frame/story_frames/shot_videos` maps only as legacy fallback.

5. `copy_worker_result.py` must accept the native `render_worker.py` result shape.
   `render_worker.py` writes top-level `summary` and `jobs`; outputs commonly live under `summary.outputs` or done jobs, not only top-level `selected_outputs/outputs/results`. Promotion should normalize those shapes before writing durable `render_results/*.json`.

6. Capability IDs need one registry before contracts.
   Patch docs have mixed names such as `multi_anchor_frames`, `season_arc`, `episode_breakdown`, and `visual_anchor_planning.multi.v1`. Create one canonical machine-readable capability ID list and make pipeline specs use only registry IDs.

7. Serial goal names must distinguish goal from anchor mode.
   Use canonical goals such as `p2_episode_anchor_plan` / `p3_episode_anchor_render`; express act-level behavior as `anchor_mode: per_act`, not as alternate goal names like `p2_act_anchor_plan`.

8. Muse must remain a planner, not a provider runtime worker.
   Docs may contain old wording like “Muse generates music.mp3”. Canonical boundary: Muse writes `muse_output.json` and `music_request.json`; render/audio adapter writes `outputs/music.mp3` and `music_result.json`.

9. Music/video pipelines require render modality support.
   Current render CLI supports only `images|videos`, and fal worker supports only `t2i|i2i|i2v|flf2v`. Do not activate `music_video.v1` until audio/music request schemas and render adapter modality routing exist.

10. Layout/profile names and duplicate initializers must be normalized.
    Prefer profiles `cinematic`, `serial_season`, `serial_episode`, `music_video`, `renovation_timelapse`. Make `kinodel-project-layout` the owner of initialization; any duplicate initializer in `pipeline-kinodel` should forward or be deprecated.

11. Durable templates must not teach legacy shapes.
    Request templates should be canonical `kinodel.render_requests.v1` envelopes with `schema`, `project_id`, `status`, `stage`, and `jobs`. Move bare arrays/single-job examples and local `/home/...` input media paths to clearly marked legacy examples.

12. Chunk references need a stable mount format.
    Chunk resolver should pass compact refs/summaries by `chunk_id`, `chunk_type`, `source_path`, `mounted_as`, and selected media refs. Do not inline full images/audio/history in delegate handoffs.

## Safe upgrade order

1. Phase 0 docs: align pipeline IDs, serial artifact names, Muse boundary, capability IDs, and mark old draft examples non-canonical.
2. Phase 1 only: add spec schema, `cinematic.v1.json`, and validator; no behavior change.
3. Add compatibility tests proving compiled cinematic route matches current hardcoded maps and p4/p7 remain hard stops.
4. Phase 2: introduce `CompiledRoute` loader with hardcoded cinematic fallback and explicit gate decision state for spec projects.
5. Only then proceed to layout profiles, capability contracts, render adapter registry, chunk resolver, serial specs, and music-video specs.
