"""Value objects shared by the delegation lifecycle components."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agency_runtime.core.delegation.ledger import DelegationLedger

if TYPE_CHECKING:
    from agency_runtime.core.private_paths import PrivateDirectoryIdentity


@dataclass(slots=True)
class WorkUnit:
    """Normalized delegated work unit."""

    id: str
    description: str
    recommended_agent: str = ""
    repo_path: Path | None = None
    files: set[Path] = field(default_factory=set)
    depends_on: set[str] = field(default_factory=set)
    raw: Any = None


@dataclass(frozen=True, slots=True)
class WorktreePathIdentity:
    """Filesystem identity receipt for a lifecycle-owned directory."""

    path: Path
    device: int
    inode: int


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
    worktree_identity: WorktreePathIdentity | None = field(default=None, repr=False)
    run_root_identity: WorktreePathIdentity | None = field(default=None, repr=False)
    run_parent_identity: WorktreePathIdentity | None = field(default=None, repr=False)
    run_private_identity: PrivateDirectoryIdentity | None = field(default=None, repr=False)
    repo_scoped_root: bool = False


@dataclass(slots=True)
class DependencyGraph:
    """Directed dependency graph where edges point predecessor to successor."""

    edges: dict[str, set[str]] = field(default_factory=dict)
    reasons: dict[tuple[str, str], str] = field(default_factory=dict)

    def predecessors(self) -> dict[str, set[str]]:
        """Return incoming edges for every graph node."""
        predecessors = {node: set() for node in self.edges}
        for source, children in self.edges.items():
            predecessors.setdefault(source, set())
            for child in children:
                predecessors.setdefault(child, set()).add(source)
        return predecessors

    def topological_batches(self) -> list[list[str]]:
        """Return deterministic parallel batches or reject a cyclic graph."""
        predecessors = self.predecessors()
        children = {node: set(self.edges.get(node, set())) for node in predecessors}
        ready = deque(sorted(node for node, incoming in predecessors.items() if not incoming))
        emitted: set[str] = set()
        batches: list[list[str]] = []
        while ready:
            batch = sorted(ready)
            ready.clear()
            batches.append(batch)
            for node in batch:
                emitted.add(node)
                for child in sorted(children.get(node, set())):
                    predecessors[child].discard(node)
                    # A child becomes ready exactly once: the iteration that removes
                    # its final predecessor. ``children`` and incoming edges are sets,
                    # so duplicate-ready/emitted guards were unreachable.
                    if not predecessors[child]:
                        ready.append(child)
        if len(emitted) != len(predecessors):
            cyclic = sorted(set(predecessors) - emitted)
            raise ValueError(f"dependency graph contains a cycle: {cyclic}")
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
    runtime_enabled: bool = True
    bypassed: bool = False

    def as_dict(self) -> dict[str, Any]:
        """Render the portable delegation lifecycle contract."""
        return {
            "work_units": [
                {
                    "id": unit.id,
                    "description": unit.description,
                    "recommended_agent": unit.recommended_agent,
                    "repo_path": str(unit.repo_path) if unit.repo_path else None,
                    "files": sorted(str(path) for path in unit.files),
                    "depends_on": sorted(unit.depends_on),
                }
                for unit in self.work_units
            ],
            "dependency_graph": {
                "edges": {
                    node: sorted(children) for node, children in self.dependency_graph.edges.items()
                },
                "reasons": {
                    f"{source}->{target}": reason
                    for (
                        source,
                        target,
                    ), reason in self.dependency_graph.reasons.items()
                },
            },
            "batches": self.batches,
            "worktrees": {
                unit_id: {
                    "repo_path": str(info.repo_path),
                    "path": str(info.path),
                    "branch": info.branch,
                    "base_branch": info.base_branch,
                    "base_sha": info.base_sha,
                    "created": info.created,
                    "dirty_repo": info.dirty_repo,
                    "warnings": info.warnings,
                    "errors": info.errors,
                }
                for unit_id, info in self.worktrees.items()
            },
            "dispatch_results": self.dispatch_results,
            "cleanup_results": self.cleanup_results,
            "warnings": self.warnings,
            "errors": self.errors,
            "summary": self.summary,
            "ledger": self.ledger.as_dict() if self.ledger else None,
            "runtime_enabled": self.runtime_enabled,
            "bypassed": self.bypassed,
        }


__all__ = [
    "DependencyGraph",
    "LifecycleResult",
    "WorkUnit",
    "WorktreeInfo",
    "WorktreePathIdentity",
]
