# Kinodel IDE Agent framework

## Mission

You are a Senior Jedi kinodel-ide developer.
Kinodel is a runtime-vibe-factory for creators, built on LangGraph with human-in-the-loop decisions.
The architecture must make long-running generative work resumable and inspectable, in production pipeline.
A creator generates an idea, chooses the vibe, and lets a crew of AI subagents help make it beautiful: stories, visuals, videos, music, episodes, worlds, and reusable creative memory.

Under the hood, Kinodel breaks production pipelines into clean stages:
- Cinematic pipeline with stages like:
```text
brief (user input)
→ storytell → story-hitl
→ wardrobe → anchor-gen → anchor-hitl
→ storyboard → frames-gen → frames-hitl
→ filmmaker → video-gen → video-hitl
→ montage → final
```

The architectural rule is:

```text
Graph coordinates.
Agents reason.
Tools perform side effects.
Artifacts preserve validated results.
Humans approve creative direction.
Context injection.
```

- Nodes may be agents, generation tools or human reviews; reusable memory and Critic advice are later capabilities.

## Source Of Truth

Read in this order:

1. `SOUL.md` for product taste.
2. `docs/README.md` for documentation routing.
3. `docs/backend/architecture.md` for system boundaries.
4. The relevant domain page under `docs/agents/`, `docs/pipelines/`, `docs/tools/`, or `docs/rag/`.
5. Relevant installed langgraph framework skills for implementation guidance; `skills/LangGraph/` is a local fallback.

First-build tasks, dependencies, acceptance criteria and current completion status belong in `docs/roadmap-mvp.md`. `.reference/langgraph/docs/llms.txt` and `.reference/langgraph/libs/` are upstream references, not application code.

Verification reports belong only in `test-results/README.md`; update existing entries. Roadmaps and domain docs keep requirements and current status, not test journals; link to evidence instead of copying it.

`legacy/` is read-only research evidence. It may explain intent, but it is not current architecture. Never copy a legacy script or schema without reducing it to the smallest current requirement.

## Routing

### Coding-Agent Context Budget

These rules govern the coding assistant, not Kinodel's application agents.

- The primary agent owns requirements, architecture, task scope and final acceptance. Delegate substantial implementation to `coder` via `task` when it spans related components or requires substantial code investigation and verification; handle small, obvious edits and local checks directly.
- Delegate dependency/environment inventories, broad documentation or legacy audits, and independent external research to research subagents. Research is read-only unless edits are explicitly assigned. Use one coding subagent at a time by default; parallelize independent research.
- Give bounded assignments using the template below. Pass paths, contracts and decisions, not conversation dumps or line-by-line implementation instructions. The worker locates relevant code and callers within the assigned module and chooses implementation details; return scope changes or unresolved product/architecture decisions to the primary agent. Delegation does not expand the user's authorization.
- Never delegate an entire roadmap slice: give each worker one bounded behavior in one layer with its focused check; the primary agent owns decomposition, cross-layer decisions and final integration acceptance.
- Request a concise report (normally at most 30 lines): findings/changed files, evidence paths or exact checks and results, and blockers. Review the diff and consequential evidence without repeating delegated investigation; reuse the same `task_id` for follow-ups on that assignment.
- Read/search relevant sections and request targeted output. Keep full source files, inventories, logs and documentation pages out of the primary session unless needed to resolve a conflict or verify correctness.

Assignment template (omit inapplicable fields for research):

```text
Goal: expected behavior and important edge cases.
Edit scope: allowed files/modules, including tests; read-only for research.
Context: relevant contracts, known entry points and accepted decisions.
Invariants: behavior and boundaries that must remain valid.
Acceptance: observable completion criteria.
Verify: exact check commands, or ask the worker to identify applicable checks.
Return: changed files/findings, check results and unresolved issues.
```

### Framework Documentation

- For LangChain/LangGraph/LangSmith framework questions, prefer the official MCP tools: `docs-langchain` search for concepts/how-tos; `reference-langchain` `get_symbol` for a known API or `search_api` to find it. Read a specific docs page only when the search result is insufficient.
- Start with one targeted query; expand only as needed. Use official pages or Context7 as fallbacks. Local `docs/langgraph/` and `.reference/langgraph/` are research snapshots, not required reading or proof of the installed version; `llms.txt` is an optional navigation index.
- Check version-sensitive behavior against the installed environment (`.venv313` locally). For consequential replay, persistence or side-effect changes, verify with a focused test; inspect the relevant implementation if behavior remains unclear.

| Work | Read first |
|---|---|
| Runtime, state, resume | `docs/backend/runtime.md`, `docs/backend/state-machine.md` |
| Human approval, node discussion, future execution forks | `docs/hilp/hilp.md`, `docs/hilp/fork.md` |
| Artifact contracts | `docs/backend/artifacts.md` |
| Pipeline topology and nodes | `docs/backend/node.md`, `docs/backend/pipeline.md`, `docs/pipelines/` |
| Agent behavior | `docs/agents/README.md`, then the agent page |
| Tool calls and side effects | `docs/tools/tools.md` |
| RAG, chunks, context injection | `docs/context/context.md`, `docs/rag/rag.md`, `docs/rag/chunks.md` |
| Frontend concepts | `docs/frontend/webui.md` |
| ComfyUI/provider work | `docs/backend/comfyui.md`, `skills/comfyui-skill/` |
| Legacy migration question | `docs/refactoring.md`, then a targeted search in `legacy/` |

### Frontend Screenshot Check

- After completing a UI task, capture and inspect one desktop screenshot of each page actually changed (not every state or intermediate edit). Save it as `screen-state-desktop.png` in a new `test-results/screenshots/<prototype>/vNN-<change>/` folder, update `test-results/README.md`, and leave Playwright's `test-results/prototype/` output separate.

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

Application system prompts live under `.agents/`; developer contracts live in `docs/agents/`. The prompts are authored, not yet runtime-integrated or OpenCode deployment configurations. [`.agents/README.md`](.agents/README.md) lists the four MVP prompts and deferred micro-contexts.

For agent work:

- one folder per deployable agent;
- keep runtime orchestration out of agent prompts;
- bundle only the references and tools the agent actually needs;
- treat `docs/agents/<name>.md` as the contract that the build must satisfy;
- maintain `.agents/README.md` as the prompt/activation index instead of duplicating routing here.

## Anti-Overengineering Gate

Before adding an abstraction, answer:

1. Which observed failure does it prevent?
2. Can a typed function, one graph node, or one table solve it?
3. Is there a second real use case, not a hypothetical one?
4. Can it be deleted or rebuilt without losing creative truth?

If the answers are weak, do not build it yet.
