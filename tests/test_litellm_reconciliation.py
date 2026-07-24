"""Focused trust-order contracts for LiteLLM model reconciliation."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.adapters.litellm.callback import AgencyLiteLLMCallback
from agency_runtime.adapters.litellm.reconciliation import reconcile_litellm_model
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.header.contract import _model_line, fill_header_fields
from agency_runtime.core.header.finalize import finalize_response
from agency_runtime.core.receipts.normalize import normalize_litellm_receipt
from agency_runtime.core.roster.bundled import bundled_roster
from agency_runtime.core.store.sqlite import Store

NOW = datetime(2026, 7, 14, tzinfo=timezone.utc)


def _payload(trace_id: str, **changes: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": "task-general",
        "metadata": {
            "agency_trace_id": trace_id,
            "agency_session_id": "session-1",
        },
        "litellm_params": {"custom_llm_provider": "openai"},
    }
    payload.update(changes)
    return payload


def test_standard_payload_keeps_router_group_separate_from_provider_actual() -> None:
    payload = _payload(
        "standard",
        standard_logging_object={
            "model_group": "production-router",
            "hidden_params": {"litellm_model_name": "azure/routed-deployment"},
        },
    )

    actual = reconcile_litellm_model(
        payload,
        {"model": "openai/gpt-5.6-2026-06-30"},
        status="success",
    )

    assert actual.model_group == "production-router"
    assert actual.resolved_provider == "openai"
    assert actual.resolved_model == "gpt-5.6-2026-06-30"


def test_attribute_payload_and_disagreement_prefer_provider_response() -> None:
    standard = SimpleNamespace(
        model_group="reasoning-router",
        hidden_params=SimpleNamespace(
            custom_llm_provider="anthropic",
            litellm_model_name="anthropic/claude-routed",
        ),
    )
    actual = reconcile_litellm_model(
        _payload("object", standard_logging_object=standard),
        SimpleNamespace(model="claude-provider-reported"),
        status="success",
    )

    assert actual.model_group == "reasoning-router"
    assert actual.resolved_provider == "anthropic"
    assert actual.resolved_model == "claude-provider-reported"


def test_disagreeing_lower_priority_model_cannot_fabricate_provider_pair() -> None:
    actual = reconcile_litellm_model(
        _payload(
            "disagreement",
            litellm_params={},
            standard_logging_object={
                "model_group": "router",
                "hidden_params": {"litellm_model_name": "anthropic/claude-sonnet"},
            },
        ),
        {"model": "gpt-5.6"},
        status="success",
    )

    assert actual.resolved_provider == ""
    assert actual.resolved_model == "gpt-5.6"


def test_response_router_alias_echo_yields_to_distinct_routed_deployment() -> None:
    actual = reconcile_litellm_model(
        _payload(
            "alias-echo",
            model="production-router",
            standard_logging_object={
                "model_group": "production-router",
                "hidden_params": {
                    "litellm_model_name": "azure/gpt-5.6-deployment",
                },
                "metadata": {"deployment": "azure/gpt-5.6-deployment"},
            },
        ),
        {"model": "production-router"},
        status="success",
    )

    assert actual.model_group == "production-router"
    assert actual.resolved_provider == "azure"
    assert actual.resolved_model == "gpt-5.6-deployment"


def test_provider_qualified_router_alias_echo_yields_to_routed_deployment() -> None:
    actual = reconcile_litellm_model(
        _payload(
            "qualified-alias-echo",
            model="production-router",
            standard_logging_object={
                "model_group": "production-router",
                "hidden_params": {
                    "litellm_model_name": "azure/gpt-5.6-deployment",
                },
            },
        ),
        {"model": "openai/production-router"},
        status="success",
    )

    assert actual.model_group == "production-router"
    assert actual.resolved_provider == "azure"
    assert actual.resolved_model == "gpt-5.6-deployment"


def test_router_alias_echo_without_deployment_telemetry_stays_unavailable() -> None:
    for response_model, hidden in (
        ("production-router", {}),
        ("openai/production-router", {}),
        (
            "openai/production-router",
            {"litellm_model_name": "production-router"},
        ),
    ):
        actual = reconcile_litellm_model(
            _payload(
                f"unproven-{response_model}",
                model="production-router",
                litellm_params={},
                standard_logging_object={
                    "model_group": "production-router",
                    "hidden_params": hidden,
                },
            ),
            {"model": response_model},
            status="success",
        )

        assert actual.model_group == "production-router"
        assert actual.resolved_provider == ""
        assert actual.resolved_model == "unavailable"


@pytest.mark.parametrize(
    "alias_echo",
    [
        "production-router",
        "openai/production-router",
        "openai/model=production-router",
        "router:production-router",
        "router:production-router:production-router",
        "production-router@litellm",
        "[production-router]",
    ],
)
@pytest.mark.parametrize(
    "source",
    [
        "standard_hidden",
        "response_hidden",
        "standard_metadata",
        "params_deployment",
        "model_info",
    ],
)
def test_absent_response_model_never_promotes_decorated_route_alias(
    alias_echo: str,
    source: str,
) -> None:
    standard_hidden: dict[str, str] = {}
    standard_metadata: dict[str, str] = {}
    response_hidden: dict[str, str] = {}
    params: dict[str, Any] = {"custom_llm_provider": "openai", "model_info": {}}
    if source == "standard_hidden":
        standard_hidden["litellm_model_name"] = alias_echo
    elif source == "response_hidden":
        response_hidden["litellm_model_name"] = alias_echo
    elif source == "standard_metadata":
        standard_metadata["deployment"] = alias_echo
    elif source == "params_deployment":
        params["deployment"] = alias_echo
    else:
        params["model_info"] = {"base_model": alias_echo}

    actual = reconcile_litellm_model(
        _payload(
            f"absent-{source}",
            model="production-router",
            litellm_params=params,
            standard_logging_object={
                "model_group": "production-router",
                "hidden_params": standard_hidden,
                "metadata": standard_metadata,
            },
        ),
        {"_hidden_params": response_hidden},
        status="success",
    )

    assert actual.model_group == "production-router"
    assert actual.resolved_provider == "openai"
    assert actual.resolved_model == "unavailable"


def test_broken_response_identity_isolated_and_records_unavailable(tmp_path: Path) -> None:
    class BrokenResponse:
        @property
        def id(self) -> str:
            raise RuntimeError("unreadable")

    store = Store(tmp_path / "agency.db")
    callback = AgencyLiteLLMCallback(store=store, config=AgencyConfig())

    callback.log_success_event(
        _payload("broken-response-id"),
        BrokenResponse(),
        NOW,
        NOW,
    )

    receipt = store.get_model_receipt("broken-response-id")
    assert receipt is not None
    assert receipt["resolved_model"] == "unavailable"
    assert receipt["source"] == "litellm"
    assert receipt["status"] == "success"


def test_sdk_and_proxy_callbacks_persist_standard_reconciled_receipts(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    callback = AgencyLiteLLMCallback(store=store, config=AgencyConfig())
    callback.log_success_event(
        _payload(
            "sdk",
            standard_logging_object={
                "model_group": "sdk-router",
                "hidden_params": {"litellm_model_name": "azure/sdk-routed"},
            },
        ),
        {"id": "sdk-response", "model": "openai/sdk-provider-actual"},
        NOW,
        NOW,
    )
    asyncio.run(
        callback.async_log_success_event(
            _payload(
                "proxy",
                standard_logging_object=SimpleNamespace(
                    model_group="proxy-router",
                    hidden_params=SimpleNamespace(litellm_model_name="anthropic/proxy-routed"),
                ),
            ),
            {"id": "proxy-response"},
            NOW,
            NOW,
        )
    )

    sdk = store.get_model_receipt("sdk")
    proxy = store.get_model_receipt("proxy")
    assert sdk is not None
    assert sdk["model_group"] == "sdk-router"
    assert sdk["resolved_provider"] == "openai"
    assert sdk["resolved_model"] == "sdk-provider-actual"
    assert proxy is not None
    assert proxy["model_group"] == "proxy-router"
    assert proxy["resolved_provider"] == "anthropic"
    assert proxy["resolved_model"] == "proxy-routed"


def test_model_receipt_does_not_terminalize_turn_before_finalization(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    bundled = {agent["slug"]: agent for agent in bundled_roster()}
    store._activate_prevalidated_agent(bundled["code-reviewer"])
    # Seed code-reviewer's same_context_conflicts closure.
    for slug in ("codebase-onboarding-engineer", "technical-writer"):
        store._activate_prevalidated_agent(bundled[slug])
    callback = AgencyLiteLLMCallback(store=store, config=AgencyConfig())
    preflight = callback.adapter.pre_call_handler(
        "session-1",
        "Review this code change for correctness.",
        "task-general",
        trace_id="lifecycle",
    )
    assert preflight is not None
    assert store.get_run("lifecycle")["status"] == "active"

    callback.log_success_event(
        _payload(
            "lifecycle",
            standard_logging_object={
                "model_group": "review-router",
                "hidden_params": {"litellm_model_name": "openai/routed-review"},
            },
        ),
        {"id": "lifecycle-response", "model": "openai/gpt-5.6-review"},
        NOW,
        NOW,
    )

    assert store.get_run("lifecycle")["status"] == "active"
    store.record_model_receipt(
        trace_id="lifecycle",
        session_id="session-1",
        host="codex",
        requested_model="task-general",
        resolved_provider="anthropic",
        resolved_model="later-concrete-host-model",
        source="host",
        status="success",
    )
    authoritative = store.get_model_receipt("lifecycle")
    assert authoritative is not None
    assert authoritative["source"] == "litellm"
    session_authoritative = store.get_model_receipt_for_session("session-1")
    assert session_authoritative is not None
    assert session_authoritative["source"] == "litellm"
    fields = fill_header_fields({}, "session-1", store, "task-general", "lifecycle")
    assert fields["actual_model_selected"] == (
        "[general] task-general -> openai/gpt-5.6-review via LiteLLM router review-router"
    )
    finalized = finalize_response(
        "Review complete.",
        trace_metadata={
            "session_id": "session-1",
            "trace_id": "lifecycle",
            "host": "litellm",
        },
        store=store,
        model="task-general",
    )
    assert finalized["action"] == "accept"
    assert store.get_run("lifecycle")["status"] == "completed"


def test_standard_routed_model_and_known_deployment_fallbacks_are_bounded() -> None:
    routed = reconcile_litellm_model(
        _payload(
            "routed",
            standard_logging_object={
                "model_group": "g" * 400,
                "hidden_params": {"litellm_model_name": "bedrock/model-routed"},
            },
        ),
        {},
        status="success",
    )
    assert routed.resolved_provider == "bedrock"
    assert routed.resolved_model == "model-routed"
    assert len(routed.model_group) == 256

    deployment = reconcile_litellm_model(
        _payload(
            "deployment",
            standard_logging_object={
                "model_group": "fallback-router",
                "metadata": {"deployment": f"azure/{'m' * 400}"},
            },
        ),
        {},
        status="success",
    )
    assert deployment.resolved_provider == "azure"
    assert deployment.resolved_model == "m" * 256


def test_legacy_hidden_routed_model_remains_compatible() -> None:
    actual = reconcile_litellm_model(
        _payload("legacy"),
        {"_hidden_params": {"litellm_model_name": "groq/llama-routed"}},
        status="success",
    )
    assert actual.resolved_provider == "groq"
    assert actual.resolved_model == "llama-routed"


def test_broken_standard_payload_properties_degrade_without_guessing() -> None:
    class BrokenStandardPayload:
        @property
        def model_group(self) -> str:
            raise RuntimeError("unreadable")

        @property
        def hidden_params(self) -> dict[str, str]:
            raise RuntimeError("unreadable")

        @property
        def metadata(self) -> dict[str, str]:
            raise RuntimeError("unreadable")

    actual = reconcile_litellm_model(
        _payload("broken-standard", standard_logging_object=BrokenStandardPayload()),
        {},
        status="success",
    )
    assert actual.model_group == ""
    assert actual.resolved_provider == "openai"
    assert actual.resolved_model == "unavailable"


def test_opaque_model_id_and_requested_alias_never_become_actual(tmp_path: Path) -> None:
    normalized = normalize_litellm_receipt(
        {
            "x-litellm-model-group": "router",
            "x-litellm-model-id": "openai/fabricated-from-id",
        },
        "task-general",
    )
    assert normalized["model_id"] == "openai/fabricated-from-id"
    assert normalized["resolved_model"] == "unavailable"

    store = Store(tmp_path / "agency.db")
    callback = AgencyLiteLLMCallback(store=store, config=AgencyConfig())
    callback.log_success_event(
        _payload("opaque"),
        {
            "id": "response-without-model",
            "_hidden_params": {
                "additional_headers": {"x-litellm-model-id": "openai/fabricated-from-id"}
            },
        },
        NOW,
        NOW,
    )

    receipt = store.get_model_receipt("opaque")
    assert receipt is not None
    assert receipt["requested_model"] == "task-general"
    assert receipt["model_id"] == "openai/fabricated-from-id"
    assert receipt["model_group"] == ""
    assert receipt["resolved_model"] == "unavailable"


def test_failed_call_never_promotes_success_shaped_telemetry(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    callback = AgencyLiteLLMCallback(store=store, config=AgencyConfig())
    callback.log_failure_event(
        _payload(
            "failed",
            standard_logging_object={
                "model_group": "failure-router",
                "hidden_params": {"litellm_model_name": "openai/must-not-promote"},
            },
        ),
        {"model": "openai/must-not-promote"},
        NOW,
        NOW,
    )

    receipt = store.get_model_receipt("failed")
    assert receipt is not None
    assert receipt["model_group"] == "failure-router"
    assert receipt["resolved_provider"] == ""
    assert receipt["resolved_model"] == "unavailable"
    assert receipt["status"] == "failed"


def test_failure_then_success_transition_is_not_deduped_as_one_terminal_event(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "terminal-transition.db")
    callback = AgencyLiteLLMCallback(store=store, config=AgencyConfig())
    payload = _payload(
        "retry-transition",
        standard_logging_object={
            "model_group": "production-router",
            "hidden_params": {"litellm_model_name": "openai/gpt-5.6-routed"},
        },
    )
    response = {"id": "same-terminal-identity", "model": "openai/gpt-5.6-actual"}

    callback.log_failure_event(payload, response, NOW, NOW)
    callback.log_success_event(payload, response, NOW, NOW)
    # LiteLLM may invoke both sync and async hooks for the same terminal
    # observation.  Equivalent success/failure callbacks remain idempotent.
    asyncio.run(callback.async_log_success_event(payload, response, NOW, NOW))
    asyncio.run(callback.async_log_failure_event(payload, response, NOW, NOW))

    receipt = store.get_model_receipt("retry-transition")
    assert receipt is not None
    assert receipt["status"] == "success"
    assert receipt["model_group"] == "production-router"
    assert receipt["resolved_provider"] == "openai"
    assert receipt["resolved_model"] == "gpt-5.6-actual"
    assert store.runtime_table_counts()["model_receipts"] == 2


def test_session_telemetry_prefers_newest_trace_before_receipt_quality(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_model_receipt(
        trace_id="older-trace",
        session_id="session",
        resolved_provider="openai",
        resolved_model="older-concrete",
        source="litellm",
        status="success",
    )
    store.record_model_receipt(
        trace_id="newer-trace",
        session_id="session",
        resolved_model="unavailable",
        source="host",
        status="success",
    )

    receipt = store.get_model_receipt_for_session("session")
    assert receipt is not None
    assert receipt["trace_id"] == "newer-trace"
    assert receipt["resolved_model"] == "unavailable"


def test_header_names_litellm_router_and_reconciled_actual_explicitly() -> None:
    line = _model_line(
        {
            "requested_model": "task-general",
            "model_group": "production-router",
            "resolved_provider": "openai",
            "resolved_model": "gpt-5.6",
            "source": "litellm",
            "status": "success",
        },
        "",
    )
    assert line == ("[general] task-general -> openai/gpt-5.6 via LiteLLM router production-router")
