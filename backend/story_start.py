"""Durable frozen starts for fixture and live Story text; no public cinematic Brief."""

import asyncio
import json
from pathlib import Path
import sqlite3
from typing import NamedTuple
from uuid import uuid4

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.characters import CharacterRef, CharacterRepository
from backend.database import APPLICATION_ID, DATABASE_NAME, SCHEMA_VERSION
from backend.domain import StoryTextInputV1, sha256_digest
from backend.saver import SAVER_ID, SAVER_NAME, SAVER_VERSION
from backend.story_graph import StoryState, initial_story_state
from backend.story_store import _uuid, _validated_test_inputs


GRAPH_ID = "kinodel.internal-story"
GRAPH_VERSION = "1"
# Frozen authored route identifier: change the version and digest when its execution contract changes.
GRAPH_DIGEST = sha256_digest(b"kinodel.internal-story.v1:START>storytell>story_prepare_review>story_wait>story_apply>END|revise>storytell")
LIVE_GRAPH_ID = "kinodel.live-story"
LIVE_GRAPH_VERSION = "2"
LIVE_GRAPH_DIGEST = sha256_digest(b"kinodel.live-story.v2:OpenRouter+frozen-storytell-v2+text-input+generated-cast>storytell>story_prepare_review>story_wait>story_apply>END|clarify+revise>storytell")
LIVE_GRAPH_DIGESTS = {
    "1": sha256_digest(b"kinodel.live-story.v1:OpenRouter+frozen-storytell+text-input>storytell>story_prepare_review>story_wait>story_apply>END|clarify+revise>storytell"),
    "2": LIVE_GRAPH_DIGEST,
}
STORY_GRAPH_IDS = (GRAPH_ID, LIVE_GRAPH_ID)
DEFAULT_CHARACTER_ROOT = Path(__file__).resolve().parent.parent / "wiki" / "characters"


class InvalidCharacterSelection(ValueError):
    pass


class StartReceipt(NamedTuple):
    execution_id: str  # Also the LangGraph thread_id.
    work_id: str


def load_test_story_start(db: sqlite3.Connection, execution_id: str) -> tuple[StartReceipt, StoryState]:
    """Rebuild the graph input only from committed start records; fail closed on mismatches."""
    _uuid(execution_id)
    row = db.execute(
        "SELECT project_id,input_message,shot_ids,client_key,start_digest,graph_id,graph_version,graph_digest,owner_config "
        "FROM executions WHERE execution_id=?", (execution_id,),
    ).fetchone()
    work = db.execute(
        "SELECT work_id,source_id,payload_digest FROM execution_work WHERE execution_id=? AND kind='start'",
        (execution_id,),
    ).fetchone()
    if row is None or work is None or row[3] is None:
        raise ValueError("Unknown or unsupported internal Story start")
    live = row[5] == LIVE_GRAPH_ID and row[6] in LIVE_GRAPH_DIGESTS and row[7] == LIVE_GRAPH_DIGESTS[row[6]]
    if not live and (row[5:8] != (GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST) or row[8] is not None):
        raise ValueError("Unknown or unsupported internal Story start")
    if live:
        from backend.openrouter import read_owner_config
        config = read_owner_config(row[8])
        if config.adapter_version != row[6] or config.brief.user_vibe != row[1] or not 1 <= len(json.loads(row[2])) <= 8:
            raise ValueError("Frozen live Story input mismatch")
    project, message, shots_json, key, digest, *_ = row
    if type(key) is not str or not 0 < len(key) <= 256:
        raise ValueError("Internal Story start client key mismatch")
    shots = json.loads(shots_json)
    _validated_test_inputs(project, message, shots)
    if work[1:] != (execution_id, digest) or digest != _payload_digest(message, shots, row[8]):
        raise ValueError("Internal Story start integrity mismatch")
    return StartReceipt(execution_id, work[0]), initial_story_state(project, execution_id, live=live)


def _payload_digest(message: str, shots: list[str], owner_config: str | None = None) -> str:
    payload = [message, shots] if owner_config is None else ["live-story-start-v1", message, shots, owner_config]
    return sha256_digest(json.dumps(payload, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8"))


async def start_test_story(db: sqlite3.Connection, saver: AsyncSqliteSaver, project_id: str,
                           client_key: str, input_message: str, shot_ids: list[str]) -> StartReceipt:
    return await _start_story(db, saver, project_id, client_key, input_message, shot_ids, None)


async def start_live_story(db: sqlite3.Connection, saver: AsyncSqliteSaver, project_id: str,
                           client_key: str, shot_ids: list[str], brief: StoryTextInputV1, *,
                           character_refs: list[CharacterRef] | None = None,
                           character_root: Path = DEFAULT_CHARACTER_ROOT) -> StartReceipt:
    from backend.openrouter import SelectedCharacter, pin_story_owner

    brief = StoryTextInputV1.model_validate(brief)
    refs = [] if character_refs is None else character_refs
    if type(refs) is not list or len(refs) > 16:
        raise InvalidCharacterSelection("At most 16 character refs are supported")
    refs = [CharacterRef.model_validate(ref) for ref in refs]
    ids = [subject.subject_id for subject in brief.subjects] + [ref.subject_id for ref in refs]
    if len(ids) > 16 or len(ids) != len(set(ids)):
        raise InvalidCharacterSelection("Selected subjects and character refs must be unique, at most 16 combined")
    _validated_test_inputs(project_id, brief.user_vibe, shot_ids)
    if len(shot_ids) > 8 or type(client_key) is not str or not 0 < len(client_key) <= 128:
        raise ValueError("Live Story needs 1–8 shots and a bounded client key")
    await validate_story_storage(db, saver)
    old = db.execute("SELECT execution_id,shot_ids,owner_config FROM executions WHERE project_id=? AND client_key=?", (project_id, client_key)).fetchone()
    if old:
        if old[2] is None or json.loads(old[1]) != shot_ids or _live_submission(old[2]) != (brief, refs):
            raise ValueError("Start client key conflicts with another payload")
        return load_test_story_start(db, old[0])[0]  # Replay works even with missing credentials/new env settings.
    def resolve():
        repo = CharacterRepository(character_root)
        return [SelectedCharacter(ref=ref, character=repo.read_exact(ref)) for ref in refs]
    try:
        selected = await asyncio.to_thread(resolve) if refs else []
    except ValueError as error:
        raise InvalidCharacterSelection("Invalid selected character revision") from error
    resolved_brief = StoryTextInputV1(user_vibe=brief.user_vibe, shot_duration_ms=brief.shot_duration_ms,
                                     subjects=brief.subjects + [item.narrative_subject() for item in selected])
    owner_config = await pin_story_owner(resolved_brief, selected)
    return await _start_story(db, saver, project_id, client_key, brief.user_vibe, shot_ids, owner_config)


def _live_submission(body: str) -> tuple[StoryTextInputV1, list[CharacterRef]]:
    """Recover submitted subjects/refs without consulting the library or environment."""
    from backend.openrouter import StoryOwnerConfigV2, read_owner_config
    config = read_owner_config(body)
    selected = config.selected_characters if isinstance(config, StoryOwnerConfigV2) else []
    subjects = config.brief.subjects[:-len(selected)] if selected else config.brief.subjects
    return (StoryTextInputV1(user_vibe=config.brief.user_vibe, subjects=subjects,
                             shot_duration_ms=config.brief.shot_duration_ms), [item.ref for item in selected])


async def _start_story(db, saver, project_id, client_key, input_message, shot_ids, owner_config):
    """Caller owns open_database(root) and open_saver(root, db) for this whole call."""
    _validated_test_inputs(project_id, input_message, shot_ids)
    if type(client_key) is not str or not 0 < len(client_key) <= 256:
        raise ValueError("Invalid start client key")
    client_key.encode("utf-8")
    await validate_story_storage(db, saver)
    digest = _payload_digest(input_message, shot_ids, owner_config)
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute("SELECT execution_id,start_digest FROM executions WHERE project_id=? AND client_key=?",
                         (project_id, client_key)).fetchone()
        if row:
            receipt, _ = load_test_story_start(db, row[0])
            if row[1] != digest:
                # A concurrent live acceptance may have pinned the same submission first.
                old = db.execute("SELECT input_message,shot_ids,owner_config FROM executions WHERE execution_id=?", (row[0],)).fetchone()
                if owner_config is None or old[2] is None or old[:2] != (input_message, json.dumps(shot_ids, ensure_ascii=False, separators=(",", ":"))) or _live_submission(old[2]) != _live_submission(owner_config):
                    raise ValueError("Start client key conflicts with another payload")
        else:
            execution_id, work_id = str(uuid4()), str(uuid4())
            if owner_config is not None:
                from backend.openrouter import read_owner_config
                version = read_owner_config(owner_config).adapter_version
                graph_identity = (LIVE_GRAPH_ID, version, LIVE_GRAPH_DIGESTS[version])
            else:
                graph_identity = (GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST)
            db.execute(
                "INSERT INTO executions (execution_id,project_id,input_message,shot_ids,client_key,start_digest,"
                "graph_id,graph_version,graph_digest,owner_config) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (execution_id, project_id, input_message,
                 json.dumps(shot_ids, ensure_ascii=False, separators=(",", ":")), client_key,
                 digest, *graph_identity, owner_config),
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
