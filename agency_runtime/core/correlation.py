"""Canonical validation for externally supplied turn-correlation identifiers."""

from __future__ import annotations

MAX_CORRELATION_ID_BYTES = 512


def validate_correlation_id(
    value: object,
    *,
    field: str = "correlation_id",
    required: bool = True,
) -> str:
    """Return one bounded printable identifier or raise ``ValueError``.

    Empty values remain available only to compatibility surfaces that
    explicitly opt into ``required=False``. Any supplied identifier still has
    the exact same type, Unicode, control-character, and UTF-8 byte limits.
    """

    if value is None or value == "":
        if required:
            raise ValueError(f"{field} is required")
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} is required")
    if not normalized.isprintable():
        raise ValueError(f"{field} must contain only printable characters")
    try:
        encoded = normalized.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field} must be valid UTF-8 text") from exc
    if len(encoded) > MAX_CORRELATION_ID_BYTES:
        raise ValueError(f"{field} exceeds the {MAX_CORRELATION_ID_BYTES}-byte UTF-8 limit")
    return normalized


__all__ = ["MAX_CORRELATION_ID_BYTES", "validate_correlation_id"]
