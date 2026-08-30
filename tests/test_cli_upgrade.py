"""CLI contracts for version inspection and attended update planning."""

from __future__ import annotations

import json

import pytest

from agency_runtime.cli import upgrade_commands as subject
from agency_runtime.cli.main import main as cli_main

_SHA = "d" * 40


def _identity() -> dict[str, object]:
    return {
        "package_version": "1.2.3",
        "build_identity": f"1.2.3+g{_SHA[:12]}",
        "source_revision": _SHA,
        "source_branch": "main",
        "source_dirty": False,
        "install_kind": "vcs-package",
        "official_repository": True,
    }


def _status() -> dict[str, object]:
    return {
        "schema_version": "agency.update.v1",
        "installed": _identity(),
        "selector": {
            "kind": "version",
            "value": "1.3.0",
            "ref": "v1.3.0",
            "key": "version:v1.3.0",
        },
        "checked": True,
        "cache_hit": False,
        "stale": False,
        "checking": False,
        "checked_at": "2026-07-28T00:00:00+00:00",
        "status": "update_available",
        "update_available": True,
        "target": {
            "kind": "version",
            "label": "1.3.0",
            "version": "1.3.0",
            "ref": "v1.3.0",
            "commit_sha": "e" * 40,
            "url": f"https://github.com/Holeshot-Software-LLC/agency-runtime/commit/{'e' * 40}",
            "published_at": None,
        },
        "error": None,
        "command": "agency upgrade --version 1.3.0",
    }


def test_detailed_version_json_reports_build_provenance(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(subject, "installed_version_snapshot", _identity)

    assert cli_main(["version", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "agency.version.v1"
    assert payload["source_revision"] == _SHA
    assert payload["install_kind"] == "vcs-package"


def test_version_target_option_implicitly_checks_without_mutation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    captured: dict[str, object] = {}

    def check(**kwargs):
        captured.update(kwargs)
        return _status()

    monkeypatch.setattr(subject, "check_for_update", check)

    assert cli_main(["version", "--version", "1.3.0", "--json"]) == 0

    assert captured["version"] == "1.3.0"
    assert json.loads(capsys.readouterr().out)["target"]["commit_sha"] == "e" * 40


def test_version_timeout_option_implies_a_bounded_check(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    captured: dict[str, object] = {}

    def check(**kwargs):
        captured.update(kwargs)
        return _status()

    monkeypatch.setattr(subject, "check_for_update", check)

    assert cli_main(["version", "--timeout", "2.5", "--json"]) == 0

    assert captured["timeout"] == 2.5
    assert json.loads(capsys.readouterr().out)["status"] == "update_available"


def test_upgrade_prints_an_attended_exact_sha_plan_without_executing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(subject, "check_for_update", lambda **_kwargs: _status())
    monkeypatch.setattr(
        subject,
        "attended_upgrade_plan",
        lambda _status: {
            "mode": "attended-external",
            "mutation_performed": False,
            "commands": [
                {
                    "argv": ["safe-python", "-I", "-m", "pip", f"source@{'e' * 40}"],
                    "display": f"safe-python -I -m pip source@{'e' * 40}",
                }
            ],
            "reason": "review and run the exact immutable plan",
        },
    )

    assert cli_main(["upgrade", "--version", "1.3.0", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["plan"]["mutation_performed"] is False
    assert payload["plan"]["mode"] == "attended-external"
    command = payload["plan"]["commands"][0]
    assert f"@{'e' * 40}" in command["display"]
    assert "@v1.3.0" not in command["display"]


def test_upgrade_returns_failure_when_no_safe_installer_plan_exists(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(subject, "check_for_update", lambda **_kwargs: _status())
    monkeypatch.setattr(
        subject,
        "attended_upgrade_plan",
        lambda _status: {
            "mode": "unavailable",
            "mutation_performed": False,
            "commands": [],
            "reason": "no trusted installer",
        },
    )

    assert cli_main(["upgrade", "--version", "1.3.0", "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["plan"]["mode"] == "unavailable"


def test_upgrade_check_reuses_fresh_cache_unless_refresh_is_explicit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    refreshes: list[bool] = []

    def check(**kwargs):
        refreshes.append(kwargs["refresh"])
        return _status()

    monkeypatch.setattr(subject, "check_for_update", check)

    assert cli_main(["upgrade", "check", "--json"]) == 0
    capsys.readouterr()
    assert cli_main(["upgrade", "check", "--refresh", "--json"]) == 0
    capsys.readouterr()

    assert refreshes == [False, True]


def test_refresh_and_cached_modes_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit) as raised:
        cli_main(["upgrade", "--refresh", "--cached"])

    assert raised.value.code == 2
