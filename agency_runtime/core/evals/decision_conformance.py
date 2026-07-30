"""Curated mutation proof for Agency's load-bearing runtime decisions.

The evaluator never mutates the requested checkout. It copies the minimum
repository inputs into an owner-private disposable directory, proves the named
tests are green there, and then creates a fresh copy for each exact mutation.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from agency_runtime.core.filesystem_trust import metadata_is_link_or_reparse_point
from agency_runtime.core.private_paths import private_temporary_directory
from agency_runtime.core.process_environment import least_privilege_subprocess_environment

SCHEMA: Final[str] = "agency-runtime.decision-conformance"
VERSION: Final[int] = 1
DEFAULT_TIMEOUT_SECONDS: Final[float] = 90.0
_COPY_SUPPORT = (
    "conftest.py",
    "runtime_support.py",
    "test_product_validation.py",
    "__init__.py",
)


@dataclass(frozen=True, slots=True)
class DecisionMutation:
    mutation_id: str
    invariant: str
    source_path: str
    before: str
    after: str
    test_node: str


@dataclass(frozen=True, slots=True)
class _PytestRun:
    exit_code: int | None
    failed_nodes: tuple[str, ...]
    duration_ms: int
    timed_out: bool = False


MUTATIONS: Final[tuple[DecisionMutation, ...]] = (
    DecisionMutation(
        mutation_id="configured-provider-bypasses-inference",
        invariant="A configured provider always owns online planning and specialist selection.",
        source_path="agency_runtime/core/workforce/inference.py",
        before="    if not _inference_declared(config):",
        after="    if _inference_declared(config):",
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_balanced_mode_always_uses_inference_for_planning_and_selection"
        ),
    ),
    DecisionMutation(
        mutation_id="online-role-anchor-reorders-inference",
        invariant="Online deterministic recall cannot reorder the inference ranking.",
        source_path="agency_runtime/core/workforce/inference.py",
        before="""        ranked = _calibrated_rankings(
            scores,
            minimum_margin=config.workforce.min_margin,
        )""",
        after="""        ranked = _calibrated_rankings(
            scores,
            minimum_margin=config.workforce.min_margin,
        )
        anchors = tuple(
            agent_id for agent_id in _role_anchors(expected_unit) if agent_id in scores
        )
        if anchors:
            anchor_ids = frozenset(anchors)
            ranked = (
                *((agent_id, 1.0) for agent_id in anchors),
                *((agent_id, min(score, 0.99)) for agent_id, score in ranked if agent_id not in anchor_ids),
            )""",
        test_node=(
            "tests/test_workforce_selection_safety.py::"
            "test_online_inference_ranking_is_not_reordered_by_a_role_anchor"
        ),
    ),
    DecisionMutation(
        mutation_id="implicit-staffing-failure-becomes-hiring-gap",
        invariant=(
            "An online staff decision without a safe team is repaired by inference rather "
            "than relabeled as a contractor gap."
        ),
        source_path="agency_runtime/core/workforce/inference.py",
        before="""        if decision == "staff" and not proposal_row.selected:
            failures.append(_NominationFailure(unit.unit_id, "staff_without_safe_team"))""",
        after="""        if decision == "staff" and not proposal_row.selected:
            continue""",
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_staff_decision_without_safe_team_gets_one_bounded_inference_repair"
        ),
    ),
    DecisionMutation(
        mutation_id="recruiter-validation-drops-later-unit-failures",
        invariant=(
            "One bounded recruiter repair receives every invalid planned unit, not only the first."
        ),
        source_path="agency_runtime/core/workforce/inference.py",
        before="""    if failures:
        raise _NominationValidationError(failures)


@dataclass(slots=True)
class _NominationSemantics:""",
        after="""    if failures:
        raise _NominationValidationError(failures[:1])


@dataclass(slots=True)
class _NominationSemantics:""",
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_recruiter_repair_receives_every_invalid_unit_and_preserves_valid_rows"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-falls-back-to-legacy-activity-summary",
        invariant=(
            "Codex Agency product trials consume the exact activation snapshot for the "
            "executed prompt hash."
        ),
        source_path="agency_runtime/core/evals/product_host.py",
        before="""        if normalized_host == "codex" and normalized_mode == "agency":
            evidence = store.get_canary_activation_snapshot(
                host=normalized_host,
                query_hash=executed_prompt_hash.removeprefix("sha256:"),
            )""",
        after="""        if normalized_host == "codex" and normalized_mode == "agency":
            evidence = store.recent_runtime_activity(limit=500)""",
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_agency_product_host_consumes_the_exact_activation_snapshot"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-restores-ephemeral-parent",
        invariant=(
            "Ordinary Codex product trials persist the parent turn required by native "
            "multi-agent delegation."
        ),
        source_path="agency_runtime/core/evals/product_host.py",
        before="""    "never",
    "--ignore-rules",""",
        after="""    "never",
    "--ephemeral",
    "--ignore-rules",""",
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_backend_persists_parent_without_single_child_rollout_constraint"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-disables-multi-agent-v2",
        invariant="Ordinary Codex product trials explicitly enable native multi-agent V2.",
        source_path="agency_runtime/core/evals/product_host.py",
        before='    "multi_agent_v2",',
        after='    "multi_agent_v1",',
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_backend_persists_parent_without_single_child_rollout_constraint"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-disables-agents",
        invariant="Ordinary Codex product trials explicitly enable the agents capability.",
        source_path="agency_runtime/core/evals/product_host.py",
        before='    "agents.enabled=true",',
        after='    "agents.enabled=false",',
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_backend_persists_parent_without_single_child_rollout_constraint"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-allows-store-bootstrap",
        invariant=(
            "Ordinary Codex product trials require the exact pre-existing Agency evidence store."
        ),
        source_path="agency_runtime/core/evals/product_host.py",
        before="        require_existing_store=True,",
        after="        require_existing_store=False,",
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_backend_persists_parent_without_single_child_rollout_constraint"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-drops-hook-start-evidence",
        invariant=("Agency-mode product trials capture content-free hook stage diagnostics."),
        source_path="agency_runtime/core/evals/product_host.py",
        before="        hook_event_diagnostics=master_enabled,",
        after="        hook_event_diagnostics=False,",
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_backend_persists_parent_without_single_child_rollout_constraint"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-delegation-inherits-parent-history",
        invariant=(
            "Codex specialist launches exclude parent history while receiving the exact "
            "hook-injected specialist context."
        ),
        source_path="agency_runtime/core/specialist_context.py",
        before=('                "set `fork_turns` to `none` and set `task_name` to that row\'s "'),
        after='                "set `task_name` to that row\'s "',
        test_node=(
            "tests/test_unit_aware_delegation.py::"
            "test_isolated_native_hook_receives_exact_unit_agent_plan[codex]"
        ),
    ),
    DecisionMutation(
        mutation_id="product-grading-accepts-missing-write-proof",
        invariant=(
            "Product grading fails closed unless effective workspace-write evidence is true."
        ),
        source_path="agency_runtime/core/evals/product_one_shot.py",
        before="        if execution.workspace_write_proven is not True",
        after="        if execution.workspace_write_proven is False",
        test_node=(
            "tests/test_product_one_shot.py::"
            "test_unproven_workspace_write_stops_before_product_grading[None]"
        ),
    ),
    DecisionMutation(
        mutation_id="default-fast-budget-removes-recruiter-repair",
        invariant=(
            "The default fast budget funds planning, recruitment, and one bounded semantic repair."
        ),
        source_path="agency_runtime/core/config.py",
        before="    fast_call_budget: int = 3",
        after="    fast_call_budget: int = 2",
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_default_fast_mode_funds_recruiter_contract_repair_after_planning"
        ),
    ),
    DecisionMutation(
        mutation_id="declined-hiring-analysis-consumes-hire-budget",
        invariant=(
            "A declined hiring analysis does not consume the task's workforce-change "
            "allowance or starve a later declared gap."
        ),
        source_path="agency_runtime/core/selector/pipeline.py",
        before=(
            "        if not hireable or workforce_changes >= config.workforce.max_hires_per_task:"
        ),
        after=(
            "        if not hireable or len(attempted_units) >= "
            "config.workforce.max_hires_per_task:"
        ),
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_route_hiring_caps_and_daily_budget_are_cumulative_and_truthful"
        ),
    ),
    DecisionMutation(
        mutation_id="causing-unit-binding-overflows-employment-schema",
        invariant="Causing-unit facts stay inside the employment contract item bound.",
        source_path="agency_runtime/core/workforce/hiring.py",
        before="""        artifacts_produced=tuple(dict.fromkeys((unit.artifact_kind, *contract.artifacts_produced)))[
            :MAX_ITEMS
        ],""",
        after="""        artifacts_produced=tuple(dict.fromkeys((unit.artifact_kind, *contract.artifacts_produced)))[
            : MAX_ITEMS + 1
        ],""",
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_hire_compiles_schema_maximum_lists_into_bounded_workforce_contract"
        ),
    ),
    DecisionMutation(
        mutation_id="contractor-outcomes-overflow-workforce-schema",
        invariant="Employment outcomes are capped to the smaller workforce projection.",
        source_path="agency_runtime/core/workforce/hiring.py",
        before="""    outcomes = tuple(dict.fromkeys((*contract.capabilities, *contract.outcomes_owned)))[
        :MAX_OUTCOMES
    ]""",
        after="""    outcomes = tuple(dict.fromkeys((*contract.capabilities, *contract.outcomes_owned)))[
        :MAX_ITEMS
    ]""",
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_hire_compiles_schema_maximum_lists_into_bounded_workforce_contract"
        ),
    ),
    DecisionMutation(
        mutation_id="amendment-target-identity-left-model-authored",
        invariant=(
            "An amendment revises the inference-selected existing worker instead of creating a "
            "second model-authored identity."
        ),
        source_path="agency_runtime/core/workforce/hiring.py",
        before="            contract = replace(contract, slug=existing.agent_id)",
        after="            contract = contract",
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_amendment_binds_model_extension_slug_to_inferred_target"
        ),
    ),
    DecisionMutation(
        mutation_id="amendment-outcomes-overflow-workforce-schema",
        invariant=(
            "An additive amendment preserves existing outcomes while respecting the smaller "
            "workforce projection bound."
        ),
        source_path="agency_runtime/core/workforce/hiring.py",
        before="""    agent["outcomes"] = _bounded_additive(
        existing.outcomes,
        agent["outcomes"],
        maximum=MAX_OUTCOMES,
    )""",
        after="""    agent["outcomes"] = list(
        dict.fromkeys((*existing.outcomes, *agent["outcomes"]))
    )""",
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_amendment_preserves_existing_values_inside_smaller_workforce_bounds"
        ),
    ),
    DecisionMutation(
        mutation_id="contractor-diagnostics-collapse",
        invariant="Post-parse contractor failures retain their content-free validation stage.",
        source_path="agency_runtime/core/workforce/hiring.py",
        before="        return failure(exc.reason_code)",
        after='        return failure("contract_invalid:candidate")',
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_hire_reports_content_free_employment_revalidation_stage"
        ),
    ),
)

PytestRunner = Callable[[Path, Sequence[str], str, float, Path], _PytestRun]


def _normalized_node(value: str) -> str:
    return value.strip().replace(chr(92), "/")


def _failed_nodes(output: str) -> tuple[str, ...]:
    nodes: list[str] = []
    for line in output.splitlines():
        if not line.startswith("FAILED "):
            continue
        node = _normalized_node(line.removeprefix("FAILED ").split(" - ", 1)[0])
        if node and node not in nodes:
            nodes.append(node)
    return tuple(nodes)


def _run_pytest(
    checkout: Path,
    test_nodes: Sequence[str],
    python_executable: str,
    timeout_seconds: float,
    source_root: Path,
) -> _PytestRun:
    scratch = checkout / ".decision-conformance"
    scratch.mkdir(parents=True, exist_ok=True)
    home = scratch / "home"
    temporary = scratch / "temp"
    bytecode = scratch / "bytecode"
    for directory in (home, temporary, bytecode):
        directory.mkdir(parents=True, exist_ok=True)
    environment = least_privilege_subprocess_environment(
        "decision-conformance",
        home_dir=home,
        current_directory=checkout,
        forbidden_roots=(source_root,),
        extra_env={
            "AGENCY_DECISION_CONFORMANCE": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONPATH": str(checkout),
            "PYTHONPYCACHEPREFIX": str(bytecode),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "TEMP": str(temporary),
            "TMP": str(temporary),
            "TMPDIR": str(temporary),
        },
    )
    command = [
        python_executable,
        "-m",
        "pytest",
        *test_nodes,
        "-q",
        "-W",
        "error",
        "--maxfail=1",
        "-p",
        "no:cacheprovider",
        f"--basetemp={temporary / 'pytest'}",
    ]
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=checkout,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _PytestRun(
            exit_code=None,
            failed_nodes=(),
            duration_ms=round((time.perf_counter() - started) * 1000),
            timed_out=True,
        )
    output = completed.stdout + chr(10) + completed.stderr
    return _PytestRun(
        exit_code=completed.returncode,
        failed_nodes=_failed_nodes(output),
        duration_ms=round((time.perf_counter() - started) * 1000),
    )


def _relative_file(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if not candidate.parts or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("decision-conformance paths must stay repository-relative")
    current = root
    try:
        for index, part in enumerate(candidate.parts):
            current /= part
            metadata = os.lstat(current)
            if metadata_is_link_or_reparse_point(metadata):
                raise ValueError(
                    "decision-conformance inputs must not cross a link or reparse point"
                )
            if index < len(candidate.parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
                raise ValueError("decision-conformance input parent must be a directory")
        resolved = current.resolve(strict=True)
    except OSError as exc:
        raise ValueError("decision-conformance input is unavailable") from exc
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ValueError("decision-conformance path escapes the repository") from None
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("decision-conformance inputs must be regular files")
    return resolved


def _regular_tree_files(root: Path) -> tuple[Path, ...]:
    """Inventory a real, link-free source tree before it is copied."""

    try:
        root_metadata = os.lstat(root)
    except OSError as exc:
        raise ValueError("decision-conformance source tree is unavailable") from exc
    if metadata_is_link_or_reparse_point(root_metadata) or not stat.S_ISDIR(root_metadata.st_mode):
        raise ValueError("decision-conformance source tree must be a real directory")
    files: list[Path] = []
    for current, directory_names, file_names in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        directory_names.sort()
        file_names.sort()
        current_path = Path(current)
        for name in directory_names:
            candidate = current_path / name
            try:
                metadata = os.lstat(candidate)
            except OSError as exc:
                raise ValueError("decision-conformance source tree changed") from exc
            if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode):
                raise ValueError(
                    "decision-conformance source tree contains a link or reparse point"
                )
        for name in file_names:
            candidate = current_path / name
            try:
                metadata = os.lstat(candidate)
            except OSError as exc:
                raise ValueError("decision-conformance source tree changed") from exc
            if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISREG(metadata.st_mode):
                raise ValueError(
                    "decision-conformance source tree contains a link or "
                    "reparse point or a non-regular file"
                )
            files.append(candidate)
    return tuple(files)


def _validate_repository(root: Path, mutations: Sequence[DecisionMutation]) -> Path:
    try:
        resolved = root.expanduser().resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError("decision-conformance repository is unavailable") from exc
    if not resolved.is_dir() or not (resolved / "pyproject.toml").is_file():
        raise ValueError("decision-conformance requires an Agency Runtime repository root")
    if not (resolved / "agency_runtime").is_dir() or not (resolved / "tests").is_dir():
        raise ValueError("decision-conformance repository inputs are incomplete")
    seen_ids: set[str] = set()
    for mutation in mutations:
        if not mutation.mutation_id or mutation.mutation_id in seen_ids:
            raise ValueError("decision-conformance mutation ids must be unique")
        seen_ids.add(mutation.mutation_id)
        _relative_file(resolved, mutation.source_path)
        test_path = mutation.test_node.split("::", 1)[0]
        if not test_path.startswith("tests/") or "::" not in mutation.test_node:
            raise ValueError("decision-conformance test nodes must name one test")
        _relative_file(resolved, test_path)
        if not mutation.before or mutation.before == mutation.after:
            raise ValueError("decision-conformance mutations require a real exact replacement")
    return resolved


def _copy_inputs(
    source_root: Path,
    destination: Path,
    mutations: Sequence[DecisionMutation],
) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copy2(source_root / "pyproject.toml", destination / "pyproject.toml")
    _regular_tree_files(source_root / "agency_runtime")
    shutil.copytree(
        source_root / "agency_runtime",
        destination / "agency_runtime",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    _regular_tree_files(destination / "agency_runtime")
    destination_tests = destination / "tests"
    destination_tests.mkdir()
    relative_tests = {mutation.test_node.split("::", 1)[0] for mutation in mutations}
    relative_tests.update(
        f"tests/{name}" for name in _COPY_SUPPORT if (source_root / "tests" / name).is_file()
    )
    for relative in sorted(relative_tests):
        source = _relative_file(source_root, relative)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _fingerprints(
    root: Path,
    mutations: Sequence[DecisionMutation],
) -> dict[str, str]:
    relative_files = {"pyproject.toml"}
    for source in _regular_tree_files(root / "agency_runtime"):
        if "__pycache__" not in source.parts and source.suffix not in {".pyc", ".pyo"}:
            relative_files.add(source.relative_to(root).as_posix())
    relative_files.update(mutation.test_node.split("::", 1)[0] for mutation in mutations)
    relative_files.update(
        f"tests/{name}" for name in _COPY_SUPPORT if (root / "tests" / name).is_file()
    )
    return {
        relative: hashlib.sha256(_relative_file(root, relative).read_bytes()).hexdigest()
        for relative in sorted(relative_files)
    }


def _mutation_result(
    mutation: DecisionMutation,
    checkout: Path,
    *,
    python_executable: str,
    timeout_seconds: float,
    source_root: Path,
    pytest_runner: PytestRunner,
) -> dict[str, Any]:
    target = _relative_file(checkout, mutation.source_path)
    text = target.read_text(encoding="utf-8")
    occurrences = text.count(mutation.before)
    if occurrences != 1:
        return {
            "mutation_id": mutation.mutation_id,
            "invariant": mutation.invariant,
            "source_path": mutation.source_path,
            "test_node": mutation.test_node,
            "status": "stale_anchor",
            "anchor_occurrences": occurrences,
            "exit_code": None,
            "failed_nodes": [],
            "duration_ms": 0,
        }
    target.write_text(text.replace(mutation.before, mutation.after, 1), encoding="utf-8")
    result = pytest_runner(
        checkout,
        (mutation.test_node,),
        python_executable,
        timeout_seconds,
        source_root,
    )
    expected = _normalized_node(mutation.test_node)
    failed = tuple(_normalized_node(node) for node in result.failed_nodes)
    expected_failed = len(failed) == 1 and (
        failed[0] == expected or failed[0].startswith(expected + "[")
    )
    if result.timed_out:
        status = "timeout"
    elif result.exit_code == 0:
        status = "survived"
    elif result.exit_code == 1 and expected_failed:
        status = "killed"
    else:
        status = "invalid_test_result"
    return {
        "mutation_id": mutation.mutation_id,
        "invariant": mutation.invariant,
        "source_path": mutation.source_path,
        "test_node": mutation.test_node,
        "status": status,
        "anchor_occurrences": occurrences,
        "exit_code": result.exit_code,
        "failed_nodes": list(failed),
        "duration_ms": result.duration_ms,
    }


def run_decision_conformance_eval(
    repository: str | Path = ".",
    *,
    mutations: Sequence[DecisionMutation] = MUTATIONS,
    python_executable: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    pytest_runner: PytestRunner = _run_pytest,
) -> dict[str, Any]:
    """Prove a green baseline and kill every curated mutation in private copies."""

    if not mutations:
        raise ValueError("decision-conformance requires at least one mutation")
    if not 1.0 <= float(timeout_seconds) <= 300.0:
        raise ValueError("decision-conformance timeout must be from 1 through 300 seconds")
    source_root = _validate_repository(Path(repository), mutations)
    interpreter = str(Path(python_executable or sys.executable).resolve(strict=True))
    before = _fingerprints(source_root, mutations)
    baseline_nodes = tuple(dict.fromkeys(mutation.test_node for mutation in mutations))
    mutation_results: list[dict[str, Any]] = []

    with private_temporary_directory(prefix="decision-conformance") as temporary:
        baseline_copy = temporary / "baseline"
        _copy_inputs(source_root, baseline_copy, mutations)
        baseline_run = pytest_runner(
            baseline_copy,
            baseline_nodes,
            interpreter,
            float(timeout_seconds),
            source_root,
        )
        baseline_passed = baseline_run.exit_code == 0 and not baseline_run.timed_out
        if baseline_passed:
            for index, mutation in enumerate(mutations):
                mutation_copy = temporary / f"mutation-{index:02d}"
                _copy_inputs(source_root, mutation_copy, mutations)
                mutation_results.append(
                    _mutation_result(
                        mutation,
                        mutation_copy,
                        python_executable=interpreter,
                        timeout_seconds=float(timeout_seconds),
                        source_root=source_root,
                        pytest_runner=pytest_runner,
                    )
                )

    after = _fingerprints(source_root, mutations)
    source_unchanged = before == after
    killed = sum(item["status"] == "killed" for item in mutation_results)
    passed = (
        baseline_passed
        and source_unchanged
        and len(mutation_results) == len(mutations)
        and killed == len(mutations)
    )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "passed": passed,
        "status": "passed" if passed else "failed",
        "repository": str(source_root),
        "source_unchanged": source_unchanged,
        "source_scope": ("pyproject.toml, agency_runtime regular files, and selected test inputs"),
        "baseline": {
            "status": (
                "timeout"
                if baseline_run.timed_out
                else "passed"
                if baseline_run.exit_code == 0
                else "failed"
            ),
            "exit_code": baseline_run.exit_code,
            "failed_nodes": list(baseline_run.failed_nodes),
            "test_nodes": list(baseline_nodes),
            "duration_ms": baseline_run.duration_ms,
        },
        "counts": {
            "mutations": len(mutations),
            "killed": killed,
            "survived": sum(item["status"] == "survived" for item in mutation_results),
            "invalid": sum(
                item["status"] not in {"killed", "survived"} for item in mutation_results
            ),
        },
        "mutations": mutation_results,
        "evidence_boundary": (
            "Curated decision sensitivity only; no coverage, superiority, "
            "or exhaustive mutation claim."
        ),
    }


__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "MUTATIONS",
    "SCHEMA",
    "VERSION",
    "DecisionMutation",
    "run_decision_conformance_eval",
]
