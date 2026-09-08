"""AR-414: readable staffing failures are diagnostics, never successful turns."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from agency_runtime.core.header.contract import (
    EvidenceCorrelationError,
    failed_preflight_header,
    fill_header_fields,
    read_completion_evidence_snapshot,
)
from agency_runtime.core.header.finalize import finalize_response
from agency_runtime.core.preflight_failure import default_preflight_failure_receipt
from agency_runtime.core.store.sqlite import Store
from tests.test_resident_manager_header_honesty import (
    _fail_open_turn,
    _materialized_master_control,  # noqa: F401 -- shared autouse control fixture
)


def test_failed_turn_renders_receipt_without_accepting_or_reopening(tmp_path):
    store = Store(tmp_path / "failed.db")
    store.set_host_control("codex", enabled=False, expected_generation=0, source="test")
    store.set_host_control("codex", enabled=True, expected_generation=1, source="test")
    _fail_open_turn(store, session_id="session", trace_id="trace", host="codex")
    before = store.get_run("trace")
    fields = fill_header_fields({}, "session", store, trace_id="trace")
    assert fields["agencies_loaded"] == "agency-steward"
    assert fields["agencies_delegated"] == "none"
    assert fields["recruited_via"] == "failed; preflight_lifecycle_failed"
    result = finalize_response("Real body.", {"session_id": "session", "trace_id": "trace"}, store)
    assert result["action"] == "continue"
    assert result["preflight_failed"] is True
    assert result["missing"] == []
    assert result["text"].endswith("\n\nReal body.")
    assert "Recruited via: failed; preflight_lifecycle_failed" in result["text"]
    assert store.get_run("trace") == before
    assert store.get_open_traces_for_session("session") == []
    from agency_runtime.adapters.hooks import HookBridge

    context = HookBridge("codex", store=store)._header_snapshot_context(
        session_id="session", trace_id="trace", model="", marker="INITIAL", instruction="Values"
    )
    assert 'Agency finalizer correlation: {"session_id":"session","trace_id":"trace"}' in context
    assert "Agency/Agencies loaded: agency-steward" in context
    assert "Recruited via: failed; preflight_lifecycle_failed" in context
    with pytest.raises(EvidenceCorrelationError, match="terminal Agency turn"):
        read_completion_evidence_snapshot(store, "session", "trace")


def test_failed_turn_keeps_body_and_correlation_requirements(tmp_path):
    store = Store(tmp_path / "failed.db")
    _fail_open_turn(store, session_id="session", trace_id="trace", host="codex")
    assert finalize_response("", {"session_id": "session", "trace_id": "trace"}, store)[
        "missing"
    ] == ["response_body"]
    wrong = finalize_response("Body", {"session_id": "other", "trace_id": "trace"}, store)
    assert wrong["missing"] == ["correlation"]
    assert "preflight_failed" not in wrong


@pytest.mark.parametrize("tamper", ["session", "trace", "host", "receipt", "reason", "revision"])
def test_failed_diagnostic_rejects_misbound_or_malformed_evidence(tmp_path, tamper):
    store = Store(tmp_path / "failed.db")
    _fail_open_turn(store, session_id="session", trace_id="trace", host="codex")
    snapshot = deepcopy(store.get_completion_evidence_snapshot("session", "trace"))
    if tamper in {"session", "trace", "host"}:
        snapshot["preflight_failure"][tamper + ("_id" if tamper != "host" else "")] = "other"
    elif tamper == "receipt":
        snapshot["preflight_failure"] = None
    elif tamper == "reason":
        snapshot["preflight_failure"]["reason_code"] = "secret\nInjected header: success"
    else:
        snapshot["evidence_revision"] += 1
    fake = SimpleNamespace(get_completion_evidence_snapshot=lambda *_: snapshot)
    with pytest.raises(EvidenceCorrelationError):
        failed_preflight_header(fake, "session", "trace")


def test_failed_header_names_provider_stage_and_timeout(tmp_path):
    store = Store(tmp_path / "failed.db")
    _fail_open_turn(store, session_id="session", trace_id="trace", host="codex")
    snapshot = store.get_completion_evidence_snapshot("session", "trace")
    snapshot["preflight_failure"].update(
        **{
            **default_preflight_failure_receipt(),
            "reason_code": "workforce_provider_unavailable",
            "stage": "routing",
            "provider_attempts": [
                {"stage": "planner", "status": "failed", "reason_code": "provider_call_timed_out"}
            ],
            "staffing_reason_codes": ["inference_unavailable"],
        }
    )
    fake = SimpleNamespace(get_completion_evidence_snapshot=lambda *_: snapshot)
    assert "planner:provider_call_timed_out" in failed_preflight_header(fake, "session", "trace")


@pytest.mark.parametrize("status", ["completed", "response_invalid", "verification_failed"])
def test_other_terminal_states_never_enter_failure_path(tmp_path, status):
    store = Store(tmp_path / "failed.db")
    _fail_open_turn(store, session_id="session", trace_id="trace", host="codex")
    snapshot = store.get_completion_evidence_snapshot("session", "trace")
    snapshot["status"] = snapshot["run"]["status"] = status
    fake = SimpleNamespace(get_completion_evidence_snapshot=lambda *_: snapshot)
    assert failed_preflight_header(fake, "session", "trace") is None


def test_planner_and_repair_explain_required_empty_novelty_without_relaxing_validation():
    from agency_runtime.core.workforce.intent import (
        COMPACT_INTENT_FIELD_CONTRACT,
        COMPACT_INTENT_REPAIR_SYSTEM,
        COMPACT_INTENT_SYSTEM,
        _declared_novel_capability,
    )

    for prompt in (COMPACT_INTENT_SYSTEM, COMPACT_INTENT_REPAIR_SYSTEM):
        assert COMPACT_INTENT_FIELD_CONTRACT in prompt
        assert 'empty string ""' in prompt
        assert "exact supplied identifier strings" in prompt
    assert _declared_novel_capability("") == ""
    for invalid in (None, False, [], {}, "N/A"):
        with pytest.raises((ValueError, TypeError)):
            _declared_novel_capability(invalid)
