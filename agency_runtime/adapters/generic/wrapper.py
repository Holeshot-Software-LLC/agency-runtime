"""Generic adapter — evidence for a host with no dedicated adapter.

Records the same turn evidence as the named adapters. It does not execute
anything: rule 5 says the host alone decides whether to spawn.
"""

from __future__ import annotations

import logging
import shutil

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
