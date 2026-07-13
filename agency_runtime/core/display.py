"""Bounded terminal-safe rendering for configured and remote display tokens."""

from __future__ import annotations

from typing import Any


def has_terminal_control(value: str) -> bool:
    """Return whether text contains C0, DEL, or C1 terminal controls."""

    return any(ord(char) < 32 or 127 <= ord(char) < 160 for char in value)


def safe_display_token(value: Any, *, limit: int = 160) -> str:
    """Escape terminal controls and bound one human-facing token."""

    if limit <= 0:
        raise ValueError("display limit must be positive")
    rendered = "".join(
        f"\\u{ord(char):04x}" if ord(char) < 32 or 127 <= ord(char) < 160 else char
        for char in str(value)
    )
    if len(rendered) <= limit:
        return rendered
    marker = "..."
    return rendered[: max(0, limit - len(marker))] + marker[:limit]


__all__ = ["has_terminal_control", "safe_display_token"]
