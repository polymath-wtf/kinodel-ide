# Kinodel LangGraph Runtime

This reference is the foundation for rebuilding Kinodel IDE as a standalone human-in-the-loop generative app.

## Core insight

Everything that used to be a Hermes `/goal`, helper script, wake-up bridge, or manual routing rule is the same thing underneath:

```text
pipeline_spec stage -> LangGraph node -> validator -> edge / interrupt
```

The graph should own order, branching, pause/resume, and persistence. Skills and agents should only own taste, artifact contracts, and provider boundaries.

## What LangGraph replaces

| Hermes-era construct | LangGraph replacement |
| --- | --- |
| `/goal pN_*` command discipline | stable graph node IDs from `pipeline_spec.stages[]` |
| `producer_step.py` hot-path router | compiled graph edges and conditional routing |
| `state_guard.py next-goal` as runtime brain | validators plus graph checkpoint state |
| manual ReviewGate turn stops | `interrupt(gate_card)` and `Command(resume=decision)` |
| chat-memory gate approvals | persisted graph state/checkpointer records |
| terminal wake-up continuation logic | render job event updates graph state and resumes thread |
| `delegate_task` as orchestration primitive | specialist nodes/subgraphs with typed artifact handoffs |
| hardcoded cinematic maps | `PipelineRegistry` + frozen project-local `pipeline_spec.json` |

The existing helper scripts can remain during migration as diagnostics, validators, and compatibility adapters, but they must not be the design center of the standalone app.

## Canonical graph state

Keep state small and durable:

```json
{
  "project_id": "project",
  "project_dir": "/abs/projects/project/v1",
  "pipeline_id": "cinematic.v1",
  "current_stage": "p4_story_main_gate",
  "pending_gate": {"gate_id": "p4", "label": "Story/Main Frame ReviewGate"},
  "artifacts": {
    "brief": "brief.json",
    "story": "story.json"
  },
  "selected_media": {
    "main_frame": [{"path": "outputs/main_frame.png", "url": "https://..."}]
  },
  "gate_decisions": [],
  "chunk_refs": [],
  "last_error": null
}
```

Do not put full JSON bodies, provider payloads, render logs, vector hits, media blobs, or chat history into graph state.

## Node patterns

### Gate node

Gate nodes surface a JSON-serializable card with preview refs and choices:

```text
interrupt({
  "type": "review_gate",
  "gate_id": "p7",
  "preview_refs": [...],
  "choices": ["A", "B", "C", "D"]
})
```

On resume:

- `A` records approval and routes downstream.
- `B` routes to critic/fix loop.
- `C` routes edit notes to the owner stage.
- `D` pauses/stops without downstream work.

### Agent stage node

An agent node receives:

- project ID and directory;
- declared `reads`;
- declared `writes`;
- selected media refs;
- selected chunk/context-pack refs;
- optional edit notes.

It reads authoritative artifacts from `ProjectStore`, writes exactly one owned artifact, and returns status/path/summary.

### Render stage node

A render node only consumes complete provider-neutral request artifacts. It submits jobs through `RenderService`, persists scratch provider details outside graph state, and writes compact `render_results/*.json` manifests.

Long renders should not keep a request thread busy. Use a job ID/event model:

```text
submit render -> state render_job_id -> return/stream progress
provider event/result -> promote manifest -> resume graph thread
```

### Chunk node

Chunk nodes call Craft/Chunk services after approval. They produce durable `*_chunk.json` artifacts and optional index records. RAG outputs are derived support, never source of truth.

## Service split

- `PipelineRegistry` loads active specs and freezes a copy into projects.
- `ProjectStore` owns layout, atomic JSON writes, artifact refs, and media paths.
- `GraphRuntime` compiles specs into `StateGraph`s and owns checkpointer/thread IDs.
- `GateService` builds gate cards and parses decisions.
- `AgentService` wraps specialist agents/subgraphs.
- `RenderService` normalizes requests, dispatches ComfyUI/fal/local GPU jobs, and promotes results.
- `MontageService` assembles final media.
- `ChunkService` crafts and indexes cinema/avatar/music/season/episode chunks.
- `ProviderRegistry` binds provider/workflow capabilities.
- `NotificationService` streams progress and media previews to Open WebUI or future UI.

## Pipeline extensibility

New production families should add specs and contracts, not copy the cinematic runtime:

- `cinematic.v1`
- `music_video.v1`
- `serial_season.v1`
- `serial_episode.v1`
- future `renovation_timelapse.v1`

Every variant is still the same graph pattern: declared stages, artifact contracts, validators, hard gates, render boundaries, final/chunk outputs.

## Migration stance

Keep existing scripts until the backend exists, but demote them:

- `state_guard.py`: validator/diagnostic compatibility module;
- `producer_step.py`: legacy router shim;
- `render_wakeup.py`: legacy bridge until job events resume graph threads;
- `delegate_task`: legacy specialist execution shim.

Do not add more per-stage scripts, per-stage wake-ups, or hand-rolled route ledgers.
