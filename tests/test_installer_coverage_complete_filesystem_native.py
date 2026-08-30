from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import installer
from agency_runtime.core import installer_filesystem as filesystem
from agency_runtime.core import installer_inventory as inventory
from agency_runtime.core import installer_native as native
from agency_runtime.core import installer_payload_manifests as payload_manifests
from agency_runtime.core import installer_payloads as payloads
from agency_runtime.core.config import AgencyConfig, OllamaConfig
from agency_runtime.core.installer_contracts import (
    HERMES_BYTECODE_GUARD,
    INSTALL_MANIFEST,
    PLUGIN_ID,
    PLUGIN_VERSION,
    NativeCommandResult,
)


def test_native_command_result_can_expose_bounded_output() -> None:
    result = NativeCommandResult(("host", "status"), 0, "stdout", "stderr")
    assert result.to_dict(expose_output=True) == {
        "command": ["host", "status"],
        "returncode": 0,
        "ok": True,
        "stdout_truncated": False,
        "stderr_truncated": False,
        "stdout": "stdout",
        "stderr": "stderr",
    }


@pytest.mark.parametrize("path", ["../escape", "/absolute", "nested/../../escape"])
def test_safe_relative_rejects_escape_paths(path: str) -> None:
    with pytest.raises(ValueError, match="unsafe generated file path"):
        filesystem.safe_relative(path)


def test_atomic_install_staging_error_preserves_preexisting_unowned_target(
    tmp_path: Path,
) -> None:
    target = tmp_path / "plugin"
    target.mkdir()
    sentinel = target / "user-owned.txt"
    sentinel.write_text("preserve", encoding="utf-8")

    with pytest.raises(ValueError, match="unsafe generated file path"):
        filesystem.atomic_install_tree(
            target,
            {"../escape.py": "unsafe"},
            host="codex",
            dry_run=False,
            home_dir=tmp_path,
        )

    assert sentinel.read_text(encoding="utf-8") == "preserve"


def test_atomic_install_restores_backup_when_final_replace_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "plugin"
    target.mkdir()
    sentinel = target / "original.txt"
    sentinel.write_text("original", encoding="utf-8")
    original_replace = filesystem.os.replace

    def replace(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
        source_path = Path(source)
        if ".staging-" in source_path.name:
            raise OSError("injected final replace failure")
        original_replace(source, destination)

    monkeypatch.setattr(filesystem.os, "replace", replace)
    with pytest.raises(OSError, match="final replace failure"):
        filesystem.atomic_install_tree(
            target,
            {
                "plugin.py": "managed",
                HERMES_BYTECODE_GUARD: "cache denied\n",
            },
            host="hermes",
            dry_run=False,
            home_dir=tmp_path,
        )

    assert sentinel.read_text(encoding="utf-8") == "original"
    assert not any(".staging-" in path.name for path in tmp_path.iterdir())


@pytest.mark.skipif(os.name == "nt", reason="POSIX install-tree mode contract")
def test_atomic_hermes_install_is_sealed_against_bytecode_cache_drift(
    tmp_path: Path,
) -> None:
    target = tmp_path / "plugin"
    files, primary = payload_manifests.build_hermes_bundle("VALUE = 1\n", mcp={})
    assert primary == "__init__.py"
    assert HERMES_BYTECODE_GUARD in files
    previous_umask = os.umask(0o002)
    try:
        installed = filesystem.atomic_install_tree(
            target,
            files,
            host="hermes",
            dry_run=False,
            home_dir=tmp_path,
        )
    finally:
        os.umask(previous_umask)

    assert installed["unchanged"] is False
    guard_directory = target / Path(HERMES_BYTECODE_GUARD).parent
    guard_marker = target / HERMES_BYTECODE_GUARD
    assert stat.S_IMODE(target.stat().st_mode) == 0o700
    assert stat.S_IMODE(guard_directory.stat().st_mode) == 0o500
    assert stat.S_IMODE(guard_marker.stat().st_mode) == 0o400
    environment = dict(os.environ)
    environment.pop("PYTHONDONTWRITEBYTECODE", None)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import pathlib, sys; "
                f"sys.path.insert(0, {str(tmp_path)!r}); "
                "import plugin; "
                "assert plugin.VALUE == 1; "
                f"assert list(pathlib.Path({str(guard_directory)!r}).iterdir()) == "
                f"[pathlib.Path({str(guard_marker)!r})]"
            ),
        ],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert list(guard_directory.iterdir()) == [guard_marker]
    valid, error, _manifest = filesystem.validate_owned_install_tree(
        target,
        host="hermes",
        target=target,
    )
    assert valid is True
    assert error is None

    guard_directory.chmod(0o700)
    guard_marker.chmod(0o600)
    valid, error, _manifest = filesystem.validate_owned_install_tree(
        target,
        host="hermes",
        target=target,
    )
    assert valid is False
    assert error == "Install tree violates its Hermes bytecode-cache policy"
    refreshed = filesystem.atomic_install_tree(
        target,
        files,
        host="hermes",
        dry_run=False,
        home_dir=tmp_path,
    )

    assert refreshed["unchanged"] is False
    assert refreshed["backup_path"] is not None
    assert stat.S_IMODE(target.stat().st_mode) == 0o700
    assert stat.S_IMODE((target / Path(HERMES_BYTECODE_GUARD).parent).stat().st_mode) == 0o500


def _write_backup_manifest(path: Path, target_path: Path, **overrides: Any) -> None:
    path.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "owner": "agency-runtime",
        "host": "codex",
        "plugin_id": PLUGIN_ID,
        "plugin_version": PLUGIN_VERSION,
        "target": str(target_path),
        "owned_files": ["plugin.py"],
    }
    manifest.update(overrides)
    (path / INSTALL_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")


def test_backup_validation_rejects_unowned_malformed_and_mismatched_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    assert (
        filesystem.validate_owned_backup(tmp_path / "missing", host="codex", target=target)[0]
        is False
    )

    backup = tmp_path / "backup"
    backup.mkdir()
    assert "ownership manifest" in str(
        filesystem.validate_owned_backup(backup, host="codex", target=target)[1]
    )
    (backup / INSTALL_MANIFEST).write_text("{invalid", encoding="utf-8")
    assert "unreadable or invalid" in str(
        filesystem.validate_owned_backup(backup, host="codex", target=target)[1]
    )
    (backup / INSTALL_MANIFEST).write_text("[]", encoding="utf-8")
    assert "JSON object" in str(
        filesystem.validate_owned_backup(backup, host="codex", target=target)[1]
    )

    _write_backup_manifest(backup, target, owner="someone-else")
    assert "unexpected owner" in str(
        filesystem.validate_owned_backup(backup, host="codex", target=target)[1]
    )
    _write_backup_manifest(backup, target, schema_version=3)
    assert "unexpected schema_version" in str(
        filesystem.validate_owned_backup(backup, host="codex", target=target)[1]
    )
    _write_backup_manifest(backup, target, plugin_version="invalid")
    assert "invalid plugin_version" in str(
        filesystem.validate_owned_backup(backup, host="codex", target=target)[1]
    )
    _write_backup_manifest(backup, target, target="")
    assert "has no target" in str(
        filesystem.validate_owned_backup(backup, host="codex", target=target)[1]
    )
    _write_backup_manifest(backup, target, owned_files=[1])
    assert "invalid owned_files" in str(
        filesystem.validate_owned_backup(backup, host="codex", target=target)[1]
    )

    _write_backup_manifest(backup, target, target="raise-on-resolve")
    original_resolve = Path.resolve

    def resolve(path: Path, *args: Any, **kwargs: Any) -> Path:
        if str(path) == "raise-on-resolve":
            raise OSError("invalid target")
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)
    assert "target is invalid" in str(
        filesystem.validate_owned_backup(backup, host="codex", target=target)[1]
    )


def test_launcher_inventory_rejects_unowned_and_malformed_artifact_manifests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document: dict[str, Any] = {
        "owner": "attacker",
        "host": "codex",
        "plugin_id": PLUGIN_ID,
        "launcher_artifacts": [],
    }
    monkeypatch.setattr(
        inventory,
        "_read_regular_file_bounded",
        lambda *_args, **_kwargs: json.dumps(document).encode("utf-8"),
    )
    assert inventory._managed_launcher_artifacts_current(tmp_path, "codex") is None

    document["owner"] = "agency-runtime"
    assert inventory._managed_launcher_artifacts_current(tmp_path, "codex") is False


def test_home_resolution_enforces_explicit_boundary_and_honors_runtime_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    inside = home / "inside"
    assert native.home_path("~", home_dir=home) == home.resolve()
    assert native.home_path("~/inside", home_dir=home) == inside.resolve()
    with pytest.raises(ValueError, match="host path escapes"):
        native.home_path("~/../outside", home_dir=home)
    assert native.home_path(str(inside), home_dir=home) == inside.resolve()
    with pytest.raises(ValueError, match="absolute path escapes"):
        native.home_path(str(tmp_path / "outside"), home_dir=home)

    runtime = tmp_path / "runtime"
    monkeypatch.setenv("AGENCY_HOME", str(runtime))
    assert native.runtime_home() == runtime.resolve()


def test_implicit_home_and_host_evidence_work_without_environment_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    expanded = tmp_path / "expanded"
    monkeypatch.setattr(native.os.path, "expanduser", lambda _path: str(expanded))
    assert native.home_path("~/managed") == expanded.resolve()

    resolved_by_facade = tmp_path / "facade-root"
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setattr(native, "_home_path", lambda *_args, **_kwargs: resolved_by_facade)
    assert native.host_root("codex") == resolved_by_facade

    hermes_root = tmp_path / "hermes"
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(native, "_host_root", lambda *_args, **_kwargs: hermes_root)
    assert native._host_evidence_paths("hermes") == [
        hermes_root,
        hermes_root / "config.yaml",
        hermes_root / "config.yml",
    ]


def test_native_output_runner_fallback_and_object_result_are_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(native, "MAX_NATIVE_OUTPUT_CHARS", 4)
    assert native._bounded_native_text("abcdef") == ("abcd", True)
    calls: list[dict[str, Any]] = []

    def runner(command: list[str], **kwargs: Any) -> Any:
        calls.append(kwargs)
        if kwargs:
            raise TypeError("legacy runner")
        return SimpleNamespace(
            returncode=3,
            stdout="abcdef",
            stderr="ghijkl",
            stdout_truncated=False,
            stderr_truncated=False,
        )

    result = native.run_native(
        ["codex", "plugin", "list"],
        host="codex",
        command_runner=runner,
    )
    assert result.returncode == 3
    assert result.stdout == "abcd"
    assert result.stderr == "ghij"
    assert result.stdout_truncated is True
    assert result.stderr_truncated is True
    assert calls[0]["timeout"] == 30.0
    assert "env" in calls[0]
    assert calls[1] == {}


def test_native_subprocess_truncation_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.delegation import backends

    bounded = SimpleNamespace(
        returncode=1,
        stdout="partial",
        stderr="",
        timed_out=False,
        stdout_truncated=True,
        stderr_truncated=False,
    )
    monkeypatch.setattr(backends, "run_bounded_process", lambda *_args, **_kwargs: bounded)

    result = native.run_native(["codex", "plugin", "list"], host="codex")

    assert result.returncode == 1
    assert result.stdout_truncated is True
    assert result.stderr == "native command output exceeded the capture limit"

    clean = SimpleNamespace(
        returncode=0,
        stdout="complete",
        stderr="",
        timed_out=False,
        stdout_truncated=False,
        stderr_truncated=False,
    )
    monkeypatch.setattr(backends, "run_bounded_process", lambda *_args, **_kwargs: clean)
    result = native.run_native(["codex", "plugin", "list"], host="codex")
    assert result.ok is True
    assert result.stderr == ""


def test_native_host_lifecycle_uses_private_cwd_outside_broad_caller_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from agency_runtime.core.delegation import backends

    caller_home = tmp_path / "home"
    caller_home.mkdir()
    user_host_cli = caller_home / "user-bin" / "codex.exe"
    user_host_cli.parent.mkdir()
    user_host_cli.touch()
    launch_directory = tmp_path / "private-native-launch"
    launch_directory.mkdir()
    observed: dict[str, Any] = {}

    @contextmanager
    def private_launch(*, prefix: str):
        observed["prefix"] = prefix
        yield launch_directory

    def prepare(command: list[str] | tuple[str, ...], **kwargs: Any) -> list[str]:
        observed["prepare_command"] = list(command)
        observed["prepare_current_directory"] = kwargs["current_directory"]
        observed["prepare_forbidden_roots"] = kwargs["forbidden_roots"]
        return [str(user_host_cli), *list(command)[1:]]

    def run(command: list[str], **kwargs: Any) -> SimpleNamespace:
        observed["run_command"] = list(command)
        observed["run_kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout="{}",
            stderr="",
            timed_out=False,
            stdout_truncated=False,
            stderr_truncated=False,
        )

    monkeypatch.chdir(caller_home)
    monkeypatch.setenv(
        "PATH",
        str(user_host_cli.parent) + os.pathsep + os.environ.get("PATH", ""),
    )
    monkeypatch.setattr(native, "private_temporary_directory", private_launch)
    monkeypatch.setattr(native, "prepare_process_argv", prepare)
    monkeypatch.setattr(native, "freeze_process_argv", lambda command, **_kwargs: command)
    monkeypatch.setattr(backends, "run_bounded_process", run)

    result = native.run_native([str(user_host_cli), "plugin", "list"], host="codex")

    assert result.ok is True
    assert observed["prefix"] == "native-codex"
    assert observed["prepare_current_directory"] == launch_directory
    assert caller_home not in observed["prepare_forbidden_roots"]
    assert str(user_host_cli.parent.resolve()) in observed["run_kwargs"]["env"]["PATH"].split(
        os.pathsep
    )
    assert observed["run_kwargs"]["cwd"] == str(launch_directory)


def test_native_host_lifecycle_retains_ambient_repository_poison_boundary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from agency_runtime.core.delegation import backends

    repository = tmp_path / "repository"
    working_tree = repository / "src"
    poisoned_bin = repository / "bin"
    safe_bin = tmp_path / "safe-bin"
    launch_directory = tmp_path / "private-native-launch"
    for directory in (working_tree, poisoned_bin, safe_bin, launch_directory):
        directory.mkdir(parents=True)
    (repository / ".git").mkdir()
    monkeypatch.chdir(working_tree)
    monkeypatch.setenv("PATH", str(poisoned_bin) + os.pathsep + str(safe_bin))
    observed: dict[str, Any] = {}

    @contextmanager
    def private_launch(*, prefix: str):
        del prefix
        yield launch_directory

    def prepare(command: list[str] | tuple[str, ...], **kwargs: Any) -> list[str]:
        observed["forbidden_roots"] = kwargs["forbidden_roots"]
        return [str(safe_bin / "codex.exe"), *list(command)[1:]]

    def run(_command: list[str], **kwargs: Any) -> SimpleNamespace:
        observed["environment"] = kwargs["env"]
        return SimpleNamespace(
            returncode=0,
            stdout="{}",
            stderr="",
            timed_out=False,
            stdout_truncated=False,
            stderr_truncated=False,
        )

    monkeypatch.setattr(native, "private_temporary_directory", private_launch)
    monkeypatch.setattr(native, "prepare_process_argv", prepare)
    monkeypatch.setattr(native, "freeze_process_argv", lambda command, **_kwargs: command)
    monkeypatch.setattr(backends, "run_bounded_process", run)

    assert native.run_native(["codex", "plugin", "list"], host="codex").ok is True
    assert repository.resolve() in observed["forbidden_roots"]
    assert observed["environment"]["PATH"].split(os.pathsep) == [str(safe_bin.resolve())]


def test_bool_field_and_payload_config_direct_branches() -> None:
    assert native._bool_field({"enabled": "active"}, "enabled") is True
    assert native._bool_field({"enabled": "disabled"}, "enabled") is False
    assert native._bool_field({"enabled": "unknown"}, "enabled") is None
    assert native._bool_field({"first": 1, "second": True}, "first", "second") is True

    cfg = AgencyConfig(ollama=OllamaConfig(enabled=False, model=""))
    assert payloads.resolve_install_config(cfg, home_dir=None) is cfg
    assert payloads.effective_judge_budget_seconds(cfg) == cfg.judge.timeout


def test_starter_roster_seeding_is_idempotent() -> None:
    class MemoryRosterStore:
        def __init__(self) -> None:
            self.entries: dict[str, dict[str, Any]] = {}

        def activate_agent_if_missing(self, entry: dict[str, Any]) -> bool:
            slug = str(entry["slug"])
            if slug in self.entries:
                return False
            self.entries[slug] = dict(entry)
            return True

    store = MemoryRosterStore()
    assert installer.seed_starter_roster(store) == len(installer.STARTER_ROSTER)
    assert installer.seed_starter_roster(store) == 0
