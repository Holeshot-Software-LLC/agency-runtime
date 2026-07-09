"""LiteLLM response-header receipt extraction.

LiteLLM exposes the model routing truth through response headers.  This module
keeps that extraction small and dependency-free so callers can pass plain dicts,
HTTP header objects, or any object exposing ``items()``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

LITELLM_MODEL_GROUP_HEADER = "x-litellm-model-group"
LITELLM_MODEL_API_BASE_HEADER = "x-litellm-model-api-base"
LITELLM_ATTEMPTED_FALLBACKS_HEADER = "x-litellm-attempted-fallbacks"
LITELLM_MODEL_ID_HEADER = "x-litellm-model-id"


def _headers_to_dict(headers: Mapping[str, Any] | Any | None) -> dict[str, str]:
    """Return a case-insensitive-ish lowercase header mapping."""
    if not headers:
        return {}

    items: Any
    if isinstance(headers, Mapping):
        items = headers.items()
    elif hasattr(headers, "items"):
        items = headers.items()
    else:
        return {}

    normalized: dict[str, str] = {}
    for key, value in items:
        if key is None or value is None:
            continue
        normalized[str(key).strip().lower()] = str(value).strip()
    return normalized


def _parse_int(value: str | None, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def extract_litellm_receipt_headers(headers: Mapping[str, Any] | Any | None) -> dict[str, Any]:
    """Extract LiteLLM model receipt fields from response headers.

    Returned keys intentionally match the canonical receipt field names used by
    ``normalize.normalize_litellm_receipt``.
    """
    lower = _headers_to_dict(headers)
    return {
        "model_group": lower.get(LITELLM_MODEL_GROUP_HEADER, ""),
        "api_base": lower.get(LITELLM_MODEL_API_BASE_HEADER, ""),
        "attempted_fallbacks": _parse_int(lower.get(LITELLM_ATTEMPTED_FALLBACKS_HEADER), 0),
        "model_id": lower.get(LITELLM_MODEL_ID_HEADER, ""),
    }


__all__ = [
    "LITELLM_MODEL_GROUP_HEADER",
    "LITELLM_MODEL_API_BASE_HEADER",
    "LITELLM_ATTEMPTED_FALLBACKS_HEADER",
    "LITELLM_MODEL_ID_HEADER",
    "extract_litellm_receipt_headers",
]
