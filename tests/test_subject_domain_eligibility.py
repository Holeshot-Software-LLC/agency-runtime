"""AR-402: subject labels must not silently grant or remove execution authority."""

from dataclasses import asdict, replace

import pytest

from agency_runtime.core.installer import seed_starter_roster
from agency_runtime.core.roster.workforce import workforce_index_snapshot
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce.inference import _typed_shortlists
from agency_runtime.core.workforce.planning_contracts import parse_work_unit_plan
from agency_runtime.core.workforce.staffing_verifier import (
    StaffingBudget,
    StaffingContext,
    build_deterministic_proposal,
    typed_staffing_ineligibility,
    typed_staffing_requirements,
    verify_staffing,
)
from tests.test_workforce_dynamic_hiring import _unit


@pytest.fixture(scope="module")
def shipped_snapshot(tmp_path_factory):
    store = Store(tmp_path_factory.mktemp("shipped-domain-contracts") / "agency.db")
    seed_starter_roster(store)
    return workforce_index_snapshot(store, disabled_agents=())


def _context(snapshot, host="codex"):
    return StaffingContext(
        host,
        "linux",
        frozenset({"repository-read", "repository-write", "shell-execution", "native-delegation"}),
        snapshot.generation,
    )


@pytest.mark.parametrize("host", ["claude", "codex", "hermes", "openclaw", "zcode"])
def test_backend_implementation_does_not_require_roblox(shipped_snapshot, host) -> None:
    snapshot = shipped_snapshot
    contracts = {contract.agent_id: contract for contract in snapshot.contracts}
    unit = replace(
        _unit(),
        outcome="Implement rate limiting for a public API gateway",
        domains=("backend",),
        languages=(),
    )
    context = _context(snapshot, host)
    assert len(contracts) >= 282
    assert typed_staffing_ineligibility(unit, contracts["senior-developer"], context) == ()
    for slug in ("backend-architect", "api-platform-engineer"):
        assert contracts[slug].authority == "plan"
        assert "agent_authority_mismatch" in typed_staffing_ineligibility(
            unit, contracts[slug], context
        )
    assert not any(item.startswith("domain:") for item in typed_staffing_requirements(unit))


@pytest.mark.parametrize(
    "domains,artifact,lifecycle,capability,authority,slug",
    [
        (
            ("backend", "frontend"),
            "implementation-change",
            "implementation",
            "implementation",
            "modify",
            "senior-developer",
        ),
        (
            ("frontend",),
            "implementation-change",
            "implementation",
            "implementation",
            "modify",
            "frontend-developer",
        ),
        (
            ("operations",),
            "implementation-change",
            "implementation",
            "implementation",
            "modify",
            "devops-automator",
        ),
        (("backend",), "review-report", "review", "review", "review", "code-reviewer"),
    ],
)
def test_representative_work_accepts_a_faithful_audited_nominee(
    shipped_snapshot, domains, artifact, lifecycle, capability, authority, slug
) -> None:
    unit = replace(
        _unit(),
        domains=domains,
        languages=(),
        artifact_kind=artifact,
        lifecycle_phase=lifecycle,
        required_capabilities=(capability,),
        authority=authority,
        mutation_scope="workspace_write" if authority == "modify" else "read_only",
    )
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "One explicitly indivisible work unit",
            "units": [asdict(unit)],
        }
    )
    context = _context(shipped_snapshot)
    proposal = build_deterministic_proposal(
        plan,
        shipped_snapshot.contracts,
        {unit.unit_id: [(slug, 1.0)]},
        context=context,
        budget=StaffingBudget(),
        semantic_required={unit.unit_id: frozenset({slug})},
    )
    decision = verify_staffing(
        plan, proposal, shipped_snapshot.contracts, context=context, budget=StaffingBudget()
    )
    assert decision.accepted, decision.abstention_reasons
    assert proposal.units[0].selected == (slug,)
    [recall] = _typed_shortlists(plan, shipped_snapshot.contracts, context=context)
    assert not any(token.startswith("domain:") for token in recall["requirements"])
    assert all(contract.domains for contract in shipped_snapshot.contracts)


def test_explicit_out_of_scope_and_authority_still_reject(shipped_snapshot) -> None:
    senior = next(c for c in shipped_snapshot.contracts if c.agent_id == "senior-developer")
    unit = replace(_unit(), outcome="Implement rate limiting", domains=("backend",), languages=())
    excluded = replace(senior, not_for=("rate limiting",))
    assert "agent_explicitly_out_of_scope" in typed_staffing_ineligibility(
        unit, excluded, _context(shipped_snapshot)
    )
