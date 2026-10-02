"""Approval/cancel recovery after killing the real lock/saver-owning process."""

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
        db = runtime.db
        if mode == 'setup':
            await runtime.start(str(uuid4()), 'start', 'Лиса и свет', ['s1'])
            if action != 'queued':
                await runtime.run()
        before = snapshot(runtime)
        eid = before['execution']

        def approve():
            request = before['reviews'][-1]
            return runtime.respond(eid, request[0], request[1], request[3],
                                   'approve-once', 'approve', None)

        if mode == 'approve':
            approve()
            parked(mode)  # Accepted decision/work committed; no apply invocation yet.
        elif mode == 'approval_commit':
            import backend.story_graph as graph
            original = graph.apply_story_decision

            def after(*args):
                original(*args)
                parked(mode)  # Outcome committed; apply has not returned a checkpoint delta.

            with patch.object(graph, 'apply_story_decision', after):
                await runtime.run()
            raise AssertionError('Approval commit boundary not reached')
        elif mode == 'cancel':
            runtime.cancel(eid, 'cancel-once')
            parked(mode)
        elif mode == 'flight':
            entered = asyncio.Event()

            async def owner(*args, **kwargs):
                entered.set()
                await asyncio.Event().wait()

            runtime.produce_story = owner
            running = asyncio.create_task(runtime.run())
            await asyncio.wait_for(entered.wait(), timeout=10)
            assert not running.done()
            runtime.cancel(eid, 'cancel-once')
            parked(mode)  # Owner is really awaiting; no task/store cleanup before parent kill.
        elif mode == 'replay':
            receipt = (asdict(approve()) if action == 'approve' else
                       {'work_id': runtime.cancel(eid, 'cancel-once')})
            print(json.dumps(receipt), flush=True)
            return
        elif mode == 'reject':
            try:
                approve()
            except ValueError as error:
                print(json.dumps(str(error)), flush=True)
                return
            raise AssertionError('New decision accepted after cancellation')
        elif mode not in ('setup', 'inspect', 'recover'):
            raise ValueError(mode)

        processed = await runtime.run() if mode == 'recover' else None
        saved = await runtime.saver.aget_tuple({'configurable': {'thread_id': eid}})
        data = snapshot(runtime, saved)
        cancel = db.execute("SELECT work_id FROM execution_controls WHERE execution_id=? AND kind='cancel'",
                            (eid,)).fetchone()
        decision = db.execute("SELECT r.decision_id,w.work_id FROM review_requests r JOIN execution_work w "
                              "ON w.execution_id=r.execution_id AND w.kind='resume' AND w.source_id=r.request_id "
                              "WHERE r.execution_id=? AND r.action='approve'", (eid,)).fetchone()
        data['receipt'] = ({'work_id': cancel[0]} if cancel else
                           dict(zip(('decision_id', 'work_id'), decision)) if decision else None)
        data['processed'] = processed
        print(json.dumps(data), flush=True)


class ProcessStoryControls(ProcessStoryTest):
    child_script = Path(__file__)

    def recover_terminal(self, before, crashed, expected):
        recovered = self.complete('recover')
        self.assertGreater(recovered['processed'], 0)
        for key in ('execution', 'project', 'refs', 'stories', 'binding', 'current_ref'):
            self.assertEqual(crashed[key], before[key], key)
            self.assertEqual(recovered[key], crashed[key], key)
        for key in ('operations', 'receipt'):
            self.assertEqual(recovered[key], crashed[key], key)
        self.assertEqual([row[:9] + row[10:] for row in recovered['reviews']],
                         [row[:9] + row[10:] for row in crashed['reviews']])
        self.assertEqual(recovered['outcome'], expected)
        self.assertEqual([row[:2] for row in recovered['work']], [row[:2] for row in crashed['work']])
        self.assertTrue(all(row[2] in ('completed', 'obsolete') for row in recovered['work']))
        self.assertEqual(recovered['work'][-1][2], 'completed')
        self.assertEqual(self.complete('replay', 'approve' if expected[0] == 'completed' else 'cancel'),
                         crashed['receipt'])
        again = self.complete('recover')
        self.assertEqual(again, dict(recovered, processed=0))  # Immutable terminal/history; second restart idle.
        return recovered

    def test_approval_decision_persisted_before_apply(self):
        before = self.complete('setup')
        self.kill_at('approve')
        crashed = self.complete('inspect')
        self.assertEqual(crashed['checkpoint'], before['checkpoint'])
        self.assertIsNone(crashed['outcome'])
        self.assertIsNotNone(crashed['reviews'][0][8])
        self.assertIsNone(crashed['reviews'][0][9])
        self.assertEqual(crashed['work'][-1], ['resume', crashed['reviews'][0][0], 'pending'])
        recovered = self.recover_terminal(before, crashed, ['completed', before['reviews'][0][0], before['binding'][0]])
        self.assertEqual(recovered['state']['approved_story'], before['current_ref'])
        self.assertIsNotNone(recovered['reviews'][0][9])

    def test_approval_outcome_committed_before_final_checkpoint(self):
        before = self.complete('setup')
        self.kill_at('approve')
        self.kill_at('approval_commit')
        crashed = self.complete('inspect')
        self.assertEqual(crashed['outcome'], ['completed', before['reviews'][0][0], before['binding'][0]])
        self.assertIsNotNone(crashed['reviews'][0][9])
        self.assertNotIn('approved_story', crashed['state'])
        self.assertEqual(crashed['work'][-1][2], 'claimed')
        recovered = self.recover_terminal(before, crashed, crashed['outcome'])
        for key in ('checkpoint', 'state', 'pending', 'reviews'):
            self.assertEqual(recovered[key], crashed[key], key)  # Outcome wins without replaying graph END.

    def test_cancellation_accepted_while_waiting_review(self):
        before = self.complete('setup')
        self.kill_at('cancel')
        crashed = self.complete('inspect')
        self.assertIsNone(crashed['outcome'])
        self.assertEqual(crashed['reviews'], before['reviews'])
        self.assertEqual(crashed['work'][-1], ['cancel', 'cancel-once', 'pending'])
        self.assertEqual(self.complete('reject'), 'Execution is cancelling')
        recovered = self.recover_terminal(before, crashed, ['cancelled', 'cancel-once', None])
        self.assertEqual(recovered['refs'], before['refs'])
        self.assertEqual(recovered['reviews'], before['reviews'])

    def test_cancellation_accepted_with_owner_call_in_flight(self):
        before = self.complete('setup', 'queued')
        self.kill_at('flight')
        crashed = self.complete('inspect')
        self.assertEqual(crashed['execution'], before['execution'])
        self.assertIsNone(crashed['outcome'])
        self.assertEqual(crashed['refs'], [])
        self.assertEqual(crashed['work'][0][2], 'claimed')
        self.assertEqual(crashed['work'][-1], ['cancel', 'cancel-once', 'pending'])
        self.assertEqual(len(crashed['operations']), 1)
        recovered = self.recover_terminal(before, crashed, ['cancelled', 'cancel-once', None])
        self.assertEqual(recovered['work'][0][2], 'obsolete')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--child':
        asyncio.run(child(Path(sys.argv[2]), sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None))
    else:
        unittest.main()
