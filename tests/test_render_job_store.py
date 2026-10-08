"""Offline initial portrait intents; no dispatch, acceptance or candidates."""

from contextlib import closing
import importlib.util
import json
import sqlite3
import subprocess
import sys
from typing import Any
import unittest

from backend import batch_store, database
from backend.domain import sha256_digest
from tests import test_batch_store as pins
from tests import test_story_wardrobe_api as fixtures
from tests.test_story_wardrobe_runtime import retained_inventory


class RenderJobStoreTests(fixtures.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    # Reuse real saved compact V2 fixtures without inheriting their test methods.
    committed: Any = pins.BatchStoreTests.committed
    pin: Any = pins.BatchStoreTests.pin
    context: Any = pins.BatchStoreTests.context
    parents: Any = pins.BatchStoreTests.parents
    prepare: Any = pins.BatchStoreTests.prepare
    path: Any = pins.BatchStoreTests.path
    offline: Any = pins.BatchStoreTests.offline

    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('backend.render_job_store'),
                             'Durable portrait job/initial intent storage is missing')
        from backend import render_job_store
        self.jobs = render_job_store
        self.store = batch_store
        self.profile = pins.production_catalog()['image_only']['profiles'][0]['pin']

    def create(self, db, batch, unit, **changes):
        args = dict(expected_unit_digest=unit.input_digest)
        args.update(changes)
        return self.jobs.create_portrait_job(db, batch.batch_id, unit.unit_key, **args)

    def read(self, db, record, unit):
        return self.jobs.read_portrait_job(db, record.job_id, expected_unit_digest=unit.input_digest)

    def pair_counts(self, db):
        return tuple(db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                     for table in ('render_jobs', 'render_submission_attempts'))

    async def test_create_idempotent_and_reopen_exact_offline_intent_without_mutation(self):
        async with self.committed() as (db, ref):
            before = retained_inventory(db, ref.execution_id)
            batch = self.pin(db, ref)
            unit = self.prepare(db, batch, batch.prepared_input.ordered_units[0].unit_key)
            files = (self.path(batch).read_bytes(), self.path(unit).read_bytes())
            with self.offline():
                record = self.create(db, batch, unit)
                changes = db.total_changes
                self.assertEqual(self.create(db, batch, unit), record)
                self.assertEqual(self.read(db, record, unit), record)
                self.assertEqual(db.total_changes, changes)
            self.assertEqual(record.intent_digest, sha256_digest(record.intent_body))
            intent = json.loads(record.intent_body)
            self.assertEqual(intent['job_id'], record.job_id)
            self.assertEqual(intent['attempt_id'], record.attempt_id)
            self.assertEqual(intent['project_id'], ref.project_id)
            self.assertEqual((intent['batch_id'], intent['batch_input_digest'], intent['batch_input_uri']),
                             (batch.batch_id, batch.input_digest, batch.uri))
            self.assertEqual((intent['unit_key'], intent['unit_input_digest'], intent['unit_input_uri']),
                             (unit.unit_key, unit.input_digest, unit.uri))
            self.assertEqual(record.prepared_input, unit.prepared_input)
            self.assertNotIn('prompt_id', intent)
            self.assertNotIn('definitely_not_sent', intent)
            self.assertEqual(self.pair_counts(db), (1, 1))
            self.assertEqual(retained_inventory(db, ref.execution_id), before)
        with database.open_database(self.root) as db, self.offline():
            self.assertEqual(self.read(db, record, unit), record)
            self.assertEqual(self.create(db, batch, unit), record)
            image = json.loads(record.prepared_input.image_pin_json)
            self.assertEqual(image['settings']['seed'], 42)
            self.assertEqual(image['graph'], json.loads(unit.prepared_input.image_pin_json)['graph'])
            self.assertEqual(batch.prepared_input.profile_snapshot['readiness'], 'preparation_only')
            self.assertIs(batch.prepared_input.profile_snapshot['can_run'], False)
            self.assertEqual(retained_inventory(db, ref.execution_id), before)
            self.assertEqual((self.path(batch).read_bytes(), self.path(unit).read_bytes()), files)

    async def test_exact_digest_and_unit_selectors_reject_without_allocating(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            unit = self.prepare(db, batch, batch.prepared_input.ordered_units[0].unit_key)
            with self.offline():
                for digest in ('sha256:' + '0' * 64, '', True):
                    with self.subTest(digest=digest), self.assertRaises(ValueError):
                        self.create(db, batch, unit, expected_unit_digest=digest)
                for batch_id, key in ((batch.batch_id, 'unknown'), ('sha256:' + '0' * 64, unit.unit_key)):
                    with self.assertRaises((ValueError, LookupError)):
                        self.jobs.create_portrait_job(db, batch_id, key, expected_unit_digest=unit.input_digest)
                self.assertEqual(self.pair_counts(db), (0, 0))
                record = self.create(db, batch, unit)
                with self.assertRaises(ValueError):
                    self.jobs.read_portrait_job(db, record.job_id, expected_unit_digest='sha256:' + '0' * 64)
                with self.assertRaises(LookupError):
                    self.jobs.read_portrait_job(db, 'sha256:' + '0' * 64, expected_unit_digest=unit.input_digest)

    async def test_background_and_reference_sheet_are_not_portrait_jobs(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            for planned in batch.prepared_input.ordered_units[1:]:
                unit = self.prepare(db, batch, planned.unit_key)
                with self.subTest(key=unit.unit_key), self.offline(), self.assertRaises(ValueError):
                    self.create(db, batch, unit)
            self.assertEqual(self.pair_counts(db), (0, 0))

    async def test_published_inputs_required_and_corruption_never_repairs(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            unit = self.prepare(db, batch, batch.prepared_input.ordered_units[0].unit_key)
            record = self.create(db, batch, unit)
            for pin, table, selector in ((batch, 'batch_input_pins', 'batch_id'),
                                         (unit, 'batch_unit_input_pins', 'batch_id')):
                path = self.path(pin)
                original = path.read_bytes()
                for body in (b'bad input', None):
                    if body is None:
                        path.unlink()
                    else:
                        path.write_bytes(body)
                    with self.offline():
                        for action in (lambda: self.create(db, batch, unit), lambda: self.read(db, record, unit)):
                            with self.assertRaises((ValueError, OSError)):
                                action()
                    self.assertEqual(self.pair_counts(db), (1, 1))
                    self.assertEqual(path.read_bytes() if path.exists() else None, body)
                    path.write_bytes(original)
                db.execute(f"UPDATE {table} SET publication_state='reserved' WHERE {selector}=?", (batch.batch_id,))
                with self.assertRaises(LookupError):
                    self.create(db, batch, unit)
                db.execute(f"UPDATE {table} SET publication_state='published' WHERE {selector}=?", (batch.batch_id,))
            self.assertEqual(self.read(db, record, unit), record)

    async def test_sql_pin_and_project_identity_corruption_rejects(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            unit = self.prepare(db, batch, batch.prepared_input.ordered_units[0].unit_key)
            record = self.create(db, batch, unit)
            mutations = [
                ('UPDATE executions SET project_id=? WHERE execution_id=?',
                 ('00000000-0000-0000-0000-000000000000', ref.execution_id), (ref.project_id, ref.execution_id)),
                ('UPDATE render_jobs SET unit_input_digest=? WHERE job_id=?',
                 ('sha256:' + '0' * 64, record.job_id), (unit.input_digest, record.job_id)),
                ('UPDATE render_submission_attempts SET attempt_id=? WHERE job_id=?',
                 ('sha256:' + '0' * 64, record.job_id), (record.attempt_id, record.job_id)),
                ('UPDATE render_submission_attempts SET intent_digest=? WHERE job_id=?',
                 ('sha256:' + '0' * 64, record.job_id), (record.intent_digest, record.job_id)),
                ('UPDATE render_submission_attempts SET intent_body=? WHERE job_id=?',
                 ('{}', record.job_id), (record.intent_body.decode(), record.job_id)),
                ('UPDATE batch_input_pins SET body=? WHERE batch_id=?',
                 ('{}', batch.batch_id), (self.path(batch).read_bytes().decode(), batch.batch_id)),
                ('UPDATE batch_unit_input_pins SET input_digest=? WHERE batch_id=?',
                 ('sha256:' + '0' * 64, batch.batch_id), (unit.input_digest, batch.batch_id)),
            ]
            for sql, changed, restore in mutations:
                db.execute(sql, changed)
                with self.subTest(sql=sql), self.offline():
                    for action in (lambda: self.create(db, batch, unit), lambda: self.read(db, record, unit)):
                        with self.assertRaises(ValueError):
                            action()
                db.execute(sql, restore)
            db.execute('DELETE FROM render_submission_attempts')
            with self.assertRaises(ValueError):
                self.create(db, batch, unit)
            self.assertEqual(self.pair_counts(db), (1, 0))

    async def test_job_identity_and_unit_ownership_are_checked_not_repaired(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            unit = self.prepare(db, batch, batch.prepared_input.ordered_units[0].unit_key)
            other = self.prepare(db, batch, batch.prepared_input.ordered_units[1].unit_key)
            record = self.create(db, batch, unit)
            db.execute('UPDATE render_jobs SET unit_key=? WHERE job_id=?', (other.unit_key, record.job_id))
            with self.assertRaises(ValueError):
                self.read(db, record, unit)
            with self.assertRaises((ValueError, sqlite3.IntegrityError)):
                self.create(db, batch, unit)
            db.execute('UPDATE render_jobs SET unit_key=? WHERE job_id=?', (unit.unit_key, record.job_id))
            self.assertEqual(self.read(db, record, unit), record)

    async def test_attempt_insert_failure_has_no_partial_visible_job(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            unit = self.prepare(db, batch, batch.prepared_input.ordered_units[0].unit_key)
            db.execute("CREATE TEMP TRIGGER fail_initial BEFORE INSERT ON render_submission_attempts "
                       "BEGIN SELECT RAISE(ABORT, 'injected attempt failure'); END")
            with self.assertRaises(sqlite3.IntegrityError):
                self.create(db, batch, unit)
            self.assertFalse(db.in_transaction)
            self.assertEqual(self.pair_counts(db), (0, 0))
            with closing(sqlite3.connect(self.root / database.DATABASE_NAME)) as observer:
                self.assertEqual(self.pair_counts(observer), (0, 0))
            db.execute('DROP TRIGGER fail_initial')
            record = self.create(db, batch, unit)
            self.assertEqual(self.read(db, record, unit), record)

    async def test_caller_transaction_is_not_committed_or_overwritten(self):
        async with self.committed() as (db, ref):
            batch = self.pin(db, ref)
            unit = self.prepare(db, batch, batch.prepared_input.ordered_units[0].unit_key)
            record = self.create(db, batch, unit)
            db.execute('BEGIN IMMEDIATE')
            with self.assertRaises(ValueError):
                self.create(db, batch, unit)
            with self.assertRaises(ValueError):
                self.read(db, record, unit)
            self.assertTrue(db.in_transaction)
            db.execute('ROLLBACK')

    async def test_real_process_death_before_and_after_commit_reopens_absent_or_exact_pair(self):
        async with self.committed() as (db, ref):
            before = retained_inventory(db, ref.execution_id)
            batch = self.pin(db, ref)
            unit = self.prepare(db, batch, batch.prepared_input.ordered_units[0].unit_key)
            files = (self.path(batch).read_bytes(), self.path(unit).read_bytes())
        script = '''
import os, sys
from pathlib import Path
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
from backend import database, render_job_store as jobs
root, batch_id, key, digest, phase = sys.argv[1:]
original = jobs._transaction
@contextmanager
def crash(db):
    with original(db):
        yield
        if phase == 'before':
            os._exit(71)
    os._exit(72)
with database.open_database(Path(root)) as db, ExitStack() as stack:
    for target in ('httpx.Client.send', 'httpx.AsyncClient',
                   'backend.production.production_catalog', 'backend.comfyui_workflows.workflow_snapshot',
                   'backend.comfyui_workflows.secrets.randbelow',
                   'backend.batch_preparation.read_saved_batch_input'):
        stack.enter_context(patch(target, side_effect=AssertionError('No effects: ' + target)))
    stack.enter_context(patch.object(jobs, '_transaction', crash))
    jobs.create_portrait_job(db, batch_id, key, expected_unit_digest=digest)
raise AssertionError('Did not reach crash point')
'''
        first = subprocess.run([sys.executable, '-B', '-c', script, str(self.root), batch.batch_id,
                                unit.unit_key, unit.input_digest, 'before'], capture_output=True, text=True, timeout=60)
        self.assertEqual(first.returncode, 71, first.stdout + first.stderr)
        with database.open_database(self.root) as db, self.offline():
            self.assertEqual(self.pair_counts(db), (0, 0))
            # Establish expected exact identity/body then remove only the test records.
            expected = self.create(db, batch, unit)
            db.execute('DELETE FROM render_submission_attempts')
            db.execute('DELETE FROM render_jobs')
        second = subprocess.run([sys.executable, '-B', '-c', script, str(self.root), batch.batch_id,
                                 unit.unit_key, unit.input_digest, 'after'], capture_output=True, text=True, timeout=60)
        self.assertEqual(second.returncode, 72, second.stdout + second.stderr)
        with database.open_database(self.root) as db, self.offline():
            self.assertEqual(self.pair_counts(db), (1, 1))
            self.assertEqual(self.read(db, expected, unit), expected)
            self.assertEqual(self.create(db, batch, unit), expected)
            self.assertEqual(retained_inventory(db, ref.execution_id), before)
            self.assertEqual((self.path(batch).read_bytes(), self.path(unit).read_bytes()), files)


if __name__ == '__main__':
    unittest.main()
