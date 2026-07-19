"""Regression tests for delegation lifecycle, ledger, and backend selection."""

from __future__ import annotations

import asyncio
import json
import subprocess
import threading
from pathlib import Path

import pytest

from agency_runtime.core.delegation import lifecycle as lifecycle_module
from agency_runtime.core.delegation.backends import (
    BackendRegistry,
    CommandBackend,
    DelegateBackend,
)
from agency_runtime.core.delegation.ledger import DelegationLedger
from agency_runtime.core.delegation.lifecycle import (
    DependencyGraph,
    WorktreeInfo,
    aggregate_results,
    build_dependency_graph,
    cleanup_worktrees,
    delegate_with_lifecycle,
    dispatch_work_units,
    normalize_work_units,
    provision_worktrees,
)
from agency_runtime.core.delegation.lifecycle_graph import (
    MAX_DEPENDENCIES_PER_UNIT,
    MAX_DESCRIPTION_CHARS,
    MAX_FILES_PER_UNIT,
    MAX_UNIT_ID_CHARS,
    MAX_WORK_UNITS,
)
from agency_runtime.core.delegation.lifecycle_types import WorkUnit
from agency_runtime.core.store.sqlite import Store


class FakeBackend(DelegateBackend):
    name = "fake"

    def __init__(self, available: bool) -> None:
        self.available = available

    def is_available(self) -> bool:
        return self.available

    def delegate(
        self,
        *,
        task: str,
        workdir: str | None = None,
        recommended_agent: str | None = None,
        **kwargs,
    ):
        return {
            "task": task,
            "workdir": workdir,
            "recommended_agent": recommended_agent,
        }


@pytest.fixture
def non_git_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Provide an explicit non-Git boundary even when basetemp is in this repo."""
    monkeypatch.setattr(lifecycle_module, "_git_root", lambda _path: None)
    return tmp_path


def _initialize_test_repo(repo: Path) -> None:
    """Create a deterministic repository isolated from operator Git settings."""
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    disabled_hooks = repo / ".git" / "test-hooks-disabled"
    disabled_hooks.mkdir()
    for key, value in (
        ("user.email", "test@example.com"),
        ("user.name", "Test User"),
        ("commit.gpgsign", "false"),
        ("core.autocrlf", "false"),
        ("core.longpaths", "true"),
        ("core.hooksPath", str(disabled_hooks)),
    ):
        subprocess.run(
            ["git", "config", "--local", key, value],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def test_normalize_work_units_preserves_contract_fields(tmp_path: Path) -> None:
    units = normalize_work_units(
        [
            {
                "id": "A-1",
                "description": "Edit README.md",
                "recommended_agent": "docs-agent",
            }
        ],
        repo_path=tmp_path,
    )

    assert units[0].id == "A-1"
    assert units[0].description == "Edit README.md"
    assert units[0].recommended_agent == "docs-agent"
    assert units[0].repo_path == tmp_path.resolve()


def test_normalize_work_units_preserves_explicit_dependencies() -> None:
    units = normalize_work_units(
        [
            {"id": "setup", "description": "Prepare inputs"},
            {
                "id": "run-report",
                "description": "Generate report",
                "depends_on": "setup",
            },
        ]
    )

    assert units[1].id == "run-report"
    assert units[1].depends_on == {"setup"}


def test_normalize_none_is_an_empty_workload() -> None:
    assert normalize_work_units(None) == []


@pytest.mark.parametrize("depends_on", ["", [""], [1], {"unit": "setup"}])
def test_normalize_work_units_rejects_invalid_dependencies(depends_on: object) -> None:
    with pytest.raises((TypeError, ValueError), match="depends_on"):
        normalize_work_units(
            [{"id": "run", "description": "Generate report", "depends_on": depends_on}]
        )


@pytest.mark.parametrize("files", [1, b"path.py", {"path": "file.py"}, [""]])
def test_normalize_work_units_rejects_invalid_file_lists(files: object) -> None:
    with pytest.raises((TypeError, ValueError), match="files"):
        normalize_work_units([{"id": "run", "description": "Generate report", "files": files}])


def test_normalize_work_units_rejects_malformed_ids_before_normalizing() -> None:
    with pytest.raises(ValueError, match="canonical id characters"):
        normalize_work_units([{"id": "A/1", "description": "First task"}])


def test_normalize_work_units_rejects_duplicate_explicit_ids() -> None:
    with pytest.raises(ValueError, match=r"duplicate work-unit id.*'A-1'"):
        normalize_work_units(
            [
                {"id": "A-1", "description": "First task"},
                {"id": "A-1", "description": "Second task"},
            ]
        )


def test_normalize_work_units_caps_an_arbitrary_iterable_before_materializing_it() -> None:
    consumed: list[int] = []

    def items():
        for index in range(100):
            consumed.append(index)
            yield {"id": f"unit-{index}", "description": f"Task {index}"}

    with pytest.raises(ValueError, match=f"more than {MAX_WORK_UNITS}"):
        normalize_work_units(items())

    assert len(consumed) == MAX_WORK_UNITS + 1


@pytest.mark.parametrize(
    "unit_id",
    ["", " leading", "trailing ", "contains space", "slash/id", 7, "x" * (MAX_UNIT_ID_CHARS + 1)],
)
def test_normalize_work_units_rejects_invalid_explicit_ids(unit_id: object) -> None:
    with pytest.raises((TypeError, ValueError), match="work-unit id"):
        normalize_work_units([{"id": unit_id, "description": "Task"}])


def test_missing_unit_ids_are_deterministic() -> None:
    payload = [{"description": "Deterministic task"}]

    first = normalize_work_units(payload)
    second = normalize_work_units(payload)

    assert first[0].id == second[0].id
    assert first[0].id.startswith("unit-1-")


def test_normalize_work_units_enforces_description_file_and_dependency_bounds() -> None:
    with pytest.raises(ValueError, match="description exceeds"):
        normalize_work_units([{"description": "x" * (MAX_DESCRIPTION_CHARS + 1)}])
    with pytest.raises(ValueError, match=f"more than {MAX_FILES_PER_UNIT}"):
        normalize_work_units(
            [
                {
                    "id": "unit",
                    "description": "Task",
                    "files": (f"file-{index}.py" for index in range(MAX_FILES_PER_UNIT + 1)),
                }
            ]
        )
    with pytest.raises(ValueError, match=f"more than {MAX_DEPENDENCIES_PER_UNIT}"):
        normalize_work_units(
            [
                {
                    "id": "unit",
                    "description": "Task",
                    "depends_on": (
                        f"dependency-{index}" for index in range(MAX_DEPENDENCIES_PER_UNIT + 1)
                    ),
                }
            ]
        )


def test_normalize_work_units_rejects_unsafe_prompt_metadata() -> None:
    with pytest.raises(ValueError, match="NUL"):
        normalize_work_units([{"description": "unsafe\x00task"}])
    with pytest.raises(ValueError, match="control characters"):
        normalize_work_units(
            [
                {
                    "description": "Task",
                    "recommended_agent": "unsafe\nagent",
                }
            ]
        )


def test_public_graph_boundary_rejects_more_than_sixteen_units() -> None:
    units = [WorkUnit(f"unit-{index}", "Task") for index in range(MAX_WORK_UNITS + 1)]

    with pytest.raises(ValueError, match=f"more than {MAX_WORK_UNITS}"):
        build_dependency_graph(units)


def test_dependency_graph_orders_overlapping_files(tmp_path: Path) -> None:
    units = normalize_work_units(
        [
            {"id": "one", "description": "Change shared.py", "files": ["shared.py"]},
            {
                "id": "two",
                "description": "Also change shared.py",
                "files": ["shared.py"],
            },
            {"id": "three", "description": "Change other.py", "files": ["other.py"]},
        ],
        repo_path=tmp_path,
    )

    graph = build_dependency_graph(units)

    assert graph.edges["one"] == {"two"}
    assert graph.topological_batches() == [["one", "three"], ["two"]]


def test_dependency_graph_honors_explicit_dependencies() -> None:
    units = normalize_work_units(
        [
            {"id": "publish", "description": "Publish report", "depends_on": ["build"]},
            {"id": "build", "description": "Build report"},
            {"id": "lint", "description": "Lint source"},
        ]
    )

    graph = build_dependency_graph(units)

    assert graph.edges["build"] == {"publish"}
    assert graph.reasons[("build", "publish")] == "explicit depends_on"
    assert graph.topological_batches() == [["build", "lint"], ["publish"]]


def test_dependency_graph_rejects_unknown_explicit_dependency() -> None:
    units = normalize_work_units(
        [{"id": "publish", "description": "Publish report", "depends_on": ["build"]}]
    )

    with pytest.raises(ValueError, match=r"'publish'.*unknown.*'build'"):
        build_dependency_graph(units)


def test_dependency_graph_rejects_explicit_cycle_before_provisioning() -> None:
    units = normalize_work_units(
        [
            {"id": "a", "description": "Task A", "depends_on": ["b"]},
            {"id": "b", "description": "Task B", "depends_on": ["a"]},
        ]
    )

    with pytest.raises(ValueError, match="dependency graph contains a cycle"):
        build_dependency_graph(units)


def test_dependency_graph_batches_are_stably_sorted() -> None:
    graph = DependencyGraph(edges={"a": {"z"}, "b": {"c"}, "c": set(), "z": set()})

    assert graph.topological_batches() == [["a", "b"], ["c", "z"]]


def test_provision_worktrees_does_not_allocate_for_non_git_work(
    non_git_repo: Path,
) -> None:
    worktree_root = non_git_repo / "worktrees"
    units = normalize_work_units(
        [{"id": "docs", "description": "Draft a standalone note"}],
        repo_path=non_git_repo,
    )

    assert provision_worktrees(units, worktree_root=worktree_root) == {}
    assert not worktree_root.exists()


def test_provision_worktrees_reports_git_discovery_failure_per_unit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    units = normalize_work_units(
        [{"id": "code", "description": "Change code"}],
        repo_path=tmp_path,
    )
    monkeypatch.setattr(
        lifecycle_module,
        "_git_root",
        lambda _path: (_ for _ in ()).throw(subprocess.TimeoutExpired("git", 10)),
    )

    worktrees = provision_worktrees(
        units,
        worktree_root=tmp_path / "worktrees",
    )

    assert worktrees["code"].created is False
    assert "could not determine Git repository" in worktrees["code"].errors[0]
    assert not (tmp_path / "worktrees").exists()


def test_provision_worktrees_rejects_option_like_base_ref_before_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    units = normalize_work_units(
        [{"id": "code", "description": "Change code"}],
        repo_path=tmp_path,
    )
    monkeypatch.setattr(
        lifecycle_module,
        "_git_root",
        lambda _path: pytest.fail("Git discovery must not run for an unsafe ref"),
    )

    with pytest.raises(ValueError, match="base_branch"):
        provision_worktrees(
            units,
            base_branch="--upload-pack=attacker-command",
            worktree_root=tmp_path / "worktrees",
        )


def test_unsafe_base_ref_blocks_lifecycle_dispatch(tmp_path: Path) -> None:
    calls: list[str] = []

    result = delegate_with_lifecycle(
        [{"id": "code", "description": "Change code"}],
        repo_path=tmp_path,
        base_branch="--upload-pack=attacker-command",
        delegate_func=lambda **_kwargs: calls.append("called"),
    )

    assert calls == []
    assert result.dispatch_results["code"]["status"] == "failed"
    assert "base_branch" in result.errors[0]


def test_provision_worktrees_pins_allocation_to_inspected_sha(
    git_integration_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = git_integration_root
    repo = tmp_path / "repo"
    repo.mkdir()
    units = normalize_work_units(
        [{"id": "code", "description": "Change code"}],
        repo_path=repo,
    )
    commands: list[list[str]] = []

    def fake_git(
        _repo: Path, args: list[str], *, timeout: int = 120
    ) -> subprocess.CompletedProcess[str]:
        del timeout
        commands.append(list(args))
        return subprocess.CompletedProcess(["git", *args], 0, "", "")

    monkeypatch.setattr(lifecycle_module, "_git_root", lambda _path: repo)
    monkeypatch.setattr(lifecycle_module, "_current_branch", lambda _repo: "main")
    monkeypatch.setattr(
        lifecycle_module,
        "_head_sha",
        lambda _repo, _ref="HEAD": "a" * 40,
    )
    monkeypatch.setattr(lifecycle_module, "_run_git", fake_git)

    provision_worktrees(units, worktree_root=tmp_path / "worktrees")

    add_command = next(args for args in commands if "worktree" in args)
    assert add_command[:3] == ["-c", "core.hooksPath=", "worktree"]
    assert add_command[-1] == "a" * 40


def test_provision_worktrees_suppresses_repository_post_checkout_hook(
    git_integration_root: Path,
) -> None:
    tmp_path = git_integration_root
    repo = tmp_path / "repo"
    _initialize_test_repo(repo)
    hooks = repo / ".git" / "hostile-hooks"
    hooks.mkdir()
    post_checkout = hooks / "post-checkout"
    post_checkout.write_text(
        "#!/bin/sh\nprintf exploited > hook-ran\n",
        encoding="utf-8",
        newline="\n",
    )
    post_checkout.chmod(0o700)
    subprocess.run(
        ["git", "config", "--local", "core.hooksPath", str(hooks)],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    units = normalize_work_units(
        [{"id": "code", "description": "Change code"}],
        repo_path=repo,
    )
    worktree_root = tmp_path / "worktrees"

    worktrees = provision_worktrees(units, worktree_root=worktree_root)

    assert worktrees["code"].created is True
    assert not (worktrees["code"].path / "hook-ran").exists()


def test_cleanup_preserves_worktree_when_git_inspection_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = WorktreeInfo(
        unit_id="code",
        repo_path=tmp_path / "repo",
        path=tmp_path / "worktree",
        branch="delegation/code-safe",
        base_branch="main",
        base_sha="a" * 40,
        created=True,
    )
    monkeypatch.setattr(lifecycle_module, "_current_branch", lambda _repo: "main")
    monkeypatch.setattr(
        lifecycle_module,
        "_head_sha",
        lambda _repo, _ref="HEAD": "a" * 40,
    )
    monkeypatch.setattr(
        lifecycle_module,
        "_run_git",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired("git status", 30)
        ),
    )

    cleanup = cleanup_worktrees({"code": info}, merge_back=True)

    assert cleanup["code"]["preserved"] is True
    assert cleanup["code"]["removed"] is False
    assert "cleanliness could not be proven" in cleanup["code"]["warnings"][-1]
    assert "TimeoutExpired" in cleanup["code"]["errors"][-1]


def test_provisioning_exception_blocks_repo_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        lifecycle_module,
        "provision_worktrees",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("worktree root unavailable")),
    )

    result = delegate_with_lifecycle(
        [{"id": "code", "description": "Change code"}],
        repo_path=tmp_path,
        delegate_func=lambda **_kwargs: calls.append("called"),
    )

    assert calls == []
    assert result.dispatch_results["code"]["status"] == "failed"
    assert "worktree provisioning failed" in result.dispatch_results["code"]["error"]
    assert "worktree provisioning failed" in result.errors[0]


@pytest.mark.parametrize("max_workers", [0, -1, True, 1.5])
def test_dispatch_rejects_invalid_worker_count(max_workers: object) -> None:
    units = normalize_work_units([{"id": "one", "description": "Do work"}])
    graph = build_dependency_graph(units)

    with pytest.raises(ValueError, match="max_workers"):
        dispatch_work_units(
            units,
            graph,
            {},
            delegate_func=lambda **_kwargs: {"ok": True},
            max_workers=max_workers,  # type: ignore[arg-type]
        )


def test_lifecycle_validates_worker_and_delegate_contracts_before_provisioning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provisioned: list[bool] = []
    monkeypatch.setattr(
        lifecycle_module,
        "provision_worktrees",
        lambda *_args, **_kwargs: provisioned.append(True) or {},
    )

    with pytest.raises(ValueError, match="max_workers"):
        delegate_with_lifecycle(
            [{"id": "unit", "description": "Task"}],
            delegate_func=lambda task: {"status": "completed"},
            max_workers=0,
        )
    with pytest.raises(TypeError, match="must be callable"):
        delegate_with_lifecycle(
            [{"id": "unit", "description": "Task"}],
            delegate_func=object(),  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="must accept"):
        delegate_with_lifecycle(
            [{"id": "unit", "description": "Task"}],
            delegate_func=lambda *, unsupported: {"status": "completed"},
        )

    assert provisioned == []


def test_lifecycle_resolves_default_backend_before_provisioning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provisioned: list[bool] = []
    monkeypatch.setattr(
        lifecycle_module,
        "provision_worktrees",
        lambda *_args, **_kwargs: provisioned.append(True) or {},
    )
    monkeypatch.setattr(
        lifecycle_module,
        "_resolve_delegate_func",
        lambda _delegate: (_ for _ in ()).throw(RuntimeError("no backend")),
    )

    with pytest.raises(RuntimeError, match="no backend"):
        delegate_with_lifecycle([{"id": "unit", "description": "Task"}])

    assert provisioned == []


def test_empty_dispatch_does_not_resolve_a_backend() -> None:
    assert dispatch_work_units([], DependencyGraph(), {}) == ({}, [], [])


def test_delegate_with_lifecycle_dispatches_and_records_ledger(
    non_git_repo: Path,
) -> None:
    db = non_git_repo / "agency.db"
    ledger = DelegationLedger(
        Store(db), trace_id="trace-1", session_id="session-1", host="test-host"
    )
    calls: list[dict[str, str | None]] = []

    def delegate_func(
        *,
        task: str,
        workdir: str | None = None,
        recommended_agent: str | None = None,
        **kwargs,
    ):
        calls.append({"task": task, "workdir": workdir, "recommended_agent": recommended_agent})
        return {
            "ok": True,
            "backend": "fake-backend",
            "executed_worker_kind": "test-worker",
            "executed_worker_id": "worker-unit-1",
            "native_run_id": "fake-backend:unit-1",
        }

    result = delegate_with_lifecycle(
        [
            {
                "id": "unit-1",
                "description": "Do the work",
                "recommended_agent": "builder",
            }
        ],
        repo_path=non_git_repo,
        delegate_func=delegate_func,
        ledger=ledger,
        merge_back=False,
    )

    assert result.dispatch_results["unit-1"]["ok"] is True
    assert calls == [
        {
            "task": calls[0]["task"],
            "workdir": str(non_git_repo.resolve()),
            "recommended_agent": "builder",
        }
    ]
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
            "executed_worker_kind": "test-worker",
            "executed_worker_id": "worker-unit-1",
            "native_run_id": "fake-backend:unit-1",
            "skip_reason": "",
            "error": "",
        }
    ]


def test_delegate_with_lifecycle_preserves_delegate_type_errors(
    non_git_repo: Path,
) -> None:
    def delegate_func(**kwargs):
        raise TypeError("inner delegate bug")

    result = delegate_with_lifecycle(
        [
            {
                "id": "unit-1",
                "description": "Do the work",
                "recommended_agent": "builder",
            }
        ],
        repo_path=non_git_repo,
        delegate_func=delegate_func,
        merge_back=False,
    )

    assert result.dispatch_results["unit-1"] == {"error": "inner delegate bug"}
    assert "inner delegate bug" in result.warnings[0]


def test_failed_predecessor_skips_dependent_unit(non_git_repo: Path) -> None:
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
        repo_path=non_git_repo,
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


def test_failed_explicit_predecessor_skips_dependent_unit(
    non_git_repo: Path,
) -> None:
    calls: list[str] = []

    def delegate_func(*, task: str, **_kwargs):
        unit_id = task.splitlines()[0].removeprefix("Work unit ").removesuffix(":")
        calls.append(unit_id)
        raise RuntimeError("producer failed")

    result = delegate_with_lifecycle(
        [
            {"id": "producer", "description": "Produce the input"},
            {
                "id": "consumer",
                "description": "Consume the input",
                "depends_on": ["producer"],
            },
        ],
        repo_path=non_git_repo,
        delegate_func=delegate_func,
        merge_back=False,
    )

    assert calls == ["producer"]
    assert result.dispatch_results["consumer"]["status"] == "skipped"
    assert result.dispatch_results["consumer"]["blocked_by"] == ["producer"]
    assert result.as_dict()["work_units"][1]["depends_on"] == ["producer"]


def test_unsuccessful_result_skips_dependent_unit(non_git_repo: Path) -> None:
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
        repo_path=non_git_repo,
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


def test_none_worker_result_is_not_completed(non_git_repo: Path) -> None:
    result = delegate_with_lifecycle(
        [{"id": "unit", "description": "Do the work"}],
        repo_path=non_git_repo,
        delegate_func=lambda **_kwargs: None,
        merge_back=False,
    )

    assert "0 completed, 1 failed/not completed" in result.summary


@pytest.mark.parametrize("ambiguous", ["", 0, [], {}, {"status": ""}])
def test_ambiguous_worker_results_are_not_completed(
    non_git_repo: Path,
    ambiguous: object,
) -> None:
    result = delegate_with_lifecycle(
        [{"id": "unit", "description": "Do the work"}],
        repo_path=non_git_repo,
        delegate_func=lambda **_kwargs: ambiguous,
        merge_back=False,
    )

    assert "0 completed, 1 failed/not completed" in result.summary


def test_independent_units_still_dispatch_concurrently(non_git_repo: Path) -> None:
    rendezvous = threading.Barrier(2)

    def delegate_func(*, task: str, **kwargs):
        rendezvous.wait(timeout=2)
        unit_id = task.splitlines()[0].removeprefix("Work unit ").removesuffix(":")
        return {
            "ok": True,
            "task": task,
            "backend": "test",
            "executed_worker_kind": "test-worker",
            "executed_worker_id": f"worker-{unit_id}",
            "native_run_id": f"test:{unit_id}",
        }

    result = delegate_with_lifecycle(
        [
            {"id": "one", "description": "Independent task one"},
            {"id": "two", "description": "Independent task two"},
        ],
        repo_path=non_git_repo,
        delegate_func=delegate_func,
        merge_back=False,
    )

    assert result.batches == [["one", "two"]]
    assert all(payload["ok"] for payload in result.dispatch_results.values())


def test_ready_successor_starts_before_an_unrelated_slow_root_finishes(
    non_git_repo: Path,
) -> None:
    successor_started = threading.Event()
    slow_root_observed_successor = threading.Event()

    def delegate_func(*, task: str, **_kwargs):
        unit_id = task.splitlines()[0].removeprefix("Work unit ").removesuffix(":")
        if unit_id == "slow-root":
            if successor_started.wait(timeout=2):
                slow_root_observed_successor.set()
            return {
                "status": "completed",
                "backend": "test",
                "executed_worker_kind": "test-worker",
                "executed_worker_id": f"worker-{unit_id}",
                "native_run_id": f"test:{unit_id}",
            }
        if unit_id == "successor":
            successor_started.set()
        return {
            "status": "completed",
            "backend": "test",
            "executed_worker_kind": "test-worker",
            "executed_worker_id": f"worker-{unit_id}",
            "native_run_id": f"test:{unit_id}",
        }

    result = delegate_with_lifecycle(
        [
            {"id": "fast-root", "description": "Fast root"},
            {"id": "slow-root", "description": "Independent slow root"},
            {
                "id": "successor",
                "description": "Consumes the fast root",
                "depends_on": ["fast-root"],
            },
        ],
        repo_path=non_git_repo,
        delegate_func=delegate_func,
        max_workers=2,
        merge_back=False,
    )

    assert result.batches == [["fast-root", "slow-root"], ["successor"]]
    assert slow_root_observed_successor.is_set()
    assert all(
        lifecycle_module._result_completed(worker_result)
        for worker_result in result.dispatch_results.values()
    )


def test_failed_unit_recursively_skips_its_dependency_chain(
    non_git_repo: Path,
) -> None:
    called: list[str] = []

    def delegate_func(*, task: str, **_kwargs):
        unit_id = task.splitlines()[0].removeprefix("Work unit ").removesuffix(":")
        called.append(unit_id)
        return {"status": "failed", "error": "root failed"}

    result = delegate_with_lifecycle(
        [
            {"id": "root", "description": "Root"},
            {
                "id": "child",
                "description": "Child",
                "depends_on": ["root"],
            },
            {
                "id": "grandchild",
                "description": "Grandchild",
                "depends_on": ["child"],
            },
        ],
        repo_path=non_git_repo,
        delegate_func=delegate_func,
        merge_back=False,
    )

    assert called == ["root"]
    assert result.dispatch_results["child"]["blocked_by"] == ["root"]
    assert result.dispatch_results["grandchild"]["blocked_by"] == ["child"]


def test_delegate_with_lifecycle_supports_task_only_delegate(
    non_git_repo: Path,
) -> None:
    def delegate_func(*, task: str):
        return {
            "backend": "task-only",
            "task": task,
            "status": "completed",
            "executed_worker_kind": "test-worker",
            "executed_worker_id": "worker-task-only",
            "native_run_id": "task-only:run-1",
        }

    result = delegate_with_lifecycle(
        [{"id": "unit-1", "description": "Do the task"}],
        repo_path=non_git_repo,
        delegate_func=delegate_func,
        merge_back=False,
    )

    assert result.dispatch_results["unit-1"]["backend"] == "task-only"
    assert "Do the task" in result.dispatch_results["unit-1"]["task"]


def test_delegate_with_lifecycle_awaits_async_delegate(non_git_repo: Path) -> None:
    async def delegate_func(*, task: str, **_kwargs):
        await asyncio.sleep(0)
        return {
            "backend": "async",
            "task": task,
            "status": "completed",
            "executed_worker_kind": "test-worker",
            "executed_worker_id": "worker-async",
            "native_run_id": "async:run-1",
        }

    result = delegate_with_lifecycle(
        [{"id": "unit-1", "description": "Do the async task"}],
        repo_path=non_git_repo,
        delegate_func=delegate_func,
        merge_back=False,
    )

    assert result.dispatch_results["unit-1"]["backend"] == "async"
    assert result.warnings == []


def test_delegate_with_lifecycle_accepts_falsey_callable(non_git_repo: Path) -> None:
    class FalseyDelegate:
        def __bool__(self) -> bool:
            return False

        def __call__(self, *, task: str, **_kwargs):
            return {
                "task": task,
                "status": "completed",
                "backend": "falsey-callable",
                "executed_worker_kind": "test-worker",
                "executed_worker_id": "worker-falsey",
                "native_run_id": "falsey-callable:run-1",
            }

    result = delegate_with_lifecycle(
        [{"id": "unit-1", "description": "Use the provided callable"}],
        repo_path=non_git_repo,
        delegate_func=FalseyDelegate(),
        merge_back=False,
    )

    assert result.dispatch_results["unit-1"]["status"] == "completed"


def test_delegate_with_lifecycle_supports_legacy_goal_context_delegate(
    non_git_repo: Path,
) -> None:
    def delegate_func(*, goal: str, context: str, recommended_agent: str):
        return {
            "backend": "legacy",
            "goal": goal,
            "context": context,
            "agent": recommended_agent,
            "status": "completed",
            "executed_worker_kind": "test-worker",
            "executed_worker_id": "worker-legacy",
            "native_run_id": "legacy:run-1",
        }

    result = delegate_with_lifecycle(
        [
            {
                "id": "unit-1",
                "description": "Do the legacy task",
                "recommended_agent": "builder",
            }
        ],
        repo_path=non_git_repo,
        delegate_func=delegate_func,
        merge_back=False,
    )

    dispatched = result.dispatch_results["unit-1"]
    assert dispatched["backend"] == "legacy"
    assert dispatched["goal"] == "Do the legacy task"
    assert dispatched["context"] == f"workdir={non_git_repo.resolve()}"
    assert dispatched["agent"] == "builder"


def test_lifecycle_provisions_worktrees_merges_back_and_removes_paths(
    git_integration_root: Path,
) -> None:
    tmp_path = git_integration_root
    repo = tmp_path / "repo"
    _initialize_test_repo(repo)

    def delegate_func(
        *,
        task: str,
        workdir: str | None = None,
        recommended_agent: str | None = None,
        **kwargs,
    ):
        assert workdir is not None
        unit_id = "one" if "one" in task else "two"
        path = Path(workdir) / f"{unit_id}.txt"
        path.write_text(f"{unit_id}\n", encoding="utf-8")
        subprocess.run(["git", "add", path.name], cwd=workdir, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"{unit_id} work"],
            cwd=workdir,
            check=True,
            capture_output=True,
            text=True,
        )
        return {
            "backend": "fake",
            "unit_id": unit_id,
            "status": "completed",
            "executed_worker_kind": "test-worker",
            "executed_worker_id": f"worker-{unit_id}",
            "native_run_id": f"fake:{unit_id}",
        }

    worktree_root = tmp_path / "worktrees"
    result = delegate_with_lifecycle(
        [
            {
                "id": "one",
                "description": "create one.txt",
                "recommended_agent": "agent-a",
            },
            {
                "id": "two",
                "description": "create two.txt",
                "recommended_agent": "agent-b",
            },
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
    assert list(worktree_root.iterdir()) == []


def test_single_git_work_unit_is_always_isolated(git_integration_root: Path) -> None:
    tmp_path = git_integration_root
    repo = tmp_path / "repo"
    _initialize_test_repo(repo)
    observed_workdirs: list[Path] = []

    def delegate_func(*, workdir: str | None = None, **_kwargs):
        assert workdir is not None
        isolated = Path(workdir)
        observed_workdirs.append(isolated)
        assert isolated.resolve() != repo.resolve()
        (isolated / "single.txt").write_text("isolated\n", encoding="utf-8")
        return {
            "status": "completed",
            "backend": "test",
            "executed_worker_kind": "test-worker",
            "executed_worker_id": "worker-single",
            "native_run_id": "test:single",
        }

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


def test_repeated_unit_ids_use_unique_owned_worktrees_and_branches(
    git_integration_root: Path,
) -> None:
    tmp_path = git_integration_root
    repo = tmp_path / "repo"
    _initialize_test_repo(repo)

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


def test_successful_uncommitted_worker_edits_are_committed_and_merged(
    git_integration_root: Path,
) -> None:
    tmp_path = git_integration_root
    repo = tmp_path / "repo"
    _initialize_test_repo(repo)

    def delegate_func(*, task: str, workdir: str | None = None, **_kwargs):
        assert workdir is not None
        unit_id = task.splitlines()[0].removeprefix("Work unit ").removesuffix(":")
        (Path(workdir) / f"{unit_id}.txt").write_text(f"{unit_id}\n", encoding="utf-8")
        return {
            "ok": True,
            "backend": "fake",
            "executed_worker_kind": "test-worker",
            "executed_worker_id": f"worker-{unit_id}",
            "native_run_id": f"fake:{unit_id}",
        }

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


def test_failed_uncommitted_worker_edits_are_preserved(git_integration_root: Path) -> None:
    tmp_path = git_integration_root
    repo = tmp_path / "repo"
    _initialize_test_repo(repo)

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


def test_dependent_worktree_sees_successful_predecessor_commit(
    git_integration_root: Path,
) -> None:
    tmp_path = git_integration_root
    repo = tmp_path / "repo"
    _initialize_test_repo(repo)

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
        return {
            "ok": True,
            "unit_id": unit_id,
            "backend": "fake",
            "executed_worker_kind": "test-worker",
            "executed_worker_id": f"worker-{unit_id}",
            "native_run_id": f"fake:{unit_id}",
        }

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


def test_failed_worktree_branch_is_not_merged_back(git_integration_root: Path) -> None:
    tmp_path = git_integration_root
    repo = tmp_path / "repo"
    _initialize_test_repo(repo)

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
