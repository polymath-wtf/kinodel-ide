"""Private immutable portrait job and its ONE initial technical submission intent.

Caller holds the existing data-root OS lock. Exact published batch/unit references
freeze graph, schemas, mappings, endpoint identity, output and resolved settings
without copying those bodies. Every read revalidates both SQL and managed bytes.
This fingerprint is NOT a native HTTP request, provider acceptance, Start or submit
authorization. Reopening says nothing about whether a request was sent. Native
envelope/correlation, dispatch, reconciliation and authorized retries belong to 6A;
there is deliberately no state machine, prompt_id or second-attempt allocator here.
"""

from dataclasses import dataclass
import sqlite3
from typing import Literal

from pydantic import TypeAdapter

from backend import batch_generation as generation, batch_store, comfyui_workflows
from backend.batch_generation import PreparedBatchUnitV1
from backend.batch_store import _committed, _identity, _transaction
from backend.domain import DomainModel, Text, canonical_json, sha256_digest
from backend.wardrobe import AnchorKey, ExactDigest


class PortraitSubmissionIntentV1(DomainModel):
    """Exact protected pin references, not a POST /prompt wire envelope."""

    schema_id: Literal['comfyui_portrait_submission_intent']
    schema_version: Literal['1']
    job_id: ExactDigest
    attempt_id: ExactDigest
    project_id: Text
    batch_id: ExactDigest
    batch_input_digest: ExactDigest
    batch_input_uri: Text
    unit_key: AnchorKey
    unit_input_digest: ExactDigest
    unit_input_uri: Text


@dataclass(frozen=True, repr=False)
class PortraitJobV1:
    job_id: str
    attempt_id: str
    intent_digest: str
    intent_body: bytes
    prepared_input: PreparedBatchUnitV1


def _inputs(db: sqlite3.Connection, batch_id: str, unit_key: str, expected_unit_digest: str):
    TypeAdapter(ExactDigest).validate_python(batch_id, strict=True)
    TypeAdapter(AnchorKey).validate_python(unit_key, strict=True)
    TypeAdapter(ExactDigest).validate_python(expected_unit_digest, strict=True)
    batch = batch_store.read_batch_input(db, batch_id)
    unit = batch_store.read_prepared_batch_unit(db, batch_id, unit_key, parent_bindings=[])
    if unit.input_digest != expected_unit_digest:
        raise ValueError('Prepared input selector conflicts with published unit')
    _, planned, binding = generation._unit(batch.prepared_input, unit_key)
    image = comfyui_workflows.replay_prepared(unit.prepared_input.image_pin_json)
    if (planned.use_case != 'hero-face' or planned.workflow != 'txt2img' or planned.references
            or binding.kind != 'portrait' or binding.reference_roles
            or unit.prepared_input.parent_bindings or image['kind'] != 'portrait' or image['references']):
        raise ValueError('Initial job storage supports only zero-reference txt2img hero-face portraits')
    return batch, unit


def _record(batch: batch_store.BatchInputPinV1, unit: batch_store.BatchUnitInputPinV1) -> PortraitJobV1:
    job_id = _identity('kinodel.comfyui-portrait-job.v1', batch.batch_id, unit.unit_key)
    attempt_id = _identity('kinodel.comfyui-initial-attempt.v1', job_id)
    intent = PortraitSubmissionIntentV1(schema_id='comfyui_portrait_submission_intent', schema_version='1',
        job_id=job_id, attempt_id=attempt_id, project_id=batch.prepared_input.source_plan_ref.project_id,
        batch_id=batch.batch_id, batch_input_digest=batch.input_digest, batch_input_uri=batch.uri,
        unit_key=unit.unit_key, unit_input_digest=unit.input_digest, unit_input_uri=unit.uri)
    body = canonical_json(intent)
    return PortraitJobV1(job_id, attempt_id, sha256_digest(body), body, unit.prepared_input)


def _row(db: sqlite3.Connection, job_id: str):
    return db.execute('SELECT j.job_id,j.batch_id,j.unit_key,j.unit_input_digest,'
                      'a.attempt_id,a.intent_digest,a.intent_body FROM render_jobs j '
                      'LEFT JOIN render_submission_attempts a ON a.job_id=j.job_id WHERE j.job_id=?',
                      (job_id,)).fetchone()


def _restore(row, batch: batch_store.BatchInputPinV1, unit: batch_store.BatchUnitInputPinV1) -> PortraitJobV1:
    record = _record(batch, unit)
    if row != (record.job_id, batch.batch_id, unit.unit_key, unit.input_digest,
               record.attempt_id, record.intent_digest, record.intent_body.decode('utf-8')):
        raise ValueError('Stored job/initial intent identity or body mismatch; refusing repair')
    return record


def read_portrait_job(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str) -> PortraitJobV1:
    """Offline exact replay. Existing intent never establishes acceptance or unsent status."""
    _committed(db)
    TypeAdapter(ExactDigest).validate_python(job_id, strict=True)
    row = _row(db, job_id)
    if row is None:
        raise LookupError('Portrait job is not committed')
    batch, unit = _inputs(db, row[1], row[2], expected_unit_digest)
    return _restore(row, batch, unit)


def create_portrait_job(db: sqlite3.Connection, batch_id: str, unit_key: str, *,
                        expected_unit_digest: str) -> PortraitJobV1:
    """Commit job binding and immutable initial intent together, or replay the exact pair.

    No replacement graph/profile/connection/seed is accepted. This internal storage
    operation does not grant permission to dispatch, retry or activate a graph.
    """
    _committed(db)
    batch, unit = _inputs(db, batch_id, unit_key, expected_unit_digest)
    record = _record(batch, unit)
    row = _row(db, record.job_id)
    if row is not None:
        return _restore(row, batch, unit)
    if db.execute('SELECT job_id FROM render_jobs WHERE batch_id=? AND unit_key=?',
                  (batch_id, unit_key)).fetchone() is not None:
        raise ValueError('Stored logical job identity mismatch; refusing replacement')
    with _transaction(db):
        db.execute('INSERT INTO render_jobs VALUES (?,?,?,?)',
                   (record.job_id, batch_id, unit_key, unit.input_digest))
        db.execute('INSERT INTO render_submission_attempts VALUES (?,?,?,?)',
                   (record.attempt_id, record.job_id, record.intent_digest, record.intent_body.decode('utf-8')))
    return record
