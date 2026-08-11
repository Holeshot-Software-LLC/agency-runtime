"""Refuse to write a config the installed hooks cannot read.

`agency config set` rewrites the whole document through the *current* renderer,
so a CLI newer than the last install stamps fields the installed projection has
never heard of onto sections the operator never touched. Both config validators
are strict allowlists, so the projection then raises "contains unsupported
fields" -- and because hooks parse config on every event, one unrelated setting
bricks every turn on the box. Observed 2026-08-11: setting an unrelated selector
flag added `token_parameter` to both providers, and every turn afterwards failed
its evidence contract with an error naming neither the field nor the file.

The install-drift line already knows the CLI and the projection disagree.
Nothing consulted it before writing config, so this does, by asking the
installed projection itself rather than guessing what it supports -- a
reimplementation of its allowlist here would be one more copy to drift.

Deliberately fails *open*. If the projection cannot be found or cannot be run,
this proves nothing and must not block an operator from editing their config;
it blocks only on a definite rejection.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argv, no shell, local interpreter only
import sys
from contextlib import suppress
from pathlib import Path

from agency_runtime.core.launcher_bootstrap import running_runtime_digest
from agency_runtime.core.private_paths import private_runtime_directory
from agency_runtime.core.runtime_staleness import _recorded_hosts, installed_runtime_pointer

_PROBE_TIMEOUT_SECONDS = 30.0
_MAX_PROJECTIONS = 4
_MAX_DETAIL_CHARS = 400

# Runs inside the installed projection, never in this process: sys.argv[1] is
# that projection's site-packages and sys.argv[2] the candidate config.
_PROBE = (
    "import sys; sys.path.insert(0, sys.argv[1]);"
    "import yaml;"
    "from agency_runtime.core.configuration_schema import validate_config_document;"
    "validate_config_document("
    "yaml.safe_load(open(sys.argv[2], encoding='utf-8')) or {}"
    ")"
)


def _projection_site_packages(digest: str) -> Path | None:
    if not digest:
        return None
    with suppress(OSError, ValueError):
        candidate = (
            private_runtime_directory("launchers") / f"runtime-sha256-{digest}" / "site-packages"
        )
        if candidate.is_dir():
            return candidate
    return None


def _installed_projections() -> list[tuple[str, Path]]:
    """Return distinct installed projections that differ from this source."""

    running = running_runtime_digest()
    seen: dict[str, Path] = {}
    for host in _recorded_hosts():
        digest, _ = installed_runtime_pointer(host)
        if not digest or digest == running or digest in seen:
            continue
        site_packages = _projection_site_packages(digest)
        if site_packages is not None:
            seen[digest] = site_packages
    return list(seen.items())[:_MAX_PROJECTIONS]


def installed_projection_rejection(candidate: Path) -> str:
    """Return why the installed hooks would reject ``candidate``, or "".

    An empty string means either that the projection accepted the document or
    that no verdict could be obtained -- the two are deliberately not
    distinguished, because neither is grounds for refusing a config edit.
    """

    for digest, site_packages in _installed_projections():
        try:
            completed = subprocess.run(  # nosec B603 - fixed argv, shell=False
                [sys.executable, "-I", "-S", "-c", _PROBE, str(site_packages), str(candidate)],
                capture_output=True,
                text=True,
                timeout=_PROBE_TIMEOUT_SECONDS,
                shell=False,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue  # cannot ask; cannot conclude
        if completed.returncode == 0:
            continue
        detail = (completed.stderr or "").strip().splitlines()
        reason = detail[-1].strip() if detail else "rejected without a reason"
        if "ConfigValidationError" not in (completed.stderr or ""):
            # A probe that failed for its own reasons -- a missing dependency in
            # the projection, say -- is not evidence about the document.
            continue
        return (
            f"the installed hooks (projection {digest[:12]}) cannot read this configuration: "
            f"{reason[:_MAX_DETAIL_CHARS]}. This CLI is newer than the last install, so it "
            "writes fields those hooks reject, and every turn would fail until they are "
            "removed. Run `agency install` first, then repeat this change."
        )
    return ""


__all__ = ["installed_projection_rejection"]
