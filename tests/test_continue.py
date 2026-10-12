"""Public Continue admission: no invocation, approval, renewed budget or provider effects."""

import asyncio
import importlib.util
import json
import subprocess
import sys
from typing import Any
import unittest
from unittest.mock import patch

import httpx
from langgraph.errors import NodeCancelledError

from backend import batch_store, config, database, wardrobe_store
from backend.api import create_app, fixture_story
from backend.story_control import open_story_runtime
from tests import test_story_wardrobe_api as fixtures
from tests import test_image_group_store as image_fixtures
from tests.test_story_wardrobe_runtime import retained_inventory


class ContinueTests(fixtures.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    source: Any = image_fixtures.ImageGroupStoreTests.source
    no_units: Any = image_fixtures.ImageGroupStoreTests.no_units

    def setUp(self):
        super().setUp()
        from backend import image_group_store
        from backend.production import production_catalog
        self.store = image_group_store
        self.profile = production_catalog()['image_only']['profiles'][0]['pin']
        self.assertIsNotNone(importlib.util.find_spec('backend.continue_command'), 'Public Continue policy is missing')

    def intent(self, ref):
        selected = config.resolve_comfyui_connection('local')
        return dict(source_plan_ref=ref.model_dump(mode='json'), image_size=dict(width=768, height=768),
                    image_profile=self.profile, connection=dict(connection='local',
                    endpoint_digest='sha256:' + selected.endpoint_digest))

    async def projection(self, runtime, execution):
        return await runtime.process_projection(execution)

    async def command(self, runtime, execution, key='play', token=None, intent=None):
        token = token or (await self.projection(runtime, execution)).occ_token
        return await runtime.continue_execution(execution, dict(command_key=key, expected_token=token,
                                                                production_intent=intent))

    async def test_saved_source_converges_new_keys_reopen_and_preserves_source(self):
        async with self.source() as (runtime, ref, _):
            before = retained_inventory(runtime.db, ref.execution_id)
            view = await self.projection(runtime, ref.execution_id)
            self.assertEqual(view.action, 'start_images')
            with image_fixtures.ImageGroupStoreTests.forbidden_effects(self):
                receipt = await self.command(runtime, ref.execution_id, token=view.occ_token, intent=self.intent(ref))
                again = await self.command(runtime, ref.execution_id, key='second', intent=self.intent(ref))
            self.assertEqual(receipt.effective_execution_id, again.effective_execution_id)
            self.assertEqual(receipt.group_id, again.group_id)
            self.assertEqual(runtime.db.execute('SELECT COUNT(*) FROM image_groups').fetchone(), (1,))
            self.assertEqual(retained_inventory(runtime.db, ref.execution_id), before)
            self.no_units(runtime.db)
            view = await self.projection(runtime, ref.execution_id)
            self.assertEqual(view.source_execution_id, ref.execution_id)
            self.assertEqual(view.effective_execution_id, receipt.effective_execution_id)
            self.assertEqual((view.image_progress.completed, view.image_progress.total), (0, 3))
            self.assertEqual(view.action, 'open')
            # SAME delivery precedes freshness checks and returns the saved immutable receipt.
            self.assertEqual(await self.command(runtime, ref.execution_id, token=receipt.expected_token,
                                                intent=self.intent(ref)), receipt)
        async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
            with image_fixtures.ImageGroupStoreTests.forbidden_effects(self, replay=True):
                reopened = await self.command(runtime, ref.execution_id, key='reload')
            self.assertEqual(reopened.effective_execution_id, receipt.effective_execution_id)

    async def test_missing_conflicting_intent_and_stale_occ_never_accept(self):
        async with self.source() as (runtime, ref, _):
            token = (await self.projection(runtime, ref.execution_id)).occ_token
            with self.assertRaises(ValueError):
                await self.command(runtime, ref.execution_id, token=token)
            with self.assertRaises(ValueError):
                await self.command(runtime, ref.execution_id, token='sha256:' + '0' * 64, intent=self.intent(ref))
            intent = self.intent(ref)
            await self.command(runtime, ref.execution_id, token=token, intent=intent)
            changed = {**intent, 'image_size': dict(width=512, height=512)}
            with self.assertRaises(ValueError):
                await self.command(runtime, ref.execution_id, key='conflict', intent=changed)
            with self.assertRaises(ValueError):
                await self.command(runtime, ref.execution_id, key='stale', token='sha256:' + '1' * 64)
            self.assertEqual(runtime.db.execute('SELECT COUNT(*) FROM image_groups').fetchone(), (1,))

    async def test_reservation_crash_and_concurrent_delivery_keep_original_pins(self):
        async with self.source() as (runtime, ref, _):
            token = (await self.projection(runtime, ref.execution_id)).occ_token
            with patch.object(batch_store, '_publish', side_effect=OSError('interrupted publication')):
                with self.assertRaises(OSError):
                    await self.command(runtime, ref.execution_id, token=token, intent=self.intent(ref))
            self.assertEqual(runtime.db.execute('SELECT COUNT(*) FROM image_groups').fetchone(), (0,))
        async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
            with image_fixtures.ImageGroupStoreTests.forbidden_effects(self, replay=True):
                receipts = await asyncio.gather(*[self.command(runtime, ref.execution_id, key='delivery-' + str(i),
                    intent=self.intent(ref)) for i in range(3)])
            self.assertEqual(len({r.group_id for r in receipts}), 1)
            self.assertEqual(runtime.db.execute('SELECT COUNT(*) FROM batch_input_pins').fetchone(), (1,))

    async def test_control_change_during_await_fences_reserved_acceptance(self):
        async with self.source() as (runtime, ref, _):
            import backend.continue_command as command
            original = command.validate_story_storage

            async def changed(*args):
                await original(*args)
                work = runtime.db.execute('SELECT work_id FROM execution_work WHERE execution_id=?',
                                          (ref.execution_id,)).fetchone()[0]
                runtime.db.execute("INSERT INTO execution_controls VALUES (?,'late-cancel','cancel',?,NULL)",
                                   (ref.execution_id, work))

            with patch.object(command, 'validate_story_storage', side_effect=changed):
                with self.assertRaises(ValueError):
                    await self.command(runtime, ref.execution_id, intent=self.intent(ref))
            self.assertEqual(runtime.db.execute('SELECT COUNT(*) FROM image_groups').fetchone(), (0,))

    async def test_text_active_human_review_and_terminal_no_approval(self):
        async with open_story_runtime(self.root, fixture_story) as runtime:
            receipt = await runtime.start(self.project, 'text', 'A journey', ['s1'])
            opened = await self.command(runtime, receipt.execution_id)
            self.assertEqual(opened.work_id, receipt.work_id)
            self.assertEqual(opened.disposition, 'open')
            await runtime.run()
            review = await self.projection(runtime, receipt.execution_id)
            self.assertEqual(review.action, 'review')
            response = await self.command(runtime, receipt.execution_id, key='review')
            self.assertEqual(response.review, review.review)
            self.assertIsNone(response.work_id)
            self.assertEqual(runtime.db.execute('SELECT decision_id FROM review_requests').fetchone(), (None,))
            self.approve(runtime, receipt.execution_id)
            await runtime.run()
            done = await self.command(runtime, receipt.execution_id, key='finished')
            self.assertEqual((done.disposition, done.reason), ('finished', 'completed'))
            self.assertIsNone(done.work_id)

    async def test_unfinished_text_keeps_budget_and_delivers_existing_segment(self):
        async with open_story_runtime(self.root, fixture_story) as runtime:
            receipt = await runtime.start(self.project, 'text', 'A journey', ['s1'])
            # A stopped owner call leaves the original work claimed and budget unchanged.
            runtime.db.execute("UPDATE execution_work SET status='claimed' WHERE work_id=?", (receipt.work_id,))
            before = runtime.db.execute('SELECT owner_attempts,owner_budget FROM story_operations').fetchall()
            result = await self.command(runtime, receipt.execution_id)
            self.assertEqual(result.work_id, receipt.work_id)
            self.assertEqual(runtime.db.execute('SELECT owner_attempts,owner_budget FROM story_operations').fetchall(), before)
            await runtime.run()
            self.assertEqual((await self.projection(runtime, receipt.execution_id)).action, 'review')

    async def test_blocked_cancelled_failed_and_image_wait_do_not_retry(self):
        async with self.source() as (runtime, ref, _):
            intent = {**self.intent(ref), 'image_size': dict(width=512, height=512)}
            accepted = await self.command(runtime, ref.execution_id, intent=intent)
            execution = accepted.effective_execution_id
            with patch('backend.image_group_worker.tick_image_groups', return_value=0):
                await runtime.run()
            view = await self.projection(runtime, ref.execution_id)
            self.assertEqual((view.status, view.action), ('waiting_job', 'open'))
            from tests import test_image_group_results as result_fixtures
            from backend import image_group_results
            self.results = image_group_results
            self.context = lambda *args: result_fixtures.ImageGroupResultTests.context(self, *args)
            self.complete = lambda *args, **kwargs: result_fixtures.ImageGroupResultTests.complete(self, *args, **kwargs)
            result_fixtures.ImageGroupResultTests.unit(self, runtime.db, execution, 0)
            view = await self.projection(runtime, ref.execution_id)
            self.assertEqual((view.image_progress.completed, view.image_progress.total), (1, 3))
            between = await self.command(runtime, ref.execution_id, key='between')
            self.assertEqual(between.group_id, accepted.group_id)
            runtime.db.execute("UPDATE execution_work SET status='blocked',blocked_reason='private endpoint /secret' "
                               'WHERE execution_id=?', (execution,))
            blocked = await self.command(runtime, ref.execution_id, key='blocked')
            self.assertEqual(blocked.disposition, 'resolve')
            self.assertNotIn('/secret', blocked.model_dump_json())
            self.assertNotIn('retry', blocked.allowed_actions)
            runtime.db.execute('DELETE FROM execution_work WHERE execution_id=? AND kind=\'reconcile\'', (execution,))
            runtime.cancel(execution, 'cancel')
            self.assertEqual((await self.command(runtime, ref.execution_id, key='cancelling')).reason, 'cancelling')
            with patch('backend.image_group_worker.tick_image_groups', return_value=0):
                await runtime.run()
            self.assertEqual((await self.command(runtime, ref.execution_id, key='cancelled')).reason, 'cancelled')

    async def test_http_session_csrf_strict_receipt_projection_and_no_invocation(self):
        async with self.source() as (_, ref, _):
            pass
        app = create_app(self.root, fixture_story, character_root=self.library)
        with patch('backend.story_control.StoryRuntime.run', return_value=0):
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('127.0.0.1', 1)),
                                             base_url='http://127.0.0.1:8765') as client:
                    path = '/api/executions/' + ref.execution_id
                    self.assertEqual((await client.get(path + '/process')).status_code, 401)
                    csrf = (await client.get('/api/session')).json()['csrf_token']
                    view = (await client.get(path + '/process')).json()
                    body = dict(command_key='http', expected_token=view['occ_token'], production_intent=self.intent(ref))
                    self.assertEqual((await client.post(path + '/continue', json=body)).status_code, 403)
                    with image_fixtures.ImageGroupStoreTests.forbidden_effects(self), patch(
                            'langgraph.pregel.Pregel.ainvoke', side_effect=AssertionError('No API graph invocation')):
                        result = await client.post(path + '/continue', json=body, headers={'X-Kinodel-CSRF': csrf})
                    self.assertEqual(result.status_code, 202, result.text)
                    self.assertNotIn('http://', result.text)
                    self.assertNotIn('endpoint_digest', result.text)
                    image = result.json()['effective_execution_id']
                    self.assertEqual((await client.get('/api/executions/' + image + '/process')).status_code, 200)
                    rich = (await client.get(path + '/projection?include_process=true')).json()
                    self.assertEqual(rich['process']['effective_execution_id'], image)

    async def test_real_process_death_after_reservation_reopens_without_current_catalog(self):
        async with self.source() as (runtime, ref, _):
            token = (await self.projection(runtime, ref.execution_id)).occ_token
            request = dict(command_key='crash', expected_token=token, production_intent=self.intent(ref))
            before = retained_inventory(runtime.db, ref.execution_id)
        script = """
import asyncio, json, os, sys
from pathlib import Path
from unittest.mock import patch
from backend.api import fixture_story
from backend.story_control import open_story_runtime
async def died(*args):
    os._exit(23)
async def main():
    async with open_story_runtime(Path(sys.argv[1]), fixture_story) as runtime:
        with patch('backend.continue_command.validate_story_storage', side_effect=died):
            await runtime.continue_execution(sys.argv[2], json.loads(sys.argv[3]))
asyncio.run(main())
"""
        result = subprocess.run([sys.executable, '-c', script, str(self.root), ref.execution_id, json.dumps(request)],
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 23, result.stderr.decode())
        async with open_story_runtime(self.root, fixture_story) as runtime:
            self.assertEqual(runtime.db.execute('SELECT acceptance_state FROM continue_handoffs').fetchone(), ('reserved',))
            consumer_key = runtime.db.execute('SELECT consumer_key FROM continue_handoffs').fetchone()[0]
            with self.assertRaises(ValueError):
                await runtime.start_images(self.project, consumer_key, **request['production_intent'])
            with image_fixtures.ImageGroupStoreTests.forbidden_effects(self, replay=True):
                accepted = await runtime.continue_execution(ref.execution_id, request)
            self.assertIsNotNone(accepted.group_id)
            self.assertEqual(retained_inventory(runtime.db, ref.execution_id), before)
            self.no_units(runtime.db)

    async def test_stopped_checkpoint_reconcile_uses_same_operation_and_remaining_budget(self):
        async def stopped(*args, **kwargs):
            raise asyncio.CancelledError()
        async with open_story_runtime(self.root, stopped) as runtime:
            receipt = await runtime.start(self.project, 'stopped', 'A journey', ['s1'])
            with self.assertRaises(NodeCancelledError):
                await runtime.run()
            runtime.db.execute("UPDATE execution_work SET status='completed' WHERE work_id=?", (receipt.work_id,))
            runtime.db.execute("UPDATE story_operations SET owner_request='{}',owner_attempts=1,owner_budget=2")
            before = runtime.db.execute('SELECT operation_id,owner_attempts,owner_budget FROM story_operations').fetchall()
            view = await self.projection(runtime, receipt.execution_id)
            self.assertEqual(view.action, 'resume')
            continued = await self.command(runtime, receipt.execution_id)
            self.assertNotEqual(continued.work_id, receipt.work_id)
            self.assertEqual(runtime.db.execute('SELECT operation_id,owner_attempts,owner_budget FROM story_operations').fetchall(), before)
            runtime.produce_story = fixture_story
            await runtime.run()
            self.assertEqual((await self.projection(runtime, receipt.execution_id)).action, 'review')
            self.assertEqual(runtime.db.execute('SELECT operation_id,owner_attempts,owner_budget FROM story_operations').fetchall(), before)

    async def test_exhausted_text_and_failed_outcome_are_resolutions_not_continuations(self):
        async def stopped(*args, **kwargs):
            raise asyncio.CancelledError()
        async with open_story_runtime(self.root, stopped) as runtime:
            receipt = await runtime.start(self.project, 'exhausted', 'A journey', ['s1'])
            with self.assertRaises(NodeCancelledError):
                await runtime.run()
            runtime.db.execute("UPDATE story_operations SET owner_request='{}',owner_attempts=2,owner_budget=2")
            before = runtime.db.total_changes
            result = await self.command(runtime, receipt.execution_id)
            self.assertEqual((result.disposition, result.reason), ('resolve', 'attempt_budget_exhausted'))
            self.assertIsNone(result.work_id)
            self.assertNotIn('retry', result.allowed_actions)
            self.assertEqual(runtime.db.total_changes, before + 1)  # receipt only
            runtime.db.execute('INSERT INTO execution_outcomes VALUES (?,\'failed\',?,NULL)',
                               (receipt.execution_id, receipt.work_id))
            failed = await self.command(runtime, receipt.execution_id, key='failed')
            self.assertEqual((failed.disposition, failed.reason, failed.allowed_actions), ('resolve', 'failed', ['new_run']))

    async def test_additive_db22_upgrade_preserves_existing_rowids_and_receipts(self):
        async with self.source() as (runtime, ref, _):
            before = retained_inventory(runtime.db, ref.execution_id)
            tables = runtime.db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "AND name NOT IN ('continue_handoffs','continue_commands') ORDER BY name").fetchall()
            inventory = {table: runtime.db.execute('SELECT rowid,* FROM ' + table).fetchall() for (table,) in tables}
            runtime.db.execute('DROP TABLE continue_commands')
            runtime.db.execute('DROP TABLE continue_handoffs')
            runtime.db.execute('PRAGMA user_version=22')
        with database.open_database(self.root) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone(), (23,))
            self.assertEqual(retained_inventory(db, ref.execution_id), before)
            self.assertEqual({table: db.execute('SELECT rowid,* FROM ' + table).fetchall() for (table,) in tables}, inventory)

    async def test_exact_retry_lineage_not_latest_or_other_private_start(self):
        from tests import test_image_group_results as result_fixtures
        from backend import image_group_results
        self.results = image_group_results
        self.context = lambda *args: result_fixtures.ImageGroupResultTests.context(self, *args)
        self.complete = lambda *args, **kwargs: result_fixtures.ImageGroupResultTests.complete(self, *args, **kwargs)
        async with self.source() as (runtime, ref, _):
            intent = {**self.intent(ref), 'image_size': dict(width=512, height=512)}
            accepted = await self.command(runtime, ref.execution_id, intent=intent)
            original = self.store.read_image_group(runtime.db, accepted.effective_execution_id).receipt
            # An independent new run from exactly the same plan stays independent.
            private = await runtime.start_images(self.project, 'independent', **intent)
            self.assertEqual((await self.projection(runtime, ref.execution_id)).effective_execution_id, original.execution_id)
            result_fixtures.ImageGroupResultTests.unit(self, runtime.db, original.execution_id, 0, finish='failed')
            failed = image_group_results.publish_image_group_result(runtime.db, original.execution_id,
                expected_request_digest=original.request_digest, status='failed', failed_unit_key='face-0')
            with patch('backend.image_group_worker.tick_image_groups', return_value=0):
                await runtime.run()
            failed_view = await self.projection(runtime, ref.execution_id)
            self.assertEqual((failed_view.action, failed_view.reason), ('resolve', 'failed'))
            successor = await runtime.retry_images(self.project, 'explicit-retry',
                predecessor_execution_id=original.execution_id, expected_result_digest=failed.digest)
            view = await self.projection(runtime, ref.execution_id)
            self.assertEqual(view.effective_execution_id, successor.execution_id)
            self.assertNotEqual(view.effective_execution_id, private.execution_id)
            self.assertEqual((await self.projection(runtime, original.execution_id)).effective_execution_id, successor.execution_id)
            with self.assertRaises(ValueError):
                await self.command(runtime, ref.execution_id, key='old-occ', token=accepted.expected_token,
                                   intent=intent)

    async def test_configured_connection_required_once_and_accepted_settings_are_frozen(self):
        async with self.source() as (runtime, ref, _):
            intent = self.intent(ref)
            changed = {**intent, 'connection': {**intent['connection'], 'endpoint_digest': 'sha256:' + '0' * 64}}
            with self.assertRaises(ValueError):
                await self.command(runtime, ref.execution_id, intent=changed)
            self.assertEqual(runtime.db.execute('SELECT COUNT(*) FROM continue_handoffs').fetchone(), (0,))
            accepted = await self.command(runtime, ref.execution_id, intent=intent)
            with patch.object(config, 'resolve_comfyui_connection', side_effect=AssertionError('Frozen settings only')):
                with image_fixtures.ImageGroupStoreTests.forbidden_effects(self, replay=True):
                    reopened = await self.command(runtime, ref.execution_id, key='new-settings', intent=intent)
            self.assertEqual(reopened.group_id, accepted.group_id)
            self.assertEqual(reopened.production.image_size.model_dump(), intent['image_size'])

    async def test_final_reserved_owner_call_is_active_but_abandoned_exhaustion_is_not(self):
        from backend import openrouter_client as provider
        entered, release = asyncio.Event(), asyncio.Event()
        calls = 0

        async def responses(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return fixtures.envelope({'status': 'ready', 'story': {}, 'explanation': None})
            entered.set()
            await release.wait()
            return fixtures.envelope({'status': 'ready', 'story': fixtures.draft(), 'explanation': None})

        with self.transport():
            async with open_story_runtime(self.root, fixture_story) as runtime:
                receipt = await runtime.start_live(self.project, 'final-call', ['s1'], self.brief)
                with patch.object(provider, 'http', side_effect=responses):
                    running = asyncio.create_task(runtime.run())
                    try:
                        await asyncio.wait_for(entered.wait(), 5)
                        budget = runtime.db.execute('SELECT owner_attempts,owner_budget FROM story_operations').fetchone()
                        self.assertEqual(budget, (2, 2))
                        view = await self.projection(runtime, receipt.execution_id)
                        self.assertEqual((view.status, view.action), ('running', 'open'))
                        opened = await self.command(runtime, receipt.execution_id, token=view.occ_token)
                        self.assertEqual((opened.disposition, opened.work_id), ('open', receipt.work_id))
                        self.assertEqual(runtime.db.execute('SELECT owner_attempts,owner_budget FROM story_operations').fetchone(), budget)
                        self.assertEqual(calls, 2)
                    finally:
                        running.cancel()
                        await asyncio.gather(running, return_exceptions=True)
                    # A durable claimed row is not evidence that the reserved call survived.
                    self.assertEqual(runtime.db.execute('SELECT status FROM execution_work WHERE work_id=?',
                                                        (receipt.work_id,)).fetchone(), ('claimed',))
                    view = await self.projection(runtime, receipt.execution_id)
                    self.assertEqual((view.status, view.action, view.reason),
                                     ('blocked', 'resolve', 'attempt_budget_exhausted'))
                    stopped = await self.command(runtime, receipt.execution_id, key='after-stop')
                    self.assertEqual(stopped.disposition, 'resolve')
                    self.assertNotIn('retry', stopped.allowed_actions)
                    self.assertEqual(runtime.db.execute('SELECT owner_attempts,owner_budget FROM story_operations').fetchone(), budget)
                    self.assertEqual(calls, 2)

    async def test_cancelled_concurrent_consumer_fences_waiting_continue_admission(self):
        import backend.continue_command as command
        async with self.source() as (runtime, ref, _):
            token = (await self.projection(runtime, ref.execution_id)).occ_token
            intent = self.intent(ref)
            entered, release = asyncio.Event(), asyncio.Event()
            original = command.validate_story_storage
            validations = 0

            async def gated(*args):
                nonlocal validations
                validations += 1
                await original(*args)
                if validations == 1:
                    entered.set()
                    await release.wait()

            with patch.object(command, 'validate_story_storage', side_effect=gated):
                first = asyncio.create_task(self.command(runtime, ref.execution_id, key='waiting-A',
                                                         token=token, intent=intent))
                try:
                    await asyncio.wait_for(entered.wait(), 5)
                    second = await self.command(runtime, ref.execution_id, key='accepting-B', token=token, intent=intent)
                    runtime.cancel(second.effective_execution_id, 'cancel-consumer')
                    release.set()
                    with self.assertRaisesRegex(ValueError, 'Stale Continue token'):
                        await first
                    view = await self.projection(runtime, ref.execution_id)
                    self.assertEqual((view.status, view.action, view.reason), ('cancelling', 'resolve', 'cancelling'))
                    self.assertIsNone(view.work_id)
                    self.assertEqual(runtime.db.execute("SELECT receipt_body FROM continue_commands WHERE command_key='waiting-A'")
                                     .fetchone(), (None,))
                    self.assertEqual(runtime.db.execute('SELECT COUNT(*) FROM image_groups').fetchone(), (1,))
                    self.assertEqual(await self.command(runtime, ref.execution_id, key='accepting-B', token=token, intent=intent), second)
                    self.no_units(runtime.db)
                finally:
                    release.set()
                    await asyncio.gather(first, return_exceptions=True)


if __name__ == '__main__':
    unittest.main()
