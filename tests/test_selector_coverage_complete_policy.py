"""Malformed-policy and reload-boundary contracts for companion routing."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core import config as config_module
from agency_runtime.core.selector import policy


def test_policy_path_resolution_uses_config_and_fails_back_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGENCY_POLICY_PATH", raising=False)
    monkeypatch.setattr(
        config_module,
        "load_config",
        lambda: SimpleNamespace(companion_policy_path="~/custom-policy.yaml"),
    )
    assert policy._resolve_policy_path() == Path.home() / "custom-policy.yaml"

    monkeypatch.setattr(
        config_module,
        "load_config",
        lambda: (_ for _ in ()).throw(OSError("config unavailable")),
    )
    assert policy._resolve_policy_path() == policy._DEFAULT_POLICY_PATH


def test_bundled_policy_load_failure_is_cached_as_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(policy, "_BUNDLED_COMPANION_POLICY", None)
    monkeypatch.setattr(
        policy,
        "_read_bounded_policy",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("bundle unavailable")),
    )

    assert policy._load_bundled_policy() == {}
    assert policy._load_bundled_policy() == {}


def test_trigger_and_condition_matching_rejects_nonlexical_inputs() -> None:
    policy._compiled_trigger.cache_clear()
    assert policy._compiled_trigger("_fallback_") is None
    assert policy._compiled_trigger("***") is None
    assert policy._matches("code review", 7) is False
    assert policy._matches_condition("code review", ["code"]) is False


def test_policy_reload_reuses_unchanged_file_and_retains_last_good_same_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "policy.yaml"
    path.write_text("actions:\n  FIRST:\n    triggers: [alpha]\n", encoding="utf-8")
    monkeypatch.setattr(policy, "_COMPANION_POLICY", None)
    monkeypatch.setattr(policy, "_POLICY_MTIME", 0.0)
    monkeypatch.setattr(policy, "_POLICY_PATH", None)
    monkeypatch.setattr(policy, "_POLICY_REQUEST_KEY", "")
    monkeypatch.setattr(policy, "_POLICY_CHECKED_AT", 0.0)

    first = policy.load_policy(path)
    second = policy.load_policy(path)
    assert first is second
    assert set(second["actions"]) == {"FIRST"}

    monkeypatch.setattr(policy, "_POLICY_MTIME", -1)
    monkeypatch.setattr(
        policy,
        "_read_bounded_policy",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("invalid update")),
    )
    retained = policy.load_policy(path)
    assert retained is first


def test_policy_route_validation_reports_every_malformed_division_shape() -> None:
    routes, errors = policy._policy_routes(
        {
            "actions": {},
            "division_anchors": {
                "not-a-mapping": [],
                "bad-anchor": {"anchor": " ", "conditional": "not-a-list"},
                "entries": {
                    "conditional": [
                        "incomplete",
                        {"slug": "", "when": "condition"},
                        {"slug": "valid", "when": ""},
                        ("tuple-specialist", "tuple condition"),
                    ]
                },
            },
        }
    )

    assert {route["slug"] for route in routes} == {"valid", "tuple-specialist"}
    assert "division_anchors.not-a-mapping must be a mapping" in errors
    assert "division_anchors.bad-anchor.anchor must be a non-empty string" in errors
    assert "division_anchors.bad-anchor.conditional must be a list" in errors
    assert any("must contain a slug and condition" in error for error in errors)
    assert any(".slug must be a non-empty string" in error for error in errors)
    assert any(".when must be a non-empty string" in error for error in errors)


def test_slug_and_availability_validation_rejects_adversarial_registry_shapes() -> None:
    errors: list[str] = []
    assert policy._slug_list("not-a-list", path="items", errors=errors) == []
    assert policy._slug_list(["same", "same", 7], path="items", errors=errors) == [
        "same",
        "same",
    ]
    assert "items must be a list" in errors
    assert "items[2] must be a non-empty string" in errors
    assert "items must not contain duplicate slugs" in errors

    invalid_mapping = policy.validate_policy(
        {"actions": {}, "specialist_availability": "invalid"},
        [],
    )
    assert "specialist_availability must be a mapping" in invalid_mapping["errors"]

    invalid_gated = policy.validate_policy(
        {
            "actions": {},
            "specialist_availability": {
                "schema_version": 2,
                "enabled": [],
                "roster_gated": "invalid",
            },
        },
        [],
    )
    assert "specialist_availability.schema_version must be 1" in invalid_gated["errors"]
    assert "specialist_availability.roster_gated must be a mapping" in invalid_gated["errors"]

    conflicting = policy.validate_policy(
        {
            "actions": {
                "ACTION": {
                    "always_include": [{"slug": "route"}],
                    "conditional": [],
                }
            },
            "specialist_availability": {
                "schema_version": 1,
                "enabled": ["route", "both", "extra"],
                "roster_gated": {
                    "reason": "requires activation",
                    "slugs": ["both"],
                },
            },
        },
        ["route"],
    )
    assert any("both enabled and roster-gated: both" in item for item in conflicting["errors"])
    assert any(
        "availability declares unreferenced specialists: both, extra" in item
        for item in conflicting["errors"]
    )


def test_invalid_companion_identity_is_never_appended() -> None:
    companions: list[str] = []
    policy._append_eligible_companion(companions, None, None)
    policy._append_eligible_companion(companions, "", None)
    assert companions == []


def test_nonmatching_division_condition_is_not_promoted() -> None:
    actions, companions = policy.detect_actions(
        "optimize the database",
        {
            "actions": {
                "OTHER": {
                    "triggers": ["unrelated"],
                    "always_include": [],
                    "conditional": [],
                }
            },
            "division_anchors": {
                "data": {
                    "keywords": ["database"],
                    "anchor": "database-anchor",
                    "conditional": [{"slug": "security-reviewer", "when": "security audit"}],
                }
            },
        },
    )

    assert actions == []
    assert companions == ["database-anchor"]
