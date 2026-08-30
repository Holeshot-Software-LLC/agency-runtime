"""Adversarial contracts for generated Hermes turn correlation."""

from __future__ import annotations

from types import ModuleType
from typing import Any

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
