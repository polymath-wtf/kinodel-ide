"""Kill the lock/saver owner during Story review, revision and discussion; replay fresh."""

import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from story_process_support import ProcessStoryTest, parked, snapshot
from backend.api import fixture_story
from backend.story_control import open_story_runtime


async def child(root, mode, action=None):
    async with open_story_runtime(root, fixture_story) as runtime:
        db, saver = runtime.db, runtime.saver
        if mode in ('queue', 'setup'):
            await runtime.start(str(uuid4()), 'start', 'Лиса и свет', ['s1'])
            if mode == 'setup':
                await runtime.run()
            return
        eid = db.execute("SELECT execution_id FROM executions WHERE client_key='start'").fetchone()[0]
        if mode in ('inspect', 'recover'):
            processed = await runtime.run() if mode == 'recover' else None
            saved = await saver.aget_tuple({'configurable': {'thread_id': eid}})
            data = snapshot(runtime, saved)
            if mode == 'recover':
                data['processed'] = processed
            print(json.dumps(data), flush=True)
        elif mode in ('decide', 'duplicate'):
            row = db.execute("SELECT request_id,request_digest,binding_revision,action,message FROM review_requests "
                             "WHERE execution_id=? ORDER BY request_revision LIMIT 1", (eid,)).fetchone()
            selected = 'revise' if action == 'nonready' else action
            message = {'revise': 'Darker', 'clarify': 'Why?', 'nonready': 'needs_input: specify time'}
            if mode == 'decide':
                assert action in message, action
            receipt = runtime.respond(eid, row[0], row[1], row[2], 'key-' + row[0],
                                      row[3] if mode == 'duplicate' else selected,
                                      row[4] if mode == 'duplicate' else message[action or ''])
            if mode == 'decide':
                parked(mode)
            print(json.dumps(asdict(receipt)), flush=True)
        elif mode == 'wait':
            await runtime.run()
            parked(mode)  # Bound, unanswered wait; its work is already settled.
        elif mode == 'resume':
            original = saver.aput_writes

            async def after_writes(*args, **kwargs):
                result = await original(*args, **kwargs)
                if any(channel == '__resume__' for channel, _ in args[1]):
                    parked(mode)  # Real saver transaction finished, before decision application.
                return result

            with patch.object(saver, 'aput_writes', after_writes):
                await runtime.run()
            raise AssertionError('resume boundary not reached')
        else:
            import backend.story_graph as graph
            import backend.story_runner as runner
            if mode in ('bind', 'next_bind'):
                target, name = runner, 'bind_story_wait'
            else:
                target, name = graph, {'prepared': 'prepare_story_review', 'apply': 'apply_story_decision',
                                       'story': 'commit_story_operation', 'response': 'commit_owner_response'}[mode]
            original = getattr(target, name)

            def at_commit(*args, **kwargs):
                if mode == 'bind':
                    parked(mode)  # Interrupt saved, application wait binding not committed.
                original(*args, **kwargs)
                parked(mode)  # Actual commit completed, before checkpoint/work settlement.

            with patch.object(target, name, at_commit):
                await runtime.run()
            raise AssertionError(mode + ' boundary not reached')


class StoryProcessRecovery(ProcessStoryTest):
    child_script = Path(__file__)

    def test_prepared_review_before_wait(self):
        self.check_review('prepared')

    def test_saved_interrupt_before_binding(self):
        self.check_review('bind')

    def test_unanswered_bound_wait(self):
        self.check_review('wait')

    def check_review(self, mode):
        self.complete('queue')
        self.kill_at(mode)
        crashed = self.complete('inspect')
        review = crashed['reviews'][0]
        self.assertEqual(len(crashed['refs']), 1)
        self.assertEqual(crashed['work'][0][2], 'completed' if mode == 'wait' else 'claimed')
        self.assertEqual(review[5], crashed['checkpoint'] if mode == 'wait' else None)
        self.assertEqual(any(channel == '__interrupt__' for _, channel, _ in crashed['pending']), mode != 'prepared')
        if mode == 'prepared':
            self.assertNotIn('review_ref', crashed['state'])
        recovered = self.complete('recover')
        self.assertEqual(recovered['processed'], 0 if mode == 'wait' else 1)
        for key in ('execution', 'project', 'refs', 'stories', 'binding', 'current_ref', 'operations'):
            self.assertEqual(recovered[key], crashed[key], key)
        self.assertEqual(len(recovered['reviews']), 1)
        self.assertEqual(recovered['reviews'][0][:5], review[:5])
        self.assert_wait(recovered, 1)
        self.assertEqual(self.complete('recover'), dict(recovered, processed=0))

    def test_decision_accepted_before_resume(self):
        self.check_decision('decide')

    def test_persisted_resume_before_apply(self):
        self.check_decision('resume')

    def test_applied_revision_before_checkpoint(self):
        self.check_decision('apply')

    def test_revised_story_commit_before_checkpoint(self):
        self.check_decision('story')

    def test_next_wait_bound_before_old_work_settled(self):
        self.check_decision('next_bind')

    def test_clarification_commit_before_checkpoint(self):
        self.check_decision('response', 'clarify')

    def test_nonready_revision_commit_before_checkpoint(self):
        self.check_decision('response', 'nonready')

    def check_decision(self, mode, action='revise'):
        self.complete('setup')
        before = self.complete('inspect')
        self.kill_at('decide', action)
        receipt = self.complete('duplicate')
        if mode != 'decide':
            self.kill_at(mode)
        crashed = self.complete('inspect')
        old = crashed['reviews'][0]
        self.assertEqual(old[:8], before['reviews'][0][:8])
        self.assertEqual(old[8], receipt['decision_id'])
        self.assertEqual(crashed['work'][-1], ['resume', old[0], 'pending' if mode == 'decide' else 'claimed'])
        self.assertEqual(old[9] is not None, mode not in ('decide', 'resume'))
        if mode == 'resume':
            self.assertIn([old[6], '__resume__', [old[8]]], crashed['pending'])
        if mode == 'apply':
            self.assertNotEqual(crashed['state']['story_activation'], old[9])
        versions = 2 if action == 'revise' else 1
        self.assertEqual(len(crashed['refs']), 2 if mode in ('story', 'next_bind') else 1)
        if mode == 'story':
            self.assertEqual(crashed['state']['story_ref'], before['current_ref'])
        if mode == 'response':
            self.assertEqual(json.loads(crashed['operations'][-1][2])['status'],
                             'clarified' if action == 'clarify' else 'needs_input')
        if mode == 'next_bind':
            self.assertEqual(crashed['reviews'][1][5], crashed['checkpoint'])
        recovered = self.complete('recover')
        self.assertEqual(recovered['processed'], 1)
        self.assertEqual((recovered['execution'], recovered['project']), (before['execution'], before['project']))
        self.assertEqual(recovered['refs'][:len(crashed['refs'])], crashed['refs'])
        self.assertEqual(recovered['stories'][:len(crashed['stories'])], crashed['stories'])
        self.assertEqual(len(recovered['refs']), versions)
        self.assertEqual(recovered['binding'], [recovered['refs'][-1]['artifact_id'], versions])
        self.assertEqual(len(recovered['operations']), 2)
        if mode in ('story', 'response', 'next_bind'):
            self.assertEqual(recovered['operations'], crashed['operations'])
        self.assertEqual(len(recovered['reviews']), 2)
        applied, new = recovered['reviews']
        self.assertEqual(applied[:9], old[:9])
        self.assertIsNotNone(applied[9])
        if old[9] is not None:
            self.assertEqual(applied, old)
        self.assertEqual(new[10], old[0])
        self.assertNotEqual(new[0], old[0])
        self.assertNotEqual(new[6:8], old[6:8])
        if mode == 'next_bind':
            self.assertEqual(recovered['reviews'], crashed['reviews'])
        self.assert_wait(recovered, 2)
        self.assertEqual(self.complete('duplicate'), receipt)
        self.assertEqual(self.complete('recover'), dict(recovered, processed=0))

    def assert_wait(self, data, revision):
        review = data['reviews'][-1]
        self.assertEqual(data['current_ref'], data['refs'][-1])
        self.assertEqual(data['state']['story_ref'], data['current_ref'])
        self.assertEqual(data['state']['binding_revision'], data['binding'][1])
        self.assertEqual(review[2:6], [revision, data['binding'][1], data['binding'][0], data['checkpoint']])
        self.assertEqual(data['state']['review_ref'], dict(request_id=review[0], digest=review[1],
                                                        revision=revision, binding_revision=review[3]))
        self.assertTrue(review[7])
        self.assertIn([review[6], '__interrupt__', None], data['pending'])
        self.assertEqual(review[8:10], [None, None])
        self.assertTrue(all(work[2] == 'completed' for work in data['work']))
        self.assertIsNone(data['outcome'])


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--child':
        asyncio.run(child(Path(sys.argv[2]), sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None))
    else:
        unittest.main()
