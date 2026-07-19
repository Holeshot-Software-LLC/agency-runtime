"""Persistent host-control parity across adapters and command surfaces."""

from __future__ import annotations

import json
import sqlite3
from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from agency_runtime.adapters.claude.wrapper import ClaudeAdapter
from agency_runtime.adapters.codex.wrapper import CodexAdapter
from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.cli import main as cli
from agency_runtime.core.host_control import (
    HostControlConflictError,
    handle_host_control_command,
    inspect_host_status,
    set_runtime_control,
)
from agency_runtime.core.store.evidence import MAX_HOST_CONTROL_GENERATION
from agency_runtime.core.store.schema import SCHEMA_VERSION
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
        trace_id="trace-enabled",
    )
    assert restarted_adapter.store.get_skills_for_trace("session-enabled", "trace-enabled") == [
        "agent-reach"
    ]


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
            "expected_generation": 0,
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
            "expected_generation": 1,
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
        trace_id="trace-after-enable",
    )
    assert adapter.store.get_skills_for_trace("same-adapter", "trace-after-enable") == [
        "recorded-after-enable"
    ]


def test_host_command_supports_status_off_and_on_across_store_restarts(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    store = Store(path)

    assert handle_host_control_command("hermes", "status", store=store)["runtime_enabled"] is True
    assert handle_host_control_command("hermes", "off", store=store)["runtime_enabled"] is False
    assert Store(path).get_host_control("hermes")["enabled"] is False
    assert handle_host_control_command("hermes", "on", store=Store(path))["runtime_enabled"] is True
    assert (
        handle_host_control_command(
            "hermes",
            "/agency runtime status",
            store=store,
        )["runtime_enabled"]
        is True
    )
    for invalid in (
        "disable now",
        "agency status!",
        "agency off.",
        "/agency on!",
        "please show agency status",
        "status now",
    ):
        with pytest.raises(ValueError, match="usage"):
            handle_host_control_command("hermes", invalid, store=store)


def test_runtime_control_parser_rejects_non_text_inputs() -> None:
    from agency_runtime.core.runtime_control_command import (
        parse_host_control_arguments,
        parse_runtime_control_command,
    )

    assert parse_runtime_control_command(None) is None
    with pytest.raises(ValueError, match="usage"):
        parse_host_control_arguments(None)


def test_host_control_generation_rejects_stale_writers_and_preserves_noops(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")

    unchanged = set_runtime_control(
        store,
        "codex",
        enabled=True,
        source="test",
        expected_generation=0,
    )
    assert unchanged == {
        "host": "codex",
        "enabled": True,
        "generation": 0,
        "updated_at": None,
        "source": "default",
    }

    disabled = set_runtime_control(
        store,
        "codex",
        enabled=False,
        source="first-writer",
        expected_generation=0,
    )
    assert disabled["generation"] == 1

    with pytest.raises(HostControlConflictError, match="expected 0, found 1"):
        set_runtime_control(
            store,
            "codex",
            enabled=True,
            source="stale-writer",
            expected_generation=0,
        )

    repeated = set_runtime_control(
        store,
        "codex",
        enabled=False,
        source="no-op",
        expected_generation=1,
    )
    assert repeated == disabled
    assert Store(tmp_path / "agency.db").get_host_control("codex") == disabled


def test_host_control_materialization_is_idempotent_and_preserves_existing_state(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "materialized.db")

    first = store.ensure_host_control_materialized("claude", source="installer")
    repeated = store.ensure_host_control_materialized("claude", source="different")

    assert first == repeated
    assert first["enabled"] is True
    assert first["generation"] == 0
    assert first["source"] == "installer"
    disabled = store.set_host_control(
        "claude",
        enabled=False,
        expected_generation=0,
        source="operator",
    )
    assert store.ensure_host_control_materialized("claude") == disabled


def test_host_control_generation_is_atomic_for_two_simultaneous_writers(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    barrier = Barrier(2)

    def disable(source: str) -> str:
        barrier.wait(timeout=5)
        try:
            receipt = set_runtime_control(
                store,
                "codex",
                enabled=False,
                source=source,
                expected_generation=0,
            )
        except HostControlConflictError:
            return "conflict"
        return f"committed:{receipt['generation']}"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(disable, ("writer-a", "writer-b")))

    assert sorted(results) == ["committed:1", "conflict"]
    assert store.get_host_control("codex")["generation"] == 1
    assert store.get_host_control("codex")["enabled"] is False


def test_host_control_validates_types_and_handles_generation_exhaustion(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    for generation in (True, -1, MAX_HOST_CONTROL_GENERATION + 1):
        with pytest.raises(ValueError, match="expected host-control generation is invalid"):
            store.set_host_control(
                "codex",
                enabled=False,
                expected_generation=generation,
            )
    with pytest.raises(ValueError, match="enabled value must be boolean"):
        store.set_host_control("codex", enabled=1, expected_generation=0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="enabled must be a boolean"):
        set_runtime_control(
            store,
            "codex",
            enabled=1,  # type: ignore[arg-type]
            source="test",
            expected_generation=0,
        )

    connection = store._connect()
    try:
        connection.execute(
            "INSERT INTO host_controls (host, enabled, generation, updated_at, source) "
            "VALUES (?, ?, ?, ?, ?)",
            ("codex", 0, MAX_HOST_CONTROL_GENERATION, "max-time", "test"),
        )
        connection.commit()
    finally:
        connection.close()

    unchanged = store.set_host_control(
        "codex",
        enabled=False,
        expected_generation=MAX_HOST_CONTROL_GENERATION,
    )
    assert unchanged["generation"] == MAX_HOST_CONTROL_GENERATION
    with pytest.raises(ValueError, match="generation is exhausted"):
        store.set_host_control(
            "codex",
            enabled=True,
            expected_generation=MAX_HOST_CONTROL_GENERATION,
        )


def test_v20_host_controls_migrate_to_generation_zero_without_state_loss(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy-host-control.db"
    initialized = Store(path)
    connection = initialized._connect()
    try:
        connection.execute("DROP TABLE host_controls")
        connection.execute(
            "CREATE TABLE host_controls (host TEXT PRIMARY KEY, enabled INTEGER NOT NULL, "
            "updated_at TEXT NOT NULL, source TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO host_controls (host, enabled, updated_at, source) "
            "VALUES ('codex', 0, 'legacy-time', 'legacy')"
        )
        connection.execute("DELETE FROM schema_version")
        connection.execute("INSERT INTO schema_version (version) VALUES (20)")
        connection.commit()
    finally:
        connection.close()

    migrated = Store(path)
    assert migrated.get_host_control("codex") == {
        "host": "codex",
        "enabled": False,
        "generation": 0,
        "updated_at": "legacy-time",
        "source": "legacy",
    }
    enabled = set_runtime_control(
        migrated,
        "codex",
        enabled=True,
        source="post-migration",
        expected_generation=0,
    )
    assert enabled["generation"] == 1

    verified = sqlite3.connect(path)
    try:
        columns = {row[1] for row in verified.execute("PRAGMA table_info(host_controls)")}
        version = int(verified.execute("SELECT MAX(version) FROM schema_version").fetchone()[0])
    finally:
        verified.close()
    assert "generation" in columns
    assert version == SCHEMA_VERSION


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
            "managed_plugin_version": "1.0.0",
            "launcher_artifacts_current": True,
        },
    )

    assert status["enabled"] is True
    assert status["runtime_enabled"] is False
    assert status["effective_enabled"] is False
    assert status["execution_capabilities"]["status"] == "native-installation-verified"
    assert status["execution_capabilities"]["execution_host"] == "codex"

    unknown = inspect_host_status(
        store,
        "claude",
        native_record={
            "host": "claude",
            "registered": True,
            "enabled": None,
            "executable_discovered": True,
            "managed_plugin_version": "1.0.0",
            "launcher_artifacts_current": True,
        },
    )
    assert unknown["runtime_enabled"] is True
    assert unknown["effective_enabled"] is None
    assert unknown["execution_capabilities"]["status"] == "native-evidence-unproven"
    assert unknown["execution_capabilities"]["capabilities"] == []


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
        lambda store, host, *, global_enabled=None: {
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
        lambda _store, host, *, global_enabled=None: {
            "host": host,
            "registered": True,
            "enabled": None,
            "runtime_enabled": True,
            "effective_enabled": None,
        },
    )

    assert cli.cmd_status(Namespace(agent="codex", json=False)) == 0
    assert "unverified" in capsys.readouterr().out
