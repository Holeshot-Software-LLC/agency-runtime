"""Tests for delegation lifecycle — normalization, dependency graph, dispatch."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agency_runtime.core.delegation.backends import BackendRegistry, CommandBackend
from agency_runtime.core.delegation.ledger import DelegationLedger
from agency_runtime.core.delegation.lifecycle import (
    DependencyGraph,
    build_dependency_graph,
    delegate_with_lifecycle,
    normalize_work_units,
)

# ─── Work unit normalization ────────────────────────────────────────


def test_normalize_string():
    units = normalize_work_units("fix the bug in auth.py")
    assert len(units) == 1
    assert "fix" in units[0].description.lower()


def test_normalize_list_of_strings():
    units = normalize_work_units(["fix bug", "add tests", "update docs"])
    assert len(units) == 3
    assert units[0].id != units[1].id


def test_normalize_detect_work_units_output():
    raw = {
        "count": 2,
        "units": ["fix the login bug", "update the README"],
        "delegate": True,
    }
    units = normalize_work_units(raw)
    assert len(units) == 2


def test_normalize_with_recommended_agent():
    units = normalize_work_units(
        [
            {"description": "review code", "recommended_agent": "code-reviewer"},
        ]
    )
    assert len(units) == 1
    assert units[0].recommended_agent == "code-reviewer"


# ─── Dependency graph ───────────────────────────────────────────────


def test_dependency_graph_no_deps():
    units = normalize_work_units(["task a", "task b", "task c"])
    graph = build_dependency_graph(units)
    batches = graph.topological_batches()
    assert len(batches) == 1  # all independent
    assert len(batches[0]) == 3


def test_dependency_graph_cycle_detection():
    graph = DependencyGraph()
    graph.edges = {"a": {"b"}, "b": {"a"}}  # cycle
    with pytest.raises(ValueError):
        graph.topological_batches()


# ─── Delegation ledger ──────────────────────────────────────────────


def test_ledger_basic():
    ledger = DelegationLedger(trace_id="test-trace")
    ledger.suggest("unit-1", "code-reviewer", backend="codex_exec")
    ledger.update(
        "unit-1",
        status="completed",
        backend="codex_exec",
        executed_worker_kind="cli-process",
        executed_worker_id="codex",
        native_run_id="codex:process:1",
    )

    d = ledger.as_dict()
    assert d["trace_id"] == "test-trace"
    assert len(d["work_units"]) == 1
    assert d["work_units"][0]["status"] == "completed"
    assert d["work_units"][0]["recommended_agent"] == "code-reviewer"


def test_ledger_skip():
    ledger = DelegationLedger(trace_id="test-trace")
    ledger.suggest("unit-1", "code-reviewer")
    ledger.update("unit-1", status="skipped", skip_reason="no backend available")

    d = ledger.as_dict()
    assert d["work_units"][0]["status"] == "skipped"
    assert "no backend" in d["work_units"][0]["skip_reason"]


def test_ledger_json_serializable():
    import json

    ledger = DelegationLedger(trace_id="test")
    ledger.suggest("unit-1", "agent-a", backend="codex")
    ledger.suggest("unit-2", "agent-b", backend="hermes")
    j = ledger.to_json()
    parsed = json.loads(j)
    assert len(parsed["work_units"]) == 2


# ─── Delegate with lifecycle ────────────────────────────────────────


def test_delegate_with_lifecycle_no_repo():
    """Test lifecycle dispatch without git repos (pure function calls)."""

    def mock_delegate(**kwargs):
        return {"status": "done", "task": kwargs.get("task", "")}

    result = delegate_with_lifecycle(
        ["review code", "write tests"],
        delegate_func=mock_delegate,
    )
    assert len(result.work_units) == 2
    assert len(result.dispatch_results) == 2


def test_delegate_with_lifecycle_empty():
    result = delegate_with_lifecycle([], delegate_func=lambda **kw: None)
    assert len(result.work_units) == 0


# ─── Backend registry ───────────────────────────────────────────────


def test_backend_registry(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(CommandBackend, "is_available", lambda _self: True)
    registry = BackendRegistry()
    backend = CommandBackend(command=[sys.executable], name="test-python")
    registry.register(backend)
    available = registry.available_backends()
    assert len(available) == 1
    assert available[0].name == "test-python"


def test_backend_registry_no_available():
    registry = BackendRegistry()
    backend = CommandBackend(command=["nonexistent-cmd-xyz"], name="missing")
    registry.register(backend)
    available = registry.available_backends()
    assert len(available) == 0
