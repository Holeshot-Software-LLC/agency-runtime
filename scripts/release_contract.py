"""Shared declarative policy for canonical release sources and archives."""

from __future__ import annotations

import re
import stat
import unicodedata
import zipfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Protocol

MAX_ARCHIVE_MEMBERS = 4_096
MAX_ARCHIVE_MEMBER_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_TOTAL_BYTES = 128 * 1024 * 1024
MAX_ZIP_COMPRESSION_RATIO = 200
MAX_ARCHIVE_NAME_CHARS = 512
MAX_ARCHIVE_COMPONENT_BYTES = 255
MAX_ARCHIVE_COMPONENT_UTF16_UNITS = 255
MAX_ARCHIVE_NAME_BYTES = 2_048
MAX_ARTIFACT_PHYSICAL_BYTES = MAX_ARCHIVE_TOTAL_BYTES
MAX_TAR_CONTAINER_BYTES = MAX_ARCHIVE_TOTAL_BYTES + (MAX_ARCHIVE_MEMBERS * 1_024) + 10_240
MAX_TREE_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_RELEASE_ENTRIES = MAX_ARCHIVE_MEMBERS
MAX_RELEASE_FILE_BYTES = MAX_ARCHIVE_MEMBER_BYTES
MAX_RELEASE_TOTAL_BYTES = MAX_ARCHIVE_TOTAL_BYTES

CANONICAL_ZIP_SYSTEM = 3
CANONICAL_ZIP_VERSION = 20
CANONICAL_ZIP_METHOD = zipfile.ZIP_STORED
CANONICAL_WHEEL_MODE = stat.S_IFREG | 0o644
CANONICAL_RECORD_MODE = stat.S_IFREG | 0o664

WINDOWS_RESERVED_BASENAMES = frozenset(
    {
        "AUX",
        "CLOCK$",
        "CON",
        "NUL",
        "PRN",
        "COM¹",
        "COM²",
        "COM³",
        "LPT¹",
        "LPT²",
        "LPT³",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)
WINDOWS_INVALID_CHARS = frozenset('<>:"|?*')

SDIST_ROOT_SOURCE_FILES = frozenset(
    {
        ".editorconfig",
        ".gitattributes",
        "AGENTS.md",
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "MANIFEST.in",
        "README.md",
        "SECURITY.md",
        "THIRD_PARTY_NOTICES.md",
        "pyproject.toml",
    }
)
RELEASE_SOURCE_PATHS = tuple(
    sorted(
        {
            *SDIST_ROOT_SOURCE_FILES,
            "agency_runtime",
            "docs",
            "examples",
            "scripts",
            "tests",
        }
    )
)

_FULL_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


class _GitRunner(Protocol):
    def run_bytes(self, arguments: list[str]) -> bytes: ...


_GitOutput = Callable[..., bytes]


def safe_release_name(name: str) -> PurePosixPath:
    """Return one normalized archive path that is portable to Windows and POSIX."""

    if not name or len(name) > MAX_ARCHIVE_NAME_CHARS or "\x00" in name or "\\" in name:
        raise ValueError(f"unsafe archive member: {name}")
    raw = name[:-1] if name.endswith("/") else name
    parts = raw.split("/")
    windows = PureWindowsPath(raw)
    if (
        not raw
        or any(
            part in {"", ".", ".."}
            or part.endswith((".", " "))
            or part.split(".", 1)[0].rstrip(" ").upper() in WINDOWS_RESERVED_BASENAMES
            or any(ord(character) < 32 or character in WINDOWS_INVALID_CHARS for character in part)
            or len(part.encode("utf-8")) > MAX_ARCHIVE_COMPONENT_BYTES
            or len(part.encode("utf-16-le")) // 2 > MAX_ARCHIVE_COMPONENT_UTF16_UNITS
            for part in parts
        )
        or raw != unicodedata.normalize("NFC", raw)
        or PurePosixPath(raw).is_absolute()
        or windows.drive
        or windows.is_absolute()
    ):
        raise ValueError(f"unsafe archive member: {name}")
    return PurePosixPath(raw)


def is_release_source(name: str) -> bool:
    """Return whether a tracked path belongs in the canonical source distribution."""

    path = PurePosixPath(name)
    if name in SDIST_ROOT_SOURCE_FILES or name.startswith("agency_runtime/"):
        return True
    if name.startswith("scripts/"):
        return path.suffix == ".py"
    if name.startswith("tests/"):
        return path.suffix in {".mjs", ".py"}
    if name.startswith("docs/"):
        return path.suffix == ".md"
    if name.startswith("examples/"):
        return path.suffix in {".json", ".md", ".yaml", ".yml"}
    return False


def partition_release_payloads(names: set[str]) -> tuple[set[str], set[str]]:
    """Partition committed wheel-package files from supporting sdist inputs."""

    package = {name for name in names if name.startswith("agency_runtime/")}
    support = {name for name in names if is_release_source(name) and name not in package}
    return package, support


def _git_output(
    root: Path,
    arguments: list[str],
    *,
    git: _GitRunner | None,
) -> bytes:
    if git is None:
        raise ValueError(
            "distribution verification requires a clean Git checkout at the reviewed HEAD: "
            "trusted release Git session is required"
        )
    try:
        return git.run_bytes(arguments)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise ValueError(
            f"distribution verification requires a clean Git checkout at the reviewed HEAD: {exc}"
        ) from exc


def reviewed_checkout(
    root: Path,
    expected_commit: str,
    *,
    git: _GitRunner | None = None,
    git_output: _GitOutput | None = None,
) -> str:
    """Require one clean live checkout at an exact full reviewed commit."""

    if _FULL_OBJECT_ID.fullmatch(expected_commit) is None:
        raise ValueError("distribution verification requires one full lowercase commit object ID")
    output = _git_output if git_output is None else git_output
    resolved = (
        output(
            root,
            ["rev-parse", "--verify", f"{expected_commit}^{{commit}}"],
            git=git,
        )
        .decode("ascii")
        .strip()
    )
    if resolved != expected_commit:
        raise ValueError("distribution verification expected commit is not canonical")
    live = (
        output(
            root,
            ["rev-parse", "--verify", "HEAD^{commit}"],
            git=git,
        )
        .decode("ascii")
        .strip()
    )
    if live != expected_commit:
        raise ValueError(
            "distribution verification live HEAD does not match the reviewed commit: "
            f"expected {expected_commit}, found {live}"
        )
    dirty = output(
        root,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignore-submodules=none"],
        git=git,
    )
    if dirty:
        raise ValueError(
            "distribution verification requires a clean Git checkout with no tracked or "
            "untracked changes"
        )
    return expected_commit
