# Tools And Services

Status: **Foundation registry**

Production backend code is Python. A tool is a typed Python operation at a trust boundary, not a shell command and not an automatic capability given to an agent. The TypeScript web app calls HTTP endpoints; graph nodes call Python services and repositories.

## What Exists In `foundation.v0`

| Caller | Allowed operation | Why |
|---|---|---|
| Web UI | create project, start execution, read status, submit review | creator control surface |
| Graph node adapter | read declared inputs, find prior operation, commit output | executes one safe stage |
| Producer / Storytell / Critic | none | they return structured candidates only |
| Resume worker | claim pending resume, invoke graph | crash recovery after review |

No generic `ToolResult` envelope is needed inside Python. Services raise typed domain errors; FastAPI maps them to HTTP responses. Do not use stdout JSON, process exit codes, a terminal, or arbitrary paths as an internal contract.

## P0 Python Contracts

These Pydantic models are the starting point. They belong with the domain DTOs, not in prompts or agent code.

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
    resume_id: str


class ResumeRequest(BaseModel):
    resume_id: str
    execution_id: str
    payload: dict[str, Any]
    expected_version: int
```

`CommitArtifactsRequest` is one Project DB transaction: validate the current execution `lease_fence`, validate draft and provenance, write immutable metadata, replace the declared bindings, and save the operation result map. `expected_binding_revisions` must contain every output slot; use an explicit `None` only for a new slot. It returns the existing result only when both `operation_id` and `input_digest` match. A changed input with the same operation ID is an integrity error.

The `candidate` field is deliberately only an envelope here. Each stage passes its concrete Pydantic model, such as `BriefV1` or `StoryV1`; it is not an untyped production artifact format. Review validators require feedback for `revise`, a question for `clarify`, candidate IDs only for a selection gate, and no hidden creative changes in `approve`.

## Foundation Operations

### HTTP Endpoints, Not Agent Tools

- `POST /projects` creates an empty project.
- `POST /projects/{project_id}/executions` requires a client idempotency key, freezes the pipeline, stores `InitialRequestV1` as the `initial_request` binding, and starts the graph. The same key and payload return the existing execution; a changed payload conflicts.
- `GET /projects` and `GET /executions/{execution_id}` return read-only status and artifact projections.
- `POST /review-requests/{request_id}/response` validates `ReviewRespondRequest`, records the decision and durable resume intent, then attempts resume.

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


async def claim_next_resume() -> "ResumeRequest | None": ...
```

Node adapters call `get_operation_result()` before any model call. They use `get_declared_inputs()` rather than a free-form artifact lookup. `commit_artifacts()` is the only artifact mutation path. `claim_next_resume()` is used by the resume worker, never by an agent. The worker claims with an expiring owner token, verifies the expected active interrupt, invokes `Command(resume=resume.payload)` on `thread_id = resume.execution_id`, and marks the exact `resume_id` complete only after the invocation returns or checkpoint inspection proves it was already consumed.

`artifact_validate`, `artifact_inspect`, and `artifact_get_by_operation` are not separate tools: validation belongs inside `commit_artifacts`; inspection is a read projection; lookup is `get_operation_result`.

## Deferred Production Services

These are needed by `cinematic.v1`, not by `foundation.v0`. Define their concrete Pydantic contracts only when their first stage is implemented.

| Service | Keep | Do not build yet |
|---|---|---|
| Render | idempotent submit, durable job record, validated output promotion | separate preflight API, generic provider toolkit, provider tools for agents |
| Media | bounded inspection and server-side remote import | arbitrary URL/path access and media utility toolbox |
| Montage | validated `MontagePlanV1` to `MontageResultV1` with fixed ffmpeg operations | interactive editing engine or a generic ffmpeg command tool |
| Context | direct typed-reference resolver and compact projections | FTS/vector discovery or persistent context packs |

When rendering begins, the minimal boundary is:

```python
async def start_render(request: "RenderStartRequest") -> "JobRef": ...
async def get_render_candidates(job_id: str) -> "CandidateSetRef": ...
async def promote_render(request: "RenderPromoteRequest") -> CommitArtifactsResult: ...
async def execute_montage(request: "MontageRequest") -> CommitArtifactsResult: ...
```

Each mutating request includes `execution_id`, `stage_id`, `operation_id`, the current `lease_fence`, exact input refs, and expected binding revisions. The repository rejects a stale fence even if a long-running model/provider call later returns. The wait token is JSON-safe and contains `job_id`, `operation_id`, and expected job version. Graph nodes, not provider callbacks, decide when to advance.

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
| `render_wakeup.py` completion wake-up | durable `execution_resumes` record |
| provider scripts | provider-specific Python adapters |
| `chunk_resolver.py` direct-first retrieval | deferred retrieval service |
| chunk/index backfills and evaluations | admin commands and test suite |

Do not rebuild `producer_state.json`, shell handoffs, duplicated provider registries, mock production vectors, or user-home dynamic imports.
