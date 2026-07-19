"""Bounded dependency-aware dispatch for delegated work units."""

from __future__ import annotations

import asyncio
import concurrent.futures
import heapq
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

_LEGACY_COMPLETION_FLAGS = ("ok", "success", "completed")
_NEGATIVE_COMPLETION_FLAGS = ("ok", "success", "completed")
_FAILURE_FIELDS = ("error", "errors", "exception", "failure")
_FAILURE_FLAGS = (
    "blocked",
    "cancelled",
    "canceled",
    "failed",
    "partial",
    "skipped",
    "timed_out",
)
_EXIT_CODE_FIELDS = ("exit_code", "returncode", "return_code", "exitCode", "process_exit_code")


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


def validate_max_workers(max_workers: int) -> None:
    """Reject invalid executor contracts before any provisioning can occur."""
    if isinstance(max_workers, bool) or not isinstance(max_workers, int) or max_workers < 1:
        raise ValueError("max_workers must be a positive integer")


def _validate_delegate_contract(func: Any) -> DelegateFunc:
    if not callable(func):
        raise TypeError("delegate_func or resolved delegation backend must be callable")
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return func
    modern = {
        "task": "task",
        "workdir": "workdir",
        "recommended_agent": "agent",
    }
    legacy = {
        "goal": "goal",
        "context": "context",
        "recommended_agent": "agent",
    }
    if any(
        signature_accepts(signature, *args, **kwargs)
        for args, kwargs in (
            ((), modern),
            ((), legacy),
            ((), {"task": "task"}),
            (("task",), {}),
        )
    ):
        return func
    raise TypeError(
        "delegate_func must accept the modern task/workdir contract, "
        "the legacy goal/context contract, task=, or one positional task"
    )


def prepare_delegate_func(
    delegate_func: DelegateFunc | None,
    *,
    resolve_func: ResolveDelegateFunc = resolve_delegate_func,
) -> DelegateFunc:
    """Resolve and validate a delegation backend without invoking it."""
    return _validate_delegate_contract(resolve_func(delegate_func))


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


def _owned_command_backend(func: DelegateFunc) -> bool:
    """Return whether a delegate is bound to a package-owned command backend."""

    from agency_runtime.core.delegation.backend_command import CommandBackend

    owner = getattr(func, "__self__", None)
    if not isinstance(owner, CommandBackend):
        owner = getattr(func, "_agency_backend", None)
    return isinstance(owner, CommandBackend)


def _execution_identity(
    result: Any,
    func: DelegateFunc,
    *,
    backend: str,
) -> tuple[str, str, str]:
    """Extract one complete worker receipt without combining partial identities."""

    if not isinstance(result, Mapping):
        return "", "", ""
    explicit = tuple(
        str(result.get(field) or "").strip() if isinstance(result.get(field), str) else ""
        for field in ("executed_worker_kind", "executed_worker_id", "native_run_id")
    )
    if all(explicit):
        return explicit
    if not _owned_command_backend(func):
        return "", "", ""
    executable = result.get("executable")
    process_id = result.get("process_id")
    if (
        not isinstance(executable, str)
        or not executable.strip()
        or isinstance(process_id, bool)
        or not isinstance(process_id, int)
        or process_id <= 0
    ):
        return "", "", ""
    return "cli-process", executable.strip(), f"{backend}:process:{process_id}"


def _normalized_status(result: Mapping[Any, Any]) -> str:
    return str(result.get("status") or "").strip().lower().replace("-", "_").replace(" ", "_")


def result_completed(result: Any = MISSING) -> bool:
    """Require canonical completion or an affirmative legacy boolean receipt."""
    if not isinstance(result, Mapping):
        return False
    if any(result.get(field) for field in _FAILURE_FIELDS):
        return False
    if any(result.get(flag) is True for flag in _FAILURE_FLAGS):
        return False
    if any(result.get(flag) is False for flag in _NEGATIVE_COMPLETION_FLAGS):
        return False
    for code_key in _EXIT_CODE_FIELDS:
        code = result.get(code_key)
        if code is not None and code != 0:
            return False
    if "status" in result:
        raw_status = result.get("status")
        if not isinstance(raw_status, str) or not raw_status.strip():
            return False
        status = _normalized_status(result)
        # "delegated" proves dispatch, not successful execution.
        return status == "completed"
    return any(result.get(flag) is True for flag in _LEGACY_COMPLETION_FLAGS)


def result_failure_reason(result: Any = MISSING) -> str:
    """Extract a stable reason for a missing or unsuccessful worker result."""
    if result is MISSING:
        return "no dispatch result was recorded"
    if isinstance(result, Mapping):
        for field in _FAILURE_FIELDS:
            if result.get(field):
                return str(result[field])
        for key in ("skip_reason", "message"):
            value = result.get(key)
            if value:
                return str(value)
        if result.get("timed_out") is True:
            return "worker timed out"
        for failure_flag in _FAILURE_FLAGS:
            if result.get(failure_flag) is True:
                return f"worker reported {failure_flag}=true"
        for flag in _NEGATIVE_COMPLETION_FLAGS:
            if result.get(flag) is False:
                return f"worker reported {flag}=false"
        for code_key in _EXIT_CODE_FIELDS:
            code = result.get(code_key)
            if code is not None and code != 0:
                return f"worker reported {code_key}={code}"
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

    worker_kind, worker_id, native_run_id = _execution_identity(
        result,
        func,
        backend=backend,
    )
    if not all((worker_kind, worker_id, native_run_id)):
        reason = "delegation reported success without complete execution correlation"
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
            executed_worker_kind=worker_kind,
            executed_worker_id=worker_id,
            native_run_id=native_run_id,
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


def _skip_descendants(
    failed_unit_id: str,
    *,
    graph: DependencyGraph,
    by_id: Mapping[str, WorkUnit],
    runtime: _DispatchRuntime,
) -> None:
    """Recursively terminalize every dependent of a failed work unit."""
    pending_sources = [failed_unit_id]
    while pending_sources:
        source = heapq.heappop(pending_sources)
        for child_id in sorted(graph.edges.get(source, set())):
            if child_id in runtime.results:
                continue
            reason = f"dependency did not complete successfully: {source}"
            _record_skip(
                by_id[child_id],
                reason=reason,
                blocked_by=[source],
                results=runtime.results,
                warnings=runtime.warnings,
                ledger=runtime.ledger,
            )
            heapq.heappush(pending_sources, child_id)


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
    validate_max_workers(max_workers)
    by_id = _validate_graph_nodes(units, graph)
    batches = graph.topological_batches()
    if not units:
        return {}, batches, []

    func = prepare_delegate_func(delegate_func, resolve_func=resolve_delegate_func)
    predecessors = graph.predecessors()
    results: dict[str, Any] = {}
    warnings: list[str] = []
    for unit in units:
        if ledger:
            ledger.suggest(unit.id, unit.recommended_agent)

    pool_size = min(max_workers, len(units))
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
        remaining = {unit_id: len(incoming) for unit_id, incoming in predecessors.items()}
        ready = sorted(unit_id for unit_id, count in remaining.items() if count == 0)
        heapq.heapify(ready)
        future_to_unit: dict[concurrent.futures.Future[Any], WorkUnit] = {}
        while ready or future_to_unit:
            while ready and len(future_to_unit) < pool_size:
                unit_id = heapq.heappop(ready)
                if unit_id in results:
                    continue
                unit = by_id[unit_id]
                future = _schedule_unit(unit, runtime)
                if future is None:
                    _skip_descendants(
                        unit_id,
                        graph=graph,
                        by_id=by_id,
                        runtime=runtime,
                    )
                    continue
                future_to_unit[future] = unit

            if not future_to_unit:
                continue
            completed, _pending = concurrent.futures.wait(
                future_to_unit,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            for future in sorted(completed, key=lambda item: future_to_unit[item].id):
                unit = future_to_unit.pop(future)
                _collect_dispatch_result(future, unit, runtime)
                if not result_completed_func(results.get(unit.id, MISSING)):
                    _skip_descendants(
                        unit.id,
                        graph=graph,
                        by_id=by_id,
                        runtime=runtime,
                    )
                    continue
                for child_id in sorted(graph.edges.get(unit.id, set())):
                    if child_id in results:
                        continue
                    remaining[child_id] -= 1
                    if remaining[child_id] == 0:
                        heapq.heappush(ready, child_id)
    return results, batches, warnings


__all__ = [
    "MISSING",
    "DelegateFunc",
    "backend_name",
    "call_delegate",
    "dispatch_work_units",
    "prepare_delegate_func",
    "resolve_delegate_func",
    "result_completed",
    "result_failure_reason",
    "signature_accepts",
    "validate_max_workers",
]
