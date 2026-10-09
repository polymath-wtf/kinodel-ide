"""6B.3 reference STORAGE only: all completions are trusted local fixture facts."""

from contextlib import contextmanager
import importlib.util
import json
import subprocess
import sys
from typing import Any
import unittest
from unittest.mock import patch
from uuid import uuid4

from backend import batch_store, database, portrait_candidate_store as candidates
from backend import portrait_submission_store as submissions, render_job_store as jobs
from backend.domain import canonical_json, sha256_digest
from tests import test_story_wardrobe_api as fixtures
from tests import test_anchor_parent_resolver as parent_fixtures, test_batch_store as batch_fixtures
from tests.test_portrait_worker import ZERO


class AnchorReferenceStoreTests(fixtures.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    source: Any = parent_fixtures.AnchorParentResolverTests.source
    batch: Any = parent_fixtures.AnchorParentResolverTests.batch
    imported: Any = parent_fixtures.AnchorParentResolverTests.imported
    complete: Any = parent_fixtures.AnchorParentResolverTests.complete
    parent_pair: Any = parent_fixtures.AnchorParentResolverTests.parent_pair
    pin: Any = batch_fixtures.BatchStoreTests.pin
    context: Any = batch_fixtures.BatchStoreTests.context
    parents: Any = batch_fixtures.BatchStoreTests.parents
    prepare: Any = batch_fixtures.BatchStoreTests.prepare
    path: Any = batch_fixtures.BatchStoreTests.path
    offline: Any = batch_fixtures.BatchStoreTests.offline

    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('backend.anchor_reference_store'), 'Reference storage owner is missing')
        from backend import anchor_reference_store
        self.refs = anchor_reference_store
        self.store = batch_store
        self.profile = batch_fixtures.production_catalog()['image_only']['profiles'][0]['pin']

    def sheet(self, db, ref, **changes):
        batch = self.batch(db, ref, **changes)
        records, bindings = self.parent_pair(db, batch)
        unit = self.prepare(db, batch, 'sheet-0', parent_bindings=bindings)
        job = jobs.create_anchor_unit_job(db, batch.batch_id, 'sheet-0', expected_unit_digest=unit.input_digest,
                                         parent_bindings=bindings)
        return batch, unit, job, records

    def authorize(self, db, unit, job, *, subfolder=''):
        preview = self.refs.preview_anchor_reference_intent(db, job.job_id, expected_project_id=self.project,
            expected_unit_digest=unit.input_digest, subfolder=subfolder)
        return self.refs.authorize_anchor_reference_transfer(db, job.job_id, expected_project_id=self.project,
            expected_unit_digest=unit.input_digest, expected_intent_digest=preview.intent_digest, subfolder=subfolder)

    def args(self, record, *, revision=True):
        args: dict[str, Any] = dict(expected_project_id=self.project, expected_unit_digest=record.intent.unit_input_digest,
                                   expected_intent_digest=record.intent_digest)
        if revision:
            args['expected_revision'] = record.revision
        return args

    def role(self, record, role):
        return record.references[0 if role == 'portrait' else 1]

    def claim(self, db, record, role):
        return self.refs.claim_anchor_reference_upload(db, record.intent.job_id, role=role, **self.args(record))

    def receipt(self, db, record, role, *, name=None, subfolder=None):
        intent = record.intent.references[0 if role == 'portrait' else 1]
        native = dict(name=name or intent.name, subfolder=intent.subfolder if subfolder is None else subfolder, type='input')
        return self.refs.record_anchor_reference_receipt(db, record.intent.job_id, role=role, receipt=native, **self.args(record))

    def verify(self, db, record, role, **changes):
        intent = record.intent.references[0 if role == 'portrait' else 1]
        args = dict(expected_receipt_digest=self.role(record, role).receipt.digest,
                    remote_digest=intent.parent.digest, source_digest=intent.parent.digest, byte_length=intent.parent.byte_length)
        args.update(changes)
        return self.refs.verify_anchor_reference_remote(db, record.intent.job_id, role=role, **self.args(record), **args)

    def verified_pair(self, db, record, *, renamed=False, windows=False):
        for role in ('portrait', 'background'):
            record = self.claim(db, record, role)
            item = record.intent.references[0 if role == 'portrait' else 1]
            name = item.name[:-4] + ' (2).png' if renamed else item.name
            record = self.receipt(db, record, role, name=name,
                subfolder=item.subfolder.replace('/', '\\') if windows else item.subfolder)
            record = self.verify(db, record, role)
        return record

    async def test_preview_authorization_reopen_ordered_owned_pins_no_mutation(self):
        async with self.source() as (db, ref):
            batch, unit, job, original = self.sheet(db, ref)
            changes = db.total_changes
            preview = self.refs.preview_anchor_reference_intent(db, job.job_id, expected_project_id=self.project,
                expected_unit_digest=unit.input_digest)
            self.assertEqual(db.total_changes, changes)
            record = self.authorize(db, unit, job)
            self.assertEqual(record.intent_digest, preview.intent_digest)
            self.assertEqual((record.state, record.revision), ('authorized', 0))
            for item, role, node, (_, parent_job, candidate) in zip(record.intent.references, ('portrait', 'background'),
                                                                  ('470', '496'), original, strict=True):
                self.assertEqual((item.role, item.node_id, item.input_field, item.type, item.overwrite, item.subfolder),
                                 (role, node, 'image', 'input', False, ''))
                self.assertEqual((item.parent.candidate_id, item.parent.job_id, item.parent.attempt_id, item.parent.digest),
                                 (candidate.candidate_id, parent_job.job_id, parent_job.attempt_id, candidate.digest))
                self.assertTrue(item.name.startswith('kinodel-' + job.job_id[7:] + '-' + role + '-'))
                self.assertNotEqual(item.name, job.prepared_input.parent_bindings[0].input_name)
            self.assertEqual(len({item.name for item in record.intent.references}), 2)
            self.assertNotIn('original_bytes', json.loads(canonical_json(record)))
            self.assertEqual(self.authorize(db, unit, job), record)
            self.assertEqual(canonical_json(unit.prepared_input), self.path(unit).read_bytes())
        with database.open_database(self.root) as db, self.offline():
            before = db.total_changes
            self.assertEqual(self.refs.read_anchor_reference_transfer(db, job.job_id, **self.args(record, revision=False)), record)
            self.assertEqual(db.total_changes, before)

    async def test_fresh_claim_once_restart_never_grants_upload_again_and_role_order(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            record = self.authorize(db, unit, job)
            with self.assertRaises(ValueError):
                self.claim(db, record, 'background')
            dispatched = self.claim(db, record, 'portrait')
            self.assertEqual(self.role(dispatched, 'portrait').state, 'dispatching')
            for current in (record, dispatched):
                with self.assertRaises(ValueError):
                    self.claim(db, current, 'portrait')
        with database.open_database(self.root) as db, self.offline():
            reopened = self.refs.read_anchor_reference_transfer(db, job.job_id, **self.args(dispatched, revision=False))
            self.assertEqual(reopened, dispatched)
            with self.assertRaises(ValueError):
                self.claim(db, reopened, 'portrait')
            blocked = self.refs.block_anchor_reference(db, job.job_id, role='portrait', reason='acceptance_unknown', **self.args(reopened))
            self.assertEqual(self.role(blocked, 'portrait').state, 'blocked_sent')
            self.assertIsNone(self.role(blocked, 'portrait').receipt)
            with self.assertRaises(ValueError):
                self.claim(db, blocked, 'portrait')
            with self.assertRaises(ValueError):
                self.claim(db, blocked, 'background')

    async def test_saved_receipt_get_resume_exact_replays_conflicts_and_final_graph(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            record = self.authorize(db, unit, job, subfolder='kinodel/nested')
            dispatched = self.claim(db, record, 'portrait')
            name = record.intent.references[0].name[:-4] + ' (1).png'
            received = self.receipt(db, dispatched, 'portrait', name=name, subfolder='kinodel\\nested')
            self.assertEqual(self.receipt(db, dispatched, 'portrait', name=name, subfolder='kinodel\\nested'), received)
            first_receipt = self.role(received, 'portrait').receipt
            assert first_receipt is not None
            self.assertEqual((first_receipt.subfolder, first_receipt.native_subfolder), ('kinodel/nested', 'kinodel\\nested'))
            for args in (dict(name=record.intent.references[0].name), dict(name=name, subfolder='other')):
                with self.assertRaises(ValueError):
                    self.receipt(db, received, 'portrait', **args)
            with self.assertRaises(ValueError):
                self.refs.finalize_anchor_references(db, job.job_id, **self.args(received))
        with database.open_database(self.root) as db, self.offline(), \
                patch('backend.comfyui_workflows.workflow_snapshot', side_effect=AssertionError('Current registry')):
            before = db.total_changes
            received = self.refs.read_anchor_reference_transfer(db, job.job_id, **self.args(received, revision=False))
            with self.assertRaises(ValueError):
                self.claim(db, received, 'portrait')
            self.assertEqual(db.total_changes, before)
            blocked = self.refs.block_anchor_reference(db, job.job_id, role='portrait', reason='remote_invalid', **self.args(received))
            self.assertEqual(self.role(blocked, 'portrait').receipt, self.role(received, 'portrait').receipt)
            verified = self.verify(db, blocked, 'portrait')  # GET retry, not another upload claim.
            self.assertEqual(self.verify(db, blocked, 'portrait'), verified)
            with self.assertRaises(ValueError):
                self.verify(db, verified, 'portrait', remote_digest=ZERO)
            record = self.claim(db, verified, 'background')
            record = self.receipt(db, record, 'background', name=record.intent.references[1].name[:-4] + ' (3).png',
                                  subfolder='kinodel\\nested')
            record = self.verify(db, record, 'background')
            final = self.refs.finalize_anchor_references(db, job.job_id, **self.args(record))
            self.assertEqual(final.state, 'finalized')
            assert final.final is not None
            self.assertEqual(self.refs.finalize_anchor_references(db, job.job_id, **self.args(record)), final)
            self.assertEqual(self.refs.read_anchor_reference_transfer(db, job.job_id, **self.args(final, revision=False)), final)
            prepared = json.loads(unit.prepared_input.image_pin_json)
            graph = json.loads(final.final.graph_json)
            self.assertEqual(final.final.seed, prepared['settings']['seed'])
            self.assertEqual(final.final.graph_digest, sha256_digest(final.final.graph_json.encode()))
            for role, node in (('portrait', '470'), ('background', '496')):
                receipt = self.role(final, role).receipt
                assert receipt is not None
                self.assertEqual(graph[node]['inputs']['image'], receipt.subfolder + '/' + receipt.name)
                graph[node]['inputs']['image'] = prepared['graph'][node]['inputs']['image']
            self.assertEqual(graph, prepared['graph'], 'Only the two declared LoadImage literals may change')
            self.assertEqual(self.path(unit).read_bytes(), canonical_json(unit.prepared_input))
            preview = submissions.preview_anchor_unit_submission(db, job.job_id, expected_unit_digest=unit.input_digest)
            self.assertEqual(preview.graph_digest, final.final.graph_digest)
            self.assertIsNone(submissions._row(db, job.job_id), 'Final reference pin alone never authorizes prompt dispatch')

    async def test_empty_nonempty_windows_and_invalid_receipt_paths_namespace_type_and_role_swap(self):
        async with self.source() as (db, ref):
            for i, folder in enumerate(('', 'nested/deep', 'nested\\deep')):
                _, unit, job, _ = self.sheet(db, ref, activation_id=sha256_digest(str(i).encode()))
                record = self.authorize(db, unit, job, subfolder=folder)
                record = self.verified_pair(db, record, renamed=True, windows=True)
                final = self.refs.finalize_anchor_references(db, job.job_id, **self.args(record))
                assert final.final is not None
                self.assertEqual(final.final.seed, 42)
            _, unit, job, _ = self.sheet(db, ref, activation_id=ZERO)
            record = self.claim(db, self.authorize(db, unit, job), 'portrait')
            good = dict(name=record.intent.references[0].name, subfolder='', type='input')
            cases = [{**good, 'name': record.intent.references[1].name}, {**good, 'name': 'foreign.png'},
                     {**good, 'name': '../' + good['name']}, {**good, 'name': 'C:evil.png'},
                     {**good, 'name': good['name'] + ' [input]'}, {**good, 'name': 'NUL.png'},
                     {**good, 'type': 'output'}, {**good, 'overwrite': True}]
            cases += [{**good, 'subfolder': path} for path in ('/absolute', '\\absolute', '\\\\host\\share',
                       'C:/input', 'a/../b', 'a//b', 'a\\..\\b', 'COM1', 'a:ads', 'a\0b', 'a[output]', 'a%20b', 'other')]
            for receipt in cases:
                before = db.total_changes
                with self.subTest(receipt=receipt), self.assertRaises(ValueError):
                    self.refs.record_anchor_reference_receipt(db, job.job_id, role='portrait', receipt=receipt, **self.args(record))
                self.assertEqual(db.total_changes, before)

    async def test_verification_needs_saved_receipt_exact_source_remote_digest_length_and_selector(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            record = self.claim(db, self.authorize(db, unit, job), 'portrait')
            item = record.intent.references[0]
            with self.assertRaises(ValueError):
                self.refs.verify_anchor_reference_remote(db, job.job_id, role='portrait', **self.args(record),
                    expected_receipt_digest=ZERO, remote_digest=item.parent.digest, source_digest=item.parent.digest,
                    byte_length=item.parent.byte_length)
            record = self.receipt(db, record, 'portrait')
            for changes in (dict(remote_digest=ZERO), dict(source_digest=ZERO), dict(byte_length=1),
                            dict(expected_receipt_digest=ZERO)):
                before = db.total_changes
                with self.assertRaises(ValueError):
                    self.verify(db, record, 'portrait', **changes)
                self.assertEqual(db.total_changes, before)
            with self.assertRaises(TypeError):
                self.refs.verify_anchor_reference_remote(db, job.job_id, role='portrait', verified=True, **self.args(record))  # type: ignore[call-arg] -- rejected bypass

    async def test_project_digest_selector_subfolder_and_revision_conflicts_refuse_before_mutation(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            record = self.authorize(db, unit, job)
            for changes in (dict(expected_project_id='11111111-1111-4111-8111-111111111111'),
                            dict(expected_unit_digest=ZERO), dict(expected_intent_digest=ZERO), dict(expected_revision=4)):
                before = db.total_changes
                with self.assertRaises(ValueError):
                    self.refs.claim_anchor_reference_upload(db, job.job_id, role='portrait', **{**self.args(record), **changes})
                self.assertEqual(db.total_changes, before)
            with self.assertRaises(ValueError):
                self.authorize(db, unit, job, subfolder='changed')
            db.execute('BEGIN')
            with self.assertRaises(ValueError):
                self.claim(db, record, 'portrait')
            self.assertTrue(db.in_transaction)
            db.execute('ROLLBACK')

    async def test_predispatch_readiness_block_is_not_potentially_sent_and_clear_rechecks_parents(self):
        async with self.source() as (db, ref):
            _, unit, job, original = self.sheet(db, ref)
            record = self.authorize(db, unit, job)
            blocked = self.refs.block_anchor_reference(db, job.job_id, role='portrait', reason='readiness_unavailable', **self.args(record))
            self.assertEqual(self.role(blocked, 'portrait').state, 'blocked_unsent')
            self.assertIsNone(self.role(blocked, 'portrait').dispatch_revision)
            with self.assertRaises(ValueError):
                self.refs.block_anchor_reference(db, job.job_id, role='portrait', reason='readiness_unavailable',
                    **{**self.args(blocked), 'expected_revision': True})
            path = self.path(original[0][2])
            saved = path.read_bytes()
            path.write_bytes(b'corrupt')
            before = db.total_changes
            with self.assertRaises((OSError, ValueError)):
                self.refs.revalidate_anchor_reference_readiness(db, job.job_id, role='portrait', **self.args(blocked))
            self.assertEqual(db.total_changes, before)
            path.write_bytes(saved)
            ready = self.refs.revalidate_anchor_reference_readiness(db, job.job_id, role='portrait', **self.args(blocked))
            dispatched = self.claim(db, ready, 'portrait')
            with self.assertRaises(ValueError):
                self.refs.revalidate_anchor_reference_readiness(db, job.job_id, role='portrait', **self.args(dispatched))

    async def test_cas_pin_drift_and_write_fault_roll_back_without_dispatch_permission(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            record = self.authorize(db, unit, job)
            before = self.refs._row(db, job.job_id)
            transaction = self.refs._transaction
            @contextmanager
            def drift(db):
                with transaction(db):
                    db.execute("UPDATE render_submission_attempts SET intent_body='{}' WHERE job_id=?", (job.job_id,))
                    yield
            with patch.object(self.refs, '_transaction', side_effect=drift), self.assertRaises(ValueError):
                self.claim(db, record, 'portrait')
            self.assertEqual(self.refs._row(db, job.job_id), before)
            self.assertEqual(jobs.read_anchor_unit_job(db, job.job_id, expected_unit_digest=unit.input_digest), job)
            with patch.object(self.refs, '_transaction', side_effect=OSError('disk full')), self.assertRaises(OSError):
                self.claim(db, record, 'portrait')
            self.assertEqual(self.refs._row(db, job.job_id), before)

    async def test_real_process_death_after_claim_and_receipt_commit_never_reclaims_upload(self):
        script = '''
import os,sys
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
from backend import database, anchor_reference_store as store
root,project,job,input_digest,intent_digest,phase=sys.argv[1:]
args=dict(expected_project_id=project,expected_unit_digest=input_digest,expected_intent_digest=intent_digest)
transaction=store._transaction
@contextmanager
def die_after_commit(db):
    with transaction(db): yield
    os._exit(91 if phase=='claim' else 92)
with database.open_database(Path(root)) as db:
    record=store.read_anchor_reference_transfer(db,job,**args)
    with patch.object(store,'_transaction',side_effect=die_after_commit):
        if phase=='claim': store.claim_anchor_reference_upload(db,job,role='portrait',expected_revision=record.revision,**args)
        else:
            intent=record.intent.references[0]
            store.record_anchor_reference_receipt(db,job,role='portrait',expected_revision=record.revision,
                receipt=dict(name=intent.name[:-4]+' (1).png',subfolder=intent.subfolder,type='input'),**args)
raise AssertionError('Expected process death after committed fact')
'''
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            record = self.authorize(db, unit, job)
        for phase, code in (('claim', 91), ('receipt', 92)):
            child = subprocess.run([sys.executable, '-B', '-c', script, str(self.root), self.project, job.job_id,
                unit.input_digest, record.intent_digest, phase], capture_output=True, text=True, timeout=60)
            self.assertEqual(child.returncode, code, child.stdout + child.stderr)
            with database.open_database(self.root) as db, self.offline():
                current = self.refs.read_anchor_reference_transfer(db, job.job_id, **self.args(record, revision=False))
                self.assertEqual(self.role(current, 'portrait').state, 'dispatching' if phase == 'claim' else 'received')
                with self.assertRaises(ValueError):
                    self.claim(db, current, 'portrait')
                if phase == 'receipt':
                    verified = self.verify(db, current, 'portrait')
                    self.assertEqual(self.role(verified, 'portrait').state, 'verified')

    async def test_corrupt_parent_cancel_or_foreign_binding_blocks_new_effects_without_writes(self):
        async with self.source() as (db, ref):
            _, unit, job, original = self.sheet(db, ref)
            record = self.authorize(db, unit, job)
            path = self.path(original[0][2])
            saved = path.read_bytes()
            path.write_bytes(b'corrupt')
            before = db.total_changes
            with self.assertRaises((OSError, ValueError)):
                self.claim(db, record, 'portrait')
            with self.assertRaises((OSError, ValueError)):
                self.authorize(db, unit, job)
            self.assertEqual(db.total_changes, before)
            path.write_bytes(saved)
            work_id = str(uuid4())
            db.execute("INSERT INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,status) "
                       "VALUES (?,?,'cancel','cancel-after-authorize',?,'pending')", (work_id, ref.execution_id, ZERO))
            db.execute("INSERT INTO execution_controls VALUES (?,'cancel-after-authorize','cancel',?,NULL)",
                       (ref.execution_id, work_id))
            before = db.total_changes
            with self.assertRaises(ValueError):
                self.claim(db, record, 'portrait')
            self.assertEqual(db.total_changes, before)

    async def test_final_record_corruption_and_shared_endpoint_folder_ownership_never_heal(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            record = self.authorize(db, unit, job)
            _, other_unit, other_job, _ = self.sheet(db, ref, activation_id=ZERO)
            other = self.authorize(db, other_unit, other_job)
            # Canonical foreign ownership record cannot silently be overwritten,
            # even when an injected claim reports the same source bytes.
            body = other.model_dump()
            body['intent']['references'][0]['name'] = record.intent.references[0].name
            body['intent_digest'] = sha256_digest(canonical_json(self.refs.AnchorReferenceIntentV1.model_validate(body['intent'])))
            forged = self.refs.AnchorReferenceTransferV1.model_validate(body)
            before_row = self.refs._row(db, other_job.job_id)
            db.execute('UPDATE anchor_reference_transfers SET intent_digest=?,record_digest=?,record_body=? WHERE job_id=?',
                (forged.intent_digest, sha256_digest(canonical_json(forged)), canonical_json(forged).decode(), other_job.job_id))
            before = db.total_changes
            with self.assertRaisesRegex(ValueError, 'ownership'):
                self.claim(db, record, 'portrait')
            self.assertEqual(db.total_changes, before)
            db.execute('UPDATE anchor_reference_transfers SET intent_digest=?,record_digest=?,record_body=? WHERE job_id=?',
                (before_row[3], before_row[4], before_row[5], other_job.job_id))
            final = self.refs.finalize_anchor_references(db, job.job_id, **self.args(self.verified_pair(db, record)))
            chronology = final.model_dump()
            chronology['references'][1]['dispatch_revision'] = chronology['references'][0]['verification_revision'] - 1
            with self.assertRaises(ValueError):
                self.refs.AnchorReferenceTransferV1.model_validate(chronology)
            saved = self.refs._row(db, job.job_id)
            value = json.loads(saved[5])
            graph = json.loads(value['final']['graph_json'])
            graph['470']['inputs']['image'] = 'foreign.png'
            value['final']['graph_json'] = json.dumps(graph, sort_keys=True, separators=(',', ':'))
            value['final']['graph_digest'] = sha256_digest(value['final']['graph_json'].encode())
            altered = canonical_json(self.refs.AnchorReferenceTransferV1.model_validate(value))
            db.execute('UPDATE anchor_reference_transfers SET record_digest=?,record_body=? WHERE job_id=?',
                       (sha256_digest(altered), altered.decode(), job.job_id))
            before = db.total_changes
            with self.assertRaises(ValueError):
                self.refs.read_anchor_reference_transfer(db, job.job_id, **self.args(final, revision=False))
            self.assertEqual(db.total_changes, before)
