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
from datetime import datetime
from http.client import HTTPConnection
from pathlib import Path

import pytest
import yaml

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
    monkeypatch.setenv("AGENCY_JUDGE_TIMEOUT", "0.05")
    from agency_runtime.core.config import reset_config_cache

    reset_config_cache()
    store = Store(tmp_path / "dashboard.db")
    store.activate_agent(
        {
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
            "port": port,
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
        with exc:
            return exc.code, exc.read(), dict(exc.headers)


def _json_response(*args, **kwargs) -> tuple[int, dict, dict[str, str]]:
    status, raw, headers = _request(*args, **kwargs)
    return status, json.loads(raw), headers


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
    assert b"directionKnown" in script
    assert b'inspection_status === "complete"' in script
    assert b"Delegation dependency graph" in script
    assert b"receipt.signals?.work_units?.units" in script
    assert b'["id", "Decision"]' in script
    assert b"hostLocation(host)" in script
    assert b"Number.isInteger(days)" in script
    assert b"await refreshRuntimeEvidence()" in script
    assert b"collectConfigChanges" in script
    assert b"total_count" in script
    assert b"next_cursor" in script
    assert b"/api/config" in script
    assert b"SAVE SENSITIVE CONFIG" in script
    assert b"APPLY LOCAL-ONLY PROFILE" in script
    assert b"requestConfirmation" in script
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
    assert b"overflow-wrap: anywhere" in stylesheet
    assert b".host-row > div" in stylesheet
    assert b".rail::-webkit-scrollbar" in stylesheet
    assert b"prefers-reduced-motion: reduce" in stylesheet
    assert b"forced-colors: active" in stylesheet
    assert b":focus-visible" in stylesheet

    assert b'class="skip-link"' in raw
    assert b'href="#main-content"' in raw
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
        [node, "--test", str(root / "tests" / "dashboard_ui.test.mjs")],
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
        "recent",
    }
    assert set(first["activity"]) == {
        "runs",
        "routing",
        "delegations",
        "receipts",
        "finalizations",
    }
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
    )
    status, changed, _headers = _json_response(
        dashboard_server,
        "/api/live",
        token=dashboard_server["token"],
    )
    assert status == 200
    assert changed["revision"] != first["revision"]


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
    original = Store.recent_dashboard_activity
    calls: list[int] = []

    def counted(self: Store, *, limit: int = 50):
        calls.append(limit)
        return original(self, limit=limit)

    monkeypatch.setattr(Store, "recent_dashboard_activity", counted)

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
    for slug in ("alpha-reviewer", "zulu-reviewer"):
        dashboard_server["store"].activate_agent(
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
    assert all("user_message" not in row for row in activity["runs"])
    assert all("stdout" not in row and "stderr" not in row for row in activity.get("workers", []))


def test_dashboard_route_lab_returns_explain_receipt(dashboard_server):
    status, payload, _headers = _json_response(
        dashboard_server,
        "/api/route",
        method="POST",
        body={
            "task": "review this application security design",
            "session_id": "dashboard-test",
        },
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


def test_dashboard_host_api_preserves_unknown_boolean_states(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
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
        body={"host": "attacker", "enabled": True, "confirm": "ENABLE attacker"},
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
        body={"host": "codex", "enabled": False, "confirm": "DISABLE codex"},
        token=dashboard_server["token"],
    )

    assert status == 200
    assert payload["ok"] is True
    assert payload["enabled"] is False
    assert dashboard_server["store"].get_host_control("codex")["enabled"] is False
    assert invalidated == []


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
