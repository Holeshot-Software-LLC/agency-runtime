"""AR-143 shared operator-presence coverage for persistent CLI mutations."""

from __future__ import annotations

from pathlib import Path

import pytest

from agency_runtime.cli import main as cli_main
from agency_runtime.core import operator_presence


@pytest.mark.parametrize(
    ("argv", "family"),
    [
        (["on"], "runtime-control"),
        (["off", "--global"], "runtime-control"),
        (["configure"], "configuration"),
        (["config", "set", "judge.model", "gpt-test"], "configuration"),
        (
            ["config", "provider", "set", "primary", "--type", "openai"],
            "configuration",
        ),
        (["config", "provider", "remove", "primary"], "configuration"),
        (["config", "reset"], "configuration"),
        (["sync"], "roster-governance"),
        (["source", "add", "https://example.test/roster"], "roster-governance"),
        (["roster", "diff"], "roster-governance"),
        (["roster", "approve", "snapshot-1"], "roster-governance"),
        (["roster", "activate", "snapshot-1"], "roster-governance"),
        (
            ["roster", "retire", "worker", "--scan-id", "scan-1"],
            "roster-governance",
        ),
        (["roster", "upstream", "import"], "roster-governance"),
        (["roster", "candidate", "audit", "candidate-1"], "roster-governance"),
        (
            ["roster", "candidate", "reject", "candidate-1", "--reason", "unsafe"],
            "roster-governance",
        ),
        (["agents", "enable", "worker"], "agent-governance"),
        (["agents", "disable", "worker"], "agent-governance"),
        (
            [
                "workforce",
                "promote",
                "worker",
                "--expected-revision",
                "1",
                "--reason",
                "proven",
            ],
            "workforce-governance",
        ),
        (
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
            "workforce-governance",
        ),
        (
            [
                "workforce",
                "resume",
                "worker",
                "--expected-revision",
                "1",
                "--reason",
                "recovered",
            ],
            "workforce-governance",
        ),
        (
            [
                "workforce",
                "retire",
                "worker",
                "--expected-revision",
                "1",
                "--reason",
                "obsolete",
                "--confirm",
                "RETIRE worker",
            ],
            "workforce-governance",
        ),
        (
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
            "workforce-governance",
        ),
        (
            [
                "workforce",
                "amend",
                "case-1",
                "--approved-by",
                "operator",
                "--confirm",
                "APPROVE case-1",
            ],
            "hiring-governance",
        ),
        (
            [
                "workforce",
                "enable",
                "worker",
                "--reason",
                "needed",
                "--confirm",
                "ENABLE worker",
            ],
            "workforce-governance",
        ),
        (
            [
                "workforce",
                "disable",
                "worker",
                "--reason",
                "unsafe",
                "--confirm",
                "DISABLE worker",
            ],
            "workforce-governance",
        ),
        (
            [
                "hiring",
                "approve",
                "case-1",
                "--approved-by",
                "operator",
                "--confirm",
                "APPROVE case-1",
            ],
            "hiring-governance",
        ),
        (["db", "trim", "--keep-last", "10"], "database-maintenance"),
        (["dashboard", "service", "start"], "dashboard-service"),
        (["dashboard", "service", "stop"], "dashboard-service"),
        (["dashboard", "service", "restart"], "dashboard-service"),
        (["dashboard", "service", "uninstall"], "dashboard-service"),
        (["dashboard", "service", "install"], "dashboard-service"),
        (["dashboard", "service", "open", "--no-open"], "dashboard-service"),
    ],
)
def test_every_persistent_control_leaf_requests_operator_presence(
    argv: list[str],
    family: str,
) -> None:
    args = cli_main.build_parser().parse_args(argv)

    request = operator_presence.request_for_namespace(args)

    assert request is not None
    assert request.family == family
    assert request.command_path[0] == argv[0]
    assert len(request.operation_digest) == 64


@pytest.mark.parametrize(
    "argv",
    [
        ["status"],
        ["doctor"],
        ["config", "show"],
        ["config", "get", "judge.model"],
        ["config", "provider", "list"],
        ["config", "validate"],
        ["source", "list"],
        ["roster", "list"],
        ["roster", "scans"],
        ["roster", "upstream", "status"],
        ["roster", "candidate", "findings", "candidate-1"],
        ["roster", "candidate", "compare", "candidate-1"],
        ["agents", "list"],
        ["search", "security"],
        ["route", "review security"],
        ["policy"],
        ["workforce", "list"],
        ["workforce", "show", "worker"],
        ["contractor", "list"],
        ["hiring", "list"],
        ["db", "stats"],
        ["dashboard", "service", "status"],
    ],
)
def test_read_only_leaves_do_not_request_operator_presence(argv: list[str]) -> None:
    args = cli_main.build_parser().parse_args(argv)

    assert operator_presence.request_for_namespace(args) is None


def test_roster_rollback_retains_the_shared_fail_closed_boundary() -> None:
    args = cli_main.build_parser().parse_args(
        [
            "roster",
            "rollback",
            "worker",
            "sha256:" + "2" * 64,
            "--expected-current-version",
            "sha256:" + "1" * 64,
            "--expected-current-hash",
            "3" * 64,
        ]
    )

    request = operator_presence.request_for_namespace(args)
    assert request is not None
    assert request.family == "roster-governance"


@pytest.mark.parametrize(
    "argv",
    [
        ["uninstall", "--agent", "codex", "--confirm-plan", "a" * 64],
        ["uninstall", "--all", "--confirm-plan", "b" * 64],
    ],
)
def test_host_uninstall_commit_retains_the_shared_fail_closed_boundary(argv: list[str]) -> None:
    args = cli_main.build_parser().parse_args(argv)

    request = operator_presence.request_for_namespace(args)
    assert request is not None
    assert request.family == "installation"


def test_host_uninstall_dry_run_remains_write_free() -> None:
    args = cli_main.build_parser().parse_args(["uninstall", "--agent", "codex", "--dry-run"])

    assert operator_presence.request_for_namespace(args) is None


@pytest.mark.parametrize(
    "argv",
    [
        ["install"],
        ["install", "--all"],
        ["install", "--agent", "codex"],
        ["install", "--agent", "codex", "--no-dashboard"],
        ["install", "--rollback", "--agent", "codex"],
    ],
)
def test_full_suite_and_scoped_install_shapes_use_the_installer_boundary(argv: list[str]) -> None:
    args = cli_main.build_parser().parse_args(argv)

    assert operator_presence.request_for_namespace(args) is None


def test_prepared_presence_marker_rejects_every_other_command_path() -> None:
    args = cli_main.build_parser().parse_args(["config", "reset"])
    args._operator_presence_prepared_action = "roster.rollback.v1"

    with pytest.raises(operator_presence.OperatorPresenceError, match="binding is invalid"):
        operator_presence.request_for_namespace(args)


@pytest.mark.parametrize(
    "argv",
    [
        ["install", "--dry-run"],
        ["on", "--dry-run"],
        ["off", "--dry-run"],
        ["sync", "--dry-run"],
        ["roster", "upstream", "import", "--dry-run"],
        ["db", "trim", "--dry-run"],
        ["dashboard", "service", "install", "--dry-run"],
    ],
)
def test_write_free_modes_are_exempt(argv: list[str]) -> None:
    args = cli_main.build_parser().parse_args(argv)

    assert operator_presence.request_for_namespace(args) is None


def test_denial_prevents_handler_and_persistent_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    marker = tmp_path / "handler-ran"

    def mutating_handler(_args: object) -> int:
        marker.write_text("changed", encoding="utf-8")
        return 0

    monkeypatch.setattr(cli_main, "cmd_config_reset", mutating_handler)
    monkeypatch.setattr(
        operator_presence,
        "_request_os_operator_presence",
        lambda _prompt: operator_presence._PresenceResult(
            status=operator_presence._PresenceStatus.CANCELED,
            mechanism="test-verifier",
            detail="operator canceled",
        ),
    )

    assert cli_main.main(["config", "reset"]) == 1
    assert not marker.exists()
    assert "no persistent change was dispatched" in capsys.readouterr().err


def test_operation_change_during_verification_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = cli_main.build_parser().parse_args(["config", "set", "judge.model", "before"])

    def verified_after_mutation(_prompt: str) -> operator_presence._PresenceResult:
        args.value = "after"
        return operator_presence._PresenceResult(
            status=operator_presence._PresenceStatus.VERIFIED,
            mechanism="test-verifier",
            detail="verified",
        )

    monkeypatch.setattr(
        operator_presence,
        "_request_os_operator_presence",
        verified_after_mutation,
    )

    with pytest.raises(operator_presence.OperatorPresenceError, match="changed during"):
        operator_presence.enforce_for_namespace(args)


def test_prompt_exposes_no_raw_arguments_but_digest_binds_them() -> None:
    parser = cli_main.build_parser()
    first = operator_presence.request_for_namespace(
        parser.parse_args(["config", "set", "secret.api_key", "top-secret-value"])
    )
    second = operator_presence.request_for_namespace(
        parser.parse_args(["config", "set", "secret.api_key", "different-secret"])
    )

    assert first is not None and second is not None
    assert "secret.api_key" not in first.prompt
    assert "top-secret-value" not in first.prompt
    assert first.operation_digest != second.operation_digest


def test_boundary_has_no_phrase_environment_or_exported_credential_bypass() -> None:
    source = Path(operator_presence.__file__).read_text(encoding="utf-8")

    for forbidden in (
        "CredUIPrompt",
        "CredUnPack",
        "LogonUser",
        "getpass",
        "isatty",
        "os.environ",
    ):
        assert forbidden not in source
