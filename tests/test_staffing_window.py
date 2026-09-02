"""AR-353: the staffing-verdict window is measured from bounded store reads.

The window was described from memory ("hermes flaps ~50%"); these tests pin
the store read (turn counts and the newest failure receipts since a canonical
cutoff), the content-free projection (rates, dominant stage and codes), the
cutoff resolution, and the CLI surface that prints it.
"""

from __future__ import annotations

import argparse
import io
import json
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.cli import evidence_commands
from agency_runtime.core.staffing_window import (
    DEFAULT_STAFFING_WINDOW_HOURS,
    MAX_STAFFING_WINDOW_HOURS,
    NO_PROVIDER_ATTEMPT,
    VERDICT_AFTER_APPLIED_ATTEMPTS,
    failing_stage,
    last_stage,
    staffing_window_cutoff,
    staffing_window_projection,
    store_timestamp,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.store.turn_window import (
    MAX_TURN_WINDOW_RECEIPTS,
    bounded_turn_window_limit,
    turn_window_cutoff,
    turn_window_host,
)
from agency_runtime.core.turn_intent import classify_turn_intent

_NOW = datetime(2026, 9, 2, 4, 0, tzinfo=timezone.utc)


def _attempt(stage: str, status: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "stage": stage,
        "provider_name": "agency-planner-v2",
        "provider_type": "litellm",
        "requested_model": "task-agency-planner-v2",
        "model_group": "task-agency-planner-v2",
        "actual_model": "task-agency-planner-v2",
        "model_receipt_source": "response.body.model",
        "status": status,
        "reason_code": reason,
        **extra,
    }


def _receipt(
    *,
    reason_code: str = "workforce_inference_failed",
    staffing: list[str] | None = None,
    attempts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "agency.preflight.failure.v3",
        "stage": "routing",
        "reason_code": reason_code,
        "invariant_code": "",
        "exception_category": "runtime_error",
        "provider_attempts": attempts or [],
        "staffing_reason_codes": staffing or [],
        "hiring_reason_codes": [],
        "eligibility_reason_codes": [],
    }


def _fail_turn(
    store: Store,
    *,
    host: str,
    trace_id: str,
    receipt: dict[str, Any],
) -> None:
    lifecycle = store.begin_preflight_attempt(
        trace_id=trace_id,
        session_id=f"{host}-session",
        host=host,
        user_message="",
        reservation_token="",
        request_fingerprint="f" * 64,
        request_kind="nontrivial",
        lease_seconds=30,
        turn_classification=classify_turn_intent("Audit and harden the runtime.", None).as_dict(),
    )
    assert store.fail_preflight_attempt(
        session_id=f"{host}-session",
        trace_id=trace_id,
        attempt_token=str(lifecycle["attempt_token"]),
        status="preflight_failed",
        failure_receipt=receipt,
    )


def _ok_turn(store: Store, *, host: str, trace_id: str) -> None:
    store.create_run(
        trace_id=trace_id,
        session_id=f"{host}-session",
        host=host,
        metadata={"request_kind": "trivial"},
    )


def test_cutoff_resolution_is_bounded_and_canonical() -> None:
    assert staffing_window_cutoff(now=_NOW) == store_timestamp(
        _NOW - timedelta(hours=DEFAULT_STAFFING_WINDOW_HOURS)
    )
    assert staffing_window_cutoff(hours=6, now=_NOW) == "2026-09-01T22:00:00.000000+00:00"
    assert staffing_window_cutoff(since="2026-09-01T20:29:00Z", now=_NOW) == (
        "2026-09-01T20:29:00.000000+00:00"
    )
    assert staffing_window_cutoff(since="2026-09-01 20:29:00", now=_NOW).startswith(
        "2026-09-01T20:29:00"
    )
    with pytest.raises(ValueError, match="not both"):
        staffing_window_cutoff(since="2026-09-01T00:00:00Z", hours=1, now=_NOW)
    with pytest.raises(ValueError, match="future"):
        staffing_window_cutoff(since="2026-09-03T00:00:00Z", now=_NOW)
    with pytest.raises(ValueError, match="between"):
        staffing_window_cutoff(hours=MAX_STAFFING_WINDOW_HOURS + 1, now=_NOW)
    with pytest.raises(ValueError, match="ISO-8601"):
        staffing_window_cutoff(since="yesterday", now=_NOW)


def test_turn_window_inputs_are_validated() -> None:
    assert turn_window_host("") == ""
    assert turn_window_host(" Claude ") == "claude"
    with pytest.raises(ValueError, match="unsupported"):
        turn_window_host("clawd")
    with pytest.raises(ValueError, match="canonical"):
        turn_window_cutoff("2026-09-01T20:29:00Z")
    assert bounded_turn_window_limit(1, maximum=MAX_TURN_WINDOW_RECEIPTS, field="x") == 1
    for bad in (0, True, MAX_TURN_WINDOW_RECEIPTS + 1, "5"):
        with pytest.raises(ValueError, match="between"):
            bounded_turn_window_limit(bad, maximum=MAX_TURN_WINDOW_RECEIPTS, field="x")


def test_failing_and_last_stage_name_the_first_unapplied_attempt() -> None:
    applied = _attempt("planner", "applied", "structured_response_applied")
    rejected = _attempt("recruiter", "rejected", "provider_response_contract_invalid")
    assert failing_stage([applied, rejected]) == "recruiter"
    assert last_stage([applied, rejected]) == "recruiter"
    assert failing_stage([applied]) == VERDICT_AFTER_APPLIED_ATTEMPTS
    assert failing_stage([]) == NO_PROVIDER_ATTEMPT
    assert last_stage([]) == NO_PROVIDER_ATTEMPT


def test_store_window_counts_turns_and_reads_receipts_since_the_cutoff(tmp_path: Path) -> None:
    store = Store(tmp_path / "window.db")
    cutoff = store_timestamp(datetime.now(timezone.utc) - timedelta(hours=1))
    _ok_turn(store, host="claude", trace_id="claude-ok")
    _fail_turn(
        store,
        host="claude",
        trace_id="claude-fail",
        receipt=_receipt(
            staffing=["staffing_critic_rejected"],
            attempts=[
                _attempt("planner", "applied", "structured_response_applied"),
                _attempt(
                    "recruiter",
                    "rejected",
                    "provider_response_contract_invalid",
                    validation_failures=[
                        {"unit_id": "unit-audit-runtime", "reason_code": "staff_without_safe_team"}
                    ],
                ),
            ],
        ),
    )
    _fail_turn(
        store,
        host="hermes",
        trace_id="hermes-fail",
        receipt=_receipt(
            staffing=["inference_invalid"],
            attempts=[_attempt("planner", "failed", "provider_no_valid_response")],
        ),
    )

    window = store.get_staffing_window(cutoff=cutoff, limit=10)

    assert window["cutoff"] == cutoff
    assert window["receipts_truncated"] is False
    counts = {(row["host"], row["status"]): row["count"] for row in window["turns"]}
    assert counts[("claude", "preflight_failed")] == 1
    assert counts[("hermes", "preflight_failed")] == 1
    assert counts[("claude", "active")] == 1
    assert [row["host"] for row in window["receipts"]] == ["hermes", "claude"]
    assert window["receipts"][1]["staffing_reason_codes"] == ["staffing_critic_rejected"]

    scoped = store.get_staffing_window(cutoff=cutoff, host="hermes", limit=1)
    assert [row["host"] for row in scoped["receipts"]] == ["hermes"]
    assert all(row["host"] == "hermes" for row in scoped["turns"])

    truncated = store.get_staffing_window(cutoff=cutoff, limit=1)
    assert truncated["receipts_truncated"] is True

    projection = staffing_window_projection(window, now=store_timestamp(datetime.now(timezone.utc)))
    claude = projection["hosts"]["claude"]
    assert claude["turns_started"] == 2
    assert claude["turns_preflight_failed"] == 1
    assert claude["failure_rate"] == 0.5
    assert claude["dominant"]["failing_stage"] == "recruiter"
    assert claude["dominant"]["staffing_reason_code"] == "staffing_critic_rejected"
    assert claude["validation_reason_codes"][0] == {
        "value": "recruiter:staff_without_safe_team",
        "count": 1,
    }
    assert projection["hosts"]["hermes"]["dominant"]["failing_stage"] == "planner"
    assert projection["hosts"]["openclaw"] == projection["hosts"]["zcode"]
    assert projection["hosts"]["openclaw"]["turns_started"] == 0
    assert projection["totals"]["turns_started"] == 3
    assert projection["totals"]["turns_preflight_failed"] == 2
    assert projection["totals"]["dominant"]["provider_outcome"] in {
        "planner applied/structured_response_applied",
        "planner failed/provider_no_valid_response",
        "recruiter rejected/provider_response_contract_invalid",
    }
    assert projection["latency"]["recorded"] is False
    assert "no per-attempt timing" in projection["latency"]["note"]


def test_projection_reports_attempt_timing_only_when_it_is_recorded() -> None:
    window = {
        "cutoff": "2026-09-01T00:00:00.000000+00:00",
        "host": "",
        "limit": 10,
        "turns": [{"host": "codex", "status": "preflight_failed", "count": 1}],
        "receipts": [
            {
                "host": "codex",
                "reason_code": "workforce_inference_failed",
                "staffing_reason_codes": ["selection_confidence_too_low"],
                "provider_attempts": [
                    _attempt("planner", "applied", "structured_response_applied", duration_ms=1200),
                    _attempt("critic", "applied", "structured_response_applied", duration_ms=800),
                ],
            }
        ],
        "receipts_truncated": False,
    }

    projection = staffing_window_projection(window)

    assert projection["latency"]["recorded"] is True
    assert projection["latency"]["source"] == "provider_attempt_timing"
    codex = projection["hosts"]["codex"]
    assert codex["failure_rate"] == 1.0
    assert codex["dominant"]["failing_stage"] == VERDICT_AFTER_APPLIED_ATTEMPTS
    assert codex["dominant"]["last_stage"] == "critic"


def test_cli_prints_the_window_and_json(tmp_path: Path) -> None:
    store = Store(tmp_path / "cli.db")
    _fail_turn(
        store,
        host="openclaw",
        trace_id="oc-fail",
        receipt=_receipt(
            staffing=["inference_invalid"],
            attempts=[_attempt("planner", "rejected", "provider_response_contract_invalid")],
        ),
    )
    args = argparse.Namespace(
        host=None, since=None, hours=2, limit=None, db=str(tmp_path / "cli.db"), json=False
    )
    text = io.StringIO()
    with redirect_stdout(text):
        assert evidence_commands.cmd_evidence_staffing(args) == 0
    human = text.getvalue()
    assert "openclaw  1 turns, 1 preflight_failed (100.0%)" in human
    assert "failing stage planner" in human
    assert "zcode     no turns" in human

    args.json = True
    payload = io.StringIO()
    with redirect_stdout(payload):
        assert evidence_commands.cmd_evidence_staffing(args) == 0
    parsed = json.loads(payload.getvalue())
    assert parsed["window"]["kind"] == "turns_started_and_failure_receipts_since_cutoff"
    assert parsed["hosts"]["openclaw"]["turns_preflight_failed"] == 1
    assert parsed["latency"]["recorded"] is False
