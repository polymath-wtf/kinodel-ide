"""Concrete first Wardrobe operation under the caller's local data-root ownership.

No approval application, graph registration, queue or revision machinery. The
new route's applied Story approval is a required input, not something this store
can create. Character delete hides a card; general ACL/withdrawal is not active.
"""

import json
import sqlite3
from typing import Literal
from uuid import uuid4

from pydantic import Field, TypeAdapter, model_validator

from backend.domain import (ArtifactRef, CanonicalUUID, DomainModel, MAX_JSON_BYTES,
                            OwnerResponseV1, Text, canonical_json, make_operation_id,
                            parse_json_model, sha256_digest, validate_story_for_text_input)
from backend.openrouter import SelectedCharacter, StoryOwnerConfigV2, read_owner_config
from backend.openrouter_client import TransportException, TransportPhase, encode
from backend.openrouter_wardrobe import (WardrobeInvalidOutput, WardrobeOwnerConfigV1, WardrobeOwnerUnavailable, prepare_wardrobe_repair,
                                        read_wardrobe_config)
from backend.review_store import _digest
from backend.story_start import _payload_digest
from backend.story_store import (_assert_writable, _check_file, _destination, _publish,
                                 _uuid, _validated_test_inputs, read_story)
from backend.wardrobe import (ExactDigest, VisualAnchorPlanV1, WardrobeImageEvidenceV1,
                              WardrobeInputV1, WardrobeTextProjectionV1, validate_wardrobe_plan)


GRAPH_ID = "kinodel.story-wardrobe"
GRAPH_VERSION = "1"
GRAPH_DIGEST = sha256_digest(b"kinodel.story-wardrobe.v1:OpenRouter+frozen-storytell-v2+text-input+generated-cast>storytell>story_prepare_review>story_wait>story_apply>wardrobe>END|clarify+revise>storytell")


class WardrobeAttemptBudgetExhausted(ValueError):
    """The hard two-completion allowance cannot be expanded by technical retry."""


class WardrobeAuthorityV1(DomainModel):
    execution_id: CanonicalUUID
    activation_id: ExactDigest
    approval_request_id: ExactDigest
    approval_request_digest: ExactDigest
    decision_id: ExactDigest
    story_ref: ArtifactRef
    story_binding_revision: int = Field(ge=1)
    start_digest: ExactDigest
    story_owner_config_digest: ExactDigest


class PreparedWardrobeInputsV1(WardrobeAuthorityV1):
    schema_version: Literal["1"]
    wardrobe_config_digest: ExactDigest
    repair_instruction: Text
    repair_request_digest: ExactDigest
    planned_artifact_id: CanonicalUUID


class WardrobeValidationDiagnostic(DomainModel):
    attempt: int = Field(ge=1, le=2)
    code: Literal["invalid_envelope", "incomplete_output", "tool_calls", "non_text_content",
                  "invalid_result", "response_limit"]


class WardrobeProviderDiagnostic(DomainModel):
    """Latest actual failed HTTP attempt; no raw messages or claimed provider receipt."""

    attempt: int = Field(ge=1, le=2)
    stage: Literal["http", "transport"]
    status_code: int | None = Field(default=None, ge=100, le=599)
    exception_type: TransportException | None = None
    previous_validation: WardrobeValidationDiagnostic | None = None
    elapsed_ms: int | None = Field(default=None, ge=0, strict=True)
    phase: TransportPhase | None = None

    @model_validator(mode="after")
    def consistent_evidence(self):
        if (self.stage == "http" and (self.status_code is None or self.exception_type is not None)
                or self.stage == "transport" and self.exception_type is None
                or self.previous_validation is not None and self.previous_validation.attempt >= self.attempt):
            raise ValueError("Wardrobe provider diagnostic evidence mismatch")
        return self


WardrobeDiagnostic = WardrobeValidationDiagnostic | WardrobeProviderDiagnostic
WARDROBE_DIAGNOSTIC = TypeAdapter(WardrobeDiagnostic)


def wardrobe_authority(db: sqlite3.Connection, execution_id: str, request_id: str
                       ) -> tuple[WardrobeAuthorityV1, WardrobeInputV1, list[SelectedCharacter]]:
    """Rehydrate ONLY committed start/Story/approval authority, without image reads."""
    _uuid(execution_id)
    _assert_writable(db, execution_id)
    row = db.execute("SELECT project_id,input_message,shot_ids,client_key,start_digest,graph_id,"
                     "graph_version,graph_digest,owner_config FROM executions WHERE execution_id=?",
                     (execution_id,)).fetchone()
    if row is None or row[5:8] != (GRAPH_ID, GRAPH_VERSION, GRAPH_DIGEST):
        raise ValueError("Wardrobe requires its exact new frozen route identity")
    config = read_owner_config(row[8])
    if not isinstance(config, StoryOwnerConfigV2):
        raise ValueError("Wardrobe requires frozen Story owner configuration v2")
    shots = json.loads(row[2])
    _validated_test_inputs(row[0], row[1], shots)
    work = db.execute("SELECT source_id,payload_digest FROM execution_work WHERE execution_id=? AND kind='start'",
                      (execution_id,)).fetchall()
    if (not isinstance(row[3], str) or not 0 < len(row[3]) <= 256
            or row[1] != config.brief.user_vibe or not 1 <= len(shots) <= 8
            or row[4] != _payload_digest(row[1], shots, row[8]) or work != [(execution_id, row[4])]):
        raise ValueError("Wardrobe frozen start/work lineage mismatch")
    cursor = db.execute("SELECT * FROM review_requests WHERE execution_id=? AND request_id=?",
                        (execution_id, request_id))
    values = cursor.fetchone()
    if values is None:
        raise ValueError("Wardrobe requires exact applied Story approval")
    review = dict(zip((column[0] for column in cursor.description), values))
    applied = _digest("kinodel.story-review-apply.v1", request_id, review["decision_id"], "approve")
    if (review["action"] != "approve" or review["message"] is not None
            or not all(review[key] for key in ("checkpoint_id", "task_id", "interrupt_id", "decision_key", "decision_id"))
            or review["applied_activation"] != applied
            or request_id != _digest("kinodel.story-review.v1", execution_id, review["trigger_activation"])
            or review["request_digest"] != _digest("kinodel.story-review-body.v1", request_id, review["request_revision"],
                review["subject_artifact_id"], review["subject_digest"], review["binding_revision"], review["previous_request_id"])
            or review["decision_digest"] != _digest("kinodel.story-decision.v1", request_id, review["request_digest"],
                review["binding_revision"], "approve", None)
            or review["decision_id"] != _digest("kinodel.story-decision-id.v1", request_id, review["decision_key"])
            or db.execute("SELECT request_id FROM review_requests WHERE execution_id=? ORDER BY request_revision DESC LIMIT 1",
                          (execution_id,)).fetchone() != (request_id,)):
        raise ValueError("Wardrobe applied Story approval receipt mismatch")
    resume = db.execute("SELECT work_id,payload_digest,resume_ref FROM execution_work "
                        "WHERE execution_id=? AND kind='resume' AND source_id=?", (execution_id, request_id)).fetchone()
    if resume != (_digest("kinodel.story-resume-work.v1", review["decision_id"]), review["decision_digest"], review["decision_id"]):
        raise ValueError("Wardrobe approval resume-work lineage mismatch")
    current = db.execute("SELECT artifact_id,binding_revision FROM execution_bindings WHERE execution_id=? AND slot='story'",
                         (execution_id,)).fetchone()
    if current != (review["subject_artifact_id"], review["binding_revision"]):
        raise ValueError("Wardrobe Story binding is stale")
    ref, story = read_story(db, execution_id, artifact_id=review["subject_artifact_id"])
    if (ref.project_id != row[0] or ref.schema_id != "story" or ref.schema_version not in ("1", "2")
            or ref.produced_by_stage != "storytell" or ref.digest != review["subject_digest"]):
        raise ValueError("Wardrobe approved Story ref mismatch")
    validate_story_for_text_input(story, config.brief, shots)
    if db.execute("SELECT 1 FROM execution_bindings WHERE execution_id=? AND slot='wardrobe_plan'", (execution_id,)).fetchone():
        raise ValueError("Wardrobe initial output binding already exists")
    texts, images = [], []
    for index, selected in enumerate(config.selected_characters):
        content = selected.narrative_subject().description
        texts.append(WardrobeTextProjectionV1(alias=f"character-bio-{index}", role="canon", content=content,
            projection_digest=sha256_digest(content.encode("utf-8")), source_ref={"kind": "source",
                "source_id": selected.ref.subject_id, "revision_id": str(selected.ref.revision), "digest": selected.ref.digest}))
        for image_index, image in enumerate(selected.character.images):
            images.append(WardrobeImageEvidenceV1(alias=f"character-image-{index}-{image_index}", role="portrait",
                subject_ids=[selected.ref.subject_id], ref={"source_id": f"{selected.ref.subject_id}-image-{image_index}",
                    "revision_id": str(selected.ref.revision), **image.model_dump(mode="json")}))
    supplied = WardrobeInputV1(schema_version="1", capability_set="anchor-basics.v1", narrative_ref=ref,
        story=story, narrative_input=config.brief, selected_characters=[selected.ref for selected in config.selected_characters],
        text_context=texts, image_evidence=images)
    canonical_json(supplied)
    authority = WardrobeAuthorityV1(execution_id=execution_id, activation_id=applied, approval_request_id=request_id,
        approval_request_digest=review["request_digest"], decision_id=review["decision_id"], story_ref=ref,
        story_binding_revision=review["binding_revision"], start_digest=row[4], story_owner_config_digest=sha256_digest(row[8].encode("utf-8")))
    return authority, supplied, config.selected_characters


def _candidate(kind: str, body: str, supplied: WardrobeInputV1):
    result = parse_json_model(body.encode("utf-8"), VisualAnchorPlanV1 if kind == "plan" else OwnerResponseV1)
    if canonical_json(result).decode("utf-8") != body:
        raise ValueError("Wardrobe candidate is not canonical")
    if isinstance(result, VisualAnchorPlanV1):
        return validate_wardrobe_plan(result, supplied)
    if result.status not in ("needs_input", "out_of_scope") or not result.explanation.strip():
        raise ValueError("Invalid Wardrobe non-ready result")
    return result


def _transition(record: dict) -> str:
    return _digest("kinodel.wardrobe-result.v1", record["operation_id"], record["input_digest"],
                   record["candidate_kind"], record["candidate_digest"])


def read_wardrobe_operation(db: sqlite3.Connection, operation_id: str) -> dict:
    """Every persisted read revalidates canonical configuration/request/candidate pins."""
    cursor = db.execute("SELECT * FROM wardrobe_operations WHERE operation_id=?", (operation_id,))
    row = cursor.fetchone()
    if row is None:
        raise ValueError("Unknown prepared Wardrobe operation")
    record = dict(zip((column[0] for column in cursor.description), row))
    pins = parse_json_model(record["prepared_inputs"].encode("utf-8"), PreparedWardrobeInputsV1)
    if (canonical_json(pins).decode("utf-8") != record["prepared_inputs"]
            or sha256_digest(canonical_json(pins)) != record["input_digest"]
            or (pins.execution_id, pins.activation_id, pins.approval_request_id) !=
               (record["execution_id"], record["activation_id"], record["approval_request_id"])
            or make_operation_id(pins.execution_id, "wardrobe", pins.activation_id, "generate") != operation_id
            or pins.activation_id != _digest("kinodel.story-review-apply.v1", pins.approval_request_id, pins.decision_id, "approve")
            or sha256_digest(record["owner_config"].encode("utf-8")) != pins.wardrobe_config_digest):
        raise ValueError("Wardrobe prepared input pins mismatch")
    config = read_wardrobe_config(record["owner_config"])
    if (config.wardrobe_input.narrative_ref != pins.story_ref
            or sha256_digest(record["repair_request"].encode("utf-8")) != pins.repair_request_digest
            or prepare_wardrobe_repair(record["owner_config"], pins.repair_instruction) != record["repair_request"]):
        raise ValueError("Wardrobe frozen request pins mismatch")
    diagnostic = None
    if record["validation_diagnostic"] is not None:
        if len(record["validation_diagnostic"].encode("utf-8")) > MAX_JSON_BYTES:
            raise ValueError("Wardrobe diagnostic exceeds size limit")
        diagnostic = WARDROBE_DIAGNOSTIC.validate_json(record["validation_diagnostic"], strict=True)
        historical_fields = {"elapsed_ms", "phase"} - diagnostic.model_fields_set
        if (encode(diagnostic.model_dump(mode="json", exclude=historical_fields)) != record["validation_diagnostic"]
                or diagnostic.attempt > record["owner_attempts"]):
            raise ValueError("Wardrobe diagnostic attempt mismatch")
    validation = diagnostic.previous_validation if isinstance(diagnostic, WardrobeProviderDiagnostic) else diagnostic
    if (record["owner_repairs"] and validation is None
            or validation is not None and validation.attempt == 1 and record["owner_repairs"] != 1):
        raise ValueError("Wardrobe repair selection does not match rejected attempt")
    candidate = None
    if record["candidate_body"] is not None:
        if sha256_digest(record["candidate_body"].encode("utf-8")) != record["candidate_digest"] or not record["owner_attempts"]:
            raise ValueError("Wardrobe candidate digest mismatch")
        candidate = _candidate(record["candidate_kind"], record["candidate_body"], config.wardrobe_input)
    if record["next_activation"] is not None and (record["next_activation"] != _transition(record)
            or (record["candidate_kind"] == "plan" and record["artifact_id"] != pins.planned_artifact_id)):
        raise ValueError("Wardrobe committed result receipt mismatch")
    record.update(pins=pins, config=config, candidate=candidate, diagnostic=diagnostic)
    return record


def find_wardrobe_operation(db: sqlite3.Connection, execution_id: str, request_id: str) -> dict | None:
    _uuid(execution_id)
    row = db.execute("SELECT operation_id FROM wardrobe_operations WHERE execution_id=? AND approval_request_id=?",
                     (execution_id, request_id)).fetchone()
    return read_wardrobe_operation(db, row[0]) if row else None


def _check_start_settings(db: sqlite3.Connection, execution_id: str, config: WardrobeOwnerConfigV1,
                          repair_instruction: str) -> None:
    from backend.openrouter import StoryWardrobeOwnerConfigV2
    start = read_owner_config(db.execute("SELECT owner_config FROM executions WHERE execution_id=?",
                                        (execution_id,)).fetchone()[0])
    if isinstance(start, StoryWardrobeOwnerConfigV2):
        settings = start.wardrobe_settings
        if (any(getattr(config, key) != getattr(settings, key) for key in
                ("adapter_version", "model", "system_prompt", "prompt_digest", "result_schema",
                 "timeout_seconds", "max_tokens", "reasoning_effort"))
                or repair_instruction != settings.repair_instruction):
            raise ValueError("Wardrobe configuration does not match frozen Start settings")


def _check_authority(db: sqlite3.Connection, record: dict) -> None:
    authority, supplied, _ = wardrobe_authority(db, record["execution_id"], record["approval_request_id"])
    pinned = WardrobeAuthorityV1.model_validate({key: getattr(record["pins"], key) for key in WardrobeAuthorityV1.model_fields})
    if authority != pinned or supplied != record["config"].wardrobe_input:
        raise ValueError("Wardrobe prepared authority changed")
    _check_start_settings(db, record["execution_id"], record["config"], record["pins"].repair_instruction)


def prepare_wardrobe_operation(db: sqlite3.Connection, execution_id: str, request_id: str,
                              config_body: str, repair_instruction: str) -> dict:
    config = read_wardrobe_config(config_body)
    repair = prepare_wardrobe_repair(config_body, repair_instruction)
    db.execute("BEGIN IMMEDIATE")
    try:
        authority, supplied, _ = wardrobe_authority(db, execution_id, request_id)
        if supplied != config.wardrobe_input:
            raise ValueError("Wardrobe configuration does not match authoritative input")
        _check_start_settings(db, execution_id, config, repair_instruction)
        operation_id = make_operation_id(execution_id, "wardrobe", authority.activation_id, "generate")
        existing = find_wardrobe_operation(db, execution_id, request_id)
        if existing is not None:
            _check_authority(db, existing)
            if existing["owner_config"] != config_body or existing["pins"].repair_instruction != repair_instruction:
                raise ValueError("Wardrobe operation preparation conflict")
        else:
            pins = PreparedWardrobeInputsV1(**authority.model_dump(mode="python"), schema_version="1",
                wardrobe_config_digest=sha256_digest(config_body.encode("utf-8")), repair_instruction=repair_instruction,
                repair_request_digest=sha256_digest(repair.encode("utf-8")), planned_artifact_id=str(uuid4()))
            body = canonical_json(pins)
            db.execute("INSERT INTO wardrobe_operations (operation_id,execution_id,activation_id,approval_request_id,"
                       "input_digest,prepared_inputs,owner_config,repair_request) VALUES (?,?,?,?,?,?,?,?)",
                       (operation_id, execution_id, authority.activation_id, request_id, sha256_digest(body), body.decode("utf-8"), config_body, repair))
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return read_wardrobe_operation(db, operation_id)


def reserve_wardrobe_attempt(db: sqlite3.Connection, operation_id: str) -> dict:
    db.execute("BEGIN IMMEDIATE")
    try:
        record = read_wardrobe_operation(db, operation_id)
        _check_authority(db, record)
        if record["candidate"] is not None or record["next_activation"] is not None:
            raise ValueError("Wardrobe result already pinned; no further completion allowed")
        if record["owner_attempts"] >= 2:
            if isinstance(record["diagnostic"], WardrobeValidationDiagnostic) and record["diagnostic"].attempt == 2:
                raise WardrobeInvalidOutput(record["diagnostic"].code, "Wardrobe invalid_output; structured repair budget exhausted")
            raise WardrobeAttemptBudgetExhausted("Wardrobe completion attempt budget exhausted")
        updated = db.execute("UPDATE wardrobe_operations SET owner_attempts=owner_attempts+1 "
                             "WHERE operation_id=? AND owner_attempts=? AND owner_attempts<2 AND candidate_body IS NULL",
                             (operation_id, record["owner_attempts"]))
        if updated.rowcount != 1:
            raise ValueError("Wardrobe attempt reservation conflict")
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return read_wardrobe_operation(db, operation_id)


def record_wardrobe_unavailable(db: sqlite3.Connection, reserved: dict, error: WardrobeOwnerUnavailable) -> WardrobeProviderDiagnostic:
    db.execute("BEGIN IMMEDIATE")
    try:
        record = read_wardrobe_operation(db, reserved["operation_id"])
        _check_authority(db, record)
        if (any(record[key] != reserved[key] for key in ("input_digest", "owner_attempts", "owner_repairs", "validation_diagnostic"))
                or record["candidate"] is not None or record["next_activation"] is not None):
            raise ValueError("Wardrobe diagnostic attempt conflict")
        prior = record["diagnostic"]
        validation = prior.previous_validation if isinstance(prior, WardrobeProviderDiagnostic) else prior
        diagnostic = WardrobeProviderDiagnostic(attempt=reserved["owner_attempts"],
            stage="transport" if error.exception_type else "http", status_code=error.status_code,
            exception_type=error.exception_type, previous_validation=validation,
            elapsed_ms=error.elapsed_ms, phase=error.phase)
        updated = db.execute("UPDATE wardrobe_operations SET validation_diagnostic=? WHERE operation_id=? "
                             "AND input_digest=? AND owner_attempts=? AND owner_repairs=? AND validation_diagnostic IS ? "
                             "AND candidate_body IS NULL AND next_activation IS NULL",
                             (canonical_json(diagnostic).decode("utf-8"), reserved["operation_id"], reserved["input_digest"],
                              reserved["owner_attempts"], reserved["owner_repairs"], reserved["validation_diagnostic"]))
        if updated.rowcount != 1:
            raise ValueError("Wardrobe diagnostic attempt conflict")
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return diagnostic


def record_wardrobe_invalid(db: sqlite3.Connection, operation_id: str, attempt: int, error: WardrobeInvalidOutput) -> bool:
    db.execute("BEGIN IMMEDIATE")
    try:
        record = read_wardrobe_operation(db, operation_id)
        _check_authority(db, record)
        if attempt != record["owner_attempts"] or record["candidate"] is not None:
            raise ValueError("Wardrobe rejected attempt conflict")
        diagnostic = WardrobeValidationDiagnostic(attempt=attempt, code=error.code)
        repair = attempt < 2 and record["owner_repairs"] == 0
        db.execute("UPDATE wardrobe_operations SET validation_diagnostic=?,owner_repairs=owner_repairs+? WHERE operation_id=?",
                   (canonical_json(diagnostic).decode("utf-8"), int(repair), operation_id))
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return repair


def pin_wardrobe_candidate(db: sqlite3.Connection, operation_id: str, result: VisualAnchorPlanV1 | OwnerResponseV1) -> None:
    kind = "plan" if isinstance(result, VisualAnchorPlanV1) else "response"
    body = canonical_json(result).decode("utf-8")
    db.execute("BEGIN IMMEDIATE")
    try:
        record = read_wardrobe_operation(db, operation_id)
        _check_authority(db, record)
        _candidate(kind, body, record["config"].wardrobe_input)
        if not record["owner_attempts"]:
            raise ValueError("Wardrobe candidate has no reserved attempt")
        if record["candidate"] is not None:
            if (record["candidate_kind"], record["candidate_body"]) != (kind, body):
                raise ValueError("Wardrobe pending candidate conflict")
        else:
            db.execute("UPDATE wardrobe_operations SET candidate_kind=?,candidate_body=?,candidate_digest=? WHERE operation_id=?",
                       (kind, body, sha256_digest(body.encode("utf-8")), operation_id))
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise


def read_wardrobe_plan(db: sqlite3.Connection, execution_id: str, *, artifact_id: str | None = None) -> tuple[ArtifactRef, VisualAnchorPlanV1]:
    _uuid(execution_id)
    if artifact_id is not None:
        _uuid(artifact_id)
    row = db.execute("SELECT e.project_id,a.artifact_id,a.operation_id,a.digest,a.uri,a.schema_id,a.schema_version,a.produced_by_stage "
                     "FROM artifacts a JOIN executions e ON e.execution_id=a.execution_id "
                     "WHERE a.execution_id=? AND a.artifact_id=COALESCE(?, (SELECT artifact_id FROM execution_bindings "
                     "WHERE execution_id=? AND slot='wardrobe_plan'))", (execution_id, artifact_id, execution_id)).fetchone()
    if row is None or row[5:] != ("visual_anchor_plan", "1", "wardrobe"):
        raise ValueError("Wardrobe plan binding not committed or wrong schema/owner")
    ref = ArtifactRef(project_id=row[0], execution_id=execution_id, artifact_id=row[1], operation_id=row[2],
        digest=row[3], uri=row[4], schema_id=row[5], schema_version=row[6], produced_by_stage=row[7], media_type="application/json")
    path = _destination(db, ref.project_id, ref.artifact_id, ref.digest)
    _check_file(path)
    with path.open("rb") as source:
        body = source.read(MAX_JSON_BYTES + 1)
    if sha256_digest(body) != ref.digest:
        raise ValueError("Committed Wardrobe plan bytes failed integrity check")
    record = read_wardrobe_operation(db, ref.operation_id)
    if (record["execution_id"] != execution_id or record["artifact_id"] != ref.artifact_id
            or record["next_activation"] is None or record["candidate_digest"] != ref.digest
            or record["candidate_body"].encode("utf-8") != body):
        raise ValueError("Wardrobe artifact/result integrity mismatch")
    return ref, record["candidate"]


def replay_wardrobe_operation(db: sqlite3.Connection, record: dict) -> tuple[ArtifactRef | OwnerResponseV1, str]:
    if record["next_activation"] is None:
        raise ValueError("Wardrobe operation is not committed")
    result = (read_wardrobe_plan(db, record["execution_id"], artifact_id=record["artifact_id"])[0]
              if record["candidate_kind"] == "plan" else record["candidate"])
    return result, record["next_activation"]


def commit_wardrobe_operation(db: sqlite3.Connection, operation_id: str) -> tuple[ArtifactRef | OwnerResponseV1, str]:
    record = read_wardrobe_operation(db, operation_id)
    if record["next_activation"] is not None:
        return replay_wardrobe_operation(db, record)
    _check_authority(db, record)
    if record["candidate"] is None:
        raise ValueError("Wardrobe operation has no pinned candidate")
    artifact_id = None
    uri = None
    if record["candidate_kind"] == "plan":
        artifact_id = record["pins"].planned_artifact_id
        ref = record["pins"].story_ref
        uri = f"kinodel://projects/{ref.project_id}/artifacts/{artifact_id}"
        _publish(_destination(db, ref.project_id, artifact_id, record["candidate_digest"]), record["candidate_body"].encode("utf-8"))
    db.execute("BEGIN IMMEDIATE")
    try:
        actual = read_wardrobe_operation(db, operation_id)
        _check_authority(db, actual)
        if actual["candidate_body"] != record["candidate_body"] or actual["next_activation"] is not None:
            raise ValueError("Wardrobe publication finalization conflict")
        if artifact_id is not None:
            db.execute("INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)", (artifact_id, record["execution_id"], operation_id,
                record["candidate_digest"], uri, "visual_anchor_plan", "1", "wardrobe"))
            db.execute("INSERT INTO execution_bindings VALUES (?, 'wardrobe_plan', ?, 1)", (record["execution_id"], artifact_id))
        db.execute("UPDATE wardrobe_operations SET artifact_id=?,next_activation=? WHERE operation_id=? AND next_activation IS NULL",
                   (artifact_id, _transition(record), operation_id))
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return replay_wardrobe_operation(db, read_wardrobe_operation(db, operation_id))
