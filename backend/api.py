"""Loopback HTTP for the internal Story fixture; the lifespan owns its only runner."""

import asyncio
from contextlib import asynccontextmanager
from hmac import compare_digest
from ipaddress import ip_address
import json
import logging
from pathlib import Path
import secrets
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import Field, model_validator

from backend.config import resolve_data_root
from backend.domain import ArtifactRef, CanonicalUUID, Digest, DomainModel, Narrative, OwnerResponseV1, StoryV1, Text, UnitKey
from backend.story_control import open_story_runtime
from backend.story_start import GRAPH_ID
from backend.story_reads import recent_story_executions, story_projection
from backend.story_store import read_story


COOKIE = "kinodel_session"
PORT = 8765
DIST_ROOT = Path(__file__).resolve().parent.parent / "web" / "dist"
log = logging.getLogger(__name__)
ExecutionStatus = Literal["running", "waiting_review", "blocked", "cancelling", "completed", "cancelled", "failed"]


class TestStart(DomainModel):
    project_id: CanonicalUUID
    client_key: Text
    input_message: Narrative
    shot_ids: list[UnitKey] = Field(min_length=1, max_length=128)


class ResponseCommand(DomainModel):
    request_digest: Digest
    expected_revision: int = Field(strict=True, ge=1)
    command_key: Text
    action: Literal["approve", "revise", "clarify"]
    message: str | None = None


class ControlCommand(DomainModel):
    command_key: Text


class RetryCommand(ControlCommand):
    work_id: str
    expected_version: int = Field(strict=True, ge=0)


class ReviewState(DomainModel):
    request_id: str
    digest: Digest
    revision: int
    binding_revision: int
    subject_artifact_id: CanonicalUUID


class WorkState(DomainModel):
    work_id: str
    kind: Literal["start", "resume", "reconcile", "cancel"]
    status: Literal["pending", "claimed", "completed", "blocked", "failed", "obsolete"]
    blocked_reason: str | None
    work_version: int


class OutcomeState(DomainModel):
    outcome: Literal["completed", "cancelled", "failed"]
    source_id: str
    subject_artifact_id: CanonicalUUID | None


class StoryState(DomainModel):
    ref: ArtifactRef
    story: StoryV1
    current: bool


class DiscussionState(DomainModel):
    request_id: str
    action: Literal["revise", "clarify"]
    message: str
    response: OwnerResponseV1 | None


class ExecutionState(DomainModel):
    execution_id: CanonicalUUID
    project_id: CanonicalUUID
    status: ExecutionStatus
    outcome: OutcomeState | None
    review: ReviewState | None
    work: list[WorkState]
    stories: list[StoryState]
    discussion: list[DiscussionState]


class SubmittedState(DomainModel):
    input_message: Narrative
    shot_ids: list[UnitKey]
    client_key: str | None
    start_digest: Digest | None


class GraphState(DomainModel):
    id: str
    version: str | None
    digest: str | None


class StoryRefState(DomainModel):
    ref: ArtifactRef
    version: int | None
    current: bool


class ReviewResultState(DomainModel):
    kind: Literal["revised_story", "owner_response", "approved_subject"]
    ref: ArtifactRef | None
    response: OwnerResponseV1 | None

    @model_validator(mode="after")
    def validate_result(self):
        if self.kind == "owner_response":
            valid = self.ref is None and self.response is not None
        else:
            valid = self.ref is not None and self.response is None
        if not valid:
            raise ValueError("Recorded review result does not match its kind")
        return self


class ReviewHistoryState(DomainModel):
    request_id: str
    digest: Digest
    revision: int
    binding_revision: int
    previous_request_id: str | None
    base_ref: ArtifactRef
    accepted: bool
    applied: bool
    decision_id: str | None
    work_id: str | None
    action: Literal["approve", "revise", "clarify"] | None
    message: str | None
    result: ReviewResultState | None


class RemainingActions(DomainModel):
    revise: int
    clarify: int


class StoryProjection(DomainModel):
    execution_id: CanonicalUUID
    project_id: CanonicalUUID
    status: ExecutionStatus
    outcome: OutcomeState | None
    submitted: SubmittedState
    graph: GraphState
    work: list[WorkState]
    stories: list[StoryRefState]
    reviews: list[ReviewHistoryState]
    review: ReviewState | None
    remaining_actions: RemainingActions
    allowed_actions: list[Literal["approve", "revise", "clarify"]]


class RecentStory(DomainModel):
    execution_id: CanonicalUUID
    project_id: CanonicalUUID
    input_preview: str
    status: ExecutionStatus
    current_story: StoryRefState | None


class RecentStories(DomainModel):
    items: list[RecentStory]


def fixture_story(message: str, shots: list[str], prior: StoryV1 | None, feedback: str | None,
                  *, discussion=None) -> StoryV1 | OwnerResponseV1:
    """Visible deterministic substitute until the live owner adapter is installed."""
    text = feedback or message
    if discussion and discussion[-1][0] == "clarify":
        return OwnerResponseV1(status="clarified", explanation=f"The Story follows: {message[:4000]}")
    if feedback and feedback.startswith("needs_input:"):
        return OwnerResponseV1(status="needs_input", explanation="Please provide the missing detail.")
    if feedback and feedback.startswith("out_of_scope:"):
        return OwnerResponseV1(status="out_of_scope", explanation="That edit changes another stage.")
    return StoryV1(schema_id="story", schema_version="1", hook=text[:16384], story=text,
                   shots=[dict(shot_id=shot, action=text[:16384], narrative_function="Story beat",
                               subject_ids=[], state_before="Before", state_after="After") for shot in shots])


def _state(db, execution_id: str) -> dict:
    metadata = story_projection(db, execution_id)
    if metadata is None:
        raise HTTPException(404, "Unknown internal Story execution")
    stories = []
    for item in metadata["stories"]:
        try:
            ref, body = read_story(db, execution_id, artifact_id=item["ref"]["artifact_id"])
        except FileNotFoundError as error:
            raise ValueError("Committed Story file is missing") from error
        stories.append({"ref": ref.model_dump(mode="json"), "story": body.model_dump(mode="json"),
                         "current": item["current"]})
    discussion = [dict(zip(("request_id", "action", "message", "response"),
                           (row[0], row[1], row[2], json.loads(row[3]) if row[3] else None)))
                  for row in db.execute(
                      "SELECT r.request_id,r.action,r.message,o.owner_response FROM review_requests r "
                      "LEFT JOIN story_operations o ON o.execution_id=r.execution_id "
                      "AND o.activation_id=r.applied_activation "
                      "WHERE r.execution_id=? AND r.action IN ('revise','clarify') "
                      "ORDER BY r.request_revision", (execution_id,)).fetchall()]
    return {"execution_id": execution_id, "project_id": metadata["project_id"], "status": metadata["status"],
            "outcome": metadata["outcome"], "review": metadata["review"], "work": metadata["work"],
            "stories": stories, "discussion": discussion}


def create_app(root: Path | None = None, produce_story=fixture_story) -> FastAPI:
    """One ASGI app per local owner; Uvicorn must bind only 127.0.0.1:8765."""
    session, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        closing = asyncio.Event()
        async with open_story_runtime(root if root is not None else resolve_data_root(), produce_story) as runtime:
            app.state.runtime = runtime
            try:
                await runtime.run()  # Reconcile existing records before advertising readiness.
            except ValueError as error:
                log.warning("Story work blocked at startup: %s", error)

            async def worker():
                while not closing.is_set():
                    try:
                        await runtime.run()
                    except ValueError as error:
                        log.warning("Story work blocked: %s", error)
                    except Exception:
                        log.exception("Story worker stopped on unexpected error")
                    try:
                        await asyncio.wait_for(closing.wait(), 0.2)
                    except TimeoutError:
                        pass

            task = asyncio.create_task(worker())
            try:
                yield
            finally:
                closing.set()
                await runtime.close()
                await task
                del app.state.runtime

    app = FastAPI(title="Kinodel internal Story prototype", lifespan=lifespan)

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        host = request.headers.get("host", "")
        origin = request.headers.get("origin")
        try:
            peer_is_local = request.client is not None and ip_address(request.client.host).is_loopback
        except ValueError:
            peer_is_local = False
        if not peer_is_local or host not in (f"127.0.0.1:{PORT}", f"localhost:{PORT}") or (
            origin is not None and origin != f"http://{host}"
        ):
            return JSONResponse({"detail": "Local origin required"}, status_code=403)
        if request.url.path.startswith("/api/") and request.url.path != "/api/session":
            cookie = request.cookies.get(COOKIE, "")
            if not compare_digest(cookie, session):
                return JSONResponse({"detail": "Local session required"}, status_code=401)
            if request.method not in ("GET", "HEAD") and not compare_digest(
                request.headers.get("X-Kinodel-CSRF", ""), csrf
            ):
                return JSONResponse({"detail": "CSRF token required"}, status_code=403)
        return await call_next(request)

    @app.get("/api/session")
    async def open_session():
        response = JSONResponse({"csrf_token": csrf})
        response.set_cookie(COOKIE, session, httponly=True, samesite="strict", path="/")
        return response

    @app.get("/", include_in_schema=False)
    @app.get("/index.html", include_in_schema=False)
    async def ui_index():
        index = DIST_ROOT / "index.html"
        if DIST_ROOT.is_symlink() or index.is_symlink():
            raise HTTPException(404)
        if not index.is_file():
            return HTMLResponse("<!doctype html><html lang='ru'><meta charset='utf-8'>"
                                "<title>Kinodel</title><body>Frontend-сборка отсутствует. "
                                "Выполните npm ci и npm run build в web/.</body></html>", status_code=503)
        return FileResponse(index)

    @app.get("/assets/{filename}", include_in_schema=False)
    async def ui_asset(filename: str):
        # Only Vite's flat asset directory is public. No SPA fallback or source tree mounts.
        if filename.startswith(".") or not filename or DIST_ROOT.is_symlink() or (DIST_ROOT / "assets").is_symlink():
            raise HTTPException(404)
        assets = (DIST_ROOT / "assets").resolve()
        path = assets / filename
        if not path.is_file() or path.is_symlink() or path.resolve().parent != assets:
            raise HTTPException(404)
        return FileResponse(path)

    @app.post("/api/executions/internal-story", status_code=202)
    async def start(body: TestStart, request: Request):
        try:
            receipt = await request.app.state.runtime.start(body.project_id, body.client_key,
                                                             body.input_message, body.shot_ids)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        return {"execution_id": receipt.execution_id, "work_id": receipt.work_id}

    @app.get("/api/executions", response_model=RecentStories)
    async def recent_executions(request: Request, limit: int = Query(20, ge=1, le=100)):
        try:
            return RecentStories.model_validate({"items": recent_story_executions(request.app.state.runtime.db, limit)})
        except (ValueError, TypeError) as error:
            raise HTTPException(409, str(error)) from error

    @app.get("/api/executions/{execution_id}/projection", response_model=StoryProjection)
    async def read_projection(execution_id: CanonicalUUID, request: Request):
        try:
            projection = story_projection(request.app.state.runtime.db, execution_id)
            if projection is None:
                raise HTTPException(404, "Unknown internal Story execution")
            return StoryProjection.model_validate(projection)
        except (ValueError, TypeError) as error:
            raise HTTPException(409, str(error)) from error

    @app.get("/api/executions/{execution_id}", response_model=ExecutionState)
    async def read_execution(execution_id: CanonicalUUID, request: Request):
        try:
            return ExecutionState.model_validate(_state(request.app.state.runtime.db, execution_id))
        except (ValueError, TypeError) as error:
            raise HTTPException(409, str(error)) from error

    @app.get("/api/executions/{execution_id}/stories/{artifact_id}")
    async def story(execution_id: CanonicalUUID, artifact_id: CanonicalUUID, request: Request):
        db = request.app.state.runtime.db
        if db.execute("SELECT 1 FROM executions WHERE execution_id=? AND graph_id=?", (execution_id, GRAPH_ID)).fetchone() is None:
            raise HTTPException(404, "Unknown internal Story execution")
        try:
            ref, body = read_story(db, execution_id, artifact_id=artifact_id)
        except (ValueError, FileNotFoundError) as error:
            raise HTTPException(404, str(error)) from error
        return {"ref": ref.model_dump(mode="json"), "story": body.model_dump(mode="json")}

    @app.post("/api/executions/{execution_id}/reviews/{request_id}/respond", status_code=202)
    async def respond(execution_id: CanonicalUUID, request_id: str, body: ResponseCommand, request: Request):
        try:
            receipt = request.app.state.runtime.respond(execution_id, request_id, body.request_digest,
                                                        body.expected_revision, body.command_key, body.action,
                                                        body.message)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        return {"decision_id": receipt.decision_id, "work_id": receipt.work_id}

    @app.post("/api/executions/{execution_id}/retry", status_code=202)
    async def retry(execution_id: CanonicalUUID, body: RetryCommand, request: Request):
        try:
            work_id = request.app.state.runtime.retry(execution_id, body.work_id,
                                                      body.command_key, body.expected_version)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        return {"work_id": work_id}

    @app.post("/api/executions/{execution_id}/cancel", status_code=202)
    async def cancel(execution_id: CanonicalUUID, body: ControlCommand, request: Request):
        try:
            work_id = request.app.state.runtime.cancel(execution_id, body.command_key)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        return {"work_id": work_id}

    return app


app = create_app()
