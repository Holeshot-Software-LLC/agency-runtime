"""Fail-closed identity for the managed host bundle serving a native child.

Native-child delivery evidence must name the exact Agency installation and
immutable runtime that produced it.  This module deliberately derives that
identity only from the installer's existing bounded ownership and launcher
receipts.  It never accepts a caller-supplied target or hashes a path that was
not first admitted by the managed install manifest.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.installer_contracts import HOSTS, PLUGIN_VERSION
from agency_runtime.core.installer_filesystem import validate_owned_install_tree
from agency_runtime.core.installer_inventory import _managed_bundle_identity
from agency_runtime.core.installer_native import plugin_target
from agency_runtime.core.launcher_bootstrap import (
    running_runtime_digest,
    runtime_digest_for_bootstrap,
)
from agency_runtime.core.process_argv import (
    persistent_artifacts_from_manifest,
    revalidate_persistent_artifacts,
    snapshot_persistent_artifacts,
)

_SHA256 = re.compile(r"[0-9a-f]{64}")
CANARY_NATIVE_INSTALL_HOME_ENV = "AGENCY_CANARY_NATIVE_INSTALL_HOME"


@dataclass(frozen=True, slots=True)
class NativeChildInstallIdentity:
    """Immutable identity bound to one exact managed host installation."""

    host: str
    plugin_version: str
    install_id: str
    bundle_digest: str
    running_runtime_digest: str
    candidate_digest: str


def _valid_digest(value: object) -> str:
    text = str(value or "")
    return text if _SHA256.fullmatch(text) else ""


def _managed_state(
    target: Path,
    host: str,
) -> tuple[dict[str, Any], str, str, str] | None:
    """Read one exact, stable owned-tree state or fail closed."""

    valid, _error, manifest = validate_owned_install_tree(
        target,
        host=host,
        target=target,
    )
    if not valid or manifest is None:
        return None
    plugin_version, install_id, bundle_digest = _managed_bundle_identity(target, host)
    if (
        plugin_version != PLUGIN_VERSION
        or manifest.get("plugin_version") != plugin_version
        or manifest.get("install_id") != install_id
        or not isinstance(install_id, str)
        or not install_id
        or not _valid_digest(bundle_digest)
    ):
        return None
    return dict(manifest), plugin_version, install_id, str(bundle_digest)


def current_managed_host_install_identity(
    host: str,
    *,
    home_dir: str | Path | None = None,
) -> NativeChildInstallIdentity | None:
    """Return the current managed host/runtime identity, or ``None``.

    ``home_dir`` is an explicit installer namespace boundary used by tests and
    operator-scoped inspection.  Production callers omit it, so the target is
    always resolved through the host installer's authoritative path rules.
    The installed launcher receipt must name the same private runtime
    projection that this process is executing.
    """

    if not isinstance(host, str) or host not in HOSTS:
        return None
    try:
        target = plugin_target(host, home_dir=home_dir)
        before = _managed_state(target, host)
        if before is None:
            return None
        manifest, plugin_version, install_id, bundle_digest = before

        launcher_artifacts = persistent_artifacts_from_manifest(manifest.get("launcher_artifacts"))
        if len(launcher_artifacts) != 2:
            return None
        observed_artifacts = snapshot_persistent_artifacts(
            tuple(item.lexical_path for item in launcher_artifacts)
        )
        if observed_artifacts != launcher_artifacts:
            return None

        bootstrap = launcher_artifacts[1]
        lexical_candidate = _valid_digest(runtime_digest_for_bootstrap(bootstrap.lexical_path))
        resolved_candidate = _valid_digest(runtime_digest_for_bootstrap(bootstrap.resolved_path))
        running = _valid_digest(running_runtime_digest())
        if (
            not lexical_candidate
            or lexical_candidate != resolved_candidate
            or running != lexical_candidate
        ):
            return None

        # Re-read the small managed tree after the launcher hash.  A bundle or
        # manifest that changed while identity was being assembled is not a
        # usable evidence binding.
        after = _managed_state(target, host)
        if after != before:
            return None
        revalidate_persistent_artifacts(launcher_artifacts)
    except (OSError, TypeError, ValueError, RuntimeError, UnicodeError):
        return None

    return NativeChildInstallIdentity(
        host=host,
        plugin_version=plugin_version,
        install_id=install_id,
        bundle_digest=bundle_digest,
        running_runtime_digest=running,
        candidate_digest=lexical_candidate,
    )


def current_runtime_managed_host_install_identity(
    host: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> NativeChildInstallIdentity | None:
    """Resolve the install serving this hook, including an isolated canary.

    Normal host hooks continue to use the installer's authoritative owner-home
    rules.  The safe Claude canary deliberately redirects ``HOME`` so the host
    cannot read ambient configuration; its parent therefore carries the
    original owner-home boundary in a canary-only environment capability.  The
    capability is accepted only with the explicit canary marker, must be an
    absolute path, and is still subjected to the complete managed-tree,
    launcher, runtime, and stable re-read validation above.
    """

    source = os.environ if environ is None else environ
    home_dir: Path | None = None
    if source.get("AGENCY_CANARY_MODE") == "1":
        raw_home = source.get(CANARY_NATIVE_INSTALL_HOME_ENV)
        if not isinstance(raw_home, str) or not raw_home.strip():
            return None
        try:
            home_dir = Path(raw_home).expanduser()
        except (OSError, RuntimeError, TypeError, ValueError):
            return None
        if not home_dir.is_absolute():
            return None
    return current_managed_host_install_identity(host, home_dir=home_dir)


__all__ = [
    "CANARY_NATIVE_INSTALL_HOME_ENV",
    "NativeChildInstallIdentity",
    "current_managed_host_install_identity",
    "current_runtime_managed_host_install_identity",
]
