# Kinodel Skills Refactor Plan

## Goal

Keep the useful production knowledge from `skills/kinodel`, but remove the Hermes-era assumption that the LLM chat must manually enforce the state machine.

## New foundation

The standalone app should treat skills as:

- agent role contracts;
- artifact schemas;
- prompt-quality guidance;
- provider adapter knowledge;
- migration references.

They should not be the primary runtime.

## What becomes legacy

| Current element | New role |
| --- | --- |
| `/goal` route prose | compatibility names for graph nodes |
| `producer_step.py` | legacy router shim / migration test oracle |
| `state_guard.py next-goal` | validator and diagnostic helper |
| `delegate_task` instructions | compatibility wrapper around future specialist nodes |
| `render_wakeup.py` | legacy render bridge until graph job events exist |
| Telegram-specific notes | gateway-specific delivery adapter notes |

## What remains canonical

- `pipeline_spec.v1`
- project-local frozen `pipeline_spec.json`
- artifact contracts and validators
- hard ReviewGate semantics
- provider-neutral render requests
- compact render result manifests
- chunk schemas and craft rules
- specialist ownership boundaries

## Target skill posture

### `pipeline-kinodel`

Owns laws, graph/stage taxonomy, artifact route, and active pipeline specs.

### `producer-kinodel`

Owns human-facing orchestration semantics and gate behavior. In nextgen backend, it maps to GraphRuntime + GateService + AgentService rather than a single mega-agent prompt.

### Specialist skills

Remain small and capability-focused:

- `storytell-kinodel`: narrative/story artifact;
- `wardrobe-kinodel`: visual anchors;
- `storyboard-kinodel`: story image requests;
- `filmmaker-kinodel`: video motion requests;
- `critic-kinodel`: QC notes;
- `montage-kinodel`: assembly;
- `craft-kinodel`: chunk packaging.

### `render-kinodel`

Becomes RenderService/provider-adapter knowledge. It must stay non-creative.

### `comfyui`

Provider toolkit and debugging guide only.

## Migration stages

1. **Docs and contracts**
   - Mark LangGraph-first runtime as canonical.
   - Demote Hermes helpers to compatibility.
   - Keep existing cinematic behavior intact.

2. **Backend skeleton**
   - Build `PipelineRegistry`, `ProjectStore`, `GraphRuntime`, `GateService`.
   - Compile `cinematic.v1` into a graph.
   - Use existing validators/scripts where cheaper than rewriting.

3. **Render service**
   - Wrap existing render worker/provider modules behind an async job service.
   - Replace terminal wake-ups with job events and graph resume.

4. **Agent nodes**
   - Convert `delegate_task` handoff envelopes into typed node inputs.
   - Keep same artifact paths and schemas.

5. **Open WebUI integration**
   - Expose Kinodel backend as an Open WebUI pipeline or OpenAI-compatible tool/model facade.
   - Return gate cards and media refs through chat initially.

6. **Chunk/RAG expansion**
   - Activate chunk resolver and direct chunk handoffs before broad semantic search.
   - Add avatar/music/season/episode chunk flows.

## Do not do

- Do not delete working legacy scripts before the LangGraph backend replaces them.
- Do not add new one-off scripts per pipeline stage.
- Do not make Producer write specialist artifacts.
- Do not move provider payloads into planner artifacts.
- Do not make RAG the source of truth for active project state.
