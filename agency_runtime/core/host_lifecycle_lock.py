"""One owner-private lock for host integration install and uninstall mutations."""

from __future__ import annotations

import os
import stat
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

from agency_runtime.core.configuration import restrict_private_file
from agency_runtime.core.installer_native import runtime_home
from agency_runtime.core.private_paths import ensure_private_directory
from agency_runtime.core.store.security import metadata_is_link_or_reparse_point

_LOCK_TIMEOUT_SECONDS = 30.0


class HostLifecycleLockError(RuntimeError):
    """A host integration transaction could not acquire its shared lock."""


def _open_lock(path: Path):
    flags = os.O_RDWR | os.O_CREAT | int(getattr(os, "O_BINARY", 0))
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        path_stat = os.lstat(path)
        handle_stat = os.fstat(descriptor)
        if (
            not stat.S_ISREG(path_stat.st_mode)
            or metadata_is_link_or_reparse_point(path_stat)
            or (int(path_stat.st_dev), int(getattr(path_stat, "st_ino", 0) or 0))
            != (int(handle_stat.st_dev), int(getattr(handle_stat, "st_ino", 0) or 0))
        ):
            raise OSError("host integration lock must be a regular file")
        return os.fdopen(descriptor, "r+b")
    except Exception:
        os.close(descriptor)
        raise


@contextmanager
def host_integrations_lock(*, home_dir: str | Path | None) -> Iterator[None]:
    """Serialize every prepared host-integration lifecycle transaction."""

    parent = ensure_private_directory(
        runtime_home(home_dir=home_dir) / "locks",
        product_owned=True,
    )
    lock_path = parent / "host-integrations.lock"
    handle = _open_lock(lock_path)
    locked = False
    try:
        restrict_private_file(lock_path)
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        deadline = time.monotonic() + _LOCK_TIMEOUT_SECONDS
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise HostLifecycleLockError(
                        "another host integration transaction is active"
                    ) from exc
                time.sleep(0.025)
        yield
    finally:
        if locked:
            with suppress(OSError, ValueError):
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        with suppress(OSError, ValueError):
            handle.close()


__all__ = ["HostLifecycleLockError", "host_integrations_lock"]
