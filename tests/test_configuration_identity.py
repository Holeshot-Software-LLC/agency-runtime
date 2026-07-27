"""Security and reboot contracts for the durable configuration identity."""

from __future__ import annotations

import json
import platform
import stat
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import agency_runtime.core.config_binding as config_binding_module
from agency_runtime.core import configuration_identity as identity
from agency_runtime.core import configuration_persistence as persistence
from agency_runtime.core import process_argv
from agency_runtime.core.config import load_config, reset_config_cache
from agency_runtime.core.config_binding import (
    StoreConfigBindingError,
    assert_store_config_binding,
    config_for_store,
)
from agency_runtime.core.configuration import apply_config_operations, read_config_state
from agency_runtime.core.configuration_contracts import ConfigurationError
from agency_runtime.core.configuration_identity import (
    DASHBOARD_MANIFEST_RELATIVE_PATH,
    resolve_config_identity_path,
    trusted_dashboard_config_path,
)
from agency_runtime.core.dashboard_service_core import _config_path, _context
from agency_runtime.core.dashboard_service_manifest import _manifest_value, _write_manifest
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.process_argv import snapshot_persistent_artifacts
from agency_runtime.core.routing_snapshot import capture_routing_snapshot
from agency_runtime.core.selector import policy as policy_module
from agency_runtime.core.selector.explain import explain_route
from agency_runtime.core.store import sqlite as sqlite_store
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.dashboard import run_dashboard
from tests.runtime_support import trusted_test_interpreter

pytestmark = pytest.mark.runtime_configuration_identity


@pytest.fixture(autouse=True)
def _isolated_config_environment(
    monkeypatch: pytest.MonkeyPatch,
    private_installer_launcher_files: tuple[Path, Path],
):
    _executable, bootstrap = private_installer_launcher_files
    monkeypatch.setattr(process_argv, "agency_bootstrap_path", lambda: str(bootstrap))
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_service_core.prepare_private_package_runtime",
        lambda path: str(bootstrap) if Path(path) == bootstrap else str(path),
    )
    monkeypatch.delenv("AGENCY_CONFIG_PATH", raising=False)
    reset_config_cache()
    try:
        yield
    finally:
        reset_config_cache()


def _installed_manifest(
    home: Path, config: Path, platform_name: str
) -> tuple[Path, dict[str, Any]]:
    ctx = _context(
        home_dir=home,
        platform_name=platform_name,
        config_path=config,
        python_executable=str(trusted_test_interpreter()),
    )
    assert ctx is not None
    ctx = replace(
        ctx,
        launcher_artifacts=snapshot_persistent_artifacts((ctx.worker_argv[0], ctx.worker_argv[3])),
    )
    _write_manifest(ctx)
    return ctx.manifest_path, _manifest_value(ctx)


def test_store_without_db_path_uses_its_bound_config_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process_config = tmp_path / "process" / "agency.yaml"
    process_config.parent.mkdir()
    process_config.write_text("store:\n  db_path: process.db\n", encoding="utf-8")
    custom_config = tmp_path / "custom" / "agency.yaml"
    custom_config.parent.mkdir()
    custom_config.write_text("store:\n  db_path: runtime/custom.db\n", encoding="utf-8")
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(process_config))

    store = Store(config_path=custom_config)

    assert store.config_path == custom_config.resolve()
    assert store.db_path == custom_config.parent / "runtime" / "custom.db"
    assert store.db_path.exists()
    assert not (process_config.parent / "process.db").exists()


def test_store_config_binding_rejects_public_path_tampering_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "agency.yaml"
    config_path.write_text(f"store:\n  db_path: {tmp_path / 'agency.db'}\n", encoding="utf-8")
    store = Store(config_path=config_path)
    store.config_path = tmp_path / "poisoned.yaml"
    monkeypatch.setattr(
        config_binding_module,
        "load_config",
        lambda *_args, **_kwargs: pytest.fail("tampered config path was read"),
    )

    with pytest.raises(StoreConfigBindingError, match="configuration identity changed"):
        assert_store_config_binding(store)


@pytest.mark.parametrize("drift_source", ["file", "environment"])
def test_config_derived_store_fails_closed_after_live_store_target_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift_source: str,
) -> None:
    config_path = tmp_path / "agency.yaml"
    original_db = tmp_path / "original.db"
    replacement_db = tmp_path / "replacement.db"
    config_path.write_text(f"store:\n  db_path: {original_db}\n", encoding="utf-8")
    monkeypatch.delenv("AGENCY_DB_PATH", raising=False)
    store = Store(config_path=config_path)

    assert store.db_path == original_db
    assert config_for_store(store).store.resolved_path() == original_db

    if drift_source == "file":
        state = read_config_state(config_path)
        apply_config_operations(
            [{"op": "set", "path": "store.db_path", "value": str(replacement_db)}],
            expected_revision=state.revision,
            path=config_path,
        )
    else:
        monkeypatch.setenv("AGENCY_DB_PATH", str(replacement_db))

    with pytest.raises(StoreConfigBindingError, match="configured Store path changed"):
        config_for_store(store)
    with pytest.raises(StoreConfigBindingError, match="configured Store path changed"):
        capture_routing_snapshot(store)
    with pytest.raises(StoreConfigBindingError, match="configured Store path changed"):
        store.get_disabled_agent_slugs()
    with pytest.raises(StoreConfigBindingError, match="configured Store path changed"):
        store.create_run(trace_id=f"trace-{drift_source}-store-target-drift")
    assert store.db_path == original_db


@pytest.mark.parametrize("drift_source", ["file", "environment"])
def test_explicit_db_store_remains_authoritative_after_config_target_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift_source: str,
) -> None:
    config_path = tmp_path / "agency.yaml"
    configured_db = tmp_path / "configured.db"
    replacement_db = tmp_path / "replacement.db"
    explicit_db = tmp_path / "explicit.db"
    config_path.write_text(f"store:\n  db_path: {configured_db}\n", encoding="utf-8")
    monkeypatch.delenv("AGENCY_DB_PATH", raising=False)
    store = Store(explicit_db, config_path=config_path)

    if drift_source == "file":
        state = read_config_state(config_path)
        apply_config_operations(
            [{"op": "set", "path": "store.db_path", "value": str(replacement_db)}],
            expected_revision=state.revision,
            path=config_path,
        )
    else:
        monkeypatch.setenv("AGENCY_DB_PATH", str(replacement_db))

    live = config_for_store(store)
    assert live.store.resolved_path() == replacement_db
    assert store.db_path == explicit_db
    assert store.get_disabled_agent_slugs() == frozenset()


def test_explicit_config_snapshot_bypasses_later_store_target_file_drift(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "agency.yaml"
    original_db = tmp_path / "original.db"
    replacement_db = tmp_path / "replacement.db"
    config_path.write_text(f"store:\n  db_path: {original_db}\n", encoding="utf-8")
    store = Store(config_path=config_path)
    explicit = config_for_store(store)
    state = read_config_state(config_path)
    apply_config_operations(
        [{"op": "set", "path": "store.db_path", "value": str(replacement_db)}],
        expected_revision=state.revision,
        path=config_path,
    )

    assert config_for_store(store, explicit) is explicit


@pytest.mark.parametrize("config_derived", [False, True])
def test_store_rejects_public_database_target_mutation(
    tmp_path: Path,
    config_derived: bool,
) -> None:
    config_path = tmp_path / "agency.yaml"
    configured_db = tmp_path / "configured.db"
    explicit_db = tmp_path / "explicit.db"
    replacement_db = tmp_path / "replacement.db"
    config_path.write_text(f"store:\n  db_path: {configured_db}\n", encoding="utf-8")
    store = (
        Store(config_path=config_path)
        if config_derived
        else Store(explicit_db, config_path=config_path)
    )
    explicit_config = load_config(config_path, reload=True)

    store.db_path = replacement_db

    with pytest.raises(StoreConfigBindingError, match="Store database identity changed"):
        config_for_store(store)
    with pytest.raises(StoreConfigBindingError, match="Store database identity changed"):
        config_for_store(store, explicit_config)
    with pytest.raises(StoreConfigBindingError, match="Store database identity changed"):
        store.create_run(trace_id="trace-db-path-mutation")
    assert not replacement_db.exists()


def test_store_explicit_db_path_precedes_bound_config_db_path(tmp_path: Path) -> None:
    custom_config = tmp_path / "custom" / "agency.yaml"
    custom_config.parent.mkdir()
    custom_config.write_text("store:\n  db_path: ignored.db\n", encoding="utf-8")
    explicit_db = tmp_path / "explicit" / "agency.db"

    store = Store(explicit_db, config_path=custom_config)

    assert store.db_path == explicit_db
    assert explicit_db.exists()
    assert not (custom_config.parent / "ignored.db").exists()


def test_store_validates_bound_config_before_explicit_db_path_mutation(
    tmp_path: Path,
) -> None:
    invalid_config = tmp_path / "invalid.yaml"
    invalid_config.write_text("observability: false\n", encoding="utf-8")
    explicit_db = tmp_path / "must-not-exist" / "agency.db"

    with pytest.raises(ValueError, match="observability: must be a mapping"):
        Store(explicit_db, config_path=invalid_config)

    assert not explicit_db.parent.exists()


def test_store_without_db_path_rejects_invalid_bound_config(tmp_path: Path) -> None:
    invalid_config = tmp_path / "invalid.yaml"
    invalid_config.write_text("store: [not-a-mapping]\n", encoding="utf-8")

    with pytest.raises(ValueError, match="store: must be a mapping"):
        Store(config_path=invalid_config)


@pytest.mark.parametrize("content", ["[]\n", "true\n", "configuration\n"])
def test_store_never_opens_fallback_for_non_mapping_config_root(
    tmp_path: Path,
    content: str,
) -> None:
    invalid_config = tmp_path / "invalid.yaml"
    invalid_config.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="configuration root must be a mapping"):
        Store(config_path=invalid_config)

    assert list(tmp_path.rglob("*.db")) == []


@pytest.mark.parametrize(
    "content",
    [
        "providers: {}\n",
        "providers:\n  - invalid-entry\n",
        "observability: false\n",
        "unsupported: true\n",
    ],
)
def test_store_never_opens_fallback_for_invalid_persisted_sections(
    tmp_path: Path,
    content: str,
) -> None:
    invalid_config = tmp_path / "invalid.yaml"
    invalid_config.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError):
        Store(config_path=invalid_config)

    assert list(tmp_path.rglob("*.db")) == []


@pytest.mark.parametrize(
    ("process_capture", "custom_capture", "expected_message"),
    [(True, False, ""), (False, True, "bound config content")],
)
def test_store_content_capture_uses_bound_config_not_process_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    process_capture: bool,
    custom_capture: bool,
    expected_message: str,
) -> None:
    process_config = tmp_path / "process.yaml"
    process_config.write_text(
        f"observability:\n  capture_content: {str(process_capture).lower()}\n",
        encoding="utf-8",
    )
    custom_config = tmp_path / "custom.yaml"
    custom_config.write_text(
        f"observability:\n  capture_content: {str(custom_capture).lower()}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(process_config))
    store = Store(tmp_path / "agency.db", config_path=custom_config)

    run_id = store.create_run(
        trace_id="bound-config-trace",
        session_id="bound-config-session",
        user_message="bound config content",
    )

    connection = store._connect()
    try:
        row = connection.execute(
            "SELECT user_message FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    finally:
        connection.close()
    assert row["user_message"] == expected_message
    preflight_trace = "bound-preflight-trace"
    store.begin_preflight_attempt(
        session_id="bound-config-session",
        trace_id=preflight_trace,
        request_fingerprint="a" * 64,
        request_kind="nontrivial",
        user_message="bound preflight content",
    )
    delegation_trace = "bound-delegation-trace"
    store.record_delegation(
        trace_id=delegation_trace,
        session_id="bound-config-session",
        status="failed",
        error="bound delegation content",
    )
    connection = store._connect()
    try:
        preflight_row = connection.execute(
            "SELECT user_message FROM runs WHERE trace_id = ?",
            (preflight_trace,),
        ).fetchone()
    finally:
        connection.close()
    delegation = store.get_delegations(delegation_trace)[0]
    if custom_capture:
        assert preflight_row["user_message"] == "bound preflight content"
        assert delegation["error"] == "bound delegation content"
    else:
        assert preflight_row["user_message"] == ""
        assert "bound delegation content" not in delegation["error"]


def test_bound_store_schema_migration_uses_bound_privacy_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process_config = tmp_path / "process.yaml"
    process_config.write_text(
        "observability:\n  capture_content: true\nagents:\n  disabled:\n    - code-reviewer\n",
        encoding="utf-8",
    )
    custom_config = tmp_path / "custom.yaml"
    custom_config.write_text(
        "observability:\n  capture_content: false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(process_config))
    observed: list[bool] = []

    def observe_schema_policy(_connection, *, now, capture_content) -> None:
        assert callable(now)
        observed.append(capture_content())

    monkeypatch.setattr(
        sqlite_store,
        "migrate_schema",
        observe_schema_policy,
    )

    Store(tmp_path / "agency.db", config_path=custom_config)

    assert observed == [False]


def test_store_schema_uses_the_pre_mutation_validated_capture_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "agency.yaml"
    config_path.write_text(
        "observability:\n  capture_content: true\n",
        encoding="utf-8",
    )
    real_load_config = load_config
    load_calls = 0
    observed: list[bool] = []

    def load_then_corrupt(path, *, reload=False):
        nonlocal load_calls
        load_calls += 1
        cfg = real_load_config(path, reload=reload)
        config_path.write_text("observability: false\n", encoding="utf-8")
        return cfg

    def observe_schema_policy(_connection, *, now, capture_content) -> None:
        assert callable(now)
        observed.append(capture_content())

    monkeypatch.setattr(sqlite_store, "load_config", load_then_corrupt)
    monkeypatch.setattr(sqlite_store, "migrate_schema", observe_schema_policy)

    Store(tmp_path / "agency.db", config_path=config_path)

    assert load_calls == 1
    assert observed == [True]


def test_bound_store_reloads_live_capture_policy_and_fails_private_if_invalid(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "agency.yaml"
    config_path.write_text(
        "observability:\n  capture_content: false\n",
        encoding="utf-8",
    )
    store = Store(tmp_path / "agency.db", config_path=config_path)

    hidden_id = store.create_run(
        trace_id="live-capture-hidden",
        user_message="hidden content",
    )
    config_path.write_text(
        "observability:\n  capture_content: true\n",
        encoding="utf-8",
    )
    visible_id = store.create_run(
        trace_id="live-capture-visible",
        user_message="visible content",
    )
    config_path.write_text("observability: false\n", encoding="utf-8")
    invalid_id = store.create_run(
        trace_id="live-capture-invalid",
        user_message="must fail private",
    )

    connection = store._connect()
    try:
        messages = {
            str(row["id"]): str(row["user_message"])
            for row in connection.execute(
                "SELECT id, user_message FROM runs WHERE id IN (?, ?, ?)",
                (hidden_id, visible_id, invalid_id),
            )
        }
    finally:
        connection.close()
    assert messages == {
        hidden_id: "",
        visible_id: "visible content",
        invalid_id: "",
    }


def test_default_store_freezes_process_config_identity_at_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process_config = tmp_path / "process.yaml"
    process_config.write_text(
        "observability:\n  capture_content: true\nagents:\n  disabled:\n    - code-reviewer\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(process_config))
    store = Store(tmp_path / "agency.db")
    replacement_config = tmp_path / "replacement.yaml"
    replacement_config.write_text(
        "observability:\n  capture_content: false\nagents:\n  disabled: []\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(replacement_config))

    run_id = store.create_run(
        trace_id="unbound-config-trace",
        user_message="process default content",
    )

    connection = store._connect()
    try:
        row = connection.execute(
            "SELECT user_message FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    finally:
        connection.close()
    assert store.config_path == process_config.resolve()
    assert row["user_message"] == "process default content"
    assert store.get_disabled_agent_slugs() == frozenset({"code-reviewer"})


def test_bound_store_supplies_default_config_to_preflight_and_explain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process_config = tmp_path / "process.yaml"
    process_config.write_text(
        "selector:\n  min_confidence: 0.9\n",
        encoding="utf-8",
    )
    custom_config = tmp_path / "custom.yaml"
    custom_config.write_text(
        "selector:\n  min_confidence: 0.1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(process_config))
    store = Store(tmp_path / "agency.db", config_path=custom_config)
    store._activate_prevalidated_agent(
        {
            "slug": "bound-reviewer",
            "name": "Bound Reviewer",
            "description": "Reviews code changes for correctness.",
            "prompt_body": "Review code changes for correctness and report actionable findings.",
        }
    )
    task = "review this implementation carefully"

    preflight = run_preflight(
        store,
        session_id="bound-routing-session",
        user_message=task,
        host="test",
    )
    explanation = explain_route(
        "bound-explain-session",
        task,
        store.get_active_roster_as_catalog(),
        store=store,
        host="test",
        platform=platform.system().casefold(),
    )

    assert preflight.trivial is False
    assert explanation["routing"]["context_fingerprint"] == preflight.routing["context_fingerprint"]
    connection = store._connect()
    try:
        recipe = json.loads(
            connection.execute(
                "SELECT preflight_result FROM runs WHERE trace_id = ?",
                (preflight.trace_id,),
            ).fetchone()["preflight_result"]
        )
    finally:
        connection.close()
    assert recipe["routing"]["context_fingerprint"] == preflight.routing["context_fingerprint"]
    process_explanation = explain_route(
        "process-explain-session",
        task,
        store.get_active_roster_as_catalog(),
        config=load_config(process_config),
        host="test",
        platform=platform.system().casefold(),
    )
    assert (
        preflight.routing["context_fingerprint"]
        != process_explanation["routing"]["context_fingerprint"]
    )


def test_explicit_preflight_config_precedes_store_binding(
    tmp_path: Path,
) -> None:
    bound_config = tmp_path / "bound.yaml"
    bound_config.write_text(
        "selector:\n  min_confidence: 0.1\n",
        encoding="utf-8",
    )
    explicit_config = tmp_path / "explicit.yaml"
    explicit_config.write_text(
        "selector:\n  min_confidence: 0.9\n",
        encoding="utf-8",
    )
    store = Store(tmp_path / "agency.db", config_path=bound_config)
    task = "review this implementation carefully"

    result = run_preflight(
        store,
        session_id="explicit-routing-session",
        user_message=task,
        host="test",
        config=load_config(explicit_config),
    )
    explicit = explain_route(
        "explicit-config-explain",
        task,
        store.get_active_roster_as_catalog(),
        config=load_config(explicit_config),
        store=store,
        host="test",
        platform=platform.system().casefold(),
    )
    bound = explain_route(
        "bound-config-explain",
        task,
        store.get_active_roster_as_catalog(),
        store=store,
        host="test",
        platform=platform.system().casefold(),
    )

    assert result.trivial is False
    assert result.routing["context_fingerprint"] == explicit["routing"]["context_fingerprint"]
    assert result.routing["context_fingerprint"] != bound["routing"]["context_fingerprint"]


def test_bound_preflight_uses_bound_disabled_agent_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process_config = tmp_path / "process.yaml"
    process_config.write_text("agents:\n  disabled: []\n", encoding="utf-8")
    custom_config = tmp_path / "custom.yaml"
    custom_config.write_text(
        "agents:\n  disabled:\n    - bound-reviewer\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(process_config))
    store = Store(tmp_path / "agency.db", config_path=custom_config)
    store._activate_prevalidated_agent(
        {
            "slug": "bound-reviewer",
            "name": "Bound Reviewer",
            "description": "Reviews code changes for correctness.",
            "prompt_body": "Review code changes for correctness and report actionable findings.",
        }
    )

    result = run_preflight(
        store,
        session_id="disabled-routing-session",
        user_message="review this implementation carefully",
        host="test",
    )

    assert "bound-reviewer" not in result.routing["selected_ids"]
    assert "bound-reviewer" not in {
        agent["slug"]
        for agent in store.get_active_roster_as_catalog(disabled_agents={"bound-reviewer"})
    }


def test_bound_config_without_policy_path_ignores_process_config_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    poison_policy = tmp_path / "poison-policy.yaml"
    poison_policy.write_text(
        "actions:\n"
        "  POISON:\n"
        "    triggers: [review]\n"
        "    always_include:\n"
        "      - slug: poison-agent\n",
        encoding="utf-8",
    )
    process_config = tmp_path / "process.yaml"
    process_config.write_text(
        f"companion_policy_path: {json.dumps(str(poison_policy))}\n",
        encoding="utf-8",
    )
    custom_config = tmp_path / "custom.yaml"
    custom_config.write_text("selector:\n  trivial_msg_threshold: 1\n", encoding="utf-8")
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(process_config))
    monkeypatch.setattr(policy_module, "_DEFAULT_POLICY_PATH", tmp_path / "missing-policy.yaml")
    store = Store(tmp_path / "agency.db", config_path=custom_config)
    catalog = [
        {
            "slug": "poison-agent",
            "name": "Poison Agent",
            "description": "Must only come from the poisoned process policy.",
        },
        {
            "slug": "code-reviewer",
            "name": "Code Reviewer",
            "description": "Reviews code changes for correctness.",
        },
    ]

    explanation = explain_route(
        "bound-policy-session",
        "review this implementation carefully",
        catalog,
        store=store,
    )

    assert "poison-agent" not in explanation["routing"]["companion_ids"]


@pytest.mark.parametrize("platform_name", ["windows", "linux"])
def test_owned_service_manifest_restores_config_identity_after_reboot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    platform_name: str,
) -> None:
    home = tmp_path / platform_name
    custom = (tmp_path / "custom" / platform_name / "agency.yaml").resolve()
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(custom))
    _installed_manifest(home, custom, platform_name)

    # A shell-only override disappears after reboot. The private installed
    # service identity remains the shared CLI/dashboard default.
    monkeypatch.delenv("AGENCY_CONFIG_PATH")
    assert resolve_config_identity_path(home_dir=home, platform_name=platform_name) == custom
    assert (
        persistence.resolve_config_path(
            home_dir=home,
            use_environment=False,
            platform_name=platform_name,
        )
        == custom
    )
    assert (
        _config_path(
            home.resolve(),
            home,
            None,
            platform_name=platform_name,
        )
        == custom
    )


def test_explicit_and_environment_paths_precede_installed_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    installed = (tmp_path / "installed.yaml").resolve()
    _installed_manifest(home, installed, "linux")
    environment = (tmp_path / "environment.yaml").resolve()
    explicit = (tmp_path / "explicit.yaml").resolve()

    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(environment))
    assert resolve_config_identity_path(home_dir=home, platform_name="linux") == environment
    assert resolve_config_identity_path(explicit, home_dir=home, platform_name="linux") == explicit
    assert (
        resolve_config_identity_path(
            home_dir=home,
            use_environment=False,
            platform_name="linux",
        )
        == installed
    )


ManifestMutation = Callable[[dict[str, Any], Path], None]


def _set(field: str, value: object) -> ManifestMutation:
    def mutate(document: dict[str, Any], _tmp_path: Path) -> None:
        document[field] = value

    return mutate


def _extra(document: dict[str, Any], _tmp_path: Path) -> None:
    document["unexpected"] = True


def _relative_config(document: dict[str, Any], _tmp_path: Path) -> None:
    document["config_path"] = "relative/agency.yaml"
    document["worker_argv"][-1] = "relative/agency.yaml"


def _worker_config_mismatch(document: dict[str, Any], tmp_path: Path) -> None:
    document["worker_argv"][-1] = str((tmp_path / "other.yaml").resolve())


def _relative_worker(document: dict[str, Any], _tmp_path: Path) -> None:
    document["worker_argv"][0] = "python"


def _short_worker(document: dict[str, Any], _tmp_path: Path) -> None:
    document["worker_argv"] = document["worker_argv"][:-1]


def _non_string_worker(document: dict[str, Any], _tmp_path: Path) -> None:
    document["worker_argv"][1] = 7


def _wrong_worker_shape(document: dict[str, Any], _tmp_path: Path) -> None:
    document["worker_argv"][2] = "attacker.cli"


def _invalid_worker_text(document: dict[str, Any], _tmp_path: Path) -> None:
    document["worker_argv"][0] = "bad\npython"


def _noncanonical_config(document: dict[str, Any], tmp_path: Path) -> None:
    value = str(tmp_path / "nested" / ".." / "agency.yaml")
    document["config_path"] = value
    document["worker_argv"][-1] = value


def _invalid_config_text(document: dict[str, Any], _tmp_path: Path) -> None:
    document["config_path"] = "bad\nconfig.yaml"
    document["worker_argv"][-1] = "bad\nconfig.yaml"


@pytest.mark.parametrize(
    "mutate",
    [
        _set("schema_version", True),
        _set("schema_version", 3),
        _set("owner", "attacker"),
        _set("service", "other"),
        _set("platform", "windows"),
        _set("manager", "root-service"),
        _set("registration", "other.service"),
        _set("package_version", ""),
        _set("package_version", 1),
        _set("package_version", "x" * 129),
        _set("runtime_fingerprint", "sha256:not-a-digest"),
        _set("runtime_fingerprint", 1),
        _set("runtime_fingerprint", "sha256:" + "0" * 64),
        _set("launcher_artifacts", []),
        _set("installed_at", "not-a-date"),
        _set("installed_at", 1),
        _set("installed_at", "x" * 129),
        _set("installed_at", "2026-07-15T12:00:00"),
        _set("worker_argv", "not-a-list"),
        _set("config_path", None),
        _extra,
        _relative_config,
        _noncanonical_config,
        _invalid_config_text,
        _worker_config_mismatch,
        _relative_worker,
        _short_worker,
        _non_string_worker,
        _wrong_worker_shape,
        _invalid_worker_text,
    ],
    ids=[
        "boolean-schema",
        "future-schema",
        "owner",
        "service",
        "platform",
        "manager",
        "registration",
        "package-version",
        "package-version-type",
        "package-version-long",
        "fingerprint",
        "fingerprint-type",
        "fingerprint-mismatch",
        "launcher-artifacts",
        "installed-at",
        "installed-at-type",
        "installed-at-long",
        "installed-at-naive",
        "worker-type",
        "config-path-type",
        "extra-field",
        "relative-config",
        "noncanonical-config",
        "invalid-config-text",
        "worker-config-mismatch",
        "relative-worker",
        "short-worker",
        "non-string-worker",
        "wrong-worker-shape",
        "invalid-worker-text",
    ],
)
def test_untrusted_manifest_never_redirects_default_config(
    tmp_path: Path,
    mutate: ManifestMutation,
) -> None:
    home = tmp_path / "home"
    custom = (tmp_path / "custom.yaml").resolve()
    manifest_path, document = _installed_manifest(home, custom, "linux")
    mutate(document, tmp_path)
    manifest_path.write_text(json.dumps(document), encoding="utf-8")

    expected = (home / ".agency-runtime" / "agency.yaml").resolve()
    assert trusted_dashboard_config_path(home, platform_name="linux") is None
    assert (
        resolve_config_identity_path(
            home_dir=home,
            use_environment=False,
            platform_name="linux",
        )
        == expected
    )


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        b"[]",
        b'{"owner":"one","owner":"two"}',
        b"{" + b" " * (64 * 1024) + b"}",
    ],
    ids=["invalid-json", "non-object", "duplicate-key", "oversized"],
)
def test_malformed_or_oversized_manifest_is_ignored(tmp_path: Path, payload: bytes) -> None:
    home = tmp_path / "home"
    manifest_path = home / DASHBOARD_MANIFEST_RELATIVE_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(payload)

    assert trusted_dashboard_config_path(home, platform_name="linux") is None


def test_launcher_binding_rejects_malformed_drifted_and_unbound_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manifest_path, document = _installed_manifest(
        tmp_path / "home",
        (tmp_path / "custom.yaml").resolve(),
        "linux",
    )
    worker = document["worker_argv"]
    artifacts = document["launcher_artifacts"]

    assert identity._valid_launcher_binding("invalid", worker) is False
    assert identity._valid_launcher_binding(artifacts, None) is False
    assert identity._valid_launcher_binding(artifacts, [worker[0]]) is False
    assert identity._valid_launcher_binding([None], worker) is False

    extra = json.loads(json.dumps(artifacts))
    extra[0]["unexpected"] = True
    assert identity._valid_launcher_binding(extra, worker) is False

    invalid_digest = json.loads(json.dumps(artifacts))
    invalid_digest[0]["sha256"] = "invalid"
    assert identity._valid_launcher_binding(invalid_digest, worker) is False
    assert identity._valid_launcher_binding(artifacts[:1], worker) is False

    unbound = json.loads(json.dumps(artifacts))
    unbound[0]["lexical_path"] = str((tmp_path / "other-python").resolve())
    assert identity._valid_launcher_binding(unbound, worker) is False

    def drifted(_artifacts) -> None:
        raise OSError("launcher drifted")

    monkeypatch.setattr(identity, "revalidate_persistent_artifacts", drifted)
    assert identity._valid_launcher_binding(artifacts, worker) is False


def test_manifest_must_be_a_regular_non_link_file(tmp_path: Path) -> None:
    home = tmp_path / "home"
    manifest_path = home / DASHBOARD_MANIFEST_RELATIVE_PATH
    manifest_path.mkdir(parents=True)
    assert trusted_dashboard_config_path(home, platform_name="linux") is None

    manifest_path.rmdir()
    target = tmp_path / "manifest-target.json"
    target.write_text("{}", encoding="utf-8")
    try:
        manifest_path.symlink_to(target)
    except OSError:
        pytest.skip("this host does not permit an unprivileged file symlink")
    assert trusted_dashboard_config_path(home, platform_name="linux") is None


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        (SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0), False),
        (SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400), False),
        (SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0), False),
    ],
)
def test_manifest_parent_chain_rejects_links_reparse_points_and_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    metadata: SimpleNamespace,
    expected: bool,
) -> None:
    home = tmp_path.resolve()
    manifest = home / DASHBOARD_MANIFEST_RELATIVE_PATH
    monkeypatch.setattr(identity.os, "lstat", lambda _path: metadata)
    assert identity._real_manifest_parent(home, manifest) is expected
    monkeypatch.setattr(identity, "_real_manifest_parent", lambda *_args: False)
    assert identity._manifest_document(home) is None


def test_config_loader_uses_current_platform_installed_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_platform = "windows" if platform.system().casefold() == "windows" else "linux"
    home = tmp_path / "home"
    custom = (tmp_path / "custom" / "agency.yaml").resolve()
    custom.parent.mkdir(parents=True)
    custom.write_text("agents:\n  disabled: [code-reviewer]\n", encoding="utf-8")
    _installed_manifest(home, custom, target_platform)
    monkeypatch.setattr(persistence.Path, "home", classmethod(lambda _cls: home))

    assert persistence.resolve_config_path() == custom
    assert load_config(reload=True).agents.disabled == ("code-reviewer",)


@pytest.mark.parametrize(
    "value",
    ["relative.yaml", "", "bad\npath.yaml", "bad\x7fpath.yaml", "x" * 4097],
)
def test_explicit_config_identity_rejects_unsafe_paths(value: str) -> None:
    if value == "relative.yaml":
        # Explicit CLI paths are intentionally made absolute relative to the
        # caller, while manifest paths must already be absolute and canonical.
        assert resolve_config_identity_path(value).is_absolute()
        return
    with pytest.raises(ValueError, match="config path is invalid"):
        resolve_config_identity_path(value)


@pytest.mark.parametrize("linked_component", ["file", "parent"])
def test_config_identity_rejects_existing_link_components(
    tmp_path: Path,
    linked_component: str,
) -> None:
    destination = tmp_path / "destination"
    destination.mkdir()
    target = destination / "agency.yaml"
    target.write_text("profile: standard\n", encoding="utf-8")
    if linked_component == "file":
        candidate = tmp_path / "agency.yaml"
        link_target = target
        directory = False
    else:
        redirected_parent = tmp_path / "redirected"
        candidate = redirected_parent / "agency.yaml"
        link_target = destination
        directory = True
    try:
        (candidate if linked_component == "file" else candidate.parent).symlink_to(
            link_target,
            target_is_directory=directory,
        )
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(ConfigurationError, match="configuration path symlink or reparse"):
        resolve_config_identity_path(candidate)


def test_cached_config_rejects_file_replaced_by_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / "agency.yaml"
    config.write_text("profile: standard\n", encoding="utf-8")
    target = tmp_path / "redirected.yaml"
    target.write_text("store:\n  db_path: redirected.db\n", encoding="utf-8")
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config))
    assert load_config(reload=True).config_path == str(config.absolute())
    config.unlink()
    try:
        config.symlink_to(target)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(ConfigurationError, match="configuration path symlink or reparse"):
        load_config()

    assert not (tmp_path / "redirected.db").exists()


def test_public_config_read_and_apply_reject_link_identity(tmp_path: Path) -> None:
    target = tmp_path / "target.yaml"
    original = b"profile: standard\n"
    target.write_bytes(original)
    link = tmp_path / "agency.yaml"
    try:
        link.symlink_to(target)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(ConfigurationError, match="configuration path symlink or reparse"):
        read_config_state(link)
    with pytest.raises(ConfigurationError, match="configuration path symlink or reparse"):
        apply_config_operations(
            [{"op": "set", "path": "profile", "value": "power"}],
            expected_revision="sha256:" + "0" * 64,
            path=link,
        )

    assert target.read_bytes() == original
    assert link.is_symlink()


def test_cli_and_dashboard_startup_reject_link_config_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from agency_runtime.cli.main import main

    target = tmp_path / "target.yaml"
    original = b"profile: standard\n"
    target.write_bytes(original)
    link = tmp_path / "agency.yaml"
    try:
        link.symlink_to(target)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(link))

    assert main(["config", "path"]) == 1
    assert "refusing configuration path symlink or reparse point" in capsys.readouterr().err
    with pytest.raises(ConfigurationError, match="configuration path symlink or reparse"):
        run_dashboard(open_browser=False, config_path=link)

    assert target.read_bytes() == original
    assert link.is_symlink()


def test_identity_helpers_reject_unsupported_platform_and_nontext_paths(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    custom = (tmp_path / "custom.yaml").resolve()
    manifest_path, document = _installed_manifest(home, custom, "linux")
    document["platform"] = "darwin"
    manifest_path.write_text(json.dumps(document), encoding="utf-8")
    assert trusted_dashboard_config_path(home, platform_name="darwin") is None
    assert identity._platform_name("plan9") == "plan9"
    assert identity._canonical_absolute_path(None) is None
    assert trusted_dashboard_config_path("bad\nhome", platform_name="linux") is None
    with pytest.raises(ValueError, match="must be text"):
        resolve_config_identity_path(b"bytes-path")  # type: ignore[arg-type]
    assert resolve_config_identity_path(home_dir=tmp_path).is_absolute()
