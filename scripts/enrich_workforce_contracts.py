"""Batch-enrich workforce contracts with user-facing scope qualifiers.

Analyzes each specialist's description, capabilities, and existing scope to
produce the natural-language terms users would actually use to ask for that
specialist. This bridges the vocabulary gap between specialist-speak
("implement bounded history and branch operations") and user-speak
("commit and push", "create a pull request").

Run once to batch-enrich the roster, then the sync process applies the same
enrichment to new agents and the hiring process applies it to contractors.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from agency_runtime.core.config import AgencyConfig, ProviderEntry
from agency_runtime.core.roster.bundled import BundledRoster
from agency_runtime.core.structured_provider import StructuredProviderResult
from agency_runtime.core.workforce.inference import invoke_structured_provider_result

ENRICHMENT_SYSTEM = (
    "You are a workforce contract enricher. Given a specialist's identity, "
    "description, capabilities, and existing scope, produce 2-4 concise "
    "user-facing scope qualifiers that capture the natural-language terms a "
    "person would use to ask for this specialist. Think about how a developer, "
    "manager, or stakeholder would phrase the request — not how the specialist "
    "describes itself. Use common verbs and nouns from everyday engineering "
    "language. Each qualifier is a short phrase (3-8 words). Return only a JSON "
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


def enrich_agent(
    agent: dict,
    *,
    provider: ProviderEntry,
) -> list[str] | None:
    """Use inference to produce enriched user-facing scope qualifiers."""
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
    return [str(q).strip() for q in qualifiers if str(q).strip()]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Enrich workforce contracts with user-facing scope qualifiers")
    parser.add_argument("--output", default="docs/workforce-enrichment.json", help="Output JSON file")
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
    enriched: dict[str, list[str]] = {}
    for i, agent in enumerate(roster):
        slug = agent["slug"]
        print(f"  [{i+1}/{len(roster)}] {slug}...", end=" ", flush=True)
        try:
            qualifiers = enrich_agent(agent, provider=provider)
            if qualifiers:
                enriched[slug] = qualifiers
                print(f"OK ({len(qualifiers)} qualifiers)")
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
