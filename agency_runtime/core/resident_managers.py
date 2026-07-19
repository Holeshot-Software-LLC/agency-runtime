"""Stable, compact parent-context contract for Agency's resident managers."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

RESIDENT_MANAGER_KERNEL_VERSION: Final[int] = 1
MAX_RESIDENT_MANAGER_KERNEL_CHARS: Final[int] = 1024
RESIDENT_MANAGER_SLUGS: Final[tuple[str, str]] = (
    "agents-orchestrator",
    "chief-of-staff",
)
RESIDENT_MANAGER_SLUG_SET: Final[frozenset[str]] = frozenset(RESIDENT_MANAGER_SLUGS)

RESIDENT_MANAGER_KERNEL: Final[str] = """\
[Agency resident-manager kernel v1]
Chief of Staff owns the requested outcome, scope, priorities, constraints, and acceptance
gates. It does not select workers, prescribe execution, or claim completed work.
Agents Orchestrator owns decomposition, compatible specialist selection, delegation
recommendations, and evidence boundaries. It does not redefine the outcome, schedule native
workers, or claim execution.
The native host alone spawns, schedules, cancels, and recovers workers. Specialists execute
bounded assignments; independent reviewers remain isolated.
These managers are parent-only: never load or delegate them as ordinary specialists.
Temporary specialist context is turn- or assignment-scoped. Report activity only from
authoritative current-turn receipts."""

if len(RESIDENT_MANAGER_KERNEL) > MAX_RESIDENT_MANAGER_KERNEL_CHARS:
    raise RuntimeError("resident-manager kernel exceeds its context budget")

RESIDENT_MANAGER_KERNEL_HASH: Final[str] = hashlib.sha256(
    RESIDENT_MANAGER_KERNEL.encode("utf-8")
).hexdigest()


@dataclass(frozen=True, slots=True)
class ResidentManagerKernelReference:
    """Content-free identity persisted across compaction boundaries."""

    version: int
    content_hash: str
    slugs: tuple[str, str]

    def as_dict(self) -> dict[str, object]:
        """Return the bounded content-free projection persisted with a turn."""

        return {
            "version": self.version,
            "content_hash": self.content_hash,
            "slugs": list(self.slugs),
        }


RESIDENT_MANAGER_KERNEL_REFERENCE: Final[ResidentManagerKernelReference] = (
    ResidentManagerKernelReference(
        version=RESIDENT_MANAGER_KERNEL_VERSION,
        content_hash=RESIDENT_MANAGER_KERNEL_HASH,
        slugs=RESIDENT_MANAGER_SLUGS,
    )
)


def _normalized_slug(value: object) -> str:
    return value.strip().casefold() if isinstance(value, str) else ""


def is_resident_manager_slug(value: object) -> bool:
    """Return whether ``value`` identifies one protected parent manager."""

    return _normalized_slug(value) in RESIDENT_MANAGER_SLUG_SET


def is_current_resident_manager_kernel_reference(value: object) -> bool:
    """Return whether ``value`` identifies the exact installed manager kernel."""

    if not isinstance(value, Mapping):
        return False
    return (
        value.get("version") == RESIDENT_MANAGER_KERNEL_REFERENCE.version
        and value.get("content_hash") == RESIDENT_MANAGER_KERNEL_REFERENCE.content_hash
        and value.get("slugs") == list(RESIDENT_MANAGER_KERNEL_REFERENCE.slugs)
    )


def resident_manager_boundary_error(value: object, *, operation: str) -> str:
    """Return a stable error when an ordinary specialist boundary receives a manager."""

    slug = _normalized_slug(value)
    if slug not in RESIDENT_MANAGER_SLUG_SET:
        return ""
    action = " ".join(str(operation or "").split())[:96]
    if not action:
        action = "be used as an ordinary specialist"
    return f"resident manager '{slug}' is parent-only and cannot {action}"


def reject_resident_manager(value: object, *, operation: str) -> None:
    """Raise when an ordinary specialist operation targets a resident manager."""

    if error := resident_manager_boundary_error(value, operation=operation):
        raise ValueError(error)


__all__ = [
    "MAX_RESIDENT_MANAGER_KERNEL_CHARS",
    "RESIDENT_MANAGER_KERNEL",
    "RESIDENT_MANAGER_KERNEL_HASH",
    "RESIDENT_MANAGER_KERNEL_REFERENCE",
    "RESIDENT_MANAGER_KERNEL_VERSION",
    "RESIDENT_MANAGER_SLUGS",
    "RESIDENT_MANAGER_SLUG_SET",
    "ResidentManagerKernelReference",
    "is_current_resident_manager_kernel_reference",
    "is_resident_manager_slug",
    "reject_resident_manager",
    "resident_manager_boundary_error",
]
