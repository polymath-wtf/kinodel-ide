"""Exact offline public image reads. Caller owns the root lock and DB thread.

No latest/Retry resolution, lifecycle maintenance, provider access or repair. A
candidate import is not completion. Private provenance never enters these DTOs.
"""

import sqlite3
from typing import Annotated, Literal
from urllib.parse import quote, urlencode

from pydantic import Field, model_validator

from backend import batch_store, image_group_results as results, image_group_store as groups
from backend import portrait_candidate_store as candidates, portrait_submission_store as submissions
from backend.domain import CanonicalUUID, DomainModel, MAX_LIST_ITEMS, sha256_digest
from backend.story_store import _root, _uuid
from backend.wardrobe import AnchorKey, AnchorUseCase, ExactDigest


class ImageMediaRefV1(DomainModel):
    execution_id: CanonicalUUID
    group_id: ExactDigest
    unit_key: AnchorKey
    job_id: ExactDigest
    attempt_id: ExactDigest
    unit_input_digest: ExactDigest
    origin_execution_id: CanonicalUUID
    candidate_id: ExactDigest
    candidate_digest: ExactDigest
    candidate_metadata_digest: ExactDigest


class ImageOriginalV1(DomainModel):
    media_ref: ImageMediaRefV1
    mime_type: Literal['image/png']
    byte_length: Annotated[int, Field(strict=True, ge=1, le=candidates.MAX_PNG_BYTES)]
    width: Annotated[int, Field(strict=True, ge=1, le=candidates.MAX_DIMENSION)]
    height: Annotated[int, Field(strict=True, ge=1, le=candidates.MAX_DIMENSION)]
    url: Annotated[str, Field(strict=True, max_length=2048, pattern=r'^/api/executions/')]


class ImageUnitStateV1(DomainModel):
    unit_key: AnchorKey
    use_case: AnchorUseCase
    available: bool
    reason: Literal['unstarted', 'not_completed', 'unit_unavailable_or_invalid'] | None
    original: ImageOriginalV1 | None

    @model_validator(mode='after')
    def valid_availability(self):
        if self.available != (self.original is not None) or self.available != (self.reason is None):
            raise ValueError('Image availability requires its verified original')
        return self


class ImageResultStateV1(DomainModel):
    result_id: ExactDigest
    digest: ExactDigest
    status: Literal['complete', 'failed'] | None
    issue: Literal['manifest_unavailable_or_invalid'] | None

    @model_validator(mode='after')
    def valid_status(self):
        if (self.status is None) != (self.issue is not None):
            raise ValueError('Image result status requires full manifest validation')
        return self


class ImageProjectionV1(DomainModel):
    schema_version: Literal['1']
    execution_id: CanonicalUUID
    project_id: CanonicalUUID
    group_id: ExactDigest
    total_units: Annotated[int, Field(strict=True, ge=1, le=MAX_LIST_ITEMS)]
    available_units: Annotated[int, Field(strict=True, ge=0, le=MAX_LIST_ITEMS)]
    units: Annotated[list[ImageUnitStateV1], Field(min_length=1, max_length=MAX_LIST_ITEMS)]
    result: ImageResultStateV1 | None


def _group(db, execution_id):
    batch_store._committed(db)
    _uuid(execution_id)
    if groups._row(db, execution_id) is None:
        raise LookupError('Exact image consumer not found')
    return groups.read_image_group(db, execution_id)


def _completed_output(db, group, unit_key, context, outputs):
    """Reuse validated immutable outputs only within this synchronous operation."""
    if unit_key in outputs:
        return outputs[unit_key]
    _, planned = results._declared(group, unit_key)
    if context is None:
        raise ValueError('Image binding context is unavailable or invalid')
    row = results._unit_row(db, group.receipt.group_id, unit_key)
    if row is None:
        raise LookupError('Image unit has no selected attempt')
    binding = results.ImageUnitAttemptV1(*row)
    job = results._validate_binding(db, group, binding, context)
    submission = submissions._row(db, binding.job_id, binding.attempt_id)
    if submission is None:
        return None
    if submission[6] != 'completed':
        results._facts(db, binding)  # Validate noncompleted facts before showing that reason.
        return None
    # The SQL label is just a branch hint; _output independently validates the
    # completed submission and exact candidate. Do not validate _facts twice.
    output = results._output(db, binding, job)
    parents = []
    for reference in planned.references:
        parent = _completed_output(db, group, reference.source.unit_key, context, outputs)
        if parent is None:
            raise ValueError('Image unit parent is not completed')
        parents.append(parent)
    results._validate_parents(planned, job, parents)
    outputs[unit_key] = output
    return output


def _completed_original(db, group, unit_key, context, outputs):
    output = _completed_output(db, group, unit_key, context, outputs)
    if output is None:
        return None
    # Never cache media bytes: the owner verifies the actual bytes returned by
    # this read, even when completion/parent facts were already checked above.
    candidate, original = candidates.read_anchor_unit_candidate_original(db, output.candidate_id,
        expected_unit_digest=output.unit_input_digest)
    if (candidate.job_id, candidate.attempt_id, candidate.digest, sha256_digest(candidate.metadata_body)) != (
            output.job_id, output.attempt_id, output.candidate_digest, output.candidate_metadata_digest):
        raise ValueError('Original differs from the completed exact group candidate')
    return output, candidate, original


def _media_ref(group, output):
    return ImageMediaRefV1(execution_id=group.receipt.execution_id, group_id=group.receipt.group_id,
        **{key: getattr(output, key) for key in ImageMediaRefV1.model_fields
           if key not in ('execution_id', 'group_id')})


def _original_url(ref):
    path = (f'/api/executions/{ref.execution_id}/images/'
            f'candidates/{quote(ref.candidate_id, safe="")}/original')
    selectors = ref.model_dump(exclude={'execution_id', 'candidate_id'})
    return path + '?' + urlencode(selectors)


def read_image_original(db: sqlite3.Connection, media_ref: ImageMediaRefV1) -> bytes:
    """Only the selected consumer's completed attempt; never a generic candidate URL."""
    ref = ImageMediaRefV1.model_validate(media_ref)
    group = _group(db, ref.execution_id)
    if ref.group_id != group.receipt.group_id:
        raise ValueError('Original group selector mismatch')
    selected = _completed_original(db, group, ref.unit_key, results._binding_context(db, group), {})
    if selected is None:
        raise LookupError('Exact image unit is not completed')
    output, _, original = selected
    if ref != _media_ref(group, output):
        raise ValueError('Original exact candidate/attempt/digest selector mismatch')
    return original


def _result_projection(db, group, root):
    row = results._result_row(db, group.receipt.group_id)
    if row is None or row[6] == 'reserved':
        return None
    # Preserve ONLY an exact canonical published envelope if full validation fails
    # (e.g. original loss). This is not a substitute manifest validator: status
    # stays null until the existing complete-set reader succeeds, never inferred
    # from N originals, a SQL label, or consumer outcome.
    body = results.ImageGroupResultBodyV1.model_validate_json(batch_store._body(row[4]))
    receipt = group.receipt
    if (row[6] != 'published' or row[:6] != results._result_values(body)
            or (body.result_id, body.project_id, body.execution_id, body.group_id, body.wait_id,
                body.stage_id, body.activation_id, body.request_digest, body.batch_id, body.input_digest,
                body.input_batch_id, body.input_batch_digest) != (
                batch_store._identity('kinodel.image-group-result.v1', receipt.group_id, receipt.wait_id),
                root.prepared_input.source_plan_ref.project_id, receipt.execution_id, receipt.group_id,
                receipt.wait_id, receipt.stage_id, receipt.activation_id, receipt.request_digest,
                receipt.batch_id, receipt.input_digest, root.batch_id, root.input_digest)):
        raise ValueError('Published image manifest envelope mismatch')
    if batch_store._read_file(_root(db) / row[5].removeprefix('kinodel://')) != row[4].encode('utf-8'):
        raise ValueError('Published image manifest bytes mismatch')
    envelope = results.ImageGroupResultV1(body.result_id, row[2], row[5], body.status, body)
    results._check_wake(db, group, envelope)
    try:
        validated = results.read_image_group_result(db, receipt.execution_id)
    except (ValueError, TypeError, LookupError, KeyError, OSError, RecursionError):
        return ImageResultStateV1(result_id=body.result_id, digest=row[2], status=None,
                                  issue='manifest_unavailable_or_invalid')
    return ImageResultStateV1(result_id=validated.result_id, digest=validated.digest,
                              status=validated.status, issue=None)


def image_projection(db: sqlite3.Connection, execution_id: str) -> ImageProjectionV1:
    """Ordered full declaration, including unavailable/unstarted partial outputs."""
    group = _group(db, execution_id)
    try:
        context = results._binding_context(db, group)
    except (ValueError, TypeError, LookupError, KeyError, OSError, RecursionError):
        # A broken predecessor original must not hide the declaration/manifest
        # identity or cause the same expensive failed context read for every unit.
        context = None
    root = context[0] if context is not None else results.read_image_input_batch(db, execution_id)
    outputs = {}
    units = []
    for planned in group.batch.prepared_input.ordered_units:
        original = None
        reason = 'unstarted'
        if results._unit_row(db, group.receipt.group_id, planned.unit_key) is not None:
            try:
                selected = _completed_original(db, group, planned.unit_key, context, outputs)
                reason = 'not_completed'
                if selected is not None:
                    output, candidate, _ = selected
                    ref = _media_ref(group, output)
                    original = ImageOriginalV1(media_ref=ref, mime_type=candidate.mime_type,
                        width=candidate.width, height=candidate.height, byte_length=candidate.byte_length,
                        url=_original_url(ref))
                    reason = None
            except (ValueError, TypeError, LookupError, KeyError, OSError, RecursionError):
                reason = 'unit_unavailable_or_invalid'
        units.append(ImageUnitStateV1(unit_key=planned.unit_key, use_case=planned.use_case,
                                     available=original is not None, reason=reason, original=original))
    return ImageProjectionV1(schema_version='1', execution_id=execution_id,
        project_id=root.prepared_input.source_plan_ref.project_id, group_id=group.receipt.group_id,
        total_units=len(units), available_units=sum(unit.available for unit in units), units=units,
        result=_result_projection(db, group, root))
