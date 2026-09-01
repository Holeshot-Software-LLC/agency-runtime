"""Honest in-turn disclosure when Agency's own staffing or tooling fell short.

AR-356: a fail-open turn used to deliver the steward kernel and nothing else,
so the parent model had no way to know it was unstaffed and could imply
expertise it was never dealt. The disclosure line below is appended to the
capsule on fail-open turns only; staffed turns never see it, so their capsule
bytes are unchanged. The wording is a versioned, hash-pinned contract exactly
like the resident kernel: changing it is a deliberate, test-visible act.

The same honesty rule extends to tooling: a card's requested capability is not
proof its tools were available (cards already say "availability must be proven
before use"). When a specialist is loaded whose required tools this host has not
proven, the load discloses the degradation instead of letting the model imply
capability it lacks.

Everything rendered here is content-free: reason codes come from the
allowlisted preflight-failure vocabulary, tool labels from the governed
capability vocabulary, never from provider output or error text.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from typing import Final

from agency_runtime.core.preflight_failure import PREFLIGHT_FAILURE_REASONS

FAIL_OPEN_DISCLOSURE_VERSION: Final[int] = 1
# The whole rendered line stays well under this; the bound exists so a future
# reason-code list can never grow the capsule unexpectedly.
MAX_FAIL_OPEN_DISCLOSURE_CHARS: Final[int] = 512
MAX_DISCLOSED_REASON_CODES: Final[int] = 4
MAX_DISCLOSED_TOOLS: Final[int] = 8

FAIL_OPEN_DISCLOSURE_MARKER: Final[str] = "[Agency staffing failed this turn"
FAIL_OPEN_DISCLOSURE_TEMPLATE: Final[str] = (
    "[Agency staffing failed this turn: {reason}] No specialist was staffed; you are "
    "proceeding under the steward alone. Do not imply specialist expertise, staffing, or "
    "tool access this turn never received; say so if it matters to the answer."
)
FAIL_OPEN_DISCLOSURE_HASH: Final[str] = hashlib.sha256(
    FAIL_OPEN_DISCLOSURE_TEMPLATE.encode("utf-8")
).hexdigest()

TOOL_DEGRADATION_MARKER: Final[str] = "[Agency tool degradation"
TOOL_DEGRADATION_UNPROVEN_TEMPLATE: Final[str] = (
    "[Agency tool degradation: '{slug}' requires {tools}, and this host has not proven "
    "any tool availability for this turn] Treat those capabilities as absent until you "
    "prove them yourself; do not imply them."
)
TOOL_DEGRADATION_MISSING_TEMPLATE: Final[str] = (
    "[Agency tool degradation: '{slug}' requires {tools}, which this host did not prove "
    "available this turn] Treat those capabilities as absent; do not imply them."
)
TOOL_DEGRADATION_HASH: Final[str] = hashlib.sha256(
    (TOOL_DEGRADATION_UNPROVEN_TEMPLATE + "\n" + TOOL_DEGRADATION_MISSING_TEMPLATE).encode("utf-8")
).hexdigest()

_UNKNOWN_REASON: Final[str] = "preflight_failed"
_REASON_CODE = re.compile(r"^[a-z][a-z0-9_]{1,95}$")
_TOOL_LABEL = re.compile(r"^[a-z0-9][a-z0-9._+-]{0,63}$")


def _bounded_codes(values: Iterable[object], *, limit: int, pattern: re.Pattern[str]) -> list[str]:
    """Return allowlisted, deduplicated, bounded tokens; drop anything else silently."""

    result: list[str] = []
    for value in values:
        if isinstance(value, (bytes, bytearray)) or not isinstance(value, str):
            continue
        token = value.strip().casefold()
        if pattern.fullmatch(token) is None or token in result:
            continue
        result.append(token)
        if len(result) >= limit:
            break
    return result


def disclosed_reason_class(
    reason_code: object,
    staffing_reason_codes: Iterable[object] = (),
) -> str:
    """Render the bounded reason class for a fail-open turn.

    ``reason_code`` must be one of the persisted preflight-failure reasons;
    anything else collapses to ``preflight_failed`` so a malformed value can
    never leak into the capsule. Staffing codes are allowlisted tokens (the
    verifier/critic vocabulary such as ``staffing_critic_rejected``), bounded
    in count, and never carry provider detail.
    """

    reason = str(reason_code or "").strip().casefold()
    if reason not in PREFLIGHT_FAILURE_REASONS:
        reason = _UNKNOWN_REASON
    codes = _bounded_codes(
        staffing_reason_codes,
        limit=MAX_DISCLOSED_REASON_CODES,
        pattern=_REASON_CODE,
    )
    if not codes:
        return reason
    return f"{reason}; staffing: {', '.join(codes)}"


def render_fail_open_disclosure(
    reason_code: object,
    staffing_reason_codes: Iterable[object] = (),
) -> str:
    """Return the one bounded disclosure line for a fail-open turn."""

    rendered = FAIL_OPEN_DISCLOSURE_TEMPLATE.format(
        reason=disclosed_reason_class(reason_code, staffing_reason_codes)
    )
    if len(rendered) > MAX_FAIL_OPEN_DISCLOSURE_CHARS:
        # Only reachable if the template itself grows; keep the invariant loud
        # in tests rather than truncating a contract line mid-word.
        raise RuntimeError("fail-open disclosure exceeds its bounded budget")
    return rendered


def render_tool_degradation(
    slug: object,
    required_tools: Iterable[object],
    *,
    proven_capabilities: Iterable[object] | None,
) -> str:
    """Return the tool-degradation disclosure for one loaded specialist, or "".

    ``proven_capabilities`` is the host's proven capability list for this turn.
    ``None`` means the host proved nothing (no capability receipt reached the
    store for the turn); an empty or partial list means specific tools are
    missing. A card without required tools, or one whose tools are all proven,
    renders nothing — staffed turns and ordinary loads are byte-identical.
    """

    normalized_slug = str(slug or "").strip()
    required = _bounded_codes(required_tools, limit=MAX_DISCLOSED_TOOLS, pattern=_TOOL_LABEL)
    if not normalized_slug or not required:
        return ""
    if proven_capabilities is None:
        return TOOL_DEGRADATION_UNPROVEN_TEMPLATE.format(
            slug=normalized_slug,
            tools=", ".join(required),
        )
    proven = set(_bounded_codes(proven_capabilities, limit=64, pattern=_TOOL_LABEL))
    missing = [tool for tool in required if tool not in proven]
    if not missing:
        return ""
    return TOOL_DEGRADATION_MISSING_TEMPLATE.format(
        slug=normalized_slug,
        tools=", ".join(missing),
    )


__all__ = [
    "FAIL_OPEN_DISCLOSURE_HASH",
    "FAIL_OPEN_DISCLOSURE_MARKER",
    "FAIL_OPEN_DISCLOSURE_TEMPLATE",
    "FAIL_OPEN_DISCLOSURE_VERSION",
    "MAX_DISCLOSED_REASON_CODES",
    "MAX_DISCLOSED_TOOLS",
    "MAX_FAIL_OPEN_DISCLOSURE_CHARS",
    "TOOL_DEGRADATION_HASH",
    "TOOL_DEGRADATION_MARKER",
    "TOOL_DEGRADATION_MISSING_TEMPLATE",
    "TOOL_DEGRADATION_UNPROVEN_TEMPLATE",
    "disclosed_reason_class",
    "render_fail_open_disclosure",
    "render_tool_degradation",
]
