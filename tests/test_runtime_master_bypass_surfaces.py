"""Cross-surface contracts for the durable Agency master switch."""

from __future__ import annotations

import asyncio
import io
import json
from argparse import Namespace
from types import SimpleNamespace
from typing import Any

import pytest

import agency_runtime.adapters.hermes.bridge as hermes_bridge
import agency_runtime.adapters.hooks as hook_module
import agency_runtime.adapters.litellm.callback as litellm_callback
import agency_runtime.adapters.openclaw.node_bridge as openclaw_bridge
import agency_runtime.cli.install_commands as install_commands
import agency_runtime.core.host_control as host_control
import agency_runtime.core.runtime_control as runtime_control
import agency_runtime.server.http as http_server
import agency_runtime.server.mcp as mcp_server
from agency_runtime import AgencyRuntime
from agency_runtime.adapters.base import BaseAdapter
from agency_runtime.adapters.litellm.callback import AgencyLiteLLMCallback
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.header.finalize import response_hash


class _UnexpectedAccess(AssertionError):
    """Raised when an off-mode boundary touches work behind the master gate."""


def _unexpected(*_args: Any, **_kwargs: Any) -> Any:
    raise _UnexpectedAccess("off-mode boundary performed Agency work")


class _BombStore:
    def __getattr__(self, _name: str) -> Any:
        return _unexpected()


class _ConcreteAdapter(BaseAdapter):
    host_name = "codex"

    def is_available(self) -> bool:
        return True

    def get_delegate_backend(self) -> str | None:
        return None


def _master(enabled: bool, generation: int = 7, *, source: str = "test") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "enabled": enabled,
        "generation": generation,
        "updated_at": "2026-07-16T12:00:00Z",
        "source": source,
    }


def _set_master(monkeypatch: pytest.MonkeyPatch, enabled: bool) -> None:
    monkeypatch.setattr(runtime_control, "master_enabled", lambda: enabled)
    monkeypatch.setattr(
        runtime_control,
        "read_enforcement_runtime_control",
        lambda: (_master(enabled), "test"),
    )


def test_base_adapter_global_off_precedes_store_host_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch, False)
    adapter = _ConcreteAdapter(store=_BombStore())  # type: ignore[arg-type]

    assert adapter.runtime_enabled() is False


def test_public_facade_global_off_is_lazy_and_work_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every public work boundary bypasses before Store or input validation."""

    import agency_runtime.core.store.sqlite as sqlite_store

    _set_master(monkeypatch, False)
    monkeypatch.setattr(sqlite_store, "Store", _unexpected)
    runtime = AgencyRuntime("must-not-open.db")
    exact = "  exact public draft \N{EM DASH}\nunchanged  "

    routing = runtime.route("", "", trace_id="turn")
    preflight = runtime.preflight("", "", trace_id="turn")

    assert routing["status"] == "bypassed"
    assert routing["selected_ids"] == []
    assert preflight["routing"]["status"] == "bypassed"
    assert preflight["context"] == ""
    assert runtime.route_with_context("", "", trace_id="turn") == ""
    assert runtime.detect_work_units("1. inspect\n2. mutate") == {
        "count": 0,
        "confidence": "none",
        "source": "master_control",
        "units": [],
        "delegate": False,
    }
    assert runtime.get_roster() == []
    assert runtime.search("security") == []
    assert runtime.record_skill("", "", trace_id="") is None
    assert runtime.record_specialist("", "", trace_id="") is None
    assert runtime.record_model_receipt(trace_id="", session_id="") == ""
    assert (
        runtime.record_delegation(
            trace_id="",
            session_id="",
            work_unit_id="",
            recommended_agent="",
        )
        == ""
    )
    assert runtime.finalize_header(exact, trace_id="") == exact
    assert runtime._store is None


def test_hook_bridge_global_off_precedes_event_and_correlation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch, False)
    bridge = hook_module.HookBridge(
        "codex",
        store=_BombStore(),  # type: ignore[arg-type]
        adapter=SimpleNamespace(),
    )
    monkeypatch.setattr(bridge, "_event_name", _unexpected)

    assert bridge.handle({"malformed": "but framed"}) == {}


def test_hook_bridge_honors_brokered_off_state_from_a_restricted_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runtime_control,
        "read_effective_runtime_control",
        lambda **_kwargs: (_ for _ in ()).throw(
            runtime_control.RuntimeControlSecurityError("restricted reader unavailable")
        ),
    )
    monkeypatch.setattr(
        runtime_control,
        "_restricted_windows_control_target",
        lambda _path: True,
    )
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.dashboard_api_request",
        lambda path, *, timeout: (
            {"master": _master(False, source="dashboard")}
            if path == "/api/runtime" and timeout == 0.25
            else _unexpected()
        ),
    )
    bridge = hook_module.HookBridge(
        "codex",
        store=_BombStore(),  # type: ignore[arg-type]
        adapter=SimpleNamespace(),
    )
    monkeypatch.setattr(bridge, "_event_name", _unexpected)

    assert bridge.handle({"malformed": "but framed"}) == {}


def test_hook_stdio_global_off_never_constructs_bridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch, False)
    monkeypatch.setattr(hook_module, "HookBridge", _unexpected)
    source = io.BytesIO(
        json.dumps(
            {
                "hook_event_name": "Stop",
                "session_id": "session",
                "turn_id": "turn",
                "final_response": "exact draft",
            }
        ).encode()
    )
    sink = io.BytesIO()

    assert (
        hook_module.run_hook_stdio(
            "codex",
            expected_event="Stop",
            input_stream=source,
            output_stream=sink,
        )
        == 0
    )
    assert json.loads(sink.getvalue()) == {}


def test_hook_stdio_threads_one_master_snapshot_through_the_bridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reads = 0

    def read_master() -> tuple[dict[str, Any], str]:
        nonlocal reads
        reads += 1
        return _master(True), "dashboard"

    monkeypatch.setattr(runtime_control, "read_enforcement_runtime_control", read_master)
    source = io.BytesIO(b"{}")
    sink = io.BytesIO()

    assert (
        hook_module.run_hook_stdio(
            "codex",
            input_stream=source,
            output_stream=sink,
            error_stream=io.StringIO(),
        )
        == 0
    )
    assert reads == 1
    assert json.loads(sink.getvalue()) == {}


def test_hook_stdio_global_off_defers_explicit_store_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch, False)
    monkeypatch.setattr(hook_module, "Store", _unexpected)
    source = io.BytesIO(
        json.dumps(
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": "session",
                "turn_id": "turn",
                "prompt": "review",
            }
        ).encode()
    )
    sink = io.BytesIO()

    assert (
        hook_module.run_hook_stdio(
            "codex",
            db_path="must-not-open.db",
            config_path="must-not-load.yaml",
            expected_event="UserPromptSubmit",
            input_stream=source,
            output_stream=sink,
        )
        == 0
    )
    assert json.loads(sink.getvalue()) == {}


def test_hermes_global_off_preserves_exact_response_without_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch, False)
    monkeypatch.setattr(hermes_bridge, "_adapter", _unexpected)
    exact = "  exact response \N{EM DASH} including whitespace  \n"

    assert hermes_bridge.handle({"action": "transform_llm_output", "response_text": exact}) == exact
    assert hermes_bridge.handle({"action": "pre_llm_call"}) is None


def test_openclaw_global_off_seals_exact_outbound_without_correlation_or_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch, False)
    monkeypatch.setattr(openclaw_bridge, "validate_correlation_id", _unexpected)
    monkeypatch.setattr(openclaw_bridge, "OpenClawAdapter", _unexpected)
    outbound = "  exact outbound \N{EM DASH}\nunchanged  "

    result = openclaw_bridge.handle(
        {
            "action": "outbound_gate",
            "outboundPayload": outbound,
            "finalResponse": "must not be selected",
            "sessionId": "invalid if parsed",
            "traceId": "invalid if parsed",
        }
    )

    assert result == {
        "action": "allow",
        "responseHash": response_hash(outbound),
        "runtimeDisabled": True,
        "bypassed": True,
    }


def test_openclaw_installed_main_global_off_skips_config_and_store(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_master(monkeypatch, False)
    outbound = "  installed outbound \N{EM DASH}\nunchanged  "
    monkeypatch.setattr(
        openclaw_bridge,
        "_read_payload",
        lambda: {
            "action": "outbound_gate",
            "outboundPayload": outbound,
            "finalResponse": "not selected",
        },
    )
    monkeypatch.setattr(openclaw_bridge, "_config_path", _unexpected)
    monkeypatch.setattr(openclaw_bridge, "_configured_adapter", _unexpected)

    assert openclaw_bridge.main(["--config", "must-not-load.yaml"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "action": "allow",
        "responseHash": response_hash(outbound),
        "runtimeDisabled": True,
        "bypassed": True,
    }


def _bare_http_handler(path: str) -> tuple[Any, list[dict[str, Any]], list[tuple[Any, str]]]:
    handler = object.__new__(http_server.AgencyHTTPHandler)
    handler.path = path
    handler.server = SimpleNamespace(store=object())
    payloads: list[dict[str, Any]] = []
    errors: list[tuple[Any, str]] = []
    handler._validate_request_boundary = lambda **_kwargs: True
    handler._json_ok = payloads.append
    handler._json_error = lambda status, message: errors.append((status, message))
    return handler, payloads, errors


def test_http_global_off_status_and_roster_never_touch_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch, False)
    reads = 0

    def read_master() -> tuple[dict[str, Any], str]:
        nonlocal reads
        reads += 1
        return _master(False), "dashboard"

    monkeypatch.setattr(
        runtime_control,
        "read_enforcement_runtime_control",
        read_master,
    )

    status_handler, status_payloads, status_errors = _bare_http_handler("/status")
    status_handler.do_GET()
    roster_handler, roster_payloads, roster_errors = _bare_http_handler("/roster")
    roster_handler.do_GET()

    assert status_errors == []
    assert status_payloads == [
        {
            "status": "ok",
            "runtime_enabled": False,
            "bypassed": True,
            "master": _master(False),
        }
    ]
    assert roster_errors == []
    assert roster_payloads == [
        {
            "runtime_enabled": False,
            "bypassed": True,
            "agents": [],
            "count": 0,
        }
    ]
    assert reads == 2


def test_http_global_off_finalize_preserves_exact_draft_before_runtime_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch, False)
    for name in (
        "run_preflight",
        "explain_route",
        "finalize_response",
        "validate_correlation_id",
    ):
        monkeypatch.setattr(http_server, name, _unexpected)
    handler, payloads, errors = _bare_http_handler("/finalize")
    exact = "  exact HTTP draft \N{EM DASH}\nunchanged  "
    handler._read_json_body = lambda: {"draft_text": exact}

    handler.do_POST()

    assert errors == []
    assert payloads == [
        {
            "runtime_enabled": False,
            "bypassed": True,
            "action": "bypass",
            "text": exact,
        }
    ]


def test_http_global_on_uses_existing_dispatch_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch, True)
    handler, payloads, errors = _bare_http_handler("/finalize")
    body = {"draft_text": "draft"}
    dispatched: list[dict[str, Any]] = []
    handler._read_json_body = lambda: body
    handler._handle_finalize = dispatched.append

    handler.do_POST()

    assert dispatched == [body]
    assert payloads == []
    assert errors == []


def test_mcp_global_off_bypasses_delegation_and_preserves_exact_finalize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch, False)
    monkeypatch.setattr("agency_runtime.server.mcp_tools.dispatch_tool_call", _unexpected)
    exact = "  exact MCP draft \N{EM DASH}\nunchanged  "

    delegated = mcp_server.handle_tool_call(
        "agency.delegate",
        {"agent": "code-reviewer", "task": "review"},
        store=_BombStore(),
    )
    finalized = mcp_server.handle_tool_call(
        "agency.finalize",
        {"draft_text": exact},
        store=_BombStore(),
    )

    assert delegated == {"runtime_enabled": False, "bypassed": True}
    assert finalized == {
        "action": "bypass",
        "text": exact,
        "runtime_enabled": False,
        "bypassed": True,
    }


def test_mcp_protocol_global_off_does_not_materialize_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch, False)
    reads = 0

    def read_master() -> tuple[dict[str, Any], str]:
        nonlocal reads
        reads += 1
        return _master(False), "dashboard"

    monkeypatch.setattr(runtime_control, "read_enforcement_runtime_control", read_master)
    server = mcp_server.MCPServer()
    server.initialize_responded = True
    server.initialized = True
    monkeypatch.setattr(server, "_runtime_store", _unexpected)

    response = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "agency.preflight",
                "arguments": {"session_id": "session", "user_message": "review this"},
            },
        }
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured == {"runtime_enabled": False, "bypassed": True}
    assert reads == 1
    assert server.store is None


def test_mcp_protocol_global_off_defers_explicit_store_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agency_runtime.core.store.sqlite as sqlite_store

    _set_master(monkeypatch, False)
    monkeypatch.setattr(sqlite_store, "Store", _unexpected)
    server = mcp_server.MCPServer(
        db_path="must-not-open.db",
        config_path="must-not-load.yaml",
    )
    server.initialize_responded = True
    server.initialized = True

    response = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "agency.preflight",
                "arguments": {"session_id": "session", "user_message": "review"},
            },
        }
    )

    assert response is not None
    assert response["result"]["structuredContent"] == {
        "runtime_enabled": False,
        "bypassed": True,
    }
    assert server.store is None


def test_mcp_protocol_global_off_checks_injected_identity_without_config_io(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    import agency_runtime.core.config_binding as config_binding

    _set_master(monkeypatch, False)
    config_path = tmp_path / "agency.yaml"
    db_path = tmp_path / "agency.db"
    store = SimpleNamespace(
        config_path=config_path,
        _configured_config_path=config_path,
        _configured_store_path=db_path,
        _store_path_config_derived=False,
        db_path=db_path,
        _frozen_db_path=db_path,
    )
    monkeypatch.setattr(config_binding, "load_config", _unexpected)
    server = mcp_server.MCPServer(
        store=store,
        db_path=str(db_path),
        config_path=str(config_path),
    )
    server.initialize_responded = True
    server.initialized = True

    response = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "agency.preflight",
                "arguments": {"session_id": "session", "user_message": "review"},
            },
        }
    )

    assert response is not None
    assert response["result"]["structuredContent"] == {
        "runtime_enabled": False,
        "bypassed": True,
    }
    assert server.store is store


def test_http_startup_global_off_defers_config_and_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}
    _set_master(monkeypatch, False)
    monkeypatch.setattr(http_server, "load_config", _unexpected)
    monkeypatch.setattr(http_server, "Store", _unexpected)

    class _Server:
        auth_token = "token"
        server_address = ("127.0.0.1", 7800)

        def __init__(self, store: object, host: str, port: int, **kwargs: Any) -> None:
            observed.update(store=store, host=host, port=port, kwargs=kwargs)

        def serve_forever(self) -> None:
            raise KeyboardInterrupt

        def server_close(self) -> None:
            observed["closed"] = True

    monkeypatch.setattr(http_server, "AgencyHTTPServer", _Server)

    http_server.serve(db_path="must-not-open.db")

    assert observed["store"] is None
    assert observed["host"] == http_server.DEFAULT_HOST
    assert observed["port"] == http_server.DEFAULT_PORT
    assert callable(observed["kwargs"]["store_factory"])
    assert observed["closed"] is True


def test_mcp_global_on_uses_existing_dispatch_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch, True)
    store = object()
    calls: list[tuple[str, dict[str, Any], object]] = []

    def dispatch(name: str, arguments: dict[str, Any], observed_store: object) -> dict[str, Any]:
        calls.append((name, arguments, observed_store))
        return {"ok": True}

    monkeypatch.setattr("agency_runtime.server.mcp_tools.dispatch_tool_call", dispatch)

    assert mcp_server.handle_tool_call("agency.preflight", {"user_message": "x"}, store) == {
        "ok": True
    }
    assert calls == [("agency.preflight", {"user_message": "x"}, store)]


def test_litellm_global_off_preserves_requests_and_records_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch, False)
    monkeypatch.setattr(litellm_callback, "LiteLLMAdapter", _unexpected)
    monkeypatch.setattr(litellm_callback, "inject_message_context", _unexpected)
    monkeypatch.setattr(litellm_callback, "inject_proxy_context", _unexpected)
    callback = AgencyLiteLLMCallback(config=AgencyConfig())
    sdk_kwargs = {"metadata": {"caller": "sdk"}}
    sdk_messages = [{"role": "user", "content": "exact SDK request"}]
    proxy_data = {
        "model": "router-name",
        "messages": [{"role": "user", "content": "exact proxy request"}],
    }

    callback.log_pre_api_call("router-name", sdk_messages, sdk_kwargs)
    sdk_result = asyncio.run(
        callback.async_pre_request_hook("router-name", sdk_messages, sdk_kwargs)
    )
    proxy_result = asyncio.run(
        callback.async_pre_call_hook(None, None, proxy_data, "chat_completion")
    )
    callback.log_success_event(
        {"model": "router-name"},
        {"id": "response", "model": "provider/model"},
        object(),
        object(),
    )

    assert sdk_result is sdk_kwargs
    assert proxy_result is proxy_data
    assert sdk_kwargs == {"metadata": {"caller": "sdk"}}
    assert proxy_data == {
        "model": "router-name",
        "messages": [{"role": "user", "content": "exact proxy request"}],
    }
    assert callback._adapter is None
    assert callback._recorded_events == {}
    assert callback._route_contexts == {}


def test_direct_litellm_adapter_global_off_is_constructor_lazy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch, False)
    monkeypatch.setattr(litellm_callback, "Store", _unexpected)
    monkeypatch.setattr(litellm_callback, "config_for_store", _unexpected)

    adapter = litellm_callback.LiteLLMAdapter()

    assert adapter.is_available() is False
    assert adapter.pre_call_handler("", "", "") is None
    assert adapter._store is None
    assert adapter._config is None


def test_cli_global_direct_write_uses_compare_and_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _master(True)
    updated = _master(False, 8, source="cli")
    observed: list[tuple[bool, int, str]] = []
    monkeypatch.setattr(runtime_control, "read_effective_runtime_control", lambda: current)

    def write(enabled: bool, *, expected_generation: int, source: str) -> dict[str, Any]:
        observed.append((enabled, expected_generation, source))
        return updated

    monkeypatch.setattr(runtime_control, "set_master_enabled", write)
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.dashboard_api_request",
        _unexpected,
    )

    result = install_commands._global_control_result(
        Namespace(native=False, dry_run=False),
        enabled=False,
    )

    assert observed == [(False, 7, "cli")]
    assert result["transport"] == "direct"
    assert result["changed"] is True
    assert result["master"] == updated
    assert result["fresh_session_required"] is True


def test_cli_global_broker_fallback_preserves_cas_and_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _master(True)
    updated = _master(False, 8, source="dashboard")
    calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def unreadable() -> dict[str, Any]:
        raise runtime_control.RuntimeControlSecurityError("restricted token")

    def broker(
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        timeout: float = 2.0,
    ) -> dict[str, Any]:
        calls.append((path, method, payload))
        if path == "/api/runtime":
            assert timeout == 0.25
        return (
            {"master": current}
            if method == "GET"
            else {"ok": True, "changed": True, "master": updated}
        )

    monkeypatch.setattr(runtime_control, "read_effective_runtime_control", unreadable)
    monkeypatch.setattr(
        runtime_control,
        "_restricted_windows_control_target",
        lambda _path: True,
    )
    monkeypatch.setattr(runtime_control, "set_master_enabled", _unexpected)
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.dashboard_api_request",
        broker,
    )

    result = install_commands._global_control_result(
        Namespace(native=False, dry_run=False),
        enabled=False,
    )

    assert calls == [
        ("/api/runtime", "GET", None),
        (
            "/api/runtime/toggle",
            "POST",
            {
                "enabled": False,
                "expected_generation": 7,
                "confirm": "DISABLE AGENCY",
            },
        ),
    ]
    assert result["transport"] == "dashboard"
    assert result["master"] == updated


def test_cli_global_enable_uses_writer_broker_after_effective_direct_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _master(False, 8)
    updated = _master(True, 9, source="dashboard")
    calls: list[tuple[str, str, dict[str, Any] | None]] = []
    monkeypatch.setattr(
        runtime_control,
        "read_effective_runtime_control",
        lambda: current,
    )

    def unwritable(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise runtime_control.RuntimeControlSecurityError("restricted token")

    def broker(
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        calls.append((path, method, payload))
        return {"ok": True, "changed": True, "master": updated}

    monkeypatch.setattr(runtime_control, "set_master_enabled", unwritable)
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.dashboard_api_request",
        broker,
    )

    result = install_commands._global_control_result(
        Namespace(native=False, dry_run=False),
        enabled=True,
    )

    assert calls == [
        (
            "/api/runtime/toggle",
            "POST",
            {
                "enabled": True,
                "expected_generation": 8,
                "confirm": "ENABLE AGENCY",
            },
        )
    ]
    assert result["previous_enabled"] is False
    assert result["enabled"] is True
    assert result["transport"] == "dashboard"


def test_cli_global_cas_conflict_is_not_hidden_by_broker_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runtime_control,
        "read_effective_runtime_control",
        lambda: _master(True),
    )

    def conflict(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise runtime_control.RuntimeControlConflictError("stale generation")

    monkeypatch.setattr(runtime_control, "set_master_enabled", conflict)
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.dashboard_api_request",
        _unexpected,
    )

    with pytest.raises(runtime_control.RuntimeControlConflictError, match="stale generation"):
        install_commands._global_control_result(
            Namespace(native=False, dry_run=False),
            enabled=False,
        )


def test_cli_global_dry_run_and_native_conflict_are_write_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _master(True)
    monkeypatch.setattr(runtime_control, "read_effective_runtime_control", lambda: current)
    monkeypatch.setattr(runtime_control, "set_master_enabled", _unexpected)
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.dashboard_api_request",
        _unexpected,
    )

    preview = install_commands._global_control_result(
        Namespace(native=False, dry_run=True),
        enabled=False,
    )

    assert preview["enabled"] is False
    assert preview["previous_enabled"] is True
    assert preview["changed"] is False
    assert preview["dry_run"] is True
    assert preview["master"] == current
    assert preview["fresh_session_required"] is False
    with pytest.raises(ValueError, match="--global cannot be combined with --native"):
        install_commands._global_control_result(
            Namespace(native=True, dry_run=False),
            enabled=False,
        )


def test_cli_global_command_never_constructs_host_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _master(True)
    emitted: list[dict[str, Any]] = []
    monkeypatch.setattr(runtime_control, "read_effective_runtime_control", lambda: current)
    dependencies = install_commands.InstallDependencies(
        store_factory=_unexpected,
        emit_json=emitted.append,
    )

    exit_code = install_commands.cmd_off(
        Namespace(
            global_control=True,
            native=False,
            dry_run=True,
            json=True,
        ),
        dependencies=dependencies,
    )

    assert exit_code == 0
    assert emitted[0]["scope"] == "global"
    assert emitted[0]["dry_run"] is True


@pytest.mark.parametrize("command", ["on", "off"])
def test_cli_parser_exposes_mutually_exclusive_global_target(command: str) -> None:
    from agency_runtime.cli.main import build_parser

    parsed = build_parser().parse_args([command, "--global", "--json"])
    assert parsed.global_control is True
    assert parsed.agent is None
    with pytest.raises(SystemExit):
        build_parser().parse_args([command, "--global", "--agent", "codex"])


def test_host_status_global_off_overrides_host_and_native_layers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_control, "master_enabled", _unexpected)
    store = SimpleNamespace(
        get_host_control=lambda _host: {
            "enabled": True,
            "updated_at": "now",
            "source": "test",
        }
    )

    status = host_control.inspect_host_status(
        store,
        "codex",
        native_record={"host": "codex", "registered": True, "enabled": True},
        global_enabled=False,
    )

    assert status["runtime_enabled"] is True
    assert status["master_enabled"] is False
    assert status["effective_enabled"] is False


def test_cli_status_passes_brokered_master_state_to_host_inspection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emitted: list[dict[str, Any]] = []
    store = object()
    monkeypatch.setattr(
        install_commands,
        "_read_master_control_with_broker",
        lambda: (_master(False, source="dashboard"), "dashboard"),
    )

    def inspect(
        observed_store: object,
        host: str,
        *,
        global_enabled: bool | None = None,
    ) -> dict[str, Any]:
        assert observed_store is store
        assert global_enabled is False
        return {
            "host": host,
            "runtime_enabled": True,
            "master_enabled": False,
            "effective_enabled": False,
        }

    monkeypatch.setattr(host_control, "inspect_host_status", inspect)
    inference = {
        "schema_version": "agency.dashboard.inference_operations.v1",
        "configured": False,
        "required_for_eligible_turns": False,
        "state": "not_configured",
        "evidence": "configuration readiness plus recent persisted routing/model receipts",
        "provider_chain": [],
        "latest_model_resolution": None,
        "recent_failures": [],
        "failure_count": 0,
        "failures_truncated": False,
    }
    monkeypatch.setattr(
        install_commands,
        "_direct_inference_snapshot",
        lambda _store, _dependencies: inference,
    )
    dependencies = install_commands.InstallDependencies(
        store_factory=lambda _config: store,
        emit_json=emitted.append,
    )

    assert (
        install_commands.cmd_status(
            Namespace(agent="codex", json=True),
            dependencies=dependencies,
        )
        == 0
    )
    assert emitted == [
        {
            "master": _master(False, source="dashboard"),
            "master_transport": "dashboard",
            "hosts": [
                {
                    "host": "codex",
                    "runtime_enabled": True,
                    "master_enabled": False,
                    "effective_enabled": False,
                }
            ],
            "inference": inference,
        }
    ]


def test_cli_delegate_bypasses_before_backend_or_store_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agency_runtime.cli.delegation_commands as delegation_commands

    emitted: list[dict[str, Any]] = []
    _set_master(monkeypatch, False)
    monkeypatch.setattr(delegation_commands, "_store", _unexpected)
    monkeypatch.setattr(delegation_commands, "_print_json", emitted.append)

    assert delegation_commands.cmd_delegate(Namespace(json=True)) == 0
    assert emitted == [
        {
            "status": "bypassed",
            "runtime_enabled": False,
            "bypassed": True,
            "exit_code": 0,
        }
    ]


def test_command_backend_bypasses_before_task_argv_temp_or_process_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.delegation import backend_command

    _set_master(monkeypatch, False)
    monkeypatch.setattr(backend_command, "_run_backend_process", _unexpected)
    monkeypatch.setattr(backend_command.CommandBackend, "_validate_task", _unexpected)
    backend = backend_command.CommandBackend(command=(), name="test")

    result = backend.execute(task=None)  # type: ignore[arg-type]

    assert result["status"] == "bypassed"
    assert result["runtime_enabled"] is False
    assert result["bypassed"] is True
    assert result["exit_code"] == 0
    assert result["command"] == []


def test_lifecycle_bypasses_before_normalization_worktrees_or_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.delegation import lifecycle

    _set_master(monkeypatch, False)
    monkeypatch.setattr(lifecycle, "normalize_work_units", _unexpected)
    monkeypatch.setattr(lifecycle, "provision_worktrees", _unexpected)
    monkeypatch.setattr(lifecycle, "dispatch_work_units", _unexpected)

    result = lifecycle.delegate_with_lifecycle(object(), max_workers=0)

    assert result.runtime_enabled is False
    assert result.bypassed is True
    assert result.work_units == []
    assert result.worktrees == {}
    assert result.dispatch_results == {}
    assert result.errors == []
    assert result.as_dict()["bypassed"] is True
