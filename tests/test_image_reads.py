"""7.3B guarded HTTP reads on real storage; no lifecycle or native effects."""

from contextlib import asynccontextmanager
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
from time import perf_counter
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
from uuid import uuid4

import httpx

from backend import batch_store, image_group_results as results, image_group_store as groups
from backend import render_job_store as jobs
from backend.api import create_app
from backend.domain import canonical_json, sha256_digest
from tests import test_image_group_results as storage
from tests.test_story_wardrobe_api import WardrobeFixtures
from tests import test_story_wardrobe_api as fixtures
from tests.test_story_cast import draft
from tests.test_wardrobe_compact_v2 import compact_draft


ZERO = 'sha256:' + '0' * 64


class ImageReadTests(WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    source = storage.ImageGroupResultTests.source
    arguments = storage.ImageGroupResultTests.arguments
    context = storage.ImageGroupResultTests.context
    offline = storage.ImageGroupResultTests.offline
    complete = storage.ImageGroupResultTests.complete
    start = storage.ImageGroupResultTests.start
    unit = storage.ImageGroupResultTests.unit
    publish = storage.ImageGroupResultTests.publish
    retry = storage.ImageGroupResultTests.retry

    def setUp(self):
        super().setUp()
        self.results = results
        from backend.production import production_catalog
        self.profile = production_catalog()['image_only']['profiles'][0]['pin']

    @asynccontextmanager
    async def client(self, runtime):
        app = create_app(self.root, character_root=self.library)
        app.state.runtime = runtime
        # No lifespan: HTTP GETs must not acquire/run/reconcile the worker.
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('127.0.0.1', 321)),
                                     base_url='http://127.0.0.1:8765') as client:
            await client.get('/api/session')
            yield client

    def images_url(self, receipt):
        return f'/api/executions/{receipt.execution_id}/images'

    def selector(self, url, **changes):
        parts = urlsplit(url)
        query = {key: values[0] for key, values in parse_qs(parts.query).items()}
        query.update(changes)
        return urlunsplit(parts._replace(query=urlencode(query)))

    def read_only(self, db):
        # Also catches accidental lifecycle maintenance, not just row-count drift.
        db.set_authorizer(lambda action, *args: sqlite3.SQLITE_DENY if action in (
            sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
            sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_ALTER_TABLE) else sqlite3.SQLITE_OK)

    def test_opaque_unit_key_is_a_query_selector_not_a_filesystem_path(self):
        from backend.image_reads import ImageMediaRefV1, _original_url
        unit_key = '../face/../?#\\ユニット'
        ref = ImageMediaRefV1(execution_id=self.project, group_id=ZERO, unit_key=unit_key,
            job_id=ZERO, attempt_id=ZERO, unit_input_digest=ZERO, origin_execution_id=self.project,
            candidate_id=ZERO, candidate_digest=ZERO, candidate_metadata_digest=ZERO)
        parts = urlsplit(_original_url(ref))
        self.assertEqual(parts.path, f'/api/executions/{self.project}/images/candidates/{ZERO.replace(":", "%3A")}/original')
        self.assertEqual(parse_qs(parts.query)['unit_key'], [unit_key])

    async def test_partial_original_full_order_and_only_published_validated_complete(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            async with self.client(runtime) as client:
                response = await client.get(self.images_url(receipt))
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual([u['reason'] for u in response.json()['units']], ['unstarted'] * 3)
                first = self.unit(runtime.db, receipt.execution_id, 0)
                changes = runtime.db.total_changes
                with self.offline():
                    projection = (await client.get(self.images_url(receipt))).json()
                    self.assertEqual((projection['total_units'], projection['available_units']), (3, 1))
                    self.assertEqual([u['unit_key'] for u in projection['units']], ['face-0', 'location', 'sheet-0'])
                    self.assertIsNone(projection['result'])
                    original = projection['units'][0]['original']
                    response = await client.get(original['url'])
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.content, (self.root / first[2].uri.removeprefix('kinodel://')).read_bytes())
                    self.assertEqual(response.headers['content-type'], 'image/png')
                    self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
                    self.assertEqual(int(response.headers['content-length']), original['byte_length'])
                    self.assertEqual(original['media_ref']['candidate_id'], first[2].candidate_id)
                    self.assertEqual((original['width'], original['height'], original['mime_type']), (512, 512, 'image/png'))
                self.assertEqual(runtime.db.total_changes, changes)
                for i in (1, 2):
                    self.unit(runtime.db, receipt.execution_id, i)
                self.assertIsNone((await client.get(self.images_url(receipt))).json()['result'])
                manifest = self.publish(runtime.db, receipt)
                changes = runtime.db.total_changes
                self.read_only(runtime.db)
                projection = (await client.get(self.images_url(receipt))).json()
                self.assertEqual(projection['result'], dict(result_id=manifest.result_id, digest=manifest.digest,
                                                            status='complete', issue=None))
                self.assertEqual(projection['available_units'], 3)
                for unit in projection['units']:
                    self.assertTrue(unit['available'])
                    self.assertIsNone(unit['reason'])
                    self.assertEqual((await client.get(unit['original']['url'])).status_code, 200)
                self.assertEqual(runtime.db.total_changes, changes)
                wire = json.dumps(projection)
                for private in ('kinodel://', str(self.root), 'endpoint', 'wire_body', 'filename', 'subfolder', 'provider'):
                    self.assertNotIn(private, wire)
                runtime.db.set_authorizer(None)

    async def test_failed_partial_and_noncompleted_import_are_not_original_authority(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            first = self.unit(runtime.db, receipt.execution_id, 0)
            failed = self.unit(runtime.db, receipt.execution_id, 1, finish='failed')
            manifest = self.publish(runtime.db, receipt, status='failed', failed_unit_key='location')
            async with self.client(runtime) as client:
                projection = (await client.get(self.images_url(receipt))).json()
                self.assertEqual(projection['available_units'], 1)
                self.assertEqual(projection['result']['status'], 'failed')
                self.assertEqual(projection['result']['digest'], manifest.digest)
                self.assertEqual([u['reason'] for u in projection['units']], [None, 'not_completed', 'unstarted'])
                self.assertIsNone(projection['units'][1]['original'])
                first_url = projection['units'][0]['original']['url']
                forged = first_url.replace('face-0', 'location').replace(first[2].candidate_id.replace(':', '%3A'),
                                                                       failed[2].candidate_id.replace(':', '%3A'))
                forged = self.selector(forged, job_id=failed[0].job_id, attempt_id=failed[0].attempt_id,
                    unit_input_digest=failed[0].unit_input_digest, candidate_digest=failed[2].digest,
                    candidate_metadata_digest=sha256_digest(failed[2].metadata_body))
                self.assertIn((await client.get(forged)).status_code, (404, 409))
                pending = await self.start(runtime, ref, key='noncompleted')
                imported = self.unit(runtime.db, pending.execution_id, 0, finish='accepted')
                projection = (await client.get(self.images_url(pending))).json()
                self.assertEqual(projection['units'][0]['reason'], 'not_completed')
                forged = first_url.replace(receipt.execution_id, pending.execution_id).replace(
                    first[2].candidate_id.replace(':', '%3A'), imported[2].candidate_id.replace(':', '%3A'))
                forged = self.selector(forged, group_id=pending.group_id, job_id=imported[0].job_id,
                    attempt_id=imported[0].attempt_id, unit_input_digest=imported[0].unit_input_digest,
                    origin_execution_id=pending.execution_id, candidate_digest=imported[2].digest,
                    candidate_metadata_digest=sha256_digest(imported[2].metadata_body))
                self.assertIn((await client.get(forged)).status_code, (404, 409))

    async def test_retry_retains_two_origins_and_new_sheet_exact_attempt_no_following(self):
        async with self.source() as (runtime, ref, _):
            initial = await self.start(runtime, ref)
            original = [self.unit(runtime.db, initial.execution_id, i,
                                  finish='failed' if i == 2 else 'completed') for i in range(3)]
            failed_result = self.publish(runtime.db, initial, status='failed', failed_unit_key='sheet-0')
            retry = await self.retry(runtime, initial, failed_result)
            binding, job, _, facts = original[2]
            allocated = jobs.allocate_anchor_unit_retry(runtime.db, job.job_id,
                expected_unit_digest=binding.unit_input_digest, previous_attempt_id=job.attempt_id,
                expected_previous_wire_digest=facts.preview.wire_digest, expected_previous_revision=facts.revision,
                retry_trigger_id=retry.group_id)
            new_sheet = self.unit(runtime.db, retry.execution_id, 2, job=allocated)
            self.publish(runtime.db, retry)
            async with self.client(runtime) as client:
                old = (await client.get(self.images_url(initial))).json()
                current = (await client.get(self.images_url(retry))).json()
                self.assertEqual((old['result']['status'], current['result']['status']), ('failed', 'complete'))
                self.assertEqual(current['available_units'], 3)
                for i, unit in enumerate(current['units']):
                    media = unit['original']['media_ref']
                    self.assertEqual(media['execution_id'], retry.execution_id)
                    self.assertEqual(media['origin_execution_id'], initial.execution_id if i < 2 else retry.execution_id)
                    self.assertEqual(media['candidate_id'], original[i][2].candidate_id if i < 2 else new_sheet[2].candidate_id)
                    self.assertEqual((await client.get(unit['original']['url'])).status_code, 200)
                sheet_url = current['units'][2]['original']['url']
                self.assertIn((await client.get(self.selector(sheet_url, attempt_id=job.attempt_id))).status_code, (404, 409))
                self.assertIn((await client.get(sheet_url.replace(retry.execution_id, initial.execution_id))).status_code, (404, 409))
                self.assertIsNone(old['units'][2]['original'])

    async def test_request_local_validation_reuse_bounds_full_retry_and_original_work(self):
        from backend import image_reads, portrait_candidate_store as candidates
        async with self.source() as (runtime, ref, _):
            full = await self.start(runtime, ref, key='full-count')
            for i in range(3):
                self.unit(runtime.db, full.execution_id, i)
            self.publish(runtime.db, full)
            initial = await self.start(runtime, ref, key='failed-count')
            old = [self.unit(runtime.db, initial.execution_id, i,
                             finish='failed' if i == 2 else 'completed') for i in range(3)]
            failed = self.publish(runtime.db, initial, status='failed', failed_unit_key='sheet-0')
            retry = await self.retry(runtime, initial, failed, key='retry-count')
            binding, job, _, facts = old[2]
            allocated = jobs.allocate_anchor_unit_retry(runtime.db, job.job_id,
                expected_unit_digest=binding.unit_input_digest, previous_attempt_id=job.attempt_id,
                expected_previous_wire_digest=facts.preview.wire_digest, expected_previous_revision=facts.revision,
                retry_trigger_id=retry.group_id)
            sheet = self.unit(runtime.db, retry.execution_id, 2, job=allocated)
            self.publish(runtime.db, retry)
            changes = runtime.db.total_changes
            measured = {}

            def measure(name, read):
                with patch.object(candidates, '_verify', wraps=candidates._verify) as png_check, \
                     patch.object(jobs, 'read_anchor_unit_job', wraps=jobs.read_anchor_unit_job) as job_check, \
                     patch.object(results, 'read_image_group_result', wraps=results.read_image_group_result) as manifest_check:
                    start = perf_counter()
                    value = read()
                    measured[name] = dict(seconds=round(perf_counter() - start, 3), png=png_check.call_count,
                        job=job_check.call_count, manifest=manifest_check.call_count)
                    return value

            with self.offline():
                self.read_only(runtime.db)
                full_projection = measure('full_list', lambda: image_reads.image_projection(runtime.db, full.execution_id))
                retry_projection = measure('retry_list', lambda: image_reads.image_projection(runtime.db, retry.execution_id))
                assert retry_projection.units[2].original is not None
                media_ref = retry_projection.units[2].original.media_ref
                original = measure('retry_sheet_original', lambda: image_reads.read_image_original(runtime.db, media_ref))
                self.assertEqual(original, (self.root / sheet[2].uri.removeprefix('kinodel://')).read_bytes())
                assert full_projection.result is not None and retry_projection.result is not None
                self.assertEqual((full_projection.available_units, full_projection.result.status), (3, 'complete'))
                self.assertEqual((retry_projection.available_units, retry_projection.result.status), (3, 'complete'))
                # Validation reuse must end at the operation boundary. A later
                # read must notice both changed returned bytes and a broken
                # retained-predecessor context, without repairing either.
                for candidate in (sheet[2], old[0][2]):
                    path = self.root / candidate.uri.removeprefix('kinodel://')
                    saved = path.read_bytes()
                    path.write_bytes(b'changed after the preceding read')
                    try:
                        projection = image_reads.image_projection(runtime.db, retry.execution_id)
                        assert projection.result is not None
                        self.assertEqual((projection.result.result_id, projection.result.digest),
                                         (retry_projection.result.result_id, retry_projection.result.digest))
                        self.assertEqual(projection.result.issue, 'manifest_unavailable_or_invalid')
                        self.assertIsNone(projection.result.status)
                        self.assertEqual(projection.available_units, 2 if candidate == sheet[2] else 0)
                        with self.assertRaises((ValueError, LookupError, OSError)):
                            image_reads.read_image_original(runtime.db, media_ref)
                        self.assertEqual(path.read_bytes(), b'changed after the preceding read')
                    finally:
                        path.write_bytes(saved)
                self.assertEqual(runtime.db.total_changes, changes)
                runtime.db.set_authorizer(None)
            print('7.3B validation measurements: ' + json.dumps(measured, sort_keys=True))
            # Count bounds, not timing thresholds: hardware/load do not change
            # the amount of duplicate validation. Existing manifest reads remain.
            for name, bounds in (('full_list', (26, 60, 1)), ('retry_list', (60, 140, 3)),
                                 ('retry_sheet_original', (40, 100, 1))):
                for key, maximum in zip(('png', 'job', 'manifest'), bounds, strict=True):
                    with self.subTest(operation=name, check=key):
                        self.assertLessEqual(measured[name][key], maximum)

    async def test_exact_selectors_foreign_consumer_project_and_http_guards(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            self.unit(runtime.db, receipt.execution_id, 0)
            other = await self.start(runtime, ref, key='independent')
            async with self.client(runtime) as client:
                projection = (await client.get(self.images_url(receipt))).json()
                url = projection['units'][0]['original']['url']
                changes = runtime.db.total_changes
                for name in ('group_id', 'job_id', 'attempt_id', 'unit_input_digest', 'candidate_digest', 'candidate_metadata_digest'):
                    with self.subTest(selector=name):
                        self.assertIn((await client.get(self.selector(url, **{name: ZERO}))).status_code, (404, 409))
                self.assertIn((await client.get(self.selector(url, origin_execution_id=str(uuid4())))).status_code, (404, 409))
                for foreign in (url.replace(receipt.execution_id, other.execution_id), url.replace('face-0', 'location'),
                                url.replace(projection['units'][0]['original']['media_ref']['candidate_id'].replace(':', '%3A'),
                                            ZERO.replace(':', '%3A'))):
                    self.assertIn((await client.get(foreign)).status_code, (404, 409))
                self.assertEqual((await client.get(self.images_url(SimpleNamespace(execution_id=ref.execution_id)))).status_code, 404)
                query = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
                for required in ('attempt_id', 'candidate_digest', 'unit_key'):
                    absent = {k: v for k, v in query.items() if k != required}
                    self.assertEqual((await client.get(urlsplit(url)._replace(query=urlencode(absent)).geturl())).status_code, 422)
                self.assertEqual(runtime.db.total_changes, changes)
                for route in (self.images_url(receipt), url):
                    self.assertEqual((await client.get(route, headers={'Host': 'evil.example'})).status_code, 403)
                    self.assertEqual((await client.get(route, headers={'Origin': 'http://evil.example'})).status_code, 403)
                    self.assertEqual((await client.get(route, headers={'Cookie': ''})).status_code, 401)
                runtime.db.execute('UPDATE executions SET project_id=? WHERE execution_id=?', (str(uuid4()), receipt.execution_id))
                for route in (self.images_url(receipt), url):
                    response = await client.get(route)
                    self.assertEqual(response.status_code, 409)
                    self.assertNotIn(str(self.root), response.text)

    async def test_foreign_project_candidate_cannot_be_selected_through_another_consumer(self):
        from backend.wardrobe_store import read_wardrobe_plan
        async with self.source() as (runtime, ref, _):
            foreign_project = str(uuid4())
            output = dict(status='ready', plan=compact_draft(('comedian',)), explanation=None)
            story = draft(cast=[dict(subject_id='comedian', description='Traveler')], subject_ids=['comedian'])
            with self.transport(output), patch.object(fixtures, 'draft', return_value=story):
                source = await runtime.start_wardrobe(foreign_project, 'foreign-source', ['s1'], self.brief)
                await runtime.run()
                self.approve(runtime, source.execution_id)
                await runtime.run()
            foreign_ref, _ = read_wardrobe_plan(runtime.db, source.execution_id)
            receipt = await self.start(runtime, ref)
            self.unit(runtime.db, receipt.execution_id, 0)
            foreign = await groups.start_image_execution(runtime.db, runtime.saver, foreign_project, 'foreign-images',
                **self.arguments(foreign_ref, image_size=dict(width=512, height=512)))
            self.unit(runtime.db, foreign.execution_id, 0)
            async with self.client(runtime) as client:
                selected = (await client.get(self.images_url(receipt))).json()
                other = (await client.get(self.images_url(foreign))).json()
                self.assertEqual((selected['project_id'], other['project_id']), (self.project, foreign_project))
                other_url = other['units'][0]['original']['url']
                self.assertEqual((await client.get(other_url)).status_code, 200)
                # Valid foreign job/attempt/candidate/content selectors, but the
                # selected consumer/group cannot confer authority over them.
                forged = self.selector(other_url.replace(foreign.execution_id, receipt.execution_id), group_id=receipt.group_id)
                with self.offline():
                    self.assertIn((await client.get(forged)).status_code, (404, 409))

    async def test_missing_corrupt_and_redirected_originals_do_not_heal_or_hide_result(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            units = [self.unit(runtime.db, receipt.execution_id, i) for i in range(3)]
            manifest = self.publish(runtime.db, receipt)
            # Background loss does not invalidate the independent portrait.
            path = self.root / units[1][2].uri.removeprefix('kinodel://')
            saved = path.read_bytes()
            async with self.client(runtime) as client:
                valid = (await client.get(self.images_url(receipt))).json()
                url = valid['units'][1]['original']['url']
                parked = path.with_suffix('.parked')
                for mode in ('missing', 'corrupt', 'redirected'):
                    with self.subTest(mode=mode):
                        if mode == 'missing':
                            path.rename(parked)
                        elif mode == 'corrupt':
                            path.write_bytes(b'not an original')
                        else:
                            path.rename(parked)
                            os.link(parked, path)  # Redirected/foreign hardlink rejected cross-platform.
                        changes = runtime.db.total_changes
                        with self.offline():
                            response = await client.get(self.images_url(receipt))
                            self.assertEqual(response.status_code, 200, response.text)
                            projection = response.json()
                            self.assertTrue(projection['units'][0]['available'])
                            self.assertFalse(projection['units'][1]['available'])
                            self.assertIsNone(projection['units'][1]['original'])
                            self.assertEqual(projection['result'], dict(result_id=manifest.result_id, digest=manifest.digest,
                                status=None, issue='manifest_unavailable_or_invalid'))
                            self.assertIn((await client.get(url)).status_code, (404, 409))
                        self.assertEqual(runtime.db.total_changes, changes)
                        if mode != 'corrupt':
                            if mode == 'redirected':
                                path.unlink()
                            self.assertFalse(path.exists())
                            parked.rename(path)
                        else:
                            self.assertEqual(path.read_bytes(), b'not an original')
                            path.write_bytes(saved)

    async def test_manifest_file_or_body_or_wake_mismatch_is_not_absent_or_complete(self):
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            for i in range(3):
                self.unit(runtime.db, receipt.execution_id, i)
            manifest = self.publish(runtime.db, receipt)
            path = self.root / manifest.uri.removeprefix('kinodel://')
            async with self.client(runtime) as client:
                row = results._result_row(runtime.db, receipt.group_id)
                values = row[:6]
                for mode in ('file', 'body', 'wake', 'membership'):
                    with self.subTest(mode=mode):
                        if mode == 'file':
                            path.write_bytes(b'invalid manifest')
                        elif mode == 'body':
                            runtime.db.execute("UPDATE image_group_results SET body='{}' WHERE group_id=?", (receipt.group_id,))
                        elif mode == 'wake':
                            runtime.db.execute("UPDATE execution_work SET resume_ref='foreign' WHERE execution_id=? AND kind='resume'",
                                               (receipt.execution_id,))
                        else:
                            # A self-consistent envelope/file/wake still cannot
                            # turn a wrong ordered complete set into completion.
                            bad_body = manifest.body.model_copy(update={'outputs': list(reversed(manifest.body.outputs))})
                            values = results._result_values(bad_body)
                            bad_path = self.root / values[5].removeprefix('kinodel://')
                            batch_store._publish_body(bad_path, values[4].encode('utf-8'))
                            runtime.db.execute('UPDATE image_group_results SET result_digest=?,body=?,uri=? WHERE group_id=?',
                                               (values[2], values[4], values[5], receipt.group_id))
                            runtime.db.execute("UPDATE execution_work SET payload_digest=? WHERE execution_id=? AND kind='resume'",
                                               (values[2], receipt.execution_id))
                        changes = runtime.db.total_changes
                        response = await client.get(self.images_url(receipt))
                        self.assertEqual(response.status_code, 200 if mode == 'membership' else 409, response.text)
                        if mode == 'membership':
                            self.assertEqual(response.json()['result'], dict(result_id=manifest.result_id,
                                digest=values[2], status=None, issue='manifest_unavailable_or_invalid'))
                        self.assertNotIn(str(self.root), response.text)
                        self.assertEqual(runtime.db.total_changes, changes)
                        path.write_bytes(canonical_json(manifest.body))
                        runtime.db.execute('UPDATE image_group_results SET result_digest=?,body=?,uri=? WHERE group_id=?',
                                           (row[2], row[4], row[5], receipt.group_id))
                        runtime.db.execute("UPDATE execution_work SET resume_ref=?,payload_digest=? WHERE execution_id=? AND kind='resume'",
                                           (manifest.result_id, manifest.digest, receipt.execution_id))

    async def test_fresh_process_provider_forbidden_http_reads_byte_identical_no_writes(self):
        self.assertIsNotNone(importlib.util.find_spec('backend.image_reads'), 'Guarded image reads are missing')
        async with self.source() as (runtime, ref, _):
            receipt = await self.start(runtime, ref)
            for i in range(3):
                self.unit(runtime.db, receipt.execution_id, i)
            self.publish(runtime.db, receipt)
            async with self.client(runtime) as client:
                before = (await client.get(self.images_url(receipt))).json()
        child = '''
import asyncio, hashlib, json, socket, sqlite3, sys
from pathlib import Path
from types import SimpleNamespace
import httpx
from backend import database
from backend.api import create_app
def forbidden(*args, **kwargs): raise AssertionError('Forbidden network on originals read')
async def main():
    # Windows creates an internal loopback socketpair while starting its event
    # loop. Block network only after that setup, before opening any app/storage.
    socket.socket.connect = forbidden
    socket.create_connection = forbidden
    httpx.Client.send = forbidden
    send = httpx.AsyncClient.send
    async def local_send(self, *args, **kwargs):
        assert isinstance(self._transport, httpx.ASGITransport), 'Provider HTTP on read'
        return await send(self, *args, **kwargs)
    httpx.AsyncClient.send = local_send
    with database.open_database(Path(sys.argv[1])) as db:
        changes = db.total_changes
        db.set_authorizer(lambda action, *args: sqlite3.SQLITE_DENY if action in
            (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
        app = create_app(Path(sys.argv[1]))
        app.state.runtime = SimpleNamespace(db=db)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('127.0.0.1', 321)),
                                     base_url='http://127.0.0.1:8765') as client:
            await client.get('/api/session')
            response = await client.get('/api/executions/' + sys.argv[2] + '/images')
            assert response.status_code == 200, response.text
            projection = response.json()
            for unit in projection['units']:
                original = unit['original']
                response = await client.get(original['url'])
                assert response.status_code == 200, response.text
                assert 'sha256:' + hashlib.sha256(response.content).hexdigest() == original['media_ref']['candidate_digest']
            assert db.total_changes == changes
            print(json.dumps(projection))
asyncio.run(main())
'''
        run = subprocess.run([sys.executable, '-B', '-c', child, str(self.root), receipt.execution_id],
                             capture_output=True, text=True, timeout=45)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), before)


if __name__ == '__main__':
    unittest.main()
