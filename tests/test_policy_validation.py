"""Companion-policy availability and strict validation coverage."""

from __future__ import annotations

import argparse
import copy
import json

import pytest

from agency_runtime.cli import main as cli
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.selector.policy import (
    detect_actions,
    load_bundled_policy,
    validate_policy,
)

STARTER_SLUGS = {str(item["slug"]) for item in STARTER_ROSTER}


def test_bundled_policy_classifies_every_route_against_starter_roster() -> None:
    report = validate_policy(load_bundled_policy(), STARTER_SLUGS)

    assert report["valid"] is True
    assert report["errors"] == []
    assert report["unique_policy_slugs"] == 238
    assert report["enabled_slugs"] == sorted(STARTER_SLUGS)
    assert report["disabled_count"] == 231
    assert {item["reason"] for item in report["disabled_routes"]} == {
        "No governed active definition is available; this route is enabled "
        "only after approved roster activation."
    }
    assert {route["source"] for route in report["routes"]} == {
        "action",
        "division",
    }


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            "Implement ICU MessageFormat with CLDR plural rules and RTL support",
            "internationalization-engineer",
        ),
        (
            "Implement Stripe payments and billing for the API",
            "payments-billing-engineer",
        ),
        (
            "Benchmark Playwright end-to-end test automation performance",
            "test-automation-engineer",
        ),
    ],
)
def test_bundled_specialist_routes_resolve(
    message: str,
    expected: str,
) -> None:
    _actions, companions = detect_actions(
        message,
        load_bundled_policy(),
        active_slugs=STARTER_SLUGS,
    )

    assert expected in companions


def test_roster_gated_routes_are_skipped_without_an_active_roster() -> None:
    _actions, companions = detect_actions("anything at all", load_bundled_policy())

    assert "agents-orchestrator" not in companions
    assert "chief-of-staff" not in companions


def test_roster_gated_route_activates_after_governed_roster_activation() -> None:
    active = STARTER_SLUGS | {"agents-orchestrator"}

    _actions, companions = detect_actions(
        "anything at all",
        load_bundled_policy(),
        active_slugs=active,
    )

    assert "agents-orchestrator" in companions
    assert "chief-of-staff" not in companions


def test_unclassified_action_route_fails_validation() -> None:
    policy = copy.deepcopy(load_bundled_policy())
    policy["actions"]["CODING"]["conditional"].append(
        {"slug": "undeclared-specialist", "when": "undeclared specialty"}
    )

    report = validate_policy(policy, STARTER_SLUGS)

    assert report["valid"] is False
    assert any(
        "policy routes have no availability declaration" in error
        and "undeclared-specialist" in error
        for error in report["errors"]
    )


def test_unclassified_division_anchor_fails_validation() -> None:
    policy = copy.deepcopy(load_bundled_policy())
    policy["division_anchors"]["specialized"]["anchor"] = "undeclared-anchor"

    report = validate_policy(policy, STARTER_SLUGS)

    assert report["valid"] is False
    assert any("undeclared-anchor" in error for error in report["errors"])


def test_enabled_specialist_must_be_referenced_and_active() -> None:
    policy = copy.deepcopy(load_bundled_policy())
    policy["actions"]["CODING"]["conditional"].append(
        {"slug": "missing-enabled", "when": "missing enabled"}
    )
    policy["specialist_availability"]["enabled"].append("missing-enabled")

    report = validate_policy(policy, STARTER_SLUGS)

    assert report["valid"] is False
    assert report["missing_enabled"] == ["missing-enabled"]
    assert "enabled specialist is not active: missing-enabled" in report["errors"]


def test_roster_gated_routes_require_a_reason() -> None:
    policy = copy.deepcopy(load_bundled_policy())
    policy["specialist_availability"]["roster_gated"]["reason"] = " "

    report = validate_policy(policy, STARTER_SLUGS)

    assert report["valid"] is False
    assert any("reason must be a non-empty string" in error for error in report["errors"])


class _CatalogStore:
    def __init__(self, slugs: set[str]) -> None:
        self._catalog = [{"slug": slug} for slug in sorted(slugs)]

    def get_active_roster_as_catalog(self) -> list[dict[str, str]]:
        return self._catalog


def test_policy_cli_json_is_truthful_and_includes_division_routes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "load_policy", load_bundled_policy)
    monkeypatch.setattr(cli, "_store", lambda: _CatalogStore(STARTER_SLUGS))

    result = cli.cmd_policy(argparse.Namespace(json=True))
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["valid"] is True
    assert payload["unique_policy_slugs"] == 238
    assert payload["division_count"] == 6
    assert payload["disabled_count"] == 231
    assert payload["all_missing"] == []


def test_policy_cli_text_preserves_the_availability_breakdown(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "load_policy", load_bundled_policy)
    monkeypatch.setattr(cli, "_store", lambda: _CatalogStore(STARTER_SLUGS))

    result = cli.cmd_policy(argparse.Namespace(json=False))
    output = capsys.readouterr().out

    assert result == 0
    assert output.startswith("Companion policy: 16 broad actions, 6 division anchors, ")
    assert "\n✅ VALID:" in output
    assert "\n✅ CODING\n" in output
    assert "   always_include (" in output
    assert "   roster-gated and disabled (" in output
    assert "   conditional (" in output


def test_policy_cli_returns_nonzero_for_missing_enabled_specialists(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "load_policy", load_bundled_policy)
    monkeypatch.setattr(cli, "_store", lambda: _CatalogStore(set()))

    result = cli.cmd_policy(argparse.Namespace(json=True))
    payload = json.loads(capsys.readouterr().out)

    assert result == 1
    assert payload["valid"] is False
    assert payload["missing_enabled"] == sorted(STARTER_SLUGS)


def test_policy_cli_returns_nonzero_for_malformed_policy(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "load_policy", lambda: {"actions": []})
    monkeypatch.setattr(cli, "_store", lambda: _CatalogStore(STARTER_SLUGS))

    result = cli.cmd_policy(argparse.Namespace(json=True))
    payload = json.loads(capsys.readouterr().out)

    assert result == 1
    assert payload["valid"] is False
    assert "actions must be a mapping" in payload["errors"]
