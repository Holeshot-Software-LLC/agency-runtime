"""Ranking may permute a unit's candidates but may never move them between units."""

from itertools import permutations

import pytest

from agency_runtime.core.workforce.inference import _parse_recall_rerank

_OFFERED = {
    "unit-discovery": ("reviewer", "investigator"),
    "unit-fix": ("implementer", "tester"),
}


def _reply(first=("reviewer", "investigator"), second=("implementer", "tester")):
    return {
        "units": [
            {"unit_id": "unit-discovery", "ranked_candidate_ids": list(first)},
            {"unit_id": "unit-fix", "ranked_candidate_ids": list(second)},
        ]
    }


@pytest.mark.parametrize("first", list(permutations(_OFFERED["unit-discovery"])))
@pytest.mark.parametrize("second", list(permutations(_OFFERED["unit-fix"])))
def test_inference_retains_every_candidate_order(first, second):
    assert _parse_recall_rerank(_reply(first, second), _OFFERED) == {
        "unit-discovery": first,
        "unit-fix": second,
    }


@pytest.mark.parametrize(
    "first",
    [
        ("reviewer", "implementer"),  # Captured failure: candidate from another unit.
        ("reviewer", "investigator", "tester"),  # Captured surplus cross-unit candidate.
        ("reviewer",),
        ("reviewer", "reviewer"),
        ("reviewer", "invented-worker"),
    ],
)
def test_membership_validator_still_rejects_invalid_rankings(first):
    with pytest.raises(ValueError, match="every offered candidate exactly once"):
        _parse_recall_rerank(_reply(first), _OFFERED)


def test_duplicate_or_reordered_units_are_still_rejected():
    for units in (list(reversed(_reply()["units"])), [_reply()["units"][0]] * 2):
        with pytest.raises(ValueError, match="unit order"):
            _parse_recall_rerank({"units": units}, _OFFERED)
