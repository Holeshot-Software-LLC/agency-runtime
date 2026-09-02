"""Bounded lifetime for a stdio server whose client stopped talking (AR-372).

A stdio server exits when its client closes the pipe. It has no answer for a
client that keeps the pipe open and simply goes away, and that is the shape
that exhausts a machine: measured 2026-09-02, an operator's Windows box
reached 98.6% commit charge behind roughly 2,100 live Agency MCP/CLI
processes with live parents, and process creation began to fail. The same
leak reproduced on Linux in the maintainer's own session -- two
``agency_runtime.server.mcp --stdio`` processes alive for 16h13m and 15h28m,
each still parented by a running host and each pinned to a launcher tree two
deploys old.

Two independent bounds, because neither alone is sufficient:

* **Parent liveness** catches the orphan promptly, but the measured leaks all
  had live parents -- long-running host sessions that had simply stopped
  using their server.
* **Idle timeout** catches those, and is deliberately generous: a server is
  bound to one session, so ending it early would break the next tool call in
  a session the user is still holding open. Hours of silence is abandonment;
  minutes is a user reading.

Both are advisory and fail open. A bound that cannot be evaluated never ends
a server, because a supervisor that guesses is worse than one that waits.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from collections.abc import Callable

# A session idle this long has been abandoned: no host keeps a user waiting
# hours between tool calls. Deliberately far above any real inter-turn gap.
DEFAULT_IDLE_TIMEOUT_SECONDS = 4 * 60 * 60
IDLE_TIMEOUT_ENVIRONMENT_VARIABLE = "AGENCY_MCP_IDLE_TIMEOUT_SECONDS"
MIN_IDLE_TIMEOUT_SECONDS = 60
MAX_IDLE_TIMEOUT_SECONDS = 24 * 60 * 60
DEFAULT_POLL_SECONDS = 30.0

EXIT_IDLE = "idle_timeout"
EXIT_PARENT_GONE = "parent_exited"


def configured_idle_timeout_seconds(environ: dict[str, str] | None = None) -> float:
    """Return the idle bound, honouring a bounded operator override."""

    raw = (environ if environ is not None else os.environ).get(
        IDLE_TIMEOUT_ENVIRONMENT_VARIABLE, ""
    )
    try:
        requested = float(str(raw).strip())
    except (TypeError, ValueError):
        return float(DEFAULT_IDLE_TIMEOUT_SECONDS)
    if requested != requested or requested in (float("inf"), float("-inf")):
        return float(DEFAULT_IDLE_TIMEOUT_SECONDS)
    return float(min(max(requested, MIN_IDLE_TIMEOUT_SECONDS), MAX_IDLE_TIMEOUT_SECONDS))


def _posix_parent_alive(original_parent_pid: int) -> bool | None:
    """POSIX reparents an orphan, so a changed ppid means the parent exited."""

    getppid = getattr(os, "getppid", None)
    if not callable(getppid):
        return None
    try:
        return int(getppid()) == original_parent_pid
    except OSError:
        return None


class ParentWatch:
    """Answer 'is the process that started us still running?', or decline to.

    Windows does not reparent an orphan and reuses process ids, so a pid
    comparison there can answer about a stranger. Only POSIX is asserted;
    Windows returns ``None`` and leaves the idle bound to do the work.
    """

    def __init__(self, *, parent_pid: int | None = None, windows: bool | None = None) -> None:
        self._windows = os.name == "nt" if windows is None else bool(windows)
        getppid = getattr(os, "getppid", None)
        if parent_pid is not None:
            self._parent_pid: int | None = int(parent_pid)
        elif callable(getppid):
            try:
                self._parent_pid = int(getppid())
            except OSError:
                self._parent_pid = None
        else:
            self._parent_pid = None

    @property
    def observable(self) -> bool:
        return not self._windows and self._parent_pid is not None

    def alive(self) -> bool | None:
        """``True``/``False`` when knowable, ``None`` when it is not."""

        if not self.observable:
            return None
        assert self._parent_pid is not None
        return _posix_parent_alive(self._parent_pid)


class StdioLifetimeBound:
    """Watchdog that ends a stdio server the client abandoned."""

    def __init__(
        self,
        *,
        idle_timeout_seconds: float | None = None,
        poll_seconds: float = DEFAULT_POLL_SECONDS,
        parent_watch: ParentWatch | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        on_expire: Callable[[str], None] | None = None,
    ) -> None:
        self._idle_timeout = (
            configured_idle_timeout_seconds()
            if idle_timeout_seconds is None
            else float(idle_timeout_seconds)
        )
        self._poll = max(0.01, float(poll_seconds))
        self._parent = parent_watch if parent_watch is not None else ParentWatch()
        self._monotonic = monotonic
        self._on_expire = on_expire if on_expire is not None else _default_expire
        self._lock = threading.Lock()
        self._last_activity = self._monotonic()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def idle_timeout_seconds(self) -> float:
        return self._idle_timeout

    def record_activity(self) -> None:
        with self._lock:
            self._last_activity = self._monotonic()

    def expired_reason(self) -> str | None:
        """Return why this server should end, or ``None`` to keep serving."""

        if self._parent.alive() is False:
            return EXIT_PARENT_GONE
        with self._lock:
            idle_for = self._monotonic() - self._last_activity
        return EXIT_IDLE if idle_for >= self._idle_timeout else None

    def start(self) -> None:
        if self._thread is not None:
            return
        thread = threading.Thread(
            target=self._run,
            name="agency-mcp-lifetime",
            daemon=True,
        )
        self._thread = thread
        thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:  # pragma: no cover - exercised through expired_reason
        while not self._stop.wait(self._poll):
            reason = self.expired_reason()
            if reason is not None:
                self._on_expire(reason)
                return


def _default_expire(reason: str) -> None:  # pragma: no cover - process exit
    print(f"agency mcp server exiting: {reason}", file=sys.stderr, flush=True)
    os._exit(0)


__all__ = [
    "DEFAULT_IDLE_TIMEOUT_SECONDS",
    "DEFAULT_POLL_SECONDS",
    "EXIT_IDLE",
    "EXIT_PARENT_GONE",
    "IDLE_TIMEOUT_ENVIRONMENT_VARIABLE",
    "MAX_IDLE_TIMEOUT_SECONDS",
    "MIN_IDLE_TIMEOUT_SECONDS",
    "ParentWatch",
    "StdioLifetimeBound",
    "configured_idle_timeout_seconds",
]
