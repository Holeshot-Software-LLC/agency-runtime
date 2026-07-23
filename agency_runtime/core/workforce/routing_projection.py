"""Project verified workforce outcomes into the native preflight contract."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any

from agency_runtime.core.unit_assignment import (
    MAX_WORK_UNIT_CHARS,
    MUTATION_SCOPES,
    PARALLELIZATION_MODES,
    project_unit_assignment_agents,
    work_unit_id_from_text,
)
from agency_runtime.core.workforce.inference import WorkforceRoutingOutcome

_ARTIFACTS = frozenset(
    {
        "analysis",
        "architecture-record",
        "documentation",
        "implementation-change",
        "plan",
        "review-report",
        "test-code",
        "test-evidence",
    }
)
_LIFECYCLES = frozenset(
    {
        "coordination",
        "discovery",
        "documentation",
        "design",
        "implementation",
        "planning",
        "release",
        "review",
        "testing",
    }
)
_AUTHORITIES = frozenset({"advise", "plan", "modify", "review"})
_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,127}\Z")
_WORK_UNIT_ID = re.compile(r"unit-[0-9a-f]{10}\Z")


def project_workforce_unit_bindings(value: Any) -> list[dict[str, Any]] | None:
    """Validate the content-free verifier bindings required for exact replay."""

    if not isinstance(value, (list, tuple)) or len(value) > 16:
        return None
    projected: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            return None
        work_unit_id = str(item.get("work_unit_id") or "").strip().casefold()
        selected = item.get("selected")
        dependencies = item.get("depends_on")
        tools = item.get("required_tools")
        evidence = item.get("required_evidence")
        delivery = str(item.get("delivery") or "").strip().casefold()
        timing = str(item.get("timing") or "").strip().casefold()
        parallelization = str(item.get("parallelization") or "").strip().casefold()
        mutation_scope = str(item.get("mutation_scope") or "").strip().casefold()
        artifact = str(item.get("artifact_kind") or "").strip().casefold()
        try:
            confidence = float(item.get("confidence"))
        except (TypeError, ValueError, OverflowError):
            return None
        if (
            _WORK_UNIT_ID.fullmatch(work_unit_id) is None
            or not isinstance(selected, (list, tuple))
            or not 1 <= len(selected) <= 4
            or any(_ID.fullmatch(str(agent).strip().casefold()) is None for agent in selected)
            or not isinstance(dependencies, (list, tuple))
            or len(dependencies) > 16
            or any(
                _WORK_UNIT_ID.fullmatch(str(dep).strip().casefold()) is None for dep in dependencies
            )
            or delivery not in {"delegate", "load"}
            or timing not in {"immediate", "after_dependencies", "after_artifact"}
            or parallelization not in PARALLELIZATION_MODES
            or mutation_scope not in MUTATION_SCOPES
            or artifact not in _ARTIFACTS
            or not isinstance(tools, (list, tuple))
            or not isinstance(evidence, (list, tuple))
            or len(tools) > 32
            or len(evidence) > 32
            or any(
                not isinstance(entry, str) or not entry or len(entry) > 128
                for entry in (*tools, *evidence)
            )
            or not math.isfinite(confidence)
            or not 0.0 <= confidence <= 1.0
        ):
            return None
        projected.append(
            {
                "work_unit_id": work_unit_id,
                "selected": [str(agent).strip().casefold() for agent in selected],
                "delivery": delivery,
                "timing": timing,
                "depends_on": [str(dep).strip().casefold() for dep in dependencies],
                "parallelization": parallelization,
                "mutation_scope": mutation_scope,
                "artifact_kind": artifact,
                "required_tools": list(tools),
                "required_evidence": list(evidence),
                "confidence": confidence,
            }
        )
    return projected


def project_workforce_unit_descriptors(value: Any) -> list[dict[str, Any]] | None:
    """Validate the closed, content-free shape persisted for workforce replay."""

    if not isinstance(value, (list, tuple)) or len(value) > 16:
        return None
    result: list[dict[str, Any]] = []
    for ordinal, item in enumerate(value, start=1):
        if not isinstance(item, Mapping) or set(item) != {
            "ordinal",
            "artifact_kind",
            "lifecycle_phase",
            "authority",
        }:
            return None
        artifact = str(item["artifact_kind"]).strip().casefold()
        lifecycle = str(item["lifecycle_phase"]).strip().casefold()
        authority = str(item["authority"]).strip().casefold()
        if (
            item["ordinal"] != ordinal
            or artifact not in _ARTIFACTS
            or lifecycle not in _LIFECYCLES
            or authority not in _AUTHORITIES
        ):
            return None
        result.append(
            {
                "ordinal": ordinal,
                "artifact_kind": artifact,
                "lifecycle_phase": lifecycle,
                "authority": authority,
            }
        )
    return result


def _goal(request: str, descriptor: Mapping[str, Any]) -> str:
    text = (
        f"Request: {' '.join(request.split())}. "
        f"Work unit {descriptor['ordinal']}: produce {descriptor['artifact_kind']} "
        f"during {descriptor['lifecycle_phase']} with {descriptor['authority']} authority."
    )
    return " ".join(text.split())[:MAX_WORK_UNIT_CHARS]


def workforce_work_units_from_descriptors(
    request: str,
    descriptors: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Rebuild unit goals from correlated request content and closed descriptors."""

    return [_goal(request, item) for item in descriptors]


def _catalog_by_slug(
    catalog: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for item in catalog:
        slug = str(item.get("slug") or item.get("agent_slug") or "").strip().casefold()
        if slug and slug not in result:
            result[slug] = item
    return result


def _assignment_agents(
    catalog: Sequence[Mapping[str, Any]],
    bindings: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_slug = _catalog_by_slug(catalog)
    candidates: dict[str, dict[str, Any]] = {}
    for binding in bindings:
        work_unit_id = str(binding["work_unit_id"])
        for ordinal, raw_slug in enumerate(binding["selected"]):
            slug = str(raw_slug).strip().casefold()
            metadata = by_slug.get(slug)
            if metadata is None:
                raise RuntimeError(f"verified workforce agent is absent from catalog: {slug}")
            candidate = candidates.setdefault(
                slug,
                {
                    "slug": slug,
                    "name": metadata.get("name"),
                    "description": metadata.get("description"),
                    "capabilities": metadata.get("capabilities"),
                    "tags": [
                        *(metadata.get("tags") or []),
                        *(metadata.get("categories") or []),
                    ],
                    "required_tools": metadata.get("required_tools"),
                    "evidence_requirements": metadata.get("evidence_requirements"),
                    "matched_work_unit_ids": [],
                    "primary_work_unit_ids": [],
                },
            )
            candidate["matched_work_unit_ids"].append(work_unit_id)
            if ordinal == 0:
                candidate["primary_work_unit_ids"].append(work_unit_id)
    projected = project_unit_assignment_agents(list(candidates.values()), strict=True)
    if projected is None:
        raise RuntimeError("verified workforce assignments could not be projected")
    return projected


def _provider_attempts(outcome: WorkforceRoutingOutcome) -> list[dict[str, Any]]:
    return [
        {
            "stage": item.stage,
            "provider_name": item.provider_name,
            "provider_type": item.provider_type,
            "requested_model": item.requested_model,
            "model_group": item.model_group,
            "actual_model": item.actual_model,
            "model_receipt_source": item.model_receipt_source,
            "status": item.status,
            "reason_code": item.reason_code,
            "reason": item.reason_code,
            "validation_detail": item.validation_detail,
            "latency_ms": item.latency_ms,
        }
        for item in outcome.attempts
    ]


def project_workforce_routing(
    outcome: WorkforceRoutingOutcome,
    catalog: Sequence[Mapping[str, Any]],
    *,
    request: str,
    roster_count: int,
    contract_fingerprint: str,
) -> dict[str, Any]:
    """Return a bounded route whose selections are exactly verifier-approved."""

    plan = outcome.plan
    proposal = outcome.proposal
    staffing = outcome.staffing
    proposal_by_unit = (
        {item.unit_id: item for item in proposal.units} if proposal is not None else {}
    )
    staffing_by_unit = {item.unit_id: item for item in staffing.units}
    descriptors: list[dict[str, Any]] = []
    unit_ids: dict[str, str] = {}
    if plan is not None:
        for ordinal, unit in enumerate(plan.units, start=1):
            descriptor = {
                "ordinal": ordinal,
                "artifact_kind": unit.artifact_kind,
                "lifecycle_phase": unit.lifecycle_phase,
                "authority": unit.authority,
            }
            descriptors.append(descriptor)
            goal = _goal(request, descriptor)
            unit_ids[unit.unit_id] = work_unit_id_from_text(goal)
    goals = workforce_work_units_from_descriptors(request, descriptors)

    bindings: list[dict[str, Any]] = []
    if outcome.accepted and plan is not None:
        for unit in plan.units:
            verified = staffing_by_unit[unit.unit_id]
            proposed = proposal_by_unit[unit.unit_id]
            bindings.append(
                {
                    "source_unit_id": unit.unit_id,
                    "work_unit_id": unit_ids[unit.unit_id],
                    "selected": list(verified.selected),
                    "delivery": verified.delivery,
                    "timing": verified.timing,
                    "depends_on": [unit_ids[item] for item in unit.depends_on],
                    "parallelization": unit.parallelization,
                    "mutation_scope": unit.mutation_scope,
                    "artifact_kind": unit.artifact_kind,
                    "required_tools": list(unit.required_tools),
                    "required_evidence": list(unit.acceptance_evidence),
                    "confidence": proposed.confidence,
                    "margin": proposed.margin,
                }
            )

    selected = list(dict.fromkeys(agent for binding in bindings for agent in binding["selected"]))
    confidences = [float(item["confidence"]) for item in bindings]
    margins = [float(item["margin"]) for item in bindings]
    attempts = _provider_attempts(outcome)
    inference_configured = outcome.inference_mode != "deterministic"
    disabled_shadows = [
        asdict(shadow) for unit in staffing.units for shadow in unit.disabled_shadows
    ]
    unavailable_shadows = [
        asdict(shadow) for unit in staffing.units for shadow in unit.unavailable_shadows
    ]
    return {
        "selected_ids": selected,
        "semantic_ids": selected,
        "confidence": min(confidences, default=0.0),
        "margin": min(margins, default=0.0),
        "latency_ms": sum(item.latency_ms for item in outcome.attempts),
        "status": outcome.status,
        "source": (
            "workforce_deterministic"
            if outcome.inference_mode == "deterministic"
            else "workforce_inference"
        ),
        "error": ", ".join(outcome.abstention_codes),
        "candidate_count": roster_count,
        "top_score": max(confidences, default=0.0),
        "inference_configured": inference_configured,
        "inference_required": inference_configured,
        "inference_attempted": bool(outcome.calls_used),
        "inference_mode": outcome.inference_mode,
        "provider_attempts": attempts,
        "inference_failures": [
            item["reason_code"] for item in attempts if item["status"] != "applied"
        ],
        "workforce_cache_hits": list(outcome.cache_hits),
        "work_units": {
            "count": len(goals),
            "confidence": "high" if outcome.accepted else "none",
            "source": "verified-workforce-plan",
            "units": goals,
            "delegate": any(item["delivery"] == "delegate" for item in bindings),
        },
        "workforce_contract_fingerprint": contract_fingerprint,
        "workforce_plan": None if plan is None else plan.as_dict(),
        "workforce_proposal": None if proposal is None else proposal.as_dict(),
        "workforce_staffing": staffing.as_dict(),
        "workforce_unit_bindings": bindings,
        "workforce_unit_descriptors": descriptors,
        "unit_assignment_agents": _assignment_agents(catalog, bindings) if bindings else [],
        "disabled_candidate_shadows": disabled_shadows,
        "unavailable_candidate_shadows": unavailable_shadows,
        "fallback_applied": False,
        "fallback_considered": not selected,
    }


__all__ = [
    "project_workforce_routing",
    "project_workforce_unit_bindings",
    "project_workforce_unit_descriptors",
    "workforce_work_units_from_descriptors",
]
