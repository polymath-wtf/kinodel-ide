# Web UI

Status: **Product foundation**

The UI is a projection and control surface for runtime state. It never becomes a second state machine.

## Primary Surfaces

- **Project workspace**: current artifact, references, feedback, and preview.
- **Pipeline timeline**: completed, running, waiting, blocked, failed, and future stages.
- **Review gate**: exact artifact revision, previews, approve/revise/cancel actions.
- **Artifact board**: briefs, stories, frames, clips, audio, final outputs, and revision lineage.
- **Context explorer**: wiki/chunk search, provenance, rights, and explicit agent assignment.
- **Render monitor**: job progress and actionable failures without raw provider sludge.
- **Montage timeline**: later manual editing of explicit clip/audio selections.

Chat is one interface, not the application shell. A creator should be able to inspect and change production without reconstructing state from conversation.

## Runtime Rules

- Every action sends an expected state/artifact revision.
- Review cards show which revision and digest are being approved.
- Reconnect derives truth from runtime/artifact queries, not missed events.
- Output existence never changes a gate to approved.
- Event delivery may duplicate; UI deduplicates by event ID.
- Provider logs and secrets are operator diagnostics, not normal creator UI.

## Context UX

- `@file` may reference a project artifact or source.
- `@@chunk` may explicitly attach approved creative memory.
- The UI shows the compact projection that will be supplied to each agent.
- Users can inspect provenance and `take`/`ignore` rights constraints.
- Removing context changes the next invocation, not historical artifacts.
- Semantic suggestions remain suggestions until explicitly selected or allowed by pipeline policy.

## First UI Slice

Only build:

1. create/open execution;
2. show current stage and artifact;
3. render typed brief/story forms and previews;
4. approve, revise with notes, or cancel;
5. reconnect to an interrupted execution;
6. show typed failures.

Kanban, node editor, Obsidian-like graph, and manual timeline editing are later surfaces.
