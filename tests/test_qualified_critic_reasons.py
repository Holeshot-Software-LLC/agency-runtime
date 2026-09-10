"""AR-416: a qualified native veto must not silently lose its standard cause."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from agency_runtime.core.fail_open_disclosure import (
    MAX_FAIL_OPEN_DISCLOSURE_CHARS,
    render_fail_open_disclosure,
)
from agency_runtime.core.header.finalize import finalize_response
from agency_runtime.core.preflight_failure import (
    default_preflight_failure_receipt,
    preflight_staffing_reason_codes,
)
from agency_runtime.core.selector.receipt_projection import project_durable_routing_receipt
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce.inference import _critic_receipt_codes
from tests.test_strict_critic_doctrine import _POINTER, _routing, _run_neighbourhood

_OMITTED = "critic_reason_detail_omitted"


def test_captured_qualified_veto_survives_receipts_and_terminal_header(tmp_path: Path) -> None:
    # The observed native code (AR-414 packet in docs/roadmap/evidence/), with
    # the wrong_neighbors pointer that code always implied added under AR-433 /
    # ADR-0246, on a neighbourhood that holds the named card eligible. The
    # exact captured reply without a pointer is replayed in
    # test_the_captured_native_reply_without_a_pointer_is_repaired_not_vetoed.
    # JSON evidence attachments stay outside the governed sdist payload (AR-417).
    verdict = {
        "approved": False,
        "reason_codes": ["wrong-neighbor-selection-documentation-evidence-researcher"],
        "wrong_neighbors": [_POINTER],
    }
    outcome, _ = _run_neighbourhood(verdict)
    assert not outcome.accepted
    assert outcome.staffing.units == ()
    routing = _routing(outcome)
    codes = preflight_staffing_reason_codes(routing)
    assert codes == ["staffing_critic_rejected", "critic_wrong_neighbor_selection", _OMITTED]
    assert project_durable_routing_receipt(routing)["staffing"]["global_reason_codes"] == codes

    store = Store(tmp_path / "agency.db")
    attempt = store.begin_preflight_attempt(
        session_id="qualified-critic",
        trace_id="qualified-critic",
        host="codex",
        request_fingerprint=sha256(b"qualified native critic fixture").hexdigest(),
        request_kind="nontrivial",
    )
    binding = store.plan_resident_manager_binding(session_id="qualified-critic", host="codex")
    failure = default_preflight_failure_receipt()
    failure.update(
        stage="routing", reason_code="workforce_inference_failed", staffing_reason_codes=codes
    )
    assert store.fail_preflight_attempt(
        session_id="qualified-critic",
        trace_id="qualified-critic",
        attempt_token=attempt["attempt_token"],
        failure_receipt=failure,
        resident_manager_binding=binding,
    )
    result = finalize_response(
        "Captured veto diagnostic.",
        trace_metadata={
            "session_id": "qualified-critic",
            "trace_id": "qualified-critic",
            "host": "codex",
        },
        store=store,
    )
    assert result["action"] == "continue"
    assert "critic_wrong_neighbor_selection" in result["text"]
    assert _OMITTED in result["text"]
    assert "documentation_evidence_researcher" not in result["text"]
    assert store.get_run("qualified-critic")["status"] == "preflight_failed"
    with store._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM finalization_events").fetchone()[0] == 0


def test_the_captured_native_reply_without_a_pointer_is_repaired_not_vetoed() -> None:
    """AR-433: the exact AR-414 reply carries no pointer, so it is no longer a veto."""

    from agency_runtime.core.workforce.cache import clear_workforce_caches
    from tests.test_strict_critic_doctrine import _NEIGHBOUR as _NAMED_CARD
    from tests.test_strict_critic_doctrine import (
        _NOMINATION,
        _PLAN,
        _config,
        _context,
        _contract,
        _desktop_engineer,
        _result,
        _snapshot,
    )

    captured = {
        "approved": False,
        "reason_codes": ["wrong-neighbor-selection-documentation-evidence-researcher"],
    }
    clear_workforce_caches()
    replies = iter(
        (
            _result(_PLAN),
            _result(_NOMINATION),
            _result(captured),
            _result({"approved": True, "reason_codes": []}),
        )
    )
    prompts: list[str] = []

    def invoke(*args, **_kwargs):
        prompts.append(str(args[1]))
        return next(replies)

    from agency_runtime.core.workforce.inference import plan_and_staff_workforce

    outcome = plan_and_staff_workforce(
        "Put this editor on my machine.",
        _snapshot(_contract("operations-manager"), _contract(_NAMED_CARD), _desktop_engineer()),
        config=_config(),
        context=_context(),
        invoker=invoke,
    )
    # The name inside the code is not a pointer: the runtime cannot verify it
    # there, so the reply is refused once and the next verdict stands.
    assert outcome.attempts[-2].validation_reason_codes == ("critic_wrong_neighbor_unnamed",)
    assert "staffing_critic_rejected" not in outcome.abstention_codes
    assert "[RUNTIME VALIDATION FEEDBACK]" in prompts[3]
    assert outcome.accepted


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("wrong-neighbor-selection-" + "x" * 80, ("critic_wrong_neighbor_selection", _OMITTED)),
        ("wrong-neighbor-selectionish-" + "x" * 70, (_OMITTED,)),
        ("x" * 128, (_OMITTED,)),
        ("x" * 129, ()),
        ("wrong-neighbor-selection-" + " " * 80 + "x", ()),
        ("wrong-neighbor-selection", ("critic_wrong_neighbor_selection",)),
    ],
)
def test_oversized_valid_codes_are_explicit_without_weakening_validation(code, expected):
    assert _critic_receipt_codes((code,)) == expected


def test_qualified_reason_projection_preserves_existing_budgets() -> None:
    codes = _critic_receipt_codes(
        ("wrong-neighbor-selection-" + "x" * 80, *(f"defect-{i}" for i in range(20)))
    )
    assert len(codes) == 16
    assert all(len(code) <= 56 for code in codes)
    assert (
        len(render_fail_open_disclosure("workforce_inference_failed", codes))
        <= MAX_FAIL_OPEN_DISCLOSURE_CHARS
    )
