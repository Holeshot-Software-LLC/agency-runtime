"""Complete base HTTP boundary, concurrency, and entrypoint coverage."""

from __future__ import annotations

import argparse
import io
import runpy
import socketserver
from email.message import Message
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.selector import pipeline
from agency_runtime.core.specialist_context import (
    MAX_SELECTED_SPECIALISTS,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server import http


def _headers(**values: str) -> Message:
    headers = Message()
    for name, value in values.items():
        headers[name.replace("_", "-")] = value
    return headers


def _bare_handler(
    *,
    headers: Message | None = None,
    rfile: Any | None = None,
    server: Any | None = None,
) -> tuple[http.AgencyHTTPHandler, list[tuple[int, str]]]:
    handler = object.__new__(http.AgencyHTTPHandler)
    handler.headers = headers or Message()
    handler.rfile = rfile or io.BytesIO()
    handler.server = server or SimpleNamespace(max_body_size=1024)
    handler.close_connection = False
    errors: list[tuple[int, str]] = []
    handler._json_error = lambda status, message: errors.append((int(status), message))
    return handler, errors


def test_read_json_body_rejects_short_reads() -> None:
    handler, errors = _bare_handler(
        headers=_headers(Content_Length="10"),
        rfile=io.BytesIO(b"{}"),
    )
    assert handler._read_json_body() is None
    assert errors == [(HTTPStatus.BAD_REQUEST, "request body ended early")]
    assert handler.close_connection is True


def test_drain_rejected_body_handles_every_failure_mode() -> None:
    handler, _errors = _bare_handler(headers=_headers(Content_Length="invalid"))
    handler._drain_bounded_request_body()
    assert handler.close_connection is True

    handler, _errors = _bare_handler(headers=_headers(Content_Length="0"))
    handler._drain_bounded_request_body()
    assert handler.close_connection is False

    handler, _errors = _bare_handler(
        headers=_headers(Content_Length="2048"),
        server=SimpleNamespace(max_body_size=1024),
    )
    handler._drain_bounded_request_body()
    assert handler.close_connection is True

    class _FailingReader:
        def read(self, _size: int) -> bytes:
            raise TimeoutError

    handler, _errors = _bare_handler(headers=_headers(Content_Length="4"), rfile=_FailingReader())
    handler._drain_bounded_request_body()
    assert handler.close_connection is True

    handler, _errors = _bare_handler(headers=_headers(Content_Length="4"), rfile=io.BytesIO(b""))
    handler._drain_bounded_request_body()
    assert handler.close_connection is True


def test_http_json_serialization_failure_is_redacted() -> None:
    sent: list[tuple[str, Any]] = []
    handler = object.__new__(http.AgencyHTTPHandler)
    handler.send_response = lambda status: sent.append(("status", status))
    handler.send_header = lambda name, value: sent.append((name, value))
    handler.end_headers = lambda: None
    handler.wfile = SimpleNamespace(write=lambda value: sent.append(("body", value)))
    handler._send_json(200, {"bad": object()})
    assert ("status", HTTPStatus.INTERNAL_SERVER_ERROR) in sent
    assert ("body", b'{"error":"internal serialization error"}') in sent


def test_request_boundary_rejects_host_and_accepts_matching_origin() -> None:
    server = SimpleNamespace(
        allowed_hosts={"127.0.0.1:7800"},
        auth_token="token",
    )
    handler, errors = _bare_handler(
        headers=_headers(Host="attacker.invalid", Authorization="Bearer token"),
        server=server,
    )
    assert handler._validate_request_boundary() is False
    assert errors[0][0] == HTTPStatus.BAD_REQUEST

    handler, errors = _bare_handler(
        headers=_headers(
            Host="127.0.0.1:7800",
            Origin="http://127.0.0.1:7800/",
            Authorization="Bearer token",
        ),
        server=server,
    )
    assert handler._validate_request_boundary() is True
    assert errors == []


def test_trivial_preflight_seeds_steward_without_selecting_a_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler, errors = _bare_handler()
    store = Store(tmp_path / "fresh-http.db")
    handler.server.store = store
    payloads: list[dict[str, Any]] = []
    handler._json_ok = payloads.append
    from agency_runtime.core.selector import pipeline
    from agency_runtime.core.selector.policy import load_bundled_policy

    monkeypatch.setattr(pipeline, "load_policy", lambda *_args: load_bundled_policy())
    monkeypatch.setattr(
        pipeline,
        "query_judge",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("trivial HTTP preflight must not invoke the semantic judge")
        ),
    )

    handler._handle_preflight({"session_id": "fresh-http", "user_message": "thanks"})

    assert errors == []
    preflight = payloads[0]
    trace_id = preflight["trace_id"]
    assert preflight["trivial"] is True
    assert preflight["routing"]["selected_ids"] == []
    assert preflight["routing"]["status"] == "abstained"
    assert preflight["loaded_specialists"] == []
    assert preflight["resident_managers"] == ["agency-steward"]
    assert "agency-steward" in preflight["context"]
    assert "[Agency resident-steward kernel v2]" in preflight["context"]
    assert not any(line.startswith("[AGENCY LOADED]") for line in preflight["context"].splitlines())
    assert store.get_active_specialists_for_trace("fresh-http", trace_id) == []

    handler.server.allow_context_writes = False
    handler._handle_finalize(
        {
            "session_id": "fresh-http",
            "trace_id": trace_id,
            "host": "http",
            "draft_text": "The turn is complete.",
        }
    )
    assert "Agency/Agencies loaded: agency-steward" in payloads[1]["text"]


def test_http_preflight_rejects_oversized_prompt_without_truncating(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler, errors = _bare_handler()
    store = Store(tmp_path / "bounded-http.db")
    handler.server.store = store
    payloads: list[dict[str, Any]] = []
    handler._json_ok = payloads.append
    user_message = "Review this implementation in depth"
    work_units = pipeline.detect_work_units(user_message)
    slugs = [f"bounded-agent-{index}" for index in range(MAX_SELECTED_SPECIALISTS)]
    for slug in slugs:
        store._activate_prevalidated_agent(
            {
                "slug": slug,
                "name": slug,
                "division": "test",
                "description": "Bounded prompt test",
                "source": "test",
                "version": "1.0.0",
                "hash": slug,
                "categories": ["test"],
                "capabilities": ["testing"],
                "tool_affinity": [],
                "prompt_path": f"test://{slug}",
                "prompt_body": "x" * 20_000,
            }
        )

    monkeypatch.setattr(
        pipeline,
        "route",
        lambda *_args, **_kwargs: {
            "selected_ids": slugs,
            "semantic_ids": slugs,
            "confidence": 0.99,
            "status": "confidence_bypass",
            "source": "semantic",
            "query_hash": "a" * 64,
            "context_fingerprint": "b" * 64,
            "source_message_hash": "c" * 64,
            "work_units": work_units,
        },
    )
    handler._handle_preflight(
        {
            "session_id": "bounded-http",
            "user_message": user_message,
        }
    )

    assert payloads == []
    assert errors == [
        (
            HTTPStatus.CONFLICT,
            "specialist prompt exceeds the exact-delivery ceiling: bounded-agent-0",
        )
    ]
    assert store.get_open_traces_for_session("bounded-http") == []
    assert store.get_specialists_for_session("bounded-http") == []


def test_explain_and_search_use_safe_limit_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    handler, _errors = _bare_handler()
    handler.server.store = SimpleNamespace(get_active_roster_as_catalog=lambda: [])
    payloads: list[dict[str, Any]] = []
    handler._json_ok = payloads.append
    limits: list[int] = []
    monkeypatch.setattr(
        http,
        "explain_route",
        lambda *_args, **kwargs: limits.append(kwargs["limit"]) or {"ok": True},
    )
    handler._handle_explain({"task": "review", "limit": {"invalid": True}})
    assert limits == [10]

    monkeypatch.setattr(
        http,
        "pre_narrow",
        lambda _query, _catalog, *, limit: limits.append(limit) or ([], []),
    )
    handler._handle_search({"query": "review", "limit": object()})
    assert limits == [10, 10]
    assert payloads[-1]["agents"] == []


def test_finalize_refuses_untrusted_caller_evidence() -> None:
    handler, errors = _bare_handler(server=SimpleNamespace(allow_context_writes=False))
    handler._handle_finalize(
        {
            "draft_text": "answer",
            "skills_loaded": ["security"],
        }
    )
    assert errors == [(HTTPStatus.FORBIDDEN, "caller-provided evidence is disabled on this server")]


def test_finalize_rejects_positive_delegation_without_execution_correlation() -> None:
    handler, errors = _bare_handler(server=SimpleNamespace(allow_context_writes=True))

    handler._handle_finalize(
        {
            "draft_text": "answer",
            "delegations": [
                {
                    "agent": "code-reviewer",
                    "work_unit_id": "unit-review",
                    "backend": "spawn_agent",
                    "status": "completed",
                }
            ],
        }
    )

    assert errors == [
        (
            HTTPStatus.BAD_REQUEST,
            "positive delegations require executed_worker_kind, "
            "executed_worker_id, and native_run_id",
        )
    ]


def test_trusted_http_evidence_cannot_manufacture_an_implicit_turn(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    handler, errors = _bare_handler(
        server=SimpleNamespace(
            allow_context_writes=True,
            store=store,
        )
    )
    handler._json_ok = lambda _payload: pytest.fail("unknown correlation must not finalize")

    handler._handle_finalize(
        {
            "draft_text": "answer",
            "session_id": "session",
            "trace_id": "missing-turn",
            "skills_loaded": ["security-review"],
            "delegations": [
                {
                    "agent": "code-reviewer",
                    "status": "delegated",
                    "backend": "spawn_agent",
                    "work_unit_id": "unit-review",
                    "executed_worker_kind": "generic-worker",
                    "executed_worker_id": "worker-review",
                    "native_run_id": "native-review",
                }
            ],
        }
    )

    assert errors == [(HTTPStatus.CONFLICT, "trace_id does not identify an existing active turn")]
    assert store.get_run("missing-turn") is None
    assert store.get_specialists_for_session("session") == []
    assert store.get_delegations("missing-turn") == []


def test_trusted_http_evidence_rejects_unpromoted_reservation(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.reserve_session_turn(
        session_id="session",
        trace_id="reserved-turn",
        host="http",
    )
    handler, errors = _bare_handler(
        server=SimpleNamespace(
            allow_context_writes=True,
            store=store,
        )
    )
    handler._json_ok = lambda _payload: pytest.fail("unpromoted correlation must not finalize")

    handler._handle_finalize(
        {
            "draft_text": "answer",
            "session_id": "session",
            "trace_id": "reserved-turn",
            "skills_loaded": ["security-review"],
            "delegations": [
                {
                    "agent": "code-reviewer",
                    "status": "delegated",
                    "backend": "spawn_agent",
                    "work_unit_id": "unit-review",
                    "executed_worker_kind": "generic-worker",
                    "executed_worker_id": "worker-review",
                    "native_run_id": "native-review",
                }
            ],
        }
    )

    assert errors == [(HTTPStatus.CONFLICT, "trace_id has not completed preflight")]
    assert store.get_skills_for_trace("session", "reserved-turn") == []
    assert store.get_delegations("reserved-turn") == []


def test_localhost_server_path_uses_default_address_family(tmp_path: Path) -> None:
    server = http.AgencyHTTPServer(
        Store(tmp_path / "agency.db"),
        "localhost",
        0,
        auth_token="token",
    )
    try:
        assert server.server_address[1] > 0
    finally:
        server.server_close()


def test_ipv6_loopback_selects_ipv6_before_socket_creation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def initialize(server: Any, address: tuple[str, int], _handler: Any) -> None:
        server.server_address = address

    monkeypatch.setattr(http.ThreadingHTTPServer, "__init__", initialize)
    server = http.AgencyHTTPServer(
        Store(tmp_path / "agency.db"),
        "::1",
        0,
        auth_token="token",
    )
    assert server.address_family == http.socket.AF_INET6
    assert "[::1]:0" in server.allowed_hosts


class _Slot:
    def __init__(self, acquired: bool) -> None:
        self.acquired = acquired
        self.releases = 0

    def acquire(self, *, blocking: bool) -> bool:
        assert blocking is False
        return self.acquired

    def release(self) -> None:
        self.releases += 1


def test_concurrency_rejection_schedules_a_bounded_daemon_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = object.__new__(http.AgencyHTTPServer)
    server._request_slots = _Slot(False)
    server._rejection_slots = _Slot(True)
    request = object()
    scheduled: list[tuple[Any, tuple[Any, ...], bool, str]] = []
    started: list[bool] = []

    class _Thread:
        def __init__(
            self,
            *,
            target: Any,
            args: tuple[Any, ...],
            daemon: bool,
            name: str,
        ) -> None:
            scheduled.append((target, args, daemon, name))

        def start(self) -> None:
            started.append(True)

    monkeypatch.setattr(http, "Thread", _Thread)
    server.process_request(request, ("127.0.0.1", 1))
    assert scheduled == [(server._reject_excess_request, (request,), True, "agency-http-overload")]
    assert started == [True]


def test_concurrency_rejection_hard_closes_when_rejection_budget_is_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = object.__new__(http.AgencyHTTPServer)
    server._request_slots = _Slot(False)
    server._rejection_slots = _Slot(False)
    shutdown: list[Any] = []
    server.shutdown_request = shutdown.append
    monkeypatch.setattr(
        http,
        "Thread",
        lambda **_kwargs: pytest.fail("a rejection worker must not be created"),
    )
    request = object()
    server.process_request(request, ("127.0.0.1", 1))
    assert shutdown == [request]


def test_concurrency_rejection_restores_budget_when_thread_start_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Thread:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def start(self) -> None:
            raise RuntimeError("thread unavailable")

    server = object.__new__(http.AgencyHTTPServer)
    server._request_slots = _Slot(False)
    rejection_slot = _Slot(True)
    server._rejection_slots = rejection_slot
    monkeypatch.setattr(http, "Thread", _Thread)
    with pytest.raises(RuntimeError, match="thread unavailable"):
        server.process_request(object(), ("127.0.0.1", 1))
    assert rejection_slot.releases == 1


class _RejectedRequest:
    def __init__(
        self,
        events: list[Any],
        *,
        chunks: list[bytes] | None = None,
        fail: str | None = None,
    ) -> None:
        self.events = events
        self.chunks = list(chunks or [b""])
        self.fail = fail

    def settimeout(self, value: float) -> None:
        self.events.append(("timeout", value))
        if self.fail == "timeout":
            raise OSError("closed")

    def sendall(self, payload: bytes) -> None:
        self.events.append(("send", payload))
        if self.fail == "send":
            raise OSError("closed")

    def shutdown(self, how: int) -> None:
        self.events.append(("shutdown", how))
        if self.fail == "shutdown":
            raise OSError("closed")

    def recv(self, size: int) -> bytes:
        self.events.append(("recv", size))
        if self.fail == "recv":
            raise TimeoutError("slow peer")
        return self.chunks.pop(0)


def _bare_rejection_server(
    events: list[Any],
) -> tuple[http.AgencyHTTPServer, _Slot]:
    server = object.__new__(http.AgencyHTTPServer)
    server.max_body_size = 1024
    slot = _Slot(True)
    server._rejection_slots = slot
    server.close_request = lambda request: events.append(("close", request))
    return server, slot


def test_overload_worker_half_closes_drains_and_releases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[Any] = []
    request = _RejectedRequest(events, chunks=[b"GET / HTTP/1.1\r\n\r\n", b""])
    server, slot = _bare_rejection_server(events)
    moments = iter([100.0, 100.01, 100.02])
    monkeypatch.setattr(http, "monotonic", lambda: next(moments))

    server._reject_excess_request(request)

    assert events[0] == ("timeout", http._REJECTION_DEADLINE_SECONDS)
    assert events[1] == ("send", http._OVERLOAD_RESPONSE)
    assert events[2] == ("shutdown", http.socket.SHUT_WR)
    assert [event[0] for event in events[3:]] == [
        "timeout",
        "recv",
        "timeout",
        "recv",
        "close",
    ]
    assert events[-1] == ("close", request)
    assert slot.releases == 1


def test_overload_worker_enforces_byte_and_deadline_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    byte_events: list[Any] = []
    byte_request = _RejectedRequest(
        byte_events,
        chunks=[
            b"x" * http._MAX_REJECTION_HEADER_BYTES,
            b"x" * 1024,
        ],
    )
    byte_server, byte_slot = _bare_rejection_server(byte_events)
    monkeypatch.setattr(http, "monotonic", lambda: 10.0)
    byte_server._reject_excess_request(byte_request)
    assert [event for event in byte_events if event[0] == "recv"] == [
        ("recv", http._MAX_REJECTION_HEADER_BYTES),
        ("recv", 1024),
    ]
    assert byte_slot.releases == 1

    deadline_events: list[Any] = []
    deadline_request = _RejectedRequest(deadline_events)
    deadline_server, deadline_slot = _bare_rejection_server(deadline_events)
    moments = iter([20.0, 21.0])
    monkeypatch.setattr(http, "monotonic", lambda: next(moments))
    deadline_server._reject_excess_request(deadline_request)
    assert not [event for event in deadline_events if event[0] == "recv"]
    assert deadline_slot.releases == 1


@pytest.mark.parametrize("failure", ["timeout", "send", "shutdown", "recv"])
def test_overload_worker_closes_and_releases_after_socket_failures(
    failure: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[Any] = []
    request = _RejectedRequest(events, fail=failure)
    server, slot = _bare_rejection_server(events)
    monkeypatch.setattr(http, "monotonic", lambda: 1.0)
    server._reject_excess_request(request)
    assert events[-1] == ("close", request)
    assert slot.releases == 1


def test_overload_worker_releases_budget_when_close_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _RejectedRequest([])
    server = object.__new__(http.AgencyHTTPServer)
    slot = _Slot(True)
    server._rejection_slots = slot
    server.close_request = lambda _request: (_ for _ in ()).throw(OSError("close failed"))
    moments = iter([1.0, 2.0])
    monkeypatch.setattr(http, "monotonic", lambda: next(moments))
    with pytest.raises(OSError, match="close failed"):
        server._reject_excess_request(request)
    assert slot.releases == 1


def test_worker_start_failure_releases_concurrency_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = object.__new__(http.AgencyHTTPServer)
    slot = _Slot(True)
    server._request_slots = slot
    monkeypatch.setattr(
        socketserver.ThreadingMixIn,
        "process_request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("worker failed")),
    )
    with pytest.raises(RuntimeError, match="worker failed"):
        server.process_request(object(), ("127.0.0.1", 1))
    assert slot.releases == 1


def test_serve_uses_config_defaults_and_closes_after_interrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    events: list[tuple[str, Any]] = []

    class _Server:
        auth_token = "token"
        server_address = ("127.0.0.1", 8125)

        def __init__(self, _store: Any, host: str, port: int, **kwargs: Any) -> None:
            events.append(("init", (host, port, kwargs)))

        def serve_forever(self) -> None:
            raise KeyboardInterrupt

        def server_close(self) -> None:
            events.append(("close", None))

    cfg = SimpleNamespace(server=SimpleNamespace(host="localhost", port=0, max_body_size=2048))
    monkeypatch.setattr(http, "load_config", lambda: cfg)
    monkeypatch.setattr(http, "AgencyHTTPServer", _Server)
    monkeypatch.setattr(http, "Store", lambda path=None: events.append(("store", path)) or object())
    monkeypatch.setattr(http.sys.stdout, "isatty", lambda: True)
    http.serve(db_path=tmp_path / "agency.db")
    assert events[-1] == ("close", None)
    assert "bearer token: token" in capsys.readouterr().out


def test_main_parses_arguments_and_module_entrypoint_executes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Any, ...]] = []
    monkeypatch.setattr(
        argparse.ArgumentParser,
        "parse_args",
        lambda _self: argparse.Namespace(host="localhost", port=0, db=str(tmp_path / "one.db")),
    )
    monkeypatch.setattr(http, "serve", lambda *args: calls.append(args))
    http.main()
    assert calls == [("localhost", 0, str(tmp_path / "one.db"))]

    monkeypatch.setattr(
        socketserver.BaseServer,
        "serve_forever",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt),
    )
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "module.db"))
    runpy.run_path(str(Path(http.__file__)), run_name="__main__")
