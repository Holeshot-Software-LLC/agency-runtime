"""Secure loopback-only operations dashboard for Agency Runtime."""

from __future__ import annotations

import errno
import hashlib
import json
import logging
import os
import re
import secrets
import signal
import webbrowser
from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from http import HTTPStatus
from importlib.resources import files
from pathlib import Path
from threading import RLock, Thread, current_thread, main_thread
from time import monotonic
from typing import Any
from urllib.parse import parse_qs, urlparse

from agency_runtime.core.agent_activation import (
    normalize_agent_slug,
    updated_disabled_agents,
)
from agency_runtime.core.cli_transport import discover_cli_models
from agency_runtime.core.config import load_config
from agency_runtime.core.configuration import (
    ConfigConflictError,
    ConfigState,
    ConfigurationError,
    apply_config_operations,
    config_read_lock,
    read_config_state,
    resolve_config_path,
)
from agency_runtime.core.dashboard_operational import (
    MAX_OPERATIONAL_ROSTER_RESULTS,
    MAX_RECENT_FAILURES,
    MAX_REVIEW_RESULTS,
    candidate_review_snapshot,
    inference_operational_snapshot,
    roster_operational_page,
)
from agency_runtime.core.dashboard_runtime import (
    remove_dashboard_runtime,
    write_dashboard_runtime,
)
from agency_runtime.core.dashboard_service_core import (
    dashboard_service_environment_error,
    dashboard_service_environment_overrides,
)
from agency_runtime.core.delegation.operational import (
    delegation_plan_projection,
    empty_delegation_plan_projection,
)
from agency_runtime.core.host_capabilities import (
    EXECUTION_HOSTS,
    project_host_capability_receipt,
)
from agency_runtime.core.host_control import HostControlConflictError
from agency_runtime.core.roster.inference import resolve_inference_audit_policy
from agency_runtime.core.roster.selector_projection import (
    selector_roster_projection,
    ui_roster_projection,
)
from agency_runtime.core.roster.sync import activate_snapshot, approve_snapshot
from agency_runtime.core.routing_snapshot import RoutingSnapshot, capture_routing_snapshot
from agency_runtime.core.runtime_control import (
    RuntimeControlConflictError,
    read_runtime_control,
    runtime_control_path,
    set_master_enabled,
)
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.selector.explain import explain_route
from agency_runtime.core.selector.policy import load_policy, policy_path_for_config
from agency_runtime.core.selector.receipt_projection import (
    RECEIPT_DESCRIPTION_BYTES,
    bounded_receipt_text,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.http import (
    AgencyHTTPHandler,
    AgencyHTTPServer,
    _bounded_roster_page,
)

logger = logging.getLogger("agency_runtime.server.dashboard")

_ASSETS: dict[str, tuple[str, str]] = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/charts.js": ("charts.js", "text/javascript; charset=utf-8"),
    "/dashboard-core.js": ("dashboard-core.js", "text/javascript; charset=utf-8"),
    "/dashboard-config.js": ("dashboard-config.js", "text/javascript; charset=utf-8"),
    "/dashboard-render.js": ("dashboard-render.js", "text/javascript; charset=utf-8"),
    "/dashboard-live.js": ("dashboard-live.js", "text/javascript; charset=utf-8"),
    "/dashboard-actions.js": ("dashboard-actions.js", "text/javascript; charset=utf-8"),
}

_HOST_INSPECTION_CACHE_SECONDS = 3.0
_HOST_INSPECTION_DEADLINE_SECONDS = 2.0
_ACTIVITY_NAMES = (
    "runs",
    "routing",
    "delegations",
    "receipts",
    "finalizations",
    "specialists",
)
_SPECIALIST_ACTIVITY_FIELDS = (
    "id",
    "session_id",
    "trace_id",
    "slug",
    "loaded_at",
    "expired_at",
    "state",
)
_BROKER_POLICY_RESPONSE_BYTES = 2 * 1024 * 1024 - 64 * 1024
_ROUTE_LAB_HOST_INVENTORY_LIMIT = len(EXECUTION_HOSTS) * 2
_ROUTE_LAB_REJECTION_LIMIT = 50
_ROUTE_LAB_REJECTION_TEXT_BYTES = 256
_EXPECTED_CLIENT_DISCONNECT_ERRNOS = frozenset(
    value
    for value in (
        getattr(errno, "ECONNABORTED", None),
        getattr(errno, "ECONNRESET", None),
        getattr(errno, "EPIPE", None),
        getattr(errno, "ESHUTDOWN", None),
        getattr(errno, "ENOTCONN", None),
    )
    if value is not None
)
_EXPECTED_CLIENT_DISCONNECT_WINERRORS = frozenset(
    {
        10053,  # WSAECONNABORTED
        10054,  # WSAECONNRESET
        10058,  # WSAESHUTDOWN
    }
)


def _is_expected_client_disconnect(exc: BaseException) -> bool:
    """Return whether response I/O failed because the client went away."""

    if isinstance(exc, (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)):
        return True
    if not isinstance(exc, OSError):
        return False
    return (
        exc.errno in _EXPECTED_CLIENT_DISCONNECT_ERRNOS
        or getattr(exc, "winerror", None) in _EXPECTED_CLIENT_DISCONNECT_WINERRORS
    )


class DashboardRestartRequiredError(RuntimeError):
    """Signal that this process no longer owns the configured Store identity."""

    def __init__(self, binding: dict[str, Any]) -> None:
        super().__init__("dashboard restart required: configured store path changed")
        self.binding = binding

    @property
    def payload(self) -> dict[str, Any]:
        return {
            "error": str(self),
            "restart_required": True,
            **self.binding,
        }


class _AgentToggleNoChange(Exception):
    """Carry the locked snapshot for a semantic no-op agent toggle."""

    def __init__(self, state: ConfigState, binding: Mapping[str, Any]) -> None:
        super().__init__("agent activation state is already current")
        self.state = state
        self.binding = dict(binding)


def _agent_lookup_slug(raw_path: str) -> str:
    """Return the one canonical slug accepted by the exact dashboard lookup."""

    try:
        query = parse_qs(
            urlparse(raw_path).query,
            keep_blank_values=True,
            max_num_fields=4,
        )
    except ValueError as exc:
        raise ValueError("invalid agent lookup query") from exc
    if set(query) != {"slug"} or len(query["slug"]) != 1:
        raise ValueError("agent lookup requires exactly one slug")
    raw_slug = query["slug"][0]
    slug = normalize_agent_slug(raw_slug)
    if raw_slug != slug:
        raise ValueError("agent lookup slug must be canonical")
    return slug


def _config_payload(
    state: ConfigState,
    *,
    changed_paths: tuple[str, ...] = (),
    restart_required_paths: tuple[str, ...] = (),
    policy_enforced: bool = False,
    service_binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a JSON-safe, credential-free configuration response."""

    payload = {
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
    if service_binding is not None:
        payload["service_binding"] = dict(service_binding)
    return payload


def _roster_revision(generation: int) -> str:
    return hashlib.sha256(f"agency.roster.v1:{generation}".encode()).hexdigest()


def _routing_catalog_revision(catalog: list[dict[str, Any]]) -> str:
    """Hash the exact selector catalog used by one routing operation."""

    encoder = json.JSONEncoder(
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256()
    for chunk in encoder.iterencode(catalog):
        digest.update(chunk.encode("utf-8"))
    return digest.hexdigest()


def _bounded_policy_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Reject a policy projection that cannot fit the authenticated wire cap."""

    encoded = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) > _BROKER_POLICY_RESPONSE_BYTES:
        raise ValueError("companion policy exceeds the broker response budget")
    return payload


def _absolute_runtime_path(value: object) -> Path:
    if not isinstance(value, (str, os.PathLike)):
        raise ConfigurationError("effective store path is invalid")
    return Path(os.path.abspath(Path(value).expanduser()))


def _store_service_binding(store: Store, state: ConfigState) -> dict[str, Any]:
    """Compare the process-frozen Store path with one config-state snapshot."""

    effective_store = state.effective.get("store")
    if not isinstance(effective_store, Mapping):
        raise ConfigurationError("effective store configuration is invalid")
    active_path = _absolute_runtime_path(store.db_path)
    desired_path = _absolute_runtime_path(effective_store.get("db_path"))
    config_derived = bool(getattr(store, "_store_path_config_derived", True))
    restart_required = config_derived and os.path.normcase(str(active_path)) != os.path.normcase(
        str(desired_path)
    )
    return {
        "store_path": str(active_path),
        "desired_store_path": str(desired_path),
        "store_restart_required": restart_required,
    }


def _require_store_service_binding(store: Store, state: ConfigState) -> dict[str, Any]:
    binding = _store_service_binding(store, state)
    if binding["store_restart_required"]:
        raise DashboardRestartRequiredError(binding)
    return binding


def _store_response_identity(
    state: ConfigState,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the shared credential-free identity carried by Store responses."""

    return {
        "config_path": str(state.path),
        "config_revision": state.revision,
        "environment_overrides": state.environment_overrides,
        **dict(binding),
    }


def _require_agent_toggle_precondition(
    store: Store,
    config_path: str | Path | None,
    slug: str,
    *,
    enabled: bool,
    confirmation: object,
    expected_disabled: tuple[str, ...],
) -> dict[str, Any]:
    """Bind a toggle to the locked config and active Store roster."""

    state = read_config_state(config_path)
    binding = _require_store_service_binding(store, state)
    if store.get_roster_entry(slug) is None:
        raise ValueError(f"agent is not present in the active roster: {slug}")
    verb = "ENABLE" if enabled else "DISABLE"
    expected_confirmation = f"{verb} {slug}"
    if confirmation != expected_confirmation:
        raise ValueError(f"confirmation phrase must be {expected_confirmation}")
    effective = state.effective.get("agents", {})
    disabled = effective.get("disabled", []) if isinstance(effective, dict) else []
    updated = updated_disabled_agents(disabled, slug, enabled=enabled)
    if updated != expected_disabled:
        raise ConfigConflictError("configuration changed; refresh before saving")
    if tuple(disabled) == updated:
        raise _AgentToggleNoChange(state, binding)
    return binding


def _activation_page_rows(
    rows: list[dict[str, Any]],
    disabled: frozenset[str],
) -> list[dict[str, Any]]:
    """Return the compact activation-list contract without routing taxonomy."""

    return [
        {key: projected[key] for key in ("agent_slug", "name", "division", "enabled", "protected")}
        for agent in rows
        for projected in (ui_roster_projection(agent, disabled),)
    ]


def _roster_projection_kind(raw_path: str) -> str:
    try:
        query = parse_qs(
            urlparse(raw_path).query,
            keep_blank_values=True,
            max_num_fields=16,
        )
    except ValueError as exc:
        raise ValueError("invalid roster query") from exc
    values = query.get("projection", [])
    allowed = {"activation"}
    if len(values) > 1 or (values and values[0] not in allowed):
        raise ValueError("roster projection must be activation when provided")
    return values[0] if values else "ui"


def _single_query_values(
    raw_path: str,
    *,
    allowed: frozenset[str],
    maximum_fields: int,
) -> dict[str, str]:
    """Parse one bounded, unambiguous query string for an operational API."""

    try:
        query = parse_qs(
            urlparse(raw_path).query,
            keep_blank_values=True,
            max_num_fields=maximum_fields,
        )
    except ValueError as exc:
        raise ValueError("invalid operational query") from exc
    if not set(query).issubset(allowed):
        raise ValueError("operational query contains unsupported fields")
    if any(len(values) != 1 for values in query.values()):
        raise ValueError("operational query fields must not be repeated")
    return {key: values[0] for key, values in query.items()}


def _strict_query_limit(
    values: Mapping[str, str],
    *,
    default: int,
    maximum: int,
    label: str,
) -> int:
    raw = values.get("limit", str(default))
    try:
        parsed = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an integer") from exc
    if not 1 <= parsed <= maximum:
        raise ValueError(f"{label} must be between 1 and {maximum}")
    return parsed


def _roster_operations_query(
    raw_path: str,
) -> tuple[int, str | None, dict[str, str]]:
    filter_fields = frozenset(
        {"query", "division", "capability", "authority", "host", "platform", "tool"}
    )
    values = _single_query_values(
        raw_path,
        allowed=filter_fields | {"limit", "after"},
        maximum_fields=10,
    )
    limit = _strict_query_limit(
        values,
        default=MAX_OPERATIONAL_ROSTER_RESULTS,
        maximum=MAX_OPERATIONAL_ROSTER_RESULTS,
        label="roster result limit",
    )
    after = values.pop("after", None)
    values.pop("limit", None)
    if after is not None:
        normalized = normalize_agent_slug(after)
        if normalized != after:
            raise ValueError("roster operations cursor must be canonical")
        after = normalized
    return limit, after, values


_REMEDIATION_CURSOR_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,511}\Z")


def _review_query(raw_path: str) -> tuple[int, str | None, str, str]:
    values = _single_query_values(
        raw_path,
        allowed=frozenset(
            {
                "limit",
                "candidate_id",
                "pending_cursor",
                "history_cursor",
            }
        ),
        maximum_fields=5,
    )
    limit = _strict_query_limit(
        values,
        default=25,
        maximum=MAX_REVIEW_RESULTS,
        label="candidate result limit",
    )
    candidate_id = values.get("candidate_id")
    cursors: list[str] = []
    for field in ("pending_cursor", "history_cursor"):
        value = values.get(field, "")
        if value and _REMEDIATION_CURSOR_RE.fullmatch(value) is None:
            raise ValueError(f"{field.replace('_', ' ')} is invalid")
        cursors.append(value)
    return limit, candidate_id or None, *cursors


def _inference_query_limit(raw_path: str) -> int:
    values = _single_query_values(
        raw_path,
        allowed=frozenset({"limit"}),
        maximum_fields=2,
    )
    return _strict_query_limit(
        values,
        default=MAX_RECENT_FAILURES,
        maximum=MAX_RECENT_FAILURES,
        label="failure result limit",
    )


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


def _unknown_host(host: str, *, status: str, error: str | None = None) -> dict[str, Any]:
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
        "maturity": "inspection-pending" if status == "timed_out" else "inspection-error",
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
        self._invalidated: set[str] = set()

    def _finished(self, host: str, future: Future[dict[str, Any]]) -> None:
        with self._lock:
            if self._in_flight.get(host) is not future:
                return
            if host in self._invalidated:
                self._in_flight.pop(host, None)
                self._invalidated.discard(host)
                return
        try:
            value = dict(future.result())
            value["host"] = host
            value["inspection_status"] = "complete"
            value["inspection_error"] = None
        except Exception as exc:  # native details remain in server logs
            logger.warning("host inspection failed for %s (%s)", host, type(exc).__name__)
            value = _unknown_host(
                host,
                status="error",
                error=f"inspection failed ({type(exc).__name__})",
            )
        with self._lock:
            if self._in_flight.get(host) is not future:
                return
            self._in_flight.pop(host, None)
            if host in self._invalidated:
                self._invalidated.discard(host)
                return
            self._cache[host] = (monotonic() + self.cache_seconds, value)

    def invalidate(self, host: str | None = None) -> None:
        """Discard cached and in-flight evidence after a native state change."""
        targets = self.hosts if host is None else (host,)
        with self._lock:
            for target in targets:
                self._cache.pop(target, None)
                future = self._in_flight.get(target)
                if future is not None:
                    self._invalidated.add(target)
                    cancelled = future.cancel()
                    # Production futures have callbacks, which synchronously
                    # remove a successfully cancelled future. Keep this fallback
                    # for injected executors/futures without callback support.
                    if cancelled and self._in_flight.get(target) is future:
                        self._in_flight.pop(target, None)
                        self._invalidated.discard(target)

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
                    future.add_done_callback(lambda item, name=host: self._finished(name, item))
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


def _route_lab_native_records(
    inspect_hosts: Callable[[], list[dict[str, Any]]],
) -> tuple[dict[str, dict[str, Any]], frozenset[str]]:
    """Return one bounded native record per canonical execution host.

    The dashboard inventory is trusted only as evidence input. Duplicate host
    identities are ambiguous and therefore cannot authorize Route Lab.
    """

    raw_records = inspect_hosts()
    if not isinstance(raw_records, list):
        raise RuntimeError("host inspection returned an invalid inventory")
    if len(raw_records) > _ROUTE_LAB_HOST_INVENTORY_LIMIT:
        raise RuntimeError("host inspection exceeded the supported inventory bound")
    records: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    for raw_record in raw_records:
        if not isinstance(raw_record, Mapping):
            continue
        raw_host = raw_record.get("host")
        if not isinstance(raw_host, str):
            continue
        host = raw_host.strip().casefold()
        if host not in EXECUTION_HOSTS:
            continue
        if host in records:
            duplicates.add(host)
            continue
        records[host] = dict(raw_record)
    return records, frozenset(duplicates)


def _route_lab_host_failure(
    status: Mapping[str, Any],
    capability_receipt: Mapping[str, Any] | None,
) -> str:
    """Project a bounded, credential-free host eligibility reason."""

    if capability_receipt is None:
        return "authoritative capability receipt is invalid"
    if status.get("effective_enabled") is False:
        return "host is not effectively enabled"
    if status.get("effective_enabled") is not True:
        return "host enablement is unproven"
    evidence = capability_receipt.get("evidence")
    if isinstance(evidence, list):
        bounded = [
            bounded_receipt_text(item, maximum_bytes=_ROUTE_LAB_REJECTION_TEXT_BYTES)
            for item in evidence[:4]
            if isinstance(item, str) and item.strip()
        ]
        if bounded:
            return ", ".join(bounded)
    return f"capability status is {capability_receipt.get('status', 'unknown')}"


def _route_lab_host_capability(
    store: Store,
    inspect_hosts: Callable[[], list[dict[str, Any]]],
    *,
    requested_host: object,
    global_enabled: bool,
) -> tuple[str, dict[str, Any]]:
    """Resolve one verified installed execution host for Route Lab.

    Callers may omit the host only when exactly one current, effectively
    enabled native installation can be derived. User input never supplies tool
    capabilities; the bounded installation receipt is the sole authority.
    """

    from agency_runtime.core.host_control import inspect_host_status

    if requested_host is None:
        normalized_requested = ""
    elif not isinstance(requested_host, str):
        raise ValueError("host must be a supported execution-host string")
    else:
        normalized_requested = requested_host.strip().casefold()
        if normalized_requested not in EXECUTION_HOSTS:
            expected = ", ".join(EXECUTION_HOSTS)
            raise ValueError(f"host must be one of: {expected}")

    records, duplicates = _route_lab_native_records(inspect_hosts)
    statuses: dict[str, tuple[dict[str, Any], dict[str, Any] | None]] = {}
    verified: list[str] = []
    for host in EXECUTION_HOSTS:
        if host in duplicates:
            continue
        status = inspect_host_status(
            store,
            host,
            native_record=records.get(host, {"host": host}),
            global_enabled=global_enabled,
        )
        capability_receipt = project_host_capability_receipt(status.get("execution_capabilities"))
        statuses[host] = (status, capability_receipt)
        if (
            capability_receipt is not None
            and capability_receipt.get("status") == "native-installation-verified"
            and capability_receipt.get("execution_host") == host
            and status.get("effective_enabled") is True
        ):
            verified.append(host)

    if normalized_requested:
        if normalized_requested in duplicates:
            raise ValueError(
                f"Route Lab cannot use {normalized_requested}: host inventory is ambiguous"
            )
        status, capability_receipt = statuses[normalized_requested]
        if normalized_requested not in verified or capability_receipt is None:
            reason = _route_lab_host_failure(status, capability_receipt)
            raise ValueError(f"Route Lab cannot use {normalized_requested}: {reason}")
        return normalized_requested, capability_receipt

    if not verified:
        expected = ", ".join(EXECUTION_HOSTS)
        raise ValueError(
            "Route Lab requires a verified and enabled execution host; "
            f"none is available ({expected})"
        )
    if len(verified) > 1:
        raise ValueError(
            "host is required when multiple verified execution hosts are available: "
            + ", ".join(verified)
        )
    selected_host = verified[0]
    capability_receipt = statuses[selected_host][1]
    if capability_receipt is None:  # pragma: no cover - guarded by ``verified``
        raise RuntimeError("verified Route Lab host lost its capability receipt")
    return selected_host, capability_receipt


def _route_lab_eligibility_projection(
    receipt: Mapping[str, Any],
    capability_receipt: Mapping[str, Any],
    *,
    catalog_size: int,
) -> dict[str, Any]:
    """Return a bounded projection of deterministic eligibility rejections."""

    routing = receipt.get("routing")
    raw_rejections = (
        routing.get("eligibility_rejections", []) if isinstance(routing, Mapping) else []
    )
    if not isinstance(raw_rejections, list):
        raw_rejections = []
    rejected: list[dict[str, str]] = []
    for item in raw_rejections[:_ROUTE_LAB_REJECTION_LIMIT]:
        if not isinstance(item, Mapping):
            continue
        slug = bounded_receipt_text(
            item.get("slug"),
            maximum_bytes=_ROUTE_LAB_REJECTION_TEXT_BYTES,
        )
        reason = bounded_receipt_text(
            item.get("reason"),
            maximum_bytes=_ROUTE_LAB_REJECTION_TEXT_BYTES,
        )
        if slug and reason:
            rejected.append({"slug": slug, "reason": reason})
    rejection_count = len(raw_rejections)
    return {
        "execution_host": capability_receipt["execution_host"],
        "capability_status": capability_receipt["status"],
        "eligible_count": max(0, catalog_size - rejection_count),
        "rejection_count": rejection_count,
        "rejections": rejected,
        "truncated": rejection_count > len(rejected),
    }


def _provider_health(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize observed model receipts without claiming a live health probe."""
    observed: dict[str, dict[str, Any]] = {}
    successful = {"success", "completed", "ok"}
    failed = {"failed", "failure", "error", "cancelled", "timed_out", "timeout"}
    for receipt in receipts:
        provider = str(receipt.get("resolved_provider") or "unresolved").strip() or "unresolved"
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

    return {name: len(activity.get(name, [])) for name in _ACTIVITY_NAMES}


def _dashboard_activity(
    activity: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Strip optional captured detail from dashboard activity responses."""

    rendered: dict[str, list[dict[str, Any]]] = {}
    for name in _ACTIVITY_NAMES:
        rows = activity.get(name, [])
        if name == "specialists":
            rendered[name] = [
                {key: row[key] for key in _SPECIALIST_ACTIVITY_FIELDS if key in row} for row in rows
            ]
            continue
        excluded = (
            "skip_reason" if name == "delegations" else "work_units" if name == "routing" else None
        )
        if excluded is not None and any(excluded in row for row in rows):
            rendered[name] = [
                {key: value for key, value in row.items() if key != excluded} for row in rows
            ]
        else:
            rendered[name] = rows
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
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
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

    @property
    def config_path(self) -> Path:
        """Return the immutable configuration identity owned by this server."""

        return self.server.config_path  # type: ignore[attr-defined]

    @property
    def runtime_control_path(self) -> Path:
        """Return the immutable master-switch identity owned by this server."""

        return self.server.runtime_control_path  # type: ignore[attr-defined]

    def _master_control(self) -> dict[str, Any]:
        """Read master state through the authenticated writer's strict boundary.

        The effective-state adapter is for untrusted consumer sandboxes and
        requires a restricted caller to have no mutation rights.  This service
        intentionally owns those rights so it can broker compare-and-swap
        updates; its immutable server-bound path still receives the complete
        owner-private and identity validation performed by the strict reader.
        """

        return read_runtime_control(path=self.runtime_control_path)

    def _close_expected_client_disconnect(self, exc: BaseException) -> bool:
        """Close one abandoned connection without turning it into a server fault."""

        if not _is_expected_client_disconnect(exc):
            return False
        self.close_connection = True
        return True

    def handle_one_request(self) -> None:
        """Keep expected response-I/O disconnects out of socketserver error logs."""

        try:
            super().handle_one_request()
        except OSError as exc:
            if not self._close_expected_client_disconnect(exc):
                raise

    def do_OPTIONS(self) -> None:
        self._json_error(HTTPStatus.METHOD_NOT_ALLOWED, "cross-origin requests are not allowed")

    def do_GET(self) -> None:
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
            handler = {
                "/api/live": self._handle_live,
                "/api/overview": self._handle_overview,
                "/api/roster": self._handle_roster,
                "/api/roster/operations": self._handle_roster_operations,
                "/api/roster/reviews": self._handle_roster_reviews,
                "/api/agents/lookup": self._handle_agent_lookup,
                "/api/activity": self._handle_activity,
                "/api/hosts": self._handle_hosts,
                "/api/inference": self._handle_inference,
                "/api/runtime": lambda: self._json_ok({"master": self._master_control()}),
                "/api/config": self._handle_config,
                "/api/providers/models": self._handle_provider_models,
                "/api/health": lambda: self._json_ok({"status": "ok"}),
                "/api/snapshots": self._handle_snapshots,
                "/api/policy": self._handle_policy,
            }.get(path)
            if handler is None:
                self._json_error(HTTPStatus.NOT_FOUND, f"unknown path: {path}")
            else:
                handler()
        except DashboardRestartRequiredError as exc:
            self._send_json(HTTPStatus.CONFLICT, exc.payload)
        except ConfigConflictError as exc:
            self._json_error(HTTPStatus.CONFLICT, str(exc))
        except ConfigurationError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
        except (KeyError, ValueError, RuntimeError) as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:  # defensive boundary; details stay in logs
            if self._close_expected_client_disconnect(exc):
                return
            logger.exception("dashboard GET failed for %s (%s)", path, type(exc).__name__)
            self._json_error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal server error")

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if not path.startswith("/api/"):
            self._json_error(HTTPStatus.NOT_FOUND, f"unknown path: {path}")
            return
        if not self._authorise_api_request(require_json=True):
            return
        try:
            body = self._read_json_body()
            if body is None:
                return
            handler = {
                "/api/route": self._handle_route_lab,
                "/api/search": self._handle_search_broker,
                "/api/maintenance/trim": self._handle_trim,
                "/api/roster/action": self._handle_roster_action,
                "/api/hosts/toggle": self._handle_host_toggle,
                "/api/agents/toggle": self._handle_agent_toggle,
                "/api/runtime/toggle": self._handle_runtime_toggle,
                "/api/config": self._handle_config_update,
            }.get(path)
            if handler is None:
                self._json_error(HTTPStatus.NOT_FOUND, f"unknown path: {path}")
            else:
                handler(body)
        except DashboardRestartRequiredError as exc:
            self._send_json(HTTPStatus.CONFLICT, exc.payload)
        except ConfigConflictError as exc:
            self._json_error(HTTPStatus.CONFLICT, str(exc))
        except RuntimeControlConflictError as exc:
            self._json_error(HTTPStatus.CONFLICT, str(exc))
        except HostControlConflictError as exc:
            self._json_error(HTTPStatus.CONFLICT, str(exc))
        except ConfigurationError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
        except (KeyError, ValueError, RuntimeError) as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:  # defensive boundary; details stay in logs
            if self._close_expected_client_disconnect(exc):
                return
            logger.exception("dashboard POST failed for %s (%s)", path, type(exc).__name__)
            self._json_error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal server error")

    def _authorise_api_request(self, *, require_json: bool = False) -> bool:
        if not self._valid_host_header():
            self._json_error(HTTPStatus.BAD_REQUEST, "invalid Host header")
            return False

        origin = self.headers.get("Origin")
        if origin:
            expected_origin = f"http://{self.headers.get('Host', '')}"
            if origin.rstrip("/").lower() != expected_origin.rstrip("/").lower():
                self._json_error(HTTPStatus.FORBIDDEN, "cross-origin requests are not allowed")
                return False

        supplied = self.headers.get("Authorization", "")
        expected = f"Bearer {self.auth_token}"
        if (
            len(supplied) > 8192
            or not supplied.isascii()
            or len(expected) > 8192
            or not expected.isascii()
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
            "default-src 'self'; base-uri 'none'; object-src 'none'; "
            "script-src 'self'; style-src 'self'; connect-src 'self'; "
            "frame-ancestors 'none'; form-action 'self'",
        )
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")

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
        self._send_security_headers(
            content_type="application/json; charset=utf-8", cache_control="no-store"
        )
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_overview(self) -> None:
        stats = self.store.database_stats()
        activity = _dashboard_activity(self.store.recent_dashboard_activity(limit=200))
        cfg = load_config(self.config_path)
        state = read_config_state(self.config_path)
        binding = _store_service_binding(self.store, state)
        self._json_ok(
            {
                **_live_overview(activity, stats),
                "inference": inference_operational_snapshot(cfg, activity),
                "roster_count": self.store.count_enabled_roster(),
                "retention_days": cfg.observability.retention_days,
                "capture_content": cfg.observability.capture_content,
                "counts": stats["tables"],
                "master": self._master_control(),
                "service_binding": binding,
                **_store_response_identity(state, binding),
            }
        )

    def _handle_live(self) -> None:
        state = read_config_state(self.config_path)
        binding = _store_service_binding(self.store, state)
        limit = _bounded_query_limit(self.path, default=100)
        activity = _dashboard_activity(self.store.recent_dashboard_activity(limit=limit))
        inference = inference_operational_snapshot(
            load_config(self.config_path),
            activity,
            failure_limit=min(limit, MAX_RECENT_FAILURES),
        )
        core = {
            "schema_version": 1,
            "overview": {
                **_live_overview(activity, self.store.database_sizes()),
                "inference": inference,
            },
            "activity": activity,
            "master": self._master_control(),
        }
        self._json_ok(
            {
                "schema_version": core["schema_version"],
                "sampled_at": _utc_now(),
                "revision": _dashboard_revision(core),
                "overview": core["overview"],
                "activity": core["activity"],
                "master": core["master"],
                "service_binding": binding,
                **_store_response_identity(state, binding),
            }
        )

    def _handle_activity(self) -> None:
        state = read_config_state(self.config_path)
        binding = _store_service_binding(self.store, state)
        limit = _bounded_query_limit(self.path, default=50)
        self._json_ok(
            {
                **_dashboard_activity(self.store.recent_dashboard_activity(limit=limit)),
                "service_binding": binding,
                **_store_response_identity(state, binding),
            }
        )

    def _handle_snapshots(self) -> None:
        state = read_config_state(self.config_path)
        binding = _require_store_service_binding(self.store, state)
        effective = state.effective.get("agents", {})
        disabled = (
            frozenset(effective.get("disabled", [])) if isinstance(effective, dict) else frozenset()
        )
        operations = roster_operational_page(
            self.store,
            disabled_agents=disabled,
        )
        reviews = candidate_review_snapshot(self.store)
        self._json_ok(
            {
                "snapshots": self.store.list_roster_snapshots(),
                "operations": operations,
                "reviews": reviews,
                "service_binding": binding,
                **_store_response_identity(state, binding),
            }
        )

    def _handle_roster_operations(self) -> None:
        limit, after, filters = _roster_operations_query(self.path)
        state = read_config_state(self.config_path)
        binding = _require_store_service_binding(self.store, state)
        effective = state.effective.get("agents", {})
        disabled = (
            frozenset(effective.get("disabled", [])) if isinstance(effective, dict) else frozenset()
        )
        operations = roster_operational_page(
            self.store,
            disabled_agents=disabled,
            filters=filters,
            limit=limit,
            after=after,
        )
        self._json_ok(
            {
                **operations,
                "roster_revision": _roster_revision(operations["roster_generation"]),
                **_store_response_identity(state, binding),
            }
        )

    def _handle_roster_reviews(self) -> None:
        limit, candidate_id, pending_cursor, history_cursor = _review_query(self.path)
        state = read_config_state(self.config_path)
        binding = _require_store_service_binding(self.store, state)
        self._json_ok(
            {
                **candidate_review_snapshot(
                    self.store,
                    limit=limit,
                    candidate_id=candidate_id,
                    pending_cursor=pending_cursor,
                    history_cursor=history_cursor,
                ),
                **_store_response_identity(state, binding),
            }
        )

    def _handle_inference(self) -> None:
        limit = _inference_query_limit(self.path)
        state = read_config_state(self.config_path)
        binding = _require_store_service_binding(self.store, state)
        activity = _dashboard_activity(self.store.recent_dashboard_activity(limit=max(limit, 50)))
        self._json_ok(
            {
                **inference_operational_snapshot(
                    load_config(self.config_path),
                    activity,
                    failure_limit=limit,
                ),
                **_store_response_identity(state, binding),
            }
        )

    def _handle_hosts(self) -> None:
        from agency_runtime.core.host_control import inspect_host_status

        state = read_config_state(self.config_path)
        binding = _require_store_service_binding(self.store, state)
        inspector = self.server.host_inspector  # type: ignore[attr-defined]
        master = self._master_control()
        global_enabled = bool(master["enabled"])
        hosts = [
            inspect_host_status(
                self.store,
                str(item.get("host") or ""),
                native_record=item,
                global_enabled=global_enabled,
            )
            for item in inspector()
        ]
        self._json_ok(
            {
                "hosts": hosts,
                "master": master,
                **_store_response_identity(state, binding),
            }
        )

    def _handle_runtime_toggle(self, body: dict[str, Any]) -> None:
        """Apply the authenticated global master switch with generation CAS."""

        enabled = body.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be a JSON boolean")
        expected_generation = body.get("expected_generation")
        if (
            isinstance(expected_generation, bool)
            or not isinstance(expected_generation, int)
            or expected_generation < 0
        ):
            raise ValueError("expected_generation must be a non-negative integer")
        expected_confirmation = "ENABLE AGENCY" if enabled else "DISABLE AGENCY"
        if body.get("confirm") != expected_confirmation:
            raise ValueError(f"confirmation phrase must be {expected_confirmation}")
        before = self._master_control()
        updated = set_master_enabled(
            enabled,
            expected_generation=expected_generation,
            source="dashboard",
            path=self.runtime_control_path,
        )
        self._json_ok(
            {
                "ok": True,
                "changed": updated != before,
                "master": updated,
            }
        )

    def _handle_roster(self) -> None:
        """Return preserved definitions plus reversible activation state."""

        try:
            limit, after = _bounded_roster_page(self.path)
            projection = _roster_projection_kind(self.path)
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        state = read_config_state(self.config_path)
        binding = _require_store_service_binding(self.store, state)
        effective = state.effective.get("agents", {})
        disabled = (
            frozenset(effective.get("disabled", [])) if isinstance(effective, dict) else frozenset()
        )
        if projection == "activation":
            page_limit = limit
            snapshot = self.store.get_active_roster_activation_page_snapshot(
                limit=page_limit,
                after=after,
                disabled_agents=disabled,
            )
        else:
            page_limit = limit
            snapshot = self.store.get_active_roster_ui_page_snapshot(
                limit=page_limit,
                after=after,
                disabled_agents=disabled,
            )
        page = snapshot["rows"]
        if projection == "activation":
            roster = _activation_page_rows(page[:page_limit], disabled)
        else:
            roster = [ui_roster_projection(agent, disabled) for agent in page[:page_limit]]
        truncated = len(page) > len(roster)
        total_count = int(snapshot["total_count"])
        enabled_count = int(snapshot["enabled_count"])
        self._json_ok(
            {
                "agents": roster,
                "count": len(roster),
                "total_count": total_count,
                "enabled_count": enabled_count,
                "disabled_count": total_count - enabled_count,
                "limit": page_limit,
                "truncated": truncated,
                "next_cursor": roster[-1]["agent_slug"] if truncated else None,
                "config_path": str(state.path),
                "config_revision": state.revision,
                "environment_overrides": state.environment_overrides,
                "roster_revision": _roster_revision(int(snapshot["generation"])),
                "projection": projection,
                **binding,
            }
        )

    def _handle_agent_lookup(self) -> None:
        """Return one governed roster definition without materializing its prompt."""

        try:
            slug = _agent_lookup_slug(self.path)
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        state = read_config_state(self.config_path)
        binding = _require_store_service_binding(self.store, state)
        effective = state.effective.get("agents", {})
        disabled = (
            frozenset(effective.get("disabled", [])) if isinstance(effective, dict) else frozenset()
        )
        snapshot = self.store.get_active_roster_entry_snapshot(
            slug,
            disabled_agents=disabled,
        )
        roster = [selector_roster_projection(agent, disabled) for agent in snapshot["rows"]]
        total_count = int(snapshot["total_count"])
        enabled_count = int(snapshot["enabled_count"])
        self._json_ok(
            {
                "agents": roster,
                "count": len(roster),
                "total_count": total_count,
                "enabled_count": enabled_count,
                "disabled_count": total_count - enabled_count,
                "limit": 1,
                "truncated": False,
                "next_cursor": None,
                "filter_slug": slug,
                "config_path": str(state.path),
                "config_revision": state.revision,
                "environment_overrides": state.environment_overrides,
                "roster_revision": _roster_revision(int(snapshot["generation"])),
                "projection": "selector",
                **binding,
            }
        )

    def _handle_config(self) -> None:
        state = read_config_state(self.config_path)
        self._json_ok(
            _config_payload(
                state,
                service_binding=_store_service_binding(self.store, state),
            )
        )

    def _handle_provider_models(self) -> None:
        query = parse_qs(urlparse(self.path).query, keep_blank_values=False)
        transport = str((query.get("transport") or ["codex"])[0]).strip().casefold()
        refresh = str((query.get("refresh") or [""])[0]).strip().casefold() in {
            "1",
            "true",
        }
        self._json_ok(discover_cli_models(transport, refresh=refresh).as_dict())

    def _routing_operation_snapshot(self) -> tuple[RoutingSnapshot, dict[str, Any]]:
        """Freeze config, Store binding, and catalog identity for one operation."""

        with config_read_lock(self.config_path):
            before = read_config_state(self.config_path)
            binding = _require_store_service_binding(self.store, before)
            snapshot = capture_routing_snapshot(self.store)
            after = read_config_state(self.config_path)
            if (
                before.path != after.path
                or before.revision != after.revision
                or before.environment_overrides != after.environment_overrides
            ):
                raise ConfigConflictError("configuration changed while routing snapshot loaded")
            if resolve_config_path(snapshot.config.config_path) != self.config_path:
                raise ConfigurationError("routing snapshot configuration identity is invalid")
            agents = after.effective.get("agents")
            disabled = agents.get("disabled") if isinstance(agents, Mapping) else None
            if not isinstance(disabled, list) or frozenset(disabled) != frozenset(
                snapshot.config.agents.disabled
            ):
                raise ConfigConflictError("routing snapshot activation policy is inconsistent")
        return snapshot, {
            "config_path": str(after.path),
            "config_revision": after.revision,
            "store_path": str(binding["store_path"]),
            "roster_revision": _routing_catalog_revision(snapshot.catalog),
            "environment_overrides": after.environment_overrides,
        }

    def _handle_policy(self) -> None:
        """Return a credential-free bounded policy projection for CLI brokerage."""

        snapshot, identity = self._routing_operation_snapshot()
        policy = load_policy(policy_path_for_config(snapshot.config))
        policy_revision = hashlib.sha256(
            json.dumps(
                policy,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        self._json_ok(
            _bounded_policy_response(
                {
                    "schema_version": "agency.policy_snapshot.v1",
                    "policy": policy,
                    "active_slugs": sorted(
                        str(agent.get("slug") or "")
                        for agent in snapshot.catalog
                        if str(agent.get("slug") or "")
                    ),
                    "operation_snapshot": identity,
                    "policy_revision": policy_revision,
                }
            )
        )

    def _handle_config_update(self, body: dict[str, Any]) -> None:
        operations = body.get("operations")
        if not isinstance(operations, list):
            raise ValueError("operations must be a JSON array")
        confirmations = body.get("confirmations")
        if not isinstance(confirmations, list) or any(
            not isinstance(item, str) for item in confirmations
        ):
            raise ValueError("confirmations must be a JSON string array")
        missing = sorted(_required_config_confirmations(operations) - set(confirmations))
        if missing:
            raise ValueError(f"missing confirmation phrase: {missing[0]}")
        result = apply_config_operations(
            operations,
            expected_revision=body.get("expected_revision"),
            path=self.config_path,
        )
        self._json_ok(
            _config_payload(
                result.state,
                changed_paths=result.changed_paths,
                restart_required_paths=result.restart_required,
                policy_enforced=result.policy_enforced,
                service_binding=_store_service_binding(self.store, result.state),
            )
        )

    def _handle_agent_toggle(self, body: dict[str, Any]) -> None:
        """Persist one quick activation toggle through the config CAS writer."""

        slug = normalize_agent_slug(body.get("slug"))
        enabled = body.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be a JSON boolean")
        state = read_config_state(self.config_path)
        # Fail fast on an already-stale service, then repeat this proof inside
        # the writer lock before any toggle can be committed.
        _require_store_service_binding(self.store, state)
        effective = state.effective.get("agents", {})
        disabled = effective.get("disabled", []) if isinstance(effective, dict) else []
        updated = updated_disabled_agents(disabled, slug, enabled=enabled)
        if body.get("expected_revision") != state.revision:
            raise ConfigConflictError("configuration changed; refresh before saving")
        binding: dict[str, Any] = {}

        def locked_precondition() -> None:
            binding.update(
                _require_agent_toggle_precondition(
                    self.store,
                    self.config_path,
                    slug,
                    enabled=enabled,
                    confirmation=body.get("confirm"),
                    expected_disabled=updated,
                )
            )

        try:
            result = apply_config_operations(
                [{"op": "set", "path": "agents.disabled", "value": list(updated)}],
                expected_revision=state.revision,
                path=self.config_path,
                locked_precondition=locked_precondition,
            )
        except _AgentToggleNoChange as no_change:
            self._json_ok(
                {
                    "ok": True,
                    "slug": slug,
                    "enabled": enabled,
                    "changed": False,
                    "config": _config_payload(
                        no_change.state,
                        service_binding=no_change.binding,
                    ),
                    **no_change.binding,
                }
            )
            return
        self._json_ok(
            {
                "ok": True,
                "slug": slug,
                "enabled": enabled,
                "changed": bool(result.changed_paths),
                "config": _config_payload(
                    result.state,
                    changed_paths=result.changed_paths,
                    restart_required_paths=result.restart_required,
                    policy_enforced=result.policy_enforced,
                    service_binding=binding,
                ),
                **binding,
            }
        )

    def _handle_route_lab(self, body: dict[str, Any]) -> None:
        task = body.get("task")
        if not isinstance(task, str) or not task.strip():
            raise ValueError("task is required")
        limit = body.get("limit", 10)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise ValueError("limit must be an integer from 1 through 50")
        session_id = body.get("session_id", "dashboard")
        if not isinstance(session_id, str):
            raise ValueError("session_id must be a string")
        master = self._master_control()
        if not master["enabled"]:
            self._json_ok(
                {
                    "schema_version": "agency.selection_explain.v1",
                    "session_id": session_id,
                    "task": task,
                    "routing": {
                        "runtime_enabled": False,
                        "bypassed": True,
                        "trace_id": "",
                        "selected_ids": [],
                        "semantic_ids": [],
                        "confidence": 0.0,
                        "latency_ms": 0,
                        "status": "bypassed",
                        "source": "master_control",
                        "provider": "master_control",
                    },
                    "selected": [],
                    "considered_candidates": [],
                    "rejected_candidates": [],
                    "signals": {"source": "master_control"},
                    "delegation_plan": empty_delegation_plan_projection(),
                    "delegation_graph": {"nodes": [], "edges": []},
                    "runtime_enabled": False,
                    "status": "disabled",
                    "bypassed": True,
                    "message": "Agency Runtime is disabled; Route Lab bypassed routing.",
                    "master": master,
                }
            )
            return
        snapshot, identity = self._routing_operation_snapshot()
        if len(task) > snapshot.config.selector.max_user_msg_len:
            raise ValueError("task exceeds the configured maximum length")
        requested_host = body.get("host")
        execution_host, capability_receipt = _route_lab_host_capability(
            self.store,
            self.server.host_inspector,  # type: ignore[attr-defined]
            requested_host=requested_host,
            global_enabled=True,
        )
        receipt = explain_route(
            session_id,
            task,
            snapshot.catalog,
            config=snapshot.config,
            limit=limit,
            store=self.store,
            host=execution_host,
            platform=str(capability_receipt["platform"]),
            available_tools=tuple(capability_receipt["capabilities"]),
            capability_receipt=capability_receipt,
        )
        eligibility = _route_lab_eligibility_projection(
            receipt,
            capability_receipt,
            catalog_size=len(snapshot.catalog),
        )
        routing = receipt.get("routing")
        if isinstance(routing, dict):
            routing["eligibility_rejections"] = list(eligibility["rejections"])
            routing["eligibility_rejection_count"] = eligibility["rejection_count"]
            routing["eligibility_rejections_truncated"] = eligibility["truncated"]
        receipt["host_capability_receipt"] = capability_receipt
        receipt["eligibility"] = {
            **eligibility,
            "host_resolution": "explicit" if requested_host is not None else "derived",
        }
        receipt["delegation_plan"] = delegation_plan_projection(
            receipt,
            catalog=snapshot.catalog,
            config=snapshot.config,
            execution_host=execution_host,
            capability_receipt=capability_receipt,
        )
        receipt["delegation_graph"] = _delegation_graph(receipt)
        receipt["operation_snapshot"] = identity
        self._json_ok(receipt)

    def _handle_search_broker(self, body: dict[str, Any]) -> None:
        """Search full selector metadata but return only bounded result summaries."""

        query = body.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query is required")
        limit = body.get("limit", 10)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("limit must be an integer from 1 through 100")
        master = self._master_control()
        if not master["enabled"]:
            self._json_ok(
                {
                    "schema_version": "agency.search.v1",
                    "query": query,
                    "agents": [],
                    "count": 0,
                    "runtime_enabled": False,
                    "status": "disabled",
                    "bypassed": True,
                    "message": "Agency Runtime is disabled; search was bypassed.",
                    "master": master,
                }
            )
            return
        snapshot, identity = self._routing_operation_snapshot()
        if len(query) > snapshot.config.selector.max_user_msg_len:
            raise ValueError("query exceeds the configured maximum length")
        candidates, scores = pre_narrow(query, snapshot.catalog, limit=limit)
        agents = [
            {
                "slug": str(agent.get("slug") or ""),
                "name": str(agent.get("name") or ""),
                "division": str(agent.get("division") or ""),
                "description": bounded_receipt_text(
                    agent.get("description"),
                    maximum_bytes=RECEIPT_DESCRIPTION_BYTES,
                ),
                "score": round(float(score), 4),
            }
            for agent, score in zip(candidates, scores, strict=True)
        ]
        self._json_ok(
            {
                "schema_version": "agency.search.v1",
                "query": query,
                "agents": agents,
                "count": len(agents),
                "operation_snapshot": identity,
            }
        )

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
        with config_read_lock(self.config_path):
            state = read_config_state(self.config_path)
            binding = _require_store_service_binding(self.store, state)
            result = self.store.trim_runtime_tables(
                older_than_days=days,
                dry_run=dry_run,
                vacuum=vacuum,
            )
        self._json_ok(
            {
                **result,
                **_store_response_identity(state, binding),
            }
        )

    def _handle_roster_action(self, body: dict[str, Any]) -> None:
        action = str(body.get("action") or "").strip().lower()
        snapshot_id = str(body.get("snapshot_id") or "").strip()
        if action not in {"approve", "activate"} or not snapshot_id:
            raise ValueError("action and snapshot_id are required")
        expected = f"{action.upper()} {snapshot_id}"
        if body.get("confirm") != expected:
            raise ValueError(f"confirmation phrase must be {expected}")
        with config_read_lock(self.config_path):
            state = read_config_state(self.config_path)
            binding = _require_store_service_binding(self.store, state)
            inference_required = resolve_inference_audit_policy(
                load_config(self.config_path)
            ).required
            if action == "approve":
                approve_snapshot(
                    self.store,
                    snapshot_id,
                    require_inference=inference_required,
                )
            else:
                activate_snapshot(
                    self.store,
                    snapshot_id,
                    require_inference=inference_required,
                )
        self._json_ok(
            {
                "ok": True,
                "action": action,
                "snapshot_id": snapshot_id,
                "config_path": str(state.path),
                "config_revision": state.revision,
                **binding,
            }
        )

    def _handle_host_toggle(self, body: dict[str, Any]) -> None:
        from agency_runtime.core.host_control import (
            SUPPORTED_HOSTS,
            inspect_host_status,
            set_runtime_control,
        )

        host = str(body.get("host") or "").strip().lower()
        if host not in SUPPORTED_HOSTS:
            raise ValueError(f"unknown host: {host or '<empty>'}")
        enabled = body.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be a JSON boolean")
        expected_generation = body.get("expected_generation")
        if (
            isinstance(expected_generation, bool)
            or not isinstance(expected_generation, int)
            or expected_generation < 0
        ):
            raise ValueError("expected_generation must be a non-negative integer")
        verb = "ENABLE" if enabled else "DISABLE"
        expected = f"{verb} {host}"
        if body.get("confirm") != expected:
            raise ValueError(f"confirmation phrase must be {expected}")
        with config_read_lock(self.config_path):
            state = read_config_state(self.config_path)
            binding = _require_store_service_binding(self.store, state)
            control = set_runtime_control(
                self.store,
                host,
                enabled=enabled,
                source="dashboard",
                expected_generation=expected_generation,
            )
        inspector = self.server.host_inspector  # type: ignore[attr-defined]
        native = next(
            (item for item in inspector() if item.get("host") == host),
            {"host": host},
        )
        master = self._master_control()
        result = inspect_host_status(
            self.store,
            host,
            native_record=native,
            global_enabled=bool(master["enabled"]),
        )
        self._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                **control,
                "status": result,
                **_store_response_identity(state, binding),
            },
        )


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
        config_path: str | Path | None = None,
        runtime_control_home: str | Path | None = None,
    ) -> None:
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("the dashboard is loopback-only")
        store_config_path = getattr(store, "config_path", None)
        if store_config_path is None:
            raise ValueError("dashboard Store must have a configuration identity")
        selected_config_path = store_config_path if config_path is None else config_path
        canonical_config_path = resolve_config_path(selected_config_path)
        if resolve_config_path(store_config_path) != canonical_config_path:
            raise ValueError("dashboard Store and configuration paths must match")
        self.auth_token = auth_token
        self.host_inspector = host_inspector or _HOST_INSPECTIONS.inspect
        self.config_path = canonical_config_path
        self.runtime_control_path = runtime_control_path(home_dir=runtime_control_home)
        super().__init__(
            store,
            host,
            port,
            handler_class=DashboardHTTPHandler,
            max_body_size=load_config(canonical_config_path).server.max_body_size,
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
    canonical_config_path = resolve_config_path(config_path)
    cfg = load_config(canonical_config_path)
    if service_mode and (environment_names := dashboard_service_environment_overrides(cfg)):
        raise RuntimeError(dashboard_service_environment_error(environment_names))
    if service_mode and port == 0:
        port = cfg.dashboard.port
    store = (
        Store(db_path, config_path=canonical_config_path)
        if db_path is not None
        else Store(config_path=canonical_config_path)
    )
    token = secrets.token_urlsafe(32)
    server = DashboardHTTPServer(
        store,
        auth_token=token,
        port=port,
        config_path=canonical_config_path,
        runtime_control_home=home_dir,
    )
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

    def maintain_retention() -> None:
        try:
            store.trim_runtime_tables(
                older_than_days=cfg.observability.retention_days,
                vacuum=False,
            )
        except Exception as exc:
            logger.warning(
                "dashboard retention maintenance failed: %s",
                type(exc).__name__,
            )

    maintenance = Thread(
        target=maintain_retention,
        daemon=True,
        name="agency-dashboard-retention",
    )
    maintenance.start()

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
        maintenance.join(timeout=0.5)
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
