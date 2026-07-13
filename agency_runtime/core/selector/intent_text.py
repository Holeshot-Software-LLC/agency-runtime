"""Conservative extraction of affirmative routing intent.

The selector should route work the user asked agents to perform, not work they
explicitly excluded. This module masks only high-precision exclusion forms and
preserves string offsets so callers that slice the original message remain
correct. It deliberately does not try to solve general natural-language
negation.
"""

from __future__ import annotations

import re

_EXCLUSION_START_RE = re.compile(
    r"\b(?:do\s+not|don['\u2019]?t|without|no\s+need\s+to)\b"
    r"|\bno\b(?=(?:\s+[a-z0-9_-]+){0,4}\s+(?:work|changes?|tasks?)\b)"
    r"|\bbut\s+not\b"
    r"|(?<=[,;:])\s*\bnot\b",
    re.IGNORECASE,
)
_GENERAL_END_RE = re.compile(
    r"[;.\n]|\b(?:but|instead|rather|just|only)\b",
    re.IGNORECASE,
)
_WITHOUT_END_RE = re.compile(
    r"[,;.\n]|\b(?:but|instead|rather|just|only)\b",
    re.IGNORECASE,
)
_DOUBLE_NEGATIVE_RE = re.compile(
    r"\s+(?:skip|omit|disable)\b",
    re.IGNORECASE,
)


def mask_excluded_intent(text: str) -> str:
    """Replace explicit exclusion spans with spaces while preserving offsets."""
    if not isinstance(text, str):
        raise TypeError("routing text must be a string")
    masked = list(text)
    cursor = 0
    while (match := _EXCLUSION_START_RE.search(text, cursor)) is not None:
        marker = match.group(0).strip().lower().replace("\u2019", "'")
        if marker in {"do not", "don't", "dont"} and _DOUBLE_NEGATIVE_RE.match(
            text,
            match.end(),
        ):
            cursor = match.end()
            continue
        boundary_pattern = _WITHOUT_END_RE if marker in {"without", "no"} else _GENERAL_END_RE
        boundary = boundary_pattern.search(text, match.end())
        end = boundary.start() if boundary is not None else len(text)
        for index in range(match.start(), end):
            if masked[index] not in "\r\n":
                masked[index] = " "
        cursor = max(end, match.end())
    return "".join(masked)


def affirmative_intent(text: str) -> str:
    """Return compact affirmative text for lexical routing and policy matching."""
    return re.sub(r"\s+", " ", mask_excluded_intent(text)).strip()


__all__ = ["affirmative_intent", "mask_excluded_intent"]
