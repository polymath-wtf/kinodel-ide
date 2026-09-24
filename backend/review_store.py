"""Internal Story review records. Graph wait binding and delivery stay worker-owned."""

from dataclasses import dataclass
import json
import re
import sqlite3

from backend.domain import ArtifactRef, sha256_digest
from backend.story_store import _uuid, read_story


@dataclass(frozen=True)
class ReviewRef:
    request_id: str
    revision: int
    digest: str


@dataclass(frozen=True)
class DecisionRef:
    decision_id: str
    work_id: str


def _digest(*values: object) -> str:
    return sha256_digest(json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def prepare_story_review(db: sqlite3.Connection, execution_id: str, trigger_activation: str,
                         subject: ArtifactRef, binding_revision: int,
                         *, previous_request_id: str | None = None) -> ReviewRef:
    """Create one immutable request for one Story binding, never a latest-result lookup."""
    _uuid(execution_id)
    if not isinstance(trigger_activation, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", trigger_activation) is None:
        raise ValueError("Invalid review trigger activation")
    if type(binding_revision) is not int or binding_revision < 1:
        raise ValueError("Invalid Story binding revision")
    if subject.execution_id != execution_id or read_story(db, execution_id, artifact_id=subject.artifact_id)[0] != subject:
        raise ValueError("Review subject mismatch")
    existing = db.execute("SELECT request_id, subject_artifact_id, subject_digest, binding_revision, "
                          "previous_request_id, request_revision, request_digest FROM review_requests "
                          "WHERE execution_id=? AND trigger_activation=?", (execution_id, trigger_activation)).fetchone()
    if existing:
        if existing[1:5] != (subject.artifact_id, subject.digest, binding_revision, previous_request_id):
            raise ValueError("Review trigger conflict")
        return ReviewRef(existing[0], existing[5], existing[6])
    db.execute("BEGIN IMMEDIATE")
    try:
        last = db.execute("SELECT request_id, applied_activation, action FROM review_requests WHERE execution_id=? "
                          "ORDER BY request_revision DESC LIMIT 1", (execution_id,)).fetchone()
        if (last is None and previous_request_id is not None) or (
            last is not None and (last[0] != previous_request_id or last[1] is None)
        ):
            raise ValueError("Previous review not applied")
        if last is not None and last[2] == "approve":
            raise ValueError("Story already approved")
        current = db.execute("SELECT artifact_id, binding_revision FROM execution_bindings "
                             "WHERE execution_id=? AND slot='story'", (execution_id,)).fetchone()
        if current != (subject.artifact_id, binding_revision):
            raise ValueError("Stale Story binding revision")
        revision = 1 if last is None else db.execute(
            "SELECT request_revision FROM review_requests WHERE request_id=?", (last[0],)
        ).fetchone()[0] + 1
        request_id = _digest("kinodel.story-review.v1", execution_id, trigger_activation)
        digest = _digest("kinodel.story-review-body.v1", request_id, revision,
                         subject.artifact_id, subject.digest, binding_revision, previous_request_id)
        db.execute("INSERT INTO review_requests (request_id,execution_id,trigger_activation,"
                   "subject_artifact_id,subject_digest,binding_revision,request_revision,"
                   "previous_request_id,request_digest) VALUES (?,?,?,?,?,?,?,?,?)",
                   (request_id, execution_id, trigger_activation, subject.artifact_id, subject.digest,
                    binding_revision, revision, previous_request_id, digest))
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return ReviewRef(request_id, revision, digest)


def bind_story_wait(db: sqlite3.Connection, execution_id: str, request_id: str,
                    checkpoint_id: str, task_id: str, interrupt_id: str) -> None:
    """Called only after a durable checkpoint exposes this exact interrupt."""
    if not all(isinstance(item, str) and item for item in (checkpoint_id, task_id, interrupt_id)):
        raise ValueError("Invalid wait binding")
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute("SELECT checkpoint_id,task_id,interrupt_id,decision_id,applied_activation "
                         "FROM review_requests WHERE execution_id=? AND request_id=?",
                         (execution_id, request_id)).fetchone()
        if row is None or row[3] is not None or row[4] is not None:
            raise ValueError("Review wait not open")
        if row[0] is None:
            db.execute("UPDATE review_requests SET checkpoint_id=?,task_id=?,interrupt_id=? "
                       "WHERE request_id=?", (checkpoint_id, task_id, interrupt_id, request_id))
        elif row[:3] != (checkpoint_id, task_id, interrupt_id):
            raise ValueError("Review wait binding conflict")
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise


def accept_story_decision(db: sqlite3.Connection, execution_id: str, request_id: str,
                          request_digest: str, expected_revision: int, command_key: str,
                          action: str, message: str | None) -> DecisionRef:
    """Idempotent acceptance; a unique resume work item commits with the decision."""
    _uuid(execution_id)
    if not isinstance(command_key, str) or not 0 < len(command_key) <= 128:
        raise ValueError("Invalid command key")
    if action not in ("approve", "revise", "clarify"):
        raise ValueError("Invalid review action")
    if (action == "approve" and message is not None) or (action != "approve" and (
        not isinstance(message, str) or not message.strip() or len(message) > 131072
    )):
        raise ValueError("Invalid review message")
    if message is not None:
        message.encode("utf-8")
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValueError("Invalid expected revision")
    payload = _digest("kinodel.story-decision.v1", request_id, request_digest,
                      expected_revision, action, message)
    db.execute("BEGIN IMMEDIATE")
    try:
        old = db.execute("SELECT decision_id,decision_digest,request_id FROM review_requests "
                         "WHERE execution_id=? AND decision_key=?", (execution_id, command_key)).fetchone()
        if old is not None:
            if old[1] != payload or old[2] != request_id:
                raise ValueError("Decision command conflict")
            work_id = db.execute("SELECT work_id FROM execution_work WHERE execution_id=? "
                                 "AND kind='resume' AND source_id=?", (execution_id, request_id)).fetchone()[0]
            db.execute("COMMIT")
            return DecisionRef(old[0], work_id)
        row = db.execute("SELECT request_digest,binding_revision,subject_artifact_id,subject_digest,"
                         "checkpoint_id,decision_id,applied_activation FROM review_requests "
                         "WHERE execution_id=? AND request_id=?", (execution_id, request_id)).fetchone()
        if row is None or row[6] is not None:
            raise ValueError("stale or applied review request")
        if row[5] is not None:
            raise ValueError("Review decision already accepted")
        if row[4] is None:
            raise ValueError("Review wait not bound")
        if (row[0], row[1]) != (request_digest, expected_revision):
            raise ValueError("Stale review request digest or revision")
        current = db.execute("SELECT b.artifact_id,b.binding_revision,a.digest FROM execution_bindings b "
                             "JOIN artifacts a ON a.artifact_id=b.artifact_id "
                             "WHERE b.execution_id=? AND b.slot='story'", (execution_id,)).fetchone()
        if current != (row[2], row[1], row[3]):
            raise ValueError("Stale review subject")
        decision_id = _digest("kinodel.story-decision-id.v1", request_id, command_key)
        work_id = _digest("kinodel.story-resume-work.v1", decision_id)
        db.execute("UPDATE review_requests SET decision_key=?,decision_digest=?,decision_id=?,"
                   "action=?,message=? WHERE request_id=?",
                   (command_key, payload, decision_id, action, message, request_id))
        db.execute("INSERT INTO execution_work VALUES (?,?,?,?,?,?,?)",
                   (work_id, execution_id, "resume", request_id, payload, decision_id, "pending"))
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return DecisionRef(decision_id, work_id)


def apply_story_decision(db: sqlite3.Connection, execution_id: str, request_id: str,
                         decision_id: str) -> str:
    """Commit exact approval/route receipt; replay never changes the current binding."""
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute("SELECT decision_id,action,subject_artifact_id,subject_digest,"
                         "binding_revision,applied_activation FROM review_requests "
                         "WHERE execution_id=? AND request_id=?", (execution_id, request_id)).fetchone()
        if row is None or row[0] != decision_id or row[1] is None:
            raise ValueError("Unknown accepted review decision")
        if row[5] is not None:
            db.execute("COMMIT")
            return row[5]
        current = db.execute("SELECT b.artifact_id,b.binding_revision,a.digest FROM execution_bindings b "
                             "JOIN artifacts a ON a.artifact_id=b.artifact_id "
                             "WHERE b.execution_id=? AND b.slot='story'", (execution_id,)).fetchone()
        if current != (row[2], row[4], row[3]):
            raise ValueError("Stale review subject at apply")
        next_activation = _digest("kinodel.story-review-apply.v1", request_id, decision_id, row[1])
        db.execute("UPDATE review_requests SET applied_activation=? WHERE request_id=?",
                   (next_activation, request_id))
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return next_activation
