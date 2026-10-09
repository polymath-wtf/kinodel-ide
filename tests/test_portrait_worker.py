"""Native protocol/fault checks against isolated saved V2 pins, never live ComfyUI."""

import asyncio
from contextlib import contextmanager
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
import unittest
from unittest.mock import patch

import httpx

from backend import batch_store, database, portrait_candidate_store as candidates
from backend import portrait_submission_store as submissions, render_job_store
from backend.config import resolve_comfyui_connection
from backend.domain import sha256_digest
from tests import test_batch_store as pins
from tests import test_story_wardrobe_api as fixtures
from tests.test_portrait_candidate_store import png


NOW = 1_000_000
ZERO = 'sha256:' + '0' * 64
ENDPOINT = 'https://portrait.test/native/'


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


class Chunks(httpx.AsyncByteStream):
    def __init__(self, body, *, pause: float = 0, partial=None):
        self.body, self.pause, self.partial = body, pause, partial
        self.closed = False

    async def __aiter__(self):
        for start in range(0, len(self.body), 65536):
            if self.pause:
                await asyncio.sleep(self.pause)
            if self.partial is not None and start >= self.partial:
                raise httpx.ReadError('private-token partial transport')
            yield self.body[start:start + 65536]

    async def aclose(self):
        self.closed = True


def response(value, *, status=200, headers=None, raw=False, pause: float = 0, partial=None):
    body = value if raw else encoded(value)
    fields = {'content-type': 'application/json' if not raw else 'image/png'}
    fields.update(headers or {})
    return httpx.Response(status, headers=fields, stream=Chunks(body, pause=pause, partial=partial))


def prompt_tuple(preview, prompt_id='prompt-1'):
    wire = json.loads(preview.wire_body)
    return [1, prompt_id, wire['prompt'], {**wire['extra_data'], 'client_id': wire['client_id']}, ['865']]


def history(preview, prompt_id='prompt-1', *, filename='portrait.png', subfolder=''):
    return {prompt_id: {'prompt': prompt_tuple(preview, prompt_id), 'outputs': {
        '865': {'images': [{'filename': filename, 'subfolder': subfolder, 'type': 'output'}]}},
        'status': {'status_str': 'success', 'completed': True,
                   'messages': [['execution_success', {'prompt_id': prompt_id}]]}}}


class PortraitWorkerTests(fixtures.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    committed: Any = pins.BatchStoreTests.committed
    pin: Any = pins.BatchStoreTests.pin
    context: Any = pins.BatchStoreTests.context
    parents: Any = pins.BatchStoreTests.parents
    prepare: Any = pins.BatchStoreTests.prepare
    path: Any = pins.BatchStoreTests.path

    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('backend.portrait_worker'), 'Native portrait worker is missing')
        from backend import portrait_worker
        self.worker = portrait_worker
        self.store = batch_store
        self.profile = pins.production_catalog()['image_only']['profiles'][0]['pin']
        env = patch.dict(os.environ, {'COMFYUI_LOCAL_ENDPOINT': ENDPOINT, 'COMFYUI_AUTH_TOKEN': 'private-token',
                                     'COMFYUI_CONNECTION': 'server'})
        env.start()
        self.addCleanup(env.stop)
        self.calls = []

    def job(self, db, ref, *, authorize=True, timeout=900_000):
        settings = resolve_comfyui_connection('local')
        batch = self.pin(db, ref, image_size={'width': 512, 'height': 512}, connection={
            'connection': 'local', 'endpoint_digest': 'sha256:' + settings.endpoint_digest})
        unit = self.prepare(db, batch, batch.prepared_input.ordered_units[0].unit_key)
        job = render_job_store.create_portrait_job(db, batch.batch_id, unit.unit_key,
                                                  expected_unit_digest=unit.input_digest)
        preview = submissions.preview_portrait_submission(db, job.job_id, expected_unit_digest=unit.input_digest)
        if not authorize:
            return preview
        return submissions.authorize_portrait_submission(db, job.job_id, expected_unit_digest=unit.input_digest,
            expected_wire_digest=preview.wire_digest, accepted_at_ms=NOW, job_timeout_ms=timeout)

    def args(self, record):
        preview = record.preview
        return dict(expected_unit_digest=preview.unit_input_digest, expected_wire_digest=preview.wire_digest,
                    expected_revision=record.revision)

    def reset(self, db, record):
        db.execute('DELETE FROM portrait_submissions')
        return submissions.authorize_portrait_submission(db, record.preview.job_id,
            expected_unit_digest=record.preview.unit_input_digest, expected_wire_digest=record.preview.wire_digest,
            accepted_at_ms=NOW)

    def dispatched(self, db, record):
        return submissions.claim_portrait_dispatch(db, record.preview.job_id, now_ms=NOW + 1, **self.args(record))

    def accepted(self, db, record):
        return submissions.record_portrait_acceptance(db, record.preview.job_id, **self.args(self.dispatched(db, record)),
            prompt_id='prompt-1', evidence=dict(kind='prompt_response', digest=sha256_digest(b'accepted'),
                prompt_id='prompt-1', wire_digest=record.preview.wire_digest, endpoint_digest=record.preview.endpoint_digest))

    async def tick(self, db, record, handler, *, now=NOW + 2, **changes):
        args: dict[str, Any] = dict(**self.args(record), clock_ms=lambda: now, transport=httpx.MockTransport(handler))
        args.update(changes)
        return await self.worker.tick_portrait_job(db, record.preview.job_id, **args)

    def server(self, db, record, *, queue=None, histories=None, media=None, post=None):
        def handle(request):
            self.assertFalse(db.in_transaction, 'SQL transaction crossed HTTP')
            self.calls.append(request)
            route = request.url.path.removeprefix('/native/')
            if route == 'prompt' and request.method == 'POST':
                if isinstance(post, Exception):
                    raise post
                return response(post if post is not None else {'prompt_id': 'prompt-1', 'number': 1, 'node_errors': {}})
            if route == 'queue':
                return response(queue if queue is not None else {'queue_running': [], 'queue_pending': []})
            if route in ('history', 'history/prompt-1'):
                return response(histories if histories is not None else history(record.preview))
            if route == 'view':
                return media() if media else response(png(), raw=True)
            raise AssertionError('Unexpected native route: ' + route)
        return handle

    async def test_unauthorized_preview_config_and_revision_fail_before_claim_or_http(self):
        async with self.committed() as (db, ref):
            preview = self.job(db, ref, authorize=False)
            no_http = lambda _: self.fail('Unauthorized HTTP')
            with self.assertRaises(LookupError):
                await self.worker.tick_portrait_job(db, preview.job_id, expected_unit_digest=preview.unit_input_digest,
                    expected_wire_digest=preview.wire_digest, expected_revision=0, transport=httpx.MockTransport(no_http))
            record = self.job(db, ref)
            for env in ({'COMFYUI_LOCAL_ENDPOINT': 'https://other.test/'}, {'COMFYUI_LOCAL_ENDPOINT': 'bad'},
                        {'COMFYUI_AUTH_TOKEN': 'bad\nsecret'}):
                with patch.dict(os.environ, env), self.assertRaises(ValueError) as rejected:
                    await self.tick(db, record, no_http)
                self.assertNotIn('secret', str(rejected.exception))
            with patch.object(self.worker.httpx, 'AsyncClient', side_effect=ValueError('private-token')), self.assertRaises(ValueError):
                await self.tick(db, record, no_http)
            with self.assertRaises(ValueError):
                await self.tick(db, record, no_http, expected_revision=1)
            db.execute('BEGIN')
            with self.assertRaises(ValueError):
                await self.tick(db, record, no_http)
            self.assertTrue(db.in_transaction)
            db.execute('ROLLBACK')
            self.assertEqual(submissions.read_portrait_submission(db, preview.job_id,
                expected_unit_digest=preview.unit_input_digest, expected_wire_digest=preview.wire_digest), record)
            expired = await self.tick(db, record, no_http, now=record.deadline_ms)
            self.assertEqual((expired.state, expired.reason, expired.dispatched_at_ms), ('failed', 'deadline_exceeded', None))

    async def test_exact_one_post_verified_client_and_successful_declared_original_import(self):
        async with self.committed() as (db, ref):
            record = self.job(db, ref)
            client = self.worker.httpx.AsyncClient
            with patch.object(self.worker.httpx, 'AsyncClient', wraps=client) as opened:
                accepted = await self.tick(db, record, self.server(db, record))
            self.assertEqual((accepted.state, accepted.prompt_id), ('accepted', 'prompt-1'))
            self.assertFalse(opened.call_args.kwargs['trust_env'])
            self.assertFalse(opened.call_args.kwargs['follow_redirects'])
            self.assertIs(opened.call_args.kwargs['verify'], True)
            self.assertEqual(opened.call_args.kwargs['timeout'].connect, 5)
            self.assertEqual(opened.call_args.kwargs['timeout'].read, 15)
            self.assertEqual(self.calls[0].content, record.preview.wire_body)
            self.assertEqual(self.calls[0].headers['accept-encoding'], 'identity')
            self.assertEqual(self.calls[0].headers['authorization'], 'Bearer private-token')
            self.assertEqual(self.calls[0].url.host, 'portrait.test')
            completed = await self.tick(db, accepted, self.server(db, accepted))
            self.assertEqual(completed.state, 'completed')
            assert completed.candidate_id is not None and completed.evidence is not None
            candidate = candidates.read_portrait_candidate(db, completed.candidate_id,
                expected_unit_digest=record.preview.unit_input_digest)
            self.assertEqual(self.path(candidate).read_bytes(), png())
            self.assertEqual(completed.evidence.kind, 'history')
            self.assertEqual(completed.evidence.digest, sha256_digest(encoded(history(record.preview)['prompt-1'])))
            unchanged = await self.tick(db, completed, lambda _: self.fail('Terminal HTTP'))
            self.assertEqual(unchanged, completed)
            self.assertEqual(sum(r.method == 'POST' for r in self.calls), 1)
        with database.open_database(self.root) as db:
            self.assertEqual(await self.tick(db, completed, lambda _: self.fail('Reopen HTTP')), completed)

    async def test_response_id_commits_before_node_errors_or_later_bad_response_contract(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            for status, post in (
                (200, {'prompt_id': 'prompt-1', 'number': 1, 'node_errors': {'865': {'errors': ['private-token']}}}),
                (200, {'prompt_id': 'prompt-1', 'number': 'bad', 'node_errors': {}}),
                (200, {'prompt_id': 'prompt-1', 'number': True, 'node_errors': {}}),
                (200, {'prompt_id': 'prompt-1', 'number': 1, 'node_errors': []}),
                (200, {'prompt_id': 'prompt-1'}),
                (503, {'prompt_id': 'prompt-1', 'number': 1, 'node_errors': {}}),
            ):
                with self.subTest(status=status, post=post):
                    record = self.reset(db, original)
                    def handle(request):
                        self.assertFalse(db.in_transaction)
                        self.assertEqual((request.method, request.url.path), ('POST', '/native/prompt'))
                        self.calls.append(request)
                        return response(post, status=status)
                    result = await self.tick(db, record, handle)
                    self.assertEqual((result.state, result.prompt_id, result.reason), ('blocked', 'prompt-1', 'contract_error'))
                    assert result.acceptance_evidence is not None
                    self.assertEqual(result.acceptance_evidence.kind, 'prompt_response')
                    self.assertEqual(result.acceptance_evidence.digest, sha256_digest(encoded(post)))
                    self.assertEqual(result.evidence, result.acceptance_evidence)
                    self.assertNotIn('private-token', result.model_dump_json())
                    self.assertEqual(await self.tick(db, result, lambda _: self.fail('Sticky block HTTP')), result)

    async def test_owned_response_contract_block_reopens_and_revalidates_without_second_post(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            post = {'prompt_id': 'prompt-1', 'number': 'malformed-metadata', 'node_errors': {}}
            actual_accept = submissions.record_portrait_acceptance
            def inspect_acceptance(*args, **kwargs):
                accepted = actual_accept(*args, **kwargs)
                self.assertEqual((accepted.state, accepted.prompt_id, accepted.reason), ('accepted', 'prompt-1', None))
                self.assertEqual(submissions.read_portrait_submission(db, original.preview.job_id,
                    expected_unit_digest=original.preview.unit_input_digest,
                    expected_wire_digest=original.preview.wire_digest), accepted)
                return accepted
            with patch.object(submissions, 'record_portrait_acceptance', side_effect=inspect_acceptance):
                blocked = await self.tick(db, original, self.server(db, original, post=post))
            self.assertEqual((blocked.state, blocked.reason, blocked.prompt_id), ('blocked', 'contract_error', 'prompt-1'))
            assert blocked.acceptance_evidence is not None
            self.assertEqual(blocked.acceptance_evidence.digest, sha256_digest(encoded(post)))
            self.assertEqual(blocked.evidence, blocked.acceptance_evidence)
        with database.open_database(self.root) as db:
            restored = submissions.read_portrait_submission(db, blocked.preview.job_id,
                expected_unit_digest=blocked.preview.unit_input_digest, expected_wire_digest=blocked.preview.wire_digest)
            self.assertEqual(restored, blocked)
            self.assertEqual(await self.tick(db, restored, lambda _: self.fail('Offline default HTTP')), restored)
            self.assertEqual(len(self.calls), 1)
            completed = await self.tick(db, restored, self.server(db, restored), revalidate_contract=True)
            self.assertEqual((completed.state, completed.reason, completed.prompt_id), ('completed', None, 'prompt-1'))
            self.assertEqual(completed.acceptance_evidence, restored.acceptance_evidence)
            self.assertEqual(completed.preview, original.preview)
            self.assertEqual((completed.accepted_at_ms, completed.deadline_ms, completed.dispatched_at_ms),
                             (original.accepted_at_ms, original.deadline_ms, blocked.dispatched_at_ms))
            self.assertEqual((completed.output_recovery_authorized_at_ms, completed.output_recovery_deadline_ms), (None, None))
            assert completed.evidence is not None
            self.assertEqual(completed.evidence.digest, sha256_digest(encoded(history(original.preview)['prompt-1'])))
            assert completed.candidate_id is not None
            candidate = candidates.read_portrait_candidate(db, completed.candidate_id,
                expected_unit_digest=original.preview.unit_input_digest)
            self.assertEqual(self.path(candidate).read_bytes(), png())
            self.assertEqual([(request.method, request.url.path) for request in self.calls], [
                ('POST', '/native/prompt'), ('GET', '/native/queue'), ('GET', '/native/history/prompt-1'), ('GET', '/native/view')])

    async def test_lost_response_queue_then_history_recovers_without_second_post(self):
        async with self.committed() as (db, ref):
            record = self.job(db, ref)
            lost = await self.tick(db, record, self.server(db, record, post=httpx.ReadTimeout('private-token')))
            self.assertEqual((lost.state, lost.reason, lost.prompt_id), ('blocked', 'acceptance_unknown', None))
            queue = {'queue_running': [prompt_tuple(record.preview)], 'queue_pending': []}
            queued = await self.tick(db, lost, self.server(db, lost, queue=queue, histories={}))
            assert queued.acceptance_evidence is not None
            self.assertEqual((queued.state, queued.prompt_id, queued.acceptance_evidence.kind), ('accepted', 'prompt-1', 'queue'))
            complete = await self.tick(db, queued, self.server(db, queued))
            self.assertEqual(complete.state, 'completed')
            self.assertEqual(sum(r.method == 'POST' for r in self.calls), 1)

    async def test_unknown_empty_eviction_and_expired_known_jobs_remain_blocked_no_post(self):
        async with self.committed() as (db, ref):
            record = self.job(db, ref)
            dispatched = self.dispatched(db, record)
            unknown = await self.tick(db, dispatched, self.server(db, dispatched, histories={}), now=record.deadline_ms + 1)
            self.assertEqual((unknown.state, unknown.reason, unknown.prompt_id), ('blocked', 'acceptance_unknown', None))
            pending = {'queue_running': [], 'queue_pending': [prompt_tuple(record.preview)]}
            known = await self.tick(db, unknown, self.server(db, unknown, queue=pending, histories={}), now=record.deadline_ms + 1)
            self.assertEqual((known.state, known.prompt_id), ('blocked', 'prompt-1'))
            self.assertIsNotNone(known.acceptance_evidence)
            evicted = await self.tick(db, known, self.server(db, known, histories={}), now=record.deadline_ms + 1)
            self.assertEqual((evicted.state, evicted.prompt_id), ('blocked', 'prompt-1'))
            self.assertEqual(sum(r.method == 'POST' for r in self.calls), 0)

    async def test_conflicting_multiple_matches_and_malformed_native_tuples_block(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            good = prompt_tuple(original.preview)
            variants = [good[:4], [True, *good[1:]], [1, 'prompt-1', {}, good[3], good[4]],
                        [1, 'prompt-1', good[2], {}, good[4]], [1, 'prompt-1', good[2], good[3], []]]
            mismatch = copy.deepcopy(good)
            mismatch[3]['kinodel_portrait_v1']['intent_digest'] = ZERO
            variants.append(mismatch)
            for item in variants:
                record = self.dispatched(db, self.reset(db, original))
                result = await self.tick(db, record, self.server(db, record,
                    queue={'queue_running': [item], 'queue_pending': []}, histories={}))
                self.assertEqual(result.state, 'blocked')
            record = self.dispatched(db, self.reset(db, original))
            conflict = await self.tick(db, record, self.server(db, record, queue={
                'queue_running': [good, prompt_tuple(original.preview, 'prompt-2')], 'queue_pending': []}, histories={}))
            self.assertEqual((conflict.state, conflict.reason), ('blocked', 'contract_error'))
            self.assertEqual(sum(r.method == 'POST' for r in self.calls), 0)

    def foreign_tuple(self, preview, prompt_id='foreign-1'):
        item = prompt_tuple(preview, prompt_id)
        item[3]['kinodel_portrait_v1'].update(job_id=ZERO, attempt_id=ZERO)
        item[3]['client_id'] = 'foreign-client'
        return item

    async def test_broken_foreign_queue_and_history_do_not_poison_owned_import_and_reopen(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            record = self.accepted(db, original)
            bad_queue = self.foreign_tuple(record.preview)
            bad_queue[0] = 'private-token C:\\private\\queue.png'
            bad_history = {'private': 'https://private.test/token', 'prompt': self.foreign_tuple(record.preview, 'foreign-2')[:4]}
            queue = {'queue_running': [bad_queue, prompt_tuple(record.preview)], 'queue_pending': []}
            histories = {**history(record.preview), 'foreign-2': bad_history,
                         'foreign-3': {**history(record.preview, 'foreign-3')['foreign-3'],
                                       'prompt': self.foreign_tuple(record.preview, 'foreign-3')}}
            # Existing candidate identity/original must be reused, not downloaded again.
            candidate = candidates.import_portrait_candidate(db, record.preview.job_id, record.preview.attempt_id,
                expected_unit_digest=record.preview.unit_input_digest, stream=io.BytesIO(png()), descriptor=dict(
                    node_id='865', history_key='images', index=0, filename='portrait.png', subfolder='',
                    type='output', mime_type='image/png'))
            completed = await self.tick(db, record, self.server(db, record, queue=queue, histories=histories,
                media=lambda: self.fail('Downloaded existing candidate')))
            self.assertEqual((completed.state, completed.candidate_id), ('completed', candidate.candidate_id))
            self.assertEqual([(d.kind, d.source, d.prompt_id, d.reason) for d in completed.diagnostics], [
                ('broken_job', 'queue', 'foreign-1', 'native_tuple'),
                ('broken_job', 'history', 'foreign-2', 'native_tuple')])
            self.assertEqual(completed.diagnostics[0].digest, sha256_digest(encoded(bad_queue)))
            self.assertEqual(completed.diagnostics[1].digest,
                             sha256_digest(encoded({'key': 'foreign-2', 'record': bad_history})))
            for private in ('private-token', 'C:\\private', 'https://private.test/token'):
                self.assertNotIn(private, completed.model_dump_json())
            self.assertEqual(completed.acceptance_evidence, record.acceptance_evidence)
            self.assertEqual(completed.preview, original.preview)
            self.assertEqual(self.path(candidate).read_bytes(), png())
        with database.open_database(self.root) as db:
            restored = submissions.read_portrait_submission(db, completed.preview.job_id,
                expected_unit_digest=completed.preview.unit_input_digest, expected_wire_digest=completed.preview.wire_digest)
            self.assertEqual(restored, completed)
            self.assertEqual(await self.tick(db, restored, lambda _: self.fail('Offline diagnostic HTTP')), restored)
            self.assertTrue(all(r.method == 'GET' for r in self.calls))

    async def test_foreign_diagnostics_replay_stable_unknown_dispatch_never_proves_acceptance(self):
        async with self.committed() as (db, ref):
            record = self.dispatched(db, self.job(db, ref))
            foreign = self.foreign_tuple(record.preview)[:4]
            queue = {'queue_running': [foreign, foreign], 'queue_pending': []}
            first = await self.tick(db, record, self.server(db, record, queue=queue, histories={}))
            self.assertEqual((first.state, first.reason, first.prompt_id), ('blocked', 'acceptance_unknown', None))
            self.assertEqual(len(first.diagnostics), 1)
            row = submissions._row(db, first.preview.job_id)
            replayed = await self.tick(db, first, self.server(db, first, queue=queue, histories={}))
            self.assertEqual(replayed, first)
            self.assertEqual(submissions._row(db, first.preview.job_id), row)
            completed = await self.tick(db, replayed, self.server(db, replayed))
            self.assertEqual(completed.state, 'completed')
            self.assertEqual(completed.diagnostics, first.diagnostics)
            self.assertFalse(any(r.method == 'POST' for r in self.calls))

    async def test_malformed_own_related_or_identity_free_records_never_hide_as_foreign(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            cases = [('own_id', True), ('own_job', True), ('own_attempt', True), ('other_namespace', True),
                     ('own_client', True), ('no_identity', True), ('unknown_foreign_id_only', False),
                     ('unknown_partial_foreign_correlation', False)]
            for name, known in cases:
                with self.subTest(name=name):
                    record = (self.accepted if known else self.dispatched)(db, self.reset(db, original))
                    item = self.foreign_tuple(record.preview)[:4]
                    if name == 'own_id': item[1] = 'prompt-1'
                    if name == 'own_job': item[3]['kinodel_portrait_v1']['job_id'] = record.preview.job_id
                    if name == 'own_attempt': item[3]['kinodel_portrait_v1']['attempt_id'] = record.preview.attempt_id
                    if name == 'other_namespace': item[3]['kinodel_anchor_unit_v1'] = {'job_id': record.preview.job_id}
                    if name == 'own_client': item[3]['client_id'] = json.loads(record.preview.wire_body)['client_id']
                    if name == 'no_identity': item = []
                    if name == 'unknown_foreign_id_only': item[3] = {}
                    if name == 'unknown_partial_foreign_correlation': del item[3]['kinodel_portrait_v1']['attempt_id']
                    result = await self.tick(db, record, self.server(db, record,
                        queue={'queue_running': [item], 'queue_pending': []}))
                    self.assertEqual((result.state, result.reason), ('blocked', 'contract_error'))
                    self.assertEqual(result.diagnostics, [])
                    self.assertEqual(await self.tick(db, result, lambda _: self.fail('Sticky contract HTTP')), result)
            self.assertFalse(any(r.method == 'POST' or r.url.path.endswith('/view') for r in self.calls))

    async def test_history_key_and_discovered_owned_id_override_malformed_foreign_hints(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            for name in ('own_key', 'own_tuple_id', 'discovered_id', 'foreign_only_own_route', 'foreign_shape'):
                with self.subTest(name=name):
                    record = (self.dispatched if name == 'discovered_id' else self.accepted)(db, self.reset(db, original))
                    item = self.foreign_tuple(record.preview)[:4]
                    if name in ('own_tuple_id', 'discovered_id'): item[1] = 'prompt-1'
                    key = 'prompt-1' if name == 'own_key' else item[1]
                    histories = {key: {'prompt': item}}
                    if name == 'discovered_id': histories = history(record.preview)
                    if name == 'foreign_only_own_route':
                        histories = history(record.preview, 'foreign-1')
                        histories['foreign-1']['prompt'] = self.foreign_tuple(record.preview)
                    if name == 'foreign_shape': histories = {'foreign-1': {'private': 'private-token'}}
                    queue = {'queue_running': [item] if name == 'discovered_id' else [], 'queue_pending': []}
                    result = await self.tick(db, record, self.server(db, record, queue=queue, histories=histories))
                    self.assertEqual(result.state, 'blocked')
                    self.assertEqual(result.reason, 'history_unavailable' if name in ('foreign_only_own_route', 'foreign_shape') else 'contract_error')
                    self.assertEqual(len(result.diagnostics), 1 if name == 'foreign_shape' else 0)
            self.assertFalse(any(r.method == 'POST' or r.url.path.endswith('/view') for r in self.calls))

    async def test_broken_foreign_diagnostic_survives_later_owned_conflict_and_top_level_stays_strict(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            record = self.dispatched(db, original)
            foreign = self.foreign_tuple(record.preview)[:4]
            result = await self.tick(db, record, self.server(db, record, queue={'queue_running': [foreign,
                prompt_tuple(record.preview), prompt_tuple(record.preview, 'prompt-2')], 'queue_pending': []}, histories={}))
            self.assertEqual((result.state, result.reason, result.prompt_id), ('blocked', 'contract_error', None))
            self.assertEqual(len(result.diagnostics), 1)
            for queue, histories in (([], {}), ({'queue_running': [], 'queue_pending': [], 'extra': []}, {}),
                                     ({'queue_running': [], 'queue_pending': []}, [])):
                record = self.dispatched(db, self.reset(db, original))
                result = await self.tick(db, record, self.server(db, record, queue=queue, histories=histories))
                self.assertEqual((result.state, result.reason), ('blocked', 'contract_error'))
                self.assertEqual(result.diagnostics, [])

    async def test_foreign_history_bad_status_and_identity_are_diagnostic_not_success(self):
        async with self.committed() as (db, ref):
            record = self.accepted(db, self.job(db, ref))
            foreign = history(record.preview, 'foreign-1')['foreign-1']
            foreign['prompt'] = self.foreign_tuple(record.preview)
            foreign['status'] = {'private': 'private-token'}
            identity = {'prompt': self.foreign_tuple(record.preview, 'foreign-3')}
            histories = {**history(record.preview), 'foreign-1': foreign, 'foreign-2': identity}
            completed = await self.tick(db, record, self.server(db, record, histories=histories))
            self.assertEqual(completed.state, 'completed')
            self.assertEqual([(d.reason, d.prompt_id) for d in completed.diagnostics], [
                ('history_status', 'foreign-1'), ('history_identity', 'foreign-3')])
            self.assertNotIn('private-token', completed.model_dump_json())

    async def test_valid_nonmatch_owned_signals_block_queue_and_history(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            for source, known, signal in (('queue', True, 'client'), ('history', True, 'job'),
                                           ('queue', False, 'attempt'), ('history', False, 'client'),
                                           ('queue', False, 'discovered_id')):
                with self.subTest(source=source, known=known, signal=signal):
                    record = (self.accepted if known else self.dispatched)(db, self.reset(db, original))
                    item = self.foreign_tuple(record.preview)
                    if signal == 'client': item[3]['client_id'] = json.loads(record.preview.wire_body)['client_id']
                    elif signal == 'discovered_id': item[1] = 'prompt-1'
                    else: item[3]['kinodel_anchor_unit_v1'] = {signal + '_id': getattr(record.preview, signal + '_id')}
                    queue = {'queue_running': [item] if source == 'queue' else [], 'queue_pending': []}
                    if signal == 'discovered_id': queue['queue_running'].insert(0, prompt_tuple(record.preview))
                    histories = history(record.preview)
                    if source == 'history':
                        histories.update(history(record.preview, 'foreign-1'))
                        histories['foreign-1']['prompt'] = item
                    result = await self.tick(db, record, self.server(db, record, queue=queue, histories=histories))
                    self.assertEqual((result.state, result.reason), ('blocked', 'contract_error'))
                    self.assertEqual(result.prompt_id, record.prompt_id)
                    self.assertEqual(result.diagnostics, [])
                    self.assertEqual(await self.tick(db, result, lambda _: self.fail('Sticky contract HTTP')), result)
            self.assertFalse(any(r.method == 'POST' or r.url.path.endswith('/view') for r in self.calls))

    async def test_discovered_owned_id_cleans_quarantine_before_every_later_protocol_exit(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            for source, trailing_error in (('queue', False), ('queue', True), ('history', True), ('queue-reversed', True)):
                with self.subTest(source=source, trailing_error=trailing_error):
                    record = self.dispatched(db, self.reset(db, original))
                    queue = {'queue_running': [self.foreign_tuple(record.preview, 'foreign-keep')[:4],
                        self.foreign_tuple(record.preview, 'prompt-1')[:4]], 'queue_pending': []}
                    histories = {}
                    if source.startswith('queue'):
                        if source == 'queue-reversed': queue['queue_running'].insert(1, prompt_tuple(record.preview))
                        else: queue['queue_running'].append(prompt_tuple(record.preview))
                        if trailing_error: queue['queue_running'].append([])
                    else:
                        histories = {**history(record.preview), 'zzz-ambiguous': {}}
                    result = await self.tick(db, record, self.server(db, record, queue=queue, histories=histories))
                    self.assertEqual((result.state, result.reason, result.prompt_id), ('blocked', 'contract_error', None))
                    self.assertEqual([d.prompt_id for d in result.diagnostics], ['foreign-keep'])
                    self.assertEqual(submissions.read_portrait_submission(db, result.preview.job_id,
                        expected_unit_digest=result.preview.unit_input_digest, expected_wire_digest=result.preview.wire_digest), result)
                    self.assertEqual(await self.tick(db, result, lambda _: self.fail('Sticky contract HTTP')), result)
            self.assertTrue(all(r.method == 'GET' for r in self.calls))

    async def test_valid_nonkinodel_records_without_correlation_do_not_block_unknown_owned_import(self):
        async with self.committed() as (db, ref):
            record = self.dispatched(db, self.job(db, ref))
            item = prompt_tuple(record.preview, 'nonkinodel-1')
            item[3] = {}  # Absence of correlation is not an explicit own signal on a valid tuple.
            histories = {**history(record.preview), **history(record.preview, 'nonkinodel-1')}
            histories['nonkinodel-1']['prompt'] = item
            result = await self.tick(db, record, self.server(db, record,
                queue={'queue_running': [item], 'queue_pending': []}, histories=histories))
            self.assertEqual((result.state, result.prompt_id, result.diagnostics), ('completed', 'prompt-1', []))
            self.assertFalse(any(r.method == 'POST' for r in self.calls))

    async def test_known_history_identity_graph_correlation_client_and_output_checks(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            base = history(original.preview)
            variants = []
            for change in ('tuple_id', 'graph', 'correlation', 'client', 'missing_slot', 'partial', 'error', 'messages', 'traversal'):
                value = copy.deepcopy(base)
                item = value['prompt-1']
                if change == 'tuple_id': item['prompt'][1] = 'other'
                if change == 'graph': item['prompt'][2]['865']['class_type'] = 'Other'
                if change == 'correlation': item['prompt'][3]['kinodel_portrait_v1']['input_digest'] = ZERO
                if change == 'client': item['prompt'][3]['client_id'] = 'other'
                if change == 'missing_slot': item['outputs'] = {'999': item['outputs']['865']}
                if change == 'partial': item['status']['completed'] = False
                if change == 'error': item['status']['messages'].append(['execution_error', {'secret': 'private-token'}])
                if change == 'messages': item['status']['messages'] = ['malformed']
                if change == 'traversal': item['outputs']['865']['images'][0]['filename'] = '../evil.png'
                variants.append((change, value))
            for name, value in variants:
                record = self.accepted(db, self.reset(db, original))
                result = await self.tick(db, record, self.server(db, record, histories=value))
                self.assertNotEqual(result.state, 'completed', name)
                self.assertEqual(result.prompt_id, 'prompt-1')
                self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_candidates').fetchone(), (0,))
            self.assertFalse(any(r.url.path.endswith('/view') for r in self.calls))

    async def test_matching_history_failure_terminal_and_contract_block_does_not_heal(self):
        async with self.committed() as (db, ref):
            record = self.accepted(db, self.job(db, ref))
            failed_history = history(record.preview)
            failed_history['prompt-1']['status'] = {'status_str': 'error', 'completed': False,
                'messages': [['execution_error', {'prompt_id': 'prompt-1'}]]}
            result = await self.tick(db, record, self.server(db, record, histories=failed_history))
            self.assertEqual((result.state, result.reason, result.prompt_id), ('failed', 'provider_failed', 'prompt-1'))
            record = self.accepted(db, self.reset(db, record))
            blocked = submissions.block_portrait_submission(db, record.preview.job_id, reason='contract_error', **self.args(record))
            self.assertEqual(await self.tick(db, blocked, lambda _: self.fail('Contract block healed')), blocked)
            # Bare storage acceptance is not permission to clear an unresolved contract reason.
            recovered = submissions.record_portrait_acceptance(db, blocked.preview.job_id, **self.args(blocked),
                prompt_id='prompt-1', evidence=dict(kind='history', digest=sha256_digest(b'claimed history'),
                    prompt_id='prompt-1', wire_digest=blocked.preview.wire_digest, endpoint_digest=blocked.preview.endpoint_digest))
            still_blocked = await self.tick(db, recovered, lambda _: self.fail('Unresolved contract reason healed'))
            self.assertEqual((still_blocked.state, still_blocked.reason, still_blocked.prompt_id), ('blocked', 'contract_error', 'prompt-1'))

    async def test_download_original_encoding_url_bounds_partial_and_bad_png_never_complete(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            good_history = history(original.preview, filename='face & summer.png', subfolder='portraits/café')
            variants = [lambda: response(b'not png', raw=True),
                        lambda: response(png(), raw=True, headers={'content-type': 'image/jpeg'}),
                        lambda: response(png(), raw=True, headers={'content-encoding': 'gzip'}),
                        lambda: response(png(), raw=True, headers={'content-length': str(len(png()) + 1)}),
                        lambda: response(png(), raw=True, headers={'content-length': str(16 * 1024 * 1024 + 1)}),
                        lambda: response(png() + b'x' * 65536, raw=True, partial=65536)]
            for media in variants:
                record = self.accepted(db, self.reset(db, original))
                result = await self.tick(db, record, self.server(db, record, histories=good_history, media=media))
                self.assertEqual(result.state, 'blocked')
                self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_candidates').fetchone(), (0,))
            views = [r for r in self.calls if r.url.path.endswith('/view')]
            self.assertTrue(views)
            self.assertEqual(views[0].url.params['filename'], 'face & summer.png')
            self.assertEqual(views[0].url.params['subfolder'], 'portraits/café')
            self.assertEqual(views[0].url.params['type'], 'output')
            self.assertNotIn('face & summer.png', str(views[0].url))

    async def test_json_duplicate_nonfinite_encoding_redirect_and_total_timeout_are_bounded(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            bodies = [b'{"prompt_id":"prompt-1","prompt_id":"other"}', b'{"n":NaN}', b'{"n":1e999}', b'not JSON']
            responses = [lambda body=body: response(body, raw=True, headers={'content-type': 'application/json'}) for body in bodies]
            responses += [lambda: response({}, headers={'content-encoding': 'gzip'}),
                          lambda: response({}, headers={'content-length': '16777217'}),
                          lambda: response({}, status=302, headers={'location': 'https://other.test/'}),
                          lambda: response({}, pause=.1)]
            for reply in responses:
                record = self.reset(db, original)
                def handle(request):
                    self.calls.append(request)
                    self.assertFalse(db.in_transaction)
                    return reply()
                with patch.object(self.worker, 'REQUEST_TIMEOUT', .02):
                    result = await self.tick(db, record, handle)
                self.assertEqual((result.state, result.prompt_id), ('blocked', None))
            self.assertTrue(all(r.method == 'POST' and r.url.host == 'portrait.test' for r in self.calls))

    async def test_published_candidate_resume_rechecks_history_and_never_download_heals_corruption(self):
        async with self.committed() as (db, ref):
            record = self.accepted(db, self.job(db, ref))
            candidate = candidates.import_portrait_candidate(db, record.preview.job_id, record.preview.attempt_id,
                expected_unit_digest=record.preview.unit_input_digest, stream=io.BytesIO(png()), descriptor=dict(
                    node_id='865', history_key='images', index=0, filename='portrait.png', subfolder='',
                    type='output', mime_type='image/png'))
            handler = self.server(db, record, media=lambda: self.fail('Downloaded existing original'))
            completed = await self.tick(db, record, handler, now=record.deadline_ms + 1)
            self.assertEqual((completed.state, completed.candidate_id), ('completed', candidate.candidate_id))
            record = self.accepted(db, self.reset(db, record))
            self.path(candidate).write_bytes(b'corrupt')
            blocked = await self.tick(db, record, handler)
            self.assertEqual((blocked.state, blocked.reason), ('blocked', 'output_invalid'))
            self.assertEqual(self.path(candidate).read_bytes(), b'corrupt')

    async def test_revision_change_across_http_cannot_publish_or_overwrite_facts(self):
        async with self.committed() as (db, ref):
            record = self.accepted(db, self.job(db, ref))
            handle = self.server(db, record)
            def drift(request):
                if request.url.path.endswith('/queue'):
                    submissions.block_portrait_submission(db, record.preview.job_id, **self.args(record), reason='history_unavailable')
                return handle(request)
            with self.assertRaises(ValueError):
                await self.tick(db, record, drift)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_candidates').fetchone(), (0,))
            self.assertEqual(db.execute('SELECT state,revision FROM portrait_submissions').fetchone(), ('blocked', 3))

    async def test_large_finite_native_queue_number_does_not_crash_after_acceptance_commit(self):
        async with self.committed() as (db, ref):
            record = self.job(db, ref)
            result = await self.tick(db, record, self.server(db, record, post={
                'prompt_id': 'prompt-1', 'number': 10**400, 'node_errors': {}}))
            self.assertEqual((result.state, result.prompt_id), ('accepted', 'prompt-1'))

    async def test_setup_failure_is_safe_before_claim_and_tick_bounds_transport_cleanup(self):
        class BrokenSetup(httpx.MockTransport):
            async def __aenter__(self):
                raise ValueError('private-token https://private.test/')
        class SlowClose(httpx.MockTransport):
            async def aclose(self):
                await asyncio.sleep(10)
        async with self.committed() as (db, ref):
            record = self.job(db, ref)
            with self.assertRaises(ValueError) as rejected:
                await self.tick(db, record, lambda _: self.fail('Setup sent HTTP'),
                                transport=BrokenSetup(lambda _: self.fail('Setup sent HTTP')))
            self.assertNotIn('private-token', str(rejected.exception))
            self.assertEqual(db.execute('SELECT state,revision FROM portrait_submissions').fetchone(), ('authorized', 0))
            accepted = self.accepted(db, record)
            handler = self.server(db, accepted, histories={})
            with patch.object(self.worker, 'TICK_TIMEOUT', .02, create=True), self.assertRaises(ValueError):
                await asyncio.wait_for(self.tick(db, accepted, handler, transport=SlowClose(handler)), timeout=.3)

    async def test_actual_body_caps_slow_png_and_absolute_remaining_http_budget(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            huge = b'x' * (16 * 1024 * 1024 + 1)
            for media in (lambda: response(huge, raw=True), lambda: response(png(), raw=True, pause=.1)):
                record = self.accepted(db, self.reset(db, original))
                with patch.object(self.worker, 'REQUEST_TIMEOUT', .02):
                    result = await self.tick(db, record, self.server(db, record, media=media))
                self.assertEqual((result.state, result.reason), ('blocked', 'output_invalid'))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_candidates').fetchone(), (0,))
            record = self.reset(db, original)
            result = await self.tick(db, record, lambda _: response(huge, raw=True, headers={'content-type': 'application/json'}))
            self.assertEqual((result.state, result.prompt_id), ('blocked', None))
            record = self.reset(db, original)
            result = await self.tick(db, record, lambda _: response(
                {'prompt_id': 'prompt-1', 'number': 1, 'node_errors': {}}, pause=.1), now=record.deadline_ms - 1)
            self.assertEqual((result.state, result.reason), ('blocked', 'acceptance_unknown'))

    async def test_unsolicited_partial_transfer_is_not_an_original_or_native_evidence(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            for status, headers in ((206, {'content-range': 'bytes 0-10/100'}),
                                    (200, {'content-range': 'bytes 0-10/100'}),
                                    (200, {'transfer-encoding': 'gzip'}),
                                    (200, {'transfer-encoding': 'chunked', 'content-length': str(len(png()))})):
                record = self.accepted(db, self.reset(db, original))
                result = await self.tick(db, record, self.server(db, record,
                    media=lambda: response(png(), raw=True, status=status, headers=headers)))
                self.assertEqual((result.state, result.reason), ('blocked', 'output_invalid'))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_candidates').fetchone(), (0,))
            record = self.accepted(db, self.reset(db, original))
            def partial_queue(request):
                self.assertFalse(db.in_transaction)
                return response({'queue_running': [prompt_tuple(record.preview)], 'queue_pending': []}, status=206)
            blocked = await self.tick(db, record, partial_queue)
            self.assertEqual(blocked.state, 'blocked')

    async def test_expired_unsent_intent_settles_without_requiring_current_endpoint_configuration(self):
        async with self.committed() as (db, ref):
            record = self.job(db, ref)
            with patch.dict(os.environ, {'COMFYUI_LOCAL_ENDPOINT': 'bad-unused'}):
                result = await self.tick(db, record, lambda _: self.fail('Expired HTTP'), now=record.deadline_ms)
            self.assertEqual((result.state, result.reason, result.dispatched_at_ms), ('failed', 'deadline_exceeded', None))

    async def test_temporary_native_http_outage_can_reconcile_without_clearing_contract_blocks(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            handler = self.server(db, original)
            accepted = await self.tick(db, original, handler)
            def outage(request):
                if '/history/' in request.url.path:
                    self.calls.append(request)
                    return response({'error': 'private-token'}, status=503)
                return handler(request)
            blocked = await self.tick(db, accepted, outage)
            self.assertEqual((blocked.state, blocked.reason, blocked.prompt_id), ('blocked', 'history_unavailable', 'prompt-1'))
            self.assertNotIn('private-token', blocked.model_dump_json())
            completed = await self.tick(db, blocked, handler)
            self.assertEqual(completed.state, 'completed')
            self.assertEqual(sum(r.method == 'POST' for r in self.calls), 1)

    async def test_schema_float_normalization_and_native_windows_query_preserve_frozen_wire(self):
        async with self.committed() as (db, ref):
            record = self.accepted(db, self.job(db, ref))
            native = history(record.preview, subfolder='kinodel\\api')
            for field in ('cfg', 'denoise'):
                native['prompt-1']['prompt'][2]['856']['inputs'][field] = 1.0
            original_wire = record.preview.wire_body
            result = await self.tick(db, record, self.server(db, record, histories=native))
            self.assertEqual(result.state, 'completed')
            self.assertEqual(result.preview.wire_body, original_wire)
            self.assertEqual(native['prompt-1']['prompt'][2]['856']['inputs']['cfg'], 1.0)
            self.assertEqual([r.url.params['subfolder'] for r in self.calls if r.url.path.endswith('/view')], ['kinodel\\api'])
            assert result.candidate_id is not None
            candidate = candidates.read_portrait_candidate(db, result.candidate_id,
                expected_unit_digest=record.preview.unit_input_digest)
            self.assertEqual(candidate.descriptor.subfolder, 'kinodel/api')

    async def test_float_rule_rejects_changed_nonfloat_bool_and_link_numbers_without_tolerance(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            for field, value in (('cfg', 1.0000000000000002), ('cfg', True), ('seed', 42.0), ('steps', 20.0)):
                record = self.accepted(db, self.reset(db, original))
                native = history(record.preview)
                native['prompt-1']['prompt'][2]['856']['inputs'][field] = value
                result = await self.tick(db, record, self.server(db, record, histories=native))
                self.assertEqual((result.state, result.reason), ('blocked', 'contract_error'))
            record = self.accepted(db, self.reset(db, original))
            native = history(record.preview)
            native['prompt-1']['prompt'][2]['865']['inputs']['images'][1] = 0.0
            result = await self.tick(db, record, self.server(db, record, histories=native))
            self.assertEqual(result.state, 'blocked')
            self.assertFalse(any(r.url.path.endswith('/view') for r in self.calls))

    async def test_windows_subfolder_rejects_absolute_drive_unc_traversal_and_empty_components(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            for subfolder in ('\\absolute', 'C:\\dir', '\\\\server\\share', 'kinodel\\..\\api',
                              'kinodel\\\\api', 'kinodel\\', '/absolute', 'kinodel/../api'):
                record = self.accepted(db, self.reset(db, original))
                result = await self.tick(db, record, self.server(db, record,
                    histories=history(record.preview, subfolder=subfolder)))
                self.assertEqual((result.state, result.reason), ('blocked', 'contract_error'), subfolder)
            self.assertFalse(any(r.url.path.endswith('/view') for r in self.calls))

    async def test_explicit_contract_revalidation_same_owned_success_clears_only_after_safe_history(self):
        async with self.committed() as (db, ref):
            accepted = self.accepted(db, self.job(db, ref))
            blocked = submissions.block_portrait_submission(db, accepted.preview.job_id, **self.args(accepted), reason='contract_error')
            self.assertEqual(await self.tick(db, blocked, lambda _: self.fail('Default healed')), blocked)
            native = history(blocked.preview, subfolder='kinodel\\api')
            for field in ('cfg', 'denoise'):
                native['prompt-1']['prompt'][2]['856']['inputs'][field] = 1.0
            original_row = submissions._row(db, blocked.preview.job_id)
            handle = self.server(db, blocked, histories=native)
            def inspect_before_accept(*args, **kwargs):
                self.assertEqual(submissions._row(db, blocked.preview.job_id), original_row)
                self.assertEqual(kwargs['evidence'].kind, 'history')
                self.assertIs(kwargs['revalidate_contract'], True)
                return actual_accept(*args, **kwargs)
            actual_accept = submissions.record_portrait_acceptance
            with patch.object(submissions, 'record_portrait_acceptance', side_effect=inspect_before_accept):
                result = await self.tick(db, blocked, handle, revalidate_contract=True)
            self.assertEqual((result.state, result.prompt_id, result.reason), ('completed', 'prompt-1', None))
            self.assertEqual(result.acceptance_evidence, blocked.acceptance_evidence)
            self.assertEqual((result.accepted_at_ms, result.deadline_ms, result.dispatched_at_ms),
                             (blocked.accepted_at_ms, blocked.deadline_ms, blocked.dispatched_at_ms))
            self.assertFalse(any(r.method == 'POST' for r in self.calls))

    async def test_explicit_revalidation_does_not_clear_failed_unsafe_mismatched_or_queue_only_history(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            variants = []
            for change in ('failure', 'partial', 'traversal', 'namespace', 'value'):
                native = history(original.preview)
                if change == 'failure': native['prompt-1']['status']['status_str'] = 'error'
                if change == 'partial': native['prompt-1']['status']['completed'] = False
                if change == 'traversal': native['prompt-1']['outputs']['865']['images'][0]['subfolder'] = '..\\evil'
                if change == 'namespace': native['prompt-1']['prompt'][3]['kinodel_portrait_v1']['intent_digest'] = ZERO
                if change == 'value': native['prompt-1']['prompt'][2]['856']['inputs']['cfg'] = 1.01
                variants.append(native)
            variants.append({})
            for native in variants:
                accepted = self.accepted(db, self.reset(db, original))
                blocked = submissions.block_portrait_submission(db, accepted.preview.job_id, **self.args(accepted), reason='contract_error')
                result = await self.tick(db, blocked, self.server(db, blocked, histories=native,
                    queue={'queue_running': [prompt_tuple(blocked.preview)], 'queue_pending': []}), revalidate_contract=True)
                self.assertEqual(result, blocked)
            self.assertFalse(any(r.method == 'POST' or r.url.path.endswith('/view') for r in self.calls))

    async def test_explicit_revalidation_expired_budget_never_downloads_or_renews(self):
        async with self.committed() as (db, ref):
            accepted = self.accepted(db, self.job(db, ref))
            blocked = submissions.block_portrait_submission(db, accepted.preview.job_id, **self.args(accepted), reason='contract_error')
            result = await self.tick(db, blocked, self.server(db, blocked), revalidate_contract=True, now=blocked.deadline_ms + 1)
            self.assertEqual((result.state, result.reason, result.prompt_id), ('blocked', 'deadline_exceeded', 'prompt-1'))
            self.assertEqual(result.deadline_ms, blocked.deadline_ms)
            self.assertFalse(any(r.method == 'POST' or r.url.path.endswith('/view') for r in self.calls))

    async def test_unknown_contract_revalidation_reopens_sticky_then_imports_unique_safe_history_get_only(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            dispatched = self.dispatched(db, original)
            blocked = await self.tick(db, dispatched, self.server(db, dispatched, queue={
                'queue_running': [prompt_tuple(original.preview)[:4]], 'queue_pending': []}))
            self.assertEqual((blocked.state, blocked.reason, blocked.prompt_id, blocked.acceptance_evidence),
                             ('blocked', 'contract_error', None, None))
        with database.open_database(self.root) as db:
            restored = submissions.read_portrait_submission(db, blocked.preview.job_id,
                expected_unit_digest=blocked.preview.unit_input_digest, expected_wire_digest=blocked.preview.wire_digest)
            self.assertEqual(restored, blocked)
            self.assertEqual(await self.tick(db, restored, lambda _: self.fail('Default unknown contract HTTP')), restored)
            self.calls.clear()
            queue = {'queue_running': [self.foreign_tuple(restored.preview)[:4], prompt_tuple(restored.preview)],
                     'queue_pending': []}
            handle = self.server(db, restored, queue=queue)
            proof_digest = sha256_digest(encoded(history(restored.preview)['prompt-1']))
            def inspect_view(request):
                if request.url.path.endswith('/view'):
                    saved = submissions.read_portrait_submission(db, restored.preview.job_id,
                        expected_unit_digest=restored.preview.unit_input_digest,
                        expected_wire_digest=restored.preview.wire_digest)
                    self.assertEqual((saved.state, saved.reason, saved.prompt_id), ('accepted', None, 'prompt-1'))
                    self.assertEqual(saved.acceptance_evidence, saved.evidence)
                    assert saved.acceptance_evidence is not None
                    self.assertEqual((saved.acceptance_evidence.kind, saved.acceptance_evidence.digest), ('history', proof_digest))
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_candidates').fetchone(), (0,))
                return handle(request)
            completed = await self.tick(db, restored, inspect_view, revalidate_contract=True)
            self.assertEqual((completed.state, completed.reason, completed.prompt_id), ('completed', None, 'prompt-1'))
            self.assertEqual(completed.acceptance_evidence, completed.evidence)
            self.assertEqual(completed.preview, original.preview)
            self.assertEqual((completed.accepted_at_ms, completed.deadline_ms, completed.dispatched_at_ms),
                             (original.accepted_at_ms, original.deadline_ms, blocked.dispatched_at_ms))
            self.assertEqual((completed.output_recovery_authorized_at_ms, completed.output_recovery_deadline_ms), (None, None))
            self.assertEqual([d.prompt_id for d in completed.diagnostics], ['foreign-1'])
            assert completed.candidate_id is not None
            candidate = candidates.read_portrait_candidate(db, completed.candidate_id,
                expected_unit_digest=original.preview.unit_input_digest)
            self.assertEqual(self.path(candidate).read_bytes(), png())
            self.assertEqual([(r.method, r.url.path) for r in self.calls], [
                ('GET', '/native/queue'), ('GET', '/native/history'), ('GET', '/native/view')])

    async def test_unknown_contract_revalidation_rejects_nonunique_unsuccessful_unsafe_or_unowned_proof(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            for change in ('queue_only', 'absence', 'multiple_history', 'multiple_queue', 'graph', 'correlation',
                           'client', 'namespace', 'output_nodes', 'history_id', 'provider_error', 'interrupted',
                           'execution_error', 'incomplete', 'missing_output', 'multiple_outputs', 'unsafe', 'foreign',
                           'owned_foreign_hint', 'discovered_owned_quarantine'):
                with self.subTest(change=change):
                    blocked = submissions.block_portrait_submission(db, original.preview.job_id,
                        **self.args(self.dispatched(db, self.reset(db, original))), reason='contract_error')
                    queue = {'queue_running': [], 'queue_pending': []}
                    native = history(blocked.preview)
                    item = native['prompt-1']
                    if change == 'queue_only': queue['queue_running'] = [prompt_tuple(blocked.preview)]
                    if change in ('queue_only', 'absence'): native = {}
                    if change == 'multiple_history': native.update(history(blocked.preview, 'prompt-2'))
                    if change == 'multiple_queue': queue['queue_running'] = [prompt_tuple(blocked.preview, 'prompt-2')]
                    if change == 'graph': item['prompt'][2]['856']['inputs']['seed'] += 1
                    if change == 'correlation': item['prompt'][3]['kinodel_portrait_v1']['input_digest'] = ZERO
                    if change == 'client': item['prompt'][3]['client_id'] = 'other'
                    if change == 'namespace': item['prompt'][3].pop('kinodel_portrait_v1')
                    if change == 'output_nodes': item['prompt'][4] = ['999']
                    if change == 'history_id': item['prompt'][1] = 'other'
                    if change == 'provider_error': item['status']['status_str'] = 'error'
                    if change in ('interrupted', 'execution_error'):
                        item['status']['messages'].append(['execution_interrupted' if change == 'interrupted' else 'execution_error', {}])
                    if change == 'incomplete': item['status']['completed'] = False
                    if change == 'missing_output': item['outputs'] = {}
                    if change == 'multiple_outputs': item['outputs']['865']['images'] *= 2
                    if change == 'unsafe': item['outputs']['865']['images'][0]['filename'] = '../evil.png'
                    if change == 'foreign': item['prompt'] = self.foreign_tuple(blocked.preview, 'prompt-1')
                    if change == 'owned_foreign_hint':
                        item['prompt'] = self.foreign_tuple(blocked.preview, 'prompt-1')[:4]
                        item['prompt'][3]['kinodel_anchor_unit_v1'] = {'attempt_id': blocked.preview.attempt_id}
                    if change == 'discovered_owned_quarantine':
                        queue['queue_running'] = [self.foreign_tuple(blocked.preview, 'prompt-1')[:4]]
                    with patch.object(candidates, 'import_anchor_unit_candidate', side_effect=AssertionError('Imported unproved ID')):
                        result = await self.tick(db, blocked, self.server(db, blocked, queue=queue, histories=native),
                                                 revalidate_contract=True)
                    self.assertEqual(result, blocked)
                    self.assertEqual(submissions._row(db, blocked.preview.job_id)[7], None)
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_candidates').fetchone(), (0,))
            self.assertTrue(all(r.method == 'GET' and not r.url.path.endswith('/view') for r in self.calls))

    async def test_unknown_contract_revalidation_expiry_learns_id_without_download_then_explicit_grant(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            blocked = submissions.block_portrait_submission(db, original.preview.job_id,
                **self.args(self.dispatched(db, original)), reason='contract_error')
            now = blocked.deadline_ms + 1
            with self.assertRaises(ValueError):
                submissions.authorize_portrait_output_recovery(db, blocked.preview.job_id, **self.args(blocked), now_ms=now)
            learned = await self.tick(db, blocked, self.server(db, blocked), revalidate_contract=True, now=now)
            self.assertEqual((learned.state, learned.reason, learned.prompt_id), ('blocked', 'deadline_exceeded', 'prompt-1'))
            assert learned.acceptance_evidence is not None
            self.assertEqual(learned.acceptance_evidence.kind, 'history')
            self.assertEqual(learned.acceptance_evidence, learned.evidence)
            self.assertEqual(learned.preview, original.preview)
            self.assertEqual(learned.deadline_ms, original.deadline_ms)
            self.assertIsNone(learned.output_recovery_deadline_ms)
            self.assertFalse(any(r.url.path.endswith('/view') for r in self.calls))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_candidates').fetchone(), (0,))
        with database.open_database(self.root) as db:
            restored = submissions.read_portrait_submission(db, learned.preview.job_id,
                expected_unit_digest=learned.preview.unit_input_digest, expected_wire_digest=learned.preview.wire_digest)
            granted = submissions.authorize_portrait_output_recovery(db, restored.preview.job_id, **self.args(restored), now_ms=now + 1)
            completed = await self.tick(db, granted, self.server(db, granted), now=now + 2)
            self.assertEqual(completed.state, 'completed')
            self.assertEqual(completed.acceptance_evidence, learned.acceptance_evidence)
            self.assertEqual(completed.preview, original.preview)
            self.assertEqual(completed.deadline_ms, original.deadline_ms)
            self.assertEqual(completed.output_recovery_deadline_ms, granted.output_recovery_deadline_ms)
            self.assertEqual([r.url.path for r in self.calls], [
                '/native/queue', '/native/history', '/native/queue', '/native/history/prompt-1', '/native/view'])
            self.assertTrue(all(r.method == 'GET' for r in self.calls))

    async def test_unknown_contract_revalidation_committed_history_reopens_after_preimport_cancellation(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            blocked = submissions.block_portrait_submission(db, original.preview.job_id,
                **self.args(self.dispatched(db, original)), reason='contract_error')
            with patch.object(self.worker, '_finish', side_effect=asyncio.CancelledError), self.assertRaises(asyncio.CancelledError):
                await self.tick(db, blocked, self.server(db, blocked), revalidate_contract=True)
            committed = submissions.read_portrait_submission(db, blocked.preview.job_id,
                expected_unit_digest=blocked.preview.unit_input_digest, expected_wire_digest=blocked.preview.wire_digest)
            self.assertEqual((committed.state, committed.reason, committed.prompt_id), ('accepted', None, 'prompt-1'))
            assert committed.acceptance_evidence is not None
            self.assertEqual(committed.acceptance_evidence.kind, 'history')
            self.assertEqual(committed.acceptance_evidence, committed.evidence)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_candidates').fetchone(), (0,))
        with database.open_database(self.root) as db:
            restored = submissions.read_portrait_submission(db, committed.preview.job_id,
                expected_unit_digest=committed.preview.unit_input_digest, expected_wire_digest=committed.preview.wire_digest)
            self.assertEqual(restored, committed)
            completed = await self.tick(db, restored, self.server(db, restored))
            self.assertEqual(completed.state, 'completed')
            self.assertEqual(completed.acceptance_evidence, committed.acceptance_evidence)
            self.assertEqual([r.url.path for r in self.calls], [
                '/native/queue', '/native/history', '/native/queue', '/native/history/prompt-1', '/native/view'])
            self.assertTrue(all(r.method == 'GET' for r in self.calls))

    async def test_unknown_contract_revalidation_revision_drift_at_reads_acceptance_and_import_cannot_overwrite(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            for stage in ('queue', 'history', 'acceptance', 'finish', 'view'):
                with self.subTest(stage=stage):
                    blocked = submissions.block_portrait_submission(db, original.preview.job_id,
                        **self.args(self.dispatched(db, self.reset(db, original))), reason='contract_error')
                    moved = []
                    def drift(record):
                        moved.append(submissions.record_submission_diagnostics(db, record.preview.job_id, **self.args(record),
                            diagnostics=[dict(kind='broken_job', source='queue', prompt_id='foreign-1', reason='native_tuple',
                                              digest=sha256_digest(b'concurrent diagnostic'))]))
                    handle = self.server(db, blocked)
                    def handler(request):
                        if request.url.path.endswith('/' + stage):
                            record = submissions.read_portrait_submission(db, blocked.preview.job_id,
                                expected_unit_digest=blocked.preview.unit_input_digest, expected_wire_digest=blocked.preview.wire_digest)
                            drift(record)
                        return handle(request)
                    actual_accept, actual_finish = submissions.record_portrait_acceptance, self.worker._finish
                    def accept(*args, **kwargs):
                        if stage == 'acceptance': drift(blocked)
                        return actual_accept(*args, **kwargs)
                    async def finish(db, client, record, *args):
                        if stage == 'finish': drift(record)
                        return await actual_finish(db, client, record, *args)
                    with patch.object(submissions, 'record_portrait_acceptance', side_effect=accept), \
                         patch.object(self.worker, '_finish', side_effect=finish), self.assertRaises(ValueError):
                        await self.tick(db, blocked, handler, revalidate_contract=True)
                    self.assertEqual(len(moved), 1)
                    saved = submissions.read_portrait_submission(db, blocked.preview.job_id,
                        expected_unit_digest=blocked.preview.unit_input_digest, expected_wire_digest=blocked.preview.wire_digest)
                    self.assertEqual(saved, moved[0])
                    self.assertEqual(saved.prompt_id, 'prompt-1' if stage in ('finish', 'view') else None)
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_candidates').fetchone(), (0,))
            self.assertTrue(all(r.method == 'GET' for r in self.calls))

    async def test_durable_output_grant_expired_original_same_prompt_reopens_completes_one_old_post(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            accepted = await self.tick(db, original, self.server(db, original))
            blocked = submissions.block_portrait_submission(db, accepted.preview.job_id, **self.args(accepted), reason='contract_error')
            grant = getattr(submissions, 'authorize_portrait_output_recovery', None)
            self.assertIsNotNone(grant, 'Durable output-only recovery grant is missing')
            now = blocked.deadline_ms + 1
            granted = grant(db, blocked.preview.job_id, **self.args(blocked), now_ms=now)
        with database.open_database(self.root) as db:
            restored = submissions.read_portrait_submission(db, granted.preview.job_id,
                expected_unit_digest=granted.preview.unit_input_digest, expected_wire_digest=granted.preview.wire_digest)
            native = history(restored.preview, subfolder='kinodel\\api')
            for field in ('cfg', 'denoise'):
                native['prompt-1']['prompt'][2]['856']['inputs'][field] = 1.0
            completed = await self.tick(db, restored, self.server(db, restored, histories=native), now=now + 1,
                                        revalidate_contract=True)
            self.assertEqual((completed.state, completed.prompt_id), ('completed', 'prompt-1'))
            self.assertEqual(completed.deadline_ms, original.deadline_ms)
            self.assertEqual(completed.acceptance_evidence, accepted.acceptance_evidence)
            self.assertEqual(completed.preview.wire_body, original.preview.wire_body)
            self.assertEqual(completed.output_recovery_deadline_ms, granted.output_recovery_deadline_ms)
            self.assertEqual(sum(r.method == 'POST' for r in self.calls), 1)
            self.assertEqual(await self.tick(db, completed, lambda _: self.fail('Completed HTTP')), completed)

    async def test_output_grant_expired_or_unsuccessful_history_cannot_download(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            grant = getattr(submissions, 'authorize_portrait_output_recovery', None)
            self.assertIsNotNone(grant, 'Durable output-only recovery grant is missing')
            for expired, failure in ((True, False), (False, True)):
                accepted = self.accepted(db, self.reset(db, original))
                blocked = submissions.block_portrait_submission(db, accepted.preview.job_id, **self.args(accepted), reason='contract_error')
                granted = grant(db, blocked.preview.job_id, **self.args(blocked), now_ms=blocked.deadline_ms + 1)
                native = history(granted.preview)
                if failure:
                    native['prompt-1']['status']['completed'] = False
                result = await self.tick(db, granted, self.server(db, granted, histories=native), revalidate_contract=True,
                    now=granted.output_recovery_deadline_ms if expired else granted.output_recovery_authorized_at_ms + 1)
                self.assertEqual(result.state, 'blocked')
                self.assertEqual(result.output_recovery_deadline_ms, granted.output_recovery_deadline_ms)
            self.assertFalse(any(r.method == 'POST' or r.url.path.endswith('/view') for r in self.calls))

    async def test_output_grant_does_not_heal_published_corruption_or_allow_import_after_download_deadline(self):
        async with self.committed() as (db, ref):
            original = self.job(db, ref)
            accepted = self.accepted(db, original)
            blocked = submissions.block_portrait_submission(db, accepted.preview.job_id, **self.args(accepted), reason='deadline_exceeded')
            grant = getattr(submissions, 'authorize_portrait_output_recovery', None)
            self.assertIsNotNone(grant, 'Durable output-only recovery grant is missing')
            granted = grant(db, blocked.preview.job_id, **self.args(blocked), now_ms=blocked.deadline_ms + 1)
            time_box = [granted.output_recovery_authorized_at_ms + 1]
            handle = self.server(db, granted)
            def crosses_deadline(request):
                result = handle(request)
                if request.url.path.endswith('/view'):
                    time_box[0] = granted.output_recovery_deadline_ms
                return result
            result = await self.tick(db, granted, crosses_deadline, clock_ms=lambda: time_box[0])
            self.assertEqual((result.state, result.reason), ('blocked', 'deadline_exceeded'))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM portrait_candidates').fetchone(), (0,))
            candidate = candidates.import_portrait_candidate(db, result.preview.job_id, result.preview.attempt_id,
                expected_unit_digest=result.preview.unit_input_digest, stream=io.BytesIO(png()), descriptor=dict(
                    node_id='865', history_key='images', index=0, filename='portrait.png', subfolder='', type='output', mime_type='image/png'))
            self.path(candidate).write_bytes(b'corrupt')
            self.calls.clear()
            broken = await self.tick(db, result, self.server(db, result), now=granted.output_recovery_authorized_at_ms + 1)
            self.assertEqual((broken.state, broken.reason), ('blocked', 'output_invalid'))
            self.assertFalse(any(r.url.path.endswith('/view') for r in self.calls))
            self.assertEqual(self.path(candidate).read_bytes(), b'corrupt')

    async def test_real_child_death_dispatch_response_history_candidate_boundaries_never_repost(self):
        outer_root = self.root
        script = '''
import asyncio, json, os, sys
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import httpx
from backend import database, portrait_worker as worker, portrait_submission_store as store, portrait_candidate_store as candidates
from tests.test_portrait_worker import response, history
root, job_id, input_digest, wire_digest, phase = sys.argv[1:]
counter = Path(root) / 'post-count'
async def run(db):
    record = store.read_portrait_submission(db, job_id, expected_unit_digest=input_digest, expected_wire_digest=wire_digest)
    def handle(request):
        assert not db.in_transaction
        if request.method == 'POST':
            with counter.open('ab') as f: f.write(b'P'); f.flush(); os.fsync(f.fileno())
            return response(dict(prompt_id='prompt-1', number=1, node_errors={}))
        if request.url.path.endswith('/queue'): return response(dict(queue_running=[], queue_pending=[]))
        if '/history' in request.url.path: return response(history(record.preview))
        from tests.test_portrait_candidate_store import png
        return response(png(), raw=True)
    await worker.tick_portrait_job(db, job_id, expected_unit_digest=input_digest, expected_wire_digest=wire_digest,
        expected_revision=record.revision, clock_ms=lambda: 1000002, transport=httpx.MockTransport(handle))
original_claim = store.claim_portrait_dispatch
def claim(*args, **kwargs):
    result = original_claim(*args, **kwargs)
    os._exit(91)
def before_accept(*args, **kwargs): os._exit(92)
original_transaction = candidates._transaction
@contextmanager
def before_candidate(db):
    with original_transaction(db):
        yield
        os._exit(93)
def before_complete(*args, **kwargs): os._exit(94)
with database.open_database(Path(root)) as db:
    if phase == 'dispatch':
        with patch.object(store, 'claim_portrait_dispatch', claim): asyncio.run(run(db))
    elif phase == 'response':
        with patch.object(store, 'record_portrait_acceptance', before_accept): asyncio.run(run(db))
    else:
        asyncio.run(run(db))
        target, replacement = (('_transaction', before_candidate) if phase == 'history' else ('complete_portrait_submission', before_complete))
        module = candidates if phase == 'history' else store
        with patch.object(module, target, replacement): asyncio.run(run(db))
raise AssertionError('Did not die at expected boundary')
'''
        for index, phase in enumerate(('dispatch', 'response', 'history', 'candidate'), 91):
            self.root = outer_root / phase
            async with self.committed() as (db, ref):
                record = self.job(db, ref)
            child = subprocess.run([sys.executable, '-B', '-c', script, str(self.root), record.preview.job_id,
                record.preview.unit_input_digest, record.preview.wire_digest, phase], capture_output=True, text=True, timeout=60)
            self.assertEqual(child.returncode, index, child.stdout + child.stderr)
            with database.open_database(self.root) as db:
                restored = submissions.read_portrait_submission(db, record.preview.job_id,
                    expected_unit_digest=record.preview.unit_input_digest, expected_wire_digest=record.preview.wire_digest)
                result = await self.tick(db, restored, self.server(db, restored, histories={} if phase == 'dispatch' else None))
                self.assertEqual(result.state, 'blocked' if phase == 'dispatch' else 'completed')
                counter = self.root / 'post-count'
                self.assertEqual(counter.read_bytes() if counter.exists() else b'', b'' if phase == 'dispatch' else b'P')
        self.root = outer_root


if __name__ == '__main__':
    unittest.main()
