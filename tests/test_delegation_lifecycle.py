"""Regression tests for delegation lifecycle, ledger, and backend selection."""

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

import pytest

from agency_runtime.core.delegation.backends import BackendRegistry, CommandBackend, DelegateBackend
from agency_runtime.core.delegation.ledger import DelegationLedger
from agency_runtime.core.delegation.lifecycle import (
    aggregate_results,
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


def test_normalize_work_units_rejects_duplicate_normalized_ids() -> None:
    with pytest.raises(ValueError, match=r"duplicate work-unit id.*'A-1'"):
        normalize_work_units(
            [
                {"id": "A/1", "description": "First task"},
                {"id": "A 1", "description": "Second task"},
            ]
        )


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


def test_delegate_with_lifecycle_preserves_delegate_type_errors(tmp_path: Path) -> None:
    def delegate_func(**kwargs):
        raise TypeError("inner delegate bug")

    result = delegate_with_lifecycle(
        [{"id": "unit-1", "description": "Do the work", "recommended_agent": "builder"}],
        repo_path=tmp_path,
        delegate_func=delegate_func,
        merge_back=False,
    )

    assert result.dispatch_results["unit-1"] == {"error": "inner delegate bug"}
    assert "inner delegate bug" in result.warnings[0]


def test_failed_predecessor_skips_dependent_unit(tmp_path: Path) -> None:
    calls: list[str] = []
    ledger = DelegationLedger(trace_id="dependency-failure")

    def delegate_func(*, task: str, **kwargs):
        unit_id = task.splitlines()[0].removeprefix("Work unit ").removesuffix(":")
        calls.append(unit_id)
        raise RuntimeError("producer failed")

    result = delegate_with_lifecycle(
        [
            {"id": "producer", "description": "Produce the input"},
            {"id": "consumer", "description": "Then consume the producer output"},
        ],
        repo_path=tmp_path,
        delegate_func=delegate_func,
        ledger=ledger,
        merge_back=False,
    )

    assert calls == ["producer"]
    assert result.dispatch_results["producer"] == {"error": "producer failed"}
    assert result.dispatch_results["consumer"] == {
        "status": "skipped",
        "skip_reason": "dependency did not complete successfully: producer",
        "blocked_by": ["producer"],
    }
    statuses = {entry.id: entry.status for entry in ledger.entries}
    assert statuses == {"producer": "failed", "consumer": "skipped"}
    assert "0 completed, 2 failed/not completed" in result.summary


def test_unsuccessful_result_skips_dependent_unit(tmp_path: Path) -> None:
    calls: list[str] = []

    def delegate_func(*, task: str, **kwargs):
        unit_id = task.splitlines()[0].removeprefix("Work unit ").removesuffix(":")
        calls.append(unit_id)
        return {"ok": False, "message": "validation failed"}

    result = delegate_with_lifecycle(
        [
            {"id": "producer", "description": "Produce the input"},
            {"id": "consumer", "description": "Then consume the producer output"},
        ],
        repo_path=tmp_path,
        delegate_func=delegate_func,
        merge_back=False,
    )

    assert calls == ["producer"]
    assert result.dispatch_results["consumer"]["status"] == "skipped"
    assert result.dispatch_results["consumer"]["blocked_by"] == ["producer"]


def test_aggregate_results_counts_missing_result_as_not_completed() -> None:
    units = normalize_work_units(
        [
            {"id": "one", "description": "First task"},
            {"id": "two", "description": "Second task"},
        ]
    )
    graph = build_dependency_graph(units)

    summary = aggregate_results(
        units,
        graph,
        [["one", "two"]],
        {},
        {"one": {"ok": True}},
        {},
        [],
        [],
    )

    assert "Worker results: 1 completed, 1 failed/not completed." in summary


def test_none_worker_result_is_not_completed(tmp_path: Path) -> None:
    result = delegate_with_lifecycle(
        [{"id": "unit", "description": "Do the work"}],
        repo_path=tmp_path,
        delegate_func=lambda **_kwargs: None,
        merge_back=False,
    )

    assert "0 completed, 1 failed/not completed" in result.summary


@pytest.mark.parametrize("ambiguous", ["", 0, [], {}, {"status": ""}])
def test_ambiguous_worker_results_are_not_completed(
    tmp_path: Path,
    ambiguous: object,
) -> None:
    result = delegate_with_lifecycle(
        [{"id": "unit", "description": "Do the work"}],
        repo_path=tmp_path,
        delegate_func=lambda **_kwargs: ambiguous,
        merge_back=False,
    )

    assert "0 completed, 1 failed/not completed" in result.summary


def test_independent_units_still_dispatch_concurrently(tmp_path: Path) -> None:
    rendezvous = threading.Barrier(2)

    def delegate_func(*, task: str, **kwargs):
        rendezvous.wait(timeout=2)
        return {"ok": True, "task": task}

    result = delegate_with_lifecycle(
        [
            {"id": "one", "description": "Independent task one"},
            {"id": "two", "description": "Independent task two"},
        ],
        repo_path=tmp_path,
        delegate_func=delegate_func,
        merge_back=False,
    )

    assert result.batches == [["one", "two"]]
    assert all(payload["ok"] for payload in result.dispatch_results.values())


def test_delegate_with_lifecycle_supports_task_only_delegate(tmp_path: Path) -> None:
    def delegate_func(*, task: str):
        return {"backend": "task-only", "task": task, "status": "completed"}

    result = delegate_with_lifecycle(
        [{"id": "unit-1", "description": "Do the task"}],
        repo_path=tmp_path,
        delegate_func=delegate_func,
        merge_back=False,
    )

    assert result.dispatch_results["unit-1"]["backend"] == "task-only"
    assert "Do the task" in result.dispatch_results["unit-1"]["task"]


def test_delegate_with_lifecycle_supports_legacy_goal_context_delegate(tmp_path: Path) -> None:
    def delegate_func(*, goal: str, context: str, recommended_agent: str):
        return {"backend": "legacy", "goal": goal, "context": context, "agent": recommended_agent, "status": "completed"}

    result = delegate_with_lifecycle(
        [{"id": "unit-1", "description": "Do the legacy task", "recommended_agent": "builder"}],
        repo_path=tmp_path,
        delegate_func=delegate_func,
        merge_back=False,
    )

    dispatched = result.dispatch_results["unit-1"]
    assert dispatched["backend"] == "legacy"
    assert dispatched["goal"] == "Do the legacy task"
    assert dispatched["context"] == f"workdir={tmp_path.resolve()}"
    assert dispatched["agent"] == "builder"


def test_lifecycle_provisions_worktrees_merges_back_and_removes_paths(tmp_path: Path) -> None:
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
        return {"backend": "fake", "unit_id": unit_id, "status": "completed"}

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


def test_single_git_work_unit_is_always_isolated(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True, text=True)
    observed_workdirs: list[Path] = []

    def delegate_func(*, workdir: str | None = None, **_kwargs):
        assert workdir is not None
        isolated = Path(workdir)
        observed_workdirs.append(isolated)
        assert isolated.resolve() != repo.resolve()
        (isolated / "single.txt").write_text("isolated\n", encoding="utf-8")
        return {"status": "completed"}

    result = delegate_with_lifecycle(
        [{"id": "single", "description": "create single.txt"}],
        repo_path=repo,
        delegate_func=delegate_func,
        worktree_root=tmp_path / "worktrees",
    )

    assert len(observed_workdirs) == 1
    assert (repo / "single.txt").read_text(encoding="utf-8") == "isolated\n"
    assert result.cleanup_results["single"]["merged"] is True
    assert result.cleanup_results["single"]["branch_deleted"] is True


def test_repeated_unit_ids_use_unique_owned_worktrees_and_branches(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True, text=True)

    def delegate_func(*, workdir: str | None = None, **_kwargs):
        assert workdir is not None
        return {"status": "completed"}

    first = delegate_with_lifecycle(
        [{"id": "same", "description": "first pass"}],
        repo_path=repo,
        delegate_func=delegate_func,
        worktree_root=tmp_path / "worktrees",
        merge_back=False,
    )
    second = delegate_with_lifecycle(
        [{"id": "same", "description": "second pass"}],
        repo_path=repo,
        delegate_func=delegate_func,
        worktree_root=tmp_path / "worktrees",
        merge_back=False,
    )

    assert first.worktrees["same"].path != second.worktrees["same"].path
    assert first.worktrees["same"].branch != second.worktrees["same"].branch


def test_successful_uncommitted_worker_edits_are_committed_and_merged(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True, text=True)

    def delegate_func(*, task: str, workdir: str | None = None, **_kwargs):
        assert workdir is not None
        unit_id = task.splitlines()[0].removeprefix("Work unit ").removesuffix(":")
        (Path(workdir) / f"{unit_id}.txt").write_text(f"{unit_id}\n", encoding="utf-8")
        return {"ok": True, "backend": "fake"}

    result = delegate_with_lifecycle(
        [
            {"id": "one", "description": "create one.txt"},
            {"id": "two", "description": "create two.txt"},
        ],
        repo_path=repo,
        delegate_func=delegate_func,
        worktree_root=tmp_path / "worktrees",
        merge_back=True,
    )

    assert (repo / "one.txt").read_text(encoding="utf-8") == "one\n"
    assert (repo / "two.txt").read_text(encoding="utf-8") == "two\n"
    assert all(record["merged"] for record in result.cleanup_results.values())
    assert all(record["removed"] for record in result.cleanup_results.values())


def test_failed_uncommitted_worker_edits_are_preserved(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True, text=True)

    def delegate_func(*, task: str, workdir: str | None = None, **_kwargs):
        assert workdir is not None
        unit_id = task.splitlines()[0].removeprefix("Work unit ").removesuffix(":")
        (Path(workdir) / f"{unit_id}.txt").write_text("recover me\n", encoding="utf-8")
        raise RuntimeError("worker failed after editing")

    result = delegate_with_lifecycle(
        [
            {"id": "one", "description": "create one.txt"},
            {"id": "two", "description": "create two.txt"},
        ],
        repo_path=repo,
        delegate_func=delegate_func,
        worktree_root=tmp_path / "worktrees",
        merge_back=True,
    )

    assert all(record["preserved"] for record in result.cleanup_results.values())
    assert all(not record["removed"] for record in result.cleanup_results.values())
    for unit_id, info in result.worktrees.items():
        assert (info.path / f"{unit_id}.txt").read_text(encoding="utf-8") == "recover me\n"


def test_dependent_worktree_sees_successful_predecessor_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True, text=True)

    def delegate_func(*, task: str, workdir: str | None = None, **kwargs):
        assert workdir is not None
        unit_id = task.splitlines()[0].removeprefix("Work unit ").removesuffix(":")
        worktree = Path(workdir)
        if unit_id == "producer":
            (worktree / "artifact.txt").write_text("from producer\n", encoding="utf-8")
            subprocess.run(["git", "add", "artifact.txt"], cwd=worktree, check=True)
        else:
            assert (worktree / "artifact.txt").read_text(encoding="utf-8") == "from producer\n"
            (worktree / "observed.txt").write_text("consumer saw artifact\n", encoding="utf-8")
            subprocess.run(["git", "add", "observed.txt"], cwd=worktree, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"{unit_id} work"],
            cwd=worktree,
            check=True,
            capture_output=True,
            text=True,
        )
        return {"ok": True, "unit_id": unit_id}

    result = delegate_with_lifecycle(
        [
            {"id": "producer", "description": "Create an artifact"},
            {"id": "consumer", "description": "Then consume the producer output"},
        ],
        repo_path=repo,
        delegate_func=delegate_func,
        worktree_root=tmp_path / "worktrees",
        merge_back=True,
    )

    assert result.batches == [["producer"], ["consumer"]]
    assert result.dispatch_results["consumer"]["ok"] is True
    assert (repo / "artifact.txt").read_text(encoding="utf-8") == "from producer\n"
    assert (repo / "observed.txt").read_text(encoding="utf-8") == "consumer saw artifact\n"


def test_failed_worktree_branch_is_not_merged_back(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True, text=True)

    def delegate_func(*, task: str, workdir: str | None = None, **kwargs):
        assert workdir is not None
        unit_id = task.splitlines()[0].removeprefix("Work unit ").removesuffix(":")
        if unit_id != "producer":
            pytest.fail("dependent unit must not run after predecessor failure")
        worktree = Path(workdir)
        (worktree / "partial.txt").write_text("must not merge\n", encoding="utf-8")
        subprocess.run(["git", "add", "partial.txt"], cwd=worktree, check=True)
        subprocess.run(
            ["git", "commit", "-m", "partial work"],
            cwd=worktree,
            check=True,
            capture_output=True,
            text=True,
        )
        raise RuntimeError("producer failed after committing partial work")

    result = delegate_with_lifecycle(
        [
            {"id": "producer", "description": "Create an artifact"},
            {"id": "consumer", "description": "Then consume the producer output"},
        ],
        repo_path=repo,
        delegate_func=delegate_func,
        worktree_root=tmp_path / "worktrees",
        merge_back=True,
    )

    assert not (repo / "partial.txt").exists()
    assert result.cleanup_results["producer"]["merged"] is False
    assert "did not complete successfully" in result.cleanup_results["producer"]["warnings"][-1]
    assert result.dispatch_results["consumer"]["status"] == "skipped"


def test_backend_registry_selects_first_available_backend() -> None:
    registry = BackendRegistry()
    registry.register(FakeBackend(False))
    registry.register(FakeBackend(True))
    registry.register(CommandBackend(command=["python3", "-c", "print('unused')"]))

    backend = registry.select_backend()

    assert backend.name == "fake"
    assert backend.is_available()
