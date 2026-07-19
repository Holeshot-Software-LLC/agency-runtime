"""Adversarial tests for the model-receipt persistence trust boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from agency_runtime.adapters.litellm.callback import AgencyLiteLLMCallback
from agency_runtime.adapters.litellm.evidence import provider_model
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.receipts.ingress import (
    MAX_RECEIPT_FALLBACKS,
    MAX_RECEIPT_MODEL_CHARS,
    MAX_RECEIPT_MODEL_ID_CHARS,
    canonicalize_provider,
)
from agency_runtime.core.receipts.normalize import normalize_host_receipt
from agency_runtime.core.store.sqlite import Store

NOW = datetime(2026, 7, 14, tzinfo=timezone.utc)


class _BrokenString:
    def __str__(self) -> str:
        raise RuntimeError("unsafe coercion")


def test_store_bounds_and_normalizes_every_receipt_field(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_model_receipt(
        trace_id="trace",
        session_id="session",
        host="H" * 65,
        requested_model="r" * 300,
        model_group="g" * 300,
        resolved_provider=" OpenAI ",
        resolved_model="m" * 300,
        api_base="https://alice:secret@EXAMPLE.test/v1?api_key=secret#fragment",
        attempted_fallbacks=1 << 100_000,
        model_id="i" * 800,
        source="wrapper",
        started_at="not-a-time",
        ended_at="2026-07-14T12:00:00Z",
        status="SUCCESS",
    )

    receipt = store.get_model_receipt("trace")
    assert receipt is not None
    assert receipt["session_id"] == "session"
    assert receipt["host"] == "unknown"
    assert receipt["requested_model"] == "r" * MAX_RECEIPT_MODEL_CHARS
    assert receipt["model_group"] == "g" * MAX_RECEIPT_MODEL_CHARS
    assert receipt["resolved_provider"] == "openai"
    assert receipt["resolved_model"] == "unavailable"
    assert receipt["api_base"] == "https://example.test/v1"
    assert receipt["attempted_fallbacks"] == MAX_RECEIPT_FALLBACKS
    assert receipt["model_id"] == "i" * MAX_RECEIPT_MODEL_ID_CHARS
    assert receipt["source"] == "wrapper"
    assert receipt["started_at"]
    assert receipt["ended_at"] == "2026-07-14T12:00:00+00:00"
    assert receipt["status"] == "success"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" OpenAI ", "openai"),
        ("AZURE_AI", "azure_ai"),
        ("openai\nanthropic", ""),
        ("open ai", ""),
        ("custom", ""),
        ("custom/openai", ""),
        ("openai/custom", ""),
        ("openai/azure", ""),
        ("x" * 129, ""),
        (None, ""),
    ],
)
def test_provider_metadata_is_canonical_or_rejected(value: object, expected: str) -> None:
    assert canonicalize_provider(value) == expected


def test_uncoercible_provider_metadata_fails_closed() -> None:
    assert canonicalize_provider(_BrokenString()) == ""


def test_provider_normalization_is_shared_by_host_and_litellm_helpers() -> None:
    host = normalize_host_receipt(
        {
            "actual_model": "gpt-5.6",
            "provider": "OpenAI\x1b[31m",
        }
    )
    assert host["resolved_provider"] == ""
    assert provider_model("OpenAI/gpt-5.6") == ("openai", "gpt-5.6")
    assert provider_model("OpenAI\nAnthropic/gpt-5.6") == ("", "")


def test_control_fields_and_untrusted_status_fail_closed(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_model_receipt(
        trace_id="trace",
        host="codex\nspoofed",
        requested_model="requested\nspoofed",
        model_group="router\rspoofed",
        resolved_provider="openai\x1b[31m",
        resolved_model="gpt-5.6\nspoofed",
        api_base="https://example.test/v1\nspoofed",
        attempted_fallbacks=-10,
        model_id="deployment\tspoofed",
        source="litellm",
        status="success\nfailed",
    )

    receipt = store.get_model_receipt("trace")
    assert receipt is not None
    assert receipt["host"] == "unknown"
    assert receipt["requested_model"] == ""
    assert receipt["model_group"] == ""
    assert receipt["resolved_provider"] == ""
    assert receipt["resolved_model"] == "unavailable"
    assert receipt["api_base"] == ""
    assert receipt["attempted_fallbacks"] == 0
    assert receipt["model_id"] == ""
    assert receipt["source"] == "unknown"
    assert receipt["status"] == "unknown"


@pytest.mark.parametrize("api_base", ["ftp://example.test/v1", "http://[broken"])
def test_invalid_api_base_is_rejected(tmp_path: Path, api_base: str) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_model_receipt(trace_id="trace", api_base=api_base)
    receipt = store.get_model_receipt("trace")
    assert receipt is not None
    assert receipt["api_base"] == ""


def test_naive_receipt_timestamps_are_canonicalized_to_utc(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_model_receipt(
        trace_id="trace",
        started_at="2026-07-14T12:00:00",
        ended_at="2026-07-14T12:00:01",
    )
    receipt = store.get_model_receipt("trace")
    assert receipt is not None
    assert receipt["started_at"] == "2026-07-14T12:00:00+00:00"
    assert receipt["ended_at"] == "2026-07-14T12:00:01+00:00"


@pytest.mark.parametrize("attempted", [True, float("inf"), "9" * 10_000, -1])
def test_invalid_fallback_counts_collapse_to_zero(tmp_path: Path, attempted: object) -> None:
    store = Store(tmp_path / f"{type(attempted).__name__}.db")
    store.record_model_receipt(trace_id="trace", attempted_fallbacks=attempted)  # type: ignore[arg-type]
    receipt = store.get_model_receipt("trace")
    assert receipt is not None
    assert receipt["attempted_fallbacks"] == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("trace_id", "t" * 257),
        ("trace_id", "trace\nspoofed"),
        ("trace_id", "trace\n"),
        ("session_id", "s" * 257),
        ("session_id", "session\x00spoofed"),
    ],
)
def test_invalid_correlation_is_rejected_without_partial_write(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    store = Store(tmp_path / f"{field}-{len(value)}.db")
    kwargs = {"trace_id": "trace", "session_id": "session", field: value}
    with pytest.raises(ValueError, match=field):
        store.record_model_receipt(**kwargs)
    assert store.runtime_table_counts()["model_receipts"] == 0


def test_public_source_impersonation_cannot_outrank_litellm_callback(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    callback = AgencyLiteLLMCallback(store=store, config=AgencyConfig())
    callback.log_success_event(
        {
            "model": "production-router",
            "metadata": {
                "agency_trace_id": "trace",
                "agency_session_id": "session",
            },
            "standard_logging_object": {
                "model_group": "production-router",
                "hidden_params": {"litellm_model_name": "openai/gpt-5.6"},
            },
        },
        {"id": "response", "model": "openai/gpt-5.6"},
        NOW,
        NOW,
    )
    authentic = store.get_model_receipt("trace")
    assert authentic is not None
    assert authentic["source"] == "litellm"

    store.record_model_receipt(
        trace_id="trace",
        session_id="session",
        resolved_provider="anthropic",
        resolved_model="attacker-model",
        source="litellm",
        status="success",
    )

    authoritative = store.get_model_receipt("trace")
    assert authoritative is not None
    assert authoritative["source"] == "litellm"
    assert authoritative["resolved_provider"] == "openai"
    assert authoritative["resolved_model"] == "gpt-5.6"

    connection = store._connect()
    try:
        rows = connection.execute(
            "SELECT source, resolved_model FROM model_receipts WHERE trace_id = ? ORDER BY rowid",
            ("trace",),
        ).fetchall()
    finally:
        connection.close()
    assert [tuple(row) for row in rows] == [
        ("litellm", "gpt-5.6"),
        ("unknown", "attacker-model"),
    ]
