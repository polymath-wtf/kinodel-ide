# Kinodel IDE Agent Guide

## Mission

Rebuild Kinodel as a human-in-the-loop creative app on LangGraph. Preserve useful legacy invariants, not legacy machinery. The architecture must make long-running generative work resumable and inspectable, in production pipeline.


The architectural rule is:

```text
Graph coordinates.
Agents reason.
Tools perform side effects.
Artifacts preserve validated results.
Humans approve creative direction.
```

## Source Of Truth

Read in this order:

1. `SOUL.md` for product taste.
2. `docs/README.md` for documentation routing.
3. `docs/backend/architecture.md` for system boundaries.
4. The relevant domain page under `docs/agents/`, `docs/pipelines/`, `docs/tools/`, or `docs/rag/`.
5. `skills/LangGraph/` for local framework documentation when changing runtime behavior.

`legacy/` is read-only research evidence. It may explain intent, but it is not current architecture. Never copy a legacy script or schema without reducing it to the smallest current requirement.

## Routing

| Work | Read first |
|---|---|
| Runtime, state, resume, gates | `docs/backend/runtime.md`, `docs/backend/state-machine.md` |
| Artifact contracts | `docs/backend/artifacts.md` |
| Pipeline topology | `docs/backend/pipeline.md`, `docs/pipelines/` |
| Agent behavior | `docs/agents/README.md`, then the agent page |
| Tool calls and side effects | `docs/tools/tools.md` |
| RAG, chunks, context injection | `docs/rag/architecture.md`, `docs/rag/chunks/chunks.md` |
| Frontend concepts | `docs/frontend/webui.md` |
| ComfyUI/provider work | `docs/backend/comfyui.md`, `skills/comfyui-skill/` |
| Legacy migration question | `docs/refactoring.md`, then a targeted search in `legacy/` |

## Engineering Rules

- Build the smallest restart-safe vertical slice before generic infrastructure.
- Keep graph state compact and JSON-serializable; store references, not artifact bodies or media.
- Give each logical output one owner.
- Use typed node inputs and outputs; do not revive `delegate_task` envelopes or `/goal` routing.
- Nodes route deterministically. Agents do not choose the next graph edge.
- All mutating tools require validation and idempotency; replacing an existing binding or control record also requires optimistic concurrency.
- Code before a LangGraph `interrupt()` must be pure or idempotent because the node replays on resume.
- Planner artifacts are provider-neutral. Provider payloads stay in adapters and worker storage.
- Human approval is explicit and bound to an artifact revision; output existence is never approval.
- Retrieval indexes and context packs are derived. Canonical knowledge and approved artifacts remain recoverable without them.
- Prefer direct references and FTS before broad vector retrieval.
- Do not add compatibility layers for unshipped legacy behavior.

## Agent Builds

Current work belongs in `docs/agents/`. Production-ready OpenCode agents, subagents, and their bundled resources will later live under `.agents/`.

When that build starts:

- one folder per deployable agent;
- keep runtime orchestration out of agent prompts;
- bundle only the references and tools the agent actually needs;
- treat `docs/agents/<name>.md` as the contract that the build must satisfy;
- add `.agents/README.md` as the deployment index instead of duplicating routing here.

## Anti-Overengineering Gate

Before adding an abstraction, answer:

1. Which observed failure does it prevent?
2. Can a typed function, one graph node, or one table solve it?
3. Is there a second real use case, not a hypothetical one?
4. Can it be deleted or rebuilt without losing creative truth?

If the answers are weak, do not build it yet.
