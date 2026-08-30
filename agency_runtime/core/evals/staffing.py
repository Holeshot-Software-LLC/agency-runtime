"""AR-253 staffing eval: does a configured Agency actually staff a turn?

The routing eval asks whether the right specialist *would* be chosen. This one
asks a narrower and more operational question: over one fixed set of asks, how
many selection-requiring turns come back with a usable inference-owned staffing
decision, how long the decision takes, and how many recruiter calls it costs.

Three rules shape the accounting, and all three come from AR-253:

* **A provider arm that never produced a decision is not a staffing loss.** An
  invalid, timed-out, or malformed provider response is reported in its own
  bucket and left out of the rate denominator. Scoring it as a miss would make
  a broken provider look like bad selection.
* **One successful recruiter call per turn.** Bounded repair attempts around a
  failure are expected; a second *successful* staffing decision for the same
  ask is not.
* **The cold budget does not move.** 15,000 ms, unchanged, measured on the
  first ask of a run.

Host-artifact correlation is part of the manifest and is honestly reported as
unavailable when the eval runs without a host: this harness measures the
decision, and only a host artifact can prove delivery.
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any, Final

from agency_runtime.core.evals.data.routing_v1 import ROUTING_CASES

VERSION: Final[str] = "staffing-v1"
SCHEMA: Final[str] = "agency.staffing-eval.v1"

#: AR-253 keeps the cold control fixed; never trade it for latency.
COLD_BUDGET_MS: Final[int] = 15_000
#: At least this share of valid selection-requiring asks must be staffed.
MINIMUM_STAFFING_RATE: Final[float] = 0.95
#: One *successful* recruiter/staffing decision per turn.
MAXIMUM_SUCCESSFUL_RECRUITER_CALLS: Final[int] = 1

MAX_TEAM_CARDS: Final[int] = 3

_VALID_ATTEMPT_STATUSES: Final[frozenset[str]] = frozenset({"applied", "failed", "skipped"})


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def selection_requiring_asks() -> list[dict[str, Any]]:
    """The fixed asks that genuinely need a specialist chosen."""

    asks: list[dict[str, Any]] = []
    for case in ROUTING_CASES:
        required = case.get("required")
        if not isinstance(required, Sequence) or isinstance(required, (str, bytes)):
            continue
        if not required:
            continue
        asks.append(
            {
                "id": str(case.get("id") or ""),
                "query": str(case.get("query") or ""),
                "required": [str(item) for item in required],
            }
        )
    return asks


def _candidate_identity(catalog: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Name the exact candidate universe a decision was made against."""

    slugs = sorted({str(entry.get("id") or entry.get("slug") or "") for entry in catalog})
    return {
        "candidate_count": len(catalog),
        "candidate_digest": _digest("\n".join(slugs)),
    }


def _successful_recruiter_calls(attempts: object) -> int:
    if not isinstance(attempts, Sequence) or isinstance(attempts, (str, bytes)):
        return 0
    return sum(
        1
        for attempt in attempts
        if isinstance(attempt, Mapping) and attempt.get("status") == "applied"
    )


def _arm_is_valid(result: Mapping[str, Any]) -> bool:
    """Did the provider produce a decision at all?

    A provider that timed out, answered malformed, or was never configured did
    not lose a staffing race; it never entered one.
    """

    if result.get("inference_configured") is not True:
        return False
    if result.get("inference_attempted") is not True:
        return False
    attempts = result.get("provider_attempts")
    if not isinstance(attempts, Sequence) or isinstance(attempts, (str, bytes)):
        return False
    if any(
        not isinstance(attempt, Mapping) or attempt.get("status") not in _VALID_ATTEMPT_STATUSES
        for attempt in attempts
    ):
        return False
    return bool(attempts)


def _selected_cards(result: Mapping[str, Any]) -> list[str]:
    selected = result.get("selected_ids")
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes)):
        return []
    return [str(item) for item in selected if item]


def _evaluate_ask(
    ask: Mapping[str, Any],
    *,
    catalog: Sequence[Mapping[str, Any]],
    config: Any,
    judge: Any,
) -> dict[str, Any]:
    identity = _candidate_identity(catalog)
    started = time.perf_counter()
    error = ""
    result: dict[str, Any] = {}
    try:
        raw = judge(
            str(ask["query"]),
            list(catalog),
            config=config,
            max_selected=MAX_TEAM_CARDS,
            candidate_scope="complete",
        )
        result = dict(raw) if isinstance(raw, Mapping) else {}
    except Exception as exc:  # the provider transport is allowed to fail
        error = f"{type(exc).__name__}"
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    valid = bool(result) and _arm_is_valid(result)
    cards = _selected_cards(result)
    staffed = bool(valid and cards and result.get("status") == "applied")
    return {
        "id": str(ask["id"]),
        "query_digest": _digest(str(ask["query"])),
        **identity,
        "stage_latency_ms": elapsed_ms,
        "reported_latency_ms": result.get("latency_ms"),
        "decision_status": str(result.get("status") or ""),
        "inference_mode": str(result.get("inference_mode") or ""),
        "decision_valid": valid,
        "selected_cards": cards,
        "required_cards": list(ask["required"]),
        "successful_recruiter_calls": _successful_recruiter_calls(
            result.get("provider_attempts"),
        ),
        # Only a host artifact can prove a card reached a turn. This harness
        # measures the decision, so the correlation is reported unavailable
        # rather than assumed.
        "host_artifact_correlation": "unavailable",
        "staffed": staffed,
        "error": error,
    }


def _gates(metrics: Mapping[str, Any]) -> list[dict[str, Any]]:
    rate = float(metrics["staffing_rate"])
    calls = int(metrics["max_successful_recruiter_calls"])
    cold = int(metrics["cold_latency_ms"])
    return [
        {
            "name": "staffing_rate",
            "threshold": MINIMUM_STAFFING_RATE,
            "observed": rate,
            "passed": rate >= MINIMUM_STAFFING_RATE,
        },
        {
            "name": "successful_recruiter_calls_per_turn",
            "threshold": MAXIMUM_SUCCESSFUL_RECRUITER_CALLS,
            "observed": calls,
            "passed": calls <= MAXIMUM_SUCCESSFUL_RECRUITER_CALLS,
        },
        {
            "name": "cold_budget_ms",
            "threshold": COLD_BUDGET_MS,
            "observed": cold,
            "passed": cold <= COLD_BUDGET_MS,
        },
    ]


def run_staffing_eval(
    *,
    asks: Sequence[Mapping[str, Any]] | None = None,
    catalog: Sequence[Mapping[str, Any]] | None = None,
    config: Any = None,
    judge: Any = None,
    include_details: bool = True,
) -> dict[str, Any]:
    """Measure staffing over the fixed ask set and report one manifest."""

    if judge is None:
        from agency_runtime.core.selector.judge import query_judge

        judge = query_judge
    if config is None:
        from agency_runtime.core.config import load_config

        config = load_config()
    if catalog is None:
        from agency_runtime.core.roster.bundled import bundled_roster

        catalog = [dict(agent) for agent in bundled_roster()]
    selected_asks = list(asks) if asks is not None else selection_requiring_asks()

    results = [
        _evaluate_ask(ask, catalog=catalog, config=config, judge=judge) for ask in selected_asks
    ]
    valid = [row for row in results if row["decision_valid"]]
    invalid = [row for row in results if not row["decision_valid"]]
    staffed = [row for row in valid if row["staffed"]]
    metrics = {
        "asks": len(results),
        "valid_arms": len(valid),
        # Reported, never scored: a provider that produced no decision did not
        # lose a staffing race.
        "invalid_arms": len(invalid),
        "staffed": len(staffed),
        "staffing_rate": (len(staffed) / len(valid)) if valid else 0.0,
        "max_successful_recruiter_calls": max(
            (int(row["successful_recruiter_calls"]) for row in results),
            default=0,
        ),
        "cold_latency_ms": int(results[0]["stage_latency_ms"]) if results else 0,
        "host_artifact_correlation": "unavailable",
    }
    gates = _gates(metrics)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "suite": "staffing",
        "version": VERSION,
        "passed": all(gate["passed"] for gate in gates) and bool(valid),
        "metrics": metrics,
        "gates": gates,
        "invalid_arm_ids": sorted(row["id"] for row in invalid),
    }
    if include_details:
        report["asks_detail"] = results
    return report


__all__ = [
    "COLD_BUDGET_MS",
    "MAXIMUM_SUCCESSFUL_RECRUITER_CALLS",
    "MINIMUM_STAFFING_RATE",
    "SCHEMA",
    "VERSION",
    "run_staffing_eval",
    "selection_requiring_asks",
]
