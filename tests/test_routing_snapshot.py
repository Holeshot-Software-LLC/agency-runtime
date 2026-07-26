"""Regression coverage for single-operation routing/config snapshots."""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import agency_runtime.core.selector.explain as selector_explain
import agency_runtime.core.selector.pipeline as selector_pipeline
import agency_runtime.server.dashboard as dashboard_module
import agency_runtime.server.http as http_module
import agency_runtime.server.mcp_tools as mcp_tools
from agency_runtime import AgencyRuntime
from agency_runtime.cli import agent_control_broker as broker
from agency_runtime.core.agent_activation import agent_is_enabled
from agency_runtime.core.config import (
    AgencyConfig,
    AgentActivationConfig,
    SelectorConfig,
    load_config,
    reset_config_cache,
)
from agency_runtime.core.delegation.operational import empty_delegation_plan_projection
from agency_runtime.core.routing_snapshot import (
    RoutingSnapshot,
    capture_operational_routing_snapshot,
    capture_routing_snapshot,
    catalog_for_routing,
)
from agency_runtime.core.selector.receipt_projection import (
    RECEIPT_DESCRIPTION_BYTES,
    bounded_receipt_text,
)


def _config(*, disabled: tuple[str, ...] = (), maximum: int = 4000) -> AgencyConfig:
    return AgencyConfig(
        agents=AgentActivationConfig(disabled=disabled),
        selector=SelectorConfig(max_user_msg_len=maximum),
    )


def _catalog() -> list[dict[str, Any]]:
    return [
        {
            "slug": "code-reviewer",
            "name": "Code Reviewer",
            "description": "Reviews code.",
        },
        {
            "slug": "security-reviewer",
            "name": "Security Reviewer",
            "description": "Reviews security.",
        },
    ]


def test_snapshot_keeps_one_config_when_file_changes_during_catalog_read(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "agency.yaml"
    config_path.write_text("agents:\n  disabled: [code-reviewer]\n", encoding="utf-8")

    class ToggleStore:
        def __init__(self) -> None:
            self.config_path = config_path
            self.observed_disabled: frozenset[str] | None = None

        def get_active_roster_as_catalog(
            self,
            *,
            disabled_agents: frozenset[str],
        ) -> list[dict[str, Any]]:
            self.observed_disabled = disabled_agents
            config_path.write_text("agents:\n  disabled: []\n", encoding="utf-8")
            reset_config_cache()
            return [row for row in _catalog() if agent_is_enabled(row["slug"], disabled_agents)]

    store = ToggleStore()
    snapshot = capture_routing_snapshot(store)

    assert snapshot.config.agents.disabled == ("code-reviewer",)
    assert store.observed_disabled == frozenset({"code-reviewer"})
    assert [row["slug"] for row in snapshot.catalog] == ["security-reviewer"]
    assert load_config(config_path, reload=True).agents.disabled == ()


def test_catalog_snapshot_supports_keyword_compatible_store_facades() -> None:
    observed: list[frozenset[str]] = []

    class KeywordStore:
        @staticmethod
        def get_active_roster_as_catalog(**kwargs: Any) -> list[dict[str, Any]]:
            observed.append(kwargs["disabled_agents"])
            return []

    assert catalog_for_routing(KeywordStore(), frozenset({"reviewer"})) == []
    assert observed == [frozenset({"reviewer"})]


def test_operational_snapshot_reuses_one_stable_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import installer
    from agency_runtime.core import routing_snapshot as subject

    snapshot = RoutingSnapshot(_config(), _catalog(), roster_generation=7)
    captures: list[AgencyConfig | None] = []
    monkeypatch.setattr(
        subject,
        "capture_routing_snapshot",
        lambda _store, config=None: captures.append(config) or snapshot,
    )
    monkeypatch.setattr(installer, "reconcile_packaged_contractors", lambda _store: (0, 9))
    monkeypatch.setattr(installer, "ensure_no_match_fallback_roster", lambda _store: 0)
    store = SimpleNamespace(get_roster_generation=lambda: 7)

    result = capture_operational_routing_snapshot(store)

    assert result is snapshot
    assert captures == [None]


def test_operational_snapshot_recaptures_after_generation_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import installer
    from agency_runtime.core import routing_snapshot as subject

    initial = RoutingSnapshot(_config(), _catalog(), roster_generation=7)
    refreshed = RoutingSnapshot(_config(), _catalog(), roster_generation=8)
    snapshots = iter((initial, refreshed))
    captures: list[AgencyConfig | None] = []

    def capture(_store: object, config: AgencyConfig | None = None) -> RoutingSnapshot:
        captures.append(config)
        return next(snapshots)

    monkeypatch.setattr(subject, "capture_routing_snapshot", capture)
    monkeypatch.setattr(installer, "reconcile_packaged_contractors", lambda _store: (1, 8))
    monkeypatch.setattr(installer, "ensure_no_match_fallback_roster", lambda _store: 0)
    store = SimpleNamespace(get_roster_generation=lambda: 8)

    result = capture_operational_routing_snapshot(store)

    assert result is refreshed
    assert captures == [None, initial.config]


def test_public_runtime_route_passes_one_snapshot_to_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = RoutingSnapshot(_config(disabled=("code-reviewer",)), _catalog())
    runtime = AgencyRuntime()
    monkeypatch.setattr(runtime, "_active_routing_snapshot", lambda: snapshot)
    monkeypatch.setattr(runtime, "_runtime_enabled", lambda: True)
    observed: dict[str, Any] = {}

    def route(*args: Any, **kwargs: Any) -> dict[str, Any]:
        observed.update({"catalog": args[2], "config": kwargs["config"]})
        return {"selected_ids": []}

    monkeypatch.setattr(selector_pipeline, "route", route)

    assert runtime.route("session", "review code") == {"selected_ids": []}
    assert observed == {"catalog": snapshot.catalog, "config": snapshot.config}


def test_http_explain_passes_one_snapshot_to_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = RoutingSnapshot(_config(disabled=("code-reviewer",)), _catalog())
    monkeypatch.setattr(
        http_module,
        "capture_operational_routing_snapshot",
        lambda _store: snapshot,
    )
    observed: dict[str, Any] = {}

    def explain(*args: Any, **kwargs: Any) -> dict[str, Any]:
        observed.update({"catalog": args[2], "config": kwargs["config"]})
        return {"ok": True}

    monkeypatch.setattr(http_module, "explain_route", explain)
    handler = object.__new__(http_module.AgencyHTTPHandler)
    handler.server = SimpleNamespace(store=object())
    payloads: list[dict[str, Any]] = []
    handler._json_ok = payloads.append

    handler._handle_explain({"task": "review code"})

    assert payloads == [{"ok": True}]
    assert observed == {"catalog": snapshot.catalog, "config": snapshot.config}


def test_mcp_explain_passes_one_snapshot_to_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = RoutingSnapshot(_config(disabled=("code-reviewer",)), _catalog())
    monkeypatch.setattr(
        mcp_tools,
        "capture_operational_routing_snapshot",
        lambda _store: snapshot,
    )
    observed: dict[str, Any] = {}

    def explain(*args: Any, **kwargs: Any) -> dict[str, Any]:
        observed.update({"catalog": args[2], "config": kwargs["config"]})
        return {"ok": True}

    monkeypatch.setattr(selector_explain, "explain_route", explain)

    assert mcp_tools._explain_selection({"task": "review code"}, object()) == {"ok": True}
    assert observed == {"catalog": snapshot.catalog, "config": snapshot.config}


def test_dashboard_route_lab_passes_one_snapshot_to_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = RoutingSnapshot(
        _config(disabled=("code-reviewer",), maximum=100),
        _catalog(),
    )
    identity = {
        "config_path": str(Path.cwd() / "agency.yaml"),
        "config_revision": "sha256:" + "a" * 64,
        "store_path": str(Path.cwd() / "agency.db"),
        "roster_revision": "b" * 64,
        "environment_overrides": {},
    }
    monkeypatch.setattr(dashboard_module, "_delegation_graph", lambda _receipt: {"nodes": []})
    monkeypatch.setattr(
        dashboard_module,
        "delegation_plan_projection",
        lambda *_args, **_kwargs: {"units": []},
    )
    capability_receipt = {
        "contract_version": "1",
        "surface": "codex",
        "execution_host": "codex",
        "inference_surface": "",
        "platform": "windows",
        "status": "native-installation-verified",
        "source": "native-installation-evidence",
        "capabilities": ["repository-read", "test-execution"],
        "unknown_tools": [],
        "evidence": ["native-inventory-verified:codex"],
    }
    monkeypatch.setattr(
        dashboard_module,
        "_route_lab_host_capability",
        lambda *_args, **_kwargs: ("codex", capability_receipt),
    )
    observed: dict[str, Any] = {}

    def explain(*args: Any, **kwargs: Any) -> dict[str, Any]:
        observed.update(
            {
                "catalog": args[2],
                "config": kwargs["config"],
                "host": kwargs["host"],
                "platform": kwargs["platform"],
                "available_tools": kwargs["available_tools"],
            }
        )
        return {"ok": True}

    monkeypatch.setattr(dashboard_module, "explain_route", explain)
    handler = object.__new__(dashboard_module.DashboardHTTPHandler)
    handler.server = SimpleNamespace(store=object(), host_inspector=lambda: [])
    handler._master_control = lambda: {"enabled": True}
    handler._routing_operation_snapshot = lambda: (snapshot, identity)
    payloads: list[dict[str, Any]] = []
    handler._json_ok = payloads.append

    handler._handle_route_lab({"task": "review code", "host": "codex"})

    assert payloads == [
        {
            "ok": True,
            "host_capability_receipt": capability_receipt,
            "eligibility": {
                "execution_host": "codex",
                "capability_status": "native-installation-verified",
                "eligible_count": 2,
                "rejection_count": 0,
                "rejections": [],
                "truncated": False,
                "host_resolution": "explicit",
            },
            "delegation_plan": {"units": []},
            "delegation_graph": {"nodes": []},
            "operation_snapshot": identity,
        }
    ]
    assert observed == {
        "catalog": snapshot.catalog,
        "config": snapshot.config,
        "host": "codex",
        "platform": "windows",
        "available_tools": ("repository-read", "test-execution"),
    }


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"task": 7}, "task is required"),
        ({"task": "   "}, "task is required"),
        ({"task": "review", "session_id": 7}, "session_id must be a string"),
        ({"task": "review", "limit": True}, "limit must be an integer"),
        ({"task": "review", "limit": 0}, "limit must be an integer"),
        ({"task": "review", "limit": 51}, "limit must be an integer"),
        ({"task": "review", "limit": "10"}, "limit must be an integer"),
    ],
)
def test_dashboard_route_lab_rejects_coerced_broker_arguments(
    monkeypatch: pytest.MonkeyPatch,
    body: dict[str, Any],
    message: str,
) -> None:
    snapshot = RoutingSnapshot(_config(maximum=100), _catalog())
    handler = object.__new__(dashboard_module.DashboardHTTPHandler)
    handler.server = SimpleNamespace(store=object())
    handler._master_control = lambda: {"enabled": True}
    handler._routing_operation_snapshot = lambda: (snapshot, _operation_identity())
    handler._json_ok = lambda _payload: pytest.fail("invalid route input produced output")
    monkeypatch.setattr(
        dashboard_module,
        "explain_route",
        lambda *_args, **_kwargs: pytest.fail("invalid route input reached the selector"),
    )

    with pytest.raises(ValueError, match=message):
        handler._handle_route_lab(body)


def _operation_identity() -> dict[str, Any]:
    return {
        "config_path": str((Path.cwd() / "agency.yaml").resolve()),
        "config_revision": "sha256:" + "a" * 64,
        "store_path": str((Path.cwd() / "agency.db").resolve()),
        "desired_store_path": str((Path.cwd() / "agency.db").resolve()),
        "store_restart_required": False,
        "roster_revision": "b" * 64,
        "environment_overrides": {},
    }


def _disabled_master() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "enabled": False,
        "generation": 4,
        "updated_at": "2026-07-16T12:00:00Z",
        "source": "test",
    }


def _route_bypass(*, session_id: str = "session", task: str = "review") -> dict[str, Any]:
    return {
        "schema_version": "agency.selection_explain.v1",
        "session_id": session_id,
        "task": task,
        "routing": {
            "runtime_enabled": False,
            "bypassed": True,
            "trace_id": "",
            "selected_ids": [],
            "semantic_ids": [],
            "confidence": 0.0,
            "latency_ms": 0,
            "status": "bypassed",
            "source": "master_control",
            "provider": "master_control",
        },
        "selected": [],
        "considered_candidates": [],
        "rejected_candidates": [],
        "signals": {"source": "master_control"},
        "delegation_plan": empty_delegation_plan_projection(),
        "delegation_graph": {"nodes": [], "edges": []},
        "runtime_enabled": False,
        "status": "disabled",
        "bypassed": True,
        "message": "Agency Runtime is disabled; Route Lab bypassed routing.",
        "master": _disabled_master(),
    }


def _search_bypass(*, query: str = "review") -> dict[str, Any]:
    return {
        "schema_version": "agency.search.v1",
        "query": query,
        "agents": [],
        "count": 0,
        "runtime_enabled": False,
        "status": "disabled",
        "bypassed": True,
        "message": "Agency Runtime is disabled; search was bypassed.",
        "master": _disabled_master(),
    }


def test_broker_operation_identity_rejects_process_environment_overrides() -> None:
    identity = _operation_identity()
    identity["environment_overrides"] = {"companion_policy_path": "AGENCY_POLICY_PATH"}

    with pytest.raises(ValueError, match="environment overrides"):
        broker._operation_identity(identity)


def test_dashboard_master_off_route_and_search_bypass_without_store_snapshot() -> None:
    handler = object.__new__(dashboard_module.DashboardHTTPHandler)
    handler.server = SimpleNamespace(store=object())
    handler._master_control = _disabled_master
    handler._routing_operation_snapshot = lambda: pytest.fail(
        "master-off brokerage opened a Store/config routing snapshot"
    )
    payloads: list[dict[str, Any]] = []
    handler._json_ok = payloads.append

    handler._handle_route_lab({"session_id": "session", "task": "review", "limit": 3})
    handler._handle_search_broker({"query": "review", "limit": 3})

    assert payloads == [_route_bypass(), _search_bypass()]


def test_broker_accepts_canonical_master_bypass_receipts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = [_route_bypass(), _search_bypass()]
    monkeypatch.setattr(
        broker,
        "dashboard_api_request",
        lambda *_args, **_kwargs: responses.pop(0),
    )

    path, route = broker.broker_explain_selection(
        session_id="session",
        task="review",
        limit=3,
    )
    search_path, agents = broker.broker_search_agents(query="review", limit=3)

    assert path is None
    assert route == _route_bypass()
    assert search_path is None
    assert agents == []


@pytest.mark.parametrize(
    "mutation",
    [
        "unexpected_field",
        "operation_snapshot",
        "routing_field",
        "routing_boolean_number",
        "message",
        "enabled_master",
    ],
)
def test_broker_rejects_noncanonical_master_route_bypass(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    response = _route_bypass()
    if mutation == "unexpected_field":
        response["unexpected"] = True
    elif mutation == "operation_snapshot":
        response["operation_snapshot"] = _operation_identity()
    elif mutation == "routing_field":
        response["routing"]["unexpected"] = True
    elif mutation == "routing_boolean_number":
        response["routing"]["latency_ms"] = False
    elif mutation == "message":
        response["message"] = "disabled"
    else:
        response["master"]["enabled"] = True
    monkeypatch.setattr(broker, "dashboard_api_request", lambda *_args, **_kwargs: response)

    with pytest.raises(ValueError, match="bypass"):
        broker.broker_explain_selection(session_id="session", task="review", limit=3)


@pytest.mark.parametrize(
    "mutation",
    ["unexpected_field", "operation_snapshot", "agents", "message", "enabled_master"],
)
def test_broker_rejects_noncanonical_master_search_bypass(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    response = _search_bypass()
    if mutation == "unexpected_field":
        response["unexpected"] = True
    elif mutation == "operation_snapshot":
        response["operation_snapshot"] = _operation_identity()
    elif mutation == "agents":
        response["agents"] = [{"slug": "code-reviewer"}]
        response["count"] = 1
    elif mutation == "message":
        response["message"] = "disabled"
    else:
        response["master"]["enabled"] = True
    monkeypatch.setattr(broker, "dashboard_api_request", lambda *_args, **_kwargs: response)

    with pytest.raises(ValueError, match=r"bypass|search response"):
        broker.broker_search_agents(query="review", limit=3)


def test_dashboard_routing_catalog_revision_streams_the_canonical_digest() -> None:
    catalog = [
        {
            "slug": "unicode-reviewer",
            "description": "🔐" * 4_096,
            "capabilities": ["review", "security"],
        },
        {"slug": "code-reviewer", "description": "Review code."},
    ]
    canonical = json.dumps(
        catalog,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    assert (
        dashboard_module._routing_catalog_revision(catalog) == hashlib.sha256(canonical).hexdigest()
    )


def test_receipt_description_is_utf8_and_json_escape_bounded() -> None:
    raw = ("😀\\\n" * 5000) + "tail"

    bounded = bounded_receipt_text(raw, maximum_bytes=RECEIPT_DESCRIPTION_BYTES)

    assert len(bounded.encode("utf-8")) <= RECEIPT_DESCRIPTION_BYTES
    assert not bounded.endswith("�")
    assert len(json.dumps(bounded, ensure_ascii=False).encode("utf-8")) <= (
        RECEIPT_DESCRIPTION_BYTES * 2 + 2
    )


def test_broker_explain_accepts_only_the_echoed_frozen_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = _operation_identity()
    requests: list[tuple[str, str, dict[str, Any]]] = []

    def request(
        path: str,
        *,
        method: str,
        payload: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        assert timeout > 0
        requests.append((path, method, payload))
        return {
            "schema_version": "agency.selection_explain.v1",
            "session_id": payload["session_id"],
            "task": payload["task"],
            "routing": {"selected_ids": []},
            "selected": [],
            "considered_candidates": [],
            "rejected_candidates": [],
            "signals": {},
            "operation_snapshot": identity,
        }

    monkeypatch.setattr(broker, "dashboard_api_request", request)

    path, receipt = broker.broker_explain_selection(
        session_id="",
        task="review code",
        limit=10,
    )

    assert path == identity["config_path"]
    assert receipt["operation_snapshot"] == identity
    assert requests == [
        (
            "/api/route",
            "POST",
            {"session_id": "", "task": "review code", "limit": 10, "host": "codex"},
        )
    ]


def test_broker_policy_validates_content_revision_and_active_slugs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    monkeypatch.setattr(
        broker,
        "dashboard_api_request",
        lambda _path: {
            "schema_version": "agency.policy_snapshot.v1",
            "policy": policy,
            "active_slugs": ["code-reviewer", "security-reviewer"],
            "operation_snapshot": _operation_identity(),
            "policy_revision": revision,
        },
    )

    path, received, slugs = broker.broker_policy_snapshot()

    assert path == _operation_identity()["config_path"]
    assert received == policy
    assert slugs == {"code-reviewer", "security-reviewer"}


def test_broker_search_returns_only_validated_bounded_summaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    description = "😀" * (RECEIPT_DESCRIPTION_BYTES // 4)
    monkeypatch.setattr(
        broker,
        "dashboard_api_request",
        lambda _path, **_kwargs: {
            "schema_version": "agency.search.v1",
            "query": "review",
            "agents": [
                {
                    "slug": "code-reviewer",
                    "name": "Code Reviewer",
                    "division": "engineering",
                    "description": description,
                    "score": 0.75,
                }
            ],
            "count": 1,
            "operation_snapshot": _operation_identity(),
        },
    )

    path, agents = broker.broker_search_agents(query="review", limit=1)

    assert path == _operation_identity()["config_path"]
    assert agents == [
        {
            "slug": "code-reviewer",
            "name": "Code Reviewer",
            "division": "engineering",
            "description": description,
            "score": 0.75,
        }
    ]


def test_dashboard_search_routes_with_full_metadata_but_returns_bounded_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    full_description = "\\\n" * 10_000
    snapshot = RoutingSnapshot(
        _config(maximum=100),
        [{**_catalog()[0], "description": full_description}],
    )
    observed: list[str] = []

    def pre_narrow(
        _query: str,
        catalog: list[dict[str, Any]],
        *,
        limit: int,
    ) -> tuple[list[dict[str, Any]], list[float]]:
        assert limit == 1
        observed.append(catalog[0]["description"])
        return catalog, [0.5]

    monkeypatch.setattr(dashboard_module, "pre_narrow", pre_narrow)
    handler = object.__new__(dashboard_module.DashboardHTTPHandler)
    handler.server = SimpleNamespace(store=object())
    handler._master_control = lambda: {"enabled": True}
    handler._routing_operation_snapshot = lambda: (snapshot, _operation_identity())
    payloads: list[dict[str, Any]] = []
    handler._json_ok = payloads.append

    handler._handle_search_broker({"query": "review", "limit": 1})

    assert observed == [full_description]
    assert len(payloads[0]["agents"][0]["description"].encode("utf-8")) <= (
        RECEIPT_DESCRIPTION_BYTES
    )
    assert payloads[0]["operation_snapshot"] == _operation_identity()


def test_dashboard_operation_snapshot_rejects_a_mid_operation_config_toggle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = Path(_operation_identity()["config_path"])
    snapshot = RoutingSnapshot(
        AgencyConfig(
            agents=AgentActivationConfig(disabled=("code-reviewer",)),
            config_path=str(config_path),
        ),
        _catalog(),
    )
    states = [
        SimpleNamespace(
            path=str(config_path),
            revision="sha256:" + "a" * 64,
            environment_overrides={},
            effective={"agents": {"disabled": ["code-reviewer"]}},
        ),
        SimpleNamespace(
            path=str(config_path),
            revision="sha256:" + "c" * 64,
            environment_overrides={},
            effective={"agents": {"disabled": []}},
        ),
    ]
    locked = False

    @contextmanager
    def config_lock(_path: object):
        nonlocal locked
        locked = True
        try:
            yield config_path
        finally:
            locked = False

    def capture(_store: object) -> RoutingSnapshot:
        assert locked is True
        return snapshot

    monkeypatch.setattr(dashboard_module, "config_read_lock", config_lock)
    monkeypatch.setattr(dashboard_module, "read_config_state", lambda _path: states.pop(0))
    monkeypatch.setattr(
        dashboard_module,
        "_require_store_service_binding",
        lambda _store, _state: {"store_path": _operation_identity()["store_path"]},
    )
    monkeypatch.setattr(
        dashboard_module,
        "capture_operational_routing_snapshot",
        capture,
    )
    handler = object.__new__(dashboard_module.DashboardHTTPHandler)
    handler.server = SimpleNamespace(store=object(), config_path=config_path)

    with pytest.raises(
        dashboard_module.ConfigConflictError,
        match="configuration changed",
    ):
        handler._routing_operation_snapshot()
    assert locked is False


def test_policy_projection_fails_before_exceeding_the_broker_wire_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dashboard_module, "_BROKER_POLICY_RESPONSE_BYTES", 8)

    with pytest.raises(ValueError, match="response budget"):
        dashboard_module._bounded_policy_response({"policy": {"actions": {}}})
