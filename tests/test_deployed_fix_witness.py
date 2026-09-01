"""AR-363: what runs must carry the fixes main claims to ship.

These tests exist because a live session on 2026-09-01 ran launcher
projection e5e2e193 while the last install had published 8698cca9 -- stale
hooks executing pre-fix code, noticed only because a SessionStart notice
happened to say so.  A version stamp cannot catch that; a witness that reads
the load-bearing literal out of the projection the host actually invokes can.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

import pytest

import agency_runtime
from agency_runtime.cli import evidence_commands
from agency_runtime.core import deployed_fix_witness as subject
from agency_runtime.core import host_wiring_drift, runtime_staleness
from agency_runtime.core.deployed_fix_witness import (
    FIX_REGISTRY,
    WITNESS_SCHEMA,
    attest_host,
    witness_history,
)

OLD = "3790d88f054d1413b796d4991ce9fb94a9e5e4233f4251a91825a16c4afbd099"
NEW = "4841b1e8ec85dbeb30821e2c1c32400ce42c8b075f65f7a0da6e8dd54401c750"


def _projection_bootstrap(digest: str) -> str:
    return str(
        Path("/private/launchers")
        / f"runtime-sha256-{digest}"
        / "site-packages"
        / "agency_runtime"
        / "_bootstrap.py"
    )


@pytest.fixture
def private_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect every private read and write into the fixture, trusted as-is.

    The projection trust walk refuses a pytest temporary tree (its parent
    chain is umask-wide), exactly as it should on a real box, so the trust
    seam is stubbed the way test_host_wiring_drift stubs its own probes.
    """

    root = tmp_path / "agency-runtime"

    def _directory(name: str) -> Path:
        path = root / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    monkeypatch.setattr(subject, "private_runtime_directory", _directory)
    monkeypatch.setattr(runtime_staleness, "private_runtime_directory", _directory)
    monkeypatch.setattr(subject, "validate_private_directory", lambda path: path)
    monkeypatch.setattr(host_wiring_drift, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(host_wiring_drift, "storage_file_is_trusted", lambda *_a, **_k: True)
    return root


def _fix_file(runtime_root: Path, relative_path: str) -> Path:
    return runtime_root / "site-packages" / Path(*PurePosixPath(relative_path).parts)


def _stage_projection(root: Path, digest: str, *, omit: tuple[str, ...] = ()) -> Path:
    """Build a projection carrying every registered marker except ``omit``."""

    runtime_root = root / "launchers" / f"runtime-sha256-{digest}"
    for fix in FIX_REGISTRY:
        target = _fix_file(runtime_root, fix.relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        line = f"# {fix.fix_id}\n" if fix.fix_id in omit else f"# {fix.fix_id}\n{fix.marker}\n"
        with target.open("a", encoding="utf-8") as stream:
            stream.write(line)
    (runtime_root / "runtime-manifest.json").write_text("{}\n", encoding="utf-8")
    return runtime_root


def _publish(digest: str, host: str) -> None:
    runtime_staleness.record_installed_runtime(_projection_bootstrap(digest), host=host)


def _hooks_payload(projection: str) -> str:
    command = (
        "/usr/bin/python3 -I -S /home/x/.agency-runtime/launchers"
        f"/runtime-sha256-{projection}/site-packages/agency_runtime/_bootstrap.py"
    )
    return json.dumps({"hooks": {"PreToolUse": [{"command": command}]}})


def _wire_claude(tmp_path: Path, *, staged: str, wired: str) -> dict[str, Path]:
    """Stage one projection for Claude and register another as what it invokes."""

    agency_home = tmp_path / "agency-home"
    claude_home = tmp_path / "claude-home"
    staged_path = (
        agency_home
        / "marketplaces"
        / "claude"
        / "plugins"
        / "agency-preflight"
        / "hooks"
        / "hooks.json"
    )
    staged_path.parent.mkdir(parents=True)
    staged_path.write_text(_hooks_payload(staged), encoding="utf-8")
    install = claude_home / "plugins" / "cache" / "agency-runtime" / "agency-preflight" / "0.1.0"
    wired_path = install / "hooks" / "hooks.json"
    wired_path.parent.mkdir(parents=True)
    wired_path.write_text(_hooks_payload(wired), encoding="utf-8")
    (claude_home / "plugins" / "installed_plugins.json").write_text(
        json.dumps(
            {
                "version": 2,
                "plugins": {
                    "agency-preflight@agency-runtime": [
                        {"scope": "user", "installPath": str(install), "version": "0.1.0"}
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    return {"agency_home": agency_home, "claude_home": claude_home}


def _raise(error: BaseException):
    def _inner(*_args, **_kwargs):
        raise error

    return _inner


def test_every_registry_marker_is_present_in_the_working_tree() -> None:
    """The registry pins literals in main; a renamed literal must fail here, not in the field."""

    package_root = Path(agency_runtime.__file__).resolve().parent.parent
    for fix in FIX_REGISTRY:
        source = package_root / Path(*PurePosixPath(fix.relative_path).parts)
        assert fix.marker in source.read_text(encoding="utf-8"), fix.fix_id


def test_registry_entries_are_unique_and_site_packages_relative() -> None:
    ids = [fix.fix_id for fix in FIX_REGISTRY]

    assert len(ids) == len(set(ids))
    for fix in FIX_REGISTRY:
        parts = PurePosixPath(fix.relative_path).parts
        assert parts[0] == "agency_runtime"
        assert ".." not in parts
        assert fix.marker.strip() == fix.marker and fix.marker
        assert fix.issue.startswith("AR-")


def test_a_wired_projection_carrying_every_fix_is_attested(
    tmp_path: Path,
    private_root: Path,
) -> None:
    _stage_projection(private_root, NEW)
    _publish(NEW, "claude")
    homes = _wire_claude(tmp_path, staged=NEW, wired=NEW)

    witness = attest_host("claude", **homes)

    assert witness.status == "attested"
    assert witness.reason_code == "attested"
    assert witness.reason == ""
    assert witness.wired_source == "host-wiring"
    assert witness.wiring_status == "wired"
    assert witness.drift is False
    assert witness.missing_fixes == ()
    assert all(item.present and len(item.file_sha256) == 64 for item in witness.fixes)
    assert witness.recorded is True
    manifest = private_root / "witness" / "claude.json"
    document = json.loads(manifest.read_text(encoding="utf-8"))
    assert document["schema"] == WITNESS_SCHEMA
    assert document["status"] == "attested"
    assert document["wired_digest"] == NEW
    assert document["published_digest"] == NEW
    assert document["registry_size"] == len(FIX_REGISTRY)
    assert stat.S_IMODE(manifest.stat().st_mode) == 0o600
    history = private_root / "witness" / "claude.history.jsonl"
    assert stat.S_IMODE(history.stat().st_mode) == 0o600


def test_the_stale_hook_shape_is_detected_as_drift(tmp_path: Path, private_root: Path) -> None:
    """Published the new projection; the host still invokes the pre-fix one."""

    _stage_projection(private_root, OLD, omit=("AR-345",))
    _stage_projection(private_root, NEW)
    _publish(NEW, "claude")
    homes = _wire_claude(tmp_path, staged=NEW, wired=OLD)

    witness = attest_host("claude", **homes)

    assert witness.status == "drift"
    assert witness.reason_code == "published_projection_mismatch"
    assert witness.drift is True
    assert witness.wired_digest == OLD
    assert witness.published_digest == NEW
    assert witness.wired_source == "host-wiring"
    assert witness.wiring_status == "drift"
    assert "agency install --agent claude" in witness.reason
    # Fixes are verified against what actually runs, not what was published.
    assert witness.missing_fixes == ("AR-345",)
    assert witness.as_dict()["drift"] is True
    entry = witness_history("claude")[-1]
    assert entry["wired_digest"] == OLD
    assert entry["fixes"]["AR-345"] is False


def test_drift_is_reported_even_when_the_invoked_projection_is_gone(
    tmp_path: Path,
    private_root: Path,
) -> None:
    _stage_projection(private_root, NEW)
    _publish(NEW, "claude")
    homes = _wire_claude(tmp_path, staged=NEW, wired=OLD)

    witness = attest_host("claude", **homes, record=False)

    assert witness.status == "drift"
    assert witness.projection_state == "missing"
    assert all(not item.checked for item in witness.fixes)
    assert witness.missing_fixes == ()


def test_a_projection_missing_one_marker_is_missing_fix_and_names_it(
    tmp_path: Path,
    private_root: Path,
) -> None:
    _stage_projection(private_root, NEW, omit=("AR-366-stop-hook",))
    _publish(NEW, "claude")
    homes = _wire_claude(tmp_path, staged=NEW, wired=NEW)

    witness = attest_host("claude", **homes)

    assert witness.status == "missing_fix"
    assert witness.reason_code == "fix_marker_absent"
    assert witness.drift is False
    assert witness.missing_fixes == ("AR-366-stop-hook",)
    states = {item.fix.fix_id: item.state for item in witness.fixes if not item.present}
    assert states == {"AR-366-stop-hook": "absent"}
    # The sibling marker sharing a file with another fix is unaffected.
    assert next(item for item in witness.fixes if item.fix.fix_id == "AR-366-gate").present


def test_a_registered_file_absent_from_the_projection_is_named_as_missing(
    private_root: Path,
) -> None:
    runtime_root = _stage_projection(private_root, NEW)
    _publish(NEW, "codex")
    _fix_file(runtime_root, "agency_runtime/core/store/evidence.py").unlink()

    witness = attest_host("codex", record=False)

    assert witness.status == "missing_fix"
    assert witness.missing_fixes == ("AR-365",)
    absent = next(item for item in witness.fixes if item.fix.fix_id == "AR-365")
    assert absent.state == "missing_file"
    assert absent.file_sha256 == ""


def test_history_appends_one_line_per_attestation_newest_last_and_bounded(
    tmp_path: Path,
    private_root: Path,
) -> None:
    runtime_root = _stage_projection(private_root, NEW)
    _publish(NEW, "claude")
    homes = _wire_claude(tmp_path, staged=NEW, wired=NEW)

    attest_host("claude", **homes)
    broken = _fix_file(runtime_root, "agency_runtime/core/workforce/plan_policy.py")
    broken.write_text("# AR-345 marker removed\n", encoding="utf-8")
    attest_host("claude", **homes)
    attest_host("claude", **homes)

    lines = (private_root / "witness" / "claude.history.jsonl").read_text("utf-8").splitlines()
    assert len(lines) == 3
    complete = witness_history("claude", limit=50)
    assert [entry["status"] for entry in complete] == ["attested", "missing_fix", "missing_fix"]
    assert [entry["fixes"]["AR-345"] for entry in complete] == [True, False, False]
    assert complete[0]["attested_at"] <= complete[1]["attested_at"] <= complete[2]["attested_at"]
    assert set(complete[0]) == {
        "attested_at",
        "status",
        "reason_code",
        "published_digest",
        "wired_digest",
        "wired_source",
        "source_digest",
        "fixes",
    }
    bounded = witness_history("claude", limit=2)
    assert bounded == complete[-2:]


def test_an_unmeasured_host_falls_back_to_the_installed_pointer_and_says_so(
    private_root: Path,
) -> None:
    _stage_projection(private_root, NEW)
    _publish(NEW, "codex")

    witness = attest_host("codex")

    assert witness.status == "attested"
    assert witness.wired_source == "installed-pointer"
    assert witness.wiring_status == "not_measured"
    assert witness.wiring_reason_code == "host_not_measured"
    assert witness.wired_digest == NEW
    assert witness.drift is False
    document = json.loads((private_root / "witness" / "codex.json").read_text(encoding="utf-8"))
    assert document["wired_source"] == "installed-pointer"


def test_a_measured_host_without_readable_wiring_falls_back_and_says_so(
    tmp_path: Path,
    private_root: Path,
) -> None:
    _stage_projection(private_root, NEW)
    _publish(NEW, "claude")

    witness = attest_host(
        "claude",
        agency_home=tmp_path / "agency-home",
        claude_home=tmp_path / "claude-home",
        record=False,
    )

    assert witness.status == "attested"
    assert witness.wired_source == "installed-pointer"
    assert witness.wiring_status == "unavailable"
    assert witness.wiring_reason_code == "staged_missing"


def test_no_installed_pointer_is_unavailable_not_a_pass(private_root: Path) -> None:
    witness = attest_host("hermes")

    assert witness.status == "unavailable"
    assert witness.reason_code == "no_installed_pointer"
    assert witness.wired_digest == ""
    assert witness.published_digest == ""
    assert all(not item.checked for item in witness.fixes)
    # Even an unavailable verdict is bisect evidence and is recorded.
    assert witness.recorded is True
    assert witness_history("hermes")[-1]["status"] == "unavailable"


def test_a_pointer_naming_an_absent_projection_is_unavailable(private_root: Path) -> None:
    _publish(NEW, "codex")

    witness = attest_host("codex", record=False)

    assert witness.status == "unavailable"
    assert witness.reason_code == "projection_missing"
    assert witness.projection_state == "missing"


def test_an_untrusted_projection_directory_is_unavailable(
    private_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stage_projection(private_root, NEW)
    _publish(NEW, "codex")
    monkeypatch.setattr(
        subject, "validate_private_directory", _raise(PermissionError("not owner-private"))
    )

    witness = attest_host("codex", record=False)

    assert witness.status == "unavailable"
    assert witness.reason_code == "projection_untrusted"
    assert witness.projection_root == ""


def test_a_source_package_that_would_stage_something_else_is_drift(
    private_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stage_projection(private_root, NEW)
    _publish(NEW, "codex")
    monkeypatch.setattr(
        subject,
        "plan_private_package_runtime",
        lambda _path: SimpleNamespace(manifest_sha256=OLD),
    )

    witness = attest_host("codex", source_package="/checkout/agency_runtime", record=False)

    assert witness.status == "drift"
    assert witness.reason_code == "source_projection_mismatch"
    assert witness.source_drift is True
    assert witness.drift is False
    assert witness.source_digest == OLD


def test_a_source_package_that_cannot_be_planned_is_not_drift(
    private_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Planning is restricted to the active package; refusal is not evidence."""

    _stage_projection(private_root, NEW)
    _publish(NEW, "codex")
    monkeypatch.setattr(
        subject,
        "plan_private_package_runtime",
        _raise(PermissionError("private runtime staging is limited to the active package")),
    )

    witness = attest_host("codex", source_package="/elsewhere/_bootstrap.py", record=False)

    assert witness.status == "attested"
    assert witness.source_state == "unplannable"
    assert witness.source_drift is None


def test_record_false_writes_nothing(private_root: Path) -> None:
    _stage_projection(private_root, NEW)
    _publish(NEW, "codex")

    witness = attest_host("codex", record=False)

    assert witness.recorded is False
    assert not (private_root / "witness" / "codex.json").exists()
    assert witness_history("codex") == ()


def test_a_full_history_is_rotated_so_the_newest_window_survives(
    private_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stage_projection(private_root, NEW)
    _publish(NEW, "codex")
    monkeypatch.setattr(subject, "_MAX_HISTORY_BYTES", 1)

    attest_host("codex")
    attest_host("codex")

    witness_dir = private_root / "witness"
    assert (witness_dir / "codex.history.1.jsonl").is_file()
    current = (witness_dir / "codex.history.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(current) == 1
    assert len(witness_history("codex")) == 1


def test_malformed_history_lines_are_skipped_not_trusted(private_root: Path) -> None:
    witness_dir = private_root / "witness"
    witness_dir.mkdir(parents=True)
    (witness_dir / "codex.history.jsonl").write_text(
        "not json\n"
        '{"attested_at": 1}\n'
        '{"attested_at": "2026-09-01T00:00:00+00:00", "status": "attested"}\n',
        encoding="utf-8",
    )

    entries = witness_history("codex", limit=50)

    assert [entry["status"] for entry in entries] == ["attested"]


def test_a_recording_failure_is_reported_on_the_witness_not_raised(
    private_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stage_projection(private_root, NEW)
    _publish(NEW, "codex")
    monkeypatch.setattr(subject, "atomic_write_text", _raise(OSError("disk full")))

    witness = attest_host("codex")

    assert witness.status == "attested"
    assert witness.recorded is False
    assert witness.record_error == "OSError"


@pytest.mark.parametrize("host", ["", "Bad Host", "../x", "a" * 33])
def test_an_invalid_host_is_refused(host: str) -> None:
    with pytest.raises(ValueError):
        attest_host(host, record=False)


def test_evidence_witness_exits_one_on_drift_and_names_the_missing_fix(
    tmp_path: Path,
    private_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _stage_projection(private_root, OLD, omit=("AR-345",))
    _stage_projection(private_root, NEW)
    _publish(NEW, "claude")
    homes = _wire_claude(tmp_path, staged=NEW, wired=OLD)
    monkeypatch.setattr(
        evidence_commands,
        "attest_host",
        lambda host, **_kwargs: attest_host(host, **homes, record=False),
    )
    monkeypatch.setattr(evidence_commands, "recorded_hosts", lambda: ("claude",))

    code = evidence_commands.cmd_evidence_witness(SimpleNamespace(host=None, json=False))

    out = capsys.readouterr().out
    assert code == 1
    assert "claude: DRIFT" in out
    assert f"published: {NEW[:12]}  wired: {OLD[:12]}  (wired via host-wiring)" in out
    assert "missing AR-345" in out


def test_evidence_witness_json_reports_the_requested_host_and_exits_zero_when_attested(
    private_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _stage_projection(private_root, NEW)
    _publish(NEW, "codex")
    monkeypatch.setattr(
        evidence_commands,
        "attest_host",
        lambda host, **_kwargs: attest_host(host, record=False),
    )

    code = evidence_commands.cmd_evidence_witness(SimpleNamespace(host="codex", json=True))

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert [entry["host"] for entry in payload["hosts"]] == ["codex"]
    assert payload["hosts"][0]["status"] == "attested"
    assert payload["hosts"][0]["wired_source"] == "installed-pointer"


def test_evidence_witness_with_no_recorded_host_says_so(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(evidence_commands, "recorded_hosts", lambda: ())

    code = evidence_commands.cmd_evidence_witness(SimpleNamespace(host=None, json=False))

    assert code == 0
    assert "nothing to attest" in capsys.readouterr().out
