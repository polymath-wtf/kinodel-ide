---
name: bugs missing init project fallback
trigger: "packaged Kinodel init_project.py is missing or broken"
description: Rare install-drift fallback for creating a coherent Kinodel project only when the packaged initializer cannot run.
category: bug
---

# Bug: missing init_project.py fallback

Normal path:

```bash
python3 ~/.hermes/skills/kinodel/kinodel-project-layout/scripts/init_project.py <project_id> '<brief_json>'
```

Use this fallback only for install drift after BriefGate approval.

Fallback:
1. Create `<project>/v1/render_results`, `<project>/v1/qc`, and `<project>/v1/outputs`.
2. Write `brief.json` with the approved `project_id`.
3. Write pending stubs for `story.json`, `wardrobe_request.json`, `storyboard_requests.json`, `video_requests.json`, and render result manifests.
4. Continue only after `state_guard.py summary --project-dir <project>/v1` reports a coherent project.

Never use this as a normal project creation path, and never scaffold before BriefGate approval.
