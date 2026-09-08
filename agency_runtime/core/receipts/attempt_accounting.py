"""Content-free provider-chain accounting, separate from stage/list order."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from agency_runtime.core.receipts.ingress import MAX_RECEIPT_FALLBACKS

_MAX_CHAIN_INDEX = 1_000_000
# Kept equal to the failure receipt's closed stage vocabulary by regression;
# importing the preflight facade here would make receipt projection recursive.
PROVIDER_ATTEMPT_STAGES = frozenset(
    {
        "combined",
        "planner",
        "subject",
        "recruiter",
        "recall_embedding",
        "recall_reranker",
        "hiring",
        "hiring-critic",
        "hiring-repair",
        "hiring-repair-critic",
        "security_review",
        "safety_repair",
        "critic",
        "selector",
        "unknown",
    }
)


@dataclass(slots=True)
class ProviderChainAccounting:
    """One chain invocation; semantic retries share their configured entry."""

    _invoked_entries: set[int] = field(default_factory=set)
    _unknown_entries: set[int] = field(default_factory=set)

    def observe(self, index: int, *, call_attempted: bool | None) -> dict[str, Any]:
        prior = len(self._invoked_entries - {index})
        if call_attempted is True:
            self._invoked_entries.add(index)
            self._unknown_entries.discard(index)
        elif call_attempted is None and index not in self._invoked_entries:
            self._unknown_entries.add(index)
        return {
            "metadata_version": 1,
            "provider_chain_index": index,
            "provider_call_attempted": call_attempted,
            "provider_fallback_count": (
                prior if call_attempted is True and not self._unknown_entries - {index} else None
            ),
        }


def project_provider_attempt_metadata(value: object) -> dict[str, Any]:
    """Keep only explicit versioned accounting; malformed/legacy stays absent."""

    read = value.get if isinstance(value, Mapping) else lambda key: getattr(value, key, None)
    version = read("metadata_version")
    stage = read("stage")
    index = read("provider_chain_index")
    attempted = read("provider_call_attempted")
    count = read("provider_fallback_count")
    if (
        type(version) is not int
        or version != 1
        or not isinstance(stage, str)
        or stage not in PROVIDER_ATTEMPT_STAGES
        or type(index) is not int
        or not 0 <= index <= _MAX_CHAIN_INDEX
        or (attempted is not None and type(attempted) is not bool)
    ):
        return {}
    if attempted is True:
        if count is not None and (
            type(count) is not int or not 0 <= count <= min(index, MAX_RECEIPT_FALLBACKS)
        ):
            return {}
    elif count is not None:
        return {}
    return {
        "metadata_version": version,
        "stage": stage,
        "provider_chain_index": index,
        "provider_call_attempted": attempted,
        "provider_fallback_count": count,
    }


def provider_fallback_count(value: object) -> int | None:
    """Return the stamped count, never an inferred count from flattened order."""

    return project_provider_attempt_metadata(value).get("provider_fallback_count")
