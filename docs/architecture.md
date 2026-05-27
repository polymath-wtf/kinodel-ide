# Kinodel IDE Architecture

## Product model

Kinodel IDE is a creator-facing generative production studio:

```text
user chooses pipeline
→ gives vibe / refs / constraints
→ LangGraph runtime runs a typed production graph
→ specialist agents write artifacts
→ render providers create media
→ human gates approve checkpoints
→ final media + reusable chunks are archived
```

The metaphor is cinema production. Producer orchestrates; specialists own stage craft; Render owns providers; Craft owns reusable memory.

## Core simplification

Old Kinodel used many Hermes-era control aids: `/goal`, `producer_step.py`, `state_guard.py`, `delegate_task`, render wake-up scripts, and hardcoded cinematic maps.

The next foundation collapses them into one abstraction:

```text
pipeline_spec stage = LangGraph node with declared inputs, outputs, validator, and edge policy
```

That single abstraction removes most manual route enforcement.

## Backend runtime

Use LangGraph as the backend state-machine framework.

### Required LangGraph features

- **StateGraph** for deterministic stage graph compilation.
- **Checkpointer** for durable pause/resume.
- **Thread ID** per project/session.
- **interrupt()** for BriefGate and ReviewGates.
- **Command(resume=...)** for user decisions.
- **Conditional edges** for approve/edit/critic/stop flows.
- **Send / fan-out** later for parallel render or batch analysis where safe.

Development can start with sqlite or memory checkpointing. Production should use Postgres-backed persistence.

## Compact graph state

Graph state stores pointers, not warehouse data:

```json
{
  "project_id": "demo",
  "project_dir": "/projects/demo/v1",
  "pipeline_id": "cinematic.v1",
  "current_stage": "p7_story_images_gate",
  "pending_gate": {"gate_id": "p7"},
  "artifacts": {},
  "selected_media": {},
  "gate_decisions": [],
  "chunk_refs": [],
  "last_error": null
}
```

Forbidden in graph state:

- full large artifacts;
- provider payloads;
- raw logs;
- render queue internals;
- base64 media;
- broad vector hits;
- full chat history.

## Service split

### PipelineRegistry

Loads active pipeline specs:

- `cinematic.v1`
- planned `music_video.v1`
- planned `serial_season.v1`
- planned `serial_episode.v1`

It freezes a copy of the selected spec into the project for reproducible runs.

### GraphRuntime

Compiles a selected pipeline spec into a LangGraph `StateGraph`, binds nodes to services, and owns checkpoint/resume behavior.

### ProjectStore

Owns project layout, artifact paths, atomic JSON writes, validation reads, and stable media refs.

### GateService

Builds user-facing gate cards and parses decisions:

- `A` approve;
- `B` auto-fix via critic;
- `C` edit-fix with notes;
- `D` stop/pause.

### AgentService

Runs specialist agents as typed nodes/subgraphs. It passes artifact paths, selected media refs, and selected chunks/context packs. It does not paste huge project dumps.

### RenderService

Executes provider-neutral render requests via adapters:

- local ComfyUI over HTTP;
- fal.ai;
- future hosted GPU/Comfy endpoint;
- future audio/video providers.

Render keeps provider runtime details in scratch/job storage and promotes only compact `render_results/*.json`.

### MontageService

Assembles approved clips into final MP4.

### ChunkService

Crafts and indexes reusable chunks:

- `cinema_chunk`;
- `avatar_chunk`;
- `music_chunk`;
- `season_chunk`;
- `episode_chunk`.

Chunks are RAG memory, not production logs.

### NotificationService

Streams graph progress, gate cards, media previews, render statuses, and final delivery to Open WebUI and future UI.

## Initial UI shell

Open WebUI is the first UI because it already provides:

- chat UX;
- auth/users;
- model/provider abstraction;
- file/knowledge features;
- admin settings;
- Docker deploy path.

Kinodel can initially integrate as an external pipeline/backend service. Later UI work can add:

- project dashboard;
- media gallery;
- visual node graph;
- gate review panels;
- provider/account/billing controls.

## Provider strategy

Default path:

- local ComfyUI via HTTP for users who git clone and run locally;
- optional fal.ai for cloud convenience;
- future hosted Kinodel GPU endpoint for subscription users.

Provider payload ownership stays inside RenderService/provider adapters. Planner agents write provider-neutral request artifacts only.

## Hard invariants

- BriefGate and ReviewGates are human gates, not render-completion events.
- Specialists write only their owned artifacts.
- Render never invents prompts or queries broad RAG.
- RAG/chunks inspire and preserve continuity; they do not override active project truth.
- `final_chunk.json` and crafted chunks are final memory, not production trace.
- `outputs/` is storage/cache; `render_results/*.json.selected_outputs` is chaining truth.
