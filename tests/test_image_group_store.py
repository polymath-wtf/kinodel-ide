"""Image admission only: source-owned immutable membership, no production effects."""

from contextlib import asynccontextmanager, contextmanager, ExitStack, closing
import importlib.util
import json
import sqlite3
import subprocess
import sys
from typing import Any
import unittest
from unittest.mock import patch
from uuid import uuid4

from backend import batch_store, database, story_start, wardrobe_store
from backend.api import fixture_story
from backend.production import production_catalog
from backend.saver import open_saver
from backend.story_control import open_story_runtime
from tests import test_story_wardrobe_api as fixtures
from tests.test_batch_preparation import CONNECTION
from tests import test_database as database_tests
from tests.test_story_cast import draft
from tests.test_story_wardrobe_runtime import retained_inventory
from tests.test_wardrobe_compact_v2 import compact_draft


class ImageGroupStoreTests(fixtures.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('backend.image_group_store'), 'Image admission storage is missing')
        from backend import image_group_store
        self.store = image_group_store
        self.profile = production_catalog()['image_only']['profiles'][0]['pin']

    @asynccontextmanager
    async def source(self, subjects=('comedian',)):
        story = draft(cast=[{'subject_id': s, 'description': 'Traveler'} for s in subjects],
                      subject_ids=list(subjects))
        output = {'status': 'ready', 'plan': compact_draft(subjects), 'explanation': None}
        with self.transport(output), patch.object(fixtures, 'draft', return_value=story):
            async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
                receipt = await runtime.start_wardrobe(self.project, 'source', ['s1'], self.brief)
                await runtime.run()
                self.approve(runtime, receipt.execution_id)
                await runtime.run()
                ref, plan = wardrobe_store.read_wardrobe_plan(runtime.db, receipt.execution_id)
                yield runtime, ref, plan

    def arguments(self, ref, **changes):
        args = dict(source_plan_ref=ref.model_dump(mode='json'), image_size={'width': 768, 'height': 768},
                    image_profile=self.profile, connection=CONNECTION)
        args.update(changes)
        return args

    async def start(self, runtime, ref, key='images', project=None, **changes):
        return await self.store.start_image_execution(runtime.db, runtime.saver, project or self.project,
                                                       key, **self.arguments(ref, **changes))

    @contextmanager
    def forbidden_effects(self, *, replay=False):
        targets = ['backend.batch_generation.prepare_batch_unit', 'backend.comfyui_workflows.secrets.randbelow',
                   'httpx.Client.send', 'httpx.AsyncClient', 'socket.create_connection',
                   'backend.openrouter.pin_story_owner', 'backend.openrouter_wardrobe.pin_wardrobe_settings',
                   'uuid.uuid4']
        if replay:
            targets += ['backend.batch_preparation.read_saved_batch_input', 'backend.production.production_catalog',
                        'backend.comfyui_workflows.workflow_snapshot']
        with ExitStack() as stack:
            for target in targets:
                stack.enter_context(patch(target, side_effect=AssertionError('Forbidden admission effect: ' + target)))
            yield

    def no_units(self, db):
        for table in ('batch_unit_input_pins', 'render_jobs', 'render_submission_attempts', 'portrait_candidates',
                      'portrait_submissions', 'anchor_reference_transfers'):
            self.assertEqual(db.execute(f'SELECT COUNT(*) FROM {table}').fetchone(), (0,))

    async def test_full_membership_new_consumer_atomic_start_and_offline_duplicate_reopen(self):
        async with self.source(('comedian', 'fox')) as (runtime, ref, plan):
            db = runtime.db
            before = retained_inventory(db, ref.execution_id)
            async with runtime.saver.conn.execute('SELECT COUNT(*) FROM checkpoints') as cursor:
                checkpoints = await cursor.fetchone()
            with self.forbidden_effects():
                receipt = await self.start(runtime, ref)
            group = self.store.read_image_group(db, receipt.execution_id)
            self.assertNotEqual(receipt.execution_id, ref.execution_id)
            self.assertEqual(group.receipt, receipt)
            self.assertEqual(group.batch.prepared_input.ordered_units, plan.batch_prompt)
            self.assertEqual(len(plan.batch_prompt), 5)
            self.assertEqual(group.batch.prepared_input.source_plan_ref, ref)
            self.assertEqual(group.batch.prepared_input.activation_id, receipt.activation_id)
            self.assertFalse(group.batch.prepared_input.profile_snapshot['can_run'])
            self.assertEqual(group.wait_token, dict(wait_id=receipt.wait_id, stage_id='anchor-batch',
                activation_id=receipt.activation_id, request_digest=receipt.request_digest))
            self.assertEqual((group.checkpoint_id, group.task_id, group.interrupt_id), (None, None, None))
            self.assertEqual(db.execute('SELECT execution_id FROM batch_input_pins').fetchone(), (ref.execution_id,))
            self.assertEqual(db.execute('SELECT input_message,shot_ids,owner_config,graph_id,graph_version,graph_digest '
                'FROM executions WHERE execution_id=?', (receipt.execution_id,)).fetchone(),
                (self.store.IMAGE_INPUT_MARKER, '[]', None, self.store.GRAPH_ID,
                 self.store.GRAPH_VERSION, self.store.GRAPH_DIGEST))
            self.assertEqual(db.execute("SELECT work_id,source_id,payload_digest,status FROM execution_work "
                "WHERE execution_id=? AND kind='start'", (receipt.execution_id,)).fetchall(),
                [(receipt.work_id, receipt.execution_id, receipt.request_digest, 'pending')])
            self.assertEqual(retained_inventory(db, ref.execution_id), before)
            async with runtime.saver.conn.execute('SELECT COUNT(*) FROM checkpoints') as cursor:
                self.assertEqual(await cursor.fetchone(), checkpoints)
            self.no_units(db)
        with database.open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                with self.forbidden_effects(replay=True):
                    changes = db.total_changes
                    self.assertEqual(await self.store.start_image_execution(db, saver, self.project, 'images',
                                     **self.arguments(ref)), receipt)
                    self.assertEqual(self.store.read_image_group(db, receipt.execution_id), group)
                    self.assertEqual(db.total_changes, changes)
                    self.assertEqual(retained_inventory(db, ref.execution_id), before)
                    self.no_units(db)

    async def test_exact_submitted_pins_and_project_wide_route_namespace_conflict(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            cases = [dict(source_plan_ref=ref.model_copy(update={'digest': 'sha256:' + '0' * 64})),
                     dict(source_plan_ref=ref.model_copy(update={'execution_id': str(uuid4())})),
                     dict(image_size={'width': 512, 'height': 512}),
                     dict(image_profile={**self.profile, 'version': 'other'}),
                     dict(connection={**CONNECTION, 'endpoint_digest': 'sha256:' + '0' * 64}),
                     dict(connection={**CONNECTION, 'connection': 'server'})]
            with self.forbidden_effects(replay=True):
                for changes in cases:
                    with self.subTest(changes=changes), self.assertRaises(ValueError):
                        await self.start(runtime, ref, **changes)
                with self.assertRaises(ValueError):
                    await self.start(runtime, ref, key='source')
                with self.assertRaises(ValueError):
                    await runtime.start(self.project, 'images', 'not an image envelope', ['s1'])
                self.assertEqual(await self.start(runtime, ref), receipt)
            self.assertEqual(runtime.db.execute('SELECT COUNT(*) FROM image_groups').fetchone(), (1,))
            self.no_units(runtime.db)

    async def test_invalid_unapproved_crossproject_and_cancelled_sources_never_reserve(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            for sql, restore in (
                ("UPDATE execution_outcomes SET outcome='failed'", "UPDATE execution_outcomes SET outcome='completed'"),
                ("UPDATE review_requests SET action='revise'", "UPDATE review_requests SET action='approve'"),
                ("UPDATE execution_work SET status='pending' WHERE kind='resume'", "UPDATE execution_work SET status='completed' WHERE kind='resume'")):
                db.execute(sql)
                with self.assertRaises(ValueError):
                    await self.start(runtime, ref)
                db.execute(restore)
                self.assertFalse(db.in_transaction)
            for changes in (dict(project=str(uuid4())), dict(source_plan_ref=ref.model_copy(update={'schema_version': '1'}))):
                with self.assertRaises(ValueError):
                    await self.start(runtime, ref, **changes)
            source_work = db.execute("SELECT work_id FROM execution_work WHERE kind='start'").fetchone()[0]
            db.execute("INSERT INTO execution_controls VALUES (?,'cancel-source','cancel',?,NULL)",
                       (ref.execution_id, source_work))
            with self.assertRaises(ValueError):
                await self.start(runtime, ref)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM batch_input_pins').fetchone(), (0,))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM image_groups').fetchone(), (0,))
            self.no_units(db)

    async def test_reserved_pin_locks_client_key_even_to_different_source_and_settings(self):
        async with self.source() as (runtime, ref, _):
            with patch.object(batch_store, '_publish', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    await self.start(runtime, ref)
            db = runtime.db
            self.assertEqual(db.execute('SELECT COUNT(*) FROM executions').fetchone(), (1,))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM image_groups').fetchone(), (0,))
            original = db.execute('SELECT * FROM batch_input_pins').fetchall()
            conflicts: tuple[dict[str, Any], ...] = (
                dict(source_plan_ref=ref.model_copy(update={'execution_id': str(uuid4())})),
                dict(image_size={'width': 512, 'height': 512}))
            with self.forbidden_effects(replay=True):
                for changes in conflicts:
                    with self.assertRaises(ValueError):
                        await self.start(runtime, ref, **changes)
                self.assertEqual(db.execute('SELECT * FROM batch_input_pins').fetchall(), original)
                receipt = await self.start(runtime, ref)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM batch_input_pins').fetchone(), (1,))
            self.assertEqual(self.store.read_image_group(db, receipt.execution_id).batch.input_digest, original[0][5])

    async def test_acceptance_failure_is_atomic_and_published_pin_replays_without_authority(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            db.set_authorizer(lambda action, *args: sqlite3.SQLITE_DENY
                if action == sqlite3.SQLITE_INSERT and args[0] == 'image_groups' else sqlite3.SQLITE_OK)
            try:
                with self.assertRaises(sqlite3.DatabaseError):
                    await self.start(runtime, ref)
            finally:
                db.set_authorizer(None)
            self.assertFalse(db.in_transaction)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM executions').fetchone(), (1,))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM execution_work WHERE kind='start'").fetchone(), (1,))
            self.assertEqual(db.execute('SELECT publication_state FROM batch_input_pins').fetchone(), ('published',))
            with self.forbidden_effects(replay=True):
                receipt = await self.start(runtime, ref)
            self.assertEqual(self.store.read_image_group(db, receipt.execution_id).receipt, receipt)

    async def test_reserved_image_key_rejects_all_story_routes_before_owner_or_library_effects(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            selected = [{'subject_id': 'character-' + 'a' * 32, 'revision': 1, 'digest': 'sha256:' + 'a' * 64}]
            for route in ('fixture', 'live', 'wardrobe'):
                key = 'reserved-' + route
                with patch.object(batch_store, '_publish', side_effect=OSError('disk full')):
                    with self.assertRaises(OSError):
                        await self.start(runtime, ref, key=key)
                before = db.execute('SELECT * FROM batch_input_pins ORDER BY batch_id').fetchall()
                with self.subTest(route=route), ExitStack() as stack:
                    effects = [stack.enter_context(patch(target, side_effect=AssertionError('Competing start effect')))
                        for target in ('backend.story_start.CharacterRepository', 'backend.openrouter.pin_story_owner',
                                       'backend.openrouter_wardrobe.pin_wardrobe_settings', 'httpx.AsyncClient')]
                    with self.assertRaisesRegex(ValueError, 'client key conflicts'):
                        if route == 'fixture':
                            await runtime.start(self.project, key, 'competing Story', ['s1'])
                        else:
                            start = runtime.start_live if route == 'live' else runtime.start_wardrobe
                            await start(self.project, key, ['s1'], self.brief, character_refs=selected)
                    for effect in effects:
                        effect.assert_not_called()
                    self.assertIsNone(db.execute('SELECT 1 FROM executions WHERE project_id=? AND client_key=?',
                                                (self.project, key)).fetchone())
                    self.assertEqual(db.execute('SELECT * FROM batch_input_pins ORDER BY batch_id').fetchall(), before)
                    with self.forbidden_effects(replay=True):
                        receipt = await self.start(runtime, ref, key=key)
                        self.assertEqual(await self.start(runtime, ref, key=key), receipt)
            self.no_units(db)
            # The image reservation guard must not narrow the fixture Story key contract.
            long_key = 'l' * 256
            story = await runtime.start(self.project, long_key, 'long fixture key', ['s1'])
            self.assertEqual(await runtime.start(self.project, long_key, 'long fixture key', ['s1']), story)

    async def test_story_final_acceptance_rechecks_image_reservation_after_initial_admission(self):
        async with self.source() as (runtime, ref, _):
            db = runtime.db
            original_digest = story_start._payload_digest
            for route in ('fixture', 'live', 'wardrobe'):
                key = 'late-reserved-' + route
                injected = False
                def reserve_before_acceptance(*args):
                    nonlocal injected
                    if not injected:
                        injected = True
                        activation = self.store._identities(self.project, key)[0]
                        with patch.object(batch_store, '_publish', side_effect=OSError('disk full')):
                            with self.assertRaises(OSError):
                                batch_store.pin_saved_batch_input(db, ref.execution_id,
                                    **self.arguments(ref), activation_id=activation)
                    return original_digest(*args)
                with self.subTest(route=route), patch.object(story_start, '_payload_digest', side_effect=reserve_before_acceptance):
                    with self.assertRaisesRegex(ValueError, 'client key conflicts'):
                        if route == 'fixture':
                            await runtime.start(self.project, key, 'competing Story', ['s1'])
                        else:
                            start = runtime.start_live if route == 'live' else runtime.start_wardrobe
                            await start(self.project, key, ['s1'], self.brief)
                    self.assertTrue(injected)
                    self.assertFalse(db.in_transaction)
                    self.assertIsNone(db.execute('SELECT 1 FROM executions WHERE project_id=? AND client_key=?',
                                                (self.project, key)).fetchone())
                    with self.forbidden_effects(replay=True):
                        receipt = await self.start(runtime, ref, key=key)
                        self.assertEqual(await self.start(runtime, ref, key=key), receipt)
            self.no_units(db)

    async def test_binding_exact_wait_occ_nullity_and_cancellation_guard(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            db = runtime.db
            args = dict(expected_request_digest=receipt.request_digest, checkpoint_id='cp', task_id='task', interrupt_id='interrupt')
            with self.assertRaises(ValueError):
                self.store.bind_image_wait(db, receipt.execution_id, receipt.wait_id,
                                           **{**args, 'expected_request_digest': 'sha256:' + '0' * 64})
            self.store.bind_image_wait(db, receipt.execution_id, receipt.wait_id, **args)
            changes = db.total_changes
            self.store.bind_image_wait(db, receipt.execution_id, receipt.wait_id, **args)
            self.assertEqual(db.total_changes, changes)
            for field in ('checkpoint_id', 'task_id', 'interrupt_id'):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    self.store.bind_image_wait(db, receipt.execution_id, receipt.wait_id, **{**args, field: 'other'})
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(f'UPDATE image_groups SET {field}=NULL')
            db.execute("UPDATE image_groups SET checkpoint_id=NULL,task_id=NULL,interrupt_id=NULL")
            db.execute("INSERT INTO execution_controls VALUES (?,'cancel-image','cancel',?,NULL)",
                       (receipt.execution_id, receipt.work_id))
            with self.assertRaises(ValueError):
                self.store.bind_image_wait(db, receipt.execution_id, receipt.wait_id, **args)
            self.assertIsNone(self.store.read_image_group(db, receipt.execution_id).checkpoint_id)
            with self.forbidden_effects(replay=True):
                self.assertEqual(await self.start(runtime, ref), receipt)

    async def test_corrupt_envelope_group_or_published_bytes_never_heal(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            db = runtime.db
            group = self.store.read_image_group(db, receipt.execution_id)
            for table, column, value in (('executions', 'input_message', 'Story input'),
                ('executions', 'shot_ids', '["s1"]'), ('executions', 'owner_config', '{}'),
                ('executions', 'graph_digest', 'sha256:' + '0' * 64),
                ('image_groups', 'request_digest', 'sha256:' + '0' * 64),
                ('image_groups', 'wait_id', 'sha256:' + '0' * 64)):
                old = db.execute(f'SELECT {column} FROM {table} WHERE execution_id=?', (receipt.execution_id,)).fetchone()[0]
                db.execute(f'UPDATE {table} SET {column}=? WHERE execution_id=?', (value, receipt.execution_id))
                with self.subTest(table=table, column=column), self.forbidden_effects(replay=True):
                    with self.assertRaises(ValueError):
                        self.store.read_image_group(db, receipt.execution_id)
                    with self.assertRaises(ValueError):
                        await self.start(runtime, ref)
                db.execute(f'UPDATE {table} SET {column}=? WHERE execution_id=?', (old, receipt.execution_id))
            path = self.root / group.batch.uri.removeprefix('kinodel://')
            path.unlink()
            with self.forbidden_effects(replay=True), self.assertRaises(FileNotFoundError):
                await self.start(runtime, ref)
            self.assertFalse(path.exists())

    async def test_real_process_deaths_pin_publication_and_acceptance_commit_boundaries(self):
        async with self.source() as (runtime, ref, _):
            before = retained_inventory(runtime.db, ref.execution_id)
        child = '''
import asyncio, json, os, sqlite3, sys
from pathlib import Path
from backend import batch_store, database, image_group_store
from backend.saver import open_saver
root, phase = Path(sys.argv[1]), sys.argv[2]
connect = sqlite3.connect
class Crash(sqlite3.Connection):
    accepted = False
    def execute(self, sql, *args, **kwargs):
        result = super().execute(sql, *args, **kwargs)
        if sql.startswith('INSERT INTO image_groups'):
            self.accepted = True
            if phase == 'before-accept': os._exit(23)
        if sql == 'COMMIT' and self.accepted and phase == 'after-accept': os._exit(23)
        return result
sqlite3.connect = lambda *a, **kw: connect(*a, **kw, factory=Crash)
publish = batch_store._publish
def die(path, body):
    if phase == 'publish': publish(path, body)
    os._exit(23)
if phase in ('reserve', 'publish'): batch_store._publish = die
async def main():
    with database.open_database(root) as db:
        async with open_saver(root, db) as saver:
            await image_group_store.start_image_execution(db, saver, sys.argv[3], phase, **json.loads(sys.argv[4]))
asyncio.run(main())
'''
        for phase in ('reserve', 'publish', 'before-accept', 'after-accept'):
            with self.subTest(phase=phase):
                result = subprocess.run([sys.executable, '-B', '-c', child, str(self.root), phase,
                                         self.project, json.dumps(self.arguments(ref))],
                                        capture_output=True, text=True, timeout=40)
                self.assertEqual(result.returncode, 23, result.stderr)
                with database.open_database(self.root) as db:
                    accepted = db.execute('SELECT execution_id FROM executions WHERE client_key=?', (phase,)).fetchone()
                    self.assertEqual(accepted is not None, phase == 'after-accept')
                    async with open_saver(self.root, db) as saver:
                        with self.forbidden_effects(replay=True):
                            receipt = await self.store.start_image_execution(db, saver, self.project, phase,
                                                                          **self.arguments(ref))
                            self.assertEqual(await self.store.start_image_execution(db, saver, self.project, phase,
                                             **self.arguments(ref)), receipt)
                        self.assertEqual(self.store.read_image_group(db, receipt.execution_id).receipt, receipt)
                        if accepted:
                            self.assertEqual(receipt.execution_id, accepted[0])
                        self.assertEqual(retained_inventory(db, ref.execution_id), before)
                        self.no_units(db)


class ImageGroupMigrationTests(unittest.TestCase):
    def setUp(self):
        self.old = database_tests.DatabaseTests()
        self.old.setUp()
        self.addCleanup(self.old.doCleanups)
        self.old.populated_v18()
        self.root = self.old.root
        self.path = self.old.path
        with closing(sqlite3.connect(self.path, isolation_level=None)) as db:
            db.executescript(database.ANCHOR_REFERENCE_TRANSFER_SCHEMA + 'PRAGMA user_version=19;')
            db.execute("INSERT INTO anchor_reference_transfers VALUES ('attempt','job','u-digest','intent-digest',"
                       "'record-digest','frozen DB19 receipt 🦊',2,'blocked')")
            self.schema = database._schema(db)
            self.rows = {r[1]: db.execute(f'SELECT rowid,* FROM {r[1]} ORDER BY rowid').fetchall()
                         for r in self.schema if r[0] == 'table'}

    def test_actual_populated_db19_adds_only_group_table_preserving_old_rows_rowids_schema(self):
        self.assertEqual(database.SCHEMA_VERSION, 20, 'Image group requires additive DB20')
        for _ in range(2):
            with database.open_database(self.root) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone(), (20,))
                self.assertEqual([r for r in database._schema(db) if r[1] != 'image_groups'], self.schema)
                self.assertEqual({t: db.execute(f'SELECT rowid,* FROM {t} ORDER BY rowid').fetchall()
                                  for t in self.rows}, self.rows)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM image_groups').fetchone(), (0,))
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_db20_ddl_or_validation_fault_rolls_back_complete_db19(self):
        self.assertTrue(hasattr(database, 'IMAGE_GROUP_SCHEMA'), 'Image group migration is missing')
        validate = database._validate
        def fail(db):
            validate(db)
            if db.execute('PRAGMA user_version').fetchone() == (20,):
                raise ValueError('injected image group validation failure')
        for fault in (patch.object(database, 'IMAGE_GROUP_SCHEMA', database.IMAGE_GROUP_SCHEMA + 'SELECT * FROM missing;'),
                      patch.object(database, '_validate', side_effect=fail)):
            with fault, self.assertRaises((ValueError, sqlite3.OperationalError)):
                with database.open_database(self.root):
                    self.fail('Partial DB20 accepted')
            with closing(sqlite3.connect(self.path)) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone(), (19,))
                self.assertEqual(database._schema(db), self.schema)
                self.assertEqual({t: db.execute(f'SELECT rowid,* FROM {t} ORDER BY rowid').fetchall()
                                  for t in self.rows}, self.rows)


if __name__ == '__main__':
    unittest.main()
