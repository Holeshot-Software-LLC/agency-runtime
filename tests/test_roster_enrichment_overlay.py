"""Enrichment overlay contract: supplements typed stacks/domains and scope qualifiers."""

from __future__ import annotations

from agency_runtime.core.roster import enrichment


def test_overlay_is_present_and_loads_known_specialists() -> None:
    # ADR-0087 / AR-119: the shipped overlay must load and expose the
    # representative enriched specialists. senior-developer is the canonical
    # case (owns FluxUI/Livewire through prose but has empty typed stacks
    # without enrichment).
    overlay = enrichment.enrichment_overlay()
    known = {slug for slug in overlay if not slug.startswith("_")}
    assert "senior-developer" in known
    row = overlay["senior-developer"]
    assert "fluxui" in row["stacks"]
    assert row["scope_qualifiers"]


def test_apply_enrichment_supplements_without_overriding() -> None:
    # Enrichment only supplements: a value the roster already declares stays
    # ahead of the overlay, and overlay values are appended without duplicates.
    overlay_before = enrichment.enrichment_overlay()
    assert "senior-developer" in {slug for slug in overlay_before if not slug.startswith("_")}
    agent = {"slug": "senior-developer", "stacks": ["existing-stack"]}
    enrichment.apply_enrichment(agent)
    # Declared value wins (stays first); overlay stacks appended after.
    assert agent["stacks"][0] == "existing-stack"
    assert "fluxui" in agent["stacks"]


def test_apply_enrichment_is_noop_for_unenriched_slug() -> None:
    agent = {"slug": "definitely-not-a-real-specialist", "stacks": ["x"]}
    enrichment.apply_enrichment(agent)
    assert agent == {"slug": "definitely-not-a-real-specialist", "stacks": ["x"]}


def test_apply_enrichment_creates_missing_list_field() -> None:
    # If the agent dict lacks the field entirely, enrichment seeds it.
    agent = {"slug": "senior-developer"}
    enrichment.apply_enrichment(agent)
    assert "fluxui" in agent["stacks"]
    assert agent["scope_qualifiers"]


def test_enrichment_flows_through_bundled_roster_to_contract_projection() -> None:
    # End-to-end: the overlay merged in bundled_roster() must reach the typed
    # WorkforceContract so the deterministic verifier scores stack coverage.
    from agency_runtime.core.roster.bundled import bundled_roster
    from agency_runtime.core.workforce.contract import project_workforce_contract

    agents = {agent["slug"]: agent for agent in bundled_roster()}
    senior = agents["senior-developer"]
    assert "fluxui" in senior["stacks"]
    contract = project_workforce_contract(senior)
    assert "fluxui" in contract.stacks
    assert contract.scope_qualifiers
