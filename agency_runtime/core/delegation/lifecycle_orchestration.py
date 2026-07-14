"""Lifecycle result aggregation and one-shot orchestration."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from agency_runtime.core.delegation.ledger import DelegationLedger
from agency_runtime.core.delegation.lifecycle_dispatch import DelegateFunc
from agency_runtime.core.delegation.lifecycle_types import (
    DependencyGraph,
    LifecycleResult,
    WorktreeInfo,
    WorkUnit,
)

ResultCompletedFunc = Callable[[Any], bool]


def aggregate_results(
    units: Sequence[WorkUnit],
    graph: DependencyGraph,
    batches: Sequence[Sequence[str]],
    worktrees: Mapping[str, WorktreeInfo],
    dispatch_results: Mapping[str, Any],
    cleanup_results: Mapping[str, Any],
    warnings: Sequence[str],
    errors: Sequence[str],
    *,
    result_completed_func: ResultCompletedFunc,
    missing: object,
) -> str:
    """Build a compact lifecycle summary."""
    del cleanup_results  # Reserved in the public aggregation contract.
    completed = sum(
        1 for unit in units if result_completed_func(dispatch_results.get(unit.id, missing))
    )
    not_completed = len(units) - completed
    rendered_batches = ", ".join("[" + ", ".join(batch) + "]" for batch in batches)
    lines = [
        f"Delegation lifecycle completed for {len(units)} work unit(s).",
        f"Execution batches: {rendered_batches or 'none'}.",
        f"Worker results: {completed} completed, {not_completed} failed/not completed.",
    ]
    if graph.reasons:
        dependencies = "; ".join(
            f"{source}->{target}: {reason}"
            for (source, target), reason in sorted(graph.reasons.items())
        )
        lines.append(f"Dependencies: {dependencies}")
    if worktrees:
        rendered_worktrees = ", ".join(
            f"{unit_id}={'created' if info.created else 'failed'}"
            for unit_id, info in sorted(worktrees.items())
        )
        lines.append(f"Worktrees: {rendered_worktrees}")
    if warnings:
        lines.append("Warnings: " + "; ".join(warnings))
    if errors:
        lines.append("Errors: " + "; ".join(errors))
    return "\n".join(lines)


def _failed_provisioning_info(
    unit: WorkUnit,
    worktree_root: Path,
    reason: str,
) -> WorktreeInfo:
    if unit.repo_path is None:
        raise ValueError("failed provisioning records require a repository path")
    info = WorktreeInfo(
        unit.id,
        unit.repo_path,
        worktree_root / f"unavailable-{unit.id}",
        "",
        "",
        "",
    )
    info.errors.append(reason)
    return info


def _cleanup_failure_results(worktrees: Mapping[str, WorktreeInfo], reason: str) -> dict[str, Any]:
    return {
        unit_id: {
            "branch": info.branch,
            "worktree": str(info.path),
            "merged": False,
            "removed": False,
            "preserved": info.created,
            "branch_deleted": False,
            "conflict": False,
            "warnings": [
                *info.warnings,
                "worktree preserved because lifecycle cleanup failed",
            ],
            "errors": [*info.errors, reason],
        }
        for unit_id, info in worktrees.items()
    }


def delegate_with_lifecycle(
    work_units: Any,
    repo_path: str | Path | None,
    base_branch: str | None,
    *,
    delegate_func: DelegateFunc | None,
    worktree_root: Path,
    merge_back: bool,
    ledger: DelegationLedger | None,
    max_workers: int,
    missing: object,
    normalize_func: Callable[..., list[WorkUnit]],
    graph_func: Callable[[Sequence[WorkUnit]], DependencyGraph],
    provision_func: Callable[..., dict[str, WorktreeInfo]],
    dispatch_func: Callable[
        ...,
        tuple[dict[str, Any], list[list[str]], list[str]],
    ],
    cleanup_func: Callable[..., dict[str, Any]],
    aggregate_func: Callable[..., str],
    result_completed_func: ResultCompletedFunc,
) -> LifecycleResult:
    """Run normalization, isolation, dispatch, merge, cleanup, and aggregation."""
    units = normalize_func(work_units, repo_path=repo_path)
    graph = graph_func(units)
    warnings: list[str] = []
    errors: list[str] = []
    if ledger:
        for unit in units:
            ledger.suggest(unit.id, unit.recommended_agent)

    try:
        worktrees = provision_func(
            units,
            base_branch=base_branch,
            worktree_root=worktree_root,
        )
    except Exception as exc:
        reason = f"worktree provisioning failed: {type(exc).__name__}: {exc}"
        errors.append(reason)
        worktrees = {
            unit.id: _failed_provisioning_info(unit, worktree_root, reason)
            for unit in units
            if unit.repo_path is not None
        }

    try:
        dispatch_results, batches, dispatch_warnings = dispatch_func(
            units,
            graph,
            worktrees,
            delegate_func=delegate_func,
            ledger=ledger,
            max_workers=max_workers,
        )
        warnings.extend(dispatch_warnings)
    except Exception as exc:
        dispatch_results = {}
        batches = graph.topological_batches() if graph.edges else []
        errors.append(f"dispatch failed: {exc}")
        if ledger:
            for unit in units:
                ledger.update(
                    unit.id,
                    status="failed",
                    recommended_agent=unit.recommended_agent,
                    error=str(exc),
                )

    completed_unit_ids = {
        unit.id for unit in units if result_completed_func(dispatch_results.get(unit.id, missing))
    }
    try:
        cleanup_results = (
            cleanup_func(
                worktrees,
                merge_back=merge_back,
                merge_unit_ids=completed_unit_ids,
            )
            if worktrees
            else {}
        )
    except Exception as exc:
        reason = f"worktree cleanup failed: {type(exc).__name__}: {exc}"
        errors.append(reason)
        cleanup_results = _cleanup_failure_results(worktrees, reason)

    summary = aggregate_func(
        units,
        graph,
        batches,
        worktrees,
        dispatch_results,
        cleanup_results,
        warnings,
        errors,
    )
    return LifecycleResult(
        work_units=units,
        dependency_graph=graph,
        batches=batches,
        worktrees=worktrees,
        dispatch_results=dispatch_results,
        cleanup_results=cleanup_results,
        warnings=warnings,
        errors=errors,
        summary=summary,
        ledger=ledger,
    )


__all__ = ["aggregate_results", "delegate_with_lifecycle"]
