# Roadmap

Roadmap follows risk, not feature count. Each phase must leave a usable, testable vertical slice.

## 0. Foundation

- [x] Distill legacy architecture, agents, scripts, pipelines, and RAG decisions.
- [x] Define graph/agent/tool/artifact boundaries.
- [x] Define active and planned capability contracts.
- [x] Define cinematic, music-video, and serial pipeline topology.
- [x] Define minimal knowledge/retrieval architecture.
- [ ] Choose implementation language after a small LangGraph spike.
- [ ] Define executable Pydantic/Zod contracts for the first slice.

Exit: the brief/story slice can be implemented without consulting legacy orchestration code.

## 1. Restart-Safe HITL Slice

- [ ] Project/execution identity and graph registry.
- [ ] Artifact Store with immutable revisions, hashes, and slot bindings.
- [ ] Explicit `foundation.v0` graph: brief draft/review -> story/review.
- [ ] Producer and Storytell node adapters with structured output.
- [ ] `interrupt()` and typed approve/revise/cancel resume.
- [ ] Idempotent artifact commit and stale-review rejection.
- [ ] Unit tests for restart at every boundary and duplicate resume.
- [ ] Minimal API and UI showing stage, artifact, review, and failure.

Exit: stop the process at a review gate, restart it, resume once, and produce no duplicate artifacts.

## 2. First Rendered Cinematic

- [ ] Wardrobe, Storyboard, and Filmmaker adapters.
- [ ] Provider-neutral visual/motion request schemas.
- [ ] One ComfyUI provider profile and workflow registry.
- [ ] Durable render jobs, external-wait resume, and output promotion.
- [ ] Parallel frame/clip fan-out with keyed reducer and deterministic join.
- [ ] ffmpeg Montage service.
- [ ] p4, p7, and final review loops.
- [ ] Craft `CinemaChunkV1` from approved output.

Exit: one cinematic project survives provider delay, restart, revision, and final human approval.

## 3. Product Runtime

- [ ] Postgres checkpointer and per-thread invocation lock.
- [ ] Object storage and managed asset delivery.
- [ ] Runtime event stream with reconnect/deduplication.
- [ ] Cooperative cancellation and provider reconciliation.
- [ ] Auth, authorization, quotas, secrets, and audit boundaries.
- [ ] Docker-based local deployment and endpoint configuration.
- [ ] Operational metrics for graph, model, provider, and storage failures.

Exit: a small external test group can run concurrent projects safely.

## 4. Knowledge And Context

- [ ] Immutable source manifest and maintained wiki workflow.
- [ ] Recursive lint and claim-level provenance.
- [ ] Direct reference and FTS retrieval baseline.
- [ ] Gold retrieval/evidence evaluation set.
- [ ] One 768d Gemini Embedding 2 index if it beats FTS baseline.
- [ ] User-selected chunks/assets and compact per-agent projections.
- [ ] Image/PDF representations only where evaluation proves value.
- [ ] Archive and purge lifecycle.

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
