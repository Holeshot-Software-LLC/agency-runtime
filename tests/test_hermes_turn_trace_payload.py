"""Adversarial contracts for generated Hermes turn correlation."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.installer_payload_hermes import render_hermes_plugin


def _generated_plugin() -> ModuleType:
    source = render_hermes_plugin(
        5,
        AgencyConfig(),
        python_executable="/trusted/python",
        bootstrap_path="/trusted/bootstrap.py",
    )
    module = ModuleType("generated_hermes_turn_trace")
    exec(compile(source, "<generated-hermes-turn-trace>", "exec"), module.__dict__)
    return module


@pytest.mark.parametrize("trace_id", ["turn", "other-turn", ""])
def test_native_failure_formats_only_exact_turn_and_never_accepts(
    tmp_path: Path,
    trace_id: str,
) -> None:
    from agency_runtime.adapters.hermes import bridge
    from agency_runtime.core.header.contract import fill_header_fields, format_header
    from agency_runtime.core.store.sqlite import Store

    store = Store(tmp_path / "failure.db")
    store.create_run(
        trace_id="turn",
        session_id="session",
        host="hermes",
        metadata={"request_kind": "nontrivial"},
    )
    store.create_run(trace_id="other-turn", session_id="other-session", host="hermes")
    store.record_specialist_loaded("session", "code-reviewer", trace_id="turn")
    adapter = SimpleNamespace(store=store)
    payload = {
        "session_id": "session",
        "trace_id": trace_id,
        "response_text": "Response truncated",
        "failed": True,
    }
    expected = format_header(fill_header_fields({}, "session", store, "", "turn"))
    result = bridge._transform_turn_failure(adapter, payload)
    if trace_id == "turn":
        assert result.startswith(expected + "\n\nNative Hermes turn failed:")
    else:
        assert result == "Response truncated"
    assert store.get_run("turn")["status"] == "active"
    bridge._close_session(adapter, payload)
    assert store.get_run("turn")["status"] == ("failed" if trace_id == "turn" else "active")
    assert store.get_run("other-turn")["status"] == "active"
    assert store.get_authoritative_finalization("session", "turn") is None


def test_generated_failure_hook_preserves_native_failure_and_correlation() -> None:
    module = _generated_plugin()
    calls = []
    module._ACTIVE_TURN_TRACES["session"] = "turn"
    module._invoke = lambda action, payload: calls.append((action, payload)) or "Diagnostic"
    assert (
        module._transform_turn_failure("Partial", session_id="session", failed=True) == "Diagnostic"
    )
    assert calls[0][0] == "transform_turn_failure"
    assert calls[0][1]["trace_id"] == "turn"
    module._on_session_end(session_id="session", completed=False, failed=True)
    assert calls[-1][1]["failed"] is True
    assert calls[-1][1]["completed"] is False
    assert module._ACTIVE_TURN_TRACES == {}


def test_generated_plugin_preserves_preflight_trace_for_current_hermes_hooks() -> None:
    module = _generated_plugin()
    calls: list[tuple[str, dict[str, Any]]] = []

    def invoke(action: str, payload: dict[str, Any] | None = None) -> Any:
        values = dict(payload or {})
        calls.append((action, values))
        if action == "pre_llm_call":
            return {
                "session_id": values["session_id"],
                "trace_id": "generated-turn",
                "context": "routed",
            }
        if action == "transform_llm_output":
            return "finalized"
        return None

    module._invoke = invoke
    assert (
        module._pre_llm_call(
            session_id="session",
            user_message="Review this.",
            model="router",
        )["trace_id"]
        == "generated-turn"
    )
    # Current Hermes source supplies both session_id and task_id to the tool
    # callback. The task identifier must never replace the remembered trace.
    module._post_tool_call(
        tool_name="delegate_task",
        args={"task": "review"},
        result='{"status":"completed"}',
        session_id="session",
        task_id="tool-1",
    )
    module._post_api_request(
        session_id="session",
        request_id="provider-request",
        model="provider/model",
    )
    module._pre_verify("draft", session_id="session", attempt=0)
    assert module._transform_llm_output("draft", session_id="session") == "finalized"
    module._on_session_end(session_id="session", completed=True)

    for action, payload in calls[1:]:
        assert action in {
            "post_tool_call",
            "post_api_request",
            "pre_verify",
            "transform_llm_output",
            "on_session_end",
        }
        assert payload["session_id"] == "session"
        assert payload["trace_id"] == "generated-turn"
    assert module._ACTIVE_TURN_TRACES == {}


def test_generated_plugin_rejects_task_only_or_conflicting_tool_correlation() -> None:
    module = _generated_plugin()
    calls: list[tuple[str, dict[str, Any]]] = []

    def invoke(action: str, payload: dict[str, Any] | None = None) -> Any:
        values = dict(payload or {})
        calls.append((action, values))
        if action == "pre_llm_call":
            return {
                "session_id": "session",
                "trace_id": "turn",
                "context": "routed",
            }
        return None

    module._invoke = invoke
    module._pre_llm_call(session_id="session", user_message="task")
    module._post_tool_call(tool_name="delegate_task", task_id="tool-only")
    module._post_tool_call(
        tool_name="delegate_task",
        session_id="session",
        task_id="tool",
        turn_id="different-turn",
    )

    assert [action for action, _payload in calls] == ["pre_llm_call"]
    assert module._correlation({"task_id": "tool-only"}) == ("tool-only", "")


def test_generated_plugin_replaces_stale_session_trace_on_each_preflight() -> None:
    module = _generated_plugin()
    traces = iter(("turn-one", "turn-two"))

    def invoke(action: str, payload: dict[str, Any] | None = None) -> Any:
        if action != "pre_llm_call":
            return None
        values = dict(payload or {})
        return {
            "session_id": values["session_id"],
            "trace_id": next(traces),
            "context": "routed",
        }

    module._invoke = invoke
    module._pre_llm_call(session_id="session", user_message="first")
    assert module._correlation({"session_id": "session"}) == ("session", "turn-one")
    module._pre_llm_call(session_id="session", user_message="second")
    assert module._correlation({"session_id": "session"}) == ("session", "turn-two")


@pytest.mark.parametrize(
    "untrusted_metadata",
    [
        {},
        {"invocation_purpose": "title_generation"},
        {"invocation_purpose": "background_review"},
        {"invocation_purpose": "unknown"},
        {"invocation_purpose": {"kind": "summary"}},
        {"is_internal": True},
        {
            "origin_receipt": {
                "origin": "internal_retry",
                "session_id": "previous-session",
                "trace_id": "previous-turn",
            }
        },
    ],
)
@pytest.mark.parametrize(
    "user_message",
    ["agency status", "Use the requested skill.", "Review the proposed change."],
)
def test_generated_plugin_untrusted_purpose_never_suppresses_user_preflight(
    untrusted_metadata: dict[str, Any], user_message: str
) -> None:
    """AR-280: caller labels are not authenticated native lifecycle evidence."""
    module = _generated_plugin()
    calls: list[tuple[str, dict[str, Any]]] = []

    def invoke(action: str, payload: dict[str, Any] | None = None) -> Any:
        values = dict(payload or {})
        calls.append((action, values))
        return {
            "session_id": values["session_id"],
            "trace_id": values["trace_id"],
            "context": "preflight-result",
        }

    module._invoke = invoke
    module._remember_turn("session", "previous-turn")
    result = module._pre_llm_call(
        session_id="session",
        turn_id="current-turn",
        user_message=user_message,
        model="router",
        **untrusted_metadata,
    )

    assert len(calls) == 1
    action, payload = calls[0]
    assert action == "pre_llm_call"
    assert payload["session_id"] == "session"
    assert payload["trace_id"] == "current-turn"
    assert payload["user_message"] == user_message
    assert not set(untrusted_metadata).intersection(payload)
    assert result["trace_id"] == "current-turn"
    assert module._correlation({"session_id": "session"}) == (
        "session",
        "current-turn",
    )
