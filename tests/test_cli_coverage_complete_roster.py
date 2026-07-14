"""Behavior coverage for roster, routing, evaluation, and database commands."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agency_runtime.cli import roster_commands as subject


def args(**changes):
    values = {
        "all": False,
        "auto_approve": False,
        "dry_run": False,
        "json": False,
        "keep_last": 10,
        "limit": 3,
        "name": "",
        "no_details": False,
        "no_vacuum": False,
        "older_than_days": 30,
        "query": "review",
        "review": False,
        "session_id": "session",
        "snapshot_id": "snapshot",
        "task": "review",
        "trusted_for_auto_approve": False,
        "url": "source",
    }
    values.update(changes)
    return SimpleNamespace(**values)


class Store:
    def __init__(self):
        self.sources = []
        self.catalog = []
        self.calls = []

    def list_agent_sources(self):
        return self.sources

    def add_agent_source(self, *values, **kwargs):
        self.calls.append(("add", values, kwargs))
        return "source-id"

    def get_active_roster_as_catalog(self):
        return self.catalog

    def database_stats(self):
        return {
            "db_path": "agency.db",
            "db_size_bytes": 10,
            "wal_size_bytes": 2,
            "shm_size_bytes": 1,
            "tables": {"agents": 3},
        }

    def trim_runtime_tables(self, **kwargs):
        self.calls.append(("trim", kwargs))
        return {
            "dry_run": kwargs["dry_run"],
            "db_path": "agency.db",
            "db_size_before_bytes": 10,
            "db_size_after_bytes": 5,
            "tables": {"events": {"deleted": 2}, "empty": {"deleted": 0}},
        }


def test_candidate_download_validation_and_quarantine(monkeypatch):
    errors = []
    monkeypatch.setattr(subject, "download_from_source", lambda _url: [])
    assert subject._download_sync_candidates({"url": "empty"}, errors) is None
    assert errors[-1]["error"] == "source returned zero candidates"
    monkeypatch.setattr(
        subject,
        "download_from_source",
        lambda _url: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert subject._download_sync_candidates({"url": "bad"}, errors) is None
    assert errors[-1] == {"source": "bad", "error": "offline"}

    agents = [{"slug": "valid"}, {"slug": "invalid"}]
    monkeypatch.setattr(subject, "download_from_source", lambda _url: agents)
    monkeypatch.setattr(
        subject,
        "validate_agent",
        lambda agent: (agent["slug"] == "valid", "invalid agent"),
    )
    monkeypatch.setattr(
        subject,
        "quarantine_candidate",
        lambda agent, source_id, store: f"{source_id}:{agent['slug']}:{id(store)}",
    )
    store = object()
    sources = [{"id": "source-id", "url": "source"}]
    dry, dry_errors = subject._collect_sync_candidates(sources, store, dry_run=True)
    assert dry == ["valid"] and dry_errors[0]["agent"] == "invalid"
    persisted, persisted_errors = subject._collect_sync_candidates(sources, store, dry_run=False)
    assert persisted == [f"source-id:valid:{id(store)}"]
    assert persisted_errors[0]["error"] == "invalid agent"


def test_sync_trust_preflight_and_completion(monkeypatch, capsys):
    emitted = []
    monkeypatch.setattr(subject, "_print_json", emitted.append)
    assert not subject._reject_untrusted_auto_approve_sources(
        [{"url": "trusted", "trusted_for_auto_approve": 1}]
    )
    assert subject._reject_untrusted_auto_approve_sources(
        [{"url": "untrusted", "trusted_for_auto_approve": 0}]
    )
    assert "untrusted" in capsys.readouterr().err
    assert subject._auto_approve_preflight(auto_approve=False, quarantined=[], errors=[]) is None
    assert (
        subject._auto_approve_preflight(
            auto_approve=True,
            quarantined=["one"],
            errors=[{"error": "bad"}],
        )
        == 2
    )
    assert emitted[-1]["errors"]
    assert subject._auto_approve_preflight(auto_approve=True, quarantined=[], errors=[]) == 1
    assert "no candidates" in capsys.readouterr().err

    actions = []
    monkeypatch.setattr(
        subject,
        "create_roster_diff",
        lambda _store, **_kwargs: {
            "snapshot_id": "snap",
            "diff": {"added": ["one"]},
        },
    )
    monkeypatch.setattr(
        subject,
        "approve_snapshot",
        lambda _store, snapshot: actions.append(("approve", snapshot)),
    )
    monkeypatch.setattr(
        subject,
        "activate_snapshot",
        lambda _store, snapshot: actions.append(("activate", snapshot)),
    )
    assert subject._complete_sync(args(review=True, auto_approve=True), object(), ["one"], []) == 0
    assert actions == [("approve", "snap"), ("activate", "snap")]
    assert emitted[-1]["activated"] is True
    assert subject._complete_sync(args(), object(), ["one"], [{"error": "partial"}]) == 2
    assert "Created snapshot snap" in capsys.readouterr().out


def test_sync_command_no_sources_untrusted_dry_and_preflight(monkeypatch, capsys):
    store = Store()
    monkeypatch.setattr(subject, "_store", lambda: store)
    assert subject.cmd_sync(args()) == 1
    assert "No enabled sources" in capsys.readouterr().err
    store.sources = [{"url": "bad", "trusted_for_auto_approve": 0}]
    assert subject.cmd_sync(args(auto_approve=True)) == 1
    assert "not trusted" in capsys.readouterr().err

    emitted = []
    store.sources = [{"id": "source", "url": "source", "trusted_for_auto_approve": 1}]
    monkeypatch.setattr(subject, "_print_json", emitted.append)
    monkeypatch.setattr(
        subject,
        "_collect_sync_candidates",
        lambda *_a, **_kw: (["candidate"], [{"error": "partial"}]),
    )
    assert subject.cmd_sync(args(dry_run=True)) == 2
    assert emitted[-1]["valid_candidates"] == ["candidate"]
    assert subject.cmd_sync(args(auto_approve=True)) == 2


def test_crud_search_and_explain_commands(monkeypatch, capsys):
    store = Store()
    store.sources = [{"url": "one"}]
    store.catalog = [
        {
            "slug": "agent",
            "name": "Agent",
            "division": "eng",
            "description": "Useful",
        }
    ]
    emitted = []
    monkeypatch.setattr(subject, "_store", lambda: store)
    monkeypatch.setattr(subject, "_print_json", emitted.append)
    assert subject.cmd_source_add(args(trusted_for_auto_approve=True)) == 0
    assert store.calls[-1][1][1] == "source"
    assert subject.cmd_source_list(args()) == 0
    assert emitted[-1] == store.sources
    assert subject.cmd_roster_list(args()) == 0
    assert "agent\tAgent\teng\tUseful" in capsys.readouterr().out

    monkeypatch.setattr(
        subject,
        "create_roster_diff",
        lambda _store: {"snapshot_id": "snap", "diff": {"added": []}},
    )
    assert subject.cmd_roster_diff(args(json=True)) == 0
    assert emitted[-1]["snapshot_id"] == "snap"
    assert subject.cmd_roster_diff(args()) == 0
    assert emitted[-1] == {"added": []}
    actions = []
    monkeypatch.setattr(subject, "approve_snapshot", lambda *_args: actions.append("approve"))
    monkeypatch.setattr(subject, "activate_snapshot", lambda *_args: actions.append("activate"))
    assert subject.cmd_roster_approve(args()) == 0
    assert subject.cmd_roster_activate(args()) == 0
    assert actions == ["approve", "activate"]

    monkeypatch.setattr(subject, "pre_narrow", lambda query, catalog, limit: (catalog, [0.75]))
    assert subject._search("review", 3)[0]["score"] == 0.75
    monkeypatch.setattr(
        subject,
        "_search",
        lambda *_args: [{**store.catalog[0], "score": 0.75}],
    )
    assert subject.cmd_search(args()) == 0
    assert "0.8\tagent" in capsys.readouterr().out
    assert subject.cmd_search(args(json=True)) == 0
    assert emitted[-1][0]["slug"] == "agent"
    monkeypatch.setattr(
        subject,
        "explain_route",
        lambda *values, **kwargs: {"args": values[:2], "limit": kwargs["limit"]},
    )
    assert subject.cmd_explain(args()) == 0
    assert emitted[-1]["args"] == ("session", "review")


def test_route_empty_selected_companion_and_json(monkeypatch, capsys):
    import agency_runtime.core.selector.candidate_narrow as narrow
    import agency_runtime.core.selector.pipeline as pipeline

    store = Store()
    monkeypatch.setattr(subject, "_store", lambda: store)
    assert subject.cmd_route(args()) == 1
    assert "No active agents" in capsys.readouterr().err
    store.catalog = [{"slug": "agent"}]
    routing = {
        "selected_ids": ["agent"],
        "confidence": 0.8,
        "provider": "judge",
        "trace_id": "trace",
        "companion_actions": ["security"],
    }
    monkeypatch.setattr(pipeline, "route", lambda *_a, **_kw: routing)
    monkeypatch.setattr(narrow, "pre_narrow", lambda *_a, **_kw: (store.catalog, [0.9]))
    assert subject.cmd_route(args()) == 0
    output = capsys.readouterr().out
    assert "selected: agent" in output and "companion actions: security" in output
    routing.clear()
    emitted = []
    monkeypatch.setattr(subject, "_print_json", emitted.append)
    assert subject.cmd_route(args()) == 0
    assert "selected: none" in capsys.readouterr().out
    assert subject.cmd_route(args(json=True)) == 0
    assert emitted[-1]["candidates"][0]["score"] == 0.9


@pytest.mark.parametrize(
    ("command", "module_name", "function_name", "report"),
    [
        (
            subject.cmd_eval_delegation,
            "agency_runtime.core.evals.delegation",
            "run_delegation_eval",
            {
                "passed": False,
                "passed_count": 1,
                "failed_count": 1,
                "cases": [
                    {"passed": True, "name": "ok", "detail": "detail"},
                    {"passed": False, "name": "bad", "error": "failure"},
                ],
            },
        ),
        (
            subject.cmd_eval_routing,
            "agency_runtime.core.evals.routing",
            "run_routing_eval",
            {
                "passed": False,
                "corpus": {
                    "version": "v1",
                    "routing_cases": 1,
                    "policy_cases": 2,
                    "delegation_cases": 3,
                },
                "gates": [
                    {
                        "passed": False,
                        "area": "routing",
                        "metric": "accuracy",
                        "value": 0.5,
                        "operator": ">=",
                        "threshold": 0.9,
                    }
                ],
            },
        ),
        (
            subject.cmd_smoke,
            "agency_runtime.core.smoke",
            "run_smoke",
            {
                "passed": False,
                "passed_count": 1,
                "failed_count": 1,
                "skipped_count": 1,
                "checks": [
                    {"status": "pass", "name": "ok", "detail": "detail"},
                    {"status": "skip", "name": "skip", "error": "offline"},
                    {"status": "custom", "name": "other"},
                ],
            },
        ),
    ],
)
def test_eval_and_smoke_human_and_json(
    monkeypatch, capsys, command, module_name, function_name, report
):
    import importlib

    module = importlib.import_module(module_name)
    if function_name == "run_delegation_eval":
        monkeypatch.setattr(module, function_name, lambda: report)
    else:
        monkeypatch.setattr(module, function_name, lambda **_kwargs: report)
    emitted = []
    monkeypatch.setattr(subject, "_print_json", emitted.append)
    assert command(args()) == 1
    assert capsys.readouterr().out
    assert command(args(json=True)) == 1
    assert emitted[-1] == report


def test_database_commands_json_human_deleted_and_empty(monkeypatch, capsys):
    store = Store()
    emitted = []
    monkeypatch.setattr(subject, "_store", lambda: store)
    monkeypatch.setattr(subject, "_print_json", emitted.append)
    assert subject.cmd_db_stats(args(json=True)) == 0
    assert emitted[-1]["db_path"] == "agency.db"
    assert subject.cmd_db_stats(args()) == 0
    assert "agents\t3" in capsys.readouterr().out
    assert subject.cmd_db_trim(args(json=True, dry_run=True)) == 0
    assert emitted[-1]["dry_run"] is True
    assert subject.cmd_db_trim(args(dry_run=True)) == 0
    assert "DRY RUN" in capsys.readouterr().out
    original = store.trim_runtime_tables
    store.trim_runtime_tables = lambda **kwargs: {
        **original(**kwargs),
        "tables": {"empty": {"deleted": 0}},
    }
    assert subject.cmd_db_trim(args()) == 0
    assert "No rows matched" in capsys.readouterr().out
