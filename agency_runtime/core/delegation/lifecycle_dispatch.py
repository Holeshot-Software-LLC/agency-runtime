"""Bounded dependency-aware dispatch for delegated work units."""

from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from agency_runtime.core.delegation.ledger import DelegationLedger
from agency_runtime.core.delegation.lifecycle_graph import validate_unique_unit_ids
from agency_runtime.core.delegation.lifecycle_types import (
    DependencyGraph,
    WorktreeInfo,
    WorkUnit,
)

DelegateFunc = Callable[..., Any]
MISSING = object()

_NOT_COMPLETED_RESULT_STATUSES = {
    "blocked",
    "cancelled",
    "canceled",
    "error",
    "failed",
    "failure",
    "incomplete",
    "not_completed",
    "partial",
    "pending",
    "queued",
    "running",
    "skipped",
    "started",
    "suggested",
    "timed_out",
    "timeout",
}
_COMPLETED_RESULT_STATUSES = {
    "completed",
    "delegated",
    "done",
    "ok",
    "succeeded",
    "success",
}


class MergePredecessorsFunc(Protocol):
    def __call__(
        self,
        unit_id: str,
        predecessor_ids: set[str],
        worktrees: Mapping[str, WorktreeInfo],
    ) -> str | None: ...


class CommitWorktreeFunc(Protocol):
    def __call__(self, info: WorktreeInfo, unit_id: str) -> str | None: ...


ResultCompletedFunc = Callable[[Any], bool]
ResultFailureReasonFunc = Callable[[Any], str]
ResolveDelegateFunc = Callable[[DelegateFunc | None], DelegateFunc]
CallDelegateFunc = Callable[[DelegateFunc, WorkUnit, Path | None], Any]
BackendNameFunc = Callable[[Any, DelegateFunc], str]


def resolve_delegate_func(delegate_func: DelegateFunc | None) -> DelegateFunc:
    """Resolve a provided callable or the first available runtime backend."""
    if delegate_func is not None:
        return delegate_func
    from agency_runtime.core.delegation.backends import get_delegate_func

    return get_delegate_func()


async def _await_result(awaitable: Awaitable[Any]) -> Any:
    return await awaitable


def _invoke_delegate(func: DelegateFunc, *args: Any, **kwargs: Any) -> Any:
    result = func(*args, **kwargs)
    if inspect.isawaitable(result):
        # Delegates execute in executor threads, so no caller event loop is blocked
        # or nested. This also closes un-awaited coroutine leaks from async backends.
        return asyncio.run(_await_result(result))
    return result


def call_delegate(func: DelegateFunc, unit: WorkUnit, workdir: Path | None) -> Any:
    """Invoke modern, legacy, task-only, or positional delegate contracts."""
    target_workdir = workdir or unit.repo_path or Path.cwd()
    task = (
        f"Work unit {unit.id}:\n{unit.description}\n\n"
        f"Workdir: {target_workdir}\n"
        "When this is an isolated git worktree, leave every intended file change "
        "in that worktree before reporting success; Agency Runtime will create a "
        "bounded integration commit if needed."
    )
    kwargs = {
        "task": task,
        "workdir": str(target_workdir),
        "recommended_agent": unit.recommended_agent,
    }
    legacy_kwargs = {
        "goal": unit.description,
        "context": f"workdir={kwargs['workdir']}",
        "recommended_agent": unit.recommended_agent,
    }
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return _invoke_delegate(func, **kwargs)
    if signature_accepts(signature, **kwargs):
        return _invoke_delegate(func, **kwargs)
    if signature_accepts(signature, **legacy_kwargs):
        return _invoke_delegate(func, **legacy_kwargs)
    if signature_accepts(signature, task=task):
        return _invoke_delegate(func, task=task)
    return _invoke_delegate(func, task)


def signature_accepts(signature: inspect.Signature, *args: Any, **kwargs: Any) -> bool:
    """Return whether arguments bind without executing the delegate."""
    try:
        signature.bind(*args, **kwargs)
    except TypeError:
        return False
    return True


def backend_name(result: Any, func: DelegateFunc) -> str:
    """Extract the backend evidence name without assuming a mapping result."""
    if isinstance(result, Mapping) and result.get("backend"):
        return str(result["backend"])
    return str(getattr(func, "backend_name", "callable"))


def _normalized_status(result: Mapping[Any, Any]) -> str:
    return str(result.get("status") or "").strip().lower().replace("-", "_").replace(" ", "_")


def result_completed(result: Any = MISSING) -> bool:
    """Return whether a worker produced an affirmative completion result."""
    if result is MISSING or result is None or result is False:
        return False
    if not isinstance(result, Mapping):
        if isinstance(result, (str, bytes, list, tuple)):
            return bool(result)
        return False
    if result.get("error"):
        return False
    if any(result.get(flag) is False for flag in ("ok", "success", "completed", "delegated")):
        return False
    for code_key in ("exit_code", "returncode"):
        code = result.get(code_key)
        if code is not None and code != 0:
            return False
    if result.get("timed_out") is True:
        return False
    status = _normalized_status(result)
    if status in _NOT_COMPLETED_RESULT_STATUSES:
        return False
    if status in _COMPLETED_RESULT_STATUSES:
        return True
    if any(result.get(flag) is True for flag in ("ok", "success", "completed", "delegated")):
        return True
    output = result.get("output")
    return isinstance(output, (str, bytes, list, tuple, dict)) and bool(output)


def result_failure_reason(result: Any = MISSING) -> str:
    """Extract a stable reason for a missing or unsuccessful worker result."""
    if result is MISSING:
        return "no dispatch result was recorded"
    if isinstance(result, Mapping):
        for key in ("error", "skip_reason", "message"):
            value = result.get(key)
            if value:
                return str(value)
        for flag in ("ok", "success", "completed", "delegated"):
            if result.get(flag) is False:
                return f"worker reported {flag}=false"
        for code_key in ("exit_code", "returncode"):
            code = result.get(code_key)
            if code is not None and code != 0:
                return f"worker reported {code_key}={code}"
        if result.get("timed_out") is True:
            return "worker timed out"
        status = str(result.get("status") or "").strip()
        if status:
            return f"worker reported status {status!r}"
    return "worker did not report successful completion"


def _validate_graph_nodes(units: Sequence[WorkUnit], graph: DependencyGraph) -> dict[str, WorkUnit]:
    validate_unique_unit_ids(units)
    by_id = {unit.id: unit for unit in units}
    graph_ids = set(graph.edges)
    for successors in graph.edges.values():
        graph_ids.update(successors)
    if graph_ids != set(by_id):
        missing = sorted(set(by_id) - graph_ids)
        extra = sorted(graph_ids - set(by_id))
        raise ValueError(
            f"dependency graph nodes must match work units (missing={missing}, extra={extra})"
        )
    return by_id


def _record_skip(
    unit: WorkUnit,
    *,
    reason: str,
    blocked_by: list[str],
    results: dict[str, Any],
    warnings: list[str],
    ledger: DelegationLedger | None,
) -> None:
    results[unit.id] = {
        "status": "skipped",
        "skip_reason": reason,
        "blocked_by": blocked_by,
    }
    warnings.append(f"delegate for {unit.id} skipped: {reason}")
    if ledger:
        ledger.update(
            unit.id,
            status="skipped",
            recommended_agent=unit.recommended_agent,
            skip_reason=reason,
        )


def _record_isolation_failure(
    unit: WorkUnit,
    info: WorktreeInfo,
    *,
    results: dict[str, Any],
    warnings: list[str],
    ledger: DelegationLedger | None,
) -> None:
    detail = "; ".join(info.errors)
    reason = "isolated worktree was not created"
    if detail:
        reason = f"{reason}: {detail}"
    results[unit.id] = {"error": reason, "status": "failed"}
    warnings.append(f"delegate for {unit.id} failed: {reason}")
    if ledger:
        ledger.update(
            unit.id,
            status="failed",
            recommended_agent=unit.recommended_agent,
            error=reason,
        )


def _record_dispatch_result(
    unit: WorkUnit,
    result: Any,
    *,
    worktrees: Mapping[str, WorktreeInfo],
    func: DelegateFunc,
    results: dict[str, Any],
    warnings: list[str],
    ledger: DelegationLedger | None,
    result_completed_func: ResultCompletedFunc,
    result_failure_reason_func: ResultFailureReasonFunc,
    backend_name_func: BackendNameFunc,
    commit_worktree_func: CommitWorktreeFunc,
) -> None:
    results[unit.id] = result
    backend = backend_name_func(result, func)
    if not result_completed_func(result):
        reason = result_failure_reason_func(result)
        warnings.append(f"delegate for {unit.id} failed: {reason}")
        if ledger:
            ledger.update(
                unit.id,
                status="failed",
                backend=backend,
                recommended_agent=unit.recommended_agent,
                error=reason,
            )
        return

    info = worktrees.get(unit.id)
    commit_error = (
        commit_worktree_func(info, unit.id) if info is not None and info.created else None
    )
    if commit_error:
        reason = f"could not preserve successful worker changes: {commit_error}"
        results[unit.id] = {
            "status": "failed",
            "error": reason,
            "worker_result": result,
        }
        warnings.append(f"delegate for {unit.id} failed: {reason}")
        if ledger:
            ledger.update(
                unit.id,
                status="failed",
                backend=backend,
                recommended_agent=unit.recommended_agent,
                error=reason,
            )
        return
    if ledger:
        ledger.update(
            unit.id,
            status="completed",
            backend=backend,
            recommended_agent=unit.recommended_agent,
        )


@dataclass(slots=True)
class _DispatchRuntime:
    func: DelegateFunc
    executor: concurrent.futures.ThreadPoolExecutor
    worktrees: Mapping[str, WorktreeInfo]
    predecessors: Mapping[str, set[str]]
    results: dict[str, Any]
    warnings: list[str]
    ledger: DelegationLedger | None
    call_delegate_func: CallDelegateFunc
    result_completed_func: ResultCompletedFunc
    result_failure_reason_func: ResultFailureReasonFunc
    backend_name_func: BackendNameFunc
    merge_predecessors_func: MergePredecessorsFunc
    commit_worktree_func: CommitWorktreeFunc


def _blocked_predecessors(unit_id: str, runtime: _DispatchRuntime) -> list[str]:
    return sorted(
        predecessor_id
        for predecessor_id in runtime.predecessors.get(unit_id, set())
        if not runtime.result_completed_func(runtime.results.get(predecessor_id, MISSING))
    )


def _predecessor_merge_error(
    unit_id: str,
    runtime: _DispatchRuntime,
) -> str | None:
    try:
        return runtime.merge_predecessors_func(
            unit_id,
            runtime.predecessors.get(unit_id, set()),
            runtime.worktrees,
        )
    except Exception as exc:
        return f"could not apply predecessor work: {type(exc).__name__}: {exc}"


def _record_predecessor_merge_failure(
    unit: WorkUnit,
    error: str,
    runtime: _DispatchRuntime,
) -> None:
    _record_skip(
        unit,
        reason=error,
        blocked_by=sorted(runtime.predecessors.get(unit.id, set())),
        results=runtime.results,
        warnings=runtime.warnings,
        ledger=runtime.ledger,
    )
    runtime.results[unit.id]["error"] = error
    if runtime.ledger:
        runtime.ledger.update(
            unit.id,
            status="skipped",
            recommended_agent=unit.recommended_agent,
            skip_reason=error,
            error=error,
        )


def _schedule_unit(
    unit: WorkUnit,
    runtime: _DispatchRuntime,
) -> concurrent.futures.Future[Any] | None:
    blocked_by = _blocked_predecessors(unit.id, runtime)
    if blocked_by:
        reason = f"dependency did not complete successfully: {', '.join(blocked_by)}"
        _record_skip(
            unit,
            reason=reason,
            blocked_by=blocked_by,
            results=runtime.results,
            warnings=runtime.warnings,
            ledger=runtime.ledger,
        )
        return None

    info = runtime.worktrees.get(unit.id)
    if info is not None and not info.created:
        _record_isolation_failure(
            unit,
            info,
            results=runtime.results,
            warnings=runtime.warnings,
            ledger=runtime.ledger,
        )
        return None

    merge_error = _predecessor_merge_error(unit.id, runtime)
    if merge_error:
        _record_predecessor_merge_failure(unit, merge_error, runtime)
        return None

    workdir = info.path if info and info.created else unit.repo_path
    if runtime.ledger:
        runtime.ledger.update(
            unit.id,
            status="running",
            recommended_agent=unit.recommended_agent,
        )
    return runtime.executor.submit(
        runtime.call_delegate_func,
        runtime.func,
        unit,
        workdir,
    )


def _collect_dispatch_result(
    future: concurrent.futures.Future[Any],
    unit: WorkUnit,
    runtime: _DispatchRuntime,
) -> None:
    try:
        result = future.result()
        _record_dispatch_result(
            unit,
            result,
            worktrees=runtime.worktrees,
            func=runtime.func,
            results=runtime.results,
            warnings=runtime.warnings,
            ledger=runtime.ledger,
            result_completed_func=runtime.result_completed_func,
            result_failure_reason_func=runtime.result_failure_reason_func,
            backend_name_func=runtime.backend_name_func,
            commit_worktree_func=runtime.commit_worktree_func,
        )
    except Exception as exc:
        runtime.results[unit.id] = {"error": str(exc)}
        runtime.warnings.append(f"delegate for {unit.id} failed: {exc}")
        if runtime.ledger:
            runtime.ledger.update(
                unit.id,
                status="failed",
                recommended_agent=unit.recommended_agent,
                error=str(exc),
            )


def dispatch_work_units(
    units: Sequence[WorkUnit],
    graph: DependencyGraph,
    worktrees: Mapping[str, WorktreeInfo],
    *,
    delegate_func: DelegateFunc | None,
    ledger: DelegationLedger | None,
    max_workers: int,
    resolve_delegate_func: ResolveDelegateFunc,
    call_delegate_func: CallDelegateFunc,
    result_completed_func: ResultCompletedFunc,
    result_failure_reason_func: ResultFailureReasonFunc,
    backend_name_func: BackendNameFunc,
    merge_predecessors_func: MergePredecessorsFunc,
    commit_worktree_func: CommitWorktreeFunc,
) -> tuple[dict[str, Any], list[list[str]], list[str]]:
    """Dispatch ready units concurrently and block failed dependency chains."""
    if isinstance(max_workers, bool) or not isinstance(max_workers, int) or max_workers < 1:
        raise ValueError("max_workers must be a positive integer")
    by_id = _validate_graph_nodes(units, graph)
    batches = graph.topological_batches()
    if not units:
        return {}, batches, []

    func = resolve_delegate_func(delegate_func)
    predecessors = graph.predecessors()
    results: dict[str, Any] = {}
    warnings: list[str] = []
    for unit in units:
        if ledger:
            ledger.suggest(unit.id, unit.recommended_agent)

    pool_size = min(max_workers, max(len(batch) for batch in batches))
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=pool_size,
        thread_name_prefix="agency-delegate",
    ) as executor:
        runtime = _DispatchRuntime(
            func=func,
            executor=executor,
            worktrees=worktrees,
            predecessors=predecessors,
            results=results,
            warnings=warnings,
            ledger=ledger,
            call_delegate_func=call_delegate_func,
            result_completed_func=result_completed_func,
            result_failure_reason_func=result_failure_reason_func,
            backend_name_func=backend_name_func,
            merge_predecessors_func=merge_predecessors_func,
            commit_worktree_func=commit_worktree_func,
        )
        for batch in batches:
            future_to_unit: dict[concurrent.futures.Future[Any], WorkUnit] = {}
            for unit_id in batch:
                unit = by_id[unit_id]
                future = _schedule_unit(unit, runtime)
                if future is not None:
                    future_to_unit[future] = unit

            for future in concurrent.futures.as_completed(future_to_unit):
                _collect_dispatch_result(future, future_to_unit[future], runtime)
    return results, batches, warnings


__all__ = [
    "MISSING",
    "DelegateFunc",
    "backend_name",
    "call_delegate",
    "dispatch_work_units",
    "resolve_delegate_func",
    "result_completed",
    "result_failure_reason",
    "signature_accepts",
]
