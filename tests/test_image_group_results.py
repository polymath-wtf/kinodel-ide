"""7.2 storage only: real pins/media/SQLite, no scheduling or provider calls."""

import importlib.util
import io
import sqlite3
import subprocess
import sys
from typing import Any, Literal
import unittest
from unittest.mock import patch

from backend import batch_store, database, image_group_store as groups
from backend import anchor_reference_store as refs, portrait_candidate_store as candidates
from backend import portrait_submission_store as submissions, render_job_store as jobs
from backend.domain import canonical_json, sha256_digest
from backend.saver import open_saver
from tests import test_batch_store as pins, test_image_group_store as admission
from tests import test_anchor_parent_resolver as parents
from tests import test_story_wardrobe_api as fixtures
from tests.test_portrait_candidate_store import png
from tests.test_story_wardrobe_runtime import retained_inventory


class ImageGroupResultTests(fixtures.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    source: Any = admission.ImageGroupStoreTests.source
    arguments: Any = admission.ImageGroupStoreTests.arguments
    context: Any = pins.BatchStoreTests.context
    offline: Any = pins.BatchStoreTests.offline
    complete: Any = parents.AnchorParentResolverTests.complete

    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('backend.image_group_results'), 'Group result storage is missing')
        from backend import image_group_results
        self.results = image_group_results
        self.store = groups
        self.refs = refs
        self.profile = pins.production_catalog()['image_only']['profiles'][0]['pin']

    async def start(self, runtime, ref, key='images'):
        return await groups.start_image_execution(runtime.db, runtime.saver, self.project, key,
            **self.arguments(ref, image_size=dict(width=512, height=512)))

    def unit(self, db, execution, index, *, finish='completed', job=None, bad_parents=False):
        group = groups.read_image_group(db, execution)
        root = self.results.read_image_input_batch(db, execution)
        planned = group.batch.prepared_input.ordered_units[index]
        bindings = []
        for reference in planned.references:
            parent = self.results.read_image_unit_attempt(db, execution, reference.source.unit_key)
            row = submissions._row(db, parent.job_id, parent.attempt_id)
            assert row is not None
            candidate = candidates.read_anchor_unit_candidate(db, row[8], expected_unit_digest=parent.unit_input_digest)
            bindings.append(dict(unit_key=reference.source.unit_key, source_id=candidate.candidate_id,
                digest=candidate.digest, input_name='parents/' + reference.role + '.png'))
        if bad_parents:
            bindings[0]['source_id'] = bindings[1]['source_id']
        unit = batch_store.prepare_saved_batch_unit(db, root.batch_id, planned.unit_key,
            parent_bindings=bindings, context=self.context(root, planned.unit_key), seed=42)
        if job is None:
            job = jobs.create_anchor_unit_job(db, root.batch_id, planned.unit_key,
                expected_unit_digest=unit.input_digest, parent_bindings=bindings)
        binding = self.results.bind_image_unit_attempt(db, execution, planned.unit_key,
            expected_request_digest=group.receipt.request_digest, expected_unit_digest=unit.input_digest,
            job_id=job.job_id, attempt_id=job.attempt_id)
        if job.kind == 'sheet':
            preview = refs.preview_anchor_reference_intent(db, job.job_id, expected_project_id=self.project,
                expected_unit_digest=unit.input_digest, attempt_id=job.attempt_id)
            selectors = dict(expected_project_id=self.project, expected_unit_digest=unit.input_digest,
                             expected_intent_digest=preview.intent_digest, attempt_id=job.attempt_id)
            record = refs.authorize_anchor_reference_transfer(db, job.job_id, **selectors)
            for role in ('portrait', 'background'):
                record = refs.claim_anchor_reference_upload(db, job.job_id, role=role, **selectors,
                                                           expected_revision=record.revision)
                item = record.intent.references[0 if role == 'portrait' else 1]
                record = refs.record_anchor_reference_receipt(db, job.job_id, role=role, **selectors,
                    expected_revision=record.revision, receipt=dict(name=item.name, subfolder=item.subfolder, type='input'))
                receipt = record.references[0 if role == 'portrait' else 1].receipt
                assert receipt is not None
                record = refs.verify_anchor_reference_remote(db, job.job_id, role=role, **selectors,
                    expected_revision=record.revision, expected_receipt_digest=receipt.digest,
                    remote_digest=item.parent.digest, source_digest=item.parent.digest, byte_length=item.parent.byte_length)
            refs.finalize_anchor_references(db, job.job_id, **selectors, expected_revision=record.revision)
        candidate = candidates.import_anchor_unit_candidate(db, job.job_id, job.attempt_id,
            expected_unit_digest=unit.input_digest, descriptor=dict(node_id='494' if job.kind == 'sheet' else '865',
                history_key='images', index=0, filename=planned.unit_key + '.png', subfolder='', type='output',
                mime_type='image/png'), stream=io.BytesIO(png()))
        # A sent contract/deadline stop is not terminal group failure. Storage
        # fixtures attest an owned native-history provider failure instead; the
        # shared standalone parent fixture deliberately keeps its old behavior.
        record = self.complete(db, job, unit, candidate, through='accepted' if finish == 'failed' else finish)
        if finish == 'failed':
            assert record.acceptance_evidence is not None
            proof = {**record.acceptance_evidence.model_dump(), 'kind': 'history',
                     'digest': sha256_digest(b'fixture owned native provider failure')}
            record = submissions.fail_anchor_unit_submission(db, job.job_id, attempt_id=job.attempt_id,
                expected_unit_digest=unit.input_digest, expected_wire_digest=record.preview.wire_digest,
                expected_revision=record.revision, reason='provider_failed', evidence=proof)
        return binding, job, candidate, record

    def publish(self, db, receipt, *, status: Literal['complete', 'failed'] = 'complete', failed_unit_key=None):
        return self.results.publish_image_group_result(db, receipt.execution_id,
            expected_request_digest=receipt.request_digest, status=status, failed_unit_key=failed_unit_key)

    def bind_wait(self, db, receipt):
        return groups.bind_image_wait(db, receipt.execution_id, receipt.wait_id,
            expected_request_digest=receipt.request_digest, checkpoint_id='cp-' + receipt.group_id,
            task_id='task', interrupt_id='interrupt')

    def join(self, db, receipt, result):
        return self.results.join_image_group_result(db, receipt.execution_id, wait_id=receipt.wait_id,
            result_id=result.result_id, expected_result_digest=result.digest,
            expected_request_digest=receipt.request_digest)

    async def retry(self, runtime, receipt, result, key='retry', **changes):
        args = dict(predecessor_execution_id=receipt.execution_id, expected_result_digest=result.digest)
        args.update(changes)
        return await groups.retry_image_execution(runtime.db, runtime.saver, self.project, key, **args)

    async def test_full_manifest_early_result_exact_wake_and_offline_idempotent_join(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            before = retained_inventory(db, ref.execution_id)
            receipt = await self.start(runtime, ref)
            records = [self.unit(db, receipt.execution_id, i) for i in range(3)]
            result = self.publish(db, receipt)
            self.assertEqual(result.status, 'complete')
            self.assertEqual([o.unit_key for o in result.body.outputs], ['face-0', 'location', 'sheet-0'])
            self.assertEqual([o.attempt_id for o in result.body.outputs], [r[1].attempt_id for r in records])
            self.assertEqual(result.body.outputs[2].parent_bindings[0].source_id, records[0][2].candidate_id)
            self.assertEqual((self.root / result.uri.removeprefix('kinodel://')).read_bytes(), canonical_json(result.body))
            self.assertIsNone(db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                        (receipt.execution_id,)).fetchone())
            self.assertEqual(db.execute("SELECT source_id,resume_ref,payload_digest,status FROM execution_work "
                "WHERE execution_id=? AND kind='resume'", (receipt.execution_id,)).fetchall(),
                [(receipt.wait_id, result.result_id, result.digest, 'pending')])
            self.assertIsNone(self.results.read_image_group_wake(db, receipt.execution_id))
            with self.assertRaises(ValueError):
                self.join(db, receipt, result)
            self.bind_wait(db, receipt)
            wake = self.results.read_image_group_wake(db, receipt.execution_id)
            assert wake is not None
            self.assertEqual((wake.source_id, wake.resume_ref, wake.payload_digest),
                             (receipt.wait_id, result.result_id, result.digest))
            joined = self.join(db, receipt, result)
            self.assertEqual(joined.batch_outputs, result.result_id)
            self.assertEqual(joined.status, 'complete')
            self.assertEqual(retained_inventory(db, ref.execution_id), before)
        with database.open_database(self.root) as db, self.offline():
            changes = db.total_changes
            self.assertEqual(self.publish(db, receipt), result)
            self.assertEqual(self.join(db, receipt, result), joined)
            self.assertEqual(self.results.read_image_group_result(db, receipt.execution_id), result)
            self.assertEqual(db.total_changes, changes)

    async def test_partial_blocked_foreign_binding_and_changed_dependency_fail_closed(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            receipt = await self.start(runtime, ref)
            first, job, candidate, blocked = self.unit(db, receipt.execution_id, 0, finish='blocked')
            for status in ('complete', 'failed'):
                with self.assertRaises(ValueError):
                    self.publish(db, receipt, status=status, failed_unit_key='face-0' if status == 'failed' else None)
            with self.assertRaises(ValueError):
                self.unit(db, receipt.execution_id, 1)
            other = await self.start(runtime, ref, key='foreign')
            with self.assertRaises(ValueError):
                self.results.bind_image_unit_attempt(db, other.execution_id, 'face-0',
                    expected_request_digest=other.request_digest, expected_unit_digest=first.unit_input_digest,
                    job_id=job.job_id, attempt_id=job.attempt_id)
            selectors: dict[str, Any] = dict(expected_unit_digest=first.unit_input_digest, expected_wire_digest=blocked.preview.wire_digest,
                             expected_revision=blocked.revision)
            assert blocked.acceptance_evidence is not None
            proof = blocked.acceptance_evidence.model_dump()
            submissions.complete_anchor_unit_submission(db, job.job_id, **selectors,
                candidate_id=candidate.candidate_id, evidence={**proof, 'kind': 'history'})
            self.unit(db, receipt.execution_id, 1)
            with self.assertRaises(ValueError):
                self.unit(db, receipt.execution_id, 2, bad_parents=True)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM image_group_results').fetchone(), (0,))

    async def test_binding_duplicate_stale_attempt_and_cancelled_origin_guard(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            receipt = await self.start(runtime, ref)
            binding, job, _, _ = self.unit(db, receipt.execution_id, 0)
            args = dict(expected_request_digest=receipt.request_digest, expected_unit_digest=binding.unit_input_digest,
                        job_id=job.job_id, attempt_id=job.attempt_id)
            changes = db.total_changes
            self.assertEqual(self.results.bind_image_unit_attempt(db, receipt.execution_id, binding.unit_key, **args), binding)
            self.assertEqual(db.total_changes, changes)
            for key in ('job_id', 'attempt_id', 'expected_unit_digest', 'expected_request_digest'):
                with self.subTest(key=key), self.assertRaises((ValueError, LookupError)):
                    self.results.bind_image_unit_attempt(db, receipt.execution_id, binding.unit_key,
                        **{**args, key: 'sha256:' + '0' * 64})
            self.results.assert_image_attempt_writable(db, job.job_id, job.attempt_id)
            db.execute("INSERT INTO execution_controls VALUES (?,'cancel','cancel',?,NULL)",
                       (receipt.execution_id, receipt.work_id))
            with self.assertRaises(ValueError):
                self.results.assert_image_attempt_writable(db, job.job_id, job.attempt_id)
            self.assertEqual(self.results.read_image_unit_attempt(db, receipt.execution_id, binding.unit_key), binding)
            with self.assertRaises(ValueError):
                self.unit(db, receipt.execution_id, 1)

    async def test_failed_retry_before_old_wake_root_pins_success_lineage_and_atomic_acceptance(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            initial = await self.start(runtime, ref)
            retained, _, _, _ = self.unit(db, initial.execution_id, 0)
            failed, job, _, facts = self.unit(db, initial.execution_id, 1, finish='failed')
            result = self.publish(db, initial, status='failed', failed_unit_key='location')
            with self.offline():
                retry = await self.retry(runtime, initial, result)
            self.assertIsNone(groups.read_image_group(db, initial.execution_id).checkpoint_id)
            self.assertIsNone(db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                        (initial.execution_id,)).fetchone())
            self.assertNotEqual((retry.execution_id, retry.group_id, retry.wait_id, retry.batch_id),
                                (initial.execution_id, initial.group_id, initial.wait_id, initial.batch_id))
            root = self.results.read_image_input_batch(db, retry.execution_id)
            self.assertEqual(root, groups.read_image_group(db, initial.execution_id).batch)
            handoff = groups.read_image_group(db, retry.execution_id).batch.prepared_input.model_dump()
            self.assertEqual({**handoff, 'activation_id': initial.activation_id}, root.prepared_input.model_dump())
            self.assertEqual(self.results.read_image_unit_attempt(db, retry.execution_id, 'face-0'), retained)
            for key in ('location', 'sheet-0'):
                with self.assertRaises(LookupError):
                    self.results.read_image_unit_attempt(db, retry.execution_id, key)
            changes = db.total_changes
            with self.offline():
                self.assertEqual(await self.retry(runtime, initial, result), retry)
            self.assertEqual(db.total_changes, changes)
            with self.assertRaises(ValueError):
                await self.start(runtime, ref, key='retry')
            with self.assertRaises(ValueError):
                await self.retry(runtime, initial, result, expected_result_digest='sha256:' + '0' * 64)
            allocated = jobs.allocate_anchor_unit_retry(db, job.job_id, expected_unit_digest=failed.unit_input_digest,
                previous_attempt_id=job.attempt_id, expected_previous_wire_digest=facts.preview.wire_digest,
                expected_previous_revision=facts.revision, retry_trigger_id=retry.group_id)
            selected, _, _, _ = self.unit(db, retry.execution_id, 1, job=allocated, finish='failed')
            self.assertEqual(selected.origin_execution_id, retry.execution_id)
            second_result = self.publish(db, retry, status='failed', failed_unit_key='location')
            second = await self.retry(runtime, retry, second_result, key='retry-2')
            self.assertEqual(self.results.read_image_input_batch(db, second.execution_id), root)
            self.assertEqual(self.results.read_image_unit_attempt(db, second.execution_id, 'face-0'), retained)
            self.bind_wait(db, initial)
            failed_join = self.join(db, initial, result)
            self.assertEqual((failed_join.status, failed_join.batch_outputs), ('failed', None))
            self.assertIsNone(self.results.read_image_group_wake(db, second.execution_id))
            self.assertEqual(db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                        (initial.execution_id,)).fetchone(), ('failed',))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_jobs').fetchone(), (2,))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_submission_attempts').fetchone(), (3,))

    async def test_competing_retry_key_conflicts_before_admission_same_key_and_later_chain_remain_valid(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            initial = await self.start(runtime, ref)
            failed, job, _, facts = self.unit(db, initial.execution_id, 0, finish='failed')
            result = self.publish(db, initial, status='failed', failed_unit_key='face-0')
            first = await self.retry(runtime, initial, result, key='first')
            before = db.total_changes
            with self.assertRaises(ValueError, msg='A failed result can accept only one Retry owner/key'):
                await self.retry(runtime, initial, result, key='competing')
            self.assertEqual(db.total_changes, before)
            self.assertEqual(await self.retry(runtime, initial, result, key='first'), first)
            self.assertEqual(db.total_changes, before)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM image_group_retry_requests').fetchone(), (1,))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_submission_attempts').fetchone(), (1,))
            allocated = jobs.allocate_anchor_unit_retry(db, job.job_id, expected_unit_digest=failed.unit_input_digest,
                previous_attempt_id=job.attempt_id, expected_previous_wire_digest=facts.preview.wire_digest,
                expected_previous_revision=facts.revision, retry_trigger_id=first.group_id)
            self.unit(db, first.execution_id, 0, job=allocated, finish='failed')
            next_result = self.publish(db, first, status='failed', failed_unit_key='face-0')
            count = db.execute('SELECT COUNT(*) FROM render_submission_attempts').fetchone()
            successor = await self.retry(runtime, first, next_result, key='later-failed-successor')
            self.assertNotEqual(successor.execution_id, first.execution_id)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM image_group_retry_requests').fetchone(), (2,))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_submission_attempts').fetchone(), count)

    async def test_reserved_retry_fences_competing_key_before_publication_and_same_key_recovers(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            initial = await self.start(runtime, ref)
            self.unit(db, initial.execution_id, 0, finish='failed')
            result = self.publish(db, initial, status='failed', failed_unit_key='face-0')
            with patch.object(groups, '_pin_retry_handoff', side_effect=OSError('reserved owner before publication')):
                with self.assertRaises(OSError):
                    await self.retry(runtime, initial, result, key='reserved-first')
            execution = groups._identities(self.project, 'reserved-first')[1]
            reserved = groups._retry_row(db, execution)
            self.assertEqual(reserved[8], 'reserved')
            before = db.total_changes
            with self.assertRaises(ValueError, msg='A reserved Retry already owns the predecessor/result'):
                await self.retry(runtime, initial, result, key='competing')
            self.assertEqual(db.total_changes, before)
            self.assertEqual(groups._retry_row(db, execution), reserved)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM image_group_retry_requests').fetchone(), (1,))
            recovered = await self.retry(runtime, initial, result, key='reserved-first')
            self.assertEqual(recovered.execution_id, execution)
            self.assertEqual(groups._retry_row(db, execution)[8], 'accepted')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_submission_attempts').fetchone(), (1,))

    async def test_historical_retry_reader_rejects_competing_reserved_and_accepted_owners_without_choosing(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            initial = await self.start(runtime, ref)
            self.unit(db, initial.execution_id, 0, finish='failed')
            result = self.publish(db, initial, status='failed', failed_unit_key='face-0')
            first = await self.retry(runtime, initial, result, key='first')
            request = groups._read_retry_request(db, first.execution_id)
            assert request is not None
            competing = request.model_copy(update=dict(client_key='historical-competitor',
                execution_id=groups._identities(self.project, 'historical-competitor')[1]))
            db.execute('INSERT INTO image_group_retry_requests VALUES (?,?,?,?,?,?,?,?,?)',
                       (*groups._retry_values(competing), 'reserved'))
            for state in ('reserved', 'accepted'):
                db.execute('UPDATE image_group_retry_requests SET acceptance_state=? WHERE execution_id=?',
                           (state, competing.execution_id))
                before = db.total_changes
                with self.subTest(state=state), self.assertRaises(ValueError):
                    groups.read_image_group(db, first.execution_id)
                self.assertEqual(db.total_changes, before)
            self.assertEqual(self.results.read_image_group_result(db, initial.execution_id), result)

    async def test_cancel_during_publication_prevents_visible_result_wake_and_retry(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            receipt = await self.start(runtime, ref)
            self.unit(db, receipt.execution_id, 0, finish='failed')
            publish = batch_store._publish_body
            def cancel(path, body):
                self.assertFalse(db.in_transaction)
                publish(path, body)
                db.execute("INSERT INTO execution_controls VALUES (?,'cancel','cancel',?,NULL)",
                           (receipt.execution_id, receipt.work_id))
            with patch.object(batch_store, '_publish_body', side_effect=cancel), self.assertRaises(ValueError):
                self.publish(db, receipt, status='failed', failed_unit_key='face-0')
            self.assertEqual(db.execute('SELECT publication_state FROM image_group_results').fetchone(), ('reserved',))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_work WHERE execution_id=? AND kind='resume'",
                                        (receipt.execution_id,)).fetchone(), (0,))
            with self.assertRaises(LookupError):
                self.results.read_image_group_result(db, receipt.execution_id)
            with self.assertRaises((ValueError, LookupError)):
                await groups.retry_image_execution(db, runtime.saver, self.project, 'retry',
                    predecessor_execution_id=receipt.execution_id, expected_result_digest='sha256:' + '0' * 64)

    async def test_retry_reservation_fences_story_key_before_any_publication_and_acceptance_is_atomic(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            initial = await self.start(runtime, ref)
            self.unit(db, initial.execution_id, 0, finish='failed')
            result = self.publish(db, initial, status='failed', failed_unit_key='face-0')
            with patch.object(groups, '_pin_retry_handoff', side_effect=OSError('before publication')):
                with self.assertRaises(OSError):
                    await self.retry(runtime, initial, result)
            with self.assertRaisesRegex(ValueError, 'client key conflicts'):
                await runtime.start(self.project, 'retry', 'competing text', ['s1'])
            with self.assertRaises(ValueError):
                await self.start(runtime, ref, key='retry')
            db.set_authorizer(lambda action, *args: sqlite3.SQLITE_DENY
                if action == sqlite3.SQLITE_UPDATE and args[0] == 'image_group_retry_requests' else sqlite3.SQLITE_OK)
            try:
                with self.assertRaises(sqlite3.DatabaseError):
                    await self.retry(runtime, initial, result)
            finally:
                db.set_authorizer(None)
            self.assertIsNone(db.execute("SELECT execution_id FROM executions WHERE client_key='retry'").fetchone())
            self.assertEqual(db.execute('SELECT acceptance_state FROM image_group_retry_requests').fetchone(), ('reserved',))
            with self.offline():
                retry = await self.retry(runtime, initial, result)
            self.assertEqual(db.execute('SELECT acceptance_state FROM image_group_retry_requests').fetchone(), ('accepted',))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM image_groups WHERE execution_id=?',
                                        (retry.execution_id,)).fetchone(), (1,))

    async def test_candidate_corruption_and_result_or_wake_conflicts_never_heal(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            receipt = await self.start(runtime, ref)
            all_units = [self.unit(db, receipt.execution_id, i) for i in range(3)]
            candidate = all_units[0][2]
            path = self.root / candidate.uri.removeprefix('kinodel://')
            original = path.read_bytes()
            path.write_bytes(b'not original')
            with self.assertRaises(ValueError):
                self.publish(db, receipt)
            path.write_bytes(original)
            result = self.publish(db, receipt)
            with self.assertRaises(ValueError):
                self.publish(db, receipt, status='failed', failed_unit_key='face-0')
            db.execute("UPDATE execution_work SET resume_ref='foreign' WHERE execution_id=? AND kind='resume'",
                       (receipt.execution_id,))
            with self.assertRaises(ValueError):
                self.results.read_image_group_result(db, receipt.execution_id)
            db.execute("UPDATE execution_work SET resume_ref=? WHERE execution_id=? AND kind='resume'",
                       (result.result_id, receipt.execution_id))
            result_path = self.root / result.uri.removeprefix('kinodel://')
            result_path.unlink()
            with self.assertRaises(FileNotFoundError):
                self.publish(db, receipt)
            self.assertFalse(result_path.exists())

    async def test_failed_sheet_retry_complete_retains_exact_parents_and_old_wake_cannot_join(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            initial = await self.start(runtime, ref)
            original = [self.unit(db, initial.execution_id, i,
                        finish='failed' if i == 2 else 'completed') for i in range(3)]
            result = self.publish(db, initial, status='failed', failed_unit_key='sheet-0')
            self.bind_wait(db, initial)
            self.join(db, initial, result)
            retry = await self.retry(runtime, initial, result)
            failed, job, _, facts = original[2]
            allocated = jobs.allocate_anchor_unit_retry(db, job.job_id, expected_unit_digest=failed.unit_input_digest,
                previous_attempt_id=job.attempt_id, expected_previous_wire_digest=facts.preview.wire_digest,
                expected_previous_revision=facts.revision, retry_trigger_id=retry.group_id)
            selected, _, _, _ = self.unit(db, retry.execution_id, 2, job=allocated)
            complete = self.publish(db, retry)
            self.bind_wait(db, retry)
            with self.assertRaises(ValueError):
                self.join(db, retry, result)
            joined = self.join(db, retry, complete)
            self.assertEqual(joined.batch_outputs, complete.result_id)
            for output, (binding, _, candidate, _) in zip(complete.body.outputs[:2], original[:2], strict=True):
                self.assertEqual((output.candidate_id, output.attempt_id, output.origin_execution_id),
                                 (candidate.candidate_id, binding.attempt_id, initial.execution_id))
            self.assertEqual(complete.body.outputs[2].attempt_id, selected.attempt_id)
            self.assertEqual(complete.body.input_batch_id, initial.batch_id)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_jobs').fetchone(), (3,))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_submission_attempts').fetchone(), (4,))
            self.assertEqual(self.results.read_image_group_result(db, initial.execution_id), result)
            with self.assertRaises(ValueError):
                await self.retry(runtime, retry, complete, key='not-failed')

    async def test_cancelled_result_cannot_join_or_authorize_retry_and_occ_rechecks_after_io(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            initial = await self.start(runtime, ref)
            self.unit(db, initial.execution_id, 0, finish='failed')
            result = self.publish(db, initial, status='failed', failed_unit_key='face-0')
            self.bind_wait(db, initial)
            publish = batch_store._publish_body
            def cancel(path, body):
                publish(path, body)
                db.execute("INSERT INTO execution_controls VALUES (?,'cancel','cancel',?,NULL)",
                           (initial.execution_id, initial.work_id))
            with patch.object(batch_store, '_publish_body', side_effect=cancel), self.assertRaises(ValueError):
                await self.retry(runtime, initial, result)
            self.assertEqual(db.execute('SELECT acceptance_state FROM image_group_retry_requests').fetchone(), ('reserved',))
            self.assertIsNone(db.execute("SELECT execution_id FROM executions WHERE client_key='retry'").fetchone())
            with self.assertRaises(ValueError):
                self.join(db, initial, result)
            with self.assertRaises(ValueError):
                await self.retry(runtime, initial, result)
            self.assertEqual(self.results.read_image_group_result(db, initial.execution_id), result)

    async def test_result_occ_drift_after_publication_keeps_reservation_and_no_visible_wake(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            initial = await self.start(runtime, ref)
            self.unit(db, initial.execution_id, 0, finish='failed')
            publish = batch_store._publish_body
            def drift(path, body):
                publish(path, body)
                db.execute('UPDATE image_groups SET request_digest=? WHERE execution_id=?',
                           ('sha256:' + '0' * 64, initial.execution_id))
            with patch.object(batch_store, '_publish_body', side_effect=drift), self.assertRaisesRegex(ValueError, 'changed before commit'):
                self.publish(db, initial, status='failed', failed_unit_key='face-0')
            self.assertEqual(db.execute('SELECT publication_state FROM image_group_results').fetchone(), ('reserved',))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_work WHERE execution_id=? AND kind='resume'",
                                        (initial.execution_id,)).fetchone(), (0,))
            db.execute('UPDATE image_groups SET request_digest=? WHERE execution_id=?',
                       (initial.request_digest, initial.execution_id))
            with self.offline():
                result = self.publish(db, initial, status='failed', failed_unit_key='face-0')
            self.assertEqual(self.results.read_image_group_result(db, initial.execution_id), result)

    async def test_real_process_death_result_reserve_publish_atomic_wake_commit(self):
        async with self.source() as (runtime, ref, _):
            receipts = []
            for phase in ('reserve', 'publish', 'before-commit', 'after-commit'):
                receipt = await self.start(runtime, ref, key=phase)
                self.unit(runtime.db, receipt.execution_id, 0, finish='failed')
                receipts.append(receipt)
        child = '''
import os, sqlite3, sys
from pathlib import Path
from backend import batch_store, database, image_group_results
phase = sys.argv[2]
connect = sqlite3.connect
class Crash(sqlite3.Connection):
    wake = False
    def execute(self, sql, *args, **kwargs):
        result = super().execute(sql, *args, **kwargs)
        if sql.startswith('INSERT INTO execution_work') and "'resume'" in sql:
            self.wake = True
            if phase == 'before-commit': os._exit(23)
        if sql == 'COMMIT' and self.wake and phase == 'after-commit': os._exit(23)
        return result
sqlite3.connect = lambda *a, **kw: connect(*a, **kw, factory=Crash)
publish = batch_store._publish_body
def die(path, body):
    if phase == 'publish': publish(path, body)
    os._exit(23)
if phase in ('reserve', 'publish'): batch_store._publish_body = die
with database.open_database(Path(sys.argv[1])) as db:
    image_group_results.publish_image_group_result(db, sys.argv[3], expected_request_digest=sys.argv[4],
        status='failed', failed_unit_key='face-0')
'''
        for phase, receipt in zip(('reserve', 'publish', 'before-commit', 'after-commit'), receipts, strict=True):
            with self.subTest(phase=phase):
                run = subprocess.run([sys.executable, '-B', '-c', child, str(self.root), phase,
                    receipt.execution_id, receipt.request_digest], capture_output=True, text=True, timeout=45)
                self.assertEqual(run.returncode, 23, run.stderr)
                with database.open_database(self.root) as db, self.offline():
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_work WHERE execution_id=? AND kind='resume'",
                        (receipt.execution_id,)).fetchone(), (int(phase == 'after-commit'),))
                    result = self.publish(db, receipt, status='failed', failed_unit_key='face-0')
                    changes = db.total_changes
                    self.assertEqual(self.publish(db, receipt, status='failed', failed_unit_key='face-0'), result)
                    self.assertEqual(db.total_changes, changes)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_work WHERE execution_id=? AND kind='resume'",
                        (receipt.execution_id,)).fetchone(), (1,))

    async def test_real_process_death_retry_handoff_and_acceptance_never_become_ordinary_start(self):
        async with self.source() as (runtime, ref, _):
            initial = await self.start(runtime, ref)
            self.unit(runtime.db, initial.execution_id, 0, finish='failed')
            result = self.publish(runtime.db, initial, status='failed', failed_unit_key='face-0')
        child = '''
import asyncio, os, sqlite3, sys
from pathlib import Path
from backend import batch_store, database, image_group_store
from backend.saver import open_saver
phase = sys.argv[2]
connect = sqlite3.connect
class Crash(sqlite3.Connection):
    accepting = False
    def execute(self, sql, *args, **kwargs):
        result = super().execute(sql, *args, **kwargs)
        if sql.startswith('INSERT INTO image_groups'):
            self.accepting = True
            if phase == 'before-accept': os._exit(23)
        if sql == 'COMMIT' and self.accepting and phase == 'after-accept': os._exit(23)
        return result
sqlite3.connect = lambda *a, **kw: connect(*a, **kw, factory=Crash)
publish = batch_store._publish_body
def die(path, body):
    if phase == 'publish': publish(path, body)
    os._exit(23)
if phase in ('reserve', 'publish'): batch_store._publish_body = die
async def main():
    with database.open_database(Path(sys.argv[1])) as db:
        async with open_saver(Path(sys.argv[1]), db) as saver:
            await image_group_store.retry_image_execution(db, saver, sys.argv[3], phase,
                predecessor_execution_id=sys.argv[4], expected_result_digest=sys.argv[5])
asyncio.run(main())
'''
        for phase in ('reserve', 'publish', 'before-accept', 'after-accept'):
            with self.subTest(phase=phase):
                run = subprocess.run([sys.executable, '-B', '-c', child, str(self.root), phase, self.project,
                    initial.execution_id, result.digest], capture_output=True, text=True, timeout=45)
                self.assertEqual(run.returncode, 23, run.stderr)
                with database.open_database(self.root) as db:
                    self.assertEqual(db.execute('SELECT acceptance_state FROM image_group_retry_requests WHERE client_key=?',
                        (phase,)).fetchone(), ('accepted' if phase == 'after-accept' else 'reserved',))
                    async with open_saver(self.root, db) as saver:
                        with self.offline():
                            retry = await groups.retry_image_execution(db, saver, self.project, phase,
                                predecessor_execution_id=initial.execution_id, expected_result_digest=result.digest)
                            changes = db.total_changes
                            self.assertEqual(await groups.retry_image_execution(db, saver, self.project, phase,
                                predecessor_execution_id=initial.execution_id, expected_result_digest=result.digest), retry)
                            self.assertEqual(db.total_changes, changes)
                            self.assertEqual(self.results.read_image_input_batch(db, retry.execution_id).batch_id, initial.batch_id)
                            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_submission_attempts').fetchone(), (1,))


if __name__ == '__main__':
    unittest.main()
