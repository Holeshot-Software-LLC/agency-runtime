"""Install residual drift belongs to its resolved targets, not every host."""

from __future__ import annotations

from pathlib import Path

import pytest

from agency_runtime.cli import install_commands
from agency_runtime.cli.main import build_parser
from agency_runtime.core import host_control, installer, runtime_staleness
from agency_runtime.core.config import AgencyConfig

_CURRENT = "b" * 64
_STALE = "a" * 64


@pytest.fixture
def record_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Use real pointer serialization and comparisons inside a temporary namespace."""
    launchers = tmp_path / "launchers"
    launchers.mkdir()
    package_root = tmp_path / "current-package" / "agency_runtime"
    monkeypatch.setattr(runtime_staleness, "private_runtime_directory", lambda _: launchers)
    monkeypatch.setattr(runtime_staleness, "running_runtime_digest", lambda: "")
    monkeypatch.setattr(runtime_staleness, "_running_package_root", lambda: str(package_root))
    monkeypatch.setattr(
        runtime_staleness, "agency_bootstrap_path", lambda: str(package_root / "_bootstrap.py")
    )
    monkeypatch.setattr(runtime_staleness, "source_runtime_drift", lambda _: _CURRENT)

    def record(host: str, digest: str, *, foreign: bool = False) -> None:
        bootstrap = (
            launchers
            / f"runtime-sha256-{digest}"
            / "site-packages"
            / "agency_runtime"
            / "_bootstrap.py"
        )
        with monkeypatch.context() as context:
            if foreign:
                context.setattr(
                    runtime_staleness,
                    "_running_package_root",
                    lambda: str(tmp_path / "foreign-package" / "agency_runtime"),
                )
            assert runtime_staleness.record_installed_runtime(bootstrap, host=host) == digest

    return record


@pytest.mark.parametrize("json_mode", [False, True], ids=["text", "json"])
@pytest.mark.parametrize("foreign", [False, True], ids=["same-package", "foreign-package"])
@pytest.mark.parametrize(
    ("selection", "detected", "stale_hosts", "expected_host"),
    [
        (["--agent", "codex"], ["codex", "openclaw"], ["openclaw"], None),
        (["--agent", "codex"], ["codex", "openclaw"], ["codex"], "codex"),
        (["--agent", "openclaw"], ["codex", "openclaw"], ["codex", "openclaw"], "openclaw"),
        ([], ["codex"], ["openclaw"], None),
        ([], ["codex", "openclaw"], ["openclaw"], "openclaw"),
        ([], [], ["openclaw"], None),
        (["--all"], ["codex"], ["openclaw"], None),
        (["--all"], ["codex", "openclaw"], ["openclaw"], "openclaw"),
    ],
    ids=[
        "unselected-stale-host",
        "selected-stale-host",
        "skip-first-unselected-report",
        "default-resolved-subset",
        "default-all-detected",
        "no-detected-hosts",
        "all-resolved-subset",
        "all-detected",
    ],
)
def test_install_residual_drift_matches_resolved_targets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    record_host,
    json_mode: bool,
    foreign: bool,
    selection: list[str],
    detected: list[str],
    stale_hosts: list[str],
    expected_host: str | None,
) -> None:
    for host in ("codex", "openclaw"):
        record_host(
            host,
            _STALE if host in stale_hosts else _CURRENT,
            foreign=foreign and host in stale_hosts,
        )

    cfg = AgencyConfig()
    emitted: list[dict] = []
    installed: list[str] = []

    def install_hosts(targets, selected_cfg, **_kwargs):
        assert selected_cfg is cfg
        installed.extend(targets)
        return [{"host": host, "ok": True, "complete": True} for host in targets]

    monkeypatch.setattr(installer, "detect_installed_agents", lambda: detected)
    monkeypatch.setattr(installer, "seed_starter_roster", lambda _: 0)
    monkeypatch.setattr(install_commands, "_install_hosts", install_hosts)
    monkeypatch.setattr(
        install_commands, "_installed_config_path", lambda _: tmp_path / "agency.yaml"
    )
    dependencies = install_commands.InstallDependencies(
        load_config=lambda: cfg,
        store_factory=lambda _: object(),
        emit_json=emitted.append,
    )
    # An explicit profile selects the full install path rather than the exact
    # Codex-only prepared refresh, which has its own reporting contract.
    argv = ["install", *selection, "--profile", "standard", "--no-dashboard"]
    if json_mode:
        argv.append("--json")
    args = build_parser().parse_args(argv)

    assert install_commands.cmd_install(args, dependencies=dependencies) == 0
    assert installed == ([args.agent] if args.agent else detected)
    output = capsys.readouterr().out
    if json_mode:
        report = emitted[-1]
        assert report["ok"] is True
        assert report["complete"] is True
        assert [host["host"] for host in report["hosts"]] == installed
        if expected_host is None:
            assert report["runtime_drift"] is None
        else:
            assert report["runtime_drift"]["host"] == expected_host
            assert report["runtime_drift"]["foreign_package"] is foreign
    else:
        assert ("Install finished but" in output) is (expected_host is not None)
        if expected_host is not None:
            assert f"agency install --agent {expected_host}" in output


def test_targeted_install_retains_selected_foreign_package_drift(record_host) -> None:
    record_host("codex", _STALE, foreign=True)

    report = install_commands._cli_install_drift_projection(["codex"])

    assert report is not None
    assert report["host"] == "codex"
    assert report["foreign_package"] is True


def test_install_drift_reporting_failure_remains_advisory(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable():
        raise OSError("pointer unavailable")

    monkeypatch.setattr(runtime_staleness, "cli_install_drift_reports", unavailable)

    assert install_commands._cli_install_drift_projection(["codex"]) is None


def test_global_status_still_reports_unselected_stale_host(
    monkeypatch: pytest.MonkeyPatch,
    record_host,
) -> None:
    record_host("codex", _CURRENT)
    record_host("openclaw", _STALE, foreign=True)
    emitted: list[dict] = []
    monkeypatch.setattr(
        install_commands,
        "_read_master_control_with_broker",
        lambda: ({"enabled": True, "generation": 1, "source": "test"}, "direct"),
    )
    monkeypatch.setattr(
        host_control, "inspect_all_host_statuses", lambda _store, *, global_enabled: []
    )
    monkeypatch.setattr(
        install_commands, "_direct_inference_snapshot", lambda _store, _dependencies: {}
    )
    dependencies = install_commands.InstallDependencies(
        store_factory=lambda _: object(),
        emit_json=emitted.append,
    )

    assert (
        install_commands.cmd_status(
            build_parser().parse_args(["status", "--json"]), dependencies=dependencies
        )
        == 0
    )

    report = emitted[-1]
    assert report["runtime_drift"]["host"] == "openclaw"
    assert [drift["host"] for drift in report["runtime_drift_hosts"]] == ["openclaw"]
    assert report["runtime_drift_hosts"][0]["foreign_package"] is True
