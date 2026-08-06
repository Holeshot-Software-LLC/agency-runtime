"""Per-axis stack wildcard: undeclared stacks defer to inference, declared enforce.

Only 4 of the ~280 roster contracts declare ``stacks``; every other axis is
fully enriched, so no contract qualifies for the all-axes wildcard. Before the
per-axis rule, any stack-bearing unit was provably unstaffable by 276 workers
and the recruiter prompt converted that into mandatory gaps — the primary
cause of turns ending with nobody staffed.
"""

from __future__ import annotations

from dataclasses import replace

from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    AuditContract,
    CompositionContract,
    WorkforceContract,
)
from agency_runtime.core.workforce.planning_contracts import WorkUnit
from agency_runtime.core.workforce.staffing_verifier import (
    typed_staffing_coverage,
    typed_staffing_requirements,
)

_HASH = "sha256:" + "a" * 64


def _contract(agent_id: str, *, stacks: tuple[str, ...] = ()) -> WorkforceContract:
    return WorkforceContract(
        schema_version=WORKFORCE_CONTRACT_SCHEMA_VERSION,
        worker_id=f"worker:{agent_id}",
        agent_id=agent_id,
        display_name=agent_id.replace("-", " ").title(),
        archetype="engineer",
        outcomes=("Implementation",),
        capability_ids=("implementation",),
        artifact_kinds=("implementation-change",),
        lifecycle_phases=("implementation",),
        domains=("software-engineering",),
        stacks=stacks,
        scope_qualifiers=(),
        not_for=(),
        authority="modify",
        context_mode="isolated_only",
        tool_classes=("repository-read",),
        hosts=("codex", "claude", "openclaw", "hermes"),
        platforms=("windows", "linux"),
        composition=CompositionContract(independence_class=agent_id),
        audit=AuditContract(status="approved", revision="1", contract_valid=True),
        version=_HASH,
        version_hash=_HASH,
        enabled=True,
        employment="employee",
        origin="upstream",
    )


def _unit() -> WorkUnit:
    return WorkUnit(
        unit_id="unit-implement-fix",
        outcome="Implement the fix",
        artifact_kind="implementation-change",
        lifecycle_phase="implementation",
        domains=("software-engineering",),
        languages=("python",),
        frameworks=(),
        required_capabilities=("implementation",),
        authority="modify",
        mutation_scope="repository_write",
        risks=(),
        trust_boundaries=("repository",),
        claims=(),
        depends_on=(),
        resources=("repository",),
        required_tools=(),
        platforms=("windows",),
        acceptance_evidence=("Tests pass",),
        parallelization="sequential",
    )


def test_undeclared_stacks_defer_stack_coverage_to_inference() -> None:
    unit = _unit()
    contract = _contract("python-engineer", stacks=())

    coverage = typed_staffing_coverage(unit, contract)

    assert "stack:python" in coverage
    assert set(typed_staffing_requirements(unit)) <= set(coverage)


def test_declared_stacks_still_enforce_exact_stack_matching() -> None:
    unit = _unit()
    wrong = _contract("php-engineer", stacks=("php",))
    right = _contract("py-engineer", stacks=("python",))

    assert "stack:python" not in typed_staffing_coverage(unit, wrong)
    assert "stack:python" in typed_staffing_coverage(unit, right)


def test_other_axes_keep_full_enforcement_for_typed_contracts() -> None:
    unit = _unit()
    wrong_domain = replace(_contract("other"), domains=("design-systems",))

    coverage = typed_staffing_coverage(unit, wrong_domain)

    assert "domain:software-engineering" not in coverage
    assert "stack:python" in coverage  # stack axis still deferred, not erased
