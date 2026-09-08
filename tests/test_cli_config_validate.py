"""Explicit-file validation never needs an installed Store or provider."""

from __future__ import annotations

import argparse
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.cli import config_commands, install_commands
from agency_runtime.cli import main as cli
from agency_runtime.core import configuration_persistence
from agency_runtime.core.config import load_config, reset_config_cache
from agency_runtime.core.configuration_contracts import MAX_CONFIG_BYTES


def _forbidden(*_args: object, **_kwargs: object) -> None:
    pytest.fail("document validation crossed into installed state or permission repair")


@pytest.fixture
def document_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "absent-ambient.yaml"))
    monkeypatch.setenv("AGENCY_PROFILE", "invalid-ambient-override")
    monkeypatch.setattr(cli, "load_config", _forbidden)
    monkeypatch.setattr(config_commands, "run_doctor", _forbidden)
    monkeypatch.setattr(configuration_persistence, "_ensure_config_file_private", _forbidden)


def test_explicit_config_is_write_free_and_does_not_load_ambient_state(
    document_only: None,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "reviewed.yaml"
    raw = b"profile: standard\nstore:\n  db_path: uninstalled/agency.db\njudge:\n  api_key_env: UNSET_REVIEWED_KEY\n"
    path.write_bytes(raw)
    path.chmod(0o644)
    mode = stat.S_IMODE(path.stat().st_mode)

    assert cli.main(["config", "validate", "--config", str(path)]) == 0

    assert "Config document valid" in capsys.readouterr().out
    assert path.read_bytes() == raw
    assert stat.S_IMODE(path.stat().st_mode) == mode
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("raw", [b"", b"{}\n"])
def test_empty_partial_config_matches_the_existing_schema(
    document_only: None, tmp_path: Path, raw: bytes
) -> None:
    path = tmp_path / "reviewed.yaml"
    path.write_bytes(raw)
    assert cli.main(["config", "validate", "--config", str(path)]) == 0


@pytest.mark.parametrize(
    "raw",
    [
        b"null\n",
        b"[]\n",
        b"profile: standard\nprofile: power\n",
        b"profile: unknown-secret-value\n",
        b"judge:\n  api_key_env: invalid secret name\n",
        b"judge:\n  api_key: [private-value\n",
        b"profile: \xff\n",
        b"[" * 100 + b"]" * 100,
        b"x" * (MAX_CONFIG_BYTES + 1),
    ],
)
def test_invalid_config_is_rejected_without_echoing_values_or_writing(
    document_only: None,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    raw: bytes,
) -> None:
    path = tmp_path / "reviewed.yaml"
    path.write_bytes(raw)

    assert cli.main(["config", "validate", "--config", str(path)]) == 1

    output = capsys.readouterr()
    assert "Config document valid" not in output.out
    assert "unknown-secret-value" not in output.err
    assert "invalid secret name" not in output.err
    assert "private-value" not in output.err
    assert path.read_bytes() == raw
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("argument", ["", "relative.yaml", "~/agency.yaml", "/tmp/\x00"])
def test_explicit_config_requires_one_safe_absolute_path(
    document_only: None, argument: str
) -> None:
    assert cli.main(["config", "validate", "--config", argument]) == 1


def test_missing_explicit_config_never_falls_back_to_defaults(
    document_only: None, tmp_path: Path
) -> None:
    path = tmp_path / "missing.yaml"
    assert cli.main(["config", "validate", "--config", str(path)]) == 1
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX link and namespace fixture")
@pytest.mark.parametrize("kind", ["file-link", "parent-link", "writable-parent", "fifo"])
def test_unsafe_config_identity_is_refused_without_repairs(
    document_only: None, tmp_path: Path, kind: str
) -> None:
    directory = tmp_path / "config"
    directory.mkdir(mode=0o700)
    path = directory / "agency.yaml"
    path.write_text("profile: standard\n", encoding="utf-8")
    requested = path
    if kind == "file-link":
        requested = directory / "linked.yaml"
        requested.symlink_to(path)
    elif kind == "parent-link":
        linked = tmp_path / "linked"
        linked.symlink_to(directory, target_is_directory=True)
        requested = linked / "agency.yaml"
    elif kind == "writable-parent":
        directory.chmod(0o777)
    else:
        requested = directory / "pipe"
        os.mkfifo(requested)
    mode = stat.S_IMODE(directory.stat().st_mode)

    assert cli.main(["config", "validate", "--config", str(requested)]) == 1
    assert stat.S_IMODE(directory.stat().st_mode) == mode
    assert path.read_text(encoding="utf-8") == "profile: standard\n"


def test_explicit_validation_and_install_load_the_same_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "reviewed.yaml"
    path.write_text(
        "profile: standard\nstore:\n  db_path: uninstalled/agency.db\n", encoding="utf-8"
    )
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "absent-ambient.yaml"))
    # The suite's isolation fixture supplies this normal deployment override;
    # remove it only here to compare the file's own relative Store binding.
    monkeypatch.delenv("AGENCY_DB_PATH", raising=False)
    monkeypatch.setattr(config_commands, "run_doctor", _forbidden)
    reset_config_cache()
    try:
        assert cli.main(["config", "validate", "--config", str(path)]) == 0
        cfg = install_commands._load_install_config(
            argparse.Namespace(config=str(path)),
            install_commands.InstallDependencies(load_config=load_config),
        )
        assert cfg.config_path == str(path)
        assert cfg.store.db_path == str(tmp_path / "uninstalled" / "agency.db")
        assert list(tmp_path.iterdir()) == [path]
    finally:
        reset_config_cache()


def test_bare_validate_retains_installed_health_behavior(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = object()
    calls = []
    report = SimpleNamespace(
        exit_code=2,
        checks=[SimpleNamespace(status="warn", name="host", message="not installed")],
    )
    monkeypatch.setattr(
        config_commands, "run_doctor", lambda selected: calls.append(selected) or report
    )
    dependencies = config_commands.ConfigurationDependencies(load_config=lambda: cfg)

    assert config_commands.cmd_config_validate(argparse.Namespace(), dependencies=dependencies) == 2
    assert calls == [cfg]
    assert "host: not installed" in capsys.readouterr().out
