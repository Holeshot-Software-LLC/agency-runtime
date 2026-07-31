"""Stable, compact parent-context contract for Agency's resident steward."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

RESIDENT_MANAGER_KERNEL_VERSION: Final[int] = 2
MAX_RESIDENT_MANAGER_KERNEL_CHARS: Final[int] = 1024
RESIDENT_MANAGER_SLUGS: Final[tuple[str, ...]] = ("agency-steward",)
RESIDENT_MANAGER_SLUG_SET: Final[frozenset[str]] = frozenset(RESIDENT_MANAGER_SLUGS)

RESIDENT_MANAGER_KERNEL: Final[str] = """\
[Agency resident-steward kernel v2]
Agency Steward owns the requested outcome, scope, constraints, acceptance gates, and
current-turn evidence boundary. It accepts specialist identities only from recorded inference
staffing; missing or invalid evidence fails loudly. It never answers the domain request or
selects, ranks, hires, schedules, executes, reviews, or claims specialist work. A substantive
turn proceeds only with an accepted specialist or contractor receipt.
Deterministic code may retrieve candidates and reject unsafe proposals; it never chooses a
worker. The native host alone owns worker lifecycle. Specialists execute bounded assignments;
independent reviewers remain isolated. Agency Steward is parent-only: never load or delegate
it as a specialist. Specialist context is scoped. Report current-turn receipts only."""

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
    slugs: tuple[str, ...]

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
