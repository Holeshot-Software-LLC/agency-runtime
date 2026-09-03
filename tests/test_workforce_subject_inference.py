"""ADR-0197: supply the typed work subject a request's wording withheld.

An operational message such as `configure the gateway` scores nothing against
every card, so the planner reads the raw words and its typed recall faithfully
inherits the emptiness. One classification call ahead of the planner supplies
the subject, gated on the same zero-signal predicate the CLI prints, so a
request that already retrieves pays nothing.
"""

from __future__ import annotations

from typing import Any

import pytest

from agency_runtime.core.selector.candidate_narrow import retrieval_has_signal
from agency_runtime.core.workforce import inference as workforce_inference

_CATALOG: list[dict[str, Any]] = [
    {
        "slug": "developer-tooling-engineer",
        "name": "Developer Tooling Engineer",
        "description": "Install and configure developer tooling and CLI packages on linux",
        "capabilities": ["developer tooling", "package installation"],
        "task_types": ["implementation-change"],
    },
    {
        "slug": "accessibility-auditor",
        "name": "Accessibility Auditor",
        "description": "Audit interfaces for contrast and screen-reader behaviour",
        "capabilities": ["accessibility audit"],
        "task_types": ["review-report"],
    },
]


def test_zero_signal_predicate_separates_readable_from_unreadable_wording() -> None:
    assert retrieval_has_signal("install and configure developer tooling on linux", _CATALOG)
    assert not retrieval_has_signal("zzzqqq unrelated tokens", _CATALOG)
    assert not retrieval_has_signal("anything at all", [])


def test_subject_answer_is_projected_through_the_same_guard_a_plan_uses() -> None:
    parsed = workforce_inference._parse_subject_hints(
        {
            "domains": ["software-engineering"],
            "languages": [],
            "frameworks": [],
            "capability_ids": ["implementation"],
            "platforms": ["linux"],
        }
    )
    assert parsed["domains"] == ["software-engineering"]
    assert parsed["platforms"] == ["linux"]
    assert set(parsed) == set(workforce_inference._SUBJECT_HINT_FIELDS)


def test_an_all_empty_or_malformed_subject_answer_is_refused() -> None:
    empty = dict.fromkeys(workforce_inference._SUBJECT_HINT_FIELDS, [])
    with pytest.raises(ValueError, match="empty"):
        workforce_inference._parse_subject_hints(empty)

    with pytest.raises(ValueError, match="malformed"):
        workforce_inference._parse_subject_hints({"domains": [{"not": "an identifier"}]})


def test_the_subject_schema_is_closed_over_the_roster_vocabulary() -> None:
    schema = workforce_inference._subject_response_schema(
        ["software-engineering"], ["python"], ["implementation"]
    )
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(workforce_inference._SUBJECT_HINT_FIELDS)
    assert schema["properties"]["domains"]["items"]["enum"] == ["software-engineering"]
    assert schema["properties"]["platforms"]["items"]["enum"] == ["windows", "linux"]
    for field in workforce_inference._SUBJECT_HINT_FIELDS:
        assert schema["properties"][field]["maxItems"] == (
            workforce_inference.MAX_SUBJECT_HINTS_PER_FIELD
        )


def _no_call(*_args: object, **_kwargs: object) -> tuple[dict[str, list[str]], list[Any]]:
    raise AssertionError("subject inference must not run for this turn")


def test_a_readable_request_never_buys_the_classification_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workforce_inference, "infer_work_subject_hints", _no_call)

    context, revision, attempts = workforce_inference._with_inferred_subject(
        {},
        "rev-0",
        request="anything",
        snapshot=object(),
        config=object(),
        context=object(),
        budget=object(),
        invoker=object(),
        required=False,
    )

    assert (context, revision, attempts) == ({}, "rev-0", [])


def test_a_prior_turn_subject_is_never_overwritten(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(workforce_inference, "infer_work_subject_hints", _no_call)
    prior = {"workforce_subject_hints": {"domains": ["software-engineering"]}}

    context, revision, attempts = workforce_inference._with_inferred_subject(
        prior,
        "rev-1",
        request="configure the gateway",
        snapshot=object(),
        config=object(),
        context=object(),
        budget=object(),
        invoker=object(),
        required=True,
    )

    assert (context, revision, attempts) == (prior, "rev-1", [])


def test_an_unreadable_request_gains_the_typed_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    hints = {
        "domains": ["software-engineering"],
        "languages": [],
        "frameworks": [],
        "capability_ids": ["implementation"],
        "platforms": ["linux"],
    }
    monkeypatch.setattr(
        workforce_inference,
        "infer_work_subject_hints",
        lambda *_args, **_kwargs: (hints, ["attempt"]),
    )

    context, revision, attempts = workforce_inference._with_inferred_subject(
        {},
        "rev-0",
        request="configure the gateway",
        snapshot=object(),
        config=object(),
        context=object(),
        budget=object(),
        invoker=object(),
        required=True,
    )

    assert context["workforce_subject_hints"] == hints
    assert revision != "rev-0"
    assert attempts == ["attempt"]


def test_an_honest_empty_answer_keeps_its_attempts_and_changes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        workforce_inference,
        "infer_work_subject_hints",
        lambda *_args, **_kwargs: ({}, ["attempt"]),
    )

    context, revision, attempts = workforce_inference._with_inferred_subject(
        {},
        "rev-0",
        request="configure the gateway",
        snapshot=object(),
        config=object(),
        context=object(),
        budget=object(),
        invoker=object(),
        required=True,
    )

    assert (context, revision) == ({}, "rev-0")
    assert attempts == ["attempt"]


def test_the_trigger_is_a_zero_floor_not_a_tunable_threshold() -> None:
    """ADR-0197: the gate must stay "scored nothing", never "scored lowish".

    A loosened trigger would spend a classification call on turns that already
    retrieve, which is the cost the option was chosen to avoid. This pins the
    boundary at exactly zero from both sides.
    """

    barely = [
        {
            "slug": "developer-tooling-engineer",
            "name": "Developer Tooling Engineer",
            "description": "Install developer tooling",
            "capabilities": ["developer tooling"],
            "task_types": ["implementation-change"],
        }
    ]
    from agency_runtime.core.selector.candidate_narrow import pre_narrow

    _, scores = pre_narrow("install developer tooling", barely, limit=1)
    assert scores and max(scores) > 0.0
    assert retrieval_has_signal("install developer tooling", barely)

    _, zero_scores = pre_narrow("zzzqqq", barely, limit=1)
    assert not zero_scores or max(zero_scores) == 0.0
    assert not retrieval_has_signal("zzzqqq", barely)
