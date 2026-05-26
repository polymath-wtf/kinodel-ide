# Universal Runtime Patch Compatibility Audit

Use this reference before upgrading Kinodel from the hardcoded cinematic route to a universal `kinodel.pipeline_spec.v1` runtime.

## Audit order

1. Read the patch implementation plan first, then linked runtime/pipeline/chunk/agent pages.
2. Inspect executable hotspots before touching live behavior:
   - `producer-kinodel/scripts/state_guard.py`
   - `kinodel-project-layout/scripts/init_project.py`
   - `pipeline-kinodel/scripts/init_project.py`
   - `render-kinodel/scripts/render.py`
   - `render-kinodel/scripts/render_worker.py`
   - `render-kinodel/scripts/copy_worker_result.py`
   - `render-kinodel/scripts/render_wakeup.py`
   - `pipeline-kinodel/templates/*.json`
3. Check wiki/spec consistency before code: MVP pipeline IDs, p4/p7 hard stops, serial artifact names, Muse/Render ownership, chunk statuses, and `final_chunk.json` compatibility.
4. Verify linked pages have no broken wikilinks and no live `agent-serial-kinodel` link.
5. Do not start Phase 1 implementation until the docs/specs are non-contradictory.

## High-value compatibility checks

- `serial.v1` must only mean a future parent/orchestrator; MVP specs are `serial_season.v1` and `serial_episode.v1`.
- Spec-declared gates cannot rely only on “preview artifact exists and next artifact missing”. New spec-based projects need explicit gate decision state (`goal`, `gate_alias`, `decision`, `approved_at`, `notes_ref`). Old cinematic projects may keep the current p4/p7 heuristic only as fallback.
- Do not create parallel dynamic versions of every old map. Compile `pipeline_spec.v1` into one `CompiledRoute` and make helpers read from it.
- `CompiledRoute` should expose ordered stages, stage descriptors, artifact validators, gate descriptors, render descriptors, handoff descriptors, layout descriptors, chunk dependencies, and final chunk descriptor.
- Validators must distinguish status families:
  - working artifacts: `pending | complete`
  - approved/final chunks: `draft | approved | completed | archived`
- Accept legacy `final_chunk.json` with `kinodel.final_chunk.v1`; treat `kinodel.chunk.cinema.v1` as the semantic successor, not a breaking replacement.
- Render promotion and wakeup must eventually derive request/result/next-action mapping from the pipeline spec, not hardcoded cinematic `main_frame/story_frames/shot_videos` maps.
- `copy_worker_result.py` must accept native `render_worker.py` result shape (`summary.outputs` plus `jobs`) before promoting compact refs into durable `render_results/*.json`.
- Muse is a planner/composer: it writes `muse_output.json` and provider-neutral `music_request.json`; Render/audio worker produces `outputs/music.mp3` and `music_result.json`.
- Serial episode goals use canonical machine names `p2_episode_anchor_plan` / `p3_episode_anchor_render`; “act anchors” is `anchor_mode: per_act`, not a separate goal namespace.
- Canonical layout profiles: `cinematic`, `serial_season`, `serial_episode`, `music_video`, `renovation_timelapse`. `season` may only be an alias for `serial_season`.

## Simplification cascade

The unifying abstraction is: everything is a special case of a compiled pipeline route.

This eliminates duplicated hardcoded maps for goal order, schemas, request/result artifacts, review gates, render destinations, wake-up actions, layout stubs, and handoff specs. Keep cinematic hardcoded maps only as legacy fallback while `cinematic.v1` parity tests prove compatibility.

## Safe patch sequence

1. Phase 0 docs/spec cleanup: verify roadmap sources/dependencies, MVP IDs, hard-gate language, and per-phase Test gates before live skill edits.
2. Phase A: schema + `cinematic.v1` + static validator only; no behavior change. `cinematic.v1` is the compatibility mirror of the current hardcoded p0-p11 route, while `pipeline-kinodel` remains universal law/runtime architecture.
3. Add parity tests: current cinematic goal order, handoff shape, p4/p7 stop behavior, legacy final_chunk acceptance, canonical templates.
4. Phase B: spec-aware state guard with hardcoded cinematic fallback and explicit gate decision state. Spec projects cannot pass gates by artifact existence alone.
5. Phase C: dynamic layout profiles, project-local `pipeline_spec.json`, `producer_state.json`, PipelineChoiceGate before BriefGate/init_project, capability contracts, and request template cleanup. Non-cinematic profiles stay locked until activation phases.
6. Phase D: chunk resolver plus `serial_season.v1` and `serial_episode.v1`.
7. Phase E: music-video/Suno path only — `music_video.v1`, Muse planner contracts, provider-neutral `music_request.json`, and Render-owned audio/provider calls.
8. Phase F: `create-pipeline` spec drafting and draft/test `renovation_timelapse.v1`; do not auto-activate draft pipelines.
