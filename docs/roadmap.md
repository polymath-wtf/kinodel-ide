# Roadmap

Roadmap follows risk, not feature count. Each phase must leave a usable, testable vertical slice.

Local release checklist: [roadmap-mvp.md](roadmap-mvp.md). It owns the current local-build tasks, decision gates and acceptance evidence; this page retains the wider product sequence. Hosted activation is a later, separate release gate.

The [node roadmap](pipelines/node-roadmap.md) owns the phased editor. The authored cinematic route below already uses its agent/service/review boundaries and named typed workflow inputs/outputs. [Node architecture](pipelines/node-architecture.md) and [catalog](pipelines/node-list.md) guide later composition; no node editor/compiler is required for the first build.

Decision update, 2026-09-09: SQLite local / PostgreSQL server, local no-account/no-upload ownership, private endpoint storage, explicit wiki/taste context and new-execution prefix rework are accepted architecture. See [decision register](database/open-questions.md#уже-отвечено-в-контрактах). Unchecked items are implementation/verification work, not a request to reselect these decisions.

## Current Build Gate

The first deployable local `foundation.v0` build follows Brief review -> Story review -> Wardrobe anchor plan -> sequential anchor generation -> complete `main_frames` review/save -> Storyboard shot plan -> frame generation -> frame review/save -> completion. The first acceptance fixture uses portrait -> portrait-conditioned sheet -> independent character-free location, then one Story shot using the three roles. Counts are not schema constants. Critic handles creative revisions; seed-only anchor regeneration uses Render and invalidates dependent units. Plans have no separate mandatory gate. Media saving happens inside review apply, not a visible promotion node. Local mode needs no account; historical dry runs do not count as acceptance.

Dependencies below are activation-specific, not one cumulative prerequisite for the first local build. SQLite recovery and mandatory direct context belong to the local slice. PostgreSQL, Supabase and service accounting must pass their checks before hosted paths open, but do not block local-only execution. Wiki publication and search can wait; resolving explicitly selected required resources cannot. Unchecked design items below require verification against current contracts before new design work: an unchecked box alone is not evidence that the decision is missing.

Audit update, 2026-09-09: the text-only Brief/Story path is an internal implementation/test milestone, not another meaning of deployable `foundation.v0`. [Architecture gates](backend/architecture.md#implementation-gates) separate remaining P0 local decisions/proofs from hosted and future features. No new backend/package manifests or passing runtime tests were found. Before accepting executions, pin tested packages, approve physical DTO/start-pin details, freeze Q4 budgets, choose local DB/file/config/session details and validate exact node/state declarations. Provider Q13 records and one tested image workflow block the rendered build, not the earlier isolated text tests.

Current ownership supersedes the 2026-09-11 single-main-frame design: Wardrobe writes anchor prompts; Storyboard consumes approved anchors to plan shots. Image-only Brief/profile reconciliation remains an open activation task: [physical DTOs](backend/physical-dtos.md#briefv1) and [artifact minimums](backend/artifacts.md#brief-and-story-boundary) still need image-only versus video fields resolved. Runnable schema/saver/provider proofs may begin as isolated experiments now.

ComfyUI transport remains an explicit deployment question: native HTTP submission is documented, an incoming completion webhook is not configured. Confirm native versus custom gateway, endpoint location/authentication, reference-image delivery and callback reachability before adapter activation. A remote callback cannot directly reach a loopback-only local API. Preserve durable job lookup/reconciliation even when callbacks are enabled; see the [MVP transport gate](roadmap-mvp.md#comfyui-transport). Bundled workflow node inputs are not proof of the `/history` output schema. No live provider or SQLite/LangGraph execution was performed by this revalidation; the previous audit's reported 365-link check is not new runtime evidence.

## 0. Foundation

- [x] Distill legacy architecture, agents, scripts, pipelines, and RAG decisions.
- [x] Define graph/agent/tool/artifact boundaries.
- [x] Define active and planned capability contracts.
- [x] Define cinematic, music-video, and serial pipeline topology.
- [x] Define minimal knowledge/retrieval architecture.
- [x] Choose Python for graph/backend runtime; retain TypeScript only for web UI/API consumers.
- [x] Align the foundation delivery plan around `execution_work`, worker-only graph invocation, direct context, and baseline cancellation/security. Design alignment only; implementation and crash tests remain open.
- [x] Define pre-build semantic contracts for the full agent catalog: common invocation/outcomes, role-specific craft, cinematic handoffs, bounded repairs, and future Muse/Season/Episode responsibilities. Not executable schemas or deployed agents.
- [ ] Validate representative cross-agent cinematic contract fixtures and package/version each capability before enabling it; the three-role text test does not define the rendered build or the backend's architectural scope.
- [ ] Implement and validate the [physical Pydantic DTO proposal](backend/physical-dtos.md), including trusted-field rejection, canonical JSON fixtures and start reservation pins; field-level documentation is not executable completion.
- [ ] Encode and test [foundation routes](backend/reviews.md#foundation-routes): sequential anchors, complete-set review/save, dependent regeneration, Storyboard shot planning, frame review and exact completion; executable nodes/deltas remain pending.
- [ ] Implement and verify the documented identity/recovery semantics: pipeline ID/version/digest, operation IDs and input digests, idempotent start, profile-specific ownership and durable resume classification.
- [ ] Implement the documented managed-file/Project-DB commit protocol; settle Q8 start pins and verify no-overwrite publication, replay and orphan protection on supported filesystems.
- [ ] Implement the documented exact-subject review/approval semantics and validate stale detection, Critic edits, clarification, selection/promotion and downstream receipt lookup.
- [ ] Implement executable `BriefV1` and `StoryV1` after reconciling image-only pins and production fields: Brief owns approved settings/vibe; Story owns narrative beats and ordered shot actions without pre-writing image/video prompts.
- [ ] Encode cinematic validators: dynamic anchor units/roles, exact face-to-sheet dependency, compatible complete selection, unchanged-location retention, multi-image shot inputs and transitive invalidation; clip review before Montage with video activation.
- [ ] Implement documented `ContextSelectionV1` and enabled per-agent policies: mandatory direct context, trust/canon roles, citations, precedence, frozen token/media budgets, compact projections and fail-closed conflict/truncation. Library publication/discovery lifecycles belong to phase 4.
- [ ] Define deployable agent registry records and bundle rules for `.agents/`: exact schema IDs, model/runtime configuration, allowed tools, context policy, and only the references each capability needs.
- [ ] Verify source-of-truth routing, status labels, DTO names, lifecycle states and complete-set review fixtures. `cinematic.v1.json` remains a labelled historical snapshot, not an executable current declaration to revive.

Exit: the entire agent catalog has reviewed semantic contracts, with complete cinematic ownership/input/output/repair/context boundaries and acceptance examples. The short runtime slice can be implemented without legacy orchestration or a three-agent-specific backend; executable schemas and capability packages are verified before activation. Later pipelines refine these boundaries rather than inventing their agents after the first build.

## 1. Restart-Safe HITL Slice

- [ ] Project/execution identity and graph registry.
- [ ] SQLite local / PostgreSQL server Project DB: the same logical foundation entities with profile-specific transactions/constraints, not transparent interchangeable DDL.
- [ ] #todo SQLite/PostgreSQL saver integration and managed storage. Local: one application, one active graph runner, exclusive data-directory ownership. Server: separate workers, one invocation per execution. API handlers never invoke the graph.
- [ ] Artifact Store with immutable revisions, hashes, and slot bindings.
- [ ] Explicit `foundation.v0` graph following the full Current Build Gate; a separately identified text test graph may prove Brief/Story first, without changing a frozen production graph on resume.
- [ ] Static versioned capability registry with schema/context/modality validation; Producer/Storytell/Critic for text, Wardrobe anchor prompts, Storyboard shots and image-review Critic for the rendered build.
- [ ] Pinned local workflows for portrait, conditioned sheet, location and multi-reference shots; Q13 jobs/candidates, sequential waits, verified import and approved-selection save with crash/reconciliation tests. No graph `Send` or video dependency.
- [ ] Direct typed-reference resolution and `ContextSelectionV1` persisted before calls, including empty optional selections, exact revisions, and per-agent projections; no discovery/index dependency.
- [ ] Explicit first-deployment access mode, project authorization, managed-path isolation, input validation, and credential separation before accepting executions.
- [ ] Baseline cancellation: durable acceptance, reject later decisions/production commits, worker finalization, and recovery after cancellation.
- [ ] `interrupt()` and typed approve/revise/clarify/cancel resume.
- [ ] Idempotent artifact commit and stale-review rejection.
- [ ] #todo Real SQLite crash tests before the local slice; equivalent PostgreSQL tests before hosted activation: accepted-start recovery, commit-before-checkpoint replay, consumed-response/unfinished-next-node recovery, stale/duplicate review, profile-specific single-writer ownership, cancellation races, and pinned context. Automated backups/RPO/RTO are not MVP blockers.
- [ ] Windows `.bat` and Linux shell launcher -> same Python core -> isolated venv -> version-checked SQLite per [local startup](backend/local-startup.md). Verify OS-specific locks/dependencies/process cleanup on both; macOS not now. Confirm versions/architectures/prerequisites; no global installs or silent resets.
- [ ] Before hosted/service activation, implement Supabase email/password login and idempotent auth-UUID profile initialization with display login; email verification/recovery policy remains open. This does not block the independent local no-account slice.
- [ ] Minimal API and UI showing stage, artifact, review, and failure.

Exit: starts/decisions survive process death without duplicate canonical results or stale/cancelled advancement. Approved `main_frames` and shot frames persist with exact receipts; a new portrait regenerates its sheet while retaining unchanged location. Prove actual multi-reference shot delivery and the [runtime acceptance matrix](backend/runtime.md#acceptance-matrix), including sequential multi-unit recovery now. Video and parallel fan-out remain phase 2.

## 2. First Rendered Cinematic

Current decision: local direct ComfyUI uses authorized file or `/view` import without hosted order auth/bucket; remote hosted uses private GCS and signed downloads followed by verified managed-file import. Browser-hosted project files remain server-side. MVP placeholder credits remain required for Kinodel service computation; product daily free limits are deferred, not credits.

- [ ] Extend the already-tested anchor-to-shot path to full cinematic scale, Filmmaker and Montage; anchor generation and Storyboard handoff already belong to phase 1.
- [ ] Implement the pre-designed visual/motion contracts and frozen prompt-guidance resources/projections; validate the entire unit mapping before render. These are agent resources, not deferred RAG discovery.
- [ ] Extend phase-1 reference-conditioned image workflows to video roles; preserve pinned input/output mappings.
- [ ] Reuse phase-1 multi-unit jobs/waits/selection save for larger frame/clip groups; add parallel execution only with its own checks.
- [ ] Remote hosted: private GCS output upload, unchanged 365-day outputs lifecycle, separate input/workflow/prompt-body policy, signed download renewal and verified import at project owner. Paid generated downloads have no arbitrary product quota; technical size/validation/timeouts and pre-order orphan/ownership checks remain required.
- [ ] MVP placeholder credits: image 1, video low/high 3/5, text input/output 1/2 per million tokens, free models 0, signup 100; integer microcredits, bounded reservations, authoritative usage and idempotent settlement/grant. Auth and technical anti-abuse/admission bounds remain required, not product daily quotas. No real payments. Disable any paid text path lacking reliable usage/reconciliation; do not invent capture or refund.
- [ ] MVP service order logs and durable order/request/settlement identities: no scheduled deletion; do not infer permanent retention of workflow/input/prompt bodies.
- [ ] Enable [new-execution rework](backend/rework.md) only after source-stability, reuse closure, entry and crash checks; unchanged prefix reuse is not checkpoint rewind.
- [ ] Parallel frame/clip fan-out with keyed reducer and deterministic join.
- [ ] Validated `MontagePlanV1` to ffmpeg execution service.
- [ ] Story, main-frames, shot-frame, clip and final review loops.
- [ ] Craft and review `CinemaChunkV1` from approved output.

Exit: one cinematic project survives provider delay, restart, revision, and final human approval.

## 3. Product Runtime

- [ ] Runtime event stream with reconnect/deduplication.
- [ ] Extend baseline cancellation with operational controls and provider reconciliation visibility; the phase-1 image path already includes ambiguous-submit reconciliation and prevention of late promotion. Expanded operational UX remains later.
- [ ] Multi-user authorization and expanded secret/audit operations; baseline Supabase authentication and technical safety ship with their paths. Product daily quotas belong only to Final Release TODOs below.
- [ ] Extend the phase-1 automatic launcher with release packaging and endpoint configuration; no separately administered PostgreSQL or mandatory Kinodel account locally. Docker is not a required product install path.
- [ ] Operational metrics for graph, model, provider, and storage failures.

Exit: a small external test group can run concurrent projects safely.

## Explicit TODO: Deferred After Foundation

- [ ] PostgreSQL concurrency/session ownership, Supabase, GCS and service credits before hosted activation.
- [ ] Larger/parallel shot production, Filmmaker, video, Montage, Craft and `Send`/reducers after the anchor-to-shot foundation.
- [ ] Streaming/outbox, rework with prefix reuse, wiki/chunk publication, FTS/vector retrieval and richer knowledge lifecycle at their feature milestones.
- [ ] Automated backups, RPO/RTO and production transfer UX before making operational recovery promises.
- [ ] Generic repository/DI layers, graph compiler and additional runtime infrastructure only after a second real pipeline proves the need.

## 4. Knowledge And Context

- [ ] Extend the phase-1 direct resolver and projections to source/wiki/chunk libraries and richer mention picking; do not reimplement operation-scoped selection.
- [ ] Extend agent-resource coverage beyond anchor and multi-reference shot guidance in phase 1 and full cinematic guidance in phase 2.
- [ ] Define physical ownership/lifecycle for sources, wiki claims, chunks, retrieval projections, embeddings and traces: archive, supersede, rights withdrawal, purge and rebuild before enabling those libraries.
- [ ] Implement the creative-chunk envelope/promotion contract: immutable revision, approval authority, provenance, rights, semantic media handles, `take`/`ignore` and consumer continuity constraints.
- [ ] Creative chunk candidate, memory review, promotion, revision, archive, and purge lifecycle.
- [ ] Immutable source manifest and maintained wiki workflow.
- [ ] Recursive lint and claim-level provenance.
- [ ] FTS library-discovery baseline when direct selection no longer scales.
- [ ] Versioned retrieval/evidence gold set and numerical gates for direct/FTS, hybrid vectors, reranking, multimodal handles, stale/deleted leakage, latency, cost and context-token regressions.
- [ ] Verify the Gemini Embedding 2 adapter/index contract before vector rollout: endpoint/model, modalities/limits, task types, candidate 768d output, preprocessing, normalization, similarity, index identity, shadow cutover and rollback. Activate only if it beats the FTS baseline.
- [ ] Image/PDF representations only where evaluation proves value.

Exit: context improves measured tasks without becoming hidden canon or leaking deleted data.

## 5. Second Pipelines

- [ ] `music_video.v1`: Muse, audio provider, timing analysis, audio-led montage.
- [ ] `serial_season.v1`: Season and planned continuity chunks.
- [ ] `serial_episode.v1`: Episode and continuity validation.
- [ ] Extract shared graph builders only after two pipelines reveal stable duplication.
- [ ] Evaluate whether a constrained pipeline-spec compiler is justified.

Exit: shared abstractions are backed by at least two working use cases.

## 6. Creator IDE

- [ ] Artifact board and pipeline timeline.
- [ ] Chunk/wiki explorer and explicit context picker.
- [ ] Manual montage/timeline editing.
- [ ] Safe pipeline proposal designer.
- [ ] Advanced VLM/ALM and post-production services.
- [ ] Accessibility, performance, tutorials, and release hardening.

## Final Release TODOs

- [ ] #todo Free LLM product limits: 5 000 000 input and 1 000 000 output tokens per account per day, not MVP. Reset at the next local midnight in `Europe/Chisinau`; test DST transitions, not a fixed UTC offset or rolling 24 hours.
- [ ] #todo Final service order-log/identity retention and tombstone/expired-key policy before scheduled deletion is enabled. Preserve replay/settlement identity; outputs stay 365 days, workflow/input/prompt bodies have a separate policy.
- [ ] #todo Implement accepted lost-text billing by actual authoritative tokens even when response is lost; test usage lookup, unknown reconciliation/escalation, duplicate settlement and explicit new-call UX. No estimates or automatic refund; keep unsupported paid paths disabled until verified.

## Explicitly Not On The Critical Path

- #future production: automated backups, backup retention, RPO/RTO and measured disk-loss restore; stopped-installation manual transfer remains distinct from restart durability.
- #future production: Google login, cards, top-ups, payment webhooks and subscriptions. Supabase email/password and signup 100 credits belong to hosted/service MVP, not the first local-only build.
- #future: detailed onboarding, editors and branch-comparison UX; backend authorization, availability messages and review semantics remain current requirements.

- autonomous agent swarm;
- generic graph compiler before phase 5;
- graph database;
- four-tier MRL index;
- arbitrary agent terminal/filesystem access;
- full visual node editor;
- compatibility with legacy Hermes state files.
