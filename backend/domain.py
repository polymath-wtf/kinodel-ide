"""Executable foundation DTOs and their canonical JSON encoding."""

from __future__ import annotations

from collections.abc import Sequence
import hashlib
import json
import re
from typing import Annotated, Any, Literal, TypeVar
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator


MAX_JSON_BYTES = 1024 * 1024
MAX_JSON_DEPTH = 32
MAX_STRING_CHARS = 16 * 1024
MAX_NARRATIVE_CHARS = 128 * 1024
MAX_LIST_ITEMS = 256
MAX_SHOTS = 128
MAX_SUBJECTS = 128
MAX_DIMENSION = 16_384
MAX_DURATION_MS = 600_000

_DIGEST_PATTERN = r"sha256:[0-9a-f]{64}"
_ARTIFACT_URI_PATTERN = re.compile(
    r"kinodel://projects/([0-9a-f-]{36})/artifacts/([0-9a-f-]{36})"
)


def _valid_text(value: str) -> str:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValueError("Unicode surrogate code points are not allowed")
    return value


def _canonical_uuid(value: str) -> str:
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as error:
        raise ValueError("Expected a canonical UUID") from error
    if str(parsed) != value:
        raise ValueError("UUID must use canonical lowercase encoding")
    return value


Text = Annotated[
    str, Field(strict=True, min_length=1, max_length=MAX_STRING_CHARS), AfterValidator(_valid_text)
]
Narrative = Annotated[
    str, Field(strict=True, min_length=1, max_length=MAX_NARRATIVE_CHARS), AfterValidator(_valid_text)
]
UnitKey = Annotated[
    str, Field(strict=True, min_length=1, max_length=128), AfterValidator(_valid_text)
]
CanonicalUUID = Annotated[
    str, Field(strict=True, min_length=36, max_length=36), AfterValidator(_canonical_uuid)
]
Digest = Annotated[str, Field(strict=True, pattern=_DIGEST_PATTERN)]


class DomainModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, revalidate_instances="always"
    )


class OwnerResponseV1(DomainModel):
    status: Literal["clarified", "needs_input", "out_of_scope"]
    explanation: Annotated[str, Field(strict=True, min_length=1, max_length=4096), AfterValidator(_valid_text)]


class ArtifactStateRef(DomainModel):
    artifact_id: CanonicalUUID
    schema_id: Text
    schema_version: Text
    uri: Text
    digest: Digest
    media_type: Literal["application/json"]

    @model_validator(mode="after")
    def validate_uri(self) -> ArtifactStateRef:
        match = _ARTIFACT_URI_PATTERN.fullmatch(self.uri)
        if match is None or match.group(2) != self.artifact_id:
            raise ValueError("Artifact URI must contain the exact artifact identity")
        _canonical_uuid(match.group(1))
        return self


class ArtifactRef(ArtifactStateRef):
    project_id: CanonicalUUID
    execution_id: CanonicalUUID
    produced_by_stage: Text
    operation_id: Digest

    @model_validator(mode="after")
    def validate_project_uri(self) -> ArtifactRef:
        match = _ARTIFACT_URI_PATTERN.fullmatch(self.uri)
        if match is None or match.group(1) != self.project_id:
            raise ValueError("Artifact URI must contain the exact project identity")
        return self


class ArtifactContextSourceRefV1(DomainModel):
    kind: Literal["artifact"]
    ref: ArtifactRef


class SourceContextSourceRefV1(DomainModel):
    kind: Literal["source"]
    source_id: Text
    revision_id: Text
    digest: Digest


class AgentResourceContextSourceRefV1(DomainModel):
    kind: Literal["agent_resource"]
    resource_id: Text
    version: Text
    digest: Digest


ContextSourceRefV1 = Annotated[
    ArtifactContextSourceRefV1
    | SourceContextSourceRefV1
    | AgentResourceContextSourceRefV1,
    Field(discriminator="kind"),
]


class InitialContextItemV1(DomainModel):
    source_ref: ContextSourceRefV1
    role: Literal["canon", "continuity", "plan", "inspiration", "evidence", "guidance"]
    required: bool


class SourceMessageV1(DomainModel):
    chat_id: Text
    message_id: Text
    event_id: Text


class InitialRequestV1(DomainModel):
    schema_id: Literal["initial_request"]
    schema_version: Literal["1"]
    message: Narrative
    selected_context: Annotated[list[InitialContextItemV1], Field(max_length=MAX_LIST_ITEMS)]
    source_message: SourceMessageV1 | None


class ProfilePin(DomainModel):
    profile_id: Text
    version: Text
    digest: Digest


class PipelinePin(DomainModel):
    pipeline_id: Text
    version: Text
    spec_digest: Digest


class GenerationProfiles(DomainModel):
    image: ProfilePin
    video: ProfilePin


class SubjectV1(DomainModel):
    subject_id: UnitKey
    description: Text
    character_ref: ArtifactRef | None


class AspectRatio(DomainModel):
    numerator: Annotated[int, Field(strict=True, gt=0, le=MAX_DIMENSION)]
    denominator: Annotated[int, Field(strict=True, gt=0, le=MAX_DIMENSION)]


class ProductionSettings(DomainModel):
    shot_count: Annotated[int, Field(strict=True, gt=0, le=MAX_SHOTS)]
    shot_duration_ms: Annotated[int, Field(strict=True, gt=0, le=MAX_DURATION_MS)]
    width: Annotated[int, Field(strict=True, gt=0, le=MAX_DIMENSION)]
    height: Annotated[int, Field(strict=True, gt=0, le=MAX_DIMENSION)]
    aspect_ratio: AspectRatio
    output_format: Text
    workflow_class: Literal["i2v"]
    audio_policy: Literal["silent"]

    @model_validator(mode="after")
    def validate_aspect_ratio(self) -> ProductionSettings:
        if self.width * self.aspect_ratio.denominator != self.height * self.aspect_ratio.numerator:
            raise ValueError("Dimensions do not match the aspect ratio")
        return self


SettingField = Literal[
    "user_vibe",
    "must_keep",
    "exclusions",
    "assumptions",
    "subjects",
    "pipeline",
    "generation_profiles.image",
    "generation_profiles.video",
    "production.shot_count",
    "production.shot_duration_ms",
    "production.width",
    "production.height",
    "production.aspect_ratio",
    "production.output_format",
    "production.workflow_class",
    "production.audio_policy",
]


class SettingOriginV1(DomainModel):
    field: SettingField
    origin: Literal["explicit", "product_default", "assumption"]
    source_ref: ContextSourceRefV1 | None

class BriefV1(DomainModel):
    schema_id: Literal["brief"]
    schema_version: Literal["1"]
    user_vibe: Narrative
    must_keep: Annotated[list[Text], Field(max_length=MAX_LIST_ITEMS)]
    exclusions: Annotated[list[Text], Field(max_length=MAX_LIST_ITEMS)]
    assumptions: Annotated[list[Text], Field(max_length=MAX_LIST_ITEMS)]
    subjects: Annotated[list[SubjectV1], Field(max_length=MAX_SUBJECTS)]
    pipeline: PipelinePin
    generation_profiles: GenerationProfiles
    production: ProductionSettings
    setting_origins: Annotated[list[SettingOriginV1], Field(max_length=MAX_LIST_ITEMS)]

    @model_validator(mode="after")
    def validate_unique_subjects(self) -> BriefV1:
        subject_ids = [subject.subject_id for subject in self.subjects]
        if len(subject_ids) != len(set(subject_ids)):
            raise ValueError("Brief subject IDs must be unique")
        return self


class StoryShotV1(DomainModel):
    shot_id: UnitKey
    action: Text
    narrative_function: Text
    subject_ids: Annotated[list[UnitKey], Field(max_length=MAX_SUBJECTS)]
    state_before: Text
    state_after: Text

    @model_validator(mode="after")
    def validate_unique_subjects(self) -> StoryShotV1:
        if len(self.subject_ids) != len(set(self.subject_ids)):
            raise ValueError("Story shot subject IDs must be unique")
        return self


class StoryV1(DomainModel):
    schema_id: Literal["story"]
    schema_version: Literal["1"]
    hook: Text
    story: Narrative
    shots: Annotated[list[StoryShotV1], Field(min_length=1, max_length=MAX_SHOTS)]

    @model_validator(mode="after")
    def validate_unique_shots(self) -> StoryV1:
        shot_ids = [shot.shot_id for shot in self.shots]
        if len(shot_ids) != len(set(shot_ids)):
            raise ValueError("Story shot IDs must be unique")
        return self


ModelT = TypeVar("ModelT", bound=DomainModel)


def _revalidate(model: ModelT) -> ModelT:
    return type(model).model_validate(model.model_dump(mode="python"), strict=True)


def canonical_json(model: DomainModel) -> bytes:
    """Encode a revalidated body using canonical_json_v1."""
    validated = _revalidate(model)
    value = validated.model_dump(
        mode="json", exclude_none=False, exclude_unset=False, exclude_defaults=False
    )
    body = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    if len(body) > MAX_JSON_BYTES:
        raise ValueError("Canonical JSON body is too large")
    return body


def sha256_digest(body: bytes) -> str:
    if type(body) is not bytes:
        raise TypeError("Digest input must be bytes")
    return "sha256:" + hashlib.sha256(body).hexdigest()


def artifact_digest(model: DomainModel) -> str:
    """Hash only the canonical creative body bytes."""
    return sha256_digest(canonical_json(model))


def _reject_float(value: str) -> Any:
    raise ValueError(f"Floating-point JSON value is not allowed: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def _check_depth(body: bytes) -> None:
    depth = 0
    quoted = False
    escaped = False
    for byte in body:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                quoted = False
        elif byte == 0x22:
            quoted = True
        elif byte in (0x7B, 0x5B):
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise ValueError("JSON nesting is too deep")
        elif byte in (0x7D, 0x5D):
            depth -= 1


def _reject_surrogates(value: Any) -> None:
    if isinstance(value, str):
        _valid_text(value)
    elif isinstance(value, list):
        for item in value:
            _reject_surrogates(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            _valid_text(key)
            _reject_surrogates(item)


def parse_json_model(body: bytes, model_type: type[ModelT]) -> ModelT:
    """Parse the one accepted foundation wire form: bounded strict UTF-8 bytes."""
    if type(body) is not bytes:
        raise TypeError("JSON body must be bytes")
    if len(body) > MAX_JSON_BYTES:
        raise ValueError("JSON body is too large")
    if body.startswith(b"\xef\xbb\xbf"):
        raise ValueError("UTF-8 BOM is not allowed")
    _check_depth(body)
    text = body.decode("utf-8", errors="strict")
    value = json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_float=_reject_float,
        parse_constant=_reject_float,
    )
    _reject_surrogates(value)
    return model_type.model_validate(value, strict=True)


def make_operation_id(
    execution_id: str,
    stage_id: str,
    activation_id: str,
    operation_kind: str,
    task_id: str | None = None,
) -> str:
    """Derive the operation identity from the documented tagged tuple."""
    _canonical_uuid(execution_id)
    if not isinstance(activation_id, str) or re.fullmatch(_DIGEST_PATTERN, activation_id) is None:
        raise ValueError("Activation ID must use lowercase sha256 encoding")
    for value in (stage_id, operation_kind):
        if not isinstance(value, str) or not 1 <= len(value) <= MAX_STRING_CHARS:
            raise ValueError("Operation tuple strings must be non-empty and bounded")
        _valid_text(value)
    if task_id is not None:
        if not isinstance(task_id, str) or not 1 <= len(task_id) <= MAX_STRING_CHARS:
            raise ValueError("Task ID must be non-empty and bounded")
        _valid_text(task_id)
    identity = [
        "kinodel.operation.v1", execution_id, stage_id, activation_id, operation_kind, task_id
    ]
    encoded = json.dumps(
        identity, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return sha256_digest(encoded)


def validate_story_for_brief(
    story: StoryV1, brief: BriefV1, expected_shot_ids: Sequence[str]
) -> None:
    """Validate deterministic Story coverage against its prepared Brief input."""
    story = _revalidate(story)
    brief = _revalidate(brief)
    expected = list(expected_shot_ids)
    if not 1 <= len(expected) <= MAX_SHOTS:
        raise ValueError("Expected shot IDs must be non-empty and bounded")
    for shot_id in expected:
        if not isinstance(shot_id, str) or not 1 <= len(shot_id) <= 128:
            raise ValueError("Expected shot IDs must be UnitKeys")
        _valid_text(shot_id)
    if len(expected) != len(set(expected)):
        raise ValueError("Expected shot IDs must be unique")
    actual = [shot.shot_id for shot in story.shots]
    if len(actual) != brief.production.shot_count:
        raise ValueError("Story shot count must match Brief")
    if actual != expected:
        raise ValueError("Story shot IDs and order must match the prepared keys")
    declared_subjects = {subject.subject_id for subject in brief.subjects}
    if any(subject_id not in declared_subjects for shot in story.shots for subject_id in shot.subject_ids):
        raise ValueError("Every Story subject must be declared in Brief")
