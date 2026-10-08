"""Private pre-submit input pins, not image activations, jobs or creative results.

Caller holds the existing data-root OS lock. Commit the full reservation before
publishing bytes; retries finalize those bytes without source/catalog/RNG lookup.
Published pins never heal a missing or corrupt file. No transport belongs here.
Parent metadata proves neither actual image bytes, rights nor import lineage.
"""

from contextlib import contextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sqlite3
import stat

from pydantic import TypeAdapter

from backend import batch_generation as generation, batch_preparation
from backend.batch_generation import (BatchConnectionPinV1, BatchGenerationInputV1, ParentBindings,
                                      PreparedBatchUnitV1)
from backend.comfyui import NativeImagePreparationContext
from backend.database import _check_file, _sync_directory
from backend.domain import (ArtifactRef, ExactProfilePin, MAX_JSON_BYTES, MediaSize, _exact_artifact_ref,
                            canonical_json, sha256_digest)
from backend.story_store import _root, _uuid
from backend.wardrobe import AnchorKey, ExactDigest


@dataclass(frozen=True, repr=False)
class BatchInputPinV1:
    batch_id: str
    input_digest: str
    uri: str
    prepared_input: BatchGenerationInputV1


@dataclass(frozen=True, repr=False)
class BatchUnitInputPinV1:
    batch_id: str
    unit_key: str
    input_digest: str
    uri: str
    prepared_input: PreparedBatchUnitV1


def _committed(db: sqlite3.Connection) -> None:
    if db.in_transaction:
        raise ValueError("Batch pin access requires committed caller state")


@contextmanager
def _transaction(db: sqlite3.Connection):
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise


def _identity(*parts: str) -> str:
    return sha256_digest(json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _uri(project_id: str, identity: str, digest: str) -> str:
    _uuid(project_id)
    TypeAdapter(ExactDigest).validate_python(identity, strict=True)
    TypeAdapter(ExactDigest).validate_python(digest, strict=True)
    return f"kinodel://projects/{project_id}/inputs/{identity[7:]}.{digest[7:]}.json"


def _directories(path: Path, *, missing: bool = False) -> None:
    # Inspect EVERY ancestor, not just inputs: reads must reject redirected projects/root too.
    for parent in reversed(path.parents):
        try:
            info = parent.lstat()
        except FileNotFoundError:
            if missing:
                continue
            raise
        if (not stat.S_ISDIR(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError("Managed input directory was redirected")


def _read_file(path: Path) -> bytes:
    _directories(path)
    _check_file(path)
    return _read_bytes(path)


def _read_bytes(path: Path) -> bytes:
    # Caller has checked regular-file identity/link ownership before opening.
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError("Managed input file is too large")
    with path.open("rb") as source:
        body = source.read(MAX_JSON_BYTES + 1)
    if not 0 < len(body) <= MAX_JSON_BYTES:
        raise ValueError("Managed input file size is invalid")
    return body


def _body(value: str) -> bytes:
    if type(value) is not str or not 0 < len(value) <= MAX_JSON_BYTES:
        raise ValueError("Reserved input body size is invalid")
    body = value.encode("utf-8")
    if len(body) > MAX_JSON_BYTES:
        raise ValueError("Reserved input body is too large")
    return body


def _publish(path: Path, body: bytes) -> None:
    """Reserved pins only: recover our exact staging alias, never arbitrary links.

    The deterministic alias is derived from the SQL-validated destination identity
    AND digest. A crash inside link publication leaves exactly these two names of
    one inode; only that pair with the original canonical bytes may be unlinked.
    Before linking, an empty/proper-prefix single-link alias can be completed in
    place under the root lock. Destination-present and published bytes stay exact.
    """
    _directories(path, missing=True)
    for directory in (path.parent.parent.parent, path.parent.parent, path.parent):
        if not directory.exists():
            directory.mkdir()
            _sync_directory(directory.parent)
    staging = path.with_name('.batch-' + sha256_digest(path.name.encode('ascii'))[7:] + '.tmp')
    try:
        staging.lstat()
    except FileNotFoundError:
        try:
            existing = _read_file(path)
        except FileNotFoundError:
            created = None
            try:
                with staging.open('xb') as target:
                    created = os.fstat(target.fileno())
                    target.write(body)
                    target.flush()
                    os.fsync(target.fileno())
            except BaseException:
                if created is not None:
                    _check_file(staging)
                    if not os.path.samestat(created, staging.lstat()):
                        raise ValueError("Input staging file identity changed")
                    staging.unlink()  # Only this invocation's exclusive, single-link file.
                    _sync_directory(staging.parent)
                raise
        else:
            if existing != body:
                raise ValueError("Conflicting immutable input bytes")
            return
    try:
        path.lstat()
    except FileNotFoundError:
        _directories(staging)
        _check_file(staging)
        expected = staging.lstat()
        if expected.st_size > MAX_JSON_BYTES:
            raise ValueError("Managed input file is too large")
        with staging.open('rb+') as source:  # Windows fsync requires a writable descriptor.
            if not os.path.samestat(expected, os.fstat(source.fileno())):
                raise ValueError("Input staging file identity changed")
            prefix = source.read(MAX_JSON_BYTES + 1)
            if len(prefix) > MAX_JSON_BYTES or not body.startswith(prefix):
                raise ValueError("Conflicting reserved input staging bytes")
            _check_file(staging)
            if not os.path.samestat(expected, staging.lstat()):
                raise ValueError("Input staging file identity changed")
            if len(prefix) < len(body):
                source.seek(len(prefix))
                source.write(body[len(prefix):])
                source.flush()
            os.fsync(source.fileno())
        if _read_file(staging) != body:
            raise ValueError("Conflicting reserved input staging bytes")
        os.link(staging, path)  # Exclusive publication; process death may leave both names.
    infos = (staging.lstat(), path.lstat())
    if (any(not stat.S_ISREG(info.st_mode) or info.st_nlink != 2
            or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT for info in infos)
            or not os.path.samestat(*infos)):
        raise ValueError("Reserved input staging alias is not the exclusive publication pair")
    if _read_bytes(staging) != body:
        raise ValueError("Conflicting reserved input staging bytes")
    _sync_directory(path.parent)
    staging.unlink()
    _sync_directory(path.parent)


def _publish_body(path: Path, body: bytes) -> None:
    _publish(path, body)
    if _read_file(path) != body:
        raise ValueError("Published input bytes mismatch")


def _batch_row(db: sqlite3.Connection, batch_id: str):
    return db.execute("SELECT batch_id,execution_id,stage_id,activation_id,source_artifact_id,"
                      "input_digest,body,uri,publication_state FROM batch_input_pins WHERE batch_id=?",
                      (batch_id,)).fetchone()


def _restore_batch(db: sqlite3.Connection, row) -> tuple[BatchInputPinV1, bytes, Path]:
    body = _body(row[6])
    batch = generation.replay_batch_input(body, expected_digest=row[5])
    identity = _identity("kinodel.batch-input.v1", batch.source_plan_ref.execution_id,
                         batch.stage_id, batch.activation_id)
    uri = _uri(batch.source_plan_ref.project_id, identity, row[5])
    if (row[:5] != (identity, batch.source_plan_ref.execution_id, batch.stage_id,
                    batch.activation_id, batch.source_plan_ref.artifact_id)
            or row[7] != uri or row[8] not in ("reserved", "published")
            or db.execute("SELECT project_id FROM executions WHERE execution_id=?", (row[1],)).fetchone()
               != (batch.source_plan_ref.project_id,)):
        raise ValueError("Stored batch input SQL identity mismatch")
    return BatchInputPinV1(identity, row[5], uri, batch), body, _root(db) / uri.removeprefix("kinodel://")


def read_batch_input(db: sqlite3.Connection, batch_id: str) -> BatchInputPinV1:
    """Exact offline replay of SQL-committed published private metadata and bytes."""
    _committed(db)
    row = _batch_row(db, batch_id)
    if row is None or row[8] != "published":
        raise LookupError("Batch input is not published")
    record, body, path = _restore_batch(db, row)
    if _read_file(path) != body:
        raise ValueError("Stored batch input file/body mismatch")
    return record


def pin_saved_batch_input(db: sqlite3.Connection, execution_id: str, *, source_plan_ref: ArtifactRef | dict,
                         image_size: MediaSize | dict, image_profile: ExactProfilePin | dict,
                         connection: BatchConnectionPinV1 | dict, activation_id: str) -> BatchInputPinV1:
    """Validate authority on FIRST reservation only; replay original pins on recovery.

    This identity records technical preparation, not an accepted graph activation.
    Completed Story/Wardrobe work and every creative binding remain unchanged.
    """
    _committed(db)
    _uuid(execution_id)
    activation_id = TypeAdapter(ExactDigest).validate_python(activation_id, strict=True)
    expected = (_exact_artifact_ref(ArtifactRef.model_validate(source_plan_ref)),
                MediaSize.model_validate(image_size), TypeAdapter(ExactProfilePin).validate_python(image_profile, strict=True),
                BatchConnectionPinV1.model_validate(connection))
    batch_id = _identity("kinodel.batch-input.v1", execution_id, "anchor-batch", activation_id)
    row = _batch_row(db, batch_id)
    if row is None:
        with _transaction(db):
            result = batch_preparation.read_saved_batch_input(db, execution_id, source_plan_ref=expected[0],
                image_size=expected[1], image_profile=expected[2], connection=expected[3], activation_id=activation_id)
            batch = result.prepared_input
            body = canonical_json(batch)
            uri = _uri(batch.source_plan_ref.project_id, batch_id, result.input_digest)
            db.execute("INSERT INTO batch_input_pins VALUES (?,?,?,?,?,?,?,?,?)",
                       (batch_id, execution_id, batch.stage_id, activation_id, batch.source_plan_ref.artifact_id,
                        result.input_digest, body.decode("utf-8"), uri, "reserved"))
        row = _batch_row(db, batch_id)
    record, body, path = _restore_batch(db, row)
    batch = record.prepared_input
    if (batch.source_plan_ref, batch.image_size, batch.image_profile, batch.connection) != expected:
        raise ValueError("Batch input request conflicts with original pins")
    if row[8] == "published":
        return read_batch_input(db, batch_id)
    _publish_body(path, body)
    with _transaction(db):
        changed = db.execute("UPDATE batch_input_pins SET publication_state='published' "
                             "WHERE batch_id=? AND input_digest=? AND body=? AND publication_state='reserved'",
                             (batch_id, record.input_digest, body.decode("utf-8")))
        if changed.rowcount != 1:
            raise ValueError("Batch input reservation changed during publication")
    return read_batch_input(db, batch_id)


def _unit_row(db: sqlite3.Connection, batch_id: str, unit_key: str):
    return db.execute("SELECT batch_id,unit_key,input_digest,body,uri,publication_state "
                      "FROM batch_unit_input_pins WHERE batch_id=? AND unit_key=?", (batch_id, unit_key)).fetchone()


def _restore_unit(db: sqlite3.Connection, batch: BatchInputPinV1, row, parent_bindings: ParentBindings | list[dict]
                  ) -> tuple[BatchUnitInputPinV1, bytes, Path]:
    body = _body(row[3])
    prepared = generation.replay_batch_unit(batch.prepared_input, body, expected_digest=row[2],
                                            parent_bindings=parent_bindings)
    identity = _identity("kinodel.batch-unit-input.v1", batch.batch_id, prepared.unit_key)
    uri = _uri(batch.prepared_input.source_plan_ref.project_id, identity, row[2])
    if row[:2] != (batch.batch_id, prepared.unit_key) or row[4] != uri or row[5] not in ("reserved", "published"):
        raise ValueError("Stored batch unit SQL identity mismatch")
    return (BatchUnitInputPinV1(batch.batch_id, prepared.unit_key, row[2], uri, prepared), body,
            _root(db) / uri.removeprefix("kinodel://"))


def read_prepared_batch_unit(db: sqlite3.Connection, batch_id: str, unit_key: str, *,
                             parent_bindings: ParentBindings | list[dict]) -> BatchUnitInputPinV1:
    """Replay with the required expected ORDERED parent pins; never resolve candidates."""
    _committed(db)
    unit_key = TypeAdapter(AnchorKey).validate_python(unit_key, strict=True)
    row = _unit_row(db, batch_id, unit_key)
    if row is None or row[5] != "published":
        raise LookupError("Prepared batch unit is not published")
    record, body, path = _restore_unit(db, read_batch_input(db, batch_id), row, parent_bindings)
    if _read_file(path) != body:
        raise ValueError("Stored batch unit file/body mismatch")
    return record


def prepare_saved_batch_unit(db: sqlite3.Connection, batch_id: str, unit_key: str, *,
                             parent_bindings: ParentBindings | list[dict],
                             context: NativeImagePreparationContext | None = None,
                             seed: int | None = None) -> BatchUnitInputPinV1:
    """Prepare only a NEW unit. A reservation already owns its resolved ONCE seed."""
    _committed(db)
    unit_key = TypeAdapter(AnchorKey).validate_python(unit_key, strict=True)
    row = _unit_row(db, batch_id, unit_key)  # FIRST: no current installed context or RNG on replay.
    batch = read_batch_input(db, batch_id)
    if row is None:
        _, unit, binding = generation._unit(batch.prepared_input, unit_key)
        generation._parents(unit, parent_bindings)
        if (not isinstance(context, NativeImagePreparationContext)
                or (context.workflow_id, context.registry_digest, context.connection, context.endpoint_digest) !=
                   (binding.workflow_id, binding.registry_digest, batch.prepared_input.connection.connection,
                    batch.prepared_input.connection.endpoint_digest)):
            raise ValueError("Installed preparation context conflicts with frozen batch pins")
        prepared = generation.prepare_batch_unit(batch.prepared_input, unit_key, parent_bindings=parent_bindings,
            template=context.template, schemas=context.schemas, model_inventory=context.model_inventory, seed=seed)
        body = canonical_json(prepared)
        digest = sha256_digest(body)
        identity = _identity("kinodel.batch-unit-input.v1", batch_id, unit_key)
        uri = _uri(batch.prepared_input.source_plan_ref.project_id, identity, digest)
        with _transaction(db):
            db.execute("INSERT INTO batch_unit_input_pins VALUES (?,?,?,?,?,?)",
                       (batch_id, unit_key, digest, body.decode("utf-8"), uri, "reserved"))
        row = _unit_row(db, batch_id, unit_key)
    record, body, path = _restore_unit(db, batch, row, parent_bindings)
    # None/-1 request ONCE resolution, not a different explicit seed on retry.
    if seed is not None and (type(seed) is not int or (seed != -1 and
            seed != json.loads(record.prepared_input.image_pin_json)["settings"]["seed"])):
        raise ValueError("Requested seed conflicts with original prepared unit")
    if row[5] == "published":
        return read_prepared_batch_unit(db, batch_id, unit_key, parent_bindings=parent_bindings)
    _publish_body(path, body)
    with _transaction(db):
        changed = db.execute("UPDATE batch_unit_input_pins SET publication_state='published' "
            "WHERE batch_id=? AND unit_key=? AND input_digest=? AND body=? AND publication_state='reserved'",
            (batch_id, unit_key, record.input_digest, body.decode("utf-8")))
        if changed.rowcount != 1:
            raise ValueError("Batch unit reservation changed during publication")
    return read_prepared_batch_unit(db, batch_id, unit_key, parent_bindings=parent_bindings)
