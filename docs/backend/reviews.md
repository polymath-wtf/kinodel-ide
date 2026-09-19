# Human Review And Revision

Status: **Decided design; implementation and crash tests pending**

A gate stops production for a decision about one exact result. Approval, accepting feedback, applying feedback, and completing the next stage are different events. This page owns their domain semantics; [runtime.md](runtime.md) owns delivery and recovery.

## Subject And Gate Policy

One `ReviewRequest` reviews one immutable subject:

| Kind | Exact identity | Examples |
|---|---|---|
| `artifact` | slot, ArtifactRef, binding revision, producing activation | Brief, Story, final result, memory draft |
| `candidate_set` | stage, activation, candidate-set ID and digest, request digest | one complete manifest of anchor, frame, clip, or song candidates |

The card can show supporting plans and previews. They are evidence, not additional approval subjects. Two independently approved artifacts require two gates. A selected render result can inherit approval through its exact selection/promotion receipt, not through its filename.

For media, **save approved selection** names the storage operation previously called **promotion**. It runs inside the gate's apply path through Render, not as an extra visible pipeline node or human decision. It records the selected assets/result and receipt before authorizing the next stage. Button acceptance alone is not a completed save; crash replay finishes the same idempotent operation. Cinematic's VisualAnchorPlan is supporting evidence, not its own approval subject.

`GateSpec` declares subject kind, fixed `revision_stage_id`, criteria version, selection policy, approve destination, repair path, and loop limits. A repair path includes execution services and any required intermediate reapprovals, not merely an agent call. No model supplies a graph destination.

## Creator Actions

| Action | Accepted input | Durable meaning and route |
|---|---|---|
| `approve` | exact unit-to-candidate selection for media; no creative changes | save this approved selection/result, then authored next stage |
| `revise` | non-empty feedback; optional typed proposed field changes with the same base digest | create a revision case, then Critic, then the fixed owner |
| `regenerate` | anchor unit keys on a gate explicitly enabling this action | same prompts, new frozen seeds where supported; Render regenerates these units and dependents, then a new complete-set review |
| `clarify` | one question about the displayed subject | Producer explanation, then a new request for the same subject |
| `cancel` | optional reason | request cancellation; never approval or deletion |

`Edit` is the UI label for `revise`. A field editor submits a proposal to Critic; it never overwrites the artifact or bypasses its owner. Chat phrases such as `ok` are not approval. Proposed changes cannot contain paths, owner IDs, graph destinations, or runtime controls.

`Regenerate` differs from technical Retry: it authorizes new generation, is bound to the current review digest and deduplicated command, and never edits prompts. No intermediate portrait/sheet/location review is introduced. Reused unrelated candidates and parent/child compatibility follow [anchor regeneration](../pipelines/cinematic.md#anchor-regeneration). Unsupported seed controls cannot be silently ignored. Other gates do not acquire this action implicitly.

## Revision Contract

The accepted `revise` request is the revision-case identity: `revision_id = request_id`. Keep its original feedback and base subject unchanged. Store processing results in ordinary `operations`, not a second revision workflow engine.

Critic receives the exact subject, original feedback/proposed changes, relevant approved constraints, gate criteria, and the fixed owner's editable scope. It returns a bounded `RevisionRequestV1`:

| Field | Meaning |
|---|---|
| `revision_id`, `review_subject` | filled/checked by the adapter against the accepted request |
| `creator_feedback`, `proposed_changes` | original creator input, not Critic's paraphrase replacing it |
| `outcome` | `ready`, `needs_input`, or `out_of_scope` |
| `issues` | target unit/field, severity, evidence, concrete repair instruction |
| `preserve` | explicit constraints that must survive the edit |
| `question_or_reason` | required for a non-ready result |
| `revision_stage_id` | injected from GateSpec, not chosen by Critic |

`ready` schedules a new activation of that owner with the previous exact result and the Critic result. The owner produces a complete new candidate revision, not an unchecked patch. Validation and persistence remain adapter-owned. A valid but unchanged result is shown as unchanged; it is never claimed to have fulfilled the request automatically.

`needs_input` or `out_of_scope` does not call the owner. The graph creates a new request at the original gate for the unchanged subject, displaying the reason and prior feedback. The creator can submit clearer feedback, approve the existing valid result, or cancel. Critic is not allowed to silently change upstream canon or broaden its scope.

The first release has no arbitrary backward jump into already approved ancestors. A request such as changing the approved Brief while reviewing clips is explicitly out of scope; an adjusted production starts a new execution with retained source references. Authored upstream reopening is a later product feature, not hidden `update_state()` or an LLM-selected route.

Decision, 2026-09-09: earlier-stage rework creates a new execution/branch in the same project from an exact approved/validated prefix, under the [prefix-reuse contract](../database/artifacts-media.md#возврат-к-раннему-этапу). Old outputs stay immutable for comparison; changed outputs never inherit approval. Critic analyzes the correction and the declared owner produces the replacement. [Physical rework](rework.md) proposes terminal-source-only entry and receipts; [DTOs](physical-dtos.md#human-commands) define candidate/review fields. Implementation remains #todo; no arbitrary backward routes are added to an existing gate.

## Revision Progress

These are read projections from the accepted request, linked operations, and replacement review. They never select an edge.

| Phase | Evidence | Next event |
|---|---|---|
| `accepted` | revise decision committed, Critic not started | worker runs Critic |
| `critiquing` | Critic operation actively claimed | ready report or actionable reason |
| `applying` | ready report committed; owner/repair path unfinished | validated replacement, including render when required |
| `awaiting_review` | replacement subject and new review request committed | explicit new approval or further feedback |
| `resolved` | replacement approved and revision lineage linked | authored downstream stage |
| `needs_feedback` | Critic/owner could not apply within scope; same-subject request opened | new feedback, accept existing valid subject, or cancel |
| `superseded` | a later revise decision replaces this feedback case | later case owns the repair |
| `cancelled` / `failed` | execution has the corresponding terminal outcome | history only |

Infrastructure interruption is an execution `blocked`/recovering condition, not new creative feedback. A technical retry uses the same operation, input selection, and revision case. It does not call Critic again if Critic already committed.

## Request Lifecycle

`ReviewRequest` stores request ID, execution/gate IDs, request revision, gate activation, subject, digest, policy snapshot, allowed actions, prior request/revision links, optional explanation ref, decision, and timestamps.

```text
pending -> submitted -> consumed
pending -> superseded | cancelled
submitted -> cancelled   (only if not yet applied and cancellation wins)
```

`pending` is actionable only after the worker associates it with a durably saved matching interrupt. Before that the UI shows `opening`, not a clickable approval card. `submitted` means accepted for processing. `consumed` means the graph's idempotent apply operation recorded the decision outcome and next activation, not that the requested creative work finished.

Request identity is unique by `(execution_id, gate_id, request_revision)` and by its deterministic gate-activation trigger. Replay reuses the same request. A new subject, explanation, or feedback-needed result creates a new request revision. Never mutate a card already displayed or use "latest pending request" during replay of an older gate task.

The request digest covers the subject, producing activation, dependency/selection policy, gate criteria, actions, and request revision. Acceptance is one short Project DB transaction with execution-row serialization and optimistic checks:

1. authorize the actor and match the exact digest and action payload;
2. return an identical previously accepted decision; reject a conflicting duplicate;
3. for a new decision require a nonterminal execution, no accepted cancellation, and this actionable pending request;
4. verify active producing activation, exact current binding or candidate manifest, transitive execution dependencies, and current access/rights;
5. for candidate approval require exactly one allowed candidate for every required unit, no extras, policy-defined order, and matching parent candidate IDs/digests for dependent anchors;
6. atomically save the decision and one `execution_work` resume intent, unique by source request across all work states.

The apply operation checks the submitted decision against the current subject, rights, dependencies, cancellation and terminal state; it does not require `pending` again. If inputs became invalid, retain the submitted decision as history and leave the operation blocked for an authorized same-input retry. A committed apply receipt is immutable and replay returns it without applying the decision again. Cancellation and terminal outcomes never erase past approvals.

Current revision means the exact current request, producing activation and binding/manifest, not merely an existing artifact revision. If another accepted edit produces S2/R2, approval from S1/R1 conflicts and the UI refreshes the current card; it neither approves S2 nor reselects S1. An identical previously accepted command may return its receipt without advancing again. Historical approval and comparison remain available, but choosing an old result again requires an explicit authorized review/reuse path.

## Clarification And Limits

Producer answers about the exact subject without changing it. Its bounded `ReviewClarificationAnswer` is a durable operation result linked to the next card, not a creative artifact or unbounded conversation. If the question contains a new requirement, the answer explains that `revise` is needed; it does not apply it.

The initial design default is **five accepted revisions and five accepted clarifications per gate per execution**, frozen in the pipeline policy. These are chosen product limits, not LangGraph limits. Counts increment once on accepted decisions, including feedback that Critic cannot apply. Retries, duplicate delivery, and process restarts do not increment them. At a limit, the next card removes the exhausted action and explains why; when both are exhausted only approve/cancel remain. Approval remains unavailable for an invalid/stale subject. Never reset limits by creating a new request or use LangGraph's recursion limit as the product counter.

Where enabled, `regenerate` uses the same frozen revision budget; it does not reset limits or consume a clarification. Technical retries remain separate. This configurable gate limit does not create dependencies: rerendering location never forces character rerenders.

An owner's `needs_input` while repairing an existing subject follows the same unchanged-subject feedback path. Before any Brief exists, Producer may instead ask one focused input question: an `input` request with `answer`/`cancel`, not a review approval. The answer is stored separately from immutable `InitialRequestV1` and starts a new Brief activation. A second unresolved input request blocks the execution rather than looping without a bound.

## Foundation Routes

Each logical gate consists of prepare, wait, and apply nodes. Names below are logical stages; [langgraph.md](langgraph.md) specifies the node boundary.

| From | Event | Route |
|---|---|---|
| start | initial activation | `brief_propose` |
| `brief_propose` | validated draft | `brief_review` |
| `brief_propose` | first focused question | `brief_input -> answer -> brief_propose` with new activation |
| `brief_review` | approve | `story_propose -> story_review` |
| `brief_review` | revise | `brief_critic -> brief_propose -> brief_review` |
| `brief_review` | clarify | `brief_explain -> brief_review`, same subject |
| `story_review` | approve | `visual_anchor_plan -> render_anchor_candidates` |
| `story_review` | revise | `story_critic -> story_propose -> story_review` |
| `story_review` | clarify | `story_explain -> story_review`, same subject |
| `render_anchor_candidates` | durable group intent | sequential portrait -> conditioned sheet -> independent location; verified complete manifest -> `main_frames_review` |
| `main_frames_review` | approve exact compatible selection | save `main_frames` in apply path -> `frame_plan -> render_frame_candidates` |
| `main_frames_review` | revise | anchor-media Critic -> Wardrobe `visual_anchor_plan` -> changed/dependent renders -> same complete-set gate |
| `main_frames_review` | regenerate | Render selected units and dependents with new frozen seeds -> same complete-set gate; no Critic |
| `render_frame_candidates` | durable group intent | submit/wait/join -> verified complete manifest -> `frame_review` |
| `frame_review` | approve exact selection | save `story_frames` in apply path -> `complete -> END` |
| `frame_review` | revise | rendered-frame Critic -> Storyboard `frame_plan` -> render/wait/join -> same gate |
| anchor/frame gate | clarify | Producer explanation -> same-subject new request |
| any Critic / repair owner | needs input or out of scope | original gate, unchanged subject, reason attached |
| first-generation owner without a subject | non-ready result other than the bounded pre-Brief question | block with reason; do not fabricate a review subject |
| any active stage/request | cancellation accepted | stop effects, finalize cancelled under worker ownership |
| any operation | recoverable infrastructure failure | retain activation, block/retry work under runtime policy |
| any operation | integrity/programming failure | durable failed outcome; no creative route around it |

An approve transition authorizes the next stage only after saving its required result. Revise authorizes an owner activation through Critic; regenerate authorizes only the declared Render path. No successor is inferred from status, a file, or agent report text.

This table follows the rendered [build gate](../roadmap.md#current-build-gate). Text-only `story_review -> complete` remains a separately identified internal test. Completion requires current approved Brief/Story, saved approved `main_frames` and `story_frames`, exact validated supporting plans and fresh dependencies. The one-shot acceptance fixture exercises the three example anchors together; schemas do not hardcode these counts. Sequential service jobs need no graph fan-out. Exact Python node declarations and per-node deltas still require executable fixtures.

## Required Checks

- Duplicate feedback creates one Critic operation and one owner activation.
- Crash after Critic commit does not repeat Critic; crash after owner commit does not generate another revision.
- A replacement never inherits the old subject's approval.
- Clarification changes the request, not the artifact, producing activation, or approval.
- Out-of-scope feedback does not change an ancestor; exhausted limits remain exhausted after restart.
- Stale cards, incomplete candidate selection, invalid rights, and cancellation races cannot advance production.
