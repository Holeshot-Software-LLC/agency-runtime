"""Single-operation routing snapshots bound to one Store configuration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from inspect import Parameter, Signature, signature
from typing import Any

from agency_runtime.core.agent_activation import agent_is_enabled
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.config_binding import config_for_store


@dataclass(frozen=True, slots=True)
class RoutingSnapshot:
    """One immutable config identity and its matching policy-filtered catalog."""

    config: AgencyConfig
    catalog: list[dict[str, Any]]
    roster_generation: int = 0


def catalog_for_routing(
    store: Any,
    disabled_agents: frozenset[str],
    *,
    signature_reader: Callable[[Callable[..., Any]], Signature] = signature,
) -> list[dict[str, Any]]:
    """Read one catalog using an already-frozen activation-policy snapshot."""

    getter = store.get_active_roster_as_catalog
    try:
        parameters = signature_reader(getter).parameters.values()
    except (TypeError, ValueError):
        parameters = ()
    supports_snapshot = any(
        parameter.name == "disabled_agents" or parameter.kind == Parameter.VAR_KEYWORD
        for parameter in parameters
    )
    if supports_snapshot:
        return getter(disabled_agents=disabled_agents)
    return [
        row for row in getter() if agent_is_enabled(str(row.get("slug") or ""), disabled_agents)
    ]


def capture_routing_snapshot(
    store: Any,
    config: AgencyConfig | None = None,
) -> RoutingSnapshot:
    """Freeze Store-bound config before reading the catalog for one operation."""

    frozen_config = config_for_store(store, config)
    disabled_agents = frozenset(frozen_config.agents.disabled)
    snapshot_getter = getattr(store, "get_routing_roster_snapshot", None)
    if callable(snapshot_getter):
        snapshot = snapshot_getter(disabled_agents=disabled_agents)
        catalog = snapshot.get("catalog")
        generation = snapshot.get("generation")
        if (
            not isinstance(catalog, list)
            or isinstance(generation, bool)
            or not isinstance(generation, int)
            or generation < 0
        ):
            raise RuntimeError("routing roster snapshot is malformed")
        return RoutingSnapshot(
            config=frozen_config,
            catalog=catalog,
            roster_generation=generation,
        )
    return RoutingSnapshot(
        config=frozen_config,
        catalog=catalog_for_routing(
            store,
            disabled_agents,
        ),
    )


def capture_operational_routing_snapshot(
    store: Any,
    config: AgencyConfig | None = None,
) -> RoutingSnapshot:
    """Reconcile package-owned workers before an operation that may route."""

    snapshot = capture_routing_snapshot(store, config)
    from agency_runtime.core.installer import (
        ensure_no_match_fallback_roster,
        reconcile_packaged_contractors,
        seed_starter_roster,
    )

    can_activate = any(
        callable(getattr(store, name, None))
        for name in (
            "activate_agent",
            "activate_agent_if_missing",
            "activate_agents_if_missing",
            "reconcile_bundled_agents",
        )
    )
    if not snapshot.catalog and can_activate:
        seed_starter_roster(store)
    else:
        reconcile_packaged_contractors(store)
        if can_activate:
            ensure_no_match_fallback_roster(store)
    generation_getter = getattr(store, "get_roster_generation", None)
    if callable(generation_getter):
        generation = generation_getter()
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
            raise RuntimeError("roster generation counter is invalid")
        if generation == snapshot.roster_generation:
            return snapshot
    return capture_routing_snapshot(store, snapshot.config)


def bind_workforce_snapshot(store: Any, routing: RoutingSnapshot) -> tuple[RoutingSnapshot, Any]:
    """Capture contracts from the exact roster generation used by a route."""

    if getattr(routing, "roster_generation", 0) == 0:
        return routing, None
    from agency_runtime.core.roster.workforce import workforce_index_snapshot

    snapshot = routing
    for _attempt in range(2):
        workforce = workforce_index_snapshot(
            store,
            disabled_agents=frozenset(snapshot.config.agents.disabled),
        )
        if workforce.generation == snapshot.roster_generation:
            return snapshot, workforce
        snapshot = capture_routing_snapshot(store, snapshot.config)
    raise RuntimeError("roster changed while capturing the workforce routing snapshot")


__all__ = [
    "RoutingSnapshot",
    "bind_workforce_snapshot",
    "capture_operational_routing_snapshot",
    "capture_routing_snapshot",
    "catalog_for_routing",
]
