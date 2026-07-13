"""Bounded extraction helpers for LiteLLM routing evidence.

LiteLLM payloads and response objects cross a third-party callback boundary.
This module keeps all coercion, receipt-header filtering, and endpoint
sanitization deterministic and bounded before values reach the database or an
in-memory deduplication key.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import datetime, timezone
from itertools import islice
from typing import Any
from urllib.parse import urlsplit, urlunsplit

_MAX_ID_CHARS = 256
_MAX_HEADER_CHARS = 4096
_MAX_HEADER_ITEMS = 64
_MAX_FALLBACKS = 10_000


def clean(value: Any) -> str:
    """Return a stripped string without special-casing third-party classes."""

    return "" if value is None else str(value).strip()


def bounded(value: Any, limit: int) -> str:
    """Coerce *value* to text and cap it at an internal positive limit."""

    return clean(value)[:limit]


def identifier(value: Any) -> str:
    """Return a collision-resistant ID that fits the runtime's 256-char cap."""

    text = clean(value)
    if len(text) <= _MAX_ID_CHARS:
        return text
    digest = hashlib.sha256(text.encode("utf-8", errors="surrogatepass")).hexdigest()[:16]
    prefix = text[: _MAX_ID_CHARS - len(digest) - 1]
    return f"{prefix}:{digest}"


def mapping(value: Any) -> Mapping[str, Any]:
    """Return mapping-like callback data or an empty immutable view."""

    return value if isinstance(value, Mapping) else {}


def first(*values: Any) -> str:
    """Return the first non-empty string representation in *values*."""

    for value in values:
        candidate = clean(value)
        if candidate:
            return candidate
    return ""


def metadata(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Merge LiteLLM metadata shapes, preferring the request-level values."""

    direct = mapping(payload.get("metadata"))
    params = mapping(payload.get("litellm_params"))
    nested = mapping(params.get("metadata"))
    return {**nested, **direct}


def response_value(response_obj: Any, key: str) -> Any:
    """Read one response field from dict- or attribute-style LiteLLM objects."""

    if isinstance(response_obj, Mapping):
        return response_obj.get(key)
    return getattr(response_obj, key, None)


def hidden_params(response_obj: Any) -> Mapping[str, Any]:
    """Return LiteLLM's optional hidden response metadata mapping."""

    return mapping(response_value(response_obj, "_hidden_params"))


def trace_id(payload: Mapping[str, Any], response_obj: Any = None) -> str:
    """Extract a bounded request correlation ID from supported LiteLLM shapes."""

    request_metadata = metadata(payload)
    params = mapping(payload.get("litellm_params"))
    return identifier(
        first(
            request_metadata.get("agency_trace_id"),
            request_metadata.get("trace_id"),
            payload.get("litellm_call_id"),
            params.get("litellm_call_id"),
            payload.get("litellm_trace_id"),
            params.get("litellm_trace_id"),
            response_value(response_obj, "id"),
        )
    )


def session_id(payload: Mapping[str, Any], fallback_trace_id: str) -> str:
    """Extract a bounded session ID, falling back to the request trace ID."""

    request_metadata = metadata(payload)
    return identifier(
        first(
            request_metadata.get("agency_session_id"),
            request_metadata.get("session_id"),
            payload.get("session_id"),
            fallback_trace_id,
        )
    )


def known_headers(response_obj: Any) -> dict[str, str]:
    """Extract only bounded receipt headers; never copy authorization fields."""

    from agency_runtime.core.receipts.litellm import (
        LITELLM_ATTEMPTED_FALLBACKS_HEADER,
        LITELLM_MODEL_API_BASE_HEADER,
        LITELLM_MODEL_GROUP_HEADER,
        LITELLM_MODEL_ID_HEADER,
    )

    wanted = {
        LITELLM_MODEL_GROUP_HEADER,
        LITELLM_MODEL_API_BASE_HEADER,
        LITELLM_ATTEMPTED_FALLBACKS_HEADER,
        LITELLM_MODEL_ID_HEADER,
    }
    hidden = hidden_params(response_obj)
    candidates: list[Any] = [hidden.get("additional_headers")]
    raw_response = response_value(response_obj, "_response")
    if raw_response is not None:
        candidates.append(getattr(raw_response, "headers", None))

    extracted: dict[str, str] = {}
    for candidate in candidates:
        if not isinstance(candidate, Mapping) and not hasattr(candidate, "items"):
            continue
        try:
            items = candidate.items()
        except Exception:  # third-party header containers must not break traffic
            items = ()
        for key, value in islice(items, _MAX_HEADER_ITEMS):
            normalized = bounded(key, 128).casefold()
            if normalized in wanted and value is not None:
                extracted[normalized] = bounded(value, _MAX_HEADER_CHARS)

    # Some LiteLLM versions expose the same routing values directly.
    direct = {
        LITELLM_MODEL_GROUP_HEADER: hidden.get("model_group"),
        LITELLM_MODEL_API_BASE_HEADER: hidden.get("api_base"),
        LITELLM_MODEL_ID_HEADER: hidden.get("model_id"),
        LITELLM_ATTEMPTED_FALLBACKS_HEADER: hidden.get("attempted_fallbacks"),
    }
    for key, value in direct.items():
        if key not in extracted and value not in (None, ""):
            extracted[key] = bounded(value, _MAX_HEADER_CHARS)
    return extracted


def sanitize_api_base(value: Any) -> str:
    """Remove credentials/query data and reject non-HTTP endpoint metadata."""

    text = bounded(value, _MAX_HEADER_CHARS)
    if not text or any(
        character.isspace() or ord(character) < 32 or ord(character) == 127 for character in text
    ):
        return ""
    try:
        parts = urlsplit(text)
        host = parts.hostname
        port = parts.port
    except (TypeError, ValueError):
        return ""
    if parts.scheme.casefold() not in {"http", "https"} or not host:
        return ""
    host = host.casefold()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = f"{host}:{port}" if port is not None else host
    return urlunsplit((parts.scheme.casefold(), netloc, parts.path.rstrip("/"), "", ""))


def provider_model(model: Any) -> tuple[str, str]:
    """Split a provider-qualified actual model without trusting custom aliases."""

    value = bounded(model, 1024)
    if not value or value.casefold().startswith("custom/"):
        return "", ""
    if "/" not in value:
        return "", value
    provider, resolved = value.split("/", 1)
    if not provider or not resolved or provider.casefold() == "custom":
        return "", ""
    return provider, resolved


def iso_time(value: Any) -> str:
    """Normalize callback timestamps to UTC, using current time if absent."""

    if isinstance(value, datetime):
        parsed = value
    else:
        text = bounded(value, 128)
        if not text:
            return datetime.now(timezone.utc).isoformat()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc).isoformat()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def event_identity(response_obj: Any, start_time: Any) -> str:
    """Build a stable bounded identity for sync/async duplicate callbacks."""

    response_id = identifier(response_value(response_obj, "id"))
    if response_id:
        return response_id
    if isinstance(start_time, datetime):
        return iso_time(start_time)
    supplied_start = bounded(start_time, _MAX_ID_CHARS)
    return supplied_start or str(id(response_obj))


def bounded_count(value: Any, *, maximum: int = _MAX_FALLBACKS) -> int:
    """Return a non-negative, SQLite-safe operational count."""

    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return min(max(parsed, 0), maximum)


__all__ = [
    "bounded",
    "bounded_count",
    "clean",
    "event_identity",
    "first",
    "hidden_params",
    "identifier",
    "iso_time",
    "known_headers",
    "mapping",
    "metadata",
    "provider_model",
    "response_value",
    "sanitize_api_base",
    "session_id",
    "trace_id",
]
