"""Generic adapter — wraps any agent CLI.

For runtimes that don't have a dedicated adapter, the generic wrapper
provides best-effort routing and delegation via subprocess.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Any

from agency_runtime.adapters.base import BaseAdapter
from agency_runtime.core.store.sqlite import Store

logger = logging.getLogger("agency_runtime.adapters.generic")


class GenericAdapter(BaseAdapter):
    """Generic CLI wrapper adapter."""

    host_name = "generic"

    def __init__(self, store: Store | None = None, cli_cmd: str = ""):
        super().__init__(store)
        self.cli_cmd = cli_cmd

    def is_available(self) -> bool:
        if not self.cli_cmd:
            return False
        return bool(shutil.which(self.cli_cmd))

    def report_skills_loaded(self, session_id: str) -> list[str]:
        return self.store.get_skills_for_session(session_id)

    def report_specialists_loaded(self, session_id: str) -> list[str]:
        return self.store.get_specialists_for_session(session_id)

    def get_delegate_backend(self) -> str | None:
        return "generic_command" if self.is_available() else None

    def expose_model_telemetry(self, session_id: str) -> dict[str, Any]:
        return {}

    def exec(self, task: str, args: list[str] | None = None, workdir: str | None = None) -> dict[str, Any]:
        """Execute a task via a generic CLI command."""
        import os
        workdir = workdir or os.getcwd()
        cmd = [self.cli_cmd] + (args or []) + [task]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=300,
                cwd=workdir,
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "backend": "generic_command",
                "workdir": workdir,
            }
        except FileNotFoundError:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"command not found: {self.cli_cmd}",
                "backend": "generic_command",
                "workdir": workdir,
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"{self.cli_cmd} timed out after 300s",
                "backend": "generic_command",
                "workdir": workdir,
            }
