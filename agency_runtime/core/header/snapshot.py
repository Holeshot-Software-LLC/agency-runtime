"""Header-snapshot framing shared by the hook bridge and the context-budget audit.

The hook bridge hands persistent hosts an exact current-turn header under a
marker line and a one-sentence instruction. Those strings used to live inline
in the bridge; they moved here so the per-turn context-budget audit (AR-355)
sizes the text a host actually receives rather than a paraphrase that drifts
the next time the wording is tuned. Rendering is a pure function of its inputs
and manufactures no evidence -- the header itself still comes only from the
Store-backed fill in the bridge.
"""

from __future__ import annotations

from typing import Final

from agency_runtime.core.header.response_contract import SNAPSHOT_VALUES_ONLY_NOTE

HEADER_SNAPSHOT_VERSION: Final[int] = 1

# AR-357: a snapshot carries values, never a requirement. Each instruction says
# so explicitly, because the earlier "supersedes this one" wording read as a
# fresh contract per observation and let the turn's stated expectation drift
# from what the finalizer actually checks.
HEADER_SNAPSHOT_INSTRUCTIONS: Final[dict[str, str]] = {
    "INITIAL": (
        "These are this turn's current header values, from Store evidence. "
        f"{SNAPSHOT_VALUES_ONLY_NOTE}"
    ),
    "UPDATED": (f"Agency recorded the preceding tool observation. {SNAPSHOT_VALUES_ONLY_NOTE}"),
    "FINAL": (f"The native wait completed. {SNAPSHOT_VALUES_ONLY_NOTE}"),
}


def format_header_snapshot(marker: str, instruction: str, header: str) -> str:
    """Frame one already-filled header as a versioned snapshot block."""

    return f"[AGENCY {marker} HEADER SNAPSHOT v{HEADER_SNAPSHOT_VERSION}]\n{instruction}\n{header}"


__all__ = [
    "HEADER_SNAPSHOT_INSTRUCTIONS",
    "HEADER_SNAPSHOT_VERSION",
    "format_header_snapshot",
]
