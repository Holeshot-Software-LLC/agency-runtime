"""AR-409: optional subject work cannot spend mandatory staffing capacity."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import replace
from hashlib import sha256

import pytest

from agency_runtime.core.preflight_failure import (
    default_preflight_failure_receipt,
    preflight_routing_failure_reason,
    preflight_staffing_reason_codes,
    project_preflight_provider_attempts,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.structured_provider import PROVIDER_CREDENTIAL_ENV_UNSET
from agency_runtime.core.workforce import inference
from agency_runtime.core.workforce.cache import clear_workforce_caches
from agency_runtime.core.workforce.routing_projection import project_workforce_routing
from tests import test_workforce_inference as fixtures


@pytest.fixture(autouse=True)
def _isolated_stage_cache():
    clear_workforce_caches()
    yield
    clear_workforce_caches()


def _invalid_plan():
    value = fixtures._compact_plan_document()
    value["units"].append(dict(value["units"][0]))
    return value


def _invalid_recruiter():
    value = fixtures._nomination_document()
    value["units"][0]["ranked_semantic"][0]["positive_evidence"] = []
    return value


def _script(*, invalid=(), critic_approved=True, subject_refusal=False, valid_subject=False):
    calls = []
    counts = Counter()

    def invoke(provider, prompt, schema, *, system_prompt, **kwargs):
        document = json.loads(prompt.split("\n\n[RUNTIME VALIDATION FEEDBACK]")[0])
        if system_prompt == inference._SUBJECT_SYSTEM:
            stage = "subject"
        elif "planning_taxonomy" in document:
            stage = "planner"
        elif "critic_contract" in document:
            stage = "critic"
        else:
            stage = "recruiter"
        calls.append((stage, provider.name))
        counts[stage] += 1
        if stage == "subject":
            if subject_refusal and counts[stage] == 1:
                return replace(
                    fixtures._result({}),
                    failure_reason=PROVIDER_CREDENTIAL_ENV_UNSET,
                    call_attempted=False,
                )
            return fixtures._result(
                {
                    "domains": ["software-engineering"],
                    "languages": [],
                    "frameworks": [],
                    "capability_ids": ["analysis"],
                    "platforms": ["linux"],
                }
                if valid_subject
                else {}
            )
        if stage == "planner":
            value = (
                _invalid_plan()
                if stage in invalid and counts[stage] == 1
                else fixtures._compact_plan_document()
            )
        elif stage == "recruiter":
            value = (
                _invalid_recruiter()
                if stage in invalid and counts[stage] == 1
                else fixtures._nomination_document()
            )
        else:
            value = (
                {}
                if stage in invalid and counts[stage] == 1
                else {
                    "approved": critic_approved,
                    "reason_codes": [] if critic_approved else ["wrong-neighbor-risk"],
                }
            )
        return fixtures._result(value)

    return invoke, calls


def _run(invoke, *, budget=5, subject=False, mode="strict", config=None):
    return inference.plan_and_staff_workforce(
        "Analyze this implementation safely.",
        fixtures._snapshot(fixtures._contract("technical-analyst")),
        config=config or fixtures._config(mode, **{f"{mode}_call_budget": budget}),
        context=replace(fixtures._context(), host="claude", platform="linux"),
        subject_inference_required=subject,
        invoker=invoke,
    )


def test_subject_repair_no_longer_spends_the_fifth_call_needed_by_the_critic():
    # The stage-local response sequence in live Claude receipt 3615c4fb used
    # subject2 + planner1 + recruiter2 and then had no critic capacity.
    invoke, calls = _script(invalid=("recruiter",))
    outcome = _run(invoke, subject=True)

    assert outcome.accepted
    assert [stage for stage, _ in calls] == [
        "subject",
        "planner",
        "recruiter",
        "recruiter",
        "critic",
    ]
    assert outcome.calls_used == 5
    assert outcome.staffing.units[0].selected == ("technical-analyst",)
    assert outcome.attempts[0].status == "rejected"


@pytest.mark.parametrize("mode,budget", [("fast", 4), ("balanced", 4), ("strict", 5)])
def test_without_subject_both_stage_repairs_remain_funded(mode, budget):
    invoke, calls = _script(invalid=("planner", "recruiter"))
    outcome = _run(invoke, mode=mode, budget=budget)

    assert outcome.accepted
    assert outcome.calls_used == len(calls) == budget
    assert [stage for stage, _ in calls] == ["planner"] * 2 + ["recruiter"] * 2 + (
        ["critic"] if mode == "strict" else []
    )


@pytest.mark.parametrize("budget", range(1, 9))
def test_explicit_strict_cap_is_never_enlarged_or_spent_on_doomed_stages(budget):
    invoke, calls = _script()
    outcome = _run(invoke, budget=budget, subject=True)

    expected = [] if budget < 3 else ["planner", "recruiter", "critic"]
    if budget >= 4:
        expected.insert(0, "subject")
    assert [stage for stage, _ in calls] == expected
    assert outcome.calls_used == len(calls) <= budget
    assert outcome.accepted == (budget >= 3)
    if not outcome.accepted:
        assert "workforce_call_budget_exhausted" in outcome.abstention_codes
        assert "staffing_critic_rejected" not in outcome.abstention_codes


@pytest.mark.parametrize("budget,accepted", [(5, False), (6, True)])
def test_subject_and_both_repairs_require_six_calls_without_weakening_validation(budget, accepted):
    invoke, calls = _script(invalid=("planner", "recruiter"))
    outcome = _run(invoke, budget=budget, subject=True)

    assert outcome.accepted is accepted
    if accepted:
        assert outcome.calls_used == 6
        assert calls[-1][0] == "critic"
    else:
        assert [stage for stage, _ in calls] == ["subject", "planner", "planner", "recruiter"]
        assert outcome.calls_used == 4
        assert "workforce_call_budget_exhausted" in outcome.abstention_codes
        assert not outcome.staffing.accepted


@pytest.mark.parametrize("refusal", [False, True])
def test_subject_cap_is_one_actual_call_across_provider_fallbacks(refusal):
    invoke, calls = _script(subject_refusal=refusal)
    config = replace(
        fixtures._config("strict", strict_call_budget=8),
        providers=(fixtures._provider("primary"), fixtures._provider("fallback")),
    )
    outcome = _run(invoke, config=config, subject=True)

    assert outcome.accepted
    subjects = [(stage, provider) for stage, provider in calls if stage == "subject"]
    assert subjects == [("subject", "primary")] + ([("subject", "fallback")] if refusal else [])
    assert outcome.calls_used == 4
    assert len(calls) == 4 + int(refusal)


def test_cached_plan_and_recruiter_do_not_spend_reserved_calls_but_critic_is_fresh():
    invoke, calls = _script()
    first = _run(invoke, budget=3)
    second = _run(invoke, budget=3)

    assert first.accepted and second.accepted
    assert second.cache_hits == ("plan", "recruiter")
    assert second.calls_used == 1
    assert [stage for stage, _ in calls] == ["planner", "recruiter", "critic", "critic"]


def test_valid_critic_veto_is_not_repaired_even_with_unused_capacity():
    invoke, calls = _script(critic_approved=False)
    outcome = _run(invoke, budget=8, subject=True)

    assert not outcome.accepted
    assert [stage for stage, _ in calls] == ["subject", "planner", "recruiter", "critic"]
    assert outcome.calls_used == 4
    assert [reason.code for reason in outcome.staffing.abstention_reasons] == [
        "staffing_critic_rejected",
        "critic_wrong_neighbor_risk",
    ]


def test_planner_fallback_cannot_spend_recruiter_and_critic_reservation():
    calls = []

    def invoke(provider, *_args, **_kwargs):
        calls.append(provider.name)
        return fixtures._result(_invalid_plan())

    config = replace(
        fixtures._config("strict", strict_call_budget=5),
        providers=(fixtures._provider("primary"), fixtures._provider("fallback")),
    )
    outcome = _run(invoke, config=config)

    assert not outcome.accepted
    assert calls == ["primary", "primary", "fallback"]
    assert outcome.calls_used == 3
    assert "workforce_call_budget_exhausted" in outcome.abstention_codes
    assert all(attempt.stage == "planner" for attempt in outcome.attempts)


def test_valid_subject_is_still_inferred_once_and_reaches_later_stages():
    scripted, calls = _script(valid_subject=True)
    documents = []

    def invoke(provider, prompt, schema, **kwargs):
        documents.append(json.loads(prompt))
        return scripted(provider, prompt, schema, **kwargs)

    outcome = _run(invoke, subject=True)

    assert outcome.accepted
    assert [stage for stage, _ in calls] == ["subject", "planner", "recruiter", "critic"]
    assert outcome.attempts[0].status == "applied"
    planner = next(doc for doc in documents if "planning_taxonomy" in doc)
    recruiter = next(doc for doc in documents if "detail_cards" in doc)
    assert planner["inferred_work_subject"] == recruiter["inferred_work_subject"]
    assert planner["inferred_work_subject"]["platforms"] == ["linux"]


def test_critic_still_gets_one_semantic_repair_when_capacity_remains():
    invoke, calls = _script(invalid=("critic",))
    outcome = _run(invoke, subject=True)

    assert outcome.accepted
    assert [stage for stage, _ in calls] == ["subject", "planner", "recruiter", "critic", "critic"]
    assert outcome.calls_used == 5
    assert [attempt.status for attempt in outcome.attempts[-2:]] == ["rejected", "applied"]


def test_cached_stages_are_checked_before_their_own_admission_floor(monkeypatch):
    invoke, calls = _script()
    assert _run(invoke).accepted
    real_budget = inference._CallBudget
    # Model earlier actual work consuming four of this same call ledger.
    # Both exact cached stages remain usable, leaving one fresh critic call.
    monkeypatch.setattr(inference, "_CallBudget", lambda maximum: real_budget(maximum, used=4))
    outcome = _run(invoke)

    assert outcome.accepted
    assert outcome.cache_hits == ("plan", "recruiter")
    assert outcome.calls_used == 5
    assert [stage for stage, _ in calls[3:]] == ["critic"]


@pytest.mark.parametrize("reserve,max_calls", [(1, None), (0, 1)])
def test_stage_limits_count_only_calls_after_pre_request_refusal(reserve, max_calls):
    calls = []
    budget = inference._CallBudget(4, used=2)

    def invoke(provider, *_args, **_kwargs):
        calls.append(provider.name)
        if provider.name == "unavailable":
            return replace(
                fixtures._result({}),
                failure_reason=PROVIDER_CREDENTIAL_ENV_UNSET,
                call_attempted=False,
            )
        return fixtures._result({"ok": True})

    parsed, attempts, failure = inference._invoke_stage(
        stage="planner",
        providers=(fixtures._provider("unavailable"), fixtures._provider("fallback")),
        prompt="{}",
        schema={"type": "object"},
        system_prompt="test",
        budget=budget,
        invoker=invoke,
        parser=lambda value: value,
        reserve=reserve,
        max_calls=max_calls,
    )

    assert parsed == {"ok": True} and failure == ""
    assert calls == ["unavailable", "fallback"]
    assert budget.used == 3
    assert attempts[0].reason_code == PROVIDER_CREDENTIAL_ENV_UNSET


@pytest.mark.parametrize("reserve,max_calls", [(-1, None), (0, 0)])
def test_invalid_internal_reservation_is_rejected_without_provider_calls(reserve, max_calls):
    def invoke(*_args, **_kwargs):
        raise AssertionError("invalid reservation cannot call a provider")

    with pytest.raises(ValueError, match="reservation"):
        inference._invoke_stage(
            stage="planner",
            providers=(fixtures._provider(),),
            prompt="{}",
            schema={},
            system_prompt="test",
            budget=inference._CallBudget(5),
            invoker=invoke,
            parser=lambda value: value,
            reserve=reserve,
            max_calls=max_calls,
        )


@pytest.mark.parametrize("budget,invalid,used", [(2, (), 0), (5, ("planner", "recruiter"), 4)])
def test_reserved_budget_reason_survives_real_failure_receipt(tmp_path, budget, invalid, used):
    invoke, calls = _script(invalid=invalid)
    outcome = _run(invoke, budget=budget, subject=True)
    routing = project_workforce_routing(
        outcome,
        [],
        request="Analyze this implementation safely.",
        roster_count=1,
        contract_fingerprint="sha256:" + "a" * 64,
    )
    store = Store(tmp_path / "agency.db")
    started = store.begin_preflight_attempt(
        session_id="reservation-session",
        trace_id="reservation-trace",
        host="claude",
        request_fingerprint=sha256(b"bounded reservation regression").hexdigest(),
        request_kind="nontrivial",
    )
    failure = default_preflight_failure_receipt()
    failure.update(
        stage="routing",
        reason_code=preflight_routing_failure_reason(routing),
        exception_category="runtime_error",
        provider_attempts=project_preflight_provider_attempts(routing["provider_attempts"]),
        staffing_reason_codes=preflight_staffing_reason_codes(routing),
    )
    assert store.fail_preflight_attempt(
        session_id="reservation-session",
        trace_id="reservation-trace",
        attempt_token=started["attempt_token"],
        failure_receipt=failure,
    )
    receipt = store.get_preflight_failure_receipt("reservation-session", "reservation-trace")

    assert outcome.calls_used == len(calls) == used
    assert routing["selected_ids"] == []
    assert receipt["staffing_reason_codes"] == [outcome.status, "workforce_call_budget_exhausted"]
    assert "staffing_critic_rejected" not in json.dumps(receipt)
    assert store.get_run("reservation-trace")["status"] == "preflight_failed"


@pytest.mark.parametrize("already_present", [False, True])
def test_budget_reason_preserves_verifier_causes_without_duplication(already_present):
    code = "workforce_call_budget_exhausted"
    staffing = inference._empty_staffing(
        "no_safe_sufficient_team", (code,) if already_present else ()
    )
    outcome = inference._inference_failure(
        mode="strict",
        configured=True,
        plan=None,
        proposal=None,
        attempts=(),
        detail_codes=(code,),
        calls_used=4,
        staffing=staffing,
    )

    assert outcome.status == "inference_unavailable"
    assert not outcome.accepted
    assert [reason.code for reason in outcome.staffing.abstention_reasons] == [
        "no_safe_sufficient_team",
        code,
    ]
