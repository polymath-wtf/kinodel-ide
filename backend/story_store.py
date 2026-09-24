"""Internal step-1 Story fixture storage; no public cinematic start or review."""

import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile

from backend.domain import (ArtifactRef, OwnerResponseV1, StoryV1, canonical_json,
                            make_operation_id, parse_json_model, sha256_digest)
from backend.database import _check_file, _sync_directory


DISCUSSION_LIMIT = 4096
DISCUSSION_TURNS = 10


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


def _assert_writable(db: sqlite3.Connection, execution_id: str) -> None:
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version >= 8 and db.execute(
        "SELECT 1 FROM execution_controls WHERE execution_id=? AND kind='cancel'", (execution_id,)
    ).fetchone():
        raise ValueError("Execution is cancelling")
    if version >= 7 and db.execute(
        "SELECT 1 FROM execution_outcomes WHERE execution_id=?", (execution_id,)
    ).fetchone():
        raise ValueError("Execution already has a terminal outcome")


def _validated_test_inputs(project_id: str, input_message: str, shot_ids: list[str]) -> None:
    _uuid(project_id)
    if not isinstance(input_message, str) or not 0 < len(input_message) <= 131072:
        raise ValueError("Invalid test input")
    if not isinstance(shot_ids, list) or not 1 <= len(shot_ids) <= 128 or any(
        not isinstance(key, str) or not 0 < len(key) <= 128 for key in shot_ids
    ) or len(shot_ids) != len(set(shot_ids)):
        raise ValueError("Invalid prepared shot keys")
    input_message.encode("utf-8")
    for key in shot_ids:
        key.encode("utf-8")


def create_test_execution(
    db: sqlite3.Connection, project_id: str, execution_id: str,
    input_message: str, shot_ids: list[str],
) -> None:
    """A private text fixture, never a partial cinematic Brief/Run."""
    _uuid(execution_id)
    _validated_test_inputs(project_id, input_message, shot_ids)
    db.execute("BEGIN IMMEDIATE")
    try:
        db.execute(
            "INSERT INTO executions (execution_id,project_id,input_message,shot_ids) VALUES (?,?,?,?)",
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


def _bind_story(db: sqlite3.Connection, execution_id: str, artifact_id: str,
                expected_revision: int | None) -> None:
    _assert_writable(db, execution_id)
    if expected_revision is None:
        db.execute("INSERT INTO execution_bindings VALUES (?,?,?,?)", (execution_id, "story", artifact_id, 1))
    else:
        updated = db.execute(
            "UPDATE execution_bindings SET artifact_id=?, binding_revision=binding_revision+1 "
            "WHERE execution_id=? AND slot='story' AND binding_revision=?",
            (artifact_id, execution_id, expected_revision),
        )
        if updated.rowcount != 1:
            raise ValueError("Stale Story binding revision")


def prepare_story_operation(
    db: sqlite3.Connection, execution_id: str, activation_id: str, *,
    prior_ref: ArtifactRef | None = None, feedback: str | None = None,
    expected_revision: int | None = None, request_id: str | None = None,
    action: str | None = None,
) -> tuple[str, str, tuple[ArtifactRef | dict, str] | None]:
    """Pin exact test inputs before the model substitute; return a committed replay if present."""
    _uuid(execution_id)
    kind = action or ("revise" if prior_ref is not None else "generate")
    if kind not in ("generate", "revise", "clarify") or (kind == "generate") != (prior_ref is None):
        raise ValueError("Invalid owner operation kind")
    operation_id = make_operation_id(execution_id, "storytell", activation_id, kind)
    row = db.execute("SELECT input_message, shot_ids FROM executions WHERE execution_id=?", (execution_id,)).fetchone()
    if row is None:
        raise ValueError("Unknown test execution")
    if kind == "generate":
        if feedback is not None or expected_revision is not None:
            raise ValueError("Generate inputs conflict with revision inputs")
        inputs = ["test-story-generate-v1", row[0], json.loads(row[1])]
    else:
        if prior_ref is None:
            raise ValueError("Missing prior Story ref")
        if not isinstance(feedback, str) or not 0 < len(feedback) <= 131072:
            raise ValueError("Revision feedback must be nonempty and bounded")
        feedback.encode("utf-8")
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValueError("Missing expected Story binding revision")
        if prior_ref.execution_id != execution_id:
            raise ValueError("Prior Story belongs to another execution")
        if request_id is not None:
            previous = db.execute("SELECT action,message,subject_artifact_id,binding_revision,applied_activation "
                                  "FROM review_requests WHERE execution_id=? AND request_id=?",
                                  (execution_id, request_id)).fetchone()
            if previous != (kind, feedback, prior_ref.artifact_id, expected_revision, activation_id):
                raise ValueError("Owner request does not match activation")
            history = db.execute("SELECT r.action,r.message,o.owner_response FROM review_requests r "
                                 "LEFT JOIN story_operations o ON o.execution_id=r.execution_id "
                                 "AND o.activation_id=r.applied_activation "
                                 "WHERE r.execution_id=? "
                                 "AND r.request_revision <= (SELECT request_revision FROM review_requests WHERE request_id=?) "
                                 "AND r.action IN ('revise','clarify') ORDER BY r.request_revision DESC LIMIT ?",
                                 (execution_id, request_id, DISCUSSION_TURNS)).fetchall()[::-1]
            context = [[act, msg[:DISCUSSION_LIMIT],
                        json.loads(reply)["explanation"][:DISCUSSION_LIMIT] if reply else None]
                       for act, msg, reply in history]
        else:
            if kind == "clarify":
                raise ValueError("Clarification requires a review request")
            context = []
        inputs = ["test-story-owner-v2", kind, request_id, prior_ref.model_dump(mode="json"),
                  feedback, context]
    prepared = json.dumps(inputs, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    digest = sha256_digest(prepared.encode("utf-8"))
    existing = db.execute(
        "SELECT operation_id, input_digest, prepared_inputs, expected_revision, artifact_id, next_activation, "
        "owner_response, discussion_activation "
        "FROM story_operations WHERE execution_id=? AND activation_id=?", (execution_id, activation_id),
    ).fetchone()
    if existing:
        pinned = json.loads(existing[2])
        if kind == "revise" and prior_ref is not None and pinned[:1] == ["test-story-revise-v1"]:
            if pinned[1:] != [prior_ref.model_dump(mode="json"), feedback]:
                raise ValueError("Legacy operation inputs conflict")
            prepared, digest = existing[2], existing[1]
        elif kind != "generate" and request_id is not None:
            # Later reviews cannot change the context of a previously prepared call.
            inputs[-1] = pinned[-1]
            prepared = json.dumps(inputs, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            digest = sha256_digest(prepared.encode("utf-8"))
        if existing[:4] != (operation_id, digest, prepared, expected_revision):
            raise ValueError("Operation activation or prepared inputs conflict")
        if existing[4] is not None and existing[6] is not None:
            raise ValueError("Owner operation has conflicting results")
        result = None
        if existing[4] is not None:
            result = (read_story(db, execution_id, artifact_id=existing[4])[0], existing[5])
        elif existing[6] is not None:
            response = parse_json_model(existing[6].encode("utf-8"), OwnerResponseV1)
            if (canonical_json(response).decode("utf-8") != existing[6]
                    or (kind == "clarify" and response.status != "clarified")
                    or (kind == "revise" and response.status not in ("needs_input", "out_of_scope"))
                    or existing[7] != sha256_digest(json.dumps(
                        ["kinodel.story-discussion.v1", operation_id, digest], separators=(",", ":")
                    ).encode("utf-8"))):
                raise ValueError("Committed owner response mismatch")
            result = (response.model_dump(mode="json"), existing[7])
        if result is None:
            _assert_writable(db, execution_id)
        return operation_id, digest, result
    _assert_writable(db, execution_id)
    if prior_ref is not None:
        if read_story(db, execution_id, artifact_id=prior_ref.artifact_id)[0] != prior_ref:
            raise ValueError("Prior Story ref mismatch")
    current = db.execute(
        "SELECT artifact_id, binding_revision FROM execution_bindings WHERE execution_id=? AND slot='story'",
        (execution_id,),
    ).fetchone()
    if (current is None and expected_revision is not None) or (
        current is not None and (expected_revision != current[1] or prior_ref is None or prior_ref.artifact_id != current[0])
    ):
        raise ValueError("Stale or missing expected Story binding revision")
    db.execute("BEGIN IMMEDIATE")
    try:
        _assert_writable(db, execution_id)
        db.execute(
            "INSERT INTO story_operations (operation_id,execution_id,activation_id,input_digest,"
            "prepared_inputs,expected_revision,artifact_id,next_activation) VALUES (?,?,?,?,?,?,?,?)",
            (operation_id, execution_id, activation_id, digest, prepared, expected_revision, None, None),
        )
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return operation_id, digest, None


def commit_owner_response(db: sqlite3.Connection, execution_id: str, activation_id: str,
                          input_digest: str, response: dict) -> str:
    """Commit a bounded explanation without changing the Story binding."""
    body = canonical_json(OwnerResponseV1.model_validate(response))
    row = db.execute("SELECT operation_id,input_digest,prepared_inputs,expected_revision,owner_response,"
                     "discussion_activation,artifact_id FROM story_operations WHERE execution_id=? AND activation_id=?",
                     (execution_id, activation_id)).fetchone()
    if row is None or row[1] != input_digest or row[6] is not None:
        raise ValueError("Owner response inputs mismatch")
    action = json.loads(row[2])[1]
    result = parse_json_model(body, OwnerResponseV1)
    if (action == "clarify" and result.status != "clarified") or (
        action == "revise" and result.status not in ("needs_input", "out_of_scope")
    ):
        raise ValueError("Owner response status conflicts with action")
    if row[4] is not None:
        if row[4] != body.decode("utf-8") or row[5] != sha256_digest(json.dumps(
            ["kinodel.story-discussion.v1", row[0], input_digest], separators=(",", ":")
        ).encode("utf-8")):
            raise ValueError("Owner response replay conflict")
        return row[5]
    activation = sha256_digest(json.dumps(
        ["kinodel.story-discussion.v1", row[0], input_digest], separators=(",", ":")
    ).encode("utf-8"))
    db.execute("BEGIN IMMEDIATE")
    try:
        _assert_writable(db, execution_id)
        current = db.execute("SELECT binding_revision FROM execution_bindings WHERE execution_id=? AND slot='story'",
                             (execution_id,)).fetchone()
        if current != (row[3],):
            raise ValueError("Story changed during owner discussion")
        db.execute("UPDATE story_operations SET owner_response=?,discussion_activation=? "
                   "WHERE operation_id=? AND owner_response IS NULL",
                   (body.decode("utf-8"), activation, row[0]))
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return activation


def commit_story_operation(
    db: sqlite3.Connection, execution_id: str, activation_id: str, input_digest: str,
    artifact_id: str, story: StoryV1,
) -> tuple[ArtifactRef, str]:
    """Publish Story bytes, then atomically record artifact, binding and transition."""
    _uuid(execution_id)
    row = db.execute(
        "SELECT operation_id, input_digest, expected_revision, artifact_id, next_activation "
        "FROM story_operations WHERE execution_id=? AND activation_id=?", (execution_id, activation_id),
    ).fetchone()
    if row is None:
        raise ValueError("Unknown prepared activation")
    operation_id, pinned_digest, expected_revision, committed_id, next_activation = row
    if input_digest != pinned_digest:
        raise ValueError("Prepared input digest mismatch")
    if committed_id is not None:
        return read_story(db, execution_id, artifact_id=committed_id)[0], next_activation
    _assert_writable(db, execution_id)
    _uuid(artifact_id)
    body = canonical_json(story)
    story = parse_json_model(body, StoryV1)
    digest = sha256_digest(body)
    execution = db.execute("SELECT project_id, shot_ids FROM executions WHERE execution_id=?", (execution_id,)).fetchone()
    project_id, shot_keys = execution
    if [shot.shot_id for shot in story.shots] != json.loads(shot_keys):
        raise ValueError("Story does not cover prepared shot keys")
    current = db.execute(
        "SELECT binding_revision FROM execution_bindings WHERE execution_id=? AND slot='story'", (execution_id,),
    ).fetchone()
    if (current[0] if current else None) != expected_revision:
        raise ValueError("Stale Story binding revision")
    uri = f"kinodel://projects/{project_id}/artifacts/{artifact_id}"
    ref = ArtifactRef(artifact_id=artifact_id, project_id=project_id, execution_id=execution_id,
                      operation_id=operation_id, schema_id="story", schema_version="1",
                      produced_by_stage="storytell", digest=digest, uri=uri, media_type="application/json")
    next_activation = sha256_digest(json.dumps(
        ["kinodel.story-transition.v1", operation_id, "story-hitl"], separators=(",", ":")
    ).encode("utf-8"))
    _publish(_destination(db, project_id, artifact_id, digest), body)
    db.execute("BEGIN IMMEDIATE")
    try:
        actual = db.execute(
            "SELECT binding_revision FROM execution_bindings WHERE execution_id=? AND slot='story'", (execution_id,),
        ).fetchone()
        if actual != current:
            raise ValueError("Stale Story binding revision")
        db.execute("INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
                   (artifact_id, execution_id, operation_id, digest, uri, "story", "1", "storytell"))
        _bind_story(db, execution_id, artifact_id, expected_revision)
        db.execute("UPDATE story_operations SET artifact_id=?, next_activation=? WHERE operation_id=? AND artifact_id IS NULL",
                   (artifact_id, next_activation, operation_id))
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return ref, next_activation


def save_story(
    db: sqlite3.Connection, execution_id: str, operation_id: str,
    artifact_id: str, story: StoryV1, *, expected_revision: int | None = None,
) -> ArtifactRef:
    """Commit an exact Story revision; replay never restores a superseded binding."""
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
        return read_story(db, execution_id, artifact_id=committed[1])[0]
    _assert_writable(db, execution_id)
    current = db.execute(
        "SELECT binding_revision FROM execution_bindings WHERE execution_id=? AND slot='story'",
        (execution_id,),
    ).fetchone()
    if (current is None and expected_revision is not None) or (
        current is not None and expected_revision != current[0]
    ):
        raise ValueError("Stale or missing expected Story binding revision")
    _publish(_destination(db, project_id, artifact_id, digest), body)
    db.execute("BEGIN IMMEDIATE")
    try:
        actual = db.execute(
            "SELECT binding_revision FROM execution_bindings WHERE execution_id=? AND slot='story'",
            (execution_id,),
        ).fetchone()
        if actual != current:
            raise ValueError("Stale Story binding revision")
        db.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            (artifact_id, execution_id, operation_id, digest, uri, "story", "1", "storytell"),
        )
        _bind_story(db, execution_id, artifact_id, expected_revision)
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return ref


def read_story(
    db: sqlite3.Connection, execution_id: str, *, artifact_id: str | None = None,
) -> tuple[ArtifactRef, StoryV1]:
    _uuid(execution_id)
    if artifact_id is not None:
        _uuid(artifact_id)
    row = db.execute("""
        SELECT e.project_id, a.artifact_id, a.operation_id, a.digest, a.uri,
               a.schema_id, a.schema_version, a.produced_by_stage
        FROM artifacts a
        JOIN executions e ON e.execution_id=a.execution_id
        WHERE a.execution_id=? AND a.artifact_id=COALESCE(?, (
            SELECT b.artifact_id FROM execution_bindings b
            WHERE b.execution_id=a.execution_id AND b.slot='story'
        ))
    """, (execution_id, artifact_id)).fetchone()
    if row is None:
        raise ValueError("Story binding not committed")
    project_id, stored_artifact_id, operation_id, digest, uri, schema_id, version, stage = row
    ref = ArtifactRef(
        project_id=project_id, execution_id=execution_id, artifact_id=stored_artifact_id,
        operation_id=operation_id, digest=digest, uri=uri, schema_id=schema_id,
        schema_version=version, produced_by_stage=stage, media_type="application/json",
    )
    path = _destination(db, project_id, stored_artifact_id, digest)
    _check_file(path)
    body = path.read_bytes()
    if sha256_digest(body) != digest:
        raise ValueError("Committed Story bytes failed integrity check")
    story = parse_json_model(body, StoryV1)
    if canonical_json(story) != body:
        raise ValueError("Committed Story is not canonical")
    return ref, story
