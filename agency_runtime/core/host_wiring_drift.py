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
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from agency_runtime.core.bounded_io import (
    read_bounded_regular_file,
    read_bounded_regular_file_prefix,
)
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.filesystem_trust import absolute_path
from agency_runtime.core.store.security import (
    assert_storage_parent_chain,
    storage_file_is_trusted,
    storage_parent_is_trusted,
)

MAX_WIRING_FILE_BYTES: Final[int] = 512 * 1024
_CLAUDE_PLUGIN_REGISTRY_VERSION: Final[int] = 2
_CLAUDE_PLUGIN_ID: Final[str] = "agency-preflight@agency-runtime"

# Every adapter launcher path embeds the content-addressed projection it runs.
_LAUNCHER_PATTERN: Final[re.Pattern[str]] = re.compile(r"runtime-sha256-([0-9a-f]{64})")
_OBSERVED: Final[str] = "observed"


@dataclass(frozen=True, slots=True)
class WiringFileObservation:
    """One wiring file's bounded, trust-checked launcher identity."""

    state: str
    path: str
    projection: str = ""


@dataclass(frozen=True, slots=True)
class HostWiring:
    """What one host invokes, beside what the installer staged for it."""

    host: str
    measurement_status: str
    staged_state: str
    staged_projection: str
    staged_path: str
    wired_state: str
    wired_projection: str
    wired_path: str

    @property
    def wired(self) -> bool:
        """Whether the host actually invokes the projection we staged."""

        return self.status == "wired"

    @property
    def status(self) -> str:
        """Return the measured outcome without calling missing evidence drift."""

        if self.measurement_status != "measured":
            return "not_measured"
        if self.staged_state != _OBSERVED or self.wired_state != _OBSERVED:
            return "unavailable"
        if self.staged_projection == self.wired_projection:
            return "wired"
        return "drift"

    @property
    def reason_code(self) -> str:
        """Return one stable machine reason for this measurement."""

        if self.measurement_status != "measured":
            return "host_not_measured"
        if self.staged_state != _OBSERVED:
            return f"staged_{self.staged_state}"
        if self.wired_state != _OBSERVED:
            return f"wired_{self.wired_state}"
        if self.staged_projection != self.wired_projection:
            return "projection_mismatch"
        return "wired"

    @property
    def reason(self) -> str:
        """One short human explanation, empty when the host is correctly wired."""

        explanations = {
            "host_not_measured": "this host's wiring location is not measured",
            "staged_missing": "nothing is staged for this host",
            "staged_untrusted": "the staged wiring file is not trusted",
            "staged_unreadable": "the staged wiring file could not be read",
            "staged_projection_missing": "the staged wiring file names no launcher projection",
            "staged_ambiguous": "the staged wiring file names multiple launcher projections",
            "wired_missing": "no wired hook command was observed at the measured location",
            "wired_untrusted": "the host wiring file is not trusted",
            "wired_unreadable": "the host wiring file could not be read",
            "wired_projection_missing": "the host wiring file names no launcher projection",
            "wired_ambiguous": "the active host wiring could not be resolved unambiguously",
        }
        if self.reason_code == "projection_mismatch":
            return (
                "the staged and wired projection identities differ; the staged code is "
                "not the code invoked at the measured location"
            )
        return explanations.get(self.reason_code, "")

    def as_dict(self) -> dict[str, str | bool]:
        """Return the shared CLI/dashboard projection for one host."""

        return {
            "host": self.host,
            "measurement_status": self.measurement_status,
            "status": self.status,
            "wired": self.wired,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "staged_state": self.staged_state,
            "staged_projection": self.staged_projection,
            "staged_path": self.staged_path,
            "wired_state": self.wired_state,
            "wired_projection": self.wired_projection,
            "wired_path": self.wired_path,
        }


def _projection_in(path: Path | None) -> WiringFileObservation:
    """Return the launcher projection and why it may be unavailable."""

    if path is None:
        return WiringFileObservation("missing", "")
    rendered = str(path)
    try:
        if not path.is_file():
            return WiringFileObservation("missing", rendered)
    except OSError:
        return WiringFileObservation("unreadable", rendered)

    try:
        assert_storage_parent_chain(path.parent, allow_missing=False)
    except PermissionError:
        return WiringFileObservation("untrusted", rendered)
    except (OSError, ValueError):
        return WiringFileObservation("unreadable", rendered)
    if not storage_parent_is_trusted(
        path.parent, is_windows=os.name == "nt"
    ) or not storage_file_is_trusted(path, is_windows=os.name == "nt"):
        return WiringFileObservation("untrusted", rendered)
    try:
        payload = read_bounded_regular_file_prefix(
            path,
            limit=MAX_WIRING_FILE_BYTES,
            label="host wiring file",
        ).decode("utf-8", errors="ignore")
    except (OSError, ValueError):
        return WiringFileObservation("unreadable", rendered)
    found = {match.group(1) for match in _LAUNCHER_PATTERN.finditer(payload)}
    # More than one projection in a single wiring file is itself broken; refuse
    # to pick a winner rather than report a healthy-looking half-truth.
    if not found:
        return WiringFileObservation("projection_missing", rendered)
    if len(found) > 1:
        return WiringFileObservation("ambiguous", rendered)
    return WiringFileObservation(_OBSERVED, rendered, found.pop())


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


def _claude_plugin_registry(claude_home: Path) -> Path:
    """Return Claude's authoritative installed-plugin binding registry."""

    return claude_home / "plugins" / "installed_plugins.json"


def _trusted_claude_plugin_registry(path: Path) -> tuple[WiringFileObservation, Any | None]:
    """Read one bounded, private Claude installed-plugin registry."""

    rendered = str(path)
    try:
        if not path.is_file():
            return WiringFileObservation("missing", rendered), None
    except OSError:
        return WiringFileObservation("unreadable", rendered), None
    try:
        assert_storage_parent_chain(path.parent, allow_missing=False)
    except PermissionError:
        return WiringFileObservation("untrusted", rendered), None
    except (OSError, ValueError):
        return WiringFileObservation("unreadable", rendered), None
    if not storage_parent_is_trusted(
        path.parent, is_windows=os.name == "nt"
    ) or not storage_file_is_trusted(path, is_windows=os.name == "nt"):
        return WiringFileObservation("untrusted", rendered), None
    try:
        raw = read_bounded_regular_file(
            path,
            limit=MAX_WIRING_FILE_BYTES,
            label="Claude installed-plugin registry",
        )
    except (OSError, ValueError):
        return WiringFileObservation("unreadable", rendered), None
    try:
        payload = safe_load_bounded_json(
            raw,
            maximum_bytes=MAX_WIRING_FILE_BYTES,
            maximum_depth=8,
            maximum_nodes=10_000,
        )
    except (TypeError, ValueError):
        return WiringFileObservation("ambiguous", rendered), None
    return WiringFileObservation(_OBSERVED, rendered), payload


def _claude_wired_wiring(claude_home: Path) -> WiringFileObservation:
    """Resolve the exact hooks file Claude's installed-plugin registry binds."""

    registry_path = _claude_plugin_registry(claude_home)
    registry_observation, payload = _trusted_claude_plugin_registry(registry_path)
    if registry_observation.state != _OBSERVED:
        return registry_observation
    if (
        not isinstance(payload, Mapping)
        or payload.get("version") != _CLAUDE_PLUGIN_REGISTRY_VERSION
    ):
        return WiringFileObservation("ambiguous", str(registry_path))
    plugins = payload.get("plugins")
    if not isinstance(plugins, Mapping):
        return WiringFileObservation("ambiguous", str(registry_path))
    bindings = plugins.get(_CLAUDE_PLUGIN_ID)
    if bindings is None or bindings == []:
        return WiringFileObservation("missing", str(registry_path))
    if not isinstance(bindings, list) or len(bindings) != 1:
        return WiringFileObservation("ambiguous", str(registry_path))
    binding = bindings[0]
    if not isinstance(binding, Mapping) or binding.get("scope") != "user":
        return WiringFileObservation("ambiguous", str(registry_path))
    raw_install_path = binding.get("installPath")
    if (
        not isinstance(raw_install_path, str)
        or not raw_install_path
        or raw_install_path != raw_install_path.strip()
    ):
        return WiringFileObservation("ambiguous", str(registry_path))
    supplied_install_path = Path(raw_install_path)
    if not supplied_install_path.is_absolute():
        return WiringFileObservation("ambiguous", str(registry_path))
    install_path = absolute_path(supplied_install_path)
    cache_root = absolute_path(
        claude_home / "plugins" / "cache" / "agency-runtime" / "agency-preflight"
    )
    try:
        relative = install_path.relative_to(cache_root)
    except ValueError:
        return WiringFileObservation("ambiguous", str(registry_path))
    if len(relative.parts) != 1:
        return WiringFileObservation("ambiguous", str(registry_path))
    return _projection_in(install_path / "hooks" / "hooks.json")


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
    wired_observation = _claude_wired_wiring(host_home)
    staged_observation = _projection_in(staged)
    return HostWiring(
        host="claude",
        measurement_status="measured",
        staged_state=staged_observation.state,
        staged_projection=staged_observation.projection,
        staged_path=staged_observation.path,
        wired_state=wired_observation.state,
        wired_projection=wired_observation.projection,
        wired_path=wired_observation.path,
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
    if not normalized:
        raise ValueError("host wiring drift requires a host")
    return HostWiring(
        host=normalized,
        measurement_status="not_measured",
        staged_state="not_measured",
        staged_projection="",
        staged_path="",
        wired_state="not_measured",
        wired_projection="",
        wired_path="",
    )


__all__ = [
    "MAX_WIRING_FILE_BYTES",
    "HostWiring",
    "WiringFileObservation",
    "claude_host_wiring",
    "host_wiring",
]
