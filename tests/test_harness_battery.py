"""AR-337: the change-triggered harness canary battery.

The battery's whole value is running exactly when a harness changed and
saying loudly what it found, so these tests pin the change gate, the
outcome mapping (including the distinct attended-trust status), the
content-free posture counts, and the private receipt/fingerprint trail.
They also pin the two verdict refinements: the ordinary check judges only
the battery turn's own session (AR-352), and every probe is graded over k
trials as pass^k (canaries) or pass@k (ordinary checks) with every trial
persisted (AR-360).
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


_EMPTY_WINDOW: dict[str, list[dict[str, Any]]] = {
    "runs": [],
    "routing": [],
    "specialists": [],
    "finalizations": [],
    "preflight_failures": [],
}


def _run_row(row_id: str, *, host: str, session: str, trace: str) -> dict[str, Any]:
    return {"id": row_id, "host": host, "session_id": session, "trace_id": trace}


def _turn_row(
    row_id: str,
    *,
    session: str = "",
    trace: str = "",
    host: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {"id": row_id, "session_id": session, "trace_id": trace}
    if host is not None:
        row["host"] = host
    return row


def _staffed_window(
    host: str,
    *,
    suffix: str,
    preflight_failures: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Every row one staffed, finalized own turn leaves in the store window."""

    session = f"{host}-session-{suffix}"
    trace = f"{host}-trace-{suffix}"
    return {
        "runs": [_run_row(f"r{suffix}", host=host, session=session, trace=trace)],
        "routing": [_turn_row(f"d{suffix}", session=session, trace=trace)],
        "specialists": [_turn_row(f"s{suffix}", session=session, trace=trace)],
        # finalizations carry no session id; only the trace join owns them.
        "finalizations": [{"id": f"f{suffix}", "trace_id": trace, "host": host}],
        "preflight_failures": list(preflight_failures or []),
    }


def _ordinary(store: _ActivityStore, host: str = "hermes") -> tuple[str, dict[str, Any]]:
    return subject._run_ordinary_battery(
        host,
        store=store,
        resolver=_resolver({host: f"/bin/{host}"}),
        runner=lambda command, *, timeout: _completed("done"),
    )


def test_ordinary_battery_requires_staffing_complete_store_delta() -> None:
    outcome, detail = _ordinary(
        _ActivityStore([dict(_EMPTY_WINDOW), _staffed_window("hermes", suffix="1")])
    )

    assert outcome == "passed"
    assert detail["reason"] == ""
    expected = {"runs": 1, "routing": 1, "specialists": 1, "finalizations": 1}
    assert detail["new_row_counts"] == expected
    assert detail["own_session_row_counts"] == expected
    assert detail["own_sessions"] == ["hermes-session-1"]
    assert detail["foreign_session_activity"] == {}

    bare = dict(_staffed_window("hermes", suffix="1"), routing=[], specialists=[])
    outcome, detail = _ordinary(_ActivityStore([dict(_EMPTY_WINDOW), bare]))

    assert outcome == "failed"
    assert detail["reason"] == "ordinary_turn_not_staffing_complete"
    assert detail["own_session_row_counts"] == {"runs": 1, "finalizations": 1}


def test_ordinary_battery_ignores_foreign_session_preflight_failures() -> None:
    """AR-352: a staffed, finalized own turn passes even when another host's
    session and another session of the same host record preflight failures
    in the window; the report keeps them as content-free foreign activity."""

    before = dict(
        _EMPTY_WINDOW,
        runs=[
            _run_row("r-old", host="hermes", session="hermes-interactive", trace="hermes-old"),
            _run_row("r-claude", host="claude", session="claude-deploy", trace="claude-t"),
        ],
    )
    foreign_failures = [
        _turn_row("p-claude", session="claude-deploy", trace="claude-t", host="claude"),
        _turn_row("p-hermes", session="hermes-interactive", trace="hermes-old", host="hermes"),
        _turn_row("p-cron", session="openclaw-cron", trace="openclaw-t", host="openclaw"),
        _turn_row("p-odd", session="mystery", trace="mystery-t", host="not-a-host"),
    ]
    after = _staffed_window("hermes", suffix="1", preflight_failures=foreign_failures)
    after["runs"].extend(before["runs"])

    outcome, detail = _ordinary(_ActivityStore([before, after]))

    assert outcome == "passed"
    assert detail["reason"] == ""
    assert detail["own_sessions"] == ["hermes-session-1"]
    assert detail["own_session_row_counts"] == {
        "runs": 1,
        "routing": 1,
        "specialists": 1,
        "finalizations": 1,
    }
    assert detail["foreign_session_activity"] == {"preflight_failures": 4}
    assert detail["foreign_session_hosts"] == {"claude": 1, "hermes": 1, "openclaw": 1, "other": 1}
    # The unscoped total keeps its pre-AR-352 meaning: every new row in the window.
    assert detail["new_row_counts"] == {
        "runs": 1,
        "routing": 1,
        "specialists": 1,
        "finalizations": 1,
        "preflight_failures": 4,
    }


def test_ordinary_battery_fails_on_its_own_sessions_preflight_failure() -> None:
    """AR-352, the other direction: a preflight failure that belongs to the
    battery turn's own session still fails the battery."""

    own_failure = _turn_row(
        "p-own", session="hermes-session-1", trace="hermes-trace-1", host="hermes"
    )
    after = _staffed_window("hermes", suffix="1", preflight_failures=[own_failure])

    outcome, detail = _ordinary(_ActivityStore([dict(_EMPTY_WINDOW), after]))

    assert outcome == "failed"
    assert detail["reason"] == "ordinary_turn_not_staffing_complete"
    assert detail["own_session_row_counts"]["preflight_failures"] == 1
    assert detail["foreign_session_activity"] == {}

    # A failure that shares only the trace (no session id recorded) is own too.
    trace_only = _turn_row("p-trace", trace="hermes-trace-1", host="hermes")
    after = _staffed_window("hermes", suffix="1", preflight_failures=[trace_only])
    outcome, detail = _ordinary(_ActivityStore([dict(_EMPTY_WINDOW), after]))

    assert outcome == "failed"
    assert detail["own_session_row_counts"]["preflight_failures"] == 1


def test_ordinary_battery_does_not_borrow_foreign_staffing_rows() -> None:
    """The mirror hazard of AR-352: another session's routing and specialist
    rows must not staff the battery's own bare turn."""

    after = dict(
        _staffed_window("hermes", suffix="1"),
        routing=[_turn_row("d-foreign", session="hermes-interactive", trace="other")],
        specialists=[_turn_row("s-foreign", session="hermes-interactive", trace="other")],
    )

    outcome, detail = _ordinary(_ActivityStore([dict(_EMPTY_WINDOW), after]))

    assert outcome == "failed"
    assert detail["own_session_row_counts"] == {"runs": 1, "finalizations": 1}
    assert detail["foreign_session_activity"] == {"routing": 1, "specialists": 1}
    assert detail["foreign_session_hosts"] == {"unknown": 2}


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

    # Only claude drifted; only claude ran, once per default trial (AR-360).
    assert report["ran"] == ["claude"]
    assert report["trials"] == subject.BATTERY_DEFAULT_TRIALS == 2
    assert canary_calls == ["claude", "claude"]
    assert report["ok"] is True
    document = json.loads(fingerprint_path.read_text(encoding="utf-8"))
    entry = document["harnesses"]["claude"]
    assert entry["proven_version"] == "2.1.252 (Claude Code)"
    assert entry["last_outcome"] == "passed"
    assert entry["last_grading_mode"] == "pass_all_k"
    assert entry["last_trials"] == {"requested": 2, "run": 2, "passed": 2}
    receipt = Path(entry["last_receipt"])
    assert receipt.is_file()
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["outcome"] == "passed"
    assert payload["grading"]["mode"] == "pass_all_k"
    assert [trial["outcome"] for trial in payload["trials"]] == ["passed", "passed"]
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

    canary_calls: list[str] = []

    def canary_runner(host: str, **kwargs: Any) -> dict[str, Any]:
        canary_calls.append(host)
        return {
            "canary_passed": False,
            "invocation": {"failure_reason": "codex_hook_trust_not_ready"},
        }

    report = subject.run_battery(
        hosts=("codex",),
        trials=3,
        fingerprint_path=fingerprint_path,
        receipt_root=tmp_path / "receipts",
        resolver=_resolver({"codex": "/bin/codex"}),
        runner=lambda command, *, timeout: _completed("codex-cli 0.152.0"),
        canary_runner=canary_runner,
        store_factory=lambda: _ActivityStore([{}, {}]),
    )

    assert report["ok"] is False
    assert report["failed"] == ["codex"]
    detail = report["results"]["codex"]
    # An attended-trust refusal short-circuits: retrying cannot change it.
    assert canary_calls == ["codex"]
    assert detail["outcome"] == "attended_trust_required"
    assert detail["reason"] == "codex_hook_trust_not_ready"
    assert detail["grading"] == {
        "mode": "pass_all_k",
        "trials_requested": 3,
        "trials_run": 1,
        "passed_trials": [],
        "failed_trials": [1],
    }
    entry = json.loads(fingerprint_path.read_text(encoding="utf-8"))["harnesses"]["codex"]
    # The drifted version is recorded but never marked proven.
    assert entry["observed_version"] == "codex-cli 0.152.0"
    assert entry["proven_version"] == "codex-cli 0.151.0"
    assert entry["last_outcome"] == "attended_trust_required"
    assert entry["proven_at"] == "2026-08-30T00:00:00+00:00"
    assert entry["last_trials"] == {"requested": 3, "run": 1, "passed": 0}


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
                        "last_grading_mode": "pass_all_k",
                        "last_trials": {"requested": 2, "run": 2, "passed": 2},
                    },
                    "codex": {
                        "last_outcome": "attended_trust_required",
                        "observed_version": "codex-cli 0.152.0",
                        "last_grading_mode": "pass_all_k",
                        "last_trials": {"requested": "3", "run": 1, "passed": 0},
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
    assert checks["harness_battery_claude"].message == "2.1.252 (Claude Code)"
    # AR-360: the grading tally is a detail line; the message contract holds.
    assert checks["harness_battery_claude"].detail == "pass^2: 2/2 trials"
    assert checks["harness_battery_codex"].status == "warn"
    assert "attended trust" in checks["harness_battery_codex"].message
    # A malformed tally is ignored, never trusted.
    assert checks["harness_battery_codex"].detail == ""
    assert checks["harness_battery_hermes"].status == "fail"
    # Entries written before trial grading render exactly as before.
    assert checks["harness_battery_hermes"].detail == ""
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


def test_openclaw_ordinary_command_names_an_explicit_agent_owner() -> None:
    """OpenClaw 2026.8 refuses multi-agent turns without --agent; the battery
    send must name its owner or it fails before any staffing occurs."""

    from agency_runtime.core.harness_battery import _ORDINARY_COMMANDS

    command = _ORDINARY_COMMANDS["openclaw"]
    assert "--agent" in command
    assert command[command.index("--agent") + 1] == "openclaw"
    assert "--session-key" in command


def test_grade_trials_folds_outcomes_per_mode() -> None:
    """AR-360: pass^k needs every trial green, pass@k needs one; an attended
    trust refusal is a distinct outcome under either mode."""

    passed = {"outcome": "passed", "reason": ""}
    failed = {"outcome": "failed", "reason": "ordinary_turn_not_staffing_complete"}
    attended = {"outcome": "attended_trust_required", "reason": "codex_hook_trust_not_ready"}
    pass_all, pass_any = subject.GRADING_PASS_ALL_K, subject.GRADING_PASS_ANY_K

    assert subject.grade_trials(pass_all, [passed, passed]) == ("passed", "")
    assert subject.grade_trials(pass_all, [passed, failed]) == (
        "failed",
        "pass_all_k_trial_failed:2",
    )
    assert subject.grade_trials(pass_all, [failed, failed, passed]) == (
        "failed",
        "pass_all_k_trial_failed:1,2",
    )
    assert subject.grade_trials(pass_any, [failed, passed]) == ("passed", "")
    assert subject.grade_trials(pass_any, [failed, failed]) == (
        "failed",
        "pass_any_k_all_trials_failed:1,2",
    )
    assert subject.grade_trials(pass_any, [failed, attended]) == (
        "attended_trust_required",
        "codex_hook_trust_not_ready",
    )
    assert subject.grade_trials(pass_all, []) == ("failed", "no_trials_run")
    with pytest.raises(ValueError):
        subject.grade_trials("pass_maybe", [passed])


def test_trial_count_is_bounded_and_grading_modes_follow_the_probe() -> None:
    assert subject.validated_trials(None) == subject.BATTERY_DEFAULT_TRIALS == 2
    assert subject.validated_trials(1) == 1
    assert subject.validated_trials(subject.BATTERY_MAX_TRIALS) == 5
    for rejected in (0, 6, True, "2", 2.0):
        with pytest.raises(ValueError):
            subject.validated_trials(rejected)  # type: ignore[arg-type]

    assert subject.probe_grading_mode("claude") == subject.GRADING_PASS_ALL_K
    assert subject.probe_grading_mode("codex") == subject.GRADING_PASS_ALL_K
    assert subject.probe_grading_mode("hermes") == subject.GRADING_PASS_ANY_K
    assert subject.probe_grading_mode("openclaw") == subject.GRADING_PASS_ANY_K
    assert subject.grading_label(subject.GRADING_PASS_ALL_K, 2) == "pass^2"
    assert subject.grading_label(subject.GRADING_PASS_ANY_K, 3) == "pass@3"


def _private_directories(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subject,
        "ensure_private_directory",
        lambda path, **_kwargs: Path(path).mkdir(parents=True, exist_ok=True) or Path(path),
    )
    monkeypatch.setattr(subject, "_prepare_version_argv", _passthrough_preparer)


def test_flaky_ordinary_probe_passes_under_pass_any_k_and_records_every_trial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AR-360: a 50%-flaky hermes (trial 1 does not staff, trial 2 does)
    grades pass@2 as passed with both trials persisted in the receipt and
    the fingerprint, and trial 1's foreign failure is never counted twice
    (AR-352: each trial computes its own delta)."""

    _private_directories(monkeypatch)
    fingerprint_path = tmp_path / "harness-battery.json"
    foreign = _turn_row("p-foreign", session="claude-deploy", trace="claude-t", host="claude")
    first_after = dict(
        _EMPTY_WINDOW,
        runs=[_run_row("r1", host="hermes", session="hermes-session-1", trace="hermes-trace-1")],
        preflight_failures=[foreign],
    )
    second_after = _staffed_window("hermes", suffix="2", preflight_failures=[foreign])
    second_after["runs"].extend(first_after["runs"])
    store = _ActivityStore([dict(_EMPTY_WINDOW), first_after, dict(first_after), second_after])

    report = subject.run_battery(
        hosts=("hermes",),
        force=True,
        trials=2,
        fingerprint_path=fingerprint_path,
        receipt_root=tmp_path / "receipts",
        resolver=_resolver({"hermes": "/bin/hermes"}),
        runner=lambda command, *, timeout: _completed("Hermes Agent v0.21.0"),
        canary_runner=lambda host, **kwargs: {"canary_passed": True},
        store_factory=lambda: store,
    )

    assert report["ok"] is True
    assert report["trials"] == 2
    detail = report["results"]["hermes"]
    assert detail["outcome"] == "passed"
    assert detail["reason"] == ""
    assert detail["mode"] == "ordinary"
    assert detail["grading"] == {
        "mode": "pass_any_k",
        "trials_requested": 2,
        "trials_run": 2,
        "passed_trials": [2],
        "failed_trials": [1],
    }
    trials = detail["trials"]
    assert [trial["trial"] for trial in trials] == [1, 2]
    assert [trial["outcome"] for trial in trials] == ["failed", "passed"]
    assert trials[0]["reason"] == "ordinary_turn_not_staffing_complete"
    assert trials[0]["foreign_session_activity"] == {"preflight_failures": 1}
    assert trials[1]["foreign_session_activity"] == {}
    assert trials[1]["own_sessions"] == ["hermes-session-2"]
    assert all(trial["ran_at"] for trial in trials)
    entry = json.loads(fingerprint_path.read_text(encoding="utf-8"))["harnesses"]["hermes"]
    assert entry["proven_version"] == "Hermes Agent v0.21.0"
    assert entry["last_outcome"] == "passed"
    assert entry["last_grading_mode"] == "pass_any_k"
    assert entry["last_trials"] == {"requested": 2, "run": 2, "passed": 1}
    payload = json.loads(Path(entry["last_receipt"]).read_text(encoding="utf-8"))
    assert payload["grading"] == detail["grading"]
    assert [trial["outcome"] for trial in payload["trials"]] == ["failed", "passed"]


def test_flaky_canary_probe_fails_under_pass_all_k_and_names_the_failing_trial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AR-360: the same 50%-flaky series that pass@k accepts fails the
    safety-critical canary under pass^k, and the reason names the trial."""

    _private_directories(monkeypatch)
    fingerprint_path = tmp_path / "harness-battery.json"
    fingerprint_path.write_text(
        json.dumps(
            {
                "schema": subject.BATTERY_SCHEMA,
                "harnesses": {
                    "claude": {
                        "proven_version": "2.1.251 (Claude Code)",
                        "proven_at": "2026-08-30T00:00:00+00:00",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    flaps = iter([False, True])
    canary_calls: list[str] = []

    def canary_runner(host: str, **kwargs: Any) -> dict[str, Any]:
        canary_calls.append(host)
        passed = next(flaps)
        return {
            "canary_passed": passed,
            "invocation": {"failure_reason": "" if passed else "claude_finalization_missing"},
        }

    report = subject.run_battery(
        hosts=("claude",),
        trials=2,
        fingerprint_path=fingerprint_path,
        receipt_root=tmp_path / "receipts",
        resolver=_resolver({"claude": "/bin/claude"}),
        runner=lambda command, *, timeout: _completed("2.1.252 (Claude Code)"),
        canary_runner=canary_runner,
        store_factory=lambda: _ActivityStore([{}, {}]),
    )

    assert canary_calls == ["claude", "claude"]
    assert report["ok"] is False
    assert report["failed"] == ["claude"]
    detail = report["results"]["claude"]
    assert detail["outcome"] == "failed"
    assert detail["reason"] == "pass_all_k_trial_failed:1"
    assert detail["grading"]["mode"] == "pass_all_k"
    assert detail["grading"]["failed_trials"] == [1]
    assert detail["grading"]["passed_trials"] == [2]
    assert [trial["reason"] for trial in detail["trials"]] == ["claude_finalization_missing", ""]
    entry = json.loads(fingerprint_path.read_text(encoding="utf-8"))["harnesses"]["claude"]
    assert entry["proven_version"] == "2.1.251 (Claude Code)"
    assert entry["proven_at"] == "2026-08-30T00:00:00+00:00"
    assert entry["last_outcome"] == "failed"
    assert entry["last_trials"] == {"requested": 2, "run": 2, "passed": 1}
    # The very same series would pass a flaky-window probe.
    assert subject.grade_trials(subject.GRADING_PASS_ANY_K, detail["trials"]) == ("passed", "")


def test_single_trial_grades_like_the_single_shot_battery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _private_directories(monkeypatch)
    canary_calls: list[str] = []

    def canary_runner(host: str, **kwargs: Any) -> dict[str, Any]:
        canary_calls.append(host)
        return {"canary_passed": True, "attestation_persisted": True}

    report = subject.run_battery(
        hosts=("codex",),
        trials=1,
        fingerprint_path=tmp_path / "harness-battery.json",
        receipt_root=tmp_path / "receipts",
        resolver=_resolver({"codex": "/bin/codex"}),
        runner=lambda command, *, timeout: _completed("codex-cli 0.152.0"),
        canary_runner=canary_runner,
        store_factory=lambda: _ActivityStore([{}, {}]),
    )

    assert canary_calls == ["codex"]
    assert report["ok"] is True
    detail = report["results"]["codex"]
    assert detail["outcome"] == "passed"
    assert detail["grading"] == {
        "mode": "pass_all_k",
        "trials_requested": 1,
        "trials_run": 1,
        "passed_trials": [1],
        "failed_trials": [],
    }
    assert detail["trials"][0]["attestation_persisted"] is True
    assert subject.describe_result("codex", detail) == (
        "codex: passed (pass^1: 1/1 trials) (codex-cli 0.152.0)"
    )


def test_run_battery_rejects_out_of_range_trials() -> None:
    with pytest.raises(ValueError, match="1 through 5"):
        subject.run_battery(hosts=("claude",), trials=6, canary_runner=lambda *a, **k: {})
    with pytest.raises(ValueError, match="1 through 5"):
        subject.run_battery(hosts=("claude",), trials=0, canary_runner=lambda *a, **k: {})


def test_run_battery_cli_threads_trials_and_prints_the_grading_tally(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_battery(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {
            "schema": subject.BATTERY_SCHEMA,
            "observed": {"hermes": "Hermes Agent v0.21.0"},
            "ran": ["hermes"],
            "trials": 3,
            "results": {
                "hermes": {
                    "outcome": "passed",
                    "reason": "",
                    "observed_version": "Hermes Agent v0.21.0",
                    "grading": {
                        "mode": "pass_any_k",
                        "trials_requested": 3,
                        "trials_run": 3,
                        "passed_trials": [2],
                        "failed_trials": [1, 3],
                    },
                }
            },
            "failed": [],
            "ok": True,
        }

    monkeypatch.setattr(subject, "run_battery", fake_run_battery)
    args = SimpleNamespace(
        baseline=False,
        json=False,
        host="hermes",
        force=True,
        config=None,
        trials=3,
        install_service=False,
        uninstall_service=False,
    )

    assert subject.run_battery_cli(args) == 0
    assert captured["trials"] == 3
    assert captured["hosts"] == ("hermes",)
    assert captured["force"] is True
    assert capsys.readouterr().out.strip() == (
        "hermes: passed (pass@3: 1/3 trials) (Hermes Agent v0.21.0)"
    )

    failed_detail = {
        "outcome": "failed",
        "reason": "pass_all_k_trial_failed:2",
        "observed_version": "2.1.252 (Claude Code)",
        "grading": {
            "mode": "pass_all_k",
            "trials_requested": 2,
            "trials_run": 2,
            "passed_trials": [1],
            "failed_trials": [2],
        },
    }
    assert subject.describe_result("claude", failed_detail) == (
        "claude: failed (pass^2: 1/2 trials; pass_all_k_trial_failed:2) (2.1.252 (Claude Code))"
    )
