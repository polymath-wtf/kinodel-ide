# Phase C — Layout Profiles, Contracts, Templates, PipelineChoiceGate

Use this reference after Phase C or when auditing project initialization/capability binding.

## Current Phase C artifact locations

- `../kinodel-project-layout/scripts/init_project.py` — canonical initializer; old positional CLI is preserved and optional `--pipeline-id`, `--layout-profile`, `--pipeline-spec` flags are supported.
- `scripts/init_project.py` — compatibility forwarder to the layout-owned initializer.
- `contracts/capabilities.v1.json` — active/planned capability registry. Only `cinematic.v1` capabilities are active/bindable in Phase C.
- `scripts/validate_agent_contracts.py` — validates pipeline specs against active/bindable capability contracts and render adapter contracts.
- `templates/wardrobe_request.json`, `templates/storyboard_requests.json`, `templates/video_requests.json` — canonical `kinodel.render_requests.v1` envelope templates.
- `templates/producer_state.json` — Phase C producer state template with `pipeline_id`, `layout_profile`, `current_goal`, `stage_cursor`, and `gate_decisions`.

## Phase C invariants

- The old initializer CLI still works:

```bash
python3 ~/.hermes/skills/kinodel/kinodel-project-layout/scripts/init_project.py <project_id> '<brief_json>'
```

- Default production initialization is still cinematic:
  - `pipeline_id=cinematic.v1`
  - `layout_profile=cinematic`
- New projects get frozen project-local `pipeline_spec.json` and `producer_state.json`.
- Non-cinematic pipelines/profiles are declared only as planned/locked and cannot initialize production projects in Phase C.
- Planned capabilities cannot satisfy binding validation.
- p4/p7 ReviewGate behavior remains governed by Phase B: explicit gate decision state is required for spec-based projects.

## Required verification commands

```bash
python3 -m py_compile ~/.hermes/skills/kinodel/kinodel-project-layout/scripts/init_project.py
python3 ~/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_pipeline_spec.py \
  ~/.hermes/skills/kinodel/pipeline-kinodel/pipelines/cinematic.v1.json
python3 ~/.hermes/skills/kinodel/pipeline-kinodel/scripts/validate_agent_contracts.py
python3 ~/.hermes/skills/kinodel/kinodel-project-layout/tests/test_init_project_phase_c.py
python3 ~/.hermes/skills/kinodel/producer-kinodel/tests/test_state_guard_pipeline_runtime.py
```

Expected result: all pass; default init creates old cinematic files plus `pipeline_spec.json` and `producer_state.json`; locked pipelines fail before creating a project directory.

## Session implementation notes / pitfalls

- Keep `kinodel-project-layout/scripts/init_project.py` as the single owned initializer. If `pipeline-kinodel/scripts/init_project.py` exists, make it a forwarding compatibility wrapper instead of maintaining a duplicate implementation.
- Preserve the old positional initializer CLI exactly; add pipeline/profile/spec behavior only through optional flags so existing production commands continue working.
- Locking planned pipelines must happen before creating any project directory. Regression tests should assert the project path was not created for `serial_season.v1`, `serial_episode.v1`, `music_video.v1`, and other planned profiles.
- `validate_agent_contracts.py` should test both stage-required capabilities and render adapter profiles. Planned capabilities may be present in the registry for roadmap visibility, but `status: planned` / `bindable: false` must fail binding validation.
- Init tests intentionally exercise negative paths; expected `ERROR:` lines for duplicate directories or locked profiles are not failures when unittest exits OK.
