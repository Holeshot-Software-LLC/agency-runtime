"""Attended, ownership-bound host-integration uninstall commands."""

from __future__ import annotations

import argparse
import json
import logging
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from agency_runtime.core.bounded_io import atomic_write_text
from agency_runtime.core.installer_contracts import HOSTS
from agency_runtime.core.private_paths import private_runtime_directory

from ._common import print_json

_REPORT_SCHEMA = "agency.uninstall.v1"
_PRESERVED = (
    "package",
    "agency-configuration",
    "store",
    "roster",
    "evidence",
    "backups",
    "dashboard-service",
    "marketplace-registrations",
    "unrelated-host-configuration",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UninstallDependencies:
    """Patchable boundaries for uninstall planning and application."""

    plan_host: Callable[..., dict[str, Any]]
    apply_prepared: Callable[..., list[dict[str, Any]]]
    emit_json: Callable[[Any], None] = print_json
    write_journal: Callable[[Mapping[str, Any]], str] | None = None


def _dependencies() -> UninstallDependencies:
    from agency_runtime.core.installer import (
        apply_prepared_host_uninstall,
        plan_agent_uninstall,
    )

    return UninstallDependencies(
        plan_host=plan_agent_uninstall,
        apply_prepared=apply_prepared_host_uninstall,
    )


def _has_agency_evidence(inspection: Mapping[str, Any]) -> bool:
    managed = all(
        isinstance(inspection.get(field), str) and bool(inspection.get(field))
        for field in ("managed_plugin_version", "install_id", "bundle_digest")
    )
    return bool(managed or inspection.get("registered") is True)


def _target_plans(
    args: argparse.Namespace,
    deps: UninstallDependencies,
) -> tuple[list[str], list[dict[str, Any]], str, list[dict[str, Any]]]:
    agent = getattr(args, "agent", None)
    if agent:
        host = str(agent)
        plan = deps.plan_host(host)
        inspection = plan.get("inspection")
        inspections = [dict(inspection)] if isinstance(inspection, Mapping) else []
        return [host], inspections, "agent", [plan]
    plans = [deps.plan_host(host) for host in HOSTS]
    inspections = [
        dict(inspection)
        for plan in plans
        if isinstance((inspection := plan.get("inspection")), Mapping)
    ]
    selected_plans = [
        plan
        for plan in plans
        if _has_agency_evidence(plan.get("inspection") or {})
        or bool((plan.get("ownership") or {}).get("present"))
    ]
    return (
        [str(plan["host"]) for plan in selected_plans],
        inspections,
        "all",
        selected_plans,
    )


def _plan_digest(
    plans: list[Mapping[str, Any]],
    *,
    selected_by: str,
    targets: list[str],
) -> str:
    from agency_runtime.core.prepared_host_uninstall import uninstall_plan_digest

    return uninstall_plan_digest(plans, selected_by=selected_by, targets=targets)


def _journal_outcome(item: Mapping[str, Any]) -> dict[str, Any]:
    """Project one host result without native output or configuration content."""

    return {
        "host": item.get("host"),
        "status": item.get("status"),
        "ok": item.get("ok") is True,
        "complete": item.get("complete") is True,
        "changed": item.get("changed") is True,
        "failed_step": item.get("failed_step"),
        "retained_path": item.get("retained_path"),
    }


def _journal_payload(
    *,
    operation_id: str,
    plan_digest: str,
    selected_by: str,
    plans: list[Mapping[str, Any]],
    outcomes: list[Mapping[str, Any]],
    status: str,
) -> dict[str, Any]:
    return {
        "schema_version": "agency.uninstall-operation.v1",
        "operation_id": operation_id,
        "plan_digest": plan_digest,
        "selected_by": selected_by,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "planned_hosts": [
            {
                "host": plan.get("host"),
                "target": plan.get("target"),
                "install_id": (plan.get("ownership") or {}).get("install_id"),
                "bundle_digest": (plan.get("ownership") or {}).get("bundle_digest"),
                "binding_digest": plan.get("binding_digest"),
                "status": plan.get("status"),
            }
            for plan in plans
        ],
        "outcomes": [_journal_outcome(item) for item in outcomes],
    }


def _write_operation_journal(payload: Mapping[str, Any]) -> str:
    """Durably record an owner-private mutation intent or completion checkpoint."""

    operation_id = str(payload.get("operation_id") or "")
    try:
        if str(uuid.UUID(operation_id)) != operation_id:
            raise ValueError
    except (AttributeError, ValueError) as exc:
        raise ValueError("Uninstall journal operation_id is invalid") from exc
    rendered = json.dumps(dict(payload), sort_keys=True, separators=(",", ":")) + "\n"
    if len(rendered.encode("utf-8")) > 64 * 1024:
        raise ValueError("Uninstall journal exceeds its bounded size")
    target = private_runtime_directory("operations") / f"uninstall-{operation_id}.json"
    atomic_write_text(target, rendered)
    return str(target)


def _report(
    *,
    operation_id: str,
    plan_digest: str,
    selected_by: str,
    dry_run: bool,
    targets: list[str],
    inspections: list[dict[str, Any]],
    hosts: list[dict[str, Any]],
) -> dict[str, Any]:
    complete = all(item.get("ok") and item.get("complete") for item in hosts)
    return {
        "schema_version": _REPORT_SCHEMA,
        "operation_id": operation_id,
        "plan_digest": plan_digest,
        "ok": complete,
        "complete": complete,
        "dry_run": dry_run,
        "selected_by": selected_by,
        "selected_hosts": targets,
        "inspected_host_count": len(inspections),
        "hosts": hosts,
        "preserved": list(_PRESERVED),
    }


def _render_host(item: Mapping[str, Any], *, dry_run: bool) -> None:
    host = item.get("host", "unknown")
    status = item.get("status", "unknown")
    marker = "✅" if item.get("ok") else "❌"
    verb = "plan" if dry_run else "result"
    print(f"{marker} {host}: {verb} {status}")
    if item.get("target"):
        print(f"   Target: {item['target']}")
    if item.get("retained_path"):
        print(f"   Retained: {item['retained_path']}")
    if item.get("error"):
        print(f"   Error: {item['error']}")
    if item.get("recovery"):
        print(f"   Recovery: {item['recovery']}")


def _render(report: Mapping[str, Any]) -> None:
    if report.get("dry_run"):
        print("DRY RUN — no host, filesystem, package, dashboard, configuration, or Store mutation")
    selected = report.get("selected_hosts", [])
    if not selected:
        print("No owned Agency Runtime host integrations were found.")
    for item in report.get("hosts", []):
        _render_host(item, dry_run=bool(report.get("dry_run")))
    if report.get("plan_digest"):
        print(f"Plan digest: {report['plan_digest']}")
    if report.get("journal_path"):
        print(f"Operation journal: {report['journal_path']}")
    if report.get("error"):
        print(f"Error: {report['error']}")
    print("Preserved: " + ", ".join(report.get("preserved", [])))
    if report.get("dry_run") and selected:
        selector = "--all" if report.get("selected_by") == "all" else f"--agent {selected[0]}"
        print(f"Apply exactly: agency uninstall {selector} --confirm-plan {report['plan_digest']}")
    if not report.get("dry_run") and selected:
        print(
            "Restart affected harnesses before treating Agency as unloaded from existing sessions."
        )


def _apply_plans(
    deps: UninstallDependencies,
    *,
    operation_id: str,
    digest: str,
    selected_by: str,
    plans: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str | None, str | None, str | None]:
    """Apply preflighted plans while durably checkpointing every host outcome."""

    outcomes: list[dict[str, Any]] = []
    journal_path: str | None = None
    journal_error: str | None = None
    operation_error: str | None = None
    writer = deps.write_journal or _write_operation_journal
    mutating = any(plan.get("would_change") is True for plan in plans)

    def record_authorized() -> None:
        nonlocal journal_path, journal_error
        try:
            journal_path = writer(
                _journal_payload(
                    operation_id=operation_id,
                    plan_digest=digest,
                    selected_by=selected_by,
                    plans=plans,
                    outcomes=outcomes,
                    status="intent_recorded",
                )
            )
        except Exception as exc:
            journal_error = f"{type(exc).__name__}: {exc}"[:500]
            raise RuntimeError("uninstall operation journal could not be recorded") from exc

    def record_outcome(item: dict[str, Any]) -> None:
        nonlocal journal_error
        outcomes.append(dict(item))
        if mutating:
            try:
                writer(
                    _journal_payload(
                        operation_id=operation_id,
                        plan_digest=digest,
                        selected_by=selected_by,
                        plans=plans,
                        outcomes=outcomes,
                        status="applying",
                    )
                )
            except Exception as exc:
                journal_error = f"{type(exc).__name__}: {exc}"[:500]
                raise RuntimeError("uninstall operation journal could not be updated") from exc

    if journal_error is None:
        try:
            returned = deps.apply_prepared(
                [str(plan["host"]) for plan in plans],
                expected_plan_digest=digest,
                operation_id=operation_id,
                selected_by=selected_by,
                on_authorized=record_authorized if mutating else None,
                on_result=record_outcome,
            )
            if mutating and journal_path is None and journal_error is None:
                operation_error = "Prepared uninstall did not record its authorized intent"
            if not outcomes:
                outcomes.extend(dict(item) for item in returned)
            elif [dict(item) for item in returned] != outcomes:
                operation_error = "Prepared uninstall returned inconsistent host outcomes"
        except Exception as exc:
            if journal_error is None:
                operation_error = f"{type(exc).__name__}: {exc}"[:500]

    if len(outcomes) < len(plans):
        stopped_error = (
            "Uninstall stopped because its operation journal could not be updated"
            if journal_error
            else "Uninstall stopped because prepared authority or state validation failed"
            if operation_error
            else "Uninstall stopped after a preceding host failed"
        )
        outcomes.extend(
            {
                **dict(plan),
                "ok": False,
                "complete": False,
                "status": "not_attempted",
                "error": stopped_error,
            }
            for plan in plans[len(outcomes) :]
        )
    return outcomes, journal_path, journal_error, operation_error


def cmd_uninstall(
    args: argparse.Namespace,
    *,
    dependencies: UninstallDependencies | None = None,
) -> int:
    """Plan or remove exact owned host integrations across selected harnesses."""

    deps = dependencies or _dependencies()
    dry_run = bool(getattr(args, "dry_run", False))
    json_mode = bool(getattr(args, "json", False))
    targets, inspections, selected_by, plans = _target_plans(args, deps)
    operation_id = str(uuid.uuid4())
    digest = _plan_digest(plans, selected_by=selected_by, targets=targets)

    confirmed = getattr(args, "confirm_plan", None)
    confirmation_mismatch = not dry_run and confirmed != digest
    if dry_run or confirmation_mismatch or any(not plan.get("ok") for plan in plans):
        report = _report(
            operation_id=operation_id,
            plan_digest=digest,
            selected_by=selected_by,
            dry_run=dry_run,
            targets=targets,
            inspections=inspections,
            hosts=plans,
        )
        if confirmation_mismatch:
            report.update(
                {
                    "ok": False,
                    "complete": False,
                    "confirmation_required": True,
                    "error": (
                        "Uninstall plan changed or was not confirmed; rerun --dry-run and pass "
                        "its exact plan_digest with --confirm-plan"
                    ),
                }
            )
    else:
        outcomes, journal_path, journal_error, operation_error = _apply_plans(
            deps,
            operation_id=operation_id,
            digest=digest,
            selected_by=selected_by,
            plans=plans,
        )
        mutating = any(plan.get("would_change") is True for plan in plans)
        writer = deps.write_journal or _write_operation_journal
        report = _report(
            operation_id=operation_id,
            plan_digest=digest,
            selected_by=selected_by,
            dry_run=False,
            targets=targets,
            inspections=inspections,
            hosts=outcomes if outcomes else plans,
        )
        if journal_error:
            report.update(
                {
                    "ok": False,
                    "complete": False,
                    "journal_error": journal_error,
                    "error": (
                        "Uninstall operation journal could not be recorded; no further host "
                        "mutations were attempted"
                    ),
                }
            )
        else:
            if operation_error:
                report.update(
                    {
                        "ok": False,
                        "complete": False,
                        "operation_error": operation_error,
                        "error": "Prepared operator authority or uninstall state validation failed",
                    }
                )
            if mutating and journal_path is not None:
                try:
                    writer(
                        _journal_payload(
                            operation_id=operation_id,
                            plan_digest=digest,
                            selected_by=selected_by,
                            plans=plans,
                            outcomes=outcomes,
                            status="complete" if report["complete"] else "partial_failure",
                        )
                    )
                except Exception as exc:
                    report.update(
                        {
                            "ok": False,
                            "complete": False,
                            "journal_error": f"{type(exc).__name__}: {exc}"[:500],
                            "error": (
                                "Host operations finished, but their final journal update failed"
                            ),
                        }
                    )
        if journal_path:
            report["journal_path"] = journal_path
    logger.info(
        "Agency host uninstall operation=%s selected=%s complete=%s dry_run=%s",
        operation_id,
        len(targets),
        report["complete"],
        dry_run,
    )
    if json_mode:
        deps.emit_json(report)
    else:
        _render(report)
    return 0 if report["complete"] else 1


__all__ = ["UninstallDependencies", "cmd_uninstall"]
