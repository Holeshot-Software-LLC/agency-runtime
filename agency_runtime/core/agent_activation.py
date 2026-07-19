"""Validated, reversible per-agent activation policy."""

from __future__ import annotations

import re
from collections.abc import Container, Iterable

from agency_runtime.core.resident_managers import RESIDENT_MANAGER_SLUG_SET

PROTECTED_AGENT_SLUGS = RESIDENT_MANAGER_SLUG_SET
MAX_DISABLED_AGENTS = 4096
MAX_AGENT_SLUG_CHARS = 128
_AGENT_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")


def normalize_agent_slug(value: object) -> str:
    """Return one canonical bounded roster slug or reject unsafe input."""

    if not isinstance(value, str):
        raise ValueError("agent slug must be a string")
    slug = value.strip().lower()
    if not slug or len(slug) > MAX_AGENT_SLUG_CHARS or _AGENT_SLUG.fullmatch(slug) is None:
        raise ValueError(
            "agent slug must be 2-128 lowercase letters/digits plus dot, underscore, or dash"
        )
    return slug


def normalize_disabled_agents(value: object) -> tuple[str, ...]:
    """Validate and canonicalize the persisted disabled-agent set."""

    if not isinstance(value, (list, tuple)):
        raise ValueError("agents.disabled must be a list")
    if len(value) > MAX_DISABLED_AGENTS:
        raise ValueError(f"agents.disabled supports at most {MAX_DISABLED_AGENTS} entries")
    normalized = tuple(normalize_agent_slug(item) for item in value)
    if len(normalized) != len(set(normalized)):
        raise ValueError("agents.disabled must not contain duplicates")
    protected = sorted(PROTECTED_AGENT_SLUGS.intersection(normalized))
    if protected:
        raise ValueError(f"protected coordinator cannot be disabled: {protected[0]}")
    return tuple(sorted(normalized))


def updated_disabled_agents(
    current: Iterable[str],
    slug: object,
    *,
    enabled: bool,
) -> tuple[str, ...]:
    """Return the canonical set after one reversible activation change."""

    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")
    normalized_slug = normalize_agent_slug(slug)
    disabled = set(normalize_disabled_agents(list(current)))
    if enabled:
        disabled.discard(normalized_slug)
    else:
        if normalized_slug in PROTECTED_AGENT_SLUGS:
            raise ValueError(f"protected coordinator cannot be disabled: {normalized_slug}")
        disabled.add(normalized_slug)
    return normalize_disabled_agents(sorted(disabled))


def agent_is_enabled(slug: object, disabled: Container[str]) -> bool:
    """Return whether an agent is enabled; coordinators are always enabled."""

    normalized_slug = normalize_agent_slug(slug)
    if normalized_slug in PROTECTED_AGENT_SLUGS:
        return True
    return normalized_slug not in disabled
