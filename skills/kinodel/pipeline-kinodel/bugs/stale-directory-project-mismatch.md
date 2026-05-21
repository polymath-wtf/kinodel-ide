---
name: bugs stale directory project mismatch
trigger: "new Kinodel concept accidentally resumes or writes into an unrelated old project directory"
description: Prevent stale project directory reuse, mixed project_id state, old render queues, and project-local ad-hoc scripts from corrupting a new Kinodel run.
category: bug
---

# Bug: stale directory / project mismatch

Signature:
- New concept appears inside an old `~/projects/<other_id>/v1` tree.
- `brief.json`, `project_id`, output names, or scripts mention different concepts.
- Legacy `render_queue.jsonl`, `state.json`, `auto_cinema`, ComfyUI/ngrok scripts, or project-local glue are present.

Cause:
- Project directory was selected by memory/vibe/newest folder instead of an approved `project_id` + validated artifacts.
- Directory was scaffolded before BriefGate approval, leaving stale empty or mixed trees.

Fix:
1. Stop; do not render or mutate the mixed directory.
2. Derive/confirm the correct `project_id` from the approved brief.
3. If the old tree is corrupt or superseded, archive the whole tree; do not mix concepts.
4. Initialize only after BriefGate using packaged `init_project.py`.
5. Resume only by `project_id` + `state_guard.py summary/next-goal`, never by newest `outputs/` or remembered folder.

Durable law:
- BriefGate first; scaffold second.
- No project-local ad-hoc scripts.
- `render_results/*.json.selected_outputs` is chaining truth; `outputs/` is an archive/cache.
