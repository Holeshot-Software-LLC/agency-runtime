"""Secure loopback-only operations dashboard for Agency Runtime."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import signal
import webbrowser
from concurrent.futures import Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from http import HTTPStatus
from importlib.resources import files
from pathlib import Path
from threading import RLock, Thread, current_thread, main_thread
from time import monotonic
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from agency_runtime.core.config import load_config, reset_config_cache
from agency_runtime.core.dashboard_runtime import (
    remove_dashboard_runtime,
    write_dashboard_runtime,
)
from agency_runtime.core.configuration import (
    ConfigConflictError,
    ConfigState,
    ConfigurationError,
    apply_config_operations,
    read_config_state,
)
from agency_runtime.core.roster.sync import activate_snapshot, approve_snapshot
from agency_runtime.core.selector.explain import explain_route
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.http import AgencyHTTPHandler, AgencyHTTPServer

logger = logging.getLogger("agency_runtime.server.dashboard")

_ASSETS: dict[str, tuple[str, str]] = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/charts.js": ("charts.js", "text/javascript; charset=utf-8"),
}

_HOST_INSPECTION_CACHE_SECONDS = 3.0
_HOST_INSPECTION_DEADLINE_SECONDS = 2.0


def _config_payload(
    state: ConfigState,
    *,
    changed_paths: tuple[str, ...] = (),
    restart_required_paths: tuple[str, ...] = (),
    policy_enforced: bool = False,
) -> dict[str, Any]:
    """Return a JSON-safe, credential-free configuration response."""

    return {
        "path": state.path,
        "persisted": state.persisted,
        "effective": state.effective,
        "revision": state.revision,
        "secret_presence": state.secret_presence,
        "environment_overrides": state.environment_overrides,
        "changed_paths": list(changed_paths),
        "restart_required_paths": list(restart_required_paths),
        "policy_enforced": policy_enforced,
    }


def _required_config_confirmations(operations: list[Any]) -> set[str]:
    required = {"SAVE CONFIG"}
    for operation in operations:
        if not isinstance(operation, dict):
            continue
        if operation.get("op") == "secret":
            required.add("SAVE SENSITIVE CONFIG")
        if operation.get("op") == "set" and operation.get("path") == "profile":
            value = operation.get("value")
            if isinstance(value, str) and value.strip().lower() == "local-only":
                required.add("APPLY LOCAL-ONLY PROFILE")
        if (
            operation.get("op") == "set"
            and operation.get("path") == "observability.capture_content"
            and operation.get("value") is True
        ):
            required.add("ENABLE CONTENT CAPTURE")
    return required


def _unknown_host(
    host: str, *, status: str, error: str | None = None
) -> dict[str, Any]:
    """Return a truth-preserving placeholder when inspection is incomplete."""
    return {
        "host": host,
        "executable": None,
        "executable_discovered": None,
        "native_root": None,
        "native_root_exists": None,
        "current_native_root": None,
        "stale_config": None,
        "discovered": None,
        "staged": None,
        "registered": None,
        "enabled": None,
        "loaded": None,
        "canary": None,
        "marketplace_registered": None,
        "maturity": "inspection-pending"
        if status == "timed_out"
        else "inspection-error",
        "evidence": [],
        "inspection_status": status,
        "inspection_error": error,
    }


def _inspect_one_host(host: str) -> dict[str, Any]:
    from agency_runtime.core.installer import inspect_host_installation

    return inspect_host_installation(host)


class _HostInspectionCoordinator:
    """Parallel, short-lived cache around bounded native host inspection.

    Native inventories are independent and can each have their own timeout.
    Dashboard requests therefore wait only for a small global deadline and
    return explicit unknowns for unfinished hosts.  In-flight inspections are
    shared by concurrent requests rather than multiplied.
    """

    def __init__(
        self,
        *,
        inspect_one: Callable[[str], dict[str, Any]] = _inspect_one_host,
        hosts: tuple[str, ...] | None = None,
        cache_seconds: float = _HOST_INSPECTION_CACHE_SECONDS,
        deadline_seconds: float = _HOST_INSPECTION_DEADLINE_SECONDS,
        executor: ThreadPoolExecutor | None = None,
    ) -> None:
        if hosts is None:
            from agency_runtime.core.installer import HOSTS

            hosts = tuple(HOSTS)
        self.hosts = hosts
        self.inspect_one = inspect_one
        self.cache_seconds = max(0.0, cache_seconds)
        self.deadline_seconds = max(0.0, deadline_seconds)
        self.executor = executor or ThreadPoolExecutor(
            max_workers=max(1, len(hosts)),
            thread_name_prefix="agency-host-inspection",
        )
        # A future may finish between submission and callback registration;
        # ``add_done_callback`` then runs inline while ``inspect`` holds this
        # lock, so re-entrancy is intentional here.
        self._lock = RLock()
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._in_flight: dict[str, Future[dict[str, Any]]] = {}

    def _finished(self, host: str, future: Future[dict[str, Any]]) -> None:
        try:
            value = dict(future.result())
            value["host"] = host
            value["inspection_status"] = "complete"
            value["inspection_error"] = None
        except Exception as exc:  # native details remain in server logs
            logger.warning(
                "host inspection failed for %s (%s)", host, type(exc).__name__
            )
            value = _unknown_host(
                host,
                status="error",
                error=f"inspection failed ({type(exc).__name__})",
            )
        with self._lock:
            if self._in_flight.get(host) is not future:
                return
            self._in_flight.pop(host, None)
            self._cache[host] = (monotonic() + self.cache_seconds, value)

    def invalidate(self, host: str | None = None) -> None:
        """Discard cached and in-flight evidence after a native state change."""
        targets = self.hosts if host is None else (host,)
        with self._lock:
            for target in targets:
                self._cache.pop(target, None)
                future = self._in_flight.pop(target, None)
                if future is not None:
                    future.cancel()

    def inspect(self) -> list[dict[str, Any]]:
        now = monotonic()
        pending: list[Future[dict[str, Any]]] = []
        with self._lock:
            for host in self.hosts:
                cached = self._cache.get(host)
                if cached is not None and cached[0] > now:
                    continue
                future = self._in_flight.get(host)
                if future is None:
                    future = self.executor.submit(self.inspect_one, host)
                    self._in_flight[host] = future
                    future.add_done_callback(
                        lambda item, name=host: self._finished(name, item)
                    )
                pending.append(future)

        # ``wait`` returns at the shared deadline and never waits for slow
        # futures during executor shutdown because this executor is persistent.
        if pending:
            wait(pending, timeout=self.deadline_seconds)

        rendered: list[dict[str, Any]] = []
        now = monotonic()
        with self._lock:
            for host in self.hosts:
                cached = self._cache.get(host)
                if cached is None:
                    rendered.append(_unknown_host(host, status="timed_out"))
                    continue
                expires_at, value = cached
                item = dict(value)
                if expires_at <= now:
                    item["inspection_status"] = "stale"
                    item["registered"] = None
                    item["enabled"] = None
                rendered.append(item)
        return rendered


_HOST_INSPECTIONS = _HostInspectionCoordinator()


def _provider_health(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize observed model receipts without claiming a live health probe."""
    observed: dict[str, dict[str, Any]] = {}
    successful = {"success", "completed", "ok"}
    failed = {"failed", "failure", "error", "cancelled", "timed_out", "timeout"}
    for receipt in receipts:
        provider = (
            str(receipt.get("resolved_provider") or "unresolved").strip()
            or "unresolved"
        )
        status = str(receipt.get("status") or "unknown").strip().lower() or "unknown"
        item = observed.setdefault(
            provider,
            {
                "provider": provider,
                "receipt_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "unknown_count": 0,
                "latest_status": status,
                "latest_at": receipt.get("ended_at") or receipt.get("started_at"),
                "evidence": "recent model receipts; not a live provider probe",
            },
        )
        item["receipt_count"] += 1
        if status in successful:
            item["success_count"] += 1
        elif status in failed:
            item["failure_count"] += 1
        else:
            item["unknown_count"] += 1
    return list(observed.values())


def _recent_counts(activity: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    """Return honest bounded counts for the activity included in a response."""

    return {
        name: len(activity.get(name, []))
        for name in ("runs", "routing", "delegations", "receipts", "finalizations")
    }


def _dashboard_activity(
    activity: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Strip optional captured detail from dashboard activity responses."""

    rendered: dict[str, list[dict[str, Any]]] = {}
    for name in ("runs", "routing", "delegations", "receipts", "finalizations"):
        rows = activity.get(name, [])
        rendered[name] = []
        for row in rows:
            item = dict(row)
            if name == "delegations":
                item.pop("skip_reason", None)
            elif name == "routing":
                item.pop("work_units", None)
            rendered[name].append(item)
    return rendered


def _live_overview(
    activity: dict[str, list[dict[str, Any]]],
    sizes: dict[str, Any],
) -> dict[str, Any]:
    """Build the fast-path summary from one metadata-only activity read."""

    return {
        "status": "ok",
        "db_size_bytes": sizes["db_size_bytes"],
        "wal_size_bytes": sizes["wal_size_bytes"],
        "provider_health": _provider_health(activity.get("receipts", [])),
        "recent": _recent_counts(activity),
    }


def _dashboard_revision(payload: dict[str, Any]) -> str:
    """Hash observable content so sampling time alone never causes a redraw."""

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _bounded_query_limit(raw_path: str, *, default: int) -> int:
    raw_limit = parse_qs(urlparse(raw_path).query).get("limit", [str(default)])[0]
    try:
        value = int(raw_limit)
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, 200))


def _delegation_graph(receipt: dict[str, Any]) -> dict[str, Any]:
    """Build the same dependency graph used by delegation lifecycle dispatch."""
    from agency_runtime.core.delegation.lifecycle import (
        build_dependency_graph,
        normalize_work_units,
    )

    work_units = receipt.get("signals", {}).get("work_units", {}).get("units", [])
    units = normalize_work_units(work_units)
    graph = build_dependency_graph(units)
    return {
        "nodes": [{"id": unit.id, "description": unit.description} for unit in units],
        "edges": [
            {
                "from": source,
                "to": target,
                "reason": graph.reasons.get((source, target), "dependency"),
            }
            for source in sorted(graph.edges)
            for target in sorted(graph.edges[source])
        ],
    }


class DashboardHTTPHandler(AgencyHTTPHandler):
    """Authenticated API plus immutable package-owned dashboard assets."""

    server_version = "AgencyRuntimeDashboard/0.1"

    @property
    def auth_token(self) -> str:
        return self.server.auth_token  # type: ignore[attr-defined]

    def do_OPTIONS(self) -> None:  # noqa: N802 - http.server contract
        self._json_error(
            HTTPStatus.METHOD_NOT_ALLOWED, "cross-origin requests are not allowed"
        )

    def do_GET(self) -> None:  # noqa: N802 - http.server contract
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in _ASSETS:
            self._serve_asset(path)
            return
        if not path.startswith("/api/"):
            self._json_error(HTTPStatus.NOT_FOUND, f"unknown path: {path}")
            return
        if not self._authorise_api_request():
            return
        try:
            if path == "/api/live":
                self._handle_live()
            elif path == "/api/overview":
                self._handle_overview()
            elif path == "/api/roster":
                self._handle_roster()
            elif path == "/api/activity":
                self._handle_activity()
            elif path == "/api/hosts":
                self._handle_hosts()
            elif path == "/api/config":
                self._handle_config()
            elif path == "/api/health":
                self._json_ok({"status": "ok"})
            elif path == "/api/snapshots":
                self._json_ok({"snapshots": self.store.list_roster_snapshots()})
            else:
                self._json_error(HTTPStatus.NOT_FOUND, f"unknown path: {path}")
        except Exception as exc:  # defensive boundary; details stay in logs
            logger.exception(
                "dashboard GET failed for %s (%s)", path, type(exc).__name__
            )
            self._json_error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal server error")

    def do_POST(self) -> None:  # noqa: N802 - http.server contract
        path = urlparse(self.path).path.rstrip("/") or "/"
        if not path.startswith("/api/"):
            self._json_error(HTTPStatus.NOT_FOUND, f"unknown path: {path}")
            return
        if not self._authorise_api_request(require_json=True):
            return
        body = self._read_json_body()
        if body is None:
            return
        try:
            if path == "/api/route":
                self._handle_route_lab(body)
            elif path == "/api/maintenance/trim":
                self._handle_trim(body)
            elif path == "/api/roster/action":
                self._handle_roster_action(body)
            elif path == "/api/hosts/toggle":
                self._handle_host_toggle(body)
            elif path == "/api/config":
                self._handle_config_update(body)
            else:
                self._json_error(HTTPStatus.NOT_FOUND, f"unknown path: {path}")
        except ConfigConflictError as exc:
            self._json_error(HTTPStatus.CONFLICT, str(exc))
        except ConfigurationError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
        except (KeyError, ValueError, RuntimeError) as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:  # defensive boundary; details stay in logs
            logger.exception(
                "dashboard POST failed for %s (%s)", path, type(exc).__name__
            )
            self._json_error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal server error")

    def _authorise_api_request(self, *, require_json: bool = False) -> bool:
        if not self._valid_host_header():
            self._json_error(HTTPStatus.BAD_REQUEST, "invalid Host header")
            return False

        origin = self.headers.get("Origin")
        if origin:
            expected_origin = f"http://{self.headers.get('Host', '')}"
            if origin.rstrip("/").lower() != expected_origin.rstrip("/").lower():
                self._json_error(
                    HTTPStatus.FORBIDDEN, "cross-origin requests are not allowed"
                )
                return False

        supplied = self.headers.get("Authorization", "")
        expected = f"Bearer {self.auth_token}"
        if not secrets.compare_digest(supplied, expected):
            self._json_error(HTTPStatus.UNAUTHORIZED, "authentication required")
            return False

        if require_json:
            content_type = (
                self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            )
            if content_type != "application/json":
                self._json_error(
                    HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "application/json is required"
                )
                return False
        return True

    def _valid_host_header(self) -> bool:
        raw = self.headers.get("Host", "").strip().lower()
        port = int(self.server.server_address[1])
        return raw in {
            f"127.0.0.1:{port}",
            f"localhost:{port}",
            f"[::1]:{port}",
        }

    def _serve_asset(self, path: str) -> None:
        filename, content_type = _ASSETS[path]
        asset = files("agency_runtime.dashboard").joinpath(filename)
        data = asset.read_bytes()
        self.send_response(HTTPStatus.OK)
        self._send_security_headers(content_type=content_type, cache_control="no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_security_headers(self, *, content_type: str, cache_control: str) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", cache_control)
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        )
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        self.send_response(status)
        self._send_security_headers(
            content_type="application/json; charset=utf-8", cache_control="no-store"
        )
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_overview(self) -> None:
        stats = self.store.database_stats()
        activity = _dashboard_activity(self.store.recent_runtime_activity(limit=200))
        cfg = load_config()
        active = self.store.get_active_roster()
        self._json_ok(
            {
                **_live_overview(activity, stats),
                "roster_count": len(active),
                "retention_days": cfg.observability.retention_days,
                "capture_content": cfg.observability.capture_content,
                "counts": stats["tables"],
            }
        )

    def _handle_live(self) -> None:
        limit = _bounded_query_limit(self.path, default=100)
        activity = _dashboard_activity(self.store.recent_runtime_activity(limit=limit))
        core = {
            "schema_version": 1,
            "overview": _live_overview(activity, self.store.database_sizes()),
            "activity": activity,
        }
        self._json_ok(
            {
                "schema_version": core["schema_version"],
                "sampled_at": _utc_now(),
                "revision": _dashboard_revision(core),
                "overview": core["overview"],
                "activity": core["activity"],
            }
        )

    def _handle_activity(self) -> None:
        limit = _bounded_query_limit(self.path, default=50)
        self._json_ok(
            _dashboard_activity(self.store.recent_runtime_activity(limit=limit))
        )

    def _handle_hosts(self) -> None:
        inspector = self.server.host_inspector  # type: ignore[attr-defined]
        self._json_ok({"hosts": inspector()})

    def _handle_config(self) -> None:
        self._json_ok(_config_payload(read_config_state()))

    def _handle_config_update(self, body: dict[str, Any]) -> None:
        operations = body.get("operations")
        if not isinstance(operations, list):
            raise ValueError("operations must be a JSON array")
        confirmations = body.get("confirmations")
        if not isinstance(confirmations, list) or any(
            not isinstance(item, str) for item in confirmations
        ):
            raise ValueError("confirmations must be a JSON string array")
        missing = sorted(
            _required_config_confirmations(operations) - set(confirmations)
        )
        if missing:
            raise ValueError(f"missing confirmation phrase: {missing[0]}")
        result = apply_config_operations(
            operations,
            expected_revision=body.get("expected_revision"),
        )
        self._json_ok(
            _config_payload(
                result.state,
                changed_paths=result.changed_paths,
                restart_required_paths=result.restart_required,
                policy_enforced=result.policy_enforced,
            )
        )

    def _handle_route_lab(self, body: dict[str, Any]) -> None:
        task = str(body.get("task") or "").strip()
        if not task:
            raise ValueError("task is required")
        if len(task) > load_config().selector.max_user_msg_len:
            raise ValueError("task exceeds the configured maximum length")
        try:
            limit = max(1, min(int(body.get("limit", 10)), 50))
        except (TypeError, ValueError):
            limit = 10
        receipt = explain_route(
            str(body.get("session_id") or "dashboard"),
            task,
            self.store.get_active_roster_as_catalog(),
            limit=limit,
            store=self.store,
        )
        receipt["delegation_graph"] = _delegation_graph(receipt)
        self._json_ok(receipt)

    def _handle_trim(self, body: dict[str, Any]) -> None:
        if body.get("confirm") != "TRIM RUNTIME DATA":
            raise ValueError("confirmation phrase must be TRIM RUNTIME DATA")
        days = body.get("older_than_days", 30)
        if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 3650:
            raise ValueError("older_than_days must be an integer from 1 through 3650")
        dry_run = body.get("dry_run", False)
        vacuum = body.get("vacuum", False)
        if not isinstance(dry_run, bool):
            raise ValueError("dry_run must be a JSON boolean")
        if not isinstance(vacuum, bool):
            raise ValueError("vacuum must be a JSON boolean")
        result = self.store.trim_runtime_tables(
            older_than_days=days,
            dry_run=dry_run,
            vacuum=vacuum,
        )
        self._json_ok(result)

    def _handle_roster_action(self, body: dict[str, Any]) -> None:
        action = str(body.get("action") or "").strip().lower()
        snapshot_id = str(body.get("snapshot_id") or "").strip()
        if action not in {"approve", "activate"} or not snapshot_id:
            raise ValueError("action and snapshot_id are required")
        expected = f"{action.upper()} {snapshot_id}"
        if body.get("confirm") != expected:
            raise ValueError(f"confirmation phrase must be {expected}")
        if action == "approve":
            approve_snapshot(self.store, snapshot_id)
        else:
            activate_snapshot(self.store, snapshot_id)
        self._json_ok({"ok": True, "action": action, "snapshot_id": snapshot_id})

    def _handle_host_toggle(self, body: dict[str, Any]) -> None:
        from agency_runtime.core.installer import HOSTS, toggle_agency

        host = str(body.get("host") or "").strip().lower()
        if host not in HOSTS:
            raise ValueError(f"unknown host: {host or '<empty>'}")
        enabled = body.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be a JSON boolean")
        verb = "ENABLE" if enabled else "DISABLE"
        expected = f"{verb} {host}"
        if body.get("confirm") != expected:
            raise ValueError(f"confirmation phrase must be {expected}")
        result = toggle_agency(host, enabled=enabled)
        if result.get("ok"):
            _HOST_INSPECTIONS.invalidate(host)
        status = HTTPStatus.OK if result.get("ok") else HTTPStatus.CONFLICT
        self._send_json(status, result)


class DashboardHTTPServer(AgencyHTTPServer):
    """Agency server configured for authenticated dashboard traffic."""

    def __init__(
        self,
        store: Store,
        *,
        auth_token: str,
        host: str = "127.0.0.1",
        port: int = 0,
        host_inspector: Callable[[], list[dict[str, Any]]] | None = None,
    ) -> None:
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("the dashboard is loopback-only")
        self.auth_token = auth_token
        self.host_inspector = host_inspector or _HOST_INSPECTIONS.inspect
        super().__init__(
            store,
            host,
            port,
            handler_class=DashboardHTTPHandler,
            max_body_size=load_config().server.max_body_size,
        )


def run_dashboard(
    *,
    port: int = 0,
    db_path: str | Path | None = None,
    open_browser: bool = True,
    service_mode: bool = False,
    config_path: str | Path | None = None,
    home_dir: str | Path | None = None,
) -> None:
    """Start the local dashboard until interrupted."""
    if config_path is not None:
        os.environ["AGENCY_CONFIG_PATH"] = str(Path(config_path).expanduser())
        reset_config_cache()
    cfg = load_config()
    if service_mode and port == 0:
        port = cfg.dashboard.port
    store = Store(db_path) if db_path else Store()
    store.trim_runtime_tables(
        older_than_days=cfg.observability.retention_days,
        vacuum=False,
    )
    token = secrets.token_urlsafe(32)
    server = DashboardHTTPServer(store, auth_token=token, port=port)
    actual_port = int(server.server_address[1])
    url = f"http://127.0.0.1:{actual_port}/#token={token}"
    descriptor_written = False
    if service_mode:
        write_dashboard_runtime(
            token=token,
            port=actual_port,
            home_dir=home_dir,
        )
        descriptor_written = True
        logger.info("dashboard service listening on loopback port %d", actual_port)
    else:
        print(f"Agency Runtime dashboard: {url}")
        print("The access token is temporary and expires when this process stops.")
        if open_browser:
            webbrowser.open(url, new=2)

    previous_handlers: dict[int, Any] = {}
    if current_thread() is main_thread():

        def request_shutdown(_signum: int, _frame: Any) -> None:
            Thread(target=server.shutdown, daemon=True).start()

        for signum in (signal.SIGINT, signal.SIGTERM):
            try:
                previous_handlers[signum] = signal.getsignal(signum)
                signal.signal(signum, request_shutdown)
            except (AttributeError, OSError, ValueError):
                continue
    try:
        server.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        logger.info("dashboard shutdown requested")
    finally:
        server.server_close()
        for signum, previous in previous_handlers.items():
            try:
                signal.signal(signum, previous)
            except (OSError, ValueError):
                continue
        if descriptor_written:
            remove_dashboard_runtime(
                token=token,
                pid=os.getpid(),
                home_dir=home_dir,
            )


__all__ = ["DashboardHTTPHandler", "DashboardHTTPServer", "run_dashboard"]
