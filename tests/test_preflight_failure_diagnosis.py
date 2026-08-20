"""A terminal preflight failure has to explain itself without a live re-run.

Measured 2026-08-14: a failed Claude canary reported
``provider_response_contract_invalid`` on two recruiter attempts and nothing
else. The two facts that would have identified the cause -- which units failed
to be staffed, and whether the roster was eligible at all -- were both computed,
both bounded, and both discarded before the receipt was written. Recovering them
cost three live inference calls and still did not settle the question.

These cases pin the recovery. Everything asserted here is an allowlisted code:
no model text, no rejected candidate slugs, nothing that grows with the roster.
"""

from __future__ import annotations

from typing import Any

import pytest

from agency_runtime.core.preflight_failure import (
    MAX_PREFLIGHT_FAILURE_REASON_CODES,
    PREFLIGHT_FAILURE_RECEIPT_SCHEMA,
    default_preflight_failure_receipt,
    preflight_eligibility_reason_codes,
    preflight_hiring_reason_codes,
    project_preflight_failure_receipt,
    project_preflight_provider_attempts,
)


def _attempt(**overrides: Any) -> dict[str, Any]:
    attempt = {
        "stage": "recruiter",
        "provider_name": "claude-subscription",
        "provider_type": "cli",
        "requested_model": "sonnet",
        "actual_model": "sonnet",
        "status": "rejected",
        "reason_code": "provider_response_contract_invalid",
    }
    attempt.update(overrides)
    return attempt


def test_a_rejected_recruiter_attempt_names_the_units_that_failed() -> None:
    """The exact failure that was unreadable in the canary receipt."""

    detail = (
        "workforce nomination failures: unit-1=staff_without_safe_team,"
        "unit-2=staff_without_safe_team,unit-3=staff_without_safe_team"
    )
    projected = project_preflight_provider_attempts([_attempt(validation_detail=detail)])

    assert projected is not None
    assert projected[0]["validation_failures"] == [
        {"unit_id": "unit-1", "reason_code": "staff_without_safe_team"},
        {"unit_id": "unit-2", "reason_code": "staff_without_safe_team"},
        {"unit_id": "unit-3", "reason_code": "staff_without_safe_team"},
    ]


def test_an_attempt_without_nomination_detail_carries_no_empty_key() -> None:
    """A successful attempt stays exactly as small as it was."""

    projected = project_preflight_provider_attempts(
        [_attempt(stage="planner", status="applied", reason_code="structured_response_applied")]
    )

    assert projected is not None
    assert "validation_failures" not in projected[0]
    assert projected[0]["stage"] == "planner"


@pytest.mark.parametrize(
    "detail",
    [
        "the model said something unexpected about the user's private prompt",
        "workforce nomination failures: unit-1=invented_code",
        "workforce nomination failures: not-a-unit=staff_without_safe_team",
        "workforce nomination failures: unit-1",
        "",
    ],
)
def test_only_the_allowlisted_failure_contract_survives(detail: str) -> None:
    """Free text never reaches the receipt, however it is shaped."""

    projected = project_preflight_provider_attempts([_attempt(validation_detail=detail)])

    assert projected is not None
    assert "validation_failures" not in projected[0]


def test_eligibility_reasons_distinguish_an_ineligible_roster() -> None:
    """251 of 282 rejected is a different failure from a bad nomination."""

    routing = {
        "eligibility_rejections": [
            {"slug": f"agent-{index}", "reason": "execution_host_unproven"} for index in range(251)
        ]
    }

    assert preflight_eligibility_reason_codes(routing) == ["execution_host_unproven"]


def test_eligibility_reasons_never_retain_the_rejected_slugs() -> None:
    """The codes answer the question; the slugs only grow with the roster."""

    routing = {
        "eligibility_rejections": [
            {"slug": "ai-generated-code-security-auditor", "reason": "execution_host_unproven"},
            {"slug": "code-reviewer", "reason": "host_tool_missing"},
        ]
    }
    codes = preflight_eligibility_reason_codes(routing)

    assert sorted(codes) == ["execution_host_unproven", "host_tool_missing"]
    assert not any("reviewer" in code or "auditor" in code for code in codes)


def test_eligibility_reasons_stay_bounded_under_a_hostile_routing_result() -> None:
    routing = {
        "eligibility_rejections": [{"reason": f"reason_{index}"} for index in range(500)],
    }
    codes = preflight_eligibility_reason_codes(routing)

    assert len(codes) <= MAX_PREFLIGHT_FAILURE_REASON_CODES
    assert len(set(codes)) == len(codes)


def test_deferred_hiring_status_survives_a_later_preflight_failure() -> None:
    """An empty success reason list must not erase that hiring ran."""

    routing = {
        "hiring_events": [
            {
                "unit_id": "unit-implement",
                "status": "hired",
                "reason_codes": [],
                "calls_used": 3,
                "worker": "private-worker-identity",
                "notification": "private model-authored notification",
            }
        ]
    }

    codes = preflight_hiring_reason_codes(routing)

    assert codes == ["hiring_status_hired", "hiring_inference_attempted"]
    assert "worker" not in " ".join(codes)
    assert "notification" not in " ".join(codes)


def test_pending_and_not_attempted_hiring_are_distinguishable() -> None:
    routing = {
        "hiring_events": [
            {
                "status": "pending_approval",
                "reason_codes": [],
                "calls_used": 3,
            },
            {
                "status": "not_attempted",
                "reason_codes": ["task_hiring_limit_reached"],
                "calls_used": 0,
            },
        ]
    }

    assert preflight_hiring_reason_codes(routing) == [
        "hiring_status_pending_approval",
        "hiring_inference_attempted",
        "hiring_status_not_attempted",
        "task_hiring_limit_reached",
    ]


def test_untrusted_hiring_status_and_call_count_do_not_cross_the_boundary() -> None:
    routing = {
        "hiring_events": [
            {
                "status": "hired private-worker-identity",
                "reason_codes": [],
                "calls_used": "3",
            }
        ]
    }

    assert preflight_hiring_reason_codes(routing) == []


@pytest.mark.parametrize(
    "routing",
    [
        {},
        {"eligibility_rejections": None},
        {"eligibility_rejections": "execution_host_unproven"},
        {"eligibility_rejections": [{"reason": "Not A Code!"}]},
        {"eligibility_rejections": [{"slug": "code-reviewer"}]},
    ],
)
def test_a_missing_or_malformed_rejection_list_yields_no_codes(routing: dict[str, Any]) -> None:
    assert preflight_eligibility_reason_codes(routing) == []


def test_the_durable_receipt_contract_carries_both_new_diagnostics() -> None:
    receipt = {
        **default_preflight_failure_receipt(),
        "stage": "routing",
        "reason_code": "workforce_inference_failed",
        "exception_category": "runtime_error",
        "provider_attempts": [
            _attempt(
                validation_detail=(
                    "workforce nomination failures: "
                    "unit-1=staff_without_safe_team~primary~complement!4:5:4"
                )
            )
        ],
        "eligibility_reason_codes": ["execution_host_unproven"],
    }
    projected = project_preflight_failure_receipt(receipt)

    assert projected is not None
    assert projected["schema_version"] == PREFLIGHT_FAILURE_RECEIPT_SCHEMA
    assert projected["eligibility_reason_codes"] == ["execution_host_unproven"]
    assert projected["provider_attempts"][0]["validation_failures"] == [
        {
            "unit_id": "unit-1",
            "reason_code": "staff_without_safe_team",
            "ranked_agent_ids": "primary~complement",
            "required_agent_count": 4,
            "ranked_executable_count": 5,
            "maximum_selected_per_unit": 4,
        }
    ]


@pytest.mark.parametrize(
    "detail",
    [
        "workforce nomination failures: unit-1=staff_without_safe_team!4:5",
        "workforce nomination failures: unit-1=staff_without_safe_team!4:x:4",
        "workforce nomination failures: unit-1=gap_with_safe_team!0:1:4",
    ],
)
def test_team_search_counts_fail_the_receipt_projection_closed(detail: str) -> None:
    projected = project_preflight_provider_attempts([_attempt(validation_detail=detail)])

    assert projected is not None
    assert "validation_failures" not in projected[0]


def test_a_receipt_missing_the_new_field_is_rejected_by_the_contract() -> None:
    """The contract is an exact key set, so a stale writer fails loudly."""

    receipt = default_preflight_failure_receipt()
    receipt.pop("eligibility_reason_codes")

    assert project_preflight_failure_receipt(receipt) is None
