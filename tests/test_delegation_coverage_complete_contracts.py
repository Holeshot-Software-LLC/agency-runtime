"""Coverage-complete behavioral contracts for delegation value and adapter layers."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.delegation import (
    backend_security,
    lifecycle_graph,
)
from agency_runtime.core.delegation import (
    lifecycle as lifecycle_facade,
)
from agency_runtime.core.delegation.lifecycle_types import (
    DependencyGraph,
    WorkUnit,
)


class _RegistryBackend:
    def __init__(self, name: str, available: bool = False) -> None:
        self.name = name
        self.available = available
        self.calls: list[dict[str, Any]] = []

    def is_available(self) -> bool:
        return self.available

    def delegate(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {"backend": self.name, **kwargs}


def test_security_redaction_and_specialist_validation_cover_container_edges() -> None:
    assert backend_security.sensitive_variants(["", "secret"]) == ("secret",)
    assert backend_security.redact_value(("secret", {"secret": "ok"}), ("secret",)) == (
        "<task>",
        {"<task>": "ok"},
    )
    assert backend_security.specialist_prompt("task", "  ") == "task"
    with pytest.raises(TypeError, match="must be a string"):
        backend_security.specialist_prompt("task", 7)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="NUL"):
        backend_security.specialist_prompt("task", "bad\x00agent")
    with pytest.raises(ValueError, match="display-token limit"):
        backend_security.specialist_prompt(
            "task", "a" * (backend_security.MAX_SPECIALIST_CHARS + 1)
        )


class _EventStore:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = list(rows or [])
        self.recorded: list[dict[str, Any]] = []
        self.updated: list[tuple[str, dict[str, Any]]] = []

    def get_delegations(self, _trace_id: str) -> list[dict[str, Any]]:
        return self.rows

    def get_delegations_for_session(self, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        return self.rows

    def record_delegation(self, **kwargs: Any) -> str:
        self.recorded.append(kwargs)
        return f"event-{len(self.recorded)}"

    def update_delegation(self, event_id: str, **kwargs: Any) -> None:
        self.updated.append((event_id, kwargs))


def test_lifecycle_facade_private_compatibility_wrappers() -> None:
    assert lifecycle_facade._safe("A / B") == "A-B"
    lifecycle_facade._validate_unique_unit_ids([WorkUnit("one", "work")])
    signature = inspect.signature(lambda *, task: None)
    assert lifecycle_facade._signature_accepts(signature, task="work") is True


def test_graph_helpers_cover_scalar_mapping_paths_and_reachability(tmp_path: Path) -> None:
    class _OrderedSet(set[str]):
        def __iter__(self):
            return iter(sorted(set.copy(self)))

        def __sub__(self, other: set[str]) -> _OrderedSet:
            return type(self)(set.__sub__(self, other))

    mapping = {"units": 7, "description": "mapping task"}
    assert lifecycle_graph._items(mapping) == [mapping]
    assert lifecycle_graph._items(7) == [7]
    assert lifecycle_graph._description(object())
    assert lifecycle_graph._description({"description": "", "task": "fallback"}) == "fallback"
    assert lifecycle_graph._description(
        {"description": "", "task": "", "unit": "", "title": "", "summary": ""}
    ).startswith("{")
    assert lifecycle_graph._explicit_files({"files": "one.py"}) == {Path("one.py")}
    assert lifecycle_graph._explicit_dependencies({"depends_on": None}) == set()

    graph = DependencyGraph(edges={"a": {"b"}, "b": {"a", "c"}, "c": set()})
    assert lifecycle_graph._has_path(graph, "a", "c") is True
    assert lifecycle_graph._has_path(graph, "c", "a") is False
    duplicate_pending = DependencyGraph(
        edges={
            "a": _OrderedSet({"b", "c"}),
            "b": _OrderedSet(),
            "c": _OrderedSet({"b"}),
        }
    )
    assert lifecycle_graph._has_path(duplicate_pending, "a", "missing") is False

    converging = DependencyGraph(edges={"a": {"c"}, "b": {"c"}, "c": set()})
    assert converging.topological_batches() == [["a", "b"], ["c"]]

    existing = tmp_path / "existing.py"
    existing.write_text("pass\n", encoding="utf-8")
    units = lifecycle_graph.normalize_work_units(
        ["", f"Inspect {existing}"],
        repo_path=tmp_path,
        fallback_repo=None,
        git_root=lambda _path: tmp_path,
    )
    assert len(units) == 1
    assert Path("existing.py") in units[0].files


def test_work_unit_normalization_detects_only_existing_spaced_file_paths(
    tmp_path: Path,
) -> None:
    assert lifecycle_graph._path_match_is_embedded("/tmp/module.py", 0) is False
    nested = "/tmp/directory with spaces/module.py"
    assert lifecycle_graph._path_match_is_embedded(nested, nested.index("/module.py"))
    punctuation = "prefix-/module.py"
    assert lifecycle_graph._path_match_is_embedded(punctuation, punctuation.index("/module.py"))
    assignment = "--file=/tmp/module.py"
    assert not lifecycle_graph._path_match_is_embedded(assignment, assignment.index("/tmp"))
    url = "https://example.test/module.py"
    assert lifecycle_graph._path_match_is_embedded(url, url.index("//"))
    url_query = "https://example.test/route?next=C:/repo/module.py"
    assert lifecycle_graph._path_match_is_embedded(url_query, url_query.index("C:/repo"))
    url_fragment = "https://example.test/route#/tmp/module.py"
    assert lifecycle_graph._path_match_is_embedded(url_fragment, url_fragment.index("/tmp"))
    protocol_url = "//example.test/route?next=C:/repo/module.py"
    assert lifecycle_graph._path_match_is_embedded(protocol_url, 0)
    assert lifecycle_graph._path_match_is_embedded(protocol_url, protocol_url.index("C:/repo"))
    for wrapped_url in (
        "(//example.test/route?next=C:/repo/module.py)",
        "[link](//example.test/route#/tmp/module.py)",
        '"//example.test/route?next=C:/repo/module.py"',
    ):
        assert lifecycle_graph._path_match_is_embedded(wrapped_url, wrapped_url.index("//"))
        nested_root = "C:/repo" if "C:/repo" in wrapped_url else "/tmp"
        assert lifecycle_graph._path_match_is_embedded(wrapped_url, wrapped_url.index(nested_root))
    colon_delimited = "path:/tmp/module.py"
    assert not lifecycle_graph._path_match_is_embedded(
        colon_delimited, colon_delimited.index("/tmp")
    )

    spaced_file = tmp_path / "directory with spaces" / "module.py"
    spaced_file.parent.mkdir()
    spaced_file.write_text("pass\n", encoding="utf-8")

    units = lifecycle_graph.normalize_work_units(
        [f"Inspect {spaced_file.as_posix()}, then report."],
        repo_path=tmp_path,
        fallback_repo=None,
        git_root=lambda _path: tmp_path,
    )

    assert units[0].files == {Path("directory with spaces") / "module.py"}

    url_units = lifecycle_graph.normalize_work_units(
        [f"Review https://example.test/route?next={spaced_file.as_posix()}"],
        repo_path=tmp_path,
        fallback_repo=None,
        git_root=lambda _path: tmp_path,
    )
    assert url_units[0].files == set()

    network_probes: list[Path] = []
    protocol_units = lifecycle_graph.normalize_work_units(
        [f"Review //example.test/route?next={spaced_file.as_posix()}"],
        repo_path=None,
        fallback_repo=None,
        git_root=lambda path: network_probes.append(path) or tmp_path,
    )
    assert protocol_units[0].files == set()
    assert network_probes == []

    wrapped_protocol_descriptions = (
        f"Review (//example.test/route?next={spaced_file.as_posix()})",
        f"Review [link](//example.test/route#{spaced_file.as_posix()})",
        f'Review "//example.test/route?next={spaced_file.as_posix()}"',
    )
    for description in wrapped_protocol_descriptions:
        wrapped_units = lifecycle_graph.normalize_work_units(
            [description],
            repo_path=None,
            fallback_repo=None,
            git_root=lambda path: network_probes.append(path) or tmp_path,
        )
        assert wrapped_units[0].files == set()
    assert network_probes == []

    url_then_local_units = lifecycle_graph.normalize_work_units(
        [
            "Review "
            f"https://example.test/route?next={spaced_file.as_posix()} "
            f"then inspect {spaced_file.as_posix()}"
        ],
        repo_path=tmp_path,
        fallback_repo=None,
        git_root=lambda _path: tmp_path,
    )
    assert url_then_local_units[0].files == {Path("directory with spaces") / "module.py"}

    missing = tmp_path / "missing directory" / "planned.py"
    missing_units = lifecycle_graph.normalize_work_units(
        [f"Inspect {missing.as_posix()}, then report."],
        repo_path=tmp_path,
        fallback_repo=None,
        git_root=lambda _path: tmp_path,
    )
    assert missing_units[0].files == set()

    decoy = tmp_path / "directory.py"
    decoy.write_text("pass\n", encoding="utf-8")
    longest = tmp_path / "directory.py files" / "final.txt"
    longest.parent.mkdir()
    longest.write_text("done\n", encoding="utf-8")
    longest_units = lifecycle_graph.normalize_work_units(
        [f"Inspect {longest}, then report."],
        repo_path=tmp_path,
        fallback_repo=None,
        git_root=lambda _path: tmp_path,
    )
    assert longest_units[0].files == {Path("directory.py files") / "final.txt"}

    sibling_repo = tmp_path / "base-repo"
    sibling_repo.mkdir()
    spaced_repo = tmp_path / "base-repo copy"
    spaced_repo.mkdir()
    sibling_file = spaced_repo / "worker.py"
    sibling_file.write_text("pass\n", encoding="utf-8")
    probed: list[Path] = []

    def git_root(path: Path) -> Path:
        probed.append(path)
        return spaced_repo if path == sibling_file else sibling_repo

    sibling_units = lifecycle_graph.normalize_work_units(
        [f"Inspect {sibling_file}"],
        repo_path=None,
        fallback_repo=None,
        git_root=git_root,
    )
    assert probed[0] == sibling_file
    assert sibling_units[0].repo_path == spaced_repo
    assert sibling_units[0].files == {Path("worker.py")}

    late_file = tmp_path / "late file.py"
    late_file.write_text("pass\n", encoding="utf-8")
    prefix = str(tmp_path / "prefix")
    padded = (
        prefix + " " + ("x" * (lifecycle_graph._SPACED_PATH_WINDOW_CHARS + 1)) + f" {late_file}"
    )
    recovered, recovered_end, considered = lifecycle_graph._existing_spaced_file(
        padded,
        0,
        max_candidates=lifecycle_graph._SPACED_PATH_CANDIDATES_PER_MATCH,
    )
    assert recovered is None
    assert recovered_end == 0
    assert considered == 0

    nonexistent_candidates = (
        f"{tmp_path / 'missing directory' / 'first.py'} and "
        f"{tmp_path / 'other missing directory' / 'second.txt'}"
    )
    recovered, recovered_end, considered = lifecycle_graph._existing_spaced_file(
        nonexistent_candidates,
        0,
        max_candidates=lifecycle_graph._SPACED_PATH_CANDIDATES_PER_MATCH,
    )
    assert recovered is None
    assert recovered_end == 0
    assert considered == 2

    later_file = tmp_path / "later directory" / "final.py"
    later_file.parent.mkdir()
    later_file.write_text("pass\n", encoding="utf-8")
    earlier_tokens = " ".join(f"./planned{index}.py" for index in range(16))
    later_units = lifecycle_graph.normalize_work_units(
        [f"Inspect {earlier_tokens} and {later_file}"],
        repo_path=tmp_path,
        fallback_repo=None,
        git_root=lambda _path: tmp_path,
    )
    assert Path("later directory") / "final.py" in later_units[0].files

    later_compact = tmp_path / "later.py"
    later_compact.write_text("pass\n", encoding="utf-8")
    compact_units = lifecycle_graph.normalize_work_units(
        ["Inspect ./missing-path and ./later.py"],
        repo_path=tmp_path,
        fallback_repo=None,
        git_root=lambda _path: tmp_path,
    )
    assert compact_units[0].files == {Path("later.py")}

    probed: list[Path] = []
    bounded_description = " ".join(
        f"./missing-{index}" for index in range(lifecycle_graph._PATH_MATCH_LIMIT + 1)
    )
    lifecycle_graph.normalize_work_units(
        [bounded_description],
        repo_path=tmp_path,
        fallback_repo=None,
        git_root=lambda path: probed.append(path) or None,
    )
    assert len(probed) == lifecycle_graph._PATH_MATCH_LIMIT

    outside = tmp_path / "outside.py"
    outside.write_text("pass\n", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    normalized = lifecycle_graph.normalize_work_units(
        [{"description": "external", "files": [outside]}],
        repo_path=repo,
        fallback_repo=None,
        git_root=lambda _path: repo,
    )
    assert outside.resolve() in normalized[0].files

    unresolved = lifecycle_graph.normalize_work_units(
        ["Inspect ./path-without-extension"],
        repo_path=repo,
        fallback_repo=None,
        git_root=lambda _path: repo,
    )
    assert unresolved[0].files == set()


def test_graph_rejects_self_dependency_and_skips_nonoverlap_serializing() -> None:
    self_dependent = WorkUnit("same", "work", depends_on={"same"})
    with pytest.raises(ValueError, match="cannot depend on itself"):
        lifecycle_graph.build_dependency_graph([self_dependent])

    independent = [WorkUnit("one", "work"), WorkUnit("two", "work")]
    assert lifecycle_graph.build_dependency_graph(independent).edges == {
        "one": set(),
        "two": set(),
    }


def test_graph_does_not_reverse_explicit_dependency_for_shared_file(tmp_path: Path) -> None:
    shared = Path("shared.py")
    units = [
        WorkUnit(
            "consumer", "consume", repo_path=tmp_path, files={shared}, depends_on={"producer"}
        ),
        WorkUnit("producer", "produce", repo_path=tmp_path, files={shared}),
    ]

    graph = lifecycle_graph.build_dependency_graph(units)

    assert graph.edges == {"consumer": set(), "producer": {"consumer"}}
