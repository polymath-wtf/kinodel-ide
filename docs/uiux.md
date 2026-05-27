# Kinodel UI/UX

## Product shape

Kinodel starts inside Open WebUI because it already gives us chat, users, model connections, file upload, admin settings, and deploy ergonomics. The Kinodel-specific UI should grow as production panels around the LangGraph backend, not as another chat-only prompt wrapper.

## UX principle

```text
chat is the director interface
dashboard is the production board
graph is the pipeline editor
media board is the review room
```

Open WebUI is the shell. Kinodel owns the production experience.

## MVP inside Open WebUI

### Chat production thread

- **Start** — user selects `cinematic.v1` and writes a vibe.
- **BriefGate card** — backend returns a compact approval card with A/B/C/D choices.
- **Progress events** — stage updates stream as short status messages.
- **Media previews** — render results appear as attachments/links as soon as they are selected.
- **ReviewGate cards** — p4, p7, and p12 are visible approval blocks.
- **Resume** — user's next message resumes the same LangGraph thread with `Command(resume=...)`.

### Gate card layout

```text
ReviewGate — Story Images

Preview
- shot_01.png
- shot_02.png
- shot_03.png

Reply with one letter:
A — approve this gate
B — auto-fix via critic
C — edit-fix, with your notes
D — stop here
```

Buttons can mirror A/B/C/D, but text remains canonical so the same backend works in CLI, Open WebUI, Telegram, and future custom UI.

## Kinodel dashboard

The dashboard is a project-centric board.

### Project cards

Each project card shows:

- **Status** — running, waiting for gate, rendering, failed, complete.
- **Pipeline** — `cinematic.v1`, future `music_video.v1`, `serial_episode.v1`.
- **Current node** — e.g. `p7_story_images_gate`.
- **Latest preview** — selected thumbnail/video.
- **Next action** — approve gate, inspect error, open media board, resume.

### Kanban lanes

Recommended lanes:

- **Briefing** — projects waiting for BriefGate.
- **Planning** — story/wardrobe/storyboard/video request stages.
- **Rendering** — active RenderService jobs.
- **Review** — hard gates waiting for user decision.
- **Assembly** — montage/final chunk/craft stages.
- **Done** — final MP4 and reusable chunks.

The lane is derived from graph state, not manually edited.

## Node view

The node view visualizes the compiled `pipeline_spec`.

### Node card fields

- **Node ID** — `p5_storyboard_plan`.
- **Type** — `agent_stage`, `render_stage`, `review_gate`, etc.
- **Owner** — skill or service.
- **Reads** — declared input artifacts.
- **Writes** — declared output artifacts.
- **Validator** — schema/service check.
- **Support skills** — prompt helpers or optional capabilities.
- **Selected refs source** — render manifests used by the node.
- **State** — pending, running, complete, blocked, failed.

### Drill-down panel

Inside a node, users can inspect:

- **Artifact refs** — paths and validation status.
- **Media refs** — selected outputs used by downstream stages.
- **Gate decision** — A/B/C/D history for gate nodes.
- **Agent contract** — owner skill summary and support skills.
- **Logs boundary** — compact backend diagnostics, not provider raw spam.

## Pipeline customization UX

Customization should edit specs, not code.

### Safe customization fields

Creators or admins can adjust:

- **Stage enabled/disabled** — only when validators allow it.
- **Owner agent** — choose compatible skill/agent adapter.
- **Support skills** — add/remove prompt helpers.
- **Provider profile** — bind RenderService capability, not provider payload JSON.
- **Shot count and format** — stored in `brief.json` and checked by validators.
- **Gate policy** — add a human gate or require final approval.
- **Chunk dependencies** — attach avatar/music/style chunks to selected stages.

### Dangerous changes require admin mode

- **Schema changes** — changing artifact schema IDs.
- **Validator removal** — removing validators.
- **Gate bypass** — skipping p4/p7/p12 hard gates.
- **Provider leakage** — writing provider payloads into planner artifacts.
- **Silent approval** — allowing auto-approval on timeout.
- **Index mismatch** — mixing incompatible embedding dimensions in one index.

### Customization flow

```text
open pipeline template
-> duplicate as project or workspace preset
-> edit typed fields
-> validate spec
-> preview graph
-> run with frozen project-local pipeline_spec.json
```

This makes pipeline variants reproducible and debuggable.

## Media board

The media board is the review room for selected refs.

Panels:

- **Main frame** — anchor image and alternatives.
- **Story frames** — shot grid with approval/replace markers.
- **Video clips** — per-shot video previews.
- **Final assembly** — final MP4 player.
- **Chunk refs** — media handles selected for reusable memory.

User actions:

- **Approve** — approve current gate.
- **Mark repair** — mark a specific frame/clip for repair.
- **Add notes** — attach edit notes to the pending gate.
- **Compare** — compare alternatives.
- **Promote** — promote a selected output.

All actions map to graph events or ProjectStore selected refs. The UI must not mutate `outputs/` directly.

## Open WebUI integration model

Use Open WebUI as a trusted shell with Kinodel as an external backend/pipeline service:

- **Chat endpoint** — starts/resumes graph threads.
- **Streaming endpoint** — sends progress and gate cards.
- **Media endpoint** — serves public refs when providers need URLs.
- **Project endpoint** — dashboard and node graph data.

Open WebUI Knowledge/RAG can help with docs browsing, but production agents should receive typed Kinodel chunks/context packs from `ChunkService`.

## Design tone

Kinodel should feel like a small film studio:

- **Cinematic** — thumbnails and previews are first-class.
- **Traceable** — every stage has owner/input/output.
- **Calm** — gates are clear and reversible.
- **Clean** — no raw provider clutter in creator view.
- **Customizable** — advanced users edit typed pipeline specs, not hidden prompt spaghetti.
