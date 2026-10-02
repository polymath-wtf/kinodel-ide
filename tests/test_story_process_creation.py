"""Actual process death at the three Story creation commit boundaries."""

import asyncio
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from story_process_support import ProcessStoryTest, parked, snapshot
from backend.api import fixture_story
from backend.domain import StoryV1, canonical_json, sha256_digest
from backend.story_control import open_story_runtime


async def child(root, mode):
    async with open_story_runtime(root, fixture_story) as runtime:
        if mode == 'start':
            await runtime.start(str(uuid4()), 'start', 'Лиса и свет', ['s1'])
            parked('start')
        elif mode in ('inspect', 'recover'):
            processed = await runtime.run() if mode == 'recover' else None
            eid = runtime.db.execute("SELECT execution_id FROM executions WHERE client_key='start'").fetchone()[0]
            saved = await runtime.saver.aget_tuple({'configurable': {'thread_id': eid}})
            data = snapshot(runtime, saved)
            if mode == 'recover':
                data['processed'] = processed
            print(json.dumps(data), flush=True)
        elif mode == 'file':
            import backend.story_store as store
            original = store._publish

            def after_publish(*args):
                original(*args)
                parked('file')  # Immutable bytes exist; metadata transaction has not begun.

            with patch.object(store, '_publish', after_publish):
                await runtime.run()
            raise AssertionError('file: publication boundary not reached')
        elif mode == 'story':
            import backend.story_graph as graph
            original = graph.commit_story_operation

            def after_commit(*args):
                original(*args)
                parked('story')  # DB result committed; the node has not returned its checkpoint delta.

            with patch.object(graph, 'commit_story_operation', after_commit):
                await runtime.run()
            raise AssertionError('story: DB commit boundary not reached')
        else:
            raise ValueError(mode)


class StoryProcessCreation(ProcessStoryTest):
    child_script = Path(__file__)

    def test_committed_start_before_checkpoint(self):
        self.check_creation('start')

    def test_published_file_before_db_commit(self):
        self.check_creation('file')

    def test_story_db_commit_before_checkpoint(self):
        self.check_creation('story')

    def check_creation(self, boundary):
        with self.subTest(boundary=boundary):
            if boundary != 'start':
                self.kill_at('start')
            self.kill_at(boundary)
            crashed = self.complete('inspect')
            eid = crashed['execution']
            self.assertEqual(crashed['work'], [['start', eid, 'pending' if boundary == 'start' else 'claimed']])
            self.assertEqual(crashed['reviews'], [])
            self.assertIsNone(crashed['outcome'])
            self.assertNotIn('story_ref', crashed['state'])
            self.assertFalse(any(channel == 'story_ref' for _, channel, _ in crashed['pending']))
            published = {path.name: sha256_digest(path.read_bytes())
                         for path in self.root.glob('projects/*/artifacts/*.json')}
            self.assertEqual(len(published), 0 if boundary == 'start' else 1)
            for name, digest in published.items():
                self.assertTrue(name.endswith(f'.{digest[7:]}.json'))
            self.assertEqual(len(crashed['refs']), 1 if boundary == 'story' else 0)
            if boundary == 'start':
                self.assertIsNone(crashed['checkpoint'])
                self.assertEqual(crashed['operations'], [])
            else:
                self.assertIsNotNone(crashed['checkpoint'])
                self.assertEqual(len(crashed['operations']), 1)
                self.assertEqual(crashed['operations'][0][1],
                                 crashed['refs'][0]['artifact_id'] if boundary == 'story' else None)
            if boundary != 'story':
                self.assertIsNone(crashed['binding'])
                self.assertIsNone(crashed['current_ref'])

            recovered = self.complete('recover')
            self.assertEqual(recovered['processed'], 1)
            self.assertEqual((recovered['execution'], recovered['project']), (eid, crashed['project']))
            self.assertEqual(len(recovered['refs']), 1)
            self.assertEqual(len(recovered['stories']), 1)
            ref = recovered['refs'][0]
            self.assertEqual(recovered['current_ref'], ref)
            self.assertEqual((ref['execution_id'], ref['project_id']), (eid, recovered['project']))
            self.assertEqual(recovered['binding'], [ref['artifact_id'], 1])
            self.assertEqual(ref['digest'], sha256_digest(canonical_json(StoryV1.model_validate(recovered['stories'][0]))))
            self.assertEqual(ref['uri'], f"kinodel://projects/{recovered['project']}/artifacts/{ref['artifact_id']}")
            self.assertEqual(recovered['operations'], [[ref['operation_id'], ref['artifact_id'], None]])
            self.assertEqual(recovered['state']['story_ref'], ref)
            self.assertEqual(recovered['state']['binding_revision'], 1)
            self.assertEqual(len(recovered['reviews']), 1)
            review = recovered['reviews'][0]
            self.assertEqual(review[2:6], [1, 1, ref['artifact_id'], recovered['checkpoint']])
            self.assertEqual(recovered['state']['review_ref'], dict(request_id=review[0], digest=review[1],
                                                                   revision=1, binding_revision=1))
            self.assertTrue(review[7])
            self.assertIn([review[6], '__interrupt__', None], recovered['pending'])
            self.assertEqual(review[8:], [None, None, None])
            self.assertIsNone(recovered['outcome'])
            self.assertEqual(recovered['work'], [['start', eid, 'completed']])
            if boundary != 'start':
                self.assertEqual(crashed['operations'][0][0], ref['operation_id'])
            if boundary == 'story':
                for key in ('refs', 'stories', 'binding', 'current_ref', 'operations'):
                    self.assertEqual(recovered[key], crashed[key], key)
            for name, digest in published.items():
                self.assertEqual(sha256_digest((self.root / 'projects' / recovered['project'] / 'artifacts' / name)
                                              .read_bytes()), digest)
            again = self.complete('recover')
            self.assertEqual(again, dict(recovered, processed=0), 'second recovery must be idle and unchanged')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--child':
        asyncio.run(child(Path(sys.argv[2]), sys.argv[3]))
    else:
        unittest.main()
