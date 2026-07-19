"""Adversarial integrity checks for bounded work-unit planning."""

from __future__ import annotations

from copy import deepcopy

import pytest

from agency_runtime.core.selector.delegation_detection import (
    _imperative_units,
    detect_work_units,
)
from agency_runtime.core.unit_assignment import (
    MAX_SUGGESTED_WORK_UNITS,
    MAX_WORK_UNIT_PREVIEW_CHARS,
    _delegated_work_units,
    _likely_resources,
    _looks_like_resource,
    _plan_hash,
    build_unit_agent_plan,
    hydrate_unit_agent_plan,
    work_unit_id_from_text,
)


def _routing(*units: str) -> dict[str, object]:
    return {
        "selected_ids": ["code-reviewer"],
        "work_units": {
            "delegate": True,
            "count": len(units),
            "confidence": "high",
            "source": "integrity-test",
            "units": list(units),
        },
    }


def test_complete_bounded_goal_drives_identity_while_preview_stays_small() -> None:
    shared = "Implement " + "shared transport-safe requirement " * 8
    first = f"{shared}for Windows"
    second = f"{shared}for Linux"

    detected = detect_work_units(f"1. {first}\n2. {second}")

    assert detected["units"] == [first, second]
    assert detected["previews"][0] == detected["previews"][1]
    assert all(len(item) == MAX_WORK_UNIT_PREVIEW_CHARS for item in detected["previews"])
    assert detected["preview_truncated"] == [True, True]
    assert work_unit_id_from_text(first) != work_unit_id_from_text(second)

    routing = _routing(first, second)
    plan = build_unit_agent_plan(routing)
    hydrated = hydrate_unit_agent_plan(routing, plan)

    assert [item["work_unit_id"] for item in plan] == [
        work_unit_id_from_text(first),
        work_unit_id_from_text(second),
    ]
    assert plan[0]["goal_hash"] != plan[1]["goal_hash"]
    assert [item["goal"] for item in hydrated] == [first, second]
    assert all(len(item["goal_preview"]) == MAX_WORK_UNIT_PREVIEW_CHARS for item in hydrated)


def test_duplicate_imperative_spans_do_not_create_duplicate_units() -> None:
    assert _imperative_units("fix x; fix x") == ["fix x"]


def test_overflow_is_visible_and_abstains_instead_of_slicing_a_plan() -> None:
    message = "\n".join(
        f"{index + 1}. Implement bounded component {index}"
        for index in range(MAX_SUGGESTED_WORK_UNITS + 1)
    )

    detected = detect_work_units(message)

    assert detected["source"] == "numbered_list_overflow"
    assert detected["truncated"] is True
    assert detected["overflow_count"] == 1
    assert detected["overflow_count_exact"] is True
    assert detected["abstention_reason"] == "work_unit_limit_exceeded"
    assert detected["delegate"] is False
    assert len(detected["units"]) == MAX_SUGGESTED_WORK_UNITS
    assert build_unit_agent_plan({"selected_ids": ["code-reviewer"], "work_units": detected}) == []

    raw_overflow = _routing(
        *(f"Implement bounded component {index}" for index in range(MAX_SUGGESTED_WORK_UNITS + 1))
    )
    assert build_unit_agent_plan(raw_overflow) == []
    assert _delegated_work_units(raw_overflow) == []


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
        "c:/program files/agency/config.json"
    ]
    assert not _looks_like_resource("")
    assert not _looks_like_resource("https://example.test/source.py")
    assert _likely_resources("Update src/a.py and src\\a.py") == ["src/a.py"]
    many = " ".join(f"src/component-{index}.py" for index in range(12))
    assert len(_likely_resources(many)) == 8


def test_same_resource_writes_get_deterministic_dependency_edges() -> None:
    units = (
        "Update ./src/auth.py with the new contract",
        r"Write src\auth.py with validation",
        "Update docs/README.md with usage",
    )
    routing = _routing(*units)

    first = build_unit_agent_plan(routing)
    replay = build_unit_agent_plan(deepcopy(routing))

    assert replay == first
    assert first[0]["parallelization"] == "sequential"
    assert first[0]["depends_on"] == []
    assert first[1]["parallelization"] == "sequential"
    assert first[1]["depends_on"] == [first[0]["work_unit_id"]]
    assert first[2]["parallelization"] == "parallel"
    assert first[2]["depends_on"] == []
    hydrated = hydrate_unit_agent_plan(routing, first)
    assert hydrated[0]["likely_files_or_resources"] == ["src/auth.py"]
    assert hydrated[1]["likely_files_or_resources"] == ["src/auth.py"]


def test_unknown_resources_are_never_advertised_as_parallel() -> None:
    routing = _routing("Implement authentication behavior", "Review authentication behavior")

    plan = build_unit_agent_plan(routing)

    assert [item["parallelization"] for item in plan] == ["unspecified", "unspecified"]
    assert all(item["depends_on"] == [] for item in plan)
    assert all(
        item["likely_files_or_resources"] == ["repository-workspace"]
        for item in hydrate_unit_agent_plan(routing, plan)
    )

    mixed = build_unit_agent_plan(
        _routing("Implement authentication behavior", "Update src/auth.py")
    )
    assert [item["parallelization"] for item in mixed] == ["unspecified", "unspecified"]


def test_same_resource_readers_remain_parallel_without_false_dependencies() -> None:
    routing = _routing("Review src/auth.py", "Inspect ./src/auth.py")

    plan = build_unit_agent_plan(routing)

    assert [item["parallelization"] for item in plan] == ["parallel", "parallel"]
    assert all(item["depends_on"] == [] for item in plan)


def test_hydration_rejects_a_long_goal_suffix_substitution() -> None:
    shared = "Implement " + "x" * (MAX_WORK_UNIT_PREVIEW_CHARS + 40)
    routing = _routing(f"{shared}A", "Review docs/README.md")
    plan = build_unit_agent_plan(routing)
    tampered = _routing(f"{shared}B", "Review docs/README.md")

    with pytest.raises(RuntimeError, match="does not match"):
        hydrate_unit_agent_plan(tampered, plan)


def test_hydration_fails_closed_for_invalid_bounds_and_resource_receipts() -> None:
    routing = _routing("Update src/auth.py", "Review docs/README.md")
    plan = build_unit_agent_plan(routing)

    with pytest.raises(RuntimeError, match="plan is invalid"):
        hydrate_unit_agent_plan(routing, [{}])
    with pytest.raises(RuntimeError, match="no replayable work units"):
        hydrate_unit_agent_plan({"work_units": {"units": "invalid"}}, plan)
    with pytest.raises(RuntimeError, match="exceeds the work-unit plan bound"):
        hydrate_unit_agent_plan(
            {
                "work_units": {
                    "units": [
                        *(f"unit-{index}" for index in range(MAX_SUGGESTED_WORK_UNITS)),
                        "overflow",
                    ]
                }
            },
            plan,
        )

    with_empty = {"work_units": {"units": ["", *routing["work_units"]["units"]]}}
    assert len(hydrate_unit_agent_plan(with_empty, plan)) == 2

    tampered_plan = deepcopy(plan)
    tampered_plan[0]["resource_hashes"] = [_plan_hash("src/other.py")]
    with pytest.raises(RuntimeError, match="resource plan does not match"):
        hydrate_unit_agent_plan(routing, tampered_plan)


def test_duplicate_goals_and_unmatched_units_do_not_leak_plan_rows() -> None:
    duplicate = _routing("Review src/auth.py", "Review src/auth.py")
    assert len(build_unit_agent_plan(duplicate)) == 1
    assert (
        build_unit_agent_plan(
            {
                "selected_ids": [],
                "work_units": {
                    "delegate": True,
                    "count": 2,
                    "confidence": "high",
                    "source": "integrity-test",
                    "units": ["Reconcile lunar telemetry", "Inspect Martian telemetry"],
                },
            }
        )
        == []
    )
