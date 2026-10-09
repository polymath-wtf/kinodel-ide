"""6B.2 exact internal parents and original bytes; all sources/providers isolated."""

from contextlib import asynccontextmanager
import importlib.util
import io
import json
from typing import Any
import unittest
from unittest.mock import patch
from uuid import uuid4

from pydantic import TypeAdapter

from backend import batch_store, database, portrait_candidate_store as candidates
from backend import portrait_submission_store as submissions, render_job_store as jobs, wardrobe_store
from backend.api import fixture_story
from backend.domain import sha256_digest
from backend.story_control import open_story_runtime
from backend.story_store import _destination
from backend.wardrobe import AnchorKey
from tests import test_batch_store as pins, test_story_wardrobe_api as fixtures
from tests.test_portrait_candidate_store import png
from tests.test_portrait_worker import NOW, ZERO
from tests.test_story_cast import draft
from tests.test_wardrobe_compact_v2 import compact_draft


class AnchorParentResolverTests(fixtures.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    pin: Any = pins.BatchStoreTests.pin
    context: Any = pins.BatchStoreTests.context
    parents: Any = pins.BatchStoreTests.parents
    prepare: Any = pins.BatchStoreTests.prepare
    path: Any = pins.BatchStoreTests.path
    offline: Any = pins.BatchStoreTests.offline

    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('backend.anchor_parent_resolver'), 'Verified parent resolver is missing')
        from backend import anchor_parent_resolver
        self.resolver = anchor_parent_resolver
        self.store = batch_store
        self.profile = pins.production_catalog()['image_only']['profiles'][0]['pin']

    @asynccontextmanager
    async def source(self, *, future=False):
        subjects = ('comedian', 'traveler') if future else ('comedian',)
        story = draft(cast=[dict(subject_id=subject, description='Traveler') for subject in subjects], subject_ids=list(subjects))
        plan = compact_draft(subjects)
        if future:
            # A legitimate later independent hero remains unavailable to sheet-0.
            units = {unit['unit_key']: unit for unit in plan['batch_prompt']}
            plan['batch_prompt'] = [units[key] for key in ('face-0', 'location', 'sheet-0', 'face-1', 'sheet-1')]
        with self.transport(dict(status='ready', plan=plan, explanation=None)), patch.object(fixtures, 'draft', return_value=story):
            async with open_story_runtime(self.root, fixture_story, character_root=self.library) as runtime:
                receipt = await runtime.start_wardrobe(self.project, 'parents-' + uuid4().hex, ['s1'], self.brief)
                await runtime.run()
                self.approve(runtime, receipt.execution_id)
                await runtime.run()
                ref, _ = wardrobe_store.read_wardrobe_plan(runtime.db, receipt.execution_id)
                yield runtime.db, ref

    def batch(self, db, ref, **changes):
        return self.pin(db, ref, image_size=dict(width=512, height=512), **changes)

    def imported(self, db, batch, key, *, complete=True):
        unit = self.prepare(db, batch, key)
        job = jobs.create_anchor_unit_job(db, batch.batch_id, key, expected_unit_digest=unit.input_digest,
                                         parent_bindings=unit.prepared_input.parent_bindings)
        candidate = candidates.import_anchor_unit_candidate(db, job.job_id, job.attempt_id,
            expected_unit_digest=unit.input_digest, descriptor=dict(node_id='494' if job.kind == 'sheet' else '865',
                history_key='images', index=0, filename=key + '.png', subfolder='', type='output', mime_type='image/png'),
            stream=io.BytesIO(png()))
        if complete:
            self.complete(db, job, unit, candidate)
        return unit, job, candidate

    def complete(self, db, job, unit, candidate, *, through='completed'):
        preview = submissions.preview_anchor_unit_submission(db, job.job_id, expected_unit_digest=unit.input_digest)
        selectors: dict[str, Any] = dict(expected_unit_digest=unit.input_digest, expected_wire_digest=preview.wire_digest)
        record = submissions.authorize_anchor_unit_submission(db, job.job_id, **selectors, accepted_at_ms=NOW)
        if through == 'authorized':
            return record
        record = submissions.claim_anchor_unit_dispatch(db, job.job_id, **selectors, expected_revision=record.revision, now_ms=NOW + 1)
        if through == 'dispatching':
            return record
        prompt = 'parent-' + job.job_id[7:]
        proof = dict(kind='prompt_response', digest=sha256_digest(b'accepted'), prompt_id=prompt,
                     wire_digest=preview.wire_digest, endpoint_digest=preview.endpoint_digest)
        record = submissions.record_anchor_unit_acceptance(db, job.job_id, **selectors,
            expected_revision=record.revision, prompt_id=prompt, evidence=proof)
        if through == 'accepted':
            return record
        if through == 'blocked':
            return submissions.block_anchor_unit_submission(db, job.job_id, **selectors,
                expected_revision=record.revision, reason='contract_error')
        if through == 'failed':
            return submissions.fail_anchor_unit_submission(db, job.job_id, **selectors,
                expected_revision=record.revision, reason='contract_error')
        return submissions.complete_anchor_unit_submission(db, job.job_id, **selectors,
            expected_revision=record.revision, candidate_id=candidate.candidate_id,
            evidence={**proof, 'kind': 'history', 'digest': sha256_digest(b'successful declared history')})

    def parent_pair(self, db, batch, *, complete=True):
        records = [self.imported(db, batch, key, complete=complete) for key in ('face-0', 'location')]
        bindings = [dict(unit_key=unit.unit_key, source_id=candidate.candidate_id, digest=candidate.digest,
                         input_name=f'parents/{job.kind}.png') for unit, job, candidate in records]
        return records, bindings

    def resolve(self, db, batch, bindings, **changes):
        args: dict[str, Any] = dict(expected_batch_digest=batch.input_digest,
            expected_project_id=batch.prepared_input.source_plan_ref.project_id, parent_bindings=bindings)
        args.update(changes)
        return self.resolver.resolve_sheet_parents(db, batch.batch_id, 'sheet-0', **args)

    def assert_rejected(self, db, batch, bindings, **changes):
        before = db.total_changes
        with self.assertRaises((ValueError, LookupError, OSError)):
            self.resolve(db, batch, bindings, **changes)
        self.assertEqual(db.total_changes, before)
        self.assertFalse(db.in_transaction)

    async def test_exact_unapproved_completed_pair_before_preparation_and_offline_reopen(self):
        async with self.source() as (db, ref):
            batch = self.batch(db, ref)
            records, bindings = self.parent_pair(db, batch)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM batch_unit_input_pins').fetchone(), (2,))
            changes = db.total_changes
            with self.offline(), patch('backend.batch_generation.freeze_batch_input', side_effect=AssertionError('No refreeze')):
                resolved = self.resolve(db, batch, bindings)
            self.assertEqual(db.total_changes, changes)
            self.assertEqual([parent.role for parent in resolved], ['portrait', 'background'])
            for parent, (unit, job, candidate), binding in zip(resolved, records, bindings, strict=True):
                self.assertEqual(TypeAdapter(AnchorKey).validate_python(candidate.candidate_id, strict=True), candidate.candidate_id)
                self.assertEqual((parent.candidate_id, parent.job_id, parent.attempt_id, parent.unit_key,
                    parent.unit_input_digest, parent.digest, parent.original_bytes, parent.input_name),
                    (candidate.candidate_id, job.job_id, job.attempt_id, unit.unit_key, unit.input_digest,
                     candidate.digest, png(), binding['input_name']))
                self.assertEqual((parent.batch_id, parent.batch_input_digest, parent.activation_id, parent.source_plan_ref,
                    parent.story_ref, parent.connection), (batch.batch_id, batch.input_digest, batch.prepared_input.activation_id,
                    ref, batch.prepared_input.story_approval.story_ref, batch.prepared_input.connection))
                self.assertIsNone(db.execute('SELECT artifact_id FROM artifacts WHERE artifact_id=?', (parent.candidate_id,)).fetchone())
            unit = self.prepare(db, batch, 'sheet-0', parent_bindings=bindings)
            child = jobs.create_anchor_unit_job(db, batch.batch_id, 'sheet-0', expected_unit_digest=unit.input_digest,
                                               parent_bindings=bindings)
        with database.open_database(self.root) as db, self.offline(), \
                patch('backend.batch_generation.freeze_batch_input', side_effect=AssertionError('No refreeze')), \
                patch('backend.wardrobe_store.wardrobe_authority', side_effect=AssertionError('No generation authority')):
            changes = db.total_changes
            self.assertEqual(self.resolve(db, batch, bindings), resolved)
            self.assertEqual(self.resolve(db, batch, bindings, expected_child_digest=unit.input_digest,
                                         expected_child_job_id=child.job_id), resolved)
            self.assertEqual(db.total_changes, changes)
            with self.assertRaises(ValueError):
                submissions.preview_anchor_unit_submission(db, child.job_id, expected_unit_digest=unit.input_digest)

    async def test_exact_batch_project_child_and_sheet_selectors(self):
        async with self.source() as (db, ref):
            batch = self.batch(db, ref)
            records, bindings = self.parent_pair(db, batch)
            for changes in (dict(expected_batch_digest=ZERO), dict(expected_project_id=str(uuid4())),
                            dict(expected_child_digest=ZERO), dict(expected_child_job_id=records[0][1].job_id)):
                self.assert_rejected(db, batch, bindings, **changes)
            for key in ('face-0', 'location', 'unknown'):
                with self.assertRaises(ValueError):
                    self.resolver.resolve_sheet_parents(db, batch.batch_id, key, expected_batch_digest=batch.input_digest,
                        expected_project_id=self.project, parent_bindings=bindings)
            unit = self.prepare(db, batch, 'sheet-0', parent_bindings=bindings)
            self.assert_rejected(db, batch, bindings, expected_child_digest=unit.input_digest,
                                 expected_child_job_id=records[0][1].job_id)

    async def test_order_exact_source_ids_unit_role_and_future_or_self_dependencies(self):
        async with self.source(future=True) as (db, ref):
            batch = self.batch(db, ref)
            records, bindings = self.parent_pair(db, batch)
            future = self.imported(db, batch, 'face-1')[2]
            child_unit = self.prepare(db, batch, 'sheet-0', parent_bindings=bindings)
            child_job = jobs.create_anchor_unit_job(db, batch.batch_id, 'sheet-0', expected_unit_digest=child_unit.input_digest,
                                                  parent_bindings=bindings)
            child = candidates.import_anchor_unit_candidate(db, child_job.job_id, child_job.attempt_id,
                expected_unit_digest=child_unit.input_digest, descriptor=dict(node_id='494', history_key='images', index=0,
                    filename='sheet.png', subfolder='', type='output', mime_type='image/png'), stream=io.BytesIO(png()))
            cases = [[], bindings[::-1], [bindings[0], bindings[0]],
                     [{**bindings[0], 'source_id': 'face-0'}, bindings[1]],
                     [{**bindings[0], 'source_id': ZERO}, bindings[1]],
                     [{**bindings[0], 'unit_key': 'sheet-0'}, bindings[1]],
                     [{**bindings[0], 'source_id': bindings[1]['source_id']}, bindings[1]],
                     [{**bindings[0], 'source_id': future.candidate_id, 'digest': future.digest}, bindings[1]],
                     [{**bindings[0], 'source_id': child.candidate_id, 'digest': child.digest}, bindings[1]],
                     [{**bindings[0], 'digest': ZERO}, bindings[1]]]
            for values in cases:
                with self.subTest(values=values):
                    self.assert_rejected(db, batch, values)

    async def test_standalone_import_and_noncompleted_provider_facts_are_not_success(self):
        async with self.source() as (db, ref):
            batch = self.batch(db, ref)
            records, bindings = self.parent_pair(db, batch, complete=False)
            self.assert_rejected(db, batch, bindings)
            self.complete(db, records[0][1], records[0][0], records[0][2])
            self.assert_rejected(db, batch, bindings)
            self.complete(db, records[1][1], records[1][0], records[1][2])
            self.assertEqual(len(self.resolve(db, batch, bindings)), 2)
            for state in ('authorized', 'dispatching', 'accepted', 'blocked', 'failed'):
                generation = self.batch(db, ref, activation_id=sha256_digest(state.encode()))
                pending, pending_bindings = self.parent_pair(db, generation, complete=False)
                self.complete(db, pending[1][1], pending[1][0], pending[1][2])
                fact = self.complete(db, pending[0][1], pending[0][0], pending[0][2], through=state)
                self.assertEqual(fact.state, state)
                self.assert_rejected(db, generation, pending_bindings)

    async def test_other_activation_and_endpoint_generation_even_same_plan_fail(self):
        async with self.source() as (db, ref):
            batch = self.batch(db, ref)
            records, bindings = self.parent_pair(db, batch)
            other = self.batch(db, ref, activation_id='sha256:' + '9' * 64)
            self.assertEqual(other.prepared_input.source_plan_ref, batch.prepared_input.source_plan_ref)
            self.assert_rejected(db, other, bindings)
            third = self.batch(db, ref, activation_id='sha256:' + '8' * 64,
                               connection=dict(connection='server', endpoint_digest=ZERO))
            self.assert_rejected(db, third, bindings)
            other_records, other_bindings = self.parent_pair(db, other)
            self.assert_rejected(db, batch, other_bindings)
            self.assert_rejected(db, batch, [bindings[0], other_bindings[1]])

    async def test_foreign_project_and_other_saved_source_cannot_be_substituted(self):
        async with self.source() as (db, ref):
            batch = self.batch(db, ref)
            records, bindings = self.parent_pair(db, batch)
        # Same real database/root, separately committed source and parent jobs.
        self.project = str(uuid4())
        async with self.source() as (db, foreign_ref):
            foreign = self.batch(db, foreign_ref)
            _, foreign_bindings = self.parent_pair(db, foreign)
            self.assert_rejected(db, batch, foreign_bindings)
            self.assert_rejected(db, foreign, bindings)
        self.project = ref.project_id
        async with self.source() as (db, next_ref):
            next_batch = self.batch(db, next_ref)
            _, next_bindings = self.parent_pair(db, next_batch)
            self.assert_rejected(db, batch, next_bindings)
            self.assert_rejected(db, next_batch, bindings)

    async def test_missing_unpublished_corrupt_and_tampered_candidate_or_attempt(self):
        async with self.source() as (db, ref):
            batch = self.batch(db, ref)
            records, bindings = self.parent_pair(db, batch)
            for unit, job, candidate in records:
                row = candidates._row(db, candidate.candidate_id)
                db.execute("UPDATE portrait_candidates SET publication_state='reserved' WHERE candidate_id=?", (candidate.candidate_id,))
                self.assert_rejected(db, batch, bindings)
                db.execute("UPDATE portrait_candidates SET publication_state='published' WHERE candidate_id=?", (candidate.candidate_id,))
                altered = json.loads(candidate.metadata_body)
                altered['attempt_id'] = records[1][1].attempt_id if job.kind == 'portrait' else records[0][1].attempt_id
                body = json.dumps(altered, sort_keys=True, separators=(',', ':')).encode()
                db.execute('UPDATE portrait_candidates SET metadata_body=?,metadata_digest=? WHERE candidate_id=?',
                           (body.decode(), sha256_digest(body), candidate.candidate_id))
                self.assert_rejected(db, batch, bindings)
                db.execute('UPDATE portrait_candidates SET metadata_body=?,metadata_digest=? WHERE candidate_id=?',
                           (row[6], row[5], candidate.candidate_id))
                for field, value in (('endpoint_digest', ZERO), ('connection', 'server'), ('project_id', str(uuid4())),
                                     ('unit_input_digest', ZERO), ('unit_key', 'other-unit')):
                    altered = json.loads(candidate.metadata_body)
                    altered[field] = value
                    body = json.dumps(altered, sort_keys=True, separators=(',', ':')).encode()
                    db.execute('UPDATE portrait_candidates SET metadata_body=?,metadata_digest=? WHERE candidate_id=?',
                               (body.decode(), sha256_digest(body), candidate.candidate_id))
                    self.assert_rejected(db, batch, bindings)
                    db.execute('UPDATE portrait_candidates SET metadata_body=?,metadata_digest=? WHERE candidate_id=?',
                               (row[6], row[5], candidate.candidate_id))
                path = self.path(candidate)
                original = path.read_bytes()
                path.unlink()
                self.assert_rejected(db, batch, bindings)
                path.write_bytes(b'corrupt')
                self.assert_rejected(db, batch, bindings)
                path.write_bytes(original)  # Test restores its own fault, never application healing.
                db.execute('UPDATE portrait_candidates SET metadata_body=? WHERE candidate_id=?', ('{}', candidate.candidate_id))
                self.assert_rejected(db, batch, bindings)
                db.execute('UPDATE portrait_candidates SET metadata_body=? WHERE candidate_id=?', (row[6], candidate.candidate_id))

    async def test_committed_source_and_applied_story_authority_revalidated_without_refreeze(self):
        async with self.source() as (db, ref):
            batch = self.batch(db, ref)
            _, bindings = self.parent_pair(db, batch)
            cases = [
                ("UPDATE execution_outcomes SET outcome='failed' WHERE execution_id=?", "UPDATE execution_outcomes SET outcome='completed' WHERE execution_id=?"),
                ("UPDATE execution_work SET status='pending' WHERE execution_id=? AND kind='resume'", "UPDATE execution_work SET status='completed' WHERE execution_id=? AND kind='resume'"),
                ("UPDATE execution_bindings SET binding_revision=2 WHERE execution_id=? AND slot='story'", "UPDATE execution_bindings SET binding_revision=1 WHERE execution_id=? AND slot='story'"),
                ("UPDATE review_requests SET action='revise' WHERE execution_id=?", "UPDATE review_requests SET action='approve' WHERE execution_id=?"),
                ("UPDATE execution_outcomes SET subject_artifact_id=(SELECT artifact_id FROM execution_bindings WHERE execution_id=execution_outcomes.execution_id AND slot='story') WHERE execution_id=?", 'UPDATE execution_outcomes SET subject_artifact_id=? WHERE execution_id=?'),
            ]
            with self.offline(), patch('backend.batch_generation.freeze_batch_input', side_effect=AssertionError('No refreeze')):
                for corrupt, restore in cases:
                    db.execute(corrupt, (ref.execution_id,))
                    self.assert_rejected(db, batch, bindings)
                    db.execute(restore, (ref.artifact_id, ref.execution_id) if restore.count('?') == 2 else (ref.execution_id,))
                db.execute("INSERT INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,status) VALUES (?,?,'cancel',?,?,'pending')",
                    (str(uuid4()), ref.execution_id, 'cancel-after-pin', ZERO))
                work = db.execute("SELECT work_id FROM execution_work WHERE execution_id=? AND kind='cancel'", (ref.execution_id,)).fetchone()[0]
                db.execute("INSERT INTO execution_controls VALUES (?,?,'cancel',?,NULL)", (ref.execution_id, 'cancel-after-pin', work))
                self.assert_rejected(db, batch, bindings)

    async def test_saved_plan_and_story_originals_required_and_caller_transaction_refused(self):
        async with self.source() as (db, ref):
            batch = self.batch(db, ref)
            _, bindings = self.parent_pair(db, batch)
            story_ref = batch.prepared_input.story_approval.story_ref
            for source in (ref, story_ref):
                path = _destination(db, source.project_id, source.artifact_id, source.digest)
                original = path.read_bytes()
                path.write_bytes(b'{}')
                self.assert_rejected(db, batch, bindings)
                path.write_bytes(original)
            db.execute('BEGIN')
            changes = db.total_changes
            with self.assertRaises(ValueError):
                self.resolve(db, batch, bindings)
            self.assertTrue(db.in_transaction)
            self.assertEqual(db.total_changes, changes)
            db.execute('ROLLBACK')

    async def test_database_root_cannot_resolve_another_roots_records_without_its_originals(self):
        async with self.source() as (db, ref):
            batch = self.batch(db, ref)
            _, bindings = self.parent_pair(db, batch)
            with database.open_database(self.root.parent / 'other-data') as other:
                db.backup(other)  # Isolated copied SQL only, never source/production writes.
                self.assert_rejected(other, batch, bindings)

    async def test_verified_original_read_rejects_mutation_or_identical_inode_replacement(self):
        async with self.source() as (db, ref):
            batch = self.batch(db, ref)
            records, _ = self.parent_pair(db, batch)
            unit, _, candidate = records[0]
            path = self.path(candidate)
            original = path.read_bytes()
            verify = candidates._verify
            for replacement in (b'corrupt', original):
                def changed(*args, **kwargs):
                    result = verify(*args, **kwargs)
                    path.unlink()
                    path.write_bytes(replacement)
                    return result
                with patch.object(candidates, '_verify', side_effect=changed), self.assertRaises(ValueError):
                    candidates.read_anchor_unit_candidate_original(db, candidate.candidate_id, expected_unit_digest=unit.input_digest)
                path.write_bytes(original)
            before = db.total_changes
            record, body = candidates.read_anchor_unit_candidate_original(db, candidate.candidate_id, expected_unit_digest=unit.input_digest)
            self.assertEqual((record, body), (candidate, original))
            self.assertEqual(db.total_changes, before)
