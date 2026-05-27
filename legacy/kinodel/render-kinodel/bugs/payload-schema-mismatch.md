---
name: bug payload schema mismatch
trigger: "render worker says no pending jobs, skips jobs, or rejects anchors/payload instead of jobs"
description: Planner artifacts must use kinodel.render_requests.v1 with a non-empty jobs array. Legacy render_queue/anchors/payload shapes are invalid.
category: bug
---

# Bug: render request schema mismatch

Crash/signature: worker exits early, reports no pending jobs, or `state_guard.py validate` rejects request fields.

Cause: a planner wrote legacy/custom shapes (`anchors`, `render_queue.jsonl`, nested provider payloads, `job_type`) instead of `schema: kinodel.render_requests.v1` plus `jobs`.

Fix:
1. Rewrite the request artifact to the canonical `jobs` array.
2. Keep provider payloads out of planner JSON.
3. Validate before render.
