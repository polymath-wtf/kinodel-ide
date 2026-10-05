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
from backend.wardrobe import (ExactDigest, VisualAnchorPlanV1, WardrobeImageEvidenceV1,
                              WardrobeInputV1, WardrobeResultV1, resolve_wardrobe_draft)


PROMPT = Path(__file__).resolve().parent.parent / ".agents" / "wardrobe" / "system.md"
_IMAGE_FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
REPAIR_INSTRUCTION = (
    "The previous response was invalid. Return complete JSON matching the supplied schema. "
    "Use only the frozen declared/generated subjects. A ready plan must contain complete direction and unique ordered "
    "anchor units. Portrait/background have no render references; character_sheet has ordered earlier portrait and "
    "background references with matching subjects/roles. Evidence is not a render binding. "
    "For needs_input/out_of_scope return plan=null and a nonempty explanation; do not invent missing canon."
)


class WardrobeOwnerUnavailable(RuntimeError):
    """Transient transport failure; any retry requires a new durable caller reservation."""


class WardrobeInvalidOutput(ValueError):
    """Safe model-output rejection, distinct from configuration and HTTP rejection."""

    def __init__(self, code: str = "invalid_result", message: str = "Wardrobe OpenRouter invalid_output"):
        self.code = code
        super().__init__(message)


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


def _content(supplied: WardrobeInputV1, images: dict[str, bytes]) -> list[dict]:
    if type(images) is not dict or set(images) != {image.alias for image in supplied.image_evidence}:
        raise ValueError("Wardrobe image aliases must match all declared evidence exactly")
    content: list[dict] = [{"type": "text", "text": canonical_json(supplied).decode("utf-8")}]
    size = len(encode(content).encode("utf-8"))
    for image in supplied.image_evidence:
        body = images[image.alias]
        _image_bytes(image, body)
        label = {"type": "text", "text": canonical_json(image).decode("utf-8")}
        prefix = f"data:{image.ref.mime_type};base64,"
        picture = {"type": "image_url", "image_url": {"url": prefix}}
        size += len(encode(label).encode("utf-8")) + len(encode(picture).encode("utf-8")) + 4 * ((len(body) + 2) // 3) + 2
        if size > MAX_JSON_BYTES:
            raise ValueError("Wardrobe serialized evidence exceeds size limit")
        picture["image_url"]["url"] += base64.b64encode(body).decode("ascii")
        content.extend([label, picture])
    return content


def _request(model: str, prompt: str, content: list[dict], schema: dict,
             max_tokens: int, reasoning_effort: str) -> str:
    return provider.structured_request(model, prompt, content, schema, "wardrobe_result", max_tokens, reasoning_effort)


class WardrobeOwnerConfigV1(DomainModel):
    adapter_version: Literal["1"]
    model: Annotated[str, Field(min_length=1, max_length=256)]
    wardrobe_input: WardrobeInputV1
    input_digest: ExactDigest
    system_prompt: Narrative
    prompt_digest: ExactDigest
    result_schema: dict[str, Any]
    result_schema_digest: ExactDigest
    model_metadata: WardrobeModelMetadataV1
    model_metadata_digest: ExactDigest
    timeout_seconds: Literal[60]
    max_tokens: Literal[8192]
    reasoning_effort: Literal["low"]
    base_request: Annotated[str, Field(min_length=1, max_length=MAX_JSON_BYTES)]
    base_request_digest: ExactDigest

    @model_validator(mode="after")
    def consistent_request(self):
        try:
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
            if self.result_schema != WardrobeResultV1.model_json_schema():
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


def read_wardrobe_config(body: str) -> WardrobeOwnerConfigV1:
    """Pure canonical read/revalidation; does not consult environment, files or catalog."""
    try:
        if type(body) is not str:
            raise ValueError("Missing configuration")
        config = parse_json_model(body.encode("utf-8"), WardrobeOwnerConfigV1)
        if canonical_json(config).decode("utf-8") != body:
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
    if len(body.encode("utf-8")) > MAX_JSON_BYTES:
        raise ValueError("Wardrobe repair request exceeds size limit")
    return body


async def _http(method: str, route: str, seconds: int, limit: int,
                request: str | None = None, key: str | None = None) -> bytes:
    try:
        return await provider.http(method, route, seconds, limit, request, key)
    except provider.OpenRouterUnavailable:
        raise WardrobeOwnerUnavailable("Wardrobe OpenRouter unavailable") from None
    except provider.OpenRouterRejected:
        raise ValueError("Wardrobe OpenRouter request rejected; check server configuration") from None
    except provider.OpenRouterResponseTooLarge:
        if method == "POST":
            raise WardrobeInvalidOutput("response_limit", "Wardrobe OpenRouter response exceeds size limit") from None
        raise ValueError("Wardrobe OpenRouter response exceeds size limit") from None


async def prepare_wardrobe_request(supplied: WardrobeInputV1 | dict,
                                   evidence_bytes: dict[str, bytes]) -> str:
    """Fresh preparation GETs public metadata, validates bytes and freezes a secret-free request."""
    # Validate all caller-owned content before consulting the provider.
    try:
        prepared_input: WardrobeInputV1 = WardrobeInputV1.model_validate(supplied)
        content = _content(prepared_input, evidence_bytes)
    except (ValueError, TypeError, KeyError):
        raise ValueError("Wardrobe input or image evidence is invalid or exceeds size limit") from None
    _credential()
    # Same setting as Story; never substitute a model or introduce a Wardrobe-specific key.
    model = os.environ.get("LLM_MODEL", "").strip()
    provider.validate_model_name(model)
    try:
        metadata = await provider.model_metadata(model)
    except provider.OpenRouterUnavailable:
        raise WardrobeOwnerUnavailable("Wardrobe OpenRouter unavailable") from None
    except provider.OpenRouterRejected:
        raise ValueError("Wardrobe OpenRouter request rejected; check server configuration") from None
    except provider.OpenRouterResponseTooLarge:
        raise ValueError("Wardrobe OpenRouter response exceeds size limit") from None
    provider.require_capabilities(metadata, model, bool(prepared_input.image_evidence))
    try:
        prompt = PROMPT.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise ValueError("Wardrobe system prompt unavailable") from None
    try:
        schema = WardrobeResultV1.model_json_schema()
        request = _request(model, prompt, content, schema, 8192, "low")
        config = WardrobeOwnerConfigV1(
            adapter_version="1", model=model, wardrobe_input=prepared_input, input_digest=sha256_digest(canonical_json(prepared_input)),
            system_prompt=prompt, prompt_digest=sha256_digest(prompt.encode("utf-8")),
            result_schema=schema, result_schema_digest=sha256_digest(encode(schema).encode("utf-8")),
            model_metadata=metadata, model_metadata_digest=sha256_digest(canonical_json(metadata)),
            timeout_seconds=60, max_tokens=8192, reasoning_effort="low",
            base_request=request, base_request_digest=sha256_digest(request.encode("utf-8")))
        return canonical_json(config).decode("utf-8")
    except (ValueError, TypeError, RecursionError):
        raise ValueError("Wardrobe frozen request is invalid or exceeds size limit") from None


async def complete_wardrobe(config: WardrobeOwnerConfigV1 | str, *,
                           repair_instruction: str | None = None) -> VisualAnchorPlanV1 | OwnerResponseV1:
    """ONE POST. Caller must persist/reserve attempt first, then commit/replay its typed result.

    No automatic repair/retry, durable budgets, authorization, approval or immutable storage here.
    """
    if isinstance(config, WardrobeOwnerConfigV1):
        try:
            config = canonical_json(config).decode("utf-8")
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ValueError("Wardrobe frozen configuration mismatch") from None
    prepared = read_wardrobe_config(config)
    request = prepared.base_request if repair_instruction is None else prepare_wardrobe_repair(config, repair_instruction)
    body = await _http("POST", "chat/completions", prepared.timeout_seconds, MAX_JSON_BYTES,
                       request, _credential())
    try:
        content = provider.parse_completion(body, strict_envelope=True)
        result = parse_json_model(content.encode("utf-8"), WardrobeResultV1)
        if result.status == "ready":
            assert result.plan is not None  # The result validator enforces ready's complete-draft invariant.
            return resolve_wardrobe_draft(result.plan, prepared.wardrobe_input)
        return OwnerResponseV1(status=result.status, explanation=result.explanation)
    except provider.CompletionRejected as error:
        raise WardrobeInvalidOutput(error.code) from None
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError):
        raise WardrobeInvalidOutput() from None
