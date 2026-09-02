"""Content-free projection of the staffing-verdict window (AR-353).

The intermittent staffing-verdict window was described from memory and from
per-session receipts. This projects one bounded store read into the numbers the
issue asks for -- turns started, turns that closed ``preflight_failed``, the
failure rate, and which stage and codes dominate -- per host, so the window can
be measured on any box that keeps a Store. Every value is a count over a closed
vocabulary (run statuses, provider stages, reason codes); no prompt, response,
or provider identity is carried.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any, Final

from agency_runtime.core.host_capabilities import EXECUTION_HOSTS
from agency_runtime.core.routing_latency import latency_summary
from agency_runtime.core.store.turn_window import (
    MAX_TURN_WINDOW_RECEIPTS,
    bounded_turn_window_limit,
)

DEFAULT_STAFFING_WINDOW_HOURS: Final[int] = 24
MAX_STAFFING_WINDOW_HOURS: Final[int] = 24 * 30
DEFAULT_STAFFING_WINDOW_RECEIPTS: Final[int] = 500
MAX_STAFFING_WINDOW_RECEIPTS: Final[int] = MAX_TURN_WINDOW_RECEIPTS
FAILED_TURN_STATUS: Final[str] = "preflight_failed"
APPLIED_ATTEMPT_STATUS: Final[str] = "applied"
VERDICT_AFTER_APPLIED_ATTEMPTS: Final[str] = "verdict_after_applied_attempts"
NO_PROVIDER_ATTEMPT: Final[str] = "no_provider_attempt"
# Timing keys a provider attempt would carry if per-attempt latency were ever
# recorded. None is today (measured 2026-09-01); the projection checks rather
# than assumes, so a later receipt schema starts reporting without a code change.
_ATTEMPT_TIMING_KEYS: Final[tuple[str, ...]] = ("duration_ms", "latency_ms", "elapsed_ms")
_RANKED_LIMIT: Final[int] = 12


def store_timestamp(moment: datetime) -> str:
    """Render one instant exactly as the store clock does (milliseconds, ``+00:00``)."""

    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    utc = moment.astimezone(timezone.utc)
    return f"{utc.strftime('%Y-%m-%dT%H:%M:%S')}.{utc.microsecond // 1000:03d}000+00:00"


def staffing_window_cutoff(
    *,
    since: str = "",
    hours: int | None = None,
    now: datetime | None = None,
) -> str:
    """Resolve the window start from an ISO-8601 instant or a bounded hour count.

    A naive ``since`` is read as UTC, which is what every store timestamp is.
    The two forms are exclusive so a window is never described two ways at once.
    """

    if since and hours is not None:
        raise ValueError("staffing window takes --since or --hours, not both")
    current = now if now is not None else datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    if since:
        text = str(since).strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("staffing window --since must be an ISO-8601 instant") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        if parsed > current:
            raise ValueError("staffing window --since is in the future")
        return store_timestamp(parsed)
    span = DEFAULT_STAFFING_WINDOW_HOURS if hours is None else hours
    if (
        isinstance(span, bool)
        or not isinstance(span, int)
        or not 1 <= span <= MAX_STAFFING_WINDOW_HOURS
    ):
        raise ValueError(f"staffing window hours must be between 1 and {MAX_STAFFING_WINDOW_HOURS}")
    return store_timestamp(current - timedelta(hours=span))


def bounded_staffing_window_limit(limit: object) -> int:
    """Validate the public receipt window."""

    return bounded_turn_window_limit(
        limit,
        maximum=MAX_STAFFING_WINDOW_RECEIPTS,
        field="staffing window limit",
    )


def _ranked(counter: Counter[str]) -> list[dict[str, Any]]:
    """Rank a closed-vocabulary count as a list, which survives sorted JSON keys."""

    ordered = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [{"value": value, "count": count} for value, count in ordered[:_RANKED_LIMIT]]


def _dominant(counter: Counter[str]) -> str:
    ranked = _ranked(counter)
    return str(ranked[0]["value"]) if ranked else ""


def _attempts(receipt: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = receipt.get("provider_attempts")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def _codes(receipt: Mapping[str, Any], field: str) -> list[str]:
    raw = receipt.get(field)
    if not isinstance(raw, list):
        return []
    return [code for code in raw if isinstance(code, str)]


def failing_stage(attempts: Sequence[Mapping[str, Any]]) -> str:
    """Name the first provider stage whose attempt did not apply.

    A receipt whose every attempt applied still failed: the recruiter or critic
    returned a well-formed verdict that rejected the team. That is a different
    finding from a provider that returned nothing usable, so it is named as its
    own bucket rather than folded into a stage.
    """

    for attempt in attempts:
        if str(attempt.get("status") or "") != APPLIED_ATTEMPT_STATUS:
            return str(attempt.get("stage") or "unknown")
    return VERDICT_AFTER_APPLIED_ATTEMPTS if attempts else NO_PROVIDER_ATTEMPT


def last_stage(attempts: Sequence[Mapping[str, Any]]) -> str:
    """Name how far the inference pipeline got before the turn failed."""

    if not attempts:
        return NO_PROVIDER_ATTEMPT
    return str(attempts[-1].get("stage") or "unknown")


def _attempt_timings(receipts: Sequence[Mapping[str, Any]]) -> list[int]:
    values: list[int] = []
    for receipt in receipts:
        for attempt in _attempts(receipt):
            for key in _ATTEMPT_TIMING_KEYS:
                value = attempt.get(key)
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    continue
                if value > 0:
                    values.append(int(value))
                    break
    return values


def _latency(receipts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    timings = _attempt_timings(receipts)
    if timings:
        return {
            "recorded": True,
            "source": "provider_attempt_timing",
            **latency_summary(timings),
        }
    return {
        "recorded": False,
        "note": (
            "preflight failure receipts carry no per-attempt timing: an attempt "
            "records stage, provider and model identity, status, reason_code, and "
            "validation codes only. Successful routes record "
            "routing_decisions.latency_ms; see `agency evidence latency`."
        ),
    }


def _validation_codes(stage: str, attempt: Mapping[str, Any]) -> list[str]:
    """Flatten the recruiter/critic validation vocabularies one attempt carries."""

    codes: list[str] = []
    raw_codes = attempt.get("validation_reason_codes")
    if isinstance(raw_codes, list):
        codes.extend(f"{stage}:{code}" for code in raw_codes if isinstance(code, str))
    raw_failures = attempt.get("validation_failures")
    if isinstance(raw_failures, list):
        codes.extend(
            f"{stage}:{failure['reason_code']}"
            for failure in raw_failures
            if isinstance(failure, Mapping) and isinstance(failure.get("reason_code"), str)
        )
    return codes


def _host_projection(
    turn_counts: Counter[str],
    receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    started = sum(turn_counts.values())
    failed = int(turn_counts.get(FAILED_TURN_STATUS, 0))
    reason_codes: Counter[str] = Counter(str(item.get("reason_code") or "") for item in receipts)
    staffing: Counter[str] = Counter()
    hiring: Counter[str] = Counter()
    eligibility: Counter[str] = Counter()
    failing: Counter[str] = Counter()
    last: Counter[str] = Counter()
    outcomes: dict[str, Counter[str]] = {}
    flat_outcomes: Counter[str] = Counter()
    validation: Counter[str] = Counter()
    for receipt in receipts:
        staffing.update(_codes(receipt, "staffing_reason_codes"))
        hiring.update(_codes(receipt, "hiring_reason_codes"))
        eligibility.update(_codes(receipt, "eligibility_reason_codes"))
        attempts = _attempts(receipt)
        failing[failing_stage(attempts)] += 1
        last[last_stage(attempts)] += 1
        for attempt in attempts:
            stage = str(attempt.get("stage") or "unknown")
            outcome = f"{attempt.get('status') or 'unknown'}/{attempt.get('reason_code') or ''}"
            outcomes.setdefault(stage, Counter())[outcome] += 1
            flat_outcomes[f"{stage} {outcome}"] += 1
            validation.update(_validation_codes(stage, attempt))
    return {
        "turns_started": started,
        "turns_preflight_failed": failed,
        "failure_rate": round(failed / started, 4) if started else None,
        "turn_statuses": dict(sorted(turn_counts.items())),
        "receipts": len(receipts),
        "reason_codes": _ranked(reason_codes),
        "staffing_reason_codes": _ranked(staffing),
        "hiring_reason_codes": _ranked(hiring),
        "eligibility_reason_codes": _ranked(eligibility),
        "failing_stage": _ranked(failing),
        "last_stage": _ranked(last),
        "provider_outcomes": {
            stage: _ranked(counter) for stage, counter in sorted(outcomes.items())
        },
        "validation_reason_codes": _ranked(validation),
        "dominant": {
            "failing_stage": _dominant(failing),
            "last_stage": _dominant(last),
            "reason_code": _dominant(reason_codes),
            "staffing_reason_code": _dominant(staffing),
            "provider_outcome": _dominant(flat_outcomes),
        },
    }


def staffing_window_projection(window: Mapping[str, Any], *, now: str = "") -> dict[str, Any]:
    """Project one store window into per-host rates and dominant stages/codes.

    Turns are grouped by the host that started them; receipts by the host on
    the receipt. Every execution host appears even with zero turns, so an
    absent host reads as "no turns", not as "not measured".
    """

    host_filter = str(window.get("host") or "")
    turns_by_host: dict[str, Counter[str]] = {}
    for row in window.get("turns") or ():
        if not isinstance(row, Mapping):
            continue
        host = str(row.get("host") or "unknown")
        turns_by_host.setdefault(host, Counter())[str(row.get("status") or "")] += int(
            row.get("count") or 0
        )
    receipts = [item for item in window.get("receipts") or () if isinstance(item, Mapping)]
    receipts_by_host: dict[str, list[Mapping[str, Any]]] = {}
    for receipt in receipts:
        receipts_by_host.setdefault(str(receipt.get("host") or "unknown"), []).append(receipt)
    if host_filter:
        hosts = {host_filter}
    else:
        hosts = set(EXECUTION_HOSTS) | set(turns_by_host) | set(receipts_by_host)
    all_turns: Counter[str] = Counter()
    for host in hosts:
        all_turns.update(turns_by_host.get(host, Counter()))
    return {
        "window": {
            "kind": "turns_started_and_failure_receipts_since_cutoff",
            "cutoff": str(window.get("cutoff") or ""),
            "now": now,
            "host": host_filter or None,
            "receipt_limit": int(window.get("limit") or 0),
            "receipts_returned": len(receipts),
            "receipts_truncated": bool(window.get("receipts_truncated")),
        },
        "totals": _host_projection(all_turns, receipts),
        "hosts": {
            host: _host_projection(
                turns_by_host.get(host, Counter()),
                receipts_by_host.get(host, []),
            )
            for host in sorted(hosts)
        },
        "latency": _latency(receipts),
    }


__all__ = [
    "DEFAULT_STAFFING_WINDOW_HOURS",
    "DEFAULT_STAFFING_WINDOW_RECEIPTS",
    "FAILED_TURN_STATUS",
    "MAX_STAFFING_WINDOW_HOURS",
    "MAX_STAFFING_WINDOW_RECEIPTS",
    "NO_PROVIDER_ATTEMPT",
    "VERDICT_AFTER_APPLIED_ATTEMPTS",
    "bounded_staffing_window_limit",
    "failing_stage",
    "last_stage",
    "staffing_window_cutoff",
    "staffing_window_projection",
    "store_timestamp",
]
