"""Authored single-thread route, real stores/imports/checkpoints; mock providers only."""

from contextlib import contextmanager
import os
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from backend import image_group_results as results, image_group_store as groups, wardrobe_store
from backend.domain import StoryV2, OwnerResponseV1
from backend.story_control import open_story_runtime
from backend.story_reads import story_projection
from backend.wardrobe import VisualAnchorPlanV2, validate_wardrobe_plan
from tests.test_story_anchor_start import AnchorStartFixtures
from tests.test_story_cast import draft
from tests.test_wardrobe_compact_v2 import compact_draft
from tests import test_image_group_worker as native_fixtures
from tests.test_portrait_worker import NOW, ENDPOINT


class StoryAnchorRuntimeTests(AnchorStartFixtures, unittest.IsolatedAsyncioTestCase):
    server = native_fixtures.ImageGroupWorkerTests.server
    context = native_fixtures.ImageGroupWorkerTests.context

    def setUp(self):
        super().setUp()
        environment = patch.dict(os.environ, {'COMFYUI_LOCAL_ENDPOINT': ENDPOINT})
        environment.start()
        self.addCleanup(environment.stop)
        self.intent['connection'] = self.start_module.story_anchor_start_options().model_dump(mode='json')['connections'][0]
        self.intent['image_size'] = dict(width=512, height=512)
        self.requests, self.wires, self.uploads = [], {}, {}
        self.fail_keys, self.hook = set(), None

    async def asyncSetUp(self):
        asyncio.get_running_loop().slow_callback_duration = 100

    @contextmanager
    def native(self, runtime, execution):
        runtime.image_transport, runtime.image_clock_ms = self.server(runtime.db), lambda: NOW
        async def context(connection, workflow, **kwargs):
            from backend.batch_generation import _unit
            batch = results.read_image_input_batch(runtime.db, execution)
            unit = next(u for u in batch.prepared_input.ordered_units
                        if _unit(batch.prepared_input, u.unit_key)[2].workflow_id == workflow)
            return self.context(batch, unit.unit_key)
        with patch('backend.comfyui.acquire_preparation_context', side_effect=context):
            yield

    async def finished(self, runtime):
        for _ in range(15):
            await runtime.run()
            outcome = runtime.db.execute('SELECT outcome FROM execution_outcomes').fetchone()
            if outcome:
                return outcome[0]
        self.fail('Route failed to reach terminal join')

    async def public_reads(self, runtime, execution, *, images=False):
        from backend.api import create_app, PORT
        app = create_app(root=self.root)
        app.state.runtime = runtime  # ASGI read check, deliberately no lifespan/worker.
        before, changes = list(runtime.db.iterdump()), runtime.db.total_changes
        with patch('httpx.AsyncHTTPTransport.handle_async_request', side_effect=AssertionError('Read network')), \
                patch('backend.production.production_catalog', side_effect=AssertionError('Read current profile')):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=f'http://127.0.0.1:{PORT}') as client:
                self.assertEqual((await client.get('/api/session')).status_code, 200)
                paths = ['/api/executions', f'/api/executions/{execution}',
                         f'/api/executions/{execution}/projection?include_process=true',
                         f'/api/executions/{execution}/process', f'/api/executions/{execution}/story-activity',
                         f'/api/executions/{execution}/wardrobe-activity']
                projection = story_projection(runtime.db, execution)
                if projection['wardrobe_plan_ref']:
                    paths.append(f'/api/executions/{execution}/wardrobe-plans/' + projection['wardrobe_plan_ref']['artifact_id'])
                if projection['stories']:
                    paths.append(f'/api/executions/{execution}/stories/' + projection['stories'][-1]['ref']['artifact_id'])
                for path in paths:
                    response = await client.get(path)
                    self.assertEqual(response.status_code, 200, (path, response.text))
                if images:
                    response = await client.get(f'/api/executions/{execution}/images')
                    self.assertEqual(response.status_code, 200, response.text)
                    for unit in response.json()['units']:
                        if unit['available']:
                            original = await client.get(unit['original']['url'])
                            self.assertEqual(original.status_code, 200, original.text[:80])
                            from tests.test_portrait_candidate_store import png
                            self.assertEqual(original.content, png())
                            self.assertEqual(original.headers['x-content-type-options'], 'nosniff')
        self.assertEqual(runtime.db.total_changes, changes)
        self.assertEqual(list(runtime.db.iterdump()), before)

    @contextmanager
    def owners(self, subjects):
        story = draft() if subjects else draft(cast=[], subject_ids=[])
        async def wardrobe(config, **kwargs):
            from backend.openrouter_wardrobe import read_wardrobe_config
            config = read_wardrobe_config(config)
            return validate_wardrobe_plan(VisualAnchorPlanV2(schema_id='visual_anchor_plan', schema_version='2',
                narrative_ref=config.wardrobe_input.narrative_ref, **compact_draft(subjects)), config.wardrobe_input)
        with patch('backend.openrouter.produce_live_story', new=AsyncMock(return_value=StoryV2.model_validate(story))) as owner, \
                patch('backend.openrouter_wardrobe.complete_wardrobe', side_effect=wardrobe) as planner:
            yield owner, planner

    async def approve(self, runtime, execution, action='approve', message=None):
        review = story_projection(runtime.db, execution)['review']
        return runtime.respond(execution, review['request_id'], review['digest'], review['binding_revision'],
                               action + str(review['revision']), action, message)

    async def test_location_only_one_execution_automatic_handoff_and_terminal(self):
        await self.route((), ['location'])

    async def test_portrait_background_sheet_one_execution_actual_import(self):
        await self.route(('comedian',), ['face-0', 'location', 'sheet-0'])

    async def route(self, subjects, keys):
        with self.owners(subjects) as (owner, planner):
            async with open_story_runtime(self.root, lambda *args: self.fail('Fixture owner used')) as runtime:
                start = await self.start(runtime.db, runtime.saver)
                execution, db = start.execution_id, runtime.db
                view = await runtime.process_projection(execution)
                self.assertEqual(view.production.model_dump(mode='json'), {**self.intent, 'connection': 'local'})
                await self.public_reads(runtime, execution)
                await runtime.run()
                self.assertEqual(story_projection(db, execution)['status'], 'waiting_review')
                await self.approve(runtime, execution)
                # Registration and the pure batch wait happen in this SAME approval segment.
                # Native context must already be stubbed before the runner's independent tick.
                with self.native(runtime, execution):
                    await runtime.run()
                    group = groups.read_image_group(db, execution)
                    self.assertIsNotNone(group.checkpoint_id)
                    self.assertIsNone(db.execute('SELECT outcome FROM execution_outcomes').fetchone())
                    self.assertEqual((await runtime.process_projection(execution)).status, 'waiting_job')
                    await self.public_reads(runtime, execution, images=True)
                    self.assertEqual(await self.finished(runtime), 'completed')
                self.assertEqual(db.execute('SELECT outcome FROM execution_outcomes').fetchone(), ('completed',))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM executions').fetchone(), (1,))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_work WHERE kind='start'").fetchone(), (1,))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM continue_handoffs').fetchone(), (0,))
                self.assertEqual([o.unit_key for o in results.read_image_group_result(db, execution).body.outputs], keys)
                self.assertEqual(len(self.wires), len(keys))
                self.assertEqual(len(self.uploads), 2 * len(subjects))
                self.assertEqual(owner.call_count, 1)
                self.assertEqual(planner.call_count, 1)
                view = await runtime.process_projection(execution)
                self.assertEqual((view.selected_execution_id, view.source_execution_id, view.effective_execution_id),
                                 (execution, execution, execution))
                self.assertEqual(view.action, 'finished')
                self.assertEqual(story_projection(db, execution)['status'], 'completed')
                await self.public_reads(runtime, execution, images=True)
            # Provider-off reopen reads cannot perform recovery/maintenance writes.
            async with open_story_runtime(self.root, lambda *args: self.fail('Offline owner')) as runtime:
                await self.public_reads(runtime, execution, images=True)

    async def test_clarify_revise_exact_review_then_same_execution_batch(self):
        with self.owners(('comedian',)) as (owner, planner):
            owner.side_effect = [StoryV2.model_validate(draft()),
                OwnerResponseV1(status='clarified', explanation='The ribbon returns.'), StoryV2.model_validate(draft())]
            async with open_story_runtime(self.root, lambda *args: None) as runtime:
                start = await self.start(runtime.db, runtime.saver)
                await runtime.run()
                await self.approve(runtime, start.execution_id, 'clarify', 'Why the ribbon?')
                await runtime.run()
                await self.approve(runtime, start.execution_id, 'revise', 'Make the return warmer')
                await runtime.run()
                await self.approve(runtime, start.execution_id)
                with self.native(runtime, start.execution_id):
                    self.assertEqual(await self.finished(runtime), 'completed')
                group = groups.read_image_group(runtime.db, start.execution_id)
                self.assertEqual(group.batch.prepared_input.story_approval.story_binding_revision, 2)
                self.assertEqual(runtime.db.execute('SELECT COUNT(*) FROM review_requests').fetchone(), (3,))
                self.assertEqual((owner.call_count, planner.call_count), (3, 1))
                await self.public_reads(runtime, start.execution_id, images=True)

    async def test_reopen_after_approval_wardrobe_publication_and_registration(self):
        from backend import batch_store
        from backend.review_store import apply_story_decision
        boundaries = [('approval', 'backend.story_graph.apply_story_decision', apply_story_decision),
                      ('wardrobe', 'backend.wardrobe_store.commit_wardrobe_operation', wardrobe_store.commit_wardrobe_operation),
                      ('publication', 'backend.batch_store._publish_body', batch_store._publish_body),
                      ('registration', 'backend.story_anchor_graph.register_story_anchor_group', groups.register_story_anchor_group)]
        for name, target, original in boundaries:
            self.root = self.root.with_name(name)
            self.wires, self.uploads = {}, {}
            with self.subTest(boundary=name), self.owners(()) as (owner, planner):
                async with open_story_runtime(self.root, lambda *args: None) as runtime:
                    start = await self.start(runtime.db, runtime.saver)
                    await runtime.run()
                    decision = await self.approve(runtime, start.execution_id)
                    def crash(*args, **kwargs):
                        original(*args, **kwargs)
                        raise RuntimeError('lost after ' + name)
                    with patch(target, side_effect=crash), self.assertRaisesRegex(RuntimeError, 'lost after'):
                        await runtime.run()
                    self.assertEqual(runtime.db.execute('SELECT status FROM execution_work WHERE work_id=?',
                                                        (decision.work_id,)).fetchone(), ('claimed',))
                async with open_story_runtime(self.root, lambda *args: None) as runtime:
                    with self.native(runtime, start.execution_id):
                        self.assertEqual(await self.finished(runtime), 'completed')
                    self.assertEqual((owner.call_count, planner.call_count), (1, 1))
                    self.assertEqual(len(self.wires), 1)
                    self.assertEqual(runtime.db.execute('SELECT COUNT(*) FROM wardrobe_operations').fetchone(), (1,))

    async def test_reopen_import_result_pending_resume_and_join_commit(self):
        from backend import portrait_candidate_store as candidates
        for boundary in ('import', 'result', 'resume', 'join'):
            self.root = self.root.with_name(boundary)
            self.wires, self.uploads = {}, {}
            with self.subTest(boundary=boundary), self.owners(()) as (owner, planner):
                async with open_story_runtime(self.root, lambda *args: None) as runtime:
                    start = await self.start(runtime.db, runtime.saver)
                    await runtime.run()
                    await self.approve(runtime, start.execution_id)
                    with self.native(runtime, start.execution_id):
                        await runtime.run()  # Wait binding + native POST.
                        if boundary in ('resume', 'join'):
                            await runtime.run()  # Actual import and exact result/wake.
                        if boundary == 'resume':
                            original_write = runtime.saver.aput_writes
                            async def crash_write(config, writes, task_id, **kwargs):
                                await original_write(config, writes, task_id, **kwargs)
                                if any(c == '__resume__' for c, _ in writes):
                                    raise RuntimeError('lost after resume')
                            injection = patch.object(runtime.saver, 'aput_writes', side_effect=crash_write)
                        else:
                            target, original = {
                                'import': ('backend.portrait_candidate_store.import_anchor_unit_candidate', candidates.import_anchor_unit_candidate),
                                'result': ('backend.image_group_worker.results.publish_image_group_result', results.publish_image_group_result),
                                'join': ('backend.story_anchor_graph.join_image_group_result', results.join_image_group_result),
                            }[boundary]
                            def crash(*args, **kwargs):
                                original(*args, **kwargs)
                                raise RuntimeError('lost after ' + boundary)
                            injection = patch(target, side_effect=crash)
                        with injection, self.assertRaisesRegex(RuntimeError, 'lost after'):
                            await runtime.run()
                async with open_story_runtime(self.root, lambda *args: None) as runtime:
                    with self.native(runtime, start.execution_id):
                        self.assertEqual(await self.finished(runtime), 'completed')
                    self.assertEqual((owner.call_count, planner.call_count, len(self.wires)), (1, 1, 1))
                    self.assertEqual(runtime.db.execute('SELECT COUNT(*) FROM image_group_joins').fetchone(), (1,))

    async def test_cancel_before_import_prevents_late_candidate_and_join(self):
        with self.owners(()) as (owner, planner):
            async with open_story_runtime(self.root, lambda *args: None) as runtime:
                start = await self.start(runtime.db, runtime.saver)
                await runtime.run()
                await self.approve(runtime, start.execution_id)
                def cancel(request, route):
                    if route == 'view':
                        runtime.cancel(start.execution_id, 'cancel')
                with self.native(runtime, start.execution_id):
                    await runtime.run()
                    self.hook = cancel
                    await runtime.run()
                    self.hook = None
                    await runtime.run()
                self.assertEqual(runtime.db.execute('SELECT outcome FROM execution_outcomes').fetchone(), ('cancelled',))
                self.assertEqual(runtime.db.execute('SELECT COUNT(*) FROM image_group_joins').fetchone(), (0,))
                self.assertEqual(runtime.db.execute('SELECT COUNT(*) FROM portrait_candidates').fetchone(), (0,))


if __name__ == '__main__':
    unittest.main()
