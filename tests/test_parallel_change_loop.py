"""Contracts for the isolated local parallel pytest change loop."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.private_paths import ensure_private_directory, remove_private_directory
from scripts import parallel_change_loop_runtime as runtime_subject
from scripts import pytest_file_timing as timing_subject
from scripts import run_parallel_change_loop as subject
from scripts.parallel_change_loop_storage import capture_private_directory_identity
from tests.runtime_support import trusted_base_test_interpreter, wait_for_process_exit

_SELF_HOST_CHILD_TIMEOUT_SECONDS = 60


@pytest.fixture()
def self_host_runtime_home(tmp_path: Path):
    configured_root = os.environ.get("AGENCY_CI_ROOT")
    if os.name != "nt" or not configured_root:
        yield tmp_path
        return
    digest = hashlib.sha256(str(tmp_path).encode()).hexdigest()[:16]
    home = ensure_private_directory(Path(configured_root) / "h" / digest)
    identity = capture_private_directory_identity(home)
    try:
        yield home
    finally:
        remove_private_directory(identity)


def _repository(tmp_path: Path, *, file_count: int = 8, body: str | None = None) -> Path:
    repository = tmp_path / "repo"
    tests = repository / "tests"
    tests.mkdir(parents=True)
    for index in range(file_count):
        (tests / f"test_{index}.py").write_text(
            body or "def test_value():\n    assert True\n" + ("# weight\n" * index),
            encoding="utf-8",
        )
    return repository


def _runtime_preparer(base: Path, labels: list[str] | None = None):
    def prepare(label: str, **kwargs: object) -> dict[str, str]:
        if labels is not None:
            labels.append(label)
        assert kwargs["system_site_packages"] is False
        assert isinstance(kwargs["runtime_contract"], str)
        root = base / label
        home = root / "stable-home"
        temporary = root / "stable-tmp"
        binary = root / "venv" / ("Scripts" if os.name == "nt" else "bin")
        binary.mkdir(parents=True, exist_ok=True)
        home.mkdir(exist_ok=True)
        temporary.mkdir(exist_ok=True)
        python = binary / ("python.exe" if os.name == "nt" else "python")
        python.touch(exist_ok=True)
        return {
            "AGENCY_CI_ROOT": str(root),
            "AGENCY_CI_PYTHON": str(python),
            "AGENCY_CI_HOME": str(home),
            "AGENCY_CI_TEMP": str(temporary),
        }

    return prepare


def _ambient() -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "PATHEXT": os.environ.get("PATHEXT", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "WINDIR": os.environ.get("WINDIR", ""),
        "OPENAI_API_KEY": "must-not-propagate",
        "aws_secret_access_key": "must-not-propagate",
        "GitHub_Token": "must-not-propagate",
        "agency_ci_root": "hostile",
        "PyThOnPaTh": "hostile",
        "pytest_addopts": "--maxfail=1",
        "AGENCY_CONFIG_PATH": "hostile",
    }


def _filesystem_snapshot(root: Path) -> tuple[tuple[str, int, int, int, int], ...]:
    try:
        os.lstat(root)
    except FileNotFoundError:
        return ()
    paths = [root, *root.rglob("*")]
    snapshot = []
    for path in sorted(paths, key=lambda item: item.as_posix()):
        metadata = os.lstat(path)
        snapshot.append(
            (
                path.relative_to(root).as_posix(),
                stat.S_IFMT(metadata.st_mode),
                int(metadata.st_size),
                int(metadata.st_mtime_ns),
                int(getattr(metadata, "st_ino", 0) or 0),
            )
        )
    return tuple(snapshot)


def _failed_shard_details(results: tuple[subject.ShardResult, ...]) -> str:
    details: list[str] = []
    for result in results:
        if result.returncode == 0:
            continue
        try:
            payload = result.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            payload = f"log unavailable: {type(exc).__name__}"
        details.append(
            f"shard={result.index} category={result.failure_category} "
            f"timed_out={result.timed_out} cancelled={result.cancelled}\n{payload[-4096:]}"
        )
    return "\n".join(details)


def _plan(
    tmp_path: Path,
    runtime_home: Path,
    *,
    shard_count: int = 4,
    timeout: float = 17,
    collect_file_timings: bool = False,
) -> subject.ParallelTestPlan:
    repository = _repository(tmp_path, file_count=max(8, shard_count))
    return subject.build_parallel_test_plan(
        repo_root=repository,
        shard_count=shard_count,
        runtime_home=runtime_home,
        runtime_preparer=_runtime_preparer(runtime_home / "runtimes"),
        ambient_environment=_ambient(),
        timeout_seconds=timeout,
        collect_file_timings=collect_file_timings,
    )


def _timing_report(
    shard: subject.TestShardPlan,
    *,
    run_id: str,
    exit_status: int = 0,
) -> bytes:
    files = [
        {
            "collected_items": 1,
            "duration_ns": {"call": 2, "setup": 1, "teardown": 3},
            "path": path.as_posix(),
            "report_counts": {"call": 1, "setup": 1, "teardown": 1},
            "total_ns": 6,
        }
        for path in shard.test_files
    ]
    return (
        json.dumps(
            {
                "collected_item_count": len(files),
                "errors": [],
                "exit_status": exit_status,
                "files": files,
                "phase_report_count": len(files) * 3,
                "run_id": run_id,
                "schema": subject.SHARD_TIMING_SCHEMA,
                "shard": shard.index,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        + b"\n"
    )


def _assert_phase_timing_contract(
    manifest: dict[str, Any],
    plan: subject.ParallelTestPlan,
    results: tuple[subject.ShardResult, ...],
) -> None:
    assert manifest["schema"] == "agency.local-parallel-tests.latest.v3"
    phase_timings = manifest["phase_timings"]
    assert phase_timings == {
        "clock": "monotonic",
        "durations_ns": phase_timings["durations_ns"],
        "process_scope": "executor-wall-including-launch-and-timing-read",
        "publish_relevant_scope": "input-revalidation-and-timing-artifact",
        "timing_read_aggregation": "sum-across-shards",
    }
    durations = phase_timings["durations_ns"]
    assert set(durations) == {
        "launch",
        "plan",
        "process",
        "publish_relevant",
        "scratch_cleanup",
        "timing_read",
    }
    assert all(
        type(value) is int and 0 <= value <= subject.MAX_PHASE_DURATION_NS
        for value in durations.values()
    )
    assert durations["plan"] == plan.plan_duration_ns
    assert durations["launch"] <= durations["process"]
    assert durations["timing_read"] == sum(result.timing_read_duration_ns for result in results)
    by_index = {result.index: result for result in results}
    for item in manifest["shards"]:
        result = by_index[item["index"]]
        assert item["process_duration_ns"] == result.process_duration_ns
        assert item["timing_read_duration_ns"] == result.timing_read_duration_ns
        assert type(result.process_duration_ns) is int
        assert 0 <= result.process_duration_ns <= durations["process"]
        assert type(result.timing_read_duration_ns) is int
        assert 0 <= result.timing_read_duration_ns <= subject.MAX_PHASE_DURATION_NS


def test_plan_uses_one_runtime_exact_shards_and_least_privilege_environment(
    tmp_path: Path,
    self_host_runtime_home: Path,
) -> None:
    labels: list[str] = []
    repository = _repository(tmp_path)
    plan = subject.build_parallel_test_plan(
        repo_root=repository,
        runtime_home=self_host_runtime_home,
        runtime_preparer=_runtime_preparer(self_host_runtime_home / "runtimes", labels),
        ambient_environment=_ambient(),
    )

    assert len(labels) == 1
    assert len(plan.shards) == subject.DEFAULT_SHARD_COUNT == 4
    assert subject.DEFAULT_TIMEOUT_SECONDS == 45 * 60
    assert len({shard.stable_runtime_root for shard in plan.shards}) == 1
    assert len({shard.run_root for shard in plan.shards}) == 4
    assert {path for shard in plan.shards for path in shard.test_files} == set(plan.serial_files)
    assert plan.scratch_root.name == ".agency-local-change-loop-scratch-v1"
    assert all(shard.log_path.parent == plan.log_root for shard in plan.shards)
    for shard in plan.shards:
        assert shard.environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
        assert shard.environment["PYTHONNOUSERSITE"] == "1"
        assert shard.environment["HOME"] == str(shard.private_home)
        assert shard.environment["TMP"] == str(shard.private_temp)
        assert not {
            "OPENAI_API_KEY",
            "AWS_SECRET_ACCESS_KEY",
            "GITHUB_TOKEN",
            "AGENCY_CONFIG_PATH",
        } & {name.upper() for name in shard.environment}
        assert not any(
            name.casefold() == "pythonpath" for name in shard.environment if name != "PYTHONPATH"
        )


def test_windows_runtime_geometry_rejects_critical_paths_beyond_safe_budget() -> None:
    short_root = Path("C:/agency-ci/runtime")
    subject._validate_windows_runtime_geometry(
        short_root,
        short_root / "venv" / "Scripts" / "python.exe",
        shard_count=4,
        is_windows=True,
    )
    long_root = Path("C:/") / ("nested-" * 35)

    with pytest.raises(ValueError, match="use a shorter runtime home"):
        subject._validate_windows_runtime_geometry(
            long_root,
            long_root / "venv" / "Scripts" / "python.exe",
            shard_count=1,
            is_windows=True,
        )


def test_execution_rejects_same_size_source_change_after_plan(
    tmp_path: Path,
    self_host_runtime_home: Path,
) -> None:
    plan = _plan(tmp_path, self_host_runtime_home, shard_count=1)
    target = plan.repo_root / plan.serial_files[0]
    original = target.read_text("utf-8")
    target.write_text("#" + original[1:], encoding="utf-8")

    with pytest.raises(RuntimeError, match="source or timing harness changed"):
        subject.run_parallel_test_plan(plan)

    assert plan.use.state == "ready"


def test_dry_run_is_deterministic_resource_free_and_concurrent_safe(
    tmp_path: Path,
    self_host_runtime_home: Path,
) -> None:
    repository = _repository(tmp_path)

    def preparer(*_args: object, **_kwargs: object) -> dict[str, str]:
        raise AssertionError("dry-run must not prepare a runtime")

    def build(_index: int) -> dict[str, Any]:
        plan = subject.build_parallel_test_plan(
            repo_root=repository,
            runtime_home=self_host_runtime_home,
            runtime_preparer=preparer,
            ambient_environment=_ambient(),
            dry_run=True,
        )
        assert plan.use.state == "ready"
        return subject.plan_preview(plan)

    with ThreadPoolExecutor(max_workers=4) as executor:
        previews = tuple(executor.map(build, range(4)))

    assert previews.count(previews[0]) == 4
    assert previews[0]["schema_version"] == "agency.local-parallel-tests.v5"
    assert previews[0]["partition"]["algorithm"] == "source-bytes-lpt-v1"
    assert previews[0]["partition"]["status"] == "disabled"
    assert previews[0]["partition"]["reason"] == "explicit-source-bytes"
    assert len(previews[0]["partition"]["shards"]) == 4
    assert not Path(previews[0]["scratch_root"]).exists()
    assert not (tmp_path / "runtimes").exists()


def test_timing_opt_in_is_explicit_deterministic_and_resource_free(
    tmp_path: Path,
    self_host_runtime_home: Path,
) -> None:
    repository = _repository(tmp_path)

    def preparer(*_args: object, **_kwargs: object) -> dict[str, str]:
        raise AssertionError("timed dry-run must not prepare a runtime")

    plain = subject.build_parallel_test_plan(
        repo_root=repository,
        runtime_home=self_host_runtime_home,
        runtime_preparer=preparer,
        ambient_environment=_ambient(),
        dry_run=True,
    )
    timed = subject.build_parallel_test_plan(
        repo_root=repository,
        runtime_home=self_host_runtime_home,
        runtime_preparer=preparer,
        ambient_environment=_ambient(),
        dry_run=True,
        collect_file_timings=True,
    )

    plain_preview = subject.plan_preview(plain)
    timed_preview = subject.plan_preview(timed)
    assert "file_timings" not in plain_preview
    assert "file_timings" in timed_preview
    assert timed_preview == subject.plan_preview(
        subject.build_parallel_test_plan(
            repo_root=repository,
            runtime_home=self_host_runtime_home,
            runtime_preparer=preparer,
            ambient_environment=_ambient(),
            dry_run=True,
            collect_file_timings=True,
        )
    )
    for plain_shard, timed_shard in zip(plain.shards, timed.shards, strict=True):
        assert "scripts.pytest_file_timing" not in plain_shard.command
        assert subject.REPORT_OPTION not in plain_shard.command
        assert plain_shard.timing_path is None
        assert "scripts.pytest_file_timing" in timed_shard.command
        assert subject.REPORT_OPTION in timed_shard.command
        assert timed_shard.timing_path is not None
        assert str(timed_shard.timing_path) in timed_shard.command
        assert not timed_shard.timing_path.exists()
        assert subject.RUN_ID_ENVIRONMENT_KEY not in timed_shard.environment
    assert not timed.scratch_root.exists()


def test_valid_timing_reports_publish_one_run_bound_consolidated_artifact(
    tmp_path: Path,
    self_host_runtime_home: Path,
) -> None:
    plan = _plan(
        tmp_path,
        self_host_runtime_home,
        shard_count=2,
        collect_file_timings=True,
    )

    def run(command: tuple[str, ...], **kwargs: Any) -> subject.BoundedBinaryProcessResult:
        shard = next(item for item in plan.shards if item.command == tuple(command))
        assert shard.timing_path is not None
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        run_id = environment[subject.RUN_ID_ENVIRONMENT_KEY]
        assert set(environment).isdisjoint({"OPENAI_API_KEY", "GITHUB_TOKEN"})
        shard.timing_path.write_bytes(_timing_report(shard, run_id=run_id))
        return subject.BoundedBinaryProcessResult(0, b"", b"")

    exit_code, results = subject.run_parallel_test_plan(plan, bounded_runner=run)

    assert exit_code == 0
    assert all(result.failure_category is None for result in results)
    assert all(result.timing_report is not None for result in results)
    assert plan.timing_artifact_path is not None
    artifact = json.loads(plan.timing_artifact_path.read_text("utf-8"))
    assert artifact["schema"] == subject.RUN_TIMING_SCHEMA
    assert artifact["run_id"] == plan.use.run_id
    assert artifact["test_file_count"] == len(plan.serial_files)
    assert artifact["measurement_context"] == plan.measurement_context
    assert artifact["partition"] == subject.plan_preview(plan)["partition"]
    assert {item["path"] for item in artifact["files"]} == {
        path.as_posix() for path in plan.serial_files
    }
    assert sum(item["total_ns"] for item in artifact["files"]) == len(plan.serial_files) * 6
    assert "OPENAI_API_KEY" not in plan.timing_artifact_path.read_text("utf-8")
    manifest = json.loads((plan.log_root / "latest-run.json").read_text("utf-8"))
    _assert_phase_timing_contract(manifest, plan, results)
    assert manifest["file_timings"] == {
        "artifact": plan.timing_artifact_path.name,
        "complete": True,
        "schema": subject.RUN_TIMING_SCHEMA,
    }


def test_timing_evidence_rejects_source_drift_during_execution(
    tmp_path: Path,
    self_host_runtime_home: Path,
) -> None:
    plan = _plan(
        tmp_path,
        self_host_runtime_home,
        shard_count=1,
        collect_file_timings=True,
    )

    def run(command: tuple[str, ...], **kwargs: Any) -> subject.BoundedBinaryProcessResult:
        shard = next(item for item in plan.shards if item.command == tuple(command))
        assert shard.timing_path is not None
        shard.timing_path.write_bytes(
            _timing_report(shard, run_id=kwargs["env"][subject.RUN_ID_ENVIRONMENT_KEY])
        )
        target = plan.repo_root / plan.serial_files[0]
        target.write_text(target.read_text("utf-8") + "# drift\n", encoding="utf-8")
        return subject.BoundedBinaryProcessResult(0, b"", b"")

    with pytest.raises(RuntimeError, match="source or timing harness changed"):
        subject.run_parallel_test_plan(plan, bounded_runner=run)

    assert plan.timing_artifact_path is not None
    assert not plan.timing_artifact_path.exists()


def test_missing_or_non_equivalent_timing_report_cannot_turn_a_pass_green(
    tmp_path: Path,
    self_host_runtime_home: Path,
) -> None:
    for mode in ("missing", "wrong-path"):
        plan = _plan(
            tmp_path / mode,
            self_host_runtime_home,
            shard_count=1,
            collect_file_timings=True,
        )

        def run(
            command: tuple[str, ...],
            *,
            behavior: str = mode,
            active_plan: subject.ParallelTestPlan = plan,
            **kwargs: Any,
        ) -> subject.BoundedBinaryProcessResult:
            del command
            if behavior == "wrong-path":
                shard = active_plan.shards[0]
                assert shard.timing_path is not None
                payload = json.loads(
                    _timing_report(
                        shard,
                        run_id=kwargs["env"][subject.RUN_ID_ENVIRONMENT_KEY],
                    )
                )
                payload["files"][0]["path"] = "tests/not-planned.py"
                shard.timing_path.write_text(
                    json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n",
                    encoding="utf-8",
                )
            return subject.BoundedBinaryProcessResult(0, b"", b"")

        exit_code, results = subject.run_parallel_test_plan(plan, bounded_runner=run)

        assert exit_code == 1
        assert results[0].returncode == 0
        assert results[0].failure_category == "timing"
        assert results[0].timing_report is None
        assert plan.timing_artifact_path is not None
        assert not plan.timing_artifact_path.exists()
        status = json.loads(results[0].log_path.read_text("utf-8").splitlines()[0])
        assert status["failure_category"] == "timing"
        manifest = json.loads((plan.log_root / "latest-run.json").read_text("utf-8"))
        assert manifest["file_timings"]["complete"] is False


@pytest.mark.parametrize(
    ("returncode", "timed_out", "cancelled", "failure_category"),
    [
        (1, False, False, None),
        (0, True, False, "timeout"),
        (0, False, True, "cancelled"),
        (0, False, False, "containment"),
    ],
)
def test_red_shard_timing_is_never_published_as_complete(
    tmp_path: Path,
    self_host_runtime_home: Path,
    returncode: int,
    timed_out: bool,
    cancelled: bool,
    failure_category: str | None,
) -> None:
    plan = _plan(
        tmp_path,
        self_host_runtime_home,
        shard_count=1,
        collect_file_timings=True,
    )

    def run(command: tuple[str, ...], **kwargs: Any) -> subject.BoundedBinaryProcessResult:
        del command
        shard = plan.shards[0]
        assert shard.timing_path is not None
        shard.timing_path.write_bytes(
            _timing_report(
                shard,
                run_id=kwargs["env"][subject.RUN_ID_ENVIRONMENT_KEY],
                exit_status=returncode,
            )
        )
        return subject.BoundedBinaryProcessResult(
            returncode,
            b"",
            b"",
            timed_out=timed_out,
            cancelled=cancelled,
            failure_category=failure_category,
        )

    exit_code, results = subject.run_parallel_test_plan(plan, bounded_runner=run)

    assert exit_code == 1
    assert results[0].timing_report is not None
    assert plan.timing_artifact_path is not None
    assert not plan.timing_artifact_path.exists()
    manifest = json.loads((plan.log_root / "latest-run.json").read_text("utf-8"))
    assert manifest["file_timings"]["complete"] is False


def test_execution_uses_balanced_capture_and_replaces_one_coherent_log_set(
    tmp_path: Path,
    self_host_runtime_home: Path,
) -> None:
    plan = _plan(tmp_path, self_host_runtime_home)
    stale = plan.log_root / "pytest-shard-99.latest.log"
    stale.write_bytes(b"stale")
    observations: list[dict[str, Any]] = []
    barrier = threading.Barrier(4)

    def run(command: tuple[str, ...], **kwargs: Any) -> subject.BoundedBinaryProcessResult:
        observations.append(kwargs)
        barrier.wait(timeout=5)
        index = next(shard.index for shard in plan.shards if shard.command == tuple(command))
        return subject.BoundedBinaryProcessResult(
            returncode=1 if index == 2 else 0,
            stdout=b"stdout-head" + b"x" * 10_000 + b"stdout-tail",
            stderr=b"stderr-head" + b"y" * 10_000 + b"stderr-tail",
        )

    exit_code, results = subject.run_parallel_test_plan(
        plan,
        maximum_log_bytes=subject.MIN_LOG_BYTES,
        bounded_runner=run,
    )

    assert exit_code == 1
    assert [result.returncode for result in results] == [0, 0, 1, 0]
    assert not plan.scratch_root.exists() and not stale.exists()
    assert all(item["retain_output_tail"] is True for item in observations)
    assert all(item["max_stdout_bytes"] < subject.MIN_LOG_BYTES for item in observations)
    assert all(item["max_stderr_bytes"] >= 1000 for item in observations)
    statuses = []
    for result in results:
        payload = result.log_path.read_bytes()
        assert len(payload) <= subject.MIN_LOG_BYTES
        assert b"stderr-tail" in payload and subject._TRUNCATION_MARKER in payload
        statuses.append(json.loads(payload.splitlines()[0]))
    assert {status["run_id"] for status in statuses} == {plan.use.run_id}
    manifest = json.loads((plan.log_root / "latest-run.json").read_text("utf-8"))
    assert manifest["run_id"] == plan.use.run_id
    assert manifest["exit_code"] == 1
    assert manifest["elapsed_seconds"] >= 0
    _assert_phase_timing_contract(manifest, plan, results)
    assert manifest["phase_timings"]["durations_ns"]["timing_read"] == 0


@pytest.mark.parametrize("value", [True, -1, subject.MAX_PHASE_DURATION_NS + 1])
def test_phase_durations_reject_values_outside_the_manifest_contract(value: object) -> None:
    with pytest.raises(RuntimeError, match="phase duration is outside"):
        subject._bounded_phase_duration_ns(value, phase="contract-test")
    assert (
        subject._bounded_phase_duration_ns(
            subject.MAX_PHASE_DURATION_NS,
            phase="contract-test",
        )
        == subject.MAX_PHASE_DURATION_NS
    )


@pytest.mark.parametrize(
    "result",
    [
        subject.ShardResult(0, 1, Path("log")),
        subject.ShardResult(0, 0, Path("log"), timed_out=True),
        subject.ShardResult(0, 0, Path("log"), cancelled=True),
        subject.ShardResult(0, 0, Path("log"), failure_category="containment"),
    ],
)
def test_contradictory_receipts_never_aggregate_as_success(result: subject.ShardResult) -> None:
    assert subject._shard_succeeded(result) is False


def test_plan_is_single_use_and_repo_lock_rejects_concurrent_labels(
    tmp_path: Path,
    self_host_runtime_home: Path,
) -> None:
    repository = _repository(tmp_path)
    preparer = _runtime_preparer(self_host_runtime_home / "runtimes")
    first = subject.build_parallel_test_plan(
        repo_root=repository,
        shard_count=1,
        label="first-label",
        runtime_home=self_host_runtime_home,
        runtime_preparer=preparer,
        ambient_environment=_ambient(),
    )
    second = subject.build_parallel_test_plan(
        repo_root=repository,
        shard_count=1,
        label="second-label",
        runtime_home=self_host_runtime_home,
        runtime_preparer=preparer,
        ambient_environment=_ambient(),
    )
    entered = threading.Event()
    release = threading.Event()

    def blocking(*_args: Any, **_kwargs: Any) -> subject.BoundedBinaryProcessResult:
        entered.set()
        assert release.wait(timeout=10)
        return subject.BoundedBinaryProcessResult(0, b"", b"")

    future: list[tuple[int, tuple[subject.ShardResult, ...]]] = []
    worker = threading.Thread(
        target=lambda: future.append(subject.run_parallel_test_plan(first, bounded_runner=blocking))
    )
    worker.start()
    assert entered.wait(timeout=10)
    with pytest.raises(RuntimeError, match="another parallel test run"):
        subject.run_parallel_test_plan(
            second,
            bounded_runner=lambda *_a, **_k: subject.BoundedBinaryProcessResult(0, b"", b""),
        )
    release.set()
    worker.join(timeout=10)
    assert future[0][0] == 0
    with pytest.raises(RuntimeError, match="already been started"):
        subject.run_parallel_test_plan(first, bounded_runner=blocking)


def test_keyboard_interrupt_cancels_and_cleanup_failure_is_visible(
    tmp_path: Path,
    self_host_runtime_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan(tmp_path, self_host_runtime_home, shard_count=1)
    original_remove = subject.remove_private_directory
    monkeypatch.setattr(
        subject,
        "remove_private_directory",
        lambda _identity: (_ for _ in ()).throw(OSError("sensitive detail")),
    )
    with pytest.raises(subject.ParallelCleanupError) as raised:
        subject.run_parallel_test_plan(
            plan,
            bounded_runner=lambda *_a, **_k: (_ for _ in ()).throw(KeyboardInterrupt()),
        )
    assert raised.value.failure_category == "cleanup"
    assert raised.value.cleanup_component == "cancellation"
    assert "sensitive detail" not in str(raised.value)
    monkeypatch.setattr(subject, "remove_private_directory", original_remove)


def test_invalid_limits_and_dry_execution_fail_before_start(
    tmp_path: Path,
    self_host_runtime_home: Path,
) -> None:
    plan = _plan(tmp_path, self_host_runtime_home, shard_count=1)
    for value in (True, 0, subject.MAX_LOG_BYTES + 1):
        with pytest.raises(ValueError, match="maximum_log_bytes"):
            subject.run_parallel_test_plan(plan, maximum_log_bytes=value)  # type: ignore[arg-type]
    assert plan.use.state == "ready"
    dry = subject.build_parallel_test_plan(
        repo_root=plan.repo_root,
        shard_count=1,
        runtime_home=self_host_runtime_home,
        runtime_preparer=_runtime_preparer(self_host_runtime_home / "dry-runtime"),
        ambient_environment=_ambient(),
        dry_run=True,
    )
    with pytest.raises(ValueError, match="dry-run"):
        subject.run_parallel_test_plan(dry)


def test_real_private_venv_executes_pytest_without_secret_or_global_plugins(
    tmp_path: Path,
    self_host_runtime_home: Path,
) -> None:
    repository = _repository(
        tmp_path,
        file_count=1,
        body=(
            "import os, pytest\n"
            "def test_private_runtime():\n"
            "    assert pytest.__version__\n"
            "    assert os.environ.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD') == '1'\n"
            "    assert 'OPENAI_API_KEY' not in os.environ\n"
        ),
    )
    (tmp_path / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\naddopts = []\n",
        encoding="utf-8",
    )
    ambient = dict(os.environ)
    ambient["OPENAI_API_KEY"] = "do-not-leak"
    plugin_package = repository / "scripts"
    plugin_package.mkdir()
    (plugin_package / "__init__.py").touch()
    shutil.copyfile(
        Path(subject.__file__).with_name("pytest_file_timing.py"),
        plugin_package / "pytest_file_timing.py",
    )
    plan = subject.build_parallel_test_plan(
        repo_root=repository,
        shard_count=1,
        runtime_home=self_host_runtime_home,
        ambient_environment=ambient,
        timeout_seconds=_SELF_HOST_CHILD_TIMEOUT_SECONDS,
        collect_file_timings=True,
    )

    exit_code, results = subject.run_parallel_test_plan(plan)

    assert exit_code == 0 and results[0].returncode == 0, _failed_shard_details(results)
    assert not plan.scratch_root.exists()
    configuration = plan.stable_runtime_root / "venv" / "pyvenv.cfg"
    assert "include-system-site-packages = false" in configuration.read_text("utf-8").lower()
    assert plan.timing_artifact_path is not None
    artifact = json.loads(plan.timing_artifact_path.read_text("utf-8"))
    assert artifact["run_id"] == plan.use.run_id
    assert artifact["test_file_count"] == 1
    assert artifact["files"][0]["path"] == "tests/test_0.py"
    assert artifact["files"][0]["report_counts"] == {
        "call": 1,
        "setup": 1,
        "teardown": 1,
    }


def test_timing_plugin_rejects_repeated_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()

    class Config:
        @staticmethod
        def getoption(option: str) -> object:
            return "report.json" if option == timing_subject.REPORT_OPTION else 0

    # Restore the module global before pytest emits this test's call-phase
    # report. The timing plugin itself can be active while this regression runs.
    with monkeypatch.context() as isolated:
        isolated.setattr(timing_subject, "_state", sentinel)
        with pytest.raises(RuntimeError, match="already configured"):
            timing_subject.pytest_configure(Config())


def test_fixed_runtime_self_heals_when_node_identity_changes(
    tmp_path: Path,
    self_host_runtime_home: Path,
) -> None:
    repository = _repository(tmp_path, file_count=1)
    binary = tmp_path / "host-bin"
    binary.mkdir()
    node = binary / ("node.exe" if os.name == "nt" else "node")
    node.write_bytes(b"node-v1")
    node.chmod(0o700)
    ambient = {**os.environ, "PATH": f"{binary}{os.pathsep}{os.environ.get('PATH', '')}"}
    first = subject.build_parallel_test_plan(
        repo_root=repository,
        shard_count=1,
        runtime_home=self_host_runtime_home,
        ambient_environment=ambient,
    )
    sentinel = first.stable_runtime_root / "old-runtime-sentinel"
    sentinel.write_text("old", encoding="utf-8")
    node.write_bytes(b"node-v2-changed")
    node.chmod(0o700)

    second = subject.build_parallel_test_plan(
        repo_root=repository,
        shard_count=1,
        runtime_home=self_host_runtime_home,
        ambient_environment=ambient,
    )

    assert second.stable_runtime_root == first.stable_runtime_root
    assert second.runtime_key != first.runtime_key
    assert not sentinel.exists()
    assert Path(second.shards[0].environment["AGENCY_CI_NODE"]).read_bytes() == node.read_bytes()


def test_killed_runner_scratch_is_recovered_by_next_real_execution(
    tmp_path: Path,
    self_host_runtime_home: Path,
) -> None:
    repository = _repository(
        tmp_path,
        file_count=1,
        body=(
            "import os, time\n"
            "from pathlib import Path\n"
            "def test_wait():\n"
            "    Path('runner-child.pid').write_text(str(os.getpid()), encoding='ascii')\n"
            "    time.sleep(30)\n"
        ),
    )
    child_pid_path = repository / "runner-child.pid"
    ambient = dict(os.environ)
    dependency_paths = runtime_subject._dependency_paths(
        Path(__file__).resolve().parents[1],
        ambient,
    )
    ambient["PYTHONPATH"] = os.pathsep.join(str(path) for path in dependency_paths)
    preview = subject.build_parallel_test_plan(
        repo_root=repository,
        shard_count=1,
        runtime_home=self_host_runtime_home,
        ambient_environment=ambient,
        dry_run=True,
    )
    script = Path(subject.__file__).resolve()
    bootstrap = (
        "import runpy,sys,pytest;"
        "sys.argv=[sys.argv[1],*sys.argv[2:]];"
        "runpy.run_path(sys.argv[0],run_name='__main__')"
    )
    process = subprocess.Popen(
        [
            str(trusted_base_test_interpreter()),
            "-c",
            bootstrap,
            str(script),
            "--repo-root",
            str(repository),
            "--runtime-home",
            str(self_host_runtime_home),
            "--shards",
            "1",
            "--timeout-seconds",
            str(_SELF_HOST_CHILD_TIMEOUT_SECONDS),
        ],
        cwd=script.parents[1],
        env=ambient,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    child_pid: int | None = None
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and not child_pid_path.exists():
            if process.poll() is not None:
                break
            time.sleep(0.05)
        assert preview.scratch_root.exists()
        assert child_pid_path.exists()
        child_pid = int(child_pid_path.read_text(encoding="ascii"))
        process.kill()
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)
    assert child_pid is not None
    assert wait_for_process_exit(process.pid, timeout=10)
    assert wait_for_process_exit(child_pid, timeout=10)
    (repository / "tests" / "test_0.py").write_text(
        "def test_recovered():\n    assert True\n", encoding="utf-8"
    )
    recovered = subject.build_parallel_test_plan(
        repo_root=repository,
        shard_count=1,
        runtime_home=self_host_runtime_home,
        ambient_environment=ambient,
        timeout_seconds=_SELF_HOST_CHILD_TIMEOUT_SECONDS,
    )
    exit_code, results = subject.run_parallel_test_plan(recovered)
    assert exit_code == 0, _failed_shard_details(results)
    assert not recovered.scratch_root.exists()


def test_help_supports_direct_and_module_invocation() -> None:
    repository = Path(__file__).resolve().parents[1]
    script = repository / "scripts" / "run_parallel_change_loop.py"
    direct = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    module = subprocess.run(
        [sys.executable, "-m", "scripts.run_parallel_change_loop", "--help"],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert direct.returncode == module.returncode == 0
    assert "--output-dir" not in direct.stdout
    assert "--collect-file-timings" in direct.stdout
    assert "--partition" in direct.stdout
    assert "--require-exact-shard-weights" in direct.stdout
    assert subject._parser().parse_args([]).partition == "source-bytes"


def test_timing_profile_selection_requires_explicit_auto(
    tmp_path: Path,
    self_host_runtime_home: Path,
) -> None:
    repository = _repository(tmp_path)

    default = subject.build_parallel_test_plan(
        repo_root=repository,
        runtime_home=self_host_runtime_home,
        ambient_environment=_ambient(),
        dry_run=True,
    )
    explicit = subject.build_parallel_test_plan(
        repo_root=repository,
        runtime_home=self_host_runtime_home,
        ambient_environment=_ambient(),
        dry_run=True,
        partition_strategy="auto",
    )

    assert (default.partition.status, default.partition.reason) == (
        "disabled",
        "explicit-source-bytes",
    )
    assert (explicit.partition.status, explicit.partition.reason) == (
        "missing",
        "profile-missing",
    )
    with pytest.raises(ValueError, match="automatic"):
        subject.build_parallel_test_plan(
            repo_root=repository,
            runtime_home=self_host_runtime_home,
            ambient_environment=_ambient(),
            dry_run=True,
            require_exact_shard_weights=True,
        )


def test_dependency_discovery_recovers_loaded_pytest_from_private_venv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path, file_count=1)
    private_site = tmp_path / "private-site"
    private_site.mkdir()
    dependency_root = tmp_path / "dependency-root"
    pytest_package = dependency_root / "pytest"
    pytest_package.mkdir(parents=True)
    pytest_init = pytest_package / "__init__.py"
    pytest_init.write_text("", encoding="utf-8")

    monkeypatch.setattr(runtime_subject.sysconfig, "get_path", lambda _name: str(private_site))
    monkeypatch.setitem(
        runtime_subject.sys.modules,
        "pytest",
        type("LoadedPytest", (), {"__file__": str(pytest_init)})(),
    )

    assert runtime_subject._dependency_paths(repository) == (
        repository,
        private_site,
        dependency_root,
    )


def test_dependency_discovery_recovers_attested_parent_runtime_for_direct_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path, file_count=1)
    private_site = tmp_path / "private-site"
    private_site.mkdir()
    runtime_root = tmp_path / "runtime"
    python = (
        runtime_root
        / "venv"
        / ("Scripts" if os.name == "nt" else "bin")
        / ("python.exe" if os.name == "nt" else "python")
    )
    python.parent.mkdir(parents=True)
    python.write_bytes(b"python")
    dependency_root = tmp_path / "dependency-root"
    pytest_package = dependency_root / "pytest"
    pytest_package.mkdir(parents=True)
    (pytest_package / "__init__.py").write_text("", encoding="utf-8")
    receipt = json.dumps(
        {
            "dependency_paths": [str(dependency_root)],
            "runtime_key": "a" * 64,
            "schema": runtime_subject.RUNTIME_RECEIPT_SCHEMA,
        }
    ).encode()

    monkeypatch.setattr(runtime_subject.sysconfig, "get_path", lambda _name: str(private_site))
    monkeypatch.setattr(runtime_subject.sys, "executable", str(python))
    monkeypatch.setitem(
        runtime_subject.sys.modules,
        "pytest",
        type("UnloadedPytest", (), {"__file__": None})(),
    )
    monkeypatch.setattr(
        runtime_subject, "read_bounded_regular_file", lambda *_args, **_kwargs: receipt
    )
    monkeypatch.setattr(runtime_subject, "exact_private_file_is_valid", lambda *_args: True)

    assert runtime_subject._dependency_paths(
        repository,
        {
            "AGENCY_CI_PYTHON": str(python),
            "AGENCY_CI_ROOT": str(runtime_root),
        },
    ) == (repository, private_site, dependency_root)


def test_dependency_discovery_rejects_malformed_loaded_pytest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path, file_count=1)
    private_site = tmp_path / "private-site"
    private_site.mkdir()
    malformed_package = tmp_path / "not-pytest"
    malformed_package.mkdir()
    malformed_init = malformed_package / "__init__.py"
    malformed_init.write_text("", encoding="utf-8")
    monkeypatch.setattr(runtime_subject.sysconfig, "get_path", lambda _name: str(private_site))
    monkeypatch.setitem(
        runtime_subject.sys.modules,
        "pytest",
        type("MalformedPytest", (), {"__file__": str(malformed_init)})(),
    )

    with pytest.raises(RuntimeError, match="loaded pytest package path"):
        runtime_subject._dependency_paths(repository, {})


def test_direct_and_module_dry_run_are_identical_and_do_not_mutate_runtime_paths(
    tmp_path: Path,
    self_host_runtime_home: Path,
) -> None:
    repository = _repository(tmp_path, file_count=4)
    runtime_home = self_host_runtime_home
    contract = subject.build_runtime_contract(repository, "local-change-loop", os.environ)
    runtime_parent = subject.ci_runtime_root_path(
        contract.label,
        home_dir=runtime_home,
    ).parent
    lock_parent = subject._repo_execution_lock_path(
        repository.resolve(strict=True),
        create_parent=False,
    ).parent
    before = {
        runtime_parent: _filesystem_snapshot(runtime_parent),
        lock_parent: _filesystem_snapshot(lock_parent),
    }
    script = Path(subject.__file__).resolve()
    arguments = [
        "--repo-root",
        str(repository),
        "--runtime-home",
        str(runtime_home),
        "--shards",
        "2",
        "--dry-run",
    ]
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    direct = subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=script.parents[1],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    module = subprocess.run(
        [sys.executable, "-m", "scripts.run_parallel_change_loop", *arguments],
        cwd=script.parents[1],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert direct.returncode == module.returncode == 0
    assert direct.stderr == module.stderr == ""
    assert direct.stdout == module.stdout
    payload = json.loads(direct.stdout)
    assert payload["collection"] == {
        "equivalent": True,
        "serial_file_count": 4,
        "sharded_file_count": 4,
    }
    assert Path(payload["stable_runtime_root"]).parent == runtime_parent
    assert not Path(payload["stable_runtime_root"]).exists()
    assert not Path(payload["scratch_root"]).exists()
    assert before == {
        runtime_parent: _filesystem_snapshot(runtime_parent),
        lock_parent: _filesystem_snapshot(lock_parent),
    }
