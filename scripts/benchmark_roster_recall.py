#!/usr/bin/env python3
"""Explicit two-process recall benchmark; no staffing, hiring or host execution."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

from agency_runtime.core.config import load_config
from agency_runtime.core.installer import seed_starter_roster
from agency_runtime.core.private_paths import ensure_private_directory
from agency_runtime.core.provider_deadline import inference_deadline
from agency_runtime.core.roster.workforce import workforce_index_snapshot
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.structured_provider import invoke_structured_provider_result
from agency_runtime.core.workforce.inference import _run_hybrid_recall, _typed_shortlists
from agency_runtime.core.workforce.planning_contracts import parse_work_unit_plan
from agency_runtime.core.workforce.staffing_verifier import StaffingContext


def benchmark(directory: Path, host: str) -> dict:
    """Use a disposable packaged-roster Store, never the operator's database."""
    root = ensure_private_directory(directory)
    store = Store(root / "benchmark.db")
    seed_starter_roster(store)
    snapshot = workforce_index_snapshot(store, disabled_agents=())
    context = StaffingContext(
        host, "linux", frozenset({"repository-read", "native-delegation"}), snapshot.generation
    )
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Review a Python API backend for correctness.",
            "units": [
                {
                    "unit_id": "unit-api-review",
                    "outcome": "Review the API implementation and report concrete correctness defects.",
                    "artifact_kind": "review-report",
                    "lifecycle_phase": "review",
                    "domains": ["backend"],
                    "languages": ["python"],
                    "frameworks": [],
                    "required_capabilities": ["review"],
                    "authority": "review",
                    "mutation_scope": "read_only",
                    "risks": ["regression"],
                    "trust_boundaries": ["repository"],
                    "claims": [],
                    "depends_on": [],
                    "resources": ["repository"],
                    "required_tools": ["repository-read"],
                    "platforms": ["linux"],
                    "acceptance_evidence": ["Source-backed findings"],
                    "parallelization": "unspecified",
                }
            ],
        }
    )
    typed = _typed_shortlists(plan, snapshot.contracts, context=context)
    started = time.monotonic()
    with inference_deadline(started + 120):
        result, reranked, attempts = _run_hybrid_recall(
            plan=plan,
            typed_recall=typed,
            snapshot=snapshot,
            config=load_config(),
            context=context,
            invoker=invoke_structured_provider_result,
            embedding_invoker=None,
            turn_routing_context=None,
            catalog_cache_directory=root / "vectors",
        )
    safe_fields = (
        "stage",
        "status",
        "reason_code",
        "latency_ms",
        "input_count",
        "provider_call_count",
        "catalog_cache_hit",
        "requested_model",
        "actual_model",
    )
    return {
        "scope": "live recall only; packaged roster, no staffing/hiring/host execution",
        "host_context": host,
        "roster_count": snapshot.worker_count,
        "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
        "receipt": None if result is None else asdict(result.receipt),
        "candidate_ids": {}
        if result is None
        else {
            unit.unit_id: [candidate.agent_id for candidate in unit.additions]
            for unit in result.units
        },
        "reranked_ids": reranked,
        "attempts": [
            {field: getattr(attempt, field) for field in safe_fields} for attempt in attempts
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--directory",
        type=Path,
        required=True,
        help="Dedicated private benchmark directory; reuse for the warm process",
    )
    parser.add_argument(
        "--host", choices=("codex", "claude", "hermes", "openclaw", "zcode"), default="codex"
    )
    parser.add_argument(
        "--confirm-live-inference", required=True, choices=("RUN LIVE RECALL BENCHMARK",)
    )
    args = parser.parse_args()
    report = benchmark(args.directory, args.host)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["receipt"] and report["receipt"]["status"] == "applied" else 1


if __name__ == "__main__":
    raise SystemExit(main())
