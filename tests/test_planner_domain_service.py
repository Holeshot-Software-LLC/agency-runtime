"""AR-384 / ADR-0201: the planner sees, and is held to, what the roster serves.

The planner used to draw a unit's domains from the union of every declared
domain and nothing said which of them any worker could actually be staffed on
under the unit's authority. On the 2026-09-03 install smoke every plan-authority
unit that named ``platform`` had exactly one eligible coverer, an API platform
planner, because the operating system's platform and the roster's platform
domain are homonyms, and ``desktop`` had none: the recruiter was rejected for
not ranking the wrong neighbour and vetoed when it did. These tests pin the
replacement contract: the planner is shown, per artifact kind, the domains some
worker serves under that kind's authority on this host; a unit none of whose
domains is served can staff nobody and is rejected with a repairable code
before the recruiter sees it; a unit with one served domain passes, because
ADR-0198 waives the rest; and the API platform card no longer carries the
infrastructure domain that made it the wrong neighbour.
"""

from __future__ import annotations

import json
from typing import Any

from agency_runtime.core.config import AgencyConfig, ProviderEntry, WorkforceConfig
from agency_runtime.core.roster.workforce import WorkforceIndexSnapshot
from agency_runtime.core.structured_provider import StructuredProviderResult
from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    AuditContract,
    CompositionContract,
    WorkforceContract,
    _domains,
    workforce_index_fingerprint,
)
from agency_runtime.core.workforce.inference import plan_and_staff_workforce
from agency_runtime.core.workforce.intent import (
    COMPACT_INTENT_SYSTEM,
    compact_intent_taxonomy,
    served_domains_by_artifact_kind,
)
from agency_runtime.core.workforce.plan_policy import (
    PLAN_POLICY_VIOLATION_CODES,
    plan_policy_repair_guidance,
    plan_policy_violations,
)
from agency_runtime.core.workforce.planning_contracts import WorkUnit, WorkUnitPlan
from agency_runtime.core.workforce.recruiter_index import (
    project_recruiter_index_record,
    recruiter_index_fingerprint,
    serialize_recruiter_index,
)
from agency_runtime.core.workforce.staffing_verifier import StaffingContext

_CODE = "plan_unit_domains_unserved"
_HASH = "sha256:" + "a" * 64
_GENERATION = 7
_TOOLS = frozenset(
    {"code-execution", "repository-read", "repository-write", "shell-execution", "test-execution"}
)
_UNIT = "unit-install-plan"


def _contract(
    agent_id: str,
    *,
    artifacts: tuple[str, ...] = ("plan", "analysis", "review-report"),
    lifecycles: tuple[str, ...] = ("discovery", "planning", "review"),
    authority: str = "plan",
    domains: tuple[str, ...] = ("specialist-services", "operations"),
    capabilities: tuple[str, ...] = ("analysis", "planning", "review"),
    platforms: tuple[str, ...] = ("windows", "linux"),
    enabled: bool = True,
) -> WorkforceContract:
    return WorkforceContract(
        schema_version=WORKFORCE_CONTRACT_SCHEMA_VERSION,
        worker_id=f"worker:{agent_id}",
        agent_id=agent_id,
        display_name=agent_id.replace("-", " ").title(),
        archetype="planner" if authority == "plan" else "implementer",
        outcomes=(f"{agent_id} outcome",),
        capability_ids=capabilities,
        artifact_kinds=artifacts,
        lifecycle_phases=lifecycles,
        domains=domains,
        stacks=(),
        scope_qualifiers=(),
        not_for=(),
        authority=authority,
        context_mode="isolated_only",
        tool_classes=("repository-read",),
        hosts=("codex", "claude", "openclaw", "hermes"),
        platforms=platforms,
        composition=CompositionContract(independence_class=agent_id),
        audit=AuditContract(status="approved", revision="1", contract_valid=True),
        version=_HASH,
        version_hash=_HASH,
        enabled=enabled,
        employment="employee" if enabled else "disabled",
        origin="upstream",
    )


def _operations_manager() -> WorkforceContract:
    return _contract("operations-manager")


def _desktop_engineer() -> WorkforceContract:
    return _contract(
        "desktop-app-engineer",
        artifacts=("implementation-change", "analysis"),
        lifecycles=("discovery", "implementation", "testing"),
        authority="modify",
        domains=("software-engineering", "desktop"),
        capabilities=("analysis", "implementation", "testing"),
    )


def _devops_automator() -> WorkforceContract:
    return _contract(
        "devops-automator",
        artifacts=("implementation-change", "analysis", "review-report"),
        lifecycles=("discovery", "implementation", "review"),
        authority="modify",
        domains=("software-engineering", "platform"),
        capabilities=("analysis", "implementation", "review"),
    )


def _windows_only_planner() -> WorkforceContract:
    return _contract("windows-finance-planner", domains=("finance",), platforms=("windows",))


def _disabled_planner() -> WorkforceContract:
    return _contract("retired-health-planner", domains=("healthcare",), enabled=False)


def _roster() -> tuple[WorkforceContract, ...]:
    return (
        _operations_manager(),
        _desktop_engineer(),
        _devops_automator(),
        _windows_only_planner(),
        _disabled_planner(),
    )


def _context(*, platform: str = "linux", tools: frozenset[str] = _TOOLS) -> StaffingContext:
    return StaffingContext("codex", platform, tools, _GENERATION)


def _unit(
    unit_id: str,
    *,
    artifact: str = "plan",
    lifecycle: str = "planning",
    authority: str = "plan",
    mutation: str = "read_only",
    domains: tuple[str, ...] = ("desktop", "platform"),
) -> WorkUnit:
    return WorkUnit(
        unit_id=unit_id,
        outcome="Plan the editor installation on this machine.",
        artifact_kind=artifact,
        lifecycle_phase=lifecycle,
        domains=domains,
        languages=(),
        frameworks=(),
        required_capabilities=("planning",),
        authority=authority,
        mutation_scope=mutation,
        risks=(),
        trust_boundaries=("repository",),
        claims=(),
        depends_on=(),
        resources=("request",),
        required_tools=("repository-read",),
        platforms=("linux",),
        acceptance_evidence=("The install plan names the supported method.",),
        parallelization="unspecified",
    )


def _plan(*units: WorkUnit) -> WorkUnitPlan:
    return WorkUnitPlan(
        schema_version=2,
        request_summary="Install the editor on the machine.",
        units=units,
        plan_hash="sha256:" + "c" * 64,
    )


_REQUEST = "Put this editor on my machine."


def test_served_domains_follow_the_authority_the_artifact_kind_implies() -> None:
    served = served_domains_by_artifact_kind(_roster(), _context())

    # Plan authority admits only plan-authority workers: the operations manager
    # serves operations, while the desktop and platform implementers do not,
    # which is exactly the captured collision.
    assert served["plan"] == ("operations", "specialist-services")
    assert "desktop" not in served["plan"]
    assert "platform" not in served["plan"]
    # Modify authority admits the implementers and not the planner.
    assert served["implementation-change"] == ("desktop", "platform", "software-engineering")
    assert "operations" not in served["implementation-change"]
    # Read-only discovery admits an implementer inspecting its own specialty
    # (the verifier's analysis special case), so every domain is served there.
    assert {"desktop", "platform", "operations"} <= set(served["analysis"])
    # No fixture worker holds review authority.
    assert served["review-report"] == ()
    assert served["test-evidence"] == ()
    assert set(served) == {
        "analysis",
        "architecture-record",
        "documentation",
        "implementation-change",
        "plan",
        "review-report",
        "test-code",
        "test-evidence",
    }


def test_served_domains_respect_host_platform_tools_and_enablement() -> None:
    roster = _roster()

    on_linux = served_domains_by_artifact_kind(roster, _context())
    on_windows = served_domains_by_artifact_kind(roster, _context(platform="windows"))
    assert "finance" not in on_linux["plan"]
    assert "finance" in on_windows["plan"]

    # A disabled worker serves nothing, whatever it declares.
    assert "healthcare" not in on_linux["plan"]
    assert "healthcare" not in on_windows["plan"]

    # The kinds that derive code-execution or test-execution have nothing
    # proven on a host that proved only repository access; that is an empty
    # tuple, never an absent key, so the caller can tell the two apart.
    read_only_host = served_domains_by_artifact_kind(
        roster, _context(tools=frozenset({"repository-read"}))
    )
    assert read_only_host["implementation-change"] == ()
    assert read_only_host["test-code"] == ()
    assert read_only_host["plan"] == ("operations", "specialist-services")


def test_subject_domains_do_not_veto_a_plan() -> None:
    served = served_domains_by_artifact_kind(_roster(), _context())

    assert _CODE not in plan_policy_violations(
        _REQUEST, _plan(_unit(_UNIT, domains=("desktop", "platform"))), served_domains=served
    )
    assert _CODE not in plan_policy_violations(
        _REQUEST, _plan(_unit(_UNIT, domains=("platform",))), served_domains=served
    )
    # One served domain is enough: ADR-0198 waives the rest and records them,
    # so the captured helix shape (desktop beside operations) still passes.
    assert (
        plan_policy_violations(
            _REQUEST, _plan(_unit(_UNIT, domains=("desktop", "operations"))), served_domains=served
        )
        == ()
    )
    # A modify unit naming the same two domains is served by the implementers.
    assert (
        plan_policy_violations(
            _REQUEST,
            _plan(
                _unit(
                    "unit-install",
                    artifact="implementation-change",
                    lifecycle="implementation",
                    authority="modify",
                    mutation="workspace_write",
                    domains=("desktop", "platform"),
                )
            ),
            served_domains=served,
            explicit_indivisible_unit=True,
        )
        == ()
    )


def test_only_the_offending_unit_needs_to_be_wrong() -> None:
    served = served_domains_by_artifact_kind(_roster(), _context())
    plan = _plan(
        _unit("unit-one", domains=("operations",)),
        _unit("unit-two", domains=("desktop", "platform")),
    )

    assert _CODE not in plan_policy_violations(_REQUEST, plan, served_domains=served)


def test_the_rule_is_topology_independent() -> None:
    """Like the tools rule, an explicit one-unit topology is still held to it."""

    served = served_domains_by_artifact_kind(_roster(), _context())

    assert _CODE not in plan_policy_violations(
        _REQUEST,
        _plan(_unit(_UNIT)),
        served_domains=served,
        explicit_indivisible_unit=True,
    )


def test_nothing_proven_for_a_kind_defers_to_the_staffing_gate() -> None:
    served = served_domains_by_artifact_kind(_roster(), _context())
    review = _unit(
        "unit-review",
        artifact="review-report",
        lifecycle="review",
        authority="review",
        domains=("platform",),
    )

    # No fixture worker holds review authority, so the kind proves nothing and
    # the unit is left to the recruiter and the verifier.
    assert served["review-report"] == ()
    assert plan_policy_violations(_REQUEST, _plan(review), served_domains=served) == ()
    # Without a served view at all the rule is inert.
    assert plan_policy_violations(_REQUEST, _plan(_unit(_UNIT))) == ()
    assert plan_policy_violations(_REQUEST, _plan(_unit(_UNIT)), served_domains={}) == ()


def test_runtime_chosen_domains_are_never_the_planners_fault() -> None:
    # The compiler puts every test artifact in quality-assurance whatever the
    # planner wrote, and it maps prose synonyms onto security, software
    # engineering and workforce governance. Replanning cannot change those, so
    # a unit carrying only such domains is never rejected here; if the roster
    # cannot serve them the recruiter's gap is the honest outcome.
    served = {"test-evidence": ("operations",), "plan": ("operations",)}
    evidence = _unit(
        "unit-evidence",
        artifact="test-evidence",
        lifecycle="testing",
        authority="review",
        domains=("quality-assurance",),
    )
    governance = _unit("unit-audit", domains=("workforce-governance",))

    assert plan_policy_violations(_REQUEST, _plan(evidence), served_domains=served) == ()
    assert plan_policy_violations(_REQUEST, _plan(governance), served_domains=served) == ()
    assert _CODE not in plan_policy_violations(
        _REQUEST, _plan(_unit(_UNIT, domains=("desktop",))), served_domains=served
    )


def test_a_declared_novel_domain_is_left_to_hiring_not_replanned() -> None:
    # The compiler admits a domain outside the vocabulary only beside a
    # declared novel_capability; that unit exists to reach the recruiter and
    # declare a hiring gap, so replanning it would take the gap away.
    served = served_domains_by_artifact_kind(_roster(), _context())
    known = frozenset({"operations", "specialist-services", "desktop", "platform"})
    novel = _unit("unit-quantum", domains=("quantum-build-systems",))

    assert (
        plan_policy_violations(_REQUEST, _plan(novel), served_domains=served, known_domains=known)
        == ()
    )
    # Known but unserved subjects are not execution-eligibility failures.
    assert _CODE not in plan_policy_violations(
        _REQUEST, _plan(_unit(_UNIT)), served_domains=served, known_domains=known
    )
    # The same descriptive treatment applies without a vocabulary.
    assert _CODE not in plan_policy_violations(_REQUEST, _plan(novel), served_domains=served)


def test_the_rejection_is_repairable_by_the_planner() -> None:
    """A code with no repair guidance would fail the plan without saying why."""

    assert _CODE in PLAN_POLICY_VIOLATION_CODES

    guidance = {
        row["code"]: row["required_correction"] for row in plan_policy_repair_guidance((_CODE,))
    }

    # The planner authors domains and artifact_kind; the guidance points it at
    # the served view for its own artifact kind and names the homonym trap.
    assert "domains_by_artifact_kind" in guidance[_CODE]
    assert "artifact_kind" in guidance[_CODE]
    assert "host_context" in guidance[_CODE]


def test_the_taxonomy_carries_the_served_view_only_when_supplied() -> None:
    plain = compact_intent_taxonomy(("operations", "desktop"), ("python",), ("planning",))
    assert "domains_by_artifact_kind" not in plain

    served = compact_intent_taxonomy(
        ("operations", "desktop"),
        ("python",),
        ("planning",),
        served_domains={"plan": ("specialist-services", "operations"), "analysis": ()},
    )
    # Sorted on both axes so the prompt, and therefore the planner cache
    # identity, is stable across roster orderings.
    assert list(served["domains_by_artifact_kind"]) == ["analysis", "plan"]
    assert served["domains_by_artifact_kind"]["plan"] == ["operations", "specialist-services"]
    assert served["domains_by_artifact_kind"]["analysis"] == []
    assert served["known_domains"] == ["desktop", "operations"]


def test_the_planner_prompt_states_the_served_view_contract() -> None:
    assert "planning_taxonomy.domains_by_artifact_kind" in COMPACT_INTENT_SYSTEM
    assert "host_context.platform" in COMPACT_INTENT_SYSTEM
    # The prompt still keeps the vocabulary rule the served view refines.
    assert "planning_taxonomy.known_domains" in COMPACT_INTENT_SYSTEM


def test_the_api_platform_card_no_longer_carries_the_infrastructure_domain() -> None:
    # The captured collision: platform-engineering promoted the API platform
    # planner into the platform domain, making it the roster's only plan-
    # authority coverer of the operating system's platform. It keeps backend
    # from api-design; the infrastructure cards keep platform.
    api = _domains(
        {"categories": ["engineering", "api-design", "platform-engineering"]}, "engineering"
    )
    infrastructure = _domains(
        {"categories": ["engineering", "devops", "infrastructure"]}, "engineering"
    )

    assert api == ("software-engineering", "backend")
    assert "platform" not in api
    assert "platform" in infrastructure


def _snapshot(*contracts: WorkforceContract) -> WorkforceIndexSnapshot:
    records = tuple(project_recruiter_index_record(item) for item in contracts)
    return WorkforceIndexSnapshot(
        generation=_GENERATION,
        worker_count=len(contracts),
        contracts=contracts,
        contract_fingerprint=workforce_index_fingerprint(contracts),
        recruiter_fingerprint=recruiter_index_fingerprint(records),
        recruiter_index=serialize_recruiter_index(records),
    )


def _result(value: dict[str, Any]) -> StructuredProviderResult:
    return StructuredProviderResult(
        value=value,
        provider_name="task-agency-router",
        provider_type="litellm",
        transport="",
        requested_model="router-alias",
        model_group="router-alias",
        actual_model="gpt-5.6-mini",
        model_receipt_source="response.body.model",
        latency_ms=17,
    )


def _compact_plan(domains: list[str]) -> dict[str, Any]:
    return {
        "request_summary": "Install the editor on the machine.",
        "units": [
            {
                "unit_id": _UNIT,
                "outcome": "Plan the editor installation using the supported method.",
                "artifact_kind": "plan",
                "domains": domains,
                "stacks": [],
                "capability_ids": ["planning", "operations"],
                "novel_capability": "",
                "depends_on": [],
            }
        ],
    }


def _nomination() -> dict[str, Any]:
    return {
        "units": [
            {
                "unit_id": _UNIT,
                "decision": "staff",
                "ranked_semantic": [
                    {
                        "agent_id": "operations-manager",
                        "score": 0.86,
                        "classification": "required",
                        "positive_evidence": ["operations-planning-coverage"],
                        "negative_evidence": [],
                    }
                ],
            }
        ]
    }


def test_descriptive_domain_difference_does_not_spend_a_planner_retry() -> None:
    # The captured 2026-09-03 shape: the planner names the machine (desktop,
    # platform) on the install plan; before ADR-0201 that unit reached the
    # recruiter, which was rejected for not ranking the API platform planner
    # or vetoed when it did. Now the compiler rejects the plan with a named
    # code, the repair prompt carries the served view, and the corrected plan
    # staffs the operations manager first time.
    snapshot = _snapshot(_operations_manager(), _desktop_engineer(), _devops_automator())
    responses = iter(
        (
            _result(_compact_plan(["desktop", "platform"])),
            _result(_nomination()),
        )
    )
    calls: list[tuple[str, str]] = []

    def invoke(_provider, prompt, _schema, *, system_prompt, timeout=None):
        calls.append((system_prompt, prompt))
        return next(responses)

    config = AgencyConfig(
        providers=(
            ProviderEntry(
                name="task-agency-router",
                type="litellm",
                model="router-alias",
                base_url="https://router.example.test/v1",
                api_key="secret",
                timeout=5,
            ),
        ),
        workforce=WorkforceConfig(mode="balanced", balanced_call_budget=4),
    )
    outcome = plan_and_staff_workforce(
        _REQUEST,
        snapshot,
        config=config,
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    assert [attempt.stage for attempt in outcome.attempts] == ["planner", "recruiter"]
    assert [attempt.status for attempt in outcome.attempts] == ["applied", "applied"]

    first_system, first_prompt = calls[0]
    taxonomy = json.loads(first_prompt)["planning_taxonomy"]
    assert first_system == COMPACT_INTENT_SYSTEM
    assert taxonomy["domains_by_artifact_kind"]["plan"] == ["operations", "specialist-services"]
    assert taxonomy["domains_by_artifact_kind"]["implementation-change"] == [
        "desktop",
        "platform",
        "software-engineering",
    ]

    recruiter_plan = json.loads(calls[1][1])["plan"]
    assert [unit["domains"] for unit in recruiter_plan["units"]] == [["desktop", "platform"]]
    assert outcome.staffing.units[0].selected == ("operations-manager",)
    assert outcome.staffing.abstention_reasons == ()
