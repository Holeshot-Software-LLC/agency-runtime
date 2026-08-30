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

import os
from typing import Any
from uuid import uuid4


def _bypassed_routing(trace_id: str = "") -> dict[str, Any]:
    """Return the stable, work-free projection used while Agency is off."""

    return {
        "runtime_enabled": False,
        "bypassed": True,
        "trace_id": str(trace_id or ""),
        "selected_ids": [],
        "semantic_ids": [],
        "confidence": 0.0,
        "latency_ms": 0,
        "status": "bypassed",
        "source": "master_control",
        "work_units": {
            "count": 0,
            "confidence": "none",
            "source": "master_control",
            "units": [],
            "delegate": False,
        },
    }


def _current_platform() -> str:
    """Return the platform token used by native-host capability receipts."""

    return "windows" if os.name == "nt" else "linux"


class AgencyRuntime:
    """Main entry point for the Agency Runtime Control Plane.

    Usage:
        runtime = AgencyRuntime()
        routing = runtime.route("session-1", "review this pull request")
    """

    def __init__(self, db_path: str | None = None):
        # Keep construction work-free as well as imports cheap. The durable
        # master switch must be observable before SQLite is opened or migrated.
        self._db_path = db_path
        self._store: Any | None = None

    @property
    def store(self) -> Any:
        """Open the low-level Store on explicit access or enabled runtime work.

        Direct access is an intentional administrative escape hatch. Public
        routing/evidence methods never evaluate this property while Agency is
        globally disabled.
        """

        if self._store is None:
            from agency_runtime.core.store.sqlite import Store

            self._store = Store(self._db_path) if self._db_path else Store()
        return self._store

    @staticmethod
    def _runtime_enabled() -> bool:
        from agency_runtime.core.runtime_control import master_enabled

        return master_enabled()

    def _active_routing_snapshot(self) -> Any:
        """Freeze config and return its catalog, seeding the starter roster once."""
        from agency_runtime.core.routing_snapshot import (
            capture_operational_routing_snapshot,
        )

        return capture_operational_routing_snapshot(self.store)

    def _workforce_snapshot(self, routing_snapshot: Any) -> tuple[Any, Any]:
        """Bind catalog and workforce contracts to one roster generation."""

        if getattr(routing_snapshot, "roster_generation", 0) == 0:
            return routing_snapshot, None
        from agency_runtime.core.routing_snapshot import bind_workforce_snapshot

        return bind_workforce_snapshot(self.store, routing_snapshot)

    def route(
        self,
        session_id: str,
        user_message: str,
        *,
        trace_id: str = "",
        host: str = "unknown",
        platform: str = "",
        capability_receipt: Any | None = None,
    ) -> dict[str, Any]:
        """Route a user message using verified native-host capabilities.

        A host name alone is not execution evidence. Native adapters should
        pass the opaque receipt returned by :meth:`attest_native_host`; calls
        without one remain useful for diagnostics but safely exclude workers
        whose host or tool requirements cannot be proven.
        """
        if not self._runtime_enabled():
            return _bypassed_routing(trace_id)
        from agency_runtime.core.selector.pipeline import route

        if not str(session_id or "").strip():
            raise ValueError("session_id is required for Agency routing correlation")
        snapshot, workforce = self._workforce_snapshot(self._active_routing_snapshot())
        return route(
            session_id,
            user_message,
            snapshot.catalog,
            config=snapshot.config,
            trace_id=trace_id or None,
            host=host,
            platform=platform or _current_platform(),
            capability_receipt=capability_receipt,
            workforce_snapshot=workforce,
        )

    @staticmethod
    def attest_native_host(
        host: str,
        *,
        session_id: str,
        trace_id: str,
        platform: str = "",
        available_tools: tuple[str, ...] = (),
        restricted: bool = False,
    ) -> Any:
        """Create one process-local native-adapter capability receipt.

        This is an adapter integration seam, not a serialized trust bypass.
        The resulting receipt is sealed to this process, correlation, host,
        platform, and short lifetime.
        """

        from agency_runtime.core.host_capabilities import (
            native_adapter_capability_receipt,
        )

        return native_adapter_capability_receipt(
            host,
            platform=platform or _current_platform(),
            session_id=session_id,
            trace_id=trace_id,
            available_tools=available_tools,
            restricted=restricted,
        )

    def route_with_context(
        self,
        session_id: str,
        user_message: str,
        *,
        trace_id: str = "",
        host: str = "unknown",
        capability_receipt: Any | None = None,
    ) -> str:
        """Run correlated preflight and return only its context projection."""
        return str(
            self.preflight(
                session_id,
                user_message,
                trace_id=trace_id,
                host=host,
                capability_receipt=capability_receipt,
            )["context"]
        )

    def preflight(
        self,
        session_id: str,
        user_message: str,
        *,
        trace_id: str = "",
        host: str = "python",
        capability_receipt: Any | None = None,
    ) -> dict[str, Any]:
        """Run one fully correlated routing and prompt-hydration turn."""
        if not self._runtime_enabled():
            return {
                "runtime_enabled": False,
                "bypassed": True,
                "session_id": str(session_id or ""),
                "trace_id": str(trace_id or ""),
                "routing": _bypassed_routing(trace_id),
                "context": "",
                "loaded_specialists": [],
                "selected_specialists": [],
                "trivial": False,
                "roster_size": 0,
            }
        from agency_runtime.core.preflight import run_preflight
        from agency_runtime.core.turn_origin import native_adapter_turn_origin

        current_trace_id = trace_id or str(uuid4())
        origin_receipt = native_adapter_turn_origin(
            "external_user",
            host=host,
            event="adapter_preflight",
            session_id=session_id,
            trace_id=current_trace_id,
        )

        return run_preflight(
            self.store,
            session_id=session_id,
            user_message=user_message,
            host=host,
            trace_id=current_trace_id,
            capability_receipt=capability_receipt,
            origin_receipt=origin_receipt,
        ).as_dict()

    def detect_work_units(self, message: str) -> dict[str, Any]:
        """Detect independent work units in a message."""
        if not self._runtime_enabled():
            return _bypassed_routing()["work_units"]
        from agency_runtime.core.selector.pipeline import detect_work_units

        return detect_work_units(message)

    def get_roster(self) -> list[dict[str, Any]]:
        """Return the enabled agent roster without exposing disabled definitions."""
        if not self._runtime_enabled():
            return []
        return self.store.get_enabled_roster()

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search the active roster."""
        if not self._runtime_enabled():
            return []
        from agency_runtime.core.selector.candidate_narrow import pre_narrow

        # Search is an observability/read API. Installing the bundled starter
        # roster is a routing concern and must not make a read unexpectedly
        # mutate a caller's persistent roster.
        catalog = self.store.get_active_roster_as_catalog()
        candidates, _ = pre_narrow(query, catalog, limit=limit)
        return candidates

    def record_skill(self, session_id: str, skill_name: str, *, trace_id: str) -> None:
        """Record a skill load for one correlated turn."""
        if not self._runtime_enabled():
            return
        self._require_active_turn(session_id, trace_id)
        self.store.record_skill_loaded(session_id, skill_name, trace_id=trace_id)

    def record_specialist(
        self,
        session_id: str,
        agent_slug: str,
        *,
        trace_id: str,
    ) -> None:
        """Record a specialist load for one correlated turn."""
        if not self._runtime_enabled():
            return
        from agency_runtime.core.resident_managers import reject_resident_manager

        reject_resident_manager(
            agent_slug,
            operation="be recorded as an ordinary specialist load",
        )
        self._require_active_turn(session_id, trace_id)
        self.store.record_specialist_loaded(
            session_id,
            agent_slug,
            trace_id=trace_id,
        )

    def record_model_receipt(
        self,
        *,
        trace_id: str,
        session_id: str,
        **kwargs: Any,
    ) -> str:
        """Record bounded generic model telemetry for one correlated turn.

        Caller-provided source labels never grant LiteLLM callback authority.
        """
        if not self._runtime_enabled():
            return ""
        self._require_active_turn(session_id, trace_id)
        return self.store.record_model_receipt(
            trace_id=trace_id,
            session_id=session_id,
            **kwargs,
        )

    def record_delegation(
        self,
        *,
        trace_id: str,
        session_id: str,
        work_unit_id: str,
        recommended_agent: str,
        status: str = "delegated",
        backend: str = "",
        host: str = "python",
        executed_worker_kind: str = "",
        executed_worker_id: str = "",
        native_run_id: str = "",
        skip_reason: str = "",
        error: str = "",
    ) -> str:
        """Record one explicitly correlated delegation lifecycle event."""
        if not self._runtime_enabled():
            return ""
        self._require_active_turn(session_id, trace_id)
        if not str(work_unit_id or "").strip():
            raise ValueError("work_unit_id is required for delegation evidence")
        if not str(recommended_agent or "").strip():
            raise ValueError("recommended_agent is required for delegation evidence")
        from agency_runtime.core.resident_managers import reject_resident_manager

        reject_resident_manager(
            recommended_agent,
            operation="be recorded as a delegated worker",
        )
        allowed_statuses = {
            "suggested",
            "started",
            "running",
            "delegated",
            "completed",
            "failed",
            "skipped",
        }
        normalized_status = str(status or "").strip()
        if normalized_status not in allowed_statuses:
            raise ValueError("unsupported delegation status")
        if normalized_status != "suggested" and not str(backend or "").strip():
            raise ValueError("backend is required for observed delegation evidence")
        if normalized_status in {"started", "running", "delegated", "completed"}:
            if not str(executed_worker_kind or "").strip():
                raise ValueError(
                    "executed_worker_kind is required for observed delegation evidence"
                )
            if not str(executed_worker_id or "").strip():
                raise ValueError("executed_worker_id is required for observed delegation evidence")
            if not str(native_run_id or "").strip():
                raise ValueError("native_run_id is required for observed delegation evidence")
        return self.store.record_delegation(
            trace_id=trace_id,
            session_id=session_id,
            host=host,
            work_unit_id=work_unit_id,
            recommended_agent=recommended_agent,
            status=normalized_status,
            backend=backend,
            executed_worker_kind=executed_worker_kind,
            executed_worker_id=executed_worker_id,
            native_run_id=native_run_id,
            skip_reason=skip_reason,
            error=error,
        )

    @staticmethod
    def _require_turn_correlation(session_id: str, trace_id: str) -> None:
        if not str(session_id or "").strip() or not str(trace_id or "").strip():
            raise ValueError("session_id and trace_id are required for turn evidence")

    def _require_active_turn(self, session_id: str, trace_id: str) -> None:
        """Reject public evidence writes that would manufacture a parent run."""
        self._require_turn_correlation(session_id, trace_id)
        from agency_runtime.core.config_binding import assert_store_config_binding
        from agency_runtime.core.turn_correlation import active_turn_error

        assert_store_config_binding(self.store)
        if error := active_turn_error(self.store, session_id, trace_id):
            raise ValueError(error)

    def finalize_header(
        self,
        draft_text: str,
        session_id: str = "",
        model: str = "",
        *,
        trace_id: str,
    ) -> str:
        """Finalize the agency header on a draft response."""
        if not self._runtime_enabled():
            return draft_text
        from agency_runtime.core.config_binding import assert_store_config_binding
        from agency_runtime.core.header.finalize import finalize_response

        self._require_turn_correlation(session_id, trace_id)
        assert_store_config_binding(self.store)
        result = finalize_response(
            draft_text,
            trace_metadata={
                "session_id": session_id,
                "trace_id": trace_id,
                "host": "python",
            },
            store=self.store,
            model=model,
        )
        if result["action"] != "accept":
            raise RuntimeError("Agency Runtime finalization did not accept the correlated response")
        return result["text"]


__version__ = "0.1.0"

__all__ = ["AgencyRuntime", "__version__"]
