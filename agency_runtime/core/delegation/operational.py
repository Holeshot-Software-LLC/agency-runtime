"""Bounded delegation-plan projections for operational surfaces."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.host_guidance import native_delegation_instruction
from agency_runtime.core.unit_assignment import (
    assignment_agents_from_catalog,
    build_unit_agent_plan,
    hydrate_unit_agent_plan,
)

_SCHEMA = "agency.dashboard.delegation_plan.v1"
_AUTHORITY = "recommendation_only"
_DISABLED_EVIDENCE = (
    "Agency Runtime is disabled; no delegation recommendation or execution evidence was produced."
)
_ACTIVE_EVIDENCE = (
    "A plan is not execution. Delegation is proven only by correlated native spawn "
    "and worker/run evidence. A durable explicit decline is a disposition, not proof "
    "that delegated work ran."
)


def empty_delegation_plan_projection() -> dict[str, Any]:
    """Return the canonical disabled/no-plan projection."""

    return {
        "schema_version": _SCHEMA,
        "authority": _AUTHORITY,
        "execution_host": "",
        "mechanism": "",
        "evidence_contract": _DISABLED_EVIDENCE,
        "unit_count": 0,
        "units": [],
    }


def delegation_plan_projection(
    receipt: Mapping[str, Any],
    *,
    catalog: Sequence[Mapping[str, Any]],
    config: AgencyConfig,
    execution_host: str,
    capability_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the recommendation-only unit plan shown by operational surfaces."""

    raw_routing = receipt.get("routing")
    routing = dict(raw_routing) if isinstance(raw_routing, Mapping) else {}
    assignments = assignment_agents_from_catalog(
        catalog,
        routing,
        config=config,
        session_id=str(receipt.get("session_id") or "dashboard"),
        trace_id=str(routing.get("trace_id") or ""),
        host=execution_host,
        platform=str(capability_receipt.get("platform") or "unknown"),
        available_tools=tuple(
            str(item)
            for item in capability_receipt.get("capabilities", ())
            if isinstance(item, str)
        ),
        capability_receipt=capability_receipt,
    )
    routing["unit_assignment_agents"] = assignments
    plan = build_unit_agent_plan(routing, config.delegation)
    hydrated = hydrate_unit_agent_plan(routing, plan) if plan else []
    return {
        "schema_version": _SCHEMA,
        "authority": _AUTHORITY,
        "execution_host": execution_host,
        "mechanism": native_delegation_instruction(execution_host),
        "evidence_contract": _ACTIVE_EVIDENCE,
        "unit_count": len(hydrated),
        "units": [
            {
                "work_unit_id": item["work_unit_id"],
                "goal_preview": item["goal_preview"],
                "deliverable_kind": item["deliverable_kind"],
                "expected_deliverable": item["expected_deliverable"],
                "recommended_agent": item["recommended_agent"],
                "compatible_specialists": list(item["compatible_specialists"]),
                "assignment_strength": item["delegation_strength"],
                "confidence": item["selection_confidence"],
                "rationale_codes": list(item["rationale_codes"]),
                "dependencies": list(item["dependencies"]),
                "parallelization": item["parallelization"],
                "mutation_scope": item["mutation_scope"],
                "likely_files_or_resources": list(item["likely_files_or_resources"]),
                "required_tools": list(item["required_tools"]),
                "required_evidence": list(item["required_evidence"]),
            }
            for item in hydrated
        ],
    }


__all__ = [
    "delegation_plan_projection",
    "empty_delegation_plan_projection",
]
