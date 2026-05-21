---
name: bug init project existing dir
trigger: "init_project.py errors because v1 already exists"
description: The initializer refuses to overwrite an existing Kinodel project. This is expected; resume/validate the existing project instead of reinitializing.
category: bug
---

# Bug: init project existing dir

Crash/signature: `init_project.py` exits non-zero or says the `v1` directory already exists.

Cause: Kinodel project initialization is intentionally non-destructive.

Fix:
1. Run `state_guard.py summary --project-dir <project>/v1`.
2. If artifacts are valid, resume from `state_guard.py next-goal`.
3. If the concept is new, derive a new `project_id`; do not overwrite the old directory.
