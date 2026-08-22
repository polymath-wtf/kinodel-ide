# Kinodel IDE Docs

Kinodel IDE is a standalone human-in-the-loop generative production app for creators. It turns a user vibe into a controlled state-machine production: brief, story, visual anchors, story frames, video, montage, final memory, and reusable RAG chunks.

The next-generation foundation is **LangGraph-first**:

- pipeline specs compile into graph nodes and edges;
- ReviewGates use durable `interrupt()` / resume semantics;
- project state is artifact-centric and compact;
- render providers are adapters behind `RenderService`;
- Open WebUI is the initial UI shell;
- ComfyUI is the default local provider path, with fal.ai / hosted GPU endpoints as optional providers.

## Documents

- `architecture.md` — target architecture, services, graph state, pipeline families.
- `langgraph-runtime.md` — runtime compilation model, node patterns, services, and pause/resume behavior.
- `artifact-contracts.md` — durable artifact ownership, request/result contracts, and validators.
- `skill-refactor-plan.md` — how the old Kinodel skills map to the new LangGraph backend.
- `rag-and-chunks.md` — chunk strategy for cinema/avatar/music/season/episode memory.
- `uiux.md` — Open WebUI MVP shell plus future dashboard, graph editor, and media board UX.
- `mvp-roadmap.md` — deployment roadmap for the first MVP.
