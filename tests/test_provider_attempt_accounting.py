"""AR-284: stage order is not provider fallback evidence (written, unrun)."""

from __future__ import annotations

from dataclasses import asdict
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.config import ProviderEntry
from agency_runtime.core.preflight_failure import PREFLIGHT_PROVIDER_STAGES
from agency_runtime.core.receipts.attempt_accounting import (
    PROVIDER_ATTEMPT_STAGES,
    ProviderChainAccounting,
    project_provider_attempt_metadata,
    provider_fallback_count,
)
from agency_runtime.core.receipts.ingress import ReceiptProvenance, normalize_receipt_ingress
from agency_runtime.core.selector.pipeline import _record_workforce_model_receipts
from agency_runtime.core.selector.receipt_projection import project_model_receipt_attempts
from agency_runtime.core.structured_provider import StructuredProviderResult
from agency_runtime.core.workforce import hiring, inference


def _provider(index: int) -> ProviderEntry:
    return ProviderEntry(name=f"provider-{index}", type="litellm", model="test-model", timeout=10)


def _result(
    *, ok: bool = True, failure_reason: str = "", call_attempted: bool = False
) -> StructuredProviderResult:
    return StructuredProviderResult(
        value={} if failure_reason else {"ok": ok},
        provider_name="provider-result",
        provider_type="litellm",
        transport="http",
        requested_model="test-model",
        model_group="test-model",
        actual_model="actual-model",
        model_receipt_source="response.body.model",
        latency_ms=1,
        failure_reason=failure_reason,
        call_attempted=call_attempted,
    )


def _stage(
    responses: list[StructuredProviderResult | None], *, providers: int = 2, stage: str = "planner"
) -> list[inference.WorkforceInferenceAttempt]:
    pending = iter(responses)

    def parse(value: dict[str, Any]) -> dict[str, Any]:
        if value.get("ok") is not True:
            raise ValueError("invalid test response")
        return value

    result, attempts, reason = inference._invoke_stage(
        stage=stage,
        providers=tuple(_provider(index) for index in range(providers)),
        prompt="bounded test request",
        schema={"type": "object"},
        system_prompt="test",
        budget=inference._CallBudget(8),
        invoker=lambda *_args, **_kwargs: next(pending),
        parser=parse,
    )
    assert result == {"ok": True}
    assert reason == ""
    return attempts


def test_provider_accounting_keeps_the_failure_receipt_closed_stage_vocabulary() -> None:
    assert PROVIDER_ATTEMPT_STAGES == PREFLIGHT_PROVIDER_STAGES


@pytest.mark.parametrize("stage", ["planner", "recruiter", "critic"])
def test_each_inference_stage_starts_with_zero_fallbacks(stage: str) -> None:
    attempts = _stage([_result()], providers=1, stage=stage)
    assert provider_fallback_count(attempts[0]) == 0
    assert attempts[0].provider_chain_index == 0


def test_semantic_repairs_do_not_become_provider_fallbacks() -> None:
    attempts = _stage([_result(ok=False), _result(ok=False), _result()])
    assert [attempt.provider_chain_index for attempt in attempts] == [0, 0, 1]
    assert [attempt.provider_call_attempted for attempt in attempts] == [True, True, True]
    assert [provider_fallback_count(attempt) for attempt in attempts] == [0, 0, 1]


@pytest.mark.parametrize(
    ("first", "expected"),
    [
        (_result(failure_reason="provider_credential_env_unset"), [None, 0]),
        (_result(failure_reason="provider_call_failed", call_attempted=True), [0, 1]),
        (None, [None, None]),
    ],
)
def test_dispatch_facts_distinguish_refusal_failure_and_unknown(
    first: StructuredProviderResult | None, expected: list[int | None]
) -> None:
    attempts = _stage([first, _result()])
    assert [attempt.provider_chain_index for attempt in attempts] == [0, 1]
    assert [provider_fallback_count(attempt) for attempt in attempts] == expected


def test_unknown_prior_entry_stays_unknown_until_that_entry_is_observed_invoked() -> None:
    accounting = ProviderChainAccounting()
    assert accounting.observe(0, call_attempted=None)["provider_fallback_count"] is None
    assert accounting.observe(1, call_attempted=True)["provider_fallback_count"] is None
    # A later refusal cannot prove an earlier unclassified dispatch did not run.
    accounting.observe(0, call_attempted=False)
    assert accounting.observe(1, call_attempted=True)["provider_fallback_count"] is None


def test_unknown_same_entry_is_resolved_only_by_a_known_dispatch() -> None:
    accounting = ProviderChainAccounting()
    accounting.observe(0, call_attempted=None)
    assert accounting.observe(0, call_attempted=True)["provider_fallback_count"] == 0
    assert accounting.observe(1, call_attempted=True)["provider_fallback_count"] == 1


def test_count_exceeding_sql_receipt_bound_is_unknown_not_clamped() -> None:
    metadata = {
        "stage": "planner",
        "metadata_version": 1,
        "provider_chain_index": 20_000,
        "provider_call_attempted": True,
        "provider_fallback_count": 20_000,
    }
    assert provider_fallback_count(metadata) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("metadata_version", True),
        ("metadata_version", 2),
        ("stage", "prompt text must not be retained"),
        ("stage", "made_up_stage"),
        ("provider_chain_index", True),
        ("provider_chain_index", -1),
        ("provider_chain_index", 1_000_001),
        ("provider_fallback_count", True),
        ("provider_fallback_count", "0"),
        ("provider_fallback_count", -1),
        ("provider_fallback_count", 1),
        ("provider_call_attempted", 1),
    ],
)
def test_invalid_accounting_is_unknown_not_coerced(field: str, value: object) -> None:
    metadata = {"stage": "planner", **ProviderChainAccounting().observe(0, call_attempted=True)}
    metadata[field] = value
    assert project_provider_attempt_metadata(metadata) == {}
    assert provider_fallback_count(metadata) is None


def test_projection_preserves_legacy_fixed_points_and_new_separate_ordinals() -> None:
    legacy = {
        "provider_name": "provider-0",
        "provider_type": "litellm",
        "requested_model": "test-model",
        "model_group": "test-model",
        "actual_model": "actual-model",
        "model_receipt_source": "response.body.model",
        "status": "applied",
        "reason_code": "structured_response_applied",
    }
    assert project_model_receipt_attempts([legacy]) == [legacy]
    assert provider_fallback_count(legacy) is None
    attempts = [
        asdict(_stage([_result()], providers=1, stage=stage)[0])
        for stage in ("planner", "recruiter", "critic")
    ]
    projected = project_model_receipt_attempts(attempts)
    assert projected is not None
    assert [item["ordinal"] for item in projected] == [1, 2, 3]
    assert [item["provider_fallback_count"] for item in projected] == [0, 0, 0]
    assert project_model_receipt_attempts(projected) == projected


@pytest.mark.parametrize(
    ("first", "expected"),
    [
        (_result(failure_reason="provider_credential_env_unset"), [None, 0]),
        (_result(failure_reason="provider_call_failed", call_attempted=True), [0, 1]),
        (None, [None, None]),
    ],
)
def test_hiring_uses_actual_chain_dispatch_not_receipt_order(
    first: StructuredProviderResult | None, expected: list[int | None]
) -> None:
    pending = iter((first, _result()))
    result, accepted, failures = hiring._invoke(
        (_provider(0), _provider(1)),
        prompt="bounded hiring test",
        schema={"type": "object"},
        system="test",
        stage="hiring-critic",
        invoker=lambda *_args, **_kwargs: next(pending),
        budget=hiring._CallBudget(4),
    )
    assert result is not None and accepted is not None
    attempts = (*failures, accepted)
    assert [attempt.provider_chain_index for attempt in attempts] == [0, 1]
    assert [provider_fallback_count(attempt) for attempt in attempts] == expected
    assert provider_fallback_count(accepted.as_receipt()) == expected[-1]


@pytest.mark.parametrize(
    ("source", "provenance", "values", "expected"),
    [
        ("wrapper", ReceiptProvenance.GENERIC, {"attempted_fallbacks": None}, None),
        ("wrapper", ReceiptProvenance.GENERIC, {}, 0),
        ("wrapper", ReceiptProvenance.GENERIC, {"attempted_fallbacks": 2}, 2),
        ("host", ReceiptProvenance.GENERIC, {"attempted_fallbacks": None}, 0),
        ("litellm", ReceiptProvenance.LITELLM_CALLBACK, {"attempted_fallbacks": None}, 0),
    ],
)
def test_only_explicit_generic_wrapper_unknown_is_nullable(
    source: str, provenance: ReceiptProvenance, values: dict[str, Any], expected: int | None
) -> None:
    normalized = normalize_receipt_ingress({"source": source, **values}, provenance=provenance)
    assert normalized["attempted_fallbacks"] == expected


def test_direct_workforce_writer_never_uses_flattened_attempt_order() -> None:
    rows: list[dict[str, Any]] = []
    attempts = [
        _stage([_result()], providers=1, stage=stage)[0]
        for stage in ("planner", "recruiter", "critic")
    ]
    _record_workforce_model_receipts(
        SimpleNamespace(record_model_receipt=lambda **values: rows.append(values)),
        SimpleNamespace(attempts=attempts),
        session_id="session",
        trace_id="trace",
        host="hermes",
    )
    assert [row["attempted_fallbacks"] for row in rows] == [0, 0, 0]
