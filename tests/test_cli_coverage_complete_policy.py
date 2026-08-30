"""Behavior coverage for CLI policy projection and detailed rendering."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agency_runtime.cli import roster_commands as subject


def validation(*, valid=False):
    return {
        "valid": valid,
        "errors": [] if valid else ["missing specialist"],
        "mode": "strict",
        "route_count": 3,
        "unique_policy_slugs": ["missing", "disabled", "active"],
        "enabled_slugs": ["missing", "active"],
        "missing_enabled": ["missing"],
        "disabled_count": 1,
        "disabled_routes": [{"slug": "disabled"}],
        "routes": [
            {"source": "action", "group": "ignore", "slug": "active"},
            {"source": "division", "group": "engineering", "slug": "missing"},
            {
                "source": "division",
                "group": "engineering",
                "slug": "disabled",
            },
        ],
    }


def test_policy_helpers_handle_invalid_declarations_and_catalog_shapes():
    assert subject._policy_mapping({"actions": []}, "actions") == {}
    assert subject._policy_mapping({"actions": {"review": {}}}, "actions") == {"review": {}}
    assert subject._active_roster_slugs([{"slug": "one"}, {"agent_slug": "two"}, {}]) == {
        "one",
        "two",
    }
    assert subject._declared_policy_slugs([None, {}, {"slug": "one"}]) == ["one"]
    assert subject._declared_policy_slugs(None) == []


def test_policy_summaries_cover_missing_disabled_and_non_division_routes():
    actions = {
        "invalid": [],
        "review": {
            "always_include": [{"slug": "missing"}, {"slug": "disabled"}],
            "conditional": [
                {"slug": "missing"},
                {"slug": "disabled"},
                *({"slug": f"extra-{index}"} for index in range(9)),
            ],
        },
    }
    summaries = subject._summarize_policy_actions(actions, {"missing"}, {"disabled"})
    assert summaries["invalid"] == subject._empty_action_summary()
    assert summaries["review"]["always_missing"] == ["missing"]
    assert summaries["review"]["always_disabled"] == ["disabled"]
    divisions = subject._summarize_policy_divisions(
        validation()["routes"], {"missing"}, {"disabled"}
    )
    assert divisions == {
        "engineering": {
            "routes": ["missing", "disabled"],
            "missing": ["missing"],
            "disabled": ["disabled"],
        }
    }


def test_policy_renderers_show_full_actionable_breakdown(capsys):
    actions = {
        "review": {
            "always_include": [{"slug": "missing"}, {"slug": "disabled"}],
            "conditional": [
                {"slug": "missing"},
                {"slug": "disabled"},
                *({"slug": f"extra-{index}"} for index in range(9)),
            ],
        },
        "clean": {"always_include": [], "conditional": []},
    }
    summaries = subject._summarize_policy_actions(actions, {"missing"}, {"disabled"})
    subject._print_policy_action("review", summaries["review"])
    subject._print_policy_action("clean", summaries["clean"])
    subject._print_policy_report(
        actions=actions,
        divisions={"engineering": []},
        active_slugs={"active"},
        validation=validation(),
        action_summary=summaries,
    )
    output = capsys.readouterr().out
    assert "enabled but missing" in output
    assert "roster-gated and disabled" in output
    assert "enabled conditional missing" in output
    assert "roster-gated conditionals" in output
    assert "…" in output
    assert "INVALID" in output
    assert "✅ clean" in output


@pytest.mark.parametrize("json_mode", [False, True])
@pytest.mark.parametrize("valid", [False, True])
def test_policy_command_human_json_valid_and_invalid(monkeypatch, capsys, json_mode, valid):
    policy = {
        "actions": {"review": {"always_include": [{"slug": "missing"}]}},
        "division_anchors": {"engineering": []},
    }
    store = SimpleNamespace(get_active_roster_as_catalog=lambda: [{"slug": "active"}])
    emitted = []
    dependencies = subject.RosterDependencies(
        store_factory=lambda: store,
        emit_json=emitted.append,
        policy_loader=lambda: policy,
    )
    monkeypatch.setattr(subject, "validate_policy", lambda *_args: validation(valid=valid))
    assert subject.cmd_policy(SimpleNamespace(json=json_mode), dependencies=dependencies) == (
        0 if valid else 1
    )
    if json_mode:
        assert emitted[-1]["all_missing"] == ["missing"]
        assert emitted[-1]["valid"] is valid
    else:
        assert ("VALID" if valid else "INVALID") in capsys.readouterr().out
