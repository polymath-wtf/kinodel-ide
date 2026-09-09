# Earlier-Stage Rework

Status: **New-execution prefix reuse accepted; physical protocol proposed and unimplemented.** Research checked 2026-09-09. Refines [artifact invalidation](artifacts.md#invalidation) and [review scope](reviews.md#revision-contract).

## Why Not Time Travel

LangGraph supports historical checkpoint replay and `update_state` forks. Nodes after the selected checkpoint execute again, including model/API calls and interrupts. A framework fork is not automatically a new Kinodel execution and cannot roll back Project DB bindings, human approvals, GCS objects or credit settlement. Moving a result into graph state cannot forge permission to reuse it.

Keep ordinary recovery on the same `thread_id = execution_id`, latest matching checkpoint and `None` or exact `Command(resume=...)`. Rework allocates E2 with its own thread and start work; it never copies checkpoint tables, old interrupt IDs, pending writes or arbitrary `goto`. Public clients select an authored entry option, not a checkpoint. This needs no Deep Agents harness, persistent subagent conversation, branch-pointer database or generic graph compiler.

## Source Stability

Proposed minimal release rule: **terminal source execution only**. If E1 is still paused/running, the creator explicitly confirms cancellation of E1 through the existing control protocol; wait until worker finalizes cancellation and local graph/saver writes stop. Do not cancel silently on preview or roll cancellation and E2 start into an imaginary distributed transaction. If E2 validation later fails, E1 remains cancelled and its outputs remain history. Previously completed/failed/cancelled sources need no rewritten outcome.

This deliberately narrows the previously allowed stable-pause alternative. A pause alone can race another review or wake work; supporting two live branches safely is unnecessary for the first rework feature. No project-wide ban on unrelated executions is introduced. Late remote job audit/settlement may still occur for E1, but cannot bind/promote or wake E2. Historical approvals and rights are checked independently of terminal outcome: cancellation never revokes already committed approvals by itself.

## Physical Command

Proposed `ReworkStartRequestV1` fields:

| Field | Meaning |
|---|---|
| `schema_version` | Literal `"1"` |
| `client_key` | Dedupe within project; changed normalized payload conflicts |
| `source_execution_id` | E1 in same project, actor-authorized |
| `target_stage_id` | Enabled authored entry, not arbitrary node name |
| `source_snapshot_digest` | Digest of server-produced source snapshot shown to creator |
| `feedback` | Non-empty original instruction to Critic |
| `reuse_confirmed` | Must be true, bound to that exact snapshot/digest |
| `target_ref` | Exact historical target/owner output to critique, not copied into active E2 target binding |

Server snapshot fields: `{source_execution_id,terminal_receipt_ref,pipeline,entries,closure,closure_digest,target_ref,settings_pins,context_pins}`. Each entry is `{slot,artifact_ref,source_binding_revision,validation_schema_digest,approval_receipt_ref}`; approval receipt nullable only for supporting validation-only plans. Closure lists exact dependency refs/digests/modes/required approvals and necessary media/resource identities. Server reconstructs it from canonical records, never trusts a client-provided manifest as proof. The preview does not authorize indefinite storage pinning; commit rechecks everything and returns conflict if the snapshot is no longer usable.

`ReuseReceiptV1` is the immutable result of E2's start/import operation: `{source_execution_id,target_execution_id,target_stage_id,source_snapshot_digest,closure_digest,reused_bindings,source_receipt_refs,confirmed_by,confirmed_at,pipeline_compatibility_digest}`. `confirmed_by/at` and receipts are trusted metadata. A reuse receipt is authorization to consume an unchanged prefix under checked conditions, **not a new human approval of modified artifacts**. Do not copy old decisions into E2 `review_requests`.

## Start And Entry

1. Validate the registered entry, same-project access, terminal source, exact source snapshot, schema/pipeline/profile/resource compatibility, intact bytes, full transitive rights and every required approval/promotion receipt. Equal schema names alone do not prove compatible graph semantics. First implementation requires the same registered pipeline version/digest; cross-version conversion is deferred.
2. Create the durable start reservation and pins under [physical start protocol](physical-dtos.md#commits-and-start-pins). Protect all reused closure bytes from GC until start commit/explicit abandonment. Store E2's immutable InitialRequest describing this rework command; historical initial request/clarifications remain pinned evidence for Brief repair, not rewritten input history.
3. In one idempotent start/import operation, persist a stable result mapping (or return the previously committed one). Its digest covers target and canonical closure. In the short Project DB transaction recheck source terminal receipt, permissions, rights/closure, reservation and OCC; on conflict commit nothing partial. Create E2 identity/frozen snapshot, initial binding, reused prefix bindings, reuse receipt and unique start work. InitialRequest/body publication precedes that transaction. No cross-DB or checkpoint transaction is claimed.
4. Worker acquires E2 ownership and starts its exact initial state. Authored `rework_entry` validates the committed receipt, then activates target-specific Critic and fixed owner. Crash after the reuse/start commit but before checkpoint replays this same entry without regenerating prefix or reimporting approvals.
5. Ready Critic result produces a complete new target candidate and a new gate; approval unlocks ordinary descendants. Non-ready Critic result blocks E2 with an actionable explanation, without binding the historical target or approving it. In the minimal entry, corrected opening feedback requires a new E2 replacement start; in-run target feedback loops begin once a new target exists. This explicit rule avoids fabricating an unchanged-subject gate when E2 has no current target.

Foundation entry allowlist when implemented:

| Target | Reused active slots | New path |
|---|---|---|
| `brief_propose` | No production prefix; old raw inputs only as pinned evidence | Brief Critic -> Producer -> new Brief review -> Story and its review |
| `story_propose` | Exact approved `brief` | Story Critic -> Storytell -> new Story review |

These are foundation stage names; cinematic uses its own registered `brief_draft`/`story` names. Cinematic entry expansion must encode the dependency closure from [cinematic.md](../pipelines/cinematic.md#exact-dependencies), including validation-only plans and promoted results. It is not enabled by passing another string. Until entry integration passes, ordinary start begins at Brief; comparison UI and arbitrary timeline editor remain #future.

## Cross-Execution Dependencies

E2 bindings reference original E1 artifacts without changing their IDs, URIs, producing execution or provenance. The receipt's historical closure is frozen pinned evidence, checked for integrity/rights/required approvals, not against E1's future mutable bindings. For new E2 outputs, production inputs are `current_execution` dependencies on E2 slots/revisions, even when those slots hold E1 refs. Validate the matching receipt at preparation, commit, review and promotion. This is a narrow import rule, not a blanket cross-execution exemption.

Target and downstream bindings are absent from E2 until newly produced. Matching shot IDs support correspondence/comparison, never authorization to reuse old frames/clips. Changed Brief settings force new profiles/context/units as appropriate; changed Story invalidates the full cinematic suffix. New outputs require new approval. Rights withdrawal can block an already-started E2; pinning cannot override it. GC must traverse reuse receipts, prepared operation pins and retained historical closure, not just latest bindings.

## Required Checks

All **#todo**: duplicate start and changed payload; concurrent source decision/cancel; missing prefix approval or supporting bytes; incompatible version; wrong-project ref; rights withdrawal after preview/before commit; crash before/after reuse commit and first checkpoint; no prefix regeneration; no inherited target approval; old E1 callback never addresses E2; GC cannot remove a reused dependency. Verify on SQLite and PostgreSQL separately. No rework execution or provider was run during documentation research.

## Sources

- [LangGraph time travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel), checked via Context7 2026-09-09: replay/fork repeat downstream effects and interrupts.
- Local `skills/LangGraph/langgraph-fundamentals`, `langgraph-human-in-the-loop`, `langgraph-persistence`: execution/task semantics; examples are not application approval protocols.
- Local `langgraph-cli`, `managed-deep-agents`, `deep-agents-core`, `deep-agents-memory`, `deep-agents-orchestration` were read as comparison evidence. CLI deployment, managed file trees, tool HITL and Store-backed agent memory do not replace Kinodel's exact-revision gates or Project DB. Their presence is not a reason to adopt them. All paths are under `skills/LangGraph/` with `SKILL.md`.
