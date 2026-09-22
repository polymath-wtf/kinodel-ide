"""Internal step-1 Story fixture storage; no public cinematic start or review."""

import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile

from backend.domain import ArtifactRef, StoryV1, canonical_json, parse_json_model, sha256_digest
from backend.database import _check_file, _sync_directory


def _uuid(value: str) -> str:
    from uuid import UUID

    try:
        if type(value) is not str or str(UUID(value)) != value:
            raise ValueError("Expected canonical UUID")
    except (TypeError, AttributeError) as error:
        raise ValueError("Expected canonical UUID") from error
    return value


def _root(db: sqlite3.Connection) -> Path:
    return Path(db.execute("PRAGMA database_list").fetchone()[2]).parent


def create_test_execution(
    db: sqlite3.Connection, project_id: str, execution_id: str,
    input_message: str, shot_ids: list[str],
) -> None:
    """A private text fixture, never a partial cinematic Brief/Run."""
    _uuid(project_id)
    _uuid(execution_id)
    if not isinstance(input_message, str) or not 0 < len(input_message) <= 131072:
        raise ValueError("Invalid test input")
    if not isinstance(shot_ids, list) or not 1 <= len(shot_ids) <= 128 or any(
        not isinstance(key, str) or not 0 < len(key) <= 128 for key in shot_ids
    ) or len(shot_ids) != len(set(shot_ids)):
        raise ValueError("Invalid prepared shot keys")
    input_message.encode("utf-8")
    for key in shot_ids:
        key.encode("utf-8")
    db.execute("BEGIN IMMEDIATE")
    try:
        db.execute(
            "INSERT INTO executions VALUES (?,?,?,?)",
            (execution_id, project_id, input_message, json.dumps(shot_ids, ensure_ascii=False)),
        )
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise


def _destination(db: sqlite3.Connection, project_id: str, artifact_id: str, digest: str) -> Path:
    return _root(db) / "projects" / project_id / "artifacts" / f"{artifact_id}.{digest[7:]}.json"


def _publish(destination: Path, body: bytes) -> None:
    # The caller holds the data-root lock. An existing object is never overwritten.
    directory = destination.parent
    for path in (directory.parent.parent, directory.parent, directory):
        if path.exists():
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ValueError("Managed directory was redirected")
        else:
            path.mkdir()
            _sync_directory(path.parent)
    try:
        _check_file(destination)
    except FileNotFoundError:
        pass
    else:
        if destination.read_bytes() != body:
            raise ValueError("Conflicting immutable artifact bytes")
        return
    descriptor, name = tempfile.mkstemp(prefix=".story-", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as temporary:
            temporary.write(body)
            temporary.flush()
            os.fsync(temporary.fileno())
        try:
            os.link(name, destination)  # Exclusive publication on Windows and Linux.
        except FileExistsError:
            _check_file(destination)
            if destination.read_bytes() != body:
                raise ValueError("Conflicting immutable artifact bytes")
        _sync_directory(directory)
    finally:
        os.unlink(name)


def save_story(
    db: sqlite3.Connection, execution_id: str, operation_id: str,
    artifact_id: str, story: StoryV1,
) -> ArtifactRef:
    """Commit the first exact Story binding; replay returns the committed ref."""
    _uuid(execution_id)
    _uuid(artifact_id)
    body = canonical_json(story)
    story = parse_json_model(body, StoryV1)
    digest = sha256_digest(body)
    row = db.execute(
        "SELECT project_id, shot_ids FROM executions WHERE execution_id=?", (execution_id,)
    ).fetchone()
    if row is None:
        raise ValueError("Unknown test execution")
    project_id, shot_keys = row
    if [shot.shot_id for shot in story.shots] != json.loads(shot_keys):
        raise ValueError("Story does not cover prepared shot keys")
    uri = f"kinodel://projects/{project_id}/artifacts/{artifact_id}"
    ref = ArtifactRef(
        artifact_id=artifact_id, project_id=project_id, execution_id=execution_id,
        operation_id=operation_id, schema_id="story", schema_version="1",
        produced_by_stage="storytell", digest=digest, uri=uri,
        media_type="application/json",
    )
    committed = db.execute(
        "SELECT execution_id, artifact_id, digest FROM artifacts WHERE operation_id=?", (operation_id,)
    ).fetchone()
    if committed:
        if committed[0] != execution_id or committed[2] != digest:
            raise ValueError("Operation replay conflicts with committed Story")
        return read_story(db, execution_id)[0]
    _publish(_destination(db, project_id, artifact_id, digest), body)
    db.execute("BEGIN IMMEDIATE")
    try:
        db.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            (artifact_id, execution_id, operation_id, digest, uri, "story", "1", "storytell"),
        )
        db.execute(
            "INSERT INTO execution_bindings VALUES (?,?,?,?)",
            (execution_id, "story", artifact_id, 1),
        )
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return ref


def read_story(db: sqlite3.Connection, execution_id: str) -> tuple[ArtifactRef, StoryV1]:
    _uuid(execution_id)
    row = db.execute("""
        SELECT e.project_id, a.artifact_id, a.operation_id, a.digest, a.uri,
               a.schema_id, a.schema_version, a.produced_by_stage
        FROM execution_bindings b
        JOIN executions e ON e.execution_id=b.execution_id
        JOIN artifacts a ON a.artifact_id=b.artifact_id AND a.execution_id=b.execution_id
        WHERE b.execution_id=? AND b.slot='story' AND b.binding_revision=1
    """, (execution_id,)).fetchone()
    if row is None:
        raise ValueError("Story binding not committed")
    project_id, artifact_id, operation_id, digest, uri, schema_id, version, stage = row
    ref = ArtifactRef(
        project_id=project_id, execution_id=execution_id, artifact_id=artifact_id,
        operation_id=operation_id, digest=digest, uri=uri, schema_id=schema_id,
        schema_version=version, produced_by_stage=stage, media_type="application/json",
    )
    path = _destination(db, project_id, artifact_id, digest)
    _check_file(path)
    body = path.read_bytes()
    if sha256_digest(body) != digest:
        raise ValueError("Committed Story bytes failed integrity check")
    story = parse_json_model(body, StoryV1)
    if canonical_json(story) != body:
        raise ValueError("Committed Story is not canonical")
    return ref, story
