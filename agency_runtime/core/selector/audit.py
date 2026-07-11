"""Audit logging — record routing decisions and events to SQLite."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from agency_runtime.core.store.sqlite import Store

logger = logging.getLogger("agency_runtime.core.selector.audit")


def log_routing(
    store: Store,
    *,
    session_id: str,
    user_message: str,
    refined_query: str,
    selected_ids: list[str],
    confidence: float,
    latency_ms: int,
    status: str,
    provider: str = "",
    model: str = "",
    error: str = "",
) -> None:
    """Record a routing decision in the audit store."""
    try:
        store.record_import_event(
            event_type="routing",
            agent_slug=", ".join(selected_ids) if selected_ids else "none",
            detail=json.dumps({
                "session_id": session_id,
                "user_message": user_message[:500],
                "refined_query": refined_query[:500],
                "selected_ids": selected_ids,
                "confidence": confidence,
                "latency_ms": latency_ms,
                "status": status,
                "provider": provider,
                "model": model,
                "error": error,
                "ts": datetime.now(timezone.utc).isoformat(),
            }),
        )
    except Exception as exc:
        logger.debug("could not log routing event: %s", exc)
