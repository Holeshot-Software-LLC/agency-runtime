"""Adversarial integrity checks for bounded work-unit planning."""

from __future__ import annotations

import pytest

from agency_runtime.core.codex_native_plan_scope import build_codex_native_plan_scope
from agency_runtime.core.native_child_activation import build_native_child_mutation_scope
from agency_runtime.core.selector.delegation_detection import (
    _imperative_units,
    detect_work_units,
)
from agency_runtime.core.unit_assignment import (
    _likely_resources,
    _looks_like_resource,
    _plan_hash,
    _resource_contention_plan,
    native_child_activation_contract,
    work_unit_id_from_text,
)


def _routing(*units: str) -> dict[str, object]:

    unit_ids = [work_unit_id_from_text(unit) for unit in units]
    return {
        "selected_ids": ["code-reviewer"],
        "unit_assignment_agents": [
            {
                "slug": "code-reviewer",
                "primary_work_unit_ids": unit_ids[:1],
                "matched_work_unit_ids": unit_ids,
            }
        ],
        "work_units": {
            "delegate": True,
            "count": len(units),
            "confidence": "high",
            "source": "integrity-test",
            "units": list(units),
        },
    }


def test_duplicate_imperative_spans_do_not_create_duplicate_units() -> None:
    assert _imperative_units("fix x; fix x") == ["fix x"]


def test_candidate_scan_overflow_is_explicitly_lower_bounded() -> None:
    message = "\n".join(f"{index + 1}. Implement item {index}" for index in range(65))

    detected = detect_work_units(message)

    assert detected["truncated"] is True
    assert detected["overflow_count"] >= 1
    assert detected["overflow_count_exact"] is False
    assert detected["delegate"] is False


def test_resource_parser_stops_at_prose_and_normalizes_equivalent_paths() -> None:
    assert _likely_resources("Update src/auth.py and write tests/test_auth.py") == [
        "src/auth.py",
        "tests/test_auth.py",
    ]
    assert _likely_resources("Update ./src/auth.py") == ["src/auth.py"]
    assert _likely_resources(r"Write src\auth.py") == ["src/auth.py"]
    assert _likely_resources('Update "C:\\Program Files\\Agency\\config.json"') == [
        "C:/Program Files/Agency/config.json"
    ]
    assert _likely_resources("Update Src/Auth.py") == ["Src/Auth.py"]
    assert _likely_resources("Update Src/Auth.py and src/auth.py") == [
        "Src/Auth.py",
        "src/auth.py",
    ]
    assert not _looks_like_resource("")
    assert not _looks_like_resource("https://example.test/source.py")
    assert _likely_resources("Update src/a.py and src\\a.py") == ["src/a.py"]
    assert _likely_resources(
        "Create `.agency-runtime-workspace-write-proof`, then update `app.py`, "
        "`tests/test_app.py`, and `README.md`."
    ) == [
        ".agency-runtime-workspace-write-proof",
        "app.py",
        "tests/test_app.py",
        "README.md",
    ]
    many = " ".join(f"src/component-{index}.py" for index in range(12))
    # AR-232 removed the MAX_PLAN_LIST_ITEMS cap; all 12 resources are preserved.
    assert len(_likely_resources(many)) == 12


def test_required_files_survive_before_inferred_resources() -> None:
    """AR-216: explicit required files are preserved before inferred tokens."""

    unit = (
        "Build the dashboard. Endpoints: GET /health, POST /api/tasks, "
        "list/create tasks, /api/tasks/{id}/complete. "
        "Edit web/app.ts and README.md."
    )
    result = _likely_resources(unit, required_files=("web/app.ts", "README.md"))
    # Required files come first, regardless of prose noise.
    assert result[0] == "web/app.ts"
    assert result[1] == "README.md"
    # API routes and prose actions are NOT admitted as resources.
    assert "/health" not in result
    assert "/api/tasks" not in result
    assert "list/create" not in result


def test_api_routes_and_prose_actions_are_not_resources() -> None:
    """AR-216: HTTP routes, verbs, and prose actions are rejected as paths."""

    assert not _looks_like_resource("/health")
    assert not _looks_like_resource("/api/tasks")
    assert not _looks_like_resource("/api/tasks/{id}/complete")
    assert not _looks_like_resource("GET")
    assert not _looks_like_resource("POST")
    assert not _looks_like_resource("list/create")
    assert not _looks_like_resource("add/remove")
    # Real files are still accepted.
    assert _looks_like_resource("web/app.ts")
    assert _looks_like_resource("README.md")
    assert _looks_like_resource("src/app.ts")
    assert _looks_like_resource("tests/test_app.py")


def test_all_six_product_scenarios_have_valid_resource_scopes() -> None:
    """AR-216: every product scenario's required files are valid resources."""

    from agency_runtime.core.evals.product_scenarios import PRODUCT_SCENARIOS

    for scenario in PRODUCT_SCENARIOS:
        for file_contract in scenario.files:
            assert _looks_like_resource(file_contract.path), (
                f"{scenario.scenario_id}: {file_contract.path} is not a valid resource"
            )
        # Required files preserved via _likely_resources with required_files kwarg.
        paths = tuple(f.path for f in scenario.files)
        result = _likely_resources("Build it.", required_files=paths)
        assert result[: len(paths)] == list(paths), (
            f"{scenario.scenario_id}: required files not preserved in order"
        )


def test_native_child_activation_rehydrates_exact_scope_and_content_free_evidence() -> None:
    goal = "Update Src/Auth.py and verify the change"
    resource = "Src/Auth.py"
    contract = native_child_activation_contract(
        goal,
        mutation_scope="workspace_write",
        resource_hashes=[_plan_hash(resource)],
        required_evidence=["targeted-tests", "Evidence proves the requested behavior"],
    )

    assert contract["mutation_mode"] == "workspace_write"
    assert contract["mutation_path_prefixes"] == [resource]
    assert contract["evidence_requirements"][:3] == [
        "delegation-execution",
        "specialist-load",
        "targeted-tests",
    ]
    assert contract["evidence_requirements"][3].startswith("evidence-")
    with pytest.raises(ValueError, match="resources do not match"):
        native_child_activation_contract(
            goal,
            mutation_scope="workspace_write",
            resource_hashes=["0" * 64],
            required_evidence=[],
        )
    with pytest.raises(ValueError, match="external writes"):
        native_child_activation_contract(
            goal,
            mutation_scope="external_write",
            resource_hashes=[_plan_hash(resource)],
            required_evidence=[],
        )


def test_workspace_write_prose_resources_widen_to_the_whole_workspace() -> None:
    """Absolute/home paths and abbreviation noise in prose goals must not
    produce an unissuable workspace_write scope (they are not
    repository-relative POSIX prefixes)."""

    goal = (
        "Request: In C:\\Workspaces\\Example: fix the worker "
        "(agency_runtime/server/dashboard_service.py, e.g. "
        "~/.agency-runtime/run/dashboard-startup-error.json). "
        "Work unit 2: implementation with mutation_scope=workspace_write."
    )
    resources = _likely_resources(goal)
    contract = native_child_activation_contract(
        goal,
        mutation_scope="workspace_write",
        resource_hashes=[_plan_hash(item) for item in resources],
        required_evidence=["delegation-execution"],
    )
    assert contract["mutation_path_prefixes"] == ["."]
    build_native_child_mutation_scope(
        mode=contract["mutation_mode"],
        path_prefixes=contract["mutation_path_prefixes"],
    )


def test_opaque_codex_scope_preserves_the_exact_planned_path() -> None:
    scope = build_codex_native_plan_scope(
        work_unit_id="unit-0123456789",
        specialist_slug="implementation-engineer",
        specialist_version="1.0.0",
        specialist_prompt_hash="f" * 64,
        goal_hash=_plan_hash("Implement the exact product unit."),
        mutation_mode="workspace_write",
        resource_hashes=[_plan_hash("Src/Product.py")],
        mutation_path_prefixes=["Src/Product.py"],
        evidence_contract_id="agency-native-child-plan-v1",
        evidence_requirements=[
            "delegation-execution",
            "specialist-load",
            "targeted-tests",
        ],
    )

    assert scope.mutation_scope.mode == "workspace_write"
    assert scope.mutation_scope.path_prefixes == ("Src/Product.py",)
    with pytest.raises(ValueError, match="planned resource hashes"):
        build_codex_native_plan_scope(
            work_unit_id="unit-0123456789",
            specialist_slug="implementation-engineer",
            specialist_version="1.0.0",
            specialist_prompt_hash="f" * 64,
            goal_hash=_plan_hash("Implement the exact product unit."),
            mutation_mode="workspace_write",
            resource_hashes=[_plan_hash("Src/Product.py")],
            mutation_path_prefixes=["."],
            evidence_contract_id="agency-native-child-plan-v1",
            evidence_requirements=["delegation-execution", "specialist-load"],
        )


def test_resource_contention_uses_folded_keys_without_rewriting_paths() -> None:
    candidates = (
        {
            "work_unit_id": "unit-upper",
            "mutation_scope": "workspace_write",
            "resources": ["Src/Auth.py"],
        },
        {
            "work_unit_id": "unit-lower",
            "mutation_scope": "workspace_write",
            "resources": ["src/auth.py"],
        },
    )

    dependencies, contended, unknown_mutation = _resource_contention_plan(candidates)

    assert candidates[0]["resources"] == ["Src/Auth.py"]
    assert candidates[1]["resources"] == ["src/auth.py"]
    assert dependencies == {"unit-upper": [], "unit-lower": ["unit-upper"]}
    assert contended == {"unit-upper", "unit-lower"}
    assert unknown_mutation is False
