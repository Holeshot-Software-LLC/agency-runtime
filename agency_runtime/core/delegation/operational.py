"""Bounded delegation-plan projections for operational surfaces."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from agency_runtime.core.config import AgencyConfig

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
    """Return the no-plan projection; Agency does not plan units for a host.

    This used to build a recommendation-only unit plan and show it on the
    operational surfaces. Planning work units for someone else to execute is
    Job B: the harness decides what to spawn, and Agency only staffs whoever
    exists. The signature is kept so the dashboard and broker callers stay
    unchanged while the panel itself is retired.
    """

    del receipt, catalog, config, execution_host, capability_receipt
    return empty_delegation_plan_projection()


__all__ = [
    "delegation_plan_projection",
    "empty_delegation_plan_projection",
]
