"""AR-394: a rejected team says why it could not be formed.

`staff_without_safe_team` is the dominant terminal recruiter failure -- 317 of
the 484 unit rows in the last 400 live receipts on 2026-09-04. Its three
recorded counts say how far short the team fell and never why, and the two
causes with opposite fixes are exactly the ones the counts cannot separate: a
specialist retrieval never surfaced, and a specialist it surfaced that
deterministic eligibility then refused.

These tests pin the closed shortfall vocabulary, the branch each cause takes,
and the receipt row it produces.
"""

from __future__ import annotations

import pytest

from agency_runtime.core.selector.receipt_projection import (
    _SAFE_TEAM_SHORTFALL_CODES,
    project_nomination_failures,
)
from agency_runtime.core.workforce.inference import (
    SAFE_TEAM_SHORTFALL_CODES,
    _NominationFailure,
    _NominationValidationError,
    _safe_team_shortfall,
    _SafeTeamRepairContract,
)
from agency_runtime.core.workforce.planning_contracts import WorkUnit
from tests.test_workforce_inference import _context, _contract

# A unit whose platform matches the fixture context, so the roster's contracts
# are eligible for it and the two coverage causes can be told apart.
_UNIT = WorkUnit(
    unit_id="unit-implement-rate-limiting",
    outcome="Rate limiting on the public API gateway",
    artifact_kind="implementation",
    lifecycle_phase="implementation",
    domains=("software-engineering",),
    languages=(),
    frameworks=(),
    required_capabilities=("analysis",),
    authority="advise",
    mutation_scope="none",
    risks=(),
    trust_boundaries=(),
    claims=(),
    depends_on=(),
    resources=(),
    required_tools=("repository-read",),
    platforms=("windows",),
    acceptance_evidence=(),
    parallelization="parallel",
)
# The fixture roster covers this one and covers no artifact requirement at all.
_COVERED = "capability:analysis"
_UNCOVERABLE = "artifact:implementation"


class _Row:
    """The only thing the classifier reads off a proposal row."""

    def __init__(self, ranked_executable: tuple[str, ...]) -> None:
        self.ranked_executable = tuple(
            type("_Rank", (), {"agent_id": agent_id})() for agent_id in ranked_executable
        )


def _repair(
    *,
    required: tuple[str, ...] = (),
    maximum: int = 4,
    uncovered: tuple[str, ...] = (),
    uncovered_after_required: tuple[str, ...] = (),
    coverers: tuple[tuple[str, tuple[str, ...]], ...] = (),
) -> _SafeTeamRepairContract:
    return _SafeTeamRepairContract(
        maximum_selected_per_unit=maximum,
        requirements=uncovered,
        required_agent_ids=required,
        team_search_agent_ids=(),
        uncovered_requirement_ids=uncovered,
        uncovered_after_required_ids=uncovered_after_required,
        candidate_rows=(),
        eligible_coverers_by_requirement=coverers,
    )


def test_the_two_copies_of_the_vocabulary_agree() -> None:
    """The receipt projection holds its own copy; it must not drift."""

    assert SAFE_TEAM_SHORTFALL_CODES == _SAFE_TEAM_SHORTFALL_CODES


def test_more_required_than_slots_names_the_budget() -> None:
    shortfall = _safe_team_shortfall(
        None,
        _Row(("a", "b")),
        (),
        _repair(required=("a", "b", "c", "d", "e"), maximum=4, uncovered=("domain:x",)),
        _context(),
        ranking=("a", "b"),
    )
    assert shortfall == "required_over_budget"


def test_required_filling_every_slot_names_the_starved_complement() -> None:
    """The coverage cause would point the reader at the wrong fix here."""

    shortfall = _safe_team_shortfall(
        None,
        _Row(("a", "b", "c", "d")),
        (),
        _repair(
            required=("a", "b", "c", "d"),
            maximum=4,
            uncovered=("domain:x",),
            uncovered_after_required=("domain:x",),
            # A shown card covers it, and no slot is left to put it in.
            coverers=(("domain:x", ("technical-analyst",)),),
        ),
        _context(),
        ranking=("a", "b", "c", "d"),
    )
    assert shortfall == "complement_slots_exhausted"


def test_an_empty_ranking_names_itself() -> None:
    shortfall = _safe_team_shortfall(
        None, _Row(()), (), _repair(uncovered=("domain:x",)), _context(), ranking=()
    )
    assert shortfall == "no_ranked_candidate"


def test_candidates_ranked_and_all_refused_is_an_eligibility_failure() -> None:
    """AR-394 c1: present and ineligible."""

    shortfall = _safe_team_shortfall(
        None,
        _Row(()),
        (),
        _repair(uncovered=("domain:x",)),
        _context(),
        ranking=("wrong-neighbor", "also-wrong"),
    )
    assert shortfall == "ranked_candidates_ineligible"


def test_a_shown_coverer_that_was_not_selected_names_the_reply() -> None:
    shortfall = _safe_team_shortfall(
        None,
        _Row(("a",)),
        (),
        _repair(
            required=("a",),
            uncovered=("domain:x",),
            coverers=(("domain:x", ("technical-analyst",)),),
        ),
        _context(),
        ranking=("a",),
    )
    assert shortfall == "retrieved_coverer_not_selected"


def test_full_coverage_and_still_no_team_is_the_residual() -> None:
    shortfall = _safe_team_shortfall(
        None, _Row(("a",)), (), _repair(required=("a",)), _context(), ranking=("a",)
    )
    assert shortfall == "no_safe_combination"


def test_without_a_context_no_coverage_cause_is_claimed() -> None:
    """Eligibility is unknown, so the two causes cannot be told apart."""

    shortfall = _safe_team_shortfall(
        None,
        _Row(("a",)),
        (),
        _repair(required=("a",), uncovered=("domain:x",)),
        None,
        ranking=("a",),
    )
    assert shortfall == ""


def test_a_coverer_the_roster_holds_but_never_showed_names_retrieval() -> None:
    """AR-394 c1: absent from retrieval.

    Nothing in the card set the recruiter saw covers the requirement, and the
    roster holds a contract that covers it and is eligible for this unit. The
    specialist existed and was never offered.
    """

    shortfall = _safe_team_shortfall(
        _UNIT,
        _Row(("wrong-neighbor",)),
        (_contract("technical-analyst"), _contract("wrong-neighbor")),
        _repair(required=("wrong-neighbor",), uncovered=(_COVERED,), coverers=()),
        _context(),
        ranking=("wrong-neighbor",),
    )
    assert shortfall == "coverer_absent_from_retrieval"


def test_a_requirement_nothing_in_the_roster_covers_names_the_roster() -> None:
    """The ADR-0198 waiver should have fired; it did not, and the row says so."""

    shortfall = _safe_team_shortfall(
        _UNIT,
        _Row(("wrong-neighbor",)),
        (_contract("technical-analyst"), _contract("wrong-neighbor")),
        _repair(required=("wrong-neighbor",), uncovered=(_UNCOVERABLE,), coverers=()),
        _context(),
        ranking=("wrong-neighbor",),
    )
    assert shortfall == "no_eligible_coverer_in_roster"


def test_the_classification_is_total_over_the_closed_vocabulary() -> None:
    """Every member is reached by a test above, and nothing else is a member.

    The set is written out rather than derived so that adding a code without a
    test that reaches it fails here.
    """

    reached_by_a_test_above = {
        "required_over_budget",
        "complement_slots_exhausted",
        "no_ranked_candidate",
        "ranked_candidates_ineligible",
        "retrieved_coverer_not_selected",
        "coverer_absent_from_retrieval",
        "no_eligible_coverer_in_roster",
        "no_safe_combination",
    }
    assert reached_by_a_test_above == SAFE_TEAM_SHORTFALL_CODES


@pytest.mark.parametrize("shortfall", sorted(SAFE_TEAM_SHORTFALL_CODES))
def test_every_shortfall_reaches_the_receipt_on_its_own_failure(shortfall: str) -> None:
    """AR-394 c1: the receipt names the cause, not only the counts."""

    detail = str(
        _NominationValidationError(
            [
                _NominationFailure(
                    "unit-implement-rate-limiting",
                    "staff_without_safe_team",
                    "domain",
                    ("roblox-systems-scripter",),
                    "",
                    1,
                    2,
                    4,
                    None,
                    shortfall=shortfall,
                )
            ]
        )
    )
    rows = project_nomination_failures(detail)
    assert [row.get("safe_team_shortfall") for row in rows] == [shortfall]
    assert rows[0]["ranked_executable_count"] == 2


def test_a_shortfall_never_rides_on_a_malformed_reply() -> None:
    """AR-394 c2: the two failures are separated, and stay separated."""

    with pytest.raises(ValueError, match="not allowlisted"):
        _NominationValidationError(
            [
                _NominationFailure(
                    "unit-implement-rate-limiting",
                    "invalid_candidate",
                    shortfall="coverer_absent_from_retrieval",
                )
            ]
        )


def test_a_receipt_separates_a_short_team_from_a_malformed_reply() -> None:
    """AR-394 c2: one attempt, two units, two distinguishable causes."""

    detail = str(
        _NominationValidationError(
            [
                _NominationFailure(
                    "unit-implement-rate-limiting",
                    "staff_without_safe_team",
                    "domain",
                    ("roblox-systems-scripter",),
                    "",
                    0,
                    1,
                    4,
                    None,
                    shortfall="coverer_absent_from_retrieval",
                ),
                _NominationFailure(
                    "unit-write-tests",
                    "invalid_candidate",
                    diagnostic_code="recruiter_candidate_row_shape_invalid",
                ),
            ]
        )
    )
    rows = project_nomination_failures(detail)
    assert [row["reason_code"] for row in rows] == [
        "staff_without_safe_team",
        "invalid_candidate",
    ]
    # The short team says why it was short; the malformed row says nothing
    # about coverage, because nothing about coverage was ever established.
    assert rows[0]["safe_team_shortfall"] == "coverer_absent_from_retrieval"
    assert "safe_team_shortfall" not in rows[1]
    assert "ranked_executable_count" not in rows[1]


def test_a_row_claiming_a_shortfall_for_another_code_is_refused_whole() -> None:
    assert (
        project_nomination_failures(
            [
                {
                    "unit_id": "unit-write-tests",
                    "reason_code": "invalid_candidate",
                    "safe_team_shortfall": "coverer_absent_from_retrieval",
                }
            ]
        )
        == []
    )


def test_a_shortfall_outside_the_vocabulary_is_refused_whole() -> None:
    assert (
        project_nomination_failures(
            [
                {
                    "unit_id": "unit-write-tests",
                    "reason_code": "staff_without_safe_team",
                    "safe_team_shortfall": "because the model felt like it",
                }
            ]
        )
        == []
    )


def test_a_detail_written_before_ar_394_still_projects() -> None:
    """No `+` segment: the row parses exactly as it did, without a shortfall."""

    rows = project_nomination_failures(
        "workforce nomination failures: unit-analyze=staff_without_safe_team:artifact"
        "~wrong-neighbor~technical-analyst!1:1:4|agent_domain_mismatch"
    )
    assert rows == [
        {
            "unit_id": "unit-analyze",
            "reason_code": "staff_without_safe_team",
            "requirement_axis": "artifact",
            "ranked_agent_ids": "wrong-neighbor~technical-analyst",
            "top_ranked_ineligibility": "agent_domain_mismatch",
            "required_agent_count": 1,
            "ranked_executable_count": 1,
            "maximum_selected_per_unit": 4,
        }
    ]
    assert "safe_team_shortfall" not in rows[0]
