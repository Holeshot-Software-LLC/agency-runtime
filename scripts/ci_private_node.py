"""Create and attest one owner-private Node executable mirror for hosted CI."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from agency_runtime.core.exception_notes import add_exception_note
from agency_runtime.core.private_paths import ensure_private_directory
from agency_runtime.core.process_argv import snapshot_persistent_artifact
from agency_runtime.core.store.security import (
    CreatedStoragePath,
    capture_created_storage_path,
    cleanup_created_storage_paths,
    metadata_is_link_or_reparse_point,
    restrict_windows_acl,
)

NodeResolver = Callable[[str], str | None]

_COPY_BUFFER_BYTES = 1024 * 1024
_MAX_NODE_BYTES = 256 * 1024 * 1024
_MAX_NODE_MANIFEST_BYTES = 16 * 1024
_NODE_MANIFEST_VERSION = 1


@dataclass(frozen=True, slots=True)
class _NodeSourceSnapshot:
    path: str
    device: int
    inode: int
    mode: int
    size: int
    modified_ns: int
    file_attributes: int
    sha256: str

    def manifest(self) -> dict[str, int | str]:
        return {
            "path": self.path,
            "device": self.device,
            "inode": self.inode,
            "mode": self.mode,
            "size": self.size,
            "modified_ns": self.modified_ns,
            "file_attributes": self.file_attributes,
            "sha256": self.sha256,
        }


def _private_directory(path: Path) -> Path:
    try:
        return ensure_private_directory(path)
    except (OSError, PermissionError) as exc:
        raise RuntimeError(f"CI runtime path must be private: {path}") from exc


def _metadata_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        int(metadata.st_dev),
        int(getattr(metadata, "st_ino", 0) or 0),
        int(metadata.st_mode),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
        int(getattr(metadata, "st_file_attributes", 0) or 0),
    )


def _cross_handle_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    """Return fields whose Windows path and open-handle views are equivalent."""

    return (
        int(metadata.st_dev),
        int(getattr(metadata, "st_ino", 0) or 0),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
        int(getattr(metadata, "st_file_attributes", 0) or 0),
    )


def _require_regular_node_source(path: Path) -> os.stat_result:
    metadata = os.lstat(path)
    if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISREG(metadata.st_mode):
        raise RuntimeError("CI Node source must resolve to a real regular file")
    if int(getattr(metadata, "st_ino", 0) or 0) <= 0:
        raise RuntimeError("CI Node source has no stable filesystem identity")
    if not 0 < int(metadata.st_size) <= _MAX_NODE_BYTES:
        raise RuntimeError("CI Node source is empty or exceeds the copy limit")
    return metadata


def _resolve_node_source(resolver: NodeResolver) -> Path | None:
    discovered = resolver("node")
    if not discovered:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in discovered):
        raise RuntimeError("CI Node source path contains an invalid character")
    try:
        source = Path(discovered).expanduser().resolve(strict=True)
        _require_regular_node_source(source)
    except (OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError("CI Node source could not be resolved safely") from exc
    if os.name == "nt" and source.suffix.casefold() != ".exe":
        raise RuntimeError("CI Node source must resolve to a native Windows executable")
    if os.name != "nt" and not os.access(source, os.X_OK):
        raise RuntimeError("CI Node source is not executable")
    return source


def _write_all(descriptor: int, payload: bytes) -> None:
    pending = memoryview(payload)
    while pending:
        written = os.write(descriptor, pending)
        if written <= 0:
            raise OSError("CI Node copy stopped before the complete payload was written")
        pending = pending[written:]


def _snapshot_node_source(
    source: Path,
    *,
    destination_descriptor: int | None = None,
) -> _NodeSourceSnapshot:
    before = _require_regular_node_source(source)
    flags = (
        os.O_RDONLY
        | int(getattr(os, "O_BINARY", 0))
        | int(getattr(os, "O_CLOEXEC", 0))
        | int(getattr(os, "O_NOFOLLOW", 0))
    )
    descriptor = os.open(source, flags)
    try:
        opened = os.fstat(descriptor)
        if (
            metadata_is_link_or_reparse_point(opened)
            or not stat.S_ISREG(opened.st_mode)
            or _cross_handle_identity(opened) != _cross_handle_identity(before)
        ):
            raise RuntimeError("CI Node source changed while it was opened")
        digest = hashlib.sha256()
        copied = 0
        while True:
            chunk = os.read(descriptor, _COPY_BUFFER_BYTES)
            if not chunk:
                break
            copied += len(chunk)
            if copied > _MAX_NODE_BYTES:
                raise RuntimeError("CI Node source exceeds the copy limit")
            digest.update(chunk)
            if destination_descriptor is not None:
                _write_all(destination_descriptor, chunk)
        after = os.fstat(descriptor)
        current = _require_regular_node_source(source)
        if (
            copied != int(opened.st_size)
            or _metadata_identity(after) != _metadata_identity(opened)
            or _metadata_identity(current) != _metadata_identity(before)
        ):
            raise RuntimeError("CI Node source changed while it was copied")
    finally:
        os.close(descriptor)
    return _NodeSourceSnapshot(
        path=source.as_posix(),
        device=int(before.st_dev),
        inode=int(before.st_ino),
        mode=int(before.st_mode),
        size=int(before.st_size),
        modified_ns=int(before.st_mtime_ns),
        file_attributes=int(getattr(before, "st_file_attributes", 0) or 0),
        sha256=digest.hexdigest(),
    )


def _path_lexically_exists(path: Path) -> bool:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return False
    return True


def _open_exclusive_private_file(
    path: Path,
    *,
    executable: bool,
) -> tuple[int, CreatedStoragePath]:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | int(getattr(os, "O_BINARY", 0))
        | int(getattr(os, "O_CLOEXEC", 0))
    )
    try:
        descriptor = os.open(path, flags, 0o700 if executable else 0o600)
    except FileExistsError as exc:
        raise RuntimeError("private CI Node mirror collided with an existing path") from exc
    identity: CreatedStoragePath | None = None
    try:
        identity = capture_created_storage_path(path, directory=False)
        opened = os.fstat(descriptor)
        if (
            metadata_is_link_or_reparse_point(opened)
            or not stat.S_ISREG(opened.st_mode)
            or (int(opened.st_dev), int(opened.st_ino)) != (identity.device, identity.inode)
        ):
            raise RuntimeError("private CI Node mirror changed during exclusive creation")
        if os.name != "nt":
            expected_mode = 0o700 if executable else 0o600
            os.fchmod(descriptor, expected_mode)
            if stat.S_IMODE(os.fstat(descriptor).st_mode) != expected_mode:
                raise RuntimeError("private CI Node mirror permissions could not be enforced")
    except BaseException as error:
        os.close(descriptor)
        if identity is not None:
            try:
                cleanup_created_storage_paths(
                    [identity],
                    is_windows=os.name == "nt",
                )
            except Exception as cleanup_error:
                add_exception_note(
                    error,
                    f"private CI Node exclusive-create rollback failed: {cleanup_error}",
                )
        raise
    assert identity is not None
    return descriptor, identity


def _restrict_private_windows_file(path: Path) -> None:
    if os.name == "nt" and not restrict_windows_acl(path, directory=False, is_windows=True):
        raise RuntimeError("private CI Node mirror Windows ACL could not be enforced")


def _target_manifest(path: Path) -> dict[str, int | str]:
    try:
        identity = snapshot_persistent_artifact(path, require_executable=True)
    except (OSError, PermissionError, ValueError) as exc:
        raise RuntimeError("private CI Node copy was replaced or modified") from exc
    return {
        "path": Path(identity.resolved_path).as_posix(),
        "device": identity.resolved_device,
        "inode": identity.resolved_inode,
        "mode": identity.resolved_mode,
        "size": identity.resolved_size,
        "modified_ns": identity.resolved_modified_ns,
        "file_attributes": identity.resolved_file_attributes,
        "sha256": identity.sha256,
    }


def _read_node_manifest(path: Path) -> dict[str, object]:
    try:
        identity = snapshot_persistent_artifact(path)
        if identity.resolved_size > _MAX_NODE_MANIFEST_BYTES:
            raise RuntimeError("private CI Node manifest exceeds its size limit")
        payload = path.read_bytes()
        if len(payload) > _MAX_NODE_MANIFEST_BYTES:
            raise RuntimeError("private CI Node manifest exceeds its size limit")
        if hashlib.sha256(payload).hexdigest() != identity.sha256:
            raise RuntimeError("private CI Node manifest changed while it was read")
        decoded = json.loads(payload)
    except (OSError, PermissionError, UnicodeError, ValueError) as exc:
        raise RuntimeError("private CI Node manifest is invalid or unsafe") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError("private CI Node manifest is invalid or unsafe")
    return decoded


def _validate_private_node(
    target: Path,
    manifest_path: Path,
    source: _NodeSourceSnapshot,
) -> Path:
    manifest = _read_node_manifest(manifest_path)
    if manifest.get("version") != _NODE_MANIFEST_VERSION:
        raise RuntimeError("private CI Node manifest version is unsupported")
    if manifest.get("source") != source.manifest():
        raise RuntimeError("CI Node source changed since the private mirror was created")
    target_manifest = manifest.get("target")
    if not isinstance(target_manifest, dict) or target_manifest != _target_manifest(target):
        raise RuntimeError("private CI Node copy was replaced or modified")
    return target.resolve(strict=True)


def _create_private_node(
    target: Path,
    manifest_path: Path,
    source_path: Path,
) -> Path:
    created: list[CreatedStoragePath] = []
    try:
        target_descriptor, target_identity = _open_exclusive_private_file(
            target,
            executable=True,
        )
        created.append(target_identity)
        try:
            source = _snapshot_node_source(
                source_path,
                destination_descriptor=target_descriptor,
            )
            os.fsync(target_descriptor)
        finally:
            os.close(target_descriptor)
        _restrict_private_windows_file(target)
        target_record = _target_manifest(target)
        if target_record["sha256"] != source.sha256 or target_record["size"] != source.size:
            raise RuntimeError("private CI Node copy does not match its stable source")
        payload = (
            json.dumps(
                {
                    "version": _NODE_MANIFEST_VERSION,
                    "source": source.manifest(),
                    "target": target_record,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
        if len(payload) > _MAX_NODE_MANIFEST_BYTES:
            raise RuntimeError("private CI Node manifest exceeds its size limit")
        manifest_descriptor, manifest_identity = _open_exclusive_private_file(
            manifest_path,
            executable=False,
        )
        created.append(manifest_identity)
        try:
            _write_all(manifest_descriptor, payload)
            os.fsync(manifest_descriptor)
        finally:
            os.close(manifest_descriptor)
        _restrict_private_windows_file(manifest_path)
        return _validate_private_node(target, manifest_path, source)
    except BaseException as error:
        try:
            cleanup_created_storage_paths(created, is_windows=os.name == "nt")
        except Exception as cleanup_error:
            add_exception_note(
                error,
                f"private CI Node mirror rollback failed: {cleanup_error}",
            )
        raise


def prepare_private_node(
    root: Path,
    *,
    resolver: NodeResolver,
) -> Path | None:
    """Create or validate the stable private Node copy for one CI runtime."""

    source_path = _resolve_node_source(resolver)
    if source_path is None:
        return None
    binary_directory = _private_directory(root / "bin")
    target = binary_directory / ("node.exe" if os.name == "nt" else "node")
    manifest_path = binary_directory / "node-copy.json"
    target_exists = _path_lexically_exists(target)
    manifest_exists = _path_lexically_exists(manifest_path)
    if target_exists != manifest_exists:
        raise RuntimeError("private CI Node mirror is an incomplete path collision")
    if target_exists:
        source = _snapshot_node_source(source_path)
        return _validate_private_node(target, manifest_path, source)
    return _create_private_node(target, manifest_path, source_path)


__all__ = ["NodeResolver", "prepare_private_node"]
