"""Private image group storage, not scheduling, provider work or asset approval.

The handoff alone declares membership/order/dependencies. Retry jobs continue to
own the root source-owned INPUT batch, never the new consumer's handoff. Bindings
select exact attempts, not latest. Caller holds the data-root lock; all file/media
validation happens outside short SQL transactions.
"""

from dataclasses import dataclass
import json
import sqlite3
from typing import Annotated, Literal

from pydantic import Field

from backend import batch_store, image_group_store as groups, wardrobe_store
from backend import portrait_candidate_store as candidates, portrait_submission_store as submissions
from backend import render_job_store as jobs
from backend.batch_generation import ParentBindings
from backend.domain import CanonicalUUID, DomainModel, MAX_LIST_ITEMS, canonical_json, sha256_digest
from backend.story_store import _assert_writable, _root
from backend.wardrobe import AnchorKey, ExactDigest


@dataclass(frozen=True)
class ImageUnitAttemptV1:
    unit_key: str
    job_id: str
    attempt_id: str
    unit_input_digest: str
    origin_execution_id: str


class ImageGroupOutputV1(DomainModel):
    unit_key: AnchorKey
    job_id: ExactDigest
    attempt_id: ExactDigest
    unit_input_digest: ExactDigest
    origin_execution_id: CanonicalUUID
    candidate_id: ExactDigest
    candidate_digest: ExactDigest
    candidate_metadata_digest: ExactDigest
    candidate_uri: str
    parent_bindings: ParentBindings


class ImageGroupFailureV1(DomainModel):
    unit_key: AnchorKey
    job_id: ExactDigest
    attempt_id: ExactDigest
    unit_input_digest: ExactDigest
    wire_digest: ExactDigest
    submission_digest: ExactDigest
    revision: submissions.Revision
    reason: submissions.Reason


class ImageGroupResultBodyV1(DomainModel):
    schema_id: Literal['image_group_result']
    schema_version: Literal['1']
    result_id: ExactDigest
    project_id: CanonicalUUID
    execution_id: CanonicalUUID
    group_id: ExactDigest
    wait_id: ExactDigest
    stage_id: Literal['anchor-batch']
    activation_id: ExactDigest
    request_digest: ExactDigest
    batch_id: ExactDigest
    input_digest: ExactDigest
    input_batch_id: ExactDigest
    input_batch_digest: ExactDigest
    status: Literal['complete', 'failed']
    outputs: Annotated[list[ImageGroupOutputV1], Field(max_length=MAX_LIST_ITEMS)]
    failure: ImageGroupFailureV1 | None


@dataclass(frozen=True, repr=False)
class ImageGroupResultV1:
    result_id: str
    digest: str
    uri: str
    status: Literal['complete', 'failed']
    body: ImageGroupResultBodyV1


@dataclass(frozen=True)
class ImageGroupWakeV1:
    work_id: str
    execution_id: str
    source_id: str
    resume_ref: str
    payload_digest: str
    checkpoint_id: str
    task_id: str
    interrupt_id: str


class ImageGroupJoinV1(DomainModel):
    schema_version: Literal['1']
    join_id: ExactDigest
    execution_id: CanonicalUUID
    group_id: ExactDigest
    wait_id: ExactDigest
    request_digest: ExactDigest
    result_id: ExactDigest
    result_digest: ExactDigest
    status: Literal['complete', 'failed']
    batch_outputs: ExactDigest | None


def read_image_input_batch(db: sqlite3.Connection, execution_id: str) -> batch_store.BatchInputPinV1:
    """Exact root per-job input authority; retry handoff owns membership only."""
    group = groups.read_image_group(db, execution_id)
    retry = groups._read_retry_request(db, execution_id)
    return group.batch if retry is None else batch_store.read_batch_input(db, retry.input_batch_id)


def _unit_row(db, group_id, unit_key):
    return db.execute('SELECT unit_key,job_id,attempt_id,unit_input_digest,origin_execution_id '
                      'FROM image_unit_attempts WHERE group_id=? AND unit_key=?', (group_id, unit_key)).fetchone()


def _declared(group, unit_key):
    for index, unit in enumerate(group.batch.prepared_input.ordered_units):
        if unit.unit_key == unit_key:
            return index, unit
    raise ValueError('Unit is not declared by the accepted image handoff')


def _binding_context(db, group):
    retry = groups._read_retry_request(db, group.receipt.execution_id)
    root = group.batch if retry is None else batch_store.read_batch_input(db, retry.input_batch_id)
    predecessor = None if retry is None else read_image_group_result(db, retry.predecessor_execution_id)
    return root, retry, predecessor


def _validate_binding(db, group, binding, context=None):
    _declared(group, binding.unit_key)
    root, retry, predecessor = _binding_context(db, group) if context is None else context
    job = jobs.read_anchor_unit_job(db, binding.job_id, expected_unit_digest=binding.unit_input_digest,
                                   attempt_id=binding.attempt_id)
    intent = json.loads(job.intent_body)
    if (intent['batch_id'], intent['batch_input_digest'], intent['unit_key']) != (
            root.batch_id, root.input_digest, binding.unit_key):
        raise ValueError('Image binding job does not own the original exact unit input')
    initial_id = jobs._initial_attempt_id(binding.job_id, root.batch_id, binding.unit_key)
    if retry is None:
        if (binding.attempt_id, binding.origin_execution_id) != (initial_id, group.receipt.execution_id):
            raise ValueError('Initial image group must select its original initial attempt')
    else:
        assert predecessor is not None and predecessor.body.failure is not None
        retained = next((o for o in predecessor.body.outputs if o.unit_key == binding.unit_key), None)
        if retained is not None:
            if binding != ImageUnitAttemptV1(retained.unit_key, retained.job_id, retained.attempt_id,
                                             retained.unit_input_digest, retained.origin_execution_id):
                raise ValueError('Image Retry cannot replace or re-own a retained successful attempt')
        elif binding.origin_execution_id != group.receipt.execution_id:
            raise ValueError('New image attempt is not owned by its accepting consumer')
        elif predecessor.body.failure.unit_key == binding.unit_key:
            allocation = jobs._allocation_row(db, binding.attempt_id)
            if allocation is None or (allocation[1], allocation[2], allocation[3]) != (
                    binding.job_id, predecessor.body.failure.attempt_id, group.receipt.group_id):
                raise ValueError('Image Retry failed unit lacks its exact explicit group-triggered allocation')
        elif binding.attempt_id != initial_id:
            raise ValueError('Unstarted Retry unit must select its original initial attempt')
    return job


def read_image_unit_attempt(db: sqlite3.Connection, execution_id: str, unit_key: str) -> ImageUnitAttemptV1:
    """Exact offline history, including cancelled consumers and retained successes."""
    group = groups.read_image_group(db, execution_id)
    _declared(group, unit_key)
    row = _unit_row(db, group.receipt.group_id, unit_key)
    if row is None:
        raise LookupError('Image unit has no selected attempt')
    binding = ImageUnitAttemptV1(*row)
    _validate_binding(db, group, binding)
    return binding


def _facts(db, binding):
    row = submissions._row(db, binding.job_id, binding.attempt_id)
    if row is None:
        raise ValueError('Image unit attempt has no durable submission facts')
    record = submissions.read_anchor_unit_submission(db, binding.job_id, attempt_id=binding.attempt_id,
        expected_unit_digest=binding.unit_input_digest, expected_wire_digest=row[2])
    return record, row


def is_terminal_image_failure(record: submissions.PortraitSubmissionV1) -> bool:
    """Classify exact validated native facts, not a terminal-looking state/reason.

    A sent local failure remains uncertain. Only the native owner's owned history
    failure receipt proves terminal provider failure; its hash is an assertion by
    that trusted owner, not permission to infer completion from deadline or absence.
    Callers load/revalidate the exact job/attempt/wire facts before this predicate.
    """
    if record.state != 'failed':
        return False
    if record.dispatched_at_ms is None:
        return record.reason == 'deadline_exceeded' and record.prompt_id is None
    proof = record.evidence
    return (record.reason == 'provider_failed' and record.prompt_id is not None
            and record.acceptance_evidence is not None and proof is not None and proof.kind == 'history'
            and (proof.prompt_id, proof.wire_digest, proof.endpoint_digest) ==
                (record.prompt_id, record.preview.wire_digest, record.preview.endpoint_digest))


def _output(db, binding, job):
    record, _ = _facts(db, binding)
    if record.state != 'completed':
        raise ValueError('Image unit is not the exact completed attempt')
    assert record.candidate_id is not None
    candidate = candidates.read_anchor_unit_candidate(db, record.candidate_id,
                                                      expected_unit_digest=binding.unit_input_digest)
    if (candidate.job_id, candidate.attempt_id, candidate.intent_digest) != (
            binding.job_id, binding.attempt_id, job.intent_digest):
        raise ValueError('Image candidate is foreign or stale for the exact selected attempt')
    return ImageGroupOutputV1(unit_key=binding.unit_key, job_id=binding.job_id, attempt_id=binding.attempt_id,
        unit_input_digest=binding.unit_input_digest, origin_execution_id=binding.origin_execution_id,
        candidate_id=candidate.candidate_id, candidate_digest=candidate.digest,
        candidate_metadata_digest=sha256_digest(candidate.metadata_body), candidate_uri=candidate.uri,
        parent_bindings=job.prepared_input.parent_bindings)


def _validate_parents(planned, job, outputs):
    parents = job.prepared_input.parent_bindings
    if len(parents) != len(planned.references):
        raise ValueError('Image unit dependency coverage mismatch')
    for ref, parent in zip(planned.references, parents, strict=True):
        expected = next((o for o in outputs if o.unit_key == ref.source.unit_key), None)
        if expected is None or (parent.unit_key, parent.source_id, parent.digest) != (
                ref.source.unit_key, expected.candidate_id, expected.candidate_digest):
            raise ValueError('Image unit parent is not the exact earlier completed group candidate')


def _assert_group_mutable(db, group):
    _assert_writable(db, group.receipt.execution_id)
    if db.execute('SELECT 1 FROM image_group_results WHERE group_id=?', (group.receipt.group_id,)).fetchone():
        raise ValueError('Image group terminal result is already reserved or published')


def bind_image_unit_attempt(db: sqlite3.Connection, execution_id: str, unit_key: str, *,
        expected_request_digest: str, expected_unit_digest: str, job_id: str, attempt_id: str) -> ImageUnitAttemptV1:
    """Immutable insert/CAS on the actual sequential turn; never allocate or submit."""
    group = groups.read_image_group(db, execution_id)
    if expected_request_digest != group.receipt.request_digest:
        raise ValueError('Image unit binding request mismatch')
    index, planned = _declared(group, unit_key)
    old = _unit_row(db, group.receipt.group_id, unit_key)
    if old is not None:
        binding = read_image_unit_attempt(db, execution_id, unit_key)
        if (binding.job_id, binding.attempt_id, binding.unit_input_digest) != (job_id, attempt_id, expected_unit_digest):
            raise ValueError('Image unit attempt binding is immutable')
        return binding
    snapshot = _snapshot(db, group)
    context = _binding_context(db, group)
    binding = ImageUnitAttemptV1(unit_key, job_id, attempt_id, expected_unit_digest, execution_id)
    job = _validate_binding(db, group, binding, context)
    outputs = []
    for earlier in group.batch.prepared_input.ordered_units[:index]:
        row = _unit_row(db, group.receipt.group_id, earlier.unit_key)
        if row is None:
            raise ValueError('Earlier image unit has no selected completed attempt')
        previous = ImageUnitAttemptV1(*row)
        outputs.append(_output(db, previous, _validate_binding(db, group, previous, context)))
    _validate_parents(planned, job, outputs)
    with batch_store._transaction(db):
        _assert_group_mutable(db, group)
        _assert_snapshot(db, group, snapshot)
        db.execute('INSERT INTO image_unit_attempts VALUES (?,?,?,?,?,?)',
                   (group.receipt.group_id, unit_key, job_id, attempt_id, expected_unit_digest, execution_id))
    return binding


def assert_image_attempt_writable(db: sqlite3.Connection, job_id: str, attempt_id: str) -> None:
    """SQL-only native-effects guard, usable INSIDE the native mutation transaction.

    Requires a group binding before effects and checks the origin consumer rather
    than the completed source text execution. Retained successes are not re-owned.
    Native callers still validate their own exact job/input/submission selectors.
    """
    origins = db.execute('SELECT DISTINCT origin_execution_id FROM image_unit_attempts WHERE job_id=? AND attempt_id=?',
                         (job_id, attempt_id)).fetchall()
    if len(origins) != 1:
        raise ValueError('Image attempt lacks its unique accepting consumer')
    origin = origins[0][0]
    _assert_writable(db, origin)
    if db.execute('SELECT 1 FROM image_group_results r JOIN image_groups g ON r.group_id=g.group_id '
                  'WHERE g.execution_id=?', (origin,)).fetchone():
        raise ValueError('Terminal image group cannot authorize late native effects')


def _snapshot(db, group):
    """SQL-only OCC facts; no transaction covers offline file/media validation."""
    retry = groups._retry_row(db, group.receipt.execution_id)
    root_id = group.batch.batch_id if retry is None else retry[5]
    execution = group.receipt.execution_id
    identity = db.execute('SELECT graph_id,graph_version,graph_digest FROM executions WHERE execution_id=?',
                          (execution,)).fetchone()
    # This route's source remains active in the SAME execution. Recheck the exact
    # authority validated before file/media I/O, not only unit/result/work facts.
    source = tuple(db.execute(f'SELECT * FROM {table} WHERE execution_id=? ORDER BY rowid',
                              (execution,)).fetchall() for table in
                   ('executions', 'execution_bindings', 'review_requests', 'wardrobe_operations',
                    'story_operations', 'artifacts')) if wardrobe_store.is_story_anchor_graph(identity) else ()
    return (
        groups._row(db, group.receipt.execution_id), retry,
        db.execute('SELECT * FROM image_unit_attempts WHERE group_id=? ORDER BY unit_key', (group.receipt.group_id,)).fetchall(),
        batch_store._batch_row(db, group.batch.batch_id), batch_store._batch_row(db, root_id),
        db.execute('SELECT * FROM batch_unit_input_pins WHERE batch_id=? ORDER BY unit_key', (root_id,)).fetchall(),
        db.execute('SELECT * FROM render_jobs WHERE batch_id=? ORDER BY job_id', (root_id,)).fetchall(),
        *(db.execute(f'SELECT t.* FROM {table} t JOIN render_jobs j ON t.job_id=j.job_id '
                     'WHERE j.batch_id=? ORDER BY t.attempt_id', (root_id,)).fetchall()
          for table in ('render_submission_attempts', 'render_retry_allocations', 'portrait_submissions',
                        'portrait_candidates', 'anchor_reference_transfers')),
        db.execute('SELECT * FROM image_group_results WHERE group_id=?', (group.receipt.group_id,)).fetchone(),
        db.execute("SELECT work_id,execution_id,kind,source_id,resume_ref,payload_digest FROM execution_work "
                   "WHERE execution_id=? AND kind IN ('start','resume') ORDER BY kind,source_id",
                    (group.receipt.execution_id,)).fetchall(),
        source,
    )


def _assert_snapshot(db, group, snapshot):
    if _snapshot(db, group) != snapshot:
        raise ValueError('Image group/input/attempt/result facts changed before commit')


def _build_result(db, group, status, failed_unit_key):
    context = _binding_context(db, group)
    root = context[0]
    outputs = []
    failure = None
    declared = group.batch.prepared_input.ordered_units
    selected = db.execute('SELECT unit_key FROM image_unit_attempts WHERE group_id=?',
                           (group.receipt.group_id,)).fetchall()
    if any(key not in {u.unit_key for u in declared} for (key,) in selected):
        raise ValueError('Image group has an undeclared unit binding')
    for index, planned in enumerate(declared):
        row = _unit_row(db, group.receipt.group_id, planned.unit_key)
        if row is None:
            raise ValueError('Unfinished image declaration cannot publish a terminal complete set')
        binding = ImageUnitAttemptV1(*row)
        job = _validate_binding(db, group, binding, context)
        _validate_parents(planned, job, outputs)
        if status == 'failed' and planned.unit_key == failed_unit_key:
            record, row = _facts(db, binding)
            if not is_terminal_image_failure(record):
                raise ValueError('Image group failure requires an unsent failure or owned native terminal failure proof')
            if len(selected) != index + 1:
                raise ValueError('Failed image group has later selected attempts')
            failure = ImageGroupFailureV1(unit_key=planned.unit_key, job_id=binding.job_id, attempt_id=binding.attempt_id,
                unit_input_digest=binding.unit_input_digest, wire_digest=row[2], submission_digest=row[3],
                revision=record.revision, reason=record.reason)
            break
        outputs.append(_output(db, binding, job))
    if status == 'complete':
        if failed_unit_key is not None or len(outputs) != len(declared) or len(selected) != len(declared):
            raise ValueError('Image manifest must cover the exact full declaration in order')
    elif status != 'failed' or failure is None:
        raise ValueError('Image group failure must identify its exact terminal failed unit')
    receipt = group.receipt
    result_id = batch_store._identity('kinodel.image-group-result.v1', receipt.group_id, receipt.wait_id)
    return ImageGroupResultBodyV1(schema_id='image_group_result', schema_version='1', result_id=result_id,
        project_id=root.prepared_input.source_plan_ref.project_id, execution_id=receipt.execution_id,
        group_id=receipt.group_id, wait_id=receipt.wait_id, stage_id=receipt.stage_id,
        activation_id=receipt.activation_id, request_digest=receipt.request_digest,
        batch_id=receipt.batch_id, input_digest=receipt.input_digest, input_batch_id=root.batch_id,
        input_batch_digest=root.input_digest, status=status, outputs=outputs, failure=failure)


def _result_row(db, group_id):
    return db.execute('SELECT result_id,group_id,result_digest,status,body,uri,publication_state '
                      'FROM image_group_results WHERE group_id=?', (group_id,)).fetchone()


def _result_values(body):
    raw = canonical_json(body)
    digest = sha256_digest(raw)
    uri = batch_store._uri(body.project_id, body.result_id, digest).replace('/inputs/', '/image-results/')
    return (body.result_id, body.group_id, digest, body.status, raw.decode('utf-8'), uri)


def _restore_result(db, group, row):
    raw = batch_store._body(row[4])
    body = ImageGroupResultBodyV1.model_validate_json(raw)
    if (row[:6] != _result_values(body) or row[6] not in ('reserved', 'published') or body !=
            _build_result(db, group, body.status, None if body.failure is None else body.failure.unit_key)):
        raise ValueError('Image group result identity/body/complete-set lineage mismatch')
    return ImageGroupResultV1(body.result_id, row[2], row[5], body.status, body)


def _wake_values(group, result):
    receipt = group.receipt
    work_id = batch_store._identity('kinodel.image-group-wake.v1', receipt.group_id, receipt.wait_id)
    return (work_id, receipt.execution_id, receipt.wait_id, result.result_id, result.digest)


def _check_wake(db, group, result):
    rows = db.execute("SELECT work_id,execution_id,source_id,resume_ref,payload_digest FROM execution_work "
                      "WHERE execution_id=? AND kind='resume' AND source_id=?",
                      (group.receipt.execution_id, group.receipt.wait_id)).fetchall()
    if rows != [_wake_values(group, result)]:
        raise ValueError('Image result/wake is missing, conflicting or belongs to another wait')


def read_image_group_result(db: sqlite3.Connection, execution_id: str) -> ImageGroupResultV1:
    """Offline immutable terminal result, revalidating exact candidates/dependencies."""
    group = groups.read_image_group(db, execution_id)
    row = _result_row(db, group.receipt.group_id)
    if row is None or row[6] != 'published':
        raise LookupError('Image group terminal result is not published')
    result = _restore_result(db, group, row)
    if batch_store._read_file(_root(db) / result.uri.removeprefix('kinodel://')) != row[4].encode('utf-8'):
        raise ValueError('Image result managed file/body mismatch')
    _check_wake(db, group, result)
    return result


def publish_image_group_result(db: sqlite3.Connection, execution_id: str, *, expected_request_digest: str,
        status: Literal['complete', 'failed'], failed_unit_key: str | None = None) -> ImageGroupResultV1:
    """Reservation -> immutable bytes -> atomic visible result + unique exact wake.

    Result is also the private complete manifest when status=complete. Publication
    does NOT complete the consumer and cannot publish partial approval or assets.
    Exact duplicates are read-only history; reserved recovery never resubmits.
    """
    group = groups.read_image_group(db, execution_id)
    if expected_request_digest != group.receipt.request_digest:
        raise ValueError('Image result request digest mismatch')
    snapshot = _snapshot(db, group)
    body = _build_result(db, group, status, failed_unit_key)
    values = _result_values(body)
    row = _result_row(db, group.receipt.group_id)
    if row is not None:
        if row[:6] != values:
            raise ValueError('Image group terminal result is immutable')
        if row[6] == 'published':
            return read_image_group_result(db, execution_id)
    else:
        with batch_store._transaction(db):
            _assert_group_mutable(db, group)
            _assert_snapshot(db, group, snapshot)
            db.execute('INSERT INTO image_group_results VALUES (?,?,?,?,?,?,?)', (*values, 'reserved'))
        row = _result_row(db, group.receipt.group_id)
    snapshot = _snapshot(db, group)
    result = _restore_result(db, group, row)
    batch_store._publish_body(_root(db) / result.uri.removeprefix('kinodel://'), row[4].encode('utf-8'))
    _restore_result(db, group, row)  # Revalidate inputs/candidates after publication, still outside SQL transaction.
    with batch_store._transaction(db):
        _assert_writable(db, execution_id)
        _assert_snapshot(db, group, snapshot)
        db.execute("UPDATE image_group_results SET publication_state='published' WHERE group_id=?", (group.receipt.group_id,))
        work, execution, wait, ref, digest = _wake_values(group, result)
        db.execute('INSERT INTO execution_work (work_id,execution_id,kind,source_id,resume_ref,payload_digest,status) '
                   "VALUES (?,?,'resume',?,?,?,'pending')", (work, execution, wait, ref, digest))
    return read_image_group_result(db, execution_id)


def read_image_group_wake(db: sqlite3.Connection, execution_id: str) -> ImageGroupWakeV1 | None:
    """Early results are durable but undeliverable until the exact wait is bound.

    Caller must independently inspect that checkpoint/task/interrupt before native
    LangGraph resume; storage never inspects or mutates checkpointer state.
    """
    group = groups.read_image_group(db, execution_id)
    row = _result_row(db, group.receipt.group_id)
    if row is None or row[6] != 'published':
        return None
    result = read_image_group_result(db, execution_id)
    if group.checkpoint_id is None:
        return None
    assert group.task_id is not None and group.interrupt_id is not None
    return ImageGroupWakeV1(*_wake_values(group, result), group.checkpoint_id, group.task_id, group.interrupt_id)


def join_image_group_result(db: sqlite3.Connection, execution_id: str, *, wait_id: str, result_id: str,
        expected_result_digest: str, expected_request_digest: str) -> ImageGroupJoinV1:
    """Graph-owned offline exact join; immutable receipt + terminal outcome atomically.

    Complete manifest is a technical output ref, never approved/selected media.
    A failed result yields failed consumer, no batch_outputs. Old wake cannot join
    any other group's wait or a human review. Replayed receipt performs no writes.
    """
    group = groups.read_image_group(db, execution_id)
    snapshot = _snapshot(db, group)
    result = read_image_group_result(db, execution_id)
    if ((wait_id, expected_request_digest, result_id, expected_result_digest) !=
            (group.receipt.wait_id, group.receipt.request_digest, result.result_id, result.digest)
            or group.checkpoint_id is None):
        raise ValueError('Image join requires its exact bound wait/result/request')
    join = ImageGroupJoinV1(schema_version='1', join_id=batch_store._identity('kinodel.image-group-join.v1',
        group.receipt.group_id, wait_id, result_id, result.digest), execution_id=execution_id,
        group_id=group.receipt.group_id, wait_id=wait_id, request_digest=expected_request_digest,
        result_id=result_id, result_digest=result.digest, status=result.status,
        batch_outputs=result_id if result.status == 'complete' else None)
    raw = canonical_json(join)
    values = (group.receipt.group_id, result_id, sha256_digest(raw), raw.decode('utf-8'))
    old = db.execute('SELECT * FROM image_group_joins WHERE group_id=?', (group.receipt.group_id,)).fetchone()
    outcome = ('completed' if result.status == 'complete' else 'failed', result_id, None)
    if old is not None:
        if old != values or db.execute('SELECT outcome,source_id,subject_artifact_id FROM execution_outcomes '
            'WHERE execution_id=?', (execution_id,)).fetchone() != outcome:
            raise ValueError('Image join receipt/outcome conflicts with exact result')
        return join
    with batch_store._transaction(db):
        _assert_writable(db, execution_id)
        _assert_snapshot(db, group, snapshot)
        _check_wake(db, group, result)
        db.execute('INSERT INTO image_group_joins VALUES (?,?,?,?)', values)
        db.execute('INSERT INTO execution_outcomes VALUES (?,?,?,?)', (execution_id, *outcome))
    return join
