"""Exact, shared parsing for conversational Agency runtime controls.

The parser deliberately accepts only complete commands.  Callers receiving
host-native slash-command arguments must add the explicit ``agency`` namespace
before calling it; this keeps punctuation, broad words, and partial phrases
from acquiring control authority at one surface but not another.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal

RuntimeControlAction = Literal["status", "on", "off"]

RUNTIME_CONTROL_ACTIONS: Final[tuple[RuntimeControlAction, ...]] = (
    "status",
    "on",
    "off",
)
RUNTIME_CONTROL_CONVERSATION_FORMS: Final[tuple[str, ...]] = tuple(
    form
    for action in RUNTIME_CONTROL_ACTIONS
    for form in (
        f"agency {action}",
        f"/agency {action}",
        f"agency runtime {action}",
        f"/agency runtime {action}",
    )
)
_NORMALIZED_FORMS: Final = MappingProxyType(
    {
        " ".join(form.removeprefix("/").casefold().split()): action
        for action in RUNTIME_CONTROL_ACTIONS
        for form in (f"agency {action}", f"agency runtime {action}")
    }
)
_SAFE_COMMAND_TEXT: Final = re.compile(r"[A-Za-z/\s]+\Z")


@dataclass(frozen=True, slots=True)
class RuntimeControlCommand:
    """One exact normalized control command."""

    action: RuntimeControlAction
    normalized: str


def parse_runtime_control_command(value: object) -> RuntimeControlCommand | None:
    """Parse one complete command without forgiving punctuation or extra text."""

    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw or len(raw) > 64 or _SAFE_COMMAND_TEXT.fullmatch(raw) is None:
        return None
    normalized = " ".join(raw.removeprefix("/").casefold().split())
    action = _NORMALIZED_FORMS.get(normalized)
    if action is None:
        return None
    return RuntimeControlCommand(action=action, normalized=f"agency {action}")


def parse_host_control_arguments(value: object) -> RuntimeControlCommand:
    """Parse exact host-native ``/agency`` arguments through the shared parser."""

    if not isinstance(value, str):
        raise ValueError("usage: /agency [status|on|off]")
    raw = value.strip()
    complete = raw if raw.casefold().startswith(("/", "agency")) else f"agency {raw or 'status'}"
    command = parse_runtime_control_command(complete)
    if command is None:
        raise ValueError("usage: /agency [status|on|off]")
    return command


__all__ = [
    "RUNTIME_CONTROL_ACTIONS",
    "RUNTIME_CONTROL_CONVERSATION_FORMS",
    "RuntimeControlAction",
    "RuntimeControlCommand",
    "parse_host_control_arguments",
    "parse_runtime_control_command",
]
