"""Parity and redaction tests for operational CLI inference status."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from agency_runtime.cli import status_projection
from agency_runtime.core.config import AgencyConfig, OllamaConfig, ProviderEntry
from agency_runtime.core.dashboard_operational import inference_operational_snapshot


def _config() -> AgencyConfig:
    return replace(
        AgencyConfig(),
        providers=(
            ProviderEntry(
                name="production-router",
                type="litellm",
                model="balanced-router",
                base_url="http://127.0.0.1:4000",
            ),
        ),
        ollama=OllamaConfig(enabled=False),
    )


def _activity() -> dict[str, list[dict[str, object]]]:
    return {
        "receipts": [
            {
                "requested_model": "balanced-router",
                "model_group": "balanced-router",
                "resolved_provider": "anthropic",
                "resolved_model": "claude-sonnet-actual",
                "status": "failed",
                "host": "codex",
                "source": "litellm_callback",
                "recorded_at": "2026-07-18T12:00:00Z",
            }
        ],
        "routing": [
            {
                "trace_id": "trace-1",
                "semantic_status": "degraded",
                "provider": "production-router",
                "created_at": "2026-07-18T12:00:01Z",
            }
        ],
    }


def test_cli_dashboard_inference_projection_has_exact_redacted_parity() -> None:
    config = _config()
    activity = _activity()
    dashboard_projection = inference_operational_snapshot(config, activity)
    store = SimpleNamespace(
        recent_dashboard_activity=lambda *, limit: activity if limit == 50 else None
    )

    direct = status_projection.direct_inference_snapshot(store, config)
    broker_payload = deepcopy(dashboard_projection)
    broker_payload["api_key"] = "must-not-cross"
    broker_payload["prompt_body"] = "must-not-cross"
    broker_payload["provider_chain"][0]["prompt_body"] = "must-not-cross"
    broker_payload["provider_chain"][0]["observed_receipt"]["secret"] = "must-not-cross"
    broker_payload["recent_failures"][0]["raw_response"] = "must-not-cross"
    brokered = status_projection.project_brokered_inference(broker_payload)

    assert direct == dashboard_projection
    assert brokered == dashboard_projection
    assert "must-not-cross" not in repr(brokered)
    assert brokered["provider_chain"][0]["router"] == "balanced-router"
    assert brokered["latest_model_resolution"]["actual_model"] == "claude-sonnet-actual"


def test_broker_projection_handles_empty_optional_receipts() -> None:
    expected = inference_operational_snapshot(
        replace(AgencyConfig(), ollama=OllamaConfig(enabled=False)),
        {},
    )

    assert status_projection.project_brokered_inference(expected) == expected


def test_cli_dashboard_projection_includes_content_free_preflight_failure() -> None:
    activity = {
        "preflight_failures": [
            {
                "schema_version": "agency.preflight.failure.v3",
                "stage": "routing",
                "reason_code": "workforce_inference_failed",
                "invariant_code": "",
                "exception_category": "timeout",
                "provider_attempts": [],
                "staffing_reason_codes": ["selected_agent_budget_exceeded"],
                "hiring_reason_codes": ["gap_evidence_not_hireable"],
                "recorded_at": "2026-07-31T13:00:00Z",
                "trace_id": "failed-trace",
                "host": "codex",
            }
        ]
    }

    expected = inference_operational_snapshot(_config(), activity)
    projected = status_projection.project_brokered_inference(expected)

    assert projected == expected
    assert projected["state"] == "degraded"
    assert projected["failure_count"] == 1
    assert projected["recent_failures"] == [
        {
            "kind": "preflight_failure",
            "status": "preflight_failed",
            "schema_version": "agency.preflight.failure.v3",
            "stage": "routing",
            "reason_code": "workforce_inference_failed",
            "invariant_code": "",
            "exception_category": "timeout",
            "provider_attempts": [],
            "staffing_reason_codes": ["selected_agent_budget_exceeded"],
            "hiring_reason_codes": ["gap_evidence_not_hireable"],
            "recorded_at": "2026-07-31T13:00:00Z",
            "trace_id": "failed-trace",
            "host": "codex",
        }
    ]


def test_broker_projection_rejects_malformed_nested_shapes() -> None:
    with pytest.raises(ValueError, match="non-string"):
        status_projection._text(None, limit=32)
    with pytest.raises(ValueError, match="model receipt"):
        status_projection._receipt([])
    with pytest.raises(ValueError, match="provider entry"):
        status_projection._provider(None)
    valid_provider = deepcopy(
        inference_operational_snapshot(_config(), _activity())["provider_chain"][0]
    )
    for order in (True, "1", 0, 5):
        with pytest.raises(ValueError, match="provider order"):
            status_projection._provider({**valid_provider, "order": order})
    with pytest.raises(ValueError, match="provider readiness"):
        status_projection._provider({**valid_provider, "configuration_ready": "yes"})
    with pytest.raises(ValueError, match="failure kind"):
        status_projection._failure({"kind": "invented"})


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ([], "JSON object"),
        ({}, "schema"),
        (
            {
                **inference_operational_snapshot(
                    replace(AgencyConfig(), ollama=OllamaConfig(enabled=False)),
                    {},
                ),
                "provider_chain": {},
            },
            "bounded collections",
        ),
        (
            {
                **inference_operational_snapshot(
                    replace(AgencyConfig(), ollama=OllamaConfig(enabled=False)),
                    {},
                ),
                "recent_failures": [None],
                "failure_count": 1,
            },
            "failure entry",
        ),
    ],
)
def test_broker_projection_rejects_malformed_top_level_shapes(
    value: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        status_projection.project_brokered_inference(value)


@pytest.mark.parametrize(
    "change",
    [
        {"provider_chain": [None] * 5},
        {"recent_failures": {}},
        {"recent_failures": [None] * 26},
    ],
)
def test_broker_projection_enforces_collection_bounds(change: dict[str, object]) -> None:
    value = {
        **inference_operational_snapshot(
            replace(AgencyConfig(), ollama=OllamaConfig(enabled=False)),
            {},
        ),
        **change,
    }

    with pytest.raises(ValueError, match="bounded collections"):
        status_projection.project_brokered_inference(value)


@pytest.mark.parametrize(
    "change",
    [
        {"configured": None},
        {"required_for_eligible_turns": None},
        {"required_for_eligible_turns": True},
        {"failures_truncated": None},
        {"state": None},
        {"state": "invented"},
        {"failure_count": True},
        {"failure_count": "0"},
        {"failure_count": -1},
        {"failures_truncated": True},
    ],
)
def test_broker_projection_rejects_inconsistent_state(change: dict[str, object]) -> None:
    value = {
        **inference_operational_snapshot(
            replace(AgencyConfig(), ollama=OllamaConfig(enabled=False)),
            {},
        ),
        **change,
    }

    with pytest.raises(ValueError, match="internally inconsistent"):
        status_projection.project_brokered_inference(value)
