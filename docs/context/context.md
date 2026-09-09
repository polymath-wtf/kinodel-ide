# Direct Context Architecture

Status: **Decided direct-injection foundation**

Context is the exact bounded material prepared for one stage operation and hydrated for its agent invocations. It is not chat history, graph state, a permanent context-pack artifact, or an autonomous search session.

The first release resolves explicit references only. Search and embeddings may later discover candidates, but every candidate must pass through the same selection, authorization, projection, and injection contract.

Personal wiki/RAG/taste are private and enter context only through explicit selection, never automatic account-wide history injection. Local selections/indexes remain local; Kinodel signup uploads nothing. A remote endpoint receives only the selected authorized payload, not library access. Public wiki is owner-published through GitHub releases and selections pin exact snapshot/revision/digest. Future retrieval must restrict the authorized corpus before searching and recheck ACL/rights at hydration, citation and media delivery, including caches. CinemaChunk publication and taste changes require separate explicit user approval.

## Context Sources

| Origin | Selected by | Example | Trust role |
|---|---|---|---|
| `user_mention` | creator in chat/UI | `@file`, `@@chunk`, character | evidence, canon, or inspiration as declared |
| `pipeline_required` | authored graph | season, target episode, previous ending | mandatory canon/continuity |
| `agent_resource` | versioned agent manifest | `@prompt-engine`, craft rubric | trusted bounded guidance |
| `retrieval` | future evaluated resolver | FTS/vector suggestion | untrusted evidence or inspiration |

These origins never collapse into one generic RAG result. The trace must preserve who selected each item and why.

## Typed Mentions

`@` and `@@` are UI syntax, not storage identity. Selecting a mention creates a typed token containing object kind, stable ID, exact revision, display label, and requested scope. The backend reauthorizes and resolves it; raw paths, URLs, and text that merely looks like a mention grant no access.

The initial UI may display:

- `@file` for a project artifact or maintained Markdown source;
- `@@chunk` for approved creative memory;
- `@@character` as a filtered `CharacterChunkV1` picker.

These may later share one `@` picker without migrating domain data. Attached content never expands nested mentions recursively.

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

Storyboard, Filmmaker, and Muse may use prompt guidance to produce model-targeted prompt text inside typed creative plans. Wardrobe supplies semantic visual direction rather than image syntax. Their artifacts remain provider-payload neutral: changing the generation profile requires new plan activations, while adapters still own the actual request payload. Once Brief is approved, a downstream gate cannot change its frozen profile; foundation/V1 uses a new execution for that change.

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
  source_revision: string;
  source_digest: string;
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

Adapters supply consumer-specific typed content beside the trace reference: narrative canon for Storytell/Season/Episode; identity/appearance for Wardrobe/Storyboard; motion/voice for Filmmaker; rights-safe music inspiration for Muse; optional editing lessons for Montage. Craft reads declared exact source projections directly; Render and Montage execution consume plans/assets, not creative-memory search. No universal prompt-content envelope is required.

New context requires a new authorized activation or execution, never a changed selection under the same operation ID. Within foundation/V1, feedback cannot silently replace approved ancestor canon; if outside the current repair path, start a new execution with adjusted Brief/context. Reindexing is an administrative derived-data operation, not a graph transition, approval, or reason to rebuild a prepared selection.

`ContextSourceRefV1` is the canonical shape shared with [physical DTOs](../backend/physical-dtos.md#references-and-receipts), including omitted/conflicting refs. `ArtifactRef` is defined there; chunks use artifact refs. `source_revision` equals the immutable `artifact_id`, source `revision_id`, or resource `version` for the respective kind; `source_digest` equals that ref's digest. These redundant fields cannot select another revision. This is an unshipped contract correction, not a data migration or string-ref compatibility path.

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

## Prompt Assembly

Keep system instructions separate from data:

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
