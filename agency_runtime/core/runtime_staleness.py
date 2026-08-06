"""Report a stale installed hook runtime instead of failing silently.

Host hooks execute one immutable, content-addressed runtime projection whose
absolute path is frozen into the installed bundle's argv at install time (see
``launcher_bootstrap``).  That pin is deliberate: it is what stops a mutable
tree from redirecting code that runs with operator authority on every tool
call.  The cost is that shipping new source changes nothing a hook executes
until the operator reinstalls -- and that drift used to be silent, so hooks
kept enforcing old code paths and rejected work with no hint that a reinstall
was required.

This module records which projection the last install published and lets any
process compare itself against it.  The pointer is *advisory only*: it is read
to report drift, never to choose which code to execute.  A tampered pointer can
therefore at worst produce a spurious or a missing warning; it cannot redirect
a hook.  That is the whole reason the check is safe to add here rather than
resolving the runtime path dynamically at hook time.

A hook cannot detect the second drift direction -- source edited but never
reinstalled.  ``_collect_runtime_files`` only accepts the active package, and
inside a hook the active package *is* the projection, so it would hash itself
and always agree.  That check belongs to the ``agency`` CLI, which runs from
the real checkout; see ``source_runtime_drift``.
"""

from __future__ import annotations

import json
import os
import re
import stat
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.configuration import restrict_private_file
from agency_runtime.core.launcher_bootstrap import (
    running_runtime_digest,
    runtime_digest_for_bootstrap,
)
from agency_runtime.core.private_paths import private_runtime_directory

_POINTER_NAME = "current.json"
_POINTER_SCHEMA = "agency-runtime.installed-launcher-runtime"
_POINTER_SCHEMA_VERSION = 1
_MAX_POINTER_BYTES = 4096
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")
_HOST_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")


@dataclass(frozen=True, slots=True)
class RuntimeStaleness:
    """One reported drift between the running and last-installed runtime."""

    running_digest: str
    installed_digest: str
    host: str

    @property
    def message(self) -> str:
        agent = f" --agent {self.host}" if self.host else ""
        return (
            "Agency Runtime is executing a stale hook runtime: this process runs "
            f"projection {self.running_digest[:12]} but the last install published "
            f"{self.installed_digest[:12]}. Your installed hooks are stale; run "
            f"`agency install{agent}` to refresh them."
        )


def _pointer_path() -> Path:
    return private_runtime_directory("launchers") / _POINTER_NAME


def _validated_digest(value: object) -> str:
    text = str(value or "").strip()
    return text if _DIGEST_PATTERN.fullmatch(text) else ""


def _validated_host(value: object) -> str:
    text = str(value or "").strip().casefold()
    return text if _HOST_PATTERN.fullmatch(text) else ""


def record_installed_runtime(bootstrap_path: str | Path, *, host: str = "") -> str:
    """Record which projection this install published; return its digest.

    Returns "" when the staged path is not a private projection, which keeps
    non-projection installs (tests, direct source runs) from writing a pointer
    that no hook could ever match.
    """

    digest = runtime_digest_for_bootstrap(bootstrap_path)
    if not digest:
        return ""
    payload = (
        json.dumps(
            {
                "schema": _POINTER_SCHEMA,
                "schema_version": _POINTER_SCHEMA_VERSION,
                "runtime_digest": digest,
                "host": _validated_host(host),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    target = _pointer_path()
    staging = target.with_name(f".{_POINTER_NAME}.{os.getpid()}")
    descriptor = os.open(
        staging,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC | int(getattr(os, "O_BINARY", 0)),
        stat.S_IRUSR | stat.S_IWUSR,
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        restrict_private_file(staging)
        os.replace(staging, target)
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        _remove_staging(staging)
        raise
    restrict_private_file(target)
    return digest


def _remove_staging(path: Path) -> None:
    """Remove one staging artifact without masking the original failure."""

    with suppress(OSError):
        os.unlink(path)


def installed_runtime_pointer() -> tuple[str, str]:
    """Return the (digest, host) the last install published, or ("", "")."""

    try:
        payload = read_bounded_regular_file(
            _pointer_path(),
            limit=_MAX_POINTER_BYTES,
            label="installed runtime pointer",
        )
    except (OSError, ValueError):
        return "", ""
    try:
        value = safe_load_bounded_json(
            payload,
            maximum_bytes=_MAX_POINTER_BYTES,
            maximum_depth=4,
            maximum_nodes=32,
        )
    except (ValueError, TypeError):
        return "", ""
    if (
        not isinstance(value, dict)
        or value.get("schema") != _POINTER_SCHEMA
        or value.get("schema_version") != _POINTER_SCHEMA_VERSION
    ):
        return "", ""
    return _validated_digest(value.get("runtime_digest")), _validated_host(value.get("host"))


def runtime_staleness(*, host: str = "") -> RuntimeStaleness | None:
    """Return drift between the running and last-installed runtime, else None.

    Silent None means "no drift is provable": either this process is not
    running a projection at all, or no install pointer has been recorded yet.
    Both are ordinary states and must not produce a warning.
    """

    running = running_runtime_digest()
    if not running:
        return None
    installed, pointer_host = installed_runtime_pointer()
    if not installed or installed == running:
        return None
    return RuntimeStaleness(
        running_digest=running,
        installed_digest=installed,
        host=_validated_host(host) or pointer_host,
    )


def source_runtime_drift(bootstrap_path: str | Path) -> str:
    """Return the digest the current source *would* stage, or "" on failure.

    Only meaningful from a process running the real checkout -- the ``agency``
    CLI. Compare it against :func:`installed_runtime_pointer` to detect source
    that has moved ahead of the last install.
    """

    from agency_runtime.core.launcher_bootstrap import plan_private_package_runtime

    try:
        return plan_private_package_runtime(bootstrap_path).manifest_sha256
    except (OSError, ValueError):
        return ""


__all__ = [
    "RuntimeStaleness",
    "installed_runtime_pointer",
    "record_installed_runtime",
    "runtime_staleness",
    "source_runtime_drift",
]
