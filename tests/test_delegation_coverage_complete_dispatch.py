"""Dispatch decision, failure-recording, and compatibility edge contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.delegation import backends, lifecycle_dispatch
from agency_runtime.core.delegation.ledger import DelegationLedger
from agency_runtime.core.delegation.lifecycle_types import (
    DependencyGraph,
    WorktreeInfo,
    WorkUnit,
)


def test_default_delegate_resolution_uses_backend_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def selected(**_kwargs: Any) -> dict[str, bool]:
        return {"ok": True}

    monkeypatch.setattr(backends, "get_delegate_func", lambda: selected)

    assert lifecycle_dispatch.resolve_delegate_func(None) is selected


def test_call_delegate_falls_back_when_signature_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observed: dict[str, Any] = {}

    def delegate(**kwargs: Any) -> dict[str, Any]:
        observed.update(kwargs)
        return kwargs

    monkeypatch.setattr(
        lifecycle_dispatch.inspect,
        "signature",
        lambda _func: (_ for _ in ()).throw(ValueError("opaque callable")),
    )
    unit = WorkUnit("unit", "do work", repo_path=tmp_path)

    result = lifecycle_dispatch.call_delegate(delegate, unit, None)

    assert result == observed
    assert observed["workdir"] == str(tmp_path)


def test_call_delegate_supports_positional_only_contract(tmp_path: Path) -> None:
    def positional(task: str, /) -> str:
        return task

    result = lifecycle_dispatch.call_delegate(
        positional,
        WorkUnit("unit", "do work"),
        tmp_path,
    )

    assert result.startswith("Work unit unit:")


@pytest.mark.parametrize(
    "result",
    [
        {"exit_code": 2},
        {"returncode": 3},
        {"timed_out": True},
    ],
)
def test_result_completed_rejects_process_failure_evidence(result: dict[str, Any]) -> None:
    assert lifecycle_dispatch.result_completed(result) is False


@pytest.mark.parametrize(
    ("result", "reason"),
    [
        ({"ok": False}, "worker reported ok=false"),
        ({"exit_code": 7}, "worker reported exit_code=7"),
        ({"returncode": 8}, "worker reported returncode=8"),
        ({"timed_out": True}, "worker timed out"),
        ({"status": "waiting"}, "worker reported status 'waiting'"),
    ],
)
def test_result_failure_reason_preserves_specific_worker_evidence(
    result: dict[str, Any],
    reason: str,
) -> None:
    assert lifecycle_dispatch.result_failure_reason(result) == reason


def test_result_failure_reason_reports_missing_dispatch_result() -> None:
    assert lifecycle_dispatch.result_failure_reason() == "no dispatch result was recorded"


def test_graph_node_validation_reports_missing_and_extra_nodes() -> None:
    with pytest.raises(ValueError, match=r"missing=\['unit'\].*extra=\['other'\]"):
        lifecycle_dispatch._validate_graph_nodes(
            [WorkUnit("unit", "work")],
            DependencyGraph(edges={"other": set()}),
        )


def test_isolation_failure_without_detail_keeps_stable_reason(tmp_path: Path) -> None:
    unit = WorkUnit("unit", "work")
    info = WorktreeInfo("unit", tmp_path, tmp_path / "worktree", "", "", "")
    results: dict[str, Any] = {}
    warnings: list[str] = []

    lifecycle_dispatch._record_isolation_failure(
        unit,
        info,
        results=results,
        warnings=warnings,
        ledger=None,
    )

    assert results["unit"] == {
        "error": "isolated worktree was not created",
        "status": "failed",
    }

    ledger = DelegationLedger(trace_id="trace")
    lifecycle_dispatch._record_isolation_failure(
        unit,
        info,
        results=results,
        warnings=warnings,
        ledger=ledger,
    )
    assert ledger.entries[-1].status == "failed"


def test_dispatch_result_records_worker_and_commit_failures_with_ledger(
    tmp_path: Path,
) -> None:
    unit = WorkUnit("unit", "work", recommended_agent="reviewer")
    ledger = DelegationLedger(trace_id="trace")
    results: dict[str, Any] = {}
    warnings: list[str] = []

    def backend(**_kwargs: Any) -> None:
        return None

    lifecycle_dispatch._record_dispatch_result(
        unit,
        {"ok": False},
        worktrees={},
        func=backend,
        results=results,
        warnings=warnings,
        ledger=ledger,
        result_completed_func=lambda _result: False,
        result_failure_reason_func=lambda _result: "worker refused",
        backend_name_func=lambda _result, _func: "fake",
        commit_worktree_func=lambda _info, _unit_id: None,
    )
    assert ledger.entries[0].status == "failed"
    assert ledger.entries[0].error == "worker refused"

    info = WorktreeInfo(
        "unit",
        tmp_path,
        tmp_path / "worktree",
        "branch",
        "main",
        "a" * 40,
        created=True,
    )
    lifecycle_dispatch._record_dispatch_result(
        unit,
        {"ok": True},
        worktrees={"unit": info},
        func=backend,
        results=results,
        warnings=warnings,
        ledger=ledger,
        result_completed_func=lambda _result: True,
        result_failure_reason_func=lambda _result: "",
        backend_name_func=lambda _result, _func: "fake",
        commit_worktree_func=lambda _info, _unit_id: "commit failed",
    )
    assert results["unit"]["status"] == "failed"
    assert "could not preserve" in ledger.entries[0].error

    lifecycle_dispatch._record_dispatch_result(
        unit,
        {"ok": True},
        worktrees={"unit": info},
        func=backend,
        results=results,
        warnings=warnings,
        ledger=None,
        result_completed_func=lambda _result: True,
        result_failure_reason_func=lambda _result: "",
        backend_name_func=lambda _result, _func: "fake",
        commit_worktree_func=lambda _info, _unit_id: "commit failed without ledger",
    )
    assert results["unit"]["status"] == "failed"


class _NoSubmitExecutor:
    def submit(self, *_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("merge failure must prevent dispatch")


def test_schedule_unit_converts_predecessor_merge_exception_to_skip(tmp_path: Path) -> None:
    unit = WorkUnit("unit", "work", recommended_agent="reviewer")
    ledger = DelegationLedger(trace_id="trace")
    runtime = lifecycle_dispatch._DispatchRuntime(
        func=lambda **_kwargs: None,
        executor=_NoSubmitExecutor(),  # type: ignore[arg-type]
        worktrees={},
        predecessors={"unit": {"producer"}},
        results={"producer": {"ok": True}},
        warnings=[],
        ledger=ledger,
        call_delegate_func=lambda *_args: None,
        result_completed_func=lambda result: bool(result.get("ok")),
        result_failure_reason_func=lambda _result: "",
        backend_name_func=lambda _result, _func: "fake",
        merge_predecessors_func=lambda *_args: (_ for _ in ()).throw(OSError("merge unavailable")),
        commit_worktree_func=lambda *_args: None,
    )

    future = lifecycle_dispatch._schedule_unit(unit, runtime)

    assert future is None
    assert runtime.results["unit"]["status"] == "skipped"
    assert "could not apply predecessor work" in runtime.results["unit"]["error"]
    assert ledger.entries[-1].error.endswith("merge unavailable")

    runtime.ledger = None
    lifecycle_dispatch._record_predecessor_merge_failure(
        unit,
        "manual merge failure",
        runtime,
    )
    assert runtime.results["unit"]["error"] == "manual merge failure"
