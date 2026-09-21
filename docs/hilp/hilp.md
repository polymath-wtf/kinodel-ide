# Human-in-the-loop

Status: **Accepted MVP contract, 2026-09-21; implementation pending.** HITL means human-in-the-loop. A gate pauses production on one exact result; feedback goes directly to its creative owner. Critic is optional after MVP.

This directory owns human actions: approval at a gate, revision/question in node chat, and future [Fork](fork.md). Chat is an interface, not a second approval mechanism; a new output revision is not a new pipeline version. Runtime delivery and storage mechanics remain backend responsibilities.

## Subject And Gate Policy

One review shows either an immutable text artifact or one complete media-attempt set, plus supporting plans and previews. Its identity includes execution, gate, producing activation, exact subject revision/digest and dependencies. A gate declares its creative owner and fixed repair route; messages cannot select arbitrary destinations.

The story gate confirms the existing story reference. Media gates save one selected attempt for every required unit via their generation tool, then expose `anchor_frames`, `story_frames` or `shot_videos` with the exact selection receipt. Plans are supporting evidence, not additional approvals. An accepted button click is not a finished save; downstream stays blocked until apply commits.

## Creator Actions

| Action | Meaning |
|---|---|
| `approve` | Approve the displayed exact result; for media submit a complete unit-to-attempt selection |
| `revise` | Send a non-empty message and optional typed edit proposal to the current owner, bound to the displayed revision |
| `clarify` | Ask that owner about the current result; answer changes no output or approval |
| `regenerate` | At anchor review only: same prompts, new frozen seed where supported; regenerate selected units and dependents |
| `cancel` | Durably stop this execution; no later result becomes current |

Node discussion is the UI for revise/clarify. The selected action disambiguates an edit from a question; a chat message such as “ok” is not approval. Fields, paths, trusted IDs and graph destinations cannot be overwritten through chat or arbitrary patches.

## Revision Contract

1. Persist feedback with its base result, request identity and deduplication key.
2. Invoke the fixed owner with the previous complete output, approved ancestors, original task, relevant node discussion and current feedback. Preserve conversation for inspection outside graph state; pin the bounded context actually supplied to the model. Do not silently omit required instructions to fit a budget.
3. Validate a complete replacement before saving it as v2/v3. Invalid or partial output follows bounded technical repair; an explanation alone creates no output version.
4. For media, run the associated generation tool from the new saved plan, then open a new complete-set review. Old versions remain visible but cannot approve the new result.

`needs_input` or `out_of_scope` returns an explanation on the unchanged subject. Editing an approved ancestor requires a new run; the current owner cannot quietly rewrite another stage. `RevisionRequestV1` is trusted feedback context prepared by the application, not a required Critic report. No separate revision engine/table is needed.

## Foundation Routes

The authoritative destinations are [cinematic revision routes](../pipelines/cinematic.md#revision-routes). Brief is submitted input, not another gate. The four MVP reviews belong to Storytell, Wardrobe, Storyboard and Filmmaker. There is no final-film or memory gate in this route.

## Request Lifecycle

Internally use `prepare → wait → apply`: persist the exact request; checkpoint one `interrupt()`; apply an authorized decision idempotently. These are implementation steps of one visible HITL node. Wait does not render or call a model. Only a request bound to a durable interrupt becomes actionable.

API acceptance validates the current request/subject, permissions, cancellation and expected revision, then atomically stores the decision plus durable resume work. Duplicate same key/payload returns the original receipt; conflicting or stale input is rejected. Apply rechecks dependencies/current authority, saves the exact result and next activation together. It does not require the already-submitted request to be pending again.

A blocked apply creates no approval or next activation. An authorized same-input retry can complete it; a committed apply returns its existing receipt. After restart, an already consumed decision is never sent to a newer interrupt. [Runtime](../backend/runtime.md#recovery-decision-table) owns delivery and recovery.

## Durable Decisions And Discussion

Use existing `review_requests` for subject, policy, accepted decision and wait binding; `operations` for owner responses and application receipts; `execution_work` for durable resume delivery. No initial-input request is needed: Brief is submitted at Run. Request revisions are unique per execution/gate, creation deduplicates its trigger, and MVP has at most one pending request per execution.

Before checkpoint/task/interrupt binding, the node is `opening`, not actionable. The browser sends the request identity/digest and permitted action, never internal checkpoint or interrupt IDs. Decision acceptance, the accepted-action counter and unique resume work commit together; application later commits the effect, consumption receipt and next activation together. SQLite serializes writes; hosted PostgreSQL uses its own locking protocol defined by [runtime](../backend/runtime.md#single-writer-ownership).

If tab A displays v1 and tab B has already requested v2, approval from A is stale; an identical previously accepted command returns its old receipt without advancing again. Re-selecting a historical version requires an explicit authorized new review/reuse path. There is no universal `approved=true`: text approval refers to the exact subject/apply receipt, media approval to the exact selection receipt and promoted result. A decision blocked by revoked rights remains history, not approval.

For accepted revise, `revision_id = request_id`; persist feedback and owner responses with exact version references. New request/result versions do not reset gate/execution budgets. History lives outside checkpoint state, and downstream receives results rather than discussion. General project-chat editing, deletion and partial-stream UX are deferred in [future topics](../features/future.md).

## Selection Validation

Every required media unit must have exactly one allowed selection, with declared order and no extras. The bytes, plan revision and actual dependencies must match. Face B cannot be selected with a sheet generated from face A. Missing, inaccessible, stale or corrupt material blocks approval. Generation success and file existence are not human selection.

## Limits And Clarification

Retain the existing configurable default of five revisions and five clarifications per gate/execution; regenerate shares the revision budget. Counts increase on accepted requests, not retries, duplicate delivery or restart. Exhausted actions are disabled with an explanation; valid approve/cancel remain. Model/network attempts have separate technical limits.

## Required Checks

Checks and release evidence are centralized in [Local MVP acceptance](../roadmap-mvp.md#acceptance). The contract requires stale/duplicate rejection, v1→v2 direct repair, complete compatible selection, cancellation ordering and crash-safe application. A future Critic only adds optional cited recommendations; the user explicitly forwards chosen suggestions to the correct owner.
