"""Exact image-only admission and same-execution Story/anchor group registration.

Caller owns the data-root lock (and open saver for admission). Historical sources
retain separate consumer/start semantics; the explicit Story/anchor route reuses
its own execution/start. Membership/dependencies live only in immutable inputs.
No graph invocation or provider work belongs here.
"""

from dataclasses import dataclass
import sqlite3
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import TypeAdapter

from backend import batch_preparation, batch_store, wardrobe_store
from backend.batch_generation import BatchConnectionPinV1
from backend.domain import (ArtifactRef, CanonicalUUID, DomainModel, ExactProfilePin, MediaSize,
                            _exact_artifact_ref, canonical_json, sha256_digest)
from backend.story_start import validate_story_storage
from backend.story_store import _assert_writable, _uuid
from backend.wardrobe import ExactDigest


GRAPH_ID = 'kinodel.image-only'
GRAPH_VERSION = '1'
GRAPH_DIGEST = sha256_digest(
    b'kinodel.image-only.v1:START>prepare_accepted_group>group_wait>exact_complete_set_join>END|unsolicited-resume=reject')
IMAGE_INPUT_MARKER = '[kinodel image-only start v1]'
STAGE_ID = 'anchor-batch'


@dataclass(frozen=True)
class ImageStartReceiptV1:
    execution_id: str
    work_id: str
    group_id: str
    wait_id: str
    stage_id: str
    activation_id: str
    request_digest: str
    batch_id: str
    input_digest: str


@dataclass(frozen=True, repr=False)
class ImageGroupV1:
    receipt: ImageStartReceiptV1
    batch: batch_store.BatchInputPinV1
    checkpoint_id: str | None
    task_id: str | None
    interrupt_id: str | None

    @property
    def wait_token(self) -> dict[str, str]:
        receipt = self.receipt
        return dict(wait_id=receipt.wait_id, stage_id=receipt.stage_id,
                    activation_id=receipt.activation_id, request_digest=receipt.request_digest)


def _key(value: str) -> str:
    if type(value) is not str or not 0 < len(value) <= 128:
        raise ValueError('Invalid image start client key')
    value.encode('utf-8')
    return value


def _identities(project_id: str, client_key: str) -> tuple[str, str, str, str, str]:
    activation = batch_store._identity('kinodel.image-activation.v1', _uuid(project_id), _key(client_key))
    execution = str(uuid5(NAMESPACE_URL, 'kinodel.image-execution.v1:' + activation))
    group = batch_store._identity('kinodel.image-group.v1', execution, STAGE_ID, activation)
    wait = batch_store._identity('kinodel.image-wait.v1', group)
    work = batch_store._identity('kinodel.image-start-work.v1', execution)
    return activation, execution, group, wait, work


def _receipt(project_id: str, client_key: str, batch: batch_store.BatchInputPinV1) -> ImageStartReceiptV1:
    activation, execution, group, wait, work = _identities(project_id, client_key)
    handoff = batch.prepared_input
    if (handoff.source_plan_ref.project_id != project_id or handoff.activation_id != activation
            or handoff.stage_id != STAGE_ID):
        raise ValueError('Image group source/activation mismatch')
    digest = batch_store._identity('kinodel.image-group-request.v1', project_id, client_key,
        execution, GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST, group, wait, STAGE_ID,
        activation, batch.batch_id, batch.input_digest)
    return ImageStartReceiptV1(execution, work, group, wait, STAGE_ID, activation, digest,
                               batch.batch_id, batch.input_digest)


def _row(db: sqlite3.Connection, execution_id: str):
    return db.execute('SELECT group_id,execution_id,batch_id,wait_id,stage_id,activation_id,request_digest,'
                      'checkpoint_id,task_id,interrupt_id FROM image_groups WHERE execution_id=?',
                      (execution_id,)).fetchone()


def _binding(values) -> None:
    if not all(type(value) is str and 0 < len(value) <= 1024 for value in values):
        raise ValueError('Invalid image wait binding')
    for value in values:
        value.encode('utf-8')


def _story_anchor_receipt(db: sqlite3.Connection, execution_id: str,
                          batch: batch_store.BatchInputPinV1) -> ImageStartReceiptV1:
    """Group receipt reuses the EXISTING Story start work, never image-only identity."""
    from backend.story_start import load_test_story_start
    from backend import story_anchor_start as anchor
    start, _ = load_test_story_start(db, execution_id)
    handoff = batch.prepared_input
    if handoff.source_plan_ref.execution_id != execution_id:
        raise ValueError('Story/anchor group must own its source in the same execution')
    batch_preparation.validate_story_anchor_batch(db, handoff)
    project, client_key, start_digest = db.execute('SELECT project_id,client_key,start_digest FROM executions '
                                                  'WHERE execution_id=?', (execution_id,)).fetchone()
    activation = handoff.activation_id
    group = batch_store._identity('kinodel.image-group.v1', execution_id, STAGE_ID, activation)
    wait = batch_store._identity('kinodel.image-wait.v1', group)
    digest = batch_store._identity('kinodel.story-anchor-group-request.v1', project, client_key, start_digest,
        execution_id, anchor.GRAPH_ID, anchor.GRAPH_VERSION, anchor.GRAPH_DIGEST, group, wait, STAGE_ID,
        activation, batch.batch_id, batch.input_digest)
    return ImageStartReceiptV1(execution_id, start.work_id, group, wait, STAGE_ID, activation, digest,
                               batch.batch_id, batch.input_digest)


def _check_other_resumes(db, receipt, *, anchor):
    from backend.review_store import validate_applied_story_resume
    rows = db.execute("SELECT work_id,execution_id,source_id,resume_ref,payload_digest FROM execution_work "
                      "WHERE execution_id=? AND kind='resume' AND source_id<>?",
                      (receipt.execution_id, receipt.wait_id)).fetchall()
    for work in rows:
        if not anchor:
            raise ValueError('Image-only result has an unrelated resume source')
        validate_applied_story_resume(db, receipt.execution_id, work)


def register_story_anchor_group(db: sqlite3.Connection, execution_id: str,
                                approval_request_id: str) -> ImageStartReceiptV1:
    """Graph-callable idempotent registration ONLY; no new execution/start/provider work.

    Exact source pins publish first. A cancel/OCC race may retain immutable input
    facts, but cannot register an authorized group or allow new native effects.
    """
    batch_store._committed(db)
    _assert_writable(db, execution_id)
    old = _row(db, execution_id)
    if old is not None:
        group = read_image_group(db, execution_id)
        if group.batch.prepared_input.story_approval.approval_request_id != approval_request_id:
            raise ValueError('Story/anchor group approval conflicts with original pins')
        batch_preparation.read_story_anchor_plan(db, execution_id, approval_request_id)
        return group.receipt
    batch = batch_store.pin_active_anchor_batch_input(db, execution_id, approval_request_id)
    receipt = _story_anchor_receipt(db, execution_id, batch)
    with batch_store._transaction(db):
        _assert_writable(db, execution_id)
        if _story_anchor_receipt(db, execution_id, batch) != receipt:
            raise ValueError('Story/anchor source changed before group registration')
        _check_other_resumes(db, receipt, anchor=True)
        db.execute('INSERT INTO image_groups (group_id,execution_id,batch_id,wait_id,stage_id,activation_id,request_digest) '
                   'VALUES (?,?,?,?,?,?,?)', (receipt.group_id, execution_id, receipt.batch_id,
                    receipt.wait_id, STAGE_ID, receipt.activation_id, receipt.request_digest))
    return read_image_group(db, execution_id).receipt


def read_image_group(db: sqlite3.Connection, execution_id: str) -> ImageGroupV1:
    """Exact offline read, including frozen start envelope/work and published files.

    May read cancelled/terminal history. Image-only keeps its frozen envelope;
    Story/anchor additionally validates its current exact committed source. Never
    consult current catalogs or repair missing/corrupt accepted input bytes.
    """
    batch_store._committed(db)
    _uuid(execution_id)
    row = _row(db, execution_id)
    execution = db.execute('SELECT project_id,client_key,input_message,shot_ids,owner_config,start_digest,'
                           'graph_id,graph_version,graph_digest FROM executions WHERE execution_id=?',
                           (execution_id,)).fetchone()
    if row is None or execution is None:
        raise ValueError('Unknown image-only start')
    batch = batch_store.read_batch_input(db, row[2])
    anchor = wardrobe_store.is_story_anchor_graph(execution[6:])
    receipt = (_story_anchor_receipt(db, execution_id, batch) if anchor else
               _receipt(execution[0], execution[1], batch))
    if (row[:7] != (receipt.group_id, receipt.execution_id, receipt.batch_id, receipt.wait_id,
                   STAGE_ID, receipt.activation_id, receipt.request_digest)
            or execution_id != receipt.execution_id
            or (not anchor and execution[2:] != (IMAGE_INPUT_MARKER, '[]', None, receipt.request_digest,
                                                GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST))):
        raise ValueError('Image group/start integrity mismatch')
    work = db.execute("SELECT work_id,source_id,payload_digest,resume_ref FROM execution_work "
                       "WHERE execution_id=? AND kind='start'", (execution_id,)).fetchall()
    if work != [(receipt.work_id, execution_id, execution[5] if anchor else receipt.request_digest, None)]:
        raise ValueError('Image start work integrity mismatch')
    if row[7:] != (None, None, None):
        _binding(row[7:])
    retry = _read_retry_request(db, execution_id)
    if anchor and retry is not None:
        raise ValueError('Story/anchor Retry is not supported')
    _check_other_resumes(db, receipt, anchor=anchor)
    if retry is not None:
        if _retry_row(db, execution_id)[8] != 'accepted':
            raise ValueError('Image Retry acceptance/provenance is incomplete')
        original = batch_store.read_batch_input(db, retry.input_batch_id)
        if (original.input_digest != retry.input_digest or batch.prepared_input.model_dump(exclude={'activation_id'}) !=
                original.prepared_input.model_dump(exclude={'activation_id'})):
            raise ValueError('Image Retry changed original handoff pins')
    return ImageGroupV1(receipt, batch, *row[7:])


def _request(source_plan_ref, image_size, image_profile, connection):
    return (_exact_artifact_ref(ArtifactRef.model_validate(source_plan_ref)),
            MediaSize.model_validate(image_size),
            TypeAdapter(ExactProfilePin).validate_python(image_profile, strict=True),
            BatchConnectionPinV1.model_validate(connection))


def _match(batch: batch_store.BatchInputPinV1, expected) -> None:
    handoff = batch.prepared_input
    if (handoff.source_plan_ref, handoff.image_size, handoff.image_profile, handoff.connection) != expected:
        raise ValueError('Image start request conflicts with original pins')


async def start_image_execution(db: sqlite3.Connection, saver, project_id: str, client_key: str, *,
                               source_plan_ref: ArtifactRef | dict, image_size: MediaSize | dict,
                               image_profile: ExactProfilePin | dict,
                               connection: BatchConnectionPinV1 | dict) -> ImageStartReceiptV1:
    """Publish all source-owned pins BEFORE atomic consumer/group/start acceptance.

    A stable project/key activation also reserves the key's source before any
    visible execution exists: inspect ALL source-owned pins for that activation,
    because batch IDs themselves include the source execution. Abandoned pins are
    fine; changing their source/settings is not. Replays never freshly resolve.
    """
    activation, execution_id, _, _, _ = _identities(project_id, client_key)
    expected = _request(source_plan_ref, image_size, image_profile, connection)
    ref = expected[0]
    if ref.project_id != project_id:
        raise ValueError('Image source belongs to another project')
    await validate_story_storage(db, saver)
    if _retry_row(db, execution_id) is not None:
        raise ValueError('Start client key conflicts with an explicit image Retry')
    old = db.execute('SELECT execution_id,graph_id FROM executions WHERE project_id=? AND client_key=?',
                      (project_id, client_key)).fetchone()
    if old is not None:
        if old != (execution_id, GRAPH_ID):
            raise ValueError('Start client key conflicts with another route')
        group = read_image_group(db, execution_id)
        _match(group.batch, expected)
        return group.receipt
    batch_id = batch_store._identity('kinodel.batch-input.v1', ref.execution_id, STAGE_ID, activation)
    reserved = db.execute('SELECT batch_id FROM batch_input_pins WHERE stage_id=? AND activation_id=?',
                          (STAGE_ID, activation)).fetchall()
    if reserved and reserved != [(batch_id,)]:
        raise ValueError('Image start client key conflicts with reserved source')
    batch = batch_store.pin_saved_batch_input(db, ref.execution_id, source_plan_ref=ref,
        image_size=expected[1], image_profile=expected[2], connection=expected[3], activation_id=activation)
    receipt = _receipt(project_id, client_key, batch)
    with batch_store._transaction(db):
        if _retry_row(db, execution_id) is not None:
            raise ValueError('Start client key conflicts with an explicit image Retry')
        _accept_image_start(db, project_id, client_key, receipt)
    return receipt


def _accept_image_start(db, project_id, client_key, receipt, *, continue_source=None):
    """Transaction-only shared acceptance; identities/envelopes stay byte-exact."""
    reservation = db.execute('SELECT source_execution_id,acceptance_state FROM continue_handoffs '
                            'WHERE consumer_execution_id=?', (receipt.execution_id,)).fetchone()
    if reservation is not None and reservation != (continue_source, 'reserved'):
        raise ValueError('Image start key belongs to a reserved Continue handoff')
    db.execute('INSERT INTO executions (execution_id,project_id,input_message,shot_ids,client_key,start_digest,'
               'graph_id,graph_version,graph_digest,owner_config) VALUES (?,?,?,?,?,?,?,?,?,NULL)',
               (receipt.execution_id, project_id, IMAGE_INPUT_MARKER, '[]', client_key, receipt.request_digest,
                GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST))
    db.execute('INSERT INTO image_groups (group_id,execution_id,batch_id,wait_id,stage_id,activation_id,request_digest) '
               'VALUES (?,?,?,?,?,?,?)', (receipt.group_id, receipt.execution_id, receipt.batch_id,
                receipt.wait_id, STAGE_ID, receipt.activation_id, receipt.request_digest))
    db.execute('INSERT INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,resume_ref,status) '
               "VALUES (?,?,'start',?,?,NULL,'pending')",
               (receipt.work_id, receipt.execution_id, receipt.execution_id, receipt.request_digest))


class ImageRetryRequestV1(DomainModel):
    schema_version: Literal['1']
    execution_id: CanonicalUUID
    project_id: CanonicalUUID
    client_key: str
    predecessor_execution_id: CanonicalUUID
    predecessor_result_id: ExactDigest
    predecessor_result_digest: ExactDigest
    input_batch_id: ExactDigest
    input_digest: ExactDigest


def _retry_row(db, execution_id):
    return db.execute('SELECT execution_id,project_id,client_key,predecessor_execution_id,predecessor_result_id,'
        'input_batch_id,request_digest,body,acceptance_state FROM image_group_retry_requests WHERE execution_id=?',
        (execution_id,)).fetchone()


def _retry_values(request):
    body = canonical_json(request, max_bytes=8192)
    return (request.execution_id, request.project_id, request.client_key, request.predecessor_execution_id,
            request.predecessor_result_id, request.input_batch_id, sha256_digest(body), body.decode('utf-8'))


def _assert_retry_owner(db, request):
    """One reserved/accepted key owns a failed predecessor/result; never choose a branch.

    Used inside both admission transactions and on historical lineage reads. The
    reservation, not an attempt allocation or its eventual acceptance, is the fence.
    """
    owners = db.execute('SELECT execution_id FROM image_group_retry_requests '
        'WHERE predecessor_execution_id=? OR predecessor_result_id=?',
        (request.predecessor_execution_id, request.predecessor_result_id)).fetchall()
    if owners and owners != [(request.execution_id,)]:
        raise ValueError('Image Retry predecessor/result already has a competing reserved or accepted owner')


def _read_retry_request(db, execution_id, seen=None):
    row = _retry_row(db, execution_id)
    if row is None:
        return None
    seen = set() if seen is None else seen
    if execution_id in seen:
        raise ValueError('Image Retry lineage cycle')
    seen.add(execution_id)
    request = ImageRetryRequestV1.model_validate_json(row[7])
    if (row[:8] != _retry_values(request) or row[8] not in ('reserved', 'accepted')
            or request.execution_id != _identities(request.project_id, request.client_key)[1]):
        raise ValueError('Image Retry request identity/body mismatch')
    _assert_retry_owner(db, request)
    parent = _row(db, request.predecessor_execution_id)
    identity = db.execute('SELECT graph_id,graph_version,graph_digest FROM executions WHERE execution_id=?',
                          (request.predecessor_execution_id,)).fetchone()
    if identity != (GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST):
        raise ValueError('Image Retry supports only the exact image-only predecessor route')
    result = db.execute('SELECT group_id,result_digest,status,publication_state FROM image_group_results WHERE result_id=?',
                        (request.predecessor_result_id,)).fetchone()
    if parent is None or result != (parent[0], request.predecessor_result_digest, 'failed', 'published'):
        raise ValueError('Image Retry predecessor is not the exact failed group result')
    previous = _read_retry_request(db, request.predecessor_execution_id, seen)
    root_id = parent[2] if previous is None else previous.input_batch_id
    if (request.input_batch_id != root_id or (previous is not None and
            (request.project_id, request.input_digest) != (previous.project_id, previous.input_digest))):
        raise ValueError('Image Retry changed original input lineage')
    return request


def _assert_retryable(db, execution_id, result_id):
    if db.execute("SELECT 1 FROM execution_controls WHERE execution_id=? AND kind='cancel'", (execution_id,)).fetchone():
        raise ValueError('Cancelled image group cannot authorize Retry')
    outcome = db.execute('SELECT outcome,source_id,subject_artifact_id FROM execution_outcomes WHERE execution_id=?',
                         (execution_id,)).fetchone()
    if outcome is not None and outcome != ('failed', result_id, None):
        raise ValueError('Image Retry conflicts with predecessor terminal outcome')


def _retry_handoff_values(original, activation):
    value = original.prepared_input.model_dump()
    value['activation_id'] = activation
    handoff = type(original.prepared_input).model_validate(value)
    body = canonical_json(handoff)
    digest = sha256_digest(body)
    source = handoff.source_plan_ref
    batch_id = batch_store._identity('kinodel.batch-input.v1', source.execution_id, STAGE_ID, activation)
    uri = batch_store._uri(source.project_id, batch_id, digest)
    return (batch_id, source.execution_id, STAGE_ID, activation, source.artifact_id, digest, body.decode(), uri)


def _pin_retry_handoff(db, original, activation):
    """Publish the already atomic key+handoff reservation, using only original pins."""
    expected = _retry_handoff_values(original, activation)
    batch_id = expected[0]
    row = batch_store._batch_row(db, batch_id)
    if row is None or row[:8] != expected:
        raise ValueError('Image Retry handoff conflicts with original pins')
    if row[8] == 'published':
        return batch_store.read_batch_input(db, batch_id)
    record, frozen_body, path = batch_store._restore_batch(db, row)
    batch_store._publish_body(path, frozen_body)
    with batch_store._transaction(db):
        if batch_store._batch_row(db, batch_id) != row:
            raise ValueError('Image Retry handoff reservation changed')
        db.execute("UPDATE batch_input_pins SET publication_state='published' WHERE batch_id=?", (batch_id,))
    return batch_store.read_batch_input(db, record.batch_id)


async def retry_image_execution(db: sqlite3.Connection, saver, project_id: str, client_key: str, *,
                               predecessor_execution_id: str, expected_result_digest: str) -> ImageStartReceiptV1:
    """Private explicit failed-only Retry. Acceptance allocates NO attempts/effects.

    Reservation fences the key before handoff publication; its accepted marker,
    consumer/group/start and retained-success bindings commit in one transaction.
    The old result/wake/outcome are retained; a failed wake need not have settled.
    """
    from backend import image_group_results as results
    activation, execution_id, _, _, _ = _identities(project_id, client_key)
    _uuid(predecessor_execution_id)
    TypeAdapter(ExactDigest).validate_python(expected_result_digest, strict=True)
    identity = db.execute('SELECT graph_id,graph_version,graph_digest FROM executions WHERE execution_id=?',
                          (predecessor_execution_id,)).fetchone()
    if identity != (GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST):
        raise ValueError('Image Retry is not supported for this route')
    await validate_story_storage(db, saver)
    predecessor = read_image_group(db, predecessor_execution_id)
    result = results.read_image_group_result(db, predecessor_execution_id)
    original = results.read_image_input_batch(db, predecessor_execution_id)
    if (original.prepared_input.source_plan_ref.project_id != project_id or result.digest != expected_result_digest
            or result.status != 'failed'):
        raise ValueError('Image Retry requires the exact same-project failed result')
    request = ImageRetryRequestV1(schema_version='1', execution_id=execution_id, project_id=project_id,
        client_key=client_key, predecessor_execution_id=predecessor_execution_id,
        predecessor_result_id=result.result_id, predecessor_result_digest=result.digest,
        input_batch_id=original.batch_id, input_digest=original.input_digest)
    values = _retry_values(request)
    old = db.execute('SELECT execution_id FROM executions WHERE project_id=? AND client_key=?',
                     (project_id, client_key)).fetchone()
    reservation = _retry_row(db, execution_id)
    if reservation is not None and reservation[:8] != values:
        raise ValueError('Image Retry client key conflicts with predecessor/pins')
    if old is not None:
        if old != (execution_id,) or reservation is None or reservation[8] != 'accepted':
            raise ValueError('Image Retry client key conflicts with another start')
        return read_image_group(db, execution_id).receipt
    snapshot = results._snapshot(db, predecessor)
    handoff_values = _retry_handoff_values(original, activation)
    with batch_store._transaction(db):
        _assert_retryable(db, predecessor_execution_id, result.result_id)
        _assert_retry_owner(db, request)
        results._assert_snapshot(db, predecessor, snapshot)
        if reservation is None:
            if db.execute('SELECT 1 FROM batch_input_pins WHERE stage_id=? AND activation_id=?',
                          (STAGE_ID, activation)).fetchone():
                raise ValueError('Image Retry client key conflicts with an ordinary reserved start')
            db.execute('INSERT INTO image_group_retry_requests VALUES (?,?,?,?,?,?,?,?,?)', (*values, 'reserved'))
            # The existing Story key fence sees batch reservations, not this new
            # private table. Reserve both atomically before any crash/byte I/O.
            db.execute('INSERT INTO batch_input_pins VALUES (?,?,?,?,?,?,?,?,?)', (*handoff_values, 'reserved'))
    batch = _pin_retry_handoff(db, original, activation)
    receipt = _receipt(project_id, client_key, batch)
    with batch_store._transaction(db):
        _assert_retryable(db, predecessor_execution_id, result.result_id)
        _assert_retry_owner(db, request)
        results._assert_snapshot(db, predecessor, snapshot)
        if _retry_row(db, execution_id) != (*values, 'reserved'):
            raise ValueError('Image Retry reservation changed before acceptance')
        _accept_image_start(db, project_id, client_key, receipt)
        for output in result.body.outputs:
            db.execute('INSERT INTO image_unit_attempts VALUES (?,?,?,?,?,?)',
                (receipt.group_id, output.unit_key, output.job_id, output.attempt_id,
                 output.unit_input_digest, output.origin_execution_id))
        db.execute("UPDATE image_group_retry_requests SET acceptance_state='accepted' WHERE execution_id=?",
                   (execution_id,))
    return receipt


def bind_image_wait(db: sqlite3.Connection, execution_id: str, wait_id: str, *, expected_request_digest: str,
                    checkpoint_id: str, task_id: str, interrupt_id: str) -> ImageGroupV1:
    """Worker-only: bind AFTER the durable checkpoint exposes the exact wait token.

    Compare-and-set from the wholly unbound triple. An identical delivery is a
    read-only replay; replacing any bound component is forbidden. No checkpoint
    is created or inspected here, and cancellation/terminal control forbids bind.
    """
    TypeAdapter(ExactDigest).validate_python(expected_request_digest, strict=True)
    _binding((checkpoint_id, task_id, interrupt_id))
    group = read_image_group(db, execution_id)
    if (wait_id, expected_request_digest) != (group.receipt.wait_id, group.receipt.request_digest):
        raise ValueError('Image wait token mismatch')
    with batch_store._transaction(db):
        _assert_writable(db, execution_id)
        row = _row(db, execution_id)
        if row is None or row[3:7] != (wait_id, STAGE_ID, group.receipt.activation_id, expected_request_digest):
            raise ValueError('Image wait changed before binding')
        if row[7:] == (None, None, None):
            changed = db.execute('UPDATE image_groups SET checkpoint_id=?,task_id=?,interrupt_id=? '
                'WHERE execution_id=? AND wait_id=? AND request_digest=? '
                'AND checkpoint_id IS NULL AND task_id IS NULL AND interrupt_id IS NULL',
                (checkpoint_id, task_id, interrupt_id, execution_id, wait_id, expected_request_digest))
            if changed.rowcount != 1:
                raise ValueError('Image wait binding changed concurrently')
        elif row[7:] != (checkpoint_id, task_id, interrupt_id):
            raise ValueError('Image wait binding conflict')
    return read_image_group(db, execution_id)
