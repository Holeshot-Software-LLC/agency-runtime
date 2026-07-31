"""Audited, self-contained default roster for offline Agency installs."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from agency_runtime.core.roster.bundled import BundledRoster

# Compatibility name for persisted policies and older callers. ADR-0122 removed
# deterministic no-match workers: the Agency-native steward has its own compact
# parent-context lifecycle and never enters the selectable roster.
NO_MATCH_FALLBACK_SLUGS: tuple[str, ...] = ()

# Keep the historical public name while loading the complete audited package
# lazily. Normal installation is network-independent and verifies every manifest,
# prompt, provenance, and immutable-version hash before activation.
STARTER_ROSTER: Sequence[dict[str, Any]] = BundledRoster()

__all__ = ["NO_MATCH_FALLBACK_SLUGS", "STARTER_ROSTER"]
