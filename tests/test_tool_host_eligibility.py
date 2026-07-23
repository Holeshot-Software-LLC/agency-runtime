"""Operational execution-host and tool-capability eligibility contracts."""

from __future__ import annotations

import hashlib
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

import agency_runtime.core.host_capabilities as host_capabilities_module
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.host_capabilities import (
    EXECUTION_HOSTS,
    MAX_CAPABILITY_EVIDENCE_ITEMS,
    MAX_TOOL_CAPABILITIES,
    HostCapabilityReceipt,
    canonicalize_tool_capabilities,
    current_host_capability_receipt,
    diagnostic_installation_capability_receipt,
    execution_contract_projection,
    host_capability_receipt,
    host_capability_receipt_from_native_evidence,
    native_adapter_capability_receipt,
    project_host_capability_receipt,
)
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.preflight_recipe import _content_free_routing_recipe
from agency_runtime.core.roster.bundled import bundled_manifest
from agency_runtime.core.selector import pipeline
from agency_runtime.core.selector.compatibility import filter_eligible_catalog
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.store.queries import project_routing_decision
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.unit_assignment import (
    MAX_WORK_UNIT_CHARS,
    MAX_WORK_UNIT_PREVIEW_CHARS,
    work_unit_id_from_text,
)


def _agent(slug: str, **overrides: Any) -> dict[str, Any]:
    return {
        "slug": slug,
        "audit_status": "approved",
        "routing_contract_valid": True,
        "supported_hosts": ["codex", "claude", "openclaw", "hermes"],
        "supported_platforms": ["windows", "linux"],
        "required_tools": [],
        "authority": "plan",
        "context_mode": "direct_safe",
        **overrides,
    }


def test_tool_aliases_are_canonical_bounded_and_unknowns_stay_unknown() -> None:
    capabilities, unknown = canonicalize_tool_capabilities(
        [
            "source",
            "repository",
            "filesystem-search",
            "documentation-test-runner",
            "shell",
            "not-a-governed-tool",
        ]
    )

    assert capabilities == ("repository-read", "shell-execution", "test-execution")
    assert unknown == ("not-a-governed-tool",)


def test_test_result_and_coverage_readers_use_test_execution_capability() -> None:
    capabilities, unknown = canonicalize_tool_capabilities(
        ("test-results-reader", "coverage-reader")
    )

    assert capabilities == ("test-execution",)
    assert unknown == ()


def test_staffing_plan_and_workforce_readers_use_runtime_evidence_capability() -> None:
    capabilities, unknown = canonicalize_tool_capabilities(
        ("staffing-plan-reader", "workforce-index")
    )

    assert capabilities == ("runtime-evidence",)
    assert unknown == ()


def test_tool_capability_normalization_rejects_invalid_and_overflow_labels() -> None:
    capabilities, unknown = canonicalize_tool_capabilities(
        [None, *("source" for _index in range(MAX_TOOL_CAPABILITIES))]
    )

    assert capabilities == ("repository-read",)
    assert unknown == ("capability-list-overflow", "invalid-capability-label")


def test_every_reviewed_bundled_tool_label_is_in_the_governed_registry() -> None:
    manifest = bundled_manifest()
    labels = {
        tool
        for agent in manifest["agents"]
        if agent["audit_status"] == "approved"
        for tool in agent["required_tools"]
    }

    unknown = {tool for tool in labels if canonicalize_tool_capabilities((tool,))[1]}
    assert unknown == set()


@pytest.mark.parametrize("host", EXECUTION_HOSTS)
def test_host_name_alone_never_emits_execution_capabilities(host: str) -> None:
    receipt = host_capability_receipt(host, platform="linux")

    assert receipt.surface == host
    assert receipt.execution_host == ""
    assert receipt.inference_surface == ""
    assert receipt.status == "native-evidence-unproven"
    assert receipt.capabilities == ()
    assert receipt.evidence == ("unproven:missing-native-adapter-receipt",)
    assert project_host_capability_receipt(receipt.as_dict()) == receipt.as_dict()


@pytest.mark.parametrize("host", EXECUTION_HOSTS)
def test_each_native_adapter_emits_current_correlation_capabilities(host: str) -> None:
    receipt = native_adapter_capability_receipt(
        host,
        platform="linux",
        session_id="session",
        trace_id="trace",
    )

    assert receipt.surface == host
    assert receipt.execution_host == host
    assert receipt.inference_surface == ""
    assert receipt.status == "native-contract-verified"
    assert "repository-read" in receipt.capabilities
    assert "native-delegation" in receipt.capabilities
    assert receipt.evidence == (
        f"native-adapter-event:{host}",
        "managed-host-contract:1",
    )
    assert project_host_capability_receipt(receipt.as_dict()) == receipt.as_dict()


def test_native_receipt_is_opaque_and_cannot_be_reconstructed_from_transport_data() -> None:
    receipt = native_adapter_capability_receipt(
        "codex",
        platform="linux",
        session_id="session",
        trace_id="trace",
    )
    serialized = receipt.as_dict()
    reconstructed = HostCapabilityReceipt(
        surface=serialized["surface"],
        execution_host=serialized["execution_host"],
        inference_surface=serialized["inference_surface"],
        platform=serialized["platform"],
        status=serialized["status"],
        source=serialized["source"],
        capabilities=tuple(serialized["capabilities"]),
        unknown_tools=tuple(serialized["unknown_tools"]),
        evidence=tuple(serialized["evidence"]),
        session_id=serialized["session_id"],
        trace_id=serialized["trace_id"],
        observed_at=serialized["observed_at"],
    )

    resolved = current_host_capability_receipt(
        reconstructed,
        surface="codex",
        platform="linux",
        session_id="session",
        trace_id="trace",
    )

    assert resolved.execution_host == ""
    assert resolved.capabilities == ()
    assert resolved.evidence == ("unproven:missing-attestation",)


@pytest.mark.parametrize(
    ("surface", "platform", "session_id", "trace_id", "reason"),
    [
        ("claude", "linux", "session", "trace", "host-mismatch"),
        ("codex", "windows", "session", "trace", "platform-mismatch"),
        ("codex", "linux", "other-session", "trace", "correlation-mismatch"),
        ("codex", "linux", "session", "other-trace", "correlation-mismatch"),
    ],
)
def test_native_receipt_rejects_cross_host_platform_and_correlation_reuse(
    surface: str,
    platform: str,
    session_id: str,
    trace_id: str,
    reason: str,
) -> None:
    receipt = native_adapter_capability_receipt(
        "codex",
        platform="linux",
        session_id="session",
        trace_id="trace",
    )

    resolved = current_host_capability_receipt(
        receipt,
        surface=surface,
        platform=platform,
        session_id=session_id,
        trace_id=trace_id,
    )

    assert resolved.execution_host == ""
    assert resolved.capabilities == ()
    assert resolved.evidence == (f"unproven:{reason}",)


def test_native_receipt_rejects_tampering_and_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = native_adapter_capability_receipt(
        "codex",
        platform="linux",
        session_id="session",
        trace_id="trace",
    )
    tampered = replace(
        receipt,
        capabilities=tuple(sorted({*receipt.capabilities, "browser-automation"})),
    )
    rejected = current_host_capability_receipt(
        tampered,
        surface="codex",
        platform="linux",
        session_id="session",
        trace_id="trace",
    )
    assert rejected.evidence == ("unproven:invalid-attestation",)

    monkeypatch.setattr(
        host_capabilities_module,
        "_monotonic_ns",
        lambda: receipt._expires_monotonic_ns + 1,
    )
    stale = current_host_capability_receipt(
        receipt,
        surface="codex",
        platform="linux",
        session_id="session",
        trace_id="trace",
    )
    assert stale.execution_host == ""
    assert stale.capabilities == ()
    assert stale.evidence == ("unproven:stale-attestation",)


def test_unknown_platform_and_untrusted_tools_cannot_widen_native_capabilities() -> None:
    unsupported = native_adapter_capability_receipt(
        "codex",
        platform="plan9",
        session_id="session",
        trace_id="trace",
        available_tools=("shell", "source"),
    )
    claimed = host_capability_receipt(
        "codex",
        platform="linux",
        available_tools=("shell", "source"),
        session_id="session",
        trace_id="trace",
    )
    restricted = native_adapter_capability_receipt(
        "codex",
        platform="linux",
        session_id="session",
        trace_id="trace",
        restricted=True,
    )
    current_restricted = current_host_capability_receipt(
        restricted,
        surface="codex",
        platform="linux",
        session_id="session",
        trace_id="trace",
    )

    assert unsupported.status == "native-evidence-unproven"
    assert unsupported.platform == "unknown"
    assert unsupported.capabilities == ()
    assert claimed.status == "native-evidence-unproven"
    assert claimed.capabilities == ()
    assert claimed.evidence == ("unproven:untrusted-explicit-tool-list",)
    assert current_restricted == restricted
    assert current_restricted.status == "native-evidence-unproven"
    assert current_restricted.capabilities == ()
    assert current_restricted.evidence == ("unproven:adapter-reported-restricted",)


def test_capability_factories_reject_invalid_host_and_partial_correlation() -> None:
    with pytest.raises(ValueError, match="supported execution host"):
        native_adapter_capability_receipt(
            "mcp",
            platform="linux",
            session_id="session",
            trace_id="trace",
        )
    with pytest.raises(ValueError, match="supplied together"):
        host_capability_receipt(
            "codex",
            platform="linux",
            session_id="session",
        )


def test_current_receipt_normalizes_unsupported_platform_to_unproven() -> None:
    receipt = native_adapter_capability_receipt(
        "codex",
        platform="linux",
        session_id="session",
        trace_id="trace",
    )

    resolved = current_host_capability_receipt(
        receipt,
        surface="codex",
        platform="plan9",
        session_id="session",
        trace_id="trace",
    )

    assert resolved.platform == "unknown"
    assert resolved.evidence == ("unproven:platform-mismatch",)


@pytest.mark.parametrize("host", EXECUTION_HOSTS)
def test_native_inventory_requires_exact_installation_proof(host: str) -> None:
    verified = host_capability_receipt_from_native_evidence(
        host,
        platform="windows",
        native_record={
            "host": host,
            "executable_discovered": True,
            "registered": True,
            "enabled": True,
            "managed_plugin_version": "1.0.0",
            "launcher_artifacts_current": True,
        },
    )
    unproven = host_capability_receipt_from_native_evidence(
        host,
        platform="windows",
        native_record={
            "host": host,
            "executable_discovered": True,
            "registered": True,
            "enabled": None,
            "managed_plugin_version": "1.0.0",
            "launcher_artifacts_current": True,
        },
    )

    assert verified.execution_host == host
    assert verified.status == "native-installation-verified"
    assert project_host_capability_receipt(verified.as_dict()) == verified.as_dict()
    assert unproven.execution_host == ""
    assert unproven.status == "native-evidence-unproven"
    assert unproven.capabilities == ()
    assert unproven.evidence == ("unproven:enabled",)
    assert project_host_capability_receipt(unproven.as_dict()) == unproven.as_dict()


def test_installation_receipt_is_eligible_only_in_explicit_diagnostic_scope() -> None:
    inventory = host_capability_receipt_from_native_evidence(
        "codex",
        platform="linux",
        native_record={
            "host": "codex",
            "executable_discovered": True,
            "registered": True,
            "enabled": True,
            "managed_plugin_version": "1.0.0",
            "launcher_artifacts_current": True,
        },
    )
    diagnostic = diagnostic_installation_capability_receipt(
        inventory.as_dict(),
        surface="codex",
        platform="linux",
    )

    assert diagnostic is not None
    live = current_host_capability_receipt(
        diagnostic,
        surface="codex",
        platform="linux",
        session_id="session",
        trace_id="trace",
    )
    projected = current_host_capability_receipt(
        diagnostic,
        surface="codex",
        platform="linux",
        session_id="diagnostic-session",
        trace_id="diagnostic-trace",
        allow_installation_diagnostic=True,
    )

    assert live.status == "native-evidence-unproven"
    assert live.capabilities == ()
    assert projected == diagnostic


@pytest.mark.parametrize(
    ("surface", "platform"),
    [("claude", "linux"), ("codex", "windows"), ("mcp", "linux"), ("codex", "plan9")],
)
def test_diagnostic_installation_receipt_rejects_cross_surface_and_platform(
    surface: str,
    platform: str,
) -> None:
    inventory = host_capability_receipt_from_native_evidence(
        "codex",
        platform="linux",
        native_record={
            "host": "codex",
            "executable_discovered": True,
            "registered": True,
            "enabled": True,
            "managed_plugin_version": "1.0.0",
            "launcher_artifacts_current": True,
        },
    )

    assert (
        diagnostic_installation_capability_receipt(
            inventory.as_dict(),
            surface=surface,
            platform=platform,
        )
        is None
    )


def test_litellm_is_an_inference_surface_and_never_an_execution_host() -> None:
    receipt = host_capability_receipt(
        "litellm",
        platform="windows",
        available_tools=("shell", "source"),
    )

    assert receipt.execution_host == ""
    assert receipt.inference_surface == "litellm"
    assert receipt.status == "inference-only"
    assert receipt.capabilities == ()
    assert project_host_capability_receipt(receipt.as_dict()) == receipt.as_dict()


def test_unknown_surface_is_visible_and_cannot_prove_execution() -> None:
    receipt = host_capability_receipt("mcp", platform="unknown")

    assert receipt.execution_host == ""
    assert receipt.inference_surface == ""
    assert receipt.status == "unknown"
    assert receipt.capabilities == ()
    assert receipt.evidence == ("execution-host-unproven",)


def test_unknown_surface_keeps_explicit_tools_non_executable_and_bounds_platform() -> None:
    receipt = host_capability_receipt(
        "mcp",
        platform="plan9",
        available_tools=("source",),
    )

    assert receipt.platform == "unknown"
    assert receipt.status == "explicit-tools-without-execution-host"
    assert receipt.capabilities == ("repository-read",)
    assert project_host_capability_receipt(receipt.as_dict()) == receipt.as_dict()


def test_reasoning_only_specialist_remains_routable_without_tool_evidence() -> None:
    result = filter_eligible_catalog([_agent("planner")])

    assert [item["slug"] for item in result.eligible] == ["planner"]
    assert result.rejected == ()


def test_present_missing_unknown_and_aliased_tool_requirements_are_explained() -> None:
    catalog = [
        _agent("source-reader", required_tools=["repository"]),
        _agent("shell-user", required_tools=["shell"]),
        _agent("unknown-tool", required_tools=["mystery-console"]),
    ]

    explicit = filter_eligible_catalog(
        catalog,
        host="codex",
        platform="windows",
        available_tools={"source"},
    )

    assert [item["slug"] for item in explicit.eligible] == ["source-reader"]
    assert explicit.rejected == (
        {"slug": "shell-user", "reason": "missing_capabilities:shell-execution"},
        {
            "slug": "unknown-tool",
            "reason": "unknown_tool_requirement:mystery-console",
        },
    )

    unknown = filter_eligible_catalog(
        [catalog[0]],
        host="codex",
        platform="windows",
        available_tools=None,
    )
    assert unknown.rejected == (
        {
            "slug": "source-reader",
            "reason": "tool_capabilities_unproven:unknown",
        },
    )


def test_inference_surface_only_accepts_explicit_direct_safe_reasoning_contracts() -> None:
    catalog = [
        _agent("reasoner", supported_hosts=["codex", "litellm"]),
        _agent(
            "tool-user",
            supported_hosts=["codex", "litellm"],
            required_tools=["source"],
        ),
        _agent(
            "isolated",
            supported_hosts=["codex", "litellm"],
            context_mode="isolated_only",
        ),
        _agent("native-only", supported_hosts=["codex"]),
    ]

    result = filter_eligible_catalog(
        catalog,
        host="unknown",
        inference_surface="litellm",
        platform="windows",
        available_tools=(),
        capability_status="inference-only",
    )

    assert [item["slug"] for item in result.eligible] == ["reasoner"]
    assert result.rejected == (
        {"slug": "tool-user", "reason": "inference_surface_has_no_execution_tools"},
        {
            "slug": "isolated",
            "reason": "inference_surface_requires_isolation:litellm",
        },
        {
            "slug": "native-only",
            "reason": "unsupported_inference_surface:litellm",
        },
    )


def test_reasoning_and_tool_platforms_are_distinct_without_widening_execution() -> None:
    reasoning = _agent(
        "reasoning",
        supported_platforms=["linux"],
    )
    executable = _agent(
        "executable",
        supported_platforms=["linux"],
        required_tools=["source"],
    )

    projection = execution_contract_projection(reasoning)
    assert projection["supported_reasoning_platforms"] == ["windows", "linux"]
    assert projection["supported_tool_platforms"] == ["linux"]

    result = filter_eligible_catalog(
        [reasoning, executable],
        host="codex",
        platform="windows",
        available_tools={"source"},
    )
    assert [item["slug"] for item in result.eligible] == ["reasoning"]
    assert result.rejected == (
        {"slug": "executable", "reason": "unsupported_tool_platform:windows"},
    )


@pytest.mark.parametrize(
    ("agent", "route_context", "reason"),
    [
        (
            _agent("unknown-inference", supported_hosts=["codex", "litellm"]),
            {"inference_surface": "mystery"},
            "unknown_inference_surface:mystery",
        ),
        (
            _agent(
                "inference-platform",
                supported_hosts=["litellm"],
                supported_platforms=["linux"],
                authority="execute",
            ),
            {"inference_surface": "litellm", "platform": "windows"},
            "unsupported_reasoning_platform:windows",
        ),
        (
            _agent("tool-unproven", required_tools=["source"]),
            {},
            "execution_host_unproven",
        ),
        (
            _agent(
                "tool-host",
                required_tools=["source"],
                supported_hosts=["codex"],
            ),
            {"host": "claude", "available_tools": {"source"}},
            "unsupported_execution_host:claude",
        ),
        (
            _agent("isolated-reasoning", context_mode="isolated_only"),
            {},
            "execution_host_unproven",
        ),
        (
            _agent(
                "reasoning-platform",
                authority="execute",
                supported_platforms=["linux"],
            ),
            {"host": "codex", "platform": "windows"},
            "unsupported_reasoning_platform:windows",
        ),
        (
            _agent("", name="missing"),
            {},
            "missing_slug",
        ),
        (
            _agent("invalid", routing_contract_valid=False),
            {},
            "invalid_routing_contract",
        ),
        (
            _agent("quarantined", audit_status="quarantined"),
            {},
            "audit_status:quarantined",
        ),
        (
            _agent("unknown-surface", supported_hosts=["codex", "future-host"]),
            {},
            "unknown_supported_surface:future-host",
        ),
    ],
)
def test_eligibility_rejections_are_specific_and_explainable(
    agent: dict[str, Any],
    route_context: dict[str, Any],
    reason: str,
) -> None:
    result = filter_eligible_catalog([agent], **route_context)

    assert result.eligible == ()
    assert result.rejected == ({"slug": agent["slug"], "reason": reason},)


def test_legacy_litellm_host_argument_is_projected_as_inference_surface() -> None:
    result = filter_eligible_catalog(
        [_agent("reasoner", supported_hosts=["litellm"])],
        host="litellm",
        platform="linux",
        available_tools=(),
    )

    assert [agent["slug"] for agent in result.eligible] == ["reasoner"]


def test_selector_receipt_separates_litellm_from_native_execution(monkeypatch) -> None:
    catalog = [_agent("reasoner", supported_hosts=["codex", "litellm"])]
    monkeypatch.setattr(
        pipeline,
        "query_judge",
        lambda *_args, **_kwargs: {
            "selected_ids": ["reasoner"],
            "confidence": 0.9,
            "latency_ms": 1,
            "status": "applied",
        },
    )

    routed = pipeline.route(
        "session",
        "Develop a bounded technical plan",
        catalog,
        config=AgencyConfig(),
        host="litellm",
        platform="windows",
    )

    assert routed["semantic_ids"] == ["reasoner"]
    assert routed["execution_context"]["execution_host"] == ""
    assert routed["execution_context"]["inference_surface"] == "litellm"
    assert routed["execution_context"]["capabilities"] == []


def test_selector_rejects_cross_correlation_receipt_before_hard_eligibility() -> None:
    receipt = native_adapter_capability_receipt(
        "codex",
        platform="linux",
        session_id="source-session",
        trace_id="source-trace",
    )
    routed = pipeline.route(
        "other-session",
        "Modify the repository",
        [
            _agent(
                "repository-writer",
                authority="modify",
                context_mode="isolated_only",
                required_tools=["repository-write"],
            )
        ],
        config=AgencyConfig(),
        trace_id="other-trace",
        host="codex",
        platform="linux",
        capability_receipt=receipt,
    )

    assert routed["selected_ids"] == []
    assert routed["execution_context"]["status"] == "native-evidence-unproven"
    assert routed["execution_context"]["capabilities"] == []
    assert routed["eligibility_rejections"] == [
        {"slug": "repository-writer", "reason": "execution_host_unproven"}
    ]


def test_exact_unit_route_uses_parent_capability_correlation_not_cache_identity() -> None:
    receipt = native_adapter_capability_receipt(
        "codex",
        platform="linux",
        session_id="parent-session",
        trace_id="parent-trace",
    )
    routed = pipeline.route(
        "parent-session:unit:unit-one",
        "Review the repository",
        [_agent("repository-reader", required_tools=["repository-read"])],
        config=AgencyConfig(),
        trace_id="parent-trace:unit:unit-one",
        host="codex",
        platform="linux",
        capability_receipt=receipt,
        capability_session_id="parent-session",
        capability_trace_id="parent-trace",
    )

    assert routed["execution_context"] == receipt.as_dict()
    assert routed["eligibility_rejections"] == []


def test_visible_work_unit_projection_keeps_full_transport_identity_and_all_previews() -> None:
    first = "A" * MAX_WORK_UNIT_PREVIEW_CHARS + "-FIRST-TAIL" + "x" * MAX_WORK_UNIT_CHARS
    second = "B" * MAX_WORK_UNIT_PREVIEW_CHARS + "-SECOND-TAIL" + "y" * MAX_WORK_UNIT_CHARS
    bounded = pipeline._bounded_work_units(
        {
            "count": 2,
            "confidence": "high",
            "source": "numbered_list",
            "units": [first, second],
            "delegate": True,
        }
    )
    expected_first = first[:MAX_WORK_UNIT_CHARS]
    expected_second = second[:MAX_WORK_UNIT_CHARS]

    assert bounded["units"] == [expected_first, expected_second]
    context = pipeline.build_routing_context(
        {
            "selected_ids": [],
            "confidence": 0.0,
            "status": "abstained",
            "work_units": bounded,
        },
        AgencyConfig(),
    )

    assert f"[{work_unit_id_from_text(expected_first)}]" in context
    assert f"[{work_unit_id_from_text(expected_second)}]" in context
    assert "A" * MAX_WORK_UNIT_PREVIEW_CHARS in context
    assert "B" * MAX_WORK_UNIT_PREVIEW_CHARS in context
    assert "-FIRST-TAIL" not in context
    assert "-SECOND-TAIL" not in context


def test_preflight_never_routes_hard_requirements_with_unknown_tool_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agency_runtime.core.installer as installer

    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(
        {
            "slug": "tool-agent",
            "name": "Tool Agent",
            "description": "Reads a repository with an explicit tool requirement.",
            "prompt_body": "Use only the assigned repository-read capability.",
            "audit_status": "approved",
            "authority": "modify",
            "context_mode": "isolated_only",
            "required_tools": ["repository"],
            "supported_hosts": ["codex"],
            "supported_platforms": ["windows", "linux"],
            "version": "1.0.0",
        }
    )
    observed: list[tuple[tuple[str, ...] | None, HostCapabilityReceipt | None]] = []
    monkeypatch.setattr(installer, "seed_starter_roster", lambda _store: 0)
    monkeypatch.setattr(installer, "ensure_no_match_fallback_roster", lambda _store: False)

    def route(*_args: Any, **kwargs: Any) -> dict[str, Any]:
        observed.append((kwargs.get("available_tools"), kwargs.get("capability_receipt")))
        message = "Review the change"
        return {
            "selected_ids": [],
            "confidence": 0.0,
            "status": "abstained",
            "source": "test",
            "query_hash": hashlib.sha256(message.encode()).hexdigest(),
            "context_fingerprint": "c" * 64,
            "work_units": detect_work_units(message),
        }

    monkeypatch.setattr(pipeline, "route", route)
    result = run_preflight(
        store,
        session_id="session",
        user_message="Review the change",
        host="codex",
        trace_id="tool-receipt-turn",
    )

    assert result.trace_id == "tool-receipt-turn"
    assert observed
    available_tools, receipt = observed[0]
    assert available_tools == ()
    assert receipt is not None
    assert receipt.status == "native-evidence-unproven"
    assert receipt.execution_host == ""


def test_policy_roster_change_invalidates_cache_even_when_agent_is_host_ineligible(
    tmp_path: Path,
) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        "actions:\n"
        "  RELEASE:\n"
        "    triggers: [release]\n"
        "    always_include:\n"
        "      - slug: linux-release-agent\n"
        "    conditional: []\n",
        encoding="utf-8",
    )
    policy_path.chmod(0o600)
    config = AgencyConfig(companion_policy_path=str(policy_path))
    receipt = native_adapter_capability_receipt(
        "codex",
        platform="windows",
        session_id="session",
        trace_id="trace",
    )
    linux_only = {
        "slug": "linux-release-agent",
        "name": "Linux Release Agent",
        "description": "Validates Linux releases.",
        "prompt_body": "Validate the assigned Linux release.",
        "audit_status": "approved",
        "supported_hosts": ["codex"],
        "supported_platforms": ["linux"],
    }

    missing = pipeline._route_request(
        "session",
        "release this build",
        [],
        config,
        host="codex",
        platform="windows",
        capability_receipt=receipt,
    )
    present = pipeline._route_request(
        "session",
        "release this build",
        [linux_only],
        config,
        host="codex",
        platform="windows",
        capability_receipt=receipt,
    )

    assert missing.catalog == present.catalog == []
    assert missing.context_fingerprint != present.context_fingerprint
    assert pipeline._route_signals(missing).policy_validation["valid"] is False
    assert pipeline._route_signals(present).policy_validation["valid"] is True


def test_mcp_caller_host_string_cannot_mint_native_contract_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agency_runtime.core.installer as installer
    from agency_runtime.server import mcp_tools

    store = Store(tmp_path / "agency.db")
    observed: list[HostCapabilityReceipt | None] = []
    monkeypatch.setattr(installer, "seed_starter_roster", lambda _store: 0)
    monkeypatch.setattr(installer, "ensure_no_match_fallback_roster", lambda _store: False)

    def route(*_args: Any, **kwargs: Any) -> dict[str, Any]:
        observed.append(kwargs.get("capability_receipt"))
        message = "Review the change"
        return {
            "selected_ids": [],
            "confidence": 0.0,
            "status": "abstained",
            "source": "test",
            "query_hash": hashlib.sha256(message.encode()).hexdigest(),
            "context_fingerprint": "c" * 64,
            "work_units": detect_work_units(message),
        }

    monkeypatch.setattr(pipeline, "route", route)
    response = mcp_tools._preflight(
        {
            "session_id": "mcp-session",
            "trace_id": "mcp-trace",
            "host": "codex",
            "user_message": "Review the change",
        },
        store,
    )

    assert response["trace_id"] == "mcp-trace"
    assert len(observed) == 1
    assert observed[0] is not None
    assert observed[0].status == "native-evidence-unproven"
    assert observed[0].execution_host == ""
    assert observed[0].capabilities == ()


def test_preflight_preserves_exact_current_native_adapter_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agency_runtime.core.installer as installer

    store = Store(tmp_path / "agency.db")
    observed: list[HostCapabilityReceipt | None] = []
    monkeypatch.setattr(installer, "seed_starter_roster", lambda _store: 0)
    monkeypatch.setattr(installer, "ensure_no_match_fallback_roster", lambda _store: False)

    def route(*_args: Any, **kwargs: Any) -> dict[str, Any]:
        observed.append(kwargs.get("capability_receipt"))
        message = "Review the change"
        return {
            "selected_ids": [],
            "confidence": 0.0,
            "status": "abstained",
            "source": "test",
            "query_hash": hashlib.sha256(message.encode()).hexdigest(),
            "context_fingerprint": "c" * 64,
            "work_units": detect_work_units(message),
        }

    monkeypatch.setattr(pipeline, "route", route)
    runtime_platform = "windows" if os.name == "nt" else "linux"
    receipt = native_adapter_capability_receipt(
        "codex",
        platform=runtime_platform,
        session_id="session",
        trace_id="attested-turn",
    )
    result = run_preflight(
        store,
        session_id="session",
        user_message="Review the change",
        host="codex",
        trace_id="attested-turn",
        capability_receipt=receipt,
    )

    assert result.trace_id == "attested-turn"
    assert observed == [receipt]
    assert "repository-write" in receipt.capabilities


def test_capability_receipt_projection_rejects_fabricated_execution_hosts() -> None:
    receipt = native_adapter_capability_receipt(
        "codex",
        platform="linux",
        session_id="session",
        trace_id="trace",
    ).as_dict()
    receipt["execution_host"] = "litellm"

    assert project_host_capability_receipt(receipt) is None


def test_capability_projection_rejects_invalid_or_unbound_correlation_metadata() -> None:
    verified = native_adapter_capability_receipt(
        "codex",
        platform="linux",
        session_id="session",
        trace_id="trace",
    ).as_dict()
    invalid_session = {**verified, "session_id": "bad\x00session"}
    partial = {**verified, "trace_id": ""}
    unbound = {**verified, "session_id": "", "trace_id": "", "observed_at": ""}
    oversized_timestamp = {**verified, "observed_at": "x" * 65}
    malformed_timestamp = {**verified, "observed_at": "not-a-timestamp"}
    timezone_ambiguous_timestamp = {**verified, "observed_at": "2026-07-18T12:00:00"}
    installation = host_capability_receipt_from_native_evidence(
        "codex",
        platform="linux",
        native_record={
            "host": "codex",
            "executable_discovered": True,
            "registered": True,
            "enabled": True,
            "managed_plugin_version": "1.0.0",
            "launcher_artifacts_current": True,
        },
    ).as_dict()
    installation["session_id"] = "session"
    installation["trace_id"] = "trace"

    assert project_host_capability_receipt(invalid_session) is None
    assert project_host_capability_receipt(partial) is None
    assert project_host_capability_receipt(unbound) is None
    assert project_host_capability_receipt(oversized_timestamp) is None
    assert project_host_capability_receipt(malformed_timestamp) is None
    assert project_host_capability_receipt(timezone_ambiguous_timestamp) is None
    assert project_host_capability_receipt(installation) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("contract_version", "future"),
        ("execution_host", "litellm"),
        ("inference_surface", "litellm"),
        ("platform", "plan9"),
        ("status", "fabricated"),
        ("source", ""),
        ("capabilities", "repository-read"),
        ("unknown_tools", "unknown"),
        ("evidence", "evidence"),
        ("capabilities", ["fabricated"]),
        ("unknown_tools", [""]),
        ("evidence", [""]),
        ("capabilities", ["repository-read", "repository-read"]),
        ("unknown_tools", ["z", "a"]),
        ("evidence", ["same", "same"]),
    ],
)
def test_capability_receipt_projection_rejects_malformed_fields(
    field: str,
    value: object,
) -> None:
    receipt = host_capability_receipt("codex", platform="linux").as_dict()
    receipt[field] = value

    assert project_host_capability_receipt(receipt) is None


def test_capability_receipt_projection_rejects_oversized_bounded_fields() -> None:
    receipt = host_capability_receipt("codex", platform="linux").as_dict()
    for field, values in (
        ("capabilities", ["repository-read"] * (MAX_TOOL_CAPABILITIES + 1)),
        ("unknown_tools", [f"unknown-{index}" for index in range(MAX_TOOL_CAPABILITIES + 1)]),
        (
            "evidence",
            [f"evidence-{index}" for index in range(MAX_CAPABILITY_EVIDENCE_ITEMS + 1)],
        ),
    ):
        oversized = {**receipt, field: values}
        assert project_host_capability_receipt(oversized) is None


def test_capability_receipt_projection_rejects_incoherent_sources_and_statuses() -> None:
    native = native_adapter_capability_receipt(
        "codex",
        platform="linux",
        session_id="session",
        trace_id="trace",
    ).as_dict()
    native["surface"] = "claude"
    assert project_host_capability_receipt(native) is None

    inference = host_capability_receipt("litellm", platform="linux").as_dict()
    inference["source"] = "native-adapter-event"
    assert project_host_capability_receipt(inference) is None

    unknown = host_capability_receipt("unknown", platform="linux").as_dict()
    unknown["status"] = "native-contract-verified"
    assert project_host_capability_receipt(unknown) is None

    unproven = host_capability_receipt_from_native_evidence(
        "codex",
        platform="linux",
        native_record=None,
    ).as_dict()
    unproven["capabilities"] = ["repository-read"]
    assert project_host_capability_receipt(unproven) is None

    explicit = host_capability_receipt(
        "unknown",
        platform="linux",
        available_tools=("source",),
    ).as_dict()
    explicit["source"] = "native-installation-evidence"
    assert project_host_capability_receipt(explicit) is None


def test_native_inventory_unknown_host_and_platform_remain_unproven() -> None:
    receipt = host_capability_receipt_from_native_evidence(
        "mcp",
        platform="plan9",
        native_record={"host": "mcp"},
    )

    assert receipt.platform == "unknown"
    assert receipt.execution_host == ""
    assert receipt.status == "unknown"


def test_capability_receipt_survives_content_free_store_projection() -> None:
    receipt = native_adapter_capability_receipt(
        "claude",
        platform="linux",
        session_id="session",
        trace_id="trace",
    ).as_dict()
    routing = {
        "selected_ids": [],
        "status": "abstained",
        "execution_context": receipt,
    }

    recipe = _content_free_routing_recipe(routing, trace_id="trace")
    decision, _work_units, _source = project_routing_decision(recipe)

    assert recipe["execution_context"] == receipt
    assert decision["execution_context"] == receipt
