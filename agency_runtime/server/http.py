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
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Type
from urllib.parse import urlparse

from agency_runtime.core.config import load_config
from agency_runtime.core.header.finalize import finalize_response
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.selector.explain import explain_route
from agency_runtime.core.selector.pipeline import (
    build_routing_context,
    is_trivial,
    route,
)
from agency_runtime.core.selector.policy import detect_actions
from agency_runtime.core.store.sqlite import Store

logger = logging.getLogger("agency_runtime.server.http")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7800

# Body size cap to prevent unbounded reads. Routing and finalization payloads do
# not need multi-megabyte request bodies.
_MAX_BODY = 1024 * 1024


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------


class AgencyHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Agency Runtime endpoints."""

    server_version = "AgencyRuntimeHTTP/0.1"
    protocol_version = "HTTP/1.1"

    @property
    def store(self) -> Store:
        return self.server.store  # type: ignore[attr-defined]

    # ── Method dispatch ──────────────────────────────────────────────

    def do_OPTIONS(self) -> None:  # noqa: N802 — http.server contract
        self._json_error(
            HTTPStatus.METHOD_NOT_ALLOWED, "cross-origin requests are not allowed"
        )

    def do_GET(self) -> None:  # noqa: N802 — http.server contract
        if not self._validate_request_boundary():
            return
        path = _normalise_path(self.path)
        try:
            if path == "/status":
                self._handle_status()
            elif path == "/roster":
                self._handle_roster()
            else:
                self._json_error(HTTPStatus.NOT_FOUND, f"unknown path: {path}")
        except Exception as exc:
            _log_unhandled_request_error("GET", path, exc)
            self._json_error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal server error")

    def do_POST(self) -> None:  # noqa: N802 — http.server contract
        if not self._validate_request_boundary(require_json=True):
            return
        path = _normalise_path(self.path)
        body = self._read_json_body()
        if body is None:
            return  # error already sent
        try:
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
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            self._json_error(
                HTTPStatus.BAD_REQUEST, "invalid or missing Content-Length"
            )
            return None
        if length <= 0:
            self._json_error(HTTPStatus.BAD_REQUEST, "request body is empty")
            return None
        max_body_size = int(getattr(self.server, "max_body_size", _MAX_BODY))
        if length > max_body_size:
            self._json_error(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body too large"
            )
            return None
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, f"invalid JSON: {exc}")
            return None
        if not isinstance(body, dict):
            self._json_error(
                HTTPStatus.BAD_REQUEST, "request body must be a JSON object"
            )
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
            chunk = self.rfile.read(min(remaining, 64 * 1024))
            if not chunk:
                self.close_connection = True
                return
            remaining -= len(chunk)

    # ── Response helpers ─────────────────────────────────────────────

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
        )
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
                self._json_error(
                    HTTPStatus.FORBIDDEN, "cross-origin requests are not allowed"
                )
                return False

        supplied = self.headers.get("Authorization", "")
        expected = f"Bearer {self.server.auth_token}"  # type: ignore[attr-defined]
        if not secrets.compare_digest(supplied, expected):
            self._json_error(HTTPStatus.UNAUTHORIZED, "authentication required")
            return False

        if require_json:
            content_type = (
                self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            )
            if content_type != "application/json":
                self._drain_bounded_request_body()
                self._json_error(
                    HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "application/json is required"
                )
                return False
        return True

    # ── Endpoint handlers ────────────────────────────────────────────

    def _handle_preflight(self, body: dict[str, Any]) -> None:
        session_id = str(body.get("session_id", ""))
        user_message = str(body.get("user_message", ""))
        requested_model = str(body.get("model", ""))

        if not user_message:
            self._json_error(HTTPStatus.BAD_REQUEST, "user_message is required")
            return

        catalog = self.store.get_active_roster_as_catalog()
        trivial = is_trivial(user_message)
        trace_id = str(uuid.uuid4())
        routing = route(
            session_id,
            user_message,
            catalog,
            store=self.store,
            trace_id=trace_id,
        )
        context = build_routing_context(routing)
        if trivial:
            active_slugs = {
                str(agent.get("slug") or agent.get("agent_slug") or "")
                for agent in catalog
            }
            _matched, companion_ids = detect_actions(
                user_message,
                active_slugs=active_slugs,
            )
            available = [slug for slug in companion_ids if slug in active_slugs]
            context = None
            if available:
                context = (
                    "[AGENCY PREFLIGHT] Default companion specialist routing "
                    f"(deterministic, trivial message): {', '.join(available)}"
                )

        self._json_ok(
            {
                "trace_id": trace_id,
                "session_id": session_id,
                "model": requested_model,
                "routing": routing,
                "context": context,
                "trivial": trivial,
                "roster_size": len(catalog),
            }
        )

    def _handle_explain(self, body: dict[str, Any]) -> None:
        task = str(body.get("task") or body.get("user_message") or "")
        if not task:
            self._json_error(HTTPStatus.BAD_REQUEST, "task or user_message is required")
            return

        try:
            limit = int(body.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10

        payload = explain_route(
            str(body.get("session_id", "")),
            task,
            self.store.get_active_roster_as_catalog(),
            limit=limit,
            store=self.store,
        )
        self._json_ok(payload)

    def _handle_finalize(self, body: dict[str, Any]) -> None:
        draft_text = str(body.get("draft_text", ""))
        trace_id = str(body.get("trace_id") or body.get("session_id") or "")
        session_id = str(body.get("session_id") or trace_id)
        host = str(body.get("host", "unknown")) or "unknown"
        skills_loaded = body.get("skills_loaded") or []
        delegations = body.get("delegations") or []

        if not draft_text:
            self._json_error(HTTPStatus.BAD_REQUEST, "draft_text is required")
            return

        if (skills_loaded or delegations) and not self.server.allow_context_writes:  # type: ignore[attr-defined]
            self._json_error(
                HTTPStatus.FORBIDDEN,
                "caller-provided evidence is disabled on this server",
            )
            return

        # Only explicitly trusted internal servers may promote caller-provided
        # context into canonical storage.
        session_key = session_id
        for skill in skills_loaded:
            self.store.record_skill_loaded(session_key, str(skill))
        for delegation in delegations:
            if isinstance(delegation, dict):
                self.store.record_delegation(
                    trace_id=trace_id,
                    session_id=session_key,
                    host=host,
                    recommended_agent=str(
                        delegation.get("agent", delegation.get("recommended_agent", ""))
                    ),
                    status=str(delegation.get("status", "suggested")),
                    backend=str(delegation.get("backend", "")),
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
        for candidate, score in zip(candidates, scores):
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
        roster = self.store.get_active_roster()
        self._json_ok(
            {
                "status": "ok",
                "roster_count": len(roster),
                "db_path": str(self.store.db_path),
            }
        )

    def _handle_roster(self) -> None:
        roster = self.store.get_active_roster()
        self._json_ok(
            {
                "agents": roster,
                "count": len(roster),
            }
        )

    # ── Logging ──────────────────────────────────────────────────────

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s - %s", self.address_string(), format % args)


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
        store: Store,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        handler_class: Type[AgencyHTTPHandler] = AgencyHTTPHandler,
        *,
        allow_remote: bool = False,
        allow_context_writes: bool = False,
        auth_token: str | None = None,
        max_body_size: int = _MAX_BODY,
    ):
        if not allow_remote and not _is_loopback_host(host):
            raise ValueError(
                "Agency HTTP server is loopback-only unless allow_remote is explicit"
            )
        self.store = store
        self.allow_context_writes = allow_context_writes
        self.auth_token = (
            auth_token or getattr(self, "auth_token", "") or secrets.token_urlsafe(32)
        )
        if (
            isinstance(max_body_size, bool)
            or not 1024 <= int(max_body_size) <= 64 * 1024 * 1024
        ):
            raise ValueError("max_body_size must be between 1024 bytes and 64 MiB")
        self.max_body_size = int(max_body_size)
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalise_path(raw_path: str) -> str:
    """Strip query string and trailing slash, return bare path."""
    path = urlparse(raw_path).path
    return path.rstrip("/") or "/"


def _is_loopback_host(host: str) -> bool:
    normalized = str(host or "").strip().lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _log_unhandled_request_error(method: str, path: str, exc: Exception) -> None:
    """Log traceback shape without leaking exception messages or payload values."""
    frames = traceback.extract_tb(exc.__traceback__)
    frame_refs = ", ".join(
        f"{Path(frame.filename).name}:{frame.lineno}" for frame in frames[-5:]
    )
    logger.error(
        "unhandled error on %s %s: %s at %s",
        method,
        path,
        type(exc).__name__,
        frame_refs or "unknown",
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
    cfg = load_config()
    host = host or cfg.server.host
    port = port or cfg.server.port
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    store = Store(db_path) if db_path else Store()
    server = AgencyHTTPServer(
        store,
        host,
        port,
        max_body_size=cfg.server.max_body_size,
    )
    print(f"Agency Runtime HTTP bearer token: {server.auth_token}")
    logger.info("Agency Runtime HTTP server listening on %s:%d", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("shutting down (interrupted)")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Agency Runtime HTTP server")
    parser.add_argument(
        "--host", default=DEFAULT_HOST, help="bind address (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="listen port (default: 7800)"
    )
    parser.add_argument("--db", default=None, help="SQLite database path")
    args = parser.parse_args()
    serve(args.host, args.port, args.db)


if __name__ == "__main__":
    main()
