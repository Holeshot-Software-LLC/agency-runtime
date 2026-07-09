"""Base adapter interface — all adapters implement this contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agency_runtime.core.store.sqlite import Store


class BaseAdapter(ABC):
    """Base class for host/runtime adapters.

    Adapters are thin I/O shims. They translate between host events and
    the agency-runtime core. They should NOT reimplement routing,
    categorization, or delegation policy.
    """

    host_name: str = "unknown"

    def __init__(self, store: Store | None = None):
        self.store = store or Store()

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this adapter's runtime is installed and available."""
        ...

    @abstractmethod
    def report_skills_loaded(self, session_id: str) -> list[str]:
        """Return skills loaded in the current host session."""
        ...

    @abstractmethod
    def report_specialists_loaded(self, session_id: str) -> list[str]:
        """Return specialists loaded in the current host session."""
        ...

    @abstractmethod
    def get_delegate_backend(self) -> str | None:
        """Return the delegate backend name this adapter provides, or None."""
        ...

    @abstractmethod
    def expose_model_telemetry(self, session_id: str) -> dict[str, Any]:
        """Return model telemetry from the host, if available."""
        ...

    def apply_finalization(self, draft_text: str, trace_id: str, model: str = "") -> str:
        """Apply header/finalization to the final visible reply."""
        from agency_runtime.core.header.contract import finalize_header
        return finalize_header(
            draft_text,
            session_id=trace_id,
            store=self.store,
            model=model,
        )
