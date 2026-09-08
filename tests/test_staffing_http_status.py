"""AR-413: transport HTTP status survives staffing, projections and SQLite."""

import json
from dataclasses import replace

import pytest

from agency_runtime.core.preflight_failure import project_preflight_provider_attempts
from agency_runtime.core.reply_budget import PROVIDER_HTTP_STATUS_ERROR
from agency_runtime.core.selector.receipt_projection import (
    _provider_attempts,
    project_model_receipt_attempts,
)
from agency_runtime.core.workforce import hiring
from tests import test_staffing_failure_receipts as receipts
from tests import test_workforce_inference as fixtures
from tests.test_transport_failure_causes import _litellm


@pytest.mark.parametrize("status", [401, 408, 429, 502])
def test_http_status_survives_full_failed_turn_and_sqlite(tmp_path, status):
    failure = replace(
        fixtures._result({}),
        failure_reason=PROVIDER_HTTP_STATUS_ERROR,
        call_attempted=True,
        http_status=status,
    )
    outcome, calls = receipts._run([failure])
    assert not outcome.accepted
    assert len(calls) == 1
    assert outcome.attempts[0].http_status == status
    routing = receipts._routing(outcome)
    attempt = routing["provider_attempts"][0]
    attempt.update(
        api_key="PRIVATE KEY",
        response="PRIVATE RESPONSE",
        headers={"Authorization": "PRIVATE KEY"},
        endpoint="PRIVATE URL",
    )
    for project in (
        _provider_attempts,
        project_model_receipt_attempts,
        project_preflight_provider_attempts,
    ):
        projected = project([attempt])
        assert projected[0]["http_status"] == status
        assert project(projected) == projected
        assert "PRIVATE" not in json.dumps(projected)
    receipt = receipts._persist_failure(tmp_path, routing)
    assert receipt["provider_attempts"][0]["http_status"] == status
    assert "PRIVATE" not in json.dumps(receipt)


@pytest.mark.parametrize(
    "status",
    [None, 0, -1, 99, 600, 10**100, True, False, "408", " 408 ", 408.0, [], {"status": 408}],
)
def test_invalid_and_unknown_http_status_never_become_evidence(status):
    attempt = {
        "stage": "planner",
        "provider_name": "planner",
        "provider_type": "litellm",
        "status": "failed",
        "reason_code": PROVIDER_HTTP_STATUS_ERROR,
        "http_status": status,
    }
    for project in (
        _provider_attempts,
        project_model_receipt_attempts,
        project_preflight_provider_attempts,
    ):
        result = project([attempt])
        assert "http_status" not in result[0]
        assert project(result) == result


@pytest.mark.parametrize("status", [401, 408, 429, 502])
def test_hiring_failure_keeps_transport_status(status):
    failure = replace(
        fixtures._result({}),
        failure_reason=PROVIDER_HTTP_STATUS_ERROR,
        call_attempted=True,
        http_status=status,
    )
    result, attempt, failures = hiring._invoke(
        [_litellm()],
        prompt="p",
        schema={"type": "object"},
        system="s",
        stage="hiring",
        invoker=lambda *args, **kwargs: failure,
        budget=hiring._CallBudget(1),
    )
    assert result is None and attempt is None
    assert failures[0].http_status == status
    assert failures[0].as_receipt()["http_status"] == status
    assert (
        project_preflight_provider_attempts([failures[0].as_receipt()])[0]["http_status"] == status
    )


@pytest.mark.parametrize("reason", ["provider_call_timed_out", "provider_call_failed"])
def test_non_http_failure_does_not_invent_status(tmp_path, reason):
    failure = replace(fixtures._result({}), failure_reason=reason, call_attempted=True)
    outcome, _ = receipts._run([failure])
    assert not outcome.accepted
    routing = receipts._routing(outcome)
    stored = receipts._persist_failure(tmp_path, routing)
    assert "http_status" not in stored["provider_attempts"][0]
    for project in (
        _provider_attempts,
        project_model_receipt_attempts,
        project_preflight_provider_attempts,
    ):
        assert "http_status" not in project(routing["provider_attempts"])[0]
    _, _, failures = hiring._invoke(
        [_litellm()],
        prompt="p",
        schema={"type": "object"},
        system="s",
        stage="hiring",
        invoker=lambda *args, **kwargs: failure,
        budget=hiring._CallBudget(1),
    )
    assert failures[0].http_status == 0
    assert "http_status" not in project_preflight_provider_attempts([failures[0].as_receipt()])[0]


def test_legacy_receipt_without_status_remains_a_fixed_point():
    legacy = {
        "stage": "planner",
        "provider_name": "planner",
        "provider_type": "litellm",
        "status": "failed",
        "reason_code": PROVIDER_HTTP_STATUS_ERROR,
    }
    for project in (
        _provider_attempts,
        project_model_receipt_attempts,
        project_preflight_provider_attempts,
    ):
        projected = project([legacy])
        assert "http_status" not in projected[0]
        assert project(projected) == projected
