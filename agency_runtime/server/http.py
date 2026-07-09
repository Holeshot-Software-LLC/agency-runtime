"""HTTP server for Agency Runtime — exposes the control plane over JSON.

Endpoints:
    POST /preflight  — run routing preflight         {session_id, user_message, model?}
    POST /finalize   — finalize agency header        {draft_text, trace_id, host?, skills_loaded?, delegations?}
    GET  /status     — agency runtime status
    GET  /roster     — list active roster
    POST /search     — search agents                 {query, limit?}

Stdlib only (http.server).  All responses are JSON.
"""

from __future__ import annotations

import argparse
import json
import logging
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from agency_runtime.core.config import load_config
from agency_runtime.core.header.finalize import finalize_response
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.selector.pipeline import build_routing_context, is_trivial, route
from agency_runtime.core.store.sqlite import Store

logger = logging.getLogger("agency_runtime.server.http")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7800

# Body size cap to prevent unbounded reads (16 MB).
_MAX_BODY = 16 * 1024 * 1024


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

    def do_GET(self) -> None:  # noqa: N802 — http.server contract
        path = _normalise_path(self.path)
        try:
            if path == "/status":
                self._handle_status()
            elif path == "/roster":
                self._handle_roster()
            else:
                self._json_error(HTTPStatus.NOT_FOUND, f"unknown path: {path}")
        except Exception as exc:
            logger.exception("unhandled error on GET %s", path)
            self._json_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def do_POST(self) -> None:  # noqa: N802 — http.server contract
        path = _normalise_path(self.path)
        body = self._read_json_body()
        if body is None:
            return  # error already sent
        try:
            if path == "/preflight":
                self._handle_preflight(body)
            elif path == "/finalize":
                self._handle_finalize(body)
            elif path == "/search":
                self._handle_search(body)
            else:
                self._json_error(HTTPStatus.NOT_FOUND, f"unknown path: {path}")
        except Exception as exc:
            logger.exception("unhandled error on POST %s", path)
            self._json_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    # ── Body parsing ─────────────────────────────────────────────────

    def _read_json_body(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            self._json_error(HTTPStatus.BAD_REQUEST, "invalid or missing Content-Length")
            return None
        if length <= 0:
            self._json_error(HTTPStatus.BAD_REQUEST, "request body is empty")
            return None
        if length > _MAX_BODY:
            self._json_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body too large")
            return None
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw)
        except json.JSONDecodeError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, f"invalid JSON: {exc}")
            return None
        if not isinstance(body, dict):
            self._json_error(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
            return None
        return body

    # ── Response helpers ─────────────────────────────────────────────

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json_ok(self, payload: dict[str, Any]) -> None:
        self._send_json(HTTPStatus.OK, payload)

    def _json_error(self, status: int, message: str) -> None:
        self._send_json(status, {"error": message})

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
        routing = route(session_id, user_message, catalog)
        context = None if trivial else build_routing_context(routing)

        trace_id = str(uuid.uuid4())
        self._json_ok({
            "trace_id": trace_id,
            "session_id": session_id,
            "model": requested_model,
            "routing": routing,
            "context": context,
            "trivial": trivial,
            "roster_size": len(catalog),
        })

    def _handle_finalize(self, body: dict[str, Any]) -> None:
        draft_text = str(body.get("draft_text", ""))
        trace_id = str(body.get("trace_id", ""))
        host = str(body.get("host", "unknown")) or "unknown"
        skills_loaded = body.get("skills_loaded") or []
        delegations = body.get("delegations") or []

        if not draft_text:
            self._json_error(HTTPStatus.BAD_REQUEST, "draft_text is required")
            return

        # Record caller-provided context into the store so the finalization
        # gate picks it up when filling header fields from canonical storage.
        session_key = trace_id
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
        self._json_ok({
            "action": result["action"],
            "text": result["text"],
            "missing": result["missing"],
            "trace_id": trace_id,
        })

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

        self._json_ok({
            "query": query,
            "agents": results,
            "count": len(results),
        })

    def _handle_status(self) -> None:
        roster = self.store.get_active_roster()
        self._json_ok({
            "status": "ok",
            "roster_count": len(roster),
            "db_path": str(self.store.db_path),
        })

    def _handle_roster(self) -> None:
        roster = self.store.get_active_roster()
        self._json_ok({
            "agents": roster,
            "count": len(roster),
        })

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

    def __init__(self, store: Store, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.store = store
        super().__init__((host, port), AgencyHTTPHandler)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_path(raw_path: str) -> str:
    """Strip query string and trailing slash, return bare path."""
    path = urlparse(raw_path).path
    return path.rstrip("/") or "/"


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
    server = AgencyHTTPServer(store, host, port)
    logger.info("Agency Runtime HTTP server listening on %s:%d", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("shutting down (interrupted)")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Agency Runtime HTTP server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="listen port (default: 7800)")
    parser.add_argument("--db", default=None, help="SQLite database path")
    args = parser.parse_args()
    serve(args.host, args.port, args.db)


if __name__ == "__main__":
    main()
