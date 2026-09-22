# Tools And Generation

Status: **Accepted MVP boundary; implementation pending.** Agents create typed creative output and can request allowlisted tools. Tools perform validated side effects; the graph decides when each tool may run.

## Generation Tool Calls

| Creative node | Following tool node | Saved selected media |
|---|---|---|
| Wardrobe | `anchor-gen` | `anchor_frames` |
| Storyboard | `frames-gen` | `story_frames` |
| Filmmaker | `video-gen` | `shot_videos` |

These are uses of one provider-neutral [Render service](render.md), not three provider frameworks. Start with one concrete ComfyUI adapter; fal or another endpoint can implement the same validated operations when needed.

MVP uses **plan-first tool dispatch**: the agent's complete response supplies prompts and references; its adapter validates and saves the plan, then the fixed `*-gen` node invokes the generation tool. This satisfies `Storyboard → frames-gen (tool) → HITL` without an open-ended agent loop. If a model adapter emits native `tool_calls`, accept only the declared generation call, validate its semantic arguments against the saved plan, and dispatch through the same path. Native model function-calling is not a second required implementation for MVP and does not authorize extra jobs or graph edges.

## Nonblocking Contract

| Operation | Input | Output / effect |
|---|---|---|
| `generation_submit` | Exact saved plan and selected media refs; trusted execution/stage/operation and pinned profile supplied by runtime | Persist job-group intent; return `JobGroupRef` promptly, not rendered bytes |
| `generation_status` | Owned group ref | Pending/running/succeeded/blocked/failed and exact verified attempt refs |
| `generation_cancel` | Owned group ref and accepted control | Best-effort provider cancellation; local promotion remains prohibited |
| `save_selection` | Exact complete review set, accepted selection and expected binding revision | Managed assets, selected result ref and immutable receipt |

Submission returns after local durable acceptance. A worker sends the provider request, records its ID, polls/reconciles and imports verified results. The graph persists its wait and releases the invocation until the group is ready; no LLM, HTTP browser request or sleeping agent holds the render open. A resumed `*-gen` finishes its result and exposes the human review. There is no second model call just to announce render completion.

The job-group ref means **queued**, not provider acceptance, completed generation or approval. Losing the provider response after submission is `reconciling/blocked`; never resend blindly. Recovery and fast/late results follow [runtime rendering](../backend/runtime.md#rendering-extension).

## Validation And Idempotency

- Resolve credentials/endpoints and provider payloads only in the adapter. Model tool arguments contain semantic prompts/reference aliases, never secret keys, arbitrary URLs/paths, approval or routing fields.
- Check current execution, cancellation, exact inputs, schema, unit coverage and workflow capacity before upload or submission. The runtime supplies trusted IDs, idempotency keys and expected revisions.
- Persist effective workflow/input mappings, seeds and request identity before network effects. Retry uses those same values; same operation with changed input is an integrity error.
- External providers need their own verified idempotency/correlation support. Our local deduplication does not make their POST exactly-once.
- Verify returned unit, job, output node, media type, size and bytes before import. Provider URLs/paths are temporary delivery, not canonical assets.
- Save selection atomically with its receipt and binding update; optimistic concurrency rejects stale replacement. Tool workers cannot select an output or approve it on their own.

## Other Tools

[`montage`](montage.md) concatenates every approved `shot_videos` clip in Story order into silent `final_video`, with a validated internal plan, fixed ffmpeg arguments and ffprobe verification. It runs without an LLM in MVP; subprocess output stays isolated until verified import.

Context resolution and result persistence are trusted application helpers, not filesystem tools exposed to every agent. Saving needs no Craft agent; separate future [memory publication](memory.md) uses explicit review. Use direct references and consumer-specific projections; no discovery/index dependency. Producer/Storytell need no rendering tool. Critic is deferred.

## Foundation Operations

Node adapters prepare exact inputs, look up a prior committed operation before effects, validate/save output and return compact refs. Existing `get_declared_inputs`, `get_operation_result`, `commit_artifacts`, `review_respond` and worker-only `claim_next_work` retain these responsibilities; do not wrap them in a universal ToolResult or duplicate job ledger.

Physical data proposals: [DTOs](../backend/dto.md). Provider specifics: [ComfyUI](../backend/comfyui.md). Route: [cinematic](../pipelines/cinematic.md). Build tasks and tests: [Local MVP](../roadmap-mvp.md).
