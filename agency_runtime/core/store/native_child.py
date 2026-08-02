"""Content-free native child lifecycle persistence.

The host owns worker scheduling.  Agency records only stable identities,
timestamps, terminal outcome, and the reciprocal delegation link; prompts and
worker output never enter this projection.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

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
            "work_unit_id, host, worker_id, native_run_id, exit_code, started_at, ended_at "
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
        row_id = str(started["id"])
        exit_code = _OUTCOME_EXIT_CODES[normalized_outcome]
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT id, delegation_event_id, backend, session_id, trace_id, "
                "work_unit_id, host, worker_id, native_run_id, exit_code, started_at, ended_at "
                "FROM worker_runs WHERE id = ?",
                (row_id,),
            ).fetchone()
            if row is None:
                raise RuntimeError("native child end has no start receipt")
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
                host=str(started["host"]),
                backend=str(started["backend"]),
                session_id=str(started["session_id"]),
                trace_id=str(started["trace_id"]),
                work_unit_id=str(started["work_unit_id"]),
                worker_id=str(started["worker_id"]),
                native_run_id=str(started["native_run_id"]),
            )
            if delegation is not None:
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
            conn.commit()
            return {
                **dict(terminal),
                "outcome": normalized_outcome,
                "workforce_outcome_id": workforce_outcome_id,
            }
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
                "execution_tool_use_id, execution_dispatched_at, ended_at "
                "FROM worker_runs WHERE id = ? AND (? = '' OR work_unit_id = ?)",
                (row_id, normalized_unit, normalized_unit),
            ).fetchone()
            return dict(row) if row is not None else None
        finally:
            conn.close()


__all__ = ["NativeChildStoreMixin"]
