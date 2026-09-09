# Tools And Services

Status: **Foundation registry**

Production backend code is Python. A tool is a typed Python operation at a trust boundary, not a shell command and not an automatic capability given to an agent. The TypeScript web app calls HTTP endpoints; graph nodes call Python services and repositories.

Persistence profiles are SQLite local / PostgreSQL server. Execution-row locks and advisory-session claims below describe server mechanics; local uses serialized short write transactions and one background runner under exclusive application/data-directory ownership, as defined in [runtime](../backend/runtime.md#single-writer-ownership). Logical commands and OCC/idempotency obligations are shared, not a transparent SQL compatibility layer.

## Planned Foundation Callers

Nothing in this table claims deployed tools. The text milestone precedes the rendered [build gate](../roadmap.md#current-build-gate).

| Caller | Allowed operation | Why |
|---|---|---|
| Web UI | create project, request execution start, read status, submit review, request cancellation | creator control surface |
| Graph node adapter | read declared inputs, find prior operation, commit output | executes one safe stage |
| Producer / Storytell / Critic / Wardrobe / Storyboard | none | they return structured candidates only |
| Execution worker | claim durable work, invoke/recover graph, finalize cancellation | sole graph invocation path from first start |

No generic `ToolResult` envelope is needed inside Python. Services raise typed domain errors; FastAPI maps them to HTTP responses. Do not use stdout JSON, process exit codes, a terminal, or arbitrary paths as an internal contract.

## P0 Python Contracts

The field-level proposal now lives in [physical-dtos.md](../backend/physical-dtos.md), including strict action unions, unit-to-candidate selection, start pins and trusted commit metadata. The older sketches below are **non-authoritative shape illustrations**, not implementation templates: their nullable action bag, `selected_candidate_ids` list, `dict[str, Any]` candidate and `accepted: bool` omit required invariants. No backward compatibility with these unshipped sketches is required. [runtime.md](../backend/runtime.md) owns work delivery.

```python
from typing import Any, Literal

from pydantic import BaseModel


class ArtifactStateRef(BaseModel):
    artifact_id: str
    schema_id: str
    schema_version: str
    uri: str
    digest: str
    media_type: str


class BindingRef(ArtifactStateRef):
    binding_revision: int


class ArtifactDraft(BaseModel):
    slot: str
    schema_id: str
    schema_version: str
    candidate: dict[str, Any]


class CommitArtifactsRequest(BaseModel):
    project_id: str
    execution_id: str
    stage_id: str
    operation_id: str
    lease_fence: int
    input_digest: str
    input_refs: list[ArtifactStateRef]
    outputs: list[ArtifactDraft]
    expected_binding_revisions: dict[str, int | None]


class CommitArtifactsResult(BaseModel):
    outputs: dict[str, BindingRef]


class ReviewDecision(BaseModel):
    action: Literal["approve", "revise", "clarify", "cancel"]
    feedback: str | None = None
    question: str | None = None
    selected_candidate_ids: list[str] | None = None


class ReviewRespondRequest(BaseModel):
    request_id: str
    expected_request_digest: str
    decision: ReviewDecision
    idempotency_key: str


class ReviewRespondResult(BaseModel):
    accepted: bool
    work_id: str
```

`CommitArtifactsRequest` is one Project DB transaction: validate the current execution `lease_fence`, validate draft and provenance, write immutable metadata, replace the declared bindings, and save the operation result map. `expected_binding_revisions` must contain every output slot; use an explicit `None` only for a new slot. It returns the existing result only when both `operation_id` and `input_digest` match. A changed input with the same operation ID is an integrity error.

The `candidate` field is deliberately only an envelope here. Each stage passes its concrete Pydantic model, such as `BriefV1` or `StoryV1`; it is not an untyped production artifact format. Review validators require feedback for `revise`, a question for `clarify`, candidate IDs only for a selection gate, and no hidden creative changes in `approve`.

## Foundation Operations

### HTTP Endpoints, Not Agent Tools

- `POST /projects` creates an empty project.
- `POST /projects/{project_id}/executions` requires a client idempotency key, freezes the pipeline, and atomically stores the execution, `InitialRequestV1` metadata/binding, and unique start work after preparing immutable bytes. It returns accepted identity, never invokes the graph. The same key and payload return the existing execution; a changed payload conflicts.
- `GET /projects` and `GET /executions/{execution_id}` return read-only status and artifact projections.
- `POST /review-requests/{request_id}/response` validates the current actionable request and `ReviewRespondRequest`, atomically records the decision and unique resume work, then returns accepted identity without invoking the graph.
- `POST /executions/{execution_id}/cancel` records an idempotent cancellation control and cancel work under the execution-row lock. Acceptance means `cancelling`; only worker settlement establishes `cancelled`. Terminal outcomes are not overwritten.

The browser never supplies an internal interrupt ID or checkpoint ID. Authorization is enforced at these endpoints, not delegated to an agent.

### Internal Repository And Service Operations

```python
async def get_operation_result(
    *, execution_id: str, operation_id: str
) -> CommitArtifactsResult | None: ...


async def get_declared_inputs(
    *, execution_id: str, slots: list[str]
) -> dict[str, BindingRef]: ...


async def commit_artifacts(
    request: CommitArtifactsRequest,
) -> CommitArtifactsResult: ...


async def claim_next_work() -> "ExecutionWorkClaim | None": ...
```

Node adapters call `get_operation_result()` before any model call. They use `get_declared_inputs()` rather than a free-form artifact lookup. `commit_artifacts()` is the only artifact mutation path and also checks cancellation and records the deterministic next activation. The worker-only `claim_next_work()` follows the advisory-lock/fence protocol in [runtime.md](../backend/runtime.md#single-writer-ownership); `ExecutionWorkClaim` is a pending DTO, not an agent tool or arbitrary resume payload. Recovery chooses start, exact-interrupt resume, continuation, or cancellation using the runtime decision table. Work settles only at a durable pause, explicit block, or terminal outcome. A consumed decision with an unfinished following node remains recoverable work.

Direct context preparation is a foundation service, not a deferred retrieval feature: resolve declared exact references, authorize and project them for Producer/Storytell/Critic, and persist `ContextSelectionV1` on the prepared operation before any model call. No optional attachments is valid; required task inputs still apply. Retry reuses the selection and verifies rights/digests. Missing required context blocks instead of invoking search. See [context.md](../context/context.md).

`artifact_validate`, `artifact_inspect`, and `artifact_get_by_operation` are not separate tools: validation belongs inside `commit_artifacts`; inspection is a read projection; lookup is `get_operation_result`.

## Deferred Production Services

The single-image Render/media path and its required context projections are part of deployable `foundation.v0`; they follow the internal text milestone. Montage, multiple-shot generation and other full `cinematic.v1` services remain deferred. Define concrete Pydantic contracts with each enabled stage.

| Service | Keep | Do not build yet |
|---|---|---|
| Render | idempotent submit, durable job record, validated output promotion | separate preflight API, generic provider toolkit, provider tools for agents |
| Media | bounded inspection and server-side remote import | arbitrary URL/path access and media utility toolbox |
| Montage | validated `MontagePlanV1` to `MontageResultV1` with fixed ffmpeg operations | interactive editing engine or a generic ffmpeg command tool |
| Context extension | cinematic resource/media projections over the foundation resolver | FTS/vector discovery or persistent context packs |

When rendering begins, the minimal boundary is:

```python
async def start_render(request: "RenderStartRequest") -> "JobRef": ...
async def get_render_candidates(job_id: str) -> "CandidateSetRef": ...
async def promote_render(request: "RenderPromoteRequest") -> CommitArtifactsResult: ...
async def execute_montage(request: "MontageRequest") -> CommitArtifactsResult: ...
```

Each graph-owned mutating request includes `execution_id`, `stage_id`, `operation_id`, the current `lease_fence`, exact input refs, and expected binding revisions. The repository rejects a stale fence even if a long-running model/provider call later returns. Job workers use separate job ownership and cannot bind outputs. The immutable group wait token is `{wait_id, stage_id, activation_id, request_digest}`, not a mutable job version; terminal group result and unique wake work commit atomically per [runtime.md](../backend/runtime.md#rendering-extension). Graph nodes, not provider callbacks, decide when to advance.

## Explicitly Not Tools

- graph routing, joins, retry policy, and `interrupt()`;
- project/execution status queries as agent capabilities;
- agent file, terminal, SQL, network, or provider access;
- generic `artifact_validate` or `render_preflight` APIs;
- admin backfills, index rebuilds, workflow registration, and retrieval evaluation;
- legacy wake-up prompts, `/goal` maps, or output-directory scans.

## Legacy Extraction

| Legacy behavior | Keep as |
|---|---|
| `state_guard.py` validation and approval checks | Pydantic/semantic validators plus graph gates |
| `producer_step.py` route intent | authored graph edges, not a runtime tool |
| `init_project.py` no-overwrite rule | project creation endpoint |
| render worker submit/reconcile/import | deferred Python render service and worker |
| `render_wakeup.py` completion wake-up | unique durable `execution_work` resume source |
| provider scripts | provider-specific Python adapters |
| `chunk_resolver.py` direct-first retrieval | foundation direct resolver; chunk-library support and discovery later |
| chunk/index backfills and evaluations | admin commands and test suite |

Do not rebuild `producer_state.json`, shell handoffs, duplicated provider registries, mock production vectors, or user-home dynamic imports.
