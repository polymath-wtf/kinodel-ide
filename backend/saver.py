"""Separate LangGraph SQLite checkpoint storage under caller-owned open_database(root).

The caller keeps the application connection/root lock alive until this async context
and all graph tasks using the saver have finished. This is not a crash-recovery protocol.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, closing
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.database import APPLICATION_ID, BUSY_TIMEOUT_MS, DATABASE_NAME, SCHEMA_VERSION, _check_file, _check_journal, _schema, _sync_directory


SAVER_NAME = "checkpoints.sqlite3"
SAVER_ID = 0x4B534156  # KSAV; only this storage owns this identity.
SAVER_VERSION = 1
# Pinned to langgraph-checkpoint-sqlite 3.1.1; any upstream schema change must
# be reviewed before accepting an existing file (setup() silently adds tables).
SAVER_SCHEMA = """
CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint BLOB,
    metadata BLOB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
CREATE TABLE writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    value BLOB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
"""


def _validate(db: sqlite3.Connection) -> None:
    if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise ValueError("Saver integrity check failed")
    if db.execute("PRAGMA application_id").fetchone()[0] != SAVER_ID or db.execute("PRAGMA user_version").fetchone()[0] != SAVER_VERSION:
        raise ValueError("Unknown or unsupported saver identity/version")
    with closing(sqlite3.connect(":memory:")) as expected:
        expected.executescript(SAVER_SCHEMA)
        if _schema(db) != _schema(expected):
            raise ValueError("Unexpected saver schema")
    if db.execute("PRAGMA foreign_key_check").fetchone():
        raise ValueError("Saver foreign key check failed")


def _preflight(path: Path, sidecars: list[Path]) -> None:
    # Never let SQLite recover an untrusted file in its original location.
    journal = Path(str(path) + "-journal")
    if journal in sidecars:
        _check_journal(journal)
    with tempfile.TemporaryDirectory(prefix="kinodel-saver-preflight-") as directory:
        candidate = Path(directory) / path.name
        shutil.copyfile(path, candidate)
        for sidecar in sidecars:
            if not sidecar.name.endswith("-shm"):
                shutil.copyfile(sidecar, Path(directory) / sidecar.name)
        with closing(sqlite3.connect(candidate.as_uri() + "?mode=rw", uri=True, timeout=BUSY_TIMEOUT_MS / 1000)) as db:
            _validate(db)


@asynccontextmanager
async def open_saver(root: Path, application_db: sqlite3.Connection) -> AsyncIterator[AsyncSqliteSaver]:
    """Open while caller holds open_database(root); never own or release its lock."""
    root = root.resolve()
    app_file = application_db.execute("PRAGMA database_list").fetchone()[2]
    if Path(app_file).resolve() != root / DATABASE_NAME or application_db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID:
        raise ValueError("Expected the caller-owned application database for this root")
    path = root / SAVER_NAME
    sidecars = []
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(str(path) + suffix)
        try:
            _check_file(sidecar)
        except FileNotFoundError:
            continue
        sidecars.append(sidecar)
    try:
        _check_file(path)
    except FileNotFoundError:
        if (sidecars or application_db.in_transaction
                 or application_db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION
                 or application_db.execute("SELECT 1 FROM story_operations LIMIT 1").fetchone() is not None
                 or application_db.execute("SELECT 1 FROM review_requests LIMIT 1").fetchone() is not None
                 or application_db.execute("SELECT 1 FROM execution_work LIMIT 1").fetchone() is not None):
            raise ValueError("Missing saver with runtime records, sidecars or active transaction")
        # Only a legacy test root with no graph-owned operation or review may
        # acquire a new saver; never replace one that might contain checkpoints.
        descriptor, name = tempfile.mkstemp(prefix=".saver-", dir=root)
        os.close(descriptor)
        temporary = Path(name)
        try:
            with closing(sqlite3.connect(temporary.as_uri() + "?mode=rw", uri=True, timeout=BUSY_TIMEOUT_MS / 1000, isolation_level=None)) as db:
                db.execute("PRAGMA synchronous=FULL")
                db.executescript(f"BEGIN IMMEDIATE; {SAVER_SCHEMA} PRAGMA application_id={SAVER_ID}; PRAGMA user_version={SAVER_VERSION}; COMMIT;")
            _preflight(temporary, [])
            with temporary.open("rb+") as ready:
                os.fsync(ready.fileno())
            try:
                os.link(temporary, path)  # Exclusive publication; never replace an existing saver.
            except FileExistsError as error:
                raise ValueError("Saver appeared during initialization") from error
            _sync_directory(root)
        finally:
            temporary.unlink()
            _sync_directory(root)
    else:
        _preflight(path, sidecars)

    # mode=rw avoids silent re-creation if the file disappears after preflight.
    async with aiosqlite.connect(path.as_uri() + "?mode=rw", uri=True, timeout=BUSY_TIMEOUT_MS / 1000) as conn:
        for name, value, expected in (("busy_timeout", BUSY_TIMEOUT_MS, BUSY_TIMEOUT_MS),
                                      ("foreign_keys", "ON", 1), ("journal_mode", "WAL", "wal"),
                                      ("synchronous", "FULL", 2)):
            await conn.execute(f"PRAGMA {name}={value}")
            row = await (await conn.execute(f"PRAGMA {name}")).fetchone()
            if row[0] != expected:
                raise ValueError(f"Saver SQLite setting not applied: {name}")
        saver = AsyncSqliteSaver(conn)
        await saver.setup()
        yield saver
