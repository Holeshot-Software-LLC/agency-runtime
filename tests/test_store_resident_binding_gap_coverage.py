"""Adversarial branch coverage for resident-manager store persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.resident_manager_binding import (
    ResidentControlEpoch,
    ResidentManagerBinding,
    build_resident_control_epoch,
    build_resident_manager_binding,
)
from agency_runtime.core.runtime_control import RuntimeControlError, RuntimeControlSnapshot
from agency_runtime.core.store import resident_binding as subject
from agency_runtime.core.store.sqlite import Store


class _Result:
    def __init__(self, row: Any = None, *, rowcount: int = 1) -> None:
        self._row = row
        self.rowcount = rowcount

    def fetchone(self) -> Any:
        return self._row


class _Connection:
    def __init__(self, row: Any = None, *, fail_on: str = "") -> None:
        self.row = row
        self.fail_on = fail_on
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def execute(self, sql: str, *_args: Any, **_kwargs: Any) -> _Result:
        if self.fail_on and self.fail_on in sql:
            raise RuntimeError("synthetic resident binding failure")
        return _Result(self.row if sql.lstrip().startswith("SELECT") else None)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def _stable_master_control(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = RuntimeControlSnapshot(
        schema_version=1,
        enabled=True,
        generation=0,
        updated_at="2026-07-18T00:00:00Z",
        source="test",
        materialized=True,
    )
    monkeypatch.setattr(
        subject,
        "read_effective_runtime_control_snapshot",
        lambda **_kwargs: snapshot,
    )


def _epoch(*, reusable: bool = True) -> ResidentControlEpoch:
    return build_resident_control_epoch(
        master_generation=0 if reusable else None,
        master_materialized=reusable,
        host_generation=0,
        host_materialized=reusable,
    )


def _binding(
    mode: str = "injected",
    *,
    host: str = "claude",
    epoch: ResidentControlEpoch | None = None,
) -> ResidentManagerBinding:
    return build_resident_manager_binding(
        session_id="session",
        host=host,
        delivery_mode=mode,
        control_epoch=epoch or _epoch(),
    )


def _current_row(
    binding: ResidentManagerBinding,
    *,
    delivery_state: str = "acknowledged",
    restore_generation: Any = 0,
    applied_restore_generation: Any = 0,
    pending_restore_generation: Any = 0,
    pending_delivery_mode: str = "",
    pending_trace_id: str = "",
    last_trace_id: str = "turn",
) -> dict[str, Any]:
    return {
        "binding_id": binding.binding_id,
        "binding_version": binding.version,
        "kernel_version": subject.RESIDENT_MANAGER_KERNEL_REFERENCE.version,
        "kernel_hash": subject.RESIDENT_MANAGER_KERNEL_REFERENCE.content_hash,
        "restore_generation": restore_generation,
        "applied_restore_generation": applied_restore_generation,
        "pending_restore_generation": pending_restore_generation,
        "master_control_generation": binding.control_epoch.master_generation,
        "master_control_materialized": int(binding.control_epoch.master_materialized),
        "host_control_generation": binding.control_epoch.host_generation,
        "host_control_materialized": int(binding.control_epoch.host_materialized),
        "bound_at": "2026-07-18T00:00:00Z",
        "updated_at": "2026-07-18T00:00:00Z",
        "last_trace_id": last_trace_id,
        "delivery_state": delivery_state,
        "pending_delivery_mode": pending_delivery_mode,
        "pending_trace_id": pending_trace_id,
    }


def test_control_state_helpers_reject_corrupt_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RuntimeError, match="host control state"):
        subject._host_control_state(
            _Connection({"enabled": object(), "generation": 0}),
            host="claude",
        )
    with pytest.raises(RuntimeError, match="host control state"):
        subject._host_control_state(
            _Connection({"enabled": 2, "generation": 0}),
            host="claude",
        )

    monkeypatch.setattr(
        subject,
        "read_effective_runtime_control_snapshot",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeControlError("unreadable")),
    )
    assert subject._master_control_state() == (True, None, False)


def test_stored_epoch_and_contract_helpers_fail_closed() -> None:
    epoch = _epoch()
    row = _current_row(_binding())
    with pytest.raises(RuntimeError, match="stored control epoch"):
        subject._row_matches_control_epoch(
            {**row, "host_control_generation": object()},
            epoch,
        )
    with pytest.raises(RuntimeError, match="stored control epoch"):
        subject._row_matches_control_epoch(
            {**row, "master_control_materialized": 2},
            epoch,
        )
    with pytest.raises(RuntimeError, match="stored control epoch"):
        subject._row_matches_control_epoch(
            {
                **row,
                "master_control_generation": None,
                "master_control_materialized": 1,
            },
            epoch,
        )
    assert subject._row_uses_current_contract(None) is False
    with pytest.raises(RuntimeError, match="binding version state"):
        subject._row_uses_current_contract({**row, "binding_version": object()})
    with pytest.raises(RuntimeError, match="pending_trace_id"):
        subject._validated_optional_trace("bad\x00trace", field="pending_trace_id")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"restore_generation": object()}, "generation"),
        ({"binding_id": "wrong"}, "integrity"),
        (
            {
                "delivery_state": "pending",
                "pending_delivery_mode": "",
                "pending_trace_id": "",
            },
            "pending delivery",
        ),
        (
            {
                "delivery_state": "pending",
                "restore_generation": 1,
                "applied_restore_generation": 1,
                "pending_restore_generation": 1,
                "pending_delivery_mode": "restored",
                "pending_trace_id": "turn",
            },
            "pending restore",
        ),
        (
            {
                "delivery_state": "pending",
                "restore_generation": 1,
                "applied_restore_generation": 0,
                "pending_restore_generation": 1,
                "pending_delivery_mode": "injected",
                "pending_trace_id": "turn",
            },
            "pending injection",
        ),
        ({"pending_delivery_mode": "injected"}, "acknowledged"),
        ({"delivery_state": "unknown"}, "acknowledgement"),
    ],
)
def test_current_row_validation_rejects_each_invalid_state(
    changes: dict[str, Any],
    message: str,
) -> None:
    binding = _binding()
    with pytest.raises(RuntimeError, match=message):
        subject._validate_current_row(
            {**_current_row(binding), **changes},
            binding,
        )


def test_planned_delivery_preserves_an_existing_pending_claim() -> None:
    state = subject._BindingState(
        restore_generation=1,
        applied_restore_generation=0,
        pending_restore_generation=1,
        delivery_state="pending",
        pending_delivery_mode="restored",
        pending_trace_id="turn",
        last_trace_id="",
    )
    assert subject._planned_delivery(state) == "restored"


def test_plan_restore_and_retire_cover_disabled_and_request_scoped_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    monkeypatch.setattr(
        subject,
        "_current_control_state",
        lambda *_args, **_kwargs: subject._ControlState(enabled=False, epoch=_epoch()),
    )
    with pytest.raises(RuntimeError, match="controls are disabled"):
        store.plan_resident_manager_binding(session_id="session", host="claude")

    assert store.mark_resident_manager_restore_required(session_id="session", host="codex") is False
    assert store.retire_resident_manager_binding(session_id="session", host="codex") is False


@pytest.mark.parametrize("stored_generation", [object(), -1])
def test_restore_required_rejects_invalid_stored_generation(
    stored_generation: object,
) -> None:
    owner = subject.ResidentManagerBindingStoreMixin()
    connection = _Connection({"restore_generation": stored_generation})
    owner._connect = lambda: connection  # type: ignore[attr-defined]
    with pytest.raises(RuntimeError, match="restore generation"):
        owner.mark_resident_manager_restore_required(session_id="session", host="claude")
    assert connection.rolled_back is True
    assert connection.closed is True


def test_restore_required_missing_binding_and_retire_rollback(tmp_path: Path) -> None:
    store = Store(tmp_path / "missing.db")
    assert (
        store.mark_resident_manager_restore_required(session_id="session", host="claude") is False
    )

    owner = subject.ResidentManagerBindingStoreMixin()
    connection = _Connection(fail_on="DELETE FROM resident_manager_bindings")
    owner._connect = lambda: connection  # type: ignore[attr-defined]
    with pytest.raises(RuntimeError, match="synthetic resident"):
        owner.retire_resident_manager_binding(session_id="session", host="claude")
    assert connection.rolled_back is True
    assert connection.closed is True


def test_private_commit_helpers_reject_wrong_delivery_modes() -> None:
    owner = subject.ResidentManagerBindingStoreMixin()
    connection = _Connection()
    assert (
        owner._commit_new_binding(
            connection,
            session_id="session",
            trace_id="turn",
            binding=_binding("reused"),
        )
        is False
    )
    assert (
        owner._replace_stale_binding(
            connection,
            session_id="session",
            trace_id="turn",
            binding=_binding("restored"),
        )
        is False
    )
    state = subject._BindingState(
        restore_generation=0,
        applied_restore_generation=0,
        pending_restore_generation=0,
        delivery_state="acknowledged",
        pending_delivery_mode="",
        pending_trace_id="",
        last_trace_id="prior",
    )
    assert (
        owner._commit_current_binding(
            connection,
            session_id="session",
            trace_id="turn",
            binding=_binding("injected"),
            state=state,
        )
        is False
    )


def test_commit_binding_rejects_disabled_or_nonreusable_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = subject.ResidentManagerBindingStoreMixin()
    connection = _Connection()
    reusable = _binding()
    monkeypatch.setattr(
        subject,
        "_current_control_state",
        lambda *_args, **_kwargs: subject._ControlState(
            enabled=False, epoch=reusable.control_epoch
        ),
    )
    assert (
        owner._commit_resident_manager_binding(
            connection,
            session_id="session",
            trace_id="turn",
            binding=reusable,
        )
        is False
    )

    nonreusable = _binding("reused", epoch=_epoch(reusable=False))
    monkeypatch.setattr(
        subject,
        "_current_control_state",
        lambda *_args, **_kwargs: subject._ControlState(
            enabled=True,
            epoch=nonreusable.control_epoch,
        ),
    )
    assert (
        owner._commit_resident_manager_binding(
            connection,
            session_id="session",
            trace_id="turn",
            binding=nonreusable,
        )
        is False
    )


def test_acknowledgement_rejects_host_row_and_pending_mismatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = subject.ResidentManagerBindingStoreMixin()
    codex_binding = _binding("request", host="codex")
    assert (
        owner.acknowledge_resident_manager_binding(
            session_id="session",
            host="claude",
            trace_id="turn",
            binding=codex_binding,
        )
        is False
    )

    binding = _binding()
    monkeypatch.setattr(
        subject,
        "_current_control_state",
        lambda *_args, **_kwargs: subject._ControlState(
            enabled=True,
            epoch=binding.control_epoch,
        ),
    )
    connection = _Connection()
    owner._connect = lambda: connection  # type: ignore[attr-defined]
    monkeypatch.setattr(subject, "_binding_row", lambda *_args, **_kwargs: None)
    assert (
        owner.acknowledge_resident_manager_binding(
            session_id="session",
            host="claude",
            trace_id="turn",
            binding=binding,
        )
        is False
    )
    assert connection.committed is True

    pending_elsewhere = _current_row(
        binding,
        delivery_state="pending",
        pending_delivery_mode="injected",
        pending_trace_id="other-turn",
    )
    monkeypatch.setattr(
        subject,
        "_binding_row",
        lambda *_args, **_kwargs: pending_elsewhere,
    )
    connection.committed = False
    assert (
        owner.acknowledge_resident_manager_binding(
            session_id="session",
            host="claude",
            trace_id="turn",
            binding=binding,
        )
        is False
    )
    assert connection.committed is True


@pytest.mark.parametrize(
    ("binding", "expected"),
    [
        (_binding("request", host="codex"), True),
        (_binding("injected", epoch=_epoch(reusable=False)), True),
    ],
)
def test_acknowledgement_accepts_ephemeral_delivery_contracts(
    binding: ResidentManagerBinding,
    expected: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = subject.ResidentManagerBindingStoreMixin()
    connection = _Connection()
    owner._connect = lambda: connection  # type: ignore[attr-defined]
    monkeypatch.setattr(
        subject,
        "_current_control_state",
        lambda *_args, **_kwargs: subject._ControlState(
            enabled=True,
            epoch=binding.control_epoch,
        ),
    )
    assert (
        owner.acknowledge_resident_manager_binding(
            session_id="session",
            host=binding.host,
            trace_id="turn",
            binding=binding,
        )
        is expected
    )
    assert connection.committed is True
    assert connection.closed is True


def test_acknowledgement_rolls_back_unexpected_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = subject.ResidentManagerBindingStoreMixin()
    connection = _Connection()
    owner._connect = lambda: connection  # type: ignore[attr-defined]
    monkeypatch.setattr(
        subject,
        "_current_control_state",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("control failed")),
    )
    with pytest.raises(RuntimeError, match="control failed"):
        owner.acknowledge_resident_manager_binding(
            session_id="session",
            host="claude",
            trace_id="turn",
            binding=_binding(),
        )
    assert connection.rolled_back is True
    assert connection.closed is True


def test_committed_validation_rejects_nonreusable_and_missing_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = subject.ResidentManagerBindingStoreMixin()
    connection = _Connection()
    owner._connect = lambda: connection  # type: ignore[attr-defined]
    nonreusable = _binding("reused", epoch=_epoch(reusable=False))
    monkeypatch.setattr(
        subject,
        "_current_control_state",
        lambda *_args, **_kwargs: subject._ControlState(
            enabled=True,
            epoch=nonreusable.control_epoch,
        ),
    )
    assert (
        owner.validate_committed_resident_manager_binding(
            session_id="session",
            trace_id="turn",
            binding=nonreusable,
        )
        is False
    )

    reusable = _binding()
    monkeypatch.setattr(
        subject,
        "_current_control_state",
        lambda *_args, **_kwargs: subject._ControlState(
            enabled=True,
            epoch=reusable.control_epoch,
        ),
    )
    monkeypatch.setattr(subject, "_binding_row", lambda *_args, **_kwargs: None)
    assert (
        owner.validate_committed_resident_manager_binding(
            session_id="session",
            trace_id="turn",
            binding=reusable,
        )
        is False
    )
