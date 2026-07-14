from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import installer_orchestration as orchestration
from agency_runtime.core import installer_registration as registration
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.installer_contracts import NativeCommandResult


def _native_result(*, ok: bool = True, stdout: str = "", stderr: str = "") -> NativeCommandResult:
    return NativeCommandResult(("host", "probe"), 0 if ok else 1, stdout, stderr)


def test_plan_facade_and_install_dry_run_delegate_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dispatched: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def dispatch(name: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        dispatched.append((name, args, kwargs))
        return {"ok": True, "dry_run": True}

    monkeypatch.setattr(orchestration, "_dispatch", dispatch)
    assert orchestration._plan_agent_adapter("codex", marker=True)["dry_run"] is True
    assert dispatched == [("plan_agent_adapter", ("codex",), {"marker": True})]

    monkeypatch.setattr(
        orchestration,
        "_plan_agent_adapter",
        lambda *args, **kwargs: {"args": args, "kwargs": kwargs},
    )
    result = orchestration.install_agent_adapter("codex", AgencyConfig(), dry_run=True)
    assert result["args"][0] == "codex"
    assert result["kwargs"]["home_dir"] is None


def test_openclaw_install_guard_allows_only_proven_stopped_gateway(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(orchestration, "_can_execute_native", lambda **_kwargs: False)
    assert (
        orchestration._install_gateway_guard(
            "openclaw",
            "openclaw",
            tmp_path,
            "plugin.json",
            home_dir=tmp_path,
            command_runner=None,
        )
        is None
    )

    monkeypatch.setattr(orchestration, "_can_execute_native", lambda **_kwargs: True)
    monkeypatch.setattr(
        orchestration,
        "_openclaw_gateway_live",
        lambda **_kwargs: (False, _native_result()),
    )
    assert (
        orchestration._install_gateway_guard(
            "openclaw",
            "openclaw",
            tmp_path,
            "plugin.json",
            home_dir=tmp_path,
            command_runner=lambda *_args, **_kwargs: None,
        )
        is None
    )


def _stub_install_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    executable: str | None,
    root_state: tuple[bool, bool, list[str]],
) -> None:
    monkeypatch.setattr(orchestration, "_plugin_target", lambda *_args, **_kwargs: tmp_path / "p")
    monkeypatch.setattr(
        orchestration,
        "_resolve_install_config",
        lambda *_args, **_kwargs: AgencyConfig(),
    )
    monkeypatch.setattr(
        orchestration,
        "_bundle_files",
        lambda *_args, **_kwargs: ({"plugin.json": "{}\n"}, "plugin.json"),
    )
    monkeypatch.setattr(orchestration, "_resolve_binary", lambda *_args: executable)
    monkeypatch.setattr(orchestration, "_root_state", lambda *_args, **_kwargs: root_state)


def test_install_reports_absent_host_and_filesystem_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_install_inputs(
        monkeypatch,
        tmp_path,
        executable=None,
        root_state=(False, False, []),
    )
    absent = orchestration.install_agent_adapter("codex", home_dir=tmp_path)
    assert absent == {
        "ok": False,
        "exit_code": 2,
        "error": "codex is not installed on this machine",
        "host": "codex",
    }

    _stub_install_inputs(
        monkeypatch,
        tmp_path,
        executable="codex",
        root_state=(True, True, []),
    )

    def fail_install(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise OSError("injected staging failure")

    monkeypatch.setattr(orchestration, "_atomic_install_tree", fail_install)
    failed = orchestration.install_agent_adapter("codex", home_dir=tmp_path)
    assert failed["failed_step"] == "filesystem"
    assert failed["partial"] is False
    assert failed["error"] == "OSError: injected staging failure"


def test_rollback_backup_resolution_selects_only_owned_candidates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    backup_root = tmp_path / "backups"

    selected, version, error = orchestration._resolve_rollback_backup(
        "codex", target, backup_root, None
    )
    assert (selected, version) == (None, None)
    assert error == "No valid retained backup found for codex"

    old = backup_root / "2026-01-01"
    new = backup_root / "2026-02-01"
    old.mkdir(parents=True)
    new.mkdir()

    def validate(path: Path, **_kwargs: Any) -> tuple[bool, str | None, str | None]:
        return (True, None, "0.1.0") if path.name == old.name else (False, "unowned", None)

    monkeypatch.setattr(orchestration, "_validate_owned_backup", validate)
    selected, version, error = orchestration._resolve_rollback_backup(
        "codex", target, backup_root, None
    )
    assert selected == old.resolve()
    assert version == "0.1.0"
    assert error is None

    outside = tmp_path / "outside"
    outside.mkdir()
    selected, version, error = orchestration._resolve_rollback_backup(
        "codex", target, backup_root, outside
    )
    assert (selected, version) == (None, None)
    assert "inside the managed backup root" in str(error)


def test_openclaw_rollback_guard_reports_each_unproven_boundary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    selected = tmp_path / "backup"
    target = tmp_path / "target"

    missing_binary = orchestration._rollback_gateway_guard(
        "openclaw",
        None,
        target,
        selected,
        home_dir=tmp_path,
        command_runner=None,
    )
    assert missing_binary is not None
    assert "executable is unavailable" in missing_binary["native_steps"][0]["error"]

    monkeypatch.setattr(orchestration, "_can_execute_native", lambda **_kwargs: False)
    suppressed = orchestration._rollback_gateway_guard(
        "openclaw",
        "openclaw",
        target,
        selected,
        home_dir=tmp_path,
        command_runner=None,
    )
    assert suppressed is not None
    assert "suppresses" in suppressed["native_steps"][0]["error"]

    monkeypatch.setattr(orchestration, "_can_execute_native", lambda **_kwargs: True)
    monkeypatch.setattr(
        orchestration,
        "_openclaw_gateway_live",
        lambda **_kwargs: (False, _native_result()),
    )
    assert (
        orchestration._rollback_gateway_guard(
            "openclaw",
            "openclaw",
            target,
            selected,
            home_dir=tmp_path,
            command_runner=lambda *_args, **_kwargs: None,
        )
        is None
    )


def test_rollback_replacement_restores_displaced_target_after_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    selected = tmp_path / "selected"
    target.mkdir()
    selected.mkdir()
    sentinel = target / "sentinel.txt"
    sentinel.write_text("original", encoding="utf-8")
    real_replace = os.replace

    monkeypatch.setattr(orchestration, "_runtime_home", lambda **_kwargs: tmp_path / "runtime")
    monkeypatch.setattr(orchestration, "_utc_stamp", lambda: "stable-stamp")

    def fail_selected_replace(
        source: str | os.PathLike[str], destination: str | os.PathLike[str]
    ) -> None:
        if Path(source) == selected:
            raise OSError("injected restore failure")
        real_replace(source, destination)

    monkeypatch.setattr(orchestration.os, "replace", fail_selected_replace)
    displaced, error = orchestration._replace_with_backup(
        "codex",
        target,
        selected,
        home_dir=tmp_path,
    )

    assert displaced is None
    assert error == {"ok": False, "exit_code": 1, "error": "OSError: injected restore failure"}
    assert sentinel.read_text(encoding="utf-8") == "original"
    assert selected.exists()


def test_rollback_replacement_handles_absent_target_and_absent_backup(tmp_path: Path) -> None:
    target = tmp_path / "target"
    selected = tmp_path / "selected"
    selected.mkdir()

    displaced, error = orchestration._replace_with_backup(
        "codex",
        target,
        selected,
        home_dir=tmp_path,
    )
    assert displaced is None
    assert error is None
    assert target.is_dir()

    missing = tmp_path / "missing"
    second_target = tmp_path / "second-target"
    displaced, error = orchestration._replace_with_backup(
        "codex",
        second_target,
        missing,
        home_dir=tmp_path,
    )
    assert displaced is None
    assert error is not None
    assert error["exit_code"] == 1
    assert "FileNotFoundError" in error["error"]


def test_rollback_surfaces_replacement_and_native_refresh_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    selected = tmp_path / "selected"
    selected.mkdir()
    monkeypatch.setattr(orchestration, "_plugin_target", lambda *_args, **_kwargs: target)
    monkeypatch.setattr(orchestration, "_runtime_home", lambda **_kwargs: tmp_path / "runtime")
    monkeypatch.setattr(
        orchestration,
        "_resolve_rollback_backup",
        lambda *_args, **_kwargs: (selected, "0.1.0", None),
    )
    monkeypatch.setattr(orchestration, "_resolve_binary", lambda *_args: None)
    monkeypatch.setattr(
        orchestration,
        "_replace_with_backup",
        lambda *_args, **_kwargs: (
            None,
            {"ok": False, "exit_code": 1, "error": "replacement blocked"},
        ),
    )
    assert orchestration.rollback_agent_adapter("codex")["error"] == "replacement blocked"

    result = {"ok": True, "exit_code": 0}
    monkeypatch.setattr(orchestration, "_can_execute_native", lambda **_kwargs: True)
    monkeypatch.setattr(
        orchestration,
        "_native_registration_steps",
        lambda *_args, **_kwargs: ([{"name": "enable", "ok": False}], False, "enable"),
    )
    refreshed = orchestration._refresh_rollback_registration(
        result,
        "codex",
        target,
        "codex",
        home_dir=tmp_path,
        command_runner=lambda *_args, **_kwargs: None,
    )
    assert refreshed["ok"] is False
    assert refreshed["partial"] is True
    assert refreshed["failed_step"] == "enable"
    assert refreshed["maturity"] == "filesystem-restored-native-refresh-incomplete"


def test_toggle_verification_and_errors_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed_native = _native_result(ok=False)
    assert (
        orchestration._verify_toggle(
            "codex",
            True,
            failed_native,
            home_dir=None,
            command_runner=None,
        )
        == orchestration._ToggleVerification()
    )
    assert (
        orchestration._toggle_error(
            "codex", True, failed_native, orchestration._ToggleVerification()
        )
        == "native toggle failed"
    )

    failed_inventory = _native_result(ok=False, stderr="inventory unavailable")
    monkeypatch.setattr(orchestration, "_inventory_command", lambda _host: ["host", "list"])
    monkeypatch.setattr(orchestration, "_run_native", lambda *_args, **_kwargs: failed_inventory)
    verification = orchestration._verify_toggle(
        "codex",
        True,
        _native_result(),
        home_dir=None,
        command_runner=None,
    )
    assert verification.inventory is failed_inventory
    assert orchestration._toggle_error("codex", True, _native_result(), verification) == (
        "inventory unavailable"
    )
    assert (
        orchestration._toggle_error(
            "codex",
            True,
            _native_result(),
            orchestration._ToggleVerification(),
        )
        == "native toggle inventory verification failed"
    )


def test_toggle_entrypoint_reports_missing_binary_dry_run_and_test_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(orchestration, "_resolve_binary", lambda *_args: None)
    missing = orchestration.toggle_agency("codex", True)
    assert missing["exit_code"] == 2
    assert missing["error"] == "codex executable is not available"

    monkeypatch.setattr(orchestration, "_resolve_binary", lambda *_args: "codex")
    planned = orchestration.toggle_agency("codex", False, dry_run=True)
    assert planned["ok"] is True
    assert planned["dry_run"] is True
    assert planned["command"][2] == "remove"

    monkeypatch.setattr(orchestration, "_can_execute_native", lambda **_kwargs: False)
    blocked = orchestration.toggle_agency("codex", True)
    assert blocked["exit_code"] == 2
    assert "requires an injected command_runner" in blocked["error"]


def test_native_command_plans_cover_every_supported_host(tmp_path: Path) -> None:
    hermes = registration.native_command_plan("hermes", tmp_path)
    assert [step["name"] for step in hermes] == ["enable", "inventory"]

    openclaw = registration.native_command_plan("openclaw", tmp_path)
    assert openclaw[0]["kind"] == "safety_gate"
    assert openclaw[3]["argv"][-1] == "--force"

    codex = registration.native_command_plan("codex", tmp_path)
    assert "plugin_add" in {step["name"] for step in codex}
    assert codex[2]["argv"][-1] == "--json"

    claude = registration.native_command_plan("claude", tmp_path)
    assert "plugin_install" in {step["name"] for step in claude}
    assert "enable" in {step["name"] for step in claude}
    assert "--scope" in claude[2]["argv"]


def _stub_registration_plan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    executable: str | None,
) -> None:
    target = tmp_path / "plugin"
    monkeypatch.setattr(registration, "_plugin_target", lambda *_args, **_kwargs: target)
    monkeypatch.setattr(
        registration,
        "_resolve_install_config",
        lambda *_args, **_kwargs: AgencyConfig(),
    )
    monkeypatch.setattr(
        registration,
        "_bundle_files",
        lambda *_args, **_kwargs: ({"plugin.json": "{}\n"}, "plugin.json"),
    )
    monkeypatch.setattr(registration, "_resolve_binary", lambda *_args: executable)
    monkeypatch.setattr(
        registration,
        "_root_state",
        lambda *_args, **_kwargs: (True, True, ["marker"]),
    )
    monkeypatch.setattr(
        registration,
        "_atomic_install_tree",
        lambda *_args, **_kwargs: {"unchanged": True},
    )
    monkeypatch.setattr(
        registration,
        "_native_command_plan",
        lambda host, path: registration.native_command_plan(host, path),
    )
    monkeypatch.setattr(registration, "_host_root", lambda *_args, **_kwargs: tmp_path / "root")


def test_registration_plan_rejects_unknown_and_gates_openclaw_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    assert registration.plan_agent_adapter("unknown")["exit_code"] == 2

    _stub_registration_plan(monkeypatch, tmp_path, executable="openclaw")
    monkeypatch.setattr(registration, "_can_execute_native", lambda **_kwargs: True)
    monkeypatch.setattr(
        registration,
        "_openclaw_gateway_live",
        lambda **_kwargs: (True, _native_result()),
    )
    live = registration.plan_agent_adapter(
        "openclaw",
        home_dir=tmp_path,
        command_runner=lambda *_args, **_kwargs: None,
    )
    assert live["ok"] is False
    assert live["exit_code"] == 1
    assert live["gateway_safety_gate"]["state"] == "live"

    monkeypatch.setattr(registration, "_can_execute_native", lambda **_kwargs: False)
    unprobed = registration.plan_agent_adapter("openclaw", home_dir=tmp_path)
    assert unprobed["ok"] is True
    assert unprobed["gateway_safety_gate"]["state"] == "unprobed"
    assert unprobed["gateway_safety_gate"]["safe_to_mutate"] is None
