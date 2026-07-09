"""Regression tests for delegation lifecycle, ledger, and backend selection."""

from __future__ import annotations

import json
from pathlib import Path

from agency_runtime.core.delegation.backends import BackendRegistry, CommandBackend, DelegateBackend
from agency_runtime.core.delegation.ledger import DelegationLedger
from agency_runtime.core.delegation.lifecycle import (
    build_dependency_graph,
    delegate_with_lifecycle,
    normalize_work_units,
)
from agency_runtime.core.store.sqlite import Store


class FakeBackend(DelegateBackend):
    name = "fake"

    def __init__(self, available: bool) -> None:
        self.available = available

    def is_available(self) -> bool:
        return self.available

    def delegate(self, *, task: str, workdir: str | None = None, recommended_agent: str | None = None, **kwargs):
        return {"task": task, "workdir": workdir, "recommended_agent": recommended_agent}


def test_normalize_work_units_preserves_contract_fields(tmp_path: Path) -> None:
    units = normalize_work_units(
        [{"id": "A/1", "description": "Edit README.md", "recommended_agent": "docs-agent"}],
        repo_path=tmp_path,
    )

    assert units[0].id == "A-1"
    assert units[0].description == "Edit README.md"
    assert units[0].recommended_agent == "docs-agent"
    assert units[0].repo_path == tmp_path.resolve()


def test_dependency_graph_orders_overlapping_files(tmp_path: Path) -> None:
    units = normalize_work_units(
        [
            {"id": "one", "description": "Change shared.py", "files": ["shared.py"]},
            {"id": "two", "description": "Also change shared.py", "files": ["shared.py"]},
            {"id": "three", "description": "Change other.py", "files": ["other.py"]},
        ],
        repo_path=tmp_path,
    )

    graph = build_dependency_graph(units)

    assert graph.edges["one"] == {"two"}
    assert graph.topological_batches() == [["one", "three"], ["two"]]


def test_delegate_with_lifecycle_dispatches_and_records_ledger(tmp_path: Path) -> None:
    db = tmp_path / "agency.db"
    ledger = DelegationLedger(Store(db), trace_id="trace-1", session_id="session-1", host="test-host")
    calls: list[dict[str, str | None]] = []

    def delegate_func(*, task: str, workdir: str | None = None, recommended_agent: str | None = None, **kwargs):
        calls.append({"task": task, "workdir": workdir, "recommended_agent": recommended_agent})
        return {"ok": True, "backend": "fake-backend"}

    result = delegate_with_lifecycle(
        [{"id": "unit-1", "description": "Do the work", "recommended_agent": "builder"}],
        repo_path=tmp_path,
        delegate_func=delegate_func,
        ledger=ledger,
        merge_back=False,
    )

    assert result.dispatch_results["unit-1"]["ok"] is True
    assert calls == [{"task": calls[0]["task"], "workdir": str(tmp_path.resolve()), "recommended_agent": "builder"}]
    payload = json.loads(ledger.to_json())
    assert payload["trace_id"] == "trace-1"
    assert payload["session_id"] == "session-1"
    assert payload["host"] == "test-host"
    assert payload["work_units"] == [
        {
            "id": "unit-1",
            "recommended_agent": "builder",
            "status": "completed",
            "backend": "fake-backend",
            "skip_reason": "",
            "error": "",
        }
    ]


def test_lifecycle_provisions_worktrees_merges_back_and_removes_paths(tmp_path: Path) -> None:
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True, text=True)

    def delegate_func(*, task: str, workdir: str | None = None, recommended_agent: str | None = None, **kwargs):
        assert workdir is not None
        unit_id = "one" if "one" in task else "two"
        path = Path(workdir) / f"{unit_id}.txt"
        path.write_text(f"{unit_id}\n", encoding="utf-8")
        subprocess.run(["git", "add", path.name], cwd=workdir, check=True)
        subprocess.run(["git", "commit", "-m", f"{unit_id} work"], cwd=workdir, check=True, capture_output=True, text=True)
        return {"backend": "fake", "unit_id": unit_id}

    worktree_root = tmp_path / "worktrees"
    result = delegate_with_lifecycle(
        [
            {"id": "one", "description": "create one.txt", "recommended_agent": "agent-a"},
            {"id": "two", "description": "create two.txt", "recommended_agent": "agent-b"},
        ],
        repo_path=repo,
        delegate_func=delegate_func,
        worktree_root=worktree_root,
        merge_back=True,
    )

    assert set(result.worktrees) == {"one", "two"}
    assert all(info.created for info in result.worktrees.values())
    assert all(record["removed"] for record in result.cleanup_results.values())
    assert (repo / "one.txt").read_text(encoding="utf-8") == "one\n"
    assert (repo / "two.txt").read_text(encoding="utf-8") == "two\n"
    assert not any(info.path.exists() for info in result.worktrees.values())


def test_backend_registry_selects_first_available_backend() -> None:
    registry = BackendRegistry()
    registry.register(FakeBackend(False))
    registry.register(FakeBackend(True))
    registry.register(CommandBackend(command=["python3", "-c", "print('unused')"]))

    backend = registry.select_backend()

    assert backend.name == "fake"
    assert backend.is_available()
