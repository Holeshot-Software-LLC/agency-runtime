"""Roster, routing, policy, evaluation, and database commands."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypedDict

from agency_runtime.core.roster.sync import (
    activate_snapshot,
    approve_snapshot,
    create_roster_diff,
    download_from_source,
    quarantine_candidate,
    validate_agent,
)
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.selector.explain import explain_route
from agency_runtime.core.selector.policy import load_policy, validate_policy

from ._common import print_json, store


@dataclass(frozen=True, slots=True)
class RosterDependencies:
    """Patchable persistence and policy boundaries for roster commands."""

    store_factory: Callable[..., Any] = store
    emit_json: Callable[[Any], None] = print_json
    policy_loader: Callable[[], dict[str, Any]] = load_policy


DEFAULT_DEPENDENCIES = RosterDependencies()


class _PolicyActionSummary(TypedDict):
    """Roster availability for one policy action's declared specialists."""

    always_include: list[str]
    always_missing: list[str]
    always_disabled: list[str]
    conditional: list[str]
    conditional_missing: list[str]
    conditional_disabled: list[str]


class _PolicyDivisionSummary(TypedDict):
    """Roster availability for one division's declared specialists."""

    routes: list[str]
    missing: list[str]
    disabled: list[str]


# Local aliases keep the command bodies compact while the facade injects
# mutable test/process dependencies only where that compatibility is required.
_store = store
_print_json = print_json


def _reject_untrusted_auto_approve_sources(sources: list[dict[str, Any]]) -> bool:
    """Explain why automatic activation is unsafe for the selected sources."""
    untrusted = [
        source for source in sources if not int(source.get("trusted_for_auto_approve") or 0)
    ]
    if not untrusted:
        return False
    names = ", ".join(str(source.get("name") or source.get("url")) for source in untrusted)
    print(
        "Refusing --auto-approve because these sources are not trusted: " + names,
        file=sys.stderr,
    )
    print(
        "Mark an intended source with: agency source add <url> --trusted-for-auto-approve",
        file=sys.stderr,
    )
    return True


def _download_sync_candidates(
    source: dict[str, Any],
    errors: list[dict[str, str]],
) -> list[dict[str, Any]] | None:
    """Download one source while converting source failures to CLI diagnostics."""
    try:
        candidates = download_from_source(source["url"])
    except Exception as exc:
        errors.append({"source": source["url"], "error": str(exc)})
        return None
    if not candidates:
        errors.append({"source": source["url"], "error": "source returned zero candidates"})
        return None
    return candidates


def _collect_sync_candidates(
    sources: list[dict[str, Any]],
    runtime_store: Any,
    *,
    dry_run: bool,
) -> tuple[list[str], list[dict[str, str]]]:
    """Validate and optionally quarantine candidates from all enabled sources."""
    quarantined: list[str] = []
    errors: list[dict[str, str]] = []
    for source in sources:
        candidates = _download_sync_candidates(source, errors)
        if candidates is None:
            continue
        for agent in candidates:
            ok, reason = validate_agent(agent)
            if not ok:
                errors.append(
                    {
                        "source": source["url"],
                        "agent": agent.get("slug", ""),
                        "error": reason,
                    }
                )
                continue
            candidate = (
                agent["slug"]
                if dry_run
                else quarantine_candidate(agent, source["id"], runtime_store)
            )
            quarantined.append(candidate)
    return quarantined, errors


def _auto_approve_preflight(
    *,
    auto_approve: bool,
    quarantined: list[str],
    errors: list[dict[str, str]],
) -> int | None:
    """Fail closed before creating an automatically activated snapshot."""
    if not auto_approve:
        return None
    if errors:
        _print_json({"errors": errors})
        return 2
    if not quarantined:
        print(
            "Refusing --auto-approve because no candidates were quarantined",
            file=sys.stderr,
        )
        return 1
    return None


def _complete_sync(
    args: argparse.Namespace,
    runtime_store: Any,
    quarantined: list[str],
    errors: list[dict[str, str]],
) -> int:
    """Create and optionally activate the reviewed roster snapshot."""
    diff = create_roster_diff(runtime_store, candidate_ids=quarantined)
    if args.review:
        _print_json(diff["diff"])
    if args.auto_approve:
        approve_snapshot(runtime_store, diff["snapshot_id"])
        activate_snapshot(runtime_store, diff["snapshot_id"])
        _print_json(
            {
                "snapshot_id": diff["snapshot_id"],
                "activated": True,
                "candidate_count": len(quarantined),
                "diff": diff["diff"],
            }
        )
    else:
        print(f"Created snapshot {diff['snapshot_id']} from {len(quarantined)} candidates")
        print("Approve with: agency roster approve " + diff["snapshot_id"])
    if errors:
        _print_json({"errors": errors})
        return 2
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    runtime_store = _store()
    sources = runtime_store.list_agent_sources()
    if not sources:
        print(
            "No enabled sources configured. Add one with: agency source add <url>",
            file=sys.stderr,
        )
        return 1
    if args.auto_approve and _reject_untrusted_auto_approve_sources(sources):
        return 1
    quarantined, errors = _collect_sync_candidates(
        sources,
        runtime_store,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        _print_json({"dry_run": True, "valid_candidates": quarantined, "errors": errors})
        return 0 if not errors else 2
    preflight_exit = _auto_approve_preflight(
        auto_approve=args.auto_approve,
        quarantined=quarantined,
        errors=errors,
    )
    if preflight_exit is not None:
        return preflight_exit
    return _complete_sync(args, runtime_store, quarantined, errors)


def cmd_source_add(args: argparse.Namespace) -> int:
    source_id = _store().add_agent_source(
        args.url,
        args.name or args.url,
        trusted_for_auto_approve=args.trusted_for_auto_approve,
    )
    print(source_id)
    return 0


def cmd_source_list(args: argparse.Namespace) -> int:
    del args
    _print_json(_store().list_agent_sources())
    return 0


def cmd_roster_list(args: argparse.Namespace) -> int:
    del args
    roster = _store().get_active_roster_as_catalog()
    for agent in roster:
        print(
            f"{agent['slug']}\t{agent.get('name', '')}\t{agent.get('division', '')}\t{agent.get('description', '')}"
        )
    return 0


def cmd_roster_diff(args: argparse.Namespace) -> int:
    diff = create_roster_diff(_store())
    _print_json(diff if args.json else diff["diff"])
    return 0


def cmd_roster_approve(args: argparse.Namespace) -> int:
    approve_snapshot(_store(), args.snapshot_id)
    print(f"Approved snapshot {args.snapshot_id}")
    return 0


def cmd_roster_activate(args: argparse.Namespace) -> int:
    activate_snapshot(_store(), args.snapshot_id)
    print(f"Activated snapshot {args.snapshot_id}")
    return 0


def _search(query: str, limit: int) -> list[dict[str, Any]]:
    catalog = _store().get_active_roster_as_catalog()
    candidates, scores = pre_narrow(query, catalog, limit=limit)
    return [{**agent, "score": score} for agent, score in zip(candidates, scores, strict=True)]


def cmd_search(args: argparse.Namespace) -> int:
    results = _search(args.query, args.limit)
    if args.json:
        _print_json(results)
    else:
        for agent in results:
            print(
                f"{agent['score']:.1f}\t{agent['slug']}\t{agent.get('name', '')}\t{agent.get('description', '')}"
            )
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    from agency_runtime.core.selector.candidate_narrow import pre_narrow
    from agency_runtime.core.selector.pipeline import route

    store = _store()
    catalog = store.get_active_roster_as_catalog()
    if not catalog:
        print("No active agents available", file=sys.stderr)
        return 1
    routing = route("cli", args.task, catalog, store=store)
    candidates, scores = pre_narrow(args.task, catalog, limit=args.limit)
    candidate_rows = [
        {**candidate, "score": round(float(score), 4)}
        for candidate, score in zip(candidates, scores, strict=True)
    ]
    if args.json:
        _print_json(
            {
                "task": args.task,
                "routing": routing,
                "candidates": candidate_rows,
            }
        )
    else:
        selected = routing.get("selected_ids") or []
        if selected:
            print(f"selected: {', '.join(selected)}")
        else:
            print(f"selected: none (status={routing.get('status', 'unknown')})")
        print(
            f"confidence={float(routing.get('confidence', 0.0)):.3f} "
            f"source={routing.get('provider', 'deterministic')} "
            f"trace={routing.get('trace_id', '')}"
        )
        for agent in candidate_rows:
            print(f"candidate: {agent['slug']} score={agent['score']:.3f}")
        if routing.get("companion_actions"):
            print(f"companion actions: {', '.join(routing['companion_actions'])}")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    store = _store()
    payload = explain_route(
        args.session_id,
        args.task,
        store.get_active_roster_as_catalog(),
        limit=args.limit,
        store=store,
    )
    _print_json(payload)
    return 0


def _policy_mapping(policy: dict[str, Any], key: str) -> dict[Any, Any]:
    """Return one policy mapping, leaving validation to the policy validator."""
    value = policy.get(key, {})
    return value if isinstance(value, dict) else {}


def _active_roster_slugs(catalog: list[dict[str, Any]]) -> set[str]:
    """Collect canonical slugs from either supported catalog projection."""
    return {
        str(agent.get("slug") or agent.get("agent_slug"))
        for agent in catalog
        if agent.get("slug") or agent.get("agent_slug")
    }


def _declared_policy_slugs(routes: Any) -> list[str]:
    """Extract valid slug declarations while preserving their policy order."""
    return [
        str(route.get("slug"))
        for route in (routes or [])
        if isinstance(route, dict) and route.get("slug")
    ]


def _empty_action_summary() -> _PolicyActionSummary:
    return {
        "always_include": [],
        "always_missing": [],
        "always_disabled": [],
        "conditional": [],
        "conditional_missing": [],
        "conditional_disabled": [],
    }


def _summarize_policy_actions(
    actions: dict[Any, Any],
    missing_enabled: set[str],
    disabled_slugs: set[str],
) -> dict[str, _PolicyActionSummary]:
    """Project policy actions into the stable CLI availability schema."""
    summaries: dict[str, _PolicyActionSummary] = {}
    for action, data in actions.items():
        if not isinstance(data, dict):
            summaries[str(action)] = _empty_action_summary()
            continue

        always = _declared_policy_slugs(data.get("always_include"))
        conditional = _declared_policy_slugs(data.get("conditional"))
        summaries[str(action)] = {
            "always_include": always,
            "always_missing": [slug for slug in always if slug in missing_enabled],
            "always_disabled": [slug for slug in always if slug in disabled_slugs],
            "conditional": conditional,
            "conditional_missing": [slug for slug in conditional if slug in missing_enabled],
            "conditional_disabled": [slug for slug in conditional if slug in disabled_slugs],
        }
    return summaries


def _summarize_policy_divisions(
    routes: list[dict[str, Any]],
    missing_enabled: set[str],
    disabled_slugs: set[str],
) -> dict[str, _PolicyDivisionSummary]:
    """Group validated division routes into the stable CLI schema."""
    summaries: dict[str, _PolicyDivisionSummary] = {}
    for route in routes:
        if route["source"] != "division":
            continue
        division = summaries.setdefault(
            route["group"],
            {"routes": [], "missing": [], "disabled": []},
        )
        slug = route["slug"]
        division["routes"].append(slug)
        if slug in missing_enabled:
            division["missing"].append(slug)
        if slug in disabled_slugs:
            division["disabled"].append(slug)
    return summaries


def _policy_json_summary(
    *,
    actions: dict[Any, Any],
    divisions: dict[Any, Any],
    active_slugs: set[str],
    validation: dict[str, Any],
    action_summary: dict[str, _PolicyActionSummary],
    division_summary: dict[str, _PolicyDivisionSummary],
) -> dict[str, Any]:
    """Build the compatibility-stable machine-readable policy response."""
    summary: dict[str, Any] = {
        "action_count": len(actions),
        "division_count": len(divisions),
        "roster_count": len(active_slugs),
        "valid": validation["valid"],
        "errors": validation["errors"],
        "availability_mode": validation["mode"],
        "route_count": validation["route_count"],
        "unique_policy_slugs": validation["unique_policy_slugs"],
        "enabled_slugs": validation["enabled_slugs"],
        "missing_enabled": validation["missing_enabled"],
        "disabled_count": validation["disabled_count"],
        "disabled_routes": validation["disabled_routes"],
        "actions": action_summary,
        "division_anchors": division_summary,
    }
    # Compatibility alias: only required enabled specialists count as missing;
    # intentionally roster-gated routes are reported separately.
    summary["all_missing"] = validation["missing_enabled"]
    return summary


def _print_policy_action(action: str, summary: _PolicyActionSummary) -> None:
    """Render one action's human-readable availability breakdown."""
    action_missing = summary["always_missing"] + summary["conditional_missing"]
    status = "✅" if not action_missing else "❌"
    print(f"{status} {action}")

    always = summary["always_include"]
    print(f"   always_include ({len(always)}): {', '.join(always)}")
    if summary["always_missing"]:
        print("   ❌ enabled but missing: " + ", ".join(summary["always_missing"]))
    if summary["always_disabled"]:
        disabled = summary["always_disabled"]
        print(
            f"   roster-gated and disabled ({len(disabled)}): "
            + ", ".join(disabled[:8])
            + ("…" if len(disabled) > 8 else "")
        )

    conditional = summary["conditional"]
    print(
        f"   conditional ({len(conditional)}): "
        f"{', '.join(conditional[:8])}{'…' if len(conditional) > 8 else ''}"
    )
    if summary["conditional_missing"]:
        print("   ❌ enabled conditional missing: " + ", ".join(summary["conditional_missing"]))
    if summary["conditional_disabled"]:
        disabled = summary["conditional_disabled"]
        print(
            f"   roster-gated conditionals ({len(disabled)}): "
            + ", ".join(disabled[:8])
            + ("…" if len(disabled) > 8 else "")
        )


def _print_policy_report(
    *,
    actions: dict[Any, Any],
    divisions: dict[Any, Any],
    active_slugs: set[str],
    validation: dict[str, Any],
    action_summary: dict[str, _PolicyActionSummary],
) -> None:
    """Render the complete human-readable policy report."""
    print(
        f"Companion policy: {len(actions)} broad actions, {len(divisions)} "
        f"division anchors, {validation['route_count']} routes, "
        f"{len(active_slugs)} active roster agents"
    )
    marker = "✅ VALID" if validation["valid"] else "❌ INVALID"
    print(
        f"{marker}: {len(validation['enabled_slugs'])} enabled, "
        f"{validation['disabled_count']} roster-gated and currently disabled"
    )
    for error in validation["errors"]:
        print(f"   ❌ {error}")
    print()
    for action, summary in sorted(action_summary.items()):
        _print_policy_action(action, summary)


def cmd_policy(
    args: argparse.Namespace,
    *,
    dependencies: RosterDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Show the active companion policy and validate coverage against the roster."""
    policy = dependencies.policy_loader()
    actions = _policy_mapping(policy, "actions")
    divisions = _policy_mapping(policy, "division_anchors")
    catalog = dependencies.store_factory().get_active_roster_as_catalog()
    active_slugs = _active_roster_slugs(catalog)
    validation = validate_policy(policy, active_slugs)
    missing_enabled = set(validation["missing_enabled"])
    disabled_slugs = {str(item["slug"]) for item in validation["disabled_routes"]}
    action_summary = _summarize_policy_actions(
        actions,
        missing_enabled,
        disabled_slugs,
    )
    division_summary = _summarize_policy_divisions(
        validation["routes"],
        missing_enabled,
        disabled_slugs,
    )

    if args.json:
        dependencies.emit_json(
            _policy_json_summary(
                actions=actions,
                divisions=divisions,
                active_slugs=active_slugs,
                validation=validation,
                action_summary=action_summary,
                division_summary=division_summary,
            )
        )
    else:
        _print_policy_report(
            actions=actions,
            divisions=divisions,
            active_slugs=active_slugs,
            validation=validation,
            action_summary=action_summary,
        )
    return 0 if validation["valid"] else 1


def cmd_eval_delegation(args: argparse.Namespace) -> int:
    from agency_runtime.core.evals.delegation import run_delegation_eval

    report = run_delegation_eval()
    if args.json:
        _print_json(report)
    else:
        status = "passed" if report["passed"] else "failed"
        print(
            f"delegation eval {status}: {report['passed_count']} passed, {report['failed_count']} failed"
        )
        for case in report["cases"]:
            marker = "ok" if case["passed"] else "FAIL"
            detail = case.get("error") or case.get("detail") or ""
            print(f"{marker}\t{case['name']}\t{detail}")
    return 0 if report["passed"] else 1


def cmd_eval_routing(args: argparse.Namespace) -> int:
    """Run the versioned routing, policy, delegation, and latency gates."""
    from agency_runtime.core.evals.routing import run_routing_eval

    report = run_routing_eval(include_details=not args.no_details)
    if args.json:
        _print_json(report)
    else:
        status = "passed" if report["passed"] else "failed"
        corpus = report["corpus"]
        print(
            f"routing eval {status}: corpus={corpus['version']} "
            f"routing={corpus['routing_cases']} policy={corpus['policy_cases']} "
            f"delegation={corpus['delegation_cases']}"
        )
        for gate in report["gates"]:
            marker = "ok" if gate["passed"] else "FAIL"
            print(
                f"{marker}\t{gate['area']}.{gate['metric']}="
                f"{gate['value']} {gate['operator']} {gate['threshold']}"
            )
    return 0 if report["passed"] else 1


def cmd_smoke(args: argparse.Namespace) -> int:
    from agency_runtime.core.smoke import run_smoke

    report = run_smoke(all_hosts=args.all)
    if args.json:
        _print_json(report)
    else:
        status = "passed" if report["passed"] else "failed"
        print(
            f"smoke {status}: {report['passed_count']} passed, {report['failed_count']} failed, {report['skipped_count']} skipped"
        )
        for check in report["checks"]:
            marker = {"pass": "ok", "skip": "skip", "fail": "FAIL"}.get(
                check["status"], check["status"]
            )
            detail = check.get("error") or check.get("detail") or ""
            print(f"{marker}\t{check['name']}\t{detail}")
    return 0 if report["passed"] else 1


def cmd_db_stats(args: argparse.Namespace) -> int:
    stats = _store().database_stats()
    if args.json:
        _print_json(stats)
    else:
        print(f"DB: {stats['db_path']}")
        print(
            f"Size: {stats['db_size_bytes']} bytes (wal={stats['wal_size_bytes']}, shm={stats['shm_size_bytes']})"
        )
        for table, count in stats["tables"].items():
            print(f"{table}\t{count}")
    return 0


def cmd_db_trim(args: argparse.Namespace) -> int:
    report = _store().trim_runtime_tables(
        older_than_days=args.older_than_days,
        keep_last=args.keep_last,
        dry_run=args.dry_run,
        vacuum=not args.no_vacuum,
    )
    if args.json:
        _print_json(report)
    else:
        mode = "DRY RUN " if report["dry_run"] else ""
        print(f"{mode}Trimmed Agency Runtime DB: {report['db_path']}")
        print(f"Size: {report['db_size_before_bytes']} -> {report['db_size_after_bytes']} bytes")
        for table, detail in report["tables"].items():
            deleted = int(detail.get("deleted", 0))
            if deleted:
                print(f"{table}\tdeleted={deleted}")
        if not any(int(detail.get("deleted", 0)) for detail in report["tables"].values()):
            print("No rows matched the retention policy.")
    return 0
