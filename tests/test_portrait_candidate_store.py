"""Offline original import; no provider success, selection or graph effects."""

from contextlib import closing
import errno
import importlib.util
import io
import json
import os
import random
import sqlite3
import struct
import subprocess
import sys
from typing import Any
import unittest
from unittest.mock import patch
import zlib

from PIL import Image, PngImagePlugin

from backend import batch_store, database, render_job_store
from backend.domain import sha256_digest
from tests import test_batch_store as pins
from tests import test_story_wardrobe_api as fixtures
from tests.test_story_wardrobe_runtime import retained_inventory


def png(size=(512, 512), *, metadata=True, color='purple'):
    output = io.BytesIO()
    info = PngImagePlugin.PngInfo()
    if metadata:
        info.add_text('prompt', 'Exact original metadata 🦊', zip=True)
    Image.new('RGB', size, color).save(output, format='PNG', pnginfo=info)
    return output.getvalue()


def chunk(kind, body):
    return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))


def idat_parts(body):
    offset = 8
    parts = []
    while offset < len(body):
        length, kind = struct.unpack('>I4s', body[offset:offset + 8])
        parts.append((kind, body[offset + 8:offset + 8 + length]))
        offset += length + 12
    return parts


def replace_idat(body, payloads):
    result = bytearray(body[:8])
    inserted = False
    for kind, payload in idat_parts(body):
        if kind == b'IDAT':
            if not inserted:
                for replacement in payloads:
                    result.extend(chunk(b'IDAT', replacement))
                inserted = True
        else:
            result.extend(chunk(kind, payload))
    return bytes(result)


def invalid_critical_framing():
    original = png(metadata=False)
    signature, end = original[:8], chunk(b'IEND', b'')
    rgb_header = chunk(b'IHDR', idat_parts(original)[0][1])
    l_header = chunk(b'IHDR', struct.pack('>IIBBBBB', 512, 512, 8, 0, 0, 0, 0))
    compressed = b''.join(p for k, p in idat_parts(original) if k == b'IDAT')
    rgb_pixels = chunk(b'IDAT', compressed)
    la_header = chunk(b'IHDR', struct.pack('>IIBBBBB', 512, 512, 8, 4, 0, 0, 0))
    l16_header = chunk(b'IHDR', struct.pack('>IIBBBBB', 512, 512, 16, 0, 0, 0, 0))
    la_pixels = chunk(b'IDAT', zlib.compress((b'\x00' + b'\x12\x34' * 512) * 512))
    palette_header = chunk(b'IHDR', struct.pack('>IIBBBBB', 512, 512, 8, 3, 0, 0, 0))
    red, blue = chunk(b'PLTE', b'\xff\x00\x00'), chunk(b'PLTE', b'\x00\x00\xff')
    palette_pixels = chunk(b'IDAT', zlib.compress(b'\x00' * (513 * 512)))
    ancillary = chunk(b'tEXt', b'comment\x00between IDAT chunks')
    variants = {
        'duplicate_identical_ihdr': signature + rgb_header + rgb_header + rgb_pixels + end,
        'rgb8_to_l8_before_idat': signature + rgb_header + l_header + rgb_pixels + end,
        'rgb8_to_l8_after_idat': signature + rgb_header + rgb_pixels + l_header + end,
        'la8_to_l16_before_idat': signature + la_header + l16_header + la_pixels + end,
        'la8_to_l16_after_idat': signature + la_header + la_pixels + l16_header + end,
        'unknown_critical_before_idat': signature + rgb_header + chunk(b'ABCD', b'') + rgb_pixels + end,
        'unknown_critical_after_idat': signature + rgb_header + rgb_pixels + chunk(b'ABCD', b'') + end,
        'duplicate_plte': signature + palette_header + red + blue + palette_pixels + end,
        'plte_after_idat': signature + palette_header + palette_pixels + red + end,
        'indexed_missing_plte': signature + palette_header + palette_pixels + end,
        'empty_plte': signature + palette_header + chunk(b'PLTE', b'') + palette_pixels + end,
        'partial_plte_entry': signature + palette_header + chunk(b'PLTE', b'\xff\x00\x00\x7f') + palette_pixels + end,
        'plte_over_256_entries': signature + palette_header + chunk(b'PLTE', b'\x00' * (257 * 3)) + palette_pixels + end,
        'grayscale_plte': signature + l_header + red + palette_pixels + end,
        'grayscale_alpha_plte': signature + la_header + red + la_pixels + end,
        'noncontiguous_idat_trailer': (signature + rgb_header + chunk(b'IDAT', compressed[:-4])
                                      + ancillary + chunk(b'IDAT', compressed[-4:]) + end),
        'noncontiguous_empty_idat': signature + rgb_header + rgb_pixels + ancillary + chunk(b'IDAT', b'') + end,
    }
    for depth in (1, 2, 4):
        header = chunk(b'IHDR', struct.pack('>IIBBBBB', 512, 512, depth, 3, 0, 0, 0))
        palette = chunk(b'PLTE', b'\x00' * (((1 << depth) + 1) * 3))
        pixels = chunk(b'IDAT', zlib.compress(b'\x00' * (512 * (1 + 512 * depth // 8))))
        variants[f'plte_over_depth_{depth}'] = signature + header + palette + pixels + end
    return variants


class PortraitCandidateTests(fixtures.WardrobeFixtures, unittest.IsolatedAsyncioTestCase):
    committed: Any = pins.BatchStoreTests.committed
    pin: Any = pins.BatchStoreTests.pin
    context: Any = pins.BatchStoreTests.context
    parents: Any = pins.BatchStoreTests.parents
    prepare: Any = pins.BatchStoreTests.prepare
    path: Any = pins.BatchStoreTests.path
    offline: Any = pins.BatchStoreTests.offline

    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('backend.portrait_candidate_store'),
                             'Offline original portrait candidate import is missing')
        from backend import portrait_candidate_store
        self.candidates = portrait_candidate_store
        self.store = batch_store
        self.profile = pins.production_catalog()['image_only']['profiles'][0]['pin']

    def job(self, db, ref):
        batch = self.pin(db, ref, image_size={'width': 512, 'height': 512})
        unit = self.prepare(db, batch, batch.prepared_input.ordered_units[0].unit_key)
        return render_job_store.create_portrait_job(db, batch.batch_id, unit.unit_key,
                                                    expected_unit_digest=unit.input_digest), unit

    def descriptor(self, **changes):
        value = dict(node_id='865', history_key='images', index=0, filename='portrait_00001_.png',
                     subfolder='', type='output', mime_type='image/png')
        value.update(changes)
        return value

    def import_image(self, db, job, unit, body=None, **changes):
        args: dict[str, Any] = dict(expected_unit_digest=unit.input_digest, descriptor=self.descriptor(),
                    stream=io.BytesIO(png() if body is None else body))
        args.update(changes)
        return self.candidates.import_portrait_candidate(db, job.job_id, job.attempt_id, **args)

    def read(self, db, record, unit):
        return self.candidates.read_portrait_candidate(db, record.candidate_id,
                                                       expected_unit_digest=unit.input_digest)

    def count(self, db, state=None):
        return db.execute('SELECT COUNT(*) FROM portrait_candidates' +
                          (" WHERE publication_state='published'" if state else '')).fetchone()[0]

    async def test_original_metadata_preserved_exact_idempotent_offline_reopen(self):
        body = png()
        async with self.committed() as (db, ref):
            before = retained_inventory(db, ref.execution_id)
            job, unit = self.job(db, ref)
            with self.offline(), patch.object(Image.Image, 'save', side_effect=AssertionError('Original must never be re-encoded')):
                record = self.import_image(db, job, unit, body)
                changes = db.total_changes
                self.assertEqual(self.import_image(db, job, unit, body), record)
                self.assertEqual(db.total_changes, changes)
                self.assertEqual(self.read(db, record, unit), record)
            self.assertEqual(self.path(record).read_bytes(), body)
            self.assertEqual(record.digest, sha256_digest(body))
            self.assertEqual((record.byte_length, record.width, record.height, record.mime_type),
                             (len(body), 512, 512, 'image/png'))
            self.assertEqual((record.job_id, record.attempt_id, record.unit_input_digest, record.intent_digest),
                             (job.job_id, job.attempt_id, unit.input_digest, job.intent_digest))
            self.assertEqual(record.descriptor.model_dump(), self.descriptor())
            self.assertEqual(record.endpoint_digest,
                             batch_store.read_batch_input(db, json.loads(job.intent_body)['batch_id']).prepared_input.connection.endpoint_digest)
            self.assertEqual(record.uri, f'kinodel://projects/{ref.project_id}/attempts/{job.job_id[7:]}/'
                                        f'{record.candidate_id[7:]}.{record.digest[7:]}.png')
            self.assertEqual(self.count(db), 1)
            self.assertEqual(retained_inventory(db, ref.execution_id), before)
            self.assertNotIn('prompt_id', record.metadata_body.decode())
            self.assertNotIn('success', record.metadata_body.decode())
        with database.open_database(self.root) as db, self.offline():
            self.assertEqual(self.read(db, record, unit), record)
            self.assertEqual(self.import_image(db, job, unit, body), record)

    async def test_empty_and_safe_nested_subfolder_are_transport_only(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            descriptor = self.descriptor(subfolder='batch/day-01', filename='original.png')
            record = self.import_image(db, job, unit, descriptor=descriptor)
            self.assertNotIn('day-01', record.uri)
            self.assertEqual(record.descriptor.subfolder, 'batch/day-01')
            self.assertEqual(self.import_image(db, job, unit, descriptor=descriptor), record)

    async def test_descriptor_path_type_slot_and_extra_field_negatives_before_streaming(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            bad = [dict(filename=name) for name in ('../x.png', '/x.png', 'a/b.png', 'a\\b.png',
                   'C:x.png', 'x.png:stream', 'CON.png', 'com1.png', 'LPT².png', 'x.png.', 'x.png ',
                   'a\x00.png', 'a\n.png', 'a\u202e.png', '', 'a' * 256)]
            bad += [dict(subfolder=name) for name in ('..', '/a', 'a//b', 'a/../b', 'a/./b',
                     'a\\b', 'C:/a', '//server/share', 'a/', 'aux', 'a\x1fb', 'a' * 1025)]
            bad += [dict(node_id='881'), dict(history_key='gifs'), dict(index=1), dict(index=False),
                    dict(type='input'), dict(mime_type='image/jpeg'), dict(mime_type='image/png; charset=x'),
                    dict(prompt_id='invented'), dict(history_success=True)]
            for changes in bad:
                stream = io.BytesIO(png())
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    self.import_image(db, job, unit, descriptor=self.descriptor(**changes), stream=stream)
                self.assertEqual(stream.tell(), 0)
            self.assertEqual(self.count(db), 0)

    async def test_static_png_only_geometry_crc_decode_animation_truncation_and_bomb(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            jpeg = io.BytesIO()
            Image.new('RGB', (512, 512)).save(jpeg, format='JPEG')
            original = png()
            ihdr = struct.pack('>IIBBBBB', 100000, 100000, 8, 2, 0, 0, 0)
            bomb = original[:8] + chunk(b'IHDR', ihdr) + original[33:]
            # Valid CRC and geometry, but invalid zlib pixels: verify() alone is insufficient.
            invalid_pixels = original[:33] + chunk(b'IDAT', b'not zlib') + chunk(b'IEND', b'')
            animated = io.BytesIO()
            Image.new('RGB', (512, 512)).save(animated, format='PNG', save_all=True,
                append_images=[Image.new('RGB', (512, 512), 'red')], duration=50)
            for body in (b'', b'not media', jpeg.getvalue(), png((768, 768)), png((512, 768)),
                         original[:-1], original[:100], original + b'trailing', bomb,
                         invalid_pixels, animated.getvalue(), original[:33] + chunk(b'acTL', struct.pack('>II', 1, 0)) + original[33:]):
                with self.subTest(length=len(body)), self.assertRaises(ValueError):
                    self.import_image(db, job, unit, body)
                self.assertEqual(self.count(db), 0)
            for raised in (Image.DecompressionBombWarning('bomb'), Image.DecompressionBombError('bomb')):
                with patch.object(Image, 'open', side_effect=raised), self.assertRaises(ValueError):
                    self.import_image(db, job, unit)
            self.assertEqual(self.count(db), 0)

    async def test_png_end_crc_and_compressed_pixel_truncation_are_not_validated_by_verify_alone(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            original = png()
            bad_end = original[:-1] + bytes([original[-1] ^ 1])
            # A valid PNG chunk CRC with an incomplete compressed scanline stream.
            truncated_pixels = original[:33] + chunk(b'IDAT', zlib.compress(b'\x00' * 10)) + chunk(b'IEND', b'')
            for body in (bad_end, truncated_pixels):
                with self.assertRaises(ValueError):
                    self.import_image(db, job, unit, body)
                self.assertEqual(self.count(db), 0)

    async def test_incomplete_idat_zlib_trailer_never_publishes_a_candidate(self):
        original = png()
        compressed = b''.join(payload for kind, payload in idat_parts(original) if kind == b'IDAT')
        damaged = replace_idat(original, [compressed[:-4]])
        decoder = zlib.decompressobj()
        pixels = decoder.decompress(compressed[:-4])
        self.assertFalse(decoder.eof)
        self.assertEqual(len(pixels), 512 * (1 + 512 * 3))  # All pixels exist; Adler32 does not.
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            with self.assertRaises(ValueError):
                self.import_image(db, job, unit, damaged)
            self.assertEqual(self.count(db), 0)

    async def test_reader_rejects_previously_published_incomplete_idat_even_with_matching_hashes(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            original = png()
            record = self.import_image(db, job, unit, original)
            compressed = b''.join(payload for kind, payload in idat_parts(original) if kind == b'IDAT')
            damaged = replace_idat(original, [compressed[:-4]])
            # Reproduce a candidate published by the former validator: SQL/file hashes
            # agree, so rejection must come from technical validation, not tamper checks.
            metadata = json.loads(record.metadata_body)
            metadata['digest'] = sha256_digest(damaged)
            metadata['byte_length'] = len(damaged)
            metadata['uri'] = record.uri.replace(record.digest[7:], metadata['digest'][7:])
            body = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
            path = self.root / metadata['uri'].removeprefix('kinodel://')
            self.path(record).unlink()
            path.write_bytes(damaged)
            db.execute('UPDATE portrait_candidates SET metadata_body=?,metadata_digest=?,uri=?',
                       (body.decode(), sha256_digest(body), metadata['uri']))
            before = db.total_changes
            with self.assertRaises(ValueError):
                self.read(db, record, unit)
            with self.assertRaises(ValueError):
                self.import_image(db, job, unit, damaged)
            self.assertEqual(db.total_changes, before)
            self.assertEqual(path.read_bytes(), damaged)

    async def test_idat_incomplete_checksum_extra_stream_garbage_and_inflation_refuse_before_sql(self):
        original = png()
        compressed = b''.join(payload for kind, payload in idat_parts(original) if kind == b'IDAT')
        pixels = zlib.decompress(compressed)
        variants = {
            'missing_last_adler_byte': [compressed[:-1]],
            'missing_adler': [compressed[:-4]],
            'bad_adler': [compressed[:-1] + bytes([compressed[-1] ^ 1])],
            'concatenated_streams_one_chunk': [compressed + compressed],
            'concatenated_streams_split_chunks': [compressed, compressed],
            'trailing_compressed_garbage': [compressed + b'garbage'],
            'no_idat': [],
            'empty_idat': [b''],
            'one_missing_scanline_byte': [zlib.compress(pixels[:-1])],
            'one_extra_decoded_byte': [zlib.compress(pixels + b'x')],
            'excessive_inflation': [zlib.compress(b'\x00' * (len(pixels) + 65536))],
        }
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            for label, payloads in variants.items():
                with self.subTest(label=label), self.assertRaises(ValueError):
                    self.import_image(db, job, unit, replace_idat(original, payloads))
                self.assertEqual(self.count(db), 0)

    async def test_invalid_critical_framing_never_reserves_or_publishes(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            for label, damaged in invalid_critical_framing().items():
                with self.subTest(label=label):
                    try:
                        before = db.total_changes
                        with self.assertRaises(ValueError):
                            self.import_image(db, job, unit, damaged)
                        self.assertEqual(self.count(db), 0)
                        self.assertEqual(db.total_changes, before)
                    finally:
                        # Keep RED cases independent if the old validator publishes one.
                        for (uri,) in db.execute('SELECT uri FROM portrait_candidates').fetchall():
                            (self.root / uri.removeprefix('kinodel://')).unlink()
                        db.execute('DELETE FROM portrait_candidates')

    async def test_reader_rejects_invalid_critical_framing_even_with_matching_hashes(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            record = self.import_image(db, job, unit)
            path = self.path(record)
            for label, damaged in invalid_critical_framing().items():
                metadata = json.loads(record.metadata_body)
                metadata['digest'] = sha256_digest(damaged)
                metadata['byte_length'] = len(damaged)
                metadata['uri'] = record.uri.replace(record.digest[7:], metadata['digest'][7:])
                body = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                path.unlink()
                path = self.root / metadata['uri'].removeprefix('kinodel://')
                path.write_bytes(damaged)
                db.execute('UPDATE portrait_candidates SET metadata_body=?,metadata_digest=?,uri=?',
                           (body.decode(), sha256_digest(body), metadata['uri']))
                before = db.total_changes
                with self.subTest(label=label):
                    with self.assertRaises(ValueError):
                        self.read(db, record, unit)
                    with self.assertRaises(ValueError):
                        self.import_image(db, job, unit, damaged)
                    self.assertEqual(db.total_changes, before)
                    self.assertEqual(path.read_bytes(), damaged)

    async def test_unknown_ancillary_and_embedded_text_beyond_sql_cap_preserve_original(self):
        original = png()
        body = (original[:33] + chunk(b'vpAg', b'unknown ancillary before pixels')
                + chunk(b'tEXt', b'comment\x00' + b'x' * (self.candidates.MAX_METADATA_BYTES + 1))
                + original[33:-12] + chunk(b'vpAg', b'unknown ancillary after pixels') + original[-12:])
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            record = self.import_image(db, job, unit, body)
            self.assertEqual(self.read(db, record, unit), record)
            self.assertEqual(self.path(record).read_bytes(), body)

    async def test_valid_split_idat_and_png_color_depth_interlace_preserve_originals(self):
        original = png()
        compressed = b''.join(payload for kind, payload in idat_parts(original) if kind == b'IDAT')
        split = replace_idat(original, [b'', *(compressed[i:i + 7] for i in range(0, len(compressed), 7)), b''])
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            record = self.import_image(db, job, unit, split)
            self.assertEqual(self.path(record).read_bytes(), split)
            self.assertEqual(self.read(db, record, unit), record)
            valid = {'split-metadata': split}
            for mode in ('1', 'L', 'LA', 'P', 'RGB', 'RGBA', 'I;16'):
                output = io.BytesIO()
                Image.new(mode, (512, 512), 0).save(output, format='PNG', bits=1 if mode == 'P' else 8)
                valid[mode] = output.getvalue()
            output = io.BytesIO()
            Image.frombytes('RGBA', (512, 512), random.Random(42).randbytes(512 * 512 * 4)).save(output, format='PNG')
            valid['noise-RGBA'] = output.getvalue()  # Compressed IDAT spans multiple 64 KiB reads.
            self.assertGreater(sum(len(p) for k, p in idat_parts(valid['noise-RGBA']) if k == b'IDAT'), 65536)
            encoder = zlib.compressobj()
            encoded = b''.join(encoder.compress(b'\x00' * (1 + 512 * 8)) for _ in range(512)) + encoder.flush()
            valid['RGBA16'] = (original[:8] + chunk(b'IHDR', struct.pack('>IIBBBBB', 512, 512, 16, 6, 0, 0, 0))
                               + chunk(b'IDAT', encoded) + chunk(b'IEND', b''))
            # Genuine Adam7 scanlines, not just changing IHDR's interlace bit.
            raw = bytearray()
            for x, y, dx, dy in ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8),
                                 (2, 0, 4, 4), (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2)):
                columns = (512 - x + dx - 1) // dx
                rows = (512 - y + dy - 1) // dy
                raw.extend((b'\x00' + b'\x00\x00\x00' * columns) * rows)
            valid['Adam7'] = (original[:8] + chunk(b'IHDR', struct.pack('>IIBBBBB', 512, 512, 8, 2, 0, 0, 1))
                             + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
            for label, body in valid.items():
                with self.subTest(label=label):
                    path = self.root / (label.replace(';', '-') + '.png')
                    path.write_bytes(body)
                    self.assertEqual(self.candidates._verify(path, 512, 512), (sha256_digest(body), len(body)))

    async def test_valid_palette_entry_bounds_and_optional_truecolor_palettes(self):
        signature = png()[:8]
        adam7 = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
                 (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            for color, depth in ((3, 1), (3, 2), (3, 4), (3, 8), (2, 8), (2, 16), (6, 8), (6, 16)):
                channels = {2: 3, 3: 1, 6: 4}[color]
                for entries in (1, (1 << depth) if color == 3 else 256):
                    for interlace in (0, 1):
                        with self.subTest(color=color, depth=depth, entries=entries, interlace=interlace):
                            raw = bytearray()
                            for x, y, dx, dy in adam7 if interlace else ((0, 0, 1, 1),):
                                columns, rows = (512 - x + dx - 1) // dx, (512 - y + dy - 1) // dy
                                raw.extend(b'\x00' * (rows * (1 + (columns * channels * depth + 7) // 8)))
                            header = struct.pack('>IIBBBBB', 512, 512, depth, color, 0, 0, interlace)
                            body = (signature + chunk(b'IHDR', header) + chunk(b'PLTE', b'\xff\x00\x00' * entries)
                                    + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
                            record = self.import_image(db, job, unit, body)
                            self.assertEqual(self.read(db, record, unit), record)
                            self.assertEqual(self.path(record).read_bytes(), body)
                            self.path(record).unlink()
                            db.execute('DELETE FROM portrait_candidates')

    async def test_bounded_stream_and_failed_download_or_disk_full_never_visible(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            class Infinite:
                total = 0
                def read(inner, size):
                    self.assertLessEqual(size, self.candidates.STREAM_CHUNK_BYTES)
                    inner.total += size
                    return b'x' * size
            stream = Infinite()
            with self.assertRaises(ValueError):
                self.import_image(db, job, unit, stream=stream)
            self.assertLessEqual(stream.total, self.candidates.MAX_PNG_BYTES + self.candidates.STREAM_CHUNK_BYTES)
            class Broken:
                first = True
                def read(inner, size):
                    if inner.first:
                        inner.first = False
                        return png()[:80]
                    raise OSError('interrupted source')
            with self.assertRaises(OSError):
                self.import_image(db, job, unit, stream=Broken())
            with patch.object(self.candidates.os, 'fsync', side_effect=OSError(errno.ENOSPC, 'disk full')):
                with self.assertRaises(OSError):
                    self.import_image(db, job, unit)
            self.assertEqual(self.count(db), 0)
            self.assertFalse(db.in_transaction)
            with self.assertRaises(ValueError):
                self.import_image(db, job, unit, stream=type('Oversized', (), {'read': lambda s, n: b'x' * (n + 1)})())
            self.assertEqual(self.count(db), 0)

    async def test_publication_disk_full_keeps_exact_reservation_invisible_and_recoverable(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            with patch.object(self.candidates.os, 'link', side_effect=OSError(errno.ENOSPC, 'disk full')):
                with self.assertRaises(OSError):
                    self.import_image(db, job, unit)
            self.assertEqual((self.count(db), self.count(db, 'published')), (1, 0))
            frozen = db.execute('SELECT metadata_body FROM portrait_candidates').fetchone()[0]
            with closing(sqlite3.connect(self.root / database.DATABASE_NAME)) as observer:
                self.assertEqual(self.count(observer, 'published'), 0)
            record = self.import_image(db, job, unit, stream=None)
            self.assertEqual(record.metadata_body.decode(), frozen)
            self.assertEqual(self.path(record).read_bytes(), png())

    async def test_exact_retry_conflicts_never_overwrite_or_allocate_second_identity(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            record = self.import_image(db, job, unit)
            before = self.path(record).read_bytes()
            for changes in (dict(body=png(color='red')), dict(descriptor=self.descriptor(filename='other.png')),
                            dict(descriptor=self.descriptor(subfolder='other')), dict(expected_unit_digest='sha256:' + '0' * 64)):
                with self.subTest(changes=list(changes)), self.assertRaises(ValueError):
                    self.import_image(db, job, unit, **changes)
            with self.assertRaises(ValueError):
                self.candidates.import_portrait_candidate(db, job.job_id, 'sha256:' + '0' * 64,
                    expected_unit_digest=unit.input_digest, descriptor=self.descriptor(), stream=io.BytesIO(png()))
            self.assertEqual(self.count(db), 1)
            self.assertEqual(self.path(record).read_bytes(), before)

    async def test_published_missing_corrupt_oversized_or_linked_original_never_heals(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            record = self.import_image(db, job, unit)
            path = self.path(record)
            body = path.read_bytes()
            for changed in (b'corrupt', b'x' * (self.candidates.MAX_PNG_BYTES + 1), None):
                if changed is None:
                    path.unlink()
                else:
                    path.write_bytes(changed)
                for action in (lambda: self.read(db, record, unit), lambda: self.import_image(db, job, unit)):
                    with self.assertRaises((ValueError, OSError)):
                        action()
                self.assertEqual(path.read_bytes() if path.exists() else None, changed)
                path.write_bytes(body)
            alias = path.with_name('foreign.png')
            os.link(path, alias)
            with self.assertRaises(ValueError):
                self.read(db, record, unit)
            with self.assertRaises(ValueError):
                self.import_image(db, job, unit)
            alias.unlink()

    async def test_sql_canonical_identity_lineage_and_pin_corruption_refuse(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            record = self.import_image(db, job, unit)
            for column, original, changed in (
                    ('unit_input_digest', record.unit_input_digest, 'sha256:' + '0' * 64),
                    ('intent_digest', record.intent_digest, 'sha256:' + '0' * 64),
                    ('metadata_digest', sha256_digest(record.metadata_body), 'sha256:' + '0' * 64),
                    ('metadata_body', record.metadata_body.decode(), json.dumps(json.loads(record.metadata_body), indent=2)),
                    ('uri', record.uri, record.uri.replace('/attempts/', '/assets/'))):
                db.execute(f'UPDATE portrait_candidates SET {column}=?', (changed,))
                with self.subTest(column=column), self.assertRaises(ValueError):
                    self.read(db, record, unit)
                with self.assertRaises(ValueError):
                    self.import_image(db, job, unit)
                db.execute(f'UPDATE portrait_candidates SET {column}=?', (original,))
            metadata = json.loads(record.metadata_body)
            metadata['endpoint_digest'] = 'sha256:' + '0' * 64
            body = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
            db.execute('UPDATE portrait_candidates SET metadata_body=?,metadata_digest=?', (body.decode(), sha256_digest(body)))
            with self.assertRaises(ValueError):
                self.read(db, record, unit)
            db.execute('UPDATE portrait_candidates SET metadata_body=?,metadata_digest=?',
                       (record.metadata_body.decode(), sha256_digest(record.metadata_body)))
            self.path(unit).unlink()
            with self.assertRaises(OSError):
                self.read(db, record, unit)

    async def test_reservation_and_marker_transaction_failure_and_occ_fail_closed(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            db.execute("CREATE TEMP TRIGGER fail_reserve BEFORE INSERT ON portrait_candidates BEGIN SELECT RAISE(ABORT,'reserve'); END")
            with self.assertRaises(sqlite3.IntegrityError):
                self.import_image(db, job, unit)
            self.assertEqual(self.count(db), 0)
            db.execute('DROP TRIGGER fail_reserve')
            db.execute("CREATE TEMP TRIGGER fail_marker BEFORE UPDATE ON portrait_candidates BEGIN SELECT RAISE(ABORT,'marker'); END")
            with self.assertRaises(sqlite3.IntegrityError):
                self.import_image(db, job, unit)
            self.assertEqual((self.count(db), self.count(db, 'published')), (1, 0))
            candidate_id = db.execute('SELECT candidate_id FROM portrait_candidates').fetchone()[0]
            with self.assertRaises(LookupError):
                self.candidates.read_portrait_candidate(db, candidate_id, expected_unit_digest=unit.input_digest)
            db.execute('DROP TRIGGER fail_marker')
            original = self.candidates._publish
            def drift(*args):
                original(*args)
                db.execute("UPDATE portrait_candidates SET intent_digest=?", ('sha256:' + '0' * 64,))
            with patch.object(self.candidates, '_publish', side_effect=drift), self.assertRaises(ValueError):
                self.import_image(db, job, unit, stream=None)
            self.assertEqual(self.count(db, 'published'), 0)
            db.execute('UPDATE portrait_candidates SET intent_digest=?', (job.intent_digest,))
            record = self.import_image(db, job, unit, stream=None)
            db.execute('BEGIN IMMEDIATE')
            for action in (lambda: self.read(db, record, unit), lambda: self.import_image(db, job, unit)):
                with self.assertRaises(ValueError):
                    action()
            self.assertTrue(db.in_transaction)
            db.execute('ROLLBACK')

    async def test_real_process_death_boundaries_and_exact_reserved_recovery(self):
        async with self.committed() as (db, ref):
            before = retained_inventory(db, ref.execution_id)
            job, unit = self.job(db, ref)
        script = '''
import io, json, os, sys
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
from backend import database, portrait_candidate_store as store
from tests.test_portrait_candidate_store import png
root, job_id, attempt_id, digest, phase = sys.argv[1:]
descriptor = dict(node_id='865', history_key='images', index=0, filename='portrait_00001_.png', subfolder='', type='output', mime_type='image/png')
transaction, link, publish = store._transaction, store.os.link, store._publish
@contextmanager
def crash_tx(db):
    with transaction(db):
        yield
        if phase == 'before-reservation': os._exit(73)
        if phase == 'before-marker' and db.execute("SELECT publication_state FROM portrait_candidates").fetchone() == ('published',): os._exit(77)
    if phase == 'after-reservation': os._exit(74)
def crash_link(*args):
    link(*args)
    os._exit(75)
def crash_publish(*args):
    publish(*args)
    os._exit(76)
class Partial:
    calls = 0
    def read(self, n):
        self.calls += 1
        if self.calls == 1: return png()[:80]
        os._exit(72)
with database.open_database(Path(root)) as db:
    with patch.object(store, '_transaction', crash_tx), patch.object(store.os, 'link', crash_link if phase == 'after-link' else link), patch.object(store, '_publish', crash_publish if phase == 'after-publication' else publish):
        store.import_portrait_candidate(db, job_id, attempt_id, expected_unit_digest=digest, descriptor=descriptor, stream=Partial() if phase == 'stream' else io.BytesIO(png()))
raise AssertionError('Crash hook not reached')
'''
        identities = []
        for phase, code in (('stream', 72), ('before-reservation', 73), ('after-reservation', 74),
                            ('after-link', 75), ('after-publication', 76), ('before-marker', 77)):
            child = subprocess.run([sys.executable, '-B', '-c', script, str(self.root), job.job_id,
                job.attempt_id, unit.input_digest, phase], capture_output=True, text=True, timeout=60)
            self.assertEqual(child.returncode, code, child.stdout + child.stderr)
            with database.open_database(self.root) as db, self.offline():
                self.assertEqual(self.count(db, 'published'), 0)
                self.assertEqual(self.count(db), int(code >= 74))
                if code >= 74:
                    metadata = json.loads(db.execute('SELECT metadata_body FROM portrait_candidates').fetchone()[0])
                    frozen = db.execute('SELECT metadata_body,metadata_digest FROM portrait_candidates').fetchone()
                    candidate_id = metadata['candidate_id']
                    with self.assertRaises(LookupError):
                        self.candidates.read_portrait_candidate(db, candidate_id, expected_unit_digest=unit.input_digest)
                    if phase == 'after-link':
                        directory = self.root / 'projects' / ref.project_id / 'attempts' / job.job_id[7:]
                        self.assertEqual((directory / metadata['staging_name']).stat().st_nlink, 2)
                    record = self.import_image(db, job, unit, stream=None)
                    self.assertEqual(db.execute('SELECT metadata_body,metadata_digest FROM portrait_candidates').fetchone(), frozen)
                else:
                    record = self.import_image(db, job, unit)
                self.assertEqual(self.path(record).read_bytes(), png())
                identities.append(record.candidate_id)
                self.assertEqual(retained_inventory(db, ref.execution_id), before)
                self.path(record).unlink()
                db.execute('DELETE FROM portrait_candidates')
        self.assertEqual(len(set(identities)), 1)

    async def test_reserved_missing_staging_requires_exact_supplied_original(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            with patch.object(self.candidates, '_publish', side_effect=OSError('stop after reservation')):
                with self.assertRaises(OSError):
                    self.import_image(db, job, unit)
            body = db.execute('SELECT metadata_body FROM portrait_candidates').fetchone()[0]
            metadata = json.loads(body)
            directory = self.root / 'projects' / ref.project_id / 'attempts' / job.job_id[7:]
            stage = directory / metadata['staging_name']
            stage.unlink()
            with self.assertRaises((ValueError, OSError)):
                self.import_image(db, job, unit, stream=None)
            with self.assertRaises(ValueError):
                self.import_image(db, job, unit, png(color='red'))
            self.assertEqual(self.count(db, 'published'), 0)
            record = self.import_image(db, job, unit)
            self.assertEqual(record.metadata_body.decode(), body)
            self.assertEqual(self.path(record).read_bytes(), png())

    async def test_reserved_partial_staging_requires_exact_supplied_prefix_and_never_overwrites_foreign(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            with patch.object(self.candidates, '_publish', side_effect=OSError('stop')):
                with self.assertRaises(OSError):
                    self.import_image(db, job, unit)
            frozen = db.execute('SELECT metadata_body FROM portrait_candidates').fetchone()[0]
            metadata = json.loads(frozen)
            stage = (self.root / 'projects' / ref.project_id / 'attempts' / job.job_id[7:] / metadata['staging_name'])
            stage.write_bytes(b'foreign prefix')
            with self.assertRaises(ValueError):
                self.import_image(db, job, unit)
            self.assertEqual(stage.read_bytes(), b'foreign prefix')
            stage.write_bytes(png()[:80])
            with self.assertRaises(ValueError):
                self.import_image(db, job, unit, stream=None)
            record = self.import_image(db, job, unit)
            self.assertEqual(record.metadata_body.decode(), frozen)
            self.assertEqual(self.path(record).read_bytes(), png())

    async def test_unreserved_destination_is_never_adopted_even_with_exact_valid_bytes(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            descriptor = self.candidates.PortraitOutputDescriptorV1.model_validate(self.descriptor())
            identity = self.candidates._candidate_id(job.job_id, job.attempt_id, descriptor)
            directory = self.root / 'projects' / ref.project_id / 'attempts' / job.job_id[7:]
            directory.mkdir(parents=True)
            path = directory / f'{identity[7:]}.{sha256_digest(png())[7:]}.png'
            path.write_bytes(png())
            with self.assertRaises(ValueError):
                self.import_image(db, job, unit)
            self.assertEqual(self.count(db), 0)
            self.assertEqual(path.read_bytes(), png())

    async def test_redirected_attempt_ancestor_and_foreign_publication_pair_refuse(self):
        async with self.committed() as (db, ref):
            job, unit = self.job(db, ref)
            with patch.object(self.candidates, '_publish', side_effect=OSError('stop')):
                with self.assertRaises(OSError):
                    self.import_image(db, job, unit)
            metadata = json.loads(db.execute('SELECT metadata_body FROM portrait_candidates').fetchone()[0])
            directory = self.root / 'projects' / ref.project_id / 'attempts' / job.job_id[7:]
            stage = directory / metadata['staging_name']
            alias = directory / 'foreign.png'
            os.link(stage, alias)
            with self.assertRaises(ValueError):
                self.import_image(db, job, unit, stream=None)
            alias.unlink()
            destination = directory / metadata['uri'].rsplit('/', 1)[1]
            destination.write_bytes(b'foreign')
            with self.assertRaises(ValueError):
                self.import_image(db, job, unit, stream=None)
            destination.unlink()
            original_dir = directory.with_name('original-directory')
            directory.rename(original_dir)
            try:
                if os.name == 'nt':
                    made = subprocess.run(['cmd', '/c', 'mklink', '/J', str(directory), str(original_dir)],
                                          capture_output=True, text=True)
                    self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
                else:
                    directory.symlink_to(original_dir, target_is_directory=True)
                with self.assertRaises(ValueError):
                    self.import_image(db, job, unit, stream=None)
            finally:
                if os.name == 'nt':
                    directory.rmdir()
                else:
                    directory.unlink()
                original_dir.rename(directory)
            self.assertEqual(self.count(db, 'published'), 0)


if __name__ == '__main__':
    unittest.main()
