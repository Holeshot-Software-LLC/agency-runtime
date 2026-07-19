"""Regression tests for protocol work that must remain behind global off."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest

import agency_runtime.adapters.hermes.bridge as hermes_bridge
import agency_runtime.adapters.hooks as hook_module
import agency_runtime.core.runtime_control as runtime_control
import agency_runtime.server.mcp as mcp_server


def _unexpected(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("off-mode boundary performed Agency work")


def _disable_master(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime_control, "master_enabled", lambda: False)
    monkeypatch.setattr(
        runtime_control,
        "read_enforcement_runtime_control",
        lambda: (_disabled_master(), "test"),
    )


def _disabled_master() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "enabled": False,
        "generation": 8,
        "updated_at": "2026-07-16T12:00:00Z",
        "source": "test",
    }


def _initialized_mcp_server() -> mcp_server.MCPServer:
    server = mcp_server.MCPServer()
    server.initialize_responded = True
    server.initialized = True
    return server


def _mcp_call(
    server: mcp_server.MCPServer,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    response = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )
    assert response is not None
    return response["result"]["structuredContent"]


def test_mcp_status_global_off_is_store_free_for_direct_and_protocol_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_master(monkeypatch)
    monkeypatch.setattr(
        runtime_control,
        "read_effective_runtime_control",
        _disabled_master,
    )
    monkeypatch.setattr("agency_runtime.core.store.sqlite.Store", _unexpected)
    monkeypatch.setattr("agency_runtime.server.mcp_tools.dispatch_tool_call", _unexpected)
    server = _initialized_mcp_server()
    monkeypatch.setattr(server, "_runtime_store", _unexpected)

    expected = {
        "runtime_enabled": False,
        "bypassed": True,
        "master": _disabled_master(),
    }
    assert mcp_server.handle_tool_call("agency.status", {}) == expected
    assert _mcp_call(server, "agency.status", {}) == expected
    assert server.store is None


@pytest.mark.parametrize(
    ("name", "arguments", "expected"),
    [
        (
            "agency.finalize",
            {"draft_text": "  exact draft\nunchanged  "},
            {
                "action": "bypass",
                "text": "  exact draft\nunchanged  ",
                "runtime_enabled": False,
                "bypassed": True,
            },
        ),
        ("agency.preflight", {}, {"runtime_enabled": False, "bypassed": True}),
        ("agency.delegate", {}, {"runtime_enabled": False, "bypassed": True}),
    ],
)
def test_mcp_protocol_global_off_precedes_normal_tool_schema_validation(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    arguments: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    _disable_master(monkeypatch)
    server = _initialized_mcp_server()
    monkeypatch.setattr(server, "_runtime_store", _unexpected)

    assert _mcp_call(server, name, arguments) == expected
    assert server.store is None


@pytest.mark.parametrize(
    "raw",
    [
        b"{not-json",
        b"{}",
        b"x" * (hook_module.MAX_HOOK_INPUT_BYTES + 1),
    ],
    ids=["malformed-json", "mismatched-event", "oversized"],
)
def test_native_stop_global_off_bypasses_before_envelope_failure_policy(
    monkeypatch: pytest.MonkeyPatch,
    raw: bytes,
) -> None:
    _disable_master(monkeypatch)
    monkeypatch.setattr(hook_module, "HookBridge", _unexpected)
    monkeypatch.setattr(hook_module, "Store", _unexpected)
    output = io.BytesIO()
    errors = io.StringIO()

    assert (
        hook_module.run_hook_stdio(
            "codex",
            db_path="must-not-open.db",
            config_path="must-not-load.yaml",
            expected_event="Stop",
            input_stream=io.BytesIO(raw),
            output_stream=output,
            error_stream=errors,
        )
        == 0
    )
    assert json.loads(output.getvalue()) == {}
    assert errors.getvalue() == ""


class _BinarySink:
    def __init__(self) -> None:
        self.buffer = io.BytesIO()


def test_hermes_installed_main_global_off_skips_config_and_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_master(monkeypatch)
    exact = "  exact Hermes response\nunchanged  "
    sink = _BinarySink()
    monkeypatch.setattr(hermes_bridge.sys, "stdout", sink)
    monkeypatch.setattr(
        hermes_bridge,
        "_read_payload",
        lambda: {"action": "transform_llm_output", "response_text": exact},
    )
    monkeypatch.setattr(hermes_bridge, "_config_path", _unexpected)
    monkeypatch.setattr(hermes_bridge, "_adapter", _unexpected)

    assert hermes_bridge.main(["--config", "must-not-load.yaml"]) == 0
    assert json.loads(sink.buffer.getvalue()) == {"ok": True, "result": exact}
