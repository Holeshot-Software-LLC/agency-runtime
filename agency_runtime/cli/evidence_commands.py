"""Read-only, source-labelled evidence from host artifacts or Agency's Store."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from agency_runtime.core.child_delivery_evidence import (
    MAX_CHILD_ARTIFACTS,
    MAX_CHILD_FILESYSTEM_ENTRIES,
    MAX_LAUNCH_PREFIX_BYTES,
    MAX_LAUNCH_RECORDS,
    child_delivery_projection,
    default_child_artifact_root,
)
from agency_runtime.core.child_launch_outcomes import (
    MAX_CHILD_LAUNCHES,
    resolve_child_launch_outcomes,
)
from agency_runtime.core.config import load_config
from agency_runtime.core.deployed_fix_witness import HostWitness, attest_host
from agency_runtime.core.host_capabilities import EXECUTION_HOSTS
from agency_runtime.core.host_wiring_drift import host_wiring
from agency_runtime.core.native_child_staffing import (
    _failure_context_fingerprint as native_child_failure_context_fingerprint,
)
from agency_runtime.core.routing_latency import (
    DEFAULT_ROUTING_LATENCY_BUDGET_MS,
    routing_latency_projection,
)
from agency_runtime.core.rule8_evidence import (
    bounded_rule8_limit,
    rule8_evidence_projection,
)
from agency_runtime.core.runtime_staleness import recorded_hosts
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


def cmd_evidence_witness(args: argparse.Namespace) -> int:
    """Attest that each host's invoked projection carries every documented fix.

    `evidence wiring` proves a host invokes the projection the installer
    staged; this proves that projection carries the load-bearing code of each
    registered fix, and records the verdict in Agency's own private witness
    manifest and history so later drift can be bisected (AR-363). Nothing
    under a host's tree is touched. Exit status is 1 unless every host is
    attested, so this is usable as a gate.
    """

    hosts = (args.host,) if getattr(args, "host", None) else recorded_hosts()
    results = [attest_host(host) for host in hosts]
    if getattr(args, "json", False):
        _print_json({"hosts": [result.as_dict() for result in results]})
    elif not results:
        print("no host has a recorded install pointer; nothing to attest")
    else:
        for result in results:
            _print_witness(result)
    return 0 if all(result.status == "attested" for result in results) else 1


def _print_witness(result: HostWitness) -> None:
    """Print one host's verdict, naming where its wired identity came from."""

    present = sum(1 for item in result.fixes if item.present)
    via = f"wired via {result.wired_source}"
    if result.status == "attested":
        print(
            f"{result.host}: attested — projection {result.wired_digest[:12]} carries "
            f"{present}/{len(result.fixes)} registered fixes ({via}) ✅"
        )
        return
    labels = {"drift": "DRIFT", "missing_fix": "MISSING FIX"}
    print(f"{result.host}: {labels.get(result.status, 'unavailable')} — {result.reason}")
    print(
        f"  published: {result.published_digest[:12] or '(none)'}  "
        f"wired: {result.wired_digest[:12] or '(none)'}  ({via})"
    )
    for item in result.fixes:
        if item.checked and not item.present:
            print(
                f"  missing {item.fix.fix_id}: {item.fix.summary} "
                f"[{item.state}] {item.fix.relative_path}"
            )
    if result.record_error:
        print(f"  witness record not written ({result.record_error})")


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
    """Report persisted routing durations against a p95 budget.

    ``routing_decisions.latency_ms`` is the only timing column in the schema
    and nothing read it, so observed routing duration was invisible unless
    someone opened the database by hand. `agency eval routing` gates latency
    and the benchmarks score it, but both answer "did a fixture pass", not
    "what routing durations has this box recorded".

    Reports the percentiles rather than a mean, because the mean of a
    provider-call distribution hides exactly the tail an operator feels. Exit
    status is 1 when p95 exceeds the budget, so this is usable as a gate; the
    default matches the pinned cold control rather than being invented here.

    Decisions recorded at zero are excluded rather than counted as fast turns.
    Both writers store 0 when no provider call was spent, so including them
    would lower the recorded routing summary in exact proportion to how often
    no provider call was made.
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
            f"timing breakdown over {split['decisions']} decisions "
            f"({split['calls_per_decision']} provider calls each): "
            f"provider p50 {split['provider_ms']['p50_ms']} ms, "
            "derived routing remainder p50 "
            f"{split['derived_routing_remainder_ms']['p50_ms']} ms "
            "(recorded total minus timed provider receipts)"
        )
    if split["unattributed_decisions"]:
        print(
            f"  {split['unattributed_decisions']} decision(s) cannot be broken down — "
            "provider timing is incomplete or inconsistent with the recorded total"
        )
    if over_budget:
        print(f"❌ measured routing p95 {overall['p95_ms']} ms exceeds the {budget} ms budget")
    else:
        print(f"✅ p95 within the {budget} ms budget")
    return 1 if over_budget else 0


def cmd_evidence_selections(args: argparse.Namespace) -> int:
    """Report bounded specialist-selection frequency with explicit denominators.

    This is the terminal projection of the same retained routing decisions used
    by the dashboard's concentration chart. Decision share answers how often a
    specialist appeared in a selection-bearing decision. Occurrence share uses
    every selected specialist as its denominator. The current active roster is
    context only; it is not a historical selection denominator.
    """

    projection = Store(getattr(args, "db", None)).specialist_selection_distribution()
    if getattr(args, "json", False):
        _print_json(projection)
        return 0

    decisions = int(projection["decisions_with_selections"])
    occurrences = int(projection["selection_occurrences"])
    distinct = int(projection["distinct_selected_specialists"])
    roster_size = int(projection["active_roster_size"])
    scan_limit = int(projection["selection_bearing_decision_scan_limit"])
    print(
        f"specialist selection distribution: {decisions} selection-bearing decisions; "
        f"{occurrences} selection occurrences; {distinct} distinct selected specialists"
    )
    print(
        f"current active roster: {roster_size} "
        "(context only; not a historical selection denominator)"
    )
    print(
        f"top-10 concentration: {projection['top_10_selection_occurrences']} of "
        f"{occurrences} selection occurrences "
        f"({float(projection['top_10_share_of_selection_occurrences']):.1%})"
    )
    if projection["selection_bearing_decision_scan_truncated"]:
        print(
            f"window: newest {scan_limit} selection-bearing decisions; "
            "older retained evidence is outside this view"
        )
    else:
        print(
            f"window: all retained selection-bearing decisions scanned (safety limit {scan_limit})"
        )
    if not decisions:
        print("no per-specialist selection shares are available; this is not a health claim")
        return 0

    for row in projection["top_specialists"]:
        print(
            f"  {row['slug']}: {row['decisions_containing_specialist']} decisions "
            f"({float(row['share_of_decisions_with_selections']):.1%} of "
            "selection-bearing decisions); "
            f"{row['selection_occurrences']} selection occurrences "
            f"({float(row['share_of_selection_occurrences']):.1%} of all "
            "selection occurrences)"
        )
    long_tail = projection["long_tail"]
    if long_tail["specialist_count"]:
        count = int(long_tail["specialist_count"])
        print(
            f"  beyond top 50 ({count} specialist{'s' if count != 1 else ''}): "
            f"{long_tail['decisions_containing_specialist']} decisions "
            f"({float(long_tail['share_of_decisions_with_selections']):.1%} of "
            "selection-bearing decisions); "
            f"{long_tail['selection_occurrences']} selection occurrences "
            f"({float(long_tail['share_of_selection_occurrences']):.1%} of all "
            "selection occurrences)"
        )
    return 0


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

    This command is diagnostic and read-only. Receipt creation belongs only to
    the in-lifetime safe-host collector, never a caller-selected path.
    """

    hosts = (args.host,) if getattr(args, "host", None) else _HOSTS
    override = getattr(args, "root", None)
    raw_limit = getattr(args, "limit", None)
    limit = 50 if raw_limit is None else raw_limit
    if override is not None and len(hosts) != 1:
        raise ValueError("--root applies to exactly one --host")
    results = []
    for host in hosts:
        root = Path(override) if override is not None else default_child_artifact_root(host)
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
            unverified = (
                f"  [unverified v6: {child['verification_reason']}]"
                if child["v6"] and not child["verified_delivery"]
                else ""
            )
            print(f"  {child['child_id']}  {slugs}{marks}{legacy}{unverified}")
    return 0


def cmd_evidence_child_launches(args: argparse.Namespace) -> int:
    """Report one outcome per harness-spawned child launch.

    `evidence children` answers which children provably received a card, so it
    only reports artifacts carrying delivery evidence. This answers the prior
    question -- of the children the host actually spawned, how many were
    staffed, declined for a recorded reason, or left no record at all. Only the
    last group is an evidence gap, and it was previously indistinguishable from
    the other two.

    Read-only, like every projection here: it consumes no delivery capability
    and mints no receipt, so an outcome is a diagnostic and never delivery
    proof, which stays with the in-lifetime collector under ADR-0156.
    """

    hosts = (args.host,) if getattr(args, "host", None) else _HOSTS
    override = getattr(args, "root", None)
    if override is not None and len(hosts) != 1:
        raise ValueError("--root applies to exactly one --host")
    since = str(getattr(args, "since", None) or "")
    limit = getattr(args, "limit", None) or MAX_CHILD_LAUNCHES

    join = Store(getattr(args, "db", None)).child_launch_join_rows()
    decisions = join["decisions"]
    by_id = {row["id"]: row for row in decisions if row["id"]}
    by_query_hash: dict[tuple[str, str], dict[str, object]] = {}
    for row in decisions:
        by_query_hash.setdefault((row["session_id"], row["query_hash"]), row)

    def _by_fingerprint(session_id: str, launch_id: str, assignment_sha256: str):
        # The fingerprint is a digest over the parent trace too, which an
        # artifact never carries, so each candidate trace in the session is
        # tried. Bounded by the same scan that produced these rows.
        for row in decisions:
            if row["session_id"] != session_id or not row["context_fingerprint"]:
                continue
            expected = native_child_failure_context_fingerprint(
                host="claude",
                parent_session_id=session_id,
                parent_trace_id=row["trace_id"],
                launch_id=launch_id,
                task_sha256=assignment_sha256,
            )
            if row["context_fingerprint"].startswith(expected[:32]):
                return row
        return None

    results = []
    for host in hosts:
        root = Path(override) if override is not None else default_child_artifact_root(host)
        report = resolve_child_launch_outcomes(
            root,
            host=host,
            decision_by_id=by_id.get,
            decision_by_query_hash=lambda session, digest: by_query_hash.get((session, digest)),
            decision_by_fingerprint=_by_fingerprint,
            since=since,
            limit=limit,
        )
        report["decision_scan_truncated"] = join["scan_truncated"]
        results.append(report)

    if getattr(args, "json", False):
        _print_json({"hosts": results})
        return 0
    for report in results:
        _print_child_launch_report(report)
    return 0


def _print_child_launch_report(report: dict[str, Any]) -> None:
    """Print one host's launch outcomes, stating every bound it was read under."""

    if not report["root_present"]:
        print(f"{report['host']}: artifact root is absent at {report['root']}")
        return
    counts = report["counts"]
    window = f" since {report['since']}" if report["since"] else ""
    print(
        f"{report['host']}: {report['launches_seen']} child launches{window} -- "
        f"{counts['staffed']} staffed, {counts['declined']} declined, "
        f"{counts['unrecorded']} with no record"
    )
    if report["launches_out_of_window"]:
        print(f"  {report['launches_out_of_window']} launch(es) fell before the window")
    if report["artifacts_unreadable"]:
        print(f"  {report['artifacts_unreadable']} artifact(s) could not be read")
    if report["scan_truncated"] or report["decision_scan_truncated"]:
        print("  scan truncated; these counts are a bounded sample, not full history")
    for item in report["launches"]:
        if item["outcome"] == "unrecorded":
            print(f"  no record: child {item['child_id']} launched {item['launched_at']}")
