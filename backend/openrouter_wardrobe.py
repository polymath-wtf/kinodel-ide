"""Frozen Wardrobe requests and one bounded completion; no storage or attempt ownership."""

from __future__ import annotations

import base64
from io import BytesIO
import json
import os
from pathlib import Path
from typing import Annotated, Any, Literal
import warnings

from PIL import Image
from pydantic import Field, model_validator

from backend import openrouter_client as provider
from backend.characters import MAX_IMAGE_BYTES, MAX_IMAGE_PIXELS, MAX_IMAGE_SIDE
from backend.domain import (DomainModel, MAX_JSON_BYTES, Narrative, OwnerResponseV1,
                            _reject_float, _unique_object, canonical_json, parse_json_model, sha256_digest)
from backend.openrouter_client import OpenRouterModelMetadataV1 as WardrobeModelMetadataV1, credential as _credential, encode
from backend.wardrobe import (ExactDigest, VisualAnchorPlanV2, WardrobeImageEvidenceV1,
                              WardrobeInputV2, WardrobeResultV2, resolve_wardrobe_draft)


PROMPT = Path(__file__).resolve().parent.parent / ".agents" / "wardrobe" / "system.md"
_IMAGE_FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
MAX_WARDROBE_REQUEST_BYTES = 16 * 1024 * 1024
MAX_WARDROBE_CONFIG_BYTES = 20 * 1024 * 1024
REPAIR_INSTRUCTION = (
    "The previous response was invalid. Return complete JSON matching the supplied schema. "
    "Use only the frozen declared/generated subjects. A ready plan must contain complete direction and unique ordered "
    "batch_prompt units. hero-face/location use txt2img with no render references; hero-sheet uses img2img with "
    "exactly two earlier batch_unit references in portrait/background order with matching subjects/roles. "
    "workflow is a semantic mode, never a provider filename. Evidence is not a render binding. "
    "For needs_input/out_of_scope return plan=null and a nonempty explanation; do not invent missing canon."
)


class WardrobeOwnerUnavailable(RuntimeError):
    """Transient transport failure; any retry requires a new durable caller reservation."""

    def __init__(self, message="Wardrobe OpenRouter unavailable", *, status_code: int | None = None,
                  exception_type: provider.TransportException | None = "OpenRouterUnavailable",
                  elapsed_ms: int | None = None, phase: provider.TransportPhase | None = None):
        self.status_code, self.exception_type = status_code, exception_type
        self.elapsed_ms, self.phase = elapsed_ms, phase
        super().__init__(message)


class WardrobeInvalidOutput(ValueError):
    """Safe model-output rejection, distinct from configuration and HTTP rejection."""

    def __init__(self, code: str = "invalid_result", message: str = "Wardrobe OpenRouter invalid_output"):
        self.code = code
        super().__init__(message)


class WardrobeInputSizeDiagnostic(DomainModel):
    """A reproducible frozen-input bound, not a historical provider/attempt record."""

    basis: Literal["frozen_input_size"] = "frozen_input_size"
    stage: Literal["input"] = "input"
    code: Literal["evidence_size_limit"] = "evidence_size_limit"
    serialized_evidence_bytes: int = Field(gt=MAX_WARDROBE_REQUEST_BYTES)
    limit_bytes: int = Field(default=MAX_WARDROBE_REQUEST_BYTES, ge=MAX_WARDROBE_REQUEST_BYTES, le=MAX_WARDROBE_REQUEST_BYTES)


class WardrobeInputSizeLimit(ValueError):
    def __init__(self, diagnostic: WardrobeInputSizeDiagnostic):
        self.diagnostic = diagnostic
        super().__init__(f"Wardrobe serialized evidence requires {diagnostic.serialized_evidence_bytes} bytes; "
                         f"limit is {diagnostic.limit_bytes} bytes")


def wardrobe_input_size_diagnostic(supplied: WardrobeInputV2) -> WardrobeInputSizeDiagnostic | None:
    """Exact content JSON size from frozen pins, without reading images or encoding base64."""
    size = len(encode([{"type": "text", "text": canonical_json(supplied).decode("utf-8")}]).encode("utf-8"))
    for image in supplied.image_evidence:
        label = {"type": "text", "text": canonical_json(image).decode("utf-8")}
        picture = {"type": "image_url", "image_url": {"url": f"data:{image.ref.mime_type};base64,"}}
        size += len(encode(label).encode("utf-8")) + len(encode(picture).encode("utf-8")) + 4 * ((image.ref.byte_length + 2) // 3) + 2
    return WardrobeInputSizeDiagnostic(serialized_evidence_bytes=size) if size > MAX_WARDROBE_REQUEST_BYTES else None


def _image_bytes(evidence: WardrobeImageEvidenceV1, body: bytes) -> None:
    """Verify original bytes; never orient, resize, re-encode or dereference a logical ID."""
    ref = evidence.ref
    if (type(body) is not bytes or not 0 < len(body) <= MAX_IMAGE_BYTES
            or len(body) != ref.byte_length or sha256_digest(body) != ref.digest):
        raise ValueError("Wardrobe image bytes do not match the declared pin or limit")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(body)) as image:
                if (image.format != _IMAGE_FORMATS[ref.mime_type]
                        or image.size != (ref.width, ref.height)
                        or max(image.size) > MAX_IMAGE_SIDE
                        or image.width * image.height > MAX_IMAGE_PIXELS
                        or getattr(image, "n_frames", 1) != 1):
                    raise ValueError("Wardrobe image MIME, dimensions or frame limit mismatch")
                image.verify()
            with Image.open(BytesIO(body)) as image:
                image.load()  # Container verification alone does not decode the pixels.
    except (OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError("Wardrobe image decoding failed") from None


def _content(supplied: WardrobeInputV2, images: dict[str, bytes]) -> list[dict]:
    if type(images) is not dict or set(images) != {image.alias for image in supplied.image_evidence}:
        raise ValueError("Wardrobe image aliases must match all declared evidence exactly")
    diagnostic = wardrobe_input_size_diagnostic(supplied)
    if diagnostic is not None:
        raise WardrobeInputSizeLimit(diagnostic)
    for image in supplied.image_evidence:
        _image_bytes(image, images[image.alias])
    content: list[dict] = [{"type": "text", "text": canonical_json(supplied).decode("utf-8")}]
    for image in supplied.image_evidence:
        body = images[image.alias]
        label = {"type": "text", "text": canonical_json(image).decode("utf-8")}
        prefix = f"data:{image.ref.mime_type};base64,"
        picture = {"type": "image_url", "image_url": {"url": prefix}}
        picture["image_url"]["url"] += base64.b64encode(body).decode("ascii")
        content.extend([label, picture])
    return content


def _request(model: str, prompt: str, content: list[dict], schema: dict,
             max_tokens: int, reasoning_effort: str) -> str:
    return provider.structured_request(model, prompt, content, schema, "wardrobe_result", max_tokens, reasoning_effort,
                                       request_limit=MAX_WARDROBE_REQUEST_BYTES)


class WardrobeStartSettingsV2(DomainModel):
    """Static secret-free settings; generated input and capabilities are checked later."""

    adapter_version: Literal["2"] = "2"
    model: Annotated[str, Field(min_length=1, max_length=256)]
    system_prompt: Narrative
    prompt_digest: ExactDigest
    result_schema: dict[str, Any]
    timeout_seconds: Literal[180] = 180
    max_tokens: Literal[8192] = 8192
    reasoning_effort: Literal["low"] = "low"
    repair_instruction: Annotated[str, Field(min_length=1, max_length=4096)]

    @model_validator(mode="after")
    def consistent_settings(self):
        provider.validate_model_name(self.model)
        if (sha256_digest(self.system_prompt.encode("utf-8")) != self.prompt_digest
                or self.result_schema != WardrobeResultV2.model_json_schema()
                or not self.repair_instruction.strip()):
            raise ValueError("Wardrobe frozen Start settings mismatch")
        return self


def pin_wardrobe_settings(model: str) -> WardrobeStartSettingsV2:
    provider.validate_model_name(model)
    try:
        prompt = PROMPT.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise ValueError("Wardrobe system prompt unavailable") from None
    try:
        return WardrobeStartSettingsV2(model=model, system_prompt=prompt,
            prompt_digest=sha256_digest(prompt.encode("utf-8")), result_schema=WardrobeResultV2.model_json_schema(),
            repair_instruction=REPAIR_INSTRUCTION)
    except (ValueError, TypeError, RecursionError):
        raise ValueError("Wardrobe frozen Start settings are invalid or exceed size limit") from None


class WardrobeOwnerConfigV2(DomainModel):
    adapter_version: Literal["2"]
    model: Annotated[str, Field(min_length=1, max_length=256)]
    wardrobe_input: WardrobeInputV2
    input_digest: ExactDigest
    system_prompt: Narrative
    prompt_digest: ExactDigest
    result_schema: dict[str, Any]
    result_schema_digest: ExactDigest
    model_metadata: WardrobeModelMetadataV1
    model_metadata_digest: ExactDigest
    timeout_seconds: Literal[180]
    max_tokens: Literal[8192]
    reasoning_effort: Literal["low"]
    base_request: Annotated[str, Field(min_length=1, max_length=MAX_WARDROBE_REQUEST_BYTES)]
    base_request_digest: ExactDigest

    @model_validator(mode="after")
    def consistent_request(self):
        try:
            if len(self.base_request.encode("utf-8")) > MAX_WARDROBE_REQUEST_BYTES:
                raise ValueError("Request exceeds size limit")
            provider.require_capabilities(self.model_metadata, self.model, bool(self.wardrobe_input.image_evidence))
            for body, digest in (
                (canonical_json(self.wardrobe_input), self.input_digest),
                (self.system_prompt.encode("utf-8"), self.prompt_digest),
                (encode(self.result_schema).encode("utf-8"), self.result_schema_digest),
                (canonical_json(self.model_metadata), self.model_metadata_digest),
                (self.base_request.encode("utf-8"), self.base_request_digest),
            ):
                if sha256_digest(body) != digest:
                    raise ValueError("Pin mismatch")
            if self.result_schema != WardrobeResultV2.model_json_schema():
                raise ValueError("Wrong Wardrobe response schema")
            request = json.loads(self.base_request, object_pairs_hook=_unique_object, parse_constant=_reject_float)
            content = request["messages"][1]["content"]
            if type(content) is not list or len(content) != 1 + 2 * len(self.wardrobe_input.image_evidence):
                raise ValueError("Image binding count mismatch")
            images = {}
            for index, image in enumerate(self.wardrobe_input.image_evidence):
                url = content[2 + 2 * index]["image_url"]["url"]
                prefix = f"data:{image.ref.mime_type};base64,"
                if type(url) is not str or not url.startswith(prefix):
                    raise ValueError("Invalid image data URL")
                images[image.alias] = base64.b64decode(url[len(prefix):], validate=True)
            expected = _request(self.model, self.system_prompt, _content(self.wardrobe_input, images),
                                self.result_schema, self.max_tokens, self.reasoning_effort)
            if self.base_request != expected:
                raise ValueError("Request mismatch")
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError):
            raise ValueError("Wardrobe frozen configuration mismatch") from None
        return self


def read_wardrobe_config(body: str) -> WardrobeOwnerConfigV2:
    """Pure canonical read/revalidation; does not consult environment, files or catalog."""
    try:
        if type(body) is not str:
            raise ValueError("Missing configuration")
        config = parse_json_model(body.encode("utf-8"), WardrobeOwnerConfigV2, max_bytes=MAX_WARDROBE_CONFIG_BYTES)
        if canonical_json(config, max_bytes=MAX_WARDROBE_CONFIG_BYTES).decode("utf-8") != body:
            raise ValueError("Noncanonical configuration")
        return config
    except (ValueError, TypeError, RecursionError):
        raise ValueError("Wardrobe frozen configuration mismatch") from None


def prepare_wardrobe_repair(config: str, instruction: str) -> str:
    """Pure request construction; the operation freezes instruction AND bytes before POST."""
    prepared = read_wardrobe_config(config)
    if type(instruction) is not str or not instruction.strip() or len(instruction) > 4096:
        raise ValueError("Invalid Wardrobe repair instruction")
    instruction.encode("utf-8")
    request = json.loads(prepared.base_request)
    request["messages"].append({"role": "user", "content": instruction})
    body = encode(request)
    if len(body.encode("utf-8")) > MAX_WARDROBE_REQUEST_BYTES:
        raise ValueError("Wardrobe repair request exceeds size limit")
    return body


async def _http(method: str, route: str, seconds: int, limit: int,
                request: str | None = None, key: str | None = None) -> bytes:
    try:
        return await provider.http(method, route, seconds, limit, request, key, request_limit=MAX_WARDROBE_REQUEST_BYTES)
    except provider.OpenRouterUnavailable as error:
        raise WardrobeOwnerUnavailable(status_code=error.status_code, exception_type=error.exception_type,
                                      elapsed_ms=error.elapsed_ms, phase=error.phase) from None
    except provider.OpenRouterRejected:
        raise ValueError("Wardrobe OpenRouter request rejected; check server configuration") from None
    except provider.OpenRouterResponseTooLarge:
        if method == "POST":
            raise WardrobeInvalidOutput("response_limit", "Wardrobe OpenRouter response exceeds size limit") from None
        raise ValueError("Wardrobe OpenRouter response exceeds size limit") from None


async def prepare_wardrobe_request(supplied: WardrobeInputV2 | dict,
                                   evidence_bytes: dict[str, bytes], *,
                                   settings: WardrobeStartSettingsV2 | None = None) -> str:
    """Fresh preparation GETs public metadata, validates bytes and freezes a secret-free request."""
    # Validate all caller-owned content before consulting the provider.
    try:
        prepared_input: WardrobeInputV2 = WardrobeInputV2.model_validate(supplied)
        content = _content(prepared_input, evidence_bytes)
    except WardrobeInputSizeLimit:
        raise  # Preserve the typed, numeric-only cause rather than the aggregate rejection.
    except (ValueError, TypeError, KeyError):
        raise ValueError("Wardrobe input or image evidence is invalid or exceeds size limit") from None
    _credential()
    # Standalone callers may resolve static settings here; starts supply their frozen settings.
    settings = (pin_wardrobe_settings(os.environ.get("LLM_MODEL", "").strip()) if settings is None
                else WardrobeStartSettingsV2.model_validate(settings))
    model, prompt, schema = settings.model, settings.system_prompt, settings.result_schema
    try:
        request = _request(model, prompt, content, schema, settings.max_tokens, settings.reasoning_effort)
    except (ValueError, TypeError, RecursionError):
        raise ValueError("Wardrobe frozen request is invalid or exceeds size limit") from None
    try:
        metadata = await provider.model_metadata(model)
    except provider.OpenRouterUnavailable as error:
        raise WardrobeOwnerUnavailable(status_code=error.status_code, exception_type=error.exception_type,
                                      elapsed_ms=error.elapsed_ms, phase=error.phase) from None
    except provider.OpenRouterRejected:
        raise ValueError("Wardrobe OpenRouter request rejected; check server configuration") from None
    except provider.OpenRouterResponseTooLarge:
        raise ValueError("Wardrobe OpenRouter response exceeds size limit") from None
    provider.require_capabilities(metadata, model, bool(prepared_input.image_evidence))
    try:
        config = WardrobeOwnerConfigV2(
            adapter_version="2", model=model, wardrobe_input=prepared_input, input_digest=sha256_digest(canonical_json(prepared_input)),
            system_prompt=prompt, prompt_digest=sha256_digest(prompt.encode("utf-8")),
            result_schema=schema, result_schema_digest=sha256_digest(encode(schema).encode("utf-8")),
            model_metadata=metadata, model_metadata_digest=sha256_digest(canonical_json(metadata)),
            timeout_seconds=settings.timeout_seconds, max_tokens=settings.max_tokens, reasoning_effort=settings.reasoning_effort,
            base_request=request, base_request_digest=sha256_digest(request.encode("utf-8")))
        return canonical_json(config, max_bytes=MAX_WARDROBE_CONFIG_BYTES).decode("utf-8")
    except (ValueError, TypeError, RecursionError):
        raise ValueError("Wardrobe frozen request is invalid or exceeds size limit") from None


async def complete_wardrobe(config: WardrobeOwnerConfigV2 | str, *,
                           repair_instruction: str | None = None) -> VisualAnchorPlanV2 | OwnerResponseV1:
    """ONE POST. Caller must persist/reserve attempt first, then commit/replay its typed result.

    No automatic repair/retry, durable budgets, authorization, approval or immutable storage here.
    """
    if isinstance(config, WardrobeOwnerConfigV2):
        try:
            config = canonical_json(config, max_bytes=MAX_WARDROBE_CONFIG_BYTES).decode("utf-8")
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ValueError("Wardrobe frozen configuration mismatch") from None
    prepared = read_wardrobe_config(config)
    request = prepared.base_request if repair_instruction is None else prepare_wardrobe_repair(config, repair_instruction)
    body = await _http("POST", "chat/completions", prepared.timeout_seconds, MAX_JSON_BYTES,
                       request, _credential())
    try:
        content = provider.parse_completion(body, strict_envelope=True)
        result = parse_json_model(content.encode("utf-8"), WardrobeResultV2)
        if result.status == "ready":
            assert result.plan is not None  # The result validator enforces ready's complete-draft invariant.
            return resolve_wardrobe_draft(result.plan, prepared.wardrobe_input)
        return OwnerResponseV1(status=result.status, explanation=result.explanation)
    except provider.CompletionRejected as error:
        raise WardrobeInvalidOutput(error.code) from None
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError):
        raise WardrobeInvalidOutput() from None
