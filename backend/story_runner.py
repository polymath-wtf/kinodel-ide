"""Single local runner for verified frozen Story routes and their durable work."""

import asyncio
import sqlite3
from pathlib import Path
from typing import Awaitable, Callable

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from backend.domain import ArtifactRef, StoryV1, sha256_digest
from backend.review_store import bind_story_wait
from backend.story_control import cancel_requested
from backend.story_graph import WardrobeBlocked, StoryOwnerUnavailable, build_story_graph, validate_wardrobe_success
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


class _InvocationSaver(BaseCheckpointSaver):
    """One local graph invocation's write barrier, not another storage implementation."""

    def __init__(self, saver: AsyncSqliteSaver):
        super().__init__(serde=saver.serde)
        self._saver = saver
        self.aget_tuple = saver.aget_tuple
        self.alist = saver.alist
        self.get_next_version = saver.get_next_version
        # Capture caller-injected public methods too; never patch the owned saver itself.
        self._put, self._put_writes = saver.aput, saver.aput_writes
        self._writes = []
        self._closed = False
        self._graph_task = None

    @property
    def config_specs(self):
        return self._saver.config_specs

    async def _write(self, call, *args, **kwargs):
        if self._closed or (self._graph_task is not None and self._graph_task.done()):
            raise RuntimeError("Story checkpoint invocation is closed")
        task = asyncio.create_task(call(*args, **kwargs))
        self._writes.append(task)
        # Cancelling graph/executor awaiters must not abort a started SQLite write.
        return await asyncio.shield(task)

    async def aput(self, config, checkpoint, metadata, new_versions):
        return await self._write(self._put, config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config, writes, task_id, task_path=""):
        return await self._write(self._put_writes, config, writes, task_id, task_path=task_path)

    async def settle(self, graph_task):
        await asyncio.gather(graph_task, return_exceptions=True)
        # Any late orphaned framework call retains this closed proxy, not a later invocation's saver.
        self._closed = True
        results = await asyncio.gather(*self._writes, return_exceptions=True)
        for result in results:
            if isinstance(result, BaseException):
                raise result


async def _invoke(db, graph, invocation, config, execution_id, stop):
    task = asyncio.create_task(graph.ainvoke(invocation, config, durability="sync"))
    graph.checkpointer._graph_task = task
    try:
        while not task.done():
            if cancel_requested(db, execution_id) or (stop is not None and stop.is_set()):
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
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
    finally:
        if not task.done():
            task.cancel()
        draining = asyncio.create_task(graph.checkpointer.settle(task))
        cancelled = False
        while not draining.done():
            try:
                await asyncio.shield(draining)
            except asyncio.CancelledError:
                cancelled = True  # Repeated caller cancellation cannot release storage ownership early.
        draining.result()
        if cancelled:
            raise asyncio.CancelledError()


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


async def _run_one(db, saver, graph, work, stop, *, wardrobe=False):
    work_id, execution_id, kind, source_id, payload_digest, resume_ref = work
    receipt, initial = load_test_story_start(db, execution_id)
    outcome = db.execute("SELECT outcome,source_id FROM execution_outcomes WHERE execution_id=?",
                         (execution_id,)).fetchone()
    if outcome:
        approved_request = None
        if wardrobe and outcome[0] == "completed":
            record = db.execute("SELECT approval_request_id FROM wardrobe_operations WHERE execution_id=? AND operation_id=?",
                                (execution_id, outcome[1])).fetchone()
            if record is None:
                raise ValueError("Wardrobe terminal outcome has no operation")
            try:
                ref = validate_wardrobe_success(db, execution_id, record[0])
            except (ValueError, OSError):
                raise WardrobeBlocked("wardrobe_invalid") from None
            if db.execute("SELECT subject_artifact_id FROM execution_outcomes WHERE execution_id=?",
                          (execution_id,)).fetchone() != (ref.artifact_id,):
                raise ValueError("Wardrobe terminal outcome subject mismatch")
            approved_request = record[0]
        db.execute("UPDATE execution_work SET status=?,work_version=work_version+1 WHERE work_id=?",
                   ("completed" if kind == "resume" and (outcome == ("completed", source_id) or source_id == approved_request)
                    else "obsolete", work_id))
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

    persisted_resume = False
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
                persisted_resume = True
            elif decision[5] is not None:
                raise ValueError("Applied decision has no persisted resume value")
            else:
                invocation = Command(resume={decision[4]: decision[0]})
        else:
            if decision[5] is None and snapshot.values.get("decision_id") != decision[0]:
                raise ValueError("Resume moved beyond its source without a matching decision")
            invocation = None

    # Pending task writes can empty snapshot.next before the resumed step is checkpointed.
    if (snapshot is None or invocation is not None or persisted_resume or (snapshot.next and
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
    elif wardrobe:
        request_id = snapshot.values.get("review_ref", {}).get("request_id")
        ref = validate_wardrobe_success(db, execution_id, request_id)
        record = db.execute("SELECT next_activation,activation_id FROM wardrobe_operations WHERE operation_id=?",
                            (ref.operation_id,)).fetchone()
        if (kind not in ("resume", "reconcile") or (kind == "resume" and source_id != request_id)
                or snapshot.values.get("wardrobe_plan") != ref.model_dump(mode="json")
                or snapshot.values.get("approved_story") != read_story(db, execution_id)[0].model_dump(mode="json")
                or (snapshot.values.get("wardrobe_transition"), snapshot.values.get("wardrobe_activation")) != record
                or db.execute("SELECT outcome,source_id,subject_artifact_id FROM execution_outcomes WHERE execution_id=?",
                              (execution_id,)).fetchone() != ("completed", ref.operation_id, ref.artifact_id)):
            raise ValueError("No exact Wardrobe terminal receipt/checkpoint")
        # No Story-only legacy completion fallback on this frozen route.
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
                         *, stop: asyncio.Event | None = None, character_root: Path | None = None) -> int:
    """Drain pending and abandoned claims under one caller-owned root lock/saver lifetime."""
    await validate_story_storage(db, saver)
    from backend import wardrobe_store, image_group_store
    from backend.image_graph import build_image_graph
    from backend.image_runner import inspect_image_checkpoint, run_image_work
    retired = (wardrobe_store.RETIRED_GRAPH_ID, wardrobe_store.RETIRED_GRAPH_VERSION, wardrobe_store.RETIRED_GRAPH_DIGEST)

    def is_image(execution_id):
        # Membership also identifies a corrupt image envelope: never fall back to Story.
        return db.execute("SELECT 1 FROM executions e WHERE e.execution_id=? AND (e.graph_id=? OR EXISTS "
                          "(SELECT 1 FROM image_groups g WHERE g.execution_id=e.execution_id))",
                          (execution_id, image_group_store.GRAPH_ID)).fetchone() is not None

    def select_graph(execution_id):
        if is_image(execution_id):
            group = image_group_store.read_image_group(db, execution_id)
            return build_image_graph(db, _InvocationSaver(saver), group), False
        load_test_story_start(db, execution_id)  # Verify the entire frozen identity before selecting topology.
        wardrobe = db.execute("SELECT graph_id FROM executions WHERE execution_id=?",
                              (execution_id,)).fetchone()[0] == wardrobe_store.GRAPH_ID
        # Never reopen a settled write proxy: old framework tasks must stay fenced out.
        graph = build_story_graph(db, _InvocationSaver(saver), produce_story, wardrobe=wardrobe, character_root=character_root)
        return graph, wardrobe
    # Recover runnable checkpoints whose segment was incorrectly settled before a stable wait.
    for execution_id, digest in db.execute(
        "SELECT e.execution_id,e.start_digest FROM executions e WHERE (e.graph_id IS NOT NULL "
        "OR EXISTS (SELECT 1 FROM image_groups g WHERE g.execution_id=e.execution_id)) "
        "AND (NOT (e.graph_id IS ? AND e.graph_version IS ? AND e.graph_digest IS ?) "
        "OR EXISTS (SELECT 1 FROM image_groups g WHERE g.execution_id=e.execution_id)) "
        "AND NOT EXISTS (SELECT 1 FROM execution_outcomes o WHERE o.execution_id=e.execution_id) "
        "AND NOT EXISTS (SELECT 1 FROM execution_controls c WHERE c.execution_id=e.execution_id AND c.kind='cancel') "
        "AND NOT EXISTS (SELECT 1 FROM execution_work w WHERE w.execution_id=e.execution_id "
        "AND w.status IN ('pending','claimed','blocked'))", retired
    ).fetchall():
        if stop is not None and stop.is_set():
            return 0
        if is_image(execution_id):
            # A settled unanswered wait is read-only. Invalid retained checkpoints need
            # a durable diagnostic even when no pending work survived the previous run.
            config = {"configurable": {"thread_id": execution_id}}
            saved = await saver.aget_tuple(config)
            if stop is not None and stop.is_set():
                return 0
            if cancel_requested(db, execution_id):
                _finish_cancel(db, execution_id)
                continue
            checkpoint_id = saved.config["configurable"]["checkpoint_id"] if saved else execution_id
            try:
                graph, _ = select_graph(execution_id)
                group = image_group_store.read_image_group(db, execution_id)
                _, binding = await inspect_image_checkpoint(saver, graph, group)
                # Commands may arrive during saver reads; control wins over sweep repair.
                if stop is not None and stop.is_set():
                    return 0
                if cancel_requested(db, execution_id):
                    _finish_cancel(db, execution_id)
                    continue
                if binding is not None and group.checkpoint_id is not None:
                    continue
                if saved is None:
                    raise ValueError("Started image execution has no checkpoint or live work")
            except (ValueError, OSError, LookupError) as error:
                if stop is not None and stop.is_set():
                    return 0
                if cancel_requested(db, execution_id):
                    _finish_cancel(db, execution_id)
                    continue
                work_id = sha256_digest(f"kinodel.reconcile.v1:{execution_id}:{checkpoint_id}".encode())
                db.execute("INSERT OR IGNORE INTO execution_work "
                           "(work_id,execution_id,kind,source_id,payload_digest,status,blocked_reason) "
                           "VALUES (?,?, 'reconcile', ?, ?, 'blocked', ?)",
                           (work_id, execution_id, checkpoint_id, digest, str(error)))
                db.execute("UPDATE execution_work SET status='blocked',blocked_reason=?,work_version=work_version+1 "
                           "WHERE work_id=?", (str(error), work_id))
                raise ValueError(str(error)) from error
            work_id = sha256_digest(f"kinodel.reconcile.v1:{execution_id}:{checkpoint_id}".encode())
            inserted = db.execute("INSERT OR IGNORE INTO execution_work "
                                  "(work_id,execution_id,kind,source_id,payload_digest,status) "
                                  "VALUES (?,?, 'reconcile', ?, ?, 'pending')",
                                  (work_id, execution_id, checkpoint_id, digest))
            if inserted.rowcount != 1:
                raise ValueError("Unfinished image checkpoint has already been reconciled")
            continue
        graph, wardrobe = select_graph(execution_id)
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
        elif not snapshot.next and not wardrobe and not snapshot.values.get("approved_story"):
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
        "SELECT w.work_id,w.execution_id,w.kind,w.source_id,w.payload_digest,w.resume_ref FROM execution_work w "
        "JOIN executions e ON e.execution_id=w.execution_id WHERE w.status IN ('pending','claimed') "
        "AND (NOT (e.graph_id IS ? AND e.graph_version IS ? AND e.graph_digest IS ?) "
        "OR EXISTS (SELECT 1 FROM image_groups g WHERE g.execution_id=e.execution_id)) ORDER BY w.rowid", retired
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
            graph, wardrobe = select_graph(work[1])
            if is_image(work[1]):
                await run_image_work(db, saver, graph, work, stop, _invoke)
            else:
                await _run_one(db, saver, graph, work, stop, wardrobe=wardrobe)
            if cancel_requested(db, work[1]):
                _finish_cancel(db, work[1])
        except _WorkerStopped:
            break
        except WardrobeBlocked as error:
            if cancel_requested(db, work[1]):
                _finish_cancel(db, work[1])
            else:
                db.execute("UPDATE execution_work SET status='blocked',blocked_reason=?,"
                           "work_version=work_version+1 WHERE work_id=?", (str(error), work[0]))
        except StoryOwnerUnavailable:
            if cancel_requested(db, work[1]):
                _finish_cancel(db, work[1])
            else:
                db.execute("UPDATE execution_work SET status='blocked',blocked_reason='owner_unavailable',"
                           "work_version=work_version+1 WHERE work_id=?", (work[0],))
        except (ValueError, OSError, LookupError) as error:
            if not isinstance(error, ValueError) and not is_image(work[1]):
                raise  # Preserve historical Story storage/error handling.
            if cancel_requested(db, work[1]):
                _finish_cancel(db, work[1])
                continue
            db.execute("UPDATE execution_work SET status='blocked',blocked_reason=?,"
                       "work_version=work_version+1 WHERE work_id=?",
                        (str(error), work[0]))
            raise
    return processed
