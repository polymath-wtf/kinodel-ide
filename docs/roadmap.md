# Roadmap

Roadmap follows risk, not feature count. Each phase must leave a usable, testable vertical slice.

Decision update, 2026-09-09: SQLite local / PostgreSQL server, local no-account/no-upload ownership, private endpoint storage, explicit wiki/taste context and new-execution prefix rework are accepted architecture. See [decision register](database/open-questions.md#уже-отвечено-в-контрактах). Unchecked items are implementation/verification work, not a request to reselect these decisions.

## Current Build Gate

The first deployable engineering build is the local `foundation.v0` slice: Brief review -> Story review -> Wardrobe visual-anchor plan/review -> Storyboard main-frame plan -> one ComfyUI image job -> verified local candidate import/join -> explicit main-frame selection review -> promotion to SQLite metadata -> completion. Critic mediates revisions at every gate; Render is a service. Storyboard main-frame mode is required now, its full shot-frame mode remains later. This is a readiness gate, not a claim that code exists. Hosted first deployment requires registration; local mode remains no-account. Historical dry runs do not count.

Dependencies below are activation-specific, not one cumulative prerequisite for the first local build. SQLite recovery and mandatory direct context belong to the local slice. PostgreSQL, Supabase and service accounting must pass their checks before hosted paths open, but do not block local-only execution. Wiki publication and search can wait; resolving explicitly selected required resources cannot. Unchecked design items below require verification against current contracts before new design work: an unchecked box alone is not evidence that the decision is missing.

Audit update, 2026-09-09: the text-only Brief/Story path is an internal implementation/test milestone, not another meaning of deployable `foundation.v0`. [Architecture gates](backend/architecture.md#implementation-gates) separate remaining P0 local decisions/proofs from hosted and future features. No new backend/package manifests or passing runtime tests were found. Before accepting executions, pin tested packages, approve physical DTO/start-pin details, freeze Q4 budgets, choose local DB/file/config/session details and validate exact node/state declarations. Provider Q13 records and one tested image workflow block the rendered build, not the earlier isolated text tests.

## 0. Foundation

- [x] Distill legacy architecture, agents, scripts, pipelines, and RAG decisions.
- [x] Define graph/agent/tool/artifact boundaries.
- [x] Define active and planned capability contracts.
- [x] Define cinematic, music-video, and serial pipeline topology.
- [x] Define minimal knowledge/retrieval architecture.
- [x] Choose Python for graph/backend runtime; retain TypeScript only for web UI/API consumers.
- [x] Align the foundation delivery plan around `execution_work`, worker-only graph invocation, direct context, and baseline cancellation/security. Design alignment only; implementation and crash tests remain open.
- [x] Define pre-build semantic contracts for the full agent catalog: common invocation/outcomes, role-specific craft, cinematic handoffs, bounded repairs, and future Muse/Season/Episode responsibilities. Not executable schemas or deployed agents.
- [ ] Validate representative cross-agent cinematic contract fixtures and package/version each capability before enabling it; the first graph's three roles do not define the backend's architectural scope.
- [ ] Implement and validate the [physical Pydantic DTO proposal](backend/physical-dtos.md), including trusted-field rejection, canonical JSON fixtures and start reservation pins; field-level documentation is not executable completion.
- [ ] Encode and test the [foundation route table](backend/reviews.md#foundation-routes), including visual review, Storyboard main mode, external wait, selection/promotion and exact completion requirements; logical routes are documented, executable nodes/deltas are not.
- [ ] Implement and verify the documented identity/recovery semantics: pipeline ID/version/digest, operation IDs and input digests, idempotent start, profile-specific ownership and durable resume classification.
- [ ] Implement the documented managed-file/Project-DB commit protocol; settle Q8 start pins and verify no-overwrite publication, replay and orphan protection on supported filesystems.
- [ ] Implement the documented exact-subject review/approval semantics and validate stale detection, Critic edits, clarification, selection/promotion and downstream receipt lookup.
- [ ] Specify executable `BriefV1` and `StoryV1`: Brief owns approved project/generation settings and extracted user vibe; Story owns narrative beats and ordered shot actions without pre-writing Storyboard or Filmmaker prompts.
- [ ] Resolve cinematic production invariants: main frame as a continuity anchor, job candidates versus promoted assets, clip/take review before montage, managed local project storage, and revision invalidation rules.
- [ ] Define physical ownership and lifecycle for sources, wiki claims, creative chunks, retrieval projections, embeddings, and retrieval traces; include archive, supersede, rights withdrawal, purge, and rebuild behavior.
- [ ] Define the first creative-chunk envelope and promotion contract: immutable revision, approval authority, provenance, rights, semantic media handles, `take`/`ignore`, and consumer-specific continuity constraints.
- [ ] Define `ContextSelectionV1` and per-agent context policies: mandatory direct context versus suggestions, trust/canon role, citations, precedence, token budgets, compact projections, and fail-closed conflict/truncation behavior.
- [ ] Verify and freeze the Gemini Embedding 2 adapter/index contract before vector rollout: endpoint/model, supported modalities and limits, task types, 768d output, preprocessing, normalization, similarity metric, index identity, shadow reindex/cutover, and rollback.
- [ ] Define a versioned retrieval gold set and numerical promotion gate for direct/FTS, hybrid vectors, reranking, multimodal handles, stale/deleted leakage, latency, cost, and context-token regressions.
- [ ] Define deployable agent registry records and bundle rules for `.agents/`: exact schema IDs, model/runtime configuration, allowed tools, context policy, and only the references each capability needs.
- [ ] Reconcile source-of-truth contradictions before implementation: stale `cinematic.v1.json`, RAG documentation routes, status labels, reference DTO names, lifecycle states, and singular-versus-bundle review contracts.

Exit: the entire agent catalog has reviewed semantic contracts, with complete cinematic ownership/input/output/repair/context boundaries and acceptance examples. The short runtime slice can be implemented without legacy orchestration or a three-agent-specific backend; executable schemas and capability packages are verified before activation. Later pipelines refine these boundaries rather than inventing their agents after the first build.

## 1. Restart-Safe HITL Slice

- [ ] Project/execution identity and graph registry.
- [ ] SQLite local / PostgreSQL server Project DB: the same logical foundation entities with profile-specific transactions/constraints, not transparent interchangeable DDL.
- [ ] #todo SQLite/PostgreSQL saver integration and managed storage. Local: one application, one active graph runner, exclusive data-directory ownership. Server: separate workers, one invocation per execution. API handlers never invoke the graph.
- [ ] Artifact Store with immutable revisions, hashes, and slot bindings.
- [ ] Explicit `foundation.v0` graph following the full Current Build Gate; a separately identified text test graph may prove Brief/Story first, without changing a frozen production graph on resume.
- [ ] Static versioned capability/mode registry with enabled-schema/context/modality validation; Producer/Storytell/Critic for the text milestone, Wardrobe/Storyboard main mode and image-review Critic for the deployable build.
- [ ] One pinned local ComfyUI image workflow, Q13 job/group/candidate records, external wait, verified import, selection and promotion with provider crash/reconciliation tests; no `Send` or video dependency for one main unit.
- [ ] Direct typed-reference resolution and `ContextSelectionV1` persisted before calls, including empty optional selections, exact revisions, and per-agent projections; no discovery/index dependency.
- [ ] Explicit first-deployment access mode, project authorization, managed-path isolation, input validation, and credential separation before accepting executions.
- [ ] Baseline cancellation: durable acceptance, reject later decisions/production commits, worker finalization, and recovery after cancellation.
- [ ] `interrupt()` and typed approve/revise/clarify/cancel resume.
- [ ] Idempotent artifact commit and stale-review rejection.
- [ ] #todo Real SQLite crash tests before the local slice; equivalent PostgreSQL tests before hosted activation: accepted-start recovery, commit-before-checkpoint replay, consumed-response/unfinished-next-node recovery, stale/duplicate review, profile-specific single-writer ownership, cancellation races, and pinned context. Automated backups/RPO/RTO are not MVP blockers.
- [ ] Windows `.bat` and Linux shell launcher -> same Python core -> isolated venv -> version-checked SQLite per [local startup](backend/local-startup.md). Verify OS-specific locks/dependencies/process cleanup on both; macOS not now. Confirm versions/architectures/prerequisites; no global installs or silent resets.
- [ ] Before hosted/service activation, implement Supabase email/password login and idempotent auth-UUID profile initialization with display login; email verification/recovery policy remains open. This does not block the independent local no-account slice.
- [ ] Minimal API and UI showing stage, artifact, review, and failure.

Exit: accepted starts and decisions survive process death before invocation, after business commit, and during the next node; recovery produces no duplicate canonical artifacts, rejects stale decisions, and cannot continue cancelled production. The selected main frame is verified and promoted through an exact human receipt. An in-memory saver or a review-gate-only restart test is insufficient. The single-image provider cases from the [runtime acceptance matrix](backend/runtime.md#acceptance-matrix) apply now; multi-unit/video cases belong to phase 2.

## 2. First Rendered Cinematic

Current decision: local direct ComfyUI uses authorized file or `/view` import without hosted order auth/bucket; remote hosted uses private GCS and signed downloads followed by verified managed-file import. Browser-hosted project files remain server-side. MVP placeholder credits remain required for Kinodel service computation; product daily free limits are deferred, not credits.

- [ ] Extend the already-required Wardrobe/Storyboard main-frame path to full Storyboard shot frames, Filmmaker and Montage; do not defer the first main-frame planner to this phase.
- [ ] Implement the pre-designed visual/motion contracts and frozen prompt-guidance resources/projections; validate the entire unit mapping before render. These are agent resources, not deferred RAG discovery.
- [ ] One ComfyUI provider profile and workflow registry.
- [ ] Durable render jobs, external-wait resume, and output promotion.
- [ ] Remote hosted: private GCS output upload, unchanged 365-day outputs lifecycle, separate input/workflow/prompt-body policy, signed download renewal and verified import at project owner. Paid generated downloads have no arbitrary product quota; technical size/validation/timeouts and pre-order orphan/ownership checks remain required.
- [ ] MVP placeholder credits: image 1, video low/high 3/5, text input/output 1/2 per million tokens, free models 0, signup 100; integer microcredits, bounded reservations, authoritative usage and idempotent settlement/grant. Auth and technical anti-abuse/admission bounds remain required, not product daily quotas. No real payments. Disable any paid text path lacking reliable usage/reconciliation; do not invent capture or refund.
- [ ] MVP service order logs and durable order/request/settlement identities: no scheduled deletion; do not infer permanent retention of workflow/input/prompt bodies.
- [ ] Enable [new-execution rework](backend/rework.md) only after source-stability, reuse closure, entry and crash checks; unchanged prefix reuse is not checkpoint rewind.
- [ ] Parallel frame/clip fan-out with keyed reducer and deterministic join.
- [ ] Validated `MontagePlanV1` to ffmpeg execution service.
- [ ] Story, main-frame, frame, clip-selection, and final review loops.
- [ ] Craft and review `CinemaChunkV1` from approved output.

Exit: one cinematic project survives provider delay, restart, revision, and final human approval.

## 3. Product Runtime

- [ ] Runtime event stream with reconnect/deduplication.
- [ ] Extend baseline cancellation with operational controls and provider reconciliation visibility; render-job cancellation/reconciliation ships with phase 2.
- [ ] Multi-user authorization and expanded secret/audit operations; baseline Supabase authentication and technical safety ship with their paths. Product daily quotas belong only to Final Release TODOs below.
- [ ] Extend the phase-1 automatic launcher with release packaging and endpoint configuration; no separately administered PostgreSQL or mandatory Kinodel account locally. Docker is not a required product install path.
- [ ] Operational metrics for graph, model, provider, and storage failures.

Exit: a small external test group can run concurrent projects safely.

## 4. Knowledge And Context

- [ ] Extend the phase-1 direct resolver and projections to source/wiki/chunk libraries and richer mention picking; do not reimplement operation-scoped selection.
- [ ] Extend agent-resource coverage beyond the cinematic prompt-guidance resolver shipped in phase 2.
- [ ] Creative chunk candidate, memory review, promotion, revision, archive, and purge lifecycle.
- [ ] Immutable source manifest and maintained wiki workflow.
- [ ] Recursive lint and claim-level provenance.
- [ ] FTS library-discovery baseline when direct selection no longer scales.
- [ ] Gold retrieval/evidence evaluation set.
- [ ] One 768d Gemini Embedding 2 index if it beats FTS baseline.
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
- #future production: Google login, cards, top-ups, payment webhooks and subscriptions. Supabase email/password and signup 100 credits are MVP.
- #future: detailed onboarding, editors and branch-comparison UX; backend authorization, availability messages and review semantics remain current requirements.

- autonomous agent swarm;
- generic graph compiler before phase 5;
- graph database;
- four-tier MRL index;
- arbitrary agent terminal/filesystem access;
- full visual node editor;
- compatibility with legacy Hermes state files.
