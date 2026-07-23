"""Independent artifact and behavior validation for product-level trials."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import stat
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.delegation.backends import BoundedProcessResult, run_bounded_process
from agency_runtime.core.evals.product_scenarios import ProductScenario
from agency_runtime.core.private_paths import private_temporary_directory
from agency_runtime.core.store.security import metadata_is_link_or_reparse_point

MAX_PRODUCT_FILES: Final[int] = 256
MAX_PRODUCT_FILE_BYTES: Final[int] = 512 * 1024
MAX_PRODUCT_TOTAL_BYTES: Final[int] = 4 * 1024 * 1024
MAX_PROBE_OUTPUT_CHARS: Final[int] = 64 * 1024
PRODUCT_VALIDATION_SCHEMA_VERSION: Final[int] = 1

_SAFE_ENV_NAMES = frozenset(
    {
        "COMSPEC",
        "LANG",
        "LC_ALL",
        "PATH",
        "PATHEXT",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "WINDIR",
    }
)
_WINDOWS_ABSOLUTE = re.compile(r"(?i)(?:[a-z]:[\\/]|\\\\[a-z0-9._-]+[\\/])")
_PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


@dataclass(frozen=True, slots=True)
class ProductArtifact:
    path: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ProductCheck:
    check_id: str
    category: str
    passed: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class ProductValidationReport:
    scenario_id: str
    workspace_digest: str
    artifacts: tuple[ProductArtifact, ...]
    checks: tuple[ProductCheck, ...]

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(item.passed for item in self.checks)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PRODUCT_VALIDATION_SCHEMA_VERSION,
            "scenario_id": self.scenario_id,
            "workspace_digest": self.workspace_digest,
            "artifacts": [asdict(item) for item in self.artifacts],
            "checks": [asdict(item) for item in self.checks],
            "passed": self.passed,
        }


ProcessRunner = Callable[..., BoundedProcessResult]


def _safe_workspace(root: Path) -> Path:
    try:
        resolved = root.expanduser().resolve(strict=True)
        metadata = os.lstat(resolved)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError("product workspace is unavailable") from exc
    if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("product workspace must be a real directory")
    return resolved


def _relative_file(root: Path, candidate: Path) -> tuple[str, os.stat_result]:
    try:
        relative = candidate.relative_to(root).as_posix()
        metadata = os.lstat(candidate)
    except (OSError, ValueError) as exc:
        raise ValueError("product artifact could not be inspected") from exc
    if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"product artifact must be a regular file: {relative}")
    if metadata.st_size > MAX_PRODUCT_FILE_BYTES:
        raise ValueError(f"product artifact exceeds its size limit: {relative}")
    return relative, metadata


def inventory_product_workspace(root: Path) -> tuple[tuple[ProductArtifact, ...], str]:
    """Inventory a bounded, link-free generated workspace without trusting its tests."""

    workspace = _safe_workspace(root)
    artifacts: list[ProductArtifact] = []
    total = 0
    for candidate in sorted(workspace.rglob("*")):
        try:
            metadata = os.lstat(candidate)
        except OSError as exc:
            raise ValueError("product workspace changed during inventory") from exc
        if metadata_is_link_or_reparse_point(metadata):
            raise ValueError("product workspace contains a link or reparse point")
        if stat.S_ISDIR(metadata.st_mode):
            continue
        relative, metadata = _relative_file(workspace, candidate)
        if len(artifacts) >= MAX_PRODUCT_FILES:
            raise ValueError("product workspace exceeds the file-count limit")
        total += int(metadata.st_size)
        if total > MAX_PRODUCT_TOTAL_BYTES:
            raise ValueError("product workspace exceeds the total-size limit")
        payload = read_bounded_regular_file(
            candidate,
            limit=MAX_PRODUCT_FILE_BYTES,
            label="product artifact",
        )
        artifacts.append(
            ProductArtifact(relative, len(payload), hashlib.sha256(payload).hexdigest())
        )
    digest_payload = json.dumps(
        [asdict(item) for item in artifacts],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return tuple(artifacts), "sha256:" + hashlib.sha256(digest_payload).hexdigest()


def _artifact_map(artifacts: Sequence[ProductArtifact]) -> dict[str, ProductArtifact]:
    return {item.path: item for item in artifacts}


def _required_files(
    scenario: ProductScenario,
    artifacts: Sequence[ProductArtifact],
) -> tuple[bool, str]:
    by_path = _artifact_map(artifacts)
    missing = [item.path for item in scenario.files if item.path not in by_path]
    empty = [
        item.path
        for item in scenario.files
        if by_path.get(item.path, None) and not by_path[item.path].size
    ]
    if missing or empty:
        parts = []
        if missing:
            parts.append("missing=" + ",".join(missing))
        if empty:
            parts.append("empty=" + ",".join(empty))
        return False, "; ".join(parts)
    return True, f"required_files={len(scenario.files)}"


def _read_text(root: Path, relative: str) -> str:
    payload = read_bounded_regular_file(
        root / relative,
        limit=MAX_PRODUCT_FILE_BYTES,
        label="product text artifact",
    )
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"product artifact must be UTF-8: {relative}") from exc


def _content_safety(root: Path, artifacts: Sequence[ProductArtifact]) -> tuple[bool, str]:
    findings: list[str] = []
    for artifact in artifacts:
        if not artifact.path.endswith((".json", ".md", ".py", ".ps1", ".sh", ".ts", ".html")):
            continue
        text = _read_text(root, artifact.path)
        if "\x00" in text:
            findings.append(f"nul:{artifact.path}")
        if _PRIVATE_KEY.search(text):
            findings.append(f"private-key:{artifact.path}")
    return (not findings, "clean" if not findings else ",".join(findings))


def _probe_environment(temporary: Path) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in _SAFE_ENV_NAMES and isinstance(value, str)
    }
    private = str(temporary)
    environment.update(
        {
            "HOME": private,
            "USERPROFILE": private,
            "TEMP": private,
            "TMP": private,
            "TMPDIR": private,
            "NO_COLOR": "1",
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "ALL_PROXY": "http://127.0.0.1:9",
            "NO_PROXY": "",
        }
    )
    return environment


def _run(
    runner: ProcessRunner,
    argv: Sequence[str],
    *,
    root: Path,
    temporary: Path,
    timeout: float = 30.0,
) -> BoundedProcessResult:
    if not math.isfinite(timeout) or timeout <= 0 or timeout > 120:
        raise ValueError("product probe timeout is invalid")
    return runner(
        list(argv),
        timeout=timeout,
        cwd=str(root),
        env=_probe_environment(temporary),
        max_output_chars=MAX_PROBE_OUTPUT_CHARS,
    )


def _successful(result: BoundedProcessResult) -> bool:
    return bool(
        not result.timed_out
        and result.returncode == 0
        and not result.stdout_truncated
        and not result.stderr_truncated
    )


def _json_stdout(result: BoundedProcessResult) -> Any:
    if not _successful(result):
        return None
    try:
        return safe_load_bounded_json(
            result.stdout,
            maximum_bytes=MAX_PROBE_OUTPUT_CHARS,
            maximum_depth=16,
            maximum_nodes=2_000,
        )
    except (TypeError, ValueError):
        return None


def _task(value: Any, *, title: str, completed: bool) -> bool:
    return bool(
        isinstance(value, Mapping)
        and isinstance(value.get("id"), (str, int))
        and value.get("title") == title
        and value.get("completed") is completed
    )


def _list_contains(value: Any, *, title: str, completed: bool) -> bool:
    rows = value.get("tasks") if isinstance(value, Mapping) else value
    return bool(
        isinstance(rows, list)
        and any(_task(item, title=title, completed=completed) for item in rows)
    )


def _cli_checks(
    *,
    root: Path,
    temporary: Path,
    prefix: Sequence[str],
    test_argv: Sequence[str],
    ids: tuple[str, str, str],
    runner: ProcessRunner,
) -> tuple[ProductCheck, ProductCheck, ProductCheck]:
    data_path = temporary / "tasks.json"
    title = "independent-eval-task"
    add = _run(
        runner,
        [*prefix, "--data", str(data_path), "add", "--title", title],
        root=root,
        temporary=temporary,
    )
    added = _json_stdout(add)
    task_id = (
        str(added.get("id")) if isinstance(added, Mapping) and added.get("id") is not None else ""
    )
    listed = _run(
        runner,
        [*prefix, "--data", str(data_path), "list"],
        root=root,
        temporary=temporary,
    )
    completed = (
        _run(
            runner,
            [*prefix, "--data", str(data_path), "complete", task_id],
            root=root,
            temporary=temporary,
        )
        if task_id
        else BoundedProcessResult(1, "", "missing id")
    )
    completed_value = _json_stdout(completed)
    workflow = bool(
        _task(added, title=title, completed=False)
        and _list_contains(_json_stdout(listed), title=title, completed=False)
        and _task(completed_value, title=title, completed=True)
    )
    invalid = _run(
        runner,
        [*prefix, "--data", str(data_path), "complete", "missing-task-id"],
        root=root,
        temporary=temporary,
    )
    try:
        persisted = safe_load_bounded_json(
            data_path.read_bytes(),
            maximum_bytes=MAX_PRODUCT_FILE_BYTES,
            maximum_depth=16,
            maximum_nodes=2_000,
        )
    except (OSError, TypeError, ValueError):
        persisted = None
    errors_safe = bool(
        not invalid.timed_out and invalid.returncode != 0 and isinstance(persisted, (list, dict))
    )
    tests = _run(runner, test_argv, root=root, temporary=temporary, timeout=60.0)
    return (
        ProductCheck(ids[0], "core-workflow", workflow, "hidden add/list/complete probe"),
        ProductCheck(ids[1], "error-recovery", errors_safe, "hidden invalid-id probe"),
        ProductCheck(ids[2], "tests", _successful(tests), "project test command"),
    )


def _docs_check(root: Path, check_id: str, commands: Sequence[str]) -> ProductCheck:
    try:
        readme = _read_text(root, "README.md").casefold()
    except ValueError:
        return ProductCheck(check_id, "documentation", False, "README is missing or invalid")
    missing = [command for command in commands if command.casefold() not in readme]
    return ProductCheck(
        check_id,
        "documentation",
        not missing,
        "commands documented" if not missing else "missing=" + ",".join(missing),
    )


def _python_cli(
    root: Path,
    temporary: Path,
    runner: ProcessRunner,
) -> tuple[ProductCheck, ...]:
    python = _python_runtime()
    if not python:
        return tuple(
            ProductCheck(item.check_id, item.category, False, "Python runtime unavailable")
            for item in (
                ProductCheck("python-cli-workflow", "core-workflow", False, ""),
                ProductCheck("python-cli-errors", "error-recovery", False, ""),
                ProductCheck("python-cli-tests", "tests", False, ""),
                ProductCheck("python-cli-docs", "documentation", False, ""),
            )
        )
    checks = _cli_checks(
        root=root,
        temporary=temporary,
        prefix=(python, "app.py"),
        test_argv=(python, "-m", "unittest", "discover", "-s", "tests", "-v"),
        ids=("python-cli-workflow", "python-cli-errors", "python-cli-tests"),
        runner=runner,
    )
    return (*checks, _docs_check(root, "python-cli-docs", ("add", "list", "complete")))


def _python_runtime() -> str | None:
    """Prefer the base interpreter so an editable workspace venv is never executed."""

    base = str(getattr(sys, "_base_executable", "") or "").strip()
    if base and Path(base).is_file():
        return base
    return shutil.which("python3") or shutil.which("python")


def _typescript_cli(
    root: Path,
    temporary: Path,
    runner: ProcessRunner,
) -> tuple[ProductCheck, ...]:
    node = shutil.which("node")
    if not node:
        failed = tuple(
            ProductCheck(check_id, category, False, "Node.js executable unavailable")
            for check_id, category in (
                ("typescript-cli-workflow", "core-workflow"),
                ("typescript-cli-errors", "error-recovery"),
                ("typescript-cli-tests", "tests"),
            )
        )
        return (*failed, _typescript_portability(root))
    prefix = (node, "--experimental-strip-types", "src/app.ts")
    checks = _cli_checks(
        root=root,
        temporary=temporary,
        prefix=prefix,
        test_argv=(node, "--experimental-strip-types", "--test", "test/app.test.ts"),
        ids=("typescript-cli-workflow", "typescript-cli-errors", "typescript-cli-tests"),
        runner=runner,
    )
    return (*checks, _typescript_portability(root))


def _typescript_portability(root: Path) -> ProductCheck:
    try:
        package = safe_load_bounded_json(
            (root / "package.json").read_bytes(),
            maximum_bytes=MAX_PRODUCT_FILE_BYTES,
            maximum_depth=16,
            maximum_nodes=1_000,
        )
        tsconfig = safe_load_bounded_json(
            (root / "tsconfig.json").read_bytes(),
            maximum_bytes=MAX_PRODUCT_FILE_BYTES,
            maximum_depth=16,
            maximum_nodes=1_000,
        )
        source = _read_text(root, "src/app.ts")
    except (OSError, TypeError, ValueError):
        return ProductCheck(
            "typescript-cli-portable", "portability", False, "configuration is invalid"
        )
    dependencies = {}
    if isinstance(package, Mapping):
        dependencies = {
            **(
                package.get("dependencies")
                if isinstance(package.get("dependencies"), Mapping)
                else {}
            ),
            **(
                package.get("devDependencies")
                if isinstance(package.get("devDependencies"), Mapping)
                else {}
            ),
        }
    compiler = tsconfig.get("compilerOptions") if isinstance(tsconfig, Mapping) else None
    portable = bool(
        isinstance(package, Mapping)
        and not dependencies
        and isinstance(compiler, Mapping)
        and compiler.get("strict") is True
        and not _WINDOWS_ABSOLUTE.search(source)
    )
    return ProductCheck(
        "typescript-cli-portable",
        "portability",
        portable,
        "network-free strict config and no absolute Windows path",
    )


_DYNAMIC_VALIDATORS: Final[
    dict[str, Callable[[Path, Path, ProcessRunner], tuple[ProductCheck, ...]]]
] = {
    "python-cli-service": _python_cli,
    "typescript-node-application": _typescript_cli,
}


def _validator_for(
    scenario_id: str,
) -> Callable[[Path, Path, ProcessRunner], tuple[ProductCheck, ...]] | None:
    validator = _DYNAMIC_VALIDATORS.get(scenario_id)
    if validator is not None:
        return validator
    from agency_runtime.core.evals.product_validators_extended import EXTENDED_VALIDATORS

    return EXTENDED_VALIDATORS.get(scenario_id)


def validate_product_workspace(
    root: Path,
    scenario: ProductScenario,
    *,
    runner: ProcessRunner = run_bounded_process,
) -> ProductValidationReport:
    """Run hidden validation and require one result for every scenario check."""

    workspace = _safe_workspace(root)
    artifacts, digest = inventory_product_workspace(workspace)
    files_ok, file_evidence = _required_files(scenario, artifacts)
    content_ok, content_evidence = _content_safety(workspace, artifacts)
    validator = _validator_for(scenario.scenario_id)
    if validator is None:
        checks = tuple(
            ProductCheck(
                item.check_id,
                item.category,
                False,
                "independent executable validator is not implemented",
            )
            for item in scenario.acceptance
        )
    elif not files_ok or not content_ok:
        evidence = "; ".join((file_evidence, content_evidence))
        checks = tuple(
            ProductCheck(item.check_id, item.category, False, evidence)
            for item in scenario.acceptance
        )
    else:
        with private_temporary_directory(prefix="product-probe") as temporary:
            checks = validator(workspace, temporary, runner)
    expected = [item.check_id for item in scenario.acceptance]
    actual = [item.check_id for item in checks]
    if actual != expected:
        raise RuntimeError("product validator results do not match the scenario contract")
    return ProductValidationReport(scenario.scenario_id, digest, artifacts, checks)


__all__ = [
    "MAX_PRODUCT_FILES",
    "MAX_PRODUCT_FILE_BYTES",
    "MAX_PRODUCT_TOTAL_BYTES",
    "PRODUCT_VALIDATION_SCHEMA_VERSION",
    "ProductArtifact",
    "ProductCheck",
    "ProductValidationReport",
    "inventory_product_workspace",
    "validate_product_workspace",
]
