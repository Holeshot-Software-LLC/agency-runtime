"""Work-unit normalization and dependency ordering.

What survived `test_delegation_lifecycle.py` when Job B was deleted. The cases
covering worktree provisioning, worker dispatch, the ledger, and result
aggregation went with the code they covered. These cover the two functions that
still have callers -- `core/evals/routing.py` and the operations dashboard --
including the bounds that keep a hostile turn from declaring unbounded work.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agency_runtime.core.delegation.lifecycle import (
    build_dependency_graph,
    normalize_work_units,
)
from agency_runtime.core.delegation.lifecycle_graph import (
    MAX_DEPENDENCIES_PER_UNIT,
    MAX_DESCRIPTION_CHARS,
    MAX_FILES_PER_UNIT,
    MAX_UNIT_ID_CHARS,
    MAX_WORK_UNITS,
)
from agency_runtime.core.delegation.lifecycle_types import WorkUnit


def test_normalize_work_units_preserves_contract_fields(tmp_path: Path) -> None:
    units = normalize_work_units(
        [
            {
                "id": "A-1",
                "description": "Edit README.md",
                "recommended_agent": "docs-agent",
            }
        ],
        repo_path=tmp_path,
    )

    assert units[0].id == "A-1"
    assert units[0].description == "Edit README.md"
    assert units[0].recommended_agent == "docs-agent"
    assert units[0].repo_path == tmp_path.resolve()


def test_normalize_work_units_preserves_explicit_dependencies() -> None:
    units = normalize_work_units(
        [
            {"id": "setup", "description": "Prepare inputs"},
            {
                "id": "run-report",
                "description": "Generate report",
                "depends_on": "setup",
            },
        ]
    )

    assert units[1].id == "run-report"
    assert units[1].depends_on == {"setup"}


def test_normalize_none_is_an_empty_workload() -> None:
    assert normalize_work_units(None) == []


@pytest.mark.parametrize("depends_on", ["", [""], [1], {"unit": "setup"}])
def test_normalize_work_units_rejects_invalid_dependencies(depends_on: object) -> None:
    with pytest.raises((TypeError, ValueError), match="depends_on"):
        normalize_work_units(
            [{"id": "run", "description": "Generate report", "depends_on": depends_on}]
        )


@pytest.mark.parametrize("files", [1, b"path.py", {"path": "file.py"}, [""]])
def test_normalize_work_units_rejects_invalid_file_lists(files: object) -> None:
    with pytest.raises((TypeError, ValueError), match="files"):
        normalize_work_units([{"id": "run", "description": "Generate report", "files": files}])


def test_normalize_work_units_rejects_malformed_ids_before_normalizing() -> None:
    with pytest.raises(ValueError, match="canonical id characters"):
        normalize_work_units([{"id": "A/1", "description": "First task"}])


def test_normalize_work_units_rejects_duplicate_explicit_ids() -> None:
    with pytest.raises(ValueError, match=r"duplicate work-unit id.*'A-1'"):
        normalize_work_units(
            [
                {"id": "A-1", "description": "First task"},
                {"id": "A-1", "description": "Second task"},
            ]
        )


def test_normalize_work_units_caps_an_arbitrary_iterable_before_materializing_it() -> None:
    consumed: list[int] = []

    def items():
        for index in range(100):
            consumed.append(index)
            yield {"id": f"unit-{index}", "description": f"Task {index}"}

    with pytest.raises(ValueError, match=f"more than {MAX_WORK_UNITS}"):
        normalize_work_units(items())

    assert len(consumed) == MAX_WORK_UNITS + 1


@pytest.mark.parametrize(
    "unit_id",
    ["", " leading", "trailing ", "contains space", "slash/id", 7, "x" * (MAX_UNIT_ID_CHARS + 1)],
)
def test_normalize_work_units_rejects_invalid_explicit_ids(unit_id: object) -> None:
    with pytest.raises((TypeError, ValueError), match="work-unit id"):
        normalize_work_units([{"id": unit_id, "description": "Task"}])


def test_missing_unit_ids_are_deterministic() -> None:
    payload = [{"description": "Deterministic task"}]

    first = normalize_work_units(payload)
    second = normalize_work_units(payload)

    assert first[0].id == second[0].id
    assert first[0].id.startswith("unit-1-")


def test_normalize_work_units_enforces_description_file_and_dependency_bounds() -> None:
    with pytest.raises(ValueError, match="description exceeds"):
        normalize_work_units([{"description": "x" * (MAX_DESCRIPTION_CHARS + 1)}])
    with pytest.raises(ValueError, match=f"more than {MAX_FILES_PER_UNIT}"):
        normalize_work_units(
            [
                {
                    "id": "unit",
                    "description": "Task",
                    "files": (f"file-{index}.py" for index in range(MAX_FILES_PER_UNIT + 1)),
                }
            ]
        )
    with pytest.raises(ValueError, match=f"more than {MAX_DEPENDENCIES_PER_UNIT}"):
        normalize_work_units(
            [
                {
                    "id": "unit",
                    "description": "Task",
                    "depends_on": (
                        f"dependency-{index}" for index in range(MAX_DEPENDENCIES_PER_UNIT + 1)
                    ),
                }
            ]
        )


def test_normalize_work_units_rejects_unsafe_prompt_metadata() -> None:
    with pytest.raises(ValueError, match="NUL"):
        normalize_work_units([{"description": "unsafe\x00task"}])
    with pytest.raises(ValueError, match="control characters"):
        normalize_work_units(
            [
                {
                    "description": "Task",
                    "recommended_agent": "unsafe\nagent",
                }
            ]
        )


def test_public_graph_boundary_rejects_more_than_sixteen_units() -> None:
    units = [WorkUnit(f"unit-{index}", "Task") for index in range(MAX_WORK_UNITS + 1)]

    with pytest.raises(ValueError, match=f"more than {MAX_WORK_UNITS}"):
        build_dependency_graph(units)


def test_dependency_graph_orders_overlapping_files(tmp_path: Path) -> None:
    units = normalize_work_units(
        [
            {"id": "one", "description": "Change shared.py", "files": ["shared.py"]},
            {
                "id": "two",
                "description": "Also change shared.py",
                "files": ["shared.py"],
            },
            {"id": "three", "description": "Change other.py", "files": ["other.py"]},
        ],
        repo_path=tmp_path,
    )

    graph = build_dependency_graph(units)

    assert graph.edges["one"] == {"two"}
    assert graph.topological_batches() == [["one", "three"], ["two"]]


def test_dependency_graph_honors_explicit_dependencies() -> None:
    units = normalize_work_units(
        [
            {"id": "publish", "description": "Publish report", "depends_on": ["build"]},
            {"id": "build", "description": "Build report"},
            {"id": "lint", "description": "Lint source"},
        ]
    )

    graph = build_dependency_graph(units)

    assert graph.edges["build"] == {"publish"}
    assert graph.reasons[("build", "publish")] == "explicit depends_on"
    assert graph.topological_batches() == [["build", "lint"], ["publish"]]


def test_dependency_graph_rejects_unknown_explicit_dependency() -> None:
    units = normalize_work_units(
        [{"id": "publish", "description": "Publish report", "depends_on": ["build"]}]
    )

    with pytest.raises(ValueError, match=r"'publish'.*unknown.*'build'"):
        build_dependency_graph(units)
