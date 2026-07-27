from __future__ import annotations

import json
import logging
from uuid import uuid4

import pytest

from agency_runtime.core.observability import (
    ObservationEnvelope,
    RuntimeBoundary,
    correlate_current_observation,
    correlation_observation_digest,
    current_observation_context,
    emit_store_observation,
    mark_current_observation,
    new_request_id,
    normalize_request_id,
)


def _observations(caplog: pytest.LogCaptureFixture) -> list[dict[str, object]]:
    return [
        json.loads(record.getMessage().split(" ", 1)[1])
        for record in caplog.records
        if record.name == "agency_runtime.observation"
        and record.getMessage().startswith("agency_observation ")
    ]


def test_observation_envelope_is_strict_content_free_and_single_line() -> None:
    request_id = new_request_id()
    digest = correlation_observation_digest(str(uuid4()))
    envelope = ObservationEnvelope(
        request_id=request_id,
        correlation_digest=digest,
        surface="http",
        operation="preflight",
        outcome="denied",
        reason_code="invalid_request",
        duration_ms=12.34567,
        store_generation=9,
    )

    payload = envelope.as_dict()
    assert payload == {
        "schema_version": 1,
        "request_id": request_id,
        "correlation_digest": digest,
        "surface": "http",
        "operation": "preflight",
        "outcome": "denied",
        "reason_code": "invalid_request",
        "duration_ms": 12.346,
        "store_generation": 9,
    }
    assert "\n" not in envelope.to_json()

    for field, value in (
        ("operation", "prompt=do-not-log"),
        ("reason_code", "Bearer secret"),
        ("surface", "C:\\Users\\private"),
    ):
        values = {
            "request_id": request_id,
            "correlation_digest": digest,
            "surface": "http",
            "operation": "preflight",
            "outcome": "ok",
            "reason_code": "completed",
            "duration_ms": 1,
        }
        values[field] = value
        with pytest.raises(ValueError):
            ObservationEnvelope(**values)  # type: ignore[arg-type]


def test_request_ids_accept_only_random_agency_or_canonical_uuid4() -> None:
    agency_id = new_request_id()
    browser_id = str(uuid4())
    assert normalize_request_id(agency_id) == agency_id
    assert normalize_request_id(browser_id.upper()) == browser_id

    for invalid in ("request-1", "../private", "00000000-0000-1000-8000-000000000000"):
        with pytest.raises(ValueError, match="request_id"):
            normalize_request_id(invalid)


def test_nested_boundaries_and_store_events_share_request_correlation(caplog) -> None:
    caplog.set_level(logging.INFO, logger="agency_runtime.observation")
    trace_id = str(uuid4())
    digest = correlation_observation_digest(trace_id)

    with RuntimeBoundary(
        surface="mcp",
        operation="agency.preflight",
        correlation_digest=digest,
    ) as outer:
        assert current_observation_context() == (outer.request_id, digest)
        emitted = emit_store_observation(
            operation="sqlite.select",
            duration_ms=51,
            outcome="degraded",
            reason_code="slow_query",
        )
        assert emitted.request_id == outer.request_id
        assert emitted.correlation_digest == digest
        mark_current_observation("denied", "policy_denied", store_generation=4)

    payloads = [
        payload
        for payload in _observations(caplog)
        if payload.get("request_id") == outer.request_id
        and payload.get("surface") in {"store", "mcp"}
    ]
    assert [payload["surface"] for payload in payloads] == ["store", "mcp"]
    assert {payload["request_id"] for payload in payloads} == {outer.request_id}
    assert payloads[-1]["outcome"] == "denied"
    assert payloads[-1]["store_generation"] == 4
    assert current_observation_context() == ("", "")


def test_boundary_can_attach_correlation_after_entry_and_preserve_explicit_outcome(
    caplog,
) -> None:
    caplog.set_level(logging.INFO, logger="agency_runtime.observation")
    trace_id = str(uuid4())
    with RuntimeBoundary(surface="http", operation="preflight") as boundary:
        digest = correlate_current_observation(trace_id)
        mark_current_observation("bypassed", "runtime_disabled")
        mark_current_observation("ok", "completed", only_if_unset=True)

    payload = next(
        item
        for item in _observations(caplog)
        if item.get("request_id") == boundary.request_id
        and item.get("surface") == "http"
        and item.get("operation") == "preflight"
    )
    assert payload["correlation_digest"] == digest
    assert payload["outcome"] == "bypassed"
    assert payload["reason_code"] == "runtime_disabled"


def test_boundary_exception_emits_type_free_error_without_message(caplog) -> None:
    caplog.set_level(logging.INFO, logger="agency_runtime.observation")
    secret = "Bearer never-log-this"

    with (
        pytest.raises(RuntimeError, match="never-log"),
        RuntimeBoundary(surface="hook", operation="subagent_start") as boundary,
    ):
        raise RuntimeError(secret)

    serialized = "\n".join(record.getMessage() for record in caplog.records)
    assert secret not in serialized
    assert "RuntimeError" not in serialized
    payload = next(
        item
        for item in _observations(caplog)
        if item.get("request_id") == boundary.request_id
        and item.get("surface") == "hook"
        and item.get("operation") == "subagent_start"
    )
    assert payload["reason_code"] == "internal_error"
