"""AR-374: the host capability floor and the roster's tool demand must not drift apart.

Measured against the bundled manifest: every execution host proves the same nine
capabilities, the roster demands 246 distinct tool classes, and 238 of them no
host can prove. Only 8 of the 9 proven capabilities are demanded at all.

That gap is not itself a staffing failure. ``agent_tools_missing`` is raised
against ``unit.required_tools`` and never against a contract's declared
``tool_classes`` (see ``staffing_verifier._eligibility``), so a card demanding
``browser-interaction`` stays eligible for work that does not need a browser.
Re-gating contracts on their declared tools would make 238 tool classes into
permanent ineligibility for most of the roster, which is exactly the failure
AR-374 was filed to describe.

The nine are a floor, not a ceiling: ``native_adapter_capability_receipt``
unions whatever an adapter proves on top of them. No production adapter reports
anything today, so the floor is also the ceiling in practice.

These guards make either side moving a reviewable diff rather than a surprise.
"""

from __future__ import annotations

import json
from pathlib import Path

from agency_runtime.core.host_capabilities import (
    _NATIVE_HOST_CAPABILITIES,
    EXECUTION_HOSTS,
    canonicalize_tool_capabilities,
    native_adapter_capability_receipt,
)
from agency_runtime.core.roster import __file__ as _roster_init
from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    AuditContract,
    CompositionContract,
    WorkforceContract,
)
from agency_runtime.core.workforce.planning_contracts import WorkUnit
from agency_runtime.core.workforce.staffing_verifier import (
    StaffingContext,
    typed_staffing_ineligibility,
)

_BASELINE = Path(__file__).parent / "data" / "ar374_capability_vocabulary_baseline.json"
_MANIFEST = Path(_roster_init).parent / "data" / "manifest.json"
_HASH = "sha256:" + "b" * 64


def _baseline() -> dict[str, object]:
    return json.loads(_BASELINE.read_text(encoding="utf-8"))


def _demanded_tool_classes() -> set[str]:
    """Every tool class the bundled roster demands, canonicalized as the runtime does."""

    agents = json.loads(_MANIFEST.read_text(encoding="utf-8"))["agents"]
    demanded: set[str] = set()
    for agent in agents:
        canonical, unknown = canonicalize_tool_capabilities(agent.get("required_tools") or ())
        demanded.update(canonical)
        demanded.update(unknown)
    return demanded


def _contract(agent_id: str, *, tool_classes: tuple[str, ...]) -> WorkforceContract:
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
        stacks=(),
        scope_qualifiers=(),
        not_for=(),
        authority="modify",
        context_mode="isolated_only",
        tool_classes=tool_classes,
        hosts=tuple(EXECUTION_HOSTS),
        platforms=("windows", "linux"),
        composition=CompositionContract(independence_class=agent_id),
        audit=AuditContract(status="approved", revision="1", contract_valid=True),
        version=_HASH,
        version_hash=_HASH,
        enabled=True,
        employment="employee",
        origin="upstream",
    )


def _unit(*, required_tools: tuple[str, ...] = ()) -> WorkUnit:
    return WorkUnit(
        unit_id="unit-implement-fix",
        outcome="Implement the fix",
        artifact_kind="implementation-change",
        lifecycle_phase="implementation",
        domains=("software-engineering",),
        languages=(),
        frameworks=(),
        required_capabilities=("implementation",),
        authority="modify",
        mutation_scope="repository_write",
        risks=(),
        trust_boundaries=("repository",),
        claims=(),
        depends_on=(),
        resources=("repository",),
        required_tools=required_tools,
        platforms=("linux",),
        acceptance_evidence=("Tests pass",),
        parallelization="sequential",
    )


def _context(tools: frozenset[str]) -> StaffingContext:
    return StaffingContext("claude", "linux", tools, 1, None, detected_stacks=())


def test_every_execution_host_proves_the_recorded_capability_floor() -> None:
    expected = tuple(_baseline()["host_capability_floor"])

    assert tuple(EXECUTION_HOSTS) == tuple(_baseline()["execution_hosts"])
    for host in EXECUTION_HOSTS:
        assert tuple(sorted(_NATIVE_HOST_CAPABILITIES[host])) == expected, (
            f"{host} no longer proves the recorded capability floor; update "
            f"{_BASELINE.name} in the same change that moves it"
        )


def test_roster_demand_matches_the_recorded_unprovable_baseline() -> None:
    baseline = _baseline()
    floor = set(baseline["host_capability_floor"])
    recorded = set(baseline["unprovable_demanded_tool_classes"])

    demanded = _demanded_tool_classes()
    unprovable = demanded - floor

    added = sorted(unprovable - recorded)
    removed = sorted(recorded - unprovable)
    assert not added and not removed, (
        "the roster's tool vocabulary drifted from the host capability floor. "
        f"newly unprovable: {added}. no longer demanded: {removed}. "
        f"Justify the change, then update {_BASELINE.name}."
    )
    assert len(demanded) == baseline["distinct_demanded_tool_classes"]


def test_declared_tool_classes_are_not_a_production_eligibility_gate() -> None:
    """The 238-class gap must not become per-worker ineligibility."""

    floor = frozenset(_NATIVE_HOST_CAPABILITIES["claude"])
    unprovable = next(iter(sorted(set(_baseline()["unprovable_demanded_tool_classes"]))))
    worker = _contract("browser-heavy-engineer", tool_classes=("repository-read", unprovable))

    reasons = typed_staffing_ineligibility(_unit(), worker, _context(floor))

    assert "agent_tools_missing" not in reasons, (
        "a worker became ineligible for its own declared tool classes; that "
        "re-gates most of the roster into permanent ineligibility (AR-374)"
    )
    assert reasons == ()


def test_unit_required_tools_outside_the_host_floor_are_the_real_gate() -> None:
    floor = frozenset(_NATIVE_HOST_CAPABILITIES["claude"])
    unprovable = next(iter(sorted(set(_baseline()["unprovable_demanded_tool_classes"]))))
    worker = _contract("plain-engineer", tool_classes=("repository-read",))

    reasons = typed_staffing_ineligibility(
        _unit(required_tools=(unprovable,)), worker, _context(floor)
    )

    assert "agent_tools_missing" in reasons


def test_the_capability_floor_is_a_floor_and_not_a_ceiling() -> None:
    """An adapter that proves more must widen the receipt, never replace it."""

    extra = next(iter(sorted(set(_baseline()["unprovable_demanded_tool_classes"]))))

    receipt = native_adapter_capability_receipt(
        "claude",
        platform="linux",
        session_id="ar374-session",
        trace_id="ar374-turn",
        available_tools=(extra,),
    )

    assert set(_NATIVE_HOST_CAPABILITIES["claude"]) <= set(receipt.capabilities)
    assert extra in receipt.capabilities
