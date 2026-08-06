from __future__ import annotations

import json
from pathlib import Path

import pytest

from agency_runtime.core import runtime_staleness
from agency_runtime.core.launcher_bootstrap import runtime_digest_for_bootstrap

_DIGEST_A = "a" * 64
_DIGEST_B = "b" * 64


def _projection_bootstrap(digest: str) -> str:
    return str(
        Path("/private/launchers")
        / f"runtime-sha256-{digest}"
        / "site-packages"
        / "agency_runtime"
        / "_bootstrap.py"
    )


@pytest.fixture
def pointer_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect the advisory pointer away from the operator's real runtime."""

    target = tmp_path / "current.json"
    monkeypatch.setattr(runtime_staleness, "_pointer_path", lambda: target)
    return target


def test_projection_digest_is_read_from_the_directory_name() -> None:
    assert runtime_digest_for_bootstrap(_projection_bootstrap(_DIGEST_A)) == _DIGEST_A


@pytest.mark.parametrize(
    "path",
    [
        "/usr/lib/site-packages/agency_runtime/_bootstrap.py",
        "/private/launchers/runtime-sha256-short/site-packages/agency_runtime/_bootstrap.py",
        "/private/launchers/not-a-runtime/site-packages/agency_runtime/_bootstrap.py",
    ],
)
def test_non_projection_paths_have_no_digest(path: str) -> None:
    assert runtime_digest_for_bootstrap(path) == ""


def test_pointer_round_trips_the_published_digest(pointer_root: Path) -> None:
    recorded = runtime_staleness.record_installed_runtime(
        _projection_bootstrap(_DIGEST_A),
        host="claude",
    )

    assert recorded == _DIGEST_A
    assert runtime_staleness.installed_runtime_pointer() == (_DIGEST_A, "claude")


def test_non_projection_install_records_no_pointer(pointer_root: Path) -> None:
    """A pointer no hook could match would make every later hook warn falsely."""

    recorded = runtime_staleness.record_installed_runtime("/usr/lib/agency_runtime/_bootstrap.py")

    assert recorded == ""
    assert not pointer_root.exists()
    assert runtime_staleness.installed_runtime_pointer() == ("", "")


def test_drift_is_reported_when_the_running_projection_is_older(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
) -> None:
    runtime_staleness.record_installed_runtime(_projection_bootstrap(_DIGEST_B), host="claude")
    monkeypatch.setattr(runtime_staleness, "running_runtime_digest", lambda: _DIGEST_A)

    drift = runtime_staleness.runtime_staleness()

    assert drift is not None
    assert drift.running_digest == _DIGEST_A
    assert drift.installed_digest == _DIGEST_B
    assert "agency install --agent claude" in drift.message


def test_matching_projection_reports_no_drift(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
) -> None:
    runtime_staleness.record_installed_runtime(_projection_bootstrap(_DIGEST_A), host="claude")
    monkeypatch.setattr(runtime_staleness, "running_runtime_digest", lambda: _DIGEST_A)

    assert runtime_staleness.runtime_staleness() is None


def test_source_run_without_a_projection_reports_no_drift(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
) -> None:
    """Running from a checkout is ordinary, not drift."""

    runtime_staleness.record_installed_runtime(_projection_bootstrap(_DIGEST_B), host="claude")
    monkeypatch.setattr(runtime_staleness, "running_runtime_digest", lambda: "")

    assert runtime_staleness.runtime_staleness() is None


def test_missing_pointer_reports_no_drift(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
) -> None:
    monkeypatch.setattr(runtime_staleness, "running_runtime_digest", lambda: _DIGEST_A)

    assert runtime_staleness.runtime_staleness() is None


@pytest.mark.parametrize(
    "payload",
    [
        "{}",
        json.dumps({"schema": "wrong", "schema_version": 1, "runtime_digest": _DIGEST_A}),
        json.dumps(
            {
                "schema": "agency-runtime.installed-launcher-runtime",
                "schema_version": 99,
                "runtime_digest": _DIGEST_A,
            }
        ),
        json.dumps(
            {
                "schema": "agency-runtime.installed-launcher-runtime",
                "schema_version": 1,
                "runtime_digest": "not-a-digest",
            }
        ),
        "not json at all",
    ],
)
def test_malformed_pointer_is_ignored_rather_than_trusted(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
    payload: str,
) -> None:
    """The pointer is advisory; a bad one must not warn or raise."""

    pointer_root.write_text(payload, encoding="utf-8")
    monkeypatch.setattr(runtime_staleness, "running_runtime_digest", lambda: _DIGEST_A)

    assert runtime_staleness.installed_runtime_pointer() == ("", "")
    assert runtime_staleness.runtime_staleness() is None


def test_host_falls_back_to_the_recorded_pointer_host(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
) -> None:
    runtime_staleness.record_installed_runtime(_projection_bootstrap(_DIGEST_B), host="codex")
    monkeypatch.setattr(runtime_staleness, "running_runtime_digest", lambda: _DIGEST_A)

    drift = runtime_staleness.runtime_staleness()

    assert drift is not None
    assert "agency install --agent codex" in drift.message
