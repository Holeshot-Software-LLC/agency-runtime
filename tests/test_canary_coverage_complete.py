"""Complete host-canary safety, validation, and entrypoint coverage."""

from __future__ import annotations

import json
import runpy
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import canary, canary_backends
from agency_runtime.core.bounded_io import FileSizeLimitError
from agency_runtime.core.selector.policy import detect_actions, load_bundled_policy


def _result(**changes: Any) -> SimpleNamespace:
    value = {
        "returncode": 0,
        "timed_out": False,
        "stdout_truncated": False,
        "stderr_truncated": False,
        "stdout": "",
    }
    value.update(changes)
    return SimpleNamespace(**value)


def _native(host: str = "codex", **changes: Any) -> dict[str, Any]:
    value = {
        "host": host,
        "executable_discovered": True,
        "registered": True,
        "enabled": True,
        "host_version": "1.0",
        "install_id": "install",
        "bundle_digest": "digest",
    }
    value.update(changes)
    return value


def test_read_control_handles_missing_table_row_record_and_corrupt_db(tmp_path: Path) -> None:
    path = tmp_path / "control.db"
    sqlite3.connect(path).close()
    assert canary._read_control_without_writes(path, "codex")["source"] == "default"

    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE host_controls (host TEXT PRIMARY KEY, enabled INTEGER, "
        "updated_at TEXT, source TEXT)"
    )
    connection.commit()
    connection.close()
    assert canary._read_control_without_writes(path, "codex")["source"] == "default"

    connection = sqlite3.connect(path)
    connection.execute(
        "INSERT INTO host_controls VALUES (?, ?, ?, ?)",
        ("codex", 0, "now", "test"),
    )
    connection.commit()
    connection.close()
    assert canary._read_control_without_writes(path, "codex") == {
        "host": "codex",
        "enabled": False,
        "updated_at": "now",
        "source": "test",
    }

    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not sqlite")
    state = canary._read_control_without_writes(corrupt, "codex")
    assert state["enabled"] is None
    assert state["source"] == "unverified"


def test_default_inspector_requests_only_the_selected_host(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []
    monkeypatch.setattr(
        canary,
        "inspect_host_installations",
        lambda *, hosts: seen.append(hosts) or [{"host": hosts[0]}],
    )
    assert canary._default_inspector("codex") == {"host": "codex"}
    assert seen == [["codex"]]


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (FileSizeLimitError("large"), "safety limit"),
        (PermissionError("unsafe"), "unavailable or unsafe"),
    ],
)
def test_copy_auth_translates_bounded_read_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: OSError,
    message: str,
) -> None:
    monkeypatch.setattr(
        canary,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(error),
    )
    with pytest.raises(ValueError, match=message):
        canary._copy_bounded_auth(tmp_path / "source", tmp_path / "dest", host="Codex")


def test_copy_auth_cleans_destination_for_base_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "auth.json"
    source.write_text("{}", encoding="utf-8")
    destination = tmp_path / "private" / "auth.json"
    from agency_runtime.core import configuration

    calls = {"value": 0}

    def interrupt(_path: Path) -> None:
        calls["value"] += 1
        if calls["value"] == 1:
            raise KeyboardInterrupt

    monkeypatch.setattr(configuration, "restrict_private_file", interrupt)
    with pytest.raises(KeyboardInterrupt):
        canary._copy_bounded_auth(source, destination, host="Codex")
    assert not destination.exists()


def test_copy_auth_removes_partial_file_for_regular_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "auth.json"
    source.write_text("{}", encoding="utf-8")
    destination = tmp_path / "private" / "auth.json"
    from agency_runtime.core import configuration

    monkeypatch.setattr(
        configuration,
        "restrict_private_file",
        lambda _path: (_ for _ in ()).throw(PermissionError("denied")),
    )
    with pytest.raises(PermissionError, match="denied"):
        canary._copy_bounded_auth(source, destination, host="Codex")
    assert not destination.exists()


def test_copy_auth_removes_partial_file_after_stream_ownership_transfer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "auth.json"
    source.write_text("{}", encoding="utf-8")
    destination = tmp_path / "private" / "auth.json"
    real_os = canary.os

    class _FailingStream:
        def __enter__(self) -> _FailingStream:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def write(self, _payload: bytes) -> None:
            raise OSError("write failed")

    def fdopen(descriptor: int, mode: str) -> Any:
        real_os.fdopen(descriptor, mode).close()
        return _FailingStream()

    class _OSProxy:
        def __getattr__(self, name: str) -> Any:
            return fdopen if name == "fdopen" else getattr(real_os, name)

    monkeypatch.setattr(canary, "os", _OSProxy())
    with pytest.raises(OSError, match="write failed"):
        canary._copy_bounded_auth(source, destination, host="Codex")
    assert not destination.exists()


def test_agency_canary_prompt_does_not_trigger_unrelated_business_policy() -> None:
    actions, companions = detect_actions(canary.CANARY_PROMPT, load_bundled_policy())

    assert "BUSINESS" not in actions
    assert "business-strategist" not in companions


def test_agency_canary_explicitly_requests_one_whole_unit_subagent() -> None:
    prompt = canary.CANARY_PROMPT.lower()

    assert prompt.startswith("treat this as exactly one indivisible code-review work unit")
    assert "exactly one sub-agent" in prompt
    assert "delegate that complete work unit" in prompt
    assert "spawn no other sub-agents this turn" in prompt
    assert "do not inspect the environment at any point in this turn" in prompt
    assert "exactly the work unit text below" in prompt
    assert "nothing before it and nothing after it" in prompt
    assert "user explicitly requested exactly one sub-agent" in (
        canary.CODEX_CANARY_DEVELOPER_INSTRUCTIONS.lower()
    )
    assert "call wait_agent once" in canary.CODEX_CANARY_DEVELOPER_INSTRUCTIONS.lower()
    assert "fork_turns set to none" in canary.CODEX_CANARY_DEVELOPER_INSTRUCTIONS.lower()
    assert "never retry any collaboration call" in (
        canary.CODEX_CANARY_DEVELOPER_INSTRUCTIONS.lower()
    )
    assert "if the spawn fails or the wait times out" in (
        canary.CODEX_CANARY_DEVELOPER_INSTRUCTIONS.lower()
    )
    assert "do not call followup_task" in canary.CODEX_CANARY_DEVELOPER_INSTRUCTIONS.lower()


def test_codex_canary_diagnostic_uses_direct_spawn_and_one_wait_contract() -> None:
    counts = {
        "spawn_count": 1,
        "followup_count": 0,
        "wait_count": 1,
        "tool_output_count": 2,
        "child_start_count": 1,
        "child_interaction_count": 0,
    }

    assert (
        canary_backends._codex_collaboration_diagnostic_reason(
            counts,
            rollout_contract="canary",
        )
        == "native_collaboration_topology_invalid"
    )

    counts["followup_count"] = 1
    assert (
        canary_backends._codex_collaboration_diagnostic_reason(
            counts,
            rollout_contract="canary",
        )
        == "parent_followup_ambiguous"
    )

    counts["followup_count"] = 0
    counts["wait_count"] = 2
    assert (
        canary_backends._codex_collaboration_diagnostic_reason(
            counts,
            rollout_contract="canary",
        )
        == "parent_wait_ambiguous"
    )


def test_canary_output_and_records_cover_empty_and_failed_results() -> None:
    assert canary._codex_output("\n\n") is None
    assert canary._codex_output("{invalid") is None
    assert canary._codex_output('"scalar"\n{"type":"turn.completed"}') is None
    incomplete = canary._codex_canary_record(_result(stdout='{"type":"turn.completed"}'))
    assert incomplete["status"] == "failed"
    assert incomplete["exit_code"] == 0
    assert incomplete["failure_reason"] == "codex_output_projection_unavailable"
    unprojectable = canary._codex_canary_record(_result(stdout="{invalid"))
    assert unprojectable["status"] == "failed"
    assert unprojectable["exit_code"] == 0
    assert unprojectable["failure_reason"] == "codex_result_projection_unavailable"
    assert canary._codex_canary_record(_result(returncode=1))["status"] == "failed"
    assert canary._claude_canary_record(_result(returncode=1))["status"] == "failed"
    # Both backends now answer a protocol error the same way: the real process
    # exit code, "failed" as the verdict, and a typed reason for the fault.
    invalid = canary._claude_canary_record(_result(stdout="{invalid"))
    assert invalid["exit_code"] == 0
    assert invalid["status"] == "failed"
    assert invalid["failure_reason"] == "claude_result_projection_unavailable"
    empty = canary._claude_canary_record(_result(stdout="{}"))
    assert empty["exit_code"] == 0
    assert empty["status"] == "failed"
    assert empty["failure_reason"] == "claude_output_projection_unavailable"


def test_claude_process_timeout_remains_a_timeout() -> None:
    # A deadline reported as a plain failure publishes `"timed_out": false`
    # beside exit code 124, which reads as a host that ran and refused.
    record = canary._claude_canary_record(_result(returncode=124, timed_out=True))
    assert record["status"] == "timed_out"
    assert record["exit_code"] == 124
    assert record["failure_reason"] == "claude_exec_timed_out"


def test_codex_setup_and_inventory_failures_are_typed(tmp_path: Path) -> None:
    responses = iter([_result(returncode=0, timed_out=True)])
    backend = canary._SafeCodexCanaryBackend(
        executable="codex",
        db_path=tmp_path / "agency.db",
        timeout=30,
        marketplace=tmp_path,
        auth_source=tmp_path / "auth.json",
        process_runner=lambda *_args, **_kwargs: next(responses),
        source_env={},
    )
    assert backend._install_plugin(workdir=str(tmp_path), env={}) == {
        "backend": "codex",
        "status": "failed",
        "exit_code": 1,
    }

    invalid_inventory = canary._SafeCodexCanaryBackend(
        executable="codex",
        db_path=tmp_path / "agency.db",
        timeout=1,
        marketplace=tmp_path,
        auth_source=tmp_path / "auth.json",
        process_runner=lambda *_args, **_kwargs: _result(stdout="{invalid"),
        source_env={},
    )
    assert invalid_inventory._verify_plugin(workdir=str(tmp_path), env={})["isolated_plugin"] == {
        "registered": False,
        "enabled": None,
    }


def test_codex_execute_returns_setup_failure_without_invoking_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def run(argv: list[str], **_kwargs: Any) -> SimpleNamespace:
        calls.append(argv)
        return _result(returncode=2)

    backend = canary._SafeCodexCanaryBackend(
        executable="codex",
        db_path=tmp_path / "agency.db",
        timeout=1,
        marketplace=tmp_path,
        auth_source=tmp_path / "auth.json",
        process_runner=run,
        source_env={},
    )
    monkeypatch.setattr(
        canary,
        "_prepare_private_host_home",
        lambda runtime_home, **_kwargs: runtime_home / "codex",
    )
    monkeypatch.setattr(
        canary,
        "_isolated_canary_environment",
        lambda *_args, **_kwargs: {},
    )
    result = backend.execute(task="read only", workdir=str(tmp_path))
    assert result["status"] == "failed"
    assert len(calls) == 1


def test_invalid_managed_plugin_locations_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing target"):
        canary._managed_target(None, error="missing target")
    with pytest.raises(ValueError, match="Codex marketplace"):
        canary._codex_marketplace({"managed_target": str(tmp_path / "missing")})
    with pytest.raises(ValueError, match="Claude plugin"):
        canary._claude_plugin_dir({"managed_target": str(tmp_path / "missing")})


def test_response_text_recurses_bounds_depth_and_ignores_scalars() -> None:
    assert canary._response_text("answer") == "answer"
    assert canary._response_text({"text": "", "result": {"message": "nested"}}) == "nested"
    assert canary._response_text([{"output": "one"}, 2, "two"]) == "one\ntwo"
    assert canary._response_text(2) == ""
    nested: Any = "too deep"
    for _index in range(10):
        nested = {"text": nested}
    assert canary._response_text(nested) == ""


def test_nonisolated_readiness_reports_registration_enablement_and_control(
    tmp_path: Path,
) -> None:
    assessment = canary._assess_readiness(
        "openclaw",
        tmp_path / "missing.db",
        lambda _host: _native(
            "openclaw",
            registered=False,
            enabled=False,
        ),
    )
    assert "Agency Runtime plugin registration not proven" in assessment.unmet
    assert "native plugin enablement not proven" in assessment.unmet
    assert (
        "host has no proven read-only, bounded native-child noninteractive canary mode"
        in assessment.unmet
    )


def test_readiness_reports_disabled_soft_control(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        canary,
        "_read_control_without_writes",
        lambda _path, host: {"host": host, "enabled": False},
    )
    assessment = canary._assess_readiness("codex", tmp_path / "agency.db", lambda _host: _native())
    assert "Agency Runtime soft control is disabled or unverified" in assessment.unmet


def test_backend_rejects_unsafe_or_unavailable_hosts(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no proven safe"):
        canary._backend("openclaw", db_path=tmp_path / "agency.db", timeout=1)
    with pytest.raises(ValueError, match="executable is unavailable"):
        canary._backend(
            "codex",
            db_path=tmp_path / "agency.db",
            timeout=1,
            resolver=lambda _name: None,
        )


def test_prepare_live_invocation_uses_default_backend_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Store:
        def __init__(self, _path: Path) -> None:
            pass

        def recent_runtime_activity(self, *, limit: int) -> dict[str, list[Any]]:
            assert limit == 200
            return {}

    calls: list[dict[str, Any]] = []

    def factory(host: str, **kwargs: Any) -> object:
        calls.append({"host": host, **kwargs})
        return object()

    monkeypatch.setattr(canary, "Store", _Store)
    monkeypatch.setattr(canary, "_backend", factory)
    prepared = canary._prepare_live_invocation(
        "codex",
        path=tmp_path / "agency.db",
        timeout=2,
        native=_native(),
        backend_factory=factory,
        master_enabled=False,
        mode="native-only",
    )
    assert prepared.error is None
    assert calls[0]["native"] == _native()
    assert calls[0]["master_enabled"] is False
    assert calls[0]["require_exact_activation_rollout"] is False
    assert prepared.prompt is not None
    assert prepared.prompt.startswith(canary.NATIVE_ONLY_CANARY_PROMPT)

    agency = canary._prepare_live_invocation(
        "codex",
        path=tmp_path / "agency.db",
        timeout=2,
        native=_native(),
        backend_factory=factory,
        mode="agency",
    )
    assert agency.error is None
    assert calls[1]["require_exact_activation_rollout"] is True


def test_profile_and_proof_helpers_cover_current_and_receipt_failure() -> None:
    assert (
        canary._profile_is_proven("openclaw", "current-profile", None, plugin_invoked=False) is True
    )
    failures = canary._proof_failures(
        process_ok=True,
        profile_proven=True,
        header_valid=True,
        evidence={
            "accepted_trace_ids": ["trace"],
            "expected_specialist_selected": True,
            "expected_specialist_loaded": True,
            "receipt_required": True,
            "receipt_proven": False,
        },
    )
    assert failures == (
        "the host exposes response telemetry but a correlated receipt was not proven",
    )


def test_run_canary_rejects_unknown_host() -> None:
    with pytest.raises(ValueError, match="unsupported host"):
        canary.run_canary("unknown")


def test_canary_parser_main_output_and_execute_exit_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    parser = canary.build_parser()
    assert parser.parse_args(["codex"]).host == "codex"
    output = tmp_path / "report.json"
    monkeypatch.setattr(
        canary,
        "run_canary",
        lambda *_args, **_kwargs: {"ready": True, "canary_passed": False},
    )
    assert canary.main(["codex", "--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["ready"] is True
    assert '"ready": true' in capsys.readouterr().out
    assert canary.main(["codex", "--execute", "--confirm", "RUN LIVE codex CANARY"]) == 1


def test_canary_module_entrypoint_executes_readiness_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import installer

    monkeypatch.setattr(
        installer,
        "inspect_host_installations",
        lambda **_kwargs: [_native()],
    )
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "missing.db"))
    monkeypatch.setattr(sys, "argv", ["host_canary", "codex"])
    with pytest.raises(SystemExit) as exited:
        runpy.run_path(str(Path(canary.__file__)), run_name="__main__")
    assert exited.value.code == 0
