# Kinodel IDE MVP Roadmap

## MVP objective

Ship a usable standalone app where a creator can:

1. choose `cinematic.v1`;
2. enter a vibe;
3. approve a BriefGate;
4. watch the graph create story, main frame, story frames, video clips, and montage;
5. approve ReviewGates;
6. receive final MP4 and reusable cinema chunk;
7. use local ComfyUI or a configured cloud provider.

## Phase 0 — Repo and docs foundation

- Finalize LangGraph-first architecture docs.
- Mark Hermes-era helpers as compatibility, not foundation.
- Keep cinematic pipeline spec as the baseline.
- Define service boundaries and project layout.

Exit gate:

- docs describe backend, UI, providers, RAG/chunks, and deployment path.

## Phase 1 — Backend skeleton

Build Python backend package:

- `PipelineRegistry`
- `ProjectStore`
- `GraphRuntime`
- `GateService`
- minimal `AgentService`
- minimal `RenderService` wrapper

Implement `cinematic.v1` graph using LangGraph.

Persistence:

- local dev: sqlite or in-memory checkpointer;
- production target: Postgres checkpointer.

Exit gate:

- graph can run through non-render mock stages and stop/resume at gates.

## Phase 2 — Artifact compatibility

Reuse current artifact contracts:

- `brief.json`
- `story.json`
- `wardrobe_request.json`
- `storyboard_requests.json`
- `video_requests.json`
- `render_results/*.json`
- `final_chunk.json`
- `chunks/cinema_chunk.json`

Add validators as backend services. Existing scripts can be imported or wrapped during migration.

Exit gate:

- one project can initialize and resume by `thread_id + project_id`.

## Phase 3 — Specialist nodes

Convert current specialist skill contracts into graph node calls:

- Storytell node;
- Wardrobe node;
- Storyboard node;
- Filmmaker node;
- Critic node;
- Craft node.

For the first pass, these can call one selected LLM provider and write artifacts. Later they become swappable agent adapters.

Exit gate:

- mock/no-render cinematic project creates valid planner artifacts.

## Phase 4 — Render integration

Wrap current render worker/provider modules behind `RenderService`.

Provider targets:

- local ComfyUI over HTTP;
- fal.ai fallback;
- future hosted Kinodel GPU endpoint.

Replace terminal wake-up semantics with:

```text
submit job
→ persist job ID
→ stream/status poll by backend
→ promote result manifest
→ resume graph thread
```

Exit gate:

- local ComfyUI or mock provider renders main frame and story frames and resumes to ReviewGate.

## Phase 5 — Open WebUI integration

Start with Open WebUI as the shell:

- expose Kinodel backend as external pipeline/service;
- show gate cards in chat;
- return media refs/attachments;
- support resume by project/thread.

Exit gate:

- user can run the cinematic MVP from Open WebUI without touching CLI.

## Phase 6 — Final media and chunk memory

Implement:

- video render stage;
- montage stage;
- final gate;
- `final_chunk.json`;
- `cinema_chunk` crafting and mock indexing.

Exit gate:

- complete cinematic project produces final MP4 and valid cinema chunk.

## Phase 7 — Product hardening

- Project dashboard.
- Media gallery.
- Render progress UI.
- Provider settings page.
- Error recovery panels.
- Auth/account/billing groundwork.
- Docker Compose for backend + Open WebUI + Postgres + optional ComfyUI connection.

Exit gate:

- first private alpha can be deployed.

## First deployment shape

Recommended MVP stack:

```text
open-webui container
kinodel-backend container
postgres container
optional redis container
local or remote comfyui
optional fal.ai API key
shared media volume
```

Environment:

- `DATABASE_URL`
- `KINODEL_PROJECTS_DIR`
- `COMFYUI_BASE_URL`
- `FAL_KEY` optional
- `OPENAI_API_KEY` or OpenRouter/local LLM provider config
- `KINODEL_PUBLIC_MEDIA_BASE_URL` when external providers need public refs

## What can wait

- visual node editor;
- subscription billing;
- hosted GPU autoscaling;
- global semantic RAG search;
- serial and music-video production;
- advanced dashboard analytics.

## Next best engineering start

Create the backend skeleton with a mocked render provider and real LangGraph gates. This proves the core value before fighting provider latency and UI polish.
