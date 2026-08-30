"""Deterministic workspace stack detection surfaced to inference."""

from __future__ import annotations

import json
from pathlib import Path

from agency_runtime.core.workforce.inference import _context_document
from agency_runtime.core.workforce.staffing_verifier import StaffingContext
from agency_runtime.core.workspace_stacks import detect_workspace_stacks


def test_marker_files_prove_language_stacks(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
    (tmp_path / "go.mod").write_text("module example\n", encoding="utf-8")
    (tmp_path / "Api.csproj").write_text("<Project/>", encoding="utf-8")

    assert detect_workspace_stacks(tmp_path) == (
        "dotnet",
        "go",
        "javascript",
        "python",
        "typescript",
    )


def test_dependency_manifests_prove_framework_stacks(tmp_path: Path) -> None:
    (tmp_path / "composer.json").write_text(
        json.dumps(
            {
                "require": {"laravel/framework": "^12.0", "livewire/livewire": "^4.0"},
            }
        ),
        encoding="utf-8",
    )

    assert detect_workspace_stacks(tmp_path) == ("laravel", "livewire", "php")


def test_scan_is_depth_bounded_and_skips_dependency_directories(tmp_path: Path) -> None:
    nested = tmp_path / "services" / "api"
    nested.mkdir(parents=True)
    (nested / "go.mod").write_text("module nested\n", encoding="utf-8")
    too_deep = tmp_path / "a" / "b" / "c"
    too_deep.mkdir(parents=True)
    (too_deep / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    vendored = tmp_path / "node_modules" / "left-pad"
    vendored.mkdir(parents=True)
    (vendored / "package.json").write_text("{}", encoding="utf-8")

    assert detect_workspace_stacks(tmp_path) == ("go",)


def test_malformed_manifest_and_missing_root_degrade_to_no_signal(tmp_path: Path) -> None:
    (tmp_path / "composer.json").write_text("{not json", encoding="utf-8")

    assert detect_workspace_stacks(tmp_path) == ("php",)
    assert detect_workspace_stacks(tmp_path / "does-not-exist") == ()


def test_detected_stacks_flow_into_the_inference_context_document() -> None:
    context = StaffingContext(
        "claude",
        "windows",
        frozenset({"Read"}),
        3,
        None,
        detected_stacks=("python", "typescript"),
    )

    document = _context_document(context)

    assert document["detected_stacks"] == ["python", "typescript"]
    # Default constructions stay valid and content-free.
    bare = StaffingContext("claude", "windows", frozenset(), 0)
    assert _context_document(bare)["detected_stacks"] == []
