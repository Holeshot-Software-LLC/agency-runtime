"""Run, receipt, host-control, and delegation persistence methods."""

from __future__ import annotations

from typing import Any

from agency_runtime.core.store.projections import (
    RUN_CONTENT_LIMIT as _RUN_CONTENT_LIMIT,
)
from agency_runtime.core.store.projections import (
    project_delegation_detail,
    project_run_metadata,
    redact_sensitive_text,
    sanitize_api_base,
)


class EvidenceStoreMixin:
    """Evidence-domain behavior composed into the canonical SQLite store."""

    # ── Host runtime controls ─────────────────────────────────────

    def get_host_control(self, host: str) -> dict[str, Any]:
        """Return persistent soft-control state without mutating the store."""
        normalized = str(host or "").strip().lower()
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT host, enabled, updated_at, source FROM host_controls WHERE host = ?",
                (normalized,),
            ).fetchone()
            if row is None:
                return {
                    "host": normalized,
                    "enabled": True,
                    "updated_at": None,
                    "source": "default",
                }
            return {
                "host": str(row["host"]),
                "enabled": bool(row["enabled"]),
                "updated_at": str(row["updated_at"]),
                "source": str(row["source"]),
            }
        finally:
            conn.close()

    def set_host_control(
        self, host: str, *, enabled: bool, source: str = "runtime"
    ) -> dict[str, Any]:
        """Persist a host soft-control setting and return its read-back value."""
        normalized = str(host or "").strip().lower()
        if not normalized:
            raise ValueError("host is required")
        normalized_source = str(source or "runtime").strip()[:96] or "runtime"
        updated_at = self._now()
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO host_controls (host, enabled, updated_at, source) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(host) DO UPDATE SET enabled = excluded.enabled, "
                "updated_at = excluded.updated_at, source = excluded.source",
                (normalized, int(bool(enabled)), updated_at, normalized_source),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_host_control(normalized)

    def get_host_canary_attestation(self, host: str) -> dict[str, Any] | None:
        """Return the latest content-free canary attestation for a host."""
        normalized = str(host or "").strip().lower()
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT host, profile_scope, platform_system, platform_release, platform_machine, "
                "host_version, plugin_version, install_id, bundle_digest, "
                "passed_at, trace_id "
                "FROM host_canary_attestations WHERE host = ?",
                (normalized,),
            ).fetchone()
            return dict(row) if row is not None else None
        finally:
            conn.close()

    def record_host_canary_attestation(
        self,
        *,
        host: str,
        profile_scope: str,
        platform_system: str,
        platform_release: str,
        platform_machine: str,
        host_version: str,
        plugin_version: str,
        install_id: str,
        bundle_digest: str,
        trace_id: str,
        passed_at: str | None = None,
    ) -> dict[str, Any]:
        """Persist one bounded successful canary without prompts or output."""
        values = {
            "host": str(host or "").strip().lower()[:64],
            "profile_scope": str(profile_scope or "").strip().lower()[:64],
            "platform_system": str(platform_system or "").strip()[:64],
            "platform_release": str(platform_release or "").strip()[:128],
            "platform_machine": str(platform_machine or "").strip()[:128],
            "host_version": str(host_version or "").strip()[:256],
            "plugin_version": str(plugin_version or "").strip()[:64],
            "install_id": str(install_id or "").strip()[:128],
            "bundle_digest": str(bundle_digest or "").strip()[:128],
            "trace_id": str(trace_id or "").strip()[:512],
            "passed_at": str(passed_at or self._now()).strip()[:64],
        }
        if any(not values[key] for key in values):
            raise ValueError("complete host canary attestation fields are required")
        if values["profile_scope"] not in {"current-profile", "isolated-profile"}:
            raise ValueError("profile_scope must be current-profile or isolated-profile")
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO host_canary_attestations "
                "(host, profile_scope, platform_system, platform_release, platform_machine, "
                "host_version, plugin_version, install_id, bundle_digest, "
                "passed_at, trace_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(host) DO UPDATE SET "
                "profile_scope = excluded.profile_scope, "
                "platform_system = excluded.platform_system, "
                "platform_release = excluded.platform_release, "
                "platform_machine = excluded.platform_machine, "
                "host_version = excluded.host_version, "
                "plugin_version = excluded.plugin_version, "
                "install_id = excluded.install_id, "
                "bundle_digest = excluded.bundle_digest, "
                "passed_at = excluded.passed_at, trace_id = excluded.trace_id",
                (
                    values["host"],
                    values["profile_scope"],
                    values["platform_system"],
                    values["platform_release"],
                    values["platform_machine"],
                    values["host_version"],
                    values["plugin_version"],
                    values["install_id"],
                    values["bundle_digest"],
                    values["passed_at"],
                    values["trace_id"],
                ),
            )
            conn.commit()
        finally:
            conn.close()
        attestation = self.get_host_canary_attestation(values["host"])
        if attestation is None:
            raise RuntimeError("canary attestation postcondition failed")
        return attestation

    def clear_host_canary_attestation(self, host: str) -> bool:
        """Invalidate a host attestation after rollback or lifecycle replacement."""
        normalized = str(host or "").strip().lower()
        conn = self._connect()
        try:
            cursor = conn.execute(
                "DELETE FROM host_canary_attestations WHERE host = ?",
                (normalized,),
            )
            conn.commit()
            return bool(cursor.rowcount)
        finally:
            conn.close()

    # ── Runs ───────────────────────────────────────────────────────

    def create_run(
        self,
        *,
        trace_id: str,
        session_id: str = "",
        host: str = "unknown",
        user_message: str = "",
        metadata: dict | None = None,
    ) -> str:
        capture_content = self._capture_content_enabled()
        trace_id = trace_id or self._uuid()
        run_id = self._uuid()
        captured_message = (
            redact_sensitive_text(user_message, _RUN_CONTENT_LIMIT) if capture_content else ""
        )
        safe_metadata = project_run_metadata(metadata)
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO runs (id, trace_id, session_id, host, started_at, status, user_message, metadata) "
                "VALUES (?, ?, ?, ?, ?, 'active', ?, ?) "
                "ON CONFLICT(trace_id) DO UPDATE SET "
                "session_id = excluded.session_id, host = excluded.host, "
                "started_at = excluded.started_at, ended_at = NULL, status = 'active', "
                "user_message = excluded.user_message, metadata = excluded.metadata",
                (
                    run_id,
                    trace_id,
                    session_id,
                    host,
                    self._now(),
                    captured_message,
                    safe_metadata,
                ),
            )
            row = conn.execute("SELECT id FROM runs WHERE trace_id = ?", (trace_id,)).fetchone()
            conn.commit()
            return str(row["id"])
        finally:
            conn.close()

    def complete_run(self, run_id: str, status: str = "completed") -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE runs SET ended_at = ?, status = ? WHERE id = ?",
                (self._now(), status, run_id),
            )
            conn.commit()
        finally:
            conn.close()

    # ── Model receipts ─────────────────────────────────────────────

    def record_model_receipt(
        self,
        *,
        trace_id: str,
        session_id: str = "",
        host: str = "unknown",
        requested_model: str = "",
        model_group: str = "",
        resolved_provider: str = "",
        resolved_model: str = "",
        api_base: str = "",
        attempted_fallbacks: int = 0,
        model_id: str = "",
        source: str = "unknown",
        started_at: str = "",
        ended_at: str = "",
        status: str = "success",
    ) -> str:
        receipt_id = self._uuid()
        trace_id = trace_id or receipt_id
        safe_api_base = sanitize_api_base(api_base)
        conn = self._connect()
        try:
            self._ensure_run(conn, trace_id=trace_id, session_id=session_id, host=host)
            conn.execute(
                "INSERT INTO model_receipts "
                "(id, trace_id, session_id, host, requested_model, model_group, "
                "resolved_provider, resolved_model, api_base, attempted_fallbacks, "
                "model_id, source, started_at, ended_at, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    receipt_id,
                    trace_id,
                    session_id,
                    host,
                    requested_model,
                    model_group,
                    resolved_provider,
                    resolved_model,
                    safe_api_base,
                    attempted_fallbacks,
                    model_id,
                    source,
                    started_at or self._now(),
                    ended_at or self._now(),
                    status,
                ),
            )
            conn.commit()
            return receipt_id
        finally:
            conn.close()

    def get_model_receipt(self, trace_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM model_receipts WHERE trace_id = ? ORDER BY id DESC LIMIT 1",
                (trace_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_model_receipt_for_session(self, session_id: str) -> dict[str, Any] | None:
        """Get the most recent model receipt for a session."""
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM model_receipts WHERE session_id = ? "
                "ORDER BY ended_at DESC, started_at DESC, id DESC LIMIT 1",
                (session_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ── Skills ─────────────────────────────────────────────────────

    def record_skill_loaded(self, session_id: str, skill_name: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO skills_loaded (id, session_id, skill_name, loaded_at) "
                "VALUES (?, ?, ?, ?)",
                (self._uuid(), session_id, skill_name, self._now()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_skills_for_session(self, session_id: str) -> list[str]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT skill_name FROM skills_loaded WHERE session_id = ? ORDER BY loaded_at",
                (session_id,),
            )
            return [row["skill_name"] for row in cur.fetchall()]
        finally:
            conn.close()

    # ── Specialists ────────────────────────────────────────────────

    def record_specialist_loaded(self, session_id: str, agent_slug: str) -> None:
        if not session_id or not agent_slug:
            return
        conn = self._connect()
        try:
            existing = conn.execute(
                "SELECT 1 FROM specialists_loaded WHERE session_id = ? AND agent_slug = ? LIMIT 1",
                (session_id, agent_slug),
            ).fetchone()
            if existing:
                return
            conn.execute(
                "INSERT INTO specialists_loaded (id, session_id, agent_slug, loaded_at) "
                "VALUES (?, ?, ?, ?)",
                (self._uuid(), session_id, agent_slug, self._now()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_specialists_for_session(self, session_id: str) -> list[str]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT agent_slug FROM specialists_loaded WHERE session_id = ? ORDER BY loaded_at",
                (session_id,),
            )
            return [row["agent_slug"] for row in cur.fetchall()]
        finally:
            conn.close()

    # ── Delegation events ──────────────────────────────────────────

    def record_delegation(
        self,
        *,
        trace_id: str,
        session_id: str = "",
        host: str = "unknown",
        work_unit_id: str = "",
        recommended_agent: str = "",
        status: str = "suggested",
        backend: str = "",
        skip_reason: str = "",
        error: str = "",
    ) -> str:
        event_id = self._uuid()
        trace_id = trace_id or event_id
        capture_content = self._capture_content_enabled()
        safe_skip_reason = project_delegation_detail(
            skip_reason,
            field="skip_reason",
            capture_content=capture_content,
        )
        safe_error = project_delegation_detail(
            error,
            field="error",
            capture_content=capture_content,
        )
        conn = self._connect()
        try:
            self._ensure_run(conn, trace_id=trace_id, session_id=session_id, host=host)
            conn.execute(
                "INSERT INTO delegation_events "
                "(id, trace_id, session_id, host, work_unit_id, recommended_agent, "
                "status, backend, skip_reason, error, started_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    trace_id,
                    session_id,
                    host,
                    work_unit_id,
                    recommended_agent,
                    status,
                    backend,
                    safe_skip_reason,
                    safe_error,
                    self._now(),
                ),
            )
            conn.commit()
            return event_id
        finally:
            conn.close()

    def update_delegation(
        self,
        event_id: str,
        *,
        status: str,
        backend: str = "",
        error: str = "",
        recommended_agent: str = "",
        skip_reason: str = "",
        host: str = "",
    ) -> None:
        capture_content = self._capture_content_enabled()
        safe_skip_reason = project_delegation_detail(
            skip_reason,
            field="skip_reason",
            capture_content=capture_content,
        )
        safe_error = project_delegation_detail(
            error,
            field="error",
            capture_content=capture_content,
        )
        conn = self._connect()
        try:
            ended = self._now() if status in ("completed", "failed", "skipped") else None
            conn.execute(
                "UPDATE delegation_events "
                "SET status = ?, "
                "host = COALESCE(NULLIF(?, ''), host), "
                "backend = COALESCE(NULLIF(?, ''), backend), "
                "error = ?, "
                "recommended_agent = COALESCE(NULLIF(?, ''), recommended_agent), "
                "skip_reason = COALESCE(NULLIF(?, ''), skip_reason), "
                "completed_at = COALESCE(?, completed_at) "
                "WHERE id = ?",
                (
                    status,
                    host,
                    backend,
                    safe_error,
                    recommended_agent,
                    safe_skip_reason,
                    ended,
                    event_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_delegations(self, trace_id: str) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM delegation_events WHERE trace_id = ? ORDER BY started_at",
                (trace_id,),
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_delegations_for_session(
        self, session_id: str, statuses: list[str] | tuple[str, ...] | None = None
    ) -> list[dict[str, Any]]:
        """Return delegation events for a session, optionally filtered by status."""
        conn = self._connect()
        try:
            if statuses:
                placeholders = ",".join("?" for _ in statuses)
                # SQL text added here consists only of parameter placeholders.
                cur = conn.execute(
                    f"SELECT * FROM delegation_events WHERE session_id = ? AND status IN ({placeholders}) ORDER BY started_at",  # nosec B608
                    (session_id, *statuses),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM delegation_events WHERE session_id = ? ORDER BY started_at",
                    (session_id,),
                )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()
