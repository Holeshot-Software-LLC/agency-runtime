"""End-to-end first-run setup composed from guarded owner commands."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from agency_runtime.core.configuration import resolve_config_path
from agency_runtime.core.installer import detect_installed_agents
from agency_runtime.core.installer_contracts import HOSTS

from .config_commands import cmd_config_validate, cmd_configure, cmd_doctor
from .install_commands import cmd_install
from .roster_commands import cmd_smoke
from .service_commands import cmd_dashboard_service

_DIAGNOSTIC_RESULTS = frozenset({0, 2})


@dataclass(frozen=True, slots=True)
class SetupDependencies:
    """Patchable setup stage and prompt boundaries."""

    resolve_config_path: Callable[[], Path] = resolve_config_path
    configure: Callable[[argparse.Namespace], int] = cmd_configure
    validate: Callable[[argparse.Namespace], int] = cmd_config_validate
    install: Callable[[argparse.Namespace], int] = cmd_install
    dashboard_service: Callable[[argparse.Namespace], int] = cmd_dashboard_service
    doctor: Callable[[argparse.Namespace], int] = cmd_doctor
    smoke: Callable[[argparse.Namespace], int] = cmd_smoke
    detect_hosts: Callable[[], list[str]] = detect_installed_agents
    prompt: Callable[[str], str] = input


DEFAULT_DEPENDENCIES = SetupDependencies()


@dataclass(frozen=True, slots=True)
class InstallSelection:
    """One bounded setup install choice."""

    mode: str
    host: str | None
    dashboard: bool


def _input(prompt: str, dependencies: SetupDependencies) -> str:
    try:
        return dependencies.prompt(prompt)
    except EOFError as exc:
        raise ValueError(
            "interactive setup requires terminal input; rerun with --non-interactive "
            "and an explicit --all, --agent, or --skip-install choice"
        ) from exc


def _confirm(
    prompt: str,
    *,
    default: bool,
    dependencies: SetupDependencies,
) -> bool:
    suffix = "[Y/n] " if default else "[y/N] "
    while True:
        value = _input(f"{prompt} {suffix}", dependencies).strip().casefold()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("  Enter yes or no.")


def _choice(
    prompt: str,
    options: tuple[str, ...],
    *,
    default: int,
    dependencies: SetupDependencies,
) -> int:
    print(prompt)
    for index, option in enumerate(options, start=1):
        print(f"  [{index}] {option}")
    while True:
        raw = _input(f"Choice [{default}]: ", dependencies).strip()
        if not raw:
            return default
        try:
            selected = int(raw)
        except ValueError:
            selected = 0
        if 1 <= selected <= len(options):
            return selected
        print(f"  Enter a number from 1 through {len(options)}.")


def _configuration_stage(
    args: argparse.Namespace,
    *,
    dependencies: SetupDependencies,
) -> tuple[int, str]:
    path = dependencies.resolve_config_path()
    exists = path.exists()
    force = bool(getattr(args, "force_config", False))
    non_interactive = bool(getattr(args, "non_interactive", False))
    configure = force or not exists

    if exists and not force and not non_interactive:
        print(f"\nConfiguration found: {path}")
        configure = not _confirm(
            "Keep this configuration and validate it?",
            default=True,
            dependencies=dependencies,
        )

    if not configure:
        print(f"\n✓ Configuration retained: {path}")
        return 0, "retained"

    print("\n1/5 Configure inference")
    result = dependencies.configure(
        argparse.Namespace(
            non_interactive=non_interactive,
            profile=getattr(args, "profile", None),
            force=exists,
        )
    )
    return int(result), "configured" if result == 0 else "failed"


def _install_selection(
    args: argparse.Namespace,
    *,
    dependencies: SetupDependencies,
) -> InstallSelection:
    if bool(getattr(args, "skip_install", False)):
        return InstallSelection("skip", None, False)

    dashboard = not bool(getattr(args, "no_dashboard", False))
    if getattr(args, "agent", None):
        mode, host = "one", str(args.agent)
    elif bool(getattr(args, "all", False)) or bool(getattr(args, "non_interactive", False)):
        mode, host = "all", None
    else:
        detected = dependencies.detect_hosts()
        detected_label = ", ".join(detected) if detected else "none"
        print("\nDetected supported harnesses: " + detected_label)
        print("Supported harnesses: " + ", ".join(HOSTS))
        scope = _choice(
            "Which harness integrations should setup install?",
            (
                "All safely detected harnesses (recommended)",
                "One explicit supported harness",
                "No harness integration (dashboard only or verification only)",
            ),
            default=1,
            dependencies=dependencies,
        )
        mode, host = ("all", None) if scope == 1 else ("none", None)
        if scope == 2:
            host_index = _choice(
                "Choose one harness:",
                tuple(HOSTS),
                default=1,
                dependencies=dependencies,
            )
            mode, host = "one", tuple(HOSTS)[host_index - 1]

    if not bool(getattr(args, "non_interactive", False)) and dashboard:
        dashboard = _confirm(
            "Install or refresh the optional local dashboard service?",
            default=True,
            dependencies=dependencies,
        )
    return InstallSelection(mode, host, dashboard)


def _install_arguments(args: argparse.Namespace, selection: InstallSelection) -> argparse.Namespace:
    return argparse.Namespace(
        profile=getattr(args, "profile", None),
        config=None,
        all=selection.mode == "all",
        agent=selection.host,
        dry_run=False,
        rollback=False,
        verify_activation=False,
        backup=None,
        no_dashboard=not selection.dashboard,
        autonomous=False,
        production_container=False,
        activation_timeout=180.0,
        json=False,
        _setup_accept_activation_pending=True,
    )


def _run_install(
    args: argparse.Namespace,
    selection: InstallSelection,
    *,
    dependencies: SetupDependencies,
) -> tuple[int, str]:
    if selection.mode == "skip":
        print("\n2/5 Installation skipped by request.")
        return 0, "skipped"
    if selection.mode == "none" and not selection.dashboard:
        print("\n2/5 No harness or dashboard installation selected.")
        return 0, "skipped"

    print("\n2/5 Install harnesses and dashboard")
    if selection.mode == "none":
        result = dependencies.dashboard_service(
            argparse.Namespace(
                dashboard_service_action="install",
                dry_run=False,
                json=False,
                no_open=True,
            )
        )
        return int(result), "dashboard-only" if result == 0 else "failed"

    result = dependencies.install(_install_arguments(args, selection))
    label = "all-detected" if selection.mode == "all" else str(selection.host)
    result = int(result)
    if result == 0:
        install_label = label
    elif result == 2:
        install_label = "activation-pending"
    else:
        install_label = "failed"
    return result, install_label


def _smoke_requested(args: argparse.Namespace, dependencies: SetupDependencies) -> bool:
    if bool(getattr(args, "skip_smoke", False)):
        return False
    if bool(getattr(args, "non_interactive", False)):
        return True
    return _confirm(
        "Run deterministic smoke checks now?",
        default=True,
        dependencies=dependencies,
    )


def _smoke_arguments(selection: InstallSelection) -> argparse.Namespace:
    one_host = selection.mode == "one" and selection.host is not None
    return argparse.Namespace(
        all=not one_host,
        agent=selection.host if one_host else None,
        json=False,
    )


def _print_summary(stages: list[tuple[str, str]]) -> None:
    print("\nSetup summary")
    print("━" * 40)
    for stage, result in stages:
        print(f"  {stage:<16} {result}")


def _validate_non_interactive_scope(args: argparse.Namespace) -> None:
    if not bool(getattr(args, "non_interactive", False)):
        return
    if not (
        bool(getattr(args, "all", False))
        or getattr(args, "agent", None)
        or bool(getattr(args, "skip_install", False))
    ):
        raise ValueError(
            "--non-interactive requires an explicit --all, --agent, or --skip-install choice"
        )


def cmd_setup(
    args: argparse.Namespace,
    *,
    dependencies: SetupDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Guide first-run configuration, install, diagnostics, and smoke."""

    _validate_non_interactive_scope(args)
    print("Agency Runtime guided setup")
    print("Secrets use hidden prompts or environment-variable names; never command arguments.")
    stages: list[tuple[str, str]] = []

    config_result, config_label = _configuration_stage(args, dependencies=dependencies)
    stages.append(("configuration", config_label))
    if config_result != 0:
        _print_summary(stages)
        print("Resume with: agency setup")
        return 1

    print("\nValidation")
    validation_result = int(dependencies.validate(argparse.Namespace()))
    validation_label = {0: "passed", 2: "degraded"}.get(validation_result, "failed")
    stages.append(("config validate", validation_label))
    if validation_result not in _DIAGNOSTIC_RESULTS:
        _print_summary(stages)
        print("Repair configuration, then resume with: agency setup")
        return 1

    selection = _install_selection(args, dependencies=dependencies)
    install_result, install_label = _run_install(
        args,
        selection,
        dependencies=dependencies,
    )
    stages.append(("installation", install_label))

    print("\n3/5 Diagnose final posture")
    doctor_result = int(dependencies.doctor(argparse.Namespace(json=False, verbose=True)))
    doctor_label = {0: "passed", 2: "degraded"}.get(doctor_result, "failed")
    stages.append(("doctor", doctor_label))
    if install_result not in _DIAGNOSTIC_RESULTS or doctor_result not in _DIAGNOSTIC_RESULTS:
        _print_summary(stages)
        print("A stage failed. Review the output above, then resume with: agency setup")
        return 1

    if _smoke_requested(args, dependencies):
        print("\n4/5 Run deterministic smoke")
        smoke_result = int(dependencies.smoke(_smoke_arguments(selection)))
        stages.append(("smoke", "passed" if smoke_result == 0 else "failed"))
        if smoke_result != 0:
            _print_summary(stages)
            print("Smoke failed; inspect with: agency doctor --json")
            return 1
    else:
        stages.append(("smoke", "skipped"))

    stages.append(("next", "open dashboard / restart harnesses"))
    _print_summary(stages)
    print("\n5/5 Next steps")
    if selection.dashboard:
        print("  agency dashboard service open")
    print("  Restart each harness opened before installation.")
    if selection.mode in {"all", "one"} and (selection.mode == "all" or selection.host == "codex"):
        print(
            "  After Codex hook trust is settled: agency install --agent codex --verify-activation"
        )
    print("  Deterministic smoke is readiness evidence, not a live host canary.")
    return 2 if 2 in {validation_result, install_result, doctor_result} else 0


__all__ = ["InstallSelection", "SetupDependencies", "cmd_setup"]
