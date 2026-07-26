"""Compatibility and consolidation contracts retained through 0.2.x."""

from __future__ import annotations

import importlib

import pytest

from agency_runtime.core.agent_identity import agent_identity
from agency_runtime.core.bounded_values import bounded_unique_strings


def test_route_and_build_context_warns_and_forwards_exact_inputs(monkeypatch) -> None:
    pipeline = importlib.import_module("agency_runtime.core.selector.pipeline")
    config = object()
    catalog = [{"slug": "reviewer"}]
    routed = {"selected_ids": ["reviewer"]}
    observed: dict[str, object] = {}

    def fake_route(session_id, user_message, received_catalog, **kwargs):
        observed.update(
            session_id=session_id,
            user_message=user_message,
            catalog=received_catalog,
            kwargs=kwargs,
        )
        return routed

    monkeypatch.setattr(pipeline, "_get_config", lambda received, _store: received)
    monkeypatch.setattr(pipeline, "route", fake_route)
    monkeypatch.setattr(
        pipeline,
        "build_routing_context",
        lambda routing, received_config: (routing, received_config),
    )

    with pytest.warns(DeprecationWarning, match="not be removed before.*0.3.0"):
        result = pipeline.route_and_build_context(
            "session-1",
            "review this",
            catalog,
            config=config,
            trace_id="trace-1",
        )

    assert result == (routed, config)
    assert observed == {
        "session_id": "session-1",
        "user_message": "review this",
        "catalog": catalog,
        "kwargs": {
            "config": config,
            "store": None,
            "trace_id": "trace-1",
            "turn_classification": None,
            "turn_state": None,
        },
    }


def test_finalize_alias_warns_and_forwards_exact_inputs(monkeypatch) -> None:
    finalizer = importlib.import_module("agency_runtime.core.header.finalize")
    metadata = {"trace_id": "trace-1"}
    store = object()
    expected = {"action": "pass", "text": "draft", "missing": []}
    observed: dict[str, object] = {}

    def fake_finalize(draft_text, **kwargs):
        observed.update(draft_text=draft_text, **kwargs)
        return expected

    monkeypatch.setattr(finalizer, "finalize_response", fake_finalize)

    with pytest.warns(DeprecationWarning, match="not be removed before.*0.3.0"):
        result = finalizer.finalize(
            "draft",
            trace_metadata=metadata,
            store=store,
            model="provider/model",
        )

    assert result is expected
    assert observed == {
        "draft_text": "draft",
        "trace_metadata": metadata,
        "store": store,
        "model": "provider/model",
    }


def test_canonical_agent_identity_prefers_slug_over_legacy_alias() -> None:
    assert agent_identity({"slug": " canonical ", "agent_slug": "legacy"}) == "canonical"
    assert agent_identity({"agent_slug": " legacy "}) == "legacy"


def test_bounded_string_projection_limits_scan_and_normalizes_when_requested() -> None:
    assert bounded_unique_strings(
        [" alpha  beta ", "alpha beta", "outside"],
        limit=2,
        chars=20,
        collapse_whitespace=True,
    ) == ["alpha beta"]
    with pytest.raises(ValueError, match="non-negative integers"):
        bounded_unique_strings([], limit=-1, chars=20)
