"""Content-free native child lifecycle persistence.

The host owns worker scheduling.  Agency records only stable identities,
timestamps, terminal outcome, and the reciprocal delegation link; prompts and
worker output never enter this projection.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from agency_runtime.core.codex_child_tool_evidence import (
    CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SCHEMA,
    CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SOURCE,
    decode_stored_codex_child_tool_evidence,
    encode_codex_child_tool_evidence,
)
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.delegation_status import (
    MAX_DELEGATION_BACKEND_CHARS,
    MAX_DELEGATION_HOST_CHARS,
    MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
    MAX_DELEGATION_WORK_UNIT_ID_CHARS,
    MAX_DELEGATION_WORKER_ID_CHARS,
)
from agency_runtime.core.store.projections import project_delegation_detail
from agency_runtime.core.store.schema import STORE_CLOCK_SQL
from agency_runtime.core.store.workforce import record_native_assignment_outcome

_OUTCOME_EXIT_CODES = {
    "ok": 0,
    "error": 1,
    "timeout": 124,
    "killed": 130,
    "reset": 130,
    "deleted": 130,
    "unknown": 1,
}
_EXIT_CODE_OUTCOMES = {
    0: "ok",
    1: "error",
    124: "timeout",
    130: "killed",
}


def _identity(value: object, *, maximum: int, field: str) -> str:
    normalized = validate_correlation_id(value, field=field)
    if len(normalized) > maximum:
        raise ValueError(f"{field} exceeds the {maximum}-character limit")
    return normalized


def _worker_run_id(
    host: str,
    session_id: str,
    trace_id: str,
    worker_id: str,
    native_run_id: str,
) -> str:
    framed = bytearray(b"agency-runtime:native-child-run:v2\0")
    for value in (host, session_id, trace_id, worker_id, native_run_id):
        encoded = value.encode("utf-8")
        framed.extend(len(encoded).to_bytes(4, byteorder="big"))
        framed.extend(encoded)
    return f"native-child:{sha256(framed).hexdigest()}"


class NativeChildStoreMixin:
    """Store methods for native worker start/end receipts and late binding."""

    @staticmethod
    def _attached_native_child_run(
        conn: Any,
        *,
        delegation_event_id: str,
    ) -> Any | None:
        """Return the sole worker receipt already attached to a delegation.

        Schema v27 worker rows did not carry the scoped native identity.  They
        remain authoritative when attached to an exact delegation event, but
        more than one such row is ambiguous and must fail closed.
        """

        rows = conn.execute(
            "SELECT id, delegation_event_id, backend, session_id, trace_id, "
            "work_unit_id, host, worker_id, native_run_id, exit_code, started_at, ended_at, "
            "native_delivery_status "
            "FROM worker_runs WHERE delegation_event_id = ? ORDER BY rowid LIMIT 2",
            (delegation_event_id,),
        ).fetchall()
        if len(rows) > 1:
            raise ValueError("delegation event has multiple native child receipts")
        return rows[0] if rows else None

    @staticmethod
    def _native_child_delegation(
        conn: Any,
        *,
        host: str,
        backend: str,
        session_id: str,
        trace_id: str,
        work_unit_id: str,
        worker_id: str,
        native_run_id: str,
    ) -> Any | None:
        rows = conn.execute(
            "SELECT * FROM delegation_events WHERE session_id = ? AND trace_id = ? "
            "AND host = ? AND backend = ? "
            "AND executed_worker_id = ? AND native_run_id = ? "
            "AND (? = '' OR work_unit_id = ?) "
            "ORDER BY rowid LIMIT 2",
            (
                session_id,
                trace_id,
                host,
                backend,
                worker_id,
                native_run_id,
                work_unit_id,
                work_unit_id,
            ),
        ).fetchall()
        if len(rows) > 1:
            raise ValueError("native child identity matches multiple delegation events")
        return rows[0] if rows else None

    def _merge_native_child_terminal(
        self,
        conn: Any,
        *,
        delegation: Any,
        status: str,
        outcome: str,
        error: object = "",
    ) -> None:
        safe_error = project_delegation_detail(
            error or outcome,
            field="error",
            capture_content=self._capture_content_enabled(),
        )
        self._merge_delegation_transition(
            conn,
            delegation,
            status=status,
            backend=str(delegation["backend"] or ""),
            error=safe_error,
            recommended_agent=str(delegation["recommended_agent"] or ""),
            executed_worker_kind=str(delegation["executed_worker_kind"] or ""),
            executed_worker_id=str(delegation["executed_worker_id"] or ""),
            native_run_id=str(delegation["native_run_id"] or ""),
            skip_reason="",
            host=str(delegation["host"] or ""),
            now=self._now(),
        )

    def record_native_child_started(
        self,
        *,
        host: str,
        backend: str,
        session_id: str,
        trace_id: str,
        worker_id: str,
        native_run_id: str,
        work_unit_id: str = "",
    ) -> dict[str, Any]:
        """Record one child only inside its exact parent turn identity."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        normalized_host = _identity(
            host,
            maximum=MAX_DELEGATION_HOST_CHARS,
            field="host",
        ).lower()
        normalized_backend = _identity(
            backend,
            maximum=MAX_DELEGATION_BACKEND_CHARS,
            field="backend",
        )
        normalized_worker = _identity(
            worker_id,
            maximum=MAX_DELEGATION_WORKER_ID_CHARS,
            field="worker_id",
        )
        normalized_run = _identity(
            native_run_id,
            maximum=MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
            field="native_run_id",
        )
        normalized_unit = (
            _identity(
                work_unit_id,
                maximum=MAX_DELEGATION_WORK_UNIT_ID_CHARS,
                field="work_unit_id",
            )
            if work_unit_id
            else ""
        )
        row_id = _worker_run_id(
            normalized_host,
            normalized_session,
            normalized_trace,
            normalized_worker,
            normalized_run,
        )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            delegation = self._native_child_delegation(
                conn,
                host=normalized_host,
                backend=normalized_backend,
                session_id=normalized_session,
                trace_id=normalized_trace,
                work_unit_id=normalized_unit,
                worker_id=normalized_worker,
                native_run_id=normalized_run,
            )
            delegation_unit = (
                str(delegation["work_unit_id"] or "") if delegation is not None else ""
            )
            bound_unit = delegation_unit or normalized_unit
            delegation_id = str(delegation["id"]) if delegation is not None else None
            existing = conn.execute(
                "SELECT id, delegation_event_id, backend, session_id, trace_id, "
                "work_unit_id, host, worker_id, native_run_id, exit_code, started_at, ended_at "
                "FROM worker_runs WHERE id = ?",
                (row_id,),
            ).fetchone()
            if existing is None and delegation_id:
                attached = self._attached_native_child_run(
                    conn,
                    delegation_event_id=delegation_id,
                )
                if attached is not None:
                    expected_identity = {
                        "backend": normalized_backend,
                        "session_id": normalized_session,
                        "trace_id": normalized_trace,
                        "host": normalized_host,
                        "worker_id": normalized_worker,
                        "native_run_id": normalized_run,
                    }
                    if any(
                        str(attached[field] or "") not in ("", expected)
                        for field, expected in expected_identity.items()
                    ):
                        raise ValueError(
                            "attached native child receipt conflicts with its scoped identity"
                        )
                    attached_unit = str(attached["work_unit_id"] or "")
                    if attached_unit and bound_unit and attached_unit != bound_unit:
                        raise ValueError(
                            "attached native child receipt conflicts with its work unit"
                        )
                    conn.execute(
                        "UPDATE worker_runs SET id = ?, backend = ?, session_id = ?, "
                        "trace_id = ?, work_unit_id = ?, host = ?, worker_id = ?, "
                        "native_run_id = ? WHERE id = ?",
                        (
                            row_id,
                            normalized_backend,
                            normalized_session,
                            normalized_trace,
                            bound_unit,
                            normalized_host,
                            normalized_worker,
                            normalized_run,
                            str(attached["id"]),
                        ),
                    )
                    existing = conn.execute(
                        "SELECT id, delegation_event_id, backend, session_id, trace_id, "
                        "work_unit_id, host, worker_id, native_run_id, exit_code, "
                        "started_at, ended_at FROM worker_runs WHERE id = ?",
                        (row_id,),
                    ).fetchone()
                    if existing is None:
                        raise RuntimeError("native child legacy rekey postcondition failed")
            if existing is None:
                conn.execute(
                    "INSERT INTO worker_runs "
                    "(id, delegation_event_id, backend, session_id, trace_id, work_unit_id, "
                    "host, worker_id, native_run_id, workdir, exit_code, stdout, stderr, "
                    "started_at, ended_at) "
                    f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', NULL, '', '', "  # nosec B608
                    f"{STORE_CLOCK_SQL}, NULL)",  # nosec B608
                    (
                        row_id,
                        delegation_id,
                        normalized_backend,
                        normalized_session,
                        normalized_trace,
                        bound_unit,
                        normalized_host,
                        normalized_worker,
                        normalized_run,
                    ),
                )
            else:
                expected_identity = {
                    "backend": normalized_backend,
                    "session_id": normalized_session,
                    "trace_id": normalized_trace,
                    "host": normalized_host,
                    "worker_id": normalized_worker,
                    "native_run_id": normalized_run,
                }
                if any(
                    str(existing[field] or "") != expected
                    for field, expected in expected_identity.items()
                ):
                    raise ValueError("native child run id conflicts with its scoped identity")
                existing_unit = str(existing["work_unit_id"] or "")
                if existing_unit and bound_unit and existing_unit != bound_unit:
                    raise ValueError("native child run is already bound to another work unit")
                bound = str(existing["delegation_event_id"] or "")
                if bound and delegation_id and bound != delegation_id:
                    raise ValueError("native child run is already bound to another delegation")
                if (delegation_id and not bound) or (bound_unit and not existing_unit):
                    conn.execute(
                        "UPDATE worker_runs SET "
                        "delegation_event_id = COALESCE(delegation_event_id, ?), "
                        "work_unit_id = CASE WHEN work_unit_id = '' THEN ? ELSE work_unit_id END "
                        "WHERE id = ?",
                        (delegation_id, bound_unit, row_id),
                    )
                if (
                    delegation is not None
                    and existing["ended_at"] is not None
                    and existing["exit_code"] is not None
                ):
                    completed = int(existing["exit_code"] or 0) == 0
                    stored_outcome = _EXIT_CODE_OUTCOMES.get(
                        int(existing["exit_code"] or 0),
                        "error",
                    )
                    self._merge_native_child_terminal(
                        conn,
                        delegation=delegation,
                        status="completed" if completed else "failed",
                        outcome=stored_outcome,
                    )
            row = conn.execute(
                "SELECT id, delegation_event_id, backend, session_id, trace_id, "
                "work_unit_id, host, worker_id, native_run_id, exit_code, started_at, ended_at "
                "FROM worker_runs WHERE id = ?",
                (row_id,),
            ).fetchone()
            if row is None:
                raise RuntimeError("native child start postcondition failed")
            conn.commit()
            return dict(row)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def claim_codex_native_child_execution(
        self,
        *,
        session_id: str,
        trace_id: str,
        work_unit_id: str,
        worker_id: str,
        native_run_id: str,
        tool_use_id: str,
    ) -> bool:
        """Bind one exact Codex execution dispatch, idempotent by tool call."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        normalized_unit = _identity(
            work_unit_id,
            maximum=MAX_DELEGATION_WORK_UNIT_ID_CHARS,
            field="work_unit_id",
        )
        normalized_worker = _identity(
            worker_id,
            maximum=MAX_DELEGATION_WORKER_ID_CHARS,
            field="worker_id",
        )
        normalized_run = _identity(
            native_run_id,
            maximum=MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
            field="native_run_id",
        )
        normalized_tool_use = validate_correlation_id(tool_use_id, field="tool_use_id")
        row_id = _worker_run_id(
            "codex",
            normalized_session,
            normalized_trace,
            normalized_worker,
            normalized_run,
        )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT delegation_event_id, work_unit_id, execution_tool_use_id, "
                "execution_dispatched_at, ended_at FROM worker_runs WHERE id = ? "
                "AND host = 'codex' "
                "AND session_id = ? AND trace_id = ? AND worker_id = ? "
                "AND native_run_id = ?",
                (
                    row_id,
                    normalized_session,
                    normalized_trace,
                    normalized_worker,
                    normalized_run,
                ),
            ).fetchone()
            if row is None:
                conn.rollback()
                return False
            stored_unit = str(row["work_unit_id"] or "")
            if stored_unit and stored_unit != normalized_unit:
                conn.rollback()
                return False
            if not stored_unit:
                delegation = self._native_child_delegation(
                    conn,
                    host="codex",
                    backend="spawn_agent",
                    session_id=normalized_session,
                    trace_id=normalized_trace,
                    work_unit_id=normalized_unit,
                    worker_id=normalized_worker,
                    native_run_id=normalized_run,
                )
                if delegation is None:
                    conn.rollback()
                    return False
                updated_binding = conn.execute(
                    "UPDATE worker_runs SET delegation_event_id = ?, work_unit_id = ? "
                    "WHERE id = ? AND work_unit_id = '' AND "
                    "(delegation_event_id IS NULL OR delegation_event_id = ?)",
                    (
                        str(delegation["id"]),
                        normalized_unit,
                        row_id,
                        str(delegation["id"]),
                    ),
                ).rowcount
                if updated_binding != 1:
                    conn.rollback()
                    return False
            existing_tool_use = str(row["execution_tool_use_id"] or "")
            if row["ended_at"] is not None:
                conn.rollback()
                return False
            if row["execution_dispatched_at"] is not None:
                conn.rollback()
                return existing_tool_use == normalized_tool_use
            if existing_tool_use:
                conn.rollback()
                return False
            conflicting_dispatch = conn.execute(
                "SELECT 1 FROM worker_runs WHERE session_id = ? AND trace_id = ? "
                "AND execution_tool_use_id = ? AND id <> ? LIMIT 1",
                (
                    normalized_session,
                    normalized_trace,
                    normalized_tool_use,
                    row_id,
                ),
            ).fetchone()
            if conflicting_dispatch is not None:
                conn.rollback()
                return False
            updated = conn.execute(
                f"UPDATE worker_runs SET execution_tool_use_id = ?, "  # nosec B608
                f"execution_dispatched_at = {STORE_CLOCK_SQL} WHERE id = ? "  # nosec B608
                "AND execution_dispatched_at IS NULL AND execution_tool_use_id = '' "
                "AND ended_at IS NULL",
                (normalized_tool_use, row_id),
            ).rowcount
            if updated != 1:
                conn.rollback()
                return False
            stored = conn.execute(
                "SELECT execution_tool_use_id, execution_dispatched_at FROM worker_runs "
                "WHERE id = ?",
                (row_id,),
            ).fetchone()
            if (
                stored is None
                or stored["execution_tool_use_id"] != normalized_tool_use
                or stored["execution_dispatched_at"] is None
            ):
                raise RuntimeError("Codex child execution claim postcondition failed")
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def bind_native_child_launch(
        self,
        *,
        host: str,
        session_id: str,
        trace_id: str,
        worker_id: str,
        native_run_id: str,
        launch_id: str,
    ) -> bool:
        """Bind one host-reported launch call to its exact native child.

        This content-free row supports correlation only; it is never delivery
        proof.  The binding is written after the native host reports the child
        identity, may arrive after the child ended, and is immutable once set.
        """

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        normalized_host = _identity(
            host,
            maximum=MAX_DELEGATION_HOST_CHARS,
            field="host",
        ).lower()
        normalized_worker = _identity(
            worker_id,
            maximum=MAX_DELEGATION_WORKER_ID_CHARS,
            field="worker_id",
        )
        normalized_run = _identity(
            native_run_id,
            maximum=MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
            field="native_run_id",
        )
        normalized_launch = validate_correlation_id(launch_id, field="launch_id")
        row_id = _worker_run_id(
            normalized_host,
            normalized_session,
            normalized_trace,
            normalized_worker,
            normalized_run,
        )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT execution_tool_use_id, execution_dispatched_at "
                "FROM worker_runs WHERE id = ? AND host = ? AND session_id = ? "
                "AND trace_id = ? AND worker_id = ? AND native_run_id = ?",
                (
                    row_id,
                    normalized_host,
                    normalized_session,
                    normalized_trace,
                    normalized_worker,
                    normalized_run,
                ),
            ).fetchone()
            if row is None:
                conn.rollback()
                return False
            existing = str(row["execution_tool_use_id"] or "")
            if row["execution_dispatched_at"] is not None or existing:
                conn.rollback()
                return bool(
                    existing == normalized_launch and row["execution_dispatched_at"] is not None
                )
            conflict = conn.execute(
                "SELECT 1 FROM worker_runs WHERE session_id = ? AND trace_id = ? "
                "AND execution_tool_use_id = ? AND id <> ? LIMIT 1",
                (normalized_session, normalized_trace, normalized_launch, row_id),
            ).fetchone()
            if conflict is not None:
                conn.rollback()
                return False
            updated = conn.execute(
                f"UPDATE worker_runs SET execution_tool_use_id = ?, "  # nosec B608
                f"execution_dispatched_at = {STORE_CLOCK_SQL} WHERE id = ? "  # nosec B608
                "AND execution_tool_use_id = '' AND execution_dispatched_at IS NULL",
                (normalized_launch, row_id),
            ).rowcount
            if updated != 1:
                conn.rollback()
                return False
            stored = conn.execute(
                "SELECT execution_tool_use_id, execution_dispatched_at "
                "FROM worker_runs WHERE id = ?",
                (row_id,),
            ).fetchone()
            if (
                stored is None
                or stored["execution_tool_use_id"] != normalized_launch
                or stored["execution_dispatched_at"] is None
            ):
                raise RuntimeError("native child launch binding postcondition failed")
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def resolve_openclaw_native_child_completion(
        self,
        *,
        requester_session_id: str,
        completion_run_id: str,
        parent_session_id: str,
        parent_trace_id: str,
        worker_id: str,
        native_run_id: str,
        launch_id: str,
        work_unit_id: str,
    ) -> dict[str, str] | None:
        """Resolve one live OpenClaw announce run to its exact parent turn.

        OpenClaw creates an internal ``announce:v1`` agent run after a native
        child finishes its work but before the host emits ``subagent_ended``.
        That internal run is not an Agency turn.  It may borrow the parent's
        Store-backed header and finalization path only while every persisted
        launch identity remains reciprocal, unique, ready, and open.

        This is deliberately a read-only resolver.  In particular it never
        creates a run for the synthetic announce identity.
        """

        normalized_requester = validate_correlation_id(
            requester_session_id,
            field="requester_session_id",
        )
        normalized_completion = validate_correlation_id(
            completion_run_id,
            field="completion_run_id",
        )
        normalized_parent_session = validate_correlation_id(
            parent_session_id,
            field="parent_session_id",
        )
        normalized_parent_trace = validate_correlation_id(
            parent_trace_id,
            field="parent_trace_id",
        )
        normalized_worker = _identity(
            worker_id,
            maximum=MAX_DELEGATION_WORKER_ID_CHARS,
            field="worker_id",
        )
        normalized_run = _identity(
            native_run_id,
            maximum=MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
            field="native_run_id",
        )
        normalized_launch = validate_correlation_id(launch_id, field="launch_id")
        normalized_unit = _identity(
            work_unit_id,
            maximum=MAX_DELEGATION_WORK_UNIT_ID_CHARS,
            field="work_unit_id",
        )
        expected_completion = f"announce:v1:{normalized_worker}:{normalized_run}"
        if normalized_completion != expected_completion:
            return None
        # The persisted native-child projection has one parent session.  A
        # different requester cannot inherit that parent's delivery authority.
        if normalized_requester != normalized_parent_session:
            return None

        conn = self._connect()
        try:
            conn.execute("BEGIN")
            matches = conn.execute(
                "SELECT wr.id AS worker_run_id, wr.session_id AS parent_session_id, "
                "wr.trace_id AS parent_trace_id, wr.work_unit_id, wr.worker_id, "
                "wr.native_run_id, wr.execution_tool_use_id AS launch_id, "
                "delegation.id AS delegation_event_id "
                "FROM worker_runs AS wr "
                "JOIN delegation_events AS delegation "
                "ON delegation.id = wr.delegation_event_id "
                "JOIN runs AS parent ON parent.trace_id = wr.trace_id "
                "WHERE wr.host = 'openclaw' AND wr.backend = 'sessions_spawn' "
                "AND wr.session_id = ? AND wr.trace_id = ? "
                "AND wr.work_unit_id = ? AND wr.worker_id = ? AND wr.native_run_id = ? "
                "AND wr.execution_tool_use_id = ? "
                "AND wr.execution_tool_use_id <> '' "
                "AND wr.execution_dispatched_at IS NOT NULL "
                "AND wr.started_at IS NOT NULL AND wr.ended_at IS NULL "
                "AND wr.exit_code IS NULL "
                "AND ('announce:v1:' || wr.worker_id || ':' || wr.native_run_id) = ? "
                "AND delegation.trace_id = wr.trace_id "
                "AND COALESCE(delegation.session_id, '') = wr.session_id "
                "AND delegation.host = wr.host AND delegation.backend = wr.backend "
                "AND COALESCE(delegation.work_unit_id, '') = wr.work_unit_id "
                "AND delegation.executed_worker_kind = 'generic-worker' "
                "AND delegation.executed_worker_id = wr.worker_id "
                "AND delegation.native_run_id = wr.native_run_id "
                "AND delegation.status = 'delegated' "
                "AND delegation.completed_at IS NULL "
                "AND COALESCE(parent.session_id, '') = wr.session_id "
                "AND parent.host = 'openclaw' "
                "AND parent.status IN ('active', 'evidence_only') "
                "AND parent.preflight_state = 'ready' "
                "AND parent.ended_at IS NULL "
                "AND parent.terminal_finalization_id IS NULL "
                "ORDER BY wr.rowid LIMIT 2",
                (
                    normalized_parent_session,
                    normalized_parent_trace,
                    normalized_unit,
                    normalized_worker,
                    normalized_run,
                    normalized_launch,
                    normalized_completion,
                ),
            ).fetchall()
            if len(matches) > 1:
                raise ValueError("OpenClaw completion matches multiple persisted parent scopes")
            if not matches:
                conn.rollback()
                return None
            match = matches[0]
            expected_worker_id = _worker_run_id(
                "openclaw",
                normalized_parent_session,
                normalized_parent_trace,
                normalized_worker,
                normalized_run,
            )
            if str(match["worker_run_id"] or "") != expected_worker_id:
                raise ValueError("OpenClaw completion matched an invalid worker receipt")
            result = {
                "requester_session_id": normalized_requester,
                "completion_run_id": normalized_completion,
                "parent_session_id": normalized_parent_session,
                "parent_trace_id": normalized_parent_trace,
                "worker_id": normalized_worker,
                "native_run_id": normalized_run,
                "launch_id": normalized_launch,
                "work_unit_id": normalized_unit,
                "delegation_event_id": str(match["delegation_event_id"] or ""),
                "worker_run_id": expected_worker_id,
            }
            if not result["delegation_event_id"]:
                raise ValueError("OpenClaw completion has no reciprocal delegation")
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def record_codex_child_tool_evidence(
        self,
        *,
        session_id: str,
        trace_id: str,
        work_unit_id: str,
        child_session_id: str,
        evidence: object,
    ) -> dict[str, Any]:
        """Attach one immutable content-free rollout summary to its worker receipt."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        normalized_unit = _identity(
            work_unit_id,
            maximum=MAX_DELEGATION_WORK_UNIT_ID_CHARS,
            field="work_unit_id",
        )
        normalized_child = _identity(
            child_session_id,
            maximum=MAX_DELEGATION_WORKER_ID_CHARS,
            field="child_session_id",
        )
        native_run_id = _identity(
            f"codex-agent:{normalized_child}",
            maximum=MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
            field="native_run_id",
        )
        row_id = _worker_run_id(
            "codex",
            normalized_session,
            normalized_trace,
            normalized_child,
            native_run_id,
        )
        payload = encode_codex_child_tool_evidence(evidence)
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT id, tool_evidence_schema, tool_evidence, "
                "tool_evidence_source, tool_evidence_recorded_at "
                "FROM worker_runs WHERE id = ? AND backend = 'spawn_agent' "
                "AND host = 'codex' AND session_id = ? AND trace_id = ? "
                "AND work_unit_id = ? AND worker_id = ? AND native_run_id = ?",
                (
                    row_id,
                    normalized_session,
                    normalized_trace,
                    normalized_unit,
                    normalized_child,
                    native_run_id,
                ),
            ).fetchone()
            if row is None:
                raise ValueError("Codex child tool evidence had no exact worker receipt")
            existing = decode_stored_codex_child_tool_evidence(
                schema=row["tool_evidence_schema"],
                source=row["tool_evidence_source"],
                recorded_at=row["tool_evidence_recorded_at"],
                payload=row["tool_evidence"],
            )
            if existing is None:
                updated = conn.execute(
                    "UPDATE worker_runs SET tool_evidence_schema = ?, tool_evidence = ?, "
                    "tool_evidence_source = ?, "
                    f"tool_evidence_recorded_at = {STORE_CLOCK_SQL} "  # nosec B608
                    "WHERE id = ? AND tool_evidence_schema = '' "
                    "AND tool_evidence = '' AND tool_evidence_source = '' "
                    "AND tool_evidence_recorded_at IS NULL",
                    (
                        CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SCHEMA,
                        payload,
                        CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SOURCE,
                        row_id,
                    ),
                ).rowcount
                if updated != 1:
                    raise RuntimeError("Codex child tool evidence write was not atomic")
                row = conn.execute(
                    "SELECT tool_evidence_schema, tool_evidence, tool_evidence_source, "
                    "tool_evidence_recorded_at FROM worker_runs WHERE id = ?",
                    (row_id,),
                ).fetchone()
                if row is None:
                    raise RuntimeError("Codex child tool evidence postcondition failed")
                existing = decode_stored_codex_child_tool_evidence(
                    schema=row["tool_evidence_schema"],
                    source=row["tool_evidence_source"],
                    recorded_at=row["tool_evidence_recorded_at"],
                    payload=row["tool_evidence"],
                )
            if existing is None or encode_codex_child_tool_evidence(existing) != payload:
                raise ValueError("Codex child tool evidence conflicts with its worker receipt")
            conn.commit()
            return {
                "schema": str(row["tool_evidence_schema"]),
                "source": str(row["tool_evidence_source"]),
                "recorded_at": str(row["tool_evidence_recorded_at"]),
                "tool_evidence": existing,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def record_native_child_terminal_observed(
        self,
        *,
        host: str,
        backend: str,
        requester_session_id: str,
        worker_id: str,
        native_run_id: str,
        outcome: str,
        parent_trace_id: str = "",
        work_unit_id: str = "",
        launch_id: str = "",
    ) -> dict[str, Any] | None:
        """Persist one child-end observation without closing its worker.

        OpenClaw observes the child agent ending before its separate announce
        message reaches the channel.  This marker survives a gateway restart,
        but deliberately leaves ``ended_at`` and ``exit_code`` untouched so a
        post-send receipt remains the only successful completion authority.
        """

        normalized_outcome = str(outcome or "unknown").strip().lower() or "unknown"
        if normalized_outcome not in _OUTCOME_EXIT_CODES:
            raise ValueError("native child outcome is invalid")
        normalized_host = _identity(
            host,
            maximum=MAX_DELEGATION_HOST_CHARS,
            field="host",
        ).lower()
        normalized_backend = _identity(
            backend,
            maximum=MAX_DELEGATION_BACKEND_CHARS,
            field="backend",
        )
        normalized_requester = validate_correlation_id(
            requester_session_id,
            field="requester_session_id",
        )
        normalized_trace = validate_correlation_id(
            parent_trace_id,
            field="parent_trace_id",
            required=False,
        )
        normalized_worker = _identity(
            worker_id,
            maximum=MAX_DELEGATION_WORKER_ID_CHARS,
            field="worker_id",
        )
        normalized_run = (
            _identity(
                native_run_id,
                maximum=MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
                field="native_run_id",
            )
            if native_run_id
            else ""
        )
        normalized_unit = (
            _identity(
                work_unit_id,
                maximum=MAX_DELEGATION_WORK_UNIT_ID_CHARS,
                field="work_unit_id",
            )
            if work_unit_id
            else ""
        )
        normalized_launch = validate_correlation_id(
            launch_id,
            field="launch_id",
            required=False,
        )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            matches = conn.execute(
                "SELECT wr.*, delegation.status AS delegation_status, "
                "delegation.completed_at AS delegation_completed_at "
                "FROM worker_runs AS wr JOIN delegation_events AS delegation "
                "ON delegation.id = wr.delegation_event_id "
                "WHERE wr.host = ? AND wr.backend = ? AND wr.session_id = ? "
                "AND wr.worker_id = ? AND (? = '' OR wr.native_run_id = ?) "
                "AND (? = '' OR wr.trace_id = ?) "
                "AND (? = '' OR wr.work_unit_id = ?) "
                "AND (? = '' OR wr.execution_tool_use_id = ?) "
                "AND wr.execution_tool_use_id <> '' "
                "AND wr.execution_dispatched_at IS NOT NULL "
                "AND wr.started_at IS NOT NULL AND wr.ended_at IS NULL "
                "AND wr.exit_code IS NULL "
                "AND delegation.trace_id = wr.trace_id "
                "AND COALESCE(delegation.session_id, '') = wr.session_id "
                "AND delegation.host = wr.host AND delegation.backend = wr.backend "
                "AND COALESCE(delegation.work_unit_id, '') = wr.work_unit_id "
                "AND delegation.executed_worker_kind = 'generic-worker' "
                "AND delegation.executed_worker_id = wr.worker_id "
                "AND delegation.native_run_id = wr.native_run_id "
                "AND delegation.status = 'delegated' "
                "AND delegation.completed_at IS NULL "
                "ORDER BY wr.rowid LIMIT 2",
                (
                    normalized_host,
                    normalized_backend,
                    normalized_requester,
                    normalized_worker,
                    normalized_run,
                    normalized_run,
                    normalized_trace,
                    normalized_trace,
                    normalized_unit,
                    normalized_unit,
                    normalized_launch,
                    normalized_launch,
                ),
            ).fetchall()
            if len(matches) > 1:
                raise ValueError("native child end observation is ambiguous")
            if not matches:
                conn.rollback()
                return None
            row = matches[0]
            expected_id = _worker_run_id(
                normalized_host,
                str(row["session_id"]),
                str(row["trace_id"]),
                str(row["worker_id"]),
                str(row["native_run_id"]),
            )
            if str(row["id"] or "") != expected_id:
                raise ValueError("native child end observation matched an invalid worker receipt")
            existing_at = row["native_terminal_observed_at"]
            existing_outcome = str(row["native_terminal_outcome"] or "")
            existing_delivery = str(row["native_delivery_status"] or "")
            if existing_at is not None:
                if existing_outcome != normalized_outcome or existing_delivery not in {
                    "pending",
                    "delivered",
                    "failed",
                    "interrupted",
                }:
                    raise ValueError(
                        "native child terminal observation conflicts with existing evidence"
                    )
            else:
                if existing_outcome or existing_delivery:
                    raise RuntimeError("native child terminal observation is incomplete")
                updated = conn.execute(
                    "UPDATE worker_runs SET native_terminal_outcome = ?, "
                    "native_delivery_status = 'pending', "
                    f"native_terminal_observed_at = {STORE_CLOCK_SQL} "  # nosec B608
                    "WHERE id = ? AND native_terminal_outcome = '' "
                    "AND native_delivery_status = '' "
                    "AND native_terminal_observed_at IS NULL "
                    "AND ended_at IS NULL AND exit_code IS NULL",
                    (normalized_outcome, expected_id),
                ).rowcount
                if updated != 1:
                    raise RuntimeError("native child terminal observation write was not atomic")
            stored = conn.execute(
                "SELECT id, native_terminal_outcome, native_delivery_status, "
                "native_terminal_observed_at "
                "FROM worker_runs WHERE id = ?",
                (expected_id,),
            ).fetchone()
            if (
                stored is None
                or str(stored["native_terminal_outcome"] or "") != normalized_outcome
                or str(stored["native_delivery_status"] or "")
                not in {
                    "pending",
                    "delivered",
                    "failed",
                    "interrupted",
                }
                or stored["native_terminal_observed_at"] is None
            ):
                raise RuntimeError("native child terminal observation postcondition failed")
            conn.commit()
            return {
                "id": str(stored["id"]),
                "outcome": normalized_outcome,
                "observed_at": str(stored["native_terminal_observed_at"]),
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def reconcile_openclaw_pending_native_child_deliveries(self) -> int:
        """Fail only ended children whose OpenClaw delivery was interrupted."""

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                "SELECT wr.id, wr.native_terminal_outcome "
                "FROM worker_runs AS wr JOIN delegation_events AS delegation "
                "ON delegation.id = wr.delegation_event_id "
                "WHERE wr.host = 'openclaw' AND wr.backend = 'sessions_spawn' "
                "AND wr.execution_tool_use_id <> '' "
                "AND wr.execution_dispatched_at IS NOT NULL "
                "AND wr.native_terminal_observed_at IS NOT NULL "
                "AND wr.native_terminal_outcome <> '' "
                "AND wr.native_delivery_status IN ('pending', 'failed') "
                "AND wr.ended_at IS NULL AND wr.exit_code IS NULL "
                "AND delegation.trace_id = wr.trace_id "
                "AND COALESCE(delegation.session_id, '') = wr.session_id "
                "AND delegation.host = wr.host AND delegation.backend = wr.backend "
                "AND COALESCE(delegation.work_unit_id, '') = wr.work_unit_id "
                "AND delegation.executed_worker_kind = 'generic-worker' "
                "AND delegation.executed_worker_id = wr.worker_id "
                "AND delegation.native_run_id = wr.native_run_id "
                "AND delegation.status = 'delegated' "
                "AND delegation.completed_at IS NULL ORDER BY wr.rowid"
            ).fetchall()
            for row in rows:
                updated = conn.execute(
                    "UPDATE worker_runs SET native_delivery_status = 'interrupted', "
                    "native_delivery_observed_at = COALESCE(native_delivery_observed_at, "
                    f"{STORE_CLOCK_SQL}) "  # nosec B608
                    "WHERE id = ? AND native_delivery_status IN ('pending', 'failed') "
                    "AND ended_at IS NULL AND exit_code IS NULL",
                    (str(row["id"]),),
                ).rowcount
                if updated != 1:
                    raise RuntimeError("native child interruption write was not atomic")
                self._record_native_child_terminal(
                    conn,
                    row_id=str(row["id"]),
                    # Preserve the host-observed execution outcome in its
                    # dedicated column, but an unproved delivery cannot expose
                    # a successful terminal lifecycle projection.
                    normalized_outcome="error",
                    error="native_child_delivery_interrupted",
                )
            conn.commit()
            return len(rows)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def record_openclaw_native_child_delivery(
        self,
        *,
        requester_session_id: str,
        worker_id: str,
        native_run_id: str,
        response_hash: str,
        success: bool,
        parent_trace_id: str = "",
        work_unit_id: str = "",
        launch_id: str = "",
    ) -> dict[str, Any] | None:
        """Atomically bind one post-send result to an observed child."""

        if not isinstance(success, bool):
            raise TypeError("success must be a boolean")
        target_status = "delivered" if success else "failed"

        normalized_requester = validate_correlation_id(
            requester_session_id,
            field="requester_session_id",
        )
        normalized_trace = validate_correlation_id(
            parent_trace_id,
            field="parent_trace_id",
            required=False,
        )
        normalized_worker = _identity(
            worker_id,
            maximum=MAX_DELEGATION_WORKER_ID_CHARS,
            field="worker_id",
        )
        normalized_run = (
            _identity(
                native_run_id,
                maximum=MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
                field="native_run_id",
            )
            if native_run_id
            else ""
        )
        normalized_unit = (
            _identity(
                work_unit_id,
                maximum=MAX_DELEGATION_WORK_UNIT_ID_CHARS,
                field="work_unit_id",
            )
            if work_unit_id
            else ""
        )
        normalized_launch = validate_correlation_id(
            launch_id,
            field="launch_id",
            required=False,
        )
        normalized_hash = str(response_hash or "").strip()
        if len(normalized_hash) != 64 or any(
            character not in "0123456789abcdef" for character in normalized_hash
        ):
            raise ValueError("response_hash must be a lowercase SHA-256 digest")

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            matches = conn.execute(
                "SELECT wr.*, delegation.status AS delegation_status "
                "FROM worker_runs AS wr JOIN delegation_events AS delegation "
                "ON delegation.id = wr.delegation_event_id "
                "JOIN runs AS parent ON parent.trace_id = wr.trace_id "
                "JOIN finalization_events AS finalization "
                "ON finalization.id = parent.terminal_finalization_id "
                "WHERE wr.host = 'openclaw' AND wr.backend = 'sessions_spawn' "
                "AND wr.session_id = ? AND wr.worker_id = ? "
                "AND (? = '' OR wr.native_run_id = ?) "
                "AND (? = '' OR wr.trace_id = ?) "
                "AND (? = '' OR wr.work_unit_id = ?) "
                "AND (? = '' OR wr.execution_tool_use_id = ?) "
                "AND wr.execution_tool_use_id <> '' "
                "AND wr.execution_dispatched_at IS NOT NULL "
                "AND wr.native_terminal_observed_at IS NOT NULL "
                "AND wr.native_terminal_outcome <> '' "
                "AND wr.native_delivery_status IN ('pending', 'delivered', 'failed') "
                "AND delegation.trace_id = wr.trace_id "
                "AND COALESCE(delegation.session_id, '') = wr.session_id "
                "AND delegation.host = wr.host AND delegation.backend = wr.backend "
                "AND COALESCE(delegation.work_unit_id, '') = wr.work_unit_id "
                "AND delegation.executed_worker_kind = 'generic-worker' "
                "AND delegation.executed_worker_id = wr.worker_id "
                "AND delegation.native_run_id = wr.native_run_id "
                "AND COALESCE(parent.session_id, '') = wr.session_id "
                "AND parent.host = wr.host AND parent.status = 'completed' "
                "AND parent.terminal_finalization_id IS NOT NULL "
                "AND finalization.trace_id = wr.trace_id "
                "AND finalization.response_hash = ? "
                "AND finalization.terminal_status = parent.status "
                "ORDER BY wr.rowid LIMIT 2",
                (
                    normalized_requester,
                    normalized_worker,
                    normalized_run,
                    normalized_run,
                    normalized_trace,
                    normalized_trace,
                    normalized_unit,
                    normalized_unit,
                    normalized_launch,
                    normalized_launch,
                    normalized_hash,
                ),
            ).fetchall()
            if len(matches) > 1:
                raise ValueError("OpenClaw delivery matches multiple pending native children")
            if not matches:
                conn.rollback()
                return None
            row = matches[0]
            expected_id = _worker_run_id(
                "openclaw",
                str(row["session_id"]),
                str(row["trace_id"]),
                str(row["worker_id"]),
                str(row["native_run_id"]),
            )
            if str(row["id"] or "") != expected_id:
                raise ValueError("OpenClaw delivery matched an invalid worker receipt")
            stored_status = str(row["native_delivery_status"] or "")
            if stored_status == target_status:
                if (
                    row["native_delivery_observed_at"] is None
                    or (success and row["ended_at"] is None)
                    or (not success and row["ended_at"] is not None)
                ):
                    raise ValueError("OpenClaw delivery conflicts with existing evidence")
            elif stored_status != "pending":
                raise ValueError("OpenClaw delivery conflicts with existing evidence")
            else:
                if row["ended_at"] is not None or row["exit_code"] is not None:
                    raise ValueError("OpenClaw delivery matched an already-terminal worker")
                updated = conn.execute(
                    "UPDATE worker_runs SET native_delivery_status = ?, "
                    f"native_delivery_observed_at = {STORE_CLOCK_SQL} "  # nosec B608
                    "WHERE id = ? AND native_delivery_status = 'pending' "
                    "AND native_delivery_observed_at IS NULL "
                    "AND ended_at IS NULL AND exit_code IS NULL",
                    (target_status, expected_id),
                ).rowcount
                if updated != 1:
                    raise RuntimeError("OpenClaw delivery write was not atomic")
                if success:
                    child_outcome = str(row["native_terminal_outcome"] or "")
                    self._record_native_child_terminal(
                        conn,
                        row_id=expected_id,
                        normalized_outcome=child_outcome,
                        error=("" if child_outcome == "ok" else "native_child_execution_failed"),
                    )
            stored = conn.execute(
                "SELECT id, native_terminal_outcome, native_delivery_status, "
                "native_delivery_observed_at, exit_code, ended_at "
                "FROM worker_runs WHERE id = ?",
                (expected_id,),
            ).fetchone()
            if (
                stored is None
                or str(stored["native_delivery_status"] or "") != target_status
                or stored["native_delivery_observed_at"] is None
                or (success and stored["ended_at"] is None)
                or (success and stored["exit_code"] is None)
                or (not success and stored["ended_at"] is not None)
                or (not success and stored["exit_code"] is not None)
            ):
                raise RuntimeError("OpenClaw delivery postcondition failed")
            conn.commit()
            return dict(stored)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _record_native_child_terminal(
        self,
        conn: Any,
        *,
        row_id: str,
        normalized_outcome: str,
        error: object = "",
    ) -> dict[str, Any]:
        """Commit one exact worker terminal transition in the caller's transaction."""

        exit_code = _OUTCOME_EXIT_CODES[normalized_outcome]
        row = conn.execute(
            "SELECT id, delegation_event_id, backend, session_id, trace_id, "
            "work_unit_id, host, worker_id, native_run_id, exit_code, started_at, ended_at, "
            "native_delivery_status "
            "FROM worker_runs WHERE id = ?",
            (row_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError("native child end has no start receipt")
        if (
            str(row["host"] or "") == "openclaw"
            and str(row["backend"] or "") == "sessions_spawn"
            and str(row["native_delivery_status"] or "") in {"pending", "failed"}
        ):
            raise RuntimeError("OpenClaw native child completion awaits delivery evidence")
        if (
            row["ended_at"] is not None
            and row["exit_code"] is not None
            and int(row["exit_code"]) != exit_code
        ):
            raise ValueError("native child terminal outcome conflicts with existing evidence")
        conn.execute(
            f"UPDATE worker_runs SET exit_code = ?, ended_at = "  # nosec B608
            f"COALESCE(ended_at, {STORE_CLOCK_SQL}) WHERE id = ?",  # nosec B608
            (exit_code, row_id),
        )
        delegation = self._native_child_delegation(
            conn,
            host=str(row["host"]),
            backend=str(row["backend"]),
            session_id=str(row["session_id"]),
            trace_id=str(row["trace_id"]),
            work_unit_id=str(row["work_unit_id"]),
            worker_id=str(row["worker_id"]),
            native_run_id=str(row["native_run_id"]),
        )
        if delegation is not None:
            attached_delegation = str(row["delegation_event_id"] or "")
            if attached_delegation and attached_delegation != str(delegation["id"]):
                raise ValueError("native child receipt conflicts with its delegation")
            conn.execute(
                "UPDATE worker_runs SET delegation_event_id = ?, "
                "work_unit_id = CASE WHEN work_unit_id = '' THEN ? ELSE work_unit_id END "
                "WHERE id = ? AND delegation_event_id IS NULL",
                (str(delegation["id"]), str(delegation["work_unit_id"] or ""), row_id),
            )
            self._merge_native_child_terminal(
                conn,
                delegation=delegation,
                status="completed" if normalized_outcome == "ok" else "failed",
                outcome=normalized_outcome,
                error=error,
            )
            delegation = conn.execute(
                "SELECT * FROM delegation_events WHERE id = ?",
                (delegation["id"],),
            ).fetchone()
        workforce_outcome_id = (
            None
            if delegation is None
            else record_native_assignment_outcome(
                conn,
                delegation=delegation,
                worker_run_id=row_id,
                outcome=normalized_outcome,
                store=self,
            )
        )
        terminal = conn.execute(
            "SELECT id, delegation_event_id, backend, session_id, trace_id, "
            "work_unit_id, host, worker_id, native_run_id, exit_code, started_at, ended_at "
            "FROM worker_runs WHERE id = ?",
            (row_id,),
        ).fetchone()
        if terminal is None or terminal["ended_at"] is None:
            raise RuntimeError("native child end postcondition failed")
        return {
            **dict(terminal),
            "outcome": normalized_outcome,
            "workforce_outcome_id": workforce_outcome_id,
        }

    def record_native_child_ended(
        self,
        *,
        host: str,
        backend: str,
        session_id: str,
        trace_id: str,
        worker_id: str,
        native_run_id: str,
        outcome: str,
        error: object = "",
        work_unit_id: str = "",
    ) -> dict[str, Any]:
        """Record one terminal child callback, safe under replay and reordering."""

        normalized_outcome = str(outcome or "unknown").strip().lower() or "unknown"
        if normalized_outcome not in _OUTCOME_EXIT_CODES:
            raise ValueError("native child outcome is invalid")
        started = self.record_native_child_started(
            host=host,
            backend=backend,
            session_id=session_id,
            trace_id=trace_id,
            worker_id=worker_id,
            native_run_id=native_run_id,
            work_unit_id=work_unit_id,
        )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            terminal = self._record_native_child_terminal(
                conn,
                row_id=str(started["id"]),
                normalized_outcome=normalized_outcome,
                error=error,
            )
            conn.commit()
            return terminal
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def reconcile_native_child_ended(
        self,
        *,
        host: str,
        backend: str,
        requester_session_id: str,
        worker_id: str,
        native_run_id: str,
        outcome: str,
        error: object = "",
    ) -> dict[str, Any] | None:
        """Close one unique, launch-bound child when the parent trace was lost.

        Native host completion callbacks can outlive the plugin process that
        remembered their parent trace. The requester session plus host-issued
        child identities may recover that trace only from one exact persisted
        accepted launch. A missing run id is permitted for host reset/failure
        shapes, but uniqueness is still mandatory and no lifecycle row is ever
        created by this recovery path.
        """

        normalized_outcome = str(outcome or "unknown").strip().lower() or "unknown"
        if normalized_outcome not in _OUTCOME_EXIT_CODES:
            raise ValueError("native child outcome is invalid")
        normalized_host = _identity(
            host,
            maximum=MAX_DELEGATION_HOST_CHARS,
            field="host",
        ).lower()
        normalized_backend = _identity(
            backend,
            maximum=MAX_DELEGATION_BACKEND_CHARS,
            field="backend",
        )
        normalized_requester = validate_correlation_id(
            requester_session_id,
            field="requester_session_id",
        )
        normalized_worker = _identity(
            worker_id,
            maximum=MAX_DELEGATION_WORKER_ID_CHARS,
            field="worker_id",
        )
        normalized_run = (
            _identity(
                native_run_id,
                maximum=MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
                field="native_run_id",
            )
            if native_run_id
            else ""
        )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            matches = conn.execute(
                "SELECT wr.id, wr.session_id, wr.trace_id, wr.work_unit_id, wr.host, "
                "wr.backend, wr.worker_id, wr.native_run_id, wr.delegation_event_id "
                "FROM worker_runs AS wr "
                "JOIN delegation_events AS delegation "
                "ON delegation.id = wr.delegation_event_id "
                "JOIN runs AS parent ON parent.trace_id = wr.trace_id "
                "WHERE wr.host = ? AND wr.backend = ? AND wr.session_id = ? "
                "AND wr.worker_id = ? AND (? = '' OR wr.native_run_id = ?) "
                "AND wr.execution_tool_use_id <> '' "
                "AND wr.execution_dispatched_at IS NOT NULL "
                "AND delegation.trace_id = wr.trace_id "
                "AND COALESCE(delegation.session_id, '') = wr.session_id "
                "AND delegation.host = wr.host AND delegation.backend = wr.backend "
                "AND COALESCE(delegation.work_unit_id, '') = wr.work_unit_id "
                "AND delegation.executed_worker_kind = 'generic-worker' "
                "AND delegation.executed_worker_id = wr.worker_id "
                "AND delegation.native_run_id = wr.native_run_id "
                "AND delegation.status IN ('delegated', 'completed', 'failed') "
                "AND COALESCE(parent.session_id, '') = wr.session_id "
                "AND parent.host = wr.host ORDER BY wr.rowid LIMIT 2",
                (
                    normalized_host,
                    normalized_backend,
                    normalized_requester,
                    normalized_worker,
                    normalized_run,
                    normalized_run,
                ),
            ).fetchall()
            if len(matches) > 1:
                raise ValueError("native child callback matches multiple persisted parent scopes")
            if not matches:
                conn.rollback()
                return None
            matched = matches[0]
            expected_row_id = _worker_run_id(
                normalized_host,
                normalized_requester,
                str(matched["trace_id"]),
                normalized_worker,
                str(matched["native_run_id"]),
            )
            if str(matched["id"]) != expected_row_id:
                raise ValueError("native child callback matched an invalid worker receipt")
            terminal = self._record_native_child_terminal(
                conn,
                row_id=expected_row_id,
                normalized_outcome=normalized_outcome,
                error=error,
            )
            conn.commit()
            return terminal
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def record_native_child_stopped(
        self,
        *,
        host: str,
        backend: str,
        session_id: str,
        trace_id: str,
        worker_id: str,
        native_run_id: str,
        work_unit_id: str = "",
    ) -> dict[str, Any]:
        """Record an outcome-free stop without fabricating success or failure.

        Some native hosts expose a child-stop identity before the parent tool
        result carries an authoritative outcome.  This receipt deliberately
        leaves ``exit_code`` unset and does not transition the delegation.  A
        later :meth:`record_native_child_ended` call can bind and complete it.
        """

        started = self.record_native_child_started(
            host=host,
            backend=backend,
            session_id=session_id,
            trace_id=trace_id,
            worker_id=worker_id,
            native_run_id=native_run_id,
            work_unit_id=work_unit_id,
        )
        row_id = str(started["id"])
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute(
                "SELECT host, backend, native_delivery_status FROM worker_runs WHERE id = ?",
                (row_id,),
            ).fetchone()
            if current is None:
                raise RuntimeError("native child stop has no start receipt")
            if (
                str(current["host"] or "") == "openclaw"
                and str(current["backend"] or "") == "sessions_spawn"
                and str(current["native_delivery_status"] or "") in {"pending", "failed"}
            ):
                raise RuntimeError("OpenClaw native child completion awaits delivery evidence")
            conn.execute(
                f"UPDATE worker_runs SET ended_at = "  # nosec B608
                f"COALESCE(ended_at, {STORE_CLOCK_SQL}) WHERE id = ?",  # nosec B608
                (row_id,),
            )
            stopped = conn.execute(
                "SELECT id, delegation_event_id, backend, session_id, trace_id, "
                "work_unit_id, host, worker_id, native_run_id, exit_code, started_at, ended_at "
                "FROM worker_runs WHERE id = ?",
                (row_id,),
            ).fetchone()
            if stopped is None or stopped["ended_at"] is None:
                raise RuntimeError("native child stop postcondition failed")
            conn.commit()
            return {
                **dict(stopped),
                "outcome": (
                    _EXIT_CODE_OUTCOMES.get(int(stopped["exit_code"]), "error")
                    if stopped["exit_code"] is not None
                    else "unavailable"
                ),
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_native_child_run(
        self,
        *,
        host: str,
        session_id: str,
        trace_id: str,
        worker_id: str,
        native_run_id: str,
        work_unit_id: str = "",
    ) -> dict[str, Any] | None:
        """Return one content-free child lifecycle projection."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        normalized_host = _identity(
            host,
            maximum=MAX_DELEGATION_HOST_CHARS,
            field="host",
        ).lower()
        normalized_run = _identity(
            native_run_id,
            maximum=MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
            field="native_run_id",
        )
        normalized_worker = _identity(
            worker_id,
            maximum=MAX_DELEGATION_WORKER_ID_CHARS,
            field="worker_id",
        )
        normalized_unit = (
            _identity(
                work_unit_id,
                maximum=MAX_DELEGATION_WORK_UNIT_ID_CHARS,
                field="work_unit_id",
            )
            if work_unit_id
            else ""
        )
        row_id = _worker_run_id(
            normalized_host,
            normalized_session,
            normalized_trace,
            normalized_worker,
            normalized_run,
        )
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT id, delegation_event_id, backend, session_id, trace_id, "
                "work_unit_id, host, worker_id, native_run_id, exit_code, started_at, "
                "execution_tool_use_id, execution_dispatched_at, tool_evidence_schema, "
                "tool_evidence, tool_evidence_source, tool_evidence_recorded_at, "
                "native_terminal_outcome, native_delivery_status, "
                "native_terminal_observed_at, native_delivery_observed_at, ended_at "
                "FROM worker_runs WHERE id = ? AND (? = '' OR work_unit_id = ?)",
                (row_id, normalized_unit, normalized_unit),
            ).fetchone()
            if row is None:
                return None
            projected = dict(row)
            projected["tool_evidence"] = decode_stored_codex_child_tool_evidence(
                schema=projected["tool_evidence_schema"],
                source=projected["tool_evidence_source"],
                recorded_at=projected["tool_evidence_recorded_at"],
                payload=projected["tool_evidence"],
            )
            return projected
        finally:
            conn.close()


__all__ = ["NativeChildStoreMixin"]
