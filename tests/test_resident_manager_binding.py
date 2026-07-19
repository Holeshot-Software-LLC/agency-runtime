"""Exact resident-manager host-binding contract tests."""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from agency_runtime.core import resident_manager_binding as subject
from agency_runtime.core.resident_manager_binding import (
    CANONICAL_RESIDENT_MANAGER_HOSTS,
    MAX_RESIDENT_MANAGER_BINDING_BYTES,
    MAX_RESIDENT_MANAGER_CONTROL_GENERATION,
    MAX_RESIDENT_MANAGER_HOST_BYTES,
    MAX_RESIDENT_MANAGER_TURN_REFERENCE_CHARS,
    PERSISTENT_RESIDENT_MANAGER_HOSTS,
    REQUEST_SCOPED_RESIDENT_MANAGER_HOSTS,
    RESIDENT_MANAGER_BINDING_ID_HEX_CHARS,
    RESIDENT_MANAGER_BINDING_ID_PREFIX,
    RESIDENT_MANAGER_BINDING_VERSION,
    RESIDENT_MANAGER_DELIVERY_MODES,
    RESIDENT_MANAGER_HOST_MODES,
    ResidentControlEpoch,
    ResidentManagerBinding,
    build_resident_control_epoch,
    build_resident_manager_binding,
    canonical_resident_manager_host,
    deserialize_resident_manager_binding,
    resident_manager_binding_id,
    resident_manager_host_mode,
    resident_manager_turn_reference_context,
    serialize_resident_manager_binding,
    validate_resident_control_epoch,
    validate_resident_manager_binding,
)
from agency_runtime.core.resident_managers import (
    RESIDENT_MANAGER_KERNEL,
    RESIDENT_MANAGER_KERNEL_HASH,
    RESIDENT_MANAGER_KERNEL_REFERENCE,
)

SESSION_ID = "session-secret-0123456789"
TRACE_ID = "trace-secret-0123456789"


def _binding(
    host: str = "claude",
    delivery_mode: str = "injected",
) -> ResidentManagerBinding:
    return build_resident_manager_binding(
        session_id=SESSION_ID,
        host=host,
        delivery_mode=delivery_mode,
    )


def _raw_binding() -> dict[str, Any]:
    return _binding().as_dict()


def test_host_contract_is_complete_canonical_and_bounded() -> None:
    assert PERSISTENT_RESIDENT_MANAGER_HOSTS == ("claude",)
    assert REQUEST_SCOPED_RESIDENT_MANAGER_HOSTS == (
        "codex",
        "openclaw",
        "hermes",
        "litellm",
        "unknown",
    )
    assert (
        *PERSISTENT_RESIDENT_MANAGER_HOSTS,
        *REQUEST_SCOPED_RESIDENT_MANAGER_HOSTS,
    ) == CANONICAL_RESIDENT_MANAGER_HOSTS
    assert RESIDENT_MANAGER_HOST_MODES == ("persistent", "request_scoped")
    assert RESIDENT_MANAGER_DELIVERY_MODES == (
        "injected",
        "reused",
        "restored",
        "request",
    )
    assert RESIDENT_MANAGER_BINDING_VERSION == 2
    assert MAX_RESIDENT_MANAGER_HOST_BYTES == 64
    assert MAX_RESIDENT_MANAGER_BINDING_BYTES == 1_024
    assert MAX_RESIDENT_MANAGER_TURN_REFERENCE_CHARS == 384
    assert MAX_RESIDENT_MANAGER_CONTROL_GENERATION == 2**63 - 1


@pytest.mark.parametrize(
    ("value", "expected_host", "expected_mode"),
    [
        (" CODEX ", "codex", "request_scoped"),
        ("claude", "claude", "persistent"),
        ("OpenClaw", "openclaw", "request_scoped"),
        ("hermes", "hermes", "request_scoped"),
        ("litellm", "litellm", "request_scoped"),
        ("unknown", "unknown", "request_scoped"),
        ("other-host", "unknown", "request_scoped"),
        ("", "unknown", "request_scoped"),
        ("   ", "unknown", "request_scoped"),
        (None, "unknown", "request_scoped"),
        ("é" * 32, "unknown", "request_scoped"),
    ],
)
def test_host_normalization_and_scope(
    value: object,
    expected_host: str,
    expected_mode: str,
) -> None:
    assert canonical_resident_manager_host(value) == expected_host
    assert resident_manager_host_mode(value) == expected_mode


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (7, "must be a string"),
        ("codex\n", "printable"),
        ("\ud800", "UTF-8"),
        ("é" * 33, "64-byte"),
    ],
)
def test_host_normalization_rejects_ambiguous_or_unbounded_values(
    value: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        canonical_resident_manager_host(value)


def test_binding_id_is_stable_opaque_and_bound_to_every_required_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding_id = resident_manager_binding_id(session_id=SESSION_ID, host="codex")

    assert binding_id == resident_manager_binding_id(
        session_id=f"  {SESSION_ID}  ",
        host=" CODEX ",
    )
    assert binding_id != resident_manager_binding_id(
        session_id=f"{SESSION_ID}-other",
        host="codex",
    )
    assert binding_id != resident_manager_binding_id(
        session_id=SESSION_ID,
        host="claude",
    )
    assert binding_id != resident_manager_binding_id(
        session_id=SESSION_ID,
        host="codex",
        control_epoch=build_resident_control_epoch(master_generation=1),
    )
    assert binding_id != resident_manager_binding_id(
        session_id=SESSION_ID,
        host="codex",
        control_epoch=build_resident_control_epoch(host_generation=1),
    )
    assert binding_id != resident_manager_binding_id(
        session_id=SESSION_ID,
        host="codex",
        control_epoch=build_resident_control_epoch(
            master_generation=0,
            master_materialized=False,
        ),
    )
    assert binding_id != resident_manager_binding_id(
        session_id=SESSION_ID,
        host="codex",
        control_epoch=build_resident_control_epoch(
            host_generation=0,
            host_materialized=False,
        ),
    )
    assert binding_id.startswith(RESIDENT_MANAGER_BINDING_ID_PREFIX)
    assert len(binding_id) == len(RESIDENT_MANAGER_BINDING_ID_PREFIX) + (
        RESIDENT_MANAGER_BINDING_ID_HEX_CHARS
    )
    assert SESSION_ID not in binding_id
    assert RESIDENT_MANAGER_KERNEL_HASH not in binding_id

    monkeypatch.setattr(subject, "RESIDENT_MANAGER_KERNEL_HASH", "f" * 64)
    assert binding_id != resident_manager_binding_id(
        session_id=SESSION_ID,
        host="codex",
    )


@pytest.mark.parametrize("delivery_mode", ["injected", "reused", "restored"])
@pytest.mark.parametrize("host", PERSISTENT_RESIDENT_MANAGER_HOSTS)
def test_persistent_hosts_accept_only_persistent_delivery_modes(
    host: str,
    delivery_mode: str,
) -> None:
    binding = _binding(host, delivery_mode)

    assert binding.host == host
    assert binding.host_mode == "persistent"
    assert binding.delivery_mode == delivery_mode
    assert binding.requires_kernel_injection is (delivery_mode != "reused")


@pytest.mark.parametrize("host", [*REQUEST_SCOPED_RESIDENT_MANAGER_HOSTS, "future-host"])
def test_request_scoped_hosts_accept_only_request_delivery(host: str) -> None:
    binding = _binding(host, "request")

    assert binding.host == (host if host != "future-host" else "unknown")
    assert binding.host_mode == "request_scoped"
    assert binding.delivery_mode == "request"
    assert binding.requires_kernel_injection is True


@pytest.mark.parametrize(
    ("host", "delivery_mode"),
    [
        ("claude", "request"),
        ("codex", "injected"),
        ("litellm", "injected"),
        ("unknown", "reused"),
        ("claude", "INJECTED"),
        ("claude", None),
    ],
)
def test_builder_rejects_cross_scope_or_noncanonical_delivery_modes(
    host: str,
    delivery_mode: object,
) -> None:
    with pytest.raises(ValueError, match="delivery_mode"):
        build_resident_manager_binding(
            session_id=SESSION_ID,
            host=host,
            delivery_mode=delivery_mode,
        )


def test_binding_projection_is_exact_bounded_and_content_free() -> None:
    binding = _binding("claude", "restored")
    projection = binding.as_dict()
    serialized = serialize_resident_manager_binding(binding, session_id=SESSION_ID)

    assert list(projection) == [
        "version",
        "binding_id",
        "host",
        "host_mode",
        "delivery_mode",
        "control_epoch",
        "kernel",
    ]
    assert projection["control_epoch"] == {
        "master_generation": 0,
        "master_materialized": True,
        "host_generation": 0,
        "host_materialized": True,
    }
    assert projection["kernel"] == RESIDENT_MANAGER_KERNEL_REFERENCE.as_dict()
    assert len(serialized.encode("utf-8")) <= MAX_RESIDENT_MANAGER_BINDING_BYTES
    assert SESSION_ID not in serialized
    assert TRACE_ID not in serialized
    assert RESIDENT_MANAGER_KERNEL not in serialized
    assert "Chief of Staff owns" not in serialized
    assert json.loads(serialized) == projection
    assert (
        serialize_resident_manager_binding(
            projection,
            session_id=SESSION_ID,
        )
        == serialized
    )


def test_control_epoch_is_strict_and_marks_only_materialized_state_reusable() -> None:
    durable = build_resident_control_epoch(master_generation=3, host_generation=7)
    absent_master = build_resident_control_epoch(
        master_generation=0,
        master_materialized=False,
    )
    unreadable_master = build_resident_control_epoch(
        master_generation=None,
        master_materialized=False,
    )
    absent_host = build_resident_control_epoch(
        host_generation=0,
        host_materialized=False,
    )

    assert durable.reusable is True
    assert absent_master.reusable is False
    assert unreadable_master.reusable is False
    assert absent_host.reusable is False
    assert validate_resident_control_epoch(durable.as_dict()) == durable
    assert isinstance(durable, ResidentControlEpoch)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (None, "must be an object"),
        ({}, "invalid fields"),
        (
            {
                "master_generation": None,
                "master_materialized": True,
                "host_generation": 0,
                "host_materialized": True,
            },
            "requires a generation",
        ),
        (
            {
                "master_generation": 1,
                "master_materialized": False,
                "host_generation": 0,
                "host_materialized": True,
            },
            "must be zero or null",
        ),
        (
            {
                "master_generation": 0,
                "master_materialized": False,
                "host_generation": 1,
                "host_materialized": False,
            },
            "must be zero",
        ),
    ],
)
def test_control_epoch_rejects_nonexact_or_ambiguous_state(
    value: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_resident_control_epoch(value)


def test_binding_round_trip_accepts_only_canonical_json() -> None:
    binding = _binding("claude", "reused")
    serialized = serialize_resident_manager_binding(binding, session_id=SESSION_ID)

    assert (
        deserialize_resident_manager_binding(
            serialized,
            session_id=SESSION_ID,
        )
        == binding
    )
    with pytest.raises(ValueError, match="not canonical"):
        deserialize_resident_manager_binding(
            f" {serialized}",
            session_id=SESSION_ID,
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (None, "must be a string"),
        ("\ud800", "valid UTF-8"),
        ("x" * (MAX_RESIDENT_MANAGER_BINDING_BYTES + 1), "byte limit"),
        ("{", "JSON is invalid"),
        ("[]", "must be an object"),
        ("NaN", "non-finite"),
    ],
)
def test_binding_deserialization_rejects_invalid_envelopes(
    payload: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        deserialize_resident_manager_binding(payload, session_id=SESSION_ID)


def test_binding_deserialization_rejects_duplicate_fields() -> None:
    serialized = serialize_resident_manager_binding(_binding(), session_id=SESSION_ID)
    duplicate = serialized.replace(
        '"binding_id":',
        '"binding_id":"duplicate","binding_id":',
        1,
    )

    with pytest.raises(ValueError, match="duplicate fields"):
        deserialize_resident_manager_binding(duplicate, session_id=SESSION_ID)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.pop("host"), "invalid fields"),
        (lambda value: value.update(extra=True), "invalid fields"),
        (lambda value: value.update(version=True), "version"),
        (lambda value: value.update(version=1), "version"),
        (lambda value: value.update(host="CODEX"), "not canonical"),
        (lambda value: value.update(host=7), "not canonical"),
        (lambda value: value.update(host_mode=None), "host_mode"),
        (lambda value: value.update(host_mode="request_scoped"), "host_mode"),
        (lambda value: value.update(delivery_mode="REQUEST"), "delivery_mode"),
        (lambda value: value.update(delivery_mode="request"), "invalid for"),
        (
            lambda value: value["control_epoch"].update(master_generation=True),
            "generation",
        ),
        (
            lambda value: value["control_epoch"].update(master_generation=-1),
            "generation",
        ),
        (
            lambda value: value["control_epoch"].update(host_generation=True),
            "generation",
        ),
        (
            lambda value: value["control_epoch"].update(host_generation=-1),
            "generation",
        ),
        (
            lambda value: value["control_epoch"].update(master_materialized=1),
            "boolean",
        ),
        (
            lambda value: value["control_epoch"].update(host_materialized=1),
            "boolean",
        ),
        (lambda value: value.update(kernel=None), "invalid fields"),
        (
            lambda value: value["kernel"].update(extra=True),
            "invalid fields",
        ),
        (
            lambda value: value["kernel"].update(version=True),
            "not current",
        ),
        (
            lambda value: value["kernel"].update(content_hash="0" * 64),
            "not current",
        ),
        (
            lambda value: value["kernel"].update(slugs=tuple(value["kernel"]["slugs"])),
            "not current",
        ),
        (lambda value: value.update(binding_id=None), "malformed"),
        (lambda value: value.update(binding_id="rmb-" + ("a" * 31)), "malformed"),
        (lambda value: value.update(binding_id="xmb-" + ("a" * 32)), "malformed"),
        (lambda value: value.update(binding_id="rmb-" + ("g" * 32)), "malformed"),
    ],
)
def test_binding_validation_rejects_every_nonexact_field(
    mutate: Any,
    message: str,
) -> None:
    raw = copy.deepcopy(_raw_binding())
    mutate(raw)

    with pytest.raises(ValueError, match=message):
        validate_resident_manager_binding(raw, session_id=SESSION_ID)


def test_binding_validation_rejects_wrong_session_and_nonobjects() -> None:
    binding = _binding()

    assert validate_resident_manager_binding(binding, session_id=SESSION_ID) == binding
    with pytest.raises(ValueError, match="does not match its session"):
        validate_resident_manager_binding(binding, session_id="another-session")
    with pytest.raises(ValueError, match="must be an object"):
        validate_resident_manager_binding([], session_id=SESSION_ID)


def test_serialization_budget_is_enforced_after_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "MAX_RESIDENT_MANAGER_BINDING_BYTES", 1)

    with pytest.raises(RuntimeError, match="serialization budget"):
        serialize_resident_manager_binding(_binding(), session_id=SESSION_ID)


def test_current_turn_reference_is_bounded_correlated_and_prompt_free() -> None:
    binding = _binding("claude", "reused")
    context = resident_manager_turn_reference_context(
        binding,
        session_id=SESSION_ID,
        trace_id=TRACE_ID,
    )

    assert context == resident_manager_turn_reference_context(
        binding.as_dict(),
        session_id=SESSION_ID,
        trace_id=TRACE_ID,
    )
    assert context != resident_manager_turn_reference_context(
        binding,
        session_id=SESSION_ID,
        trace_id=f"{TRACE_ID}-other",
    )
    assert len(context) <= MAX_RESIDENT_MANAGER_TURN_REFERENCE_CHARS
    assert binding.binding_id in context
    assert "turn=rmt-" in context
    assert "host=claude" in context
    assert "host_mode=persistent" in context
    assert "delivery=reused" in context
    assert SESSION_ID not in context
    assert TRACE_ID not in context
    assert RESIDENT_MANAGER_KERNEL not in context
    assert "Chief of Staff owns" not in context


def test_current_turn_reference_budget_is_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "MAX_RESIDENT_MANAGER_TURN_REFERENCE_CHARS", 1)

    with pytest.raises(RuntimeError, match="context budget"):
        resident_manager_turn_reference_context(
            _binding(),
            session_id=SESSION_ID,
            trace_id=TRACE_ID,
        )
