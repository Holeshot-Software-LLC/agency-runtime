"""Staged is what we wrote; wired is what runs. Only the second can block a turn.

These tests exist because `agency status` reported a healthy install while
Claude was invoking a projection from before the Job B deletion — the files were
staged, the host's plugin cache was never refreshed, and nothing anywhere said
so.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agency_runtime.core import host_wiring_drift as subject
from agency_runtime.core.host_wiring_drift import claude_host_wiring, host_wiring

OLD = "3790d88f054d1413b796d4991ce9fb94a9e5e4233f4251a91825a16c4afbd099"
NEW = "4841b1e8ec85dbeb30821e2c1c32400ce42c8b075f65f7a0da6e8dd54401c750"


@pytest.fixture
def private_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Treat the fixture root as ACL-private, the way a real host directory is."""

    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_args, **_kwargs: True)


def _hooks_payload(projection: str) -> str:
    command = (
        rf"C:\Python313\python.exe -I -S C:\Users\x\.agency-runtime\launchers"
        rf"\runtime-sha256-{projection}\site-packages\agency_runtime\_bootstrap.py"
    )
    return json.dumps({"hooks": {"PreToolUse": [{"command": command}]}}, indent=2)


def _stage(agency_home: Path, projection: str) -> Path:
    path = (
        agency_home
        / "marketplaces"
        / "claude"
        / "plugins"
        / "agency-preflight"
        / "hooks"
        / "hooks.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_hooks_payload(projection), encoding="utf-8")
    return path


def _register(claude_home: Path, *install_paths: Path) -> Path:
    path = claude_home / "plugins" / "installed_plugins.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "plugins": {
                    "agency-preflight@agency-runtime": [
                        {
                            "scope": "user",
                            "installPath": str(install_path),
                            "version": install_path.name,
                        }
                        for install_path in install_paths
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _wire(
    claude_home: Path,
    projection: str,
    *,
    version: str = "0.1.0",
    register: bool = True,
) -> Path:
    path = (
        claude_home
        / "plugins"
        / "cache"
        / "agency-runtime"
        / "agency-preflight"
        / version
        / "hooks"
        / "hooks.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_hooks_payload(projection), encoding="utf-8")
    if register:
        _register(claude_home, path.parent.parent)
    return path


def test_a_host_running_what_was_staged_is_wired(tmp_path: Path, private_root: None) -> None:
    _stage(tmp_path / "agency", NEW)
    _wire(tmp_path / "claude", NEW)

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.wired is True
    assert result.status == "wired"
    assert result.reason_code == "wired"
    assert result.reason == ""
    assert result.staged_projection == NEW


def test_the_2026_08_10_failure_is_detected(tmp_path: Path, private_root: None) -> None:
    """Staged the new projection, host still invoking the pre-deletion one."""

    _stage(tmp_path / "agency", NEW)
    _wire(tmp_path / "claude", OLD)

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.wired is False
    assert result.status == "drift"
    assert result.reason_code == "projection_mismatch"
    assert result.staged_projection == NEW
    assert result.wired_projection == OLD
    assert "staged and wired projection identities differ" in result.reason


def test_an_absent_measured_wiring_file_stays_unavailable_without_inference(
    tmp_path: Path,
    private_root: None,
) -> None:
    _stage(tmp_path / "agency", NEW)

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.wired is False
    assert result.status == "unavailable"
    assert result.reason_code == "wired_missing"
    assert result.wired_projection == ""
    assert result.reason == "no wired hook command was observed at the measured location"
    assert "installed" not in result.reason


def test_nothing_staged_is_reported_rather_than_called_wired(
    tmp_path: Path,
    private_root: None,
) -> None:
    _wire(tmp_path / "claude", OLD)

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.wired is False
    assert result.status == "unavailable"
    assert result.reason_code == "staged_missing"
    assert "nothing is staged" in result.reason


def test_the_registered_cache_binding_wins_over_a_newer_unregistered_directory(
    tmp_path: Path,
    private_root: None,
) -> None:
    """Cache recency is not evidence of which plugin version Claude actually loads."""

    _stage(tmp_path / "agency", NEW)
    registered = _wire(tmp_path / "claude", OLD, version="0.1.0-claude.aaaaaaaaaaaa")
    unregistered = _wire(
        tmp_path / "claude",
        NEW,
        version="0.1.0-claude.bbbbbbbbbbbb",
        register=False,
    )
    os.utime(registered, (1_600_000_000, 1_600_000_000))
    os.utime(unregistered, (1_700_000_000, 1_700_000_000))

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.status == "drift"
    assert result.wired_projection == OLD
    assert result.wired_path == str(registered)


def test_multiple_registered_bindings_are_ambiguous(
    tmp_path: Path,
    private_root: None,
) -> None:
    _stage(tmp_path / "agency", NEW)
    first = _wire(tmp_path / "claude", NEW, version="first", register=False)
    second = _wire(tmp_path / "claude", NEW, version="second", register=False)
    _register(tmp_path / "claude", first.parent.parent, second.parent.parent)

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.status == "unavailable"
    assert result.reason_code == "wired_ambiguous"
    assert result.wired_state == "ambiguous"


def test_an_invalid_registered_install_path_is_ambiguous(
    tmp_path: Path,
    private_root: None,
) -> None:
    _stage(tmp_path / "agency", NEW)
    outside = tmp_path / "outside-cache"
    _register(tmp_path / "claude", outside)

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.status == "unavailable"
    assert result.reason_code == "wired_ambiguous"
    assert result.wired_state == "ambiguous"


def test_an_invalid_installed_plugin_registry_is_ambiguous(
    tmp_path: Path,
    private_root: None,
) -> None:
    _stage(tmp_path / "agency", NEW)
    registry = tmp_path / "claude" / "plugins" / "installed_plugins.json"
    registry.parent.mkdir(parents=True)
    registry.write_text("{not-json", encoding="utf-8")

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.status == "unavailable"
    assert result.reason_code == "wired_ambiguous"
    assert result.wired_state == "ambiguous"


def test_an_untrusted_installed_plugin_registry_is_unavailable(
    tmp_path: Path,
    private_root: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stage(tmp_path / "agency", NEW)
    _wire(tmp_path / "claude", NEW)
    monkeypatch.setattr(
        subject,
        "storage_file_is_trusted",
        lambda path, **_kwargs: path.name != "installed_plugins.json",
    )

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.status == "unavailable"
    assert result.reason_code == "wired_untrusted"
    assert result.wired_state == "untrusted"


def test_an_unreadable_installed_plugin_registry_is_unavailable(
    tmp_path: Path,
    private_root: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stage(tmp_path / "agency", NEW)
    _wire(tmp_path / "claude", NEW)
    monkeypatch.setattr(
        subject,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("denied")),
    )

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.status == "unavailable"
    assert result.reason_code == "wired_unreadable"
    assert result.wired_state == "unreadable"


def test_two_projections_in_one_wiring_file_is_refused(
    tmp_path: Path,
    private_root: None,
) -> None:
    """A file naming two launchers is broken; picking a winner would hide that."""

    _stage(tmp_path / "agency", NEW)
    path = _wire(tmp_path / "claude", NEW)
    path.write_text(
        _hooks_payload(NEW).replace("}", "") + _hooks_payload(OLD),
        encoding="utf-8",
    )

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.wired is False
    assert result.status == "unavailable"
    assert result.reason_code == "wired_ambiguous"
    assert result.wired_state == "ambiguous"
    assert result.wired_projection == ""


def test_a_directory_other_accounts_can_write_is_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_args, **_kwargs: False)
    _stage(tmp_path / "agency", NEW)
    _wire(tmp_path / "claude", NEW)

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.wired is False
    assert result.status == "unavailable"
    assert result.reason_code == "staged_untrusted"


def test_an_unimplemented_host_is_not_measured_never_unwired() -> None:
    result = host_wiring("codex")

    assert result.measurement_status == "not_measured"
    assert result.status == "not_measured"
    assert result.reason_code == "host_not_measured"
    assert result.wired is False
    assert "not measured" in result.reason
    assert "unwired" not in result.reason


def test_an_unreadable_file_has_a_stable_unavailable_reason(
    tmp_path: Path,
    private_root: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stage(tmp_path / "agency", NEW)
    _wire(tmp_path / "claude", NEW)
    monkeypatch.setattr(
        subject,
        "read_bounded_regular_file_prefix",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("denied")),
    )

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.status == "unavailable"
    assert result.reason_code == "staged_unreadable"
    assert result.staged_state == "unreadable"
