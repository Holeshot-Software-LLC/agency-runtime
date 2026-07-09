"""Claude Code adapter — optional, skipped if not installed.

Two modes when available:
1. Enforced wrapper mode: agency claude -p "task..."
2. Interactive hook/MCP mode: best-effort audit only.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Any

from agency_runtime.adapters.base import BaseAdapter
from agency_runtime.core.store.sqlite import Store

logger = logging.getLogger("agency_runtime.adapters.claude")


class ClaudeAdapter(BaseAdapter):
    """Claude Code CLI wrapper adapter (optional)."""

    host_name = "claude"

    def __init__(self, store: Store | None = None, claude_cmd: str = "claude"):
        super().__init__(store)
        self.claude_cmd = claude_cmd

    def is_available(self) -> bool:
        """Check if Claude Code CLI is installed."""
        try:
            result = subprocess.run(
                ["which", self.claude_cmd],
                capture_output=True, text=True, timeout=2,
            )
            return result.returncode == 0
        except Exception:
            return False

    def report_skills_loaded(self, session_id: str) -> list[str]:
        return self.store.get_skills_for_session(session_id)

    def report_specialists_loaded(self, session_id: str) -> list[str]:
        return self.store.get_specialists_for_session(session_id)

    def get_delegate_backend(self) -> str | None:
        return "claude_exec"

    def expose_model_telemetry(self, session_id: str) -> dict[str, Any]:
        return {}

    def exec(self, task: str, workdir: str | None = None, specialist_prompt: str = "") -> dict[str, Any]:
        """Execute a task via claude -p --output-format json.

        Collects modelUsage/cost/session id for receipt tracking.
        """
        import os
        workdir = workdir or os.getcwd()

        full_prompt = task
        if specialist_prompt:
            full_prompt = f"{specialist_prompt}\n\nTask: {task}"

        try:
            result = subprocess.run(
                [self.claude_cmd, "-p", "--output-format", "json", full_prompt],
                capture_output=True, text=True, timeout=300,
                cwd=workdir,
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "backend": "claude_exec",
                "workdir": workdir,
            }
        except FileNotFoundError:
            logger.info("Claude Code: not installed, adapter skipped")
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"claude not found: {self.claude_cmd}",
                "backend": "claude_exec",
                "workdir": workdir,
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": "claude exec timed out after 300s",
                "backend": "claude_exec",
                "workdir": workdir,
            }
