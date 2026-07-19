"""Final deterministic branch coverage for runtime, Store, and protocol seams."""

from __future__ import annotations

import errno
import json
import stat
import sys
from hashlib import sha256
from pathlib import Path
from threading import Lock
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import (
    host_control,
    preflight,
    preflight_recipe,
    runtime_control,
    smoke,
    specialist_context,
)
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.evals import delegation as delegation_eval
from agency_runtime.core.header import contract as header_contract
from agency_runtime.core.resident_manager_binding import build_resident_manager_binding
from agency_runtime.core.selector import pipeline, policy
from agency_runtime.core.store import delegation_activation, initialization_lock, security
from agency_runtime.core.store import preflight as store_preflight
from agency_runtime.core.store import roster as store_roster
from agency_runtime.core.store import sqlite as store_sqlite
from agency_runtime.server import http, mcp, mcp_tools


class _Result:
    def __init__(self, row: Any = None, *, rows: list[Any] | None = None, rowcount: int = 1):
        self._row = row
        self._rows = [] if rows is None else rows
        self.rowcount = rowcount

    def fetchone(self) -> Any:
        return self._row

    def fetchall(self) -> list[Any]:
        return self._rows

    def __iter__(self):
        return iter(self._rows)


def _metadata(*, mode: int, inode: int = 7, device: int = 3, links: int = 1) -> Any:
    return SimpleNamespace(
        st_mode=mode,
        st_ino=inode,
        st_dev=device,
        st_nlink=links,
        st_uid=0,
        st_size=10,
        st_mtime=1.0,
        st_ctime=1.0,
        st_mtime_ns=1,
        st_ctime_ns=1,
        st_file_attributes=0,
    )


def test_delegation_eval_rejects_a_missing_adapter_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeStore:
        def __init__(self, _path: Path) -> None:
            pass

        @staticmethod
        def get_model_receipt(_trace_id: str) -> None:
            return None

    adapter = SimpleNamespace(
        host_name="missing-host",
        post_api_request_handler=lambda **_kwargs: None,
    )
    monkeypatch.setattr(delegation_eval, "Store", FakeStore)
    monkeypatch.setattr(delegation_eval, "_make_adapter", lambda *_args: adapter)
    monkeypatch.setattr(delegation_eval, "_create_eval_turn", lambda *_args, **_kwargs: None)

    with pytest.raises(AssertionError, match="model receipt is missing"):
        delegation_eval._case_all_adapters_capture_model_receipts()


def _activation_snapshot() -> dict[str, Any]:
    event = {
        "id": "event",
        "activation_receipt_id": "activation",
        "work_unit_id": "unit",
        "status": "completed",
        "executed_worker_id": "worker",
        "native_run_id": "native",
        "retrieved_specialist_slug": "reviewer",
        "retrieved_specialist_version": "1",
        "retrieved_specialist_prompt_hash": "hash",
    }
    activation = {
        "id": "activation",
        "session_id": "session",
        "trace_id": "trace",
        "work_unit_id": "unit",
        "worker_kind": "generic-worker",
        "worker_id": "worker",
        "native_run_id": "native",
        "consumed_at": "now",
        "delegation_event_id": "event",
        "specialist_slug": "reviewer",
        "specialist_version": "1",
        "specialist_prompt_hash": "hash",
    }
    return {
        "delivery_mode": "isolated",
        "request_kind": "nontrivial",
        "selected_specialists": [{"slug": "reviewer", "version": "1", "hash": "hash"}],
        "specialist_activations": [activation],
        "delegations": [event],
        "specialists": ["reviewer"],
        "unit_agent_plan": [{"work_unit_id": "unit", "recommended_agent": "reviewer"}],
    }


def test_header_specialist_identity_and_plan_validation_errors() -> None:
    with pytest.raises(header_contract.EvidenceCorrelationError, match="activation evidence"):
        header_contract._specialist_identity({}, activation=False)
    with pytest.raises(header_contract.EvidenceCorrelationError, match="unit-agent plan"):
        header_contract._expected_activation_identities([], object())
    with pytest.raises(header_contract.EvidenceCorrelationError, match="unit-agent plan"):
        header_contract._expected_activation_identities(
            [{"slug": "reviewer", "version": "1", "hash": "hash"}],
            [{"work_unit_id": "", "recommended_agent": "reviewer"}],
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda row, event: row.update(session_id="other"), "not correlated"),
        (lambda row, event: event.update(activation_receipt_id="other"), "reciprocally bound"),
        (
            lambda row, event: event.update(executed_worker_id="", native_run_id=""),
            "no native worker identity",
        ),
        (lambda row, event: row.update(worker_id="other"), "worker identity is mismatched"),
        (
            lambda row, event: event.update(retrieved_specialist_prompt_hash="other"),
            "retrieved identity is mismatched",
        ),
    ],
)
def test_header_activation_receipt_validation_errors(mutation: Any, message: str) -> None:
    snapshot = _activation_snapshot()
    row = snapshot["specialist_activations"][0]
    event = snapshot["delegations"][0]
    mutation(row, event)
    with pytest.raises(header_contract.EvidenceCorrelationError, match=message):
        header_contract._validated_activation_identity(
            row,
            events={"event": event},
            session_id="session",
            trace_id="trace",
        )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.update(delivery_mode="future"), "delivery mode"),
        (lambda value: value.update(selected_specialists=[None]), "selected specialist evidence"),
        (lambda value: value.update(specialist_activations=[None]), "activation evidence"),
        (
            lambda value: value["specialist_activations"].append(
                dict(value["specialist_activations"][0])
            ),
            "not one-use",
        ),
        (lambda value: value.update(specialists=[]), "loaded-specialist evidence"),
        (
            lambda value: value.update(
                unit_agent_plan=[{"work_unit_id": "other", "recommended_agent": "reviewer"}]
            ),
            "not assigned",
        ),
        (
            lambda value: value.update(specialist_activations=[], specialists=[]),
            "activation is incomplete",
        ),
    ],
)
def test_header_activation_snapshot_validation_errors(mutate: Any, message: str) -> None:
    snapshot = _activation_snapshot()
    mutate(snapshot)
    with pytest.raises(header_contract.EvidenceCorrelationError, match=message):
        header_contract._validate_specialist_activations(snapshot, "session", "trace")


def test_host_status_explicit_master_state_skips_global_probe() -> None:
    class Store:
        @staticmethod
        def get_host_control(_host: str) -> dict[str, Any]:
            return {"enabled": True, "updated_at": None, "source": "test"}

    records = host_control.inspect_all_host_statuses(
        Store(),
        inspector=lambda: [],
        global_enabled=False,
    )
    assert all(record["effective_enabled"] is False for record in records)


def test_catalog_signature_failure_uses_legacy_policy_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Store:
        @staticmethod
        def get_active_roster_as_catalog() -> list[dict[str, str]]:
            return [{"slug": "enabled"}, {"slug": "disabled"}]

    monkeypatch.setattr(preflight, "signature", lambda _getter: (_ for _ in ()).throw(ValueError()))
    assert preflight._catalog_with_policy(Store(), frozenset({"disabled"})) == [{"slug": "enabled"}]


def test_preflight_recipe_delegation_and_context_error_branches() -> None:
    from agency_runtime.core.unit_assignment import build_unit_agent_plan

    routing = {
        "selected_ids": ["reviewer"],
        "work_units": {
            "confidence": "high",
            "count": 2,
            "delegate": True,
            "source": "test_fixture",
            "units": ["", "review task"],
        },
    }
    unit_plan = build_unit_agent_plan(routing)
    context = preflight_recipe._isolated_delegation_context(
        routing,
        host="codex",
        unit_plan=unit_plan,
    )
    assert "native_task_name=" in context
    mismatched_routing = {
        **routing,
        "work_units": {**routing["work_units"], "units": ["different review task"]},
    }
    with pytest.raises(RuntimeError, match="does not match the current request"):
        preflight_recipe._isolated_delegation_context(
            mismatched_routing,
            host="claude",
            unit_plan=unit_plan,
        )
    with pytest.raises(RuntimeError, match="routing context exceeds"):
        preflight_recipe._combine_context("too long", "", maximum_chars=1)
    with pytest.raises(RuntimeError, match="specialist context exceeds"):
        preflight_recipe._combine_context("", "too long", maximum_chars=1)


def _replay_recipe(delivery_mode: str) -> dict[str, Any]:
    from agency_runtime.core.selector.delegation_detection import detect_work_units

    context_limit = preflight_recipe.MAX_PREFLIGHT_CONTEXT_CHARS
    return {
        "recipe_version": preflight_recipe.PREFLIGHT_REPLAY_RECIPE_VERSION,
        "policy_fingerprint": preflight_recipe._context_policy_fingerprint(
            AgencyConfig(),
            pipeline,
            delivery_mode=delivery_mode,
            context_limit=context_limit,
        ),
        "session_id": "session",
        "trace_id": "trace",
        "routing": {"work_units": preflight_recipe._work_unit_metadata(detect_work_units("hello"))},
        "specialist_refs": [None],
        "selection_refs": [],
        "unit_assignment_agents": [],
        "unit_agent_plan": [],
        "delivery_mode": delivery_mode,
        "context_limit": context_limit,
        "trivial": False,
        "turn_classification": {
            "turn_kind": "new_intent",
            "selection_required": True,
            "reroute_required": True,
            "execution_decision_required": True,
            "continuation_of": "",
            "confidence": 1.0,
            "reason_codes": ["test_fixture"],
            "state_revision": "f" * 64,
            "classifier_version": 1,
        },
        "resident_manager_binding": build_resident_manager_binding(
            session_id="session",
            host="codex",
            delivery_mode="request",
        ).as_dict(),
        "roster_size": 0,
        "roster_generation": 0,
        "host": "codex",
    }


def test_preflight_recipe_skips_non_mapping_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    loaded = SimpleNamespace(context="", references=(), slugs=())
    monkeypatch.setattr(
        specialist_context, "rebuild_versioned_specialist_context", lambda *_a, **_k: loaded
    )
    result = preflight_recipe._result_from_recipe(
        object(),
        _replay_recipe("direct"),
        session_id="session",
        trace_id="trace",
        user_message="hello",
        config=AgencyConfig(),
        pipeline=pipeline,
    )
    assert result.context


def test_preflight_recipe_defensively_rejects_oversized_isolated_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded = SimpleNamespace(context="", references=(), slugs=())
    monkeypatch.setattr(
        specialist_context, "rebuild_versioned_specialist_context", lambda *_a, **_k: loaded
    )
    monkeypatch.setattr(
        specialist_context, "format_isolated_specialist_context", lambda *_a, **_k: ""
    )
    monkeypatch.setattr(
        preflight_recipe,
        "_combine_context",
        lambda *_a, **_k: "x" * (preflight_recipe.MAX_PREFLIGHT_CONTEXT_CHARS + 1),
    )
    with pytest.raises(RuntimeError, match="exceeds the host delivery ceiling"):
        preflight_recipe._result_from_recipe(
            object(),
            _replay_recipe("isolated"),
            session_id="session",
            trace_id="trace",
            user_message="hello",
            config=AgencyConfig(),
            pipeline=pipeline,
        )


def test_pipeline_default_policy_patch_seam(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = {"actions": {}}
    monkeypatch.setattr(pipeline.policy_module, "load_policy", lambda *_args: sentinel)
    assert pipeline.load_policy() is sentinel


def test_policy_default_resolution_and_identity_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    from agency_runtime.core import config as config_module

    monkeypatch.setattr(
        config_module, "load_config", lambda: SimpleNamespace(companion_policy_path="")
    )
    assert policy._resolve_policy_path() == policy._DEFAULT_POLICY_PATH

    monkeypatch.setattr(policy.os, "lstat", lambda _path: (_ for _ in ()).throw(OSError("no")))
    with pytest.raises(policy.PolicyIdentityError, match="identity is unavailable"):
        policy._policy_file_identity(Path("a"))

    monkeypatch.setattr(policy.os, "lstat", lambda _path: _metadata(mode=stat.S_IFREG | 0o600))
    with pytest.raises(policy.PolicyIdentityError, match="parent must be a directory"):
        policy._policy_file_identity(Path("a") / "b")

    monkeypatch.setattr(policy.os, "lstat", lambda _path: _metadata(mode=stat.S_IFDIR | 0o700))
    with pytest.raises(policy.PolicyIdentityError, match="must be a regular"):
        policy._policy_file_identity(Path("a"))


def test_policy_rejects_identity_change_during_load(monkeypatch: pytest.MonkeyPatch) -> None:
    identities = iter([(1, 2, 3, 4, 5, 6), (1, 2, 3, 4, 7, 6)])
    monkeypatch.setattr(policy, "_policy_file_identity", lambda _path: next(identities))
    monkeypatch.setattr(policy, "assert_config_namespace", lambda _path: None)
    monkeypatch.setattr(policy, "_read_bounded_policy", lambda *_a, **_k: {"actions": {}})
    monkeypatch.setattr(policy, "_COMPANION_POLICY", None)
    monkeypatch.setattr(policy, "_POLICY_PATH", None)
    with pytest.raises(policy.PolicyIdentityError, match="changed during load"):
        policy.load_policy(Path("policy.yaml"))


def test_smoke_rejects_six_argument_config_without_flag(
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
) -> None:
    from agency_runtime.core.installer import install_agent_adapter

    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    result = install_agent_adapter("codex", home_dir=home)
    manifest = Path(result["plugin_path"])
    mcp_path = manifest.parents[1] / ".mcp.json"
    payload = json.loads(mcp_path.read_text(encoding="utf-8"))
    payload["mcpServers"]["agency-runtime"]["args"] = [
        "-I",
        payload["mcpServers"]["agency-runtime"]["args"][1],
        "agency_runtime.server.mcp",
        "--stdio",
        "--wrong",
        str(tmp_path / "config.yaml"),
    ]
    mcp_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="config binding"):
        smoke._smoke_marketplace_bundle("codex", manifest)


def test_specialist_signature_and_context_ceiling_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        specialist_context,
        "signature",
        lambda _getter: (_ for _ in ()).throw(TypeError()),
    )
    assert specialist_context._supports_disabled_snapshot(object()) is False
    assert specialist_context._fit_loaded_context([{"slug": "reviewer"}], 0) == ("", [])

    reference = {
        "slug": "reviewer",
        "version": "1",
        "hash": "hash",
        "description": "Reviews code",
        "capabilities": ["review"],
    }
    prompt = {
        "agent_slug": "reviewer",
        "version": "1",
        "prompt_hash": "hash",
        "prompt_body": "Review carefully.",
    }

    class Store:
        @staticmethod
        def get_versioned_specialist_prompt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            return dict(prompt)

    with pytest.raises(RuntimeError, match="exceed the delivery ceiling"):
        specialist_context.rebuild_versioned_specialist_context(
            Store(), [reference], maximum_chars=1
        )


def _routing(trace_id: str) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "query_hash": "a" * 64,
        "context_fingerprint": "b" * 64,
        "status": "abstained",
        "source": "coverage",
        "selected_ids": [],
        "semantic_ids": [],
        "available_companion_ids": [],
        "confidence": 0.0,
        "latency_ms": 0,
        "work_units": {
            "delegate": False,
            "count": 1,
            "confidence": "low",
            "source": "coverage",
        },
    }


def test_store_ready_evidence_rejects_unit_plan_suggestion_mismatch() -> None:
    routing = _routing("trace")
    projected = store_preflight._project_routing_evidence(routing, trace_id="trace")
    assert projected is not None
    recipe = {
        "recipe_version": 5,
        "policy_fingerprint": "c" * 64,
        "session_id": "session",
        "trace_id": "trace",
        "host": "codex",
        "delivery_mode": "isolated",
        "context_limit": 4096,
        "routing": projected["decision"],
        "specialist_refs": [],
        "unit_assignment_agents": [],
        "unit_agent_plan": [],
        "trivial": False,
        "roster_size": 0,
    }
    suggestion = {"work_unit_id": "unit-0000000000", "recommended_agent": "reviewer"}
    with pytest.raises(ValueError, match="unit-agent plan"):
        store_preflight._prepare_ready_evidence(
            session_id="session",
            trace_id="trace",
            host="codex",
            attempt_token="attempt",
            recipe=recipe,
            routing_evidence=routing,
            suggestions=[suggestion],
            specialist_refs=[],
        )


def test_roster_invalid_prompt_slug_returns_none() -> None:
    store = object.__new__(store_roster.RosterStoreMixin)
    assert store.get_specialist_prompt("not a valid slug!") is None


def _handler(path: str) -> Any:
    handler = object.__new__(http.AgencyHTTPHandler)
    handler.path = path
    handler._validate_request_boundary = lambda **_kwargs: True
    handler._json_ok = lambda payload: setattr(handler, "response", (200, payload))
    handler._json_error = lambda status, message: setattr(handler, "response", (status, message))
    return handler


def test_http_disabled_unknown_routes_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime_control, "master_enabled", lambda: False)
    monkeypatch.setattr(
        runtime_control,
        "read_enforcement_runtime_control",
        lambda: (
            {
                "schema_version": 1,
                "enabled": False,
                "generation": 1,
                "updated_at": "2026-07-16T12:00:00Z",
                "source": "test",
            },
            "test",
        ),
    )
    get_handler = _handler("/unknown")
    get_handler.do_GET()
    assert get_handler.response[0] == http.HTTPStatus.NOT_FOUND

    post_handler = _handler("/unknown")
    post_handler._read_json_body = lambda: {}
    post_handler.do_POST()
    assert post_handler.response[0] == http.HTTPStatus.NOT_FOUND


def test_http_store_property_materializes_once_and_accepts_reset() -> None:
    server = object.__new__(http.AgencyHTTPServer)
    server._store = None
    server._store_lock = Lock()
    calls: list[int] = []
    server._store_factory = lambda: calls.append(1) or object()
    assert server.store is server.store
    assert calls == [1]
    server.store = None
    assert server._store is None


@pytest.mark.parametrize("master", [True, False])
def test_http_serve_store_factory_binds_live_config(
    monkeypatch: pytest.MonkeyPatch,
    master: bool,
) -> None:
    created: list[tuple[Any, Any]] = []
    cfg = SimpleNamespace(
        server=SimpleNamespace(host="127.0.0.1", port=0, max_body_size=100),
        config_path="C:/config/agency.yaml",
    )
    monkeypatch.setattr(runtime_control, "master_enabled", lambda: master)
    monkeypatch.setattr(http, "load_config", lambda: cfg)
    monkeypatch.setattr(
        http, "Store", lambda db, *, config_path=None: created.append((db, config_path)) or object()
    )

    class Server:
        auth_token = "token"
        server_address = ("127.0.0.1", 1)

        def __init__(self, *_args: Any, store_factory: Any, **_kwargs: Any) -> None:
            store_factory()

        @staticmethod
        def serve_forever() -> None:
            raise KeyboardInterrupt

        @staticmethod
        def server_close() -> None:
            pass

    monkeypatch.setattr(http, "AgencyHTTPServer", Server)
    http.serve(host="127.0.0.1", port=0, db_path="db")
    assert created == [("db", "C:/config/agency.yaml")]


def test_mcp_disabled_status_fails_enabled_on_control_read_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runtime_control,
        "read_effective_runtime_control",
        lambda: (_ for _ in ()).throw(OSError("denied")),
    )
    result = mcp._runtime_disabled_tool_result("agency.status", {})
    assert result["master"] == {
        "schema_version": 1,
        "enabled": True,
        "generation": 0,
        "updated_at": "1970-01-01T00:00:00Z",
        "source": "fail-enabled",
    }


def test_mcp_prepare_delegation_correlation_and_active_turn_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert "required" in mcp_tools._prepare_delegation({}, object())["error"]
    monkeypatch.setattr(mcp_tools, "active_turn_error", lambda *_args: "terminal")
    result = mcp_tools._prepare_delegation(
        {"session_id": "session", "trace_id": "trace"},
        object(),
    )
    assert result == {"error": "terminal"}


def test_restricted_control_target_fails_closed_on_token_probe_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "control.json"
    monkeypatch.setattr(runtime_control.os, "name", "nt")
    monkeypatch.setattr(runtime_control, "_cache_key", lambda _path: "same")
    monkeypatch.setattr(runtime_control, "runtime_control_path", lambda: target)
    monkeypatch.setattr(
        runtime_control,
        "current_process_token_is_restricted",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("denied")),
    )
    assert runtime_control._restricted_windows_control_target(target) is False


def _configure_restricted_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    target_metadata: list[Any],
    *,
    bad_directory: bool = False,
) -> Path:
    home = tmp_path / "home"
    target = home / ".agency-runtime" / "run" / "control.json"
    directory_metadata = _metadata(mode=stat.S_IFDIR | 0o700)
    target_values = iter(target_metadata)

    def fake_lstat(path: Path) -> Any:
        if Path(path) == target:
            return next(target_values)
        if bad_directory and Path(path) == home:
            return _metadata(mode=stat.S_IFREG | 0o600)
        return directory_metadata

    monkeypatch.setattr(runtime_control, "_restricted_windows_control_target", lambda _path: True)
    monkeypatch.setattr(runtime_control.Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(runtime_control.os, "lstat", fake_lstat)
    monkeypatch.setattr(
        runtime_control,
        "current_process_has_control_forgery_access",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(runtime_control, "_cache_get", lambda *_args: None)
    monkeypatch.setattr(runtime_control, "_validate_directory_snapshot", lambda _snapshot: None)
    return target


def test_restricted_control_reader_rejects_unavailable_and_inspection_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "control.json"
    monkeypatch.setattr(runtime_control, "_restricted_windows_control_target", lambda _path: False)
    with pytest.raises(runtime_control.RuntimeControlSecurityError, match="unavailable"):
        runtime_control._read_restricted_windows_control(target)

    monkeypatch.setattr(runtime_control, "_restricted_windows_control_target", lambda _path: True)
    monkeypatch.setattr(runtime_control.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(
        runtime_control.os, "lstat", lambda _path: (_ for _ in ()).throw(OSError("no"))
    )
    with pytest.raises(runtime_control.RuntimeControlSecurityError, match="identity could not"):
        runtime_control._read_restricted_windows_control(target)


def test_restricted_control_reader_rejects_bad_parent_and_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = _configure_restricted_control(
        monkeypatch,
        tmp_path,
        [_metadata(mode=stat.S_IFREG | 0o600)],
        bad_directory=True,
    )
    with pytest.raises(runtime_control.RuntimeControlSecurityError, match="real directories"):
        runtime_control._read_restricted_windows_control(target)

    monkeypatch.undo()
    target = _configure_restricted_control(
        monkeypatch,
        tmp_path,
        [_metadata(mode=stat.S_IFDIR | 0o700)],
    )
    with pytest.raises(runtime_control.RuntimeControlSecurityError, match="one real regular file"):
        runtime_control._read_restricted_windows_control(target)


def test_restricted_control_reader_cache_and_read_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    regular = _metadata(mode=stat.S_IFREG | 0o600)
    target = _configure_restricted_control(monkeypatch, tmp_path, [regular, regular])
    monkeypatch.setattr(runtime_control, "_cache_get", lambda *_args: {"enabled": True})
    assert runtime_control._read_restricted_windows_control(target) == {"enabled": True}

    monkeypatch.undo()
    target = _configure_restricted_control(monkeypatch, tmp_path, [regular])
    monkeypatch.setattr(
        runtime_control,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            runtime_control.FileSizeLimitError("large")
        ),
    )
    with pytest.raises(runtime_control.RuntimeControlValidationError, match="4 KiB"):
        runtime_control._read_restricted_windows_control(target)

    monkeypatch.undo()
    target = _configure_restricted_control(monkeypatch, tmp_path, [regular])
    monkeypatch.setattr(
        runtime_control,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("denied")),
    )
    with pytest.raises(runtime_control.RuntimeControlSecurityError, match="read safely"):
        runtime_control._read_restricted_windows_control(target)


class _LockHandle:
    def __init__(self, descriptor: int = 17) -> None:
        self.descriptor = descriptor
        self.closed = False
        self.positions: list[int] = []

    def fileno(self) -> int:
        return self.descriptor

    def seek(self, position: int) -> None:
        self.positions.append(position)

    def write(self, _content: bytes) -> None:
        return None

    def flush(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True


def test_initialization_lock_parent_validation_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent = tmp_path / "private"
    with monkeypatch.context() as scoped:
        scoped.setattr(
            initialization_lock,
            "assert_storage_parent_chain",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("inspect")),
        )
        with pytest.raises(
            initialization_lock.StorageInitializationLockSecurityError,
            match="stable directory chain",
        ):
            initialization_lock._validate_parent(parent)
    monkeypatch.setattr(
        initialization_lock, "assert_storage_parent_chain", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        initialization_lock, "storage_parent_is_trusted", lambda *_args, **_kwargs: False
    )
    with pytest.raises(
        initialization_lock.StorageInitializationLockSecurityError, match="owner-private"
    ):
        initialization_lock._validate_parent(parent)


def test_initialization_lock_identity_inspection_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "lock"
    handle = _LockHandle()
    with monkeypatch.context() as scoped:
        scoped.setattr(
            initialization_lock.os,
            "fstat",
            lambda _descriptor: (_ for _ in ()).throw(OSError("inspect")),
        )
        with pytest.raises(
            initialization_lock.StorageInitializationLockSecurityError,
            match="could not be inspected",
        ):
            initialization_lock._capture_open_identity(path, handle)  # type: ignore[arg-type]
    invalid = _metadata(mode=stat.S_IFDIR | 0o700)
    monkeypatch.setattr(initialization_lock.os, "fstat", lambda _descriptor: invalid)
    monkeypatch.setattr(initialization_lock.os, "lstat", lambda _path: invalid)
    with pytest.raises(
        initialization_lock.StorageInitializationLockSecurityError, match="changed during open"
    ):
        initialization_lock._capture_open_identity(path, handle)  # type: ignore[arg-type]


def test_initialization_lock_current_identity_returns_false_on_inspection_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "lock"
    handle = _LockHandle()
    identity = initialization_lock._LockIdentity(path, 3, 7)
    monkeypatch.setattr(
        initialization_lock.os,
        "fstat",
        lambda _descriptor: (_ for _ in ()).throw(OSError("inspect")),
    )
    assert initialization_lock._identity_is_current(identity, handle) is False  # type: ignore[arg-type]


def test_initialization_lock_open_exhausts_disappearing_existing_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = 0

    def disappearing_open(*_args: Any, **_kwargs: Any) -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise FileExistsError("exists")
        raise FileNotFoundError("disappeared")

    monkeypatch.delattr(initialization_lock.os, "O_BINARY", raising=False)
    monkeypatch.setattr(initialization_lock.os, "O_NOFOLLOW", 0x4000, raising=False)
    monkeypatch.setattr(initialization_lock, "_OPEN_RETRIES", 1)
    monkeypatch.setattr(initialization_lock.os, "open", disappearing_open)
    monkeypatch.setattr(initialization_lock, "is_link_or_reparse_point", lambda _path: False)
    with pytest.raises(
        initialization_lock.StorageInitializationLockSecurityError, match="changed repeatedly"
    ):
        initialization_lock._open_lock(tmp_path / "lock")
    assert calls == 2


@pytest.mark.parametrize(
    ("scenario", "message"),
    [
        ("link", "symlink or reparse point"),
        ("open", "could not be opened"),
        ("create", "could not be created"),
    ],
)
def test_initialization_lock_open_failures_are_security_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, scenario: str, message: str
) -> None:
    calls = 0

    def failing_open(*_args: Any, **_kwargs: Any) -> int:
        nonlocal calls
        calls += 1
        if scenario == "create":
            raise OSError("create")
        if calls == 1:
            raise FileExistsError("exists")
        raise OSError("open")

    monkeypatch.setattr(initialization_lock.os, "open", failing_open)
    monkeypatch.setattr(
        initialization_lock, "is_link_or_reparse_point", lambda _path: scenario == "link"
    )
    with pytest.raises(initialization_lock.StorageInitializationLockSecurityError, match=message):
        initialization_lock._open_lock(tmp_path / "lock")


@pytest.mark.parametrize(
    ("identity_states", "message"),
    [([False], "unchanged owner-private file"), ([True, False], "changed during preparation")],
)
def test_initialization_lock_open_revalidates_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, identity_states: list[bool], message: str
) -> None:
    path = tmp_path / "lock"
    handle = _LockHandle()
    identity = initialization_lock._LockIdentity(path, 3, 7)
    states = iter(identity_states)
    monkeypatch.setattr(initialization_lock.os, "open", lambda *_args, **_kwargs: 17)
    monkeypatch.setattr(initialization_lock.os, "fdopen", lambda *_args, **_kwargs: handle)
    monkeypatch.setattr(
        initialization_lock.os, "fstat", lambda _descriptor: SimpleNamespace(st_size=1)
    )
    monkeypatch.setattr(initialization_lock, "_capture_open_identity", lambda *_args: identity)
    monkeypatch.setattr(initialization_lock, "_restrict_lock", lambda _path: None)
    monkeypatch.setattr(initialization_lock, "_identity_is_current", lambda *_args: next(states))
    with pytest.raises(initialization_lock.StorageInitializationLockSecurityError, match=message):
        initialization_lock._open_lock(path)
    assert handle.closed is True


def test_initialization_lock_posix_acquire_and_release_use_flock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[int, int]] = []
    fake_fcntl = SimpleNamespace(
        LOCK_EX=1,
        LOCK_NB=2,
        LOCK_UN=4,
        flock=lambda descriptor, operation: calls.append((descriptor, operation)),
    )
    handle = _LockHandle()
    monkeypatch.setattr(initialization_lock, "_IS_WINDOWS", False)
    monkeypatch.setitem(sys.modules, "fcntl", fake_fcntl)
    initialization_lock._try_acquire(handle)  # type: ignore[arg-type]
    initialization_lock._release(handle)  # type: ignore[arg-type]
    assert calls == [(17, 3), (17, 4)]
    assert handle.positions == [0, 0]


def _patch_initialization_lock_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    identity_states: list[bool],
    release: Any = None,
) -> tuple[_LockHandle, Path]:
    lock_path = tmp_path / "lock"
    handle = _LockHandle()
    identity = initialization_lock._LockIdentity(lock_path, 3, 7)
    states = iter(identity_states)
    monkeypatch.setattr(initialization_lock, "_absolute", lambda path: path)
    monkeypatch.setattr(initialization_lock, "_validate_parent", lambda _parent: None)
    monkeypatch.setattr(initialization_lock, "initialization_lock_path", lambda _target: lock_path)
    monkeypatch.setattr(initialization_lock, "_open_lock", lambda _path: (handle, identity))
    monkeypatch.setattr(initialization_lock, "_acquire_bounded", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(initialization_lock, "_identity_is_current", lambda *_args: next(states))
    monkeypatch.setattr(
        initialization_lock, "_release", (lambda _handle: None) if release is None else release
    )
    return handle, lock_path


def test_initialization_lock_rejects_change_after_acquisition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handle, _lock_path = _patch_initialization_lock_context(
        monkeypatch, tmp_path, identity_states=[False, True]
    )
    with (
        pytest.raises(
            initialization_lock.StorageInitializationLockSecurityError,
            match="changed after acquisition",
        ),
        initialization_lock.storage_initialization_lock(tmp_path / "agency.db"),
    ):
        pytest.fail("a changed lock must not enter the protected body")
    assert handle.closed is True


def test_initialization_lock_preserves_body_error_and_annotates_cleanup_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fail_release(_handle: Any) -> None:
        raise OSError("unlock failed")

    handle, lock_path = _patch_initialization_lock_context(
        monkeypatch, tmp_path, identity_states=[True, False], release=fail_release
    )
    with (
        pytest.raises(ValueError, match="body failed") as exc_info,
        initialization_lock.storage_initialization_lock(tmp_path / "agency.db") as acquired,
    ):
        assert acquired == lock_path
        raise ValueError("body failed")
    notes = getattr(exc_info.value, "__notes__", [])
    assert any("lock cleanup failed" in note for note in notes)
    assert handle.closed is True


def test_initialization_lock_raises_release_failure_after_clean_body(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fail_release(_handle: Any) -> None:
        raise OSError("unlock failed")

    handle, lock_path = _patch_initialization_lock_context(
        monkeypatch, tmp_path, identity_states=[True, True], release=fail_release
    )
    with (
        pytest.raises(OSError, match="unlock failed"),
        initialization_lock.storage_initialization_lock(tmp_path / "agency.db") as acquired,
    ):
        assert acquired == lock_path
    assert handle.closed is True


def test_restricted_control_reader_detects_change_during_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    before = _metadata(mode=stat.S_IFREG | 0o600, inode=1)
    after = _metadata(mode=stat.S_IFREG | 0o600, inode=2)
    target = _configure_restricted_control(monkeypatch, tmp_path, [before, after])
    monkeypatch.setattr(runtime_control, "read_bounded_regular_file", lambda *_a, **_k: b"{}")
    with pytest.raises(runtime_control.RuntimeControlSecurityError, match="changed during read"):
        runtime_control._read_restricted_windows_control(target)


def test_http_store_race_observes_value_materialized_under_lock() -> None:
    server = object.__new__(http.AgencyHTTPServer)
    sentinel = object()
    server._store = None
    server._store_factory = lambda: (_ for _ in ()).throw(AssertionError("must not run"))

    class RacingLock:
        def __enter__(self) -> None:
            server._store = sentinel

        def __exit__(self, *_args: Any) -> None:
            return None

    server._store_lock = RacingLock()
    assert server.store is sentinel


class _QueueConnection:
    def __init__(self, *results: _Result) -> None:
        self.results = list(results)
        self.statements: list[tuple[str, tuple[Any, ...]]] = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def execute(self, statement: str, parameters: tuple[Any, ...] = ()) -> _Result:
        self.statements.append((statement, parameters))
        return self.results.pop(0) if self.results else _Result()

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class _ActivationStore(delegation_activation.DelegationActivationStoreMixin):
    def __init__(self, conn: _QueueConnection) -> None:
        self.conn = conn

    def _connect(self) -> _QueueConnection:
        return self.conn

    @staticmethod
    def get_disabled_agent_slugs() -> frozenset[str]:
        return frozenset()

    @staticmethod
    def _now() -> str:
        return "now"

    @staticmethod
    def _uuid() -> str:
        return "generated-id"


_ACTIVATION_PROMPT = "Review exactly."
_ACTIVATION_HASH = sha256(_ACTIVATION_PROMPT.encode()).hexdigest()


def _ready_run() -> dict[str, Any]:
    return {
        "host": "codex",
        "status": "active",
        "preflight_state": "ready",
        "preflight_result": "recipe",
    }


def _activation_recipe() -> dict[str, Any]:
    return {
        "specialist_refs": [{"slug": "reviewer", "version": "1", "hash": _ACTIVATION_HASH}],
        "unit_agent_plan": [],
    }


def _activation_receipt(**changes: Any) -> dict[str, Any]:
    specialist = delegation_activation.build_native_child_specialist_identity(
        slug="reviewer",
        version="1",
        content_hash=_ACTIVATION_HASH,
    )
    grant = delegation_activation.build_native_child_activation_grant(
        parent_session_id="session",
        parent_trace_id="trace",
        work_unit_id="specialist:reviewer",
        host="codex",
        specialist=specialist,
        mutation_scope=delegation_activation.build_native_child_mutation_scope(mode="read_only"),
        evidence_contract=delegation_activation.build_native_child_evidence_contract(
            contract_id="agency-native-child-v1",
            requirements=("delegation-execution", "specialist-load"),
        ),
        issued_at=100,
        expires_at=200,
    )
    receipt = {
        "id": "receipt",
        "grant_id": grant.grant_id,
        "grant_payload": delegation_activation.serialize_native_child_activation_grant(grant),
        "grant_issued_unix": 100,
        "grant_expires_unix": 200,
        "child_host": "codex",
        "session_id": "session",
        "trace_id": "trace",
        "run_status": "active",
        "run_preflight_state": "ready",
        "run_host": "codex",
        "store_now_unix": 150,
        "work_unit_id": "specialist:reviewer",
        "specialist_slug": "reviewer",
        "specialist_version": "1",
        "specialist_prompt_hash": _ACTIVATION_HASH,
        "worker_kind": "generic-worker",
        "worker_id": "",
        "native_run_id": "",
        "consumed_at": None,
    }
    receipt.update(changes)
    return receipt


def test_stored_public_grant_rejects_incomplete_current_schema_row() -> None:
    receipt = _activation_receipt()
    receipt.pop("consumed_at")

    with pytest.raises(ValueError, match="activation grant record is incomplete"):
        delegation_activation._stored_public_grant(receipt)


def test_activation_identity_and_existing_event_short_circuits() -> None:
    with pytest.raises(ValueError, match="specialist_slug is required"):
        delegation_activation._identity(
            "",
            maximum=64,
            field="specialist_slug",
            required=True,
        )
    with pytest.raises(ValueError, match="content-free identifier"):
        delegation_activation._work_unit_identity("bad unit", required=True)

    conn = _QueueConnection(_Result(row={"activation_receipt_id": "prior"}))
    delegation_activation.attach_consumed_activation_to_delegation(
        conn,
        event_id="event",
        trace_id="trace",
        work_unit_id="unit",
    )
    assert len(conn.statements) == 1


def test_disabled_specialist_terminalization_without_active_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _QueueConnection(_Result(rowcount=0))
    store = _ActivationStore(conn)
    monkeypatch.setattr(delegation_activation, "agent_is_enabled", lambda *_args: False)
    with pytest.raises(ValueError, match="is disabled"):
        store._reject_disabled_specialist(
            conn,
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
        )
    assert conn.committed is True
    assert len(conn.statements) == 1


def test_disabled_specialist_expires_active_loaded_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _QueueConnection(_Result(rowcount=1), _Result())
    store = _ActivationStore(conn)
    monkeypatch.setattr(delegation_activation, "agent_is_enabled", lambda *_args: False)
    with pytest.raises(ValueError, match="is disabled"):
        store._reject_disabled_specialist(
            conn,
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
        )
    assert len(conn.statements) == 2


@pytest.mark.parametrize(
    "row",
    [
        None,
        {
            "status": "active",
            "host": "hermes",
            "preflight_state": "pending",
            "preflight_result": None,
        },
    ],
)
def test_requires_activation_returns_false_without_ready_run(row: Any) -> None:
    conn = _QueueConnection(_Result(row=row))
    store = _ActivationStore(conn)
    assert (
        store.requires_delegation_activation(
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
        )
        is False
    )
    assert conn.closed is True


@pytest.mark.parametrize(
    ("recipe", "expected"), [(None, False), ({"delivery_mode": "isolated"}, True)]
)
def test_requires_activation_uses_ready_non_native_recipe(
    monkeypatch: pytest.MonkeyPatch,
    recipe: Any,
    expected: bool,
) -> None:
    conn = _QueueConnection(
        _Result(
            row={
                "status": "active",
                "host": "hermes",
                "preflight_state": "ready",
                "preflight_result": "recipe",
            }
        )
    )
    monkeypatch.setattr(
        delegation_activation,
        "_decode_preflight_recipe",
        lambda *_args, **_kwargs: recipe,
    )
    assert (
        _ActivationStore(conn).requires_delegation_activation(
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
        )
        is expected
    )


def test_requires_activation_is_mandatory_for_native_isolated_hosts() -> None:
    conn = _QueueConnection(
        _Result(
            row={
                "status": "active",
                "host": "codex",
                "preflight_state": "ready",
                "preflight_result": "recipe",
            }
        )
    )

    assert (
        _ActivationStore(conn).requires_delegation_activation(
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
        )
        is True
    )


def test_prepare_activation_rejects_invalid_kind_and_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(delegation_activation.secrets, "token_urlsafe", lambda _size: "token")
    store = _ActivationStore(_QueueConnection())
    with pytest.raises(ValueError, match="generic-worker attribution"):
        store.prepare_delegation_activation(
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
            work_unit_id="specialist:reviewer",
            worker_kind="native",
        )

    conn = _QueueConnection(_Result(), _Result(row=None))
    store = _ActivationStore(conn)
    with pytest.raises(ValueError, match="ready active"):
        store.prepare_delegation_activation(
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
            work_unit_id="specialist:reviewer",
        )
    assert conn.rolled_back is True


def test_prepare_activation_rejects_recipe_reference_and_prompt_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(delegation_activation.secrets, "token_urlsafe", lambda _size: "token")
    monkeypatch.setattr(delegation_activation, "agent_is_enabled", lambda *_args: True)

    conn = _QueueConnection(_Result(), _Result(row=_ready_run()))
    monkeypatch.setattr(delegation_activation, "_decode_preflight_recipe", lambda *_a, **_k: None)
    with pytest.raises(ValueError, match="could not be verified"):
        _ActivationStore(conn).prepare_delegation_activation(
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
            work_unit_id="specialist:reviewer",
        )

    conn = _QueueConnection(_Result(), _Result(row=_ready_run()))
    monkeypatch.setattr(
        delegation_activation,
        "_decode_preflight_recipe",
        lambda *_a, **_k: {"specialist_refs": [], "unit_agent_plan": []},
    )
    with pytest.raises(ValueError, match="not selected"):
        _ActivationStore(conn).prepare_delegation_activation(
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
            work_unit_id="specialist:reviewer",
        )

    conn = _QueueConnection(_Result(), _Result(row=_ready_run()))
    monkeypatch.setattr(
        delegation_activation,
        "_decode_preflight_recipe",
        lambda *_a, **_k: {
            **_activation_recipe(),
            "unit_agent_plan": [{"work_unit_id": "other-unit", "recommended_agent": "reviewer"}],
        },
    )
    with pytest.raises(ValueError, match="persisted unit-agent plan"):
        _ActivationStore(conn).prepare_delegation_activation(
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
            work_unit_id="specialist:reviewer",
        )

    conn = _QueueConnection(_Result(), _Result(row=_ready_run()), _Result(row=None))
    monkeypatch.setattr(
        delegation_activation,
        "_decode_preflight_recipe",
        lambda *_a, **_k: _activation_recipe(),
    )
    with pytest.raises(ValueError, match="prompt version is unavailable"):
        _ActivationStore(conn).prepare_delegation_activation(
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
            work_unit_id="specialist:reviewer",
        )

    conn = _QueueConnection(
        _Result(),
        _Result(row=_ready_run()),
        _Result(row={"content": "x" * (delegation_activation.MAX_SPECIALIST_PROMPT_CHARS + 1)}),
    )
    with pytest.raises(ValueError, match="exact-delivery ceiling"):
        _ActivationStore(conn).prepare_delegation_activation(
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
            work_unit_id="specialist:reviewer",
        )

    conn = _QueueConnection(
        _Result(),
        _Result(row=_ready_run()),
        _Result(row={"content": "tampered"}),
    )
    with pytest.raises(ValueError, match="integrity verification"):
        _ActivationStore(conn).prepare_delegation_activation(
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
            work_unit_id="specialist:reviewer",
        )


def test_prepare_activation_rejects_existing_grants_and_creates_public_grant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(delegation_activation.secrets, "token_urlsafe", lambda _size: "token")
    monkeypatch.setattr(delegation_activation, "agent_is_enabled", lambda *_args: True)
    monkeypatch.setattr(
        delegation_activation,
        "_decode_preflight_recipe",
        lambda *_a, **_k: _activation_recipe(),
    )
    prompt = {"content": "Review exactly."}

    conn = _QueueConnection(
        _Result(),
        _Result(row=_ready_run()),
        _Result(row=prompt),
        _Result(row={"id": "prior", "consumed_at": "now"}),
    )
    with pytest.raises(ValueError, match="already has a consumed"):
        _ActivationStore(conn).prepare_delegation_activation(
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
            work_unit_id="specialist:reviewer",
        )

    unconsumed = _QueueConnection(
        _Result(),
        _Result(row=_ready_run()),
        _Result(row=prompt),
        _Result(row={"id": "prior", "consumed_at": None, "grant_expires_unix": 200}),
    )
    with pytest.raises(ValueError, match="already has an unconsumed"):
        _ActivationStore(unconsumed).prepare_delegation_activation(
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
            work_unit_id="specialist:reviewer",
        )

    monkeypatch.setattr(
        delegation_activation,
        "_decode_preflight_recipe",
        lambda *_a, **_k: {
            **_activation_recipe(),
            "unit_agent_plan": [
                {
                    "work_unit_id": "specialist:reviewer",
                    "recommended_agent": "reviewer",
                }
            ],
        },
    )
    conn = _QueueConnection(
        _Result(),
        _Result(row=_ready_run()),
        _Result(row=prompt),
        _Result(row=None),
        _Result(row={"unix_time": 100}),
        _Result(),
    )
    result = _ActivationStore(conn).prepare_delegation_activation(
        session_id="session",
        trace_id="trace",
        specialist_slug="reviewer",
        work_unit_id="specialist:reviewer",
    )
    assert result["activation_token"] == "token"
    assert str(result["grant_id"]).startswith("ncg-")
    assert conn.committed is True
    assert not any(
        "DELETE FROM delegation_activation_receipts" in item[0] for item in conn.statements
    )


def test_consume_activation_validation_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="activation_token is invalid"):
        _ActivationStore(_QueueConnection()).consume_delegation_activation(
            activation_token="",
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
            work_unit_id="specialist:reviewer",
        )

    monkeypatch.setattr(delegation_activation, "agent_is_enabled", lambda *_args: True)
    cases = [
        (_activation_receipt(run_status="ended"), "non-ready or terminal"),
        (_activation_receipt(work_unit_id="other"), "different work unit"),
        (_activation_receipt(run_host="openclaw"), "integrity verification"),
    ]
    for receipt, message in cases:
        conn = _QueueConnection(_Result(), _Result(row=receipt))
        with pytest.raises(ValueError, match=message):
            _ActivationStore(conn).consume_delegation_activation(
                activation_token="token",
                session_id="session",
                trace_id="trace",
                specialist_slug="reviewer",
                work_unit_id="specialist:reviewer",
                worker_id="worker",
                native_run_id="run",
            )


@pytest.mark.parametrize(
    ("prompt", "consumed_rowcount", "message"),
    [
        (None, 1, "prompt version is unavailable"),
        (
            {"content": "x" * (delegation_activation.MAX_SPECIALIST_PROMPT_CHARS + 1)},
            1,
            "delivery ceiling",
        ),
        (
            {
                "agent_slug": "reviewer",
                "version": "1",
                "hash": _ACTIVATION_HASH,
                "content": _ACTIVATION_PROMPT,
            },
            0,
            "already consumed",
        ),
        (
            {
                "agent_slug": "reviewer",
                "version": "1",
                "hash": _ACTIVATION_HASH,
                "content": "tampered",
            },
            1,
            "integrity verification",
        ),
    ],
)
def test_consume_activation_prompt_and_atomic_update_failures(
    monkeypatch: pytest.MonkeyPatch,
    prompt: Any,
    consumed_rowcount: int,
    message: str,
) -> None:
    monkeypatch.setattr(delegation_activation, "agent_is_enabled", lambda *_args: True)
    results = [_Result(), _Result(row=_activation_receipt()), _Result(row=prompt)]
    if (
        prompt is not None
        and len(str(prompt["content"])) <= delegation_activation.MAX_SPECIALIST_PROMPT_CHARS
    ):
        results.extend([_Result(), _Result(rowcount=consumed_rowcount)])
    conn = _QueueConnection(*results)
    with pytest.raises(ValueError, match=message):
        _ActivationStore(conn).consume_delegation_activation(
            activation_token="token",
            session_id="session",
            trace_id="trace",
            specialist_slug="reviewer",
            work_unit_id="specialist:reviewer",
            worker_id="worker",
            native_run_id="run",
        )


def test_consume_activation_attaches_matching_delegation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(delegation_activation, "agent_is_enabled", lambda *_args: True)
    attached: list[dict[str, Any]] = []
    monkeypatch.setattr(
        delegation_activation,
        "attach_consumed_activation_to_delegation",
        lambda _conn, **kwargs: attached.append(kwargs),
    )
    prompt = {
        "agent_slug": "reviewer",
        "version": "1",
        "hash": _ACTIVATION_HASH,
        "content": _ACTIVATION_PROMPT,
    }
    consumed = {**_activation_receipt(), "consumed_at": "now"}
    conn = _QueueConnection(
        _Result(),
        _Result(row=_activation_receipt()),
        _Result(row=prompt),
        _Result(),
        _Result(rowcount=1),
        _Result(),
        _Result(row={"id": "event"}),
        _Result(row=consumed),
    )
    result = _ActivationStore(conn).consume_delegation_activation(
        activation_token="token",
        session_id="session",
        trace_id="trace",
        specialist_slug="reviewer",
        work_unit_id="specialist:reviewer",
        worker_id="worker",
        native_run_id="run",
    )
    assert result["prompt_body"] == _ACTIVATION_PROMPT
    assert attached == [
        {"event_id": "event", "trace_id": "trace", "work_unit_id": "specialist:reviewer"}
    ]
    assert conn.committed is True


def test_security_created_storage_identity_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security.os, "lstat", lambda _path: _metadata(mode=stat.S_IFDIR | 0o700))
    with pytest.raises(PermissionError, match="capture a created storage identity"):
        security.capture_created_storage_path(Path("created"), directory=False)
    monkeypatch.setattr(
        security.os, "lstat", lambda _path: _metadata(mode=stat.S_IFREG | 0o600, links=2)
    )
    with pytest.raises(PermissionError, match="not single-link"):
        security.capture_created_storage_path(Path("created"), directory=False)


def test_security_missing_created_identity_and_rollback_parent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    identity = security.CreatedStoragePath(tmp_path / "created", 3, 7, False)
    monkeypatch.setattr(
        security.os, "lstat", lambda _path: (_ for _ in ()).throw(FileNotFoundError())
    )
    assert security._created_storage_path_is_current(identity) is False
    security.cleanup_created_storage_paths([identity], is_windows=False)
    monkeypatch.setattr(security.os, "lstat", lambda _path: _metadata(mode=stat.S_IFREG | 0o600))
    monkeypatch.setattr(security, "storage_creation_boundary_is_trusted", lambda *_a, **_k: False)
    with pytest.raises(PermissionError, match="untrusted parent"):
        security.cleanup_created_storage_paths([identity], is_windows=False)


def test_security_posix_default_acl_error_classification(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_acl(*_args: Any, **_kwargs: Any) -> bytes:
        raise OSError(errno.ENODATA, "missing")

    monkeypatch.setattr(security.os, "getxattr", missing_acl, raising=False)
    assert security.posix_directory_has_default_acl(Path("parent")) is False

    def denied_acl(*_args: Any, **_kwargs: Any) -> bytes:
        raise OSError(errno.EPERM, "denied")

    monkeypatch.setattr(security.os, "getxattr", denied_acl, raising=False)
    assert security.posix_directory_has_default_acl(Path("parent")) is True


def test_security_nearest_existing_parent_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security, "_absolute_path", lambda _path: Path("/"))
    monkeypatch.setattr(
        security.os, "lstat", lambda _path: (_ for _ in ()).throw(FileNotFoundError())
    )
    with pytest.raises(PermissionError, match="no existing parent"):
        security.nearest_existing_storage_parent(Path("missing"))
    monkeypatch.setattr(security, "_absolute_path", lambda path: path)
    monkeypatch.setattr(security.os, "lstat", lambda _path: _metadata(mode=stat.S_IFREG | 0o600))
    with pytest.raises(PermissionError, match="real directories"):
        security.nearest_existing_storage_parent(Path("file"))


def test_security_posix_final_parent_must_match_effective_user(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "root"
    target = root / "target"
    monkeypatch.setattr(security, "_absolute_path", lambda _path: target)
    monkeypatch.setattr(security, "_directory_chain", lambda _path: (root, target))
    monkeypatch.setattr(security.os, "lstat", lambda _path: _metadata(mode=stat.S_IFDIR | 0o700))
    assert security.storage_parent_is_trusted(target, is_windows=False, effective_uid=1000) is False


def test_security_storage_file_inspection_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        security.os, "lstat", lambda _path: (_ for _ in ()).throw(OSError("denied"))
    )
    assert security.storage_file_is_trusted(Path("db"), is_windows=False) is False
    monkeypatch.setattr(security.os, "lstat", lambda _path: _metadata(mode=stat.S_IFDIR | 0o700))
    assert security.storage_file_is_trusted(Path("db"), is_windows=False) is False


def test_security_parent_repair_must_remain_trusted(monkeypatch: pytest.MonkeyPatch) -> None:
    trust = iter([True, False])
    monkeypatch.setattr(security, "assert_storage_parent_chain", lambda *_a, **_k: None)
    monkeypatch.setattr(security, "storage_parent_is_trusted", lambda *_a, **_k: next(trust))
    monkeypatch.setattr(security, "restrict_path_permissions", lambda *_a, **_k: None)
    with pytest.raises(PermissionError, match="unsafe after"):
        security._secure_storage_parent_component(Path("parent"), is_windows=False)


def test_security_discard_created_receipts() -> None:
    identity = security.CreatedStoragePath(Path("created"), 1, 2, True)
    created = [identity]
    security._discard_created_receipts(created, [identity])
    assert created == []


def _configure_parent_creation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security, "_absolute_path", lambda path: Path(path))
    monkeypatch.setattr(security, "storage_creation_boundary_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(security, "_secure_storage_parent_component", lambda *_a, **_k: None)


def test_security_private_parent_creation_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    boundary = tmp_path / "boundary"
    intended = boundary / "child"
    _configure_parent_creation(monkeypatch)
    monkeypatch.setattr(security, "storage_creation_boundary_is_trusted", lambda *_a, **_k: False)
    with pytest.raises(PermissionError, match="cross-account"):
        security.create_private_storage_parent(boundary, intended, is_windows=False)
    monkeypatch.setattr(security, "storage_creation_boundary_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(
        security.os, "mkdir", lambda *_a, **_k: (_ for _ in ()).throw(FileExistsError())
    )
    assert security.create_private_storage_parent(boundary, intended, is_windows=False) is False
    monkeypatch.setattr(
        security.os, "mkdir", lambda *_a, **_k: (_ for _ in ()).throw(OSError("denied"))
    )
    with pytest.raises(PermissionError, match="could not create"):
        security.create_private_storage_parent(boundary, intended, is_windows=False)


def test_security_private_parent_creation_receipt_and_rollback_note(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    boundary = tmp_path / "boundary"
    intended = boundary / "child"
    identity = security.CreatedStoragePath(intended, 1, 2, True)
    _configure_parent_creation(monkeypatch)
    monkeypatch.setattr(security.os, "mkdir", lambda *_a, **_k: None)
    monkeypatch.setattr(security, "capture_created_storage_path", lambda *_a, **_k: identity)
    created: list[security.CreatedStoragePath] = []
    assert (
        security.create_private_storage_parent(
            boundary, intended, is_windows=False, created_paths=created
        )
        is True
    )
    assert created == [identity]
    created = []
    monkeypatch.setattr(
        security,
        "_secure_storage_parent_component",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("repair failed")),
    )
    monkeypatch.setattr(
        security,
        "cleanup_created_storage_paths",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("cleanup failed")),
    )
    with pytest.raises(ValueError, match="repair failed") as captured:
        security.create_private_storage_parent(
            boundary, intended, is_windows=False, created_paths=created
        )
    assert created == []
    assert any("rollback failed" in note for note in captured.value.__notes__)


_V20_COLUMNS = {
    "delegation_activation_receipts": {
        "id",
        "token_hash",
        "session_id",
        "trace_id",
        "work_unit_id",
        "specialist_slug",
        "specialist_version",
        "specialist_prompt_hash",
        "worker_kind",
        "worker_id",
        "native_run_id",
        "created_at",
        "consumed_at",
        "delegation_event_id",
    },
    "delegation_events": {
        "executed_worker_kind",
        "executed_worker_id",
        "native_run_id",
        "retrieved_specialist_slug",
        "retrieved_specialist_version",
        "retrieved_specialist_prompt_hash",
        "activation_receipt_id",
    },
    "specialists_loaded": {"activation_receipt_id"},
    "finalization_events": {"policy_response_hash"},
    "host_controls": {"generation"},
}
_V20_INDEXES = {
    "idx_activation_receipts_trace": ("trace_id", "created_at"),
    "idx_activation_receipts_work_unit": ("trace_id", "work_unit_id", "consumed_at"),
    "idx_finalization_trace_policy_response": ("trace_id", "action", "policy_response_hash"),
}


class _V20SchemaConnection:
    def __init__(self, stage: str) -> None:
        self.stage = stage

    def execute(self, statement: str, parameters: tuple[Any, ...] = ()) -> _Result:
        normalized = " ".join(statement.split())
        if "type = 'table'" in normalized:
            table = str(parameters[0])
            if self.stage == "missing-table" and table == "delegation_activation_receipts":
                return _Result(row=None)
            return _Result(row={"present": 1})
        if normalized.startswith("PRAGMA table_info("):
            table = normalized.removeprefix("PRAGMA table_info(").removesuffix(")")
            return _Result(rows=[{"name": name} for name in _V20_COLUMNS[table]])
        if "type = 'index'" in normalized:
            return _Result(row={"present": 1})
        if normalized.startswith("PRAGMA index_info("):
            name = normalized.removeprefix("PRAGMA index_info(").removesuffix(")")
            if self.stage == "wrong-index" and name == "idx_activation_receipts_trace":
                return _Result(rows=[{"name": "wrong"}])
            columns = {
                **_V20_INDEXES,
                "unique_token": ("token_hash",),
                "unique_binding": (
                    "trace_id",
                    "work_unit_id",
                    "specialist_slug",
                    "specialist_version",
                    "specialist_prompt_hash",
                ),
            }[name]
            return _Result(rows=[{"name": column} for column in columns])
        if normalized.startswith("PRAGMA index_list("):
            rows = (
                []
                if self.stage == "missing-unique"
                else [
                    {"name": "unique_token", "unique": 1},
                    {"name": "unique_binding", "unique": 1},
                ]
            )
            return _Result(rows=rows)
        if normalized.startswith("PRAGMA foreign_key_list("):
            rows = (
                []
                if self.stage == "missing-foreign-key"
                else [
                    {"from": "trace_id", "table": "runs", "to": "trace_id"},
                    {"from": "delegation_event_id", "table": "delegation_events", "to": "id"},
                ]
            )
            return _Result(rows=rows)
        if "type = 'trigger'" in normalized:
            sql = "update runs set last_activity_at = value where trace_id = new.trace_id"
            return _Result(
                rows=[
                    {"name": "agency_delegation_activation_receipts_insert_activity", "sql": sql},
                    {"name": "agency_delegation_activation_receipts_update_activity", "sql": sql},
                ]
            )
        raise AssertionError(f"unexpected SQL: {statement}")


@pytest.mark.parametrize(
    "stage",
    ["missing-table", "wrong-index", "missing-unique", "missing-foreign-key"],
)
def test_v20_schema_rejects_missing_security_boundaries(stage: str) -> None:
    assert store_sqlite._v20_receipt_schema_is_current(_V20SchemaConnection(stage)) is False


def _bare_sqlite_store(db_path: Any) -> store_sqlite.Store:
    store = object.__new__(store_sqlite.Store)
    store.db_path = db_path
    store._permission_fingerprints = {}
    return store


def test_sqlite_requires_trusted_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(store_sqlite, "_storage_file_is_trusted", lambda _path: False)
    with pytest.raises(PermissionError, match="unsafe"):
        store_sqlite._require_storage_target_trusted(
            Path("db"),
            directory=False,
            message="unsafe",
        )


def test_sqlite_parent_must_remain_trusted_after_preparation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "runtime" / "agency.db"
    store = _bare_sqlite_store(db_path)
    trust = iter([True, False])
    monkeypatch.setattr(store_sqlite, "_assert_storage_parent_chain", lambda *_a, **_k: None)
    monkeypatch.setattr(store_sqlite, "_nearest_existing_storage_parent", lambda _path: tmp_path)
    monkeypatch.setattr(store_sqlite, "_storage_creation_boundary_is_trusted", lambda *_a: True)
    monkeypatch.setattr(store_sqlite, "_create_private_storage_parent", lambda *_a: False)
    monkeypatch.setattr(store_sqlite, "_default_runtime_directory", lambda: tmp_path / "other")
    monkeypatch.setattr(store_sqlite, "_storage_parent_is_trusted", lambda _path: next(trust))
    with pytest.raises(PermissionError, match="cross-account"):
        store._prepare_storage_parent()


def test_sqlite_rollback_records_sidecar_and_cleanup_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db = tmp_path / "agency.db"
    wal = tmp_path / "agency.db-wal"
    shm = tmp_path / "agency.db-shm"
    database_identity = security.CreatedStoragePath(db, 1, 2, False)
    sidecar_identity = security.CreatedStoragePath(shm, 1, 3, False)
    store = _bare_sqlite_store(db)
    monkeypatch.setattr(store_sqlite, "_sqlite_storage_paths", lambda _path: (db, wal, shm))

    def capture(path: Path, *, directory: bool) -> security.CreatedStoragePath:
        assert directory is False
        if path == wal:
            raise OSError("raced")
        return sidecar_identity

    monkeypatch.setattr(store_sqlite, "capture_created_storage_path", capture)
    monkeypatch.setattr(store_sqlite, "_storage_file_is_trusted", lambda _path: False)
    monkeypatch.setattr(
        store_sqlite,
        "cleanup_created_storage_paths",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("cleanup")),
    )
    error = RuntimeError("constructor")
    store._rollback_new_storage([database_identity], error=error)
    notes = getattr(error, "__notes__", [])
    assert any("identify a new sidecar" in note for note in notes)
    assert any("untrusted new sidecar" in note for note in notes)
    assert any("rollback failed" in note for note in notes)


def test_sqlite_exclusive_creation_rejects_identity_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MissingTarget:
        @staticmethod
        def lstat() -> Any:
            raise FileNotFoundError

    target = MissingTarget()
    store = _bare_sqlite_store(target)
    store._assert_storage_paths_safe = lambda: None
    monkeypatch.setattr(store_sqlite, "_sqlite_storage_paths", lambda _path: (target,))
    monkeypatch.setattr(store_sqlite.os, "open", lambda *_a, **_k: 11)
    monkeypatch.setattr(
        store_sqlite.os,
        "fstat",
        lambda _fd: _metadata(mode=stat.S_IFREG | 0o600, inode=1),
    )
    monkeypatch.setattr(
        store_sqlite,
        "capture_created_storage_path",
        lambda *_a, **_k: security.CreatedStoragePath(Path("db"), 3, 1, False),
    )
    monkeypatch.setattr(
        store_sqlite.os,
        "lstat",
        lambda _path: _metadata(mode=stat.S_IFREG | 0o600, inode=2),
    )
    monkeypatch.setattr(store_sqlite.os.path, "samestat", lambda *_a: False)
    monkeypatch.setattr(store_sqlite.os, "close", lambda _fd: None)
    with pytest.raises(PermissionError, match="changed during exclusive creation"):
        store._ensure_private_storage_file()


def test_sqlite_storage_file_trust_before_and_after_repair(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db = tmp_path / "agency.db"
    db.write_bytes(b"")
    monkeypatch.setattr(store_sqlite, "_sqlite_storage_paths", lambda _path: (db,))
    monkeypatch.setattr(store_sqlite, "_is_link_or_reparse_point", lambda _path: False)

    store = _bare_sqlite_store(db)
    store._assert_storage_paths_safe = lambda: None
    monkeypatch.setattr(store_sqlite, "_storage_file_is_trusted", lambda _path: False)
    with pytest.raises(PermissionError, match="not a trusted"):
        store._ensure_private_storage_file()

    trust = iter([True, True, False])
    monkeypatch.setattr(store_sqlite, "_storage_file_is_trusted", lambda _path: next(trust))
    monkeypatch.setattr(store_sqlite, "_restrict_path_permissions", lambda *_a, **_k: None)
    with pytest.raises(PermissionError, match="unsafe after"):
        store._ensure_private_storage_file()


def test_sqlite_repeated_trust_identity_churn_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _bare_sqlite_store(Path("sidecar"))
    metadata = iter(_metadata(mode=stat.S_IFREG | 0o600, inode=inode) for inode in range(1, 5))
    store._storage_metadata = lambda *_a, **_k: next(metadata)
    monkeypatch.setattr(store_sqlite, "_storage_file_is_trusted", lambda _path: True)
    monkeypatch.setattr(store_sqlite.os.path, "samestat", lambda *_a: False)
    with pytest.raises(PermissionError, match="changed repeatedly"):
        store._require_stable_trusted_storage_file(Path("sidecar"), optional_sidecar=True)


@pytest.mark.parametrize("changed", [False, True])
def test_sqlite_post_repair_sidecar_pretrust_race(
    monkeypatch: pytest.MonkeyPatch,
    changed: bool,
) -> None:
    path = Path("agency.db-wal")
    metadata = _metadata(mode=stat.S_IFREG | 0o600)
    store = _bare_sqlite_store(path)
    store._storage_metadata = lambda *_a, **_k: metadata
    store._optional_sidecar_identity_changed = lambda *_a, **_k: changed
    outcomes: list[BaseException | None] = [PermissionError("race")]
    if not changed:
        outcomes.append(None)

    def require(*_args: Any, **_kwargs: Any) -> None:
        outcome = outcomes.pop(0)
        if outcome is not None:
            raise outcome

    monkeypatch.setattr(store_sqlite, "_require_storage_target_trusted", require)
    result = store._validate_repaired_storage_target(
        path,
        directory=False,
        optional_sidecar=True,
        fingerprint=(3, 7),
    )
    assert result == ((True, None) if changed else (False, (3, 7)))


@pytest.mark.parametrize("changed", [False, True])
def test_sqlite_pre_repair_sidecar_pretrust_race(
    monkeypatch: pytest.MonkeyPatch,
    changed: bool,
) -> None:
    path = Path("agency.db-wal")
    metadata = _metadata(mode=stat.S_IFREG | 0o600)
    store = _bare_sqlite_store(path)
    store._storage_metadata = lambda *_a, **_k: metadata
    store._optional_sidecar_identity_changed = lambda *_a, **_k: changed
    outcomes: list[BaseException | None] = [PermissionError("race")]
    if not changed:
        outcomes.append(None)

    def require(*_args: Any, **_kwargs: Any) -> None:
        outcome = outcomes.pop(0)
        if outcome is not None:
            raise outcome

    monkeypatch.setattr(store_sqlite, "_require_storage_target_trusted", require)
    monkeypatch.setattr(store_sqlite, "_IS_WINDOWS", True)
    monkeypatch.setattr(store_sqlite, "_restrict_path_permissions", lambda *_a, **_k: None)
    store._validate_repaired_storage_target = lambda *_a, **_k: (False, (3, 7))
    assert (
        store._repair_storage_target_once(
            path,
            directory=False,
            optional_sidecar=True,
        )
        is changed
    )


def test_sqlite_stable_repair_requires_fingerprint(monkeypatch: pytest.MonkeyPatch) -> None:
    path = Path("agency.db")
    store = _bare_sqlite_store(path)
    store._storage_metadata = lambda *_a, **_k: _metadata(mode=stat.S_IFREG | 0o600)
    monkeypatch.setattr(store_sqlite, "_require_storage_target_trusted", lambda *_a, **_k: None)
    monkeypatch.setattr(store_sqlite, "_IS_WINDOWS", True)
    monkeypatch.setattr(store_sqlite, "_restrict_path_permissions", lambda *_a, **_k: None)
    store._validate_repaired_storage_target = lambda *_a, **_k: (False, None)
    with pytest.raises(RuntimeError, match="omitted its identity fingerprint"):
        store._repair_storage_target_once(path, directory=False, optional_sidecar=False)


def test_sqlite_absent_schema_and_database_identity_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = _bare_sqlite_store(tmp_path / "missing.db")
    store._assert_storage_paths_safe = lambda: None
    store._assert_storage_files_trusted = lambda: None
    assert store._current_schema_state() == (False, False)

    class Target:
        def __init__(self, metadata: Any) -> None:
            self.metadata = metadata

        def lstat(self) -> Any:
            return self.metadata

    store.db_path = Target(_metadata(mode=stat.S_IFREG | 0o600, links=2))
    with pytest.raises(PermissionError, match="exactly one hard link"):
        store._database_identity()

    store.db_path = Target(_metadata(mode=stat.S_IFREG | 0o600))
    monkeypatch.setattr(store_sqlite, "_storage_file_is_trusted", lambda _path: False)
    with pytest.raises(PermissionError, match="not a trusted current-user"):
        store._database_identity()


def test_restricted_control_cache_identity_mismatch_falls_through(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    before = _metadata(mode=stat.S_IFREG | 0o600, inode=1)
    changed = _metadata(mode=stat.S_IFREG | 0o600, inode=2)
    target = _configure_restricted_control(monkeypatch, tmp_path, [before, changed])
    monkeypatch.setattr(runtime_control, "_cache_get", lambda *_args: {"enabled": True})
    monkeypatch.setattr(
        runtime_control,
        "read_bounded_regular_file",
        lambda *_a, **_k: (_ for _ in ()).throw(OSError("stop after cache miss")),
    )
    with pytest.raises(runtime_control.RuntimeControlSecurityError, match="read safely"):
        runtime_control._read_restricted_windows_control(target)
