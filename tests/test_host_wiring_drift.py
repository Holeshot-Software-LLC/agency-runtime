"""Staged is what we wrote; wired is what runs. Only the second can block a turn.

These tests exist because `agency status` reported a healthy install while
Claude was invoking a projection from before the Job B deletion — the files were
staged, the host's plugin cache was never refreshed, and nothing anywhere said
so.
"""

from __future__ import annotations

import json
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


def _wire(claude_home: Path, projection: str, *, version: str = "0.1.0") -> Path:
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
    return path


def test_a_host_running_what_was_staged_is_wired(tmp_path: Path, private_root: None) -> None:
    _stage(tmp_path / "agency", NEW)
    _wire(tmp_path / "claude", NEW)

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.wired is True
    assert result.reason == ""
    assert result.staged_projection == NEW


def test_the_2026_08_10_failure_is_detected(tmp_path: Path, private_root: None) -> None:
    """Staged the new projection, host still invoking the pre-deletion one."""

    _stage(tmp_path / "agency", NEW)
    _wire(tmp_path / "claude", OLD)

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.wired is False
    assert result.staged_projection == NEW
    assert result.wired_projection == OLD
    assert "plugin cache was never refreshed" in result.reason


def test_a_host_that_never_installed_the_plugin_is_not_wired(
    tmp_path: Path,
    private_root: None,
) -> None:
    _stage(tmp_path / "agency", NEW)

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.wired is False
    assert result.wired_projection == ""
    assert "never installed" in result.reason


def test_nothing_staged_is_reported_rather_than_called_wired(
    tmp_path: Path,
    private_root: None,
) -> None:
    _wire(tmp_path / "claude", OLD)

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.wired is False
    assert "nothing is staged" in result.reason


def test_the_newest_cached_version_directory_is_the_one_read(
    tmp_path: Path,
    private_root: None,
) -> None:
    """A content-derived version means the cache accumulates version directories."""

    _stage(tmp_path / "agency", NEW)
    stale = _wire(tmp_path / "claude", OLD, version="0.1.0+claude.aaaaaaaaaaaa")
    fresh = _wire(tmp_path / "claude", NEW, version="0.1.0+claude.bbbbbbbbbbbb")
    import os

    os.utime(stale, (1_600_000_000, 1_600_000_000))
    os.utime(fresh, (1_700_000_000, 1_700_000_000))

    result = claude_host_wiring(agency_home=tmp_path / "agency", claude_home=tmp_path / "claude")

    assert result.wired is True
    assert result.wired_path == str(fresh)


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


def test_an_unimplemented_host_says_so_rather_than_guessing_a_path() -> None:
    with pytest.raises(ValueError, match="not implemented"):
        host_wiring("codex")
