"""Preserve full selected cards across Claude's native hook output ceiling."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

# Claude 2.1.266 persists hook additionalContext above 10,000 JS string units.
# Leave room for the bridge's response contract and initial header snapshot.
CLAUDE_INLINE_CONTEXT_UNITS = 6_000
CLAUDE_RETRIEVAL_CONTEXT_UNITS = 8_000
CLAUDE_NATIVE_HOOK_UNITS = 10_000


def utf16_units(text: str) -> int:
    """Measure the native JavaScript string limit, including astral characters."""
    return len(text.encode("utf-16-le", errors="surrogatepass")) // 2


def needs_mcp_context(host: str, frame: str, cards: str) -> bool:
    return (
        host == "claude"
        and bool(cards)
        and utf16_units(f"{frame}\n\n{cards}") > CLAUDE_INLINE_CONTEXT_UNITS
    )


def mcp_context_enabled(recipe: Mapping[str, Any]) -> bool:
    value = recipe.get("specialist_context_via_mcp", False)
    if not isinstance(value, bool) or (
        value and (recipe.get("host") != "claude" or recipe.get("recipe_version", 0) < 16)
    ):
        raise ValueError("invalid specialist context delivery surface")
    return value


def selected_card_requests(
    references: Sequence[Mapping[str, Any]], session_id: str, trace_id: str
) -> str:
    """Describe retrieval of the persisted selection; never choose new staff."""
    lines = [
        "[AGENCY SELECTED SPECIALIST CONTEXT]",
        "The following cards were selected by this turn's workforce inference. "
        "Selection is not loading. Before doing the task, retrieve every card not "
        "already loaded in this exact turn with the installed agency.load_specialist "
        "MCP tool and these exact arguments. The tool resolves the selected immutable "
        "version. Use the returned full cards; do not search, recruit, substitute "
        "specialists, or read files to obtain them. Report only actual loads in the header.",
    ]
    lines.extend(
        json.dumps(
            {"slug": reference["slug"], "session_id": session_id, "trace_id": trace_id},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for reference in references
    )
    return "\n".join(lines)
