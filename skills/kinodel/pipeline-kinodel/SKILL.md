---
name: pipeline-kinodel
description: LangGraph-first Kinodel pipeline law: graph stages, artifact boundaries, ReviewGates, and active pipeline specs.
---

# Pipeline-Kinodel

Kinodel is an artifact-centric AI filmmaking factory. This skill owns the production contract, not provider payloads or runtime orchestration.

## Foundation

Every production step is a typed graph stage:

```text
pipeline_spec.stages[] -> LangGraph node -> validator -> static edge or interrupt
```

The graph owns order, branching, pause/resume, retries, persistence, and wake-up from async jobs. Agents own artifacts and taste.

## Non-negotiable laws

- **Compact graph state** — store paths, refs, decisions, and errors; never store full artifacts, logs, media blobs, provider payloads, or chat history.
- **Artifact ownership** — each specialist writes exactly its declared artifact and returns only status/path/summary.
- **Gates are interrupts** — BriefGate, p4, p7, and p12 are human-in-the-loop stops using `interrupt()` and resume decisions.
- **Render boundary** — planner artifacts are provider-neutral; provider IDs, queue URLs, raw responses, retries, logs, and costs stay in RenderService scratch.
- **Selected refs are truth** — downstream stages chain from `render_results/*.json.selected_outputs`, not by scanning `outputs/`.
- **Final memory is minimal** — `final_chunk.json` contains final cinematic refs/story only, not production trace.
- **RAG is derived** — chunks/context packs can support agents, but active project truth is the frozen spec plus approved artifacts.

## Stage types

- `briefgate` — builds and confirms the initial user-visible brief card before project creation.
- `agent_stage` — calls one owner skill or subgraph with declared reads/writes.
- `render_stage` — submits a complete render request artifact to RenderService and promotes a compact result manifest.
- `review_gate` — creates a gate card and interrupts until the user replies A/B/C/D.
- `montage_stage` — deterministic assembly of selected video refs.
- `chunk_write_stage` — writes final/project memory from approved artifacts.

## Cinematic route

```text
p0 BriefGate
-> p1 story.json
-> p2 wardrobe_request.json
-> p3 main_frame render
-> p4 Story/Main Frame ReviewGate
-> p5 storyboard_requests.json
-> p6 story frames render
-> p7 Story Images ReviewGate
-> p8 video_requests.json
-> p9 video render
-> p10 montage final.mp4
-> p11 final_chunk.json
-> p12 Final ReviewGate
-> p13 chunks/cinema_chunk.json
```

The active machine-readable baseline is `pipelines/cinematic.v1.json`.

## Refactor rule

A migration step is valid only if it replaces a hardcoded decision with one of:

- **Typed spec field** — stage type, reads, writes, validators, owner, support skills, selected refs, gate policy.
- **Graph edge** — deterministic stage order or conditional gate path.
- **Service method** — project store, render, montage, notification, chunking, provider registry.
- **Validator** — schema/status/project/media/ref invariant.

If a rule cannot fit there, it is product behavior and needs a small contract, not more Producer prose.