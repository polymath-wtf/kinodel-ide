---
title: Kinodel Patch Implementation Plan — phased index
created: 2026-05-17
updated: 2026-05-23
type: query
tags: [kinodel, roadmap, agent-architecture, pipeline, workflow, patch]
sources:
  - [[kinodel-pipeline-runtime]]
  - [[kinodel-flexible-pipeline-patch]]
  - [[serial-pipeline]]
  - [[music-video-pipeline]]
  - [[kinodel-rag-chunk-architecture]]
  - [[kinodel-patch-phase-rag]]
  - [[create-pipeline]]
  - [[suno-api-guide]]
  - current-skills:kinodel/pipeline-kinodel
  - current-skills:kinodel/producer-kinodel
  - current-skills:kinodel/kinodel-project-layout
confidence: high
contested: false
contradictions: []
---

# Kinodel Patch Implementation Plan — phased index

This file is intentionally short. The old monolithic patch plan was too large for safe one-pass execution, so implementation is split into focused phase files. Each phase file starts with a copy-paste prompt for a GPT/Hermes agent and must be executed in order.

## Read order for any implementation chat

1. Read this index.
2. Read only the current phase file.
3. Inspect linked architecture pages only as needed.
4. Implement only the current phase.
5. Run the phase test gate.
6. Stop and summarize changed files, tests, and explicit non-changes.

## Phase discipline

- Do not combine phases in one implementation pass.
- A phase is not complete until its **Test gate** passes.
- If a test gate exposes a compatibility problem, stop and fix that phase only.
- Live skills are patched only after the relevant docs/specs are internally consistent.
- Every implementation summary must list:
  - changed files;
  - tests run and exact result;
  - explicit non-changes / out-of-scope items;
  - next phase readiness.

## Non-negotiable migration laws

1. Backward compatibility first: current cinematic p0-p11 must continue to work exactly.
2. Producer remains state machine, not creative warehouse.
3. Specialists write owned artifacts to disk and return status only.
4. Render executes explicit request artifacts; creative agents do not call providers directly.
5. Durable artifacts must stay provider-neutral: no queue URLs, raw provider payloads, retries, logs, costs.
6. BriefGate, p4, and p7 remain hard stops. `checkpoint` is a semantic label, not auto-approval permission.
7. Pipeline specs declare stage graph; agent contracts declare capabilities. Producer binds and validates.
8. Chunks enter handoffs by ID/path/compact summary, not by dumping full media/history into prompts.
9. ComfyUI remains backup/special workflow adapter; fal.ai defaults remain cinematic baseline unless a pipeline spec explicitly selects another workflow.
10. No live skill rewrite should be attempted until schema/spec/runtime compatibility tests exist.
11. Spec-based projects cannot pass review gates by artifact existence alone; explicit gate decision state is required.
12. RAG is retrieval/cache infrastructure, not canon. Durable chunks remain source of truth.
13. Render workers do not query broad RAG; they receive explicit request artifacts and selected media refs.

## Canonical MVP decisions

Pipeline IDs:

- `cinematic.v1` — compatibility mirror of current hardcoded p0-p11 cinematic route.
- `serial_season.v1` — Stage 1 serial development, ends in [[season-chunk]].
- `serial_episode.v1` — Stage 2 one-episode production, ends in [[episode-chunk]].
- `music_video.v1` — Muse + Suno/music + timed visual/video pipeline.
- `renovation_timelapse.v1` — test/draft pipeline created by [[create-pipeline]] in Phase F, not active production until separately approved.

Avoid ambiguous `serial.v1` for MVP. Later it may become a parent/orchestrator, but not during this patch.

Gate model:

- p4/p7 aliases remain hard STOP_AT_GATE.
- Spec gates must use `type: review_gate` and `stop: true`.
- New spec projects need explicit gate decision state; old cinematic projects may keep p4/p7 heuristic fallback only as legacy compatibility.

Music ownership:

- [[agent-muse-kinodel]] writes `muse_output.json` and provider-neutral `music_request.json` using [[suno-api-guide]] as provider-shape reference.
- Render/audio adapter writes `outputs/music.mp3` and `music_result.json` / `render_results/music_result.json`.
- Muse must not call providers directly.

Producer pipeline selection:

- New projects use a PipelineChoiceGate before BriefGate/init_project.
- `cinematic.v1` is the default for legacy-compatible cinematic/reels briefs.
- Non-cinematic choices are offered only when their phase has made them active; before that they are shown as planned/locked.

## Implementation phases

### Phase A — Spec and validator only

File: [[kinodel-patch-phase-a-spec-validator]]

Core feature: introduce `pipeline_spec.v1`, `cinematic.v1`, and validator. No runtime behavior change.

Important: `cinematic.v1` is the saved compatibility mirror of the current hardcoded p0-p11 route. `pipeline-kinodel` must not be converted into a cinematic-only skill; it remains universal law/runtime architecture.

Stop after: cinematic spec validates and no production commands changed.

### Phase B — Producer reads spec with hardcoded fallback

File: [[kinodel-patch-phase-b-producer-runtime]]

Core feature: make `state_guard.py` spec-aware through `CompiledRoute`, while preserving old cinematic fallback and behavior.

Stop after: old cinematic next-goal/handoff behavior is equivalent, spec projects cannot pass gates by artifact existence, and p4/p7 hard-stop remains intact.

### Phase C — Layout profiles, contracts, templates, PipelineChoiceGate

File: [[kinodel-patch-phase-c-layout-contracts-templates]]

Core feature: add safe layout profiles, project-local `pipeline_spec.json`, `producer_state.json`, PipelineChoiceGate, current-worker capability contracts, and canonical render request templates.

Stop after: cinematic init still works, `cinematic.v1` validates against active contracts, non-cinematic profiles are not active before D/E, and Producer can select/store pipeline_id before BriefGate/init_project.

### Phase RAG — Full chunk crafting, indexing, and resolver foundation

File: [[kinodel-patch-phase-rag]]

Core feature: real chunk/RAG substrate before non-cinematic activation: crafted chunk schemas, token guard, Gemini Embedding 2 adapter, local indexer, resolver, and `context pack` contract.

Stop after: cinematic still validates, chunk schemas/token guard/resolver dry-run tests pass, and Phase D/E can consume selected chunk paths / optional context pack instead of temporary chunk handoff hacks.

### Phase D — Serial MVP on top of RAG chunks

File: [[kinodel-patch-phase-d-serial-chunks]]

Core feature: Wardrobe multi-anchor capability, `serial_season.v1`, `serial_episode.v1`, Season/Episode contracts, and serial runtime binding to Phase RAG `chunk_resolver`.

Stop after: serial specs validate, serial handoffs include compact selected chunk paths / optional context pack, p4/p7 hard-stop, and cinematic remains unaffected.

### Phase E — Music video and Suno/music render path on top of RAG chunks

File: [[kinodel-patch-phase-e-music-video]]

Core feature: render adapter/workflow registry for music, `music_video.v1`, Muse/audio request contracts, Suno-compatible provider-neutral `music_request.json`, and Muse handoff using selected `music_chunk` context.

Stop after: music video validates, Muse remains planner-only, Render/audio adapter owns provider calls and `outputs/music.mp3`, and cinematic/serial regressions still pass.

### Phase F — create-pipeline and renovation_timelapse draft/test

File: [[kinodel-patch-phase-f-create-pipeline-renovation]]

Core feature: `create-pipeline` spec drafting support and a test/draft `renovation_timelapse.v1` generated through that path.

Stop after: create-pipeline drafts specs without applying them; renovation_timelapse exists as draft/test output only unless separately approved.

## Verification checklist for every phase

- Existing cinematic project still resumes correctly when the phase touches runtime behavior.
- `state_guard.py next-goal` does not skip p4/p7 unless explicit diagnostics `--skip-gates` exists and is intentionally used.
- Spec-based projects require explicit gate decisions; render/result artifact existence alone is not approval.
- Render requests are envelopes with `schema`, `project_id`, `status`, `stage`, `jobs`.
- Render result manifests expose `selected_outputs`; downstream never scans `outputs/` as source of truth.
- Pipeline-specific artifacts are declared in spec, not inferred by newest file.
- Specialist handoffs are path-based and compact.
- New docs do not contradict hard STOP_AT_GATE rule.
- Chunks are referenced through selected chunk paths / optional context pack, not pasted wholesale.
- RAG indexes are derived cache/search infrastructure; durable chunks are source of truth.
- `gemini-embedding-2` calls use stable document/query prefixes and explicit `output_dimensionality`, not API `task_type`.
- ComfyUI workflow details stay in render adapters/workflows, not planner prose.
- `cinematic.v1` remains a compatibility mirror of current p0-p11.

## Known risks to watch

1. `state_guard.py` is the main executable bottleneck: too much hardcoded cinematic state.
2. `init_project.py` currently creates fixed cinematic stubs; layout profiles must be backward-compatible.
3. `render_wakeup.py` and `copy_worker_result.py` may silently route to wrong cinematic destinations if dynamic stages are added without updating them.
4. Legacy templates can mislead agents into writing bare arrays/jobs.
5. Wardrobe is explicitly “ONE composite anchor” today; multi-anchor must be an intentional capability upgrade.
6. Music generation must not violate Render ownership.
7. Serial production needs explicit invalidation policy for edits to completed episodes.
8. Phase F renovation_timelapse is a create-pipeline test/draft, not automatic production activation.

## Architecture refs

- [[kinodel-pipeline-runtime]] — runtime architecture and two-level contracts.
- [[kinodel-flexible-pipeline-patch]] — original flexible pipeline concept.
- [[serial-pipeline]] — two-stage serial design.
- [[music-video-pipeline]] — music-video design target.
- [[kinodel-rag-chunk-architecture]] — final chunk/RAG architecture and Gemini Embedding 2 policy.
- [[kinodel-patch-phase-rag]] — shared RAG foundation before Phase D/E.
- [[suno-api-guide]] — Suno provider guide used by Phase E to shape provider-neutral `music_request.json`.
- [[create-pipeline]] — future analyzer/spec designer.
- [[avatar-chunk]], [[music-chunk]], [[season-chunk]], [[episode-chunk]], [[cinema-chunk]] — chunk taxonomy.
- [[agent-muse-kinodel]], [[agent-season-kinodel]], [[agent-episode-kinodel]] — specialist design pages.

