"""Close the remaining branch contracts in small cross-platform helpers."""

from __future__ import annotations

from pathlib import Path
from urllib.request import ProxyHandler, Request

import pytest

from agency_runtime.core.host_control import inspect_all_host_statuses, inspect_host_status
from agency_runtime.core.http_safety import _NoRedirectHandler, open_no_redirect
from agency_runtime.core.process_argv import prepare_process_argv
from agency_runtime.core.provider_validation import _join_api_path
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.mcp import MCP_TOOLS, MCPServer


def test_host_status_accepts_injected_inventory_inspectors(tmp_path: Path) -> None:
    """Callers can inject one stable inventory snapshot without native discovery."""
    store = Store(tmp_path / "agency.db")
    inventory = [
        {
            "host": " CODEX ",
            "registered": True,
            "enabled": True,
            "evidence": ["injected"],
        }
    ]
    inspector_calls = 0

    def inspect() -> list[dict[str, object]]:
        nonlocal inspector_calls
        inspector_calls += 1
        return inventory

    codex = inspect_host_status(store, "codex", inspector=inspect)
    statuses = inspect_all_host_statuses(store, inspector=inspect)

    assert codex["host"] == "codex"
    assert codex["effective_enabled"] is True
    assert codex["evidence"] == ["injected"]
    assert inspector_calls == 2
    assert [status["host"] for status in statuses] == [
        "hermes",
        "openclaw",
        "codex",
        "claude",
    ]
    assert (
        next(status for status in statuses if status["host"] == "codex")["effective_enabled"]
        is True
    )


def test_windows_command_shim_prefers_a_native_executable(tmp_path: Path) -> None:
    """A native companion avoids invoking a shell when both npm shims exist."""
    command_shim = tmp_path / "agent.cmd"
    native_executable = tmp_path / "agent.exe"
    command_shim.write_text("@echo off\n", encoding="utf-8")
    native_executable.write_bytes(b"native")

    assert prepare_process_argv(
        ["agent", "run"],
        platform_name="nt",
        resolver=lambda _name: str(command_shim),
    ) == [str(native_executable), "run"]


def test_provider_api_path_preserves_a_base_without_version_suffix() -> None:
    """Unversioned compatible endpoints receive exactly one requested API path."""
    assert _join_api_path("https://provider.example/", "/v1/models") == (
        "https://provider.example/v1/models"
    )


def test_external_http_requests_keep_proxy_policy_and_block_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only trusted loopback calls bypass proxies; remote calls still reject redirects."""
    captured: list[object] = []
    response = object()

    class Opener:
        def open(self, request: Request, *, timeout: float) -> object:
            assert request.full_url == "https://provider.example/v1/models"
            assert timeout == 1
            return response

    def build_opener(*handlers: object) -> Opener:
        captured.extend(handlers)
        return Opener()

    monkeypatch.setattr(
        "agency_runtime.core.http_safety.urllib.request.build_opener",
        build_opener,
    )

    assert open_no_redirect(Request("https://provider.example/v1/models"), timeout=1) is response
    assert len(captured) == 1
    assert isinstance(captured[0], _NoRedirectHandler)
    assert not any(isinstance(handler, ProxyHandler) for handler in captured)


def test_explain_selection_schema_matches_the_runtime_limit() -> None:
    """MCP clients should reject limits the selector would silently clamp."""
    explain_tool = next(tool for tool in MCP_TOOLS if tool["name"] == "agency.explain_selection")
    assert explain_tool["inputSchema"]["properties"]["limit"]["maximum"] == 50

    server = MCPServer(store=object())
    server.initialized = True
    response = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "agency.explain_selection",
                "arguments": {"task": "inspect routing", "limit": 51},
            },
        }
    )

    assert response is not None
    assert response["result"]["isError"] is True
    assert response["result"]["structuredContent"] == {
        "error": "argument 'limit' exceeds its maximum"
    }
