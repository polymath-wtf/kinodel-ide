"""Private durable authorization/facts for initial portrait and background anchors.

Caller owns the data-root OS lock; caller transactions are refused. No HTTP, worker,
retry allocator or graph lifecycle lives here. Only a successful *new* dispatch claim
permits its caller to send once, after commit. A read/replay of dispatching (including
process death before HTTP) is potentially sent and NEVER permits another POST.
Evidence is a restricted assertion supplied by a trusted future native adapter, not
a parser or proof obtained by this module. client_id/correlation are not idempotency.
Sheet entrypoints require exact finalized verified-parent/receipt/graph pins. The
worker additionally rechecks both remote originals before the first prompt claim.
"""

import json
import sqlite3
from typing import Annotated, Any, Literal

from pydantic import Field, TypeAdapter, model_serializer, model_validator

from backend import batch_store, portrait_candidate_store, render_job_store
from backend.batch_store import _committed, _transaction
from backend.domain import ArtifactRef, DomainModel, MAX_JSON_BYTES, Text, canonical_json, sha256_digest
from backend.wardrobe import ExactDigest


DEFAULT_JOB_TIMEOUT_MS = 15 * 60 * 1000
MAX_JOB_TIMEOUT_MS = 60 * 60 * 1000
MAX_OUTPUT_RECOVERY_MS = 5 * 60 * 1000
MAX_SUBMISSION_DIAGNOSTICS = 32
Timestamp = Annotated[int, Field(strict=True, ge=0, le=253402300799999)]
Revision = Annotated[int, Field(strict=True, ge=0, le=2**63 - 2)]
PromptId = Annotated[str, Field(strict=True, min_length=1, max_length=128, pattern=r'^[A-Za-z0-9_-]+$')]
Reason = Literal['acceptance_unknown', 'contract_error', 'deadline_exceeded', 'provider_failed',
                 'output_invalid', 'history_unavailable']


class PortraitSubmissionPreviewV1(DomainModel):
    schema_version: Literal['1']
    job_id: ExactDigest
    attempt_id: ExactDigest
    unit_input_digest: ExactDigest
    unit_input_uri: Text
    intent_digest: ExactDigest
    graph_digest: ExactDigest
    source_plan_ref: ArtifactRef
    connection: Literal['local', 'server']
    connection_digest: ExactDigest
    endpoint_digest: ExactDigest
    # Opaque canonical native JSON preserves frozen graph floats exactly.
    wire_body_json: Annotated[str, Field(strict=True, min_length=1, max_length=MAX_JSON_BYTES)]
    wire_digest: ExactDigest

    @property
    def wire_body(self) -> bytes:
        return self.wire_body_json.encode('utf-8')


class AnchorUnitSubmissionPreviewV1(PortraitSubmissionPreviewV1):
    schema_id: Literal['comfyui_anchor_unit_submission_preview']
    kind: Literal['background', 'sheet']


class SheetSubmissionPreviewV1(AnchorUnitSubmissionPreviewV1):
    kind: Literal['sheet']
    reference_attempt_id: ExactDigest
    reference_intent_digest: ExactDigest
    final_reference_digest: ExactDigest
    reference_receipt_digests: Annotated[list[ExactDigest], Field(min_length=2, max_length=2)]


class PortraitSubmissionEvidenceV1(DomainModel):
    """Adapter-verified exact correlation/endpoint evidence; no raw response or credentials."""

    kind: Literal['prompt_response', 'queue', 'history']
    digest: ExactDigest
    prompt_id: PromptId
    wire_digest: ExactDigest
    endpoint_digest: ExactDigest


class SubmissionDiagnosticV1(DomainModel):
    """Sanitized foreign native-record fact, never acceptance or output evidence."""

    kind: Literal['broken_job']
    source: Literal['queue', 'history']
    prompt_id: PromptId | None = None
    reason: Literal['native_tuple', 'native_prompt_id', 'history_shape', 'history_identity', 'history_status']
    digest: ExactDigest


class PortraitSubmissionV1(DomainModel):
    schema_version: Literal['1']
    preview: PortraitSubmissionPreviewV1
    revision: Revision
    state: Literal['authorized', 'dispatching', 'accepted', 'blocked', 'failed', 'completed']
    accepted_at_ms: Timestamp
    deadline_ms: Timestamp
    dispatched_at_ms: Timestamp | None = None
    prompt_id: PromptId | None = None
    acceptance_evidence: PortraitSubmissionEvidenceV1 | None = None
    evidence: PortraitSubmissionEvidenceV1 | None = None
    reason: Reason | None = None
    candidate_id: ExactDigest | None = None
    output_recovery_authorized_at_ms: Timestamp | None = None
    output_recovery_deadline_ms: Timestamp | None = None
    diagnostics: Annotated[list[SubmissionDiagnosticV1], Field(max_length=MAX_SUBMISSION_DIAGNOSTICS)] = Field(default_factory=list)

    @model_serializer(mode='wrap')
    def original_canonical_body_without_inactive_recovery(self, handler):
        body = handler(self)
        if self.output_recovery_authorized_at_ms is None and self.output_recovery_deadline_ms is None:
            # Omit ONLY the new inactive pair: existing DB18 canonical rows remain exact.
            body.pop('output_recovery_authorized_at_ms', None)
            body.pop('output_recovery_deadline_ms', None)
        if not self.diagnostics:
            body.pop('diagnostics', None)  # Old 6A canonical bodies/digests remain byte-identical.
        return body

    @model_validator(mode='after')
    def valid_facts(self):
        if len({canonical_json(item) for item in self.diagnostics}) != len(self.diagnostics):
            raise ValueError('Submission diagnostics must be deduplicated')
        if self.diagnostics and (self.dispatched_at_ms is None or self.state in ('authorized', 'dispatching')):
            raise ValueError('Native diagnostics require independently reconciled provider facts')
        if not 0 < self.deadline_ms - self.accepted_at_ms <= MAX_JOB_TIMEOUT_MS:
            raise ValueError('Invalid fixed portrait deadline')
        start, end = self.output_recovery_authorized_at_ms, self.output_recovery_deadline_ms
        if (start is None) != (end is None):
            raise ValueError('Output-only recovery requires its complete fixed time pair')
        if start is not None and end is not None and (
                not 0 < end - start <= MAX_OUTPUT_RECOVERY_MS or start < self.deadline_ms
                or self.prompt_id is None or self.dispatched_at_ms is None
                or self.state in ('authorized', 'dispatching')):
            raise ValueError('Output-only recovery must be bounded and owned; it cannot renew dispatch')
        if self.dispatched_at_ms is not None and not self.accepted_at_ms <= self.dispatched_at_ms < self.deadline_ms:
            raise ValueError('Dispatch marker outside authorized budget')
        if (self.prompt_id is None) != (self.acceptance_evidence is None):
            raise ValueError('Acceptance must retain prompt ID and first evidence together')
        for proof in (self.acceptance_evidence, self.evidence):
            if proof is not None and (proof.prompt_id, proof.wire_digest, proof.endpoint_digest) != (
                    self.prompt_id, self.preview.wire_digest, self.preview.endpoint_digest):
                raise ValueError('Evidence conflicts with exact prompt/wire/endpoint')
        if (self.state == 'completed') != (self.candidate_id is not None):
            raise ValueError('Only completed facts bind a candidate')
        if self.state == 'authorized':
            if (self.revision != 0 or self.dispatched_at_ms is not None or self.prompt_id is not None
                    or self.reason is not None or self.evidence is not None):
                raise ValueError('Authorization is not dispatch or acceptance')
        elif self.state == 'dispatching':
            if (self.revision != 1 or self.dispatched_at_ms is None or self.prompt_id is not None
                    or self.reason is not None or self.evidence is not None):
                raise ValueError('Invalid potentially-sent marker')
        elif self.state == 'failed' and self.dispatched_at_ms is None:
            if self.revision != 1 or self.reason != 'deadline_exceeded' or self.prompt_id is not None:
                raise ValueError('Only budget expiry can fail before dispatch')
        else:
            if self.revision < 2 or self.dispatched_at_ms is None:
                raise ValueError('Provider facts require a committed dispatch marker')
            if self.state in ('accepted', 'completed', 'failed') and self.prompt_id is None:
                raise ValueError('Unknown sent acceptance must remain blocked, not accepted or terminal')
        if self.state in ('blocked', 'failed') and self.reason is None:
            raise ValueError('Blocked/failed facts require a restricted reason')
        if self.state == 'completed' and (self.evidence is None or self.evidence.kind != 'history'):
            raise ValueError('Completion requires adapter-verified successful declared history')
        return self


class AnchorUnitSubmissionV1(PortraitSubmissionV1):
    schema_id: Literal['comfyui_anchor_unit_submission']
    preview: AnchorUnitSubmissionPreviewV1


class SheetSubmissionV1(AnchorUnitSubmissionV1):
    preview: SheetSubmissionPreviewV1


def _row(db, job_id):
    return db.execute('SELECT attempt_id,job_id,wire_digest,submission_digest,submission_body,revision,state,'
                      'prompt_id,candidate_id FROM portrait_submissions WHERE job_id=?', (job_id,)).fetchone()


def _preview(db, job_id, expected_unit_digest, portrait_only=False):
    reader = render_job_store.read_portrait_job if portrait_only else render_job_store.read_anchor_unit_job
    job = reader(db, job_id, expected_unit_digest=expected_unit_digest)
    references = _require_native_ready(db, job)
    intent = json.loads(job.intent_body)
    batch = batch_store.read_batch_input(db, intent['batch_id'])
    image = json.loads(job.prepared_input.image_pin_json)  # Job reader has replay-validated every frozen pin.
    graph, graph_digest = image['graph'], 'sha256:' + image['graph_sha256']
    if references is not None:
        final = references.final
        assert final is not None
        graph, graph_digest = json.loads(final.graph_json), final.graph_digest
    correlation: dict[str, Any] = dict(job_id=job.job_id, attempt_id=job.attempt_id,
        input_digest=expected_unit_digest, intent_digest=job.intent_digest, graph_digest=graph_digest)
    if job.kind == 'portrait':
        namespace, client_id = 'kinodel_portrait_v1', 'kinodel-' + job.attempt_id[7:]
        model, fields = PortraitSubmissionPreviewV1, {}
    else:
        namespace, client_id = 'kinodel_anchor_unit_v1', 'kinodel-anchor-unit-' + job.attempt_id[7:]
        correlation['kind'] = job.kind
        model, fields = AnchorUnitSubmissionPreviewV1, dict(schema_id='comfyui_anchor_unit_submission_preview', kind=job.kind)
        if references is not None:
            receipt_digests = []
            for item in references.references:
                assert item.receipt is not None
                receipt_digests.append(item.receipt.digest)
            reference_fields = dict(reference_attempt_id=references.intent.attempt_id,
                reference_intent_digest=references.intent_digest, final_reference_digest=sha256_digest(canonical_json(references)),
                reference_receipt_digests=receipt_digests)
            model = SheetSubmissionPreviewV1
            fields = {**fields, **reference_fields}
            correlation.update(reference_fields)
    wire = dict(prompt=graph, client_id=client_id, extra_data={namespace: correlation})
    wire_json = json.dumps(wire, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    connection = batch.prepared_input.connection
    preview = model(**fields, schema_version='1', job_id=job.job_id, attempt_id=job.attempt_id,
        unit_input_digest=expected_unit_digest, unit_input_uri=intent['unit_input_uri'], intent_digest=job.intent_digest,
        graph_digest=graph_digest, source_plan_ref=batch.prepared_input.source_plan_ref,
        connection=connection.connection, connection_digest=sha256_digest(canonical_json(connection)),
        endpoint_digest=connection.endpoint_digest, wire_body_json=wire_json,
        wire_digest=sha256_digest(wire_json.encode('utf-8')))
    # Recheck the exact binding under each write transaction, without I/O inside SQL.
    bindings = (job_id, intent['batch_id'], intent['unit_key'])
    return preview, bindings, _binding_rows(db, *bindings)


def _require_native_ready(db, job: render_job_store.AnchorUnitJobV1):
    if job.kind != 'sheet':
        return None
    # Local import avoids resolver -> parent submission -> reference store cycle.
    from backend import anchor_reference_store as references
    row = references._row(db, job.job_id)
    if row is None:
        raise ValueError('sheet native submission requires exact finalized reference pins')
    stored = references._stored(row)  # SQL selector is validated, never caller-provided readiness.
    if stored.state != 'finalized' or stored.final is None:
        raise ValueError('sheet native submission requires exact finalized reference pins')
    intent = json.loads(job.intent_body)
    return references.read_anchor_reference_transfer(db, job.job_id, expected_project_id=intent['project_id'],
        expected_unit_digest=intent['unit_input_digest'], expected_intent_digest=stored.intent_digest)


def _binding_rows(db, job_id, batch_id, unit_key):
    rows = portrait_candidate_store._binding_rows(db, job_id, batch_id, unit_key)
    if rows and rows[0] is not None and json.loads(rows[0][6]).get('kind') == 'sheet':
        from backend import anchor_reference_store as references
        return (*rows, references._row(db, job_id))
    return rows


def _values(record):
    body = canonical_json(record)
    return (record.preview.attempt_id, record.preview.job_id, record.preview.wire_digest,
            sha256_digest(body), body.decode('utf-8'), record.revision, record.state,
            record.prompt_id, record.candidate_id)


def _candidate(db, record):
    candidate = portrait_candidate_store.read_anchor_unit_candidate(db, record.candidate_id,
        expected_unit_digest=record.preview.unit_input_digest)
    if (candidate.job_id, candidate.attempt_id, candidate.intent_digest, candidate.endpoint_digest) != (
            record.preview.job_id, record.preview.attempt_id, record.preview.intent_digest, record.preview.endpoint_digest):
        raise ValueError('Completed candidate conflicts with exact submission lineage')
    return portrait_candidate_store._row(db, candidate.candidate_id)


def _restore(db, row, preview):
    body = row[4]
    if type(body) is not str or not 0 < len(body.encode('utf-8')) <= MAX_JSON_BYTES:
        raise ValueError('Invalid stored portrait submission body')
    model = (SheetSubmissionV1 if isinstance(preview, SheetSubmissionPreviewV1) else
             AnchorUnitSubmissionV1 if isinstance(preview, AnchorUnitSubmissionPreviewV1) else PortraitSubmissionV1)
    record = model.model_validate_json(body)
    if record.preview != preview or row != _values(record):
        raise ValueError('Portrait submission SQL/wire/facts mismatch; refusing repair')
    if record.candidate_id is not None:
        _candidate(db, record)
    return record


def preview_anchor_unit_submission(db: sqlite3.Connection, job_id: str, *,
                                expected_unit_digest: str, _portrait_only: bool = False) -> PortraitSubmissionPreviewV1:
    """Offline deterministic preview. Preparation/preview/5A intent never authorize a send."""
    preview, _, _ = _preview(db, job_id, expected_unit_digest, _portrait_only)
    row = _row(db, job_id)
    if row is not None:
        _restore(db, row, preview)
    return preview


def _load(db, job_id, expected_unit_digest, expected_wire_digest, portrait_only=False):
    TypeAdapter(ExactDigest).validate_python(expected_wire_digest, strict=True)
    preview, bindings, pins = _preview(db, job_id, expected_unit_digest, portrait_only)
    if preview.wire_digest != expected_wire_digest:
        raise ValueError('Native wire selector conflicts with exact frozen portrait')
    row = _row(db, job_id)
    if row is None:
        raise LookupError('Portrait submission is not explicitly authorized')
    return _restore(db, row, preview), row, bindings, pins


def read_anchor_unit_submission(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                             expected_wire_digest: str, _portrait_only: bool = False) -> PortraitSubmissionV1:
    """Read restricted durable facts. No returned state grants permission to POST."""
    return _load(db, job_id, expected_unit_digest, expected_wire_digest, _portrait_only)[0]


def _assert_pins(db, bindings, pins):
    if _binding_rows(db, *bindings) != pins:
        raise ValueError('Portrait binding changed before submission commit')


def authorize_anchor_unit_submission(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                                  expected_wire_digest: str, accepted_at_ms: int,
                                  job_timeout_ms: int = DEFAULT_JOB_TIMEOUT_MS,
                                  _portrait_only: bool = False) -> PortraitSubmissionV1:
    """Trusted caller's explicit accepted intent; replay preserves original budget and all facts."""
    _committed(db)
    TypeAdapter(ExactDigest).validate_python(expected_wire_digest, strict=True)
    TypeAdapter(Timestamp).validate_python(accepted_at_ms, strict=True)
    if type(job_timeout_ms) is not int or not 0 < job_timeout_ms <= MAX_JOB_TIMEOUT_MS:
        raise ValueError('Portrait budget must be between 1 ms and one hour')
    preview, bindings, pins = _preview(db, job_id, expected_unit_digest, _portrait_only)
    if preview.wire_digest != expected_wire_digest:
        raise ValueError('Authorization conflicts with the previewed native wire')
    model, fields = (PortraitSubmissionV1, {}) if type(preview) is PortraitSubmissionPreviewV1 else (
        AnchorUnitSubmissionV1, dict(schema_id='comfyui_anchor_unit_submission'))
    if isinstance(preview, SheetSubmissionPreviewV1):
        model = SheetSubmissionV1
    authorized = model(**fields, schema_version='1', preview=preview, state='authorized', revision=0,
                                     accepted_at_ms=accepted_at_ms, deadline_ms=accepted_at_ms + job_timeout_ms)
    row = _row(db, job_id)
    if row is not None:
        record = _restore(db, row, preview)
        if (record.accepted_at_ms, record.deadline_ms) != (authorized.accepted_at_ms, authorized.deadline_ms):
            raise ValueError('Accepted time/deadline conflict; refusing renewed authorization')
        return record
    with _transaction(db):
        _assert_pins(db, bindings, pins)
        db.execute('INSERT INTO portrait_submissions VALUES (?,?,?,?,?,?,?,?,?)', _values(authorized))
    return authorized


def _change(db, loaded, expected_revision, allowed, *, replay=True, **updates):
    record, row, bindings, pins = loaded
    TypeAdapter(Revision).validate_python(expected_revision, strict=True)
    desired = type(record).model_validate({**record.model_dump(), **updates, 'revision': expected_revision + 1})
    # Only an exact replay of this one mutation is harmless. Dispatch claims never replay.
    if replay and record.revision == expected_revision + 1 and record == desired:
        return record
    if record.revision != expected_revision or record.state not in allowed:
        raise ValueError('Portrait submission revision/state conflict; refusing regression or duplicate claim')
    candidate_row = _candidate(db, desired) if desired.candidate_id is not None else None
    with _transaction(db):
        _assert_pins(db, bindings, pins)
        if _row(db, record.preview.job_id) != row:
            raise ValueError('Portrait submission changed before CAS commit')
        if candidate_row is not None and portrait_candidate_store._row(db, desired.candidate_id) != candidate_row:
            raise ValueError('Completed candidate changed before CAS commit')
        result = db.execute('UPDATE portrait_submissions SET attempt_id=?,job_id=?,wire_digest=?,submission_digest=?,'
            'submission_body=?,revision=?,state=?,prompt_id=?,candidate_id=? WHERE job_id=? AND revision=? '
            'AND submission_digest=?', (*_values(desired), record.preview.job_id, expected_revision, row[3]))
        if result.rowcount != 1:
            raise ValueError('Portrait submission CAS conflict')
    return desired


def claim_anchor_unit_dispatch(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                            expected_wire_digest: str, expected_revision: int, now_ms: int,
                            _portrait_only: bool = False) -> PortraitSubmissionV1:
    """Commit potentially-sent marker BEFORE HTTP. Duplicate claims always fail, even exact replay."""
    loaded = _load(db, job_id, expected_unit_digest, expected_wire_digest, _portrait_only)
    TypeAdapter(Timestamp).validate_python(now_ms, strict=True)
    return _change(db, loaded, expected_revision, ('authorized',), replay=False,
                   state='dispatching', dispatched_at_ms=now_ms)


def record_submission_diagnostics(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                                  expected_wire_digest: str, expected_revision: int,
                                  diagnostics: list[SubmissionDiagnosticV1 | dict]) -> PortraitSubmissionV1:
    """Append bounded first-seen facts using the same short transaction/CAS as lifecycle writes.

    The trusted adapter has proved these malformed records unrelated. No raw payload,
    acceptance, lifecycle transition, time renewal or dispatch permission is recorded.
    """
    loaded = _load(db, job_id, expected_unit_digest, expected_wire_digest)
    record = loaded[0]
    TypeAdapter(Revision).validate_python(expected_revision, strict=True)
    incoming = TypeAdapter(Annotated[list[SubmissionDiagnosticV1], Field(strict=True, max_length=4096)]).validate_python(diagnostics)
    if record.state not in ('accepted', 'blocked'):
        raise ValueError('Diagnostics require reconciled accepted or blocked facts')
    merged = list(record.diagnostics)
    for item in incoming:
        if item not in merged and len(merged) < MAX_SUBMISSION_DIAGNOSTICS:
            merged.append(item)
    if merged == record.diagnostics and record.revision == expected_revision:
        return record
    return _change(db, loaded, expected_revision, ('accepted', 'blocked'), diagnostics=merged)


def authorize_anchor_unit_output_recovery(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                                      expected_wire_digest: str, expected_revision: int, now_ms: int,
                                      timeout_ms: int = MAX_OUTPUT_RECOVERY_MS,
                                      _portrait_only: bool = False) -> PortraitSubmissionV1:
    """One explicit GET/import-only window for an already accepted prompt after expiry.

    Never dispatch permission, a charged attempt or a renewed original budget. Exact
    grant replay preserves its original time pair, even after it expires. A changed
    time/budget or stale revision conflicts; no automatic refresh or second grant.
    The worker still proves successful declared history before using this allowance.
    """
    loaded = _load(db, job_id, expected_unit_digest, expected_wire_digest, _portrait_only)
    record = loaded[0]
    TypeAdapter(Revision).validate_python(expected_revision, strict=True)
    TypeAdapter(Timestamp).validate_python(now_ms, strict=True)
    if type(timeout_ms) is not int or not 0 < timeout_ms <= MAX_OUTPUT_RECOVERY_MS:
        raise ValueError('Output-only recovery is bounded to at most five minutes')
    if (record.prompt_id is None or now_ms < record.deadline_ms
            or not (record.state == 'accepted' or (record.state == 'blocked'
                and record.reason in ('deadline_exceeded', 'contract_error')))):
        raise ValueError('Output-only recovery requires an expired same-owned accepted/eligible blocked prompt')
    end = now_ms + timeout_ms
    if record.output_recovery_authorized_at_ms is not None:
        if (record.output_recovery_authorized_at_ms, record.output_recovery_deadline_ms) != (now_ms, end):
            raise ValueError('Output-only recovery grant is immutable; refusing renewal')
        if record.revision not in (expected_revision, expected_revision + 1):
            raise ValueError('Output-only recovery replay revision conflict')
        return record
    return _change(db, loaded, expected_revision, ('accepted', 'blocked'),
        output_recovery_authorized_at_ms=now_ms, output_recovery_deadline_ms=end)


def record_anchor_unit_acceptance(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                               expected_wire_digest: str, expected_revision: int, prompt_id: str,
                               evidence: PortraitSubmissionEvidenceV1 | dict,
                               revalidate_contract: bool = False, _portrait_only: bool = False) -> PortraitSubmissionV1:
    """Persist response ID FIRST, independent of node_errors/output checks in the future adapter.

    A blocked request recovers only via adapter-verified exact queue/history evidence.
    The first acceptance evidence/ID survive later blocking, reconciliation and failure.
    Explicit contract revalidation trusts the adapter's successful declared-history
    and descriptor checks; history/CAS only, preserving any known owned ID or committing
    the first proven ID/evidence together. Caller retains the original block in
    restricted audit before requesting this correction, not a new render.
    """
    loaded = _load(db, job_id, expected_unit_digest, expected_wire_digest, _portrait_only)
    record = loaded[0]
    proof = PortraitSubmissionEvidenceV1.model_validate(evidence)
    if type(revalidate_contract) is not bool:
        raise ValueError('Contract revalidation requires explicit boolean authorization')
    reason = record.reason
    if revalidate_contract:
        original_block = record.state == 'blocked' and record.reason == 'contract_error'
        replay = (record.state == 'accepted' and record.reason is None and record.revision == expected_revision + 1
                  and record.evidence == proof)
        if (not (original_block or replay) or (record.prompt_id is not None and prompt_id != record.prompt_id)
                or proof.kind != 'history'):
            raise ValueError('Contract revalidation requires an owned contract block and exact successful history evidence')
        reason = None
    if record.state == 'blocked' and proof.kind not in ('queue', 'history'):
        raise ValueError('Blocked acceptance requires exact queue/history evidence')
    if record.prompt_id is not None and prompt_id != record.prompt_id:
        raise ValueError('Provider prompt ID is immutable once accepted')
    return _change(db, loaded, expected_revision, ('dispatching', 'blocked'), state='accepted', prompt_id=prompt_id,
                   acceptance_evidence=record.acceptance_evidence or proof, evidence=proof, reason=reason)


def block_anchor_unit_submission(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                              expected_wire_digest: str, expected_revision: int, reason: Reason,
                              _portrait_only: bool = False) -> PortraitSubmissionV1:
    """Ambiguous acceptance/history remains nonterminal and cannot dispatch again."""
    loaded = _load(db, job_id, expected_unit_digest, expected_wire_digest, _portrait_only)
    TypeAdapter(Reason).validate_python(reason, strict=True)
    if reason == 'provider_failed' or (reason == 'acceptance_unknown' and loaded[0].prompt_id is not None):
        raise ValueError('Block reason conflicts with known provider facts')
    return _change(db, loaded, expected_revision, ('dispatching', 'accepted', 'blocked'), state='blocked', reason=reason)


def fail_anchor_unit_submission(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                             expected_wire_digest: str, expected_revision: int, reason: Reason,
                             evidence: PortraitSubmissionEvidenceV1 | dict | None = None,
                             _portrait_only: bool = False) -> PortraitSubmissionV1:
    """Terminal failure, never a retry allocator; retain any accepted ID/evidence.

    After dispatch, an unknown prompt ID must remain blocked even on deadline expiry.
    No local transport/contract failure proves provider nonacceptance.
    """
    loaded = _load(db, job_id, expected_unit_digest, expected_wire_digest, _portrait_only)
    TypeAdapter(Reason).validate_python(reason, strict=True)
    if reason in ('acceptance_unknown', 'history_unavailable'):
        raise ValueError('Unknown provider outcome is blocked, not terminal failure')
    proof = PortraitSubmissionEvidenceV1.model_validate(evidence) if evidence is not None else loaded[0].evidence
    if reason == 'provider_failed' and (proof is None or proof.kind != 'history'):
        raise ValueError('Known provider failure requires exact history evidence')
    return _change(db, loaded, expected_revision, ('authorized', 'dispatching', 'accepted', 'blocked'),
                   state='failed', reason=reason, evidence=proof)


def complete_anchor_unit_submission(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                                 expected_wire_digest: str, expected_revision: int, candidate_id: str,
                                 evidence: PortraitSubmissionEvidenceV1 | dict,
                                 _portrait_only: bool = False) -> PortraitSubmissionV1:
    """Bind an already verified 5B candidate after adapter-verified successful declared history.

    Candidate identity/media are never changed here; this is neither creative approval
    nor a selected asset. Evidence parsing and provider-success checks belong to HTTP.
    """
    loaded = _load(db, job_id, expected_unit_digest, expected_wire_digest, _portrait_only)
    proof = PortraitSubmissionEvidenceV1.model_validate(evidence)
    return _change(db, loaded, expected_revision, ('accepted', 'blocked'), state='completed',
                    candidate_id=candidate_id, evidence=proof)


# Accepted 6A entrypoints stay portrait-only. Shared implementations above do not
# broaden old callers; empty diagnostics preserve the original canonical body.
def preview_portrait_submission(db: sqlite3.Connection, job_id: str, *,
                                expected_unit_digest: str) -> PortraitSubmissionPreviewV1:
    return preview_anchor_unit_submission(db, job_id, expected_unit_digest=expected_unit_digest, _portrait_only=True)


def read_portrait_submission(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                             expected_wire_digest: str) -> PortraitSubmissionV1:
    return read_anchor_unit_submission(db, job_id, expected_unit_digest=expected_unit_digest,
                                      expected_wire_digest=expected_wire_digest, _portrait_only=True)


def authorize_portrait_submission(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                                  expected_wire_digest: str, accepted_at_ms: int,
                                  job_timeout_ms: int = DEFAULT_JOB_TIMEOUT_MS) -> PortraitSubmissionV1:
    return authorize_anchor_unit_submission(db, job_id, expected_unit_digest=expected_unit_digest,
        expected_wire_digest=expected_wire_digest, accepted_at_ms=accepted_at_ms, job_timeout_ms=job_timeout_ms, _portrait_only=True)


def claim_portrait_dispatch(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                            expected_wire_digest: str, expected_revision: int, now_ms: int) -> PortraitSubmissionV1:
    return claim_anchor_unit_dispatch(db, job_id, expected_unit_digest=expected_unit_digest,
        expected_wire_digest=expected_wire_digest, expected_revision=expected_revision, now_ms=now_ms, _portrait_only=True)


def authorize_portrait_output_recovery(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                                      expected_wire_digest: str, expected_revision: int, now_ms: int,
                                      timeout_ms: int = MAX_OUTPUT_RECOVERY_MS) -> PortraitSubmissionV1:
    return authorize_anchor_unit_output_recovery(db, job_id, expected_unit_digest=expected_unit_digest,
        expected_wire_digest=expected_wire_digest, expected_revision=expected_revision, now_ms=now_ms,
        timeout_ms=timeout_ms, _portrait_only=True)


def record_portrait_acceptance(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                               expected_wire_digest: str, expected_revision: int, prompt_id: str,
                               evidence: PortraitSubmissionEvidenceV1 | dict,
                               revalidate_contract: bool = False) -> PortraitSubmissionV1:
    return record_anchor_unit_acceptance(db, job_id, expected_unit_digest=expected_unit_digest,
        expected_wire_digest=expected_wire_digest, expected_revision=expected_revision, prompt_id=prompt_id,
        evidence=evidence, revalidate_contract=revalidate_contract, _portrait_only=True)


def block_portrait_submission(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                              expected_wire_digest: str, expected_revision: int, reason: Reason) -> PortraitSubmissionV1:
    return block_anchor_unit_submission(db, job_id, expected_unit_digest=expected_unit_digest,
        expected_wire_digest=expected_wire_digest, expected_revision=expected_revision, reason=reason, _portrait_only=True)


def fail_portrait_submission(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                             expected_wire_digest: str, expected_revision: int, reason: Reason,
                             evidence: PortraitSubmissionEvidenceV1 | dict | None = None) -> PortraitSubmissionV1:
    return fail_anchor_unit_submission(db, job_id, expected_unit_digest=expected_unit_digest,
        expected_wire_digest=expected_wire_digest, expected_revision=expected_revision, reason=reason,
        evidence=evidence, _portrait_only=True)


def complete_portrait_submission(db: sqlite3.Connection, job_id: str, *, expected_unit_digest: str,
                                 expected_wire_digest: str, expected_revision: int, candidate_id: str,
                                 evidence: PortraitSubmissionEvidenceV1 | dict) -> PortraitSubmissionV1:
    return complete_anchor_unit_submission(db, job_id, expected_unit_digest=expected_unit_digest,
        expected_wire_digest=expected_wire_digest, expected_revision=expected_revision, candidate_id=candidate_id,
        evidence=evidence, _portrait_only=True)
