---
name: render-kinodel
description: RenderService/provider adapter contract. Executes provider-neutral render requests and promotes compact result manifests.
---

# Render-Kinodel

Render is non-creative infrastructure. It executes complete request artifacts and returns selected media refs.

## Input

- `kinodel.render_requests.v1` artifact declared by the stage spec
- project/job context from `GraphRuntime`
- provider bindings from `ProviderRegistry`

## Output

Write or promote `kinodel.render_result.v1` manifests with:

- `project_id`
- `status: "complete"`
- `stage`
- `selected_outputs[]` with stable `path`, public `url` when available, kind, optional shot_id, and hashes when useful
- optional compact source request snapshot metadata

## Runtime ownership

RenderService owns:

- provider selection and capability binding
- provider payload construction
- public URL preflight
- async job IDs and provider status
- retries and backoff
- temporary request/result/events files
- compact result promotion

## Forbidden in durable planner artifacts

- provider queue IDs
- status URLs
- raw provider responses
- provider workflow JSON
- retry state
- logs
- cost/debug payloads

## LangGraph behavior

Long renders should not keep a chat/request turn alive. The node should submit a job, persist job state, stream progress through NotificationService, and resume the graph thread when the result manifest is ready.
