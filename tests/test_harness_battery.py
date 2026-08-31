"""AR-337: the change-triggered harness canary battery.

The battery's whole value is running exactly when a harness changed and
saying loudly what it found, so these tests pin the change gate, the
outcome mapping (including the distinct attended-trust status), the
content-free posture counts, and the private receipt/fingerprint trail.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import harness_battery as subject


def _completed(stdout: str = "", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, returncode=returncode, stderr="")


def _resolver(mapping: dict[str, str]):
    return lambda name: mapping.get(name)


@pytest.fixture(autouse=True)
def _fast_settle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subject.time, "sleep", lambda _seconds: None)


def _passthrough_preparer(command: tuple[str, ...], resolver) -> tuple[str, ...]:
    located = resolver(command[0]) or command[0]
    return (located, *command[1:])


def test_version_observation_is_first_line_bounded_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "_prepare_version_argv", _passthrough_preparer)
    runner_calls: list[tuple[str, ...]] = []

    def runner(command: tuple[str, ...], *, timeout: float) -> SimpleNamespace:
        runner_calls.append(tuple(command))
        return _completed("codex-cli 0.151.0\nextra noise\n")

    observed = subject.observe_harness_version(
        "codex",
        resolver=_resolver({"codex": "/bin/codex"}),
        runner=runner,
    )

    assert observed == "codex-cli 0.151.0"
    assert runner_calls == [("/bin/codex", "--version")]
    assert subject.observe_harness_version("codex", resolver=_resolver({}), runner=runner) == ""
    assert (
        subject.observe_harness_version(
            "codex",
            resolver=_resolver({"codex": "/bin/codex"}),
            runner=lambda *a, **k: _completed("boom", returncode=1),
        )
        == ""
    )


def test_version_observation_executes_the_prepared_argv_not_the_bare_command() -> None:
    """AR-340: a Windows npm shim is unlaunchable bare; the observer must run
    whatever the shim-aware preparer resolved (native exe, or node + script)."""

    runner_calls: list[tuple[str, ...]] = []

    def runner(command: tuple[str, ...], *, timeout: float) -> SimpleNamespace:
        runner_calls.append(tuple(command))
        return _completed("2.1.250 (Claude Code)")

    version, reason = subject.observe_harness_version_detail(
        "claude",
        resolver=_resolver({"claude": r"C:\agency-cli\claude.cmd"}),
        runner=runner,
        preparer=lambda command, resolver: (
            r"C:\agency-cli\node.exe",
            r"C:\agency-cli\node_modules\@anthropic-ai\claude-code\cli.js",
            *command[1:],
        ),
    )

    assert (version, reason) == ("2.1.250 (Claude Code)", "")
    assert runner_calls == [
        (
            r"C:\agency-cli\node.exe",
            r"C:\agency-cli\node_modules\@anthropic-ai\claude-code\cli.js",
            "--version",
        )
    ]


def test_version_observation_detail_names_every_skip_reason() -> None:
    detail = subject.observe_harness_version_detail
    resolver = _resolver({"claude": r"C:\agency-cli\claude.cmd"})

    assert detail("zcode", resolver=resolver) == ("", "unsupported battery harness")
    assert detail("claude", resolver=_resolver({})) == ("", "command not discovered")

    def raising_preparer(command, resolver):
        raise OSError("unlaunchable shim")

    assert detail("claude", resolver=resolver, preparer=raising_preparer) == (
        "",
        "version command is not launchable (OSError)",
    )
    assert detail(
        "claude",
        resolver=resolver,
        runner=lambda *a, **k: (_ for _ in ()).throw(subprocess.TimeoutExpired("claude", 30)),
        preparer=_passthrough_preparer,
    ) == ("", "version command failed (TimeoutExpired)")
    assert detail(
        "claude",
        resolver=resolver,
        runner=lambda *a, **k: _completed("boom", returncode=7),
        preparer=_passthrough_preparer,
    ) == ("", "version command exited 7")
    assert detail(
        "claude",
        resolver=resolver,
        runner=lambda *a, **k: _completed("   \n"),
        preparer=_passthrough_preparer,
    ) == ("", "version output was empty")


def test_changed_harnesses_trigger_only_on_observed_version_drift() -> None:
    fingerprints = {
        "schema": subject.BATTERY_SCHEMA,
        "harnesses": {
            "codex": {"proven_version": "codex-cli 0.151.0"},
            "claude": {"proven_version": "2.1.251 (Claude Code)"},
        },
    }
    observed = {
        "codex": "codex-cli 0.152.0",
        "claude": "2.1.251 (Claude Code)",
        "hermes": "Hermes Agent v0.20.6",
        "openclaw": "",
    }

    changed = subject.changed_harnesses(observed, fingerprints)

    # codex drifted, hermes has no baseline, claude matches, and the
    # unobservable openclaw never triggers a drill.
    assert changed == ("codex", "hermes")


def test_posture_counts_group_writable_entries_content_free(
    tmp_path: Path,
) -> None:
    package = tmp_path / "node_modules" / "openclaw"
    nested = package / "dist"
    nested.mkdir(parents=True)
    binary = package / "cli.js"
    binary.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    os.chmod(nested, 0o775)
    os.chmod(package, 0o755)
    launcher = tmp_path / "bin" / "openclaw"
    launcher.parent.mkdir()
    launcher.symlink_to(binary)

    counts = subject.posture_regressions(
        "openclaw",
        resolver=_resolver({"openclaw": str(launcher)}),
    )

    assert counts["group_writable"] == 1
    assert counts["other_writable"] == 0
    assert counts["scanned"] >= 3
    assert set(counts) == {"scanned", "group_writable", "other_writable"}


def test_canary_outcomes_map_trust_refusal_to_attended_status() -> None:
    assert subject._canary_outcome({"canary_passed": True}) == ("passed", "")
    assert subject._canary_outcome(
        {
            "canary_passed": False,
            "invocation": {"failure_reason": "codex_hook_trust_not_ready"},
        }
    ) == ("attended_trust_required", "codex_hook_trust_not_ready")
    assert subject._canary_outcome(
        {
            "canary_passed": False,
            "invocation": {"failure_reason": "codex_exec_timed_out"},
        }
    ) == ("failed", "codex_exec_timed_out")


class _ActivityStore:
    def __init__(self, snapshots: list[dict[str, list[dict[str, Any]]]]) -> None:
        self._snapshots = snapshots

    def recent_runtime_activity(self, *, limit: int = 200) -> dict[str, Any]:
        del limit
        return self._snapshots.pop(0)


def test_ordinary_battery_requires_staffing_complete_store_delta() -> None:
    before = {"runs": [], "routing": [], "specialists": [], "preflight_failures": []}
    after_staffed = {
        "runs": [{"id": "r1"}],
        "routing": [{"id": "d1"}],
        "specialists": [{"id": "s1"}],
        "preflight_failures": [],
    }

    outcome, detail = subject._run_ordinary_battery(
        "hermes",
        store=_ActivityStore([dict(before), after_staffed]),
        resolver=_resolver({"hermes": "/bin/hermes"}),
        runner=lambda command, *, timeout: _completed("done"),
    )

    assert outcome == "passed"
    assert detail["new_row_counts"] == {"runs": 1, "routing": 1, "specialists": 1}

    after_failed = {
        "runs": [{"id": "r1"}],
        "routing": [{"id": "d1"}],
        "specialists": [{"id": "s1"}],
        "preflight_failures": [{"id": "p1"}],
    }
    outcome, detail = subject._run_ordinary_battery(
        "hermes",
        store=_ActivityStore([dict(before), after_failed]),
        resolver=_resolver({"hermes": "/bin/hermes"}),
        runner=lambda command, *, timeout: _completed("done"),
    )
    assert outcome == "failed"
    assert detail["reason"] == "ordinary_turn_not_staffing_complete"


def test_run_battery_gates_on_change_updates_proof_and_seals_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "ensure_private_directory",
        lambda path, **_kwargs: Path(path).mkdir(parents=True, exist_ok=True) or Path(path),
    )
    monkeypatch.setattr(subject, "_prepare_version_argv", _passthrough_preparer)
    fingerprint_path = tmp_path / "harness-battery.json"
    receipts = tmp_path / "receipts"
    versions = {
        "claude": _completed("2.1.252 (Claude Code)"),
        "codex": _completed("codex-cli 0.151.0"),
        "hermes": _completed("Hermes Agent v0.20.6"),
        "openclaw": _completed("OpenClaw 2026.7.1-2"),
    }

    def runner(command: tuple[str, ...], *, timeout: float) -> SimpleNamespace:
        return versions[Path(command[0]).name]

    canary_calls: list[str] = []

    def canary_runner(host: str, **kwargs: Any) -> dict[str, Any]:
        canary_calls.append(host)
        assert kwargs["execute"] is True
        if host == "codex":
            assert kwargs["profile_scope"] == "current-profile"
            assert kwargs["require_existing_store"] is True
        return {"canary_passed": True, "attestation_persisted": host == "codex"}

    fingerprint_path.write_text(
        json.dumps(
            {
                "schema": subject.BATTERY_SCHEMA,
                "harnesses": {
                    "codex": {"proven_version": "codex-cli 0.151.0"},
                    "hermes": {"proven_version": "Hermes Agent v0.20.6"},
                    "openclaw": {"proven_version": "OpenClaw 2026.7.1-2"},
                },
            }
        ),
        encoding="utf-8",
    )

    report = subject.run_battery(
        fingerprint_path=fingerprint_path,
        receipt_root=receipts,
        resolver=_resolver(
            {name: f"/bin/{name}" for name in ("claude", "codex", "hermes", "openclaw")}
        ),
        runner=runner,
        canary_runner=canary_runner,
        store_factory=lambda: _ActivityStore([{}, {}]),
    )

    # Only claude drifted; only claude ran.
    assert report["ran"] == ["claude"]
    assert canary_calls == ["claude"]
    assert report["ok"] is True
    document = json.loads(fingerprint_path.read_text(encoding="utf-8"))
    entry = document["harnesses"]["claude"]
    assert entry["proven_version"] == "2.1.252 (Claude Code)"
    assert entry["last_outcome"] == "passed"
    receipt = Path(entry["last_receipt"])
    assert receipt.is_file()
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["outcome"] == "passed"
    assert stat.S_IMODE(receipt.stat().st_mode) == 0o600


def test_failed_battery_keeps_prior_proof_and_reports_not_ok(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "ensure_private_directory",
        lambda path, **_kwargs: Path(path).mkdir(parents=True, exist_ok=True) or Path(path),
    )
    monkeypatch.setattr(subject, "_prepare_version_argv", _passthrough_preparer)
    fingerprint_path = tmp_path / "harness-battery.json"
    fingerprint_path.write_text(
        json.dumps(
            {
                "schema": subject.BATTERY_SCHEMA,
                "harnesses": {
                    "codex": {
                        "proven_version": "codex-cli 0.151.0",
                        "proven_at": "2026-08-30T00:00:00+00:00",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    report = subject.run_battery(
        hosts=("codex",),
        fingerprint_path=fingerprint_path,
        receipt_root=tmp_path / "receipts",
        resolver=_resolver({"codex": "/bin/codex"}),
        runner=lambda command, *, timeout: _completed("codex-cli 0.152.0"),
        canary_runner=lambda host, **kwargs: {
            "canary_passed": False,
            "invocation": {"failure_reason": "codex_hook_trust_not_ready"},
        },
        store_factory=lambda: _ActivityStore([{}, {}]),
    )

    assert report["ok"] is False
    assert report["failed"] == ["codex"]
    entry = json.loads(fingerprint_path.read_text(encoding="utf-8"))["harnesses"]["codex"]
    # The drifted version is recorded but never marked proven.
    assert entry["observed_version"] == "codex-cli 0.152.0"
    assert entry["proven_version"] == "codex-cli 0.151.0"
    assert entry["last_outcome"] == "attended_trust_required"
    assert entry["proven_at"] == "2026-08-30T00:00:00+00:00"


def test_unsupported_host_is_refused() -> None:
    with pytest.raises(ValueError):
        subject.run_battery(hosts=("zcode",), canary_runner=lambda *a, **k: {})


def test_ordinary_timeout_is_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def runner(command: tuple[str, ...], *, timeout: float) -> SimpleNamespace:
        raise subprocess.TimeoutExpired(cmd=list(command), timeout=timeout)

    outcome, detail = subject._run_ordinary_battery(
        "openclaw",
        store=_ActivityStore([{}, {}]),
        resolver=_resolver({"openclaw": "/bin/openclaw"}),
        runner=runner,
    )

    assert outcome == "failed"
    assert detail["timed_out"] is True


def test_doctor_surfaces_last_battery_outcome_per_harness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import doctor

    fingerprint_path = tmp_path / "harness-battery.json"
    fingerprint_path.write_text(
        json.dumps(
            {
                "schema": subject.BATTERY_SCHEMA,
                "harnesses": {
                    "claude": {
                        "last_outcome": "passed",
                        "observed_version": "2.1.252 (Claude Code)",
                    },
                    "codex": {
                        "last_outcome": "attended_trust_required",
                        "observed_version": "codex-cli 0.152.0",
                    },
                    "hermes": {
                        "last_outcome": "failed",
                        "observed_version": "Hermes Agent v0.21.0",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(subject, "default_fingerprint_path", lambda: fingerprint_path)

    checks = {check.name: check for check in doctor._harness_battery_checks()}

    assert checks["harness_battery_claude"].status == "pass"
    assert checks["harness_battery_codex"].status == "warn"
    assert "attended trust" in checks["harness_battery_codex"].message
    assert checks["harness_battery_hermes"].status == "fail"
    assert checks["harness_battery_openclaw"].status == "warn"
    assert "no battery baseline" in checks["harness_battery_openclaw"].message


def test_baseline_adopts_observed_versions_without_running(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "ensure_private_directory",
        lambda path, **_kwargs: Path(path).mkdir(parents=True, exist_ok=True) or Path(path),
    )
    monkeypatch.setattr(subject, "_prepare_version_argv", _passthrough_preparer)
    fingerprint_path = tmp_path / "harness-battery.json"

    report = subject.record_baseline(
        fingerprint_path=fingerprint_path,
        resolver=_resolver({"codex": "/bin/codex", "claude": "/bin/claude"}),
        runner=lambda command, *, timeout: _completed(f"{Path(command[0]).name} 1.0.0"),
    )

    assert report["baseline"] == {"codex": "codex 1.0.0", "claude": "claude 1.0.0"}
    assert report["skipped"] == {
        "hermes": "command not discovered",
        "openclaw": "command not discovered",
    }
    document = json.loads(fingerprint_path.read_text(encoding="utf-8"))
    assert document["harnesses"]["codex"]["proven_version"] == "codex 1.0.0"
    # A subsequent unchanged observation triggers nothing.
    assert (
        subject.changed_harnesses({"codex": "codex 1.0.0", "claude": "claude 1.0.0"}, document)
        == ()
    )


def test_baseline_with_nothing_adoptable_is_loud_not_silent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AR-340: an empty adoption exits nonzero and names the skipped hosts."""

    fingerprint_path = tmp_path / "harness-battery.json"
    empty = subject.record_baseline(
        fingerprint_path=fingerprint_path,
        resolver=_resolver({}),
        runner=lambda command, *, timeout: _completed("never called"),
    )
    assert empty["baseline"] == {}
    assert set(empty["skipped"]) == set(subject.BATTERY_HOSTS)
    assert not fingerprint_path.exists()

    monkeypatch.setattr(subject, "record_baseline", lambda hosts=None: empty)
    args = SimpleNamespace(
        baseline=True,
        json=False,
        host=None,
        install_service=False,
        uninstall_service=False,
    )
    exit_code = subject.run_battery_cli(args)
    output = capsys.readouterr().out
    assert exit_code == 1
    assert "no harness version could be adopted" in output
    assert "claude: skipped (command not discovered)" in output

    adopted = dict(empty, baseline={"claude": "claude 1.0.0"})
    monkeypatch.setattr(subject, "record_baseline", lambda hosts=None: adopted)
    assert subject.run_battery_cli(args) == 0
    output = capsys.readouterr().out
    assert "claude: baseline claude 1.0.0" in output
    assert "codex: skipped (command not discovered)" in output
