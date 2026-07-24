"""Tests for the Agency Runtime HTTP server (agency_runtime/server/http.py).

Uses urllib (stdlib) to hit a live server bound to 127.0.0.1 with an
ephemeral port and a tmp_path SQLite database.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from agency_runtime.core.configuration import apply_config_operations, read_config_state
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.roster.bundled import BundledRoster
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.http import (
    AgencyHTTPHandler,
    AgencyHTTPServer,
    _is_loopback_host,
)

AUTH_HEADERS = {"Authorization": "Bearer test-token"}


@pytest.fixture()
def http_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Start a real HTTP server on an ephemeral port backed by a tmp DB."""
    # Use a fast judge timeout so the test doesn't hang when no LLM is available
    monkeypatch.setenv("AGENCY_JUDGE_TIMEOUT", "1")
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "missing.yaml"))
    from agency_runtime.core.config import reset_config_cache

    reset_config_cache()

    db = tmp_path / "agency.db"
    store = Store(db)

    # Seed active agents so preflight/search have a catalog to work with.
    # code-reviewer's same_context_conflicts closure (codebase-onboarding-
    # engineer -> technical-writer) must be present so the workforce index
    # fingerprint stays coherent during preflight.
    bundled = {agent["slug"]: dict(agent) for agent in BundledRoster()}
    store._activate_prevalidated_agent(bundled["code-reviewer"])
    for slug in (
        "agents-orchestrator",
        "chief-of-staff",
        "codebase-onboarding-engineer",
        "technical-writer",
    ):
        store._activate_prevalidated_agent(bundled[slug])

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
        reset_config_cache()


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
        with exc:
            return exc.code, json.loads(exc.read())


def _get(base: str, path: str) -> tuple[int, dict]:
    req = urllib.request.Request(f"{base}{path}", headers=AUTH_HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read())


def _raw_request(port: int, request: bytes) -> bytes:
    client = socket.create_connection(("127.0.0.1", port), timeout=2)
    client.settimeout(2)
    try:
        client.sendall(request)
        response = bytearray()
        while chunk := client.recv(4096):
            response.extend(chunk)
        return bytes(response)
    finally:
        client.close()


def test_http_rejects_duplicate_json_fields(http_server) -> None:
    body = b'{"session_id":"first","session_id":"second","prompt":"review"}'
    response = _raw_request(
        http_server["port"],
        (
            b"POST /preflight HTTP/1.1\r\n"
            + f"Host: 127.0.0.1:{http_server['port']}\r\n".encode()
            + b"Authorization: Bearer test-token\r\n"
            + b"Content-Type: application/json\r\n"
            + f"Content-Length: {len(body)}\r\n".encode()
            + b"Connection: close\r\n\r\n"
            + body
        ),
    )

    assert b"400 Bad Request" in response
    assert b"invalid bounded JSON" in response


# ── /status ─────────────────────────────────────────────────────────────


def test_status_returns_ok_and_roster_count(http_server):
    status, body = _get(http_server["base"], "/status")
    assert status == 200
    assert body["status"] == "ok"
    assert body["roster_count"] == 3


def test_http_fails_closed_after_config_derived_store_target_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "agency.yaml"
    original_db = tmp_path / "original.db"
    replacement_db = tmp_path / "replacement.db"
    config_path.write_text(f"store:\n  db_path: {original_db}\n", encoding="utf-8")
    monkeypatch.delenv("AGENCY_DB_PATH", raising=False)
    store = Store(config_path=config_path)
    server = AgencyHTTPServer(
        store,
        host="127.0.0.1",
        port=0,
        auth_token="test-token",
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status, body = _get(base, "/status")
        assert status == 200
        assert body["db_path"] == str(original_db)

        state = read_config_state(config_path)
        apply_config_operations(
            [{"op": "set", "path": "store.db_path", "value": str(replacement_db)}],
            expected_revision=state.revision,
            path=config_path,
        )

        status, body = _get(base, "/status")
        assert status == 500
        assert body == {"error": "internal server error"}
        assert store.db_path == original_db
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


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
    with exc_info.value as error:
        assert error.code == 403


def test_non_json_post_is_rejected(http_server):
    for _attempt in range(10):
        request = urllib.request.Request(
            f"{http_server['base']}/search",
            data=b'{"query":"code"}',
            headers={"Content-Type": "text/plain", **AUTH_HEADERS},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(request, timeout=5)
        with exc_info.value as error:
            assert error.code == 415
            assert "application/json" in json.loads(error.read())["error"]


def test_unauthenticated_local_request_is_rejected(http_server):
    request = urllib.request.Request(f"{http_server['base']}/status", method="GET")
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(request, timeout=5)
    with exc_info.value as error:
        assert error.code == 401


def test_non_ascii_authorization_is_rejected_without_handler_failure(http_server):
    response = _raw_request(
        http_server["port"],
        (
            "GET /status HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{http_server['port']}\r\n"
            "Authorization: Bearer caf\xe9\r\n"
            "Connection: close\r\n\r\n"
        ).encode("latin-1"),
    )

    assert b"401 Unauthorized" in response
    assert b"authentication required" in response


def test_options_never_grants_browser_preflight(http_server):
    request = urllib.request.Request(
        f"{http_server['base']}/status",
        headers={"Origin": "https://attacker.example"},
        method="OPTIONS",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(request, timeout=5)
    with exc_info.value as error:
        assert error.code == 405
        assert error.headers.get("Access-Control-Allow-Origin") is None


def test_http_server_refuses_non_loopback_binding(tmp_path):
    with pytest.raises(ValueError, match="loopback-only"):
        AgencyHTTPServer(Store(tmp_path / "remote.db"), host="0.0.0.0", port=0)


# ── /roster ─────────────────────────────────────────────────────────────


def test_roster_lists_active_agents(http_server):
    status, body = _get(http_server["base"], "/roster")
    assert status == 200
    assert body["count"] == 3
    assert body["total_count"] == 3
    assert body["truncated"] is False
    assert body["next_cursor"] is None
    slugs = [agent["agent_slug"] for agent in body["agents"]]
    assert "code-reviewer" in slugs
    assert "agents-orchestrator" in slugs
    assert "chief-of-staff" in slugs


def test_public_roster_and_search_exclude_config_disabled_agents(http_server):
    from agency_runtime.core.config import reset_config_cache

    Path(os.environ["AGENCY_CONFIG_PATH"]).write_text(
        "agents:\n  disabled: [code-reviewer]\n",
        encoding="utf-8",
    )
    reset_config_cache()

    status, body = _get(http_server["base"], "/roster")
    assert status == 200
    assert {agent["agent_slug"] for agent in body["agents"]} == {
        "agents-orchestrator",
        "chief-of-staff",
    }
    status, body = _post(
        http_server["base"],
        "/search",
        {"query": "code review", "limit": 10},
    )
    assert status == 200
    assert "code-reviewer" not in {agent["slug"] for agent in body["agents"]}


def test_roster_cursor_pages_are_stable_and_complete(http_server):
    status, first = _get(http_server["base"], "/roster?limit=2")

    assert status == 200
    assert [agent["agent_slug"] for agent in first["agents"]] == [
        "agents-orchestrator",
        "chief-of-staff",
    ]
    assert first["count"] == 2
    assert first["total_count"] == 3
    assert first["truncated"] is True
    assert first["next_cursor"] == "chief-of-staff"

    status, second = _get(
        http_server["base"],
        f"/roster?limit=2&after={first['next_cursor']}",
    )

    assert status == 200
    assert [agent["agent_slug"] for agent in second["agents"]] == ["code-reviewer"]
    assert second["count"] == 1
    assert second["total_count"] == 3
    assert second["truncated"] is False
    assert second["next_cursor"] is None


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
    preflight = run_preflight(
        http_server["store"],
        trace_id="trace-1",
        session_id="session-1",
        user_message="Review this pull request for quality and security",
        host="test",
    )
    assert "code-reviewer" in preflight.loaded_specialists
    loaded = ", ".join(preflight.loaded_specialists)
    draft = "\n".join(
        [
            f"Agency/Agencies loaded: {loaded}",
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
            "session_id": "session-1",
            "trace_id": "trace-1",
            "host": "test",
        },
    )
    assert status == 200
    assert body["action"] == "accept"
    assert body["trace_id"] == "trace-1"
    assert "Here is my review." in body["text"]
    assert http_server["store"].get_run("trace-1")["status"] == "completed"
    assert http_server["store"].get_active_specialists_for_trace("session-1", "trace-1") == []


def test_finalize_rejects_missing_draft(http_server):
    status, body = _post(http_server["base"], "/finalize", {"trace_id": "t1"})
    assert status == 400
    assert "draft_text" in body["error"]


def test_finalize_records_skills_and_delegations(http_server):
    preflight = run_preflight(
        http_server["store"],
        trace_id="trace-2",
        session_id="session-2",
        user_message="Review this pull request for quality and security",
        host="test",
    )
    assert "code-reviewer" in preflight.loaded_specialists
    loaded = ", ".join(preflight.loaded_specialists)
    draft = "\n".join(
        [
            f"Agency/Agencies loaded: {loaded}",
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
                    "work_unit_id": "unit-review",
                    "executed_worker_kind": "test-worker",
                    "executed_worker_id": "worker-review",
                    "native_run_id": "test-backend:run-review",
                },
            ],
        },
    )
    assert status == 200
    assert body["action"] == "accept"
    assert body["session_id"] == "session-2"
    assert "Skills loaded: finalization" in body["text"]
    assert (
        "Agency/Agencies delegated: none - executed worker has no validated Agency specialist"
    ) in body["text"]

    store = http_server["store"]
    assert store.get_skills_for_session("session-2") == ["finalization"]
    delegations = store.get_delegations_for_session("session-2")
    assert len(delegations) == 1
    assert delegations[0]["recommended_agent"] == "code-reviewer"
    assert delegations[0]["backend"] == "test-backend"
    assert delegations[0]["executed_worker_kind"] == "test-worker"
    assert delegations[0]["retrieved_specialist_slug"] == ""
    assert store.get_delegations_for_session("trace-2") == []


def test_finalize_rejects_resident_manager_as_delegated_worker(http_server):
    run_preflight(
        http_server["store"],
        trace_id="trace-resident-worker",
        session_id="session-resident-worker",
        user_message="Review this pull request for quality and security",
        host="test",
    )

    status, body = _post(
        http_server["base"],
        "/finalize",
        {
            "draft_text": "draft",
            "trace_id": "trace-resident-worker",
            "session_id": "session-resident-worker",
            "host": "test",
            "delegations": [
                {
                    "agent": "agents-orchestrator",
                    "status": "completed",
                    "backend": "test-backend",
                    "work_unit_id": "unit-review",
                    "executed_worker_kind": "test-worker",
                    "executed_worker_id": "worker-review",
                    "native_run_id": "test-backend:run-review",
                }
            ],
        },
    )

    assert status == 400
    assert "parent-only" in body["error"]
    assert http_server["store"].get_delegations("trace-resident-worker") == []


def test_finalize_rejects_delegation_without_stable_work_unit_id(http_server):
    status, body = _post(
        http_server["base"],
        "/finalize",
        {
            "draft_text": "draft",
            "trace_id": "trace-missing-work-unit",
            "session_id": "session-missing-work-unit",
            "host": "test",
            "delegations": [
                {
                    "agent": "code-reviewer",
                    "status": "completed",
                    "backend": "test-backend",
                }
            ],
        },
    )

    assert status == 400
    assert body == {"error": "delegations require agent, work_unit_id, and backend"}
    assert http_server["store"].get_delegations("trace-missing-work-unit") == []


# ── /explain ────────────────────────────────────────────────────────────


def test_explain_returns_selection_receipt(http_server):
    from agency_runtime.core.selector.cache import clear_cache
    from agency_runtime.core.selector.stickiness import clear_session_routing

    clear_cache()
    clear_session_routing()
    for _attempt in range(2):
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
    assert "decision_id" not in body["routing"]
    assert http_server["store"].get_open_traces_for_session("s-explain") == []


def test_explain_rejects_missing_task(http_server):
    status, body = _post(http_server["base"], "/explain", {"session_id": "s-explain"})

    assert status == 400
    assert "task" in body["error"]


def test_explain_clamps_untrusted_limit(http_server, monkeypatch):
    captured: list[int] = []

    def explain(*_args, limit: int, **_kwargs):
        captured.append(limit)
        return {"schema_version": "agency.selection_explain.v1"}

    monkeypatch.setattr("agency_runtime.server.http.explain_route", explain)

    status, _body = _post(
        http_server["base"],
        "/explain",
        {"task": "review code", "limit": 10**9},
    )

    assert status == 200
    assert captured == [100]


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
    status, body = _post(http_server["base"], "/search", {"query": "code", "limit": 99999})
    assert status == 200
    assert body["count"] >= 1


# ── Error handling ──────────────────────────────────────────────────────


def test_unknown_path_returns_404(http_server):
    status, body = _get(http_server["base"], "/nonexistent")
    assert status == 404
    assert "error" in body


def test_unknown_post_path_returns_404(http_server):
    status, body = _post(http_server["base"], "/nonexistent", {})
    assert status == 404
    assert "error" in body


def test_json_body_must_be_an_object(http_server):
    request = urllib.request.Request(
        f"{http_server['base']}/search",
        data=b"[]",
        headers={"Content-Type": "application/json", **AUTH_HEADERS},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(request, timeout=5)
    with exc_info.value as error:
        assert error.code == 400
        assert "JSON object" in json.loads(error.read())["error"]


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
    with exc_info.value as error:
        assert error.code == 400


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
    with exc_info.value as error:
        assert error.code == 400


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
    with exc_info.value as error:
        assert error.code == 400


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
        with raised.value as error:
            assert error.code == 413
            assert json.loads(error.read()) == {"error": "request body too large"}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("size", [1023, 64 * 1024 * 1024 + 1, True, 1024.5, "1024", None])
def test_server_rejects_invalid_body_limits(tmp_path: Path, size) -> None:
    with pytest.raises(ValueError, match="max_body_size"):
        AgencyHTTPServer(
            Store(tmp_path / f"invalid-{size}.db"),
            host="127.0.0.1",
            port=0,
            max_body_size=size,
        )


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True])
def test_server_rejects_invalid_request_timeouts(tmp_path: Path, timeout) -> None:
    with pytest.raises(ValueError, match="request_timeout"):
        AgencyHTTPServer(
            Store(tmp_path / f"invalid-timeout-{timeout}.db"),
            host="127.0.0.1",
            port=0,
            request_timeout=timeout,
        )


@pytest.mark.parametrize("token", ["", "line\nbreak", "x" * 4097, 7, b"token"])
def test_server_rejects_invalid_explicit_auth_tokens(tmp_path: Path, token: object) -> None:
    with pytest.raises(ValueError, match="auth_token"):
        AgencyHTTPServer(
            Store(tmp_path / "invalid-token.db"),
            host="127.0.0.1",
            port=0,
            auth_token=token,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("limit", [0, 1025, True, 2.5, "64", None])
def test_server_rejects_invalid_concurrency_limits(tmp_path: Path, limit) -> None:
    with pytest.raises(ValueError, match="max_concurrent_requests"):
        AgencyHTTPServer(
            Store(tmp_path / f"invalid-concurrency-{limit}.db"),
            host="127.0.0.1",
            port=0,
            max_concurrent_requests=limit,
        )


def test_server_rejects_excess_connections_and_releases_worker_slot(
    tmp_path: Path,
) -> None:
    entered = threading.Event()
    released = threading.Event()

    class BlockingHeaderHandler(AgencyHTTPHandler):
        def handle(self) -> None:
            entered.set()
            super().handle()

    class ObservableServer(AgencyHTTPServer):
        def process_request_thread(self, request, client_address) -> None:
            try:
                super().process_request_thread(request, client_address)
            finally:
                released.set()

    server = ObservableServer(
        Store(tmp_path / "concurrency.db"),
        host="127.0.0.1",
        port=0,
        handler_class=BlockingHeaderHandler,
        auth_token="test-token",
        request_timeout=2,
        max_concurrent_requests=1,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    first = socket.create_connection(("127.0.0.1", int(server.server_address[1])), timeout=2)
    try:
        assert entered.wait(timeout=2)
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_address[1]}/status",
            headers=AUTH_HEADERS,
        )
        for _ in range(8):
            with pytest.raises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request, timeout=2)
            with raised.value as error:
                assert error.code == 503
                assert error.headers["Retry-After"] == "1"
                assert error.read() == b""

        large_request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_address[1]}/preflight",
            data=b"x" * server.max_body_size,
            headers={**AUTH_HEADERS, "Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(large_request, timeout=2)
        with raised.value as error:
            assert error.code == 503
            assert error.headers["Retry-After"] == "1"
            assert error.read() == b""

        first.close()
        assert released.wait(timeout=2)
        with urllib.request.urlopen(request, timeout=2) as response:
            assert response.status == 200
    finally:
        first.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_partial_request_body_times_out_without_pinning_worker(tmp_path: Path) -> None:
    server = AgencyHTTPServer(
        Store(tmp_path / "timeout.db"),
        host="127.0.0.1",
        port=0,
        auth_token="test-token",
        request_timeout=0.05,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = socket.create_connection(
        ("127.0.0.1", int(server.server_address[1])),
        timeout=2,
    )
    client.settimeout(2)
    try:
        client.sendall(
            (
                "POST /search HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{server.server_address[1]}\r\n"
                "Authorization: Bearer test-token\r\n"
                "Content-Type: application/json\r\n"
                "Content-Length: 100\r\n"
                "Connection: close\r\n\r\n"
                "{"
            ).encode("ascii")
        )
        response = bytearray()
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            response.extend(chunk)
        assert b"408 Request Timeout" in response
        assert b"request body timed out" in response
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize(
    "framing_headers,body",
    [
        ("Transfer-Encoding: chunked\r\n", b"0\r\n\r\n"),
        ("Transfer-Encoding: \r\nContent-Length: 2\r\n", b"{}"),
        ("Content-Length: 2\r\nContent-Length: 3\r\n", b"{}"),
    ],
)
def test_server_rejects_ambiguous_request_framing(
    http_server,
    framing_headers: str,
    body: bytes,
) -> None:
    client = socket.create_connection(("127.0.0.1", http_server["port"]), timeout=2)
    client.settimeout(2)
    try:
        client.sendall(
            (
                "POST /search HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{http_server['port']}\r\n"
                "Authorization: Bearer test-token\r\n"
                "Content-Type: application/json\r\n"
                f"{framing_headers}"
                "Connection: close\r\n\r\n"
            ).encode("ascii")
            + body
        )
        response = bytearray()
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            response.extend(chunk)
        assert b"400 Bad Request" in response
        assert b"transfer encoding is unsupported" in response
    finally:
        client.close()


@pytest.mark.parametrize("raw_length", ["+2", "-1", "2x"])
def test_server_rejects_noncanonical_content_length(http_server, raw_length: str):
    response = _raw_request(
        http_server["port"],
        (
            "POST /search HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{http_server['port']}\r\n"
            "Authorization: Bearer test-token\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {raw_length}\r\n"
            "Connection: close\r\n\r\n"
            "{}"
        ).encode("ascii"),
    )

    assert b"400 Bad Request" in response
    assert b"invalid or missing Content-Length" in response


def test_server_rejects_unbounded_numeric_content_length_without_conversion(http_server):
    response = _raw_request(
        http_server["port"],
        (
            "POST /search HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{http_server['port']}\r\n"
            "Authorization: Bearer test-token\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {'9' * 5000}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii"),
    )

    assert b"HTTP/1.1 413 " in response
    assert b"request body too large" in response


def test_loopback_host_validation_is_explicit() -> None:
    assert _is_loopback_host("localhost") is True
    assert _is_loopback_host("127.0.0.1") is True
    assert _is_loopback_host("::1") is True
    assert _is_loopback_host("example.test") is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("skills_loaded", "not-a-list"),
        ("skills_loaded", ["x"] * 129),
        ("delegations", [{"agent": "reviewer"}] * 129),
        ("delegations", [{"agent": "x" * 2049}]),
    ],
)
def test_finalize_rejects_unbounded_caller_evidence(http_server, field, value) -> None:
    status, body = _post(
        http_server["base"],
        "/finalize",
        {"draft_text": "draft", field: value},
    )

    assert status == 400
    assert field in body["error"]


def test_unhandled_post_errors_do_not_leak_exception_details(http_server, monkeypatch, caplog):
    def boom(self, body):
        raise RuntimeError("secret-token")

    monkeypatch.setattr("agency_runtime.server.http.AgencyHTTPHandler._handle_search", boom)

    status, body = _post(http_server["base"], "/search", {"query": "code"})

    assert status == 500
    assert body == {"error": "internal server error"}
    assert "RuntimeError" in caplog.text
    assert "secret-token" not in caplog.text


def test_unhandled_get_errors_do_not_leak_exception_details(http_server, monkeypatch, caplog):
    def boom(self, **_kwargs):
        raise RuntimeError("secret-token")

    monkeypatch.setattr("agency_runtime.server.http.AgencyHTTPHandler._handle_status", boom)

    status, body = _get(http_server["base"], "/status")

    assert status == 500
    assert body == {"error": "internal server error"}
    assert "RuntimeError" in caplog.text
    assert "secret-token" not in caplog.text


def test_request_logging_escapes_terminal_controls(caplog) -> None:
    caplog.set_level(logging.INFO, logger="agency_runtime.server.http")
    handler = object.__new__(AgencyHTTPHandler)
    handler.client_address = ("127.0.0.1", 12345)

    handler.log_message("request %s", "GET /\x1b[31mred\nforged")

    assert "\x1b" not in caplog.text
    assert "\nforged" not in caplog.text
    assert r"\x1b[31mred\nforged" in caplog.text
