"""Focused contracts for the end-to-end guided setup command."""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.cli import setup_commands as subject


def _args(**overrides: Any) -> argparse.Namespace:
    values = {
        "non_interactive": False,
        "profile": None,
        "force_config": False,
        "all": False,
        "agent": None,
        "skip_install": False,
        "no_dashboard": False,
        "skip_smoke": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _command(
    calls: list[tuple[str, dict[str, Any]]],
    name: str,
    result: int,
):
    def run(args: argparse.Namespace) -> int:
        calls.append((name, vars(args).copy()))
        return result

    return run


def _dependencies(
    path: Path,
    calls: list[tuple[str, dict[str, Any]]],
    *,
    prompts: Iterator[str] | None = None,
    configure: int = 0,
    validate: int = 0,
    install: int = 0,
    dashboard: int = 0,
    doctor: int = 0,
    smoke: int = 0,
    detected: list[str] | None = None,
) -> subject.SetupDependencies:
    responses = prompts if prompts is not None else iter(())
    return subject.SetupDependencies(
        resolve_config_path=lambda: path,
        configure=_command(calls, "configure", configure),
        validate=_command(calls, "validate", validate),
        install=_command(calls, "install", install),
        dashboard_service=_command(calls, "dashboard", dashboard),
        doctor=_command(calls, "doctor", doctor),
        smoke=_command(calls, "smoke", smoke),
        detect_hosts=lambda: list(detected or []),
        prompt=lambda _message: next(responses),
    )


def test_interactive_setup_composes_config_install_doctor_and_smoke(tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    dependencies = _dependencies(
        tmp_path / "agency.yaml",
        calls,
        prompts=iter(("", "", "")),
        detected=["codex", "claude"],
    )

    assert subject.cmd_setup(_args(), dependencies=dependencies) == 0

    assert [name for name, _args in calls] == [
        "configure",
        "validate",
        "install",
        "doctor",
        "smoke",
    ]
    configure_args = calls[0][1]
    assert configure_args == {"non_interactive": False, "profile": None, "force": False}
    install_args = calls[2][1]
    assert install_args["all"] is True
    assert install_args["agent"] is None
    assert install_args["no_dashboard"] is False
    assert install_args["verify_activation"] is False
    assert install_args["_setup_accept_activation_pending"] is True
    assert calls[4][1] == {"all": True, "agent": None, "json": False}


def test_existing_config_is_retained_and_degraded_doctor_is_truthful(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text("profile: standard\n", encoding="utf-8")
    calls: list[tuple[str, dict[str, Any]]] = []
    dependencies = _dependencies(
        path,
        calls,
        prompts=iter(("",)),
        validate=2,
        doctor=2,
    )

    assert (
        subject.cmd_setup(
            _args(skip_install=True, skip_smoke=True),
            dependencies=dependencies,
        )
        == 2
    )
    assert [name for name, _args in calls] == ["validate", "doctor"]


def test_existing_config_replacement_is_explicit_and_uses_guarded_force(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text("profile: standard\n", encoding="utf-8")
    calls: list[tuple[str, dict[str, Any]]] = []
    dependencies = _dependencies(path, calls, prompts=iter(("n",)))

    assert (
        subject.cmd_setup(
            _args(skip_install=True, skip_smoke=True),
            dependencies=dependencies,
        )
        == 0
    )
    assert calls[0] == (
        "configure",
        {"non_interactive": False, "profile": None, "force": True},
    )


def test_dashboard_only_setup_uses_dashboard_service_without_host_install(tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    dependencies = _dependencies(
        tmp_path / "agency.yaml",
        calls,
        prompts=iter(("3", "", "n")),
        detected=["codex"],
    )

    assert subject.cmd_setup(_args(), dependencies=dependencies) == 0
    assert [name for name, _args in calls] == [
        "configure",
        "validate",
        "dashboard",
        "doctor",
    ]
    assert calls[2][1]["dashboard_service_action"] == "install"


def test_one_host_setup_scopes_install_and_smoke_without_dashboard(tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    dependencies = _dependencies(
        tmp_path / "agency.yaml",
        calls,
        prompts=iter(("2", "3", "n", "")),
        detected=["codex", "claude"],
    )

    assert subject.cmd_setup(_args(), dependencies=dependencies) == 0
    install_args = next(value for name, value in calls if name == "install")
    smoke_args = next(value for name, value in calls if name == "smoke")
    assert install_args["all"] is False
    assert install_args["agent"] == "codex"
    assert install_args["no_dashboard"] is True
    assert smoke_args == {"all": False, "agent": "codex", "json": False}


def test_non_interactive_setup_requires_explicit_install_scope(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires an explicit --all"):
        subject.cmd_setup(
            _args(non_interactive=True),
            dependencies=_dependencies(tmp_path / "agency.yaml", []),
        )


def test_install_failure_runs_read_only_doctor_but_not_smoke(tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    dependencies = _dependencies(
        tmp_path / "agency.yaml",
        calls,
        install=1,
        doctor=2,
    )

    assert (
        subject.cmd_setup(
            _args(non_interactive=True, all=True),
            dependencies=dependencies,
        )
        == 1
    )
    assert [name for name, _args in calls] == [
        "configure",
        "validate",
        "install",
        "doctor",
    ]


def test_attended_codex_activation_pending_is_degraded_and_smoke_can_run(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    dependencies = _dependencies(
        tmp_path / "agency.yaml",
        calls,
        install=2,
        doctor=2,
    )

    assert (
        subject.cmd_setup(
            _args(non_interactive=True, all=True),
            dependencies=dependencies,
        )
        == 2
    )
    assert [name for name, _args in calls] == [
        "configure",
        "validate",
        "install",
        "doctor",
        "smoke",
    ]
    assert "installation     activation-pending" in capsys.readouterr().out


def test_any_degraded_setup_stage_is_preserved_in_final_exit_code(tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    dependencies = _dependencies(
        tmp_path / "agency.yaml",
        calls,
        validate=2,
        doctor=0,
    )

    assert (
        subject.cmd_setup(
            _args(non_interactive=True, skip_install=True, skip_smoke=True),
            dependencies=dependencies,
        )
        == 2
    )


def test_validation_failure_stops_before_any_install_mutation(tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    dependencies = _dependencies(tmp_path / "agency.yaml", calls, validate=1)

    assert (
        subject.cmd_setup(
            _args(non_interactive=True, all=True),
            dependencies=dependencies,
        )
        == 1
    )
    assert [name for name, _args in calls] == ["configure", "validate"]


def test_interactive_eof_becomes_actionable_controlled_error(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text("profile: standard\n", encoding="utf-8")

    def eof(_message: str) -> str:
        raise EOFError

    dependencies = _dependencies(path, [], prompts=iter(()))
    dependencies = replace(dependencies, prompt=eof)
    with pytest.raises(ValueError, match="interactive setup requires terminal input"):
        subject.cmd_setup(_args(), dependencies=dependencies)


def test_main_facade_supplies_its_patchable_command_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.cli import main

    configure = lambda _args: 11  # noqa: E731
    dashboard = lambda _args: 12  # noqa: E731
    monkeypatch.setattr(main, "cmd_configure", configure)
    monkeypatch.setattr(main, "cmd_dashboard_service", dashboard)

    def setup(
        args: argparse.Namespace,
        *,
        dependencies: subject.SetupDependencies,
    ) -> int:
        assert args is marker
        assert dependencies.configure is configure
        assert dependencies.dashboard_service is dashboard
        assert dependencies.install is main.cmd_install
        assert dependencies.validate is main.cmd_config_validate
        assert dependencies.doctor is main.cmd_doctor
        assert dependencies.smoke is main.cmd_smoke
        return 7

    marker = _args()
    monkeypatch.setattr(main._setup, "cmd_setup", setup)
    assert main.cmd_setup(marker) == 7
