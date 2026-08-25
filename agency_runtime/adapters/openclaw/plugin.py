"""OpenClaw adapter — typed plugin hooks for OpenClaw runtime.

Uses api.on(...) typed hooks for policy/final-answer behavior.
File-based internal HOOK.md hooks are for side effects only.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from agency_runtime.adapters.base import BaseAdapter
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.installer_contracts import CommandRunner

logger = logging.getLogger("agency_runtime.adapters.openclaw")


_MAX_NATIVE_SKILL_INFO_BYTES = 64 * 1024
_MAX_NATIVE_SKILL_PATH_CHARS = 4096
_SKILL_KEY = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?")
_REQUIRED_TRUE_SKILL_FIELDS = ("eligible", "modelVisible")
_REQUIRED_FALSE_SKILL_FIELDS = (
    "disabled",
    "blockedByAllowlist",
    "blockedByAgentFilter",
    "platformIncompatible",
)


def _normalized_absolute_path(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > _MAX_NATIVE_SKILL_PATH_CHARS
        or "\x00" in value
    ):
        return ""
    try:
        normalized = os.path.normpath(value)
        if any(part in {".", ".."} for part in Path(value).parts):
            return ""
    except (OSError, TypeError, ValueError):
        return ""
    if not os.path.isabs(normalized):
        return ""
    return os.path.normcase(normalized)


def _native_skill_candidate(args: Mapping[str, Any]) -> tuple[str, str] | None:
    candidate = _normalized_absolute_path(args.get("path"))
    if not candidate or os.path.basename(candidate) != "SKILL.md":
        return None
    skill_key = os.path.basename(os.path.dirname(candidate))
    if _SKILL_KEY.fullmatch(skill_key) is None:
        return None
    return skill_key, candidate


def _authorized_native_skill_read(
    args: Mapping[str, Any],
    *,
    command_runner: CommandRunner | None = None,
) -> str:
    """Return the exact OpenClaw skill key for one inventory-authorized read."""

    candidate = _native_skill_candidate(args)
    if candidate is None:
        return ""
    skill_key, candidate_path = candidate

    from agency_runtime.core.installer_native import run_native

    try:
        receipt = run_native(
            ["openclaw", "skills", "info", skill_key, "--json"],
            host="openclaw",
            command_runner=command_runner,
            timeout=5.0,
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        return ""
    if not receipt.ok or not receipt.stdout.strip():
        return ""
    try:
        inventory = safe_load_bounded_json(
            receipt.stdout,
            maximum_bytes=_MAX_NATIVE_SKILL_INFO_BYTES,
            maximum_depth=16,
            maximum_nodes=2048,
        )
    except (TypeError, ValueError):
        return ""
    if not isinstance(inventory, dict):
        return ""
    if inventory.get("name") != skill_key or inventory.get("skillKey") != skill_key:
        return ""
    if any(inventory.get(field) is not True for field in _REQUIRED_TRUE_SKILL_FIELDS):
        return ""
    if any(inventory.get(field) is not False for field in _REQUIRED_FALSE_SKILL_FIELDS):
        return ""

    inventory_path = _normalized_absolute_path(inventory.get("filePath"))
    inventory_base = _normalized_absolute_path(inventory.get("baseDir"))
    if not inventory_path or inventory_path != candidate_path:
        return ""
    if not inventory_base or inventory_base != os.path.dirname(candidate_path):
        return ""
    return skill_key


class OpenClawAdapter(BaseAdapter):
    """OpenClaw/Nexus runtime adapter."""

    host_name = "openclaw"

    def is_available(self) -> bool:
        """Return canonical executable or native-state discovery for OpenClaw."""

        from agency_runtime.core.installer import detect_installed_agents

        return "openclaw" in detect_installed_agents()

    def on_message_received(
        self,
        session_id: str,
        user_message: str,
        model: str = "",
        trace_id: str = "",
    ) -> dict[str, Any] | None:
        """Typed plugin hook: message received, run preflight."""
        return self.build_preflight_context(session_id, user_message, model, trace_id)

    def post_tool_call_handler(self, **kwargs: Any) -> None:
        """Normalize an inventory-authorized native skill read before recording."""

        tool_name = str(kwargs.get("tool_name") or "")
        args = kwargs.get("args")
        if tool_name == "read" and isinstance(args, dict):
            skill_name = _authorized_native_skill_read(args)
            if skill_name:
                normalized = dict(kwargs)
                normalized["tool_name"] = "skill_view"
                normalized["args"] = {"name": skill_name}
                super().post_tool_call_handler(**normalized)
                return
        super().post_tool_call_handler(**kwargs)

    def on_response_finalizing(
        self,
        draft_text: str,
        session_id: str = "",
        model: str = "",
        *,
        trace_id: str = "",
    ) -> str:
        """Typed plugin hook: apply header finalization before response sent."""
        return self.apply_finalization(
            draft_text,
            session_id,
            model,
            trace_id=trace_id,
        )
