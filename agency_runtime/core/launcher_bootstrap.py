"""Owner-private runtime projection for persistent host launchers.

Persistent hooks must not import executable code from an installer-managed
site-packages tree that another local account can mutate. This module copies
Agency Runtime and its installed runtime dependency closure into one
hash-named, owner-private projection. Launchers then use python -I -S and
execute the projection's own bootstrap, so the original environment is never
processed by site before Agency takes control of sys.path.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path, PurePosixPath

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.configuration import restrict_private_directory, restrict_private_file
from agency_runtime.core.filesystem_trust import (
    metadata_is_link_or_reparse_point as _is_link_or_reparse,
)
from agency_runtime.core.private_paths import (
    PrivateDirectoryIdentity,
    allocate_private_directory,
    private_runtime_directory,
    remove_private_directory,
    validate_private_directory,
)
from agency_runtime.core.process_argv import (
    absolute_executable_path,
    agency_bootstrap_path,
    snapshot_persistent_artifact,
)

_RUNTIME_SCHEMA = "agency-runtime.private-launcher-runtime"
_RUNTIME_SCHEMA_VERSION = 1
_RUNTIME_MANIFEST = "runtime-manifest.json"
_RUNTIME_DIRECTORY_PREFIX = "runtime-sha256-"
_AGENCY_DISTRIBUTION = "agency-runtime"
_AGENCY_PACKAGE = "agency_runtime"
_MAX_RUNTIME_FILES = 20_000
_MAX_RUNTIME_FILE_BYTES = 64 * 1024 * 1024
_MAX_RUNTIME_BYTES = 512 * 1024 * 1024
_MAX_MANIFEST_BYTES = 8 * 1024 * 1024
_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9]+(?:[-_.][A-Za-z0-9]+)*)")
_PYTHON_CACHE_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True, slots=True)
class _RuntimeFile:
    relative_path: str
    payload: bytes
    sha256: str


@dataclass(frozen=True, slots=True)
class _ManifestEntry:
    relative_path: str
    sha256: str
    size: int


@dataclass(frozen=True, slots=True)
class PrivateRuntimePlan:
    """Pure content-addressed plan for one private launcher projection."""

    source_path: str
    runtime_root: str
    bootstrap_path: str
    manifest_sha256: str
    bootstrap_sha256: str
    bootstrap_size: int


def persistent_python_executable(
    requested: str | Path | None = None,
) -> str:
    """Select an exact trusted interpreter for a durable private launcher.

    A virtual-environment shim can live below a collaborative source checkout
    even when the interpreter that created it is installed in an OS-protected
    location. Persistent hooks and services execute a complete owner-private
    package projection, so they do not need the virtual environment's
    site-packages. Prefer the running interpreter's exact base executable and
    fall back to the requested/current executable only when its full namespace
    is independently trusted.

    Explicit non-current interpreter requests remain exact: they never fall
    back to a different executable behind the caller's back.
    """

    current = absolute_executable_path(sys.executable)
    requested_path = absolute_executable_path(requested) if requested is not None else current
    candidates: list[str] = []
    may_use_runtime_base = requested is None or os.path.normcase(
        requested_path
    ) == os.path.normcase(current)
    base = str(getattr(sys, "_base_executable", "") or "").strip()
    if may_use_runtime_base and base:
        candidates.append(absolute_executable_path(base))
    candidates.append(requested_path)

    failure: BaseException | None = None
    for candidate in dict.fromkeys(candidates):
        try:
            identity = snapshot_persistent_artifact(candidate, require_executable=True)
        except (OSError, ValueError) as exc:
            failure = exc
            continue
        return identity.lexical_path
    raise OSError("no trusted persistent Python executable is available") from failure


def _canonical_distribution_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", str(value).strip()).casefold()


def _safe_relative_path(value: str) -> str:
    normalized = str(value).replace("\\", "/")
    candidate = PurePosixPath(normalized)
    if (
        not normalized
        or candidate.is_absolute()
        or len(normalized) > 1024
        or any(
            part in {"", ".", ".."} or len(part) > 240 or "\x00" in part or ":" in part
            for part in candidate.parts
        )
    ):
        raise OSError("runtime distribution contains an unsafe relative path")
    return candidate.as_posix()


def _skip_runtime_path(relative_path: str) -> bool:
    parts = PurePosixPath(relative_path).parts
    return bool(
        "__pycache__" in parts
        or relative_path.casefold().endswith((".pyc", ".pyo", ".pth", ".egg-link"))
    )


def _add_source(
    sources: dict[str, Path],
    casefolded: dict[str, str],
    relative_path: str,
    source_path: Path,
) -> None:
    relative = _safe_relative_path(relative_path)
    if _skip_runtime_path(relative):
        return
    folded = relative.casefold()
    existing_spelling = casefolded.get(folded)
    if existing_spelling is not None and existing_spelling != relative:
        raise OSError("runtime distribution contains a case-colliding path")
    existing = sources.get(relative)
    if existing is not None:
        if os.path.normcase(str(existing.resolve(strict=True))) != os.path.normcase(
            str(source_path.resolve(strict=True))
        ):
            raise OSError("runtime distributions claim the same destination path")
        return
    if len(sources) >= _MAX_RUNTIME_FILES:
        raise OSError("runtime distribution exceeds the file-count limit")
    casefolded[folded] = relative
    sources[relative] = source_path


def _walk_package_sources(
    package_root: Path,
    sources: dict[str, Path],
    casefolded: dict[str, str],
) -> None:
    root_metadata = os.lstat(package_root)
    if _is_link_or_reparse(root_metadata) or not stat.S_ISDIR(root_metadata.st_mode):
        raise OSError("Agency Runtime package root must be a real directory")
    for directory, directory_names, file_names in os.walk(package_root, followlinks=False):
        parent = Path(directory)
        retained_directories: list[str] = []
        for name in sorted(directory_names):
            child = parent / name
            child_metadata = os.lstat(child)
            if _is_link_or_reparse(child_metadata) or not stat.S_ISDIR(child_metadata.st_mode):
                raise OSError("Agency Runtime package contains a linked or special directory")
            if name != "__pycache__":
                retained_directories.append(name)
        directory_names[:] = retained_directories
        for name in sorted(file_names):
            source = parent / name
            relative = source.relative_to(package_root).as_posix()
            _add_source(
                sources,
                casefolded,
                f"{_AGENCY_PACKAGE}/{relative}",
                source,
            )


def _requirement_names(distribution: metadata.Distribution) -> tuple[str, ...]:
    result: list[str] = []
    for requirement in distribution.requires or ():
        requirement_text, separator, marker = str(requirement).partition(";")
        if separator and re.search(r"\bextra\b", marker, flags=re.IGNORECASE):
            continue
        match = _REQUIREMENT_NAME.match(requirement_text)
        if match:
            result.append(match.group(1))
    return tuple(dict.fromkeys(result))


def _distribution_file_sources(
    distribution: metadata.Distribution,
    *,
    include_package_files: bool,
    sources: dict[str, Path],
    casefolded: dict[str, str],
) -> None:
    for package_path in distribution.files or ():
        raw_relative = str(package_path).replace("\\", "/")
        raw_candidate = PurePosixPath(raw_relative)
        if raw_candidate.is_absolute() or ".." in raw_candidate.parts:
            continue
        relative = _safe_relative_path(raw_relative)
        first = PurePosixPath(relative).parts[0].casefold()
        if not include_package_files and not (
            first.startswith("agency_runtime-")
            and (first.endswith(".dist-info") or first.endswith(".egg-info"))
        ):
            continue
        if _skip_runtime_path(relative):
            continue
        source = Path(distribution.locate_file(package_path))
        _add_source(sources, casefolded, relative, source)


def _distribution_closure() -> tuple[metadata.Distribution, ...]:
    pending = [_AGENCY_DISTRIBUTION]
    observed: set[str] = set()
    result: list[metadata.Distribution] = []
    while pending:
        requested = pending.pop(0)
        key = _canonical_distribution_name(requested)
        if key in observed:
            continue
        try:
            distribution = metadata.distribution(requested)
        except metadata.PackageNotFoundError:
            if key == _canonical_distribution_name(_AGENCY_DISTRIBUTION):
                raise OSError("Agency Runtime distribution metadata is unavailable") from None
            continue
        observed.add(key)
        result.append(distribution)
        pending.extend(_requirement_names(distribution))
    return tuple(result)


def _collect_runtime_files(source_path: str | Path) -> tuple[_RuntimeFile, ...]:
    source = Path(source_path)
    expected = Path(agency_bootstrap_path())
    if os.path.normcase(str(source.resolve(strict=True))) != os.path.normcase(
        str(expected.resolve(strict=True))
    ):
        raise PermissionError("private runtime staging is limited to the active Agency package")
    if source.name != "_bootstrap.py" or source.parent.name != _AGENCY_PACKAGE:
        raise OSError("Agency Runtime bootstrap has an invalid package layout")

    sources: dict[str, Path] = {}
    casefolded: dict[str, str] = {}
    _walk_package_sources(source.parent, sources, casefolded)
    for distribution in _distribution_closure():
        distribution_name = _canonical_distribution_name(distribution.metadata.get("Name", ""))
        _distribution_file_sources(
            distribution,
            include_package_files=distribution_name
            != _canonical_distribution_name(_AGENCY_DISTRIBUTION),
            sources=sources,
            casefolded=casefolded,
        )

    total_bytes = 0
    result: list[_RuntimeFile] = []
    for relative, source_file in sorted(sources.items()):
        payload = read_bounded_regular_file(
            source_file,
            limit=_MAX_RUNTIME_FILE_BYTES,
            label=f"runtime source {relative}",
        )
        total_bytes += len(payload)
        if total_bytes > _MAX_RUNTIME_BYTES:
            raise OSError("runtime distribution exceeds the total-byte limit")
        result.append(
            _RuntimeFile(
                relative,
                payload,
                hashlib.sha256(payload).hexdigest(),
            )
        )
    required_bootstrap = f"{_AGENCY_PACKAGE}/_bootstrap.py"
    if not any(item.relative_path == required_bootstrap for item in result):
        raise OSError("runtime projection is missing its Agency bootstrap")
    return tuple(result)


def _runtime_manifest(files: tuple[_RuntimeFile, ...]) -> bytes:
    value = {
        "schema": _RUNTIME_SCHEMA,
        "schema_version": _RUNTIME_SCHEMA_VERSION,
        "python_cache_tag": current_python_cache_tag(),
        "files": [
            {
                "path": item.relative_path,
                "sha256": item.sha256,
                "size": len(item.payload),
            }
            for item in files
        ],
    }
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def current_python_cache_tag() -> str:
    """Return the validated cache tag for the running interpreter."""

    value = str(getattr(sys.implementation, "cache_tag", "") or "")
    if _PYTHON_CACHE_TAG.fullmatch(value) is None:
        raise OSError("current Python interpreter has an invalid cache tag")
    return value


def _manifest_entries(
    payload: bytes,
    *,
    expected_digest: str,
    expected_python_cache_tag: str | None,
) -> tuple[_ManifestEntry, ...]:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
        raise PermissionError("private runtime directory has an invalid digest name")
    if hashlib.sha256(payload).hexdigest() != expected_digest:
        raise PermissionError("private runtime manifest does not match its hash name")
    value = safe_load_bounded_json(
        payload,
        maximum_bytes=_MAX_MANIFEST_BYTES,
        maximum_depth=8,
        maximum_nodes=100_000,
    )
    python_cache_tag = value.get("python_cache_tag") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or value.get("schema") != _RUNTIME_SCHEMA
        or value.get("schema_version") != _RUNTIME_SCHEMA_VERSION
        or not isinstance(python_cache_tag, str)
        or _PYTHON_CACHE_TAG.fullmatch(python_cache_tag) is None
        or (expected_python_cache_tag is not None and python_cache_tag != expected_python_cache_tag)
        or not isinstance(value.get("files"), list)
    ):
        raise PermissionError("private runtime manifest contract is invalid")
    canonical = (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    if canonical != payload:
        raise PermissionError("private runtime manifest is not canonical")
    raw_entries = tuple(value["files"])
    if not raw_entries or len(raw_entries) > _MAX_RUNTIME_FILES:
        raise PermissionError("private runtime manifest file count is invalid")

    entries: list[_ManifestEntry] = []
    observed: set[str] = set()
    observed_casefolded: set[str] = set()
    total_bytes = 0
    for entry in raw_entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size"}:
            raise PermissionError("private runtime manifest entry is invalid")
        path_value = entry.get("path")
        digest = entry.get("sha256")
        size = entry.get("size")
        if (
            not isinstance(path_value, str)
            or not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or size > _MAX_RUNTIME_FILE_BYTES
        ):
            raise PermissionError("private runtime manifest entry is invalid")
        try:
            relative = _safe_relative_path(path_value)
        except OSError:
            raise PermissionError("private runtime manifest entry is invalid") from None
        folded = relative.casefold()
        if relative in observed or folded in observed_casefolded:
            raise PermissionError("private runtime manifest entry is duplicated")
        observed.add(relative)
        observed_casefolded.add(folded)
        total_bytes += size
        if total_bytes > _MAX_RUNTIME_BYTES:
            raise PermissionError("private runtime manifest exceeds the byte limit")
        entries.append(_ManifestEntry(relative, digest, size))

    if not any(entry.relative_path == f"{_AGENCY_PACKAGE}/_bootstrap.py" for entry in entries):
        raise PermissionError("private runtime manifest does not identify its bootstrap")
    return tuple(entries)


def _runtime_digest(runtime_root: Path) -> str:
    name = runtime_root.name
    if not name.startswith(_RUNTIME_DIRECTORY_PREFIX):
        raise PermissionError("private runtime directory name is invalid")
    digest = name.removeprefix(_RUNTIME_DIRECTORY_PREFIX)
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise PermissionError("private runtime directory has an invalid digest name")
    return digest


def _attested_runtime_manifest(
    runtime_root: Path,
    *,
    expected_digest: str,
    expected_python_cache_tag: str | None,
) -> tuple[_ManifestEntry, ...]:
    """Read one immutable manifest through its owner-private namespace."""

    manifest_path = runtime_root / _RUNTIME_MANIFEST
    identity = snapshot_persistent_artifact(manifest_path)
    if identity.sha256 != expected_digest:
        raise PermissionError("private runtime manifest artifact does not match its hash name")
    manifest_payload = read_bounded_regular_file(
        manifest_path,
        limit=_MAX_MANIFEST_BYTES,
        label="private runtime manifest",
    )
    if (
        len(manifest_payload) != identity.lexical_size
        or hashlib.sha256(manifest_payload).hexdigest() != identity.sha256
    ):
        raise PermissionError("private runtime manifest changed during attestation")
    return _manifest_entries(
        manifest_payload,
        expected_digest=expected_digest,
        expected_python_cache_tag=expected_python_cache_tag,
    )


def _enumerated_projection_files(site_packages: Path) -> frozenset[str]:
    observed: set[str] = set()
    for directory, directory_names, file_names in os.walk(site_packages, followlinks=False):
        parent = Path(directory)
        for name in sorted(directory_names):
            child_metadata = os.lstat(parent / name)
            if _is_link_or_reparse(child_metadata) or not stat.S_ISDIR(child_metadata.st_mode):
                raise PermissionError("private runtime contains a linked or special directory")
        for name in sorted(file_names):
            path = parent / name
            relative = path.relative_to(site_packages).as_posix()
            if relative in observed:
                raise PermissionError("private runtime contains a duplicate path")
            observed.add(relative)
    return frozenset(observed)


def _verify_private_runtime_full(
    runtime_root: Path,
    *,
    expected_digest: str,
) -> str:
    """Exhaustively validate a newly staged projection before publication."""

    validate_private_directory(runtime_root)
    site_packages = validate_private_directory(runtime_root / "site-packages")
    manifest_path = runtime_root / _RUNTIME_MANIFEST
    restrict_private_file(manifest_path)
    manifest_identity = snapshot_persistent_artifact(manifest_path)
    if manifest_identity.sha256 != expected_digest:
        raise PermissionError("private runtime manifest artifact does not match its hash name")
    manifest_payload = read_bounded_regular_file(
        manifest_path,
        limit=_MAX_MANIFEST_BYTES,
        label="private runtime manifest",
    )
    entries = _manifest_entries(
        manifest_payload,
        expected_digest=expected_digest,
        expected_python_cache_tag=current_python_cache_tag(),
    )

    expected_paths: set[str] = set()
    bootstrap_path: Path | None = None
    for entry in entries:
        expected_paths.add(entry.relative_path)
        path = site_packages / Path(*PurePosixPath(entry.relative_path).parts)
        _verify_staged_runtime_file(path, entry)
        if entry.relative_path == f"{_AGENCY_PACKAGE}/_bootstrap.py":
            bootstrap_path = path

    if _enumerated_projection_files(site_packages) != frozenset(expected_paths):
        raise PermissionError("private runtime contains files outside its manifest")
    if bootstrap_path is None:
        raise PermissionError("private runtime manifest does not identify its bootstrap")
    return str(bootstrap_path)


def _verify_private_runtime_fast(
    runtime_root: Path,
    *,
    expected_python_cache_tag: str | None,
) -> str:
    """Attest a published projection without requiring mutation authority.

    The manifest and bootstrap snapshots each validate their complete
    owner-private namespace. The manifest digest binds the dependency closure;
    the bootstrap is the only projection artifact executed directly by the
    persistent launcher. Exhaustive file verification happens before the
    projection is atomically published, not on every restricted host launch.
    """

    expected_digest = _runtime_digest(runtime_root)
    entries = _attested_runtime_manifest(
        runtime_root,
        expected_digest=expected_digest,
        expected_python_cache_tag=expected_python_cache_tag,
    )
    bootstrap_entry = next(
        entry for entry in entries if entry.relative_path == f"{_AGENCY_PACKAGE}/_bootstrap.py"
    )
    bootstrap_path = (
        runtime_root / "site-packages" / Path(*PurePosixPath(bootstrap_entry.relative_path).parts)
    )
    identity = snapshot_persistent_artifact(bootstrap_path)
    if identity.sha256 != bootstrap_entry.sha256 or identity.lexical_size != bootstrap_entry.size:
        raise PermissionError("private runtime bootstrap does not match its manifest")
    return str(identity.lexical_path)


def _projection_root(source_path: str | Path) -> Path | None:
    source = Path(source_path)
    try:
        if (
            source.name != "_bootstrap.py"
            or source.parent.name != _AGENCY_PACKAGE
            or source.parent.parent.name != "site-packages"
        ):
            return None
        runtime_root = source.parent.parent.parent
        if not runtime_root.name.startswith(_RUNTIME_DIRECTORY_PREFIX):
            return None
        return runtime_root
    except (OSError, ValueError):
        return None


def _write_runtime_file(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | int(getattr(os, "O_BINARY", 0)),
        stat.S_IRUSR | stat.S_IWUSR,
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _verify_staged_runtime_file(path: Path, entry: _ManifestEntry) -> None:
    """Verify one newly created file inside the guarded private staging root.

    The staging directory and every parent directory already have owner-only
    permissions and remain identity-pinned for the transaction. Files are
    created exclusively beneath that namespace, so repeating an expensive
    Windows DACL rewrite and query for every file adds no security boundary.
    Link-resistant bounded reads still prove file kind, identity, size, and
    content before the directory can be published.
    """

    payload = read_bounded_regular_file(
        path,
        limit=_MAX_RUNTIME_FILE_BYTES,
        label=f"private runtime file {entry.relative_path}",
    )
    if len(payload) != entry.size or hashlib.sha256(payload).hexdigest() != entry.sha256:
        raise PermissionError("private runtime file does not match its manifest")


def _close_identity_guards(identity: PrivateDirectoryIdentity) -> None:
    for guard in (identity.guard, identity.parent_guard):
        if guard is not None:
            guard.close()


def stage_private_package_runtime(source_path: str | Path) -> str:
    """Publish and attest one immutable private runtime dependency closure."""

    files = _collect_runtime_files(source_path)
    manifest = _runtime_manifest(files)
    digest = hashlib.sha256(manifest).hexdigest()
    launchers = private_runtime_directory("launchers")
    target = launchers / f"{_RUNTIME_DIRECTORY_PREFIX}{digest}"
    if target.exists():
        return _verify_private_runtime_fast(
            target,
            expected_python_cache_tag=current_python_cache_tag(),
        )

    staging = allocate_private_directory(launchers, prefix=".runtime-stage")
    cleanup_identity = staging
    cleanup_required = True
    try:
        site_packages = staging.path / "site-packages"
        site_packages.mkdir()
        restrict_private_directory(site_packages)
        secured_directories = {site_packages}
        for item in files:
            target_file = site_packages / Path(*PurePosixPath(item.relative_path).parts)
            missing_parents: list[Path] = []
            current = target_file.parent
            while current not in secured_directories and current != staging.path:
                missing_parents.append(current)
                current = current.parent
            for parent in reversed(missing_parents):
                parent.mkdir(exist_ok=True)
                restrict_private_directory(parent)
                secured_directories.add(parent)
            _write_runtime_file(target_file, item.payload)
        _write_runtime_file(staging.path / _RUNTIME_MANIFEST, manifest)

        _verify_private_runtime_full(
            staging.path,
            expected_digest=digest,
        )

        try:
            os.rename(staging.path, target)
        except OSError:
            if not target.exists():
                raise
            return _verify_private_runtime_fast(
                target,
                expected_python_cache_tag=current_python_cache_tag(),
            )

        cleanup_identity = PrivateDirectoryIdentity(
            path=target,
            device=staging.device,
            inode=staging.inode,
            guard=staging.guard,
            parent_guard=staging.parent_guard,
            authority=staging.authority,
        )
        try:
            result = _verify_private_runtime_fast(
                target,
                expected_python_cache_tag=current_python_cache_tag(),
            )
        except BaseException:
            remove_private_directory(cleanup_identity)
            cleanup_required = False
            raise
        _close_identity_guards(cleanup_identity)
        cleanup_required = False
        return result
    finally:
        if cleanup_required:
            remove_private_directory(cleanup_identity)


def prepare_private_package_runtime(source_path: str | Path) -> str:
    """Return a bootstrap attested for execution by the current interpreter."""

    if runtime_root := _projection_root(source_path):
        return _verify_private_runtime_fast(
            runtime_root,
            expected_python_cache_tag=current_python_cache_tag(),
        )
    return stage_private_package_runtime(source_path)


def plan_private_package_runtime(source_path: str | Path) -> PrivateRuntimePlan:
    """Compute the exact immutable runtime destination without publishing it.

    Prepared host transactions use this read-only projection so operator
    verification can bind the candidate runtime before any launcher directory
    is created.  Publication must later return the exact planned bootstrap and
    content identity.
    """

    files = _collect_runtime_files(source_path)
    manifest = _runtime_manifest(files)
    manifest_sha256 = hashlib.sha256(manifest).hexdigest()
    bootstrap = next(
        (item for item in files if item.relative_path == f"{_AGENCY_PACKAGE}/_bootstrap.py"),
        None,
    )
    if bootstrap is None:  # pragma: no cover - package collector invariant
        raise PermissionError("private runtime projection has no Agency bootstrap")
    runtime_root = private_runtime_directory("launchers") / (
        f"{_RUNTIME_DIRECTORY_PREFIX}{manifest_sha256}"
    )
    bootstrap_path = (
        runtime_root / "site-packages" / Path(*PurePosixPath(bootstrap.relative_path).parts)
    )
    return PrivateRuntimePlan(
        source_path=str(Path(source_path).resolve()),
        runtime_root=str(runtime_root),
        bootstrap_path=str(bootstrap_path),
        manifest_sha256=manifest_sha256,
        bootstrap_sha256=bootstrap.sha256,
        bootstrap_size=len(bootstrap.payload),
    )


def runtime_digest_for_bootstrap(source_path: str | Path) -> str:
    """Return the projection digest naming one staged bootstrap, or "".

    An empty result means the path is not inside a private launcher
    projection — Agency is running from an ordinary checkout or site-packages
    install, so there is no pinned runtime to compare against.
    """

    runtime_root = _projection_root(source_path)
    if runtime_root is None:
        return ""
    try:
        return _runtime_digest(runtime_root)
    except PermissionError:
        return ""


def running_runtime_digest() -> str:
    """Return the projection digest this process is executing from, or "".

    Hooks launched by an installed bundle run one frozen projection; this
    reports which. Direct CLI and test invocations return "".
    """

    try:
        source = agency_bootstrap_path()
    except (OSError, ValueError):
        return ""
    return runtime_digest_for_bootstrap(source)


def verify_private_package_runtime(source_path: str | Path) -> str:
    """Attest an existing projection for inspection without mutating it.

    The manifest cache tag must remain a bounded canonical token, but it may
    belong to another interpreter. Call ``prepare_private_package_runtime``
    before any execution; that boundary additionally requires the current
    interpreter's exact cache tag.
    """

    runtime_root = _projection_root(source_path)
    if runtime_root is None:
        raise PermissionError("launcher is not an Agency Runtime private projection")
    return _verify_private_runtime_fast(
        runtime_root,
        expected_python_cache_tag=None,
    )


__all__ = [
    "PrivateRuntimePlan",
    "current_python_cache_tag",
    "plan_private_package_runtime",
    "prepare_private_package_runtime",
    "running_runtime_digest",
    "runtime_digest_for_bootstrap",
    "stage_private_package_runtime",
    "verify_private_package_runtime",
]
