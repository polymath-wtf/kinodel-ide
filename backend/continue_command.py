"""Concrete Continue policy/admission for the existing Story and image runtimes.

No invocation, retry budget allocation or provider I/O. A Continue-owned bridge
reserves its exact source AND full batch pins atomically, before saver awaits or
file publication. Private new runs and explicit image Retry remain independent.
"""

import json
import sqlite3
from typing import Annotated, Literal

from pydantic import AfterValidator, Field

from backend import batch_preparation, batch_store, config, image_group_store as images, wardrobe_store
from backend.batch_generation import BatchConnectionPinV1
from backend.domain import (ArtifactRef, CanonicalUUID, Digest, DomainModel, ExactProfilePin, MediaSize,
                            Text, _exact_artifact_ref, canonical_json, sha256_digest)
from backend.story_start import STORY_GRAPH_IDS, load_test_story_start, reject_retired_wardrobe, validate_story_storage
from backend.story_store import _uuid


Action = Literal['start_images', 'resume', 'open', 'review', 'resolve', 'finished']
Status = Literal['created', 'running', 'waiting_review', 'waiting_job', 'blocked', 'cancelling',
                 'completed', 'cancelled', 'failed']
Resolution = Literal['continue', 'approve', 'revise', 'clarify', 'retry', 'cancel', 'new_run', 'diagnose',
                     'recover_provider']
Reason = Literal['completed', 'cancelled', 'failed', 'cancelling', 'production_intent_required',
    'explicit_decision_required', 'external_work', 'integrity_block', 'attempt_budget_exhausted',
    'owner_unavailable', 'wardrobe_unavailable', 'wardrobe_exhausted', 'wardrobe_invalid_output',
    'wardrobe_invalid', 'wardrobe_needs_input', 'wardrobe_out_of_scope', 'acceptance_unknown',
    'contract_error', 'deadline_exceeded', 'output_invalid', 'history_unavailable', 'provider_failed',
    'reference_unavailable', 'reference_contract_error']


class ContinueProductionIntent(DomainModel):
    source_plan_ref: Annotated[ArtifactRef, AfterValidator(_exact_artifact_ref)]
    image_size: MediaSize
    image_profile: ExactProfilePin
    connection: BatchConnectionPinV1


class ContinueRequest(DomainModel):
    command_key: Annotated[Text, Field(max_length=128)]
    expected_token: Digest
    production_intent: ContinueProductionIntent | None = None


class ContinueReview(DomainModel):
    request_id: Digest
    digest: Digest
    revision: int
    binding_revision: int
    subject_artifact_id: CanonicalUUID


class ImageProgress(DomainModel):
    completed: int = Field(ge=0)
    total: int = Field(ge=1)


class ContinueProductionSettings(DomainModel):
    image_size: MediaSize
    image_profile: ExactProfilePin
    connection: Literal['local', 'server']


class ContinueProjection(DomainModel):
    schema_version: Literal['1'] = '1'
    selected_execution_id: CanonicalUUID
    source_execution_id: CanonicalUUID
    effective_execution_id: CanonicalUUID
    project_id: CanonicalUUID
    status: Status
    action: Action
    reason: Reason | None
    allowed_actions: list[Resolution]
    occ_token: Digest
    work_id: str | None = None
    group_id: Digest | None = None
    review: ContinueReview | None = None
    source_plan_ref: ArtifactRef | None = None
    image_progress: ImageProgress | None = None
    production: ContinueProductionSettings | None = None


class ContinueReceipt(ContinueProjection):
    command_key: Text
    expected_token: Digest
    disposition: Action


def _records(db, execution):
    """Private fingerprint, not a public projection. Include authority and budgets."""
    return [db.execute('SELECT * FROM ' + table + ' WHERE execution_id=? ORDER BY rowid', (execution,)).fetchall()
            for table in ('executions', 'execution_outcomes', 'execution_controls', 'execution_work',
                          'execution_bindings', 'review_requests', 'story_operations', 'wardrobe_operations')]


def _source_token(db, execution):
    return _fingerprint(_records(db, execution))


def _fingerprint(value):
    return sha256_digest(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode())


def _handoff(db, execution):
    row = db.execute('SELECT source_execution_id,source_token,expected_token,intent_digest,intent_body,'
        'consumer_execution_id,consumer_key,batch_id,acceptance_state FROM continue_handoffs '
        'WHERE source_execution_id=?', (execution,)).fetchone()
    if row:
        intent = ContinueProductionIntent.model_validate_json(row[4])
        key = 'continue:' + batch_store._identity('kinodel.continue-handoff.v1', execution)[7:]
        activation, consumer, _, _, _ = images._identities(intent.source_plan_ref.project_id, key)
        batch_id = batch_store._identity('kinodel.batch-input.v1', execution, images.STAGE_ID, activation)
        if (intent.source_plan_ref.execution_id != execution or canonical_json(intent).decode() != row[4]
                or sha256_digest(row[4].encode()) != row[3] or row[5:8] != (consumer, key, batch_id)):
            raise ValueError('Continue handoff reservation identity/pins mismatch')
    return row


def _resolve(db, selected):
    _uuid(selected)
    reject_retired_wardrobe(db, selected)
    row = db.execute('SELECT project_id,graph_id,graph_version,graph_digest FROM executions WHERE execution_id=?',
                     (selected,)).fetchone()
    if row is None:
        raise LookupError('Unknown selected execution')
    if row[1] not in (*STORY_GRAPH_IDS, images.GRAPH_ID):
        raise ValueError('Unsupported selected process')
    effective, source = selected, selected
    link = _handoff(db, selected)
    if link and link[8] == 'accepted':
        effective = link[5]
    if row[1] == images.GRAPH_ID:
        batch = db.execute('SELECT b.body FROM image_groups g JOIN batch_input_pins b ON b.batch_id=g.batch_id '
                           'WHERE g.execution_id=?', (selected,)).fetchone()
        if batch is None:
            raise ValueError('Image process has no accepted group')
        source = json.loads(batch[0])['source_plan_ref']['execution_id']
    seen = set()
    while True:
        if effective in seen:
            raise ValueError('Continue lineage cycle')
        seen.add(effective)
        successors = db.execute("SELECT execution_id FROM image_group_retry_requests "
            "WHERE predecessor_execution_id=? AND acceptance_state='accepted'", (effective,)).fetchall()
        if len(successors) > 1:
            raise ValueError('Ambiguous Continue Retry lineage')
        if not successors:
            break
        effective = successors[0][0]
        images._read_retry_request(db, effective)  # Existing exact Retry validator, never timestamp lookup.
    return source, effective, row[0]


def _safe_reason(reason):
    return reason if reason in {'owner_unavailable', 'wardrobe_unavailable', 'wardrobe_exhausted',
        'wardrobe_invalid_output', 'wardrobe_invalid', 'wardrobe_needs_input', 'wardrobe_out_of_scope',
        'acceptance_unknown', 'contract_error', 'deadline_exceeded', 'output_invalid', 'history_unavailable', 'provider_failed',
        'reference_unavailable', 'reference_contract_error'} else 'integrity_block'


def _policy(db, selected, checkpoint_id=None, runnable=None, *, active_work_ids=None):
    """One concrete allowed-action policy used by projection AND command admission."""
    from backend.story_reads import _overview, _ref, _rows
    source, effective, project = _resolve(db, selected)
    overview = _overview(db, effective)
    outcome, work, review = overview['outcome'], overview['work'], overview['review']
    live = [w for w in work if w['status'] in ('pending', 'claimed')]
    # Counters reserve before HTTP: the final authorized attempt can be in flight.
    # Only exact process-local ownership proves this; abandoned claimed rows do not.
    running_reserved = any(w['status'] == 'claimed' and w['work_id'] in (active_work_ids or ()) for w in live)
    blocked = [w for w in work if w['status'] in ('blocked', 'failed')]
    image = db.execute('SELECT group_id,batch_id,checkpoint_id FROM image_groups WHERE execution_id=?',
                       (effective,)).fetchone()
    group_id, progress, ref, production = None, None, None, None
    image_facts = []
    if image:
        group_id = image[0]
        batch = db.execute('SELECT body FROM batch_input_pins WHERE batch_id=?', (image[1],)).fetchone()
        handoff = json.loads(batch[0])
        ref = handoff['source_plan_ref']
        production = ContinueProductionSettings(image_size=handoff['image_size'], image_profile=handoff['image_profile'],
                                                connection=handoff['connection']['connection'])
        total = len(handoff['ordered_units'])
        image_facts = db.execute('SELECT u.unit_key,s.state,s.revision,s.submission_digest,s.submission_body '
            'FROM image_unit_attempts u LEFT JOIN portrait_submissions s ON s.attempt_id=u.attempt_id '
            'WHERE u.group_id=? ORDER BY u.unit_key', (group_id,)).fetchall()
        progress = ImageProgress(completed=sum(r[1] == 'completed' for r in image_facts), total=total)
    references = db.execute('SELECT r.state,r.record_digest,r.record_body FROM image_unit_attempts u '
        'JOIN anchor_reference_transfers r ON r.attempt_id=u.attempt_id WHERE u.group_id=? ORDER BY u.unit_key',
        (group_id,)).fetchall() if image else []
    exhausted = bool(db.execute('SELECT 1 FROM story_operations WHERE execution_id=? AND artifact_id IS NULL '
        'AND owner_response IS NULL AND owner_request IS NOT NULL AND owner_attempts>=owner_budget', (effective,)).fetchone()
        or db.execute('SELECT 1 FROM wardrobe_operations WHERE execution_id=? AND candidate_body IS NULL '
        'AND owner_attempts>=2', (effective,)).fetchone())
    action, reason, allowed, work_id = 'resolve', 'integrity_block', ['diagnose'], None
    status = overview['status']
    if outcome:
        reason = outcome['outcome']
        action, allowed = ('finished', []) if reason == 'completed' else ('resolve', ['new_run'])
        if reason == 'completed' and effective == source and not db.execute(
                "SELECT 1 FROM execution_controls WHERE execution_id=? AND kind='cancel'", (source,)).fetchone():
            graph = db.execute('SELECT graph_id,graph_version,graph_digest FROM executions WHERE execution_id=?',
                               (source,)).fetchone()
            if graph == (wardrobe_store.GRAPH_ID, wardrobe_store.GRAPH_VERSION, wardrobe_store.GRAPH_DIGEST):
                plans = _rows(db, "SELECT a.* FROM execution_bindings b JOIN artifacts a ON a.artifact_id=b.artifact_id "
                    "AND a.execution_id=b.execution_id WHERE b.execution_id=? AND b.slot='wardrobe_plan'", (source,))
                if len(plans) == 1 and (plans[0]['operation_id'], plans[0]['artifact_id']) == (
                        outcome['source_id'], outcome['subject_artifact_id']) and (
                        plans[0]['schema_id'], plans[0]['schema_version'], plans[0]['produced_by_stage']) == (
                        'visual_anchor_plan', '2', 'wardrobe'):
                    ref = _ref(plans[0], project, source)
                    action, reason, allowed = 'start_images', 'production_intent_required', ['continue']
        if reason == 'failed' and image and db.execute("SELECT 1 FROM image_group_results WHERE group_id=? "
                "AND status='failed' AND publication_state='published'", (group_id,)).fetchone():
            allowed = ['retry', 'new_run']
    elif status == 'cancelling':
        reason, allowed = 'cancelling', []
    elif blocked or (exhausted and not running_reserved):
        status = 'blocked'
        reason = _safe_reason(blocked[0]['blocked_reason']) if blocked else 'attempt_budget_exhausted'
        allowed = ['cancel', 'new_run']
        if blocked:
            work_id = blocked[0]['work_id']
            if blocked[0]['status'] == 'blocked' and (reason == 'owner_unavailable' or (
                    reason == 'wardrobe_unavailable' and not exhausted)):
                allowed.insert(0, 'retry')
        if image:
            allowed = ['diagnose', 'cancel']
    elif live:
        status = 'created' if all(w['kind'] == 'start' and w['status'] == 'pending' for w in live) else 'running'
        action, reason, allowed, work_id = 'open', None, ['continue', 'cancel'], live[0]['work_id']
    elif review:
        status, action, reason, allowed = 'waiting_review', 'review', 'explicit_decision_required', ['approve', 'cancel']
        from backend.review_store import REVIEW_ACTION_LIMIT
        for choice in ('revise', 'clarify'):
            if db.execute('SELECT COUNT(*) FROM review_requests WHERE execution_id=? AND action=?',
                          (effective, choice)).fetchone()[0] < REVIEW_ACTION_LIMIT:
                allowed.insert(-1, choice)
    elif image:
        stops = [json.loads(r[4]).get('reason') for r in image_facts if r[1] in ('blocked', 'failed')]
        if any(r[0] == 'blocked' for r in references):
            stops.append('reference_unavailable')
        if stops:
            status, reason, allowed = 'blocked', _safe_reason(stops[0]), ['recover_provider', 'cancel']
        elif runnable:
            status, action, reason, allowed = 'running', 'resume', None, ['continue', 'cancel']
        elif image[2] is None or checkpoint_id is None:
            status, reason, allowed = 'blocked', 'integrity_block', ['diagnose', 'cancel']
        else:
            status, action, reason, allowed = 'waiting_job', 'open', 'external_work', ['continue', 'cancel']
    elif runnable:
        status, action, reason, allowed = 'running', 'resume', None, ['continue', 'cancel']
    else:
        status, allowed = 'blocked', ['diagnose', 'cancel']
    handoff = _handoff(db, source)
    # Reservation does not advance the selected process or its source OCC token.
    # All delivery keys at that same saved point can finish the one reserved transition.
    fingerprint = [_records(db, source), _records(db, effective), handoff if handoff and handoff[8] == 'accepted' else None, checkpoint_id,
                   running_reserved, image, image_facts, references, db.execute('SELECT * FROM image_group_results WHERE group_id=?',
                                                (group_id,)).fetchall() if image else []]
    return ContinueProjection(selected_execution_id=selected, source_execution_id=source,
        effective_execution_id=effective, project_id=project, status=status, action=action, reason=reason,
        allowed_actions=allowed, occ_token=_fingerprint(fingerprint), work_id=work_id,
        group_id=group_id, review=review, source_plan_ref=ref, image_progress=progress, production=production)


async def _inspect(db, saver, selected, *, refreshed=False):
    """Read checkpoints only. Runner retains all resume/delivery/validation ownership."""
    _, effective, _ = _resolve(db, selected)
    if db.execute('SELECT 1 FROM image_groups WHERE execution_id=?', (effective,)).fetchone():
        group = images.read_image_group(db, effective)
    else:
        group = None
        load_test_story_start(db, effective)
    saved = await saver.aget_tuple({'configurable': {'thread_id': effective}})
    checkpoint = saved.config['configurable']['checkpoint_id'] if saved else None
    runnable = False
    # Only a stopped text segment needs framework task classification here.
    if saved and not db.execute('SELECT 1 FROM image_groups WHERE execution_id=?', (effective,)).fetchone():
        if not db.execute('SELECT 1 FROM execution_outcomes WHERE execution_id=?', (effective,)).fetchone():
            from backend.story_graph import build_story_graph
            wardrobe = db.execute('SELECT graph_id FROM executions WHERE execution_id=?',
                                   (effective,)).fetchone()[0] == wardrobe_store.GRAPH_ID
            def read_only_owner(*args, **kwargs):
                raise AssertionError('Continue inspection cannot invoke an owner')
            graph = build_story_graph(db, saver, read_only_owner, wardrobe=wardrobe)
            snapshot = await graph.aget_state(saved.config)
            runnable = bool(snapshot.next or saved.pending_writes)
            review = db.execute('SELECT request_id,checkpoint_id,task_id,interrupt_id FROM review_requests '
                'WHERE execution_id=? AND decision_id IS NULL AND checkpoint_id IS NOT NULL '
                'ORDER BY request_revision DESC LIMIT 1', (effective,)).fetchone()
            if review:
                from backend.story_runner import _source_wait
                _source_wait(saved, review[1], review[2], review[3], review[0])
    if group and not db.execute('SELECT 1 FROM execution_outcomes WHERE execution_id=?', (effective,)).fetchone():
        if not db.execute("SELECT 1 FROM execution_work WHERE execution_id=? AND status IN ('pending','claimed','blocked')",
                          (effective,)).fetchone() and not db.execute(
                "SELECT 1 FROM execution_controls WHERE execution_id=? AND kind='cancel'", (effective,)).fetchone():
            from backend.image_graph import build_image_graph
            from backend.image_runner import inspect_image_checkpoint
            saved, _ = await inspect_image_checkpoint(saver, build_image_graph(db, saver, group), group, db=db)
            checkpoint = saved.config['configurable']['checkpoint_id'] if saved else None
            runnable = bool(saved and (group.checkpoint_id is None or saved.metadata['step'] >= 2))
    if _resolve(db, selected)[1] != effective:
        if not refreshed:
            return await _inspect(db, saver, selected, refreshed=True)
        raise ValueError('Continue effective process changed during read; refresh projection')
    return checkpoint, runnable


async def continue_projection(db, saver, execution_id, *, active_work_ids=None) -> ContinueProjection:
    checkpoint, runnable = await _inspect(db, saver, execution_id)
    # Resolve again after awaits: decisions, cancellation and accepted lineage may change.
    return _policy(db, execution_id, checkpoint, runnable, active_work_ids=active_work_ids)


def _old_command(db, execution, command, digest):
    row = db.execute('SELECT payload_digest,receipt_body FROM continue_commands WHERE execution_id=? AND command_key=?',
                     (execution, command.command_key)).fetchone()
    if row and row[0] != digest:
        raise ValueError('Continue delivery key conflicts with original request')
    return ContinueReceipt.model_validate_json(row[1]) if row and row[1] else None


def _save_receipt(db, view, command, digest):
    old = _old_command(db, view.selected_execution_id, command, digest)
    if old is not None:
        return old
    receipt = ContinueReceipt(**view.model_dump(), command_key=command.command_key,
                              expected_token=command.expected_token, disposition=view.action)
    db.execute('INSERT INTO continue_commands VALUES (?,?,?,?) ON CONFLICT(execution_id,command_key) '
        'DO UPDATE SET receipt_body=excluded.receipt_body', (view.selected_execution_id, command.command_key,
        digest, canonical_json(receipt).decode()))
    return receipt


def _validate_connection(intent):
    selected = config.resolve_comfyui_connection(intent.connection.connection)
    if intent.connection.endpoint_digest != 'sha256:' + selected.endpoint_digest:
        raise ValueError('Continue configured connection identity changed')


def _check_occ(command, view, link):
    # Original transition copies converge only at the unchanged unclaimed consumer.
    # Controls, progress or Retry cannot borrow the pre-handoff source token.
    converging = (link and command.expected_token == link[2] and command.production_intent and
                  (link[8] == 'reserved' or (view.status == 'created' and view.action == 'open'
                                           and view.effective_execution_id == link[5])))
    if command.expected_token != view.occ_token and not converging:
        raise ValueError('Stale Continue token')


async def continue_execution(db: sqlite3.Connection, saver, execution_id: str,
                             request: ContinueRequest | dict, *, active_work_ids=None) -> ContinueReceipt:
    command = ContinueRequest.model_validate(request)
    digest = sha256_digest(canonical_json(command))
    old = _old_command(db, execution_id, command, digest)
    if old:
        return old  # Exact saved delivery precedes every stale/settings check.
    checkpoint, runnable = await _inspect(db, saver, execution_id)
    view = _policy(db, execution_id, checkpoint, runnable, active_work_ids=active_work_ids)
    intent = command.production_intent
    link = _handoff(db, execution_id)
    if intent and (not link and view.action != 'start_images'):
        raise ValueError('Production intent is not a declared handoff for this process')
    if link and intent and (sha256_digest(canonical_json(intent)), canonical_json(intent).decode()) != link[3:5]:
        raise ValueError('Continue production intent conflicts with reserved pins')
    _check_occ(command, view, link)
    if view.action != 'start_images':
        with batch_store._transaction(db):
            # No await inside this transaction. Compare the exact post-read facts.
            if _policy(db, execution_id, checkpoint, runnable, active_work_ids=active_work_ids).occ_token != view.occ_token:
                raise ValueError('Continue process changed before admission')
            if view.action == 'resume':
                # The token already includes the checkpoint; the runner validates it
                # again before invoking. Admission adds no budget or resume value.
                start_digest = db.execute('SELECT start_digest FROM executions WHERE execution_id=?',
                                   (view.effective_execution_id,)).fetchone()[0]
                work_id = sha256_digest(f'kinodel.reconcile.v1:{view.effective_execution_id}:{checkpoint}'.encode())
                old_work = db.execute('SELECT status FROM execution_work WHERE work_id=?', (work_id,)).fetchone()
                if old_work:
                    raise ValueError('Stopped checkpoint already has settled or blocked reconciliation')
                db.execute('INSERT INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,status) '
                    "VALUES (?,?,'reconcile',?,?,'pending')", (work_id, view.effective_execution_id, checkpoint, start_digest))
                view = view.model_copy(update={'work_id': work_id})
            return _save_receipt(db, view, command, digest)
    if intent is None and link is None:
        raise ValueError('Continue requires explicit production intent')
    if link is None:
        assert intent is not None
        _validate_connection(intent)
        body = canonical_json(intent).decode()
        key = 'continue:' + batch_store._identity('kinodel.continue-handoff.v1', execution_id)[7:]
        activation, consumer, _, _, _ = images._identities(view.project_id, key)
        with batch_store._transaction(db):
            prepared = batch_preparation.read_saved_batch_input(db, execution_id,
                **intent.model_dump(), activation_id=activation)
            batch_id = batch_store._identity('kinodel.batch-input.v1', execution_id, images.STAGE_ID, activation)
            pins = canonical_json(prepared.prepared_input)
            uri = batch_store._uri(view.project_id, batch_id, prepared.input_digest)
            db.execute('INSERT INTO batch_input_pins VALUES (?,?,?,?,?,?,?,?,?)',
                (batch_id, execution_id, images.STAGE_ID, activation, intent.source_plan_ref.artifact_id,
                 prepared.input_digest, pins.decode(), uri, 'reserved'))
            db.execute('INSERT INTO continue_handoffs VALUES (?,?,?,?,?,?,?,?,?)', (execution_id,
                _source_token(db, execution_id), command.expected_token, sha256_digest(body.encode()), body,
                consumer, key, batch_id, 'reserved'))
            db.execute('INSERT INTO continue_commands VALUES (?,?,?,NULL)', (execution_id, command.command_key, digest))
        link = _handoff(db, execution_id)
    await validate_story_storage(db, saver)
    with batch_store._transaction(db):
        old = _old_command(db, execution_id, command, digest)
        if old:
            return old  # Another copy may have committed this SAME delivery during the await.
        if _source_token(db, execution_id) != link[1]:
            raise ValueError('Continue source changed during admission')
        fresh = _handoff(db, execution_id)
        if fresh[8] == 'accepted':
            view = _policy(db, execution_id, active_work_ids=active_work_ids)
            _check_occ(command, view, fresh)
            return _save_receipt(db, view, command, digest)
    # Publication reuses FULL original pins, without source/catalog/settings lookup.
    if _source_token(db, execution_id) != link[1]:
        raise ValueError('Continue source changed during admission')
    row = batch_store._batch_row(db, link[7])
    batch, frozen, path = batch_store._restore_batch(db, row)
    from backend.story_graph import validate_wardrobe_success
    handoff = batch.prepared_input
    if validate_wardrobe_success(db, execution_id, handoff.story_approval.approval_request_id) != handoff.source_plan_ref:
        raise ValueError('Continue source authority changed during admission')
    if row[8] == 'reserved':
        batch_store._publish_body(path, frozen)
        with batch_store._transaction(db):
            db.execute("UPDATE batch_input_pins SET publication_state='published' WHERE batch_id=?", (link[7],))
    batch = batch_store.read_batch_input(db, link[7])
    accepted = images._receipt(view.project_id, link[6], batch)
    with batch_store._transaction(db):
        if _source_token(db, execution_id) != link[1]:
            raise ValueError('Continue source changed before acceptance')
        fresh = _handoff(db, execution_id)
        if fresh[8] == 'reserved':
            images._accept_image_start(db, view.project_id, link[6], accepted, continue_source=execution_id)
            db.execute("UPDATE continue_handoffs SET acceptance_state='accepted' WHERE source_execution_id=?",
                       (execution_id,))
        view = _policy(db, execution_id, active_work_ids=active_work_ids)
        if fresh[8] == 'accepted':
            _check_occ(command, view, fresh)
        return _save_receipt(db, view, command, digest)
