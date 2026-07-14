"""Auditable delegation ledger for Agency Runtime.

The ledger is the small contract surface shared by lifecycle runners and callers
that need a portable JSON summary. SQLite remains canonical when a Store is
provided; the in-memory entries are kept in sync so callers can serialize the
contract without issuing their own SQL.
"""

from __future__ import annotations

import json
import socket
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from agency_runtime.core.store.sqlite import Store

TERMINAL_STATUSES = {"completed", "failed", "skipped"}


@dataclass(slots=True)
class DelegationLedgerEntry:
    """One work-unit row in the delegation ledger contract."""

    id: str
    recommended_agent: str = ""
    status: str = "suggested"
    backend: str = ""
    skip_reason: str = ""
    error: str = ""
    event_id: str = ""

    def contract_dict(self) -> dict[str, str]:
        """Return the public JSON-contract fields for this entry."""
        return {
            "id": self.id,
            "recommended_agent": self.recommended_agent,
            "status": self.status,
            "backend": self.backend,
            "skip_reason": self.skip_reason,
            "error": self.error,
        }


class DelegationLedger:
    """Record delegation lifecycle state and render the required JSON contract."""

    def __init__(
        self,
        store: Store | None = None,
        *,
        trace_id: str | None = None,
        session_id: str = "",
        host: str | None = None,
    ) -> None:
        self.store = store
        self.trace_id = trace_id or str(uuid.uuid4())
        self.session_id = session_id
        self.host = host or socket.gethostname()
        self._entries: dict[str, DelegationLedgerEntry] = {}

    @property
    def entries(self) -> list[DelegationLedgerEntry]:
        """Return entries in insertion order."""
        return list(self._entries.values())

    def suggest(
        self, work_unit_id: str, recommended_agent: str = "", *, backend: str = ""
    ) -> DelegationLedgerEntry:
        """Create or update a suggested work unit."""
        entry = self._entries.get(work_unit_id)
        if entry is None:
            entry = DelegationLedgerEntry(
                id=work_unit_id,
                recommended_agent=recommended_agent or "",
                status="suggested",
                backend=backend or "",
            )
            if self.store is not None:
                entry.event_id = self.store.record_delegation(
                    trace_id=self.trace_id,
                    session_id=self.session_id,
                    host=self.host,
                    work_unit_id=work_unit_id,
                    recommended_agent=entry.recommended_agent,
                    status=entry.status,
                    backend=entry.backend,
                )
            self._entries[work_unit_id] = entry
        else:
            if recommended_agent:
                entry.recommended_agent = recommended_agent
            if backend:
                entry.backend = backend
        return entry

    def update(
        self,
        work_unit_id: str,
        *,
        status: str,
        backend: str = "",
        recommended_agent: str = "",
        skip_reason: str = "",
        error: str = "",
    ) -> DelegationLedgerEntry:
        """Update a work unit status and mirror the transition to SQLite."""
        entry = self.suggest(work_unit_id, recommended_agent=recommended_agent, backend=backend)
        entry.status = status
        if backend:
            entry.backend = backend
        if recommended_agent:
            entry.recommended_agent = recommended_agent
        entry.skip_reason = skip_reason
        entry.error = error
        if self.store is not None and entry.event_id:
            # Store.update_delegation currently updates status/backend/error.  Preserve
            # skip_reason in the in-memory contract; the initial insert already holds
            # explicit skipped suggestions when callers use record() directly.
            self.store.update_delegation(
                entry.event_id,
                status=status,
                backend=entry.backend,
                error=error,
                recommended_agent=entry.recommended_agent,
                skip_reason=skip_reason,
            )
        return entry

    def record(self, record: Mapping[str, Any]) -> DelegationLedgerEntry:
        """Record from a mapping shaped like a ledger contract row."""
        return self.update(
            str(record.get("id") or record.get("work_unit_id") or ""),
            status=str(record.get("status") or "suggested"),
            backend=str(record.get("backend") or ""),
            recommended_agent=str(record.get("recommended_agent") or ""),
            skip_reason=str(record.get("skip_reason") or ""),
            error=str(record.get("error") or ""),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the required JSON-serializable delegation ledger contract."""
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "host": self.host,
            "work_units": [entry.contract_dict() for entry in self.entries],
        }

    def to_json(self, *, indent: int | None = None) -> str:
        """Serialize the ledger contract to JSON."""
        return json.dumps(self.as_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_store(
        cls, store: Store, trace_id: str, *, session_id: str = "", host: str | None = None
    ) -> DelegationLedger:
        """Hydrate a ledger contract from existing Store delegation rows."""
        ledger = cls(store, trace_id=trace_id, session_id=session_id, host=host)
        for row in store.get_delegations(trace_id):
            entry = DelegationLedgerEntry(
                id=str(row.get("work_unit_id") or ""),
                recommended_agent=str(row.get("recommended_agent") or ""),
                status=str(row.get("status") or "suggested"),
                backend=str(row.get("backend") or ""),
                skip_reason=str(row.get("skip_reason") or ""),
                error=str(row.get("error") or ""),
                event_id=str(row.get("id") or ""),
            )
            ledger._entries[entry.id] = entry
        return ledger


__all__ = ["TERMINAL_STATUSES", "DelegationLedger", "DelegationLedgerEntry"]
