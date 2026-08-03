from __future__ import annotations

import json
import os
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from agency_runtime.core.owned_process import BoundedBinaryProcessResult
from scripts import run_ci_session_pair as subject
from tests.runtime_support import trusted_test_interpreter, wait_for_process_exit

ROOT = Path(__file__).resolve().parents[1]


def _real_process_interpreter() -> Path:
    """Use an OS-owned POSIX interpreter outside hosted tool-cache namespaces."""

    if os.name != "nt":
        system_python = Path("/usr/bin/python3")
        if system_python.is_file() and os.access(system_python, os.X_OK):
            return system_python
    return trusted_test_interpreter()


def _result(
    returncode: int = 0,
    *,
    stdout: bytes = b"",
    cancelled: bool = False,
    timed_out: bool = False,
    stdout_truncated: bool = False,
    stderr_truncated: bool = False,
    failure_category: str | None = None,
) -> BoundedBinaryProcessResult:
    category = failure_category
    if category is None and cancelled:
        category = "cancelled"
    if category is None and timed_out:
        category = "timeout"
    return BoundedBinaryProcessResult(
        returncode=returncode,
        stdout=stdout,
        stderr=b"",
        timed_out=timed_out,
        cancelled=cancelled,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        failure_category=category,
    )


def _runtime(tmp_path: Path, label: str) -> subject.RuntimeBoundary:
    root = tmp_path / label
    home = root / "home"
    temporary = root / "temp"
    home.mkdir(parents=True)
    temporary.mkdir()
    python = root / ("python.exe" if sys.platform == "win32" else "python")
    python.write_bytes(b"private-python")
    return subject.RuntimeBoundary(root, python, home, temporary)


def _plan(tmp_path: Path, label: str) -> subject.SessionPlan:
    runtime = _runtime(tmp_path, label)
    coverage = runtime.temporary / ".coverage"
    return subject.SessionPlan(
        label=label,
        expected_version=f"{sys.version_info.major}.{sys.version_info.minor}",
        system_python=runtime.python,
        runtime=runtime,
        environment=subject._session_environment(runtime, coverage_file=coverage),
        pytest_command=(str(runtime.python), "-c", label),
        pytest_basetemp=runtime.temporary / "pytest",
        timeout_seconds=10,
    )


def test_pair_executes_both_sessions_concurrently_with_distinct_state(tmp_path: Path) -> None:
    plans = (_plan(tmp_path, "session-a"), _plan(tmp_path, "session-b"))
    barrier = threading.Barrier(2)
    observed: list[tuple[tuple[str, ...], dict[str, str], threading.Event]] = []
    lock = threading.Lock()

    def runner(argv, **kwargs):
        with lock:
            observed.append((tuple(argv), kwargs["env"], kwargs["cancel_event"]))
        barrier.wait(timeout=2)
        return _result(stdout=f"{argv[-1]}\n".encode())

    results = subject.execute_pair(plans, runner=runner)

    assert all(result.succeeded for result in results), results
    assert {call[0][-1] for call in observed} == {"session-a", "session-b"}
    assert len({call[1]["HOME"] for call in observed}) == 2
    assert len({call[1]["TEMP"] for call in observed}) == 2
    assert len({call[1]["COVERAGE_FILE"] for call in observed}) == 2
    assert len({id(call[2]) for call in observed}) == 1


def test_pair_runs_real_cross_platform_owned_processes(tmp_path: Path) -> None:
    interpreter = str(_real_process_interpreter())
    plans = []
    for label in ("real-a", "real-b"):
        runtime = _runtime(tmp_path, label)
        environment = subject._session_environment(
            runtime,
            coverage_file=runtime.temporary / ".coverage",
        )
        plans.append(
            subject.SessionPlan(
                label=label,
                expected_version=f"{sys.version_info.major}.{sys.version_info.minor}",
                system_python=Path(interpreter),
                runtime=runtime,
                environment=environment,
                pytest_command=(
                    interpreter,
                    "-c",
                    (
                        "import os; "
                        f"assert os.environ['HOME'] == {environment['HOME']!r}; "
                        f"print({label!r})"
                    ),
                ),
                pytest_basetemp=runtime.temporary / "pytest",
                timeout_seconds=10,
            )
        )

    results = subject.execute_pair(tuple(plans))

    assert all(result.succeeded for result in results), results
    assert {result.phases[0].result.stdout.strip().decode() for result in results} == {
        "real-a",
        "real-b",
    }


def test_pair_cancels_and_quiesces_its_peer_after_internal_failure(tmp_path: Path) -> None:
    plans = (_plan(tmp_path, "fail"), _plan(tmp_path, "peer"))
    peer_started = threading.Event()
    peer_quiesced = threading.Event()

    def runner(argv, **kwargs):
        if argv[-1] == "peer":
            peer_started.set()
            assert kwargs["cancel_event"].wait(timeout=2)
            peer_quiesced.set()
            return _result(130, cancelled=True)
        assert peer_started.wait(timeout=2)
        raise RuntimeError("controller failure")

    with pytest.raises(RuntimeError, match="controller failure"):
        subject.execute_pair(plans, runner=runner)

    assert peer_quiesced.is_set()


def test_pair_does_not_fail_fast_on_an_ordinary_test_failure(tmp_path: Path) -> None:
    plans = (_plan(tmp_path, "failed-tests"), _plan(tmp_path, "passing-tests"))
    observed: list[str] = []

    def runner(argv, **_kwargs):
        observed.append(argv[-1])
        return _result(1 if argv[-1] == "failed-tests" else 0)

    results = subject.execute_pair(plans, runner=runner)

    assert set(observed) == {"failed-tests", "passing-tests"}
    assert {result.label: result.succeeded for result in results} == {
        "failed-tests": False,
        "passing-tests": True,
    }


@pytest.mark.parametrize(
    "outcome",
    ("missing-coverage", "stdout-truncated", "stderr-truncated", "containment"),
)
def test_pair_cancels_peer_after_nonordinary_session_outcome(
    tmp_path: Path,
    outcome: str,
) -> None:
    exceptional = _plan(tmp_path, "exceptional")
    if outcome == "missing-coverage":
        exceptional = replace(
            exceptional,
            coverage_path=exceptional.runtime.temporary / ".coverage.missing",
        )
    peer = _plan(tmp_path, "peer")
    peer_started = threading.Event()
    peer_quiesced = threading.Event()

    def runner(argv, **kwargs):
        if argv[-1] == "peer":
            peer_started.set()
            assert kwargs["cancel_event"].wait(timeout=2)
            peer_quiesced.set()
            return _result(130, cancelled=True)
        assert peer_started.wait(timeout=2)
        if outcome == "stdout-truncated":
            return _result(stdout=b"partial", stdout_truncated=True)
        if outcome == "stderr-truncated":
            return _result(stderr_truncated=True)
        if outcome == "containment":
            return _result(125, failure_category="containment")
        return _result()

    results = subject.execute_pair((exceptional, peer), runner=runner)

    by_label = {result.label: result for result in results}
    assert by_label["exceptional"].succeeded is False
    assert by_label["peer"].phases[0].result.cancelled is True
    assert peer_quiesced.is_set()


def test_real_timeout_cancels_and_reaps_peer_descendant(tmp_path: Path) -> None:
    interpreter = str(_real_process_interpreter())
    ready = tmp_path / "peer-pids.txt"
    timeout_runtime = _runtime(tmp_path, "timeout-runtime")
    peer_runtime = _runtime(tmp_path, "peer-runtime")
    timeout_plan = subject.SessionPlan(
        label="timeout",
        expected_version=f"{sys.version_info.major}.{sys.version_info.minor}",
        system_python=Path(interpreter),
        runtime=timeout_runtime,
        environment=subject._session_environment(
            timeout_runtime,
            coverage_file=timeout_runtime.temporary / ".coverage",
        ),
        pytest_command=(interpreter, "-c", "import time; time.sleep(60)"),
        pytest_basetemp=timeout_runtime.temporary / "pytest",
        timeout_seconds=10,
    )
    peer_script = """
import os
import pathlib
import subprocess
import sys
import time

child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
pathlib.Path(sys.argv[1]).write_text(
    f"{os.getpid()}\\n{child.pid}\\n",
    encoding="ascii",
)
time.sleep(60)
"""
    peer_plan = subject.SessionPlan(
        label="peer",
        expected_version=f"{sys.version_info.major}.{sys.version_info.minor}",
        system_python=Path(interpreter),
        runtime=peer_runtime,
        environment=subject._session_environment(
            peer_runtime,
            coverage_file=peer_runtime.temporary / ".coverage",
        ),
        pytest_command=(interpreter, "-c", peer_script, str(ready)),
        pytest_basetemp=peer_runtime.temporary / "pytest",
        timeout_seconds=15,
    )

    def coordinated_runner(argv, **kwargs):
        if tuple(argv) == timeout_plan.pytest_command:
            deadline = time.monotonic() + 10
            while not ready.is_file() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert ready.is_file(), "peer process tree did not become ready"
            kwargs["timeout"] = 0.2
        return subject.run_bounded_binary_process(tuple(argv), **kwargs)

    results = subject.execute_pair(
        (timeout_plan, peer_plan),
        runner=coordinated_runner,
    )

    by_label = {result.label: result for result in results}
    assert by_label["timeout"].phases[0].result.timed_out is True
    assert by_label["peer"].phases[0].result.cancelled is True
    parent_pid, child_pid = (int(value) for value in ready.read_text("ascii").splitlines())
    assert wait_for_process_exit(parent_pid, timeout=10)
    assert wait_for_process_exit(child_pid, timeout=10)


def test_green_process_with_truncated_evidence_fails_closed() -> None:
    result = subject.SessionResult(
        "truncated",
        (
            subject.PhaseResult(
                "pytest",
                _result(stdout=b"partial", stdout_truncated=True),
            ),
        ),
    )

    assert result.succeeded is False


def test_runtime_preparation_uses_and_rechecks_the_exact_interpreter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    root = tmp_path / "runtime"
    home = root / "home"
    temporary = root / "temp"
    environment = root / "venv"
    home.mkdir(parents=True)
    temporary.mkdir()
    environment.mkdir()
    runtime_python = environment / ("python.exe" if sys.platform == "win32" else "python")
    runtime_python.write_bytes(b"private-python")
    runtime_node = root / ("node.exe" if sys.platform == "win32" else "node")
    runtime_node.write_bytes(b"private-node")
    commands: list[tuple[str, ...]] = []
    controller_environments: list[dict[str, str]] = []
    for name in (
        "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
        "ACTIONS_ID_TOKEN_REQUEST_URL",
        "ACTIONS_RUNTIME_TOKEN",
        "ACTIONS_RUNTIME_URL",
        "GH_TOKEN",
        "GITHUB_ENV",
        "GITHUB_DEPLOY_TOKEN",
        "GITHUB_OUTPUT",
        "GITHUB_PAT",
        "GITHUB_PATH",
        "GITHUB_STATE",
        "GITHUB_STEP_SUMMARY",
        "GITHUB_TOKEN",
    ):
        monkeypatch.setenv(name, f"sensitive-{name.lower()}")
    monkeypatch.setenv("GITHUB_SHA", "deadbeef")
    monkeypatch.setenv("RUNNER_OS", "Windows")

    def runner(argv, **kwargs):
        command = tuple(argv)
        commands.append(command)
        controller_environments.append(kwargs["env"])
        if "scripts.prepare_ci_runtime" in command:
            return _result(
                stdout=(
                    json.dumps(
                        {
                            "AGENCY_CI_HOME": str(home),
                            "AGENCY_CI_NODE": str(runtime_node),
                            "AGENCY_CI_PYTHON": str(runtime_python),
                            "AGENCY_CI_ROOT": str(root),
                            "AGENCY_CI_TEMP": str(temporary),
                        },
                        sort_keys=True,
                    ).encode()
                    + b"\n"
                )
            )
        return _result(stdout=f"{version}\n".encode())

    boundary = subject._prepare_runtime(
        Path(sys.executable),
        expected_version=version,
        runtime_label="unit-runtime",
        runner=runner,
    )

    assert boundary == subject.RuntimeBoundary(
        root.resolve(),
        runtime_python.resolve(),
        home.resolve(),
        temporary.resolve(),
        runtime_node.resolve(),
    )
    assert commands[0][0] == str(Path(sys.executable).resolve())
    assert commands[1][-2:] == ("--label", "unit-runtime")
    assert commands[2][0] == str(runtime_python.resolve())
    assert len(controller_environments) == 3
    for controller_environment in controller_environments:
        assert not (
            subject._GITHUB_COMMAND_FILE_KEYS & controller_environment.keys()
            or subject._GITHUB_CREDENTIAL_KEYS & controller_environment.keys()
        )
        assert "ACTIONS_RUNTIME_URL" not in controller_environment
        assert "GITHUB_DEPLOY_TOKEN" not in controller_environment
        assert "GITHUB_PAT" not in controller_environment
        assert controller_environment["GITHUB_SHA"] == "deadbeef"
        assert controller_environment["RUNNER_OS"] == "Windows"


def test_session_environment_drops_pair_controller_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENCY_CI_PYTHON_A", "shared-controller-python")
    monkeypatch.setenv("AGENCY_CI_RUN_LABEL", "shared-controller-label")
    for name in (
        "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
        "ACTIONS_ID_TOKEN_REQUEST_URL",
        "ACTIONS_RUNTIME_TOKEN",
        "ACTIONS_RESULTS_URL",
        "GH_ENTERPRISE_TOKEN",
        "GH_TOKEN",
        "GITHUB_ENV",
        "GITHUB_DEPLOY_TOKEN",
        "GITHUB_OUTPUT",
        "GITHUB_PAT",
        "GITHUB_PATH",
        "GITHUB_STATE",
        "GITHUB_STEP_SUMMARY",
        "GITHUB_TOKEN",
    ):
        monkeypatch.setenv(name, f"sensitive-{name.lower()}")
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("GITHUB_SHA", "deadbeef")
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("RUNNER_OS", "Windows")
    runtime = _runtime(tmp_path, "isolated")

    environment = subject._session_environment(
        runtime,
        coverage_file=runtime.temporary / ".coverage",
    )

    assert "AGENCY_CI_PYTHON_A" not in environment
    assert "AGENCY_CI_RUN_LABEL" not in environment
    assert environment["AGENCY_CI_PYTHON"] == str(runtime.python)
    assert environment["PATH"].split(os.pathsep)[0] == str(runtime.python.parent)
    assert environment["VIRTUAL_ENV"] == str(runtime.python.parent.parent)
    assert not (
        subject._GITHUB_COMMAND_FILE_KEYS & environment.keys()
        or subject._GITHUB_CREDENTIAL_KEYS & environment.keys()
    )
    assert "ACTIONS_RESULTS_URL" not in environment
    assert "GITHUB_DEPLOY_TOKEN" not in environment
    assert "GITHUB_PAT" not in environment
    assert environment["CI"] == "true"
    assert environment["GITHUB_SHA"] == "deadbeef"
    assert environment["GITHUB_WORKSPACE"] == str(tmp_path)
    assert environment["RUNNER_OS"] == "Windows"

    mixed_case = {
        "actions_runtime_token": "secret",
        "Github_Deploy_Token": "secret",
        "Github_Env": "command-file",
        "Github_Sha": "deadbeef",
    }
    subject._strip_github_capabilities(mixed_case)
    assert mixed_case == {"Github_Sha": "deadbeef"}


def test_coverage_and_compatibility_commands_preserve_every_gate(tmp_path: Path) -> None:
    output = tmp_path / "coverage-output"
    output.mkdir()
    coverage_a = subject._coverage_plan(
        shard=0,
        system_python=Path(sys.executable),
        runtime=_runtime(tmp_path, "coverage-a"),
        output_root=output,
    )
    coverage_b = subject._coverage_plan(
        shard=1,
        system_python=Path(sys.executable),
        runtime=_runtime(tmp_path, "coverage-b"),
        output_root=output,
    )
    command = coverage_a.pytest_command

    assert command[:3] == (str(coverage_a.runtime.python), "-m", "pytest")
    assert command[command.index("-q") : command.index("-q") + 3] == ("-q", "-W", "error")
    assert command[command.index("-p") : command.index("-p") + 2] == (
        "-p",
        "no:cacheprovider",
    )
    assert command[command.index("-m", 3) : command.index("-m", 3) + 2] == (
        "-m",
        "not performance",
    )
    assert "--cov=agency_runtime" in command
    for module in subject._RELEASE_COVERAGE_MODULES:
        assert f"--cov={module}" in command
    assert "--cov-branch" in command and "--cov-report=" in command
    assert coverage_a.coverage_path != coverage_b.coverage_path
    assert coverage_a.pytest_basetemp != coverage_b.pytest_basetemp
    assert coverage_a.environment["HOME"] != coverage_b.environment["HOME"]
    assert coverage_a.environment["TEMP"] != coverage_b.environment["TEMP"]

    compatibility = subject._compatibility_plan(
        expected_version="3.10",
        system_python=Path(sys.executable),
        runtime=_runtime(tmp_path, "compatibility"),
    )
    assert compatibility.pytest_command[3:] == (
        "tests",
        "-q",
        "-W",
        "error",
        "-p",
        "no:cacheprovider",
        "-m",
        "not performance",
        "--basetemp",
        str(compatibility.pytest_basetemp),
    )
    assert compatibility.pip_check_command == (str(Path(sys.executable)), "-m", "pip", "check")

    timeouts: list[int] = []

    def runner(_argv, **kwargs):
        timeouts.append(kwargs["timeout"])
        return _result()

    session = subject._run_session(
        compatibility,
        runner=runner,
        cancel_event=threading.Event(),
    )
    assert session.succeeded
    assert timeouts == [subject._COMPATIBILITY_TIMEOUT_SECONDS, subject._PIP_CHECK_TIMEOUT_SECONDS]


def test_coverage_output_contract_rejects_missing_linked_empty_and_oversized_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = tmp_path / ".coverage.missing"
    assert subject._coverage_output_error(missing) == "coverage data was not published"

    valid = tmp_path / ".coverage.valid"
    valid.write_bytes(b"coverage")
    assert subject._coverage_output_error(valid) is None

    empty = tmp_path / ".coverage.empty"
    empty.touch()
    assert subject._coverage_output_error(empty) == (
        "coverage data failed its regular bounded file contract"
    )

    linked_source = tmp_path / ".coverage.link-source"
    linked = tmp_path / ".coverage.linked"
    linked_source.write_bytes(b"coverage")
    os.link(linked_source, linked)
    assert subject._coverage_output_error(linked) == (
        "coverage data failed its regular bounded file contract"
    )

    oversized = tmp_path / ".coverage.oversized"
    oversized.write_bytes(b"abc")
    monkeypatch.setattr(subject, "_MAX_COVERAGE_BYTES", 2)
    assert subject._coverage_output_error(oversized) == (
        "coverage data failed its regular bounded file contract"
    )


def test_governed_plan_builders_preserve_exact_members_and_interpreters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system_a = tmp_path / ("python-a.exe" if sys.platform == "win32" else "python-a")
    system_b = tmp_path / ("python-b.exe" if sys.platform == "win32" else "python-b")
    system_a.write_bytes(b"python-a")
    system_b.write_bytes(b"python-b")
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(subject, "_platform_name", lambda: "linux")

    prepared: list[tuple[Path, str, str]] = []
    coverage_runtimes = iter((_runtime(tmp_path, "coverage-0"), _runtime(tmp_path, "coverage-1")))

    def prepare_coverage(python, *, expected_version, runtime_label, runner):
        assert runner is subject.run_bounded_binary_process
        prepared.append((python, expected_version, runtime_label))
        return next(coverage_runtimes)

    monkeypatch.setattr(subject, "_prepare_runtime", prepare_coverage)
    coverage_args = subject.argparse.Namespace(
        shard_a=0,
        shard_b=1,
        python=system_a,
        run_label="unit",
    )
    coverage = subject._coverage_plans(coverage_args, output)

    assert [plan.label for plan in coverage] == ["coverage-shard-0", "coverage-shard-1"]
    assert all(plan.system_python == system_a.resolve() for plan in coverage)
    assert prepared == [
        (system_a.resolve(), "3.13", "cov-s0-unit"),
        (system_a.resolve(), "3.13", "cov-s1-unit"),
    ]

    prepared.clear()
    compatibility_runtimes = iter(
        (_runtime(tmp_path, "compatibility-310"), _runtime(tmp_path, "compatibility-311"))
    )

    def prepare_compatibility(python, *, expected_version, runtime_label, runner):
        assert runner is subject.run_bounded_binary_process
        prepared.append((python, expected_version, runtime_label))
        return next(compatibility_runtimes)

    monkeypatch.setattr(subject, "_prepare_runtime", prepare_compatibility)
    compatibility_args = subject.argparse.Namespace(
        platform="linux",
        python_a=system_a,
        python_b=system_b,
        version_a="3.10",
        version_b="3.11",
        run_label="unit",
    )
    compatibility = subject._compatibility_plans(compatibility_args, output)

    assert [plan.label for plan in compatibility] == [
        "compatibility-py3.10",
        "compatibility-py3.11",
    ]
    assert [plan.system_python for plan in compatibility] == [
        system_a.resolve(),
        system_b.resolve(),
    ]
    assert prepared == [
        (system_a.resolve(), "3.10", "compat-py310-unit"),
        (system_b.resolve(), "3.11", "compat-py311-unit"),
    ]


def test_main_creates_new_output_executes_exact_pair_and_emits_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plans = (_plan(tmp_path, "main-a"), _plan(tmp_path, "main-b"))
    results = tuple(
        subject.SessionResult(
            plan.label,
            (subject.PhaseResult("pytest", _result()),),
        )
        for plan in plans
    )
    observed: dict[str, object] = {}

    def coverage_plans(_args, output_root):
        observed["output_root"] = output_root
        return plans

    def execute_pair(received):
        observed["plans"] = received
        return results

    def emit_results(received):
        observed["results"] = received

    monkeypatch.setattr(subject, "_coverage_plans", coverage_plans)
    monkeypatch.setattr(subject, "execute_pair", execute_pair)
    monkeypatch.setattr(subject, "emit_results", emit_results)
    output = tmp_path / "main-output"

    returncode = subject.main(
        [
            "coverage",
            "--python",
            sys.executable,
            "--shard-a",
            "0",
            "--shard-b",
            "1",
            "--run-label",
            "unit",
            "--output-root",
            str(output),
        ]
    )

    assert returncode == 0
    assert observed == {
        "output_root": output.resolve(),
        "plans": plans,
        "results": results,
    }


def test_bounded_output_is_stably_labeled(capfd: pytest.CaptureFixture[str]) -> None:
    session = subject.SessionResult(
        "coverage-shard-0",
        (subject.PhaseResult("pytest", _result(stdout=b"all green\n")),),
    )

    subject.emit_results((session,))

    output = capfd.readouterr().out
    assert "[agency-ci-session:coverage-shard-0:pytest:status]" in output
    assert "[agency-ci-session:coverage-shard-0:pytest:stdout]\nall green" in output
    assert "[agency-ci-session:coverage-shard-0:pytest:stderr]" in output


def test_workflow_pairs_exact_coverage_and_compatibility_sessions() -> None:
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    jobs = workflow["jobs"]

    coverage = jobs["coverage"]
    assert coverage["runs-on"] == "ubuntu-24.04"
    assert coverage["strategy"]["fail-fast"] is False
    coverage_pairs = coverage["strategy"]["matrix"]["include"]
    assert coverage_pairs == [
        {"pair": 0, "label": 1, "shard_a": 0, "shard_b": 1},
        {"pair": 1, "label": 2, "shard_a": 2, "shard_b": 3},
    ]
    assert sorted(
        shard for pair in coverage_pairs for shard in (pair["shard_a"], pair["shard_b"])
    ) == [0, 1, 2, 3]
    coverage_run = next(
        step for step in coverage["steps"] if step["name"] == "Run paired coverage sessions"
    )
    for required in (
        "scripts.run_ci_session_pair coverage",
        '--python "${AGENCY_CI_PYTHON}"',
        '--shard-a "${AGENCY_CI_SHARD_A}"',
        '--shard-b "${AGENCY_CI_SHARD_B}"',
        '--output-root "${RUNNER_TEMP}/agency-coverage-pair-${AGENCY_CI_PAIR}"',
    ):
        assert required in coverage_run["run"]
    upload = next(step for step in coverage["steps"] if "upload-artifact@" in step.get("uses", ""))
    assert upload["with"]["name"] == "coverage-pair-${{ matrix.pair }}"
    assert upload["with"]["path"].endswith("/.coverage.*")

    compatibility = jobs["test"]
    assert compatibility["strategy"]["fail-fast"] is False
    pairs = compatibility["strategy"]["matrix"]["include"]
    assert pairs == [
        {
            "os": "ubuntu-24.04",
            "platform": "linux",
            "label": "ubuntu-310-311",
            "python_a": "3.10",
            "python_b": "3.11",
        },
        {
            "os": "ubuntu-24.04",
            "platform": "linux",
            "label": "ubuntu-312-314",
            "python_a": "3.12",
            "python_b": "3.14",
        },
        {
            "os": "windows-2022",
            "platform": "windows",
            "label": "windows-310-314",
            "python_a": "3.10",
            "python_b": "3.14",
        },
    ]
    assert {
        (pair["os"], version) for pair in pairs for version in (pair["python_a"], pair["python_b"])
    } == {
        ("ubuntu-24.04", "3.10"),
        ("ubuntu-24.04", "3.11"),
        ("ubuntu-24.04", "3.12"),
        ("ubuntu-24.04", "3.14"),
        ("windows-2022", "3.10"),
        ("windows-2022", "3.14"),
    }
    setup_steps = [
        step for step in compatibility["steps"] if "setup-python@" in step.get("uses", "")
    ]
    assert [(step["id"], step["with"]["python-version"]) for step in setup_steps] == [
        ("python-a", "${{ matrix.python_a }}"),
        ("python-b", "${{ matrix.python_b }}"),
    ]
    run = next(
        step
        for step in compatibility["steps"]
        if step["name"] == "Run paired compatibility sessions"
    )
    assert "scripts.run_ci_session_pair compatibility" in run["run"]
    assert '--platform "${AGENCY_CI_PLATFORM}"' in run["run"]
    assert '--version-a "${AGENCY_CI_VERSION_A}"' in run["run"]
    assert '--version-b "${AGENCY_CI_VERSION_B}"' in run["run"]
    assert not any(step["name"] == "Run tests" for step in compatibility["steps"])
