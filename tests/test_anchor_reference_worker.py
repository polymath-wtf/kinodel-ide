"""Native reference + sheet boundary checks; HTTP always MockTransport, isolated roots."""

import copy
from email.parser import BytesParser
from email.policy import default
import importlib.util
import io
import json
import os
import subprocess
import sys
from typing import Any
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx

from backend import anchor_reference_store as refs, batch_store, database, portrait_candidate_store as candidates
from backend import portrait_submission_store as submissions, portrait_worker as native, render_job_store as jobs
from backend.config import resolve_comfyui_connection
from backend.domain import canonical_json, sha256_digest
from tests import test_anchor_reference_store as fixtures, test_batch_store as pins, test_story_wardrobe_api as sources
from tests.test_portrait_candidate_store import png
from tests.test_portrait_worker import ENDPOINT, NOW, ZERO, response


class AnchorReferenceWorkerTests(sources.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    source: Any = fixtures.AnchorReferenceStoreTests.source
    complete: Any = fixtures.AnchorReferenceStoreTests.complete
    parent_pair: Any = fixtures.AnchorReferenceStoreTests.parent_pair
    pin: Any = pins.BatchStoreTests.pin
    context: Any = pins.BatchStoreTests.context
    parents: Any = pins.BatchStoreTests.parents
    prepare: Any = pins.BatchStoreTests.prepare
    path: Any = pins.BatchStoreTests.path
    offline: Any = pins.BatchStoreTests.offline
    sheet: Any = fixtures.AnchorReferenceStoreTests.sheet
    authorize: Any = fixtures.AnchorReferenceStoreTests.authorize
    args: Any = fixtures.AnchorReferenceStoreTests.args
    role: Any = fixtures.AnchorReferenceStoreTests.role

    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('backend.anchor_reference_worker'), 'Native reference worker is missing')
        from backend import anchor_reference_worker
        self.worker = anchor_reference_worker
        self.refs = refs
        self.store = batch_store
        self.profile = pins.production_catalog()['image_only']['profiles'][0]['pin']
        env = patch.dict(os.environ, {'COMFYUI_LOCAL_ENDPOINT': ENDPOINT, 'COMFYUI_AUTH_TOKEN': 'private-token'})
        env.start()
        self.addCleanup(env.stop)
        self.calls = []
        self.uploads = []
        self.remotes = {}
        self.prompt_wire: dict[str, Any] | None = None
        self.upload_lost = self.prompt_lost = False
        self.receipt_change = None
        self.input_response = None
        self.input_hook = None
        self.native_floats = False

    def batch(self, db, ref, **changes):
        args: dict[str, Any] = dict(image_size=dict(width=512, height=512), connection=dict(connection='local',
                                   endpoint_digest='sha256:' + resolve_comfyui_connection('local').endpoint_digest))
        args.update(changes)
        return self.pin(db, ref, **args)

    def imported(self, db, batch, key, *, complete=True):
        unit = self.prepare(db, batch, key)
        job = jobs.create_anchor_unit_job(db, batch.batch_id, key, expected_unit_digest=unit.input_digest,
                                         parent_bindings=unit.prepared_input.parent_bindings)
        candidate = candidates.import_anchor_unit_candidate(db, job.job_id, job.attempt_id,
            expected_unit_digest=unit.input_digest, descriptor=dict(node_id='865', history_key='images', index=0,
                filename=key + '.png', subfolder='', type='output', mime_type='image/png'),
            stream=io.BytesIO(png(color='purple' if job.kind == 'portrait' else 'green')))
        if complete:
            self.complete(db, job, unit, candidate)
        return unit, job, candidate

    def handler(self, db):
        def handle(request):
            self.assertFalse(db.in_transaction, 'SQL transaction crossed native I/O')
            self.calls.append(request)
            route = request.url.path.removeprefix('/native/')
            if request.method == 'POST' and route == 'upload/image':
                message = BytesParser(policy=default).parsebytes(
                    ('Content-Type: ' + request.headers['content-type'] + '\r\nMIME-Version: 1.0\r\n\r\n').encode() + request.content)
                fields = {part.get_param('name', header='content-disposition'): part for part in message.iter_parts()}
                self.assertEqual(set(fields), {'image', 'type', 'overwrite', 'subfolder'})
                image = fields['image']
                self.assertEqual(image.get_content_type(), 'image/png')
                name = image.get_filename()
                folder_body = fields['subfolder'].get_payload(decode=True)
                assert name is not None and type(folder_body) is bytes
                folder = folder_body.decode()
                self.assertEqual(fields['type'].get_payload(decode=True), b'input')
                self.assertEqual(fields['overwrite'].get_payload(decode=True), b'false')
                body = image.get_payload(decode=True)
                assert type(body) is bytes
                role = 'portrait' if '-portrait-' in name else 'background'
                self.assertEqual(body, png(color='purple' if role == 'portrait' else 'green'))
                self.uploads.append((role, name, folder, body))
                actual = dict(name=name[:-4] + ' (1).png', subfolder=folder.replace('/', '\\'), type='input')
                self.remotes[actual['name'], actual['subfolder']] = body
                if self.upload_lost:
                    raise httpx.ReadError('private-token lost upload response')
                return self.receipt_change(actual) if self.receipt_change else response(actual)
            if route == 'view' and request.url.params['type'] == 'input':
                if self.input_hook:
                    self.input_hook(request)
                if self.input_response:
                    return self.input_response(request)
                body = self.remotes.get((request.url.params['filename'], request.url.params['subfolder']))
                return response(body, raw=True) if body else response(b'', status=404, raw=True)
            if route == 'prompt' and request.method == 'POST':
                self.prompt_wire = json.loads(request.content)
                if self.prompt_lost:
                    raise httpx.ReadError('private-token lost prompt response')
                return response(dict(prompt_id='sheet-1', number=1, node_errors={}))
            if route == 'queue':
                return response(dict(queue_running=[], queue_pending=[]))
            if route in ('history', 'history/sheet-1'):
                assert self.prompt_wire is not None
                graph = copy.deepcopy(self.prompt_wire['prompt'])
                if self.native_floats:
                    schemas = pins.installed_schemas()
                    for node in graph.values():
                        declarations = schemas[node['class_type']]['input']
                        definitions = {**declarations.get('required', {}), **declarations.get('optional', {})}
                        for field, value in list(node['inputs'].items()):
                            declaration = definitions.get(field)
                            if type(value) is int and type(declaration) is list and declaration[0] == 'FLOAT':
                                node['inputs'][field] = float(value)
                return response({'sheet-1': dict(prompt=[1, 'sheet-1', graph,
                    {**self.prompt_wire['extra_data'], 'client_id': self.prompt_wire['client_id']}, ['494']],
                    outputs={'494': {'images': [dict(filename='sheet.png', subfolder='kinodel\\output', type='output')]}},
                    status=dict(status_str='success', completed=True, messages=[['execution_success', {}]]))})
            if route == 'view' and request.url.params['type'] == 'output':
                self.assertEqual(request.url.params['subfolder'], 'kinodel\\output')
                return response(png(color='blue'), raw=True)
            self.fail('Unexpected native route: ' + route)
        return handle

    async def tick(self, db, record):
        return await self.worker.tick_anchor_references(db, record.intent.job_id, **self.args(record),
            transport=httpx.MockTransport(self.handler(db)))

    async def finalized(self, db, unit, job, *, folder='kinodel/parents'):
        record = self.authorize(db, unit, job, subfolder=folder)
        first = await self.tick(db, record)
        self.assertEqual([item.state for item in first.references], ['verified', 'ready'])
        return await self.tick(db, first)

    def authorize_sheet(self, db, unit, job):
        preview = submissions.preview_anchor_unit_submission(db, job.job_id, expected_unit_digest=unit.input_digest)
        return submissions.authorize_anchor_unit_submission(db, job.job_id, expected_unit_digest=unit.input_digest,
            expected_wire_digest=preview.wire_digest, accepted_at_ms=NOW)

    async def sheet_tick(self, db, record, *, now=NOW + 2):
        return await native.tick_anchor_unit_job(db, record.preview.job_id,
            expected_unit_digest=record.preview.unit_input_digest, expected_wire_digest=record.preview.wire_digest,
            expected_revision=record.revision, clock_ms=lambda: now, transport=httpx.MockTransport(self.handler(db)))

    async def test_ordered_actual_multipart_receipt_get_verification_final_offline_reopen(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            before = canonical_json(unit.prepared_input)
            client = self.worker.httpx.AsyncClient
            with patch.object(self.worker.httpx, 'AsyncClient', wraps=client) as opened:
                final = await self.finalized(db, unit, job)
            self.assertFalse(opened.call_args.kwargs['trust_env'])
            self.assertFalse(opened.call_args.kwargs['follow_redirects'])
            self.assertIs(opened.call_args.kwargs['verify'], True)
            self.assertEqual(opened.call_args.kwargs['timeout'].connect, 5)
            self.assertEqual(opened.call_args.kwargs['timeout'].read, 15)
            self.assertEqual(final.state, 'finalized')
            self.assertEqual([entry[0] for entry in self.uploads], ['portrait', 'background'])
            self.assertEqual([(r.method, r.url.path) for r in self.calls],
                [('POST', '/native/upload/image'), ('GET', '/native/view')] * 2)
            self.assertTrue(all(r.headers['accept-encoding'] == 'identity' for r in self.calls))
            self.assertEqual(self.path(unit).read_bytes(), before)
            self.assertIsNone(submissions._row(db, job.job_id), 'Reference authorization is not prompt authorization')
        with database.open_database(self.root) as db, self.offline():
            self.assertEqual(await self.tick(db, final), final)
            preview = submissions.preview_anchor_unit_submission(db, job.job_id, expected_unit_digest=unit.input_digest)
            wire = json.loads(preview.wire_body)
            assert final.final is not None
            self.assertEqual(wire['prompt'], json.loads(final.final.graph_json))
            correlation = wire['extra_data']['kinodel_anchor_unit_v1']
            self.assertEqual((correlation['kind'], correlation['final_reference_digest'], correlation['reference_intent_digest']),
                ('sheet', sha256_digest(canonical_json(final)), final.intent_digest))
            self.assertEqual(correlation['reference_receipt_digests'],
                [item.receipt.digest for item in final.references if item.receipt is not None])
            self.assertEqual(len(self.calls), 4)

    async def test_bounded_call_timeout_after_upload_is_ambiguous_no_retry(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            record = self.authorize(db, unit, job)
            self.receipt_change = lambda actual: response(actual, pause=.1)
            with patch.object(native, 'REQUEST_TIMEOUT', .01):
                blocked = await self.tick(db, record)
            self.assertEqual(self.role(blocked, 'portrait').reason, 'acceptance_unknown')
            self.assertEqual(await self.tick(db, blocked), blocked)
            self.assertEqual(len(self.uploads), 1)

    async def test_bad_upload_receipt_protocol_and_names_never_guess_view_or_prompt(self):
        async with self.source() as (db, ref):
            cases = [lambda a: response({**a, 'name': 'foreign.png'}), lambda a: response({**a, 'subfolder': '../evil'}),
                     lambda a: response({**a, 'type': 'output'}), lambda a: response({'name': a['name']}),
                     lambda a: response(a, status=500), lambda a: response(a, headers={'content-type': 'text/plain'}),
                     lambda a: response(a, headers={'content-encoding': 'gzip'}),
                     lambda a: response(a, headers={'content-length': str(16 * 1024 * 1024 + 1)}),
                     lambda a: response(b'{"name":"a","name":"b"}', raw=True, headers={'content-type': 'application/json'}),
                     lambda a: response(a, partial=0)]
            for index, change in enumerate(cases):
                self.calls.clear()
                self.receipt_change = change
                _, unit, job, _ = self.sheet(db, ref, activation_id=sha256_digest(str(index).encode()))
                record = self.authorize(db, unit, job)
                blocked = await self.tick(db, record)
                self.assertEqual(self.role(blocked, 'portrait').state, 'blocked_sent')
                self.assertIsNone(self.role(blocked, 'portrait').receipt)
                self.assertEqual(len(self.calls), 1)
                self.assertEqual(await self.tick(db, blocked), refs.read_anchor_reference_transfer(db, job.job_id,
                    **self.args(blocked, revision=False)))
                self.assertEqual(len(self.calls), 1)
                self.assertIsNone(submissions._row(db, job.job_id))

    async def test_lost_upload_response_reopen_never_second_post_or_synthetic_receipt(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            record = self.authorize(db, unit, job)
            self.upload_lost = True
            blocked = await self.tick(db, record)
            self.assertEqual((self.role(blocked, 'portrait').state, self.role(blocked, 'portrait').reason),
                             ('blocked_sent', 'acceptance_unknown'))
        with database.open_database(self.root) as db, self.offline():
            self.assertEqual(await self.tick(db, blocked), blocked)
            self.assertEqual(len(self.calls), 1)
            self.assertIsNone(self.role(blocked, 'portrait').receipt)

    async def test_invalid_receipt_block_reopen_preserves_exact_fact_offline(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            record = self.authorize(db, unit, job)
            self.receipt_change = lambda actual: response({**actual, 'name': 'foreign.png'})
            blocked = await self.tick(db, record)
            self.assertEqual((self.role(blocked, 'portrait').state, self.role(blocked, 'portrait').reason),
                             ('blocked_sent', 'receipt_invalid'))
            self.assertEqual((blocked.revision, self.role(blocked, 'portrait').dispatch_revision), (2, 1))
            self.assertIsNone(self.role(blocked, 'portrait').receipt)
            saved = refs._row(db, job.job_id)
        configurations = [dict(COMFYUI_LOCAL_ENDPOINT='https://foreign.test/', COMFYUI_AUTH_TOKEN='rotated-token'),
                          dict(COMFYUI_LOCAL_ENDPOINT='', COMFYUI_AUTH_TOKEN='',
                               COMFYUI_CA_FILE=str(self.root / 'missing-ca.pem'))]
        for configuration in configurations:
            with database.open_database(self.root) as db, \
                    patch.dict(os.environ, configuration), self.offline():
                before = db.total_changes
                for _ in range(2):
                    self.assertEqual(await self.tick(db, blocked), blocked)
                    self.assertEqual(refs._row(db, job.job_id), saved)
                with self.assertRaisesRegex(self.worker.AnchorReferenceWorkerError, 'reference_revision_conflict'):
                    await self.worker.tick_anchor_references(db, job.job_id,
                        **{**self.args(blocked), 'expected_revision': blocked.revision - 1},
                        transport=httpx.MockTransport(self.handler(db)))
                self.assertEqual(db.total_changes, before)
                self.assertEqual(refs._row(db, job.job_id), saved)
                self.assertEqual([r.method for r in self.calls], ['POST'])
                self.assertEqual(len(self.uploads), 1)

    async def test_reopened_dispatch_without_receipt_blocks_once_then_stays_offline(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            record = self.authorize(db, unit, job)
            dispatched = refs.claim_anchor_reference_upload(db, job.job_id, role='portrait', **self.args(record))
        with database.open_database(self.root) as db, self.offline():
            before = db.total_changes
            blocked = await self.tick(db, dispatched)
            self.assertEqual(db.total_changes, before + 1)
            self.assertEqual((blocked.revision, blocked.intent, blocked.intent_digest),
                             (dispatched.revision + 1, dispatched.intent, dispatched.intent_digest))
            self.assertEqual((self.role(blocked, 'portrait').state, self.role(blocked, 'portrait').reason),
                             ('blocked_sent', 'acceptance_unknown'))
            self.assertEqual(self.role(blocked, 'portrait').dispatch_revision,
                             self.role(dispatched, 'portrait').dispatch_revision)
            self.assertIsNone(self.role(blocked, 'portrait').receipt)
            saved = refs._row(db, job.job_id)
        with database.open_database(self.root) as db, self.offline():
            before = db.total_changes
            for _ in range(2):
                self.assertEqual(await self.tick(db, blocked), blocked)
                self.assertEqual(refs._row(db, job.job_id), saved)
            self.assertEqual(db.total_changes, before)
            self.assertFalse(self.calls)
            self.assertFalse(self.uploads)

    async def test_saved_receipt_interrupted_download_reopen_get_retry_not_upload(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            record = self.authorize(db, unit, job)
            self.input_response = lambda request: response(self.remotes[request.url.params['filename'], request.url.params['subfolder']],
                                                           raw=True, partial=0)
            blocked = await self.tick(db, record)
            self.assertEqual(self.role(blocked, 'portrait').reason, 'remote_invalid')
            self.assertIsNotNone(self.role(blocked, 'portrait').receipt)
        with database.open_database(self.root) as db:
            self.input_response = None
            verified = await self.tick(db, blocked)
            self.assertEqual(self.role(verified, 'portrait').state, 'verified')
            self.assertEqual([r.method for r in self.calls], ['POST', 'GET', 'GET'])

    async def test_invalid_remote_original_mime_encoding_partial_digest_never_verifies(self):
        async with self.source() as (db, ref):
            variants = [lambda _: response(png(color='red'), raw=True),
                        lambda _: response(b'not PNG', raw=True),
                        lambda _: response(png(), raw=True, headers={'content-type': 'text/plain'}),
                        lambda _: response(png(), raw=True, headers={'content-encoding': 'gzip'}),
                        lambda _: response(png(), raw=True, headers={'content-range': 'bytes 0-4/10'}),
                        lambda _: response(png(), raw=True, headers={'content-length': str(candidates.MAX_PNG_BYTES + 1)}),
                        lambda _: response(png(), raw=True, headers={'content-length': str(len(png()) + 1)})]
            for index, change in enumerate(variants):
                self.input_response = change
                _, unit, job, _ = self.sheet(db, ref, activation_id=sha256_digest(str(index).encode()))
                record = self.authorize(db, unit, job)
                blocked = await self.tick(db, record)
                self.assertEqual(self.role(blocked, 'portrait').reason, 'remote_invalid')
                self.assertIsNone(self.role(blocked, 'portrait').verification)
                self.assertIsNone(blocked.final)

    async def test_missing_or_changed_remote_before_sheet_first_prompt_leaves_authorized_unsent(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            final = await self.finalized(db, unit, job)
            record = self.authorize_sheet(db, unit, job)
            remote = dict(self.remotes)
            for values in ({}, {key: png(color='red') for key in remote}):
                self.remotes = values
                changes = db.total_changes
                with self.assertRaisesRegex(ValueError, 'readiness|reference') as error:
                    await self.sheet_tick(db, record)
                self.assertNotIn('private-token', str(error.exception))
                self.assertEqual(db.total_changes, changes)
                self.assertEqual(submissions.read_anchor_unit_submission(db, job.job_id,
                    expected_unit_digest=unit.input_digest, expected_wire_digest=record.preview.wire_digest), record)
                self.assertFalse(any(r.url.path.endswith('/prompt') for r in self.calls))
            self.remotes = remote
            accepted = await self.sheet_tick(db, record)
            self.assertEqual(accepted.state, 'accepted')
            self.assertEqual(sum(r.url.path.endswith('/prompt') for r in self.calls), 1)
            self.assertEqual(sha256_digest(canonical_json(final)), record.preview.final_reference_digest)

    async def test_one_sheet_prompt_exact_final_graph_float_history_494_import_offline_completed(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            final = await self.finalized(db, unit, job)
            record = self.authorize_sheet(db, unit, job)
            self.calls.clear()
            accepted = await self.sheet_tick(db, record)
            self.assertEqual([(r.method, r.url.params.get('type')) for r in self.calls],
                             [('GET', 'input'), ('GET', 'input'), ('POST', None)])
            assert self.prompt_wire is not None and final.final is not None
            self.assertEqual(self.prompt_wire['prompt'], json.loads(final.final.graph_json))
            self.assertEqual(self.calls[-1].content, record.preview.wire_body)
            self.assertEqual(json.loads(unit.prepared_input.image_pin_json)['settings']['seed'], final.final.seed)
            self.remotes.clear()  # Accepted prompt reconciliation does NOT require inputs still present.
            self.native_floats = True
            completed = await self.sheet_tick(db, accepted)
            self.assertEqual(completed.state, 'completed')
            assert completed.candidate_id is not None
            candidate = candidates.read_anchor_unit_candidate(db, completed.candidate_id, expected_unit_digest=unit.input_digest)
            self.assertEqual((candidate.descriptor.node_id, candidate.descriptor.index), ('494', 0))
            self.assertEqual(self.path(candidate).read_bytes(), png(color='blue'))
        with database.open_database(self.root) as db, self.offline():
            self.assertEqual(await self.sheet_tick(db, completed), completed)
            self.assertEqual(candidates.read_anchor_unit_candidate(db, candidate.candidate_id,
                expected_unit_digest=unit.input_digest), candidate)
            self.assertEqual(sum(r.method == 'POST' for r in self.calls), 1)

    async def test_lost_sheet_response_reconcile_without_remote_inputs_never_second_prompt(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            await self.finalized(db, unit, job)
            record = self.authorize_sheet(db, unit, job)
            self.prompt_lost = True
            blocked = await self.sheet_tick(db, record)
            self.assertEqual((blocked.state, blocked.reason), ('blocked', 'acceptance_unknown'))
        with database.open_database(self.root) as db:
            self.remotes.clear()
            completed = await self.sheet_tick(db, blocked)
            self.assertEqual(completed.state, 'completed')
            self.assertEqual(sum(r.url.path.endswith('/prompt') for r in self.calls), 1)

    async def test_parent_corruption_cancel_endpoint_and_revision_before_effects_no_mutation(self):
        async with self.source() as (db, ref):
            _, unit, job, parents = self.sheet(db, ref)
            record = self.authorize(db, unit, job)
            for changes in (dict(expected_revision=9), dict(expected_project_id=str(uuid4()))):
                before = db.total_changes
                with self.assertRaises(ValueError):
                    await self.worker.tick_anchor_references(db, job.job_id, **{**self.args(record), **changes},
                        transport=httpx.MockTransport(self.handler(db)))
                self.assertEqual(db.total_changes, before)
            with patch.dict(os.environ, {'COMFYUI_LOCAL_ENDPOINT': 'https://foreign.test/'}), self.assertRaises(ValueError):
                await self.tick(db, record)
            path = self.path(parents[0][2])
            original = path.read_bytes()
            path.write_bytes(b'corrupt')
            before = db.total_changes
            with self.assertRaises((OSError, ValueError)):
                await self.tick(db, record)
            self.assertEqual(db.total_changes, before)
            path.write_bytes(original)
            work = str(uuid4())
            db.execute("INSERT INTO execution_work (work_id,execution_id,kind,source_id,payload_digest,status) "
                       "VALUES (?,?,'cancel','cancel-before-effect',?,'pending')", (work, ref.execution_id, ZERO))
            db.execute("INSERT INTO execution_controls VALUES (?,'cancel-before-effect','cancel',?,NULL)", (ref.execution_id, work))
            before = db.total_changes
            with self.assertRaises(ValueError):
                await self.tick(db, record)
            self.assertEqual(db.total_changes, before)
            self.assertFalse(self.calls)
            with patch.object(refs, 'read_anchor_reference_transfer', side_effect=OSError('disk unavailable')), self.assertRaises(OSError):
                await self.tick(db, record)

    async def test_source_or_revision_changed_across_child_remote_get_cannot_claim_prompt(self):
        async with self.source() as (db, ref):
            _, unit, job, parents = self.sheet(db, ref)
            await self.finalized(db, unit, job)
            record = self.authorize_sheet(db, unit, job)
            path = self.path(parents[0][2])
            original = path.read_bytes()
            self.input_hook = lambda _: path.write_bytes(b'corrupt')
            with self.assertRaises((OSError, ValueError)):
                await self.sheet_tick(db, record)
            self.assertEqual(submissions._row(db, job.job_id)[6], 'authorized')
            self.assertFalse(any(r.url.path.endswith('/prompt') for r in self.calls))
            path.write_bytes(original)
            def changed_revision(_):
                self.input_hook = None
                submissions.fail_anchor_unit_submission(db, job.job_id, expected_unit_digest=unit.input_digest,
                    expected_wire_digest=record.preview.wire_digest, expected_revision=record.revision, reason='deadline_exceeded')
            self.input_hook = changed_revision
            with self.assertRaises(ValueError):
                await self.sheet_tick(db, record)
            self.assertEqual(submissions._row(db, job.job_id)[6], 'failed')
            self.assertFalse(any(r.url.path.endswith('/prompt') for r in self.calls))

    async def test_sheet_history_must_match_final_reference_correlation_not_preupload_graph(self):
        async with self.source() as (db, ref):
            _, unit, job, _ = self.sheet(db, ref)
            await self.finalized(db, unit, job)
            record = self.authorize_sheet(db, unit, job)
            accepted = await self.sheet_tick(db, record)
            assert self.prompt_wire is not None
            self.prompt_wire['prompt'] = json.loads(unit.prepared_input.image_pin_json)['graph']
            self.prompt_wire['extra_data']['kinodel_anchor_unit_v1']['final_reference_digest'] = ZERO
            blocked = await self.sheet_tick(db, accepted)
            self.assertEqual((blocked.state, blocked.reason), ('blocked', 'contract_error'))
            self.assertEqual(blocked.acceptance_evidence, accepted.acceptance_evidence)
            self.assertEqual(sum(r.url.path.endswith('/prompt') for r in self.calls), 1)
            self.assertFalse(any(r.url.params.get('type') == 'output' for r in self.calls))

    async def test_real_process_death_after_reference_claim_or_receipt_never_reuploads(self):
        script = '''
import asyncio,os,sys
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import httpx
from backend import database,anchor_reference_worker as worker,anchor_reference_store as store
from tests.test_portrait_worker import response
root,project,job,input_digest,intent_digest,phase=sys.argv[1:]
transaction=store._transaction
@contextmanager
def die(db):
    with transaction(db): yield
    record=store._stored(store._row(db,job))
    if phase=='claim' and record.references[0].state=='dispatching': os._exit(91)
    if phase=='receipt' and record.references[0].state=='received': os._exit(92)
with database.open_database(Path(root)) as db:
    record=store.read_anchor_reference_transfer(db,job,expected_project_id=project,expected_unit_digest=input_digest,expected_intent_digest=intent_digest)
    def handle(request):
        with (Path(root)/'upload-count').open('ab') as f: f.write(b'U'); f.flush(); os.fsync(f.fileno())
        item=record.intent.references[0]
        return response(dict(name=item.name,subfolder=item.subfolder,type='input'))
    with patch.object(store,'_transaction',side_effect=die):
        asyncio.run(worker.tick_anchor_references(db,job,expected_project_id=project,expected_unit_digest=input_digest,
            expected_intent_digest=intent_digest,expected_revision=record.revision,transport=httpx.MockTransport(handle)))
raise AssertionError('Expected death at reference boundary')
'''
        outer = self.root
        for phase, code in (('claim', 91), ('receipt', 92)):
            self.root = outer / phase
            async with self.source() as (db, ref):
                _, unit, job, _ = self.sheet(db, ref)
                record = self.authorize(db, unit, job)
            child = subprocess.run([sys.executable, '-B', '-c', script, str(self.root), self.project, job.job_id,
                unit.input_digest, record.intent_digest, phase], capture_output=True, text=True, timeout=60)
            self.assertEqual(child.returncode, code, child.stdout + child.stderr)
            with database.open_database(self.root) as db:
                current = refs.read_anchor_reference_transfer(db, job.job_id, **self.args(record, revision=False))
                self.calls.clear()
                self.input_response = lambda _: response(png(), raw=True)
                result = await self.tick(db, current)
                self.assertEqual(self.role(result, 'portrait').state, 'blocked_sent' if phase == 'claim' else 'verified')
                self.assertFalse(any(r.method == 'POST' for r in self.calls))
                counter = self.root / 'upload-count'
                self.assertEqual(counter.read_bytes() if counter.exists() else b'', b'' if phase == 'claim' else b'U')
        self.root = outer
