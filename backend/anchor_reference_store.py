"""Durable ordered reference STORAGE, not HTTP or native sheet authorization.

Trusted local root-lock owner supplies an authorized project. Only a fresh claim
committed before I/O grants one upload POST. Reopened dispatching/blocked-sent facts
never prove unsent. Receipts and full remote GET verification are adapter assertions;
no provider request, original bytes, arbitrary graph or approval lives in this table.
"""

import copy
from dataclasses import dataclass
import json
import re
import sqlite3
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, field_validator, model_validator

from backend import anchor_parent_resolver as resolver, batch_store, comfyui_workflows as registry
from backend import portrait_candidate_store as candidates, portrait_submission_store as submissions, render_job_store as jobs
from backend.batch_generation import BatchConnectionPinV1
from backend.batch_store import _committed, _transaction
from backend.domain import ArtifactRef, CanonicalUUID, DomainModel, MAX_JSON_BYTES, canonical_json, sha256_digest
from backend.wardrobe import AnchorKey, ExactDigest


Role = Literal['portrait', 'background']
Reason = Literal['readiness_unavailable', 'acceptance_unknown', 'receipt_invalid', 'remote_invalid']
Revision = submissions.Revision
PositiveRevision = Annotated[int, Field(strict=True, ge=1, le=2**63 - 2)]
ByteLength = Annotated[int, Field(strict=True, ge=1, le=candidates.MAX_PNG_BYTES)]
Name = Annotated[str, Field(strict=True, min_length=1, max_length=255)]
Folder = Annotated[str, Field(strict=True, max_length=255)]


def _folder(value: str) -> str:
    TypeAdapter(Folder).validate_python(value, strict=True)
    normalized = value.replace('\\', '/')
    if normalized:
        for part in normalized.split('/'):
            candidates._component(part)
        registry._input_name(normalized + '/placeholder.png')
    return normalized


def _name(value: str) -> str:
    TypeAdapter(Name).validate_python(value, strict=True)
    candidates._component(value)
    registry._input_name(value)
    return value


class ReferenceParentPinV1(DomainModel):
    candidate_id: ExactDigest
    job_id: ExactDigest
    attempt_id: ExactDigest
    unit_key: AnchorKey
    unit_input_digest: ExactDigest
    batch_id: ExactDigest
    batch_input_digest: ExactDigest
    activation_id: ExactDigest
    source_plan_ref: ArtifactRef
    story_ref: ArtifactRef
    connection: BatchConnectionPinV1
    submission_wire_digest: ExactDigest
    digest: ExactDigest
    byte_length: ByteLength


class ReferenceUploadIntentV1(DomainModel):
    role: Role
    node_id: Literal['470', '496']
    input_field: Literal['image']
    parent: ReferenceParentPinV1
    name: Name
    subfolder: Folder
    type: Literal['input']
    overwrite: Literal[False]

    @field_validator('name')
    @classmethod
    def safe_name(cls, value):
        return _name(value)

    @field_validator('subfolder')
    @classmethod
    def normalized_folder(cls, value):
        if _folder(value) != value:
            raise ValueError('Intent folder must already be normalized')
        return value


class AnchorReferenceIntentV1(DomainModel):
    schema_id: Literal['comfyui_anchor_reference_intent']
    schema_version: Literal['1']
    project_id: CanonicalUUID
    job_id: ExactDigest
    attempt_id: ExactDigest
    unit_input_digest: ExactDigest
    job_intent_digest: ExactDigest
    connection: BatchConnectionPinV1
    references: Annotated[list[ReferenceUploadIntentV1], Field(min_length=2, max_length=2)]

    @model_validator(mode='after')
    def ordered_slots(self):
        if [(item.role, item.node_id) for item in self.references] != [('portrait', '470'), ('background', '496')]:
            raise ValueError('Reference intent must retain the two exact ordered slots')
        if len({(item.subfolder, item.name) for item in self.references}) != 2:
            raise ValueError('Reference upload destinations must be distinct')
        return self


@dataclass(frozen=True, repr=False)
class AnchorReferencePreviewV1:
    intent: AnchorReferenceIntentV1
    intent_body: bytes
    intent_digest: str


class ReferenceReceiptV1(DomainModel):
    name: Name
    subfolder: Folder
    native_subfolder: Folder
    type: Literal['input']

    @field_validator('name')
    @classmethod
    def safe_name(cls, value):
        return _name(value)

    @model_validator(mode='after')
    def exact_native_folder(self):
        if _folder(self.native_subfolder) != self.subfolder:
            raise ValueError('Native/normalized receipt folder mismatch')
        return self

    @property
    def digest(self) -> str:
        return sha256_digest(canonical_json(self))


class RemoteReferenceVerificationV1(DomainModel):
    receipt_digest: ExactDigest
    remote_digest: ExactDigest
    source_digest: ExactDigest
    byte_length: ByteLength


class ReferenceTransferV1(DomainModel):
    role: Role
    state: Literal['ready', 'dispatching', 'received', 'verified', 'blocked_unsent', 'blocked_sent']
    dispatch_revision: PositiveRevision | None = None
    receipt: ReferenceReceiptV1 | None = None
    receipt_revision: PositiveRevision | None = None
    verification: RemoteReferenceVerificationV1 | None = None
    verification_revision: PositiveRevision | None = None
    reason: Reason | None = None

    @model_validator(mode='after')
    def coherent_facts(self):
        if ((self.receipt is None) != (self.receipt_revision is None)
                or (self.verification is None) != (self.verification_revision is None)):
            raise ValueError('Receipt/verification facts require their committed revision')
        unsent = self.state in ('ready', 'blocked_unsent')
        if unsent != (self.dispatch_revision is None):
            raise ValueError('Predispatch readiness must not become potentially-sent')
        if unsent and (self.receipt is not None or self.verification is not None):
            raise ValueError('Unsent reference cannot contain provider facts')
        if self.state == 'dispatching' and (self.receipt is not None or self.verification is not None):
            raise ValueError('Dispatching has no actual receipt yet')
        if self.state in ('received', 'verified') and self.receipt is None:
            raise ValueError('Received/verified reference requires an actual receipt')
        if (self.state == 'verified') != (self.verification is not None):
            raise ValueError('Only verified references bind a full GET verification')
        blocked = self.state in ('blocked_unsent', 'blocked_sent')
        if blocked != (self.reason is not None):
            raise ValueError('Reference block requires its explicit reason')
        if self.state == 'blocked_unsent' and self.reason != 'readiness_unavailable':
            raise ValueError('Unsent block is readiness only')
        if self.state == 'blocked_sent' and (self.reason == 'readiness_unavailable'
                or (self.reason == 'acceptance_unknown' and self.receipt is not None)
                or (self.reason == 'remote_invalid' and self.receipt is None)):
            raise ValueError('Sent block conflicts with receipt facts')
        if self.receipt_revision is not None and (self.dispatch_revision is None or self.receipt_revision <= self.dispatch_revision):
            raise ValueError('Receipt must follow its dispatch claim')
        if self.verification_revision is not None and (self.receipt_revision is None or self.verification_revision <= self.receipt_revision):
            raise ValueError('Remote verification must follow its actual receipt')
        return self


class FinalReferenceBindingV1(DomainModel):
    role: Role
    node_id: Literal['470', '496']
    input_field: Literal['image']
    candidate_id: ExactDigest
    receipt_digest: ExactDigest
    image_path: Annotated[str, Field(strict=True, min_length=1, max_length=512)]
    digest: ExactDigest
    byte_length: ByteLength


class AnchorFinalGraphV1(DomainModel):
    graph_json: Annotated[str, Field(strict=True, min_length=1, max_length=MAX_JSON_BYTES)]
    graph_digest: ExactDigest
    seed: Annotated[int, Field(strict=True, ge=0)]
    receipt_bindings: Annotated[list[FinalReferenceBindingV1], Field(min_length=2, max_length=2)]


def _state(references, final):
    if final is not None:
        return 'finalized'
    if any(item.state.startswith('blocked_') for item in references):
        return 'blocked'
    if all(item.state == 'verified' for item in references):
        return 'verified'
    return 'authorized' if all(item.state == 'ready' for item in references) else 'active'


class AnchorReferenceTransferV1(DomainModel):
    schema_id: Literal['comfyui_anchor_reference_transfer']
    schema_version: Literal['1']
    intent: AnchorReferenceIntentV1
    intent_digest: ExactDigest
    revision: Revision
    state: Literal['authorized', 'active', 'blocked', 'verified', 'finalized']
    references: Annotated[list[ReferenceTransferV1], Field(min_length=2, max_length=2)]
    final: AnchorFinalGraphV1 | None = None

    @model_validator(mode='after')
    def exact_facts(self):
        if self.intent_digest != sha256_digest(canonical_json(self.intent)):
            raise ValueError('Reference intent digest mismatch')
        if [item.role for item in self.references] != ['portrait', 'background'] or self.state != _state(self.references, self.final):
            raise ValueError('Reference order/aggregate state mismatch')
        if self.references[1].dispatch_revision is not None and self.references[0].state != 'verified':
            raise ValueError('Background dispatch must follow portrait remote verification')
        if self.references[1].dispatch_revision is not None and (
                self.references[0].verification_revision is None
                or self.references[1].dispatch_revision <= self.references[0].verification_revision):
            raise ValueError('Background dispatch revision predates portrait remote verification')
        if self.final is not None and any(item.state != 'verified' for item in self.references):
            raise ValueError('Final graph requires both remote originals verified')
        for intent, item in zip(self.intent.references, self.references, strict=True):
            for revision in (item.dispatch_revision, item.receipt_revision, item.verification_revision):
                if revision is not None and revision > self.revision:
                    raise ValueError('Reference fact revision exceeds record revision')
            if item.receipt is not None:
                _validate_owned_receipt(intent, item.receipt)
            if item.verification is not None:
                proof = item.verification
                if (item.receipt is None or proof.receipt_digest != item.receipt.digest
                        or (proof.source_digest, proof.remote_digest, proof.byte_length) !=
                           (intent.parent.digest, intent.parent.digest, intent.parent.byte_length)):
                    raise ValueError('Remote verification is not this exact receipt/source original')
        return self


def _validate_owned_receipt(intent, receipt):
    allowed = receipt.name == intent.name or re.fullmatch(re.escape(intent.name[:-4]) + r' \([1-9][0-9]*\)\.png', receipt.name)
    if not allowed or receipt.subfolder != intent.subfolder:
        raise ValueError('Receipt name/folder conflicts with the assigned owned namespace')
    registry._input_name((receipt.subfolder + '/' if receipt.subfolder else '') + receipt.name)


def _row(db, job_id):
    return db.execute('SELECT attempt_id,job_id,unit_input_digest,intent_digest,record_digest,record_body,revision,state '
                      'FROM anchor_reference_transfers WHERE job_id=?', (job_id,)).fetchone()


def _values(record):
    body = canonical_json(record)
    return (record.intent.attempt_id, record.intent.job_id, record.intent.unit_input_digest, record.intent_digest,
            sha256_digest(body), body.decode(), record.revision, record.state)


def _stored(row):
    if type(row[5]) is not str or not 0 < len(row[5].encode()) <= MAX_JSON_BYTES:
        raise ValueError('Invalid bounded reference metadata')
    record = AnchorReferenceTransferV1.model_validate_json(row[5])
    if row != _values(record):
        raise ValueError('Reference SQL/canonical metadata mismatch; refusing repair')
    return record


def _snapshots(db, job, intent):
    first = intent.references[0].parent
    rows = [candidates._binding_rows(db, job.job_id, first.batch_id, job.prepared_input.unit_key)]
    for item in intent.references:
        parent = item.parent
        rows.append((candidates._binding_rows(db, parent.job_id, parent.batch_id, parent.unit_key),
                     candidates._row(db, parent.candidate_id), submissions._row(db, parent.job_id)))
    execution = first.source_plan_ref.execution_id
    for table in ('executions', 'execution_controls', 'execution_outcomes', 'execution_bindings',
                  'review_requests', 'execution_work', 'wardrobe_operations'):
        rows.append(db.execute(f'SELECT rowid,* FROM {table} WHERE execution_id=? ORDER BY rowid', (execution,)).fetchall())
    return rows


def _context(db, job_id, project_id, unit_digest, subfolder):
    _committed(db)
    TypeAdapter(CanonicalUUID).validate_python(project_id, strict=True)
    folder = _folder(subfolder)
    job = jobs.read_anchor_unit_job(db, job_id, expected_unit_digest=unit_digest)
    if job.kind != 'sheet':
        raise ValueError('Reference storage supports only the exact prepared sheet initial attempt')
    technical = json.loads(job.intent_body)
    batch = batch_store.read_batch_input(db, technical['batch_id'])
    parents = resolver.resolve_sheet_parents(db, batch.batch_id, job.prepared_input.unit_key,
        expected_batch_digest=batch.input_digest, expected_project_id=project_id,
        parent_bindings=job.prepared_input.parent_bindings, expected_child_digest=unit_digest, expected_child_job_id=job_id)
    image = registry.replay_prepared(job.prepared_input.image_pin_json)
    if [slot['load_id'] for slot in image['registry_snapshot']['mapping']['slots'][:2]] != ['470', '496']:
        raise ValueError('Unsupported frozen sheet loader slots')
    items = []
    for parent, node in zip(parents, ('470', '496'), strict=True):
        pin = ReferenceParentPinV1(**{name: getattr(parent, name) for name in ReferenceParentPinV1.model_fields if name != 'byte_length'},
                                  byte_length=len(parent.original_bytes))
        name = f'kinodel-{job_id[7:]}-{parent.role}-{parent.digest[7:]}.png'
        registry._input_name((folder + '/' if folder else '') + name)
        items.append(ReferenceUploadIntentV1(role=parent.role, node_id=node, input_field='image', parent=pin,
                     name=name, subfolder=folder, type='input', overwrite=False))
    intent = AnchorReferenceIntentV1(schema_id='comfyui_anchor_reference_intent', schema_version='1', project_id=project_id,
        job_id=job.job_id, attempt_id=job.attempt_id, unit_input_digest=unit_digest, job_intent_digest=job.intent_digest,
        connection=batch.prepared_input.connection, references=items)
    return intent, job, image, _snapshots(db, job, intent)


def _ownership(db, record):
    def claims(value):
        result = set()
        for intent, item in zip(value.intent.references, value.references, strict=True):
            result.add((value.intent.connection.endpoint_digest, intent.subfolder, intent.name))
            if item.receipt is not None:
                result.add((value.intent.connection.endpoint_digest, item.receipt.subfolder, item.receipt.name))
        return result
    owned = claims(record)
    for row in db.execute('SELECT attempt_id,job_id,unit_input_digest,intent_digest,record_digest,record_body,revision,state '
                          'FROM anchor_reference_transfers WHERE job_id<>?', (record.intent.job_id,)).fetchall():
        if owned & claims(_stored(row)):
            raise ValueError('Reference destination ownership conflicts with another transfer')


def _final(intent, references, image):
    if any(item.state != 'verified' for item in references):
        raise ValueError('Both ordered remote originals must be verified before final graph')
    graph = copy.deepcopy(image['graph'])
    bindings = []
    for upload, facts in zip(intent.references, references, strict=True):
        receipt = facts.receipt
        path = (receipt.subfolder + '/' if receipt.subfolder else '') + receipt.name
        graph[upload.node_id]['inputs']['image'] = path
        bindings.append(FinalReferenceBindingV1(role=upload.role, node_id=upload.node_id, input_field='image',
            candidate_id=upload.parent.candidate_id, receipt_digest=receipt.digest, image_path=path,
            digest=upload.parent.digest, byte_length=upload.parent.byte_length))
    registry.validate_graph(graph, image['schemas'], workflow=image['registry_snapshot'], planned_loaders=['470', '496'],
                            model_inventory=image['model_inventory'])
    encoded = json.dumps(graph, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return AnchorFinalGraphV1(graph_json=encoded, graph_digest=sha256_digest(encoded.encode()),
                              seed=image['settings']['seed'], receipt_bindings=bindings)


def _load(db, job_id, expected_project_id, expected_unit_digest, expected_intent_digest):
    _committed(db)
    TypeAdapter(ExactDigest).validate_python(expected_intent_digest, strict=True)
    row = _row(db, job_id)
    if row is None:
        raise LookupError('Reference transfer is not explicitly authorized')
    record = _stored(row)
    if record.intent_digest != expected_intent_digest:
        raise ValueError('Reference intent selector conflicts with original authorization')
    context = _context(db, job_id, expected_project_id, expected_unit_digest, record.intent.references[0].subfolder)
    if context[0] != record.intent:
        raise ValueError('Reference intent/input/parent ownership mismatch; refusing replacement')
    if record.final is not None and record.final != _final(record.intent, record.references, context[2]):
        raise ValueError('Stored final graph/seed/receipt bindings mismatch; refusing repair')
    _ownership(db, record)
    return record, row, context


def preview_anchor_reference_intent(db: sqlite3.Connection, job_id: str, *, expected_project_id: str,
        expected_unit_digest: str, subfolder: str = '') -> AnchorReferencePreviewV1:
    context = _context(db, job_id, expected_project_id, expected_unit_digest, subfolder)
    intent = context[0]
    body = canonical_json(intent)
    digest = sha256_digest(body)
    if _row(db, job_id) is not None:
        _load(db, job_id, expected_project_id, expected_unit_digest, digest)
    return AnchorReferencePreviewV1(intent, body, digest)


def authorize_anchor_reference_transfer(db: sqlite3.Connection, job_id: str, *, expected_project_id: str,
        expected_unit_digest: str, expected_intent_digest: str, subfolder: str = '') -> AnchorReferenceTransferV1:
    context = _context(db, job_id, expected_project_id, expected_unit_digest, subfolder)
    intent = context[0]
    if sha256_digest(canonical_json(intent)) != TypeAdapter(ExactDigest).validate_python(expected_intent_digest, strict=True):
        raise ValueError('Authorization conflicts with previewed reference intent')
    if _row(db, job_id) is not None:
        return _load(db, job_id, expected_project_id, expected_unit_digest, expected_intent_digest)[0]
    record = AnchorReferenceTransferV1(schema_id='comfyui_anchor_reference_transfer', schema_version='1',
        intent=intent, intent_digest=expected_intent_digest, revision=0, state='authorized',
        references=[ReferenceTransferV1(role=role, state='ready') for role in ('portrait', 'background')])
    with _transaction(db):
        if _snapshots(db, context[1], intent) != context[3]:
            raise ValueError('Reference source/parent pins changed before authorization')
        _ownership(db, record)
        db.execute('INSERT INTO anchor_reference_transfers VALUES (?,?,?,?,?,?,?,?)', _values(record))
    return record


def read_anchor_reference_transfer(db: sqlite3.Connection, job_id: str, *, expected_project_id: str,
        expected_unit_digest: str, expected_intent_digest: str) -> AnchorReferenceTransferV1:
    """Offline exact readiness read; rerun source/rights/original checks, never heal."""
    return _load(db, job_id, expected_project_id, expected_unit_digest, expected_intent_digest)[0]


def _role(role):
    TypeAdapter(Role).validate_python(role, strict=True)
    return 0 if role == 'portrait' else 1


def _change(db, loaded, expected_revision, *, index=None, updates: dict | None = None, final=None):
    record, row, context = loaded
    TypeAdapter(Revision).validate_python(expected_revision, strict=True)
    if record.revision != expected_revision or record.final is not None:
        raise ValueError('Reference revision/state conflict')
    references = list(record.references)
    if index is not None:
        assert updates is not None
        references[index] = ReferenceTransferV1.model_validate({**references[index].model_dump(), **updates})
    desired = AnchorReferenceTransferV1.model_validate({**record.model_dump(), 'references': references,
        'final': final, 'revision': expected_revision + 1, 'state': _state(references, final)})
    with _transaction(db):
        if _row(db, record.intent.job_id) != row or _snapshots(db, context[1], record.intent) != context[3]:
            raise ValueError('Reference facts/source/parent pins changed before CAS')
        _ownership(db, desired)
        result = db.execute('UPDATE anchor_reference_transfers SET attempt_id=?,job_id=?,unit_input_digest=?,intent_digest=?, '
            'record_digest=?,record_body=?,revision=?,state=? WHERE job_id=? AND revision=? AND record_digest=?',
            (*_values(desired), record.intent.job_id, expected_revision, row[4]))
        if result.rowcount != 1:
            raise ValueError('Reference transfer CAS conflict')
    return desired


def claim_anchor_reference_upload(db: sqlite3.Connection, job_id: str, *, role: Role, expected_project_id: str,
        expected_unit_digest: str, expected_intent_digest: str, expected_revision: int) -> AnchorReferenceTransferV1:
    """Only this fresh successful CAS permits ONE POST. Never replay a claim."""
    loaded = _load(db, job_id, expected_project_id, expected_unit_digest, expected_intent_digest)
    index = _role(role)
    if loaded[0].references[index].state != 'ready' or (index == 1 and loaded[0].references[0].state != 'verified'):
        raise ValueError('Reference upload is not unsent/ready in verified role order')
    return _change(db, loaded, expected_revision, index=index,
                   updates=dict(state='dispatching', dispatch_revision=expected_revision + 1))


def record_anchor_reference_receipt(db: sqlite3.Connection, job_id: str, *, role: Role, receipt: dict,
        expected_project_id: str, expected_unit_digest: str, expected_intent_digest: str,
        expected_revision: int) -> AnchorReferenceTransferV1:
    """Persist the actual adapter-observed receipt before any remote GET; never guess."""
    loaded = _load(db, job_id, expected_project_id, expected_unit_digest, expected_intent_digest)
    record = loaded[0]
    index = _role(role)
    if type(receipt) is not dict or set(receipt) != {'name', 'subfolder', 'type'}:
        raise ValueError('Receipt must be the exact native name/subfolder/type object')
    actual = ReferenceReceiptV1(name=receipt['name'], subfolder=_folder(receipt['subfolder']),
        native_subfolder=receipt['subfolder'], type=receipt['type'])
    _validate_owned_receipt(record.intent.references[index], actual)
    current = record.references[index]
    TypeAdapter(Revision).validate_python(expected_revision, strict=True)
    if current.receipt is not None:
        if current.receipt == actual and expected_revision in (record.revision, current.receipt_revision - 1):
            return record  # Replay of this exact fact only; never a POST permission.
        raise ValueError('Receipt/name/revision conflicts with the original saved fact')
    if current.state not in ('dispatching', 'blocked_sent'):
        raise ValueError('Actual receipt requires its committed potentially-sent claim')
    return _change(db, loaded, expected_revision, index=index,
        updates=dict(state='received', receipt=actual, receipt_revision=expected_revision + 1, reason=None))


def verify_anchor_reference_remote(db: sqlite3.Connection, job_id: str, *, role: Role, expected_project_id: str,
        expected_unit_digest: str, expected_intent_digest: str, expected_revision: int,
        expected_receipt_digest: str, remote_digest: str, source_digest: str, byte_length: int) -> AnchorReferenceTransferV1:
    """Trusted adapter assertion AFTER full bounded GET; no verified=True shortcut."""
    loaded = _load(db, job_id, expected_project_id, expected_unit_digest, expected_intent_digest)
    record = loaded[0]
    index = _role(role)
    current, parent = record.references[index], record.intent.references[index].parent
    proof = RemoteReferenceVerificationV1(receipt_digest=expected_receipt_digest,
        remote_digest=remote_digest, source_digest=source_digest, byte_length=byte_length)
    TypeAdapter(Revision).validate_python(expected_revision, strict=True)
    if (current.receipt is None or current.receipt.digest != proof.receipt_digest
            or (proof.remote_digest, proof.source_digest, proof.byte_length) != (parent.digest, parent.digest, parent.byte_length)):
        raise ValueError('Full remote GET receipt/digest/length/source proof mismatch')
    if current.verification is not None:
        if current.verification == proof and expected_revision in (record.revision, current.verification_revision - 1):
            return record
        raise ValueError('Remote verification/revision conflicts with original fact')
    if current.state not in ('received', 'blocked_sent'):
        raise ValueError('Remote GET verification requires the original saved receipt')
    return _change(db, loaded, expected_revision, index=index,
        updates=dict(state='verified', verification=proof, verification_revision=expected_revision + 1, reason=None))


def block_anchor_reference(db: sqlite3.Connection, job_id: str, *, role: Role, reason: Reason, expected_project_id: str,
        expected_unit_digest: str, expected_intent_digest: str, expected_revision: int) -> AnchorReferenceTransferV1:
    loaded = _load(db, job_id, expected_project_id, expected_unit_digest, expected_intent_digest)
    index = _role(role)
    current = loaded[0].references[index]
    TypeAdapter(Revision).validate_python(expected_revision, strict=True)
    TypeAdapter(Reason).validate_python(reason, strict=True)
    if current.state == 'verified':
        raise ValueError('Verified reference facts cannot regress or reupload')
    state = 'blocked_unsent' if current.dispatch_revision is None else 'blocked_sent'
    if current.state == state and current.reason == reason and expected_revision == loaded[0].revision:
        return loaded[0]
    return _change(db, loaded, expected_revision, index=index, updates=dict(state=state, reason=reason))


def revalidate_anchor_reference_readiness(db: sqlite3.Connection, job_id: str, *, role: Role, expected_project_id: str,
        expected_unit_digest: str, expected_intent_digest: str, expected_revision: int) -> AnchorReferenceTransferV1:
    """Clear only a NEVER-dispatched readiness block after exact current parent checks."""
    loaded = _load(db, job_id, expected_project_id, expected_unit_digest, expected_intent_digest)
    index = _role(role)
    if loaded[0].references[index].state != 'blocked_unsent':
        raise ValueError('Only a definitely-unsent readiness block can become ready')
    return _change(db, loaded, expected_revision, index=index, updates=dict(state='ready', reason=None))


def finalize_anchor_references(db: sqlite3.Connection, job_id: str, *, expected_project_id: str,
        expected_unit_digest: str, expected_intent_digest: str, expected_revision: int) -> AnchorReferenceTransferV1:
    """Derive/pin only the two actual LoadImage literals, preserving all source floats/seed."""
    loaded = _load(db, job_id, expected_project_id, expected_unit_digest, expected_intent_digest)
    record = loaded[0]
    TypeAdapter(Revision).validate_python(expected_revision, strict=True)
    if record.final is not None:
        if expected_revision in (record.revision, record.revision - 1):
            return record
        raise ValueError('Final graph replay revision conflict')
    return _change(db, loaded, expected_revision, final=_final(record.intent, record.references, loaded[2][2]))
