"""Compatibility and discoverability checks for the modular CLI facade."""

from __future__ import annotations

import argparse
import subprocess

import pytest

from agency_runtime.cli import delegation_commands
from agency_runtime.cli import main as cli


def test_parser_binds_current_facade_handler(monkeypatch) -> None:
    observed: list[argparse.Namespace] = []

    def replacement(args: argparse.Namespace) -> int:
        observed.append(args)
        return 23

    monkeypatch.setattr(cli, "cmd_search", replacement)
    parsed = cli.build_parser().parse_args(["search", "review this"])

    assert parsed.func is replacement
    assert parsed.func(parsed) == 23
    assert observed == [parsed]


def test_expected_command_error_keeps_stable_cli_prefix(monkeypatch, capsys) -> None:
    def fail(_args: argparse.Namespace) -> int:
        raise ValueError("invalid test input")

    monkeypatch.setattr(cli, "cmd_status", fail)

    assert cli.main(["status"]) == 1
    assert capsys.readouterr().err == "agency: error: invalid test input\n"


def test_compatibility_runner_reports_process_start_failures(monkeypatch, capsys) -> None:
    def missing(*_args, **_kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(delegation_commands.subprocess, "run", missing)

    assert cli._run_command(["missing\x1b[31m-command"]) == 127
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Command not found: missing\\u001b[31m-command\n"


def test_compatibility_runner_bounds_invalid_arguments(monkeypatch, capsys) -> None:
    def unexpected(*_args, **_kwargs):
        raise AssertionError("subprocess must not be started")

    monkeypatch.setattr(delegation_commands.subprocess, "run", unexpected)

    assert cli._run_command(["tool", "bad\x00value"]) == 2
    assert cli._run_command(["tool", 7]) == 2  # type: ignore[list-item]
    assert capsys.readouterr().err == (
        "Command arguments must not contain NUL bytes\nCommand arguments must be strings\n"
    )


def test_compatibility_runner_maps_timeout_to_standard_exit_code(
    monkeypatch,
    capsys,
) -> None:
    def timed_out(command, **_kwargs):
        raise subprocess.TimeoutExpired(command, 1)

    monkeypatch.setattr(delegation_commands.subprocess, "run", timed_out)

    assert cli._run_command(["slow-tool"], timeout=1) == 124
    assert capsys.readouterr().err == "Command timed out\n"


@pytest.mark.parametrize(
    ("error", "exit_code", "message"),
    [
        (PermissionError(), 126, "Command is not executable: tool\n"),
        (OSError(), 1, "Command failed to start (OSError)\n"),
    ],
)
def test_compatibility_runner_maps_other_start_errors(
    error,
    exit_code,
    message,
    monkeypatch,
    capsys,
) -> None:
    def fail(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(delegation_commands.subprocess, "run", fail)

    assert cli._run_command(["tool"]) == exit_code
    assert capsys.readouterr().err == message


def test_compatibility_runner_preserves_child_exit_code(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        delegation_commands.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(["tool"], 17),
    )

    assert cli._run_command(["tool"]) == 17
    assert cli._run_command([]) == 2
    assert capsys.readouterr().err == "No command supplied\n"
