"""Dependency-aware delegation lifecycle with git worktree isolation."""

from __future__ import annotations

import concurrent.futures
import hashlib
import re
import shutil
import subprocess
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from agency_runtime.core.delegation.ledger import DelegationLedger

DEFAULT_WORKTREE_ROOT = Path("/tmp/agency-runtime-worktrees")
DelegateFunc = Callable[..., Any]

_PATH_RE = re.compile(r"(?P<path>(?:~|/|\.\.?/)[A-Za-z0-9_./@:+\-=]+)")
_FILE_RE = re.compile(r"\.(?:py|js|jsx|ts|tsx|go|rs|java|rb|css|html|md|json|ya?ml|toml|sh|sql|txt)$", re.I)
_DEP_RE = re.compile(r"\b(?:after|then|depends? on|following|once|when .* complete|use .* output)\b", re.I)


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
            "worktrees": {k: {"repo_path": str(v.repo_path), "path": str(v.path), "branch": v.branch, "base_branch": v.base_branch, "created": v.created, "dirty_repo": v.dirty_repo, "warnings": v.warnings, "errors": v.errors} for k, v in self.worktrees.items()},
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
    return f"unit-{idx + 1}-{hashlib.sha1(description.encode()).hexdigest()[:8]}"


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
    return out


def build_dependency_graph(units: Sequence[WorkUnit]) -> DependencyGraph:
    """Build dependency edges from sequencing language and same-file overlap."""
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


def _branch_exists(repo: Path, branch: str) -> bool:
    return _run_git(repo, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"]).returncode == 0


def provision_worktrees(units: Sequence[WorkUnit], *, base_branch: str | None = None, worktree_root: Path = DEFAULT_WORKTREE_ROOT) -> dict[str, WorktreeInfo]:
    """Create worktrees only for repositories targeted by multiple units."""
    by_repo: dict[Path, list[WorkUnit]] = defaultdict(list)
    for unit in units:
        if unit.repo_path and _git_root(unit.repo_path) == unit.repo_path.resolve():
            by_repo[unit.repo_path.resolve()].append(unit)
    worktrees: dict[str, WorktreeInfo] = {}
    worktree_root.mkdir(parents=True, exist_ok=True)
    for repo, repo_units in by_repo.items():
        if len(repo_units) < 2:
            continue
        base = base_branch or _current_branch(repo) or "main"
        dirty = bool(_run_git(repo, ["status", "--porcelain"]).stdout.strip())
        for unit in repo_units:
            branch = f"delegation/{unit.id}"
            path = worktree_root / unit.id
            info = WorktreeInfo(unit.id, repo, path, branch, base, dirty_repo=dirty)
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
                info.warnings.append(f"removed stale worktree path {path}")
            cmd = ["worktree", "add", str(path), branch] if _branch_exists(repo, branch) else ["worktree", "add", str(path), "-b", branch, base]
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
    task = f"Work unit {unit.id}:\n{unit.description}\n\nWorkdir: {workdir or unit.repo_path or Path.cwd()}"
    kwargs = {"task": task, "workdir": str(workdir or unit.repo_path or Path.cwd()), "recommended_agent": unit.recommended_agent}
    try:
        return func(**kwargs)
    except TypeError:
        try:
            return func(goal=unit.description, context=f"workdir={kwargs['workdir']}", recommended_agent=unit.recommended_agent)
        except TypeError:
            return func(task)


def _backend(result: Any, func: DelegateFunc) -> str:
    return str(result.get("backend")) if isinstance(result, Mapping) and result.get("backend") else str(getattr(func, "backend_name", "callable"))


def dispatch_work_units(units: Sequence[WorkUnit], graph: DependencyGraph, worktrees: Mapping[str, WorktreeInfo], *, delegate_func: DelegateFunc | None = None, ledger: DelegationLedger | None = None) -> tuple[dict[str, Any], list[list[str]], list[str]]:
    """Dispatch topological batches with ThreadPoolExecutor."""
    func = _resolve_delegate_func(delegate_func)
    by_id = {u.id: u for u in units}
    batches = graph.topological_batches()
    results: dict[str, Any] = {}
    warnings: list[str] = []
    for unit in units:
        if ledger:
            ledger.suggest(unit.id, unit.recommended_agent)
    for batch in batches:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(batch))) as executor:
            future_to_unit = {}
            for unit_id in batch:
                unit = by_id[unit_id]
                info = worktrees.get(unit_id)
                workdir = info.path if info and info.created else unit.repo_path
                if ledger:
                    ledger.update(unit.id, status="running", recommended_agent=unit.recommended_agent)
                future_to_unit[executor.submit(_call_delegate, func, unit, workdir)] = unit
            for future in concurrent.futures.as_completed(future_to_unit):
                unit = future_to_unit[future]
                try:
                    result = future.result()
                    results[unit.id] = result
                    if ledger:
                        ledger.update(unit.id, status="completed", backend=_backend(result, func), recommended_agent=unit.recommended_agent)
                except Exception as exc:
                    results[unit.id] = {"error": str(exc)}
                    warnings.append(f"delegate for {unit.id} failed: {exc}")
                    if ledger:
                        ledger.update(unit.id, status="failed", recommended_agent=unit.recommended_agent, error=str(exc))
    return results, batches, warnings


def cleanup_worktrees(worktrees: Mapping[str, WorktreeInfo], *, merge_back: bool = True, create_pr_on_conflict: bool = False) -> dict[str, Any]:
    """Merge branches back and remove worktrees."""
    cleanup: dict[str, Any] = {}
    for unit_id, info in worktrees.items():
        record = {"branch": info.branch, "worktree": str(info.path), "merged": False, "removed": False, "conflict": False, "warnings": list(info.warnings), "errors": list(info.errors)}
        if not info.created:
            record["warnings"].append("worktree was not created; skipping cleanup")
            cleanup[unit_id] = record
            continue
        if merge_back:
            checkout = _run_git(info.repo_path, ["checkout", info.base_branch])
            if checkout.returncode != 0:
                record["errors"].append(checkout.stderr.strip() or checkout.stdout.strip() or "checkout base failed")
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
        remove = _run_git(info.repo_path, ["worktree", "remove", "--force", str(info.path)])
        if remove.returncode == 0:
            record["removed"] = True
        else:
            record["errors"].append(remove.stderr.strip() or remove.stdout.strip() or "worktree remove failed")
            shutil.rmtree(info.path, ignore_errors=True)
            record["removed"] = not info.path.exists()
        cleanup[unit_id] = record
    return cleanup


def aggregate_results(units: Sequence[WorkUnit], graph: DependencyGraph, batches: Sequence[Sequence[str]], worktrees: Mapping[str, WorktreeInfo], dispatch_results: Mapping[str, Any], cleanup_results: Mapping[str, Any], warnings: Sequence[str], errors: Sequence[str]) -> str:
    """Build a compact lifecycle summary."""
    ok = sum(1 for unit in units if not (isinstance(dispatch_results.get(unit.id), Mapping) and dispatch_results[unit.id].get("error")))
    lines = [f"Delegation lifecycle completed for {len(units)} work unit(s).", f"Execution batches: {', '.join('[' + ', '.join(b) + ']' for b in batches) or 'none'}.", f"Worker results: {ok} completed, {len(units) - ok} failed."]
    if graph.reasons:
        lines.append("Dependencies: " + "; ".join(f"{a}->{b}: {r}" for (a, b), r in sorted(graph.reasons.items())))
    if worktrees:
        lines.append("Worktrees: " + ", ".join(f"{k}={'created' if v.created else 'failed'}" for k, v in sorted(worktrees.items())))
    if warnings:
        lines.append("Warnings: " + "; ".join(warnings))
    if errors:
        lines.append("Errors: " + "; ".join(errors))
    return "\n".join(lines)


def delegate_with_lifecycle(work_units: Any, repo_path: str | Path | None = None, base_branch: str | None = None, *, delegate_func: DelegateFunc | None = None, worktree_root: str | Path = DEFAULT_WORKTREE_ROOT, merge_back: bool = True, ledger: DelegationLedger | None = None) -> LifecycleResult:
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
        dispatch_results, batches, dispatch_warnings = dispatch_work_units(units, graph, worktrees, delegate_func=delegate_func, ledger=ledger)
        warnings.extend(dispatch_warnings)
    except Exception as exc:
        dispatch_results = {}
        batches = graph.topological_batches() if graph.edges else []
        errors.append(f"dispatch failed: {exc}")
        if ledger:
            for unit in units:
                ledger.update(unit.id, status="failed", recommended_agent=unit.recommended_agent, error=str(exc))
    cleanup_results = cleanup_worktrees(worktrees, merge_back=merge_back) if worktrees else {}
    summary = aggregate_results(units, graph, batches, worktrees, dispatch_results, cleanup_results, warnings, errors)
    return LifecycleResult(units, graph, batches, worktrees, dispatch_results, cleanup_results, warnings, errors, summary, ledger)


__all__ = ["DEFAULT_WORKTREE_ROOT", "DelegateFunc", "DependencyGraph", "LifecycleResult", "WorkUnit", "WorktreeInfo", "aggregate_results", "build_dependency_graph", "cleanup_worktrees", "delegate_with_lifecycle", "dispatch_work_units", "normalize_work_units", "provision_worktrees"]
