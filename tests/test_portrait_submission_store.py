"""One offline authorized portrait dispatch; never a provider/worker test."""

import importlib.util
from contextlib import contextmanager
import io
import json
import sqlite3
import subprocess
import sys
from typing import Any
import unittest
from unittest.mock import patch

from backend import batch_store, database, portrait_candidate_store, render_job_store
from backend.domain import canonical_json, sha256_digest
from tests import test_batch_store as pins
from tests import test_story_wardrobe_api as fixtures
from tests.test_portrait_candidate_store import png


ZERO = 'sha256:' + '0' * 64
NOW = 1_000_000


class PortraitSubmissionTests(fixtures.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    committed: Any = pins.BatchStoreTests.committed
    pin: Any = pins.BatchStoreTests.pin
    context: Any = pins.BatchStoreTests.context
    parents: Any = pins.BatchStoreTests.parents
    prepare: Any = pins.BatchStoreTests.prepare
    path: Any = pins.BatchStoreTests.path
    offline: Any = pins.BatchStoreTests.offline

    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('backend.portrait_submission_store'),
                             'Durable authorized portrait submission storage is missing')
        from backend import portrait_submission_store
        self.submissions = portrait_submission_store
        self.store = batch_store
        self.profile = pins.production_catalog()['image_only']['profiles'][0]['pin']

    def job(self, db, ref):
        batch = self.pin(db, ref, image_size={'width': 512, 'height': 512})
        unit = self.prepare(db, batch, batch.prepared_input.ordered_units[0].unit_key)
        job = render_job_store.create_portrait_job(db, batch.batch_id, unit.unit_key,
                                                  expected_unit_digest=unit.input_digest)
        return job, batch, unit

    def preview(self, db, job, unit):
        return self.submissions.preview_portrait_submission(db, job.job_id, expected_unit_digest=unit.input_digest)

    def authorize(self, db, preview, **changes):
        args: dict[str, Any] = dict(expected_unit_digest=preview.unit_input_digest, expected_wire_digest=preview.wire_digest,
                    accepted_at_ms=NOW)
        args.update(changes)
        return self.submissions.authorize_portrait_submission(db, preview.job_id, **args)

    def args(self, record, **changes):
        args: dict[str, Any] = dict(expected_unit_digest=record.preview.unit_input_digest,
                    expected_wire_digest=record.preview.wire_digest, expected_revision=record.revision)
        args.update(changes)
        return args

    def read(self, db, record):
        return self.submissions.read_portrait_submission(db, record.preview.job_id,
            expected_unit_digest=record.preview.unit_input_digest, expected_wire_digest=record.preview.wire_digest)

    def claim(self, db, record, **changes):
        return self.submissions.claim_portrait_dispatch(db, record.preview.job_id,
                                                       now_ms=NOW + 1, **self.args(record, **changes))

    def evidence(self, preview, kind='prompt_response', prompt_id='prompt-1', **changes):
        value = dict(kind=kind, digest=sha256_digest(kind.encode()), prompt_id=prompt_id,
                     wire_digest=preview.wire_digest, endpoint_digest=preview.endpoint_digest)
        value.update(changes)
        return value

    def accept(self, db, record, **changes):
        args: dict[str, Any] = dict(prompt_id='prompt-1', evidence=self.evidence(record.preview))
        args.update(changes)
        return self.submissions.record_portrait_acceptance(db, record.preview.job_id,
                                                         **self.args(record), **args)

    def block(self, db, record, reason: Any = 'acceptance_unknown'):
        return self.submissions.block_portrait_submission(db, record.preview.job_id,
                                                         reason=reason, **self.args(record))

    def candidate(self, db, job, unit):
        return portrait_candidate_store.import_portrait_candidate(db, job.job_id, job.attempt_id,
            expected_unit_digest=unit.input_digest, stream=io.BytesIO(png()), descriptor=dict(
                node_id='865', history_key='images', index=0, filename='portrait.png', subfolder='',
                type='output', mime_type='image/png'))

    async def test_preview_is_exact_offline_non_authorizing_native_envelope_and_reopens(self):
        async with self.committed() as (db, ref):
            job, batch, unit = self.job(db, ref)
            old = {t: db.execute(f'SELECT rowid,* FROM {t}').fetchall() for t in (
                'render_jobs', 'render_submission_attempts', 'batch_input_pins', 'batch_unit_input_pins')}
            changes = db.total_changes
            with self.offline():
                preview = self.preview(db, job, unit)
                self.assertEqual(self.preview(db, job, unit), preview)
                with self.assertRaises(LookupError):
                    self.submissions.read_portrait_submission(db, job.job_id,
                        expected_unit_digest=unit.input_digest, expected_wire_digest=preview.wire_digest)
                with self.assertRaises(LookupError):
                    self.submissions.claim_portrait_dispatch(db, job.job_id, expected_revision=0,
                        expected_unit_digest=unit.input_digest, expected_wire_digest=preview.wire_digest, now_ms=NOW)
            self.assertEqual(db.total_changes, changes)
            body = json.loads(preview.wire_body)
            image = json.loads(job.prepared_input.image_pin_json)
            self.assertEqual(set(body), {'prompt', 'client_id', 'extra_data'})
            self.assertEqual(body['prompt'], image['graph'])
            self.assertEqual(body['client_id'], 'kinodel-' + job.attempt_id[7:])
            self.assertEqual(body['extra_data'], {'kinodel_portrait_v1': dict(job_id=job.job_id,
                attempt_id=job.attempt_id, input_digest=unit.input_digest, intent_digest=job.intent_digest,
                graph_digest='sha256:' + image['graph_sha256'])})
            self.assertEqual(preview.wire_digest, sha256_digest(preview.wire_body))
            self.assertEqual(preview.source_plan_ref, ref)
            self.assertEqual(preview.unit_input_uri, unit.uri)
            self.assertEqual(preview.endpoint_digest, batch.prepared_input.connection.endpoint_digest)
            self.assertEqual(preview.connection_digest, sha256_digest(canonical_json(batch.prepared_input.connection)))
            self.assertNotIn(preview.wire_digest, preview.wire_body.decode())
            self.assertEqual({t: db.execute(f'SELECT rowid,* FROM {t}').fetchall() for t in old}, old)
        with database.open_database(self.root) as db, self.offline():
            self.assertEqual(self.preview(db, job, unit), preview)

    async def test_explicit_authorization_fixed_budget_exact_replay_and_selector_conflicts(self):
        async with self.committed() as (db, ref):
            job, _, unit = self.job(db, ref)
            preview = self.preview(db, job, unit)
            for changes in (dict(expected_wire_digest=ZERO), dict(expected_unit_digest=ZERO),
                            dict(job_timeout_ms=0), dict(job_timeout_ms=3_600_001),
                            dict(accepted_at_ms=True), dict(job_timeout_ms=True)):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    self.authorize(db, preview, **changes)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_submissions').fetchone(), (0,))
            with self.offline():
                authorized = self.authorize(db, preview)
                self.assertEqual((authorized.state, authorized.revision), ('authorized', 0))
                self.assertEqual((authorized.accepted_at_ms, authorized.deadline_ms), (NOW, NOW + 900_000))
                self.assertIsNone(authorized.dispatched_at_ms)
                self.assertEqual(self.authorize(db, preview), authorized)
                for changes in (dict(accepted_at_ms=NOW + 1), dict(job_timeout_ms=1000)):
                    with self.assertRaises(ValueError):
                        self.authorize(db, preview, **changes)
        with database.open_database(self.root) as db, self.offline():
            self.assertEqual(self.read(db, authorized), authorized)

    async def test_claim_commits_potential_send_once_cas_and_does_not_renew_authorization(self):
        async with self.committed() as (db, ref):
            job, _, unit = self.job(db, ref)
            preview = self.preview(db, job, unit)
            authorized = self.authorize(db, preview)
            for revision in (True, -1, 1):
                with self.assertRaises(ValueError):
                    self.claim(db, authorized, expected_revision=revision)
            for now in (NOW - 1, authorized.deadline_ms, True):
                with self.assertRaises(ValueError):
                    self.submissions.claim_portrait_dispatch(db, job.job_id, now_ms=now, **self.args(authorized))
            dispatched = self.claim(db, authorized)
            self.assertEqual((dispatched.state, dispatched.revision, dispatched.dispatched_at_ms),
                             ('dispatching', 1, NOW + 1))
            for record in (authorized, dispatched):
                with self.assertRaises(ValueError):
                    self.claim(db, record)
            self.assertEqual(self.authorize(db, preview), dispatched)
        with database.open_database(self.root) as db, self.offline():
            self.assertEqual(self.read(db, dispatched), dispatched)
            with self.assertRaises(ValueError):
                self.claim(db, dispatched)

    async def test_prompt_id_commit_survives_following_contract_error_and_exact_replay(self):
        async with self.committed() as (db, ref):
            job, _, unit = self.job(db, ref)
            dispatch = self.claim(db, self.authorize(db, self.preview(db, job, unit)))
            accepted = self.accept(db, dispatch)
            self.assertEqual((accepted.state, accepted.prompt_id, accepted.revision), ('accepted', 'prompt-1', 2))
            self.assertEqual(self.accept(db, dispatch), accepted)
            with self.assertRaises(ValueError):
                self.accept(db, dispatch, prompt_id='other', evidence=self.evidence(dispatch.preview, prompt_id='other'))
            blocked = self.block(db, accepted, 'contract_error')
            self.assertEqual(blocked.prompt_id, 'prompt-1')
            self.assertEqual(blocked.acceptance_evidence, accepted.acceptance_evidence)
            with self.assertRaises(ValueError):
                self.accept(db, dispatch)
        with database.open_database(self.root) as db, self.offline():
            self.assertEqual(self.read(db, blocked), blocked)

    async def test_explicit_contract_revalidation_guard_cas_same_id_history_and_exact_replay(self):
        async with self.committed() as (db, ref):
            job, _, unit = self.job(db, ref)
            accepted = self.accept(db, self.claim(db, self.authorize(db, self.preview(db, job, unit))))
            blocked = self.block(db, accepted, 'contract_error')
            for proof, prompt, flag in ((self.evidence(blocked.preview, 'queue'), 'prompt-1', True),
                (self.evidence(blocked.preview, 'history', prompt_id='other'), 'other', True),
                (self.evidence(blocked.preview, 'history'), 'prompt-1', 1)):
                with self.assertRaises(ValueError):
                    self.accept(db, blocked, prompt_id=prompt, evidence=proof, revalidate_contract=flag)
                self.assertEqual(self.read(db, blocked), blocked)
            proof = self.evidence(blocked.preview, 'history')
            with self.assertRaises(ValueError):
                self.submissions.record_portrait_acceptance(db, job.job_id, **self.args(blocked, expected_revision=2),
                    prompt_id='prompt-1', evidence=proof, revalidate_contract=True)
            result = self.accept(db, blocked, evidence=proof, revalidate_contract=True)
            self.assertEqual((result.state, result.reason, result.prompt_id), ('accepted', None, 'prompt-1'))
            self.assertEqual(result.acceptance_evidence, accepted.acceptance_evidence)
            self.assertEqual(self.accept(db, blocked, evidence=proof, revalidate_contract=True), result)
            with self.assertRaises(ValueError):
                self.claim(db, result)

    async def test_one_output_recovery_grant_exact_replay_reopen_cas_and_never_renews(self):
        async with self.committed() as (db, ref):
            job, _, unit = self.job(db, ref)
            accepted = self.accept(db, self.claim(db, self.authorize(db, self.preview(db, job, unit))))
            blocked = self.block(db, accepted, 'contract_error')
            before = self.submissions._row(db, job.job_id)
            self.assertNotIn('output_recovery_', before[4])
            grant = getattr(self.submissions, 'authorize_portrait_output_recovery', None)
            self.assertIsNotNone(grant, 'Durable output-only recovery grant is missing')
            now = blocked.deadline_ms + 1
            for changes in (dict(expected_revision=blocked.revision - 1), dict(timeout_ms=300_001),
                            dict(timeout_ms=True), dict(now_ms=blocked.deadline_ms - 1)):
                args = dict(**self.args(blocked), now_ms=now)
                args.update(changes)
                with self.assertRaises(ValueError):
                    grant(db, job.job_id, **args)
                self.assertEqual(self.submissions._row(db, job.job_id), before)
            granted = grant(db, job.job_id, **self.args(blocked), now_ms=now)
            self.assertEqual((granted.output_recovery_authorized_at_ms, granted.output_recovery_deadline_ms), (now, now + 300_000))
            self.assertEqual(granted.revision, blocked.revision + 1)
            self.assertEqual((granted.deadline_ms, granted.accepted_at_ms, granted.dispatched_at_ms, granted.acceptance_evidence),
                             (blocked.deadline_ms, blocked.accepted_at_ms, blocked.dispatched_at_ms, blocked.acceptance_evidence))
            self.assertEqual(granted.preview.wire_body, blocked.preview.wire_body)
            self.assertEqual(grant(db, job.job_id, **self.args(blocked), now_ms=now), granted)
            self.assertEqual(grant(db, job.job_id, **self.args(granted), now_ms=now), granted)
            for later in (now + 1, now + 300_001):
                with self.assertRaises(ValueError):
                    grant(db, job.job_id, **self.args(granted), now_ms=later)
            with self.assertRaises(ValueError):
                self.claim(db, granted)
        with database.open_database(self.root) as db, self.offline():
            self.assertEqual(self.read(db, granted), granted)

    async def test_output_recovery_grant_refuses_unsent_unknown_terminal_and_other_block_reasons(self):
        async with self.committed() as (db, ref):
            job, _, unit = self.job(db, ref)
            authorized = self.authorize(db, self.preview(db, job, unit))
            grant = getattr(self.submissions, 'authorize_portrait_output_recovery', None)
            self.assertIsNotNone(grant, 'Durable output-only recovery grant is missing')
            for record in (authorized, self.claim(db, authorized)):
                with self.assertRaises(ValueError):
                    grant(db, job.job_id, **self.args(record), now_ms=authorized.deadline_ms + 1)
            dispatched = self.read(db, authorized)
            unknown = self.block(db, dispatched)
            with self.assertRaises(ValueError):
                grant(db, job.job_id, **self.args(unknown), now_ms=authorized.deadline_ms + 1)
            accepted = self.accept(db, unknown, evidence=self.evidence(authorized.preview, 'history'))
            invalid = self.block(db, accepted, 'output_invalid')
            with self.assertRaises(ValueError):
                grant(db, job.job_id, **self.args(invalid), now_ms=authorized.deadline_ms + 1)
            failed = self.submissions.fail_portrait_submission(db, job.job_id, **self.args(invalid), reason='output_invalid')
            with self.assertRaises(ValueError):
                grant(db, job.job_id, **self.args(failed), now_ms=authorized.deadline_ms + 1)

    async def test_old_canonical_rows_omit_only_recovery_pair_and_tampered_grants_reject(self):
        async with self.committed() as (db, ref):
            job, _, unit = self.job(db, ref)
            accepted = self.accept(db, self.claim(db, self.authorize(db, self.preview(db, job, unit))))
            original_row = self.submissions._row(db, job.job_id)
            old_body = json.loads(original_row[4])
            self.assertNotIn('output_recovery_deadline_ms', old_body)
            self.assertNotIn('output_recovery_authorized_at_ms', old_body)
            self.assertIn('candidate_id', old_body)
            self.assertIsNone(old_body['candidate_id'])
            self.assertEqual(self.read(db, accepted), accepted)
            grant = getattr(self.submissions, 'authorize_portrait_output_recovery', None)
            self.assertIsNotNone(grant, 'Durable output-only recovery grant is missing')
            now = accepted.deadline_ms + 1
            granted = grant(db, job.job_id, **self.args(accepted), now_ms=now)
            row = self.submissions._row(db, job.job_id)
            for changes in ({'output_recovery_deadline_ms': now + 300_001},
                            {'output_recovery_authorized_at_ms': None},
                            {'output_recovery_authorized_at_ms': True}):
                body = {**json.loads(row[4]), **changes}
                encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                db.execute('UPDATE portrait_submissions SET submission_body=?,submission_digest=?',
                           (encoded.decode(), sha256_digest(encoded)))
                with self.assertRaises(ValueError):
                    self.read(db, granted)
                db.execute('UPDATE portrait_submissions SET submission_body=?,submission_digest=?', (row[4], row[3]))

    async def test_unknown_acceptance_blocks_no_repost_exact_evidence_can_recover(self):
        async with self.committed() as (db, ref):
            job, _, unit = self.job(db, ref)
            preview = self.preview(db, job, unit)
            blocked = self.block(db, self.claim(db, self.authorize(db, preview)))
            self.assertIsNone(blocked.prompt_id)
            self.assertEqual(self.authorize(db, preview), blocked)
            with self.assertRaises(ValueError):
                self.claim(db, blocked)
            for evidence in (self.evidence(preview), self.evidence(preview, 'queue', wire_digest=ZERO),
                             self.evidence(preview, 'history', endpoint_digest=ZERO),
                             self.evidence(preview, 'queue', prompt_id='other'),
                             {**self.evidence(preview, 'queue'), 'raw_response': 'secret'}):
                with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                    self.accept(db, blocked, evidence=evidence)
            recovered = self.accept(db, blocked, evidence=self.evidence(preview, 'queue'))
            self.assertEqual((recovered.state, recovered.prompt_id), ('accepted', 'prompt-1'))
            self.assertEqual(recovered.reason, 'acceptance_unknown')
            blocked_again = self.block(db, recovered, 'history_unavailable')
            history = self.evidence(preview, 'history')
            recovered_again = self.accept(db, blocked_again, evidence=history)
            self.assertEqual(recovered_again.acceptance_evidence, recovered.acceptance_evidence)
            assert recovered_again.evidence is not None
            self.assertEqual(recovered_again.evidence.kind, 'history')

    async def test_terminal_complete_requires_history_exact_candidate_and_never_rewrites(self):
        async with self.committed() as (db, ref):
            job, _, unit = self.job(db, ref)
            authorized = self.authorize(db, self.preview(db, job, unit))
            candidate = self.candidate(db, job, unit)
            saved_candidate = db.execute('SELECT rowid,* FROM portrait_candidates').fetchall()
            accepted = self.accept(db, self.claim(db, authorized))
            history = self.evidence(accepted.preview, 'history')
            complete = self.submissions.complete_portrait_submission
            for changes in (dict(evidence=self.evidence(accepted.preview)), dict(candidate_id=ZERO)):
                args: dict[str, Any] = dict(evidence=history, candidate_id=candidate.candidate_id)
                args.update(changes)
                with self.assertRaises((ValueError, LookupError)):
                    complete(db, job.job_id, **self.args(accepted), **args)
            completed = complete(db, job.job_id, **self.args(accepted), evidence=history, candidate_id=candidate.candidate_id)
            self.assertEqual((completed.state, completed.candidate_id), ('completed', candidate.candidate_id))
            with self.assertRaises(ValueError):
                self.submissions.authorize_portrait_output_recovery(db, job.job_id, **self.args(completed),
                    now_ms=completed.deadline_ms + 1)
            self.assertEqual(complete(db, job.job_id, **self.args(accepted), evidence=history,
                                     candidate_id=candidate.candidate_id), completed)
            for action in (lambda: self.claim(db, completed), lambda: self.block(db, completed, 'contract_error'),
                           lambda: self.accept(db, completed), lambda: self.submissions.fail_portrait_submission(
                               db, job.job_id, **self.args(completed), reason='provider_failed', evidence=history)):
                with self.assertRaises(ValueError):
                    action()
            self.assertEqual(db.execute('SELECT rowid,* FROM portrait_candidates').fetchall(), saved_candidate)
        with database.open_database(self.root) as db, self.offline():
            self.assertEqual(self.read(db, completed), completed)

    async def test_terminal_failed_preserves_acceptance_and_cannot_recover_or_dispatch(self):
        async with self.committed() as (db, ref):
            job, _, unit = self.job(db, ref)
            accepted = self.accept(db, self.claim(db, self.authorize(db, self.preview(db, job, unit))))
            fail = self.submissions.fail_portrait_submission
            history = self.evidence(accepted.preview, 'history')
            failed = fail(db, job.job_id, **self.args(accepted), reason='provider_failed', evidence=history)
            self.assertEqual(failed.prompt_id, accepted.prompt_id)
            self.assertEqual(failed.acceptance_evidence, accepted.acceptance_evidence)
            self.assertEqual(fail(db, job.job_id, **self.args(accepted), reason='provider_failed', evidence=history), failed)
            for action in (lambda: self.claim(db, failed), lambda: self.accept(db, failed, evidence=history),
                           lambda: self.block(db, failed)):
                with self.assertRaises(ValueError):
                    action()

    async def test_tampered_sql_wire_lifecycle_and_pins_fail_without_healing(self):
        async with self.committed() as (db, ref):
            job, _, unit = self.job(db, ref)
            preview = self.preview(db, job, unit)
            authorized = self.authorize(db, preview)
            row = db.execute('SELECT submission_body,submission_digest FROM portrait_submissions').fetchone()
            for column, changed, original in (('wire_digest', ZERO, preview.wire_digest),
                ('submission_body', '{}', row[0]), ('submission_digest', ZERO, row[1])):
                db.execute(f'UPDATE portrait_submissions SET {column}=?', (changed,))
                changes = db.total_changes
                for action in (lambda: self.preview(db, job, unit), lambda: self.authorize(db, preview),
                               lambda: self.read(db, authorized), lambda: self.claim(db, authorized)):
                    with self.subTest(column=column), self.assertRaises(ValueError):
                        action()
                self.assertEqual(db.total_changes, changes)
                db.execute(f'UPDATE portrait_submissions SET {column}=?', (original,))
            # Even a low-level writer bypassing CHECK constraints cannot replay invalid revisions.
            db.execute('PRAGMA ignore_check_constraints=ON')
            db.execute('UPDATE portrait_submissions SET revision=99')
            with self.assertRaises(ValueError):
                self.read(db, authorized)
            db.execute('UPDATE portrait_submissions SET revision=0')
            db.execute('PRAGMA ignore_check_constraints=OFF')
            # A rehashed SQL envelope still conflicts with the independently frozen graph.
            body = json.loads(row[0])
            body['preview']['wire_body_json'] = '{}'
            body['preview']['wire_digest'] = sha256_digest(b'{}')
            encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
            db.execute('UPDATE portrait_submissions SET submission_body=?,submission_digest=?,wire_digest=?',
                       (encoded.decode(), sha256_digest(encoded), sha256_digest(b'{}')))
            with self.assertRaises(ValueError):
                self.preview(db, job, unit)
            db.execute('UPDATE portrait_submissions SET submission_body=?,submission_digest=?,wire_digest=?', (*row, preview.wire_digest))
            path = self.path(unit)
            original = path.read_bytes()
            path.write_bytes(b'broken')
            for action in (lambda: self.read(db, authorized), lambda: self.authorize(db, preview)):
                with self.assertRaises(ValueError):
                    action()
            self.assertEqual(path.read_bytes(), b'broken')
            path.write_bytes(original)
            self.assertEqual(self.read(db, authorized), authorized)

    async def test_caller_transaction_and_failed_sql_commit_do_not_claim(self):
        async with self.committed() as (db, ref):
            job, _, unit = self.job(db, ref)
            preview = self.preview(db, job, unit)
            authorized = self.authorize(db, preview)
            db.execute('BEGIN IMMEDIATE')
            for action in (lambda: self.preview(db, job, unit), lambda: self.authorize(db, preview),
                           lambda: self.read(db, authorized), lambda: self.claim(db, authorized)):
                with self.assertRaises(ValueError):
                    action()
            self.assertTrue(db.in_transaction)
            db.execute('ROLLBACK')
            db.execute("CREATE TEMP TRIGGER fail_claim BEFORE UPDATE ON portrait_submissions "
                       "BEGIN SELECT RAISE(ABORT,'injected failure'); END")
            with self.assertRaises(sqlite3.IntegrityError):
                self.claim(db, authorized)
            self.assertFalse(db.in_transaction)
            self.assertEqual(self.read(db, authorized), authorized)

    async def test_unknown_sent_acceptance_cannot_be_made_terminal_by_local_failure(self):
        async with self.committed() as (db, ref):
            job, _, unit = self.job(db, ref)
            dispatched = self.claim(db, self.authorize(db, self.preview(db, job, unit)))
            # Deadline/transport/output failures do not prove a submitted prompt was rejected.
            for reason in ('deadline_exceeded', 'contract_error', 'output_invalid'):
                with self.subTest(reason=reason), self.assertRaises(ValueError):
                    self.submissions.fail_portrait_submission(db, job.job_id, **self.args(dispatched), reason=reason)
                self.assertEqual(self.read(db, dispatched), dispatched)
            blocked = self.block(db, dispatched)
            with self.assertRaises(ValueError):
                self.submissions.fail_portrait_submission(db, job.job_id, **self.args(blocked), reason='deadline_exceeded')
            self.assertEqual(self.read(db, blocked), blocked)

    async def test_cas_rechecks_submission_and_input_rows_at_transaction_boundary(self):
        async with self.committed() as (db, ref):
            job, _, unit = self.job(db, ref)
            authorized = self.authorize(db, self.preview(db, job, unit))
            original = self.submissions._transaction
            for sql, changed, restore in (
                ('UPDATE portrait_submissions SET submission_digest=?', ZERO,
                 db.execute('SELECT submission_digest FROM portrait_submissions').fetchone()[0]),
                ('UPDATE render_submission_attempts SET intent_digest=?', ZERO, job.intent_digest)):
                @contextmanager
                def drift(connection):
                    connection.execute(sql, (changed,))
                    with original(connection):
                        yield
                with patch.object(self.submissions, '_transaction', drift), self.assertRaises(ValueError):
                    self.claim(db, authorized)
                self.assertFalse(db.in_transaction)
                self.assertEqual(db.execute('SELECT state,revision FROM portrait_submissions').fetchone(), ('authorized', 0))
                db.execute(sql, (restore,))
            self.assertEqual(self.read(db, authorized), authorized)

    async def test_true_child_death_before_after_dispatch_and_acceptance_commit(self):
        async with self.committed() as (db, ref):
            job, _, unit = self.job(db, ref)
            preview = self.preview(db, job, unit)
            authorized = self.authorize(db, preview)
        script = '''
import os, sys
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
from backend import database, portrait_submission_store as store
from backend.domain import sha256_digest
root, job, unit_digest, wire_digest, operation, phase = sys.argv[1:]
original = store._transaction
@contextmanager
def crash(db):
    with original(db):
        yield
        if phase == 'before': os._exit(81)
    os._exit(82)
with database.open_database(Path(root)) as db:
    record = store.read_portrait_submission(db, job, expected_unit_digest=unit_digest, expected_wire_digest=wire_digest)
    args = dict(expected_unit_digest=unit_digest, expected_wire_digest=wire_digest, expected_revision=record.revision)
    with patch.object(store, '_transaction', crash):
        if operation == 'dispatch':
            store.claim_portrait_dispatch(db, job, now_ms=1000001, **args)
        else:
            store.record_portrait_acceptance(db, job, prompt_id='prompt-1', **args, evidence=dict(
                kind='prompt_response', digest=sha256_digest(b'prompt_response'), prompt_id='prompt-1',
                wire_digest=wire_digest, endpoint_digest=record.preview.endpoint_digest))
raise AssertionError('Missing crash point')
'''
        for operation, phase, state, prompt in (('dispatch', 'before', 'authorized', None),
                ('dispatch', 'after', 'dispatching', None), ('accept', 'before', 'dispatching', None),
                ('accept', 'after', 'accepted', 'prompt-1')):
            child = subprocess.run([sys.executable, '-B', '-c', script, str(self.root), job.job_id,
                unit.input_digest, preview.wire_digest, operation, phase], capture_output=True, text=True, timeout=60)
            self.assertEqual(child.returncode, 81 if phase == 'before' else 82, child.stdout + child.stderr)
            with database.open_database(self.root) as db, self.offline():
                record = self.read(db, authorized)
                self.assertEqual((record.state, record.prompt_id), (state, prompt))
                self.assertEqual(self.authorize(db, preview), record)
                if state != 'authorized':
                    with self.assertRaises(ValueError):
                        self.claim(db, record)


if __name__ == '__main__':
    unittest.main()
