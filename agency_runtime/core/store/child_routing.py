"""Durable, content-free routing coordination for unplanned native children."""

from __future__ import annotations

import hmac
import json
import secrets
import time
import uuid
from contextlib import closing
from hashlib import sha256
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.store.schema import STORE_CLOCK_SQL

_MAX_CACHE_DOCUMENT_BYTES = 256 * 1024
_ZERO_TTL_COALESCING_GRACE_SECONDS = 1.0
_MAX_PARENT_SCOPE_TOKEN_CHARS = 256
_MAX_PARENT_SCOPE_TTL_SECONDS = 600
_STORE_UNIX_SQL = "CAST(STRFTIME('%s', 'NOW') AS INTEGER)"


def _decode_cache_decision(value: object) -> dict[str, Any] | None:
    if not isinstance(value, (str, bytes)) or not value:
        return None
    try:
        parsed = safe_load_bounded_json(
            value,
            maximum_bytes=_MAX_CACHE_DOCUMENT_BYTES,
            maximum_depth=32,
            maximum_nodes=50_000,
        )
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _cache_key(value: object) -> str:
    result = str(value or "").strip().casefold()
    if len(result) != 64 or any(character not in "0123456789abcdef" for character in result):
        raise ValueError("child routing cache key must be a SHA-256 digest")
    return result


class ChildRoutingStoreMixin:
    """Coordinate cache, singleflight leases, and parent-scoped call budgets."""

    def create_native_child_parent_scope(
        self,
        *,
        host: str,
        parent_session_id: str,
        parent_trace_id: str,
        work_unit_id: str,
        worker_kind: str,
        worker_id: str,
        native_run_id: str,
        child_session_id: str,
        ttl_seconds: int = _MAX_PARENT_SCOPE_TTL_SECONDS,
    ) -> dict[str, Any]:
        """Issue one bounded bearer receipt for an explicit child preflight."""

        normalized_host = str(host or "").strip().casefold()
        if normalized_host not in {"codex", "claude"}:
            raise ValueError("native child parent scope host is unsupported")
        parent_session = validate_correlation_id(
            parent_session_id,
            field="parent_session_id",
        )
        parent_trace = validate_correlation_id(parent_trace_id, field="parent_trace_id")
        unit = validate_correlation_id(
            work_unit_id,
            field="work_unit_id",
            required=False,
        )
        if len(unit) > 160:
            raise ValueError("work_unit_id exceeds the 160-character limit")
        if str(worker_kind or "").strip() != "generic-worker":
            raise ValueError("native child parent scope requires generic-worker identity")
        worker = validate_correlation_id(worker_id, field="worker_id")
        native = validate_correlation_id(native_run_id, field="native_run_id")
        child_session = validate_correlation_id(child_session_id, field="child_session_id")
        if len(worker) > 256 or len(native) > 256:
            raise ValueError("native child identity exceeds the 256-character limit")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int):
            raise ValueError("native child parent scope TTL must be an integer")
        if not 1 <= ttl_seconds <= _MAX_PARENT_SCOPE_TTL_SECONDS:
            raise ValueError(
                "native child parent scope TTL must be between 1 and "
                f"{_MAX_PARENT_SCOPE_TTL_SECONDS}"
            )
        token = secrets.token_urlsafe(32)
        token_hash = sha256(token.encode("ascii")).hexdigest()
        scope_id = str(uuid.uuid4())
        with closing(self._connect()) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                clock = conn.execute(
                    f"SELECT {_STORE_UNIX_SQL} AS unix_time"  # nosec B608
                ).fetchone()
                issued_unix = int(clock["unix_time"])
                parent = conn.execute(
                    "SELECT status, preflight_state FROM runs "
                    "WHERE session_id = ? AND trace_id = ? LIMIT 1",
                    (parent_session, parent_trace),
                ).fetchone()
                if (
                    parent is None
                    or str(parent["status"] or "") not in {"active", "evidence_only"}
                    or str(parent["preflight_state"] or "") != "ready"
                ):
                    raise ValueError(
                        "native child parent scope requires one ready active parent turn"
                    )
                prior = conn.execute(
                    "SELECT id, consumed_at, expires_unix, child_session_id, "
                    "child_trace_id FROM native_child_parent_scopes "
                    "WHERE host = ? AND parent_trace_id = ? AND worker_id = ? "
                    "AND native_run_id = ? LIMIT 1",
                    (normalized_host, parent_trace, worker, native),
                ).fetchone()
                if prior is not None:
                    child_status = None
                    if prior["consumed_at"] is not None and prior["child_trace_id"]:
                        child = conn.execute(
                            "SELECT status FROM runs WHERE session_id = ? AND trace_id = ? LIMIT 1",
                            (str(prior["child_session_id"]), str(prior["child_trace_id"])),
                        ).fetchone()
                        child_status = str(child["status"] or "") if child is not None else ""
                    replaceable = int(prior["expires_unix"]) < issued_unix or (
                        prior["consumed_at"] is not None and child_status == "preflight_failed"
                    )
                    if not replaceable:
                        raise ValueError(
                            "native child parent scope already exists for this exact child"
                        )
                    conn.execute(
                        "DELETE FROM native_child_parent_scopes WHERE id = ?",
                        (str(prior["id"]),),
                    )
                conn.execute(
                    "INSERT INTO native_child_parent_scopes "
                    "(id, token_hash, host, parent_session_id, parent_trace_id, "
                    "work_unit_id, worker_kind, worker_id, native_run_id, "
                    "child_session_id, child_trace_id, issued_unix, expires_unix, "
                    f"created_at, consumed_at, consumed_unix) VALUES "  # nosec B608
                    f"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, "  # nosec B608
                    f"{STORE_CLOCK_SQL}, NULL, NULL)",  # nosec B608
                    (
                        scope_id,
                        token_hash,
                        normalized_host,
                        parent_session,
                        parent_trace,
                        unit,
                        "generic-worker",
                        worker,
                        native,
                        child_session,
                        issued_unix,
                        issued_unix + ttl_seconds,
                    ),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {
            "parent_scope_token": token,
            "host": normalized_host,
            "parent_session_id": parent_session,
            "parent_trace_id": parent_trace,
            "work_unit_id": unit,
            "worker_kind": "generic-worker",
            "worker_id": worker,
            "native_run_id": native,
            "child_session_id": child_session,
            "expires_unix": issued_unix + ttl_seconds,
        }

    def consume_native_child_parent_scope(
        self,
        *,
        parent_scope_token: str,
        host: str,
        child_session_id: str,
        child_trace_id: str,
    ) -> dict[str, Any]:
        """Consume one exact parent scope atomically in a later process."""

        token = str(parent_scope_token or "").strip()
        if not token or len(token) > _MAX_PARENT_SCOPE_TOKEN_CHARS:
            raise ValueError("parent_scope_token is invalid")
        normalized_host = str(host or "").strip().casefold()
        if normalized_host not in {"codex", "claude"}:
            raise ValueError("native child parent scope host is unsupported")
        child_session = validate_correlation_id(child_session_id, field="child_session_id")
        child_trace = validate_correlation_id(child_trace_id, field="child_trace_id")
        token_hash = sha256(token.encode("utf-8", errors="surrogatepass")).hexdigest()
        with closing(self._connect()) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                rows = conn.execute(
                    "SELECT scope.*, run.status AS parent_status, "
                    "run.preflight_state AS parent_preflight_state, "
                    f"{_STORE_UNIX_SQL} AS store_now_unix "  # nosec B608
                    "FROM native_child_parent_scopes AS scope JOIN runs AS run "
                    "ON run.trace_id = scope.parent_trace_id "
                    "AND run.session_id = scope.parent_session_id "
                    "WHERE scope.token_hash = ? AND scope.host = ? "
                    "AND scope.child_session_id = ? AND scope.consumed_at IS NULL "
                    "ORDER BY scope.rowid LIMIT 2",
                    (token_hash, normalized_host, child_session),
                ).fetchall()
                if len(rows) != 1 or not hmac.compare_digest(
                    str(rows[0]["token_hash"] or ""),
                    token_hash,
                ):
                    raise ValueError(
                        "native child parent scope is invalid, ambiguous, or already consumed"
                    )
                scope = rows[0]
                store_now = int(scope["store_now_unix"])
                if (
                    str(scope["parent_status"] or "") not in {"active", "evidence_only"}
                    or str(scope["parent_preflight_state"] or "") != "ready"
                    or store_now < int(scope["issued_unix"])
                    or store_now > int(scope["expires_unix"])
                ):
                    raise ValueError(
                        "native child parent scope is expired or its parent is not ready"
                    )
                live_scopes = conn.execute(
                    "SELECT COUNT(*) AS count FROM native_child_parent_scopes "
                    "WHERE host = ? AND child_session_id = ? AND consumed_at IS NULL "
                    "AND issued_unix <= ? AND expires_unix >= ?",
                    (normalized_host, child_session, store_now, store_now),
                ).fetchone()
                if live_scopes is None or int(live_scopes["count"]) != 1:
                    raise ValueError(
                        "native child parent scope is invalid, ambiguous, or already consumed"
                    )
                consumed = conn.execute(
                    "UPDATE native_child_parent_scopes SET "
                    f"consumed_at = {STORE_CLOCK_SQL}, consumed_unix = ?, "  # nosec B608
                    "child_trace_id = ? WHERE id = ? AND consumed_at IS NULL "
                    "AND consumed_unix IS NULL AND child_trace_id = '' "
                    "AND issued_unix <= ? AND expires_unix >= ?",
                    (
                        store_now,
                        child_trace,
                        scope["id"],
                        store_now,
                        store_now,
                    ),
                )
                if consumed.rowcount != 1:
                    raise ValueError(
                        "native child parent scope is invalid, expired, or already consumed"
                    )
                conn.commit()
                return {
                    "host": str(scope["host"]),
                    "parent_session_id": str(scope["parent_session_id"]),
                    "parent_trace_id": str(scope["parent_trace_id"]),
                    "work_unit_id": str(scope["work_unit_id"]),
                    "worker_kind": str(scope["worker_kind"]),
                    "worker_id": str(scope["worker_id"]),
                    "native_run_id": str(scope["native_run_id"]),
                    "child_session_id": str(scope["child_session_id"]),
                    "child_trace_id": child_trace,
                }
            except Exception:
                conn.rollback()
                raise

    def restore_native_child_parent_scope_after_failed_preflight(
        self,
        *,
        parent_scope_token: str,
        host: str,
        child_session_id: str,
        child_trace_id: str,
    ) -> None:
        """Restore one consumed receipt only when its child preflight did not succeed."""

        token = str(parent_scope_token or "").strip()
        if not token or len(token) > _MAX_PARENT_SCOPE_TOKEN_CHARS:
            raise ValueError("parent_scope_token is invalid")
        normalized_host = str(host or "").strip().casefold()
        if normalized_host not in {"codex", "claude"}:
            raise ValueError("native child parent scope host is unsupported")
        child_session = validate_correlation_id(child_session_id, field="child_session_id")
        child_trace = validate_correlation_id(child_trace_id, field="child_trace_id")
        token_hash = sha256(token.encode("utf-8", errors="surrogatepass")).hexdigest()
        with closing(self._connect()) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT id, token_hash FROM native_child_parent_scopes "
                    "WHERE token_hash = ? AND host = ? AND child_session_id = ? "
                    "AND child_trace_id = ? AND consumed_at IS NOT NULL "
                    "AND consumed_unix IS NOT NULL LIMIT 1",
                    (token_hash, normalized_host, child_session, child_trace),
                ).fetchone()
                if row is None or not hmac.compare_digest(str(row["token_hash"] or ""), token_hash):
                    raise ValueError("native child parent scope cannot be retried")
                child = conn.execute(
                    "SELECT status FROM runs WHERE session_id = ? AND trace_id = ? LIMIT 1",
                    (child_session, child_trace),
                ).fetchone()
                if child is not None and str(child["status"] or "") != "preflight_failed":
                    raise ValueError("successful native child parent scope cannot be retried")
                restored = conn.execute(
                    "UPDATE native_child_parent_scopes SET consumed_at = NULL, "
                    "consumed_unix = NULL, child_trace_id = '' WHERE id = ? "
                    "AND consumed_at IS NOT NULL AND consumed_unix IS NOT NULL "
                    "AND child_trace_id = ?",
                    (str(row["id"]), child_trace),
                )
                if restored.rowcount != 1:
                    raise ValueError("native child parent scope cannot be retried")
                conn.commit()
            except BaseException:
                conn.rollback()
                raise

    def reserve_child_routing(
        self,
        *,
        parent_session_id: str,
        parent_trace_id: str,
        cache_key: str,
        budget: int,
        concurrency: int,
        lease_seconds: float = 65.0,
    ) -> dict[str, Any]:
        session = validate_correlation_id(parent_session_id, field="parent_session_id")
        trace = validate_correlation_id(parent_trace_id, field="parent_trace_id")
        key = _cache_key(cache_key)
        if isinstance(budget, bool) or not 0 <= int(budget) <= 256:
            raise ValueError("child routing inference budget is invalid")
        if isinstance(concurrency, bool) or not 1 <= int(concurrency) <= 32:
            raise ValueError("child routing inference concurrency is invalid")
        now = time.time()
        owner_token = str(uuid.uuid4())
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM child_routing_cache WHERE expires_at <= ?", (now,))
            conn.execute("DELETE FROM child_routing_leases WHERE expires_at <= ?", (now,))
            cached = conn.execute(
                "SELECT decision FROM child_routing_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()
            if cached is not None:
                decision = _decode_cache_decision(cached[0])
                if decision is None:
                    conn.execute("DELETE FROM child_routing_cache WHERE cache_key = ?", (key,))
                else:
                    return {"status": "cached", "decision": decision}
            existing = conn.execute(
                "SELECT 1 FROM child_routing_leases WHERE cache_key = ?",
                (key,),
            ).fetchone()
            if existing is not None:
                return {"status": "coalescing"}
            usage = conn.execute(
                "SELECT inference_calls FROM child_routing_usage WHERE parent_trace_id = ?",
                (trace,),
            ).fetchone()
            calls = int(usage[0]) if usage is not None else 0
            if calls >= int(budget):
                return {"status": "budget_exhausted", "inference_calls": calls}
            active = conn.execute(
                "SELECT COUNT(*) FROM child_routing_leases WHERE parent_trace_id = ?",
                (trace,),
            ).fetchone()
            if int(active[0] if active is not None else 0) >= int(concurrency):
                return {"status": "concurrency_exhausted", "inference_calls": calls}
            conn.execute(
                "INSERT INTO child_routing_leases "
                "(cache_key, parent_trace_id, owner_token, expires_at, created_at) "
                f"VALUES (?, ?, ?, ?, {STORE_CLOCK_SQL})",
                (key, trace, owner_token, now + max(1.0, min(float(lease_seconds), 120.0))),
            )
            conn.execute(
                "INSERT INTO child_routing_usage "
                "(parent_trace_id, parent_session_id, inference_calls, updated_at) "
                f"VALUES (?, ?, 1, {STORE_CLOCK_SQL}) "
                "ON CONFLICT(parent_trace_id) DO UPDATE SET "
                "inference_calls = child_routing_usage.inference_calls + 1, "
                "parent_session_id = excluded.parent_session_id, "
                f"updated_at = {STORE_CLOCK_SQL}",
                (trace, session),
            )
        return {"status": "owner", "owner_token": owner_token, "inference_calls": calls + 1}

    def read_child_routing_cache(self, cache_key: str) -> dict[str, Any] | None:
        key = _cache_key(cache_key)
        with closing(self._connect()) as conn, conn:
            row = conn.execute(
                "SELECT decision FROM child_routing_cache WHERE cache_key = ? AND expires_at > ?",
                (key, time.time()),
            ).fetchone()
        if row is None:
            return None
        return _decode_cache_decision(row[0])

    def renew_child_routing(
        self,
        *,
        cache_key: str,
        owner_token: str,
        lease_seconds: float,
    ) -> bool:
        """Extend one live lease without changing its owner or inference budget."""

        key = _cache_key(cache_key)
        token = validate_correlation_id(owner_token, field="owner_token")
        extension = max(1.0, min(float(lease_seconds), 120.0))
        with closing(self._connect()) as conn, conn:
            updated = conn.execute(
                "UPDATE child_routing_leases SET expires_at = ? "
                "WHERE cache_key = ? AND owner_token = ? AND expires_at > ?",
                (time.time() + extension, key, token, time.time()),
            ).rowcount
        return bool(updated)

    def complete_child_routing(
        self,
        *,
        cache_key: str,
        owner_token: str,
        decision: dict[str, Any],
        ttl_seconds: int,
    ) -> bool:
        key = _cache_key(cache_key)
        token = validate_correlation_id(owner_token, field="owner_token")
        try:
            document = json.dumps(
                decision,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("child routing decision is invalid") from exc
        if len(document.encode("utf-8")) > _MAX_CACHE_DOCUMENT_BYTES:
            raise ValueError("child routing decision exceeds the cache limit")
        if _decode_cache_decision(document) is None:
            raise ValueError("child routing decision exceeds the structural limits")
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            lease = conn.execute(
                "SELECT 1 FROM child_routing_leases WHERE cache_key = ? AND owner_token = ?",
                (key, token),
            ).fetchone()
            if lease is None:
                return False
            configured_ttl = int(ttl_seconds)
            effective_ttl = (
                min(configured_ttl, 86400)
                if configured_ttl > 0
                else _ZERO_TTL_COALESCING_GRACE_SECONDS
            )
            conn.execute(
                "INSERT INTO child_routing_cache (cache_key, decision, expires_at, created_at) "
                f"VALUES (?, ?, ?, {STORE_CLOCK_SQL}) ON CONFLICT(cache_key) DO UPDATE SET "
                "decision = excluded.decision, expires_at = excluded.expires_at, "
                "created_at = excluded.created_at",
                (key, document, time.time() + effective_ttl),
            )
            conn.execute(
                "DELETE FROM child_routing_leases WHERE cache_key = ? AND owner_token = ?",
                (key, token),
            )
        return True

    def abort_child_routing(self, *, cache_key: str, owner_token: str) -> None:
        key = _cache_key(cache_key)
        token = validate_correlation_id(owner_token, field="owner_token")
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "DELETE FROM child_routing_leases WHERE cache_key = ? AND owner_token = ?",
                (key, token),
            )
