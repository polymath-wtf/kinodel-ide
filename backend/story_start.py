"""Durable start for the internal Story fixture; no public cinematic Brief."""

import json
from pathlib import Path
import sqlite3
from typing import NamedTuple
from uuid import uuid4

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.database import APPLICATION_ID, DATABASE_NAME, SCHEMA_VERSION
from backend.domain import sha256_digest
from backend.saver import SAVER_ID, SAVER_NAME, SAVER_VERSION
from backend.story_graph import StoryState, initial_story_state
from backend.story_store import _uuid, _validated_test_inputs


GRAPH_ID = "kinodel.internal-story"
GRAPH_VERSION = "1"
# Frozen authored route identifier: change the version and digest when its execution contract changes.
GRAPH_DIGEST = sha256_digest(b"kinodel.internal-story.v1:START>storytell>story_prepare_review>story_wait>story_apply>END|revise>storytell")


class StartReceipt(NamedTuple):
    execution_id: str  # Also the LangGraph thread_id.
    work_id: str


def load_test_story_start(db: sqlite3.Connection, execution_id: str) -> tuple[StartReceipt, StoryState]:
    """Rebuild the graph input only from committed start records; fail closed on mismatches."""
    _uuid(execution_id)
    row = db.execute(
        "SELECT project_id,input_message,shot_ids,client_key,start_digest,graph_id,graph_version,graph_digest "
        "FROM executions WHERE execution_id=?", (execution_id,),
    ).fetchone()
    work = db.execute(
        "SELECT work_id,source_id,payload_digest FROM execution_work WHERE execution_id=? AND kind='start'",
        (execution_id,),
    ).fetchone()
    if row is None or work is None or row[3] is None or row[5:] != (GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST):
        raise ValueError("Unknown or unsupported internal Story start")
    project, message, shots_json, key, digest, *_ = row
    if type(key) is not str or not 0 < len(key) <= 256:
        raise ValueError("Internal Story start client key mismatch")
    shots = json.loads(shots_json)
    _validated_test_inputs(project, message, shots)
    if work[1:] != (execution_id, digest) or digest != _payload_digest(message, shots):
        raise ValueError("Internal Story start integrity mismatch")
    return StartReceipt(execution_id, work[0]), initial_story_state(project, execution_id)


def _payload_digest(message: str, shots: list[str]) -> str:
    return sha256_digest(json.dumps([message, shots], ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8"))


async def start_test_story(db: sqlite3.Connection, saver: AsyncSqliteSaver, project_id: str,
                           client_key: str, input_message: str, shot_ids: list[str]) -> StartReceipt:
    """Caller owns open_database(root) and open_saver(root, db) for this whole call."""
    _validated_test_inputs(project_id, input_message, shot_ids)
    if type(client_key) is not str or not 0 < len(client_key) <= 256:
        raise ValueError("Invalid start client key")
    client_key.encode("utf-8")
    await validate_story_storage(db, saver)
    digest = _payload_digest(input_message, shot_ids)
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute("SELECT execution_id,start_digest FROM executions WHERE project_id=? AND client_key=?",
                         (project_id, client_key)).fetchone()
        if row:
            if row[1] != digest:
                raise ValueError("Start client key conflicts with another payload")
            receipt, _ = load_test_story_start(db, row[0])
        else:
            execution_id, work_id = str(uuid4()), str(uuid4())
            db.execute(
                "INSERT INTO executions (execution_id,project_id,input_message,shot_ids,client_key,start_digest,"
                "graph_id,graph_version,graph_digest) VALUES (?,?,?,?,?,?,?,?,?)",
                (execution_id, project_id, input_message,
                 json.dumps(shot_ids, ensure_ascii=False, separators=(",", ":")), client_key,
                 digest, GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST),
            )
            db.execute("INSERT INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,resume_ref,status) "
                       "VALUES (?,?,?,?,?,NULL,'pending')", (work_id, execution_id, "start", execution_id, digest))
            receipt = StartReceipt(execution_id, work_id)
        db.execute("COMMIT")
        return receipt
    except BaseException:
        db.execute("ROLLBACK")
        raise


async def validate_story_storage(db: sqlite3.Connection, saver: AsyncSqliteSaver) -> None:
    """Check both open, versioned stores belong to the same caller-owned root."""
    if not isinstance(saver, AsyncSqliteSaver) or db.in_transaction:
        raise ValueError("An open preflighted saver and idle application DB are required")
    root = Path(db.execute("PRAGMA database_list").fetchone()[2]).resolve().parent
    if (Path(db.execute("PRAGMA database_list").fetchone()[2]).name != DATABASE_NAME
            or db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
            or db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION
            or db.execute("PRAGMA foreign_keys").fetchone()[0] != 1):
        raise ValueError("Unexpected application database")
    async with saver.conn.execute("PRAGMA database_list") as cursor:
        saver_path = (await cursor.fetchone())[2]
    async with saver.conn.execute("PRAGMA application_id") as cursor:
        identity = (await cursor.fetchone())[0]
    async with saver.conn.execute("PRAGMA user_version") as cursor:
        version = (await cursor.fetchone())[0]
    if Path(saver_path).resolve() != root / SAVER_NAME or (identity, version) != (SAVER_ID, SAVER_VERSION):
        raise ValueError("Saver must be open and preflighted under this data root")
