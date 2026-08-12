"""Read-only, source-labelled evidence from host artifacts or Agency's Store."""

from __future__ import annotations

import argparse
from pathlib import Path

from agency_runtime.core.child_delivery_evidence import (
    MAX_CHILD_ARTIFACTS,
    MAX_CHILD_FILESYSTEM_ENTRIES,
    MAX_LAUNCH_PREFIX_BYTES,
    MAX_LAUNCH_RECORDS,
    child_delivery_projection,
    default_child_artifact_root,
)
from agency_runtime.core.config import load_config
from agency_runtime.core.host_capabilities import EXECUTION_HOSTS
from agency_runtime.core.host_wiring_drift import host_wiring
from agency_runtime.core.routing_latency import (
    DEFAULT_ROUTING_LATENCY_BUDGET_MS,
    routing_latency_projection,
)
from agency_runtime.core.rule8_evidence import (
    bounded_rule8_limit,
    rule8_evidence_projection,
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
        _print_json({"hosts": [result.as_dict() for result in results]})
    else:
        for result in results:
            if result.wired:
                print(f"{result.host}: wired to {result.staged_projection[:12]} ✅")
                continue
            if result.status == "not_measured":
                print(f"{result.host}: wiring not measured — {result.reason}")
                continue
            label = "DRIFT" if result.status == "drift" else "wiring unavailable"
            print(f"{result.host}: {label} — {result.reason}")
            print(f"  staged: {result.staged_projection[:12] or '(none)'}  {result.staged_path}")
            print(f"  wired : {result.wired_projection[:12] or '(none)'}  {result.wired_path}")
    return 0 if all(result.wired for result in results) else 1


def cmd_evidence_rejections(args: argparse.Namespace) -> int:
    """Report the bounded exceptional-run window on each side of Rule 8.

    Rule 8 permits exactly one reason to cost a user a turn: Agency's verifier
    evaluated the response and rejected it. Agency being unable to verify or
    persist its own evidence is not a finding about the response. Rule 8 now
    requires pass-through, but the stored status alone does not prove what a
    historical host did with the turn.

    Both outcomes close a run with a distinguishable status, so this makes the
    rule auditable after the fact rather than a claim about the code -- and it
    surfaces the rejections themselves, which with a full roster and contractor
    minting behind selection should be rare enough that each one is worth
    reading. Exit status is 1 when anything was withheld, so it is usable as a
    gate.
    """

    host = str(getattr(args, "host", None) or "").strip().casefold()
    if host and host not in EXECUTION_HOSTS:
        raise ValueError("Rule-8 evidence host is unsupported")
    raw_limit = getattr(args, "limit", None)
    limit = bounded_rule8_limit(50 if raw_limit is None else raw_limit)
    store = Store(getattr(args, "db", None))
    rows = store.get_withheld_and_published_runs(
        host=host,
        limit=limit,
    )
    projection = rule8_evidence_projection(rows, host=host, limit=limit)
    withheld = projection["withheld"]
    agency_blind = projection["agency_blind"]
    if getattr(args, "json", False):
        _print_json(
            {
                **projection,
                # Compatibility only. The canonical name is ``agency_blind``:
                # these statuses do not prove what a historical host did with
                # the turn, despite the legacy key's stronger wording.
                "published_anyway": agency_blind,
                "published_anyway_statuses": projection["agency_blind_statuses"],
                "compatibility_aliases": {
                    "published_anyway": (
                        "agency_blind; legacy key name does not prove host publication"
                    ),
                    "published_anyway_statuses": "agency_blind_statuses",
                },
            }
        )
        return 1 if withheld else 0

    def _line(row: dict[str, object]) -> str:
        when = str(row.get("ended_at") or row.get("started_at") or "")[:19] or "-"
        return (
            f"  {row['status']!s:<20} {row['host']!s:<8} {when}  trace {str(row['trace_id'])[:12]}"
        )

    if not withheld and not agency_blind:
        print(
            f"no matching exceptional statuses in this retained bounded window "
            f"(limit {limit}{f', host {host}' if host else ''}); this is not a health claim"
        )
        return 0
    if not withheld:
        print("withheld by Agency: none in this retained bounded window")
    else:
        print(f"withheld by Agency: {len(withheld)} — the verifier evaluated and rejected")
        for row in withheld:
            print(_line(row))
    if agency_blind:
        print(
            f"Agency was blind: {len(agency_blind)} — could not verify or persist its "
            "evidence. Rule 8 requires pass-through, but these rows alone do not prove "
            "what the host did; historical rows can predate that rule."
        )
        for row in agency_blind:
            print(_line(row))
    return 1 if withheld else 0


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

    budget = int(
        getattr(args, "budget_ms", DEFAULT_ROUTING_LATENCY_BUDGET_MS)
        or DEFAULT_ROUTING_LATENCY_BUDGET_MS
    )
    rows = Store(getattr(args, "db", None)).get_routing_latencies(
        source=getattr(args, "source", None) or "",
        limit=getattr(args, "limit", 200) or 200,
    )
    projection = routing_latency_projection(rows, budget_ms=budget)
    overall = projection["overall"]
    split = projection["split"]
    grouped = projection["by_source"]
    over_budget = projection["over_budget"]

    if getattr(args, "json", False):
        _print_json(projection)
        return 1 if over_budget else 0

    if not overall["count"]:
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
    raw_limit = getattr(args, "limit", None)
    limit = 50 if raw_limit is None else raw_limit
    if override and len(hosts) != 1:
        raise ValueError("--root applies to exactly one --host")
    results = []
    for host in hosts:
        root = Path(override) if override else default_child_artifact_root(host)
        results.append(child_delivery_projection(root, host=host, limit=limit))
    if getattr(args, "json", False):
        _print_json(
            {
                "window": {
                    "kind": "newest_verified_child_delivery_evidence",
                    "hosts": list(hosts),
                    "detail_limit": limit,
                },
                "bounds": {
                    "artifact_scan_limit_per_host": MAX_CHILD_ARTIFACTS,
                    "filesystem_visit_limit_per_host": MAX_CHILD_FILESYSTEM_ENTRIES,
                    "artifact_prefix_bytes": MAX_LAUNCH_PREFIX_BYTES,
                    "artifact_record_limit": MAX_LAUNCH_RECORDS,
                    "detail_limit": limit,
                },
                "hosts": results,
            }
        )
        return 0
    for result in results:
        if not result["root_present"]:
            print(f"{result['host']}: artifact root is absent at {result['root']}")
            continue
        if not result["evidence_count"]:
            print(
                f"{result['host']}: no verified card-delivery proof found in "
                f"{result['artifacts_scanned']} bounded artifact candidate(s); this does "
                "not prove that no children ran"
            )
            continue
        print(
            f"{result['host']}: {result['staffed_children']} children provably staffed "
            f"({result['legacy_deliveries']} legacy-only; "
            f"{result['uncorrelated_staffed_children']} uncorrelated) under {result['root']}"
        )
        for child in result["children"]:
            slugs = ", ".join(card["slug"] for card in child["cards"]) or "-"
            marks = "" if child["correlated"] else "  [uncorrelated]"
            legacy = "  [legacy envelope]" if child["legacy"] else ""
            print(f"  {child['child_id']}  {slugs}{marks}{legacy}")
    return 0
