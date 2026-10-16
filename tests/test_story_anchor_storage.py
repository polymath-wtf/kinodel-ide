"""Same-execution storage only: real frozen admission/commits, no runner or HTTP."""

from copy import deepcopy
from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from backend import batch_store, image_group_results as results, image_group_store as groups
from backend import production, review_store, wardrobe_store
from backend.database import open_database
from backend.domain import StoryV2
from backend.saver import open_saver
from backend.story_graph import initial_story_state, validate_wardrobe_success
from backend.story_store import commit_story_operation, prepare_story_operation
from backend.wardrobe import VisualAnchorPlanV2, validate_wardrobe_plan
from backend.wardrobe_operation import produce_wardrobe_operation
from tests.test_story_anchor_start import AnchorStartFixtures
from tests.test_story_cast import draft
from tests.test_wardrobe_compact_v2 import compact_draft
from tests import test_image_group_results as image_fixtures


class AnchorStorageTests(AnchorStartFixtures, unittest.IsolatedAsyncioTestCase):
    context = image_fixtures.ImageGroupResultTests.context
    complete = image_fixtures.ImageGroupResultTests.complete
    unit = image_fixtures.ImageGroupResultTests.unit
    publish = image_fixtures.ImageGroupResultTests.publish
    bind_wait = image_fixtures.ImageGroupResultTests.bind_wait
    join = image_fixtures.ImageGroupResultTests.join

    def setUp(self):
        super().setUp()
        self.results = results

    async def committed(self, db, saver, *, revise=False):
        start = await self.start(db, saver)
        execution = start.execution_id
        activation = initial_story_state(self.project, execution, live=True)['story_activation']
        _, digest, _ = prepare_story_operation(db, execution, activation)
        ref, trigger = commit_story_operation(db, execution, activation, digest, str(uuid4()), StoryV2.model_validate(draft()))
        review = review_store.prepare_story_review(db, execution, trigger, ref, 1)
        review_store.bind_story_wait(db, execution, review.request_id, 'story-cp', 'story-task', 'story-interrupt')
        revision = 1
        if revise:
            decision = review_store.accept_story_decision(db, execution, review.request_id, review.digest, 1,
                                                         'revise', 'revise', 'Make the return warmer')
            activation = review_store.apply_story_decision(db, execution, review.request_id, decision.decision_id)
            _, digest, _ = prepare_story_operation(db, execution, activation, prior_ref=ref,
                feedback='Make the return warmer', expected_revision=1, request_id=review.request_id, action='revise')
            ref, trigger = commit_story_operation(db, execution, activation, digest, str(uuid4()), StoryV2.model_validate(draft()))
            review = review_store.prepare_story_review(db, execution, trigger, ref, 2, previous_request_id=review.request_id)
            review_store.bind_story_wait(db, execution, review.request_id, 'revised-cp', 'revised-task', 'revised-interrupt')
            revision = 2
        decision = review_store.accept_story_decision(db, execution, review.request_id, review.digest, revision,
                                                     'approve', 'approve', None)
        review_store.apply_story_decision(db, execution, review.request_id, decision.decision_id)
        self.assertIsNone(db.execute('SELECT * FROM execution_outcomes').fetchone(),
                          'Story approval must not complete the Story/anchor route')
        _, supplied, _ = wardrobe_store.wardrobe_authority(db, execution, review.request_id)
        plan = validate_wardrobe_plan(VisualAnchorPlanV2(schema_id='visual_anchor_plan', schema_version='2',
            narrative_ref=ref, **compact_draft(('comedian',))), supplied)
        with patch('backend.openrouter_wardrobe.complete_wardrobe', new=AsyncMock(return_value=plan)):
            ref, transition = await produce_wardrobe_operation(db, execution, review.request_id,
                                                              character_root=self.root.parent / 'characters')
        self.assertEqual(validate_wardrobe_success(db, execution, review.request_id), ref)
        return start, review, ref, transition

    def register(self, db, execution, review):
        self.assertTrue(callable(getattr(groups, 'register_story_anchor_group', None)),
                        'Same-execution group registration is missing')
        return groups.register_story_anchor_group(db, execution, review.request_id)

    def cancel(self, db, start):
        db.execute("INSERT INTO execution_controls VALUES (?,'cancel','cancel',?,NULL)",
                   (start.execution_id, start.work_id))

    @contextmanager
    def corruption(self, db, table, changes, where='1', args=()):
        # These readers require committed state: a savepoint would test only that
        # guard rather than the actual corrupted authority/identity.
        columns = ','.join(changes)
        original = db.execute(f'SELECT rowid,{columns} FROM {table} WHERE {where}', args).fetchall()
        assignments = ','.join(key + '=?' for key in changes)
        for row in original:
            db.execute(f'UPDATE {table} SET {assignments} WHERE rowid=?', (*changes.values(), row[0]))
        try:
            yield
        finally:
            for row in original:
                db.execute(f'UPDATE {table} SET {assignments} WHERE rowid=?', (*row[1:], row[0]))

    async def test_same_execution_group_and_exact_reopen_without_extra_start_or_effects(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                start, review, ref, transition = await self.committed(db, saver)
                receipt = self.register(db, start.execution_id, review)
                group = groups.read_image_group(db, start.execution_id)
                self.assertEqual(receipt.execution_id, ref.execution_id)
                self.assertEqual(receipt.work_id, start.work_id)  # Existing Story work, NOT image-only work.
                self.assertEqual(receipt.activation_id, transition)
                self.assertEqual(group.batch.prepared_input.source_plan_ref, ref)
                for field in ('image_size', 'image_profile', 'connection'):
                    self.assertEqual(getattr(group.batch.prepared_input, field), getattr(start.render_intent, field))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM executions').fetchone(), (1,))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_work WHERE kind='start'").fetchone(), (1,))
                for table in ('execution_outcomes', 'batch_unit_input_pins', 'render_jobs', 'portrait_submissions'):
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM ' + table).fetchone(), (0,))
                before, changes = list(db.iterdump()), db.total_changes
                self.assertEqual(self.register(db, start.execution_id, review), receipt)
                self.assertEqual(db.total_changes, changes)
                self.assertEqual(list(db.iterdump()), before)
        with open_database(self.root) as db, patch('backend.production.production_catalog', side_effect=AssertionError('Replay catalog')):
            self.assertEqual(self.register(db, start.execution_id, review), receipt)
            self.assertEqual(groups.read_image_group(db, start.execution_id), group)
            self.assertEqual(list(db.iterdump()), before)

    async def test_fresh_profile_or_connection_drift_and_cancel_refuse_without_pins(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                start, review, _, _ = await self.committed(db, saver)
                catalog = deepcopy(production.production_catalog())
                catalog['image_only']['profiles'][0]['pin']['digest'] = 'sha256:' + 'a' * 64
                with patch('backend.production.production_catalog', return_value=catalog), self.assertRaises(ValueError):
                    self.register(db, start.execution_id, review)
                with patch('backend.story_anchor_start.config.resolve_comfyui_connection',
                           return_value=SimpleNamespace(endpoint_digest='a' * 64)), self.assertRaises(ValueError):
                    self.register(db, start.execution_id, review)
                self.cancel(db, start)
                with self.assertRaises(ValueError):
                    self.register(db, start.execution_id, review)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM batch_input_pins').fetchone(), (0,))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM image_groups').fetchone(), (0,))

    async def test_reserved_bytes_recover_without_refreezing_and_source_occ_race_refuses_group(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                start, review, _, _ = await self.committed(db, saver)
                publish = batch_store._publish_body
                def lost_after_publication(path, body):
                    publish(path, body)
                    raise OSError('Lost process before SQL publication marker')
                with patch.object(batch_store, '_publish_body', side_effect=lost_after_publication), self.assertRaises(OSError):
                    self.register(db, start.execution_id, review)
                reserved = db.execute('SELECT batch_id,input_digest,body,uri FROM batch_input_pins').fetchone()
                self.assertEqual(db.execute('SELECT publication_state FROM batch_input_pins').fetchone(), ('reserved',))
                with patch('backend.production.production_catalog', side_effect=AssertionError('Recovery refroze profile')):
                    receipt = self.register(db, start.execution_id, review)
                self.assertEqual((receipt.batch_id, receipt.input_digest), reserved[:2])
                self.assertEqual(db.execute('SELECT batch_id,input_digest,body,uri FROM batch_input_pins').fetchone(), reserved)
                self.assertEqual((self.root / reserved[3].removeprefix('kinodel://')).read_bytes(), reserved[2].encode())
        self.root = self.root.with_name('source-race')
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                start, review, _, _ = await self.committed(db, saver)
                def changed_binding(path, body):
                    publish(path, body)
                    db.execute("UPDATE execution_bindings SET binding_revision=2 WHERE slot='wardrobe_plan'")
                with patch.object(batch_store, '_publish_body', side_effect=changed_binding), self.assertRaises(ValueError):
                    self.register(db, start.execution_id, review)
                self.assertEqual(db.execute('SELECT publication_state FROM batch_input_pins').fetchone(), ('reserved',))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM image_groups').fetchone(), (0,))

    async def test_scoped_wake_coexists_with_authorized_prior_story_revision_not_arbitrary_resume(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                start, review, _, _ = await self.committed(db, saver, revise=True)
                receipt = self.register(db, start.execution_id, review)
                self.unit(db, receipt.execution_id, 0, finish='failed')
                result = self.publish(db, receipt, status='failed', failed_unit_key='face-0')
                self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_work WHERE kind='resume'").fetchone(), (3,))
                self.assertEqual(results.read_image_group_result(db, receipt.execution_id), result)
                with self.corruption(db, 'review_requests', {'decision_digest': 'sha256:' + '0' * 64}, "action='revise'"):
                    with self.assertRaisesRegex(ValueError, 'Story decision'):
                        results.read_image_group_result(db, receipt.execution_id)
                db.execute("INSERT INTO execution_work (work_id,execution_id,kind,source_id,resume_ref,payload_digest,status) "
                           "VALUES (?,?, 'resume',?,?,?,'pending')",
                           ('sha256:' + '1' * 64, start.execution_id, 'sha256:' + '2' * 64,
                            result.result_id, result.digest))
                with self.assertRaisesRegex(ValueError, 'authorized Story decision'):
                    results.read_image_group_result(db, receipt.execution_id)

    async def test_applied_approval_current_bindings_and_transition_are_authority(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                start, review, _, _ = await self.committed(db, saver)
                mutations = [('review_requests', {'decision_digest': 'sha256:' + '0' * 64}, '1'),
                             ('review_requests', {'applied_activation': None}, '1'),
                             ('execution_bindings', {'binding_revision': 2}, "slot='story'"),
                             ('execution_bindings', {'binding_revision': 2}, "slot='wardrobe_plan'"),
                             ('wardrobe_operations', {'artifact_id': None, 'next_activation': None}, '1'),
                             ('executions', {'graph_digest': 'sha256:' + '0' * 64}, '1')]
                for table, changes, where in mutations:
                    with self.subTest(table=table, changes=changes), self.corruption(db, table, changes, where):
                        with self.assertRaises(ValueError):
                            self.register(db, start.execution_id, review)
                self.register(db, start.execution_id, review)

    async def test_publication_cancel_race_keeps_reservation_but_no_group_or_late_effect(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                start, review, _, _ = await self.committed(db, saver)
                publish = batch_store._publish_body
                def cancelled(path, body):
                    publish(path, body)
                    self.cancel(db, start)
                with patch.object(batch_store, '_publish_body', side_effect=cancelled), self.assertRaises(ValueError):
                    self.register(db, start.execution_id, review)
                self.assertEqual(db.execute('SELECT publication_state FROM batch_input_pins').fetchall(), [('reserved',)])
                self.assertEqual(db.execute('SELECT COUNT(*) FROM image_groups').fetchone(), (0,))
                with self.assertRaises(ValueError):
                    self.register(db, start.execution_id, review)

    async def test_full_ordered_result_scoped_wake_and_join_with_story_resume(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                start, review, _, _ = await self.committed(db, saver)
                receipt = self.register(db, start.execution_id, review)
                records = [self.unit(db, receipt.execution_id, i) for i in range(3)]
                result = self.publish(db, receipt)
                self.assertEqual([o.unit_key for o in result.body.outputs], ['face-0', 'location', 'sheet-0'])
                self.assertEqual([o.attempt_id for o in result.body.outputs], [r[1].attempt_id for r in records])
                self.assertEqual(result.body.outputs[2].parent_bindings[0].source_id, records[0][2].candidate_id)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_work WHERE kind='resume'").fetchone(), (2,))
                self.bind_wait(db, receipt)
                wake = results.read_image_group_wake(db, receipt.execution_id)
                assert wake is not None
                self.assertEqual(wake.source_id, receipt.wait_id)
                joined = self.join(db, receipt, result)
                self.assertEqual(joined.batch_outputs, result.result_id)
                before = db.total_changes
                self.assertEqual(results.read_image_group_result(db, receipt.execution_id), result)
                self.assertEqual(self.join(db, receipt, result), joined)
                self.assertEqual(db.total_changes, before)
                self.cancel(db, start)
                self.assertEqual(results.read_image_group_result(db, receipt.execution_id), result)
                with self.assertRaises(ValueError):
                    results.assert_image_attempt_writable(db, records[0][1].job_id, records[0][1].attempt_id)

    async def test_result_publication_source_occ_preserves_reserved_facts_without_wake(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                start, review, _, _ = await self.committed(db, saver)
                receipt = self.register(db, start.execution_id, review)
                self.unit(db, receipt.execution_id, 0, finish='failed')
                publish = batch_store._publish_body
                def changed_source(path, body):
                    publish(path, body)
                    db.execute("UPDATE execution_bindings SET binding_revision=2 WHERE slot='wardrobe_plan'")
                with patch.object(batch_store, '_publish_body', side_effect=changed_source), self.assertRaises(ValueError):
                    self.publish(db, receipt, status='failed', failed_unit_key='face-0')
                self.assertEqual(db.execute('SELECT publication_state FROM image_group_results').fetchone(), ('reserved',))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_work WHERE kind='resume' AND source_id=?",
                                            (receipt.wait_id,)).fetchone(), (0,))

    async def test_foreign_resume_and_story_decision_corruption_reject_and_retry_is_unsupported(self):
        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                start, review, _, _ = await self.committed(db, saver)
                receipt = self.register(db, start.execution_id, review)
                self.unit(db, receipt.execution_id, 0, finish='failed')
                result = self.publish(db, receipt, status='failed', failed_unit_key='face-0')
                mutations = [{'payload_digest': 'sha256:' + '0' * 64}, {'source_id': 'sha256:' + '0' * 64}]
                for changes, source in ((c, s) for c in mutations for s in (review.request_id, receipt.wait_id)):
                    with self.corruption(db, 'execution_work', changes, "kind='resume' AND source_id=?", (source,)):
                        with self.assertRaises(ValueError):
                            results.read_image_group_result(db, receipt.execution_id)
                before = list(db.iterdump())
                with self.assertRaisesRegex(ValueError, 'unsupported|not supported'):
                    await groups.retry_image_execution(db, saver, self.project, 'retry',
                        predecessor_execution_id=receipt.execution_id, expected_result_digest=result.digest)
                self.assertEqual(list(db.iterdump()), before)


if __name__ == '__main__':
    unittest.main()
