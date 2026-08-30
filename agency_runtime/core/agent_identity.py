"""Canonical identity projection for agent-shaped mappings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def agent_identity(agent: Mapping[str, Any]) -> str:
    """Return the canonical agent identity, preferring ``slug``.

    Runtime selector catalogs historically use ``slug`` while governed roster
    and workforce records commonly use ``agent_slug``. A few call sites used
    the opposite precedence when both keys were present, which made malformed
    or transitional projections resolve to different workers by layer. Keep
    the established selector precedence in one dependency-light owner.
    """

    return str(agent.get("slug") or agent.get("agent_slug") or "").strip()


__all__ = ["agent_identity"]
