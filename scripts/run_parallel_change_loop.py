"""Run the warning-strict non-performance pytest corpus in isolated file shards."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import secrets
import sys
import threading
import time
from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.exception_notes import add_exception_note
from agency_runtime.core.owned_process import (
    BoundedBinaryProcessResult,
    run_bounded_binary_process,
)
from agency_runtime.core.private_paths import private_runtime_directory, remove_private_directory
from scripts.parallel_change_loop_runtime import (
    RUNTIME_RECEIPT_NAME,
    RuntimeContract,
    build_runtime_contract,
    private_child_environment,
    runtime_path,
    runtime_receipt_payload,
)
from scripts.parallel_change_loop_storage import (
    bounded_head_tail,
    clear_reserved_latest_logs,
    create_exact_private_file,
    ensure_owned_directory,
    exact_private_file_is_valid,
    private_runtime_lock,
    reset_private_scratch,
    write_atomic_bounded_log,
)
from scripts.prepare_ci_runtime import ci_runtime_root_path, prepare_ci_runtime
from scripts.pytest_file_timing import (
    MAX_RUN_TIMING_BYTES,
    MAX_SHARD_TIMING_BYTES,
    REPORT_OPTION,
    RUN_ID_ENVIRONMENT_KEY,
    RUN_TIMING_SCHEMA,
    SHARD_OPTION,
    SHARD_TIMING_SCHEMA,
)
from scripts.select_test_shard import discover_test_files, partition_test_files
from scripts.test_shard_profile import (
    PartitionWeights,
    build_measurement_context,
    load_partition_weights,
)

DEFAULT_SHARD_COUNT = 4
DEFAULT_MAX_LOG_BYTES = 4 * 1024 * 1024
MIN_LOG_BYTES = 4 * 1024
MAX_LOG_BYTES = 64 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 45 * 60
MIN_TIMEOUT_SECONDS = 0.1
MAX_TIMEOUT_SECONDS = 24 * 60 * 60
MAX_WINDOWS_CRITICAL_PATH_CHARS = 240
PYTEST_FLAGS = (
    "-q",
    "-W",
    "error",
    "-p",
    "no:cacheprovider",
    "-m",
    "not performance",
    "--durations=25",
)

_LOG_ROOT_NAME = ".agency-local-change-loop-logs-v1"
_LOG_ROOT_RECEIPT_NAME = ".agency-owned-root"
_LOG_ROOT_RECEIPT = b"agency-runtime-local-change-loop-logs:v1\n"
_LOG_MANIFEST_NAME = "latest-run.json"
_TIMING_MANIFEST_NAME = "pytest-file-timings.latest.json"
_SCRATCH_ROOT_NAME = ".agency-local-change-loop-scratch-v1"
_LOCK_WAIT_SECONDS = 30.0
_STATUS_LOG_BYTES = 512
_MIN_STDERR_LOG_BYTES = 1024
_TRUNCATION_MARKER = b"\n...[bounded shard log truncated]...\n"
_PRIVATE_ENVIRONMENT_KEYS = (
    "AGENCY_CI_ROOT",
    "AGENCY_CI_PYTHON",
    "AGENCY_CI_HOME",
    "AGENCY_CI_TEMP",
    "AGENCY_CI_NODE",
    "HOME",
    "USERPROFILE",
    "TMP",
    "TEMP",
    "TMPDIR",
    "PYTHONPATH",
    "PYTHONNOUSERSITE",
    "PYTHONDONTWRITEBYTECODE",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "VIRTUAL_ENV",
)


@dataclass(slots=True)
class PlanUse:
    """In-memory single-use guard; plans own no operating-system resources."""

    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    state: str = "ready"
    run_id: str | None = None
    elapsed_seconds: float | None = None

    def begin(self) -> None:
        with self.lock:
            if self.state != "ready":
                raise RuntimeError("parallel test plan has already been started")
            self.state = "running"

    def finish(self, *, run_id: str, elapsed_seconds: float) -> None:
        with self.lock:
            if self.state == "running":
                self.state = "finished"
                self.run_id = run_id
                self.elapsed_seconds = elapsed_seconds


@dataclass(frozen=True, slots=True)
class TestShardPlan:
    index: int
    test_files: tuple[Path, ...]
    command: tuple[str, ...]
    environment: dict[str, str]
    working_directory: Path
    stable_runtime_root: Path
    run_root: Path
    private_home: Path
    private_temp: Path
    base_temp: Path
    log_path: Path
    timeout_seconds: float
    weight_total: int
    timing_path: Path | None = None


@dataclass(frozen=True, slots=True)
class ParallelTestPlan:
    repo_root: Path
    test_root: Path
    serial_files: tuple[Path, ...]
    shards: tuple[TestShardPlan, ...]
    stable_runtime_root: Path
    scratch_root: Path
    log_root: Path
    execution_lock_path: Path
    runtime_key: str
    runtime_receipt: bytes
    partition: PartitionWeights
    dry_run: bool
    measurement_context: dict[str, Any]
    timing_artifact_path: Path | None = None
    use: PlanUse = field(default_factory=PlanUse, compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class ShardResult:
    index: int
    returncode: int
    log_path: Path
    timed_out: bool = False
    cancelled: bool = False
    failure_category: str | None = None
    timing_report: dict[str, Any] | None = field(default=None, compare=False, repr=False)


class ParallelCleanupError(RuntimeError):
    failure_category = "cleanup"

    def __init__(self, component: str) -> None:
        self.cleanup_component = component
        super().__init__(f"parallel {component} cleanup failed")


RuntimePreparer = Callable[..., dict[str, str]]
BoundedRunner = Callable[..., BoundedBinaryProcessResult]


def _resolved_test_root(repo_root: Path, test_root: Path) -> tuple[Path, Path]:
    repo = repo_root.expanduser().resolve(strict=True)
    candidate = test_root if test_root.is_absolute() else repo / test_root
    tests = candidate.expanduser().resolve(strict=True)
    try:
        tests.relative_to(repo)
    except ValueError as exc:
        raise ValueError("test root must stay within the repository") from exc
    if not tests.is_dir() or tests.is_symlink():
        raise ValueError("test root must be a real directory")
    return repo, tests


def equivalent_test_file_shards(
    test_root: Path,
    *,
    shard_count: int = DEFAULT_SHARD_COUNT,
    weights: Mapping[Path, int] | None = None,
) -> tuple[tuple[Path, ...], tuple[tuple[Path, ...], ...]]:
    if isinstance(shard_count, bool) or not isinstance(shard_count, int) or shard_count < 1:
        raise ValueError("shard_count must be positive")
    serial = discover_test_files(test_root)
    shards = partition_test_files(serial, shard_count=shard_count, weights=weights)
    if any(not shard for shard in shards):
        raise ValueError("shard_count cannot exceed the pytest file count")
    flattened = tuple(path for shard in shards for path in shard)
    if len(flattened) != len(set(flattened)) or set(flattened) != set(serial):
        raise RuntimeError("serial and sharded pytest file collections differ")
    return serial, shards


def _validated_timeout(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("timeout_seconds must be a finite number")
    normalized = float(value)
    if (
        not math.isfinite(normalized)
        or normalized < MIN_TIMEOUT_SECONDS
        or normalized > MAX_TIMEOUT_SECONDS
    ):
        raise ValueError("timeout_seconds is outside the supported bounded range")
    return normalized


def _repo_execution_lock_path(repo: Path, *, create_parent: bool) -> Path:
    repo_key = str(repo).casefold() if os.name == "nt" else str(repo)
    lock_name = hashlib.sha256(repo_key.encode()).hexdigest() + ".lock"
    if create_parent:
        parent = private_runtime_directory("change-loop-locks")
    else:
        parent = Path.home().expanduser().resolve(strict=True) / ".agency-runtime"
        parent /= "change-loop-locks"
    return parent / lock_name


def _projected_runtime(
    contract: RuntimeContract,
    *,
    runtime_home: Path | None,
) -> tuple[dict[str, str], Path, Path]:
    root = ci_runtime_root_path(contract.label, home_dir=runtime_home)
    python = root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    runtime = {
        "AGENCY_CI_ROOT": str(root),
        "AGENCY_CI_PYTHON": str(python),
        "AGENCY_CI_HOME": str(root / "home"),
        "AGENCY_CI_TEMP": str(root / "tmp"),
    }
    if contract.node_source is not None:
        runtime["AGENCY_CI_NODE"] = str(root / "bin" / ("node.exe" if os.name == "nt" else "node"))
    return runtime, root, python


def _validate_windows_runtime_geometry(
    runtime_root: Path,
    python: Path,
    *,
    shard_count: int,
    is_windows: bool = os.name == "nt",
) -> None:
    if not is_windows:
        return
    scratch_root = runtime_root / _SCRATCH_ROOT_NAME
    paths = {
        "private Python": python,
        "pytest base directory": (
            scratch_root / f"shard-{shard_count - 1:02d}" / "tmp" / "pytest-change-loop"
        ),
    }
    for label, path in paths.items():
        length = len(str(path))
        if length > MAX_WINDOWS_CRITICAL_PATH_CHARS:
            raise ValueError(
                f"{label} path length {length} exceeds the supported Windows "
                f"limit {MAX_WINDOWS_CRITICAL_PATH_CHARS}; use a shorter runtime home"
            )


def build_parallel_test_plan(
    *,
    repo_root: Path,
    test_root: Path = Path("tests"),
    shard_count: int = DEFAULT_SHARD_COUNT,
    label: str = "local-change-loop",
    runtime_home: Path | None = None,
    runtime_preparer: RuntimePreparer | None = None,
    ambient_environment: Mapping[str, str] | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    dry_run: bool = False,
    collect_file_timings: bool = False,
    partition_strategy: str = "auto",
    require_exact_shard_weights: bool = False,
) -> ParallelTestPlan:
    repo, tests = _resolved_test_root(repo_root, test_root)
    relative_test_root = tests.relative_to(repo).as_posix()
    if not relative_test_root:
        relative_test_root = "."
    timeout = _validated_timeout(timeout_seconds)
    environment = dict(os.environ if ambient_environment is None else ambient_environment)
    contract = build_runtime_contract(repo, label, environment)
    serial = discover_test_files(tests)
    partition = load_partition_weights(
        repo,
        serial,
        worker_count=shard_count,
        pytest_flags=PYTEST_FLAGS,
        runtime_key=contract.key,
        test_root=relative_test_root,
        strategy=partition_strategy,
        require_exact=require_exact_shard_weights,
    )
    selected_shards = partition_test_files(
        serial,
        shard_count=shard_count,
        weights=partition.weights,
    )
    flattened = tuple(path for shard in selected_shards for path in shard)
    if len(flattened) != len(set(flattened)) or set(flattened) != set(serial):
        raise RuntimeError("serial and sharded pytest file collections differ")
    measurement_context = build_measurement_context(
        repo,
        serial,
        worker_count=shard_count,
        pytest_flags=PYTEST_FLAGS,
        runtime_key=contract.key,
        test_root=relative_test_root,
    )
    preparer = runtime_preparer or prepare_ci_runtime
    receipt = runtime_receipt_payload(contract)
    projected_runtime, projected_root, projected_python = _projected_runtime(
        contract,
        runtime_home=runtime_home,
    )
    _validate_windows_runtime_geometry(
        projected_root,
        projected_python,
        shard_count=shard_count,
    )
    execution_lock_path = _repo_execution_lock_path(
        repo,
        create_parent=not dry_run,
    )
    if dry_run:
        runtime, runtime_root, python = projected_runtime, projected_root, projected_python
        contract.assert_node_unchanged()
        log_root = runtime_root / _LOG_ROOT_NAME
    else:
        with private_runtime_lock(
            execution_lock_path,
            wait_seconds=_LOCK_WAIT_SECONDS,
            busy_message="parallel test repository is busy",
        ):
            runtime = preparer(
                contract.label,
                home_dir=runtime_home,
                node_resolver=contract.node_resolver,
                system_site_packages=False,
                runtime_contract=contract.key,
            )
            contract.assert_node_unchanged()
            runtime_root = runtime_path(runtime, "AGENCY_CI_ROOT")
            python = runtime_path(runtime, "AGENCY_CI_PYTHON")
            _validate_windows_runtime_geometry(
                runtime_root,
                python,
                shard_count=shard_count,
            )
            create_exact_private_file(runtime_root / RUNTIME_RECEIPT_NAME, receipt)
            log_root = ensure_owned_directory(
                runtime_root,
                _LOG_ROOT_NAME,
                _LOG_ROOT_RECEIPT_NAME,
                _LOG_ROOT_RECEIPT,
            )
    try:
        python.relative_to(runtime_root)
    except ValueError as exc:
        raise RuntimeError("parallel test Python escaped its stable runtime") from exc
    try:
        runtime_root.relative_to(repo)
    except ValueError:
        pass
    else:
        raise RuntimeError("parallel test runtime must stay outside the repository")
    scratch_root = runtime_root / _SCRATCH_ROOT_NAME
    plans: list[TestShardPlan] = []
    for index, selected in enumerate(selected_shards):
        shard_root = scratch_root / f"shard-{index:02d}"
        private_home = shard_root / "home"
        private_temp = shard_root / "tmp"
        base_temp = private_temp / "pytest-change-loop"
        timing_path = shard_root / "pytest-file-timings.json" if collect_file_timings else None
        relative_files = tuple(path.relative_to(repo) for path in selected)
        timing_arguments = (
            ()
            if timing_path is None
            else (
                "-p",
                "scripts.pytest_file_timing",
                REPORT_OPTION,
                str(timing_path),
                SHARD_OPTION,
                str(index),
            )
        )
        command = (
            str(python),
            "-m",
            "pytest",
            *timing_arguments,
            *(path.as_posix() for path in relative_files),
            *PYTEST_FLAGS,
            "--basetemp",
            str(base_temp),
        )
        runtime_for_environment = runtime
        projected_node: str | None = None
        if dry_run and "AGENCY_CI_NODE" in runtime:
            runtime_for_environment = dict(runtime)
            projected_node = runtime_for_environment.pop("AGENCY_CI_NODE")
        shard_environment = private_child_environment(
            environment,
            runtime_for_environment,
            runtime_root=runtime_root,
            python=python,
            private_home=private_home,
            private_temp=private_temp,
            dependency_paths=contract.dependency_paths,
            repo_root=repo,
        )
        if projected_node is not None:
            shard_environment["AGENCY_CI_NODE"] = projected_node
        plans.append(
            TestShardPlan(
                index=index,
                test_files=relative_files,
                command=command,
                environment=shard_environment,
                working_directory=repo,
                stable_runtime_root=runtime_root,
                run_root=shard_root,
                private_home=private_home,
                private_temp=private_temp,
                base_temp=base_temp,
                log_path=log_root / f"pytest-shard-{index:02d}.latest.log",
                timeout_seconds=timeout,
                weight_total=sum(partition.weights[path] for path in selected),
                timing_path=timing_path,
            )
        )
    return ParallelTestPlan(
        repo_root=repo,
        test_root=tests,
        serial_files=tuple(path.relative_to(repo) for path in serial),
        shards=tuple(plans),
        stable_runtime_root=runtime_root,
        scratch_root=scratch_root,
        log_root=log_root,
        execution_lock_path=execution_lock_path,
        runtime_key=contract.key,
        runtime_receipt=receipt,
        partition=partition,
        dry_run=dry_run,
        measurement_context=measurement_context,
        timing_artifact_path=(log_root / _TIMING_MANIFEST_NAME if collect_file_timings else None),
    )


def _partition_evidence(plan: ParallelTestPlan) -> dict[str, Any]:
    digest = hashlib.sha256()
    shards = []
    for shard in sorted(plan.shards, key=lambda item: item.index):
        digest.update(shard.index.to_bytes(4, "big"))
        paths = [path.as_posix() for path in shard.test_files]
        for path in paths:
            encoded = path.encode("utf-8")
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
        shards.append(
            {
                "index": shard.index,
                "test_files": paths,
                "weight_total": shard.weight_total,
            }
        )
    return {
        **plan.partition.preview(),
        "assignment_sha256": digest.hexdigest(),
        "shards": shards,
    }


def plan_preview(plan: ParallelTestPlan) -> dict[str, Any]:
    preview: dict[str, Any] = {
        "schema_version": "agency.local-parallel-tests.v5",
        "collection": {
            "equivalent": True,
            "serial_file_count": len(plan.serial_files),
            "sharded_file_count": sum(len(shard.test_files) for shard in plan.shards),
        },
        "partition": _partition_evidence(plan),
        "measurement_context": plan.measurement_context,
        "repo_root": plan.repo_root.as_posix(),
        "runtime_key": plan.runtime_key,
        "stable_runtime_root": plan.stable_runtime_root.as_posix(),
        "scratch_root": plan.scratch_root.as_posix(),
        "shard_count": len(plan.shards),
        "shards": [
            {
                "index": shard.index,
                "test_files": [path.as_posix() for path in shard.test_files],
                "command": list(shard.command),
                "working_directory": shard.working_directory.as_posix(),
                "private_environment": {
                    name: shard.environment[name]
                    for name in _PRIVATE_ENVIRONMENT_KEYS
                    if name in shard.environment
                },
                "run_root": shard.run_root.as_posix(),
                "basetemp": shard.base_temp.as_posix(),
                "log": shard.log_path.as_posix(),
                "timeout_seconds": shard.timeout_seconds,
                "weight_total": shard.weight_total,
            }
            for shard in plan.shards
        ],
    }
    if plan.timing_artifact_path is not None:
        preview["file_timings"] = {
            "artifact": plan.timing_artifact_path.as_posix(),
            "enabled": True,
            "measurement_context": plan.measurement_context,
            "plugin": "scripts.pytest_file_timing",
            "run_id_binding": "execution-generated",
        }
    return preview


def _capture_budgets(maximum_bytes: int) -> tuple[int, int]:
    stderr_channel = max(_MIN_STDERR_LOG_BYTES, maximum_bytes // 4)
    stdout_channel = maximum_bytes - _STATUS_LOG_BYTES - stderr_channel
    stdout_payload = stdout_channel - len(b"[stdout]\n") - 1
    stderr_payload = stderr_channel - len(b"[stderr]\n") - 1
    if min(stdout_payload, stderr_payload) <= len(_TRUNCATION_MARKER):
        raise RuntimeError("parallel shard log budget cannot retain both output channels")
    return stdout_payload, stderr_payload


def _failure_category(result: BoundedBinaryProcessResult) -> str | None:
    value = result.failure_category
    if value is None and result.cancelled:
        value = "cancelled"
    if value is None and result.timed_out:
        value = "timeout"
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", value):
        return "invalid-result"
    return value


def _result_log_payload(
    shard: TestShardPlan,
    *,
    run_id: str,
    started_at_unix_ns: int,
    result: BoundedBinaryProcessResult | None,
    maximum_bytes: int,
    error_name: str | None = None,
    failure_category_override: str | None = None,
) -> bytes:
    stdout_budget, stderr_budget = _capture_budgets(maximum_bytes)
    command = json.dumps(list(shard.command), ensure_ascii=True, separators=(",", ":")).encode()
    status = {
        "cancelled": bool(result.cancelled) if result is not None else False,
        "command_items": len(shard.command),
        "command_sha256": hashlib.sha256(command).hexdigest(),
        "failure_category": (
            "runner" if result is None else failure_category_override or _failure_category(result)
        ),
        "returncode": int(result.returncode) if result is not None else 1,
        "run_id": run_id,
        "runner_error": None if error_name is None else error_name[:80],
        "shard": shard.index,
        "started_at_unix_ns": started_at_unix_ns,
        "stderr_truncated": bool(result.stderr_truncated) if result is not None else False,
        "stdout_truncated": bool(result.stdout_truncated) if result is not None else False,
        "timed_out": bool(result.timed_out) if result is not None else False,
    }
    status_payload = (
        json.dumps(status, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
        + b"\n"
    )
    if len(status_payload) > _STATUS_LOG_BYTES:
        raise RuntimeError("parallel shard status exceeded its fixed log reservation")
    stdout = (
        b""
        if result is None
        else bounded_head_tail(result.stdout, stdout_budget, _TRUNCATION_MARKER)
    )
    stderr = (
        b""
        if result is None
        else bounded_head_tail(result.stderr, stderr_budget, _TRUNCATION_MARKER)
    )
    return status_payload + b"[stdout]\n" + stdout + b"\n[stderr]\n" + stderr + b"\n"


def _bounded_nonnegative_integer(value: object, *, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ValueError("file timing report contains an invalid bounded integer")
    return value


def _canonical_timing_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("file timing report path is not canonical")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError("file timing report path is not canonical")
    return value


def _validated_phase_map(value: object, *, maximum: int) -> dict[str, int]:
    phases = {"call", "setup", "teardown"}
    if not isinstance(value, dict) or set(value) != phases:
        raise ValueError("file timing phase map has an invalid shape")
    return {
        phase: _bounded_nonnegative_integer(value[phase], maximum=maximum)
        for phase in sorted(phases)
    }


def _load_timing_report(
    shard: TestShardPlan,
    *,
    run_id: str,
    exit_status: int,
) -> dict[str, Any]:
    if shard.timing_path is None:
        raise ValueError("file timing was not requested for this shard")
    raw = read_bounded_regular_file(
        shard.timing_path,
        limit=MAX_SHARD_TIMING_BYTES,
        label="pytest file timing report",
    )
    if not exact_private_file_is_valid(shard.timing_path, raw):
        raise ValueError("pytest file timing report is not owner-trusted")
    payload = safe_load_bounded_json(
        raw,
        maximum_bytes=MAX_SHARD_TIMING_BYTES,
        maximum_depth=5,
        maximum_nodes=100_000,
    )
    expected_keys = {
        "collected_item_count",
        "errors",
        "exit_status",
        "files",
        "phase_report_count",
        "run_id",
        "schema",
        "shard",
    }
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise ValueError("pytest file timing report has an invalid shape")
    if (
        payload["schema"] != SHARD_TIMING_SCHEMA
        or payload["run_id"] != run_id
        or payload["errors"] != []
        or _bounded_nonnegative_integer(payload["shard"], maximum=4096) != shard.index
        or _bounded_nonnegative_integer(payload["exit_status"], maximum=255) != exit_status
    ):
        raise ValueError("pytest file timing report identity is invalid")
    files = payload["files"]
    if not isinstance(files, list) or len(files) != len(shard.test_files):
        raise ValueError("pytest file timing file count is invalid")
    expected_paths = {path.as_posix() for path in shard.test_files}
    observed_paths: set[str] = set()
    collected_items = 0
    phase_reports = 0
    validated_files: list[dict[str, Any]] = []
    for item in files:
        if not isinstance(item, dict) or set(item) != {
            "collected_items",
            "duration_ns",
            "path",
            "report_counts",
            "total_ns",
        }:
            raise ValueError("pytest file timing entry has an invalid shape")
        path = _canonical_timing_path(item["path"])
        if path in observed_paths:
            raise ValueError("pytest file timing report contains a duplicate path")
        observed_paths.add(path)
        item_count = _bounded_nonnegative_integer(item["collected_items"], maximum=2**31 - 1)
        durations = _validated_phase_map(item["duration_ns"], maximum=2**63 - 1)
        counts = _validated_phase_map(item["report_counts"], maximum=2**31 - 1)
        total = _bounded_nonnegative_integer(item["total_ns"], maximum=2**63 - 1)
        if total != sum(durations.values()):
            raise ValueError("pytest file timing total does not match its phases")
        collected_items += item_count
        phase_reports += sum(counts.values())
        validated_files.append(
            {
                "collected_items": item_count,
                "duration_ns": durations,
                "path": path,
                "report_counts": counts,
                "total_ns": total,
            }
        )
    if observed_paths != expected_paths:
        raise ValueError("pytest file timing paths differ from the planned shard")
    if collected_items != _bounded_nonnegative_integer(
        payload["collected_item_count"], maximum=2**31 - 1
    ) or phase_reports != _bounded_nonnegative_integer(
        payload["phase_report_count"], maximum=2**31 - 1
    ):
        raise ValueError("pytest file timing aggregate counts are inconsistent")
    return {
        "collected_item_count": collected_items,
        "exit_status": exit_status,
        "files": sorted(validated_files, key=lambda item: item["path"]),
        "phase_report_count": phase_reports,
        "run_id": run_id,
        "schema": SHARD_TIMING_SCHEMA,
        "shard": shard.index,
    }


def _run_shard(
    shard: TestShardPlan,
    cancel_event: threading.Event,
    maximum_log_bytes: int,
    bounded_runner: BoundedRunner,
    run_id: str,
    started_at_unix_ns: int,
) -> ShardResult:
    stdout_budget, stderr_budget = _capture_budgets(maximum_log_bytes)
    environment = dict(shard.environment)
    if shard.timing_path is not None:
        environment[RUN_ID_ENVIRONMENT_KEY] = run_id
    try:
        result = bounded_runner(
            shard.command,
            timeout=shard.timeout_seconds,
            cwd=str(shard.working_directory),
            env=environment,
            max_stdout_bytes=stdout_budget,
            max_stderr_bytes=stderr_budget,
            retain_output_tail=True,
            cancel_event=cancel_event,
        )
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        write_atomic_bounded_log(
            shard.log_path,
            _result_log_payload(
                shard,
                run_id=run_id,
                started_at_unix_ns=started_at_unix_ns,
                result=None,
                maximum_bytes=maximum_log_bytes,
                error_name=type(exc).__name__,
            ),
            maximum_log_bytes,
            marker=_TRUNCATION_MARKER,
        )
        return ShardResult(shard.index, 1, shard.log_path, failure_category="runner")
    category = _failure_category(result)
    timing_report: dict[str, Any] | None = None
    if shard.timing_path is not None:
        try:
            timing_report = _load_timing_report(
                shard,
                run_id=run_id,
                exit_status=result.returncode,
            )
        except (OSError, TypeError, ValueError):
            if result.returncode == 0 and category is None:
                category = "timing"
    write_atomic_bounded_log(
        shard.log_path,
        _result_log_payload(
            shard,
            run_id=run_id,
            started_at_unix_ns=started_at_unix_ns,
            result=result,
            maximum_bytes=maximum_log_bytes,
            failure_category_override=category,
        ),
        maximum_log_bytes,
        marker=_TRUNCATION_MARKER,
    )
    return ShardResult(
        shard.index,
        result.returncode,
        shard.log_path,
        timed_out=result.timed_out,
        cancelled=result.cancelled,
        failure_category=category,
        timing_report=timing_report,
    )


def _completed_results(futures: list[Future[ShardResult]]) -> tuple[ShardResult, ...]:
    results: list[ShardResult] = []
    for future in futures:
        if not future.done() or future.cancelled():
            continue
        try:
            results.append(future.result())
        except BaseException:
            continue
    return tuple(sorted(results, key=lambda item: item.index))


def _shard_succeeded(result: ShardResult) -> bool:
    return bool(
        result.returncode == 0
        and not result.timed_out
        and not result.cancelled
        and result.failure_category is None
    )


def _timing_artifact_payload(
    plan: ParallelTestPlan,
    results: tuple[ShardResult, ...],
    *,
    run_id: str,
) -> bytes | None:
    if plan.timing_artifact_path is None:
        return None
    if (
        len(results) != len(plan.shards)
        or any(not _shard_succeeded(result) for result in results)
        or any(result.timing_report is None for result in results)
    ):
        return None
    expected_paths = {path.as_posix() for path in plan.serial_files}
    observed_paths: set[str] = set()
    files: list[dict[str, Any]] = []
    shards: list[dict[str, int]] = []
    collected_item_count = 0
    phase_report_count = 0
    for result in sorted(results, key=lambda item: item.index):
        report = result.timing_report
        if report is None or report["run_id"] != run_id or report["shard"] != result.index:
            raise RuntimeError("pytest file timing report identity changed before consolidation")
        collected = int(report["collected_item_count"])
        phases = int(report["phase_report_count"])
        collected_item_count += collected
        phase_report_count += phases
        shards.append(
            {
                "collected_item_count": collected,
                "exit_status": int(report["exit_status"]),
                "index": result.index,
                "phase_report_count": phases,
            }
        )
        for item in report["files"]:
            path = str(item["path"])
            if path in observed_paths:
                raise RuntimeError("pytest file timing paths overlap between shards")
            observed_paths.add(path)
            files.append({**item, "shard": result.index})
    if observed_paths != expected_paths:
        raise RuntimeError("pytest file timing union differs from the serial file plan")
    payload = {
        "collected_item_count": collected_item_count,
        "files": sorted(files, key=lambda item: item["path"]),
        "measurement_context": plan.measurement_context,
        "partition": _partition_evidence(plan),
        "phase_report_count": phase_report_count,
        "run_id": run_id,
        "schema": RUN_TIMING_SCHEMA,
        "shard_count": len(plan.shards),
        "shards": shards,
        "test_file_count": len(plan.serial_files),
    }
    encoded = (
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode(
            "ascii"
        )
        + b"\n"
    )
    if len(encoded) > MAX_RUN_TIMING_BYTES:
        raise RuntimeError("consolidated pytest file timing artifact exceeded its byte bound")
    return encoded


def _publish_timing_artifact(plan: ParallelTestPlan, payload: bytes | None) -> None:
    if payload is None:
        return
    timing_artifact_path = plan.timing_artifact_path
    if timing_artifact_path is None:
        raise RuntimeError("pytest file timing artifact path is unavailable")
    try:
        write_atomic_bounded_log(
            timing_artifact_path,
            payload,
            MAX_RUN_TIMING_BYTES,
            marker=_TRUNCATION_MARKER,
        )
    except BaseException as exc:
        raise ParallelCleanupError("timing-manifest") from exc


def _execute_shards(
    plan: ParallelTestPlan,
    *,
    maximum_log_bytes: int,
    bounded_runner: BoundedRunner,
    run_id: str,
    started_at_unix_ns: int,
) -> tuple[int, tuple[ShardResult, ...]]:
    cancel_event = threading.Event()
    executor: ThreadPoolExecutor | None = None
    futures: list[Future[ShardResult]] = []
    results: list[ShardResult] = []
    interruption: KeyboardInterrupt | None = None
    primary_error: BaseException | None = None
    try:
        executor = ThreadPoolExecutor(
            max_workers=len(plan.shards), thread_name_prefix="agency-pytest-shard"
        )
        futures = [
            executor.submit(
                _run_shard,
                shard,
                cancel_event,
                maximum_log_bytes,
                bounded_runner,
                run_id,
                started_at_unix_ns,
            )
            for shard in plan.shards
        ]
        results.extend(future.result() for future in as_completed(futures))
    except KeyboardInterrupt as exc:
        interruption = exc
        cancel_event.set()
        for future in futures:
            future.cancel()
    except BaseException as exc:
        primary_error = exc
        cancel_event.set()
        for future in futures:
            future.cancel()
    shutdown_error: BaseException | None = None
    if executor is not None:
        try:
            executor.shutdown(wait=True, cancel_futures=True)
        except BaseException as exc:
            shutdown_error = exc
            cancel_event.set()
            for future in futures:
                future.cancel()
            with suppress(BaseException):
                executor.shutdown(wait=True, cancel_futures=True)
    if shutdown_error is not None:
        if primary_error is not None:
            add_exception_note(
                primary_error,
                f"parallel executor shutdown failed ({type(shutdown_error).__name__})",
            )
        elif interruption is not None:
            add_exception_note(
                interruption,
                f"parallel executor shutdown failed ({type(shutdown_error).__name__})",
            )
            primary_error = ParallelCleanupError("cancellation")
        else:
            primary_error = ParallelCleanupError("executor")
    if primary_error is not None:
        raise primary_error
    if interruption is not None:
        return 130, _completed_results(futures)
    ordered = tuple(sorted(results, key=lambda item: item.index))
    return (0 if all(_shard_succeeded(result) for result in ordered) else 1), ordered


def _assert_plan_inputs_unchanged(plan: ParallelTestPlan) -> None:
    current = discover_test_files(plan.test_root)
    current_relative = tuple(path.relative_to(plan.repo_root) for path in current)
    if current_relative != plan.serial_files:
        raise RuntimeError("pytest file inventory changed after plan construction")
    current_context = build_measurement_context(
        plan.repo_root,
        current,
        worker_count=len(plan.shards),
        pytest_flags=PYTEST_FLAGS,
        runtime_key=plan.runtime_key,
        test_root=plan.test_root.relative_to(plan.repo_root).as_posix() or ".",
    )
    if current_context != plan.measurement_context:
        raise RuntimeError("pytest source or timing harness changed after plan construction")
    if plan.partition.algorithm == "source-bytes-lpt-v1":
        current_weights = {path: max(1, path.stat().st_size) for path in current}
        if current_weights != plan.partition.weights:
            raise RuntimeError("pytest source-byte weights changed after plan construction")
        return
    if plan.partition.algorithm != "duration-lpt-v1":
        raise RuntimeError("pytest partition algorithm is unsupported")
    current_partition = load_partition_weights(
        plan.repo_root,
        current,
        worker_count=len(plan.shards),
        pytest_flags=PYTEST_FLAGS,
        runtime_key=plan.runtime_key,
        test_root=plan.test_root.relative_to(plan.repo_root).as_posix() or ".",
        require_exact=plan.partition.status == "exact",
    )
    if (
        current_partition.profile_digest != plan.partition.profile_digest
        or current_partition.status != plan.partition.status
        or current_partition.weights != plan.partition.weights
    ):
        raise RuntimeError("pytest timing weights changed after plan construction")


def run_parallel_test_plan(
    plan: ParallelTestPlan,
    *,
    maximum_log_bytes: int = DEFAULT_MAX_LOG_BYTES,
    bounded_runner: BoundedRunner = run_bounded_binary_process,
) -> tuple[int, tuple[ShardResult, ...]]:
    if (
        isinstance(maximum_log_bytes, bool)
        or not isinstance(maximum_log_bytes, int)
        or not MIN_LOG_BYTES <= maximum_log_bytes <= MAX_LOG_BYTES
    ):
        raise ValueError("maximum_log_bytes is outside the supported bounded range")
    if plan.dry_run:
        raise ValueError("a dry-run plan cannot be executed")
    for shard in plan.shards:
        _validated_timeout(shard.timeout_seconds)
    _assert_plan_inputs_unchanged(plan)
    plan.use.begin()
    run_id = secrets.token_hex(16)
    started_at_unix_ns = time.time_ns()
    started = time.monotonic()
    try:
        with private_runtime_lock(
            plan.execution_lock_path,
            wait_seconds=0,
            busy_message="another parallel test run is active",
        ):
            if not exact_private_file_is_valid(
                plan.stable_runtime_root / RUNTIME_RECEIPT_NAME,
                plan.runtime_receipt,
            ) or not exact_private_file_is_valid(
                plan.log_root / _LOG_ROOT_RECEIPT_NAME,
                _LOG_ROOT_RECEIPT,
            ):
                raise RuntimeError("parallel test runtime ownership changed")
            clear_reserved_latest_logs(
                plan.log_root,
                manifest_name=_LOG_MANIFEST_NAME,
                additional_names=(_TIMING_MANIFEST_NAME,),
            )
            scratch_identity = reset_private_scratch(
                plan.scratch_root,
                child_directories=(
                    path
                    for shard in plan.shards
                    for path in (shard.run_root, shard.private_home, shard.private_temp)
                ),
            )
            outcome: tuple[int, tuple[ShardResult, ...]] | None = None
            primary_error: BaseException | None = None
            try:
                outcome = _execute_shards(
                    plan,
                    maximum_log_bytes=maximum_log_bytes,
                    bounded_runner=bounded_runner,
                    run_id=run_id,
                    started_at_unix_ns=started_at_unix_ns,
                )
            except BaseException as exc:
                primary_error = exc
            try:
                remove_private_directory(scratch_identity)
            except BaseException as cleanup_error:
                if primary_error is not None:
                    add_exception_note(
                        primary_error,
                        f"parallel scratch cleanup failed ({type(cleanup_error).__name__})",
                    )
                elif outcome is not None and outcome[0] == 130:
                    primary_error = ParallelCleanupError("cancellation")
                else:
                    primary_error = ParallelCleanupError("scratch")
            if primary_error is not None:
                raise primary_error
            if outcome is None:
                raise RuntimeError("parallel execution completed without a shard outcome")
            if plan.timing_artifact_path is not None:
                _assert_plan_inputs_unchanged(plan)
            elapsed = time.monotonic() - started
            timing_payload = _timing_artifact_payload(plan, outcome[1], run_id=run_id)
            _publish_timing_artifact(plan, timing_payload)
            manifest = {
                "elapsed_seconds": round(elapsed, 6),
                "exit_code": outcome[0],
                "measurement_context": plan.measurement_context,
                "partition": {
                    **_partition_evidence(plan),
                },
                "run_id": run_id,
                "schema": "agency.local-parallel-tests.latest.v2",
                "shards": [
                    {
                        "cancelled": result.cancelled,
                        "failure_category": result.failure_category,
                        "index": result.index,
                        "planned_weight": plan.shards[result.index].weight_total,
                        "returncode": result.returncode,
                        "timed_out": result.timed_out,
                    }
                    for result in outcome[1]
                ],
                "started_at_unix_ns": started_at_unix_ns,
            }
            if plan.timing_artifact_path is not None:
                manifest["file_timings"] = {
                    "artifact": plan.timing_artifact_path.name,
                    "complete": timing_payload is not None,
                    "schema": RUN_TIMING_SCHEMA,
                }
            try:
                write_atomic_bounded_log(
                    plan.log_root / _LOG_MANIFEST_NAME,
                    json.dumps(manifest, separators=(",", ":"), sort_keys=True).encode() + b"\n",
                    64 * 1024,
                    marker=_TRUNCATION_MARKER,
                )
            except BaseException as exc:
                raise ParallelCleanupError("manifest") from exc
            return outcome
    finally:
        plan.use.finish(run_id=run_id, elapsed_seconds=time.monotonic() - started)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--root", type=Path, default=Path("tests"))
    parser.add_argument("--shards", type=int, default=DEFAULT_SHARD_COUNT)
    parser.add_argument("--label", default="local-change-loop")
    parser.add_argument("--runtime-home", type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-log-bytes", type=int, default=DEFAULT_MAX_LOG_BYTES)
    parser.add_argument("--collect-file-timings", action="store_true")
    parser.add_argument(
        "--partition",
        choices=("auto", "source-bytes"),
        default="auto",
    )
    parser.add_argument("--require-exact-shard-weights", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        plan = build_parallel_test_plan(
            repo_root=args.repo_root,
            test_root=args.root,
            shard_count=args.shards,
            label=args.label,
            runtime_home=args.runtime_home,
            timeout_seconds=args.timeout_seconds,
            dry_run=args.dry_run,
            collect_file_timings=args.collect_file_timings,
            partition_strategy=args.partition,
            require_exact_shard_weights=args.require_exact_shard_weights,
        )
        if args.dry_run:
            print(json.dumps(plan_preview(plan), indent=2, sort_keys=True))
            return 0
        print(
            f"running {len(plan.shards)} isolated pytest shards "
            f"partition={plan.partition.algorithm} status={plan.partition.status}"
        )
        exit_code, results = run_parallel_test_plan(plan, maximum_log_bytes=args.max_log_bytes)
        for result in results:
            if not _shard_succeeded(result):
                print(
                    f"shard {result.index}: exit={result.returncode} "
                    f"category={result.failure_category or 'test'} "
                    f"log={result.log_path.as_posix()}"
                )
        passed = sum(_shard_succeeded(result) for result in results)
        elapsed = 0.0 if plan.use.elapsed_seconds is None else plan.use.elapsed_seconds
        print(
            f"parallel pytest complete: {passed}/{len(plan.shards)} shards passed "
            f"run_id={plan.use.run_id or 'external'} elapsed_seconds={elapsed:.6f}"
        )
        return exit_code
    except (OSError, RuntimeError, ValueError) as exc:
        category = str(getattr(exc, "failure_category", "runner"))
        component = getattr(exc, "cleanup_component", None)
        suffix = "" if component is None else f" component={component}"
        print(
            f"parallel test runner failed: category={category}{suffix}: {exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
