"""AR-408: a missing critic verdict is not a veto; call deadlines survive storage."""

from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.preflight_failure import (
    default_preflight_failure_receipt,
    preflight_routing_failure_reason,
    preflight_staffing_reason_codes,
    project_preflight_provider_attempts,
)
from agency_runtime.core.provider_deadline import inference_deadline
from agency_runtime.core.reply_budget import PROVIDER_CALL_TIMED_OUT, PROVIDER_HTTP_STATUS_ERROR
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce import inference
from agency_runtime.core.workforce.cache import clear_workforce_caches
from agency_runtime.core.workforce.routing_projection import project_workforce_routing
from tests import test_workforce_inference as fixtures


@pytest.fixture(autouse=True)
def _isolated_stage_cache():
    clear_workforce_caches()
    yield
    clear_workforce_caches()


def _run(replies, *, config=None, subject=False):
    calls = []
    responses = iter(replies)

    def invoke(provider, prompt, schema, **kwargs):
        calls.append((provider.name, kwargs["timeout"]))
        return next(responses)

    outcome = inference.plan_and_staff_workforce(
        "Analyze this implementation safely.",
        fixtures._snapshot(fixtures._contract("technical-analyst")),
        config=config or fixtures._config("strict"),
        context=replace(fixtures._context(), host="claude", platform="linux"),
        subject_inference_required=subject,
        invoker=invoke,
    )
    return outcome, calls


def _routing(outcome):
    return project_workforce_routing(
        outcome,
        [],
        request="Analyze this implementation safely.",
        roster_count=1,
        contract_fingerprint="sha256:" + "a" * 64,
    )


def _persist_failure(tmp_path: Path, routing: dict[str, Any]):
    store = Store(tmp_path / "agency.db")
    started = store.begin_preflight_attempt(
        session_id="receipt-session",
        trace_id="receipt-trace",
        host="claude",
        request_fingerprint=sha256(b"bounded receipt regression").hexdigest(),
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
        session_id="receipt-session",
        trace_id="receipt-trace",
        attempt_token=started["attempt_token"],
        failure_receipt=failure,
    )
    receipt = store.get_preflight_failure_receipt("receipt-session", "receipt-trace")
    assert receipt is not None
    assert store.get_run("receipt-trace")["status"] == "preflight_failed"
    return receipt


def test_five_calls_exhausted_before_critic_are_not_a_critic_veto(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # AR-408's committed candidate d9dde3cd retains the original live Claude
    # 3615c4fb response sequence. AR-409 now prevents that current flow. Replay
    # the actual exhausted critic boundary independently of the new policy.
    real_critic = inference._strict_critic

    def exhausted_critic(**kwargs):
        kwargs["budget"].used = kwargs["budget"].maximum
        return real_critic(**kwargs)

    monkeypatch.setattr(inference, "_strict_critic", exhausted_critic)
    outcome, calls = _run(
        [
            fixtures._result(fixtures._compact_plan_document()),
            fixtures._result(fixtures._nomination_document()),
        ],
        config=fixtures._config("strict", strict_call_budget=5),
    )
    assert len(calls) == 2
    assert outcome.calls_used == 5
    assert [(item.stage, item.status) for item in outcome.attempts] == [
        ("planner", "applied"),
        ("recruiter", "applied"),
    ]
    assert not outcome.accepted
    assert "workforce_call_budget_exhausted" in outcome.abstention_codes
    routing = _routing(outcome)
    assert routing["selected_ids"] == []
    receipt = _persist_failure(tmp_path, routing)
    assert receipt["staffing_reason_codes"] == ["workforce_call_budget_exhausted"]
    assert "staffing_critic_rejected" not in json.dumps(receipt)


@pytest.mark.parametrize("failure", ["missing_provider", "deadline", "timeout", "http", "invalid"])
def test_critic_without_a_valid_verdict_never_claims_a_veto(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str
) -> None:
    responses = [
        fixtures._result(fixtures._compact_plan_document()),
        fixtures._result(fixtures._nomination_document()),
    ]
    expected = "workforce_inference_failed"
    expected_calls = 3
    if failure == "missing_provider":
        real_providers = inference.configured_workforce_providers

        def providers(*args, **kwargs):
            return () if kwargs.get("stage") == "critic" else real_providers(*args, **kwargs)

        monkeypatch.setattr(inference, "configured_workforce_providers", providers)
        expected = "workforce_provider_unavailable"
        expected_calls = 2
    elif failure == "deadline":
        real_critic = inference._strict_critic
        clock = [1000.0]
        monkeypatch.setattr(inference.time, "monotonic", lambda: clock[0])

        def expired_critic(**kwargs):
            clock[0] = 1005.0
            with inference_deadline(1005.0):
                return real_critic(**kwargs)

        monkeypatch.setattr(inference, "_strict_critic", expired_critic)
        expected = "workforce_inference_deadline_exhausted"
        expected_calls = 2
    elif failure == "invalid":
        responses.extend([fixtures._result({"private": "PRIVATE RESPONSE"})] * 2)
        expected_calls = 4
    else:
        responses.append(
            replace(
                fixtures._result({}),
                failure_reason=(
                    PROVIDER_CALL_TIMED_OUT if failure == "timeout" else PROVIDER_HTTP_STATUS_ERROR
                ),
                call_attempted=True,
                http_status=503 if failure == "http" else 0,
            )
        )
    outcome, calls = _run(responses)
    assert not outcome.accepted
    assert len(calls) == outcome.calls_used == expected_calls
    assert expected in outcome.abstention_codes
    receipt = _persist_failure(tmp_path, _routing(outcome))
    assert receipt["staffing_reason_codes"] == [expected]
    assert "staffing_critic_rejected" not in json.dumps(receipt)
    assert "PRIVATE RESPONSE" not in json.dumps(receipt)
    if failure == "deadline":
        assert receipt["provider_attempts"][-1]["reason_code"] == "provider_deadline_exhausted"
        assert "timeout_ms" not in receipt["provider_attempts"][-1]


def test_actual_critic_veto_keeps_its_existing_durable_reason(tmp_path: Path) -> None:
    outcome, calls = _run(
        [
            fixtures._result(fixtures._compact_plan_document()),
            fixtures._result(fixtures._nomination_document()),
            fixtures._result({"approved": False, "reason_codes": ["wrong-neighbor-risk"]}),
        ]
    )
    assert len(calls) == outcome.calls_used == 3
    assert not outcome.accepted
    receipt = _persist_failure(tmp_path, _routing(outcome))
    assert receipt["staffing_reason_codes"] == [
        "staffing_critic_rejected",
        "critic_wrong_neighbor_risk",
    ]


def test_actual_critic_approval_still_accepts_the_verified_team() -> None:
    outcome, calls = _run(
        [
            fixtures._result(fixtures._compact_plan_document()),
            fixtures._result(fixtures._nomination_document()),
            fixtures._result({"approved": True, "reason_codes": []}),
        ]
    )
    assert outcome.accepted
    assert len(calls) == outcome.calls_used == 3
    assert outcome.staffing.abstention_reasons == ()


def test_effective_timeout_survives_workforce_projection_and_durable_failure(
    tmp_path: Path,
) -> None:
    outcome, _calls = _run(
        [fixtures._result({}), fixtures._result({})],
        config=fixtures._config("strict", strict_call_budget=5),
    )
    timed = replace(
        outcome.attempts[0],
        status="failed",
        reason_code=PROVIDER_CALL_TIMED_OUT,
        latency_ms=120206,
        timeout_ms=120000,
        validation_detail="PRIVATE RESPONSE",
    )
    outcome = replace(outcome, attempts=(timed,))
    routing = _routing(outcome)
    assert routing["provider_attempts"][0]["timeout_ms"] == 120000
    routing["provider_attempts"][0].update(api_key="PRIVATE KEY", response="PRIVATE RESPONSE")
    receipt = _persist_failure(tmp_path, routing)
    assert receipt["provider_attempts"][0]["latency_ms"] == 120206
    assert receipt["provider_attempts"][0]["timeout_ms"] == 120000
    assert "PRIVATE KEY" not in json.dumps(receipt)
    assert "PRIVATE RESPONSE" not in json.dumps(receipt)
