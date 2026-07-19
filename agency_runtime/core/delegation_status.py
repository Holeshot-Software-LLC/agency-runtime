"""Dependency-neutral delegation lifecycle status definitions."""

from __future__ import annotations

from typing import Final

DELEGATION_STATUS_PRIORITY: Final[dict[str, int]] = {
    "suggested": 0,
    "started": 1,
    "running": 2,
    "delegated": 3,
    "completed": 4,
    "skipped": 5,
    "failed": 6,
}
TERMINAL_DELEGATION_STATUSES: Final[frozenset[str]] = frozenset({"completed", "skipped", "failed"})
MAX_DELEGATION_HOST_CHARS: Final[int] = 64
MAX_DELEGATION_WORK_UNIT_ID_CHARS: Final[int] = 160
MAX_DELEGATION_AGENT_CHARS: Final[int] = 128
MAX_DELEGATION_BACKEND_CHARS: Final[int] = 128


def bounded_delegation_field(value: object, *, maximum: int) -> str:
    """Normalize one content-free delegation identifier under a hard bound."""

    return " ".join(str(value or "").split())[:maximum]


def normalize_delegation_status(value: object) -> str:
    """Return one supported lifecycle status or reject ambiguous evidence."""

    status = str(value or "suggested").strip() or "suggested"
    if status not in DELEGATION_STATUS_PRIORITY:
        raise ValueError(f"unsupported delegation status: {status[:32]}")
    return status


def dominant_delegation_status(current: object, incoming: object) -> str:
    """Return the order-independent authoritative lifecycle state.

    Failure is sticky for one work-unit identity. A later duplicated or
    reordered success callback cannot erase failure evidence; a retry must use
    a new work-unit identity.
    """

    current_status = normalize_delegation_status(current)
    incoming_status = normalize_delegation_status(incoming)
    current_rank = DELEGATION_STATUS_PRIORITY.get(current_status, 0)
    incoming_rank = DELEGATION_STATUS_PRIORITY.get(incoming_status, 0)
    return incoming_status if incoming_rank > current_rank else current_status


__all__ = [
    "DELEGATION_STATUS_PRIORITY",
    "MAX_DELEGATION_AGENT_CHARS",
    "MAX_DELEGATION_BACKEND_CHARS",
    "MAX_DELEGATION_HOST_CHARS",
    "MAX_DELEGATION_WORK_UNIT_ID_CHARS",
    "TERMINAL_DELEGATION_STATUSES",
    "bounded_delegation_field",
    "dominant_delegation_status",
    "normalize_delegation_status",
]
