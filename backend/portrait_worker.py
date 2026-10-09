"""One bounded native anchor tick; not a scheduler, public route or graph runner.

Caller owns the data-root OS lock and services one job at a time. Only a freshly
committed dispatch CAS permits POST, once. Restart/timeout/empty history never prove
unsent. Native tuple/correlation semantics are an explicit server-specific contract
to verify during the later live smoke, not a provider idempotency guarantee.
"""

import asyncio
import copy
from collections.abc import Callable
import io
import json
import math
import sqlite3
import ssl
import tempfile
import time
from urllib.parse import quote
from typing import Any, BinaryIO, cast

import httpx
from pydantic import TypeAdapter

from backend import comfyui, portrait_candidate_store as candidates, portrait_submission_store as store
from backend import render_job_store
from backend.batch_generation import BatchConnectionPinV1
from backend.config import ComfyUIConfigError, resolve_comfyui_connection
from backend.domain import canonical_json, sha256_digest
from backend.story_store import _root


REQUEST_TIMEOUT = 15.0
TICK_TIMEOUT = 60.0
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_NATIVE_RECORDS = 4096
HTTP_ERRORS = (TimeoutError, httpx.HTTPError, ssl.SSLError)


class PortraitWorkerError(ValueError):
    """Safe configuration/integrity rejection; never carries endpoints or provider bodies."""

    def __init__(self, code: str):
        self.code = code
        super().__init__('Portrait worker rejected configuration or exact durable identity: ' + code)


class _ProtocolError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _evidence(record, kind, prompt_id, native):
    return store.PortraitSubmissionEvidenceV1(kind=kind, prompt_id=prompt_id,
        digest=sha256_digest(_canonical(native)), wire_digest=record.preview.wire_digest,
        endpoint_digest=record.preview.endpoint_digest)


def _clock() -> int:
    return time.time_ns() // 1_000_000


def _now(clock):
    return TypeAdapter(store.Timestamp).validate_python(clock(), strict=True)


def _args(record) -> dict[str, Any]:
    return dict(expected_unit_digest=record.preview.unit_input_digest,
                expected_wire_digest=record.preview.wire_digest, expected_revision=record.revision)


def _fresh(db, record):
    current = store.read_anchor_unit_submission(db, record.preview.job_id,
        expected_unit_digest=record.preview.unit_input_digest, expected_wire_digest=record.preview.wire_digest)
    if current != record:
        raise PortraitWorkerError('revision_conflict')


def _block(db, record, reason):
    _fresh(db, record)
    if record.state == 'blocked' and record.reason == reason:
        return record
    return store.block_anchor_unit_submission(db, record.preview.job_id, **_args(record), reason=reason)


def _output_deadline(record, now):
    start, end = record.output_recovery_authorized_at_ms, record.output_recovery_deadline_ms
    return max(record.deadline_ms, end) if start is not None and end is not None and start <= now else record.deadline_ms


def _budget(record, clock, *, reconcile=False, output=False):
    now = _now(clock)
    deadline = _output_deadline(record, now) if output else record.deadline_ms
    remaining = (deadline - now) / 1000
    if remaining <= 0:
        if not reconcile:
            raise _ProtocolError('deadline')
        # Read-only reconciliation remains possible after expiry; it never renews dispatch/media budgets.
        return REQUEST_TIMEOUT
    return min(REQUEST_TIMEOUT, remaining)


def _headers(response, limit, media_type):
    if 'content-range' in response.headers:
        raise _ProtocolError('unsolicited_partial_transfer')
    if any(len(response.headers.get_list(name)) > 1 for name in
           ('content-length', 'content-encoding', 'content-type', 'transfer-encoding')):
        raise _ProtocolError('ambiguous_headers')
    if response.headers.get('content-encoding', 'identity').strip().lower() != 'identity':
        raise _ProtocolError('encoded_body')
    if response.headers.get('content-type', '').split(';')[0].strip().lower() != media_type:
        raise _ProtocolError('content_type')
    length = response.headers.get('content-length')
    transfer = response.headers.get('transfer-encoding')
    if transfer is not None and (transfer.strip().lower() != 'chunked' or length is not None):
        raise _ProtocolError('transfer_encoding')
    if length is not None:
        if not length.isascii() or not length.isdigit() or len(length) > 10 or int(length) > limit:
            raise _ProtocolError('body_length')
        return int(length)
    return None


async def _stream_body(response, limit, length, sink):
    count = 0
    async for chunk in response.aiter_bytes(chunk_size=candidates.STREAM_CHUNK_BYTES):
        count += len(chunk)
        if count > limit or (length is not None and count > length):
            raise _ProtocolError('body_limit')
        sink.write(chunk)
    if length is not None and count != length:
        raise _ProtocolError('partial_body')


async def _json(client, route, record, clock, *, post=False):
    async with asyncio.timeout(_budget(record, clock, reconcile=not post)), client.stream(
        'POST' if post else 'GET', route,
        content=record.preview.wire_body if post else None,
        headers={'Content-Type': 'application/json'} if post else None,
    ) as response:
        # A bounded valid response ID is saved before later status/contract checks, even on HTTP error.
        if not post and response.status_code != 200:
            raise _ProtocolError('http_status')
        length = _headers(response, MAX_JSON_BYTES, 'application/json')
        body = io.BytesIO()
        await _stream_body(response, MAX_JSON_BYTES, length, body)
        try:
            data = body.getvalue()
            data.decode('utf-8')
            if b'\0' in data:  # Reject UTF-16/32 autodetection and unescaped JSON control bytes.
                raise ValueError('Not native UTF-8 JSON')
            value = comfyui._parse_json(data)
            _canonical(value)  # Also rejects overflow floats (1e999), surrogates and nonfinite nested values.
        except (ValueError, UnicodeError, RecursionError):
            raise _ProtocolError('malformed_json') from None
        return response.status_code, value


def _number(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _observed_graph_digest(observed, frozen, schemas):
    """Only native int->float coercion at frozen schema FLOAT scalars is equivalent.

    Normalize a private comparison copy back to frozen types, never wire/native
    evidence. Booleans, INT inputs, arrays/links and changed numbers remain exact.
    """
    graph = copy.deepcopy(observed)
    for node_id, expected in frozen.items():
        actual = graph.get(node_id)
        if type(actual) is not dict or type(actual.get('inputs')) is not dict:
            continue
        schema = schemas.get(expected['class_type'], {}).get('input', {})
        fields = {**schema.get('required', {}), **schema.get('optional', {})}
        for name, value in expected['inputs'].items():
            received = actual['inputs'].get(name)
            declaration = fields.get(name)
            if (type(value) is int and type(received) is float and math.isfinite(received) and received == value
                    and type(declaration) is list and declaration and declaration[0] == 'FLOAT'):
                actual['inputs'][name] = value
    return sha256_digest(_canonical(graph))


def _match(item, record, output, schemas=None):
    if (type(item) is not list or len(item) != 5 or not _number(item[0])
            or type(item[2]) is not dict or not item[2] or type(item[3]) is not dict
            or type(item[4]) is not list or not item[4]
            or any(type(node) is not str or not node for node in item[4])):
        raise _ProtocolError('native_tuple')
    try:
        prompt_id = TypeAdapter(store.PromptId).validate_python(item[1], strict=True)
    except ValueError:
        raise _ProtocolError('native_prompt_id') from None
    wire = json.loads(record.preview.wire_body)
    namespace = ('kinodel_anchor_unit_v1' if isinstance(record.preview, store.AnchorUnitSubmissionPreviewV1)
                 else 'kinodel_portrait_v1')
    expected = wire['extra_data'][namespace]
    correlation = item[3].get(namespace)
    exact = (_observed_graph_digest(item[2], wire['prompt'], schemas or {}) == record.preview.graph_digest
             and correlation == expected and item[4] == [output['node_id']]
             and ('client_id' not in item[3] or item[3]['client_id'] == wire['client_id']))
    if not exact and _has_owned_signal(item, record):
        raise _ProtocolError('correlation_conflict')
    if exact and record.prompt_id is not None and prompt_id != record.prompt_id:
        raise _ProtocolError('multiple_prompt_ids')
    return prompt_id if exact else None


def _native_ids(item, history_key=None):
    identifiers = []
    for value in (item[1] if type(item) is list and len(item) > 1 else None, history_key):
        try:
            identifier = TypeAdapter(store.PromptId).validate_python(value, strict=True)
        except ValueError:
            continue
        if identifier not in identifiers:
            identifiers.append(identifier)
    return identifiers


def _has_owned_signal(item: Any, record: store.PortraitSubmissionV1, history_key: Any = None) -> bool:
    """Explicit native identity/correlation only; missing identity is not an own signal."""
    if record.prompt_id is not None and record.prompt_id in _native_ids(item, history_key):
        return True
    extra = item[3] if type(item) is list and len(item) > 3 and type(item[3]) is dict else {}
    correlations = [extra.get(name) for name in ('kinodel_portrait_v1', 'kinodel_anchor_unit_v1')]
    return (extra.get('client_id') == json.loads(record.preview.wire_body)['client_id'] or any(
            type(value) is dict and (value.get('job_id') == record.preview.job_id
                or value.get('attempt_id') == record.preview.attempt_id) for value in correlations))


def _definitely_unrelated(item, record, history_key=None):
    """Inspect available identity BEFORE ignoring broken shape; own signals always win."""
    if _has_owned_signal(item, record, history_key):
        return False
    identifiers = _native_ids(item, history_key)
    if record.prompt_id is not None and identifiers:
        return True  # Every validated available native ID is disjoint from the immutable owned ID.
    # An unknown owned prompt ID cannot be distinguished by a foreign-looking native ID alone.
    # Require a complete valid disjoint job/attempt pair; one missing identity stays ambiguous.
    extra = item[3] if type(item) is list and len(item) > 3 and type(item[3]) is dict else {}
    for value in (extra.get(name) for name in ('kinodel_portrait_v1', 'kinodel_anchor_unit_v1')):
        if type(value) is not dict:
            continue
        try:
            TypeAdapter(store.ExactDigest).validate_python(value.get('job_id'), strict=True)
            TypeAdapter(store.ExactDigest).validate_python(value.get('attempt_id'), strict=True)
        except ValueError:
            continue
        return True
    return False


def _matches(queue, history, record, output, schemas=None, *, diagnostics):
    if (type(queue) is not dict or set(queue) != {'queue_running', 'queue_pending'}
            or any(type(queue[key]) is not list for key in queue)
            or type(history) is not dict
            or len(history) + sum(len(values) for values in queue.values()) > MAX_NATIVE_RECORDS):
        raise _ProtocolError('native_shape')
    matches, quarantined = {}, []
    entries = [('queue', None, item) for item in [*queue['queue_running'], *queue['queue_pending']]]
    entries.extend(('history', key, native) for key, native in history.items())
    for source, key, native in entries:
        item = native if source == 'queue' else native.get('prompt') if type(native) is dict else None
        identifiers = _native_ids(item, key)
        owned_signal = _has_owned_signal(item, record, key) or any(identifier in matches for identifier in identifiers)
        if owned_signal:
            conflicting = [diagnostic for diagnostic, previous_ids in quarantined
                           if any(identifier in previous_ids for identifier in identifiers)]
            if conflicting:
                # Clean immediately, before tuple/history validation or any later scan error.
                diagnostics[:] = [diagnostic for diagnostic in diagnostics if diagnostic not in conflicting]
                raise _ProtocolError('correlation_conflict')
        try:
            if source == 'history' and (type(native) is not dict or 'prompt' not in native):
                raise _ProtocolError('history_shape')
            prompt_id = _match(item, record, output, schemas)
            if prompt_id is None and owned_signal:
                raise _ProtocolError('correlation_conflict')
            if source == 'history':
                assert type(item) is list  # _match validated the complete native tuple.
                if key != item[1]:
                    raise _ProtocolError('history_identity')
                if prompt_id is None:
                    _history_status(native)  # Foreign history still needs a well-formed native status.
        except _ProtocolError as error:
            if (error.code not in ('native_tuple', 'native_prompt_id', 'history_shape', 'history_identity', 'history_status')
                    or owned_signal or not _definitely_unrelated(item, record, key)):
                raise
            diagnostic = store.SubmissionDiagnosticV1(kind='broken_job', source=source,
                prompt_id=identifiers[0] if identifiers else None, reason=error.code,
                digest=sha256_digest(_canonical(native if source == 'queue' else {'key': key, 'record': native})))
            quarantined.append((diagnostic, identifiers))
            if diagnostic not in diagnostics and len(diagnostics) < store.MAX_SUBMISSION_DIAGNOSTICS:
                diagnostics.append(diagnostic)
            continue
        if prompt_id is None:
            continue  # Valid unrelated records are not broken_job diagnostics.
        if source == 'queue':
            if prompt_id in matches and matches[prompt_id][1] != item:
                raise _ProtocolError('conflicting_queue_records')
            matches[prompt_id] = ('queue', item, None)
        else:
            matches[prompt_id] = ('history', native, native)
    if len(matches) > 1:
        raise _ProtocolError('multiple_prompt_ids')
    return next(iter(matches.items())) if matches else None


def _history_status(native):
    status = native.get('status')
    if (type(status) is not dict or status.get('status_str') not in ('success', 'error')
            or type(status.get('completed')) is not bool or type(status.get('messages')) is not list
            or any(type(message) is not list or len(message) != 2 or type(message[0]) is not str
                   or type(message[1]) is not dict for message in status['messages'])):
        raise _ProtocolError('history_status')
    return status


def _outcome(native, output):
    status = _history_status(native)
    if status['status_str'] == 'error':
        return None  # Exact native history proves provider failure; not absence/eviction.
    if not status['completed'] or any(message[0] in ('execution_error', 'execution_interrupted')
                                      for message in status['messages']):
        raise _ProtocolError('unsuccessful_history')
    outputs = native.get('outputs')
    if type(outputs) is not dict or type(outputs.get(output['node_id'])) is not dict:
        raise _ProtocolError('missing_declared_output')
    images = outputs[output['node_id']].get(output['history_key'])
    if type(images) is not list or len(images) != 1 or type(images[0]) is not dict:
        raise _ProtocolError('partial_output')
    try:
        image = images[0]
        # Native Windows separators are transport spelling, not managed paths.
        subfolder = image.get('subfolder')
        normalized = {**image, 'subfolder': subfolder.replace('\\', '/') if type(subfolder) is str else subfolder}
        return candidates.PortraitOutputDescriptorV1(node_id=output['node_id'], history_key=output['history_key'],
            index=0, mime_type=output['media_type'], **normalized)
    except (ValueError, TypeError):
        raise _ProtocolError('output_descriptor') from None


async def _submit(db, client, record, clock):
    _fresh(db, record)
    now = _now(clock)
    if now >= record.deadline_ms:
        return store.fail_anchor_unit_submission(db, record.preview.job_id, **_args(record), reason='deadline_exceeded')
    if isinstance(record, store.SheetSubmissionV1):
        from backend import anchor_reference_worker as references
        try:
            await references.verify_sheet_remote_inputs(db, client, record, clock)
        except references.AnchorReferenceWorkerError:
            # Definitely-unsent readiness failure, not a post-dispatch blocked fact.
            raise PortraitWorkerError('sheet_reference_readiness') from None
        _fresh(db, record)
        now = _now(clock)
        if now >= record.deadline_ms:
            return store.fail_anchor_unit_submission(db, record.preview.job_id, **_args(record), reason='deadline_exceeded')
    # This successful new CAS, not the returned/reopened state, is the ONE send permission.
    claim = (store.claim_portrait_dispatch if type(record) is store.PortraitSubmissionV1
             else store.claim_anchor_unit_dispatch)
    dispatched = claim(db, record.preview.job_id, **_args(record), now_ms=now)
    try:
        status, value = await _json(client, 'prompt', dispatched, clock, post=True)
        if type(value) is not dict:
            raise _ProtocolError('prompt_response')
        try:
            prompt_id = TypeAdapter(store.PromptId).validate_python(value.get('prompt_id'), strict=True)
        except ValueError:
            raise _ProtocolError('prompt_response_id') from None
    except (*HTTP_ERRORS, _ProtocolError):
        return _block(db, dispatched, 'acceptance_unknown')
    _fresh(db, dispatched)
    accept = (store.record_portrait_acceptance if type(record) is store.PortraitSubmissionV1
              else store.record_anchor_unit_acceptance)
    accepted = accept(db, record.preview.job_id, **_args(dispatched),
        prompt_id=prompt_id, evidence=_evidence(dispatched, 'prompt_response', prompt_id, value))
    if (not 200 <= status < 300 or not _number(value.get('number'))
            or type(value.get('node_errors')) is not dict or value['node_errors']):
        return _block(db, accepted, 'contract_error')
    return accepted


async def _finish(db, client, record, clock, descriptor, proof, native_subfolder):
    _fresh(db, record)
    row = db.execute('SELECT candidate_id,publication_state FROM portrait_candidates WHERE job_id=?',
                     (record.preview.job_id,)).fetchone()
    candidate = None
    import_args = dict(expected_unit_digest=record.preview.unit_input_digest, descriptor=descriptor)
    if row is not None:
        try:
            candidate = candidates.import_anchor_unit_candidate(db, record.preview.job_id, record.preview.attempt_id, **import_args)
        except (OSError, ValueError, LookupError):
            if row[1] == 'published':
                return _block(db, record, 'output_invalid')  # NEVER fetch bytes to heal published originals.
            # Exact reserved import may need its verified stream to finish a partial original.
    if candidate is None:
        now = _now(clock)
        if now >= _output_deadline(record, now):
            return _block(db, record, 'deadline_exceeded')
        try:
            # No provider filename ever becomes a path; a private spool is only transport scratch.
            with tempfile.SpooledTemporaryFile(max_size=1024 * 1024, mode='w+b', dir=str(_root(db))) as spool:
                async with asyncio.timeout(_budget(record, clock, output=True)), client.stream('GET', 'view', params={
                    'filename': descriptor.filename, 'subfolder': native_subfolder, 'type': descriptor.type,
                }, headers={'Accept': 'image/png'}) as response:
                    if response.status_code != 200:
                        raise _ProtocolError('view_status')
                    length = _headers(response, candidates.MAX_PNG_BYTES, 'image/png')
                    await _stream_body(response, candidates.MAX_PNG_BYTES, length, spool)
                _fresh(db, record)
                now = _now(clock)
                if now >= _output_deadline(record, now):
                    return _block(db, record, 'deadline_exceeded')
                spool.seek(0)
                candidate = candidates.import_anchor_unit_candidate(db, record.preview.job_id,
                    record.preview.attempt_id, stream=cast(BinaryIO, spool), **import_args)
        except (*HTTP_ERRORS, _ProtocolError, OSError):
            now = _now(clock)
            return _block(db, record, 'deadline_exceeded' if now >= _output_deadline(record, now) else 'output_invalid')
        except ValueError as error:
            if isinstance(error, PortraitWorkerError):
                raise
            _fresh(db, record)
            return _block(db, record, 'output_invalid')
    _fresh(db, record)
    complete = (store.complete_portrait_submission if type(record) is store.PortraitSubmissionV1
                else store.complete_anchor_unit_submission)
    return complete(db, record.preview.job_id, **_args(record),
        candidate_id=candidate.candidate_id, evidence=proof)


async def _reconcile(db, client, record, clock, output, schemas, *, revalidate_contract=False):
    diagnostics = []
    try:
        _, queue = await _json(client, 'queue', record, clock)
        _fresh(db, record)
        route = 'history/' + quote(record.prompt_id, safe='') if record.prompt_id else 'history'
        _, history = await _json(client, route, record, clock)
        matched = _matches(queue, history, record, output, schemas, diagnostics=diagnostics)
    except HTTP_ERRORS:
        if revalidate_contract:
            return record
        return _block(db, record, 'history_unavailable' if record.prompt_id else 'acceptance_unknown')
    except _ProtocolError as error:
        if revalidate_contract:
            return _save_diagnostics(db, record, diagnostics)
        if error.code == 'http_status':
            return _block(db, record, 'history_unavailable' if record.prompt_id else 'acceptance_unknown')
        return _save_diagnostics(db, _block(db, record, 'contract_error'), diagnostics)
    _fresh(db, record)
    if matched is None:
        if revalidate_contract:
            return _save_diagnostics(db, record, diagnostics)
        return _save_diagnostics(db, _block(db, record, 'history_unavailable' if record.prompt_id else 'acceptance_unknown'), diagnostics)
    prompt_id, (kind, native, completed_history) = matched
    proof = _evidence(record, kind, prompt_id, native)
    accept = (store.record_portrait_acceptance if type(record) is store.PortraitSubmissionV1
              else store.record_anchor_unit_acceptance)
    if record.state in ('dispatching', 'blocked') and not revalidate_contract:
        record = accept(db, record.preview.job_id, **_args(record), prompt_id=prompt_id, evidence=proof)
    # Dispatching revision=1 is a fixed SQL contract. Persist diagnostics only after
    # independent matching acceptance or a fail-closed block, never invent either fact.
    record = _save_diagnostics(db, record, diagnostics)
    if completed_history is None:
        if revalidate_contract:
            return record
        return _block(db, record, 'deadline_exceeded') if _now(clock) >= record.deadline_ms else record
    try:
        descriptor = _outcome(completed_history, output)
    except _ProtocolError:
        if revalidate_contract:
            return record
        return _block(db, record, 'contract_error')
    if descriptor is None:
        if revalidate_contract:
            return record  # Failure is not successful contract revalidation.
        return store.fail_anchor_unit_submission(db, record.preview.job_id, **_args(record), reason='provider_failed', evidence=proof)
    if revalidate_contract:
        record = accept(db, record.preview.job_id, **_args(record),
            prompt_id=prompt_id, evidence=proof, revalidate_contract=True)
    native_subfolder = completed_history['outputs'][output['node_id']][output['history_key']][0]['subfolder']
    return await _finish(db, client, record, clock, descriptor, proof, native_subfolder)


def _save_diagnostics(db, record, diagnostics):
    _fresh(db, record)
    if not diagnostics:
        return record
    return store.record_submission_diagnostics(db, record.preview.job_id, **_args(record), diagnostics=diagnostics)


async def tick_anchor_unit_job(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                           expected_wire_digest: str, expected_revision: int,
                            revalidate_contract: bool = False,
                            transport: httpx.AsyncBaseTransport | None = None,
                            clock_ms: Callable[[], int] = _clock,
                            _portrait_only: bool = False) -> store.PortraitSubmissionV1:
    """Advance one authorized portrait/background or exact finalized-reference sheet.

    Authorized sheet tick: at most two remote-original GETs before a conditional ONE POST;
    other authorized ticks: at most ONE POST, no polling. Later/revalidation ticks:
    at most two bounded queue/history GETs and one bounded /view, never POST/upload.
    No sleep, automatic POST retry, fallback, live registry/schema lookup, browser wait,
    global queue/cancel or execution change.
    After expiry, only read-only reconciliation/exact already-staged candidate recovery
    is allowed unless a separately persisted one-shot output-only grant permits GET/import.
    That grant never changes the accepted dispatch deadline or permits another POST.
    ``revalidate_contract=True`` is trusted caller opt-in for an existing blocked
    contract with known OR unknown prompt ID only. One unique exact successful
    completed history and a strict safe declared descriptor commit the ID/first
    evidence before import, never from queue/absence/failure alone.
    """
    # The shared load requires finalized sheet pins even for direct worker calls, before HTTP.
    reader = store.read_portrait_submission if _portrait_only else store.read_anchor_unit_submission
    record = reader(db, job_id, expected_unit_digest=expected_unit_digest,
                                           expected_wire_digest=expected_wire_digest)
    TypeAdapter(store.Revision).validate_python(expected_revision, strict=True)
    if record.revision != expected_revision:
        raise PortraitWorkerError('revision_conflict')
    if type(revalidate_contract) is not bool:
        raise PortraitWorkerError('invalid_revalidation_authorization')
    if revalidate_contract and not (record.state == 'blocked' and record.reason == 'contract_error'):
        raise PortraitWorkerError('revalidation_requires_owned_contract_block')
    if record.state in ('completed', 'failed'):
        return record
    if record.reason == 'contract_error' and not revalidate_contract:
        return _block(db, record, 'contract_error')
    if record.state == 'authorized' and _now(clock_ms) >= record.deadline_ms:
        return store.fail_anchor_unit_submission(db, record.preview.job_id, **_args(record), reason='deadline_exceeded')
    job = render_job_store.read_anchor_unit_job(db, job_id, expected_unit_digest=expected_unit_digest)
    image = json.loads(job.prepared_input.image_pin_json)
    output = image['expected_output']
    try:
        settings = resolve_comfyui_connection(record.preview.connection)
        connection = BatchConnectionPinV1(connection=settings.connection, endpoint_digest='sha256:' + settings.endpoint_digest)
        if (connection.connection != record.preview.connection or connection.endpoint_digest != record.preview.endpoint_digest
                or sha256_digest(canonical_json(connection)) != record.preview.connection_digest or settings.verify is False):
            raise PortraitWorkerError('connection_pin_mismatch')
        headers = {'Accept': 'application/json', 'Accept-Encoding': 'identity'}
        if settings.auth_token:
            headers['Authorization'] = 'Bearer ' + settings.auth_token
        client = httpx.AsyncClient(base_url=settings.endpoint, headers=headers, verify=settings.verify,
            trust_env=False, follow_redirects=False, timeout=httpx.Timeout(15.0, connect=5.0), transport=transport)
    except (ComfyUIConfigError, ValueError, TypeError, OSError, ssl.SSLError):
        raise PortraitWorkerError('client_configuration') from None
    try:
        async with asyncio.timeout(TICK_TIMEOUT), client:
            if record.state == 'authorized':
                return await _submit(db, client, record, clock_ms)
            return await _reconcile(db, client, record, clock_ms, output, image['schemas'], revalidate_contract=revalidate_contract)
    except PortraitWorkerError:
        raise
    except (ValueError, *HTTP_ERRORS):
        raise PortraitWorkerError('client_or_durable_integrity') from None


async def tick_portrait_job(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                           expected_wire_digest: str, expected_revision: int,
                           revalidate_contract: bool = False,
                           transport: httpx.AsyncBaseTransport | None = None,
                           clock_ms: Callable[[], int] = _clock) -> store.PortraitSubmissionV1:
    """Accepted 6A portrait-only entrypoint; reuse the exact bounded tick implementation."""
    return await tick_anchor_unit_job(db, job_id, expected_unit_digest=expected_unit_digest,
        expected_wire_digest=expected_wire_digest, expected_revision=expected_revision,
        revalidate_contract=revalidate_contract, transport=transport, clock_ms=clock_ms, _portrait_only=True)
