"""Dependency-aware delegation lifecycle with git worktree isolation."""

from __future__ import annotations

import concurrent.futures
import hashlib
import inspect
import os
import re
import subprocess
import tempfile
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from agency_runtime.core.delegation.ledger import DelegationLedger

DEFAULT_WORKTREE_ROOT = Path(tempfile.gettempdir()) / "agency-runtime-worktrees"
DEFAULT_MAX_WORKERS = min(8, max(1, os.cpu_count() or 4))
DelegateFunc = Callable[..., Any]

_PATH_RE = re.compile(r"(?P<path>(?:~|/|\.\.?/)[A-Za-z0-9_./@:+\-=]+)")
_FILE_RE = re.compile(r"\.(?:py|js|jsx|ts|tsx|go|rs|java|rb|css|html|md|json|ya?ml|toml|sh|sql|txt)$", re.I)
_DEP_RE = re.compile(r"\b(?:after|then|depends? on|following|once|when .* complete|use .* output)\b", re.I)
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
_MISSING = object()


@dataclass(slots=True)
class WorkUnit:
    """Normalized delegated work unit."""

    id: str
    description: str
    recommended_agent: str = ""
    repo_path: Path | None = None
    files: set[Path] = field(default_factory=set)
    raw: Any = None


@dataclass(slots=True)
class WorktreeInfo:
    """Git worktree metadata for a work unit."""

    unit_id: str
    repo_path: Path
    path: Path
    branch: str
    base_branch: str
    base_sha: str
    created: bool = False
    dirty_repo: bool = False
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DependencyGraph:
    """Directed dependency graph where edges point predecessor -> successor."""

    edges: dict[str, set[str]] = field(default_factory=dict)
    reasons: dict[tuple[str, str], str] = field(default_factory=dict)

    def predecessors(self) -> dict[str, set[str]]:
        preds = {node: set() for node in self.edges}
        for src, children in self.edges.items():
            preds.setdefault(src, set())
            for dst in children:
                preds.setdefault(dst, set()).add(src)
        return preds

    def topological_batches(self) -> list[list[str]]:
        preds = self.predecessors()
        children = {node: set(self.edges.get(node, set())) for node in preds}
        ready = deque(sorted(node for node, incoming in preds.items() if not incoming))
        emitted: set[str] = set()
        batches: list[list[str]] = []
        while ready:
            batch = list(ready)
            ready.clear()
            batches.append(batch)
            for node in batch:
                emitted.add(node)
                for child in sorted(children.get(node, set())):
                    preds[child].discard(node)
                    if not preds[child] and child not in emitted and child not in ready:
                        ready.append(child)
        if len(emitted) != len(preds):
            raise ValueError(f"dependency graph contains a cycle: {sorted(set(preds) - emitted)}")
        return batches


@dataclass(slots=True)
class LifecycleResult:
    """Consolidated lifecycle output."""

    work_units: list[WorkUnit]
    dependency_graph: DependencyGraph
    batches: list[list[str]]
    worktrees: dict[str, WorktreeInfo]
    dispatch_results: dict[str, Any]
    cleanup_results: dict[str, Any]
    warnings: list[str]
    errors: list[str]
    summary: str
    ledger: DelegationLedger | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "work_units": [{"id": u.id, "description": u.description, "recommended_agent": u.recommended_agent, "repo_path": str(u.repo_path) if u.repo_path else None, "files": sorted(str(p) for p in u.files)} for u in self.work_units],
            "dependency_graph": {"edges": {k: sorted(v) for k, v in self.dependency_graph.edges.items()}, "reasons": {f"{a}->{b}": r for (a, b), r in self.dependency_graph.reasons.items()}},
            "batches": self.batches,
            "worktrees": {k: {"repo_path": str(v.repo_path), "path": str(v.path), "branch": v.branch, "base_branch": v.base_branch, "base_sha": v.base_sha, "created": v.created, "dirty_repo": v.dirty_repo, "warnings": v.warnings, "errors": v.errors} for k, v in self.worktrees.items()},
            "dispatch_results": self.dispatch_results,
            "cleanup_results": self.cleanup_results,
            "warnings": self.warnings,
            "errors": self.errors,
            "summary": self.summary,
            "ledger": self.ledger.as_dict() if self.ledger else None,
        }


def _run_git(repo: Path, args: Sequence[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=str(repo), text=True, capture_output=True, timeout=timeout)


def _git_root(path: Path) -> Path | None:
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    if candidate.is_file():
        candidate = candidate.parent
    if not candidate.exists():
        for parent in candidate.parents:
            if parent.exists():
                candidate = parent
                break
    result = subprocess.run(["git", "-C", str(candidate), "rev-parse", "--show-toplevel"], text=True, capture_output=True, timeout=10)
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else None


def _items(work_units: Any) -> list[Any]:
    if isinstance(work_units, Mapping):
        units = work_units.get("units")
        if isinstance(units, list):
            return list(units)
        return [work_units]
    if isinstance(work_units, str):
        return [work_units]
    if isinstance(work_units, Iterable):
        return list(work_units)
    return [work_units]


def _desc(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, Mapping):
        for key in ("description", "task", "unit", "title", "summary"):
            if item.get(key):
                return str(item[key]).strip()
    return str(item).strip()


def _safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.")[:80] or f"unit-{uuid.uuid4().hex[:8]}"


def _stable_id(idx: int, description: str) -> str:
    return f"unit-{idx + 1}-{hashlib.sha256(description.encode()).hexdigest()[:8]}"


def _validate_unique_unit_ids(units: Sequence[WorkUnit]) -> None:
    """Reject IDs that would make graph nodes or result entries ambiguous."""
    seen: set[str] = set()
    duplicates: set[str] = set()
    for unit in units:
        if unit.id in seen:
            duplicates.add(unit.id)
        seen.add(unit.id)
    if duplicates:
        rendered = ", ".join(repr(unit_id) for unit_id in sorted(duplicates))
        raise ValueError(f"duplicate work-unit id(s): {rendered}")


def _explicit_files(item: Any) -> set[Path]:
    if not isinstance(item, Mapping):
        return set()
    value = item.get("files") or item.get("paths") or []
    if isinstance(value, (str, Path)):
        value = [value]
    return {Path(str(v)).expanduser() for v in value} if isinstance(value, Iterable) else set()


def normalize_work_units(work_units: Any, repo_path: str | Path | None = None, *, fallback_repo: Path | None = None) -> list[WorkUnit]:
    """Normalize strings/mappings into {id, description, recommended_agent} work units."""
    repo_fallback = Path(repo_path).expanduser().resolve() if repo_path else (fallback_repo.resolve() if fallback_repo else None)
    out: list[WorkUnit] = []
    for idx, item in enumerate(_items(work_units)):
        description = _desc(item)
        if not description:
            continue
        raw_id = str(item.get("id")) if isinstance(item, Mapping) and item.get("id") else _stable_id(idx, description)
        recommended = str(item.get("recommended_agent") or item.get("agent") or "") if isinstance(item, Mapping) else ""
        repo = Path(str(item["repo_path"])).expanduser().resolve() if isinstance(item, Mapping) and item.get("repo_path") else None
        files = _explicit_files(item)
        for match in _PATH_RE.finditer(description):
            path = Path(match.group("path").rstrip(".,);]}'\"")).expanduser()
            repo = repo or _git_root(path)
            if _FILE_RE.search(str(path)) or (path.exists() and path.is_file()):
                files.add(path)
        repo = repo or repo_fallback
        norm_files: set[Path] = set()
        for file_path in files:
            absolute = file_path if file_path.is_absolute() else ((repo or Path.cwd()) / file_path)
            try:
                norm_files.add(absolute.resolve().relative_to(repo) if repo else absolute.resolve())
            except ValueError:
                norm_files.add(absolute.resolve())
        out.append(WorkUnit(id=_safe(raw_id), description=description, recommended_agent=recommended, repo_path=repo, files=norm_files, raw=item))
    _validate_unique_unit_ids(out)
    return out


def build_dependency_graph(units: Sequence[WorkUnit]) -> DependencyGraph:
    """Build dependency edges from sequencing language and same-file overlap."""
    _validate_unique_unit_ids(units)
    graph = DependencyGraph(edges={u.id: set() for u in units})
    for idx, unit in enumerate(units):
        if idx > 0 and _DEP_RE.search(unit.description):
            graph.edges[units[idx - 1].id].add(unit.id)
            graph.reasons[(units[idx - 1].id, unit.id)] = "sequencing language in work-unit description"
    for i, left in enumerate(units):
        for right in units[i + 1:]:
            if left.repo_path and right.repo_path and left.repo_path == right.repo_path and left.files and right.files:
                shared = left.files & right.files
                if shared:
                    graph.edges[left.id].add(right.id)
                    graph.reasons[(left.id, right.id)] = f"shared file(s): {', '.join(sorted(str(p) for p in shared))}"
    return graph


def _current_branch(repo: Path) -> str | None:
    result = _run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"], timeout=10)
    branch = result.stdout.strip()
    return branch if result.returncode == 0 and branch and branch != "HEAD" else None


def _head_sha(repo: Path, ref: str = "HEAD") -> str:
    result = _run_git(repo, ["rev-parse", ref], timeout=10)
    return result.stdout.strip() if result.returncode == 0 else ""


def provision_worktrees(units: Sequence[WorkUnit], *, base_branch: str | None = None, worktree_root: Path = DEFAULT_WORKTREE_ROOT) -> dict[str, WorktreeInfo]:
    """Create worktrees only for repositories targeted by multiple units."""
    _validate_unique_unit_ids(units)
    by_repo: dict[Path, list[WorkUnit]] = defaultdict(list)
    for unit in units:
        if unit.repo_path and _git_root(unit.repo_path) == unit.repo_path.resolve():
            by_repo[unit.repo_path.resolve()].append(unit)
    worktrees: dict[str, WorktreeInfo] = {}
    worktree_root.mkdir(parents=True, exist_ok=True)
    run_root = Path(tempfile.mkdtemp(prefix="run-", dir=str(worktree_root)))
    run_token = run_root.name.removeprefix("run-").replace("-", "") or uuid.uuid4().hex
    for repo, repo_units in by_repo.items():
        base = base_branch or _current_branch(repo) or "main"
        base_sha = _head_sha(repo, base)
        dirty = bool(_run_git(repo, ["status", "--porcelain"]).stdout.strip())
        for unit in repo_units:
            branch = f"delegation/{unit.id}-{run_token[:12]}"
            path = run_root / unit.id
            info = WorktreeInfo(
                unit.id,
                repo,
                path,
                branch,
                base,
                base_sha,
                dirty_repo=dirty,
            )
            if path.exists():
                info.errors.append(f"unique worktree path unexpectedly exists: {path}")
                worktrees[unit.id] = info
                continue
            cmd = ["worktree", "add", str(path), "-b", branch, base]
            result = _run_git(repo, cmd)
            if result.returncode == 0:
                info.created = True
            else:
                info.errors.append(result.stderr.strip() or result.stdout.strip() or "git worktree add failed")
            worktrees[unit.id] = info
    return worktrees


def _resolve_delegate_func(delegate_func: DelegateFunc | None) -> DelegateFunc:
    if delegate_func:
        return delegate_func
    from agency_runtime.core.delegation.backends import get_delegate_func
    return get_delegate_func()


def _call_delegate(func: DelegateFunc, unit: WorkUnit, workdir: Path | None) -> Any:
    task = (
        f"Work unit {unit.id}:\n{unit.description}\n\n"
        f"Workdir: {workdir or unit.repo_path or Path.cwd()}\n"
        "When this is an isolated git worktree, leave every intended file change "
        "in that worktree before reporting success; Agency Runtime will create a "
        "bounded integration commit if needed."
    )
    kwargs = {"task": task, "workdir": str(workdir or unit.repo_path or Path.cwd()), "recommended_agent": unit.recommended_agent}
    legacy_kwargs = {"goal": unit.description, "context": f"workdir={kwargs['workdir']}", "recommended_agent": unit.recommended_agent}
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return func(**kwargs)
    if _signature_accepts(signature, **kwargs):
        return func(**kwargs)
    if _signature_accepts(signature, **legacy_kwargs):
        return func(**legacy_kwargs)
    if _signature_accepts(signature, task=task):
        return func(task=task)
    return func(task)


def _signature_accepts(signature: inspect.Signature, *args: Any, **kwargs: Any) -> bool:
    try:
        signature.bind(*args, **kwargs)
    except TypeError:
        return False
    return True


def _backend(result: Any, func: DelegateFunc) -> str:
    return str(result.get("backend")) if isinstance(result, Mapping) and result.get("backend") else str(getattr(func, "backend_name", "callable"))


def _result_completed(result: Any = _MISSING) -> bool:
    """Return whether a worker produced an affirmative completion result."""
    if result is _MISSING:
        return False
    if result is None or result is False:
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
    status = str(result.get("status") or "").strip().lower().replace("-", "_").replace(" ", "_")
    if status in _NOT_COMPLETED_RESULT_STATUSES:
        return False
    if status in _COMPLETED_RESULT_STATUSES:
        return True
    if any(result.get(flag) is True for flag in ("ok", "success", "completed", "delegated")):
        return True
    output = result.get("output")
    return isinstance(output, (str, bytes, list, tuple, dict)) and bool(output)


def _result_failure_reason(result: Any = _MISSING) -> str:
    """Extract a stable reason for a missing or unsuccessful worker result."""
    if result is _MISSING:
        return "no dispatch result was recorded"
    if isinstance(result, Mapping):
        for key in ("error", "skip_reason", "message"):
            value = result.get(key)
            if value:
                return str(value)
        if result.get("ok") is False:
            return "worker reported ok=false"
        if result.get("success") is False:
            return "worker reported success=false"
        if result.get("completed") is False:
            return "worker reported completed=false"
        if result.get("delegated") is False:
            return "worker reported delegated=false"
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


def _merge_predecessor_work(
    unit_id: str,
    predecessor_ids: Iterable[str],
    worktrees: Mapping[str, WorktreeInfo],
) -> str | None:
    """Merge successful same-repository predecessor branches before dispatch."""
    target = worktrees.get(unit_id)
    if target is None or not target.created:
        return None
    for predecessor_id in sorted(predecessor_ids):
        predecessor = worktrees.get(predecessor_id)
        if predecessor is None or not predecessor.created:
            continue
        if predecessor.repo_path.resolve() != target.repo_path.resolve():
            continue
        merge = _run_git(target.path, ["merge", "--no-ff", "--no-edit", predecessor.branch])
        if merge.returncode == 0:
            continue
        _run_git(target.path, ["merge", "--abort"])
        detail = merge.stderr.strip() or merge.stdout.strip() or "git merge failed"
        return f"could not apply predecessor {predecessor_id!r}: {detail}"
    return None


def _commit_successful_worktree(info: WorktreeInfo, unit_id: str) -> str | None:
    """Commit successful uncommitted worker edits so they cannot be discarded."""
    status = _run_git(info.path, ["status", "--porcelain"], timeout=30)
    if status.returncode != 0:
        return status.stderr.strip() or status.stdout.strip() or "could not inspect worktree changes"
    if not status.stdout.strip():
        return None
    staged = _run_git(info.path, ["add", "--all"], timeout=60)
    if staged.returncode != 0:
        return staged.stderr.strip() or staged.stdout.strip() or "could not stage worker changes"
    committed = _run_git(
        info.path,
        [
            "-c",
            "user.name=Agency Runtime",
            "-c",
            "user.email=agency-runtime@localhost",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            f"agency(delegate): complete {unit_id}",
        ],
        timeout=60,
    )
    if committed.returncode != 0:
        return committed.stderr.strip() or committed.stdout.strip() or "could not commit worker changes"
    return None


def dispatch_work_units(units: Sequence[WorkUnit], graph: DependencyGraph, worktrees: Mapping[str, WorktreeInfo], *, delegate_func: DelegateFunc | None = None, ledger: DelegationLedger | None = None, max_workers: int = DEFAULT_MAX_WORKERS) -> tuple[dict[str, Any], list[list[str]], list[str]]:
    """Dispatch ready units concurrently and block failed dependency chains."""
    _validate_unique_unit_ids(units)
    func = _resolve_delegate_func(delegate_func)
    by_id = {u.id: u for u in units}
    batches = graph.topological_batches()
    predecessors = graph.predecessors()
    results: dict[str, Any] = {}
    warnings: list[str] = []
    if max_workers < 1:
        raise ValueError("max_workers must be at least one")
    for unit in units:
        if ledger:
            ledger.suggest(unit.id, unit.recommended_agent)
    for batch in batches:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, max(1, len(batch)))) as executor:
            future_to_unit = {}
            for unit_id in batch:
                unit = by_id[unit_id]
                blocked_by = sorted(
                    predecessor_id
                    for predecessor_id in predecessors.get(unit_id, set())
                    if not _result_completed(results.get(predecessor_id, _MISSING))
                )
                if blocked_by:
                    reason = f"dependency did not complete successfully: {', '.join(blocked_by)}"
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
                    continue
                info = worktrees.get(unit_id)
                if info is not None and not info.created:
                    reason = "isolated worktree was not created"
                    results[unit.id] = {"error": reason, "status": "failed"}
                    warnings.append(f"delegate for {unit.id} failed: {reason}")
                    if ledger:
                        ledger.update(
                            unit.id,
                            status="failed",
                            recommended_agent=unit.recommended_agent,
                            error=reason,
                        )
                    continue
                merge_error = _merge_predecessor_work(
                    unit_id,
                    predecessors.get(unit_id, set()),
                    worktrees,
                )
                if merge_error:
                    results[unit.id] = {
                        "error": merge_error,
                        "status": "skipped",
                        "skip_reason": merge_error,
                        "blocked_by": sorted(predecessors.get(unit_id, set())),
                    }
                    warnings.append(f"delegate for {unit.id} skipped: {merge_error}")
                    if ledger:
                        ledger.update(
                            unit.id,
                            status="skipped",
                            recommended_agent=unit.recommended_agent,
                            skip_reason=merge_error,
                            error=merge_error,
                        )
                    continue
                workdir = info.path if info and info.created else unit.repo_path
                if ledger:
                    ledger.update(unit.id, status="running", recommended_agent=unit.recommended_agent)
                future_to_unit[executor.submit(_call_delegate, func, unit, workdir)] = unit
            for future in concurrent.futures.as_completed(future_to_unit):
                unit = future_to_unit[future]
                try:
                    result = future.result()
                    results[unit.id] = result
                    if _result_completed(result):
                        info = worktrees.get(unit.id)
                        commit_error = (
                            _commit_successful_worktree(info, unit.id)
                            if info is not None and info.created
                            else None
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
                                    backend=_backend(result, func),
                                    recommended_agent=unit.recommended_agent,
                                    error=reason,
                                )
                            continue
                        if ledger:
                            ledger.update(unit.id, status="completed", backend=_backend(result, func), recommended_agent=unit.recommended_agent)
                    else:
                        reason = _result_failure_reason(result)
                        warnings.append(f"delegate for {unit.id} failed: {reason}")
                        if ledger:
                            ledger.update(
                                unit.id,
                                status="failed",
                                backend=_backend(result, func),
                                recommended_agent=unit.recommended_agent,
                                error=reason,
                            )
                except Exception as exc:
                    results[unit.id] = {"error": str(exc)}
                    warnings.append(f"delegate for {unit.id} failed: {exc}")
                    if ledger:
                        ledger.update(unit.id, status="failed", recommended_agent=unit.recommended_agent, error=str(exc))
    return results, batches, warnings


def cleanup_worktrees(
    worktrees: Mapping[str, WorktreeInfo],
    *,
    merge_back: bool = True,
    create_pr_on_conflict: bool = False,
    merge_unit_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Merge successful branches back and remove all provisioned worktrees."""
    cleanup: dict[str, Any] = {}
    merge_allowed: dict[tuple[Path, str, str], tuple[bool, str]] = {}
    for info in worktrees.values():
        key = (info.repo_path.resolve(), info.base_branch, info.base_sha)
        if key in merge_allowed:
            continue
        current_branch = _current_branch(info.repo_path)
        current_head = _head_sha(info.repo_path)
        currently_dirty = bool(
            _run_git(info.repo_path, ["status", "--porcelain"], timeout=30).stdout.strip()
        )
        reasons: list[str] = []
        if info.dirty_repo or currently_dirty:
            reasons.append("base worktree is dirty")
        if current_branch != info.base_branch:
            reasons.append(
                f"base worktree switched from {info.base_branch!r} to {current_branch!r}"
            )
        if not info.base_sha or current_head != info.base_sha:
            reasons.append("base branch head changed during delegation")
        merge_allowed[key] = (not reasons, "; ".join(reasons))
    for unit_id, info in worktrees.items():
        record = {"branch": info.branch, "worktree": str(info.path), "merged": False, "removed": False, "preserved": False, "branch_deleted": False, "conflict": False, "warnings": list(info.warnings), "errors": list(info.errors)}
        if not info.created:
            record["warnings"].append("worktree was not created; skipping cleanup")
            cleanup[unit_id] = record
            continue
        should_merge = merge_back and (merge_unit_ids is None or unit_id in merge_unit_ids)
        if merge_back and not should_merge:
            record["warnings"].append("work unit did not complete successfully; branch was not merged")
        if should_merge:
            allowed, reason = merge_allowed[
                (info.repo_path.resolve(), info.base_branch, info.base_sha)
            ]
            if not allowed:
                record["warnings"].append(
                    f"branch preserved instead of merging: {reason}"
                )
            else:
                merge = _run_git(info.repo_path, ["merge", "--no-ff", info.branch])
                if merge.returncode == 0:
                    record["merged"] = True
                else:
                    record["conflict"] = True
                    record["errors"].append(merge.stderr.strip() or merge.stdout.strip() or "merge failed")
                    _run_git(info.repo_path, ["merge", "--abort"])
                    if create_pr_on_conflict:
                        record["warnings"].append("merge conflict encountered; branch left for PR/manual resolution")
        dirty = _run_git(info.path, ["status", "--porcelain"], timeout=30)
        if dirty.returncode != 0:
            record["errors"].append(
                dirty.stderr.strip() or dirty.stdout.strip() or "could not inspect worktree before removal"
            )
            record["preserved"] = True
            record["warnings"].append("worktree preserved because cleanliness could not be proven")
            cleanup[unit_id] = record
            continue
        if dirty.stdout.strip():
            record["preserved"] = True
            record["warnings"].append("uncommitted worker changes preserved for manual recovery")
            cleanup[unit_id] = record
            continue
        remove = _run_git(info.repo_path, ["worktree", "remove", str(info.path)])
        if remove.returncode == 0:
            record["removed"] = True
            if record["merged"]:
                deleted = _run_git(info.repo_path, ["branch", "--delete", info.branch], timeout=30)
                if deleted.returncode == 0:
                    record["branch_deleted"] = True
                else:
                    record["warnings"].append(
                        deleted.stderr.strip() or deleted.stdout.strip() or "merged branch could not be deleted"
                    )
        else:
            record["errors"].append(remove.stderr.strip() or remove.stdout.strip() or "worktree remove failed")
            record["preserved"] = True
            record["warnings"].append("worktree removal failed; path preserved for manual recovery")
        cleanup[unit_id] = record
    return cleanup


def aggregate_results(units: Sequence[WorkUnit], graph: DependencyGraph, batches: Sequence[Sequence[str]], worktrees: Mapping[str, WorktreeInfo], dispatch_results: Mapping[str, Any], cleanup_results: Mapping[str, Any], warnings: Sequence[str], errors: Sequence[str]) -> str:
    """Build a compact lifecycle summary."""
    completed = sum(
        1
        for unit in units
        if _result_completed(dispatch_results.get(unit.id, _MISSING))
    )
    not_completed = len(units) - completed
    lines = [
        f"Delegation lifecycle completed for {len(units)} work unit(s).",
        f"Execution batches: {', '.join('[' + ', '.join(b) + ']' for b in batches) or 'none'}.",
        f"Worker results: {completed} completed, {not_completed} failed/not completed.",
    ]
    if graph.reasons:
        lines.append("Dependencies: " + "; ".join(f"{a}->{b}: {r}" for (a, b), r in sorted(graph.reasons.items())))
    if worktrees:
        lines.append("Worktrees: " + ", ".join(f"{k}={'created' if v.created else 'failed'}" for k, v in sorted(worktrees.items())))
    if warnings:
        lines.append("Warnings: " + "; ".join(warnings))
    if errors:
        lines.append("Errors: " + "; ".join(errors))
    return "\n".join(lines)


def delegate_with_lifecycle(work_units: Any, repo_path: str | Path | None = None, base_branch: str | None = None, *, delegate_func: DelegateFunc | None = None, worktree_root: str | Path = DEFAULT_WORKTREE_ROOT, merge_back: bool = True, ledger: DelegationLedger | None = None, max_workers: int = DEFAULT_MAX_WORKERS) -> LifecycleResult:
    """One-shot normalize → graph → worktree → dispatch → cleanup API."""
    units = normalize_work_units(work_units, repo_path=repo_path)
    graph = build_dependency_graph(units)
    warnings: list[str] = []
    errors: list[str] = []
    if ledger:
        for unit in units:
            ledger.suggest(unit.id, unit.recommended_agent)
    try:
        worktrees = provision_worktrees(units, base_branch=base_branch, worktree_root=Path(worktree_root))
    except Exception as exc:
        worktrees = {}
        errors.append(f"worktree provisioning failed: {exc}")
    try:
        dispatch_results, batches, dispatch_warnings = dispatch_work_units(
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
                ledger.update(unit.id, status="failed", recommended_agent=unit.recommended_agent, error=str(exc))
    completed_unit_ids = {
        unit.id
        for unit in units
        if _result_completed(dispatch_results.get(unit.id, _MISSING))
    }
    cleanup_results = (
        cleanup_worktrees(
            worktrees,
            merge_back=merge_back,
            merge_unit_ids=completed_unit_ids,
        )
        if worktrees
        else {}
    )
    summary = aggregate_results(units, graph, batches, worktrees, dispatch_results, cleanup_results, warnings, errors)
    return LifecycleResult(units, graph, batches, worktrees, dispatch_results, cleanup_results, warnings, errors, summary, ledger)


__all__ = ["DEFAULT_MAX_WORKERS", "DEFAULT_WORKTREE_ROOT", "DelegateFunc", "DependencyGraph", "LifecycleResult", "WorkUnit", "WorktreeInfo", "aggregate_results", "build_dependency_graph", "cleanup_worktrees", "delegate_with_lifecycle", "dispatch_work_units", "normalize_work_units", "provision_worktrees"]
