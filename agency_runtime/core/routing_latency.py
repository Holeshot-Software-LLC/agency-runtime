"""Content-free routing-latency projections shared by operator surfaces."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

DEFAULT_ROUTING_LATENCY_BUDGET_MS = 15_000


def nearest_rank_percentile(ordered: Sequence[int], percentile: float) -> int:
    """Return the nearest-rank percentile of an already-sorted sequence."""

    if not ordered:
        return 0
    rank = max(1, math.ceil(percentile / 100 * len(ordered)))
    return ordered[min(len(ordered), rank) - 1]


def latency_summary(values: Sequence[int]) -> dict[str, int]:
    """Return the stable summary used for every latency dimension."""

    ordered = sorted(values)
    return {
        "count": len(ordered),
        "min_ms": ordered[0] if ordered else 0,
        "p50_ms": nearest_rank_percentile(ordered, 50),
        "p95_ms": nearest_rank_percentile(ordered, 95),
        "max_ms": ordered[-1] if ordered else 0,
    }


def routing_latency_projection(
    rows: Sequence[Mapping[str, Any]],
    *,
    budget_ms: int = DEFAULT_ROUTING_LATENCY_BUDGET_MS,
) -> dict[str, Any]:
    """Project recorded routing costs without turning absent work into fast work.

    A nonpositive decision latency means routing did not spend provider time and
    is excluded. Provider/Agency attribution is available only when the stored
    receipts report a positive provider subtotal; older zero-duration receipts
    are unknown, not free provider calls.
    """

    budget = int(budget_ms or DEFAULT_ROUTING_LATENCY_BUDGET_MS)
    recorded = [row for row in rows if int(row["latency_ms"]) > 0]
    values = [int(row["latency_ms"]) for row in recorded]
    overall = latency_summary(values)
    attributable = []
    for row in recorded:
        provider_calls = int(row.get("provider_calls") or 0)
        timed_value = row.get("provider_timed_calls")
        provider_timed_calls = provider_calls if timed_value is None else int(timed_value or 0)
        if (
            provider_calls > 0
            and provider_timed_calls == provider_calls
            and int(row.get("provider_unknown_calls") or 0) == 0
            and int(row.get("provider_ms") or 0) > 0
        ):
            attributable.append(row)
    split = {
        "decisions": len(attributable),
        "unattributed_decisions": len(recorded) - len(attributable),
        "provider_ms": latency_summary([int(row["provider_ms"]) for row in attributable]),
        "agency_ms": latency_summary(
            [max(0, int(row["latency_ms"]) - int(row["provider_ms"])) for row in attributable]
        ),
        "calls_per_decision": (
            round(
                sum(int(row.get("provider_calls") or 0) for row in attributable)
                / len(attributable),
                2,
            )
            if attributable
            else 0.0
        ),
    }
    buckets: dict[str, list[int]] = {}
    for row in recorded:
        buckets.setdefault(str(row["source"] or "unknown"), []).append(int(row["latency_ms"]))
    return {
        "budget_ms": budget,
        "over_budget": bool(values) and overall["p95_ms"] > budget,
        "overall": overall,
        "split": split,
        "by_source": {name: latency_summary(bucket) for name, bucket in sorted(buckets.items())},
        "slowest": sorted(
            recorded,
            key=lambda row: int(row["latency_ms"]),
            reverse=True,
        )[:5],
    }
