"""Human and JSON operator commands for durable workforce evidence and lifecycle."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agency_runtime.core.agent_activation import normalize_agent_slug
from agency_runtime.core.config_binding import config_for_store
from agency_runtime.core.roster.workforce import workforce_index_snapshot
from agency_runtime.core.workforce.comparison import (
    consolidation_candidates,
    nearest_workers,
)
from agency_runtime.core.workforce.hiring import apply_approved_hiring_case
from agency_runtime.core.workforce.promotion import promotion_readiness

from . import _render
from ._common import print_json, store


@dataclass(frozen=True, slots=True)
class WorkforceDependencies:
    store_factory: Callable[..., Any] = store
    emit_json: Callable[[Any], None] = print_json


DEFAULT_DEPENDENCIES = WorkforceDependencies()
_SEARCH_TOKENS = re.compile(r"[a-z0-9]+")


def _emit(value: Any, *, as_json: bool, dependencies: WorkforceDependencies) -> None:
    if as_json:
        dependencies.emit_json(value)


def _worker_line(worker: dict[str, Any]) -> str:
    return "\t".join(
        (
            str(worker["agent_slug"]),
            str(worker["state"]),
            str(worker["display_label"]),
            str(worker["current_version"]),
            f"revision={worker['revision']}",
        )
    )


def cmd_workforce_list(
    args: argparse.Namespace,
    *,
    dependencies: WorkforceDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    workers = dependencies.store_factory().list_workforce_workers(
        state=str(getattr(args, "state", "") or ""),
        limit=int(args.limit),
        after_slug=str(getattr(args, "after", "") or ""),
    )
    payload = {"count": len(workers), "workers": workers}
    if args.json:
        _emit(payload, as_json=True, dependencies=dependencies)
    elif _render.use_card_default(args):
        cards = [
            _render.Card(
                title=str(worker.get("agent_slug") or worker.get("display_label") or ""),
                subtitle=str(worker.get("state") or ""),
                fields=(
                    _render.field("worker_id", worker.get("worker_id")),
                    _render.field("display", worker.get("display_label")),
                    _render.field("version", worker.get("current_version")),
                    _render.field("revision", worker.get("revision")),
                ),
            )
            for worker in workers
        ]
        print(_render.render_cards(cards))
    else:
        for worker in workers:
            print(_worker_line(worker))
    return 0


def cmd_contractor_list(
    args: argparse.Namespace,
    *,
    dependencies: WorkforceDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    args.state = "contractor"
    return cmd_workforce_list(args, dependencies=dependencies)


def _packaged_divergence_report(store_instance: Any, agent_slug: str) -> list[dict[str, str]]:
    """Return this worker's packaged divergence, or nothing when unavailable.

    Older or stubbed stores may not expose the reader, and a review surface must
    still render. An absent report means "not known", never "no divergence", so
    the caller prints nothing rather than an all-clear it cannot support.
    """

    reader = getattr(store_instance, "packaged_workforce_divergence", None)
    if not callable(reader) or not agent_slug:
        return []
    try:
        return [item.to_dict() for item in reader(agent_slug)]
    except Exception:
        return []


def cmd_workforce_show(
    args: argparse.Namespace,
    *,
    dependencies: WorkforceDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    store_instance = dependencies.store_factory()
    detail = store_instance.get_workforce_worker_detail(
        args.worker,
        evidence_limit=int(args.limit),
    )
    config = config_for_store(store_instance)
    detail["promotion_readiness"] = promotion_readiness(
        detail["worker"],
        detail["outcomes"],
        required_successes=config.workforce.auto_promote_successes,
        review_window_days=config.workforce.contractor_review_days,
    )
    # Reviewing a worker means seeing whether it still matches what the package
    # ships. A pure read: reporting a divergence never repairs or reverts it.
    detail["packaged_divergence"] = _packaged_divergence_report(
        store_instance,
        str(detail["worker"].get("agent_slug") or ""),
    )
    if args.json:
        _emit(detail, as_json=True, dependencies=dependencies)
        return 0
    worker = detail["worker"]
    print(_worker_line(worker))
    contract = detail["recruitment_contract"]
    print(f"authority\t{contract['authority']}")
    print(f"archetype\t{contract['archetype']}")
    print(f"domains\t{', '.join(contract['domains']) or 'none'}")
    print(f"stacks\t{', '.join(contract['stacks']) or 'none'}")
    print(
        "evidence\t"
        f"lineage={len(detail['lineage'])}, events={len(detail['events'])}, "
        f"outcomes={len(detail['outcomes'])}, hiring_cases={len(detail['hiring_cases'])}"
    )
    readiness = detail["promotion_readiness"]
    ready_state = "ready" if readiness["eligible_for_automatic_promotion"] else "not-ready"
    if readiness.get("in_review_window"):
        ready_state = "review-window"
    print(
        "promotion\t"
        f"verified={readiness['verified_successes']}, "
        f"required={readiness['required_successes']}, "
        f"remaining={readiness['remaining_successes']}, "
        f"automatic={ready_state}"
    )
    if readiness.get("in_review_window"):
        print("review-window\tactive")
    for reason in readiness.get("reasons", []):
        print(f"promotion-reason\t{reason}")
    if readiness.get("evidence_rule"):
        print(f"evidence-rule\t{readiness['evidence_rule']}")
    for divergence in detail["packaged_divergence"]:
        print(
            "packaged-divergence\t"
            f"{divergence['reason']}: "
            f"origin {divergence['actual_origin']} (packaged {divergence['expected_origin']}), "
            f"version {divergence['actual_version']} (packaged {divergence['expected_version']})"
        )
    if detail["packaged_divergence"]:
        slug = str(worker.get("agent_slug") or "")
        print(
            "packaged-divergence\tthis worker no longer matches the packaged revision and is "
            "left as-is; retire it with: "
            f'agency workforce retire {slug} --expected-revision <n> --reason "..." '
            f'--confirm "RETIRE {slug}"'
        )
    return 0


def cmd_workforce_search(
    args: argparse.Namespace,
    *,
    dependencies: WorkforceDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    query = " ".join(str(args.query or "").casefold().split())
    if not query:
        raise ValueError("workforce search query is required")
    tokens = frozenset(_SEARCH_TOKENS.findall(query))
    store_instance = dependencies.store_factory()
    workers = store_instance.list_workforce_workers(
        state=str(getattr(args, "state", "") or ""),
        limit=1000,
    )
    contracts = {
        item.agent_id: item.to_dict() for item in workforce_index_snapshot(store_instance).contracts
    }
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for worker in workers:
        contract = contracts[str(worker["agent_slug"])]
        corpus = json.dumps(contract, ensure_ascii=False, sort_keys=True).casefold()
        corpus_tokens = frozenset(_SEARCH_TOKENS.findall(corpus))
        score = len(tokens & corpus_tokens)
        if query in corpus:
            score += max(2, len(tokens))
        slug = str(worker["agent_slug"])
        label = str(worker["display_label"]).casefold()
        if query in (slug, label):
            score += 100
        elif query in slug:
            score += 40
        elif query in label:
            score += 20
        if score:
            ranked.append((score, str(worker["agent_slug"]), worker))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    result = [{**worker, "score": score} for score, _slug, worker in ranked[: args.limit]]
    payload = {"query": query, "count": len(result), "workers": result}
    if args.json:
        _emit(payload, as_json=True, dependencies=dependencies)
    else:
        for worker in result:
            print(f"{worker['score']}\t{_worker_line(worker)}")
    return 0


def _comparison_payload(
    args: argparse.Namespace,
    *,
    dependencies: WorkforceDependencies,
) -> dict[str, Any]:
    store_instance = dependencies.store_factory()
    snapshot = workforce_index_snapshot(store_instance)
    by_slug = {item.agent_id: item for item in snapshot.contracts}
    worker = str(store_instance.get_workforce_worker(args.worker)["agent_slug"])
    if worker not in by_slug:
        raise KeyError("workforce worker not found")
    comparisons = nearest_workers(by_slug[worker], snapshot.contracts, limit=int(args.limit))
    return {
        "worker": worker,
        "workforce_count": snapshot.worker_count,
        "contract_fingerprint": snapshot.contract_fingerprint,
        "authority": "read_only_recommendation",
        "comparisons": [item.as_dict() for item in comparisons],
    }


def cmd_workforce_duplicates(
    args: argparse.Namespace,
    *,
    dependencies: WorkforceDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    payload = _comparison_payload(args, dependencies=dependencies)
    if args.json:
        _emit(payload, as_json=True, dependencies=dependencies)
    else:
        print(
            f"{payload['worker']}	compared={payload['workforce_count'] - 1}"
            "	authority=read-only"
        )
        for item in payload["comparisons"]:
            print(
                f"{item['score']:.3f}	{item['right']}	{item['recommendation']}"
                f"	{'; '.join(item['reasons'])}"
            )
    return 0


def cmd_workforce_consolidate(
    args: argparse.Namespace,
    *,
    dependencies: WorkforceDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    snapshot = workforce_index_snapshot(dependencies.store_factory())
    candidates = consolidation_candidates(snapshot.contracts, limit=int(args.limit))
    payload = {
        "workforce_count": snapshot.worker_count,
        "contract_fingerprint": snapshot.contract_fingerprint,
        "authority": "read_only_recommendation",
        "automatic_mutation": False,
        "candidates": [item.as_dict() for item in candidates],
    }
    if args.json:
        _emit(payload, as_json=True, dependencies=dependencies)
    else:
        print(
            f"workforce={snapshot.worker_count}	candidates={len(candidates)}"
            "	authority=read-only"
        )
        for item in payload["candidates"]:
            print(
                f"{item['score']:.3f}	{item['left']}	{item['right']}"
                f"	{item['recommendation']}"
            )
    return 0


def _confirmation(action: str, slug: str, target: str = "") -> str:
    if action == "merge":
        return f"MERGE {slug} INTO {target}"
    return f"{action.upper()} {slug}"


def cmd_workforce_transition(
    args: argparse.Namespace,
    *,
    dependencies: WorkforceDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    action = str(args.workforce_action).strip().casefold()
    slug = normalize_agent_slug(args.worker)
    target = str(getattr(args, "into", "") or "")
    if target:
        target = normalize_agent_slug(target)
    if action in {"suspend", "retire", "merge"}:
        expected = _confirmation(action, slug, target)
        if str(getattr(args, "confirm", "") or "") != expected:
            raise ValueError(f'confirmation required: --confirm "{expected}"')
    worker = dependencies.store_factory().transition_workforce_worker(
        slug,
        action=action,
        expected_revision=int(args.expected_revision),
        reason=str(args.reason),
        merged_into_worker_id=target,
        actor="operator",
        surface="cli",
    )
    payload = {"action": action, "worker": worker}
    if args.json:
        _emit(payload, as_json=True, dependencies=dependencies)
    else:
        print(f"{action}\t{_worker_line(worker)}")
    return 0


def cmd_hiring_list(
    args: argparse.Namespace,
    *,
    dependencies: WorkforceDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    cases = dependencies.store_factory().list_hiring_cases(
        status=str(getattr(args, "status", "") or ""),
        case_type=str(getattr(args, "type", "") or ""),
        limit=int(args.limit),
    )
    payload = {"count": len(cases), "hiring_cases": cases}
    if args.json:
        _emit(payload, as_json=True, dependencies=dependencies)
        return 0
    if _render.use_card_default(args):
        cards = [_hiring_summary_card(case) for case in cases]
        print(_render.render_cards(cards))
        return 0
    for case in cases:
        print(
            "\t".join(
                (
                    str(case["id"]),
                    str(case["case_type"]),
                    str(case["status"]),
                    str(case["proposed_slug"]),
                    str(case["risk_tier"]),
                    str(case["work_unit_id"]),
                )
            )
        )
    return 0


def _hiring_summary_card(case: dict[str, Any]) -> _render.Card:
    title = str(case.get("proposed_slug") or "Unnamed candidate")
    subtitle = f"{case.get('case_type') or 'hire'!s} · {case.get('status') or 'unknown'!s}"
    return _render.from_mapping(
        title=title,
        subtitle=subtitle,
        fields=(
            ("Case", case.get("id") or "—"),
            ("Risk", case.get("risk_tier") or "standard"),
            ("Work unit", case.get("work_unit_id") or "—"),
            ("Created", case.get("created_at") or "—"),
            ("Approved by", case.get("human_approved_by") or "—"),
        ),
    )


def cmd_hiring_show(
    args: argparse.Namespace,
    *,
    dependencies: WorkforceDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    case = dependencies.store_factory().get_hiring_case(args.case_id)
    if args.json:
        _emit(case, as_json=True, dependencies=dependencies)
        return 0
    if _render.use_card_default(args):
        print(_hiring_detail_card(case).render())
        return 0
    print(
        f"{case['id']}\t{case['case_type']}\t{case['status']}\t{case['proposed_slug']}\t{case['risk_tier']}"
    )
    print("gap\t" + json.dumps(case["gap_evidence"], ensure_ascii=False, sort_keys=True))
    print(
        "duplicates\t" + json.dumps(case["duplicate_evidence"], ensure_ascii=False, sort_keys=True)
    )
    print("contract\t" + json.dumps(case["contract_evidence"], ensure_ascii=False, sort_keys=True))
    print("critic\t" + json.dumps(case["critic_evidence"], ensure_ascii=False, sort_keys=True))
    print("models\t" + json.dumps(case["model_evidence"], ensure_ascii=False, sort_keys=True))
    return 0


def _hiring_detail_card(case: dict[str, Any]) -> _render.Card:
    title = str(case.get("proposed_slug") or "Unnamed candidate")
    subtitle = f"{case.get('case_type') or 'hire'!s} · {case.get('status') or 'unknown'!s}"
    sections: list[tuple[str, Any]] = []
    for field_name, label in _render.HIRING_EVIDENCE_LABELS:
        body = case.get(field_name) or {}
        sections.append((label, body))
    return _render.from_mapping(
        title=title,
        subtitle=subtitle,
        fields=(
            ("Case", case.get("id") or "—"),
            ("Risk", case.get("risk_tier") or "standard"),
            ("Work unit", case.get("work_unit_id") or "—"),
            ("Created", case.get("created_at") or "—"),
            ("Decided", case.get("decided_at") or "—"),
            ("Applied", case.get("applied_at") or "—"),
            ("Approved by", case.get("human_approved_by") or "—"),
            ("Target worker", case.get("target_worker_id") or "—"),
        ),
        sections=sections,
        notes=("Full evidence loaded from the exact hiring-case response.",)
        if case.get("evidence_included")
        else (),
    )


def cmd_hiring_approve(
    args: argparse.Namespace,
    *,
    dependencies: WorkforceDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    expected = f"APPROVE {args.case_id}"
    if str(args.confirm or "") != expected:
        raise ValueError(f'confirmation required: --confirm "{expected}"')
    workforce_store = dependencies.store_factory()
    case = workforce_store.approve_hiring_case(
        args.case_id,
        approved_by=str(args.approved_by),
    )
    worker = apply_approved_hiring_case(workforce_store, case["id"])
    case = workforce_store.get_hiring_case(case["id"])
    payload = {"action": "approve", "hiring_case": case, "worker": worker}
    if args.json:
        _emit(payload, as_json=True, dependencies=dependencies)
    else:
        print(
            f"approved-and-applied\t{case['id']}\tworker={worker['agent_slug']}"
            f"\tby={case['human_approved_by']}"
        )
    return 0


__all__ = [
    "WorkforceDependencies",
    "cmd_contractor_list",
    "cmd_hiring_approve",
    "cmd_hiring_list",
    "cmd_hiring_show",
    "cmd_workforce_consolidate",
    "cmd_workforce_duplicates",
    "cmd_workforce_list",
    "cmd_workforce_search",
    "cmd_workforce_show",
    "cmd_workforce_transition",
]
