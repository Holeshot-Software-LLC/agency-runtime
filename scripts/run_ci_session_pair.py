"""Run two exact CI pytest sessions concurrently inside owned process trees.

This runner reduces hosted job fanout without merging pytest processes or their
state.  Each session receives its own attested Python runtime, HOME, temporary
directory, pytest base directory, and coverage data path.  Output is captured
with fixed head-and-tail bounds and emitted under stable session/phase labels.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.owned_process import (
    BoundedBinaryProcessResult,
    run_bounded_binary_process,
)
from scripts.select_test_shard import select_test_files

ROOT = Path(__file__).resolve().parents[1]

_SAFE_RUN_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,47}")
_VERSION = re.compile(r"3\.(?:10|11|12|13|14)")
_COVERAGE_SHARD_COUNT = 4
_COVERAGE_VERSION = "3.13"
_COVERAGE_TIMEOUT_SECONDS = 17 * 60
_COMPATIBILITY_TIMEOUT_SECONDS = 42 * 60
_PIP_CHECK_TIMEOUT_SECONDS = 5 * 60
_PREPARATION_TIMEOUT_SECONDS = 5 * 60
_PROBE_TIMEOUT_SECONDS = 30
_MAX_PHASE_STDOUT_BYTES = 192 * 1024
_MAX_PHASE_STDERR_BYTES = 64 * 1024
_MAX_PREPARATION_BYTES = 16 * 1024
_MAX_COVERAGE_BYTES = 256 * 1024 * 1024
_ALLOWED_COMPATIBILITY_PAIRS = {
    ("linux", "3.10", "3.11"),
    ("linux", "3.12", "3.14"),
    ("windows", "3.10", "3.14"),
}
_RELEASE_COVERAGE_MODULES = (
    "scripts.build_distributions",
    "scripts.canonicalize_distributions",
    "scripts.prove_autocrlf_checkout",
    "scripts.release_contract",
    "scripts.release_git",
    "scripts.verify_distribution",
)
_RUNTIME_KEYS = {
    "AGENCY_CI_HOME",
    "AGENCY_CI_NODE",
    "AGENCY_CI_PYTHON",
    "AGENCY_CI_ROOT",
    "AGENCY_CI_TEMP",
}
_GITHUB_COMMAND_FILE_KEYS = {
    "GITHUB_ENV",
    "GITHUB_OUTPUT",
    "GITHUB_PATH",
    "GITHUB_STATE",
    "GITHUB_STEP_SUMMARY",
}
_GITHUB_CREDENTIAL_KEYS = {
    "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
    "ACTIONS_ID_TOKEN_REQUEST_URL",
    "ACTIONS_RUNTIME_TOKEN",
    "GH_ENTERPRISE_TOKEN",
    "GH_TOKEN",
    "GITHUB_ENTERPRISE_TOKEN",
    "GITHUB_TOKEN",
}

BoundedRunner = Callable[..., BoundedBinaryProcessResult]


@dataclass(frozen=True, slots=True)
class RuntimeBoundary:
    root: Path
    python: Path
    home: Path
    temporary: Path
    node: Path | None = None


@dataclass(frozen=True, slots=True)
class SessionPlan:
    label: str
    expected_version: str
    system_python: Path
    runtime: RuntimeBoundary
    environment: dict[str, str]
    pytest_command: tuple[str, ...]
    pytest_basetemp: Path
    timeout_seconds: int
    pip_check_command: tuple[str, ...] | None = None
    coverage_path: Path | None = None


@dataclass(frozen=True, slots=True)
class PhaseResult:
    name: str
    result: BoundedBinaryProcessResult


@dataclass(frozen=True, slots=True)
class SessionResult:
    label: str
    phases: tuple[PhaseResult, ...]
    validation_error: str | None = None

    @property
    def succeeded(self) -> bool:
        return bool(
            self.validation_error is None
            and self.phases
            and all(_process_succeeded(phase.result) for phase in self.phases)
        )


def _process_succeeded(result: BoundedBinaryProcessResult) -> bool:
    return bool(
        result.returncode == 0
        and not result.timed_out
        and not result.cancelled
        and not result.stdout_truncated
        and not result.stderr_truncated
        and result.failure_category is None
    )


def _strip_github_capabilities(environment: dict[str, str]) -> None:
    """Remove GitHub command files and credentials from every child boundary."""

    for name in tuple(environment):
        normalized = name.upper()
        if (
            normalized in _GITHUB_COMMAND_FILE_KEYS
            or normalized in _GITHUB_CREDENTIAL_KEYS
            or (
                normalized.startswith(("GH_", "GITHUB_"))
                and normalized.endswith(("_PAT", "_TOKEN"))
            )
            or (
                normalized.startswith("ACTIONS_")
                and (normalized.endswith("_TOKEN") or normalized.endswith("_URL"))
            )
        ):
            environment.pop(name)


def _session_requires_peer_cancellation(result: SessionResult) -> bool:
    """Return whether a non-ordinary outcome invalidates the paired controller."""

    if result.validation_error is not None or not result.phases:
        return True
    return any(
        phase.result.timed_out
        or phase.result.cancelled
        or phase.result.stdout_truncated
        or phase.result.stderr_truncated
        or phase.result.failure_category is not None
        for phase in result.phases
    )


def _safe_run_label(value: str) -> str:
    if not _SAFE_RUN_LABEL.fullmatch(value):
        raise ValueError("run label must be a bounded filesystem-safe identifier")
    return value


def _expected_version(value: str) -> str:
    if not _VERSION.fullmatch(value):
        raise ValueError("expected Python version is unsupported")
    return value


def _platform_name() -> str:
    if os.name == "nt":
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    raise RuntimeError("paired CI sessions support only Linux and Windows")


def _resolve_python(path: Path) -> Path:
    try:
        resolved = path.expanduser().resolve(strict=True)
        metadata = resolved.stat()
    except OSError as exc:
        raise RuntimeError("CI session Python is unavailable") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise RuntimeError("CI session Python must resolve to a regular file")
    return resolved


def _run_checked(
    argv: Sequence[str],
    *,
    runner: BoundedRunner,
    timeout: int,
    cwd: Path,
    environment: dict[str, str] | None = None,
    maximum_bytes: int = _MAX_PREPARATION_BYTES,
) -> BoundedBinaryProcessResult:
    result = runner(
        tuple(argv),
        timeout=timeout,
        cwd=str(cwd),
        env=environment,
        max_stdout_bytes=maximum_bytes,
        max_stderr_bytes=maximum_bytes,
        retain_output_tail=True,
    )
    if (
        not _process_succeeded(result)
        or result.stdout_truncated
        or result.stderr_truncated
        or result.stderr
    ):
        raise RuntimeError("CI session preparation command failed its bounded contract")
    return result


def _probe_python_version(
    python: Path,
    *,
    runner: BoundedRunner,
    environment: dict[str, str],
) -> str:
    result = _run_checked(
        (
            str(python),
            "-I",
            "-c",
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')",
        ),
        runner=runner,
        timeout=_PROBE_TIMEOUT_SECONDS,
        cwd=ROOT,
        environment=environment,
    )
    try:
        version = result.stdout.decode("ascii").strip()
    except UnicodeError as exc:
        raise RuntimeError("CI session Python returned a non-ASCII version") from exc
    return _expected_version(version)


def _runtime_path(value: Any, *, name: str, directory: bool) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise RuntimeError(f"CI runtime {name} path is invalid")
    try:
        path = Path(value).resolve(strict=True)
        metadata = path.stat()
    except OSError as exc:
        raise RuntimeError(f"CI runtime {name} path is unavailable") from exc
    expected = stat.S_ISDIR(metadata.st_mode) if directory else stat.S_ISREG(metadata.st_mode)
    if not expected:
        raise RuntimeError(f"CI runtime {name} has the wrong filesystem type")
    return path


def _prepare_runtime(
    system_python: Path,
    *,
    expected_version: str,
    runtime_label: str,
    runner: BoundedRunner,
) -> RuntimeBoundary:
    python = _resolve_python(system_python)
    preparation_environment = os.environ.copy()
    _strip_github_capabilities(preparation_environment)
    preparation_environment.pop("AGENCY_CONFIG_PATH", None)
    preparation_environment.pop("AGENCY_DB_PATH", None)
    if (
        _probe_python_version(
            python,
            runner=runner,
            environment=preparation_environment,
        )
        != expected_version
    ):
        raise RuntimeError("CI session Python version differs from the workflow contract")
    result = _run_checked(
        (
            str(python),
            "-m",
            "scripts.prepare_ci_runtime",
            "--label",
            runtime_label,
        ),
        runner=runner,
        timeout=_PREPARATION_TIMEOUT_SECONDS,
        cwd=ROOT,
        environment=preparation_environment,
    )
    try:
        payload = json.loads(result.stdout)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("CI runtime preparation returned malformed JSON") from exc
    if (
        not isinstance(payload, dict)
        or not {
            "AGENCY_CI_HOME",
            "AGENCY_CI_PYTHON",
            "AGENCY_CI_ROOT",
            "AGENCY_CI_TEMP",
        }.issubset(payload)
        or set(payload) - _RUNTIME_KEYS
    ):
        raise RuntimeError("CI runtime preparation returned an invalid schema")
    root = _runtime_path(payload["AGENCY_CI_ROOT"], name="root", directory=True)
    node = (
        None
        if "AGENCY_CI_NODE" not in payload
        else _runtime_path(payload["AGENCY_CI_NODE"], name="Node", directory=False)
    )
    boundary = RuntimeBoundary(
        root=root,
        python=_runtime_path(payload["AGENCY_CI_PYTHON"], name="Python", directory=False),
        home=_runtime_path(payload["AGENCY_CI_HOME"], name="HOME", directory=True),
        temporary=_runtime_path(payload["AGENCY_CI_TEMP"], name="TEMP", directory=True),
        node=node,
    )
    for path in (boundary.python, boundary.home, boundary.temporary, boundary.node):
        if path is None:
            continue
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise RuntimeError("CI runtime boundary escaped its private root") from exc
    if (
        _probe_python_version(
            boundary.python,
            runner=runner,
            environment=preparation_environment,
        )
        != expected_version
    ):
        raise RuntimeError("prepared CI runtime has the wrong Python version")
    return boundary


def _create_output_root(path: Path) -> Path:
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    try:
        parent = candidate.parent.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError("CI session output parent is unavailable") from exc
    target = parent / candidate.name
    if target == ROOT or not target.name or target.name in {".", ".."}:
        raise RuntimeError("CI session output root is unsafe")
    try:
        target.mkdir(mode=0o700, exist_ok=False)
    except OSError as exc:
        raise RuntimeError("CI session output root must be new") from exc
    return target.resolve(strict=True)


def _session_environment(
    runtime: RuntimeBoundary,
    *,
    coverage_file: Path,
) -> dict[str, str]:
    environment = os.environ.copy()
    _strip_github_capabilities(environment)
    for name in tuple(environment):
        if name.startswith("AGENCY_CI_"):
            environment.pop(name)
    for name in (
        "AGENCY_CONFIG_PATH",
        "AGENCY_DB_PATH",
        "COVERAGE_PROCESS_START",
        "PYTHONHOME",
        "PYTHONPATH",
        "PYTEST_ADDOPTS",
        "VIRTUAL_ENV",
    ):
        environment.pop(name, None)
    home = str(runtime.home)
    temporary = str(runtime.temporary)
    executable_directories = [str(runtime.python.parent)]
    if runtime.node is not None and runtime.node.parent != runtime.python.parent:
        executable_directories.append(str(runtime.node.parent))
    inherited_path = environment.get("PATH", "")
    if inherited_path:
        executable_directories.append(inherited_path)
    environment.update(
        {
            "AGENCY_CI_HOME": home,
            "AGENCY_CI_PYTHON": str(runtime.python),
            "AGENCY_CI_ROOT": str(runtime.root),
            "AGENCY_CI_TEMP": temporary,
            "COVERAGE_FILE": str(coverage_file),
            "HOME": home,
            "PATH": os.pathsep.join(executable_directories),
            "PYTHONNOUSERSITE": "1",
            "TEMP": temporary,
            "TMP": temporary,
            "TMPDIR": temporary,
            "USERPROFILE": home,
            "VIRTUAL_ENV": str(runtime.python.parent.parent),
            "XDG_CACHE_HOME": str(runtime.home / ".cache"),
            "XDG_CONFIG_HOME": str(runtime.home / ".config"),
            "XDG_DATA_HOME": str(runtime.home / ".local" / "share"),
            "XDG_STATE_HOME": str(runtime.home / ".local" / "state"),
        }
    )
    if runtime.node is not None:
        environment["AGENCY_CI_NODE"] = str(runtime.node)
    return environment


def _coverage_plan(
    *,
    shard: int,
    system_python: Path,
    runtime: RuntimeBoundary,
    output_root: Path,
) -> SessionPlan:
    files = select_test_files(ROOT / "tests", shard_index=shard, shard_count=4)
    relative_files = tuple(str(path.relative_to(ROOT)) for path in files)
    coverage_path = output_root / f".coverage.{shard}"
    basetemp = runtime.temporary / f"pytest-coverage-{shard}"
    command = [str(runtime.python), "-m", "pytest", *relative_files]
    command.extend(
        (
            "-q",
            "-W",
            "error",
            "-p",
            "no:cacheprovider",
            "-m",
            "not performance",
            "--basetemp",
            str(basetemp),
            "--cov=agency_runtime",
        )
    )
    command.extend(f"--cov={module}" for module in _RELEASE_COVERAGE_MODULES)
    command.extend(("--cov-branch", "--cov-report="))
    return SessionPlan(
        label=f"coverage-shard-{shard}",
        expected_version=_COVERAGE_VERSION,
        system_python=system_python,
        runtime=runtime,
        environment=_session_environment(runtime, coverage_file=coverage_path),
        pytest_command=tuple(command),
        pytest_basetemp=basetemp,
        timeout_seconds=_COVERAGE_TIMEOUT_SECONDS,
        coverage_path=coverage_path,
    )


def _compatibility_plan(
    *,
    expected_version: str,
    system_python: Path,
    runtime: RuntimeBoundary,
) -> SessionPlan:
    compact_version = expected_version.replace(".", "")
    basetemp = runtime.temporary / f"pytest-py{compact_version}"
    coverage_path = runtime.temporary / f".coverage.py{compact_version}"
    return SessionPlan(
        label=f"compatibility-py{expected_version}",
        expected_version=expected_version,
        system_python=system_python,
        runtime=runtime,
        environment=_session_environment(runtime, coverage_file=coverage_path),
        pytest_command=(
            str(runtime.python),
            "-m",
            "pytest",
            "tests",
            "-q",
            "-W",
            "error",
            "-p",
            "no:cacheprovider",
            "-m",
            "not performance",
            "--basetemp",
            str(basetemp),
        ),
        pytest_basetemp=basetemp,
        timeout_seconds=_COMPATIBILITY_TIMEOUT_SECONDS,
        pip_check_command=(str(system_python), "-m", "pip", "check"),
    )


def _run_phase(
    plan: SessionPlan,
    phase: str,
    command: Sequence[str],
    *,
    runner: BoundedRunner,
    cancel_event: threading.Event,
    timeout_seconds: int | None = None,
) -> PhaseResult:
    result = runner(
        tuple(command),
        timeout=plan.timeout_seconds if timeout_seconds is None else timeout_seconds,
        cwd=str(ROOT),
        env=dict(plan.environment),
        max_stdout_bytes=_MAX_PHASE_STDOUT_BYTES,
        max_stderr_bytes=_MAX_PHASE_STDERR_BYTES,
        retain_output_tail=True,
        cancel_event=cancel_event,
    )
    return PhaseResult(phase, result)


def _coverage_output_error(path: Path) -> str | None:
    try:
        metadata = path.lstat()
    except OSError:
        return "coverage data was not published"
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or int(getattr(metadata, "st_nlink", 0) or 0) != 1
        or not 0 < int(metadata.st_size) <= _MAX_COVERAGE_BYTES
    ):
        return "coverage data failed its regular bounded file contract"
    return None


def _run_session(
    plan: SessionPlan,
    *,
    runner: BoundedRunner,
    cancel_event: threading.Event,
) -> SessionResult:
    phases = [
        _run_phase(
            plan,
            "pytest",
            plan.pytest_command,
            runner=runner,
            cancel_event=cancel_event,
        )
    ]
    if _process_succeeded(phases[0].result) and plan.pip_check_command is not None:
        phases.append(
            _run_phase(
                plan,
                "pip-check",
                plan.pip_check_command,
                runner=runner,
                cancel_event=cancel_event,
                timeout_seconds=_PIP_CHECK_TIMEOUT_SECONDS,
            )
        )
    validation_error = None
    if _process_succeeded(phases[0].result) and plan.coverage_path is not None:
        validation_error = _coverage_output_error(plan.coverage_path)
    return SessionResult(plan.label, tuple(phases), validation_error)


def execute_pair(
    plans: tuple[SessionPlan, SessionPlan],
    *,
    runner: BoundedRunner = run_bounded_binary_process,
) -> tuple[SessionResult, SessionResult]:
    """Execute two sessions concurrently and quiesce both trees before returning."""

    if plans[0].label == plans[1].label:
        raise ValueError("paired CI session labels must be distinct")
    cancel_event = threading.Event()
    executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="agency-ci-session")
    futures: list[Future[SessionResult]] = []
    results: list[SessionResult] = []
    try:
        futures = [
            executor.submit(
                _run_session,
                plan,
                runner=runner,
                cancel_event=cancel_event,
            )
            for plan in plans
        ]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if _session_requires_peer_cancellation(result):
                cancel_event.set()
    except BaseException:
        cancel_event.set()
        for future in futures:
            future.cancel()
        raise
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
    ordered = tuple(sorted(results, key=lambda item: item.label))
    if len(ordered) != 2:
        raise RuntimeError("paired CI runner did not collect exactly two session results")
    return ordered  # type: ignore[return-value]


def _emit_bytes(payload: bytes) -> None:
    sys.stdout.buffer.write(payload)
    if payload and not payload.endswith(b"\n"):
        sys.stdout.buffer.write(b"\n")


def emit_results(results: Sequence[SessionResult]) -> None:
    for session in sorted(results, key=lambda item: item.label):
        for phase in session.phases:
            result = phase.result
            status = {
                "cancelled": result.cancelled,
                "failure_category": result.failure_category,
                "returncode": result.returncode,
                "stderr_truncated": result.stderr_truncated,
                "stdout_truncated": result.stdout_truncated,
                "timed_out": result.timed_out,
            }
            print(
                f"[agency-ci-session:{session.label}:{phase.name}:status] "
                + json.dumps(status, sort_keys=True),
                flush=True,
            )
            print(f"[agency-ci-session:{session.label}:{phase.name}:stdout]", flush=True)
            _emit_bytes(result.stdout)
            print(f"[agency-ci-session:{session.label}:{phase.name}:stderr]", flush=True)
            _emit_bytes(result.stderr)
        if session.validation_error is not None:
            print(
                f"[agency-ci-session:{session.label}:validation] {session.validation_error}",
                flush=True,
            )


def _coverage_plans(args: argparse.Namespace, output_root: Path) -> tuple[SessionPlan, SessionPlan]:
    if _platform_name() != "linux":
        raise RuntimeError("paired coverage sessions require the governed Ubuntu runner")
    shards = (args.shard_a, args.shard_b)
    if len(set(shards)) != 2 or any(not 0 <= shard < _COVERAGE_SHARD_COUNT for shard in shards):
        raise ValueError("coverage pair must contain two distinct four-way shard indexes")
    system_python = _resolve_python(args.python)
    runtimes = tuple(
        _prepare_runtime(
            system_python,
            expected_version=_COVERAGE_VERSION,
            runtime_label=f"cov-s{shard}-{args.run_label}",
            runner=run_bounded_binary_process,
        )
        for shard in shards
    )
    return tuple(
        _coverage_plan(
            shard=shard,
            system_python=system_python,
            runtime=runtime,
            output_root=output_root,
        )
        for shard, runtime in zip(shards, runtimes, strict=True)
    )  # type: ignore[return-value]


def _compatibility_plans(
    args: argparse.Namespace,
    output_root: Path,
) -> tuple[SessionPlan, SessionPlan]:
    del output_root
    expected_a = _expected_version(args.version_a)
    expected_b = _expected_version(args.version_b)
    platform = _platform_name()
    if args.platform != platform:
        raise RuntimeError("compatibility pair platform differs from the active runner")
    if (platform, expected_a, expected_b) not in _ALLOWED_COMPATIBILITY_PAIRS:
        raise ValueError("compatibility pair is outside the governed version matrix")
    system_pythons = (_resolve_python(args.python_a), _resolve_python(args.python_b))
    versions = (expected_a, expected_b)
    runtimes = tuple(
        _prepare_runtime(
            python,
            expected_version=version,
            runtime_label=f"compat-py{version.replace('.', '')}-{args.run_label}",
            runner=run_bounded_binary_process,
        )
        for python, version in zip(system_pythons, versions, strict=True)
    )
    return tuple(
        _compatibility_plan(
            expected_version=version,
            system_python=python,
            runtime=runtime,
        )
        for python, version, runtime in zip(system_pythons, versions, runtimes, strict=True)
    )  # type: ignore[return-value]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="kind", required=True)

    coverage = subparsers.add_parser("coverage")
    coverage.add_argument("--python", type=Path, required=True)
    coverage.add_argument("--shard-a", type=int, required=True)
    coverage.add_argument("--shard-b", type=int, required=True)
    coverage.add_argument("--run-label", type=_safe_run_label, required=True)
    coverage.add_argument("--output-root", type=Path, required=True)

    compatibility = subparsers.add_parser("compatibility")
    compatibility.add_argument("--platform", choices=("linux", "windows"), required=True)
    compatibility.add_argument("--python-a", type=Path, required=True)
    compatibility.add_argument("--version-a", required=True)
    compatibility.add_argument("--python-b", type=Path, required=True)
    compatibility.add_argument("--version-b", required=True)
    compatibility.add_argument("--run-label", type=_safe_run_label, required=True)
    compatibility.add_argument("--output-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        output_root = _create_output_root(args.output_root)
        plans = (
            _coverage_plans(args, output_root)
            if args.kind == "coverage"
            else _compatibility_plans(args, output_root)
        )
        roots = {plan.runtime.root for plan in plans}
        homes = {plan.environment["HOME"] for plan in plans}
        temporary = {plan.environment["TEMP"] for plan in plans}
        basetemps = {plan.pytest_basetemp for plan in plans}
        coverage_files = {plan.environment["COVERAGE_FILE"] for plan in plans}
        if not all(
            len(values) == 2 for values in (roots, homes, temporary, basetemps, coverage_files)
        ):
            raise RuntimeError("paired CI sessions do not have distinct state boundaries")
        results = execute_pair(plans)
        emit_results(results)
        return 0 if all(result.succeeded for result in results) else 1
    except KeyboardInterrupt:
        print("paired CI sessions cancelled", file=sys.stderr)
        return 130
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"paired CI sessions failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
