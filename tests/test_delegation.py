"""Work-unit normalization and dependency ordering, from the original suite.

The dispatch, ledger, and backend-registry cases here went with Job B.
"""

from __future__ import annotations

import pytest

from agency_runtime.core.delegation.lifecycle import (
    build_dependency_graph,
    normalize_work_units,
)
from agency_runtime.core.delegation.lifecycle_types import DependencyGraph


def test_normalize_string():
    units = normalize_work_units("fix the bug in auth.py")
    assert len(units) == 1
    assert "fix" in units[0].description.lower()


def test_normalize_list_of_strings():
    units = normalize_work_units(["fix bug", "add tests", "update docs"])
    assert len(units) == 3
    assert units[0].id != units[1].id


def test_normalize_detect_work_units_output():
    raw = {
        "count": 2,
        "units": ["fix the login bug", "update the README"],
        "delegate": True,
    }
    units = normalize_work_units(raw)
    assert len(units) == 2


def test_normalize_with_recommended_agent():
    units = normalize_work_units(
        [
            {"description": "review code", "recommended_agent": "code-reviewer"},
        ]
    )
    assert len(units) == 1
    assert units[0].recommended_agent == "code-reviewer"


def test_dependency_graph_no_deps():
    units = normalize_work_units(["task a", "task b", "task c"])
    graph = build_dependency_graph(units)
    batches = graph.topological_batches()
    assert len(batches) == 1  # all independent
    assert len(batches[0]) == 3


def test_dependency_graph_cycle_detection():
    graph = DependencyGraph()
    graph.edges = {"a": {"b"}, "b": {"a"}}  # cycle
    with pytest.raises(ValueError):
        graph.topological_batches()
