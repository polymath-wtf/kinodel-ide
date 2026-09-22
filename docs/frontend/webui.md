# Web UI

Status: **Accepted product boundary; implementation pending.** UI is an inspection/control surface, not another production state machine.

## First UI Slice

Build Kinodel's own local React + TypeScript WebUI with [React Flow](https://reactflow.dev/). The application serves the compiled frontend and its HTTP API from the local Kinodel origin; React Flow renders the workflow but never routes or executes it. An external graph UI or a second runtime is not part of this client.

The main surface is the fixed [cinematic node workflow](../pipelines/cinematic.md). Each node shows its name, status and compact output preview. Selecting it opens exact inputs, instructions, output versions, relevant discussion, tool progress and errors. The MVP reads a fixed backend projection: nodes may be selected, but users cannot add, delete or reconnect them.

```text
+--------------------+       +--------------------+
| Storytell          |       | Story review       |
| Agent / completed  | ----> | HITL / waiting     |
| Story v2           |       | Review Story v2    |
+--------------------+       +--------------------+
```

```text
[Brief] -> [Storytell] -> [Story review] -> [Wardrobe] -> [Anchor generation] -> ... -> [Montage]
```

The full cinematic has all declared stages; the shortened diagram only explains the visual language.

| Name | Meaning |
|---|---|
| Pipeline | The complete production route and its connections |
| Node | One visible production stage, such as Storytell or Anchor generation |
| Node panel | The selected node's inputs, results, versions and available actions |
| Review request | The exact result version currently awaiting a creator decision |
| node-pack | A future single canvas element that contains several nodes behind declared shared inputs and outputs |

A node-pack is not an MVP runtime feature. The fixed cinematic renders ordinary nodes. Later packaging must preserve each contained node's result ownership, review boundary and recovery behavior; visual collapse alone does not silently bypass them.

Human actions follow the [HITL contract](../hilp/hilp.md#creator-actions): show approval separately from node chat, distinguish a question from an edit, and display the exact version concerned. Keep old outputs and feedback inspectable.

Local first launch needs no account. Show unavailable providers and retain access to saved projects. Login/credits/hosted services are separate later activation. [Local MVP](../roadmap-mvp.md) owns tasks and acceptance, [startup](../backend/local-startup.md) owns process lifetime.

## Minimal Workspace

| Surface | First implementation |
|---|---|
| Project / Run | Idea, visible defaults, resolved profiles, start and reopen the same execution |
| Fixed node canvas | React Flow renders ordered nodes and connections with status/preview; selecting a node opens its panel; graph editing is disabled |
| Node panel / review | Exact inputs, read-only frozen instructions, result versions, media previews and persisted feedback; explicit approve/revise/clarify and anchor regeneration |
| Execution controls | Current activity or block reason, allowed retry/cancel, provider availability and final playback/download |

Only the current actionable review accepts edits/questions; historical nodes remain inspectable. After clarify or a non-ready revision, show the explanation and the new actionable request for the unchanged subject. Display result version separately from request revision: a new question does not imply v2 of the story or images.

## Runtime Rules

Node identity, types, connections and composition scope belong to the [node contract](../backend/node.md).

- Commands include expected result/request revision and a deduplication key; stale views refresh rather than overwrite.
- Accepted commands show “applying”; only committed approval/save unlocks downstream.
- Poll authoritative reads for jobs/results/reviews; reconnect does not depend on missed events.
- Browser close does not cancel accepted work. Cancellation is an explicit command.
- Node discussion persists feedback/questions and responses with result references; no separate global chat system is required for MVP.
- Keep credentials, raw provider payloads and internal checkpoint IDs out of normal UI.

## Context And Later Editing

Creator-selected character/wiki/text/media references enter only the chosen node's declared context. Show supplied inputs and their roles. Preserve exact versions for replay; removing a draft attachment does not rewrite active prepared inputs. A larger library picker/search and richer node chat can follow actual use.

After the fixed route works: configurable known nodes, then sequential composition, then node-packs where they improve a real workflow. Editing graph/instructions for a new run does not mutate the current execution. Future [Fork](../hilp/fork.md) tries another continuation from a selected stage in a child run. Fork controls and a tree of runs are outside MVP; they do not require a branching pipeline definition.

## Frontend Layout

Start with React, React Flow, the workspace's colocated canvas/panel/viewer components and a typed HTTP client. Keep user actions next to the screen that uses them. Extract shared components or feature modules when actual reuse or complexity warrants it; no mandatory six-layer Mini-FSD or empty slices. Choose the smallest conventional bundler when implementation starts.

Frontend data remains read projections, not competing production state. Backend modules retain their Python responsibilities; UI organization does not change execution ownership.
