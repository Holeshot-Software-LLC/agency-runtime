"""Final fail-closed branch coverage for delegation and private path boundaries."""

from __future__ import annotations

import os
import stat
import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import (
    installer_filesystem,
    installer_inventory,
    installer_payloads,
    private_paths,
)
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.delegation import (
    backend_command,
    backend_hosts,
    lifecycle_dispatch,
    lifecycle_git,
    lifecycle_graph,
)
from agency_runtime.core.delegation.lifecycle_types import (
    DependencyGraph,
    WorktreeInfo,
    WorktreePathIdentity,
    WorkUnit,
)
from agency_runtime.core.private_paths import PrivateDirectoryIdentity


def _completed(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["git"], returncode, stdout, stderr)


class _Guard:
    def __init__(self, path: Path, *, current: bool = True) -> None:
        self.path = path
        self.current = current
        self.closed = 0

    def is_current(self) -> bool:
        return self.current

    def close(self) -> None:
        self.closed += 1


class _Api:
    """ctypes-compatible callable whose implementation is supplied by a test."""

    def __init__(self, function: Any) -> None:
        self.function = function
        self.argtypes: Any = None
        self.restype: Any = None

    def __call__(self, *args: Any) -> Any:
        return self.function(*args)


def _identity(
    path: Path, *, guard: Any = None, parent_guard: Any = None
) -> PrivateDirectoryIdentity:
    metadata = os.lstat(path)
    return PrivateDirectoryIdentity(
        path,
        int(metadata.st_dev),
        int(metadata.st_ino),
        guard=guard,
        parent_guard=parent_guard,
    )


def _worktree_info(tmp_path: Path, unit_id: str = "unit") -> WorktreeInfo:
    path = tmp_path / unit_id
    path.mkdir(exist_ok=True)
    return WorktreeInfo(
        unit_id,
        tmp_path,
        path,
        f"agency/{unit_id}",
        "main",
        "a" * 40,
        created=True,
    )


def test_command_availability_accepts_a_legacy_prepared_executable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = backend_command.CommandBackend(name="test", command=["tool"])
    monkeypatch.setattr(
        backend_command.CommandBackend,
        "executable_path",
        lambda _self: "trusted-tool",
    )
    monkeypatch.setattr(backend_command, "prepare_process_argv", lambda argv: list(argv))
    monkeypatch.setattr(backend_command.shutil, "which", lambda _value: "trusted-tool")

    assert backend.availability() == {
        "backend": "test",
        "available": True,
        "executable": "trusted-tool",
        "reason": "",
    }


def test_codex_backend_rejects_a_non_event_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        backend_command.CommandBackend,
        "parse_stdout",
        lambda _self, _stdout: ({"type": "turn.completed"}, {}),
    )

    with pytest.raises(ValueError, match="invalid event stream"):
        backend_hosts.CodexExecBackend().parse_stdout("ignored")


def test_delegate_contract_accepts_an_uninspectable_callable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegate = lambda **_kwargs: {"ok": True}  # noqa: E731
    monkeypatch.setattr(
        lifecycle_dispatch.inspect,
        "signature",
        lambda _func: (_ for _ in ()).throw(TypeError("opaque callable")),
    )

    assert lifecycle_dispatch._validate_delegate_contract(delegate) is delegate
    assert (
        lifecycle_dispatch.result_failure_reason({"cancelled": True})
        == "worker reported cancelled=true"
    )


def test_schedule_records_a_blocked_predecessor_without_submitting(tmp_path: Path) -> None:
    unit = WorkUnit("child", "child", depends_on={"parent"})
    runtime = lifecycle_dispatch._DispatchRuntime(
        func=lambda **_kwargs: {"ok": True},
        executor=SimpleNamespace(submit=lambda *_args: pytest.fail("must not submit")),
        worktrees={},
        predecessors={"child": {"parent"}},
        results={"parent": {"status": "failed"}},
        warnings=[],
        ledger=None,
        call_delegate_func=lambda *_args: {"ok": True},
        result_completed_func=lifecycle_dispatch.result_completed,
        result_failure_reason_func=lifecycle_dispatch.result_failure_reason,
        backend_name_func=lambda *_args: "test",
        merge_predecessors_func=lambda *_args: None,
        commit_worktree_func=lambda *_args: None,
    )

    assert lifecycle_dispatch._schedule_unit(unit, runtime) is None
    assert runtime.results["child"]["blocked_by"] == ["parent"]


def test_skip_descendants_ignores_an_already_terminal_child() -> None:
    runtime = lifecycle_dispatch._DispatchRuntime(
        func=lambda **_kwargs: {"ok": True},
        executor=SimpleNamespace(),
        worktrees={},
        predecessors={},
        results={"child": {"status": "completed"}},
        warnings=[],
        ledger=None,
        call_delegate_func=lambda *_args: {"ok": True},
        result_completed_func=lifecycle_dispatch.result_completed,
        result_failure_reason_func=lifecycle_dispatch.result_failure_reason,
        backend_name_func=lambda *_args: "test",
        merge_predecessors_func=lambda *_args: None,
        commit_worktree_func=lambda *_args: None,
    )
    graph = DependencyGraph(edges={"parent": {"child"}, "child": set()})

    lifecycle_dispatch._skip_descendants(
        "parent",
        graph=graph,
        by_id={"child": WorkUnit("child", "child")},
        runtime=runtime,
    )

    assert runtime.results == {"child": {"status": "completed"}}


def _dispatch(
    units: list[WorkUnit],
    graph: DependencyGraph,
) -> tuple[dict[str, Any], list[list[str]], list[str]]:
    return lifecycle_dispatch.dispatch_work_units(
        units,
        graph,
        {},
        delegate_func=lambda **_kwargs: {
            "ok": True,
            "status": "completed",
            "executed_worker_kind": "test-worker",
            "executed_worker_id": "test-worker-1",
            "native_run_id": "test-run-1",
        },
        ledger=None,
        max_workers=2,
        resolve_delegate_func=lambda func: func,
        call_delegate_func=lifecycle_dispatch.call_delegate,
        result_completed_func=lifecycle_dispatch.result_completed,
        result_failure_reason_func=lifecycle_dispatch.result_failure_reason,
        backend_name_func=lifecycle_dispatch.backend_name,
        merge_predecessors_func=lambda *_args: None,
        commit_worktree_func=lambda *_args: None,
    )


def test_dispatch_skips_a_ready_unit_already_terminalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    units = [WorkUnit("a", "a"), WorkUnit("b", "b")]
    graph = DependencyGraph(edges={"a": set(), "b": set()})
    original = lifecycle_dispatch._schedule_unit

    def schedule(unit: WorkUnit, runtime: lifecycle_dispatch._DispatchRuntime):
        if unit.id == "a":
            runtime.results["b"] = {"status": "skipped"}
        return original(unit, runtime)

    monkeypatch.setattr(lifecycle_dispatch, "_schedule_unit", schedule)

    results, _batches, _warnings = _dispatch(units, graph)

    assert set(results) == {"a", "b"}


def test_dispatch_waits_for_every_predecessor_before_readying_child() -> None:
    units = [
        WorkUnit("a", "a"),
        WorkUnit("b", "b"),
        WorkUnit("child", "child", depends_on={"a", "b"}),
    ]
    graph = DependencyGraph(
        edges={"a": {"child"}, "b": {"child"}, "child": set()},
    )

    results, _batches, _warnings = _dispatch(units, graph)

    assert all(lifecycle_dispatch.result_completed(result) for result in results.values())


def test_graph_item_forms_and_every_unit_bound(tmp_path: Path) -> None:
    assert lifecycle_graph._items({"units": ("one", "two")}) == ["one", "two"]
    assert lifecycle_graph._items("one") == ["one"]

    valid = WorkUnit("unit", "description")
    cases: list[tuple[WorkUnit, type[Exception], str]] = [
        (replace(valid, description=""), ValueError, "description"),
        (
            replace(valid, description="x" * (lifecycle_graph.MAX_DESCRIPTION_CHARS + 1)),
            ValueError,
            "description exceeds",
        ),
        (replace(valid, description="bad\0value"), ValueError, "NUL"),
        (replace(valid, recommended_agent=1), TypeError, "recommended_agent"),  # type: ignore[arg-type]
        (
            replace(
                valid,
                recommended_agent="x" * (lifecycle_graph.MAX_RECOMMENDED_AGENT_CHARS + 1),
            ),
            ValueError,
            "recommended_agent exceeds",
        ),
        (replace(valid, recommended_agent="bad\nagent"), ValueError, "control"),
        (
            replace(
                valid,
                files={Path(str(index)) for index in range(lifecycle_graph.MAX_FILES_PER_UNIT + 1)},
            ),
            ValueError,
            "files cannot",
        ),
        (
            replace(valid, files={Path("x" * (lifecycle_graph.MAX_PATH_CHARS + 1))}),
            ValueError,
            "file path exceeds",
        ),
        (
            replace(
                valid,
                depends_on={
                    str(index) for index in range(lifecycle_graph.MAX_DEPENDENCIES_PER_UNIT + 1)
                },
            ),
            ValueError,
            "depends_on cannot",
        ),
    ]
    for unit, error, match in cases:
        with pytest.raises(error, match=match):
            lifecycle_graph._validate_unit_bounds(unit)

    with pytest.raises(ValueError, match="file path exceeds"):
        lifecycle_graph._explicit_files({"files": ["x" * (lifecycle_graph.MAX_PATH_CHARS + 1)]})
    with pytest.raises(ValueError, match="recommended_agent exceeds"):
        lifecycle_graph.normalize_work_units(
            [{"description": "task", "recommended_agent": "x" * 257}],
            None,
            fallback_repo=None,
            git_root=lambda _path: None,
        )
    with pytest.raises(ValueError, match="repo_path exceeds"):
        lifecycle_graph.normalize_work_units(
            [{"description": "task", "repo_path": "x" * 4097}],
            None,
            fallback_repo=None,
            git_root=lambda _path: None,
        )
    with pytest.raises(ValueError, match="repo_path exceeds"):
        lifecycle_graph._repo_fallback("x" * 4097, tmp_path)


def test_normalization_rechecks_the_aggregate_file_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lifecycle_graph, "MAX_FILES_PER_UNIT", 1)
    monkeypatch.setattr(
        lifecycle_graph,
        "_explicit_files",
        lambda _item: {Path("one.py"), Path("two.py")},
    )

    with pytest.raises(ValueError, match="files cannot"):
        lifecycle_graph.normalize_work_units(
            [{"description": "task", "repo_path": str(tmp_path)}],
            None,
            fallback_repo=None,
            git_root=lambda _path: tmp_path,
        )


@pytest.mark.parametrize(
    ("guard_current", "parent_current", "expected"),
    (
        (False, True, "worktree root was replaced"),
        (True, False, "task root was replaced"),
    ),
)
def test_private_worktree_receipt_revalidates_both_guards(
    tmp_path: Path,
    guard_current: bool,
    parent_current: bool,
    expected: str,
) -> None:
    path = tmp_path / "root"
    path.mkdir()
    identity = _identity(
        path,
        guard=_Guard(path, current=guard_current),
        parent_guard=_Guard(tmp_path, current=parent_current),
    )

    with pytest.raises(PermissionError, match=expected):
        lifecycle_git._require_private_identity(identity)


def test_private_worktree_receipt_rejects_missing_or_replaced_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "root"
    path.mkdir()
    unguarded = _identity(path)
    monkeypatch.setattr(lifecycle_git, "validate_private_directory", lambda value: value)
    monkeypatch.setattr(lifecycle_git, "_directory_identity_is_current", lambda _value: False)
    with pytest.raises(PermissionError, match="private delegation worktree root was replaced"):
        lifecycle_git._require_private_identity(unguarded)

    incomplete = replace(unguarded, guard=_Guard(path))
    with pytest.raises(PermissionError, match="receipt is incomplete"):
        lifecycle_git._require_private_identity(incomplete)


def test_private_run_root_rolls_back_and_notes_cleanup_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    child = root / "run-token"
    child.mkdir(parents=True)
    identity = _identity(child)
    monkeypatch.setattr(
        lifecycle_git, "allocate_private_directory", lambda *_args, **_kwargs: identity
    )
    monkeypatch.setattr(
        lifecycle_git,
        "_require_directory_identity",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("replaced")),
    )
    monkeypatch.setattr(
        lifecycle_git,
        "remove_private_directory",
        lambda _identity: (_ for _ in ()).throw(OSError("cleanup refused")),
    )

    with pytest.raises(PermissionError, match="replaced") as caught:
        lifecycle_git._allocate_private_run_root(root)

    assert any("rollback failed" in note for note in caught.value.__notes__)


def test_host_run_root_requires_a_complete_parent_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    guard = _Guard(root)
    identity = _identity(root, guard=guard)
    monkeypatch.setattr(
        lifecycle_git,
        "allocate_host_private_directory",
        lambda **_kwargs: identity,
    )

    with pytest.raises(PermissionError, match="receipt is incomplete"):
        lifecycle_git._allocate_host_run_root(fallback_error=PermissionError("primary"))

    assert guard.closed == 1


def test_host_run_root_carries_both_identity_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    parent_guard = _Guard(tmp_path)
    guard = _Guard(root)
    identity = _identity(root, guard=guard, parent_guard=parent_guard)
    monkeypatch.setattr(
        lifecycle_git,
        "allocate_host_private_directory",
        lambda **_kwargs: identity,
    )

    allocation = lifecycle_git._allocate_host_run_root(fallback_error=OSError("primary"))

    assert allocation.private_identity is identity
    assert allocation.parent_identity.path == tmp_path
    assert "host-attested" in allocation.warning


def test_repository_run_root_refuses_long_path_and_mkdir_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lifecycle_git, "config_namespace_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(lifecycle_git, "_require_directory_identity", lambda *_a, **_k: None)
    monkeypatch.setattr(lifecycle_git, "_windows_path_error", lambda _path: "too long")
    with pytest.raises(OSError, match="too long"):
        lifecycle_git._allocate_repository_run_root(
            tmp_path,
            fallback_error=PermissionError("primary"),
        )

    monkeypatch.setattr(lifecycle_git, "_windows_path_error", lambda _path: None)
    monkeypatch.setattr(
        lifecycle_git.os,
        "mkdir",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("denied")),
    )
    with pytest.raises(PermissionError, match="could not allocate"):
        lifecycle_git._allocate_repository_run_root(
            tmp_path,
            fallback_error=PermissionError("primary"),
        )


def test_repository_run_root_notes_rollback_failure_and_exhaustion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lifecycle_git, "config_namespace_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(lifecycle_git, "restrict_path_permissions", lambda *_a, **_k: None)
    monkeypatch.setattr(lifecycle_git, "storage_parent_is_trusted", lambda *_a, **_k: False)
    monkeypatch.setattr(lifecycle_git, "_windows_path_error", lambda _path: None)
    original_rmdir = lifecycle_git.os.rmdir
    monkeypatch.setattr(
        lifecycle_git.os,
        "rmdir",
        lambda _path: (_ for _ in ()).throw(OSError("rollback denied")),
    )
    with pytest.raises(PermissionError, match="not private") as caught:
        lifecycle_git._allocate_repository_run_root(
            tmp_path,
            fallback_error=PermissionError("primary"),
        )
    assert any("rollback failed" in note for note in caught.value.__notes__)

    monkeypatch.setattr(lifecycle_git.os, "rmdir", original_rmdir)
    monkeypatch.setattr(
        lifecycle_git.os,
        "mkdir",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileExistsError()),
    )
    with pytest.raises(RuntimeError, match="unique repository-scoped"):
        lifecycle_git._allocate_repository_run_root(
            tmp_path,
            fallback_error=PermissionError("primary"),
        )


def test_repo_scoped_component_and_status_exclusion(tmp_path: Path) -> None:
    root = tmp_path / ".agency-worktrees-token"
    root.mkdir()
    allocation = lifecycle_git._AllocatedRunRoot(
        root,
        "token",
        lifecycle_git._capture_directory_identity(root),
        lifecycle_git._capture_directory_identity(tmp_path),
        repo_scoped=True,
    )
    unit = WorkUnit("unit", "unit")

    assert lifecycle_git._worktree_component(allocation, unit).startswith("w-")
    assert lifecycle_git._base_status_args(tmp_path, allocation)[-1] == (
        ":(exclude).agency-worktrees-token"
    )


def test_git_invocation_refuses_missing_or_repository_local_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        lifecycle_git,
        "resolve_executable_path",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError("missing")),
    )
    assert (
        "trusted executable is unavailable"
        in lifecycle_git._invoke_git(
            tmp_path,
            ["status"],
            timeout=1,
        ).stderr
    )

    executable = tmp_path / "git.exe"
    executable.touch()
    monkeypatch.setattr(
        lifecycle_git,
        "resolve_executable_path",
        lambda *_args, **_kwargs: str(executable),
    )
    assert (
        "inside the target repository"
        in lifecycle_git._invoke_git(
            tmp_path,
            ["status"],
            timeout=1,
        ).stderr
    )


def test_grouping_ignores_units_without_a_repository(tmp_path: Path) -> None:
    grouped, unavailable = lifecycle_git._group_units_by_repository(
        [WorkUnit("unit", "task")],
        worktree_root=tmp_path,
        git_root_func=lambda _path: tmp_path,
    )
    assert grouped == {}
    assert unavailable == {}


def test_provision_unit_without_allocation_records_creation(tmp_path: Path) -> None:
    info = lifecycle_git._provision_unit_worktree(
        WorkUnit("unit", "task", repo_path=tmp_path),
        repo=tmp_path,
        run_root=tmp_path / "runs",
        run_token="token",
        base="main",
        base_sha="a" * 40,
        dirty=False,
        warnings=[],
        run_git_func=lambda *_args, **_kwargs: _completed(),
    )

    assert info.created is True


def test_provision_rejects_an_impossible_missing_allocation_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unit = WorkUnit("unit", "task", repo_path=tmp_path)
    monkeypatch.setattr(
        lifecycle_git,
        "_group_units_by_repository",
        lambda *_args, **_kwargs: ({tmp_path: [unit]}, {}),
    )
    monkeypatch.setattr(lifecycle_git, "_allocate_private_run_root", lambda _root: None)

    with pytest.raises(RuntimeError, match="returned no receipt"):
        lifecycle_git.provision_worktrees(
            [unit],
            base_branch=None,
            worktree_root=Path.home() / ".agency-runtime" / "worktrees",
            run_git_func=lambda *_args, **_kwargs: _completed(),
            git_root_func=lambda _path: tmp_path,
            current_branch_func=lambda _repo: "main",
            head_sha_func=lambda *_args: "a" * 40,
        )


def test_windows_default_allocation_does_not_consult_host_fallback_when_primary_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unit = WorkUnit("unit", "task", repo_path=tmp_path)
    root = tmp_path / "run"
    root.mkdir()
    allocation = lifecycle_git._AllocatedRunRoot(
        root,
        "token",
        lifecycle_git._capture_directory_identity(root),
        lifecycle_git._capture_directory_identity(tmp_path),
    )
    monkeypatch.setattr(lifecycle_git, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        lifecycle_git,
        "_group_units_by_repository",
        lambda *_args, **_kwargs: ({tmp_path: [unit]}, {}),
    )
    monkeypatch.setattr(lifecycle_git, "private_runtime_directory", lambda _name: tmp_path)
    monkeypatch.setattr(lifecycle_git, "_allocate_private_run_root", lambda _root: allocation)
    monkeypatch.setattr(
        lifecycle_git,
        "_allocate_host_run_root",
        lambda **_kwargs: pytest.fail("host fallback must not run"),
    )
    monkeypatch.setattr(
        lifecycle_git,
        "_provision_repository_worktrees",
        lambda *_args, **_kwargs: {
            "unit": WorktreeInfo("unit", tmp_path, root / "unit", "b", "main", "a" * 40)
        },
    )

    result = lifecycle_git.provision_worktrees(
        [unit],
        base_branch=None,
        worktree_root=Path.home() / ".agency-runtime" / "worktrees",
        run_git_func=lambda *_args, **_kwargs: _completed(),
        git_root_func=lambda _path: tmp_path,
        current_branch_func=lambda _repo: "main",
        head_sha_func=lambda *_args: "a" * 40,
    )

    assert "unit" in result


def test_posix_default_allocation_uses_repository_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unit = WorkUnit("unit", "task", repo_path=tmp_path)
    root = tmp_path / "fallback"
    root.mkdir()
    allocation = lifecycle_git._AllocatedRunRoot(
        root,
        "token",
        lifecycle_git._capture_directory_identity(root),
        lifecycle_git._capture_directory_identity(tmp_path),
        repo_scoped=True,
    )
    monkeypatch.setattr(lifecycle_git, "_IS_WINDOWS", False)
    monkeypatch.setattr(
        lifecycle_git,
        "_group_units_by_repository",
        lambda *_args, **_kwargs: ({tmp_path: [unit]}, {}),
    )
    monkeypatch.setattr(
        lifecycle_git,
        "private_runtime_directory",
        lambda _name: (_ for _ in ()).throw(PermissionError("primary")),
    )
    monkeypatch.setattr(
        lifecycle_git,
        "_allocate_repository_run_root",
        lambda *_args, **_kwargs: allocation,
    )
    monkeypatch.setattr(
        lifecycle_git,
        "_provision_repository_worktrees",
        lambda *_args, **_kwargs: {
            "unit": WorktreeInfo("unit", tmp_path, root / "unit", "b", "main", "a" * 40)
        },
    )

    result = lifecycle_git.provision_worktrees(
        [unit],
        base_branch=None,
        worktree_root=Path.home() / ".agency-runtime" / "worktrees",
        run_git_func=lambda *_args, **_kwargs: _completed(),
        git_root_func=lambda _path: tmp_path,
        current_branch_func=lambda _repo: "main",
        head_sha_func=lambda *_args: "a" * 40,
    )

    assert "unit" in result


def test_merge_predecessor_rejects_replaced_target_or_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _worktree_info(tmp_path, "target")
    source = _worktree_info(tmp_path, "source")
    worktrees = {"target": target, "source": source}
    monkeypatch.setattr(
        lifecycle_git,
        "_require_worktree_info_identity",
        lambda _info: (_ for _ in ()).throw(PermissionError("replaced")),
    )
    assert (
        lifecycle_git.merge_predecessor_work(
            "target",
            {"source"},
            worktrees,
            run_git_func=lambda *_args, **_kwargs: pytest.fail("must not run Git"),
        )
        == "replaced"
    )

    calls = 0

    def reject_source(_info: WorktreeInfo) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise PermissionError("source replaced")

    monkeypatch.setattr(lifecycle_git, "_require_worktree_info_identity", reject_source)
    assert "source replaced" in lifecycle_git.merge_predecessor_work(
        "target",
        {"source"},
        worktrees,
        run_git_func=lambda *_args, **_kwargs: pytest.fail("must not run Git"),
    )


@pytest.mark.parametrize("failure_call", (2, 3))
def test_commit_revalidates_identity_before_each_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_call: int,
) -> None:
    info = _worktree_info(tmp_path)
    validations = 0

    def validate(_info: WorktreeInfo) -> None:
        nonlocal validations
        validations += 1
        if validations == failure_call:
            raise PermissionError("replaced")

    monkeypatch.setattr(lifecycle_git, "_require_worktree_info_identity", validate)
    git_calls: list[list[str]] = []

    def run(_path: Path, args: list[str], **_kwargs: Any):
        git_calls.append(args)
        return _completed(stdout=" M state.txt\n")

    assert (
        lifecycle_git.commit_successful_worktree(
            info,
            "unit",
            run_git_func=run,
        )
        == "replaced"
    )
    assert len(git_calls) == failure_call - 1


def test_restore_quarantine_refuses_an_existing_original(
    tmp_path: Path,
) -> None:
    original = tmp_path / "original"
    quarantine = tmp_path / "quarantine"
    original.mkdir()
    quarantine.mkdir()
    parent = lifecycle_git._capture_directory_identity(tmp_path)

    with pytest.raises(PermissionError, match="refusing to restore"):
        lifecycle_git._restore_quarantined_run_root(
            lifecycle_git._capture_directory_identity(quarantine),
            lifecycle_git._capture_directory_identity(original),
            parent,
        )


def test_empty_run_root_quarantine_collision_and_exhaustion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    root_identity = lifecycle_git._capture_directory_identity(root)
    parent_identity = lifecycle_git._capture_directory_identity(tmp_path)
    monkeypatch.setattr(
        lifecycle_git.os,
        "lstat",
        lambda path: (
            (_ for _ in ()).throw(FileNotFoundError())
            if Path(path).name.startswith(".agency-cleanup-")
            else os.stat(path)
        ),
    )
    monkeypatch.setattr(
        lifecycle_git.os,
        "rename",
        lambda *_args: (_ for _ in ()).throw(FileExistsError()),
    )
    with pytest.raises(RuntimeError, match="cleanup quarantine"):
        lifecycle_git._remove_empty_run_root(root_identity, parent_identity)


def test_empty_run_root_returns_false_for_nonempty_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "state").touch()

    assert not lifecycle_git._remove_empty_run_root(
        lifecycle_git._capture_directory_identity(root),
        lifecycle_git._capture_directory_identity(tmp_path),
    )


def test_quarantine_restore_failure_is_noted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    root_identity = lifecycle_git._capture_directory_identity(root)
    parent_identity = lifecycle_git._capture_directory_identity(tmp_path)
    monkeypatch.setattr(
        lifecycle_git,
        "_directory_identity_is_current",
        lambda _identity: True,
    )
    empty_checks = 0

    def inspect_empty(_path: Path) -> bool:
        nonlocal empty_checks
        empty_checks += 1
        if empty_checks == 2:
            raise PermissionError("quarantine changed")
        return True

    monkeypatch.setattr(
        lifecycle_git,
        "_directory_is_empty",
        inspect_empty,
    )
    monkeypatch.setattr(
        lifecycle_git,
        "_restore_quarantined_run_root",
        lambda *_args: (_ for _ in ()).throw(OSError("restore denied")),
    )

    with pytest.raises(PermissionError) as caught:
        lifecycle_git._remove_empty_run_root(root_identity, parent_identity)

    assert any("restore failed" in note for note in caught.value.__notes__)


def test_run_root_cleanup_records_only_matching_units(tmp_path: Path) -> None:
    root = tmp_path / "root"
    other = tmp_path / "other"
    root.mkdir()
    other.mkdir()
    root_identity = lifecycle_git._capture_directory_identity(root)
    parent_identity = lifecycle_git._capture_directory_identity(tmp_path)
    matching = WorktreeInfo(
        "matching",
        tmp_path,
        root / "worktree",
        "b",
        "main",
        "a" * 40,
        run_root_identity=root_identity,
        run_parent_identity=parent_identity,
    )
    nonmatching = WorktreeInfo(
        "other",
        tmp_path,
        other / "worktree",
        "b",
        "main",
        "a" * 40,
        run_root_identity=lifecycle_git._capture_directory_identity(other),
        run_parent_identity=parent_identity,
    )
    records = {
        "matching": lifecycle_git._new_cleanup_record(matching),
        "other": lifecycle_git._new_cleanup_record(nonmatching),
    }

    lifecycle_git._record_run_root_cleanup_error(
        root,
        {"matching": matching, "other": nonmatching},
        records,
        PermissionError("replaced"),
    )

    assert records["matching"]["errors"]
    assert records["other"]["errors"] == []


def test_legacy_empty_run_root_is_removed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = tmp_path / "run-legacy"
    candidate.mkdir()
    info = WorktreeInfo(
        "unit",
        tmp_path,
        candidate / "worktree",
        "b",
        "main",
        "a" * 40,
        created=True,
    )
    monkeypatch.setattr(lifecycle_git, "validate_private_directory", lambda path: path)

    lifecycle_git._remove_empty_run_roots({"unit": info})

    assert not candidate.exists()


def test_installer_residual_fail_closed_branches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target"
    stage = tmp_path / "stage"
    stage.mkdir()
    identity = _identity(stage)
    monkeypatch.setattr(
        installer_filesystem, "ensure_private_directory", lambda path, **_kwargs: path
    )
    monkeypatch.setattr(
        installer_filesystem, "allocate_private_directory", lambda *_a, **_k: identity
    )
    monkeypatch.setattr(
        installer_filesystem.os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(OSError("replace failed")),
    )
    removed: list[PrivateDirectoryIdentity] = []
    monkeypatch.setattr(installer_filesystem, "remove_private_directory", removed.append)
    with pytest.raises(OSError, match="replace failed"):
        installer_filesystem.atomic_install_tree(
            target,
            {"file.txt": "content"},
            host="codex",
            dry_run=False,
            home_dir=tmp_path,
        )
    assert removed == [identity]

    assert (
        installer_inventory._sanitize_host_version(
            SimpleNamespace(ok=True, stdout="no version", stderr="")
        )
        is None
    )
    state = SimpleNamespace(
        host="codex",
        executable="codex",
        host_version_supported=True,
        registered=True,
        enabled=True,
        loaded=True,
        staged=False,
        current_root=False,
        stale_config=False,
    )
    assert installer_inventory._maturity(state) == "runtime-verified"


def test_bundle_files_rebinds_a_normalized_config_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = AgencyConfig(config_path="relative.yaml")
    monkeypatch.setattr(installer_payloads, "_bound_config_path", lambda _cfg: "absolute.yaml")
    monkeypatch.setattr(installer_payloads, "_hook_timeout_seconds", lambda observed: 7)
    monkeypatch.setattr(
        installer_payloads, "_codex_hooks", lambda timeout, path: {"hooks": (timeout, path)}
    )
    monkeypatch.setattr(installer_payloads, "_mcp_config", lambda path="": {"path": path})
    monkeypatch.setattr(installer_payloads, "_agency_control_skill", lambda host: host)
    monkeypatch.setattr(
        installer_payloads,
        "build_codex_bundle",
        lambda **kwargs: ({"hooks": str(kwargs["hooks"])}, "digest"),
    )

    files, digest = installer_payloads.bundle_files("codex", cfg)

    assert "absolute.yaml" in files["hooks"]
    assert digest == "digest"


def test_dispatch_ignores_a_child_terminalized_while_parent_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    units = [WorkUnit("parent", "parent"), WorkUnit("child", "child")]
    graph = DependencyGraph(edges={"parent": {"child"}, "child": set()})
    original = lifecycle_dispatch._schedule_unit

    def schedule(unit: WorkUnit, runtime: lifecycle_dispatch._DispatchRuntime):
        if unit.id == "parent":
            runtime.results["child"] = {"status": "skipped"}
        return original(unit, runtime)

    monkeypatch.setattr(lifecycle_dispatch, "_schedule_unit", schedule)
    results, _batches, _warnings = _dispatch(units, graph)
    assert results["child"]["status"] == "skipped"


def test_complete_private_worktree_guard_receipt_is_accepted(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    lifecycle_git._require_private_identity(
        _identity(root, guard=_Guard(root), parent_guard=_Guard(tmp_path))
    )


def test_host_run_root_missing_both_guards_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(
        lifecycle_git,
        "allocate_host_private_directory",
        lambda **_kwargs: _identity(root),
    )
    with pytest.raises(PermissionError, match="receipt is incomplete"):
        lifecycle_git._allocate_host_run_root(fallback_error=PermissionError("primary"))


def test_repository_allocation_failure_before_identity_skips_unsafe_rollback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lifecycle_git, "config_namespace_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(lifecycle_git, "_windows_path_error", lambda _path: None)
    captures = 0
    original_capture = lifecycle_git._capture_directory_identity

    def capture(path: Path) -> WorktreePathIdentity:
        nonlocal captures
        captures += 1
        if captures == 2:
            raise PermissionError("identity unavailable")
        return original_capture(path)

    monkeypatch.setattr(lifecycle_git, "_capture_directory_identity", capture)
    with pytest.raises(PermissionError, match="identity unavailable"):
        lifecycle_git._allocate_repository_run_root(
            tmp_path,
            fallback_error=PermissionError("primary"),
        )
    assert len(list(tmp_path.glob(".agency-worktrees-*"))) == 1


def test_run_root_quarantine_retries_a_preexisting_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (tmp_path / ".agency-cleanup-collision").mkdir()
    tokens = iter(("collision", "available"))
    monkeypatch.setattr(lifecycle_git.secrets, "token_hex", lambda _size: next(tokens))
    assert lifecycle_git._remove_empty_run_root(
        lifecycle_git._capture_directory_identity(root),
        lifecycle_git._capture_directory_identity(tmp_path),
    )


def test_run_root_cleanup_without_record_and_legacy_rmdir_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    info = WorktreeInfo(
        "unit",
        tmp_path,
        root / "worktree",
        "b",
        "main",
        "a" * 40,
        run_root_identity=lifecycle_git._capture_directory_identity(root),
        run_parent_identity=lifecycle_git._capture_directory_identity(tmp_path),
    )
    lifecycle_git._record_run_root_cleanup_error(
        root,
        {"unit": info},
        {},
        PermissionError("replaced"),
    )

    legacy = tmp_path / "run-legacy-busy"
    legacy.mkdir()
    (legacy / "retained").touch()
    legacy_info = WorktreeInfo(
        "legacy",
        tmp_path,
        legacy / "worktree",
        "b",
        "main",
        "a" * 40,
        created=True,
    )
    monkeypatch.setattr(lifecycle_git, "validate_private_directory", lambda path: path)
    lifecycle_git._remove_empty_run_roots({"legacy": legacy_info})
    assert legacy.exists()


def test_installer_failed_stage_before_creation_skips_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = PrivateDirectoryIdentity(tmp_path / "missing-stage", 1, 1)
    monkeypatch.setattr(installer_filesystem, "ensure_private_directory", lambda path, **_k: path)
    monkeypatch.setattr(
        installer_filesystem, "allocate_private_directory", lambda *_a, **_k: identity
    )
    monkeypatch.setattr(
        installer_filesystem,
        "_safe_relative",
        lambda _path: (_ for _ in ()).throw(ValueError("invalid generated path")),
    )
    monkeypatch.setattr(
        installer_filesystem,
        "remove_private_directory",
        lambda _identity: pytest.fail("missing stage must not be removed"),
    )
    with pytest.raises(ValueError, match="invalid generated path"):
        installer_filesystem.atomic_install_tree(
            tmp_path / "target",
            {"bad": "content"},
            host="codex",
            dry_run=False,
            home_dir=tmp_path,
        )


def test_host_authority_registry_discards_only_the_exact_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    identity = _identity(root)
    other = replace(identity)
    discarded: list[Path] = []
    monkeypatch.setattr(private_paths, "discard_private_path_authority", discarded.append)
    private_paths._HOST_AUTHORITIES[root] = identity
    private_paths._discard_host_authority(other)
    assert private_paths._HOST_AUTHORITIES[root] is identity
    private_paths._discard_host_authority(identity)
    assert root not in private_paths._HOST_AUTHORITIES
    assert discarded == [root, root]


def test_host_authority_lookup_skips_outside_and_discards_stale_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = tmp_path / "outside"
    stale = tmp_path / "stale"
    current = tmp_path / "current"
    for path in (outside, stale, current):
        path.mkdir()
    identities = [_identity(path) for path in (outside, stale, current)]
    private_paths._HOST_AUTHORITIES.clear()
    private_paths._HOST_AUTHORITIES.update({item.path: item for item in identities})
    monkeypatch.setattr(
        private_paths,
        "_identity_is_current",
        lambda item: item.path == current,
    )
    monkeypatch.setattr(private_paths, "discard_private_path_authority", lambda _path: None)
    assert private_paths._host_authority_for(current / "child") is identities[2]
    assert private_paths._host_authority_for(stale / "child") is None
    assert stale not in private_paths._HOST_AUTHORITIES
    private_paths._HOST_AUTHORITIES.clear()


def test_host_descendant_privacy_rejects_escape_missing_file_and_public_acl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    child = root / "child"
    root.mkdir()
    child.mkdir()
    authority = _identity(root)
    assert not private_paths._host_descendant_is_private(tmp_path / "escape", authority)
    assert not private_paths._host_descendant_is_private(root / "missing", authority)

    original_lstat = private_paths.os.lstat
    monkeypatch.setattr(
        private_paths.os,
        "lstat",
        lambda path: (
            SimpleNamespace(st_mode=stat.S_IFREG) if Path(path) == child else original_lstat(path)
        ),
    )
    monkeypatch.setattr(private_paths, "metadata_is_link_or_reparse_point", lambda _meta: False)
    assert not private_paths._host_descendant_is_private(child, authority)

    monkeypatch.setattr(private_paths.os, "lstat", original_lstat)
    monkeypatch.setattr(
        private_paths,
        "windows_directory_prevents_untrusted_writes",
        lambda *_args, **_kwargs: False,
    )
    assert not private_paths._host_descendant_is_private(child, authority)


def test_host_private_descendant_creates_and_restricts_each_component(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    authority = _identity(root)
    restricted: list[Path] = []
    monkeypatch.setattr(private_paths, "_identity_is_current", lambda _identity: True)
    monkeypatch.setattr(private_paths, "_host_descendant_is_private", lambda *_args: True)
    monkeypatch.setattr(private_paths, "_restrict_private_directory", restricted.append)
    target = root / "one" / "two"
    assert (
        private_paths._ensure_host_private_descendant(
            target,
            authority,
            product_owned=True,
        )
        == target
    )
    assert restricted == [root / "one", target]

    monkeypatch.setattr(private_paths, "_identity_is_current", lambda _identity: False)
    with pytest.raises(PermissionError, match="ancestor changed"):
        private_paths._ensure_host_private_descendant(
            root / "three",
            authority,
            product_owned=False,
        )


def test_codex_thread_identity_requires_a_canonical_uuid() -> None:
    with pytest.raises(PermissionError, match="identity is unavailable"):
        private_paths._codex_thread_id("not-a-uuid")
    canonical = "019f4c7c-64ea-7650-a414-2680b0efabc6"
    with pytest.raises(PermissionError, match="not canonical"):
        private_paths._codex_thread_id(canonical.upper())


def test_codex_parent_pinning_rejects_wrong_missing_untrusted_and_stale_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    visualizations = tmp_path / "visualizations"
    visualizations.mkdir()
    assert (
        private_paths._pin_codex_host_private_parent(
            visualizations / "too" / "shallow",
            visualizations,
        )
        is None
    )

    missing = visualizations / "2026" / "07" / "16" / "019f4c7c-64ea-7650-a414-2680b0efabc6"
    assert private_paths._pin_codex_host_private_parent(missing, visualizations) is None
    missing.mkdir(parents=True)
    monkeypatch.setattr(private_paths, "validate_private_directory", lambda path: path)
    monkeypatch.setattr(
        private_paths,
        "windows_restricted_host_boundary_is_trusted",
        lambda _path: False,
    )
    assert private_paths._pin_codex_host_private_parent(missing, visualizations) is None

    monkeypatch.setattr(
        private_paths,
        "windows_restricted_host_boundary_is_trusted",
        lambda _path: True,
    )
    stale = _Guard(missing, current=False)
    monkeypatch.setattr(
        private_paths,
        "open_windows_directory_guard",
        lambda *_args, **_kwargs: stale,
    )
    assert private_paths._pin_codex_host_private_parent(missing, visualizations) is None
    assert stale.closed == 1


def test_close_directory_guards_closes_every_receipt(tmp_path: Path) -> None:
    guards = [_Guard(tmp_path), _Guard(tmp_path)]
    private_paths._close_directory_guards(guards)
    assert [guard.closed for guard in guards] == [1, 1]


def test_unique_codex_parent_accepts_one_rejects_many_and_bounds_search(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _Guard(tmp_path / "first")
    second = _Guard(tmp_path / "second")
    source = SimpleNamespace(glob=lambda _pattern: iter((Path("one"),)))
    monkeypatch.setattr(private_paths, "_pin_codex_host_private_parent", lambda *_args: first)
    assert private_paths._unique_codex_host_private_parent(source) is first

    source = SimpleNamespace(glob=lambda _pattern: iter((Path("one"), Path("two"))))
    guards = iter((first, second))
    monkeypatch.setattr(
        private_paths, "_pin_codex_host_private_parent", lambda *_args: next(guards)
    )
    with pytest.raises(PermissionError, match="ambiguous"):
        private_paths._unique_codex_host_private_parent(source)
    assert first.closed >= 1 and second.closed == 1

    source = SimpleNamespace(glob=lambda _pattern: (Path(str(index)) for index in range(4097)))
    monkeypatch.setattr(private_paths, "_pin_codex_host_private_parent", lambda *_args: None)
    with pytest.raises(PermissionError, match="exceeded its bound"):
        private_paths._unique_codex_host_private_parent(source)


def test_codex_host_private_parent_attestation_and_exact_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    thread_id = "019f4c7c-64ea-7650-a414-2680b0efabc6"
    environment = {"CODEX_SHELL": "1", "CODEX_THREAD_ID": thread_id}
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", False)
    with pytest.raises(PermissionError, match="only on Windows"):
        private_paths._codex_host_private_parent(home_dir=tmp_path, environment=environment)

    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    with pytest.raises(PermissionError, match="not attested"):
        private_paths._codex_host_private_parent(
            home_dir=tmp_path,
            environment={"CODEX_THREAD_ID": thread_id},
        )

    exact = tmp_path / ".codex" / "visualizations" / "2026" / "07" / "16" / thread_id
    exact.mkdir(parents=True)
    guard = _Guard(exact)
    monkeypatch.setattr(private_paths, "_pin_codex_host_private_parent", lambda *_args: None)
    with pytest.raises(PermissionError, match="exact boundary is not trusted"):
        private_paths._codex_host_private_parent(home_dir=tmp_path, environment=environment)

    monkeypatch.setattr(private_paths, "_pin_codex_host_private_parent", lambda *_args: guard)
    assert (
        private_paths._codex_host_private_parent(
            home_dir=tmp_path,
            environment=environment,
        )
        is guard
    )


def test_codex_host_private_parent_rejects_ambiguous_exact_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    thread_id = "019f4c7c-64ea-7650-a414-2680b0efabc6"
    for day in ("15", "16"):
        (tmp_path / ".codex" / "visualizations" / "2026" / "07" / day / thread_id).mkdir(
            parents=True
        )
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    with pytest.raises(PermissionError, match="exact identity is ambiguous"):
        private_paths._codex_host_private_parent(
            home_dir=tmp_path,
            environment={"CODEX_SHELL": "1", "CODEX_THREAD_ID": thread_id},
        )


def test_codex_host_private_parent_uses_bounded_nested_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guard = _Guard(tmp_path)
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        private_paths,
        "_unique_codex_host_private_parent",
        lambda _visualizations: guard,
    )
    assert (
        private_paths._codex_host_private_parent(
            home_dir=tmp_path,
            environment={
                "CODEX_SHELL": "1",
                "CODEX_THREAD_ID": "019f4c7c-64ea-7650-a414-2680b0efabc6",
            },
        )
        is guard
    )


def test_ensure_private_directory_uses_only_a_registered_host_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "root" / "child"
    root = tmp_path / "root"
    root.mkdir()
    authority = _identity(root)
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(private_paths, "assert_storage_parent_chain", lambda *_a, **_k: None)
    monkeypatch.setattr(private_paths, "nearest_existing_storage_parent", lambda _path: root)
    monkeypatch.setattr(
        private_paths,
        "storage_creation_boundary_is_trusted",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(private_paths, "_host_authority_for", lambda _path: authority)
    monkeypatch.setattr(
        private_paths,
        "_ensure_host_private_descendant",
        lambda path, _authority, **_kwargs: path,
    )
    assert private_paths.ensure_private_directory(target) == target
    monkeypatch.setattr(private_paths, "_host_authority_for", lambda _path: None)
    with pytest.raises(PermissionError, match="untrusted creation boundary"):
        private_paths.ensure_private_directory(target)


def test_private_directory_creation_and_repair_postconditions_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target"
    monkeypatch.setattr(private_paths, "assert_storage_parent_chain", lambda *_a, **_k: None)
    monkeypatch.setattr(private_paths, "nearest_existing_storage_parent", lambda _path: tmp_path)
    monkeypatch.setattr(
        private_paths,
        "storage_creation_boundary_is_trusted",
        lambda *_a, **_k: True,
    )
    monkeypatch.setattr(private_paths, "create_private_storage_parent", lambda *_a, **_k: None)
    monkeypatch.setattr(private_paths, "storage_parent_is_trusted", lambda *_a, **_k: False)
    with pytest.raises(PermissionError, match="is not trusted"):
        private_paths.ensure_private_directory(target)

    inspections = iter((True, False))
    monkeypatch.setattr(
        private_paths,
        "storage_parent_is_trusted",
        lambda *_a, **_k: next(inspections),
    )
    monkeypatch.setattr(private_paths, "_restrict_private_directory", lambda _path: None)
    with pytest.raises(PermissionError, match="unsafe after permission repair"):
        private_paths.ensure_private_directory(target)


def test_validate_private_directory_accepts_attested_host_descendant_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    target = root / "child"
    target.mkdir(parents=True)
    authority = _identity(root)
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(private_paths, "assert_storage_parent_chain", lambda *_a, **_k: None)
    monkeypatch.setattr(private_paths, "storage_parent_is_trusted", lambda *_a, **_k: False)
    monkeypatch.setattr(private_paths, "_host_authority_for", lambda _path: authority)
    monkeypatch.setattr(private_paths, "_host_descendant_is_private", lambda *_a: True)
    assert private_paths.validate_private_directory(target) == target
    monkeypatch.setattr(private_paths, "_host_descendant_is_private", lambda *_a: False)
    with pytest.raises(PermissionError, match="is not trusted"):
        private_paths.validate_private_directory(target)


def test_private_runtime_root_windows_fallback_and_failure_modes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(private_paths.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", False)
    monkeypatch.setattr(
        private_paths,
        "ensure_private_directory",
        lambda _path: (_ for _ in ()).throw(PermissionError("primary")),
    )
    with pytest.raises(PermissionError, match="primary"):
        private_paths.private_runtime_root()

    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(private_paths, "current_process_user_sid", lambda **_kwargs: None)
    monkeypatch.setattr(
        private_paths, "current_process_restricted_sids", lambda **_kwargs: frozenset()
    )
    with pytest.raises(PermissionError, match="cannot identify"):
        private_paths.private_runtime_root()

    calls = 0

    def ensure(path: Path) -> Path:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PermissionError("primary")
        return path

    monkeypatch.setattr(private_paths, "ensure_private_directory", ensure)
    monkeypatch.setattr(
        private_paths,
        "current_process_user_sid",
        lambda **_kwargs: "S-1-5-21-1001",
    )
    monkeypatch.setattr(
        private_paths,
        "current_process_restricted_sids",
        lambda **_kwargs: frozenset({"S-1-5-5-1-2"}),
    )
    monkeypatch.setattr(private_paths.tempfile, "gettempdir", lambda: str(tmp_path))
    assert private_paths.private_runtime_root().parent == tmp_path


def test_capture_private_identity_rejects_unusable_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        private_paths.os,
        "lstat",
        lambda _path: SimpleNamespace(st_mode=stat.S_IFREG, st_ino=0, st_dev=1),
    )
    monkeypatch.setattr(private_paths, "metadata_is_link_or_reparse_point", lambda _meta: False)
    with pytest.raises(PermissionError, match="identity is unavailable"):
        private_paths._capture_directory_identity(tmp_path)


def test_allocate_private_directory_retries_rolls_back_and_exhausts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "worker-collision").mkdir()
    tokens = iter(("collision", "available"))
    monkeypatch.setattr(private_paths, "validate_private_directory", lambda path: path)
    monkeypatch.setattr(private_paths.secrets, "token_hex", lambda _size: next(tokens))
    monkeypatch.setattr(private_paths, "ensure_private_directory", lambda path: path)
    allocated = private_paths.allocate_private_directory(root, prefix="worker")
    assert allocated.path.name == "worker-available"

    monkeypatch.setattr(private_paths.secrets, "token_hex", lambda _size: "rollback")
    monkeypatch.setattr(
        private_paths,
        "ensure_private_directory",
        lambda _path: (_ for _ in ()).throw(PermissionError("unsafe")),
    )
    with pytest.raises(PermissionError, match="unsafe"):
        private_paths.allocate_private_directory(root, prefix="worker")
    assert not (root / "worker-rollback").exists()

    monkeypatch.setattr(
        private_paths.os,
        "mkdir",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileExistsError()),
    )
    with pytest.raises(RuntimeError, match="could not allocate"):
        private_paths.allocate_private_directory(root, prefix="worker")


def test_allocate_host_private_directory_success_stale_exception_and_exhaustion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = _Guard(tmp_path)
    environment = {"CODEX_THREAD_ID": "019f4c7c-64ea-7650-a414-2680b0efabc6"}
    monkeypatch.setattr(private_paths, "_codex_host_private_parent", lambda **_kwargs: parent)

    def create(candidate: Path, **_kwargs: Any) -> _Guard:
        candidate.mkdir()
        return _Guard(candidate)

    monkeypatch.setattr(private_paths, "create_windows_logon_private_directory", create)
    monkeypatch.setattr(private_paths, "_identity_is_current", lambda _identity: True)
    monkeypatch.setattr(private_paths, "_register_host_authority", lambda _identity: None)
    identity = private_paths.allocate_host_private_directory(
        prefix="worker",
        environment=environment,
    )
    assert identity.guard is not None and identity.parent_guard is parent

    stale_parent = _Guard(tmp_path)
    stale_guard: _Guard | None = None
    monkeypatch.setattr(
        private_paths,
        "_codex_host_private_parent",
        lambda **_kwargs: stale_parent,
    )

    def create_stale(candidate: Path, **_kwargs: Any) -> _Guard:
        nonlocal stale_guard
        candidate.mkdir()
        stale_guard = _Guard(candidate)
        return stale_guard

    monkeypatch.setattr(private_paths, "create_windows_logon_private_directory", create_stale)
    monkeypatch.setattr(private_paths, "_identity_is_current", lambda _identity: False)
    with pytest.raises(PermissionError, match="changed during allocation"):
        private_paths.allocate_host_private_directory(prefix="stale", environment=environment)
    assert stale_guard is not None and stale_guard.closed == 1 and stale_parent.closed == 1

    exhausted_parent = _Guard(tmp_path)
    monkeypatch.setattr(
        private_paths,
        "_codex_host_private_parent",
        lambda **_kwargs: exhausted_parent,
    )
    monkeypatch.setattr(
        private_paths,
        "create_windows_logon_private_directory",
        lambda *_args, **_kwargs: None,
    )
    with pytest.raises(RuntimeError, match="could not allocate a unique"):
        private_paths.allocate_host_private_directory(prefix="none", environment=environment)
    assert exhausted_parent.closed == 1

    failed_parent = _Guard(tmp_path)
    monkeypatch.setattr(
        private_paths,
        "_codex_host_private_parent",
        lambda **_kwargs: failed_parent,
    )
    monkeypatch.setattr(
        private_paths,
        "create_windows_logon_private_directory",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("denied")),
    )
    with pytest.raises(OSError, match="denied"):
        private_paths.allocate_host_private_directory(prefix="failed", environment=environment)
    assert failed_parent.closed == 1


def test_private_identity_and_guard_cleanup_failure_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert not private_paths._filesystem_identity_is_current(
        PrivateDirectoryIdentity(tmp_path / "missing", 1, 1)
    )
    root = tmp_path / "root"
    root.mkdir()
    guard = _Guard(root)
    parent = _Guard(tmp_path)
    private_paths._HOST_AUTHORITIES[root] = _identity(root)
    monkeypatch.setattr(private_paths, "discard_private_path_authority", lambda _path: None)
    private_paths._close_identity_guards(_identity(root, guard=guard, parent_guard=parent))
    assert guard.closed == 1 and parent.closed == 1
    private_paths._HOST_AUTHORITIES.clear()


def test_private_cleanup_parent_rejects_incomplete_unseal_and_parent_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(private_paths, "discard_private_path_authority", lambda _path: None)
    with pytest.raises(PermissionError, match="receipt is incomplete"):
        private_paths._private_cleanup_parent(_identity(root, guard=_Guard(root)))

    guard = _Guard(root)
    parent = _Guard(tmp_path)
    monkeypatch.setattr(
        private_paths,
        "prepare_windows_logon_private_directory_cleanup",
        lambda _guard: False,
    )
    with pytest.raises(PermissionError, match="refusing to unseal"):
        private_paths._private_cleanup_parent(_identity(root, guard=guard, parent_guard=parent))

    guard = _Guard(root)
    parent = _Guard(tmp_path, current=False)
    monkeypatch.setattr(
        private_paths,
        "prepare_windows_logon_private_directory_cleanup",
        lambda _guard: True,
    )
    with pytest.raises(PermissionError, match="changed Codex task root"):
        private_paths._private_cleanup_parent(_identity(root, guard=guard, parent_guard=parent))

    guard = _Guard(root)
    parent = _Guard(tmp_path)
    assert private_paths._private_cleanup_parent(
        _identity(root, guard=guard, parent_guard=parent)
    ) == (tmp_path, True)


def test_quarantine_private_directory_retries_rejects_replacement_and_exhausts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    identity = _identity(root)
    attempts = 0
    original_rename = private_paths.os.rename

    def collide_once(source: Path, destination: Path) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise FileExistsError()
        original_rename(source, destination)

    monkeypatch.setattr(private_paths.os, "rename", collide_once)
    assert private_paths._quarantine_private_directory(identity, tmp_path).path.exists()

    replacement = tmp_path / "replacement"
    replacement.mkdir()
    replacement_identity = _identity(replacement)
    monkeypatch.setattr(
        private_paths.os,
        "rename",
        lambda *_args: (_ for _ in ()).throw(OSError("denied")),
    )
    monkeypatch.setattr(private_paths, "_filesystem_identity_is_current", lambda _identity: False)
    with pytest.raises(PermissionError, match="replaced"):
        private_paths._quarantine_private_directory(replacement_identity, tmp_path)

    monkeypatch.setattr(private_paths, "_filesystem_identity_is_current", lambda _identity: True)
    with pytest.raises(OSError, match="denied"):
        private_paths._quarantine_private_directory(replacement_identity, tmp_path)

    monkeypatch.setattr(
        private_paths.os,
        "rename",
        lambda *_args: (_ for _ in ()).throw(FileExistsError()),
    )
    with pytest.raises(private_paths.PrivateDirectoryCleanupError, match="cleanup quarantine"):
        private_paths._quarantine_private_directory(replacement_identity, tmp_path)


def test_cleanup_identity_host_guard_uses_filesystem_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = PrivateDirectoryIdentity(Path("identity"), 1, 1)
    monkeypatch.setattr(private_paths, "_filesystem_identity_is_current", lambda _identity: True)
    monkeypatch.setattr(private_paths, "_identity_is_current", lambda _identity: False)
    assert private_paths._cleanup_identity_is_current(identity, host_guarded=True)
    assert not private_paths._cleanup_identity_is_current(identity, host_guarded=False)


def test_restore_cleanup_quarantine_notes_unsafe_and_failed_restores(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_path = tmp_path / "original"
    quarantine_path = tmp_path / "quarantine"
    quarantine_path.mkdir()
    original = PrivateDirectoryIdentity(original_path, 1, 1)
    quarantine = _identity(quarantine_path)
    error = OSError("cleanup failed")
    monkeypatch.setattr(
        private_paths,
        "validate_private_directory",
        lambda _path: (_ for _ in ()).throw(PermissionError("parent unsafe")),
    )
    private_paths._restore_cleanup_quarantine(
        original,
        quarantine,
        host_guarded=False,
        error=error,
    )
    assert any("could not be restored safely" in note for note in error.__notes__)

    error = OSError("cleanup failed")
    monkeypatch.setattr(private_paths, "validate_private_directory", lambda path: path)
    monkeypatch.setattr(
        private_paths.os,
        "rename",
        lambda *_args: (_ for _ in ()).throw(OSError("restore denied")),
    )
    private_paths._restore_cleanup_quarantine(
        original,
        quarantine,
        host_guarded=False,
        error=error,
    )
    assert any("restore failed" in note for note in error.__notes__)


def test_private_temporary_directory_windows_fallback_and_posix_refusal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        private_paths,
        "private_runtime_directory",
        lambda _category: (_ for _ in ()).throw(PermissionError("primary")),
    )
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", False)
    with (
        pytest.raises(PermissionError, match="primary"),
        private_paths.private_temporary_directory(prefix="worker"),
    ):
        pass

    root = tmp_path / "host"
    root.mkdir()
    identity = _identity(root)
    removed: list[PrivateDirectoryIdentity] = []
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        private_paths,
        "allocate_host_private_directory",
        lambda **_kwargs: identity,
    )
    monkeypatch.setattr(private_paths, "remove_private_directory", removed.append)
    with private_paths.private_temporary_directory(prefix="worker") as path:
        assert path == root
    assert removed == [identity]
