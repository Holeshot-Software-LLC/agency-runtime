"""Process-sealed adapter-origin authority contracts."""

from __future__ import annotations

from dataclasses import replace

import pytest

from agency_runtime.core import preflight as preflight_module
from agency_runtime.core import turn_origin
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.turn_origin import (
    TURN_ORIGIN_HOSTS,
    current_turn_origin,
    native_adapter_turn_origin,
)


@pytest.mark.parametrize("host", sorted(TURN_ORIGIN_HOSTS))
def test_external_user_origin_is_bound_to_every_owned_adapter_surface(host: str) -> None:
    receipt = native_adapter_turn_origin(
        "external_user",
        host=host,
        event="adapter_preflight",
        session_id="session",
        trace_id="turn",
    )

    assert (
        current_turn_origin(
            receipt,
            host=host,
            session_id="session",
            trace_id="turn",
        )
        is receipt
    )


@pytest.mark.parametrize(
    ("origin", "event"),
    (
        ("external_user", "user_prompt_submit"),
        ("internal_retry", "user_prompt_submit_retry"),
        ("stop_revalidation", "stop"),
        ("automatic_continuation", "post_compact"),
        ("native_child", "subagent_start"),
    ),
)
def test_each_adapter_origin_accepts_only_its_declared_lifecycle_event(
    origin: str,
    event: str,
) -> None:
    receipt = native_adapter_turn_origin(
        origin,  # type: ignore[arg-type]
        host="codex",
        event=event,
        session_id="session",
        trace_id="turn",
    )

    assert receipt.origin == origin
    with pytest.raises(ValueError, match="event is invalid"):
        native_adapter_turn_origin(
            origin,  # type: ignore[arg-type]
            host="codex",
            event="invented",
            session_id="session",
            trace_id="turn",
        )


def test_origin_receipt_rejects_tampering_serialization_and_cross_correlation() -> None:
    receipt = native_adapter_turn_origin(
        "external_user",
        host="codex",
        event="user_prompt_submit",
        session_id="session",
        trace_id="turn",
    )

    assert (
        current_turn_origin(
            receipt.as_dict(),
            host="codex",
            session_id="session",
            trace_id="turn",
        )
        is None
    )
    for values in (
        {"host": "claude"},
        {"session_id": "other-session"},
        {"trace_id": "other-turn"},
        {"event": "wrapper"},
        {"origin": "internal_retry"},
        {"_attestation": "0" * 64},
    ):
        forged = replace(receipt, **values)
        assert (
            current_turn_origin(
                forged,
                host=forged.host,
                session_id=forged.session_id,
                trace_id=forged.trace_id,
            )
            is None
        )

    assert (
        current_turn_origin(
            receipt,
            host="claude",
            session_id="session",
            trace_id="turn",
        )
        is None
    )
    assert (
        current_turn_origin(
            receipt,
            host="codex",
            session_id="other-session",
            trace_id="turn",
        )
        is None
    )
    assert (
        current_turn_origin(
            receipt,
            host="codex",
            session_id="session",
            trace_id="other-turn",
        )
        is None
    )


def test_origin_receipt_expires_and_rejects_unknown_surfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 10_000_000_000
    monkeypatch.setattr(turn_origin.time, "monotonic_ns", lambda: now)
    receipt = native_adapter_turn_origin(
        "external_user",
        host="codex",
        event="wrapper",
        session_id="session",
        trace_id="turn",
    )
    monkeypatch.setattr(
        turn_origin.time,
        "monotonic_ns",
        lambda: now + turn_origin.TURN_ORIGIN_TTL_SECONDS * 1_000_000_000 + 1,
    )

    assert (
        current_turn_origin(
            receipt,
            host="codex",
            session_id="session",
            trace_id="turn",
        )
        is None
    )
    with pytest.raises(ValueError, match="supported adapter surface"):
        native_adapter_turn_origin(
            "external_user",
            host="invented",
            event="wrapper",
            session_id="session",
            trace_id="turn",
        )
    with pytest.raises(ValueError, match="turn origin is invalid"):
        native_adapter_turn_origin(
            "invented",  # type: ignore[arg-type]
            host="codex",
            event="wrapper",
            session_id="session",
            trace_id="turn",
        )


@pytest.mark.parametrize(
    ("origin", "event"),
    (
        ("internal_retry", "user_prompt_submit_retry"),
        ("stop_revalidation", "stop"),
        ("automatic_continuation", "post_compact"),
        ("native_child", "subagent_start"),
    ),
)
def test_internal_lifecycle_origin_cannot_start_fresh_preflight(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    origin: str,
    event: str,
) -> None:
    receipt = native_adapter_turn_origin(
        origin,  # type: ignore[arg-type]
        host="codex",
        event=event,
        session_id="session",
        trace_id="turn",
    )
    monkeypatch.setattr(
        preflight_module,
        "classify_turn_intent",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("internal lifecycle event reached classification")
        ),
    )

    with pytest.raises(ValueError, match="cannot start Agency preflight"):
        run_preflight(
            Store(tmp_path / "agency.db"),
            session_id="session",
            user_message="continue",
            host="codex",
            trace_id="turn",
            origin_receipt=receipt,
        )
