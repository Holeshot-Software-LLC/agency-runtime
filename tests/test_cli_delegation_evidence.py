"""Adversarial coverage for CLI and public delegation evidence correlation."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from agency_runtime import AgencyRuntime
from agency_runtime.cli import delegation_commands
from agency_runtime.core.delegation import backends as backend_module
from agency_runtime.core.delegation.backend_command import CommandBackend
from agency_runtime.core.delegation.backend_hosts import GenericCLIBackend
from agency_runtime.core.delegation.events import (
    mark_delegation_executed,
    work_unit_id_from_text,
)
from agency_runtime.core.delegation.ledger import DelegationLedger
from agency_runtime.core.delegation.lifecycle import delegate_with_lifecycle
from agency_runtime.core.header.contract import _delegation_line
from agency_runtime.core.store.sqlite import Store


class _CapturingStore:
    def __init__(self) -> None:
        self.recorded: list[dict[str, object]] = []
        self.updated: list[tuple[str, dict[str, object]]] = []
        self.run: dict[str, object] = {}
        self.completed: list[tuple[str, str]] = []

    def record_delegation(self, **kwargs: object) -> str:
        self.recorded.append(dict(kwargs))
        self.run = {
            "id": "run-1",
            "trace_id": kwargs["trace_id"],
            "session_id": kwargs["session_id"],
            "status": "evidence_only",
        }
        return "event-1"

    def update_delegation(self, event_id: str, **kwargs: object) -> None:
        self.updated.append((event_id, dict(kwargs)))

    def get_run(self, _trace_id: str) -> dict[str, object]:
        return dict(self.run)

    def complete_run(self, run_id: str, status: str = "completed") -> None:
        self.completed.append((run_id, status))
        self.run["status"] = status


def _args(**changes: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "agent": "code-reviewer",
        "backend": "codex",
        "command": None,
        "json": True,
        "task": "review the execution evidence",
        "timeout": None,
        "workdir": None,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def test_cli_completed_delegation_uses_process_identity_not_recommendation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _CapturingStore()
    emitted: list[dict[str, object]] = []

    class Candidate:
        name = "codex"

        def is_available(self) -> bool:
            return True

        def delegate(self, **_kwargs: object) -> dict[str, object]:
            return {
                "backend": "codex",
                "status": "completed",
                "exit_code": 0,
                "output": "done",
                "executable": "C:/trusted/codex.exe",
                "process_id": 4242,
            }

    monkeypatch.setattr(backend_module, "CodexExecBackend", lambda **_kwargs: Candidate())
    monkeypatch.setattr(delegation_commands, "_store", lambda: store)
    monkeypatch.setattr(delegation_commands, "_print_json", emitted.append)

    assert delegation_commands.cmd_delegate(_args()) == 0

    planned = store.recorded[0]
    assert planned["status"] == "suggested"
    assert planned["host"] == "cli"
    assert str(planned["session_id"]).startswith("cli-delegate-session-")
    assert str(planned["trace_id"]).startswith("cli-delegate-")
    assert planned["work_unit_id"] == work_unit_id_from_text("review the execution evidence")

    event_id, observed = store.updated[0]
    assert event_id == "event-1"
    assert observed["status"] == "completed"
    assert observed["executed_worker_kind"] == "cli-process"
    assert observed["executed_worker_id"] == "C:/trusted/codex.exe"
    assert observed["native_run_id"] == "codex:process:4242"
    assert observed["executed_worker_id"] != planned["recommended_agent"]
    assert store.completed == [("run-1", "completed")]
    assert emitted == [
        {
            "backend": "codex",
            "status": "completed",
            "exit_code": 0,
            "output": "done",
            "executable": "C:/trusted/codex.exe",
            "process_id": 4242,
            "session_id": planned["session_id"],
            "trace_id": planned["trace_id"],
            "work_unit_id": planned["work_unit_id"],
            "event_id": "event-1",
            "agent": "code-reviewer",
            "timeout_seconds": 3600.0,
            "executed_worker_kind": "cli-process",
            "executed_worker_id": "C:/trusted/codex.exe",
            "native_run_id": "codex:process:4242",
        }
    ]


@pytest.mark.parametrize("process_id", [None, 0, -1, True, 1.5, "42", "not-a-pid"])
def test_cli_never_promotes_success_without_process_correlation(
    monkeypatch: pytest.MonkeyPatch,
    process_id: object,
) -> None:
    store = _CapturingStore()
    emitted: list[dict[str, object]] = []

    class Candidate:
        name = "codex"

        def is_available(self) -> bool:
            return True

        def delegate(self, **_kwargs: object) -> dict[str, object]:
            return {
                "status": "completed",
                "exit_code": 0,
                "output": "unverified",
                "executable": "codex",
                "process_id": process_id,
            }

    monkeypatch.setattr(backend_module, "CodexExecBackend", lambda **_kwargs: Candidate())
    monkeypatch.setattr(delegation_commands, "_store", lambda: store)
    monkeypatch.setattr(delegation_commands, "_print_json", emitted.append)

    assert delegation_commands.cmd_delegate(_args()) == 1
    assert store.updated[0][1]["status"] == "failed"
    assert store.updated[0][1]["executed_worker_kind"] == ""
    assert store.updated[0][1]["executed_worker_id"] == ""
    assert store.updated[0][1]["native_run_id"] == ""
    assert store.completed == [("run-1", "failed")]
    assert emitted[0]["status"] == "failed"
    assert emitted[0]["process_exit_code"] == 0
    assert "without verifiable CLI process correlation" in str(emitted[0]["error"])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("trace_id", ""),
        ("session_id", ""),
        ("work_unit_id", ""),
        ("backend", ""),
        ("executed_worker_kind", ""),
        ("executed_worker_id", ""),
        ("native_run_id", ""),
    ],
)
def test_store_rejects_positive_evidence_without_canonical_parent_keys(
    tmp_path,
    field: str,
    value: str,
) -> None:
    store = Store(tmp_path / f"{field}.db")
    kwargs = {
        "trace_id": "trace",
        "session_id": "session",
        "work_unit_id": "unit",
        "backend": "codex",
        "status": "completed",
        "executed_worker_kind": "cli-process",
        "executed_worker_id": "C:/trusted/codex.exe",
        "native_run_id": "codex:process:4242",
    }
    kwargs[field] = value

    with pytest.raises(ValueError, match=field):
        store.record_delegation(**kwargs)


@pytest.mark.parametrize("status", ["started", "running", "delegated", "completed"])
def test_store_accepts_only_correlation_complete_positive_state(
    tmp_path,
    status: str,
) -> None:
    store = Store(tmp_path / f"{status}.db")

    event_id = store.record_delegation(
        trace_id="trace",
        session_id="session",
        work_unit_id="unit",
        backend="codex",
        status=status,
        executed_worker_kind="cli-process",
        executed_worker_id="C:/trusted/codex.exe",
        native_run_id="codex:process:4242",
    )

    [row] = store.get_delegations("trace")
    assert row["id"] == event_id
    assert row["executed_worker_kind"] == "cli-process"
    assert row["executed_worker_id"] == "C:/trusted/codex.exe"
    assert row["native_run_id"] == "codex:process:4242"


def test_store_rejects_partial_or_conflicting_positive_receipt_updates(tmp_path) -> None:
    store = Store(tmp_path / "atomic-receipt.db")
    event_id = store.record_delegation(
        trace_id="trace",
        session_id="session",
        work_unit_id="unit",
        backend="codex",
        status="delegated",
        executed_worker_kind="cli-process",
        executed_worker_id="C:/trusted/codex.exe",
        native_run_id="codex:process:4242",
    )

    with pytest.raises(ValueError, match="executed_worker_kind"):
        store.update_delegation(event_id, status="delegated", backend="claude")
    with pytest.raises(ValueError, match="conflicts with existing receipt"):
        store.update_delegation(
            event_id,
            status="completed",
            backend="claude",
            executed_worker_kind="cli-process",
            executed_worker_id="C:/trusted/claude.exe",
            native_run_id="claude:process:9000",
        )

    [unchanged] = store.get_delegations("trace")
    assert (
        unchanged["status"],
        unchanged["backend"],
        unchanged["executed_worker_kind"],
        unchanged["executed_worker_id"],
        unchanged["native_run_id"],
    ) == (
        "delegated",
        "codex",
        "cli-process",
        "C:/trusted/codex.exe",
        "codex:process:4242",
    )

    store.update_delegation(
        event_id,
        status="completed",
        backend="codex",
        executed_worker_kind="cli-process",
        executed_worker_id="C:/trusted/codex.exe",
        native_run_id="codex:process:4242",
    )
    [completed] = store.get_delegations("trace")
    assert completed["status"] == "completed"


def test_real_store_lifecycle_persists_only_correlated_terminal_success(tmp_path) -> None:
    class RecordingStore(Store):
        def __init__(self, path) -> None:
            self.observed_statuses: list[str] = []
            super().__init__(path)

        def update_delegation(self, event_id: str, *, status: str, **kwargs: object) -> None:
            self.observed_statuses.append(status)
            super().update_delegation(event_id, status=status, **kwargs)

    store = RecordingStore(tmp_path / "lifecycle.db")
    ledger = DelegationLedger(
        store,
        trace_id="trace",
        session_id="session",
        host="codex",
    )

    def delegate(**_kwargs: object) -> dict[str, object]:
        return {
            "status": "completed",
            "backend": "spawn_agent",
            "executed_worker_kind": "generic-worker",
            "executed_worker_id": "worker-42",
            "native_run_id": "spawn_agent:run-42",
        }

    result = delegate_with_lifecycle(
        [{"id": "unit-a", "description": "review the patch"}],
        delegate_func=delegate,
        ledger=ledger,
    )

    assert result.dispatch_results["unit-a"]["status"] == "completed"
    assert store.observed_statuses == ["completed"]
    [row] = store.get_delegations("trace")
    assert (
        row["status"],
        row["backend"],
        row["executed_worker_kind"],
        row["executed_worker_id"],
        row["native_run_id"],
    ) == (
        "completed",
        "spawn_agent",
        "generic-worker",
        "worker-42",
        "spawn_agent:run-42",
    )
    [entry] = ledger.as_dict()["work_units"]
    assert entry["native_run_id"] == "spawn_agent:run-42"


def test_uncorrelated_callable_success_fails_and_blocks_dependents(tmp_path) -> None:
    store = Store(tmp_path / "uncorrelated.db")
    ledger = DelegationLedger(
        store,
        trace_id="trace",
        session_id="session",
        host="codex",
    )
    invoked: list[str] = []

    def delegate(*, task: str, **_kwargs: object) -> dict[str, object]:
        invoked.append(task)
        return {"status": "completed", "backend": "callable"}

    result = delegate_with_lifecycle(
        [
            {"id": "unit-a", "description": "first"},
            {"id": "unit-b", "description": "second", "depends_on": ["unit-a"]},
        ],
        delegate_func=delegate,
        ledger=ledger,
    )

    assert len(invoked) == 1
    assert result.dispatch_results["unit-a"]["status"] == "failed"
    assert result.dispatch_results["unit-b"]["status"] == "skipped"
    rows = {row["work_unit_id"]: row for row in store.get_delegations("trace")}
    assert rows["unit-a"]["status"] == "failed"
    assert rows["unit-b"]["status"] == "skipped"
    assert rows["unit-a"]["executed_worker_kind"] == ""


@pytest.mark.parametrize("process_id", [True, 0, -1, 1.5, "42"])
def test_owned_command_backend_rejects_spoofed_process_identity(
    process_id: object,
) -> None:
    class ReceiptBackend(CommandBackend):
        def delegate(self, **_kwargs: object) -> dict[str, object]:
            return {
                "status": "completed",
                "backend": "codex",
                "executable": "C:/trusted/codex.exe",
                "process_id": process_id,
            }

    backend = ReceiptBackend(command=("unused",), name="codex")

    result = delegate_with_lifecycle(
        [{"id": "unit-a", "description": "review"}],
        delegate_func=backend.delegate,
    )

    assert result.dispatch_results["unit-a"]["status"] == "failed"
    assert "complete execution correlation" in result.dispatch_results["unit-a"]["error"]


def test_owned_command_backend_derives_real_process_receipt_for_store(tmp_path) -> None:
    class ReceiptBackend(CommandBackend):
        def delegate(self, **_kwargs: object) -> dict[str, object]:
            return {
                "status": "completed",
                "backend": "codex",
                "executable": "C:/trusted/codex.exe",
                "process_id": 4242,
            }

    store = Store(tmp_path / "owned-command.db")
    ledger = DelegationLedger(
        store,
        trace_id="trace",
        session_id="session",
        host="codex",
    )
    backend = ReceiptBackend(command=("unused",), name="codex")

    result = delegate_with_lifecycle(
        [{"id": "unit-a", "description": "review"}],
        delegate_func=backend.delegate,
        ledger=ledger,
    )

    assert result.dispatch_results["unit-a"]["status"] == "completed"
    [row] = store.get_delegations("trace")
    assert row["executed_worker_kind"] == "cli-process"
    assert row["executed_worker_id"] == "C:/trusted/codex.exe"
    assert row["native_run_id"] == "codex:process:4242"


def test_missing_native_worker_correlation_is_skipped_not_delegated(tmp_path) -> None:
    store = Store(tmp_path / "missing-worker.db")
    store.record_delegation(
        trace_id="trace",
        session_id="session",
        host="codex",
        work_unit_id="unit",
        recommended_agent="code-reviewer",
        status="suggested",
    )

    mark_delegation_executed(
        store,
        session_id="session",
        trace_id="trace",
        host="codex",
        backend="spawn_agent",
        work_unit_id="unit",
        executed_worker_kind="generic-worker",
    )

    [row] = store.get_delegations("trace")
    assert row["status"] == "skipped"
    assert row["executed_worker_kind"] == "generic-worker"
    assert row["executed_worker_id"] == ""
    assert row["native_run_id"] == ""
    assert row["skip_reason"] == (
        "delegation execution correlation incomplete: missing executed_worker_id, native_run_id"
    )
    assert _delegation_line([row]) == (
        "none - delegation execution correlation incomplete: missing "
        "executed_worker_id, native_run_id"
    )


def test_public_api_rejects_positive_state_without_worker_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = AgencyRuntime()
    store = _CapturingStore()
    runtime._store = store
    monkeypatch.setattr(AgencyRuntime, "_runtime_enabled", staticmethod(lambda: True))
    monkeypatch.setattr(runtime, "_require_active_turn", lambda *_args: None)
    common = {
        "trace_id": "trace",
        "session_id": "session",
        "work_unit_id": "unit",
        "recommended_agent": "code-reviewer",
        "backend": "codex",
        "status": "completed",
    }

    with pytest.raises(ValueError, match="executed_worker_kind"):
        runtime.record_delegation(**common)
    with pytest.raises(ValueError, match="executed_worker_id"):
        runtime.record_delegation(**common, executed_worker_kind="cli-process")
    with pytest.raises(ValueError, match="native_run_id"):
        runtime.record_delegation(
            **common,
            executed_worker_kind="cli-process",
            executed_worker_id="C:/trusted/codex.exe",
        )

    assert (
        runtime.record_delegation(
            **common,
            executed_worker_kind="cli-process",
            executed_worker_id="C:/trusted/codex.exe",
            native_run_id="codex:process:4242",
        )
        == "event-1"
    )

    assert (
        runtime.record_delegation(
            **{**common, "status": "failed"},
        )
        == "event-1"
    )


def test_command_backend_returns_actual_spawned_process_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import process_argv, runtime_control

    monkeypatch.setattr(runtime_control, "master_enabled", lambda: True)
    # This test exercises PID propagation, not namespace policy. The project
    # venv intentionally lives below a developer-writable checkout and is
    # rejected by the production executable-namespace gate.
    monkeypatch.setattr(
        process_argv,
        "assert_executable_namespace",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        process_argv,
        "_assert_executable_artifact_trusted",
        lambda *_args, **_kwargs: None,
    )
    backend = GenericCLIBackend(
        command=(getattr(sys, "_base_executable", sys.executable), "-c", "print('done')"),
        timeout=10,
    )

    result = backend.delegate(task="bounded task")

    assert result["status"] == "completed"
    assert isinstance(result["process_id"], int)
    assert result["process_id"] > 0


def test_cli_terminalizes_exact_evidence_only_parent_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    store = Store(tmp_path / "agency.db")
    emitted: list[dict[str, object]] = []

    class Candidate:
        name = "codex"

        def is_available(self) -> bool:
            return True

        def delegate(self, **_kwargs: object) -> dict[str, object]:
            return {
                "status": "completed",
                "exit_code": 0,
                "output": "done",
                "executable": "C:/trusted/codex.exe",
                "process_id": 4242,
            }

    monkeypatch.setattr(backend_module, "CodexExecBackend", lambda **_kwargs: Candidate())
    monkeypatch.setattr(delegation_commands, "_store", lambda: store)
    monkeypatch.setattr(delegation_commands, "_print_json", emitted.append)

    assert delegation_commands.cmd_delegate(_args()) == 0

    run = store.get_run(str(emitted[0]["trace_id"]))
    assert run is not None
    assert run["session_id"] == emitted[0]["session_id"]
    assert run["status"] == "completed"
    assert run["ended_at"]
    assert store.get_open_traces_for_session(str(emitted[0]["session_id"])) == []


@pytest.mark.parametrize(
    ("exception_type", "exception_args"),
    [(KeyboardInterrupt, ()), (SystemExit, (23,))],
)
def test_cli_interrupt_terminalizes_evidence_without_inventing_worker(
    monkeypatch: pytest.MonkeyPatch,
    exception_type: type[BaseException],
    exception_args: tuple[object, ...],
) -> None:
    store = _CapturingStore()

    class Candidate:
        name = "codex"

        def is_available(self) -> bool:
            return True

        def delegate(self, **_kwargs: object) -> dict[str, object]:
            raise exception_type(*exception_args)

    monkeypatch.setattr(backend_module, "CodexExecBackend", lambda **_kwargs: Candidate())
    monkeypatch.setattr(delegation_commands, "_store", lambda: store)

    with pytest.raises(exception_type) as caught:
        delegation_commands.cmd_delegate(_args())

    if exception_type is SystemExit:
        assert caught.value.code == 23
    terminal = store.updated[0][1]
    assert terminal["status"] == "skipped"
    assert terminal["executed_worker_kind"] == ""
    assert terminal["executed_worker_id"] == ""
    assert terminal["native_run_id"] == ""
    assert terminal["skip_reason"] == f"delegation interrupted ({exception_type.__name__})"
    assert store.completed == [("run-1", "interrupted")]


def test_cli_unexpected_backend_exception_is_failed_without_false_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _CapturingStore()
    emitted: list[dict[str, object]] = []

    class Candidate:
        name = "codex"

        def is_available(self) -> bool:
            return True

        def delegate(self, **_kwargs: object) -> dict[str, object]:
            raise RuntimeError("secret backend detail")

    monkeypatch.setattr(backend_module, "CodexExecBackend", lambda **_kwargs: Candidate())
    monkeypatch.setattr(delegation_commands, "_store", lambda: store)
    monkeypatch.setattr(delegation_commands, "_print_json", emitted.append)

    assert delegation_commands.cmd_delegate(_args()) == 1

    terminal = store.updated[0][1]
    assert terminal["status"] == "failed"
    assert terminal["executed_worker_kind"] == ""
    assert terminal["executed_worker_id"] == ""
    assert terminal["native_run_id"] == ""
    assert store.completed == [("run-1", "failed")]
    assert emitted[0]["error"] == "backend raised unexpected RuntimeError"
    assert "secret backend detail" not in str(emitted[0])


def test_cli_closes_parent_when_terminal_event_write_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingUpdateStore(_CapturingStore):
        def update_delegation(self, event_id: str, **kwargs: object) -> None:
            super().update_delegation(event_id, **kwargs)
            raise RuntimeError("terminal event write failed")

    store = FailingUpdateStore()

    class Candidate:
        name = "codex"

        def is_available(self) -> bool:
            return True

        def delegate(self, **_kwargs: object) -> dict[str, object]:
            raise RuntimeError("backend failed")

    monkeypatch.setattr(backend_module, "CodexExecBackend", lambda **_kwargs: Candidate())
    monkeypatch.setattr(delegation_commands, "_store", lambda: store)

    with pytest.raises(RuntimeError, match="terminal event write failed"):
        delegation_commands.cmd_delegate(_args())

    assert store.completed == [("run-1", "failed")]


def test_cli_parent_terminalization_verifies_correlation_and_closed_state() -> None:
    class MissingParentStore:
        @staticmethod
        def get_run(_trace_id: str) -> None:
            return None

    with pytest.raises(RuntimeError, match="correlation could not be verified"):
        delegation_commands._complete_cli_evidence_run(
            MissingParentStore(),
            trace_id="trace",
            session_id="session",
            status="failed",
        )

    class NonTerminalStore:
        @staticmethod
        def get_run(_trace_id: str) -> dict[str, object]:
            return {
                "id": "run-1",
                "session_id": "session",
                "status": "evidence_only",
            }

        @staticmethod
        def complete_run(_run_id: str, *, status: str) -> None:
            del status

    with pytest.raises(RuntimeError, match="did not reach terminal state"):
        delegation_commands._complete_cli_evidence_run(
            NonTerminalStore(),
            trace_id="trace",
            session_id="session",
            status="failed",
        )


def test_cli_terminal_evidence_preserves_update_and_close_failures() -> None:
    class BothWritesFailStore:
        @staticmethod
        def update_delegation(_event_id: str, **_kwargs: object) -> None:
            raise ValueError("event update failed")

        @staticmethod
        def get_run(_trace_id: str) -> None:
            return None

    with pytest.raises(ValueError, match="event update failed") as both_failed:
        delegation_commands._persist_cli_terminal_evidence(
            BothWritesFailStore(),
            event_id="event",
            trace_id="trace",
            session_id="session",
            evidence_status="failed",
            run_status="failed",
            backend="codex",
        )
    assert isinstance(both_failed.value.__cause__, RuntimeError)
    assert "correlation" in str(both_failed.value.__cause__)

    class ParentCloseFailsStore(BothWritesFailStore):
        @staticmethod
        def update_delegation(_event_id: str, **_kwargs: object) -> None:
            return None

    with pytest.raises(RuntimeError, match="correlation could not be verified"):
        delegation_commands._persist_cli_terminal_evidence(
            ParentCloseFailsStore(),
            event_id="event",
            trace_id="trace",
            session_id="session",
            evidence_status="failed",
            run_status="failed",
            backend="codex",
        )


def test_cli_interrupt_keeps_terminalization_failure_as_the_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingTerminalStore(_CapturingStore):
        def update_delegation(self, event_id: str, **kwargs: object) -> None:
            super().update_delegation(event_id, **kwargs)
            raise RuntimeError("terminalization failed")

    class Candidate:
        name = "codex"

        @staticmethod
        def is_available() -> bool:
            return True

        @staticmethod
        def delegate(**_kwargs: object) -> dict[str, object]:
            raise KeyboardInterrupt

    monkeypatch.setattr(backend_module, "CodexExecBackend", lambda **_kwargs: Candidate())
    monkeypatch.setattr(delegation_commands, "_store", FailingTerminalStore)

    with pytest.raises(KeyboardInterrupt) as interrupted:
        delegation_commands.cmd_delegate(_args())

    assert isinstance(interrupted.value.__cause__, RuntimeError)
    assert str(interrupted.value.__cause__) == "terminalization failed"


def test_cli_non_object_backend_result_fails_without_false_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _CapturingStore()
    emitted: list[dict[str, object]] = []

    class Candidate:
        name = "codex"

        @staticmethod
        def is_available() -> bool:
            return True

        @staticmethod
        def delegate(**_kwargs: object) -> list[str]:
            return ["not-an-object"]

    monkeypatch.setattr(backend_module, "CodexExecBackend", lambda **_kwargs: Candidate())
    monkeypatch.setattr(delegation_commands, "_store", lambda: store)
    monkeypatch.setattr(delegation_commands, "_print_json", emitted.append)

    assert delegation_commands.cmd_delegate(_args()) == 1
    assert store.updated[0][1]["status"] == "failed"
    assert emitted[0]["error"] == "backend raised unexpected TypeError"


def test_codex_exec_freezes_and_revalidates_executable_before_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import process_argv

    observed: list[tuple[str, object]] = []
    prepared = ["C:/resolved/codex.exe", "exec", "task"]
    frozen = ["C:/trusted/codex.exe", "exec", "task"]
    monkeypatch.setattr(
        process_argv,
        "prepare_process_argv",
        lambda argv, **_kwargs: observed.append(("prepare", list(argv))) or prepared,
    )
    monkeypatch.setattr(
        process_argv,
        "freeze_process_argv",
        lambda argv, **_kwargs: observed.append(("freeze", argv)) or frozen,
    )
    monkeypatch.setattr(
        process_argv,
        "revalidate_process_argv",
        lambda argv: observed.append(("revalidate", argv)),
    )
    monkeypatch.setattr(
        delegation_commands.subprocess,
        "run",
        lambda argv, **_kwargs: observed.append(("run", argv)) or SimpleNamespace(returncode=7),
    )

    assert delegation_commands.cmd_codex_exec(SimpleNamespace(args=["task"])) == 7
    assert observed == [
        ("prepare", ["codex", "exec", "task"]),
        ("freeze", prepared),
        ("revalidate", frozen),
        ("run", frozen),
    ]


def test_codex_exec_does_not_launch_when_identity_revalidation_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from agency_runtime.core import process_argv

    launched = False
    frozen = ["C:/trusted/codex.exe", "exec", "task"]
    monkeypatch.setattr(
        process_argv,
        "prepare_process_argv",
        lambda _argv, **_kwargs: frozen,
    )
    monkeypatch.setattr(
        process_argv,
        "freeze_process_argv",
        lambda argv, **_kwargs: argv,
    )
    monkeypatch.setattr(
        process_argv,
        "revalidate_process_argv",
        lambda _argv: (_ for _ in ()).throw(OSError("sensitive drift detail")),
    )

    def unexpected_launch(*_args: object, **_kwargs: object) -> object:
        nonlocal launched
        launched = True
        raise AssertionError("subprocess must not be started")

    monkeypatch.setattr(delegation_commands.subprocess, "run", unexpected_launch)

    assert delegation_commands.cmd_codex_exec(SimpleNamespace(args=["task"])) == 1
    assert launched is False
    assert capsys.readouterr().err == "Command failed to start (OSError)\n"
