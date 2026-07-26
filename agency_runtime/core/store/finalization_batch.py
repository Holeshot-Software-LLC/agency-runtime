"""Atomic validation, persistence, and terminalization of finalization evidence."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Final

from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.delegation_status import (
    MAX_DELEGATION_AGENT_CHARS,
    MAX_DELEGATION_BACKEND_CHARS,
    MAX_DELEGATION_HOST_CHARS,
    MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
    MAX_DELEGATION_WORK_UNIT_ID_CHARS,
    MAX_DELEGATION_WORKER_ID_CHARS,
    MAX_DELEGATION_WORKER_KIND_CHARS,
    TERMINAL_DELEGATION_STATUSES,
)
from agency_runtime.core.resident_managers import resident_manager_boundary_error
from agency_runtime.core.store.delegation_activation import (
    attach_consumed_activation_to_delegation,
)
from agency_runtime.core.store.evidence import (
    _prepare_delegation_transition,
    _require_execution_correlation,
)
from agency_runtime.core.store.projections import (
    DELEGATION_DETAIL_LIMIT,
    project_delegation_detail,
)

MAX_FINALIZATION_EVIDENCE_ITEMS: Final[int] = 128
MAX_FINALIZATION_EVIDENCE_BYTES: Final[int] = 256 * 1024
MAX_FINALIZATION_SKILL_NAME_CHARS: Final[int] = 256

_FINALIZATION_STATUSES = frozenset({"delegated", "completed", "skipped", "failed"})
_EXECUTED_FINALIZATION_STATUSES = frozenset({"delegated", "completed"})
_DELEGATION_FIELDS = frozenset(
    {
        "agent",
        "recommended_agent",
        "status",
        "backend",
        "work_unit_id",
        "executed_worker_kind",
        "executed_worker_id",
        "native_run_id",
        "skip_reason",
        "error",
    }
)
_DELEGATION_RECEIPT_FIELDS = (
    "id",
    "work_unit_id",
    "recommended_agent",
    "status",
    "backend",
    "executed_worker_kind",
    "executed_worker_id",
    "native_run_id",
)


class FinalizationEvidenceError(ValueError):
    """A caller finalization envelope failed strict, bounded validation."""


class FinalizationEvidenceConflictError(FinalizationEvidenceError):
    """A valid envelope conflicts with already-authoritative Store state."""


@dataclass(frozen=True)
class ValidatedFinalizationDelegation:
    recommended_agent: str
    status: str
    backend: str
    work_unit_id: str
    executed_worker_kind: str
    executed_worker_id: str
    native_run_id: str
    skip_reason: str
    error: str

    def canonical_payload(self) -> dict[str, str]:
        return {
            "recommended_agent": self.recommended_agent,
            "status": self.status,
            "backend": self.backend,
            "work_unit_id": self.work_unit_id,
            "executed_worker_kind": self.executed_worker_kind,
            "executed_worker_id": self.executed_worker_id,
            "native_run_id": self.native_run_id,
            "skip_reason": self.skip_reason,
            "error": self.error,
        }


@dataclass(frozen=True)
class ValidatedFinalizationEvidenceBatch:
    session_id: str
    trace_id: str
    skills: tuple[str, ...]
    delegations: tuple[ValidatedFinalizationDelegation, ...]
    encoded_bytes: int

    @property
    def item_count(self) -> int:
        return len(self.skills) + len(self.delegations)


def _identifier(
    value: object,
    *,
    field: str,
    maximum: int,
    required: bool = True,
) -> str:
    if not isinstance(value, str):
        raise FinalizationEvidenceError(f"{field} must be a string")
    if value != value.strip() or any(
        ord(character) < 32 or ord(character) == 127 for character in value
    ):
        raise FinalizationEvidenceError(f"{field} must be a canonical single-line identifier")
    if required and not value:
        raise FinalizationEvidenceError(f"{field} is required")
    if len(value) > maximum:
        raise FinalizationEvidenceError(f"{field} exceeds its maximum length")
    return value


def _detail(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise FinalizationEvidenceError(f"{field} must be a string")
    if "\x00" in value or len(value) > DELEGATION_DETAIL_LIMIT:
        raise FinalizationEvidenceError(f"{field} exceeds its bounded text contract")
    return value


def _validate_delegation(value: object, *, index: int) -> ValidatedFinalizationDelegation:
    prefix = f"delegations[{index}]"
    if not isinstance(value, dict):
        raise FinalizationEvidenceError(f"{prefix} must be an object")
    unknown = set(value) - _DELEGATION_FIELDS
    if unknown:
        raise FinalizationEvidenceError(f"{prefix} contains unknown fields")
    has_agent = "agent" in value
    has_recommended = "recommended_agent" in value
    if has_agent == has_recommended:
        raise FinalizationEvidenceError(
            f"{prefix} requires exactly one of agent or recommended_agent"
        )
    if not value.get("work_unit_id") or not value.get("backend"):
        raise FinalizationEvidenceError("delegations require agent, work_unit_id, and backend")
    recommended_agent = _identifier(
        value["agent"] if has_agent else value["recommended_agent"],
        field=f"{prefix}.recommended_agent",
        maximum=MAX_DELEGATION_AGENT_CHARS,
    )
    if boundary_error := resident_manager_boundary_error(
        recommended_agent,
        operation="be recorded as a delegated worker",
    ):
        raise FinalizationEvidenceError(boundary_error)
    status = _identifier(
        value.get("status"),
        field=f"{prefix}.status",
        maximum=32,
    )
    if status not in _FINALIZATION_STATUSES:
        raise FinalizationEvidenceError(
            f"{prefix}.status must be delegated, completed, skipped, or failed"
        )
    backend = _identifier(
        value.get("backend"),
        field=f"{prefix}.backend",
        maximum=MAX_DELEGATION_BACKEND_CHARS,
    )
    work_unit_id = _identifier(
        value.get("work_unit_id"),
        field=f"{prefix}.work_unit_id",
        maximum=MAX_DELEGATION_WORK_UNIT_ID_CHARS,
    )
    worker_kind = _identifier(
        value.get("executed_worker_kind", ""),
        field=f"{prefix}.executed_worker_kind",
        maximum=MAX_DELEGATION_WORKER_KIND_CHARS,
        required=False,
    )
    worker_id = _identifier(
        value.get("executed_worker_id", ""),
        field=f"{prefix}.executed_worker_id",
        maximum=MAX_DELEGATION_WORKER_ID_CHARS,
        required=False,
    )
    native_run_id = _identifier(
        value.get("native_run_id", ""),
        field=f"{prefix}.native_run_id",
        maximum=MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
        required=False,
    )
    lineage = (worker_kind, worker_id, native_run_id)
    if status in _EXECUTED_FINALIZATION_STATUSES and not all(lineage):
        raise FinalizationEvidenceError(
            "positive delegations require executed_worker_kind, "
            "executed_worker_id, and native_run_id"
        )
    if status not in _EXECUTED_FINALIZATION_STATUSES and any(lineage) and not all(lineage):
        raise FinalizationEvidenceError(
            f"{prefix} execution identity must be complete when present"
        )
    return ValidatedFinalizationDelegation(
        recommended_agent=recommended_agent,
        status=status,
        backend=backend,
        work_unit_id=work_unit_id,
        executed_worker_kind=worker_kind,
        executed_worker_id=worker_id,
        native_run_id=native_run_id,
        skip_reason=_detail(value.get("skip_reason", ""), field=f"{prefix}.skip_reason"),
        error=_detail(value.get("error", ""), field=f"{prefix}.error"),
    )


def validate_finalization_evidence_items(
    *,
    skills_loaded: object,
    delegations: object,
) -> tuple[tuple[str, ...], tuple[ValidatedFinalizationDelegation, ...]]:
    """Validate all evidence items independently from turn correlation."""

    if not isinstance(skills_loaded, list):
        raise FinalizationEvidenceError("skills_loaded must be a list")
    if not isinstance(delegations, list):
        raise FinalizationEvidenceError("delegations must be a list")
    if len(skills_loaded) > MAX_FINALIZATION_EVIDENCE_ITEMS:
        raise FinalizationEvidenceError("skills_loaded exceeds the item limit")
    if len(delegations) > MAX_FINALIZATION_EVIDENCE_ITEMS:
        raise FinalizationEvidenceError("delegations exceeds the item limit")
    if len(skills_loaded) + len(delegations) > MAX_FINALIZATION_EVIDENCE_ITEMS:
        raise FinalizationEvidenceError("finalization evidence exceeds the item limit")

    skills: list[str] = []
    seen_skills: set[str] = set()
    for index, value in enumerate(skills_loaded):
        skill = _identifier(
            value,
            field=f"skills_loaded[{index}]",
            maximum=MAX_FINALIZATION_SKILL_NAME_CHARS,
        )
        if skill in seen_skills:
            raise FinalizationEvidenceError("skills_loaded contains a duplicate identity")
        seen_skills.add(skill)
        skills.append(skill)

    normalized_delegations: list[ValidatedFinalizationDelegation] = []
    seen_work_units: set[str] = set()
    for index, value in enumerate(delegations):
        delegation = _validate_delegation(value, index=index)
        if delegation.work_unit_id in seen_work_units:
            raise FinalizationEvidenceError("delegations contains a duplicate work_unit_id")
        seen_work_units.add(delegation.work_unit_id)
        normalized_delegations.append(delegation)
    return tuple(skills), tuple(normalized_delegations)


def validate_finalization_evidence_batch(
    *,
    session_id: object,
    trace_id: object,
    skills_loaded: object,
    delegations: object,
) -> ValidatedFinalizationEvidenceBatch:
    """Strictly validate the complete caller envelope before opening SQLite."""

    try:
        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
    except ValueError as exc:
        raise FinalizationEvidenceError(str(exc)) from exc
    skills, normalized_delegations = validate_finalization_evidence_items(
        skills_loaded=skills_loaded,
        delegations=delegations,
    )

    encoded_bytes = _encoded_batch_bytes(
        session_id=normalized_session,
        trace_id=normalized_trace,
        skills=skills,
        delegations=normalized_delegations,
    )
    if encoded_bytes > MAX_FINALIZATION_EVIDENCE_BYTES:
        raise FinalizationEvidenceError("finalization evidence exceeds the byte limit")
    return ValidatedFinalizationEvidenceBatch(
        session_id=normalized_session,
        trace_id=normalized_trace,
        skills=skills,
        delegations=normalized_delegations,
        encoded_bytes=encoded_bytes,
    )


def _encoded_batch_bytes(
    *,
    session_id: str,
    trace_id: str,
    skills: tuple[str, ...],
    delegations: tuple[ValidatedFinalizationDelegation, ...],
) -> int:
    canonical = {
        "session_id": session_id,
        "trace_id": trace_id,
        "skills_loaded": skills,
        "delegations": [item.canonical_payload() for item in delegations],
    }
    return len(json.dumps(canonical, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


@dataclass
class _BoundTransactionState:
    rollback_requested: bool = False


class _IgnoredTransactionCursor:
    rowcount = -1

    @staticmethod
    def fetchone() -> None:
        return None

    @staticmethod
    def fetchall() -> list[Any]:
        return []


class _BoundTransactionConnection:
    """Keep existing Store read/CAS helpers inside one caller-owned transaction."""

    def __init__(self, connection: Any, state: _BoundTransactionState):
        self._connection = connection
        self._state = state

    def execute(self, sql: str, parameters: object = ()) -> Any:
        if self._state.rollback_requested:
            raise RuntimeError("finalization transaction already requested rollback")
        if str(sql).lstrip().upper().startswith("BEGIN"):
            return _IgnoredTransactionCursor()
        return self._connection.execute(sql, parameters)

    def executemany(self, sql: str, parameters: object) -> Any:
        if self._state.rollback_requested:
            raise RuntimeError("finalization transaction already requested rollback")
        return self._connection.executemany(sql, parameters)

    def commit(self) -> None:
        if self._state.rollback_requested:
            raise RuntimeError("finalization transaction already requested rollback")

    def rollback(self) -> None:
        self._state.rollback_requested = True

    @staticmethod
    def close() -> None:
        return None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)


def _transaction_bound_store(store: Any, connection: Any, state: _BoundTransactionState) -> Any:
    """Clone Store state while replacing only its connection factory."""

    bound = copy.copy(store)
    proxy = _BoundTransactionConnection(connection, state)
    bound._connect = lambda: proxy
    return bound


def _project_delegations(
    store: Any,
    delegations: tuple[ValidatedFinalizationDelegation, ...],
) -> tuple[ValidatedFinalizationDelegation, ...]:
    capture_content = store._capture_content_enabled()
    return tuple(
        ValidatedFinalizationDelegation(
            recommended_agent=item.recommended_agent,
            status=item.status,
            backend=item.backend,
            work_unit_id=item.work_unit_id,
            executed_worker_kind=item.executed_worker_kind,
            executed_worker_id=item.executed_worker_id,
            native_run_id=item.native_run_id,
            skip_reason=project_delegation_detail(
                item.skip_reason,
                field="skip_reason",
                capture_content=capture_content,
            ),
            error=project_delegation_detail(
                item.error,
                field="error",
                capture_content=capture_content,
            ),
        )
        for item in delegations
    )


def _load_batch_run(
    conn: Any,
    batch: ValidatedFinalizationEvidenceBatch,
) -> tuple[Any, bool, str]:
    run = conn.execute(
        "SELECT * FROM runs WHERE trace_id = ?",
        (batch.trace_id,),
    ).fetchone()
    if run is None:
        raise FinalizationEvidenceConflictError(
            "trace_id does not identify an existing active turn"
        )
    if str(run["session_id"] or "") != batch.session_id:
        raise FinalizationEvidenceConflictError("trace_id does not belong to session_id")
    status = str(run["status"] or "")
    terminal = status not in {"active", "evidence_only"}
    if terminal and batch.item_count:
        raise FinalizationEvidenceConflictError(
            "terminal turns cannot accept new finalization evidence"
        )
    if not terminal and (run["ended_at"] or run["terminal_finalization_id"]):
        raise FinalizationEvidenceConflictError("open turn has inconsistent terminal state")
    if terminal and (not run["ended_at"] or not run["terminal_finalization_id"]):
        raise FinalizationEvidenceConflictError("terminal turn has incomplete finalization state")
    if not terminal and status != "active":
        raise FinalizationEvidenceConflictError("trace_id has not completed preflight")
    if not terminal and str(run["preflight_state"] or "") != "ready":
        raise FinalizationEvidenceConflictError("trace_id has not completed preflight")
    authoritative_host = str(run["host"] or "unknown").strip()[:MAX_DELEGATION_HOST_CHARS]
    return run, terminal, authoritative_host or "unknown"


def _load_existing_delegations(
    conn: Any,
    *,
    trace_id: str,
    delegations: tuple[ValidatedFinalizationDelegation, ...],
) -> dict[str, Any]:
    if not delegations:
        return {}
    work_units = tuple(item.work_unit_id for item in delegations)
    placeholders = ",".join("?" for _item in work_units)
    rows = conn.execute(
        f"SELECT * FROM delegation_events WHERE trace_id = ? AND work_unit_id IN ({placeholders})",  # nosec B608
        (trace_id, *work_units),
    ).fetchall()
    return {str(row["work_unit_id"]): row for row in rows}


def _validate_persisted_delegations(
    conn: Any,
    *,
    batch: ValidatedFinalizationEvidenceBatch,
    delegations: tuple[ValidatedFinalizationDelegation, ...],
    existing_by_unit: Mapping[str, Any],
    authoritative_host: str,
    now: str,
) -> None:
    for item in delegations:
        existing = existing_by_unit.get(item.work_unit_id)
        try:
            if existing is None:
                _require_execution_correlation(
                    status=item.status,
                    trace_id=batch.trace_id,
                    session_id=batch.session_id,
                    work_unit_id=item.work_unit_id,
                    backend=item.backend,
                    worker_kind=item.executed_worker_kind,
                    worker_id=item.executed_worker_id,
                    native_run_id=item.native_run_id,
                )
                continue
            if str(existing["session_id"] or "") != batch.session_id:
                raise ValueError("delegation belongs to another session")
            _prepare_delegation_transition(
                conn,
                existing,
                status=item.status,
                backend=item.backend,
                error=item.error,
                recommended_agent=item.recommended_agent,
                executed_worker_kind=item.executed_worker_kind,
                executed_worker_id=item.executed_worker_id,
                native_run_id=item.native_run_id,
                skip_reason=item.skip_reason,
                host=authoritative_host,
                now=now,
            )
        except ValueError as exc:
            raise FinalizationEvidenceConflictError(
                "finalization delegation conflicts with authoritative evidence"
            ) from exc


def _write_batch_evidence(
    store: Any,
    conn: Any,
    *,
    batch: ValidatedFinalizationEvidenceBatch,
    delegations: tuple[ValidatedFinalizationDelegation, ...],
    existing_by_unit: Mapping[str, Any],
    authoritative_host: str,
    now: str,
) -> tuple[list[dict[str, str]], list[str]]:
    skill_receipts: list[dict[str, str]] = []
    for skill in batch.skills:
        event_id = store._uuid()
        conn.execute(
            "INSERT INTO skills_loaded "
            "(id, session_id, trace_id, skill_name, loaded_at) VALUES (?, ?, ?, ?, ?)",
            (event_id, batch.session_id, batch.trace_id, skill, now),
        )
        skill_receipts.append({"id": event_id, "skill_name": skill})

    delegation_ids: list[str] = []
    for item in delegations:
        existing = existing_by_unit.get(item.work_unit_id)
        if existing is not None:
            store._merge_delegation_transition(
                conn,
                existing,
                status=item.status,
                backend=item.backend,
                error=item.error,
                recommended_agent=item.recommended_agent,
                executed_worker_kind=item.executed_worker_kind,
                executed_worker_id=item.executed_worker_id,
                native_run_id=item.native_run_id,
                skip_reason=item.skip_reason,
                host=authoritative_host,
                now=now,
            )
            delegation_ids.append(str(existing["id"]))
            continue
        event_id = store._uuid()
        conn.execute(
            "INSERT INTO delegation_events "
            "(id, trace_id, session_id, host, work_unit_id, recommended_agent, "
            "status, backend, executed_worker_kind, executed_worker_id, native_run_id, "
            "skip_reason, error, started_at, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                batch.trace_id,
                batch.session_id,
                authoritative_host,
                item.work_unit_id,
                item.recommended_agent,
                item.status,
                item.backend,
                item.executed_worker_kind,
                item.executed_worker_id,
                item.native_run_id,
                item.skip_reason,
                item.error,
                now,
                now if item.status in TERMINAL_DELEGATION_STATUSES else None,
            ),
        )
        attach_consumed_activation_to_delegation(
            conn,
            event_id=event_id,
            trace_id=batch.trace_id,
            work_unit_id=item.work_unit_id,
        )
        delegation_ids.append(event_id)
    return skill_receipts, delegation_ids


def _run_bound_finalizer(
    store: Any,
    conn: Any,
    *,
    authoritative_host: str,
    finalizer: Callable[[Any, str], Mapping[str, Any]],
) -> tuple[dict[str, Any], _BoundTransactionState]:
    state = _BoundTransactionState()
    result = dict(finalizer(_transaction_bound_store(store, conn, state), authoritative_host))
    if (
        not isinstance(result.get("action"), str)
        or not isinstance(result.get("text"), str)
        or not isinstance(result.get("missing"), list)
        or not all(isinstance(item, str) for item in result["missing"])
    ):
        raise RuntimeError("finalizer returned an invalid result contract")
    return result, state


def _terminal_receipt_row(
    conn: Any,
    *,
    batch: ValidatedFinalizationEvidenceBatch,
    authoritative_host: str,
    response_hash: str,
) -> Any | None:
    row = conn.execute(
        "SELECT run.status, run.ended_at, run.terminal_finalization_id, "
        "run.evidence_revision, event.action, event.response_hash, "
        "event.terminal_status, event.host FROM runs AS run "
        "JOIN finalization_events AS event ON event.id = run.terminal_finalization_id "
        "WHERE run.session_id = ? AND run.trace_id = ?",
        (batch.session_id, batch.trace_id),
    ).fetchone()
    valid = bool(
        row is not None
        and str(row["action"] or "") == "accept"
        and str(row["response_hash"] or "") == response_hash
        and str(row["terminal_status"] or "") == "completed"
        and str(row["status"] or "") == "completed"
        and row["ended_at"]
        and row["terminal_finalization_id"]
        and str(row["host"] or "") == authoritative_host
    )
    return row if valid else None


def _load_delegation_receipts(conn: Any, delegation_ids: list[str]) -> list[dict[str, str]]:
    if not delegation_ids:
        return []
    placeholders = ",".join("?" for _item in delegation_ids)
    rows = conn.execute(
        "SELECT id, work_unit_id, recommended_agent, status, backend, "
        "executed_worker_kind, executed_worker_id, native_run_id "
        f"FROM delegation_events WHERE id IN ({placeholders})",  # nosec B608
        tuple(delegation_ids),
    ).fetchall()
    by_id = {str(row["id"]): row for row in rows}
    if set(by_id) != set(delegation_ids):
        raise RuntimeError("delegation receipt completeness check failed")
    return [
        {key: str(by_id[event_id][key] or "") for key in _DELEGATION_RECEIPT_FIELDS}
        for event_id in delegation_ids
    ]


def _persistence_failure(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "finalization": {
            "action": "continue",
            "text": result["text"],
            "missing": ["evidence_persistence"],
        },
        "receipt": None,
    }


class FinalizationBatchStoreMixin:
    """Commit one finalization envelope and terminal receipt all-or-nothing."""

    def finalize_evidence_batch(
        self,
        *,
        session_id: object,
        trace_id: object,
        skills_loaded: object,
        delegations: object,
        finalizer: Callable[[Any, str], Mapping[str, Any]],
    ) -> dict[str, Any]:
        batch = validate_finalization_evidence_batch(
            session_id=session_id,
            trace_id=trace_id,
            skills_loaded=skills_loaded,
            delegations=delegations,
        )
        if not callable(finalizer):
            raise FinalizationEvidenceError("finalizer must be callable")
        projected_delegations = _project_delegations(self, batch.delegations)
        projected_bytes = _encoded_batch_bytes(
            session_id=batch.session_id,
            trace_id=batch.trace_id,
            skills=batch.skills,
            delegations=projected_delegations,
        )
        if projected_bytes > MAX_FINALIZATION_EVIDENCE_BYTES:
            raise FinalizationEvidenceError("finalization evidence exceeds the byte limit")

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            _run, terminal, authoritative_host = _load_batch_run(conn, batch)
            existing_by_unit = _load_existing_delegations(
                conn,
                trace_id=batch.trace_id,
                delegations=projected_delegations,
            )
            now = self._now()
            if not terminal:
                _validate_persisted_delegations(
                    conn,
                    batch=batch,
                    delegations=projected_delegations,
                    existing_by_unit=existing_by_unit,
                    authoritative_host=authoritative_host,
                    now=now,
                )
                skill_receipts, delegation_ids = _write_batch_evidence(
                    self,
                    conn,
                    batch=batch,
                    delegations=projected_delegations,
                    existing_by_unit=existing_by_unit,
                    authoritative_host=authoritative_host,
                    now=now,
                )
            else:
                skill_receipts, delegation_ids = [], []

            result, transaction_state = _run_bound_finalizer(
                self,
                conn,
                authoritative_host=authoritative_host,
                finalizer=finalizer,
            )
            if transaction_state.rollback_requested or result["action"] != "accept":
                conn.rollback()
                return {"finalization": result, "receipt": None}

            digest = sha256(result["text"].encode("utf-8", errors="surrogatepass")).hexdigest()
            terminal_row = _terminal_receipt_row(
                conn,
                batch=batch,
                authoritative_host=authoritative_host,
                response_hash=digest,
            )
            if terminal_row is None:
                conn.rollback()
                return _persistence_failure(result)

            receipt = {
                "outcome": "replay" if terminal else "committed",
                "session_id": batch.session_id,
                "trace_id": batch.trace_id,
                "host": authoritative_host,
                "item_count": batch.item_count,
                "skill_count": len(batch.skills),
                "delegation_count": len(batch.delegations),
                "encoded_bytes": projected_bytes,
                "skills": skill_receipts,
                "delegations": _load_delegation_receipts(conn, delegation_ids),
                "finalization_event_id": str(terminal_row["terminal_finalization_id"]),
                "response_hash": digest,
                "terminal_status": str(terminal_row["status"]),
                "evidence_revision": int(terminal_row["evidence_revision"]),
            }
            conn.commit()
            return {"finalization": result, "receipt": receipt}
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()


__all__ = [
    "MAX_FINALIZATION_EVIDENCE_BYTES",
    "MAX_FINALIZATION_EVIDENCE_ITEMS",
    "MAX_FINALIZATION_SKILL_NAME_CHARS",
    "FinalizationBatchStoreMixin",
    "FinalizationEvidenceConflictError",
    "FinalizationEvidenceError",
    "ValidatedFinalizationEvidenceBatch",
    "validate_finalization_evidence_batch",
    "validate_finalization_evidence_items",
]
