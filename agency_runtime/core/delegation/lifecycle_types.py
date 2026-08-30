"""The two shapes a turn's declared work units take.

`WorktreeInfo`, `WorktreePathIdentity` and `LifecycleResult` lived here too, and
went with Job B: nothing provisions a worktree or aggregates a worker's result
any more. `LifecycleResult` is also why this module imported the delegation
ledger, which is why deleting the ledger surfaced here first.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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


__all__ = ["DependencyGraph", "WorkUnit"]
