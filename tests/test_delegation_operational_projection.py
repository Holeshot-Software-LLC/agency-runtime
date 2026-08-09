"""Focused coverage for the recommendation-only dashboard delegation plan."""

from __future__ import annotations

from typing import Any

from agency_runtime.core.delegation import operational
from agency_runtime.core.host_guidance import native_delegation_instruction


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


def test_native_delegation_guidance_requires_every_exact_plan_row() -> None:
    guidance = native_delegation_instruction("codex")

    assert "Dispatch every persisted plan row exactly once" in guidance
    assert "do not merge, omit" in guidance
    assert "perform a planned specialist unit in the parent" in guidance
    assert "stop the parent turn without claiming the planned outcome" in guidance
    assert "may refine, merge" not in guidance


def test_empty_delegation_plan_is_canonical_and_fresh() -> None:
    first = operational.empty_delegation_plan_projection()
    second = operational.empty_delegation_plan_projection()

    assert first == second
    assert first is not second
    assert first["authority"] == "recommendation_only"
    assert first["units"] == []
    assert "no delegation recommendation" in first["evidence_contract"]


