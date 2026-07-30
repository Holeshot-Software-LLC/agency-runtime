"""Truthful host-canary readiness and evidence correlation."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

import agency_runtime.core.canary as canary_module
from agency_runtime.core.canary import (
    CODEX_CANARY_EXEC_OPTIONS,
    CODEX_CURRENT_PROFILE_EXEC_OPTIONS,
    _backend,
    run_canary,
)
from agency_runtime.core.delegation.backends import BoundedProcessResult
from agency_runtime.core.header.finalize import response_hash
from agency_runtime.core.installer import (
    INSTALL_MANIFEST,
    PLUGIN_VERSION,
    inspect_host_installations,
    install_agent_adapter,
)
from agency_runtime.core.installer_contracts import CODEX_HOOK_EVENTS
from agency_runtime.core.store.sqlite import Store


def _ready_host(host: str) -> dict:
    return {
        "host": host,
        "discovered": True,
        "executable_discovered": True,
        "registered": True,
        "enabled": True,
        "loaded": None,
        "canary": None,
        "maturity": "enabled-runtime-unverified",
        "host_version": f"{host} 1.0.0",
        "install_id": f"{host}-install-1",
        "bundle_digest": "a" * 64,
    }


def _valid_header() -> str:
    return (
        "Agency/Agencies loaded: canary-specialist\n"
        "Agency/Agencies delegated: none - single-host canary\n"
        "Skills loaded: none - no skill required\n"
        "Actual Model selected: canary-provider/model\n"
        "Recruited via: deterministic\n"
        "Why: exercise the installed runtime\n"
        "How it shaped outcome: proved the final response contract\n\n"
        "Canary complete."
    )


def _hook_trust_report(status: str = "trusted") -> dict[str, object]:
    events = tuple(event[0].lower() + event[1:] for event in CODEX_HOOK_EVENTS)
    return {
        "status": status,
        "expected_count": len(events),
        "observed_count": len(events),
        "trusted_count": len(events) if status == "trusted" else 0,
        "managed_count": 0,
        "modified_count": len(events) if status == "modified" else 0,
        "untrusted_count": len(events) if status == "untrusted" else 0,
        "disabled_count": 0,
        "missing_count": 0,
        "unexpected_count": 0,
        "duplicate_count": 0,
        "warning_count": 0,
        "error_count": 0,
        "events": {
            event: {
                "enabled": True,
                "trustStatus": status,
                "currentHash": "sha256:" + "a" * 64,
            }
            for event in events
        },
    }


def _start_canary_turn(
    store: Store,
    *,
    trace_id: str,
    session_id: str,
    host: str,
    task: str,
    context_fingerprint: str,
) -> None:
    store.create_run(
        trace_id=trace_id,
        session_id=session_id,
        host=host,
    )
    store.record_routing_decision(
        trace_id=trace_id,
        session_id=session_id,
        query_hash=hashlib.sha256(task.encode("utf-8")).hexdigest(),
        context_fingerprint=context_fingerprint,
        decision={"status": "selected", "selected_ids": ["code-reviewer"]},
    )
    store.record_specialist_loaded(
        session_id,
        "code-reviewer",
        trace_id=trace_id,
    )


def _commit_accepted_canary_turn(
    store: Store,
    *,
    trace_id: str,
    session_id: str,
    host: str,
) -> None:
    snapshot = store.get_completion_evidence_snapshot(session_id, trace_id)
    result = store.commit_terminal_finalization(
        session_id=session_id,
        trace_id=trace_id,
        host=host,
        action="accept",
        response_hash=response_hash(_valid_header()),
        status="completed",
        expected_evidence_revision=snapshot["evidence_revision"],
    )
    assert result["authoritative"] is True


def test_readiness_is_nonmutating_and_never_claims_a_live_canary(
    tmp_path: Path,
) -> None:
    path = tmp_path / "does-not-exist.db"
    report = run_canary(
        "claude",
        db_path=path,
        inspector=_ready_host,
    )

    assert report["ready"] is True
    assert report["execute_confirmation"] == "RUN LIVE claude CANARY"
    assert report["live_attempted"] is False
    assert report["canary_passed"] is False
    assert path.exists() is False


def test_current_profile_codex_readiness_requires_distinct_confirmation(
    tmp_path: Path,
) -> None:
    report = run_canary(
        "codex",
        db_path=tmp_path / "missing.db",
        inspector=_ready_host,
        profile_scope="current-profile",
    )

    assert report["ready"] is True
    assert report["profile_scope"] == "current-profile"
    assert report["execute_confirmation"] == "RUN LIVE codex CURRENT-PROFILE CANARY"


def test_current_profile_canary_rejects_invalid_scope_and_non_codex_modes(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported canary profile scope"):
        run_canary("codex", db_path=tmp_path / "db", profile_scope="unknown")
    with pytest.raises(ValueError, match="support Codex Agency mode only"):
        run_canary(
            "claude",
            db_path=tmp_path / "db",
            profile_scope="current-profile",
        )
    with pytest.raises(ValueError, match="support Codex Agency mode only"):
        run_canary(
            "codex",
            db_path=tmp_path / "db",
            mode="native-only",
            profile_scope="current-profile",
        )


def test_live_canary_requires_exact_confirmation_before_backend_execution(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)

    def unexpected_backend(*_args, **_kwargs):
        raise AssertionError("backend must not run without exact confirmation")

    report = run_canary(
        "claude",
        execute=True,
        confirm="yes",
        db_path=path,
        inspector=_ready_host,
        backend_factory=unexpected_backend,
    )

    assert report["live_attempted"] is False
    assert report["canary_passed"] is False
    assert "RUN LIVE claude CANARY" in report["unmet_prerequisites"][-1]


def test_unavailable_evidence_store_fails_before_live_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    class UnavailableStore:
        def __init__(self, _path: Path) -> None:
            raise OSError("private storage detail")

    def unexpected_backend(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("backend must not run without an evidence store")

    monkeypatch.setattr(canary_module, "Store", UnavailableStore)
    monkeypatch.setattr(
        canary_module.secrets,
        "token_hex",
        lambda _size: (_ for _ in ()).throw(
            AssertionError("a nonce must not be created before the evidence store")
        ),
    )
    report = run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CANARY",
        db_path=tmp_path / "agency.db",
        inspector=_ready_host,
        backend_factory=unexpected_backend,
    )

    assert report["live_attempted"] is False
    assert report["unmet_prerequisites"] == ["runtime evidence store is unavailable"]
    assert "private storage detail" not in json.dumps(report)
    assert called is False


def test_unavailable_backend_fails_before_live_attempt(tmp_path: Path) -> None:
    path = tmp_path / "agency.db"
    Store(path)

    def unavailable_backend(*_args, **_kwargs):
        raise RuntimeError("private backend detail")

    report = run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CANARY",
        db_path=path,
        inspector=_ready_host,
        backend_factory=unavailable_backend,
    )

    assert report["live_attempted"] is False
    assert report["unmet_prerequisites"] == ["safe noninteractive canary backend is unavailable"]
    assert "private backend detail" not in json.dumps(report)


def test_post_invocation_evidence_failure_preserves_attempt_truth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingEvidenceStore:
        def __init__(self, _path: Path) -> None:
            self.reads = 0

        def recent_runtime_activity(self, *, limit: int):
            assert limit == 200
            self.reads += 1
            if self.reads == 1:
                return {}
            raise OSError("private post-invocation detail")

    class Backend:
        def execute(self, **_kwargs):
            return {
                "backend": "codex",
                "status": "completed",
                "exit_code": 0,
                "output": _valid_header(),
            }

    monkeypatch.setattr(canary_module, "Store", FailingEvidenceStore)
    report = run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CANARY",
        db_path=tmp_path / "agency.db",
        inspector=_ready_host,
        backend_factory=lambda *_args, **_kwargs: Backend(),
    )

    assert report["live_attempted"] is True
    assert report["canary_passed"] is False
    assert report["unmet_prerequisites"] == [
        "exact activation evidence could not be read after host invocation"
    ]
    assert "private post-invocation detail" not in json.dumps(report)


def test_proof_failures_are_complete_ordered_and_safely_rendered(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)

    class FailedBackend:
        def execute(self, **_kwargs):
            return {
                "backend": "codex",
                "status": "timed_out",
                "exit_code": 124,
                "stdout_truncated": True,
                "stderr_truncated": True,
                "failure_reason": "codex_exec_timed_out",
                "output": "not a valid header",
            }

    report = run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CANARY",
        db_path=path,
        inspector=_ready_host,
        backend_factory=lambda *_args, **_kwargs: FailedBackend(),
    )

    assert report["invocation"]["timed_out"] is True
    assert report["invocation"]["stdout_truncated"] is True
    assert report["invocation"]["stderr_truncated"] is True
    assert report["invocation"]["failure_reason"] == "codex_exec_timed_out"
    assert report["unmet_prerequisites"] == [
        "host invocation did not complete successfully",
        "canary profile plugin registration and enablement were not proven",
        "final response header was not proven",
        "exact Codex activation evidence was not proven (route_not_found)",
    ]


def test_canary_report_preserves_allowlisted_projection_failure_reason(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)

    class FailedProjectionBackend:
        def execute(self, **_kwargs):
            return {
                "backend": "codex",
                "status": "failed",
                "exit_code": 0,
                "failure_reason": "codex_result_projection_unavailable",
            }

    report = run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CANARY",
        db_path=path,
        inspector=_ready_host,
        backend_factory=lambda *_args, **_kwargs: FailedProjectionBackend(),
    )

    assert report["invocation"]["exit_code"] == 0
    assert report["invocation"]["failure_reason"] == ("codex_result_projection_unavailable")


def test_canary_report_omits_unhashable_projection_metadata(tmp_path: Path) -> None:
    path = tmp_path / "agency.db"
    Store(path)

    class MalformedProjectionBackend:
        def execute(self, **_kwargs):
            return {
                "backend": "codex",
                "status": "failed",
                "exit_code": 1,
                "failure_reason": [],
                "model_invocation_attempted": "false",
            }

    report = run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CANARY",
        db_path=path,
        inspector=_ready_host,
        backend_factory=lambda *_args, **_kwargs: MalformedProjectionBackend(),
    )

    assert "failure_reason" not in report["invocation"]
    assert "model_invocation_attempted" not in report["invocation"]


def test_tokenless_evidence_cannot_reach_attestation_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)

    class FailingAttestationStore(Store):
        def record_host_canary_attestation(self, **_kwargs):
            raise OSError("private persistence detail")

    class EvidenceBackend:
        def execute(self, **kwargs):
            trace_id = "attestation-write-failure"
            session_id = "attestation-session"
            store = Store(path)
            _start_canary_turn(
                store,
                trace_id=trace_id,
                session_id=session_id,
                host="codex",
                task=kwargs["task"],
                context_fingerprint="a" * 64,
            )
            _commit_accepted_canary_turn(
                store,
                trace_id=trace_id,
                session_id=session_id,
                host="codex",
            )
            return {
                "backend": "codex",
                "profile_scope": "isolated-profile",
                "isolated_plugin": {"registered": True, "enabled": True},
                "status": "completed",
                "exit_code": 0,
                "output": _valid_header(),
            }

    monkeypatch.setattr(canary_module, "Store", FailingAttestationStore)
    report = run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CANARY",
        db_path=path,
        inspector=_ready_host,
        backend_factory=lambda *_args, **_kwargs: EvidenceBackend(),
    )

    assert report["invocation"]["header_valid"] is True
    assert report["evidence"]["proven"] is False
    assert report["evidence"]["reason"] == "route_not_found"
    assert report["attestation_persisted"] is False
    assert report["canary_passed"] is False
    assert report["unmet_prerequisites"] == [
        "exact Codex activation evidence was not proven (route_not_found)"
    ]
    assert "private persistence detail" not in json.dumps(report)


def test_live_canary_passes_only_with_correlated_runtime_evidence(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)

    def backend_factory(host: str, *, db_path: Path, timeout: float):
        assert host == "claude"
        assert timeout == 10

        class FakeBackend:
            def execute(self, **kwargs):
                assert list(Path(kwargs["workdir"]).iterdir()) == []
                store = Store(db_path)
                trace_id = "trace-live-canary"
                session_id = "session-live-canary"
                _start_canary_turn(
                    store,
                    trace_id=trace_id,
                    session_id=session_id,
                    host=host,
                    task=kwargs["task"],
                    context_fingerprint="b" * 64,
                )
                store.record_model_receipt(
                    trace_id=trace_id,
                    session_id=session_id,
                    host=host,
                    resolved_provider="canary-provider",
                    resolved_model="model",
                    status="success",
                )
                _commit_accepted_canary_turn(
                    store,
                    trace_id=trace_id,
                    session_id=session_id,
                    host=host,
                )
                return {
                    "backend": host,
                    "profile_scope": "isolated-profile",
                    "isolated_plugin": {
                        "load_requested": True,
                        "registered": None,
                        "enabled": None,
                    },
                    "status": "completed",
                    "exit_code": 0,
                    "output": _valid_header(),
                }

        return FakeBackend()

    report = run_canary(
        "claude",
        execute=True,
        confirm="RUN LIVE claude CANARY",
        db_path=path,
        timeout=10,
        inspector=_ready_host,
        backend_factory=backend_factory,
    )

    assert report["live_attempted"] is True
    assert report["invocation"]["header_valid"] is True
    assert report["evidence"]["correlated_trace_ids"] == ["trace-live-canary"]
    assert report["evidence"]["accepted_trace_ids"] == ["trace-live-canary"]
    assert report["evidence"]["expected_specialist_selected"] is True
    assert report["evidence"]["expected_specialist_loaded"] is True
    assert report["canary_passed"] is True
    assert report["attestation_persisted"] is False
    assert "stdout" not in report["invocation"]
    attestation = Store(path).get_host_canary_attestation("claude")
    assert attestation is None


def test_successful_process_without_evidence_cannot_pass(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)

    class NoEvidenceBackend:
        def execute(self, **_kwargs):
            return {
                "backend": "claude",
                "profile_scope": "isolated-profile",
                "isolated_plugin": {
                    "load_requested": True,
                    "registered": None,
                    "enabled": None,
                },
                "status": "completed",
                "exit_code": 0,
                "output": _valid_header(),
            }

    report = run_canary(
        "claude",
        execute=True,
        confirm="RUN LIVE claude CANARY",
        db_path=path,
        inspector=_ready_host,
        backend_factory=lambda *_args, **_kwargs: NoEvidenceBackend(),
    )

    assert report["invocation"]["header_valid"] is True
    assert report["canary_passed"] is False
    assert report["evidence"]["correlated_trace_ids"] == []
    assert report["invocation"]["isolated_plugin"] == {
        "load_requested": True,
        "registered": None,
        "enabled": None,
        "loaded": None,
        "invoked": None,
    }


def test_valid_header_with_continue_event_and_active_run_cannot_pass(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)

    class CorrectionOnlyBackend:
        def execute(self, **kwargs):
            store = Store(path)
            trace_id = "correction-only-turn"
            session_id = "correction-only-session"
            _start_canary_turn(
                store,
                trace_id=trace_id,
                session_id=session_id,
                host="codex",
                task=kwargs["task"],
                context_fingerprint="c" * 64,
            )
            store.record_finalization(
                trace_id=trace_id,
                host="codex",
                action="continue",
            )
            return {
                "backend": "codex",
                "profile_scope": "isolated-profile",
                "isolated_plugin": {"registered": True, "enabled": True},
                "status": "completed",
                "exit_code": 0,
                "output": _valid_header(),
            }

    report = run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CANARY",
        db_path=path,
        inspector=_ready_host,
        backend_factory=lambda *_args, **_kwargs: CorrectionOnlyBackend(),
    )

    assert report["invocation"]["header_valid"] is True
    assert report["evidence"]["proven"] is False
    assert report["evidence"]["reason"] == "route_not_found"
    assert report["canary_passed"] is False
    assert report["attestation_persisted"] is False
    assert report["unmet_prerequisites"] == [
        "exact Codex activation evidence was not proven (route_not_found)"
    ]
    assert Store(path).get_run("correction-only-turn")["status"] == "canary_failed"
    assert report["failed_run_cleanup"]["closed_count"] == 1


def test_failed_canary_cleanup_is_request_scoped_without_routing_evidence(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)

    class TimedOutBackend:
        def execute(self, **kwargs):
            store = Store(path)
            fingerprint = hashlib.sha256(kwargs["task"].encode("utf-8")).hexdigest()
            store.begin_preflight_attempt(
                trace_id="timed-out-canary",
                session_id="timed-out-canary-session",
                host="codex",
                request_fingerprint=fingerprint,
                request_kind="nontrivial",
            )
            store.begin_preflight_attempt(
                trace_id="concurrent-unrelated-turn",
                session_id="concurrent-unrelated-session",
                host="codex",
                request_fingerprint="f" * 64,
                request_kind="nontrivial",
            )
            return {
                "backend": "codex",
                "profile_scope": "isolated-profile",
                "isolated_plugin": {"registered": True, "enabled": True},
                "status": "timed_out",
                "exit_code": 124,
                "output": "",
            }

    report = run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CANARY",
        db_path=path,
        inspector=_ready_host,
        backend_factory=lambda *_args, **_kwargs: TimedOutBackend(),
    )

    store = Store(path)
    assert report["canary_passed"] is False
    assert report["failed_run_cleanup"]["candidate_count"] == 1
    assert report["failed_run_cleanup"]["closed_count"] == 1
    assert store.get_run("timed-out-canary")["status"] == "canary_failed"
    assert store.get_run("concurrent-unrelated-turn")["status"] == "active"


def test_claude_real_shape_canary_passes_without_synthesizing_a_receipt(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)

    class CodexHookShapeBackend:
        def execute(self, **kwargs):
            store = Store(path)
            trace_id = "claude-turn-42"
            session_id = "claude-session"
            _start_canary_turn(
                store,
                trace_id=trace_id,
                session_id=session_id,
                host="claude",
                task=kwargs["task"],
                context_fingerprint="d" * 64,
            )
            _commit_accepted_canary_turn(
                store,
                trace_id=trace_id,
                session_id=session_id,
                host="claude",
            )
            return {
                "backend": "claude",
                "profile_scope": "isolated-profile",
                "isolated_plugin": {
                    "load_requested": True,
                    "registered": None,
                    "enabled": None,
                },
                "status": "completed",
                "exit_code": 0,
                "output": _valid_header(),
            }

    report = run_canary(
        "claude",
        execute=True,
        confirm="RUN LIVE claude CANARY",
        db_path=path,
        inspector=_ready_host,
        backend_factory=lambda *_args, **_kwargs: CodexHookShapeBackend(),
    )

    assert report["evidence"]["receipt_required"] is False
    assert report["evidence"]["receipt_proven"] is False
    assert report["evidence"]["host_receipt_count"] == 0
    assert report["canary_passed"] is True
    assert report["attestation_persisted"] is False
    assert Store(path).get_host_canary_attestation("claude") is None


def test_codex_tokenless_isolated_profile_cannot_attest_activation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)
    real_profile = {
        **_ready_host("codex"),
        "registered": False,
        "enabled": False,
    }

    class IsolatedCodexBackend:
        def execute(self, **kwargs):
            store = Store(path)
            trace_id = "codex-isolated-turn"
            session_id = "codex-isolated-session"
            _start_canary_turn(
                store,
                trace_id=trace_id,
                session_id=session_id,
                host="codex",
                task=kwargs["task"],
                context_fingerprint="f" * 64,
            )
            _commit_accepted_canary_turn(
                store,
                trace_id=trace_id,
                session_id=session_id,
                host="codex",
            )
            return {
                "backend": "codex",
                "profile_scope": "isolated-profile",
                "isolated_plugin": {
                    "registered": True,
                    "enabled": True,
                },
                "status": "completed",
                "exit_code": 0,
                "output": _valid_header(),
            }

    report = run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CANARY",
        db_path=path,
        inspector=lambda _host: real_profile,
        backend_factory=lambda *_args, **_kwargs: IsolatedCodexBackend(),
    )

    assert report["ready"] is True
    assert report["real_profile_native"]["registered"] is False
    assert report["real_profile_native"]["enabled"] is False
    assert report["invocation"]["profile_scope"] == "isolated-profile"
    assert report["canary_passed"] is False
    assert report["evidence"]["proven"] is False
    assert report["evidence"]["reason"] == "route_not_found"
    attestation = Store(path).get_host_canary_attestation("codex")
    assert attestation is None


def test_unsupported_host_canary_fails_closed_before_backend_execution(
    tmp_path: Path,
) -> None:
    called = False

    def unexpected_backend(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("unsafe backend must not run")

    report = run_canary(
        "openclaw",
        execute=True,
        confirm="RUN LIVE openclaw CANARY",
        db_path=tmp_path / "agency.db",
        inspector=_ready_host,
        backend_factory=unexpected_backend,
    )

    assert report["ready"] is False
    assert report["live_attempted"] is False
    assert report["canary_passed"] is False
    assert called is False
    assert any("no proven read-only" in item for item in report["unmet_prerequisites"])


def test_codex_safe_backend_isolates_auth_plugins_config_and_secrets(
    tmp_path: Path,
) -> None:
    injected_home = tmp_path / "injected-user-home"
    real_home = injected_home / ".codex"
    real_home.mkdir(parents=True)
    secret = "codex-auth-secret-never-log"
    (real_home / "auth.json").write_text(
        json.dumps({"token": secret}),
        encoding="utf-8",
    )
    config = real_home / "config.toml"
    config.write_text('model = "real-profile"\n', encoding="utf-8")
    marketplace = tmp_path / "managed-marketplace"
    (marketplace / ".agents" / "plugins").mkdir(parents=True)
    (marketplace / ".agents" / "plugins" / "marketplace.json").write_text(
        "{}",
        encoding="utf-8",
    )
    db_path = tmp_path / "agency.db"
    Store(db_path)
    calls: list[dict] = []
    final = "\n".join(
        (
            json.dumps(
                {
                    "type": "thread.started",
                    "thread_id": "019fa6a6-9432-7c70-a594-68ccdf7e4988",
                }
            ),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": _valid_header()},
                }
            ),
            json.dumps({"type": "turn.completed"}),
        )
    )

    def runner(argv: list[str], **kwargs):
        calls.append({"argv": list(argv), **kwargs})
        assert json.loads(
            (Path(kwargs["env"]["CODEX_HOME"]) / "auth.json").read_text(encoding="utf-8")
        ) == {"token": secret}
        stdout = (
            final
            if argv[1:2] == ["exec"]
            else json.dumps(
                [
                    {
                        "pluginId": "agency-preflight@agency-runtime",
                        "installed": True,
                        "enabled": True,
                    }
                ]
            )
            if argv[1:3] == ["plugin", "list"]
            else "{}"
        )
        return BoundedProcessResult(0, stdout, "")

    backend = _backend(
        "codex",
        db_path=db_path,
        timeout=10,
        native={"managed_target": str(marketplace)},
        resolver=lambda _name: "C:/tools/codex.exe",
        runner=runner,
        master_enabled=False,
        environ={
            "HOME": str(injected_home),
            "PATH": "C:/tools",
            "OPENAI_API_KEY": "must-not-forward",
        },
    )
    workdir = tmp_path / "empty-workdir"
    workdir.mkdir()
    result = backend.execute(
        task="nonce-bound canary",
        workdir=str(workdir),
        check=False,
    )

    assert result["status"] == "completed"
    assert result["output"] == _valid_header()
    assert result["collaboration"]["spawn_count"] == 0
    assert result["collaboration"]["wait_count"] == 0
    assert "--ephemeral" in calls[-1]["argv"]
    assert "agents.enabled=false" in calls[-1]["argv"]
    assert "multi_agent_v2" not in calls[-1]["argv"]
    assert (real_home / "auth.json").read_text(encoding="utf-8") == json.dumps({"token": secret})
    assert config.read_text(encoding="utf-8") == 'model = "real-profile"\n'
    flattened_argv = json.dumps([call["argv"] for call in calls])
    assert secret not in flattened_argv
    assert secret not in json.dumps(result)
    assert "OPENAI_API_KEY" not in calls[-1]["env"]
    assert calls[-1]["env"]["AGENCY_CANARY_MODE"] == "1"
    assert calls[-1]["env"]["AGENCY_CANARY_MASTER_ENABLED"] == "0"
    assert Path(calls[-1]["env"]["AGENCY_CANARY_CONTROL_PATH"]).parts[-3:] == (
        ".agency-runtime",
        "run",
        "control.json",
    )
    assert calls[-1]["env"]["CODEX_HOME"] != str(real_home)
    assert not Path(calls[-1]["env"]["CODEX_HOME"]).exists()
    assert "features.shell_tool=false" in calls[-1]["argv"]
    assert "features.unified_exec=false" in calls[-1]["argv"]
    assert 'web_search="disabled"' in calls[-1]["argv"]
    assert "apps._default.enabled=false" in calls[-1]["argv"]
    assert "mcp_servers={}" in calls[-1]["argv"]
    assert "--ignore-user-config" not in calls[-1]["argv"]
    assert "--ignore-rules" in calls[-1]["argv"]
    assert "--dangerously-bypass-hook-trust" in calls[-1]["argv"]
    assert list(workdir.iterdir()) == []


def test_claude_canary_loads_managed_plugin_without_safe_mode_or_profile_settings(
    tmp_path: Path,
) -> None:
    real_home = tmp_path / "real-claude"
    real_home.mkdir()
    secret = "claude-auth-secret-never-log"
    (real_home / ".credentials.json").write_text(
        json.dumps({"token": secret}),
        encoding="utf-8",
    )
    settings = real_home / "settings.json"
    settings.write_text(
        json.dumps({"hooks": {"unsafe-user-hook": []}}),
        encoding="utf-8",
    )
    marketplace = tmp_path / "managed-marketplace"
    plugin_dir = marketplace / "plugins" / "agency-preflight"
    (plugin_dir / ".claude-plugin").mkdir(parents=True)
    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
        "{}",
        encoding="utf-8",
    )
    db_path = tmp_path / "agency.db"
    Store(db_path)
    calls: list[dict] = []

    def runner(argv: list[str], **kwargs):
        calls.append({"argv": list(argv), **kwargs})
        isolated = Path(kwargs["env"]["CLAUDE_CONFIG_DIR"])
        assert isolated != real_home
        assert (isolated / ".credentials.json").read_text(encoding="utf-8") == json.dumps(
            {"token": secret}
        )
        assert not (isolated / "settings.json").exists()
        return BoundedProcessResult(
            0,
            json.dumps({"result": _valid_header()}),
            "",
        )

    backend = _backend(
        "claude",
        db_path=db_path,
        timeout=10,
        native={"managed_target": str(marketplace)},
        resolver=lambda _name: "C:/tools/claude.exe",
        runner=runner,
        environ={
            "CLAUDE_CONFIG_DIR": str(real_home),
            "HOME": str(tmp_path / "user-home"),
            "PATH": "C:/tools",
            "ANTHROPIC_API_KEY": "must-not-forward",
        },
    )
    workdir = tmp_path / "empty-claude-workdir"
    workdir.mkdir()
    result = backend.execute(
        task="nonce-bound canary",
        workdir=str(workdir),
        check=False,
    )

    assert result["status"] == "completed"
    assert result["profile_scope"] == "isolated-profile"
    assert result["isolated_plugin"] == {
        "load_requested": True,
        "registered": None,
        "enabled": None,
    }
    argv = calls[0]["argv"]
    assert "--safe-mode" not in argv
    assert argv[argv.index("--plugin-dir") + 1] == str(plugin_dir)
    assert argv[argv.index("--setting-sources") + 1] == ""
    assert argv[argv.index("--tools") + 1] == ""
    assert "mcp__*" in argv
    assert "--strict-mcp-config" in argv
    assert "--no-session-persistence" in argv
    assert "ANTHROPIC_API_KEY" not in calls[0]["env"]
    assert calls[0]["env"]["AGENCY_CANARY_MODE"] == "1"
    assert calls[0]["env"]["AGENCY_CANARY_MASTER_ENABLED"] == "1"
    assert Path(calls[0]["env"]["AGENCY_CANARY_CONTROL_PATH"]).parts[-3:] == (
        ".agency-runtime",
        "run",
        "control.json",
    )
    assert not Path(calls[0]["env"]["CLAUDE_CONFIG_DIR"]).exists()
    assert settings.read_text(encoding="utf-8") == json.dumps({"hooks": {"unsafe-user-hook": []}})
    assert secret not in json.dumps(result)
    assert secret not in json.dumps(argv)
    assert list(workdir.iterdir()) == []


def test_current_codex_cli_exposes_every_canary_command_capability(
    tmp_path: Path,
) -> None:
    executable = shutil.which("codex")
    if executable is None:
        pytest.skip("Codex CLI is not installed")
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    environment = dict(os.environ)
    environment["CODEX_HOME"] = str(codex_home)

    def help_text(*arguments: str) -> str:
        completed = subprocess.run(
            [executable, *arguments, "--help"],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            check=False,
            text=True,
            timeout=15,
        )
        if completed.returncode != 0:
            pytest.skip(
                "Codex CLI was discovered but is not executable in this environment "
                f"(exit {completed.returncode})"
            )
        return completed.stdout

    exec_help = help_text("exec")
    for option in {
        "--json",
        "--color",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--strict-config",
        "--sandbox",
        "--config",
        "--skip-git-repo-check",
        "--dangerously-bypass-hook-trust",
    }:
        assert option in exec_help
    assert CODEX_CANARY_EXEC_OPTIONS[-1] == "-"
    assert "--ephemeral" not in CODEX_CANARY_EXEC_OPTIONS
    assert "--ephemeral" not in CODEX_CURRENT_PROFILE_EXEC_OPTIONS
    assert "--ignore-user-config" not in CODEX_CANARY_EXEC_OPTIONS
    assert "--ignore-rules" in CODEX_CANARY_EXEC_OPTIONS
    assert "multi_agent_v2" in CODEX_CANARY_EXEC_OPTIONS
    assert "--dangerously-bypass-hook-trust" not in CODEX_CURRENT_PROFILE_EXEC_OPTIONS
    assert "--json" in help_text("plugin", "marketplace", "add")
    assert "--json" in help_text("plugin", "add")
    plugin_list_help = help_text("plugin", "list")
    assert "--json" in plugin_list_help
    assert "--marketplace" in plugin_list_help


def test_current_profile_codex_canary_uses_real_profile_without_trust_bypass(
    tmp_path: Path,
) -> None:
    marketplace = tmp_path / "marketplace"
    (marketplace / ".agents" / "plugins").mkdir(parents=True)
    (marketplace / ".agents" / "plugins" / "marketplace.json").write_text(
        "{}",
        encoding="utf-8",
    )
    real_home = tmp_path / "codex-home"
    real_home.mkdir()
    db_path = tmp_path / "agency.db"
    Store(db_path)
    calls: list[dict] = []

    def runner(argv: list[str], **kwargs):
        calls.append({"argv": list(argv), **kwargs})
        return BoundedProcessResult(
            0,
            "\n".join(
                [
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {"type": "agent_message", "text": _valid_header()},
                        }
                    ),
                    json.dumps({"type": "turn.completed"}),
                ]
            ),
            "",
        )

    backend = _backend(
        "codex",
        db_path=db_path,
        timeout=10,
        native={"managed_target": str(marketplace)},
        resolver=lambda _name: "C:/tools/codex.exe",
        runner=runner,
        environ={"CODEX_HOME": str(real_home), "HOME": str(tmp_path), "PATH": "C:/tools"},
        profile_scope="current-profile",
        require_exact_activation_rollout=True,
        hook_trust_inspector=lambda *_args, **_kwargs: _hook_trust_report(),
    )
    workdir = tmp_path / "empty-workdir"
    workdir.mkdir()
    result = backend.execute(task="current profile canary", workdir=str(workdir))

    assert result["status"] == "completed"
    assert result["profile_scope"] == "current-profile"
    assert "isolated_plugin" not in result
    assert len(calls) == 1
    assert calls[0]["argv"][1] == "exec"
    assert "--dangerously-bypass-hook-trust" not in calls[0]["argv"]
    assert calls[0]["env"]["CODEX_HOME"] == str(real_home)
    assert calls[0]["env"]["AGENCY_CANARY_MODE"] == "1"


def test_current_profile_codex_canary_fails_before_model_when_hook_trust_is_stale(
    tmp_path: Path,
) -> None:
    marketplace = tmp_path / "marketplace"
    (marketplace / ".agents" / "plugins").mkdir(parents=True)
    (marketplace / ".agents" / "plugins" / "marketplace.json").write_text(
        "{}",
        encoding="utf-8",
    )
    real_home = tmp_path / "codex-home"
    real_home.mkdir()
    db_path = tmp_path / "agency.db"
    Store(db_path)
    model_calls: list[dict] = []
    trust_calls: list[dict] = []

    def inspect(cwd: Path, **kwargs):
        trust_calls.append({"cwd": cwd, **kwargs})
        return _hook_trust_report("modified")

    backend = _backend(
        "codex",
        db_path=db_path,
        timeout=10,
        native={"managed_target": str(marketplace)},
        resolver=lambda _name: "C:/tools/codex.exe",
        runner=lambda *_args, **kwargs: model_calls.append(kwargs),
        environ={"CODEX_HOME": str(real_home), "HOME": str(tmp_path), "PATH": "C:/tools"},
        profile_scope="current-profile",
        require_exact_activation_rollout=True,
        hook_trust_inspector=inspect,
    )
    workdir = tmp_path / "empty-workdir"
    workdir.mkdir()

    result = backend.execute(task="current profile canary", workdir=str(workdir))

    assert result == {
        "backend": "codex",
        "profile_scope": "current-profile",
        "status": "failed",
        "exit_code": 1,
        "stdout_truncated": False,
        "stderr_truncated": False,
        "failure_reason": "codex_hook_trust_not_ready",
        "hook_trust": _hook_trust_report("modified"),
        "model_invocation_attempted": False,
        "trust_mode": "attended",
        "trust_bypass_used": False,
        "persistent_trust_changed": False,
    }
    assert model_calls == []
    assert len(trust_calls) == 1
    assert trust_calls[0]["cwd"] == workdir
    assert trust_calls[0]["executable"] == "C:/tools/codex.exe"
    assert trust_calls[0]["timeout"] <= 10
    assert trust_calls[0]["environ"]["CODEX_HOME"] == str(real_home)


def test_current_profile_codex_canary_timeout_and_backend_scope_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marketplace = tmp_path / "marketplace"
    (marketplace / ".agents" / "plugins").mkdir(parents=True)
    (marketplace / ".agents" / "plugins" / "marketplace.json").write_text(
        "{}",
        encoding="utf-8",
    )
    db_path = tmp_path / "agency.db"
    Store(db_path)
    monkeypatch.setattr(canary_module, "_remaining_canary_timeout", lambda *_a, **_kw: 0)
    backend = _backend(
        "codex",
        db_path=db_path,
        timeout=1,
        native={"managed_target": str(marketplace)},
        resolver=lambda _name: "codex",
        runner=lambda *_a, **_kw: pytest.fail("timed-out backend must not execute"),
        environ={"HOME": str(tmp_path), "PATH": "C:/tools"},
        profile_scope="current-profile",
    )
    result = backend.execute(task="canary", workdir=str(tmp_path))
    assert result["status"] == "timed_out"
    assert result["profile_scope"] == "current-profile"

    with pytest.raises(ValueError, match="unsupported canary profile scope"):
        _backend(
            "codex",
            db_path=db_path,
            timeout=1,
            native={"managed_target": str(marketplace)},
            resolver=lambda _name: "codex",
            profile_scope="unknown",
        )
    with pytest.raises(ValueError, match="support Codex only"):
        _backend(
            "claude",
            db_path=db_path,
            timeout=1,
            native={"managed_target": str(marketplace)},
            resolver=lambda _name: "claude",
            profile_scope="current-profile",
        )


def test_concurrent_same_trace_evidence_with_wrong_nonce_hash_cannot_pass(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    Store(path)

    class ConcurrentEvidenceBackend:
        def execute(self, **_kwargs):
            store = Store(path)
            trace_id = "shared-concurrent-trace"
            store.record_routing_decision(
                trace_id=trace_id,
                session_id="unrelated-session",
                query_hash="0" * 64,
                context_fingerprint="e" * 64,
                decision={"status": "selected", "selected_ids": ["unrelated"]},
            )
            store.record_finalization(
                trace_id=trace_id,
                host="claude",
                action="accept",
            )
            return {
                "backend": "claude",
                "profile_scope": "isolated-profile",
                "isolated_plugin": {
                    "load_requested": True,
                    "registered": None,
                    "enabled": None,
                },
                "status": "completed",
                "exit_code": 0,
                "output": _valid_header(),
            }

    report = run_canary(
        "claude",
        execute=True,
        confirm="RUN LIVE claude CANARY",
        db_path=path,
        inspector=_ready_host,
        backend_factory=lambda *_args, **_kwargs: ConcurrentEvidenceBackend(),
    )

    assert report["evidence"]["correlated_trace_ids"] == []
    assert report["canary_passed"] is False
    assert Store(path).get_host_canary_attestation("claude") is None


def test_inspection_uses_only_current_matching_canary_attestation(
    tmp_path: Path,
    monkeypatch,
    private_installer_launcher,
) -> None:
    db_path = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(db_path))
    staged = install_agent_adapter(
        "codex",
        home_dir=tmp_path,
        binary_resolver=lambda _name: "C:/fake/codex.exe",
    )
    assert staged["ok"] is True
    store = Store(db_path)

    identity: dict = {}

    def attest(
        version: str,
        *,
        profile_scope: str = "current-profile",
    ) -> None:
        store.record_host_canary_attestation(
            host="codex",
            proof_contract="agency.codex-activation-canary.v1",
            proof_digest="a" * 64,
            profile_scope=profile_scope,
            platform_system=platform.system(),
            platform_release=platform.release(),
            platform_machine=platform.machine(),
            host_version=identity["host_version"],
            plugin_version=version,
            install_id=identity["install_id"],
            bundle_digest=identity["bundle_digest"],
            trace_id="codex-turn-attested",
        )

    host_version = {"value": "codex-cli 0.144.1"}

    def runner(command: list[str], **_kwargs):
        joined = " ".join(command)
        if command[-1] == "--version":
            return {"returncode": 0, "stdout": host_version["value"]}
        if "marketplace list" in joined:
            return {
                "returncode": 0,
                "stdout": json.dumps([{"name": "agency-runtime"}]),
            }
        if "plugin list" in joined:
            return {
                "returncode": 0,
                "stdout": json.dumps(
                    [
                        {
                            "pluginId": "agency-preflight@agency-runtime",
                            "enabled": True,
                            "version": PLUGIN_VERSION,
                        }
                    ]
                ),
            }
        return {"returncode": 0, "stdout": "{}"}

    def inspect() -> dict:
        return inspect_host_installations(
            home_dir=tmp_path,
            binary_resolver=lambda _name: "C:/fake/codex.exe",
            command_runner=runner,
            hosts=["codex"],
        )[0]

    identity.update(inspect())
    attest(PLUGIN_VERSION)
    current = inspect()
    assert current["canary"] is True
    assert current["canary_attestation_status"] == "verified"

    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "UPDATE host_canary_attestations SET profile_scope = ? WHERE host = ?",
            ("isolated-profile", "codex"),
        )
        connection.commit()
    finally:
        connection.close()
    isolated = inspect()
    assert isolated["canary"] is None
    assert "profile_scope" in isolated["canary_stale_reasons"]
    attest(PLUGIN_VERSION)

    host_version["value"] = "codex-cli 0.145.0"
    upgraded_host = inspect()
    assert upgraded_host["canary"] is None
    assert "host_version" in upgraded_host["canary_stale_reasons"]
    host_version["value"] = identity["host_version"]

    attest("9.9.9")
    stale_attestation = inspect()
    assert stale_attestation["canary"] is None
    assert "plugin_version" in stale_attestation["canary_stale_reasons"]

    attest(PLUGIN_VERSION)
    manifest_path = Path(staged["target"]) / INSTALL_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    original_manifest = dict(manifest)
    manifest["install_id"] = "same-version-reinstall"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    reinstalled = inspect()
    assert reinstalled["canary"] is None
    assert "install_id" in reinstalled["canary_stale_reasons"]

    manifest_path.write_text(json.dumps(original_manifest), encoding="utf-8")
    owned_file = Path(staged["target"]) / original_manifest["owned_files"][0]
    original_payload = owned_file.read_text(encoding="utf-8")
    owned_file.write_text(original_payload + "\n", encoding="utf-8")
    changed_bundle = inspect()
    assert changed_bundle["canary"] is None
    assert "bundle_digest" in changed_bundle["canary_stale_reasons"]
    owned_file.write_text(original_payload, encoding="utf-8")

    manifest = dict(original_manifest)
    manifest["plugin_version"] = "0.0.0"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    stale_install = inspect()
    assert stale_install["canary"] is None
    assert "managed_plugin_version" in stale_install["canary_stale_reasons"]
