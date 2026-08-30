"""Shared projection for the two observable sides of Rule 8."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from agency_runtime.core.store.evidence import (
    PUBLISHED_ANYWAY_RUN_STATUSES,
    WITHHELD_RUN_STATUSES,
)

MAX_RULE8_EVIDENCE_ROWS: Final[int] = 500
AGENCY_BLIND_RUN_STATUSES: Final[frozenset[str]] = PUBLISHED_ANYWAY_RUN_STATUSES


def bounded_rule8_limit(limit: int) -> int:
    """Validate the public Rule-8 evidence window."""

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_RULE8_EVIDENCE_ROWS
    ):
        raise ValueError(f"Rule-8 evidence limit must be between 1 and {MAX_RULE8_EVIDENCE_ROWS}")
    return limit


def rule8_evidence_projection(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int,
    host: str = "",
) -> dict[str, Any]:
    """Partition a bounded exceptional-run window without inferring publication.

    ``AGENCY_BLIND_RUN_STATUSES`` says only that Agency could not verify or
    persist its evidence. Historical rows can predate Rule 8, so the projection
    deliberately does not claim that those host turns were published.
    """

    bounded = bounded_rule8_limit(limit)
    window = [dict(row) for row in rows[:bounded]]
    exceptional = WITHHELD_RUN_STATUSES | AGENCY_BLIND_RUN_STATUSES
    unexpected = sorted({str(row.get("status") or "") for row in window} - exceptional)
    if unexpected:
        raise ValueError("Rule-8 evidence contains a non-exceptional run status")
    withheld = [row for row in window if row.get("status") in WITHHELD_RUN_STATUSES]
    agency_blind = [row for row in window if row.get("status") in AGENCY_BLIND_RUN_STATUSES]
    returned = len(window)
    if len(withheld) + len(agency_blind) != returned:
        raise ValueError("Rule-8 evidence partition is incomplete")
    normalized_host = str(host or "").strip().casefold()
    return {
        "window": {
            "kind": "most_recent_matching_exceptional_runs",
            "host": normalized_host or None,
            "limit": bounded,
            "returned": returned,
        },
        "counts": {
            "matching_exceptional_runs": returned,
            "withheld": len(withheld),
            "agency_blind": len(agency_blind),
        },
        "withheld_statuses": sorted(WITHHELD_RUN_STATUSES),
        "agency_blind_statuses": sorted(AGENCY_BLIND_RUN_STATUSES),
        "withheld": withheld,
        "agency_blind": agency_blind,
    }


__all__ = [
    "AGENCY_BLIND_RUN_STATUSES",
    "MAX_RULE8_EVIDENCE_ROWS",
    "bounded_rule8_limit",
    "rule8_evidence_projection",
]
