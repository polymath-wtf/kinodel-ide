---
name: bug subagent timeout file artifact
trigger: "delegate_task times out while writing story/request JSON"
description: A delegated design agent can hang on simple local artifact writes. Keep Producer context lean, but validate the artifact and retry with a direct deterministic write or a smaller handoff.
category: bug
---

# Bug: subagent timeout on file artifact

Crash/signature: `delegate_task` returns `interrupted`/timeout and the target artifact remains `status: pending`.

Cause: the child model stalled before writing a local JSON artifact.

Fix:
1. Check the target file with `state_guard.py validate`.
2. If unchanged/pending, regenerate with a smaller handoff or direct write when the task is deterministic.
3. Validate JSON and schema before advancing.
