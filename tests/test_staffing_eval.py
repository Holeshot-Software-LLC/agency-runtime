"""AR-253 staffing eval: the accounting rules are the point.

The eval's value is not that it can call a judge -- it is that it refuses to
turn a broken provider into a selection failure, refuses to let a second
successful recruiter call pass unnoticed, and holds the cold budget fixed. Each
of those is asserted here against a stub, because a gate nobody has watched
fail is not a gate.
"""

from __future__ import annotations

from typing import Any

from agency_runtime.core.evals.staffing import (
    COLD_BUDGET_MS,
    MAXIMUM_SUCCESSFUL_RECRUITER_CALLS,
    MINIMUM_STAFFING_RATE,
    run_staffing_eval,
    selection_requiring_asks,
)

_CATALOG = [{"id": "code-reviewer"}, {"id": "technical-writer"}]


def _attempt(status: str = "applied", name: str = "selector") -> dict[str, Any]:
    return {
        "provider_name": name,
        "provider_type": "openai",
        "requested_model": "model",
        "model_group": "",
        "actual_model": "model",
        "model_receipt_source": "response.body.model",
        "status": status,
        "reason_code": "",
    }


def _staffed(attempts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "selected_ids": ["code-reviewer"],
        "status": "applied",
        "inference_mode": "inferred",
        "inference_configured": True,
        "inference_attempted": True,
        "latency_ms": 11,
        "candidate_count": len(_CATALOG),
        "top_score": 0.0,
        "provider_attempts": attempts if attempts is not None else [_attempt()],
    }


def _run(judge: Any, *, asks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return run_staffing_eval(
        asks=asks if asks is not None else [{"id": "one", "query": "q", "required": ["r"]}],
        catalog=_CATALOG,
        config=object(),
        judge=judge,
    )


def test_the_fixed_ask_set_is_real_and_selection_requiring() -> None:
    asks = selection_requiring_asks()
    assert len(asks) >= 20
    assert all(ask["required"] for ask in asks)
    assert all(ask["query"] for ask in asks)
    assert len({ask["id"] for ask in asks}) == len(asks)


def test_a_staffed_run_passes_every_gate() -> None:
    report = _run(lambda *_a, **_k: _staffed())

    assert report["passed"] is True
    assert report["metrics"]["staffed"] == 1
    assert report["metrics"]["staffing_rate"] == 1.0
    assert {gate["name"] for gate in report["gates"]} == {
        "staffing_rate",
        "successful_recruiter_calls_per_turn",
        "cold_budget_ms",
    }


def test_a_provider_that_never_decided_is_reported_and_never_scored() -> None:
    """The rule that keeps a broken provider from looking like bad selection."""

    asks = [
        {"id": "good", "query": "q1", "required": ["r"]},
        {"id": "broken", "query": "q2", "required": ["r"]},
    ]

    def judge(query: str, _catalog: Any, **_kwargs: Any) -> dict[str, Any]:
        if query == "q2":
            raise TimeoutError("provider timed out")
        return _staffed()

    report = _run(judge, asks=asks)

    assert report["metrics"]["asks"] == 2
    assert report["metrics"]["invalid_arms"] == 1
    assert report["metrics"]["valid_arms"] == 1
    # One valid arm, one staffed: the timeout is absent from the denominator.
    assert report["metrics"]["staffing_rate"] == 1.0
    assert report["invalid_arm_ids"] == ["broken"]
    assert report["passed"] is True


def test_a_malformed_provider_arm_is_invalid_rather_than_a_loss() -> None:
    malformed = _staffed(attempts=[{"provider_name": "selector", "status": "who knows"}])

    report = _run(lambda *_a, **_k: malformed)

    assert report["metrics"]["invalid_arms"] == 1
    assert report["metrics"]["valid_arms"] == 0
    assert report["passed"] is False  # nothing valid ran, so nothing is proven


def test_an_unstaffed_but_valid_arm_is_a_real_loss() -> None:
    declined = dict(_staffed(), selected_ids=[], status="abstained")

    report = _run(lambda *_a, **_k: declined)

    assert report["metrics"]["valid_arms"] == 1
    assert report["metrics"]["invalid_arms"] == 0
    assert report["metrics"]["staffed"] == 0
    assert report["metrics"]["staffing_rate"] == 0.0
    assert report["passed"] is False


def test_a_second_successful_recruiter_call_fails_the_gate() -> None:
    """Bounded repair attempts are fine; two applied decisions are not."""

    twice = _staffed(attempts=[_attempt(), _attempt(name="fallback")])

    report = _run(lambda *_a, **_k: twice)

    gate = next(
        item for item in report["gates"] if item["name"] == "successful_recruiter_calls_per_turn"
    )
    assert gate["observed"] == 2
    assert gate["threshold"] == MAXIMUM_SUCCESSFUL_RECRUITER_CALLS
    assert gate["passed"] is False
    assert report["passed"] is False


def test_failed_attempts_before_one_success_are_not_counted_against_the_turn() -> None:
    repaired = _staffed(attempts=[_attempt("failed"), _attempt("skipped"), _attempt()])

    report = _run(lambda *_a, **_k: repaired)

    gate = next(
        item for item in report["gates"] if item["name"] == "successful_recruiter_calls_per_turn"
    )
    assert gate["observed"] == 1
    assert report["passed"] is True


def test_the_cold_budget_gate_is_fixed_at_fifteen_seconds() -> None:
    assert COLD_BUDGET_MS == 15_000
    assert MINIMUM_STAFFING_RATE == 0.95

    def slow(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        import time

        time.sleep(0.01)
        return _staffed()

    report = _run(slow)
    gate = next(item for item in report["gates"] if item["name"] == "cold_budget_ms")
    assert gate["threshold"] == COLD_BUDGET_MS
    assert gate["observed"] >= 0
    assert gate["passed"] is True


def test_the_manifest_reports_host_correlation_as_unavailable_without_a_host() -> None:
    """Only a host artifact proves delivery; the decision alone must not claim it."""

    report = _run(lambda *_a, **_k: _staffed())

    assert report["metrics"]["host_artifact_correlation"] == "unavailable"
    assert report["asks_detail"][0]["host_artifact_correlation"] == "unavailable"
    detail = report["asks_detail"][0]
    assert detail["selected_cards"] == ["code-reviewer"]
    assert detail["candidate_count"] == len(_CATALOG)
    assert len(detail["candidate_digest"]) == 64
    assert detail["decision_valid"] is True
