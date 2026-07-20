"""Explicit Agency/native-only canary mode and master-control contracts."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from agency_runtime.core import canary
from agency_runtime.core.store.sqlite import Store


def _native(_host: str) -> dict[str, object]:
    return {
        "host": "codex",
        "executable_discovered": True,
        "registered": True,
        "enabled": True,
        "host_version": "codex 1.0",
        "install_id": "install-1",
        "bundle_digest": "a" * 64,
    }


def _control(enabled: bool, generation: int = 4) -> dict[str, object]:
    return {
        "schema_version": "agency.runtime_control.v1",
        "enabled": enabled,
        "generation": generation,
        "updated_at": "2026-07-20T00:00:00Z",
        "source": "test",
    }


class _NativeCodexBackend:
    def __init__(self, path: Path, *, emit_evidence: bool = False, output: str = "native"):
        self.path = path
        self.emit_evidence = emit_evidence
        self.output = output

    def execute(self, **kwargs):
        if self.emit_evidence:
            store = Store(self.path)
            trace_id = "unexpected-agency-trace"
            store.record_routing_decision(
                trace_id=trace_id,
                session_id="unexpected-session",
                query_hash=hashlib.sha256(kwargs["task"].encode()).hexdigest(),
                context_fingerprint="b" * 64,
                decision={"status": "selected", "selected_ids": ["reviewer"]},
            )
            store.record_finalization(trace_id=trace_id, host="codex", action="accept")
        return {
            "backend": "codex",
            "profile_scope": "isolated-profile",
            "isolated_plugin": {"registered": True, "enabled": True},
            "status": "completed",
            "exit_code": 0,
            "output": self.output,
        }


def _set_master(monkeypatch: pytest.MonkeyPatch, documents: list[dict[str, object]]) -> None:
    remaining = iter(documents)
    monkeypatch.setattr(
        canary,
        "_read_canary_master_control",
        lambda: (next(remaining), "direct"),
    )


def test_native_only_mode_passes_without_header_evidence_or_attestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)
    disabled = _control(False)
    _set_master(monkeypatch, [disabled, disabled, disabled])

    report = canary.run_canary(
        "codex",
        execute=True,
        mode="native-only",
        confirm="RUN LIVE codex NATIVE-ONLY CANARY",
        db_path=path,
        inspector=_native,
        backend_factory=lambda *_args, **_kwargs: _NativeCodexBackend(path),
    )

    assert report["mode"] == "native-only"
    assert report["canary_passed"] is True
    assert report["attestation_persisted"] is False
    assert report["invocation"]["header_valid"] is False
    assert all(count == 0 for count in report["evidence"]["counts"].values())
    assert Store(path).get_host_canary_attestation("codex") is None


@pytest.mark.parametrize(
    ("emit_evidence", "output", "expected_failure"),
    [
        (True, "native", "Agency runtime evidence was emitted in native-only mode"),
        (False, "", "host invocation did not return a nonempty response"),
        (
            False,
            "Agency/Agencies loaded: reviewer\n"
            "Agency/Agencies delegated: none\n"
            "Skills loaded: none\n"
            "Actual Model selected: test\n"
            "Why: test\n"
            "How it shaped outcome: test",
            "Agency response header was present in native-only mode",
        ),
    ],
)
def test_native_only_mode_rejects_any_agency_activity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    emit_evidence: bool,
    output: str,
    expected_failure: str,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)
    disabled = _control(False)
    _set_master(monkeypatch, [disabled, disabled])

    report = canary.run_canary(
        "codex",
        execute=True,
        mode="native-only",
        confirm="RUN LIVE codex NATIVE-ONLY CANARY",
        db_path=path,
        inspector=_native,
        backend_factory=lambda *_args, **_kwargs: _NativeCodexBackend(
            path,
            emit_evidence=emit_evidence,
            output=output,
        ),
    )

    assert report["canary_passed"] is False
    assert expected_failure in report["unmet_prerequisites"]


@pytest.mark.parametrize(
    ("mode", "enabled", "required"),
    [
        ("agency", False, "must be enabled"),
        ("native-only", True, "must be disabled"),
    ],
)
def test_mode_mismatch_fails_before_backend_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    enabled: bool,
    required: str,
) -> None:
    monkeypatch.setattr(
        canary,
        "_read_canary_master_control",
        lambda: (_control(enabled), "direct"),
    )

    report = canary.run_canary(
        "codex",
        execute=True,
        mode=mode,
        confirm=(
            "RUN LIVE codex CANARY" if mode == "agency" else "RUN LIVE codex NATIVE-ONLY CANARY"
        ),
        db_path=tmp_path / "agency.db",
        inspector=_native,
        backend_factory=lambda *_args, **_kwargs: pytest.fail("backend must not run"),
    )

    assert report["ready"] is False
    assert report["live_attempted"] is False
    assert required in report["unmet_prerequisites"][-1]


def test_master_control_drift_fails_closed_after_invocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)
    _set_master(monkeypatch, [_control(False, 4), _control(False, 5)])

    report = canary.run_canary(
        "codex",
        execute=True,
        mode="native-only",
        confirm="RUN LIVE codex NATIVE-ONLY CANARY",
        db_path=path,
        inspector=_native,
        backend_factory=lambda *_args, **_kwargs: _NativeCodexBackend(path),
    )

    assert report["canary_passed"] is False
    assert report["unmet_prerequisites"][-1] == (
        "Agency master control changed during the canary invocation"
    )


def test_master_control_read_failure_after_invocation_is_sanitized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)
    calls = 0

    def read_control():
        nonlocal calls
        calls += 1
        if calls == 1:
            return _control(False), "direct"
        raise OSError("private control path")

    monkeypatch.setattr(canary, "_read_canary_master_control", read_control)
    report = canary.run_canary(
        "codex",
        execute=True,
        mode="native-only",
        confirm="RUN LIVE codex NATIVE-ONLY CANARY",
        db_path=path,
        inspector=_native,
        backend_factory=lambda *_args, **_kwargs: _NativeCodexBackend(path),
    )

    assert report["canary_passed"] is False
    assert report["unmet_prerequisites"][-1] == (
        "authoritative Agency master control could not be re-read after invocation"
    )
    assert "private control path" not in str(report)


def test_master_control_drift_before_completion_invalidates_native_proof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)
    disabled = _control(False, 4)
    _set_master(monkeypatch, [disabled, disabled, _control(False, 5)])

    report = canary.run_canary(
        "codex",
        execute=True,
        mode="native-only",
        confirm="RUN LIVE codex NATIVE-ONLY CANARY",
        db_path=path,
        inspector=_native,
        backend_factory=lambda *_args, **_kwargs: _NativeCodexBackend(path),
    )

    assert report["canary_passed"] is False
    assert report["attestation_persisted"] is False
    assert report["unmet_prerequisites"][-1] == (
        "Agency master control changed before canary completion"
    )


def test_isolated_control_projection_materializes_both_states(tmp_path: Path) -> None:
    runtime_home = tmp_path / "runtime"
    (runtime_home / "home").mkdir(parents=True)

    disabled = canary._project_isolated_runtime_control(runtime_home, enabled=False)
    assert disabled["enabled"] is False
    enabled = canary._project_isolated_runtime_control(runtime_home, enabled=True)
    assert enabled["enabled"] is True


def test_isolated_control_projection_rejects_unverified_postcondition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import runtime_control

    runtime_home = tmp_path / "runtime"
    (runtime_home / "home").mkdir(parents=True)
    monkeypatch.setattr(
        runtime_control,
        "read_authoritative_runtime_control",
        lambda **_kwargs: (_control(True), "dashboard"),
    )

    with pytest.raises(RuntimeError, match="projection failed"):
        canary._project_isolated_runtime_control(runtime_home, enabled=True)


def test_invalid_mode_and_unreadable_master_control_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="unsupported canary mode"):
        canary.run_canary("codex", mode="maybe", inspector=_native)

    monkeypatch.setattr(
        canary,
        "_read_canary_master_control",
        lambda: (_ for _ in ()).throw(OSError("private detail")),
    )
    report = canary.run_canary("codex", db_path=tmp_path / "db", inspector=_native)
    assert report["ready"] is False
    assert report["unmet_prerequisites"] == [
        "authoritative Agency master control could not be read"
    ]
