"""Public compatibility facade for the dependency-aware delegation lifecycle."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from agency_runtime.core.delegation import lifecycle_dispatch as _dispatch
from agency_runtime.core.delegation import lifecycle_git as _git
from agency_runtime.core.delegation import lifecycle_graph as _graph
from agency_runtime.core.delegation import lifecycle_orchestration as _orchestration
from agency_runtime.core.delegation.ledger import DelegationLedger
from agency_runtime.core.delegation.lifecycle_dispatch import DelegateFunc
from agency_runtime.core.delegation.lifecycle_types import (
    DependencyGraph,
    LifecycleResult,
    WorktreeInfo,
    WorkUnit,
)

DEFAULT_WORKTREE_ROOT = Path("~") / ".agency-runtime" / "worktrees"
DEFAULT_MAX_WORKERS = min(8, max(1, os.cpu_count() or 4))
_MISSING = _dispatch.MISSING


def _run_git(
    repo: Path, args: Sequence[str], *, timeout: int = 120
) -> subprocess.CompletedProcess[str]:
    """Invocation-time Git seam retained for integrations and tests."""
    return _git.run_git(repo, args, timeout=timeout)


def _git_root(path: Path) -> Path | None:
    """Invocation-time repository discovery seam."""
    return _git.git_root(path)


def _current_branch(repo: Path) -> str | None:
    return _git.current_branch(repo, run_git_func=_run_git)


def _head_sha(repo: Path, ref: str = "HEAD") -> str:
    return _git.head_sha(repo, ref, run_git_func=_run_git)


def _safe(value: str) -> str:
    return _graph.safe_unit_id(value)


def _validate_unique_unit_ids(units: Sequence[WorkUnit]) -> None:
    _graph.validate_unique_unit_ids(units)


def _worktree_root(value: str | Path | None) -> Path:
    if value is None or Path(value) == DEFAULT_WORKTREE_ROOT:
        return Path.home() / ".agency-runtime" / "worktrees"
    return Path(value)


def normalize_work_units(
    work_units: Any,
    repo_path: str | Path | None = None,
    *,
    fallback_repo: Path | None = None,
) -> list[WorkUnit]:
    """Normalize strings and mappings into stable work units."""
    return _graph.normalize_work_units(
        work_units,
        repo_path,
        fallback_repo=fallback_repo,
        git_root=_git_root,
    )


def build_dependency_graph(units: Sequence[WorkUnit]) -> DependencyGraph:
    """Build and validate explicit and inferred dependencies."""
    return _graph.build_dependency_graph(units)


def provision_worktrees(
    units: Sequence[WorkUnit],
    *,
    base_branch: str | None = None,
    worktree_root: Path | None = None,
) -> dict[str, WorktreeInfo]:
    """Provision isolated Git worktrees without hiding invocation-time seams."""
    return _git.provision_worktrees(
        units,
        base_branch=base_branch,
        worktree_root=_worktree_root(worktree_root),
        run_git_func=_run_git,
        git_root_func=_git_root,
        current_branch_func=_current_branch,
        head_sha_func=_head_sha,
    )


def _resolve_delegate_func(delegate_func: DelegateFunc | None) -> DelegateFunc:
    return _dispatch.resolve_delegate_func(delegate_func)


def _prepare_delegate_func(delegate_func: DelegateFunc | None) -> DelegateFunc:
    return _dispatch.prepare_delegate_func(
        delegate_func,
        resolve_func=_resolve_delegate_func,
    )


def _validate_max_workers(max_workers: int) -> None:
    _dispatch.validate_max_workers(max_workers)


def _call_delegate(func: DelegateFunc, unit: WorkUnit, workdir: Path | None) -> Any:
    return _dispatch.call_delegate(func, unit, workdir)


def _signature_accepts(signature: Any, *args: Any, **kwargs: Any) -> bool:
    return _dispatch.signature_accepts(signature, *args, **kwargs)


def _backend(result: Any, func: DelegateFunc) -> str:
    return _dispatch.backend_name(result, func)


def _result_completed(result: Any = _MISSING) -> bool:
    return _dispatch.result_completed(result)


def _result_failure_reason(result: Any = _MISSING) -> str:
    return _dispatch.result_failure_reason(result)


def _merge_predecessor_work(
    unit_id: str,
    predecessor_ids: set[str],
    worktrees: Mapping[str, WorktreeInfo],
) -> str | None:
    return _git.merge_predecessor_work(
        unit_id,
        predecessor_ids,
        worktrees,
        run_git_func=_run_git,
    )


def _commit_successful_worktree(info: WorktreeInfo, unit_id: str) -> str | None:
    return _git.commit_successful_worktree(
        info,
        unit_id,
        run_git_func=_run_git,
    )


def dispatch_work_units(
    units: Sequence[WorkUnit],
    graph: DependencyGraph,
    worktrees: Mapping[str, WorktreeInfo],
    *,
    delegate_func: DelegateFunc | None = None,
    ledger: DelegationLedger | None = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> tuple[dict[str, Any], list[list[str]], list[str]]:
    """Dispatch ready units with bounded parallelism and prerequisite gating."""
    from agency_runtime.core.runtime_control import master_enabled

    if not master_enabled():
        return {}, [], []
    return _dispatch.dispatch_work_units(
        units,
        graph,
        worktrees,
        delegate_func=delegate_func,
        ledger=ledger,
        max_workers=max_workers,
        resolve_delegate_func=_resolve_delegate_func,
        call_delegate_func=_call_delegate,
        result_completed_func=_result_completed,
        result_failure_reason_func=_result_failure_reason,
        backend_name_func=_backend,
        merge_predecessors_func=_merge_predecessor_work,
        commit_worktree_func=_commit_successful_worktree,
    )


def cleanup_worktrees(
    worktrees: Mapping[str, WorktreeInfo],
    *,
    merge_back: bool = True,
    create_pr_on_conflict: bool = False,
    merge_unit_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Merge successful branches and safely remove clean worktrees."""
    return _git.cleanup_worktrees(
        worktrees,
        merge_back=merge_back,
        create_pr_on_conflict=create_pr_on_conflict,
        merge_unit_ids=merge_unit_ids,
        run_git_func=_run_git,
        current_branch_func=_current_branch,
        head_sha_func=_head_sha,
    )


def aggregate_results(
    units: Sequence[WorkUnit],
    graph: DependencyGraph,
    batches: Sequence[Sequence[str]],
    worktrees: Mapping[str, WorktreeInfo],
    dispatch_results: Mapping[str, Any],
    cleanup_results: Mapping[str, Any],
    warnings: Sequence[str],
    errors: Sequence[str],
) -> str:
    """Build the stable human-readable lifecycle summary."""
    return _orchestration.aggregate_results(
        units,
        graph,
        batches,
        worktrees,
        dispatch_results,
        cleanup_results,
        warnings,
        errors,
        result_completed_func=_result_completed,
        missing=_MISSING,
    )


def delegate_with_lifecycle(
    work_units: Any,
    repo_path: str | Path | None = None,
    base_branch: str | None = None,
    *,
    delegate_func: DelegateFunc | None = None,
    worktree_root: str | Path | None = None,
    merge_back: bool = True,
    ledger: DelegationLedger | None = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> LifecycleResult:
    """Run the one-shot normalize, isolate, dispatch, merge, and cleanup API."""
    from agency_runtime.core.runtime_control import master_enabled

    if not master_enabled():
        message = "Agency Runtime is globally disabled; delegation lifecycle was bypassed."
        return LifecycleResult(
            work_units=[],
            dependency_graph=DependencyGraph(),
            batches=[],
            worktrees={},
            dispatch_results={},
            cleanup_results={},
            warnings=[message],
            errors=[],
            summary=message,
            ledger=ledger,
            runtime_enabled=False,
            bypassed=True,
        )
    _validate_max_workers(max_workers)
    units = normalize_work_units(work_units, repo_path=repo_path)
    graph = build_dependency_graph(units)
    prepared_delegate = _prepare_delegate_func(delegate_func) if units else delegate_func

    def normalized_units(
        _work_units: Any,
        repo_path: str | Path | None = None,
    ) -> list[WorkUnit]:
        del _work_units, repo_path
        return units

    def validated_graph(_units: Sequence[WorkUnit]) -> DependencyGraph:
        del _units
        return graph

    return _orchestration.delegate_with_lifecycle(
        units,
        repo_path,
        base_branch,
        delegate_func=prepared_delegate,
        worktree_root=_worktree_root(worktree_root),
        merge_back=merge_back,
        ledger=ledger,
        max_workers=max_workers,
        missing=_MISSING,
        normalize_func=normalized_units,
        graph_func=validated_graph,
        provision_func=provision_worktrees,
        dispatch_func=dispatch_work_units,
        cleanup_func=cleanup_worktrees,
        aggregate_func=aggregate_results,
        result_completed_func=_result_completed,
    )


__all__ = [
    "DEFAULT_MAX_WORKERS",
    "DEFAULT_WORKTREE_ROOT",
    "DelegateFunc",
    "DependencyGraph",
    "LifecycleResult",
    "WorkUnit",
    "WorktreeInfo",
    "aggregate_results",
    "build_dependency_graph",
    "cleanup_worktrees",
    "delegate_with_lifecycle",
    "dispatch_work_units",
    "normalize_work_units",
    "provision_worktrees",
]
