"""Focused selector, confirmation, and operation-journal tests for uninstall CLI."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.cli import main as cli_main
from agency_runtime.cli import uninstall_commands as subject
from agency_runtime.core.installer_contracts import HOSTS
from agency_runtime.core.prepared_host_uninstall import uninstall_plan_digest


def _args(**changes: Any) -> SimpleNamespace:
    values = {
        "agent": "codex",
        "all": False,
        "confirm_plan": None,
        "dry_run": False,
        "json": True,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def _plan(host: str = "codex") -> dict[str, Any]:
    return {
        "ok": True,
        "complete": True,
        "exit_code": 0,
        "host": host,
        "target": f"C:/Users/test/.agency-runtime/host-plugins/{host}",
        "status": "planned",
        "would_change": True,
        "ownership": {
            "present": True,
            "install_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"install:{host}")),
            "bundle_digest": "a" * 64,
        },
        "inspection": {
            "host": host,
            "managed_plugin_version": "0.1.0",
            "install_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"install:{host}")),
            "bundle_digest": "a" * 64,
        },
        "binding_digest": "b" * 64,
        "native_command_plan": [
            {
                "name": "plugin_unregister",
                "argv": [host, "plugin", "remove", "agency-preflight"],
            }
        ],
    }


def _absent_plan(host: str) -> dict[str, Any]:
    return {
        "ok": True,
        "complete": True,
        "exit_code": 0,
        "host": host,
        "target": f"C:/Users/test/.agency-runtime/host-plugins/{host}",
        "status": "not_installed",
        "would_change": False,
        "ownership": {"present": False},
        "inspection": {
            "host": host,
            "registered": False,
            "managed_plugin_version": None,
            "install_id": None,
            "bundle_digest": None,
        },
        "native_command_plan": [],
    }


def _outcome(host: str) -> dict[str, Any]:
    return {
        "ok": True,
        "complete": True,
        "exit_code": 0,
        "host": host,
        "target": _plan(host)["target"],
        "status": "uninstalled",
        "changed": True,
        "retained_path": f"C:/Users/test/.agency-runtime/backups/{host}/retained",
    }


def test_cli_binds_exact_dry_run_digest_to_selector_before_prepared_apply() -> None:
    emitted: list[dict[str, Any]] = []
    apply_calls: list[dict[str, Any]] = []
    journal_states: list[str] = []
    plan = _plan()

    def apply_prepared(targets: list[str], **kwargs: Any) -> list[dict[str, Any]]:
        apply_calls.append({"targets": targets, **kwargs})
        kwargs["on_authorized"]()
        result = _outcome("codex")
        kwargs["on_result"](result)
        return [result]

    dependencies = subject.UninstallDependencies(
        plan_host=lambda _host: dict(plan),
        apply_prepared=apply_prepared,
        emit_json=emitted.append,
        write_journal=lambda payload: (
            journal_states.append(str(payload["status"])) or "C:/journal.json"
        ),
    )

    assert subject.cmd_uninstall(_args(dry_run=True), dependencies=dependencies) == 0
    dry_run_report = emitted.pop()
    digest = dry_run_report["plan_digest"]
    expected = uninstall_plan_digest([plan], selected_by="agent", targets=["codex"])
    all_selector = uninstall_plan_digest([plan], selected_by="all", targets=["codex"])
    assert digest == expected
    assert digest != all_selector
    assert dry_run_report["selected_by"] == "agent"
    assert dry_run_report["selected_hosts"] == ["codex"]
    assert dry_run_report["inspected_host_count"] == 1
    assert apply_calls == []

    assert (
        subject.cmd_uninstall(
            _args(confirm_plan="0" * 64),
            dependencies=dependencies,
        )
        == 1
    )
    mismatch = emitted.pop()
    assert mismatch["confirmation_required"] is True
    assert "exact plan_digest" in mismatch["error"]
    assert apply_calls == []

    assert subject.cmd_uninstall(_args(confirm_plan=digest), dependencies=dependencies) == 0
    applied = emitted.pop()
    assert applied["ok"] is True
    assert applied["plan_digest"] == digest
    assert "agency-configuration" in applied["preserved"]
    assert len(apply_calls) == 1
    call = apply_calls[0]
    assert call["targets"] == ["codex"]
    assert call["expected_plan_digest"] == digest
    assert call["selected_by"] == "agent"
    assert str(uuid.UUID(call["operation_id"])) == call["operation_id"]
    assert callable(call["on_result"])
    assert journal_states == ["intent_recorded", "applying", "complete"]


def test_cli_journal_callback_failure_stops_later_prepared_host() -> None:
    emitted: list[dict[str, Any]] = []
    applied_hosts: list[str] = []
    journal_writes = 0
    plan_calls: list[str] = []
    plans = {host: _plan(host) for host in ("hermes", "codex")}

    def plan_host(host: str) -> dict[str, Any]:
        plan_calls.append(host)
        return plans.get(host, _absent_plan(host))

    def write_journal(_payload: dict[str, Any]) -> str:
        nonlocal journal_writes
        journal_writes += 1
        if journal_writes == 2:
            raise OSError("journal device unavailable")
        return "C:/journal.json"

    def apply_prepared(
        targets: list[str],
        *,
        on_authorized,
        on_result,
        **_kwargs: Any,
    ) -> list[dict[str, Any]]:
        outcomes: list[dict[str, Any]] = []
        on_authorized()
        for host in targets:
            applied_hosts.append(host)
            result = _outcome(host)
            outcomes.append(result)
            on_result(result)
        return outcomes

    dependencies = subject.UninstallDependencies(
        plan_host=plan_host,
        apply_prepared=apply_prepared,
        emit_json=emitted.append,
        write_journal=write_journal,
    )
    digest = uninstall_plan_digest(
        list(plans.values()),
        selected_by="all",
        targets=list(plans),
    )

    assert (
        subject.cmd_uninstall(
            _args(agent=None, all=True, confirm_plan=digest),
            dependencies=dependencies,
        )
        == 1
    )

    report = emitted.pop()
    assert plan_calls == list(HOSTS)
    assert applied_hosts == ["hermes"]
    assert report["ok"] is False
    assert "journal could not be recorded" in report["error"]
    assert [item["status"] for item in report["hosts"]] == [
        "uninstalled",
        "not_attempted",
    ]
    assert report["hosts"][1]["host"] == "codex"


def test_cli_reports_later_hosts_not_attempted_after_normal_host_failure() -> None:
    emitted: list[dict[str, Any]] = []
    plans = {host: _plan(host) for host in ("hermes", "codex")}

    def plan_host(host: str) -> dict[str, Any]:
        return plans.get(host, _absent_plan(host))

    def apply_prepared(
        _targets: list[str],
        *,
        on_authorized,
        on_result,
        **_kwargs: Any,
    ) -> list[dict[str, Any]]:
        on_authorized()
        failed = {
            **_outcome("hermes"),
            "ok": False,
            "complete": False,
            "status": "partial_failure",
        }
        on_result(failed)
        return [failed]

    dependencies = subject.UninstallDependencies(
        plan_host=plan_host,
        apply_prepared=apply_prepared,
        emit_json=emitted.append,
        write_journal=lambda _payload: "C:/journal.json",
    )
    digest = uninstall_plan_digest(
        list(plans.values()),
        selected_by="all",
        targets=list(plans),
    )

    assert (
        subject.cmd_uninstall(
            _args(agent=None, all=True, confirm_plan=digest),
            dependencies=dependencies,
        )
        == 1
    )

    report = emitted.pop()
    assert [item["status"] for item in report["hosts"]] == [
        "partial_failure",
        "not_attempted",
    ]
    assert report["hosts"][1]["host"] == "codex"
    assert report["hosts"][1]["error"] == "Uninstall stopped after a preceding host failed"


def test_cli_operator_denial_writes_no_intent_journal() -> None:
    emitted: list[dict[str, Any]] = []
    journal_states: list[str] = []
    plan = _plan()

    def deny_before_authority(_targets: list[str], **_kwargs: Any) -> list[dict[str, Any]]:
        raise RuntimeError("operator denied")

    dependencies = subject.UninstallDependencies(
        plan_host=lambda _host: dict(plan),
        apply_prepared=deny_before_authority,
        emit_json=emitted.append,
        write_journal=lambda payload: (
            journal_states.append(str(payload["status"])) or "C:/journal.json"
        ),
    )
    digest = uninstall_plan_digest([plan], selected_by="agent", targets=["codex"])

    assert (
        subject.cmd_uninstall(
            _args(confirm_plan=digest),
            dependencies=dependencies,
        )
        == 1
    )

    report = emitted.pop()
    assert journal_states == []
    assert report["hosts"][0]["status"] == "not_attempted"
    assert "journal_path" not in report


@pytest.mark.parametrize("host", ["hermes", "openclaw", "codex", "claude", "zcode"])
def test_uninstall_parser_accepts_each_host_with_a_valid_plan_digest(host: str) -> None:
    parsed = cli_main.build_parser().parse_args(
        ["uninstall", "--agent", host, "--confirm-plan", "B" * 64, "--json"]
    )

    assert parsed.agent == host
    assert parsed.confirm_plan == "b" * 64
    assert parsed.dry_run is False
    assert parsed.json is True
    assert not any(key.startswith("_operator_presence") for key in vars(parsed))


@pytest.mark.parametrize(
    "argv",
    [
        ["uninstall", "--agent", "codex"],
        ["uninstall", "--dry-run"],
        ["uninstall", "--agent", "codex", "--dry-run", "--confirm-plan", "a" * 64],
    ],
)
def test_uninstall_parser_requires_one_target_and_one_mode(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        cli_main.build_parser().parse_args(argv)
