"""Read-only same-generation sheet parents; not upload/native/creative authorization.

Caller holds the application's data-root lock and supplies an already-authorized
project. No external asset, Character library, latest-source fallback or current
registry/provider is consulted. Prepared parent names remain metadata, not receipts.
"""

from dataclasses import dataclass
import json
import sqlite3
from typing import Literal

from pydantic import TypeAdapter

from backend import batch_generation as generation, batch_store, portrait_candidate_store as candidates
from backend import portrait_submission_store as submissions, render_job_store as jobs, wardrobe_store
from backend.batch_generation import BatchConnectionPinV1, BatchStoryApprovalV1, ParentBindings
from backend.domain import ArtifactRef, canonical_json, sha256_digest
from backend.story_graph import validate_wardrobe_success
from backend.story_store import _destination, _uuid
from backend.wardrobe import AnchorKey, ExactDigest


@dataclass(frozen=True, repr=False)
class VerifiedAnchorParentV1:
    role: Literal['portrait', 'background']
    candidate_id: str
    job_id: str
    attempt_id: str
    unit_key: str
    unit_input_digest: str
    batch_id: str
    batch_input_digest: str
    activation_id: str
    source_plan_ref: ArtifactRef
    story_ref: ArtifactRef
    connection: BatchConnectionPinV1
    submission_wire_digest: str
    input_name: str
    digest: str
    original_bytes: bytes


def _source_authority(db: sqlite3.Connection, batch: batch_store.BatchInputPinV1, project_id: str) -> None:
    handoff = batch.prepared_input
    expected = handoff.source_plan_ref
    story = handoff.story_approval.story_ref
    if (expected.project_id != project_id or story.project_id != project_id
            or db.execute('SELECT project_id FROM executions WHERE execution_id=?',
                          (expected.execution_id,)).fetchone() != (project_id,)):
        raise ValueError('Batch source/project ownership mismatch')
    if db.execute("SELECT 1 FROM execution_controls WHERE execution_id=? AND kind='cancel'",
                  (expected.execution_id,)).fetchone():
        raise ValueError('Cancelled source cannot resolve parents for new effects')
    if db.execute('SELECT outcome,source_id,subject_artifact_id FROM execution_outcomes WHERE execution_id=?',
                  (expected.execution_id,)).fetchone() != ('completed', expected.operation_id, expected.artifact_id):
        raise ValueError('Batch source lacks its exact completed Wardrobe receipt')
    # Existing exact readers own source bodies and approval validation. Also reject
    # redirected artifact ancestors before they open either source under this DB root.
    for ref in (expected, story):
        batch_store._directories(_destination(db, ref.project_id, ref.artifact_id, ref.digest))
    ref, plan = wardrobe_store.read_wardrobe_plan(db, expected.execution_id, artifact_id=expected.artifact_id)
    if ref != expected or plan.batch_prompt != handoff.ordered_units or plan.narrative_ref != story:
        raise ValueError('Batch source plan/Story no longer matches its exact frozen pins')
    operation = wardrobe_store.read_wardrobe_operation(db, ref.operation_id)
    pins = operation['pins']
    if validate_wardrobe_success(db, expected.execution_id, pins.approval_request_id) != expected:
        raise ValueError('Batch source lacks exact applied Story authority')
    if db.execute("SELECT status FROM execution_work WHERE execution_id=? AND kind='resume' AND source_id=?",
                  (expected.execution_id, pins.approval_request_id)).fetchone() != ('completed',):
        raise ValueError('Batch source applied approval work is not completed')
    approval = BatchStoryApprovalV1(story_ref=pins.story_ref, approval_request_id=pins.approval_request_id,
        approval_request_digest=pins.approval_request_digest, decision_id=pins.decision_id,
        applied_activation_id=pins.activation_id, story_binding_revision=pins.story_binding_revision)
    if (handoff.story_approval != approval or handoff.wardrobe_input_digest !=
            sha256_digest(canonical_json(operation['config'].wardrobe_input))):
        raise ValueError('Batch source authority/request differs from frozen handoff')


def resolve_sheet_parents(db: sqlite3.Connection, batch_id: str, sheet_unit_key: str, *,
        expected_batch_digest: str, expected_project_id: str, parent_bindings: ParentBindings | list[dict],
        expected_child_digest: str | None = None, expected_child_job_id: str | None = None
        ) -> tuple[VerifiedAnchorParentV1, VerifiedAnchorParentV1]:
    """Resolve EXACT ordered imported/completed portrait + background ORIGINALS offline.

    Works before sheet preparation. Optional child selectors revalidate an existing
    immutable prepared unit/job; neither metadata nor returned bytes enable native
    sheet dispatch. Each original is capped at 16 MiB by the candidate owner.
    """
    batch_store._committed(db)
    _uuid(expected_project_id)
    TypeAdapter(ExactDigest).validate_python(expected_batch_digest, strict=True)
    TypeAdapter(AnchorKey).validate_python(sheet_unit_key, strict=True)
    if expected_child_job_id is not None and expected_child_digest is None:
        raise ValueError('Child job revalidation requires its exact prepared input digest')
    batch = batch_store.read_batch_input(db, batch_id)
    if batch.input_digest != expected_batch_digest:
        raise ValueError('Batch digest selector mismatch')
    _source_authority(db, batch, expected_project_id)
    _, sheet, mapping = generation._unit(batch.prepared_input, sheet_unit_key)
    if ((sheet.use_case, sheet.workflow, mapping.kind) != ('hero-sheet', 'img2img', 'sheet')
            or [ref.role for ref in sheet.references] != ['portrait', 'background']):
        raise ValueError('Parent resolution supports only the declared two-reference sheet')
    parents, _ = generation._parents(sheet, parent_bindings)
    if expected_child_digest is not None:
        TypeAdapter(ExactDigest).validate_python(expected_child_digest, strict=True)
        child = batch_store.read_prepared_batch_unit(db, batch_id, sheet_unit_key, parent_bindings=parents)
        if child.input_digest != expected_child_digest:
            raise ValueError('Child prepared input selector mismatch')
        if expected_child_job_id is not None:
            job = jobs.read_anchor_unit_job(db, expected_child_job_id, expected_unit_digest=expected_child_digest)
            intent = json.loads(job.intent_body)
            if (job.kind != 'sheet' or job.prepared_input != child.prepared_input
                    or (intent['project_id'], intent['batch_id'], intent['unit_key']) !=
                       (expected_project_id, batch_id, sheet_unit_key)):
                raise ValueError('Child job does not own this exact sheet input')
    resolved = []
    handoff = batch.prepared_input
    for parent, reference in zip(parents, sheet.references, strict=True):
        TypeAdapter(ExactDigest).validate_python(parent.source_id, strict=True)
        row = candidates._row(db, parent.source_id)  # No lookup by unit key or "latest".
        if row is None or row[8] != 'published':
            raise LookupError('Exact parent candidate is not published')
        job_row = jobs._row(db, row[1])
        if job_row is None or (job_row[1], job_row[2], job_row[3], job_row[4]) != (
                batch_id, reference.source.unit_key, row[3], row[2]):
            raise ValueError('Parent job/attempt/unit does not belong to the exact batch generation')
        # Reject foreign generation/project before opening its original media.
        job = jobs.read_anchor_unit_job(db, row[1], expected_unit_digest=row[3])
        intent = json.loads(job.intent_body)
        if (job.kind != reference.role or (intent['project_id'], intent['batch_id'], intent['batch_input_digest']) !=
                (expected_project_id, batch_id, expected_batch_digest)):
            raise ValueError('Parent role/project/batch input ownership mismatch')
        submitted = submissions._row(db, job.job_id)
        if submitted is None or submitted[6] != 'completed':
            raise ValueError('Parent import alone is not completed provider success')
        completion = submissions.read_anchor_unit_submission(db, job.job_id,
            expected_unit_digest=row[3], expected_wire_digest=submitted[2])
        preview = completion.preview
        if (completion.state != 'completed' or completion.candidate_id != parent.source_id
                or preview.source_plan_ref != handoff.source_plan_ref
                or (preview.connection, preview.endpoint_digest, preview.connection_digest) !=
                   (handoff.connection.connection, handoff.connection.endpoint_digest,
                    sha256_digest(canonical_json(handoff.connection)))):
            raise ValueError('Parent completed submission/candidate/source/connection ownership mismatch')
        candidate, original = candidates.read_anchor_unit_candidate_original(db, parent.source_id, expected_unit_digest=row[3])
        if (candidate.digest != parent.digest or candidate.endpoint_digest != handoff.connection.endpoint_digest
                or (candidate.job_id, candidate.attempt_id, candidate.unit_input_digest, candidate.intent_digest) !=
                   (job.job_id, job.attempt_id, row[3], job.intent_digest)):
            raise ValueError('Exact imported parent digest/lineage mismatch')
        resolved.append(VerifiedAnchorParentV1(reference.role, candidate.candidate_id, job.job_id, job.attempt_id,
            parent.unit_key, candidate.unit_input_digest, batch_id, expected_batch_digest, handoff.activation_id,
            handoff.source_plan_ref, handoff.story_approval.story_ref, handoff.connection, preview.wire_digest,
            parent.input_name, candidate.digest, original))
    return resolved[0], resolved[1]
