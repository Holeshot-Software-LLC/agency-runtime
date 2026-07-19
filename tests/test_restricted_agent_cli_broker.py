"""Adversarial coverage for restricted-token agent and CLI brokerage."""

from __future__ import annotations

import hashlib
import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.cli import agent_control_broker as broker
from agency_runtime.cli import (
    config_commands,
    delegation_commands,
    install_commands,
    roster_commands,
)
from agency_runtime.cli import main as cli_main
from agency_runtime.core import config as config_module
from agency_runtime.core import dashboard_runtime, runtime_control
from agency_runtime.core.roster.ingress import (
    MAX_LIST_ITEMS,
    MAX_METADATA_TEXT_BYTES,
)
from agency_runtime.core.roster.selector_projection import (
    selector_roster_projection,
    ui_roster_projection,
)
from agency_runtime.core.store.roster import RosterStoreMixin
from agency_runtime.core.windows_acl import RestrictedWindowsTokenError
from agency_runtime.server import dashboard as dashboard_server


def _absolute_config_path(name: str = "agency.yaml") -> str:
    return str((Path.cwd() / name).resolve())


def _revision(character: str = "a") -> str:
    return "sha256:" + (character * 64)


def _store_path(name: str = "agency.db") -> str:
    return str((Path.cwd() / name).resolve())


def _row(
    slug: str,
    *,
    enabled: bool = True,
    protected: bool | None = None,
) -> dict[str, Any]:
    row = selector_roster_projection(
        {
            "agent_slug": slug,
            "name": slug.replace("-", " ").title(),
            "division": "engineering",
            "description": f"Specialist for {slug}",
            "categories": ["engineering"],
            "capabilities": ["review"],
        },
        {slug} if not enabled else (),
    )
    if protected is not None:
        row["protected"] = protected
    return row


def _page(
    rows: list[dict[str, Any]],
    *,
    total: int | None = None,
    enabled_count: int | None = None,
    limit: int = 100,
    truncated: bool = False,
    config_path: str | None = None,
    config_revision: str | None = None,
    roster_revision: str | None = None,
    store_path: str | None = None,
    filter_slug: str | None = None,
) -> dict[str, Any]:
    total_count = len(rows) if total is None else total
    enabled_total = (
        sum(bool(row["enabled"]) for row in rows) if enabled_count is None else enabled_count
    )
    value: dict[str, Any] = {
        "agents": rows,
        "count": len(rows),
        "total_count": total_count,
        "enabled_count": enabled_total,
        "disabled_count": total_count - enabled_total,
        "limit": limit,
        "truncated": truncated,
        "next_cursor": rows[-1]["agent_slug"] if truncated else None,
        "config_path": config_path or _absolute_config_path(),
        "config_revision": config_revision or _revision(),
        "roster_revision": roster_revision or ("b" * 64),
        "store_path": store_path or _store_path(),
        "environment_overrides": {},
        "projection": "selector",
    }
    if filter_slug is not None:
        value["filter_slug"] = filter_slug
    return value


def _activation_row(
    slug: str,
    *,
    enabled: bool = True,
    protected: bool | None = None,
) -> dict[str, Any]:
    row = _row(slug, enabled=enabled, protected=protected)
    return {key: row[key] for key in ("agent_slug", "name", "division", "enabled", "protected")}


def _activation_page(
    rows: list[dict[str, Any]],
    **kwargs: Any,
) -> dict[str, Any]:
    page = _page(rows, **kwargs)
    page["projection"] = "activation"
    return page


def _raise_restricted(*_args: Any, **_kwargs: Any) -> Any:
    raise RestrictedWindowsTokenError("restricted process token")


def _catalog() -> list[dict[str, Any]]:
    return [
        {
            "slug": "alpha-reviewer",
            "name": "Alpha Reviewer",
            "description": "Reviews implementation changes",
            "division": "engineering",
            "categories": ["engineering"],
            "capabilities": ["review"],
        }
    ]


def _operation_snapshot() -> dict[str, Any]:
    return {
        "config_path": _absolute_config_path(),
        "config_revision": _revision(),
        "store_path": _store_path(),
        "roster_revision": "b" * 64,
        "environment_overrides": {},
    }


def _policy_response(*, active_slugs: Any = None) -> dict[str, Any]:
    policy = {"actions": {}, "division_anchors": {}}
    revision = hashlib.sha256(
        json.dumps(
            policy,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "agency.policy_snapshot.v1",
        "policy": policy,
        "active_slugs": ["alpha-reviewer"] if active_slugs is None else active_slugs,
        "operation_snapshot": _operation_snapshot(),
        "policy_revision": revision,
    }


def _search_response(agents: list[Any]) -> dict[str, Any]:
    return {
        "schema_version": "agency.search.v1",
        "query": "review",
        "agents": agents,
        "count": len(agents),
        "operation_snapshot": _operation_snapshot(),
    }


def _search_agent(**overrides: Any) -> dict[str, Any]:
    return {
        "slug": "alpha-reviewer",
        "name": "Alpha Reviewer",
        "division": "engineering",
        "description": "Reviews implementation changes",
        "score": 0.9,
        **overrides,
    }


@pytest.mark.parametrize(
    ("invoke", "message"),
    [
        (lambda: broker._bounded_integer(True, "count"), "invalid count"),
        (lambda: broker._operation_identity(None), "operation identity"),
        (
            lambda: broker._operation_identity(
                {**_operation_snapshot(), "roster_revision": "invalid"}
            ),
            "roster revision",
        ),
        (
            lambda: broker._bounded_route_argument(
                None,
                field="task",
                maximum=10,
            ),
            "invalid task",
        ),
        (
            lambda: broker._bounded_metadata_text(None, maximum=10, label="name"),
            "must be text",
        ),
        (
            lambda: broker._bounded_metadata_text("bad\x00", maximum=10, label="name"),
            "broker contract",
        ),
        (
            lambda: broker._bounded_taxonomy(["review", "review"], label="capabilities"),
            "taxonomy exceeds",
        ),
        (
            lambda: broker._agent_row(
                {key: value for key, value in _row("alpha-reviewer").items() if key != "name"}
            ),
            "unexpected fields",
        ),
        (
            lambda: broker._agent_row({**_row("alpha-reviewer"), "agent_slug": 7}),
            "invalid slug",
        ),
    ],
)
def test_broker_scalar_and_row_boundaries_fail_closed(
    invoke: Any,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        invoke()


def test_broker_agent_page_rejects_non_object() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        broker._agent_page(None)


def test_broker_agent_row_rejects_noncanonical_derived_projection() -> None:
    row = _row("alpha-reviewer")
    row["supported_execution_hosts"] = ["codex"]

    with pytest.raises(ValueError, match="canonical selector projection"):
        broker._agent_row(row)


def test_broker_agent_row_ignores_future_non_text_template_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_projection = broker.selector_roster_projection

    def projection(agent: dict[str, Any], disabled: Any = ()) -> dict[str, Any]:
        return {**original_projection(agent, disabled), "opaque_future_field": 0}

    monkeypatch.setattr(broker, "selector_roster_projection", projection)
    row = {**_row("alpha-reviewer"), "opaque_future_field": 0}

    assert broker._agent_row(row)["slug"] == "alpha-reviewer"


def test_broker_agent_page_accepts_a_consistent_nonterminal_cursor() -> None:
    page = broker._agent_page(
        _page(
            [_row("alpha-reviewer")],
            total=2,
            enabled_count=2,
            truncated=True,
        )
    )

    assert page["truncated"] is True
    assert page["cursor"] == "alpha-reviewer"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"projection": "activation"}, "invalid projection"),
        (
            {"environment_overrides": {"store.db_path": "AGENCY_DB_PATH"}},
            "environment overrides",
        ),
        ({"agents": ()}, "agents list"),
        ({"next_cursor": 7}, "invalid cursor"),
        (
            {
                "agents": [],
                "count": 0,
                "total_count": 0,
                "enabled_count": 0,
                "disabled_count": 0,
                "truncated": True,
                "next_cursor": None,
            },
            "inconsistent pagination",
        ),
    ],
)
def test_broker_agent_page_rejects_remaining_malformed_shapes(
    mutation: dict[str, Any],
    message: str,
) -> None:
    value = _page([_row("alpha-reviewer")])
    value.update(mutation)

    with pytest.raises(ValueError, match=message):
        broker._agent_page(value)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (None, "activation entry"),
        (
            {**_activation_row("alpha-reviewer"), "agent_slug": 7},
            "invalid slug",
        ),
        (
            {**_activation_row("alpha-reviewer"), "enabled": 1},
            "invalid controls",
        ),
    ],
)
def test_broker_activation_row_rejects_remaining_malformed_shapes(
    value: Any,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        broker._activation_row(value)


def test_broker_activation_page_rejects_non_object() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        broker._activation_page(None)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"projection": "selector"}, "invalid projection"),
        ({"roster_revision": "invalid"}, "roster revision"),
        ({"agents": ()}, "agents list"),
        ({"count": 2}, "counts are inconsistent"),
        (
            {
                "agents": [],
                "count": 0,
                "total_count": 0,
                "enabled_count": 0,
                "disabled_count": 0,
                "truncated": True,
                "next_cursor": None,
            },
            "inconsistent pagination",
        ),
        ({"next_cursor": "alpha-reviewer"}, "terminal activation page"),
    ],
)
def test_broker_activation_page_rejects_remaining_malformed_shapes(
    mutation: dict[str, Any],
    message: str,
) -> None:
    value = _activation_page([_activation_row("alpha-reviewer")])
    value.update(mutation)

    with pytest.raises(ValueError, match=message):
        broker._activation_page(value)


def test_broker_reads_one_revision_stable_paginated_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [_activation_row(f"agent-{index:03d}") for index in range(101)]
    requests: list[str] = []

    def request(path: str) -> dict[str, Any]:
        requests.append(path)
        if len(requests) == 1:
            return _activation_page(rows[:100], total=101, enabled_count=101, truncated=True)
        return _activation_page(rows[100:], total=101, enabled_count=101)

    monkeypatch.setattr(broker, "dashboard_api_request", request)

    path, received = broker._broker_activation_rows()

    assert path == _absolute_config_path()
    assert [row["slug"] for row in received] == [row["agent_slug"] for row in rows]
    assert requests == [
        "/api/roster?limit=100&projection=activation",
        "/api/roster?limit=100&projection=activation&after=agent-099",
    ]


@pytest.mark.parametrize(
    "changed_page",
    [
        {"config_path": _absolute_config_path("other.yaml")},
        {"config_revision": _revision("c")},
        {"store_path": _store_path("other.db")},
        {"roster_revision": "d" * 64},
        {"total": 102, "enabled_count": 102},
        {"enabled_count": 100},
    ],
)
def test_broker_rejects_identity_changes_between_pages(
    monkeypatch: pytest.MonkeyPatch,
    changed_page: dict[str, Any],
) -> None:
    rows = [_activation_row(f"agent-{index:03d}") for index in range(101)]
    second_page = {"total": 101, "enabled_count": 101, **changed_page}
    responses = [
        _activation_page(rows[:100], total=101, enabled_count=101, truncated=True),
        _activation_page(rows[100:], **second_page),
    ]
    monkeypatch.setattr(broker, "dashboard_api_request", lambda _path: responses.pop(0))

    with pytest.raises(ValueError, match="changed identity"):
        broker._broker_activation_rows()


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (None, "JSON object"),
        ({**_row("alpha-reviewer"), "agent_slug": "Alpha-Reviewer"}, "canonical"),
        ({**_row("alpha-reviewer"), "name": 7}, "labels"),
        ({**_row("alpha-reviewer"), "categories": ("engineering",)}, "taxonomy"),
        ({**_row("alpha-reviewer"), "capabilities": ["review", 7]}, "taxonomy"),
        ({**_row("alpha-reviewer"), "enabled": 1}, "JSON booleans"),
        ({**_row("alpha-reviewer"), "protected": True}, "protection state"),
        ({**_row("chief-of-staff"), "protected": False}, "protection state"),
    ],
)
def test_broker_rejects_malformed_agent_rows(value: Any, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        broker._agent_row(value)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"config_path": "relative/agency.yaml"}, "config path"),
        ({"config_revision": "sha256:not-a-digest"}, "config revision"),
        ({"store_path": "relative/agency.db"}, "store path"),
        ({"roster_revision": "not-a-digest"}, "roster revision"),
        ({"count": 2}, "counts are inconsistent"),
        ({"enabled_count": 2, "disabled_count": 0}, "counts are inconsistent"),
        ({"truncated": "yes"}, "truncation state"),
        ({"next_cursor": "alpha-reviewer"}, "terminal agent page"),
    ],
)
def test_broker_rejects_malformed_page_metadata(
    mutation: dict[str, Any],
    message: str,
) -> None:
    value = _page([_row("alpha-reviewer")])
    value.update(mutation)

    with pytest.raises(ValueError, match=message):
        broker._agent_page(value)


@pytest.mark.parametrize("second_slug", ["agent-099", "agent-005"])
def test_broker_rejects_duplicate_or_unordered_paginated_slugs(
    monkeypatch: pytest.MonkeyPatch,
    second_slug: str,
) -> None:
    first_rows = [_activation_row(f"agent-{index:03d}") for index in range(100)]
    responses = [
        _activation_page(first_rows, total=101, enabled_count=101, truncated=True),
        _activation_page([_activation_row(second_slug)], total=101, enabled_count=101),
    ]
    monkeypatch.setattr(broker, "dashboard_api_request", lambda _path: responses.pop(0))

    with pytest.raises(ValueError, match="duplicate or unordered"):
        broker._broker_activation_rows()


def test_broker_rejects_a_short_nonterminal_activation_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        broker,
        "dashboard_api_request",
        lambda _path: _activation_page(
            [_activation_row("agent-000")],
            total=2,
            enabled_count=2,
            truncated=True,
        ),
    )

    with pytest.raises(ValueError, match="unexpectedly short"):
        broker._broker_activation_rows()


def test_broker_caps_nonterminating_activation_pagination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(broker, "_MAX_AGENTS", 1)
    monkeypatch.setattr(broker, "_PAGE_SIZE", 1)
    monkeypatch.setattr(
        broker,
        "dashboard_api_request",
        lambda _path: _activation_page(
            [_activation_row("agent-000")],
            total=1,
            enabled_count=1,
            limit=1,
            truncated=True,
        ),
    )

    with pytest.raises(ValueError, match="pagination exceeded"):
        broker._broker_activation_rows()


def test_broker_rejects_pages_that_accumulate_past_the_declared_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = [_activation_row(f"agent-{index:03d}") for index in range(100)]
    responses = [
        _activation_page(first, total=100, enabled_count=100, truncated=True),
        _activation_page(
            [_activation_row("agent-100")],
            total=100,
            enabled_count=100,
        ),
    ]
    monkeypatch.setattr(broker, "dashboard_api_request", lambda _path: responses.pop(0))

    with pytest.raises(ValueError, match="exceed their bounded total"):
        broker._broker_activation_rows()


def test_broker_rejects_terminal_page_short_of_declared_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        broker,
        "dashboard_api_request",
        lambda _path: _activation_page(
            [_activation_row("agent-000")],
            total=2,
            enabled_count=2,
        ),
    )

    with pytest.raises(ValueError, match="do not match their total count"):
        broker._broker_activation_rows()


def test_broker_rejects_rows_that_disagree_with_enabled_totals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        broker,
        "dashboard_api_request",
        lambda _path: _activation_page(
            [_activation_row("agent-000")],
            total=1,
            enabled_count=0,
        ),
    )

    with pytest.raises(ValueError, match="disagree with their enabled counts"):
        broker._broker_activation_rows()


@pytest.mark.parametrize(
    ("invoke", "message"),
    [
        (
            lambda: broker.broker_explain_selection(
                session_id="session",
                task="review",
                limit=0,
            ),
            "invalid limit",
        ),
        (
            lambda: broker.broker_search_agents(query="review", limit=0),
            "invalid limit",
        ),
    ],
)
def test_broker_route_and_search_reject_invalid_limits_before_io(
    monkeypatch: pytest.MonkeyPatch,
    invoke: Any,
    message: str,
) -> None:
    monkeypatch.setattr(
        broker,
        "dashboard_api_request",
        lambda *_args, **_kwargs: pytest.fail("invalid request reached dashboard I/O"),
    )

    with pytest.raises(ValueError, match=message):
        invoke()


@pytest.mark.parametrize("operation", ["route", "policy", "search"])
def test_broker_read_operations_reject_non_object_responses(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    monkeypatch.setattr(broker, "dashboard_api_request", lambda *_args, **_kwargs: None)

    with pytest.raises(ValueError, match="response is invalid"):
        if operation == "route":
            broker.broker_explain_selection(session_id="session", task="review", limit=1)
        elif operation == "policy":
            broker.broker_policy_snapshot()
        else:
            broker.broker_search_agents(query="review", limit=1)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"active_slugs": None}, "invalid active slugs"),
        ({"active_slugs": [7]}, "invalid active slugs"),
        (
            {"active_slugs": ["alpha-reviewer", "alpha-reviewer"]},
            "invalid active slugs",
        ),
        (
            {"active_slugs": ["beta-reviewer", "alpha-reviewer"]},
            "not ordered",
        ),
        ({"policy_revision": "invalid"}, "invalid policy revision"),
    ],
)
def test_broker_policy_rejects_remaining_malformed_evidence(
    monkeypatch: pytest.MonkeyPatch,
    mutation: dict[str, Any],
    message: str,
) -> None:
    response = _policy_response()
    response.update(mutation)
    monkeypatch.setattr(broker, "dashboard_api_request", lambda _path: response)

    with pytest.raises(ValueError, match=message):
        broker.broker_policy_snapshot()


@pytest.mark.parametrize(
    ("agents", "message"),
    [
        ([None], "search result is invalid"),
        ([_search_agent(slug=7)], "invalid slug"),
        ([_search_agent(score=True)], "search result is invalid"),
    ],
)
def test_broker_search_rejects_remaining_malformed_results(
    monkeypatch: pytest.MonkeyPatch,
    agents: list[Any],
    message: str,
) -> None:
    monkeypatch.setattr(
        broker,
        "dashboard_api_request",
        lambda *_args, **_kwargs: _search_response(agents),
    )

    with pytest.raises(ValueError, match=message):
        broker.broker_search_agents(query="review", limit=10)


def test_broker_lookup_rejects_an_empty_exact_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        broker,
        "dashboard_api_request",
        lambda _path: _page(
            [],
            total=0,
            enabled_count=0,
            limit=1,
            filter_slug="alpha-reviewer",
        ),
    )

    with pytest.raises(ValueError, match="not present in the active roster"):
        broker._lookup_agent("alpha-reviewer")


@pytest.mark.parametrize("value", [None, [7]])
def test_broker_disabled_agents_rejects_non_string_collections(value: Any) -> None:
    with pytest.raises(ValueError, match="invalid disabled agent"):
        broker._disabled_agents(value)


def test_broker_projects_compact_activation_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        _activation_row("alpha-reviewer"),
        _activation_row("beta-reviewer", enabled=False),
        _activation_row("chief-of-staff"),
    ]
    monkeypatch.setattr(
        broker,
        "dashboard_api_request",
        lambda _path: _activation_page(rows, enabled_count=2),
    )

    path, activation = broker.broker_activation_rows()
    assert path == _absolute_config_path()
    assert [row["slug"] for row in activation] == [
        "alpha-reviewer",
        "beta-reviewer",
        "chief-of-staff",
    ]
    assert activation[-1]["protected"] is True


def test_server_roster_revision_is_generation_bound_and_activation_independent() -> None:
    assert dashboard_server._roster_revision(4) == dashboard_server._roster_revision(4)
    assert dashboard_server._roster_revision(4) != dashboard_server._roster_revision(5)


def test_canonical_selector_projection_is_identical_for_direct_and_broker_paths() -> None:
    source = {
        "agent_slug": "alpha-reviewer",
        "name": "Alpha Reviewer",
        "division": "engineering",
        "description": "d" * MAX_METADATA_TEXT_BYTES,
        "categories": [f"category-{index}" for index in range(MAX_LIST_ITEMS)],
        "capabilities": [f"capability-{index}" for index in range(MAX_LIST_ITEMS)],
    }

    class DirectCatalog:
        def get_enabled_roster(self, **_kwargs: Any) -> list[dict[str, Any]]:
            return [source]

    direct = RosterStoreMixin.get_active_roster_as_catalog(DirectCatalog())  # type: ignore[arg-type]
    wire = selector_roster_projection(source)
    restricted = broker._agent_row(wire)

    assert direct == [restricted]
    assert direct[0]["description"] == source["description"]
    assert direct[0]["categories"] == source["categories"]
    assert direct[0]["capabilities"] == source["capabilities"]


def test_dashboard_roster_projection_contains_only_rendered_card_fields() -> None:
    projected = ui_roster_projection(
        {
            "agent_slug": "alpha-reviewer",
            "name": "Alpha Reviewer",
            "division": "engineering",
            "description": "must not reach the roster poll",
            "categories": ["must-not-leak"],
            "capabilities": [f"cap-{index}" for index in range(8)],
        }
    )

    assert set(projected) == {
        "agent_slug",
        "name",
        "division",
        "capabilities",
        "enabled",
        "protected",
    }
    assert projected["capabilities"] == ["cap-0", "cap-1", "cap-2", "cap-3"]


@pytest.mark.parametrize(
    ("enabled", "enabled_count"),
    [(True, 0), (False, 1)],
)
def test_exact_lookup_rejects_a_state_impossible_under_roster_totals(
    monkeypatch: pytest.MonkeyPatch,
    enabled: bool,
    enabled_count: int,
) -> None:
    monkeypatch.setattr(
        broker,
        "dashboard_api_request",
        lambda _path: _page(
            [_row("alpha-reviewer", enabled=enabled)],
            total=1,
            enabled_count=enabled_count,
            limit=1,
            filter_slug="alpha-reviewer",
        ),
    )

    with pytest.raises(ValueError, match="contradicts roster totals"):
        broker._lookup_agent("alpha-reviewer")


@pytest.mark.parametrize(
    ("before_enabled", "requested_enabled", "changed", "result_revision", "disabled"),
    [
        (True, False, True, _revision("c"), ["alpha-reviewer"]),
        (True, True, False, _revision(), []),
    ],
)
def test_broker_agent_toggle_accepts_exact_changed_and_noop_receipts(
    monkeypatch: pytest.MonkeyPatch,
    before_enabled: bool,
    requested_enabled: bool,
    changed: bool,
    result_revision: str,
    disabled: list[str],
) -> None:
    requests: list[tuple[str, str, Any]] = []

    def request(path: str, *, method: str = "GET", payload: Any = None) -> dict[str, Any]:
        requests.append((path, method, payload))
        if method == "GET":
            return _page(
                [_row("alpha-reviewer", enabled=before_enabled)],
                limit=1,
                filter_slug="alpha-reviewer",
            )
        return {
            "ok": True,
            "slug": "alpha-reviewer",
            "enabled": requested_enabled,
            "changed": changed,
            "store_path": _store_path(),
            "config": {
                "path": _absolute_config_path(),
                "revision": result_revision,
                "effective": {"agents": {"disabled": disabled}},
            },
        }

    monkeypatch.setattr(broker, "dashboard_api_request", request)

    assert broker.broker_set_agent_enabled(
        "alpha-reviewer",
        enabled=requested_enabled,
    ) == ("alpha-reviewer", changed, _absolute_config_path())
    verb = "ENABLE" if requested_enabled else "DISABLE"
    assert requests == [
        ("/api/agents/lookup?slug=alpha-reviewer", "GET", None),
        (
            "/api/agents/toggle",
            "POST",
            {
                "slug": "alpha-reviewer",
                "enabled": requested_enabled,
                "confirm": f"{verb} alpha-reviewer",
                "expected_revision": _revision(),
            },
        ),
    ]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"ok": False}, "response is invalid"),
        ({"slug": "beta-reviewer"}, "identity"),
        ({"enabled": 0}, "identity"),
        ({"changed": False}, "change state"),
        ({"config": []}, "config evidence"),
        ({"config_path": _absolute_config_path("other.yaml")}, "config identity"),
        ({"config_revision": _revision()}, "config identity"),
        ({"disabled": []}, "effective state"),
        ({"disabled": ["alpha-reviewer", "alpha-reviewer"]}, "disabled agent"),
        ({"disabled": ["chief-of-staff"]}, "disabled agent"),
    ],
)
def test_broker_agent_toggle_rejects_inconsistent_receipts(
    monkeypatch: pytest.MonkeyPatch,
    mutation: dict[str, Any],
    message: str,
) -> None:
    response: dict[str, Any] = {
        "ok": True,
        "slug": "alpha-reviewer",
        "enabled": False,
        "changed": True,
        "store_path": _store_path(),
        "config": {
            "path": _absolute_config_path(),
            "revision": _revision("c"),
            "effective": {"agents": {"disabled": ["alpha-reviewer"]}},
        },
    }
    if "config_path" in mutation:
        response["config"]["path"] = mutation["config_path"]
    elif "config_revision" in mutation:
        response["config"]["revision"] = mutation["config_revision"]
    elif "disabled" in mutation:
        response["config"]["effective"]["agents"]["disabled"] = mutation["disabled"]
    else:
        response.update(mutation)

    def request(path: str, **_kwargs: Any) -> dict[str, Any]:
        if path.startswith("/api/agents/lookup"):
            return _page(
                [_row("alpha-reviewer")],
                limit=1,
                filter_slug="alpha-reviewer",
            )
        return response

    monkeypatch.setattr(broker, "dashboard_api_request", request)

    with pytest.raises(ValueError, match=message):
        broker.broker_set_agent_enabled("alpha-reviewer", enabled=False)


def test_restricted_read_commands_use_the_broker_without_a_split_store(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    emitted: list[Any] = []
    broker_calls: list[str] = []

    def broker_activation_rows() -> tuple[str, list[dict[str, Any]]]:
        broker_calls.append("activation")
        return _absolute_config_path(), [
            {
                "slug": "alpha-reviewer",
                "name": "Alpha Reviewer",
                "division": "engineering",
                "enabled": True,
                "protected": False,
            }
        ]

    def broker_search_agents(*, query: str, limit: int) -> tuple[str, list[dict[str, Any]]]:
        broker_calls.append("search")
        return _absolute_config_path(), [{**_catalog()[0], "score": 0.9}][:limit]

    def broker_explain_selection(
        *,
        session_id: str,
        task: str,
        limit: int,
    ) -> tuple[str, dict[str, Any]]:
        broker_calls.append("explain")
        return _absolute_config_path(), {
            "schema_version": "agency.selection_explain.v1",
            "session_id": session_id,
            "task": task,
            "routing": {
                "selected_ids": ["alpha-reviewer"],
                "confidence": 0.9,
                "provider": "deterministic",
                "trace_id": "trace",
            },
            "selected": ["alpha-reviewer"],
            "considered_candidates": [{**_catalog()[0], "score": 0.9}],
            "rejected_candidates": [],
            "signals": {},
            "store_is_none": True,
        }

    monkeypatch.setattr(roster_commands, "_store", _raise_restricted)
    monkeypatch.setattr(roster_commands, "read_config_state", _raise_restricted)
    monkeypatch.setattr(broker, "broker_activation_rows", broker_activation_rows)
    monkeypatch.setattr(broker, "broker_search_agents", broker_search_agents)
    monkeypatch.setattr(broker, "broker_explain_selection", broker_explain_selection)
    monkeypatch.setattr(
        roster_commands,
        "resolve_config_path",
        lambda *_args, **_kwargs: Path(_absolute_config_path()),
    )
    monkeypatch.setattr(roster_commands, "_runtime_enabled", lambda: True)
    monkeypatch.setattr(roster_commands, "_print_json", emitted.append)
    validation = {
        "valid": True,
        "errors": [],
        "mode": "strict",
        "route_count": 0,
        "routes": [],
        "unique_policy_slugs": [],
        "enabled_slugs": [],
        "missing_enabled": [],
        "disabled_count": 0,
        "disabled_routes": [],
    }
    monkeypatch.setattr(roster_commands, "validate_policy", lambda _policy, _slugs: validation)

    assert roster_commands.cmd_roster_list(Namespace()) == 0
    assert "alpha-reviewer" in capsys.readouterr().out
    assert roster_commands.cmd_search(Namespace(query="review", limit=1, json=True)) == 0
    assert roster_commands.cmd_route(Namespace(task="review", limit=1, json=True)) == 0
    assert roster_commands.cmd_explain(Namespace(session_id="session", task="review", limit=1)) == 0
    dependencies = roster_commands.RosterDependencies(
        store_factory=_raise_restricted,
        emit_json=emitted.append,
        policy_loader=lambda: {"actions": {}, "division_anchors": {}},
    )
    assert roster_commands.cmd_policy(Namespace(json=True), dependencies=dependencies) == 0

    assert broker_calls == ["activation", "search", "explain", "explain", "activation"]
    assert any(isinstance(item, list) and item[0]["slug"] == "alpha-reviewer" for item in emitted)
    assert any(isinstance(item, dict) and item.get("store_is_none") for item in emitted)
    assert emitted[-1]["roster_count"] == 1


def test_restricted_search_honors_brokered_global_off_before_roster_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emitted: list[dict[str, Any]] = []
    monkeypatch.setattr(
        runtime_control,
        "read_effective_runtime_control",
        lambda **_kwargs: (_ for _ in ()).throw(
            runtime_control.RuntimeControlSecurityError("restricted reader unavailable")
        ),
    )
    monkeypatch.setattr(
        runtime_control,
        "_restricted_windows_control_target",
        lambda _path: True,
    )
    monkeypatch.setattr(
        dashboard_runtime,
        "dashboard_api_request",
        lambda path, *, timeout: (
            {"master": _master(False)} if path == "/api/runtime" and timeout == 0.25 else {}
        ),
    )
    monkeypatch.setattr(
        roster_commands,
        "_search",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("disabled search touched the roster")
        ),
    )
    monkeypatch.setattr(roster_commands, "_print_json", emitted.append)

    assert roster_commands.cmd_search(Namespace(query="review", limit=10, json=True)) == 0
    assert emitted == [
        {
            "runtime_enabled": False,
            "bypassed": True,
            "query": "review",
            "agents": [],
            "count": 0,
        }
    ]


def test_restricted_default_policy_uses_one_service_owned_policy_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = {"actions": {}, "division_anchors": {}}
    monkeypatch.setattr("agency_runtime.cli._common.Store", _raise_restricted)
    monkeypatch.setattr(
        broker,
        "broker_policy_snapshot",
        lambda: (_absolute_config_path(), policy, {"alpha-reviewer"}),
    )
    monkeypatch.setattr(
        roster_commands,
        "resolve_config_path",
        lambda *_args, **_kwargs: Path(_absolute_config_path()),
    )

    received, slugs = roster_commands._policy_operation(roster_commands.DEFAULT_DEPENDENCIES)

    assert received is policy
    assert slugs == {"alpha-reviewer"}


def test_restricted_search_broker_fails_closed_and_does_not_catch_generic_permissions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(roster_commands, "_store", _raise_restricted)
    monkeypatch.setattr(
        broker,
        "broker_search_agents",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("malformed dashboard roster")),
    )
    with pytest.raises(RuntimeError, match=r"could not execute search.*malformed dashboard roster"):
        roster_commands._search("review", 1)

    def ordinary_permission() -> Any:
        raise PermissionError("ordinary filesystem refusal")

    monkeypatch.setattr(
        broker,
        "broker_search_agents",
        lambda **_kwargs: calls.append("broker") or (_absolute_config_path(), []),
    )
    monkeypatch.setattr(roster_commands, "_store", ordinary_permission)
    with pytest.raises(PermissionError, match="ordinary filesystem refusal"):
        roster_commands._search("review", 1)
    assert calls == []


def test_restricted_search_rejects_dashboard_bound_to_another_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        broker,
        "broker_search_agents",
        lambda **_kwargs: (_absolute_config_path("service.yaml"), []),
    )
    monkeypatch.setattr(
        roster_commands,
        "resolve_config_path",
        lambda *_args, **_kwargs: Path(_absolute_config_path("cli.yaml")),
    )
    monkeypatch.setattr(roster_commands, "_store", _raise_restricted)

    with pytest.raises(RuntimeError, match="does not match the CLI config identity"):
        roster_commands._search("review", 1)


def test_restricted_roster_operations_reject_dashboard_config_identity_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli_path = Path(_absolute_config_path("cli.yaml"))
    service_path = _absolute_config_path("service.yaml")
    monkeypatch.setattr(
        roster_commands,
        "resolve_config_path",
        lambda *_args, **_kwargs: cli_path,
    )
    monkeypatch.setattr(roster_commands, "read_config_state", _raise_restricted)
    monkeypatch.setattr(roster_commands, "_store", _raise_restricted)
    monkeypatch.setattr(
        broker,
        "broker_activation_rows",
        lambda: (service_path, []),
    )
    monkeypatch.setattr(
        broker,
        "broker_set_agent_enabled",
        lambda *_args, **_kwargs: ("alpha-reviewer", True, service_path),
    )
    monkeypatch.setattr(
        broker,
        "broker_explain_selection",
        lambda **_kwargs: (service_path, {}),
    )

    with pytest.raises(RuntimeError, match="does not match the CLI config identity"):
        roster_commands._activation_rows()
    with pytest.raises(RuntimeError, match="does not match the CLI config identity"):
        roster_commands._set_agent_enabled("alpha-reviewer", enabled=False)
    with pytest.raises(RuntimeError, match="does not match the CLI config identity"):
        roster_commands._routing_operation(session_id="session", task="review", limit=1)

    dependencies = roster_commands.RosterDependencies(
        store_factory=_raise_restricted,
        emit_json=lambda _value: None,
        policy_loader=lambda: {"actions": {}, "division_anchors": {}},
    )
    with pytest.raises(RuntimeError, match="does not match the CLI config identity"):
        roster_commands._policy_operation(dependencies)


def test_explicit_agent_config_is_never_redirected_to_the_dashboard(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    explicit = tmp_path / "explicit.yaml"
    monkeypatch.setattr(
        roster_commands,
        "resolve_config_path",
        lambda _value=None: explicit,
    )
    monkeypatch.setattr(roster_commands, "read_config_state", _raise_restricted)
    monkeypatch.setattr(
        broker,
        "broker_activation_rows",
        lambda: calls.append("list") or (str(explicit), []),
    )
    monkeypatch.setattr(
        broker,
        "broker_set_agent_enabled",
        lambda *_args, **_kwargs: calls.append("toggle") or ("alpha-reviewer", True, ""),
    )

    with pytest.raises(RuntimeError, match="explicit agent config cannot be redirected"):
        roster_commands._activation_rows(str(explicit))
    with pytest.raises(RuntimeError, match="explicit agent config cannot be redirected"):
        roster_commands._set_agent_enabled(
            "alpha-reviewer",
            enabled=False,
            config_argument=str(explicit),
        )
    assert calls == []


def test_default_agent_activation_reads_and_writes_use_the_restricted_broker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    default_path = tmp_path / "agency.yaml"
    monkeypatch.setattr(
        roster_commands,
        "resolve_config_path",
        lambda _value=None: default_path,
    )
    monkeypatch.setattr(roster_commands, "read_config_state", _raise_restricted)
    monkeypatch.setattr(
        broker,
        "broker_activation_rows",
        lambda: (
            str(default_path),
            [
                {
                    "slug": "alpha-reviewer",
                    "name": "Alpha Reviewer",
                    "division": "engineering",
                    "enabled": True,
                    "protected": False,
                }
            ],
        ),
    )
    monkeypatch.setattr(
        broker,
        "broker_set_agent_enabled",
        lambda slug, *, enabled: (str(slug), not enabled, str(default_path)),
    )

    assert roster_commands._activation_rows() == (
        str(default_path),
        [
            {
                "slug": "alpha-reviewer",
                "name": "Alpha Reviewer",
                "division": "engineering",
                "enabled": True,
                "protected": False,
            }
        ],
    )
    assert roster_commands._set_agent_enabled("alpha-reviewer", enabled=False) == (
        "alpha-reviewer",
        True,
        str(default_path),
    )


def test_restricted_delegation_store_returns_controlled_error_without_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.delegation import backends

    emitted: list[dict[str, Any]] = []
    executions: list[str] = []

    class Candidate:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def execute(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
            executions.append("executed")
            return {"status": "completed", "exit_code": 0}

    monkeypatch.setattr(runtime_control, "master_enabled", lambda: True)
    monkeypatch.setattr(backends, "CodexExecBackend", Candidate)
    monkeypatch.setattr(delegation_commands, "_store", _raise_restricted)
    monkeypatch.setattr(delegation_commands, "_print_json", emitted.append)
    args = Namespace(
        agent="code-reviewer",
        backend="codex",
        command=None,
        json=True,
        task="review this change",
        timeout=30.0,
    )

    assert delegation_commands.cmd_delegate(args) == 2
    assert executions == []
    assert emitted == [
        {
            "status": "error",
            "error": (
                "delegation evidence Store is unavailable from this restricted process; "
                "execution was not started and is never proxied through the dashboard"
            ),
            "exit_code": 2,
        }
    ]


@pytest.mark.parametrize("failure_stage", ["store", "seed"])
@pytest.mark.parametrize("json_mode", [False, True])
def test_install_restricted_roster_initialization_fails_before_native_mutation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure_stage: str,
    json_mode: bool,
) -> None:
    from agency_runtime.core import dashboard_service, installer

    emitted: list[dict[str, Any]] = []
    cfg = config_module.AgencyConfig()
    dependencies = install_commands.InstallDependencies(
        load_config=lambda: cfg,
        store_factory=(_raise_restricted if failure_stage == "store" else lambda _cfg: object()),
        emit_json=emitted.append,
        readiness_probe=lambda: True,
    )
    monkeypatch.setattr(
        install_commands, "dashboard_service_environment_overrides", lambda _cfg: ()
    )
    monkeypatch.setattr(installer, "detect_installed_agents", lambda: [])
    monkeypatch.setattr(
        installer,
        "seed_starter_roster",
        _raise_restricted if failure_stage == "seed" else lambda _store: 0,
    )
    monkeypatch.setattr(
        dashboard_service,
        "install_dashboard_service",
        lambda **_kwargs: pytest.fail("dashboard mutation must not start"),
    )
    monkeypatch.setattr(
        installer,
        "install_agent_adapter",
        lambda *_args, **_kwargs: pytest.fail("host mutation must not start"),
    )
    args = Namespace(
        agent=None,
        all=False,
        backup=None,
        dry_run=False,
        execute=False,
        json=json_mode,
        no_dashboard=False,
        profile=None,
        rollback=False,
    )

    assert install_commands.cmd_install(args, dependencies=dependencies) == 1
    if json_mode:
        assert emitted[-1]["ok"] is False
        assert emitted[-1]["hosts"] == []
        assert emitted[-1]["dashboard"] is None
        assert "restricted process" in emitted[-1]["error"]
        assert emitted[-1]["roster_added"] == (0 if failure_stage == "store" else None)
    else:
        assert "restricted process" in capsys.readouterr().out


def _configuration_detection() -> SimpleNamespace:
    return SimpleNamespace(
        providers=SimpleNamespace(
            ollama_available=False,
            ollama_base_url="http://127.0.0.1:11434",
            ollama_models=[],
            openai_key="",
            anthropic_key="",
            litellm_available=False,
            litellm_base_url="http://127.0.0.1:4000",
        ),
        adapters=SimpleNamespace(
            hermes=False,
            openclaw=False,
            codex=True,
            claude=False,
        ),
    )


@pytest.mark.parametrize("failure_stage", ["store", "seed"])
def test_configure_reports_written_config_as_partial_when_roster_setup_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    failure_stage: str,
) -> None:
    path = tmp_path / "agency.yaml"
    writes: list[dict[str, Any]] = []
    cfg = SimpleNamespace(store=SimpleNamespace(resolved_path=lambda: tmp_path / "agency.db"))
    dependencies = config_commands.ConfigurationDependencies(
        load_config=lambda **_kwargs: cfg,
        store_factory=(
            (lambda _cfg: (_ for _ in ()).throw(PermissionError("store\nrefused")))
            if failure_stage == "store"
            else lambda _cfg: object()
        ),
        seed_starter_roster=(
            (lambda _store: (_ for _ in ()).throw(PermissionError("seed\nrefused")))
            if failure_stage == "seed"
            else lambda _store: 0
        ),
        detect_for_profile=lambda _profile: _configuration_detection(),
        interactive_wizard=lambda _detection, profile: {"profile": profile},
        validate_chain=lambda _providers: True,
        secret_prompt=lambda _prompt: "",
        configure_console=lambda: None,
    )
    monkeypatch.setattr(config_commands, "resolve_config_path", lambda: path)
    monkeypatch.setattr(
        config_commands,
        "read_config_state",
        lambda _path: SimpleNamespace(revision="empty"),
    )
    monkeypatch.setattr(
        config_commands,
        "replace_config_document",
        lambda document, **_kwargs: writes.append(document),
    )
    monkeypatch.setattr(config_commands, "reset_config_cache", lambda: None)
    monkeypatch.setattr(
        config_commands,
        "generate_config_from_detection",
        lambda _detection, profile: {"profile": profile, "providers": []},
    )
    args = Namespace(force=False, non_interactive=True, profile="standard")

    assert config_commands.cmd_configure(args, dependencies=dependencies) == 1
    output = capsys.readouterr().out
    assert writes == [{"profile": "standard", "providers": []}]
    assert f"Config written to {path}" in output
    assert "Starter roster and SQLite initialization did not complete" in output
    assert "\\u000a" in output
    assert "✅ Config written" not in output


def test_cli_main_sanitizes_os_errors_to_one_terminal_line(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli_main, "_configure_console_output", lambda: None)
    monkeypatch.setattr(
        cli_main,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda _argv: SimpleNamespace(
                func=lambda _args: (_ for _ in ()).throw(PermissionError("denied\n\x1b[31m forged"))
            )
        ),
    )

    assert cli_main.main([]) == 1
    error = capsys.readouterr().err
    assert error.splitlines() == ["agency: error: denied\\u000a\\u001b[31m forged"]


def _master(enabled: bool = True, *, generation: int = 7) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "enabled": enabled,
        "generation": generation,
        "updated_at": "2026-07-16T12:00:00Z",
        "source": "dashboard",
    }


def _host_status(*, enabled: bool = True, generation: int = 2) -> dict[str, Any]:
    return {
        "host": "codex",
        "runtime_enabled": enabled,
        "master_enabled": True,
        "effective_enabled": enabled,
        "runtime_control_generation": generation,
        "runtime_control_updated_at": "2026-07-16T12:00:00Z",
        "runtime_control_source": "dashboard",
    }


def _host_identity() -> dict[str, Any]:
    store_path = _store_path()
    return {
        "config_path": str(install_commands.resolve_config_path()),
        "config_revision": _revision(),
        "environment_overrides": {},
        "store_path": store_path,
        "desired_store_path": store_path,
        "store_restart_required": False,
    }


def test_host_broker_accepts_an_exact_noop_receipt_without_generation_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[tuple[str, str, Any]] = []

    def request(path: str, *, method: str = "GET", payload: Any = None) -> dict[str, Any]:
        requests.append((path, method, payload))
        if path == "/api/hosts":
            from agency_runtime.core.host_control import SUPPORTED_HOSTS

            hosts = [
                {
                    **_host_status(),
                    "host": host,
                }
                for host in SUPPORTED_HOSTS
            ]
            return {"hosts": hosts, "master": _master(), **_host_identity()}
        return {
            "ok": True,
            "host": "codex",
            "enabled": True,
            "generation": 2,
            "updated_at": "2026-07-16T12:00:00Z",
            "source": "dashboard",
            "status": _host_status(),
            **_host_identity(),
        }

    monkeypatch.setattr(dashboard_runtime, "dashboard_api_request", request)

    result = install_commands._dashboard_soft_control_result(
        "codex",
        enabled=True,
        dry_run=False,
    )

    assert result["generation"] == result["previous_generation"] == 2
    assert requests[-1] == (
        "/api/hosts/toggle",
        "POST",
        {
            "host": "codex",
            "enabled": True,
            "expected_generation": 2,
            "confirm": "ENABLE codex",
        },
    )


def test_master_broker_accepts_an_exact_noop_receipt_without_generation_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        install_commands,
        "_read_master_control_with_broker",
        lambda: (_master(), "direct"),
    )
    monkeypatch.setattr(
        runtime_control,
        "set_master_enabled",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            runtime_control.RuntimeControlSecurityError("restricted")
        ),
    )
    monkeypatch.setattr(
        dashboard_runtime,
        "dashboard_api_request",
        lambda *_args, **_kwargs: {
            "ok": True,
            "changed": False,
            "master": _master(),
        },
    )

    result = install_commands._global_control_result(
        Namespace(native=False, dry_run=False),
        enabled=True,
    )

    assert result["changed"] is False
    assert result["master"]["generation"] == 7
    assert result["transport"] == "dashboard"


def test_host_soft_control_brokers_only_the_exact_restricted_token_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        install_commands,
        "_soft_control_result",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            PermissionError("ordinary filesystem refusal")
        ),
    )
    monkeypatch.setattr(
        install_commands,
        "_dashboard_soft_control_result",
        lambda *_args, **_kwargs: calls.append("broker") or {},
    )

    with pytest.raises(PermissionError, match="ordinary filesystem refusal"):
        install_commands._restricted_aware_soft_control_result(
            object(),
            "codex",
            enabled=False,
            dry_run=False,
            restricted_store=False,
        )
    assert calls == []
