"""Canonical model receipt normalization.

The Agency Runtime records what actually ran, not just what was requested.
These helpers normalize telemetry from LiteLLM, host runtimes, or wrappers into
one SQLite-compatible dictionary shape.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import urlparse

from .litellm import extract_litellm_receipt_headers

RECEIPT_FIELDS: tuple[str, ...] = (
    "trace_id",
    "host",
    "session_id",
    "requested_model",
    "model_group",
    "resolved_provider",
    "resolved_model",
    "api_base",
    "attempted_fallbacks",
    "model_id",
    "source",
    "started_at",
    "ended_at",
    "status",
)

_VALID_SOURCES = {"litellm", "host", "wrapper", "unknown"}
_CUSTOM_ALIAS_RE = re.compile(r"(^|/)custom/", re.IGNORECASE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_custom_alias(value: str) -> bool:
    value = value.strip().lower()
    return value.startswith("custom/") or bool(_CUSTOM_ALIAS_RE.search(value))


def _provider_model_from_model_id(model_id: str) -> tuple[str, str]:
    """Infer provider/model from a provider-qualified model_id when honest.

    ``custom/*`` aliases are wrapper aliases, not providers, and are never
    returned as resolved providers.
    """
    model_id = _clean(model_id)
    if not model_id or _is_custom_alias(model_id):
        return "", ""
    if "/" not in model_id:
        return "", model_id
    provider, model = model_id.split("/", 1)
    if not provider or provider.lower() == "custom" or not model:
        return "", ""
    return provider, model


def _provider_from_api_base(api_base: str) -> str:
    api_base = _clean(api_base)
    if not api_base:
        return ""
    parsed = urlparse(api_base if "://" in api_base else f"//{api_base}")
    host = (parsed.hostname or "").lower()
    if not host:
        return ""
    if "openai" in host:
        return "openai"
    if "anthropic" in host:
        return "anthropic"
    if "groq" in host:
        return "groq"
    if "mistral" in host:
        return "mistral"
    if "openrouter" in host:
        return "openrouter"
    if "azure" in host:
        return "azure"
    if host in {"localhost", "127.0.0.1", "0.0.0.0"}:
        return "local"
    # Return the hostname, not any requested model alias.
    return host


def _canonical_receipt(**values: Any) -> dict[str, Any]:
    now = _now()
    receipt: dict[str, Any] = {field: "" for field in RECEIPT_FIELDS}
    receipt.update(
        {
            "host": "unknown",
            "resolved_model": "unavailable",
            "attempted_fallbacks": 0,
            "source": "unknown",
            "started_at": now,
            "ended_at": now,
            "status": "unknown",
        }
    )
    for field in RECEIPT_FIELDS:
        if field in values and values[field] is not None:
            receipt[field] = values[field]

    for field in RECEIPT_FIELDS:
        if field == "attempted_fallbacks":
            receipt[field] = _int(receipt[field], 0)
        else:
            receipt[field] = _clean(receipt[field])

    if receipt["source"] not in _VALID_SOURCES:
        receipt["source"] = "unknown"
    if not receipt["host"]:
        receipt["host"] = "unknown"
    if not receipt["resolved_model"] or _is_custom_alias(receipt["resolved_model"]):
        receipt["resolved_model"] = "unavailable"
    if _is_custom_alias(receipt["resolved_provider"]):
        receipt["resolved_provider"] = ""
    if receipt["resolved_provider"].lower() == "custom":
        receipt["resolved_provider"] = ""
    if not receipt["status"]:
        receipt["status"] = "unknown"
    if not receipt["started_at"]:
        receipt["started_at"] = now
    if not receipt["ended_at"]:
        receipt["ended_at"] = now
    return receipt


def normalize_litellm_receipt(headers: Mapping[str, Any] | Any | None, requested_model: str) -> dict[str, Any]:
    """Normalize LiteLLM response headers into a canonical receipt."""
    extracted = extract_litellm_receipt_headers(headers)
    provider, resolved_model = _provider_model_from_model_id(extracted.get("model_id", ""))
    if not provider:
        provider = _provider_from_api_base(extracted.get("api_base", ""))

    has_litellm_truth = any(
        extracted.get(key) not in (None, "", 0)
        for key in ("model_group", "api_base", "attempted_fallbacks", "model_id")
    )
    source = "litellm" if has_litellm_truth else "unknown"
    status = "success" if resolved_model else "unknown"

    return _canonical_receipt(
        requested_model=requested_model,
        model_group=extracted.get("model_group", ""),
        resolved_provider=provider,
        resolved_model=resolved_model or "unavailable",
        api_base=extracted.get("api_base", ""),
        attempted_fallbacks=extracted.get("attempted_fallbacks", 0),
        model_id=extracted.get("model_id", ""),
        source=source,
        status=status,
    )


def _first(metadata: Mapping[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        if key in metadata and metadata[key] not in (None, ""):
            return metadata[key]
    return default


def normalize_host_receipt(host_metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize generic host/wrapper telemetry into a canonical receipt.

    Common aliases are accepted because host runtimes differ in naming.  Unknown
    metadata produces an honest unavailable receipt rather than inferring truth
    from the requested alias.
    """
    metadata = dict(host_metadata or {})
    requested = _first(metadata, "requested_model", "model", "requested", default="")
    model_id = _first(metadata, "model_id", "actual_model_id", "id", default="")
    resolved_model = _first(metadata, "resolved_model", "actual_model", "model_name", default="")
    provider = _first(metadata, "resolved_provider", "provider", "actual_provider", default="")
    api_base = _first(metadata, "api_base", "base_url", "model_api_base", default="")

    inferred_provider, inferred_model = _provider_model_from_model_id(_clean(model_id))
    if not resolved_model:
        resolved_model = inferred_model
    if not provider:
        provider = inferred_provider or _provider_from_api_base(_clean(api_base))

    source = _clean(_first(metadata, "source", default="host")).lower() or "host"
    if source not in {"host", "wrapper"}:
        source = "host" if metadata else "unknown"

    return _canonical_receipt(
        trace_id=_first(metadata, "trace_id", "trace", default=""),
        host=_first(metadata, "host", "runtime", default="unknown"),
        session_id=_first(metadata, "session_id", "session", default=""),
        requested_model=requested,
        model_group=_first(metadata, "model_group", "group", default=""),
        resolved_provider=provider,
        resolved_model=resolved_model or "unavailable",
        api_base=api_base,
        attempted_fallbacks=_first(metadata, "attempted_fallbacks", "fallbacks", default=0),
        model_id=model_id,
        source=source,
        started_at=_first(metadata, "started_at", "start_time", default=""),
        ended_at=_first(metadata, "ended_at", "end_time", default=""),
        status=_first(metadata, "status", default="success" if resolved_model else "unknown"),
    )


def build_unavailable_receipt(requested_model: str, reason: str) -> dict[str, Any]:
    """Build an honest unavailable receipt when no model truth is available."""
    receipt = _canonical_receipt(
        requested_model=requested_model,
        resolved_model="unavailable",
        source="unknown",
        status="unavailable",
    )
    # Preserve the reason in model_id where the current schema has no reason
    # column; callers can also log this alongside the receipt if desired.
    receipt["model_id"] = _clean(reason)
    return receipt


__all__ = [
    "RECEIPT_FIELDS",
    "normalize_litellm_receipt",
    "normalize_host_receipt",
    "build_unavailable_receipt",
]
