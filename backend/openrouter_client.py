"""OpenRouter wire helpers only; domains, durable attempts and repairs belong to callers."""

import asyncio
import json
import os
from time import monotonic
from typing import Annotated, Any, Literal, cast, get_args

import httpx
from pydantic import Field

from backend.domain import DomainModel, MAX_JSON_BYTES, Text, _reject_float, _unique_object


BASE_URL = "https://openrouter.ai/api/v1"
FinishReason = Literal["stop", "length", "content_filter", "tool_calls", "function_call", "error", "missing", "unknown", "invalid_type"]
TransportPhase = Literal["connection", "response_read", "client_cleanup"]
TransportException = Literal["TimeoutError", "ConnectTimeout", "ReadTimeout", "WriteTimeout", "PoolTimeout",
                             "ConnectError", "ReadError", "WriteError", "CloseError", "LocalProtocolError",
                             "RemoteProtocolError", "ProxyError", "UnsupportedProtocol", "DecodingError",
                             "TooManyRedirects", "HTTPError", "OpenRouterUnavailable"]


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def credential() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key or any(ord(char) < 33 or ord(char) > 126 for char in key):
        raise ValueError("OPENROUTER_API_KEY is missing or invalid in the server environment")
    return key


class OpenRouterUnavailable(RuntimeError):
    """Transport or transient HTTP failure, without provider body or secret data."""

    def __init__(self, message="OpenRouter unavailable", *, status_code: int | None = None,
                 exception_type: TransportException | None = "OpenRouterUnavailable",
                 elapsed_ms: int | None = None, phase: TransportPhase | None = None):
        self.status_code, self.exception_type = status_code, exception_type
        self.elapsed_ms, self.phase = elapsed_ms, phase
        super().__init__(message)


class OpenRouterRejected(ValueError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"OpenRouter request rejected (HTTP {status_code}); check server configuration")


class OpenRouterResponseTooLarge(ValueError):
    pass


async def http(method: str, route: str, seconds: int, limit: int,
               request: str | None = None, key: str | None = None, *, request_limit: int = MAX_JSON_BYTES) -> bytes:
    content = request.encode("utf-8") if request is not None else None
    if content is not None and len(content) > request_limit:
        raise ValueError("OpenRouter serialized request exceeds size limit")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"} if key else {}
    status_code = None
    started = monotonic()
    phase: TransportPhase = "connection"
    failed_phase: TransportPhase | None = None
    try:
        async with asyncio.timeout(seconds), httpx.AsyncClient(
                timeout=seconds, follow_redirects=False, trust_env=False) as client:
            # HTTPX defaults to zero transport retries; stream reads share the total deadline.
            async with client.stream(method, f"{BASE_URL}/{route}", content=content, headers=headers) as response:
                phase = "response_read"
                status_code = response.status_code
                try:
                    if response.status_code in (408, 429) or response.status_code >= 500:
                        raise OpenRouterUnavailable(status_code=status_code, exception_type=None)
                    if response.status_code != 200:
                        raise OpenRouterRejected(response.status_code)
                    body = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        if len(body) + len(chunk) > limit:
                            raise OpenRouterResponseTooLarge("OpenRouter response exceeds size limit")
                        body.extend(chunk)
                except BaseException:
                    failed_phase = phase
                    raise
                finally:
                    phase = "client_cleanup"
            # Includes response and client context cleanup in the total deadline.
        return bytes(body)
    except OpenRouterUnavailable as error:
        error.elapsed_ms = max(0, int((monotonic() - started) * 1000))
        error.phase = failed_phase or phase
        raise
    except (httpx.HTTPError, TimeoutError) as error:
        name = type(error).__name__
        # Never persist arbitrary exception names/messages, URLs, headers or partial bodies.
        name = name if name in get_args(TransportException) else "HTTPError"
        raise OpenRouterUnavailable(status_code=status_code, exception_type=cast(TransportException, name),
            elapsed_ms=max(0, int((monotonic() - started) * 1000)), phase=failed_phase or phase) from None


class OpenRouterModelMetadataV1(DomainModel):
    """Only the exact model's relevant advertised capabilities, not live verification."""

    id: Annotated[str, Field(min_length=1, max_length=256)]
    supported_parameters: list[Text] = Field(max_length=256)
    input_modalities: list[Text] = Field(max_length=256)
    supported_efforts: list[Text] | None = Field(max_length=256)


def validate_model_name(model: str) -> None:
    if not model or len(model) > 256 or any(ord(char) < 33 for char in model):
        raise ValueError("LLM_MODEL is required and must be valid in the server environment")
    try:
        model.encode("utf-8")
    except UnicodeError:
        raise ValueError("LLM_MODEL is invalid in the server environment") from None


async def model_metadata(model: str) -> OpenRouterModelMetadataV1:
    """Fresh public catalog lookup; never substitute or freeze the whole catalog."""
    body = await http("GET", "models", 15, 16 * MAX_JSON_BYTES)
    try:
        catalog = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_float)["data"]
        if type(catalog) is not list or any(type(item) is not dict for item in catalog):
            raise ValueError("Malformed catalog")
        matching = [item for item in catalog if item.get("id") == model]
        if len(matching) > 1:
            raise ValueError("Ambiguous model")
        if matching:
            selected = matching[0]
            return OpenRouterModelMetadataV1(
                id=selected["id"], supported_parameters=selected.get("supported_parameters", []),
                input_modalities=selected.get("architecture", {}).get("input_modalities", []),
                supported_efforts=selected.get("reasoning", {}).get("supported_efforts"))
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise ValueError("OpenRouter model metadata unavailable") from None
    raise ValueError("Requested OpenRouter model is unavailable; no model substitution")


def require_capabilities(metadata: OpenRouterModelMetadataV1, model: str, visual: bool = False) -> None:
    validate_model_name(model)
    if metadata.id != model:
        raise ValueError("Requested OpenRouter model is unavailable; no model substitution")
    if not {"response_format", "structured_outputs"}.issubset(metadata.supported_parameters):
        raise ValueError("Requested OpenRouter model does not advertise structured outputs")
    if metadata.supported_efforts is not None and "low" not in metadata.supported_efforts:
        raise ValueError("Requested OpenRouter model does not support the bounded low reasoning profile")
    if visual and "image" not in metadata.input_modalities:
        raise ValueError("Requested OpenRouter model does not advertise image input")


def structured_request(model: str, prompt: str, content: str | list[dict], schema: dict,
                       name: str, max_tokens: int, reasoning_effort: str, *, request_limit: int = MAX_JSON_BYTES) -> str:
    body = encode({"model": model, "stream": False, "max_tokens": max_tokens,
                   "provider": {"require_parameters": True}, "reasoning": {"effort": reasoning_effort},
                   "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": content}],
                   "response_format": {"type": "json_schema", "json_schema": {
                       "name": name, "strict": True, "schema": schema}}})
    if len(body.encode("utf-8")) > request_limit:
        raise ValueError("OpenRouter serialized request exceeds size limit")
    return body


class CompletionRejected(ValueError):
    """Structural rejection only; no content, arbitrary keys, reasoning or provider errors."""

    def __init__(self, stage: str, code: str, paths: list[str], finish: FinishReason):
        self.stage, self.code, self.paths, self.finish = stage, code, paths, finish
        super().__init__("OpenRouter invalid_output")


def parse_completion(body: bytes, *, strict_envelope: bool = False) -> str:
    """Validate the completion envelope, leaving JSON/domain validation to the stage."""
    stage, code, paths, finish = "envelope", "invalid_envelope", ["choices"], "missing"
    try:
        options = {"object_pairs_hook": _unique_object, "parse_constant": _reject_float} if strict_envelope else {}
        envelope = json.loads(body.decode("utf-8") if strict_envelope else body, **options)
        choices = envelope["choices"]
        # Story's shipped adapter uses the first choice; Wardrobe requires exactly one assistant message.
        if strict_envelope and (type(choices) is not list or len(choices) != 1):
            raise ValueError("Expected one choice")
        choice = choices[0]
        reason = choice.get("finish_reason")
        finish = ("missing" if reason is None else "invalid_type" if type(reason) is not str else
                  reason if reason in ("stop", "length", "content_filter", "tool_calls", "function_call", "error") else "unknown")
        stage, code, paths = "finish", "incomplete_output", ["choices[0].finish_reason"]
        if finish != "stop":
            raise ValueError("Incomplete model output")
        stage, code, paths = "envelope", "invalid_envelope", ["choices[0].message"]
        message = choice["message"]
        tools = message.get("tool_calls")
        has_tools = tools not in (None, []) if strict_envelope else bool(tools)
        if has_tools:
            stage, code, paths = "finish", "tool_calls", ["choices[0].message.tool_calls"]
            raise ValueError("Unexpected tool calls")
        if strict_envelope and (message.get("function_call") is not None or message.get("role", "assistant") != "assistant"):
            raise ValueError("Unexpected message")
        stage, code, paths = "content", "non_text_content", ["choices[0].message.content"]
        content = message["content"]
        if type(content) is not str:
            raise ValueError("Expected text content")
        return content
    except (ValueError, KeyError, IndexError, TypeError, AttributeError, RecursionError):
        raise CompletionRejected(stage, code, paths, finish) from None
