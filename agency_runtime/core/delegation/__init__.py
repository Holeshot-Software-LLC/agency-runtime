"""Bounded process execution and work-unit ordering.

The package name is historical. Job B -- Agency planning work units, spawning
workers, provisioning worktrees, and demanding receipts -- was deleted across
2026-08-09 and 2026-08-11; rule 5 says the native host alone decides whether to
spawn. What is left is infrastructure that happened to be written here:

* `backends.run_bounded_process` -- the hardened subprocess primitive the
  installer, the host canary, and the Codex hook-trust inspector all use.
* `events` -- work-unit observation on the live hook path.
* `native_labels` -- Codex task-name correlation.
* `lifecycle` / `lifecycle_graph` -- normalizing and ordering a turn's declared
  work units, for the routing eval and the dashboard.

Nothing here executes an agent.
"""

from agency_runtime.core.delegation.backends import (
    BoundedProcessResult,
    run_bounded_process,
)
from agency_runtime.core.delegation.lifecycle import (
    DependencyGraph,
    WorkUnit,
    build_dependency_graph,
    normalize_work_units,
)

__all__ = [
    "BoundedProcessResult",
    "DependencyGraph",
    "WorkUnit",
    "build_dependency_graph",
    "normalize_work_units",
    "run_bounded_process",
]
