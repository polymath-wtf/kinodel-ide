"""Provider-neutral Wardrobe bodies and pure validation, not approval or render readiness."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import AfterValidator, Field, model_validator

from backend.domain import (
    ArtifactRef, ContextSourceRefV1, DomainModel, MAX_LIST_ITEMS, MAX_SUBJECTS,
    MediaSize, Narrative, SelectedCharacterRefs, Story, StoryTextInputV1, StoryV2,
    Text, UnitKey, _exact_artifact_ref, artifact_digest, canonical_json,
    sha256_digest, validate_story_for_text_input,
)


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("Wardrobe text must be nonblank")
    return value


AnchorText = Annotated[Text, AfterValidator(_nonblank)]
AnchorTexts = Annotated[list[AnchorText], Field(max_length=MAX_LIST_ITEMS)]
AnchorKey = Annotated[UnitKey, AfterValidator(_nonblank)]
ExactDigest = Annotated[str, Field(strict=True, pattern=r"^sha256:[0-9a-f]{64}$")]
AnchorRole = Literal["portrait", "background", "character_sheet"]
AnchorUseCase = Literal["hero-face", "location", "hero-sheet"]
AnchorWorkflow = Literal["txt2img", "img2img"]


def _subject_ids(ids: list[str]) -> list[str]:
    for subject in ids:
        _nonblank(subject)
    if len(ids) != len(set(ids)):
        raise ValueError("Wardrobe subject IDs must be unique")
    return ids


AnchorSubjects = Annotated[
    list[UnitKey], Field(max_length=MAX_SUBJECTS), AfterValidator(_subject_ids)
]


def _role_subjects(role: AnchorRole, subjects: list[str]) -> None:
    if (role == "background") != (not subjects):
        raise ValueError("Background must be character-free; portrait/sheet must name subjects")


def _use_case_role(use_case: AnchorUseCase) -> AnchorRole:
    """First Wardrobe capability's semantic roles, not provider workflow selection."""
    if use_case == "hero-face":
        return "portrait"
    if use_case == "location":
        return "background"
    return "character_sheet"


def _narrative_ref(ref: ArtifactRef) -> ArtifactRef:
    _exact_artifact_ref(ref)
    if ref.schema_id != "story" or ref.schema_version not in ("1", "2"):
        raise ValueError("Wardrobe requires an exact StoryV1/V2 ref")
    return ref


NarrativeRef = Annotated[ArtifactRef, AfterValidator(_narrative_ref)]


class AnchorImageRefV1(MediaSize):
    """Adapter-owned immutable image pin; metadata is not proof of measured/authorized bytes."""

    source_id: AnchorKey
    revision_id: AnchorKey
    digest: ExactDigest
    mime_type: Literal["image/png", "image/jpeg", "image/webp"]
    byte_length: Annotated[int, Field(strict=True, gt=0)]


class WardrobeImageEvidenceV1(DomainModel):
    """Visible evidence does not implicitly become a render reference."""

    alias: AnchorKey
    ref: AnchorImageRefV1
    role: AnchorRole
    subject_ids: AnchorSubjects

    @model_validator(mode="after")
    def role_ownership(self):
        _role_subjects(self.role, self.subject_ids)
        return self


class WardrobeTextProjectionV1(DomainModel):
    alias: AnchorKey
    source_ref: ContextSourceRefV1
    role: Literal["canon", "continuity", "inspiration", "evidence", "guidance"]
    content: Annotated[Narrative, AfterValidator(_nonblank)]
    projection_digest: ExactDigest

    @model_validator(mode="after")
    def exact_projection(self):
        if self.source_ref.kind == "artifact":
            _exact_artifact_ref(self.source_ref.ref)
        elif re.fullmatch(r"sha256:[0-9a-f]{64}", self.source_ref.digest) is None:
            raise ValueError("Wardrobe context source digest must be exact")
        if self.projection_digest != sha256_digest(self.content.encode("utf-8")):
            raise ValueError("Frozen Wardrobe text projection digest mismatch")
        return self


class WardrobeInputV2(DomainModel):
    """Prepared direct content; the eventual adapter/store must verify approvals and rights."""

    schema_version: Literal["2"]
    capability_set: Literal["anchor-basics.v2"]
    narrative_ref: NarrativeRef
    story: Story
    narrative_input: StoryTextInputV1
    selected_characters: SelectedCharacterRefs
    text_context: Annotated[list[WardrobeTextProjectionV1], Field(max_length=MAX_LIST_ITEMS)]
    image_evidence: Annotated[list[WardrobeImageEvidenceV1], Field(max_length=MAX_LIST_ITEMS)]

    @model_validator(mode="after")
    def exact_inputs(self):
        if (self.narrative_ref.schema_version != self.story.schema_version
                or self.narrative_ref.digest != artifact_digest(self.story)):
            raise ValueError("Wardrobe exact Story body digest/schema mismatch")
        declared = [subject.subject_id for subject in self.narrative_input.subjects]
        _nonblank(self.narrative_input.user_vibe)
        _subject_ids(declared)
        for subject in self.narrative_input.subjects:
            _nonblank(subject.description)
        if isinstance(self.story, StoryV2):
            _subject_ids([subject.subject_id for subject in self.story.generated_characters])
            for subject in self.story.generated_characters:
                _nonblank(subject.description)
        validate_story_for_text_input(self.story, self.narrative_input,
                                      [shot.shot_id for shot in self.story.shots])
        selected = [ref.subject_id for ref in self.selected_characters]
        if [subject for subject in declared if subject in selected] != selected:
            raise ValueError("Selected characters must match frozen declared subjects and order")
        aliases = [item.alias for item in self.text_context] + [item.alias for item in self.image_evidence]
        if len(aliases) != len(set(aliases)):
            raise ValueError("Wardrobe supplied aliases must be unique")
        images = [(item.ref.source_id, item.ref.revision_id) for item in self.image_evidence]
        if len(images) != len(set(images)):
            raise ValueError("Wardrobe supplied image pins must be unique")
        subjects = _input_subjects(self)
        if any(subject not in subjects for item in self.image_evidence for subject in item.subject_ids):
            raise ValueError("Wardrobe image evidence has unknown subject ownership")
        return self


def _input_subjects(supplied: WardrobeInputV2) -> set[str]:
    subjects = {subject.subject_id for subject in supplied.narrative_input.subjects}
    if isinstance(supplied.story, StoryV2):
        subjects.update(subject.subject_id for subject in supplied.story.generated_characters)
    return subjects


class AnchorDirectionV1(DomainModel):
    appearance: AnchorText
    wardrobe: AnchorText
    environment: AnchorText
    lighting: AnchorText
    palette: AnchorTexts
    must_preserve: AnchorTexts
    prohibited_drift: AnchorTexts


class BatchUnitSourceV2(DomainModel):
    kind: Literal["batch_unit"]
    unit_key: AnchorKey


class AnchorReferenceV2(DomainModel):
    source: BatchUnitSourceV2
    role: AnchorRole
    take: AnchorTexts
    ignore: AnchorTexts


class AnchorBatchUnitV2(DomainModel):
    unit_key: AnchorKey
    subject_ids: AnchorSubjects
    use_case: AnchorUseCase
    workflow: AnchorWorkflow
    purpose: AnchorText
    framing: AnchorText
    drawable_content: AnchorText
    image_prompt: AnchorText
    preserve: AnchorTexts
    ignore: AnchorTexts
    references: Annotated[list[AnchorReferenceV2], Field(max_length=MAX_LIST_ITEMS)]

    @model_validator(mode="after")
    def capability_and_ownership(self):
        _role_subjects(_use_case_role(self.use_case), self.subject_ids)
        if self.use_case == "hero-sheet":
            valid = self.workflow == "img2img" and [ref.role for ref in self.references] == ["portrait", "background"]
        else:
            valid = self.workflow == "txt2img" and not self.references
        if not valid:
            raise ValueError("Wardrobe anchor-basics.v2 capability requires zero-ref txt2img hero-face/location "
                             "or img2img hero-sheet with ordered earlier-unit portrait/background refs")
        return self


def _batch_units(units: list[AnchorBatchUnitV2]) -> list[AnchorBatchUnitV2]:
    earlier: dict[str, AnchorBatchUnitV2] = {}
    for unit in units:
        if unit.unit_key in earlier:
            raise ValueError("Wardrobe batch unit keys must be unique")
        sources = []
        for reference in unit.references:
            source = reference.source
            sources.append(source.unit_key)
            parent = earlier.get(source.unit_key)
            if parent is None:
                raise ValueError("Wardrobe parent must name an earlier batch unit")
            _reference_ownership(unit, reference.role, parent)
        if len(sources) != len(set(sources)):
            raise ValueError("Wardrobe reference sources must be distinct")
        earlier[unit.unit_key] = unit
    return units


def _reference_ownership(unit: AnchorBatchUnitV2, role: AnchorRole, source: AnchorBatchUnitV2) -> None:
    if role != _use_case_role(source.use_case):
        raise ValueError("Wardrobe reference role must match its source role")
    if role != "background" and set(source.subject_ids) != set(unit.subject_ids):
        raise ValueError("Wardrobe reference subjects must match the consuming unit")


class VisualAnchorDraftV2(DomainModel):
    """Model-authored creative fields only; no story pin or persistent image identity."""

    direction: AnchorDirectionV1
    batch_prompt: Annotated[list[AnchorBatchUnitV2], Field(min_length=1, max_length=MAX_LIST_ITEMS),
                            AfterValidator(_batch_units)]


class VisualAnchorPlanV2(DomainModel):
    schema_id: Literal["visual_anchor_plan"]
    schema_version: Literal["2"]
    narrative_ref: NarrativeRef
    direction: AnchorDirectionV1
    batch_prompt: Annotated[list[AnchorBatchUnitV2], Field(min_length=1, max_length=MAX_LIST_ITEMS),
                            AfterValidator(_batch_units)]


class WardrobeResultV2(DomainModel):
    status: Literal["ready", "needs_input", "out_of_scope"]
    plan: VisualAnchorDraftV2 | None
    explanation: Annotated[AnchorText, Field(max_length=4096)] | None

    @model_validator(mode="after")
    def complete_result(self):
        if ((self.status == "ready" and (self.plan is None or self.explanation is not None))
                or (self.status != "ready" and (self.plan is not None or self.explanation is None))):
            raise ValueError("Wardrobe result must contain a complete draft or an explanation")
        return self


def validate_wardrobe_plan(plan: VisualAnchorPlanV2 | dict,
                           supplied: WardrobeInputV2 | dict) -> VisualAnchorPlanV2:
    """Recheck exact inputs and first role contract; does not certify provider capability/approval."""
    prepared: WardrobeInputV2 = WardrobeInputV2.model_validate(supplied)
    canonical_json(prepared)
    validated: VisualAnchorPlanV2 = VisualAnchorPlanV2.model_validate(plan)
    if validated.narrative_ref != prepared.narrative_ref:
        raise ValueError("Wardrobe plan must use the exact supplied narrative ref")
    subjects = _input_subjects(prepared)
    for unit in validated.batch_prompt:
        if not set(unit.subject_ids).issubset(subjects):
            raise ValueError("Wardrobe batch unit has unknown subjects")
    canonical_json(validated)
    return validated


def resolve_wardrobe_draft(draft: VisualAnchorDraftV2 | dict,
                            supplied: WardrobeInputV2 | dict) -> VisualAnchorPlanV2:
    """Inject the exact Story pin into the validated creative draft, without side effects."""
    prepared: WardrobeInputV2 = WardrobeInputV2.model_validate(supplied)
    validated: VisualAnchorDraftV2 = VisualAnchorDraftV2.model_validate(draft)
    return validate_wardrobe_plan({"schema_id": "visual_anchor_plan", "schema_version": "2",
                                  "narrative_ref": prepared.narrative_ref, "direction": validated.direction,
                                  "batch_prompt": validated.batch_prompt}, prepared)
