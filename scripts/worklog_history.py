"""Deterministic Git-history identifiers shared by worklog tooling."""

from __future__ import annotations

import re
from collections.abc import Iterable

WORKLOG_SHORT_SHA_LENGTH = 8
_FULL_SHA_RE = re.compile(r"[0-9a-f]{40}")


def stable_short_shas(full_shas: Iterable[str]) -> list[str]:
    """Return fixed-width history prefixes or fail on malformed/colliding input."""

    values = list(full_shas)
    if any(_FULL_SHA_RE.fullmatch(value) is None for value in values):
        raise ValueError("worklog history requires full lowercase Git SHAs")
    shortened = [value[:WORKLOG_SHORT_SHA_LENGTH] for value in values]
    if len(shortened) != len(set(shortened)):
        raise ValueError(f"worklog {WORKLOG_SHORT_SHA_LENGTH}-character SHA prefix collision")
    return shortened
