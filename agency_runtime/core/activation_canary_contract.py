"""Closed-world task recognition for the inference-owned Codex activation canary."""

from __future__ import annotations

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
_CODEX_ACTIVATION_CANARY_TASK = re.compile(
    re.escape(CODEX_ACTIVATION_CANARY_PROMPT) + r"\n\nCanary nonce: (?P<nonce>[0-9a-f]{32})\Z"
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
    "CODEX_ACTIVATION_CANARY_PROMPT",
    "CODEX_ACTIVATION_CANARY_ROUTE_SOURCE",
    "CODEX_ACTIVATION_CANARY_WORK_UNIT",
    "CODEX_ACTIVATION_CANARY_WORK_UNIT_SOURCE",
    "is_exact_codex_activation_canary_task",
]
