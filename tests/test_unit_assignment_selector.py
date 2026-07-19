"""Exact-unit selector coverage for durable delegation assignments."""

from __future__ import annotations

from collections.abc import Callable
from threading import Event, Lock
from typing import Any

import pytest

from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    OllamaConfig,
    ProviderEntry,
)
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.selector import judge, pipeline
from agency_runtime.core.unit_assignment import (
    MAX_UNIT_SELECTION_WORKERS,
    assignment_agents_from_catalog,
    build_unit_agent_plan,
    hydrate_unit_agent_plan,
    work_unit_id_from_text,
)


def _routing(*units: str) -> dict[str, Any]:
    return {
        "selected_ids": [],
        "work_units": {
            "delegate": True,
            "count": len(units),
            "confidence": "high",
            "source": "numbered",
            "units": list(units),
        },
    }


def _provider_config(*, max_selected: int = 3) -> AgencyConfig:
    return AgencyConfig(
        judge=JudgeConfig(timeout=1.0, max_selected=max_selected),
        ollama=OllamaConfig(enabled=False),
        providers=(
            ProviderEntry(
                name="unit-selector-test",
                type="ollama",
                model="unit-selector",
                base_url="http://127.0.0.1:11434",
                timeout=1.0,
            ),
        ),
    )


def _capability_kwargs() -> dict[str, Any]:
    return {
        "session_id": "parent",
        "trace_id": "turn",
        "capability_receipt": native_adapter_capability_receipt(
            "codex",
            platform="windows",
            session_id="parent",
            trace_id="turn",
        ),
    }


def _install_provider(
    monkeypatch: pytest.MonkeyPatch,
    choose: Callable[[str, list[dict[str, Any]]], list[str] | None],
) -> list[tuple[str, tuple[str, ...]]]:
    calls: list[tuple[str, tuple[str, ...]]] = []

    def fake_try_provider(
        _provider: ProviderEntry,
        task: str,
        candidates: list[dict[str, Any]],
        _max_selected: int,
        candidate_count: int,
        top_score: float,
        *,
        request_timeout: float,
    ) -> dict[str, Any] | None:
        assert request_timeout > 0
        slugs = tuple(str(item.get("slug") or item.get("agent_slug")) for item in candidates)
        calls.append((task, slugs))
        selected = choose(task, candidates)
        if selected is None:
            return None
        return {
            "selected_ids": selected,
            "confidence": 0.97,
            "latency_ms": 0,
            "status": "applied",
            "candidate_count": candidate_count,
            "top_score": top_score,
        }

    monkeypatch.setattr(judge, "_try_provider", fake_try_provider)
    return calls


def _agent(
    slug: str,
    capability: str,
    *,
    requires: list[str] | None = None,
    conflicts_with: list[str] | None = None,
    required_tools: list[str] | None = None,
    evidence: list[str] | None = None,
    hosts: list[str] | None = None,
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "slug": slug,
        "name": slug.replace("-", " ").title(),
        "description": capability,
        "capabilities": [capability],
        "categories": [capability],
        "requires": requires or [],
        "conflicts_with": conflicts_with or [],
        "required_tools": required_tools or [],
        "evidence_requirements": evidence or [],
        "supported_hosts": hosts or ["codex", "claude", "openclaw", "hermes"],
        "supported_platforms": platforms or ["windows", "linux"],
        "authority": "review",
        "context_mode": "isolated_only",
        "audit_status": "approved",
    }


def test_configured_inference_is_attempted_for_every_exact_work_unit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = [
        _agent("security-reviewer", "authentication security"),
        _agent("technical-writer", "installation documentation"),
        _agent("irrelevant-analyst", "sales forecasting"),
    ]
    units = ("Audit authentication security", "Write installation documentation")
    calls = _install_provider(
        monkeypatch,
        lambda task, _candidates: [
            "security-reviewer" if task.startswith("Audit") else "technical-writer"
        ],
    )

    snapshot = assignment_agents_from_catalog(
        catalog,
        _routing(*units),
        config=_provider_config(),
        session_id="parent",
        trace_id="turn",
        host="codex",
        platform="windows",
        capability_receipt=native_adapter_capability_receipt(
            "codex",
            platform="windows",
            session_id="parent",
            trace_id="turn",
        ),
    )

    assert [task for task, _slugs in calls] == list(units)
    assert all(set(slugs) == {item["slug"] for item in catalog} for _task, slugs in calls)
    assert [item["slug"] for item in snapshot] == [
        "security-reviewer",
        "technical-writer",
    ]
    assert snapshot[0]["primary_work_unit_ids"] == [work_unit_id_from_text(units[0])]
    assert snapshot[1]["primary_work_unit_ids"] == [work_unit_id_from_text(units[1])]


def test_configured_unit_inference_uses_bounded_parallel_workers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = Event()
    lock = Lock()
    active = 0
    maximum_active = 0
    correlations: list[tuple[str, str, str, str]] = []

    def fake_route(session_id: str, *_args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal active, maximum_active
        correlations.append(
            (
                session_id,
                str(kwargs.get("trace_id") or ""),
                str(kwargs.get("capability_session_id") or ""),
                str(kwargs.get("capability_trace_id") or ""),
            )
        )
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
            if active >= 2:
                gate.set()
        try:
            assert gate.wait(timeout=2.0)
            return {
                "selected_ids": ["code-reviewer"],
                "semantic_ids": ["code-reviewer"],
                "inference_configured": True,
                "inference_mode": "inferred",
            }
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(pipeline, "route", fake_route)
    units = tuple(f"Review implementation {index}" for index in range(8))
    capability_kwargs = _capability_kwargs()

    snapshot = assignment_agents_from_catalog(
        [_agent("code-reviewer", "implementation review")],
        _routing(*units),
        config=_provider_config(),
        host="codex",
        platform="windows",
        **capability_kwargs,
    )

    assert 2 <= maximum_active <= MAX_UNIT_SELECTION_WORKERS
    assert snapshot[0]["primary_work_unit_ids"] == [work_unit_id_from_text(unit) for unit in units]
    assert all(session.startswith("parent:unit:unit-") for session, *_rest in correlations)
    assert all(trace.startswith("turn:unit:unit-") for _session, trace, *_rest in correlations)
    assert {
        (parent_session, parent_trace) for *_route, parent_session, parent_trace in correlations
    } == {("parent", "turn")}


def test_host_and_tool_incompatible_agents_never_reach_unit_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = [
        _agent("code-reviewer", "code review", hosts=["codex"]),
        _agent(
            "claude-only-reviewer",
            "code review",
            hosts=["claude"],
        ),
        _agent(
            "browser-reviewer",
            "code review",
            hosts=["codex"],
            required_tools=["browser-automation"],
        ),
    ]
    calls = _install_provider(monkeypatch, lambda _task, _candidates: ["code-reviewer"])

    snapshot = assignment_agents_from_catalog(
        catalog,
        _routing("Review module one", "Review module two"),
        config=_provider_config(),
        host="codex",
        platform="windows",
        **_capability_kwargs(),
    )

    assert len(calls) == 2
    assert all(slugs == ("code-reviewer",) for _task, slugs in calls)
    assert [item["slug"] for item in snapshot] == ["code-reviewer"]


def test_degraded_inference_does_not_promote_lexical_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = [
        _agent("paid-media-auditor", "audit paid media"),
        _agent("search-engine-optimizer", "evaluation search engine"),
    ]
    calls = _install_provider(monkeypatch, lambda _task, _candidates: None)

    snapshot = assignment_agents_from_catalog(
        catalog,
        _routing("audit delegation layer", "design evaluation harness"),
        config=_provider_config(),
        host="codex",
        platform="windows",
        **_capability_kwargs(),
    )

    assert len(calls) == 2
    assert snapshot == []


def test_no_config_path_is_deterministic_and_never_calls_a_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_provider(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("the isolated no-config path must not call inference")

    monkeypatch.setattr(judge, "_try_provider", fail_provider)
    catalog = [
        _agent("database-specialist", "PostgreSQL database migration"),
        _agent("technical-writer", "installation documentation README"),
    ]
    routing = _routing(
        "Migrate the PostgreSQL database",
        "Write installation documentation in the README",
    )

    first = assignment_agents_from_catalog(
        catalog,
        routing,
        host="codex",
        platform="windows",
        **_capability_kwargs(),
    )
    second = assignment_agents_from_catalog(
        catalog,
        routing,
        host="codex",
        platform="windows",
        **_capability_kwargs(),
    )

    assert first == second
    assert [item["slug"] for item in first] == [
        "database-specialist",
        "technical-writer",
    ]


def test_compatible_requirement_closure_is_primary_first_and_unions_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = [
        _agent(
            "architecture-reviewer",
            "delegation architecture review",
            requires=["evidence-specialist"],
            required_tools=["repository-read"],
            evidence=["architecture findings"],
        ),
        _agent(
            "evidence-specialist",
            "test evidence verification",
            required_tools=["test-execution"],
            evidence=["test receipts"],
        ),
    ]
    _install_provider(monkeypatch, lambda _task, _candidates: ["architecture-reviewer"])
    routing = _routing("Review delegation architecture", "Review worker architecture")

    snapshot = assignment_agents_from_catalog(
        catalog,
        routing,
        config=_provider_config(),
        host="codex",
        platform="windows",
        **_capability_kwargs(),
    )
    plan = build_unit_agent_plan({**routing, "unit_assignment_agents": snapshot})

    assert all(
        item["recommended_agents"] == ["architecture-reviewer", "evidence-specialist"]
        for item in plan
    )
    assert all(item["required_tools"] == ["repository-read", "test-execution"] for item in plan)
    assert all(
        item["required_evidence"] == ["architecture findings", "test receipts"] for item in plan
    )
    hydrated = hydrate_unit_agent_plan(
        {**routing, "unit_assignment_agents": snapshot},
        plan,
    )
    assert all(
        item["compatible_specialists"] == ["architecture-reviewer", "evidence-specialist"]
        for item in hydrated
    )


def test_conflicting_inferred_specialist_is_excluded_from_each_unit_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = [
        _agent(
            "implementation-reviewer",
            "implementation review",
            conflicts_with=["conflicting-reviewer"],
        ),
        _agent(
            "conflicting-reviewer",
            "implementation review",
            conflicts_with=["implementation-reviewer"],
        ),
    ]
    _install_provider(
        monkeypatch,
        lambda _task, _candidates: ["implementation-reviewer", "conflicting-reviewer"],
    )
    routing = _routing("Review implementation one", "Review implementation two")

    snapshot = assignment_agents_from_catalog(
        catalog,
        routing,
        config=_provider_config(),
        host="codex",
        platform="windows",
        **_capability_kwargs(),
    )
    plan = build_unit_agent_plan({**routing, "unit_assignment_agents": snapshot})

    assert [item["slug"] for item in snapshot] == ["implementation-reviewer"]
    assert all(item["recommended_agents"] == ["implementation-reviewer"] for item in plan)
