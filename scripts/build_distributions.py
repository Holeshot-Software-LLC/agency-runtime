"""Build distributions from canonical bytes in one reviewed Git commit."""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import os
import re
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from agency_runtime.core.owned_process import run_bounded_process
from agency_runtime.core.private_paths import bootstrap_private_directory
from agency_runtime.core.process_argv import (
    absolute_executable_path,
    freeze_persistent_process_argv,
    freeze_process_argv,
    prepare_process_argv,
    sanitized_executable_search_path,
)
from agency_runtime.core.store.security import (
    assert_storage_parent_chain,
    is_link_or_reparse_point,
    restrict_path_permissions,
    restrict_windows_acl,
    storage_creation_boundary_is_trusted,
    storage_parent_is_trusted,
)

try:  # Support both ``python -m scripts...`` and direct script execution.
    from scripts.canonicalize_distributions import canonicalize_distributions
    from scripts.release_contract import (
        MAX_RELEASE_ENTRIES,
        MAX_RELEASE_FILE_BYTES,
        MAX_RELEASE_TOTAL_BYTES,
        MAX_TREE_MANIFEST_BYTES,
        RELEASE_SOURCE_PATHS,
        WheelProfile,
        host_wheel_profile,
        is_release_source,
        partition_release_payloads,
        reviewed_checkout,
        safe_release_name,
    )
    from scripts.release_git import ReleaseGit
except ModuleNotFoundError as exc:  # pragma: no cover - direct-script compatibility
    if exc.name != "scripts":
        raise
    from canonicalize_distributions import canonicalize_distributions  # type: ignore[no-redef]
    from release_contract import (  # type: ignore[no-redef]
        MAX_RELEASE_ENTRIES,
        MAX_RELEASE_FILE_BYTES,
        MAX_RELEASE_TOTAL_BYTES,
        MAX_TREE_MANIFEST_BYTES,
        RELEASE_SOURCE_PATHS,
        WheelProfile,
        host_wheel_profile,
        is_release_source,
        partition_release_payloads,
        reviewed_checkout,
        safe_release_name,
    )
    from release_git import ReleaseGit  # type: ignore[no-redef]

MAX_ARTIFACT_FILE_BYTES = 128 * 1024 * 1024
MAX_ARTIFACT_TOTAL_BYTES = 256 * 1024 * 1024
MAX_GIT_BATCH_OVERHEAD_BYTES = 128
MAX_BUILD_OUTPUT_CHARS = 1024 * 1024
BUILD_TIMEOUT_SECONDS = 600
COPY_CHUNK_BYTES = 64 * 1024
_FULL_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_TREE_ENTRY = re.compile(
    rb"(100644|100755|120000|160000) (blob|commit|tree) "
    rb"([0-9a-f]{40}|[0-9a-f]{64}) +(-|0|[1-9][0-9]*)\Z"
)
_BATCH_HEADER = re.compile(rb"([0-9a-f]{40}|[0-9a-f]{64}) blob (0|[1-9][0-9]*)\Z")
_SAFE_OUTPUT = re.compile(r"[^\x00\r\n]+\Z")
_REPARSE_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_AT_FDCWD = -100
_RENAME_NOREPLACE = 1
_RELEASE_PATHS = RELEASE_SOURCE_PATHS


@dataclass(frozen=True, slots=True)
class ReleaseEntry:
    """One bounded non-executable release-source blob from the reviewed tree."""

    path: PurePosixPath
    object_id: str
    size: int


@dataclass(frozen=True, slots=True)
class DirectoryIdentity:
    """Stable identity of one real staging directory."""

    device: int
    inode: int
    mode: int
    file_attributes: int


@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    """Stable identity of one regular single-link build artifact."""

    name: str
    device: int
    inode: int
    mode: int
    size: int
    modified_ns: int
    changed_ns: int
    file_attributes: int
    link_count: int
    sha256: str


def _metadata_identity(
    metadata: os.stat_result,
    *,
    platform_name: str | None = None,
) -> tuple[int, ...]:
    """Return the stable fields used to seal a file path to an open handle."""

    effective_platform = os.name if platform_name is None else platform_name
    mode = int(metadata.st_mode)
    if effective_platform == "nt":
        # CPython derives execute bits from an .exe path suffix for lstat(), but
        # fstat() has no path and reports the same open file without those bits.
        # Preserve the file type and writable/read-only bits in the identity.
        mode &= ~0o111
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        mode,
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
        0 if os.name == "nt" else int(metadata.st_ctime_ns),
        int(getattr(metadata, "st_file_attributes", 0) or 0),
        int(getattr(metadata, "st_nlink", 0) or 0),
    )


def _is_link_or_reparse_metadata(metadata: os.stat_result) -> bool:
    return stat.S_ISLNK(metadata.st_mode) or bool(
        int(getattr(metadata, "st_file_attributes", 0) or 0) & _REPARSE_ATTRIBUTE
    )


def _directory_identity(path: Path) -> DirectoryIdentity:
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise RuntimeError(f"release directory is unavailable: {path}") from exc
    if _is_link_or_reparse_metadata(metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeError(f"release directory must be a real directory: {path}")
    inode = int(metadata.st_ino)
    if inode <= 0:
        raise RuntimeError(f"release directory has no stable identity: {path}")
    return DirectoryIdentity(
        device=int(metadata.st_dev),
        inode=inode,
        mode=int(metadata.st_mode),
        file_attributes=int(getattr(metadata, "st_file_attributes", 0) or 0),
    )


def _require_directory_identity(path: Path, expected: DirectoryIdentity) -> None:
    if _directory_identity(path) != expected:
        raise RuntimeError(f"release directory changed identity: {path}")


def _secure_private_directory(path: Path) -> DirectoryIdentity:
    restrict_path_permissions(
        path,
        directory=True,
        is_windows=os.name == "nt",
        link_checker=is_link_or_reparse_point,
        windows_acl=lambda candidate, *, directory: restrict_windows_acl(
            candidate,
            directory=directory,
            is_windows=os.name == "nt",
        ),
    )
    if not storage_parent_is_trusted(
        path,
        is_windows=os.name == "nt",
        final_parent=True,
    ):
        raise PermissionError(f"release staging directory is not private: {path}")
    return _directory_identity(path)


def _commit_timestamp(git: ReleaseGit, commit: str) -> int:
    raw = git.run_bytes(["show", "-s", "--format=%ct", commit])
    try:
        text = raw.decode("ascii", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise RuntimeError("reviewed commit timestamp is invalid") from exc
    if not re.fullmatch(r"0|[1-9][0-9]*", text):
        raise RuntimeError("reviewed commit timestamp is invalid")
    return int(text)


def _portable_component_aliases(entries: list[ReleaseEntry]) -> None:
    full_paths = {entry.path.as_posix().casefold() for entry in entries}
    if len(full_paths) != len(entries):
        raise RuntimeError("reviewed release tree contains case-aliasing paths")

    spellings: dict[str, str] = {}
    for entry in entries:
        parts = entry.path.parts
        for length in range(1, len(parts) + 1):
            spelling = "/".join(parts[:length])
            key = "/".join(part.casefold() for part in parts[:length])
            previous = spellings.setdefault(key, spelling)
            if previous != spelling:
                raise RuntimeError("reviewed release tree contains case-aliasing path components")
            if length < len(parts) and key in full_paths:
                raise RuntimeError(
                    "reviewed release tree contains a file/directory prefix collision"
                )


def _release_entries(git: ReleaseGit, commit: str) -> tuple[list[ReleaseEntry], str]:
    manifest = git.run_bytes(
        ["ls-tree", "-r", "-l", "-z", "--full-tree", commit, "--", *_RELEASE_PATHS],
        max_stdout_bytes=MAX_TREE_MANIFEST_BYTES,
    )
    entries: list[ReleaseEntry] = []
    names: set[str] = set()
    algorithms: set[str] = set()
    total_size = 0
    try:
        for raw_entry in manifest.split(b"\0"):
            if not raw_entry:
                continue
            metadata, encoded_name = raw_entry.split(b"\t", 1)
            match = _TREE_ENTRY.fullmatch(metadata)
            if match is None:
                raise RuntimeError("reviewed Git tree manifest is malformed")
            mode, object_type, encoded_id, encoded_size = match.groups()
            name = safe_release_name(encoded_name.decode("utf-8", errors="strict")).as_posix()
            if not is_release_source(name):
                continue
            if mode != b"100644" or object_type != b"blob":
                raise RuntimeError(
                    f"release source must be a non-executable regular Git blob: {name}"
                )
            object_id = encoded_id.decode("ascii", errors="strict")
            algorithm = "sha1" if len(object_id) == 40 else "sha256"
            size = int(encoded_size)
            if size > MAX_RELEASE_FILE_BYTES:
                raise RuntimeError(f"release source exceeds its file-size budget: {name}")
            total_size += size
            if total_size > MAX_RELEASE_TOTAL_BYTES:
                raise RuntimeError("reviewed release tree exceeds its aggregate byte budget")
            if name in names:
                raise RuntimeError(f"reviewed release tree duplicates a release source: {name}")
            names.add(name)
            entries.append(ReleaseEntry(PurePosixPath(name), object_id, size))
            algorithms.add(algorithm)
            if len(entries) > MAX_RELEASE_ENTRIES:
                raise RuntimeError("reviewed release tree exceeds its entry budget")
    except (UnicodeDecodeError, ValueError) as exc:
        raise RuntimeError("reviewed Git tree manifest is malformed") from exc

    package, support = partition_release_payloads(names)
    if not package or not support or "pyproject.toml" not in support or "LICENSE" not in support:
        raise RuntimeError("reviewed release tree is incomplete")
    if len(algorithms) != 1:
        raise RuntimeError("reviewed release tree mixes Git object hash algorithms")
    _portable_component_aliases(entries)
    return sorted(entries, key=lambda item: item.path.as_posix()), algorithms.pop()


def _batch_blob_output(git: ReleaseGit, entries: list[ReleaseEntry]) -> bytes:
    queries = b"".join(entry.object_id.encode("ascii") + b"\n" for entry in entries)
    maximum = sum(entry.size for entry in entries) + len(entries) * MAX_GIT_BATCH_OVERHEAD_BYTES
    return git.run_bytes(
        ["cat-file", "--batch"],
        input_bytes=queries,
        max_stdout_bytes=maximum,
    )


def _parse_blob_batch(
    entries: list[ReleaseEntry],
    output: bytes,
    *,
    algorithm: str,
) -> tuple[memoryview, ...]:
    payloads: list[memoryview] = []
    cursor = 0
    entire = memoryview(output)
    for entry in entries:
        line_end = output.find(b"\n", cursor, cursor + MAX_GIT_BATCH_OVERHEAD_BYTES)
        if line_end < 0:
            raise RuntimeError("Git blob batch header is missing or overlong")
        header = output[cursor:line_end]
        match = _BATCH_HEADER.fullmatch(header)
        if match is None:
            raise RuntimeError("Git blob batch header is malformed")
        object_id, encoded_size = match.groups()
        if object_id != entry.object_id.encode("ascii") or encoded_size != str(entry.size).encode(
            "ascii"
        ):
            raise RuntimeError(f"Git blob batch identity mismatch: {entry.path.as_posix()}")
        payload_start = line_end + 1
        payload_end = payload_start + entry.size
        if payload_end >= len(output) or output[payload_end : payload_end + 1] != b"\n":
            raise RuntimeError(f"Git blob batch payload is truncated: {entry.path.as_posix()}")
        payload = entire[payload_start:payload_end]
        digest = hashlib.new(algorithm)
        digest.update(f"blob {entry.size}\0".encode("ascii"))
        digest.update(payload)
        if digest.hexdigest() != entry.object_id:
            raise RuntimeError(
                f"Git blob payload failed object verification: {entry.path.as_posix()}"
            )
        payloads.append(payload)
        cursor = payload_end + 1
    if cursor != len(output):
        raise RuntimeError("Git blob batch contains trailing or unrequested content")
    return tuple(payloads)


def _set_timestamp(path: Path, timestamp: int) -> None:
    if _is_link_or_reparse_metadata(os.lstat(path)):
        raise RuntimeError("canonical source staging encountered a link or reparse point")
    if os.name == "nt":
        os.utime(path, (timestamp, timestamp))
    else:
        os.utime(path, (timestamp, timestamp), follow_symlinks=False)


def _source_directories(entries: list[ReleaseEntry]) -> tuple[PurePosixPath, ...]:
    directories: set[PurePosixPath] = set()
    for entry in entries:
        parent = entry.path.parent
        while parent != PurePosixPath("."):
            directories.add(parent)
            parent = parent.parent
    return tuple(sorted(directories, key=lambda item: (len(item.parts), item.as_posix())))


def _write_canonical_tree(
    destination: Path,
    entries: list[ReleaseEntry],
    payloads: tuple[memoryview, ...],
    *,
    timestamp: int,
) -> None:
    destination.mkdir(mode=0o700)
    directories: dict[Path, DirectoryIdentity] = {destination: _directory_identity(destination)}
    for relative in _source_directories(entries):
        directory = destination.joinpath(*relative.parts)
        directory.mkdir(mode=0o700)
        directories[directory] = _directory_identity(directory)

    for entry, payload in zip(entries, payloads, strict=True):
        target = destination.joinpath(*entry.path.parts)
        with target.open("xb") as stream:
            for offset in range(0, len(payload), COPY_CHUNK_BYTES):
                stream.write(payload[offset : offset + COPY_CHUNK_BYTES])
            stream.flush()
            os.fsync(stream.fileno())
        target.chmod(0o644)
        _set_timestamp(target, timestamp)
        metadata = os.lstat(target)
        link_count = int(getattr(metadata, "st_nlink", 0) or 0)
        if (
            _is_link_or_reparse_metadata(metadata)
            or not stat.S_ISREG(metadata.st_mode)
            or link_count != 1
        ):
            raise RuntimeError(f"canonical source is not a single-link regular file: {target}")

    for directory, identity in sorted(
        directories.items(), key=lambda item: len(item[0].parts), reverse=True
    ):
        _require_directory_identity(directory, identity)
        directory.chmod(0o755)
        _set_timestamp(directory, timestamp)


def materialize_reviewed_sources(
    root: Path,
    destination: Path,
    commit: str,
    *,
    git: ReleaseGit | None = None,
) -> list[ReleaseEntry]:
    """Write the exact bounded release payload from authenticated Git blobs."""

    if destination.exists() or os.path.lexists(destination):
        raise RuntimeError("canonical source destination already exists")
    session = ReleaseGit.discover(root) if git is None else git
    entries, algorithm = _release_entries(session, commit)
    output = _batch_blob_output(session, entries)
    payloads = _parse_blob_batch(entries, output, algorithm=algorithm)
    _write_canonical_tree(
        destination,
        entries,
        payloads,
        timestamp=_commit_timestamp(session, commit),
    )
    return entries


def _expected_materialized_file_mode(
    path: Path,
    *,
    platform_name: str | None = None,
) -> int:
    """Return the mode CPython can faithfully report for canonical source bytes."""

    effective_platform = os.name if platform_name is None else platform_name
    if effective_platform != "nt":
        return 0o644
    # Windows has no POSIX execute bit. CPython projects .exe files as executable
    # even after chmod(0o644), while ordinary writable files are reported as 0666.
    # The authenticated Git manifest separately requires every source blob to be
    # mode 100644, so accepting this projection does not accept an executable Git
    # tree entry.
    return 0o777 if path.suffix.casefold() == ".exe" else 0o666


def _validate_materialized_entry_contract(
    entry: ReleaseEntry,
    *,
    names: set[str],
    accumulated_size: int,
) -> int:
    name = safe_release_name(entry.path.as_posix()).as_posix()
    if name != entry.path.as_posix() or name in names:
        raise RuntimeError("materialized release tree contains an invalid or duplicate path")
    names.add(name)
    if entry.size < 0 or entry.size > MAX_RELEASE_FILE_BYTES:
        raise RuntimeError(
            f"materialized release source exceeds its file-size budget: {entry.path.as_posix()}"
        )
    total_size = accumulated_size + entry.size
    if total_size > MAX_RELEASE_TOTAL_BYTES:
        raise RuntimeError("materialized release tree exceeds its aggregate byte budget")
    if not _FULL_OBJECT_ID.fullmatch(entry.object_id):
        raise RuntimeError(
            f"materialized release source has an invalid object ID: {entry.path.as_posix()}"
        )
    return total_size


def _verify_materialized_entry(source: Path, entry: ReleaseEntry) -> None:
    target = source.joinpath(*entry.path.parts)
    try:
        before_path = os.lstat(target)
    except OSError as exc:
        raise RuntimeError(
            f"materialized release source is unavailable: {entry.path.as_posix()}"
        ) from exc
    link_count = int(getattr(before_path, "st_nlink", 0) or 0)
    if (
        _is_link_or_reparse_metadata(before_path)
        or not stat.S_ISREG(before_path.st_mode)
        or link_count != 1
    ):
        raise RuntimeError(
            "materialized release source must be a single-link regular file: "
            f"{entry.path.as_posix()}"
        )
    expected_mode = _expected_materialized_file_mode(target)
    if stat.S_IMODE(before_path.st_mode) != expected_mode:
        raise RuntimeError(
            f"materialized release source has a noncanonical mode: {entry.path.as_posix()}"
        )
    if int(before_path.st_ino) <= 0:
        raise RuntimeError(
            f"materialized release source has no stable identity: {entry.path.as_posix()}"
        )
    if int(before_path.st_size) != entry.size:
        raise RuntimeError(
            f"materialized release source has an unexpected size: {entry.path.as_posix()}"
        )
    expected_identity = _metadata_identity(before_path)
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(target, flags)
    except OSError as exc:
        raise RuntimeError(
            f"materialized release source could not be opened safely: {entry.path.as_posix()}"
        ) from exc

    algorithm = "sha1" if len(entry.object_id) == 40 else "sha256"
    digest = hashlib.new(algorithm)
    digest.update(f"blob {entry.size}\0".encode("ascii"))
    observed = 0
    try:
        opened = os.fstat(descriptor)
        if _metadata_identity(opened) != expected_identity:
            raise RuntimeError(
                f"materialized release source changed before hashing: {entry.path.as_posix()}"
            )
        while True:
            chunk = os.read(
                descriptor,
                min(COPY_CHUNK_BYTES, entry.size - observed + 1),
            )
            if not chunk:
                break
            observed += len(chunk)
            if observed > entry.size:
                raise RuntimeError(
                    "materialized release source exceeds its authenticated size: "
                    f"{entry.path.as_posix()}"
                )
            digest.update(chunk)
        after_handle = os.fstat(descriptor)
    finally:
        os.close(descriptor)

    try:
        after_path = os.lstat(target)
    except OSError as exc:
        raise RuntimeError(
            f"materialized release source changed while hashing: {entry.path.as_posix()}"
        ) from exc
    if (
        observed != entry.size
        or _metadata_identity(after_handle) != expected_identity
        or _metadata_identity(after_path) != expected_identity
    ):
        raise RuntimeError(
            f"materialized release source changed while hashing: {entry.path.as_posix()}"
        )
    if digest.hexdigest() != entry.object_id:
        raise RuntimeError(
            f"materialized release source failed object verification: {entry.path.as_posix()}"
        )


def _verify_materialized_sources(
    source: Path,
    entries: list[ReleaseEntry],
) -> None:
    """Rehash identity-sealed staged files before any build backend can read them."""

    if len(entries) > MAX_RELEASE_ENTRIES:
        raise RuntimeError("materialized release tree exceeds its entry budget")
    total_size = 0
    names: set[str] = set()
    for entry in entries:
        total_size = _validate_materialized_entry_contract(
            entry,
            names=names,
            accumulated_size=total_size,
        )
        _verify_materialized_entry(source, entry)


def _checked_destination(root: Path, requested: Path, git: ReleaseGit) -> Path:
    expanded = requested.expanduser()
    if not _SAFE_OUTPUT.fullmatch(str(expanded)) or expanded.name in {"", ".", ".."}:
        raise ValueError("distribution destination is invalid")
    lexical = Path(os.path.abspath(expanded))
    if os.path.lexists(lexical):
        raise ValueError("distribution destination must not already exist")
    parent = lexical.parent
    assert_storage_parent_chain(parent, allow_missing=False)
    parent = parent.resolve(strict=True)
    destination = parent / lexical.name
    if not storage_creation_boundary_is_trusted(
        parent,
        destination,
        is_windows=os.name == "nt",
    ):
        raise PermissionError("distribution destination parent is not a trusted namespace")
    if os.path.lexists(destination):
        raise ValueError("distribution destination must not already exist")

    try:
        relative = destination.relative_to(root)
        parent_relative = parent.relative_to(root)
    except ValueError:
        return destination
    probes = (
        relative / ".agency-release-sentinel",
        parent_relative / ".agency-release-probe" / "sentinel",
    )
    if any(not git.is_ignored(candidate.as_posix()) for candidate in probes):
        raise ValueError("in-repository distribution staging must be Git-ignored")
    return destination


def _private_build_environment(
    root: Path,
    source: Path,
    scratch: Path,
    *,
    timestamp: int,
) -> dict[str, str]:
    home = scratch / "home"
    temporary = scratch / "tmp"
    home.mkdir(mode=0o700)
    temporary.mkdir(mode=0o700)
    environment = {
        "HOME": str(home),
        "PATH": sanitized_executable_search_path(
            os.environ.get("PATH", ""),
            current_directory=source,
            forbidden_roots=(root, source),
        ),
        "PIP_CONFIG_FILE": os.devnull,
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_INPUT": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONNOUSERSITE": "1",
        "PYTHONUTF8": "1",
        "SOURCE_DATE_EPOCH": str(timestamp),
        "TEMP": str(temporary),
        "TMP": str(temporary),
        "TMPDIR": str(temporary),
        "USERPROFILE": str(home),
    }
    if os.name == "nt":
        for name in ("SYSTEMROOT", "WINDIR", "PATHEXT"):
            value = os.environ.get(name)
            if value and "\x00" not in value:
                environment[name] = value
    return environment


def _invoke_build(
    root: Path,
    source: Path,
    output: Path,
    scratch: Path,
    *,
    timestamp: int,
) -> None:
    python = absolute_executable_path(sys.executable)
    prepared = prepare_process_argv(
        [
            python,
            "-I",
            "-m",
            "build",
            "--sdist",
            "--wheel",
            "--outdir",
            str(output),
            str(source),
        ]
    )
    prepared = (
        freeze_process_argv(prepared, forbidden_roots=(root, source))
        if os.name == "nt"
        else freeze_persistent_process_argv(
            prepared,
            forbidden_roots=(root, source),
        )
    )
    result = run_bounded_process(
        prepared,
        cwd=str(source),
        env=_private_build_environment(root, source, scratch, timestamp=timestamp),
        timeout=BUILD_TIMEOUT_SECONDS,
        max_output_chars=MAX_BUILD_OUTPUT_CHARS,
    )
    if result.timed_out:
        raise RuntimeError("isolated distribution build exceeded its time limit")
    if result.stdout_truncated or result.stderr_truncated:
        raise RuntimeError("isolated distribution build exceeded its output limit")
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        suffix = f": {detail}" if detail else ""
        raise RuntimeError(f"isolated distribution build exited {result.returncode}{suffix}")


def _artifact_identity(path: Path) -> ArtifactIdentity:
    metadata = os.lstat(path)
    link_count = int(getattr(metadata, "st_nlink", 0) or 0)
    if (
        _is_link_or_reparse_metadata(metadata)
        or not stat.S_ISREG(metadata.st_mode)
        or link_count != 1
    ):
        raise RuntimeError(f"distribution artifact must be a single-link regular file: {path}")
    if int(metadata.st_size) > MAX_ARTIFACT_FILE_BYTES:
        raise RuntimeError(f"distribution artifact exceeds its file-size budget: {path}")
    inode = int(metadata.st_ino)
    if inode <= 0:
        raise RuntimeError(f"distribution artifact has no stable identity: {path}")
    expected = (
        int(metadata.st_dev),
        inode,
        int(metadata.st_mode),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
        0 if os.name == "nt" else int(metadata.st_ctime_ns),
        int(getattr(metadata, "st_file_attributes", 0) or 0),
        link_count,
    )
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_NOFOLLOW", 0))
    descriptor = os.open(path, flags)
    digest = hashlib.sha256()
    observed = 0
    try:
        opened = os.fstat(descriptor)
        opened_identity = (
            int(opened.st_dev),
            int(opened.st_ino),
            int(opened.st_mode),
            int(opened.st_size),
            int(opened.st_mtime_ns),
            0 if os.name == "nt" else int(opened.st_ctime_ns),
            int(getattr(opened, "st_file_attributes", 0) or 0),
            int(getattr(opened, "st_nlink", 0) or 0),
        )
        if opened_identity != expected:
            raise RuntimeError(f"distribution artifact changed before hashing: {path}")
        while True:
            chunk = os.read(descriptor, COPY_CHUNK_BYTES)
            if not chunk:
                break
            observed += len(chunk)
            if observed > MAX_ARTIFACT_FILE_BYTES:
                raise RuntimeError(f"distribution artifact exceeds its file-size budget: {path}")
            digest.update(chunk)
        after_handle = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_path = os.lstat(path)
    after_handle_identity = (
        int(after_handle.st_dev),
        int(after_handle.st_ino),
        int(after_handle.st_mode),
        int(after_handle.st_size),
        int(after_handle.st_mtime_ns),
        0 if os.name == "nt" else int(after_handle.st_ctime_ns),
        int(getattr(after_handle, "st_file_attributes", 0) or 0),
        int(getattr(after_handle, "st_nlink", 0) or 0),
    )
    after_path_identity = (
        int(after_path.st_dev),
        int(after_path.st_ino),
        int(after_path.st_mode),
        int(after_path.st_size),
        int(after_path.st_mtime_ns),
        0 if os.name == "nt" else int(after_path.st_ctime_ns),
        int(getattr(after_path, "st_file_attributes", 0) or 0),
        int(getattr(after_path, "st_nlink", 0) or 0),
    )
    if (
        observed != expected[3]
        or after_handle_identity != expected
        or after_path_identity != expected
    ):
        raise RuntimeError(f"distribution artifact changed while hashing: {path}")
    return ArtifactIdentity(
        name=path.name,
        device=expected[0],
        inode=inode,
        mode=expected[2],
        size=expected[3],
        modified_ns=expected[4],
        changed_ns=expected[5],
        file_attributes=expected[6],
        link_count=link_count,
        sha256=digest.hexdigest(),
    )


def _artifacts(
    directory: Path,
    *,
    expected_directory: DirectoryIdentity | None = None,
    profile: WheelProfile | None = None,
) -> tuple[Path, Path, tuple[ArtifactIdentity, ...]]:
    if expected_directory is not None:
        _require_directory_identity(directory, expected_directory)
    children: list[Path] = []
    with os.scandir(directory) as entries:
        for entry in entries:
            children.append(Path(entry.path))
            if len(children) > 2:
                raise RuntimeError(
                    "distribution build must produce exactly one wheel and one source archive"
                )
    children.sort(key=lambda path: path.name)
    identities = tuple(_artifact_identity(child) for child in children)
    if sum(identity.size for identity in identities) > MAX_ARTIFACT_TOTAL_BYTES:
        raise RuntimeError("distribution artifacts exceed their aggregate byte budget")
    wheels = [path for path in children if path.name.endswith(".whl")]
    sdists = [path for path in children if path.name.endswith(".tar.gz")]
    if len(children) != 2 or len(wheels) != 1 or len(sdists) != 1:
        raise RuntimeError(
            "distribution build must produce exactly one wheel and one source archive"
        )
    if profile is not None and not wheels[0].name.endswith(f"-{profile.tag}.whl"):
        raise RuntimeError(
            "distribution build produced a wheel outside the host-derived profile: "
            f"expected {profile.tag}, found {wheels[0].name}"
        )
    return wheels[0], sdists[0], identities


def _require_artifact_identities(
    directory: Path,
    expected: tuple[ArtifactIdentity, ...],
    *,
    expected_directory: DirectoryIdentity,
    profile: WheelProfile | None = None,
) -> None:
    _wheel, _sdist, observed = _artifacts(
        directory,
        expected_directory=expected_directory,
        profile=profile,
    )
    if observed != tuple(sorted(expected, key=lambda item: item.name)):
        raise RuntimeError("distribution artifacts changed identity before publication")


def _linux_rename_no_replace(source: Path, destination: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise RuntimeError("atomic no-replace publication is unsupported on this Linux host")
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    flags = os.O_RDONLY | int(getattr(os, "O_DIRECTORY", 0))
    descriptor = os.open(source.parent, flags)
    try:
        result = renameat2(
            descriptor,
            os.fsencode(source.name),
            descriptor,
            os.fsencode(destination.name),
            _RENAME_NOREPLACE,
        )
    finally:
        os.close(descriptor)
    if result == 0:
        return
    error = ctypes.get_errno()
    if error in {errno.EEXIST, errno.ENOTEMPTY}:
        raise FileExistsError("distribution destination appeared before publication")
    if error in {
        errno.EINVAL,
        errno.ENOSYS,
        getattr(errno, "EOPNOTSUPP", errno.ENOSYS),
    }:
        raise RuntimeError("atomic no-replace publication is unsupported")
    raise OSError(error, os.strerror(error), str(destination))


def _windows_move_no_replace(source: Path, destination: Path) -> None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    move_file = kernel32.MoveFileExW
    move_file.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_ulong]
    move_file.restype = ctypes.c_int
    if move_file(str(source), str(destination), 0):
        return
    error = ctypes.get_last_error()
    if error in {80, 183}:
        raise FileExistsError("distribution destination appeared before publication")
    raise OSError(error, "atomic no-replace publication failed", str(destination))


def _publish_no_replace(
    source: Path,
    destination: Path,
    *,
    platform_name: str | None = None,
) -> None:
    if source.parent != destination.parent:
        raise RuntimeError("atomic publication requires sibling source and destination")
    platform = os.name if platform_name is None else platform_name
    if platform == "nt":
        _windows_move_no_replace(source, destination)
    elif platform == "posix" and sys.platform.startswith("linux"):
        _linux_rename_no_replace(source, destination)
    else:
        raise RuntimeError("atomic no-replace publication is unsupported on this platform")


def build_distributions(
    root: Path,
    destination: Path,
    *,
    expected_commit: str,
    create_private_parent: bool = False,
) -> tuple[Path, Path]:
    """Construct and atomically publish canonical reviewed-commit distributions."""

    root = root.resolve(strict=True)
    if not _FULL_OBJECT_ID.fullmatch(expected_commit):
        raise ValueError(
            "canonical distribution build requires one full lowercase commit object ID"
        )
    git = ReleaseGit.discover(root)
    reviewed_checkout(root, expected_commit, git=git)
    if create_private_parent:
        requested_parent = Path(os.path.abspath(destination.expanduser())).parent
        bootstrap_private_directory(requested_parent)
    output = _checked_destination(root, destination, git)
    timestamp = _commit_timestamp(git, expected_commit)
    profile = host_wheel_profile()

    with (
        tempfile.TemporaryDirectory(
            prefix=".agency-release-source-",
            dir=output.parent,
        ) as temporary,
        tempfile.TemporaryDirectory(
            prefix=".agency-release-artifacts-",
            dir=output.parent,
        ) as artifact_temporary,
    ):
        scratch = Path(temporary)
        scratch_identity = _secure_private_directory(scratch)
        source = scratch / "source"
        staged = Path(artifact_temporary)
        staged_identity = _secure_private_directory(staged)
        entries = materialize_reviewed_sources(root, source, expected_commit, git=git)
        _verify_materialized_sources(source, entries)
        _invoke_build(root, source, staged, scratch, timestamp=timestamp)
        _require_directory_identity(scratch, scratch_identity)
        wheel, sdist, _ = _artifacts(
            staged,
            expected_directory=staged_identity,
            profile=profile,
        )
        canonicalize_distributions(wheel, sdist, timestamp=timestamp)
        wheel, sdist, artifact_identities = _artifacts(
            staged,
            expected_directory=staged_identity,
            profile=profile,
        )
        reviewed_checkout(root, expected_commit, git=git)
        _require_directory_identity(staged, staged_identity)
        _require_artifact_identities(
            staged,
            artifact_identities,
            expected_directory=staged_identity,
            profile=profile,
        )
        _publish_no_replace(staged, output)
        _require_directory_identity(output, staged_identity)
        _require_artifact_identities(
            output,
            artifact_identities,
            expected_directory=staged_identity,
            profile=profile,
        )

    return output / wheel.name, output / sdist.name


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist_dir", nargs="?", type=Path, default=Path("dist"))
    parser.add_argument(
        "--expected-commit",
        required=True,
        help="Full immutable Git commit object ID captured before the build",
    )
    parser.add_argument(
        "--create-private-parent",
        action="store_true",
        help="Create or validate the destination parent as an owner-private directory",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        wheel, sdist = build_distributions(
            root,
            args.dist_dir,
            expected_commit=args.expected_commit,
            create_private_parent=args.create_private_parent,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Canonical distribution build failed: {exc}", file=sys.stderr)
        return 1
    print(f"Canonical distribution build passed: {wheel.name}, {sdist.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
