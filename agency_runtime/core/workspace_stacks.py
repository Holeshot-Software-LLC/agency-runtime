"""Deterministic, bounded repository stack detection.

Routing reads the *intent* of an ask; this module supplies the repository
evidence side: a bounded marker-file scan of the working directory that names
the stacks present (``python``, ``typescript``, ``go``, ...). The result is
surfaced to inference through the staffing context document — it is evidence
for the planner and recruiter to read, never a selector. Detection is
deterministic and read-only: unreadable directories, oversized manifests, and
malformed JSON all degrade to "no signal" rather than failing the turn.
"""

from __future__ import annotations

import json
from pathlib import Path

MAX_SCAN_DEPTH = 2
MAX_ENTRIES_PER_DIRECTORY = 512
MAX_MANIFEST_BYTES = 256 * 1024

# Marker file name -> stack identifiers it proves. Names are matched exactly
# (case-insensitive) against directory entries down to MAX_SCAN_DEPTH.
_MARKER_FILES: dict[str, tuple[str, ...]] = {
    "pyproject.toml": ("python",),
    "setup.py": ("python",),
    "requirements.txt": ("python",),
    "pipfile": ("python",),
    "go.mod": ("go",),
    "cargo.toml": ("rust",),
    "composer.json": ("php",),
    "pom.xml": ("java",),
    "build.gradle": ("java",),
    "build.gradle.kts": ("kotlin",),
    "gemfile": ("ruby",),
    "mix.exs": ("elixir",),
    "package.json": ("javascript",),
    "tsconfig.json": ("typescript",),
}

_MARKER_SUFFIXES: dict[str, tuple[str, ...]] = {
    ".csproj": ("dotnet",),
    ".sln": ("dotnet",),
}

# package-manager manifests whose dependency tables prove framework stacks the
# roster's typed contracts use (e.g. the laravel/livewire specialists).
_DEPENDENCY_STACKS: dict[str, dict[str, str]] = {
    "composer.json": {
        "laravel/framework": "laravel",
        "livewire/livewire": "livewire",
    },
    "package.json": {
        "react": "react",
        "vue": "vue",
        "svelte": "svelte",
        "next": "nextjs",
    },
}


def _dependency_names(path: Path) -> frozenset[str]:
    try:
        if path.stat().st_size > MAX_MANIFEST_BYTES:
            return frozenset()
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return frozenset()
    if not isinstance(payload, dict):
        return frozenset()
    names: set[str] = set()
    for table in ("require", "require-dev", "dependencies", "devDependencies"):
        section = payload.get(table)
        if isinstance(section, dict):
            names.update(str(key).casefold() for key in section)
    return frozenset(names)


def detect_workspace_stacks(root: str | Path | None = None) -> tuple[str, ...]:
    """Return the sorted stacks proven by marker files under ``root``.

    ``root`` defaults to the process working directory — for hook-driven
    turns that is the repository the host session runs in. The scan is
    bounded (depth, entries, manifest bytes) and never raises.
    """

    try:
        base = Path(root) if root is not None else Path.cwd()
    except OSError:
        return ()
    stacks: set[str] = set()
    pending: list[tuple[Path, int]] = [(base, 0)]
    while pending:
        directory, depth = pending.pop()
        try:
            entries = sorted(directory.iterdir())[:MAX_ENTRIES_PER_DIRECTORY]
        except OSError:
            continue
        for entry in entries:
            name = entry.name.casefold()
            try:
                is_file = entry.is_file()
                is_dir = entry.is_dir()
            except OSError:
                continue
            if is_file:
                stacks.update(_MARKER_FILES.get(name, ()))
                for suffix, proved in _MARKER_SUFFIXES.items():
                    if name.endswith(suffix):
                        stacks.update(proved)
                if name in _DEPENDENCY_STACKS:
                    dependencies = _dependency_names(entry)
                    for package, stack in _DEPENDENCY_STACKS[name].items():
                        if package in dependencies:
                            stacks.add(stack)
            elif is_dir and depth < MAX_SCAN_DEPTH and not name.startswith("."):
                if name not in {"node_modules", "vendor", "__pycache__", "venv"}:
                    pending.append((entry, depth + 1))
    return tuple(sorted(stacks))


__all__ = ["detect_workspace_stacks"]
