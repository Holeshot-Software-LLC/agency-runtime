"""Work-unit normalization and dependency ordering.

What remains of the delegation lifecycle after Job B was deleted. Agency does not
plan work, provision worktrees, dispatch workers, or aggregate their results --
rule 5 says the native host alone decides whether to spawn. Two callers still
need to turn a turn's declared work units into a stable, ordered graph:
`core/evals/routing.py` and the operations dashboard.

Both functions are thin passes to `lifecycle_graph`, which is where the real
logic lives. This module stays as the import surface those callers already name.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from agency_runtime.core.delegation import lifecycle_graph as _graph
from agency_runtime.core.delegation.lifecycle_types import DependencyGraph, WorkUnit
from agency_runtime.core.git_runner import git_root as _git_root


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


__all__ = ["DependencyGraph", "WorkUnit", "build_dependency_graph", "normalize_work_units"]
