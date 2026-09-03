"""AR-386 / ADR-0200: the strict critic is bound to the advisory doctrine and its veto is named.

Once AR-384 let the verifier accept install-flavoured plans, the strict critic
became the gate and closed it every time. Two of its four captured codes were
fair; two contradicted the doctrine that Agency supplies expertise and never
executes: ``selected-team-lacks-live-installation-authority`` demanded an
authority no worker can hold, and ``missing-implementation-lifecycle-assurance``
demanded assurance for mutation work the planner had not planned. Nothing in
the critic's contract or system prompt said the workforce is advisory, that a
waived coverage gap is a roster fact, or that a plan-authority unit for
host-side work is the intended shape. And the veto itself reached no durable
receipt: the staffing decision was replaced by one ``staffing_critic_rejected``
reason and the critic's codes survived only in the routing result's error
string.

These tests pin the replacement: the doctrine is stated in the contract and
the system prompt, and a veto's codes ride beside the verifier's on the
staffing decision in projected form, so the preflight-failure receipt, the
routing receipt and the fail-open disclosure all name it, bounded.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from agency_runtime.core.config import AgencyConfig, ProviderEntry, WorkforceConfig
from agency_runtime.core.fail_open_disclosure import (
    MAX_FAIL_OPEN_DISCLOSURE_CHARS,
    render_fail_open_disclosure,
)
from agency_runtime.core.preflight_failure import preflight_staffing_reason_codes
from agency_runtime.core.roster.workforce import WorkforceIndexSnapshot
from agency_runtime.core.selector.receipt_projection import (
    normalize_durable_routing_receipt,
    project_durable_routing_receipt,
)
from agency_runtime.core.structured_provider import StructuredProviderResult
from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    AuditContract,
    CompositionContract,
    WorkforceContract,
    workforce_index_fingerprint,
)
from agency_runtime.core.workforce.inference import (
    _CRITIC_NEVER_VETO_FOR,
    _CRITIC_SYSTEM,
    _CRITIC_VETO_GROUNDS,
    _critic_receipt_codes,
    plan_and_staff_workforce,
)
from agency_runtime.core.workforce.recruiter_index import (
    project_recruiter_index_record,
    recruiter_index_fingerprint,
    serialize_recruiter_index,
)
from agency_runtime.core.workforce.staffing_verifier import (
    ROSTER_COVERAGE_GAP,
    AbstentionReason,
    StaffingContext,
)

_HASH = "sha256:" + "a" * 64
_GENERATION = 7
_UNIT = "unit-install-plan"
# The two captured codes that contradict the doctrine, and the two that do not.
_AUTHORITY_CODE = "selected-team-lacks-live-installation-authority"
_LIFECYCLE_CODE = "missing-implementation-lifecycle-assurance"
_FAIR_CODES = ("wrong-neighbor-selection", "planner-domain-mismatch")


def _contract(
    agent_id: str,
    *,
    authority: str = "plan",
    artifact: str = "plan",
    lifecycle: str = "planning",
    domains: tuple[str, ...] = ("operations",),
    capabilities: tuple[str, ...] = ("analysis", "planning", "review"),
) -> WorkforceContract:
    return WorkforceContract(
        schema_version=WORKFORCE_CONTRACT_SCHEMA_VERSION,
        worker_id=f"worker:{agent_id}",
        agent_id=agent_id,
        display_name=agent_id.replace("-", " ").title(),
        archetype="planner" if authority == "plan" else "implementer",
        outcomes=(f"{agent_id} outcome",),
        capability_ids=capabilities,
        artifact_kinds=(artifact,),
        lifecycle_phases=(lifecycle,),
        domains=domains,
        stacks=(),
        scope_qualifiers=(),
        not_for=(),
        authority=authority,
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


def _desktop_engineer() -> WorkforceContract:
    # The captured shape: the only desktop contract carries modify authority,
    # so domain:desktop is a waived roster coverage gap on a plan unit.
    return _contract(
        "desktop-app-engineer",
        authority="modify",
        artifact="implementation-change",
        lifecycle="implementation",
        domains=("software-engineering", "desktop"),
        capabilities=("analysis", "implementation", "testing"),
    )


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


def _context() -> StaffingContext:
    return StaffingContext(
        "codex",
        "linux",
        frozenset({"native-delegation", "repository-read", "shell-execution"}),
        _GENERATION,
    )


def _config() -> AgencyConfig:
    return AgencyConfig(
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
        workforce=WorkforceConfig(mode="strict", strict_call_budget=4),
    )


def _result(value: dict[str, Any]) -> StructuredProviderResult:
    return StructuredProviderResult(
        value=value,
        provider_name="task-agency-router",
        provider_type="litellm",
        transport="",
        requested_model="router-alias",
        model_group="router-alias",
        actual_model="critic-model",
        model_receipt_source="response.body.model",
        latency_ms=17,
    )


_PLAN = {
    "request_summary": "Install the editor on the machine.",
    "units": [
        {
            "unit_id": _UNIT,
            "outcome": "Plan the editor install using the supported method.",
            "artifact_kind": "plan",
            "domains": ["desktop", "operations"],
            "stacks": [],
            "capability_ids": ["planning", "operations"],
            "novel_capability": "",
            "depends_on": [],
        }
    ],
}
_NOMINATION = {
    "units": [
        {
            "unit_id": _UNIT,
            "decision": "staff",
            "ranked_semantic": [
                {
                    "agent_id": "operations-manager",
                    "score": 0.84,
                    "classification": "required",
                    "positive_evidence": ["operations-planning-coverage"],
                    "negative_evidence": [],
                },
                {
                    "agent_id": "desktop-app-engineer",
                    "score": 0.55,
                    "classification": "acceptable",
                    "positive_evidence": ["desktop-context"],
                    "negative_evidence": [],
                },
            ],
        }
    ]
}


def _run(critic_reply: dict[str, Any]) -> tuple[Any, list[dict[str, Any]]]:
    replies = iter((_result(_PLAN), _result(_NOMINATION), _result(critic_reply)))
    prompts: list[dict[str, Any]] = []

    def invoke(*args, **_kwargs):
        prompts.append(json.loads(args[1]))
        return next(replies)

    outcome = plan_and_staff_workforce(
        "Put this editor on my machine.",
        _snapshot(_contract("operations-manager"), _desktop_engineer()),
        config=_config(),
        context=_context(),
        invoker=invoke,
    )
    return outcome, prompts


def _routing(outcome: Any) -> dict[str, Any]:
    return {
        "trace_id": "trace-critic-veto",
        "query_hash": "a" * 64,
        "context_fingerprint": "c" * 64,
        "selected_ids": [],
        "semantic_ids": [],
        "confidence": 0.0,
        "top_score": 0.0,
        "latency_ms": 17,
        "candidate_count": 2,
        "status": outcome.status,
        "source": "inference",
        "inference_configured": True,
        "inference_required": True,
        "inference_attempted": True,
        "inference_mode": outcome.inference_mode,
        "provider_attempts": [],
        "workforce_proposal": outcome.proposal.as_dict(),
        "workforce_staffing": outcome.staffing.as_dict(),
    }


def test_the_critic_contract_and_system_prompt_state_the_advisory_doctrine() -> None:
    outcome, prompts = _run({"approved": True, "reason_codes": []})

    assert outcome.accepted
    critic_prompt = prompts[2]
    contract = critic_prompt["critic_contract"]
    assert contract["workforce_is_advisory"] is True
    assert contract["execution_authority_holder"] == "host"
    assert contract["selected_authority_bound_by_eligibility"] is True
    assert contract["roster_coverage_gaps_are_runtime_waivers"] is True
    assert contract["plan_authority_units_for_host_side_work_are_intended"] is True
    assert contract["veto_grounds"] == list(_CRITIC_VETO_GROUNDS)
    assert contract["never_veto_for"] == list(_CRITIC_NEVER_VETO_FOR)
    assert "execution-or-installation-authority" in contract["never_veto_for"]
    assert "waived-roster-coverage-gaps" in contract["never_veto_for"]
    # The waived gap the critic is told about is the one the verifier recorded.
    reasons = critic_prompt["verified_staffing"]["abstention_reasons"]
    assert [(item["code"], item["detail"]) for item in reasons] == [
        (ROSTER_COVERAGE_GAP, "domain:desktop")
    ]
    # The system prompt says the same in words the critic reads first.
    for phrase in (
        "Agency is advisory",
        "never executes anything",
        "the host applies the selected team's expertise",
        "No worker can or need hold live authority",
        "plan-authority or review-authority unit for host-side work",
        "roster_coverage_gap",
        "never a team defect",
        "implementation unit the planner did not plan",
    ):
        assert phrase in _CRITIC_SYSTEM, phrase
    assert "Reject only a specific wrong-neighbor selection" in _CRITIC_SYSTEM


def test_an_approval_leaves_the_verified_decision_and_its_advisories_untouched() -> None:
    outcome, _prompts = _run({"approved": True, "reason_codes": []})

    assert outcome.accepted
    assert outcome.staffing.units[0].selected == ("operations-manager",)
    assert outcome.staffing.abstention_reasons == (
        AbstentionReason(ROSTER_COVERAGE_GAP, _UNIT, "", "domain:desktop"),
    )
    assert outcome.abstention_codes == ()


def test_a_veto_reaches_both_receipts_and_the_disclosure_beside_the_verifier_codes() -> None:
    outcome, _prompts = _run({"approved": False, "reason_codes": [_AUTHORITY_CODE, *_FAIR_CODES]})

    assert not outcome.accepted
    assert outcome.status == "inference_invalid"
    # The routing result keeps the raw codes exactly as before.
    assert outcome.abstention_codes == (
        "inference_invalid",
        "staffing_critic_rejected",
        _AUTHORITY_CODE,
        *_FAIR_CODES,
    )
    # The staffing decision now carries the projected codes beside the class.
    assert outcome.staffing.status == "abstained"
    assert outcome.staffing.abstention_reasons == (
        AbstentionReason("staffing_critic_rejected"),
        AbstentionReason("critic_selected_team_lacks_live_installation_authority"),
        AbstentionReason("critic_wrong_neighbor_selection"),
        AbstentionReason("critic_planner_domain_mismatch"),
    )

    routing = _routing(outcome)
    # The preflight-failure receipt's staffing codes admit the underscore form.
    staffing_codes = preflight_staffing_reason_codes(routing)
    assert staffing_codes == [
        "staffing_critic_rejected",
        "critic_selected_team_lacks_live_installation_authority",
        "critic_wrong_neighbor_selection",
        "critic_planner_domain_mismatch",
    ]
    # The routing receipt's global codes carry them too, and round-trip.
    receipt = project_durable_routing_receipt(routing)
    assert receipt["staffing"]["global_reason_codes"] == staffing_codes
    assert receipt["staffing"]["status"] == "abstained"
    assert normalize_durable_routing_receipt(receipt) == receipt
    # The fail-open disclosure names the veto and stays inside its budget.
    line = render_fail_open_disclosure("workforce_inference_failed", staffing_codes)
    assert (
        "staffing_critic_rejected, critic_selected_team_lacks_live_installation_authority" in line
    )
    assert len(line) <= MAX_FAIL_OPEN_DISCLOSURE_CHARS


def test_projected_codes_are_bounded_and_carry_no_prose() -> None:
    assert _critic_receipt_codes(("Wrong-Neighbor-Selection ",)) == (
        "critic_wrong_neighbor_selection",
    )
    # Sixteen at most, duplicates folded once projected.
    many = (*(f"defect-{index}" for index in range(20)), "defect-0")
    projected = _critic_receipt_codes(many)
    assert len(projected) == 16
    assert projected[0] == "critic_defect_0" and projected[-1] == "critic_defect_15"
    # A code that would not fit the receipt bound is dropped, not cut.
    assert _critic_receipt_codes(("x" * 60, "fits")) == ("critic_fits",)
    # Anything outside the closed charset is dropped too.
    assert _critic_receipt_codes(("has space", "has.dot", "", "ok-code")) == ("critic_ok_code",)
    # Four codes at the bound still fit the disclosure line.
    longest = tuple("a" * 49 + f"-{index}" for index in range(4))
    line = render_fail_open_disclosure(
        "workforce_inference_failed",
        ["staffing_critic_rejected", *_critic_receipt_codes(longest)],
    )
    assert len(line) <= MAX_FAIL_OPEN_DISCLOSURE_CHARS


def test_the_captured_doctrine_breaking_codes_are_named_as_never_grounds() -> None:
    # The contract lists, in words, the grounds the two contradicting captured
    # codes stood on, so a critic that reads its contract has no basis for them.
    assert _AUTHORITY_CODE not in _CRITIC_VETO_GROUNDS
    assert _LIFECYCLE_CODE not in _CRITIC_VETO_GROUNDS
    assert "execution-or-installation-authority" in _CRITIC_NEVER_VETO_FOR
    assert "implementation-units-the-planner-did-not-plan" in _CRITIC_NEVER_VETO_FOR
    assert set(_CRITIC_VETO_GROUNDS).isdisjoint(_CRITIC_NEVER_VETO_FOR)
    # The fair codes remain expressible as grounds of the same kind.
    assert "wrong-neighbor-selection" in _CRITIC_VETO_GROUNDS
    assert replace  # keep the dataclass helper import honest for future fixtures
