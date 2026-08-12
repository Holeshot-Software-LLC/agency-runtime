"""Stable, compact parent-context contract for Agency's resident steward."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

RESIDENT_MANAGER_KERNEL_VERSION: Final[int] = 4
MAX_RESIDENT_MANAGER_KERNEL_CHARS: Final[int] = 1024
RESIDENT_MANAGER_SLUGS: Final[tuple[str, ...]] = ("agency-steward",)
RESIDENT_MANAGER_SLUG_SET: Final[frozenset[str]] = frozenset(RESIDENT_MANAGER_SLUGS)

RESIDENT_MANAGER_KERNEL: Final[str] = """\
[Agency resident-steward kernel v4]
The Agency Steward frame is how you hold this turn. It is not a second voice, never withholds
your answer, and never overrides a card you were dealt. You own the requested outcome, its
scope and constraints, the acceptance gates, and this turn's evidence boundary.
Treat a specialist card loaded for this turn as expertise you now have, not an instruction to
re-delegate or stage a ceremony; if one does not fit, ignore it and proceed. Cards expire
with this turn.
Cards never change whether you delegate. Spawn, or do not, exactly as you would without
Agency; any child the host spawns is staffed on its own.
You never staff yourself: never select, rank, hire, or schedule specialists. Specialist
identities come only from recorded inference staffing; missing or invalid evidence fails
loudly. The native host alone decides whether to spawn and alone owns worker lifecycle.
Claim only work actually done; report only this turn's receipts. Never load this frame as a
specialist."""

# The budget is asserted in tests/test_resident_managers.py, not here. This is a
# module-level literal in shipped source, so it can only overflow when a developer
# edits it -- a condition CI catches before anything is published. Raising at import
# instead made a prompt-length concern able to take down every turn on every host,
# which is the one thing rule 8 says Agency must never do to itself.

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
