"""Bounded CLI entry points for quantitative Agency evaluations."""

from __future__ import annotations

import argparse
from pathlib import Path

from agency_runtime.cli._common import print_json
from agency_runtime.core.evals.comparative import (
    evaluate_comparative_outcomes,
    load_comparative_jsonl,
)
from agency_runtime.core.evals.full_roster import (
    DEFAULT_CANDIDATE_LIMIT,
    run_full_roster_selection_eval,
)


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
            f"full-roster eval {status}: approved={roster['manifest_approved']} "
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


__all__ = ["DEFAULT_CANDIDATE_LIMIT", "cmd_eval_compare", "cmd_eval_full_roster"]
