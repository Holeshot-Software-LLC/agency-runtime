"""Read-only evidence commands: what a host's own artifacts prove."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from agency_runtime.core.child_delivery_evidence import (
    default_child_artifact_root,
    scan_child_delivery_evidence,
)
from agency_runtime.core.config import load_config
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


def _percentile(ordered: list[int], percentile: float) -> int:
    """Return the nearest-rank percentile of an already-sorted list."""

    if not ordered:
        return 0
    rank = max(1, math.ceil(percentile / 100 * len(ordered)))
    return ordered[min(len(ordered), rank) - 1]


def _latency_summary(values: list[int]) -> dict[str, int]:
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "min_ms": ordered[0] if ordered else 0,
        "p50_ms": _percentile(ordered, 50),
        "p95_ms": _percentile(ordered, 95),
        "max_ms": ordered[-1] if ordered else 0,
    }


def cmd_evidence_latency(args: argparse.Namespace) -> int:
    """Report what Agency's own routing actually costs a turn.

    ``routing_decisions.latency_ms`` is the only timing column in the schema
    and nothing read it, so the cost of an eligible turn was invisible unless
    someone opened the database by hand. `agency eval routing` gates latency
    and the benchmarks score it, but both answer "did a fixture pass", not
    "what is this box paying right now".

    Reports the percentiles rather than a mean, because the mean of a
    provider-call distribution hides exactly the tail an operator feels. Exit
    status is 1 when p95 exceeds the budget, so this is usable as a gate; the
    default matches the pinned cold control rather than being invented here.

    Decisions recorded at zero are excluded rather than counted as fast turns.
    Both writers store 0 when no provider call was spent, so including them
    would report Agency as cheap in exact proportion to how often it did
    nothing.
    """

    budget = int(getattr(args, "budget_ms", 15000) or 15000)
    rows = Store(getattr(args, "db", None)).get_routing_latencies(
        source=getattr(args, "source", None) or "",
        limit=getattr(args, "limit", 200) or 200,
    )
    values = [int(row["latency_ms"]) for row in rows]
    overall = _latency_summary(values)
    # Only decisions whose calls actually reported a duration can be split.
    # Receipts written before the latency column existed report 0, and counting
    # those as "no provider time" would attribute the whole turn to Agency.
    attributable = [row for row in rows if int(row.get("provider_ms") or 0) > 0]
    split = {
        "decisions": len(attributable),
        "unattributed_decisions": len(rows) - len(attributable),
        "provider_ms": _latency_summary([int(row["provider_ms"]) for row in attributable]),
        "agency_ms": _latency_summary(
            [max(0, int(row["latency_ms"]) - int(row["provider_ms"])) for row in attributable]
        ),
        "calls_per_decision": (
            round(
                sum(int(row.get("provider_calls") or 0) for row in attributable)
                / len(attributable),
                2,
            )
            if attributable
            else 0.0
        ),
    }
    buckets: dict[str, list[int]] = {}
    for row in rows:
        buckets.setdefault(str(row["source"] or "unknown"), []).append(int(row["latency_ms"]))
    grouped = {name: _latency_summary(bucket) for name, bucket in sorted(buckets.items())}
    over_budget = bool(values) and overall["p95_ms"] > budget

    if getattr(args, "json", False):
        _print_json(
            {
                "budget_ms": budget,
                "over_budget": over_budget,
                "overall": overall,
                "split": split,
                "by_source": grouped,
                "slowest": rows[:5] if rows else [],
            }
        )
        return 1 if over_budget else 0

    if not values:
        print("no routing decision has recorded a latency yet")
        return 0
    print(
        f"routing latency over {overall['count']} decisions "
        f"(budget p95 {budget} ms): "
        f"min {overall['min_ms']} ms, p50 {overall['p50_ms']} ms, "
        f"p95 {overall['p95_ms']} ms, max {overall['max_ms']} ms"
    )
    for name, summary in grouped.items():
        print(
            f"  {name:<32} n={summary['count']:<5} "
            f"p50 {summary['p50_ms']:>7} ms  p95 {summary['p95_ms']:>7} ms  "
            f"max {summary['max_ms']:>7} ms"
        )
    if split["decisions"]:
        print(
            f"split over {split['decisions']} decisions "
            f"({split['calls_per_decision']} provider calls each): "
            f"provider p50 {split['provider_ms']['p50_ms']} ms, "
            f"Agency p50 {split['agency_ms']['p50_ms']} ms"
        )
    if split["unattributed_decisions"]:
        print(
            f"  {split['unattributed_decisions']} decision(s) cannot be split — their "
            "receipts predate the per-call duration and report 0"
        )
    if over_budget:
        print(
            f"❌ p95 {overall['p95_ms']} ms exceeds the {budget} ms budget — "
            "Agency is the slow part of an eligible turn"
        )
    else:
        print(f"✅ p95 within the {budget} ms budget")
    return 1 if over_budget else 0


def cmd_evidence_intent(args: argparse.Namespace) -> int:
    """Show what each turn was understood to be, beside who was staffed for it.

    Selection quality had no audit surface at all: the store keeps
    ``source_message_hash`` and ``query_hash`` but never what was asked, so
    "were these the right specialists?" could only be answered by someone who
    happened to remember the prompt. This prints the planner's own work-unit
    text next to the specialists that decision produced, which is the
    comparison an audit actually needs.

    Retention is off unless ``selector.record_routing_intent`` is enabled, so
    an empty table has two very different causes and this says which.
    """

    store = Store(getattr(args, "db", None))
    rows = store.get_routing_intents(limit=getattr(args, "limit", 20) or 20)
    wanted = str(getattr(args, "specialist", None) or "").strip()
    if wanted:
        rows = [row for row in rows if wanted in (row.get("selected_ids") or [])]

    if getattr(args, "json", False):
        _print_json({"retained": len(rows), "decisions": rows})
        return 0

    if not rows:
        enabled = bool(getattr(load_config().selector, "record_routing_intent", False))
        if enabled:
            print("intent retention is on, but no decision has been recorded yet")
        else:
            print(
                "no retained intent — selection cannot be audited until retention is on.\n"
                "  Enable it with: agency config set selector.record_routing_intent true\n"
                "  This is the one routing table that keeps content derived from your "
                "prompts; every other one stores only hashes."
            )
        return 0

    print(f"retained intent for {len(rows)} decision(s), newest first")
    for row in rows:
        selected = row.get("selected_ids") or []
        print(f"\n{row.get('created_at', '')}  [{row.get('source') or 'unknown'}]")
        print(f"  staffed: {', '.join(selected) if selected else 'nobody'}")
        units = row.get("units") or []
        if not units:
            print("  understood as: (no work-unit text recorded)")
            continue
        print("  understood as:")
        for ordinal, unit in enumerate(units, start=1):
            print(f"    {ordinal}. {unit}")
    return 0


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
