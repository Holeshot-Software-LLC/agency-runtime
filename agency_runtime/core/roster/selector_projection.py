"""Canonical roster projections for selection and dashboard display.

Selector metadata is already bounded at roster ingress.  Preserve that exact
reviewed metadata for routing; silently shortening descriptions or taxonomy at
this later boundary changes which specialist wins.  The live dashboard has a
separate, deliberately compact projection because it renders only summary
cards.
"""

from __future__ import annotations

from collections.abc import Container
from typing import Any

from agency_runtime.core.agent_activation import (
    PROTECTED_AGENT_SLUGS,
    agent_is_enabled,
)
from agency_runtime.core.agent_identity import agent_identity
from agency_runtime.core.host_capabilities import execution_contract_projection

UI_NAME_CHARS = 128
UI_DIVISION_CHARS = 64
UI_TAXONOMY_CHARS = 64
UI_CAPABILITY_ITEMS = 4
_ROUTING_SCALAR_FIELDS = (
    "authority",
    "context_mode",
    "independence_group",
    "expected_output_contract",
    "source_revision",
    "source_content_hash",
    "audit_revision",
    "audit_status",
)
_ROUTING_LIST_FIELDS = (
    "anti_capabilities",
    "task_types",
    "preferred_when",
    "avoid_when",
    "required_tools",
    "optional_tools",
    "supported_hosts",
    "supported_platforms",
    "conflicts_with",
    "requires",
    "evidence_requirements",
    "model_requirements",
    "findings",
)


def _ui_text(value: object, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def _selector_text(value: object) -> str:
    return value if isinstance(value, str) else str(value or "")


def _selector_taxonomy(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _ui_taxonomy(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        text for item in value[:UI_CAPABILITY_ITEMS] if (text := _ui_text(item, UI_TAXONOMY_CHARS))
    ]


def selector_roster_projection(
    agent: dict[str, Any],
    disabled: Container[str] = (),
) -> dict[str, Any]:
    """Return the canonical selector input used by every direct and broker path."""

    slug = agent_identity(agent)
    projection = {
        "agent_slug": slug,
        "name": _selector_text(agent.get("name")),
        "division": _selector_text(agent.get("division")),
        "description": _selector_text(agent.get("description")),
        "categories": _selector_taxonomy(agent.get("categories")),
        "capabilities": _selector_taxonomy(agent.get("capabilities")),
        "enabled": agent_is_enabled(slug, disabled),
        "protected": slug in PROTECTED_AGENT_SLUGS,
        "routing_contract_valid": bool(agent.get("routing_contract_valid", True)),
    }
    projection.update({field: _selector_text(agent.get(field)) for field in _ROUTING_SCALAR_FIELDS})
    projection.update(
        {field: _selector_taxonomy(agent.get(field)) for field in _ROUTING_LIST_FIELDS}
    )
    projection.update(execution_contract_projection(projection))
    return projection


def ui_roster_projection(
    agent: dict[str, Any],
    disabled: Container[str] = (),
) -> dict[str, Any]:
    """Return only fields rendered by the live dashboard roster cards."""

    slug = agent_identity(agent)
    return {
        "agent_slug": slug,
        "name": _ui_text(agent.get("name"), UI_NAME_CHARS),
        "division": _ui_text(agent.get("division"), UI_DIVISION_CHARS),
        "capabilities": _ui_taxonomy(agent.get("capabilities")),
        "enabled": agent_is_enabled(slug, disabled),
        "protected": slug in PROTECTED_AGENT_SLUGS,
    }


__all__ = [
    "UI_CAPABILITY_ITEMS",
    "UI_DIVISION_CHARS",
    "UI_NAME_CHARS",
    "UI_TAXONOMY_CHARS",
    "selector_roster_projection",
    "ui_roster_projection",
]
