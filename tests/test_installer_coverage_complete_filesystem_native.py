from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import installer
from agency_runtime.core import installer_filesystem as filesystem
from agency_runtime.core import installer_inventory as inventory
from agency_runtime.core import installer_native as native
from agency_runtime.core import installer_payloads as payloads
from agency_runtime.core.config import AgencyConfig, OllamaConfig
from agency_runtime.core.installer_contracts import (
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
            {"plugin.py": "managed"},
            host="codex",
            dry_run=False,
            home_dir=tmp_path,
        )

    assert sentinel.read_text(encoding="utf-8") == "original"


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
