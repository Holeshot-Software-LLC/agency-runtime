"""Read-only Store projection of the keys a child launch can be joined by.

A harness-spawned child's artifact can be tied back to its routing decision
three different ways, and they are complementary rather than redundant, so this
returns the raw material for all three rather than picking one:

* the decision's own id, which a delivered v6 envelope carries;
* ``(session_id, query_hash)``, which matches the SHA-256 of the assignment the
  host recorded before delivery appended anything;
* the stored ``context_fingerprint``, which a reader can recompute from the
  host's launch identity once it knows the parent trace.

Nothing here writes, consumes a delivery capability, or mints a receipt. An
outcome derived from these rows is a diagnostic; proof of delivery remains the
in-lifetime collector's alone under ADR-0156.
"""

from __future__ import annotations

from typing import Any

MAX_CHILD_LAUNCH_DECISION_SCAN = 10_000


class ChildLaunchJoinStoreMixin:
    """Expose the bounded decision rows a child-launch resolver needs."""

    def child_launch_join_rows(
        self,
        *,
        limit: int = MAX_CHILD_LAUNCH_DECISION_SCAN,
    ) -> dict[str, Any]:
        """Return the newest retained decisions with every join key intact.

        The scan is bounded and its truncation is stated, so a partial read is
        never mistaken for the full retained history -- the same reason a
        resolver built on this must report unmatched launches rather than
        dropping them.
        """

        bounded = max(1, min(int(limit), MAX_CHILD_LAUNCH_DECISION_SCAN))
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT id, session_id, trace_id, query_hash, status, source, "
                "context_fingerprint, created_at FROM routing_decisions "
                "ORDER BY created_at DESC, id DESC LIMIT ?",
                (bounded + 1,),
            ).fetchall()
        finally:
            conn.close()
        truncated = len(rows) > bounded
        return {
            "scan_limit": bounded,
            "scan_truncated": truncated,
            "decisions": [
                {
                    "id": str(row["id"] or ""),
                    "session_id": str(row["session_id"] or ""),
                    "trace_id": str(row["trace_id"] or ""),
                    "query_hash": str(row["query_hash"] or ""),
                    "status": str(row["status"] or ""),
                    "source": str(row["source"] or ""),
                    "context_fingerprint": str(row["context_fingerprint"] or ""),
                    "created_at": str(row["created_at"] or ""),
                }
                for row in rows[:bounded]
            ],
        }


__all__ = ["MAX_CHILD_LAUNCH_DECISION_SCAN", "ChildLaunchJoinStoreMixin"]
