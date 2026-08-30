"""Read-only Store projection for retained specialist-selection evidence."""

from __future__ import annotations

from itertools import islice
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.selection_distribution import specialist_selection_distribution

MAX_SELECTION_BEARING_DECISION_SCAN = 10_000


class SelectionDistributionStoreMixin:
    """Provide a bounded aggregate of every retained routing selection."""

    def specialist_selection_distribution(self) -> dict[str, Any]:
        """Summarize all retained selected-specialist evidence in this Store.

        ``count_enabled_roster`` is the authoritative effective-roster API: it
        is bound to this Store's current configuration and excludes agents
        disabled by that policy. The newest 10,000 retained decisions that
        contain selections are scanned; the explicit truncation field prevents
        a bounded observation from being mistaken for full retained history.
        """

        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT selected_ids FROM routing_decisions "
                "WHERE selected_ids IS NOT NULL AND selected_ids <> '[]' "
                "ORDER BY created_at DESC, id DESC LIMIT ?",
                (MAX_SELECTION_BEARING_DECISION_SCAN + 1,),
            )
            iterator = iter(rows)
            selections = (
                _stored_selected_ids(row["selected_ids"])
                for row in islice(iterator, MAX_SELECTION_BEARING_DECISION_SCAN)
            )
            projection = specialist_selection_distribution(
                selections,
                active_roster_size=self.count_enabled_roster(),
            )
            return {
                **projection,
                "selection_bearing_decision_scan_limit": MAX_SELECTION_BEARING_DECISION_SCAN,
                "selection_bearing_decision_scan_truncated": next(iterator, None) is not None,
            }
        finally:
            conn.close()


def _stored_selected_ids(value: object) -> tuple[str, ...]:
    """Decode the Store-owned selected-id projection without widening it."""

    if not isinstance(value, str):
        return ()
    try:
        parsed = safe_load_bounded_json(
            value,
            maximum_bytes=4 * 1024,
            maximum_depth=2,
            maximum_nodes=32,
        )
    except ValueError as exc:
        raise RuntimeError("stored routing selection evidence is invalid") from exc
    if not isinstance(parsed, list):
        raise RuntimeError("stored routing selection evidence is invalid")
    return tuple(item for item in parsed if isinstance(item, str))
