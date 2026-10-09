"""One bounded native reference tick, plus GET-only readiness before a sheet POST.

Caller holds the root lock. No scheduler, retry allocator, guessed receipt or prompt
authorization here. A new committed upload claim grants one multipart POST only;
saved receipts resume GET verification. Local integrity/rights failures never heal.
"""

import asyncio
import hashlib
import io
import json
import sqlite3
from collections.abc import Callable
from typing import Any

import httpx
from pydantic import TypeAdapter

from backend import anchor_parent_resolver as resolver, anchor_reference_store as store
from backend import comfyui, portrait_candidate_store as candidates, portrait_submission_store as submissions
from backend import portrait_worker as native, render_job_store as jobs
from backend.batch_generation import BatchConnectionPinV1
from backend.config import ComfyUIConfigError, resolve_comfyui_connection
from backend.domain import canonical_json, sha256_digest


class AnchorReferenceWorkerError(ValueError):
    """Safe readiness/configuration rejection; no endpoint, provider body or credentials."""

    def __init__(self, code: str):
        self.code = code
        super().__init__('Anchor reference readiness rejected: ' + code)


def _args(record, *, revision=True):
    args: dict[str, Any] = dict(expected_project_id=record.intent.project_id, expected_unit_digest=record.intent.unit_input_digest,
                expected_intent_digest=record.intent_digest)
    if revision:
        args['expected_revision'] = record.revision
    return args


def _read(db, job_id, **selectors):
    try:
        return store.read_anchor_reference_transfer(db, job_id, **selectors)
    except (ValueError, LookupError):
        raise AnchorReferenceWorkerError('local_reference_integrity') from None
    # OSError remains a real storage failure; never reinterpret it as native ambiguity.


def _fresh(db, record):
    if _read(db, record.intent.job_id, **_args(record, revision=False)) != record:
        raise AnchorReferenceWorkerError('reference_revision_conflict')


def _originals(db, record):
    """Resolve current exact local originals before each effect (not stored media bodies)."""
    try:
        job = jobs.read_anchor_unit_job(db, record.intent.job_id, expected_unit_digest=record.intent.unit_input_digest)
        parent = record.intent.references[0].parent
        resolved = resolver.resolve_sheet_parents(db, parent.batch_id, job.prepared_input.unit_key,
            expected_batch_digest=parent.batch_input_digest, expected_project_id=record.intent.project_id,
            parent_bindings=job.prepared_input.parent_bindings, expected_child_digest=record.intent.unit_input_digest,
            expected_child_job_id=record.intent.job_id)
        for item, original in zip(record.intent.references, resolved, strict=True):
            pinned = store.ReferenceParentPinV1(**{key: getattr(original, key)
                for key in store.ReferenceParentPinV1.model_fields if key != 'byte_length'}, byte_length=len(original.original_bytes))
            if item.parent != pinned or item.role != original.role:
                raise ValueError('Exact resolved original pin conflict')
        _fresh(db, record)
        return resolved
    except (ValueError, LookupError):
        raise AnchorReferenceWorkerError('local_parent_integrity') from None


def _client(record, transport):
    try:
        settings = resolve_comfyui_connection(record.intent.connection.connection)
        connection = BatchConnectionPinV1(connection=settings.connection, endpoint_digest='sha256:' + settings.endpoint_digest)
        if connection != record.intent.connection or settings.verify is False:
            raise ValueError('Connection pin conflict')
        headers = {'Accept': 'application/json', 'Accept-Encoding': 'identity'}
        if settings.auth_token:
            headers['Authorization'] = 'Bearer ' + settings.auth_token
        return httpx.AsyncClient(base_url=settings.endpoint, headers=headers, verify=settings.verify, trust_env=False,
            follow_redirects=False, timeout=httpx.Timeout(15.0, connect=5.0), transport=transport)
    except (ComfyUIConfigError, ValueError, TypeError):
        raise AnchorReferenceWorkerError('client_configuration') from None


def _block(db, record, role, reason):
    _fresh(db, record)  # Cannot persist a native block if local originals/rights stopped being valid.
    index = store._role(role)
    current = record.references[index]
    if current.state == 'blocked_sent' and current.reason == reason:
        return record
    return store.block_anchor_reference(db, record.intent.job_id, role=role, reason=reason, **_args(record))


async def _upload(db, client, record, index):
    original = _originals(db, record)[index].original_bytes
    upload = record.intent.references[index]
    # Fresh successful CAS grants the ONE POST. Every reopened dispatch marker is sent-possible.
    dispatched = store.claim_anchor_reference_upload(db, record.intent.job_id, role=upload.role, **_args(record))
    try:
        async with asyncio.timeout(native.REQUEST_TIMEOUT), client.stream('POST', 'upload/image',
            files={'image': (upload.name, original, 'image/png')},
            data={'type': 'input', 'overwrite': 'false', 'subfolder': upload.subfolder}) as response:
            if response.status_code != 200:
                raise native._ProtocolError('upload_status')
            length = native._headers(response, native.MAX_JSON_BYTES, 'application/json')
            body = io.BytesIO()
            await native._stream_body(response, native.MAX_JSON_BYTES, length, body)
            data = body.getvalue()
            try:
                data.decode('utf-8')
                if b'\0' in data:
                    raise ValueError('Not native UTF8')
                receipt = comfyui._parse_json(data)
                native._canonical(receipt)  # Nested nonfinite/overflow/surrogate JSON also refuses.
            except (ValueError, UnicodeError, RecursionError):
                raise native._ProtocolError('upload_json') from None
    except native.HTTP_ERRORS:
        return _block(db, dispatched, upload.role, 'acceptance_unknown')
    except native._ProtocolError:
        return _block(db, dispatched, upload.role, 'receipt_invalid')
    _fresh(db, dispatched)
    try:
        # Validate actual native fields/namespace, commit them BEFORE any GET.
        return store.record_anchor_reference_receipt(db, record.intent.job_id, role=upload.role,
            receipt=receipt, **_args(dispatched))
    except (ValueError, TypeError):
        return _block(db, dispatched, upload.role, 'receipt_invalid')


class _OriginalHash:
    def __init__(self):
        self.checksum = hashlib.sha256()
        self.byte_length = 0

    def write(self, chunk):
        self.checksum.update(chunk)
        self.byte_length += len(chunk)

    @property
    def digest(self):
        return 'sha256:' + self.checksum.hexdigest()


async def _remote_original(db, client, record, index, *, timeout=native.REQUEST_TIMEOUT):
    _originals(db, record)  # Local rights/bytes are checked immediately before this GET.
    item, receipt = record.intent.references[index], record.references[index].receipt
    if receipt is None:
        raise AnchorReferenceWorkerError('saved_receipt_required')
    sink = _OriginalHash()
    async with asyncio.timeout(timeout), client.stream('GET', 'view', params={
        'filename': receipt.name, 'subfolder': receipt.native_subfolder, 'type': receipt.type,
    }, headers={'Accept': 'image/png'}) as response:
        if response.status_code != 200:
            raise native._ProtocolError('reference_view_status')
        length = native._headers(response, candidates.MAX_PNG_BYTES, 'image/png')
        await native._stream_body(response, candidates.MAX_PNG_BYTES, length, sink)
    _fresh(db, record)
    if (sink.digest, sink.byte_length) != (item.parent.digest, item.parent.byte_length):
        raise native._ProtocolError('reference_original_mismatch')
    # Exact hash/length equality to the already decoded local PNG proves original
    # bytes; no remote re-encoding, arbitrary path or separate unbounded buffer.
    return sink.digest, sink.byte_length


async def _verify(db, client, record, index):
    role = record.intent.references[index].role
    try:
        digest, length = await _remote_original(db, client, record, index)
    except (*native.HTTP_ERRORS, native._ProtocolError):
        return _block(db, record, role, 'remote_invalid')
    receipt = record.references[index].receipt
    assert receipt is not None
    return store.verify_anchor_reference_remote(db, record.intent.job_id, role=role,
        expected_receipt_digest=receipt.digest, remote_digest=digest,
        source_digest=record.intent.references[index].parent.digest, byte_length=length, **_args(record))


async def tick_anchor_references(db: sqlite3.Connection, job_id: str, *, expected_project_id: str,
        expected_unit_digest: str, expected_intent_digest: str, expected_revision: int,
        transport: httpx.AsyncBaseTransport | None = None) -> store.AnchorReferenceTransferV1:
    """One role/tick: at most one multipart POST + one original GET, then local finalize.

    Authorized reference intent is required. Unknown upload acceptance NEVER retries
    or guesses a receipt. A known receipt retries only its exact GET. Finalized reads
    return offline without current endpoint configuration or HTTP client creation.
    """
    record = _read(db, job_id, expected_project_id=expected_project_id, expected_unit_digest=expected_unit_digest,
                   expected_intent_digest=expected_intent_digest)
    TypeAdapter(store.Revision).validate_python(expected_revision, strict=True)
    if record.revision != expected_revision:
        raise AnchorReferenceWorkerError('reference_revision_conflict')
    if record.state == 'finalized':
        return record
    index = next((i for i, item in enumerate(record.references) if item.state != 'verified'), None)
    if index is None:
        return store.finalize_anchor_references(db, job_id, **_args(record))
    facts, upload = record.references[index], record.intent.references[index]
    if facts.state == 'blocked_unsent':
        return record  # Explicit readiness correction belongs to the trusted caller.
    if facts.dispatch_revision is not None and facts.receipt is None:
        if facts.state == 'blocked_sent':
            return record  # Preserve the already committed reason and revision.
        return _block(db, record, upload.role, 'acceptance_unknown')
    client = _client(record, transport)
    try:
        async with asyncio.timeout(native.TICK_TIMEOUT), client:
            if facts.state == 'ready':
                record = await _upload(db, client, record, index)
            if record.references[index].receipt is None:
                return record
            record = await _verify(db, client, record, index)
            if all(item.state == 'verified' for item in record.references):
                record = store.finalize_anchor_references(db, job_id, **_args(record))
            return record
    except AnchorReferenceWorkerError:
        raise
    except (ValueError, LookupError, *native.HTTP_ERRORS):
        raise AnchorReferenceWorkerError('reference_tick_integrity_or_timeout') from None


async def verify_sheet_remote_inputs(db: sqlite3.Connection, client: httpx.AsyncClient,
        submission: submissions.SheetSubmissionV1, clock_ms: Callable[[], int]) -> None:
    """GET-only first-prompt readiness. Failure leaves the sheet definitely UNSENT.

    Revalidate BOTH final receipt originals and local source/parents between awaits;
    never upload, refresh a binding, claim dispatch or mutate the finalized transfer.
    Accepted/reconciliation and completed ticks must not call this boundary.
    """
    preview = submission.preview
    record = _read(db, preview.job_id, expected_project_id=preview.source_plan_ref.project_id,
        expected_unit_digest=preview.unit_input_digest, expected_intent_digest=preview.reference_intent_digest)
    if record.state != 'finalized' or sha256_digest(canonical_json(record)) != preview.final_reference_digest:
        raise AnchorReferenceWorkerError('final_reference_pin_mismatch')
    try:
        for index in (0, 1):
            native._fresh(db, submission)
            await _remote_original(db, client, record, index, timeout=native._budget(submission, clock_ms))
            native._fresh(db, submission)
        _originals(db, record)
        native._budget(submission, clock_ms)  # No stale/expired claim after the last await.
    except (*native.HTTP_ERRORS, native._ProtocolError):
        raise AnchorReferenceWorkerError('remote_originals_unavailable') from None
