"""Codex adapter — first-class wrapper and delegation backend.

Works with or without LiteLLM. Codex can be both:
1. A host that receives tasks (wrapper mode).
2. A delegation backend for other hosts.
"""

from __future__ import annotations

import logging
import os
import shutil
from typing import Any

from agency_runtime.adapters.base import BaseAdapter
from agency_runtime.core.delegation.backends import CodexExecBackend
from agency_runtime.core.store.sqlite import Store

logger = logging.getLogger("agency_runtime.adapters.codex")


class CodexAdapter(BaseAdapter):
    """Codex CLI wrapper adapter."""

    host_name = "codex"

    def __init__(self, store: Store | None = None, codex_cmd: str = "codex"):
        super().__init__(store)
        self.codex_cmd = codex_cmd

    def is_available(self) -> bool:
        """Check if codex CLI is installed."""
        return bool(shutil.which(self.codex_cmd))

    def report_skills_loaded(self, session_id: str) -> list[str]:
        return self.store.get_skills_for_session(session_id)

    def report_specialists_loaded(self, session_id: str) -> list[str]:
        return self.store.get_specialists_for_session(session_id)

    def get_delegate_backend(self) -> str | None:
        return "codex_exec"

    def expose_model_telemetry(self, session_id: str) -> dict[str, Any]:
        return {}

    def exec(self, task: str, workdir: str | None = None, specialist_prompt: str = "") -> dict[str, Any]:
        """Execute a task via Codex's non-interactive JSONL contract.

        Returns:
            {
                "exit_code": int,
                "stdout": str,
                "stderr": str,
                "backend": "codex_exec",
                "workdir": str,
            }
        """
        workdir = workdir or os.getcwd()

        # Build the full prompt with specialist context if provided
        full_prompt = task
        if specialist_prompt:
            full_prompt = f"{specialist_prompt}\n\nTask: {task}"

        backend = CodexExecBackend(
            command=(self.codex_cmd, "exec"),
            name="codex_exec",
            timeout=300,
        )
        return backend.execute(task=full_prompt, workdir=workdir, check=False)

    def run_preflight(self, session_id: str, user_message: str) -> dict[str, Any] | None:
        """Run agency selector before launching codex."""
        from agency_runtime.core.selector.pipeline import is_trivial, route_and_build_context

        if is_trivial(user_message):
            return None

        catalog = self.store.get_active_roster_as_catalog()
        context = route_and_build_context(
            session_id,
            user_message,
            catalog,
            store=self.store,
        )
        return {"context": context} if context else None
