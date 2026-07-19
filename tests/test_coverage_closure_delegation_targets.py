"""Behavioral closure for config-bound dashboard, routing, and store edges."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import nullcontext
from dataclasses import replace
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.adapters.litellm import callback as litellm_callback
from agency_runtime.adapters.litellm.callback import AgencyLiteLLMCallback, LiteLLMAdapter
from agency_runtime.core import config_binding, dashboard_runtime, windows_acl
from agency_runtime.core.bounded_io import UnsafeFileError
from agency_runtime.core.config import AgencyConfig, AgentActivationConfig
from agency_runtime.core.configuration import ConfigConflictError, ConfigurationError
from agency_runtime.core.roster import selector_projection
from agency_runtime.core.selector import policy as selector_policy
from agency_runtime.core.store import roster as roster_store
from agency_runtime.core.store import sqlite as sqlite_store
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server import dashboard


def _config_state(
    *,
    path: Path,
    disabled: list[str] | None = None,
    store: object = None,
) -> SimpleNamespace:
    effective_store = {"db_path": str(path.with_suffix(".db"))} if store is None else store
    return SimpleNamespace(
        path=path,
        persisted={},
        effective={
            "agents": {"disabled": [] if disabled is None else disabled},
            "store": effective_store,
        },
        revision="sha256:" + ("a" * 64),
        secret_presence={},
        environment_overrides={},
    )


def _routing_handler(config_path: Path) -> dashboard.DashboardHTTPHandler:
    handler = object.__new__(dashboard.DashboardHTTPHandler)
    handler.server = SimpleNamespace(config_path=config_path, store=object())
    return handler


def test_dashboard_helpers_reject_stale_or_malformed_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _config_state(path=tmp_path / "agency.yaml")
    assert "service_binding" not in dashboard._config_payload(state)
    assert dashboard._bounded_policy_response({"policy": {}}) == {"policy": {}}

    with pytest.raises(ConfigurationError, match="store path is invalid"):
        dashboard._absolute_runtime_path(object())
    with pytest.raises(ConfigurationError, match="store configuration is invalid"):
        dashboard._store_service_binding(
            SimpleNamespace(db_path=tmp_path / "agency.db"),
            _config_state(path=tmp_path / "agency.yaml", store=[]),
        )

    monkeypatch.setattr(dashboard, "read_config_state", lambda _path: state)
    monkeypatch.setattr(
        dashboard,
        "_require_store_service_binding",
        lambda _store, _state: {"store_path": str(tmp_path / "agency.db")},
    )
    active_store = SimpleNamespace(get_roster_entry=lambda _slug: {"agent_slug": "reviewer"})
    with pytest.raises(ConfigConflictError, match="configuration changed"):
        dashboard._require_agent_toggle_precondition(
            active_store,
            state.path,
            "reviewer",
            enabled=False,
            confirmation="DISABLE reviewer",
            expected_disabled=(),
        )

    too_many_fields = "/api/roster?" + "&".join(f"field{index}=x" for index in range(17))
    with pytest.raises(ValueError, match="invalid roster query"):
        dashboard._roster_projection_kind(too_many_fields)


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (ConfigConflictError("stale revision"), HTTPStatus.CONFLICT),
        (ConfigurationError("invalid configuration"), HTTPStatus.BAD_REQUEST),
    ],
)
def test_dashboard_get_maps_expected_configuration_failures(
    error: Exception,
    status: HTTPStatus,
) -> None:
    handler = object.__new__(dashboard.DashboardHTTPHandler)
    handler.path = "/api/config"
    handler._authorise_api_request = lambda **_kwargs: True
    handler._handle_config = lambda: (_ for _ in ()).throw(error)
    responses: list[tuple[HTTPStatus, str]] = []
    handler._json_error = lambda response_status, message: responses.append(
        (response_status, message)
    )

    handler.do_GET()

    assert responses == [(status, str(error))]


def test_dashboard_routing_snapshot_rejects_wrong_config_and_activation_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "agency.yaml"
    handler = _routing_handler(config_path)
    state = _config_state(path=config_path)
    snapshot = SimpleNamespace(
        config=AgencyConfig(config_path=str(tmp_path / "other.yaml")),
        catalog=[],
    )
    monkeypatch.setattr(dashboard, "config_read_lock", lambda _path: nullcontext())
    monkeypatch.setattr(dashboard, "read_config_state", lambda _path: state)
    monkeypatch.setattr(
        dashboard,
        "_require_store_service_binding",
        lambda _store, _state: {"store_path": str(tmp_path / "agency.db")},
    )
    monkeypatch.setattr(dashboard, "capture_routing_snapshot", lambda _store: snapshot)

    with pytest.raises(ConfigurationError, match="configuration identity"):
        handler._routing_operation_snapshot()

    snapshot.config = AgencyConfig(
        config_path=str(config_path),
        agents=AgentActivationConfig(disabled=("reviewer",)),
    )
    with pytest.raises(ConfigConflictError, match="activation policy"):
        handler._routing_operation_snapshot()


def test_dashboard_policy_snapshot_is_content_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = AgencyConfig()
    snapshot = SimpleNamespace(
        config=config,
        catalog=[{"slug": "security-reviewer"}, {"slug": ""}],
    )
    identity = {"config_revision": "sha256:" + ("a" * 64)}
    policy = {"actions": {"review": {"agents": ["security-reviewer"]}}}
    handler = object.__new__(dashboard.DashboardHTTPHandler)
    handler._routing_operation_snapshot = lambda: (snapshot, identity)
    payloads: list[dict[str, Any]] = []
    handler._json_ok = payloads.append
    monkeypatch.setattr(dashboard, "policy_path_for_config", lambda _config: Path("policy.yaml"))
    monkeypatch.setattr(dashboard, "load_policy", lambda _path: policy)

    handler._handle_policy()

    expected_revision = hashlib.sha256(
        json.dumps(
            policy,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    assert payloads == [
        {
            "schema_version": "agency.policy_snapshot.v1",
            "policy": policy,
            "active_slugs": ["security-reviewer"],
            "operation_snapshot": identity,
            "policy_revision": expected_revision,
        }
    ]


def test_dashboard_search_rejects_missing_invalid_and_oversized_queries() -> None:
    handler = object.__new__(dashboard.DashboardHTTPHandler)
    handler.server = SimpleNamespace(store=object())
    handler._master_control = lambda: {"enabled": True}
    with pytest.raises(ValueError, match="query is required"):
        handler._handle_search_broker({})
    with pytest.raises(ValueError, match="limit must be an integer"):
        handler._handle_search_broker({"query": "review", "limit": True})

    config = AgencyConfig()
    config = replace(config, selector=replace(config.selector, max_user_msg_len=3))
    handler._routing_operation_snapshot = lambda: (
        SimpleNamespace(config=config, catalog=[]),
        {},
    )
    with pytest.raises(ValueError, match="configured maximum"):
        handler._handle_search_broker({"query": "review", "limit": 1})


def test_litellm_uses_configured_url_and_disabled_adapter_is_a_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = AgencyConfig()
    adapter = LiteLLMAdapter(config=config)
    assert adapter.base_url == config.adapters.litellm.base_url

    disabled = replace(
        config,
        adapters=replace(
            config.adapters,
            litellm=replace(config.adapters.litellm, enabled="false"),
        ),
    )
    monkeypatch.setattr(
        "agency_runtime.core.runtime_control.master_enabled",
        lambda: True,
    )
    assert LiteLLMAdapter(config=disabled).pre_call_handler("session", "task", "model") is None


def test_litellm_callback_resolves_config_from_lazily_created_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = object()
    config = AgencyConfig()
    callback = AgencyLiteLLMCallback()
    callback._adapter = LiteLLMAdapter()
    callback._adapter._store = store
    observed: list[object] = []

    def resolve(bound_store: object) -> AgencyConfig:
        observed.append(bound_store)
        return config

    monkeypatch.setattr(litellm_callback, "config_for_store", resolve)

    assert callback.config is config
    assert observed == [store]


def test_selector_projection_discards_non_list_taxonomy() -> None:
    projected = selector_projection.selector_roster_projection(
        {
            "slug": "reviewer",
            "categories": "not-a-list",
            "capabilities": {"review": True},
        }
    )

    assert projected["categories"] == []
    assert projected["capabilities"] == []


def test_custom_policy_rejects_unsafe_file_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "policy.yaml"
    path.write_text("actions: {}\n", encoding="utf-8")
    monkeypatch.setattr(
        selector_policy,
        "_read_trusted_custom_policy",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(UnsafeFileError("linked")),
    )

    with pytest.raises(selector_policy.PolicyIdentityError, match="regular non-link"):
        selector_policy.load_policy(path)


def test_roster_policy_and_snapshot_counter_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        roster_store,
        "load_config",
        lambda _path=None: SimpleNamespace(
            agents=SimpleNamespace(disabled=("reviewer", "security-reviewer"))
        ),
    )
    assert roster_store._disabled_agent_slugs() == frozenset({"reviewer", "security-reviewer"})

    store = Store(tmp_path / "agency.db")
    with pytest.raises(ValueError, match="limit is required"):
        store.get_active_roster_page_snapshot(limit=None)  # type: ignore[arg-type]

    conn = store._connect()
    try:
        conn.execute("DELETE FROM store_counters WHERE name = 'roster-generation'")
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(RuntimeError, match="counter is unavailable"):
        store.get_active_roster_page_snapshot(limit=1)
    with pytest.raises(RuntimeError, match="counter is unavailable"):
        store.get_active_roster_entry_snapshot("reviewer")


def test_sqlite_rejects_non_integer_roster_generation_counter() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("CREATE TABLE store_counters (name TEXT PRIMARY KEY, value)")
        conn.execute(
            "INSERT INTO store_counters (name, value) VALUES ('roster-generation', 'invalid')"
        )
        with pytest.raises(RuntimeError, match="counter integrity"):
            sqlite_store._validate_roster_generation_counter(conn)
    finally:
        conn.close()


def test_restricted_token_cause_handles_cyclic_exception_context() -> None:
    first = RuntimeError("first")
    second = RuntimeError("second")
    first.__context__ = second
    second.__context__ = first

    assert windows_acl.restricted_windows_token_cause(first) is None


@pytest.mark.parametrize(
    ("path", "message"),
    [
        (7, "must be a string"),
        ("http://127.0.0.1/api/runtime", "endpoint is invalid"),
        ("/api/runtime?refresh=1", "does not accept a query"),
    ],
)
def test_dashboard_control_target_rejects_noncanonical_boundaries(
    path: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        dashboard_runtime._dashboard_control_target(path)  # type: ignore[arg-type]


def test_store_binding_rejects_incomplete_missing_and_changed_identities(
    tmp_path: Path,
) -> None:
    with pytest.raises(config_binding.StoreConfigBindingError, match="binding is incomplete"):
        config_binding.assert_store_config_binding(
            SimpleNamespace(_configured_config_path=tmp_path / "agency.yaml")
        )

    frozen = tmp_path / "agency.db"
    with pytest.raises(config_binding.StoreConfigBindingError, match="identity is missing"):
        config_binding.assert_store_config_binding(SimpleNamespace(_frozen_db_path=frozen))

    with pytest.raises(config_binding.StoreConfigBindingError, match="identity changed"):
        config_binding.assert_store_config_binding(
            SimpleNamespace(_frozen_db_path=frozen, db_path=object())
        )

    incomplete = SimpleNamespace(
        _frozen_db_path=frozen,
        db_path=frozen,
        _configured_config_path=tmp_path / "agency.yaml",
        _configured_store_path=None,
        _store_path_config_derived=True,
        config_path=tmp_path / "agency.yaml",
    )
    with pytest.raises(config_binding.StoreConfigBindingError, match="binding is incomplete"):
        config_binding.assert_store_config_binding(incomplete)

    wrong_config = SimpleNamespace(
        _frozen_db_path=frozen,
        db_path=frozen,
        _configured_config_path=tmp_path / "agency.yaml",
        _configured_store_path=frozen,
        _store_path_config_derived=True,
        config_path=None,
    )
    with pytest.raises(config_binding.StoreConfigBindingError, match="identity changed"):
        config_binding.assert_store_config_binding(
            wrong_config,
            AgencyConfig(config_path=str(tmp_path / "agency.yaml")),
        )


def test_store_binding_covers_redundant_identity_failure_boundaries(tmp_path: Path) -> None:
    config_path = tmp_path / "agency.yaml"
    other_config = tmp_path / "other.yaml"
    db_path = tmp_path / "agency.db"

    def bound_store(*, public_config: object = config_path) -> SimpleNamespace:
        return SimpleNamespace(
            _frozen_db_path=db_path,
            db_path=db_path,
            _configured_config_path=config_path,
            _configured_store_path=db_path,
            _store_path_config_derived=False,
            config_path=public_config,
        )

    config_binding.assert_store_requested_runtime_identity(SimpleNamespace())

    with pytest.raises(config_binding.StoreConfigBindingError, match="identity changed"):
        config_binding.assert_store_config_binding(bound_store(public_config=object()))

    with pytest.raises(config_binding.StoreConfigBindingError, match="identity changed"):
        config_binding.assert_store_config_binding(
            bound_store(),
            AgencyConfig(config_path=str(other_config)),
        )

    with pytest.raises(config_binding.StoreConfigBindingError, match="runtime identity changed"):
        config_binding.assert_store_requested_runtime_identity(
            bound_store(public_config=object()),
            config_path=config_path,
        )

    with pytest.raises(config_binding.StoreConfigBindingError, match="runtime identity changed"):
        config_binding.assert_store_requested_runtime_identity(
            bound_store(public_config=other_config),
            config_path=config_path,
        )
