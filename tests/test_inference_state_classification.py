"""Inference state must reflect inference, not downstream staffing outcomes."""

from __future__ import annotations

from typing import Any

import pytest

from agency_runtime.core.dashboard_operational import _preflight_inference_applied


def _attempt(status: str) -> dict[str, Any]:
    return {"provider_name": "claude-haiku", "stage": "planner", "status": status}


def test_all_attempts_applied_is_not_an_inference_failure() -> None:
    """The recruiter abstaining says nothing about provider health."""

    record = {
        "reason_code": "substantive_specialist_unavailable",
        "staffing_reason_codes": ["no_safe_sufficient_team", "recruiter_abstained"],
        "provider_attempts": [_attempt("applied"), _attempt("applied")],
    }

    assert _preflight_inference_applied(record) is True


def test_one_failed_attempt_keeps_it_an_inference_failure() -> None:
    record = {"provider_attempts": [_attempt("applied"), _attempt("failed")]}

    assert _preflight_inference_applied(record) is False


@pytest.mark.parametrize("attempts", [None, [], "applied", {}, 7])
def test_a_failure_without_recorded_attempts_is_not_excused(attempts: object) -> None:
    """Silence is not evidence that inference worked."""

    assert _preflight_inference_applied({"provider_attempts": attempts}) is False


def test_non_mapping_attempts_are_not_counted_as_success() -> None:
    assert _preflight_inference_applied({"provider_attempts": ["applied", None]}) is False


@pytest.mark.parametrize("status", ["applied", "completed", "inferred", "ok", "success"])
def test_every_success_status_is_accepted(status: str) -> None:
    assert _preflight_inference_applied({"provider_attempts": [_attempt(status)]}) is True


@pytest.mark.parametrize("status", ["failed", "error", "timed_out", "cancelled", ""])
def test_failure_statuses_are_rejected(status: str) -> None:
    assert _preflight_inference_applied({"provider_attempts": [_attempt(status)]}) is False
