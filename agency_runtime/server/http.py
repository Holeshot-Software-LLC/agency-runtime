"""HTTP server for Agency Runtime — exposes the control plane over JSON.

Endpoints:
    POST /preflight  — run routing preflight         {session_id, user_message, model?}
    POST /explain    — explain specialist routing    {session_id?, task|user_message, limit?}
    POST /finalize   — finalize agency header        {draft_text, trace_id?, session_id?, host?, skills_loaded?, delegations?}
    GET  /status     — agency runtime status
    GET  /roster     — list active roster
    POST /search     — search agents                 {query, limit?}

Stdlib only (http.server).  All responses are JSON.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import logging
import secrets
import socket
import traceback
from collections.abc import Callable
from contextlib import suppress
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import BoundedSemaphore, Lock, Thread
from time import monotonic
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from agency_runtime.core.agent_activation import normalize_agent_slug
from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.config import load_config
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.header.finalize import finalize_response
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.routing_snapshot import capture_routing_snapshot
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.selector.explain import explain_route
from agency_runtime.core.specialist_context import SpecialistPromptDeliveryError
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.turn_correlation import active_turn_error

logger = logging.getLogger("agency_runtime.server.http")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7800

# Body size cap to prevent unbounded reads. Routing and finalization payloads do
# not need multi-megabyte request bodies.
_MAX_BODY = 1024 * 1024
_DEFAULT_REQUEST_TIMEOUT = 15.0
_DEFAULT_MAX_CONCURRENT_REQUESTS = 64
_MAX_CONTEXT_ITEMS = 128
_MAX_CONTEXT_TEXT = 2048
_MAX_ROSTER_RESPONSE_AGENTS = 1000
_MAX_ROSTER_CURSOR_BYTES = 1024
_MAX_CONTENT_LENGTH_DIGITS = 20
_MAX_REJECTION_WORKERS = 4
_MAX_REJECTION_HEADER_BYTES = 64 * 1024
_REJECTION_DEADLINE_SECONDS = 0.25
_REJECTION_POLL_SECONDS = 0.05
_OVERLOAD_RESPONSE = (
    b"HTTP/1.1 503 Service Unavailable\r\n"
    b"Connection: close\r\n"
    b"Content-Length: 0\r\n"
    b"Retry-After: 1\r\n\r\n"
)


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------


class AgencyHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Agency Runtime endpoints."""

    server_version = "AgencyRuntimeHTTP/0.1"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def setup(self) -> None:
        """Bound header/body socket I/O before stdlib stream wrappers are built."""

        self.request.settimeout(  # type: ignore[union-attr]
            float(getattr(self.server, "request_timeout", _DEFAULT_REQUEST_TIMEOUT))
        )
        super().setup()

    @property
    def store(self) -> Store:
        return self.server.store  # type: ignore[attr-defined]

    # ── Method dispatch ──────────────────────────────────────────────

    def do_OPTIONS(self) -> None:
        self._json_error(HTTPStatus.METHOD_NOT_ALLOWED, "cross-origin requests are not allowed")

    def do_GET(self) -> None:
        if not self._validate_request_boundary():
            return
        path = _normalise_path(self.path)
        try:
            from agency_runtime.core.runtime_control import (
                master_enabled,
                read_effective_runtime_control,
            )

            if not master_enabled():
                master = read_effective_runtime_control()
                if path == "/status":
                    self._json_ok(
                        {
                            "status": "ok",
                            "runtime_enabled": False,
                            "bypassed": True,
                            "master": master,
                        }
                    )
                elif path == "/roster":
                    self._json_ok(
                        {
                            "runtime_enabled": False,
                            "bypassed": True,
                            "agents": [],
                            "count": 0,
                        }
                    )
                else:
                    self._json_error(HTTPStatus.NOT_FOUND, f"unknown path: {path}")
                return
            if path in {"/status", "/roster"}:
                from agency_runtime.core.config_binding import assert_store_config_binding

                assert_store_config_binding(self.store)
            if path == "/status":
                self._handle_status()
            elif path == "/roster":
                self._handle_roster()
            else:
                self._json_error(HTTPStatus.NOT_FOUND, f"unknown path: {path}")
        except Exception as exc:
            _log_unhandled_request_error("GET", path, exc)
            self._json_error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal server error")

    def do_POST(self) -> None:
        if not self._validate_request_boundary(require_json=True):
            return
        path = _normalise_path(self.path)
        try:
            body = self._read_json_body()
            if body is None:
                return  # error already sent
            from agency_runtime.core.runtime_control import master_enabled

            if not master_enabled():
                payload = {"runtime_enabled": False, "bypassed": True}
                if path == "/finalize":
                    payload.update(
                        {
                            "action": "bypass",
                            "text": str(body.get("draft_text") or ""),
                        }
                    )
                if path in {"/preflight", "/explain", "/finalize", "/search"}:
                    self._json_ok(payload)
                else:
                    self._json_error(HTTPStatus.NOT_FOUND, f"unknown path: {path}")
                return
            if path in {"/preflight", "/explain", "/finalize", "/search"}:
                from agency_runtime.core.config_binding import assert_store_config_binding

                assert_store_config_binding(self.store)
            if path == "/preflight":
                self._handle_preflight(body)
            elif path == "/explain":
                self._handle_explain(body)
            elif path == "/finalize":
                self._handle_finalize(body)
            elif path == "/search":
                self._handle_search(body)
            else:
                self._json_error(HTTPStatus.NOT_FOUND, f"unknown path: {path}")
        except Exception as exc:
            _log_unhandled_request_error("POST", path, exc)
            self._json_error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal server error")

    # ── Body parsing ─────────────────────────────────────────────────

    def _read_json_body(self) -> dict[str, Any] | None:
        content_lengths = self.headers.get_all("Content-Length", [])
        transfer_encodings = self.headers.get_all("Transfer-Encoding", [])
        if transfer_encodings or len(content_lengths) != 1:
            self.close_connection = True
            self._json_error(
                HTTPStatus.BAD_REQUEST,
                "exactly one Content-Length is required; transfer encoding is unsupported",
            )
            return None
        raw_length = content_lengths[0]
        if len(raw_length) > _MAX_CONTENT_LENGTH_DIGITS:
            self.close_connection = True
            self._json_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body too large")
            return None
        if not raw_length.isascii() or not raw_length.isdigit():
            self.close_connection = True
            self._json_error(HTTPStatus.BAD_REQUEST, "invalid or missing Content-Length")
            return None
        try:
            length = int(raw_length)
        except (ValueError, OverflowError):  # defensive if integer parsing semantics change
            self.close_connection = True
            self._json_error(HTTPStatus.BAD_REQUEST, "invalid or missing Content-Length")
            return None
        if length <= 0:
            self._json_error(HTTPStatus.BAD_REQUEST, "request body is empty")
            return None
        max_body_size = int(getattr(self.server, "max_body_size", _MAX_BODY))
        if length > max_body_size:
            self.close_connection = True
            self._json_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body too large")
            return None
        try:
            raw = self.rfile.read(length)
        except (OSError, TimeoutError):
            self.close_connection = True
            self._json_error(HTTPStatus.REQUEST_TIMEOUT, "request body timed out")
            return None
        if len(raw) != length:
            self.close_connection = True
            self._json_error(HTTPStatus.BAD_REQUEST, "request body ended early")
            return None
        try:
            body = safe_load_bounded_json(raw)
        except (BoundedJSONError, UnicodeDecodeError):
            self._json_error(HTTPStatus.BAD_REQUEST, "invalid bounded JSON")
            return None
        if not isinstance(body, dict):
            self._json_error(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
            return None
        return body

    def _drain_bounded_request_body(self) -> None:
        """Consume a small rejected body so Windows can deliver the JSON error.

        Closing a socket with unread request bytes can produce a TCP reset on
        Windows, causing the client to lose the response that explains the
        rejection. Only authenticated, bounded requests reach this helper.
        Oversized or malformed lengths fail closed instead of triggering an
        unbounded read.
        """
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length) if raw_length is not None else 0
        except (TypeError, ValueError):
            self.close_connection = True
            return
        max_body_size = int(getattr(self.server, "max_body_size", _MAX_BODY))
        if length <= 0:
            return
        if length > max_body_size:
            self.close_connection = True
            return
        remaining = length
        while remaining:
            try:
                chunk = self.rfile.read(min(remaining, 64 * 1024))
            except (OSError, TimeoutError):
                self.close_connection = True
                return
            if not chunk:
                self.close_connection = True
                return
            remaining -= len(chunk)

    # ── Response helpers ─────────────────────────────────────────────

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        try:
            data = json.dumps(
                payload,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError):
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            data = b'{"error":"internal serialization error"}'
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json_ok(self, payload: dict[str, Any]) -> None:
        self._send_json(HTTPStatus.OK, payload)

    def _json_error(self, status: int, message: str) -> None:
        self._send_json(status, {"error": message})

    def _validate_request_boundary(self, *, require_json: bool = False) -> bool:
        """Reject DNS-rebinding, cross-origin, and browser-simple POSTs."""
        host = self.headers.get("Host", "").strip().lower()
        allowed_hosts = self.server.allowed_hosts  # type: ignore[attr-defined]
        if host not in allowed_hosts:
            self._json_error(HTTPStatus.BAD_REQUEST, "invalid Host header")
            return False

        origin = self.headers.get("Origin")
        if origin:
            expected = f"http://{host}"
            if origin.rstrip("/").lower() != expected.rstrip("/"):
                self._json_error(HTTPStatus.FORBIDDEN, "cross-origin requests are not allowed")
                return False

        supplied = self.headers.get("Authorization", "")
        expected = f"Bearer {self.server.auth_token}"  # type: ignore[attr-defined]
        if (
            len(supplied) > 8192
            or not supplied.isascii()
            or not secrets.compare_digest(supplied, expected)
        ):
            self._json_error(HTTPStatus.UNAUTHORIZED, "authentication required")
            return False

        if require_json:
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                self._drain_bounded_request_body()
                self._json_error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "application/json is required")
                return False
        return True

    # ── Endpoint handlers ────────────────────────────────────────────

    def _handle_preflight(self, body: dict[str, Any]) -> None:
        from agency_runtime.core.turn_origin import native_adapter_turn_origin

        try:
            session_id = validate_correlation_id(
                body.get("session_id"),
                field="session_id",
            )
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        user_message = str(body.get("user_message", ""))
        requested_model = str(body.get("model", ""))

        if not session_id or not user_message:
            self._json_error(
                HTTPStatus.BAD_REQUEST,
                "session_id and user_message are required",
            )
            return

        trace_id = str(uuid4())
        origin_receipt = native_adapter_turn_origin(
            "external_user",
            host="http",
            event="adapter_preflight",
            session_id=session_id,
            trace_id=trace_id,
        )
        try:
            result = run_preflight(
                self.store,
                session_id=session_id,
                user_message=user_message,
                host="http",
                trace_id=trace_id,
                origin_receipt=origin_receipt,
            )
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except SpecialistPromptDeliveryError as exc:
            self._json_error(HTTPStatus.CONFLICT, str(exc))
            return

        self._json_ok({**result.as_dict(), "model": requested_model})

    def _handle_explain(self, body: dict[str, Any]) -> None:
        task = str(body.get("task") or body.get("user_message") or "")
        if not task:
            self._json_error(HTTPStatus.BAD_REQUEST, "task or user_message is required")
            return

        try:
            limit = int(body.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 100))

        try:
            session_id = validate_correlation_id(
                body.get("session_id"),
                field="session_id",
                required=False,
            )
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        snapshot = capture_routing_snapshot(self.store)
        payload = explain_route(
            session_id,
            task,
            snapshot.catalog,
            config=snapshot.config,
            limit=limit,
            store=self.store,
        )
        self._json_ok(payload)

    def _handle_finalize(self, body: dict[str, Any]) -> None:
        draft_text = str(body.get("draft_text", ""))
        raw_trace_id = body.get("trace_id")
        raw_session_id = body.get("session_id")
        host = str(body.get("host", "unknown")) or "unknown"
        skills_loaded = body.get("skills_loaded") or []
        delegations = body.get("delegations") or []

        if not draft_text:
            self._json_error(HTTPStatus.BAD_REQUEST, "draft_text is required")
            return
        if (
            not isinstance(skills_loaded, list)
            or len(skills_loaded) > _MAX_CONTEXT_ITEMS
            or any(
                not isinstance(skill, str) or len(skill) > _MAX_CONTEXT_TEXT
                for skill in skills_loaded
            )
        ):
            self._json_error(HTTPStatus.BAD_REQUEST, "skills_loaded must be a bounded string list")
            return
        delegation_fields = {
            "agent",
            "recommended_agent",
            "status",
            "backend",
            "work_unit_id",
            "skip_reason",
            "error",
        }
        if (
            not isinstance(delegations, list)
            or len(delegations) > _MAX_CONTEXT_ITEMS
            or any(not isinstance(delegation, dict) for delegation in delegations)
            or any(
                not isinstance(delegation[field], str) or len(delegation[field]) > _MAX_CONTEXT_TEXT
                for delegation in delegations
                for field in delegation_fields & delegation.keys()
            )
        ):
            self._json_error(HTTPStatus.BAD_REQUEST, "delegations must be a bounded object list")
            return

        if (skills_loaded or delegations) and not self.server.allow_context_writes:  # type: ignore[attr-defined]
            self._json_error(
                HTTPStatus.FORBIDDEN,
                "caller-provided evidence is disabled on this server",
            )
            return
        allowed_delegation_statuses = {
            "delegated",
            "completed",
            "skipped",
            "failed",
        }
        for delegation in delegations:
            agent = str(delegation.get("agent", delegation.get("recommended_agent", ""))).strip()
            work_unit_id = str(delegation.get("work_unit_id", "")).strip()
            backend = str(delegation.get("backend", "")).strip()
            status = str(delegation.get("status", "")).strip()
            worker_kind = str(delegation.get("executed_worker_kind", "")).strip()
            worker_id = str(delegation.get("executed_worker_id", "")).strip()
            native_run_id = str(delegation.get("native_run_id", "")).strip()
            if not agent or not work_unit_id or not backend:
                self._json_error(
                    HTTPStatus.BAD_REQUEST,
                    "delegations require agent, work_unit_id, and backend",
                )
                return
            if status in {"delegated", "completed"} and not all(
                (worker_kind, worker_id, native_run_id)
            ):
                self._json_error(
                    HTTPStatus.BAD_REQUEST,
                    "positive delegations require executed_worker_kind, "
                    "executed_worker_id, and native_run_id",
                )
                return
            if status not in allowed_delegation_statuses:
                self._json_error(
                    HTTPStatus.BAD_REQUEST,
                    "delegation status must be delegated, completed, skipped, or failed",
                )
                return
        try:
            trace_id = validate_correlation_id(
                raw_trace_id,
                field="trace_id",
            )
            session_id = validate_correlation_id(
                raw_session_id,
                field="session_id",
            )
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        if correlation_error := active_turn_error(self.store, session_id, trace_id):
            self._json_error(HTTPStatus.CONFLICT, correlation_error)
            return
        from agency_runtime.core.resident_managers import resident_manager_boundary_error

        for delegation in delegations:
            delegated_agent = delegation.get("agent", delegation.get("recommended_agent", ""))
            if boundary_error := resident_manager_boundary_error(
                delegated_agent,
                operation="be recorded as a delegated worker",
            ):
                self._json_error(HTTPStatus.BAD_REQUEST, boundary_error)
                return

        # Only explicitly trusted internal servers may promote caller-provided
        # context into canonical storage.
        session_key = session_id
        for skill in skills_loaded:
            self.store.record_skill_loaded(
                session_key,
                str(skill),
                trace_id=trace_id,
            )
        for delegation in delegations:
            self.store.record_delegation(
                trace_id=trace_id,
                session_id=session_key,
                host=host,
                recommended_agent=str(
                    delegation.get("agent", delegation.get("recommended_agent", ""))
                ),
                work_unit_id=str(delegation["work_unit_id"]),
                status=str(delegation["status"]),
                backend=str(delegation.get("backend", "")),
                executed_worker_kind=str(delegation.get("executed_worker_kind", "")),
                executed_worker_id=str(delegation.get("executed_worker_id", "")),
                native_run_id=str(delegation.get("native_run_id", "")),
                skip_reason=str(delegation.get("skip_reason", "")),
                error=str(delegation.get("error", "")),
            )

        result = finalize_response(
            draft_text,
            trace_metadata={
                "trace_id": trace_id,
                "host": host,
                "session_id": session_key,
            },
            store=self.store,
        )
        self._json_ok(
            {
                "action": result["action"],
                "text": result["text"],
                "missing": result["missing"],
                "trace_id": trace_id,
                "session_id": session_id,
            }
        )

    def _handle_search(self, body: dict[str, Any]) -> None:
        query = str(body.get("query", ""))
        if not query:
            self._json_error(HTTPStatus.BAD_REQUEST, "query is required")
            return

        try:
            limit = int(body.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 100))

        catalog = self.store.get_active_roster_as_catalog()
        candidates, scores = pre_narrow(query, catalog, limit=limit)
        results = []
        for candidate, score in zip(candidates, scores, strict=True):
            entry = dict(candidate)
            entry["score"] = round(float(score), 2)
            results.append(entry)

        self._json_ok(
            {
                "query": query,
                "agents": results,
                "count": len(results),
            }
        )

    def _handle_status(self) -> None:
        from agency_runtime.core.runtime_control import read_effective_runtime_control

        self._json_ok(
            {
                "status": "ok",
                "runtime_enabled": True,
                "master": read_effective_runtime_control(),
                "roster_count": self.store.count_enabled_roster(),
                "db_path": str(self.store.db_path),
            }
        )

    def _handle_roster(self) -> None:
        try:
            limit, after = _bounded_roster_page(self.path)
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        disabled = self.store.get_disabled_agent_slugs()
        page = self.store.get_enabled_roster(
            limit=limit + 1,
            after=after,
            disabled_agents=disabled,
        )
        truncated = len(page) > limit
        roster = page[:limit]
        total_count = self.store.count_enabled_roster(disabled_agents=disabled)
        self._json_ok(
            {
                "agents": roster,
                "count": len(roster),
                "total_count": total_count,
                "limit": limit,
                "truncated": truncated,
                "next_cursor": roster[-1]["agent_slug"] if truncated else None,
            }
        )

    # ── Logging ──────────────────────────────────────────────────────

    def log_message(self, format: str, *args: Any) -> None:
        logger.info(
            "%s - %s",
            self.address_string(),
            _escape_log_text(format % args, limit=2048),
        )


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------


class AgencyHTTPServer(ThreadingHTTPServer):
    """Threaded HTTP server for Agency Runtime.

    Each request is handled in its own thread.  The Store creates a fresh
    SQLite connection per method call with WAL mode + busy_timeout, so
    concurrent access is safe.
    """

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        store: Store | None,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        handler_class: type[AgencyHTTPHandler] = AgencyHTTPHandler,
        *,
        allow_remote: bool = False,
        allow_context_writes: bool = False,
        auth_token: str | None = None,
        max_body_size: int = _MAX_BODY,
        request_timeout: float = _DEFAULT_REQUEST_TIMEOUT,
        max_concurrent_requests: int = _DEFAULT_MAX_CONCURRENT_REQUESTS,
        store_factory: Callable[[], Store] | None = None,
    ):
        if not allow_remote and not _is_loopback_host(host):
            raise ValueError("Agency HTTP server is loopback-only unless allow_remote is explicit")
        self._store = store
        self._store_factory = store_factory or Store
        self._store_lock = Lock()
        self.allow_context_writes = allow_context_writes
        if auth_token is None:
            candidate_token = getattr(self, "auth_token", "") or secrets.token_urlsafe(32)
        else:
            candidate_token = auth_token
        if (
            not isinstance(candidate_token, str)
            or not candidate_token
            or len(candidate_token) > 4096
            or any(character in candidate_token for character in "\r\n")
        ):
            raise ValueError("auth_token must be a bounded single-line string")
        self.auth_token = candidate_token
        if isinstance(max_body_size, bool) or not isinstance(max_body_size, int):
            raise ValueError("max_body_size must be an integer")
        if not 1024 <= max_body_size <= 64 * 1024 * 1024:
            raise ValueError("max_body_size must be between 1024 bytes and 64 MiB")
        self.max_body_size = max_body_size
        if (
            isinstance(request_timeout, bool)
            or not isinstance(request_timeout, (int, float))
            or not 0.05 <= float(request_timeout) <= 300.0
        ):
            raise ValueError("request_timeout must be between 0.05 and 300 seconds")
        self.request_timeout = float(request_timeout)
        if (
            isinstance(max_concurrent_requests, bool)
            or not isinstance(max_concurrent_requests, int)
            or not 1 <= max_concurrent_requests <= 1024
        ):
            raise ValueError("max_concurrent_requests must be between 1 and 1024")
        self.max_concurrent_requests = max_concurrent_requests
        self._request_slots = BoundedSemaphore(max_concurrent_requests)
        self._rejection_slots = BoundedSemaphore(_MAX_REJECTION_WORKERS)
        # ``TCPServer`` creates its listening socket during ``__init__`` using
        # this attribute.  Set it on the instance before delegating so an
        # explicit ``::1`` binding is genuinely IPv6 rather than merely
        # accepted by the loopback validation above.
        try:
            if ipaddress.ip_address(host).version == 6:
                self.address_family = socket.AF_INET6
        except ValueError:
            # Names such as ``localhost`` retain the stdlib's IPv4 default.
            pass
        super().__init__((host, port), handler_class)
        actual_port = int(self.server_address[1])
        self.allowed_hosts = {
            f"127.0.0.1:{actual_port}",
            f"localhost:{actual_port}",
            f"[::1]:{actual_port}",
        }

    @property
    def store(self) -> Store:
        """Materialize SQLite only when an enabled request needs runtime work."""

        if self._store is None:
            with self._store_lock:
                if self._store is None:
                    self._store = self._store_factory()
        return self._store

    @store.setter
    def store(self, value: Store | None) -> None:
        """Preserve the historic explicit-store injection seam."""

        self._store = value

    def process_request(self, request: Any, client_address: Any) -> None:
        """Start one bounded request worker or reject excess concurrency."""
        if not self._request_slots.acquire(blocking=False):
            if not self._rejection_slots.acquire(blocking=False):
                self.shutdown_request(request)
                return
            try:
                worker = Thread(
                    target=self._reject_excess_request,
                    args=(request,),
                    daemon=True,
                    name="agency-http-overload",
                )
                worker.start()
            except BaseException:
                self._rejection_slots.release()
                raise
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._request_slots.release()
            raise

    def _reject_excess_request(self, request: Any) -> None:
        """Deliver a bounded overload response without stalling the accept loop.

        Winsock may replace a response with a TCP reset when a socket is closed
        while request bytes remain unread. Half-close the response side, then
        drain only a small, time-bounded amount of input in a separately bounded
        worker. Clients beyond either rejection bound are closed immediately.
        """
        deadline = monotonic() + _REJECTION_DEADLINE_SECONDS
        try:
            request.settimeout(_REJECTION_DEADLINE_SECONDS)
            request.sendall(_OVERLOAD_RESPONSE)
            with suppress(OSError):
                request.shutdown(socket.SHUT_WR)

            remaining = self.max_body_size + _MAX_REJECTION_HEADER_BYTES
            while remaining > 0:
                timeout = deadline - monotonic()
                if timeout <= 0:
                    break
                request.settimeout(min(timeout, _REJECTION_POLL_SECONDS))
                try:
                    chunk = request.recv(min(remaining, _MAX_REJECTION_HEADER_BYTES))
                except (OSError, TimeoutError):
                    break
                if not chunk:
                    break
                remaining -= len(chunk)
        except (OSError, TimeoutError):
            pass
        finally:
            try:
                self.close_request(request)
            finally:
                self._rejection_slots.release()

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        """Release the request slot after the stdlib worker fully shuts down."""
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._request_slots.release()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalise_path(raw_path: str) -> str:
    """Strip query string and trailing slash, return bare path."""
    path = urlparse(raw_path).path
    return path.rstrip("/") or "/"


def _bounded_roster_limit(raw_path: str) -> int:
    """Return an explicit, compatible bound for roster response materialization."""
    return _bounded_roster_page(raw_path)[0]


def _bounded_roster_page(raw_path: str) -> tuple[int, str | None]:
    """Validate and return the bounded limit and stable roster cursor."""
    try:
        query = parse_qs(
            urlparse(raw_path).query,
            keep_blank_values=True,
            max_num_fields=16,
        )
    except ValueError as exc:
        raise ValueError("invalid roster query") from exc
    raw_limit = query.get(
        "limit",
        [str(_MAX_ROSTER_RESPONSE_AGENTS)],
    )[0]
    try:
        value = int(raw_limit)
    except (TypeError, ValueError):
        value = _MAX_ROSTER_RESPONSE_AGENTS
    limit = max(1, min(value, _MAX_ROSTER_RESPONSE_AGENTS))

    cursors = query.get("after", [])
    if len(cursors) > 1:
        raise ValueError("after cursor must be provided at most once")
    after = cursors[0] if cursors else None
    if after is not None and (not after or len(after.encode("utf-8")) > _MAX_ROSTER_CURSOR_BYTES):
        raise ValueError(
            f"after cursor must be between 1 and {_MAX_ROSTER_CURSOR_BYTES} UTF-8 bytes"
        )
    if after is not None:
        try:
            normalized_after = normalize_agent_slug(after)
        except ValueError as exc:
            raise ValueError("after cursor must be a canonical agent slug") from exc
        if normalized_after != after:
            raise ValueError("after cursor must be a canonical agent slug")
    return limit, after


def _is_loopback_host(host: str) -> bool:
    normalized = str(host or "").strip().lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _escape_log_text(value: object, *, limit: int) -> str:
    """Render bounded single-line diagnostics without terminal control bytes."""

    text = str(value)[:limit]
    return text.encode("unicode_escape", errors="backslashreplace").decode("ascii")


def _log_unhandled_request_error(method: str, path: str, exc: Exception) -> None:
    """Log traceback shape without leaking exception messages or payload values."""
    frames = traceback.extract_tb(exc.__traceback__)
    frame_refs = ", ".join(f"{Path(frame.filename).name}:{frame.lineno}" for frame in frames[-5:])
    logger.error(
        "unhandled error on %s %s: %s at %s",
        method,
        _escape_log_text(path, limit=512),
        type(exc).__name__,
        _escape_log_text(frame_refs or "unknown", limit=1024),
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def serve(
    host: str | None = None,
    port: int | None = None,
    db_path: str | Path | None = None,
) -> None:
    """Run the Agency Runtime HTTP server until interrupted."""
    from agency_runtime.core.runtime_control import master_enabled

    # A disabled process must not parse normal configuration or open SQLite.
    # If it is re-enabled while running, the first enabled request loads the
    # configured Store lazily; restart to apply configured bind settings.
    cfg = load_config() if master_enabled() else None
    host = (cfg.server.host if cfg is not None else DEFAULT_HOST) if host is None else host
    port = (cfg.server.port if cfg is not None else DEFAULT_PORT) if port is None else port
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    max_body_size = cfg.server.max_body_size if cfg is not None else _MAX_BODY

    def create_store() -> Store:
        live_cfg = cfg or load_config()
        config_path = getattr(live_cfg, "config_path", "") or None
        return (
            Store(db_path, config_path=config_path) if config_path is not None else Store(db_path)
        )

    server = AgencyHTTPServer(
        None,
        host,
        port,
        max_body_size=max_body_size,
        store_factory=create_store,
    )
    print(f"Agency Runtime HTTP bearer token: {server.auth_token}")
    actual_host, actual_port = server.server_address[:2]
    logger.info("Agency Runtime HTTP server listening on %s:%d", actual_host, actual_port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("shutting down (interrupted)")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Agency Runtime HTTP server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="bind address (default: 127.0.0.1)")
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="listen port (default: 7800)"
    )
    parser.add_argument("--db", default=None, help="SQLite database path")
    args = parser.parse_args()
    serve(args.host, args.port, args.db)


if __name__ == "__main__":
    main()
