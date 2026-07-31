"""Shared version contract for durable preflight recipes."""

from __future__ import annotations

from typing import Final

PREFLIGHT_REPLAY_RECIPE_VERSION: Final[int] = 13
PREFLIGHT_CONTEXT_POLICY_VERSION: Final[int] = 13
SUPPORTED_PREFLIGHT_RECIPE_VERSIONS: Final[frozenset[int]] = frozenset({5, 6, 7, 9, 10, 11, 12, 13})

__all__ = [
    "PREFLIGHT_CONTEXT_POLICY_VERSION",
    "PREFLIGHT_REPLAY_RECIPE_VERSION",
    "SUPPORTED_PREFLIGHT_RECIPE_VERSIONS",
]
