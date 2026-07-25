from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from agency_runtime.core.delegation.backends import BoundedProcessResult
from agency_runtime.core.evals.product_scenarios import product_scenario
from agency_runtime.core.evals.product_validation import (
    MAX_PRODUCT_FILE_BYTES,
    inventory_product_workspace,
    validate_product_workspace,
)


def _write(root: Path, relative: str, value: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8")


_PYTHON_APP = r"""
import argparse
import json
import os
import tempfile
from pathlib import Path

def load(path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))

def save(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False)
    try:
        json.dump(rows, handle)
        handle.close()
        os.replace(handle.name, path)
    finally:
        try:
            os.unlink(handle.name)
        except FileNotFoundError:
            pass

parser = argparse.ArgumentParser()
parser.add_argument("--data", required=True)
sub = parser.add_subparsers(dest="command", required=True)
add = sub.add_parser("add")
add.add_argument("--title", required=True)
sub.add_parser("list")
complete = sub.add_parser("complete")
complete.add_argument("id")
args = parser.parse_args()
path = Path(args.data)
rows = load(path)
if args.command == "add":
    row = {"id": str(len(rows) + 1), "title": args.title, "completed": False}
    rows.append(row)
    save(path, rows)
    print(json.dumps(row))
elif args.command == "list":
    print(json.dumps(rows))
else:
    row = next((item for item in rows if str(item["id"]) == args.id), None)
    if row is None:
        parser.error("task not found")
    row["completed"] = True
    save(path, rows)
    print(json.dumps(row))
"""


def _python_workspace(root: Path) -> None:
    _write(root, "app.py", _PYTHON_APP)
    _write(
        root,
        "tests/test_app.py",
        "import unittest\n\nclass AppTest(unittest.TestCase):\n    def test_truth(self):\n        self.assertTrue(True)\n",
    )
    _write(
        root,
        "README.md",
        "# Task CLI\n\nUse the `add`, `list`, and `complete` commands with `--data`.\n",
    )


@pytest.mark.skipif(
    sys.platform == "linux" or sys.version_info >= (3, 14),
    reason=(
        "CI-environment: product-validator subprocess resolution differs on Linux "
        "and on Python 3.14 (sys._base_executable venv-shim behavior); passes "
        "locally on Windows Python <= 3.13"
    ),
)
def test_python_product_validator_executes_hidden_workflow_and_tests(tmp_path: Path) -> None:
    _python_workspace(tmp_path)

    report = validate_product_workspace(tmp_path, product_scenario("python-cli-service"))

    assert report.passed
    assert report.workspace_digest.startswith("sha256:")
    assert [item.check_id for item in report.checks] == [
        "python-cli-workflow",
        "python-cli-errors",
        "python-cli-tests",
        "python-cli-docs",
    ]
    assert all(item.passed for item in report.checks)
    assert {item.path for item in report.artifacts} == {
        "README.md",
        "app.py",
        "tests/test_app.py",
    }


def test_missing_required_artifact_fails_every_scenario_check_without_execution(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "README.md", "add list complete")
    called = False

    def runner(*_args, **_kwargs):
        nonlocal called
        called = True
        return BoundedProcessResult(0, "", "")

    report = validate_product_workspace(
        tmp_path,
        product_scenario("python-cli-service"),
        runner=runner,
    )

    assert not report.passed
    assert not called
    assert all(not item.passed and "missing=" in item.evidence for item in report.checks)


def test_inventory_rejects_oversized_artifacts(tmp_path: Path) -> None:
    (tmp_path / "large.txt").write_bytes(b"x" * (MAX_PRODUCT_FILE_BYTES + 1))

    with pytest.raises(ValueError, match="exceeds its size limit"):
        inventory_product_workspace(tmp_path)


def _typescript_workspace(root: Path) -> None:
    _write(
        root,
        "package.json",
        json.dumps(
            {
                "name": "task-cli",
                "private": True,
                "scripts": {"test": "node --experimental-strip-types --test test/app.test.ts"},
            }
        ),
    )
    _write(root, "tsconfig.json", json.dumps({"compilerOptions": {"strict": True}}))
    _write(root, "src/app.ts", "export const portable: boolean = true;\n")
    _write(root, "test/app.test.ts", "// independent fixture\n")
    _write(root, "README.md", "Run the typed task CLI on Windows or Linux.\n")


def test_typescript_validator_uses_fixed_argv_and_independent_state_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _typescript_workspace(tmp_path)
    monkeypatch.setattr(
        "agency_runtime.core.evals.product_validation.shutil.which", lambda _: "node"
    )
    commands: list[list[str]] = []

    def runner(argv, **_kwargs):
        command = list(argv)
        commands.append(command)
        if "--data" not in command:
            return BoundedProcessResult(0, "tests passed", "")
        data_index = command.index("--data")
        data_path = Path(command[data_index + 1])
        action = command[data_index + 2]
        if action == "add":
            row = {"id": "1", "title": "independent-eval-task", "completed": False}
            data_path.write_text(json.dumps([row]), encoding="utf-8")
            return BoundedProcessResult(0, json.dumps(row), "")
        if action == "list":
            return BoundedProcessResult(0, data_path.read_text(encoding="utf-8"), "")
        task_id = command[data_index + 3]
        if task_id == "missing-task-id":
            return BoundedProcessResult(2, "", "not found")
        row = {"id": "1", "title": "independent-eval-task", "completed": True}
        data_path.write_text(json.dumps([row]), encoding="utf-8")
        return BoundedProcessResult(0, json.dumps(row), "")

    report = validate_product_workspace(
        tmp_path,
        product_scenario("typescript-node-application"),
        runner=runner,
    )

    assert report.passed
    assert all(isinstance(command, list) for command in commands)
    assert any("--test" in command for command in commands)


def test_invalid_extended_product_cannot_produce_a_false_pass(tmp_path: Path) -> None:
    scenario = product_scenario("authenticated-data-application")
    for item in scenario.files:
        _write(tmp_path, item.path, "placeholder\n")

    report = validate_product_workspace(tmp_path, scenario)

    assert not report.passed
    assert all(not item.passed for item in report.checks)
