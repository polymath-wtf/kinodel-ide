"""6B.1 bounded anchor records; no live provider, uploads or creative approval."""

import io
import json
import os
from types import SimpleNamespace
from typing import Any
import unittest
from unittest.mock import patch

import httpx

from backend import batch_store, database, portrait_candidate_store as candidates
from backend import portrait_submission_store as submissions, portrait_worker as worker, render_job_store as jobs
from backend.config import resolve_comfyui_connection
from backend.domain import ArtifactRef, canonical_json, sha256_digest
from tests import test_batch_store as pins, test_story_wardrobe_api as fixtures
from tests.test_portrait_candidate_store import png
from tests.test_portrait_worker import ENDPOINT, NOW, ZERO, history, response


class AnchorUnitLifecycleTests(fixtures.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    committed: Any = pins.BatchStoreTests.committed
    pin: Any = pins.BatchStoreTests.pin
    context: Any = pins.BatchStoreTests.context
    parents: Any = pins.BatchStoreTests.parents
    prepare: Any = pins.BatchStoreTests.prepare
    path: Any = pins.BatchStoreTests.path
    offline: Any = pins.BatchStoreTests.offline

    def setUp(self):
        super().setUp()
        self.assertTrue(hasattr(jobs, 'create_anchor_unit_job'), 'Bounded anchor-unit API is missing')
        self.store = batch_store
        self.profile = pins.production_catalog()['image_only']['profiles'][0]['pin']
        env = patch.dict(os.environ, {'COMFYUI_LOCAL_ENDPOINT': ENDPOINT, 'COMFYUI_AUTH_TOKEN': 'private-token'})
        env.start()
        self.addCleanup(env.stop)
        self.calls = []

    def batch(self, db, ref):
        return self.pin(db, ref, image_size={'width': 512, 'height': 512}, connection={
            'connection': 'local', 'endpoint_digest': 'sha256:' + resolve_comfyui_connection('local').endpoint_digest})

    def unit_job(self, db, batch, index):
        key = batch.prepared_input.ordered_units[index].unit_key
        unit = self.prepare(db, batch, key)
        job = jobs.create_anchor_unit_job(db, batch.batch_id, key, expected_unit_digest=unit.input_digest,
                                         parent_bindings=unit.prepared_input.parent_bindings)
        return unit, job

    def descriptor(self, node='865'):
        return dict(node_id=node, history_key='images', index=0, filename='original.png', subfolder='',
                    type='output', mime_type='image/png')

    def args(self, record):
        return dict(expected_unit_digest=record.preview.unit_input_digest,
                    expected_wire_digest=record.preview.wire_digest, expected_revision=record.revision)

    def authorize(self, db, job, digest):
        preview = submissions.preview_anchor_unit_submission(db, job.job_id, expected_unit_digest=digest)
        return submissions.authorize_anchor_unit_submission(db, job.job_id, expected_unit_digest=digest,
            expected_wire_digest=preview.wire_digest, accepted_at_ms=NOW)

    def fact_calls(self, db, job_id, args, prefix):
        proof = dict(kind='history', prompt_id='prompt-1', digest=ZERO,
                     wire_digest=args['expected_wire_digest'], endpoint_digest=ZERO)
        calls = [
            ('read', 'submission', {}),
            ('record', 'acceptance', dict(expected_revision=0, prompt_id='prompt-1', evidence=proof)),
            ('block', 'submission', dict(expected_revision=0, reason='contract_error')),
            ('fail', 'submission', dict(expected_revision=0, reason='deadline_exceeded')),
            ('complete', 'submission', dict(expected_revision=0, candidate_id=ZERO, evidence=proof)),
            ('authorize', 'output_recovery', dict(expected_revision=0, now_ms=NOW + 900_000)),
        ]
        for action, suffix, changes in calls:
            api = getattr(submissions, f'{action}_{prefix}_{suffix}')
            with self.subTest(api=api.__name__), self.assertRaises(ValueError):
                api(db, job_id, **args, **changes)

    async def tick(self, db, record, *, lost=False, empty=False, now=NOW + 2, histories=None):
        def handle(request):
            self.assertFalse(db.in_transaction)
            self.calls.append(request)
            if request.method == 'POST':
                if lost:
                    raise httpx.ReadError('lost response')
                return response(dict(prompt_id='prompt-1', number=1, node_errors={}))
            if request.url.path.endswith('/queue'):
                return response(dict(queue_running=[], queue_pending=[]))
            if '/history' in request.url.path:
                return response(histories if histories is not None else ({} if empty else history(record.preview)))
            if request.url.path.endswith('/view'):
                return response(png(), raw=True)
            self.fail('Unexpected route')
        return await worker.tick_anchor_unit_job(db, record.preview.job_id, **self.args(record),
            clock_ms=lambda: now, transport=httpx.MockTransport(handle))

    async def test_exact_three_roles_reopen_parents_and_portrait_restrictions(self):
        async with self.committed() as (db, ref):
            batch = self.batch(db, ref)
            records = [self.unit_job(db, batch, i) for i in range(3)]
            originals = []
            for (unit, job), kind, node in zip(records, ('portrait', 'background', 'sheet'), ('865', '865', '494'), strict=True):
                self.assertEqual(json.loads(unit.prepared_input.image_pin_json)['kind'], kind)
                if kind != 'portrait':
                    self.assertEqual(json.loads(job.intent_body)['schema_id'], 'comfyui_anchor_unit_submission_intent')
                    self.assertEqual(json.loads(job.intent_body)['kind'], kind)
                    with self.assertRaises(ValueError):
                        jobs.create_portrait_job(db, batch.batch_id, unit.unit_key, expected_unit_digest=unit.input_digest)
                    with self.assertRaises(ValueError):
                        jobs.read_portrait_job(db, job.job_id, expected_unit_digest=unit.input_digest)
                    with self.assertRaises(ValueError):
                        candidates.import_portrait_candidate(db, job.job_id, job.attempt_id,
                            expected_unit_digest=unit.input_digest, descriptor=self.descriptor(node), stream=io.BytesIO(png()))
                candidate = candidates.import_anchor_unit_candidate(db, job.job_id, job.attempt_id,
                    expected_unit_digest=unit.input_digest, descriptor=self.descriptor(node), stream=io.BytesIO(png()))
                originals.append(candidate)
                self.assertEqual(self.path(candidate).read_bytes(), png())
                if kind != 'portrait':
                    metadata = json.loads(candidate.metadata_body)
                    self.assertEqual((metadata['schema_id'], metadata['kind']), ('comfyui_anchor_unit_candidate', kind))
                    with self.assertRaises(ValueError):
                        candidates.read_portrait_candidate(db, candidate.candidate_id, expected_unit_digest=unit.input_digest)
                with self.assertRaises(ValueError):
                    jobs.create_anchor_unit_job(db, batch.batch_id, unit.unit_key, expected_unit_digest=ZERO,
                                               parent_bindings=unit.prepared_input.parent_bindings)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_submission_attempts').fetchone(), (3,))
        with database.open_database(self.root) as db, self.offline():
            changes = db.total_changes
            for (unit, job), candidate in zip(records, originals, strict=True):
                self.assertEqual(jobs.read_anchor_unit_job(db, job.job_id, expected_unit_digest=unit.input_digest), job)
                self.assertEqual(jobs.create_anchor_unit_job(db, batch.batch_id, unit.unit_key,
                    expected_unit_digest=unit.input_digest, parent_bindings=unit.prepared_input.parent_bindings), job)
                self.assertEqual(candidates.read_anchor_unit_candidate(db, candidate.candidate_id,
                    expected_unit_digest=unit.input_digest), candidate)
            sheet, job = records[2]
            for parents in ([], list(reversed(sheet.prepared_input.parent_bindings)),
                            [p.model_copy(update={'digest': ZERO}) for p in sheet.prepared_input.parent_bindings]):
                with self.assertRaises(ValueError):
                    jobs.create_anchor_unit_job(db, batch.batch_id, sheet.unit_key,
                        expected_unit_digest=sheet.input_digest, parent_bindings=parents)
            self.assertEqual(db.total_changes, changes)

    async def test_sheet_creation_requires_explicit_ordered_parent_selector(self):
        async with self.committed() as (db, ref):
            batch = self.batch(db, ref)
            key = batch.prepared_input.ordered_units[2].unit_key
            unit = self.prepare(db, batch, key)
            with self.assertRaises(ValueError):
                jobs.create_anchor_unit_job(db, batch.batch_id, key, expected_unit_digest=unit.input_digest,
                                            parent_bindings=None)  # type: ignore[arg-type] -- trust-boundary negative
            self.assertEqual(db.execute('SELECT COUNT(*) FROM render_jobs').fetchone(), (0,))

    async def test_nonportrait_initial_intent_and_candidate_keep_exact_owned_lineage(self):
        async with self.committed() as (db, ref):
            batch = self.batch(db, ref)
            pairs = [self.unit_job(db, batch, i) for i in (1, 2)]
            for unit, job in pairs:
                node = '494' if job.kind == 'sheet' else '865'
                input_row = batch_store._unit_row(db, batch.batch_id, unit.unit_key)
                db.execute('UPDATE batch_unit_input_pins SET body=? WHERE batch_id=? AND unit_key=?',
                           ('{}', batch.batch_id, unit.unit_key))
                with self.assertRaises(ValueError):
                    jobs.read_anchor_unit_job(db, job.job_id, expected_unit_digest=unit.input_digest)
                db.execute('UPDATE batch_unit_input_pins SET body=? WHERE batch_id=? AND unit_key=?',
                           (input_row[3], batch.batch_id, unit.unit_key))
                with self.assertRaises(ValueError):
                    candidates.import_anchor_unit_candidate(db, job.job_id, pairs[0][1].attempt_id
                        if job.kind == 'sheet' else pairs[1][1].attempt_id,
                        expected_unit_digest=unit.input_digest, descriptor=self.descriptor(node), stream=io.BytesIO(png()))
                row = jobs._row(db, job.job_id)
                db.execute('UPDATE render_submission_attempts SET intent_body=? WHERE job_id=?', ('{}', job.job_id))
                with self.assertRaises(ValueError):
                    jobs.read_anchor_unit_job(db, job.job_id, expected_unit_digest=unit.input_digest)
                db.execute('UPDATE render_submission_attempts SET intent_body=? WHERE job_id=?', (row[6], job.job_id))
                candidate = candidates.import_anchor_unit_candidate(db, job.job_id, job.attempt_id,
                    expected_unit_digest=unit.input_digest, descriptor=self.descriptor(node), stream=io.BytesIO(png()))
                original = candidates._row(db, candidate.candidate_id)
                body = json.loads(candidate.metadata_body)
                body['project_id'] = '11111111-1111-4111-8111-111111111111'
                # Even a self-consistent SQL checksum cannot redirect ownership.
                altered = json.dumps(body, sort_keys=True, separators=(',', ':')).encode()
                db.execute('UPDATE portrait_candidates SET metadata_body=?,metadata_digest=? WHERE candidate_id=?',
                           (altered.decode(), sha256_digest(altered), candidate.candidate_id))
                with self.assertRaises(ValueError):
                    candidates.read_anchor_unit_candidate(db, candidate.candidate_id, expected_unit_digest=unit.input_digest)
                db.execute('UPDATE portrait_candidates SET metadata_body=?,metadata_digest=? WHERE candidate_id=?',
                           (original[6], original[5], candidate.candidate_id))
                with self.assertRaises(ValueError):
                    candidates.import_anchor_unit_candidate(db, job.job_id, job.attempt_id,
                        expected_unit_digest=unit.input_digest, descriptor={**self.descriptor(node), 'filename': 'other.png'},
                        stream=io.BytesIO(png()))

    async def test_nonportrait_reserved_publication_reopens_without_replacement(self):
        async with self.committed() as (db, ref):
            batch = self.batch(db, ref)
            pairs = [self.unit_job(db, batch, i) for i in (1, 2)]
            for unit, job in pairs:
                descriptor = self.descriptor('494' if job.kind == 'sheet' else '865')
                with patch.object(candidates, '_publish', side_effect=OSError('after reservation')):
                    with self.assertRaises(OSError):
                        candidates.import_anchor_unit_candidate(db, job.job_id, job.attempt_id,
                            expected_unit_digest=unit.input_digest, descriptor=descriptor, stream=io.BytesIO(png()))
            before = db.execute('SELECT * FROM portrait_candidates ORDER BY candidate_id').fetchall()
        with database.open_database(self.root) as db, self.offline():
            for unit, job in pairs:
                candidate = candidates.import_anchor_unit_candidate(db, job.job_id, job.attempt_id,
                    expected_unit_digest=unit.input_digest, descriptor=self.descriptor('494' if job.kind == 'sheet' else '865'))
                self.assertEqual(self.path(candidate).read_bytes(), png())
            after = db.execute('SELECT * FROM portrait_candidates ORDER BY candidate_id').fetchall()
            self.assertEqual([row[:-1] for row in before], [row[:-1] for row in after])
            self.assertEqual([row[-1] for row in after], ['published', 'published'])

    async def test_sheet_declared_slot_and_all_native_entrypoints_fail_predispatch(self):
        async with self.committed() as (db, ref):
            unit, job = self.unit_job(db, self.batch(db, ref), 2)
            for descriptor in (self.descriptor(), {**self.descriptor('494'), 'history_key': 'previews'},
                               {**self.descriptor('494'), 'index': 1}):
                with self.assertRaises(ValueError):
                    candidates.import_anchor_unit_candidate(db, job.job_id, job.attempt_id,
                        expected_unit_digest=unit.input_digest, descriptor=descriptor, stream=io.BytesIO(png()))
            args: dict[str, Any] = dict(expected_unit_digest=unit.input_digest, expected_wire_digest=ZERO)
            no_http = httpx.MockTransport(lambda _: self.fail('Sheet HTTP before durable final pins'))
            for api in (submissions.preview_anchor_unit_submission, submissions.preview_portrait_submission):
                with self.assertRaises(ValueError):
                    api(db, job.job_id, expected_unit_digest=unit.input_digest)
            for api in (submissions.authorize_anchor_unit_submission, submissions.authorize_portrait_submission):
                with self.assertRaises(ValueError):
                    api(db, job.job_id, **args, accepted_at_ms=NOW)
            for api in (submissions.claim_anchor_unit_dispatch, submissions.claim_portrait_dispatch):
                with self.assertRaises(ValueError):
                    api(db, job.job_id, **args, expected_revision=0, now_ms=NOW)
            for api in (worker.tick_anchor_unit_job, worker.tick_portrait_job):
                with self.assertRaises(ValueError):
                    await api(db, job.job_id, **args, expected_revision=0, transport=no_http)
            self.fact_calls(db, job.job_id, args, 'anchor_unit')
            self.fact_calls(db, job.job_id, args, 'portrait')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_submissions').fetchone(), (0,))
            # Even a forged/reopened authorization row cannot bypass readiness by
            # calling the claim/worker directly. Gate precedes body parsing and CAS.
            db.execute('INSERT INTO portrait_submissions VALUES (?,?,?,?,?,?,?,?,?)',
                       (job.attempt_id, job.job_id, ZERO, sha256_digest(b'{}'), '{}', 0, 'authorized', None, None))
            poisoned = submissions._row(db, job.job_id)
            with self.assertRaisesRegex(ValueError, 'sheet native submission'):
                submissions.claim_anchor_unit_dispatch(db, job.job_id, **args, expected_revision=0, now_ms=NOW)
            with self.assertRaisesRegex(ValueError, 'sheet native submission'):
                await worker.tick_anchor_unit_job(db, job.job_id, **args, expected_revision=0, transport=no_http)
            self.assertEqual(submissions._row(db, job.job_id), poisoned)
            db.execute('DELETE FROM portrait_submissions WHERE job_id=?', (job.job_id,))
            candidate = candidates.import_anchor_unit_candidate(db, job.job_id, job.attempt_id,
                expected_unit_digest=unit.input_digest, descriptor=self.descriptor('494'), stream=io.BytesIO(png()))
            self.path(candidate).unlink()
            with self.assertRaises((OSError, ValueError)):
                candidates.import_anchor_unit_candidate(db, job.job_id, job.attempt_id,
                    expected_unit_digest=unit.input_digest, descriptor=self.descriptor('494'), stream=io.BytesIO(png()))

    async def test_background_one_post_success_import_and_completed_offline_no_heal(self):
        async with self.committed() as (db, ref):
            unit, job = self.unit_job(db, self.batch(db, ref), 1)
            record = self.authorize(db, job, unit.input_digest)
            wire = json.loads(record.preview.wire_body)
            self.assertEqual(set(wire['extra_data']), {'kinodel_anchor_unit_v1'})
            self.assertEqual(wire['extra_data']['kinodel_anchor_unit_v1']['kind'], 'background')
            for api in (submissions.preview_portrait_submission,):
                with self.assertRaises(ValueError):
                    api(db, job.job_id, expected_unit_digest=unit.input_digest)
            selectors = dict(expected_unit_digest=unit.input_digest, expected_wire_digest=record.preview.wire_digest)
            self.fact_calls(db, job.job_id, selectors, 'portrait')
            portrait_calls: list[tuple[Any, dict[str, Any]]] = [
                (submissions.authorize_portrait_submission, dict(accepted_at_ms=NOW)),
                (submissions.claim_portrait_dispatch, dict(expected_revision=0, now_ms=NOW + 1))]
            for api, changes in portrait_calls:
                with self.assertRaises(ValueError):
                    api(db, job.job_id, **selectors, **changes)
            self.assertEqual(submissions.read_anchor_unit_submission(db, job.job_id, **selectors), record)
            accepted = await self.tick(db, record)
            completed = await self.tick(db, accepted)
            self.assertEqual(completed.state, 'completed')
            assert completed.candidate_id is not None
            self.assertEqual([r.method for r in self.calls], ['POST', 'GET', 'GET', 'GET'])
            self.assertEqual(self.calls[0].content, record.preview.wire_body)
            candidate = candidates.read_anchor_unit_candidate(db, completed.candidate_id, expected_unit_digest=unit.input_digest)
        with database.open_database(self.root) as db, self.offline():
            self.assertEqual(submissions.read_anchor_unit_submission(db, job.job_id,
                expected_unit_digest=unit.input_digest, expected_wire_digest=record.preview.wire_digest), completed)
            self.assertEqual(candidates.read_anchor_unit_candidate(db, candidate.candidate_id,
                expected_unit_digest=unit.input_digest), candidate)
            self.assertEqual(await self.tick(db, completed), completed)
            self.path(candidate).write_bytes(b'corrupt')
            with self.assertRaises((OSError, ValueError)):
                await self.tick(db, completed)
            self.assertEqual(sum(r.method == 'POST' for r in self.calls), 1)

    async def test_background_lost_response_and_reopened_dispatch_never_second_post(self):
        async with self.committed() as (db, ref):
            unit, job = self.unit_job(db, self.batch(db, ref), 1)
            record = self.authorize(db, job, unit.input_digest)
            blocked = await self.tick(db, record, lost=True)
            self.assertEqual((blocked.state, blocked.reason), ('blocked', 'acceptance_unknown'))
        with database.open_database(self.root) as db:
            again = await self.tick(db, blocked, empty=True)
            self.assertEqual(again, blocked)
            completed = await self.tick(db, again)
            self.assertEqual(completed.state, 'completed')
            self.assertEqual(sum(r.method == 'POST' for r in self.calls), 1)

    async def test_background_claim_commits_before_send_and_reopen_not_unsent(self):
        async with self.committed() as (db, ref):
            unit, job = self.unit_job(db, self.batch(db, ref), 1)
            record = self.authorize(db, job, unit.input_digest)
            sent = submissions.claim_anchor_unit_dispatch(db, job.job_id, **self.args(record), now_ms=NOW + 1)
            with self.assertRaises(ValueError):
                submissions.claim_anchor_unit_dispatch(db, job.job_id, **self.args(record), now_ms=NOW + 1)
        with database.open_database(self.root) as db:
            blocked = await self.tick(db, sent, empty=True)
            self.assertEqual((blocked.state, blocked.reason), ('blocked', 'acceptance_unknown'))
            self.assertFalse(any(r.method == 'POST' for r in self.calls))

    async def test_background_fixed_deadline_first_evidence_and_output_only_recovery(self):
        async with self.committed() as (db, ref):
            unit, job = self.unit_job(db, self.batch(db, ref), 1)
            record = self.authorize(db, job, unit.input_digest)
            accepted = await self.tick(db, record)
            blocked = await self.tick(db, accepted, now=record.deadline_ms)
            self.assertEqual((blocked.state, blocked.reason), ('blocked', 'deadline_exceeded'))
            self.assertFalse(any(r.url.path.endswith('/view') for r in self.calls))
            granted = submissions.authorize_anchor_unit_output_recovery(db, job.job_id, **self.args(blocked),
                now_ms=record.deadline_ms + 1, timeout_ms=100)
            with self.assertRaises(ValueError):
                submissions.authorize_anchor_unit_output_recovery(db, job.job_id, **self.args(granted),
                    now_ms=record.deadline_ms + 2, timeout_ms=100)
            completed = await self.tick(db, granted, now=record.deadline_ms + 2)
            self.assertEqual(completed.state, 'completed')
            self.assertEqual((completed.accepted_at_ms, completed.deadline_ms, completed.dispatched_at_ms,
                completed.acceptance_evidence), (accepted.accepted_at_ms, accepted.deadline_ms,
                accepted.dispatched_at_ms, accepted.acceptance_evidence))
            self.assertEqual(sum(r.method == 'POST' for r in self.calls), 1)

    async def test_background_native_correlation_does_not_accept_portrait_namespace(self):
        async with self.committed() as (db, ref):
            unit, job = self.unit_job(db, self.batch(db, ref), 1)
            record = self.authorize(db, job, unit.input_digest)
            accepted = await self.tick(db, record)
            native = history(record.preview)
            data = native['prompt-1']['prompt'][3]
            data['kinodel_portrait_v1'] = data.pop('kinodel_anchor_unit_v1')
            blocked = await self.tick(db, accepted, histories=native)
            self.assertEqual((blocked.state, blocked.reason), ('blocked', 'contract_error'))
            self.assertEqual(blocked.acceptance_evidence, accepted.acceptance_evidence)
            await self.tick(db, blocked)
            self.assertEqual(sum(r.method == 'POST' for r in self.calls), 1)
            self.assertFalse(any(r.url.path.endswith('/view') for r in self.calls))


class FrozenPortrait6ABytesTests(unittest.TestCase):
    def test_original_identity_intent_candidate_namespace_and_native_bytes(self):
        # Independent fixed baseline vectors, calculated with stdlib only, never
        # deriving expected identities/bodies from the implementation under test.
        intent_body = (
            b'{"attempt_id":"sha256:44876e2917dc36123ae3e8aa16b249d90fbb090ab89ed5c0635aa0dbd3a50a11",'
            b'"batch_id":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
            b'"batch_input_digest":"sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",'
            b'"batch_input_uri":"kinodel://projects/11111111-1111-4111-8111-111111111111/inputs/batch.json",'
            b'"job_id":"sha256:f9a766f79b00b4673464b374501687e14bd92fe8ecfe82ef71f2895d19a4e919",'
            b'"project_id":"11111111-1111-4111-8111-111111111111",'
            b'"schema_id":"comfyui_portrait_submission_intent","schema_version":"1",'
            b'"unit_input_digest":"sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",'
            b'"unit_input_uri":"kinodel://projects/11111111-1111-4111-8111-111111111111/inputs/unit.json",'
            b'"unit_key":"hero-face"}')
        wire_body = (
            b'{"client_id":"kinodel-44876e2917dc36123ae3e8aa16b249d90fbb090ab89ed5c0635aa0dbd3a50a11",'
            b'"extra_data":{"kinodel_portrait_v1":{'
            b'"attempt_id":"sha256:44876e2917dc36123ae3e8aa16b249d90fbb090ab89ed5c0635aa0dbd3a50a11",'
            b'"graph_digest":"sha256:70b00500d611f4a5b77cc97d1f1389994a796b651490cf36c3ee2e9aa93b27a8",'
            b'"input_digest":"sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",'
            b'"intent_digest":"sha256:97795a55e3073e84a0a3af67cc09521038d5b7bfe38c4b316da82d01032d68d9",'
            b'"job_id":"sha256:f9a766f79b00b4673464b374501687e14bd92fe8ecfe82ef71f2895d19a4e919"}},'
            b'"prompt":{"865":{"class_type":"SaveImage","inputs":{"filename_prefix":"portrait","images":["1",0]}}}}')
        intent, wire = json.loads(intent_body), json.loads(wire_body)
        project, artifact, execution = intent['project_id'], '22222222-2222-4222-8222-222222222222', '33333333-3333-4333-8333-333333333333'
        ref = ArtifactRef(project_id=project, artifact_id=artifact, execution_id=execution,
            schema_id='wardrobe_plan', schema_version='2', uri=f'kinodel://projects/{project}/artifacts/{artifact}',
            digest=ZERO, operation_id=ZERO, media_type='application/json', produced_by_stage='wardrobe')
        connection = pins.generation.BatchConnectionPinV1(connection='local', endpoint_digest='sha256:' + 'd' * 64)
        image = dict(kind='portrait', graph=wire['prompt'],
            graph_sha256='70b00500d611f4a5b77cc97d1f1389994a796b651490cf36c3ee2e9aa93b27a8', settings=dict(width=512, height=512))
        batch: Any = SimpleNamespace(batch_id=intent['batch_id'], input_digest=intent['batch_input_digest'],
            uri=intent['batch_input_uri'], prepared_input=SimpleNamespace(source_plan_ref=ref, connection=connection))
        unit: Any = SimpleNamespace(unit_key='hero-face', input_digest=intent['unit_input_digest'],
            uri=intent['unit_input_uri'], prepared_input=SimpleNamespace(image_pin_json=json.dumps(image)))
        job = jobs._record(batch, unit)
        self.assertEqual(job.intent_body, intent_body)
        self.assertEqual(job.intent_digest, 'sha256:97795a55e3073e84a0a3af67cc09521038d5b7bfe38c4b316da82d01032d68d9')
        with patch.object(jobs, 'read_anchor_unit_job', return_value=job), \
                patch.object(batch_store, 'read_batch_input', return_value=batch), \
                patch.object(candidates, '_binding_rows', return_value=()):
            preview = submissions._preview(None, job.job_id, unit.input_digest)[0]
        self.assertEqual(preview.wire_body, wire_body)
        self.assertEqual(preview.wire_digest, 'sha256:b6bc9bb7a93ed8f4514798769ee1c95460aafd928a31d1f62c4ff27a685632e9')
        self.assertEqual(preview.connection_digest, 'sha256:ac92aca197ab1dcca9e3f96a60d2d828321b7e4cec3ab744687fb0150f9cfa20')
        self.assertEqual(sha256_digest(canonical_json(preview)),
            'sha256:56507b541ddb14b855c99b947413fffbcc01734244c4a857aaf39973223279d1')
        descriptor = candidates.PortraitOutputDescriptorV1(node_id='865', history_key='images', index=0,
            filename='portrait.png', subfolder='', type='output', mime_type='image/png')
        self.assertEqual(candidates._candidate_id(job.job_id, job.attempt_id, descriptor),
            'sha256:b6442fbe8f8d46ffa2383a6170874818f23a2cde105a2b729eb475efbc1f75bd')
        metadata = candidates._metadata((job, intent, connection, image, ()), descriptor,
            'sha256:' + 'e' * 64, 10, '.candidate-' + 'f' * 32 + '.tmp')
        self.assertNotIn('schema_id', json.loads(canonical_json(metadata)))
        self.assertNotIn('kind', json.loads(canonical_json(metadata)))
        self.assertEqual(sha256_digest(canonical_json(metadata)),
            'sha256:9429086d249400f6c269b1ad8a42a2d8350d0779c84bd052c4c13a16586df866')
        record = submissions.PortraitSubmissionV1(schema_version='1', preview=preview, revision=0,
            state='authorized', accepted_at_ms=NOW, deadline_ms=NOW + 900_000)
        body = json.loads(canonical_json(record))
        self.assertEqual(set(body), {'schema_version', 'preview', 'revision', 'state', 'accepted_at_ms', 'deadline_ms',
            'dispatched_at_ms', 'prompt_id', 'acceptance_evidence', 'evidence', 'reason', 'candidate_id'})
        self.assertNotIn('schema_id', body['preview'])
        self.assertNotIn('kind', body['preview'])
        self.assertEqual(sha256_digest(canonical_json(record)),
            'sha256:f9975cdaa3296cae6f10fc1c704c22b36f4ece5ee62f804e5259e221a10bcf55')
        for kind, job_id, attempt_id in (
            ('background', 'sha256:74aef01b9d7312cc87e72d81e8fdab4771e6ca2a9a2492707d4b6b3cd5319426',
             'sha256:a7506dda68db2669590a9f652434123dc62a279bd5b10a87235003792117a803'),
            ('sheet', 'sha256:aead1324e4f64ef7e707326b75c813a8d44397e09831deec7b72a107c6266b79',
             'sha256:0c48f81021b3e7ed6f40572dd03cb34a23b078bf1745e351fbfb9cfa3b49d080')):
            other_unit: Any = SimpleNamespace(unit_key=kind, input_digest=unit.input_digest, uri=unit.uri,
                prepared_input=SimpleNamespace(image_pin_json=json.dumps({**image, 'kind': kind})))
            other = jobs._record(batch, other_unit)
            self.assertEqual((other.job_id, other.attempt_id), (job_id, attempt_id))
            self.assertNotEqual(other.job_id, job.job_id)
