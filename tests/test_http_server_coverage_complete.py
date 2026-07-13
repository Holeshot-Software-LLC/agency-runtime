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


def test_trivial_preflight_without_available_companion_returns_null_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler, _errors = _bare_handler()
    handler.server.store = SimpleNamespace(get_active_roster_as_catalog=lambda: [])
    payloads: list[dict[str, Any]] = []
    handler._json_ok = payloads.append
    monkeypatch.setattr(http, "is_trivial", lambda _message: True)
    monkeypatch.setattr(http, "route", lambda *_args, **_kwargs: {"selected_ids": []})
    monkeypatch.setattr(http, "build_routing_context", lambda _routing: "context")
    monkeypatch.setattr(http, "detect_actions", lambda *_args, **_kwargs: ([], ["missing"]))
    handler._handle_preflight({"user_message": "thanks"})
    assert payloads[0]["trivial"] is True
    assert payloads[0]["context"] is None


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


def test_concurrency_rejection_handles_a_closed_socket() -> None:
    class _Request:
        def settimeout(self, value: float) -> None:
            assert value == 0.5

        def sendall(self, _payload: bytes) -> None:
            raise OSError("closed")

    server = object.__new__(http.AgencyHTTPServer)
    server._request_slots = _Slot(False)
    shutdown: list[Any] = []
    server.shutdown_request = shutdown.append
    request = _Request()
    server.process_request(request, ("127.0.0.1", 1))
    assert shutdown == [request]


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
