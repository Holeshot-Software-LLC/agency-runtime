"""Agency Runtime Control Plane.

A portable control plane for specialist routing, roster governance,
delegation, and model/run observability.

Usage:
    from agency_runtime import AgencyRuntime

    runtime = AgencyRuntime()
    routing = runtime.route("session-1", "review this PR")
    print(routing["selected_ids"])
"""

from __future__ import annotations

from typing import Any

from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.selector.pipeline import (
    route,
    detect_work_units,
    build_routing_context,
    route_and_build_context,
    is_trivial,
)


class AgencyRuntime:
    """Main entry point for the Agency Runtime Control Plane.

    Usage:
        runtime = AgencyRuntime()
        routing = runtime.route("session-1", "review this pull request")
    """

    def __init__(self, db_path: str | None = None):
        self.store = Store(db_path) if db_path else Store()

    def route(self, session_id: str, user_message: str) -> dict[str, Any]:
        """Route a user message to specialist agents."""
        catalog = self.store.get_active_roster_as_catalog()
        return route(session_id, user_message, catalog)

    def route_with_context(self, session_id: str, user_message: str) -> str | None:
        """Route and return the preflight context string."""
        catalog = self.store.get_active_roster_as_catalog()
        return route_and_build_context(session_id, user_message, catalog)

    def detect_work_units(self, message: str) -> dict[str, Any]:
        """Detect independent work units in a message."""
        return detect_work_units(message)

    def get_roster(self) -> list[dict[str, Any]]:
        """Return the active agent roster."""
        return self.store.get_active_roster()

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search the active roster."""
        from agency_runtime.core.selector.candidate_narrow import pre_narrow
        catalog = self.store.get_active_roster_as_catalog()
        candidates, _ = pre_narrow(query, catalog, limit=limit)
        return candidates

    def record_skill(self, session_id: str, skill_name: str) -> None:
        """Record a skill load for the session."""
        self.store.record_skill_loaded(session_id, skill_name)

    def record_specialist(self, session_id: str, agent_slug: str) -> None:
        """Record a specialist load for the session."""
        self.store.record_specialist_loaded(session_id, agent_slug)

    def record_model_receipt(self, **kwargs) -> str:
        """Record a model receipt (what actually ran)."""
        return self.store.record_model_receipt(**kwargs)

    def record_delegation(self, **kwargs) -> str:
        """Record a delegation event."""
        return self.store.record_delegation(**kwargs)

    def finalize_header(self, draft_text: str, session_id: str = "", model: str = "") -> str:
        """Finalize the agency header on a draft response."""
        from agency_runtime.core.header.contract import finalize_header
        return finalize_header(draft_text, session_id=session_id, store=self.store, model=model)


__version__ = "0.1.0"
