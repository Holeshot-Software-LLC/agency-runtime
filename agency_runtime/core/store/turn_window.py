"""Bounded windows over recent turns for operator measurements (AR-353, AR-355).

Two reads, both read-only and both bounded before any row is fetched:

* the staffing window -- how many turns each host started since an instant and
  how many of them closed ``preflight_failed``, beside the newest failure
  receipts in that window, so the intermittent staffing-verdict window can be
  measured instead of described;
* the newest ready recipes -- content-free specialist references and routing
  receipts, replayed by the context-budget audit to size a staffed capsule from
  exact immutable prompt versions rather than from a guess.

Store timestamps are canonical UTC strings written by one clock, so ``>=`` on
the text is ``>=`` on time; the cutoff is validated to that exact shape.
"""

from __future__ import annotations

import re
from typing import Any, Final

from agency_runtime.core.host_capabilities import EXECUTION_HOSTS
from agency_runtime.core.store.preflight import (
    _decode_preflight_failure_receipt,
    _decode_preflight_recipe,
)

MAX_TURN_WINDOW_RECEIPTS: Final[int] = 2_000
MAX_TURN_WINDOW_RECIPES: Final[int] = 500
_STORE_CUTOFF: Final[re.Pattern[str]] = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?\+00:00$"
)


def bounded_turn_window_limit(limit: object, *, maximum: int, field: str) -> int:
    """Reject anything but a positive integer within the window's hard ceiling."""

    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= maximum:
        raise ValueError(f"{field} must be between 1 and {maximum}")
    return limit


def turn_window_host(host: object) -> str:
    """Normalize an optional host filter; a typo must not read as an empty, green window."""

    normalized = str(host or "").strip().casefold()
    if normalized and normalized not in EXECUTION_HOSTS:
        raise ValueError("turn window host is unsupported")
    return normalized


def turn_window_cutoff(cutoff: object) -> str:
    """Accept only a canonical UTC store timestamp so text order is time order."""

    value = str(cutoff or "").strip()
    if _STORE_CUTOFF.fullmatch(value) is None:
        raise ValueError("turn window cutoff must be a canonical UTC store timestamp")
    return value


class TurnWindowStoreMixin:
    """Bounded, read-only turn windows for the evidence commands."""

    def get_staffing_window(
        self,
        *,
        cutoff: str,
        host: str = "",
        limit: int = 500,
    ) -> dict[str, Any]:
        """Return per-host turn counts and the newest failure receipts since ``cutoff``.

        Turns are counted by ``runs.started_at`` and receipts are read by
        ``preflight_failure_receipts.recorded_at``: a turn belongs to the window
        it started in, and a receipt to the window it was written in, so the two
        can disagree by at most the turns straddling the cutoff. The count is an
        aggregate and cannot grow with history; the receipt read is bounded and
        says whether older receipts inside the window were left unread.
        """

        normalized_cutoff = turn_window_cutoff(cutoff)
        normalized_host = turn_window_host(host)
        bounded = bounded_turn_window_limit(
            limit,
            maximum=MAX_TURN_WINDOW_RECEIPTS,
            field="staffing window limit",
        )
        host_clause = " AND host = ?" if normalized_host else ""
        host_parameters: tuple[str, ...] = (normalized_host,) if normalized_host else ()
        conn = self._connect()
        try:
            turn_rows = conn.execute(
                "SELECT host, status, COUNT(*) AS count FROM runs "  # nosec B608
                f"WHERE started_at >= ?{host_clause} "
                "GROUP BY host, status ORDER BY host, status",
                (normalized_cutoff, *host_parameters),
            ).fetchall()
            receipt_rows = conn.execute(
                "SELECT id, session_id, trace_id, host, stage, reason_code, invariant_code, "
                "exception_category, provider_attempts, staffing_reason_codes, "
                "hiring_reason_codes, eligibility_reason_codes, recorded_at "
                "FROM preflight_failure_receipts "  # nosec B608
                f"WHERE recorded_at >= ?{host_clause} "
                "ORDER BY recorded_at DESC, id DESC LIMIT ?",
                (normalized_cutoff, *host_parameters, bounded + 1),
            ).fetchall()
        finally:
            conn.close()
        receipts = [
            {**dict(row), **_decode_preflight_failure_receipt(row)}
            for row in receipt_rows[:bounded]
        ]
        return {
            "cutoff": normalized_cutoff,
            "host": normalized_host,
            "limit": bounded,
            "turns": [
                {
                    "host": str(row["host"] or ""),
                    "status": str(row["status"] or ""),
                    "count": int(row["count"] or 0),
                }
                for row in turn_rows
            ],
            "receipts": receipts,
            "receipts_truncated": len(receipt_rows) > bounded,
        }

    def get_recent_ready_recipes(
        self,
        *,
        host: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return the newest ready recipes, decoded, for capsule-size measurement.

        A ready recipe is content-free (specialist references and a routing
        receipt); the caller replays prompt bodies from exact immutable versions.
        A recipe that no longer validates is returned as ``None`` so the caller
        can count it instead of the read failing on one stale row.
        """

        normalized_host = turn_window_host(host)
        bounded = bounded_turn_window_limit(
            limit,
            maximum=MAX_TURN_WINDOW_RECIPES,
            field="ready recipe limit",
        )
        host_clause = " AND host = ?" if normalized_host else ""
        host_parameters: tuple[str, ...] = (normalized_host,) if normalized_host else ()
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT session_id, trace_id, host, started_at, status, "
                "LENGTH(preflight_result) AS recipe_chars, preflight_result FROM runs "  # nosec B608
                f"WHERE preflight_state = 'ready' AND preflight_result <> ''{host_clause} "
                "ORDER BY started_at DESC, id DESC LIMIT ?",
                (*host_parameters, bounded),
            ).fetchall()
        finally:
            conn.close()
        recipes: list[dict[str, Any]] = []
        for row in rows:
            session_id = str(row["session_id"] or "")
            trace_id = str(row["trace_id"] or "")
            recipes.append(
                {
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "host": str(row["host"] or ""),
                    "started_at": str(row["started_at"] or ""),
                    "status": str(row["status"] or ""),
                    "recipe_chars": int(row["recipe_chars"] or 0),
                    "recipe": _decode_preflight_recipe(
                        row["preflight_result"],
                        session_id=session_id,
                        trace_id=trace_id,
                    ),
                }
            )
        return recipes


__all__ = [
    "MAX_TURN_WINDOW_RECEIPTS",
    "MAX_TURN_WINDOW_RECIPES",
    "TurnWindowStoreMixin",
    "bounded_turn_window_limit",
    "turn_window_cutoff",
    "turn_window_host",
]
