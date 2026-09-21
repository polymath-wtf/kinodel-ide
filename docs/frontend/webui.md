# Web UI

Status: **Accepted product boundary; implementation pending.** UI is an inspection/control surface, not another production state machine.

## First UI Slice

The main surface is the fixed [cinematic node workflow](../pipelines/cinematic.md). Each node shows name, status and output preview. Selecting it opens exact inputs, instructions, output versions, relevant discussion, tool progress and errors. “Card” is only a visual treatment of a node; grouping is deferred.

Human actions follow the [HITL contract](../hilp/hilp.md#creator-actions): show approval separately from node chat, distinguish a question from an edit, and display the exact version concerned. Keep old outputs and feedback inspectable.

Local first launch needs no account. Show unavailable providers and retain access to saved projects. Login/credits/hosted services are separate later activation. [Local MVP](../roadmap-mvp.md) owns tasks and acceptance, [startup](../backend/local-startup.md) owns process lifetime.

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

After the fixed route works: configurable known nodes, then sequential composition, then optional UI groups. Editing graph/instructions for a new run does not mutate the current execution. Future [Fork](../hilp/fork.md) tries another continuation from a selected stage in a child run. Fork controls and a tree of runs are outside MVP; they do not require a branching pipeline definition.

## Mini-FSD

Use lightweight Feature-Sliced Design for frontend code as it appears, not pre-created scaffolding: `app` composes/routs the application, `pages` assembles the workspace, `widgets` contains canvas/inspector/viewer, `features` implements user actions, `entities` represents project/execution/node/artifact, and `shared` contains UI primitives and HTTP utilities. Dependencies flow downward; peer slices communicate through composition/public interfaces, not hidden cross-imports. No framework/bundler choice is implied.

Frontend entities are read projections, not competing production state. Backend modules retain their Python responsibilities; FSD does not introduce `widgets/features/entities` into runtime code. Create only slices needed by a working screen.
