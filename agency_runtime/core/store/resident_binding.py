"""Atomic persistence for the compact resident-manager host binding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.resident_manager_binding import (
    RESIDENT_MANAGER_BINDING_VERSION,
    ResidentControlEpoch,
    ResidentManagerBinding,
    build_resident_control_epoch,
    build_resident_manager_binding,
    canonical_resident_manager_host,
    resident_manager_host_mode,
    validate_resident_manager_binding,
)
from agency_runtime.core.resident_managers import RESIDENT_MANAGER_KERNEL_REFERENCE
from agency_runtime.core.runtime_control import (
    RuntimeControlError,
    read_effective_runtime_control_snapshot,
)
from agency_runtime.core.store.schema import STORE_CLOCK_SQL

_MAX_GENERATION = 2**63 - 1


@dataclass(frozen=True, slots=True)
class _BindingState:
    restore_generation: int
    applied_restore_generation: int
    pending_restore_generation: int
    delivery_state: str
    pending_delivery_mode: str
    pending_trace_id: str
    last_trace_id: str


@dataclass(frozen=True, slots=True)
class _ControlState:
    enabled: bool
    epoch: ResidentControlEpoch


def _binding_row(conn: Any, *, session_id: str, host: str) -> Any:
    return conn.execute(
        "SELECT session_id, host, binding_id, binding_version, kernel_version, "
        "kernel_hash, restore_generation, applied_restore_generation, "
        "pending_restore_generation, master_control_generation, "
        "master_control_materialized, host_control_generation, "
        "host_control_materialized, "
        "bound_at, updated_at, last_trace_id, delivery_state, "
        "pending_delivery_mode, pending_trace_id FROM resident_manager_bindings "
        "WHERE session_id = ? AND host = ?",
        (session_id, host),
    ).fetchone()


def _host_control_state(conn: Any, *, host: str) -> tuple[bool, int, bool]:
    row = conn.execute(
        "SELECT enabled, generation FROM host_controls WHERE host = ?",
        (host,),
    ).fetchone()
    if row is None:
        return True, 0, False
    try:
        enabled_value = int(row["enabled"])
        generation = int(row["generation"])
    except (TypeError, ValueError, OverflowError) as exc:
        raise RuntimeError("resident-manager host control state is invalid") from exc
    if enabled_value not in {0, 1} or not 0 <= generation <= _MAX_GENERATION:
        raise RuntimeError("resident-manager host control state is invalid")
    return bool(enabled_value), generation, True


def _master_control_state() -> tuple[bool, int | None, bool]:
    try:
        snapshot = read_effective_runtime_control_snapshot(use_cache=False)
    except (RuntimeControlError, OSError, UnicodeError, ValueError):
        return True, None, False
    return snapshot.enabled, snapshot.generation, snapshot.materialized


def _current_control_state(conn: Any, *, host: str) -> _ControlState:
    host_enabled, host_generation, host_materialized = _host_control_state(
        conn,
        host=host,
    )
    master_enabled, master_generation, master_materialized = _master_control_state()
    return _ControlState(
        enabled=bool(master_enabled and host_enabled),
        epoch=build_resident_control_epoch(
            master_generation=master_generation,
            master_materialized=master_materialized,
            host_generation=host_generation,
            host_materialized=host_materialized,
        ),
    )


def _row_matches_control_epoch(row: Any, epoch: ResidentControlEpoch) -> bool:
    try:
        stored_master_generation = row["master_control_generation"]
        master_generation = (
            None if stored_master_generation is None else int(stored_master_generation)
        )
        master_materialized = int(row["master_control_materialized"])
        host_generation = int(row["host_control_generation"])
        host_materialized = int(row["host_control_materialized"])
    except (TypeError, ValueError, OverflowError) as exc:
        raise RuntimeError("resident-manager stored control epoch is invalid") from exc
    if master_materialized not in {0, 1} or host_materialized not in {0, 1}:
        raise RuntimeError("resident-manager stored control epoch is invalid")
    try:
        stored = build_resident_control_epoch(
            master_generation=master_generation,
            master_materialized=bool(master_materialized),
            host_generation=host_generation,
            host_materialized=bool(host_materialized),
        )
    except ValueError as exc:
        raise RuntimeError("resident-manager stored control epoch is invalid") from exc
    return stored == epoch


def _row_uses_current_contract(row: Any) -> bool:
    if row is None:
        return False
    kernel = RESIDENT_MANAGER_KERNEL_REFERENCE
    try:
        binding_version = int(row["binding_version"])
        kernel_version = int(row["kernel_version"])
    except (TypeError, ValueError, OverflowError) as exc:
        raise RuntimeError("resident-manager binding version state is invalid") from exc
    return bool(
        binding_version == RESIDENT_MANAGER_BINDING_VERSION
        and kernel_version == kernel.version
        and str(row["kernel_hash"] or "") == kernel.content_hash
    )


def _validated_optional_trace(value: object, *, field: str) -> str:
    normalized = str(value or "")
    if not normalized:
        return ""
    try:
        return validate_correlation_id(normalized, field=field)
    except ValueError as exc:
        raise RuntimeError(f"resident-manager {field} is invalid") from exc


def _validate_current_row(row: Any, expected: ResidentManagerBinding) -> _BindingState:
    """Validate mutable generation and acknowledgement state before use."""

    try:
        restore_generation = int(row["restore_generation"])
        applied_generation = int(row["applied_restore_generation"])
        pending_restore_generation = int(row["pending_restore_generation"])
    except (TypeError, ValueError, OverflowError) as exc:
        raise RuntimeError("resident-manager binding generation is invalid") from exc
    if (
        str(row["binding_id"] or "") != expected.binding_id
        or not 0
        <= applied_generation
        <= pending_restore_generation
        <= restore_generation
        <= _MAX_GENERATION
        or not _row_matches_control_epoch(row, expected.control_epoch)
        or not str(row["bound_at"] or "")
        or not str(row["updated_at"] or "")
    ):
        raise RuntimeError("resident-manager binding state failed integrity validation")

    delivery_state = str(row["delivery_state"] or "")
    pending_mode = str(row["pending_delivery_mode"] or "")
    pending_trace = _validated_optional_trace(
        row["pending_trace_id"],
        field="pending_trace_id",
    )
    last_trace = _validated_optional_trace(row["last_trace_id"], field="last_trace_id")
    if delivery_state == "pending":
        if pending_mode not in {"injected", "restored"} or not pending_trace:
            raise RuntimeError("resident-manager pending delivery state is invalid")
        if pending_mode == "restored" and pending_restore_generation <= applied_generation:
            raise RuntimeError("resident-manager pending restore generation is invalid")
        if pending_mode == "injected" and pending_restore_generation != applied_generation:
            raise RuntimeError("resident-manager pending injection generation is invalid")
    elif delivery_state == "acknowledged":
        if pending_mode or pending_trace or pending_restore_generation != applied_generation:
            raise RuntimeError("resident-manager acknowledged delivery state is invalid")
    else:
        raise RuntimeError("resident-manager delivery acknowledgement state is invalid")
    return _BindingState(
        restore_generation=restore_generation,
        applied_restore_generation=applied_generation,
        pending_restore_generation=pending_restore_generation,
        delivery_state=delivery_state,
        pending_delivery_mode=pending_mode,
        pending_trace_id=pending_trace,
        last_trace_id=last_trace,
    )


def _planned_delivery(state: _BindingState) -> str:
    if state.delivery_state == "pending":
        return state.pending_delivery_mode
    if state.restore_generation > state.applied_restore_generation:
        return "restored"
    return "reused"


class ResidentManagerBindingStoreMixin:
    """Session-scoped manager injection, reuse, restoration, and retirement."""

    def plan_resident_manager_binding(
        self,
        *,
        session_id: str,
        host: str,
    ) -> ResidentManagerBinding:
        """Read the delivery mode that an atomic ready commit must later claim."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        canonical_host = canonical_resident_manager_host(host)
        conn = self._connect()
        try:
            control = _current_control_state(conn, host=canonical_host)
            if not control.enabled:
                raise RuntimeError("resident-manager controls are disabled")
            if resident_manager_host_mode(canonical_host) == "request_scoped":
                return build_resident_manager_binding(
                    session_id=normalized_session,
                    host=canonical_host,
                    delivery_mode="request",
                    control_epoch=control.epoch,
                )

            expected = build_resident_manager_binding(
                session_id=normalized_session,
                host=canonical_host,
                delivery_mode="injected",
                control_epoch=control.epoch,
            )
            if not control.epoch.reusable:
                return expected
            row = _binding_row(conn, session_id=normalized_session, host=canonical_host)
            if (
                row is None
                or not _row_uses_current_contract(row)
                or not _row_matches_control_epoch(row, control.epoch)
            ):
                return expected
            state = _validate_current_row(row, expected)
            return build_resident_manager_binding(
                session_id=normalized_session,
                host=canonical_host,
                delivery_mode=_planned_delivery(state),
                control_epoch=control.epoch,
            )
        finally:
            conn.close()

    def mark_resident_manager_restore_required(
        self,
        *,
        session_id: str,
        host: str,
    ) -> bool:
        """Record every authoritative context-loss signal without losing pending ones."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        canonical_host = canonical_resident_manager_host(host)
        if resident_manager_host_mode(canonical_host) == "request_scoped":
            return False
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute(
                "SELECT restore_generation FROM resident_manager_bindings "
                "WHERE session_id = ? AND host = ?",
                (normalized_session, canonical_host),
            ).fetchone()
            if current is None:
                conn.commit()
                return False
            try:
                restore_generation = int(current["restore_generation"])
            except (TypeError, ValueError, OverflowError) as exc:
                raise RuntimeError("resident-manager restore generation is invalid") from exc
            if not 0 <= restore_generation <= _MAX_GENERATION:
                raise RuntimeError("resident-manager restore generation is invalid")
            if restore_generation >= _MAX_GENERATION:
                raise RuntimeError("resident-manager restore generation is exhausted")
            changed = conn.execute(
                "UPDATE resident_manager_bindings SET "
                "restore_generation = restore_generation + 1, "
                f"updated_at = {STORE_CLOCK_SQL} "  # nosec B608
                "WHERE session_id = ? AND host = ? AND restore_generation = ?",
                (normalized_session, canonical_host, restore_generation),
            )
            conn.commit()
            return changed.rowcount == 1
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def retire_resident_manager_binding(
        self,
        *,
        session_id: str,
        host: str,
    ) -> bool:
        """Drop one ended host-session binding without altering historical recipes."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        canonical_host = canonical_resident_manager_host(host)
        if resident_manager_host_mode(canonical_host) == "request_scoped":
            return False
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            deleted = conn.execute(
                "DELETE FROM resident_manager_bindings WHERE session_id = ? AND host = ?",
                (normalized_session, canonical_host),
            )
            conn.commit()
            return deleted.rowcount == 1
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _commit_new_binding(
        self,
        conn: Any,
        *,
        session_id: str,
        trace_id: str,
        binding: ResidentManagerBinding,
    ) -> bool:
        if binding.delivery_mode != "injected":
            return False
        kernel = RESIDENT_MANAGER_KERNEL_REFERENCE
        conn.execute(
            "INSERT INTO resident_manager_bindings "
            "(session_id, host, binding_id, binding_version, kernel_version, "
            "kernel_hash, restore_generation, applied_restore_generation, "
            "pending_restore_generation, master_control_generation, "
            "master_control_materialized, host_control_generation, "
            "host_control_materialized, "
            "bound_at, updated_at, last_trace_id, delivery_state, "
            "pending_delivery_mode, pending_trace_id) "
            f"VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?, ?, ?, {STORE_CLOCK_SQL}, "  # nosec B608
            f"{STORE_CLOCK_SQL}, ?, 'pending', 'injected', ?)",  # nosec B608
            (
                session_id,
                binding.host,
                binding.binding_id,
                binding.version,
                kernel.version,
                kernel.content_hash,
                binding.control_epoch.master_generation,
                int(binding.control_epoch.master_materialized),
                binding.control_epoch.host_generation,
                int(binding.control_epoch.host_materialized),
                trace_id,
                trace_id,
            ),
        )
        return True

    def _replace_stale_binding(
        self,
        conn: Any,
        *,
        session_id: str,
        trace_id: str,
        binding: ResidentManagerBinding,
    ) -> bool:
        if binding.delivery_mode != "injected":
            return False
        kernel = RESIDENT_MANAGER_KERNEL_REFERENCE
        replaced = conn.execute(
            "UPDATE resident_manager_bindings SET binding_id = ?, "
            "binding_version = ?, kernel_version = ?, kernel_hash = ?, "
            "restore_generation = 0, applied_restore_generation = 0, "
            "pending_restore_generation = 0, master_control_generation = ?, "
            "master_control_materialized = ?, host_control_generation = ?, "
            "host_control_materialized = ?, "
            f"bound_at = {STORE_CLOCK_SQL}, updated_at = {STORE_CLOCK_SQL}, "  # nosec B608
            "last_trace_id = ?, delivery_state = 'pending', "
            "pending_delivery_mode = 'injected', pending_trace_id = ? "
            "WHERE session_id = ? AND host = ?",
            (
                binding.binding_id,
                binding.version,
                kernel.version,
                kernel.content_hash,
                binding.control_epoch.master_generation,
                int(binding.control_epoch.master_materialized),
                binding.control_epoch.host_generation,
                int(binding.control_epoch.host_materialized),
                trace_id,
                trace_id,
                session_id,
                binding.host,
            ),
        )
        return replaced.rowcount == 1

    def _commit_current_binding(
        self,
        conn: Any,
        *,
        session_id: str,
        trace_id: str,
        binding: ResidentManagerBinding,
        state: _BindingState,
    ) -> bool:
        if state.delivery_state == "pending" and state.pending_trace_id != trace_id:
            return False
        required_mode = _planned_delivery(state)
        if binding.delivery_mode != required_mode:
            return False
        pending = state.delivery_state == "pending" or required_mode == "restored"
        delivery_state = "pending" if pending else "acknowledged"
        pending_mode = required_mode if pending else ""
        pending_trace = trace_id if pending else ""
        pending_restore_generation = (
            state.pending_restore_generation
            if state.delivery_state == "pending"
            else state.restore_generation
            if required_mode == "restored"
            else state.applied_restore_generation
        )
        updated = conn.execute(
            "UPDATE resident_manager_bindings SET delivery_state = ?, "
            "pending_delivery_mode = ?, pending_trace_id = ?, "
            "pending_restore_generation = ?, "
            f"updated_at = {STORE_CLOCK_SQL}, last_trace_id = ? "  # nosec B608
            "WHERE session_id = ? AND host = ? AND binding_id = ? "
            "AND restore_generation = ? AND applied_restore_generation = ? "
            "AND pending_restore_generation = ? "
            "AND delivery_state = ? AND pending_delivery_mode = ? "
            "AND pending_trace_id = ?",
            (
                delivery_state,
                pending_mode,
                pending_trace,
                pending_restore_generation,
                trace_id,
                session_id,
                binding.host,
                binding.binding_id,
                state.restore_generation,
                state.applied_restore_generation,
                state.pending_restore_generation,
                state.delivery_state,
                state.pending_delivery_mode,
                state.pending_trace_id,
            ),
        )
        return updated.rowcount == 1

    def _commit_resident_manager_binding(
        self,
        conn: Any,
        *,
        session_id: str,
        trace_id: str,
        binding: object,
    ) -> bool:
        """Claim one planned delivery inside the preflight-ready transaction."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        expected = validate_resident_manager_binding(binding, session_id=normalized_session)
        current_control = _current_control_state(conn, host=expected.host)
        if not current_control.enabled or current_control.epoch != expected.control_epoch:
            return False
        if expected.host_mode == "request_scoped":
            return expected.delivery_mode == "request"
        if not expected.control_epoch.reusable:
            if expected.delivery_mode != "injected":
                return False
            conn.execute(
                "DELETE FROM resident_manager_bindings WHERE session_id = ? AND host = ?",
                (normalized_session, expected.host),
            )
            return True

        row = _binding_row(conn, session_id=normalized_session, host=expected.host)
        if row is None:
            return self._commit_new_binding(
                conn,
                session_id=normalized_session,
                trace_id=normalized_trace,
                binding=expected,
            )
        if not _row_uses_current_contract(row) or not _row_matches_control_epoch(
            row,
            expected.control_epoch,
        ):
            return self._replace_stale_binding(
                conn,
                session_id=normalized_session,
                trace_id=normalized_trace,
                binding=expected,
            )
        return self._commit_current_binding(
            conn,
            session_id=normalized_session,
            trace_id=normalized_trace,
            binding=expected,
            state=_validate_current_row(row, expected),
        )

    def acknowledge_resident_manager_binding(
        self,
        *,
        session_id: str,
        host: str,
        trace_id: str,
        binding: object,
    ) -> bool:
        """Acknowledge only the exact binding consumed by one correlated host turn."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        canonical_host = canonical_resident_manager_host(host)
        expected = validate_resident_manager_binding(binding, session_id=normalized_session)
        if expected.host != canonical_host:
            return False
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            current_control = _current_control_state(conn, host=canonical_host)
            if not current_control.enabled or current_control.epoch != expected.control_epoch:
                conn.commit()
                return False
            if resident_manager_host_mode(canonical_host) == "request_scoped":
                conn.commit()
                return expected.delivery_mode == "request"
            if not expected.control_epoch.reusable:
                conn.commit()
                return expected.delivery_mode == "injected"
            row = _binding_row(conn, session_id=normalized_session, host=canonical_host)
            if (
                row is None
                or not _row_uses_current_contract(row)
                or not _row_matches_control_epoch(row, expected.control_epoch)
            ):
                conn.commit()
                return False
            state = _validate_current_row(row, expected)
            if state.delivery_state == "acknowledged" and state.last_trace_id == normalized_trace:
                conn.commit()
                return True
            if state.delivery_state != "pending" or state.pending_trace_id != normalized_trace:
                conn.commit()
                return False
            applied = (
                state.pending_restore_generation
                if state.pending_delivery_mode == "restored"
                else state.applied_restore_generation
            )
            changed = conn.execute(
                "UPDATE resident_manager_bindings SET delivery_state = 'acknowledged', "
                "pending_delivery_mode = '', pending_trace_id = '', "
                "applied_restore_generation = ?, pending_restore_generation = ?, "
                f"updated_at = {STORE_CLOCK_SQL} "  # nosec B608
                "WHERE session_id = ? AND host = ? AND binding_id = ? "
                "AND delivery_state = 'pending' AND pending_delivery_mode = ? "
                "AND pending_trace_id = ? AND restore_generation = ? "
                "AND applied_restore_generation = ? AND pending_restore_generation = ?",
                (
                    applied,
                    applied,
                    normalized_session,
                    canonical_host,
                    expected.binding_id,
                    state.pending_delivery_mode,
                    normalized_trace,
                    state.restore_generation,
                    state.applied_restore_generation,
                    state.pending_restore_generation,
                ),
            )
            conn.commit()
            return changed.rowcount == 1
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def validate_committed_resident_manager_binding(
        self,
        *,
        session_id: str,
        trace_id: str,
        binding: object,
    ) -> bool:
        """Validate that a ready recipe remains safe to replay after lifecycle changes."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        expected = validate_resident_manager_binding(binding, session_id=normalized_session)
        conn = self._connect()
        try:
            current_control = _current_control_state(conn, host=expected.host)
            if not current_control.enabled or current_control.epoch != expected.control_epoch:
                return False
            if expected.host_mode == "request_scoped":
                return expected.delivery_mode == "request"
            if not expected.control_epoch.reusable:
                return expected.delivery_mode == "injected"
            row = _binding_row(conn, session_id=normalized_session, host=expected.host)
            if (
                row is None
                or not _row_uses_current_contract(row)
                or not _row_matches_control_epoch(row, expected.control_epoch)
            ):
                return False
            state = _validate_current_row(row, expected)
            if expected.delivery_mode == "reused":
                return bool(
                    state.delivery_state == "acknowledged"
                    and state.restore_generation == state.applied_restore_generation
                )
            if state.delivery_state == "pending":
                return bool(
                    state.pending_delivery_mode == expected.delivery_mode
                    and state.pending_trace_id == normalized_trace
                )
            return bool(
                state.last_trace_id == normalized_trace
                and state.restore_generation == state.applied_restore_generation
            )
        finally:
            conn.close()


__all__ = ["ResidentManagerBindingStoreMixin"]
