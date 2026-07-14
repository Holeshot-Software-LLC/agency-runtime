from __future__ import annotations

import io
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.adapters import base, hooks


class _AdapterStore:
    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self.prompts: dict[str, dict[str, Any] | None] = {}
        self.loaded: list[tuple[str, str]] = []

    def get_host_control(self, _host: str) -> dict[str, bool]:
        return {"enabled": self.enabled}

    def get_specialist_prompt(self, slug: str, *, max_chars: int) -> dict[str, Any] | None:
        assert max_chars == 12_000
        return self.prompts.get(slug)

    def record_specialist_loaded(self, session_id: str, slug: str) -> None:
        self.loaded.append((session_id, slug))


class _Adapter(base.BaseAdapter):
    host_name = "test"

    def is_available(self) -> bool:
        return True

    def report_skills_loaded(self, session_id: str) -> list[str]:
        return []

    def report_specialists_loaded(self, session_id: str) -> list[str]:
        return []

    def get_delegate_backend(self) -> str | None:
        return None

    def expose_model_telemetry(self, session_id: str) -> dict[str, Any]:
        return {}


def test_base_result_and_nested_value_defensive_branches() -> None:
    assert base._failure_message({"content": [{"text": "failure detail"}]}) == "failure detail"
    assert base._failure_message({"content": [None]}) == "tool call failed"
    assert base._text_failure_reason('{"status":"failed"}', 0) == "tool call failed"
    assert base._nested_value({}, ("id",), _depth=6) is None
    assert base._nested_value("{invalid", ("id",)) is None
    assert base._nested_value({"id": "direct"}, ("id",)) == "direct"
    assert base._nested_value({"result": {"id": "nested"}}, ("id",)) == "nested"


def test_base_finalization_and_selected_prompt_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _AdapterStore(enabled=False)
    adapter = _Adapter(store=store)  # type: ignore[arg-type]
    assert adapter.apply_finalization("draft", "trace") == "draft"

    import agency_runtime.core.header.contract as contract

    store.enabled = True
    monkeypatch.setattr(contract, "finalize_header", lambda draft, **_kwargs: f"final:{draft}")
    assert adapter.apply_finalization("draft", "trace") == "final:draft"

    catalog = [{"slug": f"agent-{index}"} for index in range(6)]
    store.prompts = {
        f"agent-{index}": {
            "agent_slug": f"agent-{index}",
            "prompt_body": f"prompt-{index}",
        }
        for index in range(6)
    }
    selected = adapter._selected_catalog_agents(
        catalog,
        {"selected_ids": [f"agent-{index}" for index in range(6)]},
    )
    assert len(selected) == 5
    store.prompts["missing"] = None
    assert (
        adapter._selected_catalog_agents([{"slug": "missing"}], {"selected_ids": ["missing"]}) == []
    )


def test_base_trivial_preflight_empty_prompt_and_no_companion_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _AdapterStore()
    store.get_active_roster_as_catalog = lambda: [{"slug": "writer"}]  # type: ignore[attr-defined]
    adapter = _Adapter(store=store)  # type: ignore[arg-type]

    import agency_runtime.core.selector.pipeline as pipeline
    import agency_runtime.core.selector.policy as policy

    monkeypatch.setattr(pipeline, "is_trivial", lambda _message: True)
    monkeypatch.setattr(policy, "detect_actions", lambda *_args, **_kwargs: ([], ["writer"]))
    assert adapter.build_preflight_context("session", "hi") is None

    monkeypatch.setattr(policy, "detect_actions", lambda *_args, **_kwargs: ([], []))
    assert adapter.build_preflight_context("session", "hi") is None
    monkeypatch.setattr(policy, "detect_actions", lambda *_args, **_kwargs: ([], ["absent"]))
    assert adapter.build_preflight_context("session", "hi") is None

    monkeypatch.setattr(pipeline, "is_trivial", lambda _message: False)
    store.get_active_roster_as_catalog = lambda: [{"slug": "writer"}]  # type: ignore[attr-defined]
    monkeypatch.setattr(pipeline, "route", lambda *_args, **_kwargs: {"selected_ids": []})
    monkeypatch.setattr(pipeline, "build_routing_context", lambda _routing: "")
    import agency_runtime.core.delegation.events as events

    monkeypatch.setattr(events, "record_suggested_delegations", lambda *_args, **_kwargs: None)
    assert adapter.build_preflight_context("", "complex") is None


@pytest.mark.parametrize(
    ("function", "args"),
    [
        (hooks._optional_string, ({"value": 1}, "value")),
        (hooks._required_string, ({}, "value")),
        (hooks._optional_bool, ({"value": "true"}, "value")),
    ],
)
def test_hook_scalar_contracts(function: Any, args: tuple[Any, ...]) -> None:
    with pytest.raises(hooks.HookInputError):
        function(*args)


def test_canonical_tool_call_mapping_branches() -> None:
    assert hooks._canonical_tool_call("codex", "skill", {"command": "review"}, {}) == (
        "skill_view",
        {"command": "review", "name": "review"},
    )
    assert hooks._canonical_tool_call("codex", "agency_agents_load", {"slug": "a"}, {}) == (
        "agency_agents_load",
        {"slug": "a"},
    )
    assert hooks._canonical_tool_call("codex", "unknown", None, {}) == ("unknown", {})


class _HookStore:
    def __init__(self, activity: Any = None, *, fail_finalization: bool = False) -> None:
        self.activity = activity
        self.fail_finalization = fail_finalization
        self.finalizations: list[dict[str, Any]] = []

    def recent_runtime_activity(self, *, limit: int) -> Any:
        assert limit == 200
        if isinstance(self.activity, Exception):
            raise self.activity
        return self.activity

    def record_finalization(self, **kwargs: Any) -> None:
        if self.fail_finalization:
            raise RuntimeError("database unavailable")
        self.finalizations.append(kwargs)


class _HookAdapter:
    def __init__(self) -> None:
        self.preflight: Any = None
        self.verification: Any = None
        self.tool_calls: list[dict[str, Any]] = []

    def pre_llm_call_handler(self, **_kwargs: Any) -> Any:
        return self.preflight

    def post_tool_call_handler(self, **kwargs: Any) -> None:
        self.tool_calls.append(kwargs)

    def pre_verify_handler(self, *_args: Any, **_kwargs: Any) -> Any:
        return self.verification


def test_hook_bridge_validation_recovery_and_noop_events() -> None:
    with pytest.raises(ValueError, match="unsupported hook host"):
        hooks.HookBridge("other", store=object(), adapter=object())  # type: ignore[arg-type]
    bridge = hooks.HookBridge("codex", store=_HookStore(), adapter=_HookAdapter())  # type: ignore[arg-type]
    with pytest.raises(hooks.HookInputError, match="unsupported codex"):
        bridge._event_name({"hook_event_name": "Unknown"})
    assert bridge._unambiguous_open_trace("") == ""

    bridge.store = _HookStore(RuntimeError("unavailable"))  # type: ignore[assignment]
    assert bridge._unambiguous_open_trace("session") == ""
    bridge.store = _HookStore([])  # type: ignore[assignment]
    assert bridge._unambiguous_open_trace("session") == ""

    with pytest.raises(hooks.HookInputError, match="JSON object"):
        bridge.handle([])  # type: ignore[arg-type]
    assert (
        bridge.handle(
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": "session",
                "prompt": "Agency header invalid: revise",
            }
        )
        == {}
    )
    assert (
        bridge.handle(
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": "session",
                "prompt": "hello",
            }
        )
        == {}
    )
    assert (
        bridge.handle(
            {"hook_event_name": "Stop", "session_id": "session", "last_assistant_message": ""}
        )
        == {}
    )
    assert bridge.handle({"hook_event_name": "SessionStart", "session_id": "session"}) == {}


def test_hook_finalization_persistence_failure_is_fail_open() -> None:
    store = _HookStore(fail_finalization=True)
    adapter = _HookAdapter()
    bridge = hooks.HookBridge("claude", store=store, adapter=adapter)  # type: ignore[arg-type]
    bridge._record_finalization("trace", "accept")
    bridge._record_finalization("", "accept")
    assert store.finalizations == []


def test_hook_stop_accept_records_finalization() -> None:
    store = _HookStore()
    adapter = _HookAdapter()
    bridge = hooks.HookBridge("claude", store=store, adapter=adapter)  # type: ignore[arg-type]
    assert (
        bridge.handle(
            {
                "hook_event_name": "Stop",
                "session_id": "session",
                "turn_id": "trace",
                "last_assistant_message": "complete",
            }
        )
        == {}
    )
    assert store.finalizations[0]["action"] == "accept"


def test_hook_output_binary_text_size_and_serialization_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binary = io.BytesIO()
    hooks._write_output(binary, {"value": object()})
    assert binary.getvalue() == b"{}\n"

    monkeypatch.setattr(hooks, "MAX_HOOK_OUTPUT_BYTES", 2)
    text = io.StringIO()
    hooks._write_output(text, {"value": "large"})
    assert text.getvalue() == "{}\n"


def test_hook_stdio_nonobject_nonresult_and_unexpected_fail_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for payload in (b"[]", b"{}"):
        output = io.BytesIO()
        errors = io.StringIO()
        if payload == b"{}":
            bridge = SimpleNamespace(handle=lambda _payload: [])
            monkeypatch.setattr(
                hooks,
                "HookBridge",
                lambda *_args, bridge=bridge, **_kwargs: bridge,
            )
        assert (
            hooks.run_hook_stdio(
                "codex",
                input_stream=io.BytesIO(payload),
                output_stream=output,
                error_stream=errors,
            )
            == 0
        )
        assert output.getvalue() == b"{}\n"
        assert "host operation continues" in errors.getvalue()

    bridge = SimpleNamespace(
        handle=lambda _payload: (_ for _ in ()).throw(OSError("storage unavailable"))
    )
    monkeypatch.setattr(hooks, "HookBridge", lambda *_args, **_kwargs: bridge)
    output = io.BytesIO()
    errors = io.StringIO()
    assert (
        hooks.run_hook_stdio(
            "codex",
            input_stream=io.BytesIO(b"{}"),
            output_stream=output,
            error_stream=errors,
        )
        == 0
    )
    assert "OSError" in errors.getvalue()

    bridge = SimpleNamespace(handle=lambda _payload: {})
    monkeypatch.setattr(hooks, "HookBridge", lambda *_args, **_kwargs: bridge)
    output = io.BytesIO()
    assert (
        hooks.run_hook_stdio(
            "codex",
            input_stream=io.BytesIO(b"{}"),
            output_stream=output,
            error_stream=io.StringIO(),
        )
        == 0
    )
    assert output.getvalue() == b"{}\n"
