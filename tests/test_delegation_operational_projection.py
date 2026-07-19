"""Focused coverage for the recommendation-only dashboard delegation plan."""

from __future__ import annotations

from typing import Any

import pytest

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.delegation import operational


def _hydrated_unit() -> dict[str, Any]:
    return {
        "work_unit_id": "unit-1234567890",
        "goal_preview": "Review the authentication boundary.",
        "deliverable_kind": "review",
        "expected_deliverable": "Prioritized findings with evidence.",
        "recommended_agent": "security-reviewer",
        "compatible_specialists": ["security-reviewer", "evidence-reviewer"],
        "delegation_strength": "strongly_preferred",
        "selection_confidence": 0.93,
        "rationale_codes": ["detected:list", "policy:prefer"],
        "dependencies": [],
        "parallelization": "parallel",
        "mutation_scope": "read_only",
        "likely_files_or_resources": ["repository-workspace"],
        "required_tools": ["repository-read"],
        "required_evidence": ["review-findings"],
    }


def test_empty_delegation_plan_is_canonical_and_fresh() -> None:
    first = operational.empty_delegation_plan_projection()
    second = operational.empty_delegation_plan_projection()

    assert first == second
    assert first is not second
    assert first["authority"] == "recommendation_only"
    assert first["units"] == []
    assert "no delegation recommendation" in first["evidence_contract"]


def test_delegation_plan_projects_complete_unit_assignment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}

    def assign(catalog, routing, **kwargs):
        observed["catalog"] = catalog
        observed["routing"] = dict(routing)
        observed["assignment_kwargs"] = kwargs
        return [{"slug": "security-reviewer"}]

    def build(routing, policy):
        observed["planned_routing"] = dict(routing)
        observed["policy"] = policy
        return [{"work_unit_id": "unit-1234567890"}]

    monkeypatch.setattr(operational, "assignment_agents_from_catalog", assign)
    monkeypatch.setattr(operational, "build_unit_agent_plan", build)
    monkeypatch.setattr(
        operational,
        "hydrate_unit_agent_plan",
        lambda routing, plan: (
            observed.update({"hydration_routing": routing, "plan": plan}) or [_hydrated_unit()]
        ),
    )
    monkeypatch.setattr(
        operational,
        "native_delegation_instruction",
        lambda host: f"dispatch:{host}",
    )
    config = AgencyConfig()
    catalog = [{"slug": "security-reviewer"}]
    result = operational.delegation_plan_projection(
        {
            "session_id": "",
            "routing": {
                "trace_id": "",
                "work_units": {"delegate": True, "units": ["Review auth", "Verify auth"]},
            },
        },
        catalog=catalog,
        config=config,
        execution_host="codex",
        capability_receipt={
            "platform": "",
            "capabilities": ["repository-read", 7],
        },
    )

    assert observed["catalog"] == catalog
    assert observed["assignment_kwargs"]["session_id"] == "dashboard"
    assert observed["assignment_kwargs"]["trace_id"] == ""
    assert observed["assignment_kwargs"]["platform"] == "unknown"
    assert observed["assignment_kwargs"]["available_tools"] == ("repository-read",)
    assert observed["planned_routing"]["unit_assignment_agents"] == [{"slug": "security-reviewer"}]
    assert observed["policy"] is config.delegation
    assert result == {
        "schema_version": "agency.dashboard.delegation_plan.v1",
        "authority": "recommendation_only",
        "execution_host": "codex",
        "mechanism": "dispatch:codex",
        "evidence_contract": (
            "A plan is not execution. Delegation is proven only by correlated native "
            "spawn and worker/run evidence. A durable explicit decline is a disposition, "
            "not proof that delegated work ran."
        ),
        "unit_count": 1,
        "units": [
            {
                "work_unit_id": "unit-1234567890",
                "goal_preview": "Review the authentication boundary.",
                "deliverable_kind": "review",
                "expected_deliverable": "Prioritized findings with evidence.",
                "recommended_agent": "security-reviewer",
                "compatible_specialists": [
                    "security-reviewer",
                    "evidence-reviewer",
                ],
                "assignment_strength": "strongly_preferred",
                "confidence": 0.93,
                "rationale_codes": ["detected:list", "policy:prefer"],
                "dependencies": [],
                "parallelization": "parallel",
                "mutation_scope": "read_only",
                "likely_files_or_resources": ["repository-workspace"],
                "required_tools": ["repository-read"],
                "required_evidence": ["review-findings"],
            }
        ],
    }


def test_delegation_plan_handles_unassigned_malformed_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}
    monkeypatch.setattr(
        operational,
        "assignment_agents_from_catalog",
        lambda _catalog, routing, **kwargs: (
            observed.update({"routing": dict(routing), "kwargs": kwargs}) or []
        ),
    )
    monkeypatch.setattr(operational, "build_unit_agent_plan", lambda _routing, _policy: [])
    monkeypatch.setattr(
        operational,
        "hydrate_unit_agent_plan",
        lambda *_args: pytest.fail("an empty plan must not be hydrated"),
    )

    result = operational.delegation_plan_projection(
        {"session_id": "session", "routing": None},
        catalog=[],
        config=AgencyConfig(),
        execution_host="claude",
        capability_receipt={"platform": "windows", "capabilities": []},
    )

    assert observed["routing"] == {}
    assert observed["kwargs"]["session_id"] == "session"
    assert result["unit_count"] == 0
    assert result["units"] == []
    assert "Claude Code" in result["mechanism"]
