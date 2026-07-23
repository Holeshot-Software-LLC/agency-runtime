"""Bounded CLI entry points for quantitative Agency evaluations."""

from __future__ import annotations

import argparse
from pathlib import Path

from agency_runtime.cli._common import print_json
from agency_runtime.core.config import load_config
from agency_runtime.core.evals.comparative import (
    evaluate_comparative_outcomes,
    load_comparative_jsonl,
)
from agency_runtime.core.evals.full_roster import (
    DEFAULT_CANDIDATE_LIMIT,
    run_full_roster_selection_eval,
)
from agency_runtime.core.evals.product_one_shot import run_product_trial
from agency_runtime.core.evals.product_scenarios import product_scenario
from agency_runtime.core.evals.upstream_architecture import (
    run_upstream_architecture_comparison,
)
from agency_runtime.core.evals.workforce_selection import CASES, run_workforce_inference_eval
from agency_runtime.core.host_capabilities import canonicalize_tool_capabilities
from agency_runtime.core.roster.workforce import workforce_index_snapshot
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce.inference import configured_workforce_providers
from agency_runtime.core.workforce.staffing_verifier import StaffingContext


def _eval_staffing_context(args: argparse.Namespace, generation: int) -> StaffingContext:
    """Build one canonical fail-closed capability context for an eval case."""

    available, unknown = canonicalize_tool_capabilities(args.available_tool)
    if unknown:
        raise ValueError("unknown --available-tool capability: " + ", ".join(unknown))
    return StaffingContext(
        args.host,
        args.platform,
        frozenset(available),
        generation,
    )


def _workforce_cases(args: argparse.Namespace):
    requested = tuple(dict.fromkeys(getattr(args, "case", ()) or ()))
    if requested and args.all:
        raise ValueError("--case and --all cannot be combined")
    if not requested:
        return CASES if args.all else CASES[:3]
    by_id = {case.case_id: case for case in CASES}
    return tuple(by_id[case_id] for case_id in requested)


def cmd_eval_compare(args: argparse.Namespace) -> int:
    """Validate and summarize paired native-only and Agency outcome evidence."""

    observations = load_comparative_jsonl(Path(args.input))
    print_json(evaluate_comparative_outcomes(observations))
    return 0


def cmd_eval_full_roster(args: argparse.Namespace) -> int:
    """Run the bounded complete-roster contract evaluation."""

    report = run_full_roster_selection_eval(candidate_limit=args.candidate_limit)
    if args.no_details:
        report = {key: value for key, value in report.items() if key != "details"}
    if args.json:
        print_json(report)
    else:
        status = "passed" if report["passed"] else "failed"
        roster = report["roster"]
        print(
            f"full-roster eval {status}: workforce={roster['workforce_total']} "
            f"upstream={roster['manifest_approved']} "
            f"contractors={roster['packaged_contractors']} "
            f"quarantined={roster['manifest_quarantined']} "
            f"divisions={roster['division_count']}"
        )
        for gate in report["gates"]:
            marker = "ok" if gate["passed"] else "FAIL"
            print(
                f"{marker}\t{gate['metric']}={gate['value']} {gate['operator']} {gate['threshold']}"
            )
        print("evidence\tcontract-only; no task-outcome or superiority claim")
    return 0 if report["passed"] else 1


def cmd_eval_upstream_architecture(args: argparse.Namespace) -> int:
    """Describe the pinned upstream and Agency architecture contracts."""

    report = run_upstream_architecture_comparison()
    if args.json:
        print_json(report)
    else:
        upstream = report["upstream"]
        result = report["result"]
        print(
            "upstream architecture comparison: "
            f"revision={upstream['revision']} capabilities="
            f"{result['evaluated_capability_count']}"
        )
        print("architecture\tAgency has the stronger explicit machine-enforced contract")
        print(f"boundary\t{report['evidence']['limitation']}")
    return 0


def cmd_eval_workforce(args: argparse.Namespace) -> int:
    """Run the explicitly authorized configured-inference selection corpus."""

    if args.confirm_live_inference != "RUN LIVE WORKFORCE EVAL":
        raise ValueError(
            'confirmation required: --confirm-live-inference "RUN LIVE WORKFORCE EVAL"'
        )
    store = Store()
    config = load_config()
    if not configured_workforce_providers(config, stage="combined"):
        raise ValueError("configured workforce inference provider is required")
    snapshot = workforce_index_snapshot(store)
    if snapshot.worker_count == 0:
        raise ValueError(
            "configured workforce inference evaluation requires a populated audited workforce"
        )
    selected_cases = _workforce_cases(args)
    context = _eval_staffing_context(args, snapshot.generation)
    report = run_workforce_inference_eval(
        snapshot,
        config=config,
        context=context,
        cases=selected_cases,
    )
    if args.no_details:
        report = {key: value for key, value in report.items() if key != "details"}
    if args.json:
        print_json(report)
    else:
        status = "passed" if report["passed"] else "failed"
        print(
            f"workforce inference eval {status}: {report['passed_count']}/"
            f"{report['case_count']} cases, workers={report['workforce']['count']}, "
            f"provider-calls<={report['maximum_provider_calls']}"
        )
        for item in report.get("details", []):
            marker = "ok" if item["passed"] else "FAIL"
            print(f"{marker}\t{item['case_id']}\t{','.join(item['selected_workers'])}")
    return 0 if report["passed"] else 1


def cmd_eval_product(args: argparse.Namespace) -> int:
    """Execute and independently grade one exact-confirmed native-host product trial."""

    scenario = product_scenario(args.scenario)
    report = run_product_trial(
        scenario,
        trial_id=args.trial_id,
        host=args.host,
        mode=args.mode,
        workspace=Path(args.workspace),
        timeout=args.timeout,
        confirm=args.confirm_live_product_eval,
        model=args.model,
    )
    payload = report.as_dict()
    if args.json:
        print_json(payload)
    else:
        marker = "passed" if report.passed else "failed"
        execution = payload["host_execution"]
        validation = payload["validation"]
        print(
            f"product eval {marker}: scenario={report.scenario_id} "
            f"host={report.host} mode={report.mode} trial={report.trial_id}"
        )
        print(
            f"host	status={execution['status']} "
            f"runtime-contract={execution['runtime_contract_passed']} "
            f"duration-ms={execution['duration_ms']}"
        )
        print(
            f"artifacts	validation={validation['passed']} "
            f"digest={validation.get('workspace_digest', 'unavailable')}"
        )
        print(f"evidence	{payload['claim_boundary']}")
    return 0 if report.passed else 1


__all__ = [
    "DEFAULT_CANDIDATE_LIMIT",
    "cmd_eval_compare",
    "cmd_eval_full_roster",
    "cmd_eval_product",
    "cmd_eval_upstream_architecture",
    "cmd_eval_workforce",
]
