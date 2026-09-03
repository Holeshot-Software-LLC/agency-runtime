"""Roster, routing, policy, evaluation, and database commands."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, TypedDict

from agency_runtime.core.agent_activation import (
    PROTECTED_AGENT_SLUGS,
    agent_is_enabled,
    normalize_agent_slug,
    updated_disabled_agents,
)
from agency_runtime.core.agent_identity import agent_identity
from agency_runtime.core.config import load_config
from agency_runtime.core.configuration import (
    apply_config_operations,
    read_config_state,
    resolve_config_path,
)
from agency_runtime.core.display import safe_display_token
from agency_runtime.core.roster.inference import (
    InferenceAuditPolicy,
    audit_candidates_with_policy,
    resolve_inference_audit_policy,
)
from agency_runtime.core.roster.lifecycle import (
    import_upstream_source,
    inspect_upstream_source,
)
from agency_runtime.core.roster.review import (
    candidate_comparison,
    list_candidate_audits,
    reject_candidate,
    run_candidate_audit,
)
from agency_runtime.core.roster.source_identity import SourceIdentityError
from agency_runtime.core.roster.sync import (
    RosterSyncError,
    activate_snapshot,
    approve_snapshot,
    create_retirement_diff,
    create_roster_diff,
    download_from_source,
    list_source_scans,
    quarantine_candidate,
    quarantine_manifest_import,
    reconcile_manifest_remediation_resolutions,
    remediation_queue_snapshot,
    validate_agent,
)
from agency_runtime.core.routing_snapshot import (
    RoutingSnapshot,
    bind_workforce_snapshot,
    capture_operational_routing_snapshot,
    capture_routing_snapshot,
)
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.selector.explain import explain_route
from agency_runtime.core.selector.policy import (
    load_policy,
    policy_path_for_config,
    validate_policy,
)

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


@dataclass(frozen=True, slots=True)
class _RoutingOperation:
    """Either one direct selector snapshot or one brokered explanation receipt."""

    store: Any | None
    snapshot: RoutingSnapshot | None
    receipt: dict[str, Any] | None


# Local aliases keep the command bodies compact while the facade injects
# mutable test/process dependencies only where that compatibility is required.
_store = store
_print_json = print_json


def _runtime_enabled() -> bool:
    """Read the durable master switch before any Store or routing work."""

    from agency_runtime.core.runtime_control import master_enabled

    return master_enabled()


def _bypassed_routing(*, trace_id: str = "") -> dict[str, Any]:
    """Return the stable CLI routing projection while Agency is off."""

    return {
        "runtime_enabled": False,
        "bypassed": True,
        "trace_id": trace_id,
        "selected_ids": [],
        "semantic_ids": [],
        "confidence": 0.0,
        "latency_ms": 0,
        "status": "bypassed",
        "source": "master_control",
        "provider": "master_control",
        "work_units": {
            "count": 0,
            "confidence": "none",
            "source": "master_control",
            "units": [],
            "delegate": False,
        },
    }


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
    if not candidates and not getattr(candidates, "outcomes", ()):
        errors.append({"source": source["url"], "error": "source returned zero candidates"})
        return None
    return candidates


def _quarantine_manifest_with_policy(
    candidates: list[dict[str, Any]],
    outcomes: list[Any],
    source_id: str,
    runtime_store: Any,
    audit_policy: InferenceAuditPolicy | None,
) -> tuple[list[str], list[dict[str, str]], bool]:
    if audit_policy is None:
        candidate_ids, persisted = quarantine_manifest_import(
            candidates,
            outcomes,
            source_id,
            runtime_store,
        )
        return candidate_ids, persisted, True
    candidate_ids, persisted = quarantine_manifest_import(
        candidates,
        outcomes,
        source_id,
        runtime_store,
        require_inference=audit_policy.required,
    )
    audits = audit_candidates_with_policy(runtime_store, candidate_ids, audit_policy)
    scan_ids = {str(outcome.get("scan_id") or "") for outcome in persisted}
    if len(scan_ids) != 1 or not next(iter(scan_ids)):
        raise RosterSyncError("manifest import did not return one source scan receipt")
    reconcile_manifest_remediation_resolutions(
        candidates,
        outcomes,
        source_id,
        runtime_store,
        candidate_ids=candidate_ids,
        audits=audits,
        scan_id=next(iter(scan_ids)),
    )
    return candidate_ids, persisted, all(audit["verdict"] == "passed" for audit in audits)


def _quarantine_agent_with_policy(
    agent: dict[str, Any],
    source_id: str,
    runtime_store: Any,
    audit_policy: InferenceAuditPolicy | None,
) -> tuple[str, bool]:
    if audit_policy is None:
        return quarantine_candidate(agent, source_id, runtime_store), True
    candidate_id = quarantine_candidate(
        agent,
        source_id,
        runtime_store,
        require_inference=audit_policy.required,
    )
    audit = audit_candidates_with_policy(runtime_store, [candidate_id], audit_policy)[0]
    return candidate_id, audit["verdict"] == "passed"


def _collect_sync_candidates(
    sources: list[dict[str, Any]],
    runtime_store: Any,
    *,
    dry_run: bool,
    outcome_sink: list[dict[str, str]] | None = None,
    audit_policy: InferenceAuditPolicy | None = None,
) -> tuple[list[str], list[dict[str, str]]]:
    """Validate and optionally quarantine candidates from all enabled sources."""
    quarantined: list[str] = []
    errors: list[dict[str, str]] = []
    outcomes = outcome_sink if outcome_sink is not None else []
    for source in sources:
        candidates = _download_sync_candidates(source, errors)
        if candidates is None:
            continue
        manifest_outcomes = list(getattr(candidates, "outcomes", ()))
        if manifest_outcomes and not dry_run:
            try:
                candidate_ids, persisted_outcomes, audit_ready = _quarantine_manifest_with_policy(
                    candidates,
                    manifest_outcomes,
                    source["id"],
                    runtime_store,
                    audit_policy,
                )
            except Exception as exc:
                errors.append({"source": source["url"], "error": str(exc)})
                continue
            if not audit_ready:
                errors.append(
                    {
                        "source": source["url"],
                        "error": "candidate inference audit is degraded or failed",
                    }
                )
            quarantined.extend(candidate_ids)
            outcomes.extend(persisted_outcomes)
            continue
        if manifest_outcomes:
            outcomes.extend(outcome.public_dict() for outcome in manifest_outcomes)
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
            try:
                if dry_run:
                    candidate, audit_ready = agent["slug"], True
                else:
                    candidate, audit_ready = _quarantine_agent_with_policy(
                        agent,
                        source["id"],
                        runtime_store,
                        audit_policy,
                    )
            except Exception as exc:
                errors.append(
                    {
                        "source": source["url"],
                        "agent": agent.get("slug", ""),
                        "error": str(exc),
                    }
                )
                continue
            quarantined.append(candidate)
            if not audit_ready:
                errors.append(
                    {
                        "source": source["url"],
                        "agent": agent.get("slug", ""),
                        "error": "candidate inference audit is degraded or failed",
                    }
                )
    return quarantined, errors


def _auto_approve_preflight(
    *,
    auto_approve: bool,
    quarantined: list[str],
    errors: list[dict[str, str]],
    outcomes: list[dict[str, str]] | None = None,
) -> int | None:
    """Fail closed before creating an automatically activated snapshot."""
    if not auto_approve:
        return None
    if errors:
        _print_json({"errors": errors})
        return 2
    rejected_outcomes = [
        dict(outcome)
        for outcome in (outcomes or [])
        if str(outcome.get("status") or "") != "candidate"
    ]
    if rejected_outcomes:
        _print_json(
            {
                "errors": [
                    {
                        "error": (
                            "automatic approval requires a complete manifest scan; "
                            "review quarantined or ignored entries first"
                        )
                    }
                ],
                "outcomes": rejected_outcomes,
            }
        )
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
    outcomes: list[dict[str, str]] | None = None,
    *,
    require_inference: bool = False,
) -> int:
    """Create and optionally activate the reviewed roster snapshot."""
    resolved_outcomes = outcomes or []
    diff = create_roster_diff(runtime_store, candidate_ids=quarantined)
    if args.review:
        _print_json(diff["diff"])
    if args.auto_approve:
        if require_inference:
            approve_snapshot(
                runtime_store,
                diff["snapshot_id"],
                require_inference=True,
            )
            activate_snapshot(
                runtime_store,
                diff["snapshot_id"],
                require_inference=True,
            )
        else:
            approve_snapshot(runtime_store, diff["snapshot_id"])
            activate_snapshot(runtime_store, diff["snapshot_id"])
        _print_json(
            {
                "snapshot_id": diff["snapshot_id"],
                "activated": True,
                "candidate_count": len(quarantined),
                "diff": diff["diff"],
                "outcomes": resolved_outcomes,
            }
        )
    else:
        print(f"Created snapshot {diff['snapshot_id']} from {len(quarantined)} candidates")
        print("Approve with: agency roster approve " + diff["snapshot_id"])
        if resolved_outcomes:
            _print_json({"outcomes": resolved_outcomes})
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
    audit_policy = resolve_inference_audit_policy(load_config())
    outcomes: list[dict[str, str]] = []
    quarantined, errors = _collect_sync_candidates(
        sources,
        runtime_store,
        dry_run=args.dry_run,
        outcome_sink=outcomes,
        audit_policy=audit_policy,
    )
    if args.dry_run:
        _print_json(
            {
                "dry_run": True,
                "valid_candidates": quarantined,
                "errors": errors,
                "outcomes": outcomes,
            }
        )
        return 0 if not errors else 2
    preflight_exit = _auto_approve_preflight(
        auto_approve=args.auto_approve,
        quarantined=quarantined,
        errors=errors,
        outcomes=outcomes,
    )
    if preflight_exit is not None:
        return preflight_exit
    return _complete_sync(
        args,
        runtime_store,
        quarantined,
        errors,
        outcomes,
        require_inference=audit_policy.required,
    )


def cmd_source_add(args: argparse.Namespace) -> int:
    try:
        source_id = _store().add_agent_source(
            args.url,
            args.name or args.url,
            trusted_for_auto_approve=args.trusted_for_auto_approve,
        )
    except SourceIdentityError as exc:
        print(f"Refusing roster source: {exc}", file=sys.stderr)
        return 1
    print(source_id)
    return 0


def cmd_source_list(args: argparse.Namespace) -> int:
    del args
    try:
        sources = _store().list_agent_sources()
    except SourceIdentityError as exc:
        print(f"Refusing stored roster sources: {exc}", file=sys.stderr)
        return 1
    _print_json(sources)
    return 0


def cmd_roster_list(args: argparse.Namespace) -> int:
    del args
    _path, roster = _activation_rows()
    for agent in roster:
        if not agent["enabled"]:
            continue
        print(f"{agent['slug']}\t{agent.get('name', '')}\t{agent.get('division', '')}")
    return 0


def cmd_roster_diff(args: argparse.Namespace) -> int:
    diff = create_roster_diff(_store())
    _print_json(diff if args.json else diff["diff"])
    return 0


def cmd_roster_approve(args: argparse.Namespace) -> int:
    policy = resolve_inference_audit_policy(load_config())
    approve_snapshot(
        _store(),
        args.snapshot_id,
        require_inference=policy.required,
    )
    print(f"Approved snapshot {args.snapshot_id}")
    return 0


def cmd_roster_activate(args: argparse.Namespace) -> int:
    policy = resolve_inference_audit_policy(load_config())
    activate_snapshot(
        _store(),
        args.snapshot_id,
        require_inference=policy.required,
    )
    print(f"Activated snapshot {args.snapshot_id}")
    return 0


def cmd_roster_scans(args: argparse.Namespace) -> int:
    """List immutable full/partial scan evidence used by retirement review."""

    scans = list_source_scans(_store(), limit=args.limit)
    _print_json(scans)
    return 0


def cmd_roster_remediation_queue(args: argparse.Namespace) -> int:
    """List bounded non-executable repair attempts without source prompt content."""

    _print_json(
        remediation_queue_snapshot(
            _store(),
            limit=args.limit,
            pending_cursor=args.pending_cursor,
            history_cursor=args.history_cursor,
        )
    )
    return 0


def cmd_roster_retire(args: argparse.Namespace) -> int:
    """Create, but do not approve, one explicit evidence-backed retirement."""

    snapshot = create_retirement_diff(
        _store(),
        scan_id=args.scan_id,
        slugs=[args.slug],
    )
    if args.json:
        _print_json({"snapshot_id": snapshot["snapshot_id"], "diff": snapshot["diff"]})
    else:
        print(f"Created retirement snapshot {snapshot['snapshot_id']}")
        print("Approve with: agency roster approve " + snapshot["snapshot_id"])
    return 0


def cmd_roster_rollback(args: argparse.Namespace) -> int:
    """Invoke the Store-owned native-presence rollback coordinator."""

    restored = _store().rollback_agent_revision(
        args.slug,
        args.target_version,
        expected_current_version=args.expected_current_version,
        expected_current_hash=args.expected_current_hash,
    )
    if args.json:
        _print_json(restored)
    else:
        print(f"Rolled back {restored['agent_slug']} to {restored['version']} ({restored['hash']})")
    return 0


def _upstream_sources(runtime_store: Any, source_id: str) -> list[dict[str, Any]]:
    sources = runtime_store.list_agent_sources()
    if not source_id:
        return sources
    selected = [source for source in sources if str(source.get("id") or "") == source_id]
    if not selected:
        raise ValueError(f"enabled roster source not found: {safe_display_token(source_id)}")
    return selected


def cmd_roster_upstream_status(args: argparse.Namespace) -> int:
    """Compare configured upstream sources with the packaged audited baseline."""

    runtime_store = _store()
    try:
        sources = _upstream_sources(runtime_store, args.source_id)
    except ValueError as exc:
        _print_json({"ok": False, "errors": [{"error": str(exc)}], "sources": []})
        return 1
    reports: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for source in sources:
        try:
            report = inspect_upstream_source(
                str(source["url"]),
                source_revision=args.source_revision,
            ).public_dict()
            reports.append({"source_id": source["id"], "source": source["url"], **report})
        except Exception as exc:
            errors.append({"source_id": str(source.get("id") or ""), "error": str(exc)})
    _print_json({"ok": not errors, "sources": reports, "errors": errors})
    return 0 if not errors else 2


def cmd_roster_upstream_import(args: argparse.Namespace) -> int:
    """Import only upstream deltas into quarantine; never approve or activate."""

    runtime_store = _store()
    try:
        sources = _upstream_sources(runtime_store, args.source_id)
    except ValueError as exc:
        _print_json({"ok": False, "errors": [{"error": str(exc)}], "sources": []})
        return 1
    reports: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    config = load_config()
    for source in sources:
        try:
            report = import_upstream_source(
                runtime_store,
                config=config,
                source_id=str(source["id"]),
                source_url=str(source["url"]),
                source_revision=args.source_revision,
                dry_run=args.dry_run,
            )
            reports.append({"source_id": source["id"], "source": source["url"], **report})
            if not args.dry_run and report.get("audit_ready") is False:
                errors.append(
                    {
                        "source_id": str(source.get("id") or ""),
                        "error": "configured candidate inference audit is degraded or failed",
                    }
                )
        except Exception as exc:
            errors.append({"source_id": str(source.get("id") or ""), "error": str(exc)})
    _print_json(
        {
            "ok": not errors,
            "dry_run": bool(args.dry_run),
            "approval_performed": False,
            "activation_performed": False,
            "sources": reports,
            "errors": errors,
        }
    )
    return 0 if not errors else 2


def cmd_roster_candidate_audit(args: argparse.Namespace) -> int:
    """Run deterministic and automatically configured inference audit stages."""

    try:
        policy = resolve_inference_audit_policy(
            load_config(),
            force_required=args.require_inference,
        )
        report = run_candidate_audit(
            _store(),
            args.candidate_id,
            inference_assistant=policy.assistant,
            require_inference=policy.required,
        )
    except Exception as exc:
        _print_json({"ok": False, "error": str(exc)})
        return 1
    _print_json(
        {
            "ok": report["verdict"] == "passed",
            "inference_policy": policy.public_dict(),
            "audit": report,
        }
    )
    return 0 if report["verdict"] == "passed" else 2


def cmd_roster_candidate_findings(args: argparse.Namespace) -> int:
    try:
        audits = list_candidate_audits(_store(), args.candidate_id, limit=args.limit)
    except Exception as exc:
        _print_json({"ok": False, "error": str(exc), "audits": []})
        return 1
    _print_json({"ok": True, "candidate_id": args.candidate_id, "audits": audits})
    return 0


def cmd_roster_candidate_reject(args: argparse.Namespace) -> int:
    try:
        comparison = reject_candidate(_store(), args.candidate_id, reason=args.reason)
    except Exception as exc:
        _print_json({"ok": False, "error": str(exc)})
        return 1
    _print_json({"ok": True, "comparison": comparison})
    return 0


def cmd_roster_candidate_compare(args: argparse.Namespace) -> int:
    try:
        comparison = candidate_comparison(_store(), args.candidate_id)
    except Exception as exc:
        _print_json({"ok": False, "error": str(exc)})
        return 1
    _print_json({"ok": True, "comparison": comparison})
    return 0


def _activation_store(config_argument: object) -> Any:
    """Open the roster bound to an explicit config, or use the shared default."""

    if config_argument is None:
        return _store()
    path = resolve_config_path(str(config_argument))
    return _store(load_config(path=path, reload=True))


def _activation_rows(
    config_argument: object = None,
    *,
    store_factory: Callable[[], Any] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Project preserved roster definitions with their effective policy state."""

    from agency_runtime.core.windows_acl import require_restricted_windows_token

    try:
        path = resolve_config_path(None if config_argument is None else str(config_argument))
        state = read_config_state(path)
        effective = state.effective.get("agents", {})
        disabled = (
            frozenset(effective.get("disabled", [])) if isinstance(effective, dict) else frozenset()
        )
        rows = [
            {
                "slug": agent["agent_slug"],
                "name": agent.get("name", ""),
                "division": agent.get("division", ""),
                "enabled": agent_is_enabled(agent["agent_slug"], disabled),
                "protected": agent["agent_slug"] in PROTECTED_AGENT_SLUGS,
            }
            for agent in (
                _activation_store(config_argument) if store_factory is None else store_factory()
            ).get_active_roster()
        ]
        return str(path), rows
    except Exception as direct_error:
        require_restricted_windows_token(direct_error)
        if config_argument is not None:
            raise RuntimeError(
                "an explicit agent config cannot be redirected through the dashboard broker"
            ) from direct_error
        try:
            from agency_runtime.cli.agent_control_broker import broker_activation_rows

            broker_path, rows = broker_activation_rows()
            if not _same_config_path(broker_path, str(path)):
                raise ValueError("dashboard service config does not match the CLI config identity")
            return broker_path, rows
        except (OSError, RuntimeError, ValueError) as broker_error:
            raise RuntimeError(
                "agent activation state is inaccessible from this restricted process and the "
                f"dashboard service could not broker it: {broker_error}"
            ) from direct_error


def cmd_agents_list(args: argparse.Namespace) -> int:
    """List every preserved roster definition and its activation state."""

    try:
        config_path, rows = _activation_rows(getattr(args, "config", None))
    except RuntimeError as exc:
        message = safe_display_token(str(exc), limit=500)
        if args.json:
            _print_json({"ok": False, "exit_code": 1, "error": message, "agents": []})
        else:
            print(f"❌ {message}")
        return 1
    if args.json:
        _print_json({"config_path": config_path, "agents": rows})
    else:
        print(f"config\t{config_path}")
        for agent in rows:
            status = (
                "protected" if agent["protected"] else "enabled" if agent["enabled"] else "disabled"
            )
            print(f"{status}\t{agent['slug']}\t{agent['name']}\t{agent['division']}")
    return 0


def _set_agent_enabled(
    slug: object,
    *,
    enabled: bool,
    config_argument: object = None,
    reason: str = "operator activation toggle",
) -> tuple[str, bool, str]:
    """Atomically change one effective agent policy using config revision CAS."""

    from agency_runtime.core.windows_acl import require_restricted_windows_token

    try:
        normalized = normalize_agent_slug(slug)
        path = resolve_config_path(None if config_argument is None else str(config_argument))
        state = read_config_state(path)
        effective = state.effective.get("agents", {})
        disabled = effective.get("disabled", []) if isinstance(effective, dict) else []
        updated = updated_disabled_agents(disabled, normalized, enabled=enabled)
        runtime_store = _activation_store(config_argument)
        if runtime_store.get_roster_entry(normalized) is None:
            raise ValueError(f"agent is not present in the active roster: {normalized}")
        changed = tuple(disabled) != updated
        if changed:
            result = apply_config_operations(
                [{"op": "set", "path": "agents.disabled", "value": list(updated)}],
                expected_revision=state.revision,
                path=path,
            )
            with suppress(KeyError):
                runtime_store.record_workforce_enablement(
                    normalized,
                    enabled=enabled,
                    config_revision=result.state.revision,
                    reason=reason,
                    actor="operator",
                    surface="cli",
                )
        return normalized, changed, str(path)
    except Exception as direct_error:
        require_restricted_windows_token(direct_error)
        raise RuntimeError(
            "agent activation mutation is unavailable from a restricted model-facing process; "
            "use the owner-authenticated dashboard UI or run this command from a normal user shell"
        ) from direct_error


def cmd_agent_enable(args: argparse.Namespace) -> int:
    expected = f"ENABLE {normalize_agent_slug(args.slug)}"
    try:
        if getattr(args, "confirm", expected) != expected:
            raise ValueError(f'confirmation required: --confirm "{expected}"')
        slug, changed, config_path = _set_agent_enabled(
            args.slug,
            enabled=True,
            config_argument=getattr(args, "config", None),
            reason=str(getattr(args, "reason", "operator activation toggle")),
        )
    except (RuntimeError, ValueError) as exc:
        message = safe_display_token(str(exc), limit=500)
        if getattr(args, "json", False):
            _print_json({"ok": False, "error": message})
        else:
            print(f"❌ {message}")
        return 1
    if getattr(args, "json", False):
        _print_json(
            {
                "ok": True,
                "slug": slug,
                "enabled": True,
                "changed": changed,
                "config_path": config_path,
            }
        )
        return 0
    print(f"{slug} is {'enabled' if changed else 'already enabled'}")
    print(f"config\t{config_path}")
    return 0


def cmd_agent_disable(args: argparse.Namespace) -> int:
    expected = f"DISABLE {normalize_agent_slug(args.slug)}"
    try:
        if getattr(args, "confirm", expected) != expected:
            raise ValueError(f'confirmation required: --confirm "{expected}"')
        slug, changed, config_path = _set_agent_enabled(
            args.slug,
            enabled=False,
            config_argument=getattr(args, "config", None),
            reason=str(getattr(args, "reason", "operator activation toggle")),
        )
    except (RuntimeError, ValueError) as exc:
        message = safe_display_token(str(exc), limit=500)
        if getattr(args, "json", False):
            _print_json({"ok": False, "error": message})
        else:
            print(f"❌ {message}")
        return 1
    if getattr(args, "json", False):
        _print_json(
            {
                "ok": True,
                "slug": slug,
                "enabled": False,
                "changed": changed,
                "config_path": config_path,
            }
        )
        return 0
    print(f"{slug} is {'disabled' if changed else 'already disabled'}")
    print(f"config\t{config_path}")
    return 0


def _search(query: str, limit: int) -> list[dict[str, Any]]:
    from agency_runtime.core.windows_acl import require_restricted_windows_token

    try:
        snapshot = capture_routing_snapshot(_store())
        candidates, scores = pre_narrow(query, snapshot.catalog, limit=limit)
        return [{**agent, "score": score} for agent, score in zip(candidates, scores, strict=True)]
    except Exception as direct_error:
        require_restricted_windows_token(direct_error)
        try:
            from agency_runtime.cli.agent_control_broker import broker_search_agents

            path, results = broker_search_agents(query=query, limit=limit)
            intended_path = str(resolve_config_path())
            if path is not None and not _same_config_path(path, intended_path):
                raise ValueError("dashboard service config does not match the CLI config identity")
            return results
        except (OSError, RuntimeError, ValueError) as broker_error:
            raise RuntimeError(
                "selector state is inaccessible from this restricted process and the dashboard "
                f"service could not execute search: {broker_error}"
            ) from direct_error


def cmd_search(args: argparse.Namespace) -> int:
    if not _runtime_enabled():
        payload = {
            "runtime_enabled": False,
            "bypassed": True,
            "query": args.query,
            "agents": [],
            "count": 0,
        }
        if args.json:
            _print_json(payload)
        else:
            print("Agency Runtime is globally disabled; agent search was bypassed.")
        return 0

    try:
        results = _search(args.query, args.limit)
    except RuntimeError as exc:
        message = safe_display_token(str(exc), limit=500)
        if args.json:
            _print_json(
                {
                    "ok": False,
                    "exit_code": 1,
                    "error": message,
                    "query": args.query,
                    "agents": [],
                    "count": 0,
                }
            )
        else:
            print(f"❌ {message}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(results)
    else:
        for agent in results:
            print(
                f"{agent['score']:.1f}\t{agent['slug']}\t{agent.get('name', '')}\t{agent.get('description', '')}"
            )
    return 0


def _routing_operation(*, session_id: str, task: str, limit: int) -> _RoutingOperation:
    """Capture a direct snapshot or broker the whole operation after exact refusal."""

    from agency_runtime.core.windows_acl import require_restricted_windows_token

    try:
        runtime_store = _store()
        return _RoutingOperation(
            store=runtime_store,
            snapshot=capture_operational_routing_snapshot(runtime_store),
            receipt=None,
        )
    except Exception as direct_error:
        require_restricted_windows_token(direct_error)
        try:
            from agency_runtime.cli.agent_control_broker import broker_explain_selection

            path, receipt = broker_explain_selection(
                session_id=session_id,
                task=task,
                limit=limit,
            )
            intended_path = str(resolve_config_path())
            if path is not None and not _same_config_path(path, intended_path):
                raise ValueError("dashboard service config does not match the CLI config identity")
            return _RoutingOperation(store=None, snapshot=None, receipt=receipt)
        except (OSError, RuntimeError, ValueError) as broker_error:
            raise RuntimeError(
                "selector state is inaccessible from this restricted process and the dashboard "
                f"service could not execute routing: {broker_error}"
            ) from direct_error


def _verified_route_hosts(store: Any) -> list[dict[str, Any]]:
    """Return every installation-backed host context available to a CLI route."""

    if store is None:
        return []
    from agency_runtime.core.host_capabilities import (
        diagnostic_installation_capability_receipt,
    )
    from agency_runtime.core.host_control import inspect_all_host_statuses

    try:
        statuses = inspect_all_host_statuses(store, global_enabled=True)
    except Exception:
        # This proof only narrows a diagnostic result. Any inventory or
        # compatibility failure must remove the optional authority rather than
        # make the otherwise read-only CLI route unavailable.
        return []
    contexts: list[dict[str, Any]] = []
    for selected in statuses:
        if selected.get("effective_enabled") is not True:
            continue
        capabilities = selected.get("execution_capabilities")
        if (
            not isinstance(capabilities, dict)
            or capabilities.get("status") != "native-installation-verified"
        ):
            continue
        host = str(selected.get("host") or "")
        platform = str(capabilities.get("platform") or "")
        receipt = diagnostic_installation_capability_receipt(
            capabilities,
            surface=host,
            platform=platform,
        )
        if receipt is None:
            continue
        contexts.append({"host": host, "platform": platform, "capability_receipt": receipt})
    return sorted(contexts, key=lambda item: item["host"])


def _route_host_context(store: Any, requested: str = "") -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve one host context for a CLI route, and say why when there is none.

    AR-374: this previously proved a host only when *exactly one* was verified,
    so an ordinary multi-host installation proved none and every candidate was
    rejected `execution_host_unproven`. More installation meant less capability.
    A caller now disambiguates with `--host`; the single-host case is unchanged.
    """

    verified = _verified_route_hosts(store)
    available = [item["host"] for item in verified]
    wanted = str(requested or "").strip().casefold()
    if wanted:
        for item in verified:
            if item["host"] == wanted:
                return item, {"host_proof": "requested", "verified_hosts": available}
        return {}, {
            "host_proof": "requested_host_unverified",
            "requested_host": wanted,
            "verified_hosts": available,
        }
    if len(verified) == 1:
        return verified[0], {"host_proof": "single_verified", "verified_hosts": available}
    if not verified:
        return {}, {"host_proof": "no_verified_host", "verified_hosts": []}
    return {}, {"host_proof": "ambiguous_host", "verified_hosts": available}


def cmd_route(args: argparse.Namespace) -> int:
    if not _runtime_enabled():
        routing = _bypassed_routing()
        payload = {"task": args.task, "routing": routing, "candidates": []}
        if args.json:
            _print_json(payload)
        else:
            print("selected: none (status=bypassed)")
            print("confidence=0.000 source=master_control trace=none")
        return 0

    from agency_runtime.core.selector.candidate_narrow import pre_narrow
    from agency_runtime.core.selector.pipeline import route

    try:
        operation = _routing_operation(
            session_id="cli",
            task=args.task,
            limit=args.limit,
        )
    except RuntimeError as exc:
        message = safe_display_token(str(exc), limit=500)
        if args.json:
            _print_json(
                {
                    "ok": False,
                    "exit_code": 1,
                    "error": message,
                    "task": args.task,
                    "routing": None,
                    "candidates": [],
                }
            )
        else:
            print(f"❌ {message}", file=sys.stderr)
        return 1
    receipt = operation.receipt
    snapshot = operation.snapshot
    if receipt is not None:
        routing = dict(receipt["routing"])
        candidate_rows = [dict(item) for item in receipt["considered_candidates"]]
    elif snapshot is not None:
        snapshot, workforce = bind_workforce_snapshot(operation.store, snapshot)
        catalog = snapshot.catalog
        if not catalog:
            if args.json:
                _print_json(
                    {
                        "ok": False,
                        "exit_code": 1,
                        "error": "No active agents available",
                        "task": args.task,
                        "routing": None,
                        "candidates": [],
                    }
                )
            else:
                print("No active agents available", file=sys.stderr)
            return 1
        host_context, host_proof = _route_host_context(
            operation.store, getattr(args, "host", "") or ""
        )
        routing = route(
            "cli",
            args.task,
            catalog,
            config=snapshot.config,
            store=None,
            turn_state=operation.store.get_turn_state_context("cli"),
            allow_installation_diagnostic=bool(host_context),
            workforce_snapshot=workforce,
            **host_context,
        )
        candidates, scores = pre_narrow(args.task, catalog, limit=args.limit)
        candidate_rows = [
            {**candidate, "score": round(float(score), 4)}
            for candidate, score in zip(candidates, scores, strict=True)
        ]
    else:
        raise RuntimeError("routing operation returned no direct or brokered result")
    if args.json:
        _print_json(
            {
                "task": args.task,
                "routing": routing,
                "candidates": candidate_rows,
                "host_proof": host_proof,
            }
        )
    else:
        selected = routing.get("selected_ids") or []
        if selected:
            print(f"selected: {', '.join(selected)}")
        else:
            _print_no_selection_diagnostic(routing)
        _print_host_proof(host_proof)
        print(
            f"confidence={float(routing.get('confidence', 0.0)):.3f} "
            f"source={routing.get('provider', 'deterministic')} "
            f"trace={routing.get('trace_id', '')}"
        )
        _print_latency_metrics(routing)
        for agent in candidate_rows:
            print(f"candidate: {agent['slug']} score={agent['score']:.3f}")
        if routing.get("companion_actions"):
            print(f"companion actions: {', '.join(routing['companion_actions'])}")
        _print_disabled_candidate_shadows(routing)
    return 0


def _print_host_proof(host_proof: dict[str, Any]) -> None:
    """Say which host, if any, the ranking was proven against.

    AR-374: without this the caller cannot tell a ranking that survived
    eligibility from one where every candidate was rejected
    `execution_host_unproven` and the list is score order alone.
    """

    proof = str(host_proof.get("host_proof") or "")
    hosts = ", ".join(host_proof.get("verified_hosts") or ()) or "none"
    if proof in {"requested", "single_verified"}:
        return
    if proof == "ambiguous_host":
        print(
            f"host: not proven — {hosts} are all verified; pass --host to rank against one of them"
        )
    elif proof == "requested_host_unverified":
        print(
            f"host: not proven — requested {host_proof.get('requested_host', '')!r} "
            f"is not verified; verified hosts: {hosts}"
        )
    else:
        print("host: not proven — no verified host on this installation")
    print("      every candidate is ineligible, so the list below is score order only")


def _print_no_selection_diagnostic(routing: dict[str, Any]) -> None:
    """Print the exact persisted cause when no specialist was selected.

    Surfaces status, inference_mode, error, inference_failures, and latency
    metrics so the operator can diagnose the real failure (recruiter abstention,
    plan-policy veto, provider failure) instead of guessing. The README "fails
    honestly" promise requires this.
    """

    inference_mode = routing.get("inference_mode") or ""
    inference_failures = routing.get("inference_failures") or []
    error = str(routing.get("error") or "").strip()
    status_label = routing.get("status", "unknown")
    if inference_mode:
        status_label = f"{status_label}; inference_mode={inference_mode}"
    print(f"selected: none (status={status_label})")
    if error:
        print(f"reason: {error}")
    if inference_failures:
        print(f"inference failures: {', '.join(inference_failures)}")
    _print_latency_metrics(routing)


def _print_latency_metrics(routing: dict[str, Any]) -> None:
    """Print per-stage inference latency if present."""

    stage_latencies = routing.get("stage_latencies") or {}
    total_calls = routing.get("total_inference_calls")
    if not stage_latencies and total_calls is None:
        return
    parts = [f"{stage}={ms}ms" for stage, ms in sorted(stage_latencies.items())]
    if total_calls is not None:
        parts.append(f"total_calls={total_calls}")
    if parts:
        print(f"inference: {', '.join(parts)}")


def _print_disabled_candidate_shadows(routing: dict[str, Any]) -> None:
    """Show higher-ranked disabled workers without changing routing policy."""

    for shadow in routing.get("disabled_candidate_shadows") or []:
        if not isinstance(shadow, dict):
            continue
        disabled = str(shadow.get("agent_id") or "").strip()
        fallback = str(shadow.get("fallback_agent_id") or "").strip()
        if disabled:
            suffix = f"; used {fallback}" if fallback else ""
            print(f"left on the table: disabled {disabled} ranked higher{suffix}")


def cmd_explain(args: argparse.Namespace) -> int:
    if not _runtime_enabled():
        _print_json(
            {
                "runtime_enabled": False,
                "bypassed": True,
                "session_id": str(args.session_id or ""),
                "task": str(args.task or ""),
                "routing": _bypassed_routing(),
                "selected": [],
                "considered_candidates": [],
                "rejected_candidates": [],
                "signals": {"source": "master_control"},
            }
        )
        return 0

    try:
        operation = _routing_operation(
            session_id=str(args.session_id or ""),
            task=args.task,
            limit=args.limit,
        )
    except RuntimeError as exc:
        message = safe_display_token(str(exc), limit=500)
        _print_json(
            {
                "ok": False,
                "exit_code": 1,
                "error": message,
                "session_id": str(args.session_id or ""),
                "task": str(args.task or ""),
                "routing": None,
                "selected": [],
                "considered_candidates": [],
                "rejected_candidates": [],
                "signals": {},
            }
        )
        return 1
    if operation.receipt is not None:
        payload = operation.receipt
    elif operation.snapshot is not None:
        host_context, host_proof = _route_host_context(
            operation.store, getattr(args, "host", "") or ""
        )
        payload = {
            **explain_route(
                args.session_id,
                args.task,
                operation.snapshot.catalog,
                limit=args.limit,
                config=operation.snapshot.config,
                store=operation.store,
                **host_context,
            ),
            # AR-374: an explanation that cannot say which host it was proven
            # against reads the same whether eligibility passed or rejected
            # every candidate.
            "host_proof": host_proof,
        }
    else:
        raise RuntimeError("routing operation returned no direct or brokered result")
    _print_json(payload)
    return 0


def _policy_mapping(policy: dict[str, Any], key: str) -> dict[Any, Any]:
    """Return one policy mapping, leaving validation to the policy validator."""
    value = policy.get(key, {})
    return value if isinstance(value, dict) else {}


def _active_roster_slugs(catalog: list[dict[str, Any]]) -> set[str]:
    """Collect canonical slugs from either supported catalog projection."""
    return {identity for agent in catalog if (identity := agent_identity(agent))}


def _same_config_path(left: str, right: str) -> bool:
    return os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))


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


def _policy_operation(
    dependencies: RosterDependencies,
) -> tuple[dict[str, Any], set[str]]:
    """Load direct policy inputs or broker them after an exact token refusal."""

    injected_dependencies = (
        dependencies.policy_loader is not DEFAULT_DEPENDENCIES.policy_loader
        or dependencies.store_factory is not DEFAULT_DEPENDENCIES.store_factory
    )

    from agency_runtime.core.windows_acl import require_restricted_windows_token

    try:
        if injected_dependencies:
            catalog = dependencies.store_factory().get_active_roster_as_catalog()
            return dependencies.policy_loader(), _active_roster_slugs(catalog)
        runtime_store = dependencies.store_factory()
        snapshot = capture_routing_snapshot(runtime_store)
        return (
            load_policy(policy_path_for_config(snapshot.config)),
            _active_roster_slugs(snapshot.catalog),
        )
    except Exception as direct_error:
        require_restricted_windows_token(direct_error)
        try:
            from agency_runtime.cli.agent_control_broker import (
                broker_activation_rows,
                broker_policy_snapshot,
            )

            if injected_dependencies:
                path, catalog = broker_activation_rows()
                policy = dependencies.policy_loader()
                active_slugs = _active_roster_slugs(catalog)
            else:
                path, policy, active_slugs = broker_policy_snapshot()
            intended_path = str(resolve_config_path())
            if not _same_config_path(path, intended_path):
                raise ValueError("dashboard service config does not match the CLI config identity")
            return policy, active_slugs
        except (OSError, RuntimeError, ValueError) as broker_error:
            raise RuntimeError(
                "policy state is inaccessible from this restricted process and the dashboard "
                f"service could not broker it: {broker_error}"
            ) from direct_error


def cmd_policy(
    args: argparse.Namespace,
    *,
    dependencies: RosterDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Show the active companion policy and validate coverage against the roster."""
    if dependencies is DEFAULT_DEPENDENCIES:
        # Preserve the public monkeypatch/embedding seams while keeping the
        # immutable dependency object as the normal production fast path.
        dependencies = RosterDependencies(
            store_factory=_store,
            emit_json=_print_json,
            policy_loader=load_policy,
        )
    try:
        policy, active_slugs = _policy_operation(dependencies)
    except RuntimeError as exc:
        message = safe_display_token(str(exc), limit=500)
        if args.json:
            dependencies.emit_json(
                {
                    "ok": False,
                    "exit_code": 1,
                    "error": message,
                    "valid": False,
                    "actions": {},
                    "division_anchors": {},
                }
            )
        else:
            print(f"❌ {message}", file=sys.stderr)
        return 1
    actions = _policy_mapping(policy, "actions")
    divisions = _policy_mapping(policy, "division_anchors")
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


def cmd_eval_host_parity(args: argparse.Namespace) -> int:
    from agency_runtime.core.evals.host_parity import run_host_parity_eval

    report = run_host_parity_eval()
    if args.json:
        _print_json(report)
    else:
        status = "passed" if report["passed"] else "failed"
        print(
            f"host-parity eval {status}: "
            f"{report['passed_count']} passed, {report['failed_count']} failed"
        )
        for case in report["cases"]:
            marker = "ok" if case["passed"] else "FAIL"
            detail = case.get("error") or case.get("detail") or ""
            print(f"{marker}\t{case['name']}\t{detail}")
    return 0 if report["passed"] else 1


def cmd_eval_spawn_authority(args: argparse.Namespace) -> int:
    """Prove at the source that Agency never decides to spawn an agent."""
    from agency_runtime.core.evals.spawn_authority import run_spawn_authority_eval

    report = run_spawn_authority_eval()
    if args.json:
        _print_json(report)
    else:
        status = "passed" if report["passed"] else "failed"
        print(
            f"spawn-authority eval {status}: "
            f"{report['passed_count']} passed, {report['failed_count']} failed"
        )
        for case in report["cases"]:
            marker = "ok" if case["passed"] else "FAIL"
            detail = case.get("error") or case.get("detail") or ""
            print(f"{marker}\t{case['name']}\t{detail}")
    return 0 if report["passed"] else 1


def cmd_eval_staffing(args: argparse.Namespace) -> int:
    """Measure staffing over the fixed ask set and print the manifest."""
    from agency_runtime.core.evals.staffing import run_staffing_eval

    report = run_staffing_eval(include_details=not args.no_details)
    if args.json:
        _print_json(report)
    else:
        status = "passed" if report["passed"] else "failed"
        metrics = report["metrics"]
        print(
            f"staffing eval {status}: {metrics['staffed']}/{metrics['valid_arms']} staffed"
            f" ({metrics['invalid_arms']} invalid arms reported, never scored)"
        )
        for gate in report["gates"]:
            marker = "ok" if gate["passed"] else "FAIL"
            print(
                f"{marker}	{gate['name']}	{gate['observed']} (threshold {gate['threshold']})"
            )
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

    host = getattr(args, "agent", None)
    if host and args.all:
        print("--agent and --all are mutually exclusive", file=sys.stderr)
        return 2
    report = run_smoke(all_hosts=args.all, host=host)
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
