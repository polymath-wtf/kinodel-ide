# Roadmap

Roadmap follows risk, not feature count. Each phase must leave a usable, testable vertical slice.

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
- [ ] Define executable Pydantic contracts for the first slice.
- [ ] Author the exact `foundation.v0` route table: approve/revise/clarify/cancel, Critic-mediated edits, bounded loops, blocked results, completion, and failure ownership.
- [ ] Freeze identity and recovery semantics: pipeline ID/version/digest, operation IDs and input digests, idempotent execution start, lease fencing, and durable resume states.
- [ ] Define the managed-file/Project-DB commit protocol, including content-addressed writes, committed metadata, replay checks, and orphan cleanup.
- [ ] Define durable review and approval semantics for one exact current-stage subject, including stale detection, Critic-mediated edits, clarification, asset/take selection, and downstream approval lookup.
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
- [ ] PostgreSQL Project DB: executions, operations, bindings, review requests, leases, `execution_work`, and `execution_controls`.
- [ ] `AsyncPostgresSaver`, managed local project storage, and one worker for start/resume/reconcile/cancel; API never invokes the graph.
- [ ] Artifact Store with immutable revisions, hashes, and slot bindings.
- [ ] Explicit `foundation.v0` graph: brief draft/review -> story/review.
- [ ] Static versioned capability/mode registry with enabled-schema/context/modality validation; activate Producer, Storytell, and Critic node adapters with structured output, using the full catalog's common contract.
- [ ] Direct typed-reference resolution and `ContextSelectionV1` persisted before calls, including empty optional selections, exact revisions, and per-agent projections; no discovery/index dependency.
- [ ] Explicit first-deployment access mode, project authorization, managed-path isolation, input validation, and credential separation before accepting executions.
- [ ] Baseline cancellation: durable acceptance, reject later decisions/production commits, worker finalization, and recovery after cancellation.
- [ ] `interrupt()` and typed approve/revise/clarify/cancel resume.
- [ ] Idempotent artifact commit and stale-review rejection.
- [ ] Real-PostgreSQL crash tests for accepted-start recovery, commit-before-checkpoint replay, consumed-response/unfinished-next-node recovery, stale/duplicate review, single-writer checkpoint ownership, cancellation races, and pinned context.
- [ ] Minimal API and UI showing stage, artifact, review, and failure.

Exit: accepted starts and decisions survive process death before invocation, after business commit, and during the next node; recovery produces no duplicate canonical artifacts, rejects stale decisions, and cannot continue cancelled production. An in-memory saver or a review-gate-only restart test is insufficient. See the [runtime acceptance matrix](backend/runtime.md#acceptance-matrix); provider cases belong to phase 2.

## 2. First Rendered Cinematic

- [ ] Wardrobe, Storyboard, Filmmaker, and Montage planning adapters.
- [ ] Implement the pre-designed visual/motion contracts and frozen prompt-guidance resources/projections; validate the entire unit mapping before render. These are agent resources, not deferred RAG discovery.
- [ ] One ComfyUI provider profile and workflow registry.
- [ ] Durable render jobs, external-wait resume, and output promotion.
- [ ] Parallel frame/clip fan-out with keyed reducer and deterministic join.
- [ ] Validated `MontagePlanV1` to ffmpeg execution service.
- [ ] Story, main-frame, frame, clip-selection, and final review loops.
- [ ] Craft and review `CinemaChunkV1` from approved output.

Exit: one cinematic project survives provider delay, restart, revision, and final human approval.

## 3. Product Runtime

- [ ] Runtime event stream with reconnect/deduplication.
- [ ] Extend baseline cancellation with operational controls and provider reconciliation visibility; render-job cancellation/reconciliation ships with phase 2.
- [ ] Multi-user authentication/authorization, quotas, and expanded secret/audit operations; baseline access and credential boundaries already ship in phase 1.
- [ ] Docker-based local deployment and endpoint configuration.
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

## Explicitly Not On The Critical Path

- autonomous agent swarm;
- generic graph compiler before phase 5;
- graph database;
- four-tier MRL index;
- arbitrary agent terminal/filesystem access;
- full visual node editor;
- compatibility with legacy Hermes state files.
