"""Cross-platform argv preparation that rejects unsafe Windows batch shims."""

from __future__ import annotations

import errno
import hashlib
import ntpath
import os
import posixpath
import re
import shutil
import stat
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path, PurePosixPath, PureWindowsPath

from agency_runtime.core.executable_namespace import assert_executable_namespace
from agency_runtime.core.windows_acl import windows_file_prevents_untrusted_mutation
from agency_runtime.core.windows_system import trusted_windows_system_executable

BinaryResolver = Callable[..., str | None]

_WINDOWS_REPARSE_POINT = 0x400
_WINDOWS_NATIVE_SUFFIXES = {".exe"}
_WINDOWS_DISCOVERY_SUFFIXES = {".bat", ".cmd", ".exe", ".ps1"}
_MAX_PERSISTENT_ARTIFACT_BYTES = 512 * 1024 * 1024
_REPOSITORY_MARKERS = (".git", ".hg", ".svn")


@dataclass(frozen=True, slots=True)
class ExecutableIdentity:
    """Filesystem identity frozen before an executable artifact is launched."""

    path: str
    device: int
    inode: int
    mode: int
    size: int
    modified_ns: int
    file_attributes: int


@dataclass(frozen=True, slots=True)
class PersistentArtifactIdentity:
    """Durable lexical, resolved, and content identity for a service artifact."""

    lexical_path: str
    lexical_device: int
    lexical_inode: int
    lexical_mode: int
    lexical_size: int
    lexical_modified_ns: int
    lexical_file_attributes: int
    link_target: str | None
    resolved_path: str
    resolved_device: int
    resolved_inode: int
    resolved_mode: int
    resolved_size: int
    resolved_modified_ns: int
    resolved_file_attributes: int
    sha256: str

    def manifest(self) -> dict[str, int | str | None]:
        """Return a stable JSON-safe representation."""

        return {field: getattr(self, field) for field in self.__dataclass_fields__}

    @classmethod
    def from_manifest(cls, value: object) -> PersistentArtifactIdentity:
        """Decode one bounded, type-exact ownership-manifest identity."""

        if not isinstance(value, dict):
            raise ValueError("persistent artifact identity must be an object")
        fields = cls.__dataclass_fields__
        if not set(fields).issubset(value):
            raise ValueError("persistent artifact identity is incomplete")
        strings = {"lexical_path", "resolved_path", "sha256"}
        integers = set(fields).difference(strings, {"link_target"})
        for name in strings:
            item = value[name]
            if (
                not isinstance(item, str)
                or not item
                or len(item) > 32_768
                or any(ord(character) < 32 or ord(character) == 127 for character in item)
            ):
                raise ValueError(f"persistent artifact {name} is invalid")
        link_target = value["link_target"]
        if link_target is not None and (
            not isinstance(link_target, str)
            or len(link_target) > 32_768
            or any(ord(character) < 32 or ord(character) == 127 for character in link_target)
        ):
            raise ValueError("persistent artifact link_target is invalid")
        for name in integers:
            item = value[name]
            if isinstance(item, bool) or not isinstance(item, int) or item < 0:
                raise ValueError(f"persistent artifact {name} is invalid")
        if re.fullmatch(r"[0-9a-f]{64}", str(value["sha256"])) is None:
            raise ValueError("persistent artifact sha256 is invalid")
        return cls(**{name: value[name] for name in fields})


class PreparedProcessArgv(list[str]):
    """An argv carrying the artifacts and identities approved for one launch."""

    __slots__ = (
        "argument_offset",
        "artifact_paths",
        "executable_identities",
        "frozen_launcher",
        "frozen_platform",
        "persistent_artifact_identities",
    )

    def __init__(self, values: Sequence[str], *, artifact_paths: Sequence[str]) -> None:
        if isinstance(values, (str, bytes)) or not values:
            raise TypeError("argv must be a non-empty sequence of strings")
        if any(not isinstance(value, str) for value in values):
            raise TypeError("argv must be a non-empty sequence of strings")
        if any("\x00" in value for value in values):
            raise ValueError("argv contains an invalid item")
        if isinstance(artifact_paths, (str, bytes)) or not artifact_paths:
            raise TypeError("artifact paths must be a non-empty sequence of strings")
        if any(not isinstance(path, str) for path in artifact_paths):
            raise TypeError("artifact paths must be a non-empty sequence of strings")
        if any(not path or "\x00" in path for path in artifact_paths):
            raise ValueError("artifact paths contain an invalid item")
        super().__init__(values)
        self.artifact_paths = tuple(artifact_paths)
        self.argument_offset = self._infer_argument_offset()
        self.executable_identities: tuple[ExecutableIdentity, ...] = ()
        self.persistent_artifact_identities: tuple[PersistentArtifactIdentity, ...] = ()
        self.frozen_launcher: tuple[str, ...] | None = None
        self.frozen_platform: str | None = None

    def _infer_argument_offset(self) -> int:
        """Return the end of the launcher prefix represented by artifact paths."""

        if not self or any(not isinstance(value, str) or "\x00" in value for value in self):
            raise ValueError("argv contains an invalid item")
        if (
            not isinstance(self.artifact_paths, tuple)
            or not self.artifact_paths
            or any(
                not isinstance(path, str) or not path or "\x00" in path
                for path in self.artifact_paths
            )
        ):
            raise ValueError("artifact paths contain an invalid item")
        if self[0] != self.artifact_paths[0]:
            raise ValueError("first executable artifact must be argv[0]")
        positions: list[int] = []
        for artifact in self.artifact_paths:
            matches = [index for index, value in enumerate(self) if value == artifact]
            if len(matches) != 1:
                raise ValueError(
                    f"each executable artifact must occur exactly once in argv: {artifact}"
                )
            positions.append(matches[0])
        if any(right <= left for left, right in pairwise(positions)):
            raise ValueError(
                "executable artifacts must appear in strictly increasing argv positions"
            )
        return positions[-1] + 1

    def _validate_argument_offset(self) -> None:
        """Reject mutable receipt drift before identity work or launch."""

        inferred = self._infer_argument_offset()
        if self.argument_offset != inferred:
            raise ValueError("process argv executable artifact boundary is invalid")

    def with_arguments(self, arguments: Sequence[str]) -> PreparedProcessArgv:
        """Return a receipt-preserving argv with a replacement argument suffix."""

        if isinstance(arguments, (str, bytes)):
            raise TypeError("arguments must be a sequence of strings")
        values = list(arguments)
        if any(not isinstance(item, str) for item in values):
            raise TypeError("arguments must be a sequence of strings")
        if any(not item or "\x00" in item for item in values):
            raise ValueError("arguments contain an invalid item")
        launcher = (
            list(self.frozen_launcher)
            if self.frozen_launcher is not None
            else list(self[: self.argument_offset])
        )
        bound = PreparedProcessArgv(
            [*launcher, *values],
            artifact_paths=self.artifact_paths,
        )
        bound.argument_offset = len(launcher)
        bound.executable_identities = self.executable_identities
        bound.persistent_artifact_identities = self.persistent_artifact_identities
        bound.frozen_launcher = self.frozen_launcher
        bound.frozen_platform = self.frozen_platform
        return bound

    def bind(self, *arguments: str | Sequence[str]) -> PreparedProcessArgv:
        """Convenience alias accepting either positional or one sequence argument."""

        values: Sequence[str]
        if len(arguments) == 1 and not isinstance(arguments[0], str):
            values = arguments[0]
        else:
            values = arguments  # type: ignore[assignment]
        return self.with_arguments(values)

    def freeze_persistent(
        self,
        *,
        platform_name: str | None = None,
        forbidden_roots: Sequence[str | Path] = (),
    ) -> PreparedProcessArgv:
        """Freeze durable lexical launcher identities without resolving argv spelling."""

        return freeze_persistent_process_argv(
            self,
            platform_name=platform_name,
            forbidden_roots=forbidden_roots,
        )

    def revalidate(self) -> None:
        """Revalidate this argv's frozen receipt immediately before launch."""

        revalidate_process_argv(self)


def _is_absolute_path(value: str, *, platform_name: str) -> bool:
    if platform_name == "nt":
        return PureWindowsPath(value).is_absolute()
    if platform_name == "posix":
        return PurePosixPath(value).is_absolute()
    return Path(value).is_absolute()


def _contains_path_separator(value: str) -> bool:
    return "/" in value or "\\" in value or bool(PureWindowsPath(value).drive)


def _same_lexical_path(left: str, right: str, *, platform_name: str) -> bool:
    path_module = ntpath if platform_name == "nt" else posixpath
    normalizer = path_module.normcase if platform_name == "nt" else lambda value: value
    return normalizer(path_module.normpath(left)) == normalizer(path_module.normpath(right))


def _is_lexically_within(path: str, root: str, *, platform_name: str) -> bool:
    path_module = ntpath if platform_name == "nt" else posixpath
    normalized_path = path_module.normpath(path)
    normalized_root = path_module.normpath(root)
    try:
        common = path_module.commonpath((normalized_path, normalized_root))
    except ValueError:
        return False
    return _same_lexical_path(common, normalized_root, platform_name=platform_name)


def sanitized_executable_search_path(
    search_path: str | None = None,
    *,
    platform_name: str | None = None,
    current_directory: str | Path | None = None,
    forbidden_roots: Sequence[str | Path] = (),
) -> str:
    """Return absolute PATH entries outside every target workspace root."""

    platform = platform_name or os.name
    raw_path = os.environ.get("PATH", "") if search_path is None else search_path
    if not isinstance(raw_path, str) or "\x00" in raw_path:
        raise ValueError("PATH must be text without NUL bytes")
    separator = ";" if platform == "nt" else os.pathsep
    cwd = str(Path.cwd() if current_directory is None else current_directory)
    excluded_roots = (cwd, *(str(root) for root in forbidden_roots))
    safe_entries: list[str] = []
    seen: set[str] = set()
    for entry in raw_path.split(separator):
        if (
            not entry
            or entry in {".", ".."}
            or any(ord(character) < 32 or ord(character) == 127 for character in entry)
            or not _is_absolute_path(entry, platform_name=platform)
            or any(
                _is_lexically_within(entry, root, platform_name=platform) for root in excluded_roots
            )
        ):
            continue
        path_module = ntpath if platform == "nt" else posixpath
        normalized = path_module.normpath(entry)
        key = path_module.normcase(normalized) if platform == "nt" else normalized
        if key not in seen:
            safe_entries.append(normalized)
            seen.add(key)
    return separator.join(safe_entries)


def repository_forbidden_roots(
    current_directory: str | Path | None = None,
    *,
    include_current: bool = True,
) -> tuple[Path, ...]:
    """Return an inert, canonical boundary for repository-adjacent execution.

    No Git command, hook, configuration, or repository-owned executable is
    consulted.  Every ancestor carrying a recognized repository marker is
    excluded as a whole so sibling ``bin`` directories cannot win executable
    discovery from a nested working directory.  The exact supplied directory
    is also excluded by default; repository-independent host lifecycle callers
    may omit that broad tree while retaining every marker-derived boundary.
    """

    current = Path.cwd() if current_directory is None else Path(current_directory)
    current = current.expanduser().resolve(strict=True)
    roots = [current] if include_current else []
    for candidate in (current, *current.parents):
        marker_found = False
        for marker_name in _REPOSITORY_MARKERS:
            try:
                (candidate / marker_name).lstat()
            except (FileNotFoundError, NotADirectoryError):
                continue
            except OSError:
                marker_found = True
                break
            else:
                marker_found = True
                break
        if marker_found:
            roots.append(candidate)
    return tuple(dict.fromkeys(roots))


def _call_resolver(
    resolver: BinaryResolver,
    executable: str,
    *,
    search_path: str,
) -> str | None:
    try:
        return resolver(executable, path=search_path)
    except TypeError:
        # One-argument resolvers are a supported test/embedding seam. Their
        # result is still required to be absolute before it can be accepted.
        return resolver(executable)


def _search_absolute_path(
    executable: str,
    *,
    search_path: str,
    platform_name: str,
) -> str | None:
    separator = ";" if platform_name == "nt" else os.pathsep
    if platform_name == "nt":
        suffix = PureWindowsPath(executable).suffix
        if suffix:
            names = (executable,)
        else:
            raw_extensions = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD")
            extensions = tuple(
                extension
                for extension in raw_extensions.split(";")
                if extension.casefold() in _WINDOWS_DISCOVERY_SUFFIXES
            )
            names = tuple(f"{executable}{extension}" for extension in extensions)
    else:
        names = (executable,)
    for entry in search_path.split(separator):
        if not entry:
            continue
        for name in names:
            candidate = Path(entry) / name
            try:
                status = candidate.stat()
            except OSError:
                continue
            if not stat.S_ISREG(status.st_mode):
                continue
            if platform_name != "nt" and not os.access(candidate, os.X_OK):
                continue
            return str(candidate.absolute())
    return None


def resolve_executable_path(
    executable: str,
    *,
    search_path: str | None = None,
    platform_name: str | None = None,
    resolver: BinaryResolver | None = None,
    current_directory: str | Path | None = None,
    forbidden_roots: Sequence[str | Path] = (),
) -> str:
    """Resolve a command without consulting relative or current-directory PATH entries."""

    if (
        not isinstance(executable, str)
        or not executable
        or any(ord(character) < 32 or ord(character) == 127 for character in executable)
    ):
        raise ValueError("executable must be non-empty text without control characters")
    if executable in {".", ".."}:
        raise ValueError("explicit executable paths must be absolute")
    platform = platform_name or os.name
    if _contains_path_separator(executable):
        if not _is_absolute_path(executable, platform_name=platform):
            raise ValueError("explicit executable paths must be absolute")
        resolved = executable
    else:
        safe_path = sanitized_executable_search_path(
            search_path,
            platform_name=platform,
            current_directory=current_directory,
            forbidden_roots=forbidden_roots,
        )
        if resolver is not None:
            resolved = _call_resolver(
                resolver,
                executable,
                search_path=safe_path,
            )
        else:
            resolved = _search_absolute_path(
                executable,
                search_path=safe_path,
                platform_name=platform,
            )
            if resolved is None:
                resolved = _call_resolver(
                    shutil.which,
                    executable,
                    search_path=safe_path,
                )
                if (
                    resolved
                    and platform == "nt"
                    and PureWindowsPath(resolved).suffix.casefold()
                    not in _WINDOWS_DISCOVERY_SUFFIXES
                ):
                    resolved = None
        if not resolved:
            raise FileNotFoundError(f"executable not found: {executable}")
    if not _is_absolute_path(resolved, platform_name=platform):
        raise OSError("executable resolver returned a non-absolute path")
    path_module = ntpath if platform == "nt" else posixpath
    normalized = path_module.normpath(resolved)
    _assert_artifact_outside_forbidden_roots(
        normalized,
        normalized,
        platform_name=platform,
        forbidden_roots=forbidden_roots,
    )
    return normalized


def _canonical_regular_file(
    path: str,
    *,
    platform_name: str,
    require_executable: bool = True,
) -> tuple[str, os.stat_result]:
    try:
        lexical = os.lstat(path)
    except (OSError, ValueError) as exc:
        raise FileNotFoundError(f"executable artifact is unavailable: {path}") from exc
    attributes = int(getattr(lexical, "st_file_attributes", 0))
    is_link = stat.S_ISLNK(lexical.st_mode)
    if attributes & _WINDOWS_REPARSE_POINT or (platform_name == "nt" and is_link):
        raise OSError(f"executable artifact must not be a link or reparse point: {path}")
    if not is_link and not stat.S_ISREG(lexical.st_mode):
        raise OSError(f"executable artifact must be a regular file: {path}")
    try:
        canonical = str(Path(path).resolve(strict=True))
        current = os.lstat(canonical)
    except (OSError, RuntimeError, ValueError) as exc:
        raise FileNotFoundError(f"executable artifact is unavailable: {path}") from exc
    current_attributes = int(getattr(current, "st_file_attributes", 0))
    if (
        not stat.S_ISREG(current.st_mode)
        or stat.S_ISLNK(current.st_mode)
        or current_attributes & _WINDOWS_REPARSE_POINT
    ):
        raise OSError(f"executable artifact must be a real regular file: {path}")
    if require_executable and platform_name != "nt" and not os.access(canonical, os.X_OK):
        raise PermissionError(f"executable artifact is not executable: {canonical}")
    return canonical, current


def _posix_file_has_access_acl(path: Path) -> bool:
    """Return whether an access ACL is present, failing closed on probe errors."""

    getxattr = getattr(os, "getxattr", None)
    if not callable(getxattr):
        return False
    try:
        return bool(getxattr(path, "system.posix_acl_access", follow_symlinks=False))
    except OSError as exc:
        return exc.errno not in {
            errno.ENODATA,
            getattr(errno, "ENOATTR", errno.ENODATA),
            errno.ENOTSUP,
            getattr(errno, "EOPNOTSUPP", errno.ENOTSUP),
        }


def _assert_executable_artifact_trusted(
    path: str,
    status: os.stat_result,
    *,
    platform_name: str,
) -> None:
    """Reject in-place mutation authority held by another OS account."""

    candidate = Path(path)
    if platform_name == "nt":
        if not windows_file_prevents_untrusted_mutation(candidate, is_windows=True):
            raise PermissionError(
                f"executable artifact ACL permits cross-account mutation: {candidate}"
            )
        return
    uid_getter = getattr(os, "geteuid", None)
    if not callable(uid_getter):
        raise PermissionError("executable artifact ownership cannot be verified")
    if int(status.st_uid) not in {0, int(uid_getter())}:
        raise PermissionError(f"executable artifact has an untrusted owner: {candidate}")
    if stat.S_IMODE(status.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
        raise PermissionError(f"executable artifact permits group or other writes: {candidate}")
    if _posix_file_has_access_acl(candidate):
        raise PermissionError(f"executable artifact has an unverified access ACL: {candidate}")


def _metadata_identity(status: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        int(status.st_dev),
        int(status.st_ino),
        int(status.st_mode),
        int(status.st_size),
        int(status.st_mtime_ns),
        int(getattr(status, "st_file_attributes", 0)),
    )


def _opened_metadata_identity(status: os.stat_result) -> tuple[int, int, int, int, int, int]:
    identity = _metadata_identity(status)
    if os.name != "nt":
        return identity
    # Windows handle metadata omits synthesized execute bits reported by path
    # stat. File type, ACL trust, and the remaining identity fields are stable.
    return (*identity[:2], stat.S_IFMT(int(status.st_mode)), *identity[3:])


def _stable_file_sha256(path: str, expected: os.stat_result) -> str:
    """Hash one bounded regular file while proving the opened identity stayed stable."""

    if int(expected.st_size) > _MAX_PERSISTENT_ARTIFACT_BYTES:
        raise OSError(f"persistent executable artifact exceeds the size limit: {path}")
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    digest = hashlib.sha256()
    total = 0
    try:
        opened = os.fstat(descriptor)
        if _opened_metadata_identity(opened) != _opened_metadata_identity(expected):
            raise OSError(f"persistent executable artifact changed while opening: {path}")
        while chunk := os.read(descriptor, 1024 * 1024):
            total += len(chunk)
            if total > _MAX_PERSISTENT_ARTIFACT_BYTES:
                raise OSError(f"persistent executable artifact exceeds the size limit: {path}")
            digest.update(chunk)
        after_handle = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_path = os.lstat(path)
    if _opened_metadata_identity(after_handle) != _opened_metadata_identity(
        opened
    ) or _opened_metadata_identity(after_path) != _opened_metadata_identity(opened):
        raise OSError(f"persistent executable artifact changed while hashing: {path}")
    return digest.hexdigest()


def snapshot_persistent_artifact(
    path: str | Path,
    *,
    platform_name: str | None = None,
    require_executable: bool = False,
) -> PersistentArtifactIdentity:
    """Snapshot one persistent launcher artifact without rewriting its argv spelling."""

    platform = platform_name or os.name
    lexical_path = absolute_executable_path(path)
    try:
        lexical = os.lstat(lexical_path)
    except (OSError, ValueError) as exc:
        raise FileNotFoundError(
            f"persistent executable artifact is unavailable: {lexical_path}"
        ) from exc
    lexical_attributes = int(getattr(lexical, "st_file_attributes", 0))
    lexical_is_link = stat.S_ISLNK(lexical.st_mode)
    if lexical_attributes & _WINDOWS_REPARSE_POINT or (platform == "nt" and lexical_is_link):
        raise OSError(
            f"persistent executable artifact must not be a Windows link or reparse point: "
            f"{lexical_path}"
        )
    if not lexical_is_link and not stat.S_ISREG(lexical.st_mode):
        raise OSError(f"persistent executable artifact must be a regular file: {lexical_path}")
    if lexical_is_link and platform != "nt":
        uid_getter = getattr(os, "geteuid", None)
        if not callable(uid_getter) or int(lexical.st_uid) not in {0, int(uid_getter())}:
            raise PermissionError(
                f"persistent executable link has an untrusted owner: {lexical_path}"
            )
        link_target: str | None = os.readlink(lexical_path)
    else:
        link_target = None
    assert_executable_namespace(lexical_path, is_windows=platform == "nt")
    canonical, resolved = _canonical_regular_file(
        lexical_path,
        platform_name=platform,
        require_executable=require_executable,
    )
    assert_executable_namespace(canonical, is_windows=platform == "nt")
    _assert_executable_artifact_trusted(canonical, resolved, platform_name=platform)
    content_hash = _stable_file_sha256(canonical, resolved)
    return PersistentArtifactIdentity(
        lexical_path=lexical_path,
        lexical_device=int(lexical.st_dev),
        lexical_inode=int(lexical.st_ino),
        lexical_mode=int(lexical.st_mode),
        lexical_size=int(lexical.st_size),
        lexical_modified_ns=int(lexical.st_mtime_ns),
        lexical_file_attributes=lexical_attributes,
        link_target=link_target,
        resolved_path=canonical,
        resolved_device=int(resolved.st_dev),
        resolved_inode=int(resolved.st_ino),
        resolved_mode=int(resolved.st_mode),
        resolved_size=int(resolved.st_size),
        resolved_modified_ns=int(resolved.st_mtime_ns),
        resolved_file_attributes=int(getattr(resolved, "st_file_attributes", 0)),
        sha256=content_hash,
    )


def snapshot_persistent_artifacts(
    paths: Sequence[str | Path],
    *,
    platform_name: str | None = None,
) -> tuple[PersistentArtifactIdentity, ...]:
    """Snapshot every artifact required by a persistent launcher."""

    return tuple(
        snapshot_persistent_artifact(
            path,
            platform_name=platform_name,
            require_executable=index == 0,
        )
        for index, path in enumerate(paths)
    )


def persistent_artifacts_from_manifest(
    value: object,
) -> tuple[PersistentArtifactIdentity, ...]:
    """Decode a bounded non-empty persistent launcher identity list."""

    if not isinstance(value, list) or not 1 <= len(value) <= 8:
        raise ValueError("persistent launcher artifact list is invalid")
    return tuple(PersistentArtifactIdentity.from_manifest(item) for item in value)


def revalidate_persistent_artifacts(
    expected: Sequence[PersistentArtifactIdentity],
    *,
    platform_name: str | None = None,
) -> None:
    """Reject namespace, metadata, target-spelling, or ACL drift before launch.

    The explicit operation that produced ``expected`` already recomputed the
    content hash. This final race check is intentionally metadata-only: trusted
    file ACLs exclude cross-account in-place writes, while same-user tampering
    is outside the launcher threat boundary.
    """

    if not expected:
        raise OSError("persistent launcher has no frozen artifact identity")
    platform = platform_name or os.name
    for index, frozen in enumerate(expected):
        lexical = os.lstat(frozen.lexical_path)
        observed_lexical = (
            int(lexical.st_dev),
            int(lexical.st_ino),
            int(lexical.st_mode),
            int(lexical.st_size),
            int(lexical.st_mtime_ns),
            int(getattr(lexical, "st_file_attributes", 0)),
        )
        expected_lexical = (
            frozen.lexical_device,
            frozen.lexical_inode,
            frozen.lexical_mode,
            frozen.lexical_size,
            frozen.lexical_modified_ns,
            frozen.lexical_file_attributes,
        )
        link_target = os.readlink(frozen.lexical_path) if stat.S_ISLNK(lexical.st_mode) else None
        if observed_lexical != expected_lexical or link_target != frozen.link_target:
            raise OSError(f"persistent executable artifact drifted: {frozen.lexical_path}")
        assert_executable_namespace(frozen.lexical_path, is_windows=platform == "nt")
        canonical, resolved = _canonical_regular_file(
            frozen.lexical_path,
            platform_name=platform,
            require_executable=index == 0,
        )
        _assert_executable_artifact_trusted(canonical, resolved, platform_name=platform)
        assert_executable_namespace(canonical, is_windows=platform == "nt")
        observed_resolved = _metadata_identity(resolved)
        expected_resolved = (
            frozen.resolved_device,
            frozen.resolved_inode,
            frozen.resolved_mode,
            frozen.resolved_size,
            frozen.resolved_modified_ns,
            frozen.resolved_file_attributes,
        )
        if canonical != frozen.resolved_path or observed_resolved != expected_resolved:
            raise OSError(f"persistent executable artifact drifted: {frozen.lexical_path}")


def _is_within(path: str, root: str | Path) -> bool:
    try:
        Path(path).resolve(strict=True).relative_to(Path(root).resolve(strict=True))
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _absolute_lexical_path(
    value: str | Path,
    *,
    platform_name: str,
) -> str:
    """Return an absolute normalized spelling without dereferencing links."""

    path_module = ntpath if platform_name == "nt" else posixpath
    spelling = os.fspath(value)
    if path_module.isabs(spelling):
        return path_module.normpath(spelling)
    if platform_name != os.name:
        raise ValueError("relative paths require the native platform")
    return path_module.normpath(path_module.abspath(spelling))


def _assert_artifact_outside_forbidden_roots(
    lexical_path: str | Path,
    resolved_path: str,
    *,
    platform_name: str,
    forbidden_roots: Sequence[str | Path],
) -> None:
    """Reject launch artifacts inside a forbidden root by spelling or target."""

    lexical = _absolute_lexical_path(lexical_path, platform_name=platform_name)
    for root in forbidden_roots:
        lexical_root = _absolute_lexical_path(root, platform_name=platform_name)
        if _is_lexically_within(lexical, lexical_root, platform_name=platform_name) or _is_within(
            resolved_path,
            root,
        ):
            raise OSError(
                f"executable artifact must not reside in the target repository: {lexical_path}"
            )


def _snapshot_executable(
    path: str,
    *,
    platform_name: str,
    forbidden_roots: Sequence[str | Path],
    require_native_suffix: bool,
) -> ExecutableIdentity:
    canonical, status = _canonical_regular_file(path, platform_name=platform_name)
    _assert_executable_artifact_trusted(canonical, status, platform_name=platform_name)
    _assert_artifact_outside_forbidden_roots(
        path,
        canonical,
        platform_name=platform_name,
        forbidden_roots=forbidden_roots,
    )
    if (
        platform_name == "nt"
        and require_native_suffix
        and Path(canonical).suffix.casefold() not in _WINDOWS_NATIVE_SUFFIXES
    ):
        raise OSError(f"Windows launch executable must have a trusted native suffix: {canonical}")
    inode = int(status.st_ino)
    if inode <= 0:
        raise OSError(f"executable artifact has no stable filesystem identity: {canonical}")
    return ExecutableIdentity(
        path=canonical,
        device=int(status.st_dev),
        inode=inode,
        mode=int(status.st_mode),
        size=int(status.st_size),
        modified_ns=int(status.st_mtime_ns),
        file_attributes=int(getattr(status, "st_file_attributes", 0)),
    )


def freeze_process_argv(
    argv: PreparedProcessArgv,
    *,
    platform_name: str | None = None,
    forbidden_roots: Sequence[str | Path] = (),
) -> PreparedProcessArgv:
    """Freeze the real filesystem identity of every launch-critical artifact."""

    argv._validate_argument_offset()
    platform = platform_name or os.name
    identities = tuple(
        _snapshot_executable(
            artifact,
            platform_name=platform,
            forbidden_roots=forbidden_roots,
            require_native_suffix=index == 0,
        )
        for index, artifact in enumerate(argv.artifact_paths)
    )
    for identity in identities:
        assert_executable_namespace(identity.path, is_windows=platform == "nt")
    replacements = dict(zip(argv.artifact_paths, (item.path for item in identities), strict=True))
    for index, value in enumerate(argv):
        if value in replacements:
            argv[index] = replacements[value]
    argv.artifact_paths = tuple(item.path for item in identities)
    argv._validate_argument_offset()
    argv.executable_identities = identities
    argv.persistent_artifact_identities = ()
    argv.frozen_launcher = tuple(argv[: argv.argument_offset])
    argv.frozen_platform = platform
    return argv


def freeze_persistent_process_argv(
    argv: PreparedProcessArgv,
    *,
    platform_name: str | None = None,
    forbidden_roots: Sequence[str | Path] = (),
) -> PreparedProcessArgv:
    """Freeze lexical launch artifacts for reuse without dereferencing argv[0]."""

    argv._validate_argument_offset()
    platform = platform_name or os.name
    identities = snapshot_persistent_artifacts(
        argv.artifact_paths,
        platform_name=platform,
    )
    for identity in identities:
        _assert_artifact_outside_forbidden_roots(
            identity.lexical_path,
            identity.resolved_path,
            platform_name=platform,
            forbidden_roots=forbidden_roots,
        )
    argv.executable_identities = ()
    argv.persistent_artifact_identities = identities
    argv.frozen_launcher = tuple(argv[: argv.argument_offset])
    argv.frozen_platform = platform
    return argv


def revalidate_process_argv(argv: PreparedProcessArgv) -> None:
    """Fail when any frozen artifact changed between approval and process creation."""

    try:
        argv._validate_argument_offset()
    except (TypeError, ValueError) as exc:
        raise OSError("process argv launcher changed after identity freeze") from exc
    if argv.executable_identities and argv.persistent_artifact_identities:
        raise OSError("process argv has conflicting frozen executable identities")
    if not argv.executable_identities and not argv.persistent_artifact_identities:
        raise OSError("process argv has no frozen executable identity")
    if argv.frozen_platform is None:
        raise OSError("process argv has no frozen executable platform")
    if argv.frozen_launcher is None:
        raise OSError("process argv has no frozen launcher prefix")
    if tuple(argv[: argv.argument_offset]) != argv.frozen_launcher:
        raise OSError("process argv launcher changed after identity freeze")
    if argv.persistent_artifact_identities:
        if (
            tuple(identity.lexical_path for identity in argv.persistent_artifact_identities)
            != argv.artifact_paths
        ):
            raise OSError("persistent executable identities do not cover argv artifacts")
        revalidate_persistent_artifacts(
            argv.persistent_artifact_identities,
            platform_name=argv.frozen_platform,
        )
        return
    if tuple(identity.path for identity in argv.executable_identities) != argv.artifact_paths:
        raise OSError("executable identities do not cover argv artifacts")
    for expected in argv.executable_identities:
        canonical, current = _canonical_regular_file(
            expected.path, platform_name=argv.frozen_platform
        )
        _assert_executable_artifact_trusted(
            canonical,
            current,
            platform_name=argv.frozen_platform,
        )
        observed = _metadata_identity(current)
        frozen = (
            expected.device,
            expected.inode,
            expected.mode,
            expected.size,
            expected.modified_ns,
            expected.file_attributes,
        )
        if observed != frozen:
            raise OSError(f"executable artifact changed before launch: {expected.path}")
        assert_executable_namespace(
            expected.path,
            is_windows=argv.frozen_platform == "nt",
        )


def absolute_executable_path(value: str | Path) -> str:
    """Return an absolute launcher path without dereferencing environment shims.

    Virtual environments commonly expose ``bin/python`` as a symlink. Resolving
    that symlink would persist the base interpreter in generated services and
    host plugins, where the installed Agency Runtime package may be unavailable.
    A drive-qualified or UNC Windows path is already absolute even when payloads
    are generated on POSIX, whose native path helpers would otherwise prepend
    the current working directory and corrupt the generated Windows command.
    """

    text = str(value)
    if not text or any(ord(character) < 32 or ord(character) == 127 for character in text):
        raise ValueError("executable path contains an invalid character")
    if PureWindowsPath(text).is_absolute():
        return text
    return os.path.abspath(os.path.expanduser(text))


def agency_bootstrap_path() -> str:
    """Return the exact package-owned isolated bootstrap script."""

    return str(Path(__file__).resolve().parents[1] / "_bootstrap.py")


def isolated_python_argv(
    python_executable: str | Path,
    module: str,
    *arguments: str,
    bootstrap_path: str | Path | None = None,
) -> list[str]:
    """Build an isolated argv bound to this installed Agency package root.

    ``bootstrap_path`` substitutes an already attested bootstrap -- the
    published private projection -- for the package-owned one.  Callers that
    spawn through :func:`freeze_process_argv` need it: the guard refuses any
    launch artifact another OS account could rewrite, and a package running
    from a source checkout is exactly that.
    """

    return [
        absolute_executable_path(python_executable),
        "-I",
        "-S",
        agency_bootstrap_path() if bootstrap_path is None else str(Path(bootstrap_path)),
        module,
        *arguments,
    ]


def _trusted_npm_companion(
    shim: Path,
    resolver: BinaryResolver,
    *,
    current_directory: str | Path | None = None,
    forbidden_roots: Sequence[str | Path] = (),
) -> list[str] | None:
    """Resolve allowlisted npm CLIs without sending stdin through PowerShell."""

    command = shim.stem.casefold()
    npm_root = shim.parent
    if command == "codex":
        native_candidates = [
            npm_root
            / "node_modules"
            / "@openai"
            / "codex"
            / "node_modules"
            / "@openai"
            / package
            / "vendor"
            / target
            / "bin"
            / "codex.exe"
            for package, target in (
                ("codex-win32-x64", "x86_64-pc-windows-msvc"),
                ("codex-win32-arm64", "aarch64-pc-windows-msvc"),
            )
        ]
        native_candidates.extend(
            npm_root
            / "node_modules"
            / "@openai"
            / package
            / "vendor"
            / target
            / "bin"
            / "codex.exe"
            for package, target in (
                ("codex-win32-x64", "x86_64-pc-windows-msvc"),
                ("codex-win32-arm64", "aarch64-pc-windows-msvc"),
            )
        )
        native = next((path for path in native_candidates if path.is_file()), None)
        if native is not None:
            return [str(native)]
        script = npm_root / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
    elif command == "claude":
        package_root = npm_root / "node_modules" / "@anthropic-ai" / "claude-code"
        native = package_root / "bin" / "claude.exe"
        if native.is_file():
            return [str(native)]
        script = package_root / "cli.js"
    else:
        return None

    if not script.is_file():
        return None
    sibling_node = npm_root / "node.exe"
    if sibling_node.is_file():
        node = str(sibling_node)
    else:
        try:
            node = resolve_executable_path(
                "node.exe",
                platform_name="nt",
                resolver=resolver,
                current_directory=current_directory,
                forbidden_roots=forbidden_roots,
            )
        except (FileNotFoundError, OSError, TypeError, ValueError):
            node = None
    return [node, str(script)] if node else None


def _trusted_powershell(
    *,
    platform_name: str,
    system_resolver: BinaryResolver | None,
) -> str:
    executable = (
        system_resolver("powershell.exe")
        if system_resolver is not None
        else trusted_windows_system_executable(
            "powershell.exe",
            platform_name=platform_name,
        )
    )
    if not executable:
        raise FileNotFoundError("trusted Windows PowerShell executable is unavailable")
    if not _is_absolute_path(executable, platform_name="nt"):
        raise OSError("trusted Windows PowerShell resolver returned a non-absolute path")
    return executable


def prepare_process_argv(
    argv: Sequence[str],
    *,
    platform_name: str | None = None,
    resolver: BinaryResolver | None = None,
    system_resolver: BinaryResolver | None = None,
    current_directory: str | Path | None = None,
    forbidden_roots: Sequence[str | Path] = (),
) -> PreparedProcessArgv:
    """Resolve argv[0] and never send user arguments through cmd.exe."""

    if isinstance(argv, (str, bytes)) or not argv:
        raise TypeError("argv must be a non-empty sequence of strings")
    if any(not isinstance(part, str) for part in argv):
        raise TypeError("argv must be a non-empty sequence of strings")
    process_argv = list(argv)
    if any(not part or "\x00" in part for part in process_argv):
        raise ValueError("argv contains an invalid item")
    resolved = resolve_executable_path(
        process_argv[0],
        platform_name=platform_name,
        resolver=resolver,
        current_directory=current_directory,
        forbidden_roots=forbidden_roots,
    )
    process_argv[0] = resolved
    if (platform_name or os.name) != "nt":
        return PreparedProcessArgv(process_argv, artifact_paths=(resolved,))

    windows_platform = platform_name or os.name

    shim = Path(resolved)
    suffix = shim.suffix.casefold()
    if suffix in {".cmd", ".bat"}:
        native = shim.with_suffix(".exe")
        if native.is_file():
            values = [str(native), *process_argv[1:]]
            return PreparedProcessArgv(values, artifact_paths=(str(native),))
        npm_companion = _trusted_npm_companion(
            shim,
            resolver or shutil.which,
            current_directory=current_directory,
            forbidden_roots=forbidden_roots,
        )
        if npm_companion is not None:
            values = [*npm_companion, *process_argv[1:]]
            return PreparedProcessArgv(values, artifact_paths=tuple(npm_companion))
        powershell_shim = shim.with_suffix(".ps1")
        if powershell_shim.is_file():
            powershell = _trusted_powershell(
                platform_name=windows_platform,
                system_resolver=system_resolver,
            )
            values = [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(powershell_shim),
                *process_argv[1:],
            ]
            return PreparedProcessArgv(
                values,
                artifact_paths=(powershell, str(powershell_shim)),
            )
        raise OSError(
            f"refusing unsafe cmd.exe shim invocation without .exe or .ps1 companion: {shim}"
        )
    if suffix == ".ps1":
        powershell = _trusted_powershell(
            platform_name=windows_platform,
            system_resolver=system_resolver,
        )
        values = [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            *process_argv,
        ]
        return PreparedProcessArgv(values, artifact_paths=(powershell, resolved))
    if suffix not in _WINDOWS_NATIVE_SUFFIXES:
        raise OSError(f"refusing Windows executable with an untrusted suffix: {shim}")
    return PreparedProcessArgv(process_argv, artifact_paths=(resolved,))


__all__ = [
    "BinaryResolver",
    "ExecutableIdentity",
    "PersistentArtifactIdentity",
    "PreparedProcessArgv",
    "absolute_executable_path",
    "agency_bootstrap_path",
    "freeze_persistent_process_argv",
    "freeze_process_argv",
    "isolated_python_argv",
    "persistent_artifacts_from_manifest",
    "prepare_process_argv",
    "repository_forbidden_roots",
    "resolve_executable_path",
    "revalidate_persistent_artifacts",
    "revalidate_process_argv",
    "sanitized_executable_search_path",
    "snapshot_persistent_artifact",
    "snapshot_persistent_artifacts",
]
