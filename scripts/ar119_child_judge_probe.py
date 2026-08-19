"""Read-only child-judge probe for AR-119.

Reproduces exactly the call ``staff_native_child`` makes:

    query_judge(task, eligible_catalog, config=snapshot.config,
                max_selected=MAX_INFERENCE_TEAM_CARDS,
                candidate_scope="complete")

It never calls ``_unstaffed``, ``_record_decision`` or
``_record_captured_assignment``, so it writes nothing to the Store and can
never mint a delivery receipt. Its output is a diagnostic, never Rule-4
evidence (ADR-0156).

Why the universe is rebuilt from a recorded decision rather than re-filtered:
re-deriving eligibility with ``filter_eligible_catalog(capability_status="")``
yields 33 agents where the canary's child judge saw 71, and nothing in the
result says so. Measuring a different universe is the exact failure mode this
probe exists to avoid, so the rebuild is validated against the recorded
``offered_agent_digest`` and the probe refuses to run on a mismatch.

Usage::

    python scripts/ar119_child_judge_probe.py --decision <routing_decision_id>
    python scripts/ar119_child_judge_probe.py --provider claude-subscription --runs 3

`--provider` restricts the inference chain to one configured provider. This
matters: `agency.yaml` leaves `judge.model` empty, so an unconstrained call
takes the head of the provider list, and the answer observed on 2026-08-19
depended on which provider answered.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

from agency_runtime.core.activation_canary_contract import (
    CODEX_ACTIVATION_CANARY_WORK_UNIT,
)
from agency_runtime.core.config import load_config
from agency_runtime.core.native_child_staffing import MAX_INFERENCE_TEAM_CARDS
from agency_runtime.core.routing_snapshot import capture_routing_snapshot
from agency_runtime.core.selector.judge import query_judge
from agency_runtime.core.store.sqlite import Store

# The 2026-08-19 claude-canary child decision: the 138-char control unit over a
# 71-agent universe, recorded with its own offered-agent digest.
DEFAULT_DECISION_ID = "5c963e09-fcff-4989-9d45-b2e95401b82c"

_CATALOG_KEYS = ("slug", "id", "name", "agent_slug")


def _default_db() -> Path:
    return Path(os.path.expanduser("~/.agency-runtime/agency.db"))


def _recorded_universe(db: Path, decision_id: str) -> tuple[list[str], str]:
    """Read one decision's offered-agent list and digest, read-only."""

    uri = f"file:{db}?mode=ro"
    with sqlite3.connect(uri, uri=True) as con:
        row = con.execute(
            "SELECT decision FROM routing_decisions WHERE id = ?", (decision_id,)
        ).fetchone()
    if row is None:
        raise SystemExit(f"routing decision {decision_id} not found in {db}")
    decision = json.loads(row[0])
    joined = decision.get("offered_agent_ids")
    digest = decision.get("offered_agent_digest")
    if not joined or not digest:
        raise SystemExit(
            f"decision {decision_id} recorded no offered-agent universe; "
            "pick a decision whose judge ran over the complete scope"
        )
    return joined.split("~"), digest


def _rebuild_catalog(catalog: list[dict[str, Any]], slugs: list[str]) -> list[dict[str, Any]]:
    wanted = set(slugs)
    rebuilt: list[dict[str, Any]] = []
    for entry in catalog:
        if not isinstance(entry, dict):
            continue
        for key in _CATALOG_KEYS:
            value = entry.get(key)
            if value:
                if value in wanted:
                    rebuilt.append(entry)
                break
    return rebuilt


def _restrict_provider(config: Any, provider: str) -> Any:
    names = [entry.name for entry in config.providers]
    kept = tuple(entry for entry in config.providers if entry.name == provider)
    if not kept:
        raise SystemExit(f"provider {provider!r} is not configured; available: {names}")
    return dataclasses.replace(config, providers=kept)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--decision", default=DEFAULT_DECISION_ID)
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--provider", default="", help="Restrict the chain to one provider")
    parser.add_argument("--task", default="", help="Work unit text (default: the canary unit)")
    parser.add_argument("--runs", type=int, default=1, help="Serialized repeats")
    parser.add_argument("--json", dest="json_path", type=Path, default=None)
    args = parser.parse_args(argv)

    db = args.db or _default_db()
    task = args.task or CODEX_ACTIVATION_CANARY_WORK_UNIT

    slugs, recorded_digest = _recorded_universe(db, args.decision)
    recomputed = hashlib.sha256("~".join(sorted(set(slugs))).encode("utf-8")).hexdigest()
    if recomputed != recorded_digest:
        raise SystemExit(
            "offered-agent digest mismatch: the recorded universe does not hash to "
            f"its own digest ({recomputed} != {recorded_digest})"
        )

    store = Store()
    config = load_config()
    snapshot = capture_routing_snapshot(store, config)
    catalog = _rebuild_catalog(list(snapshot.catalog), slugs)
    if len(catalog) != len(set(slugs)):
        raise SystemExit(
            f"rebuilt {len(catalog)} of {len(set(slugs))} recorded agents; the roster has "
            "changed since that decision, so this probe would measure a different universe"
        )

    judge_config = snapshot.config
    if args.provider:
        judge_config = _restrict_provider(judge_config, args.provider)

    print(
        f"universe {len(catalog)} agents | digest {recorded_digest} VERIFIED | "
        f"provider {args.provider or '(config order)'} | task {len(task)} chars",
        flush=True,
    )

    results: list[dict[str, Any]] = []
    for index in range(1, args.runs + 1):
        started = time.monotonic()
        try:
            outcome = query_judge(
                task,
                catalog,
                config=judge_config,
                max_selected=MAX_INFERENCE_TEAM_CARDS,
                candidate_scope="complete",
            )
        except Exception as exc:  # failures are kept, per series discipline
            record = {"run": index, "error": f"{type(exc).__name__}: {exc}"}
        else:
            selected = outcome.get("selected_ids")
            record = {
                "run": index,
                "status": outcome.get("status"),
                "inference_mode": outcome.get("inference_mode"),
                "staffed": bool(selected),
                "selected_ids": selected,
                "candidate_count": outcome.get("candidate_count"),
                "confidence": outcome.get("confidence"),
                # Which provider ANSWERED. Never infer this from config order.
                "provider": outcome.get("provider"),
            }
        record["wall_s"] = round(time.monotonic() - started, 1)
        results.append(record)
        print(json.dumps(record), flush=True)

    if args.json_path is not None:
        payload = {
            "schema": "agency.ar119-child-judge-probe.v1",
            "decision_id": args.decision,
            "offered_agent_digest": recorded_digest,
            "universe_size": len(catalog),
            "task_chars": len(task),
            "requested_provider": args.provider,
            "runs": results,
        }
        args.json_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")

    staffed = sum(1 for item in results if item.get("staffed"))
    print(f"{staffed} staffed / {len(results)} runs", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
