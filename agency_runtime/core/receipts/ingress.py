"""Fail-closed normalization for model receipt persistence.

Receipt metadata can originate in host callbacks, public embedding APIs, or
third-party router payloads.  This module is the final trust boundary before a
receipt reaches SQLite: correlation identifiers are validated, display fields
are bounded, routing identities are canonicalized, and only an explicit
callback provenance may persist the authoritative ``litellm`` source.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Final
from urllib.parse import urlsplit

from agency_runtime.core.store.projections import sanitize_api_base

MAX_RECEIPT_CORRELATION_CHARS: Final[int] = 256
MAX_RECEIPT_HOST_CHARS: Final[int] = 64
MAX_RECEIPT_MODEL_CHARS: Final[int] = 256
MAX_RECEIPT_PROVIDER_CHARS: Final[int] = 128
MAX_RECEIPT_MODEL_ID_CHARS: Final[int] = 512
MAX_RECEIPT_TIMESTAMP_CHARS: Final[int] = 64
MAX_RECEIPT_FALLBACKS: Final[int] = 10_000

_PROVIDER_TOKEN = re.compile(r"[a-z0-9][a-z0-9._-]*\Z")
_CUSTOM_ALIAS = re.compile(r"(?:^|/)custom(?:/|$)", re.IGNORECASE)
_GENERIC_SOURCES = frozenset({"host", "wrapper", "unknown"})
_RECEIPT_STATUSES = frozenset(
    {
        "success",
        "completed",
        "ok",
        "failed",
        "failure",
        "error",
        "cancelled",
        "canceled",
        "timed_out",
        "timeout",
        "unavailable",
        "unknown",
    }
)


class ReceiptProvenance(Enum):
    """Internal ingestion channel, deliberately absent from the public API."""

    GENERIC = "generic"
    LITELLM_CALLBACK = "litellm_callback"


def _coerce(value: Any) -> str:
    if value is None:
        return ""
    try:
        return value if isinstance(value, str) else str(value)
    except Exception:
        return ""


def _safe_text(
    value: Any,
    maximum: int,
    *,
    reject_oversize: bool = False,
) -> str:
    raw = _coerce(value)
    if not raw:
        return ""
    if len(raw) > maximum and reject_oversize:
        return ""
    candidate = raw[:maximum]
    if any(not character.isprintable() for character in candidate):
        return ""
    return candidate.strip()


def _correlation_id(value: Any, field: str) -> str:
    raw = _coerce(value)
    if not raw:
        return ""
    if any(not character.isprintable() for character in raw):
        raise ValueError(f"{field} contains a control character")
    normalized = raw.strip()
    if len(normalized) > MAX_RECEIPT_CORRELATION_CHARS:
        raise ValueError(f"{field} exceeds the model-receipt correlation limit")
    return normalized


def _fallback_count(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return min(max(parsed, 0), MAX_RECEIPT_FALLBACKS)


def canonicalize_provider(value: Any) -> str:
    """Return one safe provider token or an empty untrusted value.

    Provider metadata is an identity, so overlong or malformed values are
    rejected instead of truncated into a different provider.  ``custom``
    aliases name a router/wrapper namespace rather than an actual provider.
    """

    provider = _safe_text(value, MAX_RECEIPT_PROVIDER_CHARS, reject_oversize=True).casefold()
    if not provider or _CUSTOM_ALIAS.search(provider):
        return ""
    return provider if _PROVIDER_TOKEN.fullmatch(provider) else ""


def _timestamp(value: Any) -> str:
    text = _safe_text(value, MAX_RECEIPT_TIMESTAMP_CHARS, reject_oversize=True)
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _api_base(value: Any) -> str:
    raw = _safe_text(value, 1_024)
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw)
    except (TypeError, ValueError):
        return ""
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        return ""
    return sanitize_api_base(raw)


def normalize_receipt_ingress(
    values: Mapping[str, Any],
    *,
    provenance: ReceiptProvenance,
) -> dict[str, Any]:
    """Normalize every persisted receipt field for one explicit provenance."""

    requested_source = _safe_text(values.get("source"), 16, reject_oversize=True).casefold()
    if provenance is ReceiptProvenance.LITELLM_CALLBACK:
        source = "litellm"
    else:
        source = requested_source if requested_source in _GENERIC_SOURCES else "unknown"

    resolved_model = _safe_text(
        values.get("resolved_model"),
        MAX_RECEIPT_MODEL_CHARS,
        reject_oversize=True,
    )
    if not resolved_model or _CUSTOM_ALIAS.search(resolved_model):
        resolved_model = "unavailable"

    host = _safe_text(
        values.get("host"),
        MAX_RECEIPT_HOST_CHARS,
        reject_oversize=True,
    ).casefold()
    status = _safe_text(values.get("status"), 32, reject_oversize=True).casefold()

    return {
        "trace_id": _correlation_id(values.get("trace_id"), "trace_id"),
        "session_id": _correlation_id(values.get("session_id"), "session_id"),
        "host": host or "unknown",
        "requested_model": _safe_text(values.get("requested_model"), MAX_RECEIPT_MODEL_CHARS),
        "model_group": _safe_text(values.get("model_group"), MAX_RECEIPT_MODEL_CHARS),
        "resolved_provider": canonicalize_provider(values.get("resolved_provider")),
        "resolved_model": resolved_model,
        "api_base": _api_base(values.get("api_base")),
        "attempted_fallbacks": _fallback_count(values.get("attempted_fallbacks")),
        "model_id": _safe_text(values.get("model_id"), MAX_RECEIPT_MODEL_ID_CHARS),
        "source": source,
        "started_at": _timestamp(values.get("started_at")),
        "ended_at": _timestamp(values.get("ended_at")),
        "status": status if status in _RECEIPT_STATUSES else "unknown",
    }


__all__ = [
    "MAX_RECEIPT_CORRELATION_CHARS",
    "MAX_RECEIPT_FALLBACKS",
    "MAX_RECEIPT_HOST_CHARS",
    "MAX_RECEIPT_MODEL_CHARS",
    "MAX_RECEIPT_MODEL_ID_CHARS",
    "MAX_RECEIPT_PROVIDER_CHARS",
    "MAX_RECEIPT_TIMESTAMP_CHARS",
    "canonicalize_provider",
]
