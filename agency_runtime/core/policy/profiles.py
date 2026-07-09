"""Install policy profiles for Agency Runtime.

Profiles intentionally keep network and auto-enablement decisions explicit so a
starter install can work entirely from the bundled local roster while power-user
installs can opt in to remote synchronization.

No user-specific profiles are baked in. User-specific settings belong in
``agency.yaml``, not in source code.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InstallProfile:
    """Runtime install profile governing roster sync behavior."""

    name: str
    network_enabled: bool
    auto_sync: bool
    auto_enable_new_agents: bool
    sync_schedule: str | None = None


LOCAL_ONLY = InstallProfile(
    name="local-only",
    network_enabled=False,
    auto_sync=False,
    auto_enable_new_agents=False,
    sync_schedule=None,
)

STANDARD = InstallProfile(
    name="standard",
    network_enabled=True,
    auto_sync=False,
    auto_enable_new_agents=False,
    sync_schedule=None,
)

POWER = InstallProfile(
    name="power",
    network_enabled=True,
    auto_sync=False,
    auto_enable_new_agents=False,
    sync_schedule="manual",
)

DEFAULT_PROFILE = STANDARD

PROFILES: dict[str, InstallProfile] = {
    LOCAL_ONLY.name: LOCAL_ONLY,
    STANDARD.name: STANDARD,
    POWER.name: POWER,
}


def get_profile(name: str | None = None) -> InstallProfile:
    """Return a named install profile, defaulting to ``STANDARD``."""

    if not name:
        return DEFAULT_PROFILE
    key = name.strip().lower()
    try:
        return PROFILES[key]
    except KeyError as exc:
        valid = ", ".join(sorted(PROFILES))
        raise ValueError(f"unknown profile {name!r}; expected one of: {valid}") from exc
