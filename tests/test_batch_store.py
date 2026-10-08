"""Private preparation pins: exact replay, crash recovery and no media activation."""

from contextlib import asynccontextmanager, contextmanager, ExitStack
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Any
import unittest
from unittest.mock import patch

from backend import batch_generation as generation, database, wardrobe_store
from backend.comfyui import NativeImagePreparationContext
from backend.domain import MAX_JSON_BYTES, canonical_json, sha256_digest
from backend.production import production_catalog
from backend.story_control import open_story_runtime
from backend.api import fixture_story
from tests import test_story_wardrobe_api as fixtures
from tests.test_batch_preparation import ACTIVATION, CONNECTION
from tests.test_comfyui_workflows import ROOT, TXT, installed_schemas
from tests.test_story_cast import draft
from tests.test_story_wardrobe_runtime import retained_inventory
from tests.test_wardrobe_compact_v2 import compact_draft


class BatchStoreTests(fixtures.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('backend.batch_store'), 'Private batch pin storage is missing')
        from backend import batch_store
        self.store = batch_store
        self.profile = production_catalog()['image_only']['profiles'][0]['pin']

    @asynccontextmanager
    async def committed(self, keys=None):
        story = draft(cast=[{'subject_id': 'comedian', 'description': 'Traveler'}], subject_ids=['comedian'])
        output = {'status': 'ready', 'plan': compact_draft(('comedian',)), 'explanation': None}
        if keys is not None:
            units = output['plan']['batch_prompt']
            replacements = dict(zip((u['unit_key'] for u in units), keys, strict=True))
            for unit in units:
                unit['unit_key'] = replacements[unit['unit_key']]
                for ref in unit['references']:
                    ref['source']['unit_key'] = replacements[ref['source']['unit_key']]
        with self.transport(output), patch.object(fixtures, 'draft', return_value=story):
            async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
                receipt = await runtime.start_wardrobe(self.project, 'batch-store', ['s1'], self.brief)
                await runtime.run()
                self.approve(runtime, receipt.execution_id)
                await runtime.run()
                ref, _ = wardrobe_store.read_wardrobe_plan(runtime.db, receipt.execution_id)
                yield runtime.db, ref

    def pin(self, db, ref, **changes):
        args: dict[str, Any] = dict(source_plan_ref=ref, image_size={'width': 768, 'height': 768},
                    image_profile=self.profile, connection=CONNECTION, activation_id=ACTIVATION)
        args.update(changes)
        return self.store.pin_saved_batch_input(db, ref.execution_id, **args)

    def context(self, batch, key):
        _, _, binding = generation._unit(batch.prepared_input, key)
        name = 'txt2img krea2 api v1_local.json' if binding.workflow_id == TXT else 'qwen img2img api v1.1 3img.json'
        return NativeImagePreparationContext(binding.workflow_id, binding.registry_digest,
            batch.prepared_input.connection.connection, batch.prepared_input.connection.endpoint_digest,
            (ROOT / name).read_bytes(), installed_schemas(), {})

    def parents(self, batch, key):
        _, unit, _ = generation._unit(batch.prepared_input, key)
        return [{'unit_key': ref.source.unit_key, 'source_id': 'candidate-' + ref.source.unit_key,
                 'digest': 'sha256:' + str(i + 1) * 64, 'input_name': f'parents/input-{i}.png'}
                for i, ref in enumerate(unit.references)]

    def prepare(self, db, batch, key, **changes):
        args: dict[str, Any] = dict(parent_bindings=self.parents(batch, key), context=self.context(batch, key), seed=42)
        args.update(changes)
        return self.store.prepare_saved_batch_unit(db, batch.batch_id, key, **args)

    def path(self, record):
        return self.root / record.uri.removeprefix('kinodel://')

    def staging_path(self, destination):
        return destination.with_name('.batch-' + sha256_digest(destination.name.encode('ascii'))[7:] + '.tmp')

    @contextmanager
    def offline(self):
        with ExitStack() as stack:
            for target in ('backend.batch_preparation.read_saved_batch_input',
                           'backend.production.production_catalog', 'backend.comfyui_workflows.workflow_snapshot',
                           'backend.batch_generation.prepare_batch_unit', 'backend.comfyui_workflows.secrets.randbelow',
                           'httpx.Client.send', 'httpx.AsyncClient'):
                stack.enter_context(patch(target, side_effect=AssertionError('Offline replay: ' + target)))
            yield

    async def test_exact_private_handoff_and_unit_commit_offline_reopen_without_text_mutation(self):
        async with self.committed() as (db, ref):
            before = retained_inventory(db, ref.execution_id)
            batch = self.pin(db, ref)
            self.assertEqual(batch.input_digest, generation.batch_input_digest(batch.prepared_input))
            self.assertEqual(self.path(batch).read_bytes(), canonical_json(batch.prepared_input))
            self.assertEqual(db.execute('SELECT publication_state FROM batch_input_pins').fetchone(), ('published',))
            key = batch.prepared_input.ordered_units[0].unit_key
            unit = self.prepare(db, batch, key)
            self.assertEqual(self.path(unit).read_bytes(), canonical_json(unit.prepared_input))
            self.assertEqual(unit.input_digest, sha256_digest(canonical_json(unit.prepared_input)))
            self.assertEqual(retained_inventory(db, ref.execution_id), before)
        with database.open_database(self.root) as db, self.offline():
            changes = db.total_changes
            self.assertEqual(self.store.read_batch_input(db, batch.batch_id), batch)
            self.assertEqual(self.pin(db, ref), batch)
            self.assertEqual(self.store.read_prepared_batch_unit(db, batch.batch_id, key, parent_bindings=[]), unit)
            self.assertEqual(self.store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=[]), unit)
            self.assertEqual(db.total_changes, changes)
            self.assertEqual(retained_inventory(db, ref.execution_id), before)

    async def test_handoff_request_selector_conflicts_do_not_refreeze(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            cases = [dict(source_plan_ref=ref.model_copy(update={'digest': 'sha256:' + '0' * 64})),
                     dict(image_size={'width': 512, 'height': 512}),
                     dict(image_profile={**self.profile, 'version': 'other'}),
                     dict(connection={**CONNECTION, 'endpoint_digest': 'sha256:' + '0' * 64}),
                     dict(connection={**CONNECTION, 'connection': 'server'})]
            with self.offline():
                for changes in cases:
                    with self.subTest(changes=changes), self.assertRaises(ValueError):
                        self.pin(db, ref, **changes)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM batch_input_pins').fetchone(), (1,))
            self.assertEqual(self.store.read_batch_input(db, batch.batch_id), batch)

    async def test_source_negatives_never_reserve(self):
        async with self.committed() as (db, ref):
            for sql, restore in (
                    ("UPDATE execution_outcomes SET outcome='failed'", "UPDATE execution_outcomes SET outcome='completed'"),
                    ("UPDATE execution_work SET status='pending' WHERE kind='resume'", "UPDATE execution_work SET status='completed' WHERE kind='resume'"),
                    ("UPDATE execution_bindings SET binding_revision=2 WHERE slot='story'", "UPDATE execution_bindings SET binding_revision=1 WHERE slot='story'")):
                db.execute(sql)
                with self.assertRaises(ValueError):
                    self.pin(db, ref)
                self.assertFalse(db.in_transaction)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM batch_input_pins').fetchone(), (0,))
                db.execute(restore)
            with self.assertRaises(ValueError):
                self.pin(db, ref, source_plan_ref=ref.model_copy(update={'schema_version': '1'}))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM batch_input_pins').fetchone(), (0,))

    async def test_publication_failure_keeps_private_body_and_recovers_without_source_lookup(self):
        async with self.committed() as (db, ref):
            with patch.object(self.store, '_publish', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    self.pin(db, ref)
            batch_id, body = db.execute('SELECT batch_id,body FROM batch_input_pins').fetchone()
            with self.assertRaises(LookupError):
                self.store.read_batch_input(db, batch_id)
            # Authority belongs to the first reservation, not recovery after terminal changes.
            db.execute("UPDATE execution_bindings SET binding_revision=2 WHERE slot='story'")
        with database.open_database(self.root) as db, self.offline():
            batch = self.pin(db, ref)
            self.assertEqual(canonical_json(batch.prepared_input), body.encode())
            self.assertEqual(self.store.read_batch_input(db, batch_id), batch)

    async def test_random_seed_survives_failed_publication_and_retry_rejects_explicit_change(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            key = batch.prepared_input.ordered_units[0].unit_key
            with patch.object(generation.registry.secrets, 'randbelow', return_value=123) as rng, \
                    patch.object(self.store, '_publish', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    self.prepare(db, batch, key, seed=None)
                self.assertEqual(rng.call_count, 1)
            body = db.execute('SELECT body FROM batch_unit_input_pins').fetchone()[0]
            with self.assertRaises(LookupError):
                self.store.read_prepared_batch_unit(db, batch.batch_id, key, parent_bindings=[])
            with self.offline():
                with self.assertRaises(ValueError):
                    self.store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=[], seed=124)
                unit = self.store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=[], seed=123)
            self.assertEqual(canonical_json(unit.prepared_input), body.encode())
            self.assertEqual(json.loads(unit.prepared_input.image_pin_json)['settings']['seed'], 123)

    async def test_child_order_context_and_seed_conflicts_before_reservation_or_rng(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            key = batch.prepared_input.ordered_units[-1].unit_key
            parents = self.parents(batch, key)
            context = self.context(batch, key)
            cases = [dict(parent_bindings=[]), dict(parent_bindings=parents[::-1]),
                     dict(context=None), dict(context=replace(context, workflow_id=TXT)),
                     dict(context=replace(context, connection='server')),
                     dict(context=replace(context, endpoint_digest='sha256:' + '0' * 64)),
                     dict(context=replace(context, registry_digest='sha256:' + '0' * 64)), dict(seed=True)]
            with patch.object(generation.registry.secrets, 'randbelow', side_effect=AssertionError('No RNG')):
                for changes in cases:
                    with self.subTest(changes=changes), self.assertRaises(ValueError):
                        self.prepare(db, batch, key, **changes)
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM batch_unit_input_pins').fetchone(), (0,))
            unit = self.prepare(db, batch, key)
            with self.offline():
                self.assertEqual(self.store.prepare_saved_batch_unit(db, batch.batch_id, key,
                    parent_bindings=parents, seed=42), unit)
                for changed in (parents[::-1], [{**parents[0], 'source_id': 'changed'}, parents[1]]):
                    with self.assertRaises(ValueError):
                        self.store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=changed)
                    with self.assertRaises(ValueError):
                        self.store.read_prepared_batch_unit(db, batch.batch_id, key, parent_bindings=changed)
                with self.assertRaises(ValueError):
                    self.store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=parents, seed=43)

    async def test_published_missing_tampered_oversized_and_hardlinked_files_never_heal(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            key = batch.prepared_input.ordered_units[0].unit_key
            unit = self.prepare(db, batch, key)
            for record, read, replay in (
                    (batch, lambda: self.store.read_batch_input(db, batch.batch_id), lambda: self.pin(db, ref)),
                    (unit, lambda: self.store.read_prepared_batch_unit(db, batch.batch_id, key, parent_bindings=[]),
                     lambda: self.store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=[]))):
                path = self.path(record)
                original = path.read_bytes()
                for content in (None, b'', original[:128], original + b' ', b'x' * (MAX_JSON_BYTES + 1)):
                    path.unlink(missing_ok=True)
                    if content is not None:
                        path.write_bytes(content)
                    with self.subTest(record=record.uri, size=None if content is None else len(content)), self.offline():
                        for call in (read, replay):
                            with self.assertRaises((ValueError, OSError)):
                                call()
                    self.assertEqual(path.read_bytes() if path.exists() else None, content)
                path.write_bytes(original)
                linked = path.with_suffix('.link')
                os.link(path, linked)
                with self.assertRaises(ValueError):
                    read()
                linked.unlink()
                self.assertEqual(read(), record)

    async def test_reserved_conflicting_existing_file_is_not_overwritten(self):
        async with self.committed() as (db, ref):
            with patch.object(self.store, '_publish', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    self.pin(db, ref)
            batch_id, uri = db.execute('SELECT batch_id,uri FROM batch_input_pins').fetchone()
            path = self.root / uri.removeprefix('kinodel://')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'foreign bytes')
            with self.assertRaises(ValueError):
                self.pin(db, ref)
            self.assertEqual(path.read_bytes(), b'foreign bytes')
            with self.assertRaises(LookupError):
                self.store.read_batch_input(db, batch_id)

    async def test_sql_identity_and_body_corruption_fail_closed(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            for column, value in (('activation_id', 'sha256:' + '0' * 64), ('uri', 'kinodel://projects/../unsafe'),
                                  ('input_digest', 'sha256:' + '0' * 64), ('body', '{}')):
                old = db.execute(f'SELECT {column} FROM batch_input_pins').fetchone()[0]
                db.execute(f'UPDATE batch_input_pins SET {column}=?', (value,))
                with self.subTest(column=column), self.assertRaises(ValueError):
                    self.store.read_batch_input(db, batch.batch_id)
                db.execute(f'UPDATE batch_input_pins SET {column}=?', (old,))
            key = batch.prepared_input.ordered_units[0].unit_key
            self.prepare(db, batch, key)
            db.execute("UPDATE batch_unit_input_pins SET unit_key='unknown'")
            with self.assertRaises(ValueError):
                self.store.read_prepared_batch_unit(db, batch.batch_id, 'unknown', parent_bindings=[])

    async def test_finalization_transaction_failure_leaves_files_private_and_recoverable(self):
        async with self.committed() as (db, ref):
            db.set_authorizer(lambda action, *args: sqlite3.SQLITE_DENY
                              if action == sqlite3.SQLITE_UPDATE and args[0] == 'batch_input_pins'
                              else sqlite3.SQLITE_OK)
            try:
                with self.assertRaises(sqlite3.DatabaseError):
                    self.pin(db, ref)
            finally:
                db.set_authorizer(None)
            self.assertFalse(db.in_transaction)
            batch_id, uri = db.execute('SELECT batch_id,uri FROM batch_input_pins').fetchone()
            path = self.root / uri.removeprefix('kinodel://')
            self.assertTrue(path.is_file())
            with self.assertRaises(LookupError):
                self.store.read_batch_input(db, batch_id)
            with self.offline():
                batch = self.pin(db, ref)
            key = batch.prepared_input.ordered_units[0].unit_key
            db.set_authorizer(lambda action, *args: sqlite3.SQLITE_DENY
                              if action == sqlite3.SQLITE_UPDATE and args[0] == 'batch_unit_input_pins'
                              else sqlite3.SQLITE_OK)
            try:
                with self.assertRaises(sqlite3.DatabaseError):
                    self.prepare(db, batch, key)
            finally:
                db.set_authorizer(None)
            body, uri = db.execute('SELECT body,uri FROM batch_unit_input_pins').fetchone()
            self.assertEqual((self.root / uri.removeprefix('kinodel://')).read_bytes(), body.encode())
            with self.assertRaises(LookupError):
                self.store.read_prepared_batch_unit(db, batch_id, key, parent_bindings=[])
            with self.offline():
                unit = self.store.prepare_saved_batch_unit(db, batch_id, key, parent_bindings=[])
            self.assertEqual(canonical_json(unit.prepared_input), body.encode())

    async def test_only_committed_canonical_metadata_is_readable(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            key = batch.prepared_input.ordered_units[0].unit_key
            self.prepare(db, batch, key)
            db.execute('BEGIN IMMEDIATE')
            try:
                for call in (lambda: self.store.read_batch_input(db, batch.batch_id),
                             lambda: self.store.read_prepared_batch_unit(db, batch.batch_id, key, parent_bindings=[]),
                             lambda: self.pin(db, ref),
                             lambda: self.store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=[])):
                    with self.assertRaises(ValueError):
                        call()
            finally:
                db.execute('ROLLBACK')

    async def test_unit_keys_are_strict_selectors_never_filenames(self):
        async with self.committed(keys=('1', '../../location', 'nested/sheet')) as (db, ref):
            batch = self.pin(db, ref)
            for unit in batch.prepared_input.ordered_units:
                record = self.prepare(db, batch, unit.unit_key)
                self.assertRegex(self.path(record).name, r'^[a-f0-9]{64}\.[a-f0-9]{64}\.json$')
            invalid_keys: list[Any] = [1, True]
            for invalid in invalid_keys:
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    self.store.read_prepared_batch_unit(db, batch.batch_id, invalid, parent_bindings=[])
                with self.assertRaises(ValueError):
                    self.store.prepare_saved_batch_unit(db, batch.batch_id, invalid, parent_bindings=[])

    async def test_redirected_parent_directory_refused_on_reads_and_retries(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            key = batch.prepared_input.ordered_units[0].unit_key
            self.prepare(db, batch, key)
            inputs = self.path(batch).parent
            for directory in (inputs, inputs.parent, inputs.parent.parent):
                moved = directory.with_name('moved-' + directory.name)
                directory.rename(moved)
                try:
                    directory.symlink_to(moved, target_is_directory=True)
                except OSError as error:
                    if os.name == 'nt' and error.winerror == 1314:
                        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(directory), str(moved)],
                                                capture_output=True, text=True, timeout=10)
                        if result.returncode:
                            moved.rename(directory)
                            self.fail('Could not create test junction: ' + result.stderr)
                    else:
                        moved.rename(directory)
                        raise
                try:
                    with self.subTest(directory=directory), self.offline():
                        for call in (lambda: self.store.read_batch_input(db, batch.batch_id), lambda: self.pin(db, ref),
                                     lambda: self.store.read_prepared_batch_unit(db, batch.batch_id, key, parent_bindings=[]),
                                     lambda: self.store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=[])):
                            with self.assertRaises(ValueError):
                                call()
                finally:
                    if directory.is_symlink():
                        directory.unlink()
                    else:
                        directory.rmdir()  # Windows junction: remove the redirect, not its contents.
                    moved.rename(directory)

    async def test_real_process_death_inside_link_publication_recovers_exact_reserved_pins(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            before = retained_inventory(db, ref.execution_id)
        child = '''
import json, os, sys
from pathlib import Path
from backend import batch_store, batch_generation as generation, database
from backend.comfyui import NativeImagePreparationContext
from tests.test_comfyui_workflows import ROOT, installed_schemas
generation.registry.secrets.randbelow = lambda ceiling: 123
with database.open_database(Path(sys.argv[1])) as db:
    link = os.link
    def die(source, destination, *args, **kwargs):
        if sys.argv[2] != 'unit-staged':
            link(source, destination, *args, **kwargs)
        print(source, flush=True)
        os._exit(23)
    os.link = die
    if sys.argv[2] == 'batch':
        args = json.loads(sys.argv[3])
        batch_store.pin_saved_batch_input(db, args['source_plan_ref']['execution_id'], **args)
    else:
        batch = batch_store.read_batch_input(db, sys.argv[3])
        key = sys.argv[4]
        _, _, binding = generation._unit(batch.prepared_input, key)
        context = NativeImagePreparationContext(binding.workflow_id, binding.registry_digest,
            batch.prepared_input.connection.connection, batch.prepared_input.connection.endpoint_digest,
            (ROOT / 'txt2img krea2 api v1_local.json').read_bytes(), installed_schemas(), {})
        batch_store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=[], context=context)
'''
        activation = 'sha256:' + '9' * 64
        args = dict(source_plan_ref=ref.model_dump(mode='json'), image_size={'width': 768, 'height': 768},
                    image_profile=self.profile, connection=CONNECTION, activation_id=activation)
        for kind, selector in (('batch', json.dumps(args)), ('unit-staged', batch.batch_id), ('unit', batch.batch_id)):
            with self.subTest(kind=kind):
                key = batch.prepared_input.ordered_units[0 if kind == 'unit-staged' else 1].unit_key
                result = subprocess.run([sys.executable, '-B', '-c', child, str(self.root), kind, selector, key],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 23, result.stderr)
                staging = Path(result.stdout.strip())
                with database.open_database(self.root) as db:
                    if kind == 'batch':
                        batch_id, body, uri, state = db.execute('SELECT batch_id,body,uri,publication_state '
                            'FROM batch_input_pins WHERE activation_id=?', (activation,)).fetchone()
                        read = lambda: self.store.read_batch_input(db, batch_id)
                        retry = lambda: self.pin(db, ref, activation_id=activation)
                    else:
                        body, uri, state = db.execute('SELECT body,uri,publication_state FROM batch_unit_input_pins '
                            'WHERE batch_id=? AND unit_key=?', (batch.batch_id, key)).fetchone()
                        read = lambda: self.store.read_prepared_batch_unit(db, batch.batch_id, key, parent_bindings=[])
                        retry = lambda: self.store.prepare_saved_batch_unit(db, batch.batch_id, key,
                            parent_bindings=[], context=None, seed=123)
                    destination = self.root / uri.removeprefix('kinodel://')
                    self.assertEqual(state, 'reserved')
                    if kind == 'unit-staged':
                        self.assertFalse(destination.exists())
                        self.assertEqual(staging.stat().st_nlink, 1)
                    else:
                        self.assertEqual(destination.stat().st_nlink, 2)
                        self.assertTrue(os.path.samestat(staging.lstat(), destination.lstat()))
                        self.assertEqual(destination.read_bytes(), body.encode())
                    self.assertEqual(staging.read_bytes(), body.encode())
                    with self.assertRaises(LookupError):
                        read()
                    changes = db.total_changes
                    with self.offline():
                        record = retry()
                        self.assertEqual(retry(), record)
                        self.assertEqual(read(), record)
                    self.assertEqual(db.total_changes, changes + 1)
                    self.assertEqual(staging, self.staging_path(destination))
                    self.assertFalse(staging.exists())
                    self.assertEqual(destination.stat().st_nlink, 1)
                    self.assertEqual(canonical_json(record.prepared_input), body.encode())
                    if kind != 'batch':
                        self.assertEqual(json.loads(record.prepared_input.image_pin_json)['settings']['seed'], 123)
                    self.assertEqual(retained_inventory(db, ref.execution_id), before)

    async def test_real_process_death_during_staging_write_completes_only_pinned_prefix_offline(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            before = retained_inventory(db, ref.execution_id)
        child = '''
import os, sys
from pathlib import Path
from backend import batch_store, batch_generation as generation, database
from backend.comfyui import NativeImagePreparationContext
from tests.test_comfyui_workflows import ROOT, installed_schemas
generation.registry.secrets.randbelow = lambda ceiling: 123
with database.open_database(Path(sys.argv[1])) as db:
    batch = batch_store.read_batch_input(db, sys.argv[2])
    key = sys.argv[4]
    _, _, binding = generation._unit(batch.prepared_input, key)
    context = NativeImagePreparationContext(binding.workflow_id, binding.registry_digest,
        batch.prepared_input.connection.connection, batch.prepared_input.connection.endpoint_digest,
        (ROOT / 'txt2img krea2 api v1_local.json').read_bytes(), installed_schemas(), {})
    original_open = Path.open
    class Writer:
        def __init__(self, target): self.target = target
        def __enter__(self): return self
        def __exit__(self, *args): self.target.close()
        def fileno(self): return self.target.fileno()
        def write(self, body):
            self.target.write(body[:128])
            self.target.flush()
            os._exit(23)
    def interrupted_open(path, mode='r', *args, **kwargs):
        target = original_open(path, mode, *args, **kwargs)
        if mode == 'xb' and path.name.startswith('.batch-'):
            if sys.argv[3] == 'empty':
                os._exit(23)
            return Writer(target)
        return target
    Path.open = interrupted_open
    batch_store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=[], context=context)
'''
        for stage, unit in zip(('empty', 'prefix'), batch.prepared_input.ordered_units[:2], strict=True):
            with self.subTest(stage=stage):
                key = unit.unit_key
                result = subprocess.run([sys.executable, '-B', '-c', child, str(self.root), batch.batch_id, stage, key],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 23, result.stderr)
                with database.open_database(self.root) as db:
                    body, uri, state = db.execute('SELECT body,uri,publication_state FROM batch_unit_input_pins '
                        'WHERE batch_id=? AND unit_key=?', (batch.batch_id, key)).fetchone()
                    destination = self.root / uri.removeprefix('kinodel://')
                    staging = self.staging_path(destination)
                    inode = staging.lstat()
                    self.assertEqual(state, 'reserved')
                    self.assertEqual(inode.st_nlink, 1)
                    self.assertFalse(destination.exists())
                    self.assertEqual(staging.read_bytes(), b'' if stage == 'empty' else body.encode()[:128])
                    self.assertEqual(json.loads(json.loads(body)['image_pin_json'])['settings']['seed'], 123)
                    with self.assertRaises(LookupError):
                        self.store.read_prepared_batch_unit(db, batch.batch_id, key, parent_bindings=[])
                    retry = lambda: self.store.prepare_saved_batch_unit(db, batch.batch_id, key,
                        parent_bindings=[], context=None, seed=123)
                    with self.offline():
                        # Even completed/published bytes remain hidden until SQL finalization.
                        db.set_authorizer(lambda action, *args: sqlite3.SQLITE_DENY
                            if action == sqlite3.SQLITE_UPDATE and args[0] == 'batch_unit_input_pins' else sqlite3.SQLITE_OK)
                        try:
                            with self.assertRaises(sqlite3.DatabaseError):
                                retry()
                        finally:
                            db.set_authorizer(None)
                        self.assertFalse(db.in_transaction)
                        self.assertFalse(staging.exists())
                        self.assertTrue(os.path.samestat(inode, destination.lstat()))
                        self.assertEqual(destination.read_bytes(), body.encode())
                        self.assertEqual(db.execute('SELECT body,publication_state FROM batch_unit_input_pins '
                            'WHERE unit_key=?', (key,)).fetchone(), (body, 'reserved'))
                        with self.assertRaises(LookupError):
                            self.store.read_prepared_batch_unit(db, batch.batch_id, key, parent_bindings=[])
                        changes = db.total_changes
                        record = retry()
                        self.assertEqual(retry(), record)
                        self.assertEqual(db.total_changes, changes + 1)
                        self.assertEqual(json.loads(record.prepared_input.image_pin_json)['settings']['seed'], 123)
                        self.assertEqual(canonical_json(record.prepared_input), body.encode())
                        self.assertEqual(self.store.read_prepared_batch_unit(db, batch.batch_id, key, parent_bindings=[]), record)
                    self.assertEqual(destination.stat().st_nlink, 1)
                    self.assertEqual(retained_inventory(db, ref.execution_id), before)

    async def test_reserved_staging_alias_must_match_exact_bytes_and_only_owned_file_identity(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            key = batch.prepared_input.ordered_units[0].unit_key
            with patch.object(self.store, '_publish', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    self.prepare(db, batch, key)
            body, uri = db.execute('SELECT body,uri FROM batch_unit_input_pins').fetchone()
            destination = self.root / uri.removeprefix('kinodel://')
            staging = self.staging_path(destination)
            foreign = destination.with_name('.story-foreign')
            def snapshot():
                return [(p.lstat().st_ino, p.lstat().st_nlink, p.read_bytes() if p.is_file() else None)
                        if p.exists() else None for p in (staging, destination, foreign)]
            for failure in ('different_inode', 'foreign_link', 'foreign_destination', 'third_link', 'tampered', 'oversized',
                            'unlinked_mismatch', 'unlinked_oversized', 'prefix_foreign_link', 'empty_destination',
                            'prefix_destination', 'directory'):
                staging.write_bytes(body.encode())
                if failure == 'different_inode':
                    destination.write_bytes(body.encode())  # Same bytes do NOT prove alias ownership.
                elif failure == 'foreign_link':
                    os.link(staging, foreign)  # No destination: this link cannot be publisher-owned.
                elif failure == 'foreign_destination':
                    staging.unlink()
                    destination.write_bytes(body.encode())
                    os.link(destination, foreign)  # Unknown .story- aliases must not be scanned/deleted.
                elif failure in ('third_link', 'tampered', 'oversized'):
                    os.link(staging, destination)
                    if failure == 'third_link':
                        os.link(staging, foreign)
                    else:
                        staging.write_bytes(b'foreign bytes' if failure == 'tampered' else b'x' * (MAX_JSON_BYTES + 1))
                elif failure in ('unlinked_mismatch', 'unlinked_oversized'):
                    staging.write_bytes(body.encode()[:127] + b'!' if failure == 'unlinked_mismatch'
                                        else b'x' * (MAX_JSON_BYTES + 1))
                elif failure == 'prefix_foreign_link':
                    staging.write_bytes(body.encode()[:128])
                    os.link(staging, foreign)
                elif failure in ('empty_destination', 'prefix_destination'):
                    staging.write_bytes(b'' if failure == 'empty_destination' else body.encode()[:128])
                    os.link(staging, destination)  # Destination-present recovery always requires the FULL body.
                else:
                    staging.unlink()
                    staging.mkdir()
                paths = (staging, destination, foreign)
                before = snapshot()
                with self.subTest(failure=failure), self.offline():
                    with self.assertRaises(ValueError):
                        self.store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=[])
                    with self.assertRaises(LookupError):
                        self.store.read_prepared_batch_unit(db, batch.batch_id, key, parent_bindings=[])
                    self.assertEqual(db.execute('SELECT publication_state FROM batch_unit_input_pins').fetchone(), ('reserved',))
                    self.assertEqual(snapshot(), before)
                for path in paths:
                    if path.is_dir():
                        path.rmdir()
                    else:
                        path.unlink(missing_ok=True)
                db.execute("UPDATE batch_unit_input_pins SET publication_state='reserved'")
            with self.offline(), patch.object(self.store.os, 'fsync', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    self.store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=[])
            self.assertFalse(staging.exists())  # This invocation can clean its own failed exclusive write.
            self.assertFalse(destination.exists())
            with self.offline():
                unit = self.store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=[])
            os.link(destination, staging)
            with self.offline(), self.assertRaises(ValueError):
                self.store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=[])
            self.assertTrue(staging.exists())  # Published hardlinks are NEVER repaired.
            self.assertEqual(destination.stat().st_nlink, 2)
            with self.assertRaises(ValueError):
                self.store.read_prepared_batch_unit(db, batch.batch_id, key, parent_bindings=[])
            staging.unlink()
            self.assertEqual(self.store.read_prepared_batch_unit(db, batch.batch_id, key, parent_bindings=[]), unit)

    async def test_real_process_death_after_reservation_or_publish_recovers_seed(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            before = retained_inventory(db, ref.execution_id)
        child = '''
import os, sys
from pathlib import Path
from backend import batch_store, batch_generation as generation, database
from backend.comfyui import NativeImagePreparationContext
from tests.test_comfyui_workflows import ROOT, installed_schemas
publish = batch_store._publish
def die(path, body):
    if sys.argv[3] == 'publish':
        publish(path, body)
    os._exit(23)
batch_store._publish = die
generation.registry.secrets.randbelow = lambda ceiling: 123
with database.open_database(Path(sys.argv[1])) as db:
    batch = batch_store.read_batch_input(db, sys.argv[2])
    key = sys.argv[4]
    _, _, binding = generation._unit(batch.prepared_input, key)
    context = NativeImagePreparationContext(binding.workflow_id, binding.registry_digest,
        batch.prepared_input.connection.connection, batch.prepared_input.connection.endpoint_digest,
        (ROOT / 'txt2img krea2 api v1_local.json').read_bytes(), installed_schemas(), {})
    batch_store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=[], context=context)
'''
        for stage, key in zip(('reserve', 'publish'), (u.unit_key for u in batch.prepared_input.ordered_units[:2]), strict=True):
            result = subprocess.run([sys.executable, '-B', '-c', child, str(self.root), batch.batch_id, stage, key],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 23, result.stderr)
            with database.open_database(self.root) as db:
                body, state = db.execute('SELECT body,publication_state FROM batch_unit_input_pins WHERE unit_key=?', (key,)).fetchone()
                self.assertEqual(state, 'reserved')
                with self.assertRaises(LookupError):
                    self.store.read_prepared_batch_unit(db, batch.batch_id, key, parent_bindings=[])
                with self.offline():
                    unit = self.store.prepare_saved_batch_unit(db, batch.batch_id, key, parent_bindings=[])
                self.assertEqual(canonical_json(unit.prepared_input), body.encode())
                self.assertEqual(json.loads(unit.prepared_input.image_pin_json)['settings']['seed'], 123)
                self.assertEqual(retained_inventory(db, ref.execution_id), before)

    async def test_real_batch_process_death_replays_original_reservation_without_catalog(self):
        async with self.committed() as (db, ref):
            before = retained_inventory(db, ref.execution_id)
        child = '''
import json, os, sys
from pathlib import Path
from backend import batch_store, database
publish = batch_store._publish
def die(path, body):
    if sys.argv[3] == 'publish':
        publish(path, body)
    os._exit(23)
batch_store._publish = die
with database.open_database(Path(sys.argv[1])) as db:
    args = json.loads(sys.argv[2])
    execution = args['source_plan_ref']['execution_id']
    batch_store.pin_saved_batch_input(db, execution, **args)
'''
        for index, stage in enumerate(('reserve', 'publish')):
            activation = 'sha256:' + str(index + 1) * 64
            args = dict(source_plan_ref=ref.model_dump(mode='json'), image_size={'width': 768, 'height': 768},
                        image_profile=self.profile, connection=CONNECTION, activation_id=activation)
            result = subprocess.run([sys.executable, '-B', '-c', child, str(self.root), json.dumps(args), stage],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 23, result.stderr)
            with database.open_database(self.root) as db:
                batch_id, body, state = db.execute('SELECT batch_id,body,publication_state FROM batch_input_pins WHERE activation_id=?',
                                                   (activation,)).fetchone()
                self.assertEqual(state, 'reserved')
                with self.assertRaises(LookupError):
                    self.store.read_batch_input(db, batch_id)
                with self.offline():
                    batch = self.pin(db, ref, activation_id=activation)
                self.assertEqual(canonical_json(batch.prepared_input), body.encode())
                self.assertEqual(retained_inventory(db, ref.execution_id), before)


if __name__ == '__main__':
    unittest.main()
