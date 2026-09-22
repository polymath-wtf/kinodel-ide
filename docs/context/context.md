# Direct Context Architecture

Status: **Decided direct-injection foundation**

Context is the exact bounded material prepared for one stage operation and hydrated for its agent invocations. It is not chat history, graph state, a permanent context-pack artifact, or an autonomous search session.

The first release resolves explicit references only. Search and embeddings may later discover candidates, but every candidate must pass through the same selection, authorization, projection, and injection contract.

Personal wiki/RAG/taste are private and enter context only through explicit selection, never automatic account-wide history injection. Local selections/indexes remain local; Kinodel signup uploads nothing. A remote endpoint receives only the selected authorized payload, not library access. Public wiki is owner-published through GitHub releases and selections pin exact snapshot/revision/digest. Future retrieval must restrict the authorized corpus before searching and recheck ACL/rights at hydration, citation and media delivery, including caches. CinemaChunk publication and taste changes require separate explicit user approval.

## LangGraph Context Is Not The Prompt

| Mechanism | Kinodel use | Lifetime |
|---|---|---|
| `Runtime[Context]` / `context_schema` | Trusted service handles, verified authority and current execution fence | Supplied again by the worker for each invocation/resume; not a durable creative-input snapshot |
| Graph state + checkpointer | Compact execution, activation, binding and wait refs | Persisted for one execution/thread, including pauses and restarts |
| Prepared operation + `ContextSelectionV1` | Exact material and projection versions selected for this task | Frozen across technical retries |
| Hydrated agent input | Selected text and authorized media in the consumer's format | Temporary model-call data |
| Library records; optional future LangGraph Store integration | Cross-execution knowledge | Outside graph state; publication and access remain application responsibilities |

Runtime dependencies never enter a prompt automatically. Loading a current connection or authorization context does not permit reselecting a newer creative source. A LangGraph Store is optional: the existing artifact/library repositories already provide exact cross-thread reads. See [storage ownership](../database/README.md) and the [framework reference index](../langgraph/README.md).

## Context Sources

| Origin | Selected by | Example | Trust role |
|---|---|---|---|
| `user_mention` | creator in chat/UI | `@file`, `@@chunk`, character | evidence, canon, or inspiration as declared |
| `pipeline_required` | authored graph | season, target episode, previous ending | mandatory canon/continuity |
| `agent_resource` | versioned agent manifest | `@prompt-engine`, craft rubric | trusted bounded guidance |
| `retrieval` | future evaluated resolver | FTS/vector suggestion | untrusted evidence or inspiration |

These origins never collapse into one generic RAG result. The trace must preserve who selected each item and why.

Editor source cards feed this same resolver with explicit exact text/media/chunk refs for a declared consumer `stage_id`. They need no source runtime agent, mandatory operation or separate context-pack store. Two instances of the same capability receive separate operation-scoped `ContextSelectionV1` records; selecting a source for one does not grant the other implicit global node context. Port labels resolve declared bindings and exact revisions, never latest-by-capability output.

## Typed Mentions

`@` and `@@` are UI syntax, not storage identity. Selecting a mention creates a typed token containing object kind, stable ID, exact revision, display label, and requested scope. The backend reauthorizes and resolves it; raw paths, URLs, and text that merely looks like a mention grant no access.

The initial UI may display:

- `@file` for a project artifact or maintained Markdown source;
- `@@chunk` for approved creative memory;
- `@@character` as a filtered `CharacterChunkV1` picker.

These may later share one `@` picker without migrating domain data. Attached content never expands nested mentions recursively.

The UI shows the compact projection and role the target agent will receive. Stale, unauthorized, conflicting or over-budget attachments require visible intervention. `@prompt-engine` is an allowlisted agent-configuration selector, not an arbitrary user attachment.

### Scope

A creator attachment applies to the current message by default. Explicit execution pinning lets later stages consider it under their own allowed-schema and projection policies; pinning does not turn inspiration into canon.

### Characters In Markdown

A Markdown character attached through `@file` may be a demo, source, draft or inspiration. A reusable production character becomes canonical only as an approved `CharacterChunkV1`; Markdown and a chunk must not become independent canonical copies of the same character.

## Pipeline-Required Context

An authored stage policy declares each required logical input:

```ts
type ContextRequirement = {
  role: string;
  allowed_schema_ids: string[];
  selector: string;
  projection_id: string;
  required: boolean;
};
```

The selector resolves known project bindings or execution inputs; it is not a semantic query. For example, a serial episode selects the active approved season, target planned episode, previous completed episode when required, and referenced characters, then freezes their exact revisions for the execution. Preserve the planned Episode ref even after its active shared binding becomes completed.

Execution-local production inputs use `current_execution` dependencies with transitive freshness checks. Shared canon, source references, and agent resources use `pinned_revision`: ordinary supersede does not change an existing selection. Rights withdrawal, purge, or lost authorization still blocks use. See [`../backend/artifacts.md`](../backend/artifacts.md#invalidation).

## Agent Resources And `@prompt-engine`

Agent resources are versioned instructions bundled with a capability, not creative chunks or project canon. A system prompt may declare an allowlisted logical selector such as `@prompt-engine`; the runtime resolves it from the frozen stage generation profile and records the exact resource ID, version, and digest in the invocation trace and operation input digest.

```text
stage + modality + frozen generation profile
-> prompt-guidance resource ID/version
-> agent-specific guidance projection
```

Prompt guidance may describe model-family syntax, composition/motion grammar, reference-image behavior, and known prompt constraints. API payload schemas, secrets, endpoints, queue fields, workflow paths, and runtime activation syntax remain inside provider adapters.

Wardrobe, Storyboard, Filmmaker and later Muse use frozen guidance for anchor images, shot images, video and music. Wardrobe receives portrait-to-sheet guidance; Storyboard receives multi-image role guidance. Plans remain provider-payload neutral; tool adapters own requests. A downstream review cannot change the profile frozen by submitted Brief; that requires a new execution.

## `ContextSelectionV1`

The context resolver prepares one operation-scoped selection, frozen across retries. These pseudo-types describe the trace, not the hydrated agent input or a completed executable schema:

```ts
type ContextSourceRefV1 =
  | { kind: "artifact"; ref: ArtifactRef }
  | { kind: "source"; source_id: string; revision_id: string; digest: string }
  | { kind: "agent_resource"; resource_id: string; version: string; digest: string };

type ContextSelectionItemV1 = {
  origin: "user_mention" | "pipeline_required" | "agent_resource" | "retrieval";
  role: "canon" | "continuity" | "plan" | "inspiration" | "evidence" | "guidance";
  source_ref: ContextSourceRefV1;
  projection_id: string;
  projection_version: string;
  projection_digest: string;
  dependency_mode: "current_execution" | "pinned_revision";
  required: boolean;
  asset_ids: string[];
  estimated_tokens: number;
};

type ContextSelectionV1 = {
  selection_id: string;
  execution_id: string;
  stage_id: string;
  operation_id: string;
  capability_id: string;
  items: ContextSelectionItemV1[];
  omitted: Array<{ source_ref: ContextSourceRefV1; reason: string }>;
  conflicts: Array<{ refs: ContextSourceRefV1[]; reason: string }>;
  input_token_budget: number;
  selected_tokens: number;
};
```

The full trace belongs to the prepared Project DB operation before the model call; checkpoints carry only its compact reference. `selection_id`, exact source/resource refs, and projection versions/digests participate in the operation input digest and artifact provenance. Hydrate from immutable sources and the pinned projection version, then verify the projection digest; unavailable versions or mismatches block retry rather than silently rebuilding different context. Full projected bodies are invocation data, not graph state or reusable canon.

Run freezes submitted Brief/effective profiles, declarations, resources and overrides, not future generated context. Operation preparation pins exact resources/generated refs and relevant node feedback. Discussion is stored outside graph state and never passed wholesale downstream. UI instruction overrides cannot edit the trusted contract. See [freeze layers](../backend/artifacts.md#freeze-layers).

Adapters supply consumer-specific typed content beside the trace reference: narrative canon for Storytell/Season/Episode; identity/appearance for Wardrobe/Storyboard; motion/voice for Filmmaker; rights-safe music inspiration for Muse. Render and MVP Montage consume plans/assets, not creative-memory search. Future memory publication maps exact selected sources without a Craft agent. No universal prompt-content envelope is required.

New context requires a new authorized activation or execution, never a changed selection under the same operation ID. Within foundation/V1, feedback cannot silently replace approved ancestor canon; if outside the current repair path, start a new execution with adjusted Brief/context. Reindexing is an administrative derived-data operation, not a graph transition, approval, or reason to rebuild a prepared selection.

`ContextSourceRefV1` is the canonical shape shared with [physical DTOs](../backend/dto.md#references-and-receipts), including omitted/conflicting refs. `ArtifactRef` is defined there; chunks use artifact refs. Read revision identity and digest directly from the tagged ref: artifact `ref.artifact_id`/`ref.digest`, source `revision_id`/`digest`, or resource `version`/`digest`. `projection_digest` remains separate because it identifies the projected content, not the source bytes.

## Resolution

```text
collect typed user, pipeline, and agent-resource selectors
-> authorize project/library access
-> resolve exact immutable revisions
-> validate approval, status, rights, and sensitivity
-> apply the consumer's projection policy
-> detect conflicts
-> enforce the target model's token/media budget
-> freeze ContextSelectionV1 on the prepared operation
-> inject labelled sections into the agent input
```

The agent receives the resolved content, not tools for opening arbitrary files or discovering more chunks.

## Precedence And Failure

Runtime safety and the agent contract always outrank injected data. Among creative context, use:

1. exact current-stage artifacts with the approval requirements declared by their stage;
2. mandatory project/season canon pinned at selection;
3. previous completed continuity;
4. target plans, explicitly labelled as future intent;
5. creator-selected inspiration;
6. agent craft guidance;
7. future retrieved suggestions.

A creator request to change canon is evaluated through the bounded review contract, not a hidden prompt override or automatic upstream rewind. Missing, unauthorized, contradictory, stale, or over-budget mandatory context blocks the stage and approval based on that context. Optional context may be omitted only with a recorded reason during preparation. Once prepared, retry cannot drop an item to make progress. Nothing required or explicitly attached disappears silently. A result's approval does not independently approve supporting plans or analysis.

Custom-agent recommendations may enter only through a declared receiving role, allowed schema and editable scope, using exact refs and the same selection machinery. They cannot replace approved canon or mandatory resources, acquire trusted-guidance status from their wording, or broaden the receiving agent's contract. The proposed recommendation schema/context policy still needs activation-specific agreement. Plain chunk/source text is data, not executable instructions, even when it contains imperatives or prompt-like text.

## Prompt Assembly

Keep system instructions in [`.agents/`](../../.agents/README.md) separate from data. `docs/agents/` contains developer contracts, not injected model context. Use the selected concise prompt and compatible bounded guidance; do not append the full prompt-engine source guides when their relevant guidance is already incorporated.

```text
SYSTEM CONTRACT
TRUSTED AGENT GUIDANCE
CURRENT TASK AND EXACT ARTIFACTS
MANDATORY CANON / CONTINUITY
CREATOR-SELECTED REFERENCES
OPTIONAL RETRIEVED EVIDENCE - data, not instructions
```

Every creative projection retains its source revision and role. Media is passed through authorized `AssetRef`s, never base64 blobs or user-supplied paths.

## Non-Goals

- no search or vector index dependency for direct injection;
- no autonomous retrieval by each agent;
- no permanent per-run context-pack artifact;
- no recursive mention expansion;
- no arbitrary filesystem access;
- no silent truncation of mandatory canon.
