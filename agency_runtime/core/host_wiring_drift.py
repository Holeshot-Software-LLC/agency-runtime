"""Compare what a host actually invokes against what the installer staged.

`agency status` answers "are the staged artifacts current". On 2026-08-10 that
answered *yes* while Claude was invoking a projection from before the Job B
deletion: the install had written new files, and the host's plugin cache had
never been refreshed, because every `claude plugin …` command dies on the
executable-namespace gate. Staged-but-not-wired reported healthy, and two turns
were blocked by code we had already deleted.

Staged is what we wrote. Wired is what runs. Only the second one can block a
turn, so only the second one is evidence. This module reads both and compares
their launcher identity — a pure read, no writes and no network, so it works on
any host that writes its wiring to disk.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from agency_runtime.core.bounded_io import read_bounded_regular_file_prefix
from agency_runtime.core.store.security import (
    assert_storage_parent_chain,
    storage_parent_is_trusted,
)

MAX_WIRING_FILE_BYTES: Final[int] = 512 * 1024

# Every adapter launcher path embeds the content-addressed projection it runs.
_LAUNCHER_PATTERN: Final[re.Pattern[str]] = re.compile(r"runtime-sha256-([0-9a-f]{64})")
_SUPPORTED_HOSTS: Final[tuple[str, ...]] = ("claude",)


@dataclass(frozen=True, slots=True)
class HostWiring:
    """What one host invokes, beside what the installer staged for it."""

    host: str
    staged_projection: str
    staged_path: str
    wired_projection: str
    wired_path: str

    @property
    def wired(self) -> bool:
        """Whether the host actually invokes the projection we staged."""

        return bool(self.staged_projection) and self.staged_projection == self.wired_projection

    @property
    def reason(self) -> str:
        """One short human explanation, empty when the host is correctly wired."""

        if not self.staged_projection:
            return "nothing is staged for this host"
        if not self.wired_projection:
            return "the host has no wired hook command; it has never installed the plugin"
        if not self.wired:
            return (
                "the host still invokes an older projection; its plugin cache was never "
                "refreshed, so the installed code is not the code that runs"
            )
        return ""


def _projection_in(path: Path) -> str:
    """Return the launcher projection one wiring file names, or empty."""

    try:
        assert_storage_parent_chain(path.parent, allow_missing=False)
    except (OSError, ValueError):
        return ""
    if not storage_parent_is_trusted(path.parent, is_windows=os.name == "nt"):
        return ""
    try:
        payload = read_bounded_regular_file_prefix(
            path,
            limit=MAX_WIRING_FILE_BYTES,
            label="host wiring file",
        ).decode("utf-8", errors="ignore")
    except (OSError, ValueError):
        return ""
    found = {match.group(1) for match in _LAUNCHER_PATTERN.finditer(payload)}
    # More than one projection in a single wiring file is itself broken; refuse
    # to pick a winner rather than report a healthy-looking half-truth.
    return found.pop() if len(found) == 1 else ""


def _claude_staged_wiring(agency_home: Path) -> Path:
    return (
        agency_home
        / "marketplaces"
        / "claude"
        / "plugins"
        / "agency-preflight"
        / "hooks"
        / "hooks.json"
    )


def _claude_wired_wiring(claude_home: Path) -> Path | None:
    """Find the cached hooks file Claude actually loads.

    The cache is keyed by plugin version, so the directory name moves whenever
    the version does — which, once the version is content-derived, is exactly
    when the wiring changes.
    """

    root = claude_home / "plugins" / "cache" / "agency-runtime" / "agency-preflight"
    if not root.is_dir():
        return None
    candidates = sorted(
        (path for path in root.glob("*/hooks/hooks.json") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def claude_host_wiring(
    *,
    agency_home: Path | None = None,
    claude_home: Path | None = None,
) -> HostWiring:
    """Read Claude's staged and wired launcher identities."""

    home = Path(agency_home) if agency_home else Path.home() / ".agency-runtime"
    host_home = (
        Path(claude_home)
        if claude_home
        else Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude").expanduser()
    )
    staged = _claude_staged_wiring(home)
    wired = _claude_wired_wiring(host_home)
    return HostWiring(
        host="claude",
        staged_projection=_projection_in(staged) if staged.is_file() else "",
        staged_path=str(staged),
        wired_projection=_projection_in(wired) if wired is not None else "",
        wired_path=str(wired) if wired is not None else "",
    )


def host_wiring(host: str, **kwargs: Path | None) -> HostWiring:
    """Read one supported host's wiring.

    Only Claude is implemented: its staged and cached paths are both measured
    facts on a real box. Codex, zcode, openclaw and hermes each write their
    wiring somewhere too, and each is a table entry away — but guessing a path
    would produce a confident "correctly wired" from a file that does not exist,
    which is worse than admitting the gap.
    """

    normalized = str(host or "").strip().casefold()
    if normalized == "claude":
        return claude_host_wiring(**kwargs)  # type: ignore[arg-type]
    raise ValueError(f"host wiring drift is not implemented for {normalized or 'an empty host'}")


__all__ = [
    "MAX_WIRING_FILE_BYTES",
    "HostWiring",
    "claude_host_wiring",
    "host_wiring",
]
