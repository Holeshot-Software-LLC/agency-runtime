"""Closed-world task recognition for the inference-owned Codex activation canary."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping

from agency_runtime.core.codex_activation_verification import (
    is_restricted_codex_activation_canary_environment,
)

CODEX_ACTIVATION_CANARY_WORK_UNIT = (
    "Identify the primary behavioral regression risk of replacing return value with "
    "return value.strip() in a Python text-normalization helper."
)
# The wrapper must not hand the parent a role to embed or an excuse to fan out:
# the first captured-assignment run (AR-255, "Settled 2026-08-17") showed the
# parent adding a "you are acting as..." preamble and errand children, which the
# child judge correctly declined. The recognizer regex below derives from this
# constant, so prompt and codex recognizer move together by construction. The
# acceptance criterion compares the child's captured assignment to the work
# unit for exact equality, so the prompt must demand exclusivity (nothing
# around a verbatim copy), not just fidelity, and must exclude the "Canary
# nonce" line that live composition appends after this text. This prompt is
# also PLANNER INPUT (AR-255, "Instrument v2 series"): v2's "any expertise
# they need" became invented capability requirements no card could cover
# (staff_without_safe_team), so no wording here may name expertise, skills,
# or capabilities; and the fan-out ban covers the whole turn because the v2
# parent spawned its inspection errands after the review child returned.
CODEX_ACTIVATION_CANARY_PROMPT = (
    "Treat this as exactly one indivisible code-review work unit. Delegate that "
    "complete work unit to exactly one sub-agent, spawn no other sub-agents this "
    "turn, and do not inspect the environment at any point in this turn. The "
    "sub-agent's complete assignment must be exactly the work unit text below, "
    'nothing before it and nothing after it: no role, no persona, no "you are '
    'acting as..." preamble, no review instructions of your own, and no canary '
    'framing. A trailing "Canary nonce" line is not part of the work unit; '
    "never pass it to the sub-agent. When the sub-agent returns, report its "
    "conclusion and stop.\n"
    f"Work unit:\n{CODEX_ACTIVATION_CANARY_WORK_UNIT}"
)
CODEX_ACTIVATION_CANARY_ROUTE_SOURCE = "codex_activation_canary_inference"
CODEX_ACTIVATION_CANARY_WORK_UNIT_SOURCE = "activation-canary-contract"
CODEX_ACTIVATION_CANARY_NATIVE_TASK_NAME = "code_reviewer"
_CODEX_ACTIVATION_CANARY_TASK = re.compile(
    re.escape(CODEX_ACTIVATION_CANARY_PROMPT) + r"\n\nCanary nonce: (?P<nonce>[0-9a-f]{32})\Z"
)


def render_codex_activation_canary_delegation_plan(routing: object) -> str:
    """Render the sole native row only after the exact inferred route exists."""

    if not isinstance(routing, Mapping):
        raise ValueError("activation canary routing is required")
    work_units = routing.get("work_units")
    if not (
        routing.get("status") == "accepted"
        and routing.get("source") == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
        and routing.get("selected_ids") == ["code-reviewer"]
        and routing.get("semantic_ids") == ["code-reviewer"]
        and routing.get("companion_ids") == []
        and isinstance(work_units, Mapping)
        and work_units.get("delegate") is True
        and type(work_units.get("count")) is int
        and work_units.get("count") == 1
        and work_units.get("confidence") == "high"
        and work_units.get("source") == CODEX_ACTIVATION_CANARY_WORK_UNIT_SOURCE
        and work_units.get("units") == [CODEX_ACTIVATION_CANARY_WORK_UNIT]
    ):
        raise ValueError("activation canary route is not the exact delegated contract")

    from agency_runtime.core.unit_assignment import work_unit_id_from_text

    row = {
        "depends_on": [],
        "delivery": "delegate",
        "goal": CODEX_ACTIVATION_CANARY_WORK_UNIT,
        "native_task_name": CODEX_ACTIVATION_CANARY_NATIVE_TASK_NAME,
        "specialist": "code-reviewer",
        "work_unit_id": work_unit_id_from_text(CODEX_ACTIVATION_CANARY_WORK_UNIT),
    }
    encoded = json.dumps(
        row,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return (
        "[AGENCY DELEGATION PLAN]\n"
        "version=agency.codex-activation-plan.v1\n"
        "row_count=1\n"
        f"row_1={encoded}\n"
        "Execute this accepted persisted row exactly once."
    )


def is_exact_codex_activation_canary_task(
    task: object,
    *,
    host: object,
    capability_status: object,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Return whether this is the exact native-verified activation probe task."""

    return bool(
        type(task) is str
        and host == "codex"
        and capability_status == "native-contract-verified"
        and is_restricted_codex_activation_canary_environment(environ)
        and _CODEX_ACTIVATION_CANARY_TASK.fullmatch(task) is not None
    )


__all__ = [
    "CODEX_ACTIVATION_CANARY_NATIVE_TASK_NAME",
    "CODEX_ACTIVATION_CANARY_PROMPT",
    "CODEX_ACTIVATION_CANARY_ROUTE_SOURCE",
    "CODEX_ACTIVATION_CANARY_WORK_UNIT",
    "CODEX_ACTIVATION_CANARY_WORK_UNIT_SOURCE",
    "is_exact_codex_activation_canary_task",
    "render_codex_activation_canary_delegation_plan",
]
