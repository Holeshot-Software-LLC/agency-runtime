"""A durable roll of the long-lived processes Agency owns (AR-372).

``agency off`` used to flip a control flag and leave every process Agency had
started still running: hooks became no-ops while MCP servers slept on their
pipes indefinitely. That is how an operator's Windows box reached 98.6%
commit charge behind roughly 2,100 live processes, and it is why "off" has to
mean off.

Ownership is recorded, never guessed. A long-lived server writes one entry
when it starts and removes it when it exits, so ``agency off`` ends exactly
the processes Agency started and nothing that merely looks like one. Every
read re-verifies liveness against the recorded start time, because process
ids are reused -- on Windows especially -- and a stale id must never cost an
unrelated process its life.

The roll is advisory. A registry that cannot be read or written never blocks
a server from starting: losing the ability to record ownership is Agency's
problem, not a reason to deny the operator a working runtime.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.private_paths import ensure_private_directory

REGISTRY_SCHEMA = "agency.owned-processes.v1"
REGISTRY_FILENAME = "owned-processes.json"
# One entry per long-lived server; a machine with more than this has a defect
# the ceiling should already have refused.
MAX_REGISTERED_PROCESSES = 512
MAX_REGISTRY_BYTES = 256 * 1024
MAX_KIND_CHARS = 64
_START_TIME_TOLERANCE_SECONDS = 2.0


@dataclass(frozen=True, slots=True)
class OwnedProcess:
    """One recorded Agency-owned process."""

    pid: int
    kind: str
    started_at: float
    recorded_at: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "kind": self.kind,
            "started_at": self.started_at,
            "recorded_at": self.recorded_at,
        }


def registry_path(*, home_dir: str | Path | None = None) -> Path:
    from agency_runtime.core.installer_native import runtime_home

    return runtime_home(home_dir=home_dir) / "run" / REGISTRY_FILENAME


def process_start_time(pid: int) -> float | None:
    """Return a stable start marker for ``pid``, or ``None`` when unknowable.

    The marker exists to tell one process from a later one that reused its id.
    Linux exposes it directly; elsewhere the registry falls back to liveness
    alone, which is weaker but never wrong about a process that is gone.
    """

    try:
        raw = Path(f"/proc/{int(pid)}/stat").read_bytes()
    except (OSError, ValueError):
        return None
    try:
        # Field 22 is starttime; the comm field may contain spaces or ')'.
        tail = raw[raw.rindex(b")") + 2 :].split()
        return float(int(tail[19]))
    except (IndexError, ValueError):
        return None


def _process_is_zombie(pid: int) -> bool:
    """Whether ``pid`` has exited but has not been reaped by its parent.

    A zombie answers ``os.kill(pid, 0)`` successfully because the id is still
    allocated, so signalling alone reports a finished process as running --
    and the roll would keep it forever. Where the state is readable, an
    unreaped exit counts as gone.
    """

    try:
        raw = Path(f"/proc/{int(pid)}/stat").read_bytes()
    except (OSError, ValueError):
        return False
    try:
        return raw[raw.rindex(b")") + 2 :].split()[0] == b"Z"
    except (IndexError, ValueError):
        return False


def process_is_alive(pid: int) -> bool:
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, ValueError):
        return False
    return not _process_is_zombie(pid)


def _entry_is_current(entry: OwnedProcess) -> bool:
    """Whether this exact process still runs, not merely something with its id."""

    if not process_is_alive(entry.pid):
        return False
    observed = process_start_time(entry.pid)
    if observed is None or entry.started_at <= 0:
        return True
    return abs(observed - entry.started_at) <= _START_TIME_TOLERANCE_SECONDS


def _project_entry(value: object) -> OwnedProcess | None:
    if not isinstance(value, Mapping):
        return None
    pid = value.get("pid")
    kind = str(value.get("kind") or "").strip()[:MAX_KIND_CHARS]
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0 or not kind:
        return None
    try:
        started_at = float(value.get("started_at") or 0.0)
        recorded_at = float(value.get("recorded_at") or 0.0)
    except (TypeError, ValueError):
        return None
    return OwnedProcess(pid=pid, kind=kind, started_at=started_at, recorded_at=recorded_at)


def _read_entries(path: Path) -> list[OwnedProcess]:
    try:
        raw = path.read_bytes()
    except OSError:
        return []
    try:
        parsed = safe_load_bounded_json(raw, maximum_bytes=MAX_REGISTRY_BYTES)
    except (BoundedJSONError, TypeError, ValueError, UnicodeDecodeError):
        return []
    if not isinstance(parsed, Mapping) or parsed.get("schema") != REGISTRY_SCHEMA:
        return []
    rows = parsed.get("processes")
    if not isinstance(rows, list):
        return []
    entries: list[OwnedProcess] = []
    seen: set[int] = set()
    for row in rows[:MAX_REGISTERED_PROCESSES]:
        entry = _project_entry(row)
        if entry is None or entry.pid in seen:
            continue
        seen.add(entry.pid)
        entries.append(entry)
    return entries


def _write_entries(path: Path, entries: list[OwnedProcess]) -> bool:
    payload = json.dumps(
        {
            "schema": REGISTRY_SCHEMA,
            "processes": [entry.as_dict() for entry in entries[:MAX_REGISTERED_PROCESSES]],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(payload) > MAX_REGISTRY_BYTES:
        return False
    try:
        ensure_private_directory(path.parent)
        temporary = path.with_name(f".{path.name}.{os.getpid()}")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            pass
        os.replace(temporary, path)
    except OSError:
        return False
    return True


def live_processes(*, home_dir: str | Path | None = None) -> list[OwnedProcess]:
    """Return the recorded processes that are still the ones we recorded."""

    return [
        entry
        for entry in _read_entries(registry_path(home_dir=home_dir))
        if _entry_is_current(entry)
    ]


def register_process(
    kind: str,
    *,
    pid: int | None = None,
    home_dir: str | Path | None = None,
) -> bool:
    """Record one long-lived process as Agency-owned. Advisory: never raises."""

    normalized_kind = str(kind or "").strip()[:MAX_KIND_CHARS]
    if not normalized_kind:
        return False
    identifier = os.getpid() if pid is None else int(pid)
    path = registry_path(home_dir=home_dir)
    entries = [entry for entry in _read_entries(path) if entry.pid != identifier]
    entries = [entry for entry in entries if _entry_is_current(entry)]
    if len(entries) >= MAX_REGISTERED_PROCESSES:
        return False
    entries.append(
        OwnedProcess(
            pid=identifier,
            kind=normalized_kind,
            started_at=float(process_start_time(identifier) or 0.0),
            recorded_at=time.time(),
        )
    )
    return _write_entries(path, entries)


def forget_process(
    *,
    pid: int | None = None,
    home_dir: str | Path | None = None,
) -> bool:
    """Remove one process from the roll after it exits cleanly."""

    identifier = os.getpid() if pid is None else int(pid)
    path = registry_path(home_dir=home_dir)
    entries = [entry for entry in _read_entries(path) if entry.pid != identifier]
    return _write_entries(path, entries)


def _terminate(pid: int) -> bool:
    import signal

    for attempt in (getattr(signal, "SIGTERM", 15), getattr(signal, "SIGKILL", 9)):
        try:
            os.kill(pid, attempt)
        except (ProcessLookupError, PermissionError, OSError, ValueError):
            return not process_is_alive(pid)
        for _ in range(20):
            if not process_is_alive(pid):
                return True
            time.sleep(0.1)
    return not process_is_alive(pid)


def terminate_owned_processes(
    *,
    home_dir: str | Path | None = None,
    kinds: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """End every recorded process Agency owns and report what happened.

    Only entries whose recorded start time still matches are signalled, so a
    reused process id can never cost an unrelated process its life.
    """

    path = registry_path(home_dir=home_dir)
    remaining: list[OwnedProcess] = []
    ended: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for entry in _read_entries(path):
        if not _entry_is_current(entry):
            continue
        if kinds is not None and entry.kind not in kinds:
            remaining.append(entry)
            continue
        if _terminate(entry.pid):
            ended.append({"pid": entry.pid, "kind": entry.kind})
        else:
            failed.append({"pid": entry.pid, "kind": entry.kind})
            remaining.append(entry)
    _write_entries(path, remaining)
    return {
        "schema": REGISTRY_SCHEMA,
        "ended": ended,
        "failed": failed,
        "remaining": len(remaining),
    }


def registered_kinds(*, home_dir: str | Path | None = None) -> Iterator[str]:
    for entry in live_processes(home_dir=home_dir):
        yield entry.kind


__all__ = [
    "MAX_REGISTERED_PROCESSES",
    "MAX_REGISTRY_BYTES",
    "REGISTRY_SCHEMA",
    "OwnedProcess",
    "forget_process",
    "live_processes",
    "process_is_alive",
    "process_start_time",
    "register_process",
    "registered_kinds",
    "registry_path",
    "terminate_owned_processes",
]
