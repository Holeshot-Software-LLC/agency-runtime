"""Shared declarative policy for canonical release sources and archives."""

from __future__ import annotations

import re
import stat
import struct
import sys
import sysconfig
import unicodedata
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
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
CANONICAL_LF_WHEEL_GENERATED_FILES = frozenset(
    {
        "METADATA",
        "RECORD",
        "WHEEL",
        "entry_points.txt",
        "top_level.txt",
    }
)
CANONICAL_LF_SDIST_GENERATED_FILES = frozenset(
    {
        "PKG-INFO",
        "agency_runtime.egg-info/PKG-INFO",
        "agency_runtime.egg-info/SOURCES.txt",
        "agency_runtime.egg-info/dependency_links.txt",
        "agency_runtime.egg-info/entry_points.txt",
        "agency_runtime.egg-info/requires.txt",
        "agency_runtime.egg-info/top_level.txt",
        "setup.cfg",
    }
)

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

DISTRIBUTION_LICENSE_FILES = (
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
)
IMMUTABLE_THIRD_PARTY_FILE_SHA256: tuple[tuple[str, str], ...] = ()

ARTIFACT_SET_PORTABLE = "portable"
ARTIFACT_SET_WINDOWS_X64 = "windows-x64"
ARTIFACT_SET_RELEASE = "release"
ARTIFACT_SET_HOST = "host"
ARTIFACT_SETS = frozenset(
    {
        ARTIFACT_SET_PORTABLE,
        ARTIFACT_SET_WINDOWS_X64,
        ARTIFACT_SET_RELEASE,
    }
)


@dataclass(frozen=True, slots=True)
class WheelProfile:
    """One exact wheel filename, metadata, and native-payload contract."""

    name: str
    tag: str
    root_is_purelib: bool
    includes_native_executable: bool


PORTABLE_WHEEL_PROFILE = WheelProfile(
    name=ARTIFACT_SET_PORTABLE,
    tag="py3-none-any",
    root_is_purelib=True,
    includes_native_executable=False,
)
WINDOWS_X64_WHEEL_PROFILE = WheelProfile(
    name=ARTIFACT_SET_WINDOWS_X64,
    tag="py3-none-win_amd64",
    root_is_purelib=False,
    includes_native_executable=False,
)
WHEEL_PROFILES = {
    PORTABLE_WHEEL_PROFILE.name: PORTABLE_WHEEL_PROFILE,
    WINDOWS_X64_WHEEL_PROFILE.name: WINDOWS_X64_WHEEL_PROFILE,
}


def host_wheel_profile(
    *,
    platform_name: str | None = None,
    pointer_size: int | None = None,
    platform_tag: str | None = None,
) -> WheelProfile:
    """Return the wheel profile fixed by this build interpreter and host."""

    runtime_platform = sys.platform if platform_name is None else platform_name
    runtime_pointer_size = struct.calcsize("P") if pointer_size is None else pointer_size
    runtime_platform_tag = sysconfig.get_platform() if platform_tag is None else platform_tag
    if (
        runtime_platform == "win32"
        and runtime_pointer_size == 8
        and runtime_platform_tag.casefold().replace("_", "-") == "win-amd64"
    ):
        return WINDOWS_X64_WHEEL_PROFILE
    return PORTABLE_WHEEL_PROFILE


def wheel_profiles_for_artifact_set(artifact_set: str) -> tuple[WheelProfile, ...]:
    """Return the exact ordered wheel profiles required by an artifact set."""

    if artifact_set == ARTIFACT_SET_RELEASE:
        return PORTABLE_WHEEL_PROFILE, WINDOWS_X64_WHEEL_PROFILE
    try:
        return (WHEEL_PROFILES[artifact_set],)
    except KeyError as exc:
        raise ValueError(f"unsupported distribution artifact set: {artifact_set}") from exc


def wheel_filename(version: str, profile: WheelProfile) -> str:
    """Return one exact normalized Agency Runtime wheel filename."""

    return f"agency_runtime-{version}-{profile.tag}.whl"


def distribution_artifact_names(version: str, artifact_set: str) -> tuple[str, ...]:
    """Return the ordered exact filenames for one verified artifact set."""

    wheels = tuple(
        wheel_filename(version, profile)
        for profile in wheel_profiles_for_artifact_set(artifact_set)
    )
    return (*wheels, f"agency_runtime-{version}.tar.gz")


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
        "setup.py",
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
