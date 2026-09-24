"""Application SQLite foundation, separate from checkpointer storage."""

from collections.abc import Iterator
from contextlib import closing, contextmanager
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import struct
import tempfile

from backend.ownership import own_data_root


DATABASE_NAME = "application.sqlite3"
APPLICATION_ID = 0x4B494E4F  # KINO; SQLite header identity, not a business record.
SCHEMA_VERSION = 8
BUSY_TIMEOUT_MS = 1000
INITIALIZING = ".kinodel-initializing-v1"
READY = ".kinodel-ready-v1"
JOURNAL_MAGIC = bytes.fromhex("d9d505f920a163d7")

BASE_SCHEMA = """
CREATE TABLE executions (
    execution_id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
    input_message TEXT NOT NULL CHECK(length(input_message)>0),
    shot_ids TEXT NOT NULL
);
CREATE TABLE artifacts (
    artifact_id TEXT PRIMARY KEY, execution_id TEXT NOT NULL REFERENCES executions(execution_id),
    operation_id TEXT NOT NULL UNIQUE, digest TEXT NOT NULL,
    uri TEXT NOT NULL UNIQUE, schema_id TEXT NOT NULL CHECK(schema_id='story'),
    schema_version TEXT NOT NULL CHECK(schema_version='1'),
    produced_by_stage TEXT NOT NULL CHECK(produced_by_stage='storytell')
);
"""
BINDING_SCHEMA = """
CREATE TABLE execution_bindings (
    execution_id TEXT NOT NULL REFERENCES executions(execution_id),
    slot TEXT NOT NULL CHECK(slot='story'),
    artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
    binding_revision INTEGER NOT NULL CHECK(binding_revision>=1),
    PRIMARY KEY(execution_id, slot)
);
"""
STORY_SCHEMA = BASE_SCHEMA + BINDING_SCHEMA
V2_SCHEMA = BASE_SCHEMA + BINDING_SCHEMA.replace("CHECK(binding_revision>=1)", "CHECK(binding_revision=1)")
OPERATION_SCHEMA = """
CREATE TABLE story_operations (
    operation_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL REFERENCES executions(execution_id),
    activation_id TEXT NOT NULL,
    input_digest TEXT NOT NULL,
    prepared_inputs TEXT NOT NULL,
    expected_revision INTEGER CHECK(expected_revision>=1),
    artifact_id TEXT REFERENCES artifacts(artifact_id),
    next_activation TEXT,
    UNIQUE(execution_id, activation_id),
    CHECK((artifact_id IS NULL) = (next_activation IS NULL))
);
"""
REVIEW_SCHEMA = """
CREATE TABLE review_requests (
    request_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL REFERENCES executions(execution_id),
    trigger_activation TEXT NOT NULL,
    subject_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
    subject_digest TEXT NOT NULL,
    binding_revision INTEGER NOT NULL CHECK(binding_revision>=1),
    request_revision INTEGER NOT NULL CHECK(request_revision>=1),
    previous_request_id TEXT REFERENCES review_requests(request_id),
    request_digest TEXT NOT NULL,
    checkpoint_id TEXT, task_id TEXT, interrupt_id TEXT,
    decision_key TEXT, decision_digest TEXT, decision_id TEXT,
    action TEXT CHECK(action IN ('approve','revise','clarify')),
    message TEXT, applied_activation TEXT,
    UNIQUE(execution_id, trigger_activation),
    UNIQUE(execution_id, request_revision),
    UNIQUE(execution_id, decision_key),
    CHECK((checkpoint_id IS NULL) = (task_id IS NULL)),
    CHECK((checkpoint_id IS NULL) = (interrupt_id IS NULL)),
    CHECK((decision_id IS NULL) = (decision_key IS NULL)),
    CHECK((decision_id IS NULL) = (decision_digest IS NULL)),
    CHECK((decision_id IS NULL) = (action IS NULL)),
    CHECK(applied_activation IS NULL OR decision_id IS NOT NULL)
);
CREATE UNIQUE INDEX one_open_story_review ON review_requests(execution_id)
    WHERE applied_activation IS NULL;
CREATE TABLE execution_work (
    work_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL REFERENCES executions(execution_id),
    kind TEXT NOT NULL CHECK(kind IN ('start','resume','reconcile','cancel')),
    source_id TEXT NOT NULL, payload_digest TEXT NOT NULL,
    resume_ref TEXT, status TEXT NOT NULL CHECK(status IN ('pending','claimed','completed','blocked','failed','obsolete')),
    UNIQUE(execution_id, kind, source_id)
);
"""
START_SCHEMA = """
ALTER TABLE executions ADD COLUMN client_key TEXT;
ALTER TABLE executions ADD COLUMN start_digest TEXT;
ALTER TABLE executions ADD COLUMN graph_id TEXT;
ALTER TABLE executions ADD COLUMN graph_version TEXT;
ALTER TABLE executions ADD COLUMN graph_digest TEXT;
CREATE UNIQUE INDEX one_start_per_project_key ON executions(project_id, client_key);
"""
RUNNER_SCHEMA = """
ALTER TABLE execution_work ADD COLUMN settled_checkpoint_id TEXT;
ALTER TABLE execution_work ADD COLUMN blocked_reason TEXT;
CREATE TABLE execution_outcomes (
    execution_id TEXT PRIMARY KEY REFERENCES executions(execution_id),
    outcome TEXT NOT NULL CHECK(outcome IN ('completed','cancelled','failed')),
    source_id TEXT NOT NULL,
    subject_artifact_id TEXT REFERENCES artifacts(artifact_id)
);
"""
CONTROL_SCHEMA = """
ALTER TABLE execution_work ADD COLUMN work_version INTEGER NOT NULL DEFAULT 0;
CREATE TABLE execution_controls (
    execution_id TEXT NOT NULL REFERENCES executions(execution_id),
    command_key TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('cancel','retry')),
    work_id TEXT NOT NULL REFERENCES execution_work(work_id),
    expected_version INTEGER,
    PRIMARY KEY(execution_id, command_key)
);
CREATE UNIQUE INDEX one_cancel_per_execution ON execution_controls(execution_id) WHERE kind='cancel';
"""


def _schema(db: sqlite3.Connection) -> list[tuple[str, str, str]]:
    return db.execute(
        "SELECT type, name, sql FROM sqlite_schema WHERE name NOT LIKE 'sqlite_autoindex_%' ORDER BY type, name"
    ).fetchall()


def _expected_schema(version: int) -> list[tuple[str, str, str]]:
    with closing(sqlite3.connect(":memory:")) as candidate:
        candidate.executescript(V2_SCHEMA if version == 2 else STORY_SCHEMA +
                                 (OPERATION_SCHEMA if version >= 4 else "") +
                                 (REVIEW_SCHEMA if version >= 5 else ""))
        if version >= 6:
            candidate.executescript(START_SCHEMA)
        if version >= 7:
            candidate.executescript(RUNNER_SCHEMA)
        if version >= 8:
            candidate.executescript(CONTROL_SCHEMA)
        return _schema(candidate)


def _check_file(path: Path) -> None:
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
        or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    ):
        raise ValueError(f"Database file must be regular, unredirected and single-link: {path.name}")


def _validate(db: sqlite3.Connection) -> None:
    if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise ValueError("Application database integrity check failed")
    if db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID:
        raise ValueError("Unknown application database identity")
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version not in (1, 2, 3, 4, 5, 6, 7, SCHEMA_VERSION):
        raise ValueError("Unsupported application database version; maintenance required")
    if _schema(db) != ([] if version == 1 else _expected_schema(version)):
        raise ValueError("Unexpected application database schema")
    if version != 1 and db.execute("PRAGMA foreign_key_check").fetchone():
        raise ValueError("Application database foreign key check failed")


def _sync_directory(root: Path) -> None:
    # Windows stdlib cannot fsync directory entries. File fsync + SQLite FULL
    # support process-death recovery, not a Windows power-loss guarantee.
    if os.name != "nt":
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _marker(path: Path, *, create: bool = False) -> bool:
    # Empty content is the entire v1 record. O_EXCL publishes it in one step;
    # there is no partially written record or creator-specific ownership.
    if create:
        try:
            with path.open("xb") as marker:
                os.fsync(marker.fileno())
        except FileExistsError:
            pass
    try:
        _check_file(path)
    except FileNotFoundError:
        return False
    if path.stat().st_size != 0:
        raise ValueError(f"Malformed bootstrap marker: {path.name}")
    with path.open("rb+") as marker:
        os.fsync(marker.fileno())
    _sync_directory(path.parent)
    return True


def _check_journal(path: Path) -> None:
    """Reject damaged synced records that SQLite playback can silently skip.

    Single-database FULL journals only; SQLite still performs actual recovery.
    Format: https://www.sqlite.org/fileformat2.html#the_rollback_journal
    """
    size = path.stat().st_size
    if not size:
        return
    with path.open("rb") as source:
        if size >= 16:
            source.seek(-8, os.SEEK_END)
            if source.read(8) == JOURNAL_MAGIC:
                raise ValueError("Super-journal recovery requires maintenance")
        offset = 0
        dimensions = None
        while offset < size:
            source.seek(offset)
            header = source.read(28)
            if header[:8] == b"\0" * 8:
                return  # Cold/PERSIST journal or unsynced tail; SQLite ignores it.
            if len(header) != 28 or header[:8] != JOURNAL_MAGIC:
                raise ValueError("Malformed rollback journal header")
            count, nonce, pages, sector, page_size = struct.unpack(">5I", header[8:])
            if any(n < 512 or n > 65536 or n & (n - 1) for n in (sector, page_size)):
                raise ValueError("Invalid rollback journal dimensions")
            current = (pages, sector, page_size)
            if dimensions is not None and dimensions != current:
                raise ValueError("Inconsistent rollback journal headers")
            dimensions = current
            offset += sector
            if count == 0xFFFFFFFF or count > (size - offset) // (page_size + 8):
                raise ValueError("Truncated or unsupported rollback journal")
            source.seek(offset)
            for _ in range(count):
                number = int.from_bytes(source.read(4), "big")
                page = source.read(page_size)
                checksum = int.from_bytes(source.read(4), "big")
                if not 1 <= number <= pages or checksum != (
                    nonce + sum(page[page_size - 200::-200])
                ) & 0xFFFFFFFF:
                    raise ValueError("Invalid rollback journal page/checksum")
            offset += count * (page_size + 8)
            offset = ((offset + sector - 1) // sector) * sector


def _preflight(path: Path, sidecars: list[Path], pending: bool) -> bool:
    """Validate a private recovery first; never recover unknown original bytes.

    The root lock excludes application writers throughout copying and recovery.
    SQLite, rather than our own journal parser, interprets the committed header.
    A dirty main-file header is not evidence of ownership or compatibility.
    """
    journal = Path(str(path) + "-journal")
    if journal in sidecars:
        _check_journal(journal)

    def inspect(candidate: Path) -> bool:
        with closing(sqlite3.connect(
            candidate.as_uri() + "?mode=rw", uri=True,
            timeout=BUSY_TIMEOUT_MS / 1000, isolation_level=None,
        )) as db:
            if (pending and db.execute("PRAGMA page_count").fetchone() == (0,)
                    and candidate.stat().st_size == 0):
                return True  # Only the recorded, never-ready reservation may be blank.
            _validate(db)
            return False

    # Even mode=ro can create WAL/SHM sidecars for a clean WAL-mode database.
    # ponytail: private recovery needs DB-sized temporary space; revisit
    # copy preflight if actual project sizes make that impractical.
    with tempfile.TemporaryDirectory(prefix="kinodel-preflight-") as temporary:
        candidate = Path(temporary) / path.name
        shutil.copyfile(path, candidate)
        for sidecar in sidecars:
            if not sidecar.name.endswith("-shm"):  # Derived WAL index.
                shutil.copyfile(sidecar, Path(temporary) / sidecar.name)
        return inspect(candidate)


@contextmanager
def open_database(root: Path) -> Iterator[sqlite3.Connection]:
    """Own the root until the connection closes (uncommitted work rolls back).

    Empty versioned markers permanently record reservation and completion.
    Publish reservation before creating the lock: any lock winner can continue.
    A lock alone proves nothing; a ready root with a missing DB never initializes.
    Trusted local filesystem and no forked/background connection users required.
    """
    if not root.is_absolute():
        raise ValueError("Data root must be absolute")
    root = root.resolve()
    fresh = not root.exists() or (root.is_dir() and not any(root.iterdir()))
    if fresh:
        root.mkdir(parents=True, exist_ok=True)
        _sync_directory(root.parent)
        _marker(root / INITIALIZING, create=True)
    with own_data_root(root):
        path = root / DATABASE_NAME
        reserved = _marker(root / INITIALIZING)
        ready = _marker(root / READY)
        pending = reserved and not ready
        if pending:
            allowed = {INITIALIZING, ".kinodel.lock", DATABASE_NAME, DATABASE_NAME + "-journal"}
            if any(entry.name not in allowed for entry in root.iterdir()):
                raise ValueError("Unexpected files in incomplete bootstrap root")
        try:
            path.lstat()
        except FileNotFoundError:
            if not pending or {entry.name for entry in root.iterdir()} != {
                INITIALIZING, ".kinodel.lock",
            }:
                raise ValueError("Application database missing from existing root; refusing initialization")
            with path.open("xb"):
                pass
        _check_file(path)
        # SQLite sidecars must not redirect writes either.
        sidecars = []
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(path) + suffix)
            try:
                _check_file(sidecar)
            except FileNotFoundError:
                continue
            sidecars.append(sidecar)
        initialize = _preflight(path, sidecars, pending)
        db = sqlite3.connect(
            path.as_uri() + "?mode=rw", uri=True,
            timeout=BUSY_TIMEOUT_MS / 1000, isolation_level=None,
        )
        try:
            if initialize:
                db.execute("PRAGMA synchronous=FULL")
                # First migration: atomically stamp identity/version, no speculative tables.
                db.executescript(
                    f"BEGIN IMMEDIATE; PRAGMA application_id={APPLICATION_ID};"
                    "PRAGMA user_version=1; COMMIT;"
                )
            _validate(db)
            if db.execute("PRAGMA user_version").fetchone()[0] == 1:
                # v1 has no business rows. DDL and version stamp commit together.
                db.execute("PRAGMA synchronous=FULL")
                db.executescript(
                    f"BEGIN IMMEDIATE; {STORY_SCHEMA} PRAGMA user_version=3; COMMIT;"
                )
                _validate(db)
            if db.execute("PRAGMA user_version").fetchone()[0] == 2:
                db.execute("PRAGMA synchronous=FULL")
                db.executescript(
                    "BEGIN IMMEDIATE; ALTER TABLE execution_bindings RENAME TO old_bindings;"
                    f"{BINDING_SCHEMA}"
                    "INSERT INTO execution_bindings SELECT * FROM old_bindings;"
                    "DROP TABLE old_bindings;"
                    "PRAGMA user_version=3; COMMIT;"
                )
                _validate(db)
            if db.execute("PRAGMA user_version").fetchone()[0] == 3:
                db.execute("PRAGMA synchronous=FULL")
                db.executescript(
                    f"BEGIN IMMEDIATE; {OPERATION_SCHEMA} PRAGMA user_version=4; COMMIT;"
                )
                _validate(db)
            if db.execute("PRAGMA user_version").fetchone()[0] == 4:
                db.execute("PRAGMA synchronous=FULL")
                db.executescript(
                    f"BEGIN IMMEDIATE; {REVIEW_SCHEMA} PRAGMA user_version=5; COMMIT;"
                )
                _validate(db)
            if db.execute("PRAGMA user_version").fetchone()[0] == 5:
                db.execute("PRAGMA synchronous=FULL")
                db.executescript(
                    f"BEGIN IMMEDIATE; {START_SCHEMA} PRAGMA user_version=6; COMMIT;"
                )
                _validate(db)
            if db.execute("PRAGMA user_version").fetchone()[0] == 6:
                db.execute("PRAGMA synchronous=FULL")
                db.executescript(
                    f"BEGIN IMMEDIATE; {RUNNER_SCHEMA} PRAGMA user_version=7; COMMIT;"
                )
                _validate(db)
            if db.execute("PRAGMA user_version").fetchone()[0] == 7:
                db.execute("PRAGMA synchronous=FULL")
                db.executescript(
                    f"BEGIN IMMEDIATE; {CONTROL_SCHEMA} PRAGMA user_version={SCHEMA_VERSION}; COMMIT;"
                )
                _validate(db)
            _marker(root / READY, create=True)
            settings = {
                "journal_mode": ("WAL", "wal"),
                "synchronous": ("FULL", 2),
                "foreign_keys": ("ON", 1),
                "busy_timeout": (str(BUSY_TIMEOUT_MS), BUSY_TIMEOUT_MS),
            }
            for name, (value, expected) in settings.items():
                db.execute(f"PRAGMA {name}={value}")
                if db.execute(f"PRAGMA {name}").fetchone()[0] != expected:
                    raise ValueError(f"SQLite setting not applied: {name}")
            yield db
        finally:
            db.close()
