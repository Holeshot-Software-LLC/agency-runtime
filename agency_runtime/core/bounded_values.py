"""Dependency-light canonical projections for bounded scalar collections."""

from __future__ import annotations

from typing import Any


def bounded_unique_strings(
    values: Any,
    *,
    limit: int,
    chars: int,
    collapse_whitespace: bool = False,
) -> list[str]:
    """Return unique bounded strings from at most ``limit`` inputs.

    Applying the item ceiling before normalization keeps adversarial lists from
    turning a projection helper into an unbounded scan. Callers choose whether
    internal whitespace is semantically significant; identity order and
    case-sensitive de-duplication are otherwise shared.
    """

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or isinstance(chars, bool)
        or not isinstance(chars, int)
        or limit < 0
        or chars < 0
    ):
        raise ValueError("limit and chars must be non-negative integers")
    if not isinstance(values, (list, tuple)) or not limit or not chars:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in values[:limit]:
        raw = str(item or "")
        normalized = " ".join(raw.split()) if collapse_whitespace else raw.strip()
        normalized = normalized[:chars]
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


__all__ = ["bounded_unique_strings"]
