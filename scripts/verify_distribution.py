"""Verify built Agency Runtime wheel and source distribution contents."""

from __future__ import annotations

import argparse
import ast
import base64
import configparser
import csv
import hashlib
import io
import os
import re
import stat
import struct
import sys
import tarfile
import time
import zipfile
import zlib
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from email import policy
from email.message import Message
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from packaging.markers import InvalidMarker, Marker
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

try:  # Support both ``python -m scripts...`` and direct script execution.
    from scripts.release_contract import (
        CANONICAL_RECORD_MODE,
        CANONICAL_WHEEL_MODE,
        CANONICAL_ZIP_METHOD,
        CANONICAL_ZIP_SYSTEM,
        CANONICAL_ZIP_VERSION,
        MAX_ARCHIVE_COMPONENT_BYTES,
        MAX_ARCHIVE_MEMBER_BYTES,
        MAX_ARCHIVE_MEMBERS,
        MAX_ARCHIVE_NAME_BYTES,
        MAX_ARCHIVE_NAME_CHARS,
        MAX_ARCHIVE_TOTAL_BYTES,
        MAX_ARTIFACT_PHYSICAL_BYTES,
        MAX_RELEASE_ENTRIES,
        MAX_RELEASE_FILE_BYTES,
        MAX_RELEASE_TOTAL_BYTES,
        MAX_TAR_CONTAINER_BYTES,
        MAX_TREE_MANIFEST_BYTES,
        MAX_ZIP_COMPRESSION_RATIO,
        RELEASE_SOURCE_PATHS,
        is_release_source,
        partition_release_payloads,
        reviewed_checkout,
        safe_release_name,
    )
    from scripts.release_git import ReleaseGit, ReleaseGitError
except ModuleNotFoundError as exc:  # pragma: no cover - direct-script compatibility
    if exc.name != "scripts":
        raise
    from release_contract import (  # type: ignore[no-redef]
        CANONICAL_RECORD_MODE,
        CANONICAL_WHEEL_MODE,
        CANONICAL_ZIP_METHOD,
        CANONICAL_ZIP_SYSTEM,
        CANONICAL_ZIP_VERSION,
        MAX_ARCHIVE_COMPONENT_BYTES,
        MAX_ARCHIVE_MEMBER_BYTES,
        MAX_ARCHIVE_MEMBERS,
        MAX_ARCHIVE_NAME_BYTES,
        MAX_ARCHIVE_NAME_CHARS,
        MAX_ARCHIVE_TOTAL_BYTES,
        MAX_ARTIFACT_PHYSICAL_BYTES,
        MAX_RELEASE_ENTRIES,
        MAX_RELEASE_FILE_BYTES,
        MAX_RELEASE_TOTAL_BYTES,
        MAX_TAR_CONTAINER_BYTES,
        MAX_TREE_MANIFEST_BYTES,
        MAX_ZIP_COMPRESSION_RATIO,
        RELEASE_SOURCE_PATHS,
        is_release_source,
        partition_release_payloads,
        reviewed_checkout,
        safe_release_name,
    )
    from release_git import ReleaseGit, ReleaseGitError  # type: ignore[no-redef]

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 release environment
    import tomli as tomllib

REQUIRED_PACKAGE_FILES = {
    "agency_runtime/core/companion_policy.yaml",
    "agency_runtime/core/config_defaults.yaml",
    "agency_runtime/core/canary.py",
    "agency_runtime/core/configuration.py",
    "agency_runtime/core/dashboard_runtime.py",
    "agency_runtime/core/dashboard_service.py",
    "agency_runtime/core/evals/data/__init__.py",
    "agency_runtime/core/evals/data/routing_v1.py",
    "agency_runtime/dashboard/__init__.py",
    "agency_runtime/dashboard/app.css",
    "agency_runtime/dashboard/app.js",
    "agency_runtime/dashboard/charts.js",
    "agency_runtime/dashboard/index.html",
}
REQUIRED_SDIST_FILES = {
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
    "docs/RELEASE_CHECKLIST.md",
    "docs/THREAT_MODEL.md",
    "examples/rosters/agents.json",
    "pyproject.toml",
    "scripts/verify_distribution.py",
    "scripts/build_distributions.py",
    "scripts/canonicalize_distributions.py",
    "scripts/release_contract.py",
    "scripts/release_git.py",
    "tests/dashboard_ui.test.mjs",
    *REQUIRED_PACKAGE_FILES,
}
REQUIRED_CLASSIFIERS = {
    "Operating System :: Microsoft :: Windows",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
}
FORBIDDEN_PARTS = {
    ".coverage",
    ".DS_Store",
    ".env",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "agency.yaml",
    "build",
    "dist",
}
FORBIDDEN_SUFFIXES = {".db", ".egg-link", ".pyc", ".pyo", ".sqlite", ".sqlite3"}
WHEEL_METADATA_FILES = {
    "METADATA",
    "RECORD",
    "WHEEL",
    "entry_points.txt",
    "licenses/LICENSE",
    "top_level.txt",
}
EXPECTED_CONSOLE_SCRIPTS = {"agency": "agency_runtime.cli.main:main"}
VERSION_PATTERN = re.compile(
    r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:(?:a|b|rc)(?:0|[1-9]\d*))?"
)
MAX_PAX_HEADER_BYTES = 64 * 1_024
EXPECTED_DISTRIBUTION_ARTIFACT_COUNT = 2
READ_CHUNK_BYTES = 64 * 1024
SDIST_GENERATED_METADATA_FILES = {
    "PKG-INFO",
    "agency_runtime.egg-info/PKG-INFO",
    "agency_runtime.egg-info/SOURCES.txt",
    "agency_runtime.egg-info/dependency_links.txt",
    "agency_runtime.egg-info/entry_points.txt",
    "agency_runtime.egg-info/requires.txt",
    "agency_runtime.egg-info/top_level.txt",
    "setup.cfg",
}


@dataclass(frozen=True, slots=True)
class _FilesystemIdentity:
    device: int
    inode: int
    mode: int
    size: int
    modified_ns: int
    changed_ns: int
    file_attributes: int
    link_count: int


@dataclass(frozen=True, slots=True)
class _ArtifactBinding:
    name: str
    identity: _FilesystemIdentity


_CoreMetadataProjection = tuple[tuple[tuple[str, str], ...], str]


@dataclass(frozen=True, slots=True)
class _CommittedProjectContract:
    version: str
    dependencies: tuple[str, ...]
    license_payload: bytes
    core_metadata: _CoreMetadataProjection


class _ArtifactSetError(ValueError):
    def __init__(self, failures: list[str]) -> None:
        super().__init__("; ".join(failures))
        self.failures = tuple(failures)


def _is_link_or_reparse(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


def _filesystem_identity(metadata: os.stat_result) -> _FilesystemIdentity:
    inode = int(getattr(metadata, "st_ino", 0) or 0)
    if inode <= 0:
        raise ValueError("filesystem object has no stable identity")
    return _FilesystemIdentity(
        device=int(metadata.st_dev),
        inode=inode,
        mode=int(metadata.st_mode),
        size=int(metadata.st_size),
        modified_ns=int(metadata.st_mtime_ns),
        # Windows reports creation/change time with subtly different precision
        # through path and handle stat APIs. The non-share-write handle prevents
        # mutation while open there; POSIX ctime remains a useful mutation seal.
        changed_ns=0 if os.name == "nt" else int(metadata.st_ctime_ns),
        file_attributes=int(getattr(metadata, "st_file_attributes", 0) or 0),
        link_count=int(getattr(metadata, "st_nlink", 0) or 0),
    )


def _real_directory_identity(path: Path) -> _FilesystemIdentity:
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise ValueError("distribution directory must be a real directory") from exc
    if _is_link_or_reparse(metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("distribution directory must be a real non-link directory")
    return _filesystem_identity(metadata)


def _artifact_identity(metadata: os.stat_result, *, name: str) -> _FilesystemIdentity:
    if _is_link_or_reparse(metadata) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"distribution artifact must be a real regular file: {name}")
    identity = _filesystem_identity(metadata)
    if identity.link_count != 1:
        raise ValueError(f"distribution artifact must have exactly one hard link: {name}")
    if identity.size > MAX_ARTIFACT_PHYSICAL_BYTES:
        raise ValueError(f"distribution artifact exceeds the physical size limit: {name}")
    return identity


def _windows_descriptor(path: Path, *, directory: bool) -> int:
    import ctypes
    import msvcrt

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
    ]
    create_file.restype = ctypes.c_void_p
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    close_handle.restype = ctypes.c_int
    # A read-data handle with no delete sharing prevents the directory or
    # artifact pathname from being renamed out from under this verification.
    desired_access = 0x80000000
    flags = 0x00200000 | (0x02000000 if directory else 0)
    handle = create_file(
        str(path),
        desired_access,
        0x00000001,
        None,
        3,
        flags,
        None,
    )
    invalid_handle = ctypes.c_void_p(-1).value
    if handle in {None, invalid_handle}:
        error = ctypes.get_last_error()
        raise OSError(error, "distribution path could not be opened without link traversal", path)
    descriptor_flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    try:
        return msvcrt.open_osfhandle(int(handle), descriptor_flags)
    except BaseException:
        close_handle(handle)
        raise


def _open_descriptor(path: Path, *, directory: bool) -> int:
    if os.name == "nt":
        return _windows_descriptor(path, directory=directory)
    flags = os.O_RDONLY | int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    if directory:
        flags |= int(getattr(os, "O_DIRECTORY", 0))
    return os.open(path, flags)


def _same_identity(metadata: os.stat_result, expected: _FilesystemIdentity) -> bool:
    try:
        return _filesystem_identity(metadata) == expected
    except ValueError:
        return False


def _require_directory_identity(path: Path, expected: _FilesystemIdentity) -> None:
    try:
        current = os.lstat(path)
    except OSError as exc:
        raise ValueError("distribution directory changed during verification") from exc
    if (
        _is_link_or_reparse(current)
        or not stat.S_ISDIR(current.st_mode)
        or not _same_identity(current, expected)
    ):
        raise ValueError("distribution directory changed during verification")


@contextmanager
def _bound_distribution_directory(
    path: Path,
) -> Iterator[tuple[int, _FilesystemIdentity]]:
    expected = _real_directory_identity(path)
    try:
        descriptor = _open_descriptor(path, directory=True)
    except OSError as exc:
        raise ValueError("distribution directory could not be opened safely") from exc
    try:
        opened = os.fstat(descriptor)
        if (
            _is_link_or_reparse(opened)
            or not stat.S_ISDIR(opened.st_mode)
            or not _same_identity(opened, expected)
        ):
            raise ValueError("distribution directory changed while it was opened")
        _require_directory_identity(path, expected)
        try:
            yield descriptor, expected
        finally:
            if not _same_identity(os.fstat(descriptor), expected):
                raise ValueError("distribution directory changed during verification")
            _require_directory_identity(path, expected)
    finally:
        os.close(descriptor)


def _directory_names(path: Path, descriptor: int) -> list[str]:
    scan_target: Path | int = path if os.name == "nt" else descriptor
    names: list[str] = []
    with os.scandir(scan_target) as entries:
        for entry in entries:
            if len(names) >= EXPECTED_DISTRIBUTION_ARTIFACT_COUNT:
                raise ValueError("distribution directory exceeds its physical entry limit")
            names.append(entry.name)
    if len(names) != len(set(names)):
        raise ValueError("distribution directory contains duplicate child names")
    return sorted(names)


def _child_lstat(directory: Path, descriptor: int, name: str) -> os.stat_result:
    if os.name == "nt":
        return os.lstat(directory / name)
    return os.stat(name, dir_fd=descriptor, follow_symlinks=False)


def _capture_artifact_bindings(
    directory: Path,
    descriptor: int,
    *,
    version: str,
) -> tuple[_ArtifactBinding, _ArtifactBinding]:
    names = _directory_names(directory, descriptor)
    expected_wheel = f"agency_runtime-{version}-py3-none-any.whl"
    expected_sdist = f"agency_runtime-{version}.tar.gz"
    expected_names = {expected_wheel, expected_sdist}
    if set(names) != expected_names or len(names) != 2:
        paths = [directory / name for name in names]
        # A set/count mismatch necessarily violates at least one of the two
        # exact filename contracts checked by this helper.
        raise _ArtifactSetError(
            _artifact_identity_failures(
                [path for path in paths if path.name.endswith(".whl")],
                [path for path in paths if path.name.endswith(".tar.gz")],
                version=version,
            )
        )
    wheel = _ArtifactBinding(
        expected_wheel,
        _artifact_identity(
            _child_lstat(directory, descriptor, expected_wheel),
            name=expected_wheel,
        ),
    )
    sdist = _ArtifactBinding(
        expected_sdist,
        _artifact_identity(
            _child_lstat(directory, descriptor, expected_sdist),
            name=expected_sdist,
        ),
    )
    return wheel, sdist


def _open_child_descriptor(directory: Path, descriptor: int, name: str) -> int:
    if os.name == "nt":
        return _windows_descriptor(directory / name, directory=False)
    flags = os.O_RDONLY | int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    return os.open(name, flags, dir_fd=descriptor)


@contextmanager
def _bound_artifact(
    directory: Path,
    directory_descriptor: int,
    binding: _ArtifactBinding,
) -> Iterator[BinaryIO]:
    try:
        descriptor = _open_child_descriptor(
            directory,
            directory_descriptor,
            binding.name,
        )
    except OSError as exc:
        raise ValueError(
            f"distribution artifact could not be opened safely: {binding.name}"
        ) from exc
    stream: BinaryIO | None = None
    try:
        opened = os.fstat(descriptor)
        if not _same_identity(opened, binding.identity):
            raise ValueError(f"distribution artifact changed while it was opened: {binding.name}")
        _artifact_identity(opened, name=binding.name)
        current = _child_lstat(directory, directory_descriptor, binding.name)
        if not _same_identity(current, binding.identity):
            raise ValueError(f"distribution artifact path changed: {binding.name}")
        stream = os.fdopen(descriptor, "rb")
        descriptor = -1
        try:
            yield stream
        finally:
            if not _same_identity(os.fstat(stream.fileno()), binding.identity):
                raise ValueError(f"distribution artifact changed while it was read: {binding.name}")
            current = _child_lstat(directory, directory_descriptor, binding.name)
            if not _same_identity(current, binding.identity):
                raise ValueError(f"distribution artifact path changed: {binding.name}")
    finally:
        if stream is not None:
            stream.close()
        else:
            os.close(descriptor)


def _require_artifact_bindings(
    directory: Path,
    descriptor: int,
    expected: tuple[_ArtifactBinding, _ArtifactBinding],
) -> None:
    names = _directory_names(directory, descriptor)
    if names != sorted(binding.name for binding in expected):
        raise ValueError("distribution directory contents changed during verification")
    for binding in expected:
        current = _child_lstat(directory, descriptor, binding.name)
        if not _same_identity(current, binding.identity):
            raise ValueError(f"distribution artifact path changed: {binding.name}")
        _artifact_identity(current, name=binding.name)


@contextmanager
def _bound_distribution_artifacts(
    directory: Path,
    *,
    version: str,
) -> Iterator[tuple[BinaryIO, BinaryIO]]:
    with _bound_distribution_directory(directory) as (directory_descriptor, directory_identity):
        wheel, sdist = _capture_artifact_bindings(
            directory,
            directory_descriptor,
            version=version,
        )
        with (
            _bound_artifact(directory, directory_descriptor, wheel) as wheel_stream,
            _bound_artifact(directory, directory_descriptor, sdist) as sdist_stream,
        ):
            try:
                yield wheel_stream, sdist_stream
            finally:
                _require_artifact_bindings(
                    directory,
                    directory_descriptor,
                    (wheel, sdist),
                )
                _require_directory_identity(directory, directory_identity)


_safe_name = safe_release_name


def _register_archive_member(
    seen: dict[str, str],
    *,
    raw_name: str,
    path: PurePosixPath,
) -> None:
    key = path.as_posix().casefold()
    if previous := seen.get(key):
        raise ValueError(
            f"archive contains duplicate or aliasing members: {previous!r}, {raw_name!r}"
        )
    seen[key] = raw_name


_is_sdist_source = is_release_source


_partition_release_payloads = partition_release_payloads


def _release_git(root: Path) -> ReleaseGit:
    try:
        return ReleaseGit.discover(root)
    except (OSError, ReleaseGitError, TypeError, ValueError) as exc:
        raise ValueError(
            "distribution verification requires a clean Git checkout at the reviewed HEAD: "
            f"trusted release Git unavailable: {exc}"
        ) from exc


def _git_output(
    root: Path,
    args: list[str],
    *,
    git: ReleaseGit | None = None,
    input_bytes: bytes | None = None,
    max_stdout_bytes: int = MAX_TREE_MANIFEST_BYTES,
) -> bytes:
    session = _release_git(root) if git is None else git
    try:
        return session.run_bytes(
            args,
            input_bytes=input_bytes,
            max_stdout_bytes=max_stdout_bytes,
        )
    except (OSError, ReleaseGitError, TypeError, ValueError) as exc:
        raise ValueError(
            f"distribution verification requires a clean Git checkout at the reviewed HEAD: {exc}"
        ) from exc


def _reviewed_checkout(
    root: Path,
    expected_commit: str,
    *,
    git: ReleaseGit | None = None,
) -> str:
    return reviewed_checkout(
        root,
        expected_commit,
        git=git,
        git_output=_git_output,
    )


def _reviewed_commit_timestamp(
    root: Path,
    reviewed_commit: str,
    *,
    git: ReleaseGit | None = None,
) -> int:
    encoded = _git_output(
        root,
        ["show", "-s", "--format=%ct", reviewed_commit],
        git=git,
        max_stdout_bytes=64,
    )
    try:
        value = encoded.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise ValueError("reviewed commit timestamp is invalid") from exc
    if re.fullmatch(r"0|[1-9][0-9]*", value) is None:
        raise ValueError("reviewed commit timestamp is invalid")
    timestamp = int(value)
    _canonical_zip_timestamp(timestamp)
    return timestamp


def _parse_tracked_release_manifest(
    manifest: bytes,
) -> tuple[dict[str, str], set[str]]:
    entries: dict[str, str] = {}
    algorithms: set[str] = set()
    total_size = 0
    try:
        for item in manifest.split(b"\0"):
            if not item:
                continue
            metadata, encoded_name = item.split(b"\t", 1)
            match = re.fullmatch(
                rb"(100644|100755|120000|160000) (blob|commit|tree) "
                rb"([0-9a-f]{40}|[0-9a-f]{64}) +([0-9]+|-)",
                metadata,
            )
            if match is None:
                raise ValueError("committed release payload manifest is malformed")
            mode, object_type, object_id, encoded_size = match.groups()
            name = _safe_name(encoded_name.decode("utf-8")).as_posix()
            if not _is_sdist_source(name):
                continue
            if object_type != b"blob" or mode != b"100644" or encoded_size == b"-":
                raise ValueError(
                    f"committed release payload must be a non-executable regular file: {name}"
                )
            size = int(encoded_size)
            if encoded_size != str(size).encode("ascii"):
                raise ValueError("committed release payload manifest is malformed")
            if size > MAX_RELEASE_FILE_BYTES:
                raise ValueError(f"committed release payload exceeds its file-size limit: {name}")
            total_size += size
            if total_size > MAX_RELEASE_TOTAL_BYTES:
                raise ValueError("committed release payload exceeds its aggregate byte limit")
            digest = object_id.decode("ascii")
            # The manifest regex above admits only lowercase 40- or 64-digit
            # hexadecimal object IDs, so length fully determines the algorithm.
            algorithm = "sha1" if len(digest) == 40 else "sha256"
            if name in entries:
                raise ValueError(f"committed release payload is duplicated: {name}")
            entries[name] = digest
            algorithms.add(algorithm)
            if len(entries) > MAX_RELEASE_ENTRIES:
                raise ValueError("committed release payload exceeds its entry limit")
    except (UnicodeDecodeError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith("committed release"):
            raise
        raise ValueError("committed release payload manifest is malformed") from exc
    return entries, algorithms


def _tracked_release_payloads(
    root: Path,
    reviewed_commit: str,
    *,
    git: ReleaseGit | None = None,
) -> tuple[dict[str, str], dict[str, str], str]:
    """Return clean-checkout payload paths and their committed Git blob IDs."""

    inside = _git_output(
        root,
        ["rev-parse", "--is-inside-work-tree"],
        git=git,
    ).strip()
    if inside != b"true":
        raise ValueError("distribution verification requires a Git worktree checkout")

    manifest = _git_output(
        root,
        ["ls-tree", "-r", "-l", "-z", reviewed_commit, "--", *RELEASE_SOURCE_PATHS],
        git=git,
        max_stdout_bytes=MAX_TREE_MANIFEST_BYTES,
    )
    entries, algorithms = _parse_tracked_release_manifest(manifest)

    package_names, support_names = _partition_release_payloads(set(entries))
    package = {name: entries[name] for name in package_names}
    support = {name: entries[name] for name in support_names}
    if not package or not support or "pyproject.toml" not in support or "LICENSE" not in support:
        raise ValueError("committed release payload manifest is incomplete")
    if len(algorithms) != 1:
        raise ValueError("committed release payload manifest mixes object hash algorithms")
    return package, support, algorithms.pop()


def _committed_blob(
    root: Path,
    object_id: str,
    *,
    git: ReleaseGit | None = None,
) -> bytes:
    payload = _git_output(
        root,
        ["cat-file", "blob", object_id],
        git=git,
        max_stdout_bytes=MAX_RELEASE_FILE_BYTES,
    )
    algorithm = "sha1" if len(object_id) == 40 else "sha256"
    digest = hashlib.new(algorithm)
    digest.update(f"blob {len(payload)}\0".encode("ascii"))
    digest.update(payload)
    if digest.hexdigest() != object_id:
        raise ValueError("committed Git blob failed independent object verification")
    return payload


def _literal_release_version(payload: bytes, *, source: str) -> str:
    try:
        tree = ast.parse(payload.decode("utf-8"), filename=source)
    except (SyntaxError, UnicodeDecodeError) as exc:
        raise ValueError(f"committed release version source is invalid: {source}") from exc
    values: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if (
            isinstance(target, ast.Name)
            and target.id == "__version__"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            values.append(node.value.value)
    if len(values) != 1 or VERSION_PATTERN.fullmatch(values[0]) is None:
        raise ValueError("committed package must define one canonical literal __version__")
    return values[0]


def _normalized_requirement(
    value: str,
    *,
    extra: str | None = None,
    additional_marker: str | None = None,
) -> str:
    try:
        requirement = Requirement(value)
        parsed_additional = Marker(additional_marker) if additional_marker else None
    except (InvalidMarker, InvalidRequirement) as exc:
        raise ValueError(f"invalid release dependency: {value!r}") from exc
    normalized_extras = sorted(canonicalize_name(extra) for extra in requirement.extras)
    extras = f"[{','.join(normalized_extras)}]" if normalized_extras else ""
    normalized = f"{canonicalize_name(requirement.name)}{extras}"
    if requirement.url:
        normalized += f"@{requirement.url}"
    else:
        normalized += str(requirement.specifier)
    marker_parts = [f"({requirement.marker})"] if requirement.marker else []
    if parsed_additional is not None:
        marker_parts.append(f"({parsed_additional})")
    if extra is not None:
        marker_parts.append(f'extra == "{canonicalize_name(extra)}"')
    if marker_parts:
        normalized += f";{Marker(' and '.join(marker_parts))}"
    return normalized


def _normalized_dependencies(
    values: object,
    *,
    source: str,
    extra: str | None = None,
    additional_marker: str | None = None,
) -> tuple[str, ...]:
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise ValueError(f"{source} dependencies must be a list of requirement strings")
    normalized = tuple(
        _normalized_requirement(
            value,
            extra=extra,
            additional_marker=additional_marker,
        )
        for value in values
    )
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{source} dependencies contain duplicates")
    return tuple(sorted(normalized))


def _normalized_metadata_body(body: str) -> str:
    return body.replace("\r\n", "\n").replace("\r", "\n")


def _expected_core_metadata_projection(
    project: dict[str, object],
    *,
    version: str,
    dependencies: tuple[str, ...],
    readme_payload: bytes,
) -> _CoreMetadataProjection:
    description = project.get("description")
    authors = project.get("authors")
    keywords = project.get("keywords")
    classifiers = project.get("classifiers")
    license_files = project.get("license-files")
    urls = project.get("urls", {})
    optional = project.get("optional-dependencies", {})
    if (
        project.get("name") != "agency-runtime"
        or project.get("requires-python") != ">=3.10"
        or project.get("license") != "MIT"
        or project.get("readme") != "README.md"
        or project.get("dynamic") != ["version"]
        or not isinstance(description, str)
        or not description
        or not isinstance(authors, list)
        or not authors
        or any(
            not isinstance(author, dict)
            or set(author) != {"name"}
            or not isinstance(author.get("name"), str)
            or not author["name"]
            for author in authors
        )
        or not isinstance(keywords, list)
        or any(not isinstance(value, str) or not value for value in keywords)
        or len(keywords) != len(set(keywords))
        or not isinstance(classifiers, list)
        or any(not isinstance(value, str) or not value for value in classifiers)
        or len(classifiers) != len(set(classifiers))
        or license_files != ["LICENSE"]
        or not isinstance(urls, dict)
        or any(
            not isinstance(name, str) or not name or not isinstance(value, str) or not value
            for name, value in urls.items()
        )
        or not isinstance(optional, dict)
    ):
        raise ValueError("committed project core metadata contract is malformed")
    try:
        readme = _normalized_metadata_body(readme_payload.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError("committed project README is not UTF-8") from exc

    extras = tuple(sorted(canonicalize_name(name) for name in optional))
    if len(extras) != len(set(extras)):
        raise ValueError("committed project extra names are not canonical and unique")
    headers: list[tuple[str, str]] = [
        ("metadata-version", "2.4"),
        ("name", "agency-runtime"),
        ("version", version),
        ("summary", description),
        ("author", ", ".join(author["name"] for author in authors)),
        ("license-expression", "MIT"),
        ("requires-python", ">=3.10"),
        ("description-content-type", "text/markdown"),
        ("license-file", "LICENSE"),
        ("dynamic", "license-file"),
    ]
    if keywords:
        headers.append(("keywords", ",".join(keywords)))
    headers.extend(("classifier", value) for value in classifiers)
    headers.extend(("project-url", f"{name}, {value}") for name, value in urls.items())
    headers.extend(("requires-dist", value) for value in dependencies)
    headers.extend(("provides-extra", value) for value in extras)
    return tuple(sorted(headers)), readme


def _committed_project_contract(
    root: Path,
    package: dict[str, str],
    support: dict[str, str],
    *,
    git: ReleaseGit | None = None,
) -> _CommittedProjectContract:
    try:
        version_blob = _committed_blob(
            root,
            package["agency_runtime/__init__.py"],
            git=git,
        )
        pyproject_blob = _committed_blob(root, support["pyproject.toml"], git=git)
        license_blob = _committed_blob(root, support["LICENSE"], git=git)
        project = tomllib.loads(pyproject_blob.decode("utf-8"))["project"]
        if not isinstance(project, dict):
            raise TypeError
        dependencies = list(
            _normalized_dependencies(
                project.get("dependencies"),
                source="committed pyproject",
            )
        )
        optional = project.get("optional-dependencies", {})
        if not isinstance(optional, dict) or any(not isinstance(name, str) for name in optional):
            raise ValueError("committed optional dependencies are malformed")
        for extra, values in optional.items():
            dependencies.extend(
                _normalized_dependencies(
                    values,
                    source=f"committed pyproject optional dependency {extra}",
                    extra=extra,
                )
            )
    except (KeyError, TypeError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError("committed release project metadata is malformed") from exc
    version = _literal_release_version(
        version_blob,
        source="agency_runtime/__init__.py",
    )
    if len(dependencies) != len(set(dependencies)):
        raise ValueError("committed project dependency metadata contains duplicates")
    sorted_dependencies = tuple(sorted(dependencies))
    try:
        readme_blob = _committed_blob(root, support["README.md"], git=git)
    except KeyError as exc:
        raise ValueError("committed release project metadata is malformed") from exc
    core_metadata = _expected_core_metadata_projection(
        project,
        version=version,
        dependencies=sorted_dependencies,
        readme_payload=readme_blob,
    )
    return _CommittedProjectContract(
        version=version,
        dependencies=sorted_dependencies,
        license_payload=license_blob,
        core_metadata=core_metadata,
    )


def _git_blob_id(payload: bytes, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    digest.update(f"blob {len(payload)}\0".encode("ascii"))
    digest.update(payload)
    return digest.hexdigest()


def _committed_payload_failures(
    artifact: str,
    payloads: dict[str, bytes],
    committed: dict[str, str],
    algorithm: str,
) -> list[str]:
    changed = sorted(
        name
        for name, object_id in committed.items()
        if name in payloads and _git_blob_id(payloads[name], algorithm) != object_id
    )
    if not changed:
        return []
    return [f"{artifact} payload differs from committed HEAD: {', '.join(changed)}"]


def _junk_reason(name: str) -> str | None:
    path = _safe_name(name)
    if any(part in FORBIDDEN_PARTS for part in path.parts):
        return "generated directory or file"
    if any(part.startswith(".env.") and part != ".env.example" for part in path.parts):
        return "environment secret file"
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return "generated/runtime suffix"
    if path.name.endswith((".db-shm", ".db-wal", ".sqlite-shm", ".sqlite-wal")):
        return "generated/runtime sidecar"
    return None


def _check_member_limits(
    *,
    artifact: str,
    count: int,
    declared_size: int,
    accumulated_size: int,
) -> int:
    if count > MAX_ARCHIVE_MEMBERS:
        raise ValueError(f"{artifact} exceeds the archive member count limit")
    if declared_size < 0 or declared_size > MAX_ARCHIVE_MEMBER_BYTES:
        raise ValueError(f"{artifact} member exceeds the declared size limit")
    total = accumulated_size + declared_size
    if total > MAX_ARCHIVE_TOTAL_BYTES:
        raise ValueError(f"{artifact} exceeds the total uncompressed size limit")
    return total


def _read_member(stream: object, *, declared_size: int, label: str) -> bytes:
    read = getattr(stream, "read", None)
    if not callable(read):
        raise ValueError(f"unable to read archive member: {label}")
    chunks: list[bytes] = []
    observed = 0
    while True:
        chunk = read(min(READ_CHUNK_BYTES, declared_size + 1 - observed))
        if not isinstance(chunk, bytes):
            raise ValueError(f"archive member did not yield bytes: {label}")
        if not chunk:
            break
        chunks.append(chunk)
        observed += len(chunk)
        if observed > declared_size:
            raise ValueError(f"archive member exceeds its declared size: {label}")
    if observed != declared_size:
        raise ValueError(f"archive member is shorter than its declared size: {label}")
    return b"".join(chunks)


def _preflight_zip_central_records(
    stream: BinaryIO,
    *,
    directory_offset: int,
    directory_end: int,
    members: int,
) -> None:
    offset = directory_offset
    total_size = 0
    for count in range(1, members + 1):
        stream.seek(offset)
        header = stream.read(46)
        if len(header) != 46 or header[:4] != b"PK\x01\x02":
            raise ValueError("wheel central directory contains an unknown record or count mismatch")
        (
            _made_by,
            _extract,
            flags,
            _method,
            _modified_time,
            _modified_date,
            _crc,
            compressed_size,
            file_size,
            name_size,
            extra_size,
            comment_size,
            _volume,
            _internal_attr,
            _external_attr,
            _local_offset,
        ) = struct.unpack_from("<6H3L5H2L", header, 4)
        end = offset + 46 + name_size + extra_size + comment_size
        if end > directory_end or not 0 < name_size <= MAX_ARCHIVE_NAME_BYTES:
            raise ValueError("wheel central directory record exceeds its bounded layout")
        encoded_name = stream.read(name_size)
        if extra_size or comment_size:
            raise ValueError("wheel member contains a comment or extra field")
        try:
            decoded_name = encoded_name.decode("utf-8" if flags & 0x800 else "cp437")
        except UnicodeDecodeError as exc:
            raise ValueError("wheel central directory filename is invalid") from exc
        _safe_name(decoded_name)
        total_size = _check_member_limits(
            artifact="wheel",
            count=count,
            declared_size=file_size,
            accumulated_size=total_size,
        )
        if compressed_size > MAX_ARTIFACT_PHYSICAL_BYTES:
            raise ValueError("wheel compressed member exceeds the physical size limit")
        if file_size and (
            compressed_size <= 0 or file_size / compressed_size > MAX_ZIP_COMPRESSION_RATIO
        ):
            raise ValueError(f"wheel member exceeds the compression ratio limit: {decoded_name}")
        offset = end
    if offset != directory_end:
        raise ValueError("wheel central directory contains an unknown record or count mismatch")


def _preflight_zip_member_count(source: Path | BinaryIO) -> tuple[int, int, int]:
    if isinstance(source, Path):
        size = source.stat().st_size
        stream_context = None
    else:
        size = os.fstat(source.fileno()).st_size
        stream_context = None
    if size > MAX_ARTIFACT_PHYSICAL_BYTES:
        raise ValueError("wheel exceeds the physical size limit")
    if isinstance(source, Path):
        stream_context = source.open("rb")
    trailer_size = min(size, 65_557)
    stream = source if stream_context is None else stream_context
    try:
        stream.seek(size - trailer_size)
        trailer = stream.read(trailer_size)
    finally:
        if stream_context is not None:
            stream_context.close()
        else:
            stream.seek(0)
    marker = trailer.rfind(b"PK\x05\x06")
    if marker < 0 or len(trailer) - marker < 22:
        raise ValueError("wheel is missing a canonical ZIP end record")
    (
        disk_number,
        directory_disk,
        disk_members,
        total_members,
        directory_size,
        directory_offset,
        comment_size,
    ) = struct.unpack_from("<4H2LH", trailer, marker + 4)
    absolute_marker = size - trailer_size + marker
    if comment_size or marker + 22 != len(trailer):
        raise ValueError("wheel must not contain an archive comment or trailing data")
    if disk_number or directory_disk or disk_members != total_members or total_members == 0xFFFF:
        raise ValueError("wheel must be a single-disk non-ZIP64 archive")
    if directory_offset + directory_size != absolute_marker:
        raise ValueError("wheel central directory layout is noncanonical")
    if total_members > MAX_ARCHIVE_MEMBERS:
        raise ValueError("wheel exceeds the archive member count limit")
    central_context = source.open("rb") if isinstance(source, Path) else source
    try:
        _preflight_zip_central_records(
            central_context,
            directory_offset=directory_offset,
            directory_end=absolute_marker,
            members=total_members,
        )
    finally:
        if isinstance(source, Path):
            central_context.close()
        else:
            central_context.seek(0)
    return size, directory_offset, total_members


def _canonical_zip_timestamp(timestamp: int) -> tuple[int, int, int, int, int, int]:
    if (
        isinstance(timestamp, bool)
        or not isinstance(timestamp, int)
        or timestamp < 0
        or timestamp >= 2**32
    ):
        raise ValueError("canonical archive timestamp must fit the unsigned 32-bit format")
    try:
        year, month, day, hour, minute, second = time.gmtime(timestamp)[:6]
    except (OverflowError, OSError, ValueError) as exc:
        raise ValueError("canonical archive timestamp is outside the supported range") from exc
    if year < 1980:
        raise ValueError("canonical archive timestamp is outside the ZIP range")
    return year, month, day, hour, minute, second - (second % 2)


def _encoded_zip_name(item: zipfile.ZipInfo) -> bytes:
    expected_utf8 = not item.filename.isascii()
    if bool(item.flag_bits & 0x800) != expected_utf8:
        raise ValueError(f"wheel filename encoding flag is noncanonical: {item.filename}")
    return item.filename.encode("utf-8" if expected_utf8 else "ascii")


def _dos_zip_fields(item: zipfile.ZipInfo) -> tuple[int, int]:
    year, month, day, hour, minute, second = item.date_time
    try:
        time.strptime(
            f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}",
            "%Y-%m-%d %H:%M:%S",
        )
    except ValueError as exc:
        raise ValueError(f"wheel member has an invalid DOS timestamp: {item.filename}") from exc
    if year < 1980 or year > 2107 or second % 2:
        raise ValueError(f"wheel member has a noncanonical DOS timestamp: {item.filename}")
    return (hour << 11) | (minute << 5) | second // 2, ((year - 1980) << 9) | (month << 5) | day


def _validate_canonical_wheel_info(
    item: zipfile.ZipInfo,
    *,
    expected_timestamp: tuple[int, int, int, int, int, int] | None,
) -> None:
    is_record = item.filename.endswith(".dist-info/RECORD")
    expected_mode = CANONICAL_RECORD_MODE if is_record else CANONICAL_WHEEL_MODE
    if (
        item.create_system != CANONICAL_ZIP_SYSTEM
        or item.create_version != CANONICAL_ZIP_VERSION
        or item.extract_version != CANONICAL_ZIP_VERSION
        or item.reserved != 0
        or item.volume != 0
        or item.internal_attr != 0
        or item.external_attr != expected_mode << 16
    ):
        raise ValueError(f"wheel member header is noncanonical: {item.filename}")
    _encoded_zip_name(item)
    _dos_zip_fields(item)
    if expected_timestamp is not None and item.date_time != expected_timestamp:
        raise ValueError(
            f"wheel member timestamp does not match the reviewed commit: {item.filename}"
        )


def _validate_zip_central_records(
    archive: zipfile.ZipFile,
    infos: list[zipfile.ZipInfo],
    *,
    directory_offset: int,
    directory_end: int,
) -> None:
    stream = archive.fp
    if stream is None:
        raise ValueError("wheel archive was closed during verification")
    offset = directory_offset
    for item in infos:
        stream.seek(offset)
        header = stream.read(46)
        if len(header) != 46 or header[:4] != b"PK\x01\x02":
            raise ValueError("wheel central directory contains an unknown record or gap")
        (
            made_by,
            extract,
            flags,
            method,
            modified_time,
            modified_date,
            crc,
            compressed_size,
            file_size,
            name_size,
            extra_size,
            comment_size,
            volume,
            internal_attr,
            external_attr,
            local_offset,
        ) = struct.unpack_from("<6H3L5H2L", header, 4)
        encoded_name = stream.read(name_size)
        extra = stream.read(extra_size)
        comment = stream.read(comment_size)
        dos_time, dos_date = _dos_zip_fields(item)
        offset += 46 + name_size + extra_size + comment_size
        if (
            offset > directory_end
            or made_by != (item.create_system << 8) | item.create_version
            or extract != (item.reserved << 8) | item.extract_version
            or flags != item.flag_bits
            or method != item.compress_type
            or modified_time != dos_time
            or modified_date != dos_date
            or crc != item.CRC
            or compressed_size != item.compress_size
            or file_size != item.file_size
            or encoded_name != _encoded_zip_name(item)
            or extra != item.extra
            or comment != item.comment
            or volume != item.volume
            or internal_attr != item.internal_attr
            or external_attr != item.external_attr
            or local_offset != item.header_offset
        ):
            raise ValueError(f"wheel central record differs from parsed metadata: {item.filename}")
    if offset != directory_end:
        raise ValueError("wheel central directory contains an unknown record or gap")


def _zip_local_data_end(archive: zipfile.ZipFile, item: zipfile.ZipInfo) -> int:
    stream = archive.fp
    if stream is None:
        raise ValueError("wheel archive was closed during verification")
    stream.seek(item.header_offset)
    header = stream.read(30)
    if len(header) != 30 or header[:4] != b"PK\x03\x04":
        raise ValueError(f"wheel local header is invalid: {item.filename}")
    (
        _signature,
        extract_version,
        flags,
        method,
        modified_time,
        modified_date,
        crc,
        compressed_size,
        file_size,
        name_size,
        extra_size,
    ) = struct.unpack("<I5H3L2H", header)
    encoded_name = stream.read(name_size)
    local_extra = stream.read(extra_size)
    encoding = "utf-8" if flags & 0x800 else "cp437"
    try:
        local_name = encoded_name.decode(encoding)
    except UnicodeDecodeError as exc:
        raise ValueError(f"wheel local filename is invalid: {item.filename}") from exc
    year, month, day, hour, minute, second = item.date_time
    expected_time = (hour << 11) | (minute << 5) | (second // 2)
    expected_date = ((year - 1980) << 9) | (month << 5) | day
    if (
        local_name != item.filename
        or extract_version != item.extract_version
        or flags != item.flag_bits
        or method != item.compress_type
        or modified_time != expected_time
        or modified_date != expected_date
        or crc != item.CRC
        or compressed_size != item.compress_size
        or file_size != item.file_size
        or local_extra
    ):
        raise ValueError(f"wheel local header differs from its central record: {item.filename}")
    if method == zipfile.ZIP_STORED and compressed_size != file_size:
        raise ValueError(f"wheel stored member has a noncanonical size: {item.filename}")
    if method == zipfile.ZIP_DEFLATED:
        _require_exact_deflate_stream(
            stream,
            compressed_size=compressed_size,
            file_size=file_size,
            label=item.filename,
        )
    return item.header_offset + 30 + name_size + extra_size + item.compress_size


def _require_exact_deflate_stream(
    stream: BinaryIO,
    *,
    compressed_size: int,
    file_size: int,
    label: str,
) -> None:
    if file_size < 0 or file_size > MAX_ARCHIVE_MEMBER_BYTES:
        raise ValueError(f"wheel member exceeds the declared size limit: {label}")
    if compressed_size < 0 or compressed_size > MAX_ARTIFACT_PHYSICAL_BYTES:
        raise ValueError(f"wheel compressed member exceeds the physical size limit: {label}")
    if file_size and (
        compressed_size <= 0 or file_size / compressed_size > MAX_ZIP_COMPRESSION_RATIO
    ):
        raise ValueError(f"wheel member exceeds the compression ratio limit: {label}")
    decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
    remaining = compressed_size
    observed = 0
    try:
        while remaining:
            chunk = stream.read(min(READ_CHUNK_BYTES, remaining))
            if not isinstance(chunk, bytes) or not chunk:
                raise ValueError(f"wheel contains unsupported or invalid compressed data: {label}")
            remaining -= len(chunk)
            pending = chunk
            while pending:
                allowance = min(READ_CHUNK_BYTES, max(1, file_size + 1 - observed))
                inflated = decompressor.decompress(pending, allowance)
                observed += len(inflated)
                if observed > file_size:
                    raise ValueError(f"wheel member exceeds its declared size: {label}")
                if decompressor.unused_data:
                    raise ValueError(
                        f"wheel deflated member contains trailing compressed data: {label}"
                    )
                remaining_input = decompressor.unconsumed_tail
                if remaining_input == pending and not inflated:
                    raise ValueError(
                        f"wheel contains unsupported or invalid compressed data: {label}"
                    )
                pending = remaining_input
            if decompressor.eof and remaining:
                raise ValueError(
                    f"wheel deflated member contains trailing compressed data: {label}"
                )
        observed += len(decompressor.flush(min(READ_CHUNK_BYTES, max(1, file_size + 1 - observed))))
    except zlib.error as exc:
        raise ValueError(f"wheel contains unsupported or invalid compressed data: {label}") from exc
    if (
        not decompressor.eof
        or decompressor.unused_data
        or decompressor.unconsumed_tail
        or observed != file_size
    ):
        raise ValueError(f"wheel contains unsupported or invalid compressed data: {label}")


def _require_no_file_prefix_collisions(names: set[str], *, artifact: str) -> None:
    aliases = {name.casefold(): name for name in names}
    for name in sorted(names):
        parts = PurePosixPath(name.casefold()).parts
        for index in range(1, len(parts)):
            prefix = PurePosixPath(*parts[:index]).as_posix()
            if prefix in aliases:
                raise ValueError(
                    f"{artifact} contains a file-prefix collision: {aliases[prefix]}, {name}"
                )


def _validate_wheel_member_container(
    item: zipfile.ZipInfo,
    *,
    name: str,
    canonical_timestamp: tuple[int, int, int, int, int, int] | None,
) -> None:
    if item.comment or item.extra:
        raise ValueError(f"wheel member contains a comment or extra field: {name}")
    if item.flag_bits & 0x1:
        raise ValueError(f"wheel contains an encrypted member: {name}")
    if item.flag_bits & ~0x800:
        raise ValueError(f"wheel member uses unsupported ZIP flags: {name}")
    if item.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
        raise ValueError(f"wheel member uses an unsupported compression method: {name}")
    encoded_mode = item.external_attr >> 16
    file_type = stat.S_IFMT(encoded_mode)
    if item.is_dir():
        raise ValueError(f"wheel contains a directory member: {item.filename}")
    if file_type not in {0, stat.S_IFREG}:
        raise ValueError(f"wheel contains a non-regular member: {item.filename}")
    if encoded_mode & 0o111:
        raise ValueError(f"wheel contains an executable regular file: {item.filename}")
    if canonical_timestamp is not None:
        if item.compress_type != CANONICAL_ZIP_METHOD:
            raise ValueError(f"wheel member compression method is noncanonical: {item.filename}")
        _validate_canonical_wheel_info(
            item,
            expected_timestamp=canonical_timestamp,
        )
    if item.file_size and (
        item.compress_size <= 0 or item.file_size / item.compress_size > MAX_ZIP_COMPRESSION_RATIO
    ):
        raise ValueError(f"wheel member exceeds the compression ratio limit: {name}")


def _wheel_payload(
    source: Path | BinaryIO,
    *,
    expected_timestamp: int | None = None,
) -> tuple[set[str], dict[str, bytes]]:
    size, expected_directory_offset, expected_members = _preflight_zip_member_count(source)
    canonical_timestamp = (
        None if expected_timestamp is None else _canonical_zip_timestamp(expected_timestamp)
    )
    try:
        with zipfile.ZipFile(source) as archive:
            if archive.comment:
                raise ValueError("wheel must not contain an archive comment")
            infos = archive.infolist()
            if len(infos) != expected_members or archive.start_dir != expected_directory_offset:
                raise ValueError("wheel central directory layout is noncanonical")
            if [item.filename for item in infos] != sorted(item.filename for item in infos):
                raise ValueError("wheel members are not in canonical sorted order")
            _validate_zip_central_records(
                archive,
                infos,
                directory_offset=expected_directory_offset,
                directory_end=size - 22,
            )
            names = set()
            payloads: dict[str, bytes] = {}
            seen: dict[str, str] = {}
            total_size = 0
            expected_header_offset = 0
            for count, item in enumerate(infos, start=1):
                if item.header_offset != expected_header_offset:
                    raise ValueError("wheel contains a prefix, gap, or unreferenced local record")
                member = _safe_name(item.filename)
                _register_archive_member(seen, raw_name=item.filename, path=member)
                name = member.as_posix()
                total_size = _check_member_limits(
                    artifact="wheel",
                    count=count,
                    declared_size=item.file_size,
                    accumulated_size=total_size,
                )
                _validate_wheel_member_container(
                    item,
                    name=name,
                    canonical_timestamp=canonical_timestamp,
                )
                expected_header_offset = _zip_local_data_end(archive, item)
                names.add(name)
                with archive.open(item, mode="r") as stream:
                    payloads[name] = _read_member(
                        stream,
                        declared_size=item.file_size,
                        label=item.filename,
                    )
            if expected_header_offset != archive.start_dir:
                raise ValueError("wheel contains a gap or unreferenced local record")
            _require_no_file_prefix_collisions(names, artifact="wheel")
            return names, payloads
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, zlib.error) as exc:
        raise ValueError("wheel contains unsupported or invalid compressed data") from exc


def _seekable_stream_size(stream: BinaryIO) -> int:
    try:
        return os.fstat(stream.fileno()).st_size
    except (AttributeError, io.UnsupportedOperation, OSError):
        try:
            position = stream.tell()
            stream.seek(0, os.SEEK_END)
            size = stream.tell()
            stream.seek(position)
            return size
        except (AttributeError, io.UnsupportedOperation, OSError) as exc:
            raise ValueError("sdist source must be a bounded seekable stream") from exc


@contextmanager
def _bounded_sdist_source(source: Path | BinaryIO) -> Iterator[tuple[BinaryIO, int]]:
    physical_size = (
        source.stat().st_size if isinstance(source, Path) else _seekable_stream_size(source)
    )
    if physical_size > MAX_ARTIFACT_PHYSICAL_BYTES:
        raise ValueError("sdist exceeds the physical size limit")
    stream = source.open("rb") if isinstance(source, Path) else source
    try:
        stream.seek(0)
        yield stream, physical_size
    finally:
        if isinstance(source, Path):
            stream.close()
        else:
            stream.seek(0)


@dataclass(slots=True)
class _BoundedGzipReader:
    stream: BinaryIO
    physical_size: int
    observed: int = 0

    def read_exact(self, size: int) -> bytes:
        chunks: list[bytes] = []
        remaining = size
        while remaining:
            chunk = self.stream.read(min(READ_CHUNK_BYTES, remaining))
            if not isinstance(chunk, bytes):
                raise ValueError("sdist compressed stream did not yield bytes")
            if not chunk:
                raise ValueError("sdist stored gzip stream is truncated")
            if len(chunk) > remaining:
                raise ValueError("sdist compressed stream exceeded its requested boundary")
            self.observed += len(chunk)
            if self.observed > self.physical_size or self.observed > MAX_ARTIFACT_PHYSICAL_BYTES:
                raise ValueError("sdist exceeds the physical size limit")
            remaining -= len(chunk)
            chunks.append(chunk)
        return b"".join(chunks)

    def require_eof(self) -> None:
        trailing = self.stream.read(1)
        if not isinstance(trailing, bytes):
            raise ValueError("sdist compressed stream did not yield bytes")
        if trailing or self.observed != self.physical_size:
            raise ValueError("sdist compressed stream is shorter than its physical size")


def _read_stored_gzip_header(reader: _BoundedGzipReader) -> bytes:
    fixed_header = reader.read_exact(10)
    encoded_filename = bytearray()
    for _index in range(MAX_ARCHIVE_COMPONENT_BYTES + 1):
        encoded = reader.read_exact(1)
        encoded_filename.extend(encoded)
        if encoded == b"\0":
            break
    return fixed_header + bytes(encoded_filename)


def _read_stored_gzip_payload(
    reader: _BoundedGzipReader,
    *,
    maximum_payload: int,
) -> bytes:
    payload = bytearray()
    crc = 0
    final = False
    while reader.observed < reader.physical_size - 8:
        block_header = reader.read_exact(5)
        marker = block_header[0]
        block_size, inverse_size = struct.unpack_from("<HH", block_header, 1)
        if marker not in {0, 1}:
            raise ValueError("sdist stored gzip block header is noncanonical")
        if inverse_size != (~block_size & 0xFFFF):
            raise ValueError("sdist stored gzip block length is invalid")
        if block_size > reader.physical_size - reader.observed - 8:
            raise ValueError("sdist stored gzip block exceeds its boundary")
        final = marker == 1
        if (not final and block_size != 65_535) or (final and not block_size and payload):
            raise ValueError("sdist stored gzip segmentation is noncanonical")
        block = reader.read_exact(block_size)
        payload.extend(block)
        crc = zlib.crc32(block, crc)
        if len(payload) > maximum_payload:
            raise ValueError("sdist decompressed tar exceeds its size or compression-ratio limit")
        if final:
            break
    if not final or reader.observed != reader.physical_size - 8:
        raise ValueError("sdist contains trailing data or multiple gzip members")
    expected_crc, expected_size = struct.unpack("<LL", reader.read_exact(8))
    if expected_crc != crc & 0xFFFFFFFF or expected_size != len(payload):
        raise ValueError("sdist stored gzip trailer is invalid")
    reader.require_eof()
    return bytes(payload)


def _decompress_single_gzip(
    stream: BinaryIO,
    *,
    source: Path | BinaryIO,
    physical_size: int,
    expected_filename: str | None,
    expected_mtime: int | None = None,
) -> bytes:
    reader = _BoundedGzipReader(stream, physical_size)
    header = _read_stored_gzip_header(reader)
    _validate_gzip_header(
        header,
        source=source,
        expected_filename=expected_filename,
        expected_mtime=expected_mtime,
    )
    maximum_payload = min(
        MAX_TAR_CONTAINER_BYTES,
        physical_size * MAX_ZIP_COMPRESSION_RATIO,
    )
    return _read_stored_gzip_payload(reader, maximum_payload=maximum_payload)


def _bounded_gzip_payload(
    source: Path | BinaryIO,
    *,
    expected_filename: str | None = None,
    expected_mtime: int | None = None,
) -> bytes:
    with _bounded_sdist_source(source) as (stream, physical_size):
        return _decompress_single_gzip(
            stream,
            source=source,
            physical_size=physical_size,
            expected_filename=expected_filename,
            expected_mtime=expected_mtime,
        )


def _validate_gzip_header(
    header: bytes,
    *,
    source: Path | BinaryIO,
    expected_filename: str | None = None,
    expected_mtime: int | None = None,
) -> None:
    if len(header) < 11 or header[:4] != b"\x1f\x8b\x08\x08":
        raise ValueError("sdist gzip header is noncanonical")
    if header[8] != 0 or header[9] != 255:
        raise ValueError("sdist gzip compression header is noncanonical")
    if expected_mtime is not None and (
        expected_mtime < 0
        or expected_mtime >= 2**32
        or int.from_bytes(header[4:8], "little") != expected_mtime
    ):
        raise ValueError("sdist gzip timestamp does not match the reviewed commit")
    terminator = header.find(b"\0", 10, 10 + MAX_ARCHIVE_COMPONENT_BYTES + 1)
    if terminator < 0:
        raise ValueError("sdist gzip filename is missing or exceeds its size limit")
    encoded_name = header[10:terminator]
    try:
        filename = encoded_name.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("sdist gzip filename must be portable ASCII") from exc
    if not filename or Path(filename).name != filename or not filename.endswith(".tar"):
        raise ValueError("sdist gzip filename is noncanonical")
    source_name_value = getattr(source, "name", None)
    if isinstance(source, Path):
        source_name = source.name
    elif isinstance(source_name_value, (str, os.PathLike)):
        source_name = Path(source_name_value).name
    else:
        source_name = None
    derived_name = source_name[:-3] if source_name and source_name.endswith(".gz") else None
    required_name = expected_filename if expected_filename is not None else derived_name
    if required_name is not None and filename != required_name:
        raise ValueError("sdist gzip filename does not match its artifact name")


def _tar_member_size(header: bytes) -> int:
    encoded = header[124:136]
    stripped = encoded.rstrip(b"\0 ").lstrip(b" ")
    if not stripped or re.fullmatch(rb"[0-7]+", stripped) is None:
        raise ValueError("sdist tar header has a noncanonical size")
    return int(stripped, 8)


def _tar_canonical_octal(field: bytes, *, label: str) -> int:
    if len(field) < 2 or field[-1:] != b"\0" or re.fullmatch(rb"[0-7]+", field[:-1]) is None:
        raise ValueError(f"sdist tar header has a noncanonical {label}")
    return int(field[:-1], 8)


def _tar_nul_padded(field: bytes, *, label: str, allow_empty: bool) -> bytes:
    value, marker, padding = field.partition(b"\0")
    if not marker or any(padding) or (not allow_empty and not value):
        raise ValueError(f"sdist tar header has a noncanonical {label}")
    return value


def _tar_header_name(field: bytes, *, pax_path: str | None) -> bytes:
    if pax_path is None:
        value = (
            field if b"\0" not in field else _tar_nul_padded(field, label="name", allow_empty=False)
        )
        try:
            value.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError("sdist tar name must use portable ASCII without PAX") from exc
        return value
    placeholder = pax_path.encode("ascii", errors="replace")[: len(field)]
    expected = placeholder + (b"\0" * (len(field) - len(placeholder)))
    if field != expected:
        raise ValueError("sdist tar header has a noncanonical PAX base name")
    return placeholder


def _validate_canonical_tar_header(
    header: bytes,
    *,
    expected_mtime: int,
    pax_path: str | None = None,
) -> tuple[int, bytes]:
    checksum = header[148:156]
    if re.fullmatch(rb"[0-7]{6}\0 ", checksum) is None:
        raise ValueError("sdist tar checksum spelling is noncanonical")
    if int(checksum[:6], 8) != sum(header[:148]) + 8 * ord(" ") + sum(header[156:]):
        raise ValueError("sdist tar checksum is invalid")
    name = _tar_header_name(header[:100], pax_path=pax_path)
    mode = _tar_canonical_octal(header[100:108], label="mode")
    uid = _tar_canonical_octal(header[108:116], label="uid")
    gid = _tar_canonical_octal(header[116:124], label="gid")
    size = _tar_canonical_octal(header[124:136], label="size")
    modified = _tar_canonical_octal(header[136:148], label="mtime")
    member_type = header[156:157]
    directory_spelling = pax_path.endswith("/") if pax_path is not None else name.endswith(b"/")
    if member_type not in {tarfile.XHDTYPE, tarfile.REGTYPE, tarfile.DIRTYPE}:
        member_name = name.decode("ascii")
        raise ValueError(f"sdist contains an unsupported member type: {member_name}")
    if (
        any(header[157:257])
        or header[257:263] != b"ustar\0"
        or header[263:265] != b"00"
        or any(header[265:345])
        or any(header[345:512])
    ):
        raise ValueError("sdist tar header has noncanonical owner, device, or reserved fields")
    if member_type == tarfile.XHDTYPE:
        if name != b"././@PaxHeader" or mode or uid or gid or modified:
            raise ValueError("sdist PAX tar header is noncanonical")
    elif member_type == tarfile.REGTYPE:
        if mode != 0o644 or uid or gid or modified != expected_mtime or directory_spelling:
            raise ValueError("sdist regular-file tar header is noncanonical")
    elif member_type == tarfile.DIRTYPE and (
        mode != 0o755 or uid or gid or modified != expected_mtime or size or not directory_spelling
    ):
        raise ValueError("sdist directory tar header is noncanonical")
    return size, member_type


def _parse_pax_records(payload: bytes) -> dict[str, str]:
    records: dict[str, str] = {}
    offset = 0
    while offset < len(payload):
        separator = payload.find(b" ", offset)
        if separator < 0:
            raise ValueError("sdist PAX record length is malformed")
        encoded_length = payload[offset:separator]
        if not encoded_length or not encoded_length.isdigit() or encoded_length.startswith(b"0"):
            raise ValueError("sdist PAX record length is noncanonical")
        length = int(encoded_length)
        end = offset + length
        if end > len(payload) or payload[end - 1 : end] != b"\n":
            raise ValueError("sdist PAX record exceeds its header boundary")
        record = payload[separator + 1 : end - 1]
        key, assignment, encoded_value = record.partition(b"=")
        if not key or not assignment:
            raise ValueError("sdist PAX record is malformed")
        try:
            decoded_key = key.decode("ascii")
            value = encoded_value.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("sdist PAX record text is invalid") from exc
        if decoded_key not in {"mtime", "path"}:
            raise ValueError(f"sdist PAX record key is unsupported: {decoded_key}")
        if decoded_key in records:
            raise ValueError(f"sdist PAX record key is duplicated: {decoded_key}")
        records[decoded_key] = value
        offset = end
    return records


def _require_canonical_pax_payload(records: dict[str, str]) -> None:
    path = records.get("path")
    if (
        set(records) != {"path"}
        or path is None
        or (path.isascii() and len(path.encode("utf-8")) <= 100)
    ):
        raise ValueError("sdist PAX payload is noncanonical")


def _require_canonical_tar_end(payload: bytes, *, offset: int, pending_pax: bool) -> None:
    zero = b"\0" * 512
    if offset + 1_024 > len(payload) or payload[offset + 512 : offset + 1_024] != zero:
        raise ValueError("sdist tar end marker must contain two zero blocks")
    if any(payload[offset + 1_024 :]):
        raise ValueError("sdist tar contains nonzero trailing data")
    if pending_pax:
        raise ValueError("sdist tar contains an orphan PAX header")
    canonical_length = ((offset + 1_024 + 10_239) // 10_240) * 10_240
    if len(payload) != canonical_length:
        raise ValueError("sdist tar contains noncanonical excess zero padding")


def _preflight_tar_layout(
    payload: bytes,
    *,
    expected_mtime: int | None = None,
) -> None:
    if not payload or len(payload) % 10_240:
        raise ValueError("sdist tar container length is noncanonical")
    offset = 0
    pending_pax: dict[str, str] | None = None
    member_count = 0
    total_size = 0
    zero = b"\0" * 512
    while offset + 512 <= len(payload):
        header = payload[offset : offset + 512]
        if header == zero:
            _require_canonical_tar_end(
                payload,
                offset=offset,
                pending_pax=pending_pax is not None,
            )
            return
        raw_member_type = header[156:157] or tarfile.REGTYPE
        if raw_member_type in {
            tarfile.GNUTYPE_LONGNAME,
            tarfile.GNUTYPE_LONGLINK,
            tarfile.XGLTYPE,
            tarfile.SOLARIS_XHDTYPE,
        }:
            raise ValueError("sdist tar contains an unsupported extended header")
        if expected_mtime is None:
            member_size = _tar_member_size(header)
            member_type = raw_member_type
        else:
            member_size, member_type = _validate_canonical_tar_header(
                header,
                expected_mtime=expected_mtime,
                pax_path=None if pending_pax is None else pending_pax.get("path"),
            )
        if member_type == tarfile.XHDTYPE:
            if pending_pax is not None:
                raise ValueError("sdist tar contains chained PAX headers")
            if member_size > MAX_PAX_HEADER_BYTES:
                raise ValueError("sdist PAX header exceeds its size limit")
            start = offset + 512
            records = _parse_pax_records(payload[start : start + member_size])
            if expected_mtime is not None:
                _require_canonical_pax_payload(records)
            pending_pax = records
        else:
            member_count += 1
            total_size = _check_member_limits(
                artifact="sdist",
                count=member_count,
                declared_size=member_size if member_type == tarfile.REGTYPE else 0,
                accumulated_size=total_size,
            )
            pending_pax = None
        member_end = offset + 512 + member_size
        next_offset = offset + 512 + ((member_size + 511) // 512) * 512
        if next_offset > len(payload):
            raise ValueError("sdist tar member exceeds the container boundary")
        if any(payload[member_end:next_offset]):
            raise ValueError("sdist tar member padding must contain only zero bytes")
        offset = next_offset
    raise ValueError("sdist tar is missing its canonical end marker")


def _validate_pax_headers(
    item: tarfile.TarInfo,
    *,
    expected_mtime: int | None = None,
) -> None:
    headers = item.pax_headers
    if expected_mtime is not None and set(headers) - {"path"}:
        raise ValueError(f"sdist member has noncanonical PAX headers: {item.name}")
    if set(headers) - {"mtime", "path"}:
        raise ValueError(f"sdist member has unsupported PAX headers: {item.name}")
    path = headers.get("path")
    if path is not None:
        if item.isdir() != path.endswith("/"):
            raise ValueError(f"sdist member has a noncanonical PAX path: {item.name}")
        effective_path = path[:-1] if item.isdir() and path.endswith("/") else path
        if effective_path != item.name or len(path) > MAX_ARCHIVE_NAME_CHARS:
            raise ValueError(f"sdist member has a noncanonical PAX path: {item.name}")
    modified = headers.get("mtime")
    if modified is not None and (
        len(modified) > 32
        or re.fullmatch(r"-?(?:0|[1-9]\d*)(?:\.(?:0|[0-9]*[1-9]))?", modified) is None
    ):
        raise ValueError(f"sdist member has a noncanonical PAX mtime: {item.name}")


def _validated_tar_members(
    archive: tarfile.TarFile,
    *,
    expected_mtime: int | None = None,
) -> list[tuple[tarfile.TarInfo, PurePosixPath]]:
    if archive.pax_headers:
        raise ValueError("sdist tar contains unsupported global PAX headers")
    seen: dict[str, str] = {}
    validated: list[tuple[tarfile.TarInfo, PurePosixPath]] = []
    total_size = 0
    for count, item in enumerate(archive, start=1):
        _validate_pax_headers(item, expected_mtime=expected_mtime)
        path_name = _safe_name(item.name)
        _register_archive_member(seen, raw_name=item.name, path=path_name)
        if item.type not in {tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE}:
            raise ValueError(f"sdist contains an unsupported member type: {item.name}")
        canonical = path_name.as_posix()
        if item.isdir():
            if item.name not in {canonical, f"{canonical}/"} or item.size != 0:
                raise ValueError(f"sdist contains a noncanonical directory: {item.name}")
            declared_size = 0
        else:
            if item.name != canonical:
                raise ValueError(f"sdist contains a noncanonical regular file: {item.name}")
            if item.mode & 0o111:
                raise ValueError(f"sdist contains an executable regular file: {item.name}")
            declared_size = item.size
        if expected_mtime is not None and (
            item.uid != 0
            or item.gid != 0
            or item.uname
            or item.gname
            or item.devmajor != 0
            or item.devminor != 0
            or item.mtime != expected_mtime
            or item.mode != (0o755 if item.isdir() else 0o644)
        ):
            raise ValueError(f"sdist member header is noncanonical: {item.name}")
        total_size = _check_member_limits(
            artifact="sdist",
            count=count,
            declared_size=declared_size,
            accumulated_size=total_size,
        )
        validated.append((item, path_name))
    if [path.as_posix() for _item, path in validated] != sorted(
        path.as_posix() for _item, path in validated
    ):
        raise ValueError("sdist members are not in canonical sorted order")
    return validated


def _sdist_payloads_from_members(
    archive: tarfile.TarFile,
    validated: list[tuple[tarfile.TarInfo, PurePosixPath]],
    *,
    expected_root: str | None,
) -> tuple[set[str], dict[str, bytes]]:
    roots = {path_name.parts[0] for _item, path_name in validated}
    if len(roots) != 1:
        raise ValueError(f"sdist must have one top-level directory, found {sorted(roots)}")
    root_members = [item for item, path_name in validated if len(path_name.parts) == 1]
    if len(root_members) != 1 or not root_members[0].isdir():
        raise ValueError("sdist must contain one explicit top-level directory")
    root = next(iter(roots))
    if expected_root is not None and root != expected_root:
        raise ValueError(f"sdist has unexpected top-level directory: {root}")
    names = set()
    payloads: dict[str, bytes] = {}
    directories: set[str] = set()
    for item, path_name in validated:
        stripped = PurePosixPath(*path_name.parts[1:]).as_posix()
        if stripped == ".":
            continue
        names.add(stripped)
        if item.isdir():
            directories.add(stripped)
        if item.type in {tarfile.REGTYPE, tarfile.AREGTYPE}:
            extracted = archive.extractfile(item)
            if extracted is None:
                raise ValueError(f"unable to read sdist member: {item.name}")
            with extracted:
                payloads[stripped] = _read_member(
                    extracted,
                    declared_size=item.size,
                    label=item.name,
                )
    file_names = set(payloads)
    _require_no_file_prefix_collisions(file_names, artifact="sdist")
    required_directories = {
        PurePosixPath(*parts[:index]).as_posix()
        for name in file_names
        for parts in (PurePosixPath(name).parts,)
        for index in range(1, len(parts))
    }
    if directories != required_directories:
        raise ValueError("sdist directory entries must exactly match file parent directories")
    return names, payloads


def _sdist_payload(
    source: Path | BinaryIO,
    *,
    expected_root: str | None = None,
    expected_timestamp: int | None = None,
) -> tuple[set[str], dict[str, bytes]]:
    tar_payload = _bounded_gzip_payload(
        source,
        expected_filename=f"{expected_root}.tar" if expected_root is not None else None,
        expected_mtime=expected_timestamp,
    )
    _preflight_tar_layout(tar_payload, expected_mtime=expected_timestamp)
    with tarfile.open(fileobj=io.BytesIO(tar_payload), mode="r:") as archive:
        validated = _validated_tar_members(
            archive,
            expected_mtime=expected_timestamp,
        )
        return _sdist_payloads_from_members(
            archive,
            validated,
            expected_root=expected_root,
        )


def _metadata(payloads: dict[str, bytes]) -> tuple[str, bytes]:
    matches = [
        (name, data) for name, data in payloads.items() if name.endswith(".dist-info/METADATA")
    ]
    if len(matches) != 1:
        raise ValueError(f"wheel must contain one METADATA file, found {len(matches)}")
    return matches[0]


def _hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _missing_file_failures(
    wheel_names: set[str],
    sdist_names: set[str],
    required_package_files: set[str],
    required_sdist_files: set[str] | None = None,
) -> list[str]:
    failures: list[str] = []
    sdist_required = REQUIRED_SDIST_FILES if required_sdist_files is None else required_sdist_files
    missing_wheel = sorted(required_package_files - wheel_names)
    missing_sdist = sorted((sdist_required | required_package_files) - sdist_names)
    if missing_wheel:
        failures.append(f"wheel missing required files: {', '.join(missing_wheel)}")
    if missing_sdist:
        failures.append(f"sdist missing required files: {', '.join(missing_sdist)}")
    return failures


def _unexpected_scoped_payload_failures(
    artifact: str,
    names: set[str],
    expected: set[str],
    *,
    prefixes: tuple[str, ...],
) -> list[str]:
    observed = {name for name in names if name.startswith(prefixes)}
    unexpected = sorted(observed - expected)
    if not unexpected:
        return []
    return [f"{artifact} contains unexpected source payload: {', '.join(unexpected)}"]


def _wheel_payload_contract_failures(
    payloads: dict[str, bytes],
    committed_package_files: set[str],
    *,
    version: str,
) -> list[str]:
    dist_info = f"agency_runtime-{version}.dist-info"
    expected = committed_package_files | {
        f"{dist_info}/{relative}" for relative in WHEEL_METADATA_FILES
    }
    unexpected = sorted(set(payloads) - expected)
    if not unexpected:
        return []
    return [f"wheel contains unexpected payload: {', '.join(unexpected)}"]


def _sdist_payload_contract_failures(
    payloads: dict[str, bytes],
    committed_source_files: set[str],
) -> list[str]:
    expected = committed_source_files | SDIST_GENERATED_METADATA_FILES
    unexpected = sorted(set(payloads) - expected)
    if not unexpected:
        return []
    return [f"sdist contains unexpected payload: {', '.join(unexpected)}"]


def _artifact_identity_failures(
    wheels: list[Path],
    sdists: list[Path],
    *,
    version: str,
) -> list[str]:
    failures: list[str] = []
    expected_wheel = f"agency_runtime-{version}-py3-none-any.whl"
    expected_sdist = f"agency_runtime-{version}.tar.gz"
    if len(wheels) != 1 or wheels[0].name != expected_wheel:
        failures.append(f"expected exact wheel filename: {expected_wheel}")
    if len(sdists) != 1 or sdists[0].name != expected_sdist:
        failures.append(f"expected exact sdist filename: {expected_sdist}")
    return failures


def _junk_failures(artifact: str, names: set[str]) -> list[str]:
    junk: list[str] = []
    for name in names:
        reason = _junk_reason(name)
        if reason:
            junk.append(f"{name} ({reason})")
    if not junk:
        return []
    return [f"{artifact} contains generated junk: {', '.join(sorted(junk))}"]


def _payload_mismatch_failures(
    names: set[str], wheel_payloads: dict[str, bytes], sdist_payloads: dict[str, bytes]
) -> list[str]:
    shared = names & set(wheel_payloads) & set(sdist_payloads)
    return [
        f"wheel/sdist payload mismatch: {name}"
        for name in sorted(shared)
        if _hash(wheel_payloads[name]) != _hash(sdist_payloads[name])
    ]


def _console_scripts_payload_failures(payload: bytes, *, label: str) -> list[str]:
    try:
        entries = configparser.ConfigParser(interpolation=None, strict=True)
        entries.optionxform = str
        entries.read_string(payload.decode("utf-8"))
        observed = (
            dict(entries.items("console_scripts", raw=True))
            if not entries.defaults() and entries.sections() == ["console_scripts"]
            else {}
        )
    except (UnicodeDecodeError, configparser.Error):
        observed = {}
    if observed == EXPECTED_CONSOLE_SCRIPTS:
        return []
    return [f"{label} console entry point contract is invalid"]


def _console_script_failures(
    dist_info: str,
    wheel_payloads: dict[str, bytes],
) -> list[str]:
    payload = wheel_payloads.get(f"{dist_info}/entry_points.txt")
    if payload is None:
        return []
    return _console_scripts_payload_failures(payload, label="wheel")


def _top_level_package_failures(
    dist_info: str,
    wheel_payloads: dict[str, bytes],
) -> list[str]:
    payload = wheel_payloads.get(f"{dist_info}/top_level.txt")
    if payload is None:
        return []
    try:
        top_levels = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        top_levels = []
    if top_levels == ["agency_runtime"]:
        return []
    return ["wheel top-level package contract is invalid"]


def _singleton_header(
    metadata: Message,
    name: str,
    *,
    label: str,
) -> tuple[str | None, list[str]]:
    values = metadata.get_all(name, [])
    if len(values) == 1:
        return values[0], []
    return None, [f"{label} must contain exactly one {name} header"]


def _project_metadata_failures(
    metadata: Message,
    *,
    label: str,
    expected_version: str,
    expected_dependencies: tuple[str, ...],
    expected_core_metadata: _CoreMetadataProjection,
    require_classifiers: bool,
) -> list[str]:
    failures: list[str] = []
    if metadata.defects:
        failures.append(f"{label} contains malformed email metadata")
    expected_headers = {
        "Metadata-Version": "2.4",
        "Name": "agency-runtime",
        "Version": expected_version,
        "Requires-Python": ">=3.10",
        "License-Expression": "MIT",
    }
    for name, expected in expected_headers.items():
        observed, singleton_failures = _singleton_header(metadata, name, label=label)
        failures.extend(singleton_failures)
        if observed is not None and observed != expected:
            failures.append(f"{label} has unexpected {name}: {observed!r}")

    requirements = metadata.get_all("Requires-Dist", [])
    try:
        observed_dependencies = _normalized_dependencies(requirements, source=label)
    except ValueError:
        observed_dependencies = ()
        failures.append(f"{label} dependency metadata is invalid or duplicated")
    if observed_dependencies != expected_dependencies:
        failures.append(f"{label} dependency metadata does not match committed pyproject")

    if require_classifiers:
        classifiers = set(metadata.get_all("Classifier", []))
        missing_classifiers = sorted(REQUIRED_CLASSIFIERS - classifiers)
        if missing_classifiers:
            failures.append(f"missing classifiers: {', '.join(missing_classifiers)}")
    try:
        observed_headers, observed_body = _canonical_project_metadata_projection(metadata)
    except (AttributeError, TypeError, ValueError):
        failures.append(f"{label} cannot be projected into canonical core metadata")
    else:
        expected_headers, expected_body = expected_core_metadata
        unexpected = Counter(observed_headers) - Counter(expected_headers)
        missing = Counter(expected_headers) - Counter(observed_headers)
        if unexpected:
            failures.append(
                f"{label} contains unsupported or unexpected core metadata: "
                f"{_metadata_counter_summary(unexpected)}"
            )
        if missing:
            failures.append(
                f"{label} is missing or alters reviewed core metadata: "
                f"{_metadata_counter_summary(missing)}"
            )
        if observed_body != expected_body:
            failures.append(f"{label} description body does not match committed README")
    return failures


def _metadata_counter_summary(headers: Counter[tuple[str, str]]) -> str:
    return ", ".join(
        f"{name}={value!r}" if count == 1 else f"{name}={value!r} x{count}"
        for (name, value), count in sorted(headers.items())
    )


def _canonical_project_metadata_projection(metadata: Message) -> _CoreMetadataProjection:
    headers: list[tuple[str, str]] = []
    for name, value in metadata.items():
        normalized_name = name.casefold()
        normalized_value = str(value)
        if normalized_name == "requires-dist":
            normalized_value = _normalized_requirement(normalized_value)
        elif normalized_name == "provides-extra":
            normalized_value = canonicalize_name(normalized_value)
        headers.append((normalized_name, normalized_value))
    body = metadata.get_payload()
    if not isinstance(body, str):
        raise ValueError("distribution core metadata body is not plain text")
    return tuple(sorted(headers)), _normalized_metadata_body(body)


def _core_metadata_projection(metadata: Message) -> tuple[Counter[tuple[str, str]], str]:
    headers = Counter((name.casefold(), str(value)) for name, value in metadata.items())
    body = metadata.get_payload()
    if not isinstance(body, str):
        raise ValueError("distribution core metadata body is not plain text")
    return headers, _normalized_metadata_body(body)


def _metadata_parity_failures(
    wheel_metadata: Message,
    sdist_payloads: dict[str, bytes],
) -> list[str]:
    package_info = sdist_payloads.get("PKG-INFO")
    if package_info is None:
        return []
    try:
        sdist_metadata = BytesParser(policy=policy.default).parsebytes(package_info)
        wheel_headers, wheel_body = _core_metadata_projection(wheel_metadata)
        sdist_headers, sdist_body = _core_metadata_projection(sdist_metadata)
    except (TypeError, ValueError):
        return ["wheel METADATA and sdist PKG-INFO cannot be compared safely"]
    failures: list[str] = []
    if wheel_headers != sdist_headers:
        failures.append("wheel METADATA headers differ from sdist PKG-INFO")
    if wheel_body != sdist_body:
        failures.append("wheel METADATA body differs from sdist PKG-INFO")
    return failures


def _wheel_control_failures(dist_info: str, wheel_payloads: dict[str, bytes]) -> list[str]:
    payload = wheel_payloads.get(f"{dist_info}/WHEEL")
    if payload is None:
        return []
    try:
        metadata = BytesParser(policy=policy.default).parsebytes(payload)
    except (TypeError, ValueError):
        return ["wheel control metadata is invalid"]
    header_counts = Counter(name.lower() for name, _value in metadata.raw_items())
    allowed = {"generator", "root-is-purelib", "tag", "wheel-version"}
    failures: list[str] = []
    if metadata.defects or set(header_counts) - allowed:
        failures.append("wheel control metadata contains unsupported headers or syntax")
    expected = {
        "wheel-version": "1.0",
        "root-is-purelib": "true",
        "tag": "py3-none-any",
    }
    for name, value in expected.items():
        if header_counts[name] != 1 or metadata.get(name) != value:
            failures.append(f"wheel control metadata has invalid {name}")
    if header_counts["generator"] > 1:
        failures.append("wheel control metadata has duplicate generator headers")
    body = metadata.get_payload()
    if isinstance(body, str) and body.strip():
        failures.append("wheel control metadata contains an unexpected body")
    return failures


def _canonical_record_payload(dist_info: str, wheel_payloads: dict[str, bytes]) -> bytes:
    record_name = f"{dist_info}/RECORD"
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    for name in sorted(set(wheel_payloads) - {record_name}):
        digest = (
            base64.urlsafe_b64encode(hashlib.sha256(wheel_payloads[name]).digest())
            .rstrip(b"=")
            .decode("ascii")
        )
        writer.writerow((name, f"sha256={digest}", str(len(wheel_payloads[name]))))
    writer.writerow((record_name, "", ""))
    return output.getvalue().encode("utf-8")


def _record_failures(dist_info: str, wheel_payloads: dict[str, bytes]) -> list[str]:
    record_name = f"{dist_info}/RECORD"
    payload = wheel_payloads.get(record_name)
    if payload is None:
        return []
    rows: dict[str, tuple[str, str]] = {}
    seen: dict[str, str] = {}
    try:
        reader = csv.reader(io.StringIO(payload.decode("utf-8"), newline=""), strict=True)
        for row in reader:
            if len(row) != 3:
                raise ValueError("RECORD row must contain three columns")
            raw_name, digest, size = row
            path = _safe_name(raw_name)
            _register_archive_member(seen, raw_name=raw_name, path=path)
            rows[path.as_posix()] = (digest, size)
    except (UnicodeDecodeError, csv.Error, ValueError):
        return ["wheel RECORD is malformed, duplicated, or noncanonical"]

    failures: list[str] = []
    expected_names = set(wheel_payloads)
    missing = sorted(expected_names - set(rows))
    extra = sorted(set(rows) - expected_names)
    if missing:
        failures.append(f"wheel RECORD missing members: {', '.join(missing)}")
    if extra:
        failures.append(f"wheel RECORD contains extra members: {', '.join(extra)}")
    for name in sorted(expected_names & set(rows)):
        digest, size = rows[name]
        if name == record_name:
            if digest or size:
                failures.append("wheel RECORD self row must have empty hash and size")
            continue
        expected_digest = (
            base64.urlsafe_b64encode(hashlib.sha256(wheel_payloads[name]).digest())
            .rstrip(b"=")
            .decode("ascii")
        )
        if digest != f"sha256={expected_digest}" or size != str(len(wheel_payloads[name])):
            failures.append(f"wheel RECORD hash or size mismatch: {name}")
    if payload != _canonical_record_payload(dist_info, wheel_payloads):
        failures.append(
            "wheel RECORD bytes are noncanonical; rows must be sorted with LF endings "
            "and the self row last"
        )
    return failures


def _setup_cfg_failures(payload: bytes) -> list[str]:
    try:
        config = configparser.ConfigParser(interpolation=None, strict=True)
        config.optionxform = str
        config.read_string(payload.decode("utf-8"))
        observed = (
            dict(config.items("egg_info", raw=True))
            if not config.defaults() and config.sections() == ["egg_info"]
            else {}
        )
    except (UnicodeDecodeError, configparser.Error):
        observed = {}
    if observed == {"tag_build": "", "tag_date": "0"}:
        return []
    return ["sdist generated setup.cfg contract is invalid"]


def _sources_manifest_failures(payload: bytes, sdist_payloads: dict[str, bytes]) -> list[str]:
    seen: dict[str, str] = {}
    observed: set[str] = set()
    try:
        lines = payload.decode("utf-8").splitlines()
        if not lines or any(not line for line in lines):
            raise ValueError("empty source manifest row")
        for line in lines:
            path = _safe_name(line)
            _register_archive_member(seen, raw_name=line, path=path)
            observed.add(path.as_posix())
    except (UnicodeDecodeError, ValueError):
        return ["sdist generated SOURCES.txt is malformed or duplicated"]
    expected = set(sdist_payloads) - {"PKG-INFO", "setup.cfg"}
    expected_payload = ("\n".join(sorted(expected)) + "\n").encode("utf-8")
    if observed == expected and payload == expected_payload:
        return []
    return ["sdist generated SOURCES.txt does not match the exact sorted LF payload manifest"]


def _requires_txt_dependencies(payload: bytes) -> tuple[str, ...]:
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("requires.txt is not UTF-8") from exc
    dependencies: list[str] = []
    current_extra: str | None = None
    current_marker: str | None = None
    for line in lines:
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            current_extra, separator, marker = section.partition(":")
            if not current_extra or not re.fullmatch(r"[A-Za-z0-9._-]+", current_extra):
                raise ValueError("requires.txt has an invalid extra section")
            current_marker = marker if separator else None
            continue
        dependencies.append(
            _normalized_requirement(
                line,
                extra=current_extra,
                additional_marker=current_marker,
            )
        )
    if len(dependencies) != len(set(dependencies)):
        raise ValueError("requires.txt dependencies contain duplicates")
    return tuple(sorted(dependencies))


def _sdist_generated_metadata_failures(
    payloads: dict[str, bytes],
    *,
    expected_version: str,
    expected_dependencies: tuple[str, ...],
    expected_core_metadata: _CoreMetadataProjection,
) -> list[str]:
    failures: list[str] = []
    missing = sorted(SDIST_GENERATED_METADATA_FILES - set(payloads))
    if missing:
        failures.append(f"sdist missing generated metadata files: {', '.join(missing)}")

    package_info_names = ("PKG-INFO", "agency_runtime.egg-info/PKG-INFO")
    for name in package_info_names:
        payload = payloads.get(name)
        if payload is not None:
            metadata = BytesParser(policy=policy.default).parsebytes(payload)
            failures.extend(
                _project_metadata_failures(
                    metadata,
                    label=f"sdist {name}",
                    expected_version=expected_version,
                    expected_dependencies=expected_dependencies,
                    expected_core_metadata=expected_core_metadata,
                    require_classifiers=True,
                )
            )
    root_info = payloads.get(package_info_names[0])
    egg_info = payloads.get(package_info_names[1])
    if root_info is not None and egg_info is not None and root_info != egg_info:
        failures.append("sdist PKG-INFO copies differ")

    entry_points = payloads.get("agency_runtime.egg-info/entry_points.txt")
    if entry_points is not None:
        failures.extend(_console_scripts_payload_failures(entry_points, label="sdist"))
    top_level = payloads.get("agency_runtime.egg-info/top_level.txt")
    if top_level is not None:
        try:
            top_levels = top_level.decode("utf-8").splitlines()
        except UnicodeDecodeError:
            top_levels = []
        if top_levels != ["agency_runtime"]:
            failures.append("sdist generated top_level.txt contract is invalid")

    requires = payloads.get("agency_runtime.egg-info/requires.txt")
    if requires is not None:
        try:
            observed_dependencies = _requires_txt_dependencies(requires)
        except ValueError:
            observed_dependencies = ()
            failures.append("sdist generated requires.txt is invalid or duplicated")
        if observed_dependencies != expected_dependencies:
            failures.append("sdist generated requires.txt does not match committed pyproject")

    dependency_links = payloads.get("agency_runtime.egg-info/dependency_links.txt")
    if dependency_links is not None and dependency_links.strip():
        failures.append("sdist generated dependency_links.txt must be empty")
    setup_cfg = payloads.get("setup.cfg")
    if setup_cfg is not None:
        failures.extend(_setup_cfg_failures(setup_cfg))
    sources = payloads.get("agency_runtime.egg-info/SOURCES.txt")
    if sources is not None:
        failures.extend(_sources_manifest_failures(sources, payloads))
    return failures


def _metadata_failures(
    metadata_name: str,
    metadata: Message,
    wheel_names: set[str],
    wheel_payloads: dict[str, bytes],
    *,
    expected_version: str,
    expected_dependencies: tuple[str, ...],
    expected_license: bytes,
    expected_core_metadata: _CoreMetadataProjection,
) -> list[str]:
    failures = _project_metadata_failures(
        metadata,
        label="wheel METADATA",
        expected_version=expected_version,
        expected_dependencies=expected_dependencies,
        expected_core_metadata=expected_core_metadata,
        require_classifiers=True,
    )
    expected_dist_info = f"agency_runtime-{expected_version}.dist-info"
    if metadata_name != f"{expected_dist_info}/METADATA":
        failures.append(f"unexpected wheel metadata path: {metadata_name}")

    for required in sorted(WHEEL_METADATA_FILES - {"METADATA"}):
        name = f"{expected_dist_info}/{required}"
        if name not in wheel_names:
            failures.append(f"wheel missing metadata file: {name}")

    license_payload = wheel_payloads.get(f"{expected_dist_info}/licenses/LICENSE")
    if license_payload is not None and license_payload != expected_license:
        failures.append("wheel license payload differs from committed HEAD")
    failures.extend(_wheel_control_failures(expected_dist_info, wheel_payloads))
    failures.extend(_console_script_failures(expected_dist_info, wheel_payloads))
    failures.extend(_top_level_package_failures(expected_dist_info, wheel_payloads))
    failures.extend(_record_failures(expected_dist_info, wheel_payloads))
    return failures


def verify(
    dist_dir: Path,
    *,
    repository_root: Path | None = None,
    expected_commit: str | None = None,
) -> list[str]:
    failures: list[str] = []
    if expected_commit is None:
        return ["distribution verification requires an expected reviewed commit"]
    root = (
        Path(__file__).resolve().parents[1]
        if repository_root is None
        else repository_root.resolve()
    )
    try:
        git = _release_git(root)
        reviewed_commit = _reviewed_checkout(root, expected_commit, git=git)
        reviewed_timestamp = _reviewed_commit_timestamp(
            root,
            reviewed_commit,
            git=git,
        )
        committed_package, committed_support, object_algorithm = _tracked_release_payloads(
            root,
            reviewed_commit,
            git=git,
        )
        project_contract = _committed_project_contract(
            root,
            committed_package,
            committed_support,
            git=git,
        )
        version = project_contract.version
        expected_dependencies = project_contract.dependencies
    except (OSError, RuntimeError, ValueError) as exc:
        return [str(exc)]

    try:
        with _bound_distribution_artifacts(dist_dir, version=version) as (
            wheel_stream,
            sdist_stream,
        ):
            wheel_names, wheel_payloads = _wheel_payload(
                wheel_stream,
                expected_timestamp=reviewed_timestamp,
            )
            sdist_names, sdist_payloads = _sdist_payload(
                sdist_stream,
                expected_root=f"agency_runtime-{version}",
                expected_timestamp=reviewed_timestamp,
            )
    except _ArtifactSetError as exc:
        return list(exc.failures)
    except (OSError, tarfile.TarError, zipfile.BadZipFile, ValueError) as exc:
        return [str(exc)]

    try:
        metadata_name, metadata_payload = _metadata(wheel_payloads)
        metadata = BytesParser(policy=policy.default).parsebytes(metadata_payload)
    except ValueError as exc:
        return [str(exc)]

    committed_package_files = set(committed_package)
    committed_support_files = set(committed_support)
    committed_sdist_files = committed_package_files | committed_support_files
    required_package_files = REQUIRED_PACKAGE_FILES | committed_package_files
    required_sdist_files = REQUIRED_SDIST_FILES | committed_sdist_files
    failures.extend(
        _missing_file_failures(
            set(wheel_payloads),
            set(sdist_payloads),
            required_package_files,
            required_sdist_files,
        )
    )
    failures.extend(
        _wheel_payload_contract_failures(
            wheel_payloads,
            committed_package_files,
            version=version,
        )
    )
    failures.extend(_sdist_payload_contract_failures(sdist_payloads, committed_sdist_files))
    for artifact, names in (("wheel", wheel_names), ("sdist", sdist_names)):
        failures.extend(_junk_failures(artifact, names))
    failures.extend(
        _payload_mismatch_failures(
            required_package_files,
            wheel_payloads,
            sdist_payloads,
        )
    )
    failures.extend(
        _committed_payload_failures(
            "wheel",
            wheel_payloads,
            committed_package,
            object_algorithm,
        )
    )
    failures.extend(
        _committed_payload_failures(
            "sdist package",
            sdist_payloads,
            committed_package,
            object_algorithm,
        )
    )
    failures.extend(
        _committed_payload_failures(
            "sdist release support",
            sdist_payloads,
            committed_support,
            object_algorithm,
        )
    )
    failures.extend(
        _metadata_failures(
            metadata_name,
            metadata,
            set(wheel_payloads),
            wheel_payloads,
            expected_version=version,
            expected_dependencies=expected_dependencies,
            expected_license=project_contract.license_payload,
            expected_core_metadata=project_contract.core_metadata,
        )
    )
    failures.extend(_metadata_parity_failures(metadata, sdist_payloads))
    failures.extend(
        _sdist_generated_metadata_failures(
            sdist_payloads,
            expected_version=version,
            expected_dependencies=expected_dependencies,
            expected_core_metadata=project_contract.core_metadata,
        )
    )
    try:
        _reviewed_checkout(root, reviewed_commit, git=git)
    except (OSError, RuntimeError, ValueError) as exc:
        failures.append(str(exc))
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist_dir", nargs="?", type=Path, default=Path("dist"))
    parser.add_argument(
        "--expected-commit",
        required=True,
        help="Full immutable Git commit object ID captured before the build",
    )
    args = parser.parse_args(argv)
    lexical_dist = Path(os.path.abspath(os.path.expanduser(os.fspath(args.dist_dir))))
    failures = verify(lexical_dist, expected_commit=args.expected_commit)
    if failures:
        print("Distribution verification failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Distribution verification passed (wheel and sdist contents match release policy).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
