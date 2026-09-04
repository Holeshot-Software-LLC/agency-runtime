"""Bounded, credential-safe structured-output provider transport.

The semantic selector and roster auditor have different prompts and response
schemas. This module provides their small common transport boundary without
coupling callers to selector-specific validation.
"""

from __future__ import annotations

import json
import math
import os
import time
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.cli_transport import invoke_cli_structured
from agency_runtime.core.config import (
    ProviderEntry,
    _is_loopback_http_url,
    is_safe_credential_url,
)
from agency_runtime.core.http_safety import open_no_redirect
from agency_runtime.core.model_capabilities import requires_completion_token_parameter
from agency_runtime.core.reply_budget import completion_cap_tokens

MAX_STRUCTURED_PROMPT_BYTES = 1_280 * 1024
MAX_STRUCTURED_SCHEMA_BYTES = 64 * 1024
MAX_STRUCTURED_RESPONSE_BYTES = 128 * 1024
MAX_STRUCTURED_TIMEOUT_SECONDS = 120.0
MAX_STRUCTURED_REQUEST_BYTES = (2 * MAX_STRUCTURED_PROMPT_BYTES) + (96 * 1024)
_STRUCTURED_READ_CHUNK_BYTES = 16 * 1024
_HTTP_PROVIDER_TYPES = frozenset(
    {
        "anthropic",
        "litellm",
        "ollama",
        "openai",
        "openai-compatible",
    }
)

# Per-adapter ``thinking_level`` mapping. Mirrors
# ``docs/roadmap/reference-workforce-inference-stages.md`` §"thinking_level
# adapter mapping".
_ANTHROPIC_THINKING_BUDGETS = {
    "low": 1024,
    "medium": 4096,
    "high": 16384,
    "xhigh": 32768,
}
_OPENAI_REASONING_EFFORTS = frozenset({"low", "medium", "high"})
_LITELLM_REASONING_EFFORTS = frozenset({"low", "medium", "high", "xhigh"})


def _translate_thinking_level_for_adapter(
    provider_type: str,
    thinking_level: str,
) -> str:
    """Return the consumed thinking level for ``provider_type``.

    The receipt records both the configured value (what the operator asked
    for) and the consumed value (what the adapter actually applied). When
    the adapter does not understand a value, the consumed value is the
    string ``"unsupported"`` and the request omits the parameter. CLI and
    ollama transports ignore the value at call time and the configured
    value is still recorded for the audit trail.
    """
    if not thinking_level:
        return ""
    normalized = thinking_level.strip().casefold()
    if not normalized:
        return ""
    if provider_type == "openai-compatible":
        return normalized if normalized in _OPENAI_REASONING_EFFORTS else "unsupported"
    if provider_type == "anthropic":
        return normalized if normalized in _ANTHROPIC_THINKING_BUDGETS else "unsupported"
    return normalized  # litellm: reasoning_effort; ollama / cli: recorded and ignored


def translate_thinking_level_for_adapter(
    provider_type: str,
    thinking_level: str,
) -> str:
    """Public adapter: project the consumed thinking level for one provider type."""

    return _translate_thinking_level_for_adapter(provider_type, thinking_level)


@dataclass(frozen=True, slots=True)
class StructuredProviderResult:
    """Validated structured output plus non-secret provider identity evidence."""

    value: dict[str, Any]
    provider_name: str
    provider_type: str
    transport: str
    requested_model: str
    model_group: str
    actual_model: str
    model_receipt_source: str
    latency_ms: int
    thinking_level_configured: str = ""
    thinking_level_consumed: str = ""
    # AR-385: what the transport asked for and what the provider reports it
    # spent. ``reply_budget_tokens`` is the stage's or operator's visible-reply
    # allowance; ``completion_cap_tokens`` adds the thinking allowance and is
    # the figure actually sent. ``completion_tokens`` is None when the reply
    # carried no usage. A reply is truncated when the provider says so or when
    # it spent exactly the cap, which is how a gateway that reports ``stop``
    # for a cut reply still shows its hand.
    reply_budget_tokens: int = 0
    completion_cap_tokens: int = 0
    completion_tokens: int | None = None
    finish_reason: str = ""
    reply_truncated: bool = False
    # AR-388 / ADR-0204: a non-empty value means the transport made no call at
    # all and says why, from a closed vocabulary; ``value`` is then empty.
    failure_reason: str = ""

    def receipt(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "provider_type": self.provider_type,
            "transport": self.transport,
            "requested_model": self.requested_model,
            "model_group": self.model_group,
            "actual_model": self.actual_model,
            "model_receipt_source": self.model_receipt_source,
            "latency_ms": self.latency_ms,
            "thinking_level_configured": self.thinking_level_configured,
            "thinking_level_consumed": self.thinking_level_consumed,
            "reply_budget_tokens": self.reply_budget_tokens,
            "completion_cap_tokens": self.completion_cap_tokens,
            "completion_tokens": self.completion_tokens,
            "finish_reason": self.finish_reason,
            "reply_truncated": self.reply_truncated,
        }


def _bounded_timeout(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        timeout = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    if not math.isfinite(timeout) or timeout <= 0:
        return 0.0
    return min(timeout, MAX_STRUCTURED_TIMEOUT_SECONDS)


def _bounded_json(value: Mapping[str, Any], *, maximum_bytes: int) -> bytes | None:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError):
        return None
    return encoded if len(encoded) <= maximum_bytes else None


def _parse_json_object(value: bytes | str) -> dict[str, Any] | None:
    try:
        parsed = safe_load_bounded_json(
            value,
            maximum_bytes=MAX_STRUCTURED_RESPONSE_BYTES,
            maximum_depth=32,
            maximum_nodes=10_000,
        )
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _set_response_read_timeout(response: object, timeout: float) -> bool:
    """Reduce a urllib response's underlying socket timeout when discoverable."""

    pending = [response]
    visited: set[int] = set()
    updated = False
    while pending and len(visited) < 16:
        current = pending.pop(0)
        identity = id(current)
        if identity in visited:
            continue
        visited.add(identity)
        try:
            setter = getattr(current, "settimeout", None)
        except Exception:
            setter = None
        if callable(setter):
            try:
                setter(timeout)
            except Exception:
                pass
            else:
                updated = True
        for attribute in ("fp", "raw", "_sock", "sock", "socket"):
            try:
                nested = getattr(current, attribute, None)
            except Exception:
                continue
            if nested is not None and id(nested) not in visited:
                pending.append(nested)
    return updated


def _read_http_response(response: object, *, deadline: float) -> bytes | None:
    """Read one bounded response without allowing slow-drip deadline extension."""

    reader = getattr(response, "read1", None)
    if not callable(reader):
        reader = getattr(response, "read", None)
        if not callable(reader):
            return None
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        _set_response_read_timeout(response, remaining)
        value = reader(MAX_STRUCTURED_RESPONSE_BYTES + 1)
        if time.monotonic() >= deadline or not isinstance(
            value,
            (bytes, bytearray, memoryview),
        ):
            return None
        raw = bytes(value)
        return raw if len(raw) <= MAX_STRUCTURED_RESPONSE_BYTES else None

    chunks: list[bytes] = []
    total = 0
    while total <= MAX_STRUCTURED_RESPONSE_BYTES:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        _set_response_read_timeout(response, remaining)
        requested = min(
            _STRUCTURED_READ_CHUNK_BYTES,
            (MAX_STRUCTURED_RESPONSE_BYTES + 1) - total,
        )
        value = reader(requested)
        if not isinstance(value, (bytes, bytearray, memoryview)):
            return None
        chunk = bytes(value)
        if time.monotonic() >= deadline:
            return None
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        total += len(chunk)
    return None


def _parse_model_text(value: object) -> dict[str, Any] | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2 and lines[0].strip().casefold() in {"```", "```json"}:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    parsed = _parse_json_object(text)
    if parsed is not None:
        return parsed
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    return _parse_json_object(text[start : end + 1])


def _model_identity(value: object) -> str:
    """Return a bounded display-safe model identity from provider evidence."""

    if not isinstance(value, str):
        return ""
    normalized = " ".join(value.split())
    if (
        not normalized
        or "\x00" in normalized
        or len(normalized.encode("utf-8", errors="replace")) > 512
        or any(ord(character) < 32 for character in normalized)
    ):
        return ""
    return normalized


def _response_text(
    data: Mapping[str, Any],
    *,
    provider_type: str,
    ollama_mode: bool,
) -> str:
    if ollama_mode:
        message = data.get("message")
        return (
            str(message.get("content"))
            if isinstance(message, Mapping) and isinstance(message.get("content"), str)
            else ""
        )
    if provider_type == "anthropic":
        blocks = data.get("content")
        if not isinstance(blocks, list):
            return ""
        text = "".join(
            str(block["text"])
            for block in blocks
            if isinstance(block, Mapping)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
        )
        # GLM may wrap JSON in markdown code fences; strip them so the
        # parser can find the JSON object.
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].strip().casefold() in {"```", "```json"}:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            stripped = "\n".join(lines).strip()
        return stripped
    choices = data.get("choices")
    first = choices[0] if isinstance(choices, list) and choices else None
    message = first.get("message") if isinstance(first, Mapping) else None
    return (
        str(message.get("content"))
        if isinstance(message, Mapping) and isinstance(message.get("content"), str)
        else ""
    )


_TRUNCATED_FINISH_REASONS = frozenset({"length", "max_tokens"})


def _finish_reason(value: object) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip().casefold()[:32]
    return normalized if normalized.isidentifier() or normalized.isalnum() else ""


def _token_count(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _response_usage(
    data: Mapping[str, Any],
    *,
    provider_type: str,
    ollama_mode: bool,
) -> tuple[int | None, str]:
    """Return ``(completion_tokens, finish_reason)`` from one provider reply.

    Both values are read only from the reply's own accounting fields, never
    from model text, and both stay bounded: a count is a non-negative int or
    unknown, a finish reason is a short identifier or empty.
    """

    if ollama_mode:
        return _token_count(data.get("eval_count")), _finish_reason(data.get("done_reason"))
    usage = data.get("usage")
    usage = usage if isinstance(usage, Mapping) else {}
    if provider_type == "anthropic":
        return _token_count(usage.get("output_tokens")), _finish_reason(data.get("stop_reason"))
    choices = data.get("choices")
    first = choices[0] if isinstance(choices, list) and choices else None
    finish = first.get("finish_reason") if isinstance(first, Mapping) else None
    return _token_count(usage.get("completion_tokens")), _finish_reason(finish)


def _reply_truncated(completion_tokens: int | None, finish_reason: str, cap: int) -> bool:
    """Whether the reply reached the requested completion cap (AR-385).

    A provider that says ``length`` or ``max_tokens`` is believed. One that
    reports ``stop`` while spending exactly the cap is not: the captured
    MiniMax replies through the gateway did exactly that, with a closed JSON
    object missing its last rows.
    """

    if finish_reason in _TRUNCATED_FINISH_REASONS:
        return True
    return completion_tokens is not None and cap > 0 and completion_tokens >= cap


def _forwarded_thinking_level(provider: ProviderEntry) -> str:
    """Return the reasoning effort the HTTP payload will carry, or empty."""

    provider_type = provider.type.strip().casefold()
    if (
        provider_type == "openai-compatible"
        and provider.reasoning_effort in _OPENAI_REASONING_EFFORTS
    ):
        return provider.reasoning_effort
    if provider_type == "litellm" and provider.reasoning_effort in _LITELLM_REASONING_EFFORTS:
        return provider.reasoning_effort
    return ""


def _requested_completion_cap(provider: ProviderEntry) -> tuple[int, int]:
    """Return ``(reply_budget, completion_cap)`` for one provider entry."""

    return completion_cap_tokens(
        provider, thinking_level_forwarded=_forwarded_thinking_level(provider)
    )


def _join_api_path(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    normalized = "/" + path.lstrip("/")
    if base.casefold().endswith("/v1") and normalized.casefold().startswith("/v1/"):
        normalized = normalized[3:]
    return base + normalized


def _schema_instruction(system_prompt: str, schema: Mapping[str, Any]) -> str:
    serialized = json.dumps(
        schema,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )
    return (
        f"{system_prompt}\n\nReturn ONLY a single valid JSON object matching this "
        f"schema (no prose, no markdown, no explanation). Start with {{ and end with }}:\n"
        f"{serialized}"
    )


def _http_payload(
    provider: ProviderEntry,
    prompt: str,
    schema: Mapping[str, Any],
    *,
    system_prompt: str,
) -> tuple[dict[str, Any], str]:
    provider_type = provider.type.strip().casefold()
    ollama_mode = provider.ollama_mode or provider_type == "ollama"
    # AR-385: the cap is the stage's or operator's reply budget plus the
    # thinking allowance the adapter forwards, never a transport constant.
    _reply_budget, completion_cap = _requested_completion_cap(provider)
    if ollama_mode:
        return (
            {
                "format": dict(schema),
                "messages": [
                    {"content": system_prompt, "role": "system"},
                    {"content": prompt, "role": "user"},
                ],
                "model": provider.model,
                "options": {"num_ctx": 131072, "num_predict": completion_cap, "temperature": 0},
                "stream": False,
                "think": False,
            },
            "/api/chat",
        )
    if provider_type == "anthropic":
        payload: dict[str, Any] = {
            "max_tokens": completion_cap,
            "messages": [
                {"content": prompt, "role": "user"},
            ],
            "model": provider.model,
            "system": _schema_instruction(system_prompt, schema),
            "temperature": 0,
        }
        # Thinking mode is disabled for structured JSON: thinking consumes
        # the response budget and truncates the JSON output. The schema
        # instruction already enforces JSON without needing extended reasoning.
        return payload, "/v1/messages"
    payload = {
        "messages": [
            {"content": _schema_instruction(system_prompt, schema), "role": "system"},
            {"content": prompt, "role": "user"},
        ],
        "model": provider.model,
        "response_format": {"type": "json_object"},
        "stream": False,
        "temperature": 0,
    }
    if provider_type == "litellm":
        payload["response_format"] = {
            "json_schema": {
                "name": "agency_structured_response",
                "schema": dict(schema),
                "strict": True,
            },
            "type": "json_schema",
        }
    if requires_completion_token_parameter(provider.model, declared=provider.token_parameter):
        payload["max_completion_tokens"] = completion_cap
        payload.pop("temperature", None)
    else:
        payload["max_tokens"] = completion_cap
    forwarded = _forwarded_thinking_level(provider)
    if forwarded:
        payload["reasoning_effort"] = forwarded
    return payload, "/v1/chat/completions"


def _http_headers(provider_type: str, api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if provider_type == "litellm":
        # Keep retry authority local to the Agency call. The shared gateway may
        # serve foreign routes with a different global retry policy, while
        # Agency's ordered deployments use one attempt per order level.
        headers["x-litellm-num-retries"] = "0"
    if not api_key or provider_type == "ollama":
        return headers
    if provider_type == "anthropic":
        headers["anthropic-version"] = "2023-06-01"
        headers["x-api-key"] = api_key
    else:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


# AR-388 / ADR-0204. A provider whose configured credential variable the
# launching environment never carried is a fault of that environment, not of
# the gateway. The transport says so instead of sending an unauthenticated
# request, so the stage records the cause before any call is made.
PROVIDER_CREDENTIAL_ENV_UNSET = "provider_credential_env_unset"
_KEYLESS_PROVIDER_TYPES = frozenset({"ollama", "cli"})


def provider_credential_env_unset(provider: ProviderEntry) -> bool:
    """Return whether the provider names a credential variable the environment lacks."""

    if provider.api_key or not provider.api_key_env:
        return False
    if provider.type.strip().casefold() in _KEYLESS_PROVIDER_TYPES or provider.ollama_mode:
        return False
    return not os.environ.get(provider.api_key_env)


def _credential_unset_result(
    provider: ProviderEntry,
    provider_type: str,
    started: float,
) -> StructuredProviderResult:
    return StructuredProviderResult(
        value={},
        provider_name=provider.name,
        provider_type=provider_type,
        transport="",
        requested_model=provider.model,
        model_group=provider.model if provider_type == "litellm" else "",
        actual_model="",
        model_receipt_source="unavailable",
        latency_ms=max(0, int((time.monotonic() - started) * 1000)),
        thinking_level_configured=provider.reasoning_effort,
        thinking_level_consumed=_translate_thinking_level_for_adapter(
            provider_type, provider.reasoning_effort
        ),
        failure_reason=PROVIDER_CREDENTIAL_ENV_UNSET,
    )


def _http_provider_is_safe(provider: ProviderEntry, api_key: str) -> bool:
    provider_type = provider.type.strip().casefold()
    if provider_type not in _HTTP_PROVIDER_TYPES or not provider.model or not provider.base_url:
        return False
    if not is_safe_credential_url(provider.base_url):
        return False
    if provider_type == "ollama" or provider.ollama_mode:
        return _is_loopback_http_url(provider.base_url) or provider.base_url.casefold().startswith(
            "https://"
        )
    keyless_loopback = provider_type in {
        "openai",
        "openai-compatible",
        "litellm",
    } and _is_loopback_http_url(provider.base_url)
    return bool(api_key or keyless_loopback)


def invoke_structured_provider_result(
    provider: ProviderEntry,
    prompt: str,
    schema: Mapping[str, Any],
    *,
    system_prompt: str,
    timeout: float | None = None,
) -> StructuredProviderResult | None:
    """Return bounded structured output with truthful provider-model evidence."""

    started = time.monotonic()
    if not isinstance(prompt, str) or not isinstance(system_prompt, str):
        return None
    try:
        invalid_text = (
            not prompt.strip()
            or "\x00" in prompt
            or len(prompt.encode("utf-8")) > MAX_STRUCTURED_PROMPT_BYTES
            or not system_prompt.strip()
            or "\x00" in system_prompt
            or len(system_prompt.encode("utf-8")) > MAX_STRUCTURED_SCHEMA_BYTES
        )
    except UnicodeError:
        return None
    if invalid_text:
        return None
    schema_bytes = _bounded_json(schema, maximum_bytes=MAX_STRUCTURED_SCHEMA_BYTES)
    request_timeout = _bounded_timeout(provider.timeout if timeout is None else timeout)
    if schema_bytes is None or request_timeout <= 0:
        return None
    provider_type = provider.type.strip().casefold()
    if provider_type == "cli":
        value = invoke_cli_structured(
            provider,
            prompt,
            schema,
            timeout=request_timeout,
            system_prompt=system_prompt,
        )
        if value is None:
            return None
        return StructuredProviderResult(
            value=value,
            provider_name=provider.name,
            provider_type=provider_type,
            transport=provider.transport.strip().casefold(),
            requested_model=provider.model,
            model_group="",
            # A successful allowlisted CLI invocation executed with this exact explicit
            # --model argument. Unlike a router alias, there is no downstream model to
            # reconcile; retain the command-bound selection as the receipt and identify
            # its source honestly instead of reporting an unavailable model.
            actual_model=provider.model,
            model_receipt_source="cli.explicit_model_argument",
            latency_ms=max(0, int((time.monotonic() - started) * 1000)),
            thinking_level_configured=provider.reasoning_effort,
            thinking_level_consumed=_translate_thinking_level_for_adapter(
                provider_type, provider.reasoning_effort
            ),
        )

    if provider_credential_env_unset(provider):
        return _credential_unset_result(provider, provider_type, started)
    api_key = provider.resolve_api_key()
    if not _http_provider_is_safe(provider, api_key):
        return None
    payload, path = _http_payload(
        provider,
        prompt,
        schema,
        system_prompt=system_prompt,
    )
    body = _bounded_json(payload, maximum_bytes=MAX_STRUCTURED_REQUEST_BYTES)
    if body is None:
        return None
    request = urllib.request.Request(
        _join_api_path(provider.base_url, path),
        data=body,
        headers=_http_headers(provider_type, api_key),
        method="POST",
    )
    deadline = time.monotonic() + request_timeout
    try:
        with open_no_redirect(request, timeout=request_timeout) as response:
            raw = _read_http_response(response, deadline=deadline)
    except Exception:
        return None
    if raw is None:
        return None
    response_object = _parse_json_object(raw)
    if response_object is None:
        return None
    ollama_mode = provider.ollama_mode or provider_type == "ollama"
    reply_budget, completion_cap = _requested_completion_cap(provider)
    completion_tokens, finish_reason = _response_usage(
        response_object, provider_type=provider_type, ollama_mode=ollama_mode
    )
    truncated = _reply_truncated(completion_tokens, finish_reason, completion_cap)
    value = _parse_model_text(
        _response_text(response_object, provider_type=provider_type, ollama_mode=ollama_mode)
    )
    if value is None:
        if not truncated:
            return None
        # The reply was cut before a complete JSON object formed. Return the
        # truncation as evidence rather than a bare None, so the stage can
        # record why it has nothing to parse instead of "no valid response".
        value = {}
    actual_model = _model_identity(response_object.get("model"))
    return StructuredProviderResult(
        value=value,
        provider_name=provider.name,
        provider_type=provider_type,
        transport="",
        requested_model=provider.model,
        model_group=provider.model if provider_type == "litellm" else "",
        actual_model=actual_model,
        model_receipt_source="response.body.model" if actual_model else "unavailable",
        latency_ms=max(0, int((time.monotonic() - started) * 1000)),
        thinking_level_configured=provider.reasoning_effort,
        thinking_level_consumed=_translate_thinking_level_for_adapter(
            provider_type, provider.reasoning_effort
        ),
        reply_budget_tokens=reply_budget,
        completion_cap_tokens=completion_cap,
        completion_tokens=completion_tokens,
        finish_reason=finish_reason,
        reply_truncated=truncated,
    )


def invoke_structured_provider(
    provider: ProviderEntry,
    prompt: str,
    schema: Mapping[str, Any],
    *,
    system_prompt: str,
    timeout: float | None = None,
) -> dict[str, Any] | None:
    """Compatibility wrapper returning only the validated structured value."""

    result = invoke_structured_provider_result(
        provider,
        prompt,
        schema,
        system_prompt=system_prompt,
        timeout=timeout,
    )
    return None if result is None else result.value


__all__ = [
    "MAX_STRUCTURED_PROMPT_BYTES",
    "MAX_STRUCTURED_RESPONSE_BYTES",
    "MAX_STRUCTURED_SCHEMA_BYTES",
    "StructuredProviderResult",
    "invoke_structured_provider",
    "invoke_structured_provider_result",
    "translate_thinking_level_for_adapter",
]
