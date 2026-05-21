# Kinodel IDE

**Kinodel** is an open-source runtime-vibe-factory for creators.

The vision is a webapp where a creator can open one idea, choose the vibe, and let a crew of AI subagents help make it beautiful: stories, visuals, videos, music, episodes, worlds, and reusable creative memory.

Under the hood, Kinodel breaks production into clean stages: story, visual anchors, storyboard frames, video shots, montage, and final chunks. Each stage has its own specialist agent, its own artifact, and its own place in the pipeline.

Core vibe:

```text
Producer routes.
Subagents create.
Artifacts remember.
Gates keep control.
Render workers grind.
Chunks carry the finished magic forward.
```

## What is inside

```text
skills/kinodel/
  pipeline-kinodel/          architecture law, pipeline specs, templates
  producer-kinodel/          runtime orchestrator and state machine helpers
  kinodel-project-layout/    project initializer and layout contracts
  storytell-kinodel/         story planning specialist
  wardrobe-kinodel/          main-frame / visual anchor planner
  storyboard-kinodel/        story image request planner
  filmmaker-kinodel/         video request planner
  render-kinodel/            provider-neutral render worker layer
  montage-kinodel/           final video assembly stage
  critic-kinodel/            optional QC / edit-fix notes
  comfyui/                   local ComfyUI workflows and helpers
```

## Runtime pipeline

The current canonical route is `cinematic.v1`:

```text
BriefGate
→ brief.json
→ story.json
→ wardrobe_request.json
→ main_frame render
→ ReviewGate p4
→ storyboard_requests.json
→ story images render
→ ReviewGate p7
→ video_requests.json
→ video render
→ montage
→ final_chunk.json
```

This is not a loose prompt chain. It is a staged production graph with explicit ownership:

- **Producer**: talks to the user, validates state, launches workers, enforces gates.
- **Specialists**: write exactly one owned artifact and return compact status.
- **Render**: consumes provider-neutral request artifacts and owns provider payloads.
- **Montage**: assembles validated video refs into the final MP4.
- **Final chunk**: stores the sealed creative result, not debug logs or process noise.

## Subagent architecture

Kinodel is designed around fresh subagent contexts.

The main Producer stays small:

```text
project_id
current_goal
artifact paths
pending gate
selected media refs
```

Creative work is delegated through compact handoff envelopes:

```text
delegate_task(owner_skill)
→ read listed artifacts
→ write owned artifact
→ preserve project_id
→ set status=complete
→ return only status/path/summary
```

This keeps context clean, improves prompt-cache locality, and prevents one giant chat from becoming the production database.

## Artifact-first state

Durable production state lives in files:

```text
~/projects/<project_id>/v1/
  brief.json
  story.json
  wardrobe_request.json
  storyboard_requests.json
  video_requests.json
  render_results/
  qc/
  outputs/
  final_chunk.json
```

Important rules:

- **Every durable artifact carries `project_id`.**
- **`status=pending` is not production-ready.**
- **Render result manifests, not `outputs/` scans, are the chaining truth.**
- **Provider payloads, queue IDs, logs, costs, retries, and scratch state stay out of planner artifacts.**
- **`final_chunk.json` contains only the finished cinematic memory.**

## Gates

Kinodel uses text-first hard stops:

- **BriefGate**: confirms production format before project initialization.
- **ReviewGate p4**: story + main frame approval.
- **ReviewGate p7**: story images approval.

Render completion never means approval.

At gates, the user decides:

```text
A — approve
B — auto-fix via critic
C — edit-fix with notes
D — stop
```

This makes the runtime safe to resume across chats, terminals, and long render jobs.

## Render layer

`render-kinodel` is provider-neutral at the contract boundary.

Planner agents write requests like:

```text
kind
render_prompt
input_media
output_name
stage
```

The render worker owns provider mapping, retries, events, result manifests, and output promotion.

Supported direction in this snapshot:

- **Local ComfyUI** workflows for image and video paths.
- **fal.ai** workflows as optional/fallback adapters.
- **Background render execution** with result files and wakeup/copy validation.

## Pipeline specs

The repo already contains the beginning of a flexible runtime layer:

```text
pipeline_spec.v1
cinematic.v1.json
CompiledRoute
producer_state.json
capability contracts
project-local pipeline specs
```

The goal is to move from one hardcoded cinematic route to a family of validated production graphs.

Current route: **cinematic short video**.

Next planned routes:

- **Serial season development**: `season-kinodel` designs a season bible, arcs, episodes, hooks, cliffhangers, and payoffs.
- **Serial episode production**: `episode-kinodel` turns an approved season chunk into detailed per-episode production.
- **Music video / Muse path**: `muse` plans music, vibe, lyrics, audio chunks, and future clip generation around sound.

These agents are documented in the private wiki now; the fresh runtime patch is not applied in this repo snapshot yet.

The intended future output is chunk-native:

```text
season_chunk.json
episode_chunk.json
avatar_chunk.json
music_chunk.json
final_chunk.json
```

Chunks are the durable memory layer: compact, reusable, and safe to feed into the next pipeline without dragging the whole production trace behind them.

## Future: LangGraph

Kinodel is moving toward a graph-native runtime built on:

https://github.com/langchain-ai/langgraph.git

Why LangGraph fits:

- **Staged graph execution**
- **Resumable state**
- **Explicit checkpoints**
- **Human-in-the-loop gates**
- **Typed edges between specialist agents**
- **Durable artifact validation between nodes**
- **Long-running render jobs as external worker nodes**

The current skillpack is the production logic before the graph runtime becomes the execution engine.

## Design principles

- **Artifact-centric over chat-centric.**
- **Specialist ownership over monolithic prompting.**
- **Provider-neutral planning over provider-leaked artifacts.**
- **Hard user gates over autonomous drift.**
- **Compact handoffs over context bloat.**
- **Final chunks over process archives.**
- **Runtime specs over ad-hoc pipelines.**

## Status

This is an early public commit of the Kinodel skills runtime.

It is not polished as an installable product yet.
It is a working architecture snapshot: skills, contracts, templates, scripts, tests, render adapters, and the direction of a future graph-based AI production system.
