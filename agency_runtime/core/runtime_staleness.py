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
and always agree.  That check belongs to the ``agency`` CLI; see
``cli_install_drift``.

Note what that check compares: the package the CLI *itself* runs from, not
whichever checkout happens to be the working directory.  A packaged tool
install commonly owns the ``agency`` on PATH, in which case editing source
moves neither the CLI nor the projection it would stage, and both agree with
the pointer while every hook keeps running last week's code.

Digests cannot detect that across environments.  ``_collect_runtime_files``
hashes the installed distribution closure along with the sources, so a
checkout and a packaged tool never produce the same digest however identical
their source, and comparing them would fire forever.  The pointer therefore
records the source package root as well, the roots decide whether a digest
comparison is meaningful at all, and a mismatch is reported by naming the
directory the install actually came from.
"""

from __future__ import annotations

import json
import os
import re
import stat
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.configuration import restrict_private_file
from agency_runtime.core.launcher_bootstrap import (
    running_runtime_digest,
    runtime_digest_for_bootstrap,
)
from agency_runtime.core.private_paths import private_runtime_directory
from agency_runtime.core.process_argv import agency_bootstrap_path

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


def _running_package_root() -> str:
    """Return the package directory this process runs from, or ""."""

    try:
        return str(Path(agency_bootstrap_path()).parent)
    except (OSError, ValueError):
        return ""


def _same_package_root(left: str, right: str) -> bool:
    """Compare two package roots the way the host filesystem would."""

    if not left or not right:
        return False
    return os.path.normcase(os.path.normpath(left)) == os.path.normcase(os.path.normpath(right))


def record_installed_runtime(bootstrap_path: str | Path, *, host: str = "") -> str:
    """Record which projection this install published; return its digest.

    Returns "" when the staged path is not a private projection, which keeps
    non-projection installs (tests, direct source runs) from writing a pointer
    that no hook could ever match.

    The source package root is recorded alongside the digest.  Staging is
    restricted to the active package, so the recorded root is the one this
    install ran from -- and a later comparison needs it, because the digest
    covers the installed distribution closure as well as the sources, and is
    therefore only meaningful against the same environment.
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
                "source_root": _running_package_root(),
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


def _pointer_document() -> dict[str, Any]:
    """Return the validated pointer document, or an empty mapping."""

    try:
        payload = read_bounded_regular_file(
            _pointer_path(),
            limit=_MAX_POINTER_BYTES,
            label="installed runtime pointer",
        )
    except (OSError, ValueError):
        return {}
    try:
        value = safe_load_bounded_json(
            payload,
            maximum_bytes=_MAX_POINTER_BYTES,
            maximum_depth=4,
            maximum_nodes=32,
        )
    except (ValueError, TypeError):
        return {}
    if (
        not isinstance(value, dict)
        or value.get("schema") != _POINTER_SCHEMA
        or value.get("schema_version") != _POINTER_SCHEMA_VERSION
    ):
        return {}
    return value


def installed_runtime_pointer() -> tuple[str, str]:
    """Return the (digest, host) the last install published, or ("", "")."""

    value = _pointer_document()
    if not value:
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


@dataclass(frozen=True, slots=True)
class InstallDrift:
    """A reason the installed hooks do not correspond to this CLI's package."""

    source_digest: str
    installed_digest: str
    package_root: str
    installed_source_root: str
    host: str

    @property
    def foreign_package(self) -> bool:
        """Whether the install came from a different package than this one."""

        return not _same_package_root(self.package_root, self.installed_source_root)

    @property
    def message(self) -> str:
        agent = f" --agent {self.host}" if self.host else ""
        if self.foreign_package:
            return (
                "installed hooks were staged from a different package than this one "
                f"({self.installed_source_root or 'unrecorded'}); edits here do not reach "
                f"them, and `agency install{agent}` from this package would replace them"
            )
        return (
            "installed hooks are behind this CLI: it would stage projection "
            f"{self.source_digest[:12]} but the last install published "
            f"{self.installed_digest[:12]}; hooks keep running the old code until "
            f"`agency install{agent}`"
        )


def cli_install_drift() -> InstallDrift | None:
    """Return why the installed hooks do not correspond to this CLI, else None.

    This is the drift direction a hook cannot see.  :func:`runtime_staleness`
    covers the other one -- a session whose hooks predate the last install --
    but it compares a projection against a pointer the very same install wrote,
    so it stays silent when source moves and nobody reinstalls.

    Two distinct failures are reported here, and conflating them produces a
    warning that always fires:

    *Foreign package.*  The `agency` on PATH is frequently not the checkout
    being edited.  Digests cannot settle this, because a projection digest
    covers the installed distribution closure as well as the sources, so two
    environments never agree however identical their source.  Comparing them
    across environments is a guaranteed false positive, and a warning that
    always fires is worse than none.  The recorded source root decides it
    instead, and the report names the directory rather than a digest.

    *Stale install.*  Same package, moved-on source: the digests are then
    directly comparable and their difference is real.

    Silent None means no drift is provable: this process is itself a frozen
    projection (a hook, which would only ever hash itself), no pointer has been
    recorded, no projection can be planned from this package, or the pointer
    predates source-root recording and cannot be attributed to an environment.
    """

    if running_runtime_digest():
        return None
    pointer = _pointer_document()
    installed = _validated_digest(pointer.get("runtime_digest"))
    if not installed:
        return None
    package_root = _running_package_root()
    if not package_root:
        return None
    installed_root = str(pointer.get("source_root") or "")
    # A pointer written before source roots were recorded cannot be attributed
    # to an environment, so no comparison it supports is trustworthy.
    if not installed_root:
        return None
    host = _validated_host(pointer.get("host"))
    if not _same_package_root(package_root, installed_root):
        return InstallDrift(
            source_digest="",
            installed_digest=installed,
            package_root=package_root,
            installed_source_root=installed_root,
            host=host,
        )
    digest = source_runtime_drift(agency_bootstrap_path())
    if not digest or digest == installed:
        return None
    return InstallDrift(
        source_digest=digest,
        installed_digest=installed,
        package_root=package_root,
        installed_source_root=installed_root,
        host=host,
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
    "InstallDrift",
    "RuntimeStaleness",
    "cli_install_drift",
    "installed_runtime_pointer",
    "record_installed_runtime",
    "runtime_staleness",
    "source_runtime_drift",
]
