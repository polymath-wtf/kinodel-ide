"""Image-only activation through the single local runner; no rendering effects."""

import asyncio
from contextlib import ExitStack
import subprocess
import sys
from typing import Any
import unittest
from unittest.mock import patch
from uuid import uuid4

from backend import image_group_store as store
from backend.production import production_catalog
from backend.story_control import open_story_runtime
from tests import test_story_wardrobe_api as fixtures
from tests import test_image_group_store as storage_fixtures
from tests.test_story_wardrobe_runtime import retained_inventory


fixture_methods: Any = storage_fixtures.ImageGroupStoreTests


class ImageRuntimeTests(fixtures.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    source = fixture_methods.source
    arguments = fixture_methods.arguments
    no_units = fixture_methods.no_units
    forbidden_effects = fixture_methods.forbidden_effects

    def setUp(self):
        super().setUp()
        self.store = store
        self.profile = production_catalog()['image_only']['profiles'][0]['pin']

    async def accept(self, runtime, ref, key='images'):
        self.assertTrue(callable(getattr(runtime, 'start_images', None)), 'Private runtime image start is missing')
        return await runtime.start_images(self.project, key, **self.arguments(ref))

    def work(self, runtime, receipt):
        return runtime.db.execute('SELECT status,settled_checkpoint_id FROM execution_work WHERE work_id=?',
                                  (receipt.work_id,)).fetchone()

    def no_production(self, runtime, stack):
        stack.enter_context(self.forbidden_effects(replay=True))
        stack.enter_context(patch.object(runtime, 'produce_story', side_effect=AssertionError('Story producer invoked')))

    async def test_private_start_full_order_one_wait_repeat_and_reopen_are_read_only(self):
        async with self.source(('comedian', 'fox')) as (runtime, ref, plan):
            before = retained_inventory(runtime.db, ref.execution_id)
            receipt = await self.accept(runtime, ref)
            with ExitStack() as stack:
                self.no_production(runtime, stack)
                self.assertEqual(await runtime.run(), 1)
                group = store.read_image_group(runtime.db, receipt.execution_id)
                self.assertTrue(all((group.checkpoint_id, group.task_id, group.interrupt_id)))
                self.assertEqual(self.work(runtime, receipt), ('completed', group.checkpoint_id))
                self.assertEqual(group.batch.prepared_input.ordered_units, plan.batch_prompt)
                self.assertEqual(len(plan.batch_prompt), 5)
                self.assertFalse(group.batch.prepared_input.profile_snapshot['can_run'])
                saved = await runtime.saver.aget_tuple({'configurable': {'thread_id': receipt.execution_id}})
                self.assertEqual(saved.checkpoint['channel_values']['wait_ref'], group.wait_token)
                self.assertNotIn('review_ref', saved.checkpoint['channel_values'])
                self.assertEqual(runtime.db.execute('SELECT COUNT(*) FROM review_requests WHERE execution_id=?',
                                                    (receipt.execution_id,)).fetchone(), (0,))
                changes = runtime.db.total_changes
                with patch('backend.story_runner._invoke', side_effect=AssertionError('Wait reinvoked')):
                    self.assertEqual(await runtime.run(), 0)
                    self.assertEqual(await self.accept(runtime, ref), receipt)
                self.assertEqual(runtime.db.total_changes, changes)
                self.assertEqual(retained_inventory(runtime.db, ref.execution_id), before)
                self.no_units(runtime.db)
        async with open_story_runtime(self.root, lambda *a: self.fail('Story invoked'), character_root=self.library) as runtime:
            with self.forbidden_effects(replay=True), patch('backend.story_runner._invoke', side_effect=AssertionError('Reopen reinvoked')):
                changes = runtime.db.total_changes
                self.assertEqual(await self.accept(runtime, ref), receipt)
                self.assertEqual(await runtime.run(), 0)
                self.assertEqual(store.read_image_group(runtime.db, receipt.execution_id), group)
                self.assertEqual(await runtime.saver.aget_tuple({'configurable': {'thread_id': receipt.execution_id}}), saved)
                self.assertEqual(runtime.db.total_changes, changes)
                self.assertEqual(retained_inventory(runtime.db, ref.execution_id), before)

    async def test_cancel_before_start_and_at_wait_settles_only_consumer(self):
        async with self.source() as (runtime, ref, _):
            before = retained_inventory(runtime.db, ref.execution_id)
            for phase in ('start', 'wait'):
                receipt = await self.accept(runtime, ref, key=phase)
                with ExitStack() as stack:
                    self.no_production(runtime, stack)
                    if phase == 'wait':
                        await runtime.run()
                    runtime.cancel(receipt.execution_id, 'cancel')
                    with patch('backend.story_runner._invoke', side_effect=AssertionError('Cancelled graph invoked')):
                        await runtime.run()
                    self.assertEqual(runtime.db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                                        (receipt.execution_id,)).fetchone(), ('cancelled',))
                    self.assertEqual(await self.accept(runtime, ref, key=phase), receipt)
                    self.assertEqual(await runtime.run(), 0)
                    self.assertEqual(retained_inventory(runtime.db, ref.execution_id), before)
                    self.no_units(runtime.db)

    async def test_ordinary_story_response_and_retry_cannot_answer_external_wait(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.accept(runtime, ref)
            await runtime.run()
            with self.assertRaises(ValueError):
                runtime.respond(receipt.execution_id, receipt.wait_id, receipt.request_digest, 1, 'answer', 'approve', None)
            with self.assertRaises(ValueError):
                runtime.retry(receipt.execution_id, receipt.work_id, 'retry', 0)
            self.assertEqual(await runtime.run(), 0)
            self.assertIsNone(runtime.db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                                (receipt.execution_id,)).fetchone())

    async def test_wrong_graph_identity_is_blocked_without_story_dispatch(self):
        async with self.source() as (runtime, ref, _):
            for field, value in (('graph_id', 'kinodel.internal-story'), ('graph_version', 'other'),
                                 ('graph_digest', 'sha256:' + '0' * 64)):
                receipt = await self.accept(runtime, ref, key=field)
                runtime.db.execute(f'UPDATE executions SET {field}=? WHERE execution_id=?', (value, receipt.execution_id))
                with ExitStack() as stack:
                    self.no_production(runtime, stack)
                    stack.enter_context(patch('backend.story_runner._invoke', side_effect=AssertionError('Wrong graph invoked')))
                    with self.assertRaises(ValueError):
                        await runtime.run()
                self.assertEqual(self.work(runtime, receipt)[0], 'blocked')
                self.assertIsNone(await runtime.saver.aget_tuple({'configurable': {'thread_id': receipt.execution_id}}))

    async def test_checkpoint_identity_token_and_bound_triple_tamper_block_in_sweep(self):
        async with self.source() as (runtime, ref, _):
            for field in ('project_id', 'execution_id', 'group_ref', 'wait_ref', 'checkpoint_id', 'task_id', 'interrupt_id'):
                receipt = await self.accept(runtime, ref, key=field)
                await runtime.run()
                group = store.read_image_group(runtime.db, receipt.execution_id)
                config = {'configurable': {'thread_id': receipt.execution_id}}
                if field in ('checkpoint_id', 'task_id', 'interrupt_id'):
                    runtime.db.execute(f'UPDATE image_groups SET {field}=? WHERE execution_id=?', ('wrong', receipt.execution_id))
                else:
                    saved = await runtime.saver.aget_tuple(config)
                    checkpoint = dict(saved.checkpoint)
                    values = dict(checkpoint['channel_values'])
                    values[field] = str(uuid4()) if field.endswith('_id') else {'wrong': 'token'}
                    checkpoint['channel_values'] = values
                    await runtime.saver.aput(saved.config, checkpoint, saved.metadata, {})
                with ExitStack() as stack:
                    self.no_production(runtime, stack)
                    stack.enter_context(patch('backend.story_runner._invoke', side_effect=AssertionError('Tampered graph invoked')))
                    with self.assertRaises(ValueError):
                        await runtime.run()
                self.assertEqual(runtime.db.execute("SELECT status FROM execution_work WHERE execution_id=? AND kind='reconcile'",
                                                    (receipt.execution_id,)).fetchone(), ('blocked',))
                self.assertEqual(runtime.db.execute('SELECT COUNT(*) FROM execution_outcomes WHERE execution_id=?',
                                                    (receipt.execution_id,)).fetchone(), (0,))
                # Isolate this corrupt retained execution from the next subcase's sweep.
                self.assertIsNotNone(group.checkpoint_id)

    async def test_persisted_resume_or_alien_pending_write_rejected_before_invocation(self):
        async with self.source() as (runtime, ref, _):
            for channel, value in (('__resume__', ['unsolicited']), ('wait_ref', ['unsolicited']),
                                   ('branch:to:exact_complete_set_join', ['unsolicited']),
                                   ('__interrupt__', ['unsolicited']), ('__interrupt__', None)):
                receipt = await self.accept(runtime, ref, key=channel + str(value))
                await runtime.run()
                group = store.read_image_group(runtime.db, receipt.execution_id)
                saved = await runtime.saver.aget_tuple({'configurable': {'thread_id': receipt.execution_id}})
                await runtime.saver.aput_writes(saved.config, [(channel, value)], group.task_id)
                with patch('backend.story_runner._invoke', side_effect=AssertionError('Resume invoked')), self.assertRaises(ValueError):
                    await runtime.run()
                self.assertEqual(runtime.db.execute("SELECT status FROM execution_work WHERE execution_id=? AND kind='reconcile'",
                                                    (receipt.execution_id,)).fetchone(), ('blocked',))

    async def test_runnable_checkpoint_missettled_is_reconciled_with_none(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.accept(runtime, ref)
            original = runtime.saver.aput
            async def fail_before_wait(config, checkpoint, metadata, versions):
                if 'branch:to:group_wait' in checkpoint['channel_values']:
                    raise RuntimeError('before wait checkpoint')
                return await original(config, checkpoint, metadata, versions)
            with patch.object(runtime.saver, 'aput', fail_before_wait), self.assertRaisesRegex(RuntimeError, 'before wait'):
                await runtime.run()
            runtime.db.execute("UPDATE execution_work SET status='completed' WHERE work_id=?", (receipt.work_id,))
            from backend import story_runner
            invoke = story_runner._invoke
            inputs = []
            async def record(*args):
                inputs.append(args[2])
                return await invoke(*args)
            with self.forbidden_effects(replay=True), patch.object(story_runner, '_invoke', record):
                self.assertEqual(await runtime.run(), 1)
            self.assertEqual(inputs, [None])
            group = store.read_image_group(runtime.db, receipt.execution_id)
            self.assertIsNotNone(group.checkpoint_id)
            self.assertEqual(runtime.db.execute("SELECT status,settled_checkpoint_id FROM execution_work WHERE kind='reconcile'",
                                                ).fetchone(), ('completed', group.checkpoint_id))
            self.assertEqual(await runtime.run(), 0)

    async def test_missing_accepted_bytes_blocks_start_without_preparation_or_dispatch(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.accept(runtime, ref)
            group = store.read_image_group(runtime.db, receipt.execution_id)
            (self.root / group.batch.uri.removeprefix('kinodel://')).unlink()
            with ExitStack() as stack:
                self.no_production(runtime, stack)
                stack.enter_context(patch('backend.story_runner._invoke', side_effect=AssertionError('Missing batch invoked')))
                with self.assertRaises((ValueError, OSError)):
                    await runtime.run()
            self.assertEqual(self.work(runtime, receipt)[0], 'blocked')
            self.no_units(runtime.db)

    async def test_null_or_retired_graph_identity_on_settled_image_still_gets_durable_block(self):
        async with self.source() as (runtime, ref, _):
            from backend import wardrobe_store
            for key, identity in (('null', (None, store.GRAPH_VERSION, store.GRAPH_DIGEST)),
                                  ('retired', (wardrobe_store.RETIRED_GRAPH_ID, wardrobe_store.RETIRED_GRAPH_VERSION,
                                               wardrobe_store.RETIRED_GRAPH_DIGEST))):
                receipt = await self.accept(runtime, ref, key=key)
                await runtime.run()
                runtime.db.execute('UPDATE executions SET graph_id=?,graph_version=?,graph_digest=? WHERE execution_id=?',
                                   (*identity, receipt.execution_id))
                with patch('backend.story_runner._invoke', side_effect=AssertionError('Wrong route invoked')):
                    with self.assertRaises(ValueError):
                        await runtime.run()
                self.assertEqual(runtime.db.execute("SELECT status FROM execution_work WHERE execution_id=? AND kind='reconcile'",
                                                    (receipt.execution_id,)).fetchone(), ('blocked',))

    async def test_checkpoint_ancestor_tamper_is_not_hidden_by_matching_latest_wait(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.accept(runtime, ref)
            await runtime.run()
            saved = await runtime.saver.aget_tuple({'configurable': {'thread_id': receipt.execution_id}})
            parent = await runtime.saver.aget_tuple(saved.parent_config)
            checkpoint = dict(parent.checkpoint)
            checkpoint['channel_values'] = {**checkpoint['channel_values'], 'execution_id': str(uuid4())}
            await runtime.saver.aput(parent.config, checkpoint, parent.metadata, {})
            with patch('backend.story_runner._invoke', side_effect=AssertionError('Alien lineage invoked')):
                with self.assertRaises(ValueError):
                    await runtime.run()
            self.assertEqual(runtime.db.execute("SELECT status FROM execution_work WHERE execution_id=? AND kind='reconcile'",
                                                (receipt.execution_id,)).fetchone(), ('blocked',))

    async def test_graph_rejects_unsolicited_answer_and_cannot_reach_join_or_complete(self):
        async with self.source() as (runtime, ref, _):
            from langgraph.types import Command
            from backend.image_graph import build_image_graph
            from backend.story_runner import _InvocationSaver, _invoke
            receipt = await self.accept(runtime, ref)
            await runtime.run()
            group = store.read_image_group(runtime.db, receipt.execution_id)
            graph = build_image_graph(runtime.db, _InvocationSaver(runtime.saver), group)
            with self.forbidden_effects(replay=True), self.assertRaisesRegex(ValueError, 'Unsolicited'):
                await _invoke(runtime.db, graph, Command(resume={group.interrupt_id: 'arbitrary'}),
                              {'configurable': {'thread_id': receipt.execution_id}}, receipt.execution_id, None)
            with patch('backend.story_runner._invoke', side_effect=AssertionError('Persisted answer invoked')):
                with self.assertRaises(ValueError):
                    await runtime.run()
            self.assertIsNone(runtime.db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                                (receipt.execution_id,)).fetchone())
            self.no_units(runtime.db)

    async def test_real_process_death_before_binding_and_after_binding_before_settlement(self):
        async with self.source() as (runtime, ref, _):
            before = retained_inventory(runtime.db, ref.execution_id)
            receipts = {phase: await self.accept(runtime, ref, key=phase) for phase in ('before', 'after')}
        child = '''
import asyncio, os, sys
from pathlib import Path
from backend import image_runner
from backend.story_control import open_story_runtime
phase = sys.argv[2]
bind = image_runner.bind_image_wait
def crash(*args, **kwargs):
    if phase == 'before': os._exit(23)
    result = bind(*args, **kwargs)
    os._exit(23)
image_runner.bind_image_wait = crash
async def main():
    async with open_story_runtime(Path(sys.argv[1]), lambda *a: (_ for _ in ()).throw(AssertionError('Story invoked'))) as runtime:
        await runtime.run()
asyncio.run(main())
'''
        for phase, receipt in receipts.items():
            result = subprocess.run([sys.executable, '-B', '-c', child, str(self.root), phase],
                                    capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 23, result.stderr)
            async with open_story_runtime(self.root, lambda *a: self.fail('Story invoked')) as runtime:
                group = store.read_image_group(runtime.db, receipt.execution_id)
                self.assertEqual(group.checkpoint_id is None, phase == 'before')
                saved = await runtime.saver.aget_tuple({'configurable': {'thread_id': receipt.execution_id}})
                self.assertIsNotNone(saved)
                with self.forbidden_effects(replay=True), patch('backend.story_runner._invoke', side_effect=AssertionError('Death replay reinvoked')):
                    # Only recover this phase; the next accepted start has not run yet.
                    other = receipts['after']
                    if phase == 'before':
                        runtime.db.execute("UPDATE execution_work SET status='blocked' WHERE work_id=?", (other.work_id,))
                    self.assertEqual(await runtime.run(), 1)
                settled = store.read_image_group(runtime.db, receipt.execution_id)
                self.assertEqual(settled.checkpoint_id, saved.config['configurable']['checkpoint_id'])
                if phase == 'after':
                    self.assertEqual(settled, group)
                self.assertEqual(self.work(runtime, receipt), ('completed', settled.checkpoint_id))
                self.assertEqual(retained_inventory(runtime.db, ref.execution_id), before)
                self.no_units(runtime.db)
                if phase == 'before':
                    runtime.db.execute("UPDATE execution_work SET status='pending' WHERE work_id=?", (other.work_id,))

    async def test_shutdown_drains_image_saver_and_commands_before_reopen(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.accept(runtime, ref)
            entered, release = asyncio.Event(), asyncio.Event()
            original = runtime.saver.aput
            async def gated(*args, **kwargs):
                entered.set()
                await release.wait()
                return await original(*args, **kwargs)
            with patch.object(runtime.saver, 'aput', gated):
                running = asyncio.create_task(runtime.run())
                await asyncio.wait_for(entered.wait(), 5)
                closing = asyncio.create_task(runtime.close())
                try:
                    await asyncio.sleep(0.15)
                    self.assertFalse(closing.done())
                    self.assertFalse(running.done())
                    with self.assertRaisesRegex(ValueError, 'closed'):
                        await self.accept(runtime, ref)
                finally:
                    release.set()
                    await asyncio.gather(running, closing)
            self.assertIsNone(runtime.db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                                (receipt.execution_id,)).fetchone())
        async with open_story_runtime(self.root, lambda *a: self.fail('Story invoked')) as runtime:
            self.assertEqual(await runtime.run(), 1)
            self.assertIsNotNone(store.read_image_group(runtime.db, receipt.execution_id).checkpoint_id)

    async def test_cancel_during_image_invocation_drains_started_saver_write(self):
        async with self.source() as (runtime, ref, _):
            before = retained_inventory(runtime.db, ref.execution_id)
            receipt = await self.accept(runtime, ref)
            entered, release = asyncio.Event(), asyncio.Event()
            original = runtime.saver.aput_writes
            async def gated(*args, **kwargs):
                entered.set()
                await release.wait()
                return await original(*args, **kwargs)
            with patch.object(runtime.saver, 'aput_writes', gated):
                running = asyncio.create_task(runtime.run())
                try:
                    await asyncio.wait_for(entered.wait(), 5)
                    runtime.cancel(receipt.execution_id, 'cancel')
                    await asyncio.sleep(0.15)
                    self.assertFalse(running.done())
                    self.assertIsNone(runtime.db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                                        (receipt.execution_id,)).fetchone())
                finally:
                    release.set()
                    await running
            self.assertEqual(runtime.db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                                (receipt.execution_id,)).fetchone(), ('cancelled',))
            self.assertEqual(retained_inventory(runtime.db, ref.execution_id), before)
            self.no_units(runtime.db)

    async def test_shutdown_drains_already_accepted_start_command_lifetime(self):
        async with self.source() as (runtime, ref, _):
            entered, release = asyncio.Event(), asyncio.Event()
            original = store.start_image_execution
            async def gated(*args, **kwargs):
                entered.set()
                await release.wait()
                return await original(*args, **kwargs)
            with patch.object(store, 'start_image_execution', gated):
                starting = asyncio.create_task(self.accept(runtime, ref))
                await asyncio.wait_for(entered.wait(), 5)
                closing = asyncio.create_task(runtime.close())
                try:
                    await asyncio.sleep(0.1)
                    self.assertFalse(closing.done())
                    with self.assertRaisesRegex(ValueError, 'closed'):
                        await self.accept(runtime, ref, key='later')
                finally:
                    release.set()
                    receipt = await starting
                    await closing
                self.assertEqual(self.work(runtime, receipt), ('pending', None))
        async with open_story_runtime(self.root, lambda *a: self.fail('Story invoked')) as runtime:
            self.assertEqual(await runtime.run(), 1)
            self.assertIsNotNone(store.read_image_group(runtime.db, receipt.execution_id).checkpoint_id)

    async def _sweep_cancel_race(self, *, corrupt):
        from backend import story_runner

        async with self.source() as (runtime, ref, _):
            source_before = retained_inventory(runtime.db, ref.execution_id)
            for read_number in (1, 2):  # Opening read, then the awaited checkpoint inspection.
                receipt = await self.accept(runtime, ref, key=f'race-{read_number}')
                await runtime.run()
                if corrupt:
                    runtime.db.execute('UPDATE image_groups SET task_id=? WHERE execution_id=?',
                                       ('alien-task', receipt.execution_id))
                group = store.read_image_group(runtime.db, receipt.execution_id)
                config = {'configurable': {'thread_id': receipt.execution_id}}
                saved = await runtime.saver.aget_tuple(config)
                original = runtime.saver.aget_tuple
                calls = 0
                cancel_work = None

                async def accept_cancel_during_read(*args, **kwargs):
                    nonlocal calls, cancel_work
                    result = await original(*args, **kwargs)
                    if args[0]['configurable']['thread_id'] == receipt.execution_id:
                        calls += 1
                        if calls == read_number:
                            cancel_work = runtime.cancel(receipt.execution_id, 'cancel-race')
                    return result

                with self.forbidden_effects(replay=True), patch.object(runtime.saver, 'aget_tuple', accept_cancel_during_read), \
                        patch.object(story_runner, '_invoke', side_effect=AssertionError('Sweep invoked graph')), \
                        patch.object(story_runner, '_finish_cancel', wraps=story_runner._finish_cancel) as finish:
                    self.assertEqual(await runtime.run(), 0, 'Sweep cancellation must settle before later work selection')
                    finish.assert_called_once_with(runtime.db, receipt.execution_id)
                self.assertIsNotNone(cancel_work)
                self.assertEqual(runtime.db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                                    (receipt.execution_id,)).fetchone(), ('cancelled',))
                self.assertEqual(runtime.db.execute('SELECT status FROM execution_work WHERE work_id=?',
                                                    (cancel_work,)).fetchone(), ('completed',))
                self.assertEqual(runtime.db.execute("SELECT COUNT(*) FROM execution_work WHERE execution_id=? AND kind='reconcile'",
                                                    (receipt.execution_id,)).fetchone(), (0,))
                self.assertEqual(store.read_image_group(runtime.db, receipt.execution_id), group)
                self.assertEqual(await runtime.saver.aget_tuple(config), saved)
                self.assertEqual(retained_inventory(runtime.db, ref.execution_id), source_before)
                self.assertEqual(await runtime.run(), 0)
                self.no_units(runtime.db)

    async def test_corrupt_settled_wait_cancel_during_sweep_read_preempts_integrity_diagnostic(self):
        await self._sweep_cancel_race(corrupt=True)

    async def test_healthy_settled_wait_cancel_during_sweep_read_settles_once_in_sweep(self):
        await self._sweep_cancel_race(corrupt=False)

    async def test_stop_during_corrupt_settled_wait_inspection_does_not_write_diagnostic(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.accept(runtime, ref)
            await runtime.run()
            runtime.db.execute('UPDATE image_groups SET task_id=? WHERE execution_id=?',
                               ('alien-task', receipt.execution_id))
            changes = runtime.db.total_changes
            original = runtime.saver.aget_tuple
            calls = 0

            async def stop_during_read(*args, **kwargs):
                nonlocal calls
                result = await original(*args, **kwargs)
                if args[0]['configurable']['thread_id'] == receipt.execution_id:
                    calls += 1
                    if calls == 2:
                        runtime._stopping.set()
                return result

            with patch.object(runtime.saver, 'aget_tuple', stop_during_read), \
                    patch('backend.story_runner._invoke', side_effect=AssertionError('Stopped sweep invoked graph')):
                self.assertEqual(await runtime.run(), 0)
            self.assertEqual(runtime.db.total_changes, changes)
            self.assertIsNone(runtime.db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                                (receipt.execution_id,)).fetchone())


del fixture_methods  # unittest discovers all module-level TestCase classes, including imported aliases.


if __name__ == '__main__':
    unittest.main()
