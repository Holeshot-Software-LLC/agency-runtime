"""Agent-chaos harness with explicit failure oracles (AR-362).

Experiments inject one owned fault into a dedicated, rolled-back runtime and
judge the system's response with an explicit oracle; every run seals a
receipt. See ``contracts`` for the five records, ``safety`` for the envelope
that keeps experiments off live user turns, ``experiments`` for the shipped
scenarios, and ``runner`` for the CLI and battery-facing entry points.
"""

from __future__ import annotations

from agency_runtime.core.chaos.contracts import (
    CHAOS_GATE_VARIABLE,
    CHAOS_RECEIPT_SCHEMA,
    CHAOS_REPORT_SCHEMA,
    CHAOS_SESSION_PREFIX,
    CHAOS_SUMMARY_SCHEMA,
    VERDICT_FAIL,
    VERDICT_PASS,
    ChaosSafetyError,
    Effect,
    Experiment,
    Oracle,
    Receipt,
    Safety,
    Verdict,
    project_chaos_receipt,
)
from agency_runtime.core.chaos.experiments import (
    RUNNER_HARD_KILL,
    STAFFING_WINDOW,
    StaffingShape,
    staffing_shapes,
)
from agency_runtime.core.chaos.runner import (
    CHAOS_EXPERIMENT_NAMES,
    CHAOS_EXPERIMENTS,
    chaos_report_summary,
    default_receipt_root,
    resolve_experiments,
    run_chaos_cli,
    run_chaos_experiments,
    run_experiment,
    write_chaos_receipt,
)
from agency_runtime.core.chaos.safety import ChaosEnvelope, arm_safety, live_database_paths

__all__ = [
    "CHAOS_EXPERIMENTS",
    "CHAOS_EXPERIMENT_NAMES",
    "CHAOS_GATE_VARIABLE",
    "CHAOS_RECEIPT_SCHEMA",
    "CHAOS_REPORT_SCHEMA",
    "CHAOS_SESSION_PREFIX",
    "CHAOS_SUMMARY_SCHEMA",
    "RUNNER_HARD_KILL",
    "STAFFING_WINDOW",
    "VERDICT_FAIL",
    "VERDICT_PASS",
    "ChaosEnvelope",
    "ChaosSafetyError",
    "Effect",
    "Experiment",
    "Oracle",
    "Receipt",
    "Safety",
    "StaffingShape",
    "Verdict",
    "arm_safety",
    "chaos_report_summary",
    "default_receipt_root",
    "live_database_paths",
    "project_chaos_receipt",
    "resolve_experiments",
    "run_chaos_cli",
    "run_chaos_experiments",
    "run_experiment",
    "staffing_shapes",
    "write_chaos_receipt",
]
