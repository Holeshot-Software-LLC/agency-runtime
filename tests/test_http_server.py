"""Tests for the Agency Runtime HTTP server (agency_runtime/server/http.py).

Uses urllib (stdlib) to hit a live server bound to 127.0.0.1 with an
ephemeral port and a tmp_path SQLite database.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.http import AgencyHTTPServer

AUTH_HEADERS = {"Authorization": "Bearer test-token"}


@pytest.fixture()
def http_server(tmp_path: Path):
    """Start a real HTTP server on an ephemeral port backed by a tmp DB."""
    import os

    # Use a fast judge timeout so the test doesn't hang when no LLM is available
    os.environ["AGENCY_JUDGE_TIMEOUT"] = "1"
    os.environ["AGENCY_CONFIG_PATH"] = "/dev/null"
    from agency_runtime.core.config import reset_config_cache

    reset_config_cache()

    db = tmp_path / "agency.db"
    store = Store(db)

    # Seed active agents so preflight/search have a catalog to work with.
    store.activate_agent(
        {
            "slug": "code-reviewer",
            "name": "Code Reviewer",
            "division": "engineering",
            "description": "Reviews pull requests and source code for quality and security.",
            "source": "test",
            "version": "1.0",
            "hash": "abc123",
            "categories": ["code-review"],
            "capabilities": ["code-review"],
            "tool_affinity": [],
            "prompt_path": "",
        }
    )
    for slug in ("agents-orchestrator", "chief-of-staff"):
        store.activate_agent(
            {
                "slug": slug,
                "name": slug.replace("-", " ").title(),
                "division": "specialized",
                "description": f"Default companion specialist {slug}",
                "source": "test",
                "version": "1.0",
                "hash": slug,
                "categories": [],
                "capabilities": [],
                "tool_affinity": [],
                "prompt_path": "",
            }
        )

    server = AgencyHTTPServer(
        store,
        host="127.0.0.1",
        port=0,
        allow_context_writes=True,
        auth_token="test-token",
    )
    actual_port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield {
            "port": actual_port,
            "store": store,
            "base": f"http://127.0.0.1:{actual_port}",
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _post(base: str, path: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers={"Content-Type": "application/json", **AUTH_HEADERS},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _get(base: str, path: str) -> tuple[int, dict]:
    req = urllib.request.Request(f"{base}{path}", headers=AUTH_HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


# ── /status ─────────────────────────────────────────────────────────────


def test_status_returns_ok_and_roster_count(http_server):
    status, body = _get(http_server["base"], "/status")
    assert status == 200
    assert body["status"] == "ok"
    assert body["roster_count"] == 3


def test_responses_include_local_security_headers(http_server):
    request = urllib.request.Request(
        f"{http_server['base']}/status",
        headers=AUTH_HEADERS,
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Cache-Control"] == "no-store"


def test_cross_origin_requests_are_rejected(http_server):
    request = urllib.request.Request(
        f"{http_server['base']}/status",
        headers={"Origin": "https://attacker.example", **AUTH_HEADERS},
        method="GET",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(request, timeout=5)
    assert exc_info.value.code == 403


def test_non_json_post_is_rejected(http_server):
    request = urllib.request.Request(
        f"{http_server['base']}/search",
        data=b'{"query":"code"}',
        headers={"Content-Type": "text/plain", **AUTH_HEADERS},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(request, timeout=5)
    assert exc_info.value.code == 415


def test_unauthenticated_local_request_is_rejected(http_server):
    request = urllib.request.Request(f"{http_server['base']}/status", method="GET")
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(request, timeout=5)
    assert exc_info.value.code == 401


def test_http_server_refuses_non_loopback_binding(tmp_path):
    with pytest.raises(ValueError, match="loopback-only"):
        AgencyHTTPServer(Store(tmp_path / "remote.db"), host="0.0.0.0", port=0)


# ── /roster ─────────────────────────────────────────────────────────────


def test_roster_lists_active_agents(http_server):
    status, body = _get(http_server["base"], "/roster")
    assert status == 200
    assert body["count"] == 3
    slugs = [agent["agent_slug"] for agent in body["agents"]]
    assert "code-reviewer" in slugs
    assert "agents-orchestrator" in slugs
    assert "chief-of-staff" in slugs


# ── /preflight ──────────────────────────────────────────────────────────


def test_preflight_returns_routing_and_context(http_server):
    status, body = _post(
        http_server["base"],
        "/preflight",
        {
            "session_id": "s1",
            "user_message": "Please review this pull request for quality and security",
            "model": "task-agency-router",
        },
    )
    assert status == 200
    assert body["session_id"] == "s1"
    assert body["model"] == "task-agency-router"
    assert "trace_id" in body
    assert "routing" in body
    assert body["roster_size"] == 3
    assert body["trivial"] is False
    # context may be None if the LLM judge is unreachable, but the routing
    # dict must always have selected_ids.
    assert "selected_ids" in body["routing"]


def test_preflight_rejects_missing_user_message(http_server):
    status, body = _post(http_server["base"], "/preflight", {"session_id": "s1"})
    assert status == 400
    assert "user_message" in body["error"]


def test_preflight_detects_trivial_messages(http_server):
    status, body = _post(
        http_server["base"],
        "/preflight",
        {
            "session_id": "s1",
            "user_message": "ok",
        },
    )
    assert status == 200
    assert body["trivial"] is True
    assert body["context"] is not None
    assert "agents-orchestrator, chief-of-staff" in body["context"]


# ── /finalize ───────────────────────────────────────────────────────────


def test_finalize_returns_accept_with_complete_header(http_server):
    draft = "\n".join(
        [
            "Agency/Agencies loaded: code-reviewer",
            "Agency/Agencies delegated: none",
            "Skills loaded: none",
            "Actual Model selected: task-agency-router -> openai/gpt-4",
            "Why: code review requested",
            "How it shaped outcome: routed to specialist",
            "",
            "Here is my review.",
        ]
    )
    status, body = _post(
        http_server["base"],
        "/finalize",
        {
            "draft_text": draft,
            "trace_id": "trace-1",
            "host": "test",
        },
    )
    assert status == 200
    assert body["action"] == "accept"
    assert body["trace_id"] == "trace-1"
    assert "Here is my review." in body["text"]


def test_finalize_rejects_missing_draft(http_server):
    status, body = _post(http_server["base"], "/finalize", {"trace_id": "t1"})
    assert status == 400
    assert "draft_text" in body["error"]


def test_finalize_records_skills_and_delegations(http_server):
    draft = "\n".join(
        [
            "Agency/Agencies loaded: code-reviewer",
            "Agency/Agencies delegated: code-reviewer via test-backend",
            "Skills loaded: finalization",
            "Actual Model selected: task-agency-router -> openai/gpt-4",
            "Why: review work",
            "How it shaped outcome: made delegation explicit",
            "",
            "Done.",
        ]
    )
    status, body = _post(
        http_server["base"],
        "/finalize",
        {
            "draft_text": draft,
            "trace_id": "trace-2",
            "session_id": "session-2",
            "host": "test",
            "skills_loaded": ["finalization"],
            "delegations": [
                {
                    "agent": "code-reviewer",
                    "status": "completed",
                    "backend": "test-backend",
                },
            ],
        },
    )
    assert status == 200
    assert body["action"] == "accept"
    assert body["session_id"] == "session-2"
    assert "Skills loaded: finalization" in body["text"]
    assert "Agency/Agencies delegated: code-reviewer via test-backend" in body["text"]

    store = http_server["store"]
    assert store.get_skills_for_session("session-2") == ["finalization"]
    delegations = store.get_delegations_for_session("session-2")
    assert len(delegations) == 1
    assert delegations[0]["recommended_agent"] == "code-reviewer"
    assert delegations[0]["backend"] == "test-backend"
    assert store.get_delegations_for_session("trace-2") == []


# ── /explain ────────────────────────────────────────────────────────────


def test_explain_returns_selection_receipt(http_server):
    from agency_runtime.core.selector.cache import clear_cache
    from agency_runtime.core.selector.stickiness import clear_session_routing

    clear_cache()
    clear_session_routing()
    status, body = _post(
        http_server["base"],
        "/explain",
        {
            "session_id": "s-explain",
            "task": "review code quality",
            "limit": 5,
        },
    )

    assert status == 200
    assert body["schema_version"] == "agency.selection_explain.v1"
    assert body["task"] == "review code quality"
    assert body["selected"]
    assert body["signals"]["selection"]["roster_size"] >= 1


def test_explain_rejects_missing_task(http_server):
    status, body = _post(http_server["base"], "/explain", {"session_id": "s-explain"})

    assert status == 400
    assert "task" in body["error"]


# ── /search ─────────────────────────────────────────────────────────────


def test_search_returns_matching_agents(http_server):
    status, body = _post(http_server["base"], "/search", {"query": "code review"})
    assert status == 200
    assert body["count"] >= 1
    slugs = [a["slug"] for a in body["agents"]]
    assert "code-reviewer" in slugs


def test_search_rejects_missing_query(http_server):
    status, body = _post(http_server["base"], "/search", {})
    assert status == 400
    assert "query" in body["error"]


def test_search_clamps_limit(http_server):
    status, body = _post(
        http_server["base"], "/search", {"query": "code", "limit": 99999}
    )
    assert status == 200
    assert body["count"] >= 1


# ── Error handling ──────────────────────────────────────────────────────


def test_unknown_path_returns_404(http_server):
    status, body = _get(http_server["base"], "/nonexistent")
    assert status == 404
    assert "error" in body


def test_invalid_json_returns_400(http_server):
    base = http_server["base"]
    req = urllib.request.Request(
        f"{base}/search",
        data=b"{bad json",
        headers={"Content-Type": "application/json", **AUTH_HEADERS},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req, timeout=5)
    assert exc_info.value.code == 400


def test_invalid_utf8_json_returns_400(http_server):
    base = http_server["base"]
    req = urllib.request.Request(
        f"{base}/search",
        data=b"\xff",
        headers={"Content-Type": "application/json", **AUTH_HEADERS},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req, timeout=5)
    assert exc_info.value.code == 400


def test_empty_body_returns_400(http_server):
    base = http_server["base"]
    req = urllib.request.Request(
        f"{base}/search",
        data=b"",
        headers={"Content-Type": "application/json", **AUTH_HEADERS},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req, timeout=5)
    assert exc_info.value.code == 400


def test_server_enforces_configured_body_limit(tmp_path: Path) -> None:
    server = AgencyHTTPServer(
        Store(tmp_path / "bounded.db"),
        host="127.0.0.1",
        port=0,
        auth_token="test-token",
        max_body_size=1024,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    request = urllib.request.Request(
        f"http://127.0.0.1:{server.server_address[1]}/search",
        data=b"{" + (b" " * 1024) + b"}",
        headers={"Content-Type": "application/json", **AUTH_HEADERS},
        method="POST",
    )
    try:
        with pytest.raises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(request, timeout=5)
        assert raised.value.code == 413
        assert json.loads(raised.value.read()) == {"error": "request body too large"}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("size", [1023, 64 * 1024 * 1024 + 1, True])
def test_server_rejects_invalid_body_limits(tmp_path: Path, size) -> None:
    with pytest.raises(ValueError, match="max_body_size"):
        AgencyHTTPServer(
            Store(tmp_path / f"invalid-{size}.db"),
            host="127.0.0.1",
            port=0,
            max_body_size=size,
        )


def test_unhandled_post_errors_do_not_leak_exception_details(
    http_server, monkeypatch, caplog
):
    def boom(self, body):
        raise RuntimeError("secret-token")

    monkeypatch.setattr(
        "agency_runtime.server.http.AgencyHTTPHandler._handle_search", boom
    )

    status, body = _post(http_server["base"], "/search", {"query": "code"})

    assert status == 500
    assert body == {"error": "internal server error"}
    assert "RuntimeError" in caplog.text
    assert "secret-token" not in caplog.text


def test_unhandled_get_errors_do_not_leak_exception_details(
    http_server, monkeypatch, caplog
):
    def boom(self):
        raise RuntimeError("secret-token")

    monkeypatch.setattr(
        "agency_runtime.server.http.AgencyHTTPHandler._handle_status", boom
    )

    status, body = _get(http_server["base"], "/status")

    assert status == 500
    assert body == {"error": "internal server error"}
    assert "RuntimeError" in caplog.text
    assert "secret-token" not in caplog.text
