"""Short durable Story control transactions and the local lock-owning lifetime."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3
from uuid import uuid4

from backend.database import open_database
from backend.review_store import accept_story_decision
from backend.saver import open_saver
from backend.story_start import start_test_story
from backend.story_store import _uuid


def _key(value: str) -> str:
    if type(value) is not str or not 0 < len(value) <= 128:
        raise ValueError("Invalid control command key")
    value.encode("utf-8")
    return value


def cancel_requested(db: sqlite3.Connection, execution_id: str) -> bool:
    return db.execute("SELECT 1 FROM execution_controls WHERE execution_id=? AND kind='cancel'",
                      (execution_id,)).fetchone() is not None


def cancel_story(db: sqlite3.Connection, execution_id: str, command_key: str) -> str:
    """Accept exactly one cancellation, without waiting for an active invocation."""
    _uuid(execution_id)
    _key(command_key)
    db.execute("BEGIN IMMEDIATE")
    try:
        old = db.execute("SELECT kind,work_id FROM execution_controls WHERE execution_id=? AND command_key=?",
                         (execution_id, command_key)).fetchone()
        if old:
            if old[0] != "cancel":
                raise ValueError("Control command conflict")
            result = old[1]
        else:
            if db.execute("SELECT 1 FROM execution_controls WHERE execution_id=? AND kind='cancel'",
                          (execution_id,)).fetchone():
                raise ValueError("Execution already cancelling")
            if db.execute("SELECT 1 FROM execution_outcomes WHERE execution_id=?", (execution_id,)).fetchone():
                raise ValueError("Execution is terminal")
            start = db.execute("SELECT start_digest FROM executions WHERE execution_id=? AND graph_id IS NOT NULL",
                               (execution_id,)).fetchone()
            if start is None:
                raise ValueError("Unknown internal Story execution")
            result = str(uuid4())
            db.execute("INSERT INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,status) "
                       "VALUES (?,?, 'cancel', ?, ?, 'pending')", (result, execution_id, command_key, start[0]))
            db.execute("INSERT INTO execution_controls VALUES (?,?, 'cancel', ?, NULL)",
                       (execution_id, command_key, result))
        db.execute("COMMIT")
        return result
    except BaseException:
        db.execute("ROLLBACK")
        raise


def retry_story_work(db: sqlite3.Connection, execution_id: str, work_id: str,
                     command_key: str, expected_version: int) -> str:
    """Requeue only an explicitly retryable blocked segment, never replace its source."""
    _uuid(execution_id)
    _key(command_key)
    if type(expected_version) is not int or expected_version < 0:
        raise ValueError("Invalid expected work version")
    db.execute("BEGIN IMMEDIATE")
    try:
        old = db.execute("SELECT kind,work_id,expected_version FROM execution_controls "
                         "WHERE execution_id=? AND command_key=?", (execution_id, command_key)).fetchone()
        if old:
            if old != ("retry", work_id, expected_version):
                raise ValueError("Control command conflict")
        else:
            if cancel_requested(db, execution_id) or db.execute(
                "SELECT 1 FROM execution_outcomes WHERE execution_id=?", (execution_id,)
            ).fetchone():
                raise ValueError("Execution is cancelling or terminal")
            row = db.execute("SELECT status,blocked_reason,work_version,kind FROM execution_work "
                             "WHERE execution_id=? AND work_id=?", (execution_id, work_id)).fetchone()
            if row is None or row[0] != "blocked" or row[1] != "owner_unavailable" or row[3] not in (
                "start", "resume", "reconcile"
            ):
                raise ValueError("Work is not explicitly retryable")
            if row[2] != expected_version:
                raise ValueError("Stale work version")
            db.execute("UPDATE execution_work SET status='pending',blocked_reason=NULL,"
                       "work_version=work_version+1 WHERE work_id=? AND work_version=? AND status='blocked'",
                       (work_id, expected_version))
            db.execute("INSERT INTO execution_controls VALUES (?,?, 'retry', ?, ?)",
                       (execution_id, command_key, work_id, expected_version))
        db.execute("COMMIT")
        return work_id
    except BaseException:
        db.execute("ROLLBACK")
        raise


class StoryRuntime:
    def __init__(self, db, saver, produce_story):
        self.db, self.saver, self.produce_story = db, saver, produce_story
        self._stopping = asyncio.Event()
        self._running = None
        self._commands = set()

    def _open(self):
        if self._stopping.is_set():
            raise ValueError("Story runtime closed")

    async def start(self, *args):
        self._open()
        task = asyncio.current_task()
        self._commands.add(task)
        try:
            return await start_test_story(self.db, self.saver, *args)
        finally:
            self._commands.remove(task)

    def cancel(self, *args):
        self._open()
        return cancel_story(self.db, *args)

    def respond(self, *args):
        self._open()
        return accept_story_decision(self.db, *args)

    def retry(self, *args):
        self._open()
        return retry_story_work(self.db, *args)

    async def run(self):
        from backend.story_runner import run_story_work

        self._open()
        if self._running is not None:
            raise ValueError("Story runner already active")
        self._running = asyncio.current_task()
        try:
            return await run_story_work(self.db, self.saver, self.produce_story, stop=self._stopping)
        finally:
            self._running = None

    async def close(self):
        self._stopping.set()

        async def drain():
            if self._commands:
                await asyncio.gather(*self._commands, return_exceptions=True)
            if self._running is not None and self._running != asyncio.current_task():
                await asyncio.gather(self._running, return_exceptions=True)

        draining = asyncio.create_task(drain())
        try:
            await asyncio.shield(draining)
        except asyncio.CancelledError:
            await draining  # Never release ownership while saver or graph tasks still write.
            raise


@asynccontextmanager
async def open_story_runtime(root: Path, produce_story):
    """Stop active graph/saver writers before closing stores and releasing the root lock."""
    with open_database(root) as db:
        async with open_saver(root, db) as saver:
            runtime = StoryRuntime(db, saver, produce_story)
            try:
                yield runtime
            finally:
                await runtime.close()
