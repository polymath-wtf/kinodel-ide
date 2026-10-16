"""One sequential unit/native tick per accepted image group under the root lock.

No graph/checkpointer access, polling loop, implicit Retry or output-only grant.
The existing native owners retain every prepared byte, dispatch claim and receipt;
result storage alone publishes the exact terminal manifest and unique durable wake.
"""

import asyncio
from collections.abc import Callable
import sqlite3

import httpx

from backend import anchor_reference_store as references, anchor_reference_worker as reference_worker
from backend import batch_generation, batch_store, comfyui, image_group_results as results, image_group_store as groups
from backend import portrait_submission_store as submissions, portrait_worker as native, render_job_store as jobs
from backend.story_control import cancel_requested
from backend.story_store import _assert_writable


def _control(db, execution_id, stop):
    if stop is not None and stop.is_set():
        return 'stopped'
    if cancel_requested(db, execution_id):
        return 'cancelled'
    _assert_writable(db, execution_id)
    if db.execute("SELECT 1 FROM execution_work WHERE execution_id=? AND status='blocked'", (execution_id,)).fetchone():
        return 'blocked'
    return None


def _submission(db, binding):
    row = submissions._row(db, binding.job_id, binding.attempt_id)
    if row is None:
        return None
    return submissions.read_anchor_unit_submission(db, binding.job_id, attempt_id=binding.attempt_id,
        expected_unit_digest=binding.unit_input_digest, expected_wire_digest=row[2])


def _publish(db, group, status, failed_unit=None):
    return results.publish_image_group_result(db, group.receipt.execution_id,
        expected_request_digest=group.receipt.request_digest, status=status, failed_unit_key=failed_unit).status


async def _tick(db, group, transport, clock_ms, stop):
    execution_id = group.receipt.execution_id
    root = results.read_image_input_batch(db, execution_id)
    outputs = []
    planned = None
    binding = None
    record = None
    for unit in group.batch.prepared_input.ordered_units:
        planned = unit
        try:
            binding = results.read_image_unit_attempt(db, execution_id, unit.unit_key)
        except LookupError:
            binding = None
            break
        record = _submission(db, binding)
        if record is None or record.state != 'completed':
            break
        job = jobs.read_anchor_unit_job(db, binding.job_id, expected_unit_digest=binding.unit_input_digest,
                                       attempt_id=binding.attempt_id)
        results._validate_parents(unit, job, outputs)
        outputs.append(results._output(db, binding, job))
    else:
        return _publish(db, group, 'complete')
    assert planned is not None
    if record is not None and binding is not None and record.state == 'failed':
        return _publish(db, group, 'failed', planned.unit_key) if results.is_terminal_image_failure(record) else 'blocked'
    if binding is None:
        parents = []
        for reference in planned.references:
            parent = next(output for output in outputs if output.unit_key == reference.source.unit_key)
            parents.append(dict(unit_key=parent.unit_key, source_id=parent.candidate_id, digest=parent.candidate_digest,
                                input_name='parents/' + parent.candidate_id[7:] + '.png'))
        batch_store._assert_image_turn(db, root.batch_id, planned.unit_key, execution_id)
        context = None
        if batch_store._unit_row(db, root.batch_id, planned.unit_key) is None:
            _, _, workflow = batch_generation._unit(root.prepared_input, planned.unit_key)
            context = await comfyui.acquire_preparation_context(root.prepared_input.connection.connection, workflow.workflow_id,
                expected_endpoint_digest=root.prepared_input.connection.endpoint_digest,
                expected_registry_digest=workflow.registry_digest, transport=transport)
            control = _control(db, execution_id, stop)
            if control:
                return control
        prepared = batch_store.prepare_saved_batch_unit(db, root.batch_id, planned.unit_key,
            parent_bindings=parents, context=context, image_execution_id=execution_id)
        if control := _control(db, execution_id, stop):
            return control
        job = jobs.create_anchor_unit_job(db, root.batch_id, planned.unit_key,
            expected_unit_digest=prepared.input_digest, parent_bindings=parents, image_execution_id=execution_id)
        if control := _control(db, execution_id, stop):
            return control
        retry = groups._read_retry_request(db, execution_id)
        if retry is not None:
            predecessor = results.read_image_group_result(db, retry.predecessor_execution_id)
            failure = predecessor.body.failure
            assert failure is not None
            if failure.unit_key == planned.unit_key:
                job = jobs.allocate_anchor_unit_retry(db, failure.job_id, expected_unit_digest=failure.unit_input_digest,
                    previous_attempt_id=failure.attempt_id, expected_previous_wire_digest=failure.wire_digest,
                    expected_previous_revision=failure.revision, retry_trigger_id=group.receipt.group_id,
                    image_execution_id=execution_id)
        if control := _control(db, execution_id, stop):
            return control
        binding = results.bind_image_unit_attempt(db, execution_id, planned.unit_key,
            expected_request_digest=group.receipt.request_digest, expected_unit_digest=prepared.input_digest,
            job_id=job.job_id, attempt_id=job.attempt_id)
        record = _submission(db, binding)
    else:
        job = jobs.read_anchor_unit_job(db, binding.job_id, expected_unit_digest=binding.unit_input_digest,
                                       attempt_id=binding.attempt_id)
    if control := _control(db, execution_id, stop):
        return control
    jobs.assert_anchor_attempt_writable(db, job.job_id, job.attempt_id)
    if job.kind == 'sheet' and record is None:
        row = references._row(db, job.job_id, job.attempt_id)
        selectors = dict(expected_project_id=root.prepared_input.source_plan_ref.project_id,
                         expected_unit_digest=binding.unit_input_digest, attempt_id=binding.attempt_id)
        if row is None:
            preview = references.preview_anchor_reference_intent(db, job.job_id, **selectors)
            if control := _control(db, execution_id, stop):
                return control
            transfer = references.authorize_anchor_reference_transfer(db, job.job_id, **selectors,
                                                                      expected_intent_digest=preview.intent_digest)
        else:
            transfer = references.read_anchor_reference_transfer(db, job.job_id, **selectors, expected_intent_digest=row[3])
        if transfer.state != 'finalized':
            transfer = await reference_worker.tick_anchor_references(db, job.job_id, **selectors,
                expected_intent_digest=transfer.intent_digest, expected_revision=transfer.revision, transport=transport, stop=stop)
            control = _control(db, execution_id, stop)
            if control:
                return control
            return 'blocked' if transfer.state == 'blocked' else 'active'
    if record is None:
        preview = submissions.preview_anchor_unit_submission(db, job.job_id,
            expected_unit_digest=binding.unit_input_digest, attempt_id=binding.attempt_id)
        if control := _control(db, execution_id, stop):
            return control
        record = submissions.authorize_anchor_unit_submission(db, job.job_id,
            expected_unit_digest=binding.unit_input_digest, expected_wire_digest=preview.wire_digest,
            accepted_at_ms=clock_ms(), attempt_id=binding.attempt_id)
    record = await native.tick_anchor_unit_job(db, job.job_id, expected_unit_digest=binding.unit_input_digest,
        expected_wire_digest=record.preview.wire_digest, expected_revision=record.revision, attempt_id=binding.attempt_id,
        transport=transport, clock_ms=clock_ms, stop=stop)
    control = _control(db, execution_id, stop)
    if control:
        return control
    if record.state == 'failed':
        return _publish(db, group, 'failed', planned.unit_key) if results.is_terminal_image_failure(record) else 'blocked'
    if record.state == 'completed' and planned == group.batch.prepared_input.ordered_units[-1]:
        return _publish(db, group, 'complete')
    return 'blocked' if record.state == 'blocked' else 'active'


async def tick_image_group(db: sqlite3.Connection, execution_id: str, *, expected_request_digest: str,
        transport: httpx.AsyncBaseTransport | None = None, clock_ms: Callable[[], int] = native._clock,
        stop: asyncio.Event | None = None) -> str:
    """Advance only the first unfinished declared unit; next unit needs a later sweep.

    Group acceptance authorizes its exact current attempt. Blocked/unknown acceptance
    stays nonterminal, with existing native GET-only recovery and explicit contract
    revalidation/output grants left to their trusted entrypoints. Failed-only group
    Retry is a separate consumer; its retained successes are never re-owned/ticked.
    """
    group = groups.read_image_group(db, execution_id)
    if expected_request_digest != group.receipt.request_digest:
        raise ValueError('Image worker request identity mismatch')
    row = results._result_row(db, group.receipt.group_id)
    if row is not None and row[6] == 'published':
        return results.read_image_group_result(db, execution_id).status
    control = _control(db, execution_id, stop)
    if control:
        return control
    if row is not None:  # Finish only the immutable result reservation, never native effects.
        body = results.ImageGroupResultBodyV1.model_validate_json(row[4])
        return _publish(db, group, body.status, None if body.failure is None else body.failure.unit_key)
    try:
        return await _tick(db, group, transport, clock_ms, stop)
    except (ValueError, OSError, LookupError):
        control = _control(db, execution_id, stop)
        if control:
            return control
        raise


def _native_slot(db):
    """Native occupancy survives graph blocking, cancellation and consumer outcomes.

    Only unsent or proved terminal native attempts release the slot. In particular,
    a local post-dispatch deadline/failure is not proof that the provider stopped.
    Retained-success bindings do not create another owner of the physical attempt.
    """
    rows = db.execute("SELECT DISTINCT u.unit_key,u.job_id,u.attempt_id,u.unit_input_digest,u.origin_execution_id,s.state "
        "FROM image_unit_attempts u JOIN portrait_submissions s ON s.job_id=u.job_id AND s.attempt_id=u.attempt_id "
        "WHERE s.state NOT IN ('authorized','completed')").fetchall()
    holders = []
    for key, job, attempt, digest, origin, state in rows:
        facts, _ = results._facts(db, results.ImageUnitAttemptV1(key, job, attempt, digest, origin))
        if submissions.read_native_terminal_observation(db, facts) is not None:
            continue
        if state == 'failed':
            if results.is_terminal_image_failure(facts):
                continue
        holders.append((origin, facts))
    if len(holders) > 1:
        raise ValueError('Multiple unresolved image attempts hold the native provider slot')
    return holders[0] if holders else None


async def tick_image_groups(db: sqlite3.Connection, *, transport: httpx.AsyncBaseTransport | None = None,
        clock_ms: Callable[[], int] = native._clock, stop: asyncio.Event | None = None) -> int:
    """One native turn, including settled waits, without losing unresolved occupancy."""
    if stop is not None and stop.is_set():
        return 0
    holder = _native_slot(db)
    rows = db.execute("SELECT g.execution_id,g.request_digest FROM image_groups g "
        "WHERE NOT EXISTS (SELECT 1 FROM execution_outcomes o WHERE o.execution_id=g.execution_id) "
        "AND NOT EXISTS (SELECT 1 FROM execution_controls c WHERE c.execution_id=g.execution_id AND c.kind='cancel') "
        "AND NOT EXISTS (SELECT 1 FROM image_group_results r WHERE r.group_id=g.group_id AND r.publication_state='published') "
        "AND NOT EXISTS (SELECT 1 FROM execution_work w WHERE w.execution_id=g.execution_id AND w.status='blocked') "
        "ORDER BY g.rowid").fetchall()
    if holder is not None:
        origin, record = holder
        rows = [(execution, digest) for execution, digest in rows if execution == origin]
        if not rows:
            # Cancellation/graph failure cannot permit promotion, but observation must
            # outlive them. A proved terminal release uses this turn, not a second job.
            await native.observe_anchor_unit_terminal(db, record.preview.job_id, **native._args(record),
                transport=transport, clock_ms=clock_ms, stop=stop)
            return 1
    processed = 0
    for execution_id, digest in rows:
        if stop is not None and stop.is_set():
            break
        await tick_image_group(db, execution_id, expected_request_digest=digest, transport=transport,
                               clock_ms=clock_ms, stop=stop)
        processed += 1
        break  # One native job globally; later groups wait for this group's terminal result.
    return processed
