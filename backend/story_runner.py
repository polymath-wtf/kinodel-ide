"""Single local runner for the internal Story fixture and its durable work."""

import asyncio
import sqlite3
from typing import Awaitable, Callable

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from backend.domain import ArtifactRef, StoryV1, sha256_digest
from backend.review_store import bind_story_wait
from backend.story_control import cancel_requested
from backend.story_graph import StoryOwnerUnavailable, build_story_graph
from backend.story_start import load_test_story_start, validate_story_storage
from backend.story_store import read_story


def _source_wait(saved, checkpoint_id: str, task_id: str, interrupt_id: str, request_id: str):
    if saved is None or saved.config["configurable"]["checkpoint_id"] != checkpoint_id:
        raise ValueError("Review source checkpoint missing")
    values = saved.checkpoint["channel_values"]
    if values.get("review_ref", {}).get("request_id") != request_id:
        raise ValueError("Review source state mismatch")
    if not any(task == task_id and channel == "__interrupt__" and len(value) == 1
               and value[0].id == interrupt_id and value[0].value == values["review_ref"]
               for task, channel, value in saved.pending_writes):
        raise ValueError("Review source interrupt mismatch")


class _WorkerStopped(Exception):
    pass


async def _invoke(db, graph, invocation, config, execution_id, stop):
    task = asyncio.create_task(graph.ainvoke(invocation, config, durability="sync"))
    try:
        while not task.done():
            if cancel_requested(db, execution_id) or (stop is not None and stop.is_set()):
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)  # Saver/task cleanup precedes terminal/lock release.
                if stop is not None and stop.is_set():
                    raise _WorkerStopped()
                return False
            await asyncio.wait({task}, timeout=0.05)
        try:
            await task
        except Exception:
            if not cancel_requested(db, execution_id):
                raise
        if stop is not None and stop.is_set():
            raise _WorkerStopped()
        return not cancel_requested(db, execution_id)
    except asyncio.CancelledError:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        raise


def _finish_cancel(db, execution_id):
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute("SELECT command_key,work_id FROM execution_controls WHERE execution_id=? AND kind='cancel'",
                         (execution_id,)).fetchone()
        if row is None:
            raise ValueError("Missing cancellation control")
        work = db.execute("SELECT execution_id,kind,source_id FROM execution_work WHERE work_id=?",
                          (row[1],)).fetchone()
        if work != (execution_id, "cancel", row[0]):
            raise ValueError("Cancellation work identity mismatch")
        outcome = db.execute("SELECT outcome,source_id FROM execution_outcomes WHERE execution_id=?",
                             (execution_id,)).fetchone()
        if outcome is None:
            db.execute("INSERT INTO execution_outcomes VALUES (?, 'cancelled', ?, NULL)", (execution_id, row[0]))
        elif outcome != ("cancelled", row[0]):
            raise ValueError("Cancellation conflicts with terminal outcome")
        db.execute("UPDATE execution_work SET status='obsolete',work_version=work_version+1 "
                   "WHERE execution_id=? AND kind!='cancel' AND status IN ('pending','claimed','blocked')",
                   (execution_id,))
        db.execute("UPDATE execution_work SET status='completed',work_version=work_version+1 "
                   "WHERE work_id=? AND status!='completed'", (row[1],))
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise


async def _run_one(db, saver, graph, work, stop):
    work_id, execution_id, kind, source_id, payload_digest, resume_ref = work
    receipt, initial = load_test_story_start(db, execution_id)
    outcome = db.execute("SELECT outcome,source_id FROM execution_outcomes WHERE execution_id=?",
                         (execution_id,)).fetchone()
    if outcome:
        db.execute("UPDATE execution_work SET status=?,work_version=work_version+1 WHERE work_id=?",
                   ("completed" if kind == "resume" and outcome == ("completed", source_id) else "obsolete", work_id))
        return
    config = {"configurable": {"thread_id": execution_id}}
    saved = await saver.aget_tuple(config)
    snapshot = await graph.aget_state(config) if saved is not None else None
    if snapshot is not None and (snapshot.values.get("execution_id") != execution_id
                                 or snapshot.values.get("project_id") != initial["project_id"]):
        raise ValueError("Checkpoint execution identity mismatch")
    decision = None
    if kind == "start":
        if work_id != receipt.work_id or source_id != execution_id or payload_digest != db.execute(
            "SELECT start_digest FROM executions WHERE execution_id=?", (execution_id,)
        ).fetchone()[0] or resume_ref is not None:
            raise ValueError("Start work identity mismatch")
    elif kind == "resume":
        decision = db.execute(
            "SELECT decision_id,decision_digest,checkpoint_id,task_id,interrupt_id,applied_activation,"
            "request_digest,request_revision,binding_revision,subject_artifact_id "
            "FROM review_requests WHERE execution_id=? AND request_id=?", (execution_id, source_id),
        ).fetchone()
        if (decision is None or decision[0] != resume_ref or decision[1] != payload_digest
                or not all(decision[2:5]) or saved is None):
            raise ValueError("Resume work identity mismatch")
        source_config = {"configurable": {"thread_id": execution_id, "checkpoint_id": decision[2]}}
        source = await saver.aget_tuple(source_config)
        _source_wait(source, decision[2], decision[3], decision[4], source_id)
        if (source.checkpoint["channel_values"].get("review_ref") != {
                "request_id": source_id, "digest": decision[6], "revision": decision[7],
                "binding_revision": decision[8]
        } or source.checkpoint["channel_values"].get("story_ref", {}).get("artifact_id") != decision[9]):
            raise ValueError("Source review payload differs from accepted decision")
        # A checkpoint from another fork/thread must never borrow this review's decision.
        cursor = saved
        while cursor is not None and cursor.config["configurable"]["checkpoint_id"] != decision[2]:
            cursor = await saver.aget_tuple(cursor.parent_config) if cursor.parent_config else None
        if cursor is None:
            raise ValueError("Review source is not in checkpoint lineage")
    elif kind == "reconcile":
        if (saved is None or saved.config["configurable"]["checkpoint_id"] != source_id
                or payload_digest != db.execute("SELECT start_digest FROM executions WHERE execution_id=?",
                                                (execution_id,)).fetchone()[0] or resume_ref is not None):
            raise ValueError("Reconcile work identity mismatch")
    else:
        raise ValueError("Unsupported Story work kind")

    if saved is None:
        if kind != "start":
            raise ValueError("Cannot resume without a checkpoint")
        invocation = initial
    elif kind in ("start", "reconcile"):
        # Never re-submit initial state after any checkpoint was persisted.
        invocation = None
    else:
        assert saved is not None and snapshot is not None and decision is not None
        if saved.config["configurable"]["checkpoint_id"] == decision[2]:
            already_written = [value for task, channel, value in saved.pending_writes
                               if task == decision[3] and channel == "__resume__"]
            if already_written:
                if already_written != [[decision[0]]]:
                    raise ValueError("Conflicting persisted resume value")
                invocation = None
            elif decision[5] is not None:
                raise ValueError("Applied decision has no persisted resume value")
            else:
                invocation = Command(resume={decision[4]: decision[0]})
        else:
            if decision[5] is None and snapshot.values.get("decision_id") != decision[0]:
                raise ValueError("Resume moved beyond its source without a matching decision")
            invocation = None

    if (snapshot is None or invocation is not None or (snapshot.next and
            (not snapshot.interrupts or (kind == "resume" and
             snapshot.interrupts[0].value["request_id"] == source_id)))):
        if not await _invoke(db, graph, invocation, config, execution_id, stop):
            return
    if cancel_requested(db, execution_id):
        return
    snapshot = await graph.aget_state(config)
    saved = await saver.aget_tuple(config)
    if (saved is None or snapshot.config["configurable"]["checkpoint_id"] != saved.config["configurable"]["checkpoint_id"]
            or snapshot.values.get("execution_id") != execution_id
            or snapshot.values.get("project_id") != initial["project_id"]):
        raise ValueError("Checkpoint changed during Story work")
    checkpoint_id = snapshot.config["configurable"]["checkpoint_id"]
    if snapshot.interrupts:
        if snapshot.next != ("story_wait",) or len(snapshot.tasks) != 1 or len(snapshot.interrupts) != 1:
            raise ValueError("Unexpected Story interrupt")
        task, interrupt = snapshot.tasks[0], snapshot.interrupts[0]
        request = interrupt.value
        if task.name != "story_wait" or request != snapshot.values.get("review_ref"):
            raise ValueError("Review checkpoint payload mismatch")
        row = db.execute(
            "SELECT request_digest,request_revision,binding_revision,subject_artifact_id,decision_id,"
            "checkpoint_id,task_id,interrupt_id "
            "FROM review_requests WHERE execution_id=? AND request_id=?", (execution_id, request["request_id"]),
        ).fetchone()
        if (row is None or row[:3] != (request["digest"], request["revision"], request["binding_revision"])
                or row[3] != snapshot.values["story_ref"]["artifact_id"]):
            raise ValueError("Current review identity mismatch")
        _source_wait(saved, checkpoint_id, task.id, interrupt.id, request["request_id"])
        if row[4] is not None and (kind != "start" or row[5:] != (checkpoint_id, task.id, interrupt.id)):
            raise ValueError("Decided review is not this start's settled wait")
        if kind == "resume" and db.execute(
            "SELECT applied_activation FROM review_requests WHERE execution_id=? AND request_id=?",
            (execution_id, source_id),
        ).fetchone()[0] is None:
            raise ValueError("Previous decision has not been applied")
        if row[4] is None:
            bind_story_wait(db, execution_id, request["request_id"], checkpoint_id, task.id, interrupt.id)
    elif snapshot.next:
        raise ValueError("Story segment stopped before a stable wait")
    else:
        approved = snapshot.values.get("approved_story")
        row = db.execute(
            "SELECT r.request_id,r.subject_artifact_id FROM review_requests r "
            "JOIN execution_bindings b ON b.execution_id=r.execution_id AND b.slot='story' "
            "WHERE r.execution_id=? AND r.action='approve' AND r.applied_activation IS NOT NULL "
            "AND r.subject_artifact_id=b.artifact_id AND r.binding_revision=b.binding_revision",
            (execution_id,),
        ).fetchone()
        applied = db.execute("SELECT applied_activation FROM review_requests WHERE execution_id=? AND request_id=?",
                             (execution_id, source_id)).fetchone() if kind == "resume" else None
        if (row is None or (kind == "resume" and (applied is None or applied[0] is None or row[0] != source_id))
                or kind not in ("resume", "reconcile") or not isinstance(approved, dict)
                or ArtifactRef.model_validate(approved) != read_story(db, execution_id, artifact_id=row[1])[0]):
            raise ValueError("No exact approved Story for terminal outcome")
        db.execute("BEGIN IMMEDIATE")
        try:
            outcome = db.execute("SELECT outcome,source_id,subject_artifact_id FROM execution_outcomes "
                                 "WHERE execution_id=?", (execution_id,)).fetchone()
            if outcome is None:
                # Older v6 approval may already have reached END without a terminal receipt.
                db.execute("INSERT INTO execution_outcomes VALUES (?,?,?,?)",
                           (execution_id, "completed", row[0], row[1]))
            elif outcome != ("completed", row[0], row[1]):
                raise ValueError("Terminal Story outcome conflicts with approval")
            db.execute("UPDATE execution_work SET status='completed',settled_checkpoint_id=?,"
                       "work_version=work_version+1 WHERE work_id=?",
                       (checkpoint_id, work_id))
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise
        return
    db.execute("UPDATE execution_work SET status='completed',settled_checkpoint_id=?,"
               "work_version=work_version+1 WHERE work_id=?",
               (checkpoint_id, work_id))


async def run_story_work(db: sqlite3.Connection, saver: AsyncSqliteSaver,
                         produce_story: Callable[[str, list[str], StoryV1 | None, str | None], StoryV1 | Awaitable[StoryV1]],
                         *, stop: asyncio.Event | None = None) -> int:
    """Drain pending and abandoned claims under one caller-owned root lock/saver lifetime."""
    await validate_story_storage(db, saver)
    graph = build_story_graph(db, saver, produce_story)
    # Recover runnable checkpoints whose segment was incorrectly settled before a stable wait.
    for execution_id, digest in db.execute(
        "SELECT e.execution_id,e.start_digest FROM executions e WHERE e.graph_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM execution_outcomes o WHERE o.execution_id=e.execution_id) "
        "AND NOT EXISTS (SELECT 1 FROM execution_controls c WHERE c.execution_id=e.execution_id AND c.kind='cancel') "
        "AND NOT EXISTS (SELECT 1 FROM execution_work w WHERE w.execution_id=e.execution_id "
        "AND w.status IN ('pending','claimed','blocked'))"
    ).fetchall():
        config = {"configurable": {"thread_id": execution_id}}
        saved = await saver.aget_tuple(config)
        if saved is None:
            raise ValueError("Started Story has no checkpoint or live work")
        snapshot = await graph.aget_state(config)
        if snapshot.interrupts:
            request = db.execute("SELECT checkpoint_id,decision_id FROM review_requests WHERE execution_id=? "
                                 "AND request_id=?", (execution_id, snapshot.interrupts[0].value["request_id"])).fetchone()
            if request is not None and request == (saved.config["configurable"]["checkpoint_id"], None):
                continue  # Already actionable; never re-invoke an unanswered wait.
        elif not snapshot.next and not snapshot.values.get("approved_story"):
            raise ValueError("Empty checkpoint without terminal Story receipt")
        checkpoint_id = saved.config["configurable"]["checkpoint_id"]
        work_id = sha256_digest(f"kinodel.reconcile.v1:{execution_id}:{checkpoint_id}".encode())
        # A decision may arrive while saver.aget_tuple/graph.aget_state yielded to the API.
        if db.execute("SELECT 1 FROM execution_work WHERE execution_id=? "
                      "AND status IN ('pending','claimed','blocked')", (execution_id,)).fetchone():
            continue
        inserted = db.execute("INSERT OR IGNORE INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,status) "
                   "VALUES (?,?, 'reconcile', ?, ?, 'pending')",
                   (work_id, execution_id, checkpoint_id, digest))
        if inserted.rowcount != 1:
            raise ValueError("Unfinished checkpoint has already been reconciled")
    rows = db.execute(
        "SELECT work_id,execution_id,kind,source_id,payload_digest,resume_ref FROM execution_work "
        "WHERE status IN ('pending','claimed') ORDER BY rowid"
    ).fetchall()
    processed = 0
    for work in rows:
        if stop is not None and stop.is_set():
            break
        processed += 1
        if cancel_requested(db, work[1]):
            _finish_cancel(db, work[1])
            continue
        db.execute("UPDATE execution_work SET status='claimed',work_version=work_version+1 "
                   "WHERE work_id=? AND status='pending'", (work[0],))
        try:
            await _run_one(db, saver, graph, work, stop)
            if cancel_requested(db, work[1]):
                _finish_cancel(db, work[1])
        except _WorkerStopped:
            break
        except StoryOwnerUnavailable:
            if cancel_requested(db, work[1]):
                _finish_cancel(db, work[1])
            else:
                db.execute("UPDATE execution_work SET status='blocked',blocked_reason='owner_unavailable',"
                           "work_version=work_version+1 WHERE work_id=?", (work[0],))
        except ValueError as error:
            if cancel_requested(db, work[1]):
                _finish_cancel(db, work[1])
                continue
            db.execute("UPDATE execution_work SET status='blocked',blocked_reason=?,"
                       "work_version=work_version+1 WHERE work_id=?",
                        (str(error), work[0]))
            raise
    return processed
