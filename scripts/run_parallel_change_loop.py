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
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
from scripts.select_test_shard import select_test_files

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
    dry_run: bool
    use: PlanUse = field(default_factory=PlanUse, compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class ShardResult:
    index: int
    returncode: int
    log_path: Path
    timed_out: bool = False
    cancelled: bool = False
    failure_category: str | None = None


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
) -> tuple[tuple[Path, ...], tuple[tuple[Path, ...], ...]]:
    if isinstance(shard_count, bool) or not isinstance(shard_count, int) or shard_count < 1:
        raise ValueError("shard_count must be positive")
    serial = select_test_files(test_root, shard_index=0, shard_count=1)
    shards = tuple(
        select_test_files(test_root, shard_index=index, shard_count=shard_count)
        for index in range(shard_count)
    )
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
) -> ParallelTestPlan:
    repo, tests = _resolved_test_root(repo_root, test_root)
    serial, selected_shards = equivalent_test_file_shards(tests, shard_count=shard_count)
    timeout = _validated_timeout(timeout_seconds)
    environment = dict(os.environ if ambient_environment is None else ambient_environment)
    contract = build_runtime_contract(repo, label, environment)
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
        relative_files = tuple(path.relative_to(repo) for path in selected)
        command = (
            str(python),
            "-m",
            "pytest",
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
        dry_run=dry_run,
    )


def plan_preview(plan: ParallelTestPlan) -> dict[str, Any]:
    return {
        "schema_version": "agency.local-parallel-tests.v4",
        "collection": {
            "equivalent": True,
            "serial_file_count": len(plan.serial_files),
            "sharded_file_count": sum(len(shard.test_files) for shard in plan.shards),
        },
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
            }
            for shard in plan.shards
        ],
    }


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
) -> bytes:
    stdout_budget, stderr_budget = _capture_budgets(maximum_bytes)
    command = json.dumps(list(shard.command), ensure_ascii=True, separators=(",", ":")).encode()
    status = {
        "cancelled": bool(result.cancelled) if result is not None else False,
        "command_items": len(shard.command),
        "command_sha256": hashlib.sha256(command).hexdigest(),
        "failure_category": "runner" if result is None else _failure_category(result),
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


def _run_shard(
    shard: TestShardPlan,
    cancel_event: threading.Event,
    maximum_log_bytes: int,
    bounded_runner: BoundedRunner,
    run_id: str,
    started_at_unix_ns: int,
) -> ShardResult:
    stdout_budget, stderr_budget = _capture_budgets(maximum_log_bytes)
    try:
        result = bounded_runner(
            shard.command,
            timeout=shard.timeout_seconds,
            cwd=str(shard.working_directory),
            env=dict(shard.environment),
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
    write_atomic_bounded_log(
        shard.log_path,
        _result_log_payload(
            shard,
            run_id=run_id,
            started_at_unix_ns=started_at_unix_ns,
            result=result,
            maximum_bytes=maximum_log_bytes,
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
            clear_reserved_latest_logs(plan.log_root, manifest_name=_LOG_MANIFEST_NAME)
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
            elapsed = time.monotonic() - started
            manifest = {
                "elapsed_seconds": round(elapsed, 6),
                "exit_code": outcome[0],
                "run_id": run_id,
                "schema": "agency.local-parallel-tests.latest.v1",
                "shards": [
                    {
                        "cancelled": result.cancelled,
                        "failure_category": result.failure_category,
                        "index": result.index,
                        "returncode": result.returncode,
                        "timed_out": result.timed_out,
                    }
                    for result in outcome[1]
                ],
                "started_at_unix_ns": started_at_unix_ns,
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
        )
        if args.dry_run:
            print(json.dumps(plan_preview(plan), indent=2, sort_keys=True))
            return 0
        print(f"running {len(plan.shards)} isolated pytest shards")
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
