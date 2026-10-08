"""Restricted, offline Wardrobe V2 handoff and pre-upload unit preparation.

The trusted caller resolves the committed plan, applied Story approval and exact
WardrobeInputV2 before freezing. Resolver steps 5/6 own parent import/lineage,
actual bytes, rights and upload receipts: these pins prove none of those things.
Persist canonical bodies AND their digests in trusted storage before effects.
No DB, transport, creative generation, approval or scheduling lives here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from typing import Annotated, Any, Literal

from pydantic import Field, TypeAdapter, model_validator

from backend import comfyui_workflows as registry, production
from backend.domain import (ArtifactRef, DomainModel, ExactProfilePin, MAX_JSON_BYTES, MAX_LIST_ITEMS,
                            MediaSize, Text, _exact_artifact_ref, artifact_digest,
                            canonical_json, parse_json_model, sha256_digest)
from backend.wardrobe import (AnchorBatchUnitV2, AnchorKey, AnchorRole, AnchorText, AnchorUseCase,
                              AnchorWorkflow, ExactDigest, NarrativeRef, VisualAnchorPlanV2,
                              WardrobeInputV2, validate_wardrobe_plan)


_SIGNATURES = (
    ("hero-face", "txt2img", [], "krea2-txt2img", "portrait"),
    ("location", "txt2img", [], "krea2-txt2img", "background"),
    ("hero-sheet", "img2img", ["portrait", "background"], "qwen21-multi-img2img", "sheet"),
)


class BatchStoryApprovalV1(DomainModel):
    """Provenance supplied by a trusted applied-approval resolver, not authorization."""

    story_ref: NarrativeRef
    approval_request_id: ExactDigest
    approval_request_digest: ExactDigest
    decision_id: ExactDigest
    applied_activation_id: ExactDigest
    story_binding_revision: Annotated[int, Field(strict=True, ge=1)]


class BatchConnectionPinV1(DomainModel):
    """Native connection identity only; endpoint/credentials remain with the worker."""

    connection: Literal["local", "server"]
    endpoint_digest: ExactDigest


class BatchWorkflowBindingV1(DomainModel):
    use_case: AnchorUseCase
    workflow: AnchorWorkflow
    reference_roles: Annotated[list[AnchorRole], Field(max_length=2)]
    workflow_id: Text
    kind: Literal["portrait", "background", "sheet"]
    registry_digest: ExactDigest


class BatchStageMappingV1(DomainModel):
    """First technical mapping version; independent of creative plan numbering."""

    schema_version: Literal["1"]
    stage_id: Literal["anchor-batch"]
    bindings: Annotated[list[BatchWorkflowBindingV1], Field(min_length=3, max_length=3)]

    @model_validator(mode="after")
    def supported_signatures(self):
        signatures = tuple((b.use_case, b.workflow, b.reference_roles, b.workflow_id, b.kind)
                           for b in self.bindings)
        if signatures != _SIGNATURES:
            raise ValueError("Unsupported Wardrobe batch mapping")
        return self


def _frozen_workflows(snapshot: dict[str, Any]) -> dict[str, dict]:
    try:
        specs = snapshot["workflows"]
        if type(specs) is not list or any(type(spec) is not dict for spec in specs):
            raise ValueError("Invalid frozen profile workflows")
        ids = [spec["id"] for spec in specs]
        if ids != ["krea2-txt2img", "qwen21-multi-img2img"]:
            raise ValueError("Unsupported frozen profile workflows")
        return dict(zip(ids, specs, strict=True))
    except (KeyError, TypeError) as error:
        raise ValueError("Invalid frozen profile workflows") from error


class BatchGenerationInputV1(DomainModel):
    """Technical handoff, not a creative artifact or permission to start a job."""

    schema_id: Literal["batch_generation_input"]
    schema_version: Literal["1"]
    stage_id: Literal["anchor-batch"]
    activation_id: ExactDigest
    source_plan_ref: ArtifactRef
    story_approval: BatchStoryApprovalV1
    wardrobe_input_digest: ExactDigest
    image_size: MediaSize
    image_profile: ExactProfilePin
    connection: BatchConnectionPinV1
    profile_snapshot: dict[str, Any]
    mapping: BatchStageMappingV1
    mapping_digest: ExactDigest
    ordered_units: Annotated[list[AnchorBatchUnitV2], Field(min_length=1, max_length=MAX_LIST_ITEMS)]

    @model_validator(mode="after")
    def exact_handoff(self):
        ref = _exact_artifact_ref(self.source_plan_ref)
        story = self.story_approval.story_ref
        if ((ref.schema_id, ref.schema_version, ref.produced_by_stage) != ("visual_anchor_plan", "2", "wardrobe")
                or (ref.project_id, ref.execution_id) != (story.project_id, story.execution_id)
                or story.produced_by_stage != "storytell"):
            raise ValueError("Batch requires the exact same-execution Wardrobe V2 and approved Story pins")
        plan = VisualAnchorPlanV2(schema_id="visual_anchor_plan", schema_version="2",
                                 narrative_ref=story, batch_prompt=self.ordered_units)
        if ref.digest != artifact_digest(plan):
            raise ValueError("Batch source plan digest mismatch")
        if self.mapping_digest != sha256_digest(canonical_json(self.mapping)):
            raise ValueError("Batch mapping digest mismatch")
        snapshot = self.profile_snapshot
        specs = _frozen_workflows(snapshot)
        if (set(snapshot) != {"schema_version", "profile_id", "version", "provider", "readiness", "can_run",
                             "roles", "supported_sizes", "workflows"}
                or snapshot["schema_version"] != "1" or snapshot["provider"] != "comfyui"
                or snapshot["readiness"] != "preparation_only" or snapshot["can_run"] is not False
                or (snapshot["profile_id"], snapshot["version"]) != ("comfyui-image-preparation", "1")
                or (self.image_profile.profile_id, self.image_profile.version) !=
                   (snapshot["profile_id"], snapshot["version"])
                or self.image_profile.digest != "sha256:" + registry.canonical_digest(snapshot)):
            raise ValueError("Batch image profile snapshot mismatch")
        if self.image_size.model_dump(mode="json") not in snapshot["supported_sizes"]:
            raise ValueError("Unsupported batch image size")
        try:
            for binding in self.mapping.bindings:
                spec = specs[binding.workflow_id]
                if (binding.registry_digest != "sha256:" + registry.canonical_digest(spec)
                        or spec["preparation_enabled"] is not True
                        or dict(spec["kinds"])[binding.kind] != binding.reference_roles
                        or len(spec["mapping"]["slots"]) < len(binding.reference_roles)
                        or [self.image_size.width, self.image_size.height] not in spec["supported_sizes"]):
                    raise ValueError("Batch workflow mapping/profile mismatch")
        except (KeyError, TypeError) as error:
            raise ValueError("Invalid frozen batch workflow mapping") from error
        return self


def freeze_batch_input(plan: VisualAnchorPlanV2 | dict, *, source_plan_ref: ArtifactRef | dict,
                       wardrobe_input: WardrobeInputV2 | dict, story_approval: BatchStoryApprovalV1 | dict,
                       activation_id: str, image_size: MediaSize | dict, image_profile: ExactProfilePin | dict,
                       connection: BatchConnectionPinV1 | dict) -> BatchGenerationInputV1:
    """Validate exact caller authority and freeze today's declared preparation profile.

    No latest-source lookup or approval boolean is accepted. The caller must verify
    the committed source/approval itself. Evidence shown to Wardrobe is not copied
    into render bindings. This function neither samples seeds nor prepares children.
    """
    supplied = WardrobeInputV2.model_validate(wardrobe_input)
    validated = validate_wardrobe_plan(VisualAnchorPlanV2.model_validate(plan), supplied)
    approval = BatchStoryApprovalV1.model_validate(story_approval)
    if approval.story_ref != supplied.narrative_ref:
        raise ValueError("Batch approval must pin the exact Wardrobe authority Story")
    profile = TypeAdapter(ExactProfilePin).validate_python(image_profile, strict=True)
    matches = [p for p in production.production_catalog()["image_only"]["profiles"] if p["pin"] == profile.model_dump()]
    if len(matches) != 1:
        raise ValueError("Unknown or stale batch image profile")
    public = {key: value for key, value in matches[0].items() if key != "pin"}
    ids = sorted({role["workflow_id"] for role in public["roles"]})
    specs = {identity: registry.workflow_snapshot(identity) for identity in ids}
    snapshot = {"schema_version": "1", "profile_id": profile.profile_id, "version": profile.version,
                **public, "workflows": [specs[identity] for identity in ids]}
    mapping = BatchStageMappingV1(schema_version="1", stage_id="anchor-batch", bindings=[
        BatchWorkflowBindingV1(use_case=use_case, workflow=mode, reference_roles=roles,
                               workflow_id=identity, kind=kind,
                               registry_digest="sha256:" + registry.canonical_digest(specs[identity]))
        for use_case, mode, roles, identity, kind in _SIGNATURES])
    batch = BatchGenerationInputV1(schema_id="batch_generation_input", schema_version="1", stage_id="anchor-batch",
        activation_id=activation_id, source_plan_ref=source_plan_ref, story_approval=approval,
        wardrobe_input_digest=sha256_digest(canonical_json(supplied)), image_size=image_size,
        image_profile=profile, connection=connection, profile_snapshot=snapshot, mapping=mapping,
        mapping_digest=sha256_digest(canonical_json(mapping)), ordered_units=validated.batch_prompt)
    canonical_json(batch)
    return batch


def batch_input_digest(batch: BatchGenerationInputV1 | dict) -> str:
    """Canonical handoff identity includes activation, authority, settings and order."""
    return sha256_digest(canonical_json(BatchGenerationInputV1.model_validate(batch)))


def _replay_body(body: bytes, model_type, expected_digest: str):
    value = parse_json_model(body, model_type)
    if canonical_json(value) != body or sha256_digest(body) != expected_digest:
        raise ValueError("Frozen batch body identity/digest mismatch")
    return value


def replay_batch_input(body: bytes, *, expected_digest: str) -> BatchGenerationInputV1:
    """Read the original stored identity, without current registry/catalog or effects.

    Digests detect corruption, not authorization. expected_digest must come from
    trusted immutable storage, never from the submitted body itself.
    """
    return _replay_body(body, BatchGenerationInputV1, expected_digest)


class BatchParentBindingV1(DomainModel):
    """Resolver-owned exact earlier candidate and planned name, NOT an upload receipt.

    Metadata alone proves neither verified import/bytes nor rights. No candidate,
    approval or provider name is invented by this layer.
    """

    unit_key: AnchorKey
    source_id: AnchorKey
    digest: ExactDigest
    input_name: AnchorText


ParentBindings = Annotated[list[BatchParentBindingV1], Field(max_length=2)]


class PreparedBatchUnitV1(DomainModel):
    schema_version: Literal["1"]
    batch_input_digest: ExactDigest
    unit_key: AnchorKey
    parent_bindings: ParentBindings
    # The registry's wire format contains schema floats. Keep its exact canonical
    # JSON opaque to the foundation parser (which intentionally forbids floats).
    image_pin_json: Annotated[str, Field(strict=True, min_length=1, max_length=MAX_JSON_BYTES)]

    @model_validator(mode="after")
    def valid_prepared_pin(self):
        pin = registry.replay_prepared(self.image_pin_json)
        if self.image_pin_json != _pin_json(pin):
            raise ValueError("Noncanonical prepared image pin")
        return self


def _pin_json(pin: dict) -> str:
    return json.dumps(pin, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _unit(batch: BatchGenerationInputV1 | dict, unit_key: str):
    validated = BatchGenerationInputV1.model_validate(batch)
    canonical_json(validated)
    unit = next((unit for unit in validated.ordered_units if unit.unit_key == unit_key), None)
    if unit is None:
        raise ValueError("Unknown batch unit key")
    binding = next(b for b in validated.mapping.bindings if b.use_case == unit.use_case)
    return validated, unit, binding


def _parents(unit: AnchorBatchUnitV2, bindings: ParentBindings | list[dict]):
    parents = TypeAdapter(ParentBindings).validate_python(bindings, strict=True)
    if ([parent.unit_key for parent in parents] != [ref.source.unit_key for ref in unit.references]
            or len({parent.source_id for parent in parents}) != len(parents)):
        raise ValueError("Missing, mismatched or duplicate ordered batch parents")
    refs = [registry.ReferenceSnapshot(role=reference.role, source_id=parent.source_id,
                                      sha256=parent.digest.removeprefix("sha256:"), input_name=parent.input_name)
            for reference, parent in zip(unit.references, parents, strict=True)]
    return parents, refs


def prepare_batch_unit(batch: BatchGenerationInputV1 | dict, unit_key: str, *,
                       parent_bindings: ParentBindings | list[dict], template: bytes,
                       schemas: Mapping[str, dict], model_inventory: Mapping[str, Sequence[str]] | None = None,
                       seed: int | None = None) -> PreparedBatchUnitV1:
    """Prepare only this unit when all exact resolver-provided parents are available.

    Caller supplies trusted installed schemas/template/inventory. Existing registry
    validation and ONCE-only seed resolution run before returning a pre-upload pin.
    Persist the returned body/digest; technical replay must use replay_batch_unit.
    """
    validated, unit, binding = _unit(batch, unit_key)
    parents, refs = _parents(unit, parent_bindings)
    current = registry.workflow_snapshot(binding.workflow_id)
    frozen = _frozen_workflows(validated.profile_snapshot)[binding.workflow_id]
    if registry.canonical_digest(current) != registry.canonical_digest(frozen):
        raise ValueError("Batch registry changed; refuse new preparation under frozen mapping")
    pin = registry.prepare_image(binding.workflow_id, template, kind=binding.kind,
        settings=registry.ImageSettings(prompt=unit.image_prompt, width=validated.image_size.width,
                                        height=validated.image_size.height, seed=seed),
        references=refs, schemas=schemas, model_inventory=model_inventory)
    prepared = PreparedBatchUnitV1(schema_version="1", batch_input_digest=batch_input_digest(validated),
                                  unit_key=unit.unit_key, parent_bindings=parents, image_pin_json=_pin_json(pin))
    canonical_json(prepared)
    return prepared


def replay_batch_unit(batch: BatchGenerationInputV1 | dict, body: bytes, *, expected_digest: str,
                      parent_bindings: ParentBindings | list[dict]) -> PreparedBatchUnitV1:
    """Revalidate original unit/parent pins and resolved seed without re-preparing.

    Rights/import/byte verification still belongs to the caller before any effect.
    The expected body digest is the original protected storage record's digest.
    """
    prepared = _replay_body(body, PreparedBatchUnitV1, expected_digest)
    validated, unit, binding = _unit(batch, prepared.unit_key)
    parents, refs = _parents(unit, parent_bindings)
    pin = registry.replay_prepared(prepared.image_pin_json)
    expected_refs = [{"role": ref.role, "source_id": ref.source_id, "sha256": ref.sha256,
                      "input_name": ref.input_name} for ref in refs]
    if (prepared.batch_input_digest != batch_input_digest(validated) or prepared.parent_bindings != parents
            or pin["registry_sha256"] != binding.registry_digest.removeprefix("sha256:")
            or pin["kind"] != binding.kind or pin["references"] != expected_refs
            or pin["settings"]["prompt"] != unit.image_prompt
            or (pin["settings"]["width"], pin["settings"]["height"]) !=
               (validated.image_size.width, validated.image_size.height)):
        raise ValueError("Prepared batch unit/source/parent identity mismatch")
    return prepared
