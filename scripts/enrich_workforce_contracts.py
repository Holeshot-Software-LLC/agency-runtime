"""Batch-enrich workforce contracts with user-facing scope qualifiers and stacks.

Analyzes each specialist's description, capabilities, and existing scope to
produce (1) the natural-language terms users would actually use to ask for that
specialist (bridging the vocabulary gap between specialist-speak "implement
bounded history and branch operations" and user-speak "commit and push") and
(2) controlled stack identifiers the deterministic verifier scores as typed
coverage (many specialists declare no stacks, so a FluxUI/Livewire owner scores
zero stack coverage until enriched).

The output is the overlay file consumed by
:mod:`agency_runtime.core.roster.enrichment`
(``agency_runtime/core/roster/data/scope_qualifiers.json`` by default), merged
into each agent dict in :func:`bundled_roster` before contract projection.
Run once to batch-enrich the roster; the same enrichment is applied to new
agents during sync and to contractors during hiring.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from agency_runtime.core.config import AgencyConfig, ProviderEntry
from agency_runtime.core.roster.bundled import BundledRoster
from agency_runtime.core.workforce.inference import invoke_structured_provider_result

ENRICHMENT_SYSTEM = (
    "You are a workforce contract enricher. Given a specialist's identity, "
    "description, capabilities, and existing scope, produce (1) 2-4 concise "
    "user-facing scope qualifiers that capture the natural-language terms a "
    "person would use to ask for this specialist (think how a developer, "
    "manager, or stakeholder would phrase the request, not how the specialist "
    "describes itself; each qualifier is a short phrase of 3-8 words), and "
    "(2) 0-6 controlled stack identifiers for the languages/frameworks/platforms "
    "this specialist actually owns (lowercase, dot/hyphen/plus-separated tokens "
    "such as python, typescript, react, laravel, livewire, fluxui, postgres). "
    "Omit stacks the specialist does not genuinely own. Return only a JSON "
    "object matching the schema."
)

ENRICHMENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "scope_qualifiers": {
            "type": "array",
            "items": {"type": "string", "minLength": 3, "maxLength": 80},
            "minItems": 2,
            "maxItems": 4,
        },
        "stacks": {
            "type": "array",
            "items": {"type": "string", "pattern": r"^[a-z0-9][a-z0-9._+-]{0,63}$"},
            "maxItems": 6,
        },
    },
    "required": ["scope_qualifiers"],
}


def _build_prompt(agent: dict) -> str:
    """Build a compact enrichment prompt from a specialist's identity."""
    parts = [f"slug: {agent['slug']}"]
    if agent.get("name"):
        parts.append(f"name: {agent['name']}")
    if agent.get("description"):
        parts.append(f"description: {agent['description']}")
    if agent.get("capabilities"):
        parts.append(f"capabilities: {', '.join(agent['capabilities'])}")
    existing = agent.get("scope_qualifiers") or agent.get("preferred_when") or []
    if existing:
        parts.append(f"existing scope: {json.dumps(existing)}")
    return "\n".join(parts)


def _norm_stack(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().casefold()
    if not token or len(token) > 64:
        return None
    import re

    return token if re.fullmatch(r"[a-z0-9][a-z0-9._+-]{0,63}", token) else None


def enrich_agent(
    agent: dict,
    *,
    provider: ProviderEntry,
) -> dict[str, list[str]] | None:
    """Use inference to produce enriched scope qualifiers and typed stacks.

    Returns ``{"scope_qualifiers": [...], "stacks": [...]}`` (stacks may be
    empty) matching the overlay format consumed by
    :func:`agency_runtime.core.roster.enrichment.apply_enrichment`.
    """

    prompt = _build_prompt(agent)
    result = invoke_structured_provider_result(
        provider,
        prompt,
        ENRICHMENT_SCHEMA,
        system_prompt=ENRICHMENT_SYSTEM,
        timeout=30,
    )
    if result is None or not isinstance(result.value, dict):
        return None
    qualifiers = result.value.get("scope_qualifiers")
    if not isinstance(qualifiers, list) or not qualifiers:
        return None
    cleaned_qualifiers = [str(q).strip() for q in qualifiers if str(q).strip()]
    if not cleaned_qualifiers:
        return None
    raw_stacks = result.value.get("stacks") or []
    stacks: list[str] = []
    seen: set[str] = set()
    for item in raw_stacks:
        normalized = _norm_stack(item)
        if normalized and normalized not in seen:
            seen.add(normalized)
            stacks.append(normalized)
    return {"scope_qualifiers": cleaned_qualifiers, "stacks": stacks}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Enrich workforce contracts with user-facing scope qualifiers and typed stacks",
    )
    parser.add_argument(
        "--output",
        default="agency_runtime/core/roster/data/scope_qualifiers.json",
        help="Output overlay JSON file (consumed by roster.enrichment)",
    )
    parser.add_argument("--limit", type=int, default=0, help="Limit to N specialists (0 = all)")
    parser.add_argument("--slug", default="", help="Enrich only this slug")
    args = parser.parse_args()

    config = AgencyConfig()
    if not config.providers:
        print("ERROR: no provider configured. Set AGENCY_CONFIG_PATH.", file=sys.stderr)
        return 1

    provider = config.providers[0]
    roster = list(BundledRoster())
    if args.slug:
        roster = [a for a in roster if a["slug"] == args.slug]
    elif args.limit:
        roster = roster[: args.limit]

    print(f"Enriching {len(roster)} specialists with provider {provider.name}...")
    enriched: dict[str, dict[str, list[str]]] = {}
    for i, agent in enumerate(roster):
        slug = agent["slug"]
        print(f"  [{i + 1}/{len(roster)}] {slug}...", end=" ", flush=True)
        try:
            row = enrich_agent(agent, provider=provider)
            if row:
                enriched[slug] = row
                print(
                    f"OK ({len(row['scope_qualifiers'])} qualifiers, {len(row['stacks'])} stacks)"
                )
            else:
                print("SKIP (no result)")
        except Exception as exc:
            print(f"ERROR: {exc}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nEnriched {len(enriched)}/{len(roster)} specialists -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
