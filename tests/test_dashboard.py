"""Security and API tests for the installed local operations dashboard."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
from http.client import HTTPConnection, HTTPResponse
from pathlib import Path
from uuid import uuid4

import pytest
import yaml

from agency_runtime.core.dashboard_runtime import (
    dashboard_api_request,
    remove_dashboard_runtime,
    write_dashboard_runtime,
)
from agency_runtime.core.observability import correlation_observation_digest
from agency_runtime.core.roster.bundled import bundled_roster
from agency_runtime.core.roster.ingress import MAX_LIST_ITEMS
from agency_runtime.core.roster.sync import quarantine_candidate
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.store.workforce import (
    MAX_HIRING_COLLECTION_RESPONSE_BYTES,
    MAX_HIRING_SUMMARY_PAGE,
    WorkforcePayloadBudgetError,
)
from agency_runtime.core.workforce.known_installer import install_known_contractors
from agency_runtime.core.workforce.promotion import promotion_readiness
from agency_runtime.server import dashboard as dashboard_module
from agency_runtime.server.dashboard import (
    MAX_WORKFORCE_DETAIL_RESPONSE_BYTES,
    DashboardHTTPHandler,
    DashboardHTTPServer,
    _HostInspectionCoordinator,
    _provider_health,
)

_OWNER_MUTATION_PATHS = DashboardHTTPHandler._OWNER_MUTATION_PATHS


def _verified_codex_record() -> dict[str, object]:
    return {
        "host": "codex",
        "executable_discovered": True,
        "registered": True,
        "enabled": True,
        "managed_plugin_version": "test",
        "launcher_artifacts_current": True,
    }


@pytest.fixture()
def dashboard_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "missing.yaml"))
    monkeypatch.setenv("AGENCY_JUDGE_TIMEOUT", "0.05")
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "dashboard.db"))
    for name in (
        "AGENCY_JUDGE_MODEL",
        "AGENCY_JUDGE_BASE_URL",
        "AGENCY_JUDGE_API_KEY",
        "LITELLM_API_KEY",
        "OLLAMA_BASE_URL",
        "AGENCY_OLLAMA_FALLBACK_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    from agency_runtime.core.config import reset_config_cache

    reset_config_cache()
    store = Store()
    store._activate_prevalidated_agent(
        {
            "slug": "security-reviewer",
            "name": "Security Reviewer",
            "division": "engineering",
            "description": "Reviews application security and threat boundaries.",
            "source": "test",
            "version": "1.0",
            "hash": hashlib.sha256(
                b"Review application security and threat boundaries."
            ).hexdigest(),
            "categories": ["security"],
            "capabilities": [
                "application-attack-surfaces",
                "security-review",
                "threat-modeling",
            ],
            "tool_affinity": ["git"],
            "authority": "review",
            "context_mode": "isolated_only",
            "supported_hosts": ["codex", "claude", "openclaw", "hermes"],
            "supported_platforms": ["windows", "linux"],
            "audit_status": "approved",
            "audit_revision": "dashboard-test-v1",
            "routing_contract_valid": True,
            "outcomes": ["Review application attack surfaces, security, and threat boundaries"],
            "artifact_kinds": ["review-report"],
            "lifecycle_phases": ["review"],
            "domains": ["security"],
            "required_tools": ["repository-read"],
            "prompt_path": "",
            "prompt_body": "Review application security and threat boundaries.",
        }
    )
    store.record_delegation(
        trace_id="trace-dashboard",
        session_id="session-dashboard",
        host="test",
        work_unit_id="unit-1",
        recommended_agent="security-reviewer",
        status="completed",
        backend="test",
        executed_worker_kind="test-worker",
        executed_worker_id="dashboard-worker",
        native_run_id="dashboard-native-run",
    )
    token = "test-dashboard-token-32-characters"
    broker_token = "test-dashboard-broker-token-32-characters"
    server = DashboardHTTPServer(
        store,
        auth_token=token,
        broker_token=broker_token,
        port=0,
        host_inspector=lambda: [_verified_codex_record()],
        runtime_control_home=tmp_path,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.01},
        daemon=True,
    )
    thread.start()
    port = int(server.server_address[1])
    try:
        yield {
            "base": f"http://127.0.0.1:{port}",
            "port": port,
            "token": token,
            "broker_token": broker_token,
            "store": store,
            "home": tmp_path,
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        reset_config_cache()


def _request(
    server: dict,
    path: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    token: str | None = None,
    origin: str | None = None,
    content_type: str = "application/json",
    request_id: str | None = None,
) -> tuple[int, bytes, dict[str, str]]:
    headers: dict[str, str] = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if origin is not None:
        headers["Origin"] = origin
    if request_id is not None:
        headers["X-Agency-Request-ID"] = request_id
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = content_type
    request = urllib.request.Request(
        f"{server['base']}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, exc.read(), dict(exc.headers)


def _json_response(*args, **kwargs) -> tuple[int, dict, dict[str, str]]:
    status, raw, headers = _request(*args, **kwargs)
    return status, json.loads(raw), headers


def _wait_for_dashboard_observation(
    caplog: pytest.LogCaptureFixture,
    request_id: str,
    *,
    timeout: float = 5.0,
) -> dict[str, object]:
    """Wait for a threaded dashboard request boundary to finish emitting."""

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for record in caplog.records:
            message = record.getMessage()
            if not message.startswith("agency_observation "):
                continue
            observation = json.loads(message.split(" ", 1)[1])
            if (
                observation.get("surface") == "dashboard"
                and observation.get("request_id") == request_id
            ):
                return observation
        time.sleep(0.01)
    pytest.fail(f"dashboard observation was not emitted for request {request_id}")


def _raw_request(server: dict, payload: bytes) -> bytes:
    client = socket.create_connection(("127.0.0.1", server["port"]), timeout=2)
    client.settimeout(2)
    try:
        client.sendall(payload)
        response = bytearray()
        while chunk := client.recv(4096):
            response.extend(chunk)
        return bytes(response)
    finally:
        client.close()


def _nested_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for nested in value.values() for key in _nested_keys(nested)}
    if isinstance(value, list):
        return {key for nested in value for key in _nested_keys(nested)}
    return set()


def _insert_workforce_rows(
    store: Store,
    rows: list[tuple[str, str]],
) -> None:
    """Materialize deterministic workforce-page fixtures in one transaction."""

    observed_at = "2026-07-26T00:00:00+00:00"
    values = [
        (
            f"worker-id-{slug}",
            slug,
            slug.replace("-", " ").title(),
            employment,
            f"version-id-{slug}",
            hashlib.sha256(slug.encode("utf-8")).hexdigest(),
            observed_at,
            observed_at,
        )
        for slug, employment in rows
    ]
    conn = store._connect()
    try:
        conn.executemany(
            "INSERT INTO agent_workers "
            "(worker_id, agent_slug, display_name, origin, employment_class, standing, "
            "current_agent_version_id, current_version, current_hash, revision, "
            "created_at, updated_at) VALUES "
            "(?, ?, ?, 'upstream', ?, 'active', ?, '1.0.0', ?, 0, ?, ?)",
            values,
        )
        conn.commit()
    finally:
        conn.close()


_OWNER_DASHBOARD_MUTATIONS = {
    "/api/agents/toggle": {"slug": "security-reviewer", "enabled": False},
    "/api/config": {"expected_revision": "missing", "operations": []},
    "/api/hiring/approve": {"case_id": "case-1", "approved_by": "operator"},
    "/api/hosts/toggle": {"host": "codex", "enabled": False},
    "/api/maintenance/trim": {"older_than_days": 30},
    "/api/roster/action": {"action": "approve", "snapshot_id": "snapshot-1"},
    "/api/runtime/toggle": {"enabled": False},
    "/api/workforce/action": {"action": "suspend", "worker": "security-reviewer"},
}


def _dashboard_authority_bytes(server: dict) -> dict[str, bytes]:
    store = server["store"]
    paths = [
        Path(store.db_path),
        Path(f"{store.db_path}-wal"),
        Path(f"{store.db_path}-shm"),
        Path(store.config_path),
        Path(server["home"]) / ".agency-runtime" / "control.json",
    ]
    return {str(path): path.read_bytes() for path in paths if path.is_file()}


@pytest.mark.parametrize("path,body", _OWNER_DASHBOARD_MUTATIONS.items())
def test_every_dashboard_mutation_is_denied_for_broker_without_state_change(
    dashboard_server: dict,
    path: str,
    body: dict,
) -> None:
    mutation_paths = frozenset(_OWNER_DASHBOARD_MUTATIONS)
    assert mutation_paths == _OWNER_MUTATION_PATHS
    before = _dashboard_authority_bytes(dashboard_server)

    status, payload, _headers = _json_response(
        dashboard_server,
        path,
        method="POST",
        body=body,
        token=dashboard_server["broker_token"],
    )

    assert status == 403
    assert payload == {"error": "owner control required"}
    assert _dashboard_authority_bytes(dashboard_server) == before
    assert mutation_paths == DashboardHTTPHandler._OWNER_MUTATION_PATHS


@pytest.mark.parametrize("mutation", ["trim", "roster-approve", "host-toggle"])
def test_store_mutations_hold_config_identity_lock_against_store_path_changes(
    dashboard_server: dict,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    """A config writer cannot retarget the Store after a binding preflight."""

    from contextlib import contextmanager

    from agency_runtime.core import configuration
    from agency_runtime.core.config import reset_config_cache
    from agency_runtime.core.configuration import apply_config_operations, read_config_state

    config_path = Path(dashboard_server["store"].config_path)
    store_path = Path(dashboard_server["store"].db_path)
    initial = read_config_state(config_path)
    apply_config_operations(
        [{"op": "set", "path": "store.db_path", "value": str(store_path)}],
        expected_revision=initial.revision,
        path=config_path,
    )
    monkeypatch.delenv("AGENCY_DB_PATH")
    reset_config_cache()
    before = read_config_state(config_path)
    assert Path(before.effective["store"]["db_path"]) == store_path

    mutation_entered = threading.Event()
    release_mutation = threading.Event()
    writer_lock_attempted = threading.Event()
    writer_done = threading.Event()
    original_lock = configuration._config_lock

    @contextmanager
    def observed_lock(*args, **kwargs):
        if threading.current_thread().name == "config-writer":
            writer_lock_attempted.set()
        with original_lock(*args, **kwargs):
            yield

    monkeypatch.setattr(configuration, "_config_lock", observed_lock)

    def pause_mutation() -> None:
        mutation_entered.set()
        if not release_mutation.wait(timeout=3):
            raise TimeoutError("test did not release the Store mutation")

    if mutation == "trim":
        original_trim = Store.trim_runtime_tables

        def paused_trim(store, *args, **kwargs):
            pause_mutation()
            return original_trim(store, *args, **kwargs)

        monkeypatch.setattr(Store, "trim_runtime_tables", paused_trim)
        endpoint = "/api/maintenance/trim"
        body = {
            "confirm": "TRIM RUNTIME DATA",
            "older_than_days": 30,
            "dry_run": False,
            "vacuum": False,
        }
    elif mutation == "roster-approve":

        def paused_approve(_store, _snapshot_id, **_kwargs):
            pause_mutation()

        monkeypatch.setattr(dashboard_module, "approve_snapshot", paused_approve)
        endpoint = "/api/roster/action"
        body = {
            "action": "approve",
            "snapshot_id": "race-snapshot",
            "confirm": "APPROVE race-snapshot",
        }
    else:
        from agency_runtime.core import host_control

        original_set_runtime_control = host_control.set_runtime_control

        def paused_set_runtime_control(*args, **kwargs):
            pause_mutation()
            return original_set_runtime_control(*args, **kwargs)

        monkeypatch.setattr(host_control, "set_runtime_control", paused_set_runtime_control)
        endpoint = "/api/hosts/toggle"
        body = {
            "host": "codex",
            "enabled": False,
            "expected_generation": 0,
            "confirm": "DISABLE codex",
        }

    request_result: list[tuple[int, dict, dict[str, str]]] = []
    request_errors: list[BaseException] = []

    def request_mutation() -> None:
        try:
            request_result.append(
                _json_response(
                    dashboard_server,
                    endpoint,
                    method="POST",
                    body=body,
                    token=dashboard_server["token"],
                )
            )
        except BaseException as exc:  # preserve the worker failure for the test thread
            request_errors.append(exc)

    writer_result: list[object] = []
    writer_errors: list[BaseException] = []

    def change_store_path() -> None:
        try:
            writer_result.append(
                apply_config_operations(
                    [
                        {
                            "op": "set",
                            "path": "store.db_path",
                            "value": str(dashboard_server["home"] / "replacement.db"),
                        }
                    ],
                    expected_revision=before.revision,
                    path=config_path,
                )
            )
        except BaseException as exc:  # preserve the worker failure for the test thread
            writer_errors.append(exc)
        finally:
            writer_done.set()

    request_thread = threading.Thread(target=request_mutation, name="store-mutation")
    writer_thread = threading.Thread(target=change_store_path, name="config-writer")
    request_thread.start()
    try:
        assert mutation_entered.wait(timeout=3)
        writer_thread.start()
        assert writer_lock_attempted.wait(timeout=3)
        assert not writer_done.wait(timeout=0.1)
    finally:
        release_mutation.set()
    request_thread.join(timeout=5)
    writer_thread.join(timeout=5)

    assert not request_thread.is_alive()
    assert not writer_thread.is_alive()
    assert request_errors == []
    assert writer_errors == []
    assert len(writer_result) == 1
    assert len(request_result) == 1
    status, payload, _headers = request_result[0]
    assert status == 200
    assert payload["config_revision"] == before.revision
    after = read_config_state(config_path)
    assert after.revision != before.revision
    assert Path(after.effective["store"]["db_path"]) == dashboard_server["home"] / "replacement.db"


def test_agent_toggle_checks_roster_while_holding_config_writer_lock(
    dashboard_server: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Store retarget cannot pass between roster membership and toggle CAS."""

    from contextlib import contextmanager

    from agency_runtime.core import configuration
    from agency_runtime.core.config import reset_config_cache
    from agency_runtime.core.configuration import (
        ConfigConflictError,
        apply_config_operations,
        read_config_state,
    )

    config_path = Path(dashboard_server["store"].config_path)
    store_path = Path(dashboard_server["store"].db_path)
    initial = read_config_state(config_path)
    apply_config_operations(
        [{"op": "set", "path": "store.db_path", "value": str(store_path)}],
        expected_revision=initial.revision,
        path=config_path,
    )
    monkeypatch.delenv("AGENCY_DB_PATH")
    reset_config_cache()
    before = read_config_state(config_path)

    membership_entered = threading.Event()
    release_membership = threading.Event()
    writer_lock_attempted = threading.Event()
    writer_done = threading.Event()
    original_lock = configuration._config_lock
    original_has_active_roster_definition = Store.has_active_roster_definition

    @contextmanager
    def observed_lock(*args, **kwargs):
        if threading.current_thread().name == "config-writer":
            writer_lock_attempted.set()
        with original_lock(*args, **kwargs):
            yield

    def paused_has_active_roster_definition(store, slug):
        membership_entered.set()
        if not release_membership.wait(timeout=3):
            raise TimeoutError("test did not release the roster membership check")
        return original_has_active_roster_definition(store, slug)

    monkeypatch.setattr(configuration, "_config_lock", observed_lock)
    monkeypatch.setattr(
        Store,
        "has_active_roster_definition",
        paused_has_active_roster_definition,
    )

    request_result: list[tuple[int, dict, dict[str, str]]] = []
    request_errors: list[BaseException] = []

    def toggle_agent() -> None:
        try:
            request_result.append(
                _json_response(
                    dashboard_server,
                    "/api/agents/toggle",
                    method="POST",
                    body={
                        "slug": "security-reviewer",
                        "enabled": False,
                        "expected_revision": before.revision,
                        "confirm": "DISABLE security-reviewer",
                    },
                    token=dashboard_server["token"],
                )
            )
        except BaseException as exc:  # preserve the worker failure for the test thread
            request_errors.append(exc)

    writer_result: list[object] = []
    writer_errors: list[BaseException] = []

    def change_store_path() -> None:
        try:
            writer_result.append(
                apply_config_operations(
                    [
                        {
                            "op": "set",
                            "path": "store.db_path",
                            "value": str(dashboard_server["home"] / "replacement.db"),
                        }
                    ],
                    expected_revision=before.revision,
                    path=config_path,
                )
            )
        except BaseException as exc:  # preserve the worker failure for the test thread
            writer_errors.append(exc)
        finally:
            writer_done.set()

    request_thread = threading.Thread(target=toggle_agent, name="agent-toggle")
    writer_thread = threading.Thread(target=change_store_path, name="config-writer")
    request_thread.start()
    try:
        assert membership_entered.wait(timeout=3)
        writer_thread.start()
        assert writer_lock_attempted.wait(timeout=3)
        assert not writer_done.wait(timeout=0.1)
    finally:
        release_membership.set()
    request_thread.join(timeout=5)
    writer_thread.join(timeout=5)

    assert not request_thread.is_alive()
    assert not writer_thread.is_alive()
    assert request_errors == []
    assert len(request_result) == 1
    status, payload, _headers = request_result[0]
    assert status == 200
    assert payload["changed"] is True
    assert payload["config"]["effective"]["agents"]["disabled"] == ["security-reviewer"]
    assert writer_result == []
    assert len(writer_errors) == 1
    assert isinstance(writer_errors[0], ConfigConflictError)
    after = read_config_state(config_path)
    assert Path(after.effective["store"]["db_path"]) == store_path


@pytest.mark.parametrize(
    "persisted_document",
    [None, {"agents": {"disabled": []}}],
    ids=["absent-agents-key", "explicit-empty-disabled-list"],
)
def test_agent_toggle_semantic_noop_preserves_persisted_config(
    dashboard_server: dict,
    persisted_document: dict | None,
) -> None:
    """A locked no-op toggle neither rewrites nor normalizes the config."""

    from agency_runtime.core.config import reset_config_cache

    config_path = Path(dashboard_server["store"].config_path)
    if persisted_document is not None:
        config_path.write_text(
            yaml.safe_dump(persisted_document, sort_keys=True),
            encoding="utf-8",
        )
    reset_config_cache()
    before_raw = config_path.read_bytes() if config_path.exists() else None
    status, initial, _headers = _json_response(
        dashboard_server,
        "/api/config",
        token=dashboard_server["token"],
    )
    assert status == 200

    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/agents/toggle",
        method="POST",
        body={
            "slug": "security-reviewer",
            "enabled": True,
            "expected_revision": initial["revision"],
            "confirm": "ENABLE security-reviewer",
        },
        token=dashboard_server["token"],
    )

    assert status == 200
    assert payload["changed"] is False
    assert payload["config"]["revision"] == initial["revision"]
    after_raw = config_path.read_bytes() if config_path.exists() else None
    assert after_raw == before_raw


def test_dashboard_static_shell_is_local_and_hardened(dashboard_server):
    status, raw, headers = _request(dashboard_server, "/")

    assert status == 200
    assert b"Signal Observatory" in raw
    assert headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert "object-src 'none'" in headers["Content-Security-Policy"]
    assert "connect-src 'self'" in headers["Content-Security-Policy"]
    assert headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert headers["Cache-Control"] == "no-store"

    status, charts, _headers = _request(dashboard_server, "/charts.js")
    assert status == 200
    assert b"AgencyCharts" in charts
    assert b"bucketActivity" in charts
    assert b"outcomeCounts" in charts
    assert b"retryDelay" in charts

    status, favicon, favicon_headers = _request(dashboard_server, "/favicon.svg")
    assert status == 200
    assert favicon_headers["Content-Type"] == "image/svg+xml"
    assert b"<svg" in favicon
    assert b"Agency Runtime" in favicon

    status, app_entry, _headers = _request(dashboard_server, "/app.js")
    assert status == 200
    assert b'from "./dashboard-actions.js"' in app_entry
    assert b"createDashboard" in app_entry
    module_assets = []
    for module_name in (
        "dashboard-actions.js",
        "dashboard-config.js",
        "dashboard-core.js",
        "dashboard-live.js",
        "dashboard-render.js",
    ):
        status, module_asset, module_headers = _request(dashboard_server, f"/{module_name}")
        assert status == 200
        assert module_headers["Content-Type"] == "text/javascript; charset=utf-8"
        module_assets.append(module_asset)
    script = app_entry + b"".join(module_assets)
    assert b"registration unknown" in script
    assert b"enablement unknown" in script
    assert b"runtime off" in script
    assert b"callbacks.toggleHost" in script
    assert b"callbacks.toggleAgent" in script
    assert b"Delegation dependency graph" in script
    assert b"receipt.signals?.work_units?.units" in script
    assert b'["id", "Decision"]' in script
    assert b"hostLocation(host)" in script
    assert b"await refreshRuntimeEvidence()" in script
    assert b"collectConfigChanges" in script
    assert b"total_count" in script
    assert b"next_cursor" in script
    assert b"/api/agents/lookup?slug=" in script
    for mutation_path in _OWNER_DASHBOARD_MUTATIONS:
        assert mutation_path.encode() in script
    assert b"APPLY LOCAL-ONLY PROFILE" in script
    assert b"window.prompt" not in script
    assert b"visibilitychange" in script
    assert b"AbortController" in script
    assert b"cancelFullRefresh" in script
    assert b"event.persisted" in script
    assert b'panel.setAttribute("aria-labelledby", active.id)' in script
    assert b"panel.tabIndex = 0" in script
    assert b"APIError" in script
    assert b"updateLocalClock" in script
    assert b"aria-current" in script
    assert b".inert" in script
    assert b"setInterval" not in script
    assert b"navigator.onLine" not in script
    assert b'addEventListener("offline"' not in script

    status, stylesheet, _headers = _request(dashboard_server, "/app.css")
    assert status == 200
    assert re.search(rb"overflow-wrap:\s*anywhere", stylesheet)
    assert b".host-row>div" in stylesheet
    assert b".rail::-webkit-scrollbar" in stylesheet
    assert re.search(rb"prefers-reduced-motion:\s*reduce", stylesheet)
    assert re.search(rb"forced-colors:\s*active", stylesheet)
    assert b":focus-visible" in stylesheet

    assert b'class="skip-link"' in raw
    assert b'href="#main-content"' in raw
    assert b'<link rel="icon" href="/favicon.svg" type="image/svg+xml">' in raw
    assert b'id="roster-search-form"' in raw
    assert b'role="search"' in raw
    assert b'for="roster-search-slug"' in raw
    assert b'id="main-content"' in raw
    assert b'id="live-toggle"' in raw
    assert b'id="live-status"' in raw
    assert b'id="last-sync"' in raw
    assert b'id="live-announcer"' in raw
    assert b'id="activity-chart"' in raw
    assert b'id="activity-chart-summary"' in raw
    assert b'id="outcome-chart"' in raw
    assert b'id="outcome-chart-summary"' in raw
    assert b'id="outcome-success"' in raw
    assert b'id="evidence-caption"' in raw
    assert b'data-evidence="specialists">Specialist activations' in raw
    assert b'id="evidence-context"' in raw
    assert b"activation-current" in stylesheet
    assert b'aria-controls="view-overview"' in raw
    assert b'id="view-routing" class="view" data-view-panel="routing" hidden' in raw
    assert raw.index(b'<script src="/charts.js"') < raw.index(
        b'<script type="module" src="/app.js"'
    )
    assert b'id="provider-health"' in raw
    assert b'id="roster-page-status"' in raw
    assert b'role="status" aria-live="polite"' in raw
    assert b'id="config-form"' in raw
    assert b'data-config-path="dashboard.port"' in raw
    assert b'id="config-server-host"' in raw
    assert b'data-config-path="server.host"' in raw
    assert b'id="config-loopback-hosts"' in raw
    assert b'data-config-path="providers"' in raw
    assert b'id="trim-button"' in raw
    assert b'id="workforce-action-form"' in raw
    assert b'id="config-save-button"' in raw
    assert b'id="confirmation-modal"' in raw
    assert b"not a live provider probe" in raw

    assets = raw + stylesheet + charts + script
    lowered_assets = assets.lower()
    assert b'src="http://' not in lowered_assets
    assert b'src="https://' not in lowered_assets
    assert b'href="http://' not in lowered_assets
    assert b'href="https://' not in lowered_assets
    for forbidden in (
        b"innerHTML",
        b"outerHTML",
        b"insertAdjacentHTML",
        b"eval(",
        b"new Function",
        b"document.write",
    ):
        assert forbidden not in assets


def test_dashboard_workforce_and_hiring_apis_share_revision_bound_lifecycle(
    dashboard_server,
) -> None:
    install_known_contractors(dashboard_server["store"])
    token = dashboard_server["token"]
    slug = "typescript-application-engineer"

    status, workforce, _headers = _json_response(
        dashboard_server,
        "/api/workforce?state=contractor&limit=20",
        token=token,
    )
    assert status == 200
    assert workforce["counts"]["contractor"] == 9
    assert any(item["agent_slug"] == slug for item in workforce["workers"])

    status, detail, _headers = _json_response(
        dashboard_server,
        f"/api/workforce?worker={slug}",
        token=token,
    )
    assert status == 200
    assert detail["detail"]["worker"]["state"] == "contractor"
    assert detail["detail"]["recruitment_contract"]["stacks"] == [
        "typescript",
        "javascript",
    ]
    assert len(detail["detail"]["closest_workers"]) == min(10, workforce["total"] - 1)
    assert detail["detail"]["promotion_readiness"] == {
        "state": "contractor",
        "human_promotion_available": True,
        "automatic_policy_enabled": False,
        "eligible_for_automatic_promotion": False,
        "required_successes": 0,
        "verified_successes": 0,
        "remaining_successes": 0,
        "verified_work_units": [],
        "evidence_rule": (
            "Distinct accepted work units with an activation receipt and a receipt from "
            "a different verifying worker."
        ),
        "reasons": ["Automatic promotion is off; promotion requires an operator."],
    }
    assert detail["detail"]["compiled_prompt"]["preview"]
    assert detail["detail"]["compiled_prompt"]["hash"]

    status, hiring, _headers = _json_response(
        dashboard_server,
        "/api/hiring?status=applied&limit=20",
        token=token,
    )
    assert status == 200
    assert hiring["count"] == 9
    assert all(item["status"] == "applied" for item in hiring["hiring_cases"])

    status, promoted, _headers = _json_response(
        dashboard_server,
        "/api/workforce/action",
        method="POST",
        body={
            "action": "promote",
            "worker": slug,
            "expected_revision": 0,
            "reason": "independently verified assignments",
        },
        token=token,
    )
    assert status == 200
    assert promoted["worker"]["state"] == "employee"

    status, rejected, _headers = _json_response(
        dashboard_server,
        "/api/workforce/action",
        method="POST",
        body={
            "action": "suspend",
            "worker": slug,
            "expected_revision": 1,
            "reason": "operator hold",
            "confirm": "wrong",
        },
        token=token,
    )
    assert status == 400
    assert f"SUSPEND {slug}" in rejected["error"]

    status, suspended, _headers = _json_response(
        dashboard_server,
        "/api/workforce/action",
        method="POST",
        body={
            "action": "suspend",
            "worker": slug,
            "expected_revision": 1,
            "reason": "operator hold",
            "confirm": f"SUSPEND {slug}",
        },
        token=token,
    )
    assert status == 200
    assert suspended["worker"]["state"] == "suspended"


def test_dashboard_hiring_collection_stays_bounded_and_exact_case_keeps_evidence(
    dashboard_server,
) -> None:
    store = dashboard_server["store"]
    large_document = {"payload": "http-exact-evidence-" * 12_000}
    evidence_fields = {
        "gap_evidence",
        "duplicate_evidence",
        "contract_evidence",
        "critic_evidence",
        "model_evidence",
    }
    exact_case_id = ""
    for index in range(MAX_HIRING_SUMMARY_PAGE):
        evidence = large_document if index == 0 else {"case": index}
        contract_document = json.dumps(
            evidence,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        case = store.create_hiring_case(
            case_type="hire",
            proposed_slug=f"http-bounded-hire-{index}",
            work_unit_id=f"http-bounded-hiring-unit-{index}",
            request_hash=hashlib.sha256(f"http-bounded-hiring-{index}".encode()).hexdigest(),
            gap_evidence=evidence,
            duplicate_evidence=evidence,
            contract_evidence=evidence,
            critic_evidence=evidence,
            model_evidence=evidence,
            contract_hash=hashlib.sha256(contract_document.encode("utf-8")).hexdigest(),
        )
        if index == 0:
            exact_case_id = str(case["id"])

    status, raw_collection, headers = _request(
        dashboard_server,
        f"/api/hiring?limit={MAX_HIRING_SUMMARY_PAGE}",
        token=dashboard_server["token"],
    )
    collection = json.loads(raw_collection)

    assert status == 200
    assert len(raw_collection) <= MAX_HIRING_COLLECTION_RESPONSE_BYTES
    assert int(headers["Content-Length"]) == len(raw_collection)
    assert collection["count"] == collection["total_count"] == MAX_HIRING_SUMMARY_PAGE
    assert all(item["evidence_included"] is False for item in collection["hiring_cases"])
    assert all(not evidence_fields.intersection(item) for item in collection["hiring_cases"])
    assert b"http-exact-evidence" not in raw_collection

    status, raw_exact, _headers = _request(
        dashboard_server,
        f"/api/hiring?case_id={exact_case_id}",
        token=dashboard_server["token"],
    )
    exact = json.loads(raw_exact)["hiring_case"]
    assert status == 200
    assert len(raw_exact) > MAX_HIRING_COLLECTION_RESPONSE_BYTES
    assert exact["evidence_included"] is True
    assert all(exact[field] == large_document for field in evidence_fields)


def test_dashboard_hiring_response_budget_failure_is_a_generic_500(
    dashboard_server,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_sentinel = "private-budget-invariant-detail"

    def oversized_snapshot(**_kwargs):
        return {
            "rows": [{"id": "oversized", "payload": private_sentinel * 50_000}],
            "total_count": 1,
            "filtered_count": 1,
            "status_counts": {"proposed": 1},
            "type_counts": {"hire": 1},
            "truncated": False,
            "next_created_at": "",
            "next_id": "",
            "collection_revision": "oversized-test-revision",
        }

    monkeypatch.setattr(
        dashboard_server["store"],
        "get_hiring_cases_page_snapshot",
        oversized_snapshot,
    )
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/hiring?limit=200",
        token=dashboard_server["token"],
    )

    assert status == 500
    assert payload == {"error": "internal server error"}
    assert private_sentinel not in json.dumps(payload)

    def rejected_snapshot(**_kwargs):
        raise WorkforcePayloadBudgetError(private_sentinel)

    monkeypatch.setattr(
        dashboard_server["store"],
        "get_hiring_cases_page_snapshot",
        rejected_snapshot,
    )
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/hiring?limit=200",
        token=dashboard_server["token"],
    )
    assert status == 500
    assert payload == {"error": "internal server error"}


def test_dashboard_worker_detail_omits_history_documents_with_readiness_parity(
    dashboard_server,
) -> None:
    store = dashboard_server["store"]
    install_known_contractors(store)
    contractor = store.get_workforce_worker(
        "typescript-application-engineer",
        disabled_agents=(),
    )
    verifier = store.get_workforce_worker("security-reviewer", disabled_agents=())
    store.create_run(
        trace_id="dashboard-summary-trace",
        session_id="dashboard-summary-session",
        host="codex",
    )
    with closing(store._connect()) as conn, conn:
        conn.executemany(
            "INSERT INTO delegation_activation_receipts "
            "(id, token_hash, session_id, trace_id, work_unit_id, specialist_slug, "
            "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
            "native_run_id, created_at, consumed_at) VALUES "
            "(?, ?, 'dashboard-summary-session', 'dashboard-summary-trace', ?, ?, ?, ?, "
            "'native-child', ?, ?, '2026-07-26T00:00:00+00:00', "
            "'2026-07-26T00:00:01+00:00')",
            [
                (
                    "dashboard-contractor-activation",
                    "5" * 64,
                    "dashboard-summary-unit",
                    contractor["agent_slug"],
                    contractor["current_version"],
                    contractor["current_hash"],
                    "dashboard-contractor-child",
                    "codex:dashboard-contractor-child",
                ),
                (
                    "dashboard-verifier-activation",
                    "6" * 64,
                    "dashboard-summary-review",
                    verifier["agent_slug"],
                    verifier["current_version"],
                    verifier["current_hash"],
                    "dashboard-verifier-child",
                    "codex:dashboard-verifier-child",
                ),
            ],
        )
        event_sequence = int(
            conn.execute(
                "SELECT COALESCE(MAX(event_sequence), 0) + 1 FROM agent_worker_events"
            ).fetchone()[0]
        )
        conn.execute(
            "INSERT INTO agent_worker_events "
            "(id, event_sequence, worker_id, event_type, from_class, to_class, "
            "from_standing, to_standing, version, actor, surface, reason, evidence, "
            "created_at) VALUES (?, ?, ?, 'audit', 'contractor', 'contractor', "
            "'active', 'active', ?, 'test', 'dashboard', 'large private audit evidence', ?, "
            "'2026-07-26T00:00:02+00:00')",
            (
                str(uuid4()),
                event_sequence,
                contractor["worker_id"],
                contractor["current_version"],
                json.dumps(
                    {"payload": "dashboard-private-event-" * 10_000},
                    separators=(",", ":"),
                ),
            ),
        )
    recorded = store.record_workforce_outcome(
        contractor["worker_id"],
        idempotency_key="7" * 64,
        event_type="acceptance",
        outcome="passed",
        score=1.0,
        evidence_hash="8" * 64,
        evidence_refs={
            "payload": "dashboard-private-outcome-" * 9_000,
            "independent_verifier_worker_id": verifier["worker_id"],
            "independent_verification_receipt_id": "dashboard-verifier-activation",
        },
        activation_receipt_id="dashboard-contractor-activation",
        auto_promote_successes=0,
        disabled_agents=(),
    )
    full = store.get_workforce_worker_detail(
        contractor["worker_id"],
        disabled_agents=(),
    )
    expected_readiness = promotion_readiness(
        full["worker"],
        full["outcomes"],
        required_successes=0,
    )
    assert full["outcomes"][0]["evidence_refs"] == recorded["evidence_refs"]

    status, raw, headers = _request(
        dashboard_server,
        f"/api/workforce?worker={contractor['worker_id']}&limit=100",
        token=dashboard_server["token"],
    )
    detail = json.loads(raw)["detail"]

    assert status == 200
    assert len(raw) <= MAX_WORKFORCE_DETAIL_RESPONSE_BYTES
    assert int(headers["Content-Length"]) == len(raw)
    assert detail["promotion_readiness"] == expected_readiness
    assert all("evidence" not in item for item in detail["events"])
    assert all("evidence_refs" not in item for item in detail["outcomes"])
    assert all("_promotion_evidence_qualified" not in item for item in detail["outcomes"])
    assert detail["events_total_count"] == full["events_total_count"]
    assert detail["outcomes_total_count"] == full["outcomes_total_count"]
    assert b"dashboard-private-event" not in raw
    assert b"dashboard-private-outcome" not in raw


def test_dashboard_worker_detail_response_budget_failure_is_a_generic_500(
    dashboard_server,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR, logger="agency_runtime.server.dashboard")
    store = dashboard_server["store"]
    worker = store.get_workforce_worker("security-reviewer", disabled_agents=())
    private_sentinel = "oversized-worker-private-sentinel"

    def oversized_worker_detail(_worker, **_kwargs):
        return {
            "worker": worker,
            "outcomes": [],
            "private_payload": private_sentinel + ("x" * MAX_WORKFORCE_DETAIL_RESPONSE_BYTES),
        }

    monkeypatch.setattr(
        store,
        "get_workforce_worker_detail",
        oversized_worker_detail,
    )
    status, raw, _headers = _request(
        dashboard_server,
        "/api/workforce?worker=security-reviewer&limit=200",
        token=dashboard_server["token"],
    )

    assert status == 500
    assert json.loads(raw) == {"error": "internal server error"}
    assert private_sentinel.encode("utf-8") not in raw
    assert private_sentinel not in "\n".join(record.getMessage() for record in caplog.records)


def test_dashboard_workforce_toggle_records_operator_reason(dashboard_server) -> None:
    install_known_contractors(dashboard_server["store"])
    token = dashboard_server["token"]
    slug = "typescript-application-engineer"
    status, workforce, _headers = _json_response(
        dashboard_server,
        "/api/workforce?limit=20",
        token=token,
    )
    assert status == 200

    status, toggled, _headers = _json_response(
        dashboard_server,
        "/api/agents/toggle",
        method="POST",
        body={
            "slug": slug,
            "enabled": False,
            "confirm": f"DISABLE {slug}",
            "expected_revision": workforce["config_revision"],
            "reason": "temporarily excluded after an unsafe near-neighbor result",
        },
        token=token,
    )
    assert status == 200
    assert toggled["changed"] is True

    status, detail, _headers = _json_response(
        dashboard_server,
        f"/api/workforce?worker={slug}",
        token=token,
    )
    assert status == 200
    assert detail["detail"]["worker"]["state"] == "disabled"
    event = detail["detail"]["events"][0]
    assert event["event_type"] == "disable"
    assert "reason" not in event
    assert event["reason_present"] is True
    assert "reason_hash" not in event
    serialized = json.dumps(detail)
    assert "temporarily excluded" not in serialized
    assert (
        hashlib.sha256(b"temporarily excluded after an unsafe near-neighbor result").hexdigest()
        not in serialized
    )


@pytest.mark.parametrize("total_count", [263, 1001])
def test_dashboard_workforce_pages_expose_exact_large_population_and_facets(
    dashboard_server,
    total_count: int,
) -> None:
    store = dashboard_server["store"]
    baseline = store.get_workforce_page_snapshot(limit=1)
    assert baseline["total_count"] == 1
    additions = [
        (
            f"scale-worker-{index:04d}",
            "contractor" if index % 3 == 0 else "employee",
        )
        for index in range(total_count - 1)
    ]
    _insert_workforce_rows(store, additions)
    expected_contractors = sum(employment == "contractor" for _slug, employment in additions)

    def drain(*, state: str = "") -> tuple[list[str], set[str]]:
        after = ""
        slugs: list[str] = []
        revisions: set[str] = set()
        while True:
            path = "/api/workforce?limit=73"
            if state:
                path += f"&state={state}"
            if after:
                path += f"&after={after}"
            status, payload, _headers = _json_response(
                dashboard_server,
                path,
                token=dashboard_server["token"],
            )
            assert status == 200
            page = [str(worker["agent_slug"]) for worker in payload["workers"]]
            assert page == sorted(page)
            assert not set(page).intersection(slugs)
            assert payload["count"] == payload["page_count"] == len(page)
            assert payload["total_count"] == payload["total"] == total_count
            assert payload["counts"]["contractor"] == expected_contractors
            assert payload["counts"]["employee"] == total_count - expected_contractors
            assert payload["ordering"] == "agent_slug:asc"
            assert payload["cursor_semantics"] == "live-keyset-after-exclusive"
            revisions.add(str(payload["collection_revision"]))
            slugs.extend(page)
            if not payload["truncated"]:
                assert payload["next_cursor"] is None
                break
            assert payload["next_cursor"] == page[-1]
            after = str(payload["next_cursor"])
        return slugs, revisions

    all_slugs, all_revisions = drain()
    assert len(all_slugs) == len(set(all_slugs)) == total_count
    assert all_slugs == sorted(all_slugs)
    assert len(all_revisions) == 1

    contractor_slugs, contractor_revisions = drain(state="contractor")
    assert len(contractor_slugs) == expected_contractors
    assert contractor_slugs == sorted(contractor_slugs)
    assert contractor_revisions == all_revisions


def test_dashboard_workforce_live_keyset_is_deterministic_across_interpage_insert(
    dashboard_server,
) -> None:
    store = dashboard_server["store"]
    _insert_workforce_rows(
        store,
        [(f"live-worker-{index:04d}", "employee") for index in range(204)],
    )
    status, first, _headers = _json_response(
        dashboard_server,
        "/api/workforce?limit=50",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert first["total_count"] == 205
    assert first["truncated"] is True
    first_slugs = [str(worker["agent_slug"]) for worker in first["workers"]]
    cursor = str(first["next_cursor"])
    assert cursor == first_slugs[-1]

    inserted_slug = f"{cursor}-inserted"
    _insert_workforce_rows(store, [(inserted_slug, "employee")])

    collected = list(first_slugs)
    later_revisions: set[str] = set()
    after = cursor
    while True:
        status, payload, _headers = _json_response(
            dashboard_server,
            f"/api/workforce?limit=50&after={after}",
            token=dashboard_server["token"],
        )
        assert status == 200
        assert payload["total_count"] == 206
        assert payload["cursor_semantics"] == "live-keyset-after-exclusive"
        page = [str(worker["agent_slug"]) for worker in payload["workers"]]
        assert page == sorted(page)
        assert all(slug > after for slug in page)
        assert not set(page).intersection(collected)
        collected.extend(page)
        later_revisions.add(str(payload["collection_revision"]))
        if not payload["truncated"]:
            assert payload["next_cursor"] is None
            break
        after = str(payload["next_cursor"])

    assert inserted_slug in collected
    assert len(collected) == len(set(collected)) == 206
    assert collected == sorted(collected)
    assert later_revisions
    assert str(first["collection_revision"]) not in later_revisions


def test_dashboard_javascript_parses_when_node_is_available() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable")

    root = Path(__file__).parents[1]
    for name in (
        "app.js",
        "charts.js",
        "dashboard-actions.js",
        "dashboard-config.js",
        "dashboard-core.js",
        "dashboard-live.js",
        "dashboard-render.js",
    ):
        script = root / "agency_runtime" / "dashboard" / name
        completed = subprocess.run(
            [node, "--check", str(script)],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert completed.returncode == 0, completed.stderr

    completed = subprocess.run(
        [node, str(root / "tests" / "dashboard_ui.test.mjs")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_dashboard_api_requires_per_launch_token(dashboard_server):
    status, payload, _headers = _json_response(dashboard_server, "/api/overview")

    assert status == 401
    assert payload == {"error": "authentication required"}


def test_dashboard_update_endpoint_is_authenticated_observed_and_read_only(
    dashboard_server,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import update_service

    caplog.set_level(logging.INFO, logger="agency_runtime.observation")
    captured: dict[str, object] = {}
    identity = {
        "package_version": "0.1.0",
        "build_identity": f"0.1.0+g{'a' * 12}",
        "source_revision": "a" * 40,
        "source_branch": "main",
        "source_dirty": False,
        "install_kind": "source-checkout",
        "official_repository": True,
    }
    release_target = {
        "kind": "release",
        "label": "v0.2.0",
        "version": "0.2.0",
        "ref": "v0.2.0",
        "commit_sha": "b" * 40,
        "url": "https://github.com/Holeshot-Software-LLC/agency-runtime/releases/tag/v0.2.0",
        "published_at": "2026-07-28T00:00:00Z",
    }
    main_target = {
        "kind": "main",
        "label": "main",
        "version": None,
        "ref": "main",
        "commit_sha": "c" * 40,
        "url": f"https://github.com/Holeshot-Software-LLC/agency-runtime/commit/{'c' * 40}",
        "published_at": None,
    }
    cache = {
        "schema_version": update_service.CACHE_SCHEMA_VERSION,
        "entries": {
            "channel:release": {
                "checked_at": 1_000,
                "expires_at": 2_000,
                "target": release_target,
                "error": None,
            },
            "channel:main": {
                "checked_at": 1_000,
                "expires_at": 2_000,
                "target": main_target,
                "error": None,
            },
        },
    }
    monkeypatch.setattr(update_service, "_read_cache", lambda **_kwargs: cache)
    monkeypatch.setattr(update_service, "_dashboard_installed_version_snapshot", lambda: identity)
    monkeypatch.setattr(update_service.time, "time", lambda: 1_500)
    snapshot = update_service.dashboard_update_snapshot

    def inspect(*, home_dir, schedule):
        captured.update(home_dir=home_dir, schedule=schedule)
        return snapshot(home_dir=home_dir, schedule=schedule)

    monkeypatch.setattr(update_service, "dashboard_update_snapshot", inspect)
    request_id = str(uuid4())

    unauthorized, _payload, _headers = _json_response(dashboard_server, "/api/update")
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/update",
        token=dashboard_server["token"],
        request_id=request_id,
    )

    assert unauthorized == 401
    assert status == 200
    assert payload["schema_version"] == "agency.dashboard.update.v1"
    assert payload["checking"] is False
    assert payload["release"]["status"] == "update_available"
    assert payload["release"]["update_available"] is True
    assert payload["main"]["status"] == "different_target"
    assert payload["main"]["update_available"] is None
    assert captured == {"home_dir": dashboard_server["home"], "schedule": True}
    observation = _wait_for_dashboard_observation(caplog, request_id)
    assert observation["operation"] == "update"
    assert observation["outcome"] == "ok"

    node = shutil.which("node")
    if node is not None:
        module_url = (
            Path(__file__).parents[1] / "agency_runtime" / "dashboard" / "dashboard-live.js"
        ).as_uri()
        validator = (
            f"import {{ validateUpdateStatusPayload }} from {json.dumps(module_url)};"
            "let input = ''; for await (const chunk of process.stdin) input += chunk;"
            "validateUpdateStatusPayload(JSON.parse(input));"
        )
        completed = subprocess.run(
            [node, "--input-type=module", "--eval", validator],
            input=json.dumps(payload),
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr


def test_dashboard_correlates_requests_with_content_free_observations(
    dashboard_server,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="agency_runtime.observation")
    request_id = str(uuid4())

    status, payload, headers = _json_response(
        dashboard_server,
        "/api/health",
        token=dashboard_server["token"],
        request_id=request_id,
    )

    assert status == 200
    assert payload == {"status": "ok", "request_id": request_id}
    assert headers["X-Agency-Request-ID"] == request_id
    assert headers["X-Request-ID"] == request_id
    observation = _wait_for_dashboard_observation(caplog, request_id)
    assert observation == {
        "schema_version": 1,
        "request_id": request_id,
        "correlation_digest": "",
        "surface": "dashboard",
        "operation": "health",
        "outcome": "ok",
        "reason_code": "completed",
        "duration_ms": observation["duration_ms"],
    }
    assert 0 <= observation["duration_ms"] < 5_000

    caplog.clear()
    invalid = "Bearer do-not-log-this"
    status, payload, headers = _json_response(
        dashboard_server,
        "/api/health",
        token=dashboard_server["token"],
        request_id=invalid,
    )
    generated = headers["X-Agency-Request-ID"]
    assert status == 200
    assert payload == {"status": "ok"}
    assert generated.startswith("arq-")
    assert len(generated) == 36
    _wait_for_dashboard_observation(caplog, generated)
    assert invalid not in "\n".join(record.getMessage() for record in caplog.records)


def test_dashboard_route_lab_binds_generated_trace_to_request_observation(
    dashboard_server,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caplog.set_level(logging.INFO, logger="agency_runtime.observation")
    captured: dict[str, str] = {}

    def explain_with_trace(
        session_id,
        task,
        _catalog,
        *,
        trace_id,
        **_kwargs,
    ):
        captured["trace_id"] = trace_id
        return {
            "schema_version": "agency.selection_explain.v1",
            "session_id": session_id,
            "task": task,
            "routing": {
                "eligibility_rejections": [],
                "selected_ids": [],
                "trace_id": trace_id,
            },
            "selected": [],
            "considered_candidates": [],
            "rejected_candidates": [],
            "signals": {"work_units": {"units": []}},
            "status": "empty",
        }

    monkeypatch.setattr(dashboard_module, "explain_route", explain_with_trace)
    monkeypatch.setattr(
        dashboard_module,
        "delegation_plan_projection",
        lambda *_args, **_kwargs: {"units": []},
    )
    request_id = str(uuid4())
    status, payload, headers = _json_response(
        dashboard_server,
        "/api/route",
        method="POST",
        body={"task": "Trace this routing decision", "host": "codex"},
        token=dashboard_server["token"],
        request_id=request_id,
    )

    assert status == 200
    assert headers["X-Agency-Request-ID"] == request_id
    assert payload["routing"]["trace_id"] == captured["trace_id"]
    observation = _wait_for_dashboard_observation(caplog, request_id)
    assert observation["operation"] == "route"
    assert observation["correlation_digest"] == correlation_observation_digest(captured["trace_id"])


def test_dashboard_keep_alive_requests_use_independent_request_ids(
    dashboard_server,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caplog.set_level(logging.INFO, logger="agency_runtime.observation")
    request_ids = (
        "arq-11111111111111111111111111111111",
        "arq-22222222222222222222222222222222",
    )
    generated_ids = iter(request_ids)
    monkeypatch.setattr(dashboard_module, "new_request_id", lambda: next(generated_ids))
    monkeypatch.setattr(
        "agency_runtime.core.store.observed_sqlite.SLOW_SQLITE_MILLISECONDS",
        0.0,
    )

    connection = HTTPConnection("127.0.0.1", dashboard_server["port"], timeout=5)
    response_ids: list[str] = []
    sockets: list[object] = []
    try:
        for expected_request_id in request_ids:
            connection.request(
                "GET",
                "/api/overview",
                headers={"Authorization": f"Bearer {dashboard_server['token']}"},
            )
            response = connection.getresponse()
            payload = json.loads(response.read())
            assert response.status == 200
            assert response.will_close is False
            assert "request_id" not in payload
            response_ids.append(response.headers["X-Agency-Request-ID"])
            sockets.append(connection.sock)
            _wait_for_dashboard_observation(caplog, expected_request_id)
    finally:
        connection.close()

    assert response_ids == list(request_ids)
    assert sockets[0] is not None
    assert sockets[0] is sockets[1]
    observations = [
        json.loads(record.getMessage().split(" ", 1)[1])
        for record in caplog.records
        if record.getMessage().startswith("agency_observation ")
    ]
    dashboard_observations = [
        item
        for item in observations
        if item["surface"] == "dashboard" and item["operation"] == "overview"
    ]
    assert [item["request_id"] for item in dashboard_observations] == list(request_ids)
    for request_id in request_ids:
        assert any(
            item["surface"] == "store" and item["request_id"] == request_id for item in observations
        )


def test_dashboard_keep_alive_protocol_error_uses_a_fresh_request_id(
    dashboard_server,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caplog.set_level(logging.INFO, logger="agency_runtime.observation")
    request_ids = (
        "arq-33333333333333333333333333333333",
        "arq-44444444444444444444444444444444",
    )
    generated_ids = iter(request_ids)
    monkeypatch.setattr(dashboard_module, "new_request_id", lambda: next(generated_ids))

    connection = HTTPConnection("127.0.0.1", dashboard_server["port"], timeout=5)
    try:
        connection.request(
            "GET",
            "/api/health",
            headers={"Authorization": f"Bearer {dashboard_server['token']}"},
        )
        first_response = connection.getresponse()
        assert first_response.status == 200
        assert json.loads(first_response.read()) == {"status": "ok"}
        assert first_response.headers["X-Agency-Request-ID"] == request_ids[0]
        assert first_response.will_close is False
        first_socket = connection.sock
        _wait_for_dashboard_observation(caplog, request_ids[0])

        connection.request("TRACE", "/api/health")
        assert connection.sock is first_socket
        error_response = connection.getresponse()
        error_payload = json.loads(error_response.read())
        assert error_response.status == 501
        assert error_payload == {"error": "request rejected"}
        assert error_response.headers["Content-Type"] == "application/json; charset=utf-8"
        assert error_response.headers["Cache-Control"] == "no-store"
        assert error_response.headers["Connection"] == "close"
        assert error_response.headers["X-Request-ID"] == request_ids[1]
        assert error_response.headers["X-Agency-Request-ID"] == request_ids[1]
        assert error_response.will_close is True
        observation = _wait_for_dashboard_observation(caplog, request_ids[1])
        assert observation["operation"] == "protocol_error"
        assert observation["outcome"] == "error"
        assert observation["reason_code"] == "http_501"
    finally:
        connection.close()


def test_dashboard_malformed_keep_alive_request_cannot_reuse_prior_headers(
    dashboard_server,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caplog.set_level(logging.INFO, logger="agency_runtime.observation")
    supplied_request_id = "arq-55555555555555555555555555555555"
    parser_request_id = "arq-66666666666666666666666666666666"
    monkeypatch.setattr(dashboard_module, "new_request_id", lambda: parser_request_id)
    private_sentinel = b"private-parser-detail-must-not-return"

    client = socket.create_connection(("127.0.0.1", dashboard_server["port"]), timeout=5)
    client.settimeout(5)
    try:
        client.sendall(
            (
                "GET /api/health HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{dashboard_server['port']}\r\n"
                f"Authorization: Bearer {dashboard_server['token']}\r\n"
                f"X-Agency-Request-ID: {supplied_request_id}\r\n"
                "\r\n"
            ).encode("ascii")
        )
        first_response = HTTPResponse(client, method="GET")
        first_response.begin()
        assert first_response.status == 200
        assert json.loads(first_response.read()) == {
            "status": "ok",
            "request_id": supplied_request_id,
        }
        assert first_response.headers["X-Agency-Request-ID"] == supplied_request_id
        assert first_response.will_close is False
        _wait_for_dashboard_observation(caplog, supplied_request_id)

        client.sendall(
            b"GET /api/health HTTP/1.1\r\n"
            b"X-Oversized: " + private_sentinel + (b"x" * 65_537) + b"\r\n\r\n"
        )
        error_response = HTTPResponse(client, method="GET")
        error_response.begin()
        error_body = error_response.read()
        assert error_response.status == 431
        assert json.loads(error_body) == {"error": "request rejected"}
        assert error_response.headers["Content-Type"] == "application/json; charset=utf-8"
        assert error_response.headers["Connection"] == "close"
        assert error_response.headers["X-Request-ID"] == parser_request_id
        assert error_response.headers["X-Agency-Request-ID"] == parser_request_id
        assert supplied_request_id.encode("ascii") not in error_body
        assert private_sentinel not in error_body
        observation = _wait_for_dashboard_observation(caplog, parser_request_id)
        assert observation["operation"] == "protocol_error"
        assert observation["outcome"] == "denied"
        assert observation["reason_code"] == "http_431"
        assert private_sentinel.decode("ascii") not in "\n".join(
            record.getMessage() for record in caplog.records
        )
    finally:
        client.close()


def test_dashboard_broker_token_is_scoped_to_bounded_control_endpoints(
    dashboard_server,
) -> None:
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/runtime",
        token=dashboard_server["broker_token"],
    )
    assert status == 200
    assert payload["master"]["enabled"] is True

    for path in ("/api/agents/toggle", "/api/hosts/toggle", "/api/runtime/toggle"):
        status, payload, _headers = _json_response(
            dashboard_server,
            path,
            method="POST",
            body={},
            token=dashboard_server["broker_token"],
        )
        assert status == 403
        assert payload == {"error": "owner control required"}

    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/config",
        token=dashboard_server["broker_token"],
    )
    assert status == 401
    assert payload == {"error": "authentication required"}

    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/overview",
        token=dashboard_server["broker_token"],
    )
    assert status == 401
    assert payload == {"error": "authentication required"}

    status, payload, _headers = _json_response(dashboard_server, "/api/live")
    assert status == 401
    assert payload == {"error": "authentication required"}


def test_dashboard_live_snapshot_is_authenticated_stable_and_changes_with_activity(
    dashboard_server,
):
    status, first, headers = _json_response(
        dashboard_server,
        "/api/live",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert set(first) == {
        "schema_version",
        "sampled_at",
        "revision",
        "overview",
        "activity",
        "activity_collections",
        "master",
        "config_path",
        "config_revision",
        "environment_overrides",
        "store_path",
        "desired_store_path",
        "store_restart_required",
        "service_binding",
    }
    assert first["schema_version"] == 1
    assert isinstance(first["sampled_at"], str)
    sampled_at = datetime.fromisoformat(first["sampled_at"].replace("Z", "+00:00"))
    assert sampled_at.tzinfo is not None
    assert len(first["revision"]) == 64
    assert all(character in "0123456789abcdef" for character in first["revision"])
    assert set(first["overview"]) == {
        "status",
        "db_size_bytes",
        "wal_size_bytes",
        "provider_health",
        "inference",
        "recent",
    }
    assert set(first["activity"]) == {
        "runs",
        "routing",
        "delegations",
        "receipts",
        "finalizations",
        "specialists",
    }
    assert set(first["activity_collections"]) == set(first["activity"])
    assert all(
        collection["page_count"] == len(first["activity"][kind])
        and collection["total_count"] >= collection["page_count"]
        for kind, collection in first["activity_collections"].items()
    )
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"

    status, unchanged, _headers = _json_response(
        dashboard_server,
        "/api/live",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert unchanged["revision"] == first["revision"]

    dashboard_server["store"].record_delegation(
        trace_id="trace-dashboard-live",
        session_id="session-dashboard-live",
        host="test",
        work_unit_id="unit-live",
        recommended_agent="security-reviewer",
        status="completed",
        backend="test",
        executed_worker_kind="test-worker",
        executed_worker_id="dashboard-live-worker",
        native_run_id="dashboard-live-native-run",
    )
    status, changed, _headers = _json_response(
        dashboard_server,
        "/api/live",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert changed["revision"] != first["revision"]


def test_dashboard_runtime_master_api_is_authenticated_atomic_and_live(
    dashboard_server,
) -> None:
    status, payload, _headers = _json_response(dashboard_server, "/api/runtime")
    assert status == 401
    assert payload == {"error": "authentication required"}

    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/runtime",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert payload["master"]["enabled"] is True
    assert payload["master"]["generation"] == 0

    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/runtime/toggle",
        method="POST",
        body={
            "enabled": False,
            "confirm": "DISABLE AGENCY",
            "expected_generation": 0,
        },
    )
    assert status == 401
    assert payload == {"error": "authentication required"}

    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/runtime/toggle",
        method="POST",
        body={
            "enabled": False,
            "confirm": "DISABLE AGENCY",
            "expected_generation": 0,
        },
        token=dashboard_server["token"],
    )
    assert status == 200
    assert payload["ok"] is True
    assert payload["changed"] is True
    assert payload["master"]["enabled"] is False
    assert payload["master"]["generation"] == 1
    assert payload["master"]["source"] == "dashboard"

    status, unchanged, _headers = _json_response(
        dashboard_server,
        "/api/runtime/toggle",
        method="POST",
        body={
            "enabled": False,
            "confirm": "DISABLE AGENCY",
            "expected_generation": 1,
        },
        token=dashboard_server["token"],
    )
    assert status == 200
    assert unchanged["changed"] is False
    assert unchanged["master"]["generation"] == 1

    status, stale, _headers = _json_response(
        dashboard_server,
        "/api/runtime/toggle",
        method="POST",
        body={
            "enabled": True,
            "confirm": "ENABLE AGENCY",
            "expected_generation": 0,
        },
        token=dashboard_server["token"],
    )
    assert status == 409
    assert "expected 0, found 1" in stale["error"]

    for path in ("/api/live", "/api/overview", "/api/hosts"):
        status, current, _headers = _json_response(
            dashboard_server,
            path,
            token=dashboard_server["token"],
        )
        assert status == 200
        assert current["master"]["enabled"] is False
        assert current["master"]["generation"] == 1


def test_dashboard_route_lab_bypasses_all_routing_while_master_is_off(
    dashboard_server,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status, _payload, _headers = _json_response(
        dashboard_server,
        "/api/runtime/toggle",
        method="POST",
        body={
            "enabled": False,
            "confirm": "DISABLE AGENCY",
            "expected_generation": 0,
        },
        token=dashboard_server["token"],
    )
    assert status == 200

    def forbidden(*_args, **_kwargs):
        raise AssertionError("disabled Route Lab must not enter the routing path")

    monkeypatch.setattr(dashboard_module, "explain_route", forbidden)
    monkeypatch.setattr(dashboard_module, "load_config", forbidden)
    monkeypatch.setattr(Store, "get_active_roster_as_catalog", forbidden)

    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/route",
        method="POST",
        body={"task": "Route this task"},
        token=dashboard_server["token"],
    )

    assert status == 200
    assert payload["status"] == "disabled"
    assert payload["bypassed"] is True
    assert payload["master"]["enabled"] is False
    assert "bypassed routing" in payload["message"]
    assert payload["delegation_plan"]["authority"] == "recommendation_only"
    assert payload["delegation_plan"]["unit_count"] == 0
    assert "no delegation recommendation" in payload["delegation_plan"]["evidence_contract"]


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({}, "enabled must be a JSON boolean"),
        (
            {"enabled": False, "expected_generation": True},
            "expected_generation must be a non-negative integer",
        ),
        (
            {"enabled": False, "expected_generation": -1},
            "expected_generation must be a non-negative integer",
        ),
        (
            {"enabled": False, "expected_generation": 0, "confirm": "disable agency"},
            "confirmation phrase must be DISABLE AGENCY",
        ),
        (
            {"enabled": True, "expected_generation": 0, "confirm": "enable agency"},
            "confirmation phrase must be ENABLE AGENCY",
        ),
    ],
)
def test_dashboard_runtime_toggle_rejects_malformed_or_unconfirmed_updates(
    dashboard_server,
    body: dict[str, object],
    message: str,
) -> None:
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/runtime/toggle",
        method="POST",
        body=body,
        token=dashboard_server["token"],
    )

    assert status == 400
    assert payload == {"error": message}


def test_dashboard_live_snapshot_is_metadata_only_and_never_leaks_credentials(
    dashboard_server,
    monkeypatch: pytest.MonkeyPatch,
):
    from agency_runtime.core.config import reset_config_cache

    secret = "live-secret-sentinel-never-return"
    monkeypatch.setenv("AGENCY_JUDGE_API_KEY", secret)
    reset_config_cache()
    dashboard_server["store"].record_delegation(
        trace_id="trace-dashboard-secret",
        session_id="session-dashboard-secret",
        host="test",
        work_unit_id="unit-secret",
        recommended_agent="security-reviewer",
        status="failed",
        backend="test",
        error=secret,
    )
    original = Store.recent_dashboard_activity

    def captured_detail(self: Store, *, limit: int = 50):
        activity = original(self, limit=limit)
        activity["delegations"][0]["skip_reason"] = secret
        activity["routing"].append(
            {
                "id": "captured-routing",
                "created_at": "2026-07-11T12:00:00Z",
                "work_units": {"task": secret},
            }
        )
        activity["specialists"].append(
            {
                "id": "captured-specialist",
                "session_id": "session-secret",
                "trace_id": "trace-secret",
                "slug": "security-reviewer",
                "loaded_at": "2026-07-11T12:00:00Z",
                "expired_at": None,
                "state": "current",
                "prompt": secret,
            }
        )
        return activity

    monkeypatch.setattr(Store, "recent_dashboard_activity", captured_detail)

    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/live",
        token=dashboard_server["token"],
    )

    assert status == 200
    encoded = json.dumps(payload, sort_keys=True)
    assert secret not in encoded
    assert dashboard_server["token"] not in encoded
    assert all("skip_reason" not in row for row in payload["activity"]["delegations"])
    assert all("work_units" not in row for row in payload["activity"]["routing"])
    assert all("prompt" not in row for row in payload["activity"]["specialists"])
    assert _nested_keys(payload).isdisjoint(
        {
            "api_key",
            "completion",
            "content",
            "draft_text",
            "prompt",
            "request_body",
            "response_body",
            "stderr",
            "stdout",
            "task",
            "user_message",
        }
    )


def test_dashboard_live_snapshot_reads_activity_once(
    dashboard_server,
    monkeypatch: pytest.MonkeyPatch,
):
    original = Store.dashboard_activity_snapshot
    calls: list[int] = []

    def counted(self: Store, *, limit: int = 50):
        calls.append(limit)
        return original(self, limit=limit)

    monkeypatch.setattr(Store, "dashboard_activity_snapshot", counted)

    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/live",
        token=dashboard_server["token"],
    )

    assert status == 200
    assert payload["schema_version"] == 1
    assert len(calls) == 1
    assert 1 <= calls[0] <= 200


def test_dashboard_rejects_cross_origin_request(dashboard_server):
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/overview",
        token=dashboard_server["token"],
        origin="https://attacker.example",
    )

    assert status == 403
    assert "cross-origin" in payload["error"]


def test_dashboard_post_requires_json_content_type(dashboard_server):
    for _attempt in range(10):
        status, payload, _headers = _json_response(
            dashboard_server,
            "/api/route",
            method="POST",
            body={"task": "review security"},
            token=dashboard_server["token"],
            content_type="text/plain",
        )

        assert status == 415
        assert "application/json" in payload["error"]


def test_dashboard_rejects_unbounded_numeric_content_length_without_conversion(
    dashboard_server,
):
    response = _raw_request(
        dashboard_server,
        (
            "POST /api/route HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{dashboard_server['port']}\r\n"
            f"Authorization: Bearer {dashboard_server['token']}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {'9' * 5000}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii"),
    )

    assert b"HTTP/1.1 413 " in response
    assert b"request body too large" in response


def test_dashboard_roster_cursor_pages_are_stable_and_complete(dashboard_server):
    from agency_runtime.core.configuration import apply_config_operations, read_config_state

    for slug in ("alpha-reviewer", "zulu-reviewer"):
        dashboard_server["store"]._activate_prevalidated_agent(
            {
                "slug": slug,
                "name": slug,
                "description": f"{slug} description",
                "version": "1.0.0",
                "content": f"You are {slug}.",
            }
        )

    status, first, _headers = _json_response(
        dashboard_server,
        "/api/roster?limit=2",
        token=dashboard_server["token"],
    )

    assert status == 200
    assert [agent["agent_slug"] for agent in first["agents"]] == [
        "alpha-reviewer",
        "security-reviewer",
    ]
    assert first["total_count"] == 3
    assert first["truncated"] is True
    assert first["next_cursor"] == "security-reviewer"

    config_path = Path(dashboard_server["store"].config_path)
    config_before = read_config_state(config_path)
    assert first["config_revision"] == config_before.revision
    config_after = apply_config_operations(
        [{"op": "set", "path": "agents.disabled", "value": ["alpha-reviewer"]}],
        expected_revision=config_before.revision,
        path=config_path,
    ).state

    status, second, _headers = _json_response(
        dashboard_server,
        f"/api/roster?limit=2&after={first['next_cursor']}",
        token=dashboard_server["token"],
    )

    assert status == 200
    assert [agent["agent_slug"] for agent in second["agents"]] == ["zulu-reviewer"]
    assert second["total_count"] == 3
    assert second["truncated"] is False
    assert second["next_cursor"] is None
    assert second["roster_revision"] == first["roster_revision"]
    assert second["config_revision"] == config_after.revision
    assert second["config_revision"] != first["config_revision"]


def test_dashboard_operational_roster_review_and_inference_apis_are_bounded(
    dashboard_server,
):
    for path in (
        "/api/roster/operations",
        "/api/roster/reviews",
        "/api/inference",
    ):
        assert _json_response(dashboard_server, path)[0] == 401

    source_id = dashboard_server["store"].add_agent_source("fixtures/dashboard", "fixture")
    candidate_id = quarantine_candidate(
        {
            "slug": "dashboard-candidate",
            "name": "Dashboard Candidate",
            "division": "engineering",
            "description": "Candidate for bounded review.",
            "source": "fixture",
            "source_version": "candidate-source-revision",
            "version": "1.0.0",
            "content": "Perform bounded review work.",
        },
        source_id,
        dashboard_server["store"],
    )

    status, operations, _headers = _json_response(
        dashboard_server,
        "/api/roster/operations?limit=10&division=engineering&tool=git",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert operations["schema_version"] == "agency.dashboard.roster_operations.v1"
    assert operations["filters"] == {"division": "engineering", "tool": "git"}
    assert operations["agents"][0]["agent_slug"] == "security-reviewer"
    assert "revision_history" in operations["agents"][0]
    assert "prompt_body" not in repr(operations)
    assert len(operations["roster_revision"]) == 64

    status, reviews, _headers = _json_response(
        dashboard_server,
        "/api/roster/reviews?limit=10",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert reviews["queue_count"] == 1
    assert reviews["candidates"][0]["candidate"]["id"] == candidate_id
    assert "message" not in _nested_keys(reviews)

    status, detail, _headers = _json_response(
        dashboard_server,
        f"/api/roster/reviews?candidate_id={candidate_id}",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert detail["candidate_id"] == candidate_id

    status, inference, _headers = _json_response(
        dashboard_server,
        "/api/inference?limit=5",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert inference["schema_version"] == "agency.dashboard.inference_operations.v1"
    assert inference["configured"] is False
    assert inference["required_for_eligible_turns"] is False
    assert inference["state"] == "not_configured"
    assert [provider["name"] for provider in inference["provider_chain"]] == [
        "legacy-judge",
        "ollama-fallback",
    ]
    assert all(provider["configuration_ready"] for provider in inference["provider_chain"])

    status, governance, _headers = _json_response(
        dashboard_server,
        "/api/snapshots",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert governance["operations"]["total_count"] == 1
    assert governance["reviews"]["queue_count"] == 1


@pytest.mark.parametrize(
    "path",
    [
        "/api/roster/operations?unknown=value",
        "/api/roster/operations?query=a&query=b",
        "/api/roster/operations?limit=invalid",
        "/api/roster/operations?limit=0",
        "/api/roster/operations?after=Not-Canonical",
        "/api/roster/operations?a=1&b=2&c=3&d=4&e=5&f=6&g=7&h=8&i=9&j=10&k=11",
        "/api/roster/reviews?limit=0",
        "/api/roster/reviews?pending_cursor=..%2Fcursor",
        "/api/roster/reviews?history_cursor=bad%20cursor",
        "/api/roster/reviews?candidate_id=..%2Fcandidate",
        "/api/roster/reviews?candidate_id=missing",
        "/api/inference?limit=0",
        "/api/inference?unknown=value",
    ],
)
def test_dashboard_operational_queries_fail_closed(dashboard_server, path):
    status, payload, _headers = _json_response(
        dashboard_server,
        path,
        token=dashboard_server["token"],
    )
    assert status == 400
    assert payload["error"]


def test_dashboard_roster_activation_projection_omits_routing_taxonomy(
    dashboard_server,
) -> None:
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/roster?limit=1&projection=activation",
        token=dashboard_server["token"],
    )

    assert status == 200
    assert payload["projection"] == "activation"
    assert payload["store_path"] == str(dashboard_server["store"].db_path)
    assert len(payload["agents"]) == 1
    assert set(payload["agents"][0]) == {
        "agent_slug",
        "name",
        "division",
        "enabled",
        "protected",
    }


def test_dashboard_rejects_bulk_selector_roster_projection(dashboard_server) -> None:
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/roster?projection=selector",
        token=dashboard_server["token"],
    )

    assert status == 400
    assert payload["error"] == "roster projection must be activation when provided"


def test_exact_lookup_preserves_maximum_unicode_selector_metadata(
    dashboard_server,
) -> None:
    categories = [f"{index:03d}-" + ("🧪" * 126) for index in range(MAX_LIST_ITEMS)]
    capabilities = [f"{index:03d}-" + ("🛡" * 126) for index in range(MAX_LIST_ITEMS)]
    for index in range(4):
        dashboard_server["store"]._activate_prevalidated_agent(
            {
                "slug": f"max-unicode-{index:02d}",
                "name": "😀" * 128,
                "division": "🧭" * 128,
                "description": "🔐" * 4_096,
                "version": "1.0.0",
                "content": f"Unicode specialist {index}",
                "categories": categories,
                "capabilities": capabilities,
            }
        )
    descriptor = write_dashboard_runtime(
        token=dashboard_server["token"],
        port=dashboard_server["port"],
        pid=os.getpid(),
        home_dir=dashboard_server["home"],
    )
    try:
        slugs = [*(f"max-unicode-{index:02d}" for index in range(4)), "security-reviewer"]
        responses = [
            dashboard_api_request(
                f"/api/agents/lookup?slug={slug}",
                descriptor=descriptor,
            )
            for slug in slugs
        ]
    finally:
        remove_dashboard_runtime(
            token=dashboard_server["token"],
            pid=os.getpid(),
            home_dir=dashboard_server["home"],
        )

    assert all(response["count"] == 1 for response in responses)
    assert all(response["limit"] == 1 for response in responses)
    assert all(response["truncated"] is False for response in responses)
    assert all(response["projection"] == "selector" for response in responses)
    assert [response["filter_slug"] for response in responses] == slugs
    agents = [response["agents"][0] for response in responses]
    assert [agent["agent_slug"] for agent in agents] == slugs
    for agent in agents[:-1]:
        assert agent["description"] == "🔐" * 4_096
        assert agent["categories"] == categories
        assert agent["capabilities"] == capabilities


def test_roster_broker_endpoints_fail_closed_when_store_restart_is_required(
    dashboard_server,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status, config, _headers = _json_response(
        dashboard_server,
        "/api/config",
        token=dashboard_server["token"],
    )
    assert status == 200
    replacement = dashboard_server["home"] / "replacement.db"
    status, saved, _headers = _json_response(
        dashboard_server,
        "/api/config",
        token=dashboard_server["token"],
        method="POST",
        body={
            "operations": [
                {
                    "op": "set",
                    "path": "store.db_path",
                    "value": str(replacement),
                }
            ],
            "expected_revision": config["revision"],
            "confirmations": ["SAVE CONFIG"],
        },
    )
    assert status == 200
    assert saved["service_binding"]["store_restart_required"] is False

    monkeypatch.delenv("AGENCY_DB_PATH")
    from agency_runtime.core.config import reset_config_cache

    reset_config_cache()
    status, refreshed, _headers = _json_response(
        dashboard_server,
        "/api/config",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert refreshed["service_binding"] == {
        "store_path": str(dashboard_server["store"].db_path),
        "desired_store_path": str(replacement),
        "store_restart_required": True,
    }

    requests = [
        ("/api/roster?limit=1&projection=activation", "GET", None),
        ("/api/agents/lookup?slug=security-reviewer", "GET", None),
        ("/api/hosts", "GET", None),
        (
            "/api/agents/toggle",
            "POST",
            {
                "slug": "security-reviewer",
                "enabled": False,
                "expected_revision": refreshed["revision"],
                "confirm": "DISABLE security-reviewer",
            },
        ),
        (
            "/api/roster/action",
            "POST",
            {
                "action": "approve",
                "snapshot_id": "pending",
                "confirm": "APPROVE pending",
            },
        ),
        (
            "/api/hosts/toggle",
            "POST",
            {
                "host": "codex",
                "enabled": False,
                "expected_generation": 0,
                "confirm": "DISABLE codex",
            },
        ),
        (
            "/api/maintenance/trim",
            "POST",
            {"confirm": "TRIM RUNTIME DATA"},
        ),
    ]
    for path, method, body in requests:
        status, payload, _headers = _json_response(
            dashboard_server,
            path,
            token=dashboard_server["token"],
            method=method,
            body=body,
        )
        assert status == 409
        assert payload["restart_required"] is True
        assert payload["store_path"] == str(dashboard_server["store"].db_path)
        assert payload["desired_store_path"] == str(replacement)


def test_dashboard_exact_lookup_reaches_and_toggles_agent_beyond_first_thousand(
    dashboard_server,
):
    store = dashboard_server["store"]
    activated_at = "2026-07-14T12:00:00+00:00"
    rows = [
        (
            f"bulk-{index}",
            f"agent-{index:04d}",
            f"Agent {index:04d}",
            "test",
            "bulk lookup regression",
            "test",
            "1.0.0",
            f"hash-{index}",
            "[]",
            "[]",
            "[]",
            "",
            activated_at,
        )
        for index in range(1001)
    ]
    versions = [
        (
            f"bulk-version-{index}",
            f"agent-{index:04d}",
            "1.0.0",
            "1.0.0",
            "test",
            f"hash-{index}",
            "",
            "{}",
            activated_at,
        )
        for index in range(1001)
    ]
    conn = store._connect()
    try:
        conn.executemany(
            "INSERT INTO agent_versions "
            "(id, agent_slug, version, source_version, source_id, hash, content, metadata, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            versions,
        )
        conn.executemany(
            "INSERT INTO agent_active "
            "(id, agent_slug, name, division, description, source, version, hash, "
            "categories, capabilities, tool_affinity, prompt_path, activated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()

    status, first, _headers = _json_response(
        dashboard_server,
        "/api/roster",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert first["count"] == 1000
    assert first["next_cursor"] == "agent-0999"
    assert all(agent["agent_slug"] != "agent-1000" for agent in first["agents"])

    assert (
        _json_response(
            dashboard_server,
            "/api/agents/lookup?slug=agent-1000",
        )[0]
        == 401
    )
    status, lookup, _headers = _json_response(
        dashboard_server,
        "/api/agents/lookup?slug=agent-1000",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert [agent["agent_slug"] for agent in lookup["agents"]] == ["agent-1000"]
    assert lookup["agents"][0]["enabled"] is True
    assert lookup["total_count"] == 1002
    assert lookup["filter_slug"] == "agent-1000"

    status, config, _headers = _json_response(
        dashboard_server,
        "/api/config",
        token=dashboard_server["token"],
    )
    assert status == 200
    status, toggled, _headers = _json_response(
        dashboard_server,
        "/api/agents/toggle",
        method="POST",
        body={
            "slug": "agent-1000",
            "enabled": False,
            "confirm": "DISABLE agent-1000",
            "expected_revision": config["revision"],
        },
        token=dashboard_server["token"],
    )
    assert status == 200, toggled
    assert toggled["changed"] is True

    status, lookup, _headers = _json_response(
        dashboard_server,
        "/api/agents/lookup?slug=agent-1000",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert lookup["agents"][0]["enabled"] is False
    assert lookup["disabled_count"] == 1


@pytest.mark.parametrize(
    "path",
    [
        "/api/roster?after=%3Cscript%3E",
        "/api/roster?after=Security-Reviewer",
        "/api/roster?after=alpha&after=bravo",
    ],
)
def test_dashboard_roster_rejects_hostile_or_ambiguous_cursors(dashboard_server, path):
    status, payload, _headers = _json_response(
        dashboard_server,
        path,
        token=dashboard_server["token"],
    )
    assert status == 400
    assert "cursor" in payload["error"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/agents/lookup",
        "/api/agents/lookup?slug=alpha&slug=bravo",
        "/api/agents/lookup?slug=Security-Reviewer",
        "/api/agents/lookup?slug=%3Cscript%3E",
        "/api/agents/lookup?slug=alpha&one=1&two=2&three=3&four=4",
    ],
)
def test_dashboard_exact_lookup_rejects_noncanonical_queries(dashboard_server, path):
    status, _payload, _headers = _json_response(
        dashboard_server,
        path,
        token=dashboard_server["token"],
    )
    assert status == 400


def test_dashboard_exact_lookup_returns_empty_result_without_leaking_prompt(dashboard_server):
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/agents/lookup?slug=missing-agent",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert payload["agents"] == []
    assert payload["count"] == 0
    assert payload["filter_slug"] == "missing-agent"
    assert "content" not in _nested_keys(payload)


def test_dashboard_exact_lookup_treats_imported_manager_as_optional(dashboard_server):
    dashboard_server["store"]._activate_prevalidated_agent(
        next(agent for agent in bundled_roster() if agent["slug"] == "chief-of-staff")
    )
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/agents/lookup?slug=chief-of-staff",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert payload["agents"][0]["enabled"] is True
    assert payload["agents"][0]["protected"] is False


def test_dashboard_config_get_reports_redacted_revision_and_target(dashboard_server):
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/config",
        token=dashboard_server["token"],
    )

    assert status == 200
    assert payload["revision"].startswith("sha256:")
    assert payload["path"].endswith("missing.yaml")
    assert payload["effective"]["dashboard"]["port"] == 7810
    assert payload["environment_overrides"]["judge.timeout"] == "AGENCY_JUDGE_TIMEOUT"
    assert all(isinstance(value, bool) for value in payload["secret_presence"].values())


def test_dashboard_agent_toggle_is_authenticated_reversible_and_protected(dashboard_server):
    status, initial, _headers = _json_response(
        dashboard_server,
        "/api/config",
        token=dashboard_server["token"],
    )
    request = {
        "slug": "security-reviewer",
        "enabled": False,
        "confirm": "DISABLE security-reviewer",
        "expected_revision": initial["revision"],
    }
    assert (
        _json_response(
            dashboard_server,
            "/api/agents/toggle",
            method="POST",
            body=request,
        )[0]
        == 401
    )

    status, unchanged, _headers = _json_response(
        dashboard_server,
        "/api/agents/toggle",
        method="POST",
        body={
            **request,
            "enabled": True,
            "confirm": "ENABLE security-reviewer",
        },
        token=dashboard_server["token"],
    )
    assert status == 200
    assert unchanged["changed"] is False

    status, disabled, _headers = _json_response(
        dashboard_server,
        "/api/agents/toggle",
        method="POST",
        body=request,
        token=dashboard_server["token"],
    )
    assert status == 200
    assert disabled["changed"] is True
    assert disabled["config"]["effective"]["agents"]["disabled"] == ["security-reviewer"]
    status, roster, _headers = _json_response(
        dashboard_server,
        "/api/roster",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert roster["agents"][0]["enabled"] is False
    assert roster["agents"][0]["protected"] is False
    assert roster["total_count"] == 1
    assert roster["enabled_count"] == 0
    assert roster["disabled_count"] == 1
    assert dashboard_server["store"].get_roster_entry("security-reviewer") is not None

    status, conflict, _headers = _json_response(
        dashboard_server,
        "/api/agents/toggle",
        method="POST",
        body={**request, "expected_revision": initial["revision"]},
        token=dashboard_server["token"],
    )
    assert status == 409
    assert "configuration changed" in conflict["error"]

    request.update(
        {
            "enabled": True,
            "confirm": "ENABLE security-reviewer",
            "expected_revision": disabled["config"]["revision"],
        }
    )
    status, enabled, _headers = _json_response(
        dashboard_server,
        "/api/agents/toggle",
        method="POST",
        body=request,
        token=dashboard_server["token"],
    )
    assert status == 200
    assert enabled["config"]["effective"]["agents"]["disabled"] == []

    status, rejected, _headers = _json_response(
        dashboard_server,
        "/api/agents/toggle",
        method="POST",
        body={
            "slug": "agency-steward",
            "enabled": False,
            "confirm": "DISABLE agency-steward",
            "expected_revision": enabled["config"]["revision"],
        },
        token=dashboard_server["token"],
    )
    assert status == 400
    assert "protected coordinator" in rejected["error"]

    current_request = {
        **request,
        "expected_revision": enabled["config"]["revision"],
    }
    for invalid_body, expected_error in (
        ({**current_request, "slug": "not valid"}, "lowercase letters"),
        ({**current_request, "enabled": "false"}, "JSON boolean"),
        ({**current_request, "slug": "missing-agent"}, "not present"),
        ({**current_request, "confirm": "wrong"}, "confirmation phrase"),
    ):
        status, rejected, _headers = _json_response(
            dashboard_server,
            "/api/agents/toggle",
            method="POST",
            body=invalid_body,
            token=dashboard_server["token"],
        )
        assert status == 400
        assert expected_error in rejected["error"]


def test_dashboard_config_write_requires_confirmation_and_is_atomic(dashboard_server):
    status, initial, _headers = _json_response(
        dashboard_server,
        "/api/config",
        token=dashboard_server["token"],
    )
    body = {
        "expected_revision": initial["revision"],
        "operations": [
            {
                "op": "set",
                "path": "observability.retention_days",
                "value": 45,
            }
        ],
        "confirmations": [],
    }
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/config",
        method="POST",
        body=body,
        token=dashboard_server["token"],
    )
    assert status == 400
    assert payload == {"error": "missing confirmation phrase: SAVE CONFIG"}
    assert not Path(initial["path"]).exists()

    body["confirmations"] = ["SAVE CONFIG"]
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/config",
        method="POST",
        body=body,
        token=dashboard_server["token"],
    )
    assert status == 200
    assert payload["effective"]["observability"]["retention_days"] == 45
    assert payload["changed_paths"] == ["observability.retention_days"]
    assert yaml.safe_load(Path(initial["path"]).read_text(encoding="utf-8")) == {
        "observability": {"retention_days": 45}
    }


def test_concurrent_dashboards_keep_custom_config_reads_isolated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    poison_path = tmp_path / "process-default.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(poison_path))
    paths = [tmp_path / "first.yaml", tmp_path / "second.yaml"]
    for index, path in enumerate(paths):
        path.write_text(
            yaml.safe_dump({"observability": {"retention_days": 41 + index}}),
            encoding="utf-8",
        )
    tokens = ["first-token", "second-token"]
    servers: list[DashboardHTTPServer] = []
    threads: list[threading.Thread] = []
    clients: list[dict[str, object]] = []
    try:
        for index, (path, token) in enumerate(zip(paths, tokens, strict=True)):
            store = Store(tmp_path / f"dashboard-{index}.db", config_path=path)
            server = DashboardHTTPServer(
                store,
                auth_token=token,
                port=0,
                host_inspector=lambda: [],
                config_path=path,
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            servers.append(server)
            threads.append(thread)
            clients.append(
                {
                    "base": f"http://127.0.0.1:{server.server_address[1]}",
                    "token": token,
                }
            )

        def read(index: int) -> tuple[int, dict]:
            client = clients[index]
            token = str(client["token"])
            status, payload, _headers = _json_response(
                client,
                "/api/config",
                token=token,
            )
            return status, payload

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(read, range(2)))

        assert [status for status, _payload in results] == [200, 200]
        assert [
            payload["effective"]["observability"]["retention_days"] for _status, payload in results
        ] == [41, 42]
        assert [yaml.safe_load(path.read_text(encoding="utf-8")) for path in paths] == [
            {"observability": {"retention_days": 41}},
            {"observability": {"retention_days": 42}},
        ]
        assert not poison_path.exists()
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=2)


def test_dashboard_server_rejects_store_config_identity_mismatch(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db", config_path=tmp_path / "store.yaml")

    with pytest.raises(ValueError, match="Store and configuration paths must match"):
        DashboardHTTPServer(
            store,
            auth_token="token",
            config_path=tmp_path / "server.yaml",
        )


def test_dashboard_server_inherits_an_existing_store_config_identity(tmp_path: Path) -> None:
    config_path = tmp_path / "store.yaml"
    store = Store(tmp_path / "agency.db", config_path=config_path)

    server = DashboardHTTPServer(store, auth_token="token")
    try:
        assert server.config_path == config_path.resolve()
        assert store.config_path == server.config_path
    finally:
        server.server_close()


def test_dashboard_server_rejects_a_store_without_config_identity(tmp_path: Path) -> None:
    store = Store.__new__(Store)
    store.config_path = None

    with pytest.raises(ValueError, match="must have a configuration identity"):
        DashboardHTTPServer(store, auth_token="token")


def test_dashboard_config_stale_revision_returns_conflict(dashboard_server):
    status, initial, _headers = _json_response(
        dashboard_server,
        "/api/config",
        token=dashboard_server["token"],
    )
    body = {
        "expected_revision": initial["revision"],
        "operations": [{"op": "set", "path": "dashboard.port", "value": 8123}],
        "confirmations": ["SAVE CONFIG"],
    }
    assert (
        _json_response(
            dashboard_server,
            "/api/config",
            method="POST",
            body=body,
            token=dashboard_server["token"],
        )[0]
        == 200
    )

    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/config",
        method="POST",
        body=body,
        token=dashboard_server["token"],
    )
    assert status == 409
    assert payload == {"error": "configuration changed; refresh before saving"}


def test_dashboard_config_secret_is_write_only(dashboard_server):
    status, initial, _headers = _json_response(
        dashboard_server,
        "/api/config",
        token=dashboard_server["token"],
    )
    secret = "dashboard-secret-value"
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/config",
        method="POST",
        body={
            "expected_revision": initial["revision"],
            "operations": [
                {
                    "op": "secret",
                    "path": "judge.api_key",
                    "action": "replace",
                    "value": secret,
                }
            ],
            "confirmations": ["SAVE CONFIG", "SAVE SENSITIVE CONFIG"],
        },
        token=dashboard_server["token"],
    )

    assert status == 200
    assert secret not in json.dumps(payload)
    assert payload["secret_presence"]["judge.api_key"] is True
    assert payload["effective"]["judge"]["api_key"] == "***REDACTED***"


def test_dashboard_server_host_loads_and_saves_through_shared_boundary(
    dashboard_server,
):
    status, initial, _headers = _json_response(
        dashboard_server,
        "/api/config",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert initial["effective"]["server"]["host"] == "127.0.0.1"

    secret = "server-host-redaction-sentinel"
    status, seeded, _headers = _json_response(
        dashboard_server,
        "/api/config",
        method="POST",
        body={
            "expected_revision": initial["revision"],
            "operations": [
                {
                    "op": "secret",
                    "path": "judge.api_key",
                    "action": "replace",
                    "value": secret,
                }
            ],
            "confirmations": ["SAVE CONFIG", "SAVE SENSITIVE CONFIG"],
        },
        token=dashboard_server["token"],
    )
    assert status == 200

    status, saved, _headers = _json_response(
        dashboard_server,
        "/api/config",
        method="POST",
        body={
            "expected_revision": seeded["revision"],
            "operations": [{"op": "set", "path": "server.host", "value": "localhost"}],
            # A loopback host uses the ordinary config confirmation; no broader
            # network binding is available through the shared validator.
            "confirmations": ["SAVE CONFIG"],
        },
        token=dashboard_server["token"],
    )

    assert status == 200
    assert saved["effective"]["server"]["host"] == "localhost"
    assert saved["persisted"]["server"]["host"] == "localhost"
    assert saved["changed_paths"] == ["server.host"]
    assert saved["restart_required_paths"] == ["server.host"]
    assert saved["effective"]["judge"]["api_key"] == "***REDACTED***"
    assert secret not in json.dumps(saved)

    status, reloaded, _headers = _json_response(
        dashboard_server,
        "/api/config",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert reloaded["effective"]["server"]["host"] == "localhost"
    assert reloaded["persisted"]["server"]["host"] == "localhost"
    assert reloaded["effective"]["judge"]["api_key"] == "***REDACTED***"
    assert secret not in json.dumps(reloaded)


def test_dashboard_server_host_rejects_non_loopback_binding(dashboard_server):
    status, initial, _headers = _json_response(
        dashboard_server,
        "/api/config",
        token=dashboard_server["token"],
    )
    assert status == 200

    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/config",
        method="POST",
        body={
            "expected_revision": initial["revision"],
            "operations": [{"op": "set", "path": "server.host", "value": "0.0.0.0"}],
            "confirmations": ["SAVE CONFIG"],
        },
        token=dashboard_server["token"],
    )

    assert status == 400
    assert payload == {"error": "server.host: must be a loopback host"}
    assert not Path(initial["path"]).exists()


@pytest.mark.parametrize(
    ("path", "value", "required"),
    [
        ("profile", "local-only", "APPLY LOCAL-ONLY PROFILE"),
        ("profile", " LOCAL-ONLY ", "APPLY LOCAL-ONLY PROFILE"),
        (
            "observability.capture_content",
            True,
            "ENABLE CONTENT CAPTURE",
        ),
    ],
)
def test_dashboard_config_sensitive_policy_changes_require_specific_phrase(
    dashboard_server,
    path,
    value,
    required,
):
    status, initial, _headers = _json_response(
        dashboard_server,
        "/api/config",
        token=dashboard_server["token"],
    )
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/config",
        method="POST",
        body={
            "expected_revision": initial["revision"],
            "operations": [{"op": "set", "path": path, "value": value}],
            "confirmations": ["SAVE CONFIG"],
        },
        token=dashboard_server["token"],
    )

    assert status == 400
    assert payload == {"error": f"missing confirmation phrase: {required}"}


def test_dashboard_overview_and_activity_are_metadata_only(dashboard_server, monkeypatch):
    dashboard_server["store"].record_specialist_loaded(
        "session-dashboard",
        "security-reviewer",
        trace_id="trace-dashboard",
    )

    def fail_if_materialized(*_args, **_kwargs):
        raise AssertionError("overview must not materialize roster rows")

    monkeypatch.setattr(dashboard_server["store"], "get_active_roster", fail_if_materialized)
    status, overview, _headers = _json_response(
        dashboard_server,
        "/api/overview",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert overview["status"] == "ok"
    assert overview["roster_count"] == 1
    assert overview["capture_content"] is False
    assert overview["retention_days"] == 30

    status, activity, _headers = _json_response(
        dashboard_server,
        "/api/activity",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert activity["delegations"][0]["recommended_agent"] == "security-reviewer"
    assert activity["specialists"][0] == {
        "id": activity["specialists"][0]["id"],
        "session_id": "session-dashboard",
        "trace_id": "trace-dashboard",
        "slug": "security-reviewer",
        "loaded_at": activity["specialists"][0]["loaded_at"],
        "expired_at": None,
        "state": "current",
    }
    assert all("user_message" not in row for row in activity["runs"])
    assert all("stdout" not in row and "stderr" not in row for row in activity.get("workers", []))


@pytest.mark.skip(reason="ADR-0087: needs full inference nomination-delivery flow")
def test_dashboard_route_lab_returns_explain_receipt(dashboard_server):
    task = "1. Review application security design\n2. Audit threat boundaries"
    for _attempt in range(2):
        status, payload, _headers = _json_response(
            dashboard_server,
            "/api/route",
            method="POST",
            body={
                "task": task,
                "session_id": "dashboard-test",
            },
            token=dashboard_server["token"],
        )

    assert status == 200
    assert payload["schema_version"] == "agency.selection_explain.v1"
    assert payload["task"] == task
    assert payload["host_capability_receipt"]["source"] == "native-installation-evidence"
    assert payload["host_capability_receipt"]["execution_host"] == "codex"
    eligibility = payload["eligibility"]
    assert eligibility["execution_host"] == "codex"
    assert eligibility["capability_status"] == "native-installation-verified"
    assert eligibility["eligible_count"] >= 1
    assert eligibility["rejection_count"] == len(eligibility["rejections"])
    assert eligibility["truncated"] is False
    assert eligibility["host_resolution"] == "derived"
    assert payload["routing"]["execution_context"]["execution_host"] == "codex"
    assert payload["delegation_graph"]["nodes"]
    assert [item["description"] for item in payload["delegation_graph"]["nodes"]] == payload[
        "signals"
    ]["work_units"]["units"]
    plan = payload["delegation_plan"]
    assert plan["schema_version"] == "agency.dashboard.delegation_plan.v1"
    assert plan["authority"] == "recommendation_only"
    assert plan["execution_host"] == "codex"
    assert "spawn_agent" in plan["mechanism"]
    assert "not execution" in plan["evidence_contract"]
    assert plan["unit_count"] == len(plan["units"]) > 0, json.dumps(payload["routing"])
    assert all(item["recommended_agent"] == "security-reviewer" for item in plan["units"])
    assert all(item["compatible_specialists"] == ["security-reviewer"] for item in plan["units"])
    assert all(
        item["assignment_strength"] in {"optional", "preferred", "strongly_preferred"}
        for item in plan["units"]
    )
    assert all("required_evidence" in item for item in plan["units"])
    assert "prompt_body" not in _nested_keys(plan)
    assert "decision_id" not in payload["routing"]
    assert dashboard_server["store"].get_open_traces_for_session("dashboard-test") == []


def test_route_lab_host_capability_is_derived_only_from_verified_inventory(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "route-host.db")
    codex = _verified_codex_record()

    host, receipt = dashboard_module._route_lab_host_capability(
        store,
        lambda: [codex],
        requested_host=None,
        global_enabled=True,
    )

    assert host == "codex"
    assert receipt["source"] == "native-installation-evidence"
    assert receipt["status"] == "native-installation-verified"
    assert receipt["execution_host"] == "codex"
    assert receipt["capabilities"]

    claude = {**codex, "host": "claude"}
    with pytest.raises(ValueError, match="multiple verified execution hosts"):
        dashboard_module._route_lab_host_capability(
            store,
            lambda: [codex, claude],
            requested_host=None,
            global_enabled=True,
        )
    selected, selected_receipt = dashboard_module._route_lab_host_capability(
        store,
        lambda: [codex, claude],
        requested_host=" CLAUDE ",
        global_enabled=True,
    )
    assert selected == "claude"
    assert selected_receipt["execution_host"] == "claude"


@pytest.mark.parametrize("requested_host", [True, "attacker", ""])
def test_route_lab_host_capability_rejects_invalid_host_input(
    tmp_path: Path,
    requested_host: object,
) -> None:
    store = Store(tmp_path / f"invalid-route-host-{requested_host!s}.db")
    with pytest.raises(ValueError, match="host must be"):
        dashboard_module._route_lab_host_capability(
            store,
            lambda: [_verified_codex_record()],
            requested_host=requested_host,
            global_enabled=True,
        )


def test_route_lab_host_capability_rejects_unproven_duplicate_and_unbounded_inventory(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "unproven-route-host.db")
    incomplete = {
        "host": "codex",
        "executable_discovered": True,
        "registered": True,
        "enabled": True,
    }
    with pytest.raises(ValueError, match="unproven:managed_bundle"):
        dashboard_module._route_lab_host_capability(
            store,
            lambda: [incomplete],
            requested_host="codex",
            global_enabled=True,
        )
    with pytest.raises(ValueError, match="inventory is ambiguous"):
        dashboard_module._route_lab_host_capability(
            store,
            lambda: [_verified_codex_record(), _verified_codex_record()],
            requested_host="codex",
            global_enabled=True,
        )
    with pytest.raises(RuntimeError, match="invalid inventory"):
        dashboard_module._route_lab_host_capability(
            store,
            lambda: (),  # type: ignore[arg-type,return-value]
            requested_host=None,
            global_enabled=True,
        )
    with pytest.raises(RuntimeError, match="inventory bound"):
        dashboard_module._route_lab_host_capability(
            store,
            lambda: [
                {"host": f"unknown-{index}"}
                for index in range(dashboard_module._ROUTE_LAB_HOST_INVENTORY_LIMIT + 1)
            ],
            requested_host=None,
            global_enabled=True,
        )


@pytest.mark.parametrize(
    ("inspection_status", "message"),
    [
        ("timed_out", "inspection is still pending; retry shortly"),
        ("stale", "evidence expired while refresh is pending; retry shortly"),
        ("error", "inspection failed; check dashboard service diagnostics"),
    ],
)
def test_route_lab_host_capability_surfaces_transient_inspection_state(
    tmp_path: Path,
    inspection_status: str,
    message: str,
) -> None:
    store = Store(tmp_path / f"transient-route-host-{inspection_status}.db")

    with pytest.raises(ValueError, match=message):
        dashboard_module._route_lab_host_capability(
            store,
            lambda: [
                {
                    "host": "codex",
                    "inspection_status": inspection_status,
                    "registered": None,
                    "enabled": None,
                }
            ],
            requested_host="codex",
            global_enabled=True,
        )


def test_route_lab_eligibility_projection_is_bounded_and_content_safe() -> None:
    raw = [
        {"slug": f"agent-{index}", "reason": f"missing-capability-{index}"}
        for index in range(dashboard_module._ROUTE_LAB_REJECTION_LIMIT + 2)
    ]
    projection = dashboard_module._route_lab_eligibility_projection(
        {"routing": {"eligibility_rejections": raw}},
        {
            "execution_host": "codex",
            "status": "native-installation-verified",
        },
        catalog_size=100,
    )

    assert projection["execution_host"] == "codex"
    assert projection["eligible_count"] == 48
    assert projection["rejection_count"] == 52
    assert len(projection["rejections"]) == dashboard_module._ROUTE_LAB_REJECTION_LIMIT
    assert projection["truncated"] is True

    assert (
        dashboard_module._route_lab_eligibility_projection(
            {"routing": {"eligibility_rejections": "invalid"}},
            {"execution_host": "codex", "status": "native-installation-verified"},
            catalog_size=1,
        )["rejections"]
        == []
    )


@pytest.mark.parametrize(
    ("host", "message"),
    [("attacker", "host must be one of"), ("claude", "cannot use claude")],
)
def test_dashboard_route_lab_rejects_unsupported_or_unproven_host(
    dashboard_server,
    host: str,
    message: str,
) -> None:
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/route",
        method="POST",
        body={"task": "review this design", "host": host},
        token=dashboard_server["token"],
    )

    assert status == 400
    assert message in payload["error"]


@pytest.mark.skip(reason="ADR-0087: needs full inference nomination-delivery flow")
def test_dashboard_route_lab_uses_authoritative_dependency_graph(dashboard_server):
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/route",
        method="POST",
        body={
            "task": "1. Implement the API\n2. After the API is complete, test the endpoint",
            "session_id": "dashboard-graph",
        },
        token=dashboard_server["token"],
    )

    assert status == 200
    graph = payload["delegation_graph"]
    assert len(graph["nodes"]) == 4
    assert {(edge["from"], edge["to"], edge["reason"]) for edge in graph["edges"]} == {
        (graph["nodes"][0]["id"], graph["nodes"][1]["id"], "explicit depends_on"),
        (graph["nodes"][1]["id"], graph["nodes"][2]["id"], "explicit depends_on"),
        (graph["nodes"][1]["id"], graph["nodes"][3]["id"], "explicit depends_on"),
    }


@pytest.mark.skip(reason="ADR-0087: needs full inference nomination-delivery flow")
def test_dashboard_route_lab_orders_inline_then_sequence(dashboard_server):
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/route",
        method="POST",
        body={
            "task": "Review the authentication design, then document the deployment workflow.",
            "session_id": "dashboard-inline-graph",
        },
        token=dashboard_server["token"],
    )

    assert status == 200
    graph = payload["delegation_graph"]
    assert len(graph["nodes"]) == 2
    assert "review-report during review" in graph["nodes"][0]["description"]
    assert "documentation during documentation" in graph["nodes"][1]["description"]
    assert graph["edges"] == [
        {
            "from": graph["nodes"][0]["id"],
            "to": graph["nodes"][1]["id"],
            "reason": "explicit depends_on",
        }
    ]


def test_dashboard_trim_requires_exact_confirmation(dashboard_server):
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/maintenance/trim",
        method="POST",
        body={"confirm": "yes", "older_than_days": 30},
        token=dashboard_server["token"],
    )
    assert status == 400
    assert "TRIM RUNTIME DATA" in payload["error"]

    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/maintenance/trim",
        method="POST",
        body={"confirm": "TRIM RUNTIME DATA", "older_than_days": 30, "dry_run": True},
        token=dashboard_server["token"],
    )
    assert status == 200
    assert payload["dry_run"] is True


@pytest.mark.parametrize("days", [0, -1, 3651, None, "30", True])
def test_dashboard_trim_rejects_invalid_retention_days(
    dashboard_server,
    monkeypatch: pytest.MonkeyPatch,
    days,
):
    called = False

    def unexpected_trim(_store, **_kwargs):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(Store, "trim_runtime_tables", unexpected_trim)
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/maintenance/trim",
        method="POST",
        body={"confirm": "TRIM RUNTIME DATA", "older_than_days": days},
        token=dashboard_server["token"],
    )

    assert status == 400
    assert "integer from 1 through 3650" in payload["error"]
    assert called is False


@pytest.mark.parametrize(
    ("field", "value"),
    [("dry_run", 0), ("dry_run", "false"), ("vacuum", 1), ("vacuum", None)],
)
def test_dashboard_trim_requires_json_booleans(
    dashboard_server,
    monkeypatch: pytest.MonkeyPatch,
    field,
    value,
):
    called = False

    def unexpected_trim(_store, **_kwargs):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(Store, "trim_runtime_tables", unexpected_trim)
    body = {"confirm": "TRIM RUNTIME DATA", "older_than_days": 30, field: value}
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/maintenance/trim",
        method="POST",
        body=body,
        token=dashboard_server["token"],
    )

    assert status == 400
    assert f"{field} must be a JSON boolean" == payload["error"]
    assert called is False


def test_dashboard_server_refuses_non_loopback_binding(tmp_path: Path):
    store = Store(tmp_path / "dashboard.db")

    with pytest.raises(ValueError, match="loopback-only"):
        DashboardHTTPServer(store, auth_token="token", host="0.0.0.0", port=0)


def test_dashboard_host_api_preserves_unknown_boolean_states(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "missing.yaml"))
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "dashboard.db"))
    store = Store(tmp_path / "dashboard.db")
    token = "token"
    unknown = {
        "host": "codex",
        "registered": None,
        "enabled": None,
        "executable_discovered": True,
        "maturity": "host-registration-unverified",
    }
    server = DashboardHTTPServer(
        store,
        auth_token=token,
        port=0,
        host_inspector=lambda: [unknown],
        runtime_control_home=tmp_path,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    wrapped = {"base": f"http://127.0.0.1:{server.server_address[1]}", "token": token}
    try:
        status, payload, _headers = _json_response(wrapped, "/api/hosts", token=token)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 200
    assert payload["hosts"][0]["registered"] is None
    assert payload["hosts"][0]["enabled"] is None


def test_dashboard_host_api_preserves_content_free_activation_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "missing.yaml"))
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "dashboard.db"))
    store = Store(tmp_path / "dashboard.db")
    token = "token"
    attestation = {
        "proof_contract": "agency.codex-activation-canary.v1",
        "proof_digest": "a" * 64,
        "profile_scope": "current-profile",
        "passed_at": "2026-07-27T12:34:56Z",
        "trace_id": "trace-activation",
    }
    server = DashboardHTTPServer(
        store,
        auth_token=token,
        port=0,
        host_inspector=lambda: [
            {
                "host": "codex",
                "registered": True,
                "enabled": True,
                "canary": True,
                "canary_attestation_status": "verified",
                "canary_attestation": attestation,
            }
        ],
        runtime_control_home=tmp_path,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    wrapped = {"base": f"http://127.0.0.1:{server.server_address[1]}", "token": token}
    try:
        status, payload, _headers = _json_response(wrapped, "/api/hosts", token=token)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 200
    host = payload["hosts"][0]
    assert host["canary"] is True
    assert host["canary_attestation_status"] == "verified"
    assert host["canary_attestation"] == attestation


def test_dashboard_host_api_isolates_unrecognized_host_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """L2-06: one malformed host inspection record (a label normalize_host
    rejects) must degrade to a placeholder, not fail the whole /api/hosts
    payload with a 500."""
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "missing.yaml"))
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "dashboard.db"))
    store = Store(tmp_path / "dashboard.db")
    token = "token"
    records = [
        {"host": "codex", "registered": True, "enabled": True},
        {"host": "future-host-label", "registered": None, "enabled": None},
    ]
    server = DashboardHTTPServer(
        store,
        auth_token=token,
        port=0,
        host_inspector=lambda: records,
        runtime_control_home=tmp_path,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    wrapped = {"base": f"http://127.0.0.1:{server.server_address[1]}", "token": token}
    try:
        status, payload, _headers = _json_response(wrapped, "/api/hosts", token=token)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 200
    hosts = payload["hosts"]
    assert len(hosts) == 2
    # The valid host inspects normally.
    assert hosts[0]["host"] == "codex"
    # The unrecognized label is isolated to a placeholder, not a 500.
    assert hosts[1]["host"] == "future-host-label"
    assert hosts[1]["error"] == "unrecognized host label"


def test_dashboard_host_snapshot_reads_one_master_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    import agency_runtime.core.host_control as host_control

    master = {
        "schema_version": 1,
        "enabled": False,
        "generation": 9,
        "updated_at": "2026-07-16T12:00:00Z",
        "source": "test",
    }
    reads = 0
    observed: list[tuple[str, bool | None]] = []

    def read_master() -> dict:
        nonlocal reads
        reads += 1
        return master

    def inspect(_store, host: str, *, native_record, global_enabled=None):
        assert native_record["host"] == host
        observed.append((host, global_enabled))
        return {"host": host, "master_enabled": global_enabled}

    store_path = (Path.cwd() / "host-snapshot.db").resolve()
    config_path = (Path.cwd() / "host-snapshot.yaml").resolve()
    state = SimpleNamespace(
        path=str(config_path),
        revision="sha256:" + ("a" * 64),
        effective={"store": {"db_path": str(store_path)}},
        environment_overrides={},
    )
    monkeypatch.setattr(host_control, "inspect_host_status", inspect)
    monkeypatch.setattr(dashboard_module, "read_config_state", lambda _path: state)
    handler = object.__new__(dashboard_module.DashboardHTTPHandler)
    handler.server = SimpleNamespace(
        store=SimpleNamespace(db_path=store_path),
        config_path=config_path,
        host_inspector=lambda: [{"host": "codex"}, {"host": "claude"}],
    )
    handler._master_control = read_master
    payloads: list[dict] = []
    handler._json_ok = payloads.append

    handler._handle_hosts()

    assert reads == 1
    assert observed == [("codex", False), ("claude", False)]
    assert payloads == [
        {
            "hosts": [
                {"host": "codex", "master_enabled": False},
                {"host": "claude", "master_enabled": False},
            ],
            "master": master,
            "config_path": str(config_path),
            "config_revision": state.revision,
            "environment_overrides": {},
            "store_path": str(store_path),
            "desired_store_path": str(store_path),
            "store_restart_required": False,
        }
    ]


def test_dashboard_master_control_uses_strict_service_boundary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The authenticated broker must not enter the sandbox-only reader path."""

    from types import SimpleNamespace

    target = tmp_path / "control.json"
    expected = {
        "schema_version": 1,
        "enabled": True,
        "generation": 7,
        "updated_at": "2026-07-18T00:00:00Z",
        "source": "dashboard",
    }
    calls: list[tuple[Path, bool]] = []

    def strict_reader(*, path: Path, use_cache: bool = True) -> dict[str, object]:
        calls.append((path, use_cache))
        return expected

    monkeypatch.setattr(dashboard_module, "read_runtime_control", strict_reader)
    handler = object.__new__(dashboard_module.DashboardHTTPHandler)
    handler.server = SimpleNamespace(runtime_control_path=target)

    assert handler._master_control() == expected
    assert calls == [(target, True)]


def test_dashboard_runtime_endpoint_reads_master_uncached(
    dashboard_server,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.runtime_control import runtime_control_path

    expected = {
        "schema_version": 1,
        "enabled": True,
        "generation": 8,
        "updated_at": "2026-07-28T00:00:00Z",
        "source": "dashboard",
    }
    calls: list[tuple[Path, bool]] = []

    def strict_reader(*, path: Path, use_cache: bool = True) -> dict[str, object]:
        calls.append((path, use_cache))
        return expected

    monkeypatch.setattr(dashboard_module, "read_runtime_control", strict_reader)

    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/runtime",
        token=dashboard_server["token"],
    )

    assert status == 200
    assert payload == {"master": expected}
    assert calls == [(runtime_control_path(home_dir=dashboard_server["home"]), False)]


@pytest.mark.parametrize("enabled", [None, 0, 1, "false", [], {}])
def test_dashboard_host_toggle_requires_json_boolean(dashboard_server, enabled):
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/hosts/toggle",
        method="POST",
        body={
            "host": "codex",
            "enabled": enabled,
            "expected_generation": 0,
            "confirm": "DISABLE codex",
        },
        token=dashboard_server["token"],
    )

    assert status == 400
    assert payload == {"error": "enabled must be a JSON boolean"}


def test_dashboard_host_toggle_validates_host_before_confirmation(
    dashboard_server, monkeypatch: pytest.MonkeyPatch
):
    called = False

    def unexpected_toggle(*args, **kwargs):
        nonlocal called
        called = True
        return {"ok": True}

    monkeypatch.setattr("agency_runtime.core.host_control.set_runtime_control", unexpected_toggle)
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/hosts/toggle",
        method="POST",
        body={
            "host": "attacker",
            "enabled": True,
            "expected_generation": 0,
            "confirm": "ENABLE attacker",
        },
        token=dashboard_server["token"],
    )

    assert status == 400
    assert payload == {"error": "unknown host: attacker"}
    assert called is False


def test_dashboard_host_toggle_persists_soft_control_without_native_mutation(
    dashboard_server,
    monkeypatch: pytest.MonkeyPatch,
):
    invalidated: list[str] = []
    monkeypatch.setattr(
        dashboard_module._HOST_INSPECTIONS,
        "invalidate",
        invalidated.append,
    )

    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/hosts/toggle",
        method="POST",
        body={
            "host": "codex",
            "enabled": False,
            "expected_generation": 0,
            "confirm": "DISABLE codex",
        },
        token=dashboard_server["token"],
    )

    assert status == 200
    assert payload["ok"] is True
    assert payload["enabled"] is False
    assert dashboard_server["store"].get_host_control("codex")["enabled"] is False
    assert invalidated == []


def test_dashboard_host_toggle_rejects_a_stale_client_generation(dashboard_server) -> None:
    first_status, first, _headers = _json_response(
        dashboard_server,
        "/api/hosts/toggle",
        method="POST",
        body={
            "host": "codex",
            "enabled": False,
            "expected_generation": 0,
            "confirm": "DISABLE codex",
        },
        token=dashboard_server["token"],
    )
    assert first_status == 200
    assert first["generation"] == 1

    stale_status, stale, _headers = _json_response(
        dashboard_server,
        "/api/hosts/toggle",
        method="POST",
        body={
            "host": "codex",
            "enabled": True,
            "expected_generation": 0,
            "confirm": "ENABLE codex",
        },
        token=dashboard_server["token"],
    )
    assert stale_status == 409
    assert "expected 0, found 1" in stale["error"]
    assert dashboard_server["store"].get_host_control("codex")["enabled"] is False

    fresh_status, fresh, _headers = _json_response(
        dashboard_server,
        "/api/hosts/toggle",
        method="POST",
        body={
            "host": "codex",
            "enabled": True,
            "expected_generation": 1,
            "confirm": "ENABLE codex",
        },
        token=dashboard_server["token"],
    )
    assert fresh_status == 200
    assert fresh["generation"] == 2


@pytest.mark.parametrize("generation", [None, True, -1, "0"])
def test_dashboard_host_toggle_requires_a_non_negative_generation(
    dashboard_server,
    generation,
) -> None:
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/hosts/toggle",
        method="POST",
        body={
            "host": "codex",
            "enabled": False,
            "expected_generation": generation,
            "confirm": "DISABLE codex",
        },
        token=dashboard_server["token"],
    )
    assert status == 400
    assert payload == {"error": "expected_generation must be a non-negative integer"}


def test_dashboard_host_toggle_projects_the_server_bound_master_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from types import SimpleNamespace

    from agency_runtime.core import host_control

    observed: list[bool | None] = []

    def inspect(_store, host: str, *, native_record, global_enabled=None):
        observed.append(global_enabled)
        return {
            "host": host,
            "master_enabled": global_enabled,
            "effective_enabled": bool(global_enabled),
        }

    store_path = (tmp_path / "host-toggle.db").resolve()
    config_path = (tmp_path / "host-toggle.yaml").resolve()
    state = SimpleNamespace(
        path=str(config_path),
        revision="sha256:" + ("b" * 64),
        effective={"store": {"db_path": str(store_path)}},
        environment_overrides={},
    )
    monkeypatch.setattr(host_control, "inspect_host_status", inspect)
    monkeypatch.setattr(dashboard_module, "read_config_state", lambda _path: state)
    monkeypatch.setattr(
        host_control,
        "set_runtime_control",
        lambda *_args, **_kwargs: {"enabled": True, "source": "dashboard"},
    )
    handler = object.__new__(dashboard_module.DashboardHTTPHandler)
    handler.server = SimpleNamespace(
        store=SimpleNamespace(db_path=store_path),
        config_path=config_path,
        host_inspector=lambda: [{"host": "codex", "registered": True, "enabled": True}],
    )
    handler._master_control = lambda: {
        "enabled": False,
        "generation": 7,
        "source": "custom-runtime-control-home",
    }
    payloads: list[tuple[int, dict]] = []
    handler._send_json = lambda status, payload: payloads.append((status, payload))

    handler._handle_host_toggle(
        {
            "host": "codex",
            "enabled": True,
            "expected_generation": 0,
            "confirm": "ENABLE codex",
        }
    )

    assert observed == [False]
    assert payloads[0][1]["status"]["effective_enabled"] is False
    assert payloads[0][1]["config_path"] == str(config_path)
    assert payloads[0][1]["store_path"] == str(store_path)


def test_host_inspection_is_parallel_and_returns_partial_unknowns_at_deadline():
    release = threading.Event()
    started: set[str] = set()
    started_lock = threading.Lock()

    def inspect(host: str) -> dict:
        with started_lock:
            started.add(host)
        if host == "slow":
            release.wait(timeout=1)
        return {
            "host": host,
            "registered": True,
            "enabled": False,
            "maturity": "registered-disabled",
        }

    executor = ThreadPoolExecutor(max_workers=2)
    coordinator = _HostInspectionCoordinator(
        inspect_one=inspect,
        hosts=("fast", "slow"),
        deadline_seconds=0.03,
        cache_seconds=1,
        executor=executor,
    )
    started_at = time.monotonic()
    try:
        result = coordinator.inspect()
        elapsed = time.monotonic() - started_at
        by_host = {item["host"]: item for item in result}

        assert started == {"fast", "slow"}
        assert elapsed < 0.2
        assert by_host["fast"]["inspection_status"] == "complete"
        assert by_host["slow"]["registered"] is None
        assert by_host["slow"]["enabled"] is None
        assert by_host["slow"]["inspection_status"] == "timed_out"
    finally:
        release.set()
        executor.shutdown(wait=True)


def test_expired_host_evidence_is_not_actionable_while_refresh_is_pending():
    release = threading.Event()
    calls = 0
    calls_lock = threading.Lock()

    def inspect(host: str) -> dict:
        nonlocal calls
        with calls_lock:
            calls += 1
            call_number = calls
        if call_number > 1:
            release.wait(timeout=1)
        return {
            "host": host,
            "registered": True,
            "enabled": False,
            "maturity": "registered-disabled",
        }

    executor = ThreadPoolExecutor(max_workers=1)
    coordinator = _HostInspectionCoordinator(
        inspect_one=inspect,
        hosts=("codex",),
        deadline_seconds=0.02,
        cache_seconds=0.01,
        executor=executor,
    )
    try:
        assert coordinator.inspect()[0]["inspection_status"] == "complete"
        time.sleep(0.03)
        stale = coordinator.inspect()[0]

        assert stale["inspection_status"] == "stale"
        assert stale["registered"] is None
        assert stale["enabled"] is None
        assert stale["loaded"] is None
        assert stale["canary"] is None
        assert stale["canary_attestation_status"] == "inspection-unavailable"
        assert stale["canary_stale_reasons"] == ["host_inspection"]
        assert stale["maturity"] == "inspection-stale"
    finally:
        release.set()
        executor.shutdown(wait=True)


def test_provider_health_is_explicitly_receipt_based():
    health = _provider_health(
        [
            {
                "resolved_provider": "openai",
                "status": "success",
                "ended_at": "2026-07-11T01:00:00Z",
            },
            {
                "resolved_provider": "openai",
                "status": "failed",
                "ended_at": "2026-07-11T00:00:00Z",
            },
            {"resolved_provider": "", "status": "unknown"},
        ]
    )

    assert health[0] == {
        "provider": "openai",
        "receipt_count": 2,
        "success_count": 1,
        "failure_count": 1,
        "unknown_count": 0,
        "latest_status": "success",
        "latest_at": "2026-07-11T01:00:00Z",
        "evidence": "recent model receipts; not a live provider probe",
    }
    assert health[1]["provider"] == "unresolved"
    assert health[1]["unknown_count"] == 1


@pytest.mark.skipif(not socket.has_ipv6, reason="Python runtime has no IPv6 support")
def test_dashboard_serves_authenticated_requests_on_ipv6_loopback(tmp_path: Path):
    store = Store(
        tmp_path / "dashboard.db",
        config_path=tmp_path / "agency.yaml",
    )
    try:
        server = DashboardHTTPServer(
            store,
            auth_token="ipv6-token",
            host="::1",
            port=0,
            host_inspector=lambda: [],
            runtime_control_home=tmp_path,
        )
    except OSError as exc:
        pytest.skip(f"IPv6 loopback is unavailable: {exc}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # The full Windows suite can briefly delay this new server thread while
    # releasing memory from earlier process-heavy tests. Keep the bound finite
    # without turning scheduler contention into a false IPv6 failure.
    connection = HTTPConnection("::1", int(server.server_address[1]), timeout=5)
    try:
        connection.request(
            "GET",
            "/api/overview",
            headers={
                "Authorization": "Bearer ipv6-token",
                "Host": f"[::1]:{server.server_address[1]}",
            },
        )
        response = connection.getresponse()
        payload = json.loads(response.read())
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert response.status == 200
    assert payload["status"] == "ok"


@pytest.mark.parametrize(
    "exc_cls",
    [
        "RuntimeControlSecurityError",
        "RuntimeControlValidationError",
    ],
)
def test_dashboard_runtime_control_error_does_not_leak_detail_to_client(
    dashboard_server, monkeypatch: pytest.MonkeyPatch, exc_cls
) -> None:
    """L2-05: a RuntimeControlSecurityError / ValidationError carries path and
    trust-contract detail that must not reach the client. The dashboard must
    return a generic 400 without the message and log the type server-side.
    """
    from agency_runtime.core import runtime_control

    exc_type = getattr(runtime_control, exc_cls)

    def raising_reader(*, path, use_cache=True):
        assert use_cache is False
        raise exc_type(
            "control path /home/secret/.agency-runtime/control.json failed "
            "owner-private trust verification: insecure DACL SDDL"
        )

    monkeypatch.setattr(dashboard_module, "read_runtime_control", raising_reader)

    # GET /api/runtime goes through _master_control -> read_runtime_control.
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/runtime",
        token=dashboard_server["token"],
    )

    assert status == 400
    assert payload == {"error": "runtime control unavailable"}
    # The sensitive detail must not appear in the response body.
    body = json.dumps(payload)
    assert "secret" not in body
    assert "DACL" not in body
    assert "trust" not in body
