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

HEADER_SNAPSHOT_VERSION: Final[int] = 1

HEADER_SNAPSHOT_INSTRUCTIONS: Final[dict[str, str]] = {
    "INITIAL": (
        "Start each substantive progress update and the final parent response "
        "with these exact five lines, unchanged, then add the response body. "
        "A later Agency header snapshot for this turn supersedes this one."
    ),
    "UPDATED": (
        "Agency recorded the preceding tool observation. Start the next "
        "substantive or final parent response with these exact five lines, "
        "unchanged, then add the response body. A later Agency header snapshot "
        "for this turn supersedes this one."
    ),
    "FINAL": (
        "The native wait completed. Start the next substantive or final parent "
        "response with these exact five lines, unchanged, then add the response "
        "body. This is current-turn Store evidence, not a suggested draft."
    ),
}


def format_header_snapshot(marker: str, instruction: str, header: str) -> str:
    """Frame one already-filled header as a versioned snapshot block."""

    return f"[AGENCY {marker} HEADER SNAPSHOT v{HEADER_SNAPSHOT_VERSION}]\n{instruction}\n{header}"


__all__ = [
    "HEADER_SNAPSHOT_INSTRUCTIONS",
    "HEADER_SNAPSHOT_VERSION",
    "format_header_snapshot",
]
