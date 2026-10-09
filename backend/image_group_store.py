"""Private image-only admission. Caller owns the data-root lock and open saver.

The source execution still owns the immutable batch input; the new consumer owns
only its accepted group/wait and unique start work. Membership/dependencies live
in that input, never in a second mutable unit list. No graph/provider work here.
"""

from dataclasses import dataclass
import sqlite3
from uuid import NAMESPACE_URL, uuid5

from pydantic import TypeAdapter

from backend import batch_store
from backend.batch_generation import BatchConnectionPinV1
from backend.domain import ArtifactRef, ExactProfilePin, MediaSize, _exact_artifact_ref, sha256_digest
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


def read_image_group(db: sqlite3.Connection, execution_id: str) -> ImageGroupV1:
    """Exact offline read, including frozen start envelope/work and published files.

    May read cancelled/terminal history. Does not re-resolve source authority or
    current catalogs, and never repairs missing/corrupt accepted input bytes.
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
    receipt = _receipt(execution[0], execution[1], batch)
    if (row[:7] != (receipt.group_id, receipt.execution_id, receipt.batch_id, receipt.wait_id,
                   STAGE_ID, receipt.activation_id, receipt.request_digest)
            or execution_id != receipt.execution_id
            or execution[2:] != (IMAGE_INPUT_MARKER, '[]', None, receipt.request_digest,
                                 GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST)):
        raise ValueError('Image group/start integrity mismatch')
    work = db.execute("SELECT work_id,source_id,payload_digest,resume_ref FROM execution_work "
                       "WHERE execution_id=? AND kind='start'", (execution_id,)).fetchall()
    if work != [(receipt.work_id, execution_id, receipt.request_digest, None)]:
        raise ValueError('Image start work integrity mismatch')
    if row[7:] != (None, None, None):
        _binding(row[7:])
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
        db.execute('INSERT INTO executions (execution_id,project_id,input_message,shot_ids,client_key,start_digest,'
                   'graph_id,graph_version,graph_digest,owner_config) VALUES (?,?,?,?,?,?,?,?,?,NULL)',
                   (execution_id, project_id, IMAGE_INPUT_MARKER, '[]', client_key, receipt.request_digest,
                    GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST))
        db.execute('INSERT INTO image_groups (group_id,execution_id,batch_id,wait_id,stage_id,activation_id,request_digest) '
                   'VALUES (?,?,?,?,?,?,?)', (receipt.group_id, execution_id, batch.batch_id,
                    receipt.wait_id, STAGE_ID, activation, receipt.request_digest))
        db.execute('INSERT INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,resume_ref,status) '
                   "VALUES (?,?,'start',?,?,NULL,'pending')",
                   (receipt.work_id, execution_id, execution_id, receipt.request_digest))
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
