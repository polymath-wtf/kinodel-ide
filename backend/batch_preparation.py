"""Read-only saved Wardrobe source resolution; no batch activation or media work.

Caller owns the data-root lock. Only committed project JSON/SQL are read, never
the Character library, current agent resources or provider. The returned handoff
is a diagnostic proposal for a later persisted activation, not permission to submit.
"""

import sqlite3
from typing import Annotated, Literal

from pydantic import AfterValidator, Field, model_validator

from backend import batch_generation, wardrobe_store
from backend.batch_generation import (BatchConnectionPinV1, BatchGenerationInputV1, BatchStoryApprovalV1,
                                      BatchWorkflowBindingV1)
from backend.domain import (ArtifactRef, DomainModel, ExactProfilePin, MAX_LIST_ITEMS, MediaSize, _exact_artifact_ref)
from backend.story_graph import validate_wardrobe_success
from backend.story_store import _uuid
from backend.wardrobe import AnchorBatchUnitV2, ExactDigest


class AnchorBatchPreparationRequestV1(DomainModel):
    source_plan_ref: Annotated[ArtifactRef, AfterValidator(_exact_artifact_ref)]
    image_size: MediaSize
    image_profile: ExactProfilePin
    connection: Literal["local", "server"]
    activation_id: ExactDigest


class SavedBatchPreparationV1(DomainModel):
    """Internal full handoff/result; never use as an API response model."""

    schema_version: Literal["1"]
    prepared_input: BatchGenerationInputV1
    input_digest: ExactDigest
    readiness: Literal["preparation_only"]
    can_submit: Literal[False]

    @model_validator(mode="after")
    def exact_digest(self):
        if self.input_digest != batch_generation.batch_input_digest(self.prepared_input):
            raise ValueError("Saved batch preparation digest mismatch")
        return self


class PublicBatchPreparationV1(DomainModel):
    """Semantic diagnostic only; input_digest identifies the FULL private handoff."""

    schema_version: Literal["1"]
    source_plan_ref: ArtifactRef
    story_approval: BatchStoryApprovalV1
    stage_id: Literal["anchor-batch"]
    activation_id: ExactDigest
    input_digest: ExactDigest
    image_size: MediaSize
    image_profile: ExactProfilePin
    connection: BatchConnectionPinV1
    mapping_version: Literal["1"]
    mapping_digest: ExactDigest
    ordered_units: Annotated[list[AnchorBatchUnitV2], Field(min_length=1, max_length=MAX_LIST_ITEMS)]
    workflow_bindings: Annotated[list[BatchWorkflowBindingV1], Field(min_length=3, max_length=3)]
    readiness: Literal["preparation_only"]
    can_submit: Literal[False]


def project_saved_batch_preparation(result: SavedBatchPreparationV1) -> PublicBatchPreparationV1:
    """Allowlist browser fields, leaving the full immutable handoff/digest untouched."""
    validated = SavedBatchPreparationV1.model_validate(result)
    handoff = validated.prepared_input
    return PublicBatchPreparationV1(schema_version=validated.schema_version,
        source_plan_ref=handoff.source_plan_ref, story_approval=handoff.story_approval,
        stage_id=handoff.stage_id, activation_id=handoff.activation_id, input_digest=validated.input_digest,
        image_size=handoff.image_size, image_profile=handoff.image_profile, connection=handoff.connection,
        mapping_version=handoff.mapping.schema_version, mapping_digest=handoff.mapping_digest,
        ordered_units=handoff.ordered_units, workflow_bindings=handoff.mapping.bindings,
        readiness=validated.readiness, can_submit=validated.can_submit)


def read_saved_batch_input(db: sqlite3.Connection, execution_id: str, *, source_plan_ref: ArtifactRef | dict,
                           image_size: MediaSize | dict, image_profile: ExactProfilePin | dict,
                           connection: BatchConnectionPinV1 | dict, activation_id: str) -> SavedBatchPreparationV1:
    """Resolve one exact saved compact V2 under its original applied Story approval.

    Operation pins alone are insufficient. Reuse the existing read-only terminal
    receipt validator: it audits applied review/decision digests, current Story and
    plan bindings, frozen Start and resume-work lineage without wardrobe_authority
    (which rightly rejects generation after a saved output/terminal outcome).
    No current binding is substituted for the requested artifact/ref.
    """
    _uuid(execution_id)
    if db.execute("SELECT 1 FROM executions WHERE execution_id=?", (execution_id,)).fetchone() is None:
        raise LookupError("Unknown saved batch source execution")
    expected = _exact_artifact_ref(ArtifactRef.model_validate(source_plan_ref))
    if expected.execution_id != execution_id:
        raise ValueError("Saved batch source execution mismatch")
    if db.execute("SELECT 1 FROM execution_controls WHERE execution_id=? AND kind='cancel'", (execution_id,)).fetchone():
        raise ValueError("Cancelled source cannot prepare a batch")
    outcome = db.execute("SELECT outcome,source_id,subject_artifact_id FROM execution_outcomes WHERE execution_id=?",
                         (execution_id,)).fetchone()
    if outcome != ("completed", expected.operation_id, expected.artifact_id):
        raise ValueError("Saved batch source has no exact completed Wardrobe receipt")
    ref, plan = wardrobe_store.read_wardrobe_plan(db, execution_id, artifact_id=expected.artifact_id)
    if ref != expected:
        raise ValueError("Saved batch source must match the entire exact plan ref")
    record = wardrobe_store.read_wardrobe_operation(db, ref.operation_id)
    pins = record["pins"]
    if validate_wardrobe_success(db, execution_id, pins.approval_request_id) != ref:
        raise ValueError("Saved batch source no longer has its applied Story authority")
    work = db.execute("SELECT status FROM execution_work WHERE execution_id=? AND kind='resume' AND source_id=?",
                      (execution_id, pins.approval_request_id)).fetchone()
    if work != ("completed",):
        raise ValueError("Saved batch source approval work is not complete")
    approval = BatchStoryApprovalV1(story_ref=pins.story_ref, approval_request_id=pins.approval_request_id,
        approval_request_digest=pins.approval_request_digest, decision_id=pins.decision_id,
        applied_activation_id=pins.activation_id, story_binding_revision=pins.story_binding_revision)
    handoff = batch_generation.freeze_batch_input(plan, source_plan_ref=ref,
        wardrobe_input=record["config"].wardrobe_input, story_approval=approval, activation_id=activation_id,
        image_size=image_size, image_profile=image_profile, connection=connection)
    return SavedBatchPreparationV1(schema_version="1", prepared_input=handoff,
        input_digest=batch_generation.batch_input_digest(handoff), readiness="preparation_only", can_submit=False)
