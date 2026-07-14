#!/usr/bin/env python3
"""Regenerate the explicit companion-policy availability registry.

The broad policy intentionally contains more routes than the small bundled
roster. Every referenced slug is classified as either a required bundled
specialist or a roster-gated specialist. The generated block makes additions
fail validation until this script is run and the resulting classification is
reviewed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "agency_runtime" / "core" / "companion_policy.yaml"
BEGIN = "# BEGIN GENERATED SPECIALIST AVAILABILITY"
END = "# END GENERATED SPECIALIST AVAILABILITY"
DISABLED_REASON = (
    "No governed active definition is available; this route is enabled only "
    "after approved roster activation."
)
ENABLED = (
    "code-reviewer",
    "internationalization-engineer",
    "payments-billing-engineer",
    "senior-developer",
    "technical-writer",
    "test-automation-engineer",
    "workflow-architect",
)


def _action_slugs(actions: Any) -> set[str]:
    slugs: set[str] = set()
    if not isinstance(actions, dict):
        return slugs
    for action in actions.values():
        if not isinstance(action, dict):
            continue
        for key in ("always_include", "conditional"):
            entries = action.get(key) or []
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict) and entry.get("slug"):
                    slugs.add(str(entry["slug"]))
    return slugs


def _division_slugs(divisions: Any) -> set[str]:
    slugs: set[str] = set()
    if not isinstance(divisions, dict):
        return slugs
    for division in divisions.values():
        if not isinstance(division, dict):
            continue
        anchor = division.get("anchor")
        if isinstance(anchor, str) and anchor:
            slugs.add(anchor)
        conditional = division.get("conditional") or []
        if not isinstance(conditional, list):
            continue
        for entry in conditional:
            if isinstance(entry, (list, tuple)) and entry and entry[0]:
                slugs.add(str(entry[0]))
            elif isinstance(entry, dict) and entry.get("slug"):
                slugs.add(str(entry["slug"]))
    return slugs


def _referenced_slugs(policy: dict[str, Any]) -> set[str]:
    return _action_slugs(policy.get("actions") or {}) | _division_slugs(
        policy.get("division_anchors") or {}
    )


def _without_generated_block(text: str) -> str:
    if BEGIN not in text and END not in text:
        return text.rstrip() + "\n"
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError("policy availability markers are incomplete or duplicated")
    before, remainder = text.split(BEGIN, 1)
    _generated, after = remainder.split(END, 1)
    return (before.rstrip() + "\n" + after.lstrip("\r\n")).rstrip() + "\n"


def _render(policy: dict[str, Any]) -> str:
    referenced = _referenced_slugs(policy)
    enabled = set(ENABLED)
    missing = sorted(enabled - referenced)
    if missing:
        raise ValueError(f"enabled specialists are not referenced by policy: {missing}")
    gated = sorted(referenced - enabled)
    lines = [
        BEGIN,
        "specialist_availability:",
        "  schema_version: 1",
        "  enabled:",
        *[f"  - {slug}" for slug in sorted(enabled)],
        "  roster_gated:",
        f"    reason: {json.dumps(DISABLED_REASON)}",
        "    slugs:",
        *[f"    - {slug}" for slug in gated],
        END,
    ]
    return "\n".join(lines) + "\n"


def generated_text(text: str) -> str:
    base = _without_generated_block(text)
    loaded = yaml.safe_load(base) or {}
    if not isinstance(loaded, dict):
        raise ValueError("companion policy root must be a mapping")
    generated = base.rstrip() + "\n\n" + _render(loaded)
    reparsed = yaml.safe_load(generated)
    if not isinstance(reparsed, dict):
        raise ValueError("generated companion policy did not parse as a mapping")
    return generated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    current = POLICY_PATH.read_text(encoding="utf-8")
    expected = generated_text(current)
    if current == expected:
        return 0
    if args.check:
        print(f"out of date: {POLICY_PATH.relative_to(ROOT)}")
        return 1
    POLICY_PATH.write_text(expected, encoding="utf-8", newline="\n")
    print(f"updated: {POLICY_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
