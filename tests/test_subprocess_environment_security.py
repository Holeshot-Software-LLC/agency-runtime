"""Adversarial contracts for least-privilege child environments."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from agency_runtime.core.installer import _command_environment
from agency_runtime.core.process_environment import least_privilege_subprocess_environment


def test_ambient_environment_keeps_only_platform_and_selected_integration(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    poisoned = repository / "bin"
    safe_bin = tmp_path / "safe-bin"
    poisoned.mkdir(parents=True)
    safe_bin.mkdir()
    home = tmp_path / "home"
    environment = {
        "PATH": os.pathsep.join(("", ".", "relative", str(poisoned), str(safe_bin))),
        "HOME": str(home),
        "HTTP_PROXY": "http://127.0.0.1:8080",
        "LANG": "en_US.UTF-8",
        "CODEX_HOME": str(home / "codex"),
        "CLAUDE_CONFIG_DIR": str(home / "claude"),
        "HERMES_HOME": str(home / "hermes"),
        "OPENCLAW_HOME": str(home / "openclaw"),
        "OPENAI_API_KEY": "unrelated-openai-secret",
        "ANTHROPIC_API_KEY": "unrelated-anthropic-secret",
        "AWS_SECRET_ACCESS_KEY": "unrelated-aws-secret",
    }

    child = least_privilege_subprocess_environment(
        "codex",
        environ=environment,
        current_directory=repository,
        forbidden_roots=(repository,),
    )

    assert child["PATH"] == str(safe_bin.resolve())
    assert child["CODEX_HOME"] == str(home / "codex")
    assert child["HTTP_PROXY"] == "http://127.0.0.1:8080"
    assert child["LANG"] == "en_US.UTF-8"
    for name in (
        "CLAUDE_CONFIG_DIR",
        "HERMES_HOME",
        "OPENCLAW_HOME",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
    ):
        assert name not in child


@pytest.mark.parametrize("unsafe", ("", ".", "relative"))
def test_explicit_path_rejects_empty_dot_and_relative_entries(
    unsafe: str,
    tmp_path: Path,
) -> None:
    safe_bin = tmp_path / "safe-bin"
    safe_bin.mkdir()

    with pytest.raises(ValueError, match="explicit PATH"):
        least_privilege_subprocess_environment(
            "generic",
            environ={"PATH": str(safe_bin)},
            extra_env={"Path": os.pathsep.join((unsafe, str(safe_bin)))},
            current_directory=tmp_path / "working",
        )


def test_explicit_path_rejects_missing_and_repository_directories(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository_bin = repository / "bin"
    repository_bin.mkdir(parents=True)

    for value in (str(tmp_path / "missing"), str(repository_bin)):
        with pytest.raises(ValueError, match="explicit PATH"):
            least_privilege_subprocess_environment(
                "codex",
                environ={},
                extra_env={"PATH": value},
                current_directory=repository,
                forbidden_roots=(repository,),
            )


def test_extra_environment_cannot_add_another_hosts_auth_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="another integration"):
        least_privilege_subprocess_environment(
            "codex",
            environ={"HOME": str(tmp_path)},
            extra_env={"CLAUDE_CONFIG_DIR": str(tmp_path / "claude")},
        )


def test_installer_environment_omits_unrelated_credentials_and_host_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "provider-secret")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "ambient-claude"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "ambient-hermes"))

    child = _command_environment("codex", home_dir=tmp_path / "isolated-home")

    assert child["CODEX_HOME"] == str((tmp_path / "isolated-home" / ".codex").resolve())
    assert child["HOME"] == str((tmp_path / "isolated-home").resolve())
    assert "OPENAI_API_KEY" not in child
    assert "AWS_SECRET_ACCESS_KEY" not in child
    assert "CLAUDE_CONFIG_DIR" not in child
    assert "HERMES_HOME" not in child
