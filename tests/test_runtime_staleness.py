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
    """Redirect the advisory pointers away from the operator's real runtime.

    The whole launcher directory moves, not just the legacy file, because
    pointers are now per host and are discovered by scanning that directory.
    """

    launchers = tmp_path / "launchers"
    launchers.mkdir()
    monkeypatch.setattr(runtime_staleness, "private_runtime_directory", lambda _: launchers)
    return launchers / "current.json"


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


_CHECKOUT_ROOT = str(Path("/checkout") / "agency_runtime")
_TOOL_ROOT = str(Path("/tools") / "agency-runtime" / "agency_runtime")


@pytest.fixture
def in_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run as an ordinary CLI out of the checkout package."""

    monkeypatch.setattr(runtime_staleness, "running_runtime_digest", lambda: "")
    monkeypatch.setattr(runtime_staleness, "_running_package_root", lambda: _CHECKOUT_ROOT)
    monkeypatch.setattr(
        runtime_staleness,
        "agency_bootstrap_path",
        lambda: str(Path(_CHECKOUT_ROOT) / "_bootstrap.py"),
    )


def _record(pointer_root: Path, digest: str, source_root: str, host: str = "claude") -> None:
    payload = {
        "schema": "agency-runtime.installed-launcher-runtime",
        "schema_version": 1,
        "runtime_digest": digest,
        "host": host,
    }
    if source_root:
        payload["source_root"] = source_root
    pointer_root.write_text(json.dumps(payload), encoding="utf-8")


def test_cli_drift_is_reported_when_source_moves_ahead_in_the_same_package(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
    in_checkout: None,
) -> None:
    _record(pointer_root, _DIGEST_A, _CHECKOUT_ROOT)
    monkeypatch.setattr(runtime_staleness, "source_runtime_drift", lambda _path: _DIGEST_B)

    drift = runtime_staleness.cli_install_drift()

    assert drift is not None
    assert drift.foreign_package is False
    assert drift.source_digest == _DIGEST_B
    assert drift.installed_digest == _DIGEST_A
    assert _DIGEST_B[:12] in drift.message
    assert "--agent claude" in drift.message


def test_cli_drift_is_silent_when_source_matches_the_install(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
    in_checkout: None,
) -> None:
    _record(pointer_root, _DIGEST_A, _CHECKOUT_ROOT)
    monkeypatch.setattr(runtime_staleness, "source_runtime_drift", lambda _path: _DIGEST_A)

    assert runtime_staleness.cli_install_drift() is None


def test_a_foreign_install_is_named_rather_than_digest_compared(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
    in_checkout: None,
) -> None:
    """Cross-environment digests never agree, so comparing them always fires."""

    _record(pointer_root, _DIGEST_A, _TOOL_ROOT)

    def _unreachable(_path: object) -> str:
        raise AssertionError("a foreign package must not be digest-compared")

    monkeypatch.setattr(runtime_staleness, "source_runtime_drift", _unreachable)

    drift = runtime_staleness.cli_install_drift()

    assert drift is not None
    assert drift.foreign_package is True
    assert _TOOL_ROOT in drift.message
    assert "different package" in drift.message
    # A digest it could not meaningfully compute must not be implied.
    assert drift.source_digest == ""


def test_package_roots_compare_the_way_the_filesystem_does(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
    in_checkout: None,
) -> None:
    """A differently-spelled but identical root is not a foreign package."""

    _record(pointer_root, _DIGEST_A, str(Path(_CHECKOUT_ROOT) / "." / ""))
    monkeypatch.setattr(runtime_staleness, "source_runtime_drift", lambda _path: _DIGEST_A)

    assert runtime_staleness.cli_install_drift() is None


def test_a_pointer_without_a_source_root_is_not_attributed(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
    in_checkout: None,
) -> None:
    """Legacy pointers support no trustworthy comparison, so stay silent."""

    _record(pointer_root, _DIGEST_A, "")
    monkeypatch.setattr(runtime_staleness, "source_runtime_drift", lambda _path: _DIGEST_B)

    assert runtime_staleness.cli_install_drift() is None


def test_cli_drift_is_silent_inside_a_frozen_projection(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
) -> None:
    """A hook would only ever hash itself, so it must never report this."""

    _record(pointer_root, _DIGEST_A, _CHECKOUT_ROOT)
    monkeypatch.setattr(runtime_staleness, "running_runtime_digest", lambda: _DIGEST_B)

    assert runtime_staleness.cli_install_drift() is None


def test_cli_drift_is_silent_without_a_recorded_pointer(
    pointer_root: Path,
    in_checkout: None,
) -> None:
    assert runtime_staleness.cli_install_drift() is None


def test_cli_drift_is_silent_when_the_projection_cannot_be_planned(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
    in_checkout: None,
) -> None:
    _record(pointer_root, _DIGEST_A, _CHECKOUT_ROOT)
    monkeypatch.setattr(runtime_staleness, "source_runtime_drift", lambda _path: "")

    assert runtime_staleness.cli_install_drift() is None


def test_recorded_pointer_carries_the_running_package_root(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
) -> None:
    monkeypatch.setattr(runtime_staleness, "_running_package_root", lambda: _CHECKOUT_ROOT)

    runtime_staleness.record_installed_runtime(
        _projection_bootstrap(_DIGEST_A),
        host="claude",
    )

    stored = json.loads((pointer_root.parent / "current-claude.json").read_text(encoding="utf-8"))
    assert stored["source_root"] == _CHECKOUT_ROOT
    assert stored["runtime_digest"] == _DIGEST_A
    # A named host must not write the shared pointer, or one host's install
    # would keep answering for another's.
    assert not pointer_root.exists()


def test_one_hosts_install_never_answers_for_another(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
    in_checkout: None,
) -> None:
    """The exact defect: codex current, claude behind, on the same box.

    A single shared pointer could not express this. It reported codex as stale
    under claude's digest -- and named `--agent claude` as the remedy, because
    that is whose record it was carrying -- immediately after a fully
    successful codex install.
    """

    runtime_staleness.record_installed_runtime(_projection_bootstrap(_DIGEST_A), host="claude")
    runtime_staleness.record_installed_runtime(_projection_bootstrap(_DIGEST_B), host="codex")
    monkeypatch.setattr(runtime_staleness, "source_runtime_drift", lambda _path: _DIGEST_B)

    reports = runtime_staleness.cli_install_drift_reports()

    assert [report.host for report in reports] == ["claude"]
    assert reports[0].installed_digest == _DIGEST_A
    assert "--agent claude" in reports[0].message
    assert runtime_staleness.installed_runtime_pointer("codex") == (_DIGEST_B, "codex")
    assert runtime_staleness.installed_runtime_pointer("claude") == (_DIGEST_A, "claude")


def test_every_stale_host_is_reported_not_just_the_first(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
    in_checkout: None,
) -> None:
    runtime_staleness.record_installed_runtime(_projection_bootstrap(_DIGEST_A), host="claude")
    runtime_staleness.record_installed_runtime(_projection_bootstrap(_DIGEST_A), host="codex")
    monkeypatch.setattr(runtime_staleness, "source_runtime_drift", lambda _path: _DIGEST_B)

    reports = runtime_staleness.cli_install_drift_reports()

    assert sorted(report.host for report in reports) == ["claude", "codex"]
    # The single-report accessor stays a view onto the first of several, never
    # a claim that it is the only one.
    assert runtime_staleness.cli_install_drift() == reports[0]


def test_a_hook_compares_against_its_own_hosts_pointer(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
) -> None:
    """A claude hook must not be judged by whatever host installed last."""

    runtime_staleness.record_installed_runtime(_projection_bootstrap(_DIGEST_A), host="claude")
    runtime_staleness.record_installed_runtime(_projection_bootstrap(_DIGEST_B), host="codex")
    monkeypatch.setattr(runtime_staleness, "running_runtime_digest", lambda: _DIGEST_A)

    assert runtime_staleness.runtime_staleness(host="claude") is None

    codex_drift = runtime_staleness.runtime_staleness(host="codex")

    assert codex_drift is not None
    assert codex_drift.installed_digest == _DIGEST_B
    assert "--agent codex" in codex_drift.message


def test_a_legacy_pointer_still_answers_for_the_host_it_named(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
    in_checkout: None,
) -> None:
    """Existing installations must not silently lose their recorded state."""

    _record(pointer_root, _DIGEST_A, _CHECKOUT_ROOT, host="claude")
    monkeypatch.setattr(runtime_staleness, "source_runtime_drift", lambda _path: _DIGEST_B)

    assert runtime_staleness.installed_runtime_pointer("claude") == (_DIGEST_A, "claude")
    # ...and says nothing about a host it never described.
    assert runtime_staleness.installed_runtime_pointer("codex") == ("", "")
    assert [report.host for report in runtime_staleness.cli_install_drift_reports()] == ["claude"]


def test_a_per_host_record_supersedes_the_legacy_one(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
    in_checkout: None,
) -> None:
    _record(pointer_root, _DIGEST_A, _CHECKOUT_ROOT, host="claude")
    runtime_staleness.record_installed_runtime(_projection_bootstrap(_DIGEST_B), host="claude")

    assert runtime_staleness.installed_runtime_pointer("claude") == (_DIGEST_B, "claude")
    assert len(runtime_staleness.cli_install_drift_reports()) <= 1


def test_a_foreign_package_is_never_digest_compared_for_any_host(
    monkeypatch: pytest.MonkeyPatch,
    pointer_root: Path,
    in_checkout: None,
) -> None:
    """Planning hashes the whole closure; a foreign root must short-circuit."""

    _record(pointer_root, _DIGEST_A, _TOOL_ROOT, host="hermes")

    def _unreachable(_path: object) -> str:
        raise AssertionError("a foreign package must not be digest-compared")

    monkeypatch.setattr(runtime_staleness, "source_runtime_drift", _unreachable)

    reports = runtime_staleness.cli_install_drift_reports()

    assert [report.host for report in reports] == ["hermes"]
    assert reports[0].foreign_package is True
