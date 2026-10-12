"""7.2 exact result delivery on the real SQLite saver, without provider scheduling."""

import asyncio
import subprocess
import sys
from typing import Any
import unittest
from unittest.mock import patch

from backend import image_group_results as results, image_group_store as groups
from backend.story_control import open_story_runtime
from tests import test_image_group_results as storage, test_image_group_store as admission
from tests import test_story_wardrobe_api as fixtures
from tests.test_story_wardrobe_runtime import retained_inventory


class ImageResultRuntimeTests(fixtures.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    death_phases = ('resume', 'wait-writes', 'wait-checkpoint', 'join-commit', 'join-writes')
    source: Any = storage.ImageGroupResultTests.source
    arguments: Any = storage.ImageGroupResultTests.arguments
    context: Any = storage.ImageGroupResultTests.context
    complete: Any = storage.ImageGroupResultTests.complete
    unit: Any = storage.ImageGroupResultTests.unit
    start: Any = storage.ImageGroupResultTests.start
    publish: Any = storage.ImageGroupResultTests.publish
    forbidden_effects: Any = admission.ImageGroupStoreTests.forbidden_effects

    def setUp(self):
        super().setUp()
        self.results, self.store, self.refs = results, groups, storage.refs
        self.profile = storage.pins.production_catalog()['image_only']['profiles'][0]['pin']

    def finish(self, runtime, receipt, *, failed=False):
        for index in range(2 if failed else 3):
            self.unit(runtime.db, receipt.execution_id, index, finish='failed' if failed and index == 1 else 'completed')
        return self.publish(runtime.db, receipt, status='failed' if failed else 'complete',
                            failed_unit_key='location' if failed else None)

    def fail_first(self, runtime, receipt):
        self.unit(runtime.db, receipt.execution_id, 0, finish='failed')
        return self.publish(runtime.db, receipt, status='failed', failed_unit_key='face-0')

    def wake_work(self, runtime, execution):
        return runtime.db.execute("SELECT status,settled_checkpoint_id FROM execution_work WHERE execution_id=? AND kind='resume'",
                                  (execution,)).fetchone()

    async def test_early_complete_result_binds_exact_wait_and_joins_without_effects(self):
        async with self.source() as (runtime, ref, _):
            before = retained_inventory(runtime.db, ref.execution_id)
            receipt = await self.start(runtime, ref)
            result = self.finish(runtime, receipt)
            with self.forbidden_effects(replay=True):
                self.assertEqual(await runtime.run(), 2)
            saved = await runtime.saver.aget_tuple({'configurable': {'thread_id': receipt.execution_id}})
            self.assertEqual(saved.metadata['step'], 3)
            self.assertEqual(saved.checkpoint['channel_values']['result_ref'],
                             dict(result_id=result.result_id, digest=result.digest, uri=result.uri, status=result.status))
            self.assertEqual(saved.checkpoint['channel_values']['batch_outputs'], result.result_id)
            self.assertEqual(self.wake_work(runtime, receipt.execution_id), ('completed', saved.checkpoint['id']))
            self.assertEqual(runtime.db.execute('SELECT outcome,source_id FROM execution_outcomes WHERE execution_id=?',
                                                (receipt.execution_id,)).fetchone(), ('completed', result.result_id))
            changes = runtime.db.total_changes
            with self.forbidden_effects(replay=True), patch('backend.story_runner._invoke', side_effect=AssertionError('Joined graph replayed')):
                self.assertEqual(await runtime.run(), 0)
            self.assertEqual(runtime.db.total_changes, changes)
            self.assertEqual(retained_inventory(runtime.db, ref.execution_id), before)

    async def test_real_death_pending_resume_wait_output_and_join_receipt_recover_exactly(self):
        phases = self.death_phases
        async with self.source() as (runtime, ref, _):
            before = retained_inventory(runtime.db, ref.execution_id)
            receipts = {}
            for phase in phases:
                receipt = await self.start(runtime, ref, key=phase)
                await runtime.run()
                result = self.fail_first(runtime, receipt)
                runtime.db.execute("UPDATE execution_work SET status='blocked' WHERE execution_id=? AND kind='resume'",
                                   (receipt.execution_id,))
                receipts[phase] = receipt, result
        child = '''
import asyncio, os, sys
from pathlib import Path
from backend import image_graph
from backend.story_control import open_story_runtime
phase, execution = sys.argv[2:4]
async def main():
    async with open_story_runtime(Path(sys.argv[1]), lambda *a: (_ for _ in ()).throw(AssertionError('Story invoked'))) as runtime:
        runtime.db.execute("UPDATE execution_work SET status='pending' WHERE execution_id=? AND kind='resume'", (execution,))
        put, writes = runtime.saver.aput, runtime.saver.aput_writes
        async def crash_put(config, checkpoint, metadata, versions):
            result = await put(config, checkpoint, metadata, versions)
            if phase == 'wait-checkpoint' and metadata['step'] == 2: os._exit(23)
            return result
        async def crash_writes(config, values, task_id, task_path=''):
            result = await writes(config, values, task_id, task_path=task_path)
            if (phase == 'resume' and any(c == '__resume__' for c, _ in values) or
                phase == 'wait-writes' and any(c == 'result_ref' for c, _ in values) or
                phase == 'join-writes' and any(c == 'batch_outputs' for c, _ in values)): os._exit(23)
            return result
        join = image_graph.join_image_group_result
        def crash_join(*args, **kwargs):
            result = join(*args, **kwargs)
            if phase == 'join-commit': os._exit(23)
            return result
        runtime.saver.aput, runtime.saver.aput_writes = crash_put, crash_writes
        image_graph.join_image_group_result = crash_join
        await runtime.run()
asyncio.run(main())
'''
        for phase, (receipt, result) in receipts.items():
            with self.subTest(phase=phase):
                dead = subprocess.run([sys.executable, '-B', '-c', child, str(self.root), phase, receipt.execution_id],
                                      capture_output=True, text=True, timeout=60)
                self.assertEqual(dead.returncode, 23, dead.stderr)
                async with open_story_runtime(self.root, lambda *a: self.fail('Story invoked')) as runtime:
                    saved_before = await runtime.saver.aget_tuple({'configurable': {'thread_id': receipt.execution_id}})
                    self.assertEqual(saved_before.metadata['step'], 1 if phase in ('resume', 'wait-writes') else 2)
                    if phase == 'resume':
                        self.assertIn((groups.read_image_group(runtime.db, receipt.execution_id).task_id,
                                       '__resume__', [dict(result_id=result.result_id, digest=result.digest,
                                                          uri=result.uri, status=result.status)]), saved_before.pending_writes)
                    if phase == 'wait-writes':
                        self.assertIn('__resume__', [c for _, c, _ in saved_before.pending_writes], repr(saved_before.pending_writes))
                    from backend import story_runner
                    original = story_runner._invoke
                    inputs = []
                    async def record(*args):
                        inputs.append(args[2])
                        return await original(*args)
                    with self.forbidden_effects(replay=True), patch.object(story_runner, '_invoke', record):
                        self.assertEqual(await runtime.run(), 1)
                    self.assertEqual(inputs, [] if phase.startswith('join-') else [None])
                    saved_after = await runtime.saver.aget_tuple({'configurable': {'thread_id': receipt.execution_id}})
                    if phase.startswith('join-'):
                        self.assertEqual(saved_after, saved_before, 'Terminal receipt must not replay the graph to reach END')
                    else:
                        self.assertEqual(saved_after.metadata['step'], 3)
                    self.assertEqual(self.wake_work(runtime, receipt.execution_id), ('completed', saved_after.checkpoint['id']))
                    self.assertEqual(runtime.db.execute('SELECT outcome,source_id FROM execution_outcomes WHERE execution_id=?',
                                                        (receipt.execution_id,)).fetchone(), ('failed', result.result_id))
                    changes = runtime.db.total_changes
                    self.assertEqual(await runtime.run(), 0)
                    self.assertEqual(runtime.db.total_changes, changes)
                    self.assertEqual(retained_inventory(runtime.db, ref.execution_id), before)

    async def test_postwait_checkpoint_and_join_receipt_tamper_block_before_invocation(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            self.fail_first(runtime, receipt)
            await runtime.run()
            saved = await runtime.saver.aget_tuple({'configurable': {'thread_id': receipt.execution_id}})
            original = dict(saved.checkpoint)
            checkpoint = {**original, 'channel_values': {**original['channel_values'], 'batch_outputs': 'foreign'}}
            await runtime.saver.aput(saved.config, checkpoint, saved.metadata, {})
            with patch('backend.story_runner._invoke', side_effect=AssertionError('Tampered join invoked')), self.assertRaises(ValueError):
                await runtime.run()
            self.assertEqual(runtime.db.execute("SELECT status FROM execution_work WHERE execution_id=? AND kind='reconcile'",
                                                (receipt.execution_id,)).fetchone(), ('blocked',))

    async def test_cancel_during_resume_ancestor_read_preempts_delivery_and_keeps_result(self):
        async with self.source() as (runtime, ref, _):
            before = retained_inventory(runtime.db, ref.execution_id)
            receipt = await self.start(runtime, ref)
            await runtime.run()
            result = self.fail_first(runtime, receipt)
            original = runtime.saver.aget_tuple
            reads = 0
            async def cancel_during_read(*args, **kwargs):
                nonlocal reads
                saved = await original(*args, **kwargs)
                reads += 1
                if reads == 3:
                    runtime.cancel(receipt.execution_id, 'cancel-in-read')
                return saved
            with patch.object(runtime.saver, 'aget_tuple', cancel_during_read), \
                    patch('backend.story_runner._invoke', side_effect=AssertionError('Cancelled result delivered')):
                self.assertEqual(await runtime.run(), 1)
            self.assertEqual(reads, 3, 'No more saver awaits after cancellation is observed')
            self.assertEqual(runtime.db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                                (receipt.execution_id,)).fetchone(), ('cancelled',))
            self.assertEqual(self.wake_work(runtime, receipt.execution_id)[0], 'obsolete')
            self.assertEqual(results.read_image_group_result(runtime.db, receipt.execution_id), result)
            self.assertEqual(retained_inventory(runtime.db, ref.execution_id), before)

    async def test_retry_command_shutdown_uses_existing_drain_lifetime(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            result = self.fail_first(runtime, receipt)
            entered, release = asyncio.Event(), asyncio.Event()
            original = groups.retry_image_execution
            async def gated(*args, **kwargs):
                entered.set()
                await release.wait()
                return await original(*args, **kwargs)
            args = dict(predecessor_execution_id=receipt.execution_id, expected_result_digest=result.digest)
            with patch.object(groups, 'retry_image_execution', gated):
                retrying = asyncio.create_task(runtime.retry_images(self.project, 'retry', **args))
                await asyncio.wait_for(entered.wait(), 5)
                closing = asyncio.create_task(runtime.close())
                try:
                    await asyncio.sleep(0.1)
                    self.assertFalse(closing.done())
                    with self.assertRaisesRegex(ValueError, 'closed'):
                        await runtime.retry_images(self.project, 'later', **args)
                finally:
                    release.set()
                    retry = await retrying
                    await closing
                self.assertEqual(runtime.db.execute('SELECT status FROM execution_work WHERE work_id=?',
                                                    (retry.work_id,)).fetchone(), ('pending',))

    async def test_result_published_during_sweep_read_does_not_create_second_segment(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            await runtime.run()
            self.unit(runtime.db, receipt.execution_id, 0, finish='failed')
            original = runtime.saver.aget_tuple
            result = None
            async def publish_during_read(*args, **kwargs):
                nonlocal result
                saved = await original(*args, **kwargs)
                if args[0]['configurable']['thread_id'] == receipt.execution_id and result is None:
                    result = self.publish(runtime.db, receipt, status='failed', failed_unit_key='face-0')
                return saved
            with self.forbidden_effects(replay=True), patch.object(runtime.saver, 'aget_tuple', publish_during_read):
                self.assertEqual(await runtime.run(), 1)
            self.assertIsNotNone(result)
            self.assertEqual(runtime.db.execute("SELECT COUNT(*) FROM execution_work WHERE execution_id=? AND kind='reconcile'",
                                                (receipt.execution_id,)).fetchone(), (0,))
            self.assertEqual(self.wake_work(runtime, receipt.execution_id)[0], 'completed')

    async def test_terminal_outcome_without_checkpoint_or_join_blocks_as_integrity_error(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            runtime.db.execute("INSERT INTO execution_outcomes VALUES (?,'failed',?,NULL)",
                               (receipt.execution_id, receipt.group_id))
            with patch('backend.story_runner._invoke', side_effect=AssertionError('Receiptless terminal invoked')), self.assertRaises(ValueError):
                await runtime.run()
            self.assertEqual(runtime.db.execute('SELECT status FROM execution_work WHERE work_id=?',
                                                (receipt.work_id,)).fetchone(), ('blocked',))

    async def test_error_after_consumed_wait_missettled_work_reconciles_with_original_request_digest(self):
        from backend import image_graph, story_runner
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            await runtime.run()
            self.fail_first(runtime, receipt)
            with patch.object(image_graph, 'join_image_group_result', side_effect=RuntimeError('Join crashed')), self.assertRaisesRegex(RuntimeError, 'Join crashed'):
                await runtime.run()
            saved = await runtime.saver.aget_tuple({'configurable': {'thread_id': receipt.execution_id}})
            self.assertEqual(saved.metadata['step'], 2)
            self.assertIn('__error__', [channel for _, channel, _ in saved.pending_writes])
            runtime.db.execute("UPDATE execution_work SET status='completed' WHERE execution_id=? AND kind='resume'", (receipt.execution_id,))
            inputs = []
            invoke = story_runner._invoke
            async def record(*args):
                inputs.append(args[2])
                return await invoke(*args)
            with self.forbidden_effects(replay=True), patch.object(story_runner, '_invoke', record):
                self.assertEqual(await runtime.run(), 1)
            self.assertEqual(inputs, [None])
            self.assertEqual(runtime.db.execute("SELECT status,payload_digest,resume_ref FROM execution_work WHERE execution_id=? AND kind='reconcile'",
                                                (receipt.execution_id,)).fetchone(), ('completed', receipt.request_digest, None))

    async def test_old_failed_result_cannot_answer_retry_wait_even_by_direct_command(self):
        from langgraph.types import Command
        from backend.image_graph import build_image_graph, image_result_ref
        from backend.story_runner import _InvocationSaver, _invoke
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            result = self.fail_first(runtime, receipt)
            retry = await runtime.retry_images(self.project, 'retry', predecessor_execution_id=receipt.execution_id,
                                               expected_result_digest=result.digest)
            await runtime.run()
            group = groups.read_image_group(runtime.db, retry.execution_id)
            graph = build_image_graph(runtime.db, _InvocationSaver(runtime.saver), group)
            with self.forbidden_effects(replay=True), self.assertRaisesRegex(ValueError, 'Unsolicited'):
                await _invoke(runtime.db, graph, Command(resume={group.interrupt_id: image_result_ref(result)}),
                              {'configurable': {'thread_id': retry.execution_id}}, retry.execution_id, None)
            with patch('backend.story_runner._invoke', side_effect=AssertionError('Old result redelivered')), self.assertRaises(ValueError):
                await runtime.run()
            self.assertIsNone(runtime.db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                                (retry.execution_id,)).fetchone())
            self.assertEqual(runtime.db.execute("SELECT status FROM execution_work WHERE execution_id=? AND kind='reconcile'",
                                                (retry.execution_id,)).fetchone(), ('blocked',))

    async def test_stop_during_resume_read_keeps_claim_and_checkpoint_for_reopen(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            await runtime.run()
            result = self.fail_first(runtime, receipt)
            saved_before = await runtime.saver.aget_tuple({'configurable': {'thread_id': receipt.execution_id}})
            original = runtime.saver.aget_tuple
            reads = 0
            async def stop_during_read(*args, **kwargs):
                nonlocal reads
                saved = await original(*args, **kwargs)
                reads += 1
                if reads == 3:
                    runtime._stopping.set()
                return saved
            with patch.object(runtime.saver, 'aget_tuple', stop_during_read), \
                    patch('backend.story_runner._invoke', side_effect=AssertionError('Stopped result delivered')):
                self.assertEqual(await runtime.run(), 1)
            self.assertEqual(reads, 3)
            self.assertEqual(self.wake_work(runtime, receipt.execution_id), ('claimed', None))
            self.assertEqual(await runtime.saver.aget_tuple({'configurable': {'thread_id': receipt.execution_id}}), saved_before)
        async with open_story_runtime(self.root, lambda *a: self.fail('Story invoked')) as runtime:
            self.assertEqual(await runtime.run(), 1)
            self.assertEqual(runtime.db.execute('SELECT outcome,source_id FROM execution_outcomes WHERE execution_id=?',
                                                (receipt.execution_id,)).fetchone(), ('failed', result.result_id))

    async def test_early_wake_selected_before_start_stays_pending_until_binding(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            self.finish(runtime, receipt)
            runtime.db.execute("UPDATE execution_work SET rowid=-1 WHERE execution_id=? AND kind='resume'", (receipt.execution_id,))
            self.assertEqual(await runtime.run(), 2)
            self.assertEqual(self.wake_work(runtime, receipt.execution_id), ('pending', None))
            self.assertIsNotNone(groups.read_image_group(runtime.db, receipt.execution_id).checkpoint_id)
            self.assertIsNone(runtime.db.execute('SELECT outcome FROM execution_outcomes WHERE execution_id=?',
                                                (receipt.execution_id,)).fetchone())
            self.assertEqual(await runtime.run(), 1)
            self.assertEqual(self.wake_work(runtime, receipt.execution_id)[0], 'completed')

    async def test_failed_result_and_private_retry_before_old_wait_keep_distinct_wakes(self):
        async with self.source() as (runtime, ref, _):
            before = retained_inventory(runtime.db, ref.execution_id)
            receipt = await self.start(runtime, ref)
            result = self.finish(runtime, receipt, failed=True)
            self.assertTrue(callable(getattr(runtime, 'retry_images', None)), 'Private runtime image Retry is missing')
            retry = await runtime.retry_images(self.project, 'retry', predecessor_execution_id=receipt.execution_id,
                                               expected_result_digest=result.digest)
            with self.forbidden_effects(replay=True):
                self.assertEqual(await runtime.run(), 3)
            saved = await runtime.saver.aget_tuple({'configurable': {'thread_id': receipt.execution_id}})
            self.assertIsNone(saved.checkpoint['channel_values']['batch_outputs'])
            self.assertEqual(runtime.db.execute('SELECT outcome,source_id FROM execution_outcomes WHERE execution_id=?',
                                                (receipt.execution_id,)).fetchone(), ('failed', result.result_id))
            new_saved = await runtime.saver.aget_tuple({'configurable': {'thread_id': retry.execution_id}})
            self.assertEqual(new_saved.metadata['step'], 1)
            self.assertNotIn('result_ref', new_saved.checkpoint['channel_values'])
            self.assertNotEqual(groups.read_image_group(runtime.db, retry.execution_id).interrupt_id,
                                groups.read_image_group(runtime.db, receipt.execution_id).interrupt_id)
            changes = runtime.db.total_changes
            self.assertEqual(await runtime.retry_images(self.project, 'retry', predecessor_execution_id=receipt.execution_id,
                                                       expected_result_digest=result.digest), retry)
            self.assertEqual(await runtime.run(), 0)
            self.assertEqual(runtime.db.total_changes, changes)
            self.assertEqual(retained_inventory(runtime.db, ref.execution_id), before)


if __name__ == '__main__':
    unittest.main()
