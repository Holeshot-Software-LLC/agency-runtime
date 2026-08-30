from __future__ import annotations

import argparse
import re
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

from agency_runtime.cli import eval_commands
from agency_runtime.core.evals import decision_conformance as conformance


def _mutation(
    *,
    source_path: str = "agency_runtime/example.py",
    test_node: str = "tests/test_example.py::test_decision",
) -> conformance.DecisionMutation:
    return conformance.DecisionMutation(
        mutation_id="example-mutation",
        invariant="The example decision remains enabled.",
        source_path=source_path,
        before="DECISION = True",
        after="DECISION = False",
        test_node=test_node,
    )


def _fixture_repository(root: Path) -> tuple[Path, conformance.DecisionMutation]:
    repository = root / "repository"
    source = repository / "agency_runtime" / "example.py"
    test = repository / "tests" / "test_example.py"
    source.parent.mkdir(parents=True)
    test.parent.mkdir(parents=True)
    source.write_text("DECISION = True", encoding="utf-8")
    (repository / "agency_runtime" / "__init__.py").write_text("", encoding="utf-8")
    test.write_text("def test_decision(): pass", encoding="utf-8")
    (repository / "pyproject.toml").write_text("[tool.pytest.ini_options]", encoding="utf-8")
    return repository, _mutation()


def test_curated_manifest_anchors_are_current_and_unique() -> None:
    root = Path(__file__).resolve().parent.parent

    assert len({item.mutation_id for item in conformance.MUTATIONS}) == len(conformance.MUTATIONS)
    for mutation in conformance.MUTATIONS:
        source = root / mutation.source_path
        assert source.is_file()
        assert source.read_text(encoding="utf-8").count(mutation.before) == 1
        test_path, node = mutation.test_node.split("::", 1)
        test_file = root / test_path
        assert test_file.is_file()
        # The baseline collects every named node; a test renamed or removed
        # without updating the manifest makes the whole gate unrunnable, so
        # pin node existence too (parametrized ids reduce to the function).
        function_name = node.split("[", 1)[0]
        assert re.search(
            rf"^def {re.escape(function_name)}\(",
            test_file.read_text(encoding="utf-8"),
            re.MULTILINE,
        ), f"{mutation.mutation_id} names a missing test node: {mutation.test_node}"


@pytest.mark.parametrize(
    ("run", "expected"),
    [
        (conformance._PytestRun(1, ("tests/test_example.py::test_decision",), 3), "killed"),
        (conformance._PytestRun(0, (), 3), "survived"),
        (conformance._PytestRun(None, (), 3, timed_out=True), "timeout"),
        (conformance._PytestRun(2, (), 3), "invalid_test_result"),
        (
            conformance._PytestRun(1, ("tests/test_example.py::test_other",), 3),
            "invalid_test_result",
        ),
    ],
)
def test_mutation_classification_requires_the_expected_ordinary_failure(
    tmp_path: Path,
    run: conformance._PytestRun,
    expected: str,
) -> None:
    source = tmp_path / "agency_runtime" / "example.py"
    source.parent.mkdir()
    source.write_text("DECISION = True", encoding="utf-8")
    mutation = _mutation()

    result = conformance._mutation_result(
        mutation,
        tmp_path,
        python_executable=sys.executable,
        fixture_python_executable=sys.executable,
        timeout_seconds=10,
        source_root=tmp_path,
        pytest_runner=lambda *_args: run,
    )

    assert result["status"] == expected


def test_baseline_gives_each_named_test_its_own_deadline(tmp_path: Path) -> None:
    observed: list[tuple[tuple[str, ...], float]] = []

    def runner(checkout, nodes, _python, _fixture_python, timeout, source_root):
        assert checkout == tmp_path
        assert source_root == tmp_path
        observed.append((tuple(nodes), timeout))
        return conformance._PytestRun(0, (), 7)

    result = conformance._run_baseline(
        tmp_path,
        ("tests/test_one.py::test_one", "tests/test_two.py::test_two"),
        sys.executable,
        sys.executable,
        90,
        tmp_path,
        pytest_runner=runner,
    )

    assert result == conformance._PytestRun(0, (), 14)
    assert observed == [
        (("tests/test_one.py::test_one",), 90),
        (("tests/test_two.py::test_two",), 90),
    ]


def test_baseline_stops_after_the_first_failed_node(tmp_path: Path) -> None:
    observed: list[str] = []

    def runner(_checkout, nodes, _python, _fixture_python, _timeout, _source_root):
        observed.append(nodes[0])
        if len(observed) == 1:
            return conformance._PytestRun(0, (), 3)
        return conformance._PytestRun(None, (), 5, timed_out=True)

    result = conformance._run_baseline(
        tmp_path,
        ("test_one", "test_two", "test_three"),
        sys.executable,
        sys.executable,
        90,
        tmp_path,
        pytest_runner=runner,
    )

    assert result == conformance._PytestRun(None, (), 8, timed_out=True)
    assert observed == ["test_one", "test_two"]


def test_baseline_preserves_bounded_failure_diagnostic(tmp_path: Path) -> None:
    failure = conformance._PytestRun(
        1,
        ("tests/test_one.py::test_one",),
        3,
        failure_excerpt="AssertionError: exact private path was rejected",
    )

    result = conformance._run_baseline(
        tmp_path,
        ("tests/test_one.py::test_one",),
        sys.executable,
        sys.executable,
        90,
        tmp_path,
        pytest_runner=lambda *_args: failure,
    )

    assert result.failure_excerpt == "AssertionError: exact private path was rejected"


def test_pytest_environment_separates_runner_from_trusted_fixture_launcher(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    observed: dict[str, str] = {}
    command: list[str] = []

    def run(invocation, **kwargs):
        command.extend(invocation)
        observed.update(kwargs["env"])
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(conformance.subprocess, "run", run)
    conformance._run_pytest(
        checkout,
        ("tests/test_example.py::test_decision",),
        "/private/evaluator-python",
        "/trusted/persistent-python",
        10,
        tmp_path,
    )

    assert command[:3] == ["/private/evaluator-python", "-m", "pytest"]
    assert observed["AGENCY_CI_PYTHON"] == "/trusted/persistent-python"


def test_default_fixture_selection_never_derives_from_noncurrent_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, mutation = _fixture_repository(tmp_path)
    runner = tmp_path / "workspace-venv" / "python.exe"
    runner.parent.mkdir()
    runner.write_text("runner", encoding="utf-8")
    scratch = tmp_path / "private-scratch"
    scratch.mkdir()
    resolver_requests: list[str | Path | None] = []
    receipts: list[tuple[str, str]] = []

    @contextmanager
    def private_copy(*, prefix: str):
        assert prefix == "decision-conformance"
        yield scratch

    def resolve_fixture(requested: str | Path | None = None) -> str:
        resolver_requests.append(requested)
        return "/trusted/persistent-python"

    def fake_pytest(_checkout, nodes, runner_python, fixture_python, *_args):
        receipts.append((runner_python, fixture_python))
        if len(receipts) == 1:
            return conformance._PytestRun(0, (), 1)
        return conformance._PytestRun(1, (nodes[0],), 1)

    monkeypatch.setattr(conformance, "private_temporary_directory", private_copy)
    monkeypatch.setattr(conformance, "_resolve_fixture_python_executable", resolve_fixture)
    report = conformance.run_decision_conformance_eval(
        repository,
        mutations=(mutation,),
        python_executable=str(runner),
        pytest_runner=fake_pytest,
    )

    assert report["passed"] is True
    assert resolver_requests == [None]
    assert receipts == [
        (str(runner.resolve()), "/trusted/persistent-python"),
        (str(runner.resolve()), "/trusted/persistent-python"),
    ]


def test_explicit_fixture_launcher_is_validated_and_preserved_exactly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, mutation = _fixture_repository(tmp_path)
    runner = tmp_path / "workspace-venv" / "python.exe"
    fixture = tmp_path / "trusted-runtime" / "python.exe"
    runner.parent.mkdir()
    fixture.parent.mkdir()
    runner.write_text("runner", encoding="utf-8")
    fixture.write_text("fixture", encoding="utf-8")
    scratch = tmp_path / "private-scratch"
    scratch.mkdir()
    requested: list[str | Path | None] = []
    receipts: list[tuple[str, str]] = []

    @contextmanager
    def private_copy(*, prefix: str):
        assert prefix == "decision-conformance"
        yield scratch

    def resolve_fixture(value: str | Path | None = None) -> str:
        requested.append(value)
        return str(fixture.resolve())

    def fake_pytest(_checkout, nodes, runner_python, fixture_python, *_args):
        receipts.append((runner_python, fixture_python))
        if len(receipts) == 1:
            return conformance._PytestRun(0, (), 1)
        return conformance._PytestRun(1, (nodes[0],), 1)

    monkeypatch.setattr(conformance, "private_temporary_directory", private_copy)
    monkeypatch.setattr(conformance, "_resolve_fixture_python_executable", resolve_fixture)
    report = conformance.run_decision_conformance_eval(
        repository,
        mutations=(mutation,),
        python_executable=str(runner),
        fixture_python_executable=fixture,
        pytest_runner=fake_pytest,
    )

    assert report["passed"] is True
    assert requested == [fixture]
    assert receipts == [
        (str(runner.resolve()), str(fixture.resolve())),
        (str(runner.resolve()), str(fixture.resolve())),
    ]


def test_unsafe_explicit_fixture_fails_before_copy_or_pytest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, mutation = _fixture_repository(tmp_path)
    runner = tmp_path / "workspace-venv" / "python.exe"
    runner.parent.mkdir()
    runner.write_text("runner", encoding="utf-8")
    copied = False
    ran_pytest = False

    def reject_fixture(_requested: str | Path | None = None) -> str:
        raise OSError("unsafe persistent fixture launcher")

    def copy_inputs(*_args, **_kwargs) -> None:
        nonlocal copied
        copied = True

    def fake_pytest(*_args) -> conformance._PytestRun:
        nonlocal ran_pytest
        ran_pytest = True
        return conformance._PytestRun(0, (), 1)

    monkeypatch.setattr(conformance, "_resolve_fixture_python_executable", reject_fixture)
    monkeypatch.setattr(conformance, "_copy_inputs", copy_inputs)
    with pytest.raises(OSError, match="unsafe persistent fixture launcher"):
        conformance.run_decision_conformance_eval(
            repository,
            mutations=(mutation,),
            python_executable=str(runner),
            fixture_python_executable=tmp_path / "unsafe" / "python.exe",
            pytest_runner=fake_pytest,
        )

    assert copied is False
    assert ran_pytest is False


def test_evaluator_mutates_only_private_copies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    source = repository / "agency_runtime" / "example.py"
    test = repository / "tests" / "test_example.py"
    source.parent.mkdir(parents=True)
    test.parent.mkdir(parents=True)
    source.write_text("DECISION = True", encoding="utf-8")
    (repository / "agency_runtime" / "__init__.py").write_text("", encoding="utf-8")
    test.write_text("def test_decision(): pass", encoding="utf-8")
    (repository / "pyproject.toml").write_text("[tool.pytest.ini_options]", encoding="utf-8")
    scratch = tmp_path / "private-scratch"
    scratch.mkdir()
    mutation = _mutation()
    observed: list[Path] = []

    @contextmanager
    def private_copy(*, prefix: str):
        assert prefix == "decision-conformance"
        yield scratch

    def fake_pytest(checkout, nodes, _python, _fixture_python, _timeout, source_root):
        observed.append(checkout)
        assert checkout != source_root
        mutated = (checkout / mutation.source_path).read_text(encoding="utf-8")
        if "False" in mutated:
            return conformance._PytestRun(1, (nodes[0],), 2)
        return conformance._PytestRun(0, (), 2)

    monkeypatch.setattr(conformance, "private_temporary_directory", private_copy)
    report = conformance.run_decision_conformance_eval(
        repository,
        mutations=(mutation,),
        python_executable=sys.executable,
        pytest_runner=fake_pytest,
    )

    assert report["passed"] is True
    assert report["source_unchanged"] is True
    assert report["counts"] == {
        "mutations": 1,
        "killed": 1,
        "survived": 0,
        "invalid": 0,
    }
    assert source.read_text(encoding="utf-8") == "DECISION = True"
    assert len(observed) == 2
    assert all(path.is_relative_to(scratch) for path in observed)


def test_evaluator_rejects_linked_package_inputs(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    package = repository / "agency_runtime"
    tests = repository / "tests"
    package.mkdir(parents=True)
    tests.mkdir()
    source = package / "example.py"
    source.write_text("DECISION = True", encoding="utf-8")
    (package / "__init__.py").write_text("", encoding="utf-8")
    test = tests / "test_example.py"
    test.write_text("def test_decision(): pass", encoding="utf-8")
    (repository / "pyproject.toml").write_text("[tool.pytest.ini_options]", encoding="utf-8")
    try:
        (package / "linked.py").symlink_to(source)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    with pytest.raises(ValueError, match="link or reparse point"):
        conformance.run_decision_conformance_eval(
            repository,
            mutations=(_mutation(),),
            python_executable=sys.executable,
        )


def test_baseline_failure_never_admits_mutation_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    source = repository / "agency_runtime" / "example.py"
    test = repository / "tests" / "test_example.py"
    source.parent.mkdir(parents=True)
    test.parent.mkdir(parents=True)
    source.write_text("DECISION = True", encoding="utf-8")
    (repository / "agency_runtime" / "__init__.py").write_text("", encoding="utf-8")
    test.write_text("def test_decision(): pass", encoding="utf-8")
    (repository / "pyproject.toml").write_text("[tool.pytest.ini_options]", encoding="utf-8")
    scratch = tmp_path / "private-scratch"
    scratch.mkdir()

    @contextmanager
    def private_copy(*, prefix: str):
        del prefix
        yield scratch

    monkeypatch.setattr(conformance, "private_temporary_directory", private_copy)
    report = conformance.run_decision_conformance_eval(
        repository,
        mutations=(_mutation(),),
        python_executable=sys.executable,
        pytest_runner=lambda *_args: conformance._PytestRun(
            1,
            ("tests/test_example.py::test_decision",),
            2,
            failure_excerpt="AssertionError: baseline diagnostic",
        ),
    )

    assert report["passed"] is False
    assert report["baseline"]["status"] == "failed"
    assert report["baseline"]["failure_excerpt"] == "AssertionError: baseline diagnostic"
    assert report["mutations"] == []
    assert report["counts"]["killed"] == 0


def test_cli_decision_conformance_prints_bounded_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = {
        "passed": True,
        "counts": {"mutations": 1, "killed": 1, "survived": 0, "invalid": 0},
        "source_unchanged": True,
        "baseline": {"status": "passed"},
        "mutations": [{"mutation_id": "example", "status": "killed"}],
        "evidence_boundary": "curated only",
    }
    monkeypatch.setattr(
        eval_commands,
        "run_decision_conformance_eval",
        lambda *_args, **_kwargs: report,
    )

    result = eval_commands.cmd_eval_decision_conformance(
        argparse.Namespace(repository=".", timeout=90, json=False)
    )

    assert result == 0
    output = capsys.readouterr().out
    assert "decision conformance passed: killed=1/1 survived=0 invalid=0" in output
    assert "source-unchanged=True" in output
    assert "ok	example	killed" in output
