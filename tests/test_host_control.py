"""Persistent host-control parity across adapters and command surfaces."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from agency_runtime.adapters.claude.wrapper import ClaudeAdapter
from agency_runtime.adapters.codex.wrapper import CodexAdapter
from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.cli import main as cli
from agency_runtime.core.host_control import (
    handle_host_control_command,
    inspect_host_status,
    set_runtime_control,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.mcp import handle_tool_call

HOST_ADAPTERS = [HermesAdapter, OpenClawAdapter, CodexAdapter, ClaudeAdapter]


def _non_control_counts(store: Store) -> dict[str, int]:
    return {
        table: count
        for table, count in store.runtime_table_counts().items()
        if table not in {"host_controls"}
    }


@pytest.mark.parametrize("adapter_cls", HOST_ADAPTERS)
def test_disabled_host_short_circuits_every_adapter_boundary_and_persists(
    adapter_cls: type,
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    store = Store(path)
    set_runtime_control(
        store,
        adapter_cls.host_name,
        enabled=False,
        source="test",
    )
    before = _non_control_counts(store)
    adapter = adapter_cls(store=store)
    draft = "Unmodified response."

    assert adapter.build_preflight_context("session-disabled", "Review this design") is None
    adapter.post_tool_call_handler(
        tool_name="skill_view",
        args={"name": "agent-reach"},
        session_id="session-disabled",
    )
    adapter.post_api_request_handler(
        response={"model": "provider/model"},
        trace_id="trace-disabled",
        session_id="session-disabled",
    )
    assert adapter.apply_finalization(draft, "trace-disabled") == draft
    assert adapter.enforce_pre_verify(draft, "session-disabled") is None
    assert _non_control_counts(store) == before

    reopened = Store(path)
    assert reopened.get_host_control(adapter_cls.host_name)["enabled"] is False
    set_runtime_control(
        reopened,
        adapter_cls.host_name,
        enabled=True,
        source="test-restart",
    )
    restarted_adapter = adapter_cls(store=Store(path))
    restarted_adapter.post_tool_call_handler(
        tool_name="skill_view",
        args={"name": "agent-reach"},
        session_id="session-enabled",
    )
    assert restarted_adapter.report_skills_loaded("session-enabled") == ["agent-reach"]


@pytest.mark.parametrize("adapter_cls", HOST_ADAPTERS)
def test_same_adapter_observes_mcp_off_status_on_at_successive_boundaries(
    adapter_cls: type,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    adapter = adapter_cls(store=store)
    host = adapter_cls.host_name
    monkeypatch.setattr(
        "agency_runtime.core.host_control.inspect_host_status",
        lambda runtime_store, requested_host: {
            "host": requested_host,
            "registered": True,
            "enabled": True,
            "runtime_enabled": runtime_store.get_host_control(requested_host)["enabled"],
            "effective_enabled": runtime_store.get_host_control(requested_host)["enabled"],
        },
    )

    disabled = handle_tool_call(
        "agency.host_control",
        {
            "host": host,
            "enabled": False,
            "confirm": f"DISABLE {host}",
        },
        store=store,
    )
    assert disabled["ok"] is True
    assert disabled["enabled"] is False
    before = _non_control_counts(store)
    adapter.post_tool_call_handler(
        tool_name="skill_view",
        args={"name": "ignored-while-disabled"},
        session_id="same-adapter",
    )
    assert _non_control_counts(store) == before

    status = handle_tool_call(
        "agency.host_status",
        {"host": host},
        store=store,
    )
    assert status["runtime_enabled"] is False
    enabled = handle_tool_call(
        "agency.host_control",
        {
            "host": host,
            "enabled": True,
            "confirm": f"ENABLE {host}",
        },
        store=store,
    )
    assert enabled["ok"] is True
    assert enabled["enabled"] is True
    adapter.post_tool_call_handler(
        tool_name="skill_view",
        args={"name": "recorded-after-enable"},
        session_id="same-adapter",
    )
    assert adapter.report_skills_loaded("same-adapter") == ["recorded-after-enable"]


def test_host_command_supports_status_off_and_on_across_store_restarts(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    store = Store(path)

    assert handle_host_control_command("hermes", "status", store=store)["runtime_enabled"] is True
    assert handle_host_control_command("hermes", "off", store=store)["runtime_enabled"] is False
    assert Store(path).get_host_control("hermes")["enabled"] is False
    assert handle_host_control_command("hermes", "on", store=Store(path))["runtime_enabled"] is True
    with pytest.raises(ValueError, match="usage"):
        handle_host_control_command("hermes", "disable now", store=store)


def test_host_status_separates_native_and_soft_control(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    set_runtime_control(store, "codex", enabled=False, source="test")
    status = inspect_host_status(
        store,
        "codex",
        native_record={
            "host": "codex",
            "registered": True,
            "enabled": True,
            "executable_discovered": True,
        },
    )

    assert status["enabled"] is True
    assert status["runtime_enabled"] is False
    assert status["effective_enabled"] is False

    unknown = inspect_host_status(
        store,
        "claude",
        native_record={
            "host": "claude",
            "registered": True,
            "enabled": None,
            "executable_discovered": True,
        },
    )
    assert unknown["runtime_enabled"] is True
    assert unknown["effective_enabled"] is None


def test_cli_soft_control_and_status_share_persistent_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(path))
    common = {"agent": "codex", "dry_run": False, "json": True, "native": False}

    assert cli.cmd_off(Namespace(**common)) == 0
    disabled = json.loads(capsys.readouterr().out)
    assert disabled["runtime_enabled"] is False
    assert Store(path).get_host_control("codex")["enabled"] is False

    monkeypatch.setattr(
        "agency_runtime.core.host_control.inspect_host_status",
        lambda store, host: {
            "host": host,
            "registered": True,
            "enabled": True,
            "runtime_enabled": store.get_host_control(host)["enabled"],
            "effective_enabled": False,
        },
    )
    assert cli.cmd_status(Namespace(agent="codex", json=True)) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["hosts"][0]["runtime_enabled"] is False

    assert cli.cmd_on(Namespace(**common)) == 0
    enabled = json.loads(capsys.readouterr().out)
    assert enabled["runtime_enabled"] is True
    assert Store(path).get_host_control("codex")["enabled"] is True


def test_cli_human_status_renders_unknown_effective_state_as_unverified(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "agency.db"))
    monkeypatch.setattr(
        "agency_runtime.core.host_control.inspect_host_status",
        lambda _store, host: {
            "host": host,
            "registered": True,
            "enabled": None,
            "runtime_enabled": True,
            "effective_enabled": None,
        },
    )

    assert cli.cmd_status(Namespace(agent="codex", json=False)) == 0
    assert "unverified" in capsys.readouterr().out
