# Roadmap

Roadmap follows risk, not feature count. Each phase must leave a usable, testable vertical slice.

## 0. Foundation

- [x] Distill legacy architecture, agents, scripts, pipelines, and RAG decisions.
- [x] Define graph/agent/tool/artifact boundaries.
- [x] Define active and planned capability contracts.
- [x] Define cinematic, music-video, and serial pipeline topology.
- [x] Define minimal knowledge/retrieval architecture.
- [x] Choose Python for graph/backend runtime; retain TypeScript only for web UI/API consumers.
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

Exit: the first slice can be implemented without consulting legacy orchestration code, and later pipeline/RAG phases have explicit contracts to refine rather than unresolved ownership boundaries.

## 1. Restart-Safe HITL Slice

- [ ] Project/execution identity and graph registry.
- [ ] PostgreSQL Project DB: executions, operations, bindings, review requests, and leases.
- [ ] `AsyncPostgresSaver`, managed local project storage, and one resume-worker process.
- [ ] Artifact Store with immutable revisions, hashes, and slot bindings.
- [ ] Explicit `foundation.v0` graph: brief draft/review -> story/review.
- [ ] Producer, Storytell, and Critic node adapters with structured output.
- [ ] `interrupt()` and typed approve/revise/clarify/cancel resume.
- [ ] Idempotent artifact commit and stale-review rejection.
- [ ] Tests for commit-before-checkpoint replay, stale/duplicate review, fenced checkpoint writes, and execution lease recovery.
- [ ] Minimal API and UI showing stage, artifact, review, and failure.

Exit: stop the process at a review gate, restart it, resume once, and produce no duplicate artifacts.

## 2. First Rendered Cinematic

- [ ] Wardrobe, Storyboard, Filmmaker, and Montage planning adapters.
- [ ] Provider-payload-neutral visual/motion request schemas with frozen prompt-guidance profiles.
- [ ] One ComfyUI provider profile and workflow registry.
- [ ] Durable render jobs, external-wait resume, and output promotion.
- [ ] Parallel frame/clip fan-out with keyed reducer and deterministic join.
- [ ] Validated `MontagePlanV1` to ffmpeg execution service.
- [ ] Story, main-frame, frame, clip-selection, and final review loops.
- [ ] Craft and review `CinemaChunkV1` from approved output.

Exit: one cinematic project survives provider delay, restart, revision, and final human approval.

## 3. Product Runtime

- [ ] Runtime event stream with reconnect/deduplication.
- [ ] Cooperative cancellation and provider reconciliation.
- [ ] Auth, authorization, quotas, secrets, and audit boundaries.
- [ ] Docker-based local deployment and endpoint configuration.
- [ ] Operational metrics for graph, model, provider, and storage failures.

Exit: a small external test group can run concurrent projects safely.

## 4. Knowledge And Context

- [ ] Direct mention resolver, `ContextSelectionV1`, and per-agent compact projections.
- [ ] Agent-resource resolution for frozen generation profiles, including `@prompt-engine`.
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
