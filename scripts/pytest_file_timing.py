"""Explicit pytest plugin for bounded repository-relative file timings."""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SHARD_TIMING_SCHEMA = "agency.pytest-file-timings.shard.v1"
RUN_TIMING_SCHEMA = "agency.pytest-file-timings.run.v2"
RUN_ID_ENVIRONMENT_KEY = "AGENCY_PYTEST_FILE_TIMING_RUN_ID"
REPORT_OPTION = "--agency-file-timing-report"
SHARD_OPTION = "--agency-file-timing-shard"
MAX_SHARD_TIMING_BYTES = 1024 * 1024
MAX_RUN_TIMING_BYTES = 4 * 1024 * 1024
MAX_TIMED_FILES = 4096
MAX_DURATION_NS = 2**63 - 1

_RUN_ID = re.compile(r"[a-f0-9]{32}")
_PHASES = ("setup", "call", "teardown")


@dataclass(slots=True)
class _FileTiming:
    collected_items: int = 0
    duration_ns: dict[str, int] = field(default_factory=lambda: dict.fromkeys(_PHASES, 0))
    report_counts: dict[str, int] = field(default_factory=lambda: dict.fromkeys(_PHASES, 0))


@dataclass(slots=True)
class _TimingState:
    descriptor: int
    files: dict[str, _FileTiming]
    invocation_root: Path
    node_files: dict[str, str]
    run_id: str
    shard: int
    errors: set[str] = field(default_factory=set)
    written: bool = False


_state: _TimingState | None = None


def _normalized_file(path: Path, root: Path, *, strict: bool) -> str:
    candidate = path if path.is_absolute() else root / path
    resolved = candidate.resolve(strict=strict)
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("timed path escaped the pytest root") from exc
    value = relative.as_posix()
    if not value or value == "." or "\\" in value:
        raise ValueError("timed path is not canonical repository-relative text")
    return value


def _write_all(descriptor: int, payload: bytes) -> None:
    pending = memoryview(payload)
    while pending:
        written = os.write(descriptor, pending)
        if written <= 0:
            raise OSError("short timing report write")
        pending = pending[written:]


def pytest_addoption(parser: Any) -> None:
    group = parser.getgroup("agency-file-timing")
    group.addoption(REPORT_OPTION, action="store", default=None)
    group.addoption(SHARD_OPTION, action="store", type=int, default=None)


def pytest_configure(config: Any) -> None:
    global _state
    report_value = config.getoption(REPORT_OPTION)
    shard = config.getoption(SHARD_OPTION)
    if report_value is None and shard is None:
        return
    if _state is not None:
        raise RuntimeError("Agency file timing is already configured")
    if not isinstance(report_value, str) or not report_value or not isinstance(shard, int):
        raise ValueError("Agency file timing requires one report path and shard index")
    if shard < 0 or shard > MAX_TIMED_FILES:
        raise ValueError("Agency file timing shard index is outside its bound")
    run_id = os.environ.get(RUN_ID_ENVIRONMENT_KEY, "")
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("Agency file timing run identity is unavailable")
    invocation_root = Path(config.invocation_params.dir).resolve(strict=True)
    selected: dict[str, _FileTiming] = {}
    if not 1 <= len(config.args) <= MAX_TIMED_FILES:
        raise ValueError("Agency file timing selected-file count is outside its bound")
    for value in config.args:
        if not isinstance(value, str) or "::" in value:
            raise ValueError("Agency file timing requires exact file arguments")
        normalized = _normalized_file(Path(value), invocation_root, strict=True)
        if normalized in selected:
            raise ValueError("Agency file timing received a duplicate file argument")
        selected[normalized] = _FileTiming()

    report_path = Path(report_value)
    if not report_path.is_absolute():
        raise ValueError("Agency file timing report path must be absolute")
    report_parent = report_path.parent.resolve(strict=True)
    report_path = report_parent / report_path.name
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    descriptor = os.open(report_path, flags, 0o600)
    try:
        if os.name != "nt":
            os.fchmod(descriptor, 0o600)
    except BaseException:
        os.close(descriptor)
        raise
    _state = _TimingState(
        descriptor=descriptor,
        files=selected,
        invocation_root=invocation_root,
        node_files={},
        run_id=run_id,
        shard=shard,
    )


def _state_file(path: Path, *, error: str) -> tuple[str, _FileTiming] | None:
    state = _state
    if state is None:
        return None
    try:
        normalized = _normalized_file(path, state.invocation_root, strict=True)
    except (OSError, ValueError):
        state.errors.add(error)
        return None
    timing = state.files.get(normalized)
    if timing is None:
        state.errors.add(error)
    if timing is None:
        return None
    return normalized, timing


def pytest_collection_finish(session: Any) -> None:
    if _state is None:
        return
    for item in session.items:
        resolved = _state_file(Path(item.path), error="unexpected-collected-file")
        nodeid = getattr(item, "nodeid", None)
        if resolved is None:
            continue
        if not isinstance(nodeid, str) or not nodeid or nodeid in _state.node_files:
            _state.errors.add("invalid-collected-nodeid")
            continue
        normalized, timing = resolved
        _state.node_files[nodeid] = normalized
        timing.collected_items += 1


def pytest_runtest_logreport(report: Any) -> None:
    state = _state
    if state is None:
        return
    phase = getattr(report, "when", None)
    if phase not in _PHASES:
        state.errors.add("unexpected-report-phase")
        return
    nodeid = getattr(report, "nodeid", None)
    if not isinstance(nodeid, str) or not nodeid:
        state.errors.add("invalid-report-nodeid")
        return
    normalized = state.node_files.get(nodeid)
    if normalized is None:
        state.errors.add("unexpected-report-nodeid")
        return
    timing = state.files[normalized]
    duration = getattr(report, "duration", None)
    if (
        isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or not math.isfinite(float(duration))
        or float(duration) < 0
    ):
        state.errors.add("invalid-report-duration")
        return
    duration_ns = round(float(duration) * 1_000_000_000)
    current = timing.duration_ns[phase]
    if duration_ns > MAX_DURATION_NS - current:
        state.errors.add("duration-overflow")
        return
    timing.duration_ns[phase] = current + duration_ns
    timing.report_counts[phase] += 1


def _report_payload(state: _TimingState, exit_status: int) -> bytes:
    files = []
    phase_report_count = 0
    collected_item_count = 0
    for path in sorted(state.files):
        timing = state.files[path]
        phase_report_count += sum(timing.report_counts.values())
        collected_item_count += timing.collected_items
        files.append(
            {
                "collected_items": timing.collected_items,
                "duration_ns": {phase: timing.duration_ns[phase] for phase in _PHASES},
                "path": path,
                "report_counts": {phase: timing.report_counts[phase] for phase in _PHASES},
                "total_ns": sum(timing.duration_ns.values()),
            }
        )
    payload = {
        "collected_item_count": collected_item_count,
        "errors": sorted(state.errors),
        "exit_status": int(exit_status),
        "files": files,
        "phase_report_count": phase_report_count,
        "run_id": state.run_id,
        "schema": SHARD_TIMING_SCHEMA,
        "shard": state.shard,
    }
    encoded = (
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode(
            "ascii"
        )
        + b"\n"
    )
    if len(encoded) > MAX_SHARD_TIMING_BYTES:
        raise RuntimeError("Agency file timing report exceeded its byte bound")
    return encoded


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    del session
    state = _state
    if state is None:
        return
    if state.written:
        raise RuntimeError("Agency file timing report was already written")
    state.written = True
    descriptor = state.descriptor
    state.descriptor = -1
    try:
        _write_all(descriptor, _report_payload(state, exitstatus))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def pytest_unconfigure(config: Any) -> None:
    del config
    global _state
    state = _state
    _state = None
    if state is not None and state.descriptor >= 0:
        os.close(state.descriptor)


__all__ = [
    "MAX_RUN_TIMING_BYTES",
    "MAX_SHARD_TIMING_BYTES",
    "REPORT_OPTION",
    "RUN_ID_ENVIRONMENT_KEY",
    "RUN_TIMING_SCHEMA",
    "SHARD_OPTION",
    "SHARD_TIMING_SCHEMA",
]
