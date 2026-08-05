"""Operator CLI coverage for workforce, contractor, and hiring lifecycle surfaces."""

from __future__ import annotations

import json
from pathlib import Path

from agency_runtime.cli import main as cli
from agency_runtime.cli import roster_commands
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce.known_installer import install_known_contractors


def _installed_store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "agency.db")
    install_known_contractors(store)
    return store


def test_workforce_list_search_show_and_hiring_evidence_are_json_capable(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    store = _installed_store(tmp_path)
    monkeypatch.setattr(cli, "_store", lambda *args, **kwargs: store)

    assert cli.main(["workforce", "list", "--state", "contractor", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["count"] == 15
    assert all(item["state"] == "contractor" for item in listed["workers"])

    assert cli.main(["workforce", "search", "typescript", "--json"]) == 0
    searched = json.loads(capsys.readouterr().out)
    assert searched["workers"][0]["agent_slug"] == "typescript-application-engineer"

    assert (
        cli.main(
            [
                "workforce",
                "show",
                "application-integration-verifier",
                "--json",
            ]
        )
        == 0
    )
    detail = json.loads(capsys.readouterr().out)
    assert detail["worker"]["display_label"].startswith("Contractor · ")
    assert detail["recruitment_contract"]["authority"] == "review"
    assert detail["hiring_cases"][0]["status"] == "applied"
    assert detail["promotion_readiness"]["human_promotion_available"] is True
    worker_id = detail["worker"]["worker_id"]

    assert cli.main(["hiring", "list", "--status", "applied", "--json"]) == 0
    hiring = json.loads(capsys.readouterr().out)
    assert hiring["count"] == 15
    case_id = hiring["hiring_cases"][0]["id"]
    assert cli.main(["hiring", "show", case_id, "--json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["id"] == case_id
    assert shown["critic_evidence"]["approved"] is True

    assert (
        cli.main(
            [
                "workforce",
                "duplicates",
                worker_id,
                "--limit",
                "3",
                "--json",
            ]
        )
        == 0
    )
    duplicates = json.loads(capsys.readouterr().out)
    assert duplicates["authority"] == "read_only_recommendation"
    assert duplicates["workforce_count"] == 15
    assert len(duplicates["comparisons"]) == 3
    assert duplicates["comparisons"][0]["recommendation"] == "keep_distinct"

    assert cli.main(["workforce", "consolidate", "--json"]) == 0
    consolidation = json.loads(capsys.readouterr().out)
    assert consolidation["automatic_mutation"] is False
    assert consolidation["authority"] == "read_only_recommendation"


def test_workforce_show_text_mode_prints_full_promotion_readiness(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    """AR-243: the CLI text-mode workforce show prints the same promotion
    readiness fields the dashboard renders (verified, required, remaining,
    automatic state, review-window, reasons, evidence rule)."""

    store = _installed_store(tmp_path)
    monkeypatch.setattr(cli, "_store", lambda *args, **kwargs: store)

    assert (
        cli.main(["workforce", "show", "application-integration-verifier"]) == 0
    )
    output = capsys.readouterr().out
    assert "promotion\t" in output
    assert "verified=" in output
    assert "required=" in output
    assert "remaining=" in output
    assert "automatic=" in output
    assert "evidence-rule\t" in output


def test_hiring_list_and_show_render_card_and_tabular_outputs(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    store = _installed_store(tmp_path)
    monkeypatch.setattr(cli, "_store", lambda *args, **kwargs: store)

    assert cli.main(["hiring", "list", "--limit", "5", "--no-card"]) == 0
    listed = capsys.readouterr().out
    lines = [line for line in listed.splitlines() if line.strip()]
    assert lines, "hiring list --no-card should print at least one line"
    parts = lines[0].split("\t")
    assert len(parts) == 6
    assert parts[4] == "standard", "tab-separated line must carry the risk_tier column"

    assert cli.main(["hiring", "list", "--limit", "5", "--card"]) == 0
    card_output = capsys.readouterr().out
    assert "─" * 40 in card_output
    assert "Case" in card_output
    assert "Risk" in card_output
    assert "applied" in card_output
    assert card_output.count("Case") >= 1

    case_id = (
        json.loads(capsys.readouterr().out or listed or "")
        if False
        else store.list_hiring_cases(limit=1)[0]["id"]
    )

    assert cli.main(["hiring", "show", case_id, "--json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["id"] == case_id
    assert "contract_evidence" in shown

    assert cli.main(["hiring", "show", case_id, "--no-card"]) == 0
    plain = capsys.readouterr().out
    assert "contract\t" in plain
    assert "gap\t" in plain
    assert "critic\t" in plain

    assert cli.main(["hiring", "show", case_id, "--card"]) == 0
    card_detail = capsys.readouterr().out
    assert "Contract evidence" in card_detail
    assert "Gap evidence" in card_detail
    assert "Independent critic" in card_detail
    assert "Model receipts" in card_detail
    assert "Duplicate analysis" in card_detail


def test_workforce_amend_alias_requires_governed_case_approval_confirmation(
    capsys,
) -> None:
    assert (
        cli.main(
            [
                "workforce",
                "amend",
                "case-amend",
                "--approved-by",
                "operator",
                "--confirm",
                "wrong",
            ]
        )
        == 1
    )
    assert 'confirmation required: --confirm "APPROVE case-amend"' in capsys.readouterr().err


def test_workforce_toggle_requires_confirmation_reason_and_supports_json(
    monkeypatch,
    capsys,
) -> None:
    observed: list[dict[str, object]] = []

    def set_enabled(slug, *, enabled, config_argument=None, reason=""):
        observed.append(
            {
                "slug": slug,
                "enabled": enabled,
                "config": config_argument,
                "reason": reason,
            }
        )
        return str(slug), True, "C:/agency/config.yaml"

    monkeypatch.setattr(roster_commands, "_set_agent_enabled", set_enabled)
    assert (
        cli.main(
            [
                "workforce",
                "disable",
                "typescript-application-engineer",
                "--reason",
                "unsafe near-neighbor result",
                "--confirm",
                "DISABLE typescript-application-engineer",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "ok": True,
        "slug": "typescript-application-engineer",
        "enabled": False,
        "changed": True,
        "config_path": "C:/agency/config.yaml",
    }
    assert observed == [
        {
            "slug": "typescript-application-engineer",
            "enabled": False,
            "config": None,
            "reason": "unsafe near-neighbor result",
        }
    ]

    assert (
        cli.main(
            [
                "workforce",
                "enable",
                "typescript-application-engineer",
                "--reason",
                "review completed",
                "--confirm",
                "wrong",
                "--json",
            ]
        )
        == 1
    )
    rejected = json.loads(capsys.readouterr().out)
    assert "confirmation required" in rejected["error"]


def test_workforce_lifecycle_requires_revision_and_destructive_confirmation(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    store = _installed_store(tmp_path)
    monkeypatch.setattr(cli, "_store", lambda *args, **kwargs: store)
    slug = "typescript-application-engineer"

    assert (
        cli.main(
            [
                "workforce",
                "promote",
                slug,
                "--expected-revision",
                "0",
                "--reason",
                "verified assignments",
                "--json",
            ]
        )
        == 0
    )
    promoted = json.loads(capsys.readouterr().out)
    assert promoted["worker"]["state"] == "employee"
    assert not promoted["worker"]["display_label"].startswith("Contractor · ")

    assert (
        cli.main(
            [
                "workforce",
                "suspend",
                slug,
                "--expected-revision",
                "1",
                "--reason",
                "operator hold",
                "--confirm",
                "wrong",
            ]
        )
        == 1
    )
    assert f'--confirm "SUSPEND {slug}"' in capsys.readouterr().err

    assert (
        cli.main(
            [
                "workforce",
                "suspend",
                slug,
                "--expected-revision",
                "1",
                "--reason",
                "operator hold",
                "--confirm",
                f"SUSPEND {slug}",
                "--json",
            ]
        )
        == 0
    )
    suspended = json.loads(capsys.readouterr().out)
    assert suspended["worker"]["state"] == "suspended"
