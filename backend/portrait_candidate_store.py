"""Offline technical PNG candidates for ONE initial pinned anchor-unit attempt.

Caller holds the data-root OS lock. This imports original bytes, not provider
acceptance/history success, approval, selected assets or graph effects. A future
worker must prove successful declared history before calling this boundary.
Private descriptor/endpoint provenance is not a public DTO or a local path.
Windows file fsync + SQLite FULL cover process death, not power-loss durability.
"""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import struct
from typing import Annotated, BinaryIO, Literal
import unicodedata
from uuid import uuid4
import warnings
import zlib

from PIL import Image
from pydantic import Field, TypeAdapter, field_validator

from backend import batch_store, render_job_store
from backend.batch_store import _committed, _directories, _identity, _transaction
from backend.database import _check_file, _sync_directory
from backend.domain import CanonicalUUID, DomainModel, canonical_json, sha256_digest
from backend.story_store import _root
from backend.wardrobe import AnchorKey, ExactDigest


MAX_PNG_BYTES = 16 * 1024 * 1024
STREAM_CHUNK_BYTES = 64 * 1024
MAX_DIMENSION = 1024
MAX_PIXELS = MAX_DIMENSION * MAX_DIMENSION
MAX_METADATA_BYTES = 8192
_BoundedKey = Annotated[str, Field(min_length=1, max_length=128)]


def _component(value: str) -> str:
    # Comfy descriptors are untrusted transport names, including on POSIX hosts.
    if (not value or value in ('.', '..') or value != value.strip() or value.endswith('.')
            or any(c in '<>:"/\\|?*' or unicodedata.category(c).startswith('C') for c in value)
            or value.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$',
                *(f'{prefix}{n}' for prefix in ('COM', 'LPT') for n in '123456789¹²³')}):
        raise ValueError('Unsafe provider output component')
    return value


class PortraitOutputDescriptorV1(DomainModel):
    """Declared history slot and /view provenance, NOT evidence of history success."""

    node_id: _BoundedKey
    history_key: _BoundedKey
    index: Annotated[int, Field(ge=0, le=0)]
    filename: Annotated[str, Field(min_length=1, max_length=255)]
    subfolder: Annotated[str, Field(max_length=1024)]
    type: Literal['output']
    mime_type: Literal['image/png']

    @field_validator('node_id', 'history_key', 'filename')
    @classmethod
    def safe_component(cls, value):
        return _component(value)

    @field_validator('subfolder')
    @classmethod
    def safe_subfolder(cls, value):
        if value:
            for part in value.split('/'):
                if len(part) > 255:
                    raise ValueError('Provider subfolder component is too long')
                _component(part)
        return value


class _CandidateMetadataV1(DomainModel):
    schema_version: Literal['1']
    candidate_id: ExactDigest
    project_id: CanonicalUUID
    batch_id: ExactDigest
    job_id: ExactDigest
    attempt_id: ExactDigest
    unit_key: AnchorKey
    unit_input_digest: ExactDigest
    intent_digest: ExactDigest
    connection: Literal['local', 'server']
    endpoint_digest: ExactDigest
    descriptor: PortraitOutputDescriptorV1
    digest: ExactDigest
    mime_type: Literal['image/png']
    byte_length: Annotated[int, Field(ge=1, le=MAX_PNG_BYTES)]
    width: Annotated[int, Field(ge=1, le=MAX_DIMENSION)]
    height: Annotated[int, Field(ge=1, le=MAX_DIMENSION)]
    uri: Annotated[str, Field(max_length=512)]
    staging_name: Annotated[str, Field(min_length=47, max_length=47, pattern=r'^\.candidate-[0-9a-f]{32}\.tmp$')]


class _AnchorUnitCandidateMetadataV1(_CandidateMetadataV1):
    schema_id: Literal['comfyui_anchor_unit_candidate']
    kind: Literal['background', 'sheet']


@dataclass(frozen=True, repr=False)
class PortraitCandidateV1:
    candidate_id: str
    job_id: str
    attempt_id: str
    unit_input_digest: str
    intent_digest: str
    endpoint_digest: str
    descriptor: PortraitOutputDescriptorV1
    digest: str
    mime_type: str
    byte_length: int
    width: int
    height: int
    uri: str
    metadata_body: bytes


AnchorUnitCandidateV1 = PortraitCandidateV1
AnchorUnitOutputDescriptorV1 = PortraitOutputDescriptorV1


def _binding_rows(db, job_id, batch_id, unit_key):
    return (render_job_store._row(db, job_id), batch_store._batch_row(db, batch_id),
            batch_store._unit_row(db, batch_id, unit_key))


def _context(db, job_id, attempt_id, expected_unit_digest):
    TypeAdapter(ExactDigest).validate_python(attempt_id, strict=True)
    job = render_job_store.read_anchor_unit_job(db, job_id, expected_unit_digest=expected_unit_digest)
    if job.attempt_id != attempt_id:
        raise ValueError('Candidate attempt conflicts with initial portrait intent')
    intent = json.loads(job.intent_body)
    batch = batch_store.read_batch_input(db, intent['batch_id'])
    image = json.loads(job.prepared_input.image_pin_json)  # Already replay-validated by job reader.
    width, height = image['settings']['width'], image['settings']['height']
    if (image['expected_output']['media_type'] != 'image/png'
            or not (0 < width <= MAX_DIMENSION and 0 < height <= MAX_DIMENSION and width * height <= MAX_PIXELS)):
        raise ValueError('Unsupported frozen portrait media contract')
    return job, intent, batch.prepared_input.connection, image, _binding_rows(db, job_id, intent['batch_id'], intent['unit_key'])


def _assert_binding(db, context):
    job, intent, _, _, rows = context
    if _binding_rows(db, job.job_id, intent['batch_id'], intent['unit_key']) != rows:
        raise ValueError('Portrait input/intent changed during candidate publication')


def _descriptor(value, image):
    descriptor = PortraitOutputDescriptorV1.model_validate(value)
    output = image['expected_output']
    if (descriptor.node_id, descriptor.history_key, descriptor.mime_type) != (
            output['node_id'], output['history_key'], output['media_type']):
        raise ValueError('Provider descriptor conflicts with frozen declared output')
    return descriptor


def _candidate_id(job_id, attempt_id, descriptor, kind='portrait'):
    namespace = ('kinodel.comfyui-portrait-candidate.v1' if kind == 'portrait'
                 else 'kinodel.comfyui-anchor-unit-candidate.v1')
    return _identity(namespace, job_id, attempt_id,
                     descriptor.node_id, descriptor.history_key, str(descriptor.index))


def _metadata(context, descriptor, digest, byte_length, staging_name):
    job, intent, connection, image, _ = context
    identity = _candidate_id(job.job_id, job.attempt_id, descriptor, job.kind)
    uri = (f"kinodel://projects/{intent['project_id']}/attempts/{job.job_id[7:]}/"
           f'{identity[7:]}.{digest[7:]}.png')
    model, fields = (_CandidateMetadataV1, {}) if job.kind == 'portrait' else (
        _AnchorUnitCandidateMetadataV1, dict(schema_id='comfyui_anchor_unit_candidate', kind=job.kind))
    return model(**fields, schema_version='1', candidate_id=identity, project_id=intent['project_id'],
        batch_id=intent['batch_id'], job_id=job.job_id, attempt_id=job.attempt_id, unit_key=intent['unit_key'],
        unit_input_digest=intent['unit_input_digest'], intent_digest=job.intent_digest,
        connection=connection.connection, endpoint_digest=connection.endpoint_digest, descriptor=descriptor,
        digest=digest, mime_type='image/png', byte_length=byte_length, width=image['settings']['width'],
        height=image['settings']['height'], uri=uri, staging_name=staging_name)


def _row(db, candidate_id):
    return db.execute('SELECT candidate_id,job_id,attempt_id,unit_input_digest,intent_digest,'
        'metadata_digest,metadata_body,uri,publication_state FROM portrait_candidates WHERE candidate_id=?',
        (candidate_id,)).fetchone()


def _restore(db, row, expected_unit_digest):
    value = row[6]
    if type(value) is not str or not 0 < len(value) <= MAX_METADATA_BYTES:
        raise ValueError('Invalid candidate metadata size')
    body = value.encode('utf-8')
    metadata = TypeAdapter(_CandidateMetadataV1 | _AnchorUnitCandidateMetadataV1).validate_json(body)
    if canonical_json(metadata, max_bytes=MAX_METADATA_BYTES) != body or sha256_digest(body) != row[5]:
        raise ValueError('Candidate metadata is noncanonical or corrupt')
    context = _context(db, metadata.job_id, metadata.attempt_id, expected_unit_digest)
    descriptor = _descriptor(metadata.descriptor, context[3])
    expected = _metadata(context, descriptor, metadata.digest, metadata.byte_length, metadata.staging_name)
    if (metadata != expected or row[:5] != (metadata.candidate_id, metadata.job_id, metadata.attempt_id,
            metadata.unit_input_digest, metadata.intent_digest) or row[7] != metadata.uri
            or row[8] not in ('reserved', 'published')):
        raise ValueError('Candidate SQL identity/provenance mismatch; refusing repair')
    path = _root(db) / metadata.uri.removeprefix('kinodel://')
    return metadata, body, path, context


def _record(metadata, body):
    return PortraitCandidateV1(metadata.candidate_id, metadata.job_id, metadata.attempt_id,
        metadata.unit_input_digest, metadata.intent_digest, metadata.endpoint_digest, metadata.descriptor,
        metadata.digest, metadata.mime_type, metadata.byte_length, metadata.width, metadata.height, metadata.uri, body)


def _info(path, links=1):
    _directories(path)
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != links
            or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
            or not 0 < info.st_size <= MAX_PNG_BYTES):
        raise ValueError('Candidate file is redirected, foreign-linked or outside byte bounds')
    return info


def _same_file(path, source, expected, links=1):
    current = _info(path, links)
    opened = os.fstat(source.fileno())
    if (not os.path.samestat(current, expected) or not os.path.samestat(expected, opened)
            or (current.st_size, current.st_mtime_ns, current.st_ctime_ns) !=
               (expected.st_size, expected.st_mtime_ns, expected.st_ctime_ns)
            or opened.st_nlink != links):
        raise ValueError('Candidate file identity changed')


def _png_scanline_bytes(header):
    """Exact filtered-byte count, including packed samples and Adam7 pass rows."""
    width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', header)
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
    if (depth not in depths.get(color, ()) or compression != 0 or filtering != 0 or interlace not in (0, 1)):
        raise ValueError('Unsupported PNG sample/header encoding')
    bits = channels[color] * depth
    passes = ((0, 0, 1, 1),) if interlace == 0 else (
        (0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
        (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))
    total = 0
    for x, y, dx, dy in passes:
        columns, rows = max(0, (width - x + dx - 1) // dx), max(0, (height - y + dy - 1) // dy)
        if columns and rows:
            total += rows * (1 + (columns * bits + 7) // 8)
    return total


def _probe(source, width, height):
    """Bound framing, geometry and complete IDAT zlib before Pillow pixel decode."""
    source.seek(0)
    if source.read(8) != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Only original static PNG is supported')
    first = True
    palette_seen = False
    idat_seen = False
    idat_ended = False
    depth = color = 0
    decoder = zlib.decompressobj()
    decoded = 0
    expected_bytes = 0
    while True:
        header = source.read(8)
        if len(header) != 8:
            raise ValueError('Truncated PNG framing')
        length, kind = struct.unpack('>I4s', header)
        if length > MAX_PNG_BYTES or kind in (b'acTL', b'fcTL', b'fdAT'):
            raise ValueError('Oversized or animated PNG is not supported')
        if kind == b'IHDR' and not first:
            raise ValueError('Duplicate PNG header')
        if not (kind[0] & 0x20) and kind not in (b'IHDR', b'PLTE', b'IDAT', b'IEND'):
            raise ValueError('Unsupported critical PNG chunk')
        if kind != b'IDAT' and idat_seen:
            idat_ended = True
        if first:
            if kind != b'IHDR' or length != 13:
                raise ValueError('Invalid PNG header')
            size = source.read(13)
            if len(size) != 13:
                raise ValueError('Truncated PNG header')
            measured = struct.unpack('>II', size[:8])
            if (measured != (width, height) or max(measured) > MAX_DIMENSION
                    or measured[0] * measured[1] > MAX_PIXELS):
                raise ValueError('PNG geometry conflicts with frozen portrait pin')
            expected_bytes = _png_scanline_bytes(size)
            depth, color = size[8:10]
            source.seek(4, 1)
            first = False
        elif kind == b'PLTE':
            if palette_seen or idat_seen:
                raise ValueError('Duplicate or late PNG palette')
            if (color in (0, 4) or not 0 < length <= 3 * 256 or length % 3
                    or (color == 3 and length // 3 > (1 << depth))):
                raise ValueError('Invalid PNG palette color/entry count')
            palette_seen = True
            source.seek(length + 4, 1)
        elif kind == b'IDAT':
            if idat_ended:
                raise ValueError('Noncontiguous PNG IDAT chunks')
            if color == 3 and not palette_seen:
                raise ValueError('Indexed PNG requires a palette before pixels')
            idat_seen = True
            remaining = length
            while remaining:
                requested = min(remaining, STREAM_CHUNK_BYTES)
                pending = source.read(requested)
                if len(pending) != requested:
                    raise ValueError('Truncated PNG compressed pixels')
                remaining -= requested
                if decoder.eof:
                    raise ValueError('Extra PNG compressed stream/data')
                while True:
                    # One discarded block at a time; even hostile inflation cannot
                    # allocate more than 64 KiB or exceed the header's exact ceiling.
                    limit = min(STREAM_CHUNK_BYTES, expected_bytes - decoded + 1)
                    try:
                        output = decoder.decompress(pending, limit)
                    except zlib.error as error:
                        raise ValueError('Invalid PNG zlib stream/checksum') from error
                    decoded += len(output)
                    if decoded > expected_bytes or decoder.unused_data:
                        raise ValueError('Excess PNG pixels or compressed trailing data')
                    pending = decoder.unconsumed_tail
                    if not pending and len(output) < limit:
                        break
            source.seek(4, 1)
        elif kind == b'IEND':
            # Pillow can accept all decoded pixels without the final Adler32 bytes.
            if not decoder.eof or decoded != expected_bytes:
                raise ValueError('Incomplete PNG zlib stream or scanline count')
            # Pillow verify() stops at IEND before checking its CRC (12.3.0).
            if length or source.read(4) != b'\xaeB`\x82':
                raise ValueError('Invalid PNG end checksum')
        else:
            source.seek(length + 4, 1)
        if kind == b'IEND':
            if length or source.tell() != os.fstat(source.fileno()).st_size:
                raise ValueError('PNG has truncated or trailing bytes')
            break
        if source.tell() > MAX_PNG_BYTES:
            raise ValueError('PNG framing exceeds byte bounds')
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        try:
            source.seek(0)
            with Image.open(source, formats=['PNG']) as image:
                if image.size != (width, height) or getattr(image, 'is_animated', False) or getattr(image, 'n_frames', 1) != 1:
                    raise ValueError('Invalid static PNG geometry/frames')
                image.verify()  # CRC/framing, NOT pixel decode.
            source.seek(0)
            with Image.open(source, formats=['PNG']) as image:
                if image.size != (width, height):
                    raise ValueError('Invalid PNG geometry before decode')
                image.load()  # Reopen and decode, never save/re-encode the original.
        except (OSError, SyntaxError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError) as error:
            raise ValueError('Invalid or unsafe PNG media') from error


def _verify(path, width, height, *, digest=None, byte_length=None, links=1):
    expected = _info(path, links)
    if byte_length is not None and expected.st_size != byte_length:
        raise ValueError('Candidate original length mismatch')
    checksum = hashlib.sha256()
    total = 0
    with path.open('rb') as source:
        _same_file(path, source, expected, links)
        while data := source.read(STREAM_CHUNK_BYTES):
            total += len(data)
            if total > MAX_PNG_BYTES:
                raise ValueError('Candidate original exceeds byte cap')
            checksum.update(data)
        actual_digest = 'sha256:' + checksum.hexdigest()
        if total != expected.st_size or (digest is not None and digest != actual_digest):
            raise ValueError('Candidate original digest/size mismatch')
        _probe(source, width, height)
        _same_file(path, source, expected, links)
    return actual_digest, total


def _mkdir(directory):
    _directories(directory / 'placeholder', missing=True)
    missing = []
    parent = directory
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    for parent in reversed(missing):
        parent.mkdir()
        _sync_directory(parent.parent)
    _directories(directory / 'placeholder')


def _unlink_owned(path, expected):
    _directories(path)
    _check_file(path)
    if not os.path.samestat(expected, path.lstat()):
        raise ValueError('Private candidate staging identity changed')
    path.unlink()
    _sync_directory(path.parent)


def _stage(directory, stream, width, height):
    _mkdir(directory)
    path = directory / f'.candidate-{uuid4().hex}.tmp'
    created = None
    try:
        with path.open('xb') as target:
            created = os.fstat(target.fileno())
            total = 0
            checksum = hashlib.sha256()
            while True:
                data = stream.read(STREAM_CHUNK_BYTES)
                if type(data) is not bytes or len(data) > STREAM_CHUNK_BYTES:
                    raise ValueError('Stream must return bounded byte chunks')
                if not data:
                    break
                total += len(data)
                if total > MAX_PNG_BYTES:
                    raise ValueError('Candidate stream exceeds hard byte cap')
                if target.write(data) != len(data):
                    raise OSError('Short candidate staging write')
                checksum.update(data)
            target.flush()
            os.fsync(target.fileno())
        digest, length = _verify(path, width, height)
        if (digest, length) != ('sha256:' + checksum.hexdigest(), total):
            raise ValueError('Staged original differs from supplied stream')
        _sync_directory(directory)
        return path, created, digest, length
    except BaseException:
        if created is not None:
            _unlink_owned(path, created)
        raise


def _exists(path):
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False


def _restage(staging, supplied):
    """Reserved bytes absent/partial: complete only from a fully verified exact retry.

    The SQL-frozen random name is never replaced. A partial restaging write may
    survive death; exact supplied bytes must match its entire prefix before append.
    Unreserved random staging orphans are never discovered/adopted or auto-deleted.
    """
    _directories(staging)
    if _exists(staging):
        _check_file(staging)
        expected = staging.lstat()
        if expected.st_size > MAX_PNG_BYTES:
            raise ValueError('Reserved staging exceeds byte cap')
        mode = 'rb+'
    else:
        expected = None
        mode = 'xb'
    supplied_info = _info(supplied)
    with staging.open(mode) as target, supplied.open('rb') as source:
        _same_file(supplied, source, supplied_info)
        opened = os.fstat(target.fileno())
        if expected is not None and not os.path.samestat(expected, opened):
            raise ValueError('Reserved staging file identity changed')
        prefix = opened.st_size
        remaining = prefix
        while remaining:
            size = min(remaining, STREAM_CHUNK_BYTES)
            if target.read(size) != source.read(size):
                raise ValueError('Conflicting reserved staging prefix')
            remaining -= size
        # Full prefix validated before any mutation; source already matches SQL digest.
        total = prefix
        while data := source.read(STREAM_CHUNK_BYTES):
            total += len(data)
            if total > MAX_PNG_BYTES:
                raise ValueError('Restaged original exceeds hard byte cap')
            if target.write(data) != len(data):
                raise OSError('Short reserved staging write')
        _same_file(supplied, source, supplied_info)
        target.flush()
        os.fsync(target.fileno())
        _check_file(staging)
        if not os.path.samestat(opened, staging.lstat()):
            raise ValueError('Reserved staging identity changed')
    _sync_directory(staging.parent)


def _publish(path, metadata, supplied=None):
    """Exclusive publication and recovery of ONLY the owned exact two-name inode."""
    _directories(path)
    staging = path.with_name(metadata.staging_name)
    verify_args = dict(digest=metadata.digest, byte_length=metadata.byte_length)
    if _exists(path):
        if not _exists(staging):
            _verify(path, metadata.width, metadata.height, **verify_args)
            return
    else:
        if supplied is not None:
            _restage(staging, supplied)
        _verify(staging, metadata.width, metadata.height, **verify_args)
        expected = _info(staging)
        with staging.open('rb+') as source:
            _same_file(staging, source, expected)
            os.fsync(source.fileno())
        os.link(staging, path)  # No overwrite. Death here leaves the two exact aliases.
    infos = (_info(staging, 2), _info(path, 2))
    if not os.path.samestat(*infos):
        raise ValueError('Reserved candidate is not the owned exclusive publication pair')
    _verify(staging, metadata.width, metadata.height, links=2, **verify_args)
    _sync_directory(path.parent)
    staging.unlink()
    _sync_directory(path.parent)
    _verify(path, metadata.width, metadata.height, **verify_args)


def read_anchor_unit_candidate(db: sqlite3.Connection, candidate_id: str, *,
                               expected_unit_digest: str) -> AnchorUnitCandidateV1:
    """Read only published SQL; verify original bytes and immutable offline lineage."""
    _committed(db)
    TypeAdapter(ExactDigest).validate_python(candidate_id, strict=True)
    TypeAdapter(ExactDigest).validate_python(expected_unit_digest, strict=True)
    row = _row(db, candidate_id)
    if row is None or row[8] != 'published':
        raise LookupError('Portrait candidate is not published')
    metadata, body, path, _ = _restore(db, row, expected_unit_digest)
    _verify(path, metadata.width, metadata.height, digest=metadata.digest, byte_length=metadata.byte_length)
    return _record(metadata, body)


def read_anchor_unit_candidate_original(db: sqlite3.Connection, candidate_id: str, *,
        expected_unit_digest: str) -> tuple[AnchorUnitCandidateV1, bytes]:
    """Return bounded VERIFIED ORIGINAL bytes, never a caller/provider-selected path.

    Caller holds the root lock. Capture identity before PNG verification, then
    check the same opened inode/timestamps on the bounded read and hash its returned
    bytes again. A replacement after metadata/media validation is not adopted.
    """
    _committed(db)
    TypeAdapter(ExactDigest).validate_python(candidate_id, strict=True)
    TypeAdapter(ExactDigest).validate_python(expected_unit_digest, strict=True)
    row = _row(db, candidate_id)
    if row is None or row[8] != 'published':
        raise LookupError('Anchor candidate is not published')
    metadata, body, path, _ = _restore(db, row, expected_unit_digest)
    expected = _info(path)
    _verify(path, metadata.width, metadata.height, digest=metadata.digest, byte_length=metadata.byte_length)
    original = bytearray()
    checksum = hashlib.sha256()
    with path.open('rb') as source:
        _same_file(path, source, expected)
        while data := source.read(STREAM_CHUNK_BYTES):
            if len(original) + len(data) > MAX_PNG_BYTES:
                raise ValueError('Candidate original exceeds byte cap')
            original.extend(data)
            checksum.update(data)
        _same_file(path, source, expected)
    if (len(original) != metadata.byte_length or 'sha256:' + checksum.hexdigest() != metadata.digest
            or _row(db, candidate_id) != row):
        raise ValueError('Candidate original/metadata changed during verified read')
    return _record(metadata, body), bytes(original)


def import_anchor_unit_candidate(db: sqlite3.Connection, job_id: str, attempt_id: str, *,
        expected_unit_digest: str, descriptor: PortraitOutputDescriptorV1 | dict,
        stream: BinaryIO | None = None) -> PortraitCandidateV1:
    """Import a bounded original, or finish an exact reserved publication offline.

    First valid import freezes descriptor/bytes/technical metadata. Streamless
    recovery needs existing exact reserved originals. A supplied retry always
    validates and matches the original digest; published loss/corruption never heals.
    No database transaction spans streaming or image decode.
    """
    _committed(db)
    context = _context(db, job_id, attempt_id, expected_unit_digest)
    declared = _descriptor(descriptor, context[3])
    identity = _candidate_id(job_id, attempt_id, declared, context[0].kind)
    intent = context[1]
    directory = _root(db) / 'projects' / intent['project_id'] / 'attempts' / job_id[7:]
    row = _row(db, identity)
    metadata = None
    path = None
    record = None
    if row is not None:
        metadata, body, path, context = _restore(db, row, expected_unit_digest)
        if metadata.descriptor != declared:
            raise ValueError('Candidate descriptor conflicts with original provenance')
        if row[8] == 'published':
            # Fail before reading new bytes: reimport is never a missing-original repair.
            record = read_anchor_unit_candidate(db, identity, expected_unit_digest=expected_unit_digest)
            if stream is None:
                return record
    else:
        if db.execute('SELECT candidate_id FROM portrait_candidates WHERE job_id=? OR attempt_id=?',
                      (job_id, attempt_id)).fetchone():
            raise ValueError('Initial portrait candidate identity conflicts; refusing replacement')
        if stream is None:
            raise ValueError('First candidate import requires original byte stream')
    fresh = None
    owned = None
    reserved = row is not None
    try:
        if stream is not None:
            width, height = context[3]['settings']['width'], context[3]['settings']['height']
            fresh, owned, digest, length = _stage(directory, stream, width, height)
            if metadata is not None:
                assert row is not None
                if (digest, length) != (metadata.digest, metadata.byte_length):
                    raise ValueError('Candidate bytes conflict with frozen original')
                if row[8] == 'published':
                    assert record is not None
                    return record
            else:
                metadata = _metadata(context, declared, digest, length, fresh.name)
                body = canonical_json(metadata, max_bytes=MAX_METADATA_BYTES)
                path = directory / metadata.uri.rsplit('/', 1)[1]
                if _exists(path):
                    raise ValueError('Unreserved candidate destination already exists')
                with _transaction(db):
                    _assert_binding(db, context)
                    db.execute('INSERT INTO portrait_candidates VALUES (?,?,?,?,?,?,?,?,?)',
                        (identity, job_id, attempt_id, expected_unit_digest, context[0].intent_digest,
                         sha256_digest(body), body.decode('utf-8'), metadata.uri, 'reserved'))
                reserved = True
                row = _row(db, identity)
        assert metadata is not None and row is not None and path is not None  # FIRST import requires stream above.
        _publish(path, metadata, fresh if fresh is not None and fresh.name != metadata.staging_name else None)
        # Recheck SQL and pinned files after publication, then short guarded finalization.
        _restore(db, row, expected_unit_digest)
        with _transaction(db):
            _assert_binding(db, context)
            changed = db.execute("UPDATE portrait_candidates SET publication_state='published' WHERE "
                'candidate_id=? AND job_id=? AND attempt_id=? AND unit_input_digest=? AND intent_digest=? AND '
                "metadata_digest=? AND metadata_body=? AND uri=? AND publication_state='reserved'", row[:8])
            if changed.rowcount != 1:
                raise ValueError('Candidate reservation changed during publication')
        return read_anchor_unit_candidate(db, identity, expected_unit_digest=expected_unit_digest)
    finally:
        # Do not delete the SQL-pinned original on failure; it is the recovery source.
        if fresh is not None and (metadata is None or not reserved or fresh.name != metadata.staging_name):
            _unlink_owned(fresh, owned)


def read_portrait_candidate(db: sqlite3.Connection, candidate_id: str, *,
                            expected_unit_digest: str) -> PortraitCandidateV1:
    """Legacy 5B entrypoint remains strictly zero-reference hero-face portrait only."""
    _committed(db)
    TypeAdapter(ExactDigest).validate_python(candidate_id, strict=True)
    row = _row(db, candidate_id)
    if row is None or row[8] != 'published':
        raise LookupError('Portrait candidate is not published')
    render_job_store.read_portrait_job(db, row[1], expected_unit_digest=expected_unit_digest)
    return read_anchor_unit_candidate(db, candidate_id, expected_unit_digest=expected_unit_digest)


def import_portrait_candidate(db: sqlite3.Connection, job_id: str, attempt_id: str, *,
        expected_unit_digest: str, descriptor: PortraitOutputDescriptorV1 | dict,
        stream: BinaryIO | None = None) -> PortraitCandidateV1:
    """Legacy portrait-only boundary; original IDs, bytes and metadata remain exact."""
    render_job_store.read_portrait_job(db, job_id, expected_unit_digest=expected_unit_digest)
    return import_anchor_unit_candidate(db, job_id, attempt_id, expected_unit_digest=expected_unit_digest,
                                        descriptor=descriptor, stream=stream)
