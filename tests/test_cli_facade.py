"""Compatibility and discoverability checks for the modular CLI facade."""

from __future__ import annotations

import argparse

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
