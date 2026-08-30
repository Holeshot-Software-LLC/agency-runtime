"""Adversarial tests for the delegation lifecycle's Git process boundary."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import git_runner as lifecycle_git
from agency_runtime.core.delegation.backends import BoundedProcessResult


def _isolated_git_environment() -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def _raw_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "core.longpaths=true", *args],
        cwd=repo,
        env=_isolated_git_environment(),
        check=check,
        capture_output=True,
        text=True,
    )


def _initialize_repo(repo: Path) -> None:
    repo.mkdir()
    _raw_git(repo, "init", "-b", "main")
    _raw_git(repo, "config", "--local", "user.name", "Test User")
    _raw_git(repo, "config", "--local", "user.email", "test@example.com")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _raw_git(repo, "add", "README.md")
    _raw_git(repo, "commit", "-m", "initial")


def test_run_git_replaces_every_inherited_git_environment_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "GIT_DIR",
        "git_work_tree",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_KEY_0",
        "GIT_CONFIG_VALUE_0",
        "GIT_EXEC_PATH",
    ):
        monkeypatch.setenv(name, "attacker-controlled")
    observed: dict[str, Any] = {}

    def fake_runner(argv: list[str], **kwargs: Any) -> BoundedProcessResult:
        observed["argv"] = argv
        observed.update(kwargs)
        return BoundedProcessResult(0, "safe\n", "")

    monkeypatch.setattr(lifecycle_git, "run_bounded_process", fake_runner)

    result = lifecycle_git.run_git(tmp_path, ["status", "--porcelain"])

    assert result.returncode == 0
    environment = observed["env"]
    assert {key for key in environment if key.upper().startswith("GIT_")} == set(
        lifecycle_git._SAFE_GIT_ENVIRONMENT
    )
    assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_TERMINAL_PROMPT"] == "0"
    assert "--no-pager" in observed["argv"]
    assert "core.fsmonitor=false" in observed["argv"]
    assert "core.hooksPath=" in observed["argv"]
    assert observed["max_output_chars"] == 64 * 1024


@pytest.mark.parametrize(
    ("result", "returncode", "message"),
    [
        (
            BoundedProcessResult(124, "partial secret", "", timed_out=True),
            124,
            "time limit",
        ),
        (
            BoundedProcessResult(
                0,
                "partial secret",
                "",
                stdout_truncated=True,
            ),
            125,
            "safety limit",
        ),
        (
            BoundedProcessResult(
                1,
                "",
                "partial secret",
                stderr_truncated=True,
            ),
            125,
            "safety limit",
        ),
    ],
)
def test_run_git_fails_closed_on_timeout_or_truncated_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    result: BoundedProcessResult,
    returncode: int,
    message: str,
) -> None:
    monkeypatch.setattr(
        lifecycle_git,
        "run_bounded_process",
        lambda *_args, **_kwargs: result,
    )

    completed = lifecycle_git.run_git(tmp_path, ["status", "--porcelain"])

    assert completed.returncode == returncode
    assert completed.stdout == ""
    assert "partial secret" not in completed.stderr
    assert message in completed.stderr


@pytest.mark.parametrize(
    "args",
    [
        [],
        [""],
        ["status\x00--porcelain"],
        ["-c", "core.fsmonitor=attacker", "status"],
        ["--config-env=core.fsmonitor=ATTACKER", "status"],
        ["-C", "attacker-repository", "status"],
    ],
)
def test_run_git_rejects_invalid_or_unsafe_argv(tmp_path: Path, args: list[str]) -> None:
    with pytest.raises((TypeError, ValueError)):
        lifecycle_git.run_git(tmp_path, args)


def test_run_git_ignores_inherited_repository_and_inline_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    decoy = tmp_path / "decoy"
    _initialize_repo(repo)
    _initialize_repo(decoy)
    monkeypatch.setenv("GIT_DIR", str(decoy / ".git"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.fsmonitor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "DO-NOT-RUN-INLINE")

    result = lifecycle_git.run_git(repo, ["rev-parse", "--show-toplevel"])

    assert result.returncode == 0
    assert Path(result.stdout.strip()).resolve() == repo.resolve()
    assert "DO-NOT-RUN-INLINE" not in result.stderr
    assert lifecycle_git.git_root(repo / "README.md") == repo.resolve()


def test_run_git_disables_local_fsmonitor_command(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _initialize_repo(repo)
    _raw_git(
        repo,
        "config",
        "--local",
        "core.fsmonitor",
        "DO-NOT-RUN-FSMONITOR",
    )

    result = lifecycle_git.run_git(repo, ["status", "--porcelain"])

    assert result.returncode == 0
    assert "DO-NOT-RUN-FSMONITOR" not in result.stderr


@pytest.mark.parametrize(
    ("key", "args", "kind"),
    [
        ("filter.attack.clean", ["add", "--all"], "filter"),
        ("filter.attack.smudge", ["checkout", "--", "README.md"], "filter"),
        ("filter.attack.process", ["worktree", "add", "elsewhere"], "filter"),
        ("merge.attack.driver", ["merge", "--abort"], "merge driver"),
        ("diff.attack.command", ["reset", "--hard", "HEAD"], "diff command"),
        ("diff.attack.textconv", ["restore", "README.md"], "diff command"),
    ],
)
def test_run_git_refuses_executable_local_repository_config_without_values(
    tmp_path: Path,
    key: str,
    args: list[str],
    kind: str,
) -> None:
    repo = tmp_path / "repo"
    _initialize_repo(repo)
    secret_value = "DO-NOT-ECHO-EXECUTABLE-CONFIG"
    _raw_git(repo, "config", "--local", key, secret_value)

    result = lifecycle_git.run_git(repo, args)

    assert result.returncode == 126
    assert kind in result.stderr
    assert secret_value not in result.stderr


def test_run_git_refuses_executable_config_from_local_include(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _initialize_repo(repo)
    include = tmp_path / "included.gitconfig"
    include.write_text(
        '[merge "included-attack"]\n\tdriver = DO-NOT-ECHO-INCLUDED-VALUE\n',
        encoding="utf-8",
    )
    _raw_git(repo, "config", "--local", "include.path", str(include))

    result = lifecycle_git.run_git(repo, ["merge", "--abort"])

    assert result.returncode == 126
    assert "merge driver" in result.stderr
    assert "DO-NOT-ECHO-INCLUDED-VALUE" not in result.stderr


def test_config_inspection_failure_refuses_mutating_operation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        lifecycle_git,
        "run_bounded_process",
        lambda *_args, **_kwargs: BoundedProcessResult(
            0,
            "filter.attack.clean\n",
            "",
            stdout_truncated=True,
        ),
    )

    result = lifecycle_git.run_git(tmp_path, ["add", "--all"])

    assert result.returncode == 126
    assert "could not be inspected safely" in result.stderr


def test_global_config_path_is_replaced_even_for_explicit_global_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    _initialize_repo(repo)
    hostile = tmp_path / "hostile.gitconfig"
    hostile.write_text("[agency]\n\tsecret = inherited-value\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(hostile))

    result = lifecycle_git.run_git(
        repo,
        ["config", "--global", "--get", "agency.secret"],
    )

    assert result.returncode != 0
    assert "inherited-value" not in result.stdout
