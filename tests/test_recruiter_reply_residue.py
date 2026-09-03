"""ADR-0202: read the recruiter's reply where no safety property lives, and never blank an attempt.

The MiniMax deployment that serves the recruiter route does not honour the
JSON schema's ``required`` list or its array types. Captured live on the
2026-09-03 eleven-wording run: a forbidden row arrived without its empty
``positive_evidence`` array (turn 202), the units array arrived wrapped one
level too deep (203), evidence arrays arrived as objects whose keys were the
codes (203's repair), an underscore ineligibility code Agency itself shows was
cited back as negative evidence (202's repair), and a repair reply was the
empty object (204). Separately, a reply the verifier rejected (207) reached the
durable receipt with neither validation failures nor a truncation record,
which AR-385's third criterion forbids. These tests pin the replacement
contract: the row reader defaults a missing evidence array and reads a
string-keyed object as its keys while every bound the validator enforces
still applies; a single wrapper is unwrapped and no further; a reply that is
not a units object is recorded per unit as ``missing_work_unit`` with the
``recruiter_response_shape_invalid`` diagnosis and repaired; and the verifier's
``unit=code`` rows project onto both receipts through the same entry point as
nomination failures.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from agency_runtime.core.config import AgencyConfig, ProviderEntry, WorkforceConfig
from agency_runtime.core.preflight_failure import project_preflight_provider_attempts
from agency_runtime.core.roster.workforce import WorkforceIndexSnapshot
from agency_runtime.core.selector.receipt_projection import project_nomination_failures
from agency_runtime.core.structured_provider import StructuredProviderResult
from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    AuditContract,
    CompositionContract,
    WorkforceContract,
    workforce_index_fingerprint,
)
from agency_runtime.core.workforce.inference import (
    RECRUITER_VALIDATION_REASON_CODES,
    _nomination_candidate_diagnostic,
    _nomination_rows,
    _NominationAccumulator,
    _NominationValidationError,
    _normalized_candidate_row,
    _StaffingVerificationError,
    plan_and_staff_workforce,
)
from agency_runtime.core.workforce.planning_contracts import parse_work_unit_plan
from agency_runtime.core.workforce.recruiter_index import (
    project_recruiter_index_record,
    recruiter_index_fingerprint,
    serialize_recruiter_index,
)
from agency_runtime.core.workforce.staffing_verifier import (
    AbstentionReason,
    StaffingContext,
    StaffingDecision,
)

_HASH = "sha256:" + "a" * 64
_GENERATION = 7
_UNIT = "unit-install-plan"
_SHAPE = "recruiter_response_shape_invalid"
_TOOLS = frozenset({"native-delegation", "repository-read", "shell-execution"})


def _contract(
    agent_id: str,
    *,
    artifact: str = "plan",
    lifecycle: str = "planning",
    authority: str = "plan",
    domains: tuple[str, ...] = ("specialist-services", "operations"),
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


def _roster() -> tuple[WorkforceContract, ...]:
    return (
        _contract("operations-manager"),
        _contract(
            "desktop-app-engineer",
            artifact="implementation-change",
            lifecycle="implementation",
            authority="modify",
            domains=("software-engineering", "desktop"),
            capabilities=("analysis", "implementation", "testing"),
        ),
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
    return StaffingContext("codex", "linux", _TOOLS, _GENERATION)


def _config(budget: int = 3) -> AgencyConfig:
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
        workforce=WorkforceConfig(mode="balanced", balanced_call_budget=budget),
    )


def _result(value: dict[str, Any]) -> StructuredProviderResult:
    return StructuredProviderResult(
        value=value,
        provider_name="task-agency-router",
        provider_type="litellm",
        transport="",
        requested_model="router-alias",
        model_group="router-alias",
        actual_model="minimax-m3",
        model_receipt_source="response.body.model",
        latency_ms=17,
    )


def _plan_document() -> dict[str, Any]:
    return {
        "request_summary": "Install the editor on the machine.",
        "units": [
            {
                "unit_id": _UNIT,
                "outcome": "Plan the editor installation using the supported method.",
                "artifact_kind": "plan",
                "domains": ["operations"],
                "stacks": [],
                "capability_ids": ["planning", "operations"],
                "novel_capability": "",
                "depends_on": [],
            }
        ],
    }


def _typed_plan():
    return parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Install the editor on the machine.",
            "units": [
                {
                    "unit_id": _UNIT,
                    "outcome": "Plan the editor installation using the supported method.",
                    "artifact_kind": "plan",
                    "lifecycle_phase": "planning",
                    "domains": ["operations"],
                    "languages": [],
                    "frameworks": [],
                    "required_capabilities": ["planning", "operations"],
                    "authority": "plan",
                    "mutation_scope": "read_only",
                    "risks": [],
                    "trust_boundaries": ["repository"],
                    "claims": [],
                    "depends_on": [],
                    "resources": ["repository"],
                    "required_tools": ["repository-read"],
                    "platforms": ["linux"],
                    "acceptance_evidence": ["The install plan names the supported method."],
                    "parallelization": "sequential",
                }
            ],
        }
    )


def _required_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "agent_id": "operations-manager",
        "score": 0.86,
        "classification": "required",
        "positive_evidence": ["operations-planning-coverage", "domain:operations"],
        "negative_evidence": [],
    }
    row.update(overrides)
    return row


def _nomination(*rows: dict[str, Any]) -> dict[str, Any]:
    return {
        "units": [
            {
                "unit_id": _UNIT,
                "decision": "staff",
                "ranked_semantic": list(rows or (_required_row(),)),
            }
        ]
    }


# Captured verbatim from turn 202, 2026-09-03: the deployment omitted the empty
# positive_evidence array on the forbidden row and every row failed as
# recruiter_candidate_row_shape_invalid.
_CAPTURED_FORBIDDEN_ROW_WITHOUT_POSITIVE = {
    "agent_id": "desktop-app-engineer",
    "classification": "forbidden",
    "negative_evidence": ["out-of-domain-editor-installation"],
    "score": 0.1,
}
# Captured from turn 203's repair: evidence as an object whose keys are the codes.
_CAPTURED_EVIDENCE_AS_OBJECT = {
    "agent_id": "operations-manager",
    "classification": "required",
    "negative_evidence": [],
    "positive_evidence": {"linux-cli-install-planning": "", "path-only-minimal-mutation": ""},
    "score": 0.82,
}
# Captured from turn 202's repair: the ineligibility vocabulary Agency shows,
# cited back as negative evidence.
_CAPTURED_UNDERSCORE_NEGATIVE = {
    "agent_id": "desktop-app-engineer",
    "classification": "forbidden",
    "positive_evidence": ["authority:modify", "capability:implementation"],
    "negative_evidence": ["agent_domain_mismatch", "desktop-binary-install-out-of-scope"],
    "score": 0.2,
}


# --- the row reader ---------------------------------------------------------


def test_a_missing_evidence_array_reads_as_empty() -> None:
    row = _normalized_candidate_row(_CAPTURED_FORBIDDEN_ROW_WITHOUT_POSITIVE)

    assert row is not None
    assert row["positive_evidence"] == []
    assert row["negative_evidence"] == ["out-of-domain-editor-installation"]
    known = {"desktop-app-engineer", "operations-manager"}
    assert (
        _nomination_candidate_diagnostic(
            _CAPTURED_FORBIDDEN_ROW_WITHOUT_POSITIVE, known=known, classifications={}
        )
        == ""
    )
    # The contract's own rule still applies to the defaulted value: a required
    # row with no positive evidence at all is still refused.
    required_without_positive = {
        "agent_id": "operations-manager",
        "classification": "required",
        "negative_evidence": [],
        "score": 0.8,
    }
    assert (
        _nomination_candidate_diagnostic(required_without_positive, known=known, classifications={})
        == "recruiter_candidate_positive_evidence_missing"
    )


def test_an_evidence_object_reads_as_its_keys_and_keeps_every_bound() -> None:
    known = {"operations-manager"}
    row = _normalized_candidate_row(_CAPTURED_EVIDENCE_AS_OBJECT)

    assert row is not None
    assert row["positive_evidence"] == ["linux-cli-install-planning", "path-only-minimal-mutation"]
    assert (
        _nomination_candidate_diagnostic(
            _CAPTURED_EVIDENCE_AS_OBJECT, known=known, classifications={}
        )
        == ""
    )
    # The bounds the validator enforces still apply to the normalised value.
    too_many = dict(
        _CAPTURED_EVIDENCE_AS_OBJECT, positive_evidence={f"c{i}": "" for i in range(17)}
    )
    prose = dict(_CAPTURED_EVIDENCE_AS_OBJECT, positive_evidence={"has devops experience": ""})
    for row in (too_many, prose):
        assert (
            _nomination_candidate_diagnostic(row, known=known, classifications={})
            == "recruiter_candidate_positive_evidence_invalid"
        )
    # An object with a non-string key is not a code list and stays invalid.
    odd = dict(_CAPTURED_EVIDENCE_AS_OBJECT, positive_evidence={1: ""})
    assert (
        _nomination_candidate_diagnostic(odd, known=known, classifications={})
        == "recruiter_candidate_positive_evidence_invalid"
    )


def test_the_row_shape_rule_still_refuses_what_carries_no_identity() -> None:
    known = {"operations-manager"}
    extra = _required_row(provider_private_field="PRIVATE")
    no_score = {k: v for k, v in _required_row().items() if k != "score"}
    no_identity = {k: v for k, v in _required_row().items() if k != "agent_id"}

    for row in (extra, no_score, no_identity, "a string", 7, None):
        assert _normalized_candidate_row(row) is None
        assert (
            _nomination_candidate_diagnostic(row, known=known, classifications={})
            == "recruiter_candidate_row_shape_invalid"
        )


def test_the_ineligibility_vocabulary_agency_shows_is_accepted_as_evidence() -> None:
    known = {"desktop-app-engineer"}

    assert (
        _nomination_candidate_diagnostic(
            _CAPTURED_UNDERSCORE_NEGATIVE, known=known, classifications={}
        )
        == ""
    )


# --- the reply reader -------------------------------------------------------


def test_one_wrapper_is_unwrapped_and_no_further() -> None:
    rows = [{"unit_id": _UNIT, "decision": "staff", "ranked_semantic": [_required_row()]}]

    assert _nomination_rows({"units": rows}, maximum=4) == rows
    # Captured from turn 203: the deployment wrapped the array once more.
    assert _nomination_rows({"units": [{"units": rows}]}, maximum=4) == rows
    # Two levels are not a reply the contract can read.
    assert _nomination_rows({"units": [{"units": [{"units": rows}]}]}, maximum=4) == [
        {"units": rows}
    ]
    for value in ({}, {"units": []}, {"units": "x"}, {"units": rows, "extra": 1}, [], "x", None):
        assert _nomination_rows(value, maximum=4) is None
    assert _nomination_rows({"units": rows * 5}, maximum=4) is None


def test_a_reply_that_is_not_a_units_object_is_recorded_per_unit_and_repairable() -> None:
    plan = _typed_plan()
    parser = _NominationAccumulator(
        plan, _snapshot(*_roster()), config=_config(), context=_context()
    )

    with pytest.raises(_NominationValidationError) as excinfo:
        parser.parse({})

    (failure,) = excinfo.value.failures
    assert failure.unit_id == _UNIT
    assert failure.code == "missing_work_unit"
    assert failure.diagnostic_code == _SHAPE
    assert _SHAPE in RECRUITER_VALIDATION_REASON_CODES
    assert str(excinfo.value) == f"workforce nomination failures: {_UNIT}=missing_work_unit"
    # The receipt reads the same detail and carries the unit and the diagnosis.
    (entry,) = project_preflight_provider_attempts(
        [
            {
                "stage": "recruiter",
                "provider_name": "agency-recruiter",
                "provider_type": "litellm",
                "status": "rejected",
                "reason_code": "provider_response_contract_invalid",
                "validation_detail": str(excinfo.value),
                "validation_reason_codes": [failure.diagnostic_code],
            }
        ]
    )
    assert entry["validation_failures"] == [{"unit_id": _UNIT, "reason_code": "missing_work_unit"}]
    assert entry["validation_reason_codes"] == [_SHAPE]
    # The repair asks for the whole object again, and the accumulator accepts it.
    proposal = parser.parse(_nomination())
    assert proposal.units[0].selected == ("operations-manager",)


def test_an_empty_object_reply_is_repaired_before_the_turn_dies() -> None:
    # Captured from turn 204: the repair reply was {} and the attempt reached
    # the durable receipt with no validation record and no truncation record.
    responses = iter((_result(_plan_document()), _result({}), _result(_nomination())))
    calls: list[tuple[str, str]] = []

    def invoke(_provider, prompt, _schema, *, system_prompt, timeout=None):
        calls.append((system_prompt, prompt))
        return next(responses)

    outcome = plan_and_staff_workforce(
        "Put this editor on my machine.",
        _snapshot(*_roster()),
        config=_config(),
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    assert [attempt.status for attempt in outcome.attempts] == ["applied", "rejected", "applied"]
    rejected = outcome.attempts[1]
    assert rejected.reason_code == "provider_response_contract_invalid"
    assert rejected.validation_reason_codes == (_SHAPE,)
    assert rejected.validation_detail == f"workforce nomination failures: {_UNIT}=missing_work_unit"
    feedback = json.loads(calls[2][1].split("[RUNTIME VALIDATION FEEDBACK]\n", 1)[1])
    (row,) = feedback["failed_units"]
    assert row["unit_id"] == _UNIT
    assert row["diagnostic_code"] == _SHAPE
    assert "was not a units object" in row["required_correction"]


@pytest.mark.parametrize(
    "reply",
    [
        pytest.param(
            {
                "units": [
                    {
                        "units": [
                            {
                                "unit_id": _UNIT,
                                "decision": "staff",
                                "ranked_semantic": [_required_row()],
                            }
                        ]
                    }
                ]
            },
            id="nested-units",
        ),
        pytest.param(
            _nomination(_required_row(), _CAPTURED_FORBIDDEN_ROW_WITHOUT_POSITIVE),
            id="forbidden-without-positive",
        ),
        pytest.param(_nomination(_CAPTURED_EVIDENCE_AS_OBJECT), id="evidence-as-object"),
        pytest.param(
            _nomination(_required_row(), _CAPTURED_UNDERSCORE_NEGATIVE), id="underscore-negative"
        ),
    ],
)
def test_the_captured_deployment_shapes_are_staffed_first_time(reply: dict[str, Any]) -> None:
    responses = iter((_result(_plan_document()), _result(reply)))

    outcome = plan_and_staff_workforce(
        "Put this editor on my machine.",
        _snapshot(*_roster()),
        config=_config(budget=2),
        context=_context(),
        invoker=lambda *_args, **_kwargs: next(responses),
    )

    assert outcome.accepted
    assert [attempt.status for attempt in outcome.attempts] == ["applied", "applied"]
    assert outcome.staffing.units[0].selected == ("operations-manager",)


# --- the verifier's rejection reaches the attempt -----------------------------


def test_a_verifier_rejection_projects_onto_the_attempt_row() -> None:
    error = _StaffingVerificationError(
        StaffingDecision(
            "abstained",
            (),
            (
                AbstentionReason("selection_confidence_too_low", _UNIT),
                AbstentionReason("selected_agent_budget_exceeded"),
            ),
        )
    )

    assert str(error) == (
        "workforce staffing verification failures: "
        f"{_UNIT}=selection_confidence_too_low,global=selected_agent_budget_exceeded"
    )
    rows = project_nomination_failures(str(error))
    assert rows == [
        {"unit_id": _UNIT, "reason_code": "selection_confidence_too_low"},
        {"unit_id": "global", "reason_code": "selected_agent_budget_exceeded"},
    ]
    (entry,) = project_preflight_provider_attempts(
        [
            {
                "stage": "recruiter",
                "provider_name": "agency-recruiter",
                "provider_type": "litellm",
                "status": "rejected",
                "reason_code": "provider_response_contract_invalid",
                "validation_detail": str(error),
            }
        ]
    )
    assert entry["validation_failures"] == rows
    assert "truncation" not in entry


def test_verifier_rows_survive_the_re_projection_every_reader_applies() -> None:
    # The preflight-failure receipt projects attempts when it is written and
    # again when it is read back, so a row that only the detail-string path
    # admitted vanished on read. Live turn 202 (2026-09-03) showed exactly that:
    # the write carried the verifier's rows and the receipt came back blank.
    detail = (
        "workforce staffing verification failures: "
        f"{_UNIT}=roster_coverage_gap,global=selected_agent_budget_exceeded"
    )
    rows = project_nomination_failures(detail)

    assert project_nomination_failures(rows) == rows
    attempt = {
        "stage": "recruiter",
        "provider_name": "agency-recruiter",
        "provider_type": "litellm",
        "status": "rejected",
        "reason_code": "provider_response_contract_invalid",
        "validation_detail": detail,
    }
    written = project_preflight_provider_attempts([attempt])
    assert written is not None and written[0]["validation_failures"] == rows
    assert project_preflight_provider_attempts(written) == written
    # A verifier code may not smuggle nomination fields past the nomination
    # vocabulary, and a nomination code still needs its exact form.
    assert (
        project_nomination_failures(
            [
                {
                    "unit_id": _UNIT,
                    "reason_code": "selection_confidence_too_low",
                    "requirement_axis": "domain",
                }
            ]
        )
        == []
    )
    assert (
        project_nomination_failures([{"unit_id": "global", "reason_code": "invalid_candidate"}])
        == []
    )


def test_the_verifier_vocabulary_on_the_receipt_is_the_verifier_vocabulary() -> None:
    """The closed set the receipts admit is derived from the verifier's own literals."""

    import inspect
    import re

    from agency_runtime.core.workforce import staffing_verifier

    source = inspect.getsource(staffing_verifier)
    literals = set(re.findall(r'_reason\(reasons, "([a-z_]+)"', source))
    assert literals
    assert literals | {staffing_verifier.ROSTER_COVERAGE_GAP} == set(
        staffing_verifier.STAFFING_VERIFIER_REASON_CODES
    )


def test_the_verification_projection_is_closed_and_bounded() -> None:
    prefix = "workforce staffing verification failures: "

    assert project_nomination_failures(prefix + "unit-x=Selection Confidence") == []
    assert project_nomination_failures(prefix + "unit-x=invented_code") == []
    assert project_nomination_failures(prefix + "not-a-unit=selection_confidence_too_low") == []
    assert project_nomination_failures(prefix + "unit-x=selection_confidence_too_low,broken") == []
    assert project_nomination_failures("workforce something else: unit-x=code") == []
    # Bounded to the receipt's unit limit rather than blanked.
    long_detail = prefix + ",".join(
        f"unit-{index}=selection_confidence_too_low" for index in range(20)
    )
    projected = project_nomination_failures(long_detail)
    assert len(projected) == 16
    assert projected[0] == {"unit_id": "unit-0", "reason_code": "selection_confidence_too_low"}
    # A duplicated row is kept once.
    assert project_nomination_failures(
        prefix + "unit-x=recruiter_abstained,unit-x=recruiter_abstained"
    ) == [{"unit_id": "unit-x", "reason_code": "recruiter_abstained"}]
