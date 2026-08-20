"""One fixed producer/verifier work shape for the Claude outcome canary."""

from __future__ import annotations

from agency_runtime.core.child_delivery_evidence import (
    _outcome_pair_role_marker,
    _verifier_semantic_marker,
)

ACCEPTED_OUTCOME_CONTRACTOR_SLUG = "typescript-application-engineer"
ACCEPTED_OUTCOME_CONFIRMATION = "RUN LIVE claude ACCEPTED-OUTCOME CANARY"

_PRODUCER_WORK_UNIT = (
    "Implement one self-contained TypeScript function `parsePort(value: string): number`. "
    "It must accept only canonical decimal integers from 1 through 65535 and throw a "
    "descriptive Error for every other input. Return only the implementation and three "
    "short usage examples. Do not review, test, delegate, use tools, modify files, or call "
    "external services."
)

_VERIFIER_WORK_UNIT = (
    "Independently review the producer response below against this contract: one "
    "self-contained TypeScript `parsePort(value: string): number` function; only canonical "
    "decimal integers 1 through 65535 accepted; every other input throws a descriptive "
    "Error; implementation plus three short usage examples. Do not implement, edit, "
    "delegate, use tools, modify files, or call external services. Explain the decisive "
    "evidence concisely, then end with exactly one of the two machine-readable JSON lines "
    "specified below."
)


def build_accepted_outcome_canary_prompt(pair_id: str) -> str:
    """Render the exact serial two-child protocol for one random pair identity."""

    producer_marker = _outcome_pair_role_marker(pair_id=pair_id, role="producer")
    verifier_marker = _outcome_pair_role_marker(pair_id=pair_id, role="verifier")
    accepted = _verifier_semantic_marker(pair_id=pair_id, decision="accepted")
    rejected = _verifier_semantic_marker(pair_id=pair_id, decision="rejected")
    producer_task = f"{_PRODUCER_WORK_UNIT}\n{producer_marker}"
    verifier_prefix = f"{_VERIFIER_WORK_UNIT}\n{verifier_marker}"
    return (
        "This is one bounded Agency Runtime accepted-outcome canary. Use Claude's native "
        "Agent tool exactly twice, serially, with general-purpose children. Do not call any "
        "other tool, start any other child, retry a call, or run the two calls in parallel.\n\n"
        "First, call Agent once with the exact producer prompt between "
        "<producer-prompt> tags. Pass the enclosed text verbatim and do not include the "
        "tags themselves:\n"
        f"<producer-prompt>\n{producer_task}\n</producer-prompt>\n\n"
        "Wait for that child to finish. Then call Agent once with one verifier prompt "
        "formed in this exact order: the text between <verifier-prefix> tags, a newline, "
        "the producer child's complete response copied verbatim, and no other material. "
        "Pass the prefix text without the tags:\n"
        f"<verifier-prefix>\n{verifier_prefix}\n\n"
        "The verifier must end with exactly one of these JSON lines and must not emit both:\n"
        f"{accepted}\n{rejected}\n"
        "Producer response follows verbatim after this line:\n"
        "</verifier-prefix>\n\n"
        "After the verifier returns, provide a concise final summary using the authoritative "
        "Agency header supplied by the installed hook, then stop. Do not expose secrets or "
        "modify any file."
    )


__all__ = [
    "ACCEPTED_OUTCOME_CONFIRMATION",
    "ACCEPTED_OUTCOME_CONTRACTOR_SLUG",
    "build_accepted_outcome_canary_prompt",
]
