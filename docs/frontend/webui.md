# Web UI

Status: **Product foundation**

The UI is a projection and control surface for runtime state. It never becomes a second state machine.

## Primary Surfaces

- **Project workspace**: current artifact, references, feedback, and preview.
- **Pipeline timeline**: completed, running, waiting, blocked, failed, and future stages.
- **Review gate**: one exact current-stage subject, previews, approve/edit/clarify/cancel actions.
- **Artifact board**: briefs, stories, frames, clips, audio, final outputs, and revision lineage.
- **Context explorer**: wiki/chunk search, provenance, rights, and explicit agent assignment.
- **Render monitor**: job progress and actionable failures without raw provider sludge.
- **Montage timeline**: later manual editing of explicit clip/audio selections.

Chat is one interface, not the application shell. A creator should be able to inspect and change production without reconstructing state from conversation.

Local app projects/messages stay in local SQLite/files, including after login for service credits; registration uploads nothing. Browser-hosted projects/messages are server-owned user history in PostgreSQL/managed storage. First local use does not require a Kinodel account. Earlier-stage rework is an accepted [new-execution prefix-reuse contract](../database/artifacts-media.md#возврат-к-раннему-этапу): same project, exact prefix, immutable old outputs for comparison and new approvals for changed outputs. Entry implementation remains #todo; do not expose free-form timeline rewind. Installation and persistence scope: [local versus hosted](../database/local-vs-hosted.md).

## Runtime Rules

- Every action sends an expected state/artifact revision.
- Review cards show which single subject revision and digest are being approved.
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

Accepted behavior before visual design: welcome offers register/login/local-without-login only in the local install. Hosted browser requires login. Registration takes email/login/password: Supabase email credential, mutable login display label without required uniqueness, as specified in [identity](../database/projects-identity-chat.md#вход-mvp). Windows/Linux setup reports progress/failures. Downloads distinguish managed files at the project-owning backend from expiring remote GCS availability; browser-hosted files stay server-side until an explicit user download. MVP credits show server-owned integer amounts/signup 100; product daily free limits are final-release #todo, not MVP, and paid generated downloads have no arbitrary quota. Detailed welcome/editor/branch comparison UX is #future, not permission to defer authorization, stale-review rejection or error semantics.

Only build:

1. create/open execution;
2. show current stage and artifact;
3. render typed brief/story forms and previews;
4. approve, edit with notes, ask for clarification, or cancel;
5. reconnect to an interrupted execution;
6. show typed failures.

Kanban, node editor, Obsidian-like graph, and manual timeline editing are later surfaces.
