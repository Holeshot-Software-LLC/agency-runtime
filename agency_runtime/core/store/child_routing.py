"""Durable, content-free routing coordination for unplanned native children."""

from __future__ import annotations

import json
import time
import uuid
from contextlib import closing
from typing import Any

from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.store.schema import STORE_CLOCK_SQL

_MAX_CACHE_DOCUMENT_BYTES = 256 * 1024
_ZERO_TTL_COALESCING_GRACE_SECONDS = 1.0


def _cache_key(value: object) -> str:
    result = str(value or "").strip().casefold()
    if len(result) != 64 or any(character not in "0123456789abcdef" for character in result):
        raise ValueError("child routing cache key must be a SHA-256 digest")
    return result


class ChildRoutingStoreMixin:
    """Coordinate cache, singleflight leases, and parent-scoped call budgets."""

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
                try:
                    decision = json.loads(str(cached[0]))
                except (TypeError, ValueError):
                    conn.execute("DELETE FROM child_routing_cache WHERE cache_key = ?", (key,))
                else:
                    if isinstance(decision, dict):
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
        try:
            value = json.loads(str(row[0]))
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None

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
        document = json.dumps(decision, sort_keys=True, separators=(",", ":"))
        if len(document.encode("utf-8")) > _MAX_CACHE_DOCUMENT_BYTES:
            raise ValueError("child routing decision exceeds the cache limit")
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
