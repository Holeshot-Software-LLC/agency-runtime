"""Work-unit normalization and dependency graph construction."""

from __future__ import annotations

import hashlib
import re
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
_PATH_SCAN_LIMIT = _PATH_MATCH_LIMIT * 4
_SPACED_PATH_WINDOW_CHARS = 4096
_SPACED_PATH_CANDIDATES_PER_MATCH = 4
MAX_WORK_UNITS = 16
MAX_UNIT_ID_CHARS = 80
# Leave bounded room for the unit id, absolute workdir, and lifecycle guidance
# added by call_delegate before a command backend applies its 16 KiB task cap.
MAX_DESCRIPTION_CHARS = 10 * 1024
MAX_RECOMMENDED_AGENT_CHARS = 128
MAX_FILES_PER_UNIT = 128
MAX_DEPENDENCIES_PER_UNIT = MAX_WORK_UNITS - 1
MAX_PATH_CHARS = 4096
_DEP_RE = re.compile(
    r"^\s*(?:after(?:\s+that)?|then|once)\b"
    r"|\bdepends?\s+on\b"
    r"|\b(?:use|using)\s+(?:the\s+)?(?:previous|prior|above|first)\b"
    r".{0,40}\boutput\b"
    r"|\bwhen\s+(?:the\s+)?(?:previous|prior|above|first)\b"
    r".{0,40}\bcompletes?\b",
    re.I,
)


def _path_match_is_embedded(description: str, start: int) -> bool:
    """Reject roots that are suffixes of a larger path or URL."""

    token_start = max(description.rfind(character, 0, start) for character in " \t\r\n") + 1
    token_prefix = description[token_start:start]
    network_prefix = chr(92) * 2
    if (
        description.startswith("//", start)
        or description.startswith(network_prefix, start)
        or "//" in token_prefix
        or network_prefix in token_prefix
    ):
        return True
    if start <= 0:
        return False
    previous = description[start - 1]
    if previous == ":":
        return description.startswith("//", start)
    return previous.isalnum() or previous in "_./\\@+-"


def _bounded_items(value: Iterable[Any], *, limit: int, field: str) -> list[Any]:
    items = list(islice(value, limit + 1))
    if len(items) > limit:
        raise ValueError(f"{field} cannot contain more than {limit} entries")
    return items


def _items(work_units: Any) -> list[Any]:
    if work_units is None:
        return []
    if isinstance(work_units, Mapping):
        units = work_units.get("units")
        if isinstance(units, Iterable) and not isinstance(units, (str, bytes, Mapping)):
            return _bounded_items(units, limit=MAX_WORK_UNITS, field="work_units")
        return [work_units]
    if isinstance(work_units, str):
        return [work_units]
    if isinstance(work_units, Iterable):
        return _bounded_items(work_units, limit=MAX_WORK_UNITS, field="work_units")
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
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.")
    return safe[:MAX_UNIT_ID_CHARS] or "unit"


def _stable_id(index: int, description: str) -> str:
    digest = hashlib.sha256(description.encode()).hexdigest()[:8]
    return f"unit-{index + 1}-{digest}"


def _validated_unit_id(value: Any, *, field: str = "work-unit id") -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field} must be non-empty and cannot have surrounding whitespace")
    if len(value) > MAX_UNIT_ID_CHARS:
        raise ValueError(f"{field} exceeds the {MAX_UNIT_ID_CHARS}-character limit")
    if value != safe_unit_id(value):
        raise ValueError(f"{field} must contain only canonical id characters")
    return value


def _validate_unit_bounds(unit: WorkUnit) -> None:
    _validated_unit_id(unit.id)
    if not isinstance(unit.description, str) or not unit.description.strip():
        raise ValueError("work-unit description must be a non-empty string")
    if len(unit.description) > MAX_DESCRIPTION_CHARS:
        raise ValueError(
            f"work-unit description exceeds the {MAX_DESCRIPTION_CHARS}-character limit"
        )
    if "\x00" in unit.description:
        raise ValueError("work-unit description must not contain NUL bytes")
    if not isinstance(unit.recommended_agent, str):
        raise TypeError("recommended_agent must be a string")
    if len(unit.recommended_agent) > MAX_RECOMMENDED_AGENT_CHARS:
        raise ValueError(
            f"recommended_agent exceeds the {MAX_RECOMMENDED_AGENT_CHARS}-character limit"
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in unit.recommended_agent):
        raise ValueError("recommended_agent must not contain control characters")
    if len(unit.files) > MAX_FILES_PER_UNIT:
        raise ValueError(f"files cannot contain more than {MAX_FILES_PER_UNIT} entries")
    for path in unit.files:
        if len(str(path)) > MAX_PATH_CHARS:
            raise ValueError(f"file path exceeds the {MAX_PATH_CHARS}-character limit")
    if len(unit.depends_on) > MAX_DEPENDENCIES_PER_UNIT:
        raise ValueError(f"depends_on cannot contain more than {MAX_DEPENDENCIES_PER_UNIT} entries")
    for dependency in unit.depends_on:
        _validated_unit_id(dependency, field="depends_on entry")


def validate_unique_unit_ids(units: Sequence[WorkUnit]) -> None:
    """Reject non-canonical or duplicate IDs at every public lifecycle boundary."""
    if len(units) > MAX_WORK_UNITS:
        raise ValueError(f"work_units cannot contain more than {MAX_WORK_UNITS} entries")
    seen: set[str] = set()
    duplicates: set[str] = set()
    for unit in units:
        _validate_unit_bounds(unit)
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
    for path in _bounded_items(value, limit=MAX_FILES_PER_UNIT, field="files"):
        if not isinstance(path, (str, Path)) or not str(path).strip():
            raise ValueError("files entries must be non-empty paths")
        if len(str(path)) > MAX_PATH_CHARS:
            raise ValueError(f"file path exceeds the {MAX_PATH_CHARS}-character limit")
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
    for dependency in _bounded_items(
        dependencies,
        limit=MAX_DEPENDENCIES_PER_UNIT,
        field="depends_on",
    ):
        normalized.add(_validated_unit_id(dependency, field="depends_on entry"))
    return normalized


def _existing_spaced_file(
    description: str,
    start: int,
    *,
    max_candidates: int,
) -> tuple[Path | None, int, int]:
    """Recover an existing file path when natural-language tokenizing split it."""

    tail = description[start : start + _SPACED_PATH_WINDOW_CHARS]
    longest: Path | None = None
    longest_end = 0
    considered = 0
    for match in islice(_FILE_BOUNDARY_RE.finditer(tail), max_candidates):
        considered += 1
        raw_path = tail[: match.end()].rstrip(".,);]}'\"")
        if not any(character.isspace() for character in raw_path):
            continue
        candidate = Path(raw_path).expanduser()
        if candidate.is_file():
            longest = candidate
            longest_end = start + match.end()
    return longest, longest_end, considered


def _unit_contract(
    index: int,
    item: Any,
) -> tuple[str, str, str, Path | None] | None:
    description = _description(item)
    if not description:
        return None
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise ValueError(
            f"work-unit description exceeds the {MAX_DESCRIPTION_CHARS}-character limit"
        )
    if "\x00" in description:
        raise ValueError("work-unit description must not contain NUL bytes")
    raw_id = _stable_id(index, description)
    if isinstance(item, Mapping) and "id" in item:
        raw_id = _validated_unit_id(item["id"])
    recommended_agent = (
        str(item.get("recommended_agent") or item.get("agent") or "").strip()
        if isinstance(item, Mapping)
        else ""
    )
    if len(recommended_agent) > MAX_RECOMMENDED_AGENT_CHARS:
        raise ValueError(
            f"recommended_agent exceeds the {MAX_RECOMMENDED_AGENT_CHARS}-character limit"
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in recommended_agent):
        raise ValueError("recommended_agent must not contain control characters")
    raw_repo = str(item["repo_path"]) if isinstance(item, Mapping) and item.get("repo_path") else ""
    if len(raw_repo) > MAX_PATH_CHARS:
        raise ValueError(f"repo_path exceeds the {MAX_PATH_CHARS}-character limit")
    repo = Path(raw_repo).expanduser().resolve() if raw_repo else None
    return description, raw_id, recommended_agent, repo


def _repo_fallback(
    repo_path: str | Path | None,
    fallback_repo: Path | None,
) -> Path | None:
    candidate = repo_path if repo_path is not None else fallback_repo
    if candidate is None:
        return None
    if len(str(candidate)) > MAX_PATH_CHARS:
        raise ValueError(f"repo_path exceeds the {MAX_PATH_CHARS}-character limit")
    return Path(candidate).expanduser().resolve()


def normalize_work_units(
    work_units: Any,
    repo_path: str | Path | None,
    *,
    fallback_repo: Path | None,
    git_root: GitRootFunc,
) -> list[WorkUnit]:
    """Normalize strings and mappings into stable work-unit value objects."""
    repo_fallback = _repo_fallback(repo_path, fallback_repo)
    normalized: list[WorkUnit] = []
    for index, item in enumerate(_items(work_units)):
        contract = _unit_contract(index, item)
        if contract is None:
            continue
        description, raw_id, recommended_agent, repo = contract
        files = _explicit_files(item)
        depends_on = _explicit_dependencies(item)
        consumed_until = 0
        path_matches = 0
        for match in islice(_PATH_RE.finditer(description), _PATH_SCAN_LIMIT):
            match_start = match.start("path")
            if match_start < consumed_until or _path_match_is_embedded(description, match_start):
                continue
            if path_matches >= _PATH_MATCH_LIMIT:
                break
            path_matches += 1
            compact_path = Path(match.group("path").rstrip(".,);]}'\"")).expanduser()
            spaced_file, spaced_end, _considered = _existing_spaced_file(
                description,
                match_start,
                max_candidates=_SPACED_PATH_CANDIDATES_PER_MATCH,
            )
            if spaced_file is not None:
                consumed_until = max(consumed_until, spaced_end)
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
        if len(normalized_files) > MAX_FILES_PER_UNIT:
            raise ValueError(f"files cannot contain more than {MAX_FILES_PER_UNIT} entries")
        normalized.append(
            WorkUnit(
                id=raw_id,
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
    "MAX_DEPENDENCIES_PER_UNIT",
    "MAX_DESCRIPTION_CHARS",
    "MAX_FILES_PER_UNIT",
    "MAX_PATH_CHARS",
    "MAX_RECOMMENDED_AGENT_CHARS",
    "MAX_UNIT_ID_CHARS",
    "MAX_WORK_UNITS",
    "build_dependency_graph",
    "normalize_work_units",
    "safe_unit_id",
    "validate_unique_unit_ids",
]
