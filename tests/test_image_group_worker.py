"""Accepted consumers, real native pins/imports, mock HTTP only; no live provider."""

import asyncio
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from typing import Any

import httpx

from backend import batch_store, comfyui, database, image_group_results as results, image_group_store as groups
from backend import portrait_candidate_store as candidates, portrait_submission_store as submissions
from backend import render_job_store as jobs, anchor_reference_store as references
from backend.config import resolve_comfyui_connection
from tests import test_batch_store as pins, test_image_group_store as admission
from tests import test_story_wardrobe_api as fixtures
from tests.test_portrait_candidate_store import png
from tests.test_portrait_worker import ENDPOINT, NOW, response
from tests.test_story_wardrobe_runtime import retained_inventory


class ImageGroupWorkerTests(fixtures.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    source: Any = admission.ImageGroupStoreTests.source
    arguments: Any = admission.ImageGroupStoreTests.arguments
    context: Any = pins.BatchStoreTests.context

    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('backend.image_group_worker'), 'Sequential image worker is missing')
        from backend import image_group_worker
        self.worker = image_group_worker
        self.profile = pins.production_catalog()['image_only']['profiles'][0]['pin']
        env = patch.dict(os.environ, {'COMFYUI_LOCAL_ENDPOINT': ENDPOINT, 'COMFYUI_CONNECTION': 'server'})
        env.start()
        self.addCleanup(env.stop)
        self.requests = []
        self.wires: dict[str, Any] = {}
        self.uploads: dict[str, bytes] = {}
        self.fail_keys = set()
        self.hook = None

    async def start(self, runtime, ref, key='images'):
        connection = dict(connection='local', endpoint_digest='sha256:' + resolve_comfyui_connection('local').endpoint_digest)
        return await groups.start_image_execution(runtime.db, runtime.saver, self.project, key,
            **self.arguments(ref, image_size=dict(width=512, height=512), connection=connection))

    def server(self, db):
        def handle(request):
            self.assertFalse(db.in_transaction, 'SQL transaction crossed HTTP')
            self.requests.append(request)
            route = request.url.path.removeprefix('/native/')
            if self.hook:
                self.hook(request, route)
            if route == 'prompt':
                wire = json.loads(request.content)
                correlation = next(iter(wire['extra_data'].values()))
                attempt = correlation['attempt_id']
                self.assertNotIn(attempt, self.wires, 'Duplicate paid POST')
                self.wires[attempt] = wire
                return response(dict(prompt_id=attempt[7:], number=1, node_errors={}))
            if route == 'queue':
                return response(dict(queue_running=[], queue_pending=[]))
            if route.startswith('history'):
                histories = {}
                for attempt, wire in self.wires.items():
                    correlation = next(iter(wire['extra_data'].values()))
                    job = jobs._row(db, correlation['job_id'], attempt)
                    assert job is not None
                    key = job[2]
                    node = '494' if correlation.get('kind') == 'sheet' else '865'
                    histories[attempt[7:]] = dict(prompt=[1, attempt[7:], wire['prompt'],
                        {**wire['extra_data'], 'client_id': wire['client_id']}, [node]],
                        outputs={node: dict(images=[dict(filename=key + '.png', subfolder='', type='output')])},
                        status=dict(status_str='error' if key in self.fail_keys else 'success', completed=True, messages=[]))
                if '/' in route:
                    histories = {k: v for k, v in histories.items() if k == route.split('/', 1)[1]}
                return response(histories)
            if route == 'upload/image':
                # Validate actual attempt-owned multipart namespace and preserve original bytes.
                row = db.execute('SELECT record_body FROM anchor_reference_transfers ORDER BY rowid DESC LIMIT 1').fetchone()
                transfer = references.AnchorReferenceTransferV1.model_validate_json(row[0])
                item = next(r for r in transfer.intent.references if r.name.encode() in request.content)
                self.assertNotIn(item.name, self.uploads, 'Known receipt was uploaded again')
                self.assertIn(png(), request.content)
                self.uploads[item.name] = png()
                return response(dict(name=item.name, subfolder=item.subfolder, type='input'))
            if route == 'view':
                return response(self.uploads[request.url.params['filename']] if request.url.params['type'] == 'input' else png(), raw=True)
            raise AssertionError('Unexpected route: ' + route)
        return httpx.MockTransport(handle)

    @contextmanager
    def preparation(self, db, execution):
        batch = results.read_image_input_batch(db, execution)
        async def context(connection, workflow, **kwargs):
            self.assertEqual(connection, batch.prepared_input.connection.connection)
            unit = next(u for u in batch.prepared_input.ordered_units
                        if pins.generation._unit(batch.prepared_input, u.unit_key)[2].workflow_id == workflow)
            return self.context(batch, unit.unit_key)
        with patch.object(comfyui, 'acquire_preparation_context', side_effect=context) as acquire:
            yield acquire

    async def tick(self, db, receipt, **kwargs):
        return await self.worker.tick_image_group(db, receipt.execution_id,
            expected_request_digest=receipt.request_digest, transport=self.server(db), clock_ms=lambda: NOW, **kwargs)

    async def finish(self, db, receipt):
        for _ in range(20):
            state = await self.tick(db, receipt)
            if state in ('complete', 'failed'):
                return results.read_image_group_result(db, receipt.execution_id)
        self.fail('Group did not finish: ' + repr(db.execute('SELECT state,revision,submission_body FROM portrait_submissions').fetchall()))

    async def test_declared_N_order_actual_native_graphs_and_source_preservation(self):
        await self.declared(('comedian',), ['face-0', 'location', 'sheet-0'])

    async def test_location_only_N1(self):
        await self.declared((), ['location'])

    async def test_native_GET_context_only_for_missing_pin_and_cancel_before_preparation(self):
        from tests.test_comfyui import PreflightTests
        from tests.test_comfyui_workflows import installed_schemas
        fixture = PreflightTests()
        fixture.calls, fixture.responses = [], {}
        fixture.schemas = installed_schemas()
        fixture.stats = dict(system=dict(comfyui_version='0.3.50', python_version='3.13', pytorch_version='2.8'), devices=[])
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            receipt = await self.start(runtime, ref)
            native = self.server(db)
            def handle(request):
                if request.url.path.removeprefix('/native/').split('/')[0] in ('system_stats', 'object_info', 'models'):
                    return fixture.handler(request)
                return native.handler(request)
            transport = httpx.MockTransport(handle)
            self.assertEqual(await self.worker.tick_image_group(db, receipt.execution_id,
                expected_request_digest=receipt.request_digest, transport=transport, clock_ms=lambda: NOW), 'active')
            self.assertTrue(fixture.calls)
            self.assertTrue(all(call.method == 'GET' for call in fixture.calls))
            with patch.object(comfyui, 'acquire_preparation_context', side_effect=AssertionError('Pinned context')), \
                    patch('backend.comfyui_workflows.secrets.randbelow', side_effect=AssertionError('Pinned RNG')):
                self.assertEqual(await self.tick(db, receipt), 'complete')
            canceled = await self.start(runtime, ref, key='cancel-context')
            async def cancel_context(connection, workflow, **kwargs):
                context = await comfyui_original(connection, workflow, **kwargs)
                runtime.cancel(canceled.execution_id, 'cancel')
                return context
            comfyui_original = comfyui.acquire_preparation_context
            with patch.object(comfyui, 'acquire_preparation_context', side_effect=cancel_context):
                self.assertEqual(await self.worker.tick_image_group(db, canceled.execution_id,
                    expected_request_digest=canceled.request_digest, transport=transport, clock_ms=lambda: NOW), 'cancelled')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM batch_unit_input_pins WHERE batch_id=?',
                                        (canceled.batch_id,)).fetchone(), (0,))

    async def test_repeated_roles_N5(self):
        await self.declared(('comedian', 'fox'), ['face-0', 'face-1', 'location', 'sheet-0', 'sheet-1'])

    async def declared(self, subjects, expected):
        async with self.source(subjects) as (runtime, ref, _):
            db = runtime.db
            before = retained_inventory(db, ref.execution_id)
            receipt = await self.start(runtime, ref)
            with self.preparation(db, receipt.execution_id) as acquire:
                result = await self.finish(db, receipt)
            self.assertEqual([o.unit_key for o in result.body.outputs], expected)
            self.assertEqual(acquire.call_count, len(expected))
            self.assertEqual(len(self.wires), len(expected))
            self.assertEqual(len(self.uploads), 2 * len(subjects))
            for output in result.body.outputs:
                wire = self.wires[output.attempt_id]
                if output.parent_bindings:
                    self.assertEqual(wire['prompt']['470']['inputs']['image'],
                        next(name for name in self.uploads if output.job_id[7:] in name and '-portrait-' in name))
                    self.assertIn('496', wire['prompt'])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_jobs').fetchone(), (len(expected),))
            self.assertEqual(retained_inventory(db, ref.execution_id), before)
            changes = db.total_changes
            with patch.object(comfyui, 'acquire_preparation_context', side_effect=AssertionError('Terminal context')):
                self.assertEqual(await self.tick(db, receipt), 'complete')
            self.assertEqual(db.total_changes, changes)

    async def test_runner_ticks_settled_wait_and_shutdown_drains_native_await(self):
        from backend.story_runner import run_story_work
        import inspect
        self.assertIn('image_transport', inspect.signature(run_story_work).parameters,
                      'Runner has no private native tick configuration')
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            receipt = await self.start(runtime, ref)
            runtime.image_transport = self.server(db)
            runtime.image_clock_ms = lambda: NOW
            with self.preparation(db, receipt.execution_id):
                await runtime.run()
                self.assertIsNotNone(groups.read_image_group(db, receipt.execution_id).checkpoint_id)
                self.assertEqual(len(self.wires), 1)
                self.assertEqual(db.execute('SELECT status FROM execution_work WHERE work_id=?', (receipt.work_id,)).fetchone(), ('completed',))
                entered, release = asyncio.Event(), asyncio.Event()
                async def waiting(request):
                    entered.set()
                    await release.wait()
                    return response(dict(queue_running=[], queue_pending=[]))
                runtime.image_transport = httpx.MockTransport(waiting)
                running = asyncio.create_task(runtime.run())
                await entered.wait()
                closing = asyncio.create_task(runtime.close())
                await asyncio.sleep(0)
                self.assertFalse(closing.done(), 'Root ownership released during native HTTP')
                release.set()
                await asyncio.gather(running, closing)
            self.assertEqual(db.execute('SELECT state FROM portrait_submissions').fetchone(), ('accepted',))
            self.assertEqual(len(self.wires), 1)

    async def test_runner_native_completion_publishes_wake_then_joins_on_next_sweep(self):
        async with self.source(()) as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            runtime.image_transport, runtime.image_clock_ms = self.server(runtime.db), lambda: NOW
            with self.preparation(runtime.db, receipt.execution_id):
                await runtime.run()  # Start/wait + one provider dispatch.
                await runtime.run()  # Settled wait still schedules native reconciliation/import.
                result = results.read_image_group_result(runtime.db, receipt.execution_id)
                self.assertIsNone(runtime.db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                                    (receipt.execution_id,)).fetchone())
                await runtime.run()  # Only the existing graph runner delivers the exact result wake.
            self.assertEqual(runtime.db.execute('SELECT outcome,source_id FROM execution_outcomes WHERE execution_id=?',
                                               (receipt.execution_id,)).fetchone(), ('completed', result.result_id))
            self.assertEqual(len(self.wires), 1)

    async def test_repeated_runner_cancel_drains_native_response_and_client(self):
        async with self.source(()) as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            entered, release = asyncio.Event(), asyncio.Event()
            streamed = []
            async def waiting(request):
                entered.set()
                await release.wait()
                value = response(dict(prompt_id='late-response', number=1, node_errors={}))
                streamed.append(value.stream)
                return value
            runtime.image_transport, runtime.image_clock_ms = httpx.MockTransport(waiting), lambda: NOW
            with self.preparation(runtime.db, receipt.execution_id):
                running = asyncio.create_task(runtime.run())
                await entered.wait()
                running.cancel()
                await asyncio.sleep(0)
                running.cancel()
                await asyncio.sleep(0)
                self.assertFalse(running.done(), 'Runner released native activity during repeated caller cancellation')
                release.set()
                with self.assertRaises(asyncio.CancelledError):
                    await running
            self.assertTrue(streamed[0].closed)
            self.assertEqual(runtime.db.execute('SELECT state,prompt_id FROM portrait_submissions').fetchone(), ('dispatching', None))

    async def test_sweep_has_one_global_provider_turn_no_future_group_preparation(self):
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            first, second = await self.start(runtime, ref), await self.start(runtime, ref, key='second')
            with self.preparation(db, first.execution_id):
                await self.worker.tick_image_groups(db, transport=self.server(db), clock_ms=lambda: NOW)
                self.assertEqual(len(self.wires), 1)
                self.assertIsNone(batch_store._unit_row(db, second.batch_id, 'location'))
                await self.worker.tick_image_groups(db, transport=self.server(db), clock_ms=lambda: NOW)
                self.assertEqual(results.read_image_group_result(db, first.execution_id).status, 'complete')
                self.assertIsNone(batch_store._unit_row(db, second.batch_id, 'location'))
            with self.preparation(db, second.execution_id):
                await self.worker.tick_image_groups(db, transport=self.server(db), clock_ms=lambda: NOW)
                self.assertEqual(len(self.wires), 2)

    async def test_corrupt_wait_blocks_graph_but_unresolved_native_attempt_keeps_global_slot(self):
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            before = retained_inventory(db, ref.execution_id)
            first, second = await self.start(runtime, ref), await self.start(runtime, ref, key='second')
            runtime.image_transport, runtime.image_clock_ms = self.server(db), lambda: NOW
            with self.preparation(db, first.execution_id):
                await runtime.run()
                self.assertEqual(len(self.wires), 1)
                selected = results.read_image_unit_attempt(db, first.execution_id, 'location')
                record = self.worker._submission(db, selected)
                saved = await runtime.saver.aget_tuple({'configurable': {'thread_id': first.execution_id}})
                assert saved is not None
                assert saved.parent_config is not None
                checkpoint = {**saved.checkpoint, 'channel_values': {**saved.checkpoint['channel_values'],
                    'wait_ref': {**saved.checkpoint['channel_values']['wait_ref'], 'request_digest': 'sha256:' + '0' * 64}}}
                await runtime.saver.aput(saved.parent_config, checkpoint, saved.metadata, {})
                with self.assertRaises(ValueError):
                    await runtime.run()
                self.assertEqual(db.execute("SELECT status FROM execution_work WHERE execution_id=? AND kind='reconcile'",
                                            (first.execution_id,)).fetchone(), ('blocked',))
                requests = len(self.requests)
                processed = await runtime.run()
                self.assertEqual(len(self.wires), 1, 'Graph blocking cannot release a possibly running native prompt')
                self.assertEqual(processed, 0)
                self.assertEqual(len(self.requests), requests, 'Do not tick the provider for a graph-integrity blocked holder')
                self.assertEqual(self.worker._submission(db, selected), record)
                self.assertIsNone(batch_store._unit_row(db, second.batch_id, 'location'))
                # Explicit fixture-only integrity repair; the sweep must service the
                # same exact holder, not dispatch its waiting sibling first.
                await runtime.saver.aput(saved.parent_config, saved.checkpoint, saved.metadata, {})
                db.execute("UPDATE execution_work SET status='pending',blocked_reason=NULL,work_version=work_version+1 "
                           "WHERE execution_id=? AND kind='reconcile'", (first.execution_id,))
                await runtime.run()
                self.assertEqual(results.read_image_group_result(db, first.execution_id).status, 'complete')
                self.assertIsNone(batch_store._unit_row(db, second.batch_id, 'location'))
            with self.preparation(db, second.execution_id):
                await runtime.run()
            self.assertEqual(len(self.wires), 2)
            self.assertEqual(retained_inventory(db, ref.execution_id), before)

    async def test_graph_block_before_claim_does_not_hold_slot_and_existing_holder_wins_after_repair(self):
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            first, second = await self.start(runtime, ref), await self.start(runtime, ref, key='second')
            db.execute("UPDATE execution_work SET status='blocked',blocked_reason='fixture_integrity_block' WHERE work_id=?",
                       (first.work_id,))
            with self.preparation(db, second.execution_id):
                self.assertEqual(await self.worker.tick_image_groups(db, transport=self.server(db), clock_ms=lambda: NOW), 1)
                self.assertEqual(len(self.wires), 1)
                self.assertIsNone(batch_store._unit_row(db, first.batch_id, 'location'))
                db.execute("UPDATE execution_work SET status='pending',blocked_reason=NULL WHERE work_id=?", (first.work_id,))
                self.assertEqual(await self.worker.tick_image_groups(db, transport=self.server(db), clock_ms=lambda: NOW), 1)
                self.assertEqual(len(self.wires), 1, 'An older now-runnable group cannot bypass the unresolved native holder')
                self.assertEqual(results.read_image_group_result(db, second.execution_id).status, 'complete')
                self.assertIsNone(batch_store._unit_row(db, first.batch_id, 'location'))
            with self.preparation(db, first.execution_id):
                await self.worker.tick_image_groups(db, transport=self.server(db), clock_ms=lambda: NOW)
            self.assertEqual(len(self.wires), 2)

    async def test_cancelled_consumer_known_prompt_retains_native_slot_without_late_effects(self):
        await self.cancelled_slot(unknown=False)

    async def test_cancelled_consumer_unknown_prompt_retains_native_slot_without_late_effects(self):
        await self.cancelled_slot(unknown=True)

    async def cancelled_slot(self, *, unknown):
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            before = retained_inventory(db, ref.execution_id)
            first, second = await self.start(runtime, ref), await self.start(runtime, ref, key='second')
            server = self.server(db)
            def handle(request):
                value = server.handler(request)
                if unknown and request.url.path.endswith('/prompt'):
                    raise httpx.ReadError('Lost potentially accepted native response')
                return value
            runtime.image_transport, runtime.image_clock_ms = httpx.MockTransport(handle), lambda: NOW
            with self.preparation(db, first.execution_id):
                await runtime.run()
                selected = results.read_image_unit_attempt(db, first.execution_id, 'location')
                record = self.worker._submission(db, selected)
                assert record is not None
                self.assertEqual(record.state, 'blocked' if unknown else 'accepted')
                self.assertEqual(record.prompt_id is None, unknown)
                runtime.cancel(first.execution_id, 'cancel')
                requests = len(self.requests)
                await runtime.run()
                self.assertEqual(db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                            (first.execution_id,)).fetchone(), ('cancelled',))
                self.assertEqual(len(self.wires), 1, 'Consumer cancellation is not proof that the provider job stopped')
                self.assertEqual(len(self.requests), requests, 'Cancelled occupancy is retained without provider/graph effects')
                self.assertEqual(self.worker._submission(db, selected), record)
                self.assertIsNone(batch_store._unit_row(db, second.batch_id, 'location'))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM image_group_results').fetchone(), (0,))
                self.assertEqual(retained_inventory(db, ref.execution_id), before)

    async def test_unsent_cancel_and_verified_terminal_attempt_do_not_hold_native_slot(self):
        from backend import portrait_worker as native
        from backend.story_runner import _finish_cancel
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            first, second = await self.start(runtime, ref), await self.start(runtime, ref, key='second')
            async def before_claim(db, job_id, **selectors):
                return submissions.read_anchor_unit_submission(db, job_id,
                    expected_unit_digest=selectors['expected_unit_digest'], expected_wire_digest=selectors['expected_wire_digest'],
                    attempt_id=selectors['attempt_id'])
            with self.preparation(db, first.execution_id), patch.object(native, 'tick_anchor_unit_job', side_effect=before_claim):
                await self.tick(db, first)
            selected = results.read_image_unit_attempt(db, first.execution_id, 'location')
            authorized = self.worker._submission(db, selected)
            assert authorized is not None
            self.assertIsNone(authorized.dispatched_at_ms)
            runtime.cancel(first.execution_id, 'cancel-unsent')
            _finish_cancel(db, first.execution_id)
            with self.preparation(db, second.execution_id):
                await self.worker.tick_image_groups(db, transport=self.server(db), clock_ms=lambda: NOW)
            self.assertEqual(len(self.wires), 1)
            self.assertEqual(self.worker._submission(db, selected), authorized)
            current = results.read_image_unit_attempt(db, second.execution_id, 'location')
            accepted = self.worker._submission(db, current)
            assert accepted is not None
            await native.tick_anchor_unit_job(db, current.job_id, attempt_id=current.attempt_id,
                expected_unit_digest=current.unit_input_digest, expected_wire_digest=accepted.preview.wire_digest,
                expected_revision=accepted.revision, transport=self.server(db), clock_ms=lambda: NOW)
            db.execute("UPDATE execution_work SET status='blocked',blocked_reason='fixture_integrity_block' WHERE work_id=?",
                       (second.work_id,))
            third = await self.start(runtime, ref, key='third')
            with self.preparation(db, third.execution_id):
                await self.worker.tick_image_groups(db, transport=self.server(db), clock_ms=lambda: NOW)
            self.assertEqual(len(self.wires), 2, 'Verified native completion, not graph status, releases occupancy')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM image_group_results').fetchone(), (0,), 'No graph-blocked group promotion')

    async def test_sent_local_failure_retains_slot_and_multiple_legacy_holders_fail_closed(self):
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            first, second = await self.start(runtime, ref), await self.start(runtime, ref, key='second')
            with self.preparation(db, first.execution_id):
                await self.tick(db, first)
            selected = results.read_image_unit_attempt(db, first.execution_id, 'location')
            record = self.worker._submission(db, selected)
            assert record is not None
            submissions.fail_anchor_unit_submission(db, selected.job_id, attempt_id=selected.attempt_id,
                expected_unit_digest=selected.unit_input_digest, expected_wire_digest=record.preview.wire_digest,
                expected_revision=record.revision, reason='deadline_exceeded')
            db.execute("UPDATE execution_work SET status='blocked',blocked_reason='fixture_integrity_block' WHERE work_id=?",
                       (first.work_id,))
            requests = len(self.requests)
            self.assertEqual(await self.worker.tick_image_groups(db, transport=self.server(db), clock_ms=lambda: NOW), 0)
            self.assertEqual(len(self.requests), requests)
            self.assertIsNone(batch_store._unit_row(db, second.batch_id, 'location'))
            # Seed the historical pre-fix two-holder condition through the trusted
            # single-group fixture, not through the corrected scheduling entrypoint.
            with self.preparation(db, second.execution_id):
                await self.tick(db, second)
            requests = len(self.requests)
            with self.assertRaisesRegex(ValueError, 'Multiple unresolved'):
                await self.worker.tick_image_groups(db, transport=self.server(db), clock_ms=lambda: NOW)
            self.assertEqual(len(self.requests), requests, 'Never silently choose a competing native holder')

    async def test_sent_contract_failure_stays_blocked_without_result_retry_or_native_effects(self):
        await self.uncertain_failure('contract_error')

    async def test_sent_deadline_failure_stays_blocked_without_result_retry_or_native_effects(self):
        await self.uncertain_failure('deadline_exceeded')

    async def test_sent_local_failure_returned_by_native_tick_stays_blocked_same_attempt(self):
        await self.uncertain_failure('contract_error', during_tick=True)

    async def uncertain_failure(self, reason, *, during_tick=False):
        from backend import portrait_worker as native
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            before = retained_inventory(db, ref.execution_id)
            receipt = await self.start(runtime, ref)
            ticker = native.tick_anchor_unit_job
            def fail(record):
                return submissions.fail_anchor_unit_submission(db, record.preview.job_id,
                    attempt_id=record.preview.attempt_id, expected_unit_digest=record.preview.unit_input_digest,
                    expected_wire_digest=record.preview.wire_digest, expected_revision=record.revision, reason=reason)
            if during_tick:
                async def local_failure(*args, **kwargs):
                    return fail(await ticker(*args, **kwargs))
                with self.preparation(db, receipt.execution_id), patch.object(native, 'tick_anchor_unit_job', side_effect=local_failure):
                    self.assertEqual(await self.tick(db, receipt), 'blocked')
            else:
                with self.preparation(db, receipt.execution_id):
                    await self.tick(db, receipt)
                selected = results.read_image_unit_attempt(db, receipt.execution_id, 'location')
                accepted = self.worker._submission(db, selected)
                assert accepted is not None
                fail(accepted)
            selected = results.read_image_unit_attempt(db, receipt.execution_id, 'location')
            failed = self.worker._submission(db, selected)
            assert failed is not None and failed.prompt_id is not None and failed.evidence is not None
            self.assertEqual((failed.state, failed.reason, failed.evidence.kind), ('failed', reason, 'prompt_response'))
            requests, changes = len(self.requests), db.total_changes
            with patch.object(comfyui, 'acquire_preparation_context', side_effect=AssertionError('Failed attempt was reprepared')):
                self.assertEqual(await self.tick(db, receipt), 'blocked')
                self.assertEqual(await self.worker.tick_image_groups(db, transport=self.server(db), clock_ms=lambda: NOW), 1)
            self.assertEqual(db.total_changes, changes)
            self.assertEqual(len(self.requests), requests, 'An uncertain failure cannot trigger HTTP or a new paid attempt')
            with self.assertRaises(ValueError):
                results.publish_image_group_result(db, receipt.execution_id, expected_request_digest=receipt.request_digest,
                    status='failed', failed_unit_key='location')
            with self.assertRaises((ValueError, LookupError)):
                await groups.retry_image_execution(db, runtime.saver, self.project, 'no-retry',
                    predecessor_execution_id=receipt.execution_id, expected_result_digest='sha256:' + '0' * 64)
            self.assertEqual(db.total_changes, changes)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM image_group_results').fetchone(), (0,))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM image_group_retry_requests').fetchone(), (0,))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_submission_attempts').fetchone(), (1,))
            self.assertEqual(self.worker._submission(db, selected), failed, 'Native history remains unchanged')
            self.assertEqual(results.read_image_unit_attempt(db, receipt.execution_id, 'location'), selected)
            self.assertEqual(len(self.wires), 1)
            self.assertEqual(retained_inventory(db, ref.execution_id), before)

    async def test_historical_unsafe_failed_result_is_rejected_before_retry_reservation(self):
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            receipt = await self.start(runtime, ref)
            with self.preparation(db, receipt.execution_id):
                await self.tick(db, receipt)
            selected = results.read_image_unit_attempt(db, receipt.execution_id, 'location')
            accepted = self.worker._submission(db, selected)
            assert accepted is not None
            submissions.fail_anchor_unit_submission(db, selected.job_id, attempt_id=selected.attempt_id,
                expected_unit_digest=selected.unit_input_digest, expected_wire_digest=accepted.preview.wire_digest,
                expected_revision=accepted.revision, reason='contract_error')
            # Reproduce a prior publisher's exact unsafe bytes/wake, not a hash or
            # lineage corruption that would independently explain the rejection.
            with patch.object(results, 'is_terminal_image_failure', return_value=True, create=True):
                historical = results.publish_image_group_result(db, receipt.execution_id,
                    expected_request_digest=receipt.request_digest, status='failed', failed_unit_key='location')
            changes, requests = db.total_changes, len(self.requests)
            with self.assertRaises(ValueError):
                results.read_image_group_result(db, receipt.execution_id)
            with self.assertRaises(ValueError):
                await groups.retry_image_execution(db, runtime.saver, self.project, 'no-historical-retry',
                    predecessor_execution_id=receipt.execution_id, expected_result_digest=historical.digest)
            self.assertEqual(db.total_changes, changes)
            self.assertEqual(len(self.requests), requests)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM image_group_retry_requests').fetchone(), (0,))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM image_groups').fetchone(), (1,))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_submission_attempts').fetchone(), (1,))

    async def test_provider_failure_label_without_owned_history_evidence_is_not_retry_authority(self):
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            for key in ('without-history', 'response-only'):
                receipt = await self.start(runtime, ref, key=key)
                with self.preparation(db, receipt.execution_id):
                    await self.tick(db, receipt)
                selected = results.read_image_unit_attempt(db, receipt.execution_id, 'location')
                accepted = self.worker._submission(db, selected)
                assert accepted is not None
                selectors: dict[str, Any] = dict(attempt_id=selected.attempt_id, expected_unit_digest=selected.unit_input_digest,
                                 expected_wire_digest=accepted.preview.wire_digest, expected_revision=accepted.revision)
                with self.assertRaises(ValueError):
                    submissions.fail_anchor_unit_submission(db, selected.job_id, **selectors, reason='provider_failed')
                failed = submissions.fail_anchor_unit_submission(db, selected.job_id, **selectors, reason='contract_error')
                proof = None if key == 'without-history' else failed.acceptance_evidence
                # Historical canonical native facts can have a terminal-looking label
                # even though they lack the native owner's exact history receipt.
                unsafe = type(failed).model_validate({**failed.model_dump(), 'reason': 'provider_failed', 'evidence': proof})
                db.execute('UPDATE portrait_submissions SET submission_digest=?,submission_body=? WHERE attempt_id=?',
                           (submissions._values(unsafe)[3], submissions._values(unsafe)[4], selected.attempt_id))
                with self.subTest(proof=None if proof is None else proof.kind):
                    self.assertEqual(await self.tick(db, receipt), 'blocked')
                    # Exactly this attempt remains nonterminal to the classifier;
                    # multiple fixture holders must also fail closed in the sweep.
                    facts = self.worker._submission(db, selected)
                    assert facts is not None
                    self.assertFalse(results.is_terminal_image_failure(facts))
                    with self.assertRaises(ValueError):
                        results.publish_image_group_result(db, receipt.execution_id,
                            expected_request_digest=receipt.request_digest, status='failed', failed_unit_key='location')
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM image_group_results').fetchone(), (0,))
            self.assertEqual(len(self.wires), 2)

    async def test_verified_native_provider_failure_and_unsent_deadline_support_full_retry(self):
        from backend import portrait_worker as native
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            before = retained_inventory(db, ref.execution_id)
            for mode in ('provider', 'unsent'):
                receipt = await self.start(runtime, ref, key=mode)
                with self.preparation(db, receipt.execution_id):
                    if mode == 'provider':
                        self.fail_keys = {'location'}
                        result = await self.finish(db, receipt)
                    else:
                        async def before_claim(db, job_id, **selectors):
                            return submissions.read_anchor_unit_submission(db, job_id,
                                expected_unit_digest=selectors['expected_unit_digest'],
                                expected_wire_digest=selectors['expected_wire_digest'], attempt_id=selectors['attempt_id'])
                        with patch.object(native, 'tick_anchor_unit_job', side_effect=before_claim):
                            await self.tick(db, receipt)
                        selected = results.read_image_unit_attempt(db, receipt.execution_id, 'location')
                        authorized = self.worker._submission(db, selected)
                        assert authorized is not None
                        deadline = authorized.deadline_ms
                        self.assertEqual(await self.worker.tick_image_group(db, receipt.execution_id,
                            expected_request_digest=receipt.request_digest, transport=self.server(db),
                            clock_ms=lambda: deadline), 'failed')
                        result = results.read_image_group_result(db, receipt.execution_id)
                selected = results.read_image_unit_attempt(db, receipt.execution_id, 'location')
                failed = self.worker._submission(db, selected)
                assert failed is not None
                self.assertTrue(results.is_terminal_image_failure(failed))
                if mode == 'provider':
                    assert failed.evidence is not None and failed.acceptance_evidence is not None
                    self.assertEqual((failed.reason, failed.evidence.kind, failed.evidence.prompt_id),
                                     ('provider_failed', 'history', failed.prompt_id))
                else:
                    self.assertEqual((failed.reason, failed.dispatched_at_ms, failed.evidence), ('deadline_exceeded', None, None))
                self.assertIsNone(self.worker._native_slot(db))
                self.fail_keys.clear()
                retry = await groups.retry_image_execution(db, runtime.saver, self.project, 'retry-' + mode,
                    predecessor_execution_id=receipt.execution_id, expected_result_digest=result.digest)
                with patch.object(comfyui, 'acquire_preparation_context', side_effect=AssertionError('Retry context lookup')):
                    completed = await self.finish(db, retry)
                self.assertEqual(completed.status, 'complete')
                self.assertEqual(completed.body.outputs[0].job_id, selected.job_id)
                self.assertNotEqual(completed.body.outputs[0].attempt_id, selected.attempt_id)
                self.assertEqual(self.worker._submission(db, selected), failed)
            self.assertEqual(len(self.wires), 3, 'Unsent expiry pays nothing; each accepted attempt POSTs once')
            self.assertEqual(retained_inventory(db, ref.execution_id), before)

    async def test_stop_after_preparation_prevents_job_allocation_and_authorization(self):
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            receipt = await self.start(runtime, ref)
            stop = asyncio.Event()
            prepare = batch_store.prepare_saved_batch_unit
            def stopped(*args, **kwargs):
                value = prepare(*args, **kwargs)
                stop.set()
                return value
            with self.preparation(db, receipt.execution_id), patch.object(batch_store, 'prepare_saved_batch_unit', side_effect=stopped):
                self.assertEqual(await self.tick(db, receipt, stop=stop), 'stopped')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_jobs').fetchone(), (0,))
            self.assertEqual(self.wires, {})

    async def test_cancel_post_response_prevents_acceptance_and_next_unit(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            receipt = await self.start(runtime, ref)
            self.hook = lambda request, route: runtime.cancel(receipt.execution_id, 'cancel') if route == 'prompt' else None
            with self.preparation(db, receipt.execution_id):
                self.assertEqual(await self.tick(db, receipt), 'cancelled')
            self.assertEqual(db.execute('SELECT state,prompt_id FROM portrait_submissions').fetchone(), ('dispatching', None))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_jobs').fetchone(), (1,))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_candidates').fetchone(), (0,))

    async def test_failed_first_explicit_retry_allocates_only_failed_turn(self):
        await self.failed_retry('face-0')

    async def test_failed_sheet_retry_retains_both_parents_and_separate_uploads(self):
        await self.failed_retry('sheet-0')

    async def failed_retry(self, key):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            before = retained_inventory(db, ref.execution_id)
            receipt = await self.start(runtime, ref)
            self.fail_keys = {key}
            with self.preparation(db, receipt.execution_id):
                failed = await self.finish(db, receipt)
            self.assertEqual(failed.status, 'failed')
            assert failed.body.failure is not None
            self.assertEqual(failed.body.failure.unit_key, key)
            count = db.execute('SELECT COUNT(*) FROM render_submission_attempts').fetchone()[0]
            retry = await groups.retry_image_execution(db, runtime.saver, self.project, 'retry',
                predecessor_execution_id=receipt.execution_id, expected_result_digest=failed.digest)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_submission_attempts').fetchone(), (count,))
            if key == 'face-0':
                failure = failed.body.failure
                with self.assertRaises(ValueError, msg='Foreign Retry trigger must not poison the accepted turn'):
                    jobs.allocate_anchor_unit_retry(db, failure.job_id, expected_unit_digest=failure.unit_input_digest,
                        previous_attempt_id=failure.attempt_id, expected_previous_wire_digest=failure.wire_digest,
                        expected_previous_revision=failure.revision, retry_trigger_id='sha256:' + '0' * 64)
            self.fail_keys.clear()
            with self.preparation(db, retry.execution_id) as acquire:
                self.assertEqual(await self.tick(db, retry), 'active')
                selected = results.read_image_unit_attempt(db, retry.execution_id, key)
                self.assertNotEqual(selected.attempt_id, failed.body.failure.attempt_id)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM render_submission_attempts').fetchone(), (count + 1,))
                result = await self.finish(db, retry)
            self.assertEqual(result.status, 'complete')
            self.assertEqual(result.body.outputs[:len(failed.body.outputs)], failed.body.outputs)
            self.assertEqual(acquire.call_count, 2 if key == 'face-0' else 0)
            old_job = jobs.read_anchor_unit_job(db, failed.body.failure.job_id,
                expected_unit_digest=failed.body.failure.unit_input_digest, attempt_id=failed.body.failure.attempt_id)
            new_job = jobs.read_anchor_unit_job(db, selected.job_id,
                expected_unit_digest=selected.unit_input_digest, attempt_id=selected.attempt_id)
            self.assertEqual(new_job.prepared_input, old_job.prepared_input)
            self.assertNotEqual(self.wires[old_job.attempt_id], self.wires[new_job.attempt_id])
            self.assertEqual(len(self.wires), 4)
            self.assertEqual(len(self.uploads), 4 if key == 'sheet-0' else 2)
            self.assertEqual(retained_inventory(db, ref.execution_id), before)

    async def test_cancel_during_sheet_upload_stops_receipt_and_prompt(self):
        await self.cancel_sheet('upload/image')

    async def test_cancel_during_sheet_remote_original_get_stops_verification_and_prompt(self):
        await self.cancel_sheet('view')

    async def cancel_sheet(self, point):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            receipt = await self.start(runtime, ref)
            with self.preparation(db, receipt.execution_id):
                for _ in range(4):
                    await self.tick(db, receipt)
                parents = db.execute('SELECT attempt_id,state,candidate_id FROM portrait_submissions ORDER BY rowid').fetchall()
                self.assertEqual([p[1] for p in parents], ['completed', 'completed'])
                self.hook = lambda request, route: runtime.cancel(receipt.execution_id, 'cancel') if route == point else None
                self.assertEqual(await self.tick(db, receipt), 'cancelled')
            transfer = references._stored(db.execute('SELECT * FROM anchor_reference_transfers').fetchone())
            self.assertEqual(transfer.references[0].state, 'dispatching' if point == 'upload/image' else 'received')
            self.assertEqual(transfer.references[0].receipt is None, point == 'upload/image')
            self.assertIsNone(transfer.references[0].verification)
            self.assertEqual(len(self.wires), 2)
            self.assertEqual(db.execute('SELECT attempt_id,state,candidate_id FROM portrait_submissions ORDER BY rowid').fetchall(), parents)

    async def test_contract_block_remains_nonterminal_until_explicit_native_revalidation(self):
        from backend import portrait_worker as native
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            receipt = await self.start(runtime, ref)
            with self.preparation(db, receipt.execution_id):
                await self.tick(db, receipt)
            selected = results.read_image_unit_attempt(db, receipt.execution_id, 'location')
            record = self.worker._submission(db, selected)
            assert record is not None
            blocked = submissions.block_anchor_unit_submission(db, selected.job_id, attempt_id=selected.attempt_id,
                expected_unit_digest=selected.unit_input_digest, expected_wire_digest=record.preview.wire_digest,
                expected_revision=record.revision, reason='contract_error')
            calls = len(self.requests)
            self.assertEqual(await self.tick(db, receipt), 'blocked')
            self.assertEqual(len(self.requests), calls)
            self.assertEqual(self.worker._submission(db, selected), blocked)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM image_group_results').fetchone(), (0,))
            await native.tick_anchor_unit_job(db, selected.job_id, attempt_id=selected.attempt_id,
                expected_unit_digest=selected.unit_input_digest, expected_wire_digest=blocked.preview.wire_digest,
                expected_revision=blocked.revision, revalidate_contract=True, transport=self.server(db), clock_ms=lambda: NOW)
            self.assertEqual(await self.tick(db, receipt), 'complete')
            self.assertEqual(len(self.wires), 1)

    async def test_unknown_acceptance_is_get_only_same_attempt_and_contract_block_needs_explicit_revalidation(self):
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            receipt = await self.start(runtime, ref)
            server = self.server(db)
            def lost(request):
                result = server.handler(request)
                if request.url.path.endswith('/prompt'):
                    raise httpx.ReadError('lost response')
                return result
            with self.preparation(db, receipt.execution_id):
                state = await self.worker.tick_image_group(db, receipt.execution_id,
                    expected_request_digest=receipt.request_digest, transport=httpx.MockTransport(lost), clock_ms=lambda: NOW)
            self.assertEqual(state, 'blocked')
            selected = results.read_image_unit_attempt(db, receipt.execution_id, 'location')
            record = self.worker._submission(db, selected)
            assert record is not None
            self.assertEqual((record.state, record.reason, record.prompt_id), ('blocked', 'acceptance_unknown', None))
            with patch.object(comfyui, 'acquire_preparation_context', side_effect=AssertionError('Replay context')):
                self.assertEqual(await self.tick(db, receipt), 'complete')
            self.assertEqual(len(self.wires), 1)
            self.assertEqual(results.read_image_unit_attempt(db, receipt.execution_id, 'location'), selected)

    async def test_cancel_during_queue_history_view_and_import_prevents_late_promotion(self):
        async with self.source(()) as (runtime, ref, _):
            db = runtime.db
            before = retained_inventory(db, ref.execution_id)
            for point in ('queue', 'history', 'view', 'import'):
                with self.subTest(point=point):
                    receipt = await self.start(runtime, ref, key=point)
                    with self.preparation(db, receipt.execution_id):
                        self.assertEqual(await self.tick(db, receipt), 'active')
                    self.hook = lambda request, route: runtime.cancel(receipt.execution_id, 'cancel') if route.startswith(point) else None
                    if point == 'import':
                        stage = candidates._stage
                        def during_import(*args):
                            value = stage(*args)
                            runtime.cancel(receipt.execution_id, 'cancel')
                            return value
                        with patch.object(candidates, '_stage', side_effect=during_import):
                            self.assertEqual(await self.tick(db, receipt), 'cancelled')
                    else:
                        self.assertEqual(await self.tick(db, receipt), 'cancelled')
                    selected = results.read_image_unit_attempt(db, receipt.execution_id, 'location')
                    record = self.worker._submission(db, selected)
                    assert record is not None
                    self.assertEqual((record.state, record.candidate_id), ('accepted', None))
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_candidates WHERE attempt_id=?',
                                               (selected.attempt_id,)).fetchone(), (0,))
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM image_group_results WHERE group_id=?',
                                               (receipt.group_id,)).fetchone(), (0,))
                    self.hook = None
            self.assertEqual(retained_inventory(db, ref.execution_id), before)

    async def test_preparation_cancel_and_turn_guards_refuse_future_or_unbound_native_effects(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            receipt = await self.start(runtime, ref)
            batch = results.read_image_input_batch(db, receipt.execution_id)
            with self.assertRaises(ValueError):
                batch_store.prepare_saved_batch_unit(db, batch.batch_id, 'location', parent_bindings=[],
                    context=self.context(batch, 'location'))
            with self.preparation(db, receipt.execution_id):
                await self.tick(db, receipt)
            selected = results.read_image_unit_attempt(db, receipt.execution_id, 'face-0')
            record = self.worker._submission(db, selected)
            assert record is not None
            db.execute('DELETE FROM image_unit_attempts WHERE group_id=?', (receipt.group_id,))
            with self.assertRaises(ValueError):
                submissions.block_anchor_unit_submission(db, selected.job_id, attempt_id=selected.attempt_id,
                    expected_unit_digest=selected.unit_input_digest, expected_wire_digest=record.preview.wire_digest,
                    expected_revision=record.revision, reason='history_unavailable')
            db.execute('INSERT INTO image_unit_attempts VALUES (?,?,?,?,?,?)',
                (receipt.group_id, selected.unit_key, selected.job_id, selected.attempt_id,
                 selected.unit_input_digest, selected.origin_execution_id))
            runtime.cancel(receipt.execution_id, 'cancel')
            with self.assertRaises(ValueError):
                submissions.block_anchor_unit_submission(db, selected.job_id, attempt_id=selected.attempt_id,
                    expected_unit_digest=selected.unit_input_digest, expected_wire_digest=record.preview.wire_digest,
                    expected_revision=record.revision, reason='history_unavailable')
            self.assertEqual(self.worker._submission(db, selected), record)

    async def test_real_process_death_prepared_bound_posted_completed_recovers_exact_identity(self):
        async with self.source(()) as (runtime, ref, _):
            before = retained_inventory(runtime.db, ref.execution_id)
            receipts = [(point, await self.start(runtime, ref, key=point))
                        for point in ('prepared', 'bound', 'posted', 'completed')]
        for point, receipt in receipts:
            with self.subTest(point=point):
                command = [sys.executable, '-B', '-c',
                    'from tests.test_image_group_worker import worker_process; import sys; worker_process(*sys.argv[1:])',
                    str(self.root), receipt.execution_id, receipt.request_digest, point]
                child = subprocess.run(command, capture_output=True, timeout=90)
                self.assertEqual(child.returncode, 23, child.stderr.decode())
                with database.open_database(self.root) as db:
                    frozen = db.execute('SELECT input_digest,body FROM batch_unit_input_pins WHERE batch_id=?',
                                        (receipt.batch_id,)).fetchone()
                    self.assertIsNotNone(frozen)
                    journal = self.root / 'native-fixture.json'
                    provider: Any = json.loads(journal.read_text()) if journal.exists() else dict(wires={}, uploads=[])
                    self.wires = provider['wires']
                    self.uploads = {name: png() for name in provider['uploads']}
                    with patch.object(comfyui, 'acquire_preparation_context', side_effect=AssertionError('Restart context')), \
                            patch('backend.comfyui_workflows.secrets.randbelow', side_effect=AssertionError('Restart RNG')):
                        result = await self.finish(db, receipt)
                    self.assertEqual(db.execute('SELECT input_digest,body FROM batch_unit_input_pins WHERE batch_id=?',
                                                (receipt.batch_id,)).fetchone(), frozen)
                    self.assertEqual([o.unit_key for o in result.body.outputs], ['location'])
                    self.assertEqual(retained_inventory(db, ref.execution_id), before)

    async def test_real_restart_after_each_parent_and_sheet_binding_receipt_reuses_exact_pins(self):
        async with self.source() as (runtime, ref, _):
            before = retained_inventory(runtime.db, ref.execution_id)
            receipt = await self.start(runtime, ref)
        frozen = []
        for point, keys in (('face-completed', ['face-0']), ('location-completed', ['face-0', 'location']),
                            ('sheet-bound', ['face-0', 'location', 'sheet-0']),
                            ('sheet-receipt', ['face-0', 'location', 'sheet-0'])):
            child = subprocess.run([sys.executable, '-B', '-c',
                'from tests.test_image_group_worker import worker_process; import sys; worker_process(*sys.argv[1:])',
                str(self.root), receipt.execution_id, receipt.request_digest, point], capture_output=True, timeout=120)
            self.assertEqual(child.returncode, 23, child.stderr.decode())
            with database.open_database(self.root) as db:
                current = db.execute('SELECT unit_key,input_digest,body FROM batch_unit_input_pins ORDER BY rowid').fetchall()
                self.assertEqual(current[:len(frozen)], frozen)
                frozen = current
                self.assertEqual([row[0] for row in current], keys)
                self.assertEqual(retained_inventory(db, ref.execution_id), before)
        with database.open_database(self.root) as db:
            provider = json.loads((self.root / 'native-fixture.json').read_text())
            self.wires = provider['wires']
            self.uploads = {name: png() for name in provider['uploads']}
            self.assertEqual((len(self.wires), len(self.uploads)), (2, 1))
            with patch.object(comfyui, 'acquire_preparation_context', side_effect=AssertionError('Prepared sheet context')), \
                    patch('backend.comfyui_workflows.secrets.randbelow', side_effect=AssertionError('Prepared sheet RNG')):
                result = await self.finish(db, receipt)
            self.assertEqual([o.unit_key for o in result.body.outputs], ['face-0', 'location', 'sheet-0'])
            self.assertEqual((len(self.wires), len(self.uploads)), (3, 2))
            self.assertEqual(db.execute('SELECT unit_key,input_digest,body FROM batch_unit_input_pins ORDER BY rowid').fetchall(), frozen)


def worker_process(root, execution, digest, point):
    """Real abrupt termination at worker-owned coordination windows, not exceptions."""
    from backend import image_group_worker as worker
    root = Path(root)
    fixture = ImageGroupWorkerTests()
    fixture.wires, fixture.uploads, fixture.requests, fixture.fail_keys, fixture.hook = {}, {}, [], set(), None
    journal = root / 'native-fixture.json'
    if journal.exists():
        provider = json.loads(journal.read_text())
        fixture.wires = provider['wires']
        fixture.uploads = {name: png() for name in provider['uploads']}
    with database.open_database(root) as db:
        batch = results.read_image_input_batch(db, execution)
        async def context(connection, workflow, **kwargs):
            key = next(u.unit_key for u in batch.prepared_input.ordered_units
                       if pins.generation._unit(batch.prepared_input, u.unit_key)[2].workflow_id == workflow)
            return fixture.context(batch, key)
        original_server = fixture.server(db)
        def server(request):
            value = original_server.handler(request)
            if request.method == 'POST':
                journal.write_text(json.dumps(dict(wires=fixture.wires, uploads=list(fixture.uploads))))
                if point == 'posted':
                    os._exit(23)
            return value
        target = {'prepared': 'backend.render_job_store.create_anchor_unit_job',
                  'bound': 'backend.portrait_submission_store.authorize_anchor_unit_submission',
                  'completed': 'backend.portrait_submission_store.complete_anchor_unit_submission',
                  'face-completed': 'backend.portrait_submission_store.complete_anchor_unit_submission',
                  'location-completed': 'backend.portrait_submission_store.complete_anchor_unit_submission',
                  'sheet-bound': 'backend.anchor_reference_store.authorize_anchor_reference_transfer',
                  'sheet-receipt': 'backend.anchor_reference_store.record_anchor_reference_receipt'}.get(point)
        complete = submissions.complete_anchor_unit_submission
        receipt = references.record_anchor_reference_receipt
        def die(*args, **kwargs):
            if point.endswith('completed'):
                value = complete(*args, **kwargs)
                if point != 'completed' and value.preview.job_id != db.execute('SELECT job_id FROM render_jobs WHERE unit_key=?',
                    ('face-0' if point == 'face-completed' else 'location',)).fetchone()[0]:
                    return value
            elif point == 'sheet-receipt':
                receipt(*args, **kwargs)
            os._exit(23)
        async def run():
            for _ in range(10):
                await worker.tick_image_group(db, execution, expected_request_digest=digest,
                    transport=httpx.MockTransport(server), clock_ms=lambda: NOW)
        with patch.object(comfyui, 'acquire_preparation_context', side_effect=context):
            if target:
                with patch(target, side_effect=die):
                    asyncio.run(run())
            else:
                asyncio.run(run())
    raise AssertionError('Crash window was not reached')
