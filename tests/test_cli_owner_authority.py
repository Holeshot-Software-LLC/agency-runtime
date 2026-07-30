"""AR-204 owner CLI authority and retired-presence regression coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from agency_runtime.cli import main as cli_main
from agency_runtime.core.install_lifecycle import is_exact_install_lifecycle

_OWNER_CONTROL_CASES = [
    ["install"],
    ["uninstall", "--agent", "codex", "--confirm-plan", "a" * 64],
    ["on"],
    ["off", "--global"],
    ["configure"],
    ["config", "set", "judge.model", "gpt-test"],
    ["config", "provider", "set", "primary", "--type", "openai"],
    ["config", "provider", "remove", "primary"],
    ["config", "reset"],
    ["sync"],
    ["source", "add", "https://example.test/roster"],
    ["roster", "diff"],
    ["roster", "approve", "snapshot-1"],
    ["roster", "activate", "snapshot-1"],
    ["roster", "retire", "worker", "--scan-id", "scan-1"],
    [
        "roster",
        "rollback",
        "worker",
        "sha256:" + "2" * 64,
        "--expected-current-version",
        "sha256:" + "1" * 64,
        "--expected-current-hash",
        "3" * 64,
    ],
    ["roster", "upstream", "import"],
    ["roster", "candidate", "audit", "candidate-1"],
    ["roster", "candidate", "reject", "candidate-1", "--reason", "unsafe"],
    ["agents", "enable", "worker"],
    ["agents", "disable", "worker"],
    [
        "workforce",
        "promote",
        "worker",
        "--expected-revision",
        "1",
        "--reason",
        "proven",
    ],
    [
        "workforce",
        "suspend",
        "worker",
        "--expected-revision",
        "1",
        "--reason",
        "unsafe",
        "--confirm",
        "SUSPEND worker",
    ],
    [
        "workforce",
        "merge",
        "worker",
        "--into",
        "survivor",
        "--expected-revision",
        "1",
        "--reason",
        "duplicate",
        "--confirm",
        "MERGE worker INTO survivor",
    ],
    [
        "hiring",
        "approve",
        "case-1",
        "--approved-by",
        "owner",
        "--confirm",
        "APPROVE case-1",
    ],
    ["db", "trim", "--keep-last", "10"],
    ["dashboard", "service", "start"],
    ["dashboard", "service", "stop"],
    ["dashboard", "service", "restart"],
    ["dashboard", "service", "uninstall"],
    ["dashboard", "service", "install"],
    ["dashboard", "service", "open", "--no-open"],
]


@pytest.mark.parametrize("argv", _OWNER_CONTROL_CASES)
def test_owner_control_leaves_have_no_retired_presence_binding(argv: list[str]) -> None:
    parsed = cli_main.build_parser().parse_args(argv)

    assert not any(key.startswith("_operator_presence") for key in vars(parsed))


def test_owner_control_dispatch_reaches_the_bound_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    def handler(args: object) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(cli_main, "cmd_config_reset", handler)

    assert cli_main.main(["config", "reset"]) == 0
    assert len(calls) == 1


def test_install_shape_remains_closed_world_without_presence_metadata() -> None:
    parsed = cli_main.build_parser().parse_args(["install"])

    assert is_exact_install_lifecycle(parsed) is True
    parsed.future_install_flag = False
    assert is_exact_install_lifecycle(parsed) is False


def test_retired_operator_presence_module_is_not_shipped() -> None:
    package_root = Path(cli_main.__file__).resolve().parents[1]

    assert not (package_root / "core" / "operator_presence.py").exists()
