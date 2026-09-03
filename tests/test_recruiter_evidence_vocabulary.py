"""AR-373: the recruiter may cite the coverage vocabulary Agency teaches it.

`typed_staffing_requirements` shows the recruiter its coverage axes in the
form `artifact:plan`, `domain:platform`, `authority:plan`. The nomination
validator then required `[a-z0-9][a-z0-9-]{0,127}` -- hyphens only -- so a
recruiter citing those exact tokens back was rejected with
`recruiter_candidate_positive_evidence_invalid`, and the turn fell open.

Measured live 2026-09-02 on the request `install this: https://zcode.z.ai/en`:
the planner produced a good three-unit plan, the recruiter nominated
`devops-automator` as required at 0.85, and every candidate row was thrown
away over the colon. That shape is `provider_response_contract_invalid`,
counted 475 times in 24 hours on this installation.

The rows below are the real captured output.
"""

from __future__ import annotations

import pytest

from agency_runtime.core.workforce.inference import (
    _EVIDENCE_ARRAY,
    _IDENTIFIER_ARRAY,
    _nomination_candidate_diagnostic,
    _valid_nomination_evidence,
)
from agency_runtime.core.workforce.staffing_verifier import typed_staffing_requirements

# Captured verbatim from task-agency-recruiter-v2, 2026-09-02.
_CAPTURED_AXIS_ROW = {
    "agent_id": "devops-automator",
    "classification": "required",
    "score": 0.85,
    "positive_evidence": [
        "artifact:plan",
        "authority:plan",
        "capability:operations",
        "capability:planning",
        "domain:platform",
        "lifecycle:planning",
    ],
    "negative_evidence": [],
}
# The same recruiter's other accepted style, which always validated.
_CAPTURED_FREEFORM_ROW = {
    "agent_id": "devops-automator",
    "classification": "required",
    "score": 0.72,
    "positive_evidence": [
        "reproducible-install-automation",
        "deployment-safety-gates",
        "linux-platform-implementation",
    ],
    "negative_evidence": [],
}


def test_the_axis_form_agency_teaches_is_accepted() -> None:
    assert _valid_nomination_evidence(_CAPTURED_AXIS_ROW["positive_evidence"])
    assert _valid_nomination_evidence(_CAPTURED_FREEFORM_ROW["positive_evidence"])

    known = {"devops-automator"}
    for row in (_CAPTURED_AXIS_ROW, _CAPTURED_FREEFORM_ROW):
        assert _nomination_candidate_diagnostic(row, known=known, classifications={}) == ""


def test_the_vocabulary_agency_shows_is_the_vocabulary_it_accepts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Whatever `typed_staffing_requirements` emits must pass the validator.

    This is the invariant the defect broke: Agency handed the recruiter tokens
    it would then refuse. Deriving the expectation from the real builder keeps
    the two in step if either changes.
    """

    from agency_runtime.core.workforce.planning_contracts import parse_work_unit_plan

    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Install the software and verify the installation works.",
            "units": [
                {
                    "unit_id": "unit-install-operation",
                    "outcome": "Install the software on the linux host",
                    "artifact_kind": "plan",
                    "lifecycle_phase": "planning",
                    "domains": ["operations"],
                    "languages": [],
                    "frameworks": [],
                    "required_capabilities": ["planning"],
                    "authority": "plan",
                    "mutation_scope": "read_only",
                    "risks": ["regression"],
                    "trust_boundaries": ["repository"],
                    "claims": [],
                    "depends_on": [],
                    "resources": ["repository"],
                    "required_tools": [],
                    "platforms": ["linux"],
                    "acceptance_evidence": ["install verified"],
                    "parallelization": "unspecified",
                }
            ],
        }
    )
    requirements = list(typed_staffing_requirements(plan.units[0]))

    assert any(":" in item for item in requirements), "the axis form is what makes this matter"
    assert _valid_nomination_evidence(requirements[:16]), (
        f"Agency must accept the coverage vocabulary it shows the recruiter: {requirements}"
    )


def test_every_safety_bound_survives() -> None:
    """Widening the charset must not widen anything that carries a guarantee."""

    assert not _valid_nomination_evidence(["has devops experience"])  # whitespace
    assert not _valid_nomination_evidence(["Artifact:Plan"])  # uppercase
    # The underscore form is the ineligibility vocabulary Agency shows (ADR-0202).
    assert _valid_nomination_evidence(["agent_authority_mismatch"])
    assert not _valid_nomination_evidence(["artifact:plan\n"])  # control character
    assert not _valid_nomination_evidence([":leading-colon"])  # must start alphanumeric
    assert not _valid_nomination_evidence(["a" * 129])  # length bound
    assert not _valid_nomination_evidence(["dup", "dup"])  # uniqueness
    assert not _valid_nomination_evidence([f"code-{index}" for index in range(17)])  # count
    assert not _valid_nomination_evidence("artifact:plan")  # must be a list
    assert not _valid_nomination_evidence([1])  # must be strings


def test_typed_identifier_fields_are_not_widened() -> None:
    """Only evidence gained the colon and underscore; identifiers match contracts."""

    assert _EVIDENCE_ARRAY["items"]["pattern"] == r"^[a-z0-9][a-z0-9:_-]{0,127}$"
    assert _IDENTIFIER_ARRAY["items"]["pattern"] == r"^[a-z0-9][a-z0-9-]{0,127}$"
    for bound in ("maxItems", "uniqueItems"):
        assert _EVIDENCE_ARRAY[bound] == _IDENTIFIER_ARRAY[bound]
    assert _EVIDENCE_ARRAY["items"]["maxLength"] == _IDENTIFIER_ARRAY["items"]["maxLength"]
