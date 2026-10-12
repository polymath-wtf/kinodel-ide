"""Private immutable anchor jobs and explicitly allocated technical attempt intents.

Caller holds the existing data-root OS lock. Exact published batch/unit references
freeze graph, schemas, mappings, endpoint identity, output and resolved settings
without copying those bodies. Every read revalidates both SQL and managed bytes.
This fingerprint is NOT a native HTTP request, provider acceptance, Start or submit
authorization. Reopening says nothing about whether a request was sent. Native
envelope/correlation, dispatch and reconciliation remain in submission storage.
Retry allocation is failed-only and does not grant native dispatch authorization.
"""

from dataclasses import dataclass, replace
import json
import sqlite3
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter

from backend import batch_generation as generation, batch_store, comfyui_workflows
from backend.batch_generation import ParentBindings, PreparedBatchUnitV1
from backend.batch_store import _committed, _identity, _transaction
from backend.domain import DomainModel, Text, canonical_json, sha256_digest
from backend.wardrobe import AnchorKey, ExactDigest


class _SubmissionIntentPinsV1(DomainModel):
    """Exact protected pin references, not a POST /prompt wire envelope."""

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


class PortraitSubmissionIntentV1(_SubmissionIntentPinsV1):
    schema_id: Literal['comfyui_portrait_submission_intent']


AnchorUnitKind = Literal['portrait', 'background', 'sheet']


class AnchorUnitSubmissionIntentV1(_SubmissionIntentPinsV1):
    schema_id: Literal['comfyui_anchor_unit_submission_intent']
    kind: Literal['background', 'sheet']


@dataclass(frozen=True, repr=False)
class PortraitJobV1:
    job_id: str
    attempt_id: str
    intent_digest: str
    intent_body: bytes
    prepared_input: PreparedBatchUnitV1

    @property
    def kind(self) -> AnchorUnitKind:
        return TypeAdapter(AnchorUnitKind).validate_python(json.loads(self.prepared_input.image_pin_json)['kind'])


AnchorUnitJobV1 = PortraitJobV1


class AnchorRetryAllocationV1(DomainModel):
    schema_version: Literal['1']
    job_id: ExactDigest
    attempt_id: ExactDigest
    unit_input_digest: ExactDigest
    retry_trigger_id: ExactDigest
    previous_attempt_id: ExactDigest
    previous_revision: Annotated[int, Field(strict=True, ge=0, le=2**63 - 2)]
    previous_submission_digest: ExactDigest
    previous_wire_digest: ExactDigest


def _anchor_inputs(db: sqlite3.Connection, batch_id: str, unit_key: str, expected_unit_digest: str,
                   parent_bindings: ParentBindings | list[dict] | None = None
                   ) -> tuple[batch_store.BatchInputPinV1, batch_store.BatchUnitInputPinV1]:
    TypeAdapter(ExactDigest).validate_python(batch_id, strict=True)
    TypeAdapter(AnchorKey).validate_python(unit_key, strict=True)
    TypeAdapter(ExactDigest).validate_python(expected_unit_digest, strict=True)
    batch = batch_store.read_batch_input(db, batch_id)
    if parent_bindings is None:
        # On read recover the SQL-owned metadata, then revalidate its digest AND exact
        # managed bytes below. These pins are not verified media/rights/upload receipts.
        row = batch_store._unit_row(db, batch_id, unit_key)
        if row is None or row[5] != 'published':
            raise LookupError('Prepared batch unit is not published')
        body = batch_store._body(row[3])
        if row[2] != expected_unit_digest or sha256_digest(body) != row[2]:
            raise ValueError('Prepared input selector/body conflicts with published unit')
        value = json.loads(body)
        if type(value) is not dict or 'parent_bindings' not in value:
            raise ValueError('Invalid stored prepared parent metadata')
        parent_bindings = value['parent_bindings']
    parent_bindings = TypeAdapter(ParentBindings).validate_python(parent_bindings, strict=True)
    unit = batch_store.read_prepared_batch_unit(db, batch_id, unit_key, parent_bindings=parent_bindings)
    if unit.input_digest != expected_unit_digest:
        raise ValueError('Prepared input selector conflicts with published unit')
    _, planned, binding = generation._unit(batch.prepared_input, unit_key)
    image = comfyui_workflows.replay_prepared(unit.prepared_input.image_pin_json)
    signatures = {
        'portrait': ('hero-face', 'txt2img', [], 'krea2-txt2img', '865'),
        'background': ('location', 'txt2img', [], 'krea2-txt2img', '865'),
        'sheet': ('hero-sheet', 'img2img', ['portrait', 'background'], 'qwen21-multi-img2img', '494'),
    }
    kind = TypeAdapter(AnchorUnitKind).validate_python(binding.kind, strict=True)
    use_case, workflow, roles, workflow_id, output_node = signatures[kind]
    if ((planned.use_case, planned.workflow, binding.reference_roles, binding.workflow_id) !=
            (use_case, workflow, roles, workflow_id) or image['kind'] != kind
            or [ref['role'] for ref in image['references']] != roles
            or image['expected_output'] != dict(node_id=output_node, class_type='SaveImage',
                                               history_key='images', media_type='image/png')):
        raise ValueError('Initial anchor job conflicts with exact supported role/mapping/output')
    return batch, unit


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
    kind = json.loads(unit.prepared_input.image_pin_json)['kind']
    if kind == 'portrait':
        job_id = _identity('kinodel.comfyui-portrait-job.v1', batch.batch_id, unit.unit_key)
        attempt_id = _identity('kinodel.comfyui-initial-attempt.v1', job_id)
        model, fields = PortraitSubmissionIntentV1, dict(schema_id='comfyui_portrait_submission_intent')
    else:
        job_id = _identity('kinodel.comfyui-anchor-unit-job.v1', kind, batch.batch_id, unit.unit_key)
        attempt_id = _identity('kinodel.comfyui-anchor-unit-initial-attempt.v1', job_id)
        model, fields = AnchorUnitSubmissionIntentV1, dict(schema_id='comfyui_anchor_unit_submission_intent', kind=kind)
    intent = model(**fields, schema_version='1',
        job_id=job_id, attempt_id=attempt_id, project_id=batch.prepared_input.source_plan_ref.project_id,
        batch_id=batch.batch_id, batch_input_digest=batch.input_digest, batch_input_uri=batch.uri,
        unit_key=unit.unit_key, unit_input_digest=unit.input_digest, unit_input_uri=unit.uri)
    body = canonical_json(intent)
    return PortraitJobV1(job_id, attempt_id, sha256_digest(body), body, unit.prepared_input)


def _initial_attempt_id(job_id, batch_id, unit_key):
    portrait = job_id == _identity('kinodel.comfyui-portrait-job.v1', batch_id, unit_key)
    return _identity('kinodel.comfyui-initial-attempt.v1' if portrait
                     else 'kinodel.comfyui-anchor-unit-initial-attempt.v1', job_id)


def _row(db: sqlite3.Connection, job_id: str, attempt_id: str | None = None):
    if attempt_id is None:
        binding = db.execute('SELECT batch_id,unit_key FROM render_jobs WHERE job_id=?', (job_id,)).fetchone()
        if binding is None:
            return None
        attempt_id = _initial_attempt_id(job_id, *binding)
    TypeAdapter(ExactDigest).validate_python(attempt_id, strict=True)
    return db.execute('SELECT j.job_id,j.batch_id,j.unit_key,j.unit_input_digest,'
                      'a.attempt_id,a.intent_digest,a.intent_body FROM render_jobs j '
                      'LEFT JOIN render_submission_attempts a ON a.job_id=j.job_id AND a.attempt_id=? WHERE j.job_id=?',
                      (attempt_id, job_id)).fetchone()


def _attempt_record(initial, attempt_id):
    if attempt_id == initial.attempt_id:
        return initial
    intent = json.loads(initial.intent_body)
    intent['attempt_id'] = TypeAdapter(ExactDigest).validate_python(attempt_id, strict=True)
    model = PortraitSubmissionIntentV1 if initial.kind == 'portrait' else AnchorUnitSubmissionIntentV1
    body = canonical_json(model.model_validate(intent))
    return replace(initial, attempt_id=attempt_id, intent_digest=sha256_digest(body), intent_body=body)


def _allocation_row(db, attempt_id):
    return db.execute('SELECT attempt_id,job_id,previous_attempt_id,retry_trigger_id,allocation_digest,allocation_body '
                      'FROM render_retry_allocations WHERE attempt_id=?', (attempt_id,)).fetchone()


def _allocation_values(record):
    body = canonical_json(record)
    return (record.attempt_id, record.job_id, record.previous_attempt_id, record.retry_trigger_id,
            sha256_digest(body), body.decode())


def _validate_retry_lineage(db, initial, attempt_id):
    from backend import portrait_submission_store as submissions
    seen = set()
    while attempt_id != initial.attempt_id:
        if attempt_id in seen:
            raise ValueError('Retry attempt lineage cycle')
        seen.add(attempt_id)
        row = _allocation_row(db, attempt_id)
        if row is None:
            raise ValueError('Attempt is not an explicitly allocated retry of this job')
        allocation = AnchorRetryAllocationV1.model_validate_json(row[5])
        if (row != _allocation_values(allocation) or allocation.job_id != initial.job_id
                or allocation.unit_input_digest != json.loads(initial.intent_body)['unit_input_digest']
                or allocation.attempt_id != _identity('kinodel.comfyui-anchor-unit-retry-attempt.v1',
                    initial.job_id, allocation.previous_attempt_id, allocation.retry_trigger_id)):
            raise ValueError('Retry allocation identity/provenance mismatch')
        previous = submissions._row(db, initial.job_id, allocation.previous_attempt_id)
        if previous is None:
            raise ValueError('Retry predecessor facts are missing')
        model = (submissions.SheetSubmissionV1 if initial.kind == 'sheet' else
                 submissions.AnchorUnitSubmissionV1 if initial.kind == 'background' else submissions.PortraitSubmissionV1)
        facts = model.model_validate_json(previous[4])
        expected = _attempt_record(initial, allocation.previous_attempt_id)
        expected_row = (expected.job_id, json.loads(expected.intent_body)['batch_id'],
            expected.prepared_input.unit_key, allocation.unit_input_digest, expected.attempt_id,
            expected.intent_digest, expected.intent_body.decode())
        if (previous != submissions._values(facts) or facts.state != 'failed'
                or (previous[0], previous[1], previous[2], previous[3], previous[5]) !=
                   (allocation.previous_attempt_id, allocation.job_id, allocation.previous_wire_digest,
                    allocation.previous_submission_digest, allocation.previous_revision)
                or (facts.preview.intent_digest, facts.preview.unit_input_digest) !=
                   (expected.intent_digest, allocation.unit_input_digest)
                or _row(db, initial.job_id, allocation.previous_attempt_id) != expected_row):
            raise ValueError('Retry predecessor is not the exact retained failed attempt')
        attempt_id = allocation.previous_attempt_id


def _restore(row, batch: batch_store.BatchInputPinV1, unit: batch_store.BatchUnitInputPinV1,
             db: sqlite3.Connection | None = None) -> PortraitJobV1:
    record = _record(batch, unit)
    if row[4] != record.attempt_id:
        if db is None or row[4] is None:
            raise ValueError('Attempt selector does not belong to this job')
        # Initial intent remains the historical owner; never infer it from row order.
        _restore(_row(db, record.job_id), batch, unit)
        _validate_retry_lineage(db, record, row[4])
        record = _attempt_record(record, row[4])
    if row != (record.job_id, batch.batch_id, unit.unit_key, unit.input_digest,
               record.attempt_id, record.intent_digest, record.intent_body.decode('utf-8')):
        raise ValueError('Stored job/initial intent identity or body mismatch; refusing repair')
    return record


def read_portrait_job(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                      attempt_id: str | None = None) -> PortraitJobV1:
    """Offline exact replay. Existing intent never establishes acceptance or unsent status."""
    _committed(db)
    TypeAdapter(ExactDigest).validate_python(job_id, strict=True)
    row = _row(db, job_id, attempt_id)
    if row is None:
        raise LookupError('Portrait job is not committed')
    batch, unit = _inputs(db, row[1], row[2], expected_unit_digest)
    return _restore(row, batch, unit, db)


def create_portrait_job(db: sqlite3.Connection, batch_id: str, unit_key: str, *,
                        expected_unit_digest: str) -> PortraitJobV1:
    """Commit job binding and immutable initial intent together, or replay the exact pair.

    No replacement graph/profile/connection/seed is accepted. This internal storage
    operation does not grant permission to dispatch, retry or activate a graph.
    """
    _committed(db)
    batch, unit = _inputs(db, batch_id, unit_key, expected_unit_digest)
    return _create(db, batch, unit)


def read_anchor_unit_job(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                         attempt_id: str | None = None) -> AnchorUnitJobV1:
    """Offline exact replay for the three pinned anchor roles; never native authorization."""
    _committed(db)
    TypeAdapter(ExactDigest).validate_python(job_id, strict=True)
    row = _row(db, job_id, attempt_id)
    if row is None:
        raise LookupError('Anchor unit job is not committed')
    # Keep the accepted portrait read path (including its validation cost) exact.
    # SQL ID alone is never trusted: _restore still checks the full immutable pair.
    if job_id == _identity('kinodel.comfyui-portrait-job.v1', row[1], row[2]):
        batch, unit = _inputs(db, row[1], row[2], expected_unit_digest)
    else:
        batch, unit = _anchor_inputs(db, row[1], row[2], expected_unit_digest)
    return _restore(row, batch, unit, db)


def create_anchor_unit_job(db: sqlite3.Connection, batch_id: str, unit_key: str, *,
                          expected_unit_digest: str, parent_bindings: ParentBindings | list[dict],
                          image_execution_id: str | None = None) -> AnchorUnitJobV1:
    """Commit ONE initial intent with exact ordered prepared parents (not media verification)."""
    _committed(db)
    parent_bindings = TypeAdapter(ParentBindings).validate_python(parent_bindings, strict=True)
    batch, unit = _anchor_inputs(db, batch_id, unit_key, expected_unit_digest, parent_bindings)
    return _create(db, batch, unit, image_execution_id)


def _create(db: sqlite3.Connection, batch: batch_store.BatchInputPinV1,
            unit: batch_store.BatchUnitInputPinV1, image_execution_id=None) -> AnchorUnitJobV1:
    batch_id, unit_key = batch.batch_id, unit.unit_key
    record = _record(batch, unit)
    row = _row(db, record.job_id)
    if row is not None:
        return _restore(row, batch, unit)
    if db.execute('SELECT job_id FROM render_jobs WHERE batch_id=? AND unit_key=?',
                  (batch_id, unit_key)).fetchone() is not None:
        raise ValueError('Stored logical job identity mismatch; refusing replacement')
    with _transaction(db):
        batch_store._assert_image_turn(db, batch_id, unit_key, image_execution_id)
        db.execute('INSERT INTO render_jobs VALUES (?,?,?,?)',
                   (record.job_id, batch_id, unit_key, unit.input_digest))
        db.execute('INSERT INTO render_submission_attempts VALUES (?,?,?,?)',
                   (record.attempt_id, record.job_id, record.intent_digest, record.intent_body.decode('utf-8')))
    return record


def allocate_anchor_unit_retry(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
        previous_attempt_id: str, expected_previous_wire_digest: str, expected_previous_revision: int,
        retry_trigger_id: str, image_execution_id: str | None = None) -> AnchorUnitJobV1:
    """Trusted durable trigger allocates one successor of an exact FAILED attempt.

    Allocation is not authorization/HTTP. Native preview and fixed-budget authorization
    must separately name the returned attempt. A changed trigger cannot branch the
    same predecessor; successful/blocked/unknown attempts are never allocated anew.
    """
    from backend import portrait_submission_store as submissions
    previous_job = read_anchor_unit_job(db, job_id, expected_unit_digest=expected_unit_digest,
                                       attempt_id=previous_attempt_id)
    TypeAdapter(ExactDigest).validate_python(retry_trigger_id, strict=True)
    TypeAdapter(submissions.Revision).validate_python(expected_previous_revision, strict=True)
    loaded = submissions._load(db, job_id, expected_unit_digest, expected_previous_wire_digest,
                               attempt_id=previous_attempt_id)
    previous, previous_row, bindings, frozen_rows = loaded
    if previous.state != 'failed' or previous.revision != expected_previous_revision:
        raise ValueError('Retry allocation requires the exact failed predecessor revision')
    attempt_id = _identity('kinodel.comfyui-anchor-unit-retry-attempt.v1', job_id, previous_attempt_id, retry_trigger_id)
    allocation = AnchorRetryAllocationV1(schema_version='1', job_id=job_id, attempt_id=attempt_id,
        unit_input_digest=expected_unit_digest, retry_trigger_id=retry_trigger_id,
        previous_attempt_id=previous_attempt_id, previous_revision=expected_previous_revision,
        previous_submission_digest=previous_row[3], previous_wire_digest=expected_previous_wire_digest)
    existing = _allocation_row(db, attempt_id)
    if existing is not None:
        if existing != _allocation_values(allocation):
            raise ValueError('Retry trigger conflicts with retained allocation')
        return read_anchor_unit_job(db, job_id, expected_unit_digest=expected_unit_digest, attempt_id=attempt_id)
    record = _attempt_record(previous_job, attempt_id)
    with _transaction(db):
        intent = json.loads(previous_job.intent_body)
        turn = batch_store._assert_image_turn(db, intent['batch_id'], intent['unit_key'], image_execution_id)
        if turn is not None:
            predecessor = db.execute('SELECT result.body FROM image_group_retry_requests r JOIN image_group_results result '
                'ON result.result_id=r.predecessor_result_id WHERE r.execution_id=? AND r.acceptance_state=\'accepted\'',
                (turn[1],)).fetchone()
            failure = None if predecessor is None else json.loads(predecessor[0])['failure']
            if (retry_trigger_id != turn[0] or failure is None or
                    (failure['job_id'], failure['unit_key'], failure['attempt_id'], failure['wire_digest'],
                     failure['revision'], failure['submission_digest']) !=
                    (job_id, intent['unit_key'], previous_attempt_id, expected_previous_wire_digest,
                     expected_previous_revision, previous_row[3])):
                raise ValueError('Image retry allocation must own the accepting group and exact failed turn')
        submissions._assert_pins(db, bindings, frozen_rows)
        if submissions._row(db, job_id, previous_attempt_id) != previous_row:
            raise ValueError('Failed predecessor changed before retry allocation CAS')
        if db.execute('SELECT 1 FROM render_retry_allocations WHERE previous_attempt_id=? OR '
                      '(job_id=? AND retry_trigger_id=?)', (previous_attempt_id, job_id, retry_trigger_id)).fetchone():
            raise ValueError('Retry predecessor/trigger already owns a different allocation')
        db.execute('INSERT INTO render_submission_attempts VALUES (?,?,?,?)',
                   (record.attempt_id, record.job_id, record.intent_digest, record.intent_body.decode()))
        db.execute('INSERT INTO render_retry_allocations VALUES (?,?,?,?,?,?)', _allocation_values(allocation))
    return record


def assert_anchor_attempt_writable(db: sqlite3.Connection, job_id: str, attempt_id: str) -> None:
    """SQL-only native-effect fence; accepted image origin is not its text source.

    A missing image binding is a rejection, not a standalone-job escape hatch.
    Keep historical standalone 6A/B entrypoints otherwise unchanged.
    """
    if db.execute('SELECT 1 FROM render_jobs j JOIN image_groups g ON g.batch_id=j.batch_id WHERE j.job_id=?',
                  (job_id,)).fetchone():
        from backend.image_group_results import assert_image_attempt_writable
        assert_image_attempt_writable(db, job_id, attempt_id)
