"""Opt-in file sink for hook diagnostics.

A hook speaks one JSON object on stdout and must leave stderr clean -- the host
and the stdio tests both treat stderr output as a boundary violation.  That is
why this package's loggers carry a ``NullHandler`` and nothing else.  The cost
is that the evidence-contract instrumentation records exactly which constraint
failed and then throws it away, so an operator debugging a rejected turn sees
only the rejection.

This installs a bounded, owner-private *file* handler when ``AGENCY_HOOK_LOG``
names one, and never writes to stderr.  Propagation to the root logger is
disabled while the sink is installed: a submodule with no handler of its own
would otherwise reach ``logging.lastResort`` and print WARNING+ records to
stderr behind the hook's back, which is the exact boundary the NullHandler
exists to protect.

Opening the sink is never allowed to break a hook.  Diagnostics are not worth
losing a turn over, so every failure path here degrades to "no sink" rather
than raising.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from contextlib import suppress
from logging.handlers import RotatingFileHandler
from pathlib import Path

from agency_runtime.core.configuration import restrict_private_file

PATH_VARIABLE = "AGENCY_HOOK_LOG"
LEVEL_VARIABLE = "AGENCY_HOOK_LOG_LEVEL"

_PACKAGE_LOGGER = "agency_runtime"
_SINK_ATTRIBUTE = "_agency_hook_log_sink"
_FORMAT = "%(asctime)s pid=%(process)d %(levelname)s %(name)s: %(message)s"
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 2
_DEFAULT_LEVEL = "DEBUG"


def _resolved_level(value: object) -> int:
    """Resolve one configured level name, defaulting rather than raising."""

    candidate = logging.getLevelName(str(value or _DEFAULT_LEVEL).strip().upper())
    return candidate if isinstance(candidate, int) else logging.DEBUG


def install_hook_log_sink(environment: Mapping[str, str] | None = None) -> bool:
    """Install the opt-in hook log sink; return whether one is active.

    Absent ``AGENCY_HOOK_LOG`` this changes nothing at all, so the default hook
    path keeps its current behaviour exactly.  Repeated calls in one process
    are idempotent -- every hook event would otherwise stack another handler.
    """

    source = os.environ if environment is None else environment
    configured = str(source.get(PATH_VARIABLE, "") or "").strip()
    if not configured:
        return False
    logger = logging.getLogger(_PACKAGE_LOGGER)
    if getattr(logger, _SINK_ATTRIBUTE, False):
        return True
    try:
        target = Path(configured).expanduser()
        if not target.is_absolute():
            raise ValueError(f"{PATH_VARIABLE} must name an absolute path")
        target.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            target,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
    except (OSError, ValueError):
        return False
    # Best effort: a sink that cannot be locked down is still better than no
    # diagnostics, and the operator chose this path explicitly.
    with suppress(OSError, ValueError):
        restrict_private_file(target)
    level = _resolved_level(source.get(LEVEL_VARIABLE, ""))
    handler.setFormatter(logging.Formatter(_FORMAT))
    handler.setLevel(level)
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    setattr(logger, _SINK_ATTRIBUTE, True)
    return True


__all__ = ["LEVEL_VARIABLE", "PATH_VARIABLE", "install_hook_log_sink"]
