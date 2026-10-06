"""One bounded HTTP Storytell adapter. Only allowlisted provider failure metadata is recorded."""

import json
import os
from pathlib import Path
import sqlite3
from typing import Annotated, Any, Literal

from pydantic import Field, TypeAdapter, ValidationError, model_validator

from backend import openrouter_client as provider
from backend.openrouter_client import FinishReason, TransportException, credential as _credential, encode
from backend.openrouter_wardrobe import WardrobeStartSettingsV1
from backend.characters import CharacterRef, CharacterV1
from backend.domain import (Digest, DomainModel, MAX_JSON_BYTES, Narrative, OwnerResponseV1, StoryTextInputV1, StoryTextSubjectV1, StoryV1, StoryV2,
                            StorytellResultV1, StorytellResultV2, canonical_json, parse_json_model, sha256_digest,
                            validate_story_for_text_input)
from backend.story_graph import StoryOwnerUnavailable
from backend.story_store import _assert_writable


PROMPT = Path(__file__).resolve().parent.parent / ".agents" / "storytell" / "system.md"

# Only structural names/indices may leave validation; extra keys can contain personal data.
_PATH_FIELDS = "choices|message|content|finish_reason|tool_calls|status|story|explanation|schema_id|schema_version|hook|shots|shot_id|action|narrative_function|subject_ids|state_before|state_after|generated_characters|subject_id|description"
DiagnosticPath = Annotated[str, Field(max_length=192, pattern=rf"^(?:\$|(?:{_PATH_FIELDS}|\*)(?:\[[0-9]{{1,3}}\])?(?:\.(?:{_PATH_FIELDS}|\*)(?:\[[0-9]{{1,3}}\])?)*)$")]


class StoryValidationDiagnostic(DomainModel):
    """Latest rejected attempt only; never model text, error inputs/context or reasoning."""
    attempt: int = Field(ge=1)
    stage: Literal["envelope", "finish", "content", "schema", "constraints", "canonical"]
    code: Literal["invalid_envelope", "incomplete_output", "tool_calls", "non_text_content", "invalid_json",
                  "schema_validation", "result_invariant", "duplicate_shot_ids", "duplicate_subject_ids",
                  "duplicate_generated_ids", "clarification_status", "shot_order", "cast_namespace", "cast_limit",
                  "generated_identity", "undeclared_subject", "constraint_validation", "invalid_canonical"]
    paths: list[DiagnosticPath] = Field(min_length=1, max_length=16)
    finish_reason: FinishReason


class StoryProviderDiagnostic(DomainModel):
    """Latest failed HTTP attempt, not a provider receipt or raw request/response log."""
    attempt: int = Field(ge=1)
    stage: Literal["http", "transport"]
    status_code: int | None = Field(ge=100, le=599)
    exception_type: TransportException | None
    previous_validation: StoryValidationDiagnostic | None = None

    @model_validator(mode="after")
    def consistent_evidence(self):
        if (self.stage == "http" and (self.status_code is None or self.exception_type is not None)
                or self.stage == "transport" and self.exception_type is None
                or self.previous_validation is not None and self.previous_validation.attempt >= self.attempt):
            raise ValueError("Story provider diagnostic evidence mismatch")
        return self


StoryDiagnostic = StoryValidationDiagnostic | StoryProviderDiagnostic
STORY_DIAGNOSTIC = TypeAdapter(StoryDiagnostic)


_REJECTIONS = {
    "Owner result must contain a complete Story or an explanation": ("result_invariant", ["status", "story", "explanation"]),
    "Story shot IDs must be unique": ("duplicate_shot_ids", ["story.shots"]),
    "Story shot subject IDs must be unique": ("duplicate_subject_ids", ["story.shots"]),
    "Generated character IDs must be unique": ("duplicate_generated_ids", ["story.generated_characters"]),
    "Story shot IDs and order must match the prepared keys": ("shot_order", ["story.shots"]),
    "Generated character IDs must be disjoint from selected subjects": ("cast_namespace", ["story.generated_characters"]),
    "Selected and generated cast must contain at most 16 subjects": ("cast_limit", ["story.generated_characters"]),
    "Existing generated character identities must remain declared on revision": ("generated_identity", ["story.generated_characters"]),
    "Every Story subject must be declared in the text input or generated cast": ("undeclared_subject", ["story.shots"]),
    "Every Story subject must be declared in the text input": ("undeclared_subject", ["story.shots"]),
}


def _safe_path(location: tuple) -> str:
    path = ""
    for part in location[:12]:
        if type(part) is int and 0 <= part <= 256 and path:
            path += f"[{part}]"
        else:
            field = part if type(part) is str and part in _PATH_FIELDS.split("|") else "*"
            path += ("." if path else "") + field
    return path or "$"


def _diagnose(error: Exception, attempt: int, stage: str, code: str, paths: list[str], finish: str) -> StoryValidationDiagnostic:
    if isinstance(error, ValidationError):
        stage, code = "schema", "schema_validation"
        errors = error.errors(include_input=False, include_context=False, include_url=False)
        paths = list(dict.fromkeys(_safe_path(item["loc"]) for item in errors))[:16]
        if len(errors) == 1:
            code, paths = _REJECTIONS.get(errors[0]["msg"].removeprefix("Value error, "), (code, paths))
    elif stage == "constraints":
        code, paths = _REJECTIONS.get(str(error), (code, paths))
    return StoryValidationDiagnostic(attempt=attempt, stage=stage, code=code, paths=paths, finish_reason=finish)


def _invalid_output(diagnostic: StoryValidationDiagnostic) -> ValueError:
    return ValueError(f"OpenRouter invalid_output: structured repair budget exhausted; "
                      f"{diagnostic.stage}/{diagnostic.code}; paths={','.join(diagnostic.paths)}; "
                      f"finish_reason={diagnostic.finish_reason}")


class StoryOwnerConfig(DomainModel):
    adapter_version: Literal["1"]
    model: str
    brief: StoryTextInputV1
    system_prompt: Narrative
    prompt_digest: Digest
    result_schema: dict[str, Any]
    clarification_schema: dict[str, Any]
    timeout_seconds: Literal[60]
    max_tokens: Literal[8192]
    max_attempts: Literal[2]
    repair_limit: Literal[1]
    reasoning_effort: Literal["low"]


class SelectedCharacter(DomainModel):
    ref: CharacterRef
    character: CharacterV1

    @model_validator(mode="after")
    def exact_snapshot(self):
        if ((self.ref.subject_id, self.ref.revision) != (self.character.subject_id, self.character.revision)
                or self.ref.digest != sha256_digest(canonical_json(self.character))):
            raise ValueError("Selected character snapshot mismatch")
        return self

    def narrative_subject(self) -> StoryTextSubjectV1:
        bio = self.character.bio
        description = "\n".join(f"{key.title()}: {value}" for key, value in bio.model_dump().items() if value is not None)
        return StoryTextSubjectV1(subject_id=self.ref.subject_id, description=description)


class StoryOwnerConfigV2(StoryOwnerConfig):
    adapter_version: Literal["2"]
    selected_characters: list[SelectedCharacter] = Field(default_factory=list, max_length=16)

    @model_validator(mode="after")
    def selected_narrative(self):
        subjects = [item.narrative_subject() for item in self.selected_characters]
        if subjects and self.brief.subjects[-len(subjects):] != subjects:
            raise ValueError("Selected characters must match the frozen narrative projection")
        return self


class StoryWardrobeOwnerConfigV2(StoryOwnerConfigV2):
    """New starts extend v2 without changing historical canonical config bytes."""

    wardrobe_settings: WardrobeStartSettingsV1

    @model_validator(mode="after")
    def same_model(self):
        if self.wardrobe_settings.model != self.model:
            raise ValueError("Story and Wardrobe Start models must match")
        return self


def read_owner_config(body: str) -> StoryOwnerConfig | StoryOwnerConfigV2:
    if type(body) is not str:
        raise ValueError("Missing frozen Story owner configuration")
    # Canonical encoding always starts with adapter_version; parse still validates the entire body.
    model_type = StoryOwnerConfigV2 if body.startswith('{"adapter_version":"2",') else StoryOwnerConfig
    if model_type is StoryOwnerConfigV2 and "wardrobe_settings" in json.loads(body):
        model_type = StoryWardrobeOwnerConfigV2
    config = parse_json_model(body.encode("utf-8"), model_type)
    if canonical_json(config).decode("utf-8") != body or sha256_digest(config.system_prompt.encode("utf-8")) != config.prompt_digest:
        raise ValueError("Frozen Story owner configuration mismatch")
    return config


def story_availability() -> dict:
    """Local configuration only; model capabilities are checked again on fresh Start."""
    model = os.environ.get("LLM_MODEL", "").strip()
    if not model or len(model) > 256 or any(ord(char) < 33 for char in model):
        return {"configured": False, "model": None, "reason": "Модель не настроена: задайте LLM_MODEL на сервере."}
    try:
        _credential()
    except ValueError:
        return {"configured": False, "model": model, "reason": "OpenRouter не настроен: задайте OPENROUTER_API_KEY на сервере."}
    return {"configured": True, "model": model, "reason": None}


async def pin_story_owner(brief: StoryTextInputV1, selected_characters: list[SelectedCharacter] | None = None) -> str:
    _credential()
    model = os.environ.get("LLM_MODEL", "").strip()
    if not model or len(model) > 256:
        raise ValueError("LLM_MODEL is required in the server environment")
    try:
        selected = await provider.model_metadata(model)
    except (provider.OpenRouterUnavailable, provider.OpenRouterRejected, provider.OpenRouterResponseTooLarge):
        raise ValueError("OpenRouter model metadata unavailable") from None
    provider.require_capabilities(selected, model)
    prompt = PROMPT.read_text(encoding="utf-8")
    config = StoryOwnerConfigV2(adapter_version="2", model=model, brief=brief, system_prompt=prompt,
                              selected_characters=selected_characters or [],
                              prompt_digest=sha256_digest(prompt.encode("utf-8")),
                              result_schema=StorytellResultV2.model_json_schema(),
                              clarification_schema=OwnerResponseV1.model_json_schema(),
                              timeout_seconds=60, max_tokens=8192, max_attempts=2, repair_limit=1, reasoning_effort="low")
    return canonical_json(config).decode("utf-8")


async def produce_live_story(db: sqlite3.Connection, execution_id: str, activation_id: str,
                             prior: StoryV1 | StoryV2 | None, feedback: str | None,
                             action: Literal["revise", "clarify"] | None) -> StoryV1 | StoryV2 | OwnerResponseV1:
    row = db.execute("SELECT owner_config,shot_ids FROM executions WHERE execution_id=?", (execution_id,)).fetchone()
    config = read_owner_config(row[0])
    operation = db.execute("SELECT operation_id,input_digest,prepared_inputs,owner_request,owner_request_digest "
                           "FROM story_operations WHERE execution_id=? AND activation_id=?", (execution_id, activation_id)).fetchone()
    prepared = json.loads(operation[2])
    task = {"action": action or "generate", "brief": config.brief.model_dump(mode="json"),
            "shot_ids": json.loads(row[1]), "previous_story": prior.model_dump(mode="json") if prior else None,
            "feedback": feedback, "discussion": prepared[5] if action else [],
            "context": {"projection_id": f"story-text.v{config.adapter_version}", "owner_input_digest": operation[1],
                        "previous_story_ref": prepared[3] if action else None,
                        "agent_resource": {"resource_id": "storytell/system", "version": config.adapter_version, "digest": config.prompt_digest},
                         "selected_canon": [], "optional_omissions": []}}
    if isinstance(config, StoryOwnerConfigV2):
        task["context"]["selected_canon"] = [{"kind": "character", "ref": item.ref.model_dump(mode="json")}
                                             for item in config.selected_characters]
    clarification = action == "clarify"
    encoded = provider.structured_request(config.model, config.system_prompt, encode(task),
                                          config.clarification_schema if clarification else config.result_schema,
                                          "story_clarification" if clarification else "storytell_result",
                                          config.max_tokens, config.reasoning_effort)
    digest = sha256_digest(encoded.encode("utf-8"))
    if operation[3] is None:
        _assert_writable(db, execution_id)
        db.execute("UPDATE story_operations SET owner_request=?,owner_request_digest=? WHERE operation_id=?",
                   (encoded, digest, operation[0]))
    elif operation[3:] != (encoded, digest):
        raise ValueError("Frozen Story model request mismatch")
    key = _credential()
    while True:
        _assert_writable(db, execution_id)
        attempts, budget, repairs, diagnostic_body = db.execute("SELECT owner_attempts,owner_budget,owner_repairs,owner_validation_diagnostic FROM story_operations WHERE operation_id=?", (operation[0],)).fetchone()
        diagnostic = STORY_DIAGNOSTIC.validate_json(diagnostic_body) if diagnostic_body else None
        validation = diagnostic.previous_validation if isinstance(diagnostic, StoryProviderDiagnostic) else diagnostic
        if attempts >= budget:
            if isinstance(diagnostic, StoryValidationDiagnostic) and diagnostic.attempt == attempts:
                raise _invalid_output(diagnostic)
            raise StoryOwnerUnavailable("Story owner attempt budget exhausted; explicit retry required")
        # Reserve before any HTTP effect; a process crash consumes the attempt.
        db.execute("UPDATE story_operations SET owner_attempts=owner_attempts+1 WHERE operation_id=?", (operation[0],))
        payload = json.loads(encoded)
        if repairs:
            repair = ("The previous response was invalid. Return only complete JSON matching the supplied schema, exact ordered shot_ids and declared subjects. Do not add subjects or change the brief. For generate return ready; for clarify return clarified, without a replacement."
                      if config.adapter_version == "1" else
                       'The previous response was invalid. Return only complete JSON matching the supplied schema and exact ordered shot_ids. For ready, story must be a complete StoryV2 with schema_id="story", schema_version="2" and required generated_characters (use [] when empty); explanation=null. For needs_input or out_of_scope, story=null and explanation is a nonempty explanation; do not invent missing required canon to force ready. Preserve selected subjects and canon in the frozen brief. Declare every invented character in generated_characters with unique IDs disjoint from selected subjects; reference only selected or generated IDs in shots, at most 16 combined. On revise retain all previous generated IDs; descriptions may be edited. For clarify return clarified with a nonempty explanation and no story field.')
            if config.adapter_version == "2" and validation is not None:
                repair += " Rejection diagnostic: " + encode(validation.model_dump(mode="json"))
            payload["messages"].append({"role": "user", "content": repair})
        stage, code, paths, finish = "envelope", "invalid_envelope", ["choices"], "missing"
        response = None
        try:
            response = await provider.http("POST", "chat/completions", config.timeout_seconds,
                                           MAX_JSON_BYTES, encode(payload), key)
            content = provider.parse_completion(response)
            stage, code, paths, finish = "content", "invalid_json", ["choices[0].message.content"], "stop"
            body = content.encode("utf-8")
            if clarification:
                result = parse_json_model(body, OwnerResponseV1)
                stage, code, paths = "schema", "clarification_status", ["status"]
                if result.status != "clarified":
                    raise ValueError("Wrong clarification status")
            else:
                result = parse_json_model(body, StorytellResultV1 if config.adapter_version == "1" else StorytellResultV2)
                if result.story is not None:
                    stage, code, paths = "constraints", "constraint_validation", ["story"]
                    validate_story_for_text_input(result.story, config.brief, task["shot_ids"], prior)
                    stage, code, paths = "canonical", "invalid_canonical", ["story"]
                    canonical_json(result.story)
        except (provider.OpenRouterUnavailable, provider.OpenRouterRejected) as error:
            exception_type = error.exception_type if isinstance(error, provider.OpenRouterUnavailable) else None
            failure = StoryProviderDiagnostic(attempt=attempts + 1, stage="transport" if exception_type else "http",
                status_code=error.status_code, exception_type=exception_type, previous_validation=validation)
            _assert_writable(db, execution_id)
            updated = db.execute("UPDATE story_operations SET owner_validation_diagnostic=? "
                                 "WHERE operation_id=? AND owner_attempts=? AND owner_repairs=?",
                                 (encode(failure.model_dump(mode="json")), operation[0], attempts + 1, repairs))
            if updated.rowcount != 1:
                raise ValueError("Story diagnostic attempt conflict") from None
            if isinstance(error, provider.OpenRouterUnavailable):
                raise StoryOwnerUnavailable("Story owner unavailable") from None
            raise ValueError(str(error)) from None
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as error:
            # Other pre-response failures are not malformed model output.
            if response is None and not isinstance(error, provider.OpenRouterResponseTooLarge):
                raise
            if isinstance(error, provider.CompletionRejected):
                stage, code, paths, finish = error.stage, error.code, error.paths, error.finish
            diagnostic = _diagnose(error, attempts + 1, stage, code, paths, finish)
            repair_allowed = repairs < config.repair_limit and attempts + 1 < budget
            _assert_writable(db, execution_id)
            # Diagnostic and repair reservation commit together, including before restart.
            updated = db.execute("UPDATE story_operations SET owner_validation_diagnostic=?,owner_repairs=owner_repairs+? "
                                 "WHERE operation_id=? AND owner_attempts=? AND owner_repairs=?",
                                 (encode(diagnostic.model_dump(mode="json")), int(repair_allowed), operation[0], attempts + 1, repairs))
            if updated.rowcount != 1:
                raise ValueError("Story diagnostic attempt conflict") from None
            if not repair_allowed:
                raise _invalid_output(diagnostic) from None
            continue
        if clarification:
            return result
        if result.story is not None:
            return result.story
        if action != "revise":
            # A valid contradiction/missing-input explanation is not a malformed draft to repair away.
            raise ValueError(f"Storytell {result.status}: {result.explanation}")
        return OwnerResponseV1(status=result.status, explanation=result.explanation)
