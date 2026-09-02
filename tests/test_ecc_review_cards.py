"""AR-364: the two ECC review cards are governed, source-pinned, review-only specialists.

The primary catalog is not the only audited source any more. These tests pin
that the two cards carry their own repository and revision in the packaged
manifest and governed prompt, that they are reachable by the deterministic
retriever for their request shapes, and that review authority cannot be
stretched to implementation work.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.evals.full_roster_cases import RETRIEVAL_CASES
from agency_runtime.core.roster import bundled
from agency_runtime.core.roster.bundled import BundledRoster, bundled_manifest
from agency_runtime.core.workforce import (
    StaffingBudget,
    StaffingContext,
    parse_work_unit_plan,
    verify_staffing,
)
from agency_runtime.core.workforce.contract import project_workforce_contract
from agency_runtime.core.workforce.staffing_verifier import build_deterministic_proposal

ECC_SOURCE_ID = "ecc"
ECC_REPOSITORY = "https://github.com/affaan-m/ECC"
ECC_REVISION = "ca185ef5f7667078a1e70a763bd3a9c71c48acf0"
ECC_CARDS = ("silent-failure-hunter", "type-design-analyzer")
_DATA = Path(bundled.__file__).parent / "data"


def _cards() -> dict[str, dict[str, Any]]:
    agents = {agent["slug"]: dict(agent) for agent in BundledRoster() if agent["slug"] in ECC_CARDS}
    assert set(agents) == set(ECC_CARDS)
    return agents


def _unit(
    unit_id: str,
    *,
    artifact: str,
    lifecycle: str,
    capability: str,
    authority: str,
    mutation: str,
) -> dict[str, object]:
    return {
        "unit_id": unit_id,
        "outcome": f"Complete {unit_id}",
        "artifact_kind": artifact,
        "lifecycle_phase": lifecycle,
        "domains": ["software-engineering"],
        "languages": [],
        "frameworks": [],
        "required_capabilities": [capability],
        "authority": authority,
        "mutation_scope": mutation,
        "risks": ["regression"],
        "trust_boundaries": ["repository"],
        "claims": [],
        "depends_on": [],
        "resources": ["repository"],
        "required_tools": [],
        "platforms": ["windows", "linux"],
        "acceptance_evidence": [f"{unit_id} verified"],
        "parallelization": "unspecified",
    }


def _plan(unit: dict[str, object]):
    return parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Complete the requested work with safe staffing.",
            "units": [unit],
        }
    )


def _context() -> StaffingContext:
    return StaffingContext("codex", "linux", frozenset({"native-delegation", "repository-read"}), 7)


def test_cards_are_pinned_to_the_ecc_source_and_review_only() -> None:
    manifest = bundled_manifest()
    source = manifest["sources"][ECC_SOURCE_ID]
    assert source["repository"] == ECC_REPOSITORY
    assert source["revision"] == ECC_REVISION
    assert source["license"] == "MIT"
    assert source["license_file"] == f"LICENSE.{ECC_SOURCE_ID}.txt"
    assert (_DATA / source["license_file"]).read_text(encoding="utf-8").startswith("MIT License\n")

    entries = {entry["slug"]: entry for entry in manifest["agents"] if entry["slug"] in ECC_CARDS}
    assert set(entries) == set(ECC_CARDS)
    for slug, entry in entries.items():
        assert entry["source_repository"] == ECC_REPOSITORY
        assert entry["source_revision"] == ECC_REVISION
        assert entry["relative_path"] == f"agents/{slug}.md"
        assert entry["audit_status"] == "approved"
        assert entry["authority"] == "review"
        assert entry["context_mode"] == "direct_safe"
        assert entry["required_tools"] == []
        assert "review" in entry["task_types"]
        prompt = (_DATA / entry["prompt_file"]).read_text(encoding="utf-8")
        assert f"- Source: {ECC_REPOSITORY}/blob/{ECC_REVISION}/agents/{slug}.md" in prompt
    groups = {entry["independence_group"] for entry in entries.values()}
    assert len(groups) == len(ECC_CARDS)

    primary = manifest["source"]["repository"]
    others = [entry for entry in manifest["agents"] if entry["slug"] not in ECC_CARDS]
    assert others
    assert {entry["source_repository"] for entry in others} == {primary}


def test_cards_have_direct_retrieval_probes_in_the_curated_eval() -> None:
    cases = {str(case["id"]): case for case in RETRIEVAL_CASES}
    expected = {
        "silent-failure-review": "silent-failure-hunter",
        "type-design-review": "type-design-analyzer",
    }
    for case_id, slug in expected.items():
        case = cases[case_id]
        assert case["kind"] == "direct"
        assert case["required"] == (slug,)
        assert int(str(case["max_required_rank"])) <= 10


@pytest.mark.parametrize("slug", ECC_CARDS)
def test_cards_cannot_staff_implementation_authority_work(slug: str) -> None:
    contract = project_workforce_contract(_cards()[slug])
    assert contract.authority == "review"
    assert contract.archetype == "reviewer"
    context = _context()

    implementation = _plan(
        _unit(
            "unit-implement",
            artifact="implementation-change",
            lifecycle="implementation",
            capability="implementation",
            authority="modify",
            mutation="workspace_write",
        )
    )
    proposal = build_deterministic_proposal(
        implementation,
        (contract,),
        {"unit-implement": ((slug, 0.99),)},
        context=context,
        budget=StaffingBudget(),
    )
    reasons = {
        reason for item in proposal.units[0].unavailable_shadows for reason in item.reason_codes
    }
    assert "agent_authority_mismatch" in reasons
    decision = verify_staffing(
        implementation, proposal, (contract,), context=context, budget=StaffingBudget()
    )
    assert not decision.accepted

    review = _plan(
        _unit(
            "unit-review",
            artifact="review-report",
            lifecycle="review",
            capability="review",
            authority="review",
            mutation="read_only",
        )
    )
    proposal = build_deterministic_proposal(
        review,
        (contract,),
        {"unit-review": ((slug, 0.99),)},
        context=context,
        budget=StaffingBudget(),
    )
    decision = verify_staffing(
        review, proposal, (contract,), context=context, budget=StaffingBudget()
    )
    assert decision.accepted
    assert decision.units[0].selected == (slug,)
