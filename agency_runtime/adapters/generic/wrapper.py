"""Generic adapter — wraps any agent CLI.

For runtimes that don't have a dedicated adapter, the generic wrapper
provides best-effort routing and delegation via subprocess.
"""

from __future__ import annotations

import logging
import os
import shutil
from typing import Any

from agency_runtime.adapters.base import BaseAdapter
from agency_runtime.core.delegation.backends import GenericCLIBackend
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

    def get_delegate_backend(self) -> str | None:
        return "generic_command" if self.is_available() else None

    def exec(
        self, task: str, args: list[str] | None = None, workdir: str | None = None
    ) -> dict[str, Any]:
        """Execute a task via a generic CLI command."""
        workdir = workdir or os.getcwd()
        command = (self.cli_cmd, *(args or [])) if self.cli_cmd else ()
        backend = GenericCLIBackend(
            command=command,
            name="generic_command",
            timeout=300,
        )
        return backend.execute(task=task, workdir=workdir, check=False)
