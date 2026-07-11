"""Security and API tests for the installed local operations dashboard."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from pathlib import Path

import pytest

from agency_runtime.core.store.sqlite import Store
from agency_runtime.server import dashboard as dashboard_module
from agency_runtime.server.dashboard import (
    DashboardHTTPServer,
    _HostInspectionCoordinator,
    _provider_health,
)


@pytest.fixture()
def dashboard_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "missing.yaml"))
    monkeypatch.setenv("AGENCY_JUDGE_TIMEOUT", "0.01")
    from agency_runtime.core.config import reset_config_cache

    reset_config_cache()
    store = Store(tmp_path / "dashboard.db")
    store.activate_agent({
        "slug": "security-reviewer",
        "name": "Security Reviewer",
        "division": "engineering",
        "description": "Reviews application security and threat boundaries.",
        "source": "test",
        "version": "1.0",
        "hash": "security-reviewer-v1",
        "categories": ["security"],
        "capabilities": ["security-review", "threat-modeling"],
        "tool_affinity": ["git"],
        "prompt_path": "",
    })
    store.record_delegation(
        trace_id="trace-dashboard",
        session_id="session-dashboard",
        host="test",
        work_unit_id="unit-1",
        recommended_agent="security-reviewer",
        status="completed",
        backend="test",
    )
    token = "test-dashboard-token"
    server = DashboardHTTPServer(store, auth_token=token, port=0, host_inspector=lambda: [])
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
            "token": token,
            "store": store,
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
) -> tuple[int, bytes, dict[str, str]]:
    headers: dict[str, str] = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if origin is not None:
        headers["Origin"] = origin
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
        return exc.code, exc.read(), dict(exc.headers)


def _json_response(*args, **kwargs) -> tuple[int, dict, dict[str, str]]:
    status, raw, headers = _request(*args, **kwargs)
    return status, json.loads(raw), headers


def test_dashboard_static_shell_is_local_and_hardened(dashboard_server):
    status, raw, headers = _request(dashboard_server, "/")

    assert status == 200
    assert b"Agency Runtime Control Deck" in raw
    assert headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert headers["Cache-Control"] == "no-store"

    status, script, _headers = _request(dashboard_server, "/app.js")
    assert status == 200
    assert b"registration unknown" in script
    assert b"enablement unknown" in script
    assert b"directionKnown" in script
    assert b'inspection_status === "complete"' in script
    assert b"Delegation dependency graph" in script
    assert b"receipt.signals?.work_units?.units" in script
    assert b'["id", "Decision"]' in script
    assert b"hostLocation(host)" in script
    assert b"Number.isInteger(days)" in script
    assert b"await refreshRuntimeEvidence()" in script

    status, stylesheet, _headers = _request(dashboard_server, "/app.css")
    assert status == 200
    assert b"overflow-wrap: anywhere" in stylesheet
    assert b".host-row > div" in stylesheet
    assert b".rail::-webkit-scrollbar" in stylesheet

    assert b'id="provider-health"' in raw
    assert b"not a live provider probe" in raw


def test_dashboard_javascript_parses_when_node_is_available() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable")

    script = Path(__file__).parents[1] / "agency_runtime" / "dashboard" / "app.js"
    completed = subprocess.run(
        [node, "--check", str(script)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr


def test_dashboard_api_requires_per_launch_token(dashboard_server):
    status, payload, _headers = _json_response(dashboard_server, "/api/overview")

    assert status == 401
    assert payload == {"error": "authentication required"}


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


def test_dashboard_overview_and_activity_are_metadata_only(dashboard_server):
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
    assert all("user_message" not in row for row in activity["runs"])
    assert all("stdout" not in row and "stderr" not in row for row in activity.get("workers", []))


def test_dashboard_route_lab_returns_explain_receipt(dashboard_server):
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/route",
        method="POST",
        body={"task": "review this application security design", "session_id": "dashboard-test"},
        token=dashboard_server["token"],
    )

    assert status == 200
    assert payload["schema_version"] == "agency.selection_explain.v1"
    assert payload["task"] == "review this application security design"
    assert payload["selected"]
    assert payload["delegation_graph"]["nodes"]
    assert [item["description"] for item in payload["delegation_graph"]["nodes"]] == payload[
        "signals"
    ]["work_units"]["units"]


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
    assert len(graph["nodes"]) == 2
    assert graph["edges"] == [
        {
            "from": graph["nodes"][0]["id"],
            "to": graph["nodes"][1]["id"],
            "reason": "sequencing language in work-unit description",
        }
    ]


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
    assert [item["description"] for item in graph["nodes"]] == [
        "Review the authentication design",
        "then document the deployment workflow.",
    ]
    assert graph["edges"] == [
        {
            "from": graph["nodes"][0]["id"],
            "to": graph["nodes"][1]["id"],
            "reason": "sequencing language in work-unit description",
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


def test_dashboard_host_api_preserves_unknown_boolean_states(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "missing.yaml"))
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


@pytest.mark.parametrize("enabled", [None, 0, 1, "false", [], {}])
def test_dashboard_host_toggle_requires_json_boolean(dashboard_server, enabled):
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/hosts/toggle",
        method="POST",
        body={"host": "codex", "enabled": enabled, "confirm": "DISABLE codex"},
        token=dashboard_server["token"],
    )

    assert status == 400
    assert payload == {"error": "enabled must be a JSON boolean"}


def test_dashboard_host_toggle_validates_host_before_confirmation(dashboard_server, monkeypatch: pytest.MonkeyPatch):
    called = False

    def unexpected_toggle(*args, **kwargs):
        nonlocal called
        called = True
        return {"ok": True}

    monkeypatch.setattr("agency_runtime.core.installer.toggle_agency", unexpected_toggle)
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/hosts/toggle",
        method="POST",
        body={"host": "attacker", "enabled": True, "confirm": "ENABLE attacker"},
        token=dashboard_server["token"],
    )

    assert status == 400
    assert payload == {"error": "unknown host: attacker"}
    assert called is False


def test_dashboard_host_toggle_invalidates_cached_evidence(
    dashboard_server,
    monkeypatch: pytest.MonkeyPatch,
):
    invalidated: list[str] = []
    monkeypatch.setattr(
        "agency_runtime.core.installer.toggle_agency",
        lambda host, *, enabled: {"ok": True, "host": host, "enabled": enabled},
    )
    monkeypatch.setattr(
        dashboard_module._HOST_INSPECTIONS,
        "invalidate",
        invalidated.append,
    )

    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/hosts/toggle",
        method="POST",
        body={"host": "codex", "enabled": True, "confirm": "ENABLE codex"},
        token=dashboard_server["token"],
    )

    assert status == 200
    assert payload["ok"] is True
    assert invalidated == ["codex"]


def test_host_inspection_is_parallel_and_returns_partial_unknowns_at_deadline():
    release = threading.Event()
    started: set[str] = set()
    started_lock = threading.Lock()

    def inspect(host: str) -> dict:
        with started_lock:
            started.add(host)
        if host == "slow":
            release.wait(timeout=1)
        return {"host": host, "registered": True, "enabled": False, "maturity": "registered-disabled"}

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
    finally:
        release.set()
        executor.shutdown(wait=True)


def test_provider_health_is_explicitly_receipt_based():
    health = _provider_health(
        [
            {"resolved_provider": "openai", "status": "success", "ended_at": "2026-07-11T01:00:00Z"},
            {"resolved_provider": "openai", "status": "failed", "ended_at": "2026-07-11T00:00:00Z"},
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
    store = Store(tmp_path / "dashboard.db")
    try:
        server = DashboardHTTPServer(
            store,
            auth_token="ipv6-token",
            host="::1",
            port=0,
            host_inspector=lambda: [],
        )
    except OSError as exc:
        pytest.skip(f"IPv6 loopback is unavailable: {exc}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = HTTPConnection("::1", int(server.server_address[1]), timeout=2)
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
