"""Table-driven contracts for MCP dispatch and CLI transport status."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import agency_runtime.server.mcp as mcp
from agency_runtime.core.cli_transport import inspect_cli_transport
from agency_runtime.core.delegation.backends import BoundedProcessResult
from tests.runtime_support import trusted_test_interpreter

_TRUSTED_CLI = str(trusted_test_interpreter())
_TRUSTED_CLI_DIRECTORY = str(Path(_TRUSTED_CLI).parent)


class _ToolStore:
    db_path = Path("in-memory-agency.db")

    def __init__(self) -> None:
        self.skills: list[tuple[str, str]] = []
        self.delegations: list[dict[str, Any]] = []

    def get_active_roster_as_catalog(self) -> list[dict[str, Any]]:
        return []

    def get_specialist_prompt(self, _slug: str) -> None:
        return None

    def record_skill_loaded(
        self,
        session_id: str,
        skill_name: str,
        *,
        trace_id: str,
    ) -> None:
        assert trace_id == "turn"
        self.skills.append((session_id, skill_name))

    def record_delegation(self, **values: Any) -> str:
        self.delegations.append(values)
        return f"event-{len(self.delegations)}"

    def get_delegations(self, trace_id: str) -> list[dict[str, Any]]:
        return [
            delegation for delegation in self.delegations if delegation.get("trace_id") == trace_id
        ]

    @staticmethod
    def get_run(trace_id: str) -> dict[str, str] | None:
        if trace_id != "turn":
            return None
        return {
            "trace_id": trace_id,
            "session_id": "session",
            "status": "active",
            "preflight_state": "ready",
        }

    def get_active_roster(self) -> list[dict[str, Any]]:
        raise AssertionError("count-only status must not materialize the roster")

    def count_enabled_roster(self) -> int:
        return 0

    @staticmethod
    def get_host_control(host: str) -> dict[str, Any]:
        return {
            "host": host,
            "enabled": True,
            "updated_at": None,
            "source": "default",
        }


@pytest.mark.parametrize(
    ("tool_name", "arguments", "field", "expected"),
    [
        ("agency.search_agents", {"query": "security"}, "agents", []),
        (
            "agency.load_specialist",
            {"slug": "missing", "session_id": "session", "trace_id": "turn"},
            "error",
            "active agent prompt 'missing' not found",
        ),
        (
            "agency.record_skill_loaded",
            {"session_id": "session", "trace_id": "turn", "skill_name": "audit"},
            "status",
            "recorded",
        ),
        ("agency.status", {}, "roster_count", 0),
        ("agency.missing", {}, "error", "unknown tool: agency.missing"),
    ],
)
def test_direct_tool_dispatch_table(
    tool_name: str,
    arguments: dict[str, Any],
    field: str,
    expected: object,
) -> None:
    result = mcp.handle_tool_call(tool_name, arguments, _ToolStore())

    assert result[field] == expected


def _initialize(server: mcp.MCPServer) -> None:
    response = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": "initialize",
            "method": "initialize",
            "params": {
                "protocolVersion": mcp.LATEST_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "table-test", "version": "1"},
            },
        }
    )
    assert response is not None and "result" in response
    assert (
        server.dispatch({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        is None
    )


@pytest.mark.parametrize(
    ("method", "expected_kind", "expected"),
    [
        ("ping", "result", {}),
        ("tools/list", "result", {"tools": mcp.MCP_TOOLS}),
        ("resources/list", "error", -32601),
    ],
)
def test_initialized_request_dispatch_table(
    method: str,
    expected_kind: str,
    expected: object,
) -> None:
    server = mcp.MCPServer(store=_ToolStore())
    _initialize(server)

    response = server.dispatch({"jsonrpc": "2.0", "id": "request", "method": method, "params": {}})

    assert response is not None
    if expected_kind == "result":
        assert response["result"] == expected
    else:
        assert response["error"]["code"] == expected


def _process_result(
    *,
    returncode: int = 0,
    stdout: str = "",
    timed_out: bool = False,
) -> BoundedProcessResult:
    return BoundedProcessResult(
        returncode=returncode,
        stdout=stdout,
        stderr="",
        timed_out=timed_out,
    )


@pytest.mark.parametrize(
    ("scenario", "transport", "expected"),
    [
        ("unsupported", "other", (False, False, False, "unsupported CLI transport")),
        ("bad-timeout", "codex", (False, False, False, "timeout")),
        ("missing", "codex", (False, False, False, "executable not found")),
        ("resolver-error", "codex", (False, False, False, "executable not found")),
        ("auth-error", "codex", (True, False, False, "status command failed")),
        ("auth-timeout", "claude", (True, False, False, "status timed out")),
        ("auth-missing", "codex", (True, False, False, "session not available")),
        ("codex-old", "codex", (True, True, False, "non-interactive controls")),
        ("claude-old", "claude", (True, True, False, "structured-output")),
    ],
)
def test_cli_transport_status_failure_table(
    scenario: str,
    transport: str,
    expected: tuple[bool, bool, bool, str],
) -> None:
    def resolver(_name: str) -> str | None:
        if scenario == "resolver-error":
            raise OSError("private resolver detail")
        return None if scenario == "missing" else _TRUSTED_CLI

    def runner(argv: list[str], **_kwargs: Any) -> BoundedProcessResult:
        is_auth = argv[1:3] in (["login", "status"], ["auth", "status"])
        if is_auth and scenario == "auth-error":
            raise OSError("private account detail")
        if is_auth and scenario == "auth-timeout":
            return _process_result(returncode=124, timed_out=True)
        if is_auth and scenario == "auth-missing":
            return _process_result(returncode=1, stdout="account@example.invalid")
        if scenario == "claude-old":
            return _process_result(stdout="2.1.204")
        return _process_result(stdout="--json")

    timeout = 0 if scenario == "bad-timeout" else 3
    status = inspect_cli_transport(
        transport,
        timeout=timeout,
        resolver=resolver,
        runner=runner,
        environ={"PATH": _TRUSTED_CLI_DIRECTORY},
    )

    installed, authenticated, usable, reason_fragment = expected
    assert (status.installed, status.authenticated, status.usable) == (
        installed,
        authenticated,
        usable,
    )
    assert reason_fragment in status.reason
    assert "private" not in status.reason
    assert "account@example.invalid" not in status.reason
