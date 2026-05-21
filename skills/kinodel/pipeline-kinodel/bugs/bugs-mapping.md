# Kinodel pipeline bug map

Compact map of still-relevant production bug signatures. Load individual bug files only when the trigger matches.

| Trigger | Bug note | Fix summary |
| --- | --- | --- |
| `init_project.py` refuses existing `v1` | `pipeline-kinodel/bugs/init-project-existing-dir.md` | Resume/validate existing project or choose a new `project_id`; never overwrite. |
| `delegate_task` timeout leaves JSON pending | `pipeline-kinodel/bugs/subagent-timeout-file-artifact.md` | Validate target, retry with smaller handoff or direct deterministic write, then validate schema. |
| Packaged initializer missing | `pipeline-kinodel/bugs/missing-init-project-fallback.md` | Use manual scaffold only as install-drift fallback after BriefGate. |
| Stale directory/project mismatch | `pipeline-kinodel/bugs/stale-directory-project-mismatch.md` | Derive `project_id` after BriefGate; never reuse old project dirs by vibe/newest files. |
