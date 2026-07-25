from __future__ import annotations

import io
from importlib import import_module
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.adapters import base, hooks


class _AdapterStore:
    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self.prompts: dict[str, dict[str, Any] | None] = {}
        self.loaded: list[tuple[str, str, str]] = []
        self.closed: list[tuple[str, str]] = []
        self.request_kinds: dict[tuple[str, str], bool | None] = {}

    def get_host_control(self, _host: str) -> dict[str, bool]:
        return {"enabled": self.enabled}

    def get_specialist_prompt(self, slug: str, *, max_chars: int) -> dict[str, Any] | None:
        assert max_chars == 7_000
        return self.prompts.get(slug)

    def record_specialist_loaded(
        self,
        session_id: str,
        slug: str,
        *,
        trace_id: str,
    ) -> None:
        self.loaded.append((session_id, trace_id, slug))

    def close_turn_evidence(self, session_id: str, trace_id: str) -> None:
        self.closed.append((session_id, trace_id))

    def is_nontrivial_turn(self, session_id: str, trace_id: str) -> bool | None:
        return self.request_kinds.get((session_id, trace_id))


class _Adapter(base.BaseAdapter):
    host_name = "codex"

    def is_available(self) -> bool:
        return True

    def get_delegate_backend(self) -> str | None:
        return None


def test_base_result_and_nested_value_defensive_branches() -> None:
    assert base._failure_message({"content": [{"text": "failure detail"}]}) == "failure detail"
    assert base._failure_message({"content": [None]}) == "tool call failed"
    assert base._text_failure_reason('{"status":"failed"}', 0) == "tool call failed"
    assert base._nested_value({}, ("id",), _depth=6) is None
    assert base._nested_value("{invalid", ("id",)) is None
    assert base._nested_value({"id": "direct"}, ("id",)) == "direct"
    assert base._nested_value({"result": {"id": "nested"}}, ("id",)) == "nested"


def test_base_finalization_and_shared_specialist_prompt_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _AdapterStore(enabled=False)
    adapter = _Adapter(store=store)  # type: ignore[arg-type]
    assert adapter.apply_finalization("draft", "session", trace_id="turn") == "draft"

    header_finalize = import_module("agency_runtime.core.header.finalize")

    store.enabled = True
    monkeypatch.setattr(
        header_finalize,
        "finalize_response",
        lambda draft, **_kwargs: {
            "action": "accept",
            "text": f"final:{draft}",
        },
    )
    assert adapter.apply_finalization("draft", "session", trace_id="turn") == "final:draft"
    # Terminal persistence belongs to the shared finalizer; adapter wrappers
    # must not reintroduce a split record/close transaction.
    assert store.closed == []

    from agency_runtime.core.specialist_context import (
        MAX_SELECTED_SPECIALISTS,
        hydrate_selected_specialist_context,
    )

    catalog = [{"slug": f"agent-{index}"} for index in range(6)]
    store.prompts = {
        f"agent-{index}": {
            "agent_slug": f"agent-{index}",
            "prompt_body": f"prompt-{index}",
            "version": "1.0",
            "prompt_hash": f"hash-{index}",
        }
        for index in range(6)
    }
    selected = hydrate_selected_specialist_context(
        store,  # type: ignore[arg-type]
        catalog,
        {"selected_ids": [f"agent-{index}" for index in range(6)]},
        session_id="session",
        trace_id="turn",
    )
    assert selected.slugs == tuple(f"agent-{index}" for index in range(MAX_SELECTED_SPECIALISTS))
    assert f"prompt-{MAX_SELECTED_SPECIALISTS - 1}" in selected.context
    assert f"prompt-{MAX_SELECTED_SPECIALISTS}" not in selected.context
    store.prompts["missing"] = None
    missing = hydrate_selected_specialist_context(
        store,  # type: ignore[arg-type]
        [{"slug": "missing"}],
        {"selected_ids": ["missing"]},
        session_id="session",
        trace_id="missing-turn",
    )
    assert missing.slugs == ()
    assert missing.context == ""


def test_base_preflight_projects_shared_turn_result_and_reads_persisted_request_kind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _AdapterStore()
    adapter = _Adapter(store=store)  # type: ignore[arg-type]

    import agency_runtime.core.preflight as preflight

    trivial = preflight.PreflightResult(
        session_id="session",
        trace_id="trivial-turn",
        routing={"status": "trivial"},
        context="fallback context",
        loaded_specialists=("agents-orchestrator", "chief-of-staff"),
        selected_specialists=("agents-orchestrator", "chief-of-staff"),
        trivial=True,
        roster_size=9,
    )
    monkeypatch.setattr(preflight, "run_preflight", lambda *_args, **_kwargs: trivial)
    assert adapter.build_preflight_context("session", "hi") == trivial.as_dict()
    store.request_kinds[("session", "trivial-turn")] = False
    assert adapter._was_nontrivial_turn("session", "trivial-turn") is False

    nontrivial = preflight.PreflightResult(
        session_id="session",
        trace_id="complex-turn",
        routing={"status": "selected"},
        context="specialist context",
        loaded_specialists=("code-reviewer",),
        selected_specialists=("code-reviewer",),
        trivial=False,
        roster_size=9,
    )
    monkeypatch.setattr(preflight, "run_preflight", lambda *_args, **_kwargs: nontrivial)
    assert adapter.build_preflight_context("session", "review the implementation") == (
        nontrivial.as_dict()
    )
    store.request_kinds[("session", "complex-turn")] = True
    assert adapter._was_nontrivial_turn("session", "complex-turn") is True


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
        self.closed: list[tuple[str, str, str]] = []
        self.run_status: dict[str, str] = {}

    def reserve_session_turn(self, **kwargs: str) -> dict[str, Any]:
        return {
            "trace_id": kwargs["trace_id"],
            "created": True,
            "abandoned": [],
            "reservation_token": "00000000-0000-4000-9000-000000000001",
        }

    def abandon_preflight_reservation(self, **kwargs: str) -> bool:
        self.close_turn_evidence(
            kwargs["session_id"],
            kwargs["trace_id"],
            status=kwargs["status"],
        )
        return True

    def recent_runtime_activity(self, *, limit: int) -> Any:
        assert limit == 200
        if isinstance(self.activity, Exception):
            raise self.activity
        return self.activity

    def get_completion_evidence_snapshot(
        self,
        _session_id: str,
        _trace_id: str,
    ) -> dict[str, Any]:
        return {}

    def record_finalization(self, **kwargs: Any) -> str:
        if self.fail_finalization:
            raise RuntimeError("database unavailable")
        receipt = f"00000000-0000-4000-8000-{len(self.finalizations) + 1:012d}"
        self.finalizations.append({**kwargs, "id": receipt})
        return receipt

    def has_finalization_action(
        self,
        trace_id: str,
        action: str,
        *,
        response_hash: str = "",
    ) -> bool:
        return any(
            row.get("trace_id") == trace_id
            and row.get("action") == action
            and (not response_hash or row.get("response_hash") == response_hash)
            for row in self.finalizations
        )

    def get_run(self, trace_id: str) -> dict[str, str]:
        return {
            "trace_id": trace_id,
            "session_id": "session",
            "status": self.run_status.get(trace_id, "active"),
        }

    def get_authoritative_finalization(
        self,
        session_id: str,
        trace_id: str,
        *,
        action: str = "",
        response_hash: str = "",
    ) -> dict[str, str] | None:
        if session_id != "session":
            return None
        for row in reversed(self.finalizations):
            if (
                row.get("trace_id") == trace_id
                and row.get("action") == action
                and row.get("response_hash") == response_hash
                and self.run_status.get(trace_id) == "completed"
            ):
                return {
                    **{key: str(value) for key, value in row.items()},
                    "status": "completed",
                }
        return None

    def commit_terminal_finalization(self, **kwargs: Any) -> dict[str, Any]:
        self.record_finalization(**kwargs)
        self.run_status[str(kwargs["trace_id"])] = str(kwargs["status"])
        self.close_turn_evidence(
            str(kwargs["session_id"]),
            str(kwargs["trace_id"]),
            status=str(kwargs["status"]),
        )
        return {
            "outcome": "committed",
            "authoritative": True,
            "event_id": "event",
            "action": kwargs["action"],
            "response_hash": kwargs["response_hash"],
            "status": kwargs["status"],
        }

    def close_turn_evidence(
        self,
        session_id: str,
        trace_id: str,
        *,
        status: str,
    ) -> None:
        self.run_status[trace_id] = status
        self.closed.append((session_id, trace_id, status))


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
    rejected = bridge.handle(
        {"hook_event_name": "Stop", "session_id": "session", "last_assistant_message": ""}
    )
    assert rejected["continue"] is False
    assert "could not verify or persist" in rejected["stopReason"]
    assert bridge.handle({"hook_event_name": "SessionStart", "session_id": "session"}) == {}


def test_hook_stop_accept_records_finalization() -> None:
    store = _HookStore()
    adapter = _HookAdapter()
    adapter.verification = {"action": "accept", "evidence_revision": 1}
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
    assert store.closed == [("session", "trace", "completed")]


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
