"""Contracts for the isolated local parallel pytest change loop."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from scripts import run_parallel_change_loop as subject


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


def _plan(tmp_path: Path, *, shard_count: int = 4, timeout: float = 17) -> subject.ParallelTestPlan:
    repository = _repository(tmp_path, file_count=max(8, shard_count))
    return subject.build_parallel_test_plan(
        repo_root=repository,
        shard_count=shard_count,
        runtime_preparer=_runtime_preparer(tmp_path / "runtimes"),
        ambient_environment=_ambient(),
        timeout_seconds=timeout,
    )


def test_plan_uses_one_runtime_exact_shards_and_least_privilege_environment(
    tmp_path: Path,
) -> None:
    labels: list[str] = []
    repository = _repository(tmp_path)
    plan = subject.build_parallel_test_plan(
        repo_root=repository,
        runtime_preparer=_runtime_preparer(tmp_path / "runtimes", labels),
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


def test_dry_run_is_deterministic_resource_free_and_concurrent_safe(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    def preparer(*_args: object, **_kwargs: object) -> dict[str, str]:
        raise AssertionError("dry-run must not prepare a runtime")

    def build(_index: int) -> dict[str, Any]:
        plan = subject.build_parallel_test_plan(
            repo_root=repository,
            runtime_preparer=preparer,
            ambient_environment=_ambient(),
            dry_run=True,
        )
        assert plan.use.state == "ready"
        return subject.plan_preview(plan)

    with ThreadPoolExecutor(max_workers=4) as executor:
        previews = tuple(executor.map(build, range(4)))

    assert previews.count(previews[0]) == 4
    assert previews[0]["schema_version"] == "agency.local-parallel-tests.v4"
    assert not Path(previews[0]["scratch_root"]).exists()
    assert not (tmp_path / "runtimes").exists()


def test_execution_uses_balanced_capture_and_replaces_one_coherent_log_set(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
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


def test_plan_is_single_use_and_repo_lock_rejects_concurrent_labels(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    preparer = _runtime_preparer(tmp_path / "runtimes")
    first = subject.build_parallel_test_plan(
        repo_root=repository,
        shard_count=1,
        label="first-label",
        runtime_preparer=preparer,
        ambient_environment=_ambient(),
    )
    second = subject.build_parallel_test_plan(
        repo_root=repository,
        shard_count=1,
        label="second-label",
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan(tmp_path, shard_count=1)
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


def test_invalid_limits_and_dry_execution_fail_before_start(tmp_path: Path) -> None:
    plan = _plan(tmp_path, shard_count=1)
    for value in (True, 0, subject.MAX_LOG_BYTES + 1):
        with pytest.raises(ValueError, match="maximum_log_bytes"):
            subject.run_parallel_test_plan(plan, maximum_log_bytes=value)  # type: ignore[arg-type]
    assert plan.use.state == "ready"
    dry = subject.build_parallel_test_plan(
        repo_root=plan.repo_root,
        shard_count=1,
        runtime_preparer=_runtime_preparer(tmp_path / "dry-runtime"),
        ambient_environment=_ambient(),
        dry_run=True,
    )
    with pytest.raises(ValueError, match="dry-run"):
        subject.run_parallel_test_plan(dry)


def test_real_private_venv_executes_pytest_without_secret_or_global_plugins(
    tmp_path: Path,
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
    ambient = dict(os.environ)
    ambient["OPENAI_API_KEY"] = "do-not-leak"
    plan = subject.build_parallel_test_plan(
        repo_root=repository,
        shard_count=1,
        runtime_home=tmp_path,
        ambient_environment=ambient,
        timeout_seconds=60,
    )

    exit_code, results = subject.run_parallel_test_plan(plan)

    assert exit_code == 0 and results[0].returncode == 0
    assert not plan.scratch_root.exists()
    configuration = plan.stable_runtime_root / "venv" / "pyvenv.cfg"
    assert "include-system-site-packages = false" in configuration.read_text("utf-8").lower()


def test_fixed_runtime_self_heals_when_node_identity_changes(tmp_path: Path) -> None:
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
        runtime_home=tmp_path,
        ambient_environment=ambient,
    )
    sentinel = first.stable_runtime_root / "old-runtime-sentinel"
    sentinel.write_text("old", encoding="utf-8")
    node.write_bytes(b"node-v2-changed")
    node.chmod(0o700)

    second = subject.build_parallel_test_plan(
        repo_root=repository,
        shard_count=1,
        runtime_home=tmp_path,
        ambient_environment=ambient,
    )

    assert second.stable_runtime_root == first.stable_runtime_root
    assert second.runtime_key != first.runtime_key
    assert not sentinel.exists()
    assert Path(second.shards[0].environment["AGENCY_CI_NODE"]).read_bytes() == node.read_bytes()


def test_killed_runner_scratch_is_recovered_by_next_real_execution(tmp_path: Path) -> None:
    repository = _repository(
        tmp_path,
        file_count=1,
        body="import time\ndef test_wait():\n    time.sleep(30)\n",
    )
    ambient = dict(os.environ)
    preview = subject.build_parallel_test_plan(
        repo_root=repository,
        shard_count=1,
        runtime_home=tmp_path,
        ambient_environment=ambient,
        dry_run=True,
    )
    script = Path(subject.__file__).resolve()
    process = subprocess.Popen(
        [
            sys.executable,
            str(script),
            "--repo-root",
            str(repository),
            "--runtime-home",
            str(tmp_path),
            "--shards",
            "1",
            "--timeout-seconds",
            "60",
        ],
        cwd=script.parents[1],
        env=ambient,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not preview.scratch_root.exists():
            if process.poll() is not None:
                break
            time.sleep(0.05)
        assert preview.scratch_root.exists()
        process.kill()
        process.communicate(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)
    (repository / "tests" / "test_0.py").write_text(
        "def test_recovered():\n    assert True\n", encoding="utf-8"
    )
    recovered = subject.build_parallel_test_plan(
        repo_root=repository,
        shard_count=1,
        runtime_home=tmp_path,
        ambient_environment=ambient,
        timeout_seconds=60,
    )
    exit_code, _results = subject.run_parallel_test_plan(recovered)
    assert exit_code == 0
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


def test_direct_and_module_dry_run_are_identical_and_do_not_mutate_runtime_paths(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path, file_count=4)
    runtime_home = tmp_path / "runtime-home"
    runtime_home.mkdir()
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
