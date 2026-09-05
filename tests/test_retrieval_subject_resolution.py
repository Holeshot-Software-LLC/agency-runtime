"""AR-370: retrieval gets a subject, and an unstaffed turn says which kind it was.

Measured 2026-09-02 and 2026-09-03: `configure the gateway` retrieved zero
candidates, "Install ripgrep on this machine" returned a top candidate scoring
0.0, and with no signal the roster answered alphabetically -- `3d-scene-developer`
was top-three for 20 of 30 prompts and top-1 for 7. The layer meant to close
that gap, `_DOMAIN_EXPANSIONS`, was a hand-curated table of about 25 nouns
nearly all specific to one operator's stack, with no entry for any common
operational verb.

Three things are pinned here.

The expansion table is gone, so no installation ships another operator's stack
vocabulary (that half lives in ``test_selector.py``).

A request whose subject is a bare deictic or a bare URL is resolved from the
turn itself before retrieval runs, and the routing receipt records what it was
resolved to, so a wrong resolution is visible rather than silent.

An unstaffed turn says which of the three ways it went unstaffed. Only the
third is a recruiter verdict, and reporting all three as one is why this read
as a recruiter defect for weeks.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agency_runtime.core.selector.pipeline import (
    NO_RELEVANT_CANDIDATE,
    REQUEST_UNDERSPECIFIED,
    _unstaffed_retrieval_codes,
    _with_unstaffed_retrieval_codes,
)
from agency_runtime.core.selector.reference_resolution import (
    MAX_RESOLVED_SUBJECT_CHARS,
    ResolvedReference,
    mentions_bare_reference,
    resolve_bare_reference,
    strip_bare_reference,
)

_HINTS = {"workforce_subject_hints": {"languages": ["python"], "frameworks": ["fastapi"]}}


# --- a bare reference is resolved from the turn itself ----------------------


def test_a_bare_url_resolves_to_its_own_distinctive_labels() -> None:
    # The canonical case from the issue. The verb is present; the object is not.
    reference = resolve_bare_reference(
        "install this: https://zcode.z.ai/en", subject_is_retrievable=False
    )

    assert reference.detected is True
    assert reference.kind == "url"
    assert reference.resolved_from == "url"
    assert reference.subject == "zcode"
    # The parts every URL has identify nothing and are dropped.
    for generic in ("https", "www", "com", "ai", "en"):
        assert generic not in reference.subject.split()


def test_a_bare_deictic_resolves_from_the_turns_own_context() -> None:
    reference = resolve_bare_reference(
        "fix that", subject_is_retrievable=False, turn_context=_HINTS
    )

    assert reference.kind == "deictic"
    assert reference.resolved_from == "turn_context"
    assert reference.subject == "python fastapi"


def test_a_deictic_with_no_context_is_detected_and_left_unresolved() -> None:
    # Honest: the turn named nothing and nothing was available to name it.
    reference = resolve_bare_reference("fix that", subject_is_retrievable=False)

    assert reference.detected is True
    assert reference.resolved is False
    assert reference.resolved_from == ""
    assert reference.subject == ""


def test_a_request_that_names_its_own_subject_is_left_alone() -> None:
    reference = resolve_bare_reference(
        "Review this authentication diff for bugs", subject_is_retrievable=True
    )

    assert reference == ResolvedReference()
    assert reference.detected is False


def test_whether_a_subject_survives_is_asked_of_the_message_without_its_reference() -> None:
    # Deciding this here would mean shipping a list of words that do not count
    # as a subject, which is the curated vocabulary this issue removes.
    assert strip_bare_reference("install this: https://zcode.z.ai/en").strip() == "install"
    assert strip_bare_reference("Review this authentication diff") == "Review authentication diff"


def test_the_cheap_precheck_admits_only_turns_a_resolution_could_apply_to() -> None:
    # The predicate the caller pairs with this is a full pass over the eligible
    # catalog, so ordinary turns must not reach it.
    assert mentions_bare_reference("install this: https://zcode.z.ai/en") is True
    assert mentions_bare_reference("fix that") is True
    assert mentions_bare_reference("Implement Python retry backoff") is False
    assert mentions_bare_reference("") is False


def test_the_resolved_subject_is_bounded_and_content_free() -> None:
    long_url = "https://example.test/" + "/".join(f"segment{index}" for index in range(40))
    reference = resolve_bare_reference(long_url, subject_is_retrievable=False)

    assert len(reference.subject) <= MAX_RESOLVED_SUBJECT_CHARS
    assert len(reference.subject.split()) <= 8
    receipt = reference.receipt()
    assert set(receipt) == {"detected", "kind", "resolved_from", "resolved_subject"}


def test_the_resolution_reaches_the_routing_receipt() -> None:
    from agency_runtime.core.config import AgencyConfig
    from agency_runtime.core.selector.pipeline import build_route_request

    request = build_route_request(
        "reference",
        "install this: https://zcode.z.ai/en",
        [],
        AgencyConfig(),
        trace_id="reference",
    )

    assert request.reference_resolution["detected"] is True
    assert request.reference_resolution["kind"] == "url"
    assert request.reference_resolution["resolved_subject"] == "zcode"
    # The resolution steered retrieval, so it must be readable afterwards.
    assert "zcode" in request.routing_query


# --- the three ways a turn goes unstaffed ------------------------------------


def _outcome(
    *,
    accepted: bool = False,
    plan_units: tuple[dict[str, object], ...] = (),
    proposal_candidates: int = 0,
    recall_candidates: int = 0,
    selected: tuple[str, ...] = (),
) -> SimpleNamespace:
    return SimpleNamespace(
        staffing=SimpleNamespace(
            accepted=accepted,
            units=(SimpleNamespace(selected=selected),),
            abstention_reasons=(),
        ),
        plan=SimpleNamespace(units=tuple(SimpleNamespace(**unit) for unit in plan_units)),
        proposal=SimpleNamespace(
            units=(SimpleNamespace(candidates=tuple(range(proposal_candidates))),)
        ),
        attempts=(SimpleNamespace(stage="recall_reranker", candidate_count=recall_candidates),),
        abstention_codes=(),
    )


def test_a_turn_with_no_retrievable_subject_is_reported_underspecified() -> None:
    outcome = _outcome(plan_units=({"domains": (), "required_capabilities": ()},))

    assert _unstaffed_retrieval_codes(outcome, message_has_signal=False) == (
        REQUEST_UNDERSPECIFIED,
    )


def test_a_real_subject_that_retrieved_nothing_is_not_underspecified() -> None:
    # The roster came up empty, not the request. These are different failures
    # and the operator could not tell them apart.
    outcome = _outcome(plan_units=({"domains": ("operations",)},))

    assert _unstaffed_retrieval_codes(outcome, message_has_signal=False) == (NO_RELEVANT_CANDIDATE,)


def test_a_message_that_named_something_is_never_underspecified() -> None:
    outcome = _outcome(plan_units=({"domains": ()},))

    assert _unstaffed_retrieval_codes(outcome, message_has_signal=True) == (NO_RELEVANT_CANDIDATE,)


def test_a_real_candidate_set_is_left_to_the_recruiters_own_verdict() -> None:
    # An unsafe or insufficient team out of real candidates already has a code,
    # and it is the only one of the three that is a recruiter judgement.
    outcome = _outcome(plan_units=({"domains": ("operations",)},), proposal_candidates=5)

    assert _unstaffed_retrieval_codes(outcome, message_has_signal=True) == ()


def test_a_staffed_turn_carries_no_retrieval_code() -> None:
    staffed = _outcome(accepted=True, proposal_candidates=5)
    assert _unstaffed_retrieval_codes(staffed, message_has_signal=True) == ()

    selected = _outcome(selected=("operations-manager",), proposal_candidates=5)
    assert _unstaffed_retrieval_codes(selected, message_has_signal=True) == ()


@pytest.mark.parametrize(
    ("message_has_signal", "plan_units", "expected"),
    [
        (False, ({"domains": ()},), REQUEST_UNDERSPECIFIED),
        (False, ({"domains": ("operations",)},), NO_RELEVANT_CANDIDATE),
    ],
)
def test_the_code_reaches_the_decision_the_receipt_reads(
    message_has_signal: bool,
    plan_units: tuple[dict[str, object], ...],
    expected: str,
) -> None:
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class _Reason:
        code: str
        unit_id: str = ""
        agent_id: str = ""
        detail: str = ""

    @dataclass(frozen=True)
    class _Staffing:
        accepted: bool
        units: tuple[object, ...]
        abstention_reasons: tuple[_Reason, ...]

    @dataclass(frozen=True)
    class _Outcome:
        staffing: _Staffing
        plan: object
        proposal: object
        attempts: tuple[object, ...]
        abstention_codes: tuple[str, ...]

    base = _outcome(plan_units=plan_units)
    outcome = _Outcome(
        staffing=_Staffing(False, (SimpleNamespace(selected=()),), ()),
        plan=base.plan,
        proposal=base.proposal,
        attempts=base.attempts,
        abstention_codes=(),
    )

    updated = _with_unstaffed_retrieval_codes(outcome, message_has_signal=message_has_signal)

    assert expected in {reason.code for reason in updated.staffing.abstention_reasons}
    assert expected in updated.abstention_codes


# --- the verb table cannot silently regress ---------------------------------


def test_the_corpus_carries_a_case_for_every_operational_verb() -> None:
    from agency_runtime.core.evals.data.routing_v1 import ROUTING_CASES

    verb_cases = {str(case["id"]) for case in ROUTING_CASES if str(case["id"]).startswith("verb-")}

    assert verb_cases == {
        "verb-install-distribution",
        "verb-install-tool",
        "verb-configure",
        "verb-restart",
        "verb-troubleshoot",
        "verb-upgrade",
        "verb-monitor",
        "verb-runbook",
    }


def test_every_operational_verb_retrieves_its_specialist() -> None:
    """The measured table, pinned. Seven of eight retrieved nothing at all.

    Each query is a work statement -- the action, the artifact and the host --
    because that is what the runtime retrieves on once the zero-signal trigger
    and the inferred subject have run. This eval is deterministic recall and
    cannot make an inference call, so a case in the user's raw words would
    measure the inference stage's absence rather than retrieval's behaviour.
    """

    from agency_runtime.core.agent_identity import agent_identity
    from agency_runtime.core.evals.data.routing_v1 import CATALOG, ROUTING_CASES
    from agency_runtime.core.selector.candidate_narrow import pre_narrow
    from agency_runtime.core.selector.intent_text import affirmative_intent
    from agency_runtime.core.selector.semantic_retrieval import retrieve_candidate_union

    for case in ROUTING_CASES:
        if not str(case["id"]).startswith("verb-"):
            continue
        retrieval = retrieve_candidate_union(
            affirmative_intent(str(case["query"])), CATALOG, lexical_retriever=pre_narrow
        )
        top = [slug for item in retrieval.candidates[:3] if (slug := agent_identity(item))]

        assert top, f"{case['id']} retrieved nothing"
        for required in case["required"]:
            assert required in top, f"{case['id']} missed {required}: {top}"
        for forbidden in case["forbidden"]:
            assert forbidden not in top, f"{case['id']} admitted {forbidden}"
