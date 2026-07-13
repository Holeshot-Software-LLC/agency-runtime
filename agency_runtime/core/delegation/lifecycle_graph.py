"""Work-unit normalization and dependency graph construction."""

from __future__ import annotations

import hashlib
import re
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from itertools import islice
from pathlib import Path
from typing import Any

from agency_runtime.core.delegation.lifecycle_types import DependencyGraph, WorkUnit

GitRootFunc = Callable[[Path], Path | None]

_PATH_RE = re.compile(
    r"(?P<path>(?:[A-Za-z]:[\\/]|~[\\/]|/|\.\.?[\\/])"
    r"[A-Za-z0-9_./\\@:+\-=]+)"
)
_FILE_SUFFIX = r"(?:py|js|jsx|ts|tsx|go|rs|java|rb|css|html|md|json|ya?ml|toml|sh|sql|txt)"
_FILE_RE = re.compile(rf"\.{_FILE_SUFFIX}$", re.I)
_FILE_BOUNDARY_RE = re.compile(
    rf"\.{_FILE_SUFFIX}(?![A-Za-z0-9_./\\@:+\-=])",
    re.I,
)
_PATH_MATCH_LIMIT = 32
_SPACED_PATH_WINDOW_CHARS = 4096
_SPACED_PATH_CANDIDATES_PER_MATCH = 4
_DEP_RE = re.compile(
    r"^\s*(?:after(?:\s+that)?|then|once)\b"
    r"|\bdepends?\s+on\b"
    r"|\b(?:use|using)\s+(?:the\s+)?(?:previous|prior|above|first)\b"
    r".{0,40}\boutput\b"
    r"|\bwhen\s+(?:the\s+)?(?:previous|prior|above|first)\b"
    r".{0,40}\bcompletes?\b",
    re.I,
)


def _items(work_units: Any) -> list[Any]:
    if work_units is None:
        return []
    if isinstance(work_units, Mapping):
        units = work_units.get("units")
        if isinstance(units, Iterable) and not isinstance(units, (str, bytes, Mapping)):
            return list(units)
        return [work_units]
    if isinstance(work_units, str):
        return [work_units]
    if isinstance(work_units, Iterable):
        return list(work_units)
    return [work_units]


def _description(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, Mapping):
        for key in ("description", "task", "unit", "title", "summary"):
            if item.get(key):
                return str(item[key]).strip()
    return str(item).strip()


def safe_unit_id(value: str) -> str:
    """Normalize an identifier for result keys, branches, and directory names."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.")[:80]
    return safe or f"unit-{uuid.uuid4().hex[:8]}"


def _stable_id(index: int, description: str) -> str:
    digest = hashlib.sha256(description.encode()).hexdigest()[:8]
    return f"unit-{index + 1}-{digest}"


def validate_unique_unit_ids(units: Sequence[WorkUnit]) -> None:
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


def _has_path(graph: DependencyGraph, source: str, target: str) -> bool:
    """Return whether existing dependency edges already serialize two nodes."""
    pending = list(graph.edges.get(source, set()))
    visited: set[str] = set()
    while pending:
        node = pending.pop()
        if node == target:
            return True
        if node in visited:
            continue
        visited.add(node)
        pending.extend(graph.edges.get(node, set()) - visited)
    return False


def _explicit_files(item: Any) -> set[Path]:
    if not isinstance(item, Mapping):
        return set()
    value = item.get("files") or item.get("paths") or []
    if isinstance(value, (str, Path)):
        value = [value]
    if not isinstance(value, Iterable) or isinstance(value, (bytes, Mapping)):
        raise TypeError("files must be a path or iterable of paths")
    paths: set[Path] = set()
    for path in value:
        if not isinstance(path, (str, Path)) or not str(path).strip():
            raise ValueError("files entries must be non-empty paths")
        paths.add(Path(path).expanduser())
    return paths


def _explicit_dependencies(item: Any) -> set[str]:
    if not isinstance(item, Mapping) or "depends_on" not in item:
        return set()
    value = item.get("depends_on")
    if value is None:
        return set()
    if isinstance(value, str):
        dependencies: Iterable[Any] = (value,)
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, Mapping)):
        dependencies = value
    else:
        raise TypeError("depends_on must be a work-unit id or iterable of ids")
    normalized: set[str] = set()
    for dependency in dependencies:
        if not isinstance(dependency, str) or not dependency.strip():
            raise ValueError("depends_on entries must be non-empty work-unit ids")
        normalized.add(safe_unit_id(dependency))
    return normalized


def _existing_spaced_file(
    description: str,
    start: int,
    *,
    max_candidates: int,
) -> tuple[Path | None, int]:
    """Recover an existing file path when natural-language tokenizing split it."""

    tail = description[start : start + _SPACED_PATH_WINDOW_CHARS]
    longest: Path | None = None
    considered = 0
    for match in islice(_FILE_BOUNDARY_RE.finditer(tail), max_candidates):
        considered += 1
        raw_path = tail[: match.end()].rstrip(".,);]}'\"")
        if not any(character.isspace() for character in raw_path):
            continue
        candidate = Path(raw_path).expanduser()
        if candidate.is_file():
            longest = candidate
    return longest, considered


def normalize_work_units(
    work_units: Any,
    repo_path: str | Path | None,
    *,
    fallback_repo: Path | None,
    git_root: GitRootFunc,
) -> list[WorkUnit]:
    """Normalize strings and mappings into stable work-unit value objects."""
    repo_fallback = (
        Path(repo_path).expanduser().resolve()
        if repo_path
        else (fallback_repo.resolve() if fallback_repo else None)
    )
    normalized: list[WorkUnit] = []
    for index, item in enumerate(_items(work_units)):
        description = _description(item)
        if not description:
            continue
        raw_id = (
            str(item.get("id"))
            if isinstance(item, Mapping) and item.get("id")
            else _stable_id(index, description)
        )
        recommended_agent = (
            str(item.get("recommended_agent") or item.get("agent") or "")
            if isinstance(item, Mapping)
            else ""
        )
        repo = (
            Path(str(item["repo_path"])).expanduser().resolve()
            if isinstance(item, Mapping) and item.get("repo_path")
            else None
        )
        files = _explicit_files(item)
        depends_on = _explicit_dependencies(item)
        for match in islice(_PATH_RE.finditer(description), _PATH_MATCH_LIMIT):
            compact_path = Path(match.group("path").rstrip(".,);]}'\"")).expanduser()
            spaced_file, _considered = _existing_spaced_file(
                description,
                match.start("path"),
                max_candidates=_SPACED_PATH_CANDIDATES_PER_MATCH,
            )
            path = spaced_file or compact_path
            repo = repo or git_root(path)
            if (
                spaced_file is not None
                or _FILE_RE.search(str(path))
                or (path.exists() and path.is_file())
            ):
                files.add(path)
        repo = repo or repo_fallback
        normalized_files: set[Path] = set()
        for file_path in files:
            absolute = file_path if file_path.is_absolute() else ((repo or Path.cwd()) / file_path)
            try:
                resolved = absolute.resolve()
                normalized_files.add(resolved.relative_to(repo) if repo else resolved)
            except ValueError:
                normalized_files.add(absolute.resolve())
        normalized.append(
            WorkUnit(
                id=safe_unit_id(raw_id),
                description=description,
                recommended_agent=recommended_agent,
                repo_path=repo,
                files=normalized_files,
                depends_on=depends_on,
                raw=item,
            )
        )
    validate_unique_unit_ids(normalized)
    return normalized


def build_dependency_graph(units: Sequence[WorkUnit]) -> DependencyGraph:
    """Build explicit and safely inferred dependency edges between units."""
    validate_unique_unit_ids(units)
    graph = DependencyGraph(edges={unit.id: set() for unit in units})
    known_ids = set(graph.edges)
    for unit in units:
        unknown = sorted(unit.depends_on - known_ids)
        if unknown:
            rendered = ", ".join(repr(unit_id) for unit_id in unknown)
            raise ValueError(
                f"work unit {unit.id!r} depends on unknown work-unit id(s): {rendered}"
            )
        if unit.id in unit.depends_on:
            raise ValueError(f"work unit {unit.id!r} cannot depend on itself")
        for predecessor_id in sorted(unit.depends_on):
            graph.edges[predecessor_id].add(unit.id)
            graph.reasons[(predecessor_id, unit.id)] = "explicit depends_on"

    for index, unit in enumerate(units):
        if index > 0 and _DEP_RE.search(unit.description):
            predecessor = units[index - 1].id
            graph.edges[predecessor].add(unit.id)
            graph.reasons.setdefault(
                (predecessor, unit.id),
                "sequencing language in work-unit description",
            )

    # Reject contradictory declared/sequencing dependencies before adding
    # conservative file serialization.
    graph.topological_batches()

    for index, left in enumerate(units):
        for right in units[index + 1 :]:
            if not (
                left.repo_path
                and right.repo_path
                and left.repo_path == right.repo_path
                and left.files
                and right.files
            ):
                continue
            shared = left.files & right.files
            if shared:
                # An explicit or inferred path already provides serialization.
                # In particular, do not reverse an explicit dependency merely
                # because the consumer appeared first in caller input.
                if _has_path(graph, left.id, right.id) or _has_path(
                    graph,
                    right.id,
                    left.id,
                ):
                    continue
                graph.edges[left.id].add(right.id)
                graph.reasons.setdefault(
                    (left.id, right.id),
                    f"shared file(s): {', '.join(sorted(str(path) for path in shared))}",
                )

    # Validate before any worktree allocation. Explicit dependencies can conflict
    # with inferred sequencing or file-overlap edges.
    graph.topological_batches()
    return graph


__all__ = [
    "build_dependency_graph",
    "normalize_work_units",
    "safe_unit_id",
    "validate_unique_unit_ids",
]
