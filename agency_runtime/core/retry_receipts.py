"""Authenticated continuation receipts shared by native host adapters."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

DEFAULT_MAX_INSTRUCTION_CHARS = 48_000
_RETRY_RECEIPT_SUFFIX = "<!-- agency-continuation:{receipt} -->"
_RETRY_RECEIPT_PATTERN = re.compile(
    r"<!-- agency-continuation:"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}) -->\s*\Z",
    re.IGNORECASE,
)


def normalize_receipt_id(value: Any) -> str:
    """Accept only the canonical lowercase UUID shape emitted by the Store."""
    candidate = str(value or "").strip().lower()
    try:
        normalized = str(UUID(candidate))
    except (ValueError, AttributeError, TypeError):
        return ""
    return normalized if candidate == normalized else ""


def pending_retry_receipt(prompt: str) -> str:
    """Extract a receipt only from one complete Agency feedback instruction."""
    body = str(prompt or "").strip()
    normalized = body.casefold()
    if normalized.startswith("<hook_prompt ") and normalized.endswith("</hook_prompt>"):
        body_start = body.find(">")
        if body_start < 0:
            return ""
        body = body[body_start + 1 : -len("</hook_prompt>")].strip()
    matched = _RETRY_RECEIPT_PATTERN.search(body)
    return normalize_receipt_id(matched.group(1)) if matched is not None else ""


def attach_retry_receipt(
    reason: str,
    receipt: str,
    *,
    maximum_chars: int = DEFAULT_MAX_INSTRUCTION_CHARS,
) -> str:
    """Append a receipt without allowing the output bound to truncate it."""
    normalized_receipt = normalize_receipt_id(receipt)
    if not normalized_receipt:
        raise ValueError("continuation receipt must be a canonical UUID")
    limit = max(0, int(maximum_chars))
    suffix = "\n\n" + _RETRY_RECEIPT_SUFFIX.format(receipt=normalized_receipt)
    if len(suffix) > limit:
        raise ValueError("continuation receipt does not fit the instruction bound")
    return str(reason or "")[: max(0, limit - len(suffix))] + suffix


__all__ = [
    "DEFAULT_MAX_INSTRUCTION_CHARS",
    "attach_retry_receipt",
    "normalize_receipt_id",
    "pending_retry_receipt",
]
