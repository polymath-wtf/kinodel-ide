# Kinodel audit and remediation

Maintenance-only reference. Load this when auditing production readiness, stale references, skill-package hygiene, context aerodynamics, scripts, or gate safety. Do not load during normal production runs.

## Scope

Audit the class-level Kinodel library, not only the current project directory:

- `~/.hermes/skills/kinodel/*/SKILL.md`
- `references/`, `bugs/`, `scripts/`, `providers/`, `workflows/`, `templates/`, `tests/`
- packaged scripts used by Producer/Render

## Required checks

1. Skill package hygiene
   - Run the skill validator per Kinodel skill when available.
   - Frontmatter should be packaging-clean for the active Hermes validator.
   - Remove generated files such as `__pycache__` before build.

2. Context aerodynamics
   - Estimate SKILL.md size/line count for hot-path skills.
   - Hot path normally loads only `pipeline-kinodel` + `producer-kinodel`; specialists should be delegated.
   - Backup/debug skills such as `comfyui` must not be loaded in normal production unless explicitly requested.
   - Large examples, provider payloads, incident transcripts, and old project notes belong in owner references or `bugs/`, not hot SKILL.md bodies.

3. Link integrity
   - Check pointers to `references/`, `bugs/`, `providers/`, `scripts/`, and templates.
   - Fix pointers after moving ownership boundaries.
   - Avoid vague glob-style pointers when deterministic filenames are possible.

4. Stale/legacy content
   - Search for `scenario.json`, `auto_cinema`, old ComfyUI-first flows, old project names, `render_queue.jsonl`, and ad-hoc project-local scripts.
   - Preserve only durable lessons in class-level skills; archive one-off incident narratives after their lessons are encoded.
   - Keep ComfyUI/ngrok/local-model incident material under the ComfyUI backup skill or archive, not the fal-first hot path.

5. Script smoke checks
   - Compile Python scripts with `python3 -m py_compile`.
   - Smoke-test `init_project.py` under a fake `HOME`, never by creating an empty real project before BriefGate.
   - Smoke-test `state_guard.py summary`, `validate`, and `next-goal` on a synthetic project.
   - Check `render.py --help` and ensure `--stage {images|videos}` is required.

6. Gate safety
   - Verify p4/p7 hard stops are still documented and enforced.
   - Any bypass/skip-gates flag must be documented as diagnostics/debug-only, not normal production flow.

7. Artifact-contract consistency
   - Planner artifacts remain provider-neutral with `schema`, `project_id`, `status`, `stage`, and non-empty `jobs[]` when complete.
   - Render result manifests use compact `selected_outputs`; downstream stages must not scan `outputs/` to infer state.
   - Provider queue IDs, raw responses, logs, costs, retry state, and temporary payloads stay in `/tmp/kinodel/...` or debug output.

## Remediation patterns

- Frontmatter remediation: `quick_validate.py` accepts only `name`, `description`, `license`, `allowed-tools`, and `metadata` as top-level `SKILL.md` frontmatter. Move older custom fields under `metadata.hermes`.
- Slash visibility: after moving/renaming skills, verify with `hermes skills list | grep -E 'kinodel|comfyui'`.
- Bug directory hygiene: keep still-relevant failures as compact `bugs/*.md` notes and add a row to `bugs/bugs-mapping.md`.
- Provider boundary: ComfyUI is the normal default provider family; fal.ai is an explicit option/fallback. Do not load low-level ComfyUI debugging skill unless setup/workflow troubleshooting is needed.
- Gate bypass hygiene: `state_guard.py next-goal --skip-gates` is DEBUG ONLY and must never appear in normal production advancement.
- Dry-run decision rule: render dry-run/validate-only is CI polish, not automatically P0 if `state_guard.py validate` already catches schema and public-URL issues.

## Reporting format

Return:

- overall status: production-ready / production-capable with blockers / not ready
- P0 build blockers
- P1 context/aerodynamics cleanup
- P2 polish
- concrete file paths for stale references/scripts
- smoke-test results and exact commands when useful

Do not stop at a narrative summary if the audit found fixable skill-library issues. Patch relevant class-level skills or support references immediately when safe.
