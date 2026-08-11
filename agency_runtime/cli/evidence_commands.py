"""Read-only evidence commands: what a host's own artifacts prove."""

from __future__ import annotations

import argparse
from pathlib import Path

from agency_runtime.core.child_delivery_evidence import (
    default_child_artifact_root,
    scan_child_delivery_evidence,
)
from agency_runtime.core.host_wiring_drift import host_wiring
from agency_runtime.core.store.evidence import (
    PUBLISHED_ANYWAY_RUN_STATUSES,
    WITHHELD_RUN_STATUSES,
)
from agency_runtime.core.store.sqlite import Store

from ._common import print_json as _print_json

_HOSTS = ("claude", "codex")
_WIRING_HOSTS = ("claude",)


def cmd_evidence_wiring(args: argparse.Namespace) -> int:
    """Report whether each host invokes the projection the installer staged.

    `agency status` answers whether the staged artifacts are current, which is a
    different question and once reported healthy while the host ran code from
    before the Job B deletion. Exit status is 1 on drift so this is usable as a
    gate before trusting any live observation.
    """

    hosts = (args.host,) if getattr(args, "host", None) else _WIRING_HOSTS
    results = [host_wiring(host) for host in hosts]
    if getattr(args, "json", False):
        _print_json(
            {
                "hosts": [
                    {
                        "host": result.host,
                        "wired": result.wired,
                        "reason": result.reason,
                        "staged_projection": result.staged_projection,
                        "staged_path": result.staged_path,
                        "wired_projection": result.wired_projection,
                        "wired_path": result.wired_path,
                    }
                    for result in results
                ]
            }
        )
    else:
        for result in results:
            if result.wired:
                print(f"{result.host}: wired to {result.staged_projection[:12]} ✅")
                continue
            print(f"{result.host}: NOT wired to what was staged — {result.reason}")
            print(f"  staged: {result.staged_projection[:12] or '(none)'}  {result.staged_path}")
            print(f"  wired : {result.wired_projection[:12] or '(none)'}  {result.wired_path}")
    return 0 if all(result.wired for result in results) else 1


def cmd_evidence_rejections(args: argparse.Namespace) -> int:
    """Report every turn Agency withheld, and every turn it published while blind.

    Rule 8 permits exactly one reason to cost a user a turn: Agency's verifier
    evaluated the response and rejected it. Agency being unable to verify or
    persist its own evidence is not a finding about the response, and publishes.

    Both outcomes close a run with a distinguishable status, so this makes the
    rule auditable after the fact rather than a claim about the code -- and it
    surfaces the rejections themselves, which with a full roster and contractor
    minting behind selection should be rare enough that each one is worth
    reading. Exit status is 1 when anything was withheld, so it is usable as a
    gate.
    """

    store = Store(getattr(args, "db", None))
    rows = store.get_withheld_and_published_runs(
        host=getattr(args, "host", None) or "",
        limit=getattr(args, "limit", 50) or 50,
    )
    withheld = [row for row in rows if row["status"] in WITHHELD_RUN_STATUSES]
    published = [row for row in rows if row["status"] in PUBLISHED_ANYWAY_RUN_STATUSES]
    if getattr(args, "json", False):
        _print_json(
            {
                "withheld": withheld,
                "published_anyway": published,
                "withheld_statuses": sorted(WITHHELD_RUN_STATUSES),
                "published_anyway_statuses": sorted(PUBLISHED_ANYWAY_RUN_STATUSES),
            }
        )
        return 1 if withheld else 0

    def _line(row: dict[str, object]) -> str:
        when = str(row.get("ended_at") or row.get("started_at") or "")[:19] or "-"
        return (
            f"  {row['status']!s:<20} {row['host']!s:<8} {when}  trace {str(row['trace_id'])[:12]}"
        )

    if not withheld:
        print("withheld by Agency: none ✅")
    else:
        print(f"withheld by Agency: {len(withheld)} — the verifier evaluated and rejected")
        for row in withheld:
            print(_line(row))
    if published:
        # Deliberately not labelled "published": the status records that Agency
        # was blind for that turn, not what the host did with the response. Runs
        # closed before the rule-8 fix were denied on exactly this condition, so
        # calling them published would be a claim this data cannot support.
        print(
            f"Agency was blind: {len(published)} — could not verify or persist its "
            "evidence. Under rule 8 these publish; before the fix they were denied."
        )
        for row in published:
            print(_line(row))
    return 1 if withheld else 0


def cmd_evidence_children(args: argparse.Namespace) -> int:
    """Report which harness-spawned children provably received a card.

    Reads only what the host wrote. A card is counted when its body verifies
    against its own pinned hash inside the input the child received before it
    first spoke — never from an Agency row, which the delivering code writes.
    """

    hosts = (args.host,) if getattr(args, "host", None) else _HOSTS
    override = getattr(args, "root", None)
    if override and len(hosts) != 1:
        raise ValueError("--root applies to exactly one --host")
    results = []
    for host in hosts:
        root = Path(override) if override else default_child_artifact_root(host)
        findings = scan_child_delivery_evidence(root, host=host) if root.is_dir() else []
        results.append(
            {
                "host": host,
                "root": str(root),
                "root_present": root.is_dir(),
                "staffed_children": sum(1 for finding in findings if finding.staffed),
                "legacy_deliveries": sum(
                    1 for finding in findings if finding.legacy_delivery and not finding.staffed
                ),
                "children": [
                    {
                        "child_id": finding.child_id,
                        "artifact": finding.artifact,
                        "parent_id": finding.host_parent_id,
                        "correlated": finding.correlated,
                        "legacy": finding.legacy_delivery,
                        "cards": [
                            {
                                "slug": card.specialist_slug,
                                "version": card.specialist_version,
                                "prompt_hash": card.specialist_prompt_hash,
                            }
                            for card in finding.cards
                        ],
                    }
                    for finding in findings
                ],
            }
        )
    if getattr(args, "json", False):
        _print_json({"hosts": results})
        return 0
    for result in results:
        if not result["root_present"]:
            print(f"{result['host']}: no artifacts at {result['root']}")
            continue
        print(
            f"{result['host']}: {result['staffed_children']} children provably staffed "
            f"({result['legacy_deliveries']} legacy) under {result['root']}"
        )
        for child in result["children"]:
            slugs = ", ".join(card["slug"] for card in child["cards"]) or "-"
            marks = "" if child["correlated"] else "  [uncorrelated]"
            legacy = "  [legacy envelope]" if child["legacy"] else ""
            print(f"  {child['child_id']}  {slugs}{marks}{legacy}")
    return 0
