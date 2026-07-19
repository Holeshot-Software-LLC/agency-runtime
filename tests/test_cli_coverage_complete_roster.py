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
        "scan_id": "scan",
        "session_id": "session",
        "slug": "agent",
        "snapshot_id": "snapshot",
        "task": "review",
        "target_version": "sha256:old",
        "expected_current_version": "sha256:new",
        "expected_current_hash": "current-hash",
        "history_cursor": "",
        "pending_cursor": "",
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

    def get_active_roster(self):
        return [
            {
                "agent_slug": item["slug"],
                "name": item.get("name", ""),
                "division": item.get("division", ""),
            }
            for item in self.catalog
        ]

    def rollback_agent_revision(self, *values, **kwargs):
        self.calls.append(("rollback", values, kwargs))
        return {
            "agent_slug": values[0],
            "version": values[1],
            "hash": "restored-hash",
        }

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
    assert (
        subject._auto_approve_preflight(
            auto_approve=True,
            quarantined=["one"],
            errors=[],
            outcomes=[
                {"status": "candidate", "slug": "one"},
                {"status": "quarantined", "slug": "unsafe"},
            ],
        )
        == 2
    )
    assert emitted[-1]["outcomes"] == [{"status": "quarantined", "slug": "unsafe"}]

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


def test_sync_inference_audit_and_failure_edges(monkeypatch):
    policy = SimpleNamespace(required=True)
    calls = []
    reconciliations = []
    monkeypatch.setattr(
        subject,
        "quarantine_manifest_import",
        lambda *_args, **kwargs: (
            calls.append(kwargs) or (["candidate"], [{"status": "candidate", "scan_id": "scan-1"}])
        ),
    )
    monkeypatch.setattr(
        subject,
        "audit_candidates_with_policy",
        lambda *_args: [{"candidate_id": "candidate", "verdict": "failed"}],
    )
    monkeypatch.setattr(
        subject,
        "reconcile_manifest_remediation_resolutions",
        lambda *_args, **kwargs: reconciliations.append(kwargs),
    )
    candidate_ids, outcomes, ready = subject._quarantine_manifest_with_policy(
        [{"slug": "candidate"}],
        [object()],
        "source",
        object(),
        policy,
    )
    assert candidate_ids == ["candidate"]
    assert outcomes == [{"status": "candidate", "scan_id": "scan-1"}]
    assert ready is False
    assert calls == [{"require_inference": True}]
    assert reconciliations == [
        {
            "candidate_ids": ["candidate"],
            "audits": [{"candidate_id": "candidate", "verdict": "failed"}],
            "scan_id": "scan-1",
        }
    ]

    class ManifestCandidates(list):
        outcomes = (object(),)

    monkeypatch.setattr(
        subject,
        "download_from_source",
        lambda _url: ManifestCandidates([{"slug": "candidate"}]),
    )
    monkeypatch.setattr(
        subject,
        "_quarantine_manifest_with_policy",
        lambda *_args, **_kwargs: (
            ["candidate"],
            [{"status": "candidate"}],
            False,
        ),
    )
    quarantined, errors = subject._collect_sync_candidates(
        [{"id": "source", "url": "source"}],
        object(),
        dry_run=False,
        audit_policy=policy,
    )
    assert quarantined == ["candidate"]
    assert "degraded or failed" in errors[0]["error"]

    monkeypatch.setattr(subject, "download_from_source", lambda _url: [{"slug": "candidate"}])
    monkeypatch.setattr(subject, "validate_agent", lambda _agent: (True, ""))
    monkeypatch.setattr(
        subject,
        "_quarantine_agent_with_policy",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("quarantine failed")),
    )
    quarantined, errors = subject._collect_sync_candidates(
        [{"id": "source", "url": "source"}],
        object(),
        dry_run=False,
        audit_policy=policy,
    )
    assert quarantined == []
    assert errors == [
        {
            "source": "source",
            "agent": "candidate",
            "error": "quarantine failed",
        }
    ]


def test_sync_non_inference_and_manifest_collection_edges(monkeypatch):
    monkeypatch.setattr(
        subject,
        "quarantine_manifest_import",
        lambda *_args, **_kwargs: (["candidate"], [{"status": "candidate"}]),
    )
    assert subject._quarantine_manifest_with_policy(
        [{"slug": "candidate"}],
        [object()],
        "source",
        object(),
        None,
    ) == (["candidate"], [{"status": "candidate"}], True)

    monkeypatch.setattr(
        subject,
        "quarantine_candidate",
        lambda agent, source_id, _store, **_kwargs: f"{source_id}:{agent['slug']}",
    )
    assert subject._quarantine_agent_with_policy(
        {"slug": "candidate"},
        "source",
        object(),
        None,
    ) == ("source:candidate", True)
    policy = SimpleNamespace(required=True)
    monkeypatch.setattr(
        subject,
        "audit_candidates_with_policy",
        lambda *_args: [{"verdict": "failed"}],
    )
    assert subject._quarantine_agent_with_policy(
        {"slug": "candidate"},
        "source",
        object(),
        policy,
    ) == ("source:candidate", False)

    monkeypatch.setattr(subject, "download_from_source", lambda _url: [])
    assert (
        subject._collect_sync_candidates(
            [{"id": "empty", "url": "empty"}],
            object(),
            dry_run=False,
        )[0]
        == []
    )

    class Outcome:
        def public_dict(self):
            return {"status": "candidate", "slug": "candidate"}

    class ManifestCandidates(list):
        outcomes = (Outcome(),)

    manifest = ManifestCandidates([{"slug": "candidate"}])
    sink = []
    monkeypatch.setattr(subject, "download_from_source", lambda _url: manifest)
    monkeypatch.setattr(subject, "validate_agent", lambda _agent: (True, ""))
    quarantined, errors = subject._collect_sync_candidates(
        [{"id": "source", "url": "source"}],
        object(),
        dry_run=True,
        outcome_sink=sink,
    )
    assert quarantined == ["candidate"]
    assert errors == []
    assert sink == [{"status": "candidate", "slug": "candidate"}]

    monkeypatch.setattr(
        subject,
        "_quarantine_manifest_with_policy",
        lambda *_args, **_kwargs: (
            ["candidate"],
            [{"status": "candidate"}],
            True,
        ),
    )
    quarantined, errors = subject._collect_sync_candidates(
        [{"id": "source", "url": "source"}],
        object(),
        dry_run=False,
    )
    assert quarantined == ["candidate"]
    assert errors == []

    monkeypatch.setattr(
        subject,
        "_quarantine_manifest_with_policy",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("manifest failed")),
    )
    quarantined, errors = subject._collect_sync_candidates(
        [{"id": "source", "url": "source"}],
        object(),
        dry_run=False,
    )
    assert quarantined == []
    assert errors[0]["error"] == "manifest failed"

    monkeypatch.setattr(subject, "download_from_source", lambda _url: [{"slug": "candidate"}])
    monkeypatch.setattr(
        subject,
        "_quarantine_agent_with_policy",
        lambda *_args, **_kwargs: ("candidate", False),
    )
    quarantined, errors = subject._collect_sync_candidates(
        [{"id": "source", "url": "source"}],
        object(),
        dry_run=False,
    )
    assert quarantined == ["candidate"]
    assert "degraded or failed" in errors[0]["error"]


def test_sync_successful_preflight_and_outcome_reporting(monkeypatch):
    emitted = []
    monkeypatch.setattr(subject, "_print_json", emitted.append)
    assert (
        subject._auto_approve_preflight(
            auto_approve=True,
            quarantined=["candidate"],
            errors=[],
        )
        is None
    )
    monkeypatch.setattr(
        subject,
        "create_roster_diff",
        lambda *_args, **_kwargs: {"snapshot_id": "snapshot", "diff": {}},
    )
    assert (
        subject._complete_sync(
            args(),
            object(),
            ["candidate"],
            [],
            outcomes=[{"status": "candidate"}],
        )
        == 0
    )
    assert emitted[-1] == {"outcomes": [{"status": "candidate"}]}


def test_sync_inference_activation_rollback_and_upstream_degraded(
    monkeypatch,
    capsys,
):
    actions = []
    emitted = []
    monkeypatch.setattr(
        subject,
        "create_roster_diff",
        lambda *_args, **_kwargs: {"snapshot_id": "snapshot", "diff": {}},
    )
    monkeypatch.setattr(
        subject,
        "approve_snapshot",
        lambda *_args, **kwargs: actions.append(("approve", kwargs)),
    )
    monkeypatch.setattr(
        subject,
        "activate_snapshot",
        lambda *_args, **kwargs: actions.append(("activate", kwargs)),
    )
    monkeypatch.setattr(subject, "_print_json", emitted.append)
    assert (
        subject._complete_sync(
            args(auto_approve=True, source_revision="upstream"),
            object(),
            ["candidate"],
            [],
            require_inference=True,
        )
        == 0
    )
    assert actions == [
        ("approve", {"require_inference": True}),
        ("activate", {"require_inference": True}),
    ]

    store = Store()
    monkeypatch.setattr(subject, "_store", lambda: store)
    assert subject.cmd_roster_rollback(args(json=False)) == 0
    assert "Rolled back agent" in capsys.readouterr().out

    store.sources = [{"id": "source", "url": "https://example.invalid/roster.json"}]
    monkeypatch.setattr(subject, "load_config", lambda: object())
    monkeypatch.setattr(
        subject,
        "import_upstream_source",
        lambda *_args, **_kwargs: {"audit_ready": False, "candidate_count": 1},
    )
    assert (
        subject.cmd_roster_upstream_import(
            args(
                source_id="",
                source_revision="revision",
                dry_run=False,
            )
        )
        == 2
    )
    assert emitted[-1]["ok"] is False
    assert "degraded or failed" in emitted[-1]["errors"][0]["error"]


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


def test_sync_command_auto_approve_rejects_partial_manifest_outcomes(monkeypatch):
    store = Store()
    store.sources = [{"id": "source", "url": "source", "trusted_for_auto_approve": 1}]
    emitted = []
    monkeypatch.setattr(subject, "_store", lambda: store)
    monkeypatch.setattr(subject, "_print_json", emitted.append)

    def collect(*_args, outcome_sink, **_kwargs):
        outcome_sink.extend(
            [
                {"status": "candidate", "slug": "safe"},
                {"status": "quarantined", "slug": "unsafe"},
            ]
        )
        return ["candidate-id"], []

    monkeypatch.setattr(subject, "_collect_sync_candidates", collect)
    monkeypatch.setattr(
        subject,
        "_complete_sync",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("partial scans must fail before snapshot activation")
        ),
    )

    assert subject.cmd_sync(args(auto_approve=True)) == 2
    assert emitted[-1]["outcomes"] == [{"status": "quarantined", "slug": "unsafe"}]


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
    monkeypatch.setattr(
        subject,
        "_activation_rows",
        lambda: (
            "config",
            [
                {
                    "slug": "agent",
                    "name": "Agent",
                    "division": "eng",
                    "enabled": True,
                    "protected": False,
                }
            ],
        ),
    )
    assert subject.cmd_roster_list(args()) == 0
    assert "agent\tAgent\teng" in capsys.readouterr().out

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
    monkeypatch.setattr(
        subject,
        "approve_snapshot",
        lambda *_args, **_kwargs: actions.append("approve"),
    )
    monkeypatch.setattr(
        subject,
        "activate_snapshot",
        lambda *_args, **_kwargs: actions.append("activate"),
    )
    assert subject.cmd_roster_approve(args()) == 0
    assert subject.cmd_roster_activate(args()) == 0
    assert actions == ["approve", "activate"]
    monkeypatch.setattr(subject, "list_source_scans", lambda *_args, **_kwargs: [{"id": "scan"}])
    assert subject.cmd_roster_scans(args(limit=10)) == 0
    assert emitted[-1] == [{"id": "scan"}]
    remediation_arguments = []
    monkeypatch.setattr(
        subject,
        "remediation_queue_snapshot",
        lambda *_args, **kwargs: (
            remediation_arguments.append(kwargs)
            or {
                "schema_version": "agency.roster.remediation_queue.v2",
                "pending": [{"receipt": {"activation_eligible": False}}],
                "pending_count": 1,
                "history": [],
                "history_count": 0,
                "pending_has_more": False,
                "history_has_more": False,
                "next_pending_cursor": "",
                "next_history_cursor": "",
            }
        ),
    )
    assert (
        subject.cmd_roster_remediation_queue(
            args(
                limit=10,
                pending_cursor="pending-event",
                history_cursor="history-event",
            )
        )
        == 0
    )
    assert remediation_arguments == [
        {
            "limit": 10,
            "pending_cursor": "pending-event",
            "history_cursor": "history-event",
        }
    ]
    assert emitted[-1]["pending"] == [{"receipt": {"activation_eligible": False}}]
    monkeypatch.setattr(
        subject,
        "create_retirement_diff",
        lambda *_args, **_kwargs: {
            "snapshot_id": "retirement",
            "diff": {"removed": ["agent"]},
        },
    )
    assert subject.cmd_roster_retire(args(json=True)) == 0
    assert emitted[-1]["snapshot_id"] == "retirement"
    assert subject.cmd_roster_retire(args(json=False)) == 0
    assert "Approve with: agency roster approve retirement" in capsys.readouterr().out
    assert subject.cmd_roster_rollback(args(json=True)) == 0
    assert emitted[-1]["version"] == "sha256:old"
    assert store.calls[-1][0] == "rollback"

    monkeypatch.setattr(
        subject,
        "capture_routing_snapshot",
        lambda _store: SimpleNamespace(catalog=store.catalog, config=object()),
    )
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


def test_roster_and_activation_command_failures_are_bounded_and_machine_readable(
    monkeypatch,
    capsys,
):
    emitted = []
    rows = [
        {
            "slug": "disabled",
            "name": "Disabled",
            "division": "eng",
            "enabled": False,
            "protected": False,
        },
        {
            "slug": "enabled",
            "name": "Enabled",
            "division": "eng",
            "enabled": True,
            "protected": False,
        },
    ]
    monkeypatch.setattr(subject, "_print_json", emitted.append)
    monkeypatch.setattr(subject, "_activation_rows", lambda *_args, **_kwargs: ("config", rows))

    assert subject.cmd_roster_list(args()) == 0
    output = capsys.readouterr().out
    assert "enabled\tEnabled\teng" in output
    assert "disabled\tDisabled\teng" not in output

    monkeypatch.setattr(
        subject,
        "_activation_rows",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("state\nrefused")),
    )
    assert subject.cmd_agents_list(args(json=True)) == 1
    assert emitted[-1] == {
        "ok": False,
        "exit_code": 1,
        "error": "state\\u000arefused",
        "agents": [],
    }
    assert subject.cmd_agents_list(args(json=False)) == 1
    assert "state\\u000arefused" in capsys.readouterr().out

    monkeypatch.setattr(
        subject,
        "_set_agent_enabled",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("toggle refused")),
    )
    assert subject.cmd_agent_enable(args(slug="agent")) == 1
    assert subject.cmd_agent_disable(args(slug="agent")) == 1
    assert capsys.readouterr().out.count("toggle refused") == 2


def test_search_route_and_explain_contain_operation_failures(
    monkeypatch,
    capsys,
):
    emitted = []
    monkeypatch.setattr(subject, "_runtime_enabled", lambda: True)
    monkeypatch.setattr(subject, "_print_json", emitted.append)
    monkeypatch.setattr(
        subject,
        "_search",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("search refused")),
    )

    assert subject.cmd_search(args(json=True)) == 1
    assert emitted[-1]["error"] == "search refused"
    assert emitted[-1]["agents"] == []
    assert subject.cmd_search(args(json=False)) == 1
    assert "search refused" in capsys.readouterr().err

    monkeypatch.setattr(
        subject,
        "_routing_operation",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("routing refused")),
    )
    assert subject.cmd_route(args(json=True)) == 1
    assert emitted[-1]["routing"] is None
    assert subject.cmd_route(args(json=False)) == 1
    assert "routing refused" in capsys.readouterr().err
    assert subject.cmd_explain(args()) == 1
    assert emitted[-1]["signals"] == {}


def test_route_and_explain_reject_empty_or_impossible_operations(monkeypatch):
    emitted = []
    monkeypatch.setattr(subject, "_runtime_enabled", lambda: True)
    monkeypatch.setattr(subject, "_print_json", emitted.append)
    monkeypatch.setattr(
        subject,
        "_routing_operation",
        lambda **_kwargs: SimpleNamespace(
            store=object(),
            snapshot=SimpleNamespace(catalog=[], config=object()),
            receipt=None,
        ),
    )

    assert subject.cmd_route(args(json=True)) == 1
    assert emitted[-1]["error"] == "No active agents available"

    monkeypatch.setattr(
        subject,
        "_routing_operation",
        lambda **_kwargs: SimpleNamespace(store=None, snapshot=None, receipt=None),
    )
    with pytest.raises(RuntimeError, match="no direct or brokered result"):
        subject.cmd_route(args())
    with pytest.raises(RuntimeError, match="no direct or brokered result"):
        subject.cmd_explain(args())


def test_default_policy_operation_uses_one_direct_routing_snapshot(monkeypatch):
    runtime_store = object()
    config = object()
    catalog = [{"slug": "reviewer"}]
    policy = {"actions": {}, "division_anchors": {}}
    dependencies = subject.RosterDependencies(
        store_factory=lambda: runtime_store,
        emit_json=lambda _value: None,
        policy_loader=lambda: pytest.fail("default operation must use the bound config policy"),
    )
    monkeypatch.setattr(subject, "DEFAULT_DEPENDENCIES", dependencies)
    monkeypatch.setattr(
        subject,
        "capture_routing_snapshot",
        lambda store: (
            SimpleNamespace(config=config, catalog=catalog)
            if store is runtime_store
            else pytest.fail("unexpected Store")
        ),
    )
    monkeypatch.setattr(
        subject,
        "policy_path_for_config",
        lambda received: "policy.yaml" if received is config else pytest.fail("unexpected config"),
    )
    monkeypatch.setattr(
        subject,
        "load_policy",
        lambda path: policy if path == "policy.yaml" else pytest.fail("unexpected policy path"),
    )

    assert subject._policy_operation(dependencies) == (policy, {"reviewer"})


def test_policy_command_contains_direct_or_brokered_failures(monkeypatch, capsys):
    emitted = []
    monkeypatch.setattr(subject, "_print_json", emitted.append)

    def fail(dependencies):
        assert dependencies.store_factory is subject._store
        assert dependencies.emit_json is subject._print_json
        assert dependencies.policy_loader is subject.load_policy
        raise RuntimeError("policy refused")

    monkeypatch.setattr(subject, "_policy_operation", fail)
    assert subject.cmd_policy(args(json=True)) == 1
    assert emitted[-1] == {
        "ok": False,
        "exit_code": 1,
        "error": "policy refused",
        "valid": False,
        "actions": {},
        "division_anchors": {},
    }
    assert subject.cmd_policy(args(json=False)) == 1
    assert "policy refused" in capsys.readouterr().err
